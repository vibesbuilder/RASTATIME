"""
RASTATIME 2026-11-24 - library scan: can Liquidsoap decode every file?
(operator Go 2026-11-24; ARCHITECTURE 23.132).

The dead air of 2026-11-23 19:07-20:00 came from a library MP3 that the
standalone ffmpeg decodes without a message but Liquidsoap's own FFmpeg
refused at playout time; a lossless remux made it decodable.  Since
2026-11-24 the import asks Liquidsoap (analyzer ``check_liquidsoap``); this
command asks it for the files already in the library, with the same probe.

Every file (``cc_files``: imported, file exists, not hidden) is resolved
by a short-lived Liquidsoap process (not the playout instance), in batches
of ``--batch`` files per process (~12 ms per file).  Report only, unless
``--repair``:

  --repair          remux the files Liquidsoap cannot decode losslessly
                    (``ffmpeg -map 0 -c copy``) and keep the remux when
                    Liquidsoap decodes it: the original moves to
                    ``<storage>/_replaced/remux-YYYY-MM-DD/<id>-<name>``, the
                    remux takes its place (same path), md5 / filesize are
                    updated and ``source_md5`` keeps the old md5 for the
                    duplicate check.  A file scheduled now or within the
                    next 6 hours is skipped.
  --report PATH     the CSV (default: <logs>/liquidsoap-decode-YYYY-MM-DD.csv)
  --ids 12 34       check only these files
  --limit N         at most N files (0 = all)
  --batch N         files per Liquidsoap process (default 200)
  --ffmpeg-dir DIR  directory holding ffmpeg (for --repair)

One run at a time (PostgreSQL advisory lock); exit code 1 = no Liquidsoap
binary (or no ffmpeg with --repair).
"""

from __future__ import annotations

import csv
import os
import shutil
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, transaction
from django.utils import timezone
from rastatime_shared.files import compute_md5

from ....schedule.models import Schedule
from ... import audio_features as af
from ...models import File
from ...root import get_storage_root

try:
    from rastatime_analyzer.pipeline import check_liquidsoap as cl
except ImportError:  # pragma: no cover - analyzer not installed in this environment
    cl = None  # type: ignore[assignment]

LOCK_KEY = "rastatime_scan_liquidsoap_decode"
SCHEDULE_GUARD = timedelta(hours=6)
FIELDS = ("id", "status", "artist", "title", "path", "detail")
REPLACED_DIR = "_replaced"


def default_report() -> Path:
    config = os.environ.get("RASTATIME_CONFIG_FILEPATH")
    logs = Path(config).resolve().parent.parent / "logs" if config else Path.cwd()
    if not logs.is_dir():
        logs = Path.cwd()
    return logs / f"liquidsoap-decode-{date.today().isoformat()}.csv"


def scheduled_soon(file_id: int, now=None) -> bool:
    """In cc_schedule now or within the next SCHEDULE_GUARD hours."""
    now = now or timezone.now()
    return Schedule.objects.filter(
        file_id=file_id, ends_at__gt=now, starts_at__lt=now + SCHEDULE_GUARD
    ).exists()


def backup_path(root: Path, file_id: int, path: Path, today: Optional[date] = None) -> Path:
    """Where the original of a repaired file is kept."""
    folder = root / REPLACED_DIR / f"remux-{(today or date.today()).isoformat()}"
    return folder / f"{file_id}-{path.name}"


