"""
RASTATIME 2026-09-09 - option d: /source-event is fed by the harbor
callbacks rendered into rastatime.liq; the Liquidsoap telnet loop only
verifies - about a second after each event and otherwise every
``RASTATIME_DJ_RECONCILE_SECONDS`` (default 600 s since the second
step of 2026-09-09, floor 5 s).  While an
older render without the callbacks is loaded (probe
``rastatime.source_events``), the loop polls every 5 s as before.
"""
from __future__ import annotations

import logging
import threading
import time
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest

from libretime_playout import source_switcher as ss
from libretime_playout.source_switcher import SourceState, SourceSwitcher

IDLE = "no source client connected"
LIVE = "source client connected"
NO_PROBE = 'ERROR: unknown command, type "help" to get a list of commands.'


def _switcher():
    states = []
    return SourceSwitcher(switch_callback=states.append), states


def _client(master=IDLE, show=IDLE, events="on"):
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: {
        "master_dj.status": master,
        "show_dj.status": show,
        ss.SOURCE_EVENTS_PROBE: events,
    }[cmd]
    return client


def _probe_calls(client):
    return [c for c in client.send_command.call_args_list if c.args[0] == ss.SOURCE_EVENTS_PROBE]


def _record_waits(monkeypatch, sw, requested=False):
    """Replace sw.wait_reconcile: record the timeout, return ``requested``."""
    timeouts = []

    def fake_wait(timeout):
        timeouts.append(timeout)
        return requested

    monkeypatch.setattr(sw, "wait_reconcile", fake_wait)
    return timeouts


@pytest.fixture
def telnet_factory(monkeypatch):
    """Replace the LiquidsoapTelnetClient the loop instantiates."""
    holder = {}
    monkeypatch.setattr(
        "libretime_playout.engine.liquidsoap_telnet.LiquidsoapTelnetClient",
        lambda **kwargs: holder["client"],
    )
    return holder


@pytest.fixture
def handler(monkeypatch):
    """A bare _EventHandler (no socket) whose _send records the reply."""
    sw, states = _switcher()
    monkeypatch.setattr(ss._EventHandler, "switcher", sw)
    h = ss._EventHandler.__new__(ss._EventHandler)
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    return h, sw, states, sent


# ---- configuration --------------------------------------------------------


def test_defaults_are_slow_and_bounded():
    assert ss.DEFAULT_RECONCILE_INTERVAL_S == 600.0
    assert ss.MIN_RECONCILE_INTERVAL_S == 5.0
    assert ss.RECONCILE_SETTLE_S == 1.0
    assert ss.LEGACY_POLL_INTERVAL_S == 5.0
    assert ss.RECONCILE_INTERVAL_ENV == "RASTATIME_DJ_RECONCILE_SECONDS"
    assert ss.SOURCE_EVENTS_PROBE == "rastatime.source_events"


@pytest.mark.parametrize("raw,expected", [
    ("", 600.0),
    ("300", 300.0),
    (" 45 ", 45.0),
    ("abc", 600.0),      # not a number -> default
    ("1", 5.0),          # below the floor -> floor
    ("0", 5.0),
])
def test_reconcile_interval_from_env(raw, expected):
    assert ss.reconcile_interval_from_env({ss.RECONCILE_INTERVAL_ENV: raw}) == expected


def test_reconcile_interval_env_unset_uses_default():
    assert ss.reconcile_interval_from_env({}) == 600.0
    assert ss.reconcile_interval_from_env({}, default=7.0) == 7.0


# ---- SourceSwitcher wake-up -----------------------------------------------


def test_request_reconcile_wakes_wait_once():
    sw, _ = _switcher()
    assert sw.wait_reconcile(0) is False
    sw.request_reconcile()
    sw.request_reconcile()                  # idempotent
    assert sw.wait_reconcile(0) is True
    assert sw.wait_reconcile(0) is False    # cleared by the wait


def test_reconcile_once_syncs_state_from_telnet():
    sw, states = _switcher()
    ss._reconcile_liquidsoap_once(_client(master=LIVE), sw)
    assert sw.current_state == SourceState.MASTER
    ss._reconcile_liquidsoap_once(_client(), sw)
    assert sw.current_state == SourceState.SCHEDULED
    assert states == [SourceState.MASTER, SourceState.SCHEDULED]


@pytest.mark.parametrize("reply,expected", [
    ("on", True),
    ("  on\n", True),
    (NO_PROBE, False),
    ("off", False),
    ("", False),
])
def test_source_events_probe(reply, expected):
    assert ss._source_events_present(_client(events=reply)) is expected


# ---- /source-event ----------------------------------------------------------


def test_source_event_applies_state_and_requests_verification(handler):
    h, sw, states, sent = handler
    h._handle_source_event(urlparse("/source-event?source=master&status=on"))
    assert sent == [(200, "ok")]
    assert sw.is_master_connected() is True
    assert states == [SourceState.MASTER]
    assert sw.wait_reconcile(0) is True      # verification requested
    h._handle_source_event(urlparse("/source-event?source=master&status=off"))
    assert sw.current_state == SourceState.SCHEDULED
    assert sw.wait_reconcile(0) is True


def test_source_event_show_side(handler):
    h, sw, states, sent = handler
    h._handle_source_event(urlparse("/source-event?source=show&status=on"))
    assert sw.current_state == SourceState.SHOW
    assert sw.wait_reconcile(0) is True


