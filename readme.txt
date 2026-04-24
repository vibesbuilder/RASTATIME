RASTATIME — readme.txt
=======================

Version: 0.3.1
Date: 2026-04-25

Summary
-------
T5.3 complete: queue playback verified and gap-handling documented.
3-item queue V criterion passes; 7 new queue-specific tests added.
Total: 162/162.

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
