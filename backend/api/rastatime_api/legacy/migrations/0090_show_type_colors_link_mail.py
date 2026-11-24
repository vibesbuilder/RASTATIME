# pylint: disable=invalid-name
#
# RASTATIME 2026-11-24 - two operator wishes in one migration (operator Go
# 2026-11-24, ARCHITECTURE 23.134 and 23.135):
#
#   cc_show_types
#     + background_color, color  VARCHAR(6) NULL  (hex without "#", like
#       cc_show.background_color / cc_show.color): choosing the type in the
#       show form fills the show's colours; Settings -> Show Types can apply
#       them to every show of the type.  Empty = the type has no colours.
#   cc_cba_upload
#     + link_mail_at    TIMESTAMPTZ NULL
#     + link_mail_note  TEXT NULL
#       after a finished upload the background service e-mails the link of
#       the new post to the producers of the show (Settings -> Archiving ->
#       "Link by e-mail"); the job keeps when and to whom, or why not.
#
# The readers check the columns first (information_schema / to_jsonb), so
# code and migration may come in any order.  Propel is not regenerated.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show_types
    ADD COLUMN background_color VARCHAR(6) NULL,
    ADD COLUMN color VARCHAR(6) NULL;
ALTER TABLE cc_cba_upload
    ADD COLUMN link_mail_at TIMESTAMPTZ NULL,
    ADD COLUMN link_mail_note TEXT NULL;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0089_show_host_names"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="90",
                sql=UP,
            )
        )
    ]
