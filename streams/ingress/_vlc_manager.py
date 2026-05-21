"""
LibVlcIngressManager — concrete StreamIngressManager backed by libVLC.

Responsibilities
----------------
* Implement the :class:`~streams.ingress.interface.StreamIngressManager` ABC.
* Register, activate, and deactivate incoming remote stream sources.
* When a source is activated: construct an HTTP URI from the
  :class:`~streams.ingress.interface.StreamSource` config and load it into
  the playout engine as a :class:`~playout.engine_interface.QueueItem`.
  libVLC will then pull the stream and route it through the audio pipeline
  exactly as if it were a local audio file.
* Run a watchdog timer to detect when the remote source goes silent and
  transition the connection to DISCONNECTED automatically.

Architectural notes
-------------------
UC-I1 (Show Source) and UC-I2 (Master Source) — the ingress manager does NOT
automatically return the engine to scheduled content after a source is lost or
deactivated.  The calling layer (QueueManager / PlayoutScheduler) must reload
the scheduled queue explicitly.  This keeps the ingress manager stateless with
respect to scheduled content.

The engine protocol is deliberately minimal (:class:`_IngressEngine`): only
``load_queue``, ``start``, and ``stop`` are required.  This allows any
``PlayoutEngine`` implementation to serve as a backend, and allows lightweight
test doubles that do not require VLC to be installed.

Stream URI format
-----------------
:func:`build_stream_uri` constructs the URI from the source config:

* Without credentials: ``http://host:port/mount``
* With credentials:    ``http://user:password@host:port/mount``
* Mount is always normalised to start with ``/``.

Watchdog
--------
After activation, a :class:`threading.Timer` fires every ``watchdog_interval``
seconds and calls ``health_checker(source)``.  If healthy, the source
transitions to ACTIVE (if not already) and the watchdog re-arms.  If
unhealthy, the source transitions to DISCONNECTED, the engine is stopped,
and the source is removed from the active set.  State-change callbacks
are fired so the application layer can respond (e.g. reload scheduled queue).

Thread safety
-------------
All mutations to ``_sources``, ``_connections``, and ``_active_source_id``
are protected by ``self._lock``.  Callbacks and engine calls are made outside
the lock.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Protocol

from playout.engine_interface import QueueItem

from .._types import StreamState
from ._connection import SourceConnection
from .interface import (
    SourceStateChangedEvent,
    SourceStatus,
    StreamIngressManager,
    StreamSource,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine protocol — satisfied by VlcPlayoutEngine and test doubles
# ---------------------------------------------------------------------------

class _IngressEngine(Protocol):
    """Minimal playout engine protocol required for ingress activation."""

    def load_queue(self, items: list) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...


# ---------------------------------------------------------------------------
# Health checker protocol (injectable for testing)
# ---------------------------------------------------------------------------

IngressHealthChecker = Callable[[StreamSource], bool]
"""
``health_checker(source) -> bool``

Returns ``True`` if the remote stream source is reachable and has an active
source client.  Returns ``False`` on any error or if the source is gone.

