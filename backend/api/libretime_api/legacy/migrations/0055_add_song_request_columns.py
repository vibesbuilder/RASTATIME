# pylint: disable=invalid-name
#
# RASTATIME 2026-06-07 — Song Requests, Phase 1 (data foundation).
#
# Adds four columns to cc_files that act as a denormalised per-track
# aggregate cache for the song-request feature.  The authoritative
# per-request log lives in the Django-managed rastatime_song_request
# table (libretime_api.song_request app); these columns are derived
# from it so smart blocks can filter/sort on them cheaply via raw SQL
# (same pattern as cc_files.expires_at / disabled — migration 0049):
#
#   cc_files.requested      BOOLEAN DEFAULT false
#       TRUE while the track has one or more open (pending/queued)
#       requests.  The "use requests" smart-block option filters on
#       this (Phase 2).  Reset to FALSE when the track airs or all its
#       open requests expire (Phase 6).
#
#   cc_files.requested_at   TIMESTAMP NULL
#       Timestamp of the most recent request for this track.  Drives
#       the "Oldest request first" smart-block sort and the expiry
#       window.  NULL = no open request.
#
#   cc_files.request_count  INTEGER DEFAULT 0
#       Number of open requests for this track (the "votes" count).
#       Drives the "Most requested first" smart-block sort.
#
#   cc_files.requestable    BOOLEAN DEFAULT false
#       TRUE if the track is in the operator-defined "Requestable Pool"
#       (a smart block whose members a sync task flags here — Phase 3).
#       The public catalog-search endpoint only returns requestable
#       tracks.  Same flag-maintained-by-a-task pattern as `disabled`.
#
# Propel classes are NOT regenerated for these columns; the legacy
# frontend reads/writes them via raw SQL (see the expires_at / disabled
# precedent in Application_Model_Block and StoredFile).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_files ADD COLUMN requested BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE cc_files ADD COLUMN requested_at TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE cc_files ADD COLUMN request_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE cc_files ADD COLUMN requestable BOOLEAN DEFAULT false NOT NULL;
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS requested;
ALTER TABLE cc_files DROP COLUMN IF EXISTS requested_at;
ALTER TABLE cc_files DROP COLUMN IF EXISTS request_count;
ALTER TABLE cc_files DROP COLUMN IF EXISTS requestable;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0054_add_playlistcontents_linein_id"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="55",
                sql=UP,
            )
        )
    ]
