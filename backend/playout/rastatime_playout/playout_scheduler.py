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
The implementation is engine-agnostic by construction (it talks to
:class:`PlayoutEngine`); since 2026-09-10 the only engine is the
:class:`LiquidsoapPlayoutEngine`.  Liquidsoap owns local playback, the
Icecast outputs, the DJ harbors, the webstream / line-in inputs and the
recording; this scheduler drives it over telnet.  (The mpv engine, its
FfmpegStreamer Icecast companions and the Icecast admin kick were
deleted with BACKLOG "Legacy-mpv-Code-Delete".)

Design references
-----------------
QUEUE_BEHAVIOR.md §3.1, §4.1 (show start HARD mode), §4.2 (show end),
§6.1 (cue_in/cue_out not yet enforced — stop timer uses schedule end_at).
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from rastatime_api_client.v2 import ApiClient

from . import liquidsoap_health
from .config import CACHE_DIR
from .engine.ffmpeg_linein_capture import FfmpegLineinCapture
from .engine.interface import PlayoutEngine, PlayoutState
from .liquidsoap_config import (
    DEFAULT_CROSSFADE_DURATION,
    crossfade_buffer_seconds,
)
from .liquidsoap_service import (
    MAIN_OUTPUT_BY_INDEX,
    NightlyRestartPolicy,
    restart_liquidsoap_service,
)
from .live_text import LiveTextWriter
from .player.events import (
    EventKind,
    FileEvent,
    LineinEvent,
    ShowRecordEvent,
    WebStreamEvent,
)
from .player.schedule import get_schedule
from .recording_path import build_output_path
from .source_switcher import SourceState
from .tunein import TuneInPusher

logger = logging.getLogger(__name__)

# (Removed _MIN_START_LAG — replaced by catch-up logic that checks
# self._playing_key to avoid restarting in-progress tracks.)


# RASTATIME 2026-09-04 - how close (seconds) a same-device line-in
# follow-up must start to count as "back-to-back" for the STOP handoff
# in _on_stop.  Live incident 2026-09-04 11:00: a line-in armed SEVEN
# MINUTES later kept the ending line-in on air through a whole jingle
# + webstream show, because the old check only asked "is a same-device
# timer armed at all?".  Timer callbacks fire within a few ms of their
# target, so 2 s is generous for a true same-instant handoff and far
# below any real gap between shows.
LINEIN_FOLLOW_UP_WINDOW_SECONDS = 2.0

# RASTATIME 2026-09-04 - "Paket 2": how long before its slot a line-in
# or webstream is connected and buffered with its bus gate CLOSED, so
# that at the slot start only the gate has to open (start gap ~0
# instead of the ~2 s the capture chain / the webstream pre-buffer
# need).  10 s was the operator's figure; the slowest observed
# webstream buffer-up was 9 s.
# RASTATIME 2026-10-21 - 15 s for line-ins: the fresh input.http of the
# capture mount (23.68) connected 11-12 s after linein_http.start in
# both measured slots (09:02, 11:02), so with 10 s the arm came up about
# one second after the gate.  Webstreams keep their own 10 s below.
PREPARE_LEAD_SECONDS = 15.0
# RASTATIME 2026-09-06 - webstreams pre-warm 10 s early, same as
# line-ins.  The 2026-09-05 bump to 20 s ("Option 1") went with the fat
# bridge and is reverted along with it; the 5 s bridge fills well within
# 10 s.  A stalled upstream is handled by the watchdog inside
# Liquidsoap, not by pre-warming earlier.
WEBSTREAM_PREPARE_LEAD_SECONDS = 10.0
# RASTATIME 2026-09-27 - a file track is queued behind the playing one
# this many seconds BEFORE the cross operator opens its tail window
# (BUFFER = max(track, show crossfade) seconds before the playing
# track's end).  Cross needs the partner on the queue before that moment,
# otherwise it runs the end-of-track transition alone and the next track
# follows without a crossfade (bench 2026-09-27).
# The margin also covers copying the file into the cache (~2 s for an
# 8 MB track, seen in the 2026-09-27 rehearsal) and row layouts whose
# overlap is shorter than the buffer (the window then opens before the
# row start).  Queued requests wait on the queue, so being early is free.
QUEUE_AHEAD_MARGIN_SECONDS = 5.0
# A predecessor with more than BUFFER + this many seconds of audio left at
# the successor's start is cut (overbook); less means the rows overlap by
# the crossfade and cross does the hand-over.  Event starts are whole
# seconds (event_isoparse drops microseconds) while the rows carry them,
# so a start can run up to 1 s early - the rehearsal measured 3.56 s left
# for a 3 s overlap; 0.3 s tolerance turned that into a skip.
SKIP_TOLERANCE_SECONDS = 1.5
# RASTATIME 2026-09-29 - a pre-warmed webstream / line-in that follows a
# file track opens its gate when the track's audio is over (minus the
# overlap of the pair), not on the whole second its timer fires at: the
# rows carry microseconds and the file chain runs a moment behind the
# schedule (push + request resolution), so the timer is up to ~1.3 s
# early and the switch would fade the track's last second away.  More
# audio left than this is an overbook - the live item starts at once.
FILE_TAIL_HOLD_MAX_SECONDS = 4.0
# How far the file chain runs behind the rows until a push has measured it.
FILE_CHAIN_LAG_DEFAULT_SECONDS = 0.25
# RASTATIME 2026-10-01 - the other direction: a file pushed after a live
# item, a pre-warmed live item after a live item, and the stop of a live
# item wait for the row's exact time instead of acting on the whole second
# the timer fired at (up to ~1 s early).  More than this is not the
# whole-second effect - act at once.
EXACT_TIME_HOLD_MAX_SECONDS = 1.5
# RASTATIME 2026-10-02 - a planned restart at a track boundary blocks
# _on_file_start for a few seconds (stop, start, back: ~3.8 s on 2026-10-02
# 17:20); the track that follows enters its audio that far in so the show
# stays on its rows.  Below this much the push is left alone (timers fire
# on the whole second before the row time).
BOUNDARY_RESTART_CATCHUP_MIN_SECONDS = 0.5

# RASTATIME 2026-09-07 - the webstream watchdog lives inside Liquidsoap
# (frame counter on the bus, rendered by liquidsoap_config).  The
# scheduler's telnet poll of 2026-09-06 was removed on 2026-09-15 after
# a quiet week (it leaked ~87 KB per poll on the Windows build).
# Below this many seconds to the slot a pre-warm cannot finish (capture
# health check + decoder lock ~2 s); the slot then starts the normal way.
MIN_PREPARE_SECONDS = 2.5


