"""
LiquidsoapPlayoutEngine — Liquidsoap adapter for RASTATIME.

RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C2 (engine wire-up).

Drop-in replacement for :class:`MpvPlayoutEngine` and
:class:`VlcPlayoutEngine` (ADR-002).  Talks to a long-running
Liquidsoap subprocess via the telnet line-protocol server on
``localhost:1234`` (see :mod:`liquidsoap_telnet`).

Architectural shift vs. mpv/VLC engines
---------------------------------------

The mpv and VLC engines own the audio output themselves — when
``play(uri)`` is called, mpv/VLC starts decoding and pushing to
the OS audio device, and the Pypo scheduler then spawns three
parallel FfmpegStreamer subprocesses that re-read the same file
and push it to Icecast.

The Liquidsoap engine inverts the relationship.  Liquidsoap is a
long-running NSSM-managed subprocess that holds:

  * A ``request.queue`` source that we push file URIs into
  * The Master/Show DJ ``input.harbor`` sources (Phase C4)
  * A ``switch(...)`` that picks the active source (Phase C4)
  * Three ``output.icecast`` blocks (mp3 / aac / ogg) with a
    single persistent Icecast PUT per mount (Phase C3)

When the scheduler wants to "play file X", we call :meth:`play`
which sends an ``annotate:`` + ``file:`` wrapped URI to
``request.queue.push`` over telnet.  Liquidsoap then decodes,
encodes, mixes, and ships the audio entirely by itself — no
separate FfmpegStreamer subprocesses, and Liquidsoap's native
gapless transitions handle the tail-cut problem that the mpv
engine works around with ``wait_until_stopped`` + 500 ms hack.

Cue points + replay-gain
------------------------

``cue_in`` / ``cue_out`` / ``gain_db`` ride on the Liquidsoap
``annotate:`` protocol, which lets us attach metadata to any
request URI.  The .liq script then reads those annotations
with operators like ``amplify(override="replaygain_track_gain",
…)`` and the built-in cue-handling on ``request.queue``.

Example URI we send to Liquidsoap::

    annotate:cue_in="0.5",cue_out="180.0",
             replaygain_track_gain="-5.95 dB"
             :file:///C:/rastatime/scheduler/580.mp3

The .liq side picks these up automatically — the ``request.queue``
operator parses ``cue_in`` / ``cue_out`` natively, and our
``amplify(override="replaygain_track_gain", …)`` block picks up
the gain value (which the operator parses as a "<float> dB"
string).

What this phase does NOT cover (deferred to later C-phases):

  * Live-source switching (Master DJ / Show DJ): Phase C4 via
    ``input.harbor`` in the .liq script + ``var.set`` over
    telnet — not via :meth:`play`.
  * ICY-metadata pushes per track: Phase C6 via
    ``metadata.update`` over telnet (separate code path that
    runs in parallel with this engine).
  * Recording: Phase C5 via ``output.file`` in the .liq script
    (no Python-side hook — entirely server-side).
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Dict, List, Optional

from .interface import PlayoutEngine, PlayoutState
from .liquidsoap_telnet import LiquidsoapTelnetClient

logger = logging.getLogger(__name__)


# Regex used by _normalise_uri — matches both ``C:\foo`` and ``C:/foo``
# at the very start of the URI argument, so we can detect a Windows
# drive-letter path that needs ``file:///`` wrapping.
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


# How long Engine.stop() waits before it actually skips on Liquidsoap.
# If play() comes within this window with the SAME URI, both calls
# collapse to a no-op (Pypo's catch-up pattern can fire stop+play for
# the same track 2-3 times in quick succession; without de-dup
# Liquidsoap would crossfade between two copies of the same file).
# 0.5 s is long enough to swallow the catch-up triple-bounce we saw
# in the C8 reality-test, short enough that a DJ-source-takeover
# (which legitimately stops the queue without a follow-up play)
# doesn't hold up the silence-fallback noticeably.
_DEFERRED_STOP_SECONDS = 0.5

# Tracks shorter than this (in seconds) get crossfade disabled via the
# per-track `liq_cross_duration="0.0"` annotation.  Reason: the
# crossfade operator's fade-in/fade-out zones (default 1 s each on
# our config) eat the start + end of short jingles / StationIDs,
# making them barely audible or completely silent.  Phase-D Stück-B
# observation 2026-05-28: a 3 s jingle had ~1 s of pure audio between
# 1 s fade-in and 1 s fade-out.  Setting `liq_cross_duration=0.0` for
# tracks under this threshold tells Liquidsoap to do a direct cut
# instead — jingles play in their full original length.
#
# 8.0 s is the operator-decision threshold (Phase-D Stück-B,
# 2026-05-28): jingles up to 8 s are typically StationIDs / sweepers
# that should "punch" with a hard cut; tracks above 8 s are music or
# spoken-word content where the crossfade improves the listener
# experience.
_NO_CROSSFADE_THRESHOLD_SECONDS = 8.0


class LiquidsoapPlayoutEngine(PlayoutEngine):
    """
    Liquidsoap-backed playout engine — same PlayoutEngine contract
    as the mpv/VLC adapters, but delegates the actual audio work to
    a long-running Liquidsoap subprocess over telnet.

    Connection target defaults match the Liquidsoap stdlib telnet
    server example (``127.0.0.1:1234``); override via env-vars
    ``RASTATIME_LIQUIDSOAP_HOST`` and ``RASTATIME_LIQUIDSOAP_PORT``
    if the operator runs Liquidsoap on a different port (e.g. to
    isolate from a second Liquidsoap instance).

    Thread-safety: ``play()``, ``stop()``, ``close()`` may be
    called from different threads.  All public methods route
    through :class:`LiquidsoapTelnetClient`, which serialises
    socket I/O on its own internal lock — so concurrent calls
    from Python are safe.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        telnet_client: Optional[LiquidsoapTelnetClient] = None,
    ) -> None:
        # State mirror of what we've told Liquidsoap to do.  Until
        # we wire up a proper get-status-from-telnet pull, this is
        # the engine's best knowledge of "what's currently playing".
        self._state = PlayoutState.STOPPED
        self._current_uri: Optional[str] = None
        self._current_request_id: Optional[str] = None

        # Deferred-stop machinery (Phase-C8 follow-up): stop() doesn't
        # immediately send `scheduled.skip` to Liquidsoap — it only
        # marks the intent + arms a short timer.  play() within the
        # _DEFERRED_STOP_SECONDS window either cancels the skip (same
        # URI, idempotent re-issue) or flushes it (different URI, real
        # track change).  All mutations to these fields happen under
        # self._stop_lock so a Pypo stop+play+catch-up burst doesn't
        # race with the timer thread's flush.
        self._stop_lock = threading.Lock()
        self._stop_requested = False
        self._stop_timer: Optional[threading.Timer] = None

        # Telnet client to Liquidsoap.  Connection is lazy — first
        # send_command opens the socket.  Allows the scheduler to
        # boot before Liquidsoap is fully up.
        #
        # The ``telnet_client`` injection point is for tests — production
        # callers leave it None and the engine builds the real client
        # from the env-var-resolved host/port.
        if telnet_client is not None:
            self._telnet = telnet_client
        else:
            self._telnet = LiquidsoapTelnetClient(
                host=host
                or os.environ.get("RASTATIME_LIQUIDSOAP_HOST", "127.0.0.1"),
                port=port
                or int(os.environ.get("RASTATIME_LIQUIDSOAP_PORT", "1234")),
            )

        logger.info(
            "LiquidsoapPlayoutEngine initialised (telnet target %s:%d)",
            self._telnet._host, self._telnet._port,
        )

    # ------------------------------------------------------------------
    # PlayoutEngine interface
    # ------------------------------------------------------------------

    def play(
        self,
        uri: str,
        *,
        cue_in: float = 0.0,
        cue_out: Optional[float] = None,
        media_options: Optional[List[str]] = None,
        gain_db: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Push ``uri`` onto Liquidsoap's request queue.

        ``cue_in`` / ``cue_out`` / ``gain_db`` / ``metadata`` are all
        encoded as Liquidsoap ``annotate:`` attributes — the .liq
        script reads them with ``request.queue`` (cue handling),
        ``amplify(override="replaygain_track_gain", …)`` (gain
        handling), and Liquidsoap's built-in metadata propagation
        (which ships ``title`` / ``artist`` / etc. through to every
        ``output.icecast`` block automatically).

        ``media_options`` is accepted for interface compatibility but
        ignored: Liquidsoap takes HTTP auth from the URI's userinfo,
        same as mpv/ffmpeg.

        On any telnet failure the engine flips into ``ERROR`` state
        and logs — same pattern as the mpv engine.  We do NOT raise
        out of ``play()`` because the Pypo scheduler treats a play()
        exception as a scheduler-level crash; we want a clear-but-
        contained failure that the next play() attempt can recover
        from.
        """
        meta_summary = (
            ",".join(f"{k}={v!r}" for k, v in (metadata or {}).items())
            if metadata else "none"
        )

        # Deferred-stop idempotency (Phase-C8 follow-up).  Pypo's
        # catch-up flow can call stop()+play() for the SAME URI two or
        # three times within a few hundred ms when the schedule API
        # re-identifies an in-progress event.  If we see a pending stop
        # for what would be a re-issue of the currently-playing track,
        # cancel both the deferred skip AND skip the new push — the
        # track keeps playing uninterrupted on the Liquidsoap side.
        with self._stop_lock:
            if self._stop_timer is not None:
                self._stop_timer.cancel()
                self._stop_timer = None
            if (
                self._stop_requested
                and uri == self._current_uri
                and self._state == PlayoutState.PLAYING
            ):
                self._stop_requested = False
                logger.debug(
                    "Liquidsoap play: idempotent re-issue for %s — "
                    "cancelling pending stop, keeping current track.",
                    self._redact(uri),
                )
                return
            # Different URI (or first play): flush any pending stop NOW
            # so Liquidsoap can switch cleanly.
            if self._stop_requested:
                self._stop_requested = False
                try:
                    self._telnet.request_queue_skip()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "Liquidsoap deferred-stop skip failed: %s", exc,
                    )

        logger.info(
            "Liquidsoap play: uri=%s cue_in=%.2fs cue_out=%s gain=%s meta=%s",
            self._redact(uri),
            cue_in,
            f"{cue_out:.2f}s" if cue_out is not None else "natural",
            f"{gain_db:+.2f}dB" if gain_db else "none",
            meta_summary,
        )

        self._current_uri = uri
        self._current_request_id = None

        try:
            wrapped = self._build_annotate_uri(
                uri,
                cue_in=cue_in,
                cue_out=cue_out,
                gain_db=gain_db,
                metadata=metadata,
            )
            response = self._telnet.request_queue_push(wrapped)
            # Liquidsoap signals push-failure either as "ERROR: …" or
            # by replying with a non-numeric, non-empty string.  The
            # most common case in the wild is "ERROR: unknown command"
            # (queue source-id mismatch between .liq and Python side)
            # — that used to silently flip the engine to PLAYING with
            # request_id=None and listeners only heard silence.  Now
            # we check the response prefix and bail out into ERROR.
            if response.startswith("ERROR"):
                logger.error(
                    "Liquidsoap rejected push for %s: %s",
                    self._redact(uri), response.strip(),
                )
                self._state = PlayoutState.ERROR
                return
            self._current_request_id = self._extract_request_id(response)
            self._state = PlayoutState.PLAYING
            logger.debug(
                "Liquidsoap accepted request_id=%s for %s",
                self._current_request_id, self._redact(uri),
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Telnet errors (ConnectionError) and any other surprise
            # from the wire layer end up here.  Mirror the mpv engine:
            # set ERROR state, log, and swallow so the scheduler can
            # decide whether the next event should still try.
            logger.error(
                "Liquidsoap play failed for %s: %s",
                self._redact(uri), exc,
            )
            self._state = PlayoutState.ERROR

    def stop(self) -> None:
        """
        Defer the skip-on-Liquidsoap by _DEFERRED_STOP_SECONDS so a
        subsequent play() within the window can either cancel it (same
        URI = catch-up idempotency, see :meth:`play`) or flush it (URI
        change = real track-transition).  If no play() arrives, a
        Timer thread flushes the skip eventually so DJ-takeover-style
        stops still take effect.

        The legacy mpv/VLC engines do an immediate hard-stop because
        they own the audio path; with Liquidsoap the queue + crossfade
        operators handle gapless transitions natively and an aggressive
        skip-then-push produces an audible glitch (Phase-C8 reality-
        test 2026-05-26 found this).
        """
        logger.info("Liquidsoap stop (deferred up to %.1fs)", _DEFERRED_STOP_SECONDS)
        with self._stop_lock:
            self._stop_requested = True
            if self._stop_timer is not None:
                self._stop_timer.cancel()
            self._stop_timer = threading.Timer(
                _DEFERRED_STOP_SECONDS, self._flush_pending_stop,
            )
            self._stop_timer.daemon = True
            self._stop_timer.start()

    def _flush_pending_stop(self) -> None:
        """
        Timer-thread callback: actually send the deferred skip to
        Liquidsoap.  No-op if play() already cancelled the stop.
        """
        with self._stop_lock:
            if not self._stop_requested:
                return
            self._stop_requested = False
            self._stop_timer = None
        # Outside the lock to keep the lock-window tiny.
        try:
            self._telnet.request_queue_skip()
            logger.debug("Liquidsoap deferred-stop flushed.")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Liquidsoap deferred-stop telnet error: %s", exc,
            )
        # Clear playback state only after the actual skip — keeping
        # _current_uri intact during the deferral window is what lets
        # play() detect the idempotent re-issue.
        self._state = PlayoutState.STOPPED
        self._current_uri = None
        self._current_request_id = None

    def get_state(self) -> PlayoutState:
        """
        Return cached state.  Liquidsoap's telnet
        ``request.queue.queue`` could be polled to refresh this, but
        Pypo only checks state in the next-track-handler hot path so
        caching is fine.

        TODO Phase C8: optionally pull live status before returning,
        bounded by a short telnet timeout, as a robustness measure
        against the Python-side state mirror drifting from the actual
        Liquidsoap queue state.
        """
        return self._state

    def close(self) -> None:
        """
        Close the telnet connection.  Does NOT terminate the
        Liquidsoap subprocess — that's NSSM's job (see
        ``nssm-install-liquidsoap.ps1``).

        Flushes any pending deferred-stop synchronously first so the
        running track is actually skipped at shutdown (otherwise it
        would play on after the Python process exits — Liquidsoap's
        queue lives in the long-running subprocess, not in Python).
        """
        with self._stop_lock:
            if self._stop_timer is not None:
                self._stop_timer.cancel()
                self._stop_timer = None
            had_pending = self._stop_requested
            self._stop_requested = False
        if had_pending:
            try:
                self._telnet.request_queue_skip()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Liquidsoap close: flushing pending stop failed: %s", exc,
                )
        try:
            self._telnet.close()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap close telnet error: %s", exc)
        logger.info("LiquidsoapPlayoutEngine closed")

    def set_audio_device(self, device_id: Optional[str]) -> None:
        """
        Liquidsoap's local-monitoring output is configured in the
        .liq script (``output.ao`` / ``output.portaudio`` / etc.).
        Live device switching would need a server-command-driven
        re-wiring inside the script — not in Phase C scope.

        For Phase C we just log + warn, same fallback that the
        ``PlayoutEngine`` ABC does by default.  Phase D may add a
        proper ``var.set`` + script-side reconfigurable output.
        """
        logger.warning(
            "set_audio_device(%r) called — Liquidsoap engine does not yet "
            "implement runtime device switching.  Configure the local "
            "output statically in rastatime.liq for now.",
            device_id,
        )

    # ------------------------------------------------------------------
    # PlayoutEngine optional method — already on the ABC
    # ------------------------------------------------------------------

    def wait_until_stopped(self, timeout: float) -> bool:
        """
        For mpv this waits for libmpv's end-file event so short-track
        tails get flushed before the hard stop (see the Phase-1
        Seamless-Bus-Mix work).

        For Liquidsoap this is a NO-OP that returns True immediately:
        the .liq pipeline has gapless transitions between
        ``request.queue`` items natively, so the scheduler does NOT
        need to delay its next-track event for a tail-flush.  That's
        actually one of the headline benefits of moving to
        Liquidsoap — the 500 ms wait hack in the mpv path goes away
        once the Liquidsoap engine is the active backend.
        """
        return True

    # ------------------------------------------------------------------
    # Phase C5 — Show recording (Liquidsoap-specific, NOT on the ABC)
    # ------------------------------------------------------------------
    #
    # The rastatime.liq template renders an ``output.file(id="recording",
    # …)`` block whose filename comes from a Liquidsoap interactive
    # variable ``recording_path``.  Pypo's _on_show_record_start /
    # _on_show_record_end hooks call these three wrappers when
    # ``streaming_handled_externally=True`` — the legacy mpv/VLC engines
    # leave FfmpegRecorder in charge and never touch them.
    #
    # Reality-tested 2026-05-27 (Mechanismus B):
    #   * fresh start: 100.6 % of expected byte count over 10 s
    #   * back-to-back: 100.3 % of expected, three-command roundtrip 31 ms
    # The OS write-cache buffers actual bytes for ~256 KB; the cache is
    # flushed when ``recording_stop`` closes the file, so the per-show
    # MP3 always ends complete and at the expected duration.

    def recording_start(self, path: str) -> None:
        """
        Open Liquidsoap's ``output.file(id="recording", ...)`` at
        ``path`` and start writing the internal bus (mixed scheduled +
        DJ + blank-fallback audio) to a fresh MP3.

        Uses Mechanismus B (verified 2026-05-27): explicit
        stop → var.set recording_path → start triple-command — this
        forces Liquidsoap to re-evaluate the filename function on each
        start so the new path is honoured (otherwise the filename
        function is only evaluated once when the output block first
        opens).

        Path constraints (Liquidsoap-telnet wire-form):
          * forward-slash form (``C:/...`` on Windows, no backslashes)
          * no ``\\n``, ``\\r``, ``"``, or ``\\`` characters in the path
            — these would break the wire-form parsing.  Caller is
            responsible for sanitisation (the rastatime.liq output.file
            block does its own mkdir on the parent directory, but the
            scheduler also creates the parent dir defensively because
            output.file's mkdir behaviour is encoder-dependent).

        The initial ``recording_stop`` is a safety idempotency guard:
        if a prior show's stop somehow missed (Pypo crash mid-show,
        telnet timeout that left Liquidsoap in 'on' state), the stop
        here closes the orphan file before we re-open at the new path.
        """
        # Safety: idempotent stop in case a prior show didn't end cleanly.
        try:
            self._telnet.recording_stop()
        except (OSError, ConnectionError) as exc:
            logger.warning(
                "Liquidsoap recording_start: prior-stop telnet failed "
                "(%s); continuing with set_path + start anyway.", exc,
            )
        self._telnet.recording_set_path(path)
        self._telnet.recording_start()
        logger.info("Liquidsoap recording_start: opened %s", path)

    def recording_stop(self) -> None:
        """
        Close the currently-open recording file.  Idempotent — a stop
        on an already-stopped recording replies "Done" on the
        Liquidsoap side and produces no error.

        Closing the file forces the OS write-cache flush, so the .mp3
        on disk reflects every audio frame that was on the bus up to
        the stop instant.  No post-roll delay is needed because the
        recording is on the SAME internal bus as the Icecast outputs —
        the legacy FfmpegRecorder's 1 s post-roll was a workaround for
        HTTP-source-buffering lag, which doesn't apply here.
        """
        self._telnet.recording_stop()
        logger.info("Liquidsoap recording_stop: closed current recording")

    def recording_status(self) -> str:
        """
        Return Liquidsoap's free-text recording status (typically
        ``'on'`` or ``'off'``).  Mainly for diagnostics — Pypo's
        scheduler doesn't gate on this since the start/stop wrappers
        are themselves idempotent.
        """
        return self._telnet.recording_status()

    # ------------------------------------------------------------------
    # Phase E — Scheduled webstream lifecycle (Liquidsoap-specific)
    # ------------------------------------------------------------------
    #
    # The rastatime.liq template renders an ``input.http(id="webstream",
    # start=false, ...)`` source initialised with an empty URL.  Pypo's
    # _on_webstream_start / _on_stop hooks (for WebStreamEvent items)
    # call these two wrappers when streaming_handled_externally=True —
    # the legacy mpv/VLC engines keep using engine.play(url) and never
    # touch them.
    #
    # Why a separate input.http source instead of request.queue.push:
    # the Phase-E reality-test 2026-05-29 (logged in
    # C:/rastatime/logs/liquidsoap.log around 10:55:00 + 11:01:05)
    # showed request.queue fails on HTTP URLs:
    #   * procol.external mime-type sniff returns "text/html" for
    #     typical streaming endpoints (redirect URLs)
    #   * file-extension detection fails
    #   * 29 s default request timeout — stream never becomes ready
    # input.http is the canonical Liquidsoap pattern for persistent
    # HTTP audio sources; it self-syncs, auto-reconnects, and exposes
    # set_url / start / stop methods via the source-id namespace.

    def webstream_start(
        self, url: str, *, gain_db: Optional[float] = None,
    ) -> None:
        """
        Start a scheduled webstream by setting the URL + optional gain
        on Liquidsoap's input.http source, then issuing webstream.start.

        Phase-E sequence (analogue to recording_start's Mechanism B):
          1. webstream_set_url(url)              — set the HTTP URL
          2. webstream_set_gain(linear_factor)   — set amplify factor
                                                   (only if gain_db is set
                                                    and non-zero)
          3. webstream_start                     — connect + buffer

        The source goes ``source.is_ready=true`` only after the
        input.http max_buffer seconds (default 10 s) of audio have been
        pre-fetched.  The switch operator in the .liq script then flips
        the bus from scheduled (silence_fallback) to webstream
        automatically.

        ``gain_db`` is in decibels (typically -12 to +12 dB).  Pypo
        converts to a linear amplify factor before pushing to Liquidsoap::

            linear_factor = 10 ** (gain_db / 20.0)
            # e.g. +3 dB → 1.412, -6 dB → 0.501, 0 dB → 1.0

        A ``gain_db`` of None or 0 skips the gain set entirely — the
        Liquidsoap-side interactive.float defaults to 1.0 (unity) and
        we don't need to re-set it.  But to be safe across show-to-show
        transitions where one show had +3 dB and the next has none, we
        DO set 1.0 explicitly when gain_db is None — otherwise the
        next webstream would inherit the previous show's gain.
        """
        gain_for_log = (
            f"{gain_db:+.2f}dB"
            if gain_db is not None and abs(gain_db) > 0.001
            else "unity"
        )
        logger.info(
            "Liquidsoap webstream_start: url=%s gain=%s",
            self._redact(url), gain_for_log,
        )

        try:
            self._telnet.webstream_set_url(url)
            # Always set the gain — either the actual value or unity —
            # so a previous show's non-unity gain doesn't leak into the
            # new webstream.
            if gain_db is not None and abs(gain_db) > 0.001:
                linear_factor = 10.0 ** (gain_db / 20.0)
            else:
                linear_factor = 1.0
            self._telnet.webstream_set_gain(linear_factor)
            self._telnet.webstream_start()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Liquidsoap webstream_start failed for %s: %s",
                self._redact(url), exc,
            )
            # Don't raise — same fail-soft pattern as play() so the
            # Pypo scheduler can carry on with the next event.

    def webstream_stop(self) -> None:
        """
        Stop the input.http source — Liquidsoap closes the HTTP
        connection cleanly.  ``source.is_ready`` goes false, the
        switch operator falls through to scheduled.

        Idempotent: a stop on an already-stopped source replies "Done"
        on the Liquidsoap side and produces no error.  Same convention
        as :meth:`recording_stop`.
        """
        try:
            self._telnet.webstream_stop()
            logger.info("Liquidsoap webstream_stop: closed")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Liquidsoap webstream_stop telnet error: %s", exc,
            )

    def webstream_status(self) -> str:
        """
        Return Liquidsoap's free-text input.http status string, one of
        ``"stopped"``, ``"starting"``, ``"polling"``, ``"connected <url>"``,
        or ``"stopping"``.  Mainly for diagnostics — the start/stop
        wrappers are themselves idempotent.
        """
        return self._telnet.webstream_status()

    # ------------------------------------------------------------------
    # Phase-F-2 — Scheduled line-input lifecycle (Liquidsoap-specific)
    # ------------------------------------------------------------------
    #
    # The rastatime.liq template renders an ``input.ffmpeg(id="linein",
    # format="dshow", start=false, ...)`` source that opens a Windows
    # dshow audio device DIRECTLY via Liquidsoap's in-process
    # libavdevice — no external ffmpeg subprocess, no HTTP hop
    # (this replaced the Phase-F input.http + FfmpegLineinCapture
    # approach on 2026-05-30).
    #
    # Pypo's _on_linein_start (in Liquidsoap mode) builds the dshow
    # alternative-name spec from the schedule item's device GUID and
    # passes it to engine.linein_start(dshow_spec).  _on_stop calls
    # linein_stop.  No Python subprocess to manage anymore.
    #
    # The template exposes set_url / start / stop / status via
    # server.register (input.ffmpeg does NOT auto-register them, unlike
    # input.http — spike-verified 2026-05-30).  Runtime device-switch
    # works (set_url with a different spec), the capability
    # input.portaudio lacked.

    def linein_start(self, dshow_spec: str) -> None:
        """
        Open a scheduled line-input on Liquidsoap's input.ffmpeg dshow
        source.

        ``dshow_spec`` is the device's dshow alternative-name form, e.g.
        ``audio=@device_cm_{33D9A762-...}\\wave_{<GUID>}`` — Pypo builds
        it from the schedule item's device GUID
        (``_stable_id_to_dshow_audio``).

        Uses **Mechanism B** (stop → set_url → start), the same pattern
        as :meth:`recording_start`.  RASTATIME 2026-05-30 live-test
        revealed why this is REQUIRED: ``set_url`` on an already-running
        input.ffmpeg source is a NO-OP — the device only changes when
        the source is stopped first, then re-opened.  Without the
        leading stop, a device-switch between back-to-back line-in
        shows left the OLD device on air ("Jabra selected, Tascam
        still audible" bug).  The isolated spike confirmed
        stop→set_url→start switches the device cleanly.

        The leading stop is also an idempotency guard: a stop on an
        already-stopped source replies "Done" and is harmless.

        Mirrors :meth:`webstream_start`'s fail-soft behaviour — any
        telnet error is logged + swallowed so the scheduler can
        continue with the next event.
        """
        logger.info("Liquidsoap linein_start: dshow_spec=%s", dshow_spec)
        try:
            # Mechanism B: stop first so set_url actually takes effect
            # on the (possibly already-running) source.  Also stop the
            # http companion — the previous show may have been a
            # multichannel line-in (RASTATIME 2026-08-31).
            self._telnet.linein_http_stop()
            self._telnet.linein_stop()
            self._telnet.linein_set_url(dshow_spec)
            self._telnet.linein_start()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Liquidsoap linein_start failed: %s", exc,
            )

    def linein_start_http(self) -> None:
        """
        RASTATIME 2026-08-31 — multichannel line-in path (BACKLOG
        "Line-In: Kanal-Auswahl auf Multi-Input-Devices").

        Start the fixed-URL ``input.http`` companion source that
        consumes the local /linein-capture mount.  The caller must
        have started :class:`FfmpegLineinCapture` (with its MME
        feeder) first, so the mount carries audio by the time the
        source's max_buffer fills.  Stops the direct-dshow source
        first — the previous show may have been a plain-stereo
        line-in.  Fail-soft like :meth:`linein_start`.
        """
        logger.info("Liquidsoap linein_start_http: /linein-capture mount")
        try:
            self._telnet.linein_stop()
            self._telnet.linein_http_stop()
            self._telnet.linein_http_start()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Liquidsoap linein_start_http failed: %s", exc,
            )

    def linein_stop(self) -> None:
        """
        Tell Liquidsoap to disconnect the line-in sources.  Stops both
        the direct-dshow source and the http companion (RASTATIME
        2026-08-31 — only one is ever running, and a stop on the idle
        one is harmless), so the caller needs no path bookkeeping.
        ``source.is_ready`` goes false, the switch operator falls
        through to scheduled.

        Idempotent: a stop on an already-stopped source replies "Done"
        on the Liquidsoap side and produces no error.  Same convention
        as :meth:`webstream_stop` and :meth:`recording_stop`.
        """
        try:
            self._telnet.linein_stop()
            self._telnet.linein_http_stop()
            logger.info("Liquidsoap linein_stop: closed")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Liquidsoap linein_stop telnet error: %s", exc,
            )

    def linein_status(self) -> str:
        """
        Return Liquidsoap's free-text input.http status for the linein
        source.  Same semantics as :meth:`webstream_status`.  Mainly
        for diagnostics.
        """
        return self._telnet.linein_status()

    # ------------------------------------------------------------------
    # Internal helpers — URI / annotate building
    # ------------------------------------------------------------------

    @classmethod
    def _build_annotate_uri(
        cls,
        uri: str,
        *,
        cue_in: float,
        cue_out: Optional[float],
        gain_db: Optional[float],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Wrap ``uri`` in a Liquidsoap ``annotate:`` envelope encoding
        the cue points + replay-gain + ICY-metadata.  If no
        annotations are needed the bare URI (with file:// normalisation
        applied) is returned as-is — avoids extra parser work in
        Liquidsoap.

        Examples::

            >>> _build_annotate_uri("file:///x.mp3", cue_in=0,
            ...                     cue_out=None, gain_db=None)
            'file:///x.mp3'

            >>> _build_annotate_uri(
            ...   "file:///x.mp3", cue_in=0.5, cue_out=180.0,
            ...   gain_db=-5.95,
            ...   metadata={"title": "Song", "artist": "Band"})
            'annotate:cue_in="0.50",cue_out="180.00",replaygain_track_gain="-5.95 dB",title="Song",artist="Band":file:///x.mp3'
        """
        normalised = cls._normalise_uri(uri)

        annotations = []
        if cue_in and cue_in > 0:
            annotations.append(f'cue_in="{cue_in:.2f}"')
        if cue_out is not None and cue_out > 0:
            annotations.append(f'cue_out="{cue_out:.2f}"')
        if gain_db is not None and abs(gain_db) > 0.001:
            # Liquidsoap's amplify(override="replaygain_track_gain", …)
            # parses the value as a "<float> dB" string — sign is
            # carried in the float, "dB" suffix is required.
            annotations.append(
                f'replaygain_track_gain="{gain_db:+.2f} dB"'
            )

        # RASTATIME 2026-05-28 — Phase-D Stück-B: short-track crossfade-
        # override REVERTED.  Initial attempt was to set
        # `liq_cross_duration="0.0"` for tracks under 8 s, expecting
        # Liquidsoap's crossfade operator to skip the fade-in/fade-out
        # zones for that one track.  Live-test at 18:16 and 18:21
        # showed the OPPOSITE effect: short tracks (3-7 s jingles) became
        # COMPLETELY SILENT instead of "barely audible".  Liquidsoap's
        # interpretation of liq_cross_duration=0.0 seems to be "skip
        # this track entirely" rather than "play without crossfade".
        # See BACKLOG: Phase-D-Polish — "smarter short-track handling
        # in Liquidsoap crossfade".  For now no per-track annotation;
        # short tracks suffer the 1 s fade-in + 1 s fade-out eating
        # their start + end, but at least play partially audibly.

        # ICY-metadata fields — Liquidsoap propagates these to all
        # output.icecast blocks automatically.  Empty values and the
        # None entries skipped silently so callers can pass dicts
        # that contain ``None`` for missing fields (common in Pypo,
        # e.g. a track with no artist tag).
        if metadata:
            for key, value in metadata.items():
                if value is None or value == "":
                    continue
                annotations.append(
                    f'{key}="{cls._escape_annotate_value(str(value))}"'
                )

        if not annotations:
            return normalised

        return f"annotate:{','.join(annotations)}:{normalised}"

    @staticmethod
    def _escape_annotate_value(value: str) -> str:
        """
        Escape a metadata value for inclusion in
        ``annotate:key="..."`` syntax.  Liquidsoap's parser handles
        ``\\"`` and ``\\\\`` inside the double-quoted string.

        Identical semantics to
        :meth:`LiquidsoapTelnetClient._escape_value` — kept as a
        separate method here so the engine doesn't have to reach into
        the telnet-client internals.
        """
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _normalise_uri(uri: str) -> str:
        """
        Convert a Windows local-file path into Liquidsoap-friendly
        ``file://`` URI form.  HTTP URIs pass through unchanged.

        Liquidsoap 2.4's ``file:`` protocol handler strips the
        prefix and treats the rest as the path.  For Windows drive
        paths that means we need ``file://C:/path`` (2 slashes) —
        the conventional RFC-8089 ``file:///C:/path`` (3 slashes)
        leaves ``/C:/path`` after the strip and Liquidsoap rejects
        that as ``Unknown protocol URI "/C:/..."``.

        (Phase-C8 reality-test 2026-05-26 nailed this down via the
        manual telnet ``scheduled.push`` probe: only the 2-slash and
        no-slash variants get accepted.  See LIQUIDSOAP_PHASE_C8.md
        for the live-test trace.)

        An already-prefixed ``file:///`` URI from somewhere else
        gets converted to the 2-slash form for the same reason.

        Examples::

            >>> _normalise_uri("C:\\\\rastatime\\\\580.mp3")
            'file://C:/rastatime/580.mp3'
            >>> _normalise_uri("C:/rastatime/580.mp3")
            'file://C:/rastatime/580.mp3'
            >>> _normalise_uri("file:///C:/rastatime/580.mp3")
            'file://C:/rastatime/580.mp3'
            >>> _normalise_uri("file://C:/rastatime/580.mp3")
            'file://C:/rastatime/580.mp3'
            >>> _normalise_uri("http://example.com/stream.mp3")
            'http://example.com/stream.mp3'
        """
        # Bare Windows drive-letter path (back- or forward-slash).
        if _WINDOWS_DRIVE_RE.match(uri):
            forward = uri.replace("\\", "/")
            return f"file://{forward}"
        # Legacy 3-slash form fed in from somewhere else — rewrite
        # to 2-slash so the same Liquidsoap path-stripper doesn't
        # leave a leading "/" on the drive letter.
        if uri.startswith("file:///") and len(uri) > 8 and _WINDOWS_DRIVE_RE.match(uri[8:]):
            return "file://" + uri[8:]
        # Already a URI with scheme — pass through.  Liquidsoap
        # accepts file://, http://, https://, ftp://, plus its own
        # internal protocols (annotate:, replaygain:, …).  We don't
        # try to be clever here — the scheduler hands us valid URIs.
        return uri

    @staticmethod
    def _extract_request_id(response: str) -> Optional[str]:
        """
        Liquidsoap's ``request.queue.push`` replies with the
        request-id as a bare integer string (e.g. ``"42"``), or with
        a multi-line error if the URI couldn't be parsed.  Return the
        id if the response looks like one, else None.
        """
        if not response:
            return None
        # Take the first line, in case the response is multi-line.
        first = response.splitlines()[0].strip()
        if first.isdigit():
            return first
        return None

    @staticmethod
    def _redact(uri: Optional[str]) -> str:
        """
        Strip the password from a ``http://user:pass@host/…`` URI so
        it doesn't end up in the playout log.

        Mirrors :meth:`MpvPlayoutEngine._redact` so log lines stay
        consistent across both engines.
        """
        if not uri or "://" not in uri:
            return uri or ""
        scheme, rest = uri.split("://", 1)
        if "@" not in rest:
            return uri
        userinfo, hostpart = rest.rsplit("@", 1)
        if ":" in userinfo:
            user, _ = userinfo.split(":", 1)
            return f"{scheme}://{user}:***@{hostpart}"
        return uri
