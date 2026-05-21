"""
T14.1 — LineIn domain model unit tests.

Exercises the pure :class:`~audio.linein.domain.LineIn` dataclass
without Django, database, or audio hardware.

Test inventory
--------------
Construction and defaults (5):
  1.  All seven fields are present after direct construction.
  2.  ``enabled`` defaults to ``True``.
  3.  ``description`` defaults to an empty string.
  4.  ``priority`` defaults to ``0``.
  5.  ``channel_mapping`` is stored as a tuple.

Validation (5):
  6.  Blank ``name`` raises ``ValueError``.
  7.  Blank ``device_id`` raises ``ValueError``.
  8.  Empty ``channel_mapping`` raises ``ValueError``.
  9.  A negative channel index raises ``ValueError``.
 10.  A non-integer channel element raises ``TypeError``.

Equality (1):
 11.  Two instances with identical field values are equal (frozen __eq__).

create() factory (3):
 12.  Returns a ``LineIn`` with the given field values.
 13.  Two successive ``create()`` calls produce different ``id`` values.
 14.  The generated ``id`` is a non-empty string in UUID format.

with_name (2):
 15.  Returns a new instance with ``name`` updated.
 16.  Original instance is unchanged (immutability).

with_device_id (1):
 17.  Returns a new instance with ``device_id`` updated.

with_channel_mapping (2):
 18.  Accepts a list; stores the result as a tuple.
 19.  An empty list passed to ``with_channel_mapping`` raises ``ValueError``.

with_enabled (2):
 20.  ``with_enabled(True)`` sets the flag to True.
 21.  ``with_enabled(False)`` sets the flag to False.

with_description (1):
 22.  Returns a new instance with ``description`` updated.

with_priority (1):
 23.  Returns a new instance with ``priority`` updated.

to_dict (4):
 24.  Returns a dict with exactly the seven expected keys.
 25.  ``channel_mapping`` is serialised as a plain list, not a tuple.
 26.  Values match the instance fields.
 27.  Modifying the returned dict does not affect the instance.

from_dict (5):
 28.  Round-trips correctly: ``from_dict(to_dict())`` equals the original.
 29.  Extra keys in the dict are ignored.
 30.  ``channel_mapping`` list in the dict becomes a tuple after deserialization.
 31.  Missing required key ``name`` raises ``KeyError``.
 32.  An empty ``channel_mapping`` list in the dict raises ``ValueError``
      (propagated from constructor validation).

Migration file (1):
 33.  Django migration module imports cleanly and defines a ``Migration``
      class with ``initial=True`` and a ``CreateModel`` operation targeting
      ``"rastatime_linein"``.

(33 tests total)
"""

from __future__ import annotations

import importlib
import re

import pytest

from audio.linein.domain import LineIn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _linein(**kwargs) -> LineIn:
    defaults = dict(
        id="test-id-001",
        name="Drum Kit",
        device_id="dev-abc123",
        channel_mapping=(0, 1),
    )
    defaults.update(kwargs)
    return LineIn(**defaults)


# ---------------------------------------------------------------------------
# 1–5  Construction and defaults
# ---------------------------------------------------------------------------

def test_all_fields_present_after_construction():
    li = _linein()
    assert hasattr(li, "id")
    assert hasattr(li, "name")
    assert hasattr(li, "device_id")
    assert hasattr(li, "channel_mapping")
    assert hasattr(li, "enabled")
    assert hasattr(li, "description")
    assert hasattr(li, "priority")


def test_enabled_defaults_to_true():
    li = _linein()
    assert li.enabled is True


def test_description_defaults_to_empty_string():
    li = _linein()
    assert li.description == ""


def test_priority_defaults_to_zero():
    li = _linein()
    assert li.priority == 0


def test_channel_mapping_is_tuple():
    li = _linein(channel_mapping=(0, 1))
    assert isinstance(li.channel_mapping, tuple)


# ---------------------------------------------------------------------------
# 6–10  Validation
# ---------------------------------------------------------------------------

def test_blank_name_raises_value_error():
    with pytest.raises(ValueError):
        _linein(name="")


def test_blank_device_id_raises_value_error():
    with pytest.raises(ValueError):
        _linein(device_id="")


def test_empty_channel_mapping_raises_value_error():
    with pytest.raises(ValueError):
        _linein(channel_mapping=())


def test_negative_channel_index_raises_value_error():
    with pytest.raises(ValueError):
        _linein(channel_mapping=(-1, 0))


def test_non_integer_channel_element_raises_type_error():
    with pytest.raises(TypeError):
        _linein(channel_mapping=(0, "1"))


# ---------------------------------------------------------------------------
# 11  Equality
# ---------------------------------------------------------------------------

def test_equality_same_fields():
    a = _linein()
    b = _linein()
    assert a == b


# ---------------------------------------------------------------------------
# 12–14  create() factory
# ---------------------------------------------------------------------------

def test_create_returns_linein_with_given_fields():
    li = LineIn.create(
        name="Interview Mic",
        device_id="dev-xyz",
        channel_mapping=[0],
        enabled=False,
        description="Guest mic",
        priority=5,
    )
    assert li.name        == "Interview Mic"
    assert li.device_id   == "dev-xyz"
    assert li.channel_mapping == (0,)
    assert li.enabled     is False
    assert li.description == "Guest mic"
    assert li.priority    == 5


def test_create_generates_unique_ids():
    a = LineIn.create(name="A", device_id="dev-1", channel_mapping=[0])
    b = LineIn.create(name="B", device_id="dev-2", channel_mapping=[0])
    assert a.id != b.id


def test_create_id_is_uuid_format():
    li = LineIn.create(name="X", device_id="dev-3", channel_mapping=[0])
    assert _UUID_RE.match(li.id), f"Not a UUID: {li.id!r}"


