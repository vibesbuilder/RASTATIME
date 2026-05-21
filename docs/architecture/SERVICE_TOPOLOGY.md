# SERVICE_TOPOLOGY.md — RASTATIME Windows Service Split

**Status:** Accepted  
**Task:** T21.1  
**Date:** 2026-04-30  
**Prerequisite ADRs:** ADR-001 (Windows-first), ADR-002 (libVLC), ADR-003 (Icecast auxiliary), ADR-005 (NSSM)

---

## 1. Overview

RASTATIME runs as a set of Windows services managed by NSSM (Non-Sucking
Service Manager, ADR-005).  Each service is an independent OS process; NSSM
handles auto-start on reboot and restart-on-crash for each.

There are **four candidate services**.  Two are mandatory in all deployments;
two are conditional on feature adoption.

```
┌──────────────────────────────────────────────────────────────┐
│  PostgreSQL 17  (external, Windows service, always required) │
└──────────────────┬───────────────────────────────────────────┘
                   │ DB connection
       ┌───────────▼───────────┐     ┌─────────────────────────┐
       │  RASTATIME-API        │◄────│  RASTATIME-WORKER        │
       │  Waitress / Django    │     │  Background job runner   │
       │  port 8000            │     │  (APScheduler-based)     │
       └───────────┬───────────┘     └─────────────────────────┘
                   │ DB + shared state
       ┌───────────▼───────────┐     ┌─────────────────────────┐
       │  RASTATIME-PLAYOUT    │────►│  RASTATIME-ICECAST       │
       │  libVLC playout engine│     │  Icecast 2.x stream srv  │
       │  (no external port)   │     │  port 8001  [OPTIONAL]   │
       └───────────────────────┘     └─────────────────────────┘
```

---

## 2. Service Definitions

### 2.1 RASTATIME-API  *(mandatory)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-API` |
| Executable | `python.exe` |
| Arguments | `-m libretime_api.waitress_serve --host 0.0.0.0 --port 8000 --threads 8` |
| Working directory | `C:\rastatime\backend\api` |
| Bind address | `0.0.0.0:8000` |
| Log (stdout) | `C:\rastatime\logs\api-stdout.log` |
| Log (stderr) | `C:\rastatime\logs\api-stderr.log` |
| Depends on | PostgreSQL (external Windows service) |
| Restart on crash | Yes — NSSM automatic restart, 5 s delay |

**Responsibility:**  
Django REST API (LibreTime API v2 + RASTATIME extensions). Serves the PHP
legacy frontend, the scheduler, and external API clients.  All DB writes for
the API tier go through this process.

**Key environment variables:**

```
DJANGO_SETTINGS_MODULE = libretime_api.settings.prod
LIBRETIME_CONFIG_FILEPATH = C:\rastatime\config\libretime.conf
RASTATIME_API_HOST = 0.0.0.0
RASTATIME_API_PORT = 8000
RASTATIME_API_THREADS = 8
```

---

### 2.2 RASTATIME-WORKER  *(mandatory)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-WORKER` |
| Executable | `python.exe` |
| Arguments | `-m rastatime_worker` |
| Working directory | `C:\rastatime\backend` |
| External port | None |
| Log (stdout) | `C:\rastatime\logs\worker-stdout.log` |
| Log (stderr) | `C:\rastatime\logs\worker-stderr.log` |
| Depends on | PostgreSQL; RASTATIME-API should be up (health-check gate in T22.1) |
| Restart on crash | Yes — NSSM automatic restart, 10 s delay |

**Responsibility:**  
Replaces Celery.  Runs as an APScheduler-based (or custom polling loop)
Windows-native background runner.  Handles:
- Media file import and metadata extraction
- Podcast episode fetching
- Watched-folder scans
- Playout history aggregation
- Scheduled cleanup tasks

No broker (RabbitMQ) is required.  All job state lives in PostgreSQL.  A
broker may be introduced in a later phase if fan-out or deferred retries
become necessary — this is a conditional item (see §4).

**Key environment variables:**

```
DJANGO_SETTINGS_MODULE = libretime_api.settings.prod
LIBRETIME_CONFIG_FILEPATH = C:\rastatime\config\libretime.conf
```

---

### 2.3 RASTATIME-PLAYOUT  *(mandatory)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-PLAYOUT` |
| Executable | `python.exe` |
| Arguments | `-m playout` |
| Working directory | `C:\rastatime` |
| External port | None (IPC via shared DB; future: named pipe or local socket) |
| Log (stdout) | `C:\rastatime\logs\playout-stdout.log` |
| Log (stderr) | `C:\rastatime\logs\playout-stderr.log` |
| Depends on | PostgreSQL; RASTATIME-API (reads schedule via API or direct DB) |
| Restart on crash | Yes — NSSM automatic restart, 5 s delay |

**Responsibility:**  
libVLC-based on-air playout engine (ADR-002).  Reads the show schedule from
PostgreSQL, drives the libVLC queue, tracks now-playing state, writes playback
history events via `PlaybackEventPersister`, and manages line-in routing.  
Soundcard output device selection is read from `rastatime_soundcard_settings`.

**Key environment variables:**

```
DJANGO_SETTINGS_MODULE = libretime_api.settings.prod
LIBRETIME_CONFIG_FILEPATH = C:\rastatime\config\libretime.conf
RASTATIME_VLC_PLUGIN_PATH = C:\Program Files\VideoLAN\VLC\plugins
```

**Note on IPC:**  
In the initial implementation the playout engine and the API server share state
exclusively through PostgreSQL.  The `now_playing` module exposes a
process-level singleton useful for single-process dev mode; in production the
two processes communicate only through the DB.  A lightweight IPC mechanism
(named pipe or local REST endpoint) may be added in a later phase if latency
requirements demand it.

