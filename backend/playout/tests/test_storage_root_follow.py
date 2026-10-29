"""
RASTATIME 2026-09-16 - the media library root is a Local Machine setting.
The scheduler follows the API's effective root on every refresh (direct
file access without a restart after a move); the preflight warns when the
root is missing or read-only.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.preflight import PreflightChecker


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _sched(api_client, storage_path="C:/rastatime/media"):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    return ps.PlayoutScheduler(engine=engine, api_client=api_client, storage_path=storage_path)


# ---- scheduler ---------------------------------------------------------------

def test_scheduler_follows_the_effective_root():
    api = MagicMock()
    api.get_storage_location.return_value = _Resp({"root": "D:/stor", "source": "setting"})
    s = _sched(api)
    s._refresh_storage_root()
    assert s._storage_path == "D:/stor"
    api.get_storage_location.return_value = _Resp({"root": "D:/stor"})
    s._refresh_storage_root()
    assert s._storage_path == "D:/stor"


@pytest.mark.parametrize("payload", [None, {}, {"root": ""}, {"root": 5}, "nonsense"])
def test_scheduler_keeps_the_root_on_odd_answers(payload):
    api = MagicMock()
    api.get_storage_location.return_value = _Resp(payload)
    s = _sched(api)
    s._refresh_storage_root()
    assert s._storage_path == "C:/rastatime/media"


def test_scheduler_tolerates_an_old_api_and_errors():
    api = MagicMock(spec=[])                      # no get_storage_location at all
    s = _sched(api)
    s._refresh_storage_root()
    assert s._storage_path == "C:/rastatime/media"
    api = MagicMock()
    api.get_storage_location.side_effect = ConnectionError("down")
    s = _sched(api)
    s._refresh_storage_root()
    assert s._storage_path == "C:/rastatime/media"


# ---- preflight ---------------------------------------------------------------

@pytest.fixture
def checker():
    api = MagicMock()
    c = PreflightChecker(api_client=api)
    submitted = {}
    c._submit_warnings = lambda warning_type, run_id, warnings: submitted.__setitem__(warning_type, warnings)
    c._submitted = submitted
    return c


def test_preflight_warns_when_the_root_is_missing(checker):
    checker._api_client.get_storage_location.return_value = _Resp(
        {"root": "D:/stor", "source": "setting", "exists": False, "writable": False}
    )
    checker._scan_storage_root()
    warnings = checker._submitted[PreflightChecker.WARNING_TYPE_STORAGE_ROOT]
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "error"
    assert "D:/stor is missing" in warnings[0]["detail"]["message"]


def test_preflight_warns_when_the_root_is_read_only(checker):
    checker._api_client.get_storage_location.return_value = _Resp(
        {"root": "D:/stor", "exists": True, "writable": False}
    )
    checker._scan_storage_root()
    assert "is not writable" in checker._submitted[PreflightChecker.WARNING_TYPE_STORAGE_ROOT][0]["detail"]["message"]


def test_preflight_clears_the_type_when_the_root_is_fine(checker):
    checker._api_client.get_storage_location.return_value = _Resp(
        {"root": "C:/rastatime/media", "exists": True, "writable": True}
    )
    checker._scan_storage_root()
    assert checker._submitted[PreflightChecker.WARNING_TYPE_STORAGE_ROOT] == []


def test_preflight_submits_nothing_without_the_endpoint(checker):
    checker._api_client.get_storage_location.side_effect = ConnectionError("down")
    checker._scan_storage_root()
    assert PreflightChecker.WARNING_TYPE_STORAGE_ROOT not in checker._submitted
    checker._api_client.get_storage_location.side_effect = None
    checker._api_client.get_storage_location.return_value = _Resp({"detail": "not found"})
    checker._scan_storage_root()
    assert PreflightChecker.WARNING_TYPE_STORAGE_ROOT not in checker._submitted
