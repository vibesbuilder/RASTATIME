"""
Stream output status API.

GET /api/v2/streams/outputs
    Returns a JSON array of all registered stream outputs with their live
    runtime state.  Always returns HTTP 200; returns ``[]`` if no egress
    manager is connected.

GET /api/v2/streams/outputs/<output_id>
    Returns live status for one specific stream output.
    Returns HTTP 404 if the output_id is not registered.

Response shape (per output)
---------------------------
::

    {
        "output_id":       "main-mp3",
        "name":            "Main MP3 Stream",
        "protocol":        "icecast",
        "url":             "ice.example.com",
        "port":            8000,
        "mount":           "/live",
        "codec":           "mp3",
        "bitrate":         128,
        "enabled":         true,
        "state":           "active",
        "connected_since": "2026-04-26T14:30:00+00:00",
        "error_message":   null
    }

Single-process deployment (dev mode / combined server)
------------------------------------------------------
Call ``streams.egress.connect_egress_manager(mgr)`` at startup to wire the
manager to the process-level singleton.  The views then reflect live state.

Multi-process deployment (production)
--------------------------------------
The singleton stays ``None`` in the API process (separate OS process from the
playout engine).  A future task will add a shared transport (Redis / DB).
"""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def stream_outputs(request: HttpRequest) -> JsonResponse:
    """
    Return live status for all registered stream outputs.

    Always returns HTTP 200.  Returns ``[]`` if no egress manager is wired.
    """
    import streams.egress._registry as _reg          # lazy — avoids circular dep
    from streams.egress._api_helpers import list_output_statuses

    mgr = _reg.default_manager
    if mgr is None:
        return JsonResponse([], safe=False)

    return JsonResponse(list_output_statuses(mgr), safe=False)


@require_GET
def stream_output_detail(request: HttpRequest, output_id: str) -> JsonResponse:
    """
    Return live status for one stream output identified by *output_id*.

    Returns HTTP 404 if the output is not registered or no manager is wired.
    """
    import streams.egress._registry as _reg          # lazy — avoids circular dep
    from streams.egress._api_helpers import get_single_output_status

    mgr = _reg.default_manager
    if mgr is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    data = get_single_output_status(mgr, output_id)
    if data is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    return JsonResponse(data)
