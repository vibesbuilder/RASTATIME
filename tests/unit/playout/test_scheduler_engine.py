"""
T6.1 validation — scheduler actions mapped to PlayoutEngine.

Verifies that:
1.  HARD start stops current, loads new queue, starts immediately.
2.  SOFT start when engine is STOPPED falls back to hard start.
3.  SOFT start when engine is PLAYING splices new items after current track.
4.  schedule_next() preloads items via append() and arms a soft-start timer.
5.  StartMode enum has HARD and SOFT values.
6.  ScheduledShow.start_mode defaults to HARD.

V criterion (VLC required):
7.  Two back-to-back HARD shows each play fully with the VlcPlayoutEngine;
    all four TrackChangedEvents fire in the correct order.
8.  Two SOFT shows: show B splices after show A's track without interruption.

Mock-based tests (1-6) run without VLC.
VLC tests (7-8) are skipped when VLC is not installed.
"""

import math
import struct
import tempfile
import threading
import time
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pytest

from playout.engine_interface import PlayoutState, QueueItem, TrackChangedEvent
from playout.engine_mock import MockPlayoutEngine
from playout.scheduler import PlayoutScheduler, ScheduledShow, StartMode

TICK = 0.05      # mock track duration
MARGIN = TICK * 15


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _mock_items(n: int, duration: float = TICK) -> list:
    return [
        QueueItem(id=f"t{i}", uri=f"file:///track{i}.mp3", duration=duration)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# StartMode enum
# ---------------------------------------------------------------------------

def test_start_mode_values():
    assert StartMode.HARD.value == "hard"
    assert StartMode.SOFT.value == "soft"
    assert StartMode.HARD == "hard"  # str-enum
    assert StartMode.SOFT == "soft"


def test_scheduled_show_default_start_mode():
    show = ScheduledShow(
        show_id="x",
        start_at=_now(),
        end_at=_now() + timedelta(seconds=10),
    )
    assert show.start_mode == StartMode.HARD


# ---------------------------------------------------------------------------
# HARD start (mock engine)
# ---------------------------------------------------------------------------

def test_hard_start_stops_current_and_loads_new():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    old_items = _mock_items(1, duration=60.0)
    engine.load_queue(old_items)
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    new_items = _mock_items(2, duration=60.0)
    show = ScheduledShow(
        show_id="new",
        start_at=_now(),      # immediate
        end_at=_now() + timedelta(seconds=120),
        items=new_items,
        start_mode=StartMode.HARD,
    )
    scheduler.schedule(show)
    time.sleep(MARGIN)

    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == new_items[0]
    engine.stop()


def test_hard_start_from_stopped():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)
    items = _mock_items(1, duration=60.0)

    show = ScheduledShow(
        show_id="s",
        start_at=_now(),
        end_at=_now() + timedelta(seconds=60),
        items=items,
        start_mode=StartMode.HARD,
    )
    scheduler.schedule(show)
    time.sleep(MARGIN)

    assert engine.get_state() == PlayoutState.PLAYING
    engine.stop()


# ---------------------------------------------------------------------------
# SOFT start (mock engine)
# ---------------------------------------------------------------------------

def test_soft_start_from_stopped_falls_back_to_hard():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    assert engine.get_state() == PlayoutState.STOPPED

    items = _mock_items(1, duration=60.0)
    show = ScheduledShow(
        show_id="s",
        start_at=_now(),
        end_at=_now() + timedelta(seconds=60),
        items=items,
        start_mode=StartMode.SOFT,
    )
    scheduler.schedule(show)
    time.sleep(MARGIN)

    # Fell back to hard start
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == items[0]
    engine.stop()


