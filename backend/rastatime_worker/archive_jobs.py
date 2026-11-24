"""
RASTATIME 2026-11-03 - archiving stage 2: the upload jobs (``cc_cba_upload``,
legacy migration 0075) processed by RASTATIME-WORKER.

The legacy frontend queues a job ("Archive online..." in the calendar's
Episode dialog); :func:`run_once` claims the next due one, collects the
episode, show and account data with raw SQL (the tables have no Django
models - the legacy frontend owns them), checks it, writes the body and
uploads it through :mod:`cba`, then records the outcome:

* ``done``    - post id on the episode (``cc_episode.cba_post_id``); since
  2026-11-24 the link of the post is e-mailed to the producers of the show
  when Settings -> Archiving -> "Link by e-mail" is on (:func:`send_link_mail`,
  over the SMTP server of Settings -> Alerts; a failed mail never changes
  the job);
* ``retry``   - nothing reached the CBA: queued again after 2, 5, 15, 30,
  60, 120, 240 minutes, until ``give_up_at`` (24 h after queuing) - then
  ``failed`` with the last reason;
* ``failed``  - missing data or the CBA refused: no further attempt;
* ``unclear`` - the post may exist: no automatic attempt, the operator
  looks on cba.media and links the post or archives again.

A job still ``running`` when the worker starts was cut off by a stop or a
crash: back to ``queued`` when no byte had left, else ``unclear``.

The topic list for the show form is fetched here as well, once a day
(``cc_pref`` ``cba_categories_json``).  Never logs the password.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from . import cba

logger = logging.getLogger("rastatime_worker.archive")

BACKOFF_MINUTES = (2, 5, 15, 30, 60, 120, 240)

#: the link mail (Settings -> Archiving -> "Link by e-mail", cc_pref
#: cba_link_mail_*); the station replaces the texts, these are the defaults
LINK_MAIL_SUBJECT = "{show}: the episode of {date} is online"
LINK_MAIL_BODY = (
    "Hello {name},\n\n"
    'the episode "{title}" of {show} ({date} {time}) is now online on cba.media:\n\n'
    "{link}\n\n"
    "{station}"
)
LINK_MAIL_PRIVATE = (
    "Note: the post is private - the link works only when logged in with the"
    " CBA account of the show."
)
LINK_MAIL_FIELDS = ("name", "show", "title", "date", "time", "link", "station")
CATEGORIES_MAX_AGE = timedelta(hours=24)
PROGRESS_EVERY = 5.0


def _db():
    from django.db import connection  # noqa: PLC0415 - Django is set up by the caller

    return connection


def _rows(sql: str, params: Optional[list] = None) -> list[dict[str, Any]]:
    with _db().cursor() as cur:
        cur.execute(sql, params or [])
        if cur.description is None:
            return []
        names = [c[0] for c in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _execute(sql: str, params: Optional[list] = None) -> int:
    with _db().cursor() as cur:
        cur.execute(sql, params or [])
        return cur.rowcount


def tables_ready() -> bool:
    return (
        _rows(
            "SELECT count(*) AS n FROM information_schema.tables WHERE table_schema = current_schema()"
            " AND table_name IN ('cc_cba_upload', 'cc_cba_account', 'cc_episode', 'cc_show_archiving')"
        )[0]["n"]
        == 4
    )


def _pref(key: str) -> Optional[str]:
    rows = _rows(
        "SELECT valstr FROM cc_pref WHERE keystr = %s AND subjid IS NULL ORDER BY id LIMIT 1", [key]
    )
    return rows[0]["valstr"] if rows else None


def _set_pref(key: str, value: str) -> None:
    if not _execute(
        "UPDATE cc_pref SET valstr = %s WHERE keystr = %s AND subjid IS NULL", [value, key]
    ):
        _execute("INSERT INTO cc_pref (keystr, valstr) VALUES (%s, %s)", [key, value])


def station_timezone():
    from zoneinfo import ZoneInfo  # noqa: PLC0415

    try:
        return ZoneInfo(_pref("timezone") or "UTC")
    except Exception:  # noqa: BLE001 - an unknown zone name falls back to UTC
        return ZoneInfo("UTC")


def upload_kbit() -> int:
    try:
        value = int(_pref("cba_upload_kbit") or 0)
    except ValueError:
        value = 0
    return value if value > 0 else 4000


def recover_interrupted() -> int:
    """At start: jobs left 'running' by a stop or crash (see module doc)."""
    n = _execute(
        "UPDATE cc_cba_upload SET status = 'queued', next_attempt_at = now(),"
        " last_error = 'the background service stopped before the upload began'"
        " WHERE status = 'running' AND COALESCE(bytes_sent, 0) = 0"
    )
    n += _execute(
        "UPDATE cc_cba_upload SET status = 'unclear', finished_at = now(),"
        " last_error = 'the background service stopped during the upload'"
        " WHERE status = 'running'"
    )
    return n


def claim_next() -> Optional[dict[str, Any]]:
    rows = _rows(
        "UPDATE cc_cba_upload SET status = 'running', started_at = now(), attempts = attempts + 1,"
        " bytes_sent = 0, bytes_total = NULL"
        " WHERE id = (SELECT id FROM cc_cba_upload WHERE status = 'queued' AND next_attempt_at <= now()"
        "             ORDER BY next_attempt_at, id LIMIT 1 FOR UPDATE SKIP LOCKED)"
        " RETURNING id, instance_id, file_id, attempts, give_up_at"
    )
    return rows[0] if rows else None


def load_episode(instance_id: int, file_id: Optional[int]) -> Optional[cba.Episode]:
    from rastatime_api.storage.root import get_storage_root  # noqa: PLC0415

    rows = _rows(
        "SELECT si.starts, si.description, s.name AS show_name, s.description AS show_description,"
        "       e.title, e.teaser, e.image_path, e.image_license, e.image_caption, e.production_date, e.cba_post_id,"
        "       a.languages, a.category_id, a.cba_series_id, a.cba_status, a.license, a.tags, a.teaser AS show_teaser,"
        "       a.contains_copyright, acc.username, acc.app_password, f.filepath"
        "  FROM cc_show_instances si"
        "  JOIN cc_show s ON s.id = si.show_id"
        "  LEFT JOIN cc_episode e ON e.instance_id = si.id"
        "  LEFT JOIN cc_show_archiving a ON a.show_id = si.show_id"
        "  LEFT JOIN cc_cba_account acc ON acc.id = a.cba_account_id"
        "  LEFT JOIN cc_files f ON f.id = %s"
        " WHERE si.id = %s",
        [file_id, instance_id],
    )
    if not rows:
        return None
    r = rows[0]
    tz = station_timezone()
    starts = r["starts"]
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    root = get_storage_root()

    def absolute(rel: Optional[str]) -> str:
        if not rel:
            return ""
        return rel if os.path.isabs(rel) else os.path.join(root, rel)

    editors = tuple(
        row["name"]
        for row in _rows(
            "SELECT p.name FROM cc_show_editor_profile se JOIN cc_editor_profile p ON p.id = se.profile_id"
            " JOIN cc_show_instances si ON si.show_id = se.show_id WHERE si.id = %s ORDER BY lower(p.name), p.id",
            [instance_id],
        )
    )
    return cba.Episode(
        show_name=r["show_name"] or "",
        starts_local=starts.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S"),
        title=r["title"] or "",
        description=r["description"] or "",
        show_description=r["show_description"] or "",
        teaser=r["teaser"] or "",
        show_teaser=r["show_teaser"] or "",
        production_date=r["production_date"].isoformat() if r["production_date"] else "",
        languages=r["languages"] or "",
        category_id=r["category_id"],
        series_id=r["cba_series_id"],
        status=r["cba_status"] or "publish",
        license=r["license"] or "",
        tags=r["tags"] or "",
        editors=editors,
        contains_copyright=bool(r["contains_copyright"]),
        image_path=absolute(r["image_path"]),
        image_license=r["image_license"] or "",
        image_caption=r["image_caption"] or "",
        audio_path=absolute(r["filepath"]),
        username=r["username"] or "",
        password=r["app_password"] or "",
        already_post_id=r["cba_post_id"],
        today_local=datetime.now(tz).strftime("%Y-%m-%d"),
    )


def _finish(job_id: int, status: str, message: str = "", post_id: Optional[int] = None) -> None:
    _execute(
        "UPDATE cc_cba_upload SET status = %s, last_error = %s, post_id = %s, finished_at = now() WHERE id = %s",
        [status, message or None, post_id, job_id],
    )


def _retry_or_give_up(job: dict[str, Any], message: str) -> str:
    attempts = int(job["attempts"])
    delay = BACKOFF_MINUTES[min(attempts - 1, len(BACKOFF_MINUTES) - 1)]
    next_at = datetime.now(UTC) + timedelta(minutes=delay)
    give_up = job["give_up_at"]
    if give_up.tzinfo is None:
        give_up = give_up.replace(tzinfo=UTC)
    if next_at > give_up:
        _finish(job["id"], "failed", f"gave up after 24 hours: {message}")
        return "failed"
    _execute(
        "UPDATE cc_cba_upload SET status = 'queued', next_attempt_at = %s, last_error = %s WHERE id = %s",
        [next_at, message, job["id"]],
    )
    return "retry"


def post_link(post_id: int) -> str:
    """The address of a CBA post (redirects to its page; the same as in Archive Status)."""
    return f"https://cba.media/?p={int(post_id)}"


def fill_template(template: str, values: dict[str, str]) -> str:
    """Replace the placeholders {name} ... {station}; any other brace stays as typed."""
    out = template
    for key in LINK_MAIL_FIELDS:
        out = out.replace("{" + key + "}", values.get(key, ""))
    return out


def link_mail_texts() -> Optional[tuple[str, str, str]]:
    """(subject, body, private note) when the link mail is switched on, else None."""
    if (_pref("cba_link_mail_enabled") or "").strip().lower() not in ("1", "true", "t", "on"):
        return None
    return (
        (_pref("cba_link_mail_subject") or "").strip() or LINK_MAIL_SUBJECT,
        (_pref("cba_link_mail_body") or "").strip() or LINK_MAIL_BODY,
        (_pref("cba_link_mail_private") or "").strip() or LINK_MAIL_PRIVATE,
    )


def producer_addresses(instance_id: int) -> list[tuple[str, str]]:
    """(name, e-mail) of the active producers of the episode's show that have an address."""
    return [
        (str(r["name"]), str(r["email"]).strip())
        for r in _rows(
            "SELECT p.name, p.email FROM cc_show_editor_profile se"
            " JOIN cc_editor_profile p ON p.id = se.profile_id"
            " JOIN cc_show_instances si ON si.show_id = se.show_id"
            " WHERE si.id = %s AND p.active AND COALESCE(trim(p.email), '') <> ''"
            " ORDER BY lower(p.name), p.id",
            [instance_id],
        )
    ]


