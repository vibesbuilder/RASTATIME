"""
NowPlayingState — thread-safe in-memory tracker of what is on air.

Updated by connecting it to a PlayoutEngine's ``on_track_change``
callback::

    from playout.now_playing import NowPlayingState
    state = NowPlayingState()
    engine.on_track_change(state.on_track_change)

    entry = state.get()
    if entry.is_playing:
        print(f"On air: {entry.item.title} @ {entry.started_at}")
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from ..engine_interface import QueueItem, TrackChangedEvent


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class NowPlayingEntry:
    """
    Snapshot of the current on-air state.

    Parameters
    ----------
    item:
        The ``QueueItem`` currently playing, or *None* when idle.
    started_at:
        UTC datetime when *item* started, or *None* when idle.
    """

    item: Optional[QueueItem]
    started_at: Optional[datetime]

    @property
    def is_playing(self) -> bool:
        """*True* when a track is on air."""
        return self.item is not None

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for ``JsonResponse``."""
        if self.item is None:
            return {
                "is_playing": False,
                "item": None,
                "started_at": None,
            }
        return {
            "is_playing": True,
            "item": {
                "id": self.item.id,
                "uri": self.item.uri,
                "title": self.item.title,
                "artist": self.item.artist,
                "duration": self.item.duration,
                "metadata": self.item.metadata,
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


class NowPlayingState:
    """
    Thread-safe now-playing tracker.

    Connect to a ``PlayoutEngine`` via::

        engine.on_track_change(state.on_track_change)

    Subscribe to state-change notifications via ``subscribe()``.
    Subscribers are called from whatever thread the engine fires its
    callbacks on — do not block.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entry = NowPlayingEntry(item=None, started_at=None)
        self._subscribers: List[Callable[[NowPlayingEntry], None]] = []

    # ------------------------------------------------------------------
    # Engine callback
    # ------------------------------------------------------------------

    def on_track_change(self, event: TrackChangedEvent) -> None:
        """
        Registered with ``engine.on_track_change()``.

        Updates the in-memory entry and notifies subscribers.
        """
        if event.current_item is not None:
            new_entry = NowPlayingEntry(
                item=event.current_item,
                started_at=event.timestamp,
            )
        else:
            new_entry = NowPlayingEntry(item=None, started_at=None)

        with self._lock:
            self._entry = new_entry

        for cb in list(self._subscribers):
            try:
                cb(new_entry)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self) -> NowPlayingEntry:
        """Return a snapshot of the current on-air state."""
        with self._lock:
            return self._entry

    def subscribe(self, cb: Callable[[NowPlayingEntry], None]) -> None:
        """
        Register *cb* to be called whenever the now-playing state changes.

        *cb* receives the new ``NowPlayingEntry``.  Called on the engine's
        callback thread — must not block.
        """
        self._subscribers.append(cb)
