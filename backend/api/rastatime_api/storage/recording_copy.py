"""
RASTATIME 2026-11-14 - copy finished show recordings to a second folder.

Settings -> Local Machine -> Show Recording -> "Copy finished recordings
to": the folder (usually on a network drive) where the show makers pick up
their recordings.  ``manage.py recording_copy`` - fired every two minutes
by the Windows task RASTATIME-RecordingCopy, which runs under an account
that may write there (the services run as SYSTEM and may not) - copies
every recording that

  * was finished after the setting was switched on (``..._since``),
  * is not being written any more (no other process has it open, and its
    last write is a few seconds old),
  * has not been copied before (ledger), so a file a show maker moved away
    from the target is not put back,

flat into the target: first as ``<name>.part``, then renamed, so nobody
picks up half a file.  Nothing is ever deleted or overwritten at the
target; a name that is taken by a different file gets " (2)".

The result of every run is stored as JSON in ``cc_pref`` (status line of
the settings page).  The functions below take plain paths and dicts, so
they are testable without a database; only :func:`run_from_settings`
touches the settings.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

SOURCE_KEY = "local_recording_folder"
TARGET_KEY = "local_recording_copy_folder"
SINCE_KEY = "local_recording_copy_since"
STATE_KEY = "local_recording_copy_state"

AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".opus"})
#: Liquidsoap's start-up sentinel and aborted recordings are tiny.
MIN_BYTES = 64 * 1024
#: A file whose last write is younger than this may still be flushed.
SETTLE_SECONDS = 15.0
PART_SUFFIX = ".part"
COPY_CHUNK = 1024 * 1024
MAX_MESSAGE = 300


def utc_iso(ts: Optional[float] = None) -> str:
    moment = datetime.fromtimestamp(time.time() if ts is None else ts, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value) -> Optional[float]:
    """Epoch seconds of an ISO-8601 UTC text ("...Z"), None when unreadable."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()


def is_locked(path: Path) -> bool:
    """
    True while another process has the file open for WRITING (Windows):
    an open that shares reading only fails with a sharing violation then.
    Liquidsoap keeps the recording open until the show ends.  Readers (the
    library import, a virus scanner) do not count and are not disturbed by
    the probe.  Elsewhere there is no such test; the settle time alone
    decides.
    """
    if sys.platform != "win32":
        return False
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    generic_read, share_read, open_existing = 0x80000000, 0x1, 3
    handle = kernel32.CreateFileW(str(path), generic_read, share_read, None, open_existing, 0, None)
    if handle == wintypes.HANDLE(-1).value:
        return True
    kernel32.CloseHandle(wintypes.HANDLE(handle))
    return False


def ledger_key(source: Path, path: Path) -> str:
    return path.relative_to(source).as_posix()


def find_candidates(
    source: Path,
    since: float,
    ledger: dict,
    now: float,
    locked: Callable[[Path], bool] = is_locked,
) -> list[Path]:
    """The finished recordings that have not been copied yet, oldest first."""
    found: list[tuple[float, Path]] = []
    for root, _dirs, files in os.walk(source):
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size < MIN_BYTES or stat.st_mtime < since:
                continue
            if now - stat.st_mtime < SETTLE_SECONDS:
                continue
            if ledger_key(source, path) in ledger:
                continue
            if locked(path):
                continue
            found.append((stat.st_mtime, path))
    return [path for _mtime, path in sorted(found)]


def free_target_name(target: Path, name: str, size: int) -> tuple[Optional[str], bool]:
    """
    ``(file name to write, already_there)``.  A file of this name and size
    at the target counts as copied (nothing is written); a different file
    of this name is never overwritten - the copy gets " (2)", " (3)", ...
    """
    stem, suffix = os.path.splitext(name)
    candidate = name
    for number in range(2, 100):
        existing = target / candidate
        if not existing.exists():
            return candidate, False
        try:
            if existing.stat().st_size == size:
                return None, True
        except OSError:
            pass
        candidate = f"{stem} ({number}){suffix}"
    raise OSError(f"no free name for {name} in {target}")