# ---------------------------------------------------------------------------
# 15–16  with_name
# ---------------------------------------------------------------------------

def test_with_name_sets_field():
    updated = _linein().with_name("Kick Drum")
    assert updated.name == "Kick Drum"


def test_with_name_original_unchanged():
    original = _linein()
    _ = original.with_name("Other")
    assert original.name == "Drum Kit"


# ---------------------------------------------------------------------------
# 17  with_device_id
# ---------------------------------------------------------------------------

def test_with_device_id_sets_field():
    updated = _linein().with_device_id("new-dev-id")
    assert updated.device_id == "new-dev-id"


# ---------------------------------------------------------------------------
# 18–19  with_channel_mapping
# ---------------------------------------------------------------------------

def test_with_channel_mapping_accepts_list_stores_tuple():
    updated = _linein().with_channel_mapping([2, 3])
    assert updated.channel_mapping == (2, 3)
    assert isinstance(updated.channel_mapping, tuple)


def test_with_channel_mapping_empty_raises():
    with pytest.raises(ValueError):
        _linein().with_channel_mapping([])


# ---------------------------------------------------------------------------
# 20–21  with_enabled
# ---------------------------------------------------------------------------

def test_with_enabled_true():
    li = _linein(enabled=False).with_enabled(True)
    assert li.enabled is True


def test_with_enabled_false():
    li = _linein(enabled=True).with_enabled(False)
    assert li.enabled is False


# ---------------------------------------------------------------------------
# 22  with_description
# ---------------------------------------------------------------------------

def test_with_description_sets_field():
    updated = _linein().with_description("Used for broadcast interviews")
    assert updated.description == "Used for broadcast interviews"


# ---------------------------------------------------------------------------
# 23  with_priority
# ---------------------------------------------------------------------------

def test_with_priority_sets_field():
    updated = _linein().with_priority(10)
    assert updated.priority == 10


# ---------------------------------------------------------------------------
# 24–27  to_dict
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {"id", "name", "device_id", "channel_mapping",
                  "enabled", "description", "priority",
                  "length_seconds", "device_name"}


def test_to_dict_has_correct_keys():
    d = _linein().to_dict()
    assert set(d.keys()) == _EXPECTED_KEYS


def test_to_dict_channel_mapping_is_list():
    d = _linein(channel_mapping=(0, 1)).to_dict()
    assert isinstance(d["channel_mapping"], list)
    assert d["channel_mapping"] == [0, 1]


def test_to_dict_values_match_fields():
    li = _linein(
        id="specific-id",
        name="Bass DI",
        device_id="dev-bass",
        channel_mapping=(4,),
        enabled=False,
        description="Bass direct-inject",
        priority=3,
    )
    d = li.to_dict()
    assert d["id"]              == "specific-id"
    assert d["name"]            == "Bass DI"
    assert d["device_id"]       == "dev-bass"
    assert d["channel_mapping"] == [4]
    assert d["enabled"]         is False
    assert d["description"]     == "Bass direct-inject"
    assert d["priority"]        == 3


def test_to_dict_mutation_does_not_affect_instance():
    li = _linein(name="Original")
    d = li.to_dict()
    d["name"] = "mutated"
    assert li.name == "Original"   # frozen — unaffected


# ---------------------------------------------------------------------------
# 28–32  from_dict
# ---------------------------------------------------------------------------

def test_from_dict_round_trips():
    original = _linein(
        id="round-trip-id",
        name="Snare",
        device_id="dev-snare",
        channel_mapping=(2, 3),
        enabled=True,
        description="Top snare mic",
        priority=1,
    )
    restored = LineIn.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_ignores_extra_keys():
    data = {
        "id": "x-id", "name": "X", "device_id": "dev-x",
        "channel_mapping": [0], "unknown_key": "ignored",
    }
    li = LineIn.from_dict(data)
    assert li.name == "X"   # present field works; must not raise


def test_from_dict_channel_mapping_becomes_tuple():
    data = {
        "id": "t-id", "name": "T", "device_id": "dev-t",
        "channel_mapping": [0, 1],
    }
    li = LineIn.from_dict(data)
    assert isinstance(li.channel_mapping, tuple)
    assert li.channel_mapping == (0, 1)


def test_from_dict_missing_required_key_name_raises():
    data = {"id": "m-id", "device_id": "dev-m", "channel_mapping": [0]}
    with pytest.raises(KeyError):
        LineIn.from_dict(data)


def test_from_dict_empty_channel_mapping_raises():
    data = {
        "id": "e-id", "name": "Empty", "device_id": "dev-e",
        "channel_mapping": [],
    }
    with pytest.raises(ValueError):
        LineIn.from_dict(data)


# ---------------------------------------------------------------------------
# 33  Migration file validity
# ---------------------------------------------------------------------------

def test_migration_module_imports_and_has_create_model():
    """
    Verify the Django migration file is syntactically valid and well-formed.

    Skipped automatically if Django is not installed in the current environment.
    """
    pytest.importorskip(
        "django.db.migrations",
        reason="Django not installed in this environment — skipping migration validation",
    )
    from django.db.migrations.operations.models import CreateModel

    mod = importlib.import_module(
        "libretime_api.linein.migrations.0001_initial"
    )
    assert hasattr(mod, "Migration"), "Migration class missing"
    mig = mod.Migration
    assert getattr(mig, "initial", False) is True, "Migration.initial must be True"

    create_ops = [op for op in mig.operations if isinstance(op, CreateModel)]
    assert len(create_ops) == 1, "Expected exactly one CreateModel operation"

    create_op = create_ops[0]
    assert create_op.name == "LineIn"

    options = create_op.options or {}
    assert options.get("db_table") == "rastatime_linein"
