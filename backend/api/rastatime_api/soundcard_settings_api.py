"""
Soundcard settings REST API.

GET  /api/v2/audio/soundcard-settings
    Returns the persisted operator soundcard settings as JSON.
    Creates the singleton row with defaults if not yet stored.

    If a device manager is connected to the process singleton
    (``audio.soundcard.connect_device_manager``), the response includes a
    ``missing_device_ids`` list — stable IDs of configured devices that are
    not currently available (e.g. unplugged).  When no manager is wired the
    list is always empty (cannot check).

POST /api/v2/audio/soundcard-settings
    Accepts a JSON body with any subset of:
        main_output_id    : string | null
        preview_output_id : string | null
        line_in_device_ids: list[string]
    Saves to the singleton DB row and returns the updated settings
    (including an updated ``missing_device_ids`` field).

Response shape (both verbs on success)
---------------------------------------
::

    {
        "main_output_id":    "9ab29437-d4ec-473d-9a94-1ad46a86e9ff",
        "preview_output_id": null,
        "line_in_device_ids": [],
        "missing_device_ids": []
    }

HTTP status codes
-----------------
200  GET success or POST success
400  POST body is not valid JSON or contains a structural error
405  Wrong method (Django's @require_http_methods handles this)
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rastatime_api.permissions import internal_only  # RASTATIME 2026-10-25 role audit S3/S4

logger = logging.getLogger(__name__)


def _push_audio_output_to_playout(stable_id: str) -> None:
    """
    Best-effort push of the new audio-output selection to the playout
    service's HTTP listener (default ``127.0.0.1:8770``).  This makes
    the switch take effect live, without a service restart.

    Failures are swallowed and logged at WARNING — the database row
    has already been persisted, so the new device will be picked up
    on the next playout-service start regardless.
    """
    url = "http://127.0.0.1:8770/set-audio-output"
    if stable_id:
        url += "?output_id=" + urllib.parse.quote(stable_id, safe="")
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            logger.info(
                "set-audio-output: pushed %r to playout -> HTTP %d",
                stable_id or "(default)", resp.status,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "set-audio-output: could not reach playout listener at %s "
            "(setting saved; will apply on next service start): %s",
            url, exc,
        )


def _orm_to_response(obj) -> dict:
    """
    Convert the ORM singleton to the base API response dict.

    Does not include ``missing_device_ids`` — that requires a live manager
    and is added by :func:`_build_response`.
    """
    return {
        "main_output_id":       obj.main_output_id    or None,
        "preview_output_id":    obj.preview_output_id or None,
        "line_in_device_ids":   list(obj.line_in_device_ids or []),
        # RASTATIME 2026-05-14 — B.4 #4 output side: friendly-name
        # fallback identifiers for when the saved stable_ids no longer
        # resolve after a reboot.  Empty string for legacy rows.
        "main_output_name":     obj.main_output_name    or "",
        "preview_output_name":  obj.preview_output_name or "",
    }


def _build_response(obj) -> dict:
    """
    Build the full API response, including ``missing_device_ids``.

    Attempts to run the startup availability check against the process-level
    device manager.  If no manager is connected the list is empty.
    """
    base = _orm_to_response(obj)

    import audio.soundcard._registry as _reg                  # lazy — avoids circular dep
    mgr = _reg.default_manager

    if mgr is None:
        base["missing_device_ids"] = []
        return base

    # Lazy import so Django startup doesn't pull in audio.soundcard._startup
    # before the manager is wired.
    from audio.soundcard._startup import check_devices_at_startup

    domain = obj.to_domain()
    result = check_devices_at_startup(domain, mgr)
    base["missing_device_ids"] = sorted(result.all_missing_ids)
    return base


@csrf_exempt                             # CSRF managed by RASTATIME's session auth layer
@require_http_methods(["GET", "POST"])
@internal_only
def soundcard_settings(request: HttpRequest) -> JsonResponse:
    """
    GET  — return persisted soundcard settings (creates defaults if absent).
    POST — update and return the new settings.
    """
    from rastatime_api.soundcard.models import SoundcardSettings  # lazy Django import

    if request.method == "GET":
        obj = SoundcardSettings.get_settings()
        return JsonResponse(_build_response(obj))

    # POST ----------------------------------------------------------------
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    obj = SoundcardSettings.get_settings()

    # Apply each field if present; ignore unknown keys.
    if "main_output_id" in body:
        raw = body["main_output_id"]
        if raw is not None and not isinstance(raw, str):
            return JsonResponse({"error": "main_output_id must be a string or null."}, status=400)
        obj.main_output_id = (raw or "")

    if "preview_output_id" in body:
        raw = body["preview_output_id"]
        if raw is not None and not isinstance(raw, str):
            return JsonResponse({"error": "preview_output_id must be a string or null."}, status=400)
        obj.preview_output_id = (raw or "")

    # RASTATIME 2026-05-14 — B.4 #4 output side: friendly-name persistence.
    # Both are optional strings (may be empty).  Older frontends won't
    # send them; that's OK, the name-fallback is then a no-op.
    if "main_output_name" in body:
        raw = body["main_output_name"]
        if raw is not None and not isinstance(raw, str):
            return JsonResponse({"error": "main_output_name must be a string."}, status=400)
        obj.main_output_name = (raw or "")

    if "preview_output_name" in body:
        raw = body["preview_output_name"]
        if raw is not None and not isinstance(raw, str):
            return JsonResponse({"error": "preview_output_name must be a string."}, status=400)
        obj.preview_output_name = (raw or "")

    if "line_in_device_ids" in body:
        raw = body["line_in_device_ids"]
        if not isinstance(raw, list):
            return JsonResponse({"error": "line_in_device_ids must be a list."}, status=400)
        if not all(isinstance(x, str) for x in raw):
            return JsonResponse({"error": "line_in_device_ids must be a list of strings."}, status=400)
        obj.line_in_device_ids = raw

    obj.save()

    # Push the (possibly new) main-output selection to the live playout
    # service so the playout re-routes immediately.  Only meaningful when
    # ``main_output_id`` was in the request body — other field changes
    # (line-ins, preview) don't affect the playback device.  Best-effort:
    # if the playout isn't running, the setting is still persisted and
    # will be picked up on the next service start.
    if "main_output_id" in body:
        _push_audio_output_to_playout(obj.main_output_id or "")

    return JsonResponse(_build_response(obj))
