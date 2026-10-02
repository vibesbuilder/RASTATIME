"""
T14.2 / T14.3 — Pure serialization and validation helpers for the Line-In API.

No Django import — this module can be used in unit tests without a
running application server.  It mirrors the design of
:mod:`audio.soundcard._api_helpers`.
"""

from __future__ import annotations

import math
from typing import Iterable

from .domain import INPUT_GAIN_DB_MAX, INPUT_GAIN_DB_MIN, LineIn


# ---------------------------------------------------------------------------
# Serialisation (T14.2)
# ---------------------------------------------------------------------------

def serialize_linein(linein: LineIn) -> dict:
    """
    Convert a :class:`~audio.linein.domain.LineIn` domain instance to a
    JSON-serialisable dict.

    Returns
    -------
    dict
        Keys: ``id``, ``name``, ``device_id``, ``channel_mapping``
        (plain list), ``enabled`` (bool), ``description``, ``priority`` (int).
    """
    return {
        "id":              linein.id,
        "name":            linein.name,
        "device_id":       linein.device_id,
        "device_name":     linein.device_name,
        "channel_mapping": list(linein.channel_mapping),
        "enabled":         bool(linein.enabled),
        "description":     linein.description,
        "priority":        int(linein.priority),
        "length_seconds":  linein.length_seconds,
        "input_gain_db":   float(linein.input_gain_db),
    }


def list_lineins_response(lineins: Iterable[LineIn]) -> dict:
    """
    Build the list API response dict from an iterable of domain objects.

    Returns
    -------
    dict
        ``{"line_ins": [serialize_linein(li) for li in lineins]}``.
        Always returns the ``"line_ins"`` key, even if the list is empty.
    """
    return {"line_ins": [serialize_linein(li) for li in lineins]}


# ---------------------------------------------------------------------------
# Body validation (T14.3)
# ---------------------------------------------------------------------------

def parse_linein_create_body(body: dict) -> dict:
    """
    Validate and normalise a POST (create) request body.

    All three required fields must be present; optional fields fall back
    to domain defaults.

    Parameters
    ----------
    body:
        Decoded JSON dict from the request body.

    Returns
    -------
    dict
        Validated field dict ready for :meth:`~audio.linein.domain.LineIn.create`.

    Raises
    ------
    ValueError
        If any required field is missing or any field fails type/value
        validation.
    """
    # --- required ---
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("'name' must be a non-empty string")

    device_id = body.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("'device_id' must be a non-empty string")

    channel_mapping = body.get("channel_mapping")
    if not isinstance(channel_mapping, list) or len(channel_mapping) == 0:
        raise ValueError("'channel_mapping' must be a non-empty list")
    _validate_channel_mapping(channel_mapping)

    # --- optional ---
    enabled = body.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("'enabled' must be a boolean")

    description = body.get("description", "")
    if not isinstance(description, str):
        raise ValueError("'description' must be a string")

    priority = body.get("priority", 0)
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("'priority' must be an integer")

    length_seconds = body.get("length_seconds")
    if length_seconds is not None:
        if not isinstance(length_seconds, int) or isinstance(length_seconds, bool):
            raise ValueError("'length_seconds' must be a non-negative integer or null")
        if length_seconds < 0:
            raise ValueError("'length_seconds' must be a non-negative integer or null")

    # RASTATIME 2026-05-14 — device_name optional (default "").  Older
    # frontend clients won't include it; that's OK, the resolver's
    # name-fallback is then a no-op for that row.
    device_name = body.get("device_name", "")
    if not isinstance(device_name, str):
        raise ValueError("'device_name' must be a string (may be empty)")

    # RASTATIME 2026-10-02 - optional static input gain (default 0 dB).
    input_gain_db = _validate_input_gain_db(body.get("input_gain_db", 0.0))

    return {
        "name":            name.strip(),
        "device_id":       device_id.strip(),
        "device_name":     device_name,
        "channel_mapping": channel_mapping,
        "enabled":         enabled,
        "description":     description,
        "priority":        priority,
        "length_seconds":  length_seconds,
        "input_gain_db":   input_gain_db,
    }


def parse_linein_patch_body(body: dict) -> dict:
    """
    Validate and normalise a PATCH (partial update) request body.

    Any subset of fields may be provided; fields not in *body* are not
    returned and must not overwrite existing values.

    Returns
    -------
    dict
        Validated subset of fields to apply.

    Raises
    ------
    ValueError
        If a provided field fails type/value validation.
    """
    out: dict = {}

    if "name" in body:
        val = body["name"]
        if not isinstance(val, str) or not val.strip():
            raise ValueError("'name' must be a non-empty string")
        out["name"] = val.strip()

    if "device_id" in body:
        val = body["device_id"]
        if not isinstance(val, str) or not val.strip():
            raise ValueError("'device_id' must be a non-empty string")
        out["device_id"] = val.strip()

    if "device_name" in body:
        val = body["device_name"]
        if not isinstance(val, str):
            raise ValueError("'device_name' must be a string (may be empty)")
        out["device_name"] = val

    if "channel_mapping" in body:
        val = body["channel_mapping"]
        if not isinstance(val, list) or len(val) == 0:
            raise ValueError("'channel_mapping' must be a non-empty list")
        _validate_channel_mapping(val)
        out["channel_mapping"] = val

    if "enabled" in body:
        val = body["enabled"]
        if not isinstance(val, bool):
            raise ValueError("'enabled' must be a boolean")
        out["enabled"] = val

    if "description" in body:
        val = body["description"]
        if not isinstance(val, str):
            raise ValueError("'description' must be a string")
        out["description"] = val

    if "priority" in body:
        val = body["priority"]
        if not isinstance(val, int) or isinstance(val, bool):
            raise ValueError("'priority' must be an integer")
        out["priority"] = val

    if "length_seconds" in body:
        val = body["length_seconds"]
        if val is not None:
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValueError(
                    "'length_seconds' must be a non-negative integer or null"
                )
            if val < 0:
                raise ValueError(
                    "'length_seconds' must be a non-negative integer or null"
                )
        out["length_seconds"] = val

    if "input_gain_db" in body:
        out["input_gain_db"] = _validate_input_gain_db(body["input_gain_db"])

    return out


def _validate_input_gain_db(val) -> float:
    """
    RASTATIME 2026-10-02 - a finite number within the domain range
    (-20..+20 dB); returned as float.  Raises ValueError otherwise.
    """
    if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
        raise ValueError("'input_gain_db' must be a number")
    if not INPUT_GAIN_DB_MIN <= val <= INPUT_GAIN_DB_MAX:
        raise ValueError(
            f"'input_gain_db' must be between {INPUT_GAIN_DB_MIN:+.0f} "
            f"and {INPUT_GAIN_DB_MAX:+.0f} dB"
        )
    return float(val)


def _validate_channel_mapping(mapping: list) -> None:
    """Raise ValueError if any element is not a non-negative integer."""
    for idx, ch in enumerate(mapping):
        if not isinstance(ch, int) or isinstance(ch, bool):
            raise ValueError(
                f"channel_mapping[{idx}] must be an int, got {type(ch).__name__!r}"
            )
        if ch < 0:
            raise ValueError(
                f"channel_mapping[{idx}] must be >= 0, got {ch!r}"
            )
