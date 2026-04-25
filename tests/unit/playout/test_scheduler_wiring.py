"""
T8.3 validation — PlayoutScheduler → QueueManager wiring.

Verifies that:
1.  PlayoutScheduler(engine) creates a QueueManager internally;
    scheduler.queue_manager exposes it.
2.  PlayoutScheduler(engine, queue_manager=qm) uses the supplied QueueManager.
3.  schedule() calls qm.start_show(items, mode) at start_at.
4.  schedule() calls qm.end_show() at end_at.
5.  set_fallback(fb) delegates to qm.set_fallback(fb).
6.  clear_fallback() delegates to qm.clear_fallback().
7.  fallback_is_active() delegates to qm.fallback_is_active().
8.  Empty-items show is skipped (scheduler-level guard added in T8.3).
9.  Past show is silently ignored (end_at <= now).
10. cancel() prevents start_show from being called.
11. V criterion: full end-to-end show cycle — schedule() fires start_show
    then end_show through the real QueueManager and MockPlayoutEngine.
12. V criterion: fallback configured via scheduler fires automatically after
    end_show; engine transitions to PLAYING with the fallback item.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytest

from playout.engine_interface import PlayoutState, QueueItem
from playout.engine_mock import MockPlayoutEngine
from playout.fallback import FallbackQueue
from playout.queue_manager import ContentKind, QueueManager
from playout.scheduler import PlayoutScheduler, ScheduledShow, StartMode

TICK = 0.05
MARGIN = TICK * 15


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _item(item_id: str, duration: float = TICK * 10) -> QueueItem:
    return QueueItem(id=item_id, uri=f"file:///{item_id}.mp3", duration=duration)


def _show(
    show_id: str = "s",
    delay: float = 0.0,
    duration: float = TICK * 4,
    items=None,
    mode: StartMode = StartMode.HARD,
) -> ScheduledShow:
    if items is None:
        items = [_item(f"{show_id}-t0", duration=duration)]
    start = _now() + timedelta(seconds=delay)
    end = start + timedelta(seconds=duration)
    return ScheduledShow(show_id=show_id, start_at=start, end_at=end,
                         items=items, start_mode=mode)


# ---------------------------------------------------------------------------
# Spy QueueManager — records delegated calls
# ---------------------------------------------------------------------------

class _SpyQM(QueueManager):
    """Records calls to start_show, end_show, set_fallback, clear_fallback."""

    def __init__(self, engine) -> None:
        super().__init__(engine)
        self.calls: List[str] = []

    def start_show(self, items, mode):
        self.calls.append(f"start_show({len(items)},{mode.value})")
        super().start_show(items, mode)

    def end_show(self):
        self.calls.append("end_show")
        super().end_show()

    def set_fallback(self, fallback):
        self.calls.append(f"set_fallback({len(fallback)})")
        super().set_fallback(fallback)

    def clear_fallback(self):
        self.calls.append("clear_fallback")
        super().clear_fallback()


# ---------------------------------------------------------------------------
# 1–2  QueueManager injection
# ---------------------------------------------------------------------------

def test_scheduler_creates_queue_manager_internally():
    engine = MockPlayoutEngine()
    sched = PlayoutScheduler(engine)
    assert isinstance(sched.queue_manager, QueueManager)


def test_scheduler_accepts_external_queue_manager():
    engine = MockPlayoutEngine()
    qm = QueueManager(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)
    assert sched.queue_manager is qm


# ---------------------------------------------------------------------------
# 3–4  Timer callbacks delegate to QueueManager
# ---------------------------------------------------------------------------

def test_schedule_calls_start_show_at_start_at():
    """schedule() must call qm.start_show(items, mode) when start_at arrives."""
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    show = _show(delay=TICK, duration=TICK * 100, mode=StartMode.HARD)
    sched.schedule(show)

    time.sleep(TICK * 2 + MARGIN)

    assert any(c.startswith("start_show(1,hard)") for c in qm.calls), (
        f"start_show not called; calls: {qm.calls}"
    )

    engine.stop()
    sched.cancel_all()


def test_schedule_calls_end_show_at_end_at():
    """schedule() must call qm.end_show() when end_at arrives."""
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    # Short show so end_at fires quickly
    show = _show(delay=0.0, duration=TICK * 3, mode=StartMode.HARD)
    sched.schedule(show)

    # Wait for end_at
    time.sleep(TICK * 3 + MARGIN)

    assert "end_show" in qm.calls, f"end_show not called; calls: {qm.calls}"


def test_schedule_passes_correct_items_and_mode():
    """start_show receives the show's items and start_mode."""
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    items = [_item("x"), _item("y"), _item("z")]
    show = ScheduledShow(
        show_id="multi",
        start_at=_now() + timedelta(seconds=TICK),
        end_at=_now() + timedelta(seconds=TICK * 100),
        items=items,
        start_mode=StartMode.SOFT,
    )
    sched.schedule(show)
    time.sleep(TICK * 2 + MARGIN)

    # 3 items, SOFT mode
    assert any(c == "start_show(3,soft)" for c in qm.calls), (
        f"Expected start_show(3,soft); calls: {qm.calls}"
    )

    engine.stop()
    sched.cancel_all()


# ---------------------------------------------------------------------------
# 5–7  Fallback delegation
# ---------------------------------------------------------------------------

