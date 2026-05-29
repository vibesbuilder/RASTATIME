"""
PlayoutScheduler — schedule-polling and timer dispatch for RASTATIME playout.

Replaces the Liquidsoap-based PypoFetch/PypoPush/PypoLiqQueue chain with a
simpler, engine-agnostic loop that:

  1. Polls RASTATIME-API every POLL_INTERVAL seconds for the 24-hour schedule.
  2. Arms one threading.Timer per scheduled FileEvent:
       - start timer  → download file → engine.play() + ffmpeg.start()
       - stop  timer  → engine.stop() + ffmpeg.stop()
  3. On each schedule refresh, cancels all pending timers and re-arms
     from the fresh data (handles show edits / deletions gracefully).

Naming note (RASTATIME 2026-05-13)
----------------------------------
This class used to be called ``PlayoutScheduler`` back when local playback ran
through libVLC.  We moved to mpv (libmpv) in May 2026 — the "Vlc" prefix
became actively misleading, so the class was renamed to
``PlayoutScheduler``.  The implementation is engine-agnostic by
construction (it talks to :class:`PlayoutEngine`, not to libVLC or libmpv
directly), so the rename is purely cosmetic.

Icecast streaming is handled by FfmpegStreamer (one instance per configured
stream output).  For each track, FFmpeg reads the same audio file and
streams it to Icecast via the ``icecast://`` protocol — independently of
the local playback engine.

Design references
-----------------
QUEUE_BEHAVIOR.md §3.1, §4.1 (show start HARD mode), §4.2 (show end),
§6.1 (cue_in/cue_out not yet enforced — stop timer uses schedule end_at).
"""
import base64
import logging
import threading
import time
import urllib.request as urllib_request
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from libretime_api_client.v2 import ApiClient

from .config import CACHE_DIR
from .engine.ffmpeg_linein_capture import FfmpegLineinCapture
from .recording_path import build_output_path
from .engine.ffmpeg_streamer import FfmpegStreamer
from .engine.interface import PlayoutEngine, PlayoutState
from .player.events import (
    EventKind,
    FileEvent,
    LineinEvent,
    ShowRecordEvent,
    WebStreamEvent,
)
from .player.schedule import get_schedule
from .source_switcher import SourceState

logger = logging.getLogger(__name__)

# (Removed _MIN_START_LAG — replaced by catch-up logic that checks
# self._playing_key to avoid restarting in-progress tracks.)


