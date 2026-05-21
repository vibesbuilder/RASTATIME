"""
T13.1 — SoundcardSettings domain model unit tests.

Exercises the pure :class:`~audio.soundcard.settings_model.SoundcardSettings`
dataclass without Django, database, or audio hardware.

Test inventory
--------------
Construction and defaults (4):
  1.  Default construction: all fields at documented defaults.
  2.  main_output_id and preview_output_id default to None.
  3.  line_in_device_ids defaults to an empty tuple.
  4.  Two instances with the same field values are equal (frozen dataclass __eq__).

Derived properties (6):
  5.  is_output_configured() is False when main_output_id is None.
  6.  is_output_configured() is True when main_output_id is set.
  7.  has_preview_output() is False when preview_output_id is None.
  8.  has_preview_output() is True when preview_output_id is set.
  9.  has_line_ins() is False on a fresh instance.
 10.  has_line_ins() is True after a line-in is added.

with_main_output (3):
 11.  Returns a new instance with main_output_id set.
 12.  Original instance is unchanged (immutability).
 13.  Chaining preserves other fields.

without_main_output (2):
 14.  Clears main_output_id to None on an instance that had it set.
 15.  No-op on an instance already at None (returns equal new instance).

with_preview_output (3):
 16.  Sets preview_output_id to a stable_id.
 17.  Passing None clears the preview output.
 18.  Preserves other fields.

with_line_in_added (3):
 19.  Appends a new stable_id to line_in_device_ids.
 20.  Idempotent: adding the same id twice does not create a duplicate.
 21.  Preserves other fields and ordering of existing IDs.

with_line_in_removed (3):
 22.  Removes a present stable_id from line_in_device_ids.
 23.  Silent no-op for an id not in the list.
 24.  Preserves the order of remaining IDs.

to_dict (4):
 25.  Returns a dict with exactly the three expected keys.
 26.  Values match the instance fields (None stays None).
 27.  line_in_device_ids is serialised as a plain list (not a tuple).
 28.  Modifying the returned dict does not affect the instance.

from_dict (4):
 29.  Round-trips correctly: from_dict(to_dict()) equals original.
 30.  Missing keys fall back to defaults (empty dict → all defaults).
 31.  Extra keys in the dict are ignored.
 32.  Empty string values for IDs are normalised to None.

Migration file (1):
 33.  Django migration module imports cleanly and defines a Migration class
      with initial=True and a CreateModel operation.

(33 tests total)
"""

from __future__ import annotations

import importlib

import pytest

from audio.soundcard.settings_model import SoundcardSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(**kwargs) -> SoundcardSettings:
    return SoundcardSettings(**kwargs)


# ---------------------------------------------------------------------------
# 1–4  Construction and defaults
# ---------------------------------------------------------------------------

def test_default_construction_fields_present():
    s = SoundcardSettings()
    assert hasattr(s, "main_output_id")
    assert hasattr(s, "preview_output_id")
    assert hasattr(s, "line_in_device_ids")


def test_default_ids_are_none():
    s = SoundcardSettings()
    assert s.main_output_id    is None
    assert s.preview_output_id is None


def test_default_line_in_is_empty_tuple():
    s = SoundcardSettings()
    assert s.line_in_device_ids == ()
    assert isinstance(s.line_in_device_ids, tuple)


def test_equality_same_fields():
    a = SoundcardSettings(main_output_id="out-1", preview_output_id=None,
                          line_in_device_ids=("in-1",))
    b = SoundcardSettings(main_output_id="out-1", preview_output_id=None,
                          line_in_device_ids=("in-1",))
    assert a == b


# ---------------------------------------------------------------------------
# 5–10  Derived properties
# ---------------------------------------------------------------------------

def test_is_output_configured_false_by_default():
    assert SoundcardSettings().is_output_configured() is False


def test_is_output_configured_true_when_set():
    s = SoundcardSettings(main_output_id="out-1")
    assert s.is_output_configured() is True


