# pylint: disable=invalid-name
#
# RASTATIME 2026-05-16 - add cc_webstream.input_gain_db so the operator
# can apply a per-webstream static dB offset (analogous to the existing
# cc_files.replay_gain pipeline).  Default 0 = no change to behaviour.
#
# The FFmpeg streamer emits the value as a `-af volume=<dB>dB` audio
# filter when starting the encoder against the webstream URL; see
# ARCHITECTURE Section 23.10.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_webstream ADD COLUMN input_gain_db NUMERIC DEFAULT 0;
"""

DOWN = """
ALTER TABLE cc_webstream DROP COLUMN IF EXISTS input_gain_db;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0047_add_cc_schedule_linein_id"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="48",
                sql=UP,
            )
        )
    ]
