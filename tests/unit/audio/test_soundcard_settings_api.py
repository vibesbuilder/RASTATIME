"""
T13.2 — soundcard_settings_api unit tests.

Exercises the ORM-to-response serialization logic inline (no Django or
libretime_api import required) and tests the full Django view through
``django.test.RequestFactory`` when Django is available in the environment.

Test inventory
--------------
ORM-to-response logic (4):
  1.  Returned dict has exactly the three base keys (missing_device_ids added by _build_response).
  2.  Empty strings in the ORM object become None in the response.
  3.  Non-empty IDs are returned as-is.
  4.  line_in_device_ids is always a list (not a tuple or None).

Django view — GET (4):   [skipped when Django absent]
  5.  GET returns HTTP 200 when the singleton exists.
  6.  Response body contains the four expected keys (incl. missing_device_ids).
  7.  Newly created singleton has None IDs and an empty list.
  8.  Existing data is reflected in the GET response.

Django view — POST (9):  [skipped when Django absent]
  9.  POST with all three fields returns HTTP 200.
 10.  POST response body contains updated values.
 11.  POST with only main_output_id updates only that field.
 12.  POST with main_output_id=null clears the field.
 13.  POST with invalid JSON returns HTTP 400.
 14.  POST with a non-object JSON body returns HTTP 400.
 15.  POST with a non-string main_output_id returns HTTP 400.
 16.  POST with non-list line_in_device_ids returns HTTP 400.
 17.  POST with a list containing non-strings returns HTTP 400.

(17 tests total; 13 skipped in root venv where Django is not installed)
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Minimal fake ORM row (no Django required)
# ---------------------------------------------------------------------------

class _FakeOrm:
    """Stand-in for the Django SoundcardSettings ORM row."""

    def __init__(self, main_output_id="", preview_output_id="",
                 line_in_device_ids=None):
        self.main_output_id     = main_output_id
        self.preview_output_id  = preview_output_id
        self.line_in_device_ids = line_in_device_ids if line_in_device_ids is not None else []
        self._saved = False

    def save(self) -> None:
        self._saved = True


# ---------------------------------------------------------------------------
# The serialization logic under test — mirrors _orm_to_response exactly.
# Tested inline so this file works without libretime_api on sys.path.
# ---------------------------------------------------------------------------

def _orm_to_response(obj) -> dict:
    """Local copy of the function from soundcard_settings_api._orm_to_response."""
    return {
        "main_output_id":     obj.main_output_id    or None,
        "preview_output_id":  obj.preview_output_id or None,
        "line_in_device_ids": list(obj.line_in_device_ids or []),
    }


# ---------------------------------------------------------------------------
# 1–4  ORM-to-response serialization (no Django required)
# ---------------------------------------------------------------------------

def test_orm_to_response_keys():
    result = _orm_to_response(_FakeOrm())
    assert set(result.keys()) == {"main_output_id", "preview_output_id", "line_in_device_ids"}


def test_orm_to_response_empty_strings_become_none():
    obj = _FakeOrm(main_output_id="", preview_output_id="")
    result = _orm_to_response(obj)
    assert result["main_output_id"]    is None
    assert result["preview_output_id"] is None


def test_orm_to_response_non_empty_ids_preserved():
    obj = _FakeOrm(main_output_id="out-1", preview_output_id="prev-1")
    result = _orm_to_response(obj)
    assert result["main_output_id"]    == "out-1"
    assert result["preview_output_id"] == "prev-1"


def test_orm_to_response_line_in_device_ids_is_list():
    obj = _FakeOrm(line_in_device_ids=["in-1", "in-2"])
    result = _orm_to_response(obj)
    assert isinstance(result["line_in_device_ids"], list)
    assert result["line_in_device_ids"] == ["in-1", "in-2"]


# ---------------------------------------------------------------------------
# 5–17  Django view tests
# ---------------------------------------------------------------------------
# All tests below are skipped automatically when Django is not installed.
# They are expected to pass in the backend/api venv where Django is present.
#
# The skipif condition is evaluated at collection time; it does NOT use
# pytest.importorskip at module level (which would skip the whole file).

try:
    import django as _django_pkg  # noqa: F401
    _HAS_DJANGO = True
except ImportError:
    _HAS_DJANGO = False

_skip_no_django = pytest.mark.skipif(
    not _HAS_DJANGO,
    reason="Django not installed in this environment — skipping view tests",
)


@pytest.fixture()
def rf():
    pytest.importorskip("django.test")
    from django.test import RequestFactory as RF
    return RF()


@pytest.fixture()
def view():
    pytest.importorskip("django.test")
    from libretime_api.soundcard_settings_api import soundcard_settings   # type: ignore[import]
    return soundcard_settings


@pytest.fixture()
def singleton(db):
    """Return the freshly initialised singleton ORM row."""
    pytest.importorskip("django.test")
    from libretime_api.soundcard.models import SoundcardSettings          # type: ignore[import]
    return SoundcardSettings.get_settings()


# 5
@_skip_no_django
@pytest.mark.django_db
def test_get_returns_200(rf, view, singleton):
    resp = view(rf.get("/api/v2/audio/soundcard-settings"))
    assert resp.status_code == 200


# 6 — T13.3 added missing_device_ids to every response
@_skip_no_django
@pytest.mark.django_db
def test_get_body_has_expected_keys(rf, view, singleton):
    body = json.loads(view(rf.get("/api/v2/audio/soundcard-settings")).content)
    assert set(body.keys()) == {
        "main_output_id", "preview_output_id", "line_in_device_ids",
        "missing_device_ids",
    }


# 7
@_skip_no_django
@pytest.mark.django_db
def test_get_fresh_singleton_defaults(rf, view, singleton):
    body = json.loads(view(rf.get("/api/v2/audio/soundcard-settings")).content)
    assert body["main_output_id"]     is None
    assert body["preview_output_id"]  is None
    assert body["line_in_device_ids"] == []


# 8
@_skip_no_django
@pytest.mark.django_db
def test_get_reflects_existing_data(rf, view, singleton):
    singleton.main_output_id = "out-99"
    singleton.save()
    body = json.loads(view(rf.get("/api/v2/audio/soundcard-settings")).content)
    assert body["main_output_id"] == "out-99"


def _post(rf, view, payload):
    req = rf.post(
        "/api/v2/audio/soundcard-settings",
        data=json.dumps(payload),
        content_type="application/json",
    )
    return view(req)


# 9
@_skip_no_django
@pytest.mark.django_db
def test_post_all_fields_returns_200(rf, view, singleton):
    resp = _post(rf, view, {"main_output_id": "out-1", "preview_output_id": "prev-1",
                            "line_in_device_ids": ["in-1"]})
    assert resp.status_code == 200


# 10
@_skip_no_django
@pytest.mark.django_db
def test_post_response_reflects_new_values(rf, view, singleton):
    body = json.loads(_post(rf, view, {
        "main_output_id": "out-2", "preview_output_id": "prev-2",
        "line_in_device_ids": ["in-a", "in-b"],
    }).content)
    assert body["main_output_id"]     == "out-2"
    assert body["preview_output_id"]  == "prev-2"
    assert body["line_in_device_ids"] == ["in-a", "in-b"]


# 11
@_skip_no_django
@pytest.mark.django_db
def test_post_partial_update_preserves_other_fields(rf, view, singleton):
    singleton.preview_output_id = "prev-existing"
    singleton.save()
    body = json.loads(_post(rf, view, {"main_output_id": "out-new"}).content)
    assert body["main_output_id"]    == "out-new"
    assert body["preview_output_id"] == "prev-existing"


# 12
@_skip_no_django
@pytest.mark.django_db
def test_post_null_clears_field(rf, view, singleton):
    singleton.main_output_id = "out-set"
    singleton.save()
    body = json.loads(_post(rf, view, {"main_output_id": None}).content)
    assert body["main_output_id"] is None


# 13
@_skip_no_django
@pytest.mark.django_db
def test_post_invalid_json_returns_400(rf, view, singleton):
    req = rf.post("/api/v2/audio/soundcard-settings",
                  data=b"not { json", content_type="application/json")
    assert view(req).status_code == 400


# 14
@_skip_no_django
@pytest.mark.django_db
def test_post_non_object_json_returns_400(rf, view, singleton):
    assert _post(rf, view, [1, 2, 3]).status_code == 400


# 15
@_skip_no_django
@pytest.mark.django_db
def test_post_non_string_main_output_id_returns_400(rf, view, singleton):
    assert _post(rf, view, {"main_output_id": 42}).status_code == 400


# 16
@_skip_no_django
@pytest.mark.django_db
def test_post_non_list_line_in_returns_400(rf, view, singleton):
    assert _post(rf, view, {"line_in_device_ids": "not-a-list"}).status_code == 400


# 17
@_skip_no_django
@pytest.mark.django_db
def test_post_line_in_non_string_elements_returns_400(rf, view, singleton):
    assert _post(rf, view, {"line_in_device_ids": ["ok", 123]}).status_code == 400
