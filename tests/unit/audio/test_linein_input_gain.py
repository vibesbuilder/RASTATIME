"""
RASTATIME 2026-10-02 - per-line-in static input gain (input_gain_db):
domain validation, builders, dict round trip, API body validation and
serialisation.  The playout side is covered in
backend/playout/tests/test_scheduler_linein.py.
"""

from __future__ import annotations

import math

import pytest

from audio.linein._api_helpers import (
    parse_linein_create_body,
    parse_linein_patch_body,
    serialize_linein,
)
from audio.linein.domain import LineIn


def _linein(**kw) -> LineIn:
    return LineIn.create(name="Studio A", device_id="dev-1", channel_mapping=[4, 5], **kw)


_CREATE = {"name": "Studio A", "device_id": "dev-1", "channel_mapping": [4, 5]}


# ---- domain -------------------------------------------------------------

def test_gain_defaults_to_zero():
    assert _linein().input_gain_db == 0.0


@pytest.mark.parametrize("gain", [-20.0, -3.5, 0, 6, 20.0])
def test_gain_within_range_is_accepted(gain):
    assert _linein(input_gain_db=gain).input_gain_db == gain


@pytest.mark.parametrize("gain", [-20.1, 20.1, math.inf, math.nan])
def test_gain_out_of_range_raises(gain):
    with pytest.raises(ValueError):
        _linein(input_gain_db=gain)


@pytest.mark.parametrize("gain", ["6", True, None])
def test_gain_must_be_a_number(gain):
    with pytest.raises(TypeError):
        _linein(input_gain_db=gain)


def test_every_builder_keeps_the_gain():
    li = _linein(input_gain_db=4.5)
    built = [
        li.with_name("B"), li.with_device_id("dev-2"), li.with_channel_mapping([0]),
        li.with_enabled(False), li.with_description("x"), li.with_priority(3),
        li.with_length_seconds(60), li.with_device_name("Line"),
    ]
    assert all(b.input_gain_db == 4.5 for b in built)
    assert li.with_input_gain_db(-2.0).input_gain_db == -2.0


def test_dict_round_trip_and_legacy_dict():
    li = _linein(input_gain_db=-6.0)
    assert LineIn.from_dict(li.to_dict()) == li
    legacy = li.to_dict()
    del legacy["input_gain_db"]
    assert LineIn.from_dict(legacy).input_gain_db == 0.0


# ---- API helpers ----------------------------------------------------------

def test_serialize_includes_the_gain_as_float():
    assert serialize_linein(_linein(input_gain_db=3)).get("input_gain_db") == 3.0


def test_create_body_gain_is_optional_and_validated():
    assert parse_linein_create_body(dict(_CREATE))["input_gain_db"] == 0.0
    assert parse_linein_create_body({**_CREATE, "input_gain_db": 6})["input_gain_db"] == 6.0
    for bad in ("6", True, 25.0, -21):
        with pytest.raises(ValueError):
            parse_linein_create_body({**_CREATE, "input_gain_db": bad})


def test_patch_body_only_carries_the_gain_when_sent():
    assert "input_gain_db" not in parse_linein_patch_body({"name": "B"})
    assert parse_linein_patch_body({"input_gain_db": -4.5}) == {"input_gain_db": -4.5}
    with pytest.raises(ValueError):
        parse_linein_patch_body({"input_gain_db": 30})
