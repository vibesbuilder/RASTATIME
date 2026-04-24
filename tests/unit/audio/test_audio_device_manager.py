"""
T2.3 validation — AudioDeviceManager interface.

Verifies that:
1. AudioDeviceManager cannot be instantiated directly.
2. An incomplete subclass cannot be instantiated.
3. A complete subclass can be instantiated and returns correct values.
4. AudioDevice fields and defaults are correct.
5. DeviceUnavailableError carries the device_id.
6. All expected symbols are exported from the public interface.
"""

import pytest

from audio.soundcard import (
    AudioDevice,
    AudioDeviceKind,
    AudioDeviceManager,
    DeviceUnavailableError,
)


# ---------------------------------------------------------------------------
# AudioDeviceKind
# ---------------------------------------------------------------------------

def test_audio_device_kind_values():
    assert AudioDeviceKind.OUTPUT.value == "output"
    assert AudioDeviceKind.INPUT.value == "input"


# ---------------------------------------------------------------------------
# AudioDevice
# ---------------------------------------------------------------------------

def test_audio_device_required_fields():
    dev = AudioDevice(
        stable_id="abc123",
        name="Speakers (Realtek)",
        kind=AudioDeviceKind.OUTPUT,
        channels=2,
        driver="WASAPI",
    )
    assert dev.stable_id == "abc123"
    assert dev.channels == 2
    assert dev.driver == "WASAPI"


def test_audio_device_defaults():
    dev = AudioDevice(
        stable_id="x",
        name="Mic",
        kind=AudioDeviceKind.INPUT,
        channels=2,
        driver="WASAPI",
    )
    assert dev.is_default is False
    assert dev.is_available is True
    assert dev.raw_id == ""
    assert dev.metadata == {}


def test_audio_device_unavailable_flag():
    dev = AudioDevice(
        stable_id="gone",
        name="Old Soundcard",
        kind=AudioDeviceKind.OUTPUT,
        channels=2,
        driver="WASAPI",
        is_available=False,
    )
    assert dev.is_available is False


# ---------------------------------------------------------------------------
# DeviceUnavailableError
# ---------------------------------------------------------------------------

def test_device_unavailable_error_carries_id():
    err = DeviceUnavailableError("dev-42")
    assert err.device_id == "dev-42"
    assert "dev-42" in str(err)


def test_device_unavailable_error_is_exception():
    with pytest.raises(DeviceUnavailableError):
        raise DeviceUnavailableError("dev-99")


# ---------------------------------------------------------------------------
# AudioDeviceManager — instantiation guards
# ---------------------------------------------------------------------------

def test_abstract_manager_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AudioDeviceManager()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    class Incomplete(AudioDeviceManager):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# ---------------------------------------------------------------------------
# Minimal concrete stub
# ---------------------------------------------------------------------------

_STUB_OUTPUT = AudioDevice(
    stable_id="out-stub",
    name="Stub Speakers",
    kind=AudioDeviceKind.OUTPUT,
    channels=2,
    driver="WASAPI",
    is_default=True,
)

_STUB_INPUT = AudioDevice(
    stable_id="in-stub",
    name="Stub Microphone",
    kind=AudioDeviceKind.INPUT,
    channels=2,
    driver="WASAPI",
)


class _StubDeviceManager(AudioDeviceManager):
    def list_outputs(self): return [_STUB_OUTPUT]
    def list_inputs(self): return [_STUB_INPUT]
    def get_default_output(self): return _STUB_OUTPUT
    def get_default_input(self): return _STUB_INPUT
    def resolve_stable_id(self, raw_id, kind): return f"stable-{raw_id}"
    def lookup_by_stable_id(self, stable_id, kind):
        if stable_id == "out-stub": return _STUB_OUTPUT
        if stable_id == "in-stub": return _STUB_INPUT
        return None
    def open_output(self, stable_id): pass
    def open_input(self, stable_id): pass
    def close_output(self, stable_id): pass
    def close_input(self, stable_id): pass


def test_stub_manager_can_be_instantiated():
    mgr = _StubDeviceManager()
    assert len(mgr.list_outputs()) == 1
    assert len(mgr.list_inputs()) == 1


def test_stub_default_output():
    mgr = _StubDeviceManager()
    assert mgr.get_default_output().stable_id == "out-stub"


def test_stub_lookup_by_stable_id_found():
    mgr = _StubDeviceManager()
    dev = mgr.lookup_by_stable_id("out-stub", AudioDeviceKind.OUTPUT)
    assert dev is not None
    assert dev.name == "Stub Speakers"


def test_stub_lookup_by_stable_id_not_found_returns_none():
    mgr = _StubDeviceManager()
    dev = mgr.lookup_by_stable_id("nonexistent", AudioDeviceKind.OUTPUT)
    assert dev is None


def test_stub_resolve_stable_id():
    mgr = _StubDeviceManager()
    result = mgr.resolve_stable_id("raw-win-id-001", AudioDeviceKind.OUTPUT)
    assert result == "stable-raw-win-id-001"
