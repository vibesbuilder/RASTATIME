# pylint: disable=invalid-name
#
# RASTATIME 2026-09-27 — per-track "Exclude from Crossover".
#
#   cc_files.exclude_crossfade  BOOLEAN NOT NULL DEFAULT false
#       Set from the track metadata editor.  A track with the flag is never
#       faded: it plays to its end and the next track follows without
#       overlap (the scheduler lays the neighbouring rows out without the
#       crossfade offset, the playout tells Liquidsoap to use the "cut"
#       shape).  Replaces the never-active 8-second rule of May 2026.
#
# Propel classes are NOT regenerated; the legacy frontend reads and writes
# the column via raw SQL (same precedent as cc_files.expires_at, 0049, and
# cc_files.requestable, 0055).  The Django File model (managed = False)
# gets a matching field so the playout sees the flag through the API.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_files ADD COLUMN exclude_crossfade BOOLEAN DEFAULT false NOT NULL;
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS exclude_crossfade;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0058_add_instance_delayed_start_from"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="59",
                sql=UP,
            )
        )
    ]
