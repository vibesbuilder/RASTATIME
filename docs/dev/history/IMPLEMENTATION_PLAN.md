# RASTATIME — Implementation Plan
**Derived from:** `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md`, `AGENTS.md`
**Plan version:** 0.1
**Status:** pre-coding execution plan. No source has been forked yet.

---

## 1. Subsystem, Dependency, and Replacement Inventory

### 1.1 Major Subsystems (target state)

| # | Subsystem | Role | Origin |
|---|---|---|---|
| S1 | Application core (API + domain) | Shows, schedule, playlists, media, history, users, webstreams, podcasts | Preserved from LibreTime (refactored) |
| S2 | Web UI | Operator-facing frontend (EN default, DE translation) | Preserved from LibreTime (refactored) |
| S3 | Playout core | Authoritative on-air engine | **Replaced** — libVLC-based |
| S4 | Queue manager | Show queue + fallback orchestration | New module on top of S3 |
| S5 | Stream egress | Outgoing public streams | **Replaced** — libVLC-first, Icecast optional |
| S6 | Stream ingress | Incoming remote live streams | **Replaced** — libVLC-first, Icecast optional |
| S7 | Soundcard abstraction | Local audio device enum + mapping | **New** |
| S8 | Line-In subsystem | Local hardware contribution inputs | **New** |
| S9 | Background runner | Async jobs (import, podcasts, media scan, cleanup) | **Replaced** — Celery → Windows-native runner |
| S10 | Database | Persistent store | **Preserved** — PostgreSQL |
| S11 | Broker (optional) | Async broker | **Conditional** — RabbitMQ kept only if still beneficial |
| S12 | Service lifecycle | Auto-start, recovery | **Replaced** — NSSM + Windows services |
| S13 | Installer/bootstrap | Host setup | **Replaced** — PowerShell bootstrap + (later) MSI-like installer |
| S14 | Auxiliary stream server | Icecast | **Optional supporting component** |

### 1.2 Runtime Assumptions (target)

- OS: Windows 11.
- Python runtime on Windows (version to be pinned in ADR; LibreTime currently tracks modern CPython).
- Database: PostgreSQL on Windows (Windows installer, service-managed).
- libVLC: installed as a native Windows DLL set; Python binding via `python-vlc`.
- Services start via NSSM at boot; no `systemd`, `systemctl`, `nginx`, `gunicorn`.
- English canonical, German translation layer only.
- Paths: Windows-native, never `/etc`, `/var`, `/srv`.

### 1.3 Replacement Decisions (summary)

| Current (LibreTime) | RASTATIME decision |
|---|---|
| Liquidsoap | **Replace** with libVLC adapter (`S3`) |
| Celery | **Replace** with Windows-native runner (`S9`); broker optional |
| Gunicorn | **Replace** with Windows-appropriate WSGI/ASGI server (e.g. Waitress, Hypercorn) |
| nginx | **Replace/remove**; optionally reverse-proxy only if required |
| systemd units | **Replace** with NSSM-managed services |
| ALSA/PortAudio assumptions | **Replace** with Windows audio API path (WASAPI/DirectSound via libVLC) |
| Linux installer scripts | **Replace** with PowerShell bootstrap + service install scripts |
| Linux paths in config | **Abstract** via `paths.py`/config keys |

### 1.4 Linux-Specific Assumptions To Remove or Abstract

- `systemctl` / `systemd` service calls.
- Hardcoded paths: `/etc/airtime`, `/var/log/airtime`, `/srv/airtime`, `/usr/share/airtime`.
- Shell scripts (`*.sh`) used as runtime mechanism (keep only as reference).
- Liquidsoap process spawning, Liquidsoap config generation, Liquidsoap `.liq` templates.
- PortAudio/ALSA device enumeration code.
- `pg_hba.conf` / Linux-specific PostgreSQL setup instructions.
- `nginx.conf` / `gunicorn.service` references in install docs.
- File permission logic relying on POSIX (`chmod`, `chown`).
- Use of `fork()`-semantics assumptions in worker code.
- Signal handling that relies on UNIX signals not present on Windows (`SIGHUP` etc.).

### 1.5 Where Direct Port Is Unrealistic — Reimplementation Required

