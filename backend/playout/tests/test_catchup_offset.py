"""
RASTATIME 2026-09-28 - catch-up enters a running track at its offset, and
a running row that a show-builder edit re-timed is rebound, not restarted.

Production 2026-09-28: after a PLAYOUT restart the catch-up replayed
'Fade' from the top (141 s in); ``schedule-remove`` on the running show
moved the playing row 9 s (same row id) and the refresh declared it
"removed from schedule", stopped it and restarted the same track.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import EventKind, FileEvent, WebStreamEvent


def _file(start, row_id=777, file_id=1, cue_in=0.0, seconds=200.0):
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=seconds - cue_in),
        row_id=row_id,
        id=file_id,
        uri=f"file:///C:/rastatime/scheduler/{file_id}.mp3",
        show_name="bbc",
        track_title="Song",
        artist_name="Band",
        mime="audio/mpeg",
        filesize=1,
        cue_in=cue_in,
        cue_out=seconds,
        fade_in=0.0,
        fade_out=0.0,
        replay_gain=None,
    )


def _webstream(start, row_id=888, stream_id=2):
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START,
        start=start,
        end=start + timedelta(minutes=5),
        row_id=row_id,
        uri="http://stream.example/bbc",
        id=stream_id,
        show_name="bbc",
    )


@pytest.fixture
def sched(monkeypatch):
    from libretime_playout import playout_scheduler as ps

    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.PLAYING
    engine.enqueue.return_value = True
    engine.playing_remaining_seconds.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), track_crossfade_seconds=2.0)
    s.reset_gates = MagicMock()
    s._switcher = None
    s._ensure_file_cached = MagicMock(return_value=Path("C:/cache/a.mp3"))
    s._notify_media_started = MagicMock()
    s._set_bus_show = MagicMock()
    return s, engine


def _refresh(s, events):
    with patch("libretime_playout.playout_scheduler.get_schedule", return_value=events):
        s.refresh()
    timers = dict(s._timers)
    s._cancel_all_timers()
    return timers


# ---------------------------------------------------------------------------
# A - catch-up at the offset
# ---------------------------------------------------------------------------

def test_catch_up_hands_the_offset_to_the_start(sched):
    s, _ = sched
    now = datetime.utcnow()
    running = _file(now - timedelta(seconds=141))
    with patch.object(s, "_on_file_start"):
        s._arm_file_event("K", running, now)
        start_t, stop_t = s._timers["K"]
        start_t.cancel()
        stop_t.cancel()
    assert start_t.args[0] == "K" and start_t.args[1] is running
    assert start_t.args[2] == pytest.approx(141.0, abs=0.5)


def test_file_start_seeks_into_the_track(sched):
    s, engine = sched
    ev = _file(datetime.utcnow() - timedelta(seconds=141), cue_in=0.5)
    s._on_file_start("K", ev, seek=141.0)
    engine.play.assert_called_once()
    assert engine.play.call_args.kwargs["cue_in"] == pytest.approx(141.5)
    assert engine.play.call_args.kwargs["cue_out"] == 200.0
    assert s._playing_key == "K" and s._current_event is ev


def test_file_start_without_offset_is_unchanged(sched):
    s, engine = sched
    ev = _file(datetime.utcnow(), cue_in=0.5)
    s._on_file_start("K", ev)
    assert engine.play.call_args.kwargs["cue_in"] == 0.5


def test_catch_up_past_the_audio_plays_nothing(sched):
    s, engine = sched
    ev = _file(datetime.utcnow() - timedelta(seconds=199), seconds=200.0)
    s._on_file_start("K", ev, seek=199.8)
    engine.play.assert_not_called()
    s._notify_media_started.assert_called_once_with(ev.row_id)
    assert s._current_event is ev              # bookkeeping for the stop timer


def test_catch_up_drops_a_queued_copy_that_would_start_at_the_top(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=100), row_id=1, file_id=1)
    nxt = _file(now - timedelta(seconds=30), row_id=2, file_id=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("n", nxt)
    s._on_file_start("n", nxt, seek=30.0)
    engine.flush_queued.assert_called_once()
    engine.adopt_queued.assert_not_called()
    assert engine.play.call_args.kwargs["cue_in"] == pytest.approx(30.0)
    assert s._queued_ahead is None


# ---------------------------------------------------------------------------
# B - identity without the start; re-timed rows are rebound
# ---------------------------------------------------------------------------

def test_same_item_ignores_the_start_but_not_the_medium(sched):
    s, _ = sched
    now = datetime.utcnow()
    a = _file(now, row_id=5, file_id=9)
    assert s._same_scheduled_item(a, _file(now + timedelta(seconds=9), row_id=5, file_id=9, cue_in=2.2))
    assert not s._same_scheduled_item(a, _file(now, row_id=5, file_id=10))
    assert not s._same_scheduled_item(a, _file(now, row_id=6, file_id=9))
    w = _webstream(now)
    assert s._same_scheduled_item(w, _webstream(now + timedelta(seconds=30)))
    assert not s._same_scheduled_item(w, _webstream(now, stream_id=3))
    assert not s._same_scheduled_item(a, w)


def test_refresh_rebinds_a_re_timed_running_row(sched):
    """18:30:16 - schedule-remove moved the playing row 9 s and its cue-in
    2 s: rebind the key, no stop, no catch-up of the same track."""
    s, engine = sched
    now = datetime.utcnow()
    running = _file(now - timedelta(seconds=220), row_id=6252, file_id=614, seconds=300.0)
    s._playing_key, s._current_event = "2026-09-28-16-26-41#file-6252", running
    s._current_audio_path = "C:/cache/a.mp3"
    moved = _file(now - timedelta(seconds=211), row_id=6252, file_id=614, cue_in=2.18, seconds=300.0)

    with patch.object(s, "_on_file_start") as on_start:
        _refresh(s, {"2026-09-28-16-26-50#file-6252": moved})

    on_start.assert_not_called()
    engine.stop.assert_not_called()
    assert s._playing_key == "2026-09-28-16-26-50#file-6252"
    assert s._current_event is running        # the audio on air keeps its timing


def test_refresh_stops_a_running_row_moved_into_the_future(sched):
    s, engine = sched
    now = datetime.utcnow()
    running = _file(now - timedelta(seconds=20), row_id=7, file_id=3)
    s._playing_key, s._current_event = "K1", running
    s._current_audio_path = "C:/cache/a.mp3"
    s._queued_ahead = ("q", _file(now + timedelta(seconds=100), row_id=8, file_id=4))
    later = _file(now + timedelta(seconds=120), row_id=7, file_id=3)

    with patch.object(s, "_on_file_start") as on_start:
        timers = _refresh(s, {"K2": later})

    engine.stop.assert_called_once()
    on_start.assert_not_called()
    assert s._playing_key is None and s._current_event is None
    assert s._queued_ahead is None            # flushed with the stop
    assert timers["K2"][0] is not None        # armed for its new start


def test_refresh_still_removes_a_really_gone_row(sched):
    s, engine = sched
    now = datetime.utcnow()
    running = _file(now - timedelta(seconds=20), row_id=7, file_id=3)
    s._playing_key, s._current_event = "K1", running
    s._current_audio_path = "C:/cache/a.mp3"
    other = _file(now + timedelta(seconds=120), row_id=9, file_id=3)   # same file, other row

    _refresh(s, {"K2": other})

    engine.stop.assert_called_once()
    assert s._playing_key is None


def test_queue_ahead_re_enqueues_a_re_cued_successor(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=190), row_id=1, file_id=1)        # 10 s left
    queued = _file(now + timedelta(seconds=8), row_id=2, file_id=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("old", queued)
    # same row, same key shift: nothing to do
    s._on_file_queue_ahead("new", queued.model_copy(update={"start": queued.start + timedelta(seconds=1)}))
    engine.flush_queued.assert_not_called()
    engine.enqueue.assert_not_called()
    assert s._queued_ahead[0] == "new"
    # same row, re-cued by an edit: the queued request carries the old cues
    recued = _file(now + timedelta(seconds=8), row_id=2, file_id=2, cue_in=3.0)
    s._on_file_queue_ahead("new2", recued)
    engine.flush_queued.assert_called_once()
    engine.enqueue.assert_called_once()
    assert engine.enqueue.call_args.kwargs["cue_in"] == 3.0


# ---------------------------------------------------------------------------
# C - 20:05:35 incident: a refresh straddling a boundary, and the engine's
# "remaining" that belonged to the successor
# ---------------------------------------------------------------------------

def test_refresh_does_not_catch_up_a_predecessor_of_the_playing_item(sched):
    """The successor's PLAY fired while the refresh was fetching; the
    re-arm saw the predecessor 'in progress' (its row overlaps by the
    crossfade) and caught it up - cutting the successor."""
    s, _ = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=325), row_id=1, file_id=1, seconds=328.0)   # 3 s left
    cur = _file(now - timedelta(seconds=1), row_id=2, file_id=2)
    s._playing_key, s._current_event = "cur", cur
    with patch.object(s, "_on_file_start") as on_start:
        s._arm_file_event("prev", prev, now)
        start_t, stop_t = s._timers["prev"]
        stop_t.cancel()
    on_start.assert_not_called()
    assert start_t is None
    assert s._playing_key == "cur"
    # nothing on air: an in-progress row IS a catch-up
    s._playing_key, s._current_event = None, None
    with patch.object(s, "_on_file_start"):
        s._arm_file_event("prev", prev, now)
        start_t, stop_t = s._timers["prev"]
        start_t.cancel()
        stop_t.cancel()
    assert start_t is not None


def test_implausible_engine_remaining_means_the_hand_over_happened(sched):
    """'predecessor has 214.9 s of audio left' for a track with 3 s to go:
    the queue's remaining was the successor's.  No skip."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=322), row_id=1, file_id=1, seconds=325.0)
    nxt = _file(now, row_id=2, file_id=2)
    s._current_event, s._playing_key = prev, "p"
    s._current_started_at = now - timedelta(seconds=322)
    s._current_clip_seconds = 325.0
    s._queued_ahead = ("n", nxt)
    engine.playing_remaining_seconds.return_value = 214.9
    s._on_file_start("n", nxt)
    engine.adopt_queued.assert_called_once()
    assert engine.adopt_queued.call_args.kwargs["skip_current"] is False
    assert s._current_started_at >= now and s._current_clip_seconds == 200.0


