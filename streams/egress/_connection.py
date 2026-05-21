"""
StreamConnection — lifecycle state-holder for one outgoing stream output.

Responsibilities
----------------
* Hold one :class:`~streams.egress.interface.StreamOutput` configuration.
* Track the connection's :class:`~streams._types.StreamState` through its
  lifecycle: IDLE → CONNECTING → ACTIVE → DISCONNECTED / ERROR.
* Fire :class:`~streams.egress.interface.OutputStateChangedEvent` callbacks
  on every state transition.
* Track ``connected_since`` timestamp and ``error_message``.

What ``StreamConnection`` does NOT do
--------------------------------------
* It does not call libVLC directly (that is ``LibVlcEgressManager``'s job).
* It does not own the watchdog timer (owned by the manager for testability).
* It does not push ICY metadata (handled by ``IcyMetadataPusher``).

Thread safety
-------------
All state mutations are protected by an internal ``threading.Lock``.
Callbacks are fired outside the lock to avoid deadlock.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional, TYPE_CHECKING

from .._types import StreamState
from .interface import OutputStateChangedEvent, OutputStatus, StreamOutput

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

StateCallback = Callable[[OutputStateChangedEvent], None]


class StreamConnection:
    """
    Lifecycle state holder for one :class:`StreamOutput`.

    A ``StreamConnection`` is created by :class:`LibVlcEgressManager` when an
    output is registered.  The manager calls :meth:`transition` to drive state
    changes as connection events occur.

    Parameters
    ----------
    output:
        The immutable stream output configuration for this connection.
    """

    def __init__(self, output: StreamOutput) -> None:
        self._output: StreamOutput = output
        self._lock = threading.Lock()

        # Current state
        self._state: StreamState = StreamState.IDLE
        self._connected_since: Optional[datetime] = None
        self._error_message: Optional[str] = None

        # Reconnect exponential backoff
        self._reconnect_attempt: int = 0
        self._reconnect_backoff: float = 5.0   # seconds, doubles on each attempt
        _RECONNECT_MAX_BACKOFF: float = 60.0   # seconds

        self._RECONNECT_MAX_BACKOFF = _RECONNECT_MAX_BACKOFF
        self._BASE_BACKOFF = 5.0

        # Registered state-change callbacks
        self._callbacks: list[StateCallback] = []

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def output(self) -> StreamOutput:
        """The stream output configuration (immutable)."""
        return self._output

    @property
    def output_id(self) -> str:
        """Convenience alias for ``output.id``."""
        return self._output.id

    @property
    def state(self) -> StreamState:
        """Current connection state (thread-safe snapshot)."""
        with self._lock:
            return self._state

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

        Parameters
        ----------
        new_state:
            The target :class:`~streams._types.StreamState`.
        error_message:
            Optional human-readable error detail; populated for ERROR and
            DISCONNECTED transitions.
        """
        event: Optional[OutputStateChangedEvent]

        with self._lock:
            if new_state == self._state:
                return  # no-op if already in target state

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
                self._reconnect_attempt = 0
                self._reconnect_backoff = self._BASE_BACKOFF
                self._error_message = None

            event = OutputStateChangedEvent(
                output_id=self._output.id,
                previous_state=previous,
                current_state=new_state,
                error_message=error_message,
            )

        logger.info(
            "StreamConnection %r: %s → %s%s",
            self._output.id,
            previous.value,
            new_state.value,
            f" ({error_message})" if error_message else "",
        )

        # Fire callbacks outside the lock
        for cb in list(self._callbacks):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled exception in state-change callback")

    # ------------------------------------------------------------------
    # Reconnect backoff helpers
    # ------------------------------------------------------------------

    def next_backoff(self) -> float:
        """
        Return the current reconnect backoff interval and advance it.

        Each call doubles the backoff (exponential) up to
        ``_RECONNECT_MAX_BACKOFF`` seconds.

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

    @property
    def reconnect_attempt(self) -> int:
        """Number of reconnect attempts since the last successful ACTIVE state."""
        with self._lock:
            return self._reconnect_attempt

    # ------------------------------------------------------------------
    # Status snapshot
    # ------------------------------------------------------------------

    def status(self) -> OutputStatus:
        """
        Return a snapshot of the current runtime status.

        Safe to call from any thread.
        """
        with self._lock:
            return OutputStatus(
                output_id=self._output.id,
                state=self._state,
                connected_since=self._connected_since,
                error_message=self._error_message,
            )

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def add_state_callback(self, callback: StateCallback) -> None:
        """
        Register a callback invoked on every state transition.

        The callback receives an :class:`OutputStateChangedEvent`.
        Multiple callbacks may be registered; all are called in order.
        """
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"StreamConnection(id={self._output.id!r}, "
                f"state={self._state.value!r})"
            )