class PlayoutScheduler:
    """
    Schedule-driven playout controller.  Engine-agnostic — talks to a
    :class:`PlayoutEngine` (the Liquidsoap adapter in
    :mod:`engine.liquidsoap_engine`) without knowing which library does
    the actual decoding.

    Thread model
    ------------
    * The main thread calls ``refresh()`` periodically.
    * ``threading.Timer`` daemon threads fire ``_on_start`` / ``_on_stop``
      callbacks at the appropriate wall-clock times.
    * The callbacks call into ``PlayoutEngine``; the Liquidsoap telnet
      client serialises its socket I/O on its own lock.
    """

    def __init__(
        self,
        engine: PlayoutEngine,
        api_client: ApiClient,
        cache_dir: Optional[Path] = None,
        storage_path: Optional[str] = None,
        api_client_v1: Optional["object"] = None,
        read_icy_preferences: Optional[Callable[[], Optional[object]]] = None,
        input_transition_seconds: float = 2.0,
        track_crossfade_seconds: float = DEFAULT_CROSSFADE_DURATION,
        render_liquidsoap: Optional[Callable[[], object]] = None,
        nightly_restart: Optional[NightlyRestartPolicy] = None,
        render_settings_fingerprint: Optional[Callable[[], Optional[str]]] = None,
        render_restart_pending: bool = False,
        recording_extension: Optional[Callable[[], str]] = None,
        tunein: Optional[TuneInPusher] = None,
        live_text: Optional[LiveTextWriter] = None,
        linein_icecast_credentials: Optional[tuple[str, str]] = None,
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
        self._timers: dict[str, tuple[Optional[threading.Timer], Optional[threading.Timer]]] = {}
        # Currently armed events, parallel to ``self._timers`` — keyed
        # by the same event_key.  Stored separately (rather than as a
        # third tuple element on ``_timers``) so the lookup is a clean
        # ``dict[str, AnyEvent]`` for code that doesn't care about timer
        # objects.  Used by Phase B.4 #3 (same-device transition) so
        # ``_on_stop`` for show A can ask "is there a same-device
        # LineinEvent B already armed?" without poking around in timer
        # internals.
        self._armed_events: dict[str, object] = {}
        self._lock = threading.Lock()
        # RASTATIME 2026-09-05 - nightly quiet-window restart of LIQUIDSOAP
        # (memory-leak safety net, see liquidsoap_service).  The render
        # callable runs right before the restart so the fresh instance
        # gets today's device resolution and cc_pref.
        self._render_liquidsoap = render_liquidsoap
        self._nightly_restart = nightly_restart
        self._nightly_restart_done: Optional[date] = None
        # RASTATIME 2026-09-09 - a planned restart that found something on
        # air (24/7 programme) waits for the next file-to-file track
        # boundary; the reason text is kept for the log.  Attempts are
        # rate-limited so a failing restart is not hammered every poll.
        self._boundary_restart_pending: Optional[str] = None
        # RASTATIME 2026-09-16 - settings applied by the playout: the
        # fingerprint of the rendered settings (baseline = first refresh
        # after the start render); a change arms a planned restart.
        self._render_settings_fingerprint = render_settings_fingerprint
        self._rendered_fingerprint: Optional[str] = None
        self._settings_restart_attempted_at: Optional[datetime] = None
        # RASTATIME 2026-09-16 - the startup render changed rastatime.liq
        # outside the boot window: apply it like a settings change.
        self._render_restart_pending = render_restart_pending
        self._planned_restart_attempted_at: Optional[datetime] = None
        # RASTATIME 2026-10-18 - file extension of the show recording: the
        # format of the LAST render (not the setting of the moment), so the
        # file name always matches the encoder Liquidsoap is running with.
        self._recording_extension = recording_extension
        # RASTATIME 2026-10-19 - the recording Liquidsoap has open right now:
        # (instance_id, path) from _on_show_record_start, consumed by
        # _on_show_record_end, which reports the closed file to the legacy
        # API (copy into the library).  None while nothing is recording or
        # after a PLAYOUT restart mid-show (the path is then unknown).
        self._open_show_recording: Optional[tuple[Optional[int], Path]] = None
        # RASTATIME 2026-09-06 - did the constructor's recording.stop +
        # gate reset reach Liquidsoap?  False means telnet was not up yet
        # and ensure_liquidsoap_initial_state() has to keep trying.
        self._initial_state_ok: bool = False
        # RASTATIME 2026-09-07 - last observed Liquidsoap uptime.  A drop
        # between polls means LIQUIDSOAP was restarted under a running
        # PLAYOUT (manual "PLAYOUT then LIQUIDSOAP" order leaves the fresh
        # instance with the recording sentinel on and default gates);
        # refresh() then re-applies the initial state.
        self._last_liquidsoap_uptime: Optional[float] = None
        # RASTATIME 2026-09-09 - restart detection without telnet: (pid,
        # age_seconds) of the main instance from the process table; the
        # process probe is fetched once per refresh cycle and shared with
        # the planned-restart triggers.
        self._last_liquidsoap_process: Optional[tuple[int, float]] = None
        self._cycle_process_infos: Optional[tuple] = None
        self._cycle_process_cache_enabled = False

        # Track which event key is currently playing so that refresh()
        # doesn't restart an in-progress track every 120 s.
        self._playing_key: Optional[str] = None
        self._current_event: Optional[FileEvent] = None
        self._current_audio_path: Optional[str] = None

        # RASTATIME 2026-06-05 — Record-per-Hour cue sidecars (stage 5).
        # Optional; set via set_cue_writer().  None = no cue marking.
        self._cue_writer = None

        # RASTATIME 2026-05-30 — Phase-F-2 race fix #3 (line-in
        # device-switch).  Monotonic counter bumped every time
        # ``_on_linein_start`` actually (re)starts a line-in source.
        # ``_on_stop`` snapshots it on entry and re-checks it before
        # tearing the line-in down, so a finishing show's teardown can
        # never kill a back-to-back follow-up show's freshly started
        # source — even when the two ``threading.Timer`` callbacks fire in
        # the "stop after start" order (observed live 2026-05-29 21:15:00:
        # a jabra-show start was followed 2 ms later by the tascam-show
        # stop, whose ``linein_stop`` muted the jabra source).
        self._linein_generation: int = 0
        # RASTATIME 2026-09-04 - Paket 2 state (see PREPARE_LEAD_SECONDS).
        # _prepared: (key, event) of the ONE source currently pre-warmed
        # with its gate closed; identity-compared (keys shift across
        # refreshes).  _webstream_generation mirrors _linein_generation so
        # a drained stop can tell "my" source from a newer one.  The drain
        # is the bus transition length (crossfade D, or the fixed duck
        # fade when D = 0) plus a margin: the old source must keep being
        # pulled until the fade is over, THEN it is stopped.
        self._webstream_generation: int = 0
        self._prepare_timers: dict[str, threading.Timer] = {}
        self._prepared: Optional[tuple[str, object]] = None
        # RASTATIME 2026-09-27 - input_transition_seconds is the Default
        # SHOW Crossfade Duration (every input switch: new source at once,
        # old fades out under it over this many seconds); the drain keeps
        # the old source pulled until that fade is over.  The track
        # crossfade only shapes queue transitions; both define the tail
        # buffer of the cross operator (queue-ahead lead + skip decision).
        self._input_transition_seconds = max(0.0, float(input_transition_seconds))
        self._drain_seconds = self._input_transition_seconds + 0.5
        self._track_crossfade_seconds = max(0.0, float(track_crossfade_seconds))
        self._cross_buffer_seconds = crossfade_buffer_seconds(
            self._track_crossfade_seconds,
            self._input_transition_seconds,
        )
        # (key, FileEvent) queued behind the playing track, or None; and the
        # track it was queued behind (the predecessor's STOP may clear
        # _current_event before the successor's start runs - same instant
        # when rows are clipped at a show boundary, rehearsal 2026-09-27)
        self._queued_ahead: Optional[tuple[str, FileEvent]] = None
        self._queued_ahead_prev: Optional[FileEvent] = None
        # RASTATIME 2026-10-03 - a row whose queue-ahead was held back
        # behind a shorter queued row (see _on_file_queue_ahead); queued as
        # soon as that row starts, so cross has its partner in time.
        self._deferred_queue_ahead: Optional[tuple[str, FileEvent]] = None
        # RASTATIME 2026-10-03 - rows whose _on_file_start is executing right
        # now (key -> event): a refresh in the same second must not catch
        # them up a second time (12:17:55 incident: a jingle aired twice).
        self._starting: dict[str, FileEvent] = {}
        # RASTATIME 2026-09-28 - when the current file track was pushed and
        # how much audio it had then: the upper bound for what the engine
        # may report as "left" (the queue's remaining belongs to the
        # successor once cross has pulled it - 20:05:35 incident).
        self._current_started_at: Optional[datetime] = None
        self._current_clip_seconds: Optional[float] = None
        # RASTATIME 2026-09-29 - how far the audio of the running file
        # chain is behind its rows (measured at the push that started the
        # chain; tracks queued behind it follow sample-accurately).
        self._file_chain_lag: Optional[float] = None

        # RASTATIME 2026-05-16 — cached effective dB gain for the
        # currently-playing event.  Source of the value depends on the
        # event type (file → ReplayGain sum; webstream →
        # cc_webstream.input_gain_db; live sources → None).  The
        # resume path reads this back after a DJ-source disconnect, so
        # a previous event's gain does not leak into the new playback.
        #
        # (Was ``_current_replay_gain_db`` before 2026-05-16; renamed
        # when webstream input-gain joined the same plumbing.)
        self._current_gain_db: Optional[float] = None

        # Source-switcher integration.  Set by __main__ via
        # ``set_source_switcher``.  When non-None and reporting a state
        # other than SCHEDULED, scheduled track-start/stop callbacks
        # don't touch the audio engine — they only update the
        # currently-tracked event so we know what to resume to when
        # the DJ disconnects.
        self._switcher = None

        # RASTATIME 2026-09-13 - ICY metadata: the Settings -> Streams values
        # (Stream Label, Off Air Metadata, station name) are re-read every
        # refresh and pushed over telnet only when they changed; bus_show
        # follows the show on air (see _sync_icy_metadata).
        self._read_icy_preferences = read_icy_preferences
        # RASTATIME 2026-09-28 - TuneIn now-playing pushes (title/artist at
        # every start, show name for live inputs, keep-alive every refresh).
        self._tunein = tunein
        # RASTATIME 2026-09-28 - Live Text Info: Liquidsoap needs the switch +
        # format (pushed on refresh when they change); the writer itself is
        # fed by the /live-text listener endpoint.
        self._live_text = live_text
        self._live_text_pushed: Optional[tuple[bool, int]] = None
        self._icy_pushed: Optional[object] = None
        # RASTATIME 2026-11-02 - one pending early refresh at a time
        # (_schedule_refresh_soon / request_refresh_soon).
        self._refresh_soon_lock = threading.Lock()
        self._refresh_soon_pending = False
        self._bus_show_pushed: Optional[str] = None

        # RASTATIME 2026-05-12 — Phase B Line-In capture.
        #
        # Lazy-created instance shared across all LineinEvents.  We
        # build it eagerly here (rather than on first use) so any
        # configuration error (missing ffmpeg, bad icecast credentials)
        # surfaces at startup, not at scheduled-air-time.  ``stop()``
        # on an idle instance is a no-op, so it's safe to keep around.
        try:
            # RASTATIME 2026-10-04 (go-live stage 0) - the capture pushes to
            # the local Icecast with the SAME source credentials as the
            # stream outputs (Settings -> Streams); the module default
            # ("source"/"admin") only applies when no local output exists.
            capture_kwargs = {}
            if linein_icecast_credentials:
                capture_kwargs = {
                    "icecast_user": linein_icecast_credentials[0],
                    "icecast_password": linein_icecast_credentials[1],
                }
            self._linein_capture: Optional[FfmpegLineinCapture] = FfmpegLineinCapture(
                **capture_kwargs
            )
            # Phase B.4 #1 — wire the auto-restart callback so the
            # capture's watchdog can re-arm Liquidsoap's input.http
            # companion on the listen URL after a successful restart
            # (e.g. operator yanked the mic USB cable mid-show).
            # Otherwise the Icecast mount comes back but the consumer
            # stays tuned to a now-dead stream.
            self._linein_capture.set_on_restart_callback(self._on_linein_capture_restart)
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
        # (HTTP-tap + lifecycle-watchdog + post-roll-Timer) was deleted.
        logger.info(
            "PlayoutScheduler: recording is owned by Liquidsoap output.file from the internal bus.",
        )
        # rastatime.liq's output.file(id="recording") uses default
        # start=true because Liquidsoap-2.4.4 silently swallows
        # `recording.start` when the block was declared with
        # start=false (the file simply never opens, no error).
        # Without an explicit stop here, the sentinel
        # `_uninitialized.mp3` would keep growing from Liquidsoap
        # boot until the first _on_show_record_start hook fires —
        # potentially hours.  RASTATIME 2026-09-06: a single attempt
        # was not enough - whenever PLAYOUT comes up before
        # LIQUIDSOAP (manual restart order, boot-window restart,
        # nightly restart) the stop hit a dead telnet and the
        # sentinel grew (32 MB in 14 min on 2026-09-06 17:30).
        # First attempt synchronously; on failure a daemon thread
        # keeps trying until telnet is back (see
        # ensure_liquidsoap_initial_state).
        if hasattr(self._engine, "recording_stop"):
            ok, exc = self._apply_initial_liquidsoap_state(reset_gates=False)
            self._initial_state_ok = ok
            if ok:
                logger.info(
                    "PlayoutScheduler: initial recording.stop sent "
                    "to Liquidsoap (silences sentinel-file write "
                    "from boot until first scheduled show).",
                )
            else:
                logger.warning(
                    "PlayoutScheduler: initial recording.stop failed "
                    "(Liquidsoap not ready yet?): %s — "
                    "ensure_liquidsoap_initial_state() retries until "
                    "telnet is back.",
                    exc,
                )

        logger.info("PlayoutScheduler initialised (cache_dir=%s)", self._cache_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """
        Fetch the schedule from the API and re-arm all pending timers.

        Any previously armed timers are cancelled first so that edits to
        the schedule take effect immediately.
        """
        # RASTATIME 2026-09-07 - notice a LIQUIDSOAP restart that happened
        # under us (manual restart order, or a crash+NSSM-restart) and
        # re-apply the initial state so the fresh instance does not record
        # the _uninitialized.mp3 sentinel forever.  The process table is
        # read once per cycle (2026-09-09) and shared with the
        # planned-restart triggers at the end of the cycle.
        self._cycle_process_infos = None
        self._cycle_process_cache_enabled = True
        self._maybe_reinit_after_liquidsoap_restart()

        logger.info("PlayoutScheduler: refreshing schedule from API …")
        # RASTATIME 2026-10-10 - phase timing: the start timers are armed
        # against ``now`` (taken after the fetch), so every second spent
        # between ``now`` and the arming loop makes every track start late
        # (2026-10-10 11:15: PLAY 1.7 s after the row second, air +1.9 s).
        t_fetch0 = time.monotonic()
        try:
            events = get_schedule(self._api_client)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("PlayoutScheduler: schedule fetch failed: %s", exc)
            return

        now = datetime.utcnow()
        t_now = time.monotonic()
        armed_count = 0
        skipped_past = 0
        skipped_type = 0

        # RASTATIME 2026-09-13 - ICY metadata settings + show on air.
        self._sync_icy_metadata(events, now)
        t_icy = time.monotonic()
        # RASTATIME 2026-09-16 - the library root is a setting; follow it.
        self._refresh_storage_root()
        t_root = time.monotonic()

        with self._lock:
            t_lock = time.monotonic()
            self._cancel_all_timers()

            # RASTATIME 2026-09-04 - a pre-warmed source whose item is no
            # longer in the schedule must be torn down again (its gate is
            # closed, so it is inaudible, but the capture holds the
            # device and the http source polls the mount).  Identity
            # comparison, keys shift across refreshes.
            if self._prepared is not None and not any(
                self._same_scheduled_item(e, self._prepared[1]) for e in events.values()
            ):
                self._undo_prepare("its item left the schedule")

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
                # RASTATIME 2026-09-04 - Option A of the key-instability
                # fix: look the playing item up by IDENTITY, not by key
                # (see _same_scheduled_item).  Live 2026-09-04 11:08:17:
                # the running line-in came back as a different key, this
                # block declared it "removed from schedule", killed the
                # capture, and the catch-up below restarted it -- 9 s of
                # dead air filled with stale jingles.  A schedule item
                # that is still present under any key is simply rebound;
                # only an item present under NO key is really gone.
                cur = self._current_event
                moved_ahead: Optional[float] = None
                if cur is not None and not self._same_scheduled_item(current_evt, cur):
                    match = next(
                        (k for k, e in events.items() if self._same_scheduled_item(e, cur)),
                        None,
                    )
                    if match is not None and events[match].start > now:
                        # RASTATIME 2026-09-28 - the running row was moved
                        # into the future (show-builder edit): it is not
                        # on air any more and starts again at its new
                        # start, which the arming loop below handles.
                        moved_ahead = (events[match].start - now).total_seconds()
                        current_evt = None
                    elif match is not None:
                        logger.info(
                            "Playing event %s is keyed %s in the refreshed "
                            "schedule (same item%s) - rebinding, no teardown.",
                            self._playing_key,
                            match,
                            ", re-timed" if events[match].start != cur.start else "",
                        )
                        self._playing_key = match
                        current_evt = events[match]
                    else:
                        # A DIFFERENT item under our old key is not us.
                        current_evt = None
                event_gone_or_truncated = current_evt is None or current_evt.end <= now
                if (
                    current_evt is not None
                    and current_evt.end <= now
                    and self._queued_ahead is not None
                    and (now - current_evt.end).total_seconds() < 1.5
                ):
                    # RASTATIME 2026-10-03 - the row ended in this very
                    # second and its successor is on the queue: the STOP
                    # timer and the queue hand over by themselves.  Tearing
                    # down here flushed the queued jingle (12:17:55).
                    logger.info(
                        "Playing event %s ended this second with %s queued ahead "
                        "- leaving the hand-over to the queue.",
                        self._playing_key,
                        self._queued_ahead[0],
                    )
                    event_gone_or_truncated = False
                if event_gone_or_truncated:
                    stale_key = self._playing_key
                    reason = (
                        f"moved to the future (starts again in {moved_ahead:.0f} s)"
                        if moved_ahead is not None
                        else "removed from schedule"
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
                            stale_key,
                            reason,
                        )
                        # Liquidsoap keeps relaying the master harbor; leave it be.
                    elif dj_state == SourceState.SHOW:
                        logger.info(
                            "Scheduled event %s %s while Show source is "
                            "active — kicking the show DJ off the harbor.",
                            stale_key,
                            reason,
                        )
                        self.kick_dj_source("show")
                        # The source-disconnect event will transition the
                        # switcher to SCHEDULED and trigger resume; since
                        # we wipe _current_event right after this block,
                        # resume sees no active scheduled track and the
                        # playout falls silent, as expected for a cancel.
                    else:  # SCHEDULED
                        logger.info(
                            "Scheduled event %s %s — stopping playback.",
                            stale_key,
                            reason,
                        )
                        self._engine.stop()
                        # engine.stop() flushes pending requests: a
                        # successor queued ahead is gone with them and
                        # starts the normal way at its row start.
                        self._queued_ahead = None
                        self._queued_ahead_prev = None

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

            # RASTATIME 2026-10-10 - the clock reference for the start timers
            # is taken HERE, right before the arming loop.  Everything the
            # refresh did since the fetch (ICY sync, storage-root call, the
            # current-event bookkeeping above) can take seconds - the
            # storage-location endpoint walked a 198k-file library for 2 s on
            # every refresh - and with the reference taken earlier every track
            # started that much late (11:15 show: PLAY 1.7 s after the row).
            now = datetime.utcnow()
            t_arm0 = time.monotonic()

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

        t_end = time.monotonic()
        logger.info(
            "PlayoutScheduler: armed=%d  past=%d  other=%d  (fetch %.2f s, icy %.2f s, "
            "root %.2f s, lock wait %.2f s, bookkeeping %.2f s; timers armed %.2f s "
            "after the clock reference)",
            armed_count,
            skipped_past,
            skipped_type,
            t_now - t_fetch0,
            t_icy - t_now,
            t_root - t_icy,
            t_lock - t_root,
            t_arm0 - t_lock,
            t_end - t_arm0,
        )

        # RASTATIME 2026-09-05 - after the timers are re-armed we know
        # exactly what is on air and what comes next: the right moment
        # to decide about the nightly quiet-window restart.
        self._maybe_nightly_restart()
        # RASTATIME 2026-09-28 - TuneIn forgets a quiet station after 5 min
        self._tunein_keepalive()
        # RASTATIME 2026-09-16 - a changed 24/7 / Main Output / crossfade /
        # stream-output setting gets the same quiet-moment restart.
        self._maybe_settings_restart()
        self._cycle_process_cache_enabled = False
        self._cycle_process_infos = None

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-05 - nightly quiet-window restart of LIQUIDSOAP
    # ------------------------------------------------------------------

    def _quiet_for_restart_locked(self, margin_seconds: float) -> tuple[bool, str]:
        """
        Caller holds ``_lock``.  Quiet means: nothing on air, nothing
        pre-warmed, and no armed item starting within ``margin_seconds``.
        """
        if self._playing_key is not None or self._current_event is not None:
            return False, "an item is on air"
        if self._prepared is not None:
            return False, "a source is pre-warmed"
        now = datetime.utcnow()
        soonest = None
        for event in self._armed_events.values():
            start = getattr(event, "start", None)
            if start is None or start <= now:
                continue
            if soonest is None or start < soonest:
                soonest = start
        if soonest is not None:
            wait = (soonest - now).total_seconds()
            if wait < margin_seconds:
                return False, f"next item starts in {wait:.0f} s"
        return True, ""

    SETTINGS_RESTART_REASON = (
        "settings changed (24/7 recording, Main Output, crossfade or stream outputs)"
    )
    RENDER_RESTART_REASON = "rastatime.liq changed at the playout start"

    def _current_settings_fingerprint(self) -> Optional[str]:
        fn = self._render_settings_fingerprint
        if fn is None:
            return None
        try:
            value = fn()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("settings fingerprint failed: %s", exc)
            return None
        return value or None

    def _maybe_settings_restart(self, now_local: Optional[datetime] = None) -> bool:
        """
        RASTATIME 2026-09-16 - apply operator settings that live in the
        rendered script without a manual restart.  The first refresh after
        a start records the baseline (the start just rendered those
        settings); a later change re-renders and restarts LIQUIDSOAP the
        same way the nightly restart does: at once when nothing is on air,
        otherwise at the next file-to-file track boundary (listeners stay on
        the standby mounts meanwhile).  A failed attempt is retried after
        30 minutes.  Returns True when a restart was attempted.
        """
        if self._render_liquidsoap is None:
            return False
        current = self._current_settings_fingerprint()
        if current is None:
            return False
        if self._rendered_fingerprint is None:
            self._rendered_fingerprint = current
            if not self._render_restart_pending:
                return False
        elif current == self._rendered_fingerprint and not self._render_restart_pending:
            return False
        now_local = now_local or datetime.now()
        if self._boundary_restart_pending:
            return False  # armed already (any reason)
        if (
            self._settings_restart_attempted_at is not None
            and now_local - self._settings_restart_attempted_at < timedelta(minutes=30)
        ):
            return False
        policy = self._nightly_restart
        margin = policy.quiet_margin_seconds if policy is not None else 300.0
        with self._lock:
            quiet, why = self._quiet_for_restart_locked(margin)
        reason = (
            self.RENDER_RESTART_REASON
            if self._render_restart_pending
            else self.SETTINGS_RESTART_REASON
        )
        if quiet:
            self._settings_restart_attempted_at = now_local
            return self._perform_planned_restart(f"quiet moment: {reason}", now_local)
        self._boundary_restart_pending = reason
        logger.warning(
            "Settings changed (24/7 recording / Main Output / crossfade / stream "
            "outputs) but %s - applying at the next file-to-file track boundary.",
            why,
        )
        return False

    def _maybe_nightly_restart(self, now_local: Optional[datetime] = None) -> bool:
        """
        Restart LIQUIDSOAP when the policy says so (daily / every N days
        / memory limits, see NightlyRestartPolicy): in a quiet moment
        when nothing is on air, otherwise at the next file-to-file track
        boundary (RASTATIME 2026-09-09, 24/7 programme).

        Why: the savonet Windows build leaks memory in ``Unix.select``
        (3.4 GB after two hours on 2026-09-05 before the template fix).
        The synchronous queue removed the permanent poller; a daily
        restart in a quiet window is the safety net for what remains
        (telnet, harbor and http wake-ups).  Returns True when a restart
        was attempted.
        """
        policy = self._nightly_restart
        if policy is None or not policy.enabled:
            return False
        now_local = now_local or datetime.now()
        if self._boundary_restart_pending:
            return False  # armed - waits for a track boundary
        if (
            self._planned_restart_attempted_at is not None
            and now_local - self._planned_restart_attempted_at < timedelta(minutes=30)
        ):
            return False  # a failed attempt is not hammered
        age_seconds, private_mb = self._liquidsoap_process_probe()
        reason = policy.reason_due(
            now_local,
            self._nightly_restart_done,
            age_seconds,
            private_mb,
        )
        if reason is None:
            return False
        with self._lock:
            quiet, why = self._quiet_for_restart_locked(policy.quiet_margin_seconds)
        if quiet:
            return self._perform_planned_restart(f"quiet moment: {reason}", now_local)
        # RASTATIME 2026-09-09 - 24/7 programme: never a quiet moment, so
        # restart between two file tracks instead (see _on_file_start).
        self._boundary_restart_pending = reason
        logger.warning(
            "Planned Liquidsoap restart due (%s) but %s - restarting at the "
            "next file-to-file track boundary instead.",
            reason,
            why,
        )
        return False

    def _liquidsoap_process_infos(self) -> Optional[list]:
        """
        The liquidsoap.exe process table (``liquidsoap_health.
        liquidsoap_process_info``), read once per refresh cycle and shared
        by the restart detector and the planned-restart triggers; None
        when the probe cannot run.  Outside a cycle every call reads it.
        """
        cached = self._cycle_process_infos
        if cached is not None:
            return cached[0]
        try:
            infos = liquidsoap_health.liquidsoap_process_info()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Liquidsoap process probe failed: %s", exc)
            infos = None
        if self._cycle_process_cache_enabled:
            self._cycle_process_infos = (infos,)
        return infos

    def _liquidsoap_main_process(self):
        """
        The main instance (rastatime.liq) from the process table, or None.
        Since the standby source (2026-09-09) two liquidsoap.exe run and
        the oldest one is usually the standby, so the script name decides
        (``liquidsoap_health.main_instances``); among several candidates
        the oldest wins (replicas are younger).
        """
        infos = self._liquidsoap_process_infos()
        candidates = liquidsoap_health.main_instances(infos) if infos else []
        if not candidates:
            return None
        return max(candidates, key=lambda i: i.age_seconds)

    def _liquidsoap_process_probe(self) -> tuple[Optional[float], Optional[float]]:
        """``(age_seconds, private_mb)`` of the main instance, or ``(None, None)``."""
        info = self._liquidsoap_main_process()
        if info is None:
            return None, None
        return float(info.age_seconds), float(info.private_mb)

    def _liquidsoap_process_identity(self) -> Optional[tuple[int, float]]:
        """``(pid, age_seconds)`` of the main instance, or None."""
        info = self._liquidsoap_main_process()
        if info is None:
            return None
        return int(info.pid), float(info.age_seconds)

    @staticmethod
    def _boundary_allows_restart(prev_event: object, next_event: object) -> bool:
        """A restart may sit between two FILE tracks (or at the very first
        track); a webstream or line-in on either side keeps waiting."""
        if not isinstance(next_event, FileEvent):
            return False
        return prev_event is None or isinstance(prev_event, FileEvent)

    def _perform_planned_restart(
        self,
        reason: str,
        now_local: Optional[datetime] = None,
        settle_async: bool = False,
    ) -> bool:
        """
        Re-render, restart RASTATIME-LIQUIDSOAP, re-apply the initial
        state.  Returns True when an attempt was made.  ``settle_async``
        runs the 10 s stays-up check in a daemon thread so a track that
        waits for us (boundary restart) is not delayed by it.
        """
        now_local = now_local or datetime.now()
        self._nightly_restart_done = now_local.date()
        self._planned_restart_attempted_at = now_local
        policy = self._nightly_restart
        logger.warning(
            "Planned Liquidsoap restart (%s; window from %s): re-rendering "
            "rastatime.liq and restarting RASTATIME-LIQUIDSOAP.",
            reason,
            policy.start.strftime("%H:%M") if policy and policy.start else "?",
        )
        outcome = None
        if self._render_liquidsoap is not None:
            try:
                outcome = self._render_liquidsoap()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Planned restart: re-render failed (%s) - restarting "
                    "with the existing rastatime.liq.",
                    exc,
                )
        # RASTATIME 2026-09-07: name-safe or not at all.  A device_id
        # render is only valid for the device list it was taken from;
        # on 09-06 and 09-07 the display was asleep at 04:01, the index
        # pointed at another endpoint and the fresh instance crash-looped
        # until 08:21.  The running instance is healthy - keep it.
        if getattr(outcome, "main_output_mode", None) == MAIN_OUTPUT_BY_INDEX:
            logger.error(
                "Planned Liquidsoap restart skipped: the fresh render addresses "
                "the Main Output by PortAudio index (no name-safe entry right "
                "now: display asleep, device renamed, or a non-MME/WASAPI "
                "match).  The running instance keeps playing.  Check "
                "Settings -> Local Machine -> Main Output."
            )
            return True
        if not restart_liquidsoap_service(
            f"planned restart ({reason})",
            verify=self._liquidsoap_restarted_recently,
        ):
            logger.error(
                "Planned Liquidsoap restart failed - the running instance "
                "keeps going; restart PLAYOUT, then LIQUIDSOAP, manually."
            )
            return True
        self._after_liquidsoap_restart()
        # RASTATIME 2026-09-16 - the fresh instance carries the current
        # settings: new baseline for the settings change detector.
        self._rendered_fingerprint = (
            self._current_settings_fingerprint() or self._rendered_fingerprint
        )
        self._render_restart_pending = False
        # The 30-minute hold is for FAILED attempts only - live 2026-09-16 the
        # folder change (16:53) was applied at once, the bitrate change saved
        # six minutes later waited until 17:24 behind it.
        self._settings_restart_attempted_at = None
        if settle_async:
            t = threading.Thread(
                target=self._settle_after_restart,
                args=(outcome,),
                daemon=True,
                name="liquidsoap-settle-check",
            )
            t.start()
        else:
            self._settle_after_restart(outcome)
        return True

    def _settle_after_restart(self, outcome: object = None) -> bool:
        """
        RASTATIME 2026-10-02 - the stays-up check, and the one automatic
        way out it has: a render with Stereo Tool whose instance dies at
        start (library incompatible, licence refused - `--check` does not
        see it) is rendered again WITHOUT Stereo Tool and restarted, with
        the lockout set for the rest of this PLAYOUT run.  Everything else
        stays as loud as before (operator restarts by hand).
        """
        if self._confirm_liquidsoap_stays_up():
            return True
        if not getattr(outcome, "stereotool_active", False):
            return False
        return self._fall_back_without_stereotool()

    def _fall_back_without_stereotool(self) -> bool:
        from .liquidsoap_config import STEREOTOOL_LOCKOUT  # noqa: PLC0415

        STEREOTOOL_LOCKOUT["active"] = True
        STEREOTOOL_LOCKOUT["reason"] = (
            "Liquidsoap did not stay up after a start with Stereo Tool at "
            + datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        logger.error(
            "Stereo Tool: the fresh Liquidsoap instance died within seconds - "
            "rendering WITHOUT Stereo Tool and restarting; it stays off until "
            "the next PLAYOUT restart.  Check the library path, the licence "
            "and the newest logs/liquidsoap-stdout*.log (Settings -> Streams "
            "-> Output Processing)."
        )
        if self._render_liquidsoap is not None:
            try:
                self._render_liquidsoap()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error("Stereo Tool fallback: re-render failed: %s", exc)
                return False
        if not restart_liquidsoap_service(
            "fallback without Stereo Tool",
            verify=self._liquidsoap_restarted_recently,
        ):
            logger.error("Stereo Tool fallback: restart failed - restart LIQUIDSOAP by hand.")
            return False
        self._after_liquidsoap_restart()
        self._rendered_fingerprint = (
            self._current_settings_fingerprint() or self._rendered_fingerprint
        )
        return self._confirm_liquidsoap_stays_up()

    def _liquidsoap_restarted_recently(
        self,
        timeout: float = 30.0,
        fresh_seconds: float = 120.0,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """
        Did LIQUIDSOAP come back as a *fresh* instance?  Polls the
        telnet ``uptime`` for up to ``timeout`` seconds and returns
        True once it answers with less than ``fresh_seconds``.

        Passed to :func:`restart_liquidsoap_service` as ``verify``:
        ``nssm restart`` exits 1 even when stop and start both happened
        (2026-09-07), and a blind retry would restart the fresh
        instance again.
        """
        reader = getattr(self._engine, "liquidsoap_uptime_seconds", None)
        if reader is None:
            return False
        sleep = sleep or time.sleep
        deadline = time.monotonic() + timeout
        while True:
            uptime = reader()
            if (
                isinstance(uptime, (int, float))
                and not isinstance(uptime, bool)
                and 0 <= uptime < fresh_seconds
            ):
                logger.info(
                    "Liquidsoap is back as a fresh instance (uptime %.0f s).",
                    uptime,
                )
                return True
            if time.monotonic() >= deadline:
                return False
            sleep(1.0)

    def _confirm_liquidsoap_stays_up(
        self,
        settle_seconds: float = 10.0,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """
        After a restart: wait ``settle_seconds`` and check that the
        instance is still there.  A Liquidsoap that cannot open its
        Main Output dies within ~2 s of start and NSSM throttles it
        into a crash loop - that must be loud, not "no warnings
        active" (the 2026-09-07 04:02-08:21 outage).
        """
        reader = getattr(self._engine, "liquidsoap_uptime_seconds", None)
        if reader is None:
            return True
        (sleep or time.sleep)(settle_seconds)
        uptime = reader()
        alive = isinstance(uptime, (int, float)) and not isinstance(uptime, bool) and uptime >= 0
        if alive:
            logger.info(
                "Nightly restart: Liquidsoap still up after %.0f s (uptime %.0f s).",
                settle_seconds,
                uptime,
            )
            return True
        logger.error(
            "Nightly restart: Liquidsoap is DOWN again %.0f s after the restart "
            "- a crash loop (NSSM throttling)?  Most likely the Main Output "
            "device: read the newest logs/liquidsoap-stdout-*.log, then "
            "restart PLAYOUT and LIQUIDSOAP manually once the cause is "
            "fixed.",
            settle_seconds,
        )
        return False

    def _after_liquidsoap_restart(self, attempts: int = 15, delay: float = 2.0) -> None:
        """
        Put the fresh instance into the state it has right after a
        playout start: nothing playing, nothing pre-warmed, recording
        sentinel stopped, gates open.  Telnet needs a few seconds to
        come up, hence the retries.
        """
        with self._lock:
            self._prepared = None
            self._playing_key = None
            self._current_event = None
            # RASTATIME 2026-09-28 - the fresh instance has an empty queue:
            # a successor queued ahead in the old one is gone with it.  The
            # planned boundary restart at 20:27:08 kept the bookkeeping,
            # the successor's PLAY "adopted" a queue with nothing on it and
            # the station was silent until the next row.
            self._queued_ahead = None
            self._queued_ahead_prev = None
            self._current_started_at = None
            self._current_clip_seconds = None
        # RASTATIME 2026-11-02 - the engine's own "on air" mirror must go
        # too, or the catch-up of the same file takes the idempotent
        # shortcut and never pushes (rehearsal 02:30:57, silent station).
        self._forget_engine_playback_state("Planned Liquidsoap restart")
        if self._retry_initial_liquidsoap_state(attempts, delay, sleep=time.sleep):
            logger.info("Nightly restart: Liquidsoap is back, sentinel stopped, gates reset.")
            self._request_source_reconcile()
            # RASTATIME 2026-11-02 - re-arm the running item now, not at the
            # next 120-s poll (the rehearsal waited 2 min for the catch-up).
            self._schedule_refresh_soon("Planned Liquidsoap restart")
        else:
            logger.error(
                "Nightly restart: Liquidsoap telnet did not come back within %d attempts.",
                attempts,
            )

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-06 - initial Liquidsoap state with retries
    # ------------------------------------------------------------------

    def _apply_initial_liquidsoap_state(
        self,
        reset_gates: bool = True,
    ) -> tuple[bool, Optional[BaseException]]:
        """
        One attempt: ``recording.stop`` (raises while telnet is down,
        so it doubles as the readiness probe) and then, unless
        ``reset_gates`` is False, both bus gates open.  Returns
        ``(ok, exception)``.  The constructor passes ``reset_gates=False``
        - ``__main__`` resets the gates itself right after construction.
        """
        try:
            self._engine.recording_stop()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return False, exc
        if reset_gates:
            self.reset_gates()
        # A fresh instance starts with linein.gain at unity; a line-in on
        # air keeps its trim across the restart (2026-10-02).
        current = getattr(self, "_current_event", None)
        if isinstance(current, LineinEvent):
            self._apply_linein_gain(current)
        # Seed the restart detector with this instance's uptime so a
        # later drop is recognised as a fresh Liquidsoap (2026-09-07).
        if hasattr(self._engine, "liquidsoap_uptime_seconds"):
            self._last_liquidsoap_uptime = self._engine.liquidsoap_uptime_seconds()
        # The process-table detector (2026-09-09) re-seeds itself on the
        # next cycle; a fresh baseline avoids a second "restarted" round
        # after a planned restart.
        self._last_liquidsoap_process = None
        # A fresh instance starts with the rendered ICY defaults; push the
        # live values again on the next refresh (2026-09-13).
        self._icy_pushed = None
        self._bus_show_pushed = None
        return True, None

    def _retry_initial_liquidsoap_state(
        self,
        attempts: int,
        delay: float,
        sleep: Callable[[float], None],
    ) -> bool:
        for attempt in range(1, attempts + 1):
            ok, exc = self._apply_initial_liquidsoap_state()
            if ok:
                if attempt > 1:
                    logger.info(
                        "PlayoutScheduler: Liquidsoap telnet is back (attempt %d): "
                        "recording sentinel stopped, gates reset.",
                        attempt,
                    )
                return True
            logger.debug("PlayoutScheduler: Liquidsoap not ready (attempt %d): %s", attempt, exc)
            if attempt < attempts:
                sleep(delay)
        return False

    def _forget_queued_ahead(self, why: str) -> None:
        """
        RASTATIME 2026-09-28 - a fresh Liquidsoap instance has an empty
        queue: a successor queued ahead in the old one is gone with it,
        and its PLAY must push afresh instead of adopting nothing (the
        20:27:08 boundary restart left the station silent).
        """
        if self._queued_ahead is not None:
            logger.info(
                "%s: forgetting the queued-ahead successor %s (the fresh "
                "instance's queue is empty).",
                why,
                self._queued_ahead[0],
            )
        self._queued_ahead = None
        self._queued_ahead_prev = None

    def _forget_current_after_restart(self, why: str) -> None:
        """
        RASTATIME 2026-11-02 - an UNPLANNED Liquidsoap restart (crash +
        NSSM restart, or the operator's ``nssm restart`` a few seconds
        after PLAYOUT's own start) leaves the fresh instance on
        ``silence_fallback``: its queue is empty, but this scheduler
        still believed the running item was on air and never pushed it
        again - the station stayed silent until the row ended or PLAYOUT
        was restarted (fresh-machine rehearsal 2026-11-02 02:28, ~6 min
        of silence).  The planned restart path (``_after_liquidsoap_restart``)
        clears the same bookkeeping; do it here too, so the refresh pass
        that follows the detection re-arms the running item as a catch-up
        (``Catch-up: in-progress event ... entering at +N s``) exactly
        like a PLAYOUT start does.  A pre-warmed source died with the old
        instance as well.
        """
        with self._lock:
            current = self._current_event
            self._prepared = None
            self._playing_key = None
            self._current_event = None
            self._current_started_at = None
            self._current_clip_seconds = None
        if current is not None:
            logger.warning(
                "%s: the fresh instance plays nothing - re-arming %r as a catch-up "
                "on this refresh pass.",
                why,
                getattr(current, "track_title", None) or getattr(current, "uri", None) or current,
            )
        self._forget_engine_playback_state(why)

    def _forget_engine_playback_state(self, why: str) -> None:
        """
        RASTATIME 2026-11-02 - drop the engine's "what is on air" mirror
        after a Liquidsoap restart (see ``LiquidsoapPlayoutEngine.
        forget_playback_state``); a catch-up of the same file must push
        again instead of taking the deferred-stop idempotency shortcut.
        """
        forget = getattr(self._engine, "forget_playback_state", None)
        if callable(forget):
            try:
                forget(why)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("%s: engine state reset raised: %s", why, exc)

    def _schedule_refresh_soon(self, why: str, delay: float = 1.0) -> None:
        """
        RASTATIME 2026-11-02 - run ``refresh()`` on a daemon Timer instead
        of waiting for the next poll: after a planned Liquidsoap restart
        the running item is re-armed within a second, not within 120 s
        (the rehearsal's station was silent for the whole interval).
        Coalescing: while one such refresh is pending, further requests
        (the three outputs reconnect within a second) are folded into it.
        """
        with self._refresh_soon_lock:
            if self._refresh_soon_pending:
                return
            self._refresh_soon_pending = True
        logger.info("%s: refreshing the schedule in %.0f s to re-arm the running item.", why, delay)

        def _run() -> None:
            with self._refresh_soon_lock:
                self._refresh_soon_pending = False
            try:
                self.refresh()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("%s: the early refresh failed: %s", why, exc)

        t = threading.Timer(delay, _run)
        t.daemon = True
        t.start()

    def request_refresh_soon(self, why: str, delay: float = 2.0) -> None:
        """
        RASTATIME 2026-11-02 - public entry for the stream-status reporter:
        an ``output.icecast`` that (re)connects is the first sign of a fresh
        Liquidsoap instance, so the restart detection at the top of
        ``refresh()`` runs seconds after the restart instead of at the next
        poll (studio probe 12:10: 68 s of silence until the 120-s cycle).
        """
        self._schedule_refresh_soon(why, delay)

    def _maybe_reinit_after_liquidsoap_restart(self) -> None:
        """
        Detect a Liquidsoap restart and re-apply the initial state
        (recording sentinel stop + gates).  Called each refresh.

        RASTATIME 2026-09-09: the process table is the primary signal -
        a new PID, or a younger age of the main instance than last cycle
        (``_liquidsoap_process_identity``) - because it costs no telnet
        command (every telnet command leaks ~87-155 KB on the Windows
        build and ``uptime`` was one of the last three periodic ones).
        The telnet ``uptime`` drop of 2026-09-07 remains the fallback
        while the process table cannot be read.
        """
        ident = self._liquidsoap_process_identity()
        if ident is not None:
            self._maybe_reinit_by_process(ident)
            return
        if not hasattr(self._engine, "liquidsoap_uptime_seconds"):
            return
        uptime = self._engine.liquidsoap_uptime_seconds()
        # Contract is float|None; anything else (unreachable telnet, a
        # loosely-mocked engine) is treated as "unknown" and ignored.
        if not isinstance(uptime, (int, float)) or isinstance(uptime, bool):
            return
        prev = self._last_liquidsoap_uptime
        if isinstance(prev, (int, float)) and not isinstance(prev, bool) and uptime + 5.0 < prev:
            logger.warning(
                "Liquidsoap restarted under PLAYOUT (uptime %.0f s < previous "
                "%.0f s) - re-sending recording.stop and reopening the gates.",
                uptime,
                prev,
            )
            ok, exc = self._apply_initial_liquidsoap_state()  # also re-seeds uptime
            if not ok:
                logger.warning(
                    "Post-restart re-init failed (telnet not ready yet?): %s - retrying next poll.",
                    exc,
                )
                return
            self._forget_queued_ahead("Liquidsoap restarted")
            self._forget_current_after_restart("Liquidsoap restarted")
            self._request_source_reconcile()
        else:
            self._last_liquidsoap_uptime = uptime

    def _maybe_reinit_by_process(self, ident: tuple[int, float]) -> None:
        """
        Process-table restart detector (2026-09-09): a new PID, or the
        same PID with a younger age than last cycle, is a fresh instance.
        The first call after a start or a planned restart only seeds.
        """
        pid, age = ident
        prev = self._last_liquidsoap_process
        if prev is None:
            self._last_liquidsoap_process = ident
            return
        prev_pid, prev_age = prev
        if pid == prev_pid and age + 5.0 >= prev_age:
            self._last_liquidsoap_process = ident
            return
        logger.warning(
            "Liquidsoap restarted under PLAYOUT (pid %d, %.0f s old; before pid "
            "%d, %.0f s) - re-sending recording.stop and reopening the gates.",
            pid,
            age,
            prev_pid,
            prev_age,
        )
        ok, exc = self._apply_initial_liquidsoap_state()
        if not ok:
            logger.warning(
                "Post-restart re-init failed (telnet not ready yet?): %s - retrying next poll.",
                exc,
            )
            return  # baseline kept -> detected again next cycle
        self._last_liquidsoap_process = ident
        self._forget_queued_ahead("Liquidsoap restarted")
        self._forget_current_after_restart("Liquidsoap restarted")
        self._request_source_reconcile()

    def ensure_liquidsoap_initial_state(
        self,
        attempts: int = 45,
        delay: float = 2.0,
        background: bool = True,
    ) -> Optional[bool]:
        """
        Keep trying to put Liquidsoap into its start state until its
        telnet answers (default: up to 90 s).

        Why: PLAYOUT regularly comes up before LIQUIDSOAP - the manual
        restart order, the boot-window restart in ``__main__`` and the
        nightly restart all leave a window in which the old single
        attempt failed silently; the fresh instance then recorded the
        ``_uninitialized.mp3`` sentinel for hours and kept whatever
        gate state it booted with.  ``background=False`` runs the loop
        inline (tests) and returns the result.
        """
        if not hasattr(self._engine, "recording_stop"):
            return None
        if self._initial_state_ok:
            return True
        if not background:
            ok = self._retry_initial_liquidsoap_state(attempts, delay, sleep=time.sleep)
            self._initial_state_ok = ok
            return ok

        def _worker() -> None:
            if self._retry_initial_liquidsoap_state(attempts, delay, sleep=time.sleep):
                self._initial_state_ok = True
            else:
                logger.error(
                    "PlayoutScheduler: Liquidsoap telnet never answered within "
                    "%.0f s - recording sentinel and gates are in an unknown "
                    "state; restart PLAYOUT once Liquidsoap is up.",
                    attempts * delay,
                )

        t = threading.Thread(target=_worker, name="liquidsoap-initial-state", daemon=True)
        t.start()
        return None

    def shutdown(self) -> None:
        """Cancel all pending timers, stop the engine and the line-in capture."""
        logger.info("PlayoutScheduler: shutting down …")
        with self._lock:
            self._cancel_all_timers()
        self._engine.stop()
        # RASTATIME 2026-05-12 — also release the Line-In capture so
        # the microphone device handle is freed.  Otherwise it would
        # stay locked until the OS reaped the orphaned ffmpeg subprocess.
        if self._linein_capture is not None:
            self._linein_capture.close()
        # RASTATIME 2026-05-28 — Phase-C5 Teil 2d: gracefully stop any
        # in-flight show recording on the Liquidsoap side so the .mp3
        # is playable (MP3 has no container trailer so it would still
        # be playable without a clean stop, but tidier this way).
        # Errors are logged but not raised — shutdown must complete.
        try:
            self._engine.recording_stop()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Shutdown: Liquidsoap recording_stop failed: %s",
                exc,
            )
        logger.info("PlayoutScheduler: shutdown complete")

    # ------------------------------------------------------------------
    # Timer management  (must hold self._lock)
    # ------------------------------------------------------------------

    def _cancel_all_timers(self) -> None:
        for _key, (start_t, stop_t) in list(self._timers.items()):
            if start_t is not None:
                start_t.cancel()
            if stop_t is not None:
                stop_t.cancel()
        self._timers.clear()
        for t in self._prepare_timers.values():
            t.cancel()
        self._prepare_timers.clear()
        # Parallel armed-events lookup is cleared in lockstep so
        # ``_on_stop``'s same-device-follow-up check sees a consistent
        # snapshot of "what's armed right now" (rather than ghosts of
        # the previous refresh).
        self._armed_events.clear()
        self._deferred_queue_ahead = None  # re-armed by the queue-ahead timers

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
                key,
                start_delay,
                event.track_title,
            )
            self._arm_queue_ahead(key, event, start_delay)

        elif key != self._playing_key and self._same_scheduled_item(self._current_event, event):
            # RASTATIME 2026-09-04 - same item, new key (see
            # _same_scheduled_item): adopt the key, do not re-play.
            logger.info(
                "Catch-up skipped: %s is the playing track under a new key (%s -> %s); rebinding.",
                event.track_title,
                self._playing_key,
                key,
            )
            self._playing_key = key

        elif key != self._playing_key and any(
            self._same_scheduled_item(starting, event) for starting in list(self._starting.values())
        ):
            # RASTATIME 2026-10-03 - the refresh landed in the row's start
            # second: its timer PLAY is running this very moment.  A
            # catch-up here pushed the same jingle a second time (12:17:55).
            logger.info(
                "Catch-up skipped: %s (%r) is starting right now - its timer fired this second.",
                key,
                event.track_title,
            )

        elif key != self._playing_key and self._precedes_playing(event):
            # RASTATIME 2026-09-28 - a refresh that spans a track boundary
            # (the API fetch takes ~4 s) re-arms the predecessor whose row
            # still overlaps by the crossfade: it is in progress by the
            # clock but the scheduler has moved on.  Catching it up cut
            # the successor and left dead air (20:05:36 incident).
            logger.info(
                "Catch-up skipped: %s (%r) precedes the playing item %s.",
                key,
                event.track_title,
                self._playing_key,
            )

        elif key != self._playing_key:
            # Event has already started but we are NOT playing it.
            # This covers: (a) service restart during a running show,
            # (b) first schedule refresh that discovers an in-progress track,
            # (c) late schedule detection.
            # Start playback immediately (delay=0).
            # RASTATIME 2026-09-28 - enter the track at the offset it
            # would be at (the resume path after a DJ hand-back did this
            # all along; the catch-up replayed the track from the top -
            # 2026-09-28 18:21: 'Fade' restarted 141 s in, the next track
            # then found 140 s of audio left where the rows said 2 s).
            seek = -start_delay
            logger.info(
                "Catch-up: in-progress event %s (started %.0fs ago)  track=%r "
                "- entering at +%.1f s",
                key,
                seek,
                event.track_title,
                seek,
            )
            start_t = threading.Timer(0, self._on_file_start, args=(key, event, seek))
            start_t.daemon = True
            start_t.start()

        else:
            # We are already playing this event — don't restart it.
            logger.debug(
                "Skipping re-arm for currently-playing event %s  track=%r",
                key,
                event.track_title,
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
        elif key != self._playing_key and self._same_scheduled_item(self._current_event, event):
            # RASTATIME 2026-09-04 - same item, new key: rebind instead of
            # reconnecting the stream (an audible gap).
            logger.info(
                "Catch-up skipped: web stream already playing under a new "
                "key (%s -> %s); rebinding.",
                self._playing_key,
                key,
            )
            self._playing_key = key
        elif key != self._playing_key and self._precedes_playing(event):
            logger.info(
                "Catch-up skipped: web stream %s precedes the playing item %s.",
                key,
                self._playing_key,
            )
        elif key != self._playing_key:
            logger.info(
                "Catch-up: in-progress web stream %s (started %.0fs ago)",
                key,
                -start_delay,
            )
            start_t = threading.Timer(0, self._on_webstream_start, args=(key, event))
            start_t.daemon = True
            start_t.start()

        self._arm_prepare(key, event, start_delay, self._on_webstream_prepare)
        stop_t = threading.Timer(stop_delay, self._on_stop, args=(key,))
        stop_t.daemon = True
        stop_t.start()

        self._timers[key] = (start_t, stop_t)
        self._armed_events[key] = event
        logger.debug(
            "Armed WebStreamEvent %s: start=%.1fs stop=%.1fs  uri=%s",
            key,
            start_delay,
            stop_delay,
            event.uri,
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
            start_t = threading.Timer(start_delay, self._on_linein_start, args=(key, event))
            start_t.daemon = True
            start_t.start()
        elif key != self._playing_key and self._precedes_playing(event):
            logger.info(
                "Catch-up skipped: line-in %s precedes the playing item %s.",
                key,
                self._playing_key,
            )
        elif key != self._playing_key:
            # RASTATIME 2026-09-03 - a schedule refresh can hand the SAME
            # in-progress line-in back under a DIFFERENT key (seen live:
            # "<ts>_2" at start, bare "<ts>" 70 s later).  The old guard
            # only compared keys, so catch-up re-played it and
            # linein_start_http tore the http source down and back up
            # mid-show -- the audible ~1 s dropout the operator reported
            # at 15:16.  The capture itself was idempotent ("already
            # capturing"), so the source bounce was the whole damage.
            # Skip catch-up when the same device + channel mapping is
            # already on air, but adopt the new key so the _on_stop armed
            # below still matches.
            # 2026-09-04: identity instead of device+mapping (Option A,
            # see _same_scheduled_item); is_running stays, because a dead
            # capture is exactly what catch-up should rescue.
            already_on_air = (
                self._same_scheduled_item(self._current_event, event)
                and self._linein_capture is not None
                and self._linein_capture.is_running
            )
            if already_on_air:
                logger.info(
                    "Catch-up skipped: line-in already on air with the same "
                    "device+channels (key %s -> %s); not bouncing the source.",
                    self._playing_key,
                    key,
                )
                self._playing_key = key
                # Nothing to arm: the source is already playing.  None is
                # the same "no start timer" marker the resume path stores,
                # and both consumers (_cancel_all_timers, the same-device
                # follow-up check in _on_stop) already handle it.
                start_t = None
            else:
                logger.info(
                    "Catch-up: in-progress line-in %s (started %.0fs ago)  name=%r",
                    key,
                    -start_delay,
                    event.name,
                )
                start_t = threading.Timer(0, self._on_linein_start, args=(key, event))
                start_t.daemon = True
                start_t.start()

        self._arm_prepare(key, event, start_delay, self._on_linein_prepare)
        stop_t = threading.Timer(stop_delay, self._on_stop, args=(key,))
        stop_t.daemon = True
        stop_t.start()

        self._timers[key] = (start_t, stop_t)
        self._armed_events[key] = event
        logger.debug(
            "Armed LineinEvent %s: start=%.1fs stop=%.1fs  device=%s",
            key,
            start_delay,
            stop_delay,
            event.device_id,
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
            key,
            event.type.value,
            delay,
            event.show_id,
            event.show_name,
        )

    # ------------------------------------------------------------------
    # Timer callbacks (run in daemon threads)
    # ------------------------------------------------------------------

    def _precedes_playing(self, event: object) -> bool:
        """
        RASTATIME 2026-09-28 - ``event`` sits at or before the item on
        air in schedule order.  Such a row is never caught up: the
        scheduler has already moved past it (its row merely overlaps the
        successor by the crossfade, or the refresh straddled the
        boundary).  With nothing on air every in-progress row is a
        legitimate catch-up.

        RASTATIME 2026-10-02 - the playing item itself never "precedes":
        a refresh that hands it back under a new key (``<ts>_2`` ->
        ``<ts>``, see _same_scheduled_item) has to reach the rebind
        branch of its arm path, or the stop timer armed under the new
        key dies on _on_stop's stale-key check and the slot never ends.
        The file and web stream paths test identity before this guard;
        the line-in path tests it after - so the exclusion lives here,
        once, for all three.
        """
        cur = self._current_event
        if cur is None or self._playing_key is None:
            return False
        if self._same_scheduled_item(cur, event):
            return False
        return getattr(event, "start", None) is not None and event.start <= cur.start  # type: ignore[attr-defined]

    def _plausible_remaining(
        self,
        now: datetime,
        started_at: Optional[datetime],
        clip_seconds: Optional[float],
    ) -> Optional[float]:
        """
        RASTATIME 2026-09-28 - the most audio a file track pushed at
        ``started_at`` with ``clip_seconds`` of audio can still have: that
        minus the time since, plus the cross buffer (an adopted track's
        audio starts up to BUFFER after its PLAY) and 2 s of slack.
        ``None`` when unknown.
        """
        if started_at is None or clip_seconds is None:
            return None
        elapsed = (now - started_at).total_seconds()
        return max(0.0, clip_seconds - elapsed) + self._cross_buffer_seconds + 2.0

    def _file_audio_end(self, event: FileEvent) -> datetime:
        """
        RASTATIME 2026-09-29 - when the audio of a file track leaves the
        air: exact row start + clip + the lag of the file chain.  The
        engine cannot be asked: inside the last BUFFER seconds the queue
        has handed the track to the cross operator's tail and reports
        nothing for it.
        """
        start = event.start_exact or event.start
        clip = float(event.cue_out or 0.0) - float(event.cue_in or 0.0)
        end = start + timedelta(seconds=clip) if clip > 0 else (event.end_exact or event.end)
        lag = self._file_chain_lag
        if lag is None:
            lag = FILE_CHAIN_LAG_DEFAULT_SECONDS
        return end + timedelta(seconds=lag)

    def _catch_up_after_boundary_restart(
        self,
        key: str,
        event: FileEvent,
        seek: float,
    ) -> float:
        """
        RASTATIME 2026-10-02 - operator decision (a): after a planned restart
        at the track boundary the track enters its audio by the time the
        restart took, so the rows stay the truth; (b) - letting the chain
        run late until the next live item - was declined.  Returns the seek
        to use; a short delay (timer granularity) leaves it alone.
        """
        start = event.start_exact or event.start
        elapsed = (datetime.utcnow() - start).total_seconds()
        if elapsed - seek < BOUNDARY_RESTART_CATCHUP_MIN_SECONDS:
            return seek
        logger.info(
            "PLAY  %s: the boundary restart took %.1f s - entering the track at "
            "+%.1f s so the show stays on its rows.",
            key,
            elapsed - seek,
            elapsed,
        )
        return elapsed

    def _note_file_chain_lag(self, event: FileEvent, seek: float) -> None:
        """A push onto an idle queue starts a chain: audio position vs. rows."""
        start = event.start_exact or event.start
        lag = (datetime.utcnow() - start).total_seconds() - seek
        self._file_chain_lag = max(-1.0, min(lag, 10.0))

    def _carry_file_chain_lag(self, prev_event: object, event: FileEvent, mode: str) -> None:
        """
        RASTATIME 2026-10-02 - an adopted track starts when its
        predecessor's audio ends, minus the overlap of the pair (none at a
        show boundary, where the old tail plays out first).  Rows that
        abut keep the chain's lag; a gap in the layout - the 0.3 s between
        a StationID clipped at 59.7 and the next show at :00 - is swallowed
        on air and shortens the lag by that much (the 08:00 block started
        exactly on its rows while the model still said +0.3 s).
        """
        if not isinstance(prev_event, FileEvent):
            return
        overlap = 0.0 if mode.startswith("show") else self._pair_crossfade(prev_event, event)
        audio_start = self._file_audio_end(prev_event) - timedelta(seconds=overlap)
        lag = (audio_start - (event.start_exact or event.start)).total_seconds()
        lag = max(-1.0, min(lag, 10.0))
        if self._file_chain_lag is None or abs(lag - self._file_chain_lag) > 0.005:
            logger.info(
                "PLAY  %s: the file chain runs %.2f s behind the rows (was %s).",
                event.track_title or event.id,
                lag,
                "unknown" if self._file_chain_lag is None else f"{self._file_chain_lag:.2f} s",
            )
        self._file_chain_lag = lag

    def _dj_on_air(self) -> bool:
        return bool(self._switcher and self._switcher.current_state != SourceState.SCHEDULED)

    def _wait_for_exact_time(self, key: str, when: Optional[datetime], what: str) -> bool:
        """
        RASTATIME 2026-10-01 - timers fire on the whole second before the
        row time; wait for the exact time (at most EXACT_TIME_HOLD_MAX_SECONDS
        - more means the timer was late or the row is odd, act now).  False
        when another item took the spotlight during the wait.
        """
        if when is None or self._dj_on_air():
            return True
        delay = (when - datetime.utcnow()).total_seconds()
        if delay <= 0.02 or delay > EXACT_TIME_HOLD_MAX_SECONDS:
            return True
        logger.info("%s  %s: the row's exact time is in %.2f s - waiting.", what, key, delay)
        time.sleep(delay)
        if self._playing_key != key:
            logger.info(
                "%s  %s: superseded by %s during the wait - leaving the engine alone.",
                what,
                key,
                self._playing_key,
            )
            return False
        return True

    def _hold_live_start(self, key: str, prev_event: object, event: object) -> bool:
        """
        RASTATIME 2026-09-29 - a pre-warmed live item: after a file track
        wait until the track's audio is over (minus the overlap of the
        pair), after anything else (2026-10-01) until the row's exact
        start, before the gate opens.  False when another item took the
        spotlight during the wait - the caller then leaves the engine alone.
        """
        if self._dj_on_air():
            return True
        if self._prepared is None or not self._same_scheduled_item(self._prepared[1], event):
            return True  # a cold start has its own start-up time
        if not isinstance(prev_event, FileEvent):
            return self._wait_for_exact_time(key, getattr(event, "start_exact", None), "PLAY")
        overlap = min(self._track_crossfade(prev_event), self._input_transition_seconds)
        left = (self._file_audio_end(prev_event) - datetime.utcnow()).total_seconds()
        hold = left - overlap
        if hold <= 0.05:
            return True
        if hold > FILE_TAIL_HOLD_MAX_SECONDS:
            logger.info(
                "PLAY  %s: %r has %.1f s of audio left - overbook, the live item starts now.",
                key,
                prev_event.track_title or prev_event.id,
                left,
            )
            return True
        logger.info(
            "PLAY  %s: %r has %.2f s of audio left (overlap %.2f s) - the gate opens in %.2f s.",
            key,
            prev_event.track_title or prev_event.id,
            left,
            overlap,
            hold,
        )
        time.sleep(hold)
        if self._playing_key != key:
            logger.info(
                "PLAY  %s: superseded by %s during the wait - leaving the engine alone.",
                key,
                self._playing_key,
            )
            return False
        return True

    def _let_file_run_out(self, key: str, event: object) -> None:
        """
        RASTATIME 2026-09-29 - the stop timer of a file track fires on the
        whole second before its row end: wait for the audio to be over, so
        neither the deferred skip nor the bookkeeping reset comes early.
        """
        if not isinstance(event, FileEvent) or self._dj_on_air():
            return
        left = (self._file_audio_end(event) - datetime.utcnow()).total_seconds()
        if left <= 0.05 or left > FILE_TAIL_HOLD_MAX_SECONDS:
            return
        logger.info(
            "STOP  %s: %.2f s of audio left - letting the track run out.",
            key,
            left,
        )
        time.sleep(left)

    @staticmethod
    def _same_scheduled_item(a: object, b: object) -> bool:
        """
        RASTATIME 2026-09-04 - identity of a schedule item, independent
        of its event KEY.

        Keys are ``<start timestamp>`` plus an ``_N`` suffix that
        ``insert_event`` hands out by INSERTION ORDER when several
        events share a start second (show-record start/end, the
        webstream buffer/output pair, ...).  As time passes, events at
        the same second drop out of the fetch window and the survivors'
        suffixes shift -- the same running slot came back as
        ``<ts>_0`` in one refresh and bare ``<ts>`` in the next
        (2026-09-04 11:08:17).  Anything that trusts keys across a
        refresh therefore has to compare by identity instead:

          * same event class and kind,
          * same schedule row (``row_id``) and the same medium (``id``:
            the file, the webstream or the line-in configuration),
          * for line-ins additionally the same device + channel
            mapping, so an edited row is NOT mistaken for the running
            one (the capture would keep the old device).

        The START is deliberately NOT part of the identity (2026-09-28):
        a show-builder edit of the running show re-times the rows that
        follow, including the running one (18:30:16: ``schedule-remove``
        moved the playing row 9 s and its cue-in 2 s, same row id).  With
        the start in the comparison that row counted as "removed from
        schedule" and the catch-up restarted the same track from its
        top.  Row ids are serial and never reused, so row + medium is
        identity enough; ``refresh()`` treats a row moved into the
        future as gone (it starts again at its new start).

        Show-record events carry no row_id; they never occupy the
        playing slot, so they simply never match.
        """
        if a is None or b is None or type(a) is not type(b):
            return False
        if getattr(a, "type", None) != getattr(b, "type", None):
            return False
        if getattr(a, "row_id", None) is None:
            return False
        if a.row_id != b.row_id:  # type: ignore[attr-defined]
            return False
        if getattr(a, "id", None) != getattr(b, "id", None):
            return False
        if isinstance(a, LineinEvent):
            return (
                a.device_id == b.device_id  # type: ignore[attr-defined]
                and list(getattr(a, "channel_mapping", None) or [0, 1])
                == list(getattr(b, "channel_mapping", None) or [0, 1])
            )
        return True

    def _close_predecessor_source(self, prev_event: object, key: str) -> None:
        """
        RASTATIME 2026-09-04 - the successor closes the predecessor's
        EXCLUSIVE source (line-in capture + source, or the webstream
        source) instead of trusting the predecessor's own _on_stop to
        get there first.

        Why: _on_stop and the successor's _on_*_start fire on separate
        Timer threads at the same wallclock instant, and _on_stop bails
        out the moment it is no longer the playing key (race fix #1).
        If the successor wins the race, nobody closes the line-in --
        and a line-in that stays up outranks every scheduled track in
        the bus switch (webstreams outrank it, and drop back onto it
        when they end).  That is exactly the 2026-09-04 11:00 incident,
        reached through the follow-up rule instead of the race; this
        closes the race-shaped door as well.

        Every call here is idempotent (capture.stop on a stopped capture,
        ``linein_stop`` / ``webstream_stop`` reply "Done" on an idle
        source), so it does not matter whether _on_stop already ran.
        A file predecessor needs nothing: engine.stop() handles the
        request queue.  Line-in -> line-in is NOT routed here -- that
        transition has its own same-device shortcut / bounce logic in
        _on_linein_start.
        """
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            return  # a DJ is on air; sources stay as they are
        if isinstance(prev_event, LineinEvent):
            logger.info(
                "PLAY %s takes over from line-in %r - releasing it.",
                key,
                prev_event.name,
            )
            self._release_linein(f"successor {key}")
        elif isinstance(prev_event, WebStreamEvent):
            logger.info(
                "PLAY %s takes over from web stream %s - releasing it.",
                key,
                prev_event.uri,
            )
            self._release_webstream(f"successor {key}")

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-04 - Paket 2: pre-warm + gates + drained stop
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-27 - crossfade: queue-ahead + shape decision
    # ------------------------------------------------------------------

    def _arm_queue_ahead(self, key: str, event: FileEvent, start_delay: float) -> None:
        """Arm the queue-ahead timer at start - (BUFFER + margin)."""
        lead = start_delay - (self._cross_buffer_seconds + QUEUE_AHEAD_MARGIN_SECONDS)
        if lead < 0:
            if start_delay < 0.5:
                return  # too close: the track starts the normal way
            lead = 0.0  # a refresh landed inside the lead window: queue now
        t = threading.Timer(lead, self._on_file_queue_ahead, args=(key, event))
        t.daemon = True
        t.start()
        self._prepare_timers[f"{key}/queue"] = t

    @staticmethod
    def _natural_end(event: FileEvent) -> datetime:
        """
        When the track's audio really ends: start + (cue_out - cue_in).
        The row end (``event.end``) is clipped to the show end for a track
        that runs past its show (the API cuts ``ends_at`` there), so it
        says nothing about how much audio is left - the 2026-09-27
        rehearsal saw "0.0 s left" for a track with 45 s to go.
        """
        clip = float(event.cue_out or 0.0) - float(event.cue_in or 0.0)
        if clip <= 0:
            return event.end
        return event.start + timedelta(seconds=clip)

    def _on_file_queue_ahead(self, key: str, event: FileEvent) -> None:
        """
        T - (BUFFER + margin): put the next file track on the queue behind
        the playing file track, so cross has its partner when the playing
        track enters its last BUFFER seconds.  Only when a file track is
        on air and still has audio left: after a webstream / line-in /
        silence the track starts the normal way at its row start (a
        queued request would start playing at once on an idle queue).
        """
        prev = self._current_event
        if not isinstance(prev, FileEvent) or self._playing_key is None:
            return
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            return
        if self._engine.get_state() != PlayoutState.PLAYING:
            return
        if self._queued_ahead is not None:
            queued_evt = self._queued_ahead[1]
            if self._same_scheduled_item(queued_evt, event) and (
                (queued_evt.cue_in, queued_evt.cue_out, queued_evt.uri)
                == (event.cue_in, event.cue_out, event.uri)
            ):
                self._queued_ahead = (key, event)  # key shifted across a refresh
                return
            # RASTATIME 2026-10-03 - rows shorter than the lead window
            # (BUFFER + margin): the queued row is still armed and starts
            # before this one, so it is the real successor, not stale.  It
            # stays; this row starts the normal way behind it (2026-10-02
            # 23:36: two StationIDs of 3.2 s and 4.9 s were swapped, one of
            # them aired twice and the chain ran 2.9 s late to the show end).
            if queued_evt.start <= event.start and any(
                self._same_scheduled_item(armed, queued_evt)
                for armed in list(self._armed_events.values())
            ):
                logger.info(
                    "Queue-ahead: %s stays queued ahead of %s (rows shorter than "
                    "the lead window) - %s is queued as soon as it starts.",
                    self._queued_ahead[0],
                    key,
                    key,
                )
                self._deferred_queue_ahead = (key, event)
                return
            # a different row, or the same row re-cued by a show-builder
            # edit (2026-09-28): the queued request carries the old cues
            logger.info(
                "Queue-ahead: %s replaces the stale queued track %s.",
                key,
                self._queued_ahead[0],
            )
            self._engine.flush_queued()
            self._queued_ahead = None
        remaining = (self._natural_end(prev) - datetime.utcnow()).total_seconds()
        if remaining < 0.5:
            return  # the predecessor is over: a gap follows, normal start
        local = self._ensure_file_cached(event)
        if local is None:
            return
        mode = self._cross_mode(prev, event, skip=False)
        ok = self._engine.enqueue(
            str(local),
            cue_in=event.cue_in or 0.0,
            cue_out=event.cue_out,
            gain_db=event.replay_gain,
            metadata=self._track_metadata(event),
            transition=mode,
        )
        if ok:
            self._queued_ahead = (key, event)
            self._queued_ahead_prev = prev
            logger.info(
                "Queue-ahead %s | %r follows %r in %.1f s (%s)",
                key,
                event.track_title or event.id,
                prev.track_title or prev.id,
                remaining,
                mode,
            )

    def _cross_mode(self, prev: object, nxt: FileEvent, *, skip: bool) -> str:
        """
        Shape of the queue transition prev -> nxt as ``<shape>/<nofade>``
        (see liquidsoap_config._render_crossfade_block; the engine sets
        ``rt_cross`` and ``rt_nofade`` from it).  ``skip`` = the
        predecessor is cut at nxt's start (overbook) instead of ending by
        itself.  ``nofade`` names the side(s) flagged "No Fade during
        Crossover": old | new | both | - .
        """
        old_nf = isinstance(prev, FileEvent) and prev.no_fade_crossfade
        new_nf = nxt.no_fade_crossfade
        if not isinstance(prev, FileEvent):
            shape = "instant" if skip else "track"
        elif (
            prev.instance_id is not None
            and nxt.instance_id is not None
            and prev.instance_id != nxt.instance_id
        ):
            shape = "show_skip" if skip else "show"
            # 2026-09-29: a track that takes no crossfade at all (type value
            # 0 or "Exclude from Crossover") is not faded at a show boundary
            old_nf = old_nf or self._track_crossfade(prev) < 0.05
        else:
            shape = "track_skip" if skip else "track"
        nofade = "both" if (old_nf and new_nf) else "old" if old_nf else "new" if new_nf else "-"
        overlap = self._pair_crossfade(prev, nxt)
        if shape.startswith("track") and abs(overlap - self._track_crossfade_seconds) > 0.005:
            # the overlap of THIS transition differs from the house value
            return f"{shape}/{nofade}/{overlap:.2f}"
        return f"{shape}/{nofade}"

    def _track_crossfade(self, event: object) -> float:
        """
        RASTATIME 2026-09-29 - seconds ``event`` overlaps a neighbour: 0
        for "Exclude from Crossover", else its track type's value, else the
        house track crossfade.  Never more than the cross buffer.
        """
        if not isinstance(event, FileEvent):
            return self._track_crossfade_seconds
        if event.exclude_crossfade:
            return 0.0
        value = event.crossfade_seconds
        if value is None:
            return self._track_crossfade_seconds
        return max(0.0, min(float(value), self._cross_buffer_seconds))

    def _pair_crossfade(self, prev: object, nxt: FileEvent) -> float:
        """The SMALLER of the two tracks' values: a type with 0 always butts."""
        if not isinstance(prev, FileEvent):
            return self._track_crossfade(nxt)
        return min(self._track_crossfade(prev), self._track_crossfade(nxt))

    @staticmethod
    def _track_metadata(event: FileEvent) -> dict[str, str]:
        # RASTATIME 2026-10-14 - a track whose metadata stays off the stream
        # sends no artist / title; icy_hide makes the label builder show
        # "Station name - Show name" in every format (jingles, IDs, promos).
        # 2026-10-15 23:44 rehearsal: a packet with EMPTY title/artist keys
        # did show "Station - Show" for the jingle, but afterwards NO packet
        # reached the Icecast output any more (three tracks, stream title
        # stuck) - reverted to the key-less packet (jingle keeps the previous
        # title, every later track labels normally) until the replica shows
        # why; see CHANGELOG 2026-10-15.
        if getattr(event, "icy_hidden", False):
            return {
                "icy_hide": "true",
                "show_name": event.show_name or "",
            }
        return {
            "title": event.track_title or "",
            "artist": event.artist_name or "",
            "show_name": event.show_name or "",
        }

    def _arm_prepare(
        self, key: str, event: object, start_delay: float, handler: Callable[[str, object], None]
    ) -> None:
        """Arm the prepare timer at start - PREPARE_LEAD_SECONDS (an item
        starting sooner than that goes the normal way)."""
        if start_delay < MIN_PREPARE_SECONDS:
            return
        # RASTATIME 2026-09-05 - a refresh cancels and re-arms every timer.
        # When it lands INSIDE the lead window (seen live 20:16:49 for a
        # 20:17:00 slot) the old "lead <= 0.5 -> skip" dropped the pre-warm
        # and the slot started with the normal 2 s gap.  Now the pre-warm
        # fires immediately; the handlers are idempotent for an item that
        # is already pre-warmed.
        lead_seconds = (
            WEBSTREAM_PREPARE_LEAD_SECONDS
            if isinstance(event, WebStreamEvent)
            else PREPARE_LEAD_SECONDS
        )
        lead = max(0.0, start_delay - lead_seconds)
        t = threading.Timer(lead, handler, args=(key, event))
        t.daemon = True
        t.start()
        self._prepare_timers[key] = t

    def _on_linein_prepare(self, key: str, event: LineinEvent) -> None:
        """T - 10 s: bring the line-in up with the bus gate CLOSED."""
        if self._linein_capture is None:
            return
        if isinstance(self._current_event, LineinEvent):
            logger.info(
                "Prepare %s skipped: a line-in is on air (single capture); "
                "it starts the normal way at its slot.",
                key,
            )
            return
        if self._prepared is not None:
            if self._same_scheduled_item(self._prepared[1], event):
                logger.debug("Prepare %s: already pre-warmed.", key)
                return
            logger.info("Prepare %s skipped: %s is already pre-warmed.", key, self._prepared[0])
            return
        dev_name = getattr(event, "device_name", "") or ""
        if not dev_name:
            return  # legacy dshow path cannot be pre-warmed
        resolved = self._resolve_linein_device(event)
        if not resolved:
            logger.warning("Prepare %s: device unavailable - no pre-warm.", key)
            return
        mapping = list(getattr(event, "channel_mapping", None) or [0, 1])
        logger.info("Prepare %s: pre-warming line-in %r (gate closed).", key, event.name)
        self._linein_generation += 1  # a pending drained stop must not kill us
        self._engine.linein_gate(False)
        self._engine.linein_start_http()
        try:
            self._linein_capture.start(
                resolved,
                channel_mapping=tuple(mapping),
                device_name=dev_name,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Prepare %s: capture start failed: %s", key, exc)
            self._engine.linein_stop()
            self._engine.linein_gate(True)
            return
        if not self._linein_capture.is_running:
            logger.error("Prepare %s: capture did not come up - not pre-warmed.", key)
            self._engine.linein_stop()
            self._engine.linein_gate(True)
            return
        self._prepared = (key, event)

    def _on_webstream_prepare(self, key: str, event: WebStreamEvent) -> None:
        """T - 10 s: connect + buffer the webstream with the bus gate CLOSED."""
        if isinstance(self._current_event, WebStreamEvent):
            logger.info(
                "Prepare %s skipped: a web stream is on air (single source).",
                key,
            )
            return
        if self._prepared is not None:
            if self._same_scheduled_item(self._prepared[1], event):
                logger.debug("Prepare %s: already pre-buffered.", key)
                return
            logger.info("Prepare %s skipped: %s is already pre-warmed.", key, self._prepared[0])
            return
        logger.info("Prepare %s: pre-buffering web stream %s (gate closed).", key, event.uri)
        self._webstream_generation += 1
        self._engine.webstream_gate(False)
        self._engine.webstream_start(event.uri, gain_db=event.input_gain_db)
        self._prepared = (key, event)

    def _take_prepared(self, event: object) -> bool:
        """True (and clears the mark) when ``event`` is the pre-warmed item."""
        if self._prepared is None or not self._same_scheduled_item(self._prepared[1], event):
            return False
        self._prepared = None
        return True

    def _undo_prepare(self, reason: str) -> None:
        if self._prepared is None:
            return
        key, event = self._prepared
        self._prepared = None
        logger.info("Undoing pre-warm of %s: %s.", key, reason)
        if isinstance(event, LineinEvent):
            self._linein_generation += 1
            self._engine.linein_stop()
            if self._linein_capture is not None:
                self._linein_capture.stop()
            self._engine.linein_gate(True)
        elif isinstance(event, WebStreamEvent):
            self._webstream_generation += 1
            self._engine.webstream_stop()
            self._engine.webstream_gate(True)

    def _apply_linein_gain(self, event: object) -> None:
        """
        RASTATIME 2026-10-02 - push a line-in's static input gain
        (``rastatime_linein.input_gain_db``) to the ``linein.gain``
        amplify factor of the .liq.  Every path that puts a line-in on
        air calls this, so the previous line-in's gain never carries
        over (``None`` / 0 = unity).  No-op for other events and for an
        engine without the setter.
        """
        setter = getattr(self._engine, "linein_set_gain", None)
        if setter is None or not isinstance(event, LineinEvent):
            return
        setter(getattr(event, "input_gain_db", None))

    def reset_gates(self) -> None:
        """Open both bus gates (startup: a previous Pypo may have died
        mid-prepare with a gate closed)."""
        self._engine.linein_gate(True)
        self._engine.webstream_gate(True)

    def _release_linein(self, why: str) -> None:
        """Take the line-in off air NOW via the gate (the bus fades it out
        under the successor while its buffered tail plays) and stop the
        capture + source once the fade is over."""
        gen = self._linein_generation
        self._engine.linein_gate(False)
        logger.info("Line-in released (%s): gate closed, stop in %.1f s.", why, self._drain_seconds)
        t = threading.Timer(self._drain_seconds, self._drained_linein_stop, args=(gen,))
        t.daemon = True
        t.start()

    def _drained_linein_stop(self, gen: int) -> None:
        if self._linein_generation != gen:
            logger.info(
                "Drained line-in stop skipped: a newer line-in took over (gen %d->%d).",
                gen,
                self._linein_generation,
            )
            return
        if self._linein_capture is not None:
            self._linein_capture.stop()
        self._engine.linein_stop()

    def _release_webstream(self, why: str) -> None:
        gen = self._webstream_generation
        self._engine.webstream_gate(False)
        logger.info(
            "Web stream released (%s): gate closed, stop in %.1f s.", why, self._drain_seconds
        )
        t = threading.Timer(self._drain_seconds, self._drained_webstream_stop, args=(gen,))
        t.daemon = True
        t.start()

    def _drained_webstream_stop(self, gen: int) -> None:
        if self._webstream_generation != gen:
            logger.info("Drained web stream stop skipped: a newer web stream took over.")
            return
        self._engine.webstream_stop()

    def _queue_deferred_ahead(self) -> None:
        """
        RASTATIME 2026-10-03 - the row held back by _on_file_queue_ahead
        (its lead window opened while a shorter row was queued) goes on the
        queue now that the shorter row plays: a 2.7 s jingle left its
        successor's own PLAY 0.3 s, and 0.6 s of dead air followed
        (12:40:23).  Nothing to do when the row is gone or is the current one.
        """
        deferred = self._deferred_queue_ahead
        if deferred is None:
            return
        self._deferred_queue_ahead = None
        key, event = deferred
        cur = self._current_event
        if not isinstance(cur, FileEvent) or self._same_scheduled_item(cur, event):
            return
        if event.start < cur.start or not any(
            self._same_scheduled_item(armed, event) for armed in list(self._armed_events.values())
        ):
            return
        logger.info(
            "Queue-ahead: %s was held back behind %r - queuing it now.",
            key,
            cur.track_title or cur.id,
        )
        self._on_file_queue_ahead(key, event)

    def _on_file_start(self, key: str, event: FileEvent, seek: float = 0.0) -> None:
        """Start ``event`` now (see _on_file_start_impl); marks the row as starting."""
        # RASTATIME 2026-10-10 - how late the start timer fired against the
        # row second (timers are armed on whole seconds; more than ~0.5 s
        # means the refresh armed them late or the thread was held up).
        if seek <= 0 and event.start is not None:
            late = (datetime.utcnow() - event.start).total_seconds()
            if late > 0.5:
                logger.info(
                    "PLAY  %s: the start timer fired %.2f s after the row second.",
                    key,
                    late,
                )
        self._starting[key] = event
        try:
            self._on_file_start_impl(key, event, seek)
        except Exception:  # pylint: disable=broad-exception-caught
            # RASTATIME 2026-11-02 - this runs on a Timer thread: an
            # unhandled exception used to vanish into stderr and the row
            # simply never played (rehearsal 2026-11-02: silence after a
            # catch-up with no further line in playout-stdout.log).  Log it
            # where the operator looks and let the next row proceed.
            logger.exception(
                "PLAY  %s failed with an unexpected error - the row stays silent, "
                "the next row starts on its own timer.",
                key,
            )
        finally:
            self._starting.pop(key, None)
            self._queue_deferred_ahead()

    def _on_file_start_impl(self, key: str, event: FileEvent, seek: float = 0.0) -> None:
        """
        Start ``event`` now.  ``seek`` (seconds, catch-up only) is how far
        into the track the schedule already is: a service restart or a
        refresh that discovers an in-progress row enters the audio there
        instead of at its top (2026-09-28).
        """
        seek = max(0.0, float(seek or 0.0))
        logger.info(
            "PLAY  %s  |  %r  |  show: %s%s",
            key,
            event.track_title or event.id,
            event.show_name,
            f"  (catch-up at +{seek:.1f} s)" if seek > 0 else "",
        )
        local = self._ensure_file_cached(event)
        if local is None:
            logger.error("Cannot play %s — file could not be downloaded", key)
            return

        # RASTATIME 2026-09-09 - a planned Liquidsoap restart that found
        # the station on air (24/7 programme) happens here, between two
        # file tracks: the previous track has ended, the fresh instance
        # is up within a few seconds, then this track starts.  Listeners
        # hear a short gap instead of a mid-track hole; Icecast keeps
        # them on the fallback mounts meanwhile (see icecast.xml).
        if self._boundary_restart_pending and self._boundary_allows_restart(
            self._current_event,
            event,
        ):
            reason = self._boundary_restart_pending
            self._boundary_restart_pending = None
            if self._perform_planned_restart(
                f"at the track boundary before {key}: {reason}",
                settle_async=True,
            ):
                # 2026-09-28 - whatever was queued ahead lived in the old
                # instance; this track needs a fresh push (see
                # _after_liquidsoap_restart, which clears the same state).
                self._queued_ahead = None
                self._queued_ahead_prev = None
                # RASTATIME 2026-10-02 - the restart took its time; enter
                # the track that far in instead of shifting the whole file
                # chain (the 17:20 test show ran +3.9 s behind its rows to
                # the end).
                seek = self._catch_up_after_boundary_restart(key, event, seek)

        # Track which event is "current" regardless of whether a DJ is
        # overriding right now — this is what we resume to once the DJ
        # disconnects.  These four lines must run BEFORE the DJ-active
        # short-circuit below, otherwise switch_audio_source(SCHEDULED)
        # at disconnect time would not know what to fall back to.
        prev_event = self._current_event  # for _close_predecessor_source
        prev_started_at = self._current_started_at
        prev_clip = self._current_clip_seconds
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = str(local)
        self._current_started_at = datetime.utcnow()
        self._current_clip_seconds = max(
            0.0,
            float(event.cue_out or 0.0) - float(event.cue_in or 0.0) - seek,
        )
        # RASTATIME 2026-06-05 — cue mark for the 24/7 recording sidecar.
        self._cue_item_start(
            "track",
            show=event.show_name,
            item=event.row_id,
            title=event.track_title,
            artist=event.artist_name,
        )
        self._tunein_now_playing(
            "track",
            title=event.track_title,
            artist=event.artist_name,
            show=event.show_name,
        )
        # RASTATIME 2026-05-16 — cache the effective gain for the
        # resume path.  For file events the value is the precomputed
        # ReplayGain sum of ``cc_files.replay_gain`` and
        # ``cc_pref.replay_gain_modifier`` (see player/schedule.py).
        # ``None`` ⇒ replay-gain globally disabled; engines/streamers
        # skip the volume filter.
        self._current_gain_db = event.replay_gain
        self._set_bus_show(event.show_name)  # ICY show for DJ takeovers (2026-09-13)

        # If a DJ source is currently dominant, do not touch the audio
        # engine — the DJ stream stays on air.  We've already recorded
        # the current event so the scheduled track can be picked up
        # when the DJ disconnects.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            logger.info(
                "Track %s queued — %s source active, scheduled audio held back",
                key,
                self._switcher.current_state.value,
            )
            self._notify_media_started(event.row_id)
            return

        # RASTATIME 2026-09-28 - a catch-up past the track's audio: nothing
        # left to play, the next row follows on its own timer.
        clip = float(event.cue_out or 0.0) - float(event.cue_in or 0.0)
        if seek > 0 and clip > 0 and seek >= clip - 0.5:
            logger.info(
                "PLAY  %s: the catch-up offset +%.1f s is past the track's %.1f s "
                "of audio - nothing to play.",
                key,
                seek,
                clip,
            )
            self._notify_media_started(event.row_id)
            return

        # RASTATIME 2026-09-27 - crossfade.  Remaining audio of a file
        # predecessor decides between "cross does the hand-over at the
        # natural end" (rows overlap by the track crossfade, or the
        # predecessor is over) and "cut it now" (overbook: the predecessor
        # would run on into this slot).
        now = datetime.utcnow()
        queued = self._queued_ahead
        if queued is not None and seek > 1.0 and self._same_scheduled_item(queued[1], event):
            # The queued copy would start at the top; a catch-up this far
            # in needs a fresh request with the offset.
            logger.info(
                "PLAY  %s: catch-up at +%.1f s - dropping the queued copy, "
                "which starts at the top.",
                key,
                seek,
            )
            self._engine.flush_queued()
            self._queued_ahead = None
            self._queued_ahead_prev = None
            queued = None
        if (
            prev_event is None
            and queued is not None
            and self._same_scheduled_item(queued[1], event)
        ):
            # The predecessor's STOP ran a moment ago (rows clipped at the
            # show end fire STOP and this PLAY at the same instant) and
            # cleared _current_event; the track it was queued behind is
            # the one still on the queue.
            prev_event = self._queued_ahead_prev
        prev_remaining = (
            (self._natural_end(prev_event) - now).total_seconds()
            if isinstance(prev_event, FileEvent)
            else 0.0
        )
        # RASTATIME 2026-09-27 - prefer the engine's own measurement: a
        # predecessor that started late (second rehearsal: 45 s, after a
        # clipped cue_out was not applied) has more audio left than the
        # row says.  The computed value stays the fallback.
        if isinstance(prev_event, FileEvent):
            measured = self._engine.playing_remaining_seconds()
            if isinstance(measured, (int, float)) and not isinstance(measured, bool):
                # RASTATIME 2026-09-28 - the queue's "remaining" belongs to
                # the successor once cross has pulled it, and the RID it
                # reports can lag a moment behind (20:05:35: "214.9 s left"
                # for a track with 3 s of audio; the skip then hit the
                # successor and left dead air).  More audio than the
                # predecessor can possibly have = the hand-over happened.
                bound = self._plausible_remaining(now, prev_started_at, prev_clip)
                if bound is not None and measured > bound:
                    logger.info(
                        "PLAY  %s: the engine's %.1f s left cannot belong to %r "
                        "(at most %.1f s of its audio is left) - the queue is on "
                        "the successor, no skip.",
                        key,
                        measured,
                        getattr(prev_event, "track_title", None) or "-",
                        bound,
                    )
                    measured = 0.0
                if abs(measured - prev_remaining) > 1.0:
                    logger.info(
                        "PLAY  %s: predecessor has %.1f s of audio left (engine), "
                        "rows said %.1f s.",
                        key,
                        measured,
                        prev_remaining,
                    )
                prev_remaining = float(measured)
        if queued is not None and self._same_scheduled_item(queued[1], event):
            # Queued ahead: cross already has this track as the partner.
            self._queued_ahead = None
            self._queued_ahead_prev = None
            skip = prev_remaining > self._cross_buffer_seconds + SKIP_TOLERANCE_SECONDS
            mode = self._cross_mode(prev_event, event, skip=skip)
            self._engine.adopt_queued(
                str(local),
                skip_current=skip,
                transition=mode if skip else None,
            )
            if skip:
                # 2026-09-29: the cut starts a new chain at this instant
                self._note_file_chain_lag(event, 0.0)
            else:
                self._carry_file_chain_lag(prev_event, event, mode)
            logger.info(
                "PLAY  %s takes over from %r: %s (predecessor has %.1f s left)",
                key,
                getattr(prev_event, "track_title", None) or "-",
                mode,
                max(0.0, prev_remaining),
            )
            self._notify_media_started(event.row_id)
            return
        if queued is not None:
            logger.info(
                "PLAY  %s: dropping the stale queued track %s.",
                key,
                queued[0],
            )
            self._engine.flush_queued()
            self._queued_ahead = None
            self._queued_ahead_prev = None

        # RASTATIME 2026-10-01 - after a live item (or silence) the push
        # waits for the row's exact start: behind a file predecessor a
        # push is free (the queue holds it), here it would start the
        # track up to a second early and shift the rest of the show.
        if seek <= 0 and not isinstance(prev_event, FileEvent):
            if not self._wait_for_exact_time(key, event.start_exact, "PLAY"):
                return

        # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1.  Let the
        # engine flush the previous track's last frames before the hard
        # stop (the Liquidsoap engine returns at once: its queue is
        # gapless by itself).
        self._engine.wait_until_stopped(timeout=0.5)

        # RASTATIME 2026-09-04 - close a line-in / webstream predecessor
        # ourselves (see _close_predecessor_source).
        self._close_predecessor_source(prev_event, key)

        # HARD start (QUEUE_BEHAVIOR §4.1): stop whatever is playing first.
        self._engine.stop()

        # RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C6 Teil 2.
        # Forward track metadata to the engine so the Liquidsoap
        # backend can attach it via annotate: + propagate to the
        # output.icecast blocks for live ICY metadata in listener
        # clients.  2026-09-27: the engine pushes first and skips the
        # predecessor afterwards - only when it would run on past this
        # slot (overbook).  Inside its last BUFFER seconds the predecessor
        # is already in the cross operator's tail (the queue has consumed
        # it): a skip there is a no-op at best and could hit the pushed
        # track; the tail plays out and this track follows at once.
        skip = prev_remaining > self._cross_buffer_seconds + SKIP_TOLERANCE_SECONDS
        self._engine.play(
            str(local),
            cue_in=(event.cue_in or 0.0) + seek,
            cue_out=event.cue_out,
            gain_db=event.replay_gain,
            metadata=self._track_metadata(event),
            transition=self._cross_mode(prev_event, event, skip=skip),
            skip_current=skip,
        )
        # 2026-09-29: this push starts a new chain unless the track waits
        # behind a file predecessor that is still playing out.
        if skip or not isinstance(prev_event, FileEvent) or prev_remaining <= 0.0:
            self._note_file_chain_lag(event, seek)

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
            key,
            event.uri,
            gain_for_log,
            event.show_name,
        )

        # Track which event is "current" regardless of whether a DJ
        # source is overriding right now.  These four lines must run
        # BEFORE the DJ-active short-circuit below — otherwise
        # ``_resume_scheduled_locked`` at DJ-disconnect time would not
        # know what to fall back to.  Same pattern as _on_file_start.
        prev_event = self._current_event  # for _close_predecessor_source
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = event.uri
        # RASTATIME 2026-06-05 — cue mark for the 24/7 recording sidecar.
        self._cue_item_start(
            "webstream",
            show=event.show_name,
            item=event.row_id,
            uri=event.uri,
        )
        self._tunein_now_playing("webstream", title=None, artist=None, show=event.show_name)
        # RASTATIME 2026-05-16 — cache the webstream's input-gain so the
        # resume path (DJ disconnect, hot-reload) reapplies it after the
        # stop/restart, instead of falling back to "no gain".
        self._current_gain_db = event.input_gain_db
        self._set_bus_show(event.show_name)  # ICY show for the webstream packets (2026-09-13)

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
                "Web stream %s queued — %s source active, scheduled audio held back",
                key,
                self._switcher.current_state.value,
            )
            return

        # RASTATIME 2026-09-29 - after a file track the gate opens when
        # its audio is over, not on the whole second this timer fired at.
        if not self._hold_live_start(key, prev_event, event):
            return

        # RASTATIME 2026-05-29 — Phase E: Liquidsoap webstream handling.
        # The .liq script has a dedicated input.http source ("webstream")
        # that we drive via telnet wrappers — set URL, set gain, start.
        # The source goes ``source.is_ready=true`` after max_buffer (10 s
        # default) of audio has buffered, at which point the switch
        # operator in the .liq flips the bus from scheduled (silence_
        # fallback) to webstream automatically.  We also clear the
        # scheduled queue so the previous track doesn't linger in the
        # background during the buffer-up phase.
        # Phase E (2026-05-29) — Liquidsoap engine path.
        # We do NOT call wait_until_stopped here: Liquidsoap's queue
        # handles its own gapless transitions and we want the
        # scheduled-track-to-webstream handover to happen as soon as
        # input.http has buffered enough.
        # RASTATIME 2026-09-04 - a line-in predecessor must be closed
        # by us: it outranks nothing while we play, but the switch
        # would drop straight back onto it when we end.
        # RASTATIME 2026-09-05 - same stream, next show: the source is
        # already playing this URL, so this is a bookkeeping hand-over
        # (mirror of the line-in same-device transition).  Releasing and
        # restarting it (20:12 live) cost a ~1 s fade-out/fade-in dip.
        # A different gain would need a restart - rare; fall through.
        if (
            isinstance(prev_event, WebStreamEvent)
            and prev_event.uri == event.uri
            and (prev_event.input_gain_db or 0.0) == (event.input_gain_db or 0.0)
        ):
            logger.info(
                "Web stream %s: same stream as %s - keeping the source, no bounce.",
                key,
                prev_event.uri,
            )
            self._take_prepared(event)
            self._webstream_generation += 1  # a pending drain must not stop us
            self._engine.stop()  # clear the scheduled queue as usual
            self._engine.webstream_gate(True)  # in case a race closed it
            return
        if isinstance(prev_event, WebStreamEvent):
            # RASTATIME 2026-09-05 - a DIFFERENT stream on the single
            # webstream source: the drained release cannot work here
            # (set_url + start on a running input.http does not
            # reconnect, and the drained stop is then skipped as "a
            # newer stream took over" - live 11:44:30 the old stream
            # simply kept playing).  Hard stop, then start: the old
            # tail is cut and the new stream needs its buffer-up.
            logger.info(
                "Web stream %s replaces %s on the single stream source - "
                "stop + start (no drain possible).",
                key,
                prev_event.uri,
            )
            self._webstream_generation += 1
            self._engine.webstream_stop()
        else:
            self._close_predecessor_source(prev_event, key)
        self._engine.stop()  # deferred-stop, clears request.queue
        if self._take_prepared(event):
            # RASTATIME 2026-09-04 - pre-buffered at T-10 s: only the
            # gate has to open.  No reconnect, no buffer-up gap.
            logger.info("Web stream %s was pre-buffered - opening the gate.", key)
            self._webstream_generation += 1
            self._engine.webstream_gate(True)
            return
        self._webstream_generation += 1
        self._engine.webstream_start(
            event.uri,
            gain_db=event.input_gain_db,
        )
        self._engine.webstream_gate(True)

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
            import audio.soundcard._registry as _reg  # noqa: PLC0415
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
                event.name,
                exc,
                event.device_id,
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
                event.name,
                event.device_id,
                dev.name,
                dev.stable_id,
            )
        return dev.stable_id

    def _on_linein_start(self, key: str, event: LineinEvent) -> None:
        """
        Bring a scheduled Line-In on air (Phase B, Liquidsoap since
        Phase F).

        Pipeline:

          FfmpegLineinCapture (MME feeder) → /linein-capture mount
                → Liquidsoap input.http (linein_http) → bus
                → Icecast outputs + recording

        Rows without a stored device name use the in-process dshow
        source (``engine.linein_start``) instead of the feeder.

        Same source-switcher-aware "queue but don't override DJ"
        pattern as :meth:`_on_file_start` / :meth:`_on_webstream_start`:
        while a DJ is active only the bookkeeping happens, and the
        resume path re-arms the line-in on disconnect.

        Same-device transition shortcut (Phase B.4 #3 — 2026-05-13)
        ----------------------------------------------------------
        If the PREVIOUS event was already a LineinEvent against the
        same physical device AND the capture is still running, this
        is a "back-to-back same-mic show change" — keep the capture
        and the Liquidsoap source alive.  Zero audio bounce, no device
        re-acquisition race.  The earlier event's ``_on_stop`` is also
        same-device-aware and skips its own teardown in that
        situation, so this shortcut works
        regardless of which timer fired first.
        """
        logger.info(
            "PLAY (line-in)  %s  |  name=%r device=%s  |  show: %s",
            key,
            event.name,
            event.device_id,
            event.show_name,
        )

        if self._linein_capture is None:
            logger.error(
                "Line-In %s cannot start: FfmpegLineinCapture failed to "
                "initialise at startup (likely missing ffmpeg).  Slot "
                "stays silent.",
                key,
            )
            return

        # Capture the OLD bookkeeping BEFORE we overwrite it — we need
        # it for the same-device-transition check below.
        prev_event = self._current_event
        same_device_transition = (
            isinstance(prev_event, LineinEvent)
            and prev_event.device_id == event.device_id  # type: ignore[attr-defined]
            # RASTATIME 2026-08-31 — a different channel mapping on the
            # SAME interface is a different studio: must bounce the
            # capture, not ride the running one.
            and list(getattr(prev_event, "channel_mapping", None) or [0, 1])
            == list(getattr(event, "channel_mapping", None) or [0, 1])
            and self._linein_capture.is_running
        )

        # Update playing-event bookkeeping unconditionally — must
        # happen BEFORE the DJ-active short-circuit, same pattern as
        # the file / webstream handlers.
        self._playing_key = key
        self._current_event = event
        self._current_audio_path = self._linein_capture.listen_url
        # RASTATIME 2026-06-05 — cue mark for the 24/7 recording sidecar.
        self._cue_item_start(
            "linein",
            show=event.show_name,
            item=event.row_id,
            name=event.name,
        )
        self._tunein_now_playing("linein", title=None, artist=None, show=event.show_name)
        self._set_bus_show(event.show_name)  # ICY show for the line-in packets (2026-09-13)

        # Drive the dashboard "On Air" light for the new row.
        row_id = getattr(event, "row_id", None)
        if row_id is not None:
            self._notify_media_started(row_id)

        # RASTATIME 2026-10-02 - this line-in's input gain, before any of
        # the early returns below: a same-device transition keeps the
        # capture but may carry a different gain, and a pre-warmed or
        # held line-in opens its gate further down.
        self._apply_linein_gain(event)

        if same_device_transition:
            logger.info(
                "Line-In %s: same-device transition (device=%s) — keeping "
                "the running capture and the Liquidsoap source alive; "
                "no audio-pipeline bounce.",
                key,
                event.device_id,
            )
            return

        # RASTATIME 2026-09-04 - pre-warmed at T-10 s (Paket 2): capture
        # and http source are up with the gate closed; open it.  The
        # webstream predecessor (if any) is released by the same call
        # that would run below, the queue is cleared, and we are done.
        # 2026-09-29: after a file track the gate opens when its audio is
        # over (the wait only happens for the pre-warmed item).
        if self._linein_capture.is_running and not self._hold_live_start(key, prev_event, event):
            return
        if (
            self._linein_capture is not None
            and self._linein_capture.is_running
            and self._take_prepared(event)
        ):
            logger.info("Line-In %s was pre-warmed - opening the gate.", key)
            if isinstance(prev_event, WebStreamEvent):
                self._close_predecessor_source(prev_event, key)
            self._engine.stop()
            self._linein_generation += 1
            self._engine.linein_gate(True)
            return

        # Resolve the device GUID (with name-fallback for USB endpoint
        # GUID shifts after reboot — see _resolve_linein_device).
        resolved_device_id = self._resolve_linein_device(event)
        if not resolved_device_id:
            logger.error(
                "Line-In %s: device %r unavailable (and no name-fallback "
                "matched name=%r) — leaving line-in stopped.",
                key,
                event.device_id,
                getattr(event, "device_name", "") or "",
            )
            return

        # RASTATIME 2026-05-30 — Phase-F-2: Liquidsoap line-in handling.
        # The .liq switch ranks DJ sources above linein, so if a DJ is
        # active we just bookkeep + return (same as webstream); the
        # resume path re-arms on disconnect.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            logger.info(
                "Line-In %s queued — %s source active, scheduled line-in held back.",
                key,
                self._switcher.current_state.value,
            )
            return
        # RASTATIME 2026-09-03 - EVERY scheduled line-in now runs
        # through the sounddevice/MME feeder, plain stereo included
        # (operator decision "Option B", 2026-09-03).
        #
        # Until today plain stereo (1/2) took the direct-dshow source
        # instead.  That path addresses the device by GUID
        # (wave_{<endpoint guid>}), but DirectShow enumerates its own
        # device GUIDs -- which are NOT the WASAPI endpoint GUIDs we
        # store.  Live proof (15:20 test show, "Tascam 1-2"): dshow
        # answered "Could not find audio only device" and the slot
        # stayed silent, while the very same device opened fine
        # through MME.  Rather than teach the dshow path a second
        # addressing scheme, we unify on the feeder: it resolves by
        # friendly name, is proven on every channel pair, and is
        # already the path the operator listens to.
        #
        # The dshow source stays in the .liq as the fallback for
        # legacy rows that never stored a device name -- the feeder
        # cannot resolve a PortAudio device from a GUID alone.
        mapping = list(getattr(event, "channel_mapping", None) or [0, 1])
        dev_name = getattr(event, "device_name", "") or ""
        use_feeder = bool(dev_name)
        if not use_feeder:
            logger.error(
                "Line-In %s: no stored device name (legacy save), so the "
                "MME feeder cannot resolve the device; falling back to "
                "the direct dshow source on channels 1/2 (requested "
                "mapping %s).  Re-save the line-in in Settings -> Local "
                "Machine to store the device name.",
                key,
                mapping,
            )

        # RASTATIME 2026-09-04 - a webstream predecessor outranks us in
        # the bus switch; close it ourselves rather than trusting the
        # racing _on_stop (see _close_predecessor_source).
        if isinstance(prev_event, WebStreamEvent):
            self._close_predecessor_source(prev_event, key)
        self._engine.stop()  # clear the scheduled queue (deferred-stop)
        # Race fix #3 — mark a new line-in generation BEFORE the telnet
        # round-trip, so a racing _on_stop (for the previous show) that
        # snapshotted the old value sees the bump and skips its
        # teardown instead of stopping the source we are bringing up.
        self._linein_generation += 1

        if use_feeder and self._linein_capture is not None:
            # RASTATIME 2026-09-03 - Lever 2 (line-in start-gap fix).
            # Arm the input.http companion BEFORE the blocking feeder
            # start.  FfmpegLineinCapture.start() spends ~0.75 s on a
            # health-check sleep before returning; starting input.http
            # first lets its connect + max_buffer fill overlap that
            # window instead of running strictly after it (~0.75 s of
            # dead air shaved).  A small poll_delay in the .liq lets it
            # grab the mount within half a second of the feeder
            # publishing it.  If the feeder never comes up we stop the
            # source again below (the b4cd37b guard, preserved).
            self._engine.linein_start_http()
            self._engine.linein_gate(True)  # may be closed from an undone pre-warm
            try:
                self._linein_capture.start(
                    resolved_device_id,
                    channel_mapping=tuple(mapping),
                    device_name=dev_name,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Line-In %s: feeder capture start failed for device %s (channels %s): %s",
                    key,
                    resolved_device_id,
                    mapping,
                    exc,
                )
                self._engine.linein_stop()
                return
            # start() gives up QUIETLY after its retry ladder (logs,
            # no raise), so verify: without a capture there is no
            # mount, and the http source armed above would poll a 404
            # for the rest of the slot unless we stop it now.
            if not self._linein_capture.is_running:
                logger.error(
                    "Line-In %s: capture did not come up - stopping "
                    "the pre-armed linein_http source so it does not "
                    "poll a dead mount.",
                    key,
                )
                self._engine.linein_stop()
                return
            return

        # Build dshow alternative-name spec from the device GUID.
        # _stable_id_to_dshow_audio lives in ffmpeg_linein_capture (the
        # feeder module); it's a pure helper, safe to reuse without
        # instantiating the capture class.
        from .engine.ffmpeg_linein_capture import _stable_id_to_dshow_audio

        dshow_spec = _stable_id_to_dshow_audio(resolved_device_id)
        self._engine.linein_start(dshow_spec)

    def _on_linein_capture_restart(self) -> None:
        """
        Callback fired by :class:`FfmpegLineinCapture`'s watchdog after a
        successful auto-restart of the capture subprocess (Phase B.4 #1 —
        device unplugged mid-show).

        The local /linein-capture mount is published again, but the
        Liquidsoap ``input.http`` companion may have given up on the
        dead stream.  Re-arm it (stop + start of ``linein_http``, same
        wiring as the resume path) and make sure the gate is open.
        Runs on the watchdog thread; takes the scheduler lock so a
        parallel ``refresh()`` cannot tear things down underneath us.

        Idempotent and safe-no-op if:

          * No LineinEvent is currently the playing event (e.g. the
            Show ended exactly during the 5-s restart back-off and
            ``_on_stop`` already ran).
          * A non-SCHEDULED source is dominant — DJ or Master takes
            priority; capture is alive but the DJ stays on air.  When
            the DJ disconnects, ``_resume_scheduled_locked`` re-arms
            the (still running) capture.
          * The playing line-in uses the in-process dshow source (no
            stored device name) — the capture is not part of that path.

        RASTATIME 2026-09-10: until the mpv cleanup this callback pushed
        the listen URL through ``engine.play`` (the mpv wiring), which
        with Liquidsoap would have queued the mount as a file request.
        """
        with self._lock:
            if not isinstance(self._current_event, LineinEvent):
                logger.info(
                    "Line-In capture restart callback: no LineinEvent is "
                    "the playing event right now — nothing to re-wire.",
                )
                return

            if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
                logger.info(
                    "Line-In capture restart callback: %s source dominant "
                    "— capture is back, but the DJ stays on air.",
                    self._switcher.current_state.value,
                )
                return

            if not (getattr(self._current_event, "device_name", "") or ""):
                logger.info(
                    "Line-In capture restart callback: the playing line-in "
                    "uses the direct dshow source — nothing to re-wire.",
                )
                return

            logger.info(
                "Line-In capture restart callback: re-arming the Liquidsoap "
                "input.http companion on %s",
                self._linein_capture.listen_url if self._linein_capture else "?",
            )
            self._engine.linein_start_http()
            self._engine.linein_gate(True)

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

        Compared to the deleted FfmpegRecorder lifecycle, the
        Liquidsoap path has:
          * No HTTP-source-tap (recording is on the same internal bus
            as the Icecast outputs)
          * No retry-on-404 (no HTTP source to fail)
          * No mid-show watchdog respawn (no subprocess to crash)
          * No post-roll Timer (no HTTP-buffering lag to compensate)
        """
        folder = self._fetch_recording_folder()
        if not folder:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s name=%r): "
                "no recording folder configured in Settings -> Local Machine",
                key,
                event.show_id,
                event.show_name,
            )
            return

        try:
            output_path = build_output_path(
                Path(folder),
                event.show_starts_at,
                event.show_name,
                extension=self._recording_file_extension(),
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Show-record start ignored (key=%s show_id=%s): could not build output path: %s",
                key,
                event.show_id,
                exc,
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
                "Show-record start ignored (key=%s show_id=%s): could not create directory %s: %s",
                key,
                event.show_id,
                output_path.parent,
                exc,
            )
            return

        # Liquidsoap's telnet wire-form rejects backslashes.  Windows
        # paths come out of pathlib with ``\\`` separators; convert to
        # forward-slashes here (Liquidsoap on Windows handles ``C:/...``
        # fine on the file-system side).
        liq_path = str(output_path).replace("\\", "/")

        logger.info(
            "PLAY (show-record start, Liquidsoap)  %s  |  show_id=%s name=%r  |  output=%s",
            key,
            event.show_id,
            event.show_name,
            output_path,
        )
        try:
            self._engine.recording_start(liq_path)
        except (OSError, ConnectionError, ValueError) as exc:
            logger.error(
                "Show-record start failed (Liquidsoap telnet, key=%s show_id=%s name=%r): %s",
                key,
                event.show_id,
                event.show_name,
                exc,
            )
            return
        self._open_show_recording = (getattr(event, "instance_id", None), output_path)

    def _on_show_record_end(self, key: str, event: ShowRecordEvent) -> None:
        """
        RASTATIME 2026-05-28 — Phase-C5 Teil 2d: Record-per-Show end
        handler.  Calls ``engine.recording_stop()`` synchronously —
        no post-roll Timer needed because Liquidsoap's ``output.file``
        is on the SAME internal bus as the Icecast outputs (the
        deleted FfmpegRecorder's 1 s post-roll was a workaround for
        HTTP-source-buffering lag that doesn't apply to the bus tap).
        """
        logger.info(
            "STOP (show-record end, Liquidsoap)  %s  |  show_id=%s name=%r",
            key,
            event.show_id,
            event.show_name,
        )
        try:
            self._engine.recording_stop()
        except (OSError, ConnectionError) as exc:
            logger.error(
                "Show-record stop failed (Liquidsoap telnet): %s (key=%s show_id=%s name=%r)",
                exc,
                key,
                event.show_id,
                event.show_name,
            )
            return
        # RASTATIME 2026-10-19 - hand the closed file to the legacy API
        open_rec, self._open_show_recording = self._open_show_recording, None
        if open_rec is None:
            logger.info(
                "Show-record end: no open recording known for instance %s "
                "(recording started before this PLAYOUT instance?) - nothing "
                "reported to the library",
                getattr(event, "instance_id", None),
            )
            return
        instance_id = getattr(event, "instance_id", None) or open_rec[0]
        self._report_recording_finished(instance_id, open_rec[1])

    def _report_recording_finished(self, instance_id: Optional[int], path: Path) -> None:
        """
        RASTATIME 2026-10-19 - "Copy Show Recordings into Library": tell the
        legacy API that ``path`` is complete.  Runs in a daemon thread: it
        first waits for the file size to settle (Liquidsoap flushes the
        encoder after ``recording.stop``), then POSTs ``recording-finished``
        with three attempts twenty seconds apart.  The legacy side decides
        whether the checkbox is on, validates the path against the
        configured recording folder and imports a tagged copy; the file in
        the recording folder is never touched here.
        """
        if self._api_client_v1 is None:
            logger.info("Show-record end: no legacy API client - %s not reported", path)
            return
        if instance_id is None:
            logger.info("Show-record end: no instance id - %s not reported", path)
            return

        def _send() -> None:
            self._wait_for_stable_file(path)
            last_exc: Optional[BaseException] = None
            for attempt in range(1, 4):
                try:
                    resp = self._api_client_v1.notify_recording_finished(
                        instance_id=instance_id,
                        path=str(path),
                        timeout=120,
                    )
                    logger.info(
                        "recording-finished reported (instance %s, %s): HTTP %s %s",
                        instance_id,
                        path,
                        getattr(resp, "status_code", "?"),
                        (getattr(resp, "text", "") or "")[:200].replace("\n", " "),
                    )
                    return
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    last_exc = exc
                    logger.warning(
                        "recording-finished attempt %d/3 failed (instance %s): %s",
                        attempt,
                        instance_id,
                        exc,
                    )
                    time.sleep(self._recording_report_retry_seconds)
            logger.error(
                "recording-finished gave up (instance %s, %s): %s",
                instance_id,
                path,
                last_exc,
            )

        t = threading.Thread(target=_send, name=f"recording-finished-{instance_id}", daemon=True)
        t.start()

    # seconds between the three report attempts (tests shrink it)
    _recording_report_retry_seconds: float = 20.0
    # the file is "settled" when its size is unchanged over one poll
    _recording_settle_poll_seconds: float = 2.0
    _recording_settle_max_seconds: float = 30.0

    def _wait_for_stable_file(self, path: Path) -> None:
        """Block until ``path`` keeps its size over one poll (or the cap)."""
        deadline = time.monotonic() + self._recording_settle_max_seconds
        last = -1
        while time.monotonic() < deadline:
            try:
                size = path.stat().st_size
            except OSError:
                size = -1
            if size >= 0 and size == last:
                return
            last = size
            time.sleep(self._recording_settle_poll_seconds)
        logger.warning(
            "recording file %s did not settle within %.0f s",
            path,
            self._recording_settle_max_seconds,
        )

    def _recording_file_extension(self) -> str:
        """Extension of the rendered show-recording encoder (mp3 fallback)."""
        if self._recording_extension is None:
            return "mp3"
        try:
            ext = str(self._recording_extension() or "").strip().lower()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("recording extension lookup failed: %s", exc)
            return "mp3"
        return ext or "mp3"

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

        # RASTATIME 2026-09-27 - a file successor is queued behind this
        # track: its own start (the same instant when the rows are clipped
        # at a show boundary, or a few seconds later) decides the
        # hand-over - adopt, and skip only on overbook.  engine.stop()
        # here would FLUSH the queued successor and start a deferred skip
        # (rehearsal 2026-09-27: the new show's first track vanished from
        # the queue, the old track played on for 43 s).  Bookkeeping stays
        # with the successor's _on_file_start.
        if isinstance(self._current_event, FileEvent) and self._queued_ahead is not None:
            logger.info(
                "STOP  %s: successor %s is queued ahead - leaving the queue to its start.",
                key,
                self._queued_ahead[0],
            )
            return

        # RASTATIME 2026-09-29 - the timer fired on the whole second before
        # the row end; the track's last moments are still on air.
        self._let_file_run_out(key, self._current_event)
        if self._playing_key != key:
            logger.info(
                "STOP  %s: %s took over while the track ran out.",
                key,
                self._playing_key,
            )
            return
        # RASTATIME 2026-10-01 - a live item ends at its row's exact time,
        # not on the whole second (its gate closed up to a second early).
        if not isinstance(self._current_event, FileEvent) and not self._wait_for_exact_time(
            key,
            getattr(self._current_event, "end_exact", None),
            "STOP",
        ):
            return

        # Race fix #3 (line-in device-switch) — snapshot the line-in
        # generation while we still hold the spotlight.  A back-to-back
        # follow-up LineinEvent's ``_on_linein_start`` bumps this counter
        # just before it (re)starts the source; re-checking it before our
        # own teardown lets us bail instead of stopping the source the new
        # show just brought up.
        linein_gen = self._linein_generation

        was_linein = isinstance(self._current_event, LineinEvent)
        cur_device = (
            self._current_event.device_id  # type: ignore[attr-defined]
            if was_linein
            else None
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
        # B's _on_linein_start: keep the capture and the Liquidsoap
        # line-in source alive.  B's handler will see ``self._current_event`` is
        # still us (a LineinEvent with the same device_id) and take the
        # same-device-transition shortcut — net result is a pure
        # bookkeeping swap with zero audio bounce.
        #
        # We deliberately do NOT clear our own bookkeeping in this
        # branch — leaving _playing_key / _current_event in place is
        # exactly what makes B's same-device check fire.
        now = datetime.utcnow()
        if was_linein and cur_device is not None and self._linein_capture is not None:
            for other_key, other_event in self._armed_events.items():
                if other_key == key:
                    continue
                if not isinstance(other_event, LineinEvent):
                    continue
                if other_event.device_id != cur_device:
                    continue
                start_t, _ = self._timers.get(other_key, (None, None))
                if start_t is None or not start_t.is_alive():
                    continue
                # RASTATIME 2026-09-04 - "armed" is not "back-to-back".
                # Every line-in in the 24 h fetch window is armed; only
                # one starting at (practically) this instant may inherit
                # the running capture.  Anything further away gets the
                # normal teardown -- otherwise this line-in stays on air
                # through whatever is scheduled in between (the 11:00
                # incident: a follow-up 7 min out masked a whole show).
                starts_in = (other_event.start - now).total_seconds()
                if abs(starts_in) > LINEIN_FOLLOW_UP_WINDOW_SECONDS:
                    logger.info(
                        "STOP %s: same-device line-in %s is armed but starts "
                        "in %.0fs - not back-to-back, tearing down normally.",
                        key,
                        other_key,
                        starts_in,
                    )
                    continue
                logger.info(
                    "STOP %s: same-device follow-up %s starts in %.1fs "
                    "(device=%s) - skipping audio teardown; bookkeeping "
                    "handoff happens when its start timer fires.",
                    key,
                    other_key,
                    starts_in,
                    cur_device,
                )
                return

        # RASTATIME 2026-09-05 - same-stream follow-up (mirror of the
        # line-in rule above): a WebStreamEvent with the SAME url starting
        # within the back-to-back window inherits the running source; do
        # not release it here, _on_webstream_start does the hand-over.
        if was_webstream:
            cur_uri = getattr(self._current_event, "uri", None)
            for other_key, other_event in self._armed_events.items():
                if other_key == key or not isinstance(other_event, WebStreamEvent):
                    continue
                if other_event.uri != cur_uri:
                    continue
                start_t, _ = self._timers.get(other_key, (None, None))
                if start_t is None or not start_t.is_alive():
                    continue
                starts_in = (other_event.start - now).total_seconds()
                if abs(starts_in) > LINEIN_FOLLOW_UP_WINDOW_SECONDS:
                    continue
                logger.info(
                    "STOP %s: same-stream follow-up %s starts in %.1fs - "
                    "skipping release; hand-over happens at its start.",
                    key,
                    other_key,
                    starts_in,
                )
                return

        # Race fix #3 (line-in device-switch) — if a follow-up LineinEvent
        # already (re)started the source on its own timer thread (the
        # generation counter moved), leave ITS bookkeeping intact and tear
        # nothing down.  This is the device-INDEPENDENT companion to the
        # same-device handoff above: that one only fires while the
        # follow-up is still *armed*, this one also covers the follow-up
        # that has *already fired* (its start-timer is no longer alive, so
        # the scan above misses it).  Scoped to ``was_linein`` so
        # webstream/file stops — which must still run, since webstream
        # outranks line-in in the bus switch — are unaffected.
        if was_linein and self._linein_generation != linein_gen:
            logger.info(
                "STOP %s: a newer line-in source already started "
                "(gen %d->%d) — skipping teardown to keep it alive.",
                key,
                linein_gen,
                self._linein_generation,
            )
            return

        # RASTATIME 2026-09-04 - re-check ownership right before the
        # reset.  The check at the top of this handler and this point
        # are separated by telnet round-trips and the follow-up scan; a
        # successor's _on_*_start can take the spotlight in between (seen
        # live 2026-09-04 11:00:09: STOP(A) and PLAY(B) on the same
        # instant, STOP's reset landed AFTER PLAY's bookkeeping and wiped
        # it, so the next refresh "caught up" B again).  If the key moved,
        # the successor owns bookkeeping AND has closed our source itself
        # (_close_predecessor_source) - nothing left for us to do.
        if self._playing_key != key:
            logger.info(
                "STOP %s: superseded by %s during teardown - leaving its "
                "bookkeeping and sources alone.",
                key,
                self._playing_key,
            )
            return
        # The re-check above and this reset must stay adjacent: a
        # successor's bookkeeping swap that lands in between is wiped by
        # the reset (2026-09-10 11:16:08 - the teaser's bookkeeping was
        # lost and the next refresh re-"caught up" the running track;
        # harmless thanks to the engine's same-URI idempotency, but a
        # false state for 28 s).  Capture what we need, reset, then do
        # the slow work.
        _ce = self._current_event
        _item = getattr(_ce, "row_id", None)
        self._playing_key = None
        self._current_event = None
        self._current_audio_path = None
        # RASTATIME 2026-06-05 — cue mark (end of the current item) for the
        # 24/7 recording sidecar.  2026-09-10: written only by the owner
        # (after the re-check) - a superseded STOP used to stamp its "end"
        # ~30 ms behind the successor's "start"; the successor's start
        # implies our end.  The ``item`` id lets a reader pair the markers.
        # CueWriter.item_end reads the 24/7 config (a DB round trip), which
        # is why it runs AFTER the reset, not between re-check and reset.
        if isinstance(_ce, FileEvent):
            self._cue_item_end("track", item=_item)
        elif isinstance(_ce, WebStreamEvent):
            self._cue_item_end("webstream", item=_item)
        elif isinstance(_ce, LineinEvent):
            self._cue_item_end("linein", item=_item)

        # Stop the Line-In capture: at this point we know we ARE the
        # event being torn down AND no same-device successor needs the
        # capture alive.  Safe to call even when no capture is running
        # (idempotent).
        # RASTATIME 2026-09-04 - the capture is not stopped here:
        # _release_linein() (below) closes the gate first and stops
        # capture + source after the drain, so the buffered tail is heard.

        # If a DJ source is currently dominant, leave the engine alone —
        # the DJ audio stays on air.  Only the scheduled-event bookkeeping
        # above still happens.
        if self._switcher and self._switcher.current_state != SourceState.SCHEDULED:
            return

        # RASTATIME 2026-05-29 — Phase F: linein-specific teardown.
        # A linein-event uses input.http / input.ffmpeg (not the
        # request.queue), so engine.stop() alone would not close the
        # source.  _release_linein() closes the gate now and stops
        # capture + source after the drain.
        if was_linein:
            # Race fix #3 final guard — a follow-up show may have started
            # its source during the brief teardown window above (after we
            # cleared bookkeeping).  The generation counter survives that
            # reset, so re-check it here: if it moved, the source on air is
            # the new show's — do NOT stop it.
            if self._linein_generation != linein_gen:
                logger.info(
                    "STOP %s: newer line-in source started during teardown "
                    "(gen %d->%d) — not calling linein_stop.",
                    key,
                    linein_gen,
                    self._linein_generation,
                )
                return
            self._release_linein(f"slot end {key}")
            # No further engine.stop() / wait_until_stopped — the
            # linein had its own source path that's now closed.
            return

        # RASTATIME 2026-05-29 — Phase E: webstream-specific teardown.
        # A webstream-event uses input.http (not the request.queue), so
        # engine.stop() (which sends scheduled.skip) would not close the
        # HTTP session.  _release_webstream() closes the gate now and
        # stops the source after the drain, so the switch falls through
        # to scheduled.
        if was_webstream:
            self._release_webstream(f"slot end {key}")
            # No further engine.stop() / wait_until_stopped — the
            # webstream had its own source path that's now closed.
            return

        # RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1 (follow-up).
        # The _on_stop handler is the SECOND track-end stop path, fired
        # by the track-end Timer just as _on_*_start fires for the next
        # event.  Same bounded wait as in _on_*_start so a track that
        # is already at EOF returns immediately and a still-decoding
        # tail gets a brief grace period before the hard-stop (the
        # Liquidsoap engine returns at once).
        if self._engine.get_state() == PlayoutState.PLAYING:
            self._engine.wait_until_stopped(timeout=0.5)
            self._engine.stop()

    # ------------------------------------------------------------------
    # Source switcher (MASTER > SHOW > SCHEDULED)
    # ------------------------------------------------------------------

    def set_cue_writer(self, cue_writer) -> None:
        """
        Wire up the CueWriter (Record-per-Hour stage 5).  Called once from
        __main__.  Optional — without it, no cue sidecars are written.  The
        CueWriter swallows + logs its own errors, so these never break a
        live on-air callback.
        """
        self._cue_writer = cue_writer

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-28 - TuneIn now-playing (Settings -> TuneIn)
    # ------------------------------------------------------------------

    def _tunein_now_playing(
        self,
        kind: str,
        *,
        title: Optional[str],
        artist: Optional[str],
        show: Optional[str],
    ) -> None:
        """A track pushes title + artist; a webstream or line-in the show name."""
        if self._tunein is None:
            return
        try:
            if kind == "track":
                self._tunein.now_playing(title or show or "", artist or "", kind=kind)
            else:
                self._tunein.now_playing(show or "", "", kind=kind)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("TuneIn now-playing (%s) failed: %s", kind, exc)

    def _tunein_keepalive(self) -> None:
        if self._tunein is None:
            return
        try:
            self._tunein.keepalive()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("TuneIn keep-alive failed: %s", exc)

    def _cue_item_start(self, kind: str, **meta) -> None:
        cw = self._cue_writer
        if cw is not None:
            cw.item_start(kind, **meta)

    def _cue_item_end(self, kind: str, **meta) -> None:
        cw = self._cue_writer
        if cw is not None:
            cw.item_end(kind, **meta)

    # ------------------------------------------------------------------
    # RASTATIME 2026-09-13 - ICY metadata (Settings -> Streams)
    # ------------------------------------------------------------------

    def _refresh_storage_root(self) -> None:
        """
        RASTATIME 2026-09-16 - the media library root is a Local Machine
        setting (``local_storage_folder``); the API reports the effective
        value.  Direct file access follows it, so a move over the UI needs no
        playout restart.  Anything odd (old API, unreachable, mocked client)
        keeps the current value - the API download stays the fallback.
        """
        getter = getattr(self._api_client, "get_storage_location", None)
        if getter is None:
            return
        try:
            data = getter().json()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("storage location fetch failed: %s", exc)
            return
        root = data.get("root") if isinstance(data, dict) else None
        if isinstance(root, str) and root and root != self._storage_path:
            logger.info(
                "Storage root for direct file access: %s (was %s)", root, self._storage_path
            )
            self._storage_path = root

    def _sync_icy_metadata(self, events: dict[str, object], now: datetime) -> None:
        """
        Once per refresh: push the Stream Label / Off Air Metadata /
        station name when they changed (the reader is None without the
        ORM), then keep ``bus_show`` at the show on air.  Engines without
        the ICY methods (tests, ABC mocks) are skipped.
        """
        if not hasattr(self._engine, "icy_settings"):
            return
        if self._read_icy_preferences is not None:
            try:
                prefs = self._read_icy_preferences()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("ICY preferences could not be read: %s", exc)
                prefs = None
            if prefs is not None and prefs != self._icy_pushed:
                self._engine.icy_settings(
                    prefs.label_format,
                    prefs.offair_text,
                    prefs.station_name,
                )
                self._icy_pushed = prefs
        self._sync_live_text_settings()
        self._set_bus_show(self._show_on_air(events, now))

    def _sync_live_text_settings(self) -> None:
        """RASTATIME 2026-09-28 - push the Live Text switch + format when changed."""
        if self._live_text is None or not hasattr(self._engine, "live_text_settings"):
            return
        try:
            current = self._live_text.liquidsoap_settings()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Live Text settings could not be read: %s", exc)
            return
        if current is None or current == self._live_text_pushed:
            return
        self._engine.live_text_settings(current[0], current[1])
        self._live_text_pushed = current

    @staticmethod
    def _show_on_air(events: dict[str, object], now: datetime) -> str:
        """Name of the show whose file / webstream / line-in item covers
        ``now`` - '' when nothing is scheduled right now."""
        for event in events.values():
            if not isinstance(event, (FileEvent, WebStreamEvent, LineinEvent)):
                continue
            if event.start <= now < event.end:
                return (getattr(event, "show_name", "") or "").strip()
        return ""

    def _set_bus_show(self, show_name: str) -> None:
        """Push ``bus_show`` only when it changes (every telnet command
        leaks on the Windows build)."""
        if not hasattr(self._engine, "bus_show_set"):
            return
        name = (show_name or "").strip()
        if name == self._bus_show_pushed:
            return
        self._engine.bus_show_set(name)
        self._bus_show_pushed = name

    def set_source_switcher(self, switcher) -> None:
        """Wire up the SourceSwitcher.  Called once from __main__."""
        self._switcher = switcher

    def _request_source_reconcile(self) -> None:
        """
        Ask the SourceSwitcher's reconciler to verify the DJ state over
        telnet now (option d, 2026-09-09).  Called after a Liquidsoap
        restart: the harbor callbacks of the old process cannot report
        the connections that died with it, and the fresh process only
        reports new ones.
        """
        switcher = self._switcher
        if switcher is not None and hasattr(switcher, "request_reconcile"):
            switcher.request_reconcile()

    def switch_audio_source(self, state: SourceState) -> None:
        """
        React to a state transition signalled by the SourceSwitcher.

        Called from a daemon thread (the HTTP listener / Liquidsoap
        telnet reconciler), so we serialise access to the engine via
        the existing scheduler lock — that keeps us coherent against
        schedule refreshes and timer callbacks happening at the same
        moment.

        MASTER / SHOW are no-ops here: Liquidsoap's own
        ``switch(track_sensitive=true, [(source.is_ready(master_dj),
        master_dj), …])`` in rastatime.liq picks the active harbor via
        ``input.harbor.source.is_ready()`` (Phase-C4 Teil 2b).  Only
        SCHEDULED does work: after a DJ disconnect the in-progress
        scheduled item is pushed / re-armed so the bus has something to
        fall back to (see :meth:`_resume_scheduled_locked`).
        """
        logger.info("PlayoutScheduler: switching audio source to %s", state.value)

        with self._lock:
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

    def kick_dj_source(self, kind: str) -> None:
        """
        Force-disconnect the DJ currently connected to the Master or
        Show harbor.

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

        RASTATIME 2026-09-10: the kick goes over telnet to the harbor
        inside Liquidsoap (``master_dj.stop`` / ``show_dj.stop``).  The
        former Icecast admin ``killsource`` of the deleted mpv path
        could not reach a DJ at all - since Phase C4 the DJs connect to
        the harbor on port 8001, not to Icecast.  The harbor's
        on_disconnect callback then reports the disconnect to
        /source-event, the SourceSwitcher goes to SCHEDULED and the
        resume path runs as for a voluntary hang-up.  Best-effort: a
        telnet error is logged by the engine and swallowed.
        """
        kind_norm = (kind or "").lower()
        if kind_norm in ("master", "master_dj"):
            source = "master"
        elif kind_norm in ("show", "live_dj", "dj"):
            source = "show"
        else:
            logger.warning(
                "kick_dj_source: unknown source kind %r — ignoring.",
                kind,
            )
            return
        if not hasattr(self._engine, "dj_kick"):
            logger.warning(
                "kick_dj_source(%s): the engine cannot kick harbor clients — ignoring.",
                kind,
            )
            return
        logger.info("kick_dj_source(%s) -> Liquidsoap %s harbor stop", kind, source)
        self._engine.dj_kick(source)

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
          * ``LineinEvent``    — re-arm the Liquidsoap line-in source
                                 (input.http companion on the feeder's
                                 /linein-capture mount, or the direct
                                 dshow source).  The capture keeps
                                 running across DJ-override windows,
                                 so the mount is already populated and
                                 resume is quick.  (Phase B / F.)

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
            # RASTATIME 2026-09-10 - same wiring as _on_webstream_start:
            # the slot may have begun while the DJ was live (source never
            # started), or the source is still running underneath the DJ
            # (webstream.start on the same URL answers "already started"
            # in the .liq).  Until the mpv cleanup this pushed the URL
            # through engine.play, i.e. into the request queue as a file
            # request.
            self._webstream_generation += 1
            self._engine.webstream_start(
                self._current_audio_path,
                gain_db=self._current_gain_db,
            )
            self._engine.webstream_gate(True)
            return

        if isinstance(self._current_event, LineinEvent):
            logger.info(
                "Resume scheduled line-in: device=%s name=%r  show: %s",
                self._current_event.device_id,
                self._current_event.name,
                self._current_event.show_name,
            )
            resume_device_id = self._resolve_linein_device(self._current_event)
            if not resume_device_id:
                logger.error(
                    "Resume line-in: device %r unavailable (no "
                    "name-fallback match for %r) — capture stays down.",
                    self._current_event.device_id,
                    getattr(self._current_event, "device_name", "") or "",
                )
                return
            mapping = list(getattr(self._current_event, "channel_mapping", None) or [0, 1])
            dev_name = getattr(self._current_event, "device_name", "") or ""
            # RASTATIME 2026-09-03 - mirrors the Option B decision in
            # _on_linein_start: the feeder serves every mapping, plain
            # stereo included, and dshow is only the legacy fallback for
            # rows without a stored device name.  Kept in lockstep on
            # purpose -- if this branch still sent 1/2 to dshow, a
            # Liquidsoap restart mid-show would silently drop a studio
            # slot back onto the by-GUID path that plays silence.
            use_feeder = bool(dev_name)

            # Make sure the capture is still running where the path
            # needs it.  start() is same-device+mapping idempotent, so
            # this never bounces a healthy pipeline.
            if self._linein_capture is not None and use_feeder:
                try:
                    self._linein_capture.start(
                        resume_device_id,
                        channel_mapping=tuple(mapping),
                        device_name=dev_name,
                    )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.error(
                        "Resume line-in: capture (re)start failed: %s",
                        exc,
                    )

            # RASTATIME 2026-08-31 — re-arm the linein sources themselves
            # (mirror of _on_linein_start).
            self._linein_generation += 1
            self._apply_linein_gain(self._current_event)  # 2026-10-02
            if use_feeder:
                self._engine.linein_start_http()
                self._engine.linein_gate(True)
            else:
                from .engine.ffmpeg_linein_capture import (
                    _stable_id_to_dshow_audio,
                )

                self._engine.linein_start(_stable_id_to_dshow_audio(resume_device_id))
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
                "title": self._current_event.track_title or "",
                "artist": self._current_event.artist_name or "",
                "show_name": self._current_event.show_name or "",
            }
        self._engine.play(
            self._current_audio_path,
            cue_in=cue_in,
            gain_db=self._current_gain_db,
            metadata=resume_metadata,
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
                    schedule_row_id,
                    exc,
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
                    full_path,
                    full_path.stat().st_size,
                )
                return full_path
            else:
                logger.debug("Direct storage miss: %s", full_path)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Direct storage lookup failed for file %d: %s", event.id, exc)

        return None
