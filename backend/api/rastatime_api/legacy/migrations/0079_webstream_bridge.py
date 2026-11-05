# pylint: disable=invalid-name
#
# RASTATIME 2026-11-05 - per-webstream clock-bridge buffer (operator go
# 2026-11-05 after the 07:00 BBC measurement, ARCHITECTURE 23.88).
#
#   cc_webstream
#     + bridge_seconds      NUMERIC NULL   buffer() fill before output
#     + bridge_max_seconds  NUMERIC NULL   buffer() max = fill level at
#                                         the gate = added delay
#
# NULL = the engine defaults (5 s / 10 s).  Propel is not regenerated:
# the legacy code reads and writes the columns with raw SQL and
# tolerates their absence until this ran.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_webstream ADD COLUMN bridge_seconds NUMERIC;
ALTER TABLE cc_webstream ADD COLUMN bridge_max_seconds NUMERIC;
"""

DOWN = """
ALTER TABLE cc_webstream DROP COLUMN IF EXISTS bridge_max_seconds;
ALTER TABLE cc_webstream DROP COLUMN IF EXISTS bridge_seconds;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0078_instance_autoloading"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="79",
                sql=UP,
            )
        )
    ]
