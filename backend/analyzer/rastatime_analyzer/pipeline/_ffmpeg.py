import json
import os
import re
import subprocess
from math import inf
from os import getenv
from pathlib import Path
from typing import Any, Optional

from ._utils import run_

FFPROBE = getenv("FFPROBE_PATH", "ffprobe")
FFMPEG = getenv("FFMPEG_PATH", "ffmpeg")

# RASTATIME 2026-10-14 - Liquidsoap and Stereo Tool run on the same machine:
# the import-time ffprobe / ffmpeg runs (tag reading, format conversion) get
# the Windows BELOW_NORMAL priority class so a long transcode never takes CPU
# time from the playout.
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def low_priority_creationflags() -> int:
    """``creationflags`` for subprocess.run: below normal priority on Windows."""
    return BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0


def ffprobe_json(filepath, timeout: float = 60.0) -> dict[str, Any]:
    """
    RASTATIME 2026-10-14 - ``ffprobe -show_format -show_streams`` as a dict.

    The output is decoded as UTF-8 explicitly (tag text is UTF-8 JSON; the
    console code page would garble it).  Raises OSError (binary missing),
    subprocess.TimeoutExpired, subprocess.CalledProcessError (unreadable
    file) or ValueError (no JSON).
    """
    cmd = [
        FFPROBE,
        *("-v", "error"),
        *("-print_format", "json"),
        "-show_format",
        "-show_streams",
        str(filepath),
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
        creationflags=low_priority_creationflags(),
    )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            cmd,
            completed.stdout,
            completed.stderr,
        )
    data = json.loads(completed.stdout.decode("utf-8", errors="replace") or "{}")
    if not isinstance(data, dict):
        raise ValueError("ffprobe returned no JSON object")
    return data


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
    # errors=: ffmpeg echoes the file's tags; a byte that is not valid in the
    # console code page killed the reader thread and the result was lost
    # (library file 648, 2026-09-29)
    cmd = _ffmpeg("-i", filepath, "-vn", "-filter", "replaygain", errors="backslashreplace")

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


def _loudness_text_normalised(filepath: Path, timeout: float = 600.0) -> str:
    """
    RASTATIME 2026-10-24 - ffmpeg's ebur128 summary for ``filepath`` measured
    from a decoded stream with constant parameters (the file's own sample
    rate and channel count, 32-bit PCM), so that decoder hiccups cannot
    split the measurement.  Returns the measuring process' stderr ("" when
    anything fails - the caller then reports "not measurable").
    """
    try:
        probe = ffprobe_json(filepath)
        audio = next(s for s in probe.get("streams", []) if s.get("codec_type") == "audio")
        rate = str(int(audio.get("sample_rate") or 48000))
        channels = str(int(audio.get("channels") or 2))
    except Exception:  # pylint: disable=broad-exception-caught
        return ""
    decode_cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-i",
        str(filepath),
        "-vn",
        "-f",
        "s32le",
        "-ar",
        rate,
        "-ac",
        channels,
        "-",
    ]
    measure_cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-f",
        "s32le",
        "-ar",
        rate,
        "-ac",
        channels,
        "-i",
        "pipe:0",
        "-filter",
        "ebur128=peak=true",
        "-f",
        "null",
        _NULL_DEVICE,
    ]
    try:
        with subprocess.Popen(
            decode_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=low_priority_creationflags(),
        ) as decoder:
            measured = subprocess.run(
                measure_cmd,
                stdin=decoder.stdout,
                capture_output=True,
                check=False,
                timeout=timeout,
                creationflags=low_priority_creationflags(),
            )
            decoder.stdout.close()
            decoder.wait(timeout=timeout)
    except Exception:  # pylint: disable=broad-exception-caught
        return ""
    if measured.returncode != 0:
        return ""
    return (measured.stderr or b"").decode("utf-8", errors="backslashreplace")


def compute_loudness(filepath: Path) -> Optional[dict]:
    """
    EBU R128 measurement of a file: integrated loudness (LUFS), true peak
    (dBTP) and loudness range (LU) as ``{"loudness_lufs", "true_peak_dbtp",
    "loudness_range_lu"}``.  ``None`` when the file is silent or the summary
    could not be read.
    """
    cmd = _ffmpeg("-i", filepath, "-vn", "-filter", "ebur128=peak=true", errors="backslashreplace")
    text = cmd.stderr or ""
    # RASTATIME 2026-10-24 - an MP3 with damaged frames ("Header missing")
    # makes ffmpeg re-initialise its filter graph at every decoder hiccup,
    # and ebur128 then prints one Summary per segment: the first with the
    # real numbers, the rest near-silent stubs with a garbage peak (four
    # Caribou files: 8 summaries, the last one -70 LUFS / +26 dBTP, which
    # the previous "last summary" rule turned into "not measurable").
    # "-reinit_filter 0" is no cure (ffmpeg then aborts the run), so such a
    # file is measured a second time from a stream normalised to its own
    # sample rate and channel count: one graph, one summary, whole file.
    if text.count("Summary:") > 1:
        text = _loudness_text_normalised(filepath)
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


# RASTATIME 2026-11-01 - newer ffmpeg builds log the filter instance as
# "[Parsed_silencedetect_1 @ 0x...]" (the index follows the position in the
# filter chain; the highpass sits in front).  The upstream pattern matched
# "[silencedetect @ ...]" only, so every import since the ffmpeg update got
# cuein 0 and cueout = length without an error.  Both spellings are accepted.
_SILENCE_DETECT_RE = re.compile(
    r"\[(?:Parsed_)?silencedetect[^\]]*\] silence_(start|end): (-?\d+(?:\.\d+)?)"
    r"(?: \| silence_duration: (\d+(?:\.\d+)?))?"
)


def compute_silences(filepath: Path) -> list[tuple[float, float]]:
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

    return list(zip(starts, ends, strict=False))


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
