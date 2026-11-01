"""
RASTATIME 2026-09-09 - the preflight judges the main Liquidsoap instance
only: the standby source is a second liquidsoap.exe, so a standby-only
process table means "Liquidsoap is down" and memory warnings name the
main instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from rastatime_playout import liquidsoap_health as lh
from rastatime_playout.preflight import PreflightChecker

TASCAM = "Tascam-Lautsprecher (US-16x08)"
MAIN = lh.ProcessInfo(14516, 3400.0, 5000.0, "C:\\Tools\\liquidsoap\\rastatime.liq")
STANDBY = lh.ProcessInfo(4348, 78.0, 12954.0, "C:\\Tools\\liquidsoap\\standby.liq")


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


def test_standby_alone_counts_as_liquidsoap_down(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: [STANDBY])
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [4348]})
    checker._scan_liquidsoap_health()
    unavailable = checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_UNAVAILABLE]
    assert len(unavailable) == 1
    assert unavailable[0]["severity"] == "error"
    assert unavailable[0]["detail"]["crash_loop"] is False
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY] == []


def test_memory_warning_names_the_main_instance_not_the_standby(checker, monkeypatch):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: [STANDBY, MAIN])
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [14516]})
    checker._scan_liquidsoap_health()
    memory = checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_MEMORY]
    assert [w["detail"]["pid"] for w in memory] == [14516]
    assert checker._submitted[PreflightChecker.WARNING_TYPE_LIQUIDSOAP_UNAVAILABLE] == []
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] == []


def test_standby_session_does_not_hide_a_missing_main_output_session(checker, monkeypatch):
    main_quiet = lh.ProcessInfo(14516, 300.0, 5000.0, "C:\\Tools\\liquidsoap\\rastatime.liq")
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: [STANDBY, main_quiet])
    # only the standby "holds" the Tascam (it cannot, but the table must not be fooled)
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [4348]})
    checker._scan_liquidsoap_health()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_MAIN_OUTPUT_SESSION] != []
