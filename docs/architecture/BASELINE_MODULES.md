# BASELINE_MODULES — LibreTime 4.5.0 Module Inventory

**Date:** 2026-04-24  
**Upstream tag:** 4.5.0 (commit f429339)  
**Purpose:** Map every LibreTime module to its RASTATIME disposition.  
**Dispositions:** Keep · Keep + Refactor · Replace · New · Reference only / Delete

---

## 1. Backend Python Packages

### 1.1 `backend/api/` — `libretime_api` (Django REST API)

**Role:** Central application server. Django project exposing a REST API for
all domain objects. Also contains the WSGI/ASGI entry points.

| Submodule | Contents | Disposition |
|---|---|---|
| `core/` | Models, serializers, views for global config and API base | **Keep + Refactor** |
| `schedule/` | Show, show instance, schedule slot models and API | **Keep** |
| `history/` | Playout history, listener stats, reporting | **Keep** |
| `storage/` | Media library, file management, upload endpoints | **Keep + Refactor** |
| `podcasts/` | Podcast ingestion, episode tracking | **Keep** |
| `legacy/` | Bridge to PHP legacy layer | **Keep short-term, reduce over time** |
| `settings/` | Stream and system settings | **Keep + Refactor** (add Soundcard settings) |
| `gunicorn.py` | Gunicorn WSGI config | **Replace** — Waitress or equivalent |
| `wsgi.py` / `asgi.py` | WSGI/ASGI entry points | **Keep** (entry point, not gunicorn-specific) |

**Key Linux assumptions to remove:**
- Gunicorn-specific worker and timeout config in `gunicorn.py`.
- Any hardcoded `/etc/libretime/` or `/var/` path defaults in `settings/`.

**RASTATIME additions required:**
- New `soundcard/` app: device selection persistence.
- New `linein/` app: line-in source entities.

---

### 1.2 `backend/api-client/` — `libretime_api_client`

**Role:** Python client library used by playout, worker, and analyzer to call
the API. Provides v1 (legacy PHP API) and v2 (Django REST API) clients.

| File | Contents | Disposition |
|---|---|---|
| `v1.py` | Legacy PHP API client | **Keep short-term** (used by worker tasks) |
| `v2.py` | Django REST API v2 client | **Keep** |
| `_client.py` | Shared HTTP client base | **Keep** |

**No platform-specific assumptions found.** Pure Python HTTP client.

---

### 1.3 `backend/analyzer/` — `libretime_analyzer`

**Role:** Media analysis pipeline. Triggered via RabbitMQ message when a file
is uploaded. Extracts metadata, cue points, replay gain, and playability info.

| Submodule | Contents | Disposition |
|---|---|---|
| `pipeline/analyze_metadata.py` | Mutagen-based tag extraction | **Keep** |
| `pipeline/analyze_cuepoint.py` | Cue point detection | **Keep** |
| `pipeline/analyze_replaygain.py` | ReplayGain via ffmpeg | **Keep** (ffmpeg available on Windows) |
| `pipeline/analyze_playability.py` | Playability check | **Keep + Refactor** |
| `pipeline/_ffmpeg.py` | ffmpeg subprocess wrapper | **Keep** (ffmpeg available on Windows) |
| `pipeline/_liquidsoap.py` | Liquidsoap-based playability probe | **Replace** — probe via ffmpeg or libVLC instead |
| `pipeline/organise_file.py` | File move/copy after analysis | **Keep + Refactor** (Windows path handling) |
| `message_listener.py` | RabbitMQ consumer entry point | **Keep + Refactor** (broker remains optional) |
| `status_reporter.py` | Reports analysis status to API | **Keep** |

**Key issue:** `_liquidsoap.py` uses a Liquidsoap subprocess call to verify
audio playability. This must be replaced with an ffmpeg probe or a libVLC
open-and-check approach.

---

### 1.4 `backend/playout/` — `libretime_playout`

**Role:** Entire Liquidsoap-based playout runtime. This is the subsystem being
fully replaced by the libVLC adapter.

