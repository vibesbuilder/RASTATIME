"""
RASTATIME 2026-11-03 - archiving stage 3: archive automatically (legacy
migration 0076, operator go 2026-11-03).

Every few minutes :func:`scan` looks at the episodes of shows with "Archive
automatically" switched on (``cc_show_archiving.auto_archive``) and queues
an upload job (trigger ``auto``) for each one that is due; the job runner in
:mod:`archive_jobs` uploads it like one queued by hand.  The rules:

* only episodes that end after the switch was turned on (``auto_since``) -
  nothing is caught up;
* due ``cba_auto_delay_min`` minutes (Settings -> CBA Accounts, default 30)
  after the end of the episode: time to fill in "Episode..." or to tick
  "Do not archive automatically";
* never: rebroadcasts, instances of a "repeat of" show, episodes with "Do
  not archive automatically", episodes with a post, and episodes with any
  upload job - whoever archived by hand keeps the episode;
* always the recording of the episode (``cc_show_instances.file_id``),
  imported, covering at least half of the show;
* the data the CBA requires (:func:`cba.build_meta`) complete.

While something is missing the episode waits; 24 hours after it was due the
scan gives up and leaves a ``skipped`` job with the reason.  A replacement
programme that ran instead of a live show is not recognised (operator
2026-11-03: switch the automatic on only for shows that run reliably).

:func:`refresh_warning` keeps the dashboard warning ``archive_failed``:
automatic uploads of the last 7 days that failed, stayed unclear or were
skipped, as long as the episode has no post (archiving it by hand or
linking the post clears the line).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from . import archive_jobs, cba

logger = logging.getLogger("rastatime_worker.archive")

GIVE_UP_AFTER = timedelta(hours=24)
MIN_RECORDING_SHARE = 0.5
WARNING_TYPE = "archive_failed"
WARNING_DAYS = 7
WARNING_MAX = 10
SCAN_LIMIT = 50

_waiting_logged: set[int] = set()


def auto_delay_min() -> int:
    """Minutes between the end of an episode and its automatic upload."""
    try:
        value = int(archive_jobs._pref("cba_auto_delay_min") or 30)
    except ValueError:
        value = 30
    return min(max(value, 0), 1440)


def recording_problems(
    file_id: Optional[int],
    import_status: Optional[int],
    recording_secs: Optional[float],
    slot_secs: Optional[float],
) -> list[str]:
    """Why the recording cannot be archived yet (empty list = usable)."""
    if not file_id:
        return ["the recording is not in the library"]
    if import_status == 2:
        return ["the import of the recording failed"]
    if import_status != 0:
        return ["the recording is still being imported"]
    if slot_secs and (recording_secs or 0) < MIN_RECORDING_SHARE * float(slot_secs):
        return [
            "the recording covers less than half of the show"
            f" ({round((recording_secs or 0) / 60)} of {round(float(slot_secs) / 60)} min)"
        ]
    return []


def decide(problems: list[str], due_at: datetime, now: datetime) -> str:
    """``queue`` (nothing missing), ``skip`` (given up) or ``wait``."""
    if not problems:
        return "queue"
    if now >= due_at + GIVE_UP_AFTER:
        return "skip"
    return "wait"


def candidates(delay_min: int) -> list[dict[str, Any]]:
    """Ended episodes of shows with the switch on that have no job and no post yet."""
    return archive_jobs._rows(
        "SELECT si.id, si.ends, si.file_id, s.name AS show_name, f.import_status,"
        "       EXTRACT(EPOCH FROM f.length) AS recording_secs,"
        "       EXTRACT(EPOCH FROM (si.ends - si.starts)) AS slot_secs"
        "  FROM cc_show_instances si"
        "  JOIN cc_show s ON s.id = si.show_id"
        "  JOIN cc_show_archiving a ON a.show_id = si.show_id"
        "  LEFT JOIN cc_episode e ON e.instance_id = si.id"
        "  LEFT JOIN cc_files f ON f.id = si.file_id"
        " WHERE a.auto_archive AND a.auto_since IS NOT NULL"
        "   AND si.ends >= a.auto_since"
        "   AND si.ends <= (now() AT TIME ZONE 'UTC') - make_interval(mins => %s)"
        "   AND NOT si.modified_instance"
        "   AND COALESCE(si.rebroadcast, 0) = 0"
        "   AND s.repeat_of_show_id IS NULL"
        "   AND NOT COALESCE(e.no_archive, FALSE)"
        "   AND e.cba_post_id IS NULL"
        "   AND NOT EXISTS (SELECT 1 FROM cc_cba_upload j WHERE j.instance_id = si.id)"
        " ORDER BY si.ends, si.id"
        " LIMIT %s",
        [delay_min, SCAN_LIMIT],
    )


def _queue(instance_id: int, file_id: int) -> Optional[int]:
    from django.db import IntegrityError  # noqa: PLC0415

    try:
        rows = archive_jobs._rows(
            "INSERT INTO cc_cba_upload (instance_id, file_id, trigger) VALUES (%s, %s, 'auto') RETURNING id",
            [instance_id, file_id],
        )
    except IntegrityError:  # queued by hand in the same moment (one open job per instance)
        return None
    return int(rows[0]["id"]) if rows else None


def _skip(instance_id: int, file_id: Optional[int], reasons: list[str]) -> None:
    archive_jobs._execute(
        "INSERT INTO cc_cba_upload (instance_id, file_id, trigger, status, last_error, finished_at)"
        " VALUES (%s, %s, 'auto', 'skipped', %s, now())",
        [instance_id, file_id, "; ".join(reasons)],
    )


def scan(now: Optional[datetime] = None) -> dict[str, int]:
    """Queue, skip or keep waiting for every candidate; returns the counts."""
    now = now or datetime.now(UTC)
    delay = auto_delay_min()
    counts = {"queued": 0, "skipped": 0, "waiting": 0}
    for c in candidates(delay):
        ends = c["ends"] if c["ends"].tzinfo else c["ends"].replace(tzinfo=UTC)
        due_at = ends + timedelta(minutes=delay)
        problems = recording_problems(
            c["file_id"], c["import_status"], c["recording_secs"], c["slot_secs"]
        )
        if not problems:
            ep = archive_jobs.load_episode(int(c["id"]), c["file_id"])
            problems = (
                cba.build_meta(ep)[1] if ep else ["the show instance does not exist any more"]
            )
        verdict = decide(problems, due_at, now)
        if verdict == "queue":
            job_id = _queue(int(c["id"]), int(c["file_id"]))
            if job_id:
                counts["queued"] += 1
                logger.info(
                    "automatic archiving: %s (instance %s) queued as job %s",
                    c["show_name"],
                    c["id"],
                    job_id,
                )
        elif verdict == "skip":
            _skip(int(c["id"]), c["file_id"], problems)
            counts["skipped"] += 1
            logger.warning(
                "automatic archiving: %s (instance %s) skipped - %s",
                c["show_name"],
                c["id"],
                "; ".join(problems),
            )
        else:
            counts["waiting"] += 1
            if int(c["id"]) not in _waiting_logged:
                _waiting_logged.add(int(c["id"]))
                logger.info(
                    "automatic archiving: %s (instance %s) waits - %s",
                    c["show_name"],
                    c["id"],
                    "; ".join(problems),
                )
    return counts


def failed_auto_uploads() -> list[dict[str, Any]]:
    """The lines of the dashboard warning (see module doc)."""
    return archive_jobs._rows(
        "SELECT j.id, j.instance_id, j.status, j.last_error, si.show_id, si.starts, s.name AS show_name"
        "  FROM cc_cba_upload j"
        "  JOIN cc_show_instances si ON si.id = j.instance_id"
        "  JOIN cc_show s ON s.id = si.show_id"
        "  LEFT JOIN cc_episode e ON e.instance_id = j.instance_id"
        " WHERE j.trigger = 'auto' AND j.status IN ('failed', 'unclear', 'skipped')"
        "   AND j.finished_at > now() - make_interval(days => %s)"
        "   AND e.cba_post_id IS NULL"
        "   AND NOT EXISTS (SELECT 1 FROM cc_cba_upload k WHERE k.instance_id = j.instance_id AND k.id > j.id)"
        " ORDER BY si.starts DESC, j.id DESC"
        " LIMIT %s",
        [WARNING_DAYS, WARNING_MAX],
    )


def warning_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PreflightWarning.replace_warnings() input for the failed jobs."""
    rows = []
    for j in jobs:
        starts = j["starts"] if j["starts"].tzinfo else j["starts"].replace(tzinfo=UTC)
        rows.append(
            {
                "severity": "warning",
                "show_id": j["show_id"],
                "show_instance_id": j["instance_id"],
                "starts_at": starts,
                "detail": {
                    "job_id": j["id"],
                    "show_name": j["show_name"],
                    "status": j["status"],
                    "reason": (j["last_error"] or "")[:300],
                },
            }
        )
    return rows


def refresh_warning() -> bool:
    """Rewrite the ``archive_failed`` warnings when their set changed; True when rewritten."""
    from rastatime_api.preflight.models import PreflightWarning  # noqa: PLC0415

    wanted = warning_rows(failed_auto_uploads())
    current = sorted(
        (d or {}).get("job_id") or 0
        for d in PreflightWarning.objects.filter(warning_type=WARNING_TYPE).values_list(
            "detail", flat=True
        )
    )
    if current == sorted(w["detail"]["job_id"] for w in wanted):
        return False
    PreflightWarning.replace_warnings(
        warning_type=WARNING_TYPE, scan_run_id=str(uuid.uuid4()), warnings=wanted
    )
    return True
