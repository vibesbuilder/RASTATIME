RASTATIME — readme.txt
=======================

Version: 0.3.7
Date: 2026-04-25

Summary
-------
T8.1 complete: QUEUE_BEHAVIOR.md written. Authoritative contract for queue
priority (live > show > fallback), transition rules (HARD/SOFT), all edge
cases, and known limitations vs. LibreTime/Liquidsoap. No code changes.
Total: 232/232. Milestone M8 started.

Changelog
---------
0.3.7 (2026-04-25)
    - Task T8.1 complete: QUEUE_BEHAVIOR.md written.
    - docs/architecture/QUEUE_BEHAVIOR.md: authoritative queue behavior
        contract for T8.2 (QueueManager) and T8.3 (scheduler–engine wiring).
      §1 Purpose — scope and authority of the document.
      §2 Queue types and priority table: live input (P1, reserved) >
         scheduled show (P2) > fallback/filler (P3).
      §3 Content sources: ScheduledShow fields and validation rules;
         FallbackQueue fields; empty-items guard.
      §4 Transition rules (6 sub-rules):
         4.1 Show start HARD (stop + disable fallback + load + start) and
             SOFT (splice after current track, fallback disabled).
         4.2 Show end: hard stop + fallback trigger.
         4.3 Fallback start: load_queue + start.
         4.4 Fallback restart (loop=True): daemon thread on queue-exhausted
             TrackChangedEvent.
         4.5 Fallback stop (loop=False): engine to STOPPED, no auto-restart.
         4.6 Show interrupts fallback: HARD stops immediately; SOFT waits.
      §5 Edge cases table (12 scenarios): past show, past start/future end,
         empty items, same show_id replacement, overlapping different shows,
         back-to-back shows, no fallback configured, clear_fallback while
         playing, clear_fallback before end, engine error, single-item loop,
         set_fallback while playing.
      §6 Known limitations (8 items flagged against LibreTime):
         cue points ignored, inter-track silence 50-200 ms, no crossfade,
         no replay gain, single sequential queue (vs. 4 Liquidsoap queues),
         no live DJ / line-in yet, no web-stream input type, timer precision
         on Windows.
      §7 Planned QueueManager (T8.2) — role and responsibilities.
      §8 State diagram (ASCII art).
      §9 Revision history.
    - No code changes; 232/232 unit tests still green.

0.3.6 (2026-04-25)

Changelog
---------
0.3.6 (2026-04-25)
    - Task T7.2 complete: feed now-playing and history.
    - playout/now_playing/_state.py: NowPlayingState + NowPlayingEntry.
        NowPlayingEntry(item, started_at): is_playing property; to_dict()
          produces JSON-serialisable shape with item sub-dict + ISO timestamp.
        NowPlayingState: thread-safe (threading.Lock); on_track_change()
          registered with engine; get() returns snapshot; subscribe(cb)
          notifies on every change; crashing subscriber isolated.
    - playout/now_playing/_history.py: PlayoutHistoryLogger + HistoryEntry.
        HistoryEntry(item, started_at, ended_at): duration_played property;
          to_dict() with item_id/title/artist/started_at/ended_at/duration.
        PlayoutHistoryLogger(max_entries=500): deque ring-buffer; on_track_change()
          finalises previous entry (sets ended_at) and opens a new one;
          recent(n) returns completed entries newest-first; current() returns
          the in-progress entry (no ended_at); total_completed() count.
    - playout/now_playing/__init__.py: exports + module-level singletons
        default_state and default_logger for single-process deployments.
        connect_engine(engine, state, logger): wires both sinks to
          engine.on_track_change() in one call; defaults to singletons.
    - backend/api/libretime_api/now_playing.py: Django view.
        GET /api/v2/now-playing — reads default_state.get().to_dict();
          always returns HTTP 200; is_playing discriminates idle/active.
          Lazy import of playout.now_playing avoids circular dependency.
    - backend/api/libretime_api/urls.py: added path for now-playing view.
    - tests/unit/playout/test_now_playing.py: 18 tests.
        NowPlayingState (6): idle init, track start/stop, to_dict shapes,
          subscriber notification, crashing subscriber isolation.
        PlayoutHistoryLogger (8): empty init, current on start, finalise
          on next start, duration_played, stop finalises last, to_dict,
          total_completed, recent() cap.
        connect_engine (1): wires both sinks to MockPlayoutEngine; asserts
          state and logger reflect the running track.
        V criterion — mock (1): MockPlayoutEngine plays 3 TICK-duration
          tracks; history accumulates ≥ 2 completed entries (t0, t1 in set).
        V criterion — VLC (1): VlcPlayoutEngine plays 2 WAVs; history has
          ≥ 1 completed entry with id "vlc-a".
    - Production note: multi-process deployments need a shared transport
        (Redis, DB) — current singleton is for single-process / dev use.
    - 232/232 unit tests green. Milestone M7 complete.

