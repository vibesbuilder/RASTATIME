"""
Public listener song-request intake API.

RASTATIME 2026-06-07 — Song Requests, Phase 3 (Django intake).

GET  /api/v2/song-requests/search?q=<text>
    Public catalogue search.  Returns up to SEARCH_LIMIT tracks from the
    operator-defined "Requestable Pool" (cc_files.requestable = true,
    maintained by the PHP sync task) whose title / artist / album match
    the query.  Read-only; throttled per IP (song_request_search rate).

POST /api/v2/song-requests
    Public request submission.  Body (JSON or form): ``file_id`` (int,
    required), ``listener_label`` (str, optional dedication).  Validates
    the track is requestable, de-duplicates (same track + same IP within
    DEDUP_WINDOW_MINUTES), records a SongRequest row and bumps the
    cc_files aggregate cache (requested / requested_at / request_count).
    Throttled per IP (song_request_submit rate).

Security notes
--------------
* These are the only PUBLIC, unauthenticated, *write*-capable endpoints
  in the app, so abuse mitigation is layered, not authenticated:
    - DRF per-IP throttle (flood protection),
    - per-track+IP de-duplication within a time window (vote stuffing),
    - the catalogue restriction (only cc_files.requestable tracks can be
      named — a listener can never inject arbitrary content, only nudge
      the ordering/frequency of the station's own library).
* No moderation step by operator decision (2026-06-07); the catalogue
  restriction is what makes that safe.
* The client IP is taken from X-Forwarded-For (the app sits behind
  Apache/Nginx) falling back to REMOTE_ADDR, and is stored only as a
  salted SHA-256 hash (never the raw IP).  XFF can be spoofed, which
  only weakens the per-IP heuristics — acceptable for this low-risk,
  catalogue-restricted feature.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.utils.timezone import now
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

# --- tunables (operator-approved defaults 2026-06-07) ----------------------
SEARCH_MIN_CHARS = 2
SEARCH_LIMIT = 25
AVAILABLE_LIMIT = 500  # whole-pool table listing cap (no query)
DEDUP_WINDOW_MINUTES = 30


class SongRequestSearchThrottle(AnonRateThrottle):
    """Per-IP throttle for the read-only catalogue search."""
    scope = "song_request_search"


class SongRequestSubmitThrottle(AnonRateThrottle):
    """Per-IP throttle for the write-capable request submission."""
    scope = "song_request_submit"


def _hash_ip(request) -> str:
    """
    Return a salted SHA-256 hash of the requester's IP, or "" if unknown.

    The raw IP is never stored or logged (privacy).  X-Forwarded-For wins
    over REMOTE_ADDR because the app runs behind Apache/Nginx; the first
    hop in the XFF list is the originating client.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
    if not ip:
        return ""
    salt = getattr(settings, "SECRET_KEY", "")
    return hashlib.sha256(f"{salt}|{ip}".encode("utf-8")).hexdigest()


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([SongRequestSearchThrottle])
def song_request_search(request):
    """
    List the requestable pool as slim track rows.  Without ``q`` (or a
    query shorter than SEARCH_MIN_CHARS) the WHOLE pool is returned (up to
    AVAILABLE_LIMIT) — this is what the table-view widget uses.  With a
    query the pool is filtered (up to SEARCH_LIMIT).
    """
    q = (request.GET.get("q") or "").strip()

    where = "WHERE requestable = true AND file_exists = true AND disabled = false "
    params = []
    if len(q) >= SEARCH_MIN_CHARS:
        like = f"%{q}%"
        where += (
            "AND (track_title ILIKE %s OR artist_name ILIKE %s "
            "OR album_title ILIKE %s) "
        )
        params += [like, like, like]
        limit = SEARCH_LIMIT
    else:
        limit = AVAILABLE_LIMIT
    params.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, track_title, artist_name, album_title FROM cc_files "
            + where
            + "ORDER BY artist_name, track_title LIMIT %s",
            params,
        )
        rows = cursor.fetchall()

    results = [
        {"id": r[0], "title": r[1] or "", "artist": r[2] or "", "album": r[3] or ""}
        for r in rows
    ]
    return Response({"results": results})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([SongRequestSubmitThrottle])
def song_request_submit(request):
    """Submit a listener request for a requestable track."""
    from libretime_api.song_request.models import SongRequest  # lazy

    data = request.data if isinstance(request.data, dict) else {}

    try:
        file_id = int(data.get("file_id"))
    except (TypeError, ValueError):
        return Response({"error": "file_id (integer) is required."}, status=400)

    listener_label = (str(data.get("listener_label") or "")).strip()[:128]
    ip_hash = _hash_ip(request)

    # 1. The track must exist, be requestable, present on disk and not expired.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT track_title, artist_name FROM cc_files "
            "WHERE id = %s AND requestable = true "
            "  AND file_exists = true AND disabled = false",
            [file_id],
        )
        row = cursor.fetchone()
    if row is None:
        return Response(
            {"error": "This track is not available for requests."}, status=404
        )

    # 2. De-duplicate: same track + same IP with an open request in the window.
    if ip_hash:
        window_start = now() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        already = SongRequest.objects.filter(
            file_id=file_id,
            ip_hash=ip_hash,
            created_at__gte=window_start,
            status__in=[SongRequest.Status.PENDING, SongRequest.Status.QUEUED],
        ).exists()
        if already:
            return Response(
                {"error": "You already requested this track recently."},
                status=409,
            )

    # 3. Record the request and bump the per-track aggregate cache atomically.
    with transaction.atomic():
        SongRequest.objects.create(
            file_id=file_id,
            listener_label=listener_label,
            ip_hash=ip_hash,
            status=SongRequest.Status.PENDING,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE cc_files "
                "SET requested = true, requested_at = NOW(), "
                "    request_count = request_count + 1 "
                "WHERE id = %s",
                [file_id],
            )

    return Response(
        {"ok": True, "title": row[0] or "", "artist": row[1] or ""}, status=201
    )
