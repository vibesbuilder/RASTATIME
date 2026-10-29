"""
T14.3 — Line-In CRUD API unit tests.

Exercises :mod:`audio.linein._api_helpers` (pure Python) and the Django
views through ``django.test.RequestFactory`` when Django is available.

Test inventory
--------------
parse_linein_create_body() — pure (6):
  1.  Returns all 6 expected keys when all required + optional fields present.
  2.  Raises ValueError when ``name`` is missing.
  3.  Raises ValueError when ``device_id`` is missing.
  4.  Raises ValueError when ``channel_mapping`` is missing or empty.
  5.  Raises ValueError when a channel element is negative.
  6.  Optional fields (enabled, description, priority) fall back to defaults.

parse_linein_patch_body() — pure (6):
  7.  Returns only the keys actually present in the body.
  8.  Returns an empty dict for an empty body (no-op PATCH).
  9.  Raises ValueError when ``name`` is an empty string.
 10.  Raises ValueError when ``channel_mapping`` element is not an int.
 11.  Raises ValueError when ``priority`` is a float (not int).
 12.  Accepts a body with every patchable field.

Django view — POST create (6):  [skipped when Django absent]
 13.  POST with valid body returns HTTP 201.
 14.  POST response body has all seven expected keys.
 15.  POST with missing ``name`` returns HTTP 400.
 16.  POST with invalid JSON returns HTTP 400.
 17.  POST with non-dict JSON (e.g. a list) returns HTTP 400.
 18.  GET on the detail route returns HTTP 405.

Django view — PATCH / DELETE (6):  [skipped when Django absent]
 19.  PATCH with valid body returns HTTP 200.
 20.  PATCH response body reflects the updated field.
 21.  PATCH with unknown ``linein_id`` returns HTTP 404.
 22.  PATCH with invalid field type returns HTTP 400.
 23.  DELETE returns HTTP 204 (no body).
 24.  DELETE with unknown ``linein_id`` returns HTTP 404.

(24 tests total; 12 skipped in root venv where Django is not installed)
"""

from __future__ import annotations

import json

import pytest

from audio.linein._api_helpers import parse_linein_create_body, parse_linein_patch_body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {"id", "name", "device_id", "channel_mapping",
                  "enabled", "description", "priority"}

_VALID_CREATE_BODY = {
    "name":            "Drum Kit",
    "device_id":       "dev-usb-001",
    "channel_mapping": [0, 1],
    "enabled":         True,
    "description":     "Main drum mix",
    "priority":        2,
}


# ---------------------------------------------------------------------------
# 1–6  parse_linein_create_body() — pure Python
# ---------------------------------------------------------------------------

def test_create_body_returns_all_keys():
    result = parse_linein_create_body(_VALID_CREATE_BODY.copy())
    assert set(result.keys()) == {
        "name", "device_id", "channel_mapping", "enabled", "description",
        "priority", "length_seconds", "device_name", "input_gain_db",
    }


def test_create_body_missing_name_raises():
    body = {k: v for k, v in _VALID_CREATE_BODY.items() if k != "name"}
    with pytest.raises(ValueError, match="name"):
        parse_linein_create_body(body)


def test_create_body_missing_device_id_raises():
    body = {k: v for k, v in _VALID_CREATE_BODY.items() if k != "device_id"}
    with pytest.raises(ValueError, match="device_id"):
        parse_linein_create_body(body)


def test_create_body_missing_channel_mapping_raises():
    body = {k: v for k, v in _VALID_CREATE_BODY.items() if k != "channel_mapping"}
    with pytest.raises(ValueError, match="channel_mapping"):
        parse_linein_create_body(body)


def test_create_body_negative_channel_raises():
    body = dict(_VALID_CREATE_BODY, channel_mapping=[0, -1])
    with pytest.raises(ValueError):
        parse_linein_create_body(body)


def test_create_body_optional_fields_have_defaults():
    minimal = {
        "name":            "Bass DI",
        "device_id":       "dev-bass",
        "channel_mapping": [2],
    }
    result = parse_linein_create_body(minimal)
    assert result["enabled"]     is True
    assert result["description"] == ""
    assert result["priority"]    == 0


# ---------------------------------------------------------------------------
# 7–12  parse_linein_patch_body() — pure Python
# ---------------------------------------------------------------------------

def test_patch_body_returns_only_present_keys():
    result = parse_linein_patch_body({"name": "New Name"})
    assert list(result.keys()) == ["name"]
    assert result["name"] == "New Name"


def test_patch_body_empty_body_returns_empty_dict():
    assert parse_linein_patch_body({}) == {}


def test_patch_body_empty_name_raises():
    with pytest.raises(ValueError, match="name"):
        parse_linein_patch_body({"name": "   "})


def test_patch_body_non_int_channel_element_raises():
    with pytest.raises(ValueError):
        parse_linein_patch_body({"channel_mapping": [0, "left"]})


def test_patch_body_float_priority_raises():
    with pytest.raises(ValueError, match="priority"):
        parse_linein_patch_body({"priority": 1.5})


def test_patch_body_full_body_accepted():
    body = {
        "name":            "Updated Name",
        "device_id":       "dev-new",
        "channel_mapping": [0, 1, 2],
        "enabled":         False,
        "description":     "Updated desc",
        "priority":        10,
    }
    result = parse_linein_patch_body(body)
    assert result == body