0.3.5 (2026-04-25)

Changelog
---------
0.3.5 (2026-04-25)
    - Task T7.1 complete: subscribe to libVLC events; normalize payload.
    - playout/engine_vlc/events.py: new module.
        extract_vlc_meta(media) -> dict: standalone function; reads
          title, artist, album, genre, track_number, year, description
          from vlc.Media.get_meta(); adds duration_ms (int ms) when VLC
          reports >= 0; returns {} for None media or missing python-vlc.
        VlcEventBridge(player): subscribes to four MediaPlayer events:
          MediaPlayerMediaChanged, MediaPlayerPlaying,
          MediaPlayerEndReached, MediaPlayerEncounteredError.
        attach() / detach(): idempotent; detach() uses event_detach(type)
          (python-vlc does not accept a callback argument in detach).
        on_playing(cb(meta)), on_end_reached(cb()), on_error(cb()),
          on_media_changed(cb()): callback registrars; all called on
          VLC's internal event thread.
        _vlc_playing(): calls extract_vlc_meta(player.get_media()) and
          passes result to all on_playing callbacks.
        Crashing callbacks are caught per-callback; others still run.
    - playout/engine_vlc/_engine.py: refactored to use VlcEventBridge.
        __init__: removed direct event_attach calls; creates
          VlcEventBridge, registers on_end_reached/_on_vlc_end,
          on_error/_on_vlc_error, on_playing/_on_vlc_playing, then
          calls bridge.attach().
        _on_vlc_end(): signature changed from (self, event) to (self);
          same behaviour (spawns daemon thread for _advance_track).
        _on_vlc_error(): signature changed from (self, event) to (self);
          same behaviour (sets ERROR state, fires error callbacks).
        _on_vlc_playing(meta): new method; enriches current QueueItem
          under _lock: fills item.title / item.artist if empty; stores
          remaining VLC fields in item.metadata["vlc"].
        close(): calls bridge.detach() before releasing player/instance.
    - playout/engine_vlc/__init__.py: exports VlcEventBridge and
        extract_vlc_meta alongside VlcPlayoutEngine.
    - tests/unit/playout/engine_vlc/test_events.py: 16 tests.
        extract_vlc_meta (5): None -> {}, title/artist mock, duration_ms,
          empty strings omitted, negative duration omitted.
        VlcEventBridge attach/detach (4): registers 4 event types,
          idempotent attach, detach unregisters, detach-before-attach noop.
        Event simulation via _MockEventManager (6): on_playing fires with
          meta, on_end_reached, on_error, on_media_changed, crashing
          callback isolation, multiple callbacks all receive event.
        V criterion (VLC): test_vlc_engine_item_metadata_enriched_with_
          duration_ms — plays a 1 s WAV with --aout=dummy; polls until
          item.metadata["vlc"]["duration_ms"] is populated; asserts int > 0.
    - Bug fixed: event_detach() in python-vlc only accepts event_type,
        not a callback argument (unlike event_attach).
    - 214/214 unit tests green.

0.3.4 (2026-04-24)
FallbackQueue stub; PlayoutScheduler fallback management (set_fallback,
clear_fallback, fallback_is_active); auto-restart for looping fallback;
show interrupts fallback via HARD mode. 13 new tests (mock + VLC).
Total: 198/198. Milestone M6 continued.

