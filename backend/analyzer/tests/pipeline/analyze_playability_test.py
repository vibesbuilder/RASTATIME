import os
from pathlib import Path
from unittest.mock import patch

import pytest
from rastatime_analyzer.pipeline.analyze_cuepoint import analyze_duration
from rastatime_analyzer.pipeline.analyze_playability import (
    TruncatedFileError,
    UnplayableFileError,
    analyze_playability,
    declared_length,
    decoded_seconds,
    is_truncated,
)

from ..fixtures import FILE_INVALID_DRM, FILES
from ._synth import requires_ffmpeg, sine

# RASTATIME 2026-05-14 — filter to fixture files that actually exist
# on disk.  Many upstream fixtures (s1-*.mp3, s1-*.m4a, s2-*.wav, …)
# are not checked into the repo; they live in the CI artifact bundle
# and are absent on a local dev checkout.  The previous Liquidsoap-
# based test passed these vacuously because Liquidsoap was missing
# too — that lucky coincidence is gone with the FFmpeg-based check,
# so we explicitly skip missing fixtures via parametrize filter.
_AVAILABLE_FILES = [str(f.path) for f in FILES if Path(f.path).is_file()]


@pytest.mark.parametrize("filepath", _AVAILABLE_FILES)
def test_analyze_playability(filepath):
    analyze_playability(filepath, {})


def test_analyze_playability_missing_ffmpeg():
    """
    RASTATIME 2026-05-14 — when the ffmpeg binary is not on PATH the
    playability check fails open: it logs a warning but does NOT raise,
    so a missing tool can't block every upload.  Same fail-open
    semantic as the old Liquidsoap-on-RASTATIME branch had.
    """
    with patch(
        "rastatime_analyzer.pipeline.analyze_playability.FFMPEG",
        "this-binary-does-not-exist-12345",
    ):
        # Should not raise; falls through with a logged warning.
        analyze_playability(str(FILES[0].path), {})


def test_analyze_playability_invalid_filepath():
    with pytest.raises(UnplayableFileError):
        test_analyze_playability("non-existent-file")


def test_analyze_playability_invalid_wma():
    """
    RASTATIME 2026-05-14 — DRM-protected WMA files cannot be decoded
    by FFmpeg without the proprietary DRM codec, so the new
    FFmpeg-based check rejects them with UnplayableFileError.  This
    replaces the upstream Liquidsoap-specific guard that needed a
    Linux distro-codename check; the codename-based gate is gone since
    distro is irrelevant on the Windows-targeted RASTATIME stack.
    """
    with pytest.raises(UnplayableFileError):
        test_analyze_playability(FILE_INVALID_DRM)


def test_analyze_playability_unknown():
    with pytest.raises(UnplayableFileError):
        test_analyze_playability("https://www.google.com")


# ---------------------------------------------------------------------------
# RASTATIME 2026-11-21 - decoded length against declared length.  A truncated
# MP3 (header 293.4 s, decodable 87.9 s) and a damaged M4A passed the exit-code
# check and left dead air on air; the import now refuses a file whose audio
# ends more than 2 s and more than 1 % before its declared length.
# ---------------------------------------------------------------------------

_LONG = 30.0


def _cut(src: Path, fraction: float, name: str) -> Path:
    dest = src.with_name(name)
    data = src.read_bytes()
    dest.write_bytes(data[: int(len(data) * fraction)])
    return dest


def _check(path: Path) -> None:
    """The pipeline order: analyze_duration (declared length), then the check."""
    analyze_playability(str(path), analyze_duration(str(path), {}))


@pytest.fixture
def mp3(tmp_path: Path) -> Path:
    return sine(tmp_path / "full.mp3", "-c:a", "libmp3lame", "-b:a", "128k", seconds=_LONG)


@requires_ffmpeg
def test_full_mp3_is_accepted(mp3: Path):
    _check(mp3)


