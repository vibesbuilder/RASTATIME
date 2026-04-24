"""
T6.2 validation — fallback playout entry.

Verifies that:
1.  FallbackQueue stores items and exposes them correctly.
2.  FallbackQueue rejects empty item lists.
3.  set_fallback() / clear_fallback() configure the scheduler.
4.  fallback_is_active() reflects the fallback state.
5.  After a scheduled show ends, fallback starts automatically (V criterion).
6.  While fallback is playing, a HARD-mode show interrupts it cleanly.
7.  Looping fallback restarts after its last item plays.
8.  Non-looping fallback plays once and stops.
9.  Fallback does NOT start if clear_fallback() was called first.
10. set_fallback() with VlcPlayoutEngine: fallback starts after show ends (V/VLC).

Mock-based tests (1-9) run without VLC.
VLC test (10) is skipped when VLC is not installed.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from playout.engine_interface import PlayoutState, QueueItem, TrackChangedEvent
from playout.engine_mock import MockPlayoutEngine
from playout.fallback import FallbackQueue
from playout.scheduler import PlayoutScheduler, ScheduledShow, StartMode

TICK = 0.05
MARGIN = TICK * 15  # 0.75 s


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _item(item_id: str, duration: float = TICK) -> QueueItem:
    return QueueItem(id=item_id, uri=f"file:///{item_id}.mp3", duration=duration)


def _show(
    show_id: str = "show-1",
    delay: float = 0.0,
    duration: float = TICK * 4,
    items=None,
) -> ScheduledShow:
    if items is None:
        items = [_item(f"{show_id}-t0", duration=duration)]
    start = _now() + timedelta(seconds=delay)
    end = start + timedelta(seconds=duration)
    return ScheduledShow(show_id=show_id, start_at=start, end_at=end, items=items)


# ---------------------------------------------------------------------------
# FallbackQueue unit tests
# ---------------------------------------------------------------------------

def test_fallback_queue_stores_items():
    items = [_item("a"), _item("b")]
    fb = FallbackQueue(items, loop=True)
    assert len(fb) == 2
    assert fb.items == items
    assert fb.loop is True
    assert not fb.is_empty()


def test_fallback_queue_non_looping():
    fb = FallbackQueue([_item("x")], loop=False)
    assert fb.loop is False


def test_fallback_queue_rejects_empty():
    with pytest.raises(ValueError, match="at least one item"):
        FallbackQueue([])


def test_fallback_queue_items_is_a_copy():
    items = [_item("a")]
    fb = FallbackQueue(items)
    fb.items.append(_item("b"))  # mutate the copy
    assert len(fb) == 1          # original unchanged


# ---------------------------------------------------------------------------
# Scheduler fallback configuration
# ---------------------------------------------------------------------------

def test_set_fallback_configures_scheduler():
    engine = MockPlayoutEngine()
    sched = PlayoutScheduler(engine)
    assert not sched.fallback_is_active()

    fb = FallbackQueue([_item("f")])
    sched.set_fallback(fb)
    assert not sched.fallback_is_active()  # not yet playing


def test_clear_fallback_removes_config():
    engine = MockPlayoutEngine()
    sched = PlayoutScheduler(engine)
    sched.set_fallback(FallbackQueue([_item("f")]))
    sched.clear_fallback()
    assert not sched.fallback_is_active()


# ---------------------------------------------------------------------------
# V criterion: fallback starts after scheduled show ends (mock engine)
# ---------------------------------------------------------------------------

def test_fallback_starts_after_show_ends():
    """
    V criterion (mock): after a scheduled show's end_at is reached,
    the fallback queue begins playing.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)

    # duration >> MARGIN so the fallback is still PLAYING when we assert
    fallback_item = _item("fallback", duration=TICK * 40)
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    show = _show(delay=0.0, duration=TICK * 2)
    sched.schedule(show)

    # Wait for: show duration + fallback start latency (well within fallback duration)
    time.sleep(TICK * 2 + MARGIN)

    assert engine.get_state() == PlayoutState.PLAYING, (
        f"Expected PLAYING (fallback running), got {engine.get_state()}"
    )
    assert engine.get_current_item() == fallback_item
    assert sched.fallback_is_active()

    engine.stop()
    sched.cancel_all()


def test_fallback_active_flag_is_true_while_playing():
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)
    fallback_item = _item("f", duration=TICK * 20)
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    show = _show(delay=0.0, duration=TICK * 2)
    sched.schedule(show)

    # Wait for show to end and fallback to start
    time.sleep(TICK * 2 + MARGIN)
    assert sched.fallback_is_active()

    engine.stop()
    sched.cancel_all()


# ---------------------------------------------------------------------------
# Show interrupts fallback
# ---------------------------------------------------------------------------