- **Playout engine**: Liquidsoap → libVLC. Semantics, events, queue model, fades differ. Reimplement, don't port.
- **Worker execution**: Celery with fork-based prefork pool is unreliable on Windows. Reimplement as service-hosted job runner (APScheduler-based or custom loop); broker optional.
- **Audio I/O**: Linux audio stack → Windows soundcard abstraction around libVLC's audio output modules. New module.
- **Line-In subsystem**: absent in LibreTime. New domain + UI + runtime.
- **Installer/service lifecycle**: Linux package install → NSSM-based scripted install. New.
- **Soundcard menu & settings**: new UI surface and new persistence.
- **Icecast integration**: keep Icecast-as-server if used, but the glue code for ingress/egress is new because it replaces Liquidsoap's role as the encoder/connector.

---

## 2. Conceptual Classification

### 2.1 Conceptually Preserved From LibreTime
- Show model, scheduling semantics, calendar behavior.
- Playlist, smartblock, media library concepts.
- Webstream concept (URL-based remote source).
- Podcast ingestion model.
- Playout history and reporting.
- User/auth concepts (review later for Windows-friendly auth).
- Route/URL shapes, API response shapes (where practical).

### 2.2 Windows-Specific Replacements
- Playout runtime (libVLC).
- Worker runtime (Windows-native runner).
- Web serving (Waitress/Hypercorn or similar).
- Service lifecycle (NSSM).
- Installer / bootstrap (PowerShell).
- File paths / config locations.
- Audio backend (WASAPI via libVLC).

### 2.3 New RASTATIME-Specific Features
- Line-In menu + domain entity + runtime routing (F-LINEIN).
- Settings → Soundcard submenu + device mapping persistence (F-SOUNDCARD).
- Stable internal device ID abstraction (F-DEVICE-ID).
- Windows service install/uninstall scripts with NSSM (F-NSSM).
- PowerShell dev bootstrap (F-BOOTSTRAP).
- FORK_NOTES.md, ADRs, Windows-specific operator docs.

---

## 3. Suggested Repository Structure

```
RASTATIME/
├── AGENTS.md
├── README.md
├── readme.txt                       # changelog per AGENTS.md rule
├── IMPLEMENTATION_PLAN.md
├── FORK_NOTES.md                    # created in Phase 0
├── RASTATIME_ARCHITECTURE_DRAFT_v0.1.md
├── docs/
│   ├── architecture/
│   │   ├── decisions/               # ADR-001..ADR-005 (and onward)
│   │   └── diagrams/
│   ├── operator/                    # install, upgrade, recovery guides
│   └── dev/                         # dev setup, debugging
├── backend/
│   ├── rastatime_api/               # Django/Python app layer (fork of LibreTime api)
│   ├── rastatime_domain/            # show, schedule, media, history
│   ├── rastatime_worker/            # Windows-native background runner
│   └── rastatime_common/            # config, paths, logging, i18n
├── frontend/
│   ├── app/                         # LibreTime-derived UI (refactored)
│   └── locales/                     # en, de
├── playout/
│   ├── engine_interface/            # abstract playout contract
│   ├── engine_mock/                 # null/mock engine
│   ├── engine_libvlc/               # libVLC adapter
│   └── queue_manager/
├── audio/
│   ├── soundcard/                   # device enum + mapping
│   └── linein/                      # local line-in runtime
├── streams/
│   ├── egress/                      # libVLC + optional Icecast
│   └── ingress/                     # libVLC + optional Icecast
├── infra/
│   ├── nssm/                        # service install/remove/status scripts
│   ├── scripts/
│   │   └── dev/                     # bootstrap.ps1, run-api.ps1, run-worker.ps1
│   └── config/                      # sample configs, templates
└── tests/
    ├── unit/
    ├── integration/
    └── smoke/
```

Notes:
- LibreTime upstream lives inside `backend/` / `frontend/` subfolders — fork import lands there.
- `playout/`, `audio/`, `streams/` are first-class siblings because they are the largest replacement zones.
- `infra/` collects all Windows-specific tooling; easy to audit and strip out of Linux-ish concerns.

---

## 4. Phase and Milestone Plan

Milestone order follows the architecture draft §20. Tasks are atomic and assistant-sized. Each task includes: **O** objective, **F** affected files/modules, **P** prerequisites, **X** expected output, **R** risks/open questions, **V** validation.

---

### Phase 0 — Project Preparation

**Milestone M0 — Fork baseline + ADRs**

