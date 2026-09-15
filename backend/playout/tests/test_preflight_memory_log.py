"""
RASTATIME 2026-09-15 - the preflight scan records the main Liquidsoap
instance's memory in the playout log: one INFO line per scan with the
absolute value, the age, the growth since the first sample of that
instance and the average rate.  The memory week of 2026-09-08..15 had no
such record; the next evaluation should be a grep, not a measuring session.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from libretime_playout import liquidsoap_health as lh
from libretime_playout.preflight import PreflightChecker

TASCAM = "Tascam-Lautsprecher (US-16x08)"
H = 3600.0


@pytest.fixture
def checker(monkeypatch):
    c = PreflightChecker(api_client=MagicMock())
    monkeypatch.setattr(c, "_submit_warnings", lambda *a, **k: None)
    monkeypatch.setattr(c, "_expected_main_output_name", lambda: TASCAM)
    monkeypatch.setattr(lh, "render_endpoint_sessions", lambda: {TASCAM: [16424, 777]})
    monkeypatch.delenv(lh.MEMORY_WARN_ENV, raising=False)
    return c


def _scan(checker, monkeypatch, caplog, procs):
    monkeypatch.setattr(lh, "liquidsoap_process_info", lambda: procs)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="libretime_playout.preflight"):
        checker._scan_liquidsoap_health()
    return [r.getMessage() for r in caplog.records if "Liquidsoap memory:" in r.getMessage()]


def _main(mb, age):
    return lh.ProcessInfo(pid=16424, private_mb=mb, age_seconds=age, script="C:/Tools/liquidsoap/rastatime.liq")


def test_first_scan_logs_the_baseline(checker, monkeypatch, caplog):
    lines = _scan(checker, monkeypatch, caplog, [_main(103.0, 0.2 * H)])
    assert lines == ["preflight: Liquidsoap memory: PID 16424 103 MB, 0.2 h old (first sample of this instance)."]


def test_later_scans_log_growth_and_rate_since_the_first_sample(checker, monkeypatch, caplog):
    _scan(checker, monkeypatch, caplog, [_main(103.0, 0.2 * H)])
    lines = _scan(checker, monkeypatch, caplog, [_main(333.0, 24.4 * H)])
    assert lines == [
        "preflight: Liquidsoap memory: PID 16424 333 MB, 24.4 h old, "
        "+230 MB since the first sample 24.2 h ago, 9.5 MB/h."
    ]


def test_rate_is_omitted_while_the_span_is_short(checker, monkeypatch, caplog):
    _scan(checker, monkeypatch, caplog, [_main(103.0, 0.2 * H)])
    lines = _scan(checker, monkeypatch, caplog, [_main(110.0, 0.45 * H)])
    assert lines == [
        "preflight: Liquidsoap memory: PID 16424 110 MB, 0.5 h old, "
        "+7 MB since the first sample 0.2 h ago."
    ]


def test_a_shrinking_instance_logs_a_negative_delta(checker, monkeypatch, caplog):
    _scan(checker, monkeypatch, caplog, [_main(300.0, 1.0 * H)])
    lines = _scan(checker, monkeypatch, caplog, [_main(280.0, 2.0 * H)])
    assert lines[0].endswith("-20 MB since the first sample 1.0 h ago, -20.0 MB/h.")


def test_a_fresh_instance_starts_a_new_baseline(checker, monkeypatch, caplog):
    _scan(checker, monkeypatch, caplog, [_main(300.0, 20.0 * H)])
    # NSSM restarted the engine: new PID, young
    fresh = lh.ProcessInfo(pid=777, private_mb=100.0, age_seconds=120.0, script="rastatime.liq")
    lines = _scan(checker, monkeypatch, caplog, [fresh])
    assert lines == ["preflight: Liquidsoap memory: PID 777 100 MB, 0.0 h old (first sample of this instance)."]
    assert 16424 not in checker._liquidsoap_memory_baseline     # old instance forgotten
    # same PID reused but younger than the baseline -> also a fresh instance
    _scan(checker, monkeypatch, caplog, [lh.ProcessInfo(pid=777, private_mb=400.0, age_seconds=10 * H, script="rastatime.liq")])
    lines = _scan(checker, monkeypatch, caplog, [lh.ProcessInfo(pid=777, private_mb=90.0, age_seconds=60.0, script="rastatime.liq")])
    assert "first sample" in lines[0]


def test_standby_instance_is_not_logged(checker, monkeypatch, caplog):
    standby = lh.ProcessInfo(pid=13280, private_mb=81.0, age_seconds=50 * H, script="C:/Tools/liquidsoap/standby.liq")
    lines = _scan(checker, monkeypatch, caplog, [standby, _main(200.0, 3.0 * H)])
    assert len(lines) == 1 and "PID 16424" in lines[0]


def test_no_process_logs_nothing(checker, monkeypatch, caplog):
    assert _scan(checker, monkeypatch, caplog, None) == []
    assert _scan(checker, monkeypatch, caplog, []) == []
