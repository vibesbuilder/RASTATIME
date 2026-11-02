# RESTART_ORDER.md — RASTATIME Service Restart and Recovery

**Status:** Accepted  
**Task:** T22.4  
**Date:** 2026-04-30  
**Prerequisite:** SERVICE_TOPOLOGY.md (T21.1), install scripts (T22.1), remove scripts (T22.2), status helper (T22.3)

---

## 1. Overview

RASTATIME runs as eight Windows services managed by NSSM.  This document
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
RabbitMQ       (external Windows service — analyzer queue + upload dispatch)
    │
    └─► RASTATIME-API        port 8765   [mandatory]
            │
            ├─► RASTATIME-WORKER     no external port  [mandatory]
            │       polls http://127.0.0.1:8765/health before starting
            │
            ├─► RASTATIME-PLAYOUT    no external port  [mandatory]
            │       polls http://127.0.0.1:8765/health before starting
            │       drives RASTATIME-LIQUIDSOAP via telnet
            │
            ├─► RASTATIME-ANALYZER   no external port  [mandatory]
            │       consumes the RabbitMQ upload queue
            │
            └─► RASTATIME-APACHE     port 80   [mandatory — web UI]
                    proxies /api/v2/ to http://127.0.0.1:8765

RASTATIME-LIQUIDSOAP  DJ harbor 8001 (both mounts); pushes to Icecast  [mandatory]
RASTATIME-ICECAST     port 8000 (listeners + admin)            [streaming]
```

**Key rule:** RASTATIME-API must be healthy (HTTP 200 at
`http://127.0.0.1:8765/health`) before the worker and playout services
start their main loops.  PostgreSQL must be Running before the API can
accept its first request; RabbitMQ must be Running before the analyzer
starts (and before uploads are attempted in the web UI).

---

## 3. Startup Order

Start services in this exact sequence.  Never start the worker or playout
before the API is healthy.

```
Step 1 ─ PostgreSQL + RabbitMQ
    net start postgresql-x64-17
    net start RabbitMQ
    # or use Services.msc / SC start
    # Verify: pg_isready -h 127.0.0.1 -p 5432
    #         Get-Service RabbitMQ   (Running)

Step 2 ─ RASTATIME-API
    nssm start RASTATIME-API
    # Wait for healthy:
    # Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
    # Expected: StatusCode 200

Step 3 ─ RASTATIME-WORKER
    nssm start RASTATIME-WORKER
    # The worker entry point polls http://127.0.0.1:8765/health internally
    # before entering its scheduling loop.

Step 4 ─ RASTATIME-ICECAST + RASTATIME-LIQUIDSOAP
    nssm start RASTATIME-ICECAST
    nssm start RASTATIME-LIQUIDSOAP
    # Icecast first, then Liquidsoap (it pushes the output mounts to
    # Icecast and offers the DJ harbor on 8001 — /main and /show
    # share the port).
    # Listener URL: http://localhost:8000/rastatime

Step 5 ─ RASTATIME-PLAYOUT
    nssm start RASTATIME-PLAYOUT
    # The playout entry point polls http://127.0.0.1:8765/health internally
    # before loading the schedule; it then drives Liquidsoap via telnet.

Step 6 ─ RASTATIME-ANALYZER
    nssm start RASTATIME-ANALYZER
    # Needs RabbitMQ (Step 1) + the API; without it uploads stay at
    # "Pending Import".

Step 7 ─ RASTATIME-APACHE
    nssm start RASTATIME-APACHE
    # Web UI on port 80; proxies /api/v2/ to the API on 8765.
```

### 3.1 Verifying a Successful Startup

After all services are started, run the status helper:

```powershell
powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1
```

Expected output (covers all eight services incl. RASTATIME-STANDBY since
2026-11-02, with HTTP probes for the API, Apache and Icecast):
- All mandatory services: `Running`
- API / Apache / Icecast probes: `HTTP 200 healthy`

---

## 4. Shutdown Order

Stop services in **reverse dependency order** to avoid the API disappearing
while the worker or playout are still running.

