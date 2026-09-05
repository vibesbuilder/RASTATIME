"""
RASTATIME 2026-09-05 — PreflightChecker: Liquidsoap memory threshold and
Main-Output session watchdog.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout import liquidsoap_health as lh
from libretime_playout.preflight import PreflightChecker

TASCAM = "Tascam-Lautsprecher (US-16x08)"


@pytest.fixture
def checker(monkeypatch):
    c = PreflightChecker(api_client=MagicMock())
    submitted = {}

    def _submit(warning_type, scan_run_id, warnings):
        submitted[warning_type] = warnings

    monkeypatch.setattr(c, "_submit_warnings", _submit)
    monkeypatch.setattr(c, "_expected_main_output_name", lambda: TASCAM)
    monkeypatch.delenv(lh.MEMORY_WARN_ENV, raising=False)
    c._submitted = submitted
    return c


def _procs(private_mb, age=5000.0):
    return [lh.ProcessInfo(pid=9064, private_mb=private_mb, age_seconds=age)]


def test_memory_below_threshold_clears_the_type(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(900))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [9064]})
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY] == []
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_memory_above_threshold_warns(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(3400))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [9064]})
    checker._scan_liquidsoap_health()
    warnings = checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY]
    assert len(warnings) == 1
    w = warnings[0]
    assert w["severity"] == "warning"
    assert w["show_id"] is None and w["starts_at"] is None
    assert w["detail"]["private_mb"] == 3400
    assert w["detail"]["threshold_mb"] == lh.DEFAULT_MEMORY_WARN_MB
    assert "restart" in w["detail"]["message"].lower()


def test_memory_twice_threshold_is_an_error(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(4200))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [9064]})
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY][0]["severity"] == "error"


def test_memory_threshold_from_env(checker, monkeypatch):
    monkeypatch.setenv(lh.MEMORY_WARN_ENV, "512")
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(600))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [9064]})
    checker._scan_liquidsoap_health()
    assert len(checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY]) == 1


def test_session_on_wrong_endpoint_is_an_error(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(500))
    monkeypatch.setattr(
        lh, "render_endpoint_sessions",
        lambda: {"Realtek-Lautsprecher (Realtek(R) Audio)": [9064], TASCAM: [], "Jabra": [1234]},
    )
    checker._scan_liquidsoap_health()
    warnings = checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION]
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "error"
    assert warnings[0]["detail"]["expected"] == TASCAM
    assert warnings[0]["detail"]["actual"] == ["Realtek-Lautsprecher (Realtek(R) Audio)"]


def test_young_process_is_not_judged(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(500, age=20.0))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {"Realtek": [9064]})
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_probe_unavailable_clears_both_types(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: None)
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY] == []
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_session_api_unavailable_means_no_session_warning(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(500))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: None)
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_no_expected_output_means_no_session_warning(checker, monkeypatch):
    monkeypatch.setattr(checker, "_expected_main_output_name", lambda: "")
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: _procs(500))
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {"Realtek": [9064]})
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_process_info_parses_powershell_output(monkeypatch):
    monkeypatch.setattr(lh.sys, "platform", "win32")

    def runner(argv, **kwargs):
        return MagicMock(returncode=0, stdout="9064 3418 7300\n", stderr="")

    infos = lh.liquidsoap_process_info(runner=runner)
    assert infos == [lh.ProcessInfo(pid=9064, private_mb=3418.0, age_seconds=7300.0)]


def test_endpoints_holding():
    sessions = {"A": [1, 2], "B": [3], "C": []}
    assert lh.endpoints_holding(sessions, [2]) == ["A"]
    assert lh.endpoints_holding(sessions, [9]) == []
