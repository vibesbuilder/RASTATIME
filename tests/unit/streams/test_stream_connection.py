"""
T10.1 — StreamConnection unit tests.

Verifies the StreamConnection state machine, backoff calculator, status
snapshot, and callback dispatch.  No VLC or Icecast required.

Test inventory
--------------
1.  Initial state is IDLE.
2.  transition(CONNECTING) fires callback with correct previous/current states.
3.  transition(ACTIVE) records connected_since timestamp.
4.  transition(IDLE) resets connected_since to None.
5.  transition(DISCONNECTED) clears connected_since.
6.  transition(ERROR) records error_message.
7.  transition(IDLE) resets error_message to None.
8.  No-op transition (same state) does not fire callbacks.
9.  Multiple callbacks are all called on transition.
10. status() returns an OutputStatus snapshot with correct fields.
11. next_backoff() starts at 5 s, doubles each call.
12. next_backoff() caps at 60 s.
13. reconnect_attempt increments each call to next_backoff().
14. Transition to ACTIVE resets backoff and attempt counter.
15. output / output_id properties expose config.
16. repr() includes id and state.
17. Thread safety: concurrent transitions from multiple threads.
"""

import threading
import time

import pytest

from streams.egress import StreamOutput, OutputStateChangedEvent, StreamConnection
from streams._types import StreamProtocol, StreamState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _output(output_id: str = "o1") -> StreamOutput:
    return StreamOutput(
        id=output_id,
        name="Test",
        protocol=StreamProtocol.ICECAST,
        url="ice.local",
        port=8000,
        mount="/live",
        username="source",
        password="pw",
        codec="mp3",
    )


def _conn(output_id: str = "o1") -> StreamConnection:
    return StreamConnection(_output(output_id))


# ---------------------------------------------------------------------------
# 1  Initial state
# ---------------------------------------------------------------------------

def test_initial_state_is_idle():
    assert _conn().state == StreamState.IDLE


# ---------------------------------------------------------------------------
# 2–7  State transitions + callback content
# ---------------------------------------------------------------------------

def test_transition_connecting_fires_callback():
    conn = _conn()
    events: list[OutputStateChangedEvent] = []
    conn.add_state_callback(events.append)

    conn.transition(StreamState.CONNECTING)

    assert len(events) == 1
    assert events[0].previous_state == StreamState.IDLE
    assert events[0].current_state == StreamState.CONNECTING
    assert events[0].output_id == "o1"


def test_transition_active_records_connected_since():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    conn.transition(StreamState.ACTIVE)

    assert conn.status().connected_since is not None


def test_transition_idle_clears_connected_since():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    conn.transition(StreamState.ACTIVE)
    conn.transition(StreamState.IDLE)

    assert conn.status().connected_since is None


def test_transition_disconnected_clears_connected_since():
    conn = _conn()
    conn.transition(StreamState.CONNECTING)
    conn.transition(StreamState.ACTIVE)
    conn.transition(StreamState.DISCONNECTED, error_message="network lost")

    status = conn.status()
    assert status.connected_since is None


def test_transition_error_records_message():
    conn = _conn()
    conn.transition(StreamState.ERROR, error_message="fatal failure")

    assert conn.status().error_message == "fatal failure"


def test_transition_idle_clears_error_message():
    conn = _conn()
    conn.transition(StreamState.ERROR, error_message="fatal failure")
    conn.transition(StreamState.IDLE)

    assert conn.status().error_message is None


# ---------------------------------------------------------------------------
# 8  No-op same-state transition
# ---------------------------------------------------------------------------

def test_same_state_transition_does_not_fire_callback():
    conn = _conn()
    events: list[OutputStateChangedEvent] = []
    conn.add_state_callback(events.append)

    conn.transition(StreamState.IDLE)  # already IDLE

    assert events == []


# ---------------------------------------------------------------------------
# 9  Multiple callbacks
# ---------------------------------------------------------------------------

def test_multiple_callbacks_all_called():
    conn = _conn()
    calls_a: list[int] = []
    calls_b: list[int] = []
    conn.add_state_callback(lambda e: calls_a.append(1))
    conn.add_state_callback(lambda e: calls_b.append(2))

    conn.transition(StreamState.CONNECTING)

    assert calls_a == [1]
    assert calls_b == [2]


# ---------------------------------------------------------------------------
# 10  status() snapshot
# ---------------------------------------------------------------------------

def test_status_returns_output_status_with_correct_fields():
    conn = _conn("out-x")
    conn.transition(StreamState.CONNECTING)

    status = conn.status()

    assert status.output_id == "out-x"
    assert status.state == StreamState.CONNECTING
    assert status.connected_since is None
    assert status.error_message is None


def test_status_active_has_connected_since():
    conn = _conn()
    conn.transition(StreamState.ACTIVE)

    assert conn.status().connected_since is not None


# ---------------------------------------------------------------------------
# 11–13  Reconnect backoff
# ---------------------------------------------------------------------------

def test_next_backoff_starts_at_5():
    conn = _conn()
    assert conn.next_backoff() == 5.0


def test_next_backoff_doubles():
    conn = _conn()
    b1 = conn.next_backoff()
    b2 = conn.next_backoff()
    assert b2 == b1 * 2


def test_next_backoff_caps_at_60():
    conn = _conn()
    # exhaust: 5, 10, 20, 40, 80→60, 60, ...
    for _ in range(10):
        conn.next_backoff()
    assert conn.next_backoff() == 60.0


def test_reconnect_attempt_increments():
    conn = _conn()
    assert conn.reconnect_attempt == 0
    conn.next_backoff()
    assert conn.reconnect_attempt == 1
    conn.next_backoff()
    assert conn.reconnect_attempt == 2


# ---------------------------------------------------------------------------
# 14  ACTIVE resets backoff
# ---------------------------------------------------------------------------

def test_active_resets_backoff_and_attempt():
    conn = _conn()
    conn.next_backoff()
    conn.next_backoff()
    assert conn.reconnect_attempt == 2

    conn.transition(StreamState.ACTIVE)

    assert conn.reconnect_attempt == 0
    # Backoff should be back to base (5.0)
    assert conn.next_backoff() == 5.0


# ---------------------------------------------------------------------------
# 15  Properties
# ---------------------------------------------------------------------------

def test_output_property_returns_config():
    out = _output("p-test")
    conn = StreamConnection(out)
    assert conn.output is out
    assert conn.output_id == "p-test"


# ---------------------------------------------------------------------------
# 16  repr
# ---------------------------------------------------------------------------

def test_repr_contains_id_and_state():
    conn = _conn("my-output")
    r = repr(conn)
    assert "my-output" in r
    assert "idle" in r


# ---------------------------------------------------------------------------
# 17  Thread safety
# ---------------------------------------------------------------------------

def test_concurrent_transitions_do_not_corrupt_state():
    """
    Drive 20 threads through CONNECTING → ACTIVE transitions simultaneously.
    The final state must be ACTIVE (or IDLE if some thread raced to IDLE).
    No exceptions must occur.
    """
    conn = _conn()
    errors: list[Exception] = []

    def _drive():
        try:
            conn.transition(StreamState.CONNECTING)
            conn.transition(StreamState.ACTIVE)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_drive) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Exceptions in threads: {errors}"
    assert conn.state in (StreamState.CONNECTING, StreamState.ACTIVE)
