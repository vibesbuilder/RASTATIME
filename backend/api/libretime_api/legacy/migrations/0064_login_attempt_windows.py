# pylint: disable=invalid-name
#
# RASTATIME 2026-10-06 — brute-force protection for the public login.
#
#   cc_login_attempts.last_attempt  TIMESTAMP      (per source IP)
#   cc_subjs.login_attempt_at       TIMESTAMP      (per user name)
#
# LibreTime counted failed logins per IP and per user but never looked at
# the counters, and the per-IP INSERT wrote the literal ':ip'.  With the
# UI reachable from the internet (go-live 2026-10-06) the legacy login
# blocks an address after RASTATIME_LOGIN_IP_LIMIT failures inside
# RASTATIME_LOGIN_IP_WINDOW_MIN minutes for RASTATIME_LOGIN_IP_BLOCK_MIN
# minutes, and brakes a user name softly (constants.php).  Both need a
# time stamp next to the counter.  Propel classes are NOT regenerated; the
# legacy models use raw SQL.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_login_attempts ADD COLUMN last_attempt TIMESTAMP;
ALTER TABLE cc_subjs ADD COLUMN login_attempt_at TIMESTAMP;
"""

DOWN = """
ALTER TABLE cc_login_attempts DROP COLUMN IF EXISTS last_attempt;
ALTER TABLE cc_subjs DROP COLUMN IF EXISTS login_attempt_at;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0063_add_no_fade_per_track_type"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="64",
                sql=UP,
            )
        )
    ]
