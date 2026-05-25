"""
LiquidsoapPlayoutEngine — Liquidsoap adapter for RASTATIME.

RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase B (skeleton).

Drop-in replacement for :class:`MpvPlayoutEngine` and
:class:`VlcPlayoutEngine` (ADR-002).  Talks to a Liquidsoap
subprocess via the telnet line-protocol server on
``localhost:1234`` (see :mod:`liquidsoap_telnet`).

Architectural shift vs. mpv/VLC engines
---------------------------------------

The mpv and VLC engines own the audio output themselves — when
``play(uri)`` is called, mpv/VLC starts decoding and pushing to
the OS audio device, and the Pypo scheduler then spawns three
parallel FfmpegStreamer subprocesses that re-read the same file
and push it to Icecast.

The Liquidsoap engine inverts the relationship.  Liquidsoap is a
long-running subprocess that holds:

  * A request.queue source that we push file URIs into
  * The Master/Show DJ input.harbor sources
  * A switch(...) that picks the active source
  * Three output.icecast blocks (mp3 / aac / ogg) with a single
    persistent Icecast PUT per mount

When the scheduler wants to "play file X", it calls
:meth:`play` which sends ``request.queue.push file:///X`` over
telnet to Liquidsoap.  Liquidsoap then decodes + encodes + ships
the audio entirely by itself — no separate FfmpegStreamer
subprocesses.

This eliminates the entire FFmpeg-streamer lifecycle that lives
in ``playout_scheduler.py::_start_streamers / _stop_streamers``;
in the Liquidsoap world those methods become no-ops.

PHASE-B STATE: skeleton.  All methods are stubs with TODO
comments pointing at Phase C work.  Instantiating this class is
deliberately allowed (so the env-var dispatch in __main__.py can
import and try to instantiate) — the stub methods raise
NotImplementedError so any accidental invocation in production
is loud, not silent.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from .interface import PlayoutEngine, PlayoutState
from .liquidsoap_telnet import LiquidsoapTelnetClient

logger = logging.getLogger(__name__)


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
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
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
        import os  # local import to avoid module-level os dep
        self._telnet = LiquidsoapTelnetClient(
            host = host or os.environ.get("RASTATIME_LIQUIDSOAP_HOST", "127.0.0.1"),
            port = port or int(os.environ.get("RASTATIME_LIQUIDSOAP_PORT", "1234")),
        )

        logger.info(
            "LiquidsoapPlayoutEngine skeleton initialised (telnet target %s:%d)",
            self._telnet._host, self._telnet._port,
        )

    # ------------------------------------------------------------------
    # PlayoutEngine interface — Phase B skeletons
    # ------------------------------------------------------------------

    def play(
        self,
        uri: str,
        *,
        cue_in: float = 0.0,
        cue_out: Optional[float] = None,
        media_options: Optional[List[str]] = None,
        gain_db: Optional[float] = None,
    ) -> None:
        """
        Push ``uri`` onto Liquidsoap's request queue.  Optional cue
        points are encoded as annotate-protocol attributes
        (``annotate:cue_in=…,cue_out=…:file:///…``).  Replay-gain is
        either applied via the ``replaygain`` protocol or set as a
        per-track Liquidsoap variable that the .liq script picks up.

        TODO Phase C:
          * URI normalisation (Windows paths need ``file:///C:/…``)
          * annotate-protocol wrap for cue_in / cue_out
          * gain_db handling (var.set vs. annotate)
          * media_options ignored (Liquidsoap handles HTTP auth via
            URI userinfo, same as mpv/ffmpeg)
        """
        raise NotImplementedError(
            "LiquidsoapPlayoutEngine.play — Phase C target"
        )

    def stop(self) -> None:
        """
        Skip whatever Liquidsoap is currently playing — that drops
        back to the request.queue silence-on-empty default, which
        in our .liq script is wired to ``blank()`` (silence) so the
        Icecast PUT stays connected but quiet.

        TODO Phase C — implement via ``request.queue.skip``.
        """
        raise NotImplementedError(
            "LiquidsoapPlayoutEngine.stop — Phase C target"
        )

    def get_state(self) -> PlayoutState:
        """
        Return cached state.  Liquidsoap's telnet ``request.queue.queue``
        could be polled to refresh this, but Pypo only checks state
        in the next-track-handler hot path so caching is fine.

        TODO Phase C — optionally pull live status before returning,
        bounded by a short telnet timeout.
        """
        return self._state

    def close(self) -> None:
        """
        Close the telnet connection.  Does NOT terminate the
        Liquidsoap subprocess — that's NSSM's job.

        TODO Phase C — call self._telnet.close() once that is
        implemented.
        """
        logger.info("LiquidsoapPlayoutEngine.close — skeleton no-op")

    def set_audio_device(self, device_id: Optional[str]) -> None:
        """
        Liquidsoap's local-monitoring output is configured in the
        .liq script (``output.ao`` / ``output.portaudio`` / etc.).
        Live device switching would need a server-command-driven
        re-wiring inside the script — not in Phase B scope.

        For Phase B / C we just log + warn, same fallback that the
        PlayoutEngine ABC does by default.  Phase D may add a
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
        the .liq pipeline already has gapless transitions between
        request.queue items natively, so the scheduler does NOT need
        to delay its next-track event for a tail-flush.  That's
        actually one of the selling points of moving to Liquidsoap —
        the 500 ms wait hack we have in the mpv path goes away.
        """
        return True
