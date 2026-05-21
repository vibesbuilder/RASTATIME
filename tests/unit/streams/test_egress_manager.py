"""
T10.1 — LibVlcEgressManager unit tests.

Tests the concrete StreamEgressManager implementation using lightweight spy
objects.  No VLC installation or real Icecast server required.

Test inventory
--------------
Registration (4):
 1.  add_output() + list_outputs() returns the output.
 2.  remove_output() removes from list and stops active connection.
 3.  remove_output() on unknown id is a no-op (no exception).
 4.  list_outputs() returns all registered outputs regardless of state.

Lifecycle (8):
 5.  start_output() on unknown id raises ValueError.
 6.  stop_output() on unknown id raises ValueError.
 7.  start_output() calls engine.set_sout_chain() with a non-None chain.
 8.  stop_output() after start calls set_sout_chain(None) (no active outputs).
 9.  start_all() starts all enabled outputs.
10.  start_all() skips disabled outputs.
11.  stop_all() transitions all connections to IDLE and clears sout.
12.  stop_all() cancels the watchdog.

Status (3):
13.  get_output_status() for registered-not-started output returns IDLE.
14.  get_output_status() for started output returns CONNECTING/ACTIVE.
15.  get_output_status() for unknown id raises ValueError.

Callbacks (3):
16.  on_output_state_change() fires when connection transitions.
17.  Multiple state callbacks are all invoked.
18.  Exceptions in callbacks are swallowed (no propagation).

Watchdog / reconnect (4):
19.  Healthy watchdog tick keeps output in ACTIVE state.
20.  Unhealthy watchdog tick transitions output to DISCONNECTED.
21.  Unhealthy watchdog schedules reconnect (start_output called again).
22.  cancel_watchdog via stop_all prevents further ticks.

Metadata (2):
23.  Track-change event triggers push() on all active metadata pushers.
24.  Track-change with None current_item triggers push_idle().

SoutBuilder integration (2):
25.  Unsupported codec in output → start_output does not crash (logs error).
26.  Two outputs → duplicate{} chain sent to engine.
"""

import threading
import time
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from streams._types import StreamProtocol, StreamState
from streams.egress import (
    LibVlcEgressManager,
    OutputStateChangedEvent,
    StreamOutput,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _SpyEngine:
    """Minimal engine double that records set_sout_chain and reload_sout calls."""

    def __init__(self) -> None:
        self.sout_calls: list[Optional[str]] = []
        self.reload_count: int = 0
        self._track_change_cbs = []

    def set_sout_chain(self, chain: Optional[str]) -> None:
        self.sout_calls.append(chain)

    def reload_sout(self) -> None:
        self.reload_count += 1

    def on_track_change(self, callback) -> None:
        self._track_change_cbs.append(callback)

    def fire_track_change(self, current_item=None, previous_item=None):
        """Helper: simulate a TrackChangedEvent."""
        class _Ev:
            pass
        ev = _Ev()
        ev.current_item = current_item
        ev.previous_item = previous_item
        for cb in self._track_change_cbs:
            cb(ev)


class _SpyPusher:
    """Records metadata push calls."""

    def __init__(self):
        self.pushed: list[tuple[str, str]] = []
        self.idle_count: int = 0

    def push(self, title: str, artist: str = "") -> bool:
        self.pushed.append((title, artist))
        return True

    def push_idle(self) -> bool:
        self.idle_count += 1
        return True


def _output(
    output_id: str = "o1",
    codec: str = "mp3",
    enabled: bool = True,
) -> StreamOutput:
    return StreamOutput(
        id=output_id,
        name="Test Output",
        protocol=StreamProtocol.ICECAST,
        url="ice.local",
        port=8000,
        mount="/live",
        username="source",
        password="hackme",
        bitrate=128,
        codec=codec,
        enabled=enabled,
    )


def _manager(
    engine: Optional[_SpyEngine] = None,
    health_checker=None,
    watchdog_interval: float = 9999.0,  # effectively disabled in unit tests
) -> tuple[LibVlcEgressManager, _SpyEngine]:
    """Return (manager, engine) with a fast-disabled watchdog."""
    eng = engine or _SpyEngine()
    hc = health_checker if health_checker is not None else (lambda o: True)
    mgr = LibVlcEgressManager(
        eng, watchdog_interval=watchdog_interval, health_checker=hc
    )
    return mgr, eng


# ---------------------------------------------------------------------------
# 1–4  Registration
# ---------------------------------------------------------------------------

def test_add_output_then_list():
    mgr, _ = _manager()
    out = _output()
    mgr.add_output(out)
    assert out in mgr.list_outputs()


def test_remove_output_removes_from_list():
    mgr, _ = _manager()
    out = _output()
    mgr.add_output(out)
    mgr.remove_output("o1")
    assert out not in mgr.list_outputs()


def test_remove_output_unknown_is_noop():
    mgr, _ = _manager()
    mgr.remove_output("nonexistent")  # must not raise


def test_list_outputs_all_regardless_of_state():
    mgr, _ = _manager()
    o1 = _output("o1")
    o2 = _output("o2")
    mgr.add_output(o1)
    mgr.add_output(o2)
    assert len(mgr.list_outputs()) == 2


# ---------------------------------------------------------------------------
# 5–12  Lifecycle
# ---------------------------------------------------------------------------

def test_start_output_unknown_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError, match="Unknown output"):
        mgr.start_output("ghost")


