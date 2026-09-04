"""
Which capture path ``FfmpegLineinCapture`` takes (RASTATIME 2026-09-03,
"Option B").

This is the decision that actually determines whether audio flows.  Up
to 2026-09-03 plain stereo ``(0, 1)`` let ffmpeg open the device
directly over DirectShow, addressed as
``audio=@device_cm_{...}\\wave_{<endpoint guid>}``.  That GUID is the
Windows *audio endpoint* GUID; DirectShow enumerates its own device
GUIDs and does not know it.  On the Tascam US-16x08 ffmpeg answered
"Could not find audio only device" and the 15:20 test show went out
silent.

So the MME feeder now serves every mapping, and dshow survives only as
the fallback for legacy rows that never stored a friendly device name.

The same decision is made in ``PlayoutScheduler._on_linein_start`` and
``_resume_scheduled_locked`` (covered in test_linein_start_ordering);
all three must stay in lockstep, or a slot silently lands back on the
by-GUID path.
"""

from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.ffmpeg_linein_capture import FfmpegLineinCapture

DEVICE_ID = "0fb30b0b-c875-432b-a48f-dbb5208995c9"


@pytest.fixture(name="capture")
def _capture():
    with patch(
        "libretime_playout.engine.ffmpeg_linein_capture._find_ffmpeg",
        return_value="ffmpeg.exe",
    ):
        cap = FfmpegLineinCapture()
    # Stop before anything is actually spawned; we only care which
    # command set _start_locked assembled.
    cap._launch_processes = MagicMock(name="_launch_processes")
    return cap


def _feeder_cmd_used(capture) -> bool:
    """True when _start_locked handed a feeder command to the launcher."""
    capture._launch_processes.assert_called_once()
    _device_id, feeder_cmd, _cmd = capture._launch_processes.call_args[0]
    return feeder_cmd is not None


def test_plain_stereo_uses_the_mme_feeder():
    """The regression that produced a silent show: (0, 1) must NOT go
    to dshow when a device name is available."""
    with patch(
        "libretime_playout.engine.ffmpeg_linein_capture._find_ffmpeg",
        return_value="ffmpeg.exe",
    ):
        cap = FfmpegLineinCapture()
    cap._launch_processes = MagicMock()
    cap._channel_mapping = (0, 1)
    cap._device_name = "Mikrofon (US-16x08)"

    cap._start_locked(DEVICE_ID)

    assert _feeder_cmd_used(cap)


def test_multichannel_mapping_still_uses_the_feeder(capture):
    capture._channel_mapping = (2, 3)
    capture._device_name = "Mikrofon (US-16x08)"

    capture._start_locked(DEVICE_ID)

    assert _feeder_cmd_used(capture)


@pytest.mark.parametrize("mapping", [(0, 1), (2, 3)])
def test_row_without_device_name_falls_back_to_dshow(capture, mapping):
    """The feeder resolves devices by friendly name, so a legacy row
    that never stored one has nothing to resolve.  dshow is then the
    only thing left to try -- it may well fail on a multichannel
    interface, which is why the code logs an error telling the operator
    to re-save the line-in."""
    capture._channel_mapping = mapping
    capture._device_name = ""

    capture._start_locked(DEVICE_ID)

    assert not _feeder_cmd_used(capture)


def test_empty_device_id_starts_nothing(capture):
    capture._channel_mapping = (0, 1)
    capture._device_name = "Mikrofon (US-16x08)"

    capture._start_locked("")

    capture._launch_processes.assert_not_called()
