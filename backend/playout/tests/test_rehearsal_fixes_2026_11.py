"""
RASTATIME 2026-11-02 - fixes from the fresh-machine install rehearsal
(docs/operator/INSTALL_PROBE.md §5, product findings 2, 3, 6, 9, 11, 12):

* an unplanned Liquidsoap restart re-arms the running item (finding 2)
* Main Output "Off" renders no output.portaudio (finding 3)
* output.icecast reports connect / error to PLAYOUT -> web app (finding 6)
* no restart attempt for a Liquidsoap service that is not installed
  (finding 9, see test_liquidsoap_service.py)
* the no-harbor render answers the probe with "none" (finding 11)
* stereo() instead of the deprecated audio_to_stereo, no duplicate
  flush_and_skip registration (finding 12)
"""

from __future__ import annotations

from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from rastatime_playout import liquidsoap_config as lc
from rastatime_playout import liquidsoap_health as lh
from rastatime_playout import playout_scheduler as ps
from rastatime_playout import source_switcher as ss
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.source_switcher import SourceSwitcher
from rastatime_playout.stream_status import StreamStatusReporter

MAIN_SCRIPT = "C:\\Tools\\liquidsoap\\rastatime.liq"


def _stream(**over):
    base = {
        "type": "mp3",
        "host": "localhost",
        "port": 8000,
        "mount": "rastatime",
        "pass": "hackme",
        "user": "source",
        "bitrate": 128,
        "name": "RASTATIME",
        "description": "Live stream",
    }
    base.update(over)
    return base


def _active(rendered: str) -> str:
    return "\n".join(ln for ln in rendered.splitlines() if not ln.lstrip().startswith("#"))


# ---- finding 6: output.icecast callbacks -----------------------------------------------


def test_icecast_outputs_are_bound_and_report_to_playout():
    out = _active(lc.render_rastatime_liq([_stream(stream_id=2), _stream(mount="aac", type="aac")]))
    assert "def rastatime_stream_event(n, status, message) =" in out
    assert '"http://127.0.0.1:8770/stream-event?stream=#{n}&status=#{status}"' in out
    # stream_id wins over the position; the second dict falls back to its position
    assert "rt_stream_2 = output.icecast(" in out
    assert (
        'rt_stream_2.on_connect(synchronous=false, fun () ->\n  rastatime_stream_event(2, "ok"'
        in out
    )
    assert "rt_stream_2.on_error(synchronous=false, fun (~restart_in, err) ->" in out
    assert 'rastatime_stream_event(2, "error", "#{err}")' in out
    assert "restart_in(3.)" in out
    assert "rt_stream_2 = output.icecast(" in out and "rt_stream_1 = output.icecast(" not in out
    assert "rt_stream_2.on_error" in out


def test_icecast_outputs_without_status_url_render_plain_blocks():
    out = _active(lc.render_rastatime_liq([_stream()], stream_status_url=None))
    assert "rastatime_stream_event" not in out
    assert "rt_stream_" not in out
    assert "output.icecast(" in out
    # the standby script never reports (its outputs are the silence fallbacks)
    standby = lc.render_standby_liq([_stream()])
    assert "rastatime_stream_event" not in standby


# ---- finding 3: Main Output "Off" ---------------------------------------------------------


def test_main_output_off_renders_no_portaudio_and_the_marker():
    out = lc.render_rastatime_liq(
        [_stream()], local_output_enabled=False, local_output_endpoint_id="none"
    )
    assert "output.portaudio(" not in _active(out)
    assert "# rastatime-main-output: none" in out
    assert "Main Output set to Off" in out
    # the machine variable still disables it, with the same marker
    env_off = lc.render_rastatime_liq([_stream()], local_output_enabled=False)
    assert "# rastatime-main-output: none" in env_off
    assert "RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false" in env_off


# ---- finding 12: deprecated audio_to_stereo, duplicate flush_and_skip ------------------


def test_render_uses_stereo_and_registers_flush_and_skip_once():
    out = lc.render_rastatime_liq([_stream()], linein_enabled=True)
    assert "audio_to_stereo(" not in out
    assert "linein_dshow = stereo(linein_raw)" in out
    # the stdlib registers scheduled.flush_and_skip itself (telnet.liq)
    assert '"flush_and_skip"' not in _active(out)


# ---- finding 11: no harbor configured answers the probe with "none" --------------------


def test_no_harbor_render_registers_the_probe_with_none():
    out = _active(lc.render_rastatime_liq([_stream()]))  # no harbor passwords
    assert (
        'server.register(namespace="rastatime", description="Harbor source events rendered (option d)",'
        in out
    )
    assert '"source_events", fun (_) -> "none")' in out


def test_probe_distinguishes_on_none_and_absent():
    def client(reply):
        c = MagicMock()
        c.send_command.return_value = reply
        return c

    assert ss._probe_source_events(client("on")) == "on"
    assert ss._probe_source_events(client("none\n")) == "none"
    assert ss._probe_source_events(client("ERROR: unknown command")) == "absent"
    assert ss._source_events_present(client("none")) is True
    assert ss._source_events_present(client("ERROR: unknown command")) is False


