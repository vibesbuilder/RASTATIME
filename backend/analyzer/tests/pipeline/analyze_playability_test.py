from pathlib import Path
from unittest.mock import patch

import pytest

from rastatime_analyzer.pipeline.analyze_playability import (
    UnplayableFileError,
    analyze_playability,
)

from ..fixtures import FILE_INVALID_DRM, FILES


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
