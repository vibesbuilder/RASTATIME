"""
PlayoutHistoryLogger — in-memory ring-buffer of completed track plays.

Records a ``HistoryEntry`` for every track that starts playing.  Entries
are finalised (``ended_at`` set) when the next ``TrackChangedEvent``
arrives, meaning the currently playing track always has ``ended_at=None``
until it finishes.

Connect to a ``PlayoutEngine`` via::

    from playout.now_playing import PlayoutHistoryLogger
    logger = PlayoutHistoryLogger()
    engine.on_track_change(logger.on_track_change)

    recent = logger.recent(10)     # list[HistoryEntry], newest first
    current = logger.current()     # HistoryEntry | None (in-progress)

Completion subscribers
----------------------
Register a callback to be notified whenever a ``HistoryEntry`` is
finalised (i.e. the next track starts or playback stops)::

    logger.on_entry_completed(my_callback)
    # my_callback(entry: HistoryEntry) is called for each completed entry.

Callbacks are invoked **outside** the internal lock, on whatever thread
the engine fires its ``TrackChangedEvent`` on.  They must not block.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Deque, List, Optional

from ..engine_interface import QueueItem, TrackChangedEvent


@dataclass
class HistoryEntry:
    """
    Record of a single track play.

    Parameters
    ----------
    item:
        The ``QueueItem`` that was played.
    started_at:
        UTC datetime when the track started.
    ended_at:
        UTC datetime when the track ended; *None* while still playing.
    """

    item: QueueItem
    started_at: datetime
    ended_at: Optional[datetime] = None

    @property
    def duration_played(self) -> Optional[float]:
        """Seconds actually played; *None* if still in progress."""
        if self.ended_at is None:
            return None
        return max(0.0, (self.ended_at - self.started_at).total_seconds())

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for ``JsonResponse``."""
        return {
            "item_id": self.item.id,
            "title": self.item.title,
            "artist": self.item.artist,
            "uri": self.item.uri,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_played": self.duration_played,
        }


class PlayoutHistoryLogger:
    """
    Thread-safe in-memory playout history ring-buffer.

    Each ``TrackChangedEvent`` is processed as follows:

    * The *previous* item's ``HistoryEntry`` (if any) is finalised with
      ``ended_at = event.timestamp`` and pushed into the completed ring.
    * The *current* item (if not *None*) starts a new in-progress entry.

    Parameters
    ----------
    max_entries:
        Maximum number of *completed* entries to retain.  Oldest entries
        are discarded automatically when the buffer is full.  The
        in-progress entry is not counted.

    Example
    -------
    ::

        logger = PlayoutHistoryLogger()
        engine.on_track_change(logger.on_track_change)

        # … after some tracks play …
        for entry in logger.recent(5):
            print(entry.item.title, entry.duration_played)
    """

    def __init__(self, max_entries: int = 500) -> None:
        self._lock = threading.Lock()
        self._completed: Deque[HistoryEntry] = deque(maxlen=max_entries)
        self._in_progress: Optional[HistoryEntry] = None
        self._completion_callbacks: List[Callable[[HistoryEntry], None]] = []

    # ------------------------------------------------------------------
    # Subscriber registration
    # ------------------------------------------------------------------

    def on_entry_completed(self, cb: Callable[[HistoryEntry], None]) -> None:
        """
        Register *cb* to be called whenever a ``HistoryEntry`` is finalised.

        A ``HistoryEntry`` is finalised when the next ``TrackChangedEvent``
        arrives (i.e. the current track ends and the next one begins, or
        playback stops entirely).

        *cb* receives the completed ``HistoryEntry`` (with ``ended_at`` set).
        It is called **outside** the internal lock, on the engine's callback
        thread.  It must not block.  Exceptions are silently swallowed so
        that one bad subscriber cannot break others.

        Parameters
        ----------
        cb:
            Callable with signature ``(entry: HistoryEntry) -> None``.
        """
        self._completion_callbacks.append(cb)

    # ------------------------------------------------------------------
    # Engine callback
    # ------------------------------------------------------------------

    def on_track_change(self, event: TrackChangedEvent) -> None:
        """
        Registered with ``engine.on_track_change()``.

        Finalises the previous entry and opens a new one.
        Completion subscribers are notified outside the lock.
        """
        completed_entry: Optional[HistoryEntry] = None

        with self._lock:
            # Finalise in-progress entry (previous item just ended)
            if self._in_progress is not None:
                self._in_progress.ended_at = event.timestamp
                self._completed.append(self._in_progress)
                completed_entry = self._in_progress
                self._in_progress = None

            # Start tracking the new item (if any)
            if event.current_item is not None:
                self._in_progress = HistoryEntry(
                    item=event.current_item,
                    started_at=event.timestamp,
                )

        # Notify completion subscribers outside the lock
        if completed_entry is not None:
            for cb in list(self._completion_callbacks):
                try:
                    cb(completed_entry)
                except Exception:  # noqa: BLE001
                    pass

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def recent(self, n: int = 10) -> List[HistoryEntry]:
        """
        Return the *n* most recent completed entries, newest first.

        The currently playing track (if any) is excluded — it has no
        ``ended_at`` yet.  Use ``current()`` to inspect it.
        """
        with self._lock:
            entries = list(self._completed)
        return list(reversed(entries))[:n]

    def current(self) -> Optional[HistoryEntry]:
        """
        Return the entry for the currently playing track, or *None*.

        The returned entry has ``ended_at=None``; it is a live snapshot
        of the in-progress play.
        """
        with self._lock:
            return self._in_progress

    def total_completed(self) -> int:
        """Return the number of completed entries in the buffer."""
        with self._lock:
            return len(self._completed)
