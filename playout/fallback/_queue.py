"""
FallbackQueue — stub queue manager for fallback/filler content.

A ``FallbackQueue`` holds an ordered list of :class:`QueueItem` objects
that the :class:`~playout.scheduler.PlayoutScheduler` plays automatically
whenever no scheduled show is active.

Stub scope (T6.2)
-----------------
This is an intentionally minimal implementation.  The ``items`` list is
static; no weighting, history-awareness, or smart-playlist logic is applied.
A full queue manager (dynamic playlists, weighted random selection, duplicate
avoidance) is planned for a later milestone.

Loop behaviour
--------------
When ``loop=True`` (default) the scheduler restarts the entire item list
after the last item finishes, creating continuous filler playback.

When ``loop=False`` the items play once; after the last item the engine
returns to STOPPED until the next scheduled show.

Usage example
-------------
::

    from playout.fallback import FallbackQueue
    from playout.scheduler import PlayoutScheduler
    from playout.engine_interface import QueueItem
    from playout.engine_vlc import VlcPlayoutEngine

    engine = VlcPlayoutEngine(vlc_args=["--aout=dummy"])
    scheduler = PlayoutScheduler(engine)

    fallback = FallbackQueue(
        items=[
            QueueItem(id="jingle", uri="file:///jingle.wav", duration=30.0),
            QueueItem(id="filler", uri="file:///filler.mp3", duration=180.0),
        ],
        loop=True,
    )
    scheduler.set_fallback(fallback)
"""

from __future__ import annotations

from typing import List

from ..engine_interface import QueueItem


class FallbackQueue:
    """
    Ordered list of fallback items played when no show is scheduled.

    Parameters
    ----------
    items:
        Tracks to use as filler content.  Must contain at least one item
        for fallback to be active.
    loop:
        If *True* (default), the item list restarts after the last item
        finishes.  If *False*, plays once and stops.

    Notes
    -----
    This is a **stub** implementation (T6.2).  Future versions will support
    dynamic playlists, weighted random selection, and history-aware deduplication.
    """

    def __init__(self, items: List[QueueItem], loop: bool = True) -> None:
        if not items:
            raise ValueError("FallbackQueue requires at least one item")
        self._items: List[QueueItem] = list(items)
        self._loop: bool = loop

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def items(self) -> List[QueueItem]:
        """A copy of the fallback item list."""
        return list(self._items)

    @property
    def loop(self) -> bool:
        """Whether the fallback list repeats after the last item."""
        return self._loop

    def is_empty(self) -> bool:
        """Always *False* for a valid ``FallbackQueue`` (constructor enforces non-empty)."""
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return (
            f"FallbackQueue({len(self._items)} item(s), loop={self._loop})"
        )
