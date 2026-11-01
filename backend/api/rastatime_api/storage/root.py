"""
RASTATIME 2026-09-16 - the media library's storage root as a setting.

The root used to live only in ``rastatime.conf`` (``storage.path``).  Since
stage 1 every stored path is relative to the root, so the root can be an
operator setting (Settings -> Local Machine -> Media Library Location):
the site preference ``local_storage_folder`` wins when set, the
configuration file is the initial value and the fallback.  PHP resolves the
same way per request (``Application_Common_Storage::root()``); the playout
asks ``GET /api/v2/storage/location`` on every refresh.

Readers call :func:`get_storage_root`; the value is cached for a few
seconds because the file views resolve it on every download.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

from django.conf import settings

STORAGE_ROOT_KEY = "local_storage_folder"
MOVE_STATE_KEY = "local_storage_move"
ROOT_CACHE_SECONDS = 15.0
# RASTATIME 2026-10-10 - the library size is served from the cache and
# recounted in the background once it is older than this; a GET never
# waits for the walk any more (198k files = 2 s, every playout refresh paid
# it and armed its start timers 2 s late).  Only the very first count after
# a start, and ``refresh=True`` (move validation), walk synchronously.
SIZE_CACHE_SECONDS = 900.0

_lock = threading.Lock()
_root_cache: tuple[float, Optional[str]] = (0.0, None)
_size_cache: dict = {}
_size_refreshing: set = set()


def normalize(path: str) -> str:
    """Forward slashes, no trailing slash (``D:/stor``); '' stays ''."""
    value = (path or "").strip().replace("\\", "/")
    while value.endswith("/") and len(value) > 3:
        value = value[:-1]
    if len(value) == 2 and value[1] == ":":
        value += "/"
    return value


def config_root() -> str:
    """The configuration value as configured (the API joined it raw before)."""
    return str(settings.CONFIG.storage.path)


def read_setting(key: str) -> Optional[str]:
    from ..core.models import Preference  # noqa: PLC0415

    row = Preference.site.filter(key=key).values_list("value", flat=True).first()
    if row is None:
        return None
    value = str(row).strip()
    return value or None


def write_setting(key: str, value: Optional[str]) -> None:
    from ..core.models import Preference  # noqa: PLC0415

    Preference.site.update_or_create(key=key, defaults={"value": value or ""})


def setting_root() -> Optional[str]:
    value = read_setting(STORAGE_ROOT_KEY)
    return normalize(value) if value else None


def invalidate() -> None:
    global _root_cache  # noqa: PLW0603
    with _lock:
        _root_cache = (0.0, None)
        _size_cache.clear()


def get_storage_root(refresh: bool = False) -> str:
    """The effective root: the setting when set, else the configuration."""
    global _root_cache  # noqa: PLW0603
    now = time.monotonic()
    with _lock:
        stamp, cached = _root_cache
        if not refresh and cached is not None and now - stamp < ROOT_CACHE_SECONDS:
            return cached
    root = setting_root() or config_root()
    with _lock:
        _root_cache = (now, root)
    return root


def set_storage_root_setting(path: Optional[str]) -> None:
    """Persist the setting ('' or None = back to the configuration value)."""
    write_setting(STORAGE_ROOT_KEY, normalize(path) if path else "")
    invalidate()


def walk_size(root: str) -> tuple[int, int]:
    """(files, bytes) below ``root``; missing root -> (0, 0)."""
    files = total = 0
    for _dirpath, _dirs, names in os.walk(root):
        for name in names:
            files += 1
            try:
                total += os.path.getsize(os.path.join(_dirpath, name))
            except OSError:
                pass
    return files, total


def _recount(root: str) -> None:
    """Background recount for library_size (one walker per root)."""
    try:
        size = walk_size(root)
        with _lock:
            _size_cache[root.lower()] = (time.monotonic(), size)
    finally:
        with _lock:
            _size_refreshing.discard(root.lower())


def library_size(root: Optional[str] = None, refresh: bool = False) -> tuple[int, int]:
    """
    (files, bytes) below the root.  Served from the cache; a stale entry
    (older than SIZE_CACHE_SECONDS) is returned at once and recounted in a
    background thread.  ``refresh=True`` walks synchronously.
    """
    root = normalize(root or get_storage_root())
    key = root.lower()
    now = time.monotonic()
    with _lock:
        entry = _size_cache.get(key)
        if entry and not refresh:
            if now - entry[0] >= SIZE_CACHE_SECONDS and key not in _size_refreshing:
                _size_refreshing.add(key)
                threading.Thread(
                    target=_recount, args=(root,), name="library-size", daemon=True
                ).start()
            return entry[1]
    size = walk_size(root)
    with _lock:
        _size_cache[key] = (time.monotonic(), size)
    return size


def library_size_age(root: Optional[str] = None) -> Optional[float]:
    """Seconds since the cached library size was counted; None = not yet."""
    root = normalize(root or get_storage_root())
    with _lock:
        entry = _size_cache.get(root.lower())
    return None if entry is None else time.monotonic() - entry[0]


def root_info() -> dict:
    """What the UI shows: effective root, where it comes from, health."""
    setting = setting_root()
    config = config_root()
    root = setting or config
    exists = os.path.isdir(root)
    writable = exists and os.access(root, os.W_OK)
    return {
        "root": root,
        "source": "setting" if setting else "config",
        "setting_root": setting or "",
        "config_root": config,
        "exists": exists,
        "writable": writable,
    }