```
Step 1 ─ RASTATIME-APACHE  (web UI first — stops new operator actions)
    nssm stop RASTATIME-APACHE confirm

Step 2 ─ RASTATIME-ANALYZER
    nssm stop RASTATIME-ANALYZER confirm

Step 3 ─ RASTATIME-PLAYOUT  ⚠ stops schedule-driven playout
    nssm stop RASTATIME-PLAYOUT confirm

Step 4 ─ RASTATIME-LIQUIDSOAP  ⚠ stops on-air audio + DJ harbors
    nssm stop RASTATIME-LIQUIDSOAP confirm

Step 5 ─ RASTATIME-ICECAST
    nssm stop RASTATIME-ICECAST confirm

Step 6 ─ RASTATIME-WORKER
    nssm stop RASTATIME-WORKER confirm

Step 7 ─ RASTATIME-API
    nssm stop RASTATIME-API confirm

Step 8 ─ PostgreSQL + RabbitMQ  (only if a full system shutdown is intended)
    net stop postgresql-x64-17
    net stop RabbitMQ
```

> **⚠ Caution:** Steps 3–4 (stopping RASTATIME-PLAYOUT / -LIQUIDSOAP)
> interrupt on-air audio output immediately.  Coordinate with on-air
> staff before executing during a broadcast.

### 4.1 Using the Remove Scripts (Clean Uninstall)

To stop **and deregister** a service, use the T22.2 remove scripts in the
same order as the §4 shutdown (RASTATIME-LIQUIDSOAP has no remove
script — deregister it via nssm directly):

```powershell
powershell -File infra\nssm\remove-apache.ps1   -Force
powershell -File infra\nssm\remove-analyzer.ps1 -Force
powershell -File infra\nssm\remove-playout.ps1  -Force
nssm stop   RASTATIME-LIQUIDSOAP confirm
nssm remove RASTATIME-LIQUIDSOAP confirm
powershell -File infra\nssm\remove-icecast.ps1  -Force
powershell -File infra\nssm\remove-worker.ps1   -Force
powershell -File infra\nssm\remove-api.ps1      -Force
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
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

# d. If restart does not help, reinstall the service
powershell -File infra\nssm\install-api.ps1 -StartService
```

> `install-api.ps1` binds the API to 127.0.0.1 by default (since
> 2026-11-02; Apache proxies to it locally).  `-ApiHost 0.0.0.0` is only
> for a deliberately LAN-exposed API.

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
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

# b. Restart the worker
nssm restart RASTATIME-WORKER

# c. If crashing repeatedly, reinstall
powershell -File infra\nssm\install-worker.ps1 -StartService
```

---

### 5.3 Recovery: RASTATIME-PLAYOUT

**Symptoms:** On-air silence; `now_playing` not updating; Liquidsoap
telnet/connection errors in the playout log.

**Diagnosis:**
```powershell
Get-Service RASTATIME-PLAYOUT, RASTATIME-LIQUIDSOAP
Get-Content C:\rastatime\logs\playout-stdout.log -Tail 50
Get-Content C:\rastatime\logs\playout-stderr.log -Tail 50
Get-Content C:\rastatime\logs\liquidsoap-stdout.log -Tail 50
```

**Recovery steps:**
```powershell
# a. Ensure RASTATIME-API is healthy (playout reads schedule via DB/API)
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

# b. Check the Liquidsoap engine + rendered script
Test-Path C:\Tools\liquidsoap\liquidsoap.exe
Test-Path C:\Tools\liquidsoap\rastatime.liq

# c. Restart Liquidsoap first, then playout
nssm restart RASTATIME-LIQUIDSOAP
nssm restart RASTATIME-PLAYOUT

