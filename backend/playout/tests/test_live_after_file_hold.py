"""
RASTATIME 2026-09-29 - a pre-warmed webstream / line-in after a file track
opens its gate when the track's audio is over, and a file track's stop lets
the track run out.

Since the crossfade per track type the rows carry microseconds (a jingle
sequence ends at 08:01:06.78), but event timers fire on the whole second
(08:01:06) and the file chain runs a moment behind the rows.  The relay's
gate opened about one second early and the switch faded the intro's last
second away.  Inside its last BUFFER seconds a track sits in the cross
operator's tail, so the engine cannot be asked how much is left - the end is
computed from the exact row start, the clip and the measured chain lag.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import (
    EventKind,
    FileEvent,
    LineinEvent,
    WebStreamEvent,
)
from libretime_playout.player.schedule import generate_file_events
from libretime_playout.source_switcher import SourceState

SLEEP = "libretime_playout.playout_scheduler.time.sleep"


def _file(start_exact, seconds=6.9, crossfade=0.0, row_id=777, file_id=1, exclude=False):
    start = start_exact.replace(microsecond=0)
    end_exact = start_exact + timedelta(seconds=seconds)
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=end_exact.replace(microsecond=0),
        start_exact=start_exact,
        end_exact=end_exact,
        row_id=row_id,
        id=file_id,
        uri=f"file:///C:/rastatime/scheduler/{file_id}.mp3",
        show_name="bbc",
        track_title="Intro BBC News",
        artist_name="Example Radio",
        mime="audio/mpeg",
        filesize=1,
        cue_in=0.0,
        cue_out=seconds,
        fade_in=0.0,
        fade_out=0.0,
        replay_gain=None,
        crossfade_seconds=crossfade,
        exclude_crossfade=exclude,
    )


def _webstream(start_exact, row_id=888):
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START,
        start=start_exact.replace(microsecond=0),
        end=start_exact.replace(microsecond=0) + timedelta(minutes=5),
        start_exact=start_exact,
        row_id=row_id,
        uri="http://stream.example/bbc",
        id=2,
        show_name="bbc",
    )


def _linein(start_exact, row_id=999):
    return LineinEvent(
        type=EventKind.LINEIN_START,
        start=start_exact.replace(microsecond=0),
        end=start_exact.replace(microsecond=0) + timedelta(minutes=5),
        start_exact=start_exact,
        row_id=row_id,
        id=42,
        show_name="bbc",
        device_id="0fb30b0b-c875-432b-a48f-dbb5208995c9",
        device_name="Tascam 1-2",
        name="Studio",
        channel_mapping=[0, 1],
    )


@pytest.fixture
def sched(monkeypatch):
    from libretime_playout import playout_scheduler as ps

    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.playing_remaining_seconds.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    with patch("libretime_playout.playout_scheduler.FfmpegLineinCapture") as capture_cls:
        capture = MagicMock()
        capture.is_running = True
        capture.listen_url = "http://localhost:8000/linein-capture"
        capture_cls.return_value = capture
        s = ps.PlayoutScheduler(
            engine=engine, api_client=MagicMock(),
            track_crossfade_seconds=3.0, input_transition_seconds=1.0,
        )
    s._switcher = None
    s._ensure_file_cached = MagicMock(return_value=Path("C:/cache/a.mp3"))
    s._notify_media_started = MagicMock()
    s._set_bus_show = MagicMock()
    s._resolve_linein_device = lambda evt: evt.device_id
    return s, engine, capture


def _on_air(s, event, key="f", lag=0.25):
    s._current_event, s._playing_key = event, key
    s._file_chain_lag = lag


def _ending_in(seconds, lag=0.25, **kw):
    """A file track whose audio leaves the air ``seconds`` from now."""
    clip = kw.pop("clip", 6.9)
    start = datetime.utcnow() + timedelta(seconds=seconds - clip - lag)
    return _file(start, seconds=clip, **kw)


# ---------------------------------------------------------------------------
# the end of the audio
# ---------------------------------------------------------------------------

def test_audio_end_is_exact_start_plus_clip_plus_chain_lag(sched):
    s, _, _ = sched
    ev = _file(datetime(2026, 9, 30, 6, 0, 59, 880000), seconds=6.9)
    assert ev.start == datetime(2026, 9, 30, 6, 0, 59)          # timers: whole seconds
    s._file_chain_lag = 0.3
    assert s._file_audio_end(ev) == datetime(2026, 9, 30, 6, 1, 7, 80000)
    s._file_chain_lag = None                                     # nothing measured yet
    assert s._file_audio_end(ev) == datetime(2026, 9, 30, 6, 1, 7, 30000)


def test_audio_end_without_exact_times_falls_back_to_the_whole_second(sched):
    s, _, _ = sched
    ev = _file(datetime(2026, 9, 30, 6, 0, 59, 880000), seconds=6.9).model_copy(
        update={"start_exact": None, "end_exact": None},
    )
    s._file_chain_lag = 0.0
    assert s._file_audio_end(ev) == datetime(2026, 9, 30, 6, 1, 5, 900000)


def test_a_push_onto_the_idle_queue_measures_the_chain_lag(sched):
    s, engine, _ = sched
    ev = _file(datetime.utcnow() - timedelta(seconds=0.2), seconds=9.9)
    s._on_file_start("K", ev)
    engine.play.assert_called_once()
    assert s._file_chain_lag == pytest.approx(0.2, abs=0.15)


def test_a_catch_up_push_counts_its_offset(sched):
    s, engine, _ = sched
    ev = _file(datetime.utcnow() - timedelta(seconds=30.4), seconds=200.0)
    s._on_file_start("K", ev, seek=30.0)
    assert s._file_chain_lag == pytest.approx(0.4, abs=0.15)


def test_a_push_behind_a_playing_file_keeps_the_chain_lag(sched):
    s, engine, _ = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=5), seconds=8.0, row_id=1, file_id=1)
    _on_air(s, prev, key="p", lag=0.3)
    s._on_file_start("n", _file(now, seconds=9.9, row_id=2, file_id=2))
    engine.play.assert_called_once()
    assert s._file_chain_lag == 0.3


def test_generate_file_events_carries_the_exact_times():
    events = {}
    schedule = {
        "id": 6296,
        "starts_at": datetime(2026, 9, 30, 6, 0, 59),
        "ends_at": datetime(2026, 9, 30, 6, 1, 6),
        "starts_at_exact": datetime(2026, 9, 30, 6, 0, 59, 880000),
        "ends_at_exact": datetime(2026, 9, 30, 6, 1, 6, 780000),
        "fade_in": "00:00:00.5", "fade_out": "00:00:00.5",
        "cue_in": "00:00:00", "cue_out": "00:00:06.9",
        "instance": 2001,
    }
    file = {
        "id": 593, "url": None, "track_title": "Intro BBC News", "artist_name": "ExampleFM",
        "mime": "audio/mpeg", "replay_gain": "-9.0", "size": 1,
    }
    prefs = MagicMock(loudness_mode=None, replay_gain_enabled=False, replay_gain_offset=0.0)
    generate_file_events(events, schedule, file, {"name": "BBC"}, prefs)
    (event,) = events.values()
    assert event.start == datetime(2026, 9, 30, 6, 0, 59)
    assert event.start_exact == datetime(2026, 9, 30, 6, 0, 59, 880000)
    assert event.end_exact == datetime(2026, 9, 30, 6, 1, 6, 780000)


# ---------------------------------------------------------------------------
# webstream after a file track
# ---------------------------------------------------------------------------

def test_prewarmed_webstream_waits_for_the_jingle_to_end(sched):
    s, engine, _ = sched
    intro = _ending_in(1.0, crossfade=0.0)
    ws = _webstream(datetime.utcnow())
    _on_air(s, intro)
    s._prepared = ("W", ws)
    order = []
    engine.webstream_gate.side_effect = lambda *_a, **_k: order.append("gate")
    with patch(SLEEP, side_effect=lambda d: order.append(("sleep", d))) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_called_once()
    assert sleep.call_args.args[0] == pytest.approx(1.0, abs=0.1)
    assert order[0][0] == "sleep" and order[-1] == "gate"
    engine.webstream_gate.assert_called_once_with(True)
    assert s._playing_key == "W" and s._current_event is ws


def test_the_overlap_of_the_pair_is_taken_off_the_wait(sched):
    """Music (house value 3 s) into a relay: min(track, show value) = 1 s."""
    s, engine, _ = sched
    song = _ending_in(1.8, crossfade=None, clip=200.0)
    ws = _webstream(datetime.utcnow())
    _on_air(s, song)
    s._prepared = ("W", ws)
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    assert sleep.call_args.args[0] == pytest.approx(0.8, abs=0.1)
    engine.webstream_gate.assert_called_once_with(True)


def test_no_wait_when_the_overlap_covers_what_is_left(sched):
    s, engine, _ = sched
    song = _ending_in(0.9, crossfade=None, clip=200.0)
    ws = _webstream(datetime.utcnow())
    _on_air(s, song)
    s._prepared = ("W", ws)
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_not_called()
    engine.webstream_gate.assert_called_once_with(True)


def test_overbook_starts_the_relay_at_once(sched):
    s, engine, _ = sched
    song = _ending_in(40.0, crossfade=0.0, clip=200.0)
    ws = _webstream(datetime.utcnow())
    _on_air(s, song)
    s._prepared = ("W", ws)
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_not_called()
    engine.stop.assert_called_once()
    engine.webstream_gate.assert_called_once_with(True)


def test_a_cold_webstream_start_does_not_wait(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(1.0))
    ws = _webstream(datetime.utcnow())
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_not_called()
    engine.webstream_start.assert_called_once()


def test_no_wait_after_a_webstream_or_silence(sched):
    s, engine, _ = sched
    ws = _webstream(datetime.utcnow())
    s._prepared = ("W", ws)
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_not_called()
    engine.webstream_gate.assert_called_once_with(True)


def test_no_wait_while_a_dj_is_on_air(sched):
    s, engine, _ = sched
    s._switcher = MagicMock()
    s._switcher.current_state = SourceState.MASTER
    _on_air(s, _ending_in(1.0))
    ws = _webstream(datetime.utcnow())
    s._prepared = ("W", ws)
    with patch(SLEEP) as sleep:
        s._on_webstream_start("W", ws)
    sleep.assert_not_called()
    engine.webstream_gate.assert_not_called()
    assert s._current_event is ws                     # bookkeeping for the resume


def test_superseded_during_the_wait_leaves_the_engine_alone(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(1.0))
    ws = _webstream(datetime.utcnow())
    s._prepared = ("W", ws)

    def taken_over(_seconds):
        s._playing_key = "someone-else"

    with patch(SLEEP, side_effect=taken_over):
        s._on_webstream_start("W", ws)
    engine.stop.assert_not_called()
    engine.webstream_gate.assert_not_called()
    assert s._prepared == ("W", ws)


# ---------------------------------------------------------------------------
# line-in after a file track
# ---------------------------------------------------------------------------

def test_prewarmed_linein_waits_for_the_jingle_to_end(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(0.7))
    li = _linein(datetime.utcnow())
    s._prepared = ("L", li)
    order = []
    engine.linein_gate.side_effect = lambda *_a, **_k: order.append("gate")
    with patch(SLEEP, side_effect=lambda d: order.append(("sleep", d))) as sleep:
        s._on_linein_start("L", li)
    assert sleep.call_args.args[0] == pytest.approx(0.7, abs=0.1)
    assert order[0][0] == "sleep" and order[-1] == "gate"
    engine.linein_gate.assert_called_once_with(True)


def test_superseded_linein_does_not_fall_through_to_a_cold_start(sched):
    s, engine, capture = sched
    _on_air(s, _ending_in(0.7))
    li = _linein(datetime.utcnow())
    s._prepared = ("L", li)

    def taken_over(_seconds):
        s._playing_key = "someone-else"

    with patch(SLEEP, side_effect=taken_over):
        s._on_linein_start("L", li)
    engine.linein_gate.assert_not_called()
    engine.linein_start_http.assert_not_called()
    capture.start.assert_not_called()
    engine.stop.assert_not_called()


# ---------------------------------------------------------------------------
# the stop of a file track
# ---------------------------------------------------------------------------

def test_stop_lets_the_track_run_out(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(0.8), key="f")
    order = []
    engine.stop.side_effect = lambda *_a, **_k: order.append("stop")
    with patch(SLEEP, side_effect=lambda d: order.append(("sleep", d))) as sleep:
        s._on_stop("f")
    assert sleep.call_args.args[0] == pytest.approx(0.8, abs=0.1)
    assert order[0][0] == "sleep"
    assert order[-1] == "stop"
    assert s._playing_key is None and s._current_event is None


def test_stop_yields_to_the_item_that_took_over_meanwhile(sched):
    s, engine, _ = sched
    intro = _ending_in(0.8)
    _on_air(s, intro, key="f")
    ws = _webstream(datetime.utcnow())

    def relay_starts(_seconds):
        s._playing_key, s._current_event = "W", ws

    with patch(SLEEP, side_effect=relay_starts):
        s._on_stop("f")
    engine.stop.assert_not_called()
    assert s._playing_key == "W" and s._current_event is ws


def test_stop_of_a_track_that_is_over_does_not_wait(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(-2.0), key="f")
    with patch(SLEEP) as sleep:
        s._on_stop("f")
    sleep.assert_not_called()
    assert s._playing_key is None


def test_stop_of_an_overrunning_track_cuts_at_once(sched):
    s, engine, _ = sched
    _on_air(s, _ending_in(30.0, clip=200.0), key="f")
    with patch(SLEEP) as sleep:
        s._on_stop("f")
    sleep.assert_not_called()
    engine.stop.assert_called_once()


def test_stop_of_a_webstream_does_not_wait(sched):
    s, engine, _ = sched
    ws = _webstream(datetime.utcnow() - timedelta(minutes=5))
    s._current_event, s._playing_key = ws, "W"
    with patch(SLEEP) as sleep:
        s._on_stop("W")
    sleep.assert_not_called()
