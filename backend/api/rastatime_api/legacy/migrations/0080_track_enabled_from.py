# pylint: disable=invalid-name
#
# RASTATIME 2026-11-08 - "Enabled From" and a stored "disabled by hand"
# (operator go 2026-11-08, option A, ARCHITECTURE 23.99).
#
#   cc_files
#     + disabled_by_hand  BOOLEAN NOT NULL DEFAULT FALSE
#                           the "Track disabled" box ticked by a person
#     + enabled_from      TIMESTAMP NULL
#                           the track stays disabled until this day (00:00)
#
# cc_files.disabled stays the column everything reads; from now on it is
# derived: disabled_by_hand OR expiry reached OR enabled_from still ahead
# (the hourly TrackExpiryTask recomputes it in both directions).  The
# backfill keeps today's state: a disabled track whose expiry has not
# been reached can only have been disabled by hand (23.98).  Propel is
# not regenerated: the legacy code uses raw SQL and tolerates the
# absence of the columns until this ran.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_files ADD COLUMN disabled_by_hand BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE cc_files ADD COLUMN enabled_from TIMESTAMP NULL DEFAULT NULL;
UPDATE cc_files SET disabled_by_hand = TRUE
 WHERE disabled AND NOT (expires_at IS NOT NULL AND expires_at <= NOW());
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS enabled_from;
ALTER TABLE cc_files DROP COLUMN IF EXISTS disabled_by_hand;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0079_webstream_bridge"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="80",
                sql=UP,
            )
        )
    ]
