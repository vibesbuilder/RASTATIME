# pylint: disable=invalid-name
#
# RASTATIME 2026-11-03 - archiving stage 2 (upload to cba.media by hand,
# operator go 2026-11-03).  The feature is called "Archiving" in the UI
# (operator: "Publish" belongs to My Podcast), so the per-show table of
# stage 1 is renamed with it.
#
#   cc_show_publishing  -> cc_show_archiving, plus
#       cba_account_id  the CBA user the episodes are archived under
#                       (ON DELETE SET NULL)
#       cba_status      visibility on cba.media: publish | unlisted | private
#   cc_cba_account      CBA users (label, user name, WordPress application
#                       password - write-only in the UI, admins only)
#   cc_episode          + production_date (NULL = the broadcast day),
#                       no_archive (never archive this episode
#                       automatically), cba_post_id / cba_archived_at,
#                       image_caption widened to 500 (CBA limit)
#   cc_cba_upload       one row per upload job, processed by
#                       RASTATIME-WORKER; at most one open (queued or
#                       running) job per instance
#   cc_pref cba_upload_kbit  upload bandwidth limit (default 4000 kbit/s,
#                       the uplink also carries the listener streams)

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
ALTER TABLE cc_show_publishing RENAME TO cc_show_archiving;
CREATE TABLE cc_cba_account (
    id SERIAL PRIMARY KEY,
    label VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    app_password VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE cc_show_archiving
    ADD COLUMN cba_account_id INTEGER REFERENCES cc_cba_account (id) ON DELETE SET NULL,
    ADD COLUMN cba_status VARCHAR(16) NOT NULL DEFAULT 'publish'
        CHECK (cba_status IN ('publish', 'unlisted', 'private'));
ALTER TABLE cc_episode
    ADD COLUMN production_date DATE,
    ADD COLUMN no_archive BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN cba_post_id INTEGER,
    ADD COLUMN cba_archived_at TIMESTAMPTZ,
    ALTER COLUMN image_caption TYPE VARCHAR(500);
CREATE TABLE cc_cba_upload (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES cc_show_instances (id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES cc_files (id) ON DELETE SET NULL,
    trigger VARCHAR(8) NOT NULL DEFAULT 'manual' CHECK (trigger IN ('manual', 'auto')),
    status VARCHAR(12) NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'done', 'failed', 'unclear', 'cancelled')),
    attempts SMALLINT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    give_up_at TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '24 hours',
    last_error TEXT,
    post_id INTEGER,
    bytes_total BIGINT,
    bytes_sent BIGINT,
    requested_by INTEGER REFERENCES cc_subjs (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);
CREATE INDEX cc_cba_upload_instance_idx ON cc_cba_upload (instance_id);
CREATE UNIQUE INDEX cc_cba_upload_open_idx ON cc_cba_upload (instance_id)
    WHERE status IN ('queued', 'running');
INSERT INTO cc_pref (keystr, valstr)
    SELECT 'cba_upload_kbit', '4000'
    WHERE NOT EXISTS (SELECT 1 FROM cc_pref WHERE keystr = 'cba_upload_kbit' AND subjid IS NULL);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0074_publishing"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="75",
                sql=UP,
            )
        )
    ]
