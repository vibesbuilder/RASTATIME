"""
FfmpegStreamer — FFmpeg-based Icecast streamer for RASTATIME.

Replaces VLC's broken sout/shout chain on Windows with a reliable FFmpeg
subprocess that reads audio files and streams to Icecast via the built-in
``icecast://`` protocol.

Architecture
------------
The local playback engine (mpv since 2026-05) plays the file for
monitoring.  For each track the PlayoutScheduler plays locally, it also
starts an FFmpeg subprocess that reads the same file and streams it to
Icecast — independent of the local-monitor decode path.

The FFmpeg command:

  ffmpeg -re -i input.mp3 -c:a libmp3lame -b:a 192k
         -f mp3 -content_type audio/mpeg
         icecast://source:pass@host:port/mount

  - ``-re`` reads input at native speed (real-time).
  - ``-c:a libmp3lame`` transcodes to MP3 (or libvorbis for OGG, etc.).
  - ``-f mp3`` selects the output container format.
  - ``icecast://`` is FFmpeg's built-in Icecast output protocol.

Why FFmpeg instead of VLC sout?
  VLC 3.0's sout chain parser on Windows treats ``//`` as a comment,
  but VLC's shout module requires ``//`` in the dst URL for correct
  RFC 3986 authority parsing (user:pass@host:port/mount).  This makes
  it impossible to pass Icecast credentials through VLC's sout chain.
  FFmpeg handles Icecast natively without these parser issues.
"""
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import IO, Dict, List, Optional

logger = logging.getLogger(__name__)

# FFmpeg codec/format mapping for each stream format key stored in cc_pref.
# default_samplerate is used when the stream config does not specify one.
# libopus only accepts 8/12/16/24/48 kHz — 44100 Hz is forced up to 48000 Hz.
_FFMPEG_CODEC_MAP: Dict[str, tuple] = {
    # (ffmpeg codec, ffmpeg format, content_type, default_samplerate)
    "mp3":  ("libmp3lame", "mp3",  "audio/mpeg",       44100),
    "ogg":  ("libvorbis",  "ogg",  "application/ogg",  44100),
    "opus": ("libopus",    "ogg",  "application/ogg",  48000),
    "aac":  ("aac",        "adts", "audio/aac",        44100),
}

# Sample rates accepted by libopus (Hz).  Anything else gets clamped to 48000.
_OPUS_VALID_SAMPLERATES = {8000, 12000, 16000, 24000, 48000}

_CHANNELS_MAP: Dict[str, int] = {
    "stereo": 2,
    "mono": 1,
}


def _find_ffmpeg() -> str:
    """Locate ffmpeg.exe.  Returns the path or raises RuntimeError."""
    # 1. Check RASTATIME_FFMPEG_PATH environment variable
    env_path = os.environ.get("RASTATIME_FFMPEG_PATH", "")
    if env_path and Path(env_path).is_file():
        return env_path

    # 2. Check common install locations
    for candidate in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]:
        if Path(candidate).is_file():
            return candidate

    # 3. Check PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    raise RuntimeError(
        "ffmpeg.exe not found.  Install FFmpeg and ensure it is on PATH,\n"
        "or set RASTATIME_FFMPEG_PATH to the ffmpeg.exe location."
    )


