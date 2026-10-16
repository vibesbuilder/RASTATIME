# pylint: disable=invalid-name
#
# RASTATIME 2026-10-16 - teaser automation: a jingle may announce SEVERAL
# shows (operator at the acceptance of 0069: the hourly "bbc" slots are
# separate shows and share one "BBC today" jingle).  The single column
# cc_files.teaser_show_id becomes the link table cc_file_teaser; the
# teaser type stays on cc_files (one jingle, one wording).
#
#   cc_file_teaser (file_id -> cc_files ON DELETE CASCADE,
#                   show_id -> cc_show  ON DELETE CASCADE,
#                   PRIMARY KEY (file_id, show_id))
#
# Existing links are carried over before the column is dropped.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
CREATE TABLE cc_file_teaser (
    file_id INTEGER NOT NULL REFERENCES cc_files(id) ON DELETE CASCADE,
    show_id INTEGER NOT NULL REFERENCES cc_show(id) ON DELETE CASCADE,
    PRIMARY KEY (file_id, show_id)
);
CREATE INDEX cc_file_teaser_show_idx ON cc_file_teaser (show_id);
INSERT INTO cc_file_teaser (file_id, show_id)
    SELECT id, teaser_show_id FROM cc_files WHERE teaser_show_id IS NOT NULL;
DROP INDEX IF EXISTS cc_files_teaser_show_idx;
ALTER TABLE cc_files DROP COLUMN teaser_show_id;
"""

DOWN = """
ALTER TABLE cc_files ADD COLUMN teaser_show_id INTEGER REFERENCES cc_show(id) ON DELETE SET NULL;
UPDATE cc_files f SET teaser_show_id = (SELECT MIN(show_id) FROM cc_file_teaser t WHERE t.file_id = f.id);
DROP TABLE IF EXISTS cc_file_teaser;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0069_file_teaser"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="70",
                sql=UP,
            )
        )
    ]
