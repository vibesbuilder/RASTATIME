"""
RASTATIME 2026-11-18 - the show source ends with the show.

A show DJ who stayed connected past the end kept the next show's opening off
air (2026-11-17 10:00: the hour jingle joined at second 6 of 10).  The legacy
check now names the end of the show (chain) a login goes on air for
(X-Rastatime-On-Air-Until / -Instance); PLAYOUT hands Liquidsoap
``ok <hold> <until>`` and keeps the episode; Liquidsoap closes the bus arm at
the end (show_dj_until); the SourceSwitcher leaves SHOW half a second before
it - without a resume - and disconnects the client right after.
"""

from __future__ import annotations

import io
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from rastatime_playout import source_switcher as ss
from rastatime_playout.dj_auth import DjAuthenticator, instance_from, on_air_until_from
from rastatime_playout.source_switcher import REASON_SHOW_END, SourceState, SourceSwitcher


def _session(hold=None, until=None, instance=None):
    headers = {"icecast-auth-user": "1"}
    if hold is not None:
        headers["x-rastatime-hold-until"] = str(hold)
    if until is not None:
        headers["x-rastatime-on-air-until"] = str(until)
    if instance is not None:
        headers["x-rastatime-on-air-instance"] = str(instance)
    session = MagicMock()
    session.post.return_value = SimpleNamespace(status_code=200, headers=headers)
    return session


# ---- the headers ------------------------------------------------------------


def test_on_air_until_from_takes_a_future_time_within_two_days():
    now = 1_800_000_000.0
    assert on_air_until_from(None, now) is None
    assert on_air_until_from("", now) is None
    assert on_air_until_from("later", now) is None
    assert on_air_until_from(str(int(now)), now) is None  # passed
    assert on_air_until_from(str(int(now) + 900), now) == int(now) + 900
    assert on_air_until_from(f"{now + 900:.1f}", now) == int(now) + 900
    assert on_air_until_from(str(int(now) + 3 * 86400), now) is None  # not trusted, no end


def test_instance_from():
    assert instance_from("4711") == 4711
    assert instance_from(" 12 ") == 12
    assert instance_from(None) == 0
    assert instance_from("x") == 0
    assert instance_from("-3") == 0


# ---- DjAuthenticator ----------------------------------------------------------


def test_show_login_answer_carries_the_end_and_the_episode(caplog):
    until = int(time.time()) + 900
    auth = DjAuthenticator("http://web", session=_session(until=until, instance=4711))
    with caplog.at_level("INFO"):
        assert auth.check("show", "host", "pw", "192.168.1.7") == f"ok 0 {until} 4711"
    assert "on air until" in caplog.text


def test_early_show_login_answer_carries_hold_end_and_episode():
    hold = int(time.time()) + 200
    until = hold + 900
    auth = DjAuthenticator("http://web", session=_session(hold, until, 12))
    assert auth.check("show", "host", "pw", "192.168.1.7") == f"ok {hold} {until} 12"


def test_no_end_header_answers_as_before():
    assert DjAuthenticator("http://web", session=_session()).check("show", "h", "p") == "ok"
    hold = int(time.time()) + 200
    assert (
        DjAuthenticator("http://web", session=_session(hold)).check("show", "h", "p")
        == f"ok {hold}"
    )


def test_a_master_login_never_gets_an_end():
    until = int(time.time()) + 900
    auth = DjAuthenticator("http://web", session=_session(until=until, instance=1))
    assert auth.check("master", "boss", "pw") == "ok"


def test_an_implausible_end_is_not_applied():
    far = int(time.time()) + 5 * 86400
    auth = DjAuthenticator("http://web", session=_session(until=far, instance=1))
    assert auth.check("show", "h", "p") == "ok"


# ---- SourceSwitcher -----------------------------------------------------------


def _switcher():
    states, ended = [], []
    sw = SourceSwitcher(switch_callback=states.append, show_end_callback=lambda: ended.append(1))
    return sw, states, ended


def _wait(cond, timeout=4.0):
    deadline = time.time() + timeout
    while not cond() and time.time() < deadline:
        time.sleep(0.02)
    return cond()


