"""
VlcPlayoutEngine — libVLC adapter for RASTATIME (ADR-002, T5.1–T5.4).

Uses python-vlc to play scheduled audio files and HTTP streams on the
**local audio device only**.  Icecast streaming is handled separately by
``FfmpegStreamer`` (see ``ffmpeg_streamer.py``).

Notes
-----
- ``--no-video`` prevents spurious VLC GUI windows on Windows.
- ``--intf dummy`` keeps VLC fully headless.
"""
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .interface import PlayoutEngine, PlayoutState

logger = logging.getLogger(__name__)


class VlcPlayoutEngine(PlayoutEngine):
    """
    libVLC-backed playout engine (ADR-002).

    Thread-safety: ``play()`` and ``stop()`` may be called from different
    threads (the main loop and threading.Timer callbacks).  The python-vlc
    C-extension is thread-safe for the operations used here.
    """

    def __init__(
        self,
        extra_vlc_args: Optional[List[str]] = None,
    ) -> None:
        """
        Initialise the VLC instance and media player.

        VLC handles **local audio playback only**.  Icecast streaming is
        handled by ``FfmpegStreamer`` (started by the scheduler alongside
        each VLC play command).
        """
        # ----------------------------------------------------------
        # Resolve VLC paths BEFORE importing python-vlc.
        # VLC's internal plugin loader needs the VLC root directory
        # on PATH to resolve transitive DLL dependencies of plugins
        # such as libaccess_output_shout_plugin.dll (depends on
        # libshout, libvorbis, libogg, etc.).
        # ----------------------------------------------------------
        vlc_plugin_path = os.environ.get("RASTATIME_VLC_PLUGIN_PATH", "")
        if vlc_plugin_path:
            os.environ.setdefault("VLC_PLUGIN_PATH", vlc_plugin_path)
            vlc_root = str(Path(vlc_plugin_path).parent)
        else:
            vlc_root = r"C:\Program Files\VideoLAN\VLC"

        # Add VLC root to process PATH so VLC's own DLL loader finds
        # plugin dependencies (libshout.dll, libvorbis.dll, etc.)
        current_path = os.environ.get("PATH", "")
        if vlc_root.lower() not in current_path.lower():
            os.environ["PATH"] = vlc_root + os.pathsep + current_path
            logger.info("Added VLC root to PATH: %s", vlc_root)

        # Also register via os.add_dll_directory() (Python 3.8+ / Windows)
        # for any ctypes-based DLL loading.
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            try:
                if Path(vlc_root).is_dir():
                    os.add_dll_directory(vlc_root)
                    logger.debug("os.add_dll_directory(%s)", vlc_root)
            except OSError as e:
                logger.debug("os.add_dll_directory failed: %s", e)

        try:
            import vlc  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "python-vlc is not installed or libvlc.dll is missing.\n"
                "Install VLC (64-bit) from https://www.videolan.org/vlc/ and\n"
                "ensure the VLC directory is on PATH (or set VLC_PLUGIN_PATH)."
            ) from exc

        self._vlc = vlc
        self._state = PlayoutState.STOPPED
        self._current_uri: Optional[str] = None

        # Verbosity is configurable via env var so the operator can flip
        # libVLC into debug mode for one restart cycle (to investigate
        # HTTP-auth issues against /main, /show, etc.) and back, without
        # editing code.
        #
        #   0 = errors only
        #   1 = + warnings + module info (default)
        #   2 = + debug (LOUD — flood expected in playout-stderr.log)
        #   3 = + extra debug
        #
        # Set in NSSM:
        #     nssm set rastatime-playout AppEnvironmentExtra RASTATIME_VLC_VERBOSE=2
        #     nssm restart rastatime-playout
        # Reset by deleting the env var (or setting it to "1") and restarting.
        try:
            verbose_level = int(os.environ.get("RASTATIME_VLC_VERBOSE", "1"))
            verbose_level = max(0, min(3, verbose_level))
        except (TypeError, ValueError):
            verbose_level = 1

        if verbose_level >= 2:
            logger.warning(
                "RASTATIME_VLC_VERBOSE=%d — libVLC will emit debug-level "
                "logs to stderr (playout-stderr.log).  Don't leave this "
                "on in production; reset to 1 when done diagnosing.",
                verbose_level,
            )

        args: List[str] = [
            "--no-video",                       # no video output window
            "--intf", "dummy",                  # fully headless interface
            "--no-osd",                         # no on-screen display
            "--verbose", str(verbose_level),
        ]
        args.extend(extra_vlc_args or [])

        logger.info("Initialising VLC instance with args: %s", args)
        self._instance = vlc.Instance(*args)
        if self._instance is None:
            raise RuntimeError("vlc.Instance() returned None — check libvlc.dll")

        self._player = self._instance.media_player_new()
        if self._player is None:
            raise RuntimeError("media_player_new() returned None")

        # Attach end-of-media and error event handlers
        em = self._player.event_manager()
        em.event_attach(
            vlc.EventType.MediaPlayerEndReached,
            self._on_end_reached,
        )
        em.event_attach(
            vlc.EventType.MediaPlayerEncounteredError,
            self._on_error,
        )

        logger.info(
            "VLC playout engine ready (local-only, python-vlc %s)",
            vlc.__version__,
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
        Start playing a URI.

        ``metadata`` is accepted for ``PlayoutEngine`` interface
        compatibility with the Liquidsoap engine but ignored by VLC:
        like mpv, this adapter is local-playback-only — Icecast
        metadata is set separately by FfmpegStreamer ``-metadata``
        flags when the streamer subprocess is spawned alongside the
        local playback.

        Cue-in: if ``cue_in > 0``, waits for VLC to start decoding (up to 3 s)
        and then seeks to the specified position.

        Note: ``cue_out`` is not yet enforced by the engine itself — the
        PlayoutScheduler arms a stop timer at the scheduled end time (which
        usually corresponds to the logical cue-out within the show slot).
        See QUEUE_BEHAVIOR.md §6.1.

        ``media_options`` are libVLC per-media options applied via
        ``media.add_option()`` — typically used for HTTP auth on live
        sources (``:http-user=…``, ``:http-pwd=…``) and to shorten the
        ``:network-caching`` for low-latency DJ relays.  Each entry
        must already include the leading colon.

        ``gain_db`` is accepted for ``PlayoutEngine`` interface
        compatibility but **not applied** by this VLC implementation
        (libVLC has its own replaygain machinery via
        ``--audio-replay-gain-mode=track`` which would conflict with a
        scheduler-passed precomputed dB).  RASTATIME's active engine
        since ADR-002 is :class:`MpvPlayoutEngine`, which does honour
        the parameter; this VLC adapter is kept only for the historical
        libVLC build and tests.

        (Was ``replay_gain_db`` before 2026-05-16; renamed when the
        same parameter started carrying non-ReplayGain values too,
        e.g. cc_webstream.input_gain_db.)
        """
        logger.info(
            "VLC play: uri=%s cue_in=%.2fs cue_out=%s media_options=%s",
            uri, cue_in, cue_out,
            # Don't dump literal passwords into the log
            [
                opt if not opt.startswith(":http-pwd=") else ":http-pwd=***"
                for opt in (media_options or [])
            ],
        )
        self._current_uri = uri
        media = self._instance.media_new(uri)
        if media is None:
            logger.error("VLC: media_new() failed for %s", uri)
            self._state = PlayoutState.ERROR
            return

        # Per-media options (HTTP auth, network-caching, ...) must be
        # applied BEFORE the player picks up the media — VLC doesn't
        # re-read them after parsing has started.
        for opt in (media_options or []):
            try:
                media.add_option(opt)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("VLC: add_option(%s) failed: %s", opt, exc)

        self._player.set_media(media)
        ret = self._player.play()
        if ret == -1:
            logger.error("VLC: player.play() returned -1 for %s", uri)
            self._state = PlayoutState.ERROR
            return

        self._state = PlayoutState.PLAYING

        # Seek to cue_in if requested
        if cue_in > 0.0:
            self._wait_playing_then_seek(int(cue_in * 1000))

    def stop(self) -> None:
        """Hard-stop playback immediately."""
        logger.info("VLC stop")
        self._player.stop()
        self._state = PlayoutState.STOPPED
        self._current_uri = None

    def get_state(self) -> PlayoutState:
        return self._state

    def close(self) -> None:
        """Release all VLC resources."""
        try:
            self._player.stop()
            self._player.release()
            self._instance.release()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        logger.info("VLC playout engine closed")

    # ------------------------------------------------------------------
    # VLC event callbacks (called from the VLC internal event thread)
    # ------------------------------------------------------------------

    def _on_end_reached(self, event) -> None:
        logger.info("VLC: end of media reached (%s)", self._current_uri)
        self._state = PlayoutState.STOPPED
        self._current_uri = None

    def _on_error(self, event) -> None:
        logger.error("VLC: playback error encountered (%s)", self._current_uri)
        self._state = PlayoutState.ERROR
        self._current_uri = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_playing_then_seek(self, position_ms: int) -> None:
        """Wait for VLC to enter Playing state, then seek to position_ms."""
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            vlc_state = self._player.get_state()
            if vlc_state in (
                self._vlc.State.Playing,
                self._vlc.State.Paused,
            ):
                self._player.set_time(position_ms)
                logger.debug("VLC: seeked to %dms", position_ms)
                return
            time.sleep(0.05)
        logger.warning(
            "VLC: timed out waiting for Playing state to seek to %dms",
            position_ms,
        )
