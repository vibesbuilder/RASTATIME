"""
T4.3 validation — PlayoutScheduler.

Verifies that:
1. PlayoutScheduler instantiates with any PlayoutEngine.
2. A scheduled show triggers engine.load_queue + engine.start at start_at (V).
3. The stop timer triggers engine.stop at end_at (V).
4. Shows whose end_at is in the past are silently ignored.
5. cancel() removes a pending show and prevents start/stop.
6. cancel_all() removes all pending shows.
7. Rescheduling the same show_id replaces the previous job.
8. A show starting immediately (delay=0) still triggers correctly.
9. pending_show_ids() reflects the live pending set.
10. start_at in the past but end_at in the future starts immediately.

Timing notes
------------
DELAY  = 0.05 s — how far in the future start_at is set.
WINDOW = 0.02 s — track duration inside the show.
MARGIN = 0.6 s  — sleep budget; covers timer jitter on a busy CI box.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from playout.engine_interface import PlayoutState, QueueItem
from playout.engine_mock import MockPlayoutEngine
from playout.scheduler import PlayoutScheduler, ScheduledShow

DELAY = 0.05      # seconds until show starts
WINDOW = 0.02     # track duration
MARGIN = 0.6      # total sleep budget


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _show(
    show_id: str = "s1",
    delay: float = DELAY,
    duration: float = WINDOW,
    n_items: int = 1,
) -> ScheduledShow:
    start = _now() + timedelta(seconds=delay)
    end = start + timedelta(seconds=duration)
    items = [
        QueueItem(id=f"{show_id}-t{i}", uri=f"file:///track{i}.mp3", duration=duration)
        for i in range(n_items)
    ]
    return ScheduledShow(show_id=show_id, start_at=start, end_at=end, items=items)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

def test_scheduler_instantiates():
    engine = MockPlayoutEngine()
    scheduler = PlayoutScheduler(engine)
    assert scheduler.pending_show_ids() == []


# ---------------------------------------------------------------------------
# V criterion: show triggers start then stop (simulated "10-second show")
# ---------------------------------------------------------------------------

def test_show_starts_and_stops(monkeypatch):
    """
    Schedule a short show; assert engine transitions STOPPED -> PLAYING -> STOPPED.
    This is the V criterion for T4.3 (simulated short show in place of 10 s).
    """
    engine = MockPlayoutEngine(default_track_duration=WINDOW)
    scheduler = PlayoutScheduler(engine)

    assert engine.get_state() == PlayoutState.STOPPED

    show = _show(delay=DELAY, duration=MARGIN * 0.5)
    scheduler.schedule(show)

    # Before start_at: engine still stopped
    assert engine.get_state() == PlayoutState.STOPPED

    # Wait past start_at
    time.sleep(DELAY + 0.05)
    assert engine.get_state() == PlayoutState.PLAYING

    # Wait past end_at (stop timer fires)
    time.sleep(MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED


def test_show_loads_correct_queue():
    """Engine receives exactly the items from the ScheduledShow."""
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    items = [
        QueueItem(id="a", uri="file:///a.mp3", duration=60.0),
        QueueItem(id="b", uri="file:///b.mp3", duration=60.0),
    ]
    show = ScheduledShow(
        show_id="queue-test",
        start_at=_now() + timedelta(seconds=DELAY),
        end_at=_now() + timedelta(seconds=DELAY + 120.0),
        items=items,
    )
    scheduler.schedule(show)

    time.sleep(DELAY + 0.05)
    assert engine.get_state() == PlayoutState.PLAYING
    # First track is still playing (60s duration, only ~0.1s elapsed)
    assert engine.get_current_item() == items[0]

    engine.stop()


# ---------------------------------------------------------------------------
# Past shows
# ---------------------------------------------------------------------------

def test_past_show_is_ignored():
    """A show whose end_at is in the past must be silently dropped."""
    engine = MockPlayoutEngine()
    scheduler = PlayoutScheduler(engine)

    past_start = _now() - timedelta(seconds=10)
    past_end = _now() - timedelta(seconds=1)
    show = ScheduledShow(
        show_id="past",
        start_at=past_start,
        end_at=past_end,
        items=[QueueItem(id="t", uri="file:///t.mp3", duration=1.0)],
    )
    scheduler.schedule(show)

    assert "past" not in scheduler.pending_show_ids()
    assert engine.get_state() == PlayoutState.STOPPED


def test_show_starting_in_past_but_ongoing():
    """
    If start_at is past but end_at is still future, the show starts immediately
    (delay clamped to 0) and the stop timer fires at end_at.
    """
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    show = ScheduledShow(
        show_id="ongoing",
        start_at=_now() - timedelta(seconds=1),   # already started
        end_at=_now() + timedelta(seconds=MARGIN * 0.5),
        items=[QueueItem(id="t", uri="file:///t.mp3", duration=60.0)],
    )
    scheduler.schedule(show)

    time.sleep(0.1)
    assert engine.get_state() == PlayoutState.PLAYING

    time.sleep(MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# cancel / cancel_all
# ---------------------------------------------------------------------------

def test_cancel_prevents_start():
    engine = MockPlayoutEngine()
    scheduler = PlayoutScheduler(engine)

    show = _show(delay=MARGIN * 0.5)  # far enough in the future
    scheduler.schedule(show)
    assert show.show_id in scheduler.pending_show_ids()

    cancelled = scheduler.cancel(show.show_id)
    assert cancelled is True
    assert show.show_id not in scheduler.pending_show_ids()

    time.sleep(MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED


def test_cancel_nonexistent_returns_false():
    scheduler = PlayoutScheduler(MockPlayoutEngine())
    assert scheduler.cancel("no-such-show") is False


def test_cancel_all_clears_all_pending():
    engine = MockPlayoutEngine()
    scheduler = PlayoutScheduler(engine)

    for i in range(3):
        scheduler.schedule(_show(show_id=f"show-{i}", delay=MARGIN * 0.5))

    assert len(scheduler.pending_show_ids()) == 3

    n = scheduler.cancel_all()
    assert n == 3
    assert scheduler.pending_show_ids() == []

    time.sleep(MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# Rescheduling
# ---------------------------------------------------------------------------

def test_reschedule_same_id_replaces_job():
    """Scheduling a show_id twice replaces the first job."""
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    # First: far in the future
    show_v1 = ScheduledShow(
        show_id="replace-me",
        start_at=_now() + timedelta(seconds=60),
        end_at=_now() + timedelta(seconds=120),
        items=[QueueItem(id="old", uri="file:///old.mp3", duration=60.0)],
    )
    scheduler.schedule(show_v1)

    # Second: starts very soon, long enough not to stop before the assert
    show_v2 = ScheduledShow(
        show_id="replace-me",
        start_at=_now() + timedelta(seconds=DELAY),
        end_at=_now() + timedelta(seconds=DELAY + 60.0),
        items=[QueueItem(id="new", uri="file:///new.mp3", duration=60.0)],
    )
    scheduler.schedule(show_v2)

    # Only one job pending
    assert scheduler.pending_show_ids().count("replace-me") == 1

    time.sleep(DELAY + 0.05)
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()


# ---------------------------------------------------------------------------
# pending_show_ids
# ---------------------------------------------------------------------------

def test_pending_show_ids_reflects_schedule():
    scheduler = PlayoutScheduler(MockPlayoutEngine())
    assert scheduler.pending_show_ids() == []

    scheduler.schedule(_show("a", delay=MARGIN))
    scheduler.schedule(_show("b", delay=MARGIN))
    ids = scheduler.pending_show_ids()
    assert "a" in ids
    assert "b" in ids

    scheduler.cancel_all()
    assert scheduler.pending_show_ids() == []


# ---------------------------------------------------------------------------
# ScheduledShow helpers
# ---------------------------------------------------------------------------

def test_scheduled_show_duration():
    start = _now()
    end = start + timedelta(seconds=10)
    show = ScheduledShow(show_id="dur", start_at=start, end_at=end, items=[])
    assert abs(show.duration - 10.0) < 0.01


def test_scheduled_show_naive_datetimes_accepted():
    """Naive (timezone-unaware) datetimes are normalised to UTC."""
    naive_start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=60)
    naive_end = naive_start + timedelta(seconds=10)
    show = ScheduledShow(show_id="naive", start_at=naive_start, end_at=naive_end, items=[])
    assert show.start_at.tzinfo is not None
    assert show.end_at.tzinfo is not None
