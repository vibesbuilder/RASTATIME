"""
RASTATIME 2026-09-28 - EBU R128 loudness measurement (stage 1).

Runs after the ReplayGain step: ffmpeg's ``ebur128`` filter gives the
integrated loudness (LUFS), the true peak (dBTP) and the loudness range
(LU) of the file.  The playout turns "target − loudness" into the
per-track gain when Settings → Streams → Loudness Normalization is set
to EBU R128; the ReplayGain 1.0 value keeps serving the ReplayGain mode.
"""

from subprocess import CalledProcessError
from typing import Any

from ._ffmpeg import compute_loudness

LOUDNESS_KEYS = ("loudness_lufs", "true_peak_dbtp", "loudness_range_lu")


def analyze_loudness(filepath: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Add the R128 measurement to ``metadata``.  A file that cannot be
    measured (silence, decoder error) keeps the keys absent so an
    earlier value in the database is left untouched.
    """
    try:
        measured = compute_loudness(filepath)
    except (CalledProcessError, OSError):
        return metadata
    if measured is None:
        return metadata
    for key in LOUDNESS_KEYS:
        metadata[key] = measured.get(key)
    return metadata
