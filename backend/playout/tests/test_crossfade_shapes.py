"""
RASTATIME 2026-09-27 - show-boundary crossfade: the playout side.

  * engine: push THEN skip, the shape goes out as ``var.set rt_cross``
    before the push, queue-ahead (enqueue / adopt_queued / flush_queued)
  * scheduler: shape decision (track / show / cut and the skip
    variants), queue-ahead behind a playing file track, adopt at the
    row start with a skip only on overbook, the normal path skips only
    while the predecessor still has audio
  * schedule.py: FileEvent carries instance_id + no_fade_crossfade
  * __main__: the show crossfade preference
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
from rastatime_playout.player.events import EventKind, FileEvent

# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------


def _engine():
    telnet = MagicMock(spec=LiquidsoapTelnetClient)
    telnet.request_queue_push.return_value = "42"
    telnet._host, telnet._port = "127.0.0.1", 1234
    return LiquidsoapPlayoutEngine(telnet_client=telnet), telnet


def _names(telnet):
    return [c[0] for c in telnet.mock_calls if not c[0].startswith("_")]


def test_play_sets_the_shape_pushes_and_skips_afterwards():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.play("C:/m/a.mp3", transition="show_skip", skip_current=True)
    names = _names(telnet)
    assert names == [
        "var_set",
        "var_set",
        "var_set",
        "var_set",
        "request_queue_push",
        "request_queue_skip",
    ]
    assert [c.args for c in telnet.var_set.call_args_list] == [
        ("rt_cross", "show_skip"),
        ("rt_nofade", "-"),
        ("rt_dur", "-1.00"),
        ("rt_cut", "0.00"),
    ]


def test_play_without_skip_current_never_skips():
    eng, telnet = _engine()
    eng.stop()  # deferred stop pending, as after _on_stop
    eng.play("C:/m/a.mp3", transition="track", skip_current=False)
    names = _names(telnet)
    assert "request_queue_skip" not in names
    assert eng._stop_timer is None  # the pending deferred stop was cancelled


def test_play_pending_stop_is_folded_into_the_skip_after_the_push():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.stop()
    eng.play("C:/m/b.mp3", skip_current=True)
    names = [n for n in _names(telnet) if n in ("request_queue_push", "request_queue_skip")]
    assert names == ["request_queue_push", "request_queue_skip"]


def test_enqueue_pushes_behind_the_playing_track():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng._current_uri = "C:/m/a.mp3"
    assert eng.enqueue("C:/m/b.mp3", cue_in=1.0, cue_out=30.0, transition="show/old") is True
    assert _names(telnet) == ["var_set", "var_set", "var_set", "var_set", "request_queue_push"]
    assert [c.args for c in telnet.var_set.call_args_list] == [
        ("rt_cross", "show"),
        ("rt_nofade", "old"),
        ("rt_dur", "-1.00"),
        ("rt_cut", "0.00"),
    ]
    assert eng._queued_uri == "C:/m/b.mp3" and eng._queued_request_id == "42"
    assert eng._current_uri == "C:/m/a.mp3"  # untouched
    assert eng.get_state() == PlayoutState.PLAYING


def test_enqueue_reports_a_rejected_push():
    eng, telnet = _engine()
    telnet.request_queue_push.return_value = "ERROR: unknown command"
    assert eng.enqueue("C:/m/b.mp3") is False
    assert eng._queued_uri is None


def test_adopt_queued_cancels_the_deferred_stop_and_skips_on_overbook():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.enqueue("C:/m/b.mp3", transition="show")
    # a deferred stop is pending (as after the predecessor's _on_stop)
    pending = threading.Timer(60.0, lambda: None)
    pending.daemon = True
    pending.start()
    eng._stop_timer, eng._stop_requested = pending, True
    eng.adopt_queued("C:/m/b.mp3", skip_current=True, transition="show_skip")
    assert eng._stop_timer is None and eng._stop_requested is False
    assert pending.finished.is_set()  # cancelled
    assert _names(telnet)[-5:] == ["var_set", "var_set", "var_set", "var_set", "request_queue_skip"]
    assert telnet.var_set.call_args_list[-4].args == ("rt_cross", "show_skip")
    assert eng._current_uri == "C:/m/b.mp3" and eng._current_request_id == "42"
    assert eng._queued_uri is None
    assert eng.get_state() == PlayoutState.PLAYING


def test_adopt_queued_without_skip_touches_nothing_on_the_wire():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.enqueue("C:/m/b.mp3", transition="track")
    before = len(telnet.mock_calls)
    eng.adopt_queued("C:/m/b.mp3", skip_current=False)
    assert len(telnet.mock_calls) == before
    assert eng._current_uri == "C:/m/b.mp3"


def test_flush_queued_drops_pending_requests():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.enqueue("C:/m/b.mp3")
    eng.flush_queued()
    telnet.request_queue_flush.assert_called_once()
    assert eng._queued_uri is None


# ---------------------------------------------------------------------------
# scheduler
# ---------------------------------------------------------------------------


def _file(
    start: datetime, row_id: int, *, instance: int = 1, exclude: bool = False, seconds: int = 180
) -> FileEvent:
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=seconds),
        row_id=row_id,
        id=row_id,
        uri="C:/media/a.mp3",
        show_name="night",
        cue_in=0.0,
        cue_out=float(seconds),
        track_title=f"t{row_id}",
        artist_name="a",
        replay_gain=None,
        fade_in=0.0,
        fade_out=0.0,
        mime="audio/mpeg",
        filesize=1000,
        instance_id=instance,
        no_fade_crossfade=exclude,
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


def test_cross_mode_matrix(sched):
    s, _ = sched
    now = datetime.utcnow()
    a = _file(now, 1, instance=1)
    b = _file(now, 2, instance=1)
    c = _file(now, 3, instance=2)
    x = _file(now, 4, instance=1, exclude=True)
    assert s._cross_mode(None, b, skip=False) == "track/-"
    assert s._cross_mode(None, b, skip=True) == "instant/-"
    assert s._cross_mode(a, b, skip=False) == "track/-"
    assert s._cross_mode(a, b, skip=True) == "track_skip/-"
    assert s._cross_mode(a, c, skip=False) == "show/-"
    assert s._cross_mode(a, c, skip=True) == "show_skip/-"
    # "No Fade during Crossover" keeps the shape and names the flagged side
    assert s._cross_mode(a, x, skip=False) == "track/new"
    assert s._cross_mode(x, c, skip=False) == "show/old"
    assert s._cross_mode(x, c, skip=True) == "show_skip/old"
    assert s._cross_mode(x, x, skip=False) == "track/both"


def test_buffer_is_the_larger_crossfade(sched):
    s, _ = sched
    assert s._cross_buffer_seconds == 2.0


def test_queue_ahead_enqueues_behind_a_playing_file(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, instance=1, seconds=180)  # 10 s left
    nxt = _file(now + timedelta(seconds=8), 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._on_file_queue_ahead("n", nxt)
    engine.enqueue.assert_called_once()
    assert engine.enqueue.call_args.kwargs["transition"] == "show/-/-/2.00"  # 10 s left, row in 8 s
    assert s._queued_ahead == ("n", nxt)


def test_queue_ahead_does_nothing_without_a_playing_file(sched):
    s, engine = sched
    now = datetime.utcnow()
    nxt = _file(now + timedelta(seconds=8), 2)
    s._current_event, s._playing_key = None, None
    s._on_file_queue_ahead("n", nxt)
    # predecessor already over -> a gap follows, the track starts the normal way
    s._current_event, s._playing_key = _file(now - timedelta(seconds=400), 1), "p"
    s._on_file_queue_ahead("n", nxt)
    engine.enqueue.assert_not_called()
    assert s._queued_ahead is None


def test_queue_ahead_replaces_a_stale_queued_track(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, seconds=180)
    old_next = _file(now + timedelta(seconds=8), 2)
    new_next = _file(now + timedelta(seconds=8), 3)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("old", old_next)
    s._on_file_queue_ahead("new", new_next)
    engine.flush_queued.assert_called_once()
    assert s._queued_ahead == ("new", new_next)


def test_queue_ahead_keeps_an_armed_earlier_row_when_rows_are_shorter_than_the_lead(sched):
    """2026-10-02 23:36: StationID tief (3.2 s) and Kreisky (4.9 s) behind a track."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=174), 1, seconds=180)  # 6 s left
    tief = _file(now + timedelta(seconds=6), 2, seconds=3)
    kreisky = _file(now + timedelta(seconds=9), 3, seconds=5)
    s._current_event, s._playing_key = prev, "p"
    s._armed_events = {"tief": tief, "kreisky": kreisky}
    s._queued_ahead = ("tief", tief)
    s._on_file_queue_ahead("kreisky", kreisky)  # its lead window arrives early
    engine.flush_queued.assert_not_called()
    engine.enqueue.assert_not_called()
    assert s._queued_ahead == ("tief", tief)