Changelog
---------
0.3.4 (2026-04-24)
    - Task T6.2 complete: fallback playout entry.
    - playout/fallback/_queue.py: FallbackQueue stub.
        __init__(items, loop=True): rejects empty list (ValueError).
        items property: returns a copy of the internal list.
        loop property: True = restart after last item; False = play once.
        is_empty(): always False for a valid instance (constructor guards).
        __len__(): delegates to internal list length.
    - playout/fallback/__init__.py: re-exports FallbackQueue.
    - playout/scheduler/_scheduler.py: fallback management added.
        PlayoutScheduler.__init__: _fallback=None, _fallback_active=False;
          registers engine.on_track_change(self._on_engine_track_change).
        set_fallback(fb): stores FallbackQueue under lock.
        clear_fallback(): clears queue + active flag under lock.
        fallback_is_active(): returns _fallback_active under lock.
        _on_engine_track_change(event): if engine stops (current_item None)
          while fallback active and loop=True, spawns _trigger_fallback thread.
        _on_stop(show_id): calls engine.stop(), sets _fallback_active=True,
          spawns _trigger_fallback thread if fallback configured.
        _hard_start(show): sets _fallback_active=False BEFORE load_queue()
          to prevent spurious fallback restart from the stop callback.
        _soft_start(show): same guard for _fallback_active.
        _trigger_fallback(): engine.load_queue(fb.items) + engine.start();
          called only in daemon threads, never on the engine callback thread.
    - tests/unit/playout/test_fallback.py: 13 tests.
        FallbackQueue unit tests (4): stores items, non-looping, rejects
          empty, items property returns a copy.
        Scheduler configuration tests (2): set_fallback does not activate
          fallback immediately; clear_fallback removes config.
        V criterion (mock): fallback starts after show ends; active flag
          is True while fallback is playing.
        Interruption: HARD-mode show stops fallback and plays show items.
        Looping: fallback restarts after last item (loop=True).
        Non-looping: fallback plays once then engine stops (loop=False).
        Suppress: clear_fallback() prevents fallback from starting.
        V criterion (VLC): smoke test — VLC show plays, then VLC fallback
          starts; skipped if VLC not installed.
    - Timing bug found + fixed in tests: fallback item duration must exceed
      the assertion wait-time; show2 end_at must exceed MARGIN to avoid
      stop-timer triggering a re-activation before the assert.
    - 198/198 unit tests green.

0.3.3 (2026-04-25)
    - Task T6.1 complete: scheduler actions mapped to engine.
    - playout/scheduler/_scheduler.py: major extension.
        StartMode(str, Enum): HARD (stop+load+start) and SOFT (splice
          after current track, or fall back to HARD if stopped).
        ScheduledShow: new start_mode field (default HARD).
        PlayoutScheduler._on_start(): dispatches to _hard_start() or
          _soft_start() based on show.start_mode.
        _hard_start(): engine.load_queue(items) + engine.start().
        _soft_start(): if STOPPED falls back to hard; if PLAYING calls
          engine.clear_queue() + engine.append() for each item so new
          items play after the current track without interruption.
        schedule_next(show): immediately appends items via engine.append()
          and arms a SOFT-mode timer for near-gapless hand-off.
    - playout/scheduler/__init__.py: exports StartMode.
    - tests/unit/playout/test_scheduler_engine.py: 9 tests.
        Mock: StartMode enum values, default start_mode, HARD from
          playing/stopped, SOFT from stopped (fallback), SOFT splices
          after current track (4 events in order), schedule_next.
        VLC (V criterion): test_two_hard_shows_back_to_back_vlc —
          schedules two 0.5 s shows back-to-back against VlcPlayoutEngine;
          asserts both items played and both stopped (4 events total).
        VLC: test_soft_show_splices_after_current_track_vlc — B splices
          after A without interruption.
    - 185/185 unit tests green.

Changelog
---------
0.3.2 (2026-04-25)
    - Task T5.4 complete: transport controls.
    - playout/engine_vlc/_engine.py:
        VlcPlayoutEngine class docstring: state-machine diagram with
          all valid transitions and idempotent-call rules.
        pause(): now uses set_pause(True) instead of the toggle pause()
          — explicit, non-toggling, safe to call from any thread.
        resume(): now uses set_pause(False) — symmetric with pause().
        Both methods document their idempotency contract.
    - tests/unit/playout/engine_vlc/test_transport_controls.py: 14 tests.
        V criterion: test_full_state_machine_cycle — exercises
          STOPPED->PLAYING->PAUSED->PLAYING->STOPPED with event
          assertion at each boundary.
        pause(): freeze test (remaining unchanged while paused),
          idempotent from PAUSED, no-op from STOPPED.
        resume(): continues from paused position (remaining decreases
          after resume), no-op from PLAYING, no-op from STOPPED.
        stop(): from PAUSED->STOPPED with callback; from STOPPED is
          no-op; double stop() idempotent.
        Restart: start() after stop() restarts from item 0.
        remaining_duration: None when stopped, None after stop from
          pause, decreases while playing.
    - 176/176 unit tests green.
    - Milestone M5 (libVLC basic playback) complete.