| Submodule | Contents | Disposition |
|---|---|---|
| `liquidsoap/main.py` | Liquidsoap process entry point | **Replace** |
| `liquidsoap/entrypoint.py` | Generates Liquidsoap `.liq` script | **Replace** |
| `liquidsoap/models.py` | Stream preferences, info data models | **Replace** — kept as reference for stream config shape |
| `liquidsoap/templates/entrypoint.liq.j2` | Jinja2 Liquidsoap script template | **Replace** |
| `liquidsoap/templates/outputs.liq.j2` | Jinja2 stream output template | **Replace** |
| `liquidsoap/client/` | Telnet client to control Liquidsoap | **Replace** — libVLC has no telnet interface |
| `player/queue.py` | Queue management logic | **Replace** — new `playout/queue_manager/` |
| `player/schedule.py` | Schedule polling and dispatch | **Replace** — new dispatcher using libVLC engine |
| `player/events.py` | Event definitions for playout | **Keep as reference** — normalize into new event model |
| `player/fetch.py` | Fetches schedule from API | **Keep + Refactor** — schedule fetch is engine-agnostic |
| `player/push.py` | Pushes now-playing state to API | **Keep + Refactor** — rebind to libVLC callbacks |
| `player/file.py` | File path resolution for playback | **Keep + Refactor** (Windows path handling) |
| `player/liquidsoap.py` | Sends commands to Liquidsoap via telnet | **Replace** — libVLC Python API instead |
| `history/` | Playout history recording | **Keep + Refactor** — rebind to libVLC events |
| `notify/` | Notifications on track change | **Keep + Refactor** — rebind to libVLC callbacks |
| `config.py` | Playout config (includes Liquidsoap paths) | **Replace** — new config for libVLC engine |
| `message_handler.py` | RabbitMQ message handler | **Keep + Refactor** — broker remains optional |

**Summary:** The entire `liquidsoap/` subtree and `player/liquidsoap.py` are
deleted and replaced by the libVLC adapter (Phase 4). The schedule fetch,
history recording, now-playing push, and notify logic are worth preserving
conceptually but must be rebound to libVLC events.

---

### 1.5 `backend/shared/` — `libretime_shared`

**Role:** Shared utilities used by all other packages. Config parsing, logging
setup, CLI helpers, file utilities, datetime helpers.

| File | Contents | Disposition |
|---|---|---|
| `config/_base.py` | BaseConfig, default config file path | **Keep + Refactor** (Windows default path) |
| `config/_models.py` | Config data models | **Keep + Refactor** (see below) |
| `config/_fields.py` | Pydantic field types | **Keep** |
| `logging.py` | Logging setup | **Keep** |
| `cli.py` | Click CLI decorators | **Keep** |
| `datetime.py` | Datetime utilities | **Keep** |
| `files.py` | File utilities | **Keep + Refactor** (Windows path safety) |

**Config models in `_models.py` — per-model disposition:**

| Model | Disposition |
|---|---|
| `DatabaseConfig` | **Keep** |
| `GeneralConfig` | **Keep + Refactor** (default paths) |
| `StorageConfig` | **Keep + Refactor** (default paths) |
| `RabbitMQConfig` | **Keep** (broker remains optional) |
| `HarborInput` | **Replace** — Liquidsoap Harbor concept; replaced by Line-In subsystem |
| `IcecastOutput` | **Keep** (Icecast remains optional per ADR-003) |
| `ShoutcastOutput` | **Keep** (stream output type) |
| `SystemOutput` | **Keep + Refactor** (soundcard output replaces Linux system sink) |
| `StreamConfig` | **Keep + Refactor** (add Windows soundcard fields) |
| `AudioChannels` | **Keep** |
| `AudioFormat` | **Keep** |

**Key Linux assumption:** `DEFAULT_CONFIG_FILEPATH` almost certainly points to
`/etc/libretime/config.yml`. Must be changed to a Windows-appropriate path.

---

### 1.6 `backend/worker/` — `libretime_worker`

**Role:** Celery-based background worker. Handles async tasks: media imports,
podcast fetches, schedule generation, cleanup, file exports.

| File | Contents | Disposition |
|---|---|---|
| `tasks.py` | All Celery task definitions | **Replace** — tasks ported to Windows runner |
| `config.py` | Celery and broker config | **Replace** |
| `main.py` | Celery worker entry point | **Replace** |

**Celery dependencies found in `tasks.py`:** `Celery`, `celery.schedules.crontab`,
`celery.signals`, `celery.utils.log`. All must be removed.

**Tasks to port individually (T16.3):**
- Media scan / import
- Podcast episode fetch
- Schedule generation
- File cleanup
- Export / push tasks

**No platform-specific syscalls found in tasks themselves** — the Celery
runtime layer is the problem, not the task business logic.

---

## 2. Frontend

### 2.1 `frontend/legacy/` — PHP/Zend Framework UI

**Role:** The operator-facing web application. Handles all user interactions:
scheduling, library, playlists, streams, podcasts, settings, history.

| Area | Key files | Disposition |
|---|---|---|
| **Controllers** | `ScheduleController`, `LibraryController`, `PlaylistController`, `DashboardController`, `PodcastController`, `PreferenceController`, `PlayouthistoryController` | **Keep + Refactor** |
| **Models** | `Show.php`, `Schedule.php`, `Scheduler.php`, `Playlist.php`, `Block.php`, `Library.php`, `Preference.php`, `RabbitMq.php` | **Keep + Refactor** |
| **Views / Layouts** | Zend layout and view system | **Keep + Refactor** |
| **Locale** | `locale/` — existing translation strings | **Keep** (basis for EN/DE) |
| **Public assets** | `public/js/`, `public/css/` | **Keep + Refactor** |
| **Build** | `build/` — asset build tooling | **Keep + Refactor** |

