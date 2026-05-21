"""
T11.1 — Input source model unit tests.

Verifies StreamSource (config data class) and SourceConnection (runtime
state machine) without any network connections or VLC installation.

Test inventory
--------------
StreamSource model (5):
 1.  Construction with all required fields stores them correctly.
 2.  Optional fields have correct defaults (port, priority, enabled).
 3.  Two StreamSource instances with equal fields compare equal.
 4.  Sources sort by descending priority (higher value = higher priority).
 5.  metadata field is independently initialised per instance (no shared dict).

SourceConnection — initial state (2):
 6.  Initial state is IDLE.
 7.  Initial is_active=False, connected_since=None, reconnect_attempt=0.

SourceConnection — state transitions (8):
 8.  transition(CONNECTING) → state=CONNECTING, connected_since still None.
 9.  transition(ACTIVE) → state=ACTIVE, connected_since set to UTC datetime.
10.  transition(ACTIVE) repeated → no-op (same state, callback NOT fired again).
11.  transition(DISCONNECTED) → connected_since cleared, error_message stored.
12.  transition(IDLE) → state=IDLE, connected_since=None, error_message=None,
     is_active=False, reconnect_attempt reset.
13.  activate() sets is_active=True without changing state.
14.  deactivate() sets is_active=False without changing state.
15.  status() returns SourceStatus snapshot with all fields correct.

SourceConnection — backoff (1):
16.  next_backoff() returns 5.0 first, then 10.0 (exponential doubling).

SourceConnection — callbacks (5):
17.  Callback fired once per transition (3 transitions → 3 calls).
18.  No callback fired on same-state no-op.
19.  Multiple callbacks all invoked on each transition.
20.  Exception in one callback is swallowed; other callbacks still called.
21.  SourceStateChangedEvent carries correct previous_state and current_state.

(21 tests total — one extra added for event shape.)
"""

from __future__ import annotations

import threading
from datetime import timezone
from typing import List

import pytest

from streams._types import StreamProtocol, StreamState
from streams.ingress._connection import SourceConnection
from streams.ingress.interface import SourceStateChangedEvent, SourceStatus, StreamSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(
    source_id: str = "s1",
    priority: int = 0,
    enabled: bool = True,
) -> StreamSource:
    return StreamSource(
        id=source_id,
        name="Test Source",
        protocol=StreamProtocol.ICECAST,
        url="icecast.example.com",
        port=8000,
        mount="/live",
        username="listener",
        password="secret",
        priority=priority,
        enabled=enabled,
    )


def _conn(source_id: str = "s1", priority: int = 0) -> SourceConnection:
    return SourceConnection(_source(source_id, priority))


# ---------------------------------------------------------------------------
# 1–5  StreamSource model
# ---------------------------------------------------------------------------

def test_stream_source_stores_all_fields():
    src = StreamSource(
        id="src-1",
        name="Main Input",
        protocol=StreamProtocol.ICECAST,
        url="ice.local",
        port=9000,
        mount="/show",
        username="dj",
        password="pw",
        priority=10,
        enabled=False,
    )
    assert src.id == "src-1"
    assert src.name == "Main Input"
    assert src.protocol == StreamProtocol.ICECAST
    assert src.url == "ice.local"
    assert src.port == 9000
    assert src.mount == "/show"
    assert src.username == "dj"
    assert src.password == "pw"
    assert src.priority == 10
    assert src.enabled is False


def test_stream_source_defaults():
    src = StreamSource(
        id="s", name="S", protocol=StreamProtocol.ICECAST, url="localhost"
    )
    assert src.port == 8000
    assert src.mount == "/"
    assert src.username == ""
    assert src.password == ""
    assert src.priority == 0
    assert src.enabled is True


def test_stream_source_equality():
    a = _source("s1")
    b = _source("s1")
    assert a == b


def test_stream_source_priority_sort_descending():
    sources = [_source("a", 1), _source("b", 10), _source("c", 5)]
    ranked = sorted(sources, key=lambda s: s.priority, reverse=True)
    assert [s.id for s in ranked] == ["b", "c", "a"]


def test_stream_source_metadata_independent_per_instance():
    a = StreamSource(id="a", name="A", protocol=StreamProtocol.ICECAST, url="x")
    b = StreamSource(id="b", name="B", protocol=StreamProtocol.ICECAST, url="x")
    a.metadata["key"] = "value"
    assert "key" not in b.metadata


# ---------------------------------------------------------------------------
# 6–7  SourceConnection — initial state
# ---------------------------------------------------------------------------

def test_source_connection_initial_state_is_idle():
    conn = _conn()
    assert conn.state == StreamState.IDLE


def test_source_connection_initial_flags():
    conn = _conn()
    assert conn.is_active is False
    assert conn.status().connected_since is None
    assert conn.reconnect_attempt == 0


