"""
RASTATIME 2026-11-13 - PreflightChecker: ``auto_dj_buffer_unusable`` - the
Auto DJ buffer playlist is gone or holds no track that outlasts the maximum
gap (§23.107).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from rastatime_playout.preflight import PreflightChecker

TYPE = PreflightChecker.WARNING_TYPE_AUTO_DJ_BUFFER


def _resp(status: int, payload):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


def _status(**over):
    data = {
        "active": True,
        "playlist_id": 77,
        "playlist_exists": True,
        "max_gap": 60.0,
        "required_seconds": 65.0,
        "tracks": 2,
        "playable": 2,
        "usable": 1,
        "longest_seconds": 240.0,
    }
    data.update(over)
    return data


@pytest.fixture
def checker(monkeypatch):
    c = PreflightChecker(api_client=MagicMock())
    submitted = {}
    monkeypatch.setattr(c, "_submit_warnings", lambda t, run_id, w: submitted.__setitem__(t, w))
    c._submitted = submitted
    return c


def test_usable_buffer_clears_the_type(checker):
    checker._api_client.session.get.return_value = _resp(200, _status())
    checker._scan_auto_dj_buffer()
    assert checker._submitted[TYPE] == []
    assert checker._api_client.session.get.call_args.args[0] == "/api/v2/auto-dj/buffer"


def test_inactive_buffer_clears_the_type(checker):
    checker._api_client.session.get.return_value = _resp(200, {"active": False})
    checker._scan_auto_dj_buffer()
    assert checker._submitted[TYPE] == []


def test_deleted_playlist_warns(checker):
    checker._api_client.session.get.return_value = _resp(
        200, _status(playlist_exists=False, tracks=0, playable=0, usable=0, longest_seconds=None)
    )
    checker._scan_auto_dj_buffer()
    (w,) = checker._submitted[TYPE]
    assert w["severity"] == "warning"
    assert w["detail"]["reason"] == "missing"
    assert "no longer exists" in w["detail"]["message"]


def test_tracks_too_short_warn(checker):
    checker._api_client.session.get.return_value = _resp(
        200, _status(usable=0, longest_seconds=50.0)
    )
    checker._scan_auto_dj_buffer()
    (w,) = checker._submitted[TYPE]
    assert w["detail"]["reason"] == "too_short"
    assert w["detail"]["longest_seconds"] == 50.0
    assert "longer than 65 s" in w["detail"]["message"]


def test_empty_playlist_warns(checker):
    checker._api_client.session.get.return_value = _resp(
        200, _status(tracks=0, playable=0, usable=0, longest_seconds=None)
    )
    checker._scan_auto_dj_buffer()
    (w,) = checker._submitted[TYPE]
    assert w["detail"]["reason"] == "empty"


def test_old_api_submits_nothing(checker):
    checker._api_client.session.get.return_value = _resp(404, {"detail": "Not found."})
    checker._scan_auto_dj_buffer()
    assert TYPE not in checker._submitted


def test_unreachable_api_submits_nothing(checker):
    checker._api_client.session.get.side_effect = OSError("refused")
    checker._scan_auto_dj_buffer()
    assert TYPE not in checker._submitted
