# pylint: disable=invalid-name
#
# RASTATIME 2026-10-14 - stream metadata per file and per track type
# (operator wish): whether a track's artist / title reach the listeners'
# players (ICY) and the Live Text Info.
#
#   cc_track_types.icy_forward  BOOLEAN NOT NULL DEFAULT TRUE
#       the type's preset: FALSE = tracks of this type (jingles, station
#       IDs, promos) show "Station name - Show name" instead
#   cc_files.icy_forward        SMALLINT NULL
#       the track's own choice: NULL = as the track type, 1 = forward,
#       0 = do not forward
#
# The playout resolves the effective flag (file wins, else the type) and
# sends the metadata packet without artist / title but with icy_hide=true;
# the Liquidsoap label builder shows "Station name - Show name" for such
# a packet in every format.  Propel classes are NOT regenerated; the legacy
# frontend reads and writes both columns via raw SQL (StoredFile,
# Tracktype), the Django models (managed = False) get the fields.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_track_types ADD COLUMN icy_forward BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE cc_files ADD COLUMN icy_forward SMALLINT;
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS icy_forward;
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS icy_forward;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0067_show_days_month_mask"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="68",
                sql=UP,
            )
        )
    ]
