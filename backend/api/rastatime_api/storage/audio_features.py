"""
RASTATIME 2026-11-14 - energy and brightness of library tracks, stage 1
(operator go 2026-11-14, ARCHITECTURE 23.115): measured with ffmpeg only,
no new dependency.

``manage.py analyze_audio_features`` - fired every ten minutes by the
Windows task RASTATIME-AudioFeatures (``scripts/audio-features.ps1``,
``infra/scripts/register-audio-features.ps1``) - measures every track that
has an integrated loudness (R128, measured on import) but no
``cc_files.audio_features`` yet, newest first.  Import and playout are not
involved: a new upload gets its values from the next run.

The measurement: 30 s from the middle of the cue range, brought to the
on-air level first (gain = -23 LUFS minus the track's integrated loudness -
without that, "energy" would mostly measure how loud a track was mastered,
which the loudness chain removes on air anyway), resampled to 22.05 kHz
mono, then per 1024-sample frame the spectral centroid, rolloff, flux and
flatness (ffmpeg ``aspectralstats``) and the RMS level (``astats``).

  * energy 1..10: spectral flux (change, attacks) + onset rate + flatness
    (dense, noisy mixes) - loudness range of the whole track (wide = calm)
    + the master's own loudness, each as a robust z-score against the
    calibration sample; the score's deciles in the library make the scale.
  * brightness 1..10: the spectral centroid (dark .. bright, the readable
    side of "timbre"), deciles likewise.

``audio_features`` (JSONB) keeps the raw values, the score and the scale
values the measurement produced.  ``energy`` / ``brightness`` are what the
library shows and smart blocks filter on: a value set by hand differs from
the measured one in ``audio_features`` and is never replaced (also not by a
re-measurement or a new scale).

The functions down to :func:`measure` take plain values (testable without
ffmpeg or a database); :func:`run` drives the database.
"""

from __future__ import annotations

import json
import math
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

#: Raw measurement.  A new version means: measure everything again.
FEATURE_VERSION = 1
#: Mapping score -> 1..10.  A new scale means: ``--rescale`` (no ffmpeg).
SCALE_VERSION = 2

SAMPLE_RATE = 22050
FRAME = 1024
FRAME_S = FRAME / SAMPLE_RATE
EXCERPT_S = 30.0
TARGET_LUFS = -23.0
#: Frames quieter than this (dBFS after the gain) are pauses, not music.
AUDIBLE_DB = -60.0
#: At least this many audible frames (~2.3 s) or the track is not measured.
MIN_AUDIBLE_FRAMES = 50
FFMPEG_TIMEOUT_S = 60.0
MAX_ERROR = 200

#: Robust reference (median, interquartile range) of each energy input,
#: from a stratified sample of 823 music tracks of the library (2026-11-14).
ENERGY_REFERENCE: dict[str, tuple[float, float]] = {
    "flux": (0.018917, 0.006392),
    "onsets_s": (1.2, 0.6165),
    "flatness": (0.33845, 0.140005),
    "lra": (5.2, 4.35),
    "lufs": (-13.8, 6.95),
}
ENERGY_WEIGHTS: dict[str, float] = {
    "flux": 1.0,
    "onsets_s": 0.5,
    "flatness": 0.75,
    "lra": -0.5,
    "lufs": 0.5,
}
#: Upper edges of the levels 1..9 (a score above the last edge is 10):
#: deciles of all 24,209 measured music tracks (scale 2, 2026-11-15; scale 1
#: came from the 823-track calibration sample).
ENERGY_EDGES: tuple[float, ...] = (
    -2.158,
    -1.385,
    -0.859,
    -0.458,
    -0.102,
    0.219,
    0.556,
    0.942,
    1.445,
)
BRIGHTNESS_EDGES_HZ: tuple[float, ...] = (1369, 1632, 1826, 1984, 2127, 2263, 2397, 2545, 2742)

_METADATA = re.compile(r"lavfi\.(?:aspectralstats|astats)\.1\.(\w+)=(\S+)")


class MeasureError(Exception):
    """A track that cannot be measured (unreadable, silent, too short)."""


