"""
T14.2 — Line-In list API unit tests.

Exercises :mod:`audio.linein._api_helpers` (no Django required) and the
Django view through ``django.test.RequestFactory`` when Django is available.

Test inventory
--------------
serialize_linein() (6):
  1.  Returned dict has exactly the seven expected keys.
  2.  ``channel_mapping`` is serialised as a plain list, not a tuple.
  3.  ``enabled`` is a plain bool.
  4.  ``priority`` is an int.
  5.  Values match the domain model fields.
  6.  Modifying the returned dict does not affect the domain instance.

list_lineins_response() (4):
  7.  Returns a dict with exactly the ``"line_ins"`` key.
  8.  ``"line_ins"`` is an empty list when no entries are given.
  9.  ``"line_ins"`` has one entry per domain object.
 10.  Each entry contains all seven expected field keys.

Django view — GET (7):   [skipped when Django absent]
 11.  GET /api/v2/audio/linein returns HTTP 200.
 12.  Response body contains the ``"line_ins"`` key.
 13.  ``"line_ins"`` is an empty list when no DB entries exist.
 14.  All persisted entries appear in the response.
 15.  Each entry in the response has all seven expected keys.
 16.  Entries follow the model ordering (``-priority``, ``name``).
 17.  POST to the endpoint returns HTTP 405 (method not allowed).

(17 tests total; 7 skipped in root venv where Django is not installed)
"""

from __future__ import annotations

import json

import pytest

from audio.linein.domain import LineIn
from audio.linein._api_helpers import list_lineins_response, serialize_linein


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {"id", "name", "device_id", "channel_mapping",
                  "enabled", "description", "priority",
                  "length_seconds", "device_name", "input_gain_db"}


def _domain(**kwargs) -> LineIn:
    defaults = dict(
        id="test-uuid-001",
        name="Drum Kit",
        device_id="dev-abc",
        channel_mapping=(0, 1),
        enabled=True,
        description="",
        priority=0,
    )
    defaults.update(kwargs)
    return LineIn(**defaults)


# ---------------------------------------------------------------------------
# 1–6  serialize_linein()
# ---------------------------------------------------------------------------

def test_serialize_linein_has_correct_keys():
    d = serialize_linein(_domain())
    assert set(d.keys()) == _EXPECTED_KEYS


def test_serialize_linein_channel_mapping_is_list():
    d = serialize_linein(_domain(channel_mapping=(2, 3)))
    assert isinstance(d["channel_mapping"], list)
    assert d["channel_mapping"] == [2, 3]


def test_serialize_linein_enabled_is_bool():
    assert isinstance(serialize_linein(_domain(enabled=True))["enabled"], bool)
    assert isinstance(serialize_linein(_domain(enabled=False))["enabled"], bool)


def test_serialize_linein_priority_is_int():
    assert isinstance(serialize_linein(_domain(priority=5))["priority"], int)


def test_serialize_linein_values_match_fields():
    li = _domain(
        id="specific-id",
        name="Bass DI",
        device_id="dev-bass",
        channel_mapping=(4,),
        enabled=False,
        description="Bass direct-inject",
        priority=3,
    )
    d = serialize_linein(li)
    assert d["id"]              == "specific-id"
    assert d["name"]            == "Bass DI"
    assert d["device_id"]       == "dev-bass"
    assert d["channel_mapping"] == [4]
    assert d["enabled"]         is False
    assert d["description"]     == "Bass direct-inject"
    assert d["priority"]        == 3


def test_serialize_linein_mutation_does_not_affect_instance():
    li = _domain(name="Original")
    d = serialize_linein(li)
    d["name"] = "mutated"
    assert li.name == "Original"


# ---------------------------------------------------------------------------
# 7–10  list_lineins_response()
# ---------------------------------------------------------------------------

def test_list_lineins_response_has_line_ins_key():
    resp = list_lineins_response([])
    assert set(resp.keys()) == {"line_ins"}


def test_list_lineins_response_empty_list_when_no_entries():
    resp = list_lineins_response([])
    assert resp["line_ins"] == []


def test_list_lineins_response_one_entry_per_domain_object():
    entries = [_domain(id=f"id-{i}", name=f"Mic {i}") for i in range(3)]
    resp = list_lineins_response(entries)
    assert len(resp["line_ins"]) == 3


def test_list_lineins_response_each_entry_has_expected_keys():
    resp = list_lineins_response([_domain()])
    assert set(resp["line_ins"][0].keys()) == _EXPECTED_KEYS


# ---------------------------------------------------------------------------
# 11–17  Django view tests
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
def view():
    pytest.importorskip("django.test")
    from rastatime_api.linein_api import linein_list        # type: ignore[import]
    return linein_list


def _make_orm_entry(name, device_id="dev-x", channels=None, priority=0,
                    enabled=True, description=""):
    """Create and persist one ORM LineIn row."""
    from rastatime_api.linein.models import LineIn as OrmLineIn   # type: ignore[import]
    from audio.linein.domain import LineIn as DomainLineIn
    domain = DomainLineIn.create(
        name=name,
        device_id=device_id,
        channel_mapping=channels or [0, 1],
        enabled=enabled,
        description=description,
        priority=priority,
    )
    return OrmLineIn.create_from_domain(domain)


# 11
@_skip_no_django
@pytest.mark.django_db
def test_get_returns_200(rf, view):
    resp = view(rf.get("/api/v2/audio/linein"))
    assert resp.status_code == 200


# 12
@_skip_no_django
@pytest.mark.django_db
def test_get_response_has_line_ins_key(rf, view):
    body = json.loads(view(rf.get("/api/v2/audio/linein")).content)
    assert "line_ins" in body


# 13
@_skip_no_django
@pytest.mark.django_db
def test_get_empty_list_when_no_entries(rf, view):
    body = json.loads(view(rf.get("/api/v2/audio/linein")).content)
    assert body["line_ins"] == []


# 14
@_skip_no_django
@pytest.mark.django_db
def test_get_all_persisted_entries_returned(rf, view, db):
    _make_orm_entry("Snare")
    _make_orm_entry("Hi-Hat")
    body = json.loads(view(rf.get("/api/v2/audio/linein")).content)
    names = {e["name"] for e in body["line_ins"]}
    assert names == {"Snare", "Hi-Hat"}


# 15
@_skip_no_django
@pytest.mark.django_db
def test_get_each_entry_has_expected_keys(rf, view, db):
    _make_orm_entry("Kick")
    body = json.loads(view(rf.get("/api/v2/audio/linein")).content)
    assert set(body["line_ins"][0].keys()) == _EXPECTED_KEYS


# 16
@_skip_no_django
@pytest.mark.django_db
def test_get_entries_ordered_by_priority_desc_then_name(rf, view, db):
    _make_orm_entry("B-Mic",   priority=0)
    _make_orm_entry("A-Mic",   priority=0)
    _make_orm_entry("High-Pri", priority=5)
    body = json.loads(view(rf.get("/api/v2/audio/linein")).content)
    names = [e["name"] for e in body["line_ins"]]
    assert names[0] == "High-Pri"          # highest priority first
    assert names[1:] == ["A-Mic", "B-Mic"] # then alphabetical


# 17
@_skip_no_django
@pytest.mark.django_db
def test_post_returns_405(rf, view):
    resp = view(rf.post("/api/v2/audio/linein"))
    assert resp.status_code == 405
