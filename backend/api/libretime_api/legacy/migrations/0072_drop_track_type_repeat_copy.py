# pylint: disable=invalid-name
#
# RASTATIME 2026-10-18 - "Copy into Repeats" removed again the same day
# (operator: not needed - a repeat carries the original's jingles too).
# Drops the per-track-type flag that 0071 added; the other 0071 columns
# ("Repeat of show") stay.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS repeat_copy;
"""

DOWN = """
ALTER TABLE cc_track_types ADD COLUMN repeat_copy BOOLEAN NOT NULL DEFAULT TRUE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0071_show_repeat_of"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="72",
                sql=UP,
            )
        )
    ]