**T0.1 — Import LibreTime baseline.**
- O: bring LibreTime source into repo at a tagged upstream version.
- F: new `backend/`, `frontend/` trees; `FORK_NOTES.md`.
- P: none.
- X: reproducible baseline commit, FORK_NOTES with upstream tag + rationale.
- R: upstream license compliance; pick tag vs. main HEAD; size of import.
- V: repo builds index, `readme.txt` v0.0.1 created with changelog entry.

**T0.2 — Create ADR folder and initial ADRs.**
- O: lock architectural direction in writing.
- F: `docs/architecture/decisions/ADR-001..ADR-005.md`.
- P: T0.1.
- X: ADR-001 Windows-first; ADR-002 libVLC main; ADR-003 Icecast auxiliary; ADR-004 English-first; ADR-005 NSSM first.
- R: none.
- V: peer review of ADRs against architecture draft §21.

**T0.3 — Create RATIONALE.md.**
- O: explain why the fork is not a Linux port.
- F: `docs/architecture/RATIONALE.md`.
- P: T0.2.
- X: short doc summarizing draft §3.
- V: doc reviewed.

**T0.4 — Baseline module inventory.**
- O: write down which LibreTime modules exist at baseline (api, worker, playout, analyzer, legacy, stream tooling).
- F: `docs/architecture/BASELINE_MODULES.md`.
- P: T0.1.
- X: tabular map of upstream modules → RASTATIME target disposition (keep / refactor / replace / delete).
- V: reviewed against `backend/` tree.

---

### Phase 1 — Inventory and Isolation

**Milestone M1 — Linux dependency inventory**

**T1.1 — Scan for Linux coupling.**
- O: produce a searchable inventory of Linux assumptions.
- F: `docs/architecture/LINUX_INVENTORY.md`.
- P: T0.1.
- X: matrix (file, pattern hit, category, disposition) covering: `systemctl`, `/etc/`, `/var/`, `/srv/`, `nginx`, `gunicorn`, `celery`, `liquidsoap`, `alsa`, `portaudio`, `.sh` runtime scripts, POSIX signals, `fork`.
- R: matrix may be large; keep it concise but actionable.
- V: every hit has a disposition label.

**T1.2 — Classify hits.**
- O: label each hit as domain / runtime binding / deployment / audio / legacy UI.
- F: same file.
- P: T1.1.
- X: labels present; summary statistics at top of file.
- V: sanity check spot-sampling.

**Milestone M2 — Runtime interfaces (no behavior change)**

**T2.1 — Define playout engine interface.**
- O: introduce `PlayoutEngine` abstract contract.
- F: `playout/engine_interface/`.
- P: M1.
- X: `PlayoutEngine` ABC with: start, stop, pause, load_queue, append, clear_queue, get_state, get_current_item, get_remaining_duration, on_track_change, on_error, select_output_device.
- R: naming stability; keep interface minimal.
- V: unit test that a NotImplemented subclass raises cleanly.

**T2.2 — Define stream ingress/egress interfaces.**
- O: abstract stream ingress and egress.
- F: `streams/egress/interface.py`, `streams/ingress/interface.py`.
- P: T2.1.
- X: contracts for outgoing stream lifecycle + incoming stream registration.
- V: static type check passes.

**T2.3 — Define audio device manager interface.**
- O: abstract device discovery + selection.
- F: `audio/soundcard/interface.py`.
- P: T2.1.
- X: `AudioDeviceManager` ABC: list_outputs, list_inputs, resolve_stable_id, open_output, open_input.
- V: type check.

**T2.4 — Define background runner interface.**
- O: abstract task execution.
- F: `backend/rastatime_worker/interface.py`.
- P: none.
- X: `JobRunner` ABC: register, submit, schedule, status, cancel.
- V: type check.

**T2.5 — Define service lifecycle/health interface.**
- O: abstract service health reporting.
- F: `infra/service_health/interface.py`.
- P: none.
- X: `ServiceHealth` ABC + JSON shape spec.
- V: schema test.

---

### Phase 2 — Windows Development Bootstrap

**Milestone M3 — Windows dev bootstrap**

**T3.1 — PowerShell bootstrap skeleton.**
- O: one-shot dev environment preparation.
- F: `infra/scripts/dev/bootstrap.ps1`.
- P: none.
- X: checks Python version, PostgreSQL presence, libVLC/VLC presence, (optional) RabbitMQ; prints readable errors.
- R: PowerShell execution policy on contributor machines; document unblock steps.
- V: run on clean Windows 11 VM with and without dependencies.

