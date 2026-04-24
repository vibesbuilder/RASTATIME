# LINUX_INVENTORY — Linux Coupling in LibreTime 4.5.0 Baseline

**Date:** 2026-04-24  
**Scope:** `backend/` and `frontend/` only.  
`infra/upstream/` is already classified as "reference only / delete" and excluded here.  
**Purpose:** Every Linux-specific assumption that must be removed or abstracted before
RASTATIME runs on Windows 11.

**Categories:**
- **runtime-binding** — directly invokes a Linux-only component at runtime
- **audio** — Linux-specific audio backend assumption
- **linux-path** — hardcoded Linux filesystem path
- **posix-perm** — POSIX file permission call (chmod/chown)
- **posix-signal** — UNIX signal usage
- **deployment** — install/service lifecycle assumption
- **legacy-ui** — PHP frontend reference to Linux components
- **domain** — business logic that references a replaced component but contains no direct Linux syscall

**Dispositions:**
- **Replace** — file/block must be replaced entirely
- **Refactor** — isolate and remove the Linux assumption; keep surrounding logic
- **Delete** — dead code or no-longer-applicable check
- **Review** — works on Windows but behavior differs; needs verification

---

## Summary Statistics

| Category | Files affected | Approx. line hits |
|---|---|---|
| Liquidsoap (runtime-binding + domain) | 32 | ~327 |
| Celery (runtime-binding + legacy-ui) | 18 | ~569 |
| systemctl / systemd (legacy-ui + deployment) | 2 | 16 |
| Linux paths (linux-path) | 8 | 20 |
| ALSA / PortAudio (audio) | 3 | 11 |
| Gunicorn (runtime-binding) | 3 | 3 |
| chmod / chown (posix-perm) | 4 | 6 |
| POSIX signals (posix-signal) | 2 | 4 |
| Shell scripts (deployment) | 4 | — |
| **nginx** | **0** | **0** — no hits in application code |
| **multiprocessing** | **0 (false alarm)** | docstring only; code uses `queue.Queue` |

---

## 1. Liquidsoap

