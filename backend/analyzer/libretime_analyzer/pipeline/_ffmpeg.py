import os
import re
from math import inf
from os import getenv
from pathlib import Path
from typing import List, Optional, Tuple

from ._utils import run_

FFPROBE = getenv("FFPROBE_PATH", "ffprobe")
FFMPEG = getenv("FFMPEG_PATH", "ffmpeg")

# OS-portable null device: 'nul' on Windows, '/dev/null' on Unix.
# Hard-coding '/dev/null' caused ffmpeg to silently produce a CompletedProcess
# with stderr=None on Windows, which then crashed compute_silences with
# AttributeError when it iterated over cmd.stderr.splitlines().
_NULL_DEVICE = os.devnull


def _ffmpeg(*args, **kwargs):
    return run_(
        FFMPEG,
        *args,
        "-f",
        "null",
        _NULL_DEVICE,
        "-hide_banner",
        "-nostats",
        **kwargs,
    )


def _ffprobe(*args, **kwargs):
    return run_(FFPROBE, *args, **kwargs)


_PROBE_REPLAYGAIN_RE = re.compile(
    r".*REPLAYGAIN_TRACK_GAIN: ([-+]?[0-9]+\.[0-9]+) dB.*",
)


def probe_replaygain(filepath: Path) -> Optional[float]:
    """
    Probe replaygain will probe the given audio file and return the replaygain if available.
    """
    cmd = _ffprobe("-i", filepath, errors="backslashreplace")

    track_gain_match = _PROBE_REPLAYGAIN_RE.search(cmd.stderr)

    if track_gain_match:
        return float(track_gain_match.group(1))
    return None


_COMPUTE_REPLAYGAIN_RE = re.compile(
    r".* track_gain = ([-+]?[0-9]+\.[0-9]+) dB.*",
)


def compute_replaygain(filepath: Path) -> Optional[float]:
    """
    Compute replaygain will analyse the given audio file and return the replaygain if available.
    """
    cmd = _ffmpeg("-i", filepath, "-vn", "-filter", "replaygain")

    track_gain_match = _COMPUTE_REPLAYGAIN_RE.search(cmd.stderr)

    if track_gain_match:
        return float(track_gain_match.group(1))
    return None


# RASTATIME 2026-09-28 - EBU R128 measurement with ffmpeg's ebur128 filter.
# The summary at the end of stderr looks like:
#
#   Integrated loudness:
#     I:         -14.2 LUFS
#     Threshold: -24.5 LUFS
#   Loudness range:
#     LRA:         5.3 LU
#     ...
#   True peak:
#     Peak:       -0.4 dBFS
#
# A silent file prints "-inf" / "-70.0" - reported as "not measurable".
_LOUDNESS_I_RE = re.compile(r"^\s*I:\s+(-?[0-9]+\.[0-9]+|-inf)\s+LUFS", re.MULTILINE)
_LOUDNESS_LRA_RE = re.compile(r"^\s*LRA:\s+(-?[0-9]+\.[0-9]+|-inf)\s+LU", re.MULTILINE)
_LOUDNESS_PEAK_RE = re.compile(r"^\s*Peak:\s+(-?[0-9]+\.[0-9]+|-inf)\s+dBFS", re.MULTILINE)
LOUDNESS_SILENCE_FLOOR_LUFS = -60.0


def _loudness_value(match: Optional[re.Match]) -> Optional[float]:
    if match is None:
        return None
    raw = match.group(1)
    if raw == "-inf":
        return None
    return float(raw)


def compute_loudness(filepath: Path) -> Optional[dict]:
    """
    EBU R128 measurement of a file: integrated loudness (LUFS), true peak
    (dBTP) and loudness range (LU) as ``{"loudness_lufs", "true_peak_dbtp",
    "loudness_range_lu"}``.  ``None`` when the file is silent or the summary
    could not be read.
    """
    cmd = _ffmpeg("-i", filepath, "-vn", "-filter", "ebur128=peak=true")
    text = cmd.stderr or ""
    summary_pos = text.rfind("Summary:")
    if summary_pos >= 0:
        text = text[summary_pos:]
    integrated = _loudness_value(_LOUDNESS_I_RE.search(text))
    if integrated is None or integrated <= LOUDNESS_SILENCE_FLOOR_LUFS:
        return None
    result = {
        "loudness_lufs": round(integrated, 2),
        "true_peak_dbtp": None,
        "loudness_range_lu": None,
    }
    peak = _loudness_value(_LOUDNESS_PEAK_RE.search(text))
    if peak is not None:
        result["true_peak_dbtp"] = round(peak, 2)
    lra = _loudness_value(_LOUDNESS_LRA_RE.search(text))
    if lra is not None:
        result["loudness_range_lu"] = round(lra, 2)
    return result


_SILENCE_DETECT_RE = re.compile(
    r"\[silencedetect.*\] silence_(start|end): (-?\d+(?:\.\d+)?)(?: \| silence_duration: (\d+(?:\.\d+)?))?"
)


def compute_silences(filepath: Path) -> List[Tuple[float, float]]:
    """
    Compute silence will analyse the given audio file and return a list of silences.
    """
    cmd = _ffmpeg(
        *("-i", filepath),
        "-vn",
        # RASTATIME: reduced silence-duration threshold from 0.9 s to 0.3 s
        # so short leading/trailing silences in jingles and station-IDs
        # are picked up (a 0.5 s pre-roll is common in studio voiceovers
        # and was previously ignored).  noise=-60 dB stays — that level is
        # already quiet enough to handle typical studio room tone.
        *("-filter", "highpass=frequency=80,silencedetect=noise=-60dB:duration=0.3"),
    )

    # Defensive: some ffmpeg builds return CompletedProcess with stderr=None
    # if the run produced no diagnostic output.  Treat that as "no silence
    # info available" rather than crashing the whole pipeline.
    if not cmd.stderr:
        return []

    starts, ends = [], []
    for line in cmd.stderr.splitlines():
        match = _SILENCE_DETECT_RE.search(line)
        if match is None:
            continue

        kind = match.group(1)
        if kind == "start":
            start = float(match.group(2))
            start = max(start, 0.0)
            starts.append(start)
        elif kind == "end":
            end = float(match.group(2))
            ends.append(end)

    # If one end is missing, set the last silence ending to infinity, and
    # clamp it to the track duration before using this value.
    if len(starts) - 1 == len(ends):
        ends.append(inf)

    return list(zip(starts, ends))


def probe_duration(filepath: Path) -> float:
    """
    Probe duration will probe the given audio file and return the duration.
    """
    cmd = _ffprobe(
        *("-i", filepath),
        *("-show_entries", "format=duration"),
        *("-v", "quiet"),
        *("-of", "csv=p=0"),
    )
    return float(cmd.stdout.strip("\n"))
