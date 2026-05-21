# pylint: disable=invalid-name
#
# RASTATIME 2026-05-17 - Per-Podcast Default Track-Type feature.
#
# Adds one column:
#
#   imported_podcast.default_track_type_id  INTEGER NULL
#       Per-podcast default track-type override.  When set, every
#       episode imported from this podcast gets
#       cc_files.track_type_id = default_track_type_id at download
#       time, regardless of whatever the episode's own ID3 tags say.
#
#       NULL = no override (track-type is left at the default that
#       the analyzer / mutagen would infer from ID3 + filename heuristics,
#       which for podcasts is typically empty).
#
#       Operator UX: configurable per podcast in the New / Edit Podcast
#       dialog ("Track Type:" dropdown).  Picking a value applies it
#       to every future episode download from that podcast.  Existing
#       (already-imported) episodes are not retroactively changed.
#
#       Foreign key references cc_track_types(id) — the same table
#       that backs the Library "Track Type" column for hand-uploaded
#       files.  Defined without ON DELETE so removing a track-type
#       row that is still referenced by a podcast will fail loudly
#       (matches the cc_files.track_type_id FK behaviour).

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE imported_podcast
    ADD COLUMN default_track_type_id INTEGER NULL DEFAULT NULL
        REFERENCES cc_track_types(id);
"""

DOWN = """
ALTER TABLE imported_podcast DROP COLUMN IF EXISTS default_track_type_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0049_add_track_expiry_and_podcast_auto_expiry"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="50",
                sql=UP,
            )
        )
    ]
