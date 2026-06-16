# pylint: disable=invalid-name
#
# RASTATIME 2026-06-16 — Mid-Show Song Requests (incremental fill), Phase R1.
#
# Adds one column to cc_show_instances:
#
#   cc_show_instances.autoplaylist_cursor  SMALLINT DEFAULT 0
#       The next UNRESOLVED dramaturgy position for a request show's
#       incremental fill.  The request-fill task
#       (AutoPlaylistManager::_fillRequestShowByPositions) no longer
#       resolves the whole autoload playlist in one pass; it resolves
#       positions progressively, a little ahead of the play head, so a
#       "use requests" block placed later in the dramaturgy draws the
#       requests that arrived WHILE the show was already on air.  The
#       cursor persists "how far the dramaturgy has been resolved" across
#       the 2-minute poll cycles so the next poll continues instead of
#       re-filling from position 0 (which would double the dramaturgy).
#
#       0 = nothing resolved yet (fresh instance).  When the cursor
#       reaches the dramaturgy length the dramaturgy is done and the
#       trailing time-remaining block tops up the rest.
#
# Propel classes are NOT regenerated for this column; the legacy frontend
# reads/writes it via raw SQL — same precedent as cc_show.allow_delayed_start
# (migration 0056) and the cc_files request columns (0055).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_show_instances
    ADD COLUMN autoplaylist_cursor SMALLINT DEFAULT 0 NOT NULL;
"""

DOWN = """
ALTER TABLE cc_show_instances DROP COLUMN IF EXISTS autoplaylist_cursor;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0056_add_show_allow_delayed_start"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="57",
                sql=UP,
            )
        )
    ]
