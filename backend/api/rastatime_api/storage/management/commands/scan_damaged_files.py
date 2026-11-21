"""
RASTATIME 2026-11-21 - library scan for damaged or cut-short files
(operator Go 2026-11-21, variant "report only"; ARCHITECTURE 23.127).

Two dead-air alarms (2026-11-18 a damaged M4A, 2026-11-21 a truncated
MP3) came from library files that stop decoding long before their stored
length: the playout trusts the length / cue-out, so the queue ran empty
until the next row.  Since 2026-11-21 the import refuses such files
(analyzer, ARCHITECTURE 23.123); this command checks the files that are
already in the library with the same rule.

Every file (``cc_files``: file exists, not hidden) is decoded once with
ffmpeg (audio only, below normal priority) and the decoded length is
compared with the end the playout uses - the cue-out, else the stored
length.  A file whose audio ends more than 2 s AND more than 1 % before
that end is reported, as is a file ffmpeg cannot decode, a missing file
and a decode that ran out of time.  Nothing is changed: the report (CSV)
lists id, artist, title, path and the lengths; the decision per file
(Disabled, replace, delete) is the operator's.

  --report PATH     the CSV (default: <logs>/damaged-files-YYYY-MM-DD.csv,
                    <logs> = the logs folder next to the config folder)
  --resume          go on after the last file of an interrupted run of the
                    same report (``<report>.progress`` holds its id)
  --ids 12 34       check only these files (report not resumable)
  --limit N         at most N files this run (0 = all)
  --ffmpeg-dir DIR  directory holding ffmpeg

One run at a time (PostgreSQL advisory lock).  Prints a progress line
every 500 files and a summary; exit code 1 = ffmpeg not found.
"""

from __future__ import annotations

import csv
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection

from ... import audio_features as af
from ...root import get_storage_root

LOCK_KEY = "rastatime_scan_damaged_files"
#: decode timeout: at least this, else half the file's length (decoding runs
#: far faster than real time; same rule as the import check)
MIN_TIMEOUT_S = 120.0
TIMEOUT_FACTOR = 0.5
PROGRESS_EVERY = 500
MAX_DETAIL = 300
FIELDS = (
    "id",
    "status",
    "artist",
    "title",
    "path",
    "length_s",
    "cue_out_s",
    "decoded_s",
    "missing_s",
    "detail",
)

try:  # the same tolerance and parser as the import check
    from rastatime_analyzer.pipeline.analyze_playability import decoded_seconds, is_truncated
except ImportError:  # pragma: no cover - analyzer not installed in this environment
    decoded_seconds = is_truncated = None  # type: ignore[assignment]


@dataclass
class Result:
    status: str  # ok | truncated | unplayable | missing | timeout
    decoded: Optional[float] = None
    detail: str = ""


def _low_priority() -> int:
    if os.name == "nt":
        return getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    return 0


def playout_end(length: Optional[float], cue_out: Optional[float]) -> Optional[float]:
    """The second at which the playout ends the file: cue-out, else the length."""
    for value in (cue_out, length):
        if value is not None and value > 0:
            return float(value)
    return None


def check_file(path: str, end: Optional[float], ffmpeg: str) -> Result:
    """Decode *path* once and judge it against *end* (seconds)."""
    if not os.path.isfile(path):
        return Result("missing", detail="file not found")
    timeout = max(MIN_TIMEOUT_S, TIMEOUT_FACTOR * end) if end else MIN_TIMEOUT_S
    cmd = [
        ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-v", "error",
        "-progress", "pipe:1", "-i", path, "-vn", "-f", "null", "-",
    ]  # fmt: skip
    try:
        done = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=_low_priority(),
        )
    except subprocess.TimeoutExpired:
        return Result("timeout", detail=f"decode took longer than {timeout:.0f} s")
    tail = " ".join((done.stderr or "").strip().splitlines()[-2:])[:MAX_DETAIL]
    if done.returncode != 0:
        return Result("unplayable", detail=f"ffmpeg exit {done.returncode}: {tail}")
    decoded = decoded_seconds(done.stdout or "")
    if decoded is None:
        return Result("ok", detail="no decode progress - length not compared")
    if end is not None and is_truncated(end, decoded):
        return Result("truncated", decoded=decoded, detail=tail)
    return Result("ok", decoded=decoded)


def default_report() -> Path:
    config = os.environ.get("RASTATIME_CONFIG_FILEPATH")
    logs = Path(config).resolve().parent.parent / "logs" if config else Path.cwd()
    if not logs.is_dir():
        logs = Path.cwd()
    return logs / f"damaged-files-{date.today().isoformat()}.csv"