def test_queue_ahead_still_replaces_a_row_that_is_no_longer_armed(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, seconds=180)
    gone = _file(now + timedelta(seconds=8), 2)
    new_next = _file(now + timedelta(seconds=8), 3)
    s._current_event, s._playing_key = prev, "p"
    s._armed_events = {"new": new_next}  # the refresh dropped row 2
    s._queued_ahead = ("gone", gone)
    s._on_file_queue_ahead("new", new_next)
    engine.flush_queued.assert_called_once()
    assert s._queued_ahead == ("new", new_next)


def test_queue_ahead_replaces_an_armed_row_that_starts_later(sched):
    """A re-timed row that moved behind this one is stale for cross."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, seconds=180)
    later = _file(now + timedelta(seconds=30), 2)
    new_next = _file(now + timedelta(seconds=8), 3)
    s._current_event, s._playing_key = prev, "p"
    s._armed_events = {"later": later, "new": new_next}
    s._queued_ahead = ("later", later)
    s._on_file_queue_ahead("new", new_next)
    engine.flush_queued.assert_called_once()
    assert s._queued_ahead == ("new", new_next)


def test_file_start_adopts_the_queued_track_without_skip_when_rows_overlap(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=178), 1, seconds=180)  # 2 s left = overlap
    nxt = _file(now, 2, instance=1)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("n", nxt)
    s._on_file_start("n", nxt)
    engine.adopt_queued.assert_called_once()
    assert engine.adopt_queued.call_args.kwargs == {"skip_current": False, "transition": None}
    engine.play.assert_not_called()
    engine.stop.assert_not_called()
    assert s._queued_ahead is None and s._current_event is nxt


def test_file_start_adopts_the_queued_track_with_skip_on_overbook(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=60), 1, instance=1, seconds=180)  # 120 s left
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("n", nxt)
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {
        "skip_current": True,
        "transition": "show_skip/-/-/120.00",
    }
    engine.play.assert_not_called()


def test_file_start_normal_path_skips_only_while_the_predecessor_has_audio(sched):
    s, engine = sched
    now = datetime.utcnow()
    nxt = _file(now, 2, instance=1)
    # (a) nothing plays: push, no skip
    s._current_event, s._playing_key = None, None
    s._on_file_start("n", nxt)
    kw = engine.play.call_args.kwargs
    assert kw["skip_current"] is False and kw["transition"] == "track/-"
    # (b) the predecessor runs on into the slot (same show): push, then skip
    engine.play.reset_mock()
    prev = _file(now - timedelta(seconds=60), 1, instance=1, seconds=180)
    s._current_event, s._playing_key = prev, "p"
    s._on_file_start("n2", _file(now, 3, instance=1))
    kw = engine.play.call_args.kwargs
    assert kw["skip_current"] is True and kw["transition"] == "track_skip/-"
    engine.adopt_queued.assert_not_called()
    # (c) the predecessor is inside its tail window (rows overlap by the
    # track crossfade): push only - cross already holds the tail, a skip
    # would be a no-op or hit the pushed track
    engine.play.reset_mock()
    prev = _file(now - timedelta(seconds=178), 1, instance=1, seconds=180)  # 2 s left
    s._current_event, s._playing_key = prev, "p"
    s._on_file_start("n3", _file(now, 4, instance=1))
    kw = engine.play.call_args.kwargs
    assert kw["skip_current"] is False and kw["transition"] == "track/-"


def test_file_start_uses_the_natural_end_not_the_clipped_row_end(sched):
    """Rehearsal 2026-09-27: a track running past its show has its row end
    clipped to the show end by the API; the audio still has 45 s left."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=135), 1, instance=1, seconds=180)  # 45 s of audio left
    prev.end = now  # row clipped to the show end
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {
        "skip_current": True,
        "transition": "show_skip/-/-/45.00",
    }


