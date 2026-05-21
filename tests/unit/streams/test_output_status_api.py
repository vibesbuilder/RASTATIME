"""
T10.3 — Stream output status API unit tests.

Verifies the process-level registry singleton and the pure serialization
helpers that back the ``/api/v2/streams/outputs`` Django view.  No Django
installation required — the Django view is a thin adapter and is tested only
indirectly through the helpers.

Test inventory
--------------
Registry (3):
 1.  default_manager is None before connect_egress_manager() is called.
 2.  connect_egress_manager(mgr) sets default_manager.
 3.  connect_egress_manager(mgr2) replaces the previous manager.

serialize_output_status() (9):
 4.  Returned dict contains all expected top-level keys.
 5.  "state" is a lowercase string (StreamState.value), not the enum object.
 6.  "protocol" is a lowercase string (StreamProtocol.value), not the enum.
 7.  "connected_since" is None when OutputStatus.connected_since is None.
 8.  "connected_since" is an ISO 8601 UTC string when connected_since is set.
 9.  "error_message" is None when OutputStatus.error_message is None.
10.  "error_message" carries the error string when set.
11.  "port" and "bitrate" are ints.
12.  "enabled" reflects output.enabled value (True/False).

list_output_statuses() (4):
13.  Returns [] when manager has no outputs registered.
14.  Returns one dict per registered output.
15.  Each dict carries name, url, port, mount, and codec fields.
16.  Skips outputs whose get_output_status() raises ValueError (race condition).
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Optional

import pytest

import streams.egress._registry as _reg
from streams._types import StreamProtocol, StreamState
from streams.egress._api_helpers import (
    list_output_statuses,
    serialize_output_status,
)
from streams.egress.interface import OutputStatus, StreamOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {
    "output_id", "name", "protocol", "url", "port", "mount",
    "codec", "bitrate", "enabled", "state", "connected_since", "error_message",
}


def _make_output(
    output_id: str = "o1",
    enabled: bool = True,
) -> StreamOutput:
    return StreamOutput(
        id=output_id,
        name="Test Stream",
        protocol=StreamProtocol.ICECAST,
        url="ice.local",
        port=8000,
        mount="/live",
        username="source",
        password="hackme",
        bitrate=128,
        codec="mp3",
        enabled=enabled,
    )


def _make_status(
    output_id: str = "o1",
    state: StreamState = StreamState.IDLE,
    connected_since: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> OutputStatus:
    return OutputStatus(
        output_id=output_id,
        state=state,
        connected_since=connected_since,
        error_message=error_message,
    )


class _MockManager:
    """Minimal egress manager double for registry/serialization tests."""

    def __init__(self, outputs: Optional[list] = None) -> None:
        self._outputs: list[StreamOutput] = list(outputs or [])

    def list_outputs(self) -> list[StreamOutput]:
        return list(self._outputs)

    def get_output_status(self, output_id: str) -> OutputStatus:
        for o in self._outputs:
            if o.id == output_id:
                return _make_status(output_id=o.id)
        raise ValueError(f"Unknown output: {output_id!r}")


@pytest.fixture(autouse=True)
def reset_registry():
    """Restore default_manager=None after every test."""
    original = _reg.default_manager
    yield
    _reg.default_manager = original


# ---------------------------------------------------------------------------
# 1–3  Registry
# ---------------------------------------------------------------------------

def test_default_manager_is_none_initially():
    _reg.default_manager = None
    assert _reg.default_manager is None


def test_connect_egress_manager_sets_default():
    mgr = _MockManager()
    _reg.connect_egress_manager(mgr)
    assert _reg.default_manager is mgr


def test_connect_egress_manager_replaces_previous():
    mgr1 = _MockManager()
    mgr2 = _MockManager()
    _reg.connect_egress_manager(mgr1)
    _reg.connect_egress_manager(mgr2)
    assert _reg.default_manager is mgr2


# ---------------------------------------------------------------------------
# 4–12  serialize_output_status()
# ---------------------------------------------------------------------------

def test_serialize_output_status_has_all_keys():
    d = serialize_output_status(_make_output(), _make_status())
    assert _EXPECTED_KEYS == set(d.keys())


def test_serialize_state_is_string_value():
    d = serialize_output_status(_make_output(), _make_status(state=StreamState.ACTIVE))
    assert d["state"] == "active"
    assert isinstance(d["state"], str)


def test_serialize_protocol_is_string_value():
    d = serialize_output_status(_make_output(), _make_status())
    assert d["protocol"] == "icecast"
    assert isinstance(d["protocol"], str)


def test_serialize_connected_since_none_when_not_set():
    d = serialize_output_status(_make_output(), _make_status(connected_since=None))
    assert d["connected_since"] is None


def test_serialize_connected_since_is_iso_string_when_set():
    ts = datetime(2026, 4, 26, 14, 30, 0, tzinfo=timezone.utc)
    d = serialize_output_status(
        _make_output(),
        _make_status(state=StreamState.ACTIVE, connected_since=ts),
    )
    assert d["connected_since"] == "2026-04-26T14:30:00+00:00"
    assert isinstance(d["connected_since"], str)


def test_serialize_error_message_none_when_not_set():
    d = serialize_output_status(_make_output(), _make_status(error_message=None))
    assert d["error_message"] is None


def test_serialize_error_message_carries_string_when_set():
    d = serialize_output_status(
        _make_output(),
        _make_status(
            state=StreamState.DISCONNECTED,
            error_message="watchdog: source not found",
        ),
    )
    assert d["error_message"] == "watchdog: source not found"


def test_serialize_port_and_bitrate_are_ints():
    d = serialize_output_status(_make_output(), _make_status())
    assert isinstance(d["port"], int)
    assert isinstance(d["bitrate"], int)
    assert d["port"] == 8000
    assert d["bitrate"] == 128


def test_serialize_enabled_reflects_output_enabled():
    d_on = serialize_output_status(_make_output(enabled=True), _make_status())
    d_off = serialize_output_status(_make_output(enabled=False), _make_status())
    assert d_on["enabled"] is True
    assert d_off["enabled"] is False


# ---------------------------------------------------------------------------
# 13–16  list_output_statuses()
# ---------------------------------------------------------------------------

def test_list_output_statuses_empty_when_no_outputs():
    mgr = _MockManager(outputs=[])
    assert list_output_statuses(mgr) == []


def test_list_output_statuses_one_entry_per_output():
    mgr = _MockManager(outputs=[_make_output("o1"), _make_output("o2")])
    result = list_output_statuses(mgr)
    assert len(result) == 2
    ids = {d["output_id"] for d in result}
    assert ids == {"o1", "o2"}


def test_list_output_statuses_dict_has_config_fields():
    mgr = _MockManager(outputs=[_make_output("o1")])
    result = list_output_statuses(mgr)
    d = result[0]
    assert d["name"] == "Test Stream"
    assert d["url"] == "ice.local"
    assert d["port"] == 8000
    assert d["mount"] == "/live"
    assert d["codec"] == "mp3"


def test_list_output_statuses_skips_on_value_error():
    """
    get_output_status() raising ValueError (race: output removed mid-loop)
    should cause the output to be skipped, not crash the function.
    """

    class _RacyManager:
        def list_outputs(self):
            return [_make_output("present"), _make_output("gone")]

        def get_output_status(self, output_id):
            if output_id == "gone":
                raise ValueError("Unknown output: 'gone'")
            return _make_status(output_id=output_id)

    result = list_output_statuses(_RacyManager())
    assert len(result) == 1
    assert result[0]["output_id"] == "present"