# d. If reinstalling the service: install-playout.ps1 does NOT set the
#    engine variables — re-apply the FULL AppEnvironmentExtra afterwards
#    (the 5 script-set vars plus RASTATIME_PLAYOUT_ENGINE=liquidsoap,
#    RASTATIME_MPV_LOG_LEVEL=warn,
#    RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0; `nssm set` replaces
#    the whole block — see MIGRATION.md §4.7).
powershell -File infra\nssm\install-playout.ps1 -StartService
```

> **⚠ Note:** Restarting playout causes a brief audio gap.  NSSM will
> restart it automatically on crash (5 s delay); manual intervention is
> only needed if the automatic restart loop is failing.

---

### 5.4 Recovery: RASTATIME-ICECAST  *(optional)*

**Symptoms:** Public stream URL unreachable; listeners get connection
refused on port 8000.  (DJ connections go to the Liquidsoap harbor on
8001, not to Icecast — for DJ problems check RASTATIME-LIQUIDSOAP.)

**Diagnosis:**
```powershell
Get-Service RASTATIME-ICECAST
Get-Content C:\rastatime\logs\icecast-nssm-stdout.log -Tail 30
# Also check the Icecast application log set in icecast.xml <logdir>
```

**Recovery steps:**
```powershell
# a. Restart Icecast (RASTATIME-STANDBY depends on it: stop that first,
#    otherwise Restart-Service refuses; Liquidsoap reconnects by itself)
Stop-Service RASTATIME-STANDBY
Restart-Service RASTATIME-ICECAST
Start-Service RASTATIME-STANDBY

# b. Verify stream endpoint
Invoke-WebRequest http://127.0.0.1:8000/ -UseBasicParsing

# c. If icecast.xml is misconfigured, edit it and restart
nssm restart RASTATIME-ICECAST

# d. Reinstall if service entry is corrupt
powershell -File infra\nssm\install-icecast.ps1 -StartService
```

> **Note:** RASTATIME-ICECAST failure does not affect the API, worker, or
> playout.  Studio audio continues through the local soundcard.
>
> Since 2026-10-24 the service runs Icecast 2.5.0 from `C:\Tools\Icecast-2.5.0`
> (NSSM Application + AppDirectory); 2.4.4 stays in `C:\Tools\Icecast` as the
> rollback together with `config/icecast.xml.2.4.4-backup`.  The live config
> needs `<charset>UTF-8</charset>` on every output mount - without it the 2.5
> Windows build sends empty ICY StreamTitle blocks.

### 5.5 Recovery: RabbitMQ boot loop `no_epmd_port` (seen 2026-10-24)

**Symptoms:** Service `RabbitMQ` shows *Running*, but nothing listens on
5672 (`Get-NetTCPConnection -State Listen | ? LocalPort -eq 5672` is
empty), `erl.exe` restarts every two minutes, the analyzer log repeats
`Connection to message queue failed ... Retrying in 5 seconds`, uploads
and podcast downloads stay unanalysed.  `C:\ProgramData\RabbitMQ\log\rabbit@RASTATIME.log`
ends every attempt with `epmd does not know us, re-registering rabbit`
and `BOOT FAILED ... {error,no_epmd_port}`.  Playout and stream are not
affected.

**Cause:** the node is named `rabbit@RASTATIME` (ErlSrv env
`RABBITMQ_NODENAME`), but the computer was renamed to `STUDIO`; the
rename only bites at the next reboot, when the node can no longer resolve
its own host name for the epmd lookup.

**Recovery (elevated):**
```powershell
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "127.0.0.1 RASTATIME","::1 RASTATIME"
Restart-Service RabbitMQ
# expect in the broker log: "started TCP listener on 127.0.0.1:5672"
# the analyzer reconnects by itself ("Listening for messages...")
```
Renaming the node instead would mean a fresh data directory with vhost,
user and permissions - not worth it.

---

## 6. Full Stack Reinstall

Use this procedure after a system migration, major Python upgrade, or if
NSSM service entries are corrupt.

```powershell
# 1. Stop and remove all services (preserve logs)
nssm stop   RASTATIME-LIQUIDSOAP confirm
nssm remove RASTATIME-LIQUIDSOAP confirm
powershell -File infra\nssm\remove-apache.ps1   -Force
powershell -File infra\nssm\remove-analyzer.ps1 -Force
powershell -File infra\nssm\remove-playout.ps1  -Force
powershell -File infra\nssm\remove-worker.ps1   -Force
powershell -File infra\nssm\remove-api.ps1      -Force
powershell -File infra\nssm\remove-icecast.ps1  -Force