# --------------------------------------------------------------------------
# pure functions
# --------------------------------------------------------------------------


def utc_iso(ts: Optional[float] = None) -> str:
    moment = datetime.fromtimestamp(time.time() if ts is None else ts, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def excerpt_start(length_s: float, cuein_s: Optional[float], cueout_s: Optional[float]) -> float:
    """Start of the 30-s excerpt: centred in the cue range (whole track without cues)."""
    lo = max(0.0, float(cuein_s or 0.0))
    hi = float(cueout_s) if cueout_s and float(cueout_s) > lo else float(length_s or 0.0)
    if hi <= lo:
        return lo
    return max(lo, (lo + hi) / 2.0 - EXCERPT_S / 2.0)


def gain_db(lufs: float) -> float:
    """Gain that brings a track of this integrated loudness to the on-air level."""
    return TARGET_LUFS - float(lufs)


def ffmpeg_command(ffmpeg: str, path: str, start: float, gain: float) -> list[str]:
    # Resampling and downmix inside the filter graph: -ar / -ac would only
    # act after the filters.
    graph = (
        f"aresample={SAMPLE_RATE},aformat=sample_fmts=flt:channel_layouts=mono,"
        f"volume={gain:.2f}dB,"
        f"asetnsamples=n={FRAME}:p=0,"
        "aspectralstats=win_size=2048:overlap=0.5:measure=centroid+rolloff+flux+flatness,"
        "astats=metadata=1:reset=1:measure_perchannel=RMS_level:measure_overall=none,"
        "ametadata=mode=print:file=-"
    )
    return [
        ffmpeg, "-hide_banner", "-nostats", "-loglevel", "error", "-threads", "1",
        "-ss", f"{start:.2f}", "-t", f"{EXCERPT_S:.0f}", "-i", path,
        "-vn", "-af", graph, "-f", "null", "-",
    ]  # fmt: skip


def parse_frames(text: str) -> list[dict[str, float]]:
    """The per-frame values of ``ametadata=print`` (frames without RMS / centroid dropped)."""
    frames: list[dict[str, float]] = []
    current: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("frame:"):
            if current:
                frames.append(current)
            current = {}
            continue
        match = _METADATA.search(line)
        if not match:
            continue
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        if math.isfinite(value):
            current[match.group(1)] = value
    if current:
        frames.append(current)
    return [f for f in frames if "RMS_level" in f and "centroid" in f]


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def onset_rate(flux: Sequence[float], frame_s: float = FRAME_S) -> float:
    """Attacks per second: flux peaks above a moving median + 3 MAD, at least 0.1 s apart."""
    n = len(flux)
    if n < 20:
        return 0.0
    half = 10
    min_gap = max(1, round(0.1 / frame_s))
    last = -min_gap
    count = 0
    for i in range(1, n - 1):
        if not (flux[i] > flux[i - 1] and flux[i] >= flux[i + 1]) or i - last < min_gap:
            continue
        window = flux[max(0, i - half) : i + half + 1]
        med = _median(window)
        mad = _median([abs(x - med) for x in window]) or 1e-12
        if flux[i] > med + 3.0 * mad:
            count += 1
            last = i
    return count / (n * frame_s)


def summarize(frames: Sequence[dict[str, float]]) -> dict[str, float]:
    """Raw features of one excerpt; MeasureError when too little of it is audible."""
    levels = [f["RMS_level"] for f in frames]
    audible = [i for i, db in enumerate(levels) if db > AUDIBLE_DB]
    if len(audible) < MIN_AUDIBLE_FRAMES:
        raise MeasureError("silent or too short")
    weight = {i: 10 ** (levels[i] / 20.0) for i in audible}
    total = sum(weight.values()) or 1e-12

    def weighted(key: str) -> float:
        return sum(frames[i].get(key, 0.0) * weight[i] for i in audible) / total

    flux = [f.get("flux", 0.0) for f in frames]
    loud = [levels[i] for i in audible]
    mean_db = sum(loud) / len(loud)
    return {
        "centroid_hz": round(weighted("centroid"), 1),
        "rolloff_hz": round(weighted("rolloff"), 1),
        "flatness": round(weighted("flatness"), 5),
        "flux": round(sum(flux) / len(flux), 6),
        "onsets_s": round(onset_rate(flux), 3),
        "rms_db": round(mean_db, 2),
        "rms_std_db": round(math.sqrt(sum((d - mean_db) ** 2 for d in loud) / len(loud)), 2),
        "frames": len(frames),
    }


def energy_score(raw: dict[str, float], lufs: float, lra: Optional[float]) -> float:
    inputs = dict(raw)
    inputs["lufs"] = float(lufs)
    inputs["lra"] = float(lra) if lra is not None else ENERGY_REFERENCE["lra"][0]
    score = 0.0
    for key, weight in ENERGY_WEIGHTS.items():
        median, iqr = ENERGY_REFERENCE[key]
        score += weight * (float(inputs[key]) - median) / iqr
    return round(score, 4)


def to_level(value: float, edges: Sequence[float]) -> int:
    """1..10: one more than the number of edges the value lies above."""
    return 1 + sum(1 for edge in edges if value > edge)


def scale(features: dict[str, Any]) -> tuple[int, int]:
    """(energy, brightness) of stored raw values with the current scale."""
    return (
        to_level(float(features["energy_score"]), ENERGY_EDGES),
        to_level(float(features["centroid_hz"]), BRIGHTNESS_EDGES_HZ),
    )


Runner = Callable[[list[str]], str]


def subprocess_runner(command: list[str]) -> str:
    """ffmpeg below normal priority, without a window; MeasureError on failure."""
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) | getattr(
        subprocess, "CREATE_NO_WINDOW", 0
    )
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=FFMPEG_TIMEOUT_S,
            creationflags=flags,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MeasureError(f"ffmpeg took longer than {FFMPEG_TIMEOUT_S:.0f} s") from exc
    if done.returncode != 0:
        detail = (done.stderr or "").strip().splitlines()
        raise MeasureError(
            f"ffmpeg exit {done.returncode}: {detail[-1] if detail else ''}"[:MAX_ERROR]
        )
    return done.stdout


