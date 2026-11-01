"""
cue_writer — per-hour cue sidecars for the 24/7 archive recordings.

RASTATIME 2026-06-05 — Record-per-Hour stage 5.

For every hour the 24/7 recorder writes ``<folder>/<YYYY-MM-DD>/<YYYY-MM-DD
HH>-00.<ext>``, this writes a JSON sidecar next to it::

    <folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.cues.json
    {
      "version": 1,
      "recording": "2026-06-05 14-00.mp3",
      "hour_start": "2026-06-05T14:00:00",
      "audio_start": "2026-06-05T14:00:00",       # creation time of the first part
      "audio_start_offset": 0.0,                   # seconds after hour_start
      "parts": [{"file": "2026-06-05 14-00.mp3", "start": "2026-06-05T14:00:00", "offset": 0.0}],
      "marks": [
        {"t": 0.0,   "kind": "track", "event": "start", "show": "...",
                     "title": "...", "artist": "..."},
        {"t": 183.4, "kind": "track", "event": "end"},
        {"t": 600.0, "kind": "show",  "event": "start", "name": "Morning Show"}
      ]
    }

``t`` is the offset in seconds from the top of the hour, so the future
catch-up player seeks straight to it.  RASTATIME 2026-09-16: the audio
file of a partial first hour (recorder started mid-hour - daily after the
04:00 restart) does not begin at the top of the hour; ``audio_start`` is
the creation time of the audio file and ``audio_start_offset`` its
distance from ``hour_start`` in seconds, so a player seeks to
``t - audio_start_offset`` inside that file.  A restart inside the hour
continues in ``<hour>-00.2.<ext>`` (the recorder never truncates an
existing hour file); ``parts`` lists every file of the hour with its
creation time and offset, refreshed at every mark, so a player picks the
part whose offset precedes ``t``.  A full hour has one part at offset 0.

Design
------

* Event-driven: the PlayoutScheduler calls :meth:`item_start` /
  :meth:`item_end` from its on-air callbacks, so the marks reflect what
  was actually recorded (the bus) — including live DJ / webstream /
  line-in take-overs that the scheduled playout history would not show.
* Show boundaries are DERIVED from a change of ``show`` between
  consecutive items, so they cover every show with content, not only
  the ones flagged for per-show recording.
* Times use the system local wall-clock (``now_fn``), matching the
  recorder's local file naming, so cue offsets line up with the audio.
* Robust: every public method swallows + logs its own errors and never
  raises into the live callback.  A no-op while the recorder is
  disabled or no folder is set.

Hour-boundary note: a track that spans the top of the hour has its
``start`` in the previous hour's sidecar and its ``end`` (t≈small) in the
new hour's — the player treats an ``end`` with no preceding ``start`` as
"continued from the previous hour".

RASTATIME 2026-10-28 - the repeated hour of the autumn clock change.  The
wall clock shows 02:xx twice; the recorder writes the second pass into
``<hour>-00.2.<ext>`` (the first file exists), and the sidecar used to
take both passes into one file with ``t`` counted from the same wall-clock
hour.  Every sidecar now carries ``hour_start_utc`` and ``utc_offset``;
when the sidecar of the wall-clock hour belongs to a different UTC hour,
the marks go to ``<hour>-00.2.cues.json`` (``.3`` ...), one sidecar per
real hour like the audio files, and ``parts`` of each sidecar lists only
the audio files created in its own hour.  A restart inside a normal hour
still adds a part to the same sidecar (same UTC hour).  ``now_fn`` may
return an aware datetime (its offset is used) or a naive local one (the
platform's offset for that instant, honouring ``fold``).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

# a part created up to this long before its hour still belongs to the hour
# (the recorder reopens on the boundary, the file system rounds)
PART_GRACE = timedelta(seconds=60)

logger = logging.getLogger(__name__)


def _clean(meta: dict) -> dict:
    """Drop None / empty-string metadata so marks stay compact."""
    return {k: v for k, v in meta.items() if v is not None and v != ""}


class CueWriter:
    """
    Writes cue marks into the current hour's sidecar.  Thread-safe (the
    scheduler fires callbacks from several ``threading.Timer`` threads).

    Parameters
    ----------
    get_config:
        Callable returning the 24/7-recording dict (shape from
        ``liquidsoap_config.read_hourly_recording_config_from_db`` — keys
        ``enabled`` / ``folder`` / ``format``).  Read per mark so a config
        change is picked up without a restart.
    now_fn:
        Injectable local-wall-clock provider (for tests).
    """

    def __init__(
        self,
        get_config: Callable[[], dict],
        *,
        now_fn: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._get_config = get_config
        self._now_fn = now_fn
        self._lock = threading.Lock()
        self._last_show: Optional[str] = None

    # -- public API (called from the scheduler) --------------------------

    def item_start(self, kind: str, *, show: Optional[str] = None, **meta) -> None:
        """
        Record the start of an on-air item (kind = track / webstream /
        linein).  Emits a derived show end/start pair first when ``show``
        differs from the previous item.
        """
        try:
            with self._lock:
                cfg = self._active_cfg()
                if cfg is None:
                    return
                now = self._now_fn()
                marks: list[dict] = []
                if show and show != self._last_show:
                    if self._last_show is not None:
                        marks.append({"kind": "show", "event": "end", "name": self._last_show})
                    marks.append({"kind": "show", "event": "start", "name": show})
                    self._last_show = show
                mark = {"kind": kind, "event": "start"}
                if show:
                    mark["show"] = show
                mark.update(_clean(meta))
                marks.append(mark)
                self._append_many(cfg, now, marks)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("CueWriter.item_start(%s) failed: %s", kind, exc)

    def item_end(self, kind: str, **meta) -> None:
        """
        Record the end of the current on-air item.  ``meta`` (RASTATIME
        2026-09-10: ``item`` = schedule row id) lets a reader pair the
        marker with its ``start`` even when markers of two items sit
        milliseconds apart.
        """
        try:
            with self._lock:
                cfg = self._active_cfg()
                if cfg is None:
                    return
                mark = {"kind": kind, "event": "end"}
                mark.update(_clean(meta))
                self._append_many(cfg, self._now_fn(), [mark])
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("CueWriter.item_end(%s) failed: %s", kind, exc)

    # -- internals -------------------------------------------------------

    def _active_cfg(self) -> Optional[dict]:
        cfg = self._get_config() or {}
        if not cfg.get("enabled") or not cfg.get("folder"):
            return None
        return cfg

    def _append_many(self, cfg: dict, now: datetime, marks: list[dict]) -> None:
        # wall clock (naive, what the recorder names files by) and the real
        # instant (aware) side by side
        aware = now if now.tzinfo is not None else now.astimezone()
        wall = aware.replace(tzinfo=None)
        hour_start = wall.replace(minute=0, second=0, microsecond=0)
        hour_start_utc = hour_start.replace(tzinfo=aware.tzinfo).astimezone(UTC)
        utc_offset = aware.utcoffset() or timedelta(0)
        offset = round((wall - hour_start).total_seconds(), 2)
        day = wall.strftime("%Y-%m-%d")
        hour = wall.strftime("%H")
        ext = str(cfg.get("format") or "mp3").lower()
        base = f"{day} {hour}-00"
        day_dir = Path(cfg["folder"]) / day

        sidecar, data, sibling_utc = self._sidecar_for(
            day_dir, base, ext, hour_start, hour_start_utc, utc_offset
        )
        self._note_audio_files(
            data,
            day_dir,
            base,
            ext,
            hour_start,
            not_before=None if data.get("sidecar_part", 1) == 1 else hour_start_utc - PART_GRACE,
            before=sibling_utc,
        )
        for mark in marks:
            entry = {"t": offset}
            entry.update(mark)
            data["marks"].append(entry)

        day_dir.mkdir(parents=True, exist_ok=True)
        tmp = day_dir / (sidecar.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, sidecar)

    def _sidecar_for(
        self,
        day_dir: Path,
        base: str,
        ext: str,
        hour_start: datetime,
        hour_start_utc: datetime,
        utc_offset: timedelta,
    ):
        """
        The sidecar of this real hour: ``<base>.cues.json`` normally;
        ``<base>.N.cues.json`` when that file belongs to another UTC hour
        (the repeated hour of the autumn clock change).  Returns the path,
        its data and - for the primary sidecar - the UTC start of a later
        sibling, so its ``parts`` stop before the sibling's files.
        """
        utc_text = hour_start_utc.isoformat(timespec="seconds")
        primary = day_dir / f"{base}.cues.json"
        data = self._load(primary, f"{base}.{ext}", hour_start, utc_text, utc_offset)
        existing_utc = data.get("hour_start_utc")
        if not existing_utc or existing_utc == utc_text:
            data.setdefault("hour_start_utc", utc_text)
            data.setdefault("utc_offset", _offset_text(utc_offset))
            sibling_utc = None
            for n in range(2, 10):
                sib = day_dir / f"{base}.{n}.cues.json"
                if not sib.exists():
                    break
                try:
                    other = json.loads(sib.read_text(encoding="utf-8")).get("hour_start_utc")
                    if other and other > utc_text:
                        sibling_utc = datetime.fromisoformat(other)
                        break
                except (OSError, ValueError, AttributeError):
                    continue
            return primary, data, sibling_utc
        # the wall-clock hour's sidecar is another real hour: use / create .N
        for n in range(2, 10):
            sib = day_dir / f"{base}.{n}.cues.json"
            if not sib.exists():
                data = self._load(sib, f"{base}.{n}.{ext}", hour_start, utc_text, utc_offset)
                data["sidecar_part"] = n
                logger.info(
                    "CueWriter: wall-clock hour %s repeats (clock change) - marks go to %s",
                    base,
                    sib.name,
                )
                return sib, data, None
            data = self._load(sib, f"{base}.{n}.{ext}", hour_start, utc_text, utc_offset)
            if data.get("hour_start_utc") == utc_text:
                data.setdefault("sidecar_part", n)
                return sib, data, None
        raise RuntimeError(f"no free sidecar name for {base}")

    @staticmethod
    def _created_utc(path: Path) -> Optional[datetime]:
        """Creation instant of an audio part (``st_birthtime`` on Windows, else ctime), aware UTC."""
        try:
            st = path.stat()
        except OSError:
            return None
        return datetime.fromtimestamp(getattr(st, "st_birthtime", st.st_ctime), tz=UTC).replace(
            microsecond=0
        )

    @classmethod
    def _note_audio_files(
        cls,
        data: dict,
        day_dir: Path,
        base: str,
        ext: str,
        hour_start: datetime,
        *,
        not_before: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> None:
        """
        RASTATIME 2026-09-16 - list the hour's audio files (``<base>.<ext>``
        and the continuation parts ``<base>.N.<ext>`` a restart inside the
        hour leaves behind) with their creation times (``st_birthtime``
        where the platform has it - Windows -, else ``st_ctime``).
        ``audio_start`` is the earliest part.  Refreshed at every mark; no
        file yet (not rotated) leaves the fields untouched.  2026-10-28:
        ``not_before`` / ``before`` (aware UTC) keep the parts of a repeated
        wall-clock hour apart - a ``.N`` sidecar takes the files created
        from its own hour on, the primary one stops before its sibling.
        """
        parts = []
        for candidate in sorted(day_dir.glob(f"{base}*.{ext}")):
            if candidate.name == f"{base}.{ext}" or candidate.name.startswith(f"{base}."):
                created_utc = cls._created_utc(candidate)
                if created_utc is None:
                    continue
                if not_before is not None and created_utc < not_before:
                    continue
                if before is not None and created_utc >= before - PART_GRACE:
                    continue
                created = created_utc.astimezone().replace(tzinfo=None)
                parts.append(
                    {
                        "file": candidate.name,
                        "start": created.isoformat(timespec="seconds"),
                        "offset": round((created - hour_start).total_seconds(), 2),
                    }
                )
        if not parts:
            return
        parts.sort(key=lambda p: (p["start"], p["file"]))
        data["audio_start"] = parts[0]["start"]
        data["audio_start_offset"] = parts[0]["offset"]
        data["parts"] = parts
        if data.get("sidecar_part", 1) != 1:
            data["recording"] = parts[0]["file"]

    def _load(
        self,
        sidecar: Path,
        audio_name: str,
        hour_start: datetime,
        hour_start_utc: str = "",
        utc_offset: Optional[timedelta] = None,
    ) -> dict:
        if sidecar.exists():
            try:
                d = json.loads(sidecar.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("marks"), list):
                    return d
            except (OSError, ValueError):
                pass  # corrupt / unreadable -> start a fresh sidecar
        data = {
            "version": 1,
            "recording": audio_name,
            "hour_start": hour_start.isoformat(),
            "marks": [],
        }
        if hour_start_utc:
            data["hour_start_utc"] = hour_start_utc
            data["utc_offset"] = _offset_text(utc_offset or timedelta(0))
        return data


def _offset_text(offset: timedelta) -> str:
    """``+02:00`` style text of a UTC offset."""
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"{sign}{total // 3600:02d}:{(total % 3600) // 60:02d}"
