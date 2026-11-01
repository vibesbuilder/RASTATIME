"""
RASTATIME 2026-09-13 — ICY metadata preferences (Settings → Streams).

What listeners see in their player comes from three ``cc_pref`` keys:

* ``stream_label_format`` — the "Stream Label" radio: 0 Artist - Title,
  1 Show - Artist - Title, 2 Station name - Show name.
* ``off_air_meta`` — the "Off Air Metadata" text shown while nothing
  is on air (the bus sits on the silence fallback).
* ``station_name`` — Settings → General, used by format 2 and as the
  last-resort label.

Until 2026-09-13 none of them reached the Liquidsoap script: the PHP
side published the change on RabbitMQ (nobody listens in RASTATIME)
and the rendered script had no off-air handling, so Icecast kept the
last track's title for hours.  Now the values are rendered into
rastatime.liq as defaults (``${ICY_METADATA_BLOCK}``) and the scheduler
re-reads them on every schedule refresh, pushing changes over telnet
(``var.set icy_format / offair_text / station_name``) - a Settings
change takes effect within one refresh cycle, no restart.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

FORMAT_ARTIST_TITLE = 0
FORMAT_SHOW_ARTIST_TITLE = 1
FORMAT_STATION_SHOW = 2
VALID_FORMATS = (FORMAT_ARTIST_TITLE, FORMAT_SHOW_ARTIST_TITLE, FORMAT_STATION_SHOW)

DEFAULT_ICY_FORMAT = FORMAT_ARTIST_TITLE
DEFAULT_OFFAIR_TEXT = "Offline"
DEFAULT_STATION_NAME = "RASTATIME"

_PREF_FORMAT = "stream_label_format"
_PREF_OFFAIR = "off_air_meta"
_PREF_STATION = "station_name"


@dataclass(frozen=True)
class IcyPreferences:
    """The three values the Liquidsoap script needs for its ICY titles."""

    label_format: int = DEFAULT_ICY_FORMAT
    offair_text: str = DEFAULT_OFFAIR_TEXT
    station_name: str = DEFAULT_STATION_NAME


def _clean_text(value: object, default: str) -> str:
    """One line of text: strip, collapse line breaks (they would end the
    telnet command), fall back to ``default`` when empty."""
    text = " ".join(str(value or "").split())
    return text or default


def parse_icy_preferences(entries: Mapping[str, object]) -> IcyPreferences:
    """
    Build :class:`IcyPreferences` from a ``cc_pref`` key/value mapping.
    Tolerant: a missing or malformed ``stream_label_format`` means
    format 0, empty texts fall back to the defaults.
    """
    raw_format = entries.get(_PREF_FORMAT)
    try:
        label_format = (
            int(str(raw_format).strip()) if raw_format not in (None, "") else DEFAULT_ICY_FORMAT
        )
    except (TypeError, ValueError):
        logger.warning(
            "cc_pref %s=%r is not an integer - using %d",
            _PREF_FORMAT,
            raw_format,
            DEFAULT_ICY_FORMAT,
        )
        label_format = DEFAULT_ICY_FORMAT
    if label_format not in VALID_FORMATS:
        logger.warning(
            "cc_pref %s=%r is not one of %s - using %d",
            _PREF_FORMAT,
            raw_format,
            VALID_FORMATS,
            DEFAULT_ICY_FORMAT,
        )
        label_format = DEFAULT_ICY_FORMAT
    return IcyPreferences(
        label_format=label_format,
        offair_text=_clean_text(entries.get(_PREF_OFFAIR), DEFAULT_OFFAIR_TEXT),
        station_name=_clean_text(entries.get(_PREF_STATION), DEFAULT_STATION_NAME),
    )


def read_icy_preferences_from_db() -> Optional[IcyPreferences]:
    """
    Read the three keys through the Django ORM (same path as the stream
    outputs and the crossfade duration in ``__main__``).  ``None`` when
    the ORM is unavailable - the caller then keeps what it has.
    """
    try:
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]  # noqa: PLC0415

        entries = dict(Preference.site.values_list("key", "value"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read the ICY metadata preferences from the DB: %s", exc)
        return None
    return parse_icy_preferences(entries)
