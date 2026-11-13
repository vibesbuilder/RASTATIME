"""
RASTATIME 2026-11-13 - Auto DJ buffer status (ARCHITECTURE §23.107).

GET /api/v2/auto-dj/buffer
    Is the Auto DJ buffer configured, and does its playlist hold a track
    that outlasts the maximum gap?  Read by the playout's preflight scan
    (warning ``auto_dj_buffer_unusable``).  Internal callers only (Api-Key
    or a direct call from this machine), like the preflight endpoints.
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rastatime_api.permissions import internal_only


@csrf_exempt
@require_http_methods(["GET"])
@internal_only
def auto_dj_buffer_status(request: HttpRequest) -> JsonResponse:  # pylint: disable=unused-argument
    from rastatime_api.schedule.buffer import buffer_status  # lazy, like the other plain views

    return JsonResponse(buffer_status())