def _mail_settings():
    from rastatime_shared.alerts import settings_from_entries  # noqa: PLC0415

    entries = {
        r["keystr"]: r["valstr"]
        for r in _rows(
            "SELECT keystr, valstr FROM cc_pref WHERE left(keystr, 7) = 'alerts_' AND subjid IS NULL"
        )
    }
    return settings_from_entries(entries, station_name=_pref("station_name") or "")


def _record_link_mail(job_id: int, note: str) -> None:
    """Keep the outcome on the job once migration 0090 added the columns."""
    if _rows(
        "SELECT count(*) AS n FROM information_schema.columns WHERE table_schema = current_schema()"
        " AND table_name = 'cc_cba_upload' AND column_name = 'link_mail_note'"
    )[0]["n"]:
        _execute(
            "UPDATE cc_cba_upload SET link_mail_at = now(), link_mail_note = %s WHERE id = %s",
            [note[:2000], job_id],
        )


def send_link_mail(
    job: dict[str, Any], ep: cba.Episode, meta: dict[str, Any], post_id: int, sender: Any = None
) -> Optional[str]:
    """
    E-mail the link of the new post to the producers of the show (operator
    Go 2026-11-24): one mail per producer, so each sees only their own
    address and is greeted by name.  Returns the note kept on the job, or
    None when the link mail is switched off.  Never raises - the upload is
    done whatever happens to the mail.
    """
    try:
        texts = link_mail_texts()
        if texts is None:
            return None
        subject_t, body_t, private_t = texts
        people = producer_addresses(int(job["instance_id"]))
        if not people:
            note = "link not e-mailed: no active producer of the show has an e-mail address"
        else:
            settings = _mail_settings()
            if not (settings.smtp_host and settings.mail_from):
                note = "link not e-mailed: SMTP server or sender missing (Settings -> Alerts)"
            else:
                if sender is None:
                    from rastatime_shared.alerts import send_mail as sender  # noqa: PLC0415
                values = {
                    "show": ep.show_name,
                    "title": str(meta.get("title") or ep.show_name),
                    "date": ep.starts_local[:10],
                    "time": ep.starts_local[11:16],
                    "link": post_link(post_id),
                    "station": settings.station_name,
                }
                sent, failed = [], []
                for name, address in people:
                    values["name"] = name
                    body = fill_template(body_t, values)
                    if ep.status == "private":
                        body += "\n\n" + private_t
                    try:
                        sender(
                            settings, fill_template(subject_t, values), body, recipients=[address]
                        )
                        sent.append(address)
                    except Exception as exc:  # noqa: BLE001 - the next producer still gets theirs
                        failed.append(f"{address} ({exc.__class__.__name__})")
                parts = []
                if sent:
                    parts.append("link e-mailed to " + ", ".join(sent))
                if failed:
                    parts.append("link e-mail failed: " + ", ".join(failed))
                note = "; ".join(parts)
        logger.info("archive job %s: %s", job["id"], note)
        _record_link_mail(int(job["id"]), note)
        return note
    except Exception:  # noqa: BLE001 - never changes the finished upload
        logger.exception("archive job %s: link e-mail not sent", job["id"])
        return "link e-mail failed: unexpected error"


