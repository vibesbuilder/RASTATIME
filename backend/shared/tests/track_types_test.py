from dataclasses import dataclass
from typing import Optional

import pytest
from rastatime_shared.track_types import match_track_type, normalise_type_value


@dataclass
class _Type:
    code: str
    name: Optional[str]


TYPES = [
    _Type("show", "Shows"),
    _Type("music", "Music"),
    _Type("jngl", "Jingles"),
    _Type("news", "News"),
]


@pytest.mark.parametrize(
    "value, code",
    [
        ("jngl", "jngl"),
        ("Jingles", "jngl"),
        ("JINGLES", "jngl"),
        ("  jingles ", "jngl"),
        ("Music", "music"),
        ("music", "music"),
        ("news", "news"),
    ],
)
def test_code_or_name_names_the_type(value, code):
    found = match_track_type(value, TYPES)
    assert found is not None
    assert found.code == code


@pytest.mark.parametrize(
    "value", ["", None, "   ", "Jingle", "CD", "Digital Media", "Music; Jingles", "DIG"]
)
def test_anything_else_names_nothing(value):
    assert match_track_type(value, TYPES) is None


def test_code_wins_over_another_types_name():
    types = [_Type("news", "Bulletins"), _Type("nws", "News")]
    assert match_track_type("news", types).code == "news"
    assert match_track_type("NEWS", types).code == "news"


def test_a_shared_name_names_nothing():
    types = [_Type("ad1", "Ads"), _Type("ad2", "Ads")]
    assert match_track_type("Ads", types) is None
    assert match_track_type("ad2", types).code == "ad2"


def test_a_type_without_name_still_matches_by_code():
    assert match_track_type("recs", [_Type("recs", None)]).code == "recs"
    assert match_track_type("", [_Type("recs", None)]) is None


def test_inner_blanks_collapse():
    assert normalise_type_value("Station   ID") == "station id"
    assert match_track_type("station id", [_Type("sid", "Station ID")]).code == "sid"
