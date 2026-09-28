"""
RASTATIME 2026-09-28 - TuneIn "now playing" pushes from the playout.

Settings -> TuneIn Settings (cc_pref ``tunein_enabled``, ``tunein_station_id``,
``tunein_partner_id``, ``tunein_partner_key``) used to be consumed by the
legacy notify endpoint (file starts only) plus a keep-alive from the old
Pypo fetcher that no longer runs, so TuneIn dropped the display after
five minutes on long tracks and never saw webstreams or line-ins.  The
playout now owns the push:

  * :meth:`TuneInPusher.now_playing` at every start of a track, webstream
    or line-in (title + artist, or the show name for live inputs),
  * :meth:`TuneInPusher.keepalive` from the schedule refresh: the last
    payload is sent again when the previous push is older than
    KEEPALIVE_SECONDS (TuneIn forgets a station that stays quiet for
    five minutes),
  * the settings are re-read from cc_pref before every push, so a save
    in the UI takes effect at the next track without a restart.

HTTP runs on a daemon thread and never blocks a playout callback; the
partner key is never logged.
"""
from __future__ import annotations

import logging
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

TUNEIN_API_URL = "https://air.radiotime.com/Playing.ashx"
# TuneIn removes the "now playing" display after 5 minutes without an update.
KEEPALIVE_SECONDS = 240.0
REQUEST_TIMEOUT_SECONDS = 10.0


@dataclass
class TuneInConfig:
    enabled: bool
    station_id: str
    partner_id: str
    partner_key: str

    def complete(self) -> bool:
        return bool(
            self.enabled and self.station_id and self.partner_id and self.partner_key
        )


def read_tunein_config_from_db() -> Optional[TuneInConfig]:
    """cc_pref via the Django ORM (same path as the ICY preferences); None on error."""
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]

        prefs = dict(Preference.site.values_list("key", "value"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("TuneIn settings could not be read: %s", exc)
        return None
    enabled = str(prefs.get("tunein_enabled") or "").strip().lower() in ("1", "true", "on", "yes")
    return TuneInConfig(
        enabled=enabled,
        station_id=str(prefs.get("tunein_station_id") or "").strip(),
        partner_id=str(prefs.get("tunein_partner_id") or "").strip(),
        partner_key=str(prefs.get("tunein_partner_key") or "").strip(),
    )


class TuneInPusher:
    """Now-playing pushes to the TuneIn AIR API (see module docstring)."""

    def __init__(
        self,
        read_config: Callable[[], Optional[TuneInConfig]],
        session: Optional[requests.Session] = None,
        clock: Callable[[], float] = time.monotonic,
        api_url: str = TUNEIN_API_URL,
    ) -> None:
        self._read_config = read_config
        self._session = session or requests.Session()
        self._clock = clock
        self._api_url = api_url
        self._lock = threading.Lock()
        self._last_payload: Optional[Tuple[str, str]] = None
        self._last_push_at: Optional[float] = None
        self._last_ok: Optional[bool] = None
        self._disabled_logged = False

    # ------------------------------------------------------------------
    # public API (called from playout callbacks - never blocks)
    # ------------------------------------------------------------------

    def now_playing(self, title: Optional[str], artist: Optional[str], *, kind: str = "track") -> None:
        """A new item is on air: remember it and push it on a daemon thread."""
        payload = (self._clean(title) or "n/a", self._clean(artist))
        with self._lock:
            self._last_payload = payload
        self._push_async(payload, reason=kind)

    def keepalive(self) -> None:
        """Re-send the last payload when the previous push is older than KEEPALIVE_SECONDS."""
        with self._lock:
            payload = self._last_payload
            last = self._last_push_at
        if payload is None:
            return
        if last is not None and self._clock() - last < KEEPALIVE_SECONDS:
            return
        self._push_async(payload, reason="keepalive")

    @property
    def last_ok(self) -> Optional[bool]:
        return self._last_ok

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(value: Optional[str]) -> str:
        return " ".join(str(value or "").split())[:255]

    def _push_async(self, payload: Tuple[str, str], *, reason: str) -> None:
        t = threading.Thread(
            target=self.push, args=(payload[0], payload[1]), kwargs={"reason": reason},
            name="tunein-push", daemon=True,
        )
        t.start()

    def push(self, title: str, artist: str, *, reason: str = "track") -> bool:
        """
        Synchronous push.  Returns True on a TuneIn ``<status>200</status>``
        answer.  Disabled or incomplete settings are a silent no-op (logged
        once); network errors and rejections are logged without the key.
        """
        with self._lock:
            self._last_payload = (title or "n/a", artist or "")
        cfg = self._read_config()
        if cfg is None or not cfg.enabled:
            self._disabled_logged = False
            return False
        if not cfg.complete():
            if not self._disabled_logged:
                logger.warning(
                    "TuneIn push enabled but Station ID / Partner ID / Partner Key "
                    "are incomplete - nothing is sent (Settings -> TuneIn)."
                )
                self._disabled_logged = True
            return False
        self._disabled_logged = False
        params = {
            "partnerId": cfg.partner_id,
            "partnerKey": cfg.partner_key,
            "id": cfg.station_id,
            "title": title or "n/a",
            "artist": artist or "",
            "commercial": "false",
        }
        now = self._clock()
        try:
            response = self._session.get(self._api_url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            ok = self._answer_ok(response.status_code, response.text)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("TuneIn push (%s) failed: %s", reason, exc)
            ok = False
        with self._lock:
            # also on failure: no hammering, the next keepalive retries after KEEPALIVE_SECONDS
            self._last_push_at = now
            self._last_ok = ok
        if ok:
            logger.info("TuneIn now playing (%s): %r - %r", reason, artist, title)
        return ok

    @staticmethod
    def _answer_ok(status_code: int, body: str) -> bool:
        if status_code != 200:
            logger.warning("TuneIn answered HTTP %s: %s", status_code, (body or "")[:200])
            return False
        try:
            root = ET.fromstring(body or "")
            status = (root.findtext("./head/status") or "").strip()
            fault = (root.findtext("./head/fault") or "").strip()
        except ET.ParseError:
            logger.warning("TuneIn answered with something that is not XML: %s", (body or "")[:200])
            return False
        if status == "200":
            return True
        logger.warning("TuneIn rejected the update: status %s %s", status or "?", fault)
        return False
