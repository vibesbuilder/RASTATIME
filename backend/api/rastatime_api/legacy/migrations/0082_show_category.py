# pylint: disable=invalid-name
#
# RASTATIME 2026-11-10 - show category (operator 2026-11-10): a free-text
# field next to the genre (Edit Show -> What, with suggestions from the
# values in use); Analytics -> Programme Minutes evaluates and exports the
# minutes per genre, per category and per genre x category.
#
#   cc_show.category  VARCHAR(255) NULL
#
# Propel classes are NOT regenerated; the legacy frontend reads the column
# through to_jsonb(cc_show) ->> 'category' (NULL until this migration ran)
# and writes it with raw SQL (Application_Service_YearlyReportService).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show ADD COLUMN category VARCHAR(255) NULL DEFAULT NULL;
"""

DOWN = """
ALTER TABLE cc_show DROP COLUMN IF EXISTS category;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0081_track_country"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="82",
                sql=UP,
            )
        )
    ]
