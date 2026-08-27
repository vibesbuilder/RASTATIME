# CRASH_RECOVERY.md — RASTATIME Crash Recovery

**Status:** Accepted  
**Task:** T23.2  
**Date:** 2026-04-30

---

## 1. Overview

This document covers recovery from unexpected failures: service crashes,
machine reboots, database corruption, and full system loss.  It complements
the planned outage procedures in `docs\operator\RESTART_ORDER.md`.

**First action in any crash scenario:**

```powershell
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\status.ps1
```

The output of `status.ps1` covers all seven RASTATIME services — SCM
status plus live HTTP probes for the API (8765), Apache (80) and
Icecast (8000).  Use it to determine which recovery path applies.

---

## 2. Crash Taxonomy

| Scenario | Symptom | Section |
|---|---|---|
| Single service crashed and did not restart | SCM status `Stopped`; NSSM retries exhausted | §3 |
| Service crash-loops (restarts < 30 s intervals) | SCM oscillates; logs show repeated start/stop | §4 |
| Machine rebooted unexpectedly | All services `Stopped` on reconnect | §5 |
| PostgreSQL down / unreachable | API returns 5xx; worker/playout log DB errors | §6 |
| Database corrupted or data loss | `psql` errors; missing rows in schedule | §7 |
| Full system loss (hardware failure) | Complete reinstall from backup | §8 |

---

## 3. Single Service Crash (No Auto-Restart)

NSSM is configured to restart each service automatically.  If a service
is `Stopped` and did not restart, NSSM's throttle limit was reached.

### 3.1 Assess

```powershell
# 1. Full stack status:
powershell -File C:\rastatime\infra\nssm\status.ps1

# 2. Check NSSM event log for throttle messages:
Get-EventLog -LogName Application -Source nssm -Newest 20 |
    Select-Object TimeGenerated, Message | Format-List
```

### 3.2 Read the logs

```powershell
# Replace 'api' with 'worker', 'playout', or 'icecast' as appropriate:
Get-Content C:\rastatime\logs\api-stderr.log  -Tail 50
Get-Content C:\rastatime\logs\api-stdout.log  -Tail 20
```

### 3.3 Restart the service

```powershell
nssm restart RASTATIME-API      # substitute the affected service
```

If the service restarts successfully, monitor for 60 seconds:

```powershell
# Watch SCM status:
1..12 | ForEach-Object {
    Start-Sleep 5
    (Get-Service RASTATIME-API).Status
}
```

### 3.4 Reinstall if the service entry is corrupt

```powershell
powershell -File C:\rastatime\infra\nssm\install-api.ps1 -StartService
```

See `docs\operator\RESTART_ORDER.md` §5 for per-service recovery details.

---

## 4. Service Crash-Loop

A crash-loop means the service starts, crashes within seconds, and NSSM
restarts it again — usually due to a bad configuration or a missing
dependency.

### 4.1 Identify the root cause

```powershell
# Stop the crash-looping service to prevent repeated failures:
nssm stop RASTATIME-API confirm

# Read the stderr log — the last error before exit is the clue:
Get-Content C:\rastatime\logs\api-stderr.log -Tail 100
```

**Common causes:**

| Log message | Cause | Fix |
|---|---|---|
| `could not connect to server` | PostgreSQL unreachable (port 5432) | Start PostgreSQL; check `libretime.conf` |
| `CDLL libvlc.dll could not be loaded` | Playout fell back to the legacy VLC engine | Verify `RASTATIME_PLAYOUT_ENGINE=liquidsoap` in the playout `AppEnvironmentExtra` (MIGRATION.md §4.7) — VLC is no longer part of the stack |
| `No module named 'libretime_api'` | PYTHONPATH incorrect | Reinstall service with `install-api.ps1` |
| `FileNotFoundError: libretime.conf` | Config file missing or wrong path | Copy from backup; check `LIBRETIME_CONFIG_FILEPATH` |
| `django.core.exceptions.ImproperlyConfigured` | Missing env var or bad settings | Check `DJANGO_SETTINGS_MODULE` in NSSM env |