**T3.2 — API run script.**
- O: start API in dev mode under Windows.
- F: `infra/scripts/dev/run-api.ps1`.
- P: T3.1.
- X: launches app server (initially Django dev server); prints health URL.
- V: dev server responds to `/health`.

**T3.3 — Worker run script.**
- O: start background runner (mocked) in dev.
- F: `infra/scripts/dev/run-worker.ps1`.
- P: T3.1, T2.4.
- X: worker process starts; logs to console.
- V: worker logs "idle" within 2s.

**T3.4 — `WINDOWS_DEV_STATUS.md`.**
- O: document current dev blockers.
- F: `docs/dev/WINDOWS_DEV_STATUS.md`.
- P: T3.1–T3.3.
- X: honest list of what works, what is stubbed.
- V: reviewed.

**T3.5 — Stub unsupported runtime modules.**
- O: disable Liquidsoap/Celery/nginx/gunicorn code paths cleanly.
- F: whichever LibreTime modules import these.
- P: M1 inventory.
- X: import-time failures gone; feature flags default to "disabled on Windows".
- R: don't delete yet — only disable.
- V: `run-api.ps1` boots without import errors.

---

### Phase 3 — Playout Abstraction

**Milestone M4 — Mock playout engine**

**T4.1 — Implement MockPlayoutEngine.**
- O: satisfy `PlayoutEngine` contract with no audio.
- F: `playout/engine_mock/`.
- P: T2.1.
- X: simulates state, current item, queue advance on a timer; emits track change events.
- V: unit test asserts state transitions on a 3-item queue.

**T4.2 — Config flag to select engine.**
- O: engine selection via config.
- F: `backend/rastatime_common/config.py`.
- P: T4.1.
- X: `PLAYOUT_ENGINE = "mock" | "libvlc"`.
- V: integration test switches engines and instantiates both.

**T4.3 — Wire mock engine to scheduler entry point.**
- O: scheduler invokes playout through interface.
- F: LibreTime scheduler module (refactor).
- P: T4.2.
- X: scheduled show triggers engine.start with the correct queue.
- V: schedule a 10s show in a test, assert engine received start/stop.

---

### Phase 4 — libVLC Core Integration

**Milestone M5 — libVLC basic playback**

**T5.1 — Add `python-vlc` dependency and runtime probe.**
- O: confirm libVLC DLLs discoverable.
- F: `backend/requirements.txt` (or `pyproject.toml`), `playout/engine_libvlc/probe.py`.
- P: T3.1.
- X: probe script prints libVLC version; docs list supported VLC versions.
- R: DLL bitness mismatch; 32-bit Python + 64-bit VLC.
- V: probe works on a fresh Windows 11 machine.

**T5.2 — Implement `LibVlcPlayoutEngine` — file playback.**
- O: first real playout capability.
- F: `playout/engine_libvlc/engine.py`.
- P: T5.1, T2.1.
- X: can play a local file and report state.
- V: unit/integration test plays a short WAV and asserts end-of-track callback.

**T5.3 — Add queue playback.**
- O: support sequenced items.
- F: same module.
- P: T5.2.
- X: load_queue, append, clear_queue work; gap handling documented.
- V: 3-item queue plays in order; track change events fire.

**T5.4 — Pause/stop/resume.**
- O: transport controls.
- F: same module.
- P: T5.3.
- X: full transport control with correct state.
- V: integration test toggles states.

**Milestone M6 — Scheduler → libVLC**

**T6.1 — Map scheduler actions to engine.**
- O: soft start, hard start, stop current, load next queue.
- F: scheduler module, `playout/engine_libvlc/`.
- P: T5.3, T4.3.
- X: scheduler triggers real playback.
- V: 30s smoke run: schedule two shows back-to-back, observe both play.

**T6.2 — Fallback playout entry.**
- O: ensure fallback content plays when scheduled content ends.
- F: scheduler + queue manager (stub).
- P: T6.1.
- X: after scheduled show ends, fallback track plays.
- V: smoke run observes fallback start.

**Milestone M7 — Track callbacks / now-playing**

**T7.1 — Subscribe to libVLC events.**
- O: normalize track change payload.
- F: `playout/engine_libvlc/events.py`.
- P: T5.3.
- X: normalized `TrackChangedEvent` (engine-agnostic).
- V: unit test with mock libVLC event stream.

