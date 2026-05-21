"""
T12.1 — WindowsAudioDeviceManager unit tests.

All enumeration is driven by a :class:`_FakeEnumerator` — no real Windows
audio stack, registry, or hardware is required for these tests.

Test inventory
--------------
_normalize_guid (3):
  1.  Braces stripped and lowercased.
  2.  Already-normalised GUID is unchanged (idempotent).
  3.  Mixed-case without braces is lowercased.

list_outputs (5):
  4.  Only active endpoints appear in the list.
  5.  AudioDevice fields match the raw endpoint data.
  6.  kind is AudioDeviceKind.OUTPUT.
  7.  is_default True when enumerator names this GUID as default.
  8.  is_default False when enumerator returns None for default.

list_inputs (3):
  9.  Only active inputs appear.
 10.  kind is AudioDeviceKind.INPUT.
 11.  Channels preserved from raw endpoint.

get_default_output (2):
 12.  Returns the correct device when enumerator provides a default GUID.
 13.  Returns None when enumerator provides no default (get_default_guid → None).

get_default_input (1):
 14.  Returns correct input device when enumerator provides default GUID.

resolve_stable_id (3):
 15.  Found active device → returns normalised stable ID.
 16.  Unknown / inactive device → raises DeviceUnavailableError.
 17.  Raw ID with braces resolved to brace-free stable ID.

lookup_by_stable_id (3):
 18.  Active output device found by stable ID.
 19.  Active input device found by stable ID.
 20.  Non-existent stable ID returns None.

open_output (3):
 21.  Opens output → get_active_output_id returns that stable ID.
 22.  Re-opening with a new ID replaces the previous selection.
 23.  Unknown stable ID raises DeviceUnavailableError.

open_input (3):
 24.  Opens input → get_active_input_ids contains that stable ID.
 25.  Multiple inputs may be open simultaneously.
 26.  Unknown stable ID raises DeviceUnavailableError.

close_output (2):
 27.  Closing the active output clears the selection.
 28.  Closing a non-open output is a silent no-op.

close_input (2):
 29.  Closing an open input removes it from the active set.
 30.  Closing a non-open input is a silent no-op.

WinRegDeviceEnumerator — real hardware (3):
 31.  On Windows, list_raw(OUTPUT) returns at least one endpoint.
 32.  On Windows, list_raw(INPUT) returns at least one endpoint.
 33.  Stable IDs are deterministic: same GUID → same normalised ID.

(33 tests total)
"""

from __future__ import annotations

import sys
from typing import Optional

import pytest

from audio.soundcard import AudioDevice, AudioDeviceKind, DeviceUnavailableError
from audio.soundcard.windows_manager import (
    WindowsAudioDeviceManager,
    WinRegDeviceEnumerator,
    _RawEndpoint,
    _normalize_guid,
)


# ---------------------------------------------------------------------------
# Fake enumerator — no registry, no hardware
# ---------------------------------------------------------------------------

class _FakeEnumerator:
    """
    Deterministic enumerator for unit tests.

    ``outputs`` and ``inputs`` are the raw endpoint lists to return.
    ``default_output_guid`` / ``default_input_guid`` are the GUIDs that
    :meth:`get_default_guid` will return, or ``None``.
    """

    def __init__(
        self,
        outputs: list[_RawEndpoint] | None = None,
        inputs: list[_RawEndpoint] | None = None,
        default_output_guid: Optional[str] = None,
        default_input_guid: Optional[str] = None,
    ) -> None:
        self._outputs: list[_RawEndpoint] = outputs or []
        self._inputs:  list[_RawEndpoint] = inputs  or []
        self._default_out = default_output_guid
        self._default_in  = default_input_guid

    def list_raw(self, kind: AudioDeviceKind) -> list[_RawEndpoint]:
        return self._outputs if kind == AudioDeviceKind.OUTPUT else self._inputs

    def get_default_guid(self, kind: AudioDeviceKind) -> Optional[str]:
        return (
            self._default_out
            if kind == AudioDeviceKind.OUTPUT
            else self._default_in
        )


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_GUID_OUT_A = "{9AB29437-D4EC-473D-9A94-1AD46A86E9FF}"
_GUID_OUT_B = "{D0AC23F7-4BE1-48F3-95D1-0A150E0CE459}"
_GUID_IN_A  = "{0BCC4357-EAFE-45B4-BA84-D810EAB113FB}"
_GUID_IN_B  = "{2AE49B28-C17B-4EE6-95F5-FE018828C02C}"
_GUID_DISABLED = "{6E9D2DD0-22F8-4605-9085-65AD1C05D379}"

