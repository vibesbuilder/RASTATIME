"""
MpvPlayoutEngine — libmpv adapter for RASTATIME.

Drop-in replacement for ``VlcPlayoutEngine`` (ADR-002).  Uses libmpv via
``python-mpv`` to play scheduled audio files and HTTP streams on the
**local audio device only**.  Icecast streaming is handled separately by
``FfmpegStreamer`` — same architecture as the VLC engine.

Why mpv instead of libVLC 3.x:
  libVLC 3.x on Windows trips over Icecast's ``icy-*`` reply headers
  when reading a URL-auth-gated mount such as ``/main`` or ``/show``:
  it falls back to its internal ``icyx://`` retry, drops the
  ``Authorization`` header in the process, gets 401 from the PHP
  listener-auth endpoint, and ends up emitting ``playback error
  encountered`` while staying silent.  mpv's HTTP/Icecast handling
  doesn't have this quirk — DJ-source monitoring works directly off
  ``/main`` and ``/show``, with sub-second latency.
"""
import logging
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

from .interface import PlayoutEngine, PlayoutState

logger = logging.getLogger(__name__)

# Default install locations searched for ``libmpv-2.dll`` (Windows).
# Override via the RASTATIME_MPV_PATH environment variable, which takes
# precedence over both.  Matches the FfmpegStreamer search pattern.
_MPV_PATH_DEFAULTS = [
    r"C:\Tools\mpv",
    r"C:\Program Files\mpv",
]


# mpv log-level → Python log-level translation.  ``status`` is mpv's
# normal playback progress chatter; we route it through DEBUG so it
# only shows when the operator explicitly asks for verbose output.
_MPV_TO_PYTHON_LEVEL = {
    "fatal": logging.CRITICAL,
    "error": logging.ERROR,
    "warn":  logging.WARNING,
    "info":  logging.INFO,
    "status": logging.DEBUG,
    "v":     logging.DEBUG,
    "debug": logging.DEBUG,
    "trace": logging.DEBUG,
}


def _bridge_mpv_log_to_python(loglevel, component, message) -> None:
    """
    libmpv ``log_handler`` callback — forwards each internal mpv log
    line into Python's standard logging machinery.

    Critical for diagnosing playback issues on Windows: ``terminal=False``
    silences mpv's stderr output completely, so without this bridge the
    operator would see only RASTATIME's own log lines and have no
    visibility into mpv's audio-output module, codec probes, cache
    underruns, ICY-metadata handling, etc.
    """
    try:
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="replace")
        if isinstance(loglevel, bytes):
            loglevel = loglevel.decode("ascii", errors="replace")
        if isinstance(component, bytes):
            component = component.decode("ascii", errors="replace")
        py_level = _MPV_TO_PYTHON_LEVEL.get(str(loglevel).lower(), logging.INFO)
        logger.log(py_level, "mpv[%s/%s] %s", component, loglevel, str(message).strip())
    except Exception:  # pylint: disable=broad-exception-caught
        # A logging bridge MUST NEVER raise — that would propagate out of
        # mpv's C callback and almost certainly crash the playout process.
        pass


def _redact_kwargs_for_log(kwargs: dict) -> dict:
    """Keep the callable out of the constructor-kwargs log line."""
    return {
        k: ("<callable>" if callable(v) else v)
        for k, v in kwargs.items()
    }


def _resolve_mpv_dll_dir() -> Optional[str]:
    """
    Return the directory containing ``libmpv-2.dll``, or None if it
    cannot be located.  Used to prepend the DLL location to %PATH%
    BEFORE ``import mpv`` — python-mpv scans %PATH% at import time
    rather than using ``os.add_dll_directory``.
    """
    env_path = os.environ.get("RASTATIME_MPV_PATH", "")
    if env_path and (Path(env_path) / "libmpv-2.dll").is_file():
        return env_path
    for candidate in _MPV_PATH_DEFAULTS:
        if (Path(candidate) / "libmpv-2.dll").is_file():
            return candidate
    return None