**T7.2 — Feed now-playing and history.**
- O: connect events to existing LibreTime now-playing + history sinks.
- F: API now-playing endpoint, history logger.
- P: T7.1.
- X: now-playing reflects real playback; history records entries.
- V: 1-minute smoke; assert at least one history row per track.

---

### Phase 5 — Default Rotation and Queue Semantics

**Milestone M8 — Queue manager + fallback**

**T8.1 — Write `QUEUE_BEHAVIOR.md`.**
- O: document queue priority, show-queue vs. fallback, switching rules.
- F: `docs/architecture/QUEUE_BEHAVIOR.md`.
- P: review LibreTime docs.
- X: written behavior contract.
- R: LibreTime behavior may be under-documented — flag assumptions explicitly.
- V: reviewed.

**T8.2 — Implement QueueManager module.**
- O: centralize queue decisions outside the engine adapter.
- F: `playout/queue_manager/`.
- P: T8.1.
- X: active-show queue, fallback queue, refill checks, show-end transitions.
- V: unit tests for: empty queue → fallback, show end mid-track, show overlap edge cases.

**T8.3 — Wire QueueManager between scheduler and engine.**
- O: scheduler talks to QueueManager; QueueManager talks to engine.
- F: scheduler, engine adapter.
- P: T8.2.
- X: engine no longer holds scheduling intelligence.
- V: smoke run with back-to-back shows and a gap → fallback plays in the gap.

---

### Phase 6 — Streaming Architecture

**Milestone M9 — Stream capability matrix**

**T9.1 — Enumerate stream use cases.**
- O: list outgoing public, multi-output, incoming contribution, metadata, reconnect.
- F: `docs/architecture/STREAM_MATRIX.md`.
- P: none.
- X: 1 row per use case with current LibreTime approach.
- V: reviewed.

**T9.2 — Test each use case against libVLC.**
- O: classify libVLC-direct vs. Icecast-needed vs. custom bridge.
- F: same file, + `streams/spikes/` small spike scripts.
- P: T9.1, T5.1.
- X: annotated matrix with empirical notes.
- R: spike results may invalidate assumptions — allow feedback into ADR revision.
- V: spike scripts reproducible.

**Milestone M10 — Outgoing stream implementation**

**T10.1 — Stream output model.**
- O: persistent entity for a stream output.
- F: domain model, migration.
- P: T9.2.
- X: table with name, protocol, url, credentials, bitrate, codec, enabled.
- V: migration up/down tested.

**T10.2 — Implement first outgoing path (libVLC).**
- O: prove a single Icecast/Shoutcast sink via libVLC sout.
- F: `streams/egress/libvlc_sink.py`.
- P: T10.1, T5.2.
- X: one working outgoing stream.
- V: listener can connect; metadata updates on track change.

**T10.3 — Expose output status in API.**
- O: operator visibility.
- F: API endpoint, UI widget.
- P: T10.2.
- X: `/streams/outputs` returns live status per sink.
- V: integration test.

**T10.4 — (Conditional) Icecast-backed output.**
- O: add Icecast option if T9.2 showed libVLC insufficient for a use case.
- F: `streams/egress/icecast_sink.py`.
- P: T9.2 decision, T10.3.
- X: Icecast server (installed separately) used as sink.
- R: Icecast process lifecycle on Windows (NSSM).
- V: two independent listeners connect.

**Milestone M11 — Incoming remote streams**

**T11.1 — Input source model.**
- O: persistent entity for a remote input.
- F: domain model, migration.
- P: T10.1.
- X: table with name, protocol, url/mount, credentials, priority.
- V: migration tested.

**T11.2 — Implement first ingress path.**
- O: one working remote input.
- F: `streams/ingress/libvlc_source.py` (and/or `icecast_source.py`).
- P: T11.1.
- X: show switches to remote input at scheduled time.
- V: smoke with a test stream.

---

### Phase 7 — Soundcard and Line-In

**Milestone M12 — Device enumeration**

**T12.1 — Implement WindowsAudioDeviceManager.**
- O: enumerate Windows audio devices with stable IDs.
- F: `audio/soundcard/windows_manager.py`.
- P: T2.3.
- X: list_outputs, list_inputs with stable internal IDs (e.g. hash of endpoint ID).
- R: libVLC's audio module enumeration vs. Windows Core Audio — pick one source of truth; document.
- V: unit test on real hardware: device list non-empty; ID stable across reboots.