def test_file_start_after_the_predecessors_stop_still_knows_the_predecessor(sched):
    """STOP(prev) and PLAY(next) fire at the same instant on clipped rows;
    STOP may clear _current_event first."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=135), 1, instance=1, seconds=180)
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = None, None
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {
        "skip_current": True,
        "transition": "show_skip/-/-/45.00",
    }
    engine.play.assert_not_called()


def test_stop_leaves_the_queue_alone_when_a_successor_is_queued(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=180), 1, seconds=180)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n", _file(now, 2)), prev
    s._on_stop("p")
    engine.stop.assert_not_called()
    engine.flush_queued.assert_not_called()
    assert s._current_event is prev  # bookkeeping left to the successor
    # without a queued successor the normal teardown runs
    s._queued_ahead, s._queued_ahead_prev = None, None
    s._on_stop("p")
    engine.stop.assert_called_once()


def test_file_start_prefers_the_engines_measured_remaining(sched):
    """A predecessor that started late has more audio left than its row
    says: the engine's measurement decides the skip."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=178), 1, instance=1, seconds=180)  # rows: 2 s left
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    engine.playing_remaining_seconds.return_value = 47.0  # engine: 47 s left
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {
        "skip_current": True,
        "transition": "show_skip/-/-/47.00",
    }
    # and the other way round: rows say overbook, the engine says the tail window is open
    engine.adopt_queued.reset_mock()
    prev2 = _file(now - timedelta(seconds=60), 3, instance=2, seconds=180)
    nxt2 = _file(now, 4, instance=2)
    s._current_event, s._playing_key = prev2, "p2"
    s._queued_ahead, s._queued_ahead_prev = ("n2", nxt2), prev2
    engine.playing_remaining_seconds.return_value = 1.8
    s._on_file_start("n2", nxt2)
    assert engine.adopt_queued.call_args.kwargs == {"skip_current": False, "transition": None}


