"""
Now-playing API endpoint.

GET /api/v2/now-playing
    Returns a JSON snapshot of what is on air right now, read from the
    schedule in the database (the same source the embed widgets and the
    legacy ``/api/live-info`` use).

RASTATIME 2026-11-05 (operator go, ARCHITECTURE 23.91) - the endpoint used
to read ``playout.now_playing.default_state``, a process-level singleton
that is only filled when the playout engine runs inside the API process.
In production they are two services, so it always answered "idle".

Response (always HTTP 200)::

    {
        "is_playing": true,
        "now": "2026-11-05T12:40:12+00:00",
        "source": "scheduled" | "live_dj" | "master_dj",
        "started_at": "2026-11-05T12:15:00+00:00",
        "item": {
            "type": "file" | "webstream" | "linein",
            "id": 25613,
            "title": "...", "artist": "...", "album": "...",
            "genre": "...", "year": "2024",
            "length_seconds": 1800.0,
            "starts_at": "...", "ends_at": "...",
            "has_artwork": false
        },
        "show": {"id": 1172, "name": "...", "description": "...", "url": "...",
                 "genre": "...", "starts_at": "...", "ends_at": "..."},
        "next": {<item fields>} | null
    }

Idle: ``{"is_playing": false, "item": null, "started_at": null, "show": ...,
"next": ..., "source": ..., "now": ...}``.  The public track fields match
``WidgetHelper::PUBLIC_TRACK_FIELDS`` of the legacy endpoints: credit
information only, no file paths, owners or checksums.

The view never raises: any database or playout error degrades to the idle
shape (the contract tests run it without a database).
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

PLAYOUT_STATE_URL = "http://127.0.0.1:8770/source-state"
PLAYOUT_STATE_TIMEOUT = 0.5


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, UTC)
    return value.isoformat()


def _seconds(value: Optional[timedelta]) -> Optional[float]:
    return round(value.total_seconds(), 3) if value is not None else None


def item_from_schedule(row: Any) -> Optional[dict]:
    """
    The public shape of one cc_schedule row (file, webstream or line-in);
    None when the row carries nothing playable.  Pure function, unit tested
    with stand-ins.
    """
    base = {
        "starts_at": _iso(getattr(row, "starts_at", None)),
        "ends_at": _iso(getattr(row, "ends_at", None)),
    }
    file = getattr(row, "file", None)
    if file is not None:
        length = getattr(row, "length", None) or getattr(file, "length", None)
        return {
            "type": "file",
            "id": getattr(file, "id", None),
            "title": getattr(file, "track_title", None),
            "artist": getattr(file, "artist_name", None),
            "album": getattr(file, "album_title", None),
            "genre": getattr(file, "genre", None),
            "year": getattr(file, "date", None),
            "length_seconds": _seconds(length),
            "has_artwork": bool(getattr(file, "artwork", None)),
            **base,
        }
    stream = getattr(row, "stream", None)
    if stream is not None:
        return {
            "type": "webstream",
            "id": getattr(stream, "id", None),
            "title": getattr(stream, "name", None),
            "artist": None,
            "album": None,
            "genre": None,
            "year": None,
            "length_seconds": _seconds(getattr(row, "length", None)),
            "has_artwork": False,
            **base,
        }
    linein = getattr(row, "linein", None)
    if linein is not None:
        return {
            "type": "linein",
            "id": getattr(linein, "id", None),
            "title": getattr(linein, "name", None),
            "artist": None,
            "album": None,
            "genre": None,
            "year": None,
            "length_seconds": _seconds(getattr(row, "length", None)),
            "has_artwork": False,
            **base,
        }
    return None


def show_from_instance(instance: Any) -> Optional[dict]:
    if instance is None:
        return None
    show = getattr(instance, "show", None)
    return {
        "id": getattr(show, "id", None),
        "name": getattr(show, "name", None),
        "description": getattr(instance, "description", None) or getattr(show, "description", None),
        "url": getattr(show, "url", None),
        "genre": getattr(show, "genre", None),
        "starts_at": _iso(getattr(instance, "starts_at", None)),
        "ends_at": _iso(getattr(instance, "ends_at", None)),
    }


def playout_source(opener=None) -> str:
    """``live_dj`` / ``master_dj`` when the playout reports a connected DJ,
    else ``scheduled``.  Fail-soft: an unreachable playout means scheduled."""
    try:
        open_ = opener or (lambda req, timeout=None: urllib.request.urlopen(req, timeout=timeout))
        with open_(PLAYOUT_STATE_URL, timeout=PLAYOUT_STATE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # pylint: disable=broad-exception-caught
        return "scheduled"
    if data.get("master_connected"):
        return "master_dj"
    if data.get("show_connected"):
        return "live_dj"
    return "scheduled"


def _snapshot(now: datetime) -> dict:
    from .schedule.models import Schedule, ShowInstance  # noqa: PLC0415 - lazy, no DB at import

    rows = (
        Schedule.objects.select_related("file", "stream", "linein", "instance", "instance__show")
        .filter(starts_at__lte=now, ends_at__gt=now, instance__modified=False)
        .order_by("-starts_at")
    )
    current = next((r for r in rows if item_from_schedule(r) is not None), None)
    instance = (
        current.instance
        if current is not None
        else ShowInstance.objects.select_related("show")
        .filter(starts_at__lte=now, ends_at__gt=now, modified=False)
        .order_by("-starts_at")
        .first()
    )
    next_row = (
        Schedule.objects.select_related("file", "stream", "linein")
        .filter(starts_at__gt=now, instance__modified=False)
        .order_by("starts_at")
        .first()
    )
    item = item_from_schedule(current) if current is not None else None
    return {
        "is_playing": item is not None,
        "now": _iso(now),
        "source": playout_source(),
        "started_at": _iso(current.starts_at) if current is not None else None,
        "item": item,
        "show": show_from_instance(instance),
        "next": item_from_schedule(next_row) if next_row is not None else None,
    }


def idle(now: Optional[datetime] = None) -> dict:
    return {
        "is_playing": False,
        "now": _iso(now),
        "source": "scheduled",
        "started_at": None,
        "item": None,
        "show": None,
        "next": None,
    }


@require_GET
def now_playing(request: HttpRequest) -> JsonResponse:
    """
    Return the current on-air state as JSON.
    Always returns HTTP 200; ``is_playing`` distinguishes active from idle.
    """
    now = timezone.now()
    try:
        return JsonResponse(_snapshot(now))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("now-playing: schedule not readable (%s) - answering idle", exc)
        return JsonResponse(idle(now))
