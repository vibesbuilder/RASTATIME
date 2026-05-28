"""
recording_path — Helpers for building per-show recording file paths.

RASTATIME 2026-05-28 — Phase-C5 Teil 2d.  Extracted from the deleted
``engine.ffmpeg_recorder`` module so the Liquidsoap-engine recording
path (PlayoutScheduler._on_show_record_start) can continue to use the
same path-building rules.

Format::

    <recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3

Dates + times are rendered in the system's local timezone so operator-
visible filenames match wall-clock time on the studio computer.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

# NTFS-illegal characters in a filename: <>:"/\|?*  plus the ASCII
# control range (which Windows also rejects).  Everything else
# — including Umlauts and spaces — is kept verbatim per design
# decision 2026-05-17.
_FILENAME_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


def sanitize_show_name(name: str) -> str:
    """
    Strip NTFS-illegal characters from a show name for use in a
    filename.  Umlauts and spaces are kept.  Empty input returns
    "untitled" so the filename still has a meaningful body.
    """
    cleaned = _FILENAME_FORBIDDEN.sub("_", (name or "").strip())
    # Collapse runs of underscores so "C++/C#" → "C__C_" → "C_C_"
    cleaned = re.sub(r"_+", "_", cleaned).strip("_ ")
    return cleaned or "untitled"


def build_output_path(
    recording_folder: Path,
    show_starts_at: datetime,
    show_name: str,
) -> Path:
    """
    Compose the output path:

        <recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3

    Date and time are derived from ``show_starts_at`` and rendered in
    the **system's local timezone** so operator-visible filenames
    match wall-clock time on the studio computer.  Pythons
    ``datetime.astimezone()`` consults the system TZ at call time, so
    DST switches (Europe/Berlin: CET <-> CEST) are handled
    transparently: a show scheduled at 13:00 local time produces
    ``13-00`` in the filename in both summer (UTC+2) and winter
    (UTC+1).  The show-name is sanitized; spaces and Umlauts are kept.

    The scheduler hands us a naive UTC datetime (Pydantic strips
    tzinfo in ``event_isoparse``), so we re-attach UTC before
    converting.  If a non-naive datetime is passed it is converted
    as-is.

    Example (operator in Europe/Berlin, May / DST = UTC+2):
        recording_folder = C:/rastatime/recordings
        show_starts_at   = datetime(2026, 5, 17, 11, 0)  # naive UTC = 13:00 local
        show_name        = "Müllers Frühstück"
        -> C:/rastatime/recordings/2026-05-17/2026-05-17 13-00 - Müllers Frühstück.mp3
    """
    if show_starts_at.tzinfo is None:
        show_starts_at = show_starts_at.replace(tzinfo=timezone.utc)
    local_dt = show_starts_at.astimezone()  # system local tz
    day_str = local_dt.strftime("%Y-%m-%d")
    time_str = local_dt.strftime("%H-%M")
    name = sanitize_show_name(show_name)
    filename = f"{day_str} {time_str} - {name}.mp3"
    return recording_folder / day_str / filename
