# pylint: disable=invalid-name
#
# RASTATIME 2026-11-16 - show types (operator wish 2026-11-16, ARCHITECTURE
# 23.120).  A show gets a type out of a list kept under Settings ->
# Track/Show Types; Analytics -> Programme Minutes counts a show as a repeat
# when its type is marked "counts as repeat" (no longer through "Repeat of
# another show", which only copies content now).
#
#   cc_show_types (new)
#     id, code (unique, 16), type_name (64), counts_as_repeat, sort_order
#     seeded with Music, Live, Recording, Repeat (counts as repeat), News,
#     Partner show - a station renames or extends them in the settings.
#   cc_show
#     + show_type_id  INTEGER NULL -> cc_show_types(id) ON DELETE SET NULL
#
# The readers check the table first (information_schema) and read the show
# column through to_jsonb(cc_show), so code and migration may come in any
# order.  Propel is not regenerated.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
CREATE TABLE cc_show_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,
    type_name VARCHAR(64) NOT NULL,
    counts_as_repeat BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO cc_show_types (code, type_name, counts_as_repeat, sort_order) VALUES
    ('music', 'Music', FALSE, 10),
    ('live', 'Live', FALSE, 20),
    ('recording', 'Recording', FALSE, 30),
    ('repeat', 'Repeat', TRUE, 40),
    ('news', 'News', FALSE, 50),
    ('partner', 'Partner show', FALSE, 60);
ALTER TABLE cc_show ADD COLUMN show_type_id INTEGER NULL
    REFERENCES cc_show_types (id) ON DELETE SET NULL;
CREATE INDEX cc_show_show_type_id_idx ON cc_show (show_type_id);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0087_track_type_audio_features"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="88",
                sql=UP,
            )
        )
    ]
