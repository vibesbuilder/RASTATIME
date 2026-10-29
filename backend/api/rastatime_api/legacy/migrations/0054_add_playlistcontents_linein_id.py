# pylint: disable=invalid-name
#
# RASTATIME 2026-05-19 — add cc_playlistcontents.linein_id so a
# Playlist can include Line-In entries alongside Tracks (file_id),
# Webstreams (stream_id) and Smart Blocks (block_id).  Phase A had
# already added the same column to cc_schedule (migration 0047) so
# the Show timeline could carry line-ins; this extends the model so
# operators can also drop line-ins into Playlists in the Dashboard.
#
# A cc_playlistcontents row carries at most one of (file_id,
# stream_id, block_id, linein_id); the rendering / scheduler code
# selects the right branch via the `type` discriminator column:
#
#     type = 0  →  file_id      (audio clip)        — pre-existing
#     type = 1  →  stream_id    (webstream)         — pre-existing
#     type = 2  →  block_id     (smart block)       — pre-existing
#     type = 3  →  linein_id    (line-in)           — RASTATIME 2026-05-19
#
# Why no FOREIGN KEY constraint to rastatime_linein:
#   rastatime_linein is a Django-managed table (rastatime_api.linein
#   app), not a Propel-managed cc_* table.  Mixing FK ownership
#   across the two migration systems leads to drop-order problems on
#   schema reset and confuses Propel reverse-engineering tools.
#   This mirrors the same call made for cc_schedule.linein_id in
#   migration 0047.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_playlistcontents ADD COLUMN linein_id INTEGER DEFAULT NULL;
"""

DOWN = """
ALTER TABLE cc_playlistcontents DROP COLUMN IF EXISTS linein_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0053_add_show_template"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="54",
                sql=UP,
            )
        )
    ]
