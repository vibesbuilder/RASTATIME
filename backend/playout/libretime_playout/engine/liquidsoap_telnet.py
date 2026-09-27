"""
liquidsoap_telnet — TCP-telnet client for Liquidsoap's built-in
server interface.

RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase C1 (full
implementation, replaces the Phase-B skeleton from commit eccc003).

Liquidsoap 2.x exposes a line-protocol "telnet" server on a
configurable TCP port (default ``localhost:1234``) when the
``.liq`` script enables it via::

    settings.server.telnet.set(true)
    settings.server.telnet.bind_addr.set("127.0.0.1")
    settings.server.telnet.port.set(1234)

Protocol summary
----------------

* Each command is one newline-terminated line.
* Each response is one or more lines, terminated by the literal
  sentinel ``END\\n`` (or ``END\\r\\n`` on some Windows builds) on
  its own line.
* The special command ``quit`` makes the server close the
  connection immediately, without an ``END`` sentinel.
* Encoding is UTF-8.

This module provides :class:`LiquidsoapTelnetClient`, which the
:class:`LiquidsoapPlayoutEngine` uses to push commands like::

    request.queue.push file:///cache/580.mp3
    var.set scheduled.gain_db = -5.95
    metadata.update title="TOH Jingle"

Thread-safety
-------------

All public methods serialise on a single mutex.  The Pypo
scheduler is single-threaded for the audio hot-path but several
helper threads (notify, recorder, source-switcher) may want to
push commands concurrently — the lock guarantees no two requests
interleave their bytes on the wire.

Reconnect strategy
------------------

:meth:`send_command` retries exactly once on a broken-socket
error (``OSError`` / ``ConnectionError``).  If the second attempt
also fails the exception propagates to the caller — the
scheduler can decide whether the failure is fatal or just a
diagnostic warning.  We do NOT do background auto-reconnect:
silent reconnects on a polling-driven scheduler can mask real
problems (e.g. Liquidsoap subprocess died).
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

    Usage::

        client = LiquidsoapTelnetClient()
        # connect is lazy — first send_command opens the socket
        resp = client.send_command("request.queue.push file:///foo.mp3")
        # resp -> "12345" (the request id, or "" if push failed)
        client.close()
    """

    # ---- Defaults ---------------------------------------------------
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 1234
    DEFAULT_TIMEOUT = 5.0
    # Name of the request.queue source as declared in the .liq script
    # (the ``id=`` parameter of ``request.queue(id=...)``).  Liquidsoap
    # 2.4 exposes a request.queue with id="X" as the server commands
    # ``X.push``, ``X.skip``, ``X.queue``, ``X.flush_and_skip`` — NOT
    # the legacy ``request.queue.push`` style of older builds.  Our
    # rastatime.liq names the queue ``scheduled`` (see the
    # ``scheduled_q = request.queue(id="scheduled")`` line in the
    # template).  If the operator renames it, override here or via the
    # ``queue_id=`` constructor argument.
    DEFAULT_QUEUE_ID = "scheduled"  # seconds, per-command

    # Liquidsoap's response sentinel.  Always on its own line.
    # We accept both line-endings because Windows-built Liquidsoap
    # may emit \r\n while Linux builds emit \n.
    _END_VARIANTS = (b"\nEND\r\n", b"\nEND\n")
    # Special case: empty response — server sends just "END\n" with
    # no preceding body.
    _END_ONLY_VARIANTS = (b"END\r\n", b"END\n")

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        queue_id: str = DEFAULT_QUEUE_ID,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._queue_id = queue_id
        self._socket: Optional[socket.socket] = None
        # Mutex around all socket I/O so two threads can't interleave
        # commands on the same TCP stream.
        self._lock = threading.Lock()
        # Receive buffer carried across calls — recv() may return
        # bytes from the next response if the server pipelines.
        # (Defensive — Liquidsoap normally responds one-at-a-time,
        # but we don't want to assume.)
        self._recv_buf: bytes = b""

    # ---- Public lifecycle -------------------------------------------

    def connect(self) -> None:
        """
        Open the TCP connection to Liquidsoap's telnet server.

        Idempotent — calling on an already-open connection is a no-op.
        Raises :class:`ConnectionError` if the connect handshake fails.
        """
        with self._lock:
            if self._socket is not None:
                return
            self._connect_locked()

    def close(self) -> None:
        """
        Close the TCP connection cleanly.

        Sends ``quit`` first so Liquidsoap closes its end gracefully,
        then shuts down the socket.  Idempotent.
        """
        with self._lock:
            self._close_locked(send_quit=True)

    # ---- Core command path ------------------------------------------

    def send_command(self, command: str) -> str:
        """
        Send one command line to Liquidsoap, read the response up to
        the ``END`` sentinel, return the response body (stripped of
        outer whitespace).

        Reconnects once on a stale-socket detection (peer closed,
        EPIPE, ECONNRESET).  Raises :class:`ConnectionError` if both
        attempts fail.

        Multi-line responses are joined with newlines.  The trailing
        ``END`` line itself is not included.
        """
        # Normalise: every command must end with a newline.
        if not command.endswith("\n"):
            command_to_send = command + "\n"
        else:
            command_to_send = command
        cmd_bytes = command_to_send.encode("utf-8")

        with self._lock:
            # Attempt 1
            try:
                if self._socket is None:
                    self._connect_locked()
                self._socket.sendall(cmd_bytes)
                return self._read_until_end_locked()
            except (OSError, ConnectionError) as exc:
                logger.debug(
                    "Telnet attempt 1 for %r failed (%s); reconnecting + retrying",
                    command.strip(), exc,
                )
                self._close_locked(send_quit=False)

            # Attempt 2 — fresh connection
            try:
                self._connect_locked()
                self._socket.sendall(cmd_bytes)
                return self._read_until_end_locked()
            except (OSError, ConnectionError) as exc:
                self._close_locked(send_quit=False)
                raise ConnectionError(
                    f"Telnet command {command.strip()!r} failed after reconnect: {exc}"
                ) from exc

    # ---- Higher-level convenience wrappers --------------------------

    def request_queue_push(self, uri: str) -> str:
        """
        Push ``uri`` onto the Liquidsoap request queue (the source
        declared as ``request.queue(id=self._queue_id)`` in
        rastatime.liq).  Returns the Liquidsoap-assigned request id
        as a string (or the raw response if it doesn't look like an
        id — caller decides).

        Use the ``annotate:`` and ``file:`` URI protocols to attach
        metadata, e.g.::

            client.request_queue_push(
                'annotate:replaygain_track_gain="-5.95 dB",cue_in="0.0":'
                'file:///C:/rastatime/scheduler/580.mp3'
            )

        Wire form on Liquidsoap 2.4: ``<queue_id>.push <uri>``
        (e.g. ``scheduled.push file:///...``).
        """
        return self.send_command(f"{self._queue_id}.push {uri}")

    def request_queue_skip(self) -> str:
        """
        Skip the currently-playing item in the request queue.

        Wire form on Liquidsoap 2.4: ``<queue_id>.skip``.
        """
        return self.send_command(f"{self._queue_id}.skip")

    def request_queue_remaining(self) -> str:
        """
        RASTATIME 2026-09-27 - seconds of audio left in the playing
        request (``<queue_id>.remaining``, a float; ``-1`` = unknown).
        """
        return self.send_command(f"{self._queue_id}.remaining")

    def request_queue_flush(self) -> str:
        """
        Drop every PENDING request from the queue; the item currently
        playing is untouched.

        RASTATIME 2026-09-04 - ``skip`` only ends the item being played.
        While the scheduled branch is not the one on air (a line-in or
        webstream is), nothing is being played from the queue, so
        ``skip`` is a no-op and every push piles up behind the last one.
        Live 2026-09-04 11:00-11:08: four jingles pushed under a masking
        line-in came out back-to-back seven minutes later, the moment
        the line-in dropped.  ``flush`` is registered in rastatime.liq
        (``scheduled_q.set_queue([])``); wire form ``<queue_id>.flush``.
        """
        return self.send_command(f"{self._queue_id}.flush")

    def metadata_update(self, fields: dict) -> str:
        """
        Push ICY metadata for the current item.

        ``fields`` is a dict of metadata key/value pairs.  Values
        are wrapped in double quotes; embedded quotes inside values
        are escaped with a backslash.

        Note: which command exactly takes the metadata depends on
        the .liq pipeline shape.  This wrapper sends the generic
        ``metadata.update`` — Phase-C will switch to the source-
        specific command (``source-id.insert`` or similar) once
        the .liq pipeline names its sources.
        """
        encoded = ",".join(
            f'{key}="{self._escape_value(str(value))}"'
            for key, value in fields.items()
        )
        return self.send_command(f"metadata.update {encoded}")

    def var_set(self, name: str, value: str) -> str:
        """
        Set a Liquidsoap script-level variable.

        Used for source switching (e.g.
        ``var.set master_dj_active = true``) and per-track
        configuration the .liq script reads at switch time.
        """
        return self.send_command(f"var.set {name} = {value}")

    def help(self) -> List[str]:
        """
        Ask Liquidsoap for the list of registered server commands.
        Returns each command line as a separate string.  Mostly
        useful for diagnostics / asserting the .liq script
        configured the expected commands.
        """
        resp = self.send_command("help")
        return [line for line in resp.splitlines() if line.strip()]

    # ---- Phase C5 — recording lifecycle wrappers -------------------------

    # The rastatime.liq template renders an ``output.file(id="recording",
    # …)`` block whose filename comes from a Liquidsoap var ``recording_path``.
    # These wrappers give Pypo's _on_show_record_start / _end a clean
    # API instead of raw send_command() calls.

    def recording_set_path(self, path: str) -> str:
        """
        Set the absolute output file path for the next recording reopen.

        Wire-form: ``var.set recording_path = <path>`` — **without**
        surrounding quotes.  Liquidsoap's telnet ``var.set`` parser
        eats the rest of the line as a raw string and does NOT strip
        surrounding quotes; the C5 reality-test 2026-05-27 hit a
        ``mkdir("\\"C")`` crash because we previously wrapped the
        value in ``"..."`` which then landed literally in the
        recording_path variable.

        The .liq side's ``reopen_when=recording_should_reopen``
        callback detects the path change and triggers Liquidsoap to
        reopen the output.file with the new path on the next bus
        frame — no explicit ``recording.start`` needed for the
        path-change-driven flow (though :meth:`recording_start` is
        still useful for explicit on/off control).

        Path constraints (Liquidsoap-telnet wire-form limits):
          * MUST NOT contain ``\\n`` (newline terminates the command)
          * MUST NOT contain ``"`` or ``\\``  — risks parser confusion
          * Forward slashes only (Windows acceptable, mkdir handles it)
          * Drive letter form ``C:/...`` is fine; ``C:\\...`` not
            recommended because backslash is ambiguous

        Example::

            client.recording_set_path(
                "C:/rastatime/recordings/2026-05-27/2026-05-27 18-00 - Show.mp3"
            )
        """
        # Quick sanity guard — these characters break the wire form
        # silently and produce mkdir-on-junk-path crashes.
        if any(ch in path for ch in ('\n', '\r', '"', '\\')):
            raise ValueError(
                f"recording_set_path: path contains a character that "
                f"would break the Liquidsoap telnet wire form: {path!r}"
            )
        return self.send_command(f"var.set recording_path = {path}")

    def recording_start(self) -> str:
        """
        Start the ``output.file(id="recording", …)`` block — Liquidsoap
        opens the file at the previously-set ``recording_path`` and
        begins writing the current bus content.

        Pre-condition: :meth:`recording_set_path` must have been
        called with a writable, full path.  A start without a path
        set lands the recording at the sentinel
        ``C:/rastatime/recordings/_uninitialized.mp3`` (see the
        template's ``var.get(default=…, "recording_path")`` fallback) —
        loud but recoverable.
        """
        return self.send_command("recording.start")

    def recording_stop(self) -> str:
        """
        Stop the recording — Liquidsoap closes the .mp3 file cleanly.
        Idempotent: calling on an already-stopped recording is harmless
        (Liquidsoap replies "Done" or similar).
        """
        return self.send_command("recording.stop")

    def recording_status(self) -> str:
        """
        Query recording state.  Returns Liquidsoap's free-text status
        line (e.g. ``"on"`` / ``"off"`` depending on version).  Mostly
        useful for diagnostics.
        """
        return self.send_command("recording.status")

    # ---- Phase E — webstream lifecycle wrappers ---------------------

    # The rastatime.liq template renders an ``input.http(id="webstream",
    # start=false, ...)`` source initialised with an empty URL.  Pypo's
    # _on_webstream_start drives the runtime cycle:
    #
    #   webstream_set_url <url>
    #   webstream_set_gain <linear_factor>    (optional, defaults 1.0)
    #   webstream_start
    #     ... show plays ...
    #   webstream_stop
    #
    # Liquidsoap 2.4.4's input.http exposes set_url / start / stop /
    # status / url methods as server-commands via the source-id namespace
    # (here "webstream"), so we hit them directly through telnet.

    def webstream_set_url(self, url: str) -> str:
        """
        Set the HTTP URL the input.http source will connect to on the
        next ``webstream_start``.

        Wire-form: ``webstream.url <url>`` — the input.http source
        exposes its OCaml ``set_url`` method as the server-command
        ``url`` (with optional argument: no arg = get, with arg = set).
        Phase E reality-test 2026-05-29 caught this: the obvious
        ``webstream.set_url <url>`` wire-form was a guess and got
        silently rejected as "unknown command" by Liquidsoap.  Verified
        via the live ``help`` output, which lists ``webstream.url [url]``.

        URL constraints (Liquidsoap-telnet wire-form limits):
          * MUST NOT contain ``\\n`` / ``\\r`` (newline terminates the command)
          * MUST NOT contain ``"`` (would confuse Liquidsoap's parser)
          * No length constraint enforced here, but practical limit is
            a few KB — typical webstream URLs are well under 200 chars.

        Example::

            client.webstream_set_url(
                "http://stream.live.vc.bbcmedia.co.uk/world_service_b2b_04"
            )
        """
        if any(ch in url for ch in ('\n', '\r', '"')):
            raise ValueError(
                f"webstream_set_url: url contains a character that "
                f"would break the Liquidsoap telnet wire form: {url!r}"
            )
        return self.send_command(f"webstream.url {url}")

    def webstream_set_gain(self, linear_factor: float) -> str:
        """
        Set the linear amplify factor for the webstream source.  Pypo
        converts cc_webstream.input_gain_db to linear before calling::

            linear_factor = 10 ** (gain_db / 20.0)
            # e.g. +3 dB → 1.412, -6 dB → 0.501, 0 dB → 1.0

        Wire-form: ``var.set webstream.gain = <factor>`` —
        ``interactive.float("webstream.gain", 1.0)`` in the .liq template
        registers as a script-level variable, NOT as a source-method-
        derived command.  Phase E reality-test 2026-05-29 caught this:
        the obvious ``webstream.gain.set <factor>`` wire-form was a
        guess and got silently rejected.  Verified via the live ``help``
        output, which lists only ``var.set <name> = <value>`` as the
        interactive-variable setter (no ``<name>.set`` shortcut).

        1.0 = unity (no gain change), default if never set.
        """
        return self.send_command(f"var.set webstream.gain = {linear_factor}")

    def webstream_start(self) -> str:
        """
        Tell the input.http source to begin connecting + buffering.
        Pre-condition: :meth:`webstream_set_url` must have been called
        with a valid URL (otherwise Liquidsoap tries to connect to the
        empty default URL and immediately fails).

        Wire-form: ``webstream.start``.  Returns Liquidsoap's free-text
        ack ("Done" or similar).  The source goes ``source.is_ready=true``
        only after ``max_buffer`` seconds of audio have been pre-fetched
        — the switch operator in the .liq script then flips the bus
        to webstream automatically.
        """
        return self.send_command("webstream.start")

    def webstream_stop(self) -> str:
        """
        Close the HTTP connection.  ``source.is_ready`` goes false, the
        switch operator falls through to scheduled.  Idempotent — a stop
        on an already-stopped source replies "Done" and produces no
        error (same convention as :meth:`recording_stop`).

        Wire-form: ``webstream.stop``.
        """
        return self.send_command("webstream.stop")

    def webstream_status(self) -> str:
        """
        Return Liquidsoap's free-text input.http status, one of:
          * ``"stopped"`` — source idle (after webstream.stop or boot)
          * ``"starting"`` — polling task is about to begin
          * ``"polling"`` — attempting to connect to the HTTP stream
          * ``"connected <url>"`` — connected, buffering or playing
          * ``"stopping"`` — source is shutting down

        Mostly for diagnostics — Pypo doesn't gate on this because the
        start/stop wrappers are themselves idempotent.

        Wire-form: ``webstream.status``.
        """
        return self.send_command("webstream.status")

    def uptime(self) -> str:
        """
        Return Liquidsoap's process uptime, free-text
        ``"0d 00h 03m 25s"``.  RASTATIME 2026-09-07: the scheduler polls
        it to notice that LIQUIDSOAP was restarted out from under a
        running PLAYOUT (manual restart order) and re-apply the initial
        state (recording sentinel stop + gates).

        Wire-form: ``uptime``.
        """
        return self.send_command("uptime")

    def webstream_ready(self) -> str:
        """
        Return ``"true"``/``"false"`` — whether the webstream source is
        producing audio right now (``source.is_ready(webstream)``, the
        same predicate the bus switch gates on).  Registered by the
        rastatime.liq template as ``webstream.ready``.  The in-process
        watchdog uses the same predicate; this command is a diagnostic
        (the scheduler's poll was removed on 2026-09-15).

        Wire-form: ``webstream.ready``.
        """
        return self.send_command("webstream.ready")

    def webstream_watchdog(self) -> str:
        """
        Counters of the in-process webstream watchdog (RASTATIME
        2026-09-07): ``checks=N reconnects=N started=… ready=…
        seen_ready=… starved=N``.  Registered by rastatime.liq as
        ``webstream.watchdog``; a render without the block answers
        ``ERROR: unknown command``.

        Wire-form: ``webstream.watchdog``.
        """
        return self.send_command("webstream.watchdog")

    def webstream_url(self) -> str:
        """
        Return the URL currently set on the input.http source (empty
        string if never set).  Diagnostics-only — Pypo tracks its own
        copy of the URL in playout_scheduler state.

        Wire-form: ``webstream.url``.
        """
        return self.send_command("webstream.url")

    # ---- Phase F — line-input lifecycle wrappers --------------------

    # The rastatime.liq template renders an
    # ``input.http(id="linein", start=false, ...)`` source initialised
    # with the FfmpegLineinCapture local Icecast mount URL (default
    # ``http://localhost:8000/linein-capture``).  Pypo's
    # _on_linein_start drives the runtime cycle in Liquidsoap-mode:
    #
    #   self._linein_capture.start(device_id)   # spawns ffmpeg dshow
    #   linein_start                            # tell Liquidsoap to consume
    #     ... show plays ...
    #   linein_stop                             # tell Liquidsoap to disconnect
    #   self._linein_capture.stop()             # ffmpeg shuts down
    #
    # The URL is fixed at render time (set_url is exposed but Pypo
    # doesn't need to call it because there is only one capture
    # instance with one URL).  The set_url wrapper is kept for parity
    # with the webstream API + future multi-mount scenarios.

    def linein_set_url(self, dshow_spec: str) -> str:
        """
        Set the dshow input spec the input.ffmpeg linein source will
        open on the next :meth:`linein_start`.

        ``dshow_spec`` is the device's dshow alternative-name form, e.g.
        ``audio=@device_cm_{33D9A762-...}\\wave_{<GUID>}``.  Note the
        backslash before ``wave_`` — this is REQUIRED and is passed
        through verbatim over telnet (Liquidsoap's set_url takes the
        rest of the line as a raw string; spike 2026-05-30 confirmed
        the backslash survives the wire and the device opens).

        Wire-form constraints (telnet line protocol):
          * MUST NOT contain ``\\n`` / ``\\r`` (newline terminates the command)
          * MUST NOT contain ``"`` (would confuse Liquidsoap's parser)
          * Backslash IS allowed (dshow specs need it).

        Wire-form: ``linein.set_url <spec>`` — registered manually in
        rastatime.liq via server.register (input.ffmpeg does not
        auto-expose set_url as a telnet command, unlike input.http).
        """
        if any(ch in dshow_spec for ch in ('\n', '\r', '"')):
            raise ValueError(
                f"linein_set_url: dshow_spec contains a character that "
                f"would break the Liquidsoap telnet wire form: {dshow_spec!r}"
            )
        return self.send_command(f"linein.set_url {dshow_spec}")

    def linein_start(self) -> str:
        """
        Open the dshow device on the input.ffmpeg linein source.
        Pre-condition: :meth:`linein_set_url` must have set a valid
        dshow spec.

        Wire-form: ``linein.start`` (registered via server.register).
        The source goes ``source.is_ready=true`` once max_buffer
        seconds of audio are pre-fetched — the bus-switch then flips
        from scheduled to linein automatically.
        """
        return self.send_command("linein.start")

    def linein_stop(self) -> str:
        """
        Close the dshow device on the input.ffmpeg linein source.
        ``source.is_ready`` goes false, the switch falls through to
        scheduled.  Idempotent.

        Wire-form: ``linein.stop`` (registered via server.register).
        No Python subprocess to stop anymore — input.ffmpeg owns the
        dshow capture in-process.
        """
        return self.send_command("linein.stop")

    def linein_http_start(self) -> str:
        """
        RASTATIME 2026-08-31 — multichannel line-in path, widened to
        every mapping on 2026-09-03.

        Start the fixed-URL ``input.http`` companion source
        (id="linein_http") that consumes the local /linein-capture
        Icecast mount fed by FfmpegLineinCapture's MME feeder.  This is
        the path for every scheduled line-in that has a stored device
        name — the in-process dshow source cannot reach channels 3+ of
        a multichannel interface, and addresses even channels 1/2 by an
        endpoint GUID DirectShow does not recognise.

        Wire-form: ``linein_http.start`` (auto-registered by
        input.http under its source id).
        """
        return self.send_command("linein_http.start")

    def linein_http_stop(self) -> str:
        """
        Stop the ``input.http`` companion source.  Idempotent — a stop
        on an already-stopped source replies harmlessly.

        Wire-form: ``linein_http.stop`` (auto-registered).
        """
        return self.send_command("linein_http.stop")

    def linein_status(self) -> str:
        """
        Return Liquidsoap's free-text input.ffmpeg status for the
        linein source — ``"stopped"`` / ``"connected <spec>"`` etc.

        Wire-form: ``linein.status`` (registered via server.register).
        """
        return self.send_command("linein.status")

    def harbor_stop(self, harbor_id: str) -> str:
        """
        RASTATIME 2026-09-10 - disconnect the DJ client on a harbor
        (``master_dj`` / ``show_dj``).  Replaces the Icecast admin
        ``killsource`` of the deleted mpv path: the DJs connect to the
        harbor inside Liquidsoap, so only Liquidsoap can drop them.

        Wire-form: ``<harbor_id>.stop`` (registered by input.harbor,
        "Stop current source client, if connected.").  Replies
        ``Done`` - also when nobody is connected.
        """
        if harbor_id not in ("master_dj", "show_dj"):
            raise ValueError(f"unknown harbor id {harbor_id!r}")
        return self.send_command(f"{harbor_id}.stop")

    # ---- RASTATIME 2026-09-13 - ICY metadata variables -----------------

    @staticmethod
    def _one_line(value: str) -> str:
        """``interactive.set`` splits the command on ``=`` and takes the
        raw, trimmed text after it (no quotes, no unescaping) - so the
        value must be one line and must not contain ``=``."""
        text = " ".join(str(value or "").split())
        return text.replace("=", "-")

    def var_set_string(self, name: str, value: str) -> str:
        """
        Set an ``interactive.string`` variable.  Wire-form: ``var.set
        <name> = <raw text>`` - the stdlib takes everything after the
        first ``=`` verbatim (quotes would become part of the value).
        """
        return self.send_command(f"var.set {name} = {self._one_line(value)}")

    def var_set_int(self, name: str, value: int) -> str:
        """Set an ``interactive.int`` variable (``var.set <name> = <int>``)."""
        return self.send_command(f"var.set {name} = {int(value)}")

    def icy_status(self) -> str:
        """The ICY settings in effect (``icy.status``, rendered 2026-09-13)."""
        return self.send_command("icy.status")

    # ---- Internals (lock must be held) ------------------------------

    def _connect_locked(self) -> None:
        """Open socket — caller must hold ``self._lock``."""
        try:
            sock = socket.create_connection(
                (self._host, self._port),
                timeout=self._timeout,
            )
            sock.settimeout(self._timeout)
            self._socket = sock
            self._recv_buf = b""
            logger.info(
                "Connected to Liquidsoap telnet at %s:%d",
                self._host, self._port,
            )
        except OSError as exc:
            raise ConnectionError(
                f"Cannot connect to Liquidsoap telnet at "
                f"{self._host}:{self._port}: {exc}"
            ) from exc

    def _close_locked(self, *, send_quit: bool) -> None:
        """Close socket — caller must hold ``self._lock``."""
        if self._socket is None:
            return
        if send_quit:
            try:
                self._socket.sendall(b"quit\n")
            except OSError:
                pass  # already broken — fine
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass
        self._socket = None
        self._recv_buf = b""
        logger.info("Disconnected from Liquidsoap telnet")

    def _read_until_end_locked(self) -> str:
        """
        Read socket bytes until the ``END`` sentinel is seen.
        Returns the response body without the sentinel line,
        stripped of outer whitespace.  Caller must hold lock.

        Uses ``self._recv_buf`` so any bytes received past the END
        sentinel (rare, but possible if the server pipelines) are
        carried over to the next call.
        """
        assert self._socket is not None  # caller already ensured

        while True:
            # Check current buffer for an END sentinel before doing
            # more I/O — saves a round-trip when send() already
            # delivered the response body.
            body = self._extract_response(self._recv_buf)
            if body is not None:
                # body is (response_str, remaining_buf)
                response_str, remaining = body
                self._recv_buf = remaining
                return response_str

            try:
                chunk = self._socket.recv(4096)
            except socket.timeout as exc:
                raise ConnectionError(
                    f"Timed out waiting for END sentinel after "
                    f"{self._timeout}s"
                ) from exc

            if not chunk:
                raise ConnectionError(
                    "Telnet socket closed unexpectedly before END "
                    "sentinel"
                )
            self._recv_buf += chunk

    @classmethod
    def _extract_response(cls, buf: bytes):
        """
        Look for the END sentinel in ``buf``.  Returns
        ``(response_str, remaining_buf)`` if found, ``None`` otherwise.

        Response is everything before the END line, stripped.
        Remaining_buf is anything after the END line (typically
        empty, but server-side pipelining could leave bytes).
        """
        for sentinel in cls._END_VARIANTS:
            idx = buf.find(sentinel)
            if idx != -1:
                body = buf[:idx]
                remaining = buf[idx + len(sentinel):]
                return body.decode("utf-8", errors="replace").strip(), remaining

        # Empty-response special case: buf starts with "END\r\n" or "END\n"
        # (no preceding body, no leading newline before END).
        for sentinel in cls._END_ONLY_VARIANTS:
            if buf.startswith(sentinel):
                remaining = buf[len(sentinel):]
                return "", remaining

        return None

    @staticmethod
    def _escape_value(value: str) -> str:
        """
        Escape a metadata value for inclusion in
        ``metadata.update key="..."`` format.

        Backslash-escapes embedded double quotes and backslashes.
        Liquidsoap's parser handles ``\\"`` and ``\\\\`` inside
        the double-quoted string.
        """
        return value.replace("\\", "\\\\").replace('"', '\\"')
