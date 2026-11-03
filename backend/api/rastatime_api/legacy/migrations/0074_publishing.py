# pylint: disable=invalid-name
#
# RASTATIME 2026-11-03 - publishing stage 1 (CBA publishing, operator go
# 2026-11-03): editorial team profiles, per-show publishing defaults and
# per-episode (= show instance) data.  Nothing is uploaded yet; stage 2
# adds the upload jobs.
#
#   cc_editor_profile       a person of an editorial team; may exist
#                           without a login (subjs_id NULL) - the CBA
#                           field "editors" takes names only
#   cc_show_editor_profile  N:M show <-> profile, both ON DELETE CASCADE
#   cc_show_publishing      one row per show (created on first save):
#                           participants (people involved, for the yearly
#                           statistics), CBA podcast (series) id, default
#                           licence, CBA topic (category) id, languages,
#                           tags, default teaser, contains copyrighted music
#   cc_episode              one row per instance (created on first save):
#                           own title, teaser, image (path relative to the
#                           storage root, like cc_show.image_path), image
#                           licence and caption, participants override
#
# The legacy frontend reads and writes the tables with raw SQL
# (Application_Service_PublishingService); Propel classes are not
# generated.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
CREATE TABLE cc_editor_profile (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    subjs_id INTEGER REFERENCES cc_subjs (id) ON DELETE SET NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE cc_show_editor_profile (
    show_id INTEGER NOT NULL REFERENCES cc_show (id) ON DELETE CASCADE,
    profile_id INTEGER NOT NULL REFERENCES cc_editor_profile (id) ON DELETE CASCADE,
    PRIMARY KEY (show_id, profile_id)
);
CREATE INDEX cc_show_editor_profile_profile_idx ON cc_show_editor_profile (profile_id);
CREATE TABLE cc_show_publishing (
    show_id INTEGER PRIMARY KEY REFERENCES cc_show (id) ON DELETE CASCADE,
    participants SMALLINT CHECK (participants >= 0),
    cba_series_id INTEGER CHECK (cba_series_id > 0),
    license VARCHAR(16),
    category_id INTEGER CHECK (category_id > 0),
    languages VARCHAR(32),
    tags VARCHAR(512),
    teaser VARCHAR(2048),
    contains_copyright BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE cc_episode (
    instance_id INTEGER PRIMARY KEY REFERENCES cc_show_instances (id) ON DELETE CASCADE,
    title VARCHAR(255),
    teaser VARCHAR(2048),
    image_path VARCHAR(512),
    image_license VARCHAR(16),
    image_caption VARCHAR(255),
    participants SMALLINT CHECK (participants >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0073_retire_super_admin"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="74",
                sql=UP,
            )
        )
    ]