### 1.1 Playout core — entire subtree

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/playout/libretime_playout/liquidsoap/main.py` | runtime-binding | **Replace** | Liquidsoap process entry; also hardcodes `/usr/bin/liquidsoap` |
| `backend/playout/libretime_playout/liquidsoap/entrypoint.py` | runtime-binding | **Replace** | Generates `.liq` script via Jinja2 |
| `backend/playout/libretime_playout/liquidsoap/models.py` | domain | **Replace** | Stream preferences model shaped for Liquidsoap; keep field semantics as reference |
| `backend/playout/libretime_playout/liquidsoap/utils.py` | runtime-binding | **Replace** | Liquidsoap utility helpers |
| `backend/playout/libretime_playout/liquidsoap/version.py` | runtime-binding | **Replace** | Reads Liquidsoap version |
| `backend/playout/libretime_playout/liquidsoap/client/_client.py` | runtime-binding | **Replace** | Telnet client to Liquidsoap — replaced by libVLC Python API |
| `backend/playout/libretime_playout/liquidsoap/client/_connection.py` | runtime-binding | **Replace** | Telnet connection — replaced |
| `backend/playout/libretime_playout/liquidsoap/templates/entrypoint.liq.j2` | runtime-binding | **Replace** | `.liq` script template — entire concept replaced |
| `backend/playout/libretime_playout/liquidsoap/templates/outputs.liq.j2` | runtime-binding | **Replace** | `.liq` stream output template — replaced |
| `backend/playout/libretime_playout/player/liquidsoap.py` | runtime-binding | **Replace** | Sends queue/playback commands to Liquidsoap via telnet |
| `backend/playout/libretime_playout/player/queue.py` | domain | **Replace** | Queue logic tightly coupled to Liquidsoap commands |
| `backend/playout/libretime_playout/player/schedule.py` | domain | **Refactor** | Schedule polling logic is portable; Liquidsoap dispatch calls replaced |
| `backend/playout/libretime_playout/player/events.py` | domain | **Refactor** | Event definitions are conceptually portable; normalize to new event model |
| `backend/playout/libretime_playout/player/fetch.py` | domain | **Refactor** | API fetch logic is engine-agnostic; keep, strip Liquidsoap references |
| `backend/playout/libretime_playout/player/push.py` | domain | **Refactor** | Now-playing push is engine-agnostic; rebind to libVLC callbacks |
| `backend/playout/libretime_playout/config.py` | runtime-binding | **Replace** | Config references Liquidsoap paths and settings |
| `backend/playout/libretime_playout/main.py` | runtime-binding | **Replace** | Entry point spawns Liquidsoap |
| `backend/playout/libretime_playout/message_handler.py` | domain | **Refactor** | RabbitMQ handler logic is portable; strip Liquidsoap-specific dispatch |
| `backend/playout/libretime_playout/notify/main.py` | domain | **Refactor** | Notification logic portable; rebind to libVLC events |
| `backend/playout/tests/liquidsoap/` | runtime-binding | **Replace** | All Liquidsoap-specific tests; replaced by libVLC adapter tests |
| `backend/playout/tests/player/liquidsoap_test.py` | runtime-binding | **Replace** | Tests for Liquidsoap player bridge |
| `backend/playout/setup.py` | runtime-binding | **Refactor** | Remove Liquidsoap from dependencies |

### 1.2 Analyzer — Liquidsoap playability probe

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/analyzer/libretime_analyzer/pipeline/_liquidsoap.py` | runtime-binding | **Replace** | Calls Liquidsoap subprocess to test if a file is playable. Replace with ffmpeg probe or libVLC open-check |
| `backend/analyzer/libretime_analyzer/pipeline/analyze_playability.py` | domain | **Refactor** | Calls `_liquidsoap.py`; keep structure, swap backend |
| `backend/analyzer/libretime_analyzer/pipeline/analyze_playability_test.py` | domain | **Refactor** | Update tests for new probe backend |
| `backend/analyzer/packages.ini` | deployment | **Refactor** | Lists Liquidsoap as a required package; remove |

### 1.3 Shared config — Liquidsoap Harbor

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/shared/libretime_shared/config/_models.py` (`HarborInput`) | runtime-binding | **Replace** | Liquidsoap Harbor is the live-input concept; replaced by Line-In subsystem (T14.1) |

### 1.4 API — historical migrations

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/api/libretime_api/legacy/migrations/0038_remove_stream_settings_liquidsoap_status.py` | domain | **Keep** | Historical migration; run-once schema change, harmless to keep |
| `backend/api/libretime_api/legacy/migrations/0039_remove_stream_settings_stats_status.py` | domain | **Keep** | Same |

### 1.5 Frontend — Liquidsoap service checks

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `frontend/legacy/application/check.php` | legacy-ui | **Replace** | Checks `liquidsoap` service via `systemctl is-active` |
| `frontend/legacy/application/configs/config-check.php` | legacy-ui | **Replace** | Shows systemd/Liquidsoap status in UI |
| `frontend/legacy/application/models/Systemstatus.php` | legacy-ui | **Refactor** | Returns service status; replace Linux health checks with Windows NSSM checks |
| `frontend/legacy/application/forms/StreamSettingSubForm.php` | domain | **Refactor** | Stream settings form; remove Liquidsoap-specific fields |
| `frontend/legacy/application/controllers/PreferenceController.php` | domain | **Refactor** | Preferences controller references Liquidsoap stream settings |
| `frontend/legacy/application/models/StreamSetting.php` | domain | **Refactor** | Stream setting model; update for libVLC-based stream config |
| `frontend/legacy/application/models/Preference.php` | domain | **Refactor** | Preference model stores Liquidsoap-related stream prefs |
| `frontend/legacy/application/services/HistoryService.php` | domain | **Refactor** | History service references Liquidsoap session data; rebind to libVLC events |

---

## 2. Celery

