# RESTART_ORDER.md — RASTATIME Service Restart and Recovery

**Status:** Accepted  
**Task:** T22.4  
**Date:** 2026-04-30  
**Prerequisite:** SERVICE_TOPOLOGY.md (T21.1), install scripts (T22.1), remove scripts (T22.2), status helper (T22.3)

---

## 1. Overview

RASTATIME runs as four Windows services managed by NSSM.  This document
defines the correct order to start, stop, and recover those services so
that dependency constraints are respected and on-air audio is protected.

**Quick reference:**

| Operation | Command |
|---|---|
| Check all service states | `powershell -File infra\nssm\status.ps1` |
| Start in correct order | see §3 |
| Stop in correct order | see §4 |
| Recover a failed service | see §5 |
| Full reinstall | see §6 |

---

## 2. Service Dependency Map

```
PostgreSQL 17  (external Windows service — must always be Running first)
    │
    └─► RASTATIME-API        port 8000   [mandatory]
            │
            ├─► RASTATIME-WORKER     no external port  [mandatory]
            │       polls http://127.0.0.1:8000/health before starting
            │
            └─► RASTATIME-PLAYOUT    no external port  [mandatory]
                    polls http://127.0.0.1:8000/health before starting

RASTATIME-ICECAST   port 8001   [optional — independent of the above]
```

**Key rule:** RASTATIME-API must be healthy (HTTP 200 at
`http://127.0.0.1:8000/health`) before the worker and playout services
start their main loops.  PostgreSQL must be Running before the API can
accept its first request.

---

## 3. Startup Order

Start services in this exact sequence.  Never start the worker or playout
before the API is healthy.

```
Step 1 ─ PostgreSQL
    net start postgresql-x64-17
    # or use Services.msc / SC start
    # Verify: pg_isready -h 127.0.0.1 -p 5432

Step 2 ─ RASTATIME-API
    nssm start RASTATIME-API
    # Wait for healthy:
    # Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
    # Expected: StatusCode 200

Step 3 ─ RASTATIME-WORKER
    nssm start RASTATIME-WORKER
    # The worker entry point polls http://127.0.0.1:8000/health internally
    # before entering its scheduling loop.

Step 4 ─ RASTATIME-PLAYOUT
    nssm start RASTATIME-PLAYOUT
    # The playout entry point polls http://127.0.0.1:8000/health internally
    # before loading the schedule and starting audio output.

Step 5 ─ RASTATIME-ICECAST  [optional]
    nssm start RASTATIME-ICECAST
    # Independent — may be started at any time.
    # Stream URL: http://localhost:8001/
```

### 3.1 Verifying a Successful Startup

After all services are started, run the status helper:

```powershell
powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1
```

Expected output:
- All mandatory services: `Running`
- API health check: `HTTP 200  OK — API is healthy`
- RASTATIME-ICECAST: `Running` or `Not installed  (optional — OK)`

---

## 4. Shutdown Order

Stop services in **reverse dependency order** to avoid the API disappearing
while the worker or playout are still running.

```
Step 1 ─ RASTATIME-ICECAST  [optional — stop first; independent]
    nssm stop RASTATIME-ICECAST confirm

Step 2 ─ RASTATIME-PLAYOUT  ⚠ stops on-air audio
    nssm stop RASTATIME-PLAYOUT confirm

Step 3 ─ RASTATIME-WORKER
    nssm stop RASTATIME-WORKER confirm

Step 4 ─ RASTATIME-API
    nssm stop RASTATIME-API confirm

Step 5 ─ PostgreSQL  (only if a full system shutdown is intended)
    net stop postgresql-x64-17
```

> **⚠ Caution:** Step 2 (stopping RASTATIME-PLAYOUT) interrupts on-air
> audio output immediately.  Coordinate with on-air staff before executing
> during a broadcast.

### 4.1 Using the Remove Scripts (Clean Uninstall)

To stop **and deregister** a service, use the T22.2 remove scripts in the
same order:

```powershell
powershell -File infra\nssm\remove-playout.ps1 -Force
powershell -File infra\nssm\remove-worker.ps1  -Force
powershell -File infra\nssm\remove-api.ps1     -Force
powershell -File infra\nssm\remove-icecast.ps1 -Force   # optional
```

Add `-PurgeLogs` to also delete the log files under `C:\rastatime\logs`.

---

## 5. Per-Service Recovery Procedures

### 5.1 Recovery: RASTATIME-API

**Symptoms:** API health check fails; worker and playout may crash-loop.

**Diagnosis:**
```powershell
# 1. Check SCM status
Get-Service RASTATIME-API

# 2. Check recent logs
Get-Content C:\rastatime\logs\api-stdout.log -Tail 50
Get-Content C:\rastatime\logs\api-stderr.log -Tail 50

# 3. Check PostgreSQL (the most common cause)
pg_isready -h 127.0.0.1 -p 5432
```

**Recovery steps:**
```powershell
# a. Ensure PostgreSQL is running (port 5432)
Get-Service postgresql*

# b. Restart the API
nssm restart RASTATIME-API

# c. Verify health
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing

# d. If restart does not help, reinstall the service
powershell -File infra\nssm\install-api.ps1 -StartService
```

---

### 5.2 Recovery: RASTATIME-WORKER

**Symptoms:** Media import stalls; podcast fetching stops; watched-folder
scans not running; playout history not aggregated.

**Diagnosis:**
```powershell
Get-Service RASTATIME-WORKER
Get-Content C:\rastatime\logs\worker-stdout.log -Tail 50
Get-Content C:\rastatime\logs\worker-stderr.log -Tail 50
```

**Recovery steps:**
```powershell
# a. Ensure RASTATIME-API is healthy first
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing

# b. Restart the worker
nssm restart RASTATIME-WORKER

# c. If crashing repeatedly, reinstall
powershell -File infra\nssm\install-worker.ps1 -StartService
```

---

### 5.3 Recovery: RASTATIME-PLAYOUT

**Symptoms:** On-air silence; `now_playing` not updating; libVLC errors in
the playout log.

**Diagnosis:**
```powershell
Get-Service RASTATIME-PLAYOUT
Get-Content C:\rastatime\logs\playout-stdout.log -Tail 50
Get-Content C:\rastatime\logs\playout-stderr.log -Tail 50
```

**Recovery steps:**
```powershell
# a. Ensure RASTATIME-API is healthy (playout reads schedule via DB/API)
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing

# b. Check VLC plugin path
Test-Path "C:\Program Files\VideoLAN\VLC\plugins"

# c. Restart playout
nssm restart RASTATIME-PLAYOUT

# d. If crashing on VLC init: reinstall with correct VLC path
powershell -File infra\nssm\install-playout.ps1 `
    -VlcPluginPath "C:\Program Files\VideoLAN\VLC\plugins" `
    -StartService
```

> **⚠ Note:** Restarting playout causes a brief audio gap.  NSSM will
> restart it automatically on crash (5 s delay); manual intervention is
> only needed if the automatic restart loop is failing.

---

### 5.4 Recovery: RASTATIME-ICECAST  *(optional)*

**Symptoms:** Public stream URL unreachable; DJs cannot connect as source
clients; listeners get connection refused on port 8001.

**Diagnosis:**
```powershell
Get-Service RASTATIME-ICECAST
Get-Content C:\rastatime\logs\icecast-nssm-stdout.log -Tail 30
# Also check the Icecast application log set in icecast.xml <logdir>
```

**Recovery steps:**
```powershell
# a. Restart Icecast
nssm restart RASTATIME-ICECAST

# b. Verify stream endpoint
Invoke-WebRequest http://127.0.0.1:8001/ -UseBasicParsing

# c. If icecast.xml is misconfigured, edit it and restart
nssm restart RASTATIME-ICECAST

# d. Reinstall if service entry is corrupt
powershell -File infra\nssm\install-icecast.ps1 -StartService
```

