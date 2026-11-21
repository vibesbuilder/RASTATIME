"""
RASTATIME 2026-05-14 — FFmpeg-based playability check (ADR-002 follow-up).

Replaces the upstream Liquidsoap-based dummy-decode check that requires
Liquidsoap on PATH.  Since RASTATIME deliberately ships without
Liquidsoap (ADR-002), the original check was a silent no-op on this
platform — broken or partially-corrupted audio files therefore only
surfaced their issues at actual playout time, mid-show.

The check decodes the audio of the full file to the null sink via:

    ffmpeg -v error -progress pipe:1 -i <file> -vn -f null -

and inspects the result.  Exit-code semantics observed empirically:

  * exit 0 + empty stderr   → file decoded cleanly
  * exit 0 + stderr lines   → SOFT WARN: file decoded BUT had framing /
    decoder warnings (typical trailing-frame "Header missing" pattern
    from poorly-encoded MP3s; file plays through but logs the warning at
    playout time).  Import is allowed, the warning is surfaced at
    WARNING level so an operator can find it later.
  * exit != 0               → HARD REJECT: file could not be decoded
    at all (missing, codec mismatch, totally corrupted).  Raises
    UnplayableFileError; the upstream pipeline (pipeline.py) catches it
    and skips the file with the operator-visible
    ``"The file could not be played: ..."`` reason.

RASTATIME 2026-11-21 - decoded length against declared length.  The exit
code alone cannot tell a harmless trailing frame from a file that stops
decoding long before its end: a truncated MP3 (header 293.4 s, decodable
87.9 s) and a damaged M4A (218.5 s, decodable 165.7 s) both passed as a
soft warning, went on air and left 198 s and 41 s of dead air, because
the playout trusts the declared length (cue-out) and the next track only
comes at its row.  The same decode run now reports how far it got
(``-progress``, ``out_time_us``); when the audio ends more than
``TRUNCATION_TOLERANCE_S`` AND more than ``TRUNCATION_TOLERANCE_RATIO`` of
the declared length (``metadata["length_seconds"]``, from
analyze_duration) early, the import is refused with
:class:`TruncatedFileError` (operator decision 2026-11-21: refuse, do not
import a shortened file).  A sample of 400 library files had none more
than 0.5 s short; files with an estimated length (VBR without a header)
only ran longer than declared.  Without a declared length or without
progress output nothing is compared (fail-open, logged).
"""

import logging
import subprocess
from typing import Any, Optional

from ._ffmpeg import FFMPEG, low_priority_creationflags

logger = logging.getLogger(__name__)


class UnplayableFileError(Exception):
    pass


class TruncatedFileError(UnplayableFileError):
    """RASTATIME 2026-11-21 - the audio ends well before the declared length."""


#: Minimum decode-verify timeout.  Even a 1 h podcast typically
#: decode-verifies in well under 30 s; the ceiling is purely a safety net
#: so a stuck FFmpeg subprocess doesn't wedge the entire import pipeline.
_DECODE_TIMEOUT_S = 120

#: RASTATIME 2026-11-21 - longer files get more time (half their length;
#: decoding runs far faster than real time).  Before, a fixed 120 s let a
#: long recording through unchecked when the decode ran out of time.
_DECODE_TIMEOUT_FACTOR = 0.5

#: RASTATIME 2026-11-21 - how much shorter than declared the audio may
#: decode before the import is refused; BOTH limits must be exceeded
#: (operator decision 2026-11-21: more than 2 s and more than 1 %).
TRUNCATION_TOLERANCE_S = 2.0
TRUNCATION_TOLERANCE_RATIO = 0.01


def declared_length(metadata: dict[str, Any]) -> Optional[float]:
    """The length analyze_duration found (container / header), or None."""
    try:
        value = float(metadata.get("length_seconds"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def decoded_seconds(progress: str) -> Optional[float]:
    """
    How far the decode got, from ffmpeg's ``-progress`` output.

    ``out_time_us`` (and the misnamed ``out_time_ms``) are microseconds;
    ``N/A`` lines are skipped.  None when no value was reported.
    """
    best: Optional[int] = None
    for line in progress.splitlines():
        key, _, value = line.partition("=")
        if key.strip() not in ("out_time_us", "out_time_ms"):
            continue
        try:
            micro = int(value.strip())
        except ValueError:
            continue
        if micro >= 0 and (best is None or micro > best):
            best = micro
    return None if best is None else best / 1_000_000


def is_truncated(declared: float, decoded: float) -> bool:
    """True when more than both tolerances of the declared length are missing."""
    missing = declared - decoded
    return missing > max(TRUNCATION_TOLERANCE_S, TRUNCATION_TOLERANCE_RATIO * declared)


def analyze_playability(filename: str, metadata: dict[str, Any]):
    """
    Decode-verify *filename* with FFmpeg.

    Soft-warns (log only, allow import) for decoder warnings produced
    during a successful decode.  Hard-rejects (raises
    :class:`UnplayableFileError`, import aborts) when FFmpeg cannot
    decode the file at all, and (:class:`TruncatedFileError`) when the
    audio ends well before the declared length.

    Returns *metadata* unchanged (the playability result is observable
    via the log and the exception path; no metadata field is mutated).
    """
    declared = declared_length(metadata)
    timeout = _DECODE_TIMEOUT_S
    if declared is not None:
        timeout = max(_DECODE_TIMEOUT_S, _DECODE_TIMEOUT_FACTOR * declared)

    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-v",
        "error",  # only emit errors on stderr
        "-progress",
        "pipe:1",  # key=value progress on stdout (out_time_us = decoded length)
        "-i",
        str(filename),
        "-vn",  # the audio only - an embedded cover is not played either
        "-f",
        "null",
        "-",  # decode-to-null sink
    ]

    try:
        completed = subprocess.run(
            cmd,
            check=False,  # we look at returncode ourselves
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=low_priority_creationflags(),
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
        stderr = exc.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        logger.warning(
            "analyze_playability: ffmpeg decode-verify timed out after "
            "%.0fs for %r — soft-warn and continue.  Tail: %r",
            timeout,
            filename,
            stderr[-200:],
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

    decoded = decoded_seconds(completed.stdout or "")
    if declared is not None and decoded is not None and is_truncated(declared, decoded):
        logger.warning(
            "analyze_playability: %r decodes only %.2f of its declared %.2f s - "
            "damaged or cut short, import refused.  stderr:\n%s",
            filename,
            decoded,
            declared,
            stderr_tail[-500:],
        )
        raise TruncatedFileError(
            f"it decodes only {decoded:.1f} of its {declared:.1f} s (damaged or cut short)"
        )
    if declared is not None and decoded is None:
        logger.warning(
            "analyze_playability: no decode progress for %r - decoded length not compared.",
            filename,
        )

    if stderr_tail:
        # Soft-warn — file decoded to its length but with decoder
        # warnings.  Typical case: trailing-frame "Header missing" from
        # MP3s with a bad ID3 tail or a truncated last frame.  The file
        # plays through fine; the warning shows up in the playout log at
        # actual play time and produces a brief glitch on the very last
        # frame.  We allow the import and log so an operator can find
        # the file later (grep service log for the path).
        logger.warning(
            "analyze_playability: %r decoded successfully but ffmpeg "
            "produced decoder warnings (typically a trailing-frame "
            "issue or bad ID3 tail).  Import allowed.  Tail:\n%s",
            filename,
            stderr_tail[-500:],
        )

    return metadata
