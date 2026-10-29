# pylint: disable=invalid-name
#
# RASTATIME 2026-05-19 - Show-Template feature (Section 23.16).
#
# Adds a single table to store reusable show configurations as JSON
# snapshots.  Operator-facing flow:
#
#   1. In the Calendar's "New Show" dialog: dropdown lists existing
#      templates; pick one to pre-fill the form with the template's
#      field values.
#   2. Save the form as a new template (using the show name as the
#      template name) for later reuse.
#   3. Manage existing templates (rename, delete) in a new Settings
#      page "Show Templates".
#
# Schema:
#
#   cc_show_template
#     id              SERIAL PRIMARY KEY
#     name            VARCHAR(255) NOT NULL UNIQUE
#                       — template's display name; unique so the
#                         "Save as Template" UI can ask before
#                         overwriting an existing one.
#     template_data   JSONB NOT NULL
#                       — Snapshot of the show fields the operator
#                         chose to capture: name, url, genre,
#                         description, duration, repeats, link,
#                         repeat_type, days, end_date / no_end,
#                         record_enabled, auto-playlist trio, auth
#                         flags, host usernames, BG/text colour, and
#                         a reference to the show image file path.
#                         Explicitly NOT stored: live-stream
#                         password (security), start_date/start_time
#                         (per-use), per-instance descriptions.
#     created_at      TIMESTAMP NOT NULL DEFAULT NOW()
#     updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
#
# Design decisions recorded 2026-05-19:
#   * Templates are STATION-WIDE — no FK to cc_subjs (any admin/PM
#     can apply/edit any template).
#   * Template-edit changes do NOT propagate to existing shows
#     (one-way stamp model — chosen by operator for simplicity and
#     to avoid surprising side-effects).
#   * Show image: store the cc_files-style path reference, not a
#     copy.  If the operator later deletes the source image, the
#     template loses its image too (acceptable trade-off chosen by
#     operator to keep storage usage flat).
#   * Schema drift on cc_show: missing fields in old templates
#     simply default to the show-form default at apply time;
#     superfluous fields in templates are silently ignored.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
CREATE TABLE cc_show_template (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(255) NOT NULL UNIQUE,
    template_data  JSONB NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX cc_show_template_name_idx ON cc_show_template (name);
"""

DOWN = """
DROP TABLE IF EXISTS cc_show_template;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0052_backfill_podcast_cuein_cueout"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="53",
                sql=UP,
            )
        )
    ]