def measure(
    path: str,
    length_s: float,
    cuein_s: Optional[float],
    cueout_s: Optional[float],
    lufs: float,
    lra: Optional[float],
    *,
    ffmpeg: str = "ffmpeg",
    runner: Runner = subprocess_runner,
    now: Optional[float] = None,
) -> dict[str, Any]:
    """The ``audio_features`` document of one track (MeasureError when it cannot be measured)."""
    start = excerpt_start(length_s, cuein_s, cueout_s)
    raw = summarize(parse_frames(runner(ffmpeg_command(ffmpeg, path, start, gain_db(lufs)))))
    features: dict[str, Any] = {
        "v": FEATURE_VERSION,
        "scale": SCALE_VERSION,
        "src": "ffmpeg",
        "at": utc_iso(now),
        "start_s": round(start, 2),
        "lufs": float(lufs),
        "lra": None if lra is None else float(lra),
        **raw,
    }
    features["energy_score"] = energy_score(raw, lufs, lra)
    features["energy"], features["brightness"] = scale(features)
    return features


def failed(reason: str, now: Optional[float] = None) -> dict[str, Any]:
    """The document of a track that could not be measured (not retried without --retry-failed)."""
    return {"v": FEATURE_VERSION, "src": "ffmpeg", "at": utc_iso(now), "error": reason[:MAX_ERROR]}


def find_ffmpeg(directory: Optional[str] = None) -> Optional[str]:
    """ffmpeg like the analyzer finds it: FFMPEG_PATH, then PATH (``directory`` first)."""
    if directory:
        found = shutil.which("ffmpeg", path=directory)
        if found:
            return found
    return shutil.which(os.environ.get("FFMPEG_PATH") or "ffmpeg")


# --------------------------------------------------------------------------
# database
# --------------------------------------------------------------------------

COLUMNS = ("energy", "brightness", "audio_features")
LOCK_KEY = "rastatime_audio_features"

