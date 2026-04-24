RASTATIME — readme.txt
=======================

Version: 0.2.1
Date: 2026-04-24

Summary
-------
T3.1 complete: PowerShell bootstrap checker at infra/scripts/dev/bootstrap.ps1.
Checks Python 3.11+, PostgreSQL, VLC/libVLC (required) and RabbitMQ (optional).
Prints color-coded [PASS]/[FAIL]/[SKIP] per dependency with remediation hints.
Exits 0 if all required deps found, 1 otherwise. No new unit tests (manual V).

Changelog
---------
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
