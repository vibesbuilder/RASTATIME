"""
T11.2 — LibVlcIngressManager unit tests.

Exercises the ingress manager without a network or VLC installation.
All I/O is replaced by:
* ``_SpyEngine``  — records load_queue / start / stop calls.
* ``_healthy``    — always-True health checker (source is live).
* ``_unhealthy``  — always-False health checker (source is gone).

Test inventory
--------------
build_stream_uri (4):
  1.  No credentials → http://host:port/mount
  2.  With credentials → http://user:pass@host:port/mount
  3.  Mount without leading slash gets one prepended.
  4.  Empty username OR empty password → no credentials embedded.

Registration (4):
  5.  register_source stores the source; list_sources returns it.
  6.  Registering the same ID twice replaces the old source.
  7.  unregister_source removes the source from list_sources.
  8.  get_source_status raises ValueError for unknown source_id.

Activation (6):
  9.  activate_source raises ValueError for unknown source_id.
 10.  activate_source calls engine.load_queue with correct URI.
 11.  activate_source calls engine.start().
 12.  activate_source transitions source to CONNECTING.
 13.  Activating a second source deactivates the first one first.
 14.  get_active_source returns the active source.

Deactivation (3):
 15.  deactivate_source raises ValueError for unknown source_id.
 16.  deactivate_source transitions source to IDLE.
 17.  deactivate_source calls engine.stop().

Status (2):
 18.  get_source_status for a never-activated source returns IDLE.
 19.  get_source_status after activation returns CONNECTING.

Watchdog (4):
 20.  Watchdog fires: healthy → source transitions to ACTIVE.
 21.  Watchdog re-arms after healthy tick (two-tick test).
 22.  Watchdog fires: unhealthy → source transitions to DISCONNECTED.
 23.  Watchdog fires: unhealthy → engine.stop() called.

State-change callbacks (3):
 24.  on_source_state_change callback is invoked on CONNECTING.
 25.  Exception in state-change callback is swallowed.
 26.  get_active_source returns None when no source is active.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional

import pytest

from streams._types import StreamProtocol, StreamState
from streams.ingress import (
    LibVlcIngressManager,
    SourceStateChangedEvent,
    StreamSource,
    build_stream_uri,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _SpyEngine:
    """Lightweight engine double — records calls, no VLC required."""

    def __init__(self) -> None:
        self.queue_calls: list[list] = []
        self.start_calls: int = 0
        self.stop_calls: int = 0

    def load_queue(self, items: list) -> None:
        self.queue_calls.append(list(items))

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


def _healthy(source: StreamSource) -> bool:
    return True


def _unhealthy(source: StreamSource) -> bool:
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(
    source_id: str = "s1",
    url: str = "icecast.example.com",
    port: int = 8000,
    mount: str = "/live",
    username: str = "",
    password: str = "",
) -> StreamSource:
    return StreamSource(
        id=source_id,
        name=f"Source {source_id}",
        protocol=StreamProtocol.ICECAST,
        url=url,
        port=port,
        mount=mount,
        username=username,
        password=password,
    )


def _manager(
    health_checker=_healthy,
    watchdog_interval: float = 0.05,
) -> tuple["LibVlcIngressManager", "_SpyEngine"]:
    engine = _SpyEngine()
    mgr = LibVlcIngressManager(
        engine=engine,
        watchdog_interval=watchdog_interval,
        health_checker=health_checker,
    )
    return mgr, engine


# ---------------------------------------------------------------------------
# 1–4  build_stream_uri
# ---------------------------------------------------------------------------

def test_uri_no_credentials():
    src = _source(url="icecast.example.com", port=8000, mount="/live")
    assert build_stream_uri(src) == "http://icecast.example.com:8000/live"


def test_uri_with_credentials():
    src = _source(
        url="ice.local", port=9000, mount="/show",
        username="dj", password="secret",
    )
    assert build_stream_uri(src) == "http://dj:secret@ice.local:9000/show"


def test_uri_mount_without_slash_gets_prepended():
    src = _source(mount="live")  # no leading slash
    uri = build_stream_uri(src)
    assert "/live" in uri
    assert uri.startswith("http://")


def test_uri_partial_credentials_no_embed():
    # only username, no password
    src = _source(username="dj", password="")
    uri = build_stream_uri(src)
    assert "@" not in uri

    # only password, no username
    src2 = _source(username="", password="secret")
    uri2 = build_stream_uri(src2)
    assert "@" not in uri2


# ---------------------------------------------------------------------------
# 5–8  Registration
# ---------------------------------------------------------------------------

def test_register_source_appears_in_list():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    assert src in mgr.list_sources()


def test_register_same_id_replaces():
    mgr, _ = _manager()
    src_a = _source("s1", url="old.example.com")
    src_b = _source("s1", url="new.example.com")
    mgr.register_source(src_a)
    mgr.register_source(src_b)
    sources = mgr.list_sources()
    assert len(sources) == 1
    assert sources[0].url == "new.example.com"


def test_unregister_source_removes_it():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.unregister_source("s1")
    assert src not in mgr.list_sources()


def test_get_source_status_unknown_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError, match="Unknown ingress source id"):
        mgr.get_source_status("no-such-id")


# ---------------------------------------------------------------------------
# 9–14  Activation
# ---------------------------------------------------------------------------

def test_activate_unknown_source_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError, match="Unknown ingress source id"):
        mgr.activate_source("ghost")


def test_activate_loads_correct_uri():
    mgr, engine = _manager()
    src = _source("s1", url="ice.local", port=9000, mount="/show",
                  username="dj", password="pw")
    mgr.register_source(src)
    mgr.activate_source("s1")

    assert len(engine.queue_calls) == 1
    item = engine.queue_calls[0][0]
    assert item.uri == "http://dj:pw@ice.local:9000/show"


def test_activate_calls_engine_start():
    mgr, engine = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    assert engine.start_calls == 1


def test_activate_transitions_to_connecting():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    status = mgr.get_source_status("s1")
    assert status.state == StreamState.CONNECTING


def test_activating_second_source_deactivates_first():
    mgr, engine = _manager()
    s1 = _source("s1")
    s2 = _source("s2")
    mgr.register_source(s1)
    mgr.register_source(s2)
    mgr.activate_source("s1")
    mgr.activate_source("s2")
    # s1 should no longer be the active source
    assert mgr.get_active_source().id == "s2"  # type: ignore[union-attr]


def test_get_active_source_returns_active():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    active = mgr.get_active_source()
    assert active is not None
    assert active.id == "s1"


# ---------------------------------------------------------------------------
# 15–17  Deactivation
# ---------------------------------------------------------------------------

def test_deactivate_unknown_source_raises():
    mgr, _ = _manager()
    with pytest.raises(ValueError, match="Unknown ingress source id"):
        mgr.deactivate_source("ghost")


def test_deactivate_transitions_to_idle():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    mgr.deactivate_source("s1")
    status = mgr.get_source_status("s1")
    assert status.state == StreamState.IDLE


def test_deactivate_calls_engine_stop():
    mgr, engine = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    mgr.deactivate_source("s1")
    assert engine.stop_calls >= 1


# ---------------------------------------------------------------------------
# 18–19  Status
# ---------------------------------------------------------------------------

def test_status_never_activated_is_idle():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    status = mgr.get_source_status("s1")
    assert status.state == StreamState.IDLE


def test_status_after_activation_is_connecting():
    mgr, _ = _manager()
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    status = mgr.get_source_status("s1")
    assert status.state == StreamState.CONNECTING


# ---------------------------------------------------------------------------
# 20–23  Watchdog
# ---------------------------------------------------------------------------

TICK = 0.05   # watchdog interval for tests (50 ms)
WAIT = 0.35   # time to wait for watchdog to fire (7× TICK)


def _wait_for_state(mgr: LibVlcIngressManager, source_id: str,
                    target: StreamState, timeout: float = WAIT) -> bool:
    """Poll until source reaches *target* state or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if mgr.get_source_status(source_id).state == target:
                return True
        except ValueError:
            pass
        time.sleep(0.01)
    return False