def test_show_dj_leaves_the_air_before_the_end_and_is_disconnected_after_it():
    sw, states, ended = _switcher()
    until = time.time() + 1.2
    sw.on_show_connect(0.0, until=until)
    assert sw.current_state == SourceState.SHOW
    assert sw.show_until() == pytest.approx(until)
    # SHOW_END_LEAD_SECONDS before the end: back to scheduled, DJ still connected
    assert _wait(lambda: sw.current_state == SourceState.SCHEDULED)
    left_at = time.time()
    assert until - ss.SHOW_END_LEAD_SECONDS - 0.1 <= left_at <= until + 0.3
    assert sw.is_show_connected() is True
    assert sw.last_transition_reason == REASON_SHOW_END
    assert states == [SourceState.SHOW, SourceState.SCHEDULED]
    assert ended == []
    # SHOW_END_KICK_AFTER_SECONDS after the end: the disconnect callback
    assert _wait(lambda: ended == [1])
    assert time.time() >= until + ss.SHOW_END_KICK_AFTER_SECONDS - 0.1
    # the harbor then reports the disconnect: no further transition, no resume
    sw.on_show_disconnect()
    assert states == [SourceState.SHOW, SourceState.SCHEDULED]
    assert sw.show_until() is None and sw._kick_timer is None and sw._until_timer is None


def test_a_dj_who_leaves_on_their_own_is_a_normal_dj_off():
    sw, states, ended = _switcher()
    sw.on_show_connect(0.0, until=time.time() + 60)
    sw.on_show_disconnect()
    assert states == [SourceState.SHOW, SourceState.SCHEDULED]
    assert sw.last_transition_reason == ""  # the scheduler resumes as before
    assert ended == [] and sw._kick_timer is None


def test_no_end_means_no_timers_and_no_end():
    sw, states, ended = _switcher()
    sw.on_show_connect(0.0)  # an older Liquidsoap render / static login
    assert sw.current_state == SourceState.SHOW
    assert sw.show_until() is None and sw._kick_timer is None
    sw.on_show_connect(0.0, until=0.0)
    assert sw.show_until() is None and sw._kick_timer is None
    sw.on_show_disconnect()
    assert ended == []


def test_early_login_then_end():
    sw, states, ended = _switcher()
    now = time.time()
    sw.on_show_connect(now + 0.3, until=now + 1.5)
    assert sw.current_state == SourceState.SCHEDULED and states == []
    assert _wait(lambda: sw.current_state == SourceState.SHOW)
    assert _wait(lambda: states == [SourceState.SHOW, SourceState.SCHEDULED])
    assert sw.last_transition_reason == REASON_SHOW_END
    sw.on_show_disconnect()


def test_master_wins_and_the_show_end_still_disconnects_the_show_dj():
    sw, states, ended = _switcher()
    sw.on_show_connect(0.0, until=time.time() + 0.6)
    sw.on_master_connect()
    assert sw.current_state == SourceState.MASTER
    assert _wait(lambda: ended == [1])
    assert sw.current_state == SourceState.MASTER  # the master is untouched
    sw.on_show_disconnect()
    sw.on_master_disconnect()


def test_a_dj_found_connected_after_the_end_is_disconnected_at_once():
    """PLAYOUT restarted over the boundary: the reconciler reads a past end."""
    sw, states, ended = _switcher()
    sw.on_show_connect(0.0, until=time.time() - 30)
    assert sw.current_state == SourceState.SCHEDULED
    assert states == []  # never on air for PLAYOUT: nothing to switch or resume
    assert _wait(lambda: ended == [1], timeout=2.0)
    sw.on_show_disconnect()


def test_grant_binds_the_episode_to_the_connect_with_the_same_end():
    sw, states, ended = _switcher()
    until = time.time() + 600
    sw.note_show_grant(until, 4711)
    sw.on_show_connect(0.0, until=until)
    assert sw.show_until_instance() == 4711
    # a later login that Liquidsoap refuses (mount taken) changes nothing
    sw.note_show_grant(until + 3600, 9999)
    assert sw.show_until_instance() == 4711
    sw.on_show_connect(None)  # telnet reconcile without values
    assert sw.show_until_instance() == 4711 and sw.show_until() == pytest.approx(until)
    sw.on_show_disconnect()
    assert sw.show_until_instance() == 0
    # the stale grant of the refused login does not fit the next connect
    sw.on_show_connect(0.0, until=until + 5)
    assert sw.show_until_instance() == 0
    sw.on_show_disconnect()


