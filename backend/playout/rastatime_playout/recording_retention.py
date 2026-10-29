"""
recording_retention — automatic cleanup of old 24/7 archive recordings.

RASTATIME 2026-06-05 — Record-per-Hour stage 3.

The 24/7 hourly recorder (see ``liquidsoap_config._render_hourly_recording_block``)
writes ``<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.<ext>``.  This module
prunes whole per-day subfolders once they are older than the operator-
configured retention window (Settings -> Local Machine -> "24/7 Recording",
``local_247_recording_retention_days``).

Design
------

* :func:`prune_old_recordings` is a PURE function (inject ``today``) so it
  is fully unit-testable against a temp directory with no clock / thread.
* :class:`RecordingRetentionThread` is a daemon thread that Pypo starts at
  boot and stops on shutdown.  It re-reads the cc_pref config each cycle,
  so a retention-days change is picked up without a Pypo restart.

Safety
------

Only directories named exactly ``YYYY-MM-DD`` directly under the configured
folder are ever considered.  Any other name — and in particular the
*separate* per-show "Show Recording Folder" — is left untouched.  Pruning is
disabled (no-op) unless the recorder is enabled, a folder is set, AND
``retention_days > 0``.
"""
from __future__ import annotations

import logging
import shutil
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


def prune_old_recordings(
    folder: Path,
    retention_days: int,
    *,
    today: date,
) -> List[Path]:
    """
    Delete per-day subfolders (named ``YYYY-MM-DD``) under ``folder`` that
    are at least ``retention_days`` days old.  Returns the deleted folder
    paths (sorted, oldest first).

    A day-folder dated ``D`` is deleted when ``(today - D).days >=
    retention_days`` — i.e. "delete a recording once it is
    ``retention_days`` days old".

    No-ops (returns ``[]``) when ``retention_days <= 0`` (keep forever) or
    the folder does not exist.  Entries that are not ``YYYY-MM-DD``
    directories are ignored, so this can never touch the separate per-show
    recordings or stray files.
    """
    if retention_days <= 0 or not folder:
        return []
    folder = Path(folder)
    if not folder.is_dir():
        return []

    try:
        entries = sorted(folder.iterdir())
    except OSError as exc:
        logger.warning("Recording retention: cannot list %s: %s", folder, exc)
        return []

    deleted: List[Path] = []
    for entry in entries:
        if not entry.is_dir():
            continue
        try:
            day = datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            continue  # not a YYYY-MM-DD folder -> leave it alone
        if (today - day).days >= retention_days:
            try:
                shutil.rmtree(entry)
                deleted.append(entry)
            except OSError as exc:
                logger.warning(
                    "Recording retention: could not delete %s: %s",
                    entry, exc,
                )
    return deleted


class RecordingRetentionThread(threading.Thread):
    """
    Daemon thread that periodically prunes old 24/7 recordings.

    Parameters
    ----------
    get_config:
        Callable returning the cc_pref 24/7-recording dict (the shape
        produced by ``liquidsoap_config.read_hourly_recording_config_from_db``
        — keys ``enabled`` / ``folder`` / ``retention_days``).  Called once
        per cycle so config changes are picked up without a restart.
    interval_s:
        Seconds between prune passes (default 1 h).
    today_fn:
        Injectable "current date" provider (for tests).

    Never raises out of the loop — a prune failure is logged and the thread
    keeps running.  Stop it with :meth:`stop` (idempotent).
    """

    def __init__(
        self,
        get_config: Callable[[], Dict],
        *,
        interval_s: float = 3600.0,
        today_fn: Callable[[], date] = date.today,
    ) -> None:
        super().__init__(name="recording-retention", daemon=True)
        self._get_config = get_config
        self._interval_s = interval_s
        self._today_fn = today_fn
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        logger.info(
            "Recording retention thread started (every %.0f s).",
            self._interval_s,
        )
        # One pass shortly after boot, then every interval until stopped.
        while not self._stop.is_set():
            try:
                self._run_once()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Recording retention pass failed: %s", exc)
            self._stop.wait(self._interval_s)
        logger.info("Recording retention thread stopped.")

    def _run_once(self) -> None:
        cfg = self._get_config() or {}
        if not cfg.get("enabled") or not cfg.get("folder"):
            return
        try:
            retention_days = int(cfg.get("retention_days") or 0)
        except (TypeError, ValueError):
            return
        if retention_days <= 0:
            return
        deleted = prune_old_recordings(
            Path(cfg["folder"]),
            retention_days,
            today=self._today_fn(),
        )
        if deleted:
            logger.info(
                "Recording retention: deleted %d day-folder(s) older than "
                "%d days from %s (%s).",
                len(deleted), retention_days, cfg["folder"],
                ", ".join(p.name for p in deleted),
            )
