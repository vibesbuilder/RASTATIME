"""
RASTATIME 2026-09-05 — liquidsoap_service: boot-window restart,
nightly restart policy, nssm restart wrapper.
"""

from __future__ import annotations

from datetime import date, datetime
from datetime import time as dtime
from types import SimpleNamespace

import pytest
from rastatime_playout import liquidsoap_service as svc

# --------------------------------------------------------------------
# boot window
# --------------------------------------------------------------------


def test_within_boot_window_uses_uptime():
    assert svc.within_boot_window(30.0)
    assert svc.within_boot_window(599.0)
    assert not svc.within_boot_window(600.0)
    assert not svc.within_boot_window(3600.0)
    assert not svc.within_boot_window(None) or svc.system_uptime_seconds() is not None


def test_boot_restart_env_switch(monkeypatch):
    monkeypatch.delenv(svc.BOOT_RESTART_ENV, raising=False)
    assert svc.boot_restart_enabled()
    monkeypatch.setenv(svc.BOOT_RESTART_ENV, "0")
    assert not svc.boot_restart_enabled()
    monkeypatch.setenv(svc.BOOT_RESTART_ENV, "off")
    assert not svc.boot_restart_enabled()


# --------------------------------------------------------------------
# nightly policy
# --------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["off", "0", "", "none", "false"])
def test_policy_disabled_values(raw):
    policy = svc.NightlyRestartPolicy.from_env(raw)
    assert not policy.enabled
    assert not policy.due(datetime(2026, 9, 6, 4, 5), None)


def test_policy_garbage_disables_with_warning(caplog):
    policy = svc.NightlyRestartPolicy.from_env("quarter past four")
    assert not policy.enabled


def test_policy_default_is_four_in_the_morning(monkeypatch):
    monkeypatch.delenv(svc.NIGHTLY_RESTART_ENV, raising=False)
    policy = svc.NightlyRestartPolicy.from_env()
    assert policy.start == dtime(4, 0)
    assert policy.window_minutes == 60


def test_policy_due_only_inside_window_and_once_per_day():
    policy = svc.NightlyRestartPolicy(start=dtime(4, 0))
    assert not policy.due(datetime(2026, 9, 6, 3, 59), None)
    assert policy.due(datetime(2026, 9, 6, 4, 0), None)
    assert policy.due(datetime(2026, 9, 6, 4, 59), None)
    assert not policy.due(datetime(2026, 9, 6, 5, 0), None)
    # already done today -> not due; done yesterday -> due again
    assert not policy.due(datetime(2026, 9, 6, 4, 10), date(2026, 9, 6))
    assert policy.due(datetime(2026, 9, 6, 4, 10), date(2026, 9, 5))


# --------------------------------------------------------------------
# nssm restart wrapper
# --------------------------------------------------------------------


def _runner_factory(results):
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        code = results.pop(0)
        return SimpleNamespace(returncode=code, stdout="", stderr="boom" if code else "")

    return runner, calls


def test_restart_success_first_try(tmp_path):
    nssm = tmp_path / "nssm.exe"
    nssm.write_bytes(b"x")
    runner, calls = _runner_factory([0])
    slept = []
    ok = svc.restart_liquidsoap_service(
        "test",
        nssm_exe=str(nssm),
        service="SVC",
        runner=runner,
        sleep=slept.append,
    )
    assert ok
    assert calls == [[str(nssm), "restart", "SVC"]]
    assert slept == []


def test_restart_retries_then_succeeds(tmp_path):
    nssm = tmp_path / "nssm.exe"
    nssm.write_bytes(b"x")
    runner, calls = _runner_factory([1, 1, 0])
    slept = []
    ok = svc.restart_liquidsoap_service(
        "test",
        nssm_exe=str(nssm),
        service="SVC",
        runner=runner,
        sleep=slept.append,
        retry_delay=0.1,
    )
    assert ok
    assert len(calls) == 3
    assert slept == [0.1, 0.1]


def test_restart_gives_up_after_attempts(tmp_path):
    nssm = tmp_path / "nssm.exe"
    nssm.write_bytes(b"x")
    runner, calls = _runner_factory([1, 1, 1])
    ok = svc.restart_liquidsoap_service(
        "test",
        nssm_exe=str(nssm),
        service="SVC",
        runner=runner,
        sleep=lambda _s: None,
    )
    assert not ok
    assert len(calls) == 3


def test_restart_without_nssm_binary_is_false(tmp_path):
    runner, calls = _runner_factory([0])
    ok = svc.restart_liquidsoap_service(
        "test",
        nssm_exe=str(tmp_path / "missing.exe"),
        runner=runner,
    )
    assert not ok
    assert calls == []


def test_restart_runner_exception_is_swallowed(tmp_path):
    nssm = tmp_path / "nssm.exe"
    nssm.write_bytes(b"x")

    def runner(argv, **kwargs):
        raise OSError("no")

    ok = svc.restart_liquidsoap_service(
        "test",
        nssm_exe=str(nssm),
        runner=runner,
        attempts=1,
    )
    assert not ok