**New UI surfaces required (RASTATIME additions):**
- `Line-In` menu entry and list/add/edit dialogs (T14.2–T14.3)
- `Settings → Soundcard` submenu (T13.2)

**Key assumption to check:** PHP config file references to `/etc/airtime/`,
`/var/log/`, or `/srv/` must be identified and abstracted.

---

## 3. Infrastructure Reference (not for production use)

### 3.1 `infra/upstream/installer/`

**Role:** LibreTime Linux installer. Installs systemd units, deb packages,
nginx config, PostgreSQL setup.

| Contents | Disposition |
|---|---|
| `systemd/` unit files | **Reference only** — replaced by NSSM (T22.1) |
| `nginx.conf` templates | **Reference only** — replaced by Waitress/no-proxy |
| Debian package scripts | **Reference only** — not applicable on Windows |
| PostgreSQL setup scripts | **Reference only** — Windows PostgreSQL uses its own installer |

**Action:** This entire folder is kept as a historical reference and must never
be executed on the target Windows system.

### 3.2 `infra/upstream/docker/`

**Role:** Docker Compose and container definitions for Linux-based deployment.

**Disposition: Reference only.** RASTATIME does not use Docker as its primary
deployment model. May be revisited for development tooling if beneficial.

### 3.3 `infra/upstream/Makefile`

**Role:** Linux development automation (install, test, lint targets).

**Disposition: Reference only.** PowerShell scripts replace Makefile targets
for Windows development (T3.1–T3.3).

---

## 4. Documentation Reference

### 4.1 `docs/upstream/`

**Role:** LibreTime's official documentation (imported as reference).

**Disposition: Reference only.** RASTATIME-specific documentation is written
separately under `docs/architecture/`, `docs/operator/`, `docs/dev/`.

---

## 5. Summary Table

| Module | RASTATIME path | Disposition | Blocking concern |
|---|---|---|---|
| Django API | `backend/api/` | Keep + Refactor | Gunicorn entry, Linux paths in settings |
| API client | `backend/api-client/` | Keep | None |
| Analyzer | `backend/analyzer/` | Keep + Refactor | `_liquidsoap.py` playability probe |
| Playout | `backend/playout/` | **Replace** (core) / Keep + Refactor (history, notify, fetch) | Entire `liquidsoap/` subtree + `player/liquidsoap.py` |
| Shared | `backend/shared/` | Keep + Refactor | `HarborInput`, `DEFAULT_CONFIG_FILEPATH`, Windows paths |
| Worker | `backend/worker/` | **Replace** | Celery runtime (tasks logic is portable) |
| Legacy UI | `frontend/legacy/` | Keep + Refactor | Linux path refs in PHP config; new Line-In and Soundcard surfaces needed |
| Upstream installer | `infra/upstream/installer/` | Reference only / Delete | systemd, nginx, deb — not for Windows |
| Upstream Docker | `infra/upstream/docker/` | Reference only | Not primary deployment model |
| Upstream Makefile | `infra/upstream/Makefile` | Reference only | Linux shell targets |
| LibreTime docs | `docs/upstream/` | Reference only | — |

---

## 6. Modules Not Present in LibreTime (RASTATIME New)

These do not exist in LibreTime 4.5.0 and must be built from scratch:

| Module | RASTATIME path | Phase |
|---|---|---|
| Playout engine interface | `playout/engine_interface/` | Phase 3 (T2.1) |
| Mock playout engine | `playout/engine_mock/` | Phase 3 (T4.1) |
| libVLC playout adapter | `playout/engine_libvlc/` | Phase 4 (T5.1–T5.4) |
| Queue manager | `playout/queue_manager/` | Phase 5 (T8.2) |
| Windows audio device manager | `audio/soundcard/` | Phase 7 (T12.1) |
| Line-In domain + runtime | `audio/linein/` | Phase 7 (T13.3–T15.2) |
| Stream egress layer | `streams/egress/` | Phase 6 (T10.1–T10.4) |
| Stream ingress layer | `streams/ingress/` | Phase 6 (T11.1–T11.2) |
| Windows-native background runner | `backend/rastatime_worker/` | Phase 8 (T16.2) |
| NSSM service scripts | `infra/nssm/` | Phase 12 (T22.1–T22.3) |
| PowerShell dev bootstrap | `infra/scripts/dev/` | Phase 2 (T3.1–T3.3) |
| Soundcard settings (API + UI) | `backend/api/soundcard/` + `frontend/` | Phase 7 (T13.1–T13.2) |
| Line-In settings (API + UI) | `backend/api/linein/` + `frontend/` | Phase 7 (T14.1–T14.3) |