def test_plausible_engine_remaining_still_skips_a_late_predecessor(sched):
    """Rehearsal 2 (2026-09-27): a predecessor that started 45 s late
    really has more audio left than its row says - the skip stays."""
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=145), row_id=1, file_id=1, seconds=300.0)
    nxt = _file(now, row_id=2, file_id=2)
    s._current_event, s._playing_key = prev, "p"
    s._current_started_at = now - timedelta(seconds=100)      # pushed 45 s late
    s._current_clip_seconds = 300.0
    s._queued_ahead = ("n", nxt)
    engine.playing_remaining_seconds.return_value = 200.0
    s._on_file_start("n", nxt)
    assert engine.adopt_queued.call_args.kwargs["skip_current"] is True


def test_file_start_records_push_time_and_clip_after_seek(sched):
    s, _ = sched
    before = datetime.utcnow()
    s._on_file_start("K", _file(before, cue_in=0.5, seconds=200.0), seek=41.0)
    assert s._current_started_at >= before
    assert s._current_clip_seconds == pytest.approx(158.5)


# ---------------------------------------------------------------------------
# D - 20:27:08 incident: a planned Liquidsoap restart at the boundary
# emptied the queue, the successor's PLAY adopted nothing -> dead air
# ---------------------------------------------------------------------------

