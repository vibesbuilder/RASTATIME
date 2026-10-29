"""
RASTATIME 2026-09-09 - the scheduler notices a LIQUIDSOAP restart from the
process table (new PID or younger age of the main instance) instead of
the telnet ``uptime`` command: every telnet command leaks ~87-155 KB on
the Windows build, and the ``uptime`` poll was one of the last three
periodic commands.  The telnet path stays as the fallback.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rastatime_playout import liquidsoap_health as lh
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.source_switcher import SourceSwitcher

MAIN_SCRIPT = "C:\\Tools\\liquidsoap\\rastatime.liq"
STANDBY_SCRIPT = "C:\\Tools\\liquidsoap\\standby.liq"


def _main(pid, age, mb=100.0):
    return lh.ProcessInfo(pid, mb, age, MAIN_SCRIPT)


def _standby(age=99999.0):
    return lh.ProcessInfo(4348, 78.0, age, STANDBY_SCRIPT)


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    table = {"infos": [], "calls": 0}

    def probe():
        table["calls"] += 1
        return table["infos"]

    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", probe)
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
    )
    s.reset_gates = MagicMock()
    switcher = SourceSwitcher(switch_callback=lambda _state: None)
    s.set_source_switcher(switcher)
    engine.recording_stop.reset_mock()
    engine.liquidsoap_uptime_seconds.reset_mock()
    return s, engine, switcher, table


def _seed(s, table, pid=14516, age=300.0):
    table["infos"] = [_standby(), _main(pid, age)]
    s._maybe_reinit_after_liquidsoap_restart()
    assert s._last_liquidsoap_process == (pid, age)


def test_first_cycle_seeds_silently_with_the_main_instance(sched):
    s, engine, switcher, table = sched
    _seed(s, table)                                      # not the older standby
    engine.recording_stop.assert_not_called()
    assert switcher.wait_reconcile(0) is False
    engine.liquidsoap_uptime_seconds.assert_not_called()   # no telnet at all


def test_same_pid_growing_age_is_a_noop(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    table["infos"] = [_standby(), _main(14516, 420.0)]
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()
    assert s._last_liquidsoap_process == (14516, 420.0)
    assert switcher.wait_reconcile(0) is False


def test_new_pid_triggers_reinit_and_reconcile(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    table["infos"] = [_standby(), _main(15000, 40.0)]
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_called_once()
    assert s.reset_gates.call_count == 1
    assert s._last_liquidsoap_process == (15000, 40.0)
    assert switcher.wait_reconcile(0) is True
    engine.liquidsoap_uptime_seconds.assert_called_once()  # only the re-init's seed


def test_same_pid_younger_age_triggers_reinit(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    table["infos"] = [_main(14516, 20.0)]                # PID reused, fresh process
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_called_once()
    assert switcher.wait_reconcile(0) is True


def test_small_age_jitter_is_not_a_restart(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    table["infos"] = [_main(14516, 297.0)]               # 3 s < 5 s margin
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()


def test_failed_reinit_keeps_the_baseline_for_a_retry(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    engine.recording_stop.side_effect = ConnectionError("telnet not up yet")
    table["infos"] = [_main(15000, 3.0)]
    s._maybe_reinit_after_liquidsoap_restart()
    assert s._last_liquidsoap_process == (14516, 300.0)   # baseline kept
    assert switcher.wait_reconcile(0) is False
    engine.recording_stop.side_effect = None
    table["infos"] = [_main(15000, 123.0)]
    s._maybe_reinit_after_liquidsoap_restart()             # retried next cycle
    assert s._last_liquidsoap_process == (15000, 123.0)
    assert switcher.wait_reconcile(0) is True


def test_planned_restart_resets_the_baseline_so_the_fresh_pid_seeds_silently(sched):
    s, engine, switcher, table = sched
    _seed(s, table)
    ok, _ = s._apply_initial_liquidsoap_state()            # what a planned restart runs
    assert ok
    assert s._last_liquidsoap_process is None
    engine.recording_stop.reset_mock()
    table["infos"] = [_main(15000, 12.0)]
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()               # no second "restarted" round
    assert s._last_liquidsoap_process == (15000, 12.0)


def test_probe_unavailable_falls_back_to_telnet_uptime(sched):
    s, engine, switcher, table = sched
    table["infos"] = None
    engine.liquidsoap_uptime_seconds.return_value = 12.0   # constructor seeded 1000 s
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_called_once()
    assert switcher.wait_reconcile(0) is True


def test_standby_only_table_uses_the_telnet_fallback(sched):
    s, engine, switcher, table = sched
    table["infos"] = [_standby()]
    engine.liquidsoap_uptime_seconds.return_value = 1100.0
    s._maybe_reinit_after_liquidsoap_restart()
    engine.liquidsoap_uptime_seconds.assert_called_once()
    engine.recording_stop.assert_not_called()
    assert s._last_liquidsoap_process is None


def test_probe_reports_the_main_instance_not_the_oldest(sched):
    s, engine, switcher, table = sched
    table["infos"] = [_standby(age=99999.0), _main(14516, 5313.0, mb=125.0)]
    assert s._liquidsoap_process_probe() == (5313.0, 125.0)
    assert s._liquidsoap_process_identity() == (14516, 5313.0)


def test_probe_without_script_info_keeps_the_oldest_rule(sched):
    s, engine, switcher, table = sched
    table["infos"] = [lh.ProcessInfo(1, 50.0, 10.0), lh.ProcessInfo(2, 60.0, 900.0)]
    assert s._liquidsoap_process_probe() == (900.0, 60.0)


def test_process_table_is_read_once_per_cycle(sched):
    s, engine, switcher, table = sched
    table["infos"] = [_main(1, 10.0)]
    s._cycle_process_cache_enabled = True
    s._cycle_process_infos = None
    s._liquidsoap_process_identity()
    s._liquidsoap_process_probe()
    s._liquidsoap_main_process()
    assert table["calls"] == 1
    s._cycle_process_cache_enabled = False                # outside a cycle: every call reads
    s._cycle_process_infos = None
    s._liquidsoap_process_identity()
    s._liquidsoap_process_probe()
    assert table["calls"] == 3
