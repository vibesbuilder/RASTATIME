# pylint: disable=invalid-name
#
# RASTATIME 2026-11-13 - loudness analysis per track type (operator wish):
# spoken spots over an always identical sound bed are levelled differently
# by the per-file loudness measurement (the speech differs, so the bed ends
# up louder or quieter from spot to spot).  A track type can switch the
# measurement off and name a fixed gain that applies instead.
#
#   cc_track_types.analyze_loudness  BOOLEAN NOT NULL DEFAULT TRUE
#       FALSE = the analyzer measures neither ReplayGain nor EBU R128 for
#       imports of this type, "Measure missing files" leaves its tracks
#       out, and the playout applies fixed_gain_db instead of the measured
#       adjustment - also for tracks of the type measured earlier
#   cc_track_types.fixed_gain_db     NUMERIC(5,2) NOT NULL DEFAULT 0
#       the gain in dB for tracks of such a type (-30 .. 30)
#
# Propel classes are NOT regenerated and the Django model does not carry
# the columns: every reader goes through to_jsonb(cc_track_types) (NULL
# until this migration ran), so the code may be live before the migration
# and the services may restart in any order.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_track_types ADD COLUMN analyze_loudness BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE cc_track_types ADD COLUMN fixed_gain_db NUMERIC(5,2) NOT NULL DEFAULT 0;
"""

DOWN = """
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS fixed_gain_db;
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS analyze_loudness;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0082_show_category"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="83",
                sql=UP,
            )
        )
    ]
