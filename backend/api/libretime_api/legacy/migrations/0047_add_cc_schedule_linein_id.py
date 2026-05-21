# pylint: disable=invalid-name
#
# RASTATIME 2026-05-12 — add cc_schedule.linein_id for the Line-In
# Library feature (Phase A).
#
# A schedule row carries at most one of (file_id, stream_id, linein_id);
# the playout picks the right event subclass based on which is set.
#
# Why no FOREIGN KEY constraint to rastatime_linein:
#   rastatime_linein is a Django-managed table (libretime_api.linein
#   app), not a Propel-managed cc_* table.  Mixing FK ownership across
#   the two migration systems leads to drop-order problems on schema
#   reset and confuses Propel reverse-engineering tools.  The Django
#   side's Schedule.linein FK gives us referential integrity at the
#   ORM layer where it matters; the SQL column is plain NULL-able int.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_schedule ADD COLUMN linein_id INTEGER DEFAULT NULL;
"""

DOWN = """
ALTER TABLE cc_schedule DROP COLUMN IF EXISTS linein_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0046_add_override_intro_outro_playlists"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="47",
                sql=UP,
            )
        )
    ]
