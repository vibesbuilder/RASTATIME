"""
liquidsoap_telnet — thin TCP-telnet client for Liquidsoap's
built-in server interface.

RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase B (skeleton).

Liquidsoap 2.x exposes a line-protocol "telnet" server on a
configurable TCP port (default ``localhost:1234``) when the
``.liq`` script enables it via::

    settings.server.telnet.set(true)
    settings.server.telnet.bind_addr.set("127.0.0.1")
    settings.server.telnet.port.set(1234)

Commands are sent as newline-terminated lines.  Responses come
back as newline-terminated lines and end with the literal
sentinel ``END\\r\\n`` (or just ``END\\n`` depending on build).

This module provides a small ``LiquidsoapTelnetClient`` that the
:class:`LiquidsoapPlayoutEngine` uses to push commands like::

    request.queue.push file:///cache/580.mp3
    var.set scheduled.gain_db = -5.95
    metadata.update title="TOH Jingle"

PHASE-B STATE: skeleton.  Real connect / read / write logic comes
in Phase C when the engine is wired into the Pypo scheduler.
"""
from __future__ import annotations

import logging
import socket
import threading
from typing import List, Optional

logger = logging.getLogger(__name__)


class LiquidsoapTelnetClient:
    """
    Thread-safe line-protocol client for Liquidsoap's telnet server.

    Default endpoint matches the upstream Liquidsoap example
    (``localhost:1234``) but is configurable.  Reconnects on the
    next ``send_command`` after a connection drop — does NOT
    auto-reconnect in the background, since Pypo's scheduler is
    polling-driven and a missed command is usually less harmful
    than a silent reconnect storm.

    Usage::

        client = LiquidsoapTelnetClient()
        client.connect()
        resp = client.send_command("request.queue.push file:///foo.mp3")
        # resp -> "12345" (the request id, or "" if push failed)
        client.close()
    """

    # ---- Defaults ---------------------------------------------------
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 1234
    DEFAULT_TIMEOUT = 5.0  # seconds, per-command
    # Liquidsoap's response sentinel — may be "END\r\n" or "END\n"
    # depending on build; we accept both.
    END_SENTINEL = b"END"

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        # One mutex around all socket I/O so two scheduler threads
        # can't interleave commands on the same TCP stream.
        self._lock = threading.Lock()

    # ---- Connection lifecycle ---------------------------------------

    def connect(self) -> None:
        """
        Open the TCP connection to Liquidsoap's telnet server.

        Idempotent — calling on an already-open connection is a no-op.
        Raises :class:`ConnectionError` if the connect handshake fails.

        TODO Phase C — implement with proper retry/backoff suited to
        Pypo-Scheduler startup (Liquidsoap may need a few seconds
        after its own start before the telnet server is bind-ready).
        """
        with self._lock:
            if self._socket is not None:
                return
            # TODO Phase C — actual socket.create_connection(...) +
            #                 set socket timeout
            raise NotImplementedError(
                "LiquidsoapTelnetClient.connect — Phase C target"
            )

    def close(self) -> None:
        """
        Close the TCP connection cleanly (sends ``quit\\n`` first
        so Liquidsoap closes its end gracefully).

        Idempotent.

        TODO Phase C — implement.
        """
        with self._lock:
            if self._socket is None:
                return
            # TODO Phase C — try send "quit\n", then shutdown + close
            raise NotImplementedError(
                "LiquidsoapTelnetClient.close — Phase C target"
            )

    # ---- Core command path ------------------------------------------

    def send_command(self, command: str) -> str:
        """
        Send one command line to Liquidsoap, read the response up to
        the ``END`` sentinel, return the response body (stripped).

        Reconnects once on a stale-socket detection (peer closed, etc.).
        Multi-line responses are joined with newlines.

        Raises :class:`ConnectionError` if neither the initial send
        nor the post-reconnect retry succeeds.

        TODO Phase C — implement the full send/recv loop + sentinel
        parsing + single-shot reconnect on EPIPE / ECONNRESET.
        """
        # TODO Phase C — full implementation
        raise NotImplementedError(
            "LiquidsoapTelnetClient.send_command — Phase C target"
        )

    # ---- Higher-level convenience wrappers --------------------------
    #
    # These are intentionally thin — they just format the protocol
    # string and call ``send_command``.  The point is so the
    # engine code never has to memorise the exact Liquidsoap server
    # syntax.

    def request_queue_push(self, uri: str) -> str:
        """
        Push ``uri`` onto the Liquidsoap request queue.  Returns the
        Liquidsoap-assigned request id as a string (empty string on
        failure).

        TODO Phase C.
        """
        return self.send_command(f"request.queue.push {uri}")

    def request_queue_skip(self) -> str:
        """
        Skip the currently-playing item in the request queue.  Used
        by the scheduler when the operator hits "Skip" in the
        Dashboard.

        TODO Phase C.
        """
        return self.send_command("request.queue.skip")

    def metadata_update(self, fields: dict) -> str:
        """
        Push ICY metadata (track title, artist, etc.) for the current
        item.  ``fields`` is a dict of metadata key/value pairs.

        TODO Phase C — needs proper escaping per Liquidsoap server
        command syntax.
        """
        # Placeholder — real implementation will quote+escape values
        joined = ",".join(f'{k}="{v}"' for k, v in fields.items())
        return self.send_command(f"metadata.update {joined}")

    def var_set(self, name: str, value: str) -> str:
        """
        Set a Liquidsoap script-level variable (used for source
        switching: ``scheduled.enable = true|false``).

        TODO Phase C.
        """
        return self.send_command(f"var.set {name} = {value}")

    def help(self) -> List[str]:
        """
        Ask Liquidsoap for the list of registered server commands.
        Mostly useful for diagnostics.

        TODO Phase C — parse the response into a list of strings.
        """
        return [self.send_command("help")]