#: A value set by hand differs from the one the last measurement produced;
#: only a value equal to it (or none on both sides) follows a new one.
_UPDATE = """
UPDATE cc_files SET
    energy = CASE WHEN energy IS NOT DISTINCT FROM (audio_features->>'energy')::smallint
                  THEN %(energy)s ELSE energy END,
    brightness = CASE WHEN brightness IS NOT DISTINCT FROM (audio_features->>'brightness')::smallint
                      THEN %(brightness)s ELSE brightness END,
    audio_features = %(features)s::jsonb
        || CASE WHEN audio_features ? 'tk' THEN jsonb_build_object('tk', audio_features->'tk')
                ELSE '{}'::jsonb END
WHERE id = %(id)s
"""

_PENDING = """
SELECT f.id, f.filepath, EXTRACT(EPOCH FROM f.length), EXTRACT(EPOCH FROM f.cuein),
       EXTRACT(EPOCH FROM f.cueout), f.loudness_lufs, f.loudness_range_lu
FROM cc_files f
WHERE f.file_exists AND f.import_status = 0 AND NOT COALESCE(f.hidden, FALSE)
  AND f.loudness_lufs IS NOT NULL AND COALESCE(f.filepath, '') <> ''
  AND f.length >= INTERVAL '10 seconds'
  AND {which}
ORDER BY f.id DESC
"""


def columns_ready(cursor) -> bool:
    cursor.execute(
        "SELECT count(*) FROM information_schema.columns WHERE table_name = 'cc_files' AND column_name = ANY(%s)",
        [list(COLUMNS)],
    )
    return cursor.fetchone()[0] == len(COLUMNS)


def pending(
    cursor, limit: int, ids: Optional[Iterable[int]] = None, retry_failed: bool = False
) -> list[tuple]:
    params: list[Any] = []
    if ids:
        which = "f.id = ANY(%s)"
        params.append(sorted(set(ids)))
    elif retry_failed:
        which = "(f.audio_features IS NULL OR f.audio_features ? 'error')"
    else:
        which = "f.audio_features IS NULL"
    sql = _PENDING.format(which=which)
    if limit > 0:
        sql += " LIMIT %s"
        params.append(limit)
    cursor.execute(sql, params)
    return cursor.fetchall()


def remaining(cursor) -> int:
    cursor.execute(
        "SELECT count(*) FROM (" + _PENDING.format(which="f.audio_features IS NULL") + ") AS p"
    )
    return cursor.fetchone()[0]


def write(cursor, file_id: int, features: dict[str, Any]) -> None:
    cursor.execute(
        _UPDATE,
        {
            "id": file_id,
            "energy": features.get("energy"),
            "brightness": features.get("brightness"),
            "features": json.dumps(features, separators=(",", ":")),
        },
    )


def run(
    cursor,
    root: str,
    *,
    ffmpeg: str,
    limit: int = 1000,
    max_seconds: float = 300.0,
    ids: Optional[Sequence[int]] = None,
    retry_failed: bool = False,
    dry_run: bool = False,
    runner: Optional[Runner] = None,
    log: Callable[[str], None] = lambda _line: None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, int]:
    """One pass: measure pending tracks until ``limit`` or ``max_seconds`` (0 = no bound)."""
    runner = runner or subprocess_runner  # looked up now (tests replace it)
    started = clock()
    counts = {"measured": 0, "failed": 0, "skipped": 0}
    base = Path(root)
    for file_id, filepath, length_s, cuein_s, cueout_s, lufs, lra in pending(
        cursor, limit, ids, retry_failed
    ):
        if max_seconds > 0 and clock() - started > max_seconds:
            break
        rel = str(filepath or "").lstrip("/\\").replace("\\", "/")
        path = base / rel
        try:
            if not path.is_file():
                raise MeasureError("file not found")
            features = measure(
                str(path),
                float(length_s or 0.0),
                None if cuein_s is None else float(cuein_s),
                None if cueout_s is None else float(cueout_s),
                float(lufs),
                None if lra is None else float(lra),
                ffmpeg=ffmpeg,
                runner=runner,
            )
            counts["measured"] += 1
            if dry_run:
                log(f"id {file_id}: energy {features['energy']}, brightness {features['brightness']} "
                    f"(score {features['energy_score']}, centroid {features['centroid_hz']} Hz)")  # fmt: skip
        except MeasureError as exc:
            features = failed(str(exc))
            counts["failed"] += 1
            log(f"id {file_id}: not measured - {exc}")
        if dry_run:
            continue
        try:
            write(cursor, int(file_id), features)
        except Exception as exc:  # noqa: BLE001 - a locked row is tried again next run
            counts["skipped"] += 1
            log(f"id {file_id}: not written - {type(exc).__name__}: {str(exc).strip()[:MAX_ERROR]}")
    return counts


