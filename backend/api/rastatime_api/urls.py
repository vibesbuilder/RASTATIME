"""
URL Configuration

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/http/urls/
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .audio_devices import audio_devices
from .core.router import urls as core_urls
from .health import health
from .history.router import urls as history_urls
from .linein_api import linein_detail, linein_list_or_create
from .now_playing import now_playing
from .podcasts.router import urls as podcasts_urls
from .preflight_api import preflight_warnings_list, preflight_warnings_replace
from .schedule.router import urls as schedule_urls
from .song_request_api import song_request_search, song_request_submit
from .soundcard_settings_api import soundcard_settings
from .storage.router import urls as storage_urls
from .storage.views.backup import (
    BackupAutoView,
    BackupCancelView,
    BackupDownloadView,
    BackupFolderView,
    BackupRunView,
    BackupStatusView,
    BackupValidateView,
)
from .storage.views.imports import FailedImportsView
from .storage.views.location import (
    StorageLocationView,
    StorageMoveCancelView,
    StorageMoveStartView,
    StorageMoveStatusView,
    StorageMoveValidateView,
)
from .storage.views.reread_tags import RereadTagsView
from .streams_status import stream_output_detail, stream_outputs

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
    # RASTATIME 2026-10-21 - refresh tag columns from the files on disk (Library button)
    path("api/v2/files/reread-tags", RereadTagsView.as_view(), name="files-reread-tags"),
    path(
        "api/v2/storage/move/validate",
        StorageMoveValidateView.as_view(),
        name="storage-move-validate",
    ),
    path("api/v2/storage/move/start", StorageMoveStartView.as_view(), name="storage-move-start"),
    path("api/v2/storage/move/cancel", StorageMoveCancelView.as_view(), name="storage-move-cancel"),
    path("api/v2/storage/move/status", StorageMoveStatusView.as_view(), name="storage-move-status"),
    # RASTATIME 2026-09-16 - manual backup (Settings -> Backup, stage 1)
    path("api/v2/storage/backup", BackupStatusView.as_view(), name="storage-backup"),
    path(
        "api/v2/storage/backup/validate",
        BackupValidateView.as_view(),
        name="storage-backup-validate",
    ),
    path("api/v2/storage/backup/folder", BackupFolderView.as_view(), name="storage-backup-folder"),
    path("api/v2/storage/backup/run", BackupRunView.as_view(), name="storage-backup-run"),
    path("api/v2/storage/backup/cancel", BackupCancelView.as_view(), name="storage-backup-cancel"),
    path("api/v2/storage/backup/auto", BackupAutoView.as_view(), name="storage-backup-auto"),
    path(
        "api/v2/storage/backup/download",
        BackupDownloadView.as_view(),
        name="storage-backup-download",
    ),
    # RASTATIME 2026-10-28 - failed imports + organize/ leftovers (preflight, Upload page)
    path(
        "api/v2/storage/imports/failed", FailedImportsView.as_view(), name="storage-imports-failed"
    ),
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
