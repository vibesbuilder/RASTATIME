"""
LibVlcEgressManager — concrete StreamEgressManager backed by libVLC sout chains.

Responsibilities
----------------
* Implement the :class:`~streams.egress.interface.StreamEgressManager` ABC.
* Register, start, stop, and monitor outgoing stream outputs.
* Build libVLC sout chain strings via :class:`~._sout.SoutBuilder` and apply
  them to the playout engine via ``engine.set_sout_chain()``.
* Push ICY metadata to Icecast via :class:`~._metadata.IcyMetadataPusher`
  on every ``TrackChangedEvent``.
* Run a watchdog timer (UC-O8) to detect silent connection loss and
  trigger exponential-backoff reconnect, because libVLC's shout module does
  NOT fire error events on Windows (T9.2 Q8a finding).

Architectural constraints
-------------------------
* Requires a playout engine that exposes ``set_sout_chain(chain)`` and
  ``on_track_change(callback)`` — satisfied by :class:`VlcPlayoutEngine`.
  The type is declared as a ``Protocol`` so the manager remains testable
  with lightweight doubles without requiring VLC to be installed.
* For multi-output (UC-O6, T10.3): calls :meth:`SoutBuilder.for_multi_output`
  to compose all enabled outputs into a single ``duplicate{}`` sout chain.

Watchdog / reconnect (UC-O8)
-----------------------------
Because VLC's shout module blocks indefinitely on connection failure
(T9.2 Q8a), the manager uses an *external* watchdog ``threading.Timer``.

Timeline::

    start_output() arms watchdog (watchdog_interval seconds)
    ↓ watchdog fires → _on_watchdog() checks Icecast health
    ↓ source present → re-arm watchdog (normal case)
    ↓ source absent  → transition to DISCONNECTED, wait backoff, reconnect

The Icecast health check is injected (``health_checker`` parameter) so
it can be mocked in unit tests without a real Icecast server.

Thread model
------------
The watchdog timer runs in a daemon thread.  All mutations to ``_outputs``
and the sout chain on the engine are protected by ``self._lock``.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Protocol

from .._types import StreamState
from ._connection import StreamConnection
from ._health import IcecastHealthChecker
from ._metadata import IcyMetadataPusher
from ._sout import SoutBuilder
from .interface import (
    OutputStateChangedEvent,
    OutputStatus,
    StreamEgressManager,
    StreamOutput,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine protocol — implemented by VlcPlayoutEngine (and test doubles)
# ---------------------------------------------------------------------------

class _SoutEngine(Protocol):
    """Minimal protocol for engines that support sout chains."""

    def set_sout_chain(self, chain: Optional[str]) -> None: ...
    def on_track_change(self, callback: Callable) -> None: ...
    def reload_sout(self) -> None:
        """
        Re-apply the current sout chain to the currently playing item.

        Optional: engines that do not support immediate sout reload simply
        leave this as a no-op.  :class:`LibVlcEgressManager` calls this
        after :meth:`set_sout_chain` so streaming starts from the current
        track position rather than waiting for the next natural advance.
        """
        ...


# ---------------------------------------------------------------------------
# Health checker protocol (injectable for testing)
# ---------------------------------------------------------------------------

HealthChecker = Callable[[StreamOutput], bool]
"""
``health_checker(output) -> bool``

Returns ``True`` if the stream source is confirmed connected (e.g. by
polling the Icecast HTTP ``/status-json.xsl`` endpoint and confirming the
mount has a source client).  Returns ``False`` if the source appears gone.