_RAW_OUT_A = _RawEndpoint(guid=_GUID_OUT_A, name="DELL U2419HC", channels=2, is_active=True)
_RAW_OUT_B = _RawEndpoint(guid=_GUID_OUT_B, name="Lautsprecher", channels=2, is_active=True)
_RAW_OUT_DEAD = _RawEndpoint(guid=_GUID_DISABLED, name="Old Card", channels=2, is_active=False)
_RAW_IN_A  = _RawEndpoint(guid=_GUID_IN_A,  name="Mikrofon",    channels=16, is_active=True)
_RAW_IN_B  = _RawEndpoint(guid=_GUID_IN_B,  name="Microphone",  channels=1,  is_active=True)


def _mgr(
    outputs=None, inputs=None,
    default_out=None, default_in=None,
) -> WindowsAudioDeviceManager:
    return WindowsAudioDeviceManager(
        enumerator=_FakeEnumerator(
            outputs=outputs or [_RAW_OUT_A, _RAW_OUT_B],
            inputs=inputs   or [_RAW_IN_A,  _RAW_IN_B],
            default_output_guid=default_out,
            default_input_guid=default_in,
        )
    )


# ---------------------------------------------------------------------------
# 1–3  _normalize_guid
# ---------------------------------------------------------------------------

def test_normalize_strips_braces_and_lowercases():
    sid = _normalize_guid("{9AB29437-D4EC-473D-9A94-1AD46A86E9FF}")
    assert sid == "9ab29437-d4ec-473d-9a94-1ad46a86e9ff"
    assert "{" not in sid
    assert "}" not in sid


def test_normalize_idempotent():
    sid = "9ab29437-d4ec-473d-9a94-1ad46a86e9ff"
    assert _normalize_guid(sid) == sid


def test_normalize_mixed_case_no_braces():
    assert _normalize_guid("AABBCCDD-0011-2233-4455-66778899AABB") == \
           "aabbccdd-0011-2233-4455-66778899aabb"


# ---------------------------------------------------------------------------
# 4–8  list_outputs
# ---------------------------------------------------------------------------

def test_list_outputs_excludes_inactive():
    mgr = _mgr(outputs=[_RAW_OUT_A, _RAW_OUT_DEAD])
    ids = [d.stable_id for d in mgr.list_outputs()]
    assert _normalize_guid(_GUID_OUT_A)     in ids
    assert _normalize_guid(_GUID_DISABLED)  not in ids


def test_list_outputs_device_fields():
    mgr = _mgr(outputs=[_RAW_OUT_A])
    dev = mgr.list_outputs()[0]
    assert dev.stable_id == _normalize_guid(_GUID_OUT_A)
    assert dev.name      == "DELL U2419HC"
    assert dev.channels  == 2
    assert dev.driver    == "WASAPI"
    assert dev.raw_id    == _GUID_OUT_A
    assert dev.is_available is True


def test_list_outputs_kind_is_output():
    mgr = _mgr()
    assert all(d.kind == AudioDeviceKind.OUTPUT for d in mgr.list_outputs())


def test_list_outputs_is_default_true_when_enumerator_says_so():
    mgr = _mgr(default_out=_GUID_OUT_A)
    for dev in mgr.list_outputs():
        expected = dev.stable_id == _normalize_guid(_GUID_OUT_A)
        assert dev.is_default is expected