def test_fresh_liquidsoap_instance_forgets_the_queued_successor(sched):
    s, _ = sched
    now = datetime.utcnow()
    s._queued_ahead = ("n", _file(now, row_id=2, file_id=2))
    s._queued_ahead_prev = _file(now - timedelta(seconds=100), row_id=1, file_id=1)
    s._current_started_at, s._current_clip_seconds = now, 200.0
    with patch.object(s, "_retry_initial_liquidsoap_state", return_value=True), \
         patch.object(s, "_request_source_reconcile"):
        s._after_liquidsoap_restart(attempts=1, delay=0.0)
    assert s._queued_ahead is None and s._queued_ahead_prev is None
    assert s._current_started_at is None and s._current_clip_seconds is None


def test_boundary_restart_pushes_the_successor_afresh(sched):
    s, engine = sched
    now = datetime.utcnow()
    prev = _file(now - timedelta(seconds=198), row_id=1, file_id=1, seconds=200.0)
    nxt = _file(now, row_id=2, file_id=2)
    s._current_event, s._playing_key = prev, "p"
    s._queued_ahead = ("n", nxt)
    s._boundary_restart_pending = "rastatime.liq changed"

    def restart(reason, settle_async=False):
        with patch.object(s, "_retry_initial_liquidsoap_state", return_value=True), \
             patch.object(s, "_request_source_reconcile"):
            s._after_liquidsoap_restart(attempts=1, delay=0.0)
        return True

    with patch.object(s, "_boundary_allows_restart", return_value=True), \
         patch.object(s, "_perform_planned_restart", side_effect=restart):
        s._on_file_start("n", nxt)
    engine.adopt_queued.assert_not_called()
    engine.play.assert_called_once()
    assert engine.play.call_args.kwargs["cue_in"] == 0.0
    assert s._playing_key == "n" and s._current_event is nxt


def test_crash_detected_restart_forgets_the_queued_successor(sched):
    s, engine = sched
    now = datetime.utcnow()
    s._queued_ahead = ("n", _file(now, row_id=2, file_id=2))
    s._last_liquidsoap_process = (100, 500.0)
    with patch.object(s, "_liquidsoap_process_identity", return_value=(200, 3.0)), \
         patch.object(s, "_apply_initial_liquidsoap_state", return_value=(True, None)), \
         patch.object(s, "_request_source_reconcile"):
        s._maybe_reinit_after_liquidsoap_restart()
    assert s._queued_ahead is None