### 4.2 Fix and restart

After resolving the root cause:

```powershell
nssm start RASTATIME-API
# Monitor for 30 s:
Start-Sleep 30
(Get-Service RASTATIME-API).Status
```

---

## 5. Unexpected Machine Reboot

After an unplanned reboot (power failure, Windows Update, etc.):

### 5.1 Verify auto-start worked

```powershell
powershell -File C:\rastatime\infra\nssm\status.ps1
```

All mandatory services should be `Running` within ~30 seconds of login
(NSSM auto-starts them with configured throttle delays).

### 5.2 If services did not auto-start

Check NSSM start type:

```powershell
nssm get RASTATIME-API Start
# Expected: SERVICE_AUTO_START
```

If not `SERVICE_AUTO_START`, re-register the service:

```powershell
powershell -File C:\rastatime\infra\nssm\install-api.ps1 -StartService
```

### 5.3 Startup order after a cold boot

If services started but in the wrong order, the worker or playout may have
timed out waiting for the API health gate.  Stop and restart in the correct
sequence:

```powershell
nssm stop RASTATIME-PLAYOUT confirm
nssm stop RASTATIME-WORKER  confirm

# Ensure API is healthy first:
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

nssm start RASTATIME-WORKER
nssm start RASTATIME-PLAYOUT
```

See `docs\operator\RESTART_ORDER.md` §3 for the full startup sequence.

---

## 6. PostgreSQL Unreachable

RASTATIME-API, RASTATIME-WORKER, and RASTATIME-PLAYOUT all require
PostgreSQL (port **5432**).  If PostgreSQL goes down, all three services
will fail.

### 6.1 Assess

```powershell
Get-Service postgresql*
pg_isready -h 127.0.0.1 -p 5432
```

### 6.2 Restart PostgreSQL

```powershell
Start-Service (Get-Service postgresql* | Select-Object -First 1).Name
pg_isready -h 127.0.0.1 -p 5432
# Expected: 127.0.0.1:5432 - accepting connections
```

### 6.3 Restart RASTATIME services

Once PostgreSQL is accepting connections, restart in dependency order:

```powershell
nssm restart RASTATIME-API
# Wait for health:
Start-Sleep -Seconds 8
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

nssm restart RASTATIME-WORKER
nssm restart RASTATIME-PLAYOUT
```

---

## 7. Database Corruption or Data Loss

If `psql` reports errors or expected rows are missing, restore from backup.

### 7.1 Assess the damage

```powershell
psql -U rastatime -h 127.0.0.1 -p 5432 -d rastatime -c "\dt"
# Look for missing tables or unexpected errors
```

### 7.2 Stop all services

```powershell
nssm stop RASTATIME-PLAYOUT confirm
nssm stop RASTATIME-WORKER  confirm
nssm stop RASTATIME-API     confirm
```

### 7.3 Restore from backup

See `docs\operator\BACKUP.md` §7 for the full restore procedure.

```powershell
# Quick reference — plain SQL restore:
$env:PGPASSWORD = "postgres-superuser-password"
psql -U postgres -h 127.0.0.1 -p 5432 -c "DROP DATABASE IF EXISTS rastatime;"
psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE rastatime OWNER rastatime;"
$env:PGPASSWORD = "rastatime-password"
psql -U rastatime -h 127.0.0.1 -p 5432 -d rastatime `
     -f C:\rastatime-backups\db\<latest-backup>.sql
Remove-Item Env:\PGPASSWORD
```

### 7.4 Apply any migrations missed since the backup

```powershell
cd C:\rastatime\backend\api
$env:DJANGO_SETTINGS_MODULE    = "libretime_api.settings.prod"
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"
$env:PYTHONPATH                = "C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime"
python libretime_api\manage.py migrate
```

### 7.5 Restart and verify

```powershell
nssm start RASTATIME-API
Start-Sleep -Seconds 8
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
nssm start RASTATIME-WORKER
nssm start RASTATIME-PLAYOUT

