"""
URL Configuration

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/http/urls/
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .audio_devices import audio_devices
from .soundcard_settings_api import soundcard_settings
from .linein_api import linein_list_or_create, linein_detail
from .preflight_api import preflight_warnings_list, preflight_warnings_replace
from .health import health
from .now_playing import now_playing
from .song_request_api import song_request_search, song_request_submit
from .streams_status import stream_output_detail, stream_outputs
from .core.router import urls as core_urls
from .history.router import urls as history_urls
from .podcasts.router import urls as podcasts_urls
from .schedule.router import urls as schedule_urls
from .storage.router import urls as storage_urls
from .storage.views.location import (
    StorageLocationView,
    StorageMoveCancelView,
    StorageMoveStartView,
    StorageMoveStatusView,
    StorageMoveValidateView,
)

api_urls = []
api_urls += core_urls
api_urls += history_urls
api_urls += podcasts_urls
api_urls += schedule_urls
api_urls += storage_urls


urlpatterns = [
    path("health", health, name="health"),
    path("api/v2/now-playing", now_playing, name="now-playing"),
    path("api/v2/song-requests/search", song_request_search, name="song-request-search"),
    path("api/v2/song-requests", song_request_submit, name="song-request-submit"),
    path("api/v2/audio/devices", audio_devices, name="audio-devices"),
    path("api/v2/audio/soundcard-settings", soundcard_settings, name="soundcard-settings"),
    path("api/v2/audio/linein", linein_list_or_create, name="linein-list"),
    path("api/v2/audio/linein/<str:linein_id>", linein_detail, name="linein-detail"),
    path("api/v2/preflight/warnings", preflight_warnings_list, name="preflight-warnings-list"),
    path(
        "api/v2/preflight/warnings/replace",
        preflight_warnings_replace,
        name="preflight-warnings-replace",
    ),
    # RASTATIME 2026-09-16 - Media Library Location (Settings -> Local Machine)
    path("api/v2/storage/location", StorageLocationView.as_view(), name="storage-location"),
    path("api/v2/storage/move/validate", StorageMoveValidateView.as_view(), name="storage-move-validate"),
    path("api/v2/storage/move/start", StorageMoveStartView.as_view(), name="storage-move-start"),
    path("api/v2/storage/move/cancel", StorageMoveCancelView.as_view(), name="storage-move-cancel"),
    path("api/v2/storage/move/status", StorageMoveStatusView.as_view(), name="storage-move-status"),
    path("api/v2/streams/outputs", stream_outputs, name="stream-outputs"),
    path(
        "api/v2/streams/outputs/<str:output_id>",
        stream_output_detail,
        name="stream-output-detail",
    ),
    path("api/browser/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/v2/", include(api_urls)),
    path(
        "api/v2/schema",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/v2/schema/swagger-ui",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