Changelog
---------
0.3.1 (2026-04-25)
    - Task T5.3 complete: queue playback.
    - playout/engine_vlc/_engine.py: documentation update.
        Module docstring: "Inter-track gap" section documents the
        50-200 ms silence between items (thread spawn + media_new +
        VLC buffer startup); notes planned gapless improvement via
        libvlc_media_list_player.
        _advance_track() docstring: explains the gap and why VLC
        operations are done outside the lock.
    - tests/unit/playout/engine_vlc/test_queue_playback.py: 7 tests.
        V criterion: test_three_item_queue_plays_in_order — 3-item
        queue plays in order; asserts 4 TrackChangedEvents with correct
        previous/current item references, STOPPED state and None
        current_item after queue exhaustion.
        Additional: event timestamps (UTC-aware), multiple listeners
        receive all events, append during playback, clear_queue discards
        pending items, load_queue during playback stops and replaces,
        inter-track gap < 2 s bound.
    - 162/162 unit tests green.

Changelog
---------
0.3.0 (2026-04-25)
    - Task T5.2 complete: VlcPlayoutEngine.
    - playout/engine_vlc/_engine.py: VlcPlayoutEngine(PlayoutEngine).
        One vlc.Instance + one MediaPlayer reused for all items.
        start(): loads first item, calls player.play(), fires callback.
        stop(): sets STOPPED, calls player.stop(), fires callback.
        pause()/resume(): delegate to player.pause() (VLC toggle).
        load_queue(): replaces queue, stops if active.
        append()/clear_queue(): same semantics as MockPlayoutEngine.
        get_remaining_duration(): uses player.get_time()/get_length()
          (ms); falls back to item.duration if VLC reports -1.
        select_output_device(): calls audio_output_device_set(); silent
          best-effort.
        close(): releases player and instance resources.
        _on_vlc_end(): dispatches _advance_track() to daemon thread
          (avoids deadlock from VLC callback thread).
        _advance_track(): increments index, loads next URI outside lock,
          fires track-change callbacks.
        _on_vlc_error(): sets ERROR state, fires on_error callbacks.
    - playout/engine_vlc/__init__.py: exports VlcPlayoutEngine.
    - tests/unit/playout/engine_vlc/test_vlc_engine.py: 18 tests.
        All use real WAV files (0.5 s, sine tone) + --aout=dummy.
        V criterion: test_end_of_file_fires_callback_and_stops asserts
          STOPPED state and item->None event after WAV playback ends.
        Transport: start/stop/pause/resume; idempotency; empty-queue.
        Queue: load_queue, append, clear_queue (playing + stopped).
        State: remaining_duration, get_current_item, get_state.
        Callbacks: multiple listeners; crashing callback guard.
    - tests/unit/rastatime_common/test_engine_config.py: updated
        libvlc test split into VLC-present path (skip if absent) and
        mocked ImportError path.
    - 155/155 unit tests green.

Changelog
---------
0.2.9 (2026-04-25)
    - Task T5.1 complete: python-vlc dependency + libVLC runtime probe.
    - requirements.txt (repo root): python-vlc>=3.0.12, pytest>=7.0.
    - playout/engine_vlc/__init__.py: package scaffold (T5.2 fills it).
    - playout/engine_vlc/probe.py: ProbeResult dataclass + probe() function.
        _find_dll(): searches known Windows paths + HKLM registry key.
        _dll_bits(): reads PE header to determine 32/64 bitness of DLL.
        _python_bits(): struct.calcsize("P")*8.
        probe(): imports vlc, locates DLL, checks bitness match, calls
          vlc.libvlc_get_version() and vlc.Instance(); all errors captured
          in ProbeResult.errors; never raises.
        ProbeResult.raise_if_unavailable(): raises RuntimeError with message.
        ProbeResult.summary(): single-line status string.
        __main__ block: CLI report; exit 0=OK / 1=unavailable.
    - tests/unit/playout/engine_vlc/test_probe.py: 19 tests.
        VLC-installed path: available=True, version strings, DLL path,
          bitness match, summary, raise_if_unavailable no-op.
        Mocked paths: no python-vlc -> available=False; bitness mismatch
          detected; invalid/missing DLL -> _dll_bits returns None.
    - Verified on this machine: libvlc 3.0.23 Vetinari, 64-bit, probe OK.
    - 136/136 unit tests green.