def test_loop_logs_no_harbor_once_at_info(monkeypatch, caplog):
    sw = SourceSwitcher(switch_callback=lambda _s: None)
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: (
        "none" if cmd == ss.SOURCE_EVENTS_PROBE else "no source client connected"
    )
    monkeypatch.setattr(ss, "LiquidsoapTelnetClient", lambda **_kw: client, raising=False)
    import rastatime_playout.engine.liquidsoap_telnet as lt  # noqa: PLC0415

    monkeypatch.setattr(lt, "LiquidsoapTelnetClient", lambda **_kw: client)
    monkeypatch.setattr(sw, "wait_reconcile", lambda _t: False)
    with caplog.at_level("INFO"):
        ss._liquidsoap_state_poll_loop(sw, interval_s=60.0, settle_s=0.0, max_ticks=3)
    infos = [r for r in caplog.records if "has no DJ harbor" in r.getMessage()]
    warns = [r for r in caplog.records if "older render" in r.getMessage()]
    assert len(infos) == 1 and infos[0].levelname == "INFO"
    assert warns == []


# ---- finding 6: /stream-event listener + reporter ----------------------------------------


@pytest.fixture
def handler():
    h = ss._EventHandler.__new__(ss._EventHandler)
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    h.headers = {}
    h.rfile = MagicMock()
    return h, sent


def test_stream_event_endpoint_forwards_to_the_reporter(handler, monkeypatch):
    h, sent = handler
    reporter = MagicMock()
    monkeypatch.setattr(ss._EventHandler, "stream_status", reporter)
    h._handle_stream_event(
        urlparse("/stream-event?stream=1&status=error&message=Connection%20failed%3A%20401")
    )
    assert sent[-1] == (200, "ok")
    reporter.report.assert_called_once_with(1, "error", "Connection failed: 401")
    h._handle_stream_event(urlparse("/stream-event?stream=x&status=ok"))
    assert sent[-1][0] == 400
    monkeypatch.setattr(ss._EventHandler, "stream_status", None)
    h._handle_stream_event(urlparse("/stream-event?stream=1&status=ok"))
    assert sent[-1] == (503, "error")


def test_reporter_dedups_and_posts_ok_or_the_message():
    posts = []
    rep = StreamStatusReporter(
        post=lambda msg, sid, boot: posts.append((msg, sid, boot)), threaded=False
    )
    assert rep.report(1, "error", "Connection failed:  401, Authentication Required") is True
    assert (
        rep.report(1, "error", "Connection failed: 401, Authentication Required") is False
    )  # repeat
    assert rep.report(1, "ok", "connected") is True
    assert rep.report(2, "ok", "") is True
    assert rep.report(7, "bogus", "") is False
    assert rep.report("n/a", "ok", "") is False
    assert posts == [
        ("Connection failed: 401, Authentication Required", "s1", None),
        ("OK", "s1", None),
        ("OK", "s2", None),
    ]
    assert rep.last(1) == "OK"


def test_reporter_uses_the_legacy_client_and_survives_failures():
    client = MagicMock()
    client.update_liquidsoap_status.side_effect = RuntimeError("web app down")
    rep = StreamStatusReporter(client, threaded=False)
    assert rep.report(3, "error", "x") is True  # logged, not raised
    client.update_liquidsoap_status.assert_called_once_with("x", "s3", None)


# ---- finding 2: unplanned restart re-arms the running item --------------------------------


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    table = {"infos": []}
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: table["infos"])
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock())
    s.reset_gates = MagicMock()
    s.set_source_switcher(SourceSwitcher(switch_callback=lambda _state: None))
    return s, engine, table


def test_process_restart_forgets_the_running_item_so_the_refresh_re_arms_it(sched, caplog):
    s, engine, table = sched
    table["infos"] = [lh.ProcessInfo(14516, 100.0, 300.0, MAIN_SCRIPT)]
    s._maybe_reinit_after_liquidsoap_restart()  # seeds
    event = MagicMock()
    event.track_title = "Fade"
    s._playing_key = "row-1"
    s._current_event = event
    s._current_started_at = object()
    s._current_clip_seconds = 180.0
    s._prepared = ("row-2", MagicMock())
    table["infos"] = [lh.ProcessInfo(15000, 100.0, 12.0, MAIN_SCRIPT)]  # fresh pid
    with caplog.at_level("WARNING"):
        s._maybe_reinit_after_liquidsoap_restart()
    assert s._playing_key is None and s._current_event is None
    assert s._prepared is None and s._current_started_at is None
    assert s._current_clip_seconds is None
    assert any("re-arming 'Fade' as a catch-up" in r.getMessage() for r in caplog.records)


def test_uptime_restart_forgets_the_running_item_too(sched, monkeypatch):
    s, engine, table = sched
    table["infos"] = []  # no process table -> uptime fallback
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: None)
    s._liquidsoap_process_identity = lambda: None
    s._last_liquidsoap_uptime = 1000.0
    s._playing_key = "row-1"
    s._current_event = MagicMock()
    engine.liquidsoap_uptime_seconds.return_value = 20.0
    s._maybe_reinit_after_liquidsoap_restart()
    assert s._playing_key is None and s._current_event is None


