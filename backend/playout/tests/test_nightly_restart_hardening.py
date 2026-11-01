"""
RASTATIME 2026-09-07 - nightly/boot restart hardening after the
04:02-08:21 crash-loop outage:

* ``restart_liquidsoap_service`` verifies a non-zero ``nssm restart``
  by observation (``verify``) before retrying;
* the scheduler refuses the nightly restart when the fresh render
  addresses the Main Output by PortAudio index;
* the fresh instance must answer ``uptime`` with a small value and
  still be there after a settle time;
* the preflight flags a missing or crash-looping Liquidsoap
  (``liquidsoap_unavailable``).
"""

from __future__ import annotations

from datetime import datetime
from datetime import time as dtime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rastatime_playout import liquidsoap_health as lh
from rastatime_playout import liquidsoap_service as svc
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.liquidsoap_service import NightlyRestartPolicy
from rastatime_playout.preflight import PreflightChecker

# ---------------------------------------------------------------------------
# restart_liquidsoap_service(verify=...)
# ---------------------------------------------------------------------------


def _runner(codes):
    calls = []

    def run(argv, **kwargs):
        calls.append(list(argv))
        code = codes.pop(0)
        return SimpleNamespace(
            returncode=code,
            stdout="",
            stderr="Unexpected status SERVICE_PAUSED in response to START control." if code else "",
        )

    return run, calls


def _nssm(tmp_path):
    nssm = tmp_path / "nssm.exe"
    nssm.write_bytes(b"x")
    return str(nssm)


def test_nonzero_exit_but_verified_is_success_without_retry(tmp_path):
    run, calls = _runner([1, 1, 1])
    ok = svc.restart_liquidsoap_service(
        "t",
        nssm_exe=_nssm(tmp_path),
        service="SVC",
        runner=run,
        sleep=lambda _s: None,
        verify=lambda: True,
    )
    assert ok
    assert len(calls) == 1  # the fresh instance is NOT restarted again


def test_nonzero_exit_and_verify_false_retries(tmp_path):
    run, calls = _runner([1, 1, 1])
    ok = svc.restart_liquidsoap_service(
        "t",
        nssm_exe=_nssm(tmp_path),
        service="SVC",
        runner=run,
        sleep=lambda _s: None,
        verify=lambda: False,
    )
    assert not ok
    assert len(calls) == 3


def test_verify_exception_counts_as_not_verified(tmp_path):
    def boom():
        raise RuntimeError("telnet down")

    run, calls = _runner([1, 1, 1])
    ok = svc.restart_liquidsoap_service(
        "t",
        nssm_exe=_nssm(tmp_path),
        service="SVC",
        runner=run,
        sleep=lambda _s: None,
        verify=boom,
    )
    assert not ok
    assert len(calls) == 3


def test_zero_exit_does_not_consult_verify(tmp_path):
    verify = MagicMock(return_value=False)
    run, calls = _runner([0])
    ok = svc.restart_liquidsoap_service(
        "t",
        nssm_exe=_nssm(tmp_path),
        service="SVC",
        runner=run,
        sleep=lambda _s: None,
        verify=verify,
    )
    assert ok
    verify.assert_not_called()


# ---------------------------------------------------------------------------
# scheduler: name-safe or not at all, verification, stays-up check
# ---------------------------------------------------------------------------


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.liquidsoap_uptime_seconds.return_value = 5000.0
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    render = MagicMock(return_value=True)
    s = ps.PlayoutScheduler(
        engine=engine,
        api_client=MagicMock(),
        render_liquidsoap=render,
        nightly_restart=NightlyRestartPolicy(start=dtime(4, 0), quiet_margin_seconds=300),
    )
    s.reset_gates = MagicMock()
    s._test = {"render": render, "restart": restart, "engine": engine}
    return s


IN_WINDOW = datetime(2026, 9, 7, 4, 1)


def test_index_render_skips_the_restart(sched, caplog):
    sched._test["render"].return_value = SimpleNamespace(
        changed=True,
        main_output_mode=svc.MAIN_OUTPUT_BY_INDEX,
    )
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_not_called()
    assert sched._nightly_restart_done == IN_WINDOW.date()  # not retried today
    assert any("skipped" in r.message for r in caplog.records)


@pytest.mark.parametrize("mode", [svc.MAIN_OUTPUT_BY_NAME, svc.MAIN_OUTPUT_DEFAULT])
def test_name_or_default_render_restarts_with_verification(sched, mode):
    sched._test["render"].return_value = SimpleNamespace(changed=True, main_output_mode=mode)
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_called_once()
    assert sched._test["restart"].call_args.kwargs["verify"] == sched._liquidsoap_restarted_recently