def test_a_moved_end_moves_the_timers_and_keeps_the_episode():
    sw, states, ended = _switcher()
    until = time.time() + 600
    sw.note_show_grant(until, 77)
    sw.on_show_connect(0.0, until=until)
    first_kick = sw._kick_timer
    sw.set_show_until(until + 900)
    assert sw.show_until() == pytest.approx(until + 900)
    assert sw.show_until_instance() == 77
    assert sw._kick_timer is not first_kick and sw.current_state == SourceState.SHOW
    # shortened into the past: off air now, disconnected right after
    sw.set_show_until(time.time() - 1)
    assert sw.current_state == SourceState.SCHEDULED
    assert sw.last_transition_reason == REASON_SHOW_END
    assert _wait(lambda: ended == [1], timeout=2.0)
    sw.on_show_disconnect()
    sw.set_show_until(time.time() + 60)  # nobody connected: ignored
    assert sw.show_until() is None


# ---- the listener -------------------------------------------------------------


@pytest.fixture
def handler():
    h = ss._EventHandler.__new__(ss._EventHandler)
    sw, states, ended = _switcher()
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    h.send_response = lambda code: sent.append(("status", code))
    h.send_header = lambda *a: None
    h.end_headers = lambda: None
    h.wfile = MagicMock()
    old = (ss._EventHandler.switcher, ss._EventHandler.dj_auth)
    ss._EventHandler.switcher = sw
    yield h, sw, states, sent
    ss._EventHandler.switcher, ss._EventHandler.dj_auth = old
    sw.on_show_disconnect()


def test_source_event_until_sets_the_end(handler):
    h, sw, states, sent = handler
    until = int(time.time()) + 300
    h._handle_source_event(urlparse(f"/source-event?source=show&status=on&from=0.&until={until}."))
    assert sw.current_state == SourceState.SHOW
    assert sw.show_until() == pytest.approx(until)
    h._handle_source_state()
    payload = json.loads(h.wfile.write.call_args.args[0])
    assert payload["show_until"] == until and payload["current_state"] == "show"


def test_source_event_without_until_has_no_end(handler):
    h, sw, states, sent = handler
    h._handle_source_event(urlparse("/source-event?source=show&status=on&from=0."))
    assert sw.show_until() is None
    h._handle_source_state()
    assert json.loads(h.wfile.write.call_args.args[0])["show_until"] is None
    h._handle_source_event(urlparse("/source-event?source=show&status=on&from=0.&until=0."))
    assert sw.show_until() is None


def test_dj_auth_listener_keeps_the_episode_and_hands_liquidsoap_two_numbers(handler):
    h, sw, states, sent = handler
    until = int(time.time()) + 300
    ss._EventHandler.dj_auth = SimpleNamespace(check=lambda *a: f"ok 0 {until} 4711")
    body = b"source=show&user=host&password=pw&address=192.168.1.7"
    h.headers = {"Content-Length": str(len(body))}
    h.rfile = io.BytesIO(body)
    h._handle_dj_auth(urlparse("/dj-auth"))
    assert sent[-1] == (200, f"ok 0 {until}")
    h._handle_source_event(urlparse(f"/source-event?source=show&status=on&from=0.&until={until}."))
    assert sw.show_until_instance() == 4711


def test_dj_auth_listener_passes_the_older_answers_through(handler):
    h, sw, states, sent = handler
    for verdict in ("ok", "ok 1800000000"):
        ss._EventHandler.dj_auth = SimpleNamespace(check=lambda *a, v=verdict: v)
        body = b"source=show&user=host&password=pw"
        h.headers = {"Content-Length": str(len(body))}
        h.rfile = io.BytesIO(body)
        h._handle_dj_auth(urlparse("/dj-auth"))
        assert sent[-1] == (200, verdict)


def test_read_show_until_over_telnet():
    client = MagicMock()
    client.send_command.return_value = "1800000000."
    assert ss._read_show_until(client) == 1_800_000_000.0
    client.send_command.return_value = "0."
    assert ss._read_show_until(client) == 0.0
    client.send_command.return_value = "ERROR: unknown variable"
    assert ss._read_show_until(client) == 0.0
    client.send_command.side_effect = RuntimeError("telnet gone")
    assert ss._read_show_until(client) == 0.0


