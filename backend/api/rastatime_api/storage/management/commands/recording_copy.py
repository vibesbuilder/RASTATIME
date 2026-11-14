"""
RASTATIME 2026-11-14 - copy finished show recordings to the folder set under
Settings -> Local Machine -> Show Recording -> "Copy finished recordings to".

Fired every two minutes by the Windows task RASTATIME-RecordingCopy (see
``scripts/recording-copy.ps1`` and
``infra/scripts/register-recording-copy.ps1``).  Prints one line per copied
file and per error, nothing on an idle run.

Exit codes: 0 = switched off, nothing to do or copied; 1 = the run reported
an error (target not reachable, a copy failed).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from ... import recording_copy


class Command(BaseCommand):
    help = "Copy finished show recordings to the configured second folder (once each)."

    def handle(self, *args, **options):
        state = recording_copy.run_from_settings(log=self.stdout.write)
        if state is None:
            return
        if state.get("ok") is False:
            raise SystemExit(1)