def test_watchdog_healthy_transitions_to_active():
    mgr, _ = _manager(health_checker=_healthy, watchdog_interval=TICK)
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    reached = _wait_for_state(mgr, "s1", StreamState.ACTIVE)
    mgr.deactivate_source("s1")
    assert reached, "Source did not reach ACTIVE state within timeout"


def test_watchdog_rearmed_after_healthy_tick():
    """Two watchdog ticks should both succeed; source stays ACTIVE."""
    mgr, _ = _manager(health_checker=_healthy, watchdog_interval=TICK)
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    # Wait long enough for at least 2 ticks
    time.sleep(TICK * 5)
    status = mgr.get_source_status("s1")
    mgr.deactivate_source("s1")
    assert status.state == StreamState.ACTIVE


def test_watchdog_unhealthy_transitions_to_disconnected():
    mgr, engine = _manager(health_checker=_unhealthy, watchdog_interval=TICK)
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    reached = _wait_for_state(mgr, "s1", StreamState.DISCONNECTED)
    assert reached, "Source did not reach DISCONNECTED state within timeout"


def test_watchdog_unhealthy_stops_engine():
    mgr, engine = _manager(health_checker=_unhealthy, watchdog_interval=TICK)
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    _wait_for_state(mgr, "s1", StreamState.DISCONNECTED)
    time.sleep(TICK)   # small extra wait for engine.stop() call
    assert engine.stop_calls >= 1


# ---------------------------------------------------------------------------
# 24–26  State-change callbacks
# ---------------------------------------------------------------------------

def test_state_callback_invoked_on_connecting():
    events: list[SourceStateChangedEvent] = []
    mgr, _ = _manager()
    mgr.on_source_state_change(events.append)
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")
    # CONNECTING must have been fired
    states = [e.current_state for e in events]
    assert StreamState.CONNECTING in states


def test_exception_in_state_callback_swallowed():
    """A raising callback must not prevent other callbacks from running."""
    good: list[int] = []

    def _bad(e: SourceStateChangedEvent) -> None:
        raise RuntimeError("kaboom")

    mgr, _ = _manager()
    mgr.on_source_state_change(_bad)
    mgr.on_source_state_change(lambda e: good.append(1))
    src = _source()
    mgr.register_source(src)
    mgr.activate_source("s1")   # must not raise
    assert good  # at least one call got through


def test_get_active_source_none_when_no_source_active():
    mgr, _ = _manager()
    assert mgr.get_active_source() is None