def repair_file(
    file_id: int, path: Path, root: Path, binary: str, ffmpeg: str, now_fn=timezone.now
) -> tuple[str, str]:
    """Remux one file in place; (status, detail).  The original is kept in _replaced/."""
    if scheduled_soon(file_id, now_fn()):
        return "skipped", "scheduled now or within the next 6 hours"
    # the import's variants: lossless remux, then without the embedded picture
    remux, how = cl.remux_until_decodable(path, binary, ffmpeg)
    if remux is None:
        return "repair_failed", f"{how} - original kept"
    if "no answer" in how:  # the library file is only replaced on a clear yes
        remux.unlink(missing_ok=True)
        return "repair_failed", "no answer from Liquidsoap about the remux - original kept"
    backup = backup_path(root, file_id, path)
    old_md5 = compute_md5(path)
    try:
        with transaction.atomic():
            row = File.objects.select_for_update().get(pk=file_id)
            if scheduled_soon(file_id, now_fn()):
                raise RuntimeError("got scheduled meanwhile")
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
            os.replace(remux, path)
            File.objects.filter(pk=file_id).update(
                md5=compute_md5(path),
                source_md5=row.source_md5 or row.md5 or old_md5,
                size=path.stat().st_size,
                updated_at=now_fn(),
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        remux.unlink(missing_ok=True)
        if backup.is_file() and compute_md5(path) != old_md5:
            os.replace(backup, path)  # the file was swapped before the failure: undo
        return "repair_failed", f"original kept: {exc}"
    return "repaired", f"{how}; original kept as {backup}"


class Command(BaseCommand):
    help = "Ask Liquidsoap whether it can decode every library file (report; --repair remuxes)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--repair", action="store_true", help="remux undecodable files")
        parser.add_argument(
            "--report", help="CSV to write (default: logs/liquidsoap-decode-DATE.csv)"
        )
        parser.add_argument("--ids", nargs="+", type=int, help="check only these file ids")
        parser.add_argument("--limit", type=int, default=0, help="at most this many files")
        parser.add_argument("--batch", type=int, default=200, help="files per Liquidsoap process")
        parser.add_argument("--ffmpeg-dir", help="directory holding ffmpeg (for --repair)")

    def handle(self, *args: Any, **options: Any) -> None:
        if cl is None:
            raise CommandError("the analyzer package (rastatime_analyzer) is not installed")
        binary = cl.liquidsoap_binary()
        if not binary:
            raise CommandError("no Liquidsoap binary - set RASTATIME_LIQUIDSOAP_EXE", returncode=1)
        ffmpeg = ""
        if options.get("repair"):
            ffmpeg = af.find_ffmpeg(options.get("ffmpeg_dir")) or ""
            if not ffmpeg:
                raise CommandError(
                    "ffmpeg not found - set FFMPEG_PATH or pass --ffmpeg-dir", returncode=1
                )
        report = Path(options["report"]) if options.get("report") else default_report()
        root = Path(get_storage_root())
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", [LOCK_KEY])
            if not cursor.fetchone()[0]:
                self.stdout.write("another scan is running - nothing done")
                return
            try:
                rows = self._files(cursor, options.get("ids"), options.get("limit") or 0)
                self._scan(rows, root, binary, ffmpeg, report, max(1, options["batch"]))
            finally:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [LOCK_KEY])

    @staticmethod
    def _files(cursor, ids, limit: int) -> list[tuple]:
        sql = (
            "SELECT id, filepath, COALESCE(artist_name, ''), COALESCE(track_title, '') "
            "FROM cc_files WHERE file_exists AND NOT hidden AND import_status = 0 "
            "AND COALESCE(filepath, '') <> '' "
        )
        params: list = []
        if ids:
            sql += "AND id = ANY(%s) "
            params.append(list(ids))
        sql += "ORDER BY id"
        if limit > 0:
            sql += " LIMIT %s"
            params.append(limit)
        cursor.execute(sql, params)
        return cursor.fetchall()

    def _scan(self, rows, root: Path, binary: str, ffmpeg: str, report: Path, batch: int):
        started = time.monotonic()
        counts: dict[str, int] = {}
        findings: list[list[Any]] = []
        for start in range(0, len(rows), batch):
            chunk = []
            for file_id, rel, artist, title in rows[start : start + batch]:
                path = Path(rel) if os.path.isabs(rel) else root / rel
                if not path.is_file():
                    counts["missing"] = counts.get("missing", 0) + 1
                    findings.append(
                        [file_id, "missing", artist, title, str(path), "file not found"]
                    )
                    continue
                chunk.append((file_id, path, artist, title))
            answers = cl.liquidsoap_decodes([str(p) for _i, p, _a, _t in chunk], binary)
            for (file_id, path, artist, title), ok in zip(chunk, answers, strict=True):
                if ok:
                    counts["ok"] = counts.get("ok", 0) + 1
                    continue
                status, detail = (
                    ("unknown", "no answer from Liquidsoap")
                    if ok is None
                    else ("undecodable", "Liquidsoap cannot decode it")
                )
                if ok is False and ffmpeg:
                    status, detail = repair_file(file_id, path, root, binary, ffmpeg)
                counts[status] = counts.get(status, 0) + 1
                findings.append([file_id, status, artist, title, str(path), detail])
            done = min(start + batch, len(rows))
            if done % 2000 < batch or done == len(rows):
                self.stdout.write(
                    f"{done} / {len(rows)} checked ({time.monotonic() - started:.0f} s), "
                    f"found {len(findings)}"
                )
        if findings:
            report.parent.mkdir(parents=True, exist_ok=True)
            with report.open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh, delimiter=";")
                writer.writerow(FIELDS)
                writer.writerows(findings)
        summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        self.stdout.write(
            f"checked {len(rows)} files in {time.monotonic() - started:.0f} s: {summary}"
            + (f" - report {report}" if findings else " - nothing found")
        )
