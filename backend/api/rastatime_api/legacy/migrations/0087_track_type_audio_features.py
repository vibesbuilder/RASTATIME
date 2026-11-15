# pylint: disable=invalid-name
#
# RASTATIME 2026-11-15 - audio features per track type (operator wish
# 2026-11-15: tempo, key, brightness and energy are only wanted for music,
# ARCHITECTURE 23.117).  A track type decides whether
# manage.py analyze_audio_features measures its tracks.
#
#   cc_track_types
#     + analyze_audio_features  BOOLEAN NOT NULL DEFAULT FALSE
#         TRUE = tracks of the type get energy / brightness and tempo / key;
#         set for the stock type with the code 'music' only.  Tracks without
#         a type are never measured.
#
# Before this ran, the readers fall back to "code = 'music'" (they go
# through to_jsonb(cc_track_types), NULL while the column is missing), so
# code and migration may come in any order.  Propel is not regenerated.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_track_types ADD COLUMN analyze_audio_features BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE cc_track_types SET analyze_audio_features = TRUE WHERE code = 'music';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0086_track_musical_key"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="87",
                sql=UP,
            )
        )
    ]
