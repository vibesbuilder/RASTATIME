"""
RASTATIME 2026-11-14 - measure energy and brightness of library tracks
(``storage/audio_features.py``, ARCHITECTURE 23.115); since 2026-11-15 also
tempo and key (stage 2, ARCHITECTURE 23.116).  Only tracks of a track type
with "Analyze audio features" (Settings -> Track Types, legacy migration
0087; before it the type with the code 'music') - ARCHITECTURE 23.117.

Fired every ten minutes by the Windows task RASTATIME-AudioFeatures
(``scripts/audio-features.ps1``); by hand for the first pass over the
library (``--limit 0 --max-seconds 0``).  Measures tracks that have a
loudness value but no ``audio_features`` yet, newest first, then - in the
time left - tempo and key of measured tracks that have none yet (librosa
in its own environment, ``.venv-features``; skipped while it or legacy
migration 0086 is missing).  A value set by hand in Edit Track is never
replaced.  Prints one line per track that could not be measured and one
summary line per part that did something; an idle run prints nothing.

  --ids 12 34        measure these tracks again (hand values stay)
  --retry-failed     also the tracks whose measurement failed before
  --rescale          energy / brightness again from the stored raw values
                     (after a new scale; no ffmpeg)
  --no-tempo-key     energy / brightness only
  --tempo-key-only   tempo / key only
  --clear-unselected remove the measured values of tracks whose type is not
                     analysed (hand values and BPM tags stay; no ffmpeg)
  --dry-run          measure and print, write nothing

Only one run at a time (PostgreSQL advisory lock); a run that finds the
lock taken ends quietly.  Exit code 1 = ffmpeg not found.
"""

from __future__ import annotations

import time
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection

from ... import audio_features as af
from ...root import get_storage_root


class Command(BaseCommand):
    help = "Measure energy / brightness and tempo / key of library tracks that have none yet."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limit", type=int, default=1000, help="at most this many tracks per part (0 = all)"
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
        parser.add_argument("--no-tempo-key", action="store_true", help="energy / brightness only")
        parser.add_argument("--tempo-key-only", action="store_true", help="tempo / key only")
        parser.add_argument(
            "--clear-unselected",
            action="store_true",
            help="remove measured values of tracks whose type is not analysed",
        )
        parser.add_argument("--dry-run", action="store_true", help="write nothing")
        parser.add_argument("--ffmpeg-dir", help="directory holding ffmpeg")

    def handle(self, *args: Any, **options: Any) -> None:
        started = time.monotonic()
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
                if options["clear_unselected"]:
                    counts = af.clear_unselected(cursor, dry_run=options["dry_run"])
                    note = " (dry run, nothing written)" if options["dry_run"] else ""
                    self.stdout.write(
                        f"cleared the measured values of {counts['tracks']} tracks of types without "
                        f"the audio analysis; kept by hand or tag: energy {counts['kept_energy']}, "
                        f"brightness {counts['kept_brightness']}, bpm {counts['kept_bpm']}, "
                        f"key {counts['kept_key']}{note}"
                    )
                    return
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
                root = str(get_storage_root())
                note = " (dry run, nothing written)" if options["dry_run"] else ""
                if not options["tempo_key_only"]:
                    counts = af.run(
                        cursor,
                        root,
                        ffmpeg=ffmpeg,
                        limit=options["limit"],
                        max_seconds=options["max_seconds"],
                        ids=options.get("ids"),
                        retry_failed=options["retry_failed"],
                        dry_run=options["dry_run"],
                        log=self.stdout.write,
                    )
                    if counts["measured"] or counts["failed"] or counts["skipped"]:
                        self.stdout.write(
                            f"measured {counts['measured']}, failed {counts['failed']}, "
                            f"not written {counts['skipped']}, waiting {af.remaining(cursor)}{note}"
                        )
                if not options["no_tempo_key"]:
                    self._tempo_key(cursor, root, ffmpeg, started, note, options)
            finally:
                cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [af.LOCK_KEY])

    def _tempo_key(
        self, cursor, root: str, ffmpeg: str, started: float, note: str, options
    ) -> None:
        explicit = options["tempo_key_only"]
        if not af.tempo_key_columns_ready(cursor):
            if explicit:
                self.stdout.write("cc_files has no musical_key yet - legacy migration 0086 first")
            return
        worker = af.find_features_worker()
        if worker is None:
            if explicit:
                self.stdout.write(
                    "no tempo / key environment - run infra/scripts/install-features-venv.ps1"
                )
            return
        max_seconds = options["max_seconds"]
        if max_seconds > 0:
            max_seconds -= time.monotonic() - started
            if max_seconds <= 0:
                return  # the energy part used the run; tempo / key next time
        python, script = worker
        counts = af.run_tempo_key(
            cursor,
            root,
            start_worker=lambda: af.TempoKeyWorker(python, script, ffmpeg),
            limit=options["limit"],
            max_seconds=max_seconds,
            ids=options.get("ids"),
            retry_failed=options["retry_failed"],
            dry_run=options["dry_run"],
            log=self.stdout.write,
        )
        if counts["measured"] or counts["failed"] or counts["skipped"]:
            self.stdout.write(
                f"tempo / key: measured {counts['measured']}, failed {counts['failed']}, "
                f"not written {counts['skipped']}, waiting {af.remaining_tempo_key(cursor)}{note}"
            )
