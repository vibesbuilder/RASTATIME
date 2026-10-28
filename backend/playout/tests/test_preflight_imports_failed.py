"""
RASTATIME 2026-10-28 - PreflightChecker: ``imports_failed`` - failed uploads
waiting on the Upload page and files left in the analyzer's organize folder.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout.preflight import PreflightChecker

TYPE = PreflightChecker.WARNING_TYPE_IMPORTS_FAILED
HOUR = 3600
DAY = 86400


def _resp(status: int, payload):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


@pytest.fixture
def checker(monkeypatch):
    c = PreflightChecker(api_client=MagicMock())
    submitted = {}
    monkeypatch.setattr(c, "_submit_warnings", lambda t, run_id, w: submitted.__setitem__(t, w))
    c._submitted = submitted
    return c


def test_old_failures_and_leftovers_make_one_warning(checker):
    checker._api_client.session.get.return_value = _resp(200, {
        "failed": [
            {"id": 24975, "name": "Sunshine.mp3", "comment": "ffprobe could not read the file", "age_seconds": 8 * DAY},
            {"id": 25000, "name": "Just now.mp3", "comment": "", "age_seconds": 120},
        ],
        "leftovers": [
            {"file": "24975-Sunshine.mp3", "age_seconds": 8 * DAY, "row": "failed"},
            {"file": "25001-Pending.mp3", "age_seconds": 2 * DAY, "row": "pending"},
            {"file": "orphan.mp3", "age_seconds": 3 * HOUR, "row": "missing"},
        ],
        "organize_dir": "D:/stor/organize",
    })
    checker._scan_imports_failed()
    warnings = checker._submitted[TYPE]
    assert len(warnings) == 1
    w = warnings[0]
    assert w["severity"] == "warning"
    assert w["detail"]["failed_count"] == 1       # the 2-minute-old failure is still being looked at
    assert w["detail"]["leftover_count"] == 1     # pending and young files do not count
    assert w["detail"]["names"] == ["Sunshine.mp3", "24975-Sunshine.mp3"]
    assert "D:/stor/organize" in w["detail"]["message"]
    assert checker._api_client.session.get.call_args.args[0] == "/api/v2/storage/imports/failed"


def test_clean_state_clears_the_type(checker):
    checker._api_client.session.get.return_value = _resp(200, {"failed": [], "leftovers": [], "organize_dir": "x"})
    checker._scan_imports_failed()
    assert checker._submitted[TYPE] == []


def test_old_api_submits_nothing(checker):
    checker._api_client.session.get.return_value = _resp(404, {"detail": "Not found."})
    checker._scan_imports_failed()
    assert TYPE not in checker._submitted


def test_unreachable_api_submits_nothing(checker):
    checker._api_client.session.get.side_effect = ConnectionError("down")
    checker._scan_imports_failed()
    assert TYPE not in checker._submitted


def test_scan_once_runs_it(checker, monkeypatch):
    called = []
    for name in ("_scan_linein_devices", "_scan_liquidsoap_health", "_scan_storage_root", "_scan_stereotool", "_scan_autoplaylist_missing"):
        monkeypatch.setattr(checker, name, lambda n=name: called.append(n))
    monkeypatch.setattr(checker, "_scan_imports_failed", lambda: called.append("imports"))
    checker.scan_once()
    assert "imports" in called
