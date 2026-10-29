"""
RASTATIME 2026-09-09 - planned LIQUIDSOAP restart for a 24/7 programme:

* NightlyRestartPolicy.reason_due: daily window (as before), every N days
  by process age, soft memory limit inside the window, hard memory limit at
  any time; env parsing.
* PlayoutScheduler: quiet moment -> restart at once; something on air ->
  arm a restart at the next file-to-file track boundary, executed by
  _on_file_start; webstream / line-in boundaries keep waiting; failed
  attempts are rate-limited.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from rastatime_playout import liquidsoap_service as svc
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.liquidsoap_service import NightlyRestartPolicy
from rastatime_playout.player.events import EventKind, FileEvent, WebStreamEvent

IN_WINDOW = datetime(2026, 9, 9, 4, 10)
DAYTIME = datetime(2026, 9, 9, 15, 0)
DAY = 86400.0


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------

def test_daily_window_without_probe_keeps_the_old_semantics():
    p = NightlyRestartPolicy(start=dtime(4, 0))
    assert p.reason_due(IN_WINDOW, None) == "daily window"
    assert p.reason_due(IN_WINDOW, IN_WINDOW.date()) is None          # done today
    assert p.reason_due(DAYTIME, None) is None                          # outside the window
    assert p.due(IN_WINDOW, None) and not p.due(DAYTIME, None)


def test_interval_uses_the_process_age():
    p = NightlyRestartPolicy(start=dtime(4, 0), every_days=7)
    assert p.reason_due(IN_WINDOW, None, age_seconds=2 * DAY) is None       # too young
    assert "days old" in p.reason_due(IN_WINDOW, None, age_seconds=6.5 * DAY)
    daily = NightlyRestartPolicy(start=dtime(4, 0), every_days=1)
    assert daily.reason_due(IN_WINDOW, None, age_seconds=23.9 * 3600)       # restarted 04:01 yesterday
    assert daily.reason_due(IN_WINDOW, None, age_seconds=5 * 3600) is None  # manual restart last evening


def test_soft_memory_limit_only_inside_the_window():
    p = NightlyRestartPolicy(start=dtime(4, 0), every_days=30, memory_soft_mb=1536)
    assert p.reason_due(DAYTIME, None, age_seconds=DAY, private_mb=1700) is None
    assert "1700 MB >= 1536 MB" in p.reason_due(IN_WINDOW, None, age_seconds=DAY, private_mb=1700)
    assert p.reason_due(IN_WINDOW, None, age_seconds=DAY, private_mb=900) is None


def test_hard_memory_limit_at_any_time_and_even_when_done_today():
    p = NightlyRestartPolicy(start=dtime(4, 0), memory_hard_mb=3072)
    assert "hard limit" in p.reason_due(DAYTIME, DAYTIME.date(), age_seconds=DAY, private_mb=3100)
    assert p.reason_due(DAYTIME, None, age_seconds=DAY, private_mb=3000) is None


def test_triggers_can_be_switched_off():
    p = NightlyRestartPolicy(start=dtime(4, 0), every_days=0, memory_soft_mb=None, memory_hard_mb=None)
    assert p.reason_due(IN_WINDOW, None, age_seconds=30 * DAY, private_mb=9000) is None
    off = NightlyRestartPolicy(start=None)
    assert off.reason_due(DAYTIME, None, age_seconds=DAY, private_mb=9000) is None


def test_from_env_reads_the_triggers(monkeypatch):
    monkeypatch.setenv(svc.NIGHTLY_RESTART_ENV, "03:30")
    monkeypatch.setenv(svc.RESTART_EVERY_DAYS_ENV, "7")
    monkeypatch.setenv(svc.RESTART_SOFT_MB_ENV, "2000")
    monkeypatch.setenv(svc.RESTART_HARD_MB_ENV, "off")
    p = NightlyRestartPolicy.from_env()
    assert p.start == dtime(3, 30) and p.every_days == 7
    assert p.memory_soft_mb == 2000 and p.memory_hard_mb is None
    monkeypatch.setenv(svc.RESTART_EVERY_DAYS_ENV, "banana")
    monkeypatch.setenv(svc.RESTART_SOFT_MB_ENV, "12")            # below the 256 floor
    p = NightlyRestartPolicy.from_env()
    assert p.every_days == svc.DEFAULT_RESTART_EVERY_DAYS and p.memory_soft_mb == 256


# ---------------------------------------------------------------------------
# scheduler
# ---------------------------------------------------------------------------

def _file_event(key_start: datetime, minutes: int = 4) -> FileEvent:
    return FileEvent(
        type=EventKind.FILE, start=key_start, end=key_start + timedelta(minutes=minutes),
        row_id=1, id=1, uri="C:/media/a.mp3", show_name="night", cue_in=0.0,
        cue_out=float(minutes * 60), track_title="t", artist_name="a", replay_gain=None,
        fade_in=0.0, fade_out=0.0, mime="audio/mpeg", filesize=1000,
    )


def _webstream_event(key_start: datetime) -> WebStreamEvent:
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START, start=key_start,
        end=key_start + timedelta(minutes=4), row_id=2, id=2,
        uri="http://cloud/", show_name="vah", input_gain_db=None,
    )


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.liquidsoap_uptime_seconds.return_value = 5.0
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    probe = MagicMock(return_value=[SimpleNamespace(pid=1, private_mb=900.0, age_seconds=DAY)])
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", probe)
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
        render_liquidsoap=MagicMock(return_value=True),
        nightly_restart=NightlyRestartPolicy(start=dtime(4, 0), quiet_margin_seconds=300),
    )
    s.reset_gates = MagicMock()
    s._confirm_liquidsoap_stays_up = MagicMock(return_value=True)
    s._test = {"restart": restart, "engine": engine, "probe": probe}
    return s


def test_quiet_moment_restarts_at_once(sched):
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_called_once()
    assert sched._boundary_restart_pending is None
    assert sched._nightly_restart_done == IN_WINDOW.date()


def test_on_air_arms_a_boundary_restart_instead(sched):
    sched._current_event = _file_event(IN_WINDOW - timedelta(minutes=2))
    sched._playing_key = "k"
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_not_called()
    assert sched._boundary_restart_pending and "day" in sched._boundary_restart_pending
    # armed: later polls do not re-arm or restart
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW + timedelta(minutes=2))
    sched._test["restart"].assert_not_called()


def test_boundary_rules():
    f, w = _file_event(IN_WINDOW), _webstream_event(IN_WINDOW)
    assert ps.PlayoutScheduler._boundary_allows_restart(None, f)
    assert ps.PlayoutScheduler._boundary_allows_restart(f, f)
    assert not ps.PlayoutScheduler._boundary_allows_restart(w, f)
    assert not ps.PlayoutScheduler._boundary_allows_restart(f, w)


def test_file_start_performs_the_armed_restart_before_playing(sched, monkeypatch):
    sched._boundary_restart_pending = "daily window"
    # 2026-10-02: row times are "now" - the restart happens at the row's own
    # timer, and the track then enters its audio by the time it took.
    row_start = datetime.utcnow()
    sched._current_event = _file_event(row_start - timedelta(minutes=4))
    monkeypatch.setattr(sched, "_ensure_file_cached", lambda e: "C:/cache/a.mp3")
    for name in ("_cue_item_start", "_notify_media_started", "_close_predecessor_source",
                 "_arm_stop_timer"):
        if hasattr(sched, name):
            monkeypatch.setattr(sched, name, MagicMock())
    calls = []
    sched._test["restart"].side_effect = lambda *a, **k: calls.append("restart") or True
    sched._test["engine"].play.side_effect = lambda *a, **k: calls.append("play")
    sched._on_file_start("2026-09-09-02-10-00", _file_event(row_start))
    assert calls[:2] == ["restart", "play"]          # fresh instance first, then the track
    assert sched._boundary_restart_pending is None
    assert sched._test["restart"].call_args.kwargs["verify"] == sched._liquidsoap_restarted_recently


def test_webstream_boundary_keeps_waiting(sched, monkeypatch):
    sched._boundary_restart_pending = "daily window"
    sched._current_event = _webstream_event(IN_WINDOW - timedelta(minutes=4))
    monkeypatch.setattr(sched, "_ensure_file_cached", lambda e: "C:/cache/a.mp3")
    for name in ("_cue_item_start", "_notify_media_started", "_close_predecessor_source",
                 "_arm_stop_timer"):
        if hasattr(sched, name):
            monkeypatch.setattr(sched, name, MagicMock())
    sched._on_file_start("k", _file_event(IN_WINDOW))
    sched._test["restart"].assert_not_called()
    assert sched._boundary_restart_pending == "daily window"


def test_memory_hard_limit_fires_in_the_afternoon(sched):
    sched._test["probe"].return_value = [SimpleNamespace(pid=1, private_mb=3200.0, age_seconds=3 * 3600)]
    assert sched._maybe_nightly_restart(now_local=DAYTIME)
    sched._test["restart"].assert_called_once()
    assert "hard limit" in sched._test["restart"].call_args.args[0]


def test_failed_attempt_is_rate_limited(sched):
    sched._test["restart"].return_value = False
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    assert sched._test["restart"].call_count == 1
    sched._nightly_restart_done = None                    # pretend a new day is not the point
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW + timedelta(minutes=10))
    assert sched._test["restart"].call_count == 1        # not hammered within 30 min
