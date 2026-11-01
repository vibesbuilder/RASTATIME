"""
RASTATIME 2026-05-14 — FFmpeg-based playability check (ADR-002 follow-up).

Replaces the upstream Liquidsoap-based dummy-decode check that requires
Liquidsoap on PATH.  Since RASTATIME deliberately ships without
Liquidsoap (ADR-002), the original check was a silent no-op on this
platform — broken or partially-corrupted audio files therefore only
surfaced their issues at actual playout time, mid-show.

The new check decodes the full file to the null sink via:

    ffmpeg -v error -i <file> -f null -

and inspects the result.  Exit-code semantics observed empirically:

  * exit 0 + empty stderr   → file decoded cleanly
  * exit 0 + stderr lines   → SOFT WARN: file decoded to end BUT had
    framing / decoder warnings (typical trailing-frame "Header missing"
    pattern from poorly-encoded MP3s; file plays through but logs the
    warning at playout time).  Import is allowed, the warning is
    surfaced at WARNING level so an operator can find it later.
  * exit != 0               → HARD REJECT: file could not be decoded
    at all (missing, codec mismatch, totally corrupted).  Raises
    UnplayableFileError; the upstream pipeline (pipeline.py) catches it
    and skips the file with the operator-visible
    ``"File is unplayable"`` error.

The pre-existing UnplayableFileError + the import-pipeline behaviour
around it are preserved — this is a drop-in replacement for the
external tool, not a contract change.
"""

import logging
import subprocess
from typing import Any

from ._ffmpeg import FFMPEG

logger = logging.getLogger(__name__)


class UnplayableFileError(Exception):
    pass


#: Generous decode-verify timeout.  Even a 1 h podcast typically
#: decode-verifies in well under 30 s; the 120 s ceiling here is purely
#: a safety net so a stuck FFmpeg subprocess doesn't wedge the entire
#: import pipeline.
_DECODE_TIMEOUT_S = 120


def analyze_playability(filename: str, metadata: dict[str, Any]):
    """
    Decode-verify *filename* with FFmpeg.

    Soft-warns (log only, allow import) for decoder warnings produced
    during a successful decode.  Hard-rejects (raises
    :class:`UnplayableFileError`, import aborts) when FFmpeg cannot
    decode the file at all.

    Returns *metadata* unchanged (the playability result is observable
    via the log and the exception path; no metadata field is mutated).
    """
    cmd = [
        FFMPEG,
        "-v",
        "error",  # only emit errors on stderr
        "-i",
        str(filename),
        "-f",
        "null",
        "-",  # decode-to-null sink
        "-hide_banner",
        "-nostats",
    ]

    try:
        completed = subprocess.run(
            cmd,
            check=False,  # we look at returncode ourselves
            capture_output=True,
            text=True,
            timeout=_DECODE_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        # FFmpeg binary missing.  This is a setup error, not a per-file
        # error — log loudly and let the file through unverified rather
        # than blocking every upload.  Same fail-open pattern the
        # upstream Liquidsoap branch used.
        logger.warning(
            "analyze_playability: ffmpeg not found (%s) — skipping check. "
            "File %r will be imported without playability verification.",
            exc,
            filename,
        )
        return metadata
    except subprocess.TimeoutExpired as exc:
        # File took too long to decode-verify.  Treat as soft-warn:
        # the file is probably OK but we couldn't confirm in time.
        logger.warning(
            "analyze_playability: ffmpeg decode-verify timed out after "
            "%ds for %r — soft-warn and continue.  Tail: %r",
            _DECODE_TIMEOUT_S,
            filename,
            (exc.stderr or "")[-200:],
        )
        return metadata

    stderr_tail = (completed.stderr or "").strip()

    if completed.returncode != 0:
        # Hard reject — file couldn't decode end-to-end.
        logger.warning(
            "analyze_playability: ffmpeg rejected %r (exit=%d).  stderr:\n%s",
            filename,
            completed.returncode,
            stderr_tail[-1000:],
        )
        raise UnplayableFileError(
            f"ffmpeg decode failed (exit {completed.returncode}): {stderr_tail[:200]!r}"
        )

    if stderr_tail:
        # Soft-warn — file decoded but with decoder warnings.
        # Typical case: trailing-frame "Header missing" from MP3s with
        # a bad ID3 tail or a truncated last frame.  The file plays
        # through fine; the warning shows up in the playout log at
        # actual play time and produces a brief glitch on the very
        # last frame.  We allow the import and log so an operator can
        # find the file later (grep service log for the path).
        logger.warning(
            "analyze_playability: %r decoded successfully but ffmpeg "
            "produced decoder warnings (typically a trailing-frame "
            "issue or bad ID3 tail).  Import allowed.  Tail:\n%s",
            filename,
            stderr_tail[-500:],
        )

    return metadata
