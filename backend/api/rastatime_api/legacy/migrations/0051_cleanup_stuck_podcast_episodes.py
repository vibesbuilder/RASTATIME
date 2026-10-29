# pylint: disable=invalid-name
#
# RASTATIME 2026-05-17 - One-shot cleanup of podcast episodes that are
# stuck on the "downloading" spinner forever.
#
# Background: every podcast_episodes row that was created by
# addPlaceholder() but whose subsequent _download() call failed (HTTP
# error from the Django API, network glitch, etc.) was left in the DB
# with file_id IS NULL.  The UI's _getImportedPodcastEpisodeArray()
# reports such rows as ingested=-1 (pending), which renders as a
# spinning loading-icon.  The operator's only recourse was to delete
# the rows by hand.
#
# The forward-going fix (CHANGELOG 2026-05-17, PodcastEpisodeService::
# _download) now removes the stuck row when the API call fails.  This
# migration cleans up the rows that accumulated BEFORE that fix went
# in, so the operator's library does not stay polluted with
# permanently-spinning ghosts.
#
# Safety: only deletes rows where file_id IS NULL.  Successfully
# imported episodes (file_id IS NOT NULL) are never touched.  The
# operator can re-download any cleaned-up episode by re-running the
# podcast's "Download Latest Episodes" or by clicking Download on
# the individual episode after the next feed-refresh re-inserts it.
#
# Idempotent: on a fresh database (no stuck rows) the DELETE is a
# zero-row no-op.  Schema version is still bumped to "51" to keep the
# migrations chain linear.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
DELETE FROM podcast_episodes WHERE file_id IS NULL;
"""

# No DOWN: this is a data cleanup, not a schema change.  The original
# rows had no useful state beyond "this episode failed to download
# once", which is information not worth restoring.
DOWN = ""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0050_add_podcast_default_track_type"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="51",
                sql=UP,
            )
        )
    ]