> **Note:** RASTATIME-ICECAST failure does not affect the API, worker, or
> playout.  Studio audio continues through the local soundcard.

---

## 6. Full Stack Reinstall

Use this procedure after a system migration, major Python upgrade, or if
NSSM service entries are corrupt.

```powershell
# 1. Stop and remove all services (preserve logs)
powershell -File infra\nssm\remove-playout.ps1 -Force
powershell -File infra\nssm\remove-worker.ps1  -Force
powershell -File infra\nssm\remove-api.ps1     -Force
powershell -File infra\nssm\remove-icecast.ps1 -Force

# 2. Rebuild the Python venv if needed
python -m venv C:\rastatime\.venv
C:\rastatime\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Reinstall services in dependency order
powershell -File infra\nssm\install-api.ps1     -StartService
# Wait for API health before installing worker and playout:
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
powershell -File infra\nssm\install-worker.ps1  -StartService
powershell -File infra\nssm\install-playout.ps1 -StartService
powershell -File infra\nssm\install-icecast.ps1 -StartService  # optional

# 4. Verify
powershell -File infra\nssm\status.ps1
```

---

## 7. NSSM Automatic Restart Behaviour

NSSM is configured to restart each service automatically on crash.  The
delays are set to respect the dependency chain:

| Service | Restart delay | Reason |
|---|---|---|
| RASTATIME-API | 5 s | Fast recovery; worker + playout wait for it |
| RASTATIME-WORKER | 10 s | Longer than API so API has time to restart first |
| RASTATIME-PLAYOUT | 5 s | Matches API; health-gate in entry point handles ordering |
| RASTATIME-ICECAST | 15 s | Independent; no rush |

If a service crash-loops (restarts more than 3 times in 60 seconds),
NSSM's `AppThrottle` kicks in and increases the delay.  Check the logs:

```powershell
Get-Content C:\rastatime\logs\api-stderr.log -Tail 100
```

---

## 8. Windows Boot Sequence

All mandatory services are configured `SERVICE_AUTO_START`.  On a cold
boot the expected sequence is:

1. Windows starts PostgreSQL (standard Windows service, starts before NSSM services)
2. NSSM starts RASTATIME-API after its `AppThrottle` delay (~5 s)
3. NSSM starts RASTATIME-WORKER after its throttle (~15 s); the worker's
   health-check gate polls `http://127.0.0.1:8000/health` internally
4. NSSM starts RASTATIME-PLAYOUT after its throttle (~15 s); same gate
5. NSSM starts RASTATIME-ICECAST (if installed) at any time

If the machine boots and services do not come up automatically, check:

```powershell
# NSSM logs its own start attempts in the Windows Application event log
Get-EventLog -LogName Application -Source nssm -Newest 20
```

---

## 9. Log File Reference

All log files live under `C:\rastatime\logs`.  NSSM rotates them at
10 MB per file, keeping 5 generations.

| Service | Stdout log | Stderr log |
|---|---|---|
| RASTATIME-API | `api-stdout.log` | `api-stderr.log` |
| RASTATIME-WORKER | `worker-stdout.log` | `worker-stderr.log` |
| RASTATIME-PLAYOUT | `playout-stdout.log` | `playout-stderr.log` |
| RASTATIME-ICECAST | `icecast-nssm-stdout.log` | `icecast-nssm-stderr.log` |

Icecast also writes its own application log via `<logdir>` in `icecast.xml`.

---

## 10. Related Tasks and Scripts

| Reference | Description |
|---|---|
| T21.1 | Service topology definition (`docs/architecture/SERVICE_TOPOLOGY.md`) |
| T22.1 | Install scripts — `infra\nssm\install-*.ps1` |
| T22.2 | Remove scripts — `infra\nssm\remove-*.ps1` |
| T22.3 | Status helper — `infra\nssm\status.ps1` |
| T22.4 | This document |
| T3.1 | Bootstrap check (`infra\scripts\dev\bootstrap.ps1`) |