# ---------------------------------------------------------------------------
# 8–15  SourceConnection — state transitions
# ---------------------------------------------------------------------------

def test_transition_to_connecting():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    assert conn.state == StreamState.CONNECTING
    assert conn.status().connected_since is None


def test_transition_to_active_sets_connected_since():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    conn.transition(StreamState.ACTIVE)
    assert conn.state == StreamState.ACTIVE
    ts = conn.status().connected_since
    assert ts is not None
    assert ts.tzinfo == timezone.utc


def test_transition_same_state_is_noop():
    events: list[SourceStateChangedEvent] = []
    conn = _conn()
    conn.add_state_callback(events.append)
    conn.transition(StreamState.ACTIVE)
    conn.transition(StreamState.ACTIVE)   # second call — no-op
    # Only one event fired (the first IDLE→ACTIVE)
    assert len(events) == 1


def test_transition_to_disconnected_clears_connected_since():
    conn = _conn()
    conn.transition(StreamState.ACTIVE)
    conn.transition(StreamState.DISCONNECTED, error_message="stream dropped")
    s = conn.status()
    assert s.state == StreamState.DISCONNECTED
    assert s.connected_since is None
    assert s.error_message == "stream dropped"


def test_transition_to_idle_resets_all():
    conn = _conn()
    conn.transition(StreamState.ACTIVE)
    conn.activate()
    conn.transition(StreamState.DISCONNECTED, error_message="lost")
    conn.transition(StreamState.IDLE)
    s = conn.status()
    assert s.state == StreamState.IDLE
    assert s.connected_since is None
    assert s.error_message is None
    assert s.is_active is False
    assert conn.reconnect_attempt == 0


def test_activate_sets_is_active_without_changing_state():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    conn.activate()
    assert conn.is_active is True
    assert conn.state == StreamState.CONNECTING   # state unchanged


def test_deactivate_clears_is_active_without_changing_state():
    conn = _conn()
    conn.transition(StreamState.ACTIVE)
    conn.activate()
    conn.deactivate()
    assert conn.is_active is False
    assert conn.state == StreamState.ACTIVE       # state unchanged


def test_status_snapshot_matches_state():
    conn = _conn("src-42")
    conn.transition(StreamState.ACTIVE)
    conn.activate()
    s = conn.status()
    assert isinstance(s, SourceStatus)
    assert s.source_id == "src-42"
    assert s.state == StreamState.ACTIVE
    assert s.is_active is True
    assert s.connected_since is not None


# ---------------------------------------------------------------------------
# 16  Backoff
# ---------------------------------------------------------------------------

def test_next_backoff_doubles_exponentially():
    conn = _conn()
    conn.transition(StreamState.DISCONNECTED)
    b1 = conn.next_backoff()
    b2 = conn.next_backoff()
    assert b1 == 5.0
    assert b2 == 10.0
    assert conn.reconnect_attempt == 2


# ---------------------------------------------------------------------------
# 17–21  Callbacks
# ---------------------------------------------------------------------------

def test_callback_fired_once_per_transition():
    events: list[SourceStateChangedEvent] = []
    conn = _conn()
    conn.add_state_callback(events.append)
    conn.transition(StreamState.CONNECTING)
    conn.transition(StreamState.ACTIVE)
    conn.transition(StreamState.DISCONNECTED)
    assert len(events) == 3


def test_no_callback_on_same_state():
    events: list[SourceStateChangedEvent] = []
    conn = _conn()
    conn.add_state_callback(events.append)
    conn.transition(StreamState.IDLE)   # IDLE → IDLE, no-op
    assert len(events) == 0


def test_multiple_callbacks_all_invoked():
    calls_a: list[int] = []
    calls_b: list[int] = []
    conn = _conn()
    conn.add_state_callback(lambda e: calls_a.append(1))
    conn.add_state_callback(lambda e: calls_b.append(2))
    conn.transition(StreamState.CONNECTING)
    assert calls_a == [1]
    assert calls_b == [2]


def test_exception_in_callback_is_swallowed():
    good_calls: list[int] = []

    def _bad(e: SourceStateChangedEvent) -> None:
        raise RuntimeError("boom")

    conn = _conn()
    conn.add_state_callback(_bad)
    conn.add_state_callback(lambda e: good_calls.append(1))
    conn.transition(StreamState.CONNECTING)   # must not raise
    assert good_calls == [1]


def test_event_carries_correct_previous_and_current_state():
    events: list[SourceStateChangedEvent] = []
    conn = _conn()
    conn.add_state_callback(events.append)
    conn.transition(StreamState.CONNECTING)
    e = events[0]
    assert e.previous_state == StreamState.IDLE
    assert e.current_state == StreamState.CONNECTING
    assert e.source_id == "s1"
