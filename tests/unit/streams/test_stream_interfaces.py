"""
T2.2 validation — StreamEgressManager interface.

Verifies that:
1. The egress ABC cannot be instantiated directly.
2. Incomplete subclasses cannot be instantiated.
3. Complete subclasses can be instantiated and return correct values.
4. All expected symbols are exported from the public interface.
5. Shared types (StreamProtocol, StreamState) have the expected values.

(The ingress interface + its concrete libVLC manager were removed with the
abandoned VLC engine on 2026-05-31; only the live egress status surface
remains.)
"""

import pytest

from streams._types import StreamProtocol, StreamState
from streams.egress import (
    OutputStateChangedEvent,
    OutputStatus,
    StreamEgressManager,
    StreamOutput,
)


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

def test_stream_protocol_values():
    assert StreamProtocol.ICECAST.value == "icecast"
    assert StreamProtocol.SHOUTCAST.value == "shoutcast"


def test_stream_state_values():
    states = {s.value for s in StreamState}
    assert states == {"idle", "connecting", "active", "disconnected", "error"}


# ---------------------------------------------------------------------------
# StreamEgressManager — instantiation guards
# ---------------------------------------------------------------------------

def test_egress_manager_cannot_be_instantiated():
    with pytest.raises(TypeError):
        StreamEgressManager()  # type: ignore[abstract]


def test_incomplete_egress_subclass_cannot_be_instantiated():
    class Incomplete(StreamEgressManager):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# ---------------------------------------------------------------------------
# StreamEgressManager — minimal concrete stub
# ---------------------------------------------------------------------------

class _StubEgressManager(StreamEgressManager):
    def add_output(self, output): pass
    def remove_output(self, output_id): pass
    def list_outputs(self): return []
    def start_output(self, output_id): pass
    def stop_output(self, output_id): pass
    def start_all(self): pass
    def stop_all(self): pass
    def get_output_status(self, output_id):
        return OutputStatus(output_id=output_id, state=StreamState.IDLE)
    def on_output_state_change(self, callback): pass


def test_egress_stub_can_be_instantiated():
    mgr = _StubEgressManager()
    assert mgr.list_outputs() == []


def test_egress_output_status_defaults():
    status = OutputStatus(output_id="out1", state=StreamState.IDLE)
    assert status.listener_count is None
    assert status.connected_since is None
    assert status.error_message is None


def test_stream_output_defaults():
    out = StreamOutput(
        id="o1",
        name="Main Stream",
        protocol=StreamProtocol.ICECAST,
        url="stream.example.com",
    )
    assert out.port == 8000
    assert out.bitrate == 128
    assert out.codec == "mp3"
    assert out.enabled is True


def test_output_state_changed_event_fields():
    event = OutputStateChangedEvent(
        output_id="o1",
        previous_state=StreamState.IDLE,
        current_state=StreamState.ACTIVE,
    )
    assert event.output_id == "o1"
    assert event.current_state == StreamState.ACTIVE
    assert event.timestamp is not None