0.2.8 (2026-04-24)
    - Task T4.3 complete: PlayoutScheduler.
    - Timer-based start/stop dispatch; cancel/cancel_all; reschedule support.
    - 12 new tests, 117/117 green. Phase 3 (Playout Abstraction) complete.

Changelog
---------
0.2.8 (2026-04-24)
    - Task T4.3 complete: PlayoutScheduler.
    - playout/scheduler/_scheduler.py: PlayoutScheduler + ScheduledShow.
        ScheduledShow: show_id, start_at (UTC), end_at (UTC), items;
          naive datetimes normalised to UTC in __post_init__.
        PlayoutScheduler: wraps any PlayoutEngine; uses threading.Timer
          pairs (start + stop) per show; _pending dict protected by Lock.
        schedule(show): fires load_queue+start at start_at, stop at
          end_at; past shows ignored; same show_id replaces previous job.
        cancel(show_id) -> bool: cancels one pending show.
        cancel_all() -> int: cancels all pending shows.
        pending_show_ids(): snapshot of pending show ids.
        Engine calls made outside the lock; exceptions caught per-call.
    - playout/scheduler/__init__.py: re-exports PlayoutScheduler, ScheduledShow.
    - tests/unit/playout/test_scheduler.py: 12 tests.
        V criterion: test_show_starts_and_stops asserts STOPPED->PLAYING
        ->STOPPED transitions on a short scheduled show.
        Additional: queue content, past shows, ongoing shows, cancel,
        cancel_all, reschedule, pending_show_ids, ScheduledShow helpers.
    - 117/117 unit tests green.
    - Phase 3 (Playout Abstraction) complete.

Changelog
---------
0.2.7 (2026-04-24)
    - Task T4.2 complete: engine selection config flag.
    - rastatime_common/__init__.py: new top-level package.
    - rastatime_common/config.py: PlayoutEngineKind(str, Enum) with
      MOCK and LIBVLC values; get_playout_engine_kind() reads
      RASTATIME_PLAYOUT_ENGINE env var (case-insensitive, strips
      whitespace, defaults to "mock"); create_playout_engine(kind,
      **kwargs) factory returns MockPlayoutEngine for MOCK and raises
      ImportError with helpful message for LIBVLC (Phase 4).
    - tests/unit/rastatime_common/test_engine_config.py: 12 tests.
        Covers: enum values, str-enum comparison, default/env/case/
        whitespace/invalid for get_playout_engine_kind, explicit/
        env/kwargs for create_playout_engine(MOCK), ImportError path
        for create_playout_engine(LIBVLC).
    - 105/105 unit tests green.

0.2.6 (2026-04-24)
    - Task T4.1 complete: MockPlayoutEngine.
    - playout/engine_mock/_engine.py: full MockPlayoutEngine(PlayoutEngine).
        Thread-safe via threading.RLock.
        Automatic queue advance via threading.Timer in _advance_track().
        on_track_change callbacks fired outside lock (deadlock-safe).
        Exceptions in callbacks caught per-callback (guard pattern).
        pause()/resume() preserve _paused_remaining; rebase _start_time.
        load_queue() stops playback and fires track_change to None.
        clear_queue() keeps current item; removes pending items only.
        select_output_device() is a safe no-op.
    - playout/engine_mock/__init__.py: re-exports MockPlayoutEngine.
    - tests/unit/playout/test_mock_engine.py: 18 tests.
        V criterion: test_state_transitions_3_item_queue verifies
        4 TrackChangedEvents on a 3-item queue (None->t0, t0->t1,
        t1->t2, t2->None) using TICK=0.05 s tracks.
        Additional: transport controls, queue management, pause/resume,
        remaining duration, device no-op, multiple callbacks,
        crashing callback guard.
    - 93/93 unit tests green.
    - Milestone M4 (Mock playout engine) complete.

