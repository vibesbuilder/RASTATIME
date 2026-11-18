"""
RASTATIME 2026-11-18 - the show source ends with the show.

A show DJ who stayed connected past the end kept the next show's opening off
air (2026-11-17 10:00: the hour jingle joined at second 6 of 10).  The legacy
check now names the end of the show (chain) a login goes on air for
(X-Rastatime-On-Air-Until / -Instance); PLAYOUT hands Liquidsoap
``ok <hold> <until>`` and keeps the episode; Liquidsoap closes the bus arm at
the end (show_dj_until); the SourceSwitcher leaves SHOW half a second before
it - without a resume - and disconnects the client right after.

First acceptance 2026-11-18 10:00: the cut and the disconnect were on time,
but the track that was on air when the DJ took over was still paused in the
queue (the bus does not pull the scheduled arm under a DJ) and came back at
the show end; the next show's rows were pushed behind it.  At the show end
PLAYOUT now replaces the paused queue: by the next show's first file row,
which then starts in the frame the show arm closes, or by a silent filler
(second half of this file).
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


# ---- the paused queue at the show end (acceptance 2026-11-18 10:00) ----------


def _real_engine():
    from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
    from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient

    telnet = MagicMock(spec=LiquidsoapTelnetClient)
    telnet.request_queue_push.return_value = "42"
    telnet._host, telnet._port = "127.0.0.1", 1234
    return LiquidsoapPlayoutEngine(telnet_client=telnet), telnet


def _names(telnet):
    return [c[0] for c in telnet.mock_calls if not c[0].startswith("_")]


def test_replace_paused_flushes_sets_the_cut_pushes_and_skips():
    from rastatime_playout.engine.interface import PAUSED_CUT_SHAPE, PlayoutState

    eng, telnet = _real_engine()
    eng._state = PlayoutState.PLAYING
    eng._current_uri = "C:/m/stale.mp3"
    eng.stop()  # a deferred stop is pending
    telnet.reset_mock()
    assert eng.replace_paused("C:/m/next.mp3", cue_in=0.0, cue_out=9.88, gain_db=-10.7) is True
    assert _names(telnet) == [
        "request_queue_flush",
        "var_set",
        "var_set",
        "var_set",
        "var_set",
        "var_set",
        "request_queue_push",
        "request_queue_skip",
    ]
    assert PAUSED_CUT_SHAPE == "show_skip/both"
    assert [c.args for c in telnet.var_set.call_args_list][:2] == [
        ("rt_cross", "show_skip"),
        ("rt_nofade", "both"),
    ]
    assert "liq_cue_out" in telnet.request_queue_push.call_args.args[0]
    # nothing of ours is on air; the pushed request waits for its adoption
    assert eng._stop_timer is None and eng._stop_requested is False
    assert eng.get_state() == PlayoutState.STOPPED
    assert eng._current_uri is None
    assert (eng._queued_uri, eng._queued_request_id) == ("C:/m/next.mp3", "42")
    eng.adopt_queued("C:/m/next.mp3")
    assert eng.get_state() == PlayoutState.PLAYING
    assert (eng._current_uri, eng._current_request_id) == ("C:/m/next.mp3", "42")
    assert "request_queue_skip" not in _names(telnet)[8:]


def test_replace_paused_filler_is_not_adoptable_and_skip_can_be_left_out():
    eng, telnet = _real_engine()
    assert eng.replace_paused("C:/c/rt-silence-10s.wav", queued_ahead=False) is True
    assert eng._queued_uri is None and eng._queued_request_id is None
    telnet.reset_mock()
    assert eng.replace_paused("C:/m/next.mp3", skip=False) is True
    assert "request_queue_skip" not in _names(telnet)
    assert "request_queue_push" in _names(telnet)


def test_replace_paused_still_skips_after_a_rejected_push_and_survives_telnet_errors():
    eng, telnet = _real_engine()
    telnet.request_queue_push.return_value = "ERROR: no such file"
    assert eng.replace_paused("C:/m/next.mp3") is False
    assert "request_queue_skip" in _names(telnet)  # the paused request must not come back
    assert eng._queued_uri is None
    telnet.request_queue_flush.side_effect = ConnectionError("telnet gone")
    assert eng.replace_paused("C:/m/next.mp3") is False  # logged, never raised


def _file_event(start, row_id, *, instance=2, seconds=10):
    from datetime import timedelta

    from rastatime_playout.player.events import EventKind, FileEvent

    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=seconds),
        row_id=row_id,
        id=row_id,
        uri="C:/media/a.mp3",
        show_name="news",
        cue_in=0.0,
        cue_out=float(seconds),
        track_title=f"t{row_id}",
        artist_name="a",
        replay_gain=-10.7,
        fade_in=0.0,
        fade_out=0.0,
        mime="audio/mpeg",
        filesize=1000,
        instance_id=instance,
    )


@pytest.fixture
def end_sched(monkeypatch, tmp_path):
    """A scheduler half a second before the end of a connected DJ's show."""
    from pathlib import Path

    from rastatime_playout import playout_scheduler as ps
    from rastatime_playout.engine.interface import PlayoutState
    from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine

    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.replace_paused.return_value = True
    engine.playing_remaining_seconds.return_value = None
    sched = ps.PlayoutScheduler(
        engine=engine,
        api_client=MagicMock(),
        cache_dir=tmp_path,
        input_transition_seconds=1.0,
        track_crossfade_seconds=3.0,
    )
    sched._ensure_file_cached = MagicMock(return_value=Path("C:/cache/a.mp3"))
    sched._notify_media_started = MagicMock()
    sched._set_bus_show = MagicMock()
    sched._close_predecessor_source = MagicMock()
    until = float(int(time.time()) + 1)  # whole second, like a show end
    sched.set_source_switcher(
        SimpleNamespace(
            last_transition_reason=REASON_SHOW_END,
            current_state=SourceState.SCHEDULED,
            show_until=lambda: until,
        )
    )

    def arm(key, event, alive=True):
        timer = MagicMock()
        timer.is_alive.return_value = alive
        sched._armed_events[key] = event
        sched._timers[key] = (timer, None)

    return sched, engine, until, arm


