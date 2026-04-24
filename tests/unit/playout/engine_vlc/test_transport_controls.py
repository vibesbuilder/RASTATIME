"""
T5.4 validation — VlcPlayoutEngine transport controls (pause/stop/resume).

Verifies that:
1.  Full state-machine cycle: STOPPED→PLAYING→PAUSED→PLAYING→STOPPED (V).
2.  pause() freezes the playback position (remaining duration does not decrease).
3.  resume() continues from the frozen position.
4.  stop() from PLAYING transitions to STOPPED and fires callback.
5.  stop() from PAUSED transitions to STOPPED and fires callback.
6.  stop() from STOPPED is a no-op (no extra callbacks).
7.  pause() from PAUSED is idempotent (state stays PAUSED, no crash).
8.  pause() from STOPPED is a no-op.
9.  resume() from PLAYING is a no-op.
10. resume() from STOPPED is a no-op.
11. start() after stop() restarts from the first queue item.
12. Double stop() is idempotent.

All tests require VLC to be installed and are skipped otherwise.
"""

import math
import struct
import tempfile
import time
import wave
from pathlib import Path
from typing import List

import pytest

from playout.engine_interface import PlayoutState, QueueItem, TrackChangedEvent

TRACK_DURATION = 2.0   # long enough to pause/resume mid-play without racing
MARGIN = 0.3           # small overhead for state transitions
_VLC_TEST_ARGS = ["--aout=dummy"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping transport control tests",
)


def _make_wav(duration: float = TRACK_DURATION) -> Path:
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


def _item(path: Path, item_id: str = "t1") -> QueueItem:
    return QueueItem(id=item_id, uri=path.as_uri(), duration=TRACK_DURATION)


@pytest.fixture()
def engine():
    from playout.engine_vlc import VlcPlayoutEngine
    eng = VlcPlayoutEngine(vlc_args=_VLC_TEST_ARGS)
    yield eng
    try:
        eng.stop()
    except Exception:
        pass
    eng.close()


@pytest.fixture()
def wav():
    p = _make_wav()
    yield p
    p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# V criterion: full state-machine cycle
# ---------------------------------------------------------------------------

@vlc_required
def test_full_state_machine_cycle(engine, wav):
    """
    V criterion for T5.4: exercise the complete transport state machine.

    STOPPED → start() → PLAYING → pause() → PAUSED
    → resume() → PLAYING → stop() → STOPPED
    """
    item = _item(wav)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    # Initial state
    assert engine.get_state() == PlayoutState.STOPPED

    # STOPPED → PLAYING
    engine.load_queue([item])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == item

    time.sleep(MARGIN)

    # PLAYING → PAUSED
    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED
    assert engine.get_current_item() == item   # item still reported while paused

    time.sleep(MARGIN)

    # PAUSED → PLAYING
    engine.resume()
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == item

    time.sleep(MARGIN)

    # PLAYING → STOPPED
    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    # start() fired None→item; stop() fired item→None
    assert len(events) == 2
    assert events[0].previous_item is None
    assert events[0].current_item == item
    assert events[1].previous_item == item
    assert events[1].current_item is None


# ---------------------------------------------------------------------------
# pause() behaviour
# ---------------------------------------------------------------------------

@vlc_required
def test_pause_freezes_remaining_duration(engine, wav):
    """Remaining duration must not decrease while paused."""
    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(0.2)   # let VLC report a real position

    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED

    r1 = engine.get_remaining_duration()
    assert r1 is not None

    time.sleep(0.3)   # wait while paused

    r2 = engine.get_remaining_duration()
    assert r2 is not None
    # Position must not have advanced (allow 1 ms tolerance for rounding)
    assert abs(r2 - r1) < 0.001, f"remaining changed while paused: {r1:.3f} → {r2:.3f}"

    engine.stop()


@vlc_required
def test_pause_from_paused_is_idempotent(engine, wav):
    """Calling pause() twice must not resume (state stays PAUSED)."""
    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(MARGIN)

    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED

    engine.pause()   # second call — must not toggle back to PLAYING
    assert engine.get_state() == PlayoutState.PAUSED

    engine.stop()