def test_list_outputs_is_default_false_when_no_default():
    mgr = _mgr(default_out=None)
    assert all(not d.is_default for d in mgr.list_outputs())


# ---------------------------------------------------------------------------
# 9–11  list_inputs
# ---------------------------------------------------------------------------

def test_list_inputs_excludes_inactive():
    dead = _RawEndpoint(guid=_GUID_DISABLED, name="Dead Mic", channels=1, is_active=False)
    mgr = _mgr(inputs=[_RAW_IN_A, dead])
    ids = [d.stable_id for d in mgr.list_inputs()]
    assert _normalize_guid(_GUID_IN_A) in ids
    assert _normalize_guid(_GUID_DISABLED) not in ids


def test_list_inputs_kind_is_input():
    mgr = _mgr()
    assert all(d.kind == AudioDeviceKind.INPUT for d in mgr.list_inputs())


def test_list_inputs_channels_preserved():
    mgr = _mgr(inputs=[_RAW_IN_A])   # _RAW_IN_A has channels=16
    dev = mgr.list_inputs()[0]
    assert dev.channels == 16


# ---------------------------------------------------------------------------
# 12–13  get_default_output
# ---------------------------------------------------------------------------

def test_get_default_output_returns_device_when_enumerator_provides_guid():
    mgr = _mgr(default_out=_GUID_OUT_A)
    dev = mgr.get_default_output()
    assert dev is not None
    assert dev.stable_id == _normalize_guid(_GUID_OUT_A)


def test_get_default_output_returns_none_when_no_default():
    mgr = _mgr(default_out=None)
    assert mgr.get_default_output() is None


# ---------------------------------------------------------------------------
# 14  get_default_input
# ---------------------------------------------------------------------------

def test_get_default_input_returns_device():
    mgr = _mgr(default_in=_GUID_IN_B)
    dev = mgr.get_default_input()
    assert dev is not None
    assert dev.stable_id == _normalize_guid(_GUID_IN_B)


# ---------------------------------------------------------------------------
# 15–17  resolve_stable_id
# ---------------------------------------------------------------------------

def test_resolve_stable_id_active_device_returns_normalised():
    mgr = _mgr()
    sid = mgr.resolve_stable_id(_GUID_OUT_A, AudioDeviceKind.OUTPUT)
    assert sid == _normalize_guid(_GUID_OUT_A)


def test_resolve_stable_id_unknown_raises():
    mgr = _mgr()
    ghost = "{AAAABBBB-0000-0000-0000-CCCCDDDDEEEE}"
    with pytest.raises(DeviceUnavailableError) as exc_info:
        mgr.resolve_stable_id(ghost, AudioDeviceKind.OUTPUT)
    assert ghost in str(exc_info.value)


def test_resolve_stable_id_normalises_braces():
    mgr = _mgr()
    # _GUID_OUT_A has braces; resolve should strip them
    sid = mgr.resolve_stable_id(_GUID_OUT_A, AudioDeviceKind.OUTPUT)
    assert "{" not in sid
    assert "}" not in sid


# ---------------------------------------------------------------------------
# 18–20  lookup_by_stable_id
# ---------------------------------------------------------------------------

def test_lookup_output_by_stable_id_found():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_OUT_A)
    dev = mgr.lookup_by_stable_id(sid, AudioDeviceKind.OUTPUT)
    assert dev is not None
    assert dev.stable_id == sid


def test_lookup_input_by_stable_id_found():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_IN_A)
    dev = mgr.lookup_by_stable_id(sid, AudioDeviceKind.INPUT)
    assert dev is not None
    assert dev.name == "Mikrofon"


def test_lookup_by_stable_id_not_found_returns_none():
    mgr = _mgr()
    dev = mgr.lookup_by_stable_id("00000000-0000-0000-0000-000000000000", AudioDeviceKind.OUTPUT)
    assert dev is None


