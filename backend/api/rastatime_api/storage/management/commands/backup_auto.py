"""
RASTATIME 2026-09-17 - automatic backups (work-order point 10, stage 3).

Meant to be fired daily by the Windows Task Scheduler (see
``scripts/backup-auto.ps1``); the command itself decides whether a run
is due (Settings -> Backup -> Automatic backups: every N days), executes
the very same backup job as the "Back up now" button - database +
configuration ZIP, plus the media mirror when "Include media library"
is on - and afterwards prunes ZIPs older than the configured retention
(the newest always survives).

Exit codes: 0 = backed up or nothing due, 1 = the backup failed.
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from ... import backup as storage_backup


class Command(BaseCommand):
    help = "Run the automatic backup when due (database + config ZIP, optional media mirror), then prune old ZIPs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even when not due (still requires enabled + folder).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=7200,
            help="Seconds to wait for the job (default 7200; the first media mirror copies everything).",
        )

    def handle(self, *args, **options):
        cfg = storage_backup.get_auto_config()
        due, reason = storage_backup.auto_backup_due(cfg)
        if options["force"]:
            reason = "forced by the operator"
        elif not due:
            self.stdout.write(f"nothing to do: {reason}")
            return
        try:
            state = storage_backup.JOB.start()
        except (storage_backup.BackupInProgress, storage_backup.InvalidFolder, RuntimeError) as exc:
            self.stderr.write(f"backup not started: {exc}")
            raise SystemExit(1)
        self.stdout.write(f"backup started ({reason})")
        deadline = time.monotonic() + max(60, options["timeout"])
        while time.monotonic() < deadline:
            state = storage_backup.JOB.status()
            if state.get("state") != "running":
                break
            time.sleep(2)
        if state.get("state") != "done":
            self.stderr.write(
                f"backup ended as '{state.get('state')}': {state.get('error') or 'no detail'}"
            )
            raise SystemExit(1)
        line = f"backup done: {state.get('file')} ({state.get('bytes')} bytes)"
        if state.get("media_synced_at"):
            line += (
                f", media mirror synced ({state.get('media_done_files')} files, "
                f"{state.get('media_done_bytes')} bytes)"
            )
        self.stdout.write(line)
        deleted = storage_backup.prune_old_backups()
        if deleted:
            self.stdout.write(f"retention: deleted {', '.join(deleted)}")