Changelog
---------
0.2.5 (2026-04-24)
    - Task T3.5 complete: stub unsupported runtime modules.
    - backend/worker/libretime_worker/config.py: guard kombu import and
      config loading; exposes RASTATIME_WORKER_AVAILABLE flag.
    - backend/worker/libretime_worker/tasks.py: guard celery/mutagen/
      libretime_api_client imports; stub decorators (worker.task, signals)
      so module parses cleanly; exposes RASTATIME_TASKS_AVAILABLE flag.
    - backend/playout/libretime_playout/liquidsoap/main.py: guard
      libretime_api_client.v2 and jinja2-dependent sub-imports;
      exposes _PLAYOUT_DEPS_AVAILABLE flag.
    - backend/analyzer/libretime_analyzer/pipeline/analyze_metadata.py:
      guard mutagen import; skip EasyID3.RegisterKey when unavailable;
      exposes _MUTAGEN_AVAILABLE flag.
    - backend/api/libretime_api/settings/dev.py: added
      RASTATIME_WINDOWS_MODE = True feature flag.
    - Verified: all 4 modules import without error; Django setup OK.
    - 75/75 unit tests green.
    - Phase 2 (Windows dev bootstrap) fully complete.

0.2.4 (2026-04-24)
    T3.4 complete: docs/dev/WINDOWS_DEV_STATUS.md created.
6 blockers documented (PostgreSQL, gunicorn, psycopg v3, Liquidsoap,
Celery, libVLC). Quick-start guide for new contributors included.
Milestone M3 (Windows dev bootstrap) complete.

Changelog
---------
0.2.4 (2026-04-24)
    - Task T3.4 complete: WINDOWS_DEV_STATUS.md.
    - docs/dev/WINDOWS_DEV_STATUS.md: honest dev status document.
        Section 1: environment — what is installed and working.
        Section 2: what works (interface layer, dev scripts, API, worker).
        Section 3: what is stubbed or disabled (Liquidsoap, Celery,
                   gunicorn, analyzer, LibreTime playout).
        Section 4: 6 known blockers (B1-B6) with workarounds + resolution.
        Section 5: next steps table (T3.5 through T17.1).
        Section 6: quick-start guide for new contributors.
    - Milestone M3 (Windows dev bootstrap) complete.

0.2.3 (2026-04-24)
    T3.3 complete: Worker run script at infra/scripts/dev/run-worker.ps1.
Dev stub logs "idle" immediately on start (V verified). 75/75 unit tests green.

