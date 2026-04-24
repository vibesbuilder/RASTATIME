"""
T2.1 validation — PlayoutEngine abstract interface.

Verifies that:
1. PlayoutEngine cannot be instantiated directly.
2. An incomplete subclass cannot be instantiated.
3. A complete subclass can be instantiated and returns correct state.
4. All expected symbols are exported from the public interface.
"""

import pytest

from playout.engine_interface import (
    PlayoutEngine,
    PlayoutError,
    PlayoutState,
    QueueItem,
    TrackChangedEvent,
)


# ---------------------------------------------------------------------------
# Instantiation guards
# ---------------------------------------------------------------------------

def test_abstract_engine_cannot_be_instantiated():
    with pytest.raises(TypeError):
        PlayoutEngine()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    class IncompleteEngine(PlayoutEngine):
        pass  # implements nothing

    with pytest.raises(TypeError):
        IncompleteEngine()


# ---------------------------------------------------------------------------
# Minimal concrete implementation
# ---------------------------------------------------------------------------

class _StubEngine(PlayoutEngine):
    """Minimal concrete engine used only for interface validation."""

    def start(self) -> None: pass
    def stop(self) -> None: pass
    def pause(self) -> None: pass
    def resume(self) -> None: pass
    def load_queue(self, items): pass
    def append(self, item): pass
    def clear_queue(self) -> None: pass
    def get_state(self) -> PlayoutState: return PlayoutState.STOPPED
    def get_current_item(self): return None
    def get_remaining_duration(self): return None
    def on_track_change(self, callback): pass
    def on_error(self, callback): pass
    def select_output_device(self, device_id: str) -> None: pass


def test_complete_subclass_can_be_instantiated():
    engine = _StubEngine()
    assert engine.get_state() == PlayoutState.STOPPED


def test_complete_subclass_returns_none_current_item():
    engine = _StubEngine()
    assert engine.get_current_item() is None


def test_complete_subclass_returns_none_remaining_duration():
    engine = _StubEngine()
    assert engine.get_remaining_duration() is None


# ---------------------------------------------------------------------------
# Type exports
# ---------------------------------------------------------------------------

def test_playout_state_values():
    assert PlayoutState.STOPPED.value == "stopped"
    assert PlayoutState.PLAYING.value == "playing"
    assert PlayoutState.PAUSED.value == "paused"
    assert PlayoutState.ERROR.value == "error"


def test_queue_item_defaults():
    item = QueueItem(id="1", uri="file:///test.mp3")
    assert item.title == ""
    assert item.artist == ""
    assert item.duration is None
    assert item.metadata == {}


def test_queue_item_with_all_fields():
    item = QueueItem(
        id="42",
        uri="file:///music/track.flac",
        title="Test Track",
        artist="Test Artist",
        duration=180.5,
        metadata={"album": "Test Album"},
    )
    assert item.duration == 180.5
    assert item.metadata["album"] == "Test Album"


def test_track_changed_event_fields():
    item_a = QueueItem(id="1", uri="file:///a.mp3")
    item_b = QueueItem(id="2", uri="file:///b.mp3")
    event = TrackChangedEvent(previous_item=item_a, current_item=item_b)
    assert event.previous_item is item_a
    assert event.current_item is item_b
    assert event.timestamp is not None


def test_playout_error_fields():
    err = PlayoutError(code="FILE_NOT_FOUND", message="Track missing")
    assert err.code == "FILE_NOT_FOUND"
    assert err.item is None
