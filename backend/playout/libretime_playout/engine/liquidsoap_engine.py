"""
LiquidsoapPlayoutEngine — Liquidsoap adapter for RASTATIME.

RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C2 (engine wire-up).

The only :class:`PlayoutEngine` implementation (ADR-002) since the
legacy mpv engine was deleted on 2026-09-10.  Talks to a long-running
Liquidsoap subprocess via the telnet line-protocol server on
``localhost:1234`` (see :mod:`liquidsoap_telnet`).

What Liquidsoap owns
--------------------

Liquidsoap is a long-running NSSM-managed subprocess that holds:

  * A ``request.queue`` source that we push file URIs into
  * The Master/Show DJ ``input.harbor`` sources (Phase C4)
  * The webstream and line-in input sources (Phases E / F)
  * A ``switch(...)`` that picks the active source (Phase C4)
  * Three ``output.icecast`` blocks (mp3 / aac / ogg) with a
    single persistent Icecast PUT per mount (Phase C3)
  * The per-show and 24/7 recording via ``output.file`` (Phase C5)

When the scheduler wants to "play file X", we call :meth:`play`
which sends an ``annotate:`` + ``file:`` wrapped URI to
``request.queue.push`` over telnet.  Liquidsoap then decodes,
encodes, mixes, and ships the audio entirely by itself, with native
gapless transitions.

Cue points + replay-gain
------------------------

``cue_in`` / ``cue_out`` / ``gain_db`` ride on the Liquidsoap
``annotate:`` protocol, which lets us attach metadata to any
request URI.  The .liq script then reads those annotations
with operators like ``amplify(override="replaygain_track_gain",
…)`` and the built-in cue-handling on ``request.queue``.

Example URI we send to Liquidsoap::

    annotate:liq_cue_in="0.5",liq_cue_out="180.0",
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
    Liquidsoap-backed playout engine: implements the PlayoutEngine
    contract by delegating the actual audio work to a long-running
    Liquidsoap subprocess over telnet.

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
        # RASTATIME 2026-09-27 - the item queued ahead of the playing one
        # (see enqueue / adopt_queued) and the last rt_cross shape sent.
        self._queued_uri: Optional[str] = None
        self._queued_request_id: Optional[str] = None
        self._cross_mode: Optional[str] = None

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
        transition: Optional[str] = None,
        skip_current: bool = True,
    ) -> None:
        """
        Push ``uri`` onto Liquidsoap's request queue.

        RASTATIME 2026-09-27 - order is PUSH, then SKIP.  The queue
        resolves a pushed request synchronously (request.queue_sync), so
        the cross operator finds the next track ready when the playing
        one is skipped and can run a real transition.  The old
        skip-then-push order made cross fall into the silence arm for a
        frame and every "crossfade" was a butt splice (production log
        2026-09-27: "Analysis ... / -infdB").  ``transition`` is sent as
        ``var.set rt_cross`` BEFORE the push; ``skip_current=False`` when
        nothing is on the queue (a skip would hit the new track).

        ``cue_in`` / ``cue_out`` / ``gain_db`` / ``metadata`` are all
        encoded as Liquidsoap ``annotate:`` attributes — the .liq
        script reads them with ``request.queue`` (cue handling),
        ``amplify(override="replaygain_track_gain", …)`` (gain
        handling), and Liquidsoap's built-in metadata propagation
        (which ships ``title`` / ``artist`` / etc. through to every
        ``output.icecast`` block automatically).

        ``media_options`` is accepted for interface compatibility but
        ignored: Liquidsoap takes HTTP auth from the URI's userinfo.

        On any telnet failure the engine flips into ``ERROR`` state
        and logs.  We do NOT raise
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
            # Different URI (or first play): a pending deferred stop is
            # folded into the skip AFTER the push (2026-09-27); nothing is
            # skipped before the new track sits on the queue.
            self._stop_requested = False

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
        self._queued_uri = None
        self._queued_request_id = None

        try:
            wrapped = self._build_annotate_uri(
                uri,
                cue_in=cue_in,
                cue_out=cue_out,
                gain_db=gain_db,
                metadata=metadata,
            )
            if transition:
                self._set_cross_mode(transition)
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
            if skip_current:
                # the pushed track is ready (synchronous queue): cut the
                # playing item now, cross runs the transition
                self._telnet.request_queue_skip()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Telnet errors (ConnectionError) and any other surprise
            # from the wire layer end up here.  Set ERROR state, log,
            # and swallow so the scheduler can
            # decide whether the next event should still try.
            logger.error(
                "Liquidsoap play failed for %s: %s",
                self._redact(uri), exc,
            )
            self._state = PlayoutState.ERROR

    def enqueue(
        self,
        uri: str,
        *,
        cue_in: float = 0.0,
        cue_out: Optional[float] = None,
        gain_db: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
        transition: Optional[str] = None,
    ) -> bool:
        """
        RASTATIME 2026-09-27 - push ``uri`` behind the playing track
        without skipping anything.  The cross operator buffers the last
        BUFFER seconds of the playing track and needs its partner on the
        queue BEFORE that window opens; the scheduler calls this a few
        seconds ahead of the row start and :meth:`adopt_queued` at the
        row start.  The shape (``rt_cross``) is set first so it is in
        place when the natural transition fires.
        """
        wrapped = self._build_annotate_uri(
            uri, cue_in=cue_in, cue_out=cue_out, gain_db=gain_db, metadata=metadata,
        )
        try:
            if transition:
                self._set_cross_mode(transition)
            response = self._telnet.request_queue_push(wrapped)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap enqueue failed for %s: %s", self._redact(uri), exc)
            return False
        if response.startswith("ERROR"):
            logger.warning(
                "Liquidsoap rejected the queued-ahead push for %s: %s",
                self._redact(uri), response.strip(),
            )
            return False
        self._queued_uri = uri
        self._queued_request_id = self._extract_request_id(response)
        logger.info(
            "Liquidsoap queued ahead: uri=%s cue_in=%.2fs cue_out=%s shape=%s rid=%s",
            self._redact(uri), cue_in,
            f"{cue_out:.2f}s" if cue_out is not None else "natural",
            transition or "-", self._queued_request_id,
        )
        return True

    def adopt_queued(
        self,
        uri: str,
        *,
        skip_current: bool = False,
        transition: Optional[str] = None,
    ) -> None:
        """
        RASTATIME 2026-09-27 - the queued-ahead item is the current one.
        A pending deferred stop is cancelled (it belonged to the
        predecessor, which cross is fading right now); with
        ``skip_current`` the predecessor is cut so the queued track takes
        over at once (overbook at a show boundary).
        """
        with self._stop_lock:
            if self._stop_timer is not None:
                self._stop_timer.cancel()
                self._stop_timer = None
            self._stop_requested = False
        if skip_current:
            try:
                if transition:
                    self._set_cross_mode(transition)
                self._telnet.request_queue_skip()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Liquidsoap skip to the queued track failed: %s", exc)
        self._current_uri = uri
        self._current_request_id = self._queued_request_id
        self._queued_uri = None
        self._queued_request_id = None
        self._state = PlayoutState.PLAYING

    def flush_queued(self) -> None:
        """RASTATIME 2026-09-27 - drop pending requests (the playing one is untouched)."""
        try:
            self._telnet.request_queue_flush()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap queue flush failed: %s", exc)
        self._queued_uri = None
        self._queued_request_id = None

    def playing_remaining_seconds(self) -> Optional[float]:
        """
        ``scheduled.remaining`` over telnet, ``"<rid> <seconds>"``.  None on
        error or unknown (-1); 0.0 when the RID is the one queued ahead -
        cross has already pulled the successor, the predecessor is in the
        tail (a skip now would hit the successor).
        """
        try:
            raw = self._telnet.request_queue_remaining().strip().splitlines()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap remaining could not be read: %s", exc)
            return None
        for line in raw:
            parts = line.strip().split()
            if not parts:
                continue
            try:
                value = float(parts[-1])
            except ValueError:
                continue
            rid = parts[0] if len(parts) > 1 else None
            if rid is not None and self._queued_request_id is not None and rid == self._queued_request_id:
                logger.info(
                    "Liquidsoap is already on the queued track (rid %s, %.1f s left) - "
                    "the hand-over has happened.", rid, value,
                )
                return 0.0
            return value if value >= 0 else None
        return None

    def _set_cross_mode(self, mode: str) -> None:
        """
        ``var.set rt_cross = <shape>`` and ``var.set rt_nofade = <side>`` -
        the shape of the next queue transition and which side is flagged
        "No Fade during Crossover".  ``mode`` is ``<shape>/<side>``; a
        bare shape means no flag.
        """
        shape, _, rest = mode.partition("/")
        nofade, _, overlap = rest.partition("/")
        # 2026-09-29: "<shape>/<side>/<seconds>" carries the overlap of this
        # transition (crossfade per track type / Exclude from Crossover);
        # without it the rendered house value applies (rt_dur = -1).
        try:
            seconds = float(overlap) if overlap else -1.0
        except ValueError:
            seconds = -1.0
        try:
            self._telnet.var_set("rt_cross", shape)
            self._telnet.var_set("rt_nofade", nofade or "-")
            self._telnet.var_set("rt_dur", f"{seconds:.2f}")
            self._cross_mode = mode
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap rt_cross=%s could not be set: %s", mode, exc)

    def stop(self) -> None:
        """
        Defer the skip-on-Liquidsoap by _DEFERRED_STOP_SECONDS so a
        subsequent play() within the window can either cancel it (same
        URI = catch-up idempotency, see :meth:`play`) or flush it (URI
        change = real track-transition).  If no play() arrives, a
        Timer thread flushes the skip eventually so DJ-takeover-style
        stops still take effect.

        No immediate hard-stop: the queue + crossfade operators handle
        gapless transitions natively and an aggressive skip-then-push
        produces an audible glitch (Phase-C8 reality-test 2026-05-26
        found this).
        """
        logger.info("Liquidsoap stop (deferred up to %.1fs)", _DEFERRED_STOP_SECONDS)
        # RASTATIME 2026-09-04 - drop PENDING requests right away, before
        # the deferred skip.  The deferred skip only affects the item on
        # air; requests queued while the scheduled branch was NOT on air
        # (line-in or webstream dominant) are never "played" and so never
        # skipped - they spill out later, all at once (11:00 incident:
        # four stale jingles at 11:07).  Flushing pending items cannot
        # touch the playing one, and in this scheduler there is never a
        # legitimately pending item at a stop (one push per event, at its
        # start), so this is a pure safety net.
        try:
            self._telnet.request_queue_flush()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap queue flush failed: %s", exc)
        self._queued_uri = None
        self._queued_request_id = None
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
        NO-OP that returns True immediately: the .liq pipeline has
        gapless transitions between ``request.queue`` items natively,
        so the scheduler does NOT need to delay its next-track event
        for a tail-flush (the deleted mpv engine needed a 500 ms wait
        here).
        """
        return True

    # ------------------------------------------------------------------
    # Phase C5 — Show recording (Liquidsoap-specific, NOT on the ABC)
    # ------------------------------------------------------------------
    #
    # The rastatime.liq template renders an ``output.file(id="recording",
    # …)`` block whose filename comes from a Liquidsoap interactive
    # variable ``recording_path``.  Pypo's _on_show_record_start /
    # _on_show_record_end hooks call these three wrappers.
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
    # call these two wrappers.
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

    def liquidsoap_uptime_seconds(self) -> Optional[float]:
        """
        Liquidsoap's process uptime in seconds, or ``None`` if the
        telnet is unreachable or the reply cannot be parsed.

        RASTATIME 2026-09-07 - the scheduler compares this across polls
        to detect that LIQUIDSOAP was restarted while PLAYOUT kept
        running (the operator's "PLAYOUT then LIQUIDSOAP" restart order
        leaves the fresh instance with the recording sentinel on).
        """
        try:
            reply = self._telnet.uptime()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Liquidsoap uptime telnet error: %s", exc)
            return None
        match = re.search(
            r"(\d+)\s*d\s+(\d+)\s*h\s+(\d+)\s*m\s+(\d+)\s*s", reply or "",
        )
        if not match:
            return None
        d, h, m, s = (int(g) for g in match.groups())
        return float(((d * 24 + h) * 60 + m) * 60 + s)

    def webstream_is_ready(self) -> bool:
        """
        Is the webstream source producing audio right now?

        RASTATIME 2026-09-06 - once polled by the scheduler's webstream
        watchdog (removed 2026-09-15); kept as a diagnostic.  Returns the
        Liquidsoap-side
        ``source.is_ready(webstream)`` (registered as ``webstream.ready``
        by the .liq template) as a bool.  On any telnet error we report
        ``True`` (fail-safe: an unreachable probe must not trigger a
        reconnect storm).
        """
        try:
            reply = self._telnet.webstream_ready()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Liquidsoap webstream_ready telnet error: %s", exc)
            return True
        return "true" in (reply or "").strip().lower()

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

    def linein_gate(self, open_: bool) -> None:
        """
        RASTATIME 2026-09-04 - open/close the line-in arm of the bus
        switch (``var.set linein_live``).  Closed, a connected + buffered
        line-in stays off air (pre-warm before the slot); flipping it
        open puts it on air on the next frame; flipping it closed at the
        slot end lets the switch fade it out under the successor while
        its buffered tail plays -- see the .liq bus block.
        """
        try:
            self._telnet.var_set("linein_live", "true" if open_ else "false")
            logger.info("Liquidsoap linein_gate: %s", "open" if open_ else "closed")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap linein_gate telnet error: %s", exc)

    def webstream_gate(self, open_: bool) -> None:
        """Same as :meth:`linein_gate` for the webstream arm."""
        try:
            self._telnet.var_set("webstream_live", "true" if open_ else "false")
            logger.info("Liquidsoap webstream_gate: %s", "open" if open_ else "closed")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap webstream_gate telnet error: %s", exc)

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
    # RASTATIME 2026-09-10 — DJ harbor kick (replaces the Icecast admin
    # killsource of the deleted mpv path)
    # ------------------------------------------------------------------

    _HARBOR_IDS = {"master": "master_dj", "show": "show_dj"}

    def dj_kick(self, source: str) -> None:
        """
        Disconnect the DJ client on the Master or Show harbor
        (``master_dj.stop`` / ``show_dj.stop``, registered by
        ``input.harbor``).  Idempotent: with nobody connected Liquidsoap
        replies "Done" as well.  The harbor's on_disconnect callback
        then reports the disconnect to PLAYOUT's /source-event, so the
        SourceSwitcher follows on its own.

        ``source`` is ``"master"`` or ``"show"``; anything else is a
        programming error (ValueError).  Telnet errors are logged and
        swallowed - the kick is best-effort, same as the other wrappers.
        """
        harbor_id = self._HARBOR_IDS.get(source)
        if harbor_id is None:
            raise ValueError(f"unknown DJ source {source!r} (master|show)")
        try:
            resp = self._telnet.harbor_stop(harbor_id)
            logger.info("Liquidsoap %s.stop -> %s", harbor_id, (resp or "").strip() or "<empty>")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap %s.stop telnet error: %s", harbor_id, exc)

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-13 — ICY metadata (Settings -> Streams)
    # ------------------------------------------------------------------

    def icy_settings(self, label_format: int, offair_text: str, station_name: str) -> None:
        """
        Push the Stream Label variant, the Off Air Metadata text and the
        station name into the running script (``icy_format``,
        ``offair_text``, ``station_name`` interactive variables).  The
        scheduler calls this only when a value changed.  Fail-soft.
        """
        try:
            self._telnet.var_set_int("icy_format", int(label_format))
            self._telnet.var_set_string("offair_text", offair_text)
            self._telnet.var_set_string("station_name", station_name)
            logger.info(
                "Liquidsoap ICY settings: format=%d offair=%r station=%r",
                int(label_format), offair_text, station_name,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap ICY settings telnet error: %s", exc)

    def live_text_settings(self, enabled: bool, label_format: int) -> None:
        """RASTATIME 2026-09-28 - Live Text Info switch + format (``livetext_*``)."""
        try:
            self._telnet.var_set("livetext_enabled", "true" if enabled else "false")
            self._telnet.var_set_int("livetext_format", int(label_format))
            logger.info("Liquidsoap Live Text: enabled=%s format=%d", enabled, int(label_format))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap Live Text settings telnet error: %s", exc)

    def bus_show_set(self, show_name: str) -> None:
        """
        Tell the script which show is on air (``bus_show``): the ICY
        title of sources without a show_name of their own (DJ harbors,
        webstreams, line-in) is built from it.  Empty = no show.
        """
        try:
            self._telnet.var_set_string("bus_show", show_name or "")
            logger.info("Liquidsoap bus_show: %r", show_name or "")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Liquidsoap bus_show telnet error: %s", exc)

    def icy_status(self) -> str:
        """The ICY settings the script reports (diagnostics)."""
        return self._telnet.icy_status()

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
            'annotate:liq_cue_in="0.50",liq_cue_out="180.00",replaygain_track_gain="-5.95 dB",title="Song",artist="Band":file:///x.mp3'
        """
        normalised = cls._normalise_uri(uri)

        annotations = []
        # RASTATIME 2026-09-27 - Liquidsoap 2.4 applies cue points during
        # request resolution from the metadata ``liq_cue_in`` /
        # ``liq_cue_out`` (cue_cut is deprecated).  The LibreTime names
        # ``cue_in`` / ``cue_out`` used until today were ignored: every
        # track played from 0 to its end (found in the crossfade
        # rehearsal: a track whose cue_out the API had clipped to the
        # show end ran 45 s into the next show).
        if cue_in and cue_in > 0:
            annotations.append(f'liq_cue_in="{cue_in:.2f}"')
        if cue_out is not None and cue_out > 0:
            annotations.append(f'liq_cue_out="{cue_out:.2f}"')
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

        Keeps log lines free of credentials (the deleted mpv engine
        had the same helper).
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