def _utc(ts):
    from datetime import datetime

    return datetime.utcfromtimestamp(ts)


def test_show_end_puts_the_next_shows_first_file_row_on_the_paused_queue(end_sched):
    sched, engine, until, arm = end_sched
    first = _file_event(_utc(until), 29929)
    later = _file_event(_utc(until + 9.88), 29930)
    arm("first", first)
    arm("later", later)
    # the DJ took over mid-track; a successor was queued ahead back then
    sched._queued_ahead = ("old", _file_event(_utc(until - 300), 1, instance=1))
    sched._file_chain_lag = 0.9
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_called_once()
    args, kwargs = engine.replace_paused.call_args
    assert args == (str(sched._ensure_file_cached.return_value),)
    assert kwargs["cue_out"] == 10.0 and kwargs["gain_db"] == -10.7
    assert kwargs["queued_ahead"] is True
    assert kwargs["metadata"]["title"] == "t29929"
    assert sched._queued_ahead == ("first", first)
    assert sched._queued_ahead_prev is None
    assert sched._paused_leftover is False
    assert sched._file_chain_lag == 0.0  # it starts on the boundary = on its row

    # its own start timer adopts it: no second push, no skip, no stop
    sched._on_file_start("first", first)
    engine.adopt_queued.assert_called_once()
    assert engine.adopt_queued.call_args.kwargs["skip_current"] is False
    engine.play.assert_not_called()
    engine.stop.assert_not_called()
    assert sched._queued_ahead is None
    assert sched._current_event is first


def test_show_end_clears_a_row_of_the_ending_show_that_is_still_current(end_sched):
    sched, engine, until, arm = end_sched
    arm("first", _file_event(_utc(until), 5))
    sched._current_event = _file_event(_utc(until - 60), 4, instance=1, seconds=60)
    sched._playing_key = "cur"
    sched._current_audio_path = "C:/cache/cur.mp3"
    sched.switch_audio_source(SourceState.SCHEDULED)
    assert sched._queued_ahead[0] == "first"
    assert sched._playing_key is None and sched._current_audio_path is None