def test_engine_reads_the_measured_remaining():
    eng, telnet = _engine()
    telnet.request_queue_remaining.return_value = "7 47.31\nEND"
    assert eng.playing_remaining_seconds() == pytest.approx(47.31)
    telnet.request_queue_remaining.return_value = "7 -1.\nEND"
    assert eng.playing_remaining_seconds() is None
    # the queue is already on the successor queued ahead: nothing to skip
    eng._state = PlayoutState.PLAYING
    telnet.request_queue_push.return_value = "9"
    eng.enqueue("C:/m/b.mp3")
    telnet.request_queue_remaining.return_value = "9 162.8\nEND"
    assert eng.playing_remaining_seconds() == 0.0
    telnet.request_queue_remaining.return_value = "8 40.0\nEND"
    assert eng.playing_remaining_seconds() == pytest.approx(40.0)
    telnet.request_queue_remaining.side_effect = RuntimeError("down")
    assert eng.playing_remaining_seconds() is None


def test_file_start_drops_a_stale_queued_track_before_the_normal_path(sched):
    s, engine = sched
    now = datetime.utcnow()
    s._current_event, s._playing_key = None, None
    s._queued_ahead = ("other", _file(now, 9))
    s._on_file_start("n", _file(now, 2))
    engine.flush_queued.assert_called_once()
    engine.play.assert_called_once()
    assert s._queued_ahead is None