# ---------------------------------------------------------------------------
# 21–23  open_output
# ---------------------------------------------------------------------------

def test_open_output_records_active_id():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_OUT_A)
    mgr.open_output(sid)
    assert mgr.get_active_output_id() == sid


def test_open_output_replaces_previous_selection():
    mgr = _mgr()
    sid_a = _normalize_guid(_GUID_OUT_A)
    sid_b = _normalize_guid(_GUID_OUT_B)
    mgr.open_output(sid_a)
    mgr.open_output(sid_b)
    assert mgr.get_active_output_id() == sid_b


def test_open_output_unknown_raises():
    mgr = _mgr()
    with pytest.raises(DeviceUnavailableError):
        mgr.open_output("00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# 24–26  open_input
# ---------------------------------------------------------------------------

def test_open_input_recorded_in_active_set():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_IN_A)
    mgr.open_input(sid)
    assert sid in mgr.get_active_input_ids()


def test_open_input_multiple_simultaneously():
    mgr = _mgr()
    sid_a = _normalize_guid(_GUID_IN_A)
    sid_b = _normalize_guid(_GUID_IN_B)
    mgr.open_input(sid_a)
    mgr.open_input(sid_b)
    active = mgr.get_active_input_ids()
    assert sid_a in active
    assert sid_b in active


def test_open_input_unknown_raises():
    mgr = _mgr()
    with pytest.raises(DeviceUnavailableError):
        mgr.open_input("00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# 27–28  close_output
# ---------------------------------------------------------------------------

def test_close_output_clears_active():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_OUT_A)
    mgr.open_output(sid)
    mgr.close_output(sid)
    assert mgr.get_active_output_id() is None


def test_close_output_noop_if_not_open():
    mgr = _mgr()
    mgr.close_output(_normalize_guid(_GUID_OUT_A))  # must not raise
    assert mgr.get_active_output_id() is None


# ---------------------------------------------------------------------------
# 29–30  close_input
# ---------------------------------------------------------------------------

def test_close_input_removes_from_active_set():
    mgr = _mgr()
    sid = _normalize_guid(_GUID_IN_A)
    mgr.open_input(sid)
    mgr.close_input(sid)
    assert sid not in mgr.get_active_input_ids()


def test_close_input_noop_if_not_open():
    mgr = _mgr()
    mgr.close_input(_normalize_guid(_GUID_IN_A))  # must not raise
    assert mgr.get_active_input_ids() == set()


# ---------------------------------------------------------------------------
# 31–33  WinRegDeviceEnumerator — real hardware (Windows-only)
# ---------------------------------------------------------------------------

_ON_WINDOWS = sys.platform.startswith("win")

@pytest.mark.skipif(not _ON_WINDOWS, reason="Windows-only: requires real audio registry")
def test_real_enumerator_outputs_non_empty():
    enum = WinRegDeviceEnumerator()
    devices = enum.list_raw(AudioDeviceKind.OUTPUT)
    assert len(devices) > 0, "Expected at least one audio output endpoint in the registry"


@pytest.mark.skipif(not _ON_WINDOWS, reason="Windows-only: requires real audio registry")
def test_real_enumerator_inputs_non_empty():
    enum = WinRegDeviceEnumerator()
    devices = enum.list_raw(AudioDeviceKind.INPUT)
    assert len(devices) > 0, "Expected at least one audio input endpoint in the registry"


@pytest.mark.skipif(not _ON_WINDOWS, reason="Windows-only: stable ID determinism")
def test_stable_id_is_deterministic():
    """Given the same GUID, _normalize_guid always produces the same stable ID."""
    guid = "{9AB29437-D4EC-473D-9A94-1AD46A86E9FF}"
    assert _normalize_guid(guid) == _normalize_guid(guid)
    assert _normalize_guid(guid) == _normalize_guid(guid.lower())
    assert _normalize_guid(guid) == _normalize_guid("{" + guid.strip("{}").lower() + "}")
