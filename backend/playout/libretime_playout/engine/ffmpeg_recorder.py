"""
FfmpegRecorder — Output-Tap recorder for RASTATIME's per-show recording
feature (ARCHITECTURE Section 23.13).

Architecture
------------
For shows where ``cc_show.record == true``, the PlayoutScheduler emits
two events: SHOW_RECORD_START at the show's scheduled start, and
SHOW_RECORD_END at the show's scheduled end.  At SHOW_RECORD_START
this class spawns an FFmpeg subprocess that reads the first
configured Icecast output mountpoint (e.g.
``http://localhost:8000/rastatime``) and writes it to a single .mp3
file under
``<recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3``.

The command form:

  ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 \\
         -i http://localhost:8000/rastatime \\
         -c copy -y <output-file>

  - ``-c copy``: no re-encode; we keep the source bitrate as-is.  This
    is intentional — the recording quality matches what listeners
    actually hear, and CPU cost on the recorder is ~1-2 %.
  - ``-reconnect_*``: ride out short Icecast hiccups without dying.
  - ``-y``: overwrite if a file exists (e.g. from a failed prior run);
    the half-written file would be unusable anyway.

Failure-isolation: the recorder is an independent subprocess.  If the
Icecast mountpoint is unreachable, or FFmpeg crashes mid-show, the
stream-encoder side and the playout engine are not affected — only
the recording file is missing or incomplete.  Per Phase 4 design
decision, we do NOT restart a crashed recorder (would risk a crash
loop); we log the failure and move on.

Thread-safety: ``start()`` and ``stop()`` may be called from timer
callbacks on different threads.  The subprocess handle is guarded by
``_lock``.
"""

import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Optional

from .ffmpeg_streamer import _find_ffmpeg  # re-use the same probe

logger = logging.getLogger(__name__)

# NTFS-illegal characters in a filename: <>:"/\|?*  plus the ASCII
# control range (which Windows also rejects).  Everything else
# — including Umlauts and spaces — is kept verbatim per design
# decision 2026-05-17.
_FILENAME_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


def sanitize_show_name(name: str) -> str:
    """
    Strip NTFS-illegal characters from a show name for use in a
    filename.  Umlauts and spaces are kept.  Empty input returns
    "untitled" so the filename still has a meaningful body.
    """
    cleaned = _FILENAME_FORBIDDEN.sub("_", (name or "").strip())
    # Collapse runs of underscores so "C++/C#" → "C__C_" → "C_C_"
    cleaned = re.sub(r"_+", "_", cleaned).strip("_ ")
    return cleaned or "untitled"


def build_output_path(
    recording_folder: Path,
    show_starts_at: datetime,
    show_name: str,
) -> Path:
    """
    Compose the output path:

        <recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3

    Date and time are derived from ``show_starts_at`` and rendered in
    the **system's local timezone** so operator-visible filenames
    match wall-clock time on the studio computer.  Pythons
    ``datetime.astimezone()`` consults the system TZ at call time, so
    DST switches (Europe/Berlin: CET <-> CEST) are handled
    transparently: a show scheduled at 13:00 local time produces
    ``13-00`` in the filename in both summer (UTC+2) and winter
    (UTC+1).  The show-name is sanitized; spaces and Umlauts are kept.

    The scheduler hands us a naive UTC datetime (Pydantic strips
    tzinfo in ``event_isoparse``), so we re-attach UTC before
    converting.  If a non-naive datetime is passed it is converted
    as-is.

    Example (operator in Europe/Berlin, May / DST = UTC+2):
        recording_folder = C:/rastatime/recordings
        show_starts_at   = datetime(2026, 5, 17, 11, 0)  # naive UTC = 13:00 local
        show_name        = "Müllers Frühstück"
        -> C:/rastatime/recordings/2026-05-17/2026-05-17 13-00 - Müllers Frühstück.mp3
    """
    if show_starts_at.tzinfo is None:
        show_starts_at = show_starts_at.replace(tzinfo=timezone.utc)
    local_dt = show_starts_at.astimezone()  # system local tz
    day_str = local_dt.strftime("%Y-%m-%d")
    time_str = local_dt.strftime("%H-%M")
    name = sanitize_show_name(show_name)
    filename = f"{day_str} {time_str} - {name}.mp3"
    return recording_folder / day_str / filename


