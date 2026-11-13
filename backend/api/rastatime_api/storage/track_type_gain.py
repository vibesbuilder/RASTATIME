"""
RASTATIME 2026-11-13 - fixed gain per track type (legacy migration 0083).

A track type may switch the loudness analysis off
(``cc_track_types.analyze_loudness = FALSE``); its tracks then play with
the type's ``fixed_gain_db`` instead of the measured adjustment.  The file
serializer hands the value to the playout as ``track_type_fixed_gain_db``
(null for every other type).

The two columns are read through ``to_jsonb(cc_track_types)``, which simply
yields NULL for a column that does not exist yet: this code may run before
the migration, and the API may restart before or after it.  The answer is
cached for a few seconds - a schedule fetch of the playout asks for dozens
of files in a row.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from django.db import connection

logger = logging.getLogger(__name__)

CACHE_SECONDS = 5.0
GAIN_LIMIT_DB = 30.0

_SQL = """
SELECT t.id, to_jsonb(t) ->> 'fixed_gain_db'
FROM cc_track_types t
WHERE to_jsonb(t) ->> 'analyze_loudness' = 'false'
"""

_lock = threading.Lock()
_cached_at: float = 0.0
_cached: dict[int, float] = {}


def _parse_gain(raw) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if value != value:  # NaN
        return 0.0
    return max(-GAIN_LIMIT_DB, min(GAIN_LIMIT_DB, value))


def fixed_gains() -> dict[int, float]:
    """``{track type id: gain in dB}`` of the types with the analysis off."""
    global _cached_at, _cached  # noqa: PLW0603
    now = time.monotonic()
    with _lock:
        if _cached_at and now - _cached_at < CACHE_SECONDS:
            return _cached
    try:
        with connection.cursor() as cursor:
            cursor.execute(_SQL)
            gains = {int(type_id): _parse_gain(raw) for type_id, raw in cursor.fetchall()}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("fixed gain per track type not readable: %s", exc)
        gains = {}
    with _lock:
        _cached, _cached_at = gains, now
    return gains


def fixed_gain_for(track_type_id: Optional[int]) -> Optional[float]:
    """The fixed gain of a file's track type, or None when the type measures."""
    if not track_type_id:
        return None
    return fixed_gains().get(int(track_type_id))


def clear_cache() -> None:
    """For tests: forget the cached answer."""
    global _cached_at, _cached  # noqa: PLW0603
    with _lock:
        _cached_at, _cached = 0.0, {}
