# pylint: disable=invalid-name
#
# RASTATIME 2026-05-16 - Track Expiry + Podcast Auto-Expiry feature.
#
# Adds four columns across two tables:
#
#   cc_files.expires_at    TIMESTAMP NULL
#       Per-track expiry timestamp.  Sourced from a custom ID3 TXXX
#       frame with Description="Expiry" and an ISO-8601 date value
#       (e.g. "Expiry: 2026-12-21"), or computed from the parent
#       Podcast's auto-expiry-days setting at import time.  NULL =
#       no expiry (track lives forever).  See ARCHITECTURE 23.11.
#
#   cc_files.disabled      BOOLEAN DEFAULT false
#       Set to true by the shared pruner (legacy TaskManager,
#       hourly) when expires_at < NOW().  Disabled tracks:
#         * stay visible in the Library (so the operator can sort,
#           filter, and bulk-delete them at their leisure);
#         * stay in existing Smartblocks (already-built schedules
#           keep playing);
#         * are excluded from NEW Smartblock evaluations (queries
#           filter on cc_files.disabled = false).
#       Distinct from cc_files.hidden, which is upstream's own
#       library-visibility flag.
#
#   imported_podcast.auto_expiry_enabled  BOOLEAN DEFAULT false
#   imported_podcast.auto_expiry_days     INTEGER NULL
#       Per-podcast retention.  When enabled, every episode imported
#       from this podcast gets cc_files.expires_at = now() +
#       auto_expiry_days at download time.  Per design decision B
#       (precedence vote 2026-05-16) podcast auto-expiry WINS over
#       any ID3 'Expiry' tag the publisher may have set: subscribers
#       choose retention, publishers don't.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
ALTER TABLE cc_files ADD COLUMN expires_at TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE cc_files ADD COLUMN disabled BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE imported_podcast ADD COLUMN auto_expiry_enabled BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE imported_podcast ADD COLUMN auto_expiry_days INTEGER NULL DEFAULT NULL;
"""

DOWN = """
ALTER TABLE cc_files DROP COLUMN IF EXISTS expires_at;
ALTER TABLE cc_files DROP COLUMN IF EXISTS disabled;
ALTER TABLE imported_podcast DROP COLUMN IF EXISTS auto_expiry_enabled;
ALTER TABLE imported_podcast DROP COLUMN IF EXISTS auto_expiry_days;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0048_add_cc_webstream_input_gain_db"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="49",
                sql=UP,
            )
        )
    ]
