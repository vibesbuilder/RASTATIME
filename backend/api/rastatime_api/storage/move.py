"""
RASTATIME 2026-09-16 - moving the media library to another location
(Settings -> Local Machine -> Media Library Location).

The job copies the library with robocopy (resumable: a second run skips
what is already there), verifies that every source file exists at the
target with the same size and that every ``cc_files`` path resolves there,
then switches the root setting.  The old copy stays where it is - the
operator deletes it by hand (decision 2026-09-16).  Local drives only;
network paths are refused.

State lives in the site preference ``local_storage_move`` as JSON so the
Local Machine page, the PHP import guard and a restarted API all see the
same thing::

    {"state": "idle|copying|verifying|switched|failed|cancelled|interrupted",
     "source": ..., "target": ..., "started_at": ..., "finished_at": ...,
     "total_files": n, "total_bytes": n, "done_files": n, "done_bytes": n,
     "error": null|"...", "old_copy": null|"...", "pid": n, "heartbeat": iso}

While the state is ``copying`` or ``verifying`` imports are paused: PHP
refuses uploads, the import-folder scan skips, podcast downloads answer
409.  A job whose process died (API restart) shows as ``interrupted``;
starting again resumes the copy.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from django.db import connection

from . import root as storage_root

logger = logging.getLogger(__name__)

ACTIVE_STATES = ("copying", "verifying")
HEARTBEAT_STALE_SECONDS = 45
PROGRESS_INTERVAL_SECONDS = 3.0
ROBOCOPY = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "Robocopy.exe")
RESERVE_BYTES = 100 * 1024 * 1024


class MoveInProgress(Exception):
    pass


class InvalidTarget(ValueError):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state() -> dict:
    raw = storage_root.read_setting(storage_root.MOVE_STATE_KEY)
    if not raw:
        return {"state": "idle"}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"state": "idle"}
    return data if isinstance(data, dict) and data.get("state") else {"state": "idle"}


def save_state(state: dict) -> None:
    storage_root.write_setting(storage_root.MOVE_STATE_KEY, json.dumps(state))


def validate_target(target: str, source: str, library_bytes: int) -> dict:
    """Checks a candidate location; never raises, returns ok/errors/space."""
    errors: List[str] = []
    t = storage_root.normalize(target)
    s = storage_root.normalize(source)
    if not t:
        errors.append("Enter a folder path.")
    elif t.startswith("//"):
        errors.append("Network paths are not supported - use a local drive.")
    elif not re.match(r"^[A-Za-z]:/", t):
        errors.append("Enter an absolute path on a local drive, for example D:/stor.")
    free = needed = 0
    if not errors:
        drive = t[:3]
        if not os.path.isdir(drive):
            errors.append(f"Drive {t[:2]} does not exist.")
        elif t.lower() == s.lower():
            errors.append("That is already the current location.")
        elif t.lower().startswith(s.lower().rstrip("/") + "/"):
            errors.append("The new location must not lie inside the current one.")
        elif s.lower().startswith(t.lower().rstrip("/") + "/"):
            errors.append("The current location lies inside the new one.")
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
            needed = int(library_bytes * 1.1) + RESERVE_BYTES
            if free < needed:
                errors.append(
                    f"Not enough free space: {free // 1048576} MB free, "
                    f"{needed // 1048576} MB needed."
                )
    return {"ok": not errors, "errors": errors, "target": t, "free_bytes": free, "needed_bytes": needed}


def verify_copy(source: str, target: str, limit: int = 20) -> List[str]:
    """Relative paths missing at the target or differing in size."""
    problems: List[str] = []
    src = Path(source)
    for dirpath, _dirs, names in os.walk(source):
        for name in names:
            spath = Path(dirpath) / name
            rel = spath.relative_to(src)
            tpath = Path(target) / rel
            try:
                if not tpath.is_file() or tpath.stat().st_size != spath.stat().st_size:
                    problems.append(rel.as_posix())
            except OSError:
                problems.append(rel.as_posix())
            if len(problems) >= limit:
                return problems
    return problems


def unresolvable_db_paths(target: str, limit: int = 20) -> List[str]:
    from .models import File  # noqa: PLC0415

    missing: List[str] = []
    for filepath in File.objects.exclude(filepath__isnull=True).exclude(filepath="").values_list("filepath", flat=True):
        if not (Path(target) / filepath.lstrip("/")).is_file():
            missing.append(filepath)
            if len(missing) >= limit:
                break
    return missing


class MoveJob:
    """One job per API process; the persisted state is the truth."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._proc: Optional[subprocess.Popen] = None
        self._cancel = threading.Event()

    # ---- public --------------------------------------------------------

    def status(self) -> dict:
        state = load_state()
        if state.get("state") in ACTIVE_STATES and not self._alive(state):
            state["state"] = "interrupted"
            state["error"] = "The move was interrupted (service restart) - start it again to resume."
            state["finished_at"] = _now()
            save_state(state)
        return state

    def is_locked(self) -> bool:
        return self.status().get("state") in ACTIVE_STATES

    def start(self, target: str) -> dict:
        with self._lock:
            current = self.status()
            if current.get("state") in ACTIVE_STATES:
                raise MoveInProgress("a move is already running")
            source = storage_root.get_storage_root(refresh=True)
            files, total = storage_root.library_size(source, refresh=True)
            check = validate_target(target, source, total)
            if not check["ok"]:
                raise InvalidTarget(check["errors"])
            state = {
                "state": "copying", "source": source, "target": check["target"],
                "started_at": _now(), "finished_at": None,
                "total_files": files, "total_bytes": total, "done_files": 0, "done_bytes": 0,
                "error": None, "old_copy": None, "pid": os.getpid(), "heartbeat": _now(),
            }
            save_state(state)
            self._cancel.clear()
            self._thread = threading.Thread(target=self._run, args=(state,), name="storage-move", daemon=True)
            self._thread.start()
            return state

    def cancel(self) -> dict:
        with self._lock:
            state = self.status()
            if state.get("state") == "copying" and self._proc is not None and self._proc.poll() is None:
                self._cancel.set()
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

    def _run(self, state: dict) -> None:
        source, target = state["source"], state["target"]
        try:
            self._copy(state, source, target)
            if self._cancel.is_set():
                state.update(state="cancelled", finished_at=_now(),
                             error="Cancelled by the operator - the target keeps what was copied so far.")
                save_state(state)
                return
            state.update(state="verifying", heartbeat=_now())
            save_state(state)
            problems = verify_copy(source, target)
            if problems:
                raise RuntimeError("copy incomplete: " + ", ".join(problems[:5]))
            missing = unresolvable_db_paths(target)
            if missing:
                raise RuntimeError("library files missing at the target: " + ", ".join(missing[:5]))
            storage_root.set_storage_root_setting(target)
            state.update(state="switched", finished_at=_now(), old_copy=source,
                         done_files=state["total_files"], done_bytes=state["total_bytes"])
            save_state(state)
            logger.info("storage move: library now at %s (old copy left at %s)", target, source)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("storage move failed: %s", exc)
            state.update(state="failed", finished_at=_now(), error=str(exc))
            save_state(state)
        finally:
            connection.close()

    def _copy(self, state: dict, source: str, target: str) -> None:
        cmd = [
            ROBOCOPY, str(Path(source)), str(Path(target)),
            "/E", "/COPY:DAT", "/DCOPY:T", "/R:2", "/W:2", "/NP", "/NJH", "/NJS", "/NDL", "/NFL",
            "/XD", "$RECYCLE.BIN", "System Volume Information",
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(  # noqa: S603
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags,
        )
        try:
            while self._proc.poll() is None:
                time.sleep(PROGRESS_INTERVAL_SECONDS)
                files, done = storage_root.walk_size(target)
                state.update(done_files=files, done_bytes=done, heartbeat=_now())
                save_state(state)
            output = (self._proc.stdout.read() or b"").decode("utf-8", "replace") if self._proc.stdout else ""
            rc = self._proc.returncode
        finally:
            self._proc = None
        if self._cancel.is_set():
            return
        if rc is None or rc >= 8:
            tail = output.strip().splitlines()[-3:]
            raise RuntimeError(f"robocopy exit code {rc}: {' | '.join(tail)}")


JOB = MoveJob()