### 2.1 Worker package — full replacement

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/worker/libretime_worker/tasks.py` | runtime-binding | **Replace** | Full Celery worker; task business logic is portable, Celery runtime is not |
| `backend/worker/libretime_worker/config.py` | runtime-binding | **Replace** | Celery broker URL, task routing config |
| `backend/worker/libretime_worker/main.py` | runtime-binding | **Replace** | Celery entry point (`celery -A ... worker`) |
| `backend/worker/setup.py` | runtime-binding | **Refactor** | Remove `celery` from install dependencies |

### 2.2 API — worker model

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/api/libretime_api/core/models/worker.py` | domain | **Refactor** | Worker status model; adapt to new runner's status reporting |
| `backend/api/libretime_api/core/serializers/worker.py` | domain | **Refactor** | Worker serializer; keep API shape stable |
| `backend/api/libretime_api/core/views/worker.py` | domain | **Refactor** | Worker status endpoint; rebind to Windows runner status |

### 2.3 Frontend — Celery task management

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `frontend/legacy/application/common/CeleryManager.php` | runtime-binding | **Replace** | PHP wrapper that dispatches Celery tasks; replace with HTTP call to new runner API |
| `frontend/legacy/application/common/TaskManager.php` | domain | **Refactor** | Task scheduling logic; adapt for new runner |
| `frontend/legacy/application/common/PodcastManager.php` | domain | **Refactor** | Uses Celery for podcast tasks; rebind |
| `frontend/legacy/application/models/airtime/CeleryTasks.php` | domain | **Refactor** | DB model for task tracking; keep schema, remove Celery-specific fields if any |
| `frontend/legacy/application/models/airtime/CeleryTasksPeer.php` | domain | **Refactor** | Propel ORM peer; keep |
| `frontend/legacy/application/models/airtime/CeleryTasksQuery.php` | domain | **Refactor** | Query object; keep |
| `frontend/legacy/application/models/airtime/map/CeleryTasksTableMap.php` | domain | **Refactor** | ORM mapping; keep schema |
| `frontend/legacy/application/services/CeleryServiceFactory.php` | runtime-binding | **Replace** | Creates Celery service instances; replace with Windows runner service |
| `frontend/legacy/application/services/ThirdPartyCeleryService.php` | runtime-binding | **Replace** | Third-party Celery service; replace dispatch layer |
| `frontend/legacy/application/services/ThirdPartyService.php` | domain | **Refactor** | Base third-party service; remove Celery dispatch |
| `frontend/legacy/application/services/PodcastEpisodeService.php` | domain | **Refactor** | Dispatches Celery tasks for podcast episodes; rebind |
| `frontend/legacy/application/configs/config-check.php` | legacy-ui | **Replace** | Shows Celery service health via systemctl |
| `frontend/legacy/application/check.php` | legacy-ui | **Replace** | Checks Celery via `systemctl is-active libretime-worker` |
| `frontend/legacy/application/configs/constants.php` | domain | **Refactor** | May reference Celery task constants; review |
| `frontend/legacy/application/configs/classmap-airtime-conf.php` | domain | **Refactor** | Class map; review Celery class references |
| `frontend/legacy/application/controllers/ApiController.php` | domain | **Refactor** | API controller triggers Celery tasks; rebind dispatch |

---

## 3. systemctl / systemd

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `frontend/legacy/application/check.php:52–54` | legacy-ui | **Replace** | `with_systemd()` function calls `shell_exec('which systemctl')` |
| `frontend/legacy/application/check.php:70,145,157,169,181,193` | legacy-ui | **Replace** | `exec('systemctl is-active libretime-*')` for each service |
| `frontend/legacy/application/configs/config-check.php:18–253` | legacy-ui | **Replace** | Entire service health UI assumes systemd and shows `systemctl` commands. Replace with Windows service health check (NSSM / Windows SC query) |

**Risk:** The status/health page is operator-facing. Replacing `systemctl is-active` with SC query or NSSM status call is straightforward but must surface the correct service names.

---

## 4. Linux Filesystem Paths

