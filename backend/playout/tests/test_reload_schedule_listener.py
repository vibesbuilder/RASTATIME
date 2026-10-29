"""
RASTATIME 2026-10-22 - /reload-schedule answers at once, the refresh runs
on a coalescing background runner (source_switcher._CoalescingRunner).
"""

import threading
import time
import urllib.request

import pytest

import rastatime_playout.source_switcher as ss


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.005)


class _GatedFn:
    """A runner function that blocks on a gate and counts its runs."""

    def __init__(self, fail_first=False):
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.runs = 0
        self._fail_first = fail_first

    def __call__(self):
        self.runs += 1
        self.entered.set()
        self.gate.wait(5.0)
        if self._fail_first and self.runs == 1:
            raise RuntimeError("refresh failed")


# ---- _CoalescingRunner ----------------------------------------------------


def test_request_returns_at_once_and_runs_in_the_background():
    fn = _GatedFn()
    runner = ss._CoalescingRunner("t", fn)
    t0 = time.monotonic()
    assert runner.request() is True
    assert time.monotonic() - t0 < 0.5
    assert fn.entered.wait(5.0)
    fn.gate.set()
    _wait_for(lambda: not runner._running)
    assert fn.runs == 1


def test_requests_during_a_run_collapse_into_one_more_run():
    fn = _GatedFn()
    runner = ss._CoalescingRunner("t", fn)
    assert runner.request() is True
    assert fn.entered.wait(5.0)
    assert [runner.request() for _ in range(4)] == [False] * 4
    fn.gate.set()
    _wait_for(lambda: not runner._running)
    assert fn.runs == 2


def test_a_failing_run_is_logged_and_later_runs_still_happen(caplog):
    fn = _GatedFn(fail_first=True)
    fn.gate.set()
    runner = ss._CoalescingRunner("reload-schedule", fn)
    runner.request()
    _wait_for(lambda: fn.runs == 1 and not runner._running)
    assert "reload-schedule failed: refresh failed" in caplog.text
    assert runner.request() is True
    _wait_for(lambda: fn.runs == 2 and not runner._running)


def test_reload_once_refreshes_then_requests_the_preflight_rescan():
    calls = []

    class Sched:
        def refresh(self):
            calls.append("refresh")

    class Preflight:
        def request(self):
            calls.append("preflight")
            return True

    ss._reload_schedule_once(Sched(), Preflight())
    assert calls == ["refresh", "preflight"]
    ss._reload_schedule_once(Sched(), None)
    assert calls == ["refresh", "preflight", "refresh"]


# ---- the HTTP handler -----------------------------------------------------


@pytest.fixture
def handler(monkeypatch):
    h = ss._EventHandler.__new__(ss._EventHandler)
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    return h, sent


def test_handler_answers_200_before_the_refresh_finishes(handler, monkeypatch):
    h, sent = handler
    fn = _GatedFn()
    runner = ss._CoalescingRunner("reload-schedule", fn)
    monkeypatch.setattr(ss._EventHandler, "reload_runner", runner)
    h._handle_reload_schedule()
    assert sent == [(200, "ok")]
    assert fn.entered.wait(5.0)
    assert fn.runs == 1          # still running, the reply is already out
    fn.gate.set()
    _wait_for(lambda: not runner._running)


def test_handler_without_a_scheduler_answers_500(handler, monkeypatch):
    h, sent = handler
    monkeypatch.setattr(ss._EventHandler, "reload_runner", None)
    h._handle_reload_schedule()
    assert sent == [(500, "scheduler not initialised")]


def test_listener_end_to_end_fast_reply_and_coalesced_refreshes(monkeypatch):
    monkeypatch.setattr(ss, "_liquidsoap_state_poll_loop", lambda *a, **k: None)
    gate = threading.Event()
    refreshes = []

    class Sched:
        def refresh(self):
            refreshes.append(time.monotonic())
            gate.wait(5.0)

    server = ss.start_listener(
        ss.SourceSwitcher(switch_callback=lambda _s: None),
        scheduler=Sched(), host="127.0.0.1", port=0,
    )
    port = server.server_address[1]
    try:
        for _ in range(3):
            t0 = time.monotonic()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/reload-schedule", data=b"", method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                assert resp.read() == b"ok"
            assert time.monotonic() - t0 < 1.0
        _wait_for(lambda: len(refreshes) == 1)
        gate.set()
        _wait_for(lambda: len(refreshes) == 2)
        _wait_for(lambda: not ss._EventHandler.reload_runner._running)
        assert len(refreshes) == 2
    finally:
        gate.set()
        server.shutdown()
        server.server_close()
        monkeypatch.setattr(ss._EventHandler, "switcher", None)
        monkeypatch.setattr(ss._EventHandler, "scheduler", None)
        monkeypatch.setattr(ss._EventHandler, "reload_runner", None)
