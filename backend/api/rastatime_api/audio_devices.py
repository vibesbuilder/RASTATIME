"""
Audio device list API.

GET /api/v2/audio/devices
    Returns a JSON object with ``"outputs"`` and ``"inputs"`` arrays,
    each containing one entry per currently available audio endpoint.
    Always returns HTTP 200.  Returns empty arrays if no device manager
    is connected (e.g. during startup or in a multi-process deployment
    where the playout process has not yet called
    ``connect_device_manager``).

Response shape
--------------
::

    {
        "outputs": [
            {
                "stable_id":    "9ab29437-d4ec-473d-9a94-1ad46a86e9ff",
                "name":         "DELL U2419HC",
                "kind":         "output",
                "channels":     2,
                "driver":       "WASAPI",
                "is_default":   false,
                "is_available": true
            }
        ],
        "inputs": [
            {
                "stable_id":    "0bcc4357-eafe-45b4-ba84-d810eab113fb",
                "name":         "Mikrofon",
                "kind":         "input",
                "channels":     16,
                "driver":       "WASAPI",
                "is_default":   false,
                "is_available": true
            }
        ]
    }

Single-process deployment (dev mode / combined server)
------------------------------------------------------
Call ``audio.soundcard.connect_device_manager(mgr)`` at startup to wire the
manager to the process-level singleton.  The view then reflects the live
device inventory.

Multi-process deployment (production)
--------------------------------------
The singleton stays ``None`` in the API process.  A future task will add a
shared transport (Redis / DB).
"""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET
from rastatime_api.permissions import internal_only  # RASTATIME 2026-10-25 role audit S3/S4


@require_GET
@internal_only
def audio_devices(request: HttpRequest) -> JsonResponse:
    """
    Return the list of available audio output and input devices.

    Always returns HTTP 200.  Returns ``{"outputs": [], "inputs": []}``
    if no device manager is connected to the process singleton.
    """
    import audio.soundcard._registry as _reg          # lazy — avoids circular dep
    from audio.soundcard._api_helpers import list_devices_response

    mgr = _reg.default_manager
    if mgr is None:
        return JsonResponse({"outputs": [], "inputs": []})

    return JsonResponse(list_devices_response(mgr))