@pytest.mark.parametrize("case", ["no row", "row 2 s later", "timer dead", "webstream"])
def test_show_end_without_a_file_row_replaces_the_paused_queue_by_a_silent_filler(end_sched, case):
    import wave

    from rastatime_playout import playout_scheduler as ps

    sched, engine, until, arm = end_sched
    if case == "row 2 s later":
        arm("later", _file_event(_utc(until + 2.0), 7))
    elif case == "timer dead":
        arm("gone", _file_event(_utc(until), 7), alive=False)
    elif case == "webstream":
        arm("ws", SimpleNamespace(start=_utc(until), start_exact=None, show_name="relay"))
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_called_once()
    args, kwargs = engine.replace_paused.call_args
    filler = args[0]
    assert filler.endswith("rt-silence-10s.wav")
    with wave.open(filler, "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (2, 2, 44100)
        assert wav.getnframes() == int(44100 * ps.PAUSED_FILLER_SECONDS)
        assert not any(wav.readframes(4410))
    assert kwargs["queued_ahead"] is False
    # labelled like a jingle, with the show of whatever is armed for that instant
    assert kwargs["metadata"] == {
        "icy_hide": "true",
        "show_name": {"webstream": "relay", "timer dead": "news"}.get(case, ""),
    }
    assert sched._queued_ahead is None
    assert sched._paused_leftover is True
    # the cross buffer (3 s) + the bus transition must fit well inside the filler
    assert ps.PAUSED_FILLER_SECONDS >= sched._cross_buffer_seconds * 2 + 2.0


def test_show_end_falls_back_to_the_filler_when_the_row_cannot_be_queued(end_sched):
    sched, engine, until, arm = end_sched
    arm("first", _file_event(_utc(until), 5))
    engine.replace_paused.side_effect = [False, True]
    sched.switch_audio_source(SourceState.SCHEDULED)
    assert engine.replace_paused.call_count == 2
    assert engine.replace_paused.call_args.kwargs["queued_ahead"] is False
    assert sched._queued_ahead is None and sched._paused_leftover is True


def test_show_end_handover_never_raises_and_needs_a_known_end(end_sched):
    sched, engine, until, arm = end_sched
    arm("first", _file_event(_utc(until), 5))
    engine.replace_paused.side_effect = RuntimeError("boom")
    sched.switch_audio_source(SourceState.SCHEDULED)  # logged, not raised
    assert sched._queued_ahead is None
    # without a known end nothing is replaced
    engine.replace_paused.reset_mock(side_effect=True)
    sched._switcher.show_until = lambda: None
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_not_called()


@pytest.mark.parametrize(
    ("left", "fallback_left", "skip"),
    [
        (7.0, 0.0, True),  # the filler is paused under a live item / still playing
        (0.4, 0.0, False),  # about to end by itself
        (0.0, 0.0, False),  # over: the queue is idle, a skip would hit the track
        (None, 6.0, True),  # the engine cannot be asked: by the clock
        (None, -30.0, False),
    ],
)
def test_first_file_start_after_a_filler_replaces_it(end_sched, left, fallback_left, skip):
    sched, engine, until, arm = end_sched
    sched._paused_leftover = True
    sched._paused_leftover_until = time.monotonic() + fallback_left
    engine.playing_remaining_seconds.return_value = left
    order = MagicMock()
    order.attach_mock(engine.replace_paused, "replace")
    order.attach_mock(engine.adopt_queued, "adopt")
    order.attach_mock(sched._close_predecessor_source, "close")
    row = _file_event(_utc(time.time()), 9)
    sched._on_file_start("row", row)
    engine.replace_paused.assert_called_once()
    assert engine.replace_paused.call_args.kwargs["skip"] is skip
    assert engine.replace_paused.call_args.kwargs["queued_ahead"] is True
    # pushed BEFORE the live predecessor's gate closes
    assert [c[0] for c in order.mock_calls] == ["replace", "adopt", "close"]
    engine.play.assert_not_called()
    engine.stop.assert_not_called()
    assert sched._paused_leftover is False
    # the next start goes the normal way again
    sched._current_event = None
    sched._on_file_start("row2", _file_event(_utc(time.time()), 10))
    engine.play.assert_called_once()


def test_dj_off_resume_cuts_what_was_paused_in_the_queue(end_sched):
    from rastatime_playout.engine.interface import PAUSED_CUT_SHAPE

    sched, engine, until, arm = end_sched
    sched._switcher.last_transition_reason = ""
    row = _file_event(_utc(time.time() - 20), 11, seconds=180)
    sched._current_event, sched._playing_key = row, "row"
    sched._current_audio_path = "C:/cache/a.mp3"
    sched._paused_leftover = True
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_not_called()
    engine.play.assert_called_once()
    assert engine.play.call_args.kwargs["transition"] == PAUSED_CUT_SHAPE
    assert sched._paused_leftover is False


def test_a_hand_over_held_up_past_the_end_resumes_the_row_that_has_started(end_sched):
    from rastatime_playout.engine.interface import PAUSED_CUT_SHAPE

    sched, engine, until, arm = end_sched
    late_until = until - 2.0  # the show ended a second ago, the call was held up
    sched._switcher.show_until = lambda: late_until
    row = _file_event(_utc(late_until), 12)
    sched._current_event, sched._playing_key = row, "row"
    sched._current_audio_path = "C:/cache/a.mp3"
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_not_called()
    engine.play.assert_called_once()
    assert engine.play.call_args.kwargs["transition"] == PAUSED_CUT_SHAPE
    assert engine.play.call_args.kwargs["cue_in"] >= 0.9  # entered where the row is by now
    assert sched._current_event is row