def process(job: dict[str, Any], kbit: Optional[int] = None, session: Any = None) -> str:
    """Upload one claimed job; returns the state it ended in."""
    ep = load_episode(int(job["instance_id"]), job["file_id"])
    if ep is None:
        _finish(job["id"], "failed", "the show instance does not exist any more")
        return "failed"
    meta, missing = cba.build_meta(ep)
    if missing:
        _finish(job["id"], "failed", "; ".join(missing))
        logger.warning(
            "archive job %s (instance %s): not sent - %s",
            job["id"],
            job["instance_id"],
            "; ".join(missing),
        )
        return "failed"

    tmp_dir = tempfile.mkdtemp(prefix="rt-cba-")
    body_path = os.path.join(tmp_dir, "body.bin")
    try:
        image = ep.image_path if ep.image_path and os.path.isfile(ep.image_path) else ""
        content_type, size = cba.write_body(body_path, meta, ep.audio_path, image)
        _execute("UPDATE cc_cba_upload SET bytes_total = %s WHERE id = %s", [size, job["id"]])
        rate = kbit or upload_kbit()
        logger.info(
            "archive job %s (instance %s): uploading %d bytes at %d kbit/s as %s",
            job["id"],
            job["instance_id"],
            size,
            rate,
            ep.username,
        )
        started = time.monotonic()

        def progress(sent: int) -> None:
            _execute("UPDATE cc_cba_upload SET bytes_sent = %s WHERE id = %s", [sent, job["id"]])

        outcome, sent = cba.upload(
            body_path, content_type, size, ep.username, ep.password, rate, progress, session=session
        )
        _execute("UPDATE cc_cba_upload SET bytes_sent = %s WHERE id = %s", [sent, job["id"]])
    finally:
        try:
            os.remove(body_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass

    logger.info(
        "archive job %s (instance %s): %s after %.0f s%s",
        job["id"],
        job["instance_id"],
        outcome.kind,
        time.monotonic() - started,
        f" - {outcome.message}" if outcome.message else "",
    )
    if outcome.kind == "done":
        _finish(job["id"], "done", "", outcome.post_id)
        _execute(
            "INSERT INTO cc_episode (instance_id, cba_post_id, cba_archived_at, updated_at) VALUES (%s, %s, now(), now())"
            " ON CONFLICT (instance_id) DO UPDATE SET cba_post_id = EXCLUDED.cba_post_id,"
            " cba_archived_at = now(), updated_at = now()",
            [job["instance_id"], outcome.post_id],
        )
        send_link_mail(job, ep, meta, outcome.post_id)
        return "done"
    if outcome.kind == "retry":
        return _retry_or_give_up(job, outcome.message)
    _finish(job["id"], outcome.kind, outcome.message)
    return outcome.kind


def run_once(session: Any = None) -> Optional[str]:
    """Process at most one due job; None when there was none."""
    job = claim_next()
    if job is None:
        return None
    try:
        return process(job, session=session)
    except Exception as exc:  # noqa: BLE001 - a broken job must not stop the worker
        logger.exception("archive job %s: unexpected error", job["id"])
        _finish(
            job["id"],
            "unclear",
            f"unexpected error in the background service: {exc.__class__.__name__}",
        )
        return "unclear"


def refresh_categories(force: bool = False, session: Any = None) -> bool:
    """Fetch the CBA topics once a day for the show form; True when refreshed."""
    fetched = _pref("cba_categories_fetched")
    if not force and fetched:
        try:
            if datetime.now(UTC) - datetime.fromisoformat(fetched) < CATEGORIES_MAX_AGE:
                return False
        except ValueError:
            pass
    import requests  # noqa: PLC0415

    http = session or requests
    found: list[dict[str, Any]] = []
    page = 1
    try:
        while True:
            r = http.get(
                cba.CATEGORIES_URL,
                params={"per_page": 100, "page": page, "_fields": "id,name,parent"},
                headers={"User-Agent": "RASTATIME"},
                timeout=(10, 30),
            )
            r.raise_for_status()
            found += [
                {"id": int(c["id"]), "name": str(c["name"]), "parent": int(c.get("parent") or 0)}
                for c in r.json()
            ]
            if page >= int(r.headers.get("X-WP-TotalPages", "1") or 1):
                break
            page += 1
    except Exception as exc:  # noqa: BLE001 - keep the old list
        logger.warning("CBA topics not refreshed: %s", exc.__class__.__name__)
        return False
    if not found:
        return False
    _set_pref("cba_categories_json", json.dumps(found, ensure_ascii=False))
    _set_pref("cba_categories_fetched", datetime.now(UTC).isoformat())
    logger.info("CBA topics refreshed: %d", len(found))
    return True
