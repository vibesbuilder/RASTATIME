# SERVICE_TOPOLOGY.md — RASTATIME Windows Service Split

**Status:** Accepted  
**Task:** T21.1  
**Date:** 2026-04-30  
**Revised:** 2026-08-27 — updated to the seven-service production topology
(Liquidsoap engine since the 2026-05 cutover, API on 8765, RabbitMQ
required, ANALYZER/APACHE/LIQUIDSOAP services added; verified against the
2026-08 studio-machine migration).  
**Prerequisite ADRs:** ADR-001 (Windows-first), ADR-002 (libVLC — superseded
by the 2026-05 Liquidsoap cutover), ADR-003 (Icecast auxiliary), ADR-005 (NSSM)

---

## 1. Overview

RASTATIME runs as a set of Windows services managed by NSSM (Non-Sucking
Service Manager, ADR-005).  Each service is an independent OS process; NSSM
handles auto-start on reboot and restart-on-crash for each.

There are **seven production services** (plus two external Windows
services, PostgreSQL and RabbitMQ).

```
┌──────────────────────────────────────────────────────────────┐
│  PostgreSQL 17   (external, Windows service, always required)│
│  RabbitMQ 4.x    (external, Windows service, required —      │
│                   analyzer queue + upload dispatch)          │
└──────────────────┬───────────────────────────────────────────┘
                   │
       ┌───────────▼───────────┐     ┌─────────────────────────┐
       │  RASTATIME-API        │◄────│  RASTATIME-WORKER       │
       │  Waitress / Django    │     │  Background job runner  │
       │  port 8765            │     └─────────────────────────┘
       └───────────┬───────────┘     ┌─────────────────────────┐
                   │◄────────────────│  RASTATIME-ANALYZER     │
                   │                 │  RabbitMQ upload consumer│
       ┌───────────▼───────────┐     └─────────────────────────┘
       │  RASTATIME-APACHE     │  port 80 — PHP frontend;
       │  (proxies /api/v2/ →  │  serves the web UI
       │   127.0.0.1:8765)     │
       └───────────────────────┘
       ┌───────────────────────┐     ┌─────────────────────────┐
       │  RASTATIME-PLAYOUT    │────►│  RASTATIME-LIQUIDSOAP   │
       │  Pypo scheduler       │     │  audio engine; DJ       │
       │  (drives Liquidsoap   │     │  harbor 8001 (both      │
       │   via telnet)         │     │  mounts /main + /show)  │
       └───────────────────────┘     └───────────┬─────────────┘
                                                 │ source client
                                     ┌───────────▼─────────────┐
                                     │  RASTATIME-ICECAST      │
                                     │  port 8000 (listeners)  │
                                     └─────────────────────────┘
```

---

## 2. Service Definitions

### 2.1 RASTATIME-API  *(mandatory)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-API` |
| Executable | `python.exe` |
| Arguments | `-m libretime_api.waitress_serve --host 0.0.0.0 --port 8765 --threads 8` |
| Working directory | `C:\rastatime\backend\api` |
| Bind address | `0.0.0.0:8765` |
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
RASTATIME_API_PORT = 8765
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

The worker itself needs no broker — its job state lives in PostgreSQL.
RabbitMQ is nevertheless **required** in the stack: the PHP frontend
publishes a message for every upload, and RASTATIME-ANALYZER (§2.5)
consumes that queue (vhost `/rastatime`, port 5672, credentials in the
`rabbitmq` section of `libretime.conf`).

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
| Arguments | `-m libretime_playout` |
| Working directory | `C:\rastatime` |
| External port | None (IPC via shared DB; future: named pipe or local socket) |
| Log (stdout) | `C:\rastatime\logs\playout-stdout.log` |
| Log (stderr) | `C:\rastatime\logs\playout-stderr.log` |
| Depends on | PostgreSQL; RASTATIME-API (reads schedule via API or direct DB) |
| Restart on crash | Yes — NSSM automatic restart, 5 s delay |

**Responsibility:**  
On-air playout scheduler (Pypo).  Reads the show schedule from
PostgreSQL/API, drives the **Liquidsoap** audio engine (RASTATIME-LIQUIDSOAP,
§2.7) via its telnet interface, tracks now-playing state, writes playback
history events, and manages line-in routing.  Soundcard output device
selection is read from `rastatime_soundcard_settings`.  The Liquidsoap
production script `C:\Tools\liquidsoap\rastatime.liq` is rendered from a
template plus the DB stream settings via
`python -m libretime_playout.liquidsoap_config render`.
(mpv/VLC remain only as legacy fallback engine code pending deletion.)

**Key environment variables:**

```
DJANGO_SETTINGS_MODULE = libretime_api.settings.prod
LIBRETIME_CONFIG_FILEPATH = C:\rastatime\config\libretime.conf
RASTATIME_API_URL = http://127.0.0.1:8765
RASTATIME_PLAYOUT_ENGINE = liquidsoap
RASTATIME_MPV_LOG_LEVEL = warn
RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS = 1.0
```

