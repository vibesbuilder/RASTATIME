"""
T13.3 — StartupCheckResult and check_devices_at_startup unit tests.

Exercises the pure domain logic in :mod:`audio.soundcard._startup`
without any Django, database, or real audio hardware.

Test inventory
--------------
StartupCheckResult (6):
  1.  has_any_missing is False when all fields indicate no missing device.
  2.  has_any_missing is True when missing_output_id is set.
  3.  has_any_missing is True when missing_preview_id is set.
  4.  has_any_missing is True when missing_line_in_ids is non-empty.
  5.  all_missing_ids returns frozenset with all missing stable IDs.
  6.  all_missing_ids is an empty frozenset when no devices are missing.

check_devices_at_startup() — no missing devices (3):
  7.  Returns a result with has_any_missing=False when all devices present.
  8.  No WARNING is emitted when all configured devices are present.
  9.  INFO is logged when all devices are present and at least one is configured.

check_devices_at_startup() — missing main output (3):
 10.  missing_output_id is the configured stable_id when device absent.
 11.  missing_output_id is None when main_output_id is not configured.
 12.  WARNING is logged for the missing main output.

check_devices_at_startup() — missing preview output (3):
 13.  missing_preview_id is the configured stable_id when device absent.
 14.  missing_preview_id is None when preview_output_id is not configured.
 15.  WARNING is logged for the missing preview output.

check_devices_at_startup() — missing line-ins (4):
 16.  missing_line_in_ids contains only absent line-in IDs.
 17.  missing_line_in_ids is empty when all line-ins are present.
 18.  WARNING is logged for each missing line-in.
 19.  A present and an absent line-in: only the absent ID appears.

check_devices_at_startup() — all three missing at once (1):
 20.  All three fields populated correctly when output, preview, and
      one line-in are all absent.

(20 tests total)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pytest

from audio.soundcard._startup import StartupCheckResult, check_devices_at_startup
from audio.soundcard.interface import AudioDevice, AudioDeviceKind, AudioDeviceManager
from audio.soundcard.settings_model import SoundcardSettings


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

def _output(stable_id: str, name: str = "Output") -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id, name=name,
        kind=AudioDeviceKind.OUTPUT,
        channels=2, driver="WASAPI",
    )


def _input(stable_id: str, name: str = "Input") -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id, name=name,
        kind=AudioDeviceKind.INPUT,
        channels=2, driver="WASAPI",
    )


class _FakeManager(AudioDeviceManager):
    """Minimal AudioDeviceManager for testing the startup checker."""

    def __init__(self, outputs=(), inputs=()):
        self._outputs = list(outputs)
        self._inputs  = list(inputs)

    def list_outputs(self): return list(self._outputs)
    def list_inputs(self):  return list(self._inputs)

    # Unused abstract methods — required by ABC
    def get_default_output(self): return None
    def get_default_input(self):  return None
    def resolve_stable_id(self, raw_id, kind): raise NotImplementedError
    def lookup_by_stable_id(self, stable_id, kind): return None
    def open_output(self, stable_id): pass
    def open_input(self, stable_id):  pass
    def close_output(self, stable_id): pass
    def close_input(self, stable_id):  pass


def _settings(**kwargs) -> SoundcardSettings:
    return SoundcardSettings(**kwargs)


# ---------------------------------------------------------------------------
# 1–6  StartupCheckResult
# ---------------------------------------------------------------------------

def test_has_any_missing_false_when_nothing_missing():
    r = StartupCheckResult(
        missing_output_id=None,
        missing_preview_id=None,
        missing_line_in_ids=(),
    )
    assert r.has_any_missing is False


def test_has_any_missing_true_when_output_missing():
    r = StartupCheckResult(
        missing_output_id="out-1",
        missing_preview_id=None,
        missing_line_in_ids=(),
    )
    assert r.has_any_missing is True


def test_has_any_missing_true_when_preview_missing():
    r = StartupCheckResult(
        missing_output_id=None,
        missing_preview_id="prev-1",
        missing_line_in_ids=(),
    )
    assert r.has_any_missing is True


def test_has_any_missing_true_when_line_in_missing():
    r = StartupCheckResult(
        missing_output_id=None,
        missing_preview_id=None,
        missing_line_in_ids=("in-1",),
    )
    assert r.has_any_missing is True


def test_all_missing_ids_returns_all_ids():
    r = StartupCheckResult(
        missing_output_id="out-1",
        missing_preview_id="prev-1",
        missing_line_in_ids=("in-1", "in-2"),
    )
    assert r.all_missing_ids == frozenset({"out-1", "prev-1", "in-1", "in-2"})


def test_all_missing_ids_empty_when_nothing_missing():
    r = StartupCheckResult(
        missing_output_id=None,
        missing_preview_id=None,
        missing_line_in_ids=(),
    )
    assert r.all_missing_ids == frozenset()


# ---------------------------------------------------------------------------
# 7–9  All devices present
# ---------------------------------------------------------------------------

def test_no_missing_when_all_configured_devices_present():
    mgr = _FakeManager(
        outputs=[_output("out-1")],
        inputs=[_input("in-1")],
    )
    settings = _settings(
        main_output_id="out-1",
        preview_output_id=None,
        line_in_device_ids=("in-1",),
    )
    result = check_devices_at_startup(settings, mgr)
    assert result.has_any_missing is False


def test_no_warning_when_all_devices_present(caplog):
    mgr = _FakeManager(outputs=[_output("out-1")])
    settings = _settings(main_output_id="out-1")
    with caplog.at_level(logging.WARNING, logger="audio.soundcard._startup"):
        check_devices_at_startup(settings, mgr)
    assert not any(r.levelno == logging.WARNING for r in caplog.records)


def test_info_logged_when_all_devices_present(caplog):
    mgr = _FakeManager(outputs=[_output("out-1")])
    settings = _settings(main_output_id="out-1")
    with caplog.at_level(logging.INFO, logger="audio.soundcard._startup"):
        check_devices_at_startup(settings, mgr)
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("available" in m.lower() for m in info_msgs)


# ---------------------------------------------------------------------------
# 10–12  Missing main output
# ---------------------------------------------------------------------------

def test_missing_output_id_set_when_device_absent():
    mgr = _FakeManager(outputs=[])          # no outputs available
    settings = _settings(main_output_id="out-gone")
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_output_id == "out-gone"


def test_missing_output_id_none_when_not_configured():
    mgr = _FakeManager(outputs=[])
    settings = _settings(main_output_id=None)
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_output_id is None


def test_warning_logged_for_missing_main_output(caplog):
    mgr = _FakeManager(outputs=[])
    settings = _settings(main_output_id="out-gone")
    with caplog.at_level(logging.WARNING, logger="audio.soundcard._startup"):
        check_devices_at_startup(settings, mgr)
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("out-gone" in w for w in warnings)


# ---------------------------------------------------------------------------
# 13–15  Missing preview output
# ---------------------------------------------------------------------------

def test_missing_preview_id_set_when_device_absent():
    mgr = _FakeManager(outputs=[])
    settings = _settings(preview_output_id="prev-gone")
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_preview_id == "prev-gone"


def test_missing_preview_id_none_when_not_configured():
    mgr = _FakeManager(outputs=[])
    settings = _settings(preview_output_id=None)
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_preview_id is None


def test_warning_logged_for_missing_preview_output(caplog):
    mgr = _FakeManager(outputs=[])
    settings = _settings(preview_output_id="prev-gone")
    with caplog.at_level(logging.WARNING, logger="audio.soundcard._startup"):
        check_devices_at_startup(settings, mgr)
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("prev-gone" in w for w in warnings)


# ---------------------------------------------------------------------------
# 16–19  Missing line-ins
# ---------------------------------------------------------------------------

def test_missing_line_in_ids_contains_absent_ids():
    mgr = _FakeManager(inputs=[])          # no inputs available
    settings = _settings(line_in_device_ids=("in-1", "in-2"))
    result = check_devices_at_startup(settings, mgr)
    assert set(result.missing_line_in_ids) == {"in-1", "in-2"}


def test_missing_line_in_ids_empty_when_all_present():
    mgr = _FakeManager(inputs=[_input("in-1"), _input("in-2")])
    settings = _settings(line_in_device_ids=("in-1", "in-2"))
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_line_in_ids == ()


def test_warning_logged_for_each_missing_line_in(caplog):
    mgr = _FakeManager(inputs=[])
    settings = _settings(line_in_device_ids=("in-1", "in-2"))
    with caplog.at_level(logging.WARNING, logger="audio.soundcard._startup"):
        check_devices_at_startup(settings, mgr)
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("in-1" in w for w in warnings)
    assert any("in-2" in w for w in warnings)


def test_only_absent_line_in_reported():
    mgr = _FakeManager(inputs=[_input("in-present")])
    settings = _settings(line_in_device_ids=("in-present", "in-gone"))
    result = check_devices_at_startup(settings, mgr)
    assert "in-present" not in result.missing_line_in_ids
    assert "in-gone" in result.missing_line_in_ids


# ---------------------------------------------------------------------------
# 20  All three missing simultaneously
# ---------------------------------------------------------------------------

def test_all_three_missing_simultaneously():
    mgr = _FakeManager(outputs=[], inputs=[])
    settings = _settings(
        main_output_id="out-gone",
        preview_output_id="prev-gone",
        line_in_device_ids=("in-gone",),
    )
    result = check_devices_at_startup(settings, mgr)
    assert result.missing_output_id  == "out-gone"
    assert result.missing_preview_id == "prev-gone"
    assert result.missing_line_in_ids == ("in-gone",)
    assert result.all_missing_ids    == frozenset({"out-gone", "prev-gone", "in-gone"})
