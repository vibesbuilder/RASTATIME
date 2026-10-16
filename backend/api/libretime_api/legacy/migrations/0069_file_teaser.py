# pylint: disable=invalid-name
#
# RASTATIME 2026-10-16 - teaser automation (operator wish): a jingle is
# linked to the show it announces, and a smart block criterion picks the
# jingles that fit the day of the show being filled.
#
#   cc_files.teaser_show_id  INTEGER NULL -> cc_show(id) ON DELETE SET NULL
#       the show this jingle teases
#   cc_files.teaser_type     VARCHAR(16) NULL
#       'show' (any day), 'today' ("the show airs today"),
#       'tomorrow' ("the show airs tomorrow")
#
# cc_schedule (file_id, starts) gets an index: the smart block filter
# "exclude tracks played lately" now also looks at PLANNED rows inside its
# window, per candidate file.
#
# Propel classes are NOT regenerated; the legacy frontend reads and writes
# the columns via raw SQL (StoredFile, Block), the Django model
# (managed = False) gets the fields.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files ADD COLUMN teaser_show_id INTEGER REFERENCES cc_show(id) ON DELETE SET NULL;
ALTER TABLE cc_files ADD COLUMN teaser_type VARCHAR(16);
CREATE INDEX cc_files_teaser_show_idx ON cc_files (teaser_show_id) WHERE teaser_show_id IS NOT NULL;
CREATE INDEX cc_schedule_file_id_starts_idx ON cc_schedule (file_id, starts);
"""

DOWN = """
DROP INDEX IF EXISTS cc_schedule_file_id_starts_idx;
DROP INDEX IF EXISTS cc_files_teaser_show_idx;
ALTER TABLE cc_files DROP COLUMN IF EXISTS teaser_type;
ALTER TABLE cc_files DROP COLUMN IF EXISTS teaser_show_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0068_icy_forward"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="69",
                sql=UP,
            )
        )
    ]
