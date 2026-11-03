# pylint: disable=invalid-name
#
# RASTATIME 2026-11-03 - yearly report (operator go 2026-11-03): programme
# minutes of the station's own productions, for the reporting to the
# authorities.
#
#   cc_show.own_production  BOOLEAN NOT NULL DEFAULT FALSE
#       "Own production" checkbox of the show (Edit Show -> What); only the
#       aired instances of flagged shows count in Analytics -> Yearly Report
#       -> Programme minutes.  Repeats (cc_show.repeat_of_show_id) are shown
#       in a column of their own.
#
# Propel classes are NOT regenerated; the legacy frontend reads the column
# through to_jsonb(cc_show) ->> 'own_production' (NULL until this migration
# ran) and writes it with raw SQL (Application_Service_YearlyReportService).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show ADD COLUMN own_production BOOLEAN NOT NULL DEFAULT FALSE;
"""

DOWN = """
ALTER TABLE cc_show DROP COLUMN IF EXISTS own_production;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0076_cba_auto_archive"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="77",
                sql=UP,
            )
        )
    ]