For unit tests: inject a simple lambda.
For production: the default is :class:`~._health.IcecastHealthChecker`.
"""


# ---------------------------------------------------------------------------
# LibVlcEgressManager
# ---------------------------------------------------------------------------

class LibVlcEgressManager(StreamEgressManager):
    """
    libVLC-backed implementation of :class:`StreamEgressManager`.

    Parameters
    ----------
    engine:
        A playout engine that satisfies the :class:`_SoutEngine` protocol.
        In production: a :class:`VlcPlayoutEngine` instance.
        In tests: any object with ``set_sout_chain()`` and ``on_track_change()``.
    watchdog_interval:
        Seconds between health-check ticks (default 30 s).
    health_checker:
        Injectable health-check callable.  Defaults to the Icecast HTTP
        ``/status-json.xsl`` poller.
    idle_title:
        ICY metadata title pushed when the engine is idle.
    """

    def __init__(
        self,
        engine: _SoutEngine,
        watchdog_interval: float = 30.0,
        health_checker: Optional[HealthChecker] = None,
        idle_title: str = "RASTATIME",
    ) -> None:
        self._engine = engine
        self._watchdog_interval = watchdog_interval
        self._health_checker: HealthChecker = (
            health_checker if health_checker is not None else IcecastHealthChecker()
        )
        self._idle_title = idle_title

        self._lock = threading.Lock()
        self._outputs: dict[str, StreamOutput] = {}           # registered outputs
        self._connections: dict[str, StreamConnection] = {}   # active connections
        self._metadata_pushers: dict[str, IcyMetadataPusher] = {}

        self._state_callbacks: list[Callable[[OutputStateChangedEvent], None]] = []

        self._watchdog: Optional[threading.Timer] = None

        # Subscribe to track changes for metadata push + watchdog reset
        engine.on_track_change(self._on_track_change)

    # ------------------------------------------------------------------
    # StreamEgressManager — registration
    # ------------------------------------------------------------------

    def add_output(self, output: StreamOutput) -> None:
        """Register a new stream output. Does not start streaming."""
        with self._lock:
            if output.id in self._outputs:
                logger.debug("Replacing existing output %r", output.id)
            self._outputs[output.id] = output
        logger.info("Registered output %r (%s, %s)", output.id, output.codec, output.url)

    def remove_output(self, output_id: str) -> None:
        """Unregister an output, stopping it first if active."""
        self._stop_output_internal(output_id)
        with self._lock:
            self._outputs.pop(output_id, None)
        logger.info("Removed output %r", output_id)

    def list_outputs(self) -> list[StreamOutput]:
        """Return all registered outputs."""
        with self._lock:
            return list(self._outputs.values())

    # ------------------------------------------------------------------
    # StreamEgressManager — lifecycle
    # ------------------------------------------------------------------

    def start_output(self, output_id: str) -> None:
        """
        Begin streaming on *output_id*.

        1. Validates the output is registered.
        2. Creates a :class:`StreamConnection` in CONNECTING state.
        3. Rebuilds the composite sout chain and applies it to the engine.
        4. Arms the watchdog timer.

        Raises
        ------
        ValueError
            If *output_id* is not registered.
        """
        with self._lock:
            output = self._outputs.get(output_id)
            if output is None:
                raise ValueError(f"Unknown output id: {output_id!r}")

        conn = StreamConnection(output)
        conn.add_state_callback(self._on_connection_state_change)

        pusher = IcyMetadataPusher(output, idle_title=self._idle_title)

        with self._lock:
            self._connections[output_id] = conn
            self._metadata_pushers[output_id] = pusher

        conn.transition(StreamState.CONNECTING)

        # Rebuild and apply sout chain
        self._apply_sout_chain()

        # If the engine is already playing, reload immediately so streaming
        # begins from the current track rather than waiting for the next advance.
        try:
            self._engine.reload_sout()
        except Exception:  # noqa: BLE001
            # reload_sout is optional — engines that don't support it are fine
            pass

        # Arm watchdog — transitions to ACTIVE after first successful tick
        self._arm_watchdog()

        logger.info("Started output %r", output_id)

    def stop_output(self, output_id: str) -> None:
        """
        Stop streaming on *output_id*.

        Raises
        ------
        ValueError
            If *output_id* is not registered.
        """
        with self._lock:
            if output_id not in self._outputs:
                raise ValueError(f"Unknown output id: {output_id!r}")

        self._stop_output_internal(output_id)
        self._apply_sout_chain()  # rebuild without the stopped output

    def start_all(self) -> None:
        """Start all enabled outputs."""
        with self._lock:
            ids = [oid for oid, o in self._outputs.items() if o.enabled]
        for output_id in ids:
            try:
                self.start_output(output_id)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to start output %r", output_id)

    def stop_all(self) -> None:
        """Stop all active outputs."""
        self._cancel_watchdog()
        with self._lock:
            ids = list(self._connections.keys())
        for output_id in ids:
            self._stop_output_internal(output_id)
        # Remove all sout from engine
        self._engine.set_sout_chain(None)
        logger.info("All outputs stopped")

    # ------------------------------------------------------------------
    # StreamEgressManager — status
    # ------------------------------------------------------------------

    def get_output_status(self, output_id: str) -> OutputStatus:
        """
        Return the current runtime status for one output.

        Raises ValueError if not registered.
        """
        with self._lock:
            if output_id not in self._outputs:
                raise ValueError(f"Unknown output id: {output_id!r}")
            conn = self._connections.get(output_id)

        if conn is not None:
            return conn.status()

        # Registered but not started
        return OutputStatus(output_id=output_id, state=StreamState.IDLE)

    # ------------------------------------------------------------------
    # StreamEgressManager — callbacks
    # ------------------------------------------------------------------

    def on_output_state_change(
        self, callback: Callable[[OutputStateChangedEvent], None]
    ) -> None:
        """Register a callback invoked on every output state transition."""
        self._state_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal: sout chain management
    # ------------------------------------------------------------------

    def _active_outputs(self) -> list[StreamOutput]:
        """Return configs for all currently active/connecting connections."""
        with self._lock:
            return [
                self._outputs[oid]
                for oid in self._connections
                if oid in self._outputs
            ]

    def _apply_sout_chain(self) -> None:
        """
        Rebuild the composite sout chain from all active outputs and apply
        it to the engine via ``set_sout_chain()``.

        Called after any start/stop that changes the active output set.
        """
        active = self._active_outputs()
        if not active:
            self._engine.set_sout_chain(None)
            logger.debug("sout chain cleared (no active outputs)")
            return

        try:
            chain = SoutBuilder.for_multi_output(active)
        except ValueError as exc:
            logger.error("Failed to build sout chain: %s", exc)
            return

        self._engine.set_sout_chain(chain)
        logger.debug("sout chain applied (%d output(s)): %s", len(active), chain)

    def _stop_output_internal(self, output_id: str) -> None:
        """Remove connection for *output_id* and transition it to IDLE."""
        with self._lock:
            conn = self._connections.pop(output_id, None)
            self._metadata_pushers.pop(output_id, None)
        if conn is not None:
            conn.transition(StreamState.IDLE)
            logger.debug("Stopped output %r", output_id)

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
        Watchdog tick: health-check each active connection.

        * If Icecast confirms the source is present → mark ACTIVE, re-arm.
        * If source is absent → mark DISCONNECTED, start reconnect.
        """
        with self._lock:
            conns = dict(self._connections)

        for output_id, conn in conns.items():
            with self._lock:
                output = self._outputs.get(output_id)
            if output is None:
                continue

            healthy = self._health_checker(output)
            if healthy:
                if conn.state != StreamState.ACTIVE:
                    conn.transition(StreamState.ACTIVE)
                logger.debug("Watchdog: output %r is healthy", output_id)
            else:
                logger.warning(
                    "Watchdog: output %r appears disconnected (attempt %d)",
                    output_id, conn.reconnect_attempt,
                )
                conn.transition(
                    StreamState.DISCONNECTED,
                    error_message="watchdog: source not found on Icecast",
                )
                # Schedule reconnect after exponential backoff
                backoff = conn.next_backoff()
                reconnect_timer = threading.Timer(
                    backoff, self._reconnect_output, args=(output_id,)
                )
                reconnect_timer.daemon = True
                reconnect_timer.start()
                logger.info(
                    "Reconnect for %r scheduled in %.0f s", output_id, backoff
                )
                continue  # don't re-arm watchdog for this output; reconnect will

        # Re-arm watchdog if any connection is still active
        with self._lock:
            active_ids = list(self._connections.keys())
        if active_ids:
            self._arm_watchdog()

    def _reconnect_output(self, output_id: str) -> None:
        """
        Reconnect attempt for *output_id* after a backoff delay.

        Calls :meth:`start_output` again; the engine's next media load will
        pick up the refreshed sout chain.
        """
        with self._lock:
            if output_id not in self._connections:
                logger.debug("Reconnect aborted: %r no longer tracked", output_id)
                return

        logger.info("Attempting reconnect for output %r", output_id)
        try:
            # Remove old connection state and re-start
            self._stop_output_internal(output_id)
            self.start_output(output_id)
        except Exception:  # noqa: BLE001
            logger.exception("Reconnect failed for %r", output_id)

    # ------------------------------------------------------------------
    # Internal: track-change handler (metadata push + watchdog reset)
    # ------------------------------------------------------------------

    def _on_track_change(self, event) -> None:
        """
        Called by the engine on every ``TrackChangedEvent``.

        * Pushes ICY metadata to all active Icecast outputs.
        * Idle event (current_item is None): pushes idle title.
        """
        with self._lock:
            pushers = dict(self._metadata_pushers)

        current = event.current_item
        if current is not None:
            title = getattr(current, "title", "") or ""
            artist = getattr(current, "artist", "") or ""
            for output_id, pusher in pushers.items():
                try:
                    pusher.push(title, artist)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Metadata push failed for output %r", output_id
                    )
        else:
            # Track ended / engine idle
            for output_id, pusher in pushers.items():
                try:
                    pusher.push_idle()
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Idle metadata push failed for output %r", output_id
                    )

    # ------------------------------------------------------------------
    # Internal: propagate state change events
    # ------------------------------------------------------------------

    def _on_connection_state_change(self, event: OutputStateChangedEvent) -> None:
        """Forward connection state changes to manager-level callbacks."""
        for cb in list(self._state_callbacks):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled exception in manager state callback")