@vlc_required
def test_pause_from_stopped_is_noop(engine):
    """pause() while STOPPED must leave state unchanged."""
    assert engine.get_state() == PlayoutState.STOPPED
    engine.pause()
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# resume() behaviour
# ---------------------------------------------------------------------------

@vlc_required
def test_resume_continues_from_paused_position(engine, wav):
    """After resume(), the track continues from where it was paused."""
    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(0.4)   # play a bit

    engine.pause()
    paused_remaining = engine.get_remaining_duration()
    assert paused_remaining is not None
    time.sleep(0.3)   # stay paused

    engine.resume()
    assert engine.get_state() == PlayoutState.PLAYING
    time.sleep(0.1)

    resumed_remaining = engine.get_remaining_duration()
    assert resumed_remaining is not None
    # After 0.1 s of resumed playback, remaining should be less than at pause
    assert resumed_remaining < paused_remaining

    engine.stop()


@vlc_required
def test_resume_from_playing_is_noop(engine, wav):
    """resume() while already PLAYING must not crash or change state."""
    engine.load_queue([_item(wav)])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.resume()  # must be a no-op
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()


@vlc_required
def test_resume_from_stopped_is_noop(engine):
    """resume() while STOPPED must leave state unchanged."""
    assert engine.get_state() == PlayoutState.STOPPED
    engine.resume()
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# stop() behaviour
# ---------------------------------------------------------------------------

@vlc_required
def test_stop_from_paused_transitions_to_stopped(engine, wav):
    """stop() while PAUSED must transition to STOPPED and fire callback."""
    item = _item(wav)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item])
    engine.start()
    time.sleep(MARGIN)
    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED

    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    # events: start → stop  (2 total)
    assert len(events) == 2
    assert events[-1].current_item is None


@vlc_required
def test_stop_from_stopped_is_noop(engine):
    """stop() while already STOPPED must not fire any callbacks."""
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED
    assert events == []


@vlc_required
def test_double_stop_is_idempotent(engine, wav):
    """Calling stop() twice must not raise or fire extra callbacks."""
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(MARGIN)

    engine.stop()
    engine.stop()   # second call — must be a no-op

    assert engine.get_state() == PlayoutState.STOPPED
    # Only one stop event
    stop_events = [e for e in events if e.current_item is None]
    assert len(stop_events) == 1


# ---------------------------------------------------------------------------
# Restart after stop
# ---------------------------------------------------------------------------

@vlc_required
def test_start_after_stop_restarts_from_item_zero(engine, wav):
    """After stop(), a fresh start() replays from the first queue item."""
    wav2 = _make_wav()
    try:
        items = [_item(wav, "first"), _item(wav2, "second")]
        events: List[TrackChangedEvent] = []
        engine.on_track_change(events.append)

        engine.load_queue(items)

        # First play
        engine.start()
        assert engine.get_current_item() == items[0]
        time.sleep(MARGIN)
        engine.stop()

        # Second play — must restart from item[0], not item[1]
        engine.start()
        assert engine.get_state() == PlayoutState.PLAYING
        assert engine.get_current_item() == items[0]

        engine.stop()
    finally:
        wav2.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Remaining duration across states
# ---------------------------------------------------------------------------

@vlc_required
def test_remaining_duration_is_none_when_stopped(engine):
    assert engine.get_remaining_duration() is None


@vlc_required
def test_remaining_duration_is_none_when_paused_after_stop(engine, wav):
    """Once stopped, remaining duration returns to None."""
    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(0.2)
    engine.pause()
    engine.stop()
    assert engine.get_remaining_duration() is None


@vlc_required
def test_remaining_duration_decreases_while_playing(engine, wav):
    """Remaining duration must decrease over time during playback."""
    engine.load_queue([_item(wav)])
    engine.start()
    time.sleep(0.2)   # let VLC report position

    r1 = engine.get_remaining_duration()
    time.sleep(0.3)
    r2 = engine.get_remaining_duration()

    assert r1 is not None and r2 is not None
    assert r2 < r1, f"remaining did not decrease: {r1:.3f} → {r2:.3f}"

    engine.stop()
