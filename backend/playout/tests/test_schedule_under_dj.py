"""
RASTATIME 2026-11-19 - the schedule keeps running under a DJ (trial switch
``RASTATIME_SCHEDULE_UNDER_DJ``, stage 1: file rows).

Before: the bus does not pull an arm it has not selected, so under a DJ the
request queue stood still and PLAYOUT held every file row back; the hand-back
re-entered the programme with an offset and had to get rid of the track that
was paused at the take-over (2026-11-18).

With the switch the rendered script carries a silent second consumer of the
scheduled chain that pulls it exactly while a DJ arm holds the bus, and the
scheduler treats file rows under a DJ like any other: start, queue-ahead,
exact-time waits, stop.  The hand-back (DJ off, show end) only checks that
the queue is where the rows say and falls back to the paused-queue paths when
it is not.  Webstream and line-in rows are held back as before.

Without the switch nothing changes - the rendered script is byte-identical.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rastatime_playout import liquidsoap_config as lc
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PAUSED_CUT_SHAPE, PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.player.events import EventKind, FileEvent, LineinEvent, WebStreamEvent
from rastatime_playout.source_switcher import REASON_SHOW_END, SourceState

# ---- the switch -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "on"),
    [
        (None, False),
        ("", False),
        ("0", False),
        ("off", False),
        ("1", True),
        ("true", True),
        (" On ", True),
        ("yes", True),
    ],
)
def test_the_switch_is_off_unless_the_environment_says_so(monkeypatch, value, on):
    if value is None:
        monkeypatch.delenv(lc.SCHEDULE_UNDER_DJ_ENV, raising=False)
    else:
        monkeypatch.setenv(lc.SCHEDULE_UNDER_DJ_ENV, value)
    assert lc.schedule_under_dj_enabled() is on


# ---- the rendered script --------------------------------------------------

_SHOW_HOLD = (
    "source.is_ready(show_dj) and time() >= show_dj_from()"
    " and (show_dj_until() <= 0. or time() < show_dj_until())"
)


def _bus(**kw):
    base = {
        "main_enabled": True,
        "show_enabled": True,
        "webstream_enabled": True,
        "linein_enabled": True,
        "transition_seconds": 1.0,
        "dj_fade_seconds": 1.0,
        "show_hold": True,
    }
    base.update(kw)
    return lc._render_bus_source_block(**base)


def test_without_the_switch_the_bus_block_is_what_it_was():
    off = _bus()
    assert _bus(schedule_under_dj=False) == off
    assert "scheduled_under_dj" not in off and "bus_dj_on_air" not in off
    # the show arm still reads exactly as before the refactoring
    assert "({" + _SHOW_HOLD + "}, show_dj)" in off


def test_with_the_switch_a_silent_consumer_pulls_the_chain_while_a_dj_arm_holds_the_bus():
    off, on = _bus(), _bus(schedule_under_dj=True)
    assert on.startswith(off)  # the bus itself is untouched
    extra = on[len(off) :]
    assert (
        "def bus_dj_on_air() =\n"
        "  (source.is_ready(master_dj)) or (" + _SHOW_HOLD + ")\n"
        "end\n"
        'scheduled_under_dj = switch(id="scheduled_under_dj_gate", track_sensitive=false,\n'
        "  [(bus_dj_on_air, scheduled)])\n"
        'output.dummy(id="scheduled_under_dj", fallible=true, scheduled_under_dj)\n'
    ) in extra
    # nothing but comments around it
    code = [ln for ln in extra.splitlines() if ln.strip() and not ln.startswith("#")]
    assert len(code) == 6


@pytest.mark.parametrize(
    ("kw", "condition"),
    [
        ({"show_enabled": False}, "(source.is_ready(master_dj))"),
        ({"main_enabled": False}, "(" + _SHOW_HOLD + ")"),
        ({"main_enabled": False, "show_hold": False}, "(source.is_ready(show_dj))"),
    ],
)
def test_the_consumer_uses_the_conditions_of_the_dj_arms_that_exist(kw, condition):
    on = _bus(schedule_under_dj=True, **kw)
    assert "def bus_dj_on_air() =\n  " + condition + "\nend\n" in on


def test_no_dj_arm_no_consumer():
    kw = {"main_enabled": False, "show_enabled": False}
    assert _bus(schedule_under_dj=True, **kw) == _bus(**kw)
    assert "scheduled_under_dj" not in _bus(schedule_under_dj=True, **kw)


def test_the_full_render_carries_the_switch_through():
    stream = {
        "type": "mp3",
        "host": "localhost",
        "port": 8000,
        "mount": "/main",
        "pass": "hackme",
        "bitrate": 128,
    }
    kw = {"harbor_main_password": "m", "harbor_show_password": "s"}
    off = lc.render_rastatime_liq([stream], **kw)
    on = lc.render_rastatime_liq([stream], schedule_under_dj=True, **kw)
    assert lc.render_rastatime_liq([stream], schedule_under_dj=False, **kw) == off
    assert 'output.dummy(id="scheduled_under_dj"' not in off
    assert on.count('output.dummy(id="scheduled_under_dj", fallible=true, scheduled_under_dj)') == 1
    # the consumer sits behind the bus switch and in front of the outputs' chain
    assert on.index("bus = switch(") < on.index("def bus_dj_on_air()")
    # everything else is identical
    a, b = (
        on.index("\n# RASTATIME 2026-11-19 - the schedule keeps running under a DJ"),
        on.index('output.dummy(id="scheduled_under_dj", fallible=true, scheduled_under_dj)\n')
        + len('output.dummy(id="scheduled_under_dj", fallible=true, scheduled_under_dj)\n'),
    )
    assert on[:a] + on[b:] == off


# ---- the scheduler --------------------------------------------------------


def _file(start, row_id, *, seconds=180, instance=2):
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=seconds),
        row_id=row_id,
        id=row_id,
        uri="C:/media/a.mp3",
        show_name="live show",
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


def _webstream(start, row_id, *, seconds=300):
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START,
        start=start,
        end=start + timedelta(seconds=seconds),
        row_id=row_id,
        id=row_id,
        uri="http://example.invalid/stream",
        show_name="relay",
    )


def _make(monkeypatch, tmp_path, *, under_dj=True, state=SourceState.SHOW, reason=""):
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.replace_paused.return_value = True
    engine.enqueue.return_value = True
    engine.playing_remaining_seconds.return_value = None
    sched = ps.PlayoutScheduler(
        engine=engine,
        api_client=MagicMock(),
        cache_dir=tmp_path,
        input_transition_seconds=1.0,
        track_crossfade_seconds=3.0,
        schedule_under_dj=under_dj,
    )
    sched._ensure_file_cached = MagicMock(return_value=Path("C:/cache/a.mp3"))
    sched._notify_media_started = MagicMock()
    sched._set_bus_show = MagicMock()
    until = float(int(time.time()) + 1)
    sched.set_source_switcher(
        SimpleNamespace(
            last_transition_reason=reason,
            current_state=state,
            show_until=lambda: until,
        )
    )
    engine.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING
    return sched, engine


@pytest.fixture
def make(monkeypatch, tmp_path):
    def _factory(**kw):
        return _make(monkeypatch, tmp_path, **kw)

    return _factory


def _on_air(sched, event, key="cur"):
    sched._current_event, sched._playing_key = event, key
    sched._current_audio_path = "C:/cache/a.mp3"
    sched._current_started_at = datetime.utcnow()


def _queue_value(sched, event):
    """What ``scheduled.remaining`` reports for a row that runs in step."""
    left = (sched._file_audio_end(event) - datetime.utcnow()).total_seconds()
    return max(0.0, left - sched._cross_buffer_seconds)


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_file_row_starts_under_a_dj_only_with_the_switch(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    row = _file(datetime.utcnow(), 1)
    sched._on_file_start("row", row)
    assert sched._current_event is row  # book-kept either way
    sched._notify_media_started.assert_called_once_with(1)
    if under_dj:
        engine.play.assert_called_once()
        assert engine.play.call_args.kwargs["metadata"]["title"] == "t1"
    else:
        engine.play.assert_not_called()
        engine.stop.assert_not_called()


@pytest.mark.parametrize("under_dj", [True, False])
def test_the_next_file_row_is_queued_ahead_under_a_dj_only_with_the_switch(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    now = datetime.utcnow()
    _on_air(sched, _file(now - timedelta(seconds=170), 1))
    nxt = _file(now + timedelta(seconds=8), 2)
    sched._on_file_queue_ahead("next", nxt)
    if under_dj:
        engine.enqueue.assert_called_once()
        assert sched._queued_ahead == ("next", nxt)
    else:
        engine.enqueue.assert_not_called()
        assert sched._queued_ahead is None


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_file_row_ends_in_the_unheard_chain_only_with_the_switch(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    _on_air(sched, _file(datetime.utcnow() - timedelta(seconds=200), 1))
    sched._on_stop("cur")
    assert sched._current_event is None  # book-kept either way
    assert engine.stop.called is under_dj


def _linein(start, row_id, *, seconds=300):
    return LineinEvent(
        type=EventKind.LINEIN_START,
        start=start,
        end=start + timedelta(seconds=seconds),
        row_id=row_id,
        id=row_id,
        show_name="studio",
        device_id="dev-1",
        device_name="Studio",
        name="studio",
        channel_mapping=[0, 1],
    )


def _wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# RASTATIME 2026-11-21 - a live row that ENDS under a DJ releases its source
# (before it stayed open, and a DJ leaving into a gap would have brought the
# ended webstream / line-in back on air).  With and without the switch.
@pytest.mark.parametrize("under_dj", [True, False])
@pytest.mark.parametrize("state", [SourceState.SHOW, SourceState.MASTER])
def test_a_webstream_row_that_ends_under_a_dj_releases_its_source(make, under_dj, state):
    sched, engine = make(under_dj=under_dj, state=state)
    sched._drain_seconds = 0.01
    _on_air(sched, _webstream(datetime.utcnow() - timedelta(seconds=400), 3))
    sched._on_stop("cur")
    assert sched._current_event is None and sched._playing_key is None
    engine.webstream_gate.assert_called_once_with(False)
    assert _wait_for(lambda: engine.webstream_stop.called)
    engine.stop.assert_not_called()  # the request queue is not touched


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_linein_row_that_ends_under_a_dj_releases_its_source(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    sched._drain_seconds = 0.01
    capture = MagicMock()
    sched._linein_capture = capture
    _on_air(sched, _linein(datetime.utcnow() - timedelta(seconds=400), 4))
    sched._on_stop("cur")
    assert sched._current_event is None
    engine.linein_gate.assert_called_once_with(False)
    assert _wait_for(lambda: engine.linein_stop.called)
    capture.stop.assert_called_once()
    engine.stop.assert_not_called()


def test_a_webstream_released_under_a_dj_spares_a_newer_one(make):
    # the drained stop belongs to the released stream only: a stream started
    # in the meantime (the DJ left at once) keeps running
    sched, engine = make()
    sched._drain_seconds = 0.2
    _on_air(sched, _webstream(datetime.utcnow() - timedelta(seconds=400), 3))
    sched._on_stop("cur")
    sched._webstream_generation += 1  # what a new start does
    time.sleep(0.4)
    engine.webstream_stop.assert_not_called()


def test_a_webstream_row_with_a_same_stream_follow_up_keeps_its_source_under_a_dj(make):
    sched, engine = make()
    now = datetime.utcnow()
    _on_air(sched, _webstream(now - timedelta(seconds=400), 3))
    sched._armed_events["next"] = _webstream(now, 5)
    timer = MagicMock()
    timer.is_alive.return_value = True
    sched._timers["next"] = (timer, None)
    sched._on_stop("cur")
    engine.webstream_gate.assert_not_called()
    engine.webstream_stop.assert_not_called()


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_file_row_under_a_dj_still_ends_as_before(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    _on_air(sched, _file(datetime.utcnow() - timedelta(seconds=200), 1))
    sched._on_stop("cur")
    engine.webstream_gate.assert_not_called()
    engine.linein_gate.assert_not_called()
    assert engine.stop.called is under_dj


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_webstream_row_is_held_back_under_a_dj_and_ends_the_file_row_before_it(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    now = datetime.utcnow()
    _on_air(sched, _file(now - timedelta(seconds=180), 1))
    sched._queued_ahead = ("stale", _file(now, 9))
    ws = _webstream(now, 3)
    sched._on_webstream_start("ws", ws)
    assert sched._current_event is ws
    engine.webstream_start.assert_not_called()  # still starts when the DJ leaves
    engine.webstream_gate.assert_not_called()
    if under_dj:
        engine.stop.assert_called_once()  # nothing of the file row is left in the queue
        assert sched._queued_ahead is None
    else:
        engine.stop.assert_not_called()


def test_a_webstream_row_after_another_live_row_under_a_dj_touches_nothing(make):
    sched, engine = make()
    now = datetime.utcnow()
    _on_air(sched, _webstream(now - timedelta(seconds=300), 3))
    sched._on_webstream_start("ws", _webstream(now, 4))
    engine.stop.assert_not_called()


@pytest.mark.parametrize("under_dj", [True, False])
def test_a_file_row_under_a_dj_closes_its_live_predecessor_only_with_the_switch(make, under_dj):
    sched, engine = make(under_dj=under_dj)
    sched._close_predecessor_source(
        _webstream(datetime.utcnow() - timedelta(seconds=300), 3), "row"
    )
    if under_dj:
        engine.webstream_gate.assert_called_once_with(False)
    else:
        engine.webstream_gate.assert_not_called()


@pytest.mark.parametrize("under_dj", [True, False])
def test_exact_time_waits_apply_under_a_dj_only_with_the_switch(make, monkeypatch, under_dj):
    sched, engine = make(under_dj=under_dj)
    slept = []
    monkeypatch.setattr(ps.time, "sleep", slept.append)
    sched._playing_key = "row"
    assert sched._wait_for_exact_time("row", datetime.utcnow() + timedelta(seconds=0.4), "PLAY")
    row = _file(datetime.utcnow() - timedelta(seconds=179), 1)
    sched._file_chain_lag = 0.0
    sched._let_file_run_out("row", row)
    if under_dj:
        assert len(slept) == 2 and 0.2 < slept[0] <= 0.4 and 0.5 < slept[1] <= 1.0
    else:
        assert slept == []


# ---- hand-back: DJ off ----------------------------------------------------


def test_dj_off_pushes_nothing_when_the_row_kept_running_under_the_dj(make):
    sched, engine = make(state=SourceState.SCHEDULED)
    row = _file(datetime.utcnow() - timedelta(seconds=20), 11)
    _on_air(sched, row)
    sched._paused_leftover = True
    engine.playing_remaining_seconds.return_value = _queue_value(sched, row) + 0.6  # chain lag
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.play.assert_not_called()
    engine.replace_paused.assert_not_called()
    engine.stop.assert_not_called()
    assert sched._current_event is row and sched._paused_leftover is False


def test_dj_off_inside_the_crossfade_tail_is_in_step(make):
    sched, engine = make(state=SourceState.SCHEDULED)
    row = _file(datetime.utcnow() - timedelta(seconds=178), 11)  # 2 s on air left
    _on_air(sched, row)
    engine.playing_remaining_seconds.return_value = 0.0  # cross has pulled the successor
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.play.assert_not_called()


@pytest.mark.parametrize("reported", ["stood still", "idle", "unknown"])
def test_dj_off_re_enters_with_an_offset_when_the_queue_is_not_in_step(make, reported):
    sched, engine = make(state=SourceState.SCHEDULED)
    row = _file(datetime.utcnow() - timedelta(seconds=20), 11)
    _on_air(sched, row)
    engine.playing_remaining_seconds.return_value = {
        # the queue stood still since the DJ took over 15 s ago
        "stood still": _queue_value(sched, row) + 15.0,
        "idle": 0.0,
        "unknown": None,
    }[reported]
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.play.assert_called_once()
    kwargs = engine.play.call_args.kwargs
    assert kwargs["transition"] == PAUSED_CUT_SHAPE
    assert 19.0 <= kwargs["cue_in"] <= 22.0


def test_without_the_switch_dj_off_resumes_as_before_and_does_not_ask_the_queue(make):
    sched, engine = make(under_dj=False, state=SourceState.SCHEDULED)
    row = _file(datetime.utcnow() - timedelta(seconds=20), 11)
    _on_air(sched, row)
    engine.playing_remaining_seconds.return_value = _queue_value(sched, row)
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.playing_remaining_seconds.assert_not_called()
    engine.play.assert_called_once()
    assert engine.play.call_args.kwargs["transition"] == PAUSED_CUT_SHAPE


def test_dj_off_under_a_live_row_resumes_it_as_before(make):
    sched, engine = make(state=SourceState.SCHEDULED)
    ws = _webstream(datetime.utcnow() - timedelta(seconds=60), 3)
    sched._current_event, sched._playing_key = ws, "ws"
    sched._current_audio_path = ws.uri
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.webstream_start.assert_called_once()
    engine.webstream_gate.assert_called_once_with(True)
    engine.playing_remaining_seconds.assert_not_called()


# ---- hand-back: the show source ends with its show ------------------------


def _arm(sched, key, event):
    timer = MagicMock()
    timer.is_alive.return_value = True
    sched._armed_events[key] = event
    sched._timers[key] = (timer, None)


def _until(sched):
    return datetime.utcfromtimestamp(sched._switcher.show_until())


def test_show_end_leaves_a_running_chain_alone(make):
    sched, engine = make(state=SourceState.SCHEDULED, reason=REASON_SHOW_END)
    boundary = _until(sched)
    last = _file(boundary - timedelta(seconds=180), 4, instance=1)
    first = _file(boundary, 5)
    _on_air(sched, last)
    _arm(sched, "first", first)
    sched._queued_ahead = ("first", first)  # queued ahead behind the last row, as always
    sched._queued_ahead_prev = last
    engine.playing_remaining_seconds.return_value = 0.0  # in the tail / successor pulled
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_not_called()
    engine.play.assert_not_called()
    # the boundary hand-over stays with the rows' own timers
    assert sched._current_event is last and sched._queued_ahead == ("first", first)
    assert sched._paused_leftover is False


@pytest.mark.parametrize("reported", [None, 0.0, 1.2])
def test_show_end_with_an_idle_queue_replaces_nothing(make, reported):
    sched, engine = make(state=SourceState.SCHEDULED, reason=REASON_SHOW_END)
    _arm(sched, "first", _file(_until(sched), 5))
    engine.playing_remaining_seconds.return_value = reported
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_not_called()
    assert sched._queued_ahead is None and sched._paused_leftover is False


def test_show_end_replaces_a_queue_that_stood_still_after_all(make):
    sched, engine = make(state=SourceState.SCHEDULED, reason=REASON_SHOW_END)
    first = _file(_until(sched), 5)
    _arm(sched, "first", first)
    engine.playing_remaining_seconds.return_value = 66.0  # a track is still in the queue
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.replace_paused.assert_called_once()
    assert engine.replace_paused.call_args.kwargs["queued_ahead"] is True
    assert sched._queued_ahead == ("first", first)


def test_without_the_switch_the_show_end_replaces_the_paused_queue_without_asking(make):
    sched, engine = make(under_dj=False, state=SourceState.SCHEDULED, reason=REASON_SHOW_END)
    _arm(sched, "first", _file(_until(sched), 5))
    sched.switch_audio_source(SourceState.SCHEDULED)
    engine.playing_remaining_seconds.assert_not_called()
    engine.replace_paused.assert_called_once()