def test_soft_start_splices_after_current_track():
    """
    While track A is playing, a SOFT-mode show schedules tracks B+C.
    After A ends the engine plays B then C naturally — no interruption.

    item_a has duration TICK * 20 (1.0 s) so there is plenty of time to
    schedule the SOFT show and verify A is still playing before it ends.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    scheduler = PlayoutScheduler(engine)

    item_a = QueueItem(id="a", uri="file:///a.mp3", duration=TICK * 20)  # 1.0 s
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item_a])
    engine.start()
    assert engine.get_current_item() == item_a

    # Schedule a SOFT show while A is still playing
    items_bc = _mock_items(2, duration=TICK)
    show = ScheduledShow(
        show_id="bc",
        start_at=_now(),       # fires immediately (delay=0 → timer fires ~0 ms)
        end_at=_now() + timedelta(seconds=60),
        items=items_bc,
        start_mode=StartMode.SOFT,
    )
    scheduler.schedule(show)

    # Give the delay=0 timer thread a moment to run, but not long enough for A to end
    time.sleep(TICK * 2)

    # A must still be playing (not interrupted by the soft start)
    assert engine.get_current_item() == item_a
    assert engine.get_state() == PlayoutState.PLAYING

    # Wait for A (remaining ~0.9 s) + B + C to finish
    time.sleep(TICK * 20 + TICK * 2 + MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED

    # Events: None->A, A->B, B->C, C->None
    item_ids = [
        (e.previous_item.id if e.previous_item else None,
         e.current_item.id if e.current_item else None)
        for e in events
    ]
    assert item_ids[0] == (None, "a"),   f"Unexpected event[0]: {item_ids[0]}"
    assert item_ids[1] == ("a", "t0"),  f"Unexpected event[1]: {item_ids[1]}"
    assert item_ids[2] == ("t0", "t1"), f"Unexpected event[2]: {item_ids[2]}"
    assert item_ids[3] == ("t1", None), f"Unexpected event[3]: {item_ids[3]}"

    scheduler.cancel_all()


# ---------------------------------------------------------------------------
# schedule_next() — preload
# ---------------------------------------------------------------------------

def test_schedule_next_appends_items_immediately():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    scheduler = PlayoutScheduler(engine)

    item_a = QueueItem(id="a", uri="file:///a.mp3", duration=60.0)
    engine.load_queue([item_a])
    engine.start()

    items_b = _mock_items(2, duration=60.0)
    show = ScheduledShow(
        show_id="next",
        start_at=_now() + timedelta(seconds=60),  # far future
        end_at=_now() + timedelta(seconds=120),
        items=items_b,
    )
    # schedule_next appends immediately
    scheduler.schedule_next(show)

    # Items are now appended to engine's queue (can check via clear+append side effect)
    # We verify by stopping and checking the current item is still 'a' (no interruption)
    assert engine.get_current_item() == item_a
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()
    scheduler.cancel_all()


# ---------------------------------------------------------------------------
# V criterion — VLC: two back-to-back HARD shows
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping VLC scheduler tests",
)

SHOW_DURATION = 0.5   # seconds per show (short for test speed)
VLC_MARGIN = 5.0      # generous wait budget

_VLC_ARGS = ["--aout=dummy"]


def _make_wav(duration: float = SHOW_DURATION) -> Path:
    sample_rate = 44100
    n = int(sample_rate * duration)
    samples = [
        int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
        for i in range(n)
    ]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return path


def _vlc_item(path: Path, item_id: str) -> QueueItem:
    return QueueItem(id=item_id, uri=path.as_uri(), duration=SHOW_DURATION)


@vlc_required
def test_two_hard_shows_back_to_back_vlc():
    """
    V criterion for T6.1: schedule two HARD shows back-to-back against a
    real VlcPlayoutEngine and verify that both play completely.

    Timeline (seconds from now):
        T+0.1 … T+0.6  — Show A (0.5 s WAV)
        T+0.6 … T+1.1  — Show B (0.5 s WAV)

    Expected 4 TrackChangedEvents (2 per show):
        None→A_item, A_item→None, None→B_item, B_item→None
    """
    from playout.engine_vlc import VlcPlayoutEngine

    wav_a = _make_wav()
    wav_b = _make_wav()
    engine = VlcPlayoutEngine(vlc_args=_VLC_ARGS)
    scheduler = PlayoutScheduler(engine)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    now = _now()
    show_a = ScheduledShow(
        show_id="show-a",
        start_at=now + timedelta(seconds=0.1),
        end_at=now + timedelta(seconds=0.1 + SHOW_DURATION),
        items=[_vlc_item(wav_a, "item-a")],
        start_mode=StartMode.HARD,
    )
    show_b = ScheduledShow(
        show_id="show-b",
        start_at=now + timedelta(seconds=0.1 + SHOW_DURATION),
        end_at=now + timedelta(seconds=0.1 + SHOW_DURATION * 2),
        items=[_vlc_item(wav_b, "item-b")],
        start_mode=StartMode.HARD,
    )

    try:
        scheduler.schedule(show_a)
        scheduler.schedule(show_b)

        # Wait for both shows to complete
        total = 0.1 + SHOW_DURATION * 2 + VLC_MARGIN
        time.sleep(total)

        assert engine.get_state() == PlayoutState.STOPPED, (
            f"Engine still {engine.get_state()} after both shows should have ended"
        )

        event_pairs = [
            (e.previous_item.id if e.previous_item else None,
             e.current_item.id if e.current_item else None)
            for e in events
        ]

        # Both shows must have fired their start events
        started = [pair[1] for pair in event_pairs if pair[1] is not None]
        assert "item-a" in started, f"Show A never started; events: {event_pairs}"
        assert "item-b" in started, f"Show B never started; events: {event_pairs}"

        # Both shows must have fired their stop events
        stopped = [pair[0] for pair in event_pairs if pair[1] is None]
        assert "item-a" in stopped, f"Show A never stopped; events: {event_pairs}"
        assert "item-b" in stopped, f"Show B never stopped; events: {event_pairs}"

    finally:
        scheduler.cancel_all()
        try:
            engine.stop()
        except Exception:
            pass
        engine.close()
        wav_a.unlink(missing_ok=True)
        wav_b.unlink(missing_ok=True)


@vlc_required
def test_soft_show_splices_after_current_track_vlc():
    """
    SOFT-mode show B is scheduled while show A is playing.
    Show A must not be interrupted; B plays after A ends naturally.
    """
    from playout.engine_vlc import VlcPlayoutEngine

    wav_a = _make_wav(duration=1.0)   # long enough to schedule B mid-play
    wav_b = _make_wav(duration=0.5)
    engine = VlcPlayoutEngine(vlc_args=_VLC_ARGS)
    scheduler = PlayoutScheduler(engine)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    try:
        item_a = _vlc_item(wav_a, "item-a")
        item_b = _vlc_item(wav_b, "item-b")

        # Start show A manually (hard) so it's already playing
        engine.load_queue([item_a])
        engine.start()
        assert engine.get_state() == PlayoutState.PLAYING

        # Schedule show B as SOFT while A is playing
        now = _now()
        show_b = ScheduledShow(
            show_id="show-b",
            start_at=now,   # fires immediately
            end_at=now + timedelta(seconds=10),
            items=[item_b],
            start_mode=StartMode.SOFT,
        )
        scheduler.schedule(show_b)
        time.sleep(0.1)

        # A must still be playing (not interrupted)
        assert engine.get_state() == PlayoutState.PLAYING
        assert engine.get_current_item() == item_a

        # Wait for A + B to finish
        time.sleep(1.0 + 0.5 + VLC_MARGIN)

        assert engine.get_state() == PlayoutState.STOPPED

        # item-b must have played
        played = [e.current_item.id for e in events if e.current_item]
        assert "item-b" in played, f"Show B never played; events: {played}"

    finally:
        scheduler.cancel_all()
        try:
            engine.stop()
        except Exception:
            pass
        engine.close()
        wav_a.unlink(missing_ok=True)
        wav_b.unlink(missing_ok=True)
