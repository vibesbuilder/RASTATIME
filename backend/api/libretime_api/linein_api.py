"""
Line-In source CRUD API.

GET    /api/v2/audio/linein
    List all persisted line-in entries (ordered by -priority, name).
    Always HTTP 200.  Returns ``{"line_ins": []}`` when empty.

POST   /api/v2/audio/linein
    Create a new line-in source.  Required body fields: ``name``,
    ``device_id``, ``channel_mapping`` (non-empty list of non-negative ints).
    Optional: ``enabled`` (bool, default true), ``description`` (str),
    ``priority`` (int, default 0).  Returns HTTP 201 + the created entry.

PATCH  /api/v2/audio/linein/<linein_id>
    Partially update an existing entry identified by its domain UUID.
    Any subset of fields may be provided.  Returns HTTP 200 + updated entry.
    Returns HTTP 404 if ``linein_id`` not found.

DELETE /api/v2/audio/linein/<linein_id>
    Delete an entry.  Returns HTTP 204 (no body).
    Returns HTTP 404 if ``linein_id`` not found.

Response shape (GET list)
-------------------------
::

    {"line_ins": [{
        "id":              "uuid",
        "name":            "Drum Kit",
        "device_id":       "stable-id",
        "channel_mapping": [0, 1],
        "enabled":         true,
        "description":     "",
        "priority":        0
    }]}

Response shape (POST / PATCH success)
--------------------------------------
::

    {"id": ..., "name": ..., ...}   (the seven domain fields)

HTTP status codes
-----------------
200  GET / PATCH success
201  POST success
204  DELETE success
400  Invalid request body (bad JSON, missing required field, wrong type)
404  linein_id not found (PATCH / DELETE)
405  Wrong HTTP method
"""

from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


# ---------------------------------------------------------------------------
# GET list + POST create
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
def linein_list_or_create(request: HttpRequest) -> JsonResponse:
    """
    GET  — list all line-in sources.
    POST — create a new line-in source.
    """
    from libretime_api.linein.models import LineIn as OrmLineIn   # lazy
    from audio.linein._api_helpers import (
        list_lineins_response, serialize_linein,
        parse_linein_create_body,
    )
    from audio.linein.domain import LineIn as DomainLineIn

    # --- GET ---------------------------------------------------------------
    if request.method == "GET":
        domain_objects = [row.to_domain() for row in OrmLineIn.objects.all()]
        return JsonResponse(list_lineins_response(domain_objects))

    # --- POST (create) -----------------------------------------------------
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    try:
        fields = parse_linein_create_body(body)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    domain = DomainLineIn.create(**fields)
    orm    = OrmLineIn.create_from_domain(domain)
    return JsonResponse(serialize_linein(orm.to_domain()), status=201)


# ---------------------------------------------------------------------------
# PATCH update + DELETE
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def linein_detail(request: HttpRequest, linein_id: str) -> HttpResponse:
    """
    GET    — return the single line-in identified by its domain UUID.
    PATCH  — partially update an existing line-in by its domain UUID.
    DELETE — remove an existing line-in by its domain UUID.

    RASTATIME 2026-05-12: GET added so the new Media-Library edit
    dialog can fetch one entry directly instead of pulling the full
    list and filtering client-side.
    """
    from libretime_api.linein.models import LineIn as OrmLineIn   # lazy
    from audio.linein._api_helpers import serialize_linein, parse_linein_patch_body

    # Resolve the ORM row by either the domain UUID (linein_id, used by
    # the Frontend) or the integer DB pk (used by the playout service
    # when reading cc_schedule.linein_id).  The route accepts both for
    # the same URL — purely numeric strings are treated as pk, anything
    # else as UUID.
    try:
        if linein_id.isdigit():
            orm = OrmLineIn.objects.get(pk=int(linein_id))
        else:
            orm = OrmLineIn.objects.get(linein_id=linein_id)
    except OrmLineIn.DoesNotExist:
        return JsonResponse({"error": f"Line-in '{linein_id}' not found."}, status=404)

    # --- GET ---------------------------------------------------------------
    if request.method == "GET":
        return JsonResponse(serialize_linein(orm.to_domain()))

    # --- DELETE ------------------------------------------------------------
    if request.method == "DELETE":
        orm.delete()
        return HttpResponse(status=204)

    # --- PATCH (partial update) --------------------------------------------
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    try:
        fields = parse_linein_patch_body(body)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    # Apply only the fields present in the patch body.
    if "name"            in fields: orm.name            = fields["name"]
    if "device_id"       in fields: orm.device_id       = fields["device_id"]
    if "device_name"     in fields: orm.device_name     = fields["device_name"]
    if "channel_mapping" in fields: orm.channel_mapping = fields["channel_mapping"]
    if "enabled"         in fields: orm.enabled         = fields["enabled"]
    if "description"     in fields: orm.description     = fields["description"]
    if "priority"        in fields: orm.priority        = fields["priority"]
    if "length_seconds"  in fields:
        from datetime import timedelta
        ls = fields["length_seconds"]
        orm.length = timedelta(seconds=ls) if ls is not None else None
    if "input_gain_db"   in fields: orm.input_gain_db   = fields["input_gain_db"]

    orm.save()
    return JsonResponse(serialize_linein(orm.to_domain()))
