# pylint: disable=invalid-name
#
# RASTATIME 2026-10-25 - retire the Airtime "Super Admin" role (operator go,
# option B).  The installation creates "admin" as an Admin, the interface
# cannot create a Super Admin and the API v2 never knew the role; an old
# Airtime database could still bring one, which becomes an Admin here.
#
# The first-run language / time zone dialog was shown to Super Admins only
# (so never); it now goes to Admins.  A station that is already in use
# (tracks or shows exist) is marked as set up, so the dialog does not pop
# up there; a fresh installation still gets it at the first Admin login.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
UPDATE cc_subjs SET type = 'A' WHERE type = 'S';
INSERT INTO cc_pref (keystr, valstr)
SELECT 'lang_tz_setup_complete', '1'
WHERE NOT EXISTS (
        SELECT 1 FROM cc_pref WHERE keystr = 'lang_tz_setup_complete' AND subjid IS NULL
    )
    AND (EXISTS (SELECT 1 FROM cc_files) OR EXISTS (SELECT 1 FROM cc_show));
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0072_drop_track_type_repeat_copy"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="73",
                sql=UP,
            )
        )
    ]
