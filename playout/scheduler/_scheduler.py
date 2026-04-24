"""
PlayoutScheduler — time-based bridge between a show schedule and a PlayoutEngine.

Responsibilities
----------------
* Accept a :class:`ScheduledShow` (show id, UTC start/end, track list,
  start mode).
* At ``start_at``: dispatch the configured start action to the engine.
* At ``end_at``: fire a hard ``engine.stop()`` (regardless of queue state).
* Allow cancellation of a pending show by id.

Start modes
-----------
``StartMode.HARD`` (default)
    Immediately stop whatever is playing, load the new queue, and call
    ``engine.start()``.  Use for scheduled shows that must begin on time.

``StartMode.SOFT``
    Do not interrupt the current track.  Discard any remaining pending items
    in the engine's queue (``clear_queue()``), then append the new show's
    items so they play sequentially after the current track ends.  If the
    engine is already STOPPED, behaves like HARD.

Load-next (queue preloading)
----------------------------
``schedule_next(show)`` appends the new show's items to the engine's queue
*immediately* (no timer), useful when the next show is known well in advance
and a near-gapless transition is desired.

Threading model
---------------
Timers run in daemon threads.  All mutations to ``_pending`` are protected
by a single ``threading.Lock``.  Engine calls are made *outside* the lock.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ..engine_interface import PlayoutEngine, PlayoutState, QueueItem

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# StartMode
# ---------------------------------------------------------------------------

class StartMode(str, Enum):
    """
    Controls how the scheduler transitions to a new show.

    HARD
        Stop any current playback immediately, load the new queue, start.
        Guarantees the new show begins at ``start_at`` regardless of what
        is currently playing.

    SOFT
        Do not interrupt the current track.  Clear pending queue items and
        append the new show's items so they play after the current track.
        If the engine is already STOPPED, falls back to HARD behaviour.
    """

    HARD = "hard"
    SOFT = "soft"


# ---------------------------------------------------------------------------
# ScheduledShow
# ---------------------------------------------------------------------------

@dataclass
class ScheduledShow:
    """
    Descriptor for a single scheduled on-air slot.

    Parameters
    ----------
    show_id:
        Unique string identifier for this slot (e.g. LibreTime schedule
        row id or a generated UUID).
    start_at:
        UTC datetime when playback should begin.  Naive datetimes are
        treated as UTC.
    end_at:
        UTC datetime when playback must stop (hard cutoff).  Naive
        datetimes are treated as UTC.
    items:
        Ordered list of :class:`~playout.engine_interface.QueueItem`
        objects to play.
    start_mode:
        How to begin the show — see :class:`StartMode`.  Defaults to
        ``StartMode.HARD``.
    """

    show_id: str
    start_at: datetime
    end_at: datetime
    items: list = field(default_factory=list)  # list[QueueItem]
    start_mode: StartMode = StartMode.HARD

    def __post_init__(self) -> None:
        # Normalise to aware datetimes so subtraction always works.
        if self.start_at.tzinfo is None:
            self.start_at = self.start_at.replace(tzinfo=timezone.utc)
        if self.end_at.tzinfo is None:
            self.end_at = self.end_at.replace(tzinfo=timezone.utc)

    @property
    def duration(self) -> float:
        """Total show duration in seconds."""
        return max(0.0, (self.end_at - self.start_at).total_seconds())


# ---------------------------------------------------------------------------
# Internal job holder
# ---------------------------------------------------------------------------

class _ShowJob:
    """Two timers (start + stop) associated with one scheduled show."""

    def __init__(
        self,
        show: ScheduledShow,
        start_timer: threading.Timer,
        stop_timer: threading.Timer,
    ) -> None:
        self.show = show
        self._start_timer = start_timer
        self._stop_timer = stop_timer

    def cancel(self) -> None:
        self._start_timer.cancel()
        self._stop_timer.cancel()


# ---------------------------------------------------------------------------
# PlayoutScheduler
# ---------------------------------------------------------------------------

class PlayoutScheduler:
    """
    Time-based playout dispatcher.

    Wraps any :class:`~playout.engine_interface.PlayoutEngine` and drives it
    from a wall-clock schedule.  Supports hard and soft show transitions and
    queue preloading for near-gapless show boundaries.

    Parameters
    ----------
    engine:
        The playout backend to control.  Both :class:`MockPlayoutEngine`
        and :class:`VlcPlayoutEngine` are accepted.

    Example — two back-to-back shows (hard transition)
    ---------------------------------------------------
    ::

        from datetime import datetime, timedelta, timezone
        from playout.engine_vlc import VlcPlayoutEngine
        from playout.scheduler import PlayoutScheduler, ScheduledShow, StartMode
        from playout.engine_interface import QueueItem

        engine = VlcPlayoutEngine(vlc_args=["--aout=dummy"])
        scheduler = PlayoutScheduler(engine)
        now = datetime.now(tz=timezone.utc)

        show_a = ScheduledShow(
            show_id="show-a",
            start_at=now + timedelta(seconds=1),
            end_at=now + timedelta(seconds=11),
            items=[QueueItem(id="t1", uri="file:///a.wav", duration=10.0)],
            start_mode=StartMode.HARD,
        )
        show_b = ScheduledShow(
            show_id="show-b",
            start_at=now + timedelta(seconds=11),
            end_at=now + timedelta(seconds=21),
            items=[QueueItem(id="t2", uri="file:///b.wav", duration=10.0)],
            start_mode=StartMode.HARD,
        )
        scheduler.schedule(show_a)
        scheduler.schedule(show_b)
    """

    def __init__(self, engine: PlayoutEngine) -> None:
        self._engine = engine
        self._lock = threading.Lock()
        self._pending: dict[str, _ShowJob] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule(self, show: ScheduledShow) -> None:
        """
        Schedule *show* for future playback.

        If a job with the same ``show_id`` is already pending it is cancelled
        and replaced.  Shows whose ``end_at`` is already in the past are
        silently ignored.

        The start action respects ``show.start_mode``:
        - ``HARD``: immediately replace the engine queue and start.
        - ``SOFT``: append items after the current track; start if stopped.
        """
        now = _utcnow()

        if show.end_at <= now:
            logger.debug(
                "Skipping past show %r (ended at %s)", show.show_id, show.end_at
            )
            return

        delay_start = max(0.0, (show.start_at - now).total_seconds())
        delay_stop = max(0.0, (show.end_at - now).total_seconds())

        start_timer = threading.Timer(delay_start, self._on_start, args=(show,))
        stop_timer = threading.Timer(delay_stop, self._on_stop, args=(show.show_id,))
        start_timer.daemon = True
        stop_timer.daemon = True

        job = _ShowJob(show, start_timer, stop_timer)

        with self._lock:
            existing = self._pending.pop(show.show_id, None)
            self._pending[show.show_id] = job

        if existing is not None:
            existing.cancel()
            logger.debug("Replaced existing job for show %r", show.show_id)

        start_timer.start()
        stop_timer.start()
        logger.debug(
            "Scheduled show %r: start in %.3fs, stop in %.3fs",
            show.show_id, delay_start, delay_stop,
        )

    def schedule_next(self, show: ScheduledShow) -> None:
        """
        Preload a show's items into the engine queue *right now*.

        Items are appended via ``engine.append()`` without stopping current
        playback.  The stop timer is still armed so the show ends at
        ``end_at``.  The start timer is still armed but the start action
        becomes a no-op if the engine is already playing (useful for
        near-gapless hand-off).

        Use this when the next show is known well in advance and you want
        to minimise the inter-show gap.
        """
        for item in show.items:
            self._engine.append(item)
        # Still schedule the stop; the start will soft-merge
        show = ScheduledShow(
            show_id=show.show_id,
            start_at=show.start_at,
            end_at=show.end_at,
            items=show.items,
            start_mode=StartMode.SOFT,
        )
        self.schedule(show)
        logger.info(
            "Preloaded %d item(s) for show %r", len(show.items), show.show_id
        )

    def cancel(self, show_id: str) -> bool:
        """
        Cancel a pending show.

        Returns *True* if a pending job was found and cancelled.
        """
        with self._lock:
            job = self._pending.pop(show_id, None)
        if job is not None:
            job.cancel()
            logger.debug("Cancelled show %r", show_id)
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all pending shows. Returns the number cancelled."""
        with self._lock:
            jobs = list(self._pending.values())
            self._pending.clear()
        for job in jobs:
            job.cancel()
        logger.debug("Cancelled %d pending show(s)", len(jobs))
        return len(jobs)

    def pending_show_ids(self) -> list:
        """Return a snapshot of currently pending show ids."""
        with self._lock:
            return list(self._pending.keys())

    # ------------------------------------------------------------------
    # Timer callbacks — run in daemon threads
    # ------------------------------------------------------------------

    def _on_start(self, show: ScheduledShow) -> None:
        logger.info(
            "Show %r starting (mode=%s, %d items)",
            show.show_id, show.start_mode.value, len(show.items),
        )
        try:
            if show.start_mode == StartMode.HARD:
                self._hard_start(show)
            else:
                self._soft_start(show)
        except Exception:  # noqa: BLE001
            logger.exception("Error starting show %r", show.show_id)

    def _on_stop(self, show_id: str) -> None:
        logger.info("Show %r hard-stop (end_at reached)", show_id)
        try:
            self._engine.stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping show %r", show_id)
        with self._lock:
            self._pending.pop(show_id, None)

    # ------------------------------------------------------------------
    # Start-mode implementations
    # ------------------------------------------------------------------

    def _hard_start(self, show: ScheduledShow) -> None:
        """
        Stop current playback immediately, load new queue, start.

        This is the default and guarantees the show begins at ``start_at``.
        """
        self._engine.load_queue(show.items)
        self._engine.start()
        logger.debug("Hard-started show %r", show.show_id)

    def _soft_start(self, show: ScheduledShow) -> None:
        """
        Transition to the new show without interrupting the current track.

        If the engine is STOPPED: fall back to hard start.
        If the engine is PLAYING or PAUSED: discard pending queue items
        (keeping the current track) and append the new show's items so they
        play next.  The current track finishes naturally; no gap beyond the
        normal inter-track latency.
        """
        state = self._engine.get_state()
        if state == PlayoutState.STOPPED:
            logger.debug(
                "Soft-start for %r: engine stopped, falling back to hard start",
                show.show_id,
            )
            self._hard_start(show)
            return

        # Engine is active — splice new items in after the current track.
        self._engine.clear_queue()
        for item in show.items:
            self._engine.append(item)
        logger.debug(
            "Soft-started show %r: %d item(s) queued after current track",
            show.show_id, len(show.items),
        )
