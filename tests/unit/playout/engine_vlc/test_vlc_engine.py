"""
T5.2 validation — VlcPlayoutEngine file playback.

Verifies that:
1. VlcPlayoutEngine instantiates and satisfies the PlayoutEngine ABC.
2. start() on an empty queue is a no-op (stays STOPPED).
3. start() transitions to PLAYING and fires None->item TrackChangedEvent (V).
4. End-of-file triggers item->None TrackChangedEvent and STOPPED state (V).
5. stop() transitions to STOPPED and fires the final TrackChangedEvent.
6. pause() transitions to PAUSED; resume() returns to PLAYING.
7. load_queue() replaces the queue and stops active playback.
8. append() and clear_queue() behave correctly.
9. get_remaining_duration() returns a positive float while playing.
10. select_output_device() is a safe no-op for unknown device ids.
11. on_error() callback can be registered.
12. Double start() is idempotent.

Timing notes
------------
All tests use short WAV files (WAV_DURATION = 0.5 s) and a generous
MARGIN of 4 s so that they pass reliably even on a loaded CI machine.
Audio output is suppressed via --aout=dummy so no speakers are needed.

All tests require VLC to be installed and are skipped otherwise.
"""

import math
import struct
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import List

import pytest

from playout.engine_interface import PlayoutError, PlayoutState, QueueItem, TrackChangedEvent
from playout.engine_mock import MockPlayoutEngine

# ---------------------------------------------------------------------------
# VLC availability guard
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping VlcPlayoutEngine tests",
)

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

WAV_DURATION = 0.5   # seconds per generated test track
MARGIN = 4.0         # generous wait budget for CI

# VLC args used in all tests (null audio output — no speakers needed)
_VLC_TEST_ARGS = ["--aout=dummy"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_wav(duration: float = WAV_DURATION, freq: float = 440.0) -> Path:
    """
    Generate a temporary WAV file containing a sine-wave tone and return its path.
    The caller is responsible for deleting the file.
    """
    sample_rate = 44100
    n = int(sample_rate * duration)
    samples = [
        int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
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


def _wav_item(path: Path, item_id: str = "t1") -> QueueItem:
    return QueueItem(id=item_id, uri=path.as_uri(), duration=WAV_DURATION)


@pytest.fixture()
def wav(tmp_path):
    """Single temporary WAV file; cleaned up after the test."""
    p = _make_wav()
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture()
def engine():
    """Fresh VlcPlayoutEngine with dummy audio; stopped and closed after test."""
    from playout.engine_vlc import VlcPlayoutEngine
    eng = VlcPlayoutEngine(vlc_args=_VLC_TEST_ARGS)
    yield eng
    try:
        eng.stop()
    except Exception:
        pass
    eng.close()


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

@vlc_required
def test_vlc_engine_instantiates(engine):
    from playout.engine_vlc import VlcPlayoutEngine
    from playout.engine_interface._engine import PlayoutEngine
    assert isinstance(engine, VlcPlayoutEngine)
    assert isinstance(engine, PlayoutEngine)
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None
    assert engine.get_remaining_duration() is None


# ---------------------------------------------------------------------------
# Transport — basic (V criterion)
# ---------------------------------------------------------------------------

@vlc_required
def test_start_transitions_to_playing_and_fires_callback(engine, wav):
    """V: start() fires None->item TrackChangedEvent and moves to PLAYING."""
    item = _wav_item(wav)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item])
    engine.start()

    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == item
    assert len(events) == 1
    assert events[0].previous_item is None
    assert events[0].current_item == item

    engine.stop()


@vlc_required
def test_end_of_file_fires_callback_and_stops(engine, wav):
    """V: when the WAV ends, item->None callback fires and state is STOPPED."""
    item = _wav_item(wav)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item])
    engine.start()

    # Wait past the track duration
    time.sleep(WAV_DURATION + MARGIN)

    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None
    # Event 0: None->item (start); Event 1: item->None (end)
    assert len(events) == 2
    assert events[1].previous_item == item
    assert events[1].current_item is None


@vlc_required
def test_start_empty_queue_is_noop(engine):
    engine.start()
    assert engine.get_state() == PlayoutState.STOPPED


@vlc_required
def test_double_start_is_idempotent(engine, wav):
    item = _wav_item(wav)
    engine.load_queue([item])
    engine.start()
    state_after_first = engine.get_state()
    engine.start()  # second call — must not restart
    assert engine.get_state() == state_after_first
    engine.stop()


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------