def test_source_event_rejects_bad_input_without_requesting(handler):
    h, sw, states, sent = handler
    h._handle_source_event(urlparse("/source-event?source=bogus&status=on"))
    h._handle_source_event(urlparse("/source-event?source=master&status=maybe"))
    assert [code for code, _ in sent] == [400, 400]
    assert states == []
    assert sw.wait_reconcile(0) is False


# ---- the loop ----------------------------------------------------------------


def test_loop_verifies_right_after_an_event_instead_of_polling(telnet_factory):
    sw, _ = _switcher()
    client = _client()
    telnet_factory["client"] = client
    started = time.monotonic()
    thread = threading.Thread(
        target=ss._liquidsoap_state_poll_loop,
        kwargs=dict(switcher=sw, interval_s=60.0, settle_s=0.0, max_ticks=2),
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 5.0
    while client.send_command.call_count < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert client.send_command.call_count == 3      # probe + 2 status, now waiting
    time.sleep(0.3)
    assert client.send_command.call_count == 3      # no polling while waiting
    client.send_command.side_effect = lambda cmd: LIVE if cmd == "master_dj.status" else IDLE
    sw.request_reconcile()
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert client.send_command.call_count == 5      # probe not repeated once present
    assert sw.current_state == SourceState.MASTER
    assert time.monotonic() - started < 5.0         # far below the 60-s interval


def test_loop_settles_before_verifying_an_event(telnet_factory, monkeypatch):
    sw, _ = _switcher()
    telnet_factory["client"] = _client()
    sleeps = []
    monkeypatch.setattr(ss.time, "sleep", lambda s: sleeps.append(s))
    sw.request_reconcile()                          # pending before the loop starts
    ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=1.5, max_ticks=2)
    assert sleeps == [1.5]                          # the interval itself is never slept


def test_loop_waits_the_slow_interval_when_events_are_present(telnet_factory, monkeypatch):
    sw, _ = _switcher()
    client = _client()
    telnet_factory["client"] = client
    timeouts = _record_waits(monkeypatch, sw)
    ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=0.0, max_ticks=3)
    assert timeouts == [60.0, 60.0]
    assert len(_probe_calls(client)) == 1           # probed once per instance


def test_loop_polls_every_5s_while_an_old_render_is_loaded(telnet_factory, monkeypatch, caplog):
    sw, _ = _switcher()
    client = _client(events=NO_PROBE)
    telnet_factory["client"] = client
    timeouts = _record_waits(monkeypatch, sw)
    with caplog.at_level(logging.WARNING, logger="libretime_playout.source_switcher"):
        ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=0.0, max_ticks=3)
    assert timeouts == [ss.LEGACY_POLL_INTERVAL_S, ss.LEGACY_POLL_INTERVAL_S]
    assert len(_probe_calls(client)) == 3           # re-probed every round
    warnings = [r for r in caplog.records if "no harbor source events" in r.getMessage()]
    assert len(warnings) == 1                       # warned once, not every round


def test_loop_switches_to_the_slow_interval_after_a_new_render_appears(telnet_factory, monkeypatch):
    sw, _ = _switcher()
    replies = iter([NO_PROBE, NO_PROBE, "on"])
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: (
        next(replies) if cmd == ss.SOURCE_EVENTS_PROBE else IDLE
    )
    telnet_factory["client"] = client
    timeouts = _record_waits(monkeypatch, sw)
    ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=0.0, max_ticks=4)
    assert timeouts == [5.0, 5.0, 60.0]
    assert len(_probe_calls(client)) == 3


def test_loop_reprobes_after_a_telnet_error(telnet_factory, monkeypatch):
    sw, _ = _switcher()
    calls = {"n": 0}

    def send(cmd):
        if cmd == ss.SOURCE_EVENTS_PROBE:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("telnet down")
            return "on"
        return IDLE

    client = MagicMock()
    client.send_command.side_effect = send
    telnet_factory["client"] = client
    timeouts = _record_waits(monkeypatch, sw)
    ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=0.0, max_ticks=3)
    assert timeouts == [5.0, 60.0]                  # quick retry, then slow
    assert calls["n"] == 2


def test_loop_survives_telnet_errors(telnet_factory):
    sw, _ = _switcher()
    client = MagicMock()
    client.send_command.side_effect = ConnectionError("telnet down")
    telnet_factory["client"] = client
    ss._liquidsoap_state_poll_loop(sw, interval_s=0.01, settle_s=0.0, max_ticks=3)
    assert client.send_command.call_count == 3      # the probe fails first each round
    assert sw.current_state == SourceState.SCHEDULED


def test_start_listener_passes_the_interval_to_the_liquidsoap_loop(monkeypatch):
    seen = {}

    def fake_loop(switcher, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(ss, "_liquidsoap_state_poll_loop", fake_loop)
    sw, _ = _switcher()
    server = ss.start_listener(
        sw, host="127.0.0.1", port=0,
        reconcile_interval_s=77.0,
    )
    try:
        deadline = time.monotonic() + 5.0
        while "interval_s" not in seen and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        server.shutdown()
        server.server_close()
        monkeypatch.setattr(ss._EventHandler, "switcher", None)
    assert seen == {"interval_s": 77.0}