class FfmpegRecorder:
    """
    Owns at most one FFmpeg subprocess that records the active Icecast
    output mountpoint to a single .mp3 file.

    A single recorder instance serves all shows: RASTATIME's schedule
    cannot have two simultaneously-active shows, so we never need
    parallel recorders.  If ``start()`` is called while a prior
    recording is still running (which would only happen on bad data
    or a fast-forward edge case), the prior one is stopped first.
    """

    # Maximum time (s) to wait for FFmpeg to exit gracefully after
    # we send a terminate signal.  MP3 has no container trailer to
    # write, so a clean shutdown is fast.
    _STOP_TIMEOUT_SECONDS = 5

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._output_path: Optional[Path] = None
        self._show_id: Optional[int] = None
        self._lock = threading.Lock()
        self._ffmpeg_path = _find_ffmpeg()
        # RASTATIME 2026-05-17 — per-recording stderr log so a mid-show
        # crash (recorder exited != 0) leaves a diagnosable trace.
        # Pattern lifted 1:1 from FfmpegStreamer / FfmpegLineinCapture
        # so all FFmpeg subprocesses in the project share the same
        # log-dir convention.
        log_dir = Path(
            os.environ.get("RASTATIME_LOG_DIR", r"C:\rastatime\logs")
        )
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            log_dir = Path.cwd()
        self._log_dir = log_dir
        self._stderr_fh: Optional[IO[bytes]] = None
        self._stderr_log_path: Optional[Path] = None
        # RASTATIME 2026-05-17 — for the mid-show watchdog: when the
        # recorder is respawned to recover from a death mid-show, we
        # have FFmpeg write its MP3 frames to stdout and Python opens
        # the output file in append mode, so successive recording
        # segments concatenate into a single playable .mp3.  This
        # handle is only set when ``append=True`` is passed to start().
        self._output_fh: Optional[IO[bytes]] = None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    @property
    def current_show_id(self) -> Optional[int]:
        """
        Return the show_id of the currently-running FFmpeg recording,
        or None if no recording is active.  Used by the playout
        scheduler's retry thread to detect (a) "recorder died, retry"
        (returns None) vs. (b) "another show took over, abort retry"
        (returns a different show_id).
        """
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                return None
            return self._show_id

    def start(
        self,
        source_url: str,
        output_path: Path,
        show_id: int,
        show_name: str,
        append: bool = False,
    ) -> None:
        """
        Spawn a new FFmpeg recorder reading ``source_url`` and writing
        to ``output_path``.  If a prior recording is still running
        (only possible on bad scheduling), it is stopped first.

        Creates the per-day parent directory on demand.

        ``append=True`` is used by the mid-show watchdog after an
        unscheduled FFmpeg death: FFmpeg writes its MP3 stream to
        stdout (``pipe:1``) and Python opens ``output_path`` in
        ``"ab"`` (append-binary) mode.  MP3 is frame-based with no
        container header (when written with ``-write_id3v2 0
        -write_xing 0``), so successive recording segments
        concatenate naturally into a single file that every player
        can decode end-to-end.  No post-processing required.
        """
        with self._lock:
            if self._proc is not None:
                # Either a previous recording is still running (stop +
                # replace) or it died asynchronously and left stale
                # state (stderr fh, _show_id, _output_path).  Both
                # paths route through _stop_locked() so the stderr
                # file handle from the previous attempt is closed and
                # the "already exited" diagnostic tail is logged.
                # Important for the playout scheduler's retry thread
                # — without this, every Line-In recovery attempt would
                # leak a stderr handle and confuse the next attempt's
                # log file.
                if self._proc.poll() is None:
                    logger.warning(
                        "FfmpegRecorder.start: prior recording (show_id=%s, "
                        "path=%s) still running — stopping it first",
                        self._show_id, self._output_path,
                    )
                self._stop_locked()

            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.error(
                    "FfmpegRecorder.start: could not create directory %s: %s",
                    output_path.parent, exc,
                )
                return

            cmd = [
                self._ffmpeg_path,
                # Input-side options
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_on_http_error", "4xx,5xx",
                # RASTATIME 2026-05-17 — without these two flags the
                # recorder silently dies the moment Icecast briefly drops
                # the source mid-show.  That happens at every show-to-
                # show transition because the playout engine tears down
                # and re-spawns the three FFmpeg streamers from scratch
                # (~2 s gap on /rastatime); during the gap the recorder
                # sees an EOF on the body stream, and the default FFmpeg
                # behaviour is to terminate.  This was the root cause of
                # Line-In show recordings producing no file at all when
                # they followed another show.
                "-reconnect_at_eof", "1",
                "-reconnect_on_network_error", "1",
                # RASTATIME 2026-05-17 — reconnect_delay_max was 5s but the
                # streamer-vs-recorder race at show-start (recorder reaches
                # Icecast ~500 ms before the streamer pushes its first
                # packet) cost the first ~7 seconds of every recording on
                # the first run.  1 s keeps the worst-case loss to roughly
                # one reconnect attempt.
                "-reconnect_delay_max", "1",
                # Less verbose: only warnings/errors on stderr
                "-loglevel", "warning",
                "-i", source_url,
                # Output-side options
                "-c", "copy",            # no re-encode
                "-vn",                   # no video (defence-in-depth)
                # RASTATIME 2026-05-17 — flush every packet so the
                # operator (and any disk-monitor) sees the file grow in
                # real time.  Without this FFmpeg buffers in RAM and only
                # writes on graceful exit, leaving a 0-byte file for the
                # entire show — unrecoverable if the recorder crashes.
                "-flush_packets", "1",
                # RASTATIME 2026-05-17 — suppress every form of MP3
                # container header so the playout's mid-show watchdog
                # can append later segments byte-by-byte without
                # producing mid-stream ID3 / Xing frames that confuse
                # some players.  An ID3 header at byte 0 is fine;
                # one at byte 5_000_000 is not.
                "-write_id3v2", "0",
                "-write_xing", "0",
            ]
            if append:
                # Tell FFmpeg the output format explicitly (it cannot
                # infer it from "pipe:1") and write MP3 frames to
                # stdout.  Python then redirects stdout to the
                # output_path opened in append-binary mode.
                cmd.extend(["-f", "mp3", "pipe:1"])
            else:
                # Original behaviour: FFmpeg opens the file itself,
                # truncating any prior content.
                cmd.extend(["-y", str(output_path)])

            # Per-recording stderr log.  Name includes show_id and
            # show-start so concurrent test recordings don't collide.
            # Append-mode restart attempts get the "-appendN" suffix so
            # the operator can correlate them with their segment.
            ts = time.strftime("%Y%m%d-%H%M%S")
            suffix = "-append" if append else ""
            self._stderr_log_path = (
                self._log_dir
                / f"ffmpeg-recorder-show{show_id}-{ts}{suffix}.log"
            )
            try:
                self._stderr_fh = open(
                    self._stderr_log_path, "ab", buffering=0
                )
                header = (
                    f"\n===== FfmpegRecorder start show_id={show_id} "
                    f"name={show_name!r} append={append} @ {ts} =====\n"
                    f"cmd: {' '.join(cmd)}\n"
                ).encode()
                self._stderr_fh.write(header)
            except OSError as exc:
                logger.warning(
                    "FfmpegRecorder.start: could not open stderr log %s: %s",
                    self._stderr_log_path, exc,
                )
                self._stderr_fh = None

            # In append-mode, Python owns the output file descriptor
            # and redirects FFmpeg's stdout into it.  In normal mode,
            # FFmpeg opens the file itself and stdout is /dev/null.
            if append:
                try:
                    self._output_fh = open(output_path, "ab")
                except OSError as exc:
                    logger.error(
                        "FfmpegRecorder.start(append): could not open "
                        "output file %s for append: %s",
                        output_path, exc,
                    )
                    self._close_stderr_fh()
                    self._proc = None
                    return
                stdout_target: IO = self._output_fh
            else:
                self._output_fh = None
                stdout_target = subprocess.DEVNULL

            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=stdout_target,
                    stderr=self._stderr_fh if self._stderr_fh else subprocess.DEVNULL,
                    stdin=subprocess.PIPE,  # so we can send 'q' on graceful stop
                    creationflags=getattr(
                        subprocess, "CREATE_NO_WINDOW", 0
                    ),  # no console window on Windows
                )
            except OSError as exc:
                logger.error(
                    "FfmpegRecorder.start: subprocess.Popen failed: %s", exc,
                )
                self._proc = None
                self._close_output_fh()
                self._close_stderr_fh()
                return

            self._output_path = output_path
            self._show_id = show_id
            logger.info(
                "FfmpegRecorder: started recording show_id=%s name=%r "
                "(pid=%d, source=%s, output=%s, stderr=%s)",
                show_id, show_name, self._proc.pid, source_url, output_path,
                self._stderr_log_path,
            )

    def stop(self) -> None:
        """Stop the current recording (idempotent)."""
        with self._lock:
            self._stop_locked()

    def stop_if_recording(self, show_id: int) -> None:
        """
        Stop the recording only if it is still the one for ``show_id``.

        Used by the playout scheduler's post-roll deferred stop: we
        keep recording for 1 second after SHOW_RECORD_END to capture
        the tail of the Icecast output buffer, but if a NEW show has
        already started its own recording in the meantime (back-to-
        back shows) the deferred stop must not interrupt it.  No-op
        in that case.
        """
        with self._lock:
            if self._proc is None or self._show_id != show_id:
                return
            self._stop_locked()

    def _stop_locked(self) -> None:
        """Internal stop body; caller holds ``self._lock``."""
        if self._proc is None:
            return

        proc = self._proc
        output_path = self._output_path
        show_id = self._show_id
        # Null state immediately so a concurrent start() call sees a
        # clean recorder and does not try to stop us again.
        self._proc = None
        self._output_path = None
        self._show_id = None

        stderr_log_path = self._stderr_log_path
        self._close_stderr_fh()
        # NB: close the append-mode output handle AFTER the FFmpeg
        # process has exited (handled below) so the last frames it
        # wrote to its stdout pipe actually make it into the file.

        if proc.poll() is not None:
            tail = self._read_stderr_tail(stderr_log_path)
            logger.warning(
                "FfmpegRecorder: recording for show_id=%s already exited "
                "(rc=%s, output=%s).  Last stderr from %s:\n%s",
                show_id, proc.returncode, output_path, stderr_log_path, tail,
            )
            return

        # Graceful shutdown: send 'q' to FFmpeg's stdin.  FFmpeg
        # interprets this as "finish writing and exit cleanly" — for
        # MP3 there is no container trailer to flush so the file is
        # immediately playable.
        try:
            if proc.stdin is not None:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
        except (OSError, ValueError):
            pass

        try:
            proc.wait(timeout=self._STOP_TIMEOUT_SECONDS)
            if proc.returncode != 0:
                tail = self._read_stderr_tail(stderr_log_path)
                logger.warning(
                    "FfmpegRecorder: stopped recording for show_id=%s "
                    "(rc=%s, output=%s).  Last stderr from %s:\n%s",
                    show_id, proc.returncode, output_path,
                    stderr_log_path, tail,
                )
            else:
                logger.info(
                    "FfmpegRecorder: stopped recording for show_id=%s "
                    "(rc=%s, output=%s)",
                    show_id, proc.returncode, output_path,
                )
        except subprocess.TimeoutExpired:
            logger.warning(
                "FfmpegRecorder: graceful stop timed out for show_id=%s; "
                "killing process",
                show_id,
            )
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.error(
                    "FfmpegRecorder: kill() also timed out for show_id=%s — "
                    "leaving zombie process",
                    show_id,
                )

        # FFmpeg has now exited; safe to close the append-mode output
        # file handle (no further writes possible).
        self._close_output_fh()

    def _close_stderr_fh(self) -> None:
        """Close the stderr log file handle if open."""
        if self._stderr_fh is not None:
            try:
                self._stderr_fh.close()
            except OSError:
                pass
            self._stderr_fh = None

    def _close_output_fh(self) -> None:
        """Close the append-mode output file handle if open."""
        if self._output_fh is not None:
            try:
                self._output_fh.close()
            except OSError:
                pass
            self._output_fh = None

    @staticmethod
    def _read_stderr_tail(
        log_path: Optional[Path], max_bytes: int = 2000,
    ) -> str:
        """Read the tail of the FFmpeg stderr log for diagnostics."""
        if log_path is None:
            return "(no log path)"
        try:
            with open(log_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - max_bytes))
                return fh.read().decode(errors="replace")
        except OSError as exc:
            return f"(could not read stderr log: {exc})"