class Command(BaseCommand):
    help = "Decode every library file once and report the damaged or cut-short ones (read-only)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--report", help="CSV to write (default: logs/damaged-files-DATE.csv)")
        parser.add_argument("--resume", action="store_true", help="go on after an interrupted run")
        parser.add_argument("--ids", nargs="+", type=int, help="check only these file ids")
        parser.add_argument(
            "--limit", type=int, default=0, help="at most this many files (0 = all)"
        )
        parser.add_argument("--ffmpeg-dir", help="directory holding ffmpeg")

    def handle(self, *args: Any, **options: Any) -> None:
        if decoded_seconds is None:
            raise CommandError("the analyzer package (rastatime_analyzer) is not installed")
        ffmpeg = af.find_ffmpeg(options.get("ffmpeg_dir"))
        if not ffmpeg:
            raise CommandError(
                "ffmpeg not found - set FFMPEG_PATH, put ffmpeg on PATH or pass --ffmpeg-dir",
                returncode=1,
            )
        report = Path(options["report"]) if options.get("report") else default_report()
        progress = report.with_name(report.name + ".progress")
        ids = options.get("ids")
        after = 0
        if options.get("resume") and not ids and progress.is_file():
            try:
                after = int(progress.read_text(encoding="ascii").strip() or 0)
            except ValueError:
                after = 0
        root = get_storage_root()
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", [LOCK_KEY])
            if not cursor.fetchone()[0]:
                self.stdout.write("another scan is running - nothing done")
                return
            try:
                rows = self._files(cursor, ids, after, options.get("limit") or 0)
                self._scan(rows, root, ffmpeg, report, progress, append=after > 0, track=not ids)
            finally:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [LOCK_KEY])

    @staticmethod
    def _files(cursor, ids, after: int, limit: int) -> list[tuple]:
        sql = (
            "SELECT id, filepath, COALESCE(artist_name, ''), COALESCE(track_title, ''), "
            "EXTRACT(EPOCH FROM length), EXTRACT(EPOCH FROM cueout) "
            "FROM cc_files WHERE file_exists AND NOT hidden "
        )
        params: list = []
        if ids:
            sql += "AND id = ANY(%s) "
            params.append(list(ids))
        else:
            sql += "AND id > %s "
            params.append(after)
        sql += "ORDER BY id"
        if limit > 0:
            sql += " LIMIT %s"
            params.append(limit)
        cursor.execute(sql, params)
        return cursor.fetchall()

    def _scan(self, rows, root: str, ffmpeg: str, report: Path, progress: Path, *, append, track):
        started = time.monotonic()
        counts = {"ok": 0, "truncated": 0, "unplayable": 0, "missing": 0, "timeout": 0}
        new_file = not (append and report.is_file())
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open("a" if not new_file else "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            if new_file:
                writer.writerow(FIELDS)
            for n, (file_id, rel, artist, title, length, cue_out) in enumerate(rows, 1):
                length = float(length) if length is not None else None
                cue_out = float(cue_out) if cue_out is not None else None
                path = os.path.join(root, rel) if rel and not os.path.isabs(rel) else (rel or "")
                end = playout_end(length, cue_out)
                result = check_file(path, end, ffmpeg)
                counts[result.status] += 1
                if result.status != "ok":
                    missing = (
                        round(end - result.decoded, 1)
                        if end is not None and result.decoded is not None
                        else ""
                    )
                    writer.writerow(
                        [
                            file_id,
                            result.status,
                            artist,
                            title,
                            path,
                            round(length, 1) if length is not None else "",
                            round(cue_out, 1) if cue_out is not None else "",
                            round(result.decoded, 1) if result.decoded is not None else "",
                            missing,
                            result.detail,
                        ]
                    )
                    fh.flush()
                if track:
                    progress.write_text(str(file_id), encoding="ascii")
                if n % PROGRESS_EVERY == 0:
                    self.stdout.write(
                        f"{n} / {len(rows)} checked ({time.monotonic() - started:.0f} s), "
                        f"found {n - counts['ok']}"
                    )
        found = sum(v for k, v in counts.items() if k != "ok")
        self.stdout.write(
            f"checked {len(rows)} files in {time.monotonic() - started:.0f} s: "
            f"{counts['truncated']} cut short, {counts['unplayable']} not decodable, "
            f"{counts['missing']} missing, {counts['timeout']} timed out"
            + (f" - report {report}" if found else " - nothing found")
        )
