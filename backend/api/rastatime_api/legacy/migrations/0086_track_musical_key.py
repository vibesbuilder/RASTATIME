# pylint: disable=invalid-name
#
# RASTATIME 2026-11-15 - tempo and key of a track, stage 2 of the audio
# features (operator go 2026-11-14, ARCHITECTURE 23.116): measured with
# librosa in its own environment (backend/features/tempo_key.py) by
# manage.py analyze_audio_features (Windows task RASTATIME-AudioFeatures).
# The tempo goes into the existing cc_files.bpm; the key needs a column.
#
#   cc_files
#     + musical_key  VARCHAR(3) NULL  Camelot code: 1A..12A minor, 1B..12B
#                                     major (8A = A minor, 8B = C major);
#                                     the UI shows "8A · Am"
#
# The measurement itself sits in audio_features->'tk' (migration 0085); a
# key or BPM that differs from it was set by hand and is never replaced.
# Nullable without a default: no table rewrite.  Propel is not regenerated
# (the legacy code reads and writes the column with raw SQL and tolerates
# its absence until this ran).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files
    ADD COLUMN musical_key VARCHAR(3) NULL DEFAULT NULL,
    ADD CONSTRAINT cc_files_musical_key_camelot CHECK (musical_key ~ '^(1[0-2]|[1-9])[AB]$');
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0085_track_audio_features"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="86",
                sql=UP,
            )
        )
    ]