def test_arm_queue_ahead_lead_is_buffer_plus_margin(sched, monkeypatch):
    s, _ = sched
    delays = []

    class FakeTimer:
        def __init__(self, delay, fn, args=()):
            delays.append(delay)
            self.daemon = False

        def start(self):
            pass

        def cancel(self):
            pass

    monkeypatch.setattr(ps.threading, "Timer", FakeTimer)
    ev = _file(datetime.utcnow(), 2)
    s._arm_queue_ahead("k", ev, 10.0)
    assert delays == [pytest.approx(10.0 - (2.0 + ps.QUEUE_AHEAD_MARGIN_SECONDS))]
    s._arm_queue_ahead("k2", ev, 6.0)  # inside the lead window: queue now
    assert delays[-1] == 0.0
    s._arm_queue_ahead("k3", ev, 0.2)  # too close: normal start only
    assert len(delays) == 2
    assert "k/queue" in s._prepare_timers and "k2/queue" in s._prepare_timers


# ---------------------------------------------------------------------------
# schedule.py + __main__
# ---------------------------------------------------------------------------


def test_generate_file_events_carries_instance_and_exclusion():
    from rastatime_playout.player.schedule import StreamPreferences, generate_file_events

    events = {}
    schedule = {
        "id": 7,
        "instance": 33,
        "starts_at": datetime(2026, 9, 27, 12, 0),
        "ends_at": datetime(2026, 9, 27, 12, 3),
        "fade_in": "00:00:00.500000",
        "fade_out": "00:00:00.500000",
        "cue_in": "00:00:00",
        "cue_out": "00:03:00",
    }
    file = {
        "url": "x",
        "id": 5,
        "mime": "audio/mpeg",
        "replay_gain": 0.0,
        "size": 1,
        "no_fade_crossfade": True,
    }
    prefs = StreamPreferences(
        input_fade_transition=0.0,
        message_format=0,
        message_offline="off",
        replay_gain_enabled=False,
        replay_gain_offset=0.0,
    )
    generate_file_events(events, schedule, file, {"name": "s"}, prefs)
    (ev,) = events.values()
    assert ev.instance_id == 33 and ev.no_fade_crossfade is True


def test_generate_file_events_inherits_the_types_no_fade_preset():
    """RASTATIME 2026-09-30 - track_type_no_fade (migration 0063): a track
    set to "As the track type" takes the preset; the track's own field
    wins, an excluded track has no overlap to keep its level in."""
    from rastatime_playout.player.schedule import StreamPreferences, generate_file_events

    schedule = {
        "id": 7,
        "instance": 33,
        "starts_at": datetime(2026, 9, 30, 12, 0),
        "ends_at": datetime(2026, 9, 30, 12, 3),
        "fade_in": "00:00:00.500000",
        "fade_out": "00:00:00.500000",
        "cue_in": "00:00:00",
        "cue_out": "00:03:00",
    }
    prefs = StreamPreferences(
        input_fade_transition=0.0,
        message_format=0,
        message_offline="off",
        replay_gain_enabled=False,
        replay_gain_offset=0.0,
    )
    base = {"url": "x", "id": 5, "mime": "audio/mpeg", "replay_gain": 0.0, "size": 1}

    def flag(**fields):
        events = {}
        generate_file_events(events, schedule, {**base, **fields}, {"name": "s"}, prefs)
        (ev,) = events.values()
        return ev.no_fade_crossfade

    assert flag(track_type_no_fade=True) is True  # as the track type
    assert flag(track_type_no_fade=False) is False
    assert flag() is False  # older API without the field
    assert flag(no_fade_crossfade=True, track_type_no_fade=False) is True  # the track's field wins
    assert flag(exclude_crossfade=True, track_type_no_fade=True) is False  # nothing to fade in