> `install-playout.ps1` sets only the first three (plus PYTHONPATH/PATH);
> the three `RASTATIME_*` engine extras are applied manually after install
> (`nssm set` replaces the whole env block — see MIGRATION.md §4.7).

**Note on IPC:**  
In the initial implementation the playout engine and the API server share state
exclusively through PostgreSQL.  The `now_playing` module exposes a
process-level singleton useful for single-process dev mode; in production the
two processes communicate only through the DB.  A lightweight IPC mechanism
(named pipe or local REST endpoint) may be added in a later phase if latency
requirements demand it.

---

### 2.4 RASTATIME-ICECAST  *(streaming)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-ICECAST` |
| Executable | `C:\Tools\Icecast\bin\icecast.exe` (Icecast **2.4.4** — deliberate; the live `icecast.xml` uses 2.4 auth semantics) |
| Arguments | `-c C:\rastatime\config\icecast.xml` |
| Working directory | `C:\Tools\Icecast` |
| External port | `8000` (HTTP streams + admin UI) — configurable in `icecast.xml` |
| Log | `C:\rastatime\logs\` (via `icecast.xml` `<logdir>`) |
| Depends on | Nothing from RASTATIME stack (standalone audio server) |
| Restart on crash | Yes — NSSM automatic restart, 15 s delay |

**Responsibility:**  
Stream server (ADR-003).  Serves the public listener mounts
(`/rastatime`, `/rastatime-aac`, `/rastatime-ogg`) pushed by
RASTATIME-LIQUIDSOAP as a source client, plus the hidden input mounts
`/main` and `/show` with `stream_auth`-based DJ authentication, and the
hidden `/linein-capture` mount (raw line-in fan-out; source-password
only, no `stream_auth`).

**Port rationale:**  
The API listens on 8765, so Icecast keeps its default **8000**.  Port
**8001** is the **Liquidsoap DJ harbor** — both DJ mounts (`/main` and
`/show`) share it (single-port workaround for a Liquidsoap 2.4.4
multi-port harbor bug, 2026-05-27; 8002, the originally planned Show
port, is only the harbor's ICY companion listener).  It belongs to
RASTATIME-LIQUIDSOAP, not to Icecast.

---

### 2.5 RASTATIME-ANALYZER  *(mandatory)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-ANALYZER` |
| Executable | `libretime-analyzer.exe` (venv console script) |
| Working directory | `C:\rastatime\backend\analyzer` |
| External port | None (consumes RabbitMQ) |
| Logs | `analyzer-stdout.log` / `analyzer-stderr.log` |
| Depends on | RabbitMQ + RASTATIME-API |
| Restart on crash | Yes — 10 s delay |

Media-import pipeline: consumes the RabbitMQ upload queue, extracts
metadata/ReplayGain/cue points (FFmpeg on PATH), moves files into the
storage tree and flips `cc_files` from "Pending Import" to "Ready".

### 2.6 RASTATIME-APACHE  *(mandatory — web UI)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-APACHE` |
| Executable | `C:\Tools\Apache24\bin\httpd.exe` |
| External port | `80` (web UI) |
| Logs | `apache-nssm-*.log` (NSSM) + Apache's own logs under `C:\Tools\Apache24\logs` |
| Depends on | RASTATIME-API (proxies `/api/v2/` + `/api-auth/` to `127.0.0.1:8765`) |
| Restart on crash | Yes — 5 s delay; bounded stop methods |

PHP 8.3 legacy frontend via mod_fcgid (see INSTALL_APACHE.md).

### 2.7 RASTATIME-LIQUIDSOAP  *(mandatory — audio engine)*