def test_set_fallback_delegates_to_queue_manager():
    engine = MockPlayoutEngine()
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    fb = FallbackQueue([_item("f")], loop=True)
    sched.set_fallback(fb)

    assert "set_fallback(1)" in qm.calls


def test_clear_fallback_delegates_to_queue_manager():
    engine = MockPlayoutEngine()
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    sched.clear_fallback()
    assert "clear_fallback" in qm.calls


def test_fallback_is_active_delegates_to_queue_manager():
    engine = MockPlayoutEngine()
    qm = QueueManager(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    # Initially False
    assert sched.fallback_is_active() is False

    # Manually set the flag in QM; scheduler should reflect it
    with qm._lock:
        qm._fallback_active = True
    assert sched.fallback_is_active() is True


# ---------------------------------------------------------------------------
# 8–9  Scheduler-level guards
# ---------------------------------------------------------------------------

def test_empty_items_show_is_skipped():
    """A show with an empty items list must be silently ignored (QUEUE_BEHAVIOR §3.1)."""
    engine = MockPlayoutEngine()
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    show = ScheduledShow(
        show_id="empty",
        start_at=_now() + timedelta(seconds=TICK),
        end_at=_now() + timedelta(seconds=TICK * 10),
        items=[],
    )
    sched.schedule(show)

    time.sleep(TICK * 2 + MARGIN)

    # start_show must not have been called
    assert not any(c.startswith("start_show") for c in qm.calls), (
        f"start_show should not be called for empty show; calls: {qm.calls}"
    )
    # The show must not be pending either
    assert "empty" not in sched.pending_show_ids()


def test_past_show_is_silently_ignored():
    engine = MockPlayoutEngine()
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    show = ScheduledShow(
        show_id="past",
        start_at=_now() - timedelta(seconds=10),
        end_at=_now() - timedelta(seconds=1),
        items=[_item("t")],
    )
    sched.schedule(show)

    time.sleep(MARGIN)
    assert not any(c.startswith("start_show") for c in qm.calls)
    assert "past" not in sched.pending_show_ids()


# ---------------------------------------------------------------------------
# 10  cancel() prevents start_show
# ---------------------------------------------------------------------------

def test_cancel_prevents_start_show():
    engine = MockPlayoutEngine()
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    show = _show(delay=MARGIN * 0.5)
    sched.schedule(show)
    cancelled = sched.cancel(show.show_id)
    assert cancelled is True

    time.sleep(MARGIN)
    assert not any(c.startswith("start_show") for c in qm.calls)


# ---------------------------------------------------------------------------
# 11  V criterion: full show cycle
# ---------------------------------------------------------------------------

def test_full_show_cycle_v_criterion():
    """
    V criterion (T8.3): schedule() fires start_show at start_at and end_show
    at end_at through the real QueueManager + MockPlayoutEngine.

    Timeline:
        T+TICK   — show starts  (engine PLAYING)
        T+TICK*5 — show ends    (engine STOPPED / fallback)
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    show = ScheduledShow(
        show_id="v-show",
        start_at=_now() + timedelta(seconds=TICK),
        end_at=_now() + timedelta(seconds=TICK * 5),
        items=[_item("v-t1", duration=TICK * 100)],
        start_mode=StartMode.HARD,
    )
    sched.schedule(show)

    # Before start_at: engine still stopped
    assert engine.get_state() == PlayoutState.STOPPED

    # After start_at
    time.sleep(TICK * 2)
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item().id == "v-t1"
    assert qm.active_content() == ContentKind.SHOW

    # After end_at
    time.sleep(TICK * 5 + MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED
    assert qm.active_content() == ContentKind.IDLE

    # Both delegation calls must have happened
    assert any(c.startswith("start_show") for c in qm.calls), qm.calls
    assert "end_show" in qm.calls


# ---------------------------------------------------------------------------
# 12  V criterion: fallback fires after show end
# ---------------------------------------------------------------------------

def test_fallback_fires_after_show_end_v_criterion():
    """
    V criterion (T8.3): when a fallback is configured via the scheduler,
    end_show() causes the engine to start playing the fallback item.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = _SpyQM(engine)
    sched = PlayoutScheduler(engine, queue_manager=qm)

    fallback_item = _item("fb-v", duration=TICK * 100)
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    show = ScheduledShow(
        show_id="fb-show",
        start_at=_now() + timedelta(seconds=TICK),
        end_at=_now() + timedelta(seconds=TICK * 4),
        items=[_item("show-t", duration=TICK * 100)],
        start_mode=StartMode.HARD,
    )
    sched.schedule(show)

    # Wait for show to start
    time.sleep(TICK * 2)
    assert engine.get_state() == PlayoutState.PLAYING

    # Wait for show to end + fallback to start
    time.sleep(TICK * 4 + MARGIN)

    # Fallback should have taken over
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if engine.get_state() == PlayoutState.PLAYING:
            break
        time.sleep(0.01)

    assert engine.get_state() == PlayoutState.PLAYING, (
        f"Fallback did not start; engine={engine.get_state()}"
    )
    assert engine.get_current_item().id == "fb-v"
    assert sched.fallback_is_active() is True
    assert qm.active_content() == ContentKind.FALLBACK

    engine.stop()