For unit tests: inject a simple lambda.
For production: use :func:`default_ingress_health_checker`.
"""


def default_ingress_health_checker(source: StreamSource) -> bool:
    """
    Check whether the remote stream source is still reachable.

    Makes an HTTP HEAD request to the stream URL.  Returns ``True`` for any
    2xx/3xx response (stream is live); ``False`` for 4xx/5xx or network error.

    For Icecast sources this typically returns ``200 OK`` when a DJ is
    connected; ``404 Not Found`` or connection refused when the mount is empty.
    """
    import urllib.request

    uri = build_stream_uri(source)
    try:
        req = urllib.request.Request(uri, method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status < 400
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Ingress health check failed for %r (%s): %s",
            getattr(source, "id", source),
            uri,
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# URI builder
# ---------------------------------------------------------------------------

def build_stream_uri(source: StreamSource) -> str:
    """
    Construct the HTTP stream URI for *source*.

    Rules
    -----
    * Mount is normalised to start with ``/``.
    * Credentials are embedded as ``user:password@`` only when both
      ``username`` and ``password`` are non-empty.

    Examples
    --------
    >>> build_stream_uri(source)  # no credentials
    'http://icecast.example.com:8000/live'
    >>> build_stream_uri(source)  # with credentials
    'http://listener:secret@icecast.example.com:8000/live'
    """
    mount = source.mount if source.mount.startswith("/") else f"/{source.mount}"
    if source.username and source.password:
        return (
            f"http://{source.username}:{source.password}"
            f"@{source.url}:{source.port}{mount}"
        )
    return f"http://{source.url}:{source.port}{mount}"


# ---------------------------------------------------------------------------
# LibVlcIngressManager
# ---------------------------------------------------------------------------

class LibVlcIngressManager(StreamIngressManager):
    """
    libVLC-backed implementation of :class:`StreamIngressManager`.

    Parameters
    ----------
    engine:
        A playout engine that satisfies :class:`_IngressEngine`.
        In production: :class:`VlcPlayoutEngine`.
        In tests: any object with ``load_queue``, ``start``, ``stop``.
    watchdog_interval:
        Seconds between health-check ticks (default 10 s).
    health_checker:
        Injectable health-check callable.  Defaults to
        :func:`default_ingress_health_checker`.
    """

    def __init__(
        self,
        engine: _IngressEngine,
        watchdog_interval: float = 10.0,
        health_checker: Optional[IngressHealthChecker] = None,
    ) -> None:
        self._engine = engine
        self._watchdog_interval = watchdog_interval
        self._health_checker: IngressHealthChecker = (
            health_checker
            if health_checker is not None
            else default_ingress_health_checker
        )

        self._lock = threading.Lock()
        self._sources: dict[str, StreamSource] = {}
        self._connections: dict[str, SourceConnection] = {}
        self._active_source_id: Optional[str] = None

        self._state_callbacks: list[Callable[[SourceStateChangedEvent], None]] = []
        self._watchdog: Optional[threading.Timer] = None

    # ------------------------------------------------------------------
    # StreamIngressManager — registration
    # ------------------------------------------------------------------

    def register_source(self, source: StreamSource) -> None:
        """Register a remote stream source.  Does not activate it."""
        with self._lock:
            if source.id in self._sources:
                logger.debug("Replacing existing source %r", source.id)
            self._sources[source.id] = source
        logger.info(
            "Registered ingress source %r (%s:%s%s)",
            source.id, source.url, source.port, source.mount,
        )

    def unregister_source(self, source_id: str) -> None:
        """Unregister a source, deactivating it first if currently active."""
        self._stop_source_internal(source_id, new_state=StreamState.IDLE)
        with self._lock:
            if self._active_source_id == source_id:
                self._active_source_id = None
            self._sources.pop(source_id, None)
        logger.info("Removed ingress source %r", source_id)

    def list_sources(self) -> list[StreamSource]:
        """Return all registered sources regardless of state."""
        with self._lock:
            return list(self._sources.values())

    # ------------------------------------------------------------------
    # StreamIngressManager — activation
    # ------------------------------------------------------------------

    def activate_source(self, source_id: str) -> None:
        """
        Route *source_id* to the playout pipeline.

        1. Validates the source is registered.
        2. Creates a :class:`SourceConnection` in CONNECTING state.
        3. Loads the stream URI into the engine and starts playback.
        4. Arms the watchdog.

        Only one source may be active at a time.  If another source is
        currently active it is deactivated first.

        Raises
        ------
        ValueError
            If *source_id* is not registered.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                raise ValueError(f"Unknown ingress source id: {source_id!r}")
            current_active = self._active_source_id

        # Deactivate any existing active source first
        if current_active is not None and current_active != source_id:
            self._stop_source_internal(current_active, new_state=StreamState.IDLE)

        # Create new connection
        conn = SourceConnection(source)
        conn.add_state_callback(self._on_connection_state_change)

        with self._lock:
            self._connections[source_id] = conn
            self._active_source_id = source_id

        conn.transition(StreamState.CONNECTING)
        conn.activate()

        # Load and play the stream
        item = QueueItem(
            id=f"ingress-{source.id}",
            uri=build_stream_uri(source),
            title=source.name,
            duration=None,          # live stream — no fixed duration
        )
        self._engine.load_queue([item])
        self._engine.start()

        # Arm watchdog to promote CONNECTING → ACTIVE after health check
        self._arm_watchdog()

        logger.info("Activated ingress source %r → %s", source_id, build_stream_uri(source))

    def deactivate_source(self, source_id: str) -> None:
        """
        Stop routing *source_id* to the playout pipeline and return to IDLE.

        The playout engine is stopped.  The calling layer is responsible for
        reloading scheduled content afterwards.

        Raises
        ------
        ValueError
            If *source_id* is not registered.
        """
        with self._lock:
            if source_id not in self._sources:
                raise ValueError(f"Unknown ingress source id: {source_id!r}")

        self._cancel_watchdog()
        self._stop_source_internal(source_id, new_state=StreamState.IDLE)

        with self._lock:
            if self._active_source_id == source_id:
                self._active_source_id = None

        self._engine.stop()
        logger.info("Deactivated ingress source %r", source_id)

    # ------------------------------------------------------------------
    # StreamIngressManager — status
    # ------------------------------------------------------------------

    def get_active_source(self) -> Optional[StreamSource]:
        """Return the currently active source, or ``None``."""
        with self._lock:
            active_id = self._active_source_id
            return self._sources.get(active_id) if active_id else None

    def get_source_status(self, source_id: str) -> SourceStatus:
        """
        Return the runtime status for one source.

        Raises ValueError if not registered.
        """
        with self._lock:
            if source_id not in self._sources:
                raise ValueError(f"Unknown ingress source id: {source_id!r}")
            conn = self._connections.get(source_id)

        if conn is not None:
            return conn.status()

        return SourceStatus(source_id=source_id, state=StreamState.IDLE)

    # ------------------------------------------------------------------
    # StreamIngressManager — callbacks
    # ------------------------------------------------------------------

    def on_source_state_change(
        self, callback: Callable[[SourceStateChangedEvent], None]
    ) -> None:
        """Register a callback invoked on every source state transition."""
        self._state_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal: watchdog
    # ------------------------------------------------------------------

    def _arm_watchdog(self) -> None:
        """Cancel any running watchdog and arm a fresh one."""
        self._cancel_watchdog()
        timer = threading.Timer(self._watchdog_interval, self._on_watchdog)
        timer.daemon = True
        with self._lock:
            self._watchdog = timer
        timer.start()

    def _cancel_watchdog(self) -> None:
        with self._lock:
            timer = self._watchdog
            self._watchdog = None
        if timer is not None:
            timer.cancel()

    def _on_watchdog(self) -> None:
        """
        Watchdog tick: health-check the active source.

        * Healthy → promote to ACTIVE (if CONNECTING), re-arm watchdog.
        * Unhealthy → transition to DISCONNECTED, stop engine, fire callbacks.
        """
        with self._lock:
            active_id = self._active_source_id

        if active_id is None:
            return

        with self._lock:
            conn = self._connections.get(active_id)
            source = self._sources.get(active_id)

        if conn is None or source is None:
            return

        healthy = self._health_checker(source)

        if healthy:
            if conn.state != StreamState.ACTIVE:
                conn.transition(StreamState.ACTIVE)
            logger.debug("Watchdog: ingress source %r is healthy", active_id)
            self._arm_watchdog()
        else:
            logger.warning(
                "Watchdog: ingress source %r appears lost — disconnecting",
                active_id,
            )
            conn.transition(
                StreamState.DISCONNECTED,
                error_message="watchdog: remote source unreachable",
            )
            conn.deactivate()
            with self._lock:
                # Keep conn in _connections so get_source_status() returns
                # DISCONNECTED (not the IDLE fallback).  It is replaced when
                # the source is re-activated, or removed on unregister.
                self._active_source_id = None
            self._engine.stop()

    # ------------------------------------------------------------------
    # Internal: stop helper
    # ------------------------------------------------------------------

    def _stop_source_internal(
        self, source_id: str, new_state: StreamState = StreamState.IDLE
    ) -> None:
        """Remove connection for *source_id* and transition to *new_state*."""
        with self._lock:
            conn = self._connections.pop(source_id, None)
        if conn is not None:
            conn.deactivate()
            conn.transition(new_state)
            logger.debug("Stopped ingress source %r → %s", source_id, new_state.value)

    # ------------------------------------------------------------------
    # Internal: propagate state-change events
    # ------------------------------------------------------------------

    def _on_connection_state_change(self, event: SourceStateChangedEvent) -> None:
        """Forward connection state changes to manager-level callbacks."""
        for cb in list(self._state_callbacks):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled exception in ingress manager state callback")