---

### 2.4 RASTATIME-ICECAST  *(optional — stream egress/ingress)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-ICECAST` |
| Executable | `icecast.exe` |
| Arguments | `-c C:\rastatime\config\icecast.xml` |
| Working directory | `C:\Program Files\Icecast` |
| External ports | `8001` (HTTP streams), `8002` (admin UI) — configurable in `icecast.xml` |
| Log | `C:\rastatime\logs\icecast.log` (via `icecast.xml` `<logdir>`) |
| Depends on | Nothing from RASTATIME stack (standalone audio server) |
| Restart on crash | Yes — NSSM automatic restart, 15 s delay |

**Responsibility:**  
Auxiliary stream server (ADR-003).  Used only if the deployment requires:
- Outgoing internet audio streams (HTTP/Opus/MP3) for public listeners, OR
- Incoming remote live streams (source client → Icecast mount → RASTATIME-PLAYOUT)

When Icecast is present, RASTATIME-PLAYOUT connects to it as a source client
via libVLC's `stream_out` module.  When Icecast is absent, audio reaches
listeners only through the local soundcard (direct studio monitoring) — no
public stream is available.

**Port selection rationale:**  
Icecast defaults to port 8000.  RASTATIME-API occupies port 8000.  Icecast is
therefore configured to port 8001 to avoid the conflict.  Adjust `icecast.xml`
and inform DJs/listeners of the correct mount URL.

---

## 3. Startup Order and Dependency Chain

```
Boot
 │
 ├─1─► PostgreSQL           (Windows built-in service; must be Running)
 │
 ├─2─► RASTATIME-API        (waits ~5 s for PostgreSQL TCP readiness)
 │
 ├─3─► RASTATIME-WORKER     (waits for RASTATIME-API /health 200)
 │
 ├─4─► RASTATIME-PLAYOUT    (waits for RASTATIME-API /health 200)
 │
 └─5─► RASTATIME-ICECAST    (optional; independent; start any time)
```

**NSSM does not natively enforce service-start ordering.**  
Ordering is achieved in two ways:

1. **Startup delay** — each NSSM service is configured with a startup delay
   (`AppThrottle`) that gives earlier services time to become ready.
2. **Health-check gate** (implemented in T22.1 install scripts) — worker and
   playout entry points poll `http://127.0.0.1:8000/health` with exponential
   backoff before starting their main loop.

---

## 4. Optional / Conditional Components

| Component | Condition | Phase |
|---|---|---|
| **RASTATIME-ICECAST** | Required only if outgoing public streams or remote live-stream ingress is needed | Install-time choice; add service with T22.1 script |
| **RabbitMQ broker** | Deferred; only if worker fan-out or deferred retry patterns exceed SQLite/PG capabilities | Not in phase 1; re-evaluate in M30+ |

---

## 5. Port Summary

| Service | Port | Protocol | Notes |
|---|---|---|---|
| RASTATIME-API | 8000 | HTTP (Waitress) | REST API + legacy PHP frontend proxy |
| RASTATIME-ICECAST | 8001 | HTTP (Icecast) | Audio stream HTTP endpoint; configurable |
| RASTATIME-ICECAST | 8002 | HTTP (Icecast) | Icecast admin UI; configurable |
| PostgreSQL | 5432 | TCP | Standard PostgreSQL; managed externally |

All ports are configurable via environment variables (API) or `icecast.xml`
(Icecast).  The values above are the RASTATIME defaults for phase 1.

---

## 6. Log File Layout

```
C:\rastatime\logs\
├── api-stdout.log         # Waitress + Django INFO/WARNING/ERROR
├── api-stderr.log         # Python uncaught exceptions (API)
├── worker-stdout.log      # Job runner output
├── worker-stderr.log      # Python uncaught exceptions (worker)
├── playout-stdout.log     # libVLC events, schedule reads, now-playing changes
├── playout-stderr.log     # Python uncaught exceptions (playout)
└── icecast.log            # Icecast connections, mount events (optional)
```

NSSM routes stdout/stderr per service to the files above.  Log rotation is
handled by NSSM's built-in `AppRotateFiles` option; target: 10 MB per file,
5 files kept.

---

## 7. RASTATIME-Specific Windows Considerations

| Concern | Resolution |
|---|---|
| `SIGTERM` / Unix signals | NSSM sends `WM_CLOSE` or `TerminateProcess`; Python services must use `signal.SIGBREAK` (Windows) or NSSM `AppStopMethodConsole` |
| Console window | All services run `AppNoConsole = 1` via NSSM |
| Working directory | Always set explicitly in NSSM; never rely on `cwd` at startup |
| Python path | NSSM `AppEnvironmentExtra = PYTHONPATH=C:\rastatime` set per service |
| libVLC DLLs | `RASTATIME_VLC_PLUGIN_PATH` set for playout service; libVLC installed system-wide |
| Config file | `LIBRETIME_CONFIG_FILEPATH` set for API, worker, and playout services |

---

## 8. Follow-Up Tasks

| Task | Milestone | Description |
|---|---|---|
| T22.1 | M22 | NSSM install scripts (`install-*.ps1`) — one per service |
| T22.2 | M22 | NSSM remove scripts (`remove-*.ps1`) |
| T22.3 | M22 | Status and health helper (`status.ps1`) |
| T22.4 | M22 | Restart order and recovery documentation (`RESTART_ORDER.md`) |
| T3.1 | M3 | Bootstrap script NSSM presence check |
