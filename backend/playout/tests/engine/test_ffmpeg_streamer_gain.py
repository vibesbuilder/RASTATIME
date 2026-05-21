"""
RASTATIME 2026-05-16 — Unit tests for the gain-application branch in
``FfmpegStreamer._start_locked``.

The streamer builds an FFmpeg command line from a stream-config dict.
The ``gain_db`` parameter (renamed from ``replay_gain_db`` when
webstream input-gain joined the same plumbing) makes the streamer emit
``-af volume=<dB>dB`` into its command line.  Same FFmpeg filter
mechanism for both file-track ReplayGain and webstream input-gain.

The test mocks ``subprocess.Popen`` so no real ffmpeg subprocess is
launched, and inspects the ``cmd`` list the streamer would have spawned.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.ffmpeg_streamer import FfmpegStreamer


def _make_streamer():
    """Build a minimal FfmpegStreamer instance that won't actually spawn ffmpeg."""
    config = {
        "host":     "localhost",
        "port":     8000,
        "mount":    "rastatime192",
        "user":     "source",
        "pass":     "test",
        "type":     "mp3",
        "bitrate":  192,
        "channels": "stereo",
        "samplerate": 48000,
    }
    return FfmpegStreamer(config)


def _capture_cmd(streamer, **start_kwargs):
    """Drive a single start() against a mocked Popen and return the cmd list."""
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None  # "still running"
    fake_proc.pid = 12345

    with patch(
        "libretime_playout.engine.ffmpeg_streamer.subprocess.Popen",
        return_value=fake_proc,
    ) as popen_mock, patch(
        "libretime_playout.engine.ffmpeg_streamer.time.sleep",
        return_value=None,
    ):
        streamer.start("C:/tmp/example.mp3", **start_kwargs)

    assert popen_mock.call_count == 1, (
        f"expected exactly one Popen call, got {popen_mock.call_count}"
    )
    return popen_mock.call_args[0][0]


def test_no_gain_argument_when_none():
    """Default (no gain_db) ⇒ no ``volume`` filter on the command line."""
    streamer = _make_streamer()
    cmd = _capture_cmd(streamer)
    joined = " ".join(cmd)
    assert "volume=" not in joined, (
        f"Expected no volume filter when gain_db is None, got:\n{joined}"
    )
    assert "-af" not in cmd, "no -af flag should be emitted when no filter is requested"


def test_no_gain_argument_when_essentially_zero():
    """A near-zero gain (|dB| < 0.001) is treated as no-op."""
    streamer = _make_streamer()
    cmd = _capture_cmd(streamer, gain_db=0.0)
    assert "-af" not in cmd
    cmd = _capture_cmd(streamer, gain_db=0.0005)
    assert "-af" not in cmd


def test_positive_gain_emits_volume_filter():
    """+3 dB gain ⇒ command line carries ``-af volume=+3.00dB``."""
    streamer = _make_streamer()
    cmd = _capture_cmd(streamer, gain_db=3.0)
    assert "-af" in cmd
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "volume=+3.00dB", (
        f"unexpected filter argument: {cmd[af_idx + 1]!r}"
    )


def test_negative_gain_emits_volume_filter():
    """A negative dB (e.g. a webstream that needs attenuation) is preserved with sign."""
    streamer = _make_streamer()
    cmd = _capture_cmd(streamer, gain_db=-6.5)
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "volume=-6.50dB"


def test_gain_filter_is_before_encoder_args():
    """
    ``-af`` must come before ``-c:a`` so the volume filter sits between the
    decode and the encode stage in FFmpeg's filter graph.
    """
    streamer = _make_streamer()
    cmd = _capture_cmd(streamer, gain_db=2.0)
    af_idx = cmd.index("-af")
    codec_idx = cmd.index("-c:a")
    assert af_idx < codec_idx, (
        f"-af (index {af_idx}) must precede -c:a (index {codec_idx}) "
        "so the encoder sees the gain-corrected stream"
    )