| Property | Value |
|---|---|
| NSSM service name | `RASTATIME-LIQUIDSOAP` |
| Executable | `C:\Tools\liquidsoap\liquidsoap.exe` |
| Arguments | `C:\Tools\liquidsoap\rastatime.liq` (machine-rendered — see §2.3) |
| External ports | `8001` (DJ harbor — `/main` and `/show` share it; `8002` is the harbor's ICY companion listener), telnet `1234` (localhost, Pypo control) |
| Logs | `liquidsoap-stdout.log` / `liquidsoap-stderr.log` |
| Depends on | RASTATIME-ICECAST (pushes the output mounts) |
| Restart on crash | Yes — 5 s delay, throttled |

Production audio engine since the 2026-05 cutover (Seamless-Bus-Mix
Phase 2): gapless transitions, native crossfade, persistent Icecast
source connections, DJ harbors, hourly 24/7 recording.
Install script: `backend\playout\config\nssm-install-liquidsoap.ps1`.

---

## 3. Startup Order and Dependency Chain

```
Boot
 │
 ├─1─► PostgreSQL + RabbitMQ  (Windows services; must be Running)
 │
 ├─2─► RASTATIME-API          (waits ~5 s for PostgreSQL TCP readiness)
 │
 ├─3─► RASTATIME-WORKER       (waits for RASTATIME-API /health 200)
 │
 ├─4─► RASTATIME-ICECAST      (standalone; before Liquidsoap)
 ├─5─► RASTATIME-LIQUIDSOAP   (pushes output mounts to Icecast)
 │
 ├─6─► RASTATIME-PLAYOUT      (waits for /health 200; drives Liquidsoap)
 │
 ├─7─► RASTATIME-ANALYZER     (needs RabbitMQ + API)
 └─8─► RASTATIME-APACHE       (web UI; proxies to the API)
```

**NSSM does not natively enforce service-start ordering.**  
Ordering is achieved in two ways:

1. **Startup delay** — each NSSM service is configured with a startup delay
   (`AppThrottle`) that gives earlier services time to become ready.
2. **Health-check gate** (implemented in T22.1 install scripts) — worker and
   playout entry points poll `http://127.0.0.1:8765/health` with exponential
   backoff before starting their main loop.

---

## 4. Optional / Conditional Components

| Component | Condition | Phase |
|---|---|---|
| **RASTATIME-ICECAST** | Part of the production stack (public streams + DJ input mounts) | Installed by default since the Liquidsoap cutover |
| **RabbitMQ broker** | **Required** — analyzer upload queue + PHP upload dispatch (vhost `/rastatime`, port 5672) | In production since the analyzer service |

---

## 5. Port Summary

| Service | Port | Protocol | Notes |
|---|---|---|---|
| RASTATIME-APACHE | 80 | HTTP (Apache) | Web UI; proxies `/api/v2/` to the API |
| RASTATIME-API | 8765 | HTTP (Waitress) | REST API + health endpoint |
| RASTATIME-ICECAST | 8000 | HTTP (Icecast) | Listener streams + admin UI |
| RASTATIME-LIQUIDSOAP | 8001 | HTTP (harbor) | DJ source inputs — `/main` **and** `/show` (shared port; 8002 = ICY companion) |
| RASTATIME-LIQUIDSOAP | 1234 | telnet (localhost) | Pypo control channel |
| RabbitMQ | 5672 | AMQP | Upload queue (vhost `/rastatime`); managed externally |
| PostgreSQL | 5432 | TCP | Standard PostgreSQL; managed externally |

All ports are configurable via install-script parameters (API), the
rendered `rastatime.liq` (harbors/telnet), or `icecast.xml` (Icecast).

---

## 6. Log File Layout

```
C:\rastatime\logs\
├── api-stdout.log         # Waitress + Django INFO/WARNING/ERROR
├── api-stderr.log         # Python uncaught exceptions (API)
├── worker-stdout.log      # Job runner output
├── worker-stderr.log      # Python uncaught exceptions (worker)
├── playout-stdout.log     # Scheduler events, schedule reads, now-playing changes
├── playout-stderr.log     # Python uncaught exceptions (playout)
├── analyzer-stdout.log    # Import pipeline output
├── analyzer-stderr.log    # Python uncaught exceptions (analyzer)
├── apache-nssm-stdout.log # NSSM-side Apache capture (Apache's own logs: C:\Tools\Apache24\logs)
├── apache-nssm-stderr.log
├── liquidsoap-stdout.log  # Liquidsoap engine log (clock, sources, Icecast connections)
├── liquidsoap-stderr.log
├── access.log             # Icecast access log (via icecast.xml <logdir>)
└── error.log              # Icecast error log
```

NSSM routes stdout/stderr per service to the files above (the two
Icecast `access.log`/`error.log` are written by Icecast itself via
`<logdir>`; NSSM additionally captures `icecast-nssm-stdout.log` /
`icecast-nssm-stderr.log`).  Log rotation is handled by NSSM's built-in
`AppRotateFiles` option at 10 MB per file; rotated generations
accumulate — NSSM has no file-count cap.

---

## 7. RASTATIME-Specific Windows Considerations

| Concern | Resolution |
|---|---|
| `SIGTERM` / Unix signals | NSSM sends `WM_CLOSE` or `TerminateProcess`; Python services must use `signal.SIGBREAK` (Windows) or NSSM `AppStopMethodConsole` |
| Console window | All services run `AppNoConsole = 1` via NSSM |
| Working directory | Always set explicitly in NSSM; never rely on `cwd` at startup |
| Python path | `PYTHONPATH=C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime` on the API/worker/playout services (worker additionally gets `C:\rastatime\backend`) |
| Liquidsoap engine | `RASTATIME_PLAYOUT_ENGINE=liquidsoap` on the playout service; engine at `C:\Tools\liquidsoap` (own NSSM service) |
| Config file | `LIBRETIME_CONFIG_FILEPATH` set for the API, worker, playout, and analyzer services |

---

## 8. Follow-Up Tasks

| Task | Milestone | Description |
|---|---|---|
| T22.1 | M22 | NSSM install scripts (`install-*.ps1`) — one per service |
| T22.2 | M22 | NSSM remove scripts (`remove-*.ps1`) |
| T22.3 | M22 | Status and health helper (`status.ps1`) |
| T22.4 | M22 | Restart order and recovery documentation (`RESTART_ORDER.md`) |
| T3.1 | M3 | Bootstrap script NSSM presence check |
