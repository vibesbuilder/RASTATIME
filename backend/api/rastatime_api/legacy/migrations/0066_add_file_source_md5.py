# pylint: disable=invalid-name
#
# RASTATIME 2026-10-14 - lossless audio is converted to MP3 320 kbps on
# import (Settings -> Local Machine, preference convert_lossless_to_mp3).
#
#   cc_files.source_md5  VARCHAR(32)  md5 of the file as it was handed over
#                                     (the WAV / FLAC original), indexed
#
# After a conversion cc_files.md5 is the md5 of the stored MP3, so the
# duplicate check of a later import (bulk_import, the analyzer) would no
# longer recognise the same original.  The analyzer reports the original's
# md5 as source_md5; a file counts as already imported when its md5 matches
# cc_files.md5 OR cc_files.source_md5.  The management command
# convert_lossless (files already in the library) keeps the old md5 here
# too.  NULL = the stored file is the original.
#
# Propel classes are NOT regenerated; the legacy frontend writes the
# column via raw SQL in CcFiles::updateFromArray (same precedent as the
# loudness columns, 0061).  The Django File model (managed = False) gets
# the matching field.

from django.db import migrations

from ._migrations import legacy_migration_factory

# The ALTER needs an exclusive lock on cc_files.  Behind a long transaction
# (e.g. the 03:30 backup dump) it would wait - and every cc_files read of
# the playout would queue behind it.  SET LOCAL (this migration's
# transaction only): give up after 5 s instead; run migrate again later.
UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files ADD COLUMN source_md5 VARCHAR(32);
CREATE INDEX cc_files_source_md5_idx ON cc_files (source_md5);
"""

DOWN = """
DROP INDEX IF EXISTS cc_files_source_md5_idx;
ALTER TABLE cc_files DROP COLUMN IF EXISTS source_md5;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0065_playout_history_keeps_deleted_files"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="66",
                sql=UP,
            )
        )
    ]