@vlc_required
def test_stop_transitions_to_stopped(engine, wav):
    item = _wav_item(wav)
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None
    # start event + stop event
    assert len(events) == 2
    assert events[-1].current_item is None


@vlc_required
def test_stop_from_stopped_is_noop(engine):
    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------

@vlc_required
def test_pause_and_resume(engine, wav):
    item = _wav_item(wav)
    engine.load_queue([item])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    time.sleep(0.05)
    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED

    remaining_paused = engine.get_remaining_duration()
    assert remaining_paused is not None

    # While paused the remaining duration should not decrease
    time.sleep(0.1)
    assert engine.get_remaining_duration() == remaining_paused

    engine.resume()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()


# ---------------------------------------------------------------------------
# Queue management
# ---------------------------------------------------------------------------

@vlc_required
def test_load_queue_replaces_and_stops(engine, wav):
    item = _wav_item(wav)
    engine.load_queue([item])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    p2 = _make_wav()
    try:
        engine.load_queue([_wav_item(p2, "t2")])
        assert engine.get_state() == PlayoutState.STOPPED
        assert engine.get_current_item() is None
    finally:
        p2.unlink(missing_ok=True)


@vlc_required
def test_append_extends_queue(engine, wav):
    item1 = _wav_item(wav, "t1")
    engine.load_queue([item1])
    p2 = _make_wav()
    try:
        item2 = _wav_item(p2, "t2")
        engine.append(item2)
        engine.start()
        assert engine.get_state() == PlayoutState.PLAYING
        engine.stop()
    finally:
        p2.unlink(missing_ok=True)


@vlc_required
def test_clear_queue_keeps_current(engine, wav):
    p2 = _make_wav()
    p3 = _make_wav()
    try:
        items = [_wav_item(wav, "t1"), _wav_item(p2, "t2"), _wav_item(p3, "t3")]
        engine.load_queue(items)
        engine.start()
        assert engine.get_current_item() == items[0]

        engine.clear_queue()
        assert engine.get_current_item() == items[0]
        assert engine.get_state() == PlayoutState.PLAYING
        engine.stop()
    finally:
        p2.unlink(missing_ok=True)
        p3.unlink(missing_ok=True)


@vlc_required
def test_clear_queue_when_stopped(engine, wav):
    items = [_wav_item(wav, "t1")]
    engine.load_queue(items)
    engine.clear_queue()
    assert engine.get_current_item() is None


# ---------------------------------------------------------------------------
# Remaining duration
# ---------------------------------------------------------------------------

@vlc_required
def test_remaining_duration_while_playing(engine, wav):
    engine.load_queue([_wav_item(wav)])
    engine.start()
    time.sleep(0.1)  # let VLC report a valid position

    remaining = engine.get_remaining_duration()
    assert remaining is not None
    assert 0.0 < remaining <= WAV_DURATION

    engine.stop()


@vlc_required
def test_remaining_duration_when_stopped(engine):
    assert engine.get_remaining_duration() is None


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

@vlc_required
def test_select_output_device_is_noop(engine):
    engine.select_output_device("any-unknown-id")  # must not raise


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@vlc_required
def test_multiple_track_change_callbacks(engine, wav):
    calls_a: List[TrackChangedEvent] = []
    calls_b: List[TrackChangedEvent] = []
    engine.on_track_change(calls_a.append)
    engine.on_track_change(calls_b.append)

    engine.load_queue([_wav_item(wav)])
    engine.start()
    time.sleep(WAV_DURATION + MARGIN)

    # Both callbacks receive the same events: start + end
    assert len(calls_a) == len(calls_b) == 2


@vlc_required
def test_on_error_callback_registered(engine):
    errors: List[PlayoutError] = []
    engine.on_error(errors.append)
    # No errors in normal operation — just verify registration
    assert errors == []


@vlc_required
def test_crashing_callback_does_not_propagate(engine, wav):
    """A callback that raises must not crash the engine."""
    def bad(event):
        raise RuntimeError("callback failure")

    engine.on_track_change(bad)
    engine.load_queue([_wav_item(wav)])
    engine.start()
    time.sleep(WAV_DURATION + MARGIN)
    assert engine.get_state() == PlayoutState.STOPPED
