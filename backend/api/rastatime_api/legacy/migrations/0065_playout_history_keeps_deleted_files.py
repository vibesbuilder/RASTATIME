# pylint: disable=invalid-name
#
# RASTATIME 2026-10-08 — the playout history survives the deletion of a
# track (operator decision: deleting a track, a webstream or a line-in must
# never touch the history).
#
# LibreTime declared cc_playout_history.file_id ON DELETE CASCADE, so
# deleting a file from the library silently deleted every history row of
# that file - and the rows carried nothing but the show name, the report
# read title, artist, length, composer and copyright live from cc_files.
#
#   1. the foreign key becomes ON DELETE SET NULL: the row stays, the file
#      reference is cleared and the report renders the row like a webstream
#      row - from cc_playout_history_metadata;
#   2. the file fields the two default templates show (track_title,
#      artist_name, length, composer, copyright) are copied into the
#      metadata of every existing file row that does not have them yet.
#      HistoryService::insertPlayedItem writes them for every new row.
#
# Propel classes are NOT regenerated; the legacy service uses the ORM
# metadata objects it already had.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_playout_history DROP CONSTRAINT IF EXISTS cc_playout_history_file_tag_fkey;
ALTER TABLE cc_playout_history
    ADD CONSTRAINT cc_playout_history_file_tag_fkey
    FOREIGN KEY (file_id) REFERENCES cc_files (id) ON DELETE SET NULL;

INSERT INTO cc_playout_history_metadata (history_id, key, value)
SELECT h.id, k.key, left(k.value, 128)
  FROM cc_playout_history h
  JOIN cc_files f ON f.id = h.file_id
  CROSS JOIN LATERAL (VALUES
      ('track_title', f.track_title),
      ('artist_name', f.artist_name),
      ('length', f.length::text),
      ('composer', f.composer),
      ('copyright', f.copyright)
  ) AS k(key, value)
 WHERE k.value IS NOT NULL AND k.value <> ''
   AND NOT EXISTS (
       SELECT 1 FROM cc_playout_history_metadata m
        WHERE m.history_id = h.id AND m.key = k.key);
"""

DOWN = """
ALTER TABLE cc_playout_history DROP CONSTRAINT IF EXISTS cc_playout_history_file_tag_fkey;
ALTER TABLE cc_playout_history
    ADD CONSTRAINT cc_playout_history_file_tag_fkey
    FOREIGN KEY (file_id) REFERENCES cc_files (id) ON DELETE CASCADE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0064_login_attempt_windows"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="65",
                sql=UP,
            )
        )
    ]