class FfmpegStreamer:
    """
    Manages an FFmpeg subprocess that streams audio to Icecast.

    Thread-safety: ``start()`` and ``stop()`` may be called from different
    threads (timer callbacks).  The subprocess handle is protected.
    """

    def __init__(self, stream_config: Dict) -> None:
        """
        Initialise with a stream configuration dict from cc_pref.

        Required keys: host, port, mount, pass, type, bitrate, channels.
        Optional: user (defaults to "source").
        """
        self._ffmpeg_path = _find_ffmpeg()
        self._config = stream_config
        self._process: Optional[subprocess.Popen] = None
        self._stderr_fh: Optional[IO[bytes]] = None
        # Serialise start()/stop() — both can be invoked from different
        # threads (scheduler timer callbacks, source-switcher webhook),
        # and without serialisation parallel stops produce duplicate
        # "FFmpeg stop (PID=...) — sending 'q'" log lines because each
        # thread snapshots self._process before any of them clears it.
        self._lifecycle_lock = threading.Lock()

        # Parse stream config
        fmt = str(stream_config.get("type", "mp3")).lower()
        codec_info = _FFMPEG_CODEC_MAP.get(fmt, _FFMPEG_CODEC_MAP["mp3"])
        self._codec = codec_info[0]
        self._format = codec_info[1]
        self._content_type = codec_info[2]
        default_sr = codec_info[3]

        # Sample rate: user-selectable per stream.  If the config carries
        # a value, use it; otherwise fall back to the codec default.
        # Opus has hard codec restrictions — invalid values get clamped
        # to 48000 Hz with a warning so the encoder doesn't refuse to start.
        try:
            requested_sr = int(stream_config.get("samplerate") or default_sr)
        except (TypeError, ValueError):
            requested_sr = default_sr
        if fmt == "opus" and requested_sr not in _OPUS_VALID_SAMPLERATES:
            logger.warning(
                "Sample rate %d Hz not supported by libopus; "
                "forcing 48000 Hz for stream '%s'",
                requested_sr, stream_config.get("mount", "?"),
            )
            requested_sr = 48000
        self._samplerate = requested_sr

        self._bitrate = f"{int(stream_config.get('bitrate', 128))}k"
        self._channels = _CHANNELS_MAP.get(
            str(stream_config.get("channels", "stereo")).lower(), 2
        )

        # Icecast URL
        host = stream_config.get("host", "localhost")
        port = int(stream_config.get("port", 8000))
        mount = str(stream_config.get("mount", "stream")).lstrip("/")
        password = stream_config.get("pass", "")
        user = str(stream_config.get("user", "") or "source")
        self._mount = mount
        self._icecast_url = f"icecast://{user}:{password}@{host}:{port}/{mount}"
        # Public listen URL for this output — used by PlayoutScheduler to
        # let the local playback engine pick up our re-encoded stream as
        # monitoring audio (instead of reading /main or /show directly).
        # Historical note: under libVLC 3.x this indirection was a hard
        # requirement because the icy-header / icyx:// retry path dropped
        # HTTP auth; with the mpv backend the same indirection is kept
        # for symmetry and to avoid mpv having to re-auth on every source
        # switch.
        self._listen_url = f"http://{host}:{port}/{mount}"

        # Per-mountpoint FFmpeg log file (captures stderr — connection
        # errors, encoder warnings, end-of-stream notices).
        log_dir = Path(
            os.environ.get("RASTATIME_LOG_DIR", r"C:\rastatime\logs")
        )
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            log_dir = Path.cwd()
        safe_mount = mount.replace("/", "_") or "stream"
        self._stderr_log_path = log_dir / f"ffmpeg-{safe_mount}.log"

        logger.info(
            "FfmpegStreamer ready: codec=%s bitrate=%s samplerate=%dHz "
            "-> %s:%d/%s (stderr log: %s)",
            self._codec, self._bitrate, self._samplerate,
            host, port, mount,
            self._stderr_log_path,
        )

    def start(
        self,
        audio_path: str,
        *,
        seek_seconds: float = 0.0,
        gain_db: Optional[float] = None,
    ) -> None:
        """
        Start streaming an audio file to Icecast.

        If a previous ffmpeg process is still running, it is stopped first.
        Holds the lifecycle lock for the whole start so a parallel stop()
        from another thread cannot race the new process's bookkeeping.

        RASTATIME 2026-05-16 — ``gain_db`` is a generic per-event dB
        offset applied as an FFmpeg ``volume`` audio filter before the
        encoder.  The scheduler computes the value differently per
        event type:

          * File events: ``cc_files.replay_gain`` plus the operator's
            global ``cc_pref.replay_gain_modifier`` (precomputed sum).
          * Webstream events: ``cc_webstream.input_gain_db`` (per-source
            operator-configured gain to compensate for quiet/loud feeds).
          * Live sources (Master/Show): currently ``None`` (no per-source
            gain feature yet).

        ``None`` or ``0.0`` means no filter is added (saves a CPU-free
        no-op ``volume=0dB`` filter in the chain).

        (Was ``replay_gain_db`` before 2026-05-16; renamed to reflect
        that the same mechanism now carries non-ReplayGain values.)
        """
        with self._lifecycle_lock:
            # Use the unlocked variant — we're already holding the lock.
            self._stop_locked()
            self._start_locked(
                audio_path,
                seek_seconds=seek_seconds,
                gain_db=gain_db,
            )

    def _start_locked(
        self,
        audio_path: str,
        *,
        seek_seconds: float = 0.0,
        gain_db: Optional[float] = None,
    ) -> None:
        """Internal start body — caller must hold ``self._lifecycle_lock``."""

        # Distinguish file input (scheduled track .mp3) from HTTP input
        # (DJ-source mount, e.g. http://127.0.0.1:8000/main).  Different
        # input options make sense for each:
        #
        #   File input:
        #     - "-re" paces the read at native real-time speed, so we don't
        #       race through the file and queue up output that Icecast cannot
        #       drain at the same rate.
        #
        #   HTTP / live-stream input:
        #     - "-re" is redundant — the upstream stream already paces us.
        #     - Reconnect flags let ffmpeg ride out short network blips on the
        #       DJ source without dying.  We then don't need to spin up a
        #       fresh FfmpegStreamer subprocess just because the DJ's wifi
        #       hiccuped for a second.
        is_stream_input = audio_path.lower().startswith(("http://", "https://"))

        cmd = [self._ffmpeg_path]

        if is_stream_input:
            cmd.extend([
                # All these are *input* options — they must come BEFORE the
                # "-i <url>" or ffmpeg parses them as output options.
                "-reconnect", "1",                  # reconnect after EOF
                "-reconnect_streamed", "1",         # reconnect on mid-stream drop
                # Reconnect even when the server returns an HTTP error
                # status (4xx / 5xx) instead of a stream.  This is
                # critical right after a DJ source connects: Icecast
                # fires the source-connect event-binding webhook the
                # instant the source-side TCP/auth handshake completes,
                # but the mount itself is not "open for listeners" until
                # the source has actually pushed its first audio frames.
                # During that ~1-3 s window Icecast answers listener
                # GETs with 404 "File Not Found".  Without this flag,
                # FFmpeg's default retry policy treats 4xx as fatal and
                # the streamer dies on the third attempt — exactly the
                # 17:42 / 18:13 outage pattern in the logs.
                # (RASTATIME 2026-05-13)
                "-reconnect_on_http_error", "4xx,5xx",
                # Also retry on transient TCP / DNS errors so a brief
                # network blip on the Wi-Fi DJ path doesn't kill the
                # subprocess outright.
                "-reconnect_on_network_error", "1",
                # 10 s upper bound between retry attempts (was 5 s).
                # Combined with the unbounded retry count above, this
                # gives Icecast plenty of time to finish marking the
                # mount as listener-ready.
                "-reconnect_delay_max", "10",
                # Bigger packet queue between the HTTP demuxer and the
                # encoder thread.  The default 8 packets is too small for
                # a live MP3/OGG source — when the encoder briefly stalls
                # (Icecast PUT flush, codec re-init) FFmpeg drops packets
                # and listeners hear clicks / dropouts.  4096 gives ~30 s
                # of headroom at 128 kbps, well above any realistic stall.
                "-thread_queue_size", "4096",
                # Drop malformed packets instead of letting them propagate
                # into the encoder.  BUTT and other GUI source clients
                # occasionally emit short truncated frames during sample-
                # rate changes — these surface downstream as audible
                # crackle when re-encoded verbatim.
                "-fflags", "+discardcorrupt",
            ])
        else:
            cmd.append("-re")

        cmd.append("-y")  # overwrite (no prompts)

        # Seek into the file if needed (for catch-up on in-progress tracks).
        # Only meaningful for file inputs — live streams don't support seeking.
        if seek_seconds > 0 and not is_stream_input:
            cmd.extend(["-ss", f"{seek_seconds:.2f}"])

        cmd.extend([
            "-i", audio_path,                   # input file or stream URL
            "-vn",                              # no video
        ])

        # NOTE (RASTATIME-2026-05-12): we previously added an
        # ``aresample=async=1000:first_pts=0`` filter for live inputs
        # to bridge sub-millisecond clock drift between BUTT's encoder
        # and Icecast's push clock.  In testing that filter turned out
        # to insert *more* artifacts than it removed — operators heard
        # a constant background crackle on both the local monitor and
        # the public outputs.  ``aresample=async`` resamples whenever
        # it thinks there's drift, which on a real-world Wi-Fi BUTT
        # connection happens basically all the time, producing the
        # crackle we were trying to fix.  Default ffmpeg PTS handling
        # is fine — keep the filter chain empty for live inputs.

        # RASTATIME 2026-05-16 — Generic gain application.  Source of the
        # value depends on event type (see start()'s docstring): file
        # tracks pass the precomputed ReplayGain sum, webstreams pass
        # the per-stream cc_webstream.input_gain_db.  ``None`` or 0.0 ⇒
        # no filter, no CPU cost.  Otherwise FFmpeg's ``volume`` filter
        # applies the gain before the encoder sees the audio; the
        # ``dB`` unit handles negative attenuations correctly without
        # needing the awkward ``10^(dB/20)`` linear translation.
        if gain_db is not None and abs(gain_db) > 0.001:
            cmd.extend(["-af", f"volume={gain_db:+.2f}dB"])

        cmd.extend([
            "-c:a", self._codec,                # audio codec
            "-b:a", self._bitrate,              # bitrate
            "-ac", str(self._channels),         # channels
            "-ar", str(self._samplerate),       # sample rate
            "-f", self._format,                 # output format
            "-content_type", self._content_type,  # Icecast content type
            self._icecast_url,                  # output destination
        ])

        logger.info("FFmpeg start: %s -> Icecast", Path(audio_path).name)
        logger.debug("FFmpeg cmd: %s", cmd)

        # Write a session header to the stderr log so it's clear which
        # ffmpeg invocation produced which output.
        try:
            self._stderr_fh = open(self._stderr_log_path, "ab", buffering=0)
            header = (
                f"\n===== FFmpeg start {Path(audio_path).name} "
                f"@ {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
                f"cmd: {' '.join(cmd)}\n"
            ).encode()
            self._stderr_fh.write(header)
        except OSError as exc:
            logger.warning(
                "Could not open ffmpeg stderr log %s: %s",
                self._stderr_log_path, exc,
            )
            self._stderr_fh = None

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,             # for graceful 'q' shutdown
                stdout=subprocess.DEVNULL,
                stderr=self._stderr_fh if self._stderr_fh else subprocess.DEVNULL,
                creationflags=getattr(
                    subprocess, "CREATE_NO_WINDOW", 0
                ),  # no console window on Windows
            )
        except FileNotFoundError:
            logger.error("ffmpeg.exe not found at %s", self._ffmpeg_path)
            self._close_stderr_fh()
            self._process = None
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to start FFmpeg: %s", exc)
            self._close_stderr_fh()
            self._process = None
            return

        # Brief health check — if ffmpeg crashes immediately (bad URL,
        # auth failure, codec not found), poll() returns within ~500 ms
        # and we can surface the error right away instead of silently
        # logging "streaming PID=…" while nothing actually streams.
        time.sleep(0.6)
        rc = self._process.poll()
        if rc is not None:
            tail = self._read_stderr_tail(2000)
            logger.error(
                "FFmpeg exited immediately (rc=%d).  Last stderr:\n%s",
                rc, tail,
            )
            self._close_stderr_fh()
            self._process = None
            return

        logger.info(
            "FFmpeg streaming PID=%d: %s",
            self._process.pid, Path(audio_path).name,
        )

    def stop(self) -> None:
        """
        Stop the current FFmpeg subprocess (if running).

        Tries a graceful shutdown first by sending ``b"q\\n"`` to ffmpeg's
        stdin — that is FFmpeg's documented "press Q to quit" path.  ffmpeg
        writes the output trailer, closes the Icecast PUT cleanly, and
        exits with code 0.  This avoids the WSAECONNRESET (-10054) noise
        that an abrupt ``terminate()`` produces in the stderr log of the
        outgoing session.

        Only on a 3-second timeout (or stdin write failure) do we fall
        back to ``terminate()`` → ``kill()`` as a hard escape hatch.

        Idempotent and thread-safe: a second concurrent stop() call
        will block on the lifecycle lock and then return immediately,
        because the first call has already cleared ``self._process``.
        """
        with self._lifecycle_lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        """Internal stop body — caller must hold ``self._lifecycle_lock``."""
        if self._process is None:
            self._close_stderr_fh()
            return

        proc = self._process

        if proc.poll() is None:
            # Process is still running — try graceful 'q' first.
            logger.info("FFmpeg stop (PID=%d) — sending 'q' for clean exit", proc.pid)
            try:
                self._send_quit_signal(proc)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "FFmpeg PID=%d did not exit on 'q' within 3s; "
                        "falling back to terminate()", proc.pid,
                    )
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "FFmpeg PID=%d did not exit on terminate(); kill()",
                            proc.pid,
                        )
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("FFmpeg cleanup error: %s", exc)

        # Whether the process self-exited or we terminated it, surface a
        # non-zero exit code in the playout log so anomalies don't hide.
        # rc=0 (clean) and rc=None (race; should not happen here) are silent.
        rc = proc.returncode
        if rc not in (0, None):
            tail = self._read_stderr_tail(1000)
            logger.warning(
                "FFmpeg exited with code %d.  Last stderr:\n%s", rc, tail,
            )

        self._process = None
        self._close_stderr_fh()

    def _send_quit_signal(self, proc: subprocess.Popen) -> None:
        """
        Write ``b"q\\n"`` to ffmpeg's stdin and close it.

        ffmpeg watches stdin for a 'q' character when running interactively
        ("Press [q] to stop").  Writing 'q\\n' triggers the same shutdown
        path: trailer is flushed, output muxer closes cleanly, exit 0.

        Closing stdin afterwards is important — it sends EOF, which makes
        ffmpeg notice the request even on builds where stdin polling is
        line-buffered rather than character-buffered.

        Failures (already-closed pipe, ffmpeg already exited) are demoted
        to debug and the caller falls back to terminate().
        """
        if proc.stdin is None:
            return
        try:
            if not proc.stdin.closed:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
                proc.stdin.close()
        except (BrokenPipeError, OSError) as exc:
            # Process likely already exited — graceful path is moot.
            logger.debug(
                "FFmpeg PID=%d stdin write failed (already exiting?): %s",
                proc.pid, exc,
            )

    @property
    def is_running(self) -> bool:
        """Return True if the FFmpeg subprocess is still running."""
        return self._process is not None and self._process.poll() is None

    @property
    def listen_url(self) -> str:
        """Public ``http://host:port/mount`` URL for reading this output."""
        return self._listen_url

    def close(self) -> None:
        """Stop and release all resources."""
        self.stop()
        logger.info("FfmpegStreamer closed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _close_stderr_fh(self) -> None:
        """Close the stderr log file handle if open."""
        if self._stderr_fh is not None:
            try:
                self._stderr_fh.close()
            except OSError:
                pass
            self._stderr_fh = None

    def _read_stderr_tail(self, max_bytes: int = 1000) -> str:
        """Read the tail of the stderr log file for diagnostics."""
        try:
            with open(self._stderr_log_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - max_bytes))
                return fh.read().decode(errors="replace")
        except OSError as exc:
            return f"(could not read stderr log: {exc})"