| File / Path | Line | Hardcoded path | Category | Disposition |
|---|---|---|---|---|
| `backend/shared/libretime_shared/config/_base.py` | 15 | `/etc/libretime/config.yml` | linux-path | **Refactor** — make Windows path the default; use env var override |
| `backend/api/libretime_api/manage.py` | 10 | `/etc/libretime/config.yml` | linux-path | **Refactor** — same env var override pattern |
| `backend/playout/libretime_playout/liquidsoap/main.py` | 55 | `/usr/bin/liquidsoap` | linux-path | **Replace** — entire file replaced; note for record |
| `backend/shared/libretime_shared/config/_models.py` | 47 | `/srv/libretime` (storage default) | linux-path | **Refactor** — Windows default e.g. `C:\ProgramData\rastatime\media` |
| `frontend/legacy/application/configs/constants.php` | 19 | `/var/log/libretime` | linux-path | **Refactor** — Windows log path via env var |
| `frontend/legacy/application/configs/constants.php` | 22 | `/etc/libretime` | linux-path | **Refactor** — Windows config path via env var |
| `frontend/legacy/application/configs/conf.php` | 75 | `/srv/libretime/` (storage default) | linux-path | **Refactor** — Windows storage path via env var |
| `frontend/legacy/application/configs/airtime-conf.php` | 4 | `/var/www/html/build/runtime-conf.xml` | linux-path | **Refactor** — comment reference; update or remove |
| `frontend/legacy/application/models/Preference.php` | 754 | `/var/lib/dpkg/info/airtime.config` (Debian check) | linux-path | **Delete** — Debian-specific install detection, not applicable on Windows |