# ---------------------------------------------------------------------------
# Django-gated fixtures
# ---------------------------------------------------------------------------

try:
    import django as _django_pkg   # noqa: F401
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
def list_view():
    pytest.importorskip("django.test")
    from rastatime_api.linein_api import linein_list_or_create   # type: ignore[import]
    return linein_list_or_create


@pytest.fixture()
def detail_view():
    pytest.importorskip("django.test")
    from rastatime_api.linein_api import linein_detail            # type: ignore[import]
    return linein_detail


def _make_orm_entry(name="Test Mic", device_id="dev-x",
                    channel_mapping=None, priority=0):
    from rastatime_api.linein.models import LineIn as OrmLineIn   # type: ignore[import]
    from audio.linein.domain import LineIn as DomainLineIn
    domain = DomainLineIn.create(
        name=name,
        device_id=device_id,
        channel_mapping=channel_mapping or [0, 1],
        priority=priority,
    )
    return OrmLineIn.create_from_domain(domain)


def _post_json(rf, url, body):
    return rf.post(
        url,
        data=json.dumps(body),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 13–18  POST create (Django)
# ---------------------------------------------------------------------------

@_skip_no_django
@pytest.mark.django_db
def test_post_create_returns_201(rf, list_view):
    req = _post_json(rf, "/api/v2/audio/linein", _VALID_CREATE_BODY)
    resp = list_view(req)
    assert resp.status_code == 201


@_skip_no_django
@pytest.mark.django_db
def test_post_create_response_has_expected_keys(rf, list_view):
    req = _post_json(rf, "/api/v2/audio/linein", _VALID_CREATE_BODY)
    body = json.loads(list_view(req).content)
    assert set(body.keys()) == _EXPECTED_KEYS


@_skip_no_django
@pytest.mark.django_db
def test_post_missing_name_returns_400(rf, list_view):
    body = {k: v for k, v in _VALID_CREATE_BODY.items() if k != "name"}
    req = _post_json(rf, "/api/v2/audio/linein", body)
    resp = list_view(req)
    assert resp.status_code == 400


@_skip_no_django
@pytest.mark.django_db
def test_post_invalid_json_returns_400(rf, list_view):
    req = rf.post(
        "/api/v2/audio/linein",
        data=b"not-json",
        content_type="application/json",
    )
    resp = list_view(req)
    assert resp.status_code == 400


@_skip_no_django
@pytest.mark.django_db
def test_post_non_dict_json_returns_400(rf, list_view):
    req = rf.post(
        "/api/v2/audio/linein",
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    resp = list_view(req)
    assert resp.status_code == 400


@_skip_no_django
@pytest.mark.django_db
def test_get_on_detail_route_returns_405(rf, detail_view):
    req = rf.get("/api/v2/audio/linein/some-id")
    resp = detail_view(req, linein_id="some-id")
    assert resp.status_code == 405


# ---------------------------------------------------------------------------
# 19–24  PATCH / DELETE (Django)
# ---------------------------------------------------------------------------

@_skip_no_django
@pytest.mark.django_db
def test_patch_valid_body_returns_200(rf, detail_view, db):
    orm = _make_orm_entry(name="Original")
    req = rf.patch(
        "/api/v2/audio/linein/" + orm.linein_id,
        data=json.dumps({"name": "Updated"}),
        content_type="application/json",
    )
    resp = detail_view(req, linein_id=orm.linein_id)
    assert resp.status_code == 200


@_skip_no_django
@pytest.mark.django_db
def test_patch_response_reflects_updated_field(rf, detail_view, db):
    orm = _make_orm_entry(name="Before")
    req = rf.patch(
        "/api/v2/audio/linein/" + orm.linein_id,
        data=json.dumps({"name": "After"}),
        content_type="application/json",
    )
    body = json.loads(detail_view(req, linein_id=orm.linein_id).content)
    assert body["name"] == "After"


@_skip_no_django
@pytest.mark.django_db
def test_patch_unknown_id_returns_404(rf, detail_view):
    req = rf.patch(
        "/api/v2/audio/linein/no-such-id",
        data=json.dumps({"name": "X"}),
        content_type="application/json",
    )
    resp = detail_view(req, linein_id="no-such-id")
    assert resp.status_code == 404


@_skip_no_django
@pytest.mark.django_db
def test_patch_invalid_field_type_returns_400(rf, detail_view, db):
    orm = _make_orm_entry()
    req = rf.patch(
        "/api/v2/audio/linein/" + orm.linein_id,
        data=json.dumps({"priority": "high"}),
        content_type="application/json",
    )
    resp = detail_view(req, linein_id=orm.linein_id)
    assert resp.status_code == 400


@_skip_no_django
@pytest.mark.django_db
def test_delete_returns_204(rf, detail_view, db):
    orm = _make_orm_entry(name="To Delete")
    req = rf.delete("/api/v2/audio/linein/" + orm.linein_id)
    resp = detail_view(req, linein_id=orm.linein_id)
    assert resp.status_code == 204


@_skip_no_django
@pytest.mark.django_db
def test_delete_unknown_id_returns_404(rf, detail_view):
    req = rf.delete("/api/v2/audio/linein/ghost-id")
    resp = detail_view(req, linein_id="ghost-id")
    assert resp.status_code == 404