class PlayoutScheduler:
    """
    Schedule-driven playout controller.  Engine-agnostic — talks to a
    :class:`PlayoutEngine` (currently the mpv-backed implementation in
    :mod:`engine.mpv_engine`) without knowing which library does the
    actual decoding.

    Thread model
    ------------
    * The main thread calls ``refresh()`` periodically.
    * ``threading.Timer`` daemon threads fire ``_on_start`` / ``_on_stop``
      callbacks at the appropriate wall-clock times.
    * The callbacks call into ``PlayoutEngine``; both python-mpv and
      python-vlc are thread-safe for the operations used here.
    """

    def __init__(
        self,
        engine: PlayoutEngine,
        api_client: ApiClient,
        cache_dir: Optional[Path] = None,
        storage_path: Optional[str] = None,
        stream_outputs: Optional[List[Dict]] = None,
        api_client_v1: Optional["object"] = None,
        read_stream_outputs: Optional[Callable[[], List[Dict]]] = None,
        streaming_handled_externally: bool = False,
    ) -> None:
        self._engine = engine
        self._api_client = api_client
        # Legacy v1 API client used to drive the dashboard "On Air" light:
        # /api/notify-media-item-start-play marks cc_schedule.media_item_played
        # which the dashboard polls to flip the indicator red.
        self._api_client_v1 = api_client_v1
        self._cache_dir = cache_dir or CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        # RASTATIME: direct storage access (bypasses API download)
        self._storage_path = storage_path

        # Active timers: event_key → (start_timer | None, stop_timer | None)
        self._timers: Dict[str, Tuple[Optional[threading.Timer], Optional[threading.Timer]]] = {}
        # Currently armed events, parallel to ``self._timers`` — keyed
        # by the same event_key.  Stored separately (rather than as a
        # third tuple element on ``_timers``) so the lookup is a clean
        # ``dict[str, AnyEvent]`` for code that doesn't care about timer
        # objects.  Used by Phase B.4 #3 (same-device transition) so
        # ``_on_stop`` for show A can ask "is there a same-device
        # LineinEvent B already armed?" without poking around in timer
        # internals.
        self._armed_events: Dict[str, object] = {}
        self._lock = threading.Lock()

        # Track which event key is currently playing so that refresh()
        # doesn't restart an in-progress track every 120 s.
        self._playing_key: Optional[str] = None
        self._current_event: Optional[FileEvent] = None
        self._current_audio_path: Optional[str] = None

        # RASTATIME 2026-05-16 — cached effective dB gain for the
        # currently-playing event.  Source of the value depends on the
        # event type (file → ReplayGain sum; webstream →
        # cc_webstream.input_gain_db; live sources → None).  The
        # streamers and mpv read this back when restarting after a
        # hot-reload or after a DJ-source disconnect, so a previous
        # event's gain does not leak into the new playback.
        #
        # (Was ``_current_replay_gain_db`` before 2026-05-16; renamed
        # when webstream input-gain joined the same plumbing.)
        self._current_gain_db: Optional[float] = None

        # Stream-output hot-reload: the callable lets the scheduler refresh
        # its view of cc_pref every poll cycle and re-instantiate streamers
        # when the user changes settings without needing a service restart.
        self._read_stream_outputs = read_stream_outputs
        self._current_stream_configs: List[Dict] = list(stream_outputs or [])

        # RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C7 follow-up.
        # When the Liquidsoap engine is active, Liquidsoap itself owns
        # the Icecast PUTs (one persistent stream per mount + per codec
        # in rastatime.liq), and the legacy FfmpegStreamer subprocesses
        # would fight Liquidsoap for the same mounts and lose (403
        # "mount taken").  ``streaming_handled_externally=True`` skips
        # both the initial FfmpegStreamer instantiation AND the
        # hot-reload rebuild — the streamer list stays empty, so
        # _start_streamers / _stop_streamers / _start_streamers (which
        # all iterate over self._streamers) silently no-op.
        self._streaming_handled_externally = streaming_handled_externally

        # Source-switcher integration.  Set by __main__ via
        # ``set_source_switcher``.  When non-None and reporting a state
        # other than SCHEDULED, scheduled track-start/stop callbacks
        # don't touch the audio engine — they only update the
        # currently-tracked event so we know what to resume to when
        # the DJ disconnects.
        self._switcher = None
        # Icecast input mounts for live DJ pickup.  Credentials are set
        # by __main__ from libretime.conf (stream.internal_listener.*).
        # The /main and /show mounts gate listener access via URL-auth
        # in icecast.xml, so we need to supply Basic-Auth credentials
        # in the listen URL to be allowed in.
        self._icecast_host = "127.0.0.1"
        self._icecast_port = 8000
        self._listener_user = ""
        self._listener_pass = ""

        # FFmpeg streamers — one per enabled Icecast stream output.
        # Skipped entirely when streaming_handled_externally=True
        # (Liquidsoap engine takes care of all three Icecast mounts
        # from inside rastatime.liq); see Phase C7 wire-up in
        # __main__.py.
        self._streamers: List[FfmpegStreamer] = []
        if self._streaming_handled_externally:
            logger.info(
                "PlayoutScheduler: streaming handled externally — "
                "FFmpeg streamers SKIPPED (%d cc_pref output(s) "
                "delegated to the Liquidsoap subprocess).",
                len(self._current_stream_configs),
            )
        else:
            for cfg in self._current_stream_configs:
                try:
                    streamer = FfmpegStreamer(cfg)
                    self._streamers.append(streamer)
                except RuntimeError as exc:
                    logger.error("Could not create FfmpegStreamer: %s", exc)
            if self._streamers:
                logger.info(
                    "PlayoutScheduler: %d FFmpeg streamer(s) ready for Icecast.",
                    len(self._streamers),
                )
            else:
                logger.info("PlayoutScheduler: no Icecast streamers — local playback only.")

        # RASTATIME 2026-05-12 — Phase B Line-In capture.
        #
        # Lazy-created instance shared across all LineinEvents.  We
        # build it eagerly here (rather than on first use) so any
        # configuration error (missing ffmpeg, bad icecast credentials)
        # surfaces at startup, not at scheduled-air-time.  ``stop()``
        # on an idle instance is a no-op, so it's safe to keep around.
        try:
            self._linein_capture: Optional[FfmpegLineinCapture] = FfmpegLineinCapture()
            # Phase B.4 #1 — wire the auto-restart callback so the
            # capture's watchdog can re-point mpv + the FfmpegStreamer
            # instances at the listen URL after a successful restart
            # (e.g. operator yanked the mic USB cable mid-show).
            # Otherwise the Icecast mount comes back but downstream
            # consumers stay tuned to a now-dead stream.
            self._linein_capture.set_on_restart_callback(
                self._on_linein_capture_restart
            )
            logger.info(
                "PlayoutScheduler: Line-In capture ready -> %s",
                self._linein_capture.listen_url,
            )
        except RuntimeError as exc:
            logger.error(
                "PlayoutScheduler: Line-In capture unavailable (%s) — "
                "Line-In schedule items will be skipped at start time.",
                exc,
            )
            self._linein_capture = None

        # RASTATIME 2026-05-28 — Phase-C5 Teil 2d: Record-per-Show
        # is owned by the Liquidsoap engine's output.file(id="recording")
        # block on the internal bus.  The legacy FfmpegRecorder class
        # (HTTP-tap + lifecycle-watchdog + post-roll-Timer) was deleted
        # — recording is only available in the Liquidsoap engine path.
        # In mpv/VLC engine paths the _on_show_record_* hooks log a
        # warning and silently skip recording (show still plays).
        if self._streaming_handled_externally:
            logger.info(
                "PlayoutScheduler: streaming handled externally — "
                "recording is owned by Liquidsoap output.file from "
                "the internal bus (FfmpegRecorder was deleted in C5).",
            )
            # rastatime.liq's output.file(id="recording") uses default
            # start=true because Liquidsoap-2.4.4 silently swallows
            # `recording.start` when the block was declared with
            # start=false (the file simply never opens, no error).
            # Without an explicit stop here, the sentinel
            # `_uninitialized.mp3` would keep growing from Liquidsoap
            # boot until the first _on_show_record_start hook fires —
            # potentially hours.  Best-effort: silently log if the
            # telnet isn't ready yet (NSSM startup race) — the worst
            # case is a slightly longer sentinel file.
            if hasattr(self._engine, "recording_stop"):
                try:
                    self._engine.recording_stop()
                    logger.info(
                        "PlayoutScheduler: initial recording.stop sent "
                        "to Liquidsoap (silences sentinel-file write "
                        "from boot until first scheduled show).",
                    )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "PlayoutScheduler: initial recording.stop failed "
                        "(Liquidsoap not ready yet?): %s — sentinel "
                        "file will keep growing until first show.",
                        exc,
                    )
        else:
            logger.warning(
                "PlayoutScheduler: legacy engine path (mpv/VLC) — "
                "show recordings will be SKIPPED at start time.  "
                "Recording requires RASTATIME_PLAYOUT_ENGINE=liquidsoap "
                "since C5 Teil 2d deleted FfmpegRecorder.",
            )

        logger.info("PlayoutScheduler initialised (cache_dir=%s)", self._cache_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """
        Fetch the schedule from the API and re-arm all pending timers.

        Any previously armed timers are cancelled first so that edits to
        the schedule take effect immediately.  Stream-output settings in
        cc_pref are also re-read on each refresh so user edits in the
        Frontend take effect within one poll cycle, no service restart.
        """
        # Hot-reload stream outputs from cc_pref BEFORE we touch timers,
        # so the new streamers can pick up an in-progress track immediately.
        self._reload_stream_outputs_if_changed()

        logger.info("PlayoutScheduler: refreshing schedule from API …")
        try:
            events = get_schedule(self._api_client)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("PlayoutScheduler: schedule fetch failed: %s", exc)
            return

        now = datetime.utcnow()
        armed_count = 0
        skipped_past = 0
        skipped_type = 0

        with self._lock:
            self._cancel_all_timers()

            # If the currently-playing event is no longer valid, stop
            # playback now — otherwise the track keeps running until its
            # original end timestamp because the stop-timer we just
            # cancelled was the only thing that would have stopped it.
            #
            # Two "no longer valid" cases:
            #   1. Event was removed from the schedule entirely (e.g. a
            #      future-only show was cancelled).
            #   2. Event is still in the schedule but its end was
            #      truncated to "now" — that's what Scheduler::cancelShow
            #      via removeItems() does to a currently-running item:
            #      it sets DbEnds to nowDT instead of deleting the row,
            #      so the playout stops at the truncated end.
            #
            # How we react depends on which source is on-air right now:
            #
            #   MASTER  → the station owner is broadcasting; cancelling a
            #             show must NOT interrupt them.  Leave engine alone,
            #             only clear the scheduled-track bookkeeping.
            #
            #   SHOW    → a show DJ is on /show, and the very show they
            #             are presenting was just cancelled.  Kick them
            #             off via Icecast admin so the show ends.  The
            #             source-disconnect event handler will transition
            #             the switcher back to SCHEDULED, and the resume
            #             path will find nothing to play (we clear
            #             _current_event below) — i.e. silence, matching
            #             the cancelled state.
            #
            #   SCHEDULED → no DJ active, the scheduled track is the only
            #             audio source.  Stop it immediately.
            if self._playing_key is not None:
                current_evt = events.get(self._playing_key)
                event_gone_or_truncated = (
                    current_evt is None
                    or current_evt.end <= now
                )
                if event_gone_or_truncated:
                    stale_key = self._playing_key
                    reason = (
                        "removed from schedule"
                        if current_evt is None
                        else "truncated to past (show cancelled?)"
                    )
                    dj_state = (
                        self._switcher.current_state
                        if self._switcher is not None
                        else SourceState.SCHEDULED
                    )

                    if dj_state == SourceState.MASTER:
                        logger.info(
                            "Scheduled event %s %s while Master source is "
                            "active — Master stays on-air, clearing bookkeeping.",
                            stale_key, reason,
                        )
                        # Engine/streamers are relaying /main; leave them be.
                    elif dj_state == SourceState.SHOW:
                        logger.info(
                            "Scheduled event %s %s while Show source is "
                            "active — kicking the show DJ via Icecast admin.",
                            stale_key, reason,
                        )
                        self._kick_icecast_source("/show")
                        # The source-disconnect event will transition the
                        # switcher to SCHEDULED and trigger resume; since
                        # we wipe _current_event right after this block,
                        # resume sees no active scheduled track and the
                        # playout falls silent, as expected for a cancel.
                    else:  # SCHEDULED
                        logger.info(
                            "Scheduled event %s %s — stopping playback.",
                            stale_key, reason,
                        )
                        self._engine.stop()
                        self._stop_streamers()

                    # Phase B — if the now-stale event was a Line-In,
                    # also tear down the dshow capture; otherwise the
                    # microphone device stays locked by an orphan
                    # FFmpeg subprocess.
                    if (
                        isinstance(self._current_event, LineinEvent)
                        and self._linein_capture is not None
                    ):
                        self._linein_capture.stop()

                    self._playing_key = None
                    self._current_event = None
                    self._current_audio_path = None

            for key, event in events.items():
                if isinstance(event, FileEvent):
                    end_diff = (event.end - now).total_seconds()
                    if end_diff <= 0:
                        skipped_past += 1
                        continue  # already ended — discard
                    self._arm_file_event(key, event, now)
                    armed_count += 1

                elif isinstance(event, WebStreamEvent):
                    # UC-I3: web streams can be passed directly to VLC
                    # (VLC plays HTTP streams natively).  Only arm if the
                    # event type is a start event.
                    from .player.events import EventKind  # local import to avoid cycles
                    if event.type == EventKind.WEB_STREAM_OUTPUT_START:
                        end_diff = (event.end - now).total_seconds()
                        if end_diff <= 0:
                            skipped_past += 1
                            continue
                        self._arm_webstream_event(key, event, now)
                        armed_count += 1
                    # Buffer start/end and output end events are handled
                    # implicitly by the stop timer.

                elif isinstance(event, LineinEvent):
                    # RASTATIME 2026-05-12 — Phase B: Line-In live input.
                    end_diff = (event.end - now).total_seconds()
                    if end_diff <= 0:
                        skipped_past += 1
                        continue
                    self._arm_linein_event(key, event, now)
                    armed_count += 1

                elif isinstance(event, ShowRecordEvent):
                    # RASTATIME 2026-05-17 — Phase B: Record-per-Show.
                    # ShowRecordEvent is either SHOW_RECORD_START at
                    # show.starts_at or SHOW_RECORD_END at
                    # show.ends_at.  We arm both directions through the
                    # same helper; the helper checks event.type and
                    # routes to start_recording / stop_recording.
                    from .player.events import EventKind  # local import to avoid cycles
                    end_diff = (event.start - now).total_seconds()
                    if end_diff < 0:
                        # END events that already fired are OK to drop
                        # (the recorder is already stopped or
                        # never started); START events that already
                        # fired are also dropped (mid-show restart of
                        # the playout means we cannot capture the
                        # already-elapsed portion anyway).
                        skipped_past += 1
                        continue
                    self._arm_show_record_event(key, event, now)
                    armed_count += 1

                else:
                    skipped_type += 1

        logger.info(
            "PlayoutScheduler: armed=%d  past=%d  other=%d",
            armed_count, skipped_past, skipped_type,
        )

    def shutdown(self) -> None:
        """Cancel all pending timers, stop the engine and all streamers."""
        logger.info("PlayoutScheduler: shutting down …")
        with self._lock:
            self._cancel_all_timers()
        self._engine.stop()
        for streamer in self._streamers:
            streamer.close()
        # RASTATIME 2026-05-12 — also release the Line-In capture so
        # the microphone device handle is freed.  Otherwise it would
        # stay locked until the OS reaped the orphaned ffmpeg subprocess.
        if self._linein_capture is not None:
            self._linein_capture.close()
        # RASTATIME 2026-05-28 — Phase-C5 Teil 2d: gracefully stop any
        # in-flight show recording on the Liquidsoap side so the .mp3
        # is playable (MP3 has no container trailer so it would still
        # be playable without a clean stop, but tidier this way).  In
        # the legacy mpv/VLC engine path recording is unavailable
        # since FfmpegRecorder was deleted, so nothing to stop.
        # Errors are logged but not raised — shutdown must complete.
        if self._streaming_handled_externally:
            try:
                self._engine.recording_stop()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Shutdown: Liquidsoap recording_stop failed: %s", exc,
                )
        logger.info("PlayoutScheduler: shutdown complete")

    # ------------------------------------------------------------------
    # Timer management  (must hold self._lock)
    # ------------------------------------------------------------------

    def _cancel_all_timers(self) -> None:
        for key, (start_t, stop_t) in list(self._timers.items()):
            if start_t is not None:
                start_t.cancel()
            if stop_t is not None:
                stop_t.cancel()
        self._timers.clear()
        # Parallel armed-events lookup is cleared in lockstep so
        # ``_on_stop``'s same-device-follow-up check sees a consistent
        # snapshot of "what's armed right now" (rather than ghosts of
        # the previous refresh).
        self._armed_events.clear()

    def _arm_file_event(
        self,
        key: str,
        event: FileEvent,
        now: datetime,
    ) -> None:
        start_delay = (event.start - now).total_seconds()
        stop_delay = (event.end - now).total_seconds()

        start_t: Optional[threading.Timer] = None

        if start_delay >= 0:
            # Event starts in the future — arm a timer at the scheduled time.
            start_t = threading.Timer(start_delay, self._on_file_start, args=(key, event))
            start_t.daemon = True
            start_t.start()
            logger.debug(
                "Armed FileEvent %s: starts in %.1fs  track=%r",
                key, start_delay, event.track_title,
            )

        elif key != self._playing_key:
            # Event has already started but we are NOT playing it.
            # This covers: (a) service restart during a running show,
            # (b) first schedule refresh that discovers an in-progress track,
            # (c) late schedule detection.
            # Start playback immediately (delay=0).
            logger.info(
                "Catch-up: in-progress event %s (started %.0fs ago)  track=%r",
                key, -start_delay, event.track_title,
            )
            start_t = threading.Timer(0, self._on_file_start, args=(key, event))
            start_t.daemon = True
            start_t.start()

        else:
            # We are already playing this event — don't restart it.
            logger.debug(
                "Skipping re-arm for currently-playing event %s  track=%r",
                key, event.track_title,
            )

        stop_t = threading.Timer(stop_delay, self._on_stop, args=(key,))
        stop_t.daemon = True
        stop_t.start()

        self._timers[key] = (start_t, stop_t)
        self._armed_events[key] = event

    def _arm_webstream_event(
        self,
        key: str,
        event: WebStreamEvent,
        now: datetime,
    ) -> None:
        start_delay = (event.start - now).total_seconds()
        stop_delay = max(0.0, (event.end - now).total_seconds())

        start_t: Optional[threading.Timer] = None

        if start_delay >= 0:
            start_t = threading.Timer(start_delay, self._on_webstream_start, args=(key, event))
            start_t.daemon = True
            start_t.start()
        elif key != self._playing_key:
            logger.info(
                "Catch-up: in-progress web stream %s (started %.0fs ago)",
                key, -start_delay,
            )
            start_t = threading.Timer(0, self._on_webstream_start, args=(key, event))
            start_t.daemon = True
            start_t.start()

        stop_t = threading.Timer(stop_delay, self._on_stop, args=(key,))
        stop_t.daemon = True
        stop_t.start()

        self._timers[key] = (start_t, stop_t)
        self._armed_events[key] = event
        logger.debug(
            "Armed WebStreamEvent %s: start=%.1fs stop=%.1fs  uri=%s",
            key, start_delay, stop_delay, event.uri,
        )

    def _arm_linein_event(
        self,
        key: str,
        event: LineinEvent,
        now: datetime,
    ) -> None:
        """
        Arm start + stop timers for a Line-In schedule slot (Phase B).

        Symmetric with :meth:`_arm_webstream_event`.  A live microphone
        has no concept of "started N seconds ago" the way a file does,
        but if the schedule slot already opened we still want to bring
        the capture online for the remaining minutes — catch-up just
        means "start now instead of waiting for the (already-past)
        start timestamp".
        """
        start_delay = (event.start - now).total_seconds()
        stop_delay = max(0.0, (event.end - now).total_seconds())

        start_t: Optional[threading.Timer] = None

        if start_delay >= 0:
            start_t = threading.Timer(
                start_delay, self._on_linein_start, args=(key, event)
            )
            start_t.daemon = True
            start_t.start()
        elif key != self._playing_key:
            logger.info(
                "Catch-up: in-progress line-in %s (started %.0fs ago)  name=%r",
                key, -start_delay, event.name,
            )
            start_t = threading.Timer(
                0, self._on_linein_start, args=(key, event)
            )
            start_t.daemon = True
            start_t.start()

        stop_t = threading.Timer(stop_delay, self._on_stop, args=(key,))
        stop_t.daemon = True
        stop_t.start()

        self._timers[key] = (start_t, stop_t)
        self._armed_events[key] = event
        logger.debug(
            "Armed LineinEvent %s: start=%.1fs stop=%.1fs  device=%s",
            key, start_delay, stop_delay, event.device_id,
        )

    def _arm_show_record_event(
        self,
        key: str,
        event: ShowRecordEvent,
        now: datetime,
    ) -> None:
        """
        RASTATIME 2026-05-17 - Phase B: Record-per-Show.

        Arm a single timer that fires either
        :meth:`_on_show_record_start` or :meth:`_on_show_record_end`
        depending on event.type.  A pure point-in-time event (no
        duration), so we only need one timer.
        """
        delay = max(0.0, (event.start - now).total_seconds())
        if event.type == EventKind.SHOW_RECORD_START:
            callback = self._on_show_record_start
        else:
            callback = self._on_show_record_end

        t = threading.Timer(delay, callback, args=(key, event))
        t.daemon = True
        t.start()

        # Slot the (None, t) tuple into the standard timer registry so
        # shutdown()'s _cancel_all_timers can cancel it.  The first
        # slot (start_t) is conventionally the start timer; for a
        # point-in-time event we put the callback in the second slot
        # to match the existing tuple shape used by _on_stop's lookups.
        self._timers[key] = (None, t)
        self._armed_events[key] = event
        logger.debug(
            "Armed ShowRecordEvent %s: type=%s delay=%.1fs show_id=%s name=%r",
            key, event.type.value, delay, event.show_id, event.show_name,
        )

    # ------------------------------------------------------------------
    # Timer callbacks (run in daemon threads)
    # ------------------------------------------------------------------

    def _on_file_start(self, key: str, event: FileEvent) -> None:
        logger.info(
            "PLAY  %s  |  %r  |  show: %s",
            key,
            event.track_title or event.id,
            event.show_name,
        )
        local = self._ensure_file_cached(event)
        if local is None:
            logger.error("Cannot play %s — file could not be downloaded", key)
            return

        # Track which event is "current" regardless of whether a DJ is
        # overriding right now — this is what we resume to once the DJ
        # disconnects.  These four lines must run BEFORE the DJ-active
        # short-circuit below, otherwise switch_audio_source(SCHEDULED)
        # at disconnect time would not know what to fall back to.
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = str(local)
        # RASTATIME 2026-05-16 — cache the effective gain for the
        # resume path.  For file events the value is the precomputed
        # ReplayGain sum of ``cc_files.replay_gain`` and
        # ``cc_pref.replay_gain_modifier`` (see player/schedule.py).
        # ``None`` ⇒ replay-gain globally disabled; engines/streamers
        # skip the volume filter.
        self._current_gain_db = event.replay_gain

        # If a DJ source is currently dominant, do not touch the audio
        # engine — the DJ stream stays on air.  We've already recorded
        # the current event so the scheduled track can be picked up
        # when the DJ disconnects.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            logger.info(
                "Track %s queued — %s source active, scheduled audio held back",
                key, self._switcher.current_state.value,
            )
            self._notify_media_started(event.row_id)
            return

        # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1.  Give the
        # previous track up to 200 ms to flush its last frames before
        # we hard-stop mpv + the FFmpeg streamers.  Without this, the
        # last 1–2 s of short tracks (4–10 s) regularly get clipped
        # because the scheduler-clock fires this _on_file_start event
        # slightly before mpv's end-file event arrives.  If mpv is
        # already stopped (common case: previous track ended naturally
        # before this fires) the wait returns immediately.
        self._engine.wait_until_stopped(timeout=0.5)

        # HARD start (QUEUE_BEHAVIOR §4.1): stop whatever is playing first.
        self._engine.stop()
        self._stop_streamers()

        # Calculate seek offset for catch-up (in-progress tracks)
        now = datetime.utcnow()
        elapsed = (now - event.start).total_seconds()
        seek_seconds = max(0.0, elapsed) if elapsed > 1.0 else 0.0

        # RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C6 Teil 2.
        # Forward track metadata to the engine so the Liquidsoap
        # backend can attach it via annotate: + propagate to the
        # output.icecast blocks for live ICY metadata in listener
        # clients.  mpv/VLC engines accept the parameter but ignore
        # it (FfmpegStreamer continues to handle their Icecast
        # metadata path separately).
        track_metadata = {
            "title":     event.track_title or "",
            "artist":    event.artist_name or "",
            "show_name": event.show_name or "",
        }
        # RASTATIME 2026-05-28 — Phase-D Stück-B: pass cue_out so the
        # Liquidsoap engine's _build_annotate_uri can detect short
        # tracks (jingles, StationIDs under 8 s) and add the
        # ``liq_cross_duration="0.0"`` metadata override that disables
        # the crossfade fade-in/fade-out zones for that track only.
        # Without cue_out, short tracks get eaten by the 1-s fade
        # zones and are barely audible.  (mpv-engine ignores cue_out
        # in this code path — mpv knows the natural file-end on its
        # own; the param is harmless for mpv.)
        self._engine.play(
            str(local),
            cue_in=event.cue_in or 0.0,
            cue_out=event.cue_out,
            gain_db=event.replay_gain,
            metadata=track_metadata,
        )

        # Start FFmpeg streamers in parallel (same audio file → Icecast)
        self._start_streamers(
            str(local),
            seek_seconds=seek_seconds,
            gain_db=event.replay_gain,
        )

        # Notify the legacy v1 API that this schedule row started playing.
        # This sets cc_schedule.media_item_played = true, which the
        # dashboard polls to switch the "On Air" indicator red.
        # Run in a daemon thread so a slow/hung HTTP call cannot delay
        # the next track start.
        self._notify_media_started(event.row_id)

    def _on_webstream_start(self, key: str, event: WebStreamEvent) -> None:
        # RASTATIME 2026-05-16 — log the per-stream input gain alongside
        # the URI so it's obvious from the journal what level adjustment
        # is being applied to this source.
        gain_for_log = (
            f"{event.input_gain_db:+.2f}dB"
            if event.input_gain_db is not None and abs(event.input_gain_db) > 0.001
            else "none"
        )
        logger.info(
            "PLAY (web stream)  %s  |  uri=%s  |  gain=%s  |  show: %s",
            key, event.uri, gain_for_log, event.show_name,
        )

        # Track which event is "current" regardless of whether a DJ
        # source is overriding right now.  These four lines must run
        # BEFORE the DJ-active short-circuit below — otherwise
        # ``_resume_scheduled_locked`` at DJ-disconnect time would not
        # know what to fall back to.  Same pattern as _on_file_start.
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = event.uri
        # RASTATIME 2026-05-16 — cache the webstream's input-gain so the
        # resume path (DJ disconnect, hot-reload) reapplies it after the
        # stop/restart, instead of falling back to "no gain".
        self._current_gain_db = event.input_gain_db

        # Drive the dashboard "On Air" light (web streams have row_id too)
        row_id = getattr(event, "row_id", None)
        if row_id is not None:
            self._notify_media_started(row_id)

        # If a DJ source is currently dominant, do NOT touch the audio
        # engine — DJ audio stays on air.  We've already recorded the
        # current event above so the web stream can be resumed when
        # the DJ disconnects.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            logger.info(
                "Web stream %s queued — %s source active, "
                "scheduled audio held back",
                key, self._switcher.current_state.value,
            )
            return

        # RASTATIME 2026-05-29 — Phase E: dual-engine webstream handling.
        # Liquidsoap-Engine path (streaming_handled_externally=True):
        # the .liq script has a dedicated input.http source ("webstream")
        # that we drive via telnet wrappers — set URL, set gain, start.
        # The source goes ``source.is_ready=true`` after max_buffer (10 s
        # default) of audio has buffered, at which point the switch
        # operator in the .liq flips the bus from scheduled (silence_
        # fallback) to webstream automatically.  We also clear the
        # scheduled queue so the previous track doesn't linger in the
        # background during the buffer-up phase.
        #
        # Legacy mpv/VLC path: unchanged Pypo-side behaviour — engine.play
        # opens VLC/mpv against the HTTP URL directly, and the three
        # FfmpegStreamer subprocesses re-encode the same URL to Icecast.
        # This path stays as a fallback until both engines are removed
        # (Phase E + F unblock the mpv/VLC deletion per BACKLOG).
        if self._streaming_handled_externally:
            # Phase E (2026-05-29) — Liquidsoap engine path.
            # We do NOT call wait_until_stopped here: Liquidsoap's queue
            # handles its own gapless transitions and we want the
            # scheduled-track-to-webstream handover to happen as soon as
            # input.http has buffered enough.
            self._engine.stop()  # deferred-stop, clears request.queue
            self._engine.webstream_start(
                event.uri, gain_db=event.input_gain_db,
            )
            # No _start_streamers — Liquidsoap owns the Icecast PUTs
            # from inside the .liq, and the webstream audio rides the
            # same bus that the output.icecast + output.file blocks tap.
        else:
            # Legacy mpv/VLC path — unchanged from the Phase-C era.
            # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1 (see
            # _on_file_start for the rationale).  Short scheduled tracks
            # just before a webstream item were the prime offender for
            # the tail-cut symptom.
            self._engine.wait_until_stopped(timeout=0.5)

            self._engine.stop()
            self._stop_streamers()
            self._engine.play(event.uri, cue_in=0.0, gain_db=event.input_gain_db)
            # Web streams: FFmpeg can also stream an HTTP URL to Icecast.
            # The per-stream input gain (cc_webstream.input_gain_db) is
            # applied via the same -af volume=<dB>dB mechanism as file
            # ReplayGain (see FfmpegStreamer.start()'s gain_db parameter).
            self._start_streamers(event.uri, gain_db=event.input_gain_db)

    def _resolve_linein_device(self, event: "LineinEvent") -> Optional[str]:
        """
        Resolve a Line-In event's device, with a friendly-name fallback.

        RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot.

        Windows USB-audio endpoint GUIDs (the saved ``device_id``) are
        not stable across reboots in all driver / port combinations
        (observed empirically with Jabra USB).  If the saved GUID no
        longer resolves to an active device, fall back to matching by
        the saved friendly name (``device_name``) — same physical
        device, same OS label, different endpoint GUID.

        Returns
        -------
        Optional[str]
            * The original ``event.device_id`` if it still resolves.
            * A different stable_id if the name fallback hit a renamed
              endpoint — caller should pass this to ``start()`` so
              FFmpeg's dshow input string uses the right GUID.
            * The original ``event.device_id`` again as a graceful
              degradation when the AudioDeviceManager isn't wired or
              fails — letting the existing error path fire below.
            * ``None`` only when the manager IS wired AND neither
              GUID nor name match; caller should not attempt start().
        """
        try:
            import audio.soundcard._registry as _reg   # noqa: PLC0415
        except ImportError:
            return event.device_id or None
        mgr = _reg.default_manager
        if mgr is None:
            return event.device_id or None

        from audio.soundcard.interface import AudioDeviceKind  # noqa: PLC0415
        try:
            dev = mgr.find_device_by_id_or_name(
                event.device_id,
                getattr(event, "device_name", "") or "",
                AudioDeviceKind.INPUT,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Linein '%s': device lookup raised %s; falling through to "
                "the original device_id %r.",
                event.name, exc, event.device_id,
            )
            return event.device_id or None

        if dev is None:
            return None

        if dev.stable_id != (event.device_id or "").strip().lower():
            logger.warning(
                "Linein '%s': saved device_id %r no longer resolves; "
                "name-fallback matched %r (stable_id=%s).  The schedule "
                "will use the new id for this run; the operator should "
                "re-save the device picker so future shows use it "
                "without the fallback step.",
                event.name, event.device_id, dev.name, dev.stable_id,
            )
        return dev.stable_id

    def _on_linein_start(self, key: str, event: LineinEvent) -> None:
        """
        Bring a scheduled Line-In on air (Phase B).

        Pipeline:

          FFmpegLineinCapture → /linein-capture  →  mpv (local monitor)
                                              \\
                                               → 3× FfmpegStreamer →
                                                 rastatime192 / -aac / -ogg

        The capture itself runs the same source-switcher-aware "queue
        but don't override DJ" pattern as :meth:`_on_file_start` /
        :meth:`_on_webstream_start`.  Specifically: we DO start the
        capture process even when a DJ is active, because mpv would
        otherwise have nothing to fall back to at DJ-disconnect time
        — but we don't repoint mpv or the streamers, so the DJ stream
        stays on air.  ``switch_audio_source(SCHEDULED)`` /
        :meth:`_resume_scheduled_locked` then wires the listeners up.

        Same-device transition shortcut (Phase B.4 #3 — 2026-05-13)
        ----------------------------------------------------------
        If the PREVIOUS event was already a LineinEvent against the
        same physical device AND the capture is still running, this
        is a "back-to-back same-mic show change" — keep the capture,
        mpv playback, and three FfmpegStreamer instances all alive.
        Zero audio bounce, no dshow re-acquisition race.  The earlier
        event's ``_on_stop`` is also same-device-aware and skips its
        own teardown in that situation, so this shortcut works
        regardless of which timer fired first.
        """
        logger.info(
            "PLAY (line-in)  %s  |  name=%r device=%s  |  show: %s",
            key, event.name, event.device_id, event.show_name,
        )

        if self._linein_capture is None:
            logger.error(
                "Line-In %s cannot start: FfmpegLineinCapture failed to "
                "initialise at startup (likely missing ffmpeg).  Slot "
                "stays silent.", key,
            )
            return

        # Capture the OLD bookkeeping BEFORE we overwrite it — we need
        # it for the same-device-transition check below.
        prev_event = self._current_event
        same_device_transition = (
            isinstance(prev_event, LineinEvent)
            and prev_event.device_id == event.device_id  # type: ignore[attr-defined]
            and self._linein_capture.is_running
        )

        # Update playing-event bookkeeping unconditionally — must
        # happen BEFORE the DJ-active short-circuit, same pattern as
        # the file / webstream handlers.
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = self._linein_capture.listen_url

        # Drive the dashboard "On Air" light for the new row.
        row_id = getattr(event, "row_id", None)
        if row_id is not None:
            self._notify_media_started(row_id)

        if same_device_transition:
            logger.info(
                "Line-In %s: same-device transition (device=%s) — keeping "
                "the running capture, mpv playback, and streamers alive; "
                "no audio-pipeline bounce.",
                key, event.device_id,
            )
            return

        # Always start the capture — it pushes to /linein-capture
        # regardless of whether a DJ is currently overriding the
        # downstream playback.  Cheap to keep running; cheap to stop.
        # FfmpegLineinCapture.start() is itself same-device-idempotent,
        # so this is safe even if we got here because the previous
        # event was a LineinEvent that crashed mid-show — the watchdog
        # may have already restored the capture.
        resolved_device_id = self._resolve_linein_device(event)
        if not resolved_device_id:
            logger.error(
                "Line-In %s: device %r unavailable (and no name-fallback "
                "matched name=%r) — leaving capture stopped.",
                key, event.device_id,
                getattr(event, "device_name", "") or "",
            )
            return
        try:
            self._linein_capture.start(resolved_device_id)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Line-In %s: capture start failed for device %s: %s",
                key, resolved_device_id, exc,
            )
            return

        # If a DJ source is currently dominant, leave the audio engine
        # and outgoing streamers on the DJ feed.  Capture is running
        # though, so when the DJ disconnects, the resume path will
        # point mpv + streamers at the listen URL we just set.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            logger.info(
                "Line-In %s queued — %s source active, capture running "
                "but local/output stream stays on DJ feed.",
                key, self._switcher.current_state.value,
            )
            return

        # SCHEDULED path: tell the local-playback engine to consume the
        # capture's listen URL.  Brief silence (~0.5 s) while
        # /linein-capture's burst buffer fills, identical to the
        # Master/Show source-switch behavior.
        #
        # RASTATIME 2026-05-29 — Phase F: dual-engine line-in handling.
        # Liquidsoap-Engine path (streaming_handled_externally=True):
        # the .liq script has a dedicated input.http source ("linein")
        # bound at render-time to the FfmpegLineinCapture listen URL.
        # We tell Liquidsoap to start consuming via telnet — the bus-
        # switch flips from scheduled to linein once max_buffer (10 s)
        # of audio has buffered.  FfmpegLineinCapture itself was
        # already started above with the device GUID.
        #
        # Legacy mpv/VLC path: unchanged — engine.play() points VLC at
        # the listen URL and FfmpegStreamer re-encodes to Icecast.
        # This path stays as a fallback until mpv-engine code is
        # deleted (post-Phase-F per BACKLOG).
        if self._streaming_handled_externally:
            # Phase F — Liquidsoap engine path.
            self._engine.stop()  # clear scheduled queue (deferred-stop)
            self._engine.linein_start()
            # No _start_streamers — Liquidsoap owns the Icecast PUTs.
        else:
            # Legacy mpv/VLC path — unchanged from Phase B.
            # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1 (see
            # _on_file_start for the rationale).
            self._engine.wait_until_stopped(timeout=0.5)

            self._engine.stop()
            self._stop_streamers()
            self._engine.play(self._linein_capture.listen_url, cue_in=0.0)
            self._start_streamers(self._linein_capture.listen_url)

    def _on_linein_capture_restart(self) -> None:
        """
        Callback fired by :class:`FfmpegLineinCapture`'s watchdog after a
        successful auto-restart of the dshow subprocess (Phase B.4 #1 —
        device unplugged mid-show).

        When FFmpeg dies, mpv sees the HTTP stream disconnect and logs
        ``"Stream ends prematurely"`` followed by ``end-file`` — i.e.
        mpv is now idle.  The three FfmpegStreamer instances reading
        the same /linein-capture mount likewise lose their input.
        Just respawning FFmpeg fixes the *Icecast source* but not the
        downstream consumers; they would stay tuned to a dead stream
        until the next 120-s schedule poll re-armed everything.

        This callback re-points mpv and the streamers at the (now
        live again) listen URL — same wiring as ``_on_linein_start``'s
        SCHEDULED path, minus the bookkeeping.  Runs on the watchdog
        thread; takes the scheduler lock so a parallel ``refresh()``
        cannot tear things down underneath us.

        Idempotent and safe-no-op if:

          * No LineinEvent is currently the playing event (e.g. the
            Show ended exactly during the 5-s restart back-off and
            ``_on_stop`` already ran).
          * A non-SCHEDULED source is dominant — DJ or Master takes
            priority; capture is alive but mpv/streamers stay on the
            DJ feed.  When the DJ disconnects, ``_resume_scheduled_locked``
            will pick up the (still running) capture.
        """
        with self._lock:
            if not isinstance(self._current_event, LineinEvent):
                logger.info(
                    "Line-In capture restart callback: no LineinEvent is "
                    "the playing event right now — nothing to re-wire.",
                )
                return

            if (
                self._switcher
                and self._switcher.current_state != SourceState.SCHEDULED
            ):
                logger.info(
                    "Line-In capture restart callback: %s source dominant "
                    "— capture is back, but local/output stay on that feed.",
                    self._switcher.current_state.value,
                )
                return

            if self._linein_capture is None:
                return  # defensive; should not happen if callback fired

            listen_url = self._linein_capture.listen_url
            logger.info(
                "Line-In capture restart callback: re-pointing mpv + "
                "streamers at %s", listen_url,
            )
            self._engine.stop()
            self._stop_streamers()
            self._engine.play(listen_url, cue_in=0.0)
            self._start_streamers(listen_url)

    # ------------------------------------------------------------------
    # Show-record callbacks (Phase B / ARCHITECTURE Section 23.13)
    # ------------------------------------------------------------------

    def _on_show_record_start(self, key: str, event: ShowRecordEvent) -> None:
        """
        RASTATIME 2026-05-28 — Phase-C5 Teil 2d: Record-per-Show start
        handler.  Recording is owned by Liquidsoap's ``output.file
        (id="recording", …)`` block on the internal bus.  Pypo's role
        is reduced to:

          1. Resolve the recording-folder via the API.
          2. Build the per-show output path (date / time / sanitised
             show-name) using :func:`recording_path.build_output_path`.
          3. Ensure the parent directory exists (Liquidsoap's
             output.file does not always auto-create).
          4. Call ``engine.recording_start(forward_slash_path)``.

        Failure modes (no folder, bad path, telnet down) are logged
        and silently skipped — the show plays normally, only the
        recording is missing.

        Legacy mpv/VLC engine path (``streaming_handled_externally=
        False``): logs a warning and silently skips.  Recording was
        only ever implemented for the deleted FfmpegRecorder; with
        that gone, recording requires the Liquidsoap engine.

        Compared to the deleted FfmpegRecorder lifecycle, the
        Liquidsoap path has:
          * No HTTP-source-tap (recording is on the same internal bus
            as the Icecast outputs)
          * No retry-on-404 (no HTTP source to fail)
          * No mid-show watchdog respawn (no subprocess to crash)
          * No post-roll Timer (no HTTP-buffering lag to compensate)
        """
        if not self._streaming_handled_externally:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s name=%r): "
                "recording requires RASTATIME_PLAYOUT_ENGINE=liquidsoap "
                "since C5 Teil 2d deleted FfmpegRecorder.",
                key, event.show_id, event.show_name,
            )
            return

        folder = self._fetch_recording_folder()
        if not folder:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s name=%r): "
                "no recording folder configured in Settings -> Local Machine",
                key, event.show_id, event.show_name,
            )
            return

        try:
            output_path = build_output_path(
                Path(folder), event.show_starts_at, event.show_name,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s): could not "
                "build output path: %s",
                key, event.show_id, exc,
            )
            return

        # Liquidsoap's output.file may or may not auto-create the
        # parent dir depending on encoder + platform; do it defensively
        # so a fresh per-day folder always exists.  mkdir(parents=True,
        # exist_ok=True) is idempotent.
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s): could not "
                "create directory %s: %s",
                key, event.show_id, output_path.parent, exc,
            )
            return

        # Liquidsoap's telnet wire-form rejects backslashes.  Windows
        # paths come out of pathlib with ``\\`` separators; convert to
        # forward-slashes here (Liquidsoap on Windows handles ``C:/...``
        # fine on the file-system side).
        liq_path = str(output_path).replace("\\", "/")

        logger.info(
            "PLAY (show-record start, Liquidsoap)  %s  |  show_id=%s "
            "name=%r  |  output=%s",
            key, event.show_id, event.show_name, output_path,
        )
        try:
            self._engine.recording_start(liq_path)
        except (OSError, ConnectionError, ValueError) as exc:
            logger.error(
                "Show-record start failed (Liquidsoap telnet, "
                "key=%s show_id=%s name=%r): %s",
                key, event.show_id, event.show_name, exc,
            )

    def _on_show_record_end(self, key: str, event: ShowRecordEvent) -> None:
        """
        RASTATIME 2026-05-28 — Phase-C5 Teil 2d: Record-per-Show end
        handler.  Calls ``engine.recording_stop()`` synchronously —
        no post-roll Timer needed because Liquidsoap's ``output.file``
        is on the SAME internal bus as the Icecast outputs (the
        deleted FfmpegRecorder's 1 s post-roll was a workaround for
        HTTP-source-buffering lag that doesn't apply to the bus tap).

        Legacy mpv/VLC engine path: no-op.  See
        :meth:`_on_show_record_start` for the recording-requires-
        Liquidsoap design decision.
        """
        if not self._streaming_handled_externally:
            return

        logger.info(
            "STOP (show-record end, Liquidsoap)  %s  |  show_id=%s "
            "name=%r",
            key, event.show_id, event.show_name,
        )
        try:
            self._engine.recording_stop()
        except (OSError, ConnectionError) as exc:
            logger.error(
                "Show-record stop failed (Liquidsoap telnet): %s "
                "(key=%s show_id=%s name=%r)",
                exc, key, event.show_id, event.show_name,
            )

    def _fetch_recording_folder(self) -> Optional[str]:
        """
        GET /api/v2/recording-folder → str folder
        (empty string when unconfigured).

        Returns None on any error so the caller treats the recording
        as "not configured" and skips silently.

        NB the endpoint lives at the v2 root rather than under
        ``preferences/...`` because ``router.register("preferences",
        PreferenceViewSet)`` claims that whole subtree for a REST
        detail view (with an integer pk) and would 404 any explicit
        sibling path before this handler is consulted.
        """
        try:
            resp = self._api_client.session.get(
                "/api/v2/recording-folder",
                timeout=3,
            )
            if resp.status_code != 200:
                return None
            folder = (resp.json().get("folder") or "").strip()
            return folder or None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("_fetch_recording_folder failed: %s", exc)
            return None

    def _on_stop(self, key: str) -> None:
        logger.info("STOP  %s", key)

        # Phase B.4 race fix #1 — only the currently-playing event
        # tears anything down.  See the back-to-back race in the
        # original B.4 follow-up: a finishing event A and a
        # next-event B may fire on the same wallclock instant, and
        # Python's threading.Timer makes no ordering guarantee.  If B
        # grabbed the spotlight first (already swapped _playing_key /
        # _current_event), then we are no longer the playing event and
        # any audio-layer teardown would silently kill B's freshly
        # spawned pipeline.
        if self._playing_key != key:
            return

        was_linein = isinstance(self._current_event, LineinEvent)
        cur_device = (
            self._current_event.device_id  # type: ignore[attr-defined]
            if was_linein else None
        )

        # RASTATIME 2026-05-29 — Phase E: webstream stop-detection.
        # When the stopping event is a WebStreamEvent in Liquidsoap-Mode,
        # we route the teardown through engine.webstream_stop() (closes
        # the input.http source) instead of engine.stop() (which would
        # be a no-op on the input.http and wouldn't disconnect the HTTP
        # session — input.http would keep buffering and the switch would
        # stay on webstream into the next show's silence).  Must be
        # captured BEFORE the bookkeeping reset further down.
        was_webstream = isinstance(self._current_event, WebStreamEvent)

        # Phase B.4 race fix #2 — same-device LineinEvent follow-up.
        # If we WERE the playing event AND another LineinEvent against
        # the same device is already armed with a live start-timer
        # (back-to-back shows that share a mic), defer everything to
        # B's _on_linein_start: keep the FFmpeg-dshow capture, the
        # mpv-monitor playback, and the three FfmpegStreamer instances
        # all alive.  B's handler will see ``self._current_event`` is
        # still us (a LineinEvent with the same device_id) and take the
        # same-device-transition shortcut — net result is a pure
        # bookkeeping swap with zero audio bounce.
        #
        # We deliberately do NOT clear our own bookkeeping in this
        # branch — leaving _playing_key / _current_event in place is
        # exactly what makes B's same-device check fire.
        if was_linein and cur_device is not None and self._linein_capture is not None:
            for other_key, other_event in self._armed_events.items():
                if other_key == key:
                    continue
                if not isinstance(other_event, LineinEvent):
                    continue
                if other_event.device_id != cur_device:
                    continue
                start_t, _ = self._timers.get(other_key, (None, None))
                if start_t is not None and start_t.is_alive():
                    logger.info(
                        "STOP %s: same-device follow-up %s armed (device=%s) "
                        "— skipping audio teardown; bookkeeping handoff "
                        "happens when %s's start timer fires.",
                        key, other_key, cur_device, other_key,
                    )
                    return

        self._playing_key = None
        self._current_event = None
        self._current_audio_path = None

        # Stop the Line-In capture: at this point we know we ARE the
        # event being torn down AND no same-device successor needs the
        # capture alive.  Safe to call even when no capture is running
        # (idempotent).
        if was_linein and self._linein_capture is not None:
            self._linein_capture.stop()

        # If a DJ source is currently dominant, leave the engine alone —
        # the DJ audio stays on air.  Only the scheduled-event bookkeeping
        # above still happens.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            return

        # RASTATIME 2026-05-29 — Phase F: linein-specific teardown.
        # In Liquidsoap-Mode a linein-event uses input.http (not the
        # request.queue), so engine.stop() alone would not close the
        # HTTP session.  Call linein_stop() explicitly so the bus-
        # switch falls through to scheduled.  FfmpegLineinCapture.stop()
        # already happened above (line ~1349) — that's the dshow
        # subprocess side; this is the Liquidsoap-source side.
        if was_linein and self._streaming_handled_externally:
            self._engine.linein_stop()
            # No further engine.stop() / wait_until_stopped — the
            # linein had its own source path that's now closed.
            self._stop_streamers()  # no-op in Liquidsoap-Mode
            return

        # RASTATIME 2026-05-29 — Phase E: webstream-specific teardown.
        # In Liquidsoap-Mode a webstream-event uses input.http (not the
        # request.queue), so engine.stop() (which sends scheduled.skip)
        # would not close the HTTP session.  Call webstream_stop()
        # explicitly to tear down the input.http and let the switch
        # fall through to scheduled.
        if was_webstream and self._streaming_handled_externally:
            self._engine.webstream_stop()
            # No further engine.stop() / wait_until_stopped — the
            # webstream had its own source path that's now closed.
            # The Pypo _stop_streamers no-op below stays for API
            # symmetry (it's already a no-op in Liquidsoap-Mode).
            self._stop_streamers()
            return

        # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1 (follow-up).
        # The _on_stop handler is the SECOND track-end stop path, fired
        # by the track-end Timer just as _on_*_start fires for the next
        # event.  Without a wait here the scheduler-clock-driven mpv
        # stop cut short-track tails by 1–2 s.  Same 200 ms bounded
        # wait as in _on_*_start so a track that's already at EOF
        # returns immediately and a still-decoding tail gets a brief
        # grace period before the hard-stop.
        if self._engine.get_state() == PlayoutState.PLAYING:
            self._engine.wait_until_stopped(timeout=0.5)
            self._engine.stop()
        self._stop_streamers()

    # ------------------------------------------------------------------
    # FFmpeg streamer management
    # ------------------------------------------------------------------

    def _start_streamers(
        self,
        audio_path: str,
        *,
        seek_seconds: float = 0.0,
        gain_db: Optional[float] = None,
    ) -> None:
        """Start all FFmpeg Icecast streamers for the given audio file.

        RASTATIME 2026-05-16 — ``gain_db`` is a generic per-event dB
        offset that each streamer applies as a ``-af volume=<dB>dB``
        filter (see FfmpegStreamer.start()).  Source of the value
        depends on the calling event type:

          * File events: precomputed ReplayGain sum.
          * Webstream events: ``cc_webstream.input_gain_db``.
          * Live sources (Master/Show, Linein): ``None`` (no gain).

        (Was ``replay_gain_db`` before 2026-05-16; renamed when
        webstream input-gain joined the same plumbing.)
        """
        for streamer in self._streamers:
            try:
                streamer.start(
                    audio_path,
                    seek_seconds=seek_seconds,
                    gain_db=gain_db,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error("FFmpeg streamer start failed: %s", exc)

    def _stop_streamers(self) -> None:
        """
        Stop all running FFmpeg Icecast streamers in parallel.

        RASTATIME 2026-05-25 — was sequential; that cost ~500 ms per
        streamer (3 × 500 = ~1.5 s) on every track change, directly
        bloating the next-track mpv-start latency.  The visible
        symptom was scheduled tracks getting cut 1–2 s before their
        actual cue_out because mpv only got to play (slot – 1.5 s).
        Running the three stops in worker threads + joining brings
        the total wait down to roughly the cost of the slowest
        single streamer (~500 ms instead of ~1.5 s).

        Each ``streamer.stop()`` is already thread-safe (its own
        lifecycle lock), so parallel calls do not race each other.
        """
        if not self._streamers:
            return

        threads = []
        for streamer in self._streamers:
            def _stop_one(_s=streamer):
                try:
                    _s.stop()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.error("FFmpeg streamer stop failed: %s", exc)
            t = threading.Thread(target=_stop_one, daemon=True,
                                 name=f"stop-streamer-{id(streamer):x}")
            t.start()
            threads.append(t)

        # Bounded join — if a streamer hangs we don't want to block
        # the scheduler thread forever.  ffmpeg.stop() itself already
        # has a 3 s graceful-exit timeout, so 4 s here is enough
        # headroom without freezing the next track.
        for t in threads:
            t.join(timeout=4.0)

    def _reload_stream_outputs_if_changed(self) -> None:
        """
        Re-read stream outputs from cc_pref and rebuild streamers if the
        configuration has changed.  Called on every refresh() so user
        changes in Frontend → Settings → Streams take effect within one
        poll cycle, with no service restart required.

        If a track is currently playing, the new streamers are started
        immediately on the same audio file (with seek to current position),
        so listeners hear at most a brief reconnect on the new mountpoint.
        """
        if self._read_stream_outputs is None:
            return

        # When Liquidsoap owns the Icecast PUTs, cc_pref changes apply
        # only after the operator manually re-renders rastatime.liq +
        # restarts the NSSM service (see __main__._render_rastatime_liq_at_startup).
        # Pypo's hot-reload path here would rebuild FfmpegStreamer
        # subprocesses that fight Liquidsoap for the same mounts — so
        # we skip the whole rebuild.
        if self._streaming_handled_externally:
            return

        try:
            new_configs = self._read_stream_outputs()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Hot-reload: could not re-read stream outputs: %s", exc)
            return

        if new_configs == self._current_stream_configs:
            return  # unchanged — fast path on every poll

        logger.info(
            "Stream outputs changed in cc_pref — reloading streamers "
            "(was %d, now %d)",
            len(self._current_stream_configs), len(new_configs),
        )

        # Tear down the existing streamers cleanly
        self._stop_streamers()
        for streamer in self._streamers:
            try:
                streamer.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        # Build the new set of streamers
        new_streamers: List[FfmpegStreamer] = []
        for cfg in new_configs:
            try:
                new_streamers.append(FfmpegStreamer(cfg))
            except RuntimeError as exc:
                logger.error("Hot-reload: could not create FfmpegStreamer: %s", exc)

        self._streamers = new_streamers
        self._current_stream_configs = list(new_configs)

        # If a track is playing right now, kick the new streamers off
        # mid-track so the new mountpoints/codecs come online immediately.
        if (
            self._current_audio_path is not None
            and self._current_event is not None
            and self._streamers
        ):
            now = datetime.utcnow()
            elapsed = (now - self._current_event.start).total_seconds()
            seek = max(0.0, elapsed)
            logger.info(
                "Hot-reload: restarting streamers mid-track at seek=%.1fs",
                seek,
            )
            self._start_streamers(
                self._current_audio_path,
                seek_seconds=seek,
                gain_db=self._current_gain_db,
            )

    # ------------------------------------------------------------------
    # Source switcher (MASTER > SHOW > SCHEDULED)
    # ------------------------------------------------------------------

    def set_source_switcher(self, switcher) -> None:
        """Wire up the SourceSwitcher.  Called once from __main__."""
        self._switcher = switcher

    def switch_audio_source(self, state: SourceState) -> None:
        """
        React to a state transition signalled by the SourceSwitcher.

        Called from a daemon thread (the HTTP listener / Liquidsoap
        telnet reconciler), so we serialise access to the engine +
        streamers via the existing scheduler lock — that keeps us
        coherent against schedule refreshes and timer callbacks
        happening at the same moment.

        RASTATIME 2026-05-27 — Phase-C4 Teil 2b.  In the Liquidsoap
        engine path (``streaming_handled_externally=True``) the
        MASTER / SHOW branches are no-ops: Liquidsoap's own
        ``switch(track_sensitive=true, [(source.is_ready(master_dj),
        master_dj), …])`` in rastatime.liq picks the active source
        automatically via ``input.harbor.source.is_ready()`` — Pypo
        does NOT need to push the Icecast-mount URL into the queue
        like the legacy mpv/VLC path does (those engines own the
        soundcard output and must explicitly load the DJ-relay
        stream to make it audible locally).

        Pushing ``engine.play(http://127.0.0.1:8000/show)`` against
        Liquidsoap in the C4 setup is actively harmful — that mount
        is empty (the DJ now connects to port 8001/Liquidsoap-harbor,
        not port 8000/Icecast), so Liquidsoap times out trying to
        decode it + spams the log.

        SCHEDULED path stays active in both modes: after a DJ
        disconnect Pypo still wants to push the in-progress
        scheduled track into the queue so it picks up cleanly when
        Liquidsoap's fallback switches back from blank() to the
        scheduled queue.
        """
        logger.info("PlayoutScheduler: switching audio source to %s", state.value)

        with self._lock:
            if self._streaming_handled_externally:
                # Liquidsoap-engine mode: skip the engine.play(http://...)
                # DJ-source-relay dance — Liquidsoap's switch operator
                # handles it natively.  Only the SCHEDULED branch
                # still needs to push the in-progress track.
                if state == SourceState.SCHEDULED:
                    self._resume_scheduled_locked()
                    logger.info(
                        "PlayoutScheduler: scheduled resume after "
                        "DJ-off (Liquidsoap input.harbor switch "
                        "handled MASTER/SHOW routing internally)",
                    )
                else:
                    logger.info(
                        "PlayoutScheduler: %s active — Liquidsoap-side "
                        "switch handles routing via source.is_ready(); "
                        "no engine.play() needed.",
                        state.value,
                    )
                return

            # Legacy mpv / VLC path: Pypo owns the audio engine and must
            # explicitly relay the DJ-source Icecast mount.
            #
            # Stop whatever is currently producing audio so we can swap
            # in cleanly.  This briefly silences listeners but a fresh
            # FFmpeg subprocess connects within a second.
            self._engine.stop()
            self._stop_streamers()

            if state == SourceState.MASTER:
                url = self._build_icecast_input_url("main")
                self._engine.play(url, cue_in=0.0)
                self._start_streamers(url, seek_seconds=0.0)
                logger.info("PlayoutScheduler: now relaying MASTER input from %s", url)

            elif state == SourceState.SHOW:
                url = self._build_icecast_input_url("show")
                self._engine.play(url, cue_in=0.0)
                self._start_streamers(url, seek_seconds=0.0)
                logger.info("PlayoutScheduler: now relaying SHOW input from %s", url)

            else:  # SCHEDULED — fall back to whichever track should be running
                self._resume_scheduled_locked()

    def set_audio_output(self, device_id: Optional[str]) -> None:
        """
        Re-route the local soundcard playback to the operator-selected
        output device.

        Exposed for the HTTP listener (``/set-audio-output``) so the
        Frontend can push this change live, without needing a playout
        service restart.

        ``device_id`` is the RASTATIME *stable ID* (normalised audio
        endpoint GUID without braces).  ``None`` or empty string means
        "use OS default".

        Implementation delegates to the engine layer — see
        :meth:`PlayoutEngine.set_audio_device`.
        """
        # Done under the lock so a concurrent track-start/stop callback
        # doesn't race the device switch.
        with self._lock:
            self._engine.set_audio_device(device_id)

    def set_listener_credentials(self, user: str, password: str) -> None:
        """Set the Basic-Auth credentials used to pick up /main and /show."""
        self._listener_user = user or ""
        self._listener_pass = password or ""

    def kick_dj_source(self, kind: str) -> None:
        """
        Force-disconnect the DJ currently streaming to /main or /show.

        Exposed for the HTTP listener so the PHP frontend can push a
        kick request directly when the operator hits "Cancel Show" or
        otherwise wants to end a live slot immediately, without having
        to wait for the schedule-refresh / playing-key cancellation
        path (which doesn't trigger at all if the cancelled show had
        no scheduled tracks of its own, e.g. a pure live-DJ slot).

        ``kind`` accepts the RASTATIME source names ``master`` / ``show``,
        as well as the legacy Airtime equivalents ``master_dj`` /
        ``live_dj`` so the PHP side can pass through whatever it already
        uses without translation.
        """
        kind_norm = (kind or "").lower()
        if kind_norm in ("master", "master_dj"):
            mount = "/main"
        elif kind_norm in ("show", "live_dj", "dj"):
            mount = "/show"
        else:
            logger.warning(
                "kick_dj_source: unknown source kind %r — ignoring.", kind,
            )
            return
        logger.info("kick_dj_source(%s) -> killsource %s", kind, mount)
        self._kick_icecast_source(mount)

    def _kick_icecast_source(self, mount: str) -> None:
        """
        Tell Icecast to disconnect the source currently streaming to ``mount``.

        Used when "Cancel Show" is invoked while a show DJ is connected
        to /show — ending the show by definition ends that DJ's slot.

        Icecast will then emit a source-disconnect event-binding back
        to our SourceSwitcher, which transitions state to SCHEDULED.
        Since we clear ``_current_event`` right after this call, the
        resume path finds nothing to play and the playout falls silent
        — matching the visible "show cancelled" state.

        Best-effort: if the admin call fails (e.g. credentials wrong,
        icecast down) we log a warning and carry on.  Scheduled audio
        was already stopped or about to be by the caller.
        """
        # TODO(production): once the Icecast admin-password is hardened
        # (it ships as 'admin' / 'admin'), move these into libretime.conf
        # under stream.icecast_admin and load them via __main__ like the
        # internal-listener credentials.  For now we match the
        # icecast.xml default so a fresh install works out of the box.
        admin_user = "admin"
        admin_pass = "admin"
        auth = base64.b64encode(
            f"{admin_user}:{admin_pass}".encode()
        ).decode()
        # The mount parameter must keep its leading slash UN-encoded —
        # ``quote(mount, safe='')`` would emit ``%2Fshow`` and Icecast
        # would respond "Mount Point /%2Fshow does not exist", silently
        # leaving the DJ connected.  ``safe='/'`` keeps the slash literal
        # while still escaping anything exotic that might appear in a
        # custom mount name.
        url = (
            f"http://{self._icecast_host}:{self._icecast_port}"
            f"/admin/killsource?mount={quote(mount, safe='/')}"
        )
        req = urllib_request.Request(
            url, headers={"Authorization": f"Basic {auth}"}
        )
        logger.info("Icecast killsource: POST %s", url)
        try:
            with urllib_request.urlopen(req, timeout=2.0) as resp:
                body = resp.read(2000).decode("utf-8", errors="replace").strip()
                logger.info(
                    "Icecast killsource %s -> HTTP %d  body=%r",
                    mount, resp.status, body,
                )
        except urllib_request.HTTPError as exc:
            body = ""
            try:
                body = exc.read(2000).decode("utf-8", errors="replace").strip()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            # 404 "Source does not exist" is the expected response when
            # nobody is currently pushing to the mount we tried to kick.
            # That happens on every Cancel Show that fires while Master
            # is on-air, or while no DJ at all is connected — perfectly
            # normal.  Log it at INFO without the "something is wrong"
            # framing.  Other codes (401 / 400 / 5xx) stay at WARNING
            # because they DO point at a real misconfiguration.
            if exc.code == 404:
                logger.info(
                    "Icecast killsource %s -> HTTP 404 (no source connected, no-op).",
                    mount,
                )
            else:
                logger.warning(
                    "Icecast killsource %s -> HTTP %d  body=%r — the show DJ "
                    "may remain connected.  Check icecast.xml admin-user / "
                    "admin-password and the mount name.",
                    mount, exc.code, body,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Icecast killsource %s failed: %s — the show DJ may "
                "remain connected; their audio will be ignored once the "
                "source-disconnect event eventually fires.",
                mount, exc,
            )

    def _build_icecast_input_url(self, mount: str) -> str:
        """
        Build the icecast input URL the playout uses to relay a DJ's
        audio onwards to the public output streams.

        Both /main and /show are URL-auth-gated for listeners via the
        icecast-listener-allow PHP endpoint, which compares the Basic-
        Auth user/pass against the values from libretime.conf
        (stream.internal_listener.*).  The credentials must be encoded
        so a password with reserved characters (':' / '@' / '/' / '#')
        does not corrupt the URL.
        """
        path = f"http://{self._icecast_host}:{self._icecast_port}/{mount.lstrip('/')}"
        if self._listener_user and self._listener_pass:
            user_enc = quote(self._listener_user, safe="")
            pass_enc = quote(self._listener_pass, safe="")
            return (
                f"http://{user_enc}:{pass_enc}@"
                f"{self._icecast_host}:{self._icecast_port}/{mount.lstrip('/')}"
            )
        # Falling back to no-credentials would only work if listener-auth
        # was disabled — warn so the operator sees this in the playout log.
        logger.warning(
            "Listener credentials are not configured "
            "(stream.internal_listener.* in libretime.conf is missing); "
            "the playout will likely get a 401 from Icecast for %s",
            mount,
        )
        return path

    def _resume_scheduled_locked(self) -> None:
        """
        Resume whatever is currently scheduled when all DJ sources have
        disconnected.

        Three flavours of resumable content:

          * ``FileEvent``      — re-open the cached file with a seek
                                 equal to the elapsed time inside the
                                 track, so listeners pick up roughly
                                 where the original schedule would
                                 have been.
          * ``WebStreamEvent`` — just (re)connect to the live HTTP
                                 stream.  Seeking is meaningless for
                                 a live source; listeners pick up
                                 wherever the upstream encoder is
                                 right now.
          * ``LineinEvent``    — re-target mpv + output streamers to
                                 the /linein-capture mount.  Capture
                                 process keeps running across DJ-
                                 override windows, so the mount is
                                 already populated and resume is
                                 instant.  (Phase B.)

        Must be called with ``self._lock`` already held.
        """
        now = datetime.utcnow()

        if (
            self._current_event is None
            or self._current_audio_path is None
            or self._current_event.end <= now
        ):
            logger.info(
                "Resume scheduled: no active scheduled track to resume; "
                "next track will start when its timer fires."
            )
            return

        if isinstance(self._current_event, WebStreamEvent):
            logger.info(
                "Resume scheduled web stream: uri=%s  show: %s",
                self._current_audio_path,
                self._current_event.show_name,
            )
            self._engine.play(self._current_audio_path, cue_in=0.0)
            self._start_streamers(self._current_audio_path, seek_seconds=0.0)
            return

        if isinstance(self._current_event, LineinEvent):
            logger.info(
                "Resume scheduled line-in: device=%s name=%r  show: %s",
                self._current_event.device_id,
                self._current_event.name,
                self._current_event.show_name,
            )
            # Make sure the capture is still running.  start() is a
            # no-op (well: stop+start, idempotent in practice) if the
            # process is already alive on the same device.
            if self._linein_capture is not None:
                resume_device_id = self._resolve_linein_device(self._current_event)
                if resume_device_id:
                    try:
                        self._linein_capture.start(resume_device_id)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.error(
                            "Resume line-in: capture (re)start failed: %s", exc,
                        )
                else:
                    logger.error(
                        "Resume line-in: device %r unavailable (no "
                        "name-fallback match for %r) — capture stays down.",
                        self._current_event.device_id,
                        getattr(self._current_event, "device_name", "") or "",
                    )
            self._engine.play(self._current_audio_path, cue_in=0.0)
            self._start_streamers(self._current_audio_path, seek_seconds=0.0)
            return

        # FileEvent — seek into the track to catch up.
        elapsed = (now - self._current_event.start).total_seconds()
        seek = max(0.0, elapsed)
        cue_in = (self._current_event.cue_in or 0.0) + seek

        logger.info(
            "Resume scheduled: %r at +%.1fs",
            self._current_event.track_title,
            seek,
        )
        # RASTATIME 2026-05-16 — preserve the event's gain (file
        # ReplayGain or webstream input-gain) across the resume path;
        # live-source resumes leave it None.
        # RASTATIME 2026-05-26 — Phase C6 Teil 2: same metadata
        # forwarding pattern as the fresh-start path above so
        # ICY-titles survive Pypo restarts.
        resume_metadata = None
        if isinstance(self._current_event, FileEvent):
            resume_metadata = {
                "title":     self._current_event.track_title or "",
                "artist":    self._current_event.artist_name or "",
                "show_name": self._current_event.show_name or "",
            }
        self._engine.play(
            self._current_audio_path,
            cue_in=cue_in,
            gain_db=self._current_gain_db,
            metadata=resume_metadata,
        )
        self._start_streamers(
            self._current_audio_path,
            seek_seconds=seek,
            gain_db=self._current_gain_db,
        )

    # ------------------------------------------------------------------
    # Legacy v1 API notify (drives the dashboard "On Air" light)
    # ------------------------------------------------------------------

    def _notify_media_started(self, schedule_row_id: int) -> None:
        """
        Tell the legacy v1 API that ``schedule_row_id`` has started playing.

        Runs in a daemon thread so a slow or hung HTTP call cannot delay
        the next track start.  Failure is logged but not raised — the
        legacy notify is best-effort metadata, not a blocker for audio.
        """
        if self._api_client_v1 is None:
            return

        def _send() -> None:
            try:
                self._api_client_v1.notify_media_item_start_play(
                    media_id=schedule_row_id,
                    timeout=5,
                )
                logger.debug(
                    "Notified legacy API of media start (row_id=%d)",
                    schedule_row_id,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "notify_media_item_start_play failed (row_id=%d): %s",
                    schedule_row_id, exc,
                )

        t = threading.Thread(
            target=_send,
            name=f"notify-media-{schedule_row_id}",
            daemon=True,
        )
        t.start()

    # ------------------------------------------------------------------
    # File download / cache management
    # ------------------------------------------------------------------

    def _ensure_file_cached(self, event: FileEvent) -> Optional[Path]:
        """
        Return the local path for a FileEvent.

        RASTATIME: On a single-server Windows install, try to resolve the
        file directly from storage first (avoids the API download round-trip
        and the X-Accel-Redirect / path issues).  Falls back to API download
        if direct access fails.
        """
        local = event.local_filepath
        if local.is_file() and local.stat().st_size > 0:
            logger.debug("Cache hit: %s", local)
            return local

        # --- Strategy 1: direct storage access ---
        direct = self._try_direct_storage(event)
        if direct is not None:
            return direct

        # --- Strategy 2: API download (original approach) ---
        logger.info("Downloading file %d via API", event.id)
        try:
            with local.open("wb") as fh:
                response = self._api_client.download_file(event.id, stream=True)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    fh.write(chunk)
            if local.stat().st_size > 0:
                local.chmod(0o644)
                logger.info("Download complete: %s (%d bytes)", local, local.stat().st_size)
                return local
            else:
                logger.error("API download produced 0-byte file for %d", event.id)
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "HTTP %s downloading file %d: %s",
                exc.response.status_code if exc.response else "?",
                event.id,
                exc,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to download file %d: %s", event.id, exc)

        local.unlink(missing_ok=True)
        return None

    def _try_direct_storage(self, event: FileEvent) -> Optional[Path]:
        """
        Try to resolve the file directly from the storage directory,
        bypassing the API download.  Returns the storage Path if found,
        or None.
        """
        if self._storage_path is None:
            return None

        try:
            # Get file metadata from API (lightweight JSON, not the file itself)
            resp = self._api_client.get_file(event.id)
            resp.raise_for_status()
            filepath = resp.json().get("filepath", "")
            if not filepath:
                return None

            # Construct full path (strip leading "/" for Windows compatibility)
            full_path = Path(self._storage_path) / filepath.lstrip("/")
            if full_path.is_file():
                logger.info(
                    "Direct storage hit: %s (%d bytes)",
                    full_path, full_path.stat().st_size,
                )
                return full_path
            else:
                logger.debug("Direct storage miss: %s", full_path)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Direct storage lookup failed for file %d: %s", event.id, exc)

        return None