powershell -File C:\rastatime\infra\nssm\status.ps1
```

---

## 8. Full System Loss (Hardware Failure)

Recovery from a complete hardware failure requires a new machine plus
the latest backup.

### 8.1 Provision the new machine

Install **all** prerequisites on the replacement hardware following
`docs\operator\INSTALL.md` §2 (the full set — not a subset):

- Windows prep (Smart App Control OFF, static IP), VC++ Redistributable
- Python 3.11+ (64-bit), PostgreSQL 17 (port 5432)
- RabbitMQ 4.x + Erlang OTP (vhost `/rastatime`)
- Liquidsoap 2.4.4 (`C:\Tools\liquidsoap`)
- Apache 2.4 + PHP 8.3 (`C:\Tools\Apache24` / `C:\Tools\PHP`)
- Icecast 2.4.4 (`C:\Tools\Icecast`), FFmpeg (`C:\ffmpeg\bin`), NSSM

(VLC is **not** required — Liquidsoap is the production engine.)

### 8.2 Restore the codebase

```powershell
# Clone from version control (use the same git tag as the backed-up database):
git clone https://github.com/your-org/rastatime.git C:\rastatime
cd C:\rastatime
git checkout v0.22.4    # match the version that produced the backup
```

### 8.3 Restore configuration

```powershell
New-Item -ItemType Directory -Path C:\rastatime\config -Force
Copy-Item <backup-drive>\config\libretime.conf.* `
          C:\rastatime\config\libretime.conf

# Edit libretime.conf if the new machine has a different DB host/IP
```

### 8.4 Restore the database

```powershell
# Create the DB user and database:
psql -U postgres -h 127.0.0.1 -p 5432 -c `
    "CREATE USER rastatime WITH PASSWORD '<password>';"
psql -U postgres -h 127.0.0.1 -p 5432 -c `
    "CREATE DATABASE rastatime OWNER rastatime;"

# Restore:
$env:PGPASSWORD = "rastatime-password"
psql -U rastatime -h 127.0.0.1 -p 5432 -d rastatime `
     -f <backup-drive>\db\<latest-backup>.sql
Remove-Item Env:\PGPASSWORD
```

### 8.5 Rebuild the venv and install services

```powershell
cd C:\rastatime
python -m venv .venv
.venv\Scripts\Activate.ps1
# Full dependency sequence per INSTALL.md §4 Step 4:
pip install -r requirements.txt
pip install psycopg2-binary
pip install -e backend/shared
pip install -e backend/api-client
pip install -e backend/api
pip install -e backend/playout
pip install -e backend/analyzer

# Install ALL 7 services (as Administrator) — full sequence incl. the
# playout engine env vars and the Liquidsoap service:
# see INSTALL.md §4 Step 9 (9a-9h).
```

### 8.6 Verify

```powershell
powershell -File C:\rastatime\infra\nssm\status.ps1
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
```

---

## 9. Emergency Contacts and Escalation

*(Fill in site-specific contact information here.)*

| Role | Contact | Notes |
|---|---|---|
| Primary operator | — | First responder for service issues |
| DBA / sysadmin | — | PostgreSQL and OS-level issues |
| RASTATIME maintainer | — | Code defects, migration failures |

---

## 10. Related Documentation

| Document | Description |
|---|---|
| `docs\operator\RESTART_ORDER.md` | Per-service recovery procedures (T22.4) |
| `docs\operator\BACKUP.md` | Database and config backup / restore |
| `docs\operator\UPGRADE.md` | Planned upgrade procedure |
| `docs\operator\INSTALL.md` | Fresh installation guide |
| `infra\nssm\status.ps1` | Live health check helper (T22.3) |
| `infra\nssm\install-*.ps1` | Service reinstallation scripts (T22.1) |
