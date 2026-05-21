"""
FfmpegLineinCapture — FFmpeg dshow-based Line-In capture for RASTATIME.

Phase B (RASTATIME-2026-05-12).

Companion to ``FfmpegStreamer``:

  * :class:`FfmpegStreamer` reads a file or HTTP stream and pushes it
    to one of the public Icecast output mounts.
  * :class:`FfmpegLineinCapture` reads a Windows audio capture device
    (microphone / line-in) via FFmpeg's ``dshow`` demuxer and pushes
    the result to an internal Icecast mount (e.g. ``/linein-capture``).

The two are then composed by the scheduler at LineinEvent-start time:

::

    [Microphone]
        ↓
    FfmpegLineinCapture  →  icecast://source:****@.../linein-capture
                                    ↓
                          mpv (local monitor)  +  3× FfmpegStreamer
                                                 ↓
                                       rastatime192 / -aac / -ogg

Why a separate class instead of "another FfmpegStreamer instance":

  * Input is a live capture device, not a file/URL — different ffmpeg
    args (``-f dshow -i audio="@device_cm_{...}\\wave_{<GUID>}"``).
  * No seek / cue-in semantics — microphones are instantly live.
  * Reconnect logic doesn't apply on the input side (we either own the
    device or we don't); we still need a clean graceful-quit path for
    the output Icecast PUT, hence the shared 'q'-shutdown protocol.

Device addressing:

  FFmpeg's ``dshow`` demuxer accepts two equivalent forms for naming
  an input device:

    1. Friendly name, e.g. ``audio="Jabra-Mikrofon (Jabra EVOLVE LINK)"``
       — fragile, depends on OS locale and exact display string.
    2. Alternative-name with GUID, e.g.
       ``audio="@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave_{<GUID>}"``
       — stable, matches our ``rastatime_linein.device_id`` 1:1.

  We use form #2 throughout.  The ``33D9A762-…`` class-GUID is the
  Windows-defined CLSID for the AudioInputDeviceCategory; the
  ``<GUID>`` portion is the per-endpoint GUID, which the WindowsAudio
  device manager already exposes as the ``stable_id`` (lower-cased
  and brace-stripped).  We re-uppercase and brace-wrap here.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import IO, Callable, Optional

# FFmpeg writes a status line of the form ``size=… time=HH:MM:SS.ss
# bitrate=… speed=… elapsed=…`` to its stderr roughly every 0.5 s.  The
# ``time=`` value is the encoder's input/output position — when the
# dshow demuxer stalls (Windows mic USB unplugged), FFmpeg keeps the
# status thread running and keeps writing lines, but ``time=`` stays
# frozen at the last successfully muxed timestamp.  That's the
# fingerprint we watch for in the watchdog.
_FFMPEG_STATUS_TIME_RE = re.compile(rb"time=(\d+:\d+:\d+\.\d+)")

logger = logging.getLogger(__name__)

# Windows AudioInputDeviceCategory CLSID, identical for every input
# device.  See https://learn.microsoft.com/en-us/windows/win32/api/strmif/ne-strmif-_filter_state
_DSHOW_AUDIO_INPUT_CLSID = "33D9A762-90C8-11D0-BD43-00A0C911CE86"


def _find_ffmpeg() -> str:
    """Locate ffmpeg.exe.  Returns the path or raises RuntimeError."""
    env_path = os.environ.get("RASTATIME_FFMPEG_PATH", "")
    if env_path and Path(env_path).is_file():
        return env_path

    for candidate in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]:
        if Path(candidate).is_file():
            return candidate

    found = shutil.which("ffmpeg")
    if found:
        return found

    raise RuntimeError(
        "ffmpeg.exe not found.  Install FFmpeg and ensure it is on PATH,\n"
        "or set RASTATIME_FFMPEG_PATH to the ffmpeg.exe location."
    )


def _stable_id_to_dshow_audio(stable_id: str) -> str:
    """
    Build the dshow alternative-name for an audio input device from
    its RASTATIME stable ID (= lower-cased GUID without braces).

    >>> _stable_id_to_dshow_audio("0fb30b0b-c875-432b-a48f-dbb5208995c9")
    'audio=@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\\\wave_{0FB30B0B-C875-432B-A48F-DBB5208995C9}'
    """
    guid = stable_id.strip("{}").upper()
    return (
        f"audio=@device_cm_{{{_DSHOW_AUDIO_INPUT_CLSID}}}"
        f"\\wave_{{{guid}}}"
    )


class FfmpegLineinCapture:
    """
    Captures audio from a Windows dshow input device and streams it
    to Icecast as a source.

    Lifecycle is symmetric with :class:`FfmpegStreamer`:

      * ``start(device_id)`` — spawn the ffmpeg subprocess.
      * ``stop()`` — graceful 'q'-shutdown, terminate fallback.
      * ``is_running`` property.
      * ``close()`` — alias for stop, kept for resource-cleanup
        parallelism with the rest of the engine layer.

    The Icecast destination (host/port/mount/codec) is configured at
    construction time.  Different schedule items can reuse the same
    instance; ``start()`` re-targets it to a new input device.

    Watchdog & auto-restart (Phase B.4 — RASTATIME 2026-05-13)
    ----------------------------------------------------------
    A background thread polls ``proc.poll()`` every
    :attr:`WATCHDOG_POLL_SECS` seconds.  If the FFmpeg subprocess dies
    with a non-zero return code while a capture is supposed to be live
    (i.e. nobody called :meth:`stop`), the watchdog logs the stderr
    tail and attempts up to :attr:`MAX_AUTO_RESTART_ATTEMPTS` restarts
    against the same device, separated by :attr:`AUTO_RESTART_DELAY_SECS`.
    Real-world trigger: operator yanks the microphone USB cable mid-show.

    The watchdog is *ownership-aware*: it captures its own Popen reference
    at start time and bows out as soon as it sees ``self._process``
    point somewhere else (e.g. because someone called ``start(another)``).
    That keeps the start/stop fast path completely lock-free aside from
    the existing ``_lifecycle_lock``.

    An optional ``on_restart_callback`` (set by the scheduler) is fired
    after each successful restart so downstream consumers (mpv +
    FfmpegStreamer) can re-attach to the freshly re-published mount —
    without it, the mount would come back but mpv would already have
    given up on "stream ends prematurely".
    """

    DEFAULT_MOUNT = "linein-capture"
    DEFAULT_PORT = 8000

    # Watchdog tuning.
    WATCHDOG_POLL_SECS = 2.0
    AUTO_RESTART_DELAY_SECS = 5.0
    MAX_AUTO_RESTART_ATTEMPTS = 3
    # Stall detection (Phase B.4 #1 follow-up — RASTATIME 2026-05-13)
    # --------------------------------------------------------------
    # On Windows, dshow does NOT terminate the FFmpeg subprocess when
    # the input device disappears (e.g. mic USB cable yanked); it
    # simply stops delivering samples.  FFmpeg stays alive, ``poll()``
    # returns None forever, AND its stderr status thread keeps writing
    # status lines every 0.5 s — but those lines all show the SAME
    # ``time=HH:MM:SS.ss`` value (the encoder's last muxed position),
    # while ``elapsed=`` (wallclock) keeps ticking.
    #
    # First-attempt detection via stderr-log file size was therefore
    # useless: the log grows continuously even when the encoder has
    # frozen.  Correct detection: extract the latest ``time=`` value
    # from the stderr tail and check whether it changes between polls.
    # STALL_THRESHOLD_SECS is the grace period before we declare the
    # alive-but-mute process stalled and forcibly terminate it,
    # routing the recovery through the normal dead-process restart
    # path below.
    STALL_THRESHOLD_SECS = 5.0

    def __init__(
        self,
        *,
        icecast_host: str = "localhost",
        icecast_port: int = DEFAULT_PORT,
        icecast_user: str = "source",
        icecast_password: str = "admin",
        icecast_mount: str = DEFAULT_MOUNT,
        codec: str = "libmp3lame",
        bitrate_kbps: int = 192,
        samplerate: int = 48000,
        channels: int = 2,
        on_restart_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._ffmpeg_path = _find_ffmpeg()
        self._icecast_host = icecast_host
        self._icecast_port = icecast_port
        self._icecast_user = icecast_user
        self._icecast_password = icecast_password
        self._icecast_mount = icecast_mount.lstrip("/")
        self._codec = codec
        self._bitrate = f"{int(bitrate_kbps)}k"
        self._samplerate = int(samplerate)
        self._channels = int(channels)

        self._process: Optional[subprocess.Popen] = None
        self._stderr_fh: Optional[IO[bytes]] = None
        # Same lifecycle-lock pattern as FfmpegStreamer: serialises
        # start()/stop() against each other across the scheduler timer
        # threads and the source-switcher webhook.
        self._lifecycle_lock = threading.Lock()

        # Watchdog state — see class docstring.
        self._device_id: Optional[str] = None
        self._watchdog: Optional[threading.Thread] = None
        self._watchdog_stop = threading.Event()
        self._on_restart_callback = on_restart_callback

        log_dir = Path(
            os.environ.get("RASTATIME_LOG_DIR", r"C:\rastatime\logs")
        )
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            log_dir = Path.cwd()
        self._stderr_log_path = log_dir / f"ffmpeg-{self._icecast_mount.replace('/', '_')}.log"

        logger.info(
            "FfmpegLineinCapture ready: codec=%s bitrate=%s samplerate=%dHz "
            "-> %s:%d/%s (stderr log: %s)",
            self._codec, self._bitrate, self._samplerate,
            icecast_host, icecast_port, self._icecast_mount,
            self._stderr_log_path,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    # RASTATIME 2026-05-17 — initial-spawn retry parameters.
    # Background: Tascam USB-audio + Windows dshow occasionally fails
    # the first dshow_open with rc=0xCCCC1008 ("exited immediately")
    # — a known race when the previous dshow handle from the same
    # process is not yet fully released by the kernel-mode driver.
    # A single 1-second pause and retry recovers it cleanly in
    # essentially all observed cases.  Three attempts give us
    # ~7.5 s of total tolerance before we surface a hard error.
    _IMMEDIATE_RETRY_MAX_ATTEMPTS = 3
    _IMMEDIATE_RETRY_BACKOFF_S = 1.0

    def start(self, device_id: str) -> None:
        """
        Begin capturing from ``device_id`` (the rastatime_linein stable
        ID, i.e. lower-cased GUID without braces) and pushing the
        encoded stream to the configured Icecast mount.

        If a capture is already running with a DIFFERENT device, it is
        stopped first.  If it is already running with the SAME device,
        ``start()`` is a no-op — this matters for back-to-back shows
        that share a mic (Phase B.4 #3 — same-device transition): the
        scheduler can call ``start()`` on every show boundary without
        causing a 1.5-4.5 s silence gap while FFmpeg drains its 'q'
        and a fresh subprocess warms up.

        Holds the lifecycle lock for the whole start, so a parallel
        :meth:`stop` from another thread cannot race the new
        subprocess's bookkeeping.

        If the very first dshow open fails (Tascam / USB-audio race
        described above), the spawn is retried up to
        :attr:`_IMMEDIATE_RETRY_MAX_ATTEMPTS` times.  Distinct from
        the post-start watchdog's mid-show restart logic — that one
        kicks in only after the capture has been healthy at least
        once.

        On success, an *ownership-aware* watchdog thread is spawned that
        detects unexpected death (or stall) of the subprocess and
        retries the start up to :attr:`MAX_AUTO_RESTART_ATTEMPTS` times
        (Phase B.4 #1 — device unplugged mid-show).
        """
        with self._lifecycle_lock:
            # Same-device idempotency.  poll() == None means alive.
            if (
                self._process is not None
                and self._process.poll() is None
                and self._device_id == device_id
            ):
                logger.info(
                    "FfmpegLineinCapture.start: device %s already capturing "
                    "(PID=%d) — keeping subprocess alive, no bounce.",
                    device_id, self._process.pid,
                )
                return

            self._stop_locked()
            # Clear stop signal: a previous stop() may have left it set.
            # _start_locked spawns the watchdog only if it sees the
            # subprocess come up healthy.
            self._watchdog_stop.clear()
            for attempt in range(1, self._IMMEDIATE_RETRY_MAX_ATTEMPTS + 1):
                self._start_locked(device_id)
                if self._process is not None and self._process.poll() is None:
                    # Success: subprocess survived the 1.5 s warmup
                    # health-check inside _start_locked.
                    if attempt > 1:
                        logger.info(
                            "FfmpegLineinCapture.start: succeeded on "
                            "attempt %d (device %s)",
                            attempt, device_id,
                        )
                    return
                if attempt < self._IMMEDIATE_RETRY_MAX_ATTEMPTS:
                    logger.warning(
                        "FfmpegLineinCapture.start: attempt %d failed "
                        "(device %s); retrying in %.1f s",
                        attempt, device_id, self._IMMEDIATE_RETRY_BACKOFF_S,
                    )
                    time.sleep(self._IMMEDIATE_RETRY_BACKOFF_S)

            logger.error(
                "FfmpegLineinCapture.start: gave up after %d attempts for "
                "device %s — capture will not run; Line-In show will be silent",
                self._IMMEDIATE_RETRY_MAX_ATTEMPTS, device_id,
            )

    def set_on_restart_callback(
        self, callback: Optional[Callable[[], None]]
    ) -> None:
        """
        Install/replace the callback fired by the watchdog after every
        successful auto-restart.

        Typically wired by the scheduler to re-point mpv and the
        FfmpegStreamer instances at the listen URL — without it, the
        Icecast mount comes back but downstream consumers stay tuned to
        a dead stream until the next schedule poll.
        """
        self._on_restart_callback = callback

    def _start_locked(self, device_id: str) -> None:
        if not device_id:
            logger.error(
                "FfmpegLineinCapture.start: empty device_id — refusing to start."
            )
            return

        # Remember the device for watchdog-driven restart attempts.
        self._device_id = device_id

        dshow_input = _stable_id_to_dshow_audio(device_id)
        icecast_url = (
            f"icecast://{self._icecast_user}:{self._icecast_password}@"
            f"{self._icecast_host}:{self._icecast_port}/{self._icecast_mount}"
        )

        cmd = [
            self._ffmpeg_path,
            # ------------------------------------------------------------
            # Low-latency input/output knobs (RASTATIME 2026-05-13).
            # -fflags +nobuffer  : disable the demuxer's input buffer so
            #                      samples are forwarded to the encoder
            #                      the moment dshow delivers them, rather
            #                      than batched in 200-300 ms chunks.
            # -flags +low_delay  : tell codecs that this is a live stream
            #                      — libmp3lame skips reorder buffering.
            # -flush_packets 1   : push every encoded MP3 packet to the
            #                      muxer (and from there to Icecast) the
            #                      moment it is ready, not buffered.
            # Combined with Icecast's per-mount burst-size=0 on
            # /linein-capture, this brings the operator-side monitor
            # latency from ~3.5 s down to roughly 0.5-0.8 s while leaving
            # the public mounts (/rastatime192 et al.) unaffected.
            # ------------------------------------------------------------
            "-fflags", "+nobuffer",
            "-flags", "+low_delay",
            # dshow capture options must precede ``-i``.
            "-f", "dshow",
            # ``rtbufsize`` raises the Windows DirectShow callback ring
            # buffer.  Default is small and tends to drop samples on
            # busy systems; ~200 MB is overkill but harmless.
            "-rtbufsize", "200M",
            # Bigger thread_queue_size between dshow demuxer and the
            # encoder — same headroom we use for live HTTP-stream
            # inputs in FfmpegStreamer to avoid drops.
            "-thread_queue_size", "4096",
            "-i", dshow_input,
            "-vn",
            "-c:a", self._codec,
            "-b:a", self._bitrate,
            "-ac", str(self._channels),
            "-ar", str(self._samplerate),
            "-f", "mp3",
            "-content_type", "audio/mpeg",
            "-flush_packets", "1",
            icecast_url,
        ]

        logger.info(
            "FfmpegLineinCapture start: device_id=%s -> %s:%d/%s",
            device_id, self._icecast_host, self._icecast_port, self._icecast_mount,
        )
        logger.debug("FfmpegLineinCapture cmd: %s", cmd)

        try:
            self._stderr_fh = open(self._stderr_log_path, "ab", buffering=0)
            header = (
                f"\n===== FfmpegLineinCapture start device={device_id} "
                f"@ {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
                f"cmd: {' '.join(cmd)}\n"
            ).encode()
            self._stderr_fh.write(header)
        except OSError as exc:
            logger.warning(
                "Could not open capture stderr log %s: %s",
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
                ),
            )
        except FileNotFoundError:
            logger.error("ffmpeg.exe not found at %s", self._ffmpeg_path)
            self._close_stderr_fh()
            self._process = None
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to start FfmpegLineinCapture: %s", exc)
            self._close_stderr_fh()
            self._process = None
            return

        # Brief health check — if the capture crashes immediately (bad
        # device GUID, codec missing, icecast unreachable), poll()
        # returns within ~1 s and we surface the error.  dshow's device
        # negotiation is a bit slower than HTTP, so we give it 1.5 s.
        time.sleep(1.5)
        rc = self._process.poll()
        if rc is not None:
            tail = self._read_stderr_tail(2000)
            logger.error(
                "FfmpegLineinCapture exited immediately (rc=%d).  "
                "Last stderr:\n%s",
                rc, tail,
            )
            self._close_stderr_fh()
            self._process = None
            return

        logger.info(
            "FfmpegLineinCapture streaming PID=%d: device=%s",
            self._process.pid, device_id,
        )

        # Hand this specific subprocess to a watchdog.  The watchdog
        # captures ``self._process`` by reference and bails out the
        # moment ``self._process`` points somewhere else — so a
        # subsequent ``start(other_device)`` does not need to coordinate
        # with us here; it just spawns a new watchdog and the old one
        # self-terminates on the next poll iteration.
        self._spawn_watchdog_locked(self._process)

    def _spawn_watchdog_locked(self, owned_proc: subprocess.Popen) -> None:
        """
        Spawn a watchdog thread for *owned_proc*. Caller holds the lock.

        Does NOT clear ``_watchdog_stop`` — that is the caller's
        responsibility (done by :meth:`start` exactly once per external
        start cycle).  If ``_watchdog_stop`` is already set when we get
        here, it means a parallel :meth:`stop` is waiting just outside
        the lock for us to release it; in that case we do not start a
        new watchdog at all — it would simply exit on its first poll
        anyway, but we save the thread overhead.
        """
        if self._watchdog_stop.is_set():
            return
        self._watchdog = threading.Thread(
            target=self._watchdog_loop,
            args=(owned_proc,),
            name=f"FfmpegLineinCapture-watchdog-{owned_proc.pid}",
            daemon=True,
        )
        self._watchdog.start()

    def _watchdog_loop(self, owned_proc: subprocess.Popen) -> None:
        """
        Detect unexpected death OR stall of *owned_proc* and trigger
        auto-restart.

        Exits silently when any of these become true:

          * :attr:`_watchdog_stop` is signalled
            (someone called :meth:`stop`).
          * ``self._process`` no longer references *owned_proc*
            (e.g. ``start(other)`` swapped us out).
          * The subprocess exits with rc == 0 (graceful 'q' shutdown
            triggered by :meth:`_stop_locked`).

        Restart triggers:

          1. ``poll()`` returns a non-zero rc — the subprocess died
             without us asking for it (codec error mid-stream, Icecast
             refused the source mid-stream, …).
          2. The subprocess is alive but the stderr-log file size has
             not grown for ``STALL_THRESHOLD_SECS`` — classic Windows
             dshow stall when the input device disappears (mic USB
             unplugged).  We forcibly terminate the alive-but-mute
             process, which makes the next poll iteration see rc != 0
             and take the dead-process restart path.
        """
        attempts = 0
        # Stall-detection state — only meaningful while proc is alive.
        # ``last_time_str`` is the most recent ``time=HH:MM:SS.ss``
        # value seen in the FFmpeg stderr status lines.  None means we
        # have not seen any status line yet (the warm-up window after
        # ``_start_locked``'s 1.5 s healthcheck) — we DEFER the stall
        # judgment in that case rather than false-firing on startup.
        last_time_str: Optional[bytes] = self._safe_stderr_last_time()
        last_progress_at = time.monotonic()

        while not self._watchdog_stop.is_set():
            # Interruptible sleep — wakes immediately if stop() arrives.
            if self._watchdog_stop.wait(self.WATCHDOG_POLL_SECS):
                return

            # If a parallel start() replaced us with a different process,
            # bow out — the new watchdog owns the new process.
            if self._process is not owned_proc:
                return

            rc = owned_proc.poll()
            if rc is None:
                # Process alive — check whether the encoder's ``time=``
                # cursor is still advancing.  See the class docstring
                # near STALL_THRESHOLD_SECS for why this is the right
                # signal (vs. file-size).
                cur_time_str = self._safe_stderr_last_time()

                if cur_time_str is None or cur_time_str != last_time_str:
                    # Either still warming up (no status line yet) or
                    # the encoder advanced since last poll → healthy.
                    last_time_str = cur_time_str
                    last_progress_at = time.monotonic()
                    attempts = 0
                    continue

                # ``time=`` is identical to the previous reading AND is
                # non-None.  That means FFmpeg has emitted at least one
                # status line but the encoder hasn't moved since.
                stalled_for = time.monotonic() - last_progress_at
                if stalled_for < self.STALL_THRESHOLD_SECS:
                    continue

                logger.warning(
                    "FfmpegLineinCapture watchdog: subprocess PID=%d for "
                    "device %s is alive but stalled (encoder time= frozen "
                    "at %s for %.1fs — likely USB device unplugged).  "
                    "Forcing terminate() to trigger restart.",
                    owned_proc.pid, self._device_id,
                    last_time_str.decode(errors="replace"), stalled_for,
                )
                try:
                    owned_proc.terminate()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug(
                        "terminate() raised %s — trying kill()", exc,
                    )
                    try:
                        owned_proc.kill()
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                # Reset the stall window so we don't re-fire immediately
                # if terminate is slow to take effect.
                last_progress_at = time.monotonic()
                continue

            # Subprocess exited.  rc == 0 means graceful 'q' shutdown
            # (stop_locked path) — not our problem.
            if rc == 0:
                return

            # Unexpected non-zero exit — capture the stderr tail for
            # diagnostics and decide whether to retry.
            tail = self._read_stderr_tail(1500)
            logger.warning(
                "FfmpegLineinCapture watchdog: subprocess for device %s "
                "died unexpectedly (rc=%d).  Last stderr:\n%s",
                self._device_id, rc, tail,
            )

            attempts += 1
            if attempts > self.MAX_AUTO_RESTART_ATTEMPTS:
                logger.error(
                    "FfmpegLineinCapture watchdog: %d restart attempts "
                    "failed for device %s — giving up; the line-in mount "
                    "stays offline for the rest of this slot.",
                    self.MAX_AUTO_RESTART_ATTEMPTS, self._device_id,
                )
                return

            # Back off before retry (still interruptible).
            if self._watchdog_stop.wait(self.AUTO_RESTART_DELAY_SECS):
                return

            with self._lifecycle_lock:
                # Re-check after taking the lock: stop() or start(other)
                # may have happened while we waited.
                if self._watchdog_stop.is_set():
                    return
                if self._process is not owned_proc:
                    return

                logger.info(
                    "FfmpegLineinCapture watchdog: attempt %d/%d — "
                    "restarting capture for device %s",
                    attempts, self.MAX_AUTO_RESTART_ATTEMPTS, self._device_id,
                )
                self._stop_locked()                # clears dead handles
                # _start_locked spawns a *new* watchdog at its tail.
                self._start_locked(self._device_id)

            # Fire the consumer-re-attach callback OUTSIDE the lock — it
            # touches mpv + FfmpegStreamer which take their own locks and
            # we must not invert lock order.  We do this even when the
            # new _start_locked failed (process is None) because the
            # callback should be idempotent and merely re-points mpv at
            # the listen URL — if Icecast is silent, mpv just buffers.
            cb = self._on_restart_callback
            if cb is not None:
                try:
                    cb()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "FfmpegLineinCapture watchdog: on_restart_callback "
                        "raised %s — ignoring (consumers will re-attach on "
                        "next schedule poll).", exc,
                    )

            # Hand off to the freshly spawned watchdog and exit ours.
            return

    def stop(self) -> None:
        """
        Stop the current capture subprocess (if running).

        Same graceful 'q' → terminate → kill ladder as
        :class:`FfmpegStreamer.stop`.  Also signals the watchdog to
        exit and waits up to 3 s for it to do so — so a caller can rely
        on the FFmpeg subprocess being truly gone (no zombie restart)
        once stop() returns.
        """
        # Signal the watchdog FIRST so that even if it is mid-restart
        # waiting for the lock, it sees the stop intent the moment the
        # lock becomes available.
        self._watchdog_stop.set()
        with self._lifecycle_lock:
            self._stop_locked()
        # Best-effort join — watchdog is a daemon so this is purely for
        # cleanliness, not correctness.  Done outside the lock so the
        # watchdog can complete its own lock-protected restart path
        # (which it will then abort because _watchdog_stop is set).
        wd = self._watchdog
        if wd is not None and wd.is_alive():
            wd.join(timeout=3)
        self._watchdog = None

    def _stop_locked(self) -> None:
        if self._process is None:
            self._close_stderr_fh()
            return

        proc = self._process

        if proc.poll() is None:
            logger.info(
                "FfmpegLineinCapture stop (PID=%d) — sending 'q' for clean exit",
                proc.pid,
            )
            try:
                self._send_quit_signal(proc)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "FfmpegLineinCapture PID=%d did not exit on 'q' "
                        "within 3 s; falling back to terminate()", proc.pid,
                    )
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "FfmpegLineinCapture PID=%d did not exit on "
                            "terminate(); kill()", proc.pid,
                        )
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("FfmpegLineinCapture cleanup error: %s", exc)

        rc = proc.returncode
        if rc not in (0, None):
            tail = self._read_stderr_tail(1000)
            logger.warning(
                "FfmpegLineinCapture exited with code %d.  Last stderr:\n%s",
                rc, tail,
            )

        self._process = None
        self._close_stderr_fh()

    def _send_quit_signal(self, proc: subprocess.Popen) -> None:
        """Write ``b'q\\n'`` to ffmpeg's stdin and close it."""
        if proc.stdin is None:
            return
        try:
            if not proc.stdin.closed:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
                proc.stdin.close()
        except (BrokenPipeError, OSError) as exc:
            logger.debug(
                "FfmpegLineinCapture PID=%d stdin write failed "
                "(already exiting?): %s",
                proc.pid, exc,
            )

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def listen_url(self) -> str:
        """``http://host:port/mount`` for downstream consumers (mpv, FFmpegStreamer)."""
        return f"http://{self._icecast_host}:{self._icecast_port}/{self._icecast_mount}"

    def close(self) -> None:
        """Stop and release resources.  Mirrors FfmpegStreamer.close."""
        self.stop()
        logger.info("FfmpegLineinCapture closed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _close_stderr_fh(self) -> None:
        if self._stderr_fh is not None:
            try:
                self._stderr_fh.close()
            except OSError:
                pass
            self._stderr_fh = None

    def _read_stderr_tail(self, max_bytes: int = 1000) -> str:
        try:
            with open(self._stderr_log_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - max_bytes))
                return fh.read().decode(errors="replace")
        except OSError as exc:
            return f"(could not read stderr log: {exc})"

    def _safe_stderr_last_time(self) -> Optional[bytes]:
        """
        Return the most recent ``time=HH:MM:SS.ss`` value FFmpeg has
        written to its stderr log, or ``None`` if no status line has
        been emitted yet (or the log file is unreadable).

        Used by the watchdog's stall-detection logic — see the class
        docstring near :attr:`STALL_THRESHOLD_SECS` for the rationale.

        We read only the tail of the file (last 4 KiB) because FFmpeg's
        full setup output can be hundreds of KiB and we only care about
        the latest status line.  4 KiB comfortably holds the last ~30
        status lines even with the longest filenames.

        We treat OSError as ``None`` rather than raising, because the
        watchdog runs in a daemon thread and we'd rather miss one poll
        than crash the recovery path.
        """
        try:
            with open(self._stderr_log_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - 4096))
                tail = fh.read()
        except OSError:
            return None
        matches = _FFMPEG_STATUS_TIME_RE.findall(tail)
        if not matches:
            return None
        return matches[-1]
