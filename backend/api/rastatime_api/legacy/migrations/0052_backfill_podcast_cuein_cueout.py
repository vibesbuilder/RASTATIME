# pylint: disable=invalid-name
#
# RASTATIME 2026-05-17 - One-shot back-fill of cuein / cueout on podcast
# episode files that were imported before the download_episode() fix.
#
# Background: the Library DataTable's SQL projection computes the
# displayed track length as `(cueout - cuein)::INTERVAL` rather than
# reading cc_files.length directly (StoredFile.php ~line 781).  The
# standard analyzer pipeline sets cue_in=0 and cue_out=length at
# import time so the subtraction yields the real length.  But
# download_episode() bypassed the analyzer and forgot to set them, so
# every podcast episode imported via the synchronous API path showed
# as "0 sec" in the Library even though Calendar ShowContent (which
# reads `length` directly) showed the correct value.
#
# The forward-going fix in download.py now sets cue_in=0 and
# cue_out=length at import time.  This migration patches the rows
# that accumulated BEFORE that fix went in.
#
# Safety:
#   * Only touches cc_files rows that are referenced by a
#     podcast_episodes.file_id — non-podcast files are untouched.
#   * Only fills cuein/cueout where they are currently NULL — does
#     not overwrite any operator-set cue points.
#   * Requires length IS NOT NULL — files where the analyzer never
#     got a length are skipped (would result in cueout=NULL which
#     keeps the "0 sec" display, but at least does not crash).
#
# Idempotent: on a fresh database (no podcast files yet) the UPDATE
# is a zero-row no-op.  Schema version bumped to "52" to keep the
# migrations chain linear.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
UPDATE cc_files
   SET cuein = '00:00:00'::INTERVAL,
       cueout = length
 WHERE id IN (SELECT file_id FROM podcast_episodes WHERE file_id IS NOT NULL)
   AND length IS NOT NULL
   AND cuein IS NULL
   AND cueout IS NULL;
"""

DOWN = ""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0051_cleanup_stuck_podcast_episodes"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="52",
                sql=UP,
            )
        )
    ]
