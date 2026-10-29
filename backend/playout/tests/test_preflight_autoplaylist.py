"""
RASTATIME 2026-10-28 - PreflightChecker: ``autoplaylist_missing`` - a show
in the look-ahead window with "Add Autoloading Playlist" ticked but no
playlist (deleted from the library) would run silent.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rastatime_playout.preflight import PreflightChecker

TYPE = PreflightChecker.WARNING_TYPE_AUTOPLAYLIST_MISSING


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


def _shows(c, shows: dict):
    c._api_client.get_show.side_effect = lambda pk: _resp(200, shows[pk])


def test_show_without_playlist_but_autoloading_on_is_flagged(checker):
    checker._api_client.session.get.return_value = _resp(200, [
        {"id": 501, "show": 7, "starts_at": "2026-10-29T10:00:00Z"},
        {"id": 502, "show": 8, "starts_at": "2026-10-29T12:00:00Z"},
        {"id": 503, "show": 9, "starts_at": "2026-10-29T14:00:00Z"},
    ])
    _shows(checker, {
        7: {"id": 7, "name": "Indie Lane", "auto_playlist_enabled": True, "auto_playlist": None},
        8: {"id": 8, "name": "Healthy", "auto_playlist_enabled": True, "auto_playlist": 660},
        9: {"id": 9, "name": "Live show", "auto_playlist_enabled": False, "auto_playlist": None},
    })
    checker._scan_autoplaylist_missing()
    warnings = checker._submitted[TYPE]
    assert len(warnings) == 1
    w = warnings[0]
    assert w["severity"] == "error"
    assert w["show_id"] == 7 and w["show_instance_id"] == 501
    assert w["starts_at"] == "2026-10-29T10:00:00Z"
    assert w["detail"]["show_name"] == "Indie Lane"
    assert "no playlist" in w["detail"]["message"]
    # the filter parameters reach the API
    kwargs = checker._api_client.session.get.call_args.kwargs
    assert set(kwargs["params"]) == {"starts_after", "starts_before", "modified"}
    assert kwargs["params"]["modified"] == "false"


def test_healthy_window_clears_the_type(checker):
    checker._api_client.session.get.return_value = _resp(200, [
        {"id": 501, "show": 8, "starts_at": "2026-10-29T10:00:00Z"},
    ])
    _shows(checker, {8: {"id": 8, "name": "Healthy", "auto_playlist_enabled": True, "auto_playlist": 660}})
    checker._scan_autoplaylist_missing()
    assert checker._submitted[TYPE] == []


def test_old_api_without_the_filter_submits_nothing(checker):
    checker._api_client.session.get.return_value = _resp(404, {"detail": "Not found."})
    checker._scan_autoplaylist_missing()
    assert TYPE not in checker._submitted


def test_unreachable_api_submits_nothing(checker):
    checker._api_client.session.get.side_effect = ConnectionError("down")
    checker._scan_autoplaylist_missing()
    assert TYPE not in checker._submitted


def test_scan_runs_it_with_the_other_checks(checker, monkeypatch):
    called = []
    for name in ("_scan_linein_devices", "_scan_liquidsoap_health", "_scan_storage_root", "_scan_stereotool"):
        monkeypatch.setattr(checker, name, lambda n=name: called.append(n))
    monkeypatch.setattr(checker, "_scan_autoplaylist_missing", lambda: called.append("autoplaylist"))
    checker.scan_once()
    assert "autoplaylist" in called
