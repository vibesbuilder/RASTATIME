# pylint: disable=invalid-name
#
# RASTATIME 2026-09-27 — "Exclude from Crossover" became "No Fade during
# Crossover" the same day (operator decision): the flagged track keeps the
# crossfade overlap but is not faded itself - it stays at full level while
# the other track fades.  The column follows the meaning.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_files RENAME COLUMN exclude_crossfade TO no_fade_crossfade;
"""

DOWN = """
ALTER TABLE cc_files RENAME COLUMN no_fade_crossfade TO exclude_crossfade;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0059_add_file_exclude_crossfade"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="60",
                sql=UP,
            )
        )
    ]