def test_reconcile_takes_hold_and_end_over():
    sw, states, ended = _switcher()
    until = time.time() + 300
    client = MagicMock()

    def reply(command):
        return {
            "master_dj.status": "no source client connected",
            "show_dj.status": "source client connected from 192.168.1.7",
            "var.get show_dj_from": "0.",
            "var.get show_dj_until": f"{until:.0f}.",
        }[command]

    client.send_command.side_effect = reply
    ss._reconcile_liquidsoap_once(client, sw)
    assert sw.current_state == SourceState.SHOW
    assert sw.show_until() == pytest.approx(until, abs=1)
    sw.on_show_disconnect()


# ---- the scheduler ------------------------------------------------------------


def _scheduler():
    from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    sched = PlayoutScheduler(engine=engine, api_client=MagicMock())
    return sched, engine


def test_show_end_does_not_resume_the_row_under_the_live_show():
    sched, engine = _scheduler()
    sched._resume_scheduled_locked = MagicMock()
    sched.set_source_switcher(SimpleNamespace(last_transition_reason=REASON_SHOW_END))
    sched.switch_audio_source(SourceState.SCHEDULED)
    sched._resume_scheduled_locked.assert_not_called()
    # a DJ who hangs up on their own: the resume as before
    sched.set_source_switcher(SimpleNamespace(last_transition_reason=""))
    sched.switch_audio_source(SourceState.SCHEDULED)
    sched._resume_scheduled_locked.assert_called_once()


def test_follow_show_end_moves_gate_and_switcher_when_the_episode_end_moved():
    sched, engine = _scheduler()
    known = 1_800_000_000.0
    switcher = MagicMock()
    switcher.show_until_instance.return_value = 4711
    switcher.show_until.return_value = known
    sched.set_source_switcher(switcher)
    response = MagicMock()
    response.json.return_value = {"ends_at": "2027-01-15T08:15:00Z"}  # = known + 900 s
    sched._api_client.get_show_instance.return_value = response
    import calendar
    from datetime import datetime

    moved = float(calendar.timegm(datetime(2027, 1, 15, 8, 15, 0).timetuple()))
    switcher.show_until.return_value = moved - 900
    sched.follow_show_end()
    sched._api_client.get_show_instance.assert_called_with(4711)
    engine.show_dj_until_set.assert_called_once_with(moved)
    switcher.set_show_until.assert_called_once_with(moved)

    # unchanged end: nothing sent
    engine.show_dj_until_set.reset_mock()
    switcher.set_show_until.reset_mock()
    switcher.show_until.return_value = moved
    sched.follow_show_end()
    engine.show_dj_until_set.assert_not_called()
    switcher.set_show_until.assert_not_called()


def test_follow_show_end_is_quiet_without_a_dj_and_on_errors():
    sched, engine = _scheduler()
    sched.follow_show_end()  # no switcher wired in this test scheduler
    switcher = MagicMock()
    switcher.show_until_instance.return_value = 0
    switcher.show_until.return_value = None
    sched.set_source_switcher(switcher)
    sched.follow_show_end()
    sched._api_client.get_show_instance.assert_not_called()
    # unreadable episode: the known end stays
    switcher.show_until_instance.return_value = 5
    switcher.show_until.return_value = 1_800_000_000.0
    sched._api_client.get_show_instance.side_effect = RuntimeError("api down")
    sched.follow_show_end()
    engine.show_dj_until_set.assert_not_called()
    # telnet fails: the switcher keeps its timers
    sched._api_client.get_show_instance.side_effect = None
    response = MagicMock()
    response.json.return_value = {"ends_at": "2027-01-15T08:15:00Z"}
    sched._api_client.get_show_instance.return_value = response
    engine.show_dj_until_set.side_effect = OSError("telnet gone")
    sched.follow_show_end()
    switcher.set_show_until.assert_not_called()


def test_engine_sets_the_end_over_telnet():
    from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine

    engine = LiquidsoapPlayoutEngine.__new__(LiquidsoapPlayoutEngine)
    engine._telnet = MagicMock()
    engine.show_dj_until_set(1_800_000_000)
    engine._telnet.var_set.assert_called_once_with("show_dj_until", "1800000000.0")
    engine.show_dj_until_set(-5)
    engine._telnet.var_set.assert_called_with("show_dj_until", "0.0")
