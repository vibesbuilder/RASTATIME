# pylint: disable=invalid-name
#
# RASTATIME 2026-11-14 - "published until" for the station podcast
# (operator wish, option B): a track published to My Podcast can carry the
# last day it stays published.
#
#   podcast_episodes.published_until  DATE NULL
#       NULL = no end.  Otherwise the episode stays published through this
#       day (station time zone) and the legacy StationPodcastExpiryTask
#       unpublishes it after midnight, exactly like the Unpublish button -
#       the row goes, so feed, download and public page drop it together.
#
# Propel classes are NOT regenerated and the Django model does not carry
# the column: the legacy readers go through to_jsonb(podcast_episodes)
# (NULL until this migration ran) and check the column before writing, so
# the code may be live before the migration.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE podcast_episodes ADD COLUMN published_until DATE NULL;
"""

DOWN = """
ALTER TABLE podcast_episodes DROP COLUMN IF EXISTS published_until;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0083_track_type_loudness"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="84",
                sql=UP,
            )
        )
    ]
