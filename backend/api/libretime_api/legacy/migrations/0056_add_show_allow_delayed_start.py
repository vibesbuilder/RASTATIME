# pylint: disable=invalid-name
#
# RASTATIME 2026-06-09 — Show-Shift / "Allow delayed start", Phase 1.
#
# Adds one column to cc_show:
#
#   cc_show.allow_delayed_start  BOOLEAN DEFAULT false
#       When TRUE, an instance of this show may start LATER than its
#       calendar slot when the preceding show overran.  A background
#       ShowShiftTask pushes this show's start (and its scheduled items)
#       back by the overrun while keeping the show's END fixed — the last
#       track is then clamped at the slot end by the existing overbook
#       logic (an accepted trade-off).  The shift cascades across
#       consecutive allow_delayed_start shows until the first show WITHOUT
#       the flag, which acts as the hard anchor.
#
# Propel classes are NOT regenerated for this column; the legacy frontend
# reads/writes it via raw SQL — same precedent as cc_files.requested /
# requestable (migration 0055) and cc_files.expires_at / disabled (0049).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_show
    ADD COLUMN allow_delayed_start BOOLEAN DEFAULT false NOT NULL;
"""

DOWN = """
ALTER TABLE cc_show DROP COLUMN IF EXISTS allow_delayed_start;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0055_add_song_request_columns"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="56",
                sql=UP,
            )
        )
    ]
