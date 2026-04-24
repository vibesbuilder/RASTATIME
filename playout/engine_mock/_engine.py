"""
MockPlayoutEngine — a no-audio implementation of PlayoutEngine for dev/test.

Behaviour
---------
* Simulates state (STOPPED / PLAYING / PAUSED / ERROR).
* Advances through the loaded queue automatically: each item plays for
  ``item.duration`` seconds (or ``default_track_duration`` if unknown).
* Fires ``on_track_change`` callbacks at every track boundary and at
  start/stop transitions.
* All public methods are thread-safe (internal RLock).
* Callbacks are invoked *outside* the lock to prevent deadlocks.
"""

import threading
import time
from typing import Callable, Optional

from ..engine_interface import (
    PlayoutError,
    PlayoutState,
    QueueItem,
    TrackChangedEvent,
)
from ..engine_interface._engine import PlayoutEngine


class MockPlayoutEngine(PlayoutEngine):
    """
    In-process playout stub with no audio output.

    Parameters
    ----------
    default_track_duration:
        Seconds to simulate for a QueueItem whose ``duration`` is None.
        Default 5.0 s; use a very small value (e.g. 0.05) in fast unit tests.
    """

    def __init__(self, default_track_duration: float = 5.0) -> None:
        self._lock = threading.RLock()
        self._state: PlayoutState = PlayoutState.STOPPED
        self._queue: list[QueueItem] = []
        self._current_index: int = -1          # -1 = not playing
        self._timer: Optional[threading.Timer] = None
        self._start_time: Optional[float] = None  # monotonic; reset each track
        self._paused_remaining: Optional[float] = None

        self._default_track_duration = default_track_duration

        self._track_change_cbs: list[Callable[[TrackChangedEvent], None]] = []
        self._error_cbs: list[Callable[[PlayoutError], None]] = []

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start playback from the first item in the queue."""
        with self._lock:
            if self._state in (PlayoutState.PLAYING, PlayoutState.PAUSED):
                return
            if not self._queue:
                return
            self._current_index = 0
            self._state = PlayoutState.PLAYING
            self._start_time = time.monotonic()
            first_item = self._queue[0]
            self._schedule_advance(self._item_duration(first_item))

        self._fire_track_change(None, first_item)

    def stop(self) -> None:
        """Stop playback and reset position."""
        with self._lock:
            self._cancel_timer()
            prev = self._current_item_unsafe()
            self._state = PlayoutState.STOPPED
            self._current_index = -1
            self._start_time = None
            self._paused_remaining = None

        if prev is not None:
            self._fire_track_change(prev, None)

    def pause(self) -> None:
        """Pause at the current position."""
        with self._lock:
            if self._state != PlayoutState.PLAYING:
                return
            self._cancel_timer()
            self._paused_remaining = self._remaining_unsafe()
            self._state = PlayoutState.PAUSED

    def resume(self) -> None:
        """Resume from the paused position."""
        with self._lock:
            if self._state != PlayoutState.PAUSED:
                return
            remaining = self._paused_remaining if self._paused_remaining is not None else 0.0
            self._state = PlayoutState.PLAYING
            self._paused_remaining = None
            # Rebase start_time so remaining() stays consistent
            current = self._current_item_unsafe()
            total = self._item_duration(current)
            self._start_time = time.monotonic() - (total - remaining)
            self._schedule_advance(remaining)

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def load_queue(self, items: list[QueueItem]) -> None:
        """Replace the queue; stops playback if currently playing."""
        with self._lock:
            was_playing = self._state in (PlayoutState.PLAYING, PlayoutState.PAUSED)
            prev = self._current_item_unsafe() if was_playing else None
            self._cancel_timer()
            self._queue = list(items)
            self._current_index = -1
            self._state = PlayoutState.STOPPED
            self._start_time = None
            self._paused_remaining = None

        if was_playing and prev is not None:
            self._fire_track_change(prev, None)

    def append(self, item: QueueItem) -> None:
        """Append one item to the end of the queue."""
        with self._lock:
            self._queue.append(item)

    def clear_queue(self) -> None:
        """
        Remove all *pending* items.
        The currently playing item is kept; queue shrinks to [current].
        """
        with self._lock:
            current = self._current_item_unsafe()
            if current is not None:
                self._queue = [current]
                self._current_index = 0
            else:
                self._queue = []
                self._current_index = -1

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self) -> PlayoutState:
        with self._lock:
            return self._state

    def get_current_item(self) -> Optional[QueueItem]:
        with self._lock:
            return self._current_item_unsafe()

    def get_remaining_duration(self) -> Optional[float]:
        with self._lock:
            return self._remaining_unsafe()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_track_change(
        self, callback: Callable[[TrackChangedEvent], None]
    ) -> None:
        self._track_change_cbs.append(callback)

    def on_error(self, callback: Callable[[PlayoutError], None]) -> None:
        self._error_cbs.append(callback)

    # ------------------------------------------------------------------
    # Device selection (no-op in mock)
    # ------------------------------------------------------------------

    def select_output_device(self, device_id: str) -> None:
        """No-op: mock engine has no real audio output."""

    # ------------------------------------------------------------------
    # Internal helpers — call only while holding self._lock
    # ------------------------------------------------------------------

    def _current_item_unsafe(self) -> Optional[QueueItem]:
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    def _item_duration(self, item: Optional[QueueItem]) -> float:
        if item is not None and item.duration is not None:
            return item.duration
        return self._default_track_duration

    def _remaining_unsafe(self) -> Optional[float]:
        if self._state == PlayoutState.PAUSED:
            return self._paused_remaining
        if self._state != PlayoutState.PLAYING or self._start_time is None:
            return None
        elapsed = time.monotonic() - self._start_time
        current = self._current_item_unsafe()
        total = self._item_duration(current)
        return max(0.0, total - elapsed)

    def _schedule_advance(self, delay: float) -> None:
        self._timer = threading.Timer(delay, self._advance_track)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    # ------------------------------------------------------------------
    # Timer callback (runs in a background thread)
    # ------------------------------------------------------------------

    def _advance_track(self) -> None:
        """Called by the timer when the current track's simulated time expires."""
        prev_item: Optional[QueueItem]
        next_item: Optional[QueueItem]

        with self._lock:
            if self._state != PlayoutState.PLAYING:
                return

            prev_item = self._current_item_unsafe()
            self._current_index += 1

            if self._current_index >= len(self._queue):
                # Queue exhausted — stop naturally
                self._state = PlayoutState.STOPPED
                self._current_index = -1
                self._start_time = None
                next_item = None
            else:
                next_item = self._queue[self._current_index]
                self._start_time = time.monotonic()
                self._schedule_advance(self._item_duration(next_item))

        self._fire_track_change(prev_item, next_item)

    # ------------------------------------------------------------------
    # Callback dispatch — always called OUTSIDE the lock
    # ------------------------------------------------------------------

    def _fire_track_change(
        self,
        previous: Optional[QueueItem],
        current: Optional[QueueItem],
    ) -> None:
        event = TrackChangedEvent(previous_item=previous, current_item=current)
        for cb in list(self._track_change_cbs):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                pass

    def _fire_error(self, error: PlayoutError) -> None:
        for cb in list(self._error_cbs):
            try:
                cb(error)
            except Exception:  # noqa: BLE001
                pass