def rescale(cursor, *, dry_run: bool = False) -> dict[str, int]:
    """Energy / brightness again from the stored raw values (current scale, hand values stay)."""
    cursor.execute(
        "SELECT id, audio_features FROM cc_files WHERE audio_features ? 'energy_score' AND audio_features ? 'centroid_hz'"
    )
    counts = {"checked": 0, "changed": 0}
    for file_id, features in cursor.fetchall():
        doc = features if isinstance(features, dict) else json.loads(features)
        counts["checked"] += 1
        energy, brightness = scale(doc)
        if (energy, brightness, SCALE_VERSION) == (
            doc.get("energy"),
            doc.get("brightness"),
            doc.get("scale"),
        ):
            continue
        counts["changed"] += 1
        if dry_run:
            continue
        write(
            cursor,
            int(file_id),
            {**doc, "energy": energy, "brightness": brightness, "scale": SCALE_VERSION},
        )
    return counts


# --------------------------------------------------------------------------
# tempo and key (stage 2, ARCHITECTURE 23.116)
# --------------------------------------------------------------------------
#
# librosa does not live in this environment: backend/features/tempo_key.py
# runs in its own (.venv-features, infra/scripts/install-features-venv.ps1)
# and answers one JSON line per track, measured on the stage-1 excerpt
# (``start_s``).  The answer sits under ``audio_features->'tk'``; ``bpm``
# and ``musical_key`` follow it unless they were set by hand or came from a
# BPM tag - the stage-1 rule again (0 counts as an empty BPM, the legacy
# importer writes it for "unknown").  Without the environment, or before
# legacy migration 0086, the pass is simply skipped.

#: Version the worker announces; a new one means: measure tempo / key again.
TK_VERSION = 1
TK_COLUMNS = ("musical_key",)
TK_READY_TIMEOUT_S = 180.0
TK_JOB_TIMEOUT_S = 120.0
REPO_ROOT = Path(__file__).resolve().parents[4]
FEATURES_WORKER = REPO_ROOT / "backend" / "features" / "tempo_key.py"
#: what cc_files_musical_key_camelot accepts: 1A..12A (minor), 1B..12B (major)
CAMELOT = re.compile(r"^(1[0-2]|[1-9])[AB]$")


class WorkerError(Exception):
    """The tempo / key worker did not start, died or stopped answering."""


def find_features_worker() -> Optional[tuple[str, str]]:
    """(python, script) of the tempo / key worker; None while its environment is missing."""
    venv = REPO_ROOT / ".venv-features"
    default = venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"
    python = Path(os.environ.get("RASTATIME_FEATURES_PYTHON") or default)
    if not (python.is_file() and FEATURES_WORKER.is_file()):
        return None
    return str(python), str(FEATURES_WORKER)


