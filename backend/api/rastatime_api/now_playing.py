"""
Now-playing API endpoint.

GET /api/v2/now-playing
    Returns a JSON snapshot of what is currently on air.

This view reads from ``playout.now_playing.default_state``, a process-level
singleton updated by the playout engine's ``on_track_change`` callbacks.

Single-process deployment (dev mode / combined server)
------------------------------------------------------
When the playout engine and the Django API share the same Python process,
call ``playout.now_playing.connect_engine(engine)`` at startup to wire the
engine to the default singletons.  The view will then reflect live state.

Multi-process deployment (production)
--------------------------------------
In production the playout engine and the API server run as separate OS
processes.  The default singleton stays idle (``is_playing=False``) unless
you provide a shared backing store (Redis, database, shared memory).  A
future task (post-T7.2) will add a Redis-backed transport.

Response shape (200 OK, always succeeds)
-----------------------------------------
::

    {
        "is_playing": true,
        "item": {
            "id": "track-42",
            "uri": "file:///music/song.mp3",
            "title": "My Song",
            "artist": "DJ Test",
            "duration": 210.5,
            "metadata": {"vlc": {"duration_ms": 210500}}
        },
        "started_at": "2026-04-25T14:30:00+00:00"
    }

    or, when idle:

    {"is_playing": false, "item": null, "started_at": null}
"""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def now_playing(request: HttpRequest) -> JsonResponse:
    """
    Return the current on-air state as JSON.

    Always returns HTTP 200; ``is_playing`` distinguishes active from idle.
    """
    from playout.now_playing import default_state  # lazy import — no circular dep

    entry = default_state.get()
    return JsonResponse(entry.to_dict())
