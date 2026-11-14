"""
RASTATIME 2026-11-14 - measure energy and brightness of library tracks
(``storage/audio_features.py``, ARCHITECTURE 23.115).

Fired every ten minutes by the Windows task RASTATIME-AudioFeatures
(``scripts/audio-features.ps1``); by hand for the first pass over the
library (``--limit 0 --max-seconds 0``).  Measures tracks that have a
loudness value but no ``audio_features`` yet, newest first; a value set by
hand in Edit Track is never replaced.  Prints one line per track that could
not be measured and one summary line when it did something; an idle run
prints nothing.

  --ids 12 34       measure these tracks again (hand values stay)
  --retry-failed    also the tracks whose measurement failed before
  --rescale         energy / brightness again from the stored raw values
                    (after a new scale; no ffmpeg)
  --dry-run         measure and print, write nothing

Only one run at a time (PostgreSQL advisory lock); a run that finds the
lock taken ends quietly.  Exit code 1 = ffmpeg not found.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection

from ... import audio_features as af
from ...root import get_storage_root


class Command(BaseCommand):
    help = "Measure energy and brightness of library tracks that have none yet (ffmpeg)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limit", type=int, default=1000, help="at most this many tracks (0 = all)"
        )
        parser.add_argument(
            "--max-seconds", type=float, default=300.0, help="stop after this long (0 = no limit)"
        )
        parser.add_argument("--ids", nargs="+", type=int, help="measure these file ids again")
        parser.add_argument(
            "--retry-failed", action="store_true", help="also tracks that failed before"
        )
        parser.add_argument(
            "--rescale", action="store_true", help="recompute the levels from stored values"
        )
        parser.add_argument("--dry-run", action="store_true", help="write nothing")
        parser.add_argument("--ffmpeg-dir", help="directory holding ffmpeg")

    def handle(self, *args: Any, **options: Any) -> None:
        with connection.cursor() as cursor:
            if not af.columns_ready(cursor):
                self.stdout.write(
                    "cc_files has no energy / brightness yet - legacy migration 0085 first"
                )
                return
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", [af.LOCK_KEY])
            if not cursor.fetchone()[0]:
                return  # another run is busy
            try:
                # a row the fill pass or an editor holds is tried again next run
                cursor.execute("SET lock_timeout = '2s'")
                if options["rescale"]:
                    counts = af.rescale(cursor, dry_run=options["dry_run"])
                    note = " (dry run)" if options["dry_run"] else ""
                    self.stdout.write(
                        f"rescaled: {counts['changed']} of {counts['checked']} measured tracks changed{note}"
                    )
                    return
                ffmpeg = af.find_ffmpeg(options.get("ffmpeg_dir"))
                if not ffmpeg:
                    raise CommandError(
                        "ffmpeg not found - set FFMPEG_PATH, put ffmpeg on PATH or pass --ffmpeg-dir"
                    )
                counts = af.run(
                    cursor,
                    str(get_storage_root()),
                    ffmpeg=ffmpeg,
                    limit=options["limit"],
                    max_seconds=options["max_seconds"],
                    ids=options.get("ids"),
                    retry_failed=options["retry_failed"],
                    dry_run=options["dry_run"],
                    log=self.stdout.write,
                )
                if counts["measured"] or counts["failed"] or counts["skipped"]:
                    left = af.remaining(cursor)
                    note = " (dry run, nothing written)" if options["dry_run"] else ""
                    self.stdout.write(
                        f"measured {counts['measured']}, failed {counts['failed']}, "
                        f"not written {counts['skipped']}, waiting {left}{note}"
                    )
            finally:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [af.LOCK_KEY])
