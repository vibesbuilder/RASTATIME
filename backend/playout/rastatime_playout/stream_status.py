"""
RASTATIME 2026-11-02 - output.icecast connection state -> Settings -> Streams.

The rendered ``rastatime.liq`` binds every ``output.icecast`` to
``rt_stream_N`` and registers ``on_connect`` / ``on_error`` callbacks
that POST to PLAYOUT's listener::

    /stream-event?stream=N&status=ok|error&message=<text>

PLAYOUT forwards the message to the legacy web application
(``/api/update-liquidsoap-status``, the LibreTime endpoint that pypo once
used), which stores it as ``cc_pref`` ``stream_liquidsoap_status:N`` and
shows it in the status box of stream N instead of the generic "Icecast
is running. Start RASTATIME-PLAYOUT ..." text.

Why (fresh-machine rehearsal 2026-11-02): an enabled stream with an empty
mount and password made Liquidsoap retry ``Connection failed: 401,
Authentication Required`` every 3 s for half an hour while the page
looked healthy; only ``liquidsoap-stdout.log`` knew.

The forward runs on a daemon thread and is deduplicated per stream: the
error callback fires every retry (3 s), the web application needs the
text once per change.  ``boot_time`` is sent empty so the legacy guard
("ignore reports of an instance older than the last save") never hides
a message - the operator's save clears the stored statuses itself.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Optional

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_ERROR = "error"
#: What the web application stores for a connected output (LibreTime
#: convention: ``OK`` means "no error to show").
OK_MESSAGE = "OK"
MAX_MESSAGE_CHARS = 300


class StreamStatusReporter:
    """
    Forward Liquidsoap output states to the legacy web application.

    ``client`` is the v1 legacy API client (``update_liquidsoap_status``);
    ``post`` may replace it in tests.  Never raises.
    """

    def __init__(
        self,
        client: Optional[object] = None,
        *,
        post: Optional[Callable[[str, str, Optional[str]], object]] = None,
        threaded: bool = True,
        on_reconnect: Optional[Callable[[int], object]] = None,
    ) -> None:
        if post is None and client is not None:
            post = client.update_liquidsoap_status
        self._post = post
        self._threaded = threaded
        # RASTATIME 2026-11-02 - an output that (re)connects is the earliest
        # sign of a fresh Liquidsoap instance: the scheduler refreshes at
        # once instead of noticing the restart at its next 120-s poll
        # (studio probe 12:10: 68 s of silence between the restart and the
        # re-armed webstream).
        self._on_reconnect = on_reconnect
        self._lock = threading.Lock()
        self._last: dict[int, str] = {}

    def report(self, stream: int, status: str, message: str) -> bool:
        """
        Record ``status``/``message`` for output ``stream`` (1-based).
        Returns True when the state changed and a forward was started,
        False for a repeat or an unusable request.
        """
        try:
            n = int(stream)
        except (TypeError, ValueError):
            logger.debug("stream-event: bad stream number %r", stream)
            return False
        if n < 1 or n > 9:
            logger.debug("stream-event: stream %d out of range", n)
            return False
        status = (status or "").strip().lower()
        if status not in (STATUS_OK, STATUS_ERROR):
            logger.debug("stream-event: bad status %r", status)
            return False
        text = " ".join((message or "").split())[:MAX_MESSAGE_CHARS]
        stored = OK_MESSAGE if status == STATUS_OK else (text or "Liquidsoap reported an error")
        with self._lock:
            if self._last.get(n) == stored:
                return False
            self._last[n] = stored
        if status == STATUS_OK:
            logger.info("Stream %d: Liquidsoap connected to Icecast.", n)
            if self._on_reconnect is not None:
                try:
                    self._on_reconnect(n)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug("stream-event: reconnect hook raised: %s", exc)
        else:
            logger.warning("Stream %d: Liquidsoap output error: %s", n, stored)
        if self._post is None:
            logger.debug("stream-event: no web application client - not forwarded")
            return True
        if self._threaded:
            threading.Thread(
                target=self._forward,
                args=(n, stored),
                name=f"stream-status-{n}",
                daemon=True,
            ).start()
        else:
            self._forward(n, stored)
        return True

    def _forward(self, n: int, stored: str) -> None:
        try:
            # stream_id "sN" is what the legacy action trims to N.
            self._post(stored, f"s{n}", None)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Stream %d: could not forward the Liquidsoap status to the web application: %s",
                n,
                exc,
            )

    def last(self, stream: int) -> Optional[str]:
        """The last message stored for ``stream`` (tests, /source-state)."""
        with self._lock:
            return self._last.get(int(stream))