def test_hard_show_interrupts_fallback():
    """
    A HARD-mode show started while fallback is playing must stop the
    fallback and play the show's items.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)

    fallback_item = _item("fallback", duration=TICK * 30)
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    # First show ends quickly → fallback starts
    show1 = _show("show-1", delay=0.0, duration=TICK * 2)
    sched.schedule(show1)

    # Wait for fallback to start
    time.sleep(TICK * 2 + MARGIN)
    assert sched.fallback_is_active()
    assert engine.get_current_item() == fallback_item

    # Schedule a second show — hard start interrupts fallback.
    # end_at must be >> MARGIN so show2's stop-timer doesn't fire before we assert.
    show2_item = _item("show-2-track", duration=TICK * 60)
    show2 = ScheduledShow(
        show_id="show-2",
        start_at=_now(),
        end_at=_now() + timedelta(seconds=TICK * 60),
        items=[show2_item],
        start_mode=StartMode.HARD,
    )
    sched.schedule(show2)
    time.sleep(MARGIN)

    assert engine.get_current_item() == show2_item
    assert not sched.fallback_is_active()

    engine.stop()
    sched.cancel_all()


# ---------------------------------------------------------------------------
# Looping fallback
# ---------------------------------------------------------------------------

def test_looping_fallback_restarts():
    """
    With loop=True the fallback must restart after the last item finishes.
    We measure two complete plays of the fallback item.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)

    fallback_item = _item("f", duration=TICK * 2)
    sched.set_fallback(FallbackQueue([fallback_item], loop=True))

    # Trigger fallback directly via a show that ends immediately
    show = _show(delay=0.0, duration=TICK)
    sched.schedule(show)

    # Wait for: show + 2 full fallback loops + margin
    time.sleep(TICK + TICK * 4 + MARGIN * 3)

    # Engine should still be PLAYING (looping fallback)
    assert engine.get_state() == PlayoutState.PLAYING
    assert sched.fallback_is_active()

    engine.stop()
    sched.cancel_all()


# ---------------------------------------------------------------------------
# Non-looping fallback
# ---------------------------------------------------------------------------

def test_non_looping_fallback_plays_once():
    """
    With loop=False the fallback plays through once, then the engine stops.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)

    fallback_item = _item("f", duration=TICK * 2)
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    show = _show(delay=0.0, duration=TICK)
    sched.schedule(show)

    # Wait for: show + fallback + margin
    time.sleep(TICK + TICK * 2 + MARGIN * 2)

    assert engine.get_state() == PlayoutState.STOPPED

    sched.cancel_all()


# ---------------------------------------------------------------------------
# clear_fallback prevents fallback from starting
# ---------------------------------------------------------------------------

def test_no_fallback_after_clear():
    """After clear_fallback(), nothing plays when the show ends."""
    engine = MockPlayoutEngine(default_track_duration=TICK)
    sched = PlayoutScheduler(engine)

    sched.set_fallback(FallbackQueue([_item("f", duration=TICK * 10)], loop=False))
    sched.clear_fallback()

    show = _show(delay=0.0, duration=TICK)
    sched.schedule(show)

    time.sleep(TICK + MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED
    assert not sched.fallback_is_active()


# ---------------------------------------------------------------------------
# V criterion (VLC) — fallback after real show
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping VLC fallback test",
)


@vlc_required
def test_fallback_starts_after_show_ends_vlc():
    """
    V criterion (VLC): smoke run — a short VLC show plays, then fallback starts.
    """
    import math
    import struct
    import tempfile
    import wave
    from pathlib import Path
    from playout.engine_vlc import VlcPlayoutEngine

    def _wav(duration: float = 0.4) -> Path:
        sr, n = 44100, int(44100 * duration)
        smp = [int(32767 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(n)]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            p = Path(f.name)
        with wave.open(str(p), "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{n}h", *smp))
        return p

    show_wav = _wav(0.4)
    # duration >> wait-time (3.5 s) so fallback is still PLAYING at the assert
    fallback_wav = _wav(6.0)

    engine = VlcPlayoutEngine(vlc_args=["--aout=dummy"])
    sched = PlayoutScheduler(engine)

    fallback_item = QueueItem(
        id="vlc-fallback", uri=fallback_wav.as_uri(), duration=6.0
    )
    sched.set_fallback(FallbackQueue([fallback_item], loop=False))

    now = _now()
    show = ScheduledShow(
        show_id="vlc-show",
        start_at=now + timedelta(seconds=0.1),
        end_at=now + timedelta(seconds=0.1 + 0.4),
        items=[QueueItem(id="vlc-show-t", uri=show_wav.as_uri(), duration=0.4)],
        start_mode=StartMode.HARD,
    )

    try:
        sched.schedule(show)

        # Wait for show + fallback start
        time.sleep(0.1 + 0.4 + 3.0)

        assert engine.get_state() == PlayoutState.PLAYING, (
            f"Expected PLAYING (fallback), got {engine.get_state()}"
        )
        assert engine.get_current_item() == fallback_item
        assert sched.fallback_is_active()

    finally:
        sched.cancel_all()
        try:
            engine.stop()
        except Exception:
            pass
        engine.close()
        show_wav.unlink(missing_ok=True)
        fallback_wav.unlink(missing_ok=True)