def test_resolve_dj_fade_prefers_the_preference(monkeypatch):
    from rastatime_playout import __main__ as main

    monkeypatch.setattr(
        main, "_read_pref_seconds", lambda key: 2.0 if key == "default_transition_fade" else None
    )
    assert main._resolve_dj_fade_seconds() == 2.0
    monkeypatch.setattr(main, "_read_pref_seconds", lambda key: None)
    monkeypatch.delenv("RASTATIME_LIQUIDSOAP_DJ_FADE_SECONDS", raising=False)
    assert main._resolve_dj_fade_seconds() == main._LIQUIDSOAP_DEFAULT_DJ_FADE == 1.0


def test_full_render_threads_the_dj_fade_into_the_bus():
    from rastatime_playout import liquidsoap_config as lc

    out = lc.render_rastatime_liq(
        [{"type": "mp3", "host": "h", "port": 8000, "mount": "m", "pass": "x", "bitrate": 128}],
        harbor_main_password="a",
        harbor_show_password="b",
        dj_fade_seconds=1.5,
    )
    assert "def bus_dj(old, new) =\n  add(normalize=false, [fade.out(duration=1.5, old)," in out


def test_resolve_show_crossfade_prefers_the_preference(monkeypatch):
    from rastatime_playout import __main__ as main

    monkeypatch.setattr(
        main,
        "_read_pref_seconds",
        lambda key: 2.5 if key == "default_show_crossfade_duration" else None,
    )
    assert main._resolve_show_crossfade_seconds() == 2.5
    monkeypatch.setattr(main, "_read_pref_seconds", lambda key: None)
    monkeypatch.setenv("RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS", "0.75")
    assert main._resolve_show_crossfade_seconds() == 0.75
    monkeypatch.delenv("RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS")
    assert main._resolve_show_crossfade_seconds() == main._LIQUIDSOAP_DEFAULT_SHOW_CROSSFADE


# ---------------------------------------------------------------------------
# RASTATIME 2026-09-29 - crossfade per track type + "Exclude from Crossover"
# ---------------------------------------------------------------------------


def _typed(start, row_id, instance=1, crossfade=None, exclude=False, no_fade=False):
    ev = _file(start, row_id, instance=instance)
    return ev.model_copy(
        update={
            "crossfade_seconds": crossfade,
            "exclude_crossfade": exclude,
            "no_fade_crossfade": no_fade,
        }
    )


def test_pair_crossfade_is_the_smaller_value(sched):
    s, _ = sched  # house track crossfade 2.0 s, buffer 2.0 s
    now = datetime.utcnow()
    music = _typed(now, 1)  # no type value -> house
    jingle = _typed(now, 2, crossfade=0.0)
    short = _typed(now, 3, crossfade=0.5)
    excluded = _typed(now, 4, crossfade=1.5, exclude=True)
    long_ = _typed(now, 5, crossfade=9.0)  # capped at the cross buffer
    assert s._pair_crossfade(music, music) == 2.0
    assert s._pair_crossfade(music, jingle) == 0.0
    assert s._pair_crossfade(jingle, music) == 0.0
    assert s._pair_crossfade(music, short) == 0.5
    assert s._pair_crossfade(short, excluded) == 0.0
    assert s._pair_crossfade(long_, long_) == 2.0
    assert s._pair_crossfade(None, short) == 0.5


def test_cross_mode_carries_the_overlap_only_when_it_differs(sched):
    s, _ = sched
    now = datetime.utcnow()
    music = _typed(now, 1)
    jingle = _typed(now, 2, crossfade=0.0)
    short = _typed(now, 3, crossfade=0.5)
    other_show = _typed(now, 4, instance=2)
    assert s._cross_mode(music, music, skip=False) == "track/-"
    assert s._cross_mode(music, jingle, skip=False) == "track/-/0.00"
    assert s._cross_mode(jingle, music, skip=True) == "track_skip/-/0.00"
    assert s._cross_mode(music, short, skip=False) == "track/-/0.50"
    # "No Fade" keeps its meaning next to a type value
    assert s._cross_mode(_typed(now, 5, no_fade=True), short, skip=False) == "track/old/0.50"
    # show boundary: the show value rules; a track that takes no crossfade is not faded
    assert s._cross_mode(music, other_show, skip=False) == "show/-"
    assert s._cross_mode(jingle, other_show, skip=False) == "show/old"
    assert s._cross_mode(_typed(now, 6, exclude=True), other_show, skip=True) == "show_skip/old"