def tempo_key_doc(answer: dict[str, Any], src: str, now: Optional[float] = None) -> dict[str, Any]:
    """The ``audio_features->'tk'`` document of one worker answer (MeasureError if unusable)."""
    if answer.get("error"):
        raise MeasureError(str(answer["error"])[:MAX_ERROR])
    try:
        tempo = float(answer["tempo"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MeasureError("answer without a tempo") from exc
    key = str(answer.get("key") or "")
    if not (30.0 <= tempo <= 300.0) or not CAMELOT.match(key):
        raise MeasureError(f"implausible answer: tempo {tempo}, key {key!r}")
    doc: dict[str, Any] = {
        "v": TK_VERSION,
        "src": src,
        "at": utc_iso(now),
        "tempo": round(tempo, 1),
        "bpm": int(round(tempo)),
        "key": key,
    }
    for name in ("tempo_grid", "beats", "key_corr", "key_margin", "key_second"):
        if name in answer:
            doc[name] = answer[name]
    return doc


def tempo_key_failed(reason: str, now: Optional[float] = None) -> dict[str, Any]:
    """The ``tk`` document of a track without tempo / key (not retried without --retry-failed)."""
    return {"v": TK_VERSION, "at": utc_iso(now), "error": reason[:MAX_ERROR]}


class TempoKeyWorker:
    """The worker process: one JSON line in, one out; a reader thread enforces the timeouts."""

    def __init__(
        self,
        python: str,
        script: str,
        ffmpeg: str,
        *,
        ready_timeout: float = TK_READY_TIMEOUT_S,
        job_timeout: float = TK_JOB_TIMEOUT_S,
    ) -> None:
        flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        self.job_timeout = job_timeout
        self.src = "librosa ?"
        self._lines: queue.Queue[Optional[str]] = queue.Queue()
        try:
            self._proc = subprocess.Popen(  # pylint: disable=consider-using-with
                [python, "-I", script, "--ffmpeg", ffmpeg],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=flags,
            )
        except OSError as exc:
            raise WorkerError(f"cannot start {python}: {exc}") from exc
        threading.Thread(target=self._read, daemon=True).start()
        try:
            ready = self._next(ready_timeout)
            if ready.get("v") != TK_VERSION:
                raise WorkerError(f"worker version {ready.get('v')!r}, expected {TK_VERSION}")
        except WorkerError:
            self.close()
            raise
        self.src = f"librosa {ready.get('librosa') or '?'}"

    def _read(self) -> None:
        stdout = self._proc.stdout
        if stdout is not None:
            for line in stdout:
                self._lines.put(line)
        self._lines.put(None)

    def _next(self, timeout: float) -> dict[str, Any]:
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty as exc:
            raise WorkerError(f"no answer within {timeout:.0f} s") from exc
        if line is None:
            raise WorkerError(f"worker ended (exit {self._proc.poll()})")
        try:
            return json.loads(line)
        except ValueError as exc:
            raise WorkerError(f"unreadable answer {line.strip()[:80]!r}") from exc

    def analyse(self, file_id: int, path: str, start: float) -> dict[str, Any]:
        job = json.dumps({"id": file_id, "path": path, "start": start})
        try:
            if self._proc.stdin is None:
                raise OSError("no stdin")
            self._proc.stdin.write(job + "\n")
            self._proc.stdin.flush()
        except OSError as exc:
            raise WorkerError(f"worker gone: {exc}") from exc
        answer = self._next(self.job_timeout)
        if answer.get("id") != file_id:
            raise WorkerError(f"answer for id {answer.get('id')!r} instead of {file_id}")
        return answer

    def close(self) -> None:
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=10)


_PENDING_TK = """
SELECT f.id, f.filepath, (f.audio_features->>'start_s')::float
FROM cc_files f
WHERE f.file_exists AND f.import_status = 0 AND NOT COALESCE(f.hidden, FALSE)
  AND COALESCE(f.filepath, '') <> '' AND f.audio_features ? 'energy_score'
  AND {which}
ORDER BY f.id DESC
"""
_TK_DUE = "(NOT f.audio_features ? 'tk' OR COALESCE((f.audio_features->'tk'->>'v')::int, 0) < %s)"

#: like _UPDATE: a column that differs from the last measurement was set by
#: hand (or by a tag) and stays; SET sees the old row, so the CASE compares
#: with the previous ``tk``.
_UPDATE_TK = """
UPDATE cc_files SET
    bpm = CASE WHEN NULLIF(bpm, 0) IS NOT DISTINCT FROM (audio_features->'tk'->>'bpm')::int
               THEN %(bpm)s ELSE bpm END,
    musical_key = CASE WHEN musical_key IS NOT DISTINCT FROM (audio_features->'tk'->>'key')
                       THEN %(key)s ELSE musical_key END,
    audio_features = jsonb_set(COALESCE(audio_features, '{}'::jsonb), '{tk}', %(tk)s::jsonb)
WHERE id = %(id)s
"""


def tempo_key_columns_ready(cursor) -> bool:
    cursor.execute(
        "SELECT count(*) FROM information_schema.columns WHERE table_name = 'cc_files' AND column_name = ANY(%s)",
        [list(TK_COLUMNS)],
    )
    return cursor.fetchone()[0] == len(TK_COLUMNS)


def pending_tempo_key(
    cursor, limit: int, ids: Optional[Iterable[int]] = None, retry_failed: bool = False
) -> list[tuple]:
    params: list[Any] = []
    if ids:
        which = "f.id = ANY(%s)"
        params.append(sorted(set(ids)))
    elif retry_failed:
        which = f"({_TK_DUE} OR f.audio_features->'tk' ? 'error')"
        params.append(TK_VERSION)
    else:
        which = _TK_DUE
        params.append(TK_VERSION)
    sql = _PENDING_TK.format(which=which)
    if limit > 0:
        sql += " LIMIT %s"
        params.append(limit)
    cursor.execute(sql, params)
    return cursor.fetchall()


def remaining_tempo_key(cursor) -> int:
    sql = "SELECT count(*) FROM (" + _PENDING_TK.format(which=_TK_DUE) + ") AS p"
    cursor.execute(sql, [TK_VERSION])
    return cursor.fetchone()[0]


def write_tempo_key(cursor, file_id: int, doc: dict[str, Any]) -> None:
    cursor.execute(
        _UPDATE_TK,
        {
            "id": file_id,
            "bpm": doc.get("bpm"),
            "key": doc.get("key"),
            "tk": json.dumps(doc, separators=(",", ":")),
        },
    )


def run_tempo_key(
    cursor,
    root: str,
    *,
    start_worker: Callable[[], Any],
    limit: int = 1000,
    max_seconds: float = 300.0,
    ids: Optional[Sequence[int]] = None,
    retry_failed: bool = False,
    dry_run: bool = False,
    log: Callable[[str], None] = lambda _line: None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, int]:
    """One pass over tracks without tempo / key; the worker starts only when there is work."""
    counts = {"measured": 0, "failed": 0, "skipped": 0}
    rows = pending_tempo_key(cursor, limit, ids, retry_failed)
    if not rows:
        return counts
    started = clock()
    try:
        worker = start_worker()
    except WorkerError as exc:
        log(f"tempo / key: worker did not start - {exc}")
        return counts
    base = Path(root)
    try:
        for file_id, filepath, start_s in rows:
            if max_seconds > 0 and clock() - started > max_seconds:
                break
            path = base / str(filepath or "").lstrip("/\\").replace("\\", "/")
            try:
                if not path.is_file():
                    raise MeasureError("file not found")
                answer = worker.analyse(int(file_id), str(path), float(start_s or 0.0))
                doc = tempo_key_doc(answer, worker.src)
                counts["measured"] += 1
                if dry_run:
                    log(f"id {file_id}: tempo {doc['tempo']} (bpm {doc['bpm']}), key {doc['key']}")
            except MeasureError as exc:
                doc = tempo_key_failed(str(exc))
                counts["failed"] += 1
                log(f"id {file_id}: no tempo / key - {exc}")
            if dry_run:
                continue
            try:
                write_tempo_key(cursor, int(file_id), doc)
            except Exception as exc:  # noqa: BLE001 - a locked row is tried again next run
                counts["skipped"] += 1
                log(
                    f"id {file_id}: not written - {type(exc).__name__}: {str(exc).strip()[:MAX_ERROR]}"
                )
    except WorkerError as exc:
        log(f"tempo / key: worker stopped - {exc}")
    finally:
        worker.close()
    return counts