class MpvPlayoutEngine(PlayoutEngine):
    """
    libmpv-backed playout engine — same contract as ``VlcPlayoutEngine``.

    Thread-safety: ``play()`` and ``stop()`` may be called from different
    threads (main loop + threading.Timer callbacks).  python-mpv
    serialises commands internally via a single client thread, so
    concurrent calls from Python are safe.
    """

    def __init__(self, extra_mpv_kwargs: Optional[dict] = None) -> None:
        # ----------------------------------------------------------
        # Resolve libmpv DLL path and prepend it to %PATH% BEFORE
        # ``import mpv``.  python-mpv (1.0.x) probes %PATH% at module
        # import time and raises OSError if neither ``mpv-1.dll``,
        # ``mpv-2.dll`` nor ``libmpv-2.dll`` is found there — even if
        # we later call ``os.add_dll_directory``.  So we must set
        # PATH first, then import.
        # ----------------------------------------------------------
        mpv_dir = _resolve_mpv_dll_dir()
        if mpv_dir is None:
            raise RuntimeError(
                "libmpv-2.dll not found.  Set RASTATIME_MPV_PATH to the "
                "directory containing the DLL, or install mpv to one of "
                "the default locations: "
                + ", ".join(_MPV_PATH_DEFAULTS)
            )

        current_path = os.environ.get("PATH", "")
        if mpv_dir.lower() not in current_path.lower():
            os.environ["PATH"] = mpv_dir + os.pathsep + current_path
            logger.info("Added mpv root to PATH: %s", mpv_dir)

        # Belt-and-braces: also register via os.add_dll_directory() for
        # any ctypes-based DLL loading that respects the newer API.
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            try:
                if Path(mpv_dir).is_dir():
                    os.add_dll_directory(mpv_dir)
                    logger.debug("os.add_dll_directory(%s)", mpv_dir)
            except OSError as exc:
                logger.debug("os.add_dll_directory failed: %s", exc)

        try:
            import mpv  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "python-mpv is not installed.\n"
                "Install it into the playout venv:\n"
                "  C:\\rastatime\\.venv\\Scripts\\pip.exe install python-mpv"
            ) from exc
        except OSError as exc:
            # python-mpv raises OSError at import time if it can't find
            # the DLL — surface a clearer message.
            raise RuntimeError(
                f"python-mpv import failed: {exc}.  Check that "
                f"libmpv-2.dll exists in {mpv_dir} and is the correct "
                f"architecture (x86_64)."
            ) from exc

        self._mpv = mpv
        self._state = PlayoutState.STOPPED
        self._current_uri: Optional[str] = None

        # RASTATIME 2026-05-25 (Seamless-Bus-Mix Phase 1) — threading
        # Event used by wait_until_stopped() so the scheduler can pause
        # briefly at next-track time until mpv has flushed the current
        # file's last frames.  Without this, short tracks (4–10 s) got
        # their tail 1–2 s cut off because _on_*_start(N+1) hard-stopped
        # mpv (and the FFmpeg streamers) while audio was still in the
        # decode pipeline.  Initial state is "stopped".
        self._stopped_event = threading.Event()
        self._stopped_event.set()

        # Log verbosity is configurable via env var so the operator can
        # flip libmpv into debug mode for one restart cycle without
        # editing code.  Accepts mpv's standard levels:
        #   no, fatal, error, warn (default), info, status, v, debug, trace
        log_level = os.environ.get("RASTATIME_MPV_LOG_LEVEL", "warn").lower()

        # Headless audio playback.  Each option mirrors something we
        # had to set explicitly for libVLC:
        #   - video='no'                — no video output (analogous to --no-video)
        #   - audio_display='no'        — no album-art pseudo-video window
        #   - input_default_bindings    — don't grab keyboard/mouse
        #   - terminal=False            — no TTY interaction (NSSM service)
        #   - ytdl=False                — skip youtube-dl resolution for plain HTTP
        #   - cache=yes                 — enable the stream cache
        #   - cache_secs=0.5            — 0.5 s of live-input buffer.
        #                                 The Icecast server runs on the
        #                                 same machine (localhost), so
        #                                 jitter is negligible — anything
        #                                 above ~300 ms is wasted latency.
        #                                 Combined with the per-mount
        #                                 burst-size=0 on /linein-capture
        #                                 (see infra icecast.xml), this
        #                                 brings the operator's local
        #                                 monitor latency from ~3.5 s
        #                                 (legacy default) to roughly
        #                                 0.5-0.8 s.  Public listeners
        #                                 are unaffected — they tune
        #                                 into /rastatime192 etc., which
        #                                 keep the generous default
        #                                 burst-on-connect.
        #   - demuxer_readahead_secs=0.3 — 0.3 s of decoded audio queued
        #                                 ahead of the playback head.
        #                                 Just enough to ride through a
        #                                 single mp3-frame decode without
        #                                 starving the WASAPI sink.
        #   - cache_on_disk=no          — keep the cache in memory; this is
        #                                 always a live stream of at most a
        #                                 few MB, no need to thrash the SSD.
        #   - network_timeout=10        — fail HTTP connect attempts after 10s
        #                                 instead of hanging the worker thread
        mpv_kwargs = dict(
            ytdl=False,
            video="no",
            audio_display="no",
            input_default_bindings=False,
            input_vo_keyboard=False,
            terminal=False,
            cache="yes",
            cache_secs=0.5,
            demuxer_readahead_secs=0.3,
            cache_on_disk="no",
            network_timeout=10,
            # libavformat-level HTTP retry — passed to mpv's internal
            # FFmpeg demuxer as input options.  Same rationale as the
            # FfmpegStreamer config: when the playout switches to /main
            # or /show right after a DJ source connect, Icecast may
            # answer the first listener GETs with 404 for ~1-3 s while
            # the mount finishes opening.  Without these, mpv would
            # treat the 404 as fatal and log
            # "Stream ends prematurely at 0, should be …" — the exact
            # pattern from the 17:42 / 18:13 logs.  (RASTATIME 2026-05-13)
            stream_lavf_o=(
                "reconnect=1,"
                "reconnect_streamed=1,"
                # ``4xx`` (without 5xx) — mpv's stream-lavf-o uses comma
                # as the key-separator, so a literal "4xx,5xx" value
                # would be mis-parsed.  4xx alone covers the 404 case
                # we actually need; 5xx is rare for a localhost Icecast.
                "reconnect_on_http_error=4xx,"
                "reconnect_on_network_error=1,"
                "reconnect_delay_max=10"
            ),
            # Audio-output ring buffer between mpv's decoder thread and
            # the WASAPI sink.  Default 0.2 s isn't enough on Windows —
            # the WASAPI Shared-Mode mixer occasionally stalls the
            # output thread for ~300-400 ms when other Windows audio
            # clients open/close, and that drains the ring dry,
            # producing the "Audio device underrun detected" warnings
            # we saw every ~60 s during live-stream playback.  0.5 s
            # gives the decoder enough headroom to ride through those
            # stalls without an underrun pop.
            audio_buffer=0.5,
        )
        if extra_mpv_kwargs:
            mpv_kwargs.update(extra_mpv_kwargs)

        # Bridge mpv's internal logs into Python's logging.  Without
        # this, mpv emits nothing — ``terminal=False`` disables stderr
        # output, and the only escape hatch is the C-callback that
        # python-mpv exposes via ``log_handler=`` on the constructor.
        # The result: mpv WARNINGS/INFO show up in playout-stdout.log
        # under the logger name ``libretime_playout.engine.mpv_engine``,
        # right next to our own engine logs.
        mpv_kwargs["log_handler"] = _bridge_mpv_log_to_python
        mpv_kwargs["loglevel"] = log_level

        logger.info("Initialising mpv instance: %s", _redact_kwargs_for_log(mpv_kwargs))
        self._player = mpv.MPV(**mpv_kwargs)

        # Track playback state via end-file events.  reasons emitted by
        # libmpv: 'eof', 'stop', 'quit', 'error', 'redirect', 'unknown'.
        # Only 'error' should flip us into the ERROR state — the others
        # are all expected outcomes (natural end, our own stop, etc.).
        @self._player.event_callback("end-file")
        def _on_end_file(event):  # noqa: ANN001 — python-mpv event obj
            reason = self._extract_end_file_reason(event)
            uri = self._current_uri
            if reason == "error":
                logger.error("mpv end-file: error on %s", self._redact(uri))
                self._state = PlayoutState.ERROR
            else:
                logger.info("mpv end-file: reason=%s uri=%s", reason, self._redact(uri))
                self._state = PlayoutState.STOPPED
            self._current_uri = None
            # Wake any thread waiting in wait_until_stopped().
            self._stopped_event.set()

        logger.info(
            "mpv playout engine ready (libmpv %s, python-mpv %s)",
            self._player.mpv_version,
            getattr(mpv, "__version__", "?"),
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
    ) -> None:
        """
        Start playing a URI on the local soundcard.

        ``cue_in`` is passed as the ``start=`` option to libmpv's
        ``loadfile`` command, which performs the seek before playback
        begins.  This is cleaner than libVLC's "play then seek after
        decode start" dance and gives gap-less catch-up.

        ``cue_out`` is ignored at the engine layer — the scheduler
        arms a separate stop timer at the scheduled end time, same
        as for the VLC engine.

        ``media_options`` is accepted for interface compatibility with
        ``VlcPlayoutEngine`` but ignored by mpv — HTTP auth is taken
        from the URI's userinfo, and caching is configured globally on
        the player instance.

        RASTATIME 2026-05-16 — ``gain_db`` is a generic per-event dB
        offset applied as an FFmpeg ``volume`` audio filter.  The
        scheduler computes the value differently per event type:

          * File events: precomputed ReplayGain sum.
          * Webstream events: ``cc_webstream.input_gain_db``.
          * Live sources (Master/Show, Linein): currently ``None``.

        ``None`` or 0.0 ⇒ no audio filter, mpv passes audio through
        unchanged.  Non-zero ⇒ a one-element ``volume=<dB>dB`` audio
        filter is installed via the ``af`` property; on subsequent
        ``play()`` calls without a gain value the filter is cleared so
        live sources don't inherit a previous track's gain.

        (Was ``replay_gain_db`` before 2026-05-16; renamed to reflect
        that the same mechanism now carries non-ReplayGain values.)
        """
        logger.info(
            "mpv play: uri=%s cue_in=%.2fs cue_out=%s gain=%s",
            self._redact(uri), cue_in, cue_out,
            f"{gain_db:+.2f}dB" if gain_db else "none",
        )
        self._current_uri = uri
        try:
            # mpv's ``start`` property is read at loadfile time and
            # tells the demuxer where to begin decoding.  We set it
            # before loadfile, then reset to ``none`` so a subsequent
            # play() without cue_in doesn't inherit the previous seek.
            #
            # Why this instead of ``loadfile … start=N`` as an option:
            # mpv >= 0.39 changed loadfile's argument grammar to
            #   ``loadfile <url> [<flags> [<index> [<options>]]]``
            # — i.e. an extra ``<index>`` slot before the options.
            # python-mpv 1.0.8 still emits the old 4-arg form, so the
            # option string ends up in the index slot and mpv replies
            # with MPV_ERROR_INVALID_PARAMETER (-4).  Setting the
            # property directly side-steps the grammar change entirely.
            if cue_in and cue_in > 0:
                self._player["start"] = cue_in
            else:
                self._player["start"] = "none"

            # RASTATIME 2026-05-16 — install / clear generic volume
            # filter.  The ``af`` property accepts mpv's filter-graph
            # syntax: an empty string clears any previous filter, and
            # ``lavfi=[volume=<dB>dB]`` wraps FFmpeg's volume filter
            # (same filter the streamers use, identical semantics).
            # We always set the property — either to a fresh filter
            # or to "" — so a previous event's gain doesn't leak into
            # the current play() call.
            if gain_db is not None and abs(gain_db) > 0.001:
                self._player["af"] = (
                    f"lavfi=[volume={gain_db:+.2f}dB]"
                )
            else:
                self._player["af"] = ""

            # Cleared just before loadfile so wait_until_stopped() blocks
            # until the matching end-file event sets it again.
            self._stopped_event.clear()
            self._player.command("loadfile", uri, "replace")
            self._state = PlayoutState.PLAYING
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("mpv play failed for %s: %s", self._redact(uri), exc)
            self._state = PlayoutState.ERROR
            # Failed play counts as "not playing" for waiters.
            self._stopped_event.set()

    def stop(self) -> None:
        """Hard-stop playback immediately."""
        logger.info("mpv stop")
        try:
            self._player.command("stop")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Stop on an already-stopped player is harmless but noisy;
            # demote to debug.
            logger.debug("mpv stop (already stopped?): %s", exc)
        self._state = PlayoutState.STOPPED
        self._current_uri = None
        self._stopped_event.set()

    def wait_until_stopped(self, timeout: float) -> bool:
        """
        Block up to ``timeout`` seconds waiting for the engine to enter
        STOPPED state (natural end-of-file, error, or an explicit
        :meth:`stop`).  Returns ``True`` if stopped within the timeout,
        ``False`` otherwise.

        Used by the playout scheduler at next-track time to let mpv
        flush the current file's last frames before hard-stopping the
        engine + the parallel FFmpeg streamers — without this, short
        tracks (4–10 s) get their tail 1–2 s clipped because the
        scheduler-clock fires the next event slightly before the
        in-flight audio has drained.  RASTATIME 2026-05-25 — Seamless-
        Bus-Mix Phase 1.
        """
        return self._stopped_event.wait(timeout=timeout)

    def get_state(self) -> PlayoutState:
        return self._state

    def close(self) -> None:
        """Release all libmpv resources."""
        try:
            self._player.terminate()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        logger.info("mpv playout engine closed")

    def set_audio_device(self, device_id: Optional[str]) -> None:
        """
        Switch the WASAPI output device to ``device_id`` at runtime.

        ``device_id`` is a RASTATIME *stable ID* — the normalised Windows
        audio endpoint GUID without braces, e.g.
        ``"6ab7e89f-eb4d-4641-a145-fb561fd0f902"``.  We wrap that into
        libmpv's expected ``wasapi/{<GUID>}`` syntax before setting it.

        Passing ``None`` or an empty string falls back to mpv's
        ``auto`` device, i.e. the OS-default audio endpoint.

        Errors (e.g. device disappeared while we were trying to set
        it) are caught and logged — the player keeps playing on
        whatever device it was on before, rather than silently
        crashing the scheduler thread.
        """
        if device_id:
            mpv_name = f"wasapi/{{{device_id}}}"
        else:
            mpv_name = "auto"
        try:
            self._player["audio-device"] = mpv_name
            logger.info("mpv audio-device switched to %s", mpv_name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "mpv set_audio_device(%s) failed: %s — playback stays "
                "on the previously selected device.",
                mpv_name, exc,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_end_file_reason(event) -> str:
        """
        Pull the end-file reason out of a python-mpv event object.

        The event payload shape varies a little between python-mpv
        releases (sometimes ``event.data.reason``, sometimes nested
        further), so try a couple of access patterns before giving up.
        """
        for path in (
            lambda e: e.data.reason,
            lambda e: e.event.data.reason,
            lambda e: e.reply_userdata.reason,
        ):
            try:
                val = path(event)
                if val is None:
                    continue
                # python-mpv >= 1.0 returns these as bytes/strings already;
                # earlier versions returned int enum values.
                if isinstance(val, bytes):
                    return val.decode("ascii", errors="replace")
                return str(val)
            except (AttributeError, KeyError, TypeError):
                continue
        return "unknown"

    @staticmethod
    def _redact(uri: Optional[str]) -> str:
        """
        Strip the password from a ``http://user:pass@host/...`` URI so it
        doesn't end up in the playout log.
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
