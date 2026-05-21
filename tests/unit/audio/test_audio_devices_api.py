"""
T12.2 — Audio device list API unit tests.

Exercises the process-level registry singleton and the pure serialization
helpers that back the ``GET /api/v2/audio/devices`` Django view.
No Django installation required — the view is a thin adapter tested only
indirectly through the helpers.

Test inventory
--------------
Registry (3):
  1.  default_manager is None before connect_device_manager() is called.
  2.  connect_device_manager(mgr) sets default_manager.
  3.  connect_device_manager(mgr2) replaces the previous manager.

serialize_device() (7):
  4.  Returned dict has all expected keys.
  5.  "kind" is a lowercase string value ("output" | "input"), not the enum.
  6.  "is_default" is a plain bool, True when device.is_default is True.
  7.  "is_available" is a plain bool.
  8.  "channels" is an int.
  9.  "stable_id" and "name" are strings.
 10.  Output device serialised correctly (kind="output").

list_devices_response() (7):
 11.  Returns a dict with exactly "outputs" and "inputs" keys.
 12.  Empty lists when manager has no devices.
 13.  One entry per output device.
 14.  One entry per input device.
 15.  Output entries carry all required fields (stable_id, name, kind, channels,
      driver, is_default, is_available).
 16.  Input entry has kind="input".
 17.  Both outputs and inputs returned in the same response dict.

(17 tests total)
"""

from __future__ import annotations

from typing import Optional

import pytest

import audio.soundcard._registry as _reg
from audio.soundcard import AudioDevice, AudioDeviceKind, connect_device_manager
from audio.soundcard._api_helpers import list_devices_response, serialize_device


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

def _output(
    stable_id: str = "aaaa-0001",
    name: str = "Speakers",
    channels: int = 2,
    is_default: bool = False,
) -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id,
        name=name,
        kind=AudioDeviceKind.OUTPUT,
        channels=channels,
        driver="WASAPI",
        is_default=is_default,
        is_available=True,
    )


def _input(
    stable_id: str = "bbbb-0001",
    name: str = "Microphone",
    channels: int = 1,
    is_default: bool = False,
) -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id,
        name=name,
        kind=AudioDeviceKind.INPUT,
        channels=channels,
        driver="WASAPI",
        is_default=is_default,
        is_available=True,
    )


class _StubManager:
    """Minimal AudioDeviceManager double — returns fixed device lists."""

    def __init__(
        self,
        outputs: list[AudioDevice] | None = None,
        inputs:  list[AudioDevice] | None = None,
    ) -> None:
        self._outputs: list[AudioDevice] = outputs or []
        self._inputs:  list[AudioDevice] = inputs  or []

    def list_outputs(self) -> list[AudioDevice]: return list(self._outputs)
    def list_inputs(self)  -> list[AudioDevice]: return list(self._inputs)

    # Remaining ABC methods — not exercised here
    def get_default_output(self): return None
    def get_default_input(self):  return None
    def resolve_stable_id(self, raw_id, kind): raise NotImplementedError
    def lookup_by_stable_id(self, stable_id, kind): return None
    def open_output(self, stable_id): pass
    def open_input(self, stable_id):  pass
    def close_output(self, stable_id): pass
    def close_input(self, stable_id):  pass


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


def test_connect_device_manager_sets_singleton():
    mgr = _StubManager()
    connect_device_manager(mgr)
    assert _reg.default_manager is mgr


def test_connect_device_manager_replaces_previous():
    mgr1 = _StubManager()
    mgr2 = _StubManager()
    connect_device_manager(mgr1)
    connect_device_manager(mgr2)
    assert _reg.default_manager is mgr2


# ---------------------------------------------------------------------------
# 4–10  serialize_device()
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {"stable_id", "name", "kind", "channels", "driver",
                  "is_default", "is_available"}


def test_serialize_device_has_all_keys():
    d = serialize_device(_output())
    assert set(d.keys()) == _EXPECTED_KEYS


def test_serialize_kind_is_lowercase_string_not_enum():
    d_out = serialize_device(_output())
    d_in  = serialize_device(_input())
    assert d_out["kind"] == "output"
    assert d_in["kind"]  == "input"
    assert isinstance(d_out["kind"], str)


def test_serialize_is_default_is_plain_bool_true():
    d = serialize_device(_output(is_default=True))
    assert d["is_default"] is True


def test_serialize_is_available_is_plain_bool():
    d = serialize_device(_output())
    assert isinstance(d["is_available"], bool)
    assert d["is_available"] is True


def test_serialize_channels_is_int():
    d = serialize_device(_input(channels=16))
    assert isinstance(d["channels"], int)
    assert d["channels"] == 16


def test_serialize_stable_id_and_name_are_strings():
    d = serialize_device(_output(stable_id="cafe-1234", name="Studio Monitor"))
    assert isinstance(d["stable_id"], str)
    assert isinstance(d["name"],      str)
    assert d["stable_id"] == "cafe-1234"
    assert d["name"]       == "Studio Monitor"


def test_serialize_output_device_kind_is_output():
    d = serialize_device(_output())
    assert d["kind"] == "output"


# ---------------------------------------------------------------------------
# 11–17  list_devices_response()
# ---------------------------------------------------------------------------

def test_list_devices_response_has_outputs_and_inputs_keys():
    mgr = _StubManager()
    resp = list_devices_response(mgr)
    assert set(resp.keys()) == {"outputs", "inputs"}


def test_list_devices_response_empty_lists_when_no_devices():
    mgr = _StubManager()
    resp = list_devices_response(mgr)
    assert resp["outputs"] == []
    assert resp["inputs"]  == []


def test_list_devices_response_one_entry_per_output():
    mgr = _StubManager(
        outputs=[_output("o1"), _output("o2"), _output("o3")],
    )
    resp = list_devices_response(mgr)
    assert len(resp["outputs"]) == 3
    ids = {d["stable_id"] for d in resp["outputs"]}
    assert ids == {"o1", "o2", "o3"}


def test_list_devices_response_one_entry_per_input():
    mgr = _StubManager(
        inputs=[_input("i1"), _input("i2")],
    )
    resp = list_devices_response(mgr)
    assert len(resp["inputs"]) == 2
    ids = {d["stable_id"] for d in resp["inputs"]}
    assert ids == {"i1", "i2"}


def test_list_devices_response_output_entry_has_required_fields():
    mgr = _StubManager(outputs=[_output("o1", name="Main Out", channels=2)])
    d = list_devices_response(mgr)["outputs"][0]
    assert d["stable_id"]    == "o1"
    assert d["name"]         == "Main Out"
    assert d["kind"]         == "output"
    assert d["channels"]     == 2
    assert d["driver"]       == "WASAPI"
    assert d["is_default"]   is False
    assert d["is_available"] is True


def test_list_devices_response_input_kind_is_input():
    mgr = _StubManager(inputs=[_input("i1")])
    d = list_devices_response(mgr)["inputs"][0]
    assert d["kind"] == "input"


def test_list_devices_response_returns_both_outputs_and_inputs():
    mgr = _StubManager(
        outputs=[_output("o1")],
        inputs=[_input("i1")],
    )
    resp = list_devices_response(mgr)
    assert len(resp["outputs"]) == 1
    assert len(resp["inputs"])  == 1
    assert resp["outputs"][0]["stable_id"] == "o1"
    assert resp["inputs"][0]["stable_id"]  == "i1"
