# pylint: disable=invalid-name
#
# RASTATIME 2026-09-27 — Show-Shift: own marker for shifted instances.
#
# Adds one column to cc_show_instances:
#
#   cc_show_instances.delayed_start_from  TIMESTAMP NULL
#       NULL for every ordinary instance.  Set by ShowShiftService when a
#       delayed start moved the instance (value = the slot start it was
#       moved away from) or cleared it.  It replaces the June design, which
#       marked shifted instances with modified_instance = true — upstream's
#       "this occurrence was deleted" flag.  That hid every shifted show
#       from the dashboard, live-info, the widgets, the calendar, the show
#       builder and the overlap check while the playout still played it
#       (found in the 2026-09-27 live rehearsal).
#
#       Keeping the ORIGINAL slot start (not just a boolean) lets the
#       repeat regenerator (ShowService::getInstance) still find the moved
#       occurrence when the show is edited, instead of creating a duplicate
#       at the series time.
#
# Propel classes are NOT regenerated for this column; the legacy frontend
# reads/writes it via raw SQL — same precedent as cc_show.allow_delayed_start
# (migration 0056) and cc_show_instances.autoplaylist_cursor (0057).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_show_instances
    ADD COLUMN delayed_start_from TIMESTAMP NULL;
"""

DOWN = """
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS delayed_start_from;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0057_add_instance_autoplaylist_cursor"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="58",
                sql=UP,
            )
        )
    ]
