"""
RASTATIME 2026-11-16 - early show login: a host of the NEXT show may connect
up to 5 min before it starts.  The legacy check names the start
(X-Rastatime-Hold-Until), PLAYOUT answers ``ok <unix time>``, Liquidsoap keeps
the DJ behind its show_dj_from gate, and the SourceSwitcher stays SCHEDULED
until the start (the show on air runs untouched).
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from rastatime_playout import source_switcher as ss
from rastatime_playout.dj_auth import DjAuthenticator, hold_until_from
from rastatime_playout.source_switcher import SourceState, SourceSwitcher


def _session(hold=None):
    headers = {"icecast-auth-user": "1"}
    if hold is not None:
        headers["x-rastatime-hold-until"] = str(hold)
    session = MagicMock()
    session.post.return_value = SimpleNamespace(status_code=200, headers=headers)
    return session


# ---- the header -------------------------------------------------------------


def test_hold_until_from_accepts_only_a_near_future_time():
    now = 1_800_000_000.0
    assert hold_until_from(None, now) is None
    assert hold_until_from("", now) is None
    assert hold_until_from("soon", now) is None
    assert hold_until_from(str(int(now) - 1), now) is None  # already passed
    assert hold_until_from(str(int(now) + 299), now) == int(now) + 299
    assert hold_until_from(f"{now + 120:.1f}", now) == int(now) + 120
    with pytest.raises(ValueError):
        hold_until_from(str(int(now) + 3600), now)


# ---- DjAuthenticator ----------------------------------------------------------


def test_early_show_login_answers_ok_with_the_show_start(caplog):
    hold = int(time.time()) + 240
    auth = DjAuthenticator("http://web", session=_session(hold))
    with caplog.at_level("INFO"):
        assert auth.check("show", "host", "pw", "192.168.1.7") == f"ok {hold}"
    assert "accepted early - waits off air until" in caplog.text
    assert "pw" not in caplog.text.replace("show login", "")


def test_a_hold_on_a_master_login_is_ignored():
    hold = int(time.time()) + 240
    assert (
        DjAuthenticator("http://web", session=_session(hold)).check("master", "chef", "pw") == "ok"
    )


def test_a_passed_hold_is_a_plain_ok():
    assert (
        DjAuthenticator("http://web", session=_session(int(time.time()) - 5)).check(
            "show", "h", "pw"
        )
        == "ok"
    )


def test_an_implausible_hold_refuses_the_login():
    far = int(time.time()) + 3600
    assert DjAuthenticator("http://web", session=_session(far)).check("show", "h", "pw") == "denied"


def test_dj_auth_endpoint_passes_the_hold_through():
    h = ss._EventHandler.__new__(ss._EventHandler)
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    body = b"source=show&user=h&password=pw&address=192.168.1.7"
    h.headers = {"Content-Length": str(len(body))}
    h.rfile = MagicMock()
    h.rfile.read.return_value = body
    checker = MagicMock()
    checker.check.return_value = "ok 1800000240"
    old = ss._EventHandler.dj_auth
    ss._EventHandler.dj_auth = checker
    try:
        h._handle_dj_auth(urlparse("/dj-auth"))
    finally:
        ss._EventHandler.dj_auth = old
    assert sent == [(200, "ok 1800000240")]


# ---- SourceSwitcher ----------------------------------------------------------


def _switcher():
    states = []
    return SourceSwitcher(switch_callback=states.append), states


def test_a_waiting_show_dj_keeps_the_schedule_until_the_start():
    sw, states = _switcher()
    sw.on_show_connect(time.time() + 0.3)
    assert sw.is_show_connected() is True
    assert sw.current_state == SourceState.SCHEDULED
    assert states == []  # no callback: the show on air runs on
    assert sw.show_hold_until() is not None
    deadline = time.time() + 3
    while sw.current_state != SourceState.SHOW and time.time() < deadline:
        time.sleep(0.05)
    assert sw.current_state == SourceState.SHOW
    assert states == [SourceState.SHOW]
    assert sw.show_hold_until() is None


def test_leaving_while_waiting_changes_nothing_on_air():
    sw, states = _switcher()
    sw.on_show_connect(time.time() + 60)
    sw.on_show_disconnect()
    assert sw.current_state == SourceState.SCHEDULED
    assert states == []  # no DJ-off resume for a DJ who was never on air
    assert sw.show_hold_until() is None
    assert sw._hold_timer is None


def test_the_reconciler_keeps_a_known_hold():
    sw, states = _switcher()
    hold = time.time() + 60
    sw.on_show_connect(hold)
    sw.on_show_connect(None)  # telnet reconcile without a value
    assert sw.show_hold_until() == pytest.approx(hold)
    assert sw.current_state == SourceState.SCHEDULED
    sw.on_show_disconnect()


def test_master_still_wins_over_a_waiting_show_dj():
    sw, states = _switcher()
    sw.on_show_connect(time.time() + 60)
    sw.on_master_connect()
    assert sw.current_state == SourceState.MASTER
    sw.on_master_disconnect()
    assert sw.current_state == SourceState.SCHEDULED
    sw.on_show_disconnect()


@pytest.fixture
def handler():
    h = ss._EventHandler.__new__(ss._EventHandler)
    sw, states = _switcher()
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    h.send_response = lambda code: sent.append(("status", code))
    h.send_header = lambda *a: None
    h.end_headers = lambda: None
    h.wfile = MagicMock()
    old = ss._EventHandler.switcher
    ss._EventHandler.switcher = sw
    yield h, sw, states, sent
    ss._EventHandler.switcher = old
    sw.on_show_disconnect()


def test_source_event_from_sets_the_hold(handler):
    h, sw, states, sent = handler
    hold = int(time.time()) + 120
    h._handle_source_event(urlparse(f"/source-event?source=show&status=on&from={hold}."))
    assert sw.current_state == SourceState.SCHEDULED
    assert sw.show_hold_until() == pytest.approx(hold)
    h._handle_source_state()
    payload = json.loads(h.wfile.write.call_args.args[0])
    assert payload["show_connected"] is True
    assert payload["current_state"] == "scheduled"
    assert payload["show_hold_until"] == hold


def test_source_event_with_from_zero_is_on_air_at_once(handler):
    h, sw, states, sent = handler
    h._handle_source_event(urlparse("/source-event?source=show&status=on&from=0."))
    assert sw.current_state == SourceState.SHOW
    h._handle_source_state()
    assert json.loads(h.wfile.write.call_args.args[0])["show_hold_until"] is None


def test_read_show_hold_over_telnet():
    future = time.time() + 100
    client = MagicMock()
    client.send_command.return_value = f"{future:.0f}."
    assert ss._read_show_hold(client) == pytest.approx(int(future), abs=1)
    client.send_command.return_value = "0."
    assert ss._read_show_hold(client) == 0.0
    client.send_command.side_effect = RuntimeError("telnet gone")
    assert ss._read_show_hold(client) == 0.0