**T12.2 — API endpoint for device list.**
- O: expose device inventory to UI.
- F: API route `/audio/devices`.
- P: T12.1.
- X: JSON with outputs, inputs, channels.
- V: integration test.

**Milestone M13 — Soundcard settings**

**T13.1 — Soundcard settings persistence.**
- O: store main output, optional preview output, configured line-ins.
- F: domain model + migration.
- P: T12.1.
- X: `soundcard_settings` table/entity.
- V: migration tested.

**T13.2 — Settings → Soundcard submenu UI.**
- O: operator hardware mapping.
- F: frontend settings area.
- P: T13.1, T12.2.
- X: submenu appears after "Streams"; fields for outputs and inputs; save/load works.
- R: existing LibreTime settings nav may differ — do not rename other entries.
- V: manual UI walkthrough; persistence confirmed.

**T13.3 — Graceful handling of missing devices at startup.**
- O: degraded-mode behavior when a saved device no longer exists.
- F: soundcard manager + startup check.
- P: T13.2.
- X: logs clear warning; marks selection as "unavailable"; system continues to boot.
- V: unplug device, reboot service, verify warning + UI indicator.

**Milestone M14 — Line-In model + UI**

**T14.1 — Line-In domain model.**
- O: represent local line inputs as entities.
- F: model + migration.
- P: T13.1.
- X: fields: id, name, device_id, channel_mapping, enabled, description, priority.
- V: migration tested.

**T14.2 — Line-In list view.**
- O: UI listing of configured line-ins.
- F: frontend Line-In menu entry.
- P: T14.1.
- X: menu entry visible; list renders saved entries.
- V: manual UI.

**T14.3 — Line-In add/edit dialog (Webstream-like).**
- O: parity with Webstream dialog structure, URL replaced by device + channel selectors.
- F: frontend dialog component.
- P: T14.2, T12.2.
- X: add, edit, delete, enable/disable.
- V: manual UI round trip.

**Milestone M15 — Local line-in runtime**

**T15.1 — Line-In runtime activation contract.**
- O: define how a line-in is activated as a source.
- F: `audio/linein/runtime.py`.
- P: T14.1, T2.3, T5.4.
- X: `activate(linein_id)`, `deactivate(linein_id)`, priority rules vs. scheduled playout.
- V: unit tests for state machine.

**T15.2 — Integrate line-in with playout source selection.**
- O: one working local line-in path.
- F: queue manager or source selector.
- P: T15.1, T8.3.
- X: activating a line-in routes audio from the Windows input through libVLC to the configured output.
- R: libVLC `dshow://` / `mmdevice://` input reliability on Windows; fall back to WASAPI module docs.
- V: manual: plug audio into line-in, activate, hear it on line-out.

---

### Phase 8 — Worker and Background Task Replacement

**Milestone M16 — Background runner**

**T16.1 — Background job inventory.**
- O: list LibreTime background jobs (media scan, podcast check, imports, schedule generation, cleanup, export).
- F: `docs/architecture/JOB_INVENTORY.md`.
- P: M1.
- X: table with job, cadence, retry needs, resource cost.
- V: reviewed.

**T16.2 — Implement Windows-compatible runner.**
- O: replace Celery.
- F: `backend/rastatime_worker/runner.py`.
- P: T2.4, T16.1.
- X: single-process service that registers, schedules, retries, logs jobs; NSSM-hosted.
- R: whether APScheduler suffices or a custom loop is needed; broker optionality.
- V: run one short job end-to-end.

**T16.3 — Port jobs one by one.**
- O: migrate each LibreTime job to the new runner.
- F: per-job modules.
- P: T16.2.
- X: each job migrated with retry/logging parity; integration test per job.
- V: per-job tests pass.

---

### Phase 9 — Web/API Runtime

**Milestone M17 — Windows-oriented serving**

**T17.1 — Replace gunicorn with Waitress (or equivalent).**
- O: Windows-viable WSGI server.
- F: entry script, docs.
- P: T3.2.
- X: API served via Waitress; health endpoint OK.
- V: load test at low concurrency.

**T17.2 — Decide on reverse proxy.**
- O: reach a minimal-proxy decision.
- F: ADR-00X (new).
- P: T17.1.
- X: either "no proxy" or documented Windows-tolerant option (e.g. IIS ARR, Caddy Windows build).
- V: ADR merged.