def test_has_preview_output_false_by_default():
    assert SoundcardSettings().has_preview_output() is False


def test_has_preview_output_true_when_set():
    s = SoundcardSettings(preview_output_id="prev-1")
    assert s.has_preview_output() is True


def test_has_line_ins_false_by_default():
    assert SoundcardSettings().has_line_ins() is False


def test_has_line_ins_true_after_add():
    s = SoundcardSettings().with_line_in_added("in-1")
    assert s.has_line_ins() is True


# ---------------------------------------------------------------------------
# 11–13  with_main_output
# ---------------------------------------------------------------------------

def test_with_main_output_sets_field():
    s = SoundcardSettings().with_main_output("out-42")
    assert s.main_output_id == "out-42"


def test_with_main_output_original_unchanged():
    original = SoundcardSettings()
    _ = original.with_main_output("out-42")
    assert original.main_output_id is None  # frozen — original must not change


def test_with_main_output_preserves_other_fields():
    base = SoundcardSettings(preview_output_id="prev-1",
                              line_in_device_ids=("in-1",))
    updated = base.with_main_output("out-1")
    assert updated.preview_output_id  == "prev-1"
    assert updated.line_in_device_ids == ("in-1",)


# ---------------------------------------------------------------------------
# 14–15  without_main_output
# ---------------------------------------------------------------------------

def test_without_main_output_clears_field():
    s = SoundcardSettings(main_output_id="out-1").without_main_output()
    assert s.main_output_id is None


def test_without_main_output_noop_when_already_none():
    s = SoundcardSettings()
    cleared = s.without_main_output()
    assert cleared.main_output_id is None
    assert cleared == s


# ---------------------------------------------------------------------------
# 16–18  with_preview_output
# ---------------------------------------------------------------------------

def test_with_preview_output_sets_field():
    s = SoundcardSettings().with_preview_output("prev-1")
    assert s.preview_output_id == "prev-1"


def test_with_preview_output_none_clears_field():
    s = SoundcardSettings(preview_output_id="prev-1").with_preview_output(None)
    assert s.preview_output_id is None


def test_with_preview_output_preserves_other_fields():
    base = SoundcardSettings(main_output_id="out-1", line_in_device_ids=("in-1",))
    updated = base.with_preview_output("prev-2")
    assert updated.main_output_id    == "out-1"
    assert updated.line_in_device_ids == ("in-1",)


# ---------------------------------------------------------------------------
# 19–21  with_line_in_added
# ---------------------------------------------------------------------------

def test_with_line_in_added_appends():
    s = SoundcardSettings().with_line_in_added("in-1")
    assert "in-1" in s.line_in_device_ids


def test_with_line_in_added_idempotent():
    s = SoundcardSettings().with_line_in_added("in-1").with_line_in_added("in-1")
    assert s.line_in_device_ids.count("in-1") == 1


def test_with_line_in_added_preserves_order_and_other_fields():
    base = SoundcardSettings(main_output_id="out-1",
                              line_in_device_ids=("in-1", "in-2"))
    updated = base.with_line_in_added("in-3")
    assert updated.line_in_device_ids == ("in-1", "in-2", "in-3")
    assert updated.main_output_id == "out-1"


# ---------------------------------------------------------------------------
# 22–24  with_line_in_removed
# ---------------------------------------------------------------------------

def test_with_line_in_removed_removes_present_id():
    s = SoundcardSettings(line_in_device_ids=("in-1", "in-2")).with_line_in_removed("in-1")
    assert "in-1" not in s.line_in_device_ids
    assert "in-2" in s.line_in_device_ids


def test_with_line_in_removed_noop_for_unknown_id():
    base = SoundcardSettings(line_in_device_ids=("in-1",))
    result = base.with_line_in_removed("in-999")
    assert result.line_in_device_ids == ("in-1",)


