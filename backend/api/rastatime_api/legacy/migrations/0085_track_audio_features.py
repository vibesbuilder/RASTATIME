# pylint: disable=invalid-name
#
# RASTATIME 2026-11-14 - energy and brightness of a track, stage 1
# (operator go 2026-11-14, ARCHITECTURE 23.115): measured with ffmpeg by
# manage.py analyze_audio_features (Windows task RASTATIME-AudioFeatures),
# shown in the library and Edit Track, smart block criteria.
#
#   cc_files
#     + energy          SMALLINT NULL  1 (calm) .. 10 (very energetic)
#     + brightness      SMALLINT NULL  1 (dark) .. 10 (bright)
#     + audio_features  JSONB NULL     raw values, score and the levels the
#                                      measurement produced (a level that
#                                      differs from them was set by hand);
#                                      NULL = not measured yet
#
# Nullable without a default: no table rewrite.  Propel is not regenerated
# (the legacy code reads and writes the columns with raw SQL and tolerates
# their absence until this ran).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files
    ADD COLUMN energy SMALLINT NULL DEFAULT NULL,
    ADD COLUMN brightness SMALLINT NULL DEFAULT NULL,
    ADD COLUMN audio_features JSONB NULL DEFAULT NULL,
    ADD CONSTRAINT cc_files_energy_range CHECK (energy BETWEEN 1 AND 10),
    ADD CONSTRAINT cc_files_brightness_range CHECK (brightness BETWEEN 1 AND 10);
"""

DOWN = """
ALTER TABLE cc_files
    DROP CONSTRAINT IF EXISTS cc_files_brightness_range,
    DROP CONSTRAINT IF EXISTS cc_files_energy_range,
    DROP COLUMN IF EXISTS audio_features,
    DROP COLUMN IF EXISTS brightness,
    DROP COLUMN IF EXISTS energy;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0084_podcast_episode_published_until"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="85",
                sql=UP,
            )
        )
    ]