**T17.3 — Preserve API routes and response shapes.**
- O: stable integration surface.
- F: API routes, contract tests.
- P: T0.4.
- X: parity tests against LibreTime-documented shapes where possible.
- V: contract test suite passes.

---

### Phase 10 — Data, Metadata, History

**Milestone M18 — Schema evolution**

**T18.1 — Preserve existing schema.**
- O: minimize churn.
- F: migrations folder.
- P: T0.1.
- X: existing schema retained; no rename-for-rename-sake.
- V: DB migrates clean on a Windows PostgreSQL.

**T18.2 — Add new tables only for RASTATIME features.**
- O: line-ins, soundcard settings, Windows runtime settings.
- F: migrations.
- P: T13.1, T14.1.
- X: new tables created in English, no mixed-language fields.
- V: migrations tested up/down.

**Milestone M19 — History rebinding**

**T19.1 — Normalized playback event record.**
- O: engine-agnostic history event shape.
- F: history logger module.
- P: T7.1.
- X: event schema documented and persisted.
- V: unit test.

**T19.2 — Map libVLC + stream + line-in events to history.**
- O: restore playout history fidelity.
- F: history logger + callbacks.
- P: T19.1, T11.2, T15.2.
- X: all source types appear in history with correct metadata.
- V: integration smoke; export/reports still render.

---

### Phase 11 — Frontend Language and UX

**Milestone M20 — EN/DE baseline**

**T20.1 — Set default locale to English.**
- O: canonical UI language.
- F: `frontend/locales/`, i18n config.
- P: T0.1.
- X: English default; switcher works.
- V: manual UI.

**T20.2 — Add German translation scaffolding.**
- O: German as translation layer only.
- F: `frontend/locales/de/`.
- P: T20.1.
- X: strings externalized; `de` bundle present; critical operator flows translated.
- R: avoid German identifiers in code/DB; translation only at presentation layer.
- V: manual UI in DE.

**T20.3 — Add Line-In and Soundcard menu entries with i18n.**
- O: match architecture §4.6 menu layout.
- F: nav + locale files.
- P: T13.2, T14.2, T20.1.
- X: entries present in EN and DE; existing LibreTime entries not renamed casually.
- V: manual UI both locales.

---

### Phase 12 — Windows Service Layer

**Milestone M21 — Service topology**

**T21.1 — Service split definition.**
- O: decide processes → services.
- F: `docs/architecture/SERVICE_TOPOLOGY.md`.
- P: M7, M8, M10, M16.
- X: services list: api, worker, playout, (optional) stream gateway, (optional) broker; dependency order.
- V: reviewed.

**Milestone M22 — NSSM automation**

**T22.1 — NSSM install scripts.**
- O: repeatable service install.
- F: `infra/nssm/install-*.ps1`.
- P: T21.1.
- X: one script per service; parameterized for install path.
- V: install + `Get-Service` shows service; boots on reboot.

**T22.2 — NSSM remove scripts.**
- O: clean uninstall.
- F: `infra/nssm/remove-*.ps1`.
- P: T22.1.
- X: services and registry entries removed cleanly.
- V: install → remove → no residue.

**T22.3 — Status and health helper scripts.**
- O: operator diagnostics.
- F: `infra/nssm/status.ps1`.
- P: T22.1.
- X: prints each service state + latest health JSON.
- V: manual run.

**T22.4 — Restart order and dependency docs.**
- O: crash recovery clarity.
- F: `docs/operator/RESTART_ORDER.md`.
- P: T21.1.
- X: documented sequence: DB → (broker) → worker → playout → api → streams.
- V: reviewed.

**Milestone M23 — Operator docs**

**T23.1 — Install guide.**
- O: first-install on Windows 11.
- F: `docs/operator/INSTALL.md`.
- P: T22.1.
- X: step-by-step with dependency list.
- V: fresh Windows install reproduces.

**T23.2 — Upgrade, backup, crash-recovery guides.**
- O: operational continuity.
- F: `docs/operator/UPGRADE.md`, `BACKUP.md`, `RECOVERY.md`.
- P: T22.4.
- X: short, actionable.
- V: reviewed.

**T23.3 — Device-missing + line-in-broken runbooks.**
- O: common support scenarios.
- F: `docs/operator/RUNBOOK_*.md`.
- P: T13.3, T15.2.
- X: symptoms → diagnostic steps → fix.
- V: reviewed.

