"""
T-GH-4 - Remove ALSA/PortAudio from the shared config model.

RASTATIME runs on Windows only. The five Linux audio backends (ALSA, AO, OSS,
PortAudio, PulseAudio) are removed from the SystemOutput enum and replaced by
a single WASAPI backend. The existing WASAPISystemOutput model in
audio/soundcard/ is unaffected.

Test inventory (10 tests):
  1.  SystemOutput enum has exactly one member: WASAPI.
  2.  SystemOutput enum has no ALSA member.
  3.  SystemOutput enum has no PORTAUDIO member.
  4.  SystemOutput enum has no PULSEAUDIO member.
  5.  _models.py defines WASAPISystemOutput.
  6.  _models.py does NOT define ALSASystemOutput.
  7.  _models.py does NOT define PortAudioSystemOutput.
  8.  _models.py does NOT define PulseAudioSystemOutput.
  9.  StreamConfig accepts system output with kind='wasapi'.
  10. StreamConfig rejects system output with kind='alsa'.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO   = Path(__file__).resolve().parents[2]
_SHARED = _REPO / "backend" / "shared"

# Ensure shared package is importable
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from rastatime_shared.config._models import (  # noqa: E402
    StreamConfig,
    SystemOutput,
    WASAPISystemOutput,
)


# ---------------------------------------------------------------------------
# 1-4  SystemOutput enum membership
# ---------------------------------------------------------------------------

def test_systemoutput_has_only_wasapi():
    """SystemOutput must contain exactly one member: WASAPI."""
    members = list(SystemOutput)
    assert members == [SystemOutput.WASAPI], (
        f"SystemOutput has unexpected members: {members}"
    )


def test_systemoutput_no_alsa():
    """SystemOutput must not have an ALSA member."""
    assert not hasattr(SystemOutput, "ALSA"), (
        "SystemOutput still has ALSA member"
    )


def test_systemoutput_no_portaudio():
    """SystemOutput must not have a PORTAUDIO member."""
    assert not hasattr(SystemOutput, "PORTAUDIO"), (
        "SystemOutput still has PORTAUDIO member"
    )


def test_systemoutput_no_pulseaudio():
    """SystemOutput must not have a PULSEAUDIO member."""
    assert not hasattr(SystemOutput, "PULSEAUDIO"), (
        "SystemOutput still has PULSEAUDIO member"
    )


# ---------------------------------------------------------------------------
# 5-8  Model class existence
# ---------------------------------------------------------------------------

def test_wasapi_system_output_class_exists():
    """WASAPISystemOutput must be importable from _models."""
    assert WASAPISystemOutput is not None


def test_alsa_system_output_class_gone():
    """ALSASystemOutput must not exist in _models."""
    import rastatime_shared.config._models as m
    assert not hasattr(m, "ALSASystemOutput"), (
        "_models still defines ALSASystemOutput"
    )


def test_portaudio_system_output_class_gone():
    """PortAudioSystemOutput must not exist in _models."""
    import rastatime_shared.config._models as m
    assert not hasattr(m, "PortAudioSystemOutput"), (
        "_models still defines PortAudioSystemOutput"
    )


def test_pulseaudio_system_output_class_gone():
    """PulseAudioSystemOutput must not exist in _models."""
    import rastatime_shared.config._models as m
    assert not hasattr(m, "PulseAudioSystemOutput"), (
        "_models still defines PulseAudioSystemOutput"
    )


# ---------------------------------------------------------------------------
# 9-10  StreamConfig validation
# ---------------------------------------------------------------------------

def test_streamconfig_accepts_wasapi_system_output():
    """StreamConfig must accept a system output with kind='wasapi'."""
    config = StreamConfig(outputs={"system": [{"kind": "wasapi"}]})
    assert len(config.outputs.system) == 1
    assert config.outputs.system[0].kind == SystemOutput.WASAPI


def test_streamconfig_rejects_alsa_system_output():
    """StreamConfig must reject a system output with kind='alsa'."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        StreamConfig(outputs={"system": [{"kind": "alsa"}]})