**Pattern to apply:** Replace all hardcoded Linux paths with env-var-driven config. Provide Windows-appropriate defaults (e.g. `%PROGRAMDATA%\rastatime\` or `C:\rastatime\`). Central location: `backend/shared/libretime_shared/config/_base.py`.

---

## 5. ALSA / PortAudio (Audio Backend)

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/shared/libretime_shared/config/_models.py:220` | audio | **Replace** | `SystemOutput.ALSA = "alsa"` enum value |
| `backend/shared/libretime_shared/config/_models.py:223` | audio | **Replace** | `SystemOutput.PORTAUDIO = "portaudio"` enum value |
| `backend/shared/libretime_shared/config/_models.py:231` | audio | **Replace** | `ALSASystemOutput` model class |
| `backend/shared/libretime_shared/config/_models.py:244` | audio | **Replace** | `PortAudioSystemOutput` model class |
| `backend/shared/libretime_shared/config/_models.py:255` | audio | **Replace** | Union type includes `ALSASystemOutput`, `PortAudioSystemOutput` |
| `backend/shared/tests/config/models_test.py:63` | audio | **Refactor** | Test uses `"kind": "alsa"`; update for Windows audio model |
| `backend/playout/tests/liquidsoap/fixtures/__init__.py:101,108` | audio | **Replace** | Test fixtures reference ALSA device names; part of playout replacement |

**What replaces these:** A new `WASAPI` (or `DIRECTSOUND`) enum value and a `WindowsAudioOutput` model, introduced in Phase 7 (T12.1). The `SystemOutput` enum is extended or replaced in `libretime_shared/config/_models.py`.

---

## 6. Gunicorn

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/api/requirements.txt:8` | runtime-binding | **Replace** | `gunicorn>=22.0.0,<23.1` dependency declaration; replace with Waitress |
| `backend/api/setup.py:38` | runtime-binding | **Replace** | Same gunicorn install requirement |
| `backend/api/libretime_api/gunicorn.py` | runtime-binding | **Replace** | Gunicorn config (worker count, timeout, bind). Replace with Waitress config |

---

## 7. POSIX File Permissions (chmod / chown)

| File / Path | Line | Call | Category | Disposition | Notes |
|---|---|---|---|---|---|
| `backend/playout/libretime_playout/player/file.py` | 67 | `Path.chmod(0o644)` | posix-perm | **Remove** | Part of playout file handling; no equivalent needed on Windows (NTFS ACLs differ); can be removed or wrapped in `if sys.platform != "win32"` |
| `frontend/legacy/application/models/StoredFile.php` | 927, 950 | `chmod($file, 0644)` | posix-perm | **Wrap** | PHP `chmod()` works on Windows but is a no-op on NTFS for permission bits; wrap with OS check or remove silently |
| `frontend/legacy/application/modules/rest/controllers/ShowImageController.php` | 240 | `chmod($image_file, 0644)` | posix-perm | **Wrap** | Same as above |
| `frontend/legacy/tests/application/helpers/AirtimeInstall.php` | 307–308 | `chmod()`, `chown()` | posix-perm | **Delete** | Test helper only; Windows dev setup will not use this |

---

## 8. POSIX Signals

| File / Path | Line | Signal | Category | Disposition | Notes |
|---|---|---|---|---|---|
| `backend/analyzer/libretime_analyzer/message_listener.py` | 34 | `signal.SIGTERM` | posix-signal | **Review** | `signal.SIGTERM` is available in Python on Windows. However, signal handlers must be installed from the main thread. Verify thread context at startup. Low risk. |
| `backend/playout/libretime_playout/message_handler.py` | 99 | `signal.SIGTERM` | posix-signal | **Review** | Same situation. This file is part of the playout replacement (Phase 4) so it will be rewritten anyway. |

**Note:** `signal.SIGHUP` does NOT exist on Windows. No `SIGHUP` usage found in application code — confirmed safe.

---

## 9. Shell Scripts Used as Runtime Mechanisms

| File / Path | Category | Disposition | Notes |
|---|---|---|---|
| `backend/analyzer/tools/ftp-upload-hook.sh` | deployment | **Review** | Post-processing hook called after file analysis. If this feature is used, a PowerShell equivalent is needed. Classify as optional. |
| `backend/analyzer/tools/test-hook-script.sh` | deployment | **Delete** | Dev/test script; not a production mechanism |
| `backend/analyzer/tests/fixtures/generate.sh` | deployment | **Delete** | Test fixture generator; dev-only; not called at runtime |
| `frontend/legacy/tests/runtests.sh` | deployment | **Delete** | PHP test runner; dev-only |

---

## 10. Items Confirmed Clear (No Action Required)

| Pattern | Result | Reason |
|---|---|---|
| `nginx` in application code | **0 hits** | No nginx references in `backend/` or `frontend/`; only in `infra/upstream/` (reference only) |
| `os.fork` | **0 hits** | No direct fork calls in application code |
| `multiprocessing` in pipeline.py | **False alarm** | Docstring only; actual code uses `queue.Queue` (thread-safe, Windows-compatible) |
| `signal.SIGHUP` | **0 hits** | Not used in application code |

---

## 11. Priority Order for Remediation

Based on what blocks Windows startup vs. what can be deferred:

| Priority | Item | Blocks Windows startup? | Phase |
|---|---|---|---|
| 1 | Linux config paths (`/etc/libretime`, `/srv/libretime`) | **Yes** — startup fails without config | Phase 1 / T1.2 (abstraction) |
| 2 | Gunicorn dependency | **Yes** — import fails on Windows if gunicorn is required | Phase 9 / T17.1 |
| 3 | Liquidsoap playout subtree | Yes — playout fails; stub with mock engine | Phase 3–4 |
| 4 | Celery worker | Yes — worker fails; stub with mock runner | Phase 8 |
| 5 | systemctl / service health checks | Partial — UI health page broken; API still works | Phase 12 |
| 6 | ALSA/PortAudio audio models | No — config loads but audio output fails | Phase 7 |
| 7 | chmod / chown | No — silently fails or is a no-op on Windows | Phase 7–9 |
| 8 | POSIX signals | No — SIGTERM available on Windows; low risk | Phase 4 / 8 |
| 9 | Shell scripts | No — not called at runtime | Phase 13 |
| 10 | Analyzer Liquidsoap probe | No — only triggered on file upload | Phase 4 |
