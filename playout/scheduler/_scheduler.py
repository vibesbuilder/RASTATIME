"""
PlayoutScheduler — time-based bridge between a show schedule and a PlayoutEngine.

Responsibilities
----------------
* Accept a :class:`ScheduledShow` (show id, UTC start/end, track list).
* Fire ``engine.load_queue()`` + ``engine.start()`` at ``start_at``.
* Fire ``engine.stop()`` at ``end_at`` (hard cutoff regardless of queue state).
* Allow cancellation of a pending show by id.

Threading model
---------------
Timers run in daemon threads.  All mutations to ``_pending`` are protected
by a single ``threading.Lock``.  Engine calls are made *outside* the lock.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..engine_interface import PlayoutEngine, QueueItem

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


@dataclass
class ScheduledShow:
    """
    Descriptor for a single scheduled on-air slot.

    Parameters
    ----------
    show_id:
        Unique string identifier for this slot (e.g. LibreTime schedule row id).
    start_at:
        UTC datetime when playback should begin.
    end_at:
        UTC datetime when playback must stop (hard cutoff).
    items:
        Ordered list of tracks to load into the engine at start time.
    """

    show_id: str
    start_at: datetime   # UTC (timezone-aware or naive; both accepted)
    end_at: datetime     # UTC
    items: list = field(default_factory=list)  # list[QueueItem]

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


class _ShowJob:
    """Internal holder for the two timers associated with one scheduled show."""

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


class PlayoutScheduler:
    """
    Time-based playout dispatcher.

    Wraps any :class:`~playout.engine_interface.PlayoutEngine` and drives it
    from a wall-clock schedule.

    Parameters
    ----------
    engine:
        The playout backend to control.

    Example
    -------
    ::

        from datetime import datetime, timedelta, timezone
        from playout.engine_mock import MockPlayoutEngine
        from playout.scheduler import PlayoutScheduler, ScheduledShow
        from playout.engine_interface import QueueItem

        engine = MockPlayoutEngine()
        scheduler = PlayoutScheduler(engine)

        now = datetime.now(tz=timezone.utc)
        show = ScheduledShow(
            show_id="show-1",
            start_at=now + timedelta(seconds=5),
            end_at=now + timedelta(seconds=15),
            items=[QueueItem(id="t1", uri="file:///track1.mp3", duration=10.0)],
        )
        scheduler.schedule(show)
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

        Parameters
        ----------
        show:
            The show to schedule.
        """
        now = _utcnow()

        # Skip shows that have already ended.
        if show.end_at <= now:
            logger.debug("Skipping past show %r (ended at %s)", show.show_id, show.end_at)
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

    def cancel(self, show_id: str) -> bool:
        """
        Cancel a pending show.

        Parameters
        ----------
        show_id:
            Id of the show to cancel.

        Returns
        -------
        bool
            *True* if a pending job was found and cancelled, *False* otherwise.
        """
        with self._lock:
            job = self._pending.pop(show_id, None)
        if job is not None:
            job.cancel()
            logger.debug("Cancelled show %r", show_id)
            return True
        return False

    def cancel_all(self) -> int:
        """
        Cancel all pending shows.

        Returns
        -------
        int
            Number of jobs cancelled.
        """
        with self._lock:
            jobs = list(self._pending.values())
            self._pending.clear()
        for job in jobs:
            job.cancel()
        logger.debug("Cancelled %d pending show(s)", len(jobs))
        return len(jobs)

    def pending_show_ids(self) -> list:
        """Return a snapshot of pending show ids."""
        with self._lock:
            return list(self._pending.keys())

    # ------------------------------------------------------------------
    # Timer callbacks — run in daemon threads
    # ------------------------------------------------------------------

    def _on_start(self, show: ScheduledShow) -> None:
        logger.info("Starting show %r (%d items)", show.show_id, len(show.items))
        try:
            self._engine.load_queue(show.items)
            self._engine.start()
        except Exception:  # noqa: BLE001
            logger.exception("Error starting show %r", show.show_id)

    def _on_stop(self, show_id: str) -> None:
        logger.info("Stopping show %r", show_id)
        try:
            self._engine.stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping show %r", show_id)
        with self._lock:
            self._pending.pop(show_id, None)
