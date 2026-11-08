# pylint: disable=invalid-name
#
# RASTATIME 2026-11-08 - the country of a track (operator go 2026-11-08,
# ARCHITECTURE 23.100): read from the COUNTRY tag on import, editable in
# Edit Track, the base of Analytics -> Music by Country.
#
#   cc_files
#     + country  VARCHAR(64) NULL   free text as the tag says it
#                                   ("Austria", "USA", "Germany/Switzerland")
#
# Propel is not regenerated: the legacy code uses raw SQL and tolerates
# the absence of the column until this ran.  Existing tracks get their
# value once from the files (manage.py backfill_country, empty values only).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files ADD COLUMN country VARCHAR(64) NULL DEFAULT NULL;
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS country;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0080_track_enabled_from"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="81",
                sql=UP,
            )
        )
    ]
