"""
Pre-flight warnings REST API.

GET    /api/v2/preflight/warnings
    List all current pre-flight warnings, ordered by ``starts_at``
    (NULLs last) then ``id``.  Always HTTP 200.  Returns
    ``{"warnings": [...]}`` — empty list when no warnings outstanding.

    Read endpoint for the legacy PHP frontend's dashboard banner.

POST   /api/v2/preflight/warnings/replace
    Atomic per-type replacement of warnings.  Body:

        {
            "warning_type": "linein_device_unavailable",
            "scan_run_id":  "<uuid>",
            "warnings": [
                {
                    "severity":         "warning",
                    "show_id":          12,
                    "show_instance_id": 102,
                    "starts_at":        "2026-05-14T08:00:00Z",
                    "detail": {
                        "linein_id":   2,
                        "linein_name": "Jabra-Mikro",
                        "device_id":   "0fb...",
                        "show_name":   "Morgensendung"
                    }
                },
                ...
            ]
        }

    Writes happen in a single transaction: all previously-stored rows
    with the given ``warning_type`` are deleted, then the new batch is
    inserted.  ``warnings`` may be an empty list — that simply clears
    the type.  Returns HTTP 200 with ``{"inserted": <int>}``.

    Write endpoint for the playout service's pre-flight scanner.

Response shape (GET list)
-------------------------
::

    {"warnings": [{
        "id":               42,
        "created_at":       "2026-05-13T10:30:00Z",
        "warning_type":     "linein_device_unavailable",
        "severity":         "warning",
        "show_id":          12,
        "show_instance_id": 102,
        "starts_at":        "2026-05-14T08:00:00Z",
        "detail":           {...}
    }]}

HTTP status codes
-----------------
200  GET / POST success
400  Invalid request body (bad JSON, missing required field, wrong type)
405  Wrong HTTP method
"""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from libretime_api.permissions import internal_only  # RASTATIME 2026-10-25 role audit S3/S4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_warning(row) -> dict:
    """Convert a PreflightWarning ORM row to its JSON-API shape."""
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "warning_type": row.warning_type,
        "severity": row.severity,
        "show_id": row.show_id,
        "show_instance_id": row.show_instance_id,
        "starts_at": (
            row.starts_at.isoformat().replace("+00:00", "Z")
            if row.starts_at is not None else None
        ),
        "detail": row.detail or {},
    }


def _parse_starts_at(value: Any):
    """
    Accept ISO-8601 strings (with or without trailing ``Z``) and return a
    timezone-aware datetime, or None if value is None / empty.
    """
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("'starts_at' must be an ISO-8601 string or null.")
    from datetime import datetime, timezone   # lazy
    # Django/DRF clients commonly send "...Z"; Python <3.11 fromisoformat
    # cannot parse that suffix, so normalise to +00:00.
    normalised = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError as exc:
        raise ValueError(f"'starts_at' not a valid ISO-8601 datetime: {exc}") from exc
    # If the caller forgot the offset, assume UTC (the scanner runs in UTC
    # and the legacy frontend treats naive times as UTC).
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ---------------------------------------------------------------------------
# GET — list current warnings
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET"])
@internal_only
def preflight_warnings_list(request: HttpRequest) -> JsonResponse:
    """
    Return all current pre-flight warnings as a flat list.

    Sort order: ``starts_at`` ascending (NULLs last) then ``id``.  The
    frontend uses this directly for the dashboard banner — warnings
    closest to "now" appear first.
    """
    from libretime_api.preflight.models import PreflightWarning   # lazy

    # Postgres-friendly NULLS LAST via .order_by with F + nulls_last
    from django.db.models import F   # lazy
    rows = PreflightWarning.objects.order_by(
        F("starts_at").asc(nulls_last=True), "id",
    )
    return JsonResponse({"warnings": [_serialize_warning(r) for r in rows]})


# ---------------------------------------------------------------------------
# POST — atomic per-type replacement
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["POST"])
@internal_only
def preflight_warnings_replace(request: HttpRequest) -> JsonResponse:
    """
    Atomically replace all warnings of one ``warning_type`` with a new
    batch.  See module docstring for body schema.
    """
    from libretime_api.preflight.models import PreflightWarning   # lazy

    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    warning_type = body.get("warning_type")
    scan_run_id = body.get("scan_run_id")
    warnings_in = body.get("warnings", [])

    if not isinstance(warning_type, str) or not warning_type:
        return JsonResponse(
            {"error": "'warning_type' is required and must be a non-empty string."},
            status=400,
        )
    if not isinstance(scan_run_id, str) or not scan_run_id:
        return JsonResponse(
            {"error": "'scan_run_id' is required and must be a non-empty string."},
            status=400,
        )
    if not isinstance(warnings_in, list):
        return JsonResponse(
            {"error": "'warnings' must be a JSON array (possibly empty)."},
            status=400,
        )

    # Normalise each warning's payload to the dict shape expected by
    # PreflightWarning.replace_warnings.  Bail out early on invalid
    # input so the scanner gets a clear 400 instead of half-writing.
    normalised: list[dict] = []
    for idx, w in enumerate(warnings_in):
        if not isinstance(w, dict):
            return JsonResponse(
                {"error": f"warnings[{idx}] must be a JSON object."},
                status=400,
            )
        severity = w.get("severity", PreflightWarning.Severity.WARNING)
        if severity not in {s.value for s in PreflightWarning.Severity}:
            return JsonResponse(
                {"error": f"warnings[{idx}].severity invalid: {severity!r}"},
                status=400,
            )
        try:
            starts_at = _parse_starts_at(w.get("starts_at"))
        except ValueError as exc:
            return JsonResponse(
                {"error": f"warnings[{idx}]: {exc}"},
                status=400,
            )
        normalised.append({
            "severity":         severity,
            "show_id":          w.get("show_id"),
            "show_instance_id": w.get("show_instance_id"),
            "starts_at":        starts_at,
            "detail":           w.get("detail", {}),
        })

    inserted = PreflightWarning.replace_warnings(
        warning_type=warning_type,
        scan_run_id=scan_run_id,
        warnings=normalised,
    )
    return JsonResponse({"inserted": inserted})
