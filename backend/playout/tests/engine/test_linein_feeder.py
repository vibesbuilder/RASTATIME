"""
Tests for linein_feeder (RASTATIME 2026-08-31 — BACKLOG "Line-In:
Kanal-Auswahl auf Multi-Input-Devices") and the FfmpegLineinCapture
command builders that consume it.

All hardware-free: extract_frames is a pure function, device lookup
runs against a stub sounddevice module, and the capture builders are
exercised with a monkeypatched ffmpeg path.
"""

import array

import pytest

from rastatime_playout.engine import ffmpeg_linein_capture as flc
from rastatime_playout.engine.linein_feeder import (
    extract_frames,
    find_input_device,
    parse_mapping,
)


def _frames(n_channels: int, n_frames: int) -> bytes:
    """Interleaved s16le test signal: sample = frame*100 + channel."""
    data = array.array(
        "h",
        [f * 100 + ch for f in range(n_frames) for ch in range(n_channels)],
    )
    return data.tobytes()


# ---------------------------------------------------------------------------
# extract_frames
# ---------------------------------------------------------------------------


def test_extract_stereo_pair_from_16ch():
    raw = _frames(16, 3)
    out = array.array("h")
    out.frombytes(extract_frames(raw, 16, (4, 5)))
    # frame f: left = f*100+4, right = f*100+5
    assert list(out) == [4, 5, 104, 105, 204, 205]


def test_extract_reversed_pair_swaps_lanes():
    raw = _frames(4, 2)
    out = array.array("h")
    out.frombytes(extract_frames(raw, 4, (3, 0)))
    assert list(out) == [3, 0, 103, 100]


def test_extract_mono_duplicates_to_both_lanes():
    raw = _frames(8, 2)
    out = array.array("h")
    out.frombytes(extract_frames(raw, 8, (6,)))
    assert list(out) == [6, 6, 106, 106]


def test_extract_drops_ragged_tail():
    raw = _frames(4, 3) + b"\x01\x02\x03"  # partial frame appended
    out = array.array("h")
    out.frombytes(extract_frames(raw, 4, (0, 1)))
    assert len(out) == 6  # 3 complete frames x 2 lanes


def test_extract_rejects_out_of_range_channel():
    with pytest.raises(ValueError):
        extract_frames(_frames(2, 1), 2, (2,))


def test_extract_rejects_bad_mapping_arity():
    with pytest.raises(ValueError):
        extract_frames(_frames(4, 1), 4, (0, 1, 2))
    with pytest.raises(ValueError):
        extract_frames(_frames(4, 1), 4, ())


# ---------------------------------------------------------------------------
# parse_mapping
# ---------------------------------------------------------------------------


def test_parse_mapping_pair_and_mono():
    assert parse_mapping("4,5") == (4, 5)
    assert parse_mapping(" 7 ") == (7,)


@pytest.mark.parametrize("bad", ["", "a,b", "1,2,3", "-1,0"])
def test_parse_mapping_rejects_junk(bad):
    with pytest.raises(ValueError):
        parse_mapping(bad)


# ---------------------------------------------------------------------------
# find_input_device (stub sounddevice)
# ---------------------------------------------------------------------------


class _StubSd:
    """Minimal sounddevice stand-in for find_input_device."""

    def __init__(self, devices):
        self._devices = devices

    def query_hostapis(self):
        return [{"name": "MME"}, {"name": "Windows WASAPI"}]

    def query_devices(self):
        return self._devices


def _dev(name, hostapi, max_in):
    return {"name": name, "hostapi": hostapi, "max_input_channels": max_in}


def test_find_device_exact_match_wins():
    sd = _StubSd(
        [
            _dev("Mikrofon (US-16x08 Audio)", 0, 16),
            _dev("Mikrofon (US-16x08)", 0, 16),
        ]
    )
    found = find_input_device("Mikrofon (US-16x08)", 6, sd)
    assert found == (1, 16, "Mikrofon (US-16x08)")


def test_find_device_substring_match_covers_mme_truncation():
    # MME truncates long friendly names — stored name is a prefix of
    # the PortAudio name (or vice versa).
    sd = _StubSd([_dev("Mikrofon (US-16x08 Audio)", 0, 16)])
    found = find_input_device("Mikrofon (US-16x08)", 6, sd)
    assert found is not None
    assert found[1] == 16


def test_find_device_ignores_other_hostapis_and_small_devices():
    sd = _StubSd(
        [
            _dev("Mikrofon (US-16x08)", 1, 16),  # WASAPI — wrong API
            _dev("Mikrofon (US-16x08)", 0, 2),   # too few channels
        ]
    )
    assert find_input_device("Mikrofon (US-16x08)", 6, sd) is None


# ---------------------------------------------------------------------------
# FfmpegLineinCapture command builders (feeder vs dshow path)
# ---------------------------------------------------------------------------


@pytest.fixture()
def capture(monkeypatch):
    monkeypatch.setattr(flc, "_find_ffmpeg", lambda: "C:/fake/ffmpeg.exe")
    return flc.FfmpegLineinCapture()


def test_build_ffmpeg_cmd_dshow_path(capture):
    cmd = capture._build_ffmpeg_cmd("0fb30b0b-c875-432b-a48f-dbb5208995c9", False)
    joined = " ".join(cmd)
    assert "-f dshow" in joined
    assert "wave_{0FB30B0B-C875-432B-A48F-DBB5208995C9}" in joined
    assert "pipe:0" not in joined


def test_build_ffmpeg_cmd_feeder_path_reads_stdin(capture):
    capture._channel_mapping = (4, 5)
    cmd = capture._build_ffmpeg_cmd("0fb30b0b-c875-432b-a48f-dbb5208995c9", True)
    joined = " ".join(cmd)
    assert "-f s16le" in joined
    assert "-i pipe:0" in joined
    assert "dshow" not in joined
    # encoder/output side unchanged
    assert "-content_type audio/mpeg" in joined


def test_build_feeder_cmd_carries_mapping_and_name(capture):
    capture._channel_mapping = (4, 5)
    capture._device_name = "Mikrofon (US-16x08)"
    cmd = capture._build_feeder_cmd()
    assert "rastatime_playout.engine.linein_feeder" in cmd
    assert cmd[cmd.index("--mapping") + 1] == "4,5"
    assert cmd[cmd.index("--device-name") + 1] == "Mikrofon (US-16x08)"
