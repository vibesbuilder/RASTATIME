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
libretime.conf, so a DJ can still go on air while the web application
is down.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CHECK_PATH = "/api/check-live-stream-auth/format/json"
DJTYPE_BY_SOURCE = {"master": "master", "show": "dj"}


class DjAuthenticator:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 2.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._base = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()

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
        try:
            resp = self._session.post(
                self.check_url,
                data={"djtype": djtype, "username": user, "password": password},
                timeout=self._timeout,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "dj-auth: web application unreachable at %s (%s) - %s falls back "
                "to the static harbor password", self.check_url, exc, who,
            )
            return "error"
        accepted = resp.status_code == 200 and resp.headers.get("icecast-auth-user") == "1"
        if accepted:
            logger.info("dj-auth: %s accepted", who)
            return "ok"
        if resp.status_code not in (200, 401):
            logger.warning(
                "dj-auth: unexpected HTTP %s from %s - %s falls back to the static "
                "harbor password", resp.status_code, self.check_url, who,
            )
            return "error"
        logger.info("dj-auth: %s rejected", who)
        return "denied"