def test_same_instance_keeps_the_running_item(sched):
    s, engine, table = sched
    table["infos"] = [lh.ProcessInfo(14516, 100.0, 300.0, MAIN_SCRIPT)]
    s._maybe_reinit_after_liquidsoap_restart()
    s._playing_key = "row-1"
    table["infos"] = [lh.ProcessInfo(14516, 100.0, 420.0, MAIN_SCRIPT)]
    s._maybe_reinit_after_liquidsoap_restart()
    assert s._playing_key == "row-1"


def test_file_start_logs_an_unexpected_error_instead_of_dying_silently(sched, caplog):
    s, _engine, _table = sched
    s._on_file_start_impl = MagicMock(side_effect=RuntimeError("boom"))
    s._queue_deferred_ahead = MagicMock()
    with caplog.at_level("ERROR"):
        s._on_file_start("row-9", MagicMock(start=None), 0.0)
    assert any(
        "PLAY  row-9 failed with an unexpected error" in r.getMessage() for r in caplog.records
    )
    assert "row-9" not in s._starting


# ---- finding 2, root cause from the VM log: the engine's state mirror -------------------


def _engine_with_telnet():
    telnet = MagicMock()
    telnet.request_queue_push.return_value = "12"
    telnet.request_queue_skip.return_value = "OK"
    telnet.request_queue_flush.return_value = "OK"
    telnet.var_set.return_value = "OK"
    return LiquidsoapPlayoutEngine(telnet_client=telnet), telnet


def test_engine_forget_playback_state_defeats_the_idempotent_shortcut():
    """
    02:28:41 push -> dying instance; 02:30:57 catch-up stop()+play(same
    file) returned without a push ("idempotent re-issue").  After the
    restart the mirror is dropped and the same file is pushed again.
    """
    engine, telnet = _engine_with_telnet()
    engine.play("C:/m/a.mp3", cue_in=520.9)
    assert telnet.request_queue_push.call_count == 1
    engine.stop()
    engine.play("C:/m/a.mp3", cue_in=657.9)  # the old behaviour: shortcut, no push
    assert telnet.request_queue_push.call_count == 1
    engine.forget_playback_state("Liquidsoap restarted")
    assert engine.get_state() == PlayoutState.STOPPED
    engine.stop()
    engine.play("C:/m/a.mp3", cue_in=700.0)
    assert telnet.request_queue_push.call_count == 2  # pushed afresh


def test_restart_paths_drop_the_engine_mirror(sched, monkeypatch):
    s, engine, table = sched
    # unplanned (process table)
    table["infos"] = [lh.ProcessInfo(14516, 100.0, 300.0, MAIN_SCRIPT)]
    s._maybe_reinit_after_liquidsoap_restart()
    table["infos"] = [lh.ProcessInfo(15000, 100.0, 12.0, MAIN_SCRIPT)]
    s._maybe_reinit_after_liquidsoap_restart()
    engine.forget_playback_state.assert_called_once()
    # planned
    engine.forget_playback_state.reset_mock()
    refreshed = []
    monkeypatch.setattr(s, "_schedule_refresh_soon", lambda why, delay=1.0: refreshed.append(why))
    s._after_liquidsoap_restart(attempts=1, delay=0.0)
    engine.forget_playback_state.assert_called_once()
    assert refreshed == ["Planned Liquidsoap restart"]


def test_reconnect_hook_fires_once_per_connect_and_refreshes_soon():
    """Studio probe 12:10: the outputs reconnected 68 s before the poll noticed."""
    hooked = []
    rep = StreamStatusReporter(post=lambda *_a: None, threaded=False, on_reconnect=hooked.append)
    assert rep.report(1, "ok", "") is True
    assert rep.report(1, "ok", "") is False  # repeat: no second hook
    assert rep.report(1, "error", "401") is True
    assert rep.report(1, "ok", "") is True  # reconnect after an error
    assert hooked == [1, 1]


def test_request_refresh_soon_coalesces_and_runs_refresh(sched, monkeypatch):
    s, _engine, _table = sched
    runs = []
    monkeypatch.setattr(s, "refresh", lambda: runs.append(1))
    timers = []

    class FakeTimer:
        def __init__(self, delay, fn):
            timers.append((delay, fn))
            self.daemon = False

        def start(self):
            pass

    monkeypatch.setattr(ps.threading, "Timer", FakeTimer)
    s.request_refresh_soon("stream 1 reconnected")
    s.request_refresh_soon("stream 2 reconnected")  # folded into the pending one
    s.request_refresh_soon("stream 3 reconnected")
    assert len(timers) == 1 and timers[0][0] == 2.0
    timers[0][1]()  # the timer fires
    assert runs == [1]
    s.request_refresh_soon("again")  # a new one is accepted afterwards
    assert len(timers) == 2