def test_stop_output_unknown_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError, match="Unknown output"):
        mgr.stop_output("ghost")


def test_start_output_calls_set_sout_chain():
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")

    # A non-None sout chain must have been set
    non_none = [c for c in eng.sout_calls if c is not None]
    assert non_none, f"Expected set_sout_chain with a chain; calls: {eng.sout_calls}"


def test_start_output_calls_reload_sout():
    """start_output() calls reload_sout() so streaming begins immediately."""
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")
    assert eng.reload_count >= 1, (
        f"Expected reload_sout to be called; reload_count={eng.reload_count}"
    )


def test_stop_output_clears_sout_chain():
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")
    eng.sout_calls.clear()

    mgr.stop_output("o1")

    assert None in eng.sout_calls, (
        f"Expected set_sout_chain(None) after stop; calls: {eng.sout_calls}"
    )


def test_start_all_starts_enabled_outputs():
    mgr, eng = _manager()
    mgr.add_output(_output("o1"))
    mgr.add_output(_output("o2"))
    mgr.start_all()

    # Both should have registered connections → sout chain built twice (min)
    non_none = [c for c in eng.sout_calls if c is not None]
    assert len(non_none) >= 2


def test_start_all_skips_disabled():
    mgr, eng = _manager()
    mgr.add_output(_output("o1", enabled=True))
    mgr.add_output(_output("o2", enabled=False))
    mgr.start_all()

    # Only o1 should be started; o2 disabled
    # Verify by checking that the sout chain references only /live (same mount
    # for both in our fixture, so count how many start-trigger calls happened)
    non_none = [c for c in eng.sout_calls if c is not None]
    assert len(non_none) == 1, (
        f"Expected 1 start (disabled skipped); calls: {non_none}"
    )


def test_stop_all_clears_sout():
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")
    eng.sout_calls.clear()

    mgr.stop_all()

    assert eng.sout_calls[-1] is None, (
        f"Expected final sout_calls entry to be None; calls: {eng.sout_calls}"
    )


def test_stop_all_removes_all_connections():
    mgr, _ = _manager()
    mgr.add_output(_output("o1"))
    mgr.add_output(_output("o2"))
    mgr.start_all()
    mgr.stop_all()

    for oid in ("o1", "o2"):
        status = mgr.get_output_status(oid)
        assert status.state == StreamState.IDLE


# ---------------------------------------------------------------------------
# 13–15  Status
# ---------------------------------------------------------------------------

def test_status_registered_not_started_is_idle():
    mgr, _ = _manager()
    mgr.add_output(_output())
    status = mgr.get_output_status("o1")
    assert status.state == StreamState.IDLE


def test_status_after_start_is_connecting_or_higher():
    mgr, _ = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")
    status = mgr.get_output_status("o1")
    assert status.state in (StreamState.CONNECTING, StreamState.ACTIVE)


def test_status_unknown_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError):
        mgr.get_output_status("nope")


# ---------------------------------------------------------------------------
# 16–18  Callbacks
# ---------------------------------------------------------------------------

def test_state_change_callback_fires_on_start():
    mgr, _ = _manager()
    events: list[OutputStateChangedEvent] = []
    mgr.on_output_state_change(events.append)
    mgr.add_output(_output())
    mgr.start_output("o1")

    assert any(e.output_id == "o1" for e in events)


def test_multiple_state_callbacks_all_invoked():
    mgr, _ = _manager()
    calls_a: list[int] = []
    calls_b: list[int] = []
    mgr.on_output_state_change(lambda e: calls_a.append(1))
    mgr.on_output_state_change(lambda e: calls_b.append(2))

    mgr.add_output(_output())
    mgr.start_output("o1")

    assert calls_a
    assert calls_b


def test_exception_in_state_callback_is_swallowed():
    mgr, _ = _manager()

    def _bad_cb(e):
        raise RuntimeError("boom")

    mgr.on_output_state_change(_bad_cb)
    mgr.add_output(_output())
    mgr.start_output("o1")  # must not raise


# ---------------------------------------------------------------------------
# 19–22  Watchdog / reconnect
# ---------------------------------------------------------------------------

def test_healthy_watchdog_tick_keeps_active_state():
    mgr, _ = _manager(health_checker=lambda o: True, watchdog_interval=0.05)
    mgr.add_output(_output())
    mgr.start_output("o1")
    time.sleep(0.2)

    status = mgr.get_output_status("o1")
    assert status.state == StreamState.ACTIVE


