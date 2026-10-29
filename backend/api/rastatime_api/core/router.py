from django.urls import path
from rest_framework import routers

from .views import (
    CeleryTaskViewSet,
    InfoView,
    LocalRecordingFolderView,
    LoginAttemptViewSet,
    PreferenceViewSet,
    ServiceRegisterViewSet,
    StreamPreferencesView,
    StreamStateView,
    ThirdPartyTrackReferenceViewSet,
    UserTokenViewSet,
    UserViewSet,
    VersionView,
)

router = routers.DefaultRouter(trailing_slash=False)
router.register("login-attempts", LoginAttemptViewSet)
router.register("preferences", PreferenceViewSet)
router.register("service-registers", ServiceRegisterViewSet)
router.register("users", UserViewSet)
router.register("user-tokens", UserTokenViewSet)
router.register("celery-tasks", CeleryTaskViewSet)
router.register("third-party-track-references", ThirdPartyTrackReferenceViewSet)

urls = [
    *router.urls,
    path("info", InfoView.as_view()),
    path("version", VersionView.as_view()),
    path("stream/preferences", StreamPreferencesView.as_view()),
    path("stream/state", StreamStateView.as_view()),
    # RASTATIME 2026-05-17 — NB this path lives at the v2 root, NOT under
    # ``preferences/...``: ``router.register("preferences", PreferenceViewSet)``
    # claims the entire ``/preferences/<x>`` subtree for its REST-style
    # detail view, where ``<x>`` is parsed as the integer pk.  An explicit
    # ``path("preferences/local-recording-folder", ...)`` never matches —
    # the router's detail route already returned 404 on
    # ``pk="local-recording-folder"`` before this handler is consulted.
    path("recording-folder", LocalRecordingFolderView.as_view()),
]