Changelog
---------
0.2.3 (2026-04-24)
    - Task T3.3 complete: worker run script.
    - infra/scripts/dev/run-worker.ps1 (#Requires -Version 5.1, UTF-8 BOM).
        Parameter: -IdleInterval (default 5s).
        Auto-detects .venv; sets PYTHONPATH to backend/ + backend/shared/.
        Starts python -m rastatime_worker.
    - backend/rastatime_worker/__main__.py: dev stub entry point.
        Logs "idle" immediately on start (satisfies V: within 2s).
        Heartbeat loop every IdleInterval seconds.
        Graceful shutdown on SIGINT/SIGTERM.
        Imports JobRunner interface at startup to verify import is clean.
    - Verified: worker logs "idle" at t=0s, t=1s, t=2s (with --idle-interval 1).

0.2.2 (2026-04-24)
    T3.2 complete: API dev-server run script at infra/scripts/dev/run-api.ps1.
    Adds Django dev settings (no config file required), a /health endpoint
    (DB-independent), and the PowerShell launcher. libretime_api/__init__.py
    patched to handle missing package metadata gracefully. No new unit tests (manual V).

Changelog (continued)
---------------------
0.2.2 (2026-04-24)
    - Task T3.2 complete: API run script.
    - infra/scripts/dev/run-api.ps1 (#Requires -Version 5.1).
        Parameters: -BindHost (default 127.0.0.1), -Port (default 8000).
        Auto-detects .venv; falls back to PATH python.
        Sets PYTHONPATH to backend/api + backend/shared (no editable install needed).
        Sets DJANGO_SETTINGS_MODULE=libretime_api.settings.dev.
        Prints health URL + Swagger URL before starting.
    - backend/api/libretime_api/settings/dev.py (new).
        No config file (LIBRETIME_CONFIG_FILEPATH) required.
        PostgreSQL defaults match LibreTime; override via RASTATIME_DB_* env vars.
        CORS allow-all; email to console; DEBUG=True.
    - backend/api/libretime_api/health.py (new).
        GET /health — returns {"status":"ok","service":"rastatime-api","version":"..."}.
        No database access; responds even before migrations run.
    - backend/api/libretime_api/urls.py — added path("health", ...).
    - backend/api/libretime_api/__init__.py — handle PackageNotFoundError so
      VERSION falls back to "dev" when package metadata is absent.
    - Verification: manual (dev server responds to /health after deps installed).
    - backend/shared/setup.py: pydantic constraint relaxed from <2.8 to >=2.9
      so pre-built wheels are available for Python 3.13 (no Rust/MSVC needed).
    - backend/api/libretime_api/settings/dev.py: switched default DB to SQLite
      so runserver starts without PostgreSQL; set RASTATIME_USE_POSTGRES=true
      to revert to PostgreSQL.

0.2.1 (2026-04-24)
    - Task T3.1 complete: PowerShell bootstrap checker.
    - infra/scripts/dev/bootstrap.ps1 (#Requires -Version 5.1).
    - Required checks: Python 3.11+, PostgreSQL, VLC + libvlc.dll.
    - Optional check:  RabbitMQ (SKIP, not FAIL if absent).
    - Detection strategies:
        Python:     PATH (python / python3), version parse
        PostgreSQL: psql on PATH, pg_isready on PATH, Windows service,
                    Program Files install directory
        VLC:        PATH, Program Files\VideoLAN\VLC, HKLM registry key;
                    libvlc.dll presence verified separately
        RabbitMQ:   Windows service, PATH
    - Color-coded output; inline remediation links on failure.
    - Execution policy unblock steps documented in .NOTES block.
    - Exit code 0 = all required deps present; 1 = missing.
    - Verified: script structure checks pass.

0.2.0 (2026-04-24)
    - Task T2.5 complete: ServiceHealth ABC (infra/service_health/).
    - HealthStatus: HEALTHY, DEGRADED, UNHEALTHY.
    - ComponentHealth: per-component report + to_dict() (ISO-8601 UTC timestamp).
    - SystemHealth: aggregate report + from_components() (worst-case rollup)
      + to_dict(); JSON shape spec embedded in class docstring.
    - ServiceHealth ABC — 3 abstract methods:
        check_health() -> ComponentHealth
        is_alive()     -> bool  (liveness probe)
        is_ready()     -> bool  (readiness probe)
    - tests/unit/service_health/test_service_health_interface.py: 18 tests.
    - Total unit tests: 75/75 green.
    - Milestone M2 (Runtime interfaces) complete.

0.1.9 (2026-04-24)
    - Task T2.4 complete: JobRunner ABC (backend/rastatime_worker/).
    - JobStatus: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, RETRYING.
    - JobInfo: runtime metadata for one submitted job instance.
    - JobResult: outcome of a completed or failed job instance.
    - JobNotFoundError, JobNameNotRegisteredError: typed exceptions.
    - JobRunner ABC — 11 abstract methods:
        Registration:  register, registered_jobs
        One-shot:      submit
        Recurring:     schedule, unschedule, list_schedules
        Status:        status, result
        Cancellation:  cancel
        Lifecycle:     start, stop
    - Handler-by-name pattern avoids Celery/multiprocessing pickling issues.
    - tests/unit/worker/test_job_runner_interface.py: 20 tests, all passing.
    - Total unit tests: 57/57 green.

0.1.8 (2026-04-24)
    - Task T2.3 complete: AudioDeviceManager ABC (audio/soundcard/).
    - AudioDevice: stable_id, name, kind, channels, driver, is_default,
      is_available, raw_id, metadata.
    - AudioDeviceKind: OUTPUT | INPUT.
    - DeviceUnavailableError: typed exception carrying device_id.
    - AudioDeviceManager ABC — 9 abstract methods:
        Enumeration:  list_outputs, list_inputs,
                      get_default_output, get_default_input
        ID resolution: resolve_stable_id, lookup_by_stable_id
        Selection:    open_output, open_input, close_output, close_input
    - tests/unit/audio/test_audio_device_manager.py: 13 tests, all passing.
    - Total unit tests: 37/37 green.

0.1.7 (2026-04-24)
    - Task T2.2 complete: stream ingress/egress interfaces defined.
    - streams/_types.py: StreamProtocol (ICECAST, SHOUTCAST),
      StreamState (IDLE, CONNECTING, ACTIVE, DISCONNECTED, ERROR).
    - streams/egress/interface.py: StreamEgressManager ABC (9 abstract
      methods), StreamOutput, OutputStatus, OutputStateChangedEvent.
    - streams/ingress/interface.py: StreamIngressManager ABC (8 abstract
      methods), StreamSource, SourceStatus, SourceStateChangedEvent.
    - tests/unit/streams/test_stream_interfaces.py: 14 tests, all passing.
    - Total unit tests: 24/24 green.

0.1.6 (2026-04-24)
    - Task T2.1 complete: PlayoutEngine ABC (playout/engine_interface/).
    - PlayoutEngine: 13 abstract methods (transport, queue, state, callbacks,
      device selection).
    - Supporting types: PlayoutState (4 values), QueueItem, TrackChangedEvent,
      PlayoutError.
    - conftest.py at repo root for pytest sys.path setup.
    - tests/unit/playout/test_engine_interface.py: 10 tests, all passing.
    - No behaviour change — interface only, no implementation.

0.1.5 (2026-04-24)
    - Task T1.2 complete: LINUX_INVENTORY.md classified by primary category.
    - Added "Classification Summary by Primary Category" table at top.
    - Five T1.2 categories: runtime-binding (~28 files), domain (~28),
      deployment (~8), audio (3), legacy-ui (~5). Total: ~55 files.
    - Confirmed clear: nginx (0), multiprocessing (false alarm), SIGHUP (0).
    - Pattern-based summary table updated with primary category column.

0.1.4 (2026-04-24)
    - Task T1.1 complete: docs/architecture/LINUX_INVENTORY.md created.
    - Scanned backend/ and frontend/ for 10 pattern categories.
    - 327 Liquidsoap hits (32 files), 569 Celery hits (18 files),
      16 systemctl hits (2 files), 20 Linux path hits (8 files),
      11 ALSA/PortAudio hits (3 files), 6 chmod/chown hits (4 files).
    - nginx: 0 hits in application code (clear).
    - multiprocessing in pipeline.py: false alarm (docstring only).
    - Priority remediation order documented (§11).

0.1.3 (2026-04-24)
    - Task T0.4 complete: docs/architecture/BASELINE_MODULES.md created.
    - Inventoried 6 Python packages, 1 PHP frontend, 3 infra reference areas.
    - Per-module: disposition + blocking concerns + key Linux assumptions.
    - Section 6: 13 new modules required for RASTATIME (not in LibreTime).
    - Key finding: backend/playout/liquidsoap/ is full replace; worker is
      full replace; analyzer/_liquidsoap.py needs targeted replacement.

0.1.2 (2026-04-24)
    - Task T0.3 complete: docs/architecture/RATIONALE.md created.
    - Documents six incompatibility root causes: Liquidsoap, systemd,
      Celery prefork, Gunicorn, Linux paths, ALSA/PortAudio.
    - Clarifies functional fork vs. literal port distinction.
    - Summarizes what is preserved and what is replaced.

0.1.1 (2026-04-24)
    - Task T0.2 complete: 5 Architecture Decision Records created.
    - ADR-001: Windows 11 as primary runtime target.
    - ADR-002: libVLC as mandatory main playout engine.
    - ADR-003: Icecast as optional auxiliary stream layer.
    - ADR-004: English as canonical system language; German UI-only.
    - ADR-005: NSSM as phase 1 Windows service strategy.
    - .gitkeep removed from docs/architecture/decisions/ (now has real files).

0.1.0 (2026-04-24)
    - Task T0.1 complete: LibreTime 4.5.0 baseline imported.
    - git init; .gitattributes for Windows line endings.
    - backend/: api, api-client, analyzer, playout, shared, worker.
    - frontend/legacy/: PHP/JS UI layer.
    - infra/upstream/: Linux/Docker reference files (not for production).
    - docs/upstream/: LibreTime docs reference.
    - LICENSE: AGPL-3.0 at repository root.
    - FORK_NOTES.md: upstream tag, rationale, import mapping.
    - docs/architecture/: folder skeleton with decisions/, diagrams/.
    - docs/dev/, docs/operator/: placeholder folders.
    - playout/, audio/, streams/, tests/: empty placeholder folders.
    - BLOCKERS_T0.1.md resolved (remains in repo as record).

0.0.3 (2026-04-24)
    - Created BLOCKERS_T0.1.md: blocker report for T0.1.
    - Documents three blockers: git init, version selection, import strategy.
    - Recommends LibreTime v4.2.0 + Option A (clone-then-copy).
    - No source code changes.

0.0.2 (2026-04-24)
    - Added IMPLEMENTATION_PLAN.md (derived from AGENTS.md +
      RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).
    - No source code changes.

0.0.1 (2026-04-23)
    - Initial project docs: AGENTS.md,
      RASTATIME_ARCHITECTURE_DRAFT_v0.1.md.