def test_engine_sends_the_overlap_of_the_transition():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.enqueue("C:/m/b.mp3", transition="track/-/0.00")
    assert [c.args for c in telnet.var_set.call_args_list] == [
        ("rt_cross", "track"),
        ("rt_nofade", "-"),
        ("rt_dur", "0.00"),
        ("rt_cut", "0.00"),
    ]
    telnet.var_set.reset_mock()
    eng.enqueue("C:/m/c.mp3", transition="track/new")  # back to the house value
    assert telnet.var_set.call_args_list[-2].args == ("rt_dur", "-1.00")


def test_queue_ahead_sends_the_pair_overlap(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, instance=1, seconds=180)
    jingle = _typed(now + timedelta(seconds=8), 2, crossfade=0.0)
    s._current_event, s._playing_key = prev, "p"
    s._on_file_queue_ahead("n", jingle)
    assert engine.enqueue.call_args.kwargs["transition"] == "track/-/0.00"


# ---- RASTATIME 2026-11-06 - strict show boundary -----------------------------


def test_strict_boundary_cuts_a_small_overrun_unless_delayed_start_is_allowed(sched):
    """Operator rule 2026-11-06: before a show WITHOUT 'Allow delayed start'
    the predecessor is cut at the boundary (tolerance 0.3 s); before a show
    WITH it the old threshold (tail + 1.5 s) applies."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=178), 1, instance=1, seconds=180)
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    engine.playing_remaining_seconds.return_value = 1.2  # 1.2 s past the boundary
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {
        "skip_current": True,
        "transition": "show_skip/-/-/1.20",
    }
    engine.adopt_queued.reset_mock()
    nxt2 = _file(now, 3, instance=3)
    nxt2.allow_delayed_start = True
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n2", nxt2), prev
    engine.playing_remaining_seconds.return_value = 1.2
    s._on_file_start("n2", nxt2)
    assert engine.adopt_queued.call_args.kwargs == {"skip_current": False, "transition": None}


def test_strict_boundary_within_tolerance_is_left_alone(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=178), 1, instance=1, seconds=180)
    nxt = _file(now, 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead, s._queued_ahead_prev = ("n", nxt), prev
    engine.playing_remaining_seconds.return_value = 0.2
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs == {"skip_current": False, "transition": None}


def test_queue_ahead_reports_the_boundary_cut_from_the_engine_measurement(sched):
    """At the queue-ahead the engine's remaining (still reliable) wins over
    the rows: 11 s left, row in 8 s -> 3.00 s cut; a show that allows a
    delayed start gets the plain shape."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=170), 1, instance=1, seconds=180)  # rows: 10 s left
    nxt = _file(now + timedelta(seconds=8), 2, instance=2)
    s._current_event, s._playing_key = prev, "p"
    engine.playing_remaining_seconds.return_value = 11.0
    s._on_file_queue_ahead("n", nxt)
    assert engine.enqueue.call_args.kwargs["transition"] == "show/-/-/3.00"
    engine.enqueue.reset_mock()
    s._queued_ahead = None
    nxt2 = _file(now + timedelta(seconds=8), 3, instance=3)
    nxt2.allow_delayed_start = True
    s._on_file_queue_ahead("n2", nxt2)
    assert engine.enqueue.call_args.kwargs["transition"] == "show/-"


def test_engine_sends_the_boundary_cut():
    eng, telnet = _engine()
    eng._state = PlayoutState.PLAYING
    eng.enqueue("C:/m/b.mp3", transition="show/-/-/1.20")
    assert [c.args for c in telnet.var_set.call_args_list] == [
        ("rt_cross", "show"),
        ("rt_nofade", "-"),
        ("rt_dur", "-1.00"),
        ("rt_cut", "1.20"),
    ]