@requires_ffmpeg
def test_truncated_mp3_is_refused(mp3: Path):
    cut = _cut(mp3, 0.4, "cut.mp3")
    assert declared_length(analyze_duration(str(cut), {})) == pytest.approx(_LONG, abs=0.1)
    with pytest.raises(TruncatedFileError, match=r"decodes only 1\d\.\d of its 30\.0 s"):
        _check(cut)


@requires_ffmpeg
def test_truncated_file_is_an_unplayable_file(mp3: Path):
    # the pipeline catches UnplayableFileError - the reason reaches the Upload page
    with pytest.raises(UnplayableFileError):
        _check(_cut(mp3, 0.4, "cut.mp3"))


@requires_ffmpeg
def test_truncated_m4a_is_refused(tmp_path: Path):
    m4a = sine(
        tmp_path / "full.m4a",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        seconds=_LONG,
    )
    _check(m4a)
    with pytest.raises(UnplayableFileError):
        _check(_cut(m4a, 0.6, "cut.m4a"))


@requires_ffmpeg
def test_missing_last_frames_within_the_tolerance_are_accepted(mp3: Path):
    _check(_cut(mp3, 0.995, "almost.mp3"))  # ~0.15 s short


@requires_ffmpeg
def test_garbage_after_the_audio_is_accepted(mp3: Path):
    # decoder messages at the end ("Header missing") but the full length
    tail = mp3.with_name("tail.mp3")
    tail.write_bytes(mp3.read_bytes() + os.urandom(3000))
    _check(tail)


@requires_ffmpeg
def test_vbr_mp3_without_a_header_is_accepted(tmp_path: Path):
    # ffprobe estimates the length (shorter than the audio) - longer is fine
    vbr = sine(
        tmp_path / "vbr.mp3",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        "-write_xing",
        "0",
        seconds=_LONG,
    )
    _check(vbr)


@requires_ffmpeg
def test_declared_length_decides(mp3: Path):
    analyze_playability(str(mp3), {"length_seconds": _LONG + 1.5})  # 1.5 s short: allowed
    with pytest.raises(TruncatedFileError):
        analyze_playability(str(mp3), {"length_seconds": _LONG + 5.0})


@requires_ffmpeg
def test_without_a_declared_length_nothing_is_compared(mp3: Path):
    analyze_playability(str(_cut(mp3, 0.4, "cut.mp3")), {})


@pytest.mark.parametrize(
    "declared, decoded, truncated",
    [
        (30.0, 28.1, False),  # 1.9 s missing - below 2 s
        (30.0, 27.9, True),  # 2.1 s missing, more than 1 %
        (600.0, 595.0, False),  # 5 s missing - below 1 % (6 s)
        (600.0, 593.0, True),  # 7 s missing - more than 2 s and 1 %
        (293.4, 87.9, True),  # the file of 2026-11-21
        (218.5, 165.7, True),  # the file of 2026-11-18
        (240.0, 240.6, False),  # decoded longer (estimated VBR length)
    ],
)
def test_is_truncated(declared, decoded, truncated):
    assert is_truncated(declared, decoded) is truncated


def test_decoded_seconds():
    progress = "out_time_us=N/A\nout_time_ms=N/A\nprogress=continue\n"
    progress += "out_time_us=12000000\nout_time_ms=12000000\nout_time=00:00:12.000000\n"
    progress += "out_time_us=87900000\nprogress=end\n"
    assert decoded_seconds(progress) == pytest.approx(87.9)
    assert decoded_seconds("out_time_us=N/A\nprogress=end\n") is None
    assert decoded_seconds("") is None


def test_declared_length():
    assert declared_length({"length_seconds": 12.5}) == 12.5
    assert declared_length({"length_seconds": "12.5"}) == 12.5
    assert declared_length({}) is None
    assert declared_length({"length_seconds": 0}) is None
    assert declared_length({"length_seconds": "n/a"}) is None