# 2. Rebuild the Python venv if needed (see INSTALL.md §4 Step 4 for the
#    full sequence incl. psycopg2-binary + the editable backend installs)
python -m venv C:\rastatime\.venv
C:\rastatime\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Reinstall services in dependency order (details: INSTALL.md §4 Step 9)
powershell -File infra\nssm\install-api.ps1     -StartService
# Wait for API health before installing worker and playout:
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
powershell -File infra\nssm\install-worker.ps1   -StartService
powershell -File infra\nssm\install-icecast.ps1 `
    -IcecastExe 'C:\Tools\Icecast\bin\icecast.exe' -StartService
powershell -File backend\playout\config\nssm-install-liquidsoap.ps1
nssm start RASTATIME-LIQUIDSOAP
powershell -File infra\nssm\install-playout.ps1
# install-playout.ps1 sets no engine vars — re-apply the full
# AppEnvironmentExtra (MIGRATION.md §4.7), then start (engine first,
# then playout — see §3):
nssm start RASTATIME-PLAYOUT
powershell -File infra\nssm\install-analyzer.ps1 -StartService
powershell -File infra\nssm\install-apache.ps1   -StartService

# 4. Verify (status.ps1 covers all eight services incl. RASTATIME-STANDBY)
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
| RASTATIME-ANALYZER | 10 s | Waits out transient RabbitMQ hiccups |
| RASTATIME-APACHE | 5 s | Web UI; independent of the Python services |
| RASTATIME-LIQUIDSOAP | 5 s | Audio engine; throttled so a crash-loop doesn't hammer Icecast |
| RASTATIME-ICECAST | 15 s | Standalone; no rush |

If a service exits within its `AppThrottle` window (5–15 s depending on
the service), NSSM counts the start as failed and progressively
lengthens the restart delay.  Check the logs:

```powershell
Get-Content C:\rastatime\logs\api-stderr.log -Tail 100
```

---

## 8. Windows Boot Sequence

All mandatory services are configured `SERVICE_AUTO_START`.  On a cold
boot the expected sequence is:

1. Windows starts PostgreSQL and RabbitMQ (standard Windows services,
   start before NSSM services)
2. NSSM starts RASTATIME-API after its `AppThrottle` delay (~5 s)
3. NSSM starts RASTATIME-WORKER after its throttle (~15 s); the worker's
   health-check gate polls `http://127.0.0.1:8765/health` internally
4. NSSM starts RASTATIME-PLAYOUT after its throttle (~15 s); same gate
5. NSSM starts RASTATIME-ICECAST, RASTATIME-LIQUIDSOAP,
   RASTATIME-ANALYZER, and RASTATIME-APACHE independently

If the machine boots and services do not come up automatically, check:

```powershell
# NSSM logs its own start attempts in the Windows Application event log
Get-EventLog -LogName Application -Source nssm -Newest 20
```

---

## 9. Log File Reference

All log files live under `C:\rastatime\logs`.  NSSM rotates them at
10 MB per file; rotated generations **accumulate** (NSSM has no
file-count cap) — prune old rotations manually if disk space matters.

| Service | Stdout log | Stderr log |
|---|---|---|
| RASTATIME-API | `api-stdout.log` | `api-stderr.log` |
| RASTATIME-WORKER | `worker-stdout.log` | `worker-stderr.log` |
| RASTATIME-PLAYOUT | `playout-stdout.log` | `playout-stderr.log` |
| RASTATIME-ANALYZER | `analyzer-stdout.log` | `analyzer-stderr.log` |
| RASTATIME-APACHE | `apache-nssm-stdout.log` | `apache-nssm-stderr.log` |
| RASTATIME-LIQUIDSOAP | `liquidsoap-stdout.log` | `liquidsoap-stderr.log` |
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
