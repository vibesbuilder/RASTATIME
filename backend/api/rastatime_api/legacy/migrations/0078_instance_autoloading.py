# pylint: disable=invalid-name
#
# RASTATIME 2026-11-03 - autoloading per episode (operator go 2026-11-03,
# rule "only before the fill"): "Edit Instance" may give one episode its
# own autoloading settings; the build (one hour before the start) resolves
# episode -> show.
#
#   cc_show_instances
#     + autoplaylist_override  BOOLEAN NOT NULL DEFAULT FALSE
#         TRUE = the columns below apply to this episode instead of the
#         show's settings
#     + autoplaylist_id        INTEGER NULL -> cc_playlist (SET NULL)
#         NULL = no autoloading playlist for this episode
#     + autoplaylist_repeat    BOOLEAN NOT NULL DEFAULT FALSE
#     + intro_playlist_id      INTEGER NULL -> cc_playlist (SET NULL)
#         NULL = the station default
#     + outro_playlist_id      INTEGER NULL -> cc_playlist (SET NULL)
#
# Propel is not regenerated: the legacy code reads the columns through
# to_jsonb(cc_show_instances) and writes them with raw SQL
# (AutoPlaylistManager), tolerating their absence until this ran.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show_instances ADD COLUMN autoplaylist_override BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE cc_show_instances ADD COLUMN autoplaylist_id INTEGER
    REFERENCES cc_playlist (id) ON DELETE SET NULL;
ALTER TABLE cc_show_instances ADD COLUMN autoplaylist_repeat BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE cc_show_instances ADD COLUMN intro_playlist_id INTEGER
    REFERENCES cc_playlist (id) ON DELETE SET NULL;
ALTER TABLE cc_show_instances ADD COLUMN outro_playlist_id INTEGER
    REFERENCES cc_playlist (id) ON DELETE SET NULL;
"""

DOWN = """
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS outro_playlist_id;
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS intro_playlist_id;
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS autoplaylist_repeat;
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS autoplaylist_id;
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS autoplaylist_override;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0077_show_own_production"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="78",
                sql=UP,
            )
        )
    ]
