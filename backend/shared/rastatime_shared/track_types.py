"""
RASTATIME 2026-11-09 - the track type a "Media Type" tag (ID3 TMED) names.

One rule for the import (the analyzer, against the track types the legacy
app sends with the import message) and for "Re-read Tags" (the API, against
the track type table): the tag value is compared with every type's code
first and then with its name, ignoring case and surrounding / repeated
blanks.  "Jingles", "JINGLES" and "jngl" all name the type with code
"jngl" and name "Jingles"; "Jingle" names nothing.  A value that names no
type, or a name two types share, names nothing - the tag is then ignored
and the track keeps the type it would get without the tag.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional, TypeVar

T = TypeVar("T")


def normalise_type_value(value: Any) -> str:
    """The comparison form: blanks collapsed, case folded."""
    return " ".join(str(value or "").split()).casefold()


def match_track_type(value: Any, types: Iterable[T]) -> Optional[T]:
    """
    The type (an object with ``code`` and ``name`` attributes) the value
    names, or None.  The codes are unique; a name counts only when exactly
    one type carries it.
    """
    wanted = normalise_type_value(value)
    if not wanted:
        return None
    candidates = list(types)
    for item in candidates:
        if normalise_type_value(getattr(item, "code", "")) == wanted:
            return item
    by_name = [
        item for item in candidates if normalise_type_value(getattr(item, "name", "")) == wanted
    ]
    return by_name[0] if len(by_name) == 1 else None
