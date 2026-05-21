"""
SourceConnection — lifecycle state-holder for one incoming stream source.

Responsibilities
----------------
* Hold one :class:`~streams.ingress.interface.StreamSource` configuration.
* Track the source's :class:`~streams._types.StreamState` through its
  lifecycle: IDLE → CONNECTING → ACTIVE → DISCONNECTED / ERROR.
* Track whether this source is currently *routed to playout* (``is_active``),
  which is a separate concern from the connection state:

  - A source can be ACTIVE (audio received) but not yet routing to playout.
  - A source can be CONNECTING while a previous source is still active.

* Fire :class:`~streams.ingress.interface.SourceStateChangedEvent` callbacks
  on every state transition.
* Track ``connected_since`` timestamp and ``error_message``.
* Provide exponential-backoff reconnect bookkeeping (same as
  :class:`~streams.egress._connection.StreamConnection`).

What ``SourceConnection`` does NOT do
--------------------------------------
* It does not connect to the remote stream (that is the ingress manager's job).
* It does not own a watchdog timer (owned by the manager for testability).
* It does not interact with the playout engine directly.

Thread safety
-------------
All state mutations are protected by an internal ``threading.Lock``.
Callbacks are fired outside the lock to avoid deadlock.

Relation to UC-I1 / UC-I2 (STREAM_USE_CASES §5)
-------------------------------------------------
UC-I1 (Show Source): source is registered, activated at show start_at,
  deactivated at show end_at — QueueManager preempts via start_show().
UC-I2 (Master Source): source remains active across shows (higher priority);
  normal playout resumes automatically on source disconnect.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from .._types import StreamState
from .interface import SourceStateChangedEvent, SourceStatus, StreamSource

logger = logging.getLogger(__name__)

StateCallback = Callable[[SourceStateChangedEvent], None]


class SourceConnection:
    """
    Lifecycle state holder for one :class:`StreamSource`.

    A ``SourceConnection`` is created by the ingress manager when a source is
    registered.  The manager calls :meth:`transition` to drive state changes
    as connection events occur, and :meth:`activate` / :meth:`deactivate` to
    control whether this source is currently feeding the playout pipeline.

    Parameters
    ----------
    source:
        The immutable stream source configuration for this connection.
    """

    _BASE_BACKOFF: float = 5.0
    _RECONNECT_MAX_BACKOFF: float = 60.0

    def __init__(self, source: StreamSource) -> None:
        self._source: StreamSource = source
        self._lock = threading.Lock()

        # Connection state
        self._state: StreamState = StreamState.IDLE
        self._connected_since: Optional[datetime] = None
        self._error_message: Optional[str] = None

        # Playout-routing flag (separate from connection state)
        self._is_active: bool = False

        # Reconnect exponential backoff
        self._reconnect_attempt: int = 0
        self._reconnect_backoff: float = self._BASE_BACKOFF

        # Registered state-change callbacks
        self._callbacks: list[StateCallback] = []

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def source(self) -> StreamSource:
        """The stream source configuration (immutable)."""
        return self._source

    @property
    def source_id(self) -> str:
        """Convenience alias for ``source.id``."""
        return self._source.id

    @property
    def state(self) -> StreamState:
        """Current connection state (thread-safe snapshot)."""
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        """
        ``True`` if this source is currently routed to the playout engine.

        Independent of :attr:`state` — a source may be connected but not
        yet active (buffering / priority not met) or active but degraded.
        """
        with self._lock:
            return self._is_active

    @property
    def reconnect_attempt(self) -> int:
        """Number of reconnect attempts since the last successful ACTIVE state."""
        with self._lock:
            return self._reconnect_attempt

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def transition(
        self,
        new_state: StreamState,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Transition to *new_state* and fire registered callbacks.

        Same-state transitions are no-ops (callback is NOT fired).

        Parameters
        ----------
        new_state:
            Target :class:`~streams._types.StreamState`.
        error_message:
            Optional error detail; populated for ERROR and DISCONNECTED.
        """
        with self._lock:
            if new_state == self._state:
                return  # no-op

            previous = self._state
            self._state = new_state
            self._error_message = error_message

            if new_state == StreamState.ACTIVE:
                self._connected_since = datetime.now(tz=timezone.utc)
                self._reconnect_attempt = 0
                self._reconnect_backoff = self._BASE_BACKOFF
            elif new_state in (StreamState.DISCONNECTED, StreamState.ERROR):
                self._connected_since = None
            elif new_state == StreamState.IDLE:
                self._connected_since = None
                self._error_message = None
                self._is_active = False
                self._reconnect_attempt = 0
                self._reconnect_backoff = self._BASE_BACKOFF

            event = SourceStateChangedEvent(
                source_id=self._source.id,
                previous_state=previous,
                current_state=new_state,
                error_message=error_message,
            )

        logger.info(
            "SourceConnection %r: %s → %s%s",
            self._source.id,
            previous.value,
            new_state.value,
            f" ({error_message})" if error_message else "",
        )

        for cb in list(self._callbacks):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled exception in source state-change callback")

    # ------------------------------------------------------------------
    # Playout-routing control
    # ------------------------------------------------------------------

    def activate(self) -> None:
        """
        Mark this source as currently routed to the playout engine.

        Sets :attr:`is_active` to ``True``.  Does NOT change :attr:`state`.
        Idempotent if already active.
        """
        with self._lock:
            self._is_active = True
        logger.debug("SourceConnection %r: activated (routing to playout)", self._source.id)

    def deactivate(self) -> None:
        """
        Mark this source as no longer routed to the playout engine.

        Sets :attr:`is_active` to ``False``.  Does NOT change :attr:`state`.
        Idempotent if already inactive.
        """
        with self._lock:
            self._is_active = False
        logger.debug("SourceConnection %r: deactivated", self._source.id)

    # ------------------------------------------------------------------
    # Reconnect backoff helpers
    # ------------------------------------------------------------------

    def next_backoff(self) -> float:
        """
        Return the current reconnect backoff interval and advance it.

        Each call doubles the backoff (exponential) up to
        ``_RECONNECT_MAX_BACKOFF`` (60 s).

        Returns
        -------
        float
            Seconds to wait before the next reconnect attempt.
        """
        with self._lock:
            delay = self._reconnect_backoff
            self._reconnect_attempt += 1
            self._reconnect_backoff = min(
                self._reconnect_backoff * 2,
                self._RECONNECT_MAX_BACKOFF,
            )
        return delay

    # ------------------------------------------------------------------
    # Status snapshot
    # ------------------------------------------------------------------

    def status(self) -> SourceStatus:
        """
        Return a snapshot of the current runtime status.

        Thread-safe; safe to call from any thread.
        """
        with self._lock:
            return SourceStatus(
                source_id=self._source.id,
                state=self._state,
                is_active=self._is_active,
                connected_since=self._connected_since,
                error_message=self._error_message,
            )

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def add_state_callback(self, callback: StateCallback) -> None:
        """
        Register a callback invoked on every state transition.

        The callback receives a :class:`SourceStateChangedEvent`.
        Multiple callbacks may be registered; all are called in order.
        Exceptions in callbacks are caught per-callback.
        """
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"SourceConnection(id={self._source.id!r}, "
                f"state={self._state.value!r}, "
                f"is_active={self._is_active!r})"
            )
