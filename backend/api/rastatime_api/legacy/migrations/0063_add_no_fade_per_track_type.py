# pylint: disable=invalid-name
#
# RASTATIME 2026-09-30 — "No Fade during Crossover" as a track type preset.
#
#   cc_track_types.no_fade_crossfade  BOOLEAN NOT NULL DEFAULT false
#       Every track of this type that is set to "As the track type" keeps
#       its full level while a neighbour fades (the overlap stays as the
#       type's crossfade says).  The per-track field of the track editor
#       still wins: "No Fade during Crossover" forces it on, "Exclude from
#       Crossover" leaves no overlap to fade in.  The effective flag is
#       resolved by the playout from the file plus the serializer's
#       read-only track_type_no_fade (no schedule re-layout: the overlap
#       does not change).
#
# Propel classes are NOT regenerated; the legacy frontend reads and writes
# the column via raw SQL.  The Django model (managed = False) gets the
# matching field so the playout sees the value through the API.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_track_types ADD COLUMN no_fade_crossfade BOOLEAN DEFAULT false NOT NULL;
"""

DOWN = """
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS no_fade_crossfade;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0062_add_crossfade_per_track_type"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="63",
                sql=UP,
            )
        )
    ]
