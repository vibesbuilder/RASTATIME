# pylint: disable=invalid-name
#
# RASTATIME 2026-10-14 - monthly repeats with a month selection (operator
# wish: "like the weekday boxes of a weekly repeat, but for months").
#
#   cc_show_days.month_mask  INTEGER NOT NULL DEFAULT 4095
#       bit (m - 1) set = the show repeats in month m (1 = January);
#       4095 = all twelve months = the behaviour before this column.
#
# Only monthly repeat rules (repeat_type 2 / 3) read it; the instance
# generator skips a month whose bit is clear, an edit removes the future
# instances of newly excluded months.  Propel classes are NOT regenerated;
# the legacy frontend reads and writes the column via raw SQL
# (ShowService / ShowFormService), the Django ShowDays model (managed =
# False) gets the matching field.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show_days ADD COLUMN month_mask INTEGER NOT NULL DEFAULT 4095;
"""

DOWN = """
ALTER TABLE cc_show_days DROP COLUMN IF EXISTS month_mask;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0066_add_file_source_md5"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="67",
                sql=UP,
            )
        )
    ]
