"""
dj_auth — DJ login check for the Liquidsoap harbors (RASTATIME 2026-09-10).

The harbors in rastatime.liq no longer accept a static password: their
``auth`` callback POSTs every login attempt to PLAYOUT's listener
(``/dj-auth``), and PLAYOUT asks the legacy web application, whose
``check-live-stream-auth`` endpoint holds the rules the operator sees in
the UI:

* **master** — username/password from Settings → Streams → Master Source
  (``live_stream_master_username`` / ``..._password``);
* **show** — the show on air right now: either a registered host's
  LibreTime login (``live_stream_using_airtime_auth``) or the custom
  username/password of the show's "Live Stream Input" section
  (``live_stream_using_custom_auth``).  No show on air → rejected.

The endpoint answers HTTP 200 plus the header ``icecast-auth-user: 1``
when the login is accepted and 401 otherwise (it was adapted for
Icecast's URL-auth contract).  Credentials travel in the POST body of a
localhost request; they never appear in a log line.

Verdicts: ``"ok"`` / ``"denied"`` / ``"error"``.  ``"error"`` (legacy web
unreachable) makes the harbor fall back to the static password from
rastatime.conf, so a DJ can still go on air while the web application
is down.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CHECK_PATH = "/api/check-live-stream-auth/format/json"
DJTYPE_BY_SOURCE = {"master": "master", "show": "dj"}


class RejectThrottle:
    """Per-address brake for the DJ harbor (RASTATIME 2026-10-06, brute-force
    protection): after ``limit`` rejections inside ``window`` seconds the
    address is refused for ``block`` seconds without asking the web
    application.  In-memory, per playout process; a restart forgets it,
    which is fine for a brake.  Operator thresholds: 5 / 10 min / 15 min."""

    def __init__(
        self, limit: int = 5, window: float = 600.0, block: float = 900.0, clock=None
    ) -> None:
        self.limit = limit
        self.window = window
        self.block = block
        self._clock = clock or time.monotonic
        self._rejections: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}

    def blocked_for(self, address: str) -> float:
        """Seconds the address still has to wait, 0 when it may try."""
        until = self._blocked_until.get(address or "")
        if until is None:
            return 0.0
        left = until - self._clock()
        if left <= 0:
            self._blocked_until.pop(address or "", None)
            return 0.0
        return left

    def rejected(self, address: str) -> bool:
        """Records a rejection; True when this one triggered a block."""
        key = address or ""
        now = self._clock()
        stamps = [t for t in self._rejections.get(key, []) if now - t <= self.window]
        stamps.append(now)
        self._rejections[key] = stamps
        if len(stamps) >= self.limit:
            self._blocked_until[key] = now + self.block
            self._rejections[key] = []
            return True
        return False

    def accepted(self, address: str) -> None:
        self._rejections.pop(address or "", None)
        self._blocked_until.pop(address or "", None)

    def unblock(self, address: str) -> bool:
        """Operator action (System Status / rt-blocks.ps1): forget the
        address entirely.  True when something was cleared."""
        key = address or ""
        had = key in self._blocked_until or bool(self._rejections.get(key))
        self._rejections.pop(key, None)
        self._blocked_until.pop(key, None)
        return had

    def snapshot(self) -> list[dict[str, object]]:
        """Blocked addresses and addresses with recent rejections, for the
        operator's list: address, seconds left (0 = counting only),
        rejections inside the window."""
        now = self._clock()
        rows: list[dict[str, object]] = []
        for key in sorted(set(self._blocked_until) | set(self._rejections)):
            left = (
                max(0.0, self._blocked_until.get(key, 0.0) - now)
                if key in self._blocked_until
                else 0.0
            )
            if key in self._blocked_until and left <= 0:
                self._blocked_until.pop(key, None)
            recent = [t for t in self._rejections.get(key, []) if now - t <= self.window]
            if left <= 0 and not recent:
                continue
            rows.append(
                {
                    "address": key,
                    "blocked_seconds_left": int(round(left)),
                    "rejections_in_window": len(recent),
                    "limit": self.limit,
                    "window_seconds": int(self.window),
                    "block_seconds": int(self.block),
                }
            )
        return rows


class AllowList:
    """
    RASTATIME 2026-10-08 - addresses the brake leaves alone.  The web UI
    (System Status -> Allowed addresses) keeps the list in the database and
    mirrors it into ``<config dir>/allowlist.txt``, one address or CIDR
    network per line; this reader reloads the file whenever its
    modification time changes.  A missing or unreadable file is an empty
    list.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path if path is not None else self.default_path()
        self._mtime: Optional[float] = None
        self._networks: list = []

    @staticmethod
    def default_path() -> Path:
        config = os.environ.get("RASTATIME_CONFIG_FILEPATH") or "/etc/libretime/config.yml"
        return Path(config).parent / "allowlist.txt"

    def _reload_if_changed(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            self._mtime, self._networks = None, []
            return
        if mtime == self._mtime:
            return
        networks = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    networks.append(ipaddress.ip_network(line, strict=False))
                except ValueError:
                    logger.warning(
                        "dj-auth: allow list entry %r is not an address or network - ignored", line
                    )
        except OSError as exc:
            logger.warning("dj-auth: cannot read the allow list %s: %s", self.path, exc)
            networks = []
        self._mtime, self._networks = mtime, networks

    def allows(self, address: str) -> bool:
        if not address:
            return False
        self._reload_if_changed()
        if not self._networks:
            return False
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        return any(ip in net for net in self._networks)


class DjAuthenticator:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 2.5,
        session: Optional[requests.Session] = None,
        throttle: Optional[RejectThrottle] = None,
        allow_list: Optional[AllowList] = None,
    ) -> None:
        self._base = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()
        self._throttle = throttle or RejectThrottle()
        self._allow_list = allow_list or AllowList()

    @property
    def check_url(self) -> str:
        return f"{self._base}{CHECK_PATH}"

    def check(self, source: str, user: str, password: str, address: str = "") -> str:
        djtype = DJTYPE_BY_SOURCE.get((source or "").lower())
        who = f"{source} login {user!r} from {address or '?'}"
        if djtype is None:
            logger.warning("dj-auth: unknown source %r - rejected", source)
            return "denied"
        if not self._base:
            logger.warning("dj-auth: no web base URL configured - %s cannot be checked", who)
            return "error"
        if not user or not password:
            logger.info("dj-auth: %s rejected (empty user or password)", who)
            return "denied"
        # RASTATIME 2026-10-08 - an allowed address is never braked nor counted
        allowed = self._allow_list.allows(address)
        left = 0.0 if allowed else self._throttle.blocked_for(address)
        if left > 0:
            logger.warning(
                "dj-auth: %s refused - address blocked for another %.0f s (brute-force brake)",
                who,
                left,
            )
            return "denied"
        try:
            resp = self._session.post(
                self.check_url,
                data={"djtype": djtype, "username": user, "password": password},
                timeout=self._timeout,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "dj-auth: web application unreachable at %s (%s) - %s falls back "
                "to the static harbor password",
                self.check_url,
                exc,
                who,
            )
            return "error"
        accepted = resp.status_code == 200 and resp.headers.get("icecast-auth-user") == "1"
        if accepted:
            logger.info("dj-auth: %s accepted", who)
            self._throttle.accepted(address)
            return "ok"
        if resp.status_code not in (200, 401):
            logger.warning(
                "dj-auth: unexpected HTTP %s from %s - %s falls back to the static harbor password",
                resp.status_code,
                self.check_url,
                who,
            )
            return "error"
        # RASTATIME 2026-10-06 - the legacy check names the reason; only a
        # wrong password counts towards the brake.  "no-show" (nothing on
        # air) and "not-host" (name is not a host of the running show) are
        # refusals without a password check - a DJ dialling in too early
        # must never end up blocked.  No header (older legacy) counts.
        reason = (resp.headers.get("x-rastatime-auth-reason") or "bad-password").strip().lower()
        if reason != "bad-password":
            logger.info("dj-auth: %s rejected (%s, not counted)", who, reason)
            return "denied"
        if allowed:
            logger.info("dj-auth: %s rejected (bad password; allowed address, not counted)", who)
        elif self._throttle.rejected(address):
            logger.warning(
                "dj-auth: %s rejected (bad password) - address blocked for "
                "%.0f min after %d rejections (brute-force brake)",
                who,
                self._throttle.block / 60,
                self._throttle.limit,
            )
        else:
            logger.info("dj-auth: %s rejected (bad password)", who)
        return "denied"

    @property
    def throttle(self) -> RejectThrottle:
        return self._throttle
