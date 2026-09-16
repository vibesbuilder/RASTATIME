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
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _clean(meta: Dict) -> Dict:
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
        get_config: Callable[[], Dict],
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
                marks: List[Dict] = []
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

    def _active_cfg(self) -> Optional[Dict]:
        cfg = self._get_config() or {}
        if not cfg.get("enabled") or not cfg.get("folder"):
            return None
        return cfg

    def _append_many(self, cfg: Dict, now: datetime, marks: List[Dict]) -> None:
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        offset = round((now - hour_start).total_seconds(), 2)
        day = now.strftime("%Y-%m-%d")
        hour = now.strftime("%H")
        ext = str(cfg.get("format") or "mp3").lower()
        base = f"{day} {hour}-00"
        day_dir = Path(cfg["folder"]) / day
        sidecar = day_dir / f"{base}.cues.json"

        data = self._load(sidecar, f"{base}.{ext}", hour_start)
        self._note_audio_files(data, day_dir, base, ext, hour_start)
        for mark in marks:
            entry = {"t": offset}
            entry.update(mark)
            data["marks"].append(entry)

        day_dir.mkdir(parents=True, exist_ok=True)
        tmp = day_dir / f"{base}.cues.json.tmp"
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(tmp, sidecar)

    @staticmethod
    def _note_audio_files(data: Dict, day_dir: Path, base: str, ext: str, hour_start: datetime) -> None:
        """
        RASTATIME 2026-09-16 - list the hour's audio files (``<base>.<ext>``
        and the continuation parts ``<base>.N.<ext>`` a restart inside the
        hour leaves behind) with their creation times (``st_birthtime``
        where the platform has it - Windows -, else ``st_ctime``).
        ``audio_start`` is the earliest part.  Refreshed at every mark; no
        file yet (not rotated) leaves the fields untouched.
        """
        parts = []
        for candidate in sorted(day_dir.glob(f"{base}*.{ext}")):
            if candidate.name == f"{base}.{ext}" or candidate.name.startswith(f"{base}."):
                try:
                    st = candidate.stat()
                except OSError:
                    continue
                created = datetime.fromtimestamp(getattr(st, "st_birthtime", st.st_ctime)).replace(microsecond=0)
                parts.append({
                    "file": candidate.name,
                    "start": created.isoformat(timespec="seconds"),
                    "offset": round((created - hour_start).total_seconds(), 2),
                })
        if not parts:
            return
        parts.sort(key=lambda p: (p["start"], p["file"]))
        data["audio_start"] = parts[0]["start"]
        data["audio_start_offset"] = parts[0]["offset"]
        data["parts"] = parts

    def _load(self, sidecar: Path, audio_name: str, hour_start: datetime) -> Dict:
        if sidecar.exists():
            try:
                d = json.loads(sidecar.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("marks"), list):
                    return d
            except (OSError, ValueError):
                pass  # corrupt / unreadable -> start a fresh sidecar
        return {
            "version": 1,
            "recording": audio_name,
            "hour_start": hour_start.isoformat(),
            "marks": [],
        }
