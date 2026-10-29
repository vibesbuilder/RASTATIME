"""
RASTATIME 2026-09-16 - manual backup via the UI (work-order point 10,
stage 1: database + configuration; stage 2 (2026-09-17): media library
as an incremental robocopy mirror in <backup folder>/media, verified
file-by-file after every run - never zipped and never sent through the
browser).

The job writes one self-contained ZIP per run into the operator-chosen
backup folder (site preference ``local_backup_folder``)::

    rastatime-backup-<YYYY-MM-DDTHHMM>.zip
        db.dump          pg_dump custom format (pg_restore reads it)
        config/<files>   every file directly inside the config folder
        manifest.json    created_at, database, pg_dump version, contents

pg_dump streams straight into the ZIP (no temp files); the credentials
come from Django's database settings, which production fills from
``rastatime.conf`` (operator decision 2026-09-16).  The password travels
via ``PGPASSWORD`` in the child's environment, never on the command line
and never in a log line.

State lives in the site preference ``local_backup_state`` as JSON, the
same pattern as the storage move job::

    {"state": "idle|running|done|failed|interrupted", "started_at": ...,
     "finished_at": ..., "file": ..., "bytes": n, "error": null|"...",
     "pid": n, "heartbeat": iso}

Restores stay a CLI/offline procedure (docs/operator/BACKUP.md section 7)
- deliberately no restore endpoint.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from django.conf import settings
from django.db import connection

from . import root as storage_root

logger = logging.getLogger(__name__)

BACKUP_FOLDER_KEY = "local_backup_folder"
BACKUP_STATE_KEY = "local_backup_state"
INCLUDE_MEDIA_KEY = "local_backup_include_media"
HEARTBEAT_STALE_SECONDS = 45
FREE_BYTES_MIN = 500 * 1024 * 1024
ZIP_NAME_RE = re.compile(r"^rastatime-backup-\d{4}-\d{2}-\d{2}T\d{4}(-\d+)?\.zip$")
CHUNK = 1024 * 1024
# RASTATIME 2026-09-17 - stage 2: the media library is mirrored (not
# zipped - it is many gigabytes) into <backup folder>/media with robocopy
# /MIR, so a second run only copies what changed.  Same flags as the
# storage move job, plus /PURGE semantics from /MIR: files deleted from
# the library disappear from the mirror.
MEDIA_DIRNAME = "media"
ROBOCOPY = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "Robocopy.exe")
PROGRESS_INTERVAL_SECONDS = 3.0


class BackupInProgress(Exception):
    pass


class InvalidFolder(ValueError):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state() -> dict:
    raw = storage_root.read_setting(BACKUP_STATE_KEY)
    if not raw:
        return {"state": "idle"}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"state": "idle"}
    return data if isinstance(data, dict) and data.get("state") else {"state": "idle"}


def save_state(state: dict) -> None:
    storage_root.write_setting(BACKUP_STATE_KEY, json.dumps(state))


def get_backup_folder() -> Optional[str]:
    value = storage_root.read_setting(BACKUP_FOLDER_KEY)
    return storage_root.normalize(value) if value else None


def set_backup_folder(path: str) -> None:
    storage_root.write_setting(BACKUP_FOLDER_KEY, storage_root.normalize(path))


def get_include_media() -> bool:
    return (storage_root.read_setting(INCLUDE_MEDIA_KEY) or "").lower() == "true"


# ---- stage 3 (2026-09-17): automatic backups --------------------------------
#
# The schedule itself lives in the Windows Task Scheduler (a daily run of
# ``manage.py backup_auto`` via scripts/backup-auto.ps1, registered once
# by the operator) - the command checks the due-ness below, so the task
# can fire daily while the operator chooses "every N days" here.

AUTO_KEY = "local_backup_auto"
AUTO_DEFAULTS = {"enabled": False, "every_days": 1, "retention_days": 30}


def get_auto_config() -> dict:
    raw = storage_root.read_setting(AUTO_KEY)
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    cfg = dict(AUTO_DEFAULTS)
    if isinstance(data, dict):
        cfg.update({k: data[k] for k in AUTO_DEFAULTS if k in data})
    cfg["enabled"] = bool(cfg["enabled"])
    cfg["every_days"] = max(1, int(cfg["every_days"] or 1))
    cfg["retention_days"] = max(0, int(cfg["retention_days"] or 0))
    return cfg


def set_auto_config(cfg: dict) -> None:
    storage_root.write_setting(AUTO_KEY, json.dumps(cfg))


def newest_backup_at(folder: Optional[str] = None) -> Optional[datetime]:
    backups = list_backups(folder)
    if not backups:
        return None
    return max(datetime.fromisoformat(b["created_at"]) for b in backups)


def auto_backup_due(cfg: Optional[dict] = None, folder: Optional[str] = None):
    """(due: bool, reason: str) - due when no backup exists or the newest
    is at least ``every_days`` old (minus one hour of slack, so a daily
    task firing a few minutes early still runs)."""
    cfg = cfg or get_auto_config()
    if not cfg["enabled"]:
        return False, "automatic backups are disabled"
    folder = folder or get_backup_folder()
    if not folder:
        return False, "no backup folder configured"
    newest = newest_backup_at(folder)
    if newest is None:
        return True, "no backup yet"
    age = datetime.now(timezone.utc) - newest
    threshold = timedelta(days=cfg["every_days"]) - timedelta(hours=1)
    if age >= threshold:
        return True, f"newest backup is {age.days} day(s) old"
    return False, f"newest backup is recent ({newest.isoformat(timespec='seconds')})"


def prune_old_backups(folder: Optional[str] = None, retention_days: Optional[int] = None) -> List[str]:
    """Deletes ZIPs older than ``retention_days`` (0 = keep everything).
    The newest backup always survives.  Returns the deleted names."""
    cfg_days = get_auto_config()["retention_days"] if retention_days is None else retention_days
    if cfg_days <= 0:
        return []
    folder = folder or get_backup_folder()
    backups = list_backups(folder)
    if len(backups) <= 1:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg_days)
    deleted = []
    for entry in backups[1:]:                      # newest first - keep [0]
        if datetime.fromisoformat(entry["created_at"]) < cutoff:
            try:
                os.remove(os.path.join(folder, entry["name"]))
                deleted.append(entry["name"])
            except OSError as exc:
                logger.warning("retention: could not delete %s: %s", entry["name"], exc)
    if deleted:
        logger.info("retention: deleted %d backup(s) older than %d day(s): %s",
                    len(deleted), cfg_days, ", ".join(deleted))
    return deleted


def set_include_media(value: bool) -> None:
    storage_root.write_setting(INCLUDE_MEDIA_KEY, "true" if value else "false")


def media_mirror_dir(folder: Optional[str] = None) -> Optional[str]:
    folder = folder or get_backup_folder()
    return os.path.join(folder, MEDIA_DIRNAME) if folder else None


def config_dir() -> str:
    """The folder holding rastatime.conf (and icecast.xml etc.)."""
    filepath = os.environ.get("RASTATIME_CONFIG_FILEPATH") or os.environ.get(
        "LIBRETIME_CONFIG_FILEPATH"  # stage B bridge
    )
    if filepath:
        return str(Path(filepath).parent)
    return "C:/RASTATIME/config"


def validate_folder(target: str) -> dict:
    """Checks a candidate backup folder; never raises."""
    errors: List[str] = []
    t = storage_root.normalize(target)
    root = storage_root.normalize(storage_root.get_storage_root(refresh=True))
    if not t:
        errors.append("Enter a folder path.")
    elif t.startswith("//"):
        errors.append("Network paths are not supported - use a local drive.")
    elif not re.match(r"^[A-Za-z]:/", t):
        errors.append("Enter an absolute path on a local drive, for example D:/rastatime-backups.")
    free = 0
    if not errors:
        drive = t[:3]
        if not os.path.isdir(drive):
            errors.append(f"Drive {t[:2]} does not exist.")
        elif root and (t.lower() == root.lower()
                       or t.lower().startswith(root.lower().rstrip("/") + "/")):
            errors.append("The backup folder must not lie inside the media library.")
        else:
            try:
                os.makedirs(t, exist_ok=True)
                probe = os.path.join(t, ".rastatime-write-test")
                with open(probe, "wb") as fh:
                    fh.write(b"ok")
                os.remove(probe)
            except OSError as exc:
                errors.append(f"Cannot create or write to {t}: {exc}")
            try:
                free = shutil.disk_usage(t if os.path.isdir(t) else drive).free
            except OSError:
                free = 0
            if free and free < FREE_BYTES_MIN:
                errors.append(f"Not enough free space: {free // 1048576} MB free.")
    return {"ok": not errors, "errors": errors, "target": t, "free_bytes": free}


def list_backups(folder: Optional[str] = None) -> List[dict]:
    folder = folder or get_backup_folder()
    if not folder or not os.path.isdir(folder):
        return []
    entries = []
    for path in glob.glob(os.path.join(folder, "rastatime-backup-*.zip")):
        name = os.path.basename(path)
        if not ZIP_NAME_RE.match(name):
            continue
        try:
            st = os.stat(path)
        except OSError:
            continue
        entries.append({
            "name": name, "bytes": st.st_size,
            "created_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        })
    entries.sort(key=lambda e: e["name"], reverse=True)
    return entries


def backup_file_path(name: str) -> Optional[str]:
    """Absolute path of an existing backup by its bare name; traversal-safe."""
    folder = get_backup_folder()
    if not folder or not ZIP_NAME_RE.match(name or ""):
        return None
    path = os.path.join(folder, name)
    return path if os.path.isfile(path) else None


def _pg_dump_binary() -> str:
    found = shutil.which("pg_dump")
    if found:
        return found
    candidates = sorted(glob.glob(r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe"))
    if candidates:
        return candidates[-1]
    raise RuntimeError("pg_dump not found (PATH or C:\\Program Files\\PostgreSQL\\*\\bin).")


def _pg_dump_command() -> tuple:
    """(argv, env) for a custom-format dump to stdout; password only in env."""
    db = settings.DATABASES["default"]
    binary = _pg_dump_binary()
    argv = [
        binary,
        "--host", str(db.get("HOST") or "127.0.0.1"),
        "--port", str(db.get("PORT") or "5432"),
        "--username", str(db.get("USER") or ""),
        "--dbname", str(db.get("NAME") or ""),
        "--format", "custom",
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = str(db.get("PASSWORD") or "")
    return argv, env


def _pg_dump_version(binary: str) -> str:
    try:
        out = subprocess.run(  # noqa: S603
            [binary, "--version"], capture_output=True, timeout=10, check=False,
        ).stdout.decode("utf-8", "replace").strip()
        return out or "unknown"
    except OSError:
        return "unknown"


class BackupJob:
    """One job per API process; the persisted state is the truth."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._proc: Optional[subprocess.Popen] = None
        self._cancel = threading.Event()

    # ---- public --------------------------------------------------------

    def status(self) -> dict:
        state = load_state()
        if state.get("state") == "running" and not self._alive(state):
            state["state"] = "interrupted"
            state["error"] = "The backup was interrupted (service restart) - run it again."
            state["finished_at"] = _now()
            save_state(state)
        return state

    def start(self) -> dict:
        with self._lock:
            if self.status().get("state") == "running":
                raise BackupInProgress("a backup is already running")
            folder = get_backup_folder()
            if not folder:
                raise InvalidFolder(["Choose a backup folder first."])
            check = validate_folder(folder)
            if not check["ok"]:
                raise InvalidFolder(check["errors"])
            include_media = get_include_media()
            state = {
                "state": "running", "phase": "database",
                "started_at": _now(), "finished_at": None,
                "file": None, "bytes": 0, "error": None,
                "include_media": include_media,
                "pid": os.getpid(), "heartbeat": _now(),
            }
            if include_media:
                # RASTATIME 2026-10-28 - sizes and the free-space check moved
                # into the job thread (_size_media): walking the library and
                # the mirror on a USB disk took minutes here, longer than the
                # UI waits for the answer (20 s), and "Backup Now" reported
                # "API not reachable" although the start was merely slow.
                state.update(media_source=storage_root.get_storage_root(refresh=True),
                             media_total_files=None, media_total_bytes=None,
                             media_done_files=0, media_done_bytes=0,
                             media_free_bytes=check.get("free_bytes"))
            save_state(state)
            self._cancel.clear()
            self._thread = threading.Thread(
                target=self._run, args=(state, folder), name="backup", daemon=True,
            )
            self._thread.start()
            return state

    def cancel(self) -> dict:
        """Stops the media mirror (the ZIP part is seconds and finishes).
        The mirror keeps what was copied; the next run resumes there."""
        with self._lock:
            state = self.status()
            if state.get("state") == "running" and state.get("phase") == "media":
                self._cancel.set()
                if self._proc is not None and self._proc.poll() is None:
                    try:
                        self._proc.terminate()
                    except OSError:
                        pass
            return state

    # ---- internals -----------------------------------------------------

    def _alive(self, state: dict) -> bool:
        if state.get("pid") == os.getpid():
            return self._thread is not None and self._thread.is_alive()
        try:
            beat = datetime.fromisoformat(state.get("heartbeat") or "")
        except ValueError:
            return False
        return datetime.now(timezone.utc) - beat < timedelta(seconds=HEARTBEAT_STALE_SECONDS)

    def _zip_target(self, folder: str) -> str:
        stamp = datetime.now().strftime("%Y-%m-%dT%H%M")
        path = os.path.join(folder, f"rastatime-backup-{stamp}.zip")
        n = 2
        while os.path.exists(path):
            path = os.path.join(folder, f"rastatime-backup-{stamp}-{n}.zip")
            n += 1
        return path

    def _run(self, state: dict, folder: str) -> None:
        target = self._zip_target(folder)
        try:
            argv, env = _pg_dump_command()
            config_files = sorted(
                p for p in Path(config_dir()).glob("*") if p.is_file()
            ) if os.path.isdir(config_dir()) else []
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
                self._dump_database(zf, argv, env, state)
                for cfg in config_files:
                    zf.write(cfg, f"config/{cfg.name}")
                manifest = {
                    "created_at": _now(),
                    "database": settings.DATABASES["default"].get("NAME"),
                    "pg_dump": _pg_dump_version(argv[0]),
                    "contents": ["db.dump"] + [f"config/{c.name}" for c in config_files],
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            state.update(file=os.path.basename(target), bytes=os.path.getsize(target))
            save_state(state)
            if state.get("include_media"):
                self._size_media(state, folder)
                self._mirror_media(state, folder)
                if self._cancel.is_set():
                    state.update(state="cancelled", finished_at=_now(),
                                 error="Cancelled by the operator - the database ZIP is "
                                       "complete, the media mirror keeps what was copied "
                                       "so far and the next run resumes there.")
                    save_state(state)
                    return
            state.update(state="done", phase=None, finished_at=_now())
            if state.get("include_media"):
                state["media_synced_at"] = _now()
            save_state(state)
            logger.info("backup done: %s (%d bytes)", target, state["bytes"])
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("backup failed: %s", exc)
            try:
                # No half ZIPs in the list; a partial media MIRROR stays -
                # it is incremental by design and the next run resumes it.
                if state.get("phase") == "database" and os.path.isfile(target):
                    os.remove(target)
            except OSError:
                pass
            state.update(state="failed", finished_at=_now(), error=str(exc))
            save_state(state)
        finally:
            connection.close()

    # RASTATIME 2026-10-28 - every long step of the media phase (sizing,
    # robocopy, verifying) runs under a heartbeat thread: the status view
    # declares a job without a heartbeat for HEARTBEAT_STALE_SECONDS
    # "interrupted", and a single os.walk over 100k+ files on a USB disk
    # takes longer than that.
    def _heartbeat(self, state: dict, stop: threading.Event) -> None:
        while not stop.wait(PROGRESS_INTERVAL_SECONDS):
            state["heartbeat"] = _now()
            try:
                save_state(state)
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    def _with_heartbeat(self, state: dict, work):
        stop = threading.Event()
        beat = threading.Thread(target=self._heartbeat, args=(state, stop), name="backup-heartbeat", daemon=True)
        beat.start()
        try:
            return work()
        finally:
            stop.set()
            beat.join(timeout=PROGRESS_INTERVAL_SECONDS * 2)

    def _size_media(self, state: dict, folder: str) -> None:
        """Library and mirror sizes plus the free-space check, in the job thread."""
        source = state.get("media_source") or storage_root.get_storage_root(refresh=True)
        mirror = media_mirror_dir(folder)
        state.update(phase="sizing", heartbeat=_now())
        save_state(state)

        def work():
            files, total = storage_root.library_size(source, refresh=True)
            done_files, done_bytes = (
                storage_root.walk_size(mirror) if os.path.isdir(mirror) else (0, 0)
            )
            return files, total, done_files, done_bytes

        files, total, done_files, done_bytes = self._with_heartbeat(state, work)
        try:
            free = shutil.disk_usage(folder).free
        except OSError:
            free = state.get("media_free_bytes") or 0
        needed = max(int(total * 1.1) - done_bytes, 0) + FREE_BYTES_MIN
        state.update(media_total_files=files, media_total_bytes=total,
                     media_done_files=done_files, media_done_bytes=done_bytes,
                     media_free_bytes=free, heartbeat=_now())
        save_state(state)
        if free and free < needed:
            raise RuntimeError(
                f"Not enough free space for the media mirror: "
                f"{free // 1048576} MB free, {needed // 1048576} MB needed. "
                f"The database ZIP is complete."
            )

    def _mirror_media(self, state: dict, folder: str) -> None:
        """robocopy /MIR the library into <folder>/media, then verify."""
        from . import move as storage_move  # noqa: PLC0415 (sibling, no cycle)

        source = state.get("media_source") or storage_root.get_storage_root(refresh=True)
        mirror = media_mirror_dir(folder)
        state.update(phase="media", heartbeat=_now())
        save_state(state)
        cmd = [
            ROBOCOPY, str(Path(source)), str(Path(mirror)),
            "/MIR", "/COPY:DAT", "/DCOPY:T", "/R:2", "/W:2",
            "/NP", "/NJH", "/NJS", "/NDL", "/NFL",
            "/XD", "$RECYCLE.BIN", "System Volume Information",
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(  # noqa: S603
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags,
        )

        def progress(proc):
            # one walk after the other while robocopy runs; on a slow disk a
            # walk takes minutes, so the figures are coarse but never block
            # the heartbeat
            while proc.poll() is None:
                files, done = storage_root.walk_size(mirror)
                state.update(media_done_files=files, media_done_bytes=done)
                if proc.poll() is None:
                    time.sleep(PROGRESS_INTERVAL_SECONDS)

        def copy():
            proc = self._proc
            walker = threading.Thread(target=progress, args=(proc,), name="backup-progress", daemon=True)
            walker.start()
            out = proc.communicate()[0] if proc.stdout else b""
            walker.join(timeout=PROGRESS_INTERVAL_SECONDS * 2)
            return (out or b"").decode("utf-8", "replace"), proc.returncode

        try:
            output, rc = self._with_heartbeat(state, copy)
        finally:
            self._proc = None
        if self._cancel.is_set():
            return
        if rc is None or rc >= 8:
            tail = output.strip().splitlines()[-3:]
            raise RuntimeError(f"robocopy exit code {rc}: {' | '.join(tail)}")
        state.update(phase="verifying", heartbeat=_now())
        save_state(state)
        problems = self._with_heartbeat(state, lambda: storage_move.verify_copy(source, mirror))
        if problems:
            raise RuntimeError("media mirror incomplete: " + ", ".join(problems[:5]))
        files, done = self._with_heartbeat(state, lambda: storage_root.walk_size(mirror))
        state.update(media_done_files=files, media_done_bytes=done, heartbeat=_now())
        save_state(state)

    def _dump_database(self, zf: zipfile.ZipFile, argv: list, env: dict, state: dict) -> None:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(  # noqa: S603
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, creationflags=flags,
        )
        try:
            last_beat = 0.0
            with zf.open("db.dump", "w") as member:
                while True:
                    chunk = proc.stdout.read(CHUNK)
                    if not chunk:
                        break
                    member.write(chunk)
                    now = time.monotonic()
                    if now - last_beat > 2.0:      # heartbeat, not a write storm
                        last_beat = now
                        state.update(heartbeat=_now())
                        save_state(state)
            stderr = (proc.stderr.read() or b"").decode("utf-8", "replace")
            rc = proc.wait(timeout=60)
        finally:
            if proc.poll() is None:
                proc.kill()
        if rc != 0:
            tail = " | ".join(stderr.strip().splitlines()[-3:])
            raise RuntimeError(f"pg_dump exit code {rc}: {tail}")


JOB = BackupJob()
