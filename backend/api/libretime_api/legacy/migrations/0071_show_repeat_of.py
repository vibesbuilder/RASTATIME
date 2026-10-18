# pylint: disable=invalid-name
#
# RASTATIME 2026-10-18 - "Repeat of show" (operator go 2026-10-18): a show B
# that repeats a show A gets the content of A's last aired instance copied
# in shortly before B starts (legacy Application_Service_RepeatFillService,
# RepeatFillTask).
#
#   cc_show.repeat_of_show_id                INTEGER NULL -> cc_show(id)
#       the source show; chains are allowed, loops refused by the form;
#       ON DELETE SET NULL - deleting A turns B into a plain show
#   cc_track_types.repeat_copy               BOOLEAN NOT NULL DEFAULT TRUE
#       FALSE = tracks of this type (jingles, teasers) stay out of the copy
#       so the repeat gets its own, fitting ones from its autoloading
#   cc_show_instances.filled_from_instance_id INTEGER NULL -> cc_show_instances(id)
#       the source instance once the copy ran (View Show dialog shows
#       "Repeat of show A from ..."); NULL = not filled yet
#   cc_show_instances.repeat_skipped         SMALLINT NOT NULL DEFAULT 0
#       rows of the source left out because their file is missing
#
# Propel classes are NOT regenerated; the legacy frontend reads and writes
# the columns via raw SQL and tolerates their absence until this migration
# ran.  The Django models (managed = False) get the fields.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show ADD COLUMN repeat_of_show_id INTEGER
    REFERENCES cc_show (id) ON DELETE SET NULL;
CREATE INDEX cc_show_repeat_of_idx ON cc_show (repeat_of_show_id);
ALTER TABLE cc_track_types ADD COLUMN repeat_copy BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE cc_show_instances ADD COLUMN filled_from_instance_id INTEGER
    REFERENCES cc_show_instances (id) ON DELETE SET NULL;
ALTER TABLE cc_show_instances ADD COLUMN repeat_skipped SMALLINT NOT NULL DEFAULT 0;
"""

DOWN = """
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS repeat_skipped;
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS filled_from_instance_id;
ALTER TABLE cc_track_types DROP COLUMN IF EXISTS repeat_copy;
DROP INDEX IF EXISTS cc_show_repeat_of_idx;
ALTER TABLE cc_show DROP COLUMN IF EXISTS repeat_of_show_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0070_file_teaser_shows"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="71",
                sql=UP,
            )
        )
    ]
