# pylint: disable=invalid-name
#
# RASTATIME 2026-09-29 — crossfade per track type + "Exclude from Crossover".
#
#   cc_track_types.crossfade_duration  NUMERIC(5,2) NULL
#       Seconds two neighbouring tracks of this type overlap and fade.
#       NULL = the house value (Settings → General, Default Track Crossfade
#       Duration).  Between two tracks the SMALLER of the two values
#       applies, so a type with 0 always butts against its neighbours.
#       The stock "Jingles" type (code jngl) starts with 0: short, exactly
#       timed elements must not be shortened by a music-length crossfade
#       (2026-09-29: the hourly jingle block ran 5 s ahead of its rows and
#       left silence before the news relay).
#
#   cc_files.exclude_crossfade  BOOLEAN NOT NULL DEFAULT false
#       Per-track exception: the track never overlaps a neighbour,
#       whatever its type says.  Mutually exclusive with
#       no_fade_crossfade (the track editor offers one three-way field).
#
# Propel classes are NOT regenerated; the legacy frontend reads and writes
# both columns via raw SQL.  The Django models (managed = False) get
# matching fields so the playout sees the values through the API.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_track_types ADD COLUMN crossfade_duration NUMERIC(5,2);
ALTER TABLE cc_files ADD COLUMN exclude_crossfade BOOLEAN DEFAULT false NOT NULL;
UPDATE cc_track_types SET crossfade_duration = 0 WHERE lower(code) = 'jngl';
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS exclude_crossfade;
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS crossfade_duration;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0061_add_file_loudness"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="62",
                sql=UP,
            )
        )
    ]
