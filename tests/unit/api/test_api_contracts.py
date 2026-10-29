"""
T17.3 — API contract tests.

Verify that every RASTATIME API endpoint:
  * is reachable at its documented URL,
  * returns the expected HTTP status code,
  * returns a response body with the documented shape (key set and types).

These tests use ``django.test.RequestFactory`` (view-function level) and
``django.test.Client`` (full URL-dispatch level) to cover both the
implementation and the routing contract.

All tests are skipped automatically when Django is not installed in the
current environment.  From the repo root, tests/unit/conftest.py
configures Django with the dev settings (no database): the 16 no-DB
tests run there, the 6 ``django_db`` tests are skipped and run from
backend/api, where pytest-django is configured with
``DJANGO_SETTINGS_MODULE = "rastatime_api.settings.testing"``.

Test inventory
--------------
/health (4, no DB):
  1.  GET /health → 200.
  2.  Body has ``status`` = ``"ok"``.
  3.  Body has ``service`` = ``"rastatime-api"``.
  4.  Body has non-empty ``version`` string.

/api/v2/now-playing (4, no DB):
  5.  GET /api/v2/now-playing → 200.
  6.  Body contains keys: ``is_playing``, ``item``, ``started_at``.
  7.  When idle: ``is_playing`` is ``False``.
  8.  When idle: ``item`` and ``started_at`` are both ``None``.

/api/v2/audio/devices (3, no DB):
  9.  GET /api/v2/audio/devices → 200.
 10.  Body contains keys ``outputs`` and ``inputs``.
 11.  Both values are lists when no manager is wired.

/api/v2/streams/outputs (3, no DB):
 12.  GET /api/v2/streams/outputs → 200.
 13.  Returns a JSON array when no egress manager is wired.
 14.  POST → 405 (method not allowed, ``require_GET`` enforced).

/api/v2/audio/soundcard-settings (3, DB required):
 15.  GET → 200.
 16.  Body contains the four documented keys.
 17.  Default singleton values are correct (all None / empty).

/api/v2/audio/linein (3, DB required):
 18.  GET → 200.
 19.  Body contains ``line_ins`` key.
 20.  ``line_ins`` is an empty list when the DB has no entries.

URL routing smoke tests (2):
 21.  Client GET /health resolves and returns 200.
 22.  Client GET /api/v2/now-playing resolves and returns 200.

(22 tests total; the 6 DB-backed ones are skipped from the repo root)
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Django availability guard
# ---------------------------------------------------------------------------

try:
    import django as _django_pkg  # noqa: F401
    _HAS_DJANGO = True
except ImportError:
    _HAS_DJANGO = False

_skip_no_django = pytest.mark.skipif(
    not _HAS_DJANGO,
    reason="Django not installed in this environment — skipping API contract tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def rf():
    """RequestFactory — calls views directly, bypassing URL routing."""
    pytest.importorskip("django.test")
    from django.test import RequestFactory  # noqa: PLC0415
    return RequestFactory()


@pytest.fixture()
def client():
    """Django test Client — exercises full URL routing and middleware."""
    pytest.importorskip("django.test")
    from django.test import Client  # noqa: PLC0415
    return Client()


# ---------------------------------------------------------------------------
# View imports (lazy, inside fixtures) — avoids import errors in root venv
# ---------------------------------------------------------------------------

@pytest.fixture()
def health_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.health import health  # noqa: PLC0415
    return health


@pytest.fixture()
def now_playing_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.now_playing import now_playing  # noqa: PLC0415
    return now_playing


@pytest.fixture()
def audio_devices_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.audio_devices import audio_devices  # noqa: PLC0415
    return audio_devices


@pytest.fixture()
def streams_outputs_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.streams_status import stream_outputs  # noqa: PLC0415
    return stream_outputs


@pytest.fixture()
def soundcard_settings_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.soundcard_settings_api import soundcard_settings  # noqa: PLC0415
    return soundcard_settings


@pytest.fixture()
def linein_list_view():
    pytest.importorskip("rastatime_api")
    from rastatime_api.linein_api import linein_list_or_create  # noqa: PLC0415
    return linein_list_or_create


# ---------------------------------------------------------------------------
# 1–4  /health
# ---------------------------------------------------------------------------

@_skip_no_django
def test_health_returns_200(rf, health_view):
    resp = health_view(rf.get("/health"))
    assert resp.status_code == 200


@_skip_no_django
def test_health_status_is_ok(rf, health_view):
    body = json.loads(health_view(rf.get("/health")).content)
    assert body.get("status") == "ok"


@_skip_no_django
def test_health_service_is_rastatime_api(rf, health_view):
    body = json.loads(health_view(rf.get("/health")).content)
    assert body.get("service") == "rastatime-api"


@_skip_no_django
def test_health_version_is_non_empty_string(rf, health_view):
    body = json.loads(health_view(rf.get("/health")).content)
    assert isinstance(body.get("version"), str)
    assert body["version"] != ""


# ---------------------------------------------------------------------------
# 5–8  /api/v2/now-playing
# ---------------------------------------------------------------------------

@_skip_no_django
def test_now_playing_returns_200(rf, now_playing_view):
    resp = now_playing_view(rf.get("/api/v2/now-playing"))
    assert resp.status_code == 200


@_skip_no_django
def test_now_playing_body_has_required_keys(rf, now_playing_view):
    body = json.loads(now_playing_view(rf.get("/api/v2/now-playing")).content)
    assert set(body.keys()) >= {"is_playing", "item", "started_at"}


@_skip_no_django
def test_now_playing_idle_is_playing_is_false(rf, now_playing_view):
    body = json.loads(now_playing_view(rf.get("/api/v2/now-playing")).content)
    # Default state has no playout engine wired → always idle.
    assert body["is_playing"] is False


@_skip_no_django
def test_now_playing_idle_item_and_started_at_are_none(rf, now_playing_view):
    body = json.loads(now_playing_view(rf.get("/api/v2/now-playing")).content)
    assert body["item"] is None
    assert body["started_at"] is None


# ---------------------------------------------------------------------------
# 9–11  /api/v2/audio/devices
# ---------------------------------------------------------------------------

@_skip_no_django
def test_audio_devices_returns_200(rf, audio_devices_view):
    resp = audio_devices_view(rf.get("/api/v2/audio/devices"))
    assert resp.status_code == 200


@_skip_no_django
def test_audio_devices_body_has_outputs_and_inputs(rf, audio_devices_view):
    body = json.loads(audio_devices_view(rf.get("/api/v2/audio/devices")).content)
    assert "outputs" in body
    assert "inputs" in body


@_skip_no_django
def test_audio_devices_both_are_lists_when_no_manager(rf, audio_devices_view):
    body = json.loads(audio_devices_view(rf.get("/api/v2/audio/devices")).content)
    assert isinstance(body["outputs"], list)
    assert isinstance(body["inputs"],  list)


# ---------------------------------------------------------------------------
# 12–14  /api/v2/streams/outputs
# ---------------------------------------------------------------------------

@_skip_no_django
def test_streams_outputs_returns_200(rf, streams_outputs_view):
    resp = streams_outputs_view(rf.get("/api/v2/streams/outputs"))
    assert resp.status_code == 200


@_skip_no_django
def test_streams_outputs_is_list_when_no_manager(rf, streams_outputs_view):
    body = json.loads(streams_outputs_view(rf.get("/api/v2/streams/outputs")).content)
    assert isinstance(body, list)


@_skip_no_django
def test_streams_outputs_rejects_post(rf, streams_outputs_view):
    """``require_GET`` must enforce GET-only; POST → 405."""
    resp = streams_outputs_view(rf.post("/api/v2/streams/outputs"))
    assert resp.status_code == 405


# ---------------------------------------------------------------------------
# 15–17  /api/v2/audio/soundcard-settings  (DB required)
# ---------------------------------------------------------------------------

@_skip_no_django
@pytest.mark.django_db
def test_soundcard_settings_returns_200(rf, soundcard_settings_view):
    resp = soundcard_settings_view(rf.get("/api/v2/audio/soundcard-settings"))
    assert resp.status_code == 200


@_skip_no_django
@pytest.mark.django_db
def test_soundcard_settings_body_has_documented_keys(rf, soundcard_settings_view):
    body = json.loads(
        soundcard_settings_view(rf.get("/api/v2/audio/soundcard-settings")).content
    )
    assert set(body.keys()) == {
        "main_output_id",
        "preview_output_id",
        "line_in_device_ids",
        "missing_device_ids",
    }


@_skip_no_django
@pytest.mark.django_db
def test_soundcard_settings_defaults_are_none_and_empty(rf, soundcard_settings_view):
    """Fresh DB singleton: IDs are None, lists are empty."""
    body = json.loads(
        soundcard_settings_view(rf.get("/api/v2/audio/soundcard-settings")).content
    )
    assert body["main_output_id"]     is None
    assert body["preview_output_id"]  is None
    assert body["line_in_device_ids"] == []


# ---------------------------------------------------------------------------
# 18–20  /api/v2/audio/linein  (DB required)
# ---------------------------------------------------------------------------

@_skip_no_django
@pytest.mark.django_db
def test_linein_list_returns_200(rf, linein_list_view):
    resp = linein_list_view(rf.get("/api/v2/audio/linein"))
    assert resp.status_code == 200


@_skip_no_django
@pytest.mark.django_db
def test_linein_list_body_has_line_ins_key(rf, linein_list_view):
    body = json.loads(linein_list_view(rf.get("/api/v2/audio/linein")).content)
    assert "line_ins" in body


@_skip_no_django
@pytest.mark.django_db
def test_linein_list_is_empty_initially(rf, linein_list_view):
    body = json.loads(linein_list_view(rf.get("/api/v2/audio/linein")).content)
    assert body["line_ins"] == []


# ---------------------------------------------------------------------------
# 21–22  URL routing smoke tests (Client-based)
# ---------------------------------------------------------------------------

@_skip_no_django
def test_client_health_url_resolves_and_returns_200(client):
    """Full URL routing: /health must resolve to the health view."""
    resp = client.get("/health")
    assert resp.status_code == 200


@_skip_no_django
def test_client_now_playing_url_resolves_and_returns_200(client):
    """Full URL routing: /api/v2/now-playing must resolve to the now-playing view."""
    resp = client.get("/api/v2/now-playing")
    assert resp.status_code == 200