def copy_one(path: Path, target: Path) -> tuple[str, int, bool]:
    """
    Copy one recording flat into ``target``; ``(name at the target, bytes,
    written)``.  Written as ``<name>.part`` and renamed when complete.
    """
    size = path.stat().st_size
    name, already_there = free_target_name(target, path.name, size)
    if already_there:
        return path.name, size, False
    part = target / (name + PART_SUFFIX)
    try:
        if part.exists():
            part.unlink()  # our own leftover of an interrupted run
        with open(path, "rb") as src, open(part, "wb") as dst:
            shutil.copyfileobj(src, dst, COPY_CHUNK)
        written = part.stat().st_size
        if written != size:
            raise OSError(f"copied {written} of {size} bytes")
        try:
            stat = path.stat()
            os.utime(part, (stat.st_atime, stat.st_mtime))
        except OSError:
            pass
        os.replace(part, target / name)
    except OSError:
        try:
            if part.exists():
                part.unlink()
        except OSError:
            pass
        raise
    return name, size, True


def empty_state() -> dict:
    return {
        "version": 1,
        "last_run": None,
        "ok": None,
        "message": "",
        "pending": 0,
        "last_file": None,
        "last_copied_at": None,
        "copied_total": 0,
        "ledger": {},
    }


def load_state(raw) -> dict:
    state = empty_state()
    try:
        data = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        data = None
    if isinstance(data, dict):
        for key in state:
            if key in data:
                state[key] = data[key]
    if not isinstance(state["ledger"], dict):
        state["ledger"] = {}
    return state


def run(
    source: Optional[str],
    target: Optional[str],
    since: float,
    state: dict,
    now: Optional[float] = None,
    log: Callable[[str], None] = lambda _line: None,
    locked: Callable[[Path], bool] = is_locked,
) -> dict:
    """One pass; returns the new state (the old one is not modified)."""
    now = time.time() if now is None else now
    new = load_state(json.dumps(state))
    new["last_run"] = utc_iso(now)
    new["pending"] = 0

    def fail(message: str) -> dict:
        new["ok"] = False
        new["message"] = message[:MAX_MESSAGE]
        log(f"ERROR {message}")
        return new

    if not source or not os.path.isdir(source):
        return fail(f"recording folder not reachable: {source or '(not set)'}")
    if not target or not os.path.isdir(target):
        return fail(f"target folder not reachable: {target or '(not set)'}")
    source_path, target_path = Path(source), Path(target)

    # entries of recordings that are gone from the recording folder
    for key in [k for k in new["ledger"] if not (source_path / k).exists()]:
        del new["ledger"][key]

    todo = find_candidates(source_path, since, new["ledger"], now, locked)
    errors: list[str] = []
    for index, path in enumerate(todo):
        try:
            name, size, written = copy_one(path, target_path)
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
            log(f"ERROR {path.name}: {exc}")
            new["pending"] = len(todo) - index
            break  # the target is probably gone; the next run tries again
        new["ledger"][ledger_key(source_path, path)] = {"at": utc_iso(now), "size": size}
        new["last_file"] = name
        new["last_copied_at"] = utc_iso(now)
        new["copied_total"] = int(new.get("copied_total") or 0) + 1
        log(
            f"copied {name} ({size} bytes)"
            if written
            else f"already at the target, not copied again: {name}"
        )
    new["ok"] = not errors
    new["message"] = errors[0][:MAX_MESSAGE] if errors else ""
    return new


def run_from_settings(log: Callable[[str], None] = lambda _line: None) -> Optional[dict]:
    """
    Read the settings, run one pass, store the state.  None when the copy
    is switched off (no target folder set) - nothing is read or written
    beyond the two settings then.
    """
    from . import root as storage_root  # noqa: PLC0415

    target = (storage_root.read_setting(TARGET_KEY) or "").strip()
    if not target:
        return None
    source = (storage_root.read_setting(SOURCE_KEY) or "").strip()
    since = parse_utc(storage_root.read_setting(SINCE_KEY))
    if since is None:
        # switched on without a start mark: from now on only
        since = time.time()
        storage_root.write_setting(SINCE_KEY, utc_iso(since))
    state = load_state(storage_root.read_setting(STATE_KEY))
    new = run(source, target.rstrip("\\/") or target, since, state, log=log)
    storage_root.write_setting(STATE_KEY, json.dumps(new))
    return new