---

### Phase 13 — Final Hardening

**Milestone M24 — Cleanup**

**T24.1 — Delete dead Linux code.**
- O: remove Liquidsoap remnants, nginx/gunicorn configs, unused scripts.
- F: across repo.
- P: all functional replacements landed.
- X: codebase is Windows-first; no dead imports.
- R: do not over-prune — keep anything still referenced.
- V: full test matrix passes.

**T24.2 — Config defaults audit.**
- O: no Linux paths in defaults.
- F: config files, env examples.
- P: T24.1.
- X: all defaults Windows-friendly.
- V: `grep` for `/etc`, `/var`, `/srv` returns zero hits.

**Milestone M25 — Release-readiness test matrix**

**T25.1 — Execute full test matrix.**
- O: validate product behavior.
- F: `tests/`, manual runbooks.
- P: all milestones.
- X: results documented for: reboot recovery, missing device, scheduled playout, fallback, outgoing stream, incoming stream, line-in switching, history integrity, settings persistence, locale switching, service restart.
- V: checklist file in `docs/operator/RELEASE_CHECKLIST.md`.

---

## 5. Open Questions and Ambiguities

Explicit list of things the architecture draft leaves open:

- **Python version** to pin for Windows — not fixed in draft. Decide early (ADR).
- **Waitress vs. Hypercorn vs. IIS+HttpPlatformHandler** for web serving — draft says "Windows-appropriate"; pick during T17.1.
- **RabbitMQ fate** — draft says "keep if beneficial". Final decision after T16.2.
- **Icecast usage scope** — depends entirely on T9.2 spike results.
- **libVLC audio module** on Windows — WASAPI/DirectSound; confirm which is most reliable for low-latency playout and line-in capture.
- **Legacy PHP layer** — draft says "selective keep / reduce"; recent LibreTime has reduced this already. Verify at T0.4.
- **Authentication** — LibreTime default may rely on Unix-ish assumptions (sessions, cookie paths). Review in Phase 9 if issues surface.
- **Path-abstraction strategy** — central `paths.py` vs. Django settings vs. env vars. Decide in ADR during Phase 1.
- **Installer** — draft specifies PowerShell bootstrap first. MSI/packaged installer is not in Phase 1; treat as later recommendation.
- **Icecast process lifecycle** — whether RASTATIME installs/manages Icecast or assumes separate install.
- **libVLC binding** — `python-vlc` is the obvious choice; no binding decision in draft. Confirm in ADR.
- **Multi-output / preview output** — draft mentions optional preview; exact routing semantics undefined.

---

## 6. Recommended First Build Slice

**Goal:** smallest slice that produces a reproducible Windows baseline and locks in architectural direction before any real playout code lands.

**Slice contents (should be completable as a single short sprint):**

1. **T0.1** — Import LibreTime at a tagged version into `backend/` + `frontend/`.
2. **T0.2** — Write ADR-001…ADR-005.
3. **T0.3** — `RATIONALE.md`.
4. **T0.4** — `BASELINE_MODULES.md`.
5. **T1.1 + T1.2** — Linux coupling inventory with dispositions.
6. **T3.1** — `bootstrap.ps1` that at least checks Python, PostgreSQL, libVLC.
7. **T3.4** — `WINDOWS_DEV_STATUS.md` describing what boots and what is stubbed.
8. **T2.1** — `PlayoutEngine` interface committed as code (no implementation yet).
9. **T4.1 + T4.2** — `MockPlayoutEngine` + config flag `PLAYOUT_ENGINE=mock`.
10. Update `readme.txt` to v0.1.0 with changelog entries.

**Why this slice:**
- No real audio code, so risk is minimal.
- Produces an architectural record (ADRs + inventories) that prevents drift.
- Establishes the two most important seams: Windows bootstrap and the playout interface.
- Leaves a runnable (if silent) system that future tasks can extend without changing scaffolding.
- Every step is reversible and independently reviewable.

**Explicit exit criteria for the first slice:**
- `bootstrap.ps1` runs cleanly on a fresh Windows 11 machine with dependencies installed.
- API starts in dev mode using the mock playout engine.
- ADR-001…ADR-005 merged.
- Linux inventory in repo with dispositions.
- `readme.txt` updated to v0.1.0.
