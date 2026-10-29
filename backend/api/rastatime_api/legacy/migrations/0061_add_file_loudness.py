# pylint: disable=invalid-name
#
# RASTATIME 2026-09-28 — EBU R128 loudness measurement per file (stage 1).
#
#   cc_files.loudness_lufs      NUMERIC(6,2)  integrated loudness (ITU BS.1770 / EBU R128)
#   cc_files.true_peak_dbtp     NUMERIC(6,2)  true peak of the file
#   cc_files.loudness_range_lu  NUMERIC(6,2)  loudness range (LRA)
#
# Measured by the analyzer with ffmpeg's ebur128 filter at import (and by
# the "Measure loudness now" job for the existing library).  The playout
# turns "target − loudness" into the per-track gain when Settings →
# Streams → Loudness Normalization is set to EBU R128; replay_gain (the
# ReplayGain 1.0 value) stays for the ReplayGain mode.  NULL = not measured.
#
# Propel classes are NOT regenerated; the legacy frontend writes the
# columns via raw SQL in CcFiles::updateFromArray (same precedent as
# expires_at, 0049, and no_fade_crossfade, 0059/0060).  The Django File
# model (managed = False) gets matching fields so the playout sees the
# values through the API.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_files ADD COLUMN loudness_lufs NUMERIC(6,2);
ALTER TABLE cc_files ADD COLUMN true_peak_dbtp NUMERIC(6,2);
ALTER TABLE cc_files ADD COLUMN loudness_range_lu NUMERIC(6,2);
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS loudness_range_lu;
ALTER TABLE cc_files DROP COLUMN IF EXISTS true_peak_dbtp;
ALTER TABLE cc_files DROP COLUMN IF EXISTS loudness_lufs;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0060_rename_file_no_fade_crossfade"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="61",
                sql=UP,
            )
        )
    ]
