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
from typing import Dict, List, Optional

from .interface import PlayoutEngine, PlayoutState
from .liquidsoap_telnet import LiquidsoapTelnetClient

logger = logging.getLogger(__name__)


# Regex used by _normalise_uri — matches both ``C:\foo`` and ``C:/foo``
# at the very start of the URI argument, so we can detect a Windows
# drive-letter path that needs ``file:///`` wrapping.
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


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
        Skip whatever Liquidsoap is currently playing — that drops
        back to the request.queue silence-on-empty default, which
        in our .liq script is wired to a silent ``blank()`` fallback
        so the Icecast PUT stays connected but quiet.

        Idempotent: calling on an already-empty queue is harmless
        (Liquidsoap replies "Done" or similar).
        """
        logger.info("Liquidsoap stop")
        try:
            self._telnet.request_queue_skip()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Stop on an already-stopped/disconnected client should not
            # crash the scheduler.  Demote to warning — losing the skip
            # only means the current track plays to its natural end,
            # which is annoying but not catastrophic.
            logger.warning("Liquidsoap stop telnet error: %s", exc)
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
        """
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
        ``file:///`` URI form.  HTTP URIs and already-prefixed
        ``file://`` URIs pass through unchanged.

        Liquidsoap's request-protocol parser wants forward slashes
        even on Windows, and it expects exactly the
        ``file:///<drive>:/<path>`` shape — the three-slash variant
        is what RFC 8089 / Mozilla document for Windows file URIs.
        Two-slash variants work in some tools but Liquidsoap rejects
        them.

        Examples::

            >>> _normalise_uri("C:\\\\rastatime\\\\580.mp3")
            'file:///C:/rastatime/580.mp3'
            >>> _normalise_uri("C:/rastatime/580.mp3")
            'file:///C:/rastatime/580.mp3'
            >>> _normalise_uri("file:///C:/rastatime/580.mp3")
            'file:///C:/rastatime/580.mp3'
            >>> _normalise_uri("http://example.com/stream.mp3")
            'http://example.com/stream.mp3'
        """
        # Bare Windows drive-letter path (back- or forward-slash).
        if _WINDOWS_DRIVE_RE.match(uri):
            forward = uri.replace("\\", "/")
            return f"file:///{forward}"
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