def test_unhealthy_watchdog_transitions_to_disconnected():
    """A health checker that always returns False causes DISCONNECTED transition."""
    events: list[OutputStateChangedEvent] = []
    mgr, _ = _manager(health_checker=lambda o: False, watchdog_interval=0.05)
    mgr.on_output_state_change(events.append)
    mgr.add_output(_output())
    mgr.start_output("o1")
    time.sleep(0.3)

    disconnected = [e for e in events if e.current_state == StreamState.DISCONNECTED]
    assert disconnected, f"Expected DISCONNECTED event; events: {events}"


def test_unhealthy_watchdog_schedules_reconnect():
    """
    After a watchdog tick with a failing health check, _reconnect_output
    should be scheduled.  We call _on_watchdog() directly (bypassing the
    timer) and patch _reconnect_output to capture the call synchronously.
    """
    reconnect_calls: list[str] = []

    mgr, eng = _manager(health_checker=lambda o: False, watchdog_interval=9999.0)
    mgr.add_output(_output())
    mgr.start_output("o1")

    # Patch _reconnect_output before manually firing the watchdog logic
    # (the timer-based reconnect has a 5 s backoff; we test the scheduling
    #  by intercepting the threading.Timer constructor instead)
    scheduled_args: list = []

    original_timer = threading.Timer

    def _capturing_timer(interval, func, args=(), kwargs={}):
        # Capture and immediately call if this is a reconnect timer (< 60 s)
        if interval <= 60.0 and func == mgr._reconnect_output:
            scheduled_args.append(args[0] if args else None)
            # Don't actually start the timer — just record it
            t = original_timer(9999.0, lambda: None)
            return t
        return original_timer(interval, func, args=args, kwargs=kwargs)

    with patch("streams.egress._vlc_manager.threading.Timer", side_effect=_capturing_timer):
        mgr._on_watchdog()

    assert scheduled_args, (
        "Expected _reconnect_output to be scheduled after unhealthy watchdog tick"
    )


def test_stop_all_cancels_watchdog():
    """After stop_all, no further watchdog tick should fire."""
    tick_count = [0]

    def _counting_health(o):
        tick_count[0] += 1
        return True

    mgr, _ = _manager(health_checker=_counting_health, watchdog_interval=0.05)
    mgr.add_output(_output())
    mgr.start_output("o1")
    time.sleep(0.15)
    count_before = tick_count[0]

    mgr.stop_all()
    time.sleep(0.15)
    count_after = tick_count[0]

    assert count_after == count_before, (
        f"Watchdog fired after stop_all: {count_before} → {count_after}"
    )


# ---------------------------------------------------------------------------
# 23–24  Metadata
# ---------------------------------------------------------------------------

def test_track_change_calls_push_on_metadata_pusher():
    """When a track starts, push() is called on all active metadata pushers."""
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")

    # Inject spy pusher
    spy = _SpyPusher()
    mgr._metadata_pushers["o1"] = spy

    class _Item:
        title = "Summer Nights"
        artist = "DJ Cool"

    eng.fire_track_change(current_item=_Item())

    assert ("Summer Nights", "DJ Cool") in spy.pushed


def test_track_change_none_current_calls_push_idle():
    """When current_item is None (engine idle), push_idle() is called."""
    mgr, eng = _manager()
    mgr.add_output(_output())
    mgr.start_output("o1")

    spy = _SpyPusher()
    mgr._metadata_pushers["o1"] = spy

    eng.fire_track_change(current_item=None)

    assert spy.idle_count >= 1


# ---------------------------------------------------------------------------
# 25–26  SoutBuilder integration
# ---------------------------------------------------------------------------

def test_unsupported_codec_does_not_crash_start_output():
    """start_output with an unsupported codec logs an error but doesn't raise."""
    mgr, eng = _manager()
    mgr.add_output(_output(codec="flac"))
    # Should NOT raise; SoutBuilder error is caught inside _apply_sout_chain
    mgr.start_output("o1")


def test_two_outputs_produce_duplicate_chain():
    """With two outputs, the sout chain sent to the engine contains 'duplicate'."""
    mgr, eng = _manager()
    o1 = StreamOutput(
        id="o1", name="MP3", protocol=StreamProtocol.ICECAST,
        url="ice.local", port=8000, mount="/mp3",
        username="source", password="pw", bitrate=128, codec="mp3",
    )
    o2 = StreamOutput(
        id="o2", name="OGG", protocol=StreamProtocol.ICECAST,
        url="ice.local", port=8000, mount="/ogg",
        username="source", password="pw", bitrate=128, codec="vorbis",
    )
    mgr.add_output(o1)
    mgr.add_output(o2)
    mgr.start_output("o1")
    mgr.start_output("o2")

    non_none = [c for c in eng.sout_calls if c is not None]
    assert non_none, "Expected at least one sout chain call"
    # After both outputs are started the last chain should contain 'duplicate'
    assert "duplicate" in non_none[-1], (
        f"Expected duplicate{{}} sout; got: {non_none[-1]}"
    )