def test_with_line_in_removed_preserves_order():
    s = SoundcardSettings(line_in_device_ids=("in-1", "in-2", "in-3"))
    result = s.with_line_in_removed("in-2")
    assert result.line_in_device_ids == ("in-1", "in-3")


# ---------------------------------------------------------------------------
# 25–28  to_dict
# ---------------------------------------------------------------------------

_EXPECTED_DICT_KEYS = {"main_output_id", "preview_output_id", "line_in_device_ids",
                        "main_output_name", "preview_output_name"}


def test_to_dict_has_correct_keys():
    d = SoundcardSettings().to_dict()
    assert set(d.keys()) == _EXPECTED_DICT_KEYS


def test_to_dict_values_match_fields():
    s = SoundcardSettings(main_output_id="out-1", preview_output_id="prev-1",
                           line_in_device_ids=("in-1", "in-2"))
    d = s.to_dict()
    assert d["main_output_id"]     == "out-1"
    assert d["preview_output_id"]  == "prev-1"
    assert d["line_in_device_ids"] == ["in-1", "in-2"]


def test_to_dict_line_in_device_ids_is_list_not_tuple():
    s = SoundcardSettings(line_in_device_ids=("in-1",))
    d = s.to_dict()
    assert isinstance(d["line_in_device_ids"], list)


def test_to_dict_mutation_does_not_affect_instance():
    s = SoundcardSettings(main_output_id="out-1")
    d = s.to_dict()
    d["main_output_id"] = "mutated"
    assert s.main_output_id == "out-1"   # frozen — unaffected


# ---------------------------------------------------------------------------
# 29–32  from_dict
# ---------------------------------------------------------------------------

def test_from_dict_round_trips():
    original = SoundcardSettings(
        main_output_id="out-1",
        preview_output_id="prev-1",
        line_in_device_ids=("in-1", "in-2"),
    )
    restored = SoundcardSettings.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_empty_gives_defaults():
    s = SoundcardSettings.from_dict({})
    assert s.main_output_id    is None
    assert s.preview_output_id is None
    assert s.line_in_device_ids == ()


def test_from_dict_ignores_extra_keys():
    s = SoundcardSettings.from_dict({"main_output_id": "out-1", "unknown_key": "ignored"})
    assert s.main_output_id == "out-1"   # field present
    # Must not raise


def test_from_dict_empty_string_normalised_to_none():
    s = SoundcardSettings.from_dict({
        "main_output_id":    "",
        "preview_output_id": "",
    })
    assert s.main_output_id    is None
    assert s.preview_output_id is None


# ---------------------------------------------------------------------------
# 33  Migration file validity
# ---------------------------------------------------------------------------

def test_migration_module_imports_and_has_create_model():
    """
    Verify the Django migration file is syntactically valid and well-formed.

    Imports ``django.db.migrations`` and checks that the Migration class
    exists with ``initial=True`` and a CreateModel operation for the
    correct table.  Skipped automatically if Django is not installed in
    the current Python environment (the root venv does not include Django;
    the backend/api venv does).
    """
    django_migrations = pytest.importorskip(
        "django.db.migrations",
        reason="Django not installed in this environment — skipping migration validation",
    )
    from django.db.migrations.operations.models import CreateModel

    mod = importlib.import_module(
        "libretime_api.soundcard.migrations.0001_initial"
    )
    assert hasattr(mod, "Migration"), "Migration class missing"
    mig = mod.Migration
    assert getattr(mig, "initial", False) is True, "Migration.initial must be True"

    create_ops = [
        op for op in mig.operations
        if isinstance(op, CreateModel)
    ]
    assert len(create_ops) == 1, "Expected exactly one CreateModel operation"

    create_op = create_ops[0]
    assert create_op.name == "SoundcardSettings"

    # Verify the table name is set in options
    options = create_op.options or {}
    assert options.get("db_table") == "rastatime_soundcard_settings"
