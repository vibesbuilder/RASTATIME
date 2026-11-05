"""
RASTATIME 2026-11-05 - the 10:30 incident (manual Liquidsoap restart right
after PLAYOUT's planned one): a queue-ahead landed in the fresh instance,
the restart detector assumed "plays nothing" 84 s later and re-armed the
same track as a catch-up behind it.  Three guards:

  1. the telnet reconnect runs the restart detector within a second;
  2. the detector adopts the running request when it IS the believed item;
  3. PLAY cuts to the row when the engine's remaining fits neither the
     predecessor nor the successor (stale file chain).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
from rastatime_playout.player.events import EventKind, FileEvent

# ---- helpers ---------------------------------------------------------------


def _file(now, n, *, seconds=180, instance=1, start_offset=0.0):
    start = now + timedelta(seconds=start_offset)
    return FileEvent(
        type=EventKind.FILE,
        row_id=n,
        start=start,
        end=start + timedelta(seconds=seconds),
        uri=f"file:///C:/stor/{n}.mp3",
        id=n,
        show_name="show",
        fade_in=0.0,
        fade_out=0.0,
        cue_in=0.0,
        cue_out=float(seconds),
        track_title=f"track {n}",
        artist_name="a",
        mime="audio/mpeg",
        replay_gain=None,
        filesize=1000,
        instance_id=instance,
    )


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    engine.enqueue.return_value = True
    engine.playing_remaining_seconds.return_value = None
    s = ps.PlayoutScheduler(
        engine=engine,
        api_client=MagicMock(),
        input_transition_seconds=1.0,
        track_crossfade_seconds=2.0,
    )
    s.reset_gates = MagicMock()
    s._switcher = None
    s._ensure_file_cached = MagicMock(return_value=Path("C:/cache/a.mp3"))
    s._notify_media_started = MagicMock()
    s._set_bus_show = MagicMock()
    return s, engine


# ---- 1. telnet reconnect hook ---------------------------------------------


def test_telnet_reconnect_fires_listener_once_per_reconnect(monkeypatch):
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=1)
    fired = []
    client.set_reconnect_listener(lambda: fired.append(1))

    class DeadSocket:
        def sendall(self, _):
            raise OSError("peer closed")

    class LiveSocket:
        def sendall(self, _):
            return None

    sockets = iter([LiveSocket()])

    def connect_locked():
        client._socket = next(sockets)

    monkeypatch.setattr(client, "_connect_locked", connect_locked)
    monkeypatch.setattr(client, "_close_locked", lambda **kw: setattr(client, "_socket", None))
    monkeypatch.setattr(client, "_read_until_end_locked", lambda: "Done")
    client._socket = DeadSocket()

    assert client.send_command("uptime") == "Done"
    assert client.reconnects == 1
    # the listener runs on a daemon timer thread
    import time

    for _ in range(50):
        if fired:
            break
        time.sleep(0.01)
    assert fired == [1]
    # a plain command on the live socket is not a reconnect
    assert client.send_command("uptime") == "Done"
    assert client.reconnects == 1


def test_scheduler_registers_reconnect_listener_and_refreshes_on_restart(sched, monkeypatch):
    s, engine = sched
    engine.set_reconnect_listener.assert_called_once()
    listener = engine.set_reconnect_listener.call_args.args[0]
    assert listener == s._on_engine_reconnected

    timers = []

    class FakeTimer:
        def __init__(self, delay, fn, args=(), kwargs=None):
            self.delay, self.fn, self.args = delay, fn, args
            self.daemon = False
            timers.append(self)

        def start(self):
            return None

        def cancel(self):
            return None

    monkeypatch.setattr(ps.threading, "Timer", FakeTimer)
    s._maybe_reinit_after_liquidsoap_restart = MagicMock(return_value=True)
    s._schedule_refresh_soon = MagicMock()

    s._on_engine_reconnected()
    assert timers and timers[-1].delay == 1.0
    timers[-1].fn()
    s._maybe_reinit_after_liquidsoap_restart.assert_called_once()
    s._schedule_refresh_soon.assert_called_once()
    # rate limit: a second reconnect right away does not schedule another check
    n = len(timers)
    s._on_engine_reconnected()
    assert len(timers) == n


# ---- 2. adopt the running request instead of a catch-up copy ---------------


def test_restart_detector_adopts_the_running_item(sched):
    s, engine = sched
    now = datetime.utcnow()
    cur = _file(now - timedelta(seconds=75), 1, seconds=353)
    s._current_event, s._playing_key = cur, "k1"
    s._current_started_at = now - timedelta(seconds=75)
    s._current_clip_seconds = 353.0
    engine.running_after_restart.return_value = {
        "rid": "0",
        "remaining": 278.0,
        "filename": "C:/stor/1.mp3",
        "uri_match": True,
    }

    s._forget_current_after_restart("Liquidsoap restarted")

    engine.adopt_running.assert_called_once_with("0")
    engine.forget_playback_state.assert_not_called()
    assert s._current_event is cur and s._playing_key == "k1"
    assert s._current_started_at is not None


def test_restart_detector_adopts_on_timing_when_metadata_has_no_file(sched):
    s, engine = sched
    now = datetime.utcnow()
    cur = _file(now - timedelta(seconds=75), 1, seconds=353)
    s._current_event, s._playing_key = cur, "k1"
    s._current_started_at = now - timedelta(seconds=75)
    s._current_clip_seconds = 353.0
    engine.running_after_restart.return_value = {
        "rid": "0",
        "remaining": 277.0,  # rows expect 278 s
        "filename": None,
        "uri_match": None,
    }
    s._forget_current_after_restart("Liquidsoap restarted")
    engine.adopt_running.assert_called_once_with("0")
    assert s._current_event is cur


def test_restart_detector_still_rearms_when_the_fresh_instance_plays_nothing(sched):
    s, engine = sched
    now = datetime.utcnow()
    cur = _file(now - timedelta(seconds=75), 1, seconds=353)
    s._current_event, s._playing_key = cur, "k1"
    s._current_started_at = now - timedelta(seconds=75)
    s._current_clip_seconds = 353.0
    engine.running_after_restart.return_value = None

    s._forget_current_after_restart("Liquidsoap restarted")

    engine.adopt_running.assert_not_called()
    engine.forget_playback_state.assert_called_once()
    assert s._current_event is None and s._playing_key is None


def test_restart_detector_rearms_when_another_file_plays(sched):
    s, engine = sched
    now = datetime.utcnow()
    cur = _file(now - timedelta(seconds=75), 1, seconds=353)
    s._current_event, s._playing_key = cur, "k1"
    s._current_started_at = now - timedelta(seconds=75)
    s._current_clip_seconds = 353.0
    engine.running_after_restart.return_value = {
        "rid": "3",
        "remaining": 40.0,
        "filename": "C:/stor/other.mp3",
        "uri_match": False,
    }
    s._forget_current_after_restart("Liquidsoap restarted")
    engine.adopt_running.assert_not_called()
    assert s._current_event is None


def test_engine_running_after_restart_reads_rid_and_file():
    telnet = MagicMock(spec=LiquidsoapTelnetClient)
    telnet._host, telnet._port = "127.0.0.1", 1234
    telnet.request_queue_remaining.return_value = "0 278.4\nEND"
    telnet.request_metadata.return_value = (
        'filename="D:/stor/imported/Ja, Panik/09 - Transatlantic Love Affair.mp3"\n'
        'initial_uri="annotate:...:file:///D:/stor/imported/Ja, Panik/09 - Transatlantic Love Affair.mp3"\n'
        "END"
    )
    eng = LiquidsoapPlayoutEngine(telnet_client=telnet)
    eng._current_uri = "D:\\stor\\imported\\Ja, Panik\\09 - Transatlantic Love Affair.mp3"
    snap = eng.running_after_restart()
    assert snap == {
        "rid": "0",
        "remaining": pytest.approx(278.4),
        "filename": "D:/stor/imported/Ja, Panik/09 - Transatlantic Love Affair.mp3",
        "uri_match": True,
    }
    eng.adopt_running("0")
    assert eng._current_request_id == "0"
    assert eng.get_state() == PlayoutState.PLAYING
    telnet.request_queue_flush.assert_called_once()
    # nothing playing -> None
    telnet.request_queue_remaining.return_value = "-1"
    assert eng.running_after_restart() is None


# ---- 3. clock sanity in PLAY -----------------------------------------------


def test_play_cuts_a_stale_chain_when_remaining_fits_neither_track(sched):
    """11:00:00: 'World News' (late copy, 265 s left) before a 9.9 s jingle."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=268), 1, seconds=270, instance=1)  # rows: 2 s left
    jingle = _file(now, 2, seconds=10, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._current_started_at = now - timedelta(seconds=268)
    s._current_clip_seconds = 270.0
    s._queued_ahead, s._queued_ahead_prev = ("j", jingle), prev
    engine.playing_remaining_seconds.return_value = 265.2

    s._on_file_start("j", jingle)

    assert engine.adopt_queued.call_args.kwargs["skip_current"] is True


def test_play_keeps_trusting_the_queue_when_remaining_fits_the_successor(sched):
    """20:05:35 case: the remaining belongs to the successor cross pulled."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=178), 1, seconds=180, instance=1)
    nxt = _file(now, 2, seconds=240, instance=1)
    s._current_event, s._playing_key = prev, "p"
    s._current_started_at = now - timedelta(seconds=178)
    s._current_clip_seconds = 180.0
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    engine.playing_remaining_seconds.return_value = 214.9  # < 240 + buffer: the successor

    s._on_file_start("n", nxt)

    assert engine.adopt_queued.call_args.kwargs["skip_current"] is False