def test_legacy_bool_render_still_restarts(sched):
    sched._test["render"].return_value = True
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_called_once()


def test_restarted_recently_polls_until_fresh_uptime(sched):
    engine = sched._test["engine"]
    engine.liquidsoap_uptime_seconds.reset_mock()  # the constructor seeded once
    engine.liquidsoap_uptime_seconds.side_effect = [None, 5000.0, 3.0]
    assert sched._liquidsoap_restarted_recently(timeout=30.0, sleep=lambda _s: None)
    assert engine.liquidsoap_uptime_seconds.call_count == 3


def test_restarted_recently_times_out(sched, monkeypatch):
    engine = sched._test["engine"]
    engine.liquidsoap_uptime_seconds.return_value = None
    clock = iter([0.0, 1.0, 40.0, 41.0, 42.0])
    monkeypatch.setattr(ps.time, "monotonic", lambda: next(clock))
    assert not sched._liquidsoap_restarted_recently(timeout=30.0, sleep=lambda _s: None)


def test_stays_up_check_logs_error_when_down(sched, caplog):
    sched._test["engine"].liquidsoap_uptime_seconds.return_value = None
    assert not sched._confirm_liquidsoap_stays_up(settle_seconds=0.0, sleep=lambda _s: None)
    assert any("DOWN again" in r.message for r in caplog.records)


def test_stays_up_check_ok(sched):
    sched._test["engine"].liquidsoap_uptime_seconds.return_value = 12.0
    assert sched._confirm_liquidsoap_stays_up(settle_seconds=0.0, sleep=lambda _s: None)


# ---------------------------------------------------------------------------
# preflight: liquidsoap_unavailable
# ---------------------------------------------------------------------------

TASCAM = "Tascam-Lautsprecher (US-16x08)"
UNAVAILABLE = PreflightChecker.WARNING_TYPE_LIQUIDSOAP_UNAVAILABLE


@pytest.fixture
def checker(monkeypatch):
    c = PreflightChecker(api_client=MagicMock())
    submitted = {}

    def _submit(warning_type, scan_run_id, warnings):
        submitted[warning_type] = warnings

    monkeypatch.setattr(c, "_submit_warnings", _submit)
    monkeypatch.setattr(c, "_expected_main_output_name", lambda: TASCAM)
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [9064]})
    monkeypatch.delenv(lh.MEMORY_WARN_ENV, raising=False)
    c._submitted = submitted
    return c


def test_no_process_is_an_error(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: [])
    checker._scan_liquidsoap_health()
    w = checker._submitted[UNAVAILABLE]
    assert len(w) == 1
    assert w[0]["severity"] == "error"
    assert w[0]["detail"]["crash_loop"] is False
    assert "not running" in w[0]["detail"]["message"]
    # the other two types are cleared, not invented
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY] == []


def test_healthy_old_process_clears_the_type(checker, monkeypatch):
    monkeypatch.setattr(
        lh, "liquidsoap_process_info", lambda: [lh.ProcessInfo(9064, 200.0, 5000.0)]
    )
    checker._scan_liquidsoap_health()
    checker._scan_liquidsoap_health()
    assert checker._submitted[UNAVAILABLE] == []


def test_one_fresh_process_is_not_a_crash_loop(checker, monkeypatch):
    # a legitimate (nightly) restart: one young PID, then it ages
    scans = [
        [lh.ProcessInfo(9064, 200.0, 5000.0)],
        [lh.ProcessInfo(9100, 80.0, 20.0)],
        [lh.ProcessInfo(9100, 85.0, 920.0)],
    ]
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: scans.pop(0))
    for _ in range(3):
        checker._scan_liquidsoap_health()
        assert checker._submitted[UNAVAILABLE] == []


def test_new_young_pid_on_consecutive_scans_is_a_crash_loop(checker, monkeypatch):
    scans = [[lh.ProcessInfo(100, 80.0, 1.5)], [lh.ProcessInfo(101, 80.0, 1.2)]]
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: scans.pop(0))
    checker._scan_liquidsoap_health()
    assert checker._submitted[UNAVAILABLE] == []
    checker._scan_liquidsoap_health()
    w = checker._submitted[UNAVAILABLE]
    assert len(w) == 1
    assert w[0]["detail"]["crash_loop"] is True
    assert w[0]["detail"]["pids"] == [100, 101]
    assert "keeps restarting" in w[0]["detail"]["message"]


def test_probe_unavailable_clears_the_type(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: None)
    checker._scan_liquidsoap_health()
    assert checker._submitted[UNAVAILABLE] == []
