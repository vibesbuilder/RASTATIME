# pylint: disable=invalid-name
#
# RASTATIME 2026-11-03 - archiving stage 3 (archive automatically, operator
# go 2026-11-03).
#
#   cc_show_archiving  + auto_archive   the per-show switch (off)
#                      + auto_since     when it was switched on (UTC, like
#                                       cc_show_instances.ends): only
#                                       episodes ending after that are
#                                       archived, nothing is caught up
#   cc_cba_upload      status + 'skipped': the automatic run gave up on an
#                      episode (data or recording still missing 24 hours
#                      after it was due), the reason in last_error
#   cc_pref cba_auto_delay_min  minutes between the end of an episode and
#                      its automatic upload (default 30, Settings -> CBA
#                      Accounts) - time to fill in the episode or tick
#                      "Do not archive automatically"

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show_archiving
    ADD COLUMN auto_archive BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN auto_since TIMESTAMP;
ALTER TABLE cc_cba_upload DROP CONSTRAINT IF EXISTS cc_cba_upload_status_check;
ALTER TABLE cc_cba_upload ADD CONSTRAINT cc_cba_upload_status_check
    CHECK (status IN ('queued', 'running', 'done', 'failed', 'unclear', 'cancelled', 'skipped'));
INSERT INTO cc_pref (keystr, valstr)
    SELECT 'cba_auto_delay_min', '30'
    WHERE NOT EXISTS (SELECT 1 FROM cc_pref WHERE keystr = 'cba_auto_delay_min' AND subjid IS NULL);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0075_cba_archiving"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="76",
                sql=UP,
            )
        )
    ]
