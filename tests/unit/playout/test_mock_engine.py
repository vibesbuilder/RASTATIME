"""
T4.1 validation — MockPlayoutEngine.

Verifies that:
1. MockPlayoutEngine satisfies the PlayoutEngine ABC.
2. State transitions are correct across a 3-item queue (V criterion).
3. pause / resume preserve remaining duration.
4. load_queue stops playback and resets state.
5. append and clear_queue behave correctly.
6. select_output_device is a safe no-op.
7. on_error callback can be registered.

Timing notes: tracks use duration=0.05 s (50 ms) so tests complete in <1 s.
A safety margin of 10x the track duration is added to time.sleep() calls.
"""

import time

import pytest

from playout.engine_interface import PlayoutState, QueueItem, TrackChangedEvent
from playout.engine_mock import MockPlayoutEngine

TICK = 0.05        # simulated track duration (seconds)
MARGIN = TICK * 12  # sleep margin — enough for timer thread jitter


def _items(n: int) -> list[QueueItem]:
    return [
        QueueItem(id=f"t{i}", uri=f"file:///track{i}.mp3", duration=TICK)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

def test_mock_engine_instantiates():
    engine = MockPlayoutEngine()
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None
    assert engine.get_remaining_duration() is None


def test_mock_engine_satisfies_abstract_contract():
    """MockPlayoutEngine must be a concrete (non-abstract) subclass."""
    engine = MockPlayoutEngine()
    assert isinstance(engine, MockPlayoutEngine)


# ---------------------------------------------------------------------------
# V criterion: state transitions on a 3-item queue
# ---------------------------------------------------------------------------

def test_state_transitions_3_item_queue():
    engine = MockPlayoutEngine(default_track_duration=TICK)
    items = _items(3)
    events: list[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue(items)
    assert engine.get_state() == PlayoutState.STOPPED

    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == items[0]

    # Wait for the full queue to play through
    time.sleep(MARGIN + TICK * 3)

    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    # Expected 4 events: None→t0, t0→t1, t1→t2, t2→None
    assert len(events) == 4

    assert events[0].previous_item is None
    assert events[0].current_item == items[0]

    assert events[1].previous_item == items[0]
    assert events[1].current_item == items[1]

    assert events[2].previous_item == items[1]
    assert events[2].current_item == items[2]

    assert events[3].previous_item == items[2]
    assert events[3].current_item is None


# ---------------------------------------------------------------------------
# Transport controls
# ---------------------------------------------------------------------------

def test_start_empty_queue_is_noop():
    engine = MockPlayoutEngine()
    engine.start()
    assert engine.get_state() == PlayoutState.STOPPED


def test_stop_fires_track_change_to_none():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    items = _items(2)
    events: list[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue(items)
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    # start fired None→t0; stop fired t0→None
    assert len(events) == 2
    assert events[-1].current_item is None


def test_stop_from_stopped_is_noop():
    engine = MockPlayoutEngine()
    engine.stop()
    assert engine.get_state() == PlayoutState.STOPPED


def test_pause_and_resume():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    engine.load_queue(_items(1))
    engine.start()

    assert engine.get_state() == PlayoutState.PLAYING
    time.sleep(0.02)

    engine.pause()
    assert engine.get_state() == PlayoutState.PAUSED
    remaining_paused = engine.get_remaining_duration()
    assert remaining_paused is not None
    assert remaining_paused < 60.0

    # While paused the remaining duration should not decrease
    time.sleep(0.05)
    assert engine.get_remaining_duration() == remaining_paused

    engine.resume()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.stop()


def test_double_start_is_idempotent():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    engine.load_queue(_items(1))
    engine.start()
    first_item = engine.get_current_item()
    engine.start()  # second call — must not restart
    assert engine.get_current_item() == first_item
    engine.stop()


# ---------------------------------------------------------------------------
# Queue management
# ---------------------------------------------------------------------------

def test_load_queue_replaces_and_stops():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    engine.load_queue(_items(2))
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.load_queue(_items(1))
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None


def test_append_extends_queue():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    items = _items(1)
    engine.load_queue(items)
    extra = QueueItem(id="extra", uri="file:///extra.mp3", duration=60.0)
    engine.append(extra)
    engine.start()
    engine.stop()


def test_clear_queue_keeps_current():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    items = _items(3)
    engine.load_queue(items)
    engine.start()
    assert engine.get_current_item() == items[0]

    engine.clear_queue()
    # Current item preserved; pending items gone
    assert engine.get_current_item() == items[0]
    assert engine.get_state() == PlayoutState.PLAYING
    engine.stop()


def test_clear_queue_when_stopped():
    engine = MockPlayoutEngine()
    engine.load_queue(_items(3))
    engine.clear_queue()
    assert engine.get_current_item() is None


# ---------------------------------------------------------------------------
# Remaining duration
# ---------------------------------------------------------------------------

def test_remaining_duration_while_playing():
    engine = MockPlayoutEngine(default_track_duration=60.0)
    engine.load_queue(_items(1))
    engine.start()

    remaining = engine.get_remaining_duration()
    assert remaining is not None
    assert 0.0 < remaining <= 60.0

    engine.stop()


def test_remaining_duration_when_stopped():
    engine = MockPlayoutEngine()
    assert engine.get_remaining_duration() is None


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def test_select_output_device_is_noop():
    engine = MockPlayoutEngine()
    engine.select_output_device("any-stable-id")  # must not raise


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def test_multiple_track_change_callbacks():
    engine = MockPlayoutEngine(default_track_duration=TICK)
    calls_a: list[TrackChangedEvent] = []
    calls_b: list[TrackChangedEvent] = []
    engine.on_track_change(calls_a.append)
    engine.on_track_change(calls_b.append)

    engine.load_queue(_items(1))
    engine.start()
    time.sleep(MARGIN + TICK)

    assert len(calls_a) == len(calls_b) == 2  # start + end


def test_on_error_callback_registered():
    from playout.engine_interface import PlayoutError
    engine = MockPlayoutEngine()
    errors = []
    engine.on_error(errors.append)
    # No errors fired in normal operation — just verify registration
    assert errors == []


def test_crashing_callback_does_not_propagate():
    """A callback that raises must not crash the engine."""
    engine = MockPlayoutEngine(default_track_duration=TICK)

    def bad_callback(event):
        raise RuntimeError("callback failure")

    engine.on_track_change(bad_callback)
    engine.load_queue(_items(1))
    engine.start()
    time.sleep(MARGIN + TICK)
    # If we get here without crashing, the guard worked
    assert engine.get_state() == PlayoutState.STOPPED
