"""
RASTATIME 2026-11-13 - Auto DJ buffer tracks (ARCHITECTURE §23.107).

When the Auto DJ fill pass finds nothing short enough for a leftover gap
of more than 5 s and at most "Maximum Gap" seconds, the legacy app appends
a track from the operator's buffer playlist (Settings -> Auto DJ) as the
show's last row.  It is the only row meant to run past the show end: this
API caps its cue-out at the show end like any overbooked row
(``Schedule.get_cue_out``) and, with "At the End of the Show: Fade Out",
tells the playout to fade it over its last N seconds instead of the house
show crossfade (``buffer_fade_out`` on the schedule row).

A row is a buffer row when its file is in the buffer playlist and it runs
past its show's end - recognised by the file, no column of its own
(operator decision 2026-11-13, "variant a").  The legacy app applies the
same rule (``Application_Service_AutoDjService::bufferFileIds``).
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from ..core.models import Preference
from .models import Playlist, PlaylistContent

PREF_PLAYLIST = "auto_dj_buffer_playlist_id"
PREF_MAX_GAP = "auto_dj_buffer_max_gap"
PREF_END_MODE = "auto_dj_buffer_end_mode"
PREF_FADE = "auto_dj_buffer_fade_seconds"

#: the fill pass threshold - smaller leftovers stay silent
MIN_GAP_SECONDS = 5.0
#: a buffer track must outlast the gap by the crossfade overlap + a margin
MARGIN_SECONDS = 5.0
DEFAULT_MAX_GAP_SECONDS = 60.0
#: the playout's crossfade buffer (3 s today) bounds the fade
MAX_FADE_SECONDS = 3.0
DEFAULT_FADE_SECONDS = 3.0


@dataclass(frozen=True)
class BufferSettings:
    playlist_id: Optional[int]
    max_gap: float
    #: seconds to fade a buffer row out at the show end; None = cut
    #: (the house show crossfade of the boundary)
    fade: Optional[float]
    file_ids: frozenset


def _float(raw, default: float) -> float:
    try:
        return float(raw) if raw not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _playlist_id(raw) -> Optional[int]:
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _entries(*keys: str) -> dict:
    return dict(Preference.site.filter(key__in=keys).values_list("key", "value"))


def load_buffer_settings() -> BufferSettings:
    entries = _entries(PREF_PLAYLIST, PREF_MAX_GAP, PREF_END_MODE, PREF_FADE)
    playlist_id = _playlist_id(entries.get(PREF_PLAYLIST))
    fade = None
    if entries.get(PREF_END_MODE) == "fade":
        fade = min(max(_float(entries.get(PREF_FADE), DEFAULT_FADE_SECONDS), 0.1), MAX_FADE_SECONDS)
    file_ids: frozenset = frozenset()
    if playlist_id is not None:
        file_ids = frozenset(
            PlaylistContent.objects.filter(
                playlist_id=playlist_id,
                kind=PlaylistContent.Kind.FILE,
                file__isnull=False,
            ).values_list("file_id", flat=True)
        )
    return BufferSettings(
        playlist_id=playlist_id,
        max_gap=_float(entries.get(PREF_MAX_GAP), DEFAULT_MAX_GAP_SECONDS),
        fade=fade,
        file_ids=file_ids,
    )


def is_buffer_row(row, settings: BufferSettings) -> bool:
    """The row's file is in the buffer playlist and it runs past its show's end."""
    if row.file_id is None or row.file_id not in settings.file_ids:
        return False
    show_end = row.instance.ends_at
    return row.starts_at < show_end < row.ends_at


def buffer_fade_out(row, settings: BufferSettings) -> Optional[float]:
    """Seconds the playout fades this row out at the show end (None = house shape)."""
    if settings.fade is None or not is_buffer_row(row, settings):
        return None
    return settings.fade


def buffer_status() -> dict:
    """
    For the playout's preflight scan (``auto_dj_buffer_unusable``): is the
    buffer configured and does its playlist hold a track that outlasts the
    maximum gap?  ``active`` is False when Auto DJ, "fill any show" or the
    buffer playlist is off - nothing to warn about then.
    """
    entries = _entries("auto_dj_enabled", "auto_dj_fill_any_show", PREF_PLAYLIST, PREF_MAX_GAP)
    playlist_id = _playlist_id(entries.get(PREF_PLAYLIST))
    active = (
        entries.get("auto_dj_enabled") == "true"
        and entries.get("auto_dj_fill_any_show") == "true"
        and playlist_id is not None
    )
    if not active:
        return {"active": False}
    max_gap = _float(entries.get(PREF_MAX_GAP), DEFAULT_MAX_GAP_SECONDS)
    files = PlaylistContent.objects.filter(
        playlist_id=playlist_id, kind=PlaylistContent.Kind.FILE, file__isnull=False
    )
    playable = files.filter(file__exists=True, file__disabled=False).exclude(file__hidden=True)
    usable = playable.filter(length__gt=timedelta(seconds=max_gap + MARGIN_SECONDS))
    longest = max((c.length for c in playable if c.length is not None), default=None)
    return {
        "active": True,
        "playlist_id": playlist_id,
        "playlist_exists": Playlist.objects.filter(id=playlist_id).exists(),
        "max_gap": max_gap,
        "required_seconds": max_gap + MARGIN_SECONDS,
        "tracks": files.count(),
        "playable": playable.count(),
        "usable": usable.count(),
        "longest_seconds": round(longest.total_seconds(), 1) if longest is not None else None,
    }
