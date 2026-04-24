from django.http import JsonResponse

from . import VERSION


def health(request):
    """Liveness probe — no database access, always responds if Django is up."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "rastatime-api",
            "version": VERSION,
        }
    )
