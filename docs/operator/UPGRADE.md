# UPGRADE.md — RASTATIME Upgrade Procedure

**Status:** Accepted  
**Task:** T23.2  
**Date:** 2026-04-30  
**Applies to:** All RASTATIME versions from 0.20.x onward

---

## 1. Overview

> **Autoloading note (2026-10-13).** Legacy PHP classes under
> `frontend\legacy\application\common\` are found through the Composer
> classmap. After deploying code that adds or renames a class there, run
> `php C:\Tools\composer\composer.phar dump-autoload` in `frontend\legacy`
> (services, controllers, forms and models are autoloaded by Zend and need
> nothing). Missing step = `Class "Application_Common_..." not found`.

> **Brand stage B (2026-10-29).** The Python packages, commands,
> environment variables and the configuration file carry the product name
> since 2026-10-29: `rastatime_api` / `rastatime_playout` /
> `rastatime_analyzer` / `rastatime_shared` / `rastatime_api_client`,
> `rastatime-analyzer.exe`, `RASTATIME_CONFIG_FILEPATH`,
> `config\rastatime.conf`, gettext domain `rastatime`.  Upgrading an
> installation from before that date:
> 1. `pip uninstall -y libretime-api libretime-playout libretime-analyzer
>    libretime-shared libretime-api-client` (stop `RASTATIME-ANALYZER` first,
>    its EXE is locked while running), then the five editable installs from
>    Step 3 - they now register as `rastatime-*`.
> 2. Rename `config\libretime.conf` to `config\rastatime.conf`.
> 3. nssm: `-m rastatime_api.waitress_serve`, `-m rastatime_playout`,
>    `rastatime-analyzer.exe`, `DJANGO_SETTINGS_MODULE=rastatime_api.settings.prod`,
>    `RASTATIME_CONFIG_FILEPATH=...` for API, PLAYOUT, WORKER and ANALYZER
>    (the install scripts under `infra\nssm\` write the new values).
> 4. `php C:\Tools\composer\composer.phar dump-autoload` in `frontend\legacy`
>    (renamed PHP classes); every browser session is logged out once (new
>    session namespace).
>
> **Hard cut since 2026-11-01:** only the new names are read.  The former
> `libretime_*` import names, `-m libretime_*`, `libretime-analyzer.exe`,
> `LIBRETIME_*` variables and a `libretime.conf` are ignored (a bridge kept
> them working from 2026-10-29 to 2026-11-01; its logs recorded no use).
> A service still started with a former name fails at import time, a
> `LIBRETIME_*` variable is simply not read: finish steps 1-4 above first.

> **Third-party components** (Apache, PHP, PostgreSQL, Python packages,
> Liquidsoap, Icecast, ffmpeg ...) are not covered here: see
> `docs\operator\COMPONENTS.md` for the inventory, the update classes and
> the monthly maintenance window, and run `python scripts\update_check.py`
> to compare the installed versions with upstream (2026-10-09).

This document describes how to upgrade an existing RASTATIME installation
to a newer version with minimal downtime.  The upgrade procedure covers:

- Pre-upgrade backup and checklist
- Stopping all RASTATIME services in the correct order
- Deploying the new code
- Updating Python dependencies
- Applying database schema migrations (`manage.py migrate`)
- Restarting services and verifying health
- Rolling back if something goes wrong

**Estimated downtime:** 5–15 minutes for a routine release.  Database
migrations with large table rewrites may take longer — check the release
notes before starting.

---

## 2. Pre-Upgrade Checklist

Complete every item before touching the running system.

- [ ] Read the release notes for the target version; note any breaking
      changes, migration warnings, or manual steps
- [ ] Back up the PostgreSQL database (see `docs\operator\BACKUP.md` §3)
- [ ] Back up `C:\rastatime\config\rastatime.conf`
- [ ] Note the current version: check `CHANGELOG.md` or `git describe`
- [ ] Confirm a maintenance window with on-air staff (upgrade stops audio)
- [ ] Verify you have an elevated (Administrator) PowerShell prompt ready
- [ ] Confirm you can reach the server console if a remote session drops

---

## 3. Upgrade Steps

### Step 1 — Stop all RASTATIME services

Stop services in reverse dependency order to avoid errors from missing
upstream processes.

```powershell
# As Administrator:
nssm stop RASTATIME-APACHE     confirm
nssm stop RASTATIME-ANALYZER   confirm
nssm stop RASTATIME-PLAYOUT    confirm  # ⚠ stops schedule-driven playout
nssm stop RASTATIME-LIQUIDSOAP confirm  # ⚠ stops on-air audio
nssm stop RASTATIME-ICECAST    confirm
nssm stop RASTATIME-WORKER     confirm
nssm stop RASTATIME-API        confirm

# Verify all are stopped:
Get-Service RASTATIME-* | Select-Object Name, Status
# Expected: all show Status = Stopped
```

### Step 2 — Deploy the new code

**Option A — Git pull (recommended):**

```powershell
cd C:\rastatime
git fetch origin
git status               # confirm working tree is clean
git pull origin main     # or the target release tag
git describe --tags      # confirm the new version
```

**Option B — Release archive:**

```powershell
# Extract the new archive over the existing install directory:
Expand-Archive rastatime-0.23.x.zip -DestinationPath C:\rastatime -Force
```

### Step 3 — Update Python dependencies

```powershell
cd C:\rastatime
# A fresh Windows has execution policy Restricted - allow scripts for
# this window only, or Activate.ps1 is refused:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip   # pip cannot replace its own pip.exe on Windows
pip install -r requirements.txt
# The root requirements.txt holds only python-vlc + pytest — Django,
# Waitress and psycopg2 come from the editable backend installs.
# Editable installs pick up code changes automatically; re-run them
# only if a pyproject.toml changed (full sequence: INSTALL.md §4 Step 4).

# Verify key packages after update:
python -c "import django; print('Django', django.__version__)"
python -c "import importlib.metadata as m; print('Waitress', m.version('waitress'))"
```

> If the venv must be **recreated**, `pip install -r requirements.txt`
> alone is NOT enough — run the full dependency sequence from
> INSTALL.md §4 Step 4 (requirements.txt + `psycopg2-binary` + the five
> editable backend installs), or no service will start:
> ```powershell
> deactivate
> Remove-Item -Recurse -Force C:\rastatime\.venv
> python -m venv C:\rastatime\.venv
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # fresh Windows: policy Restricted
> C:\rastatime\.venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> pip install psycopg2-binary
> pip install -e backend/shared
> pip install -e backend/api-client
> pip install -e backend/api
> pip install -e backend/playout
> pip install -e backend/analyzer
> ```

### Step 4 — Apply database migrations

```powershell
cd C:\rastatime\backend\api

$env:DJANGO_SETTINGS_MODULE     = "rastatime_api.settings.prod"
$env:RASTATIME_CONFIG_FILEPATH  = "C:\rastatime\config\rastatime.conf"
$env:PYTHONPATH                 = "C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime"

# Show pending migrations before applying:
python rastatime_api\manage.py showmigrations --plan | Where-Object { $_ -match '\[ \]' }

# Apply:
python rastatime_api\manage.py migrate

# Confirm no pending migrations remain:
python rastatime_api\manage.py migrate --check
# Expected: exit code 0, "No migrations to apply."
```

> `manage.py` lives at `backend\api\rastatime_api\manage.py` — the
> commands above are run from `backend\api`.

> **Warning:** If the migration output mentions locking a large table
> (e.g. `cc_schedule`, `cc_files`), ensure no external clients are
> connected to the database during this step.

### Step 5 — Restart services in dependency order

(There is no `collectstatic` step — the prod settings define no
`STATIC_ROOT` and none is needed.)

```powershell
# Start API first:
nssm start RASTATIME-API

# Wait for health gate (poll until HTTP 200):
$deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing -TimeoutSec 4
        if ($r.StatusCode -eq 200) { Write-Host "API healthy."; break }
    } catch {}
} while ((Get-Date) -lt $deadline)

# Start remaining services (engine before playout — RESTART_ORDER.md §3):
nssm start RASTATIME-WORKER
nssm start RASTATIME-ICECAST
nssm start RASTATIME-LIQUIDSOAP
nssm start RASTATIME-PLAYOUT
# (the playout's startup render rewrites rastatime.liq; if it logs
#  "content changed", restart RASTATIME-LIQUIDSOAP once afterwards)
nssm start RASTATIME-ANALYZER
nssm start RASTATIME-APACHE
```

### Step 6 — Verify the upgrade

```powershell
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\status.ps1
```

Expected:
- All mandatory services: `Running`
- API health: `HTTP 200  OK — API is healthy`
- No errors in `C:\rastatime\logs\api-stderr.log` (check last 20 lines)

```powershell
Get-Content C:\rastatime\logs\api-stderr.log -Tail 20
Get-Content C:\rastatime\logs\worker-stderr.log -Tail 20
```

---

## 4. Rollback Procedure

If the upgrade causes an unrecoverable error, roll back to the previous
version.

### 4.1 Stop services

```powershell
nssm stop RASTATIME-APACHE     confirm
nssm stop RASTATIME-ANALYZER   confirm
nssm stop RASTATIME-PLAYOUT    confirm
nssm stop RASTATIME-LIQUIDSOAP confirm
nssm stop RASTATIME-ICECAST    confirm
nssm stop RASTATIME-WORKER     confirm
nssm stop RASTATIME-API        confirm
```

### 4.2 Restore the previous code

**Git:**
```powershell
cd C:\rastatime
git log --oneline -10          # find the previous commit hash
git checkout <previous-hash>   # or: git checkout v0.22.4
```

**Archive:**
```powershell
Expand-Archive rastatime-0.22.4.zip -DestinationPath C:\rastatime -Force
```

### 4.3 Restore the database (if migrations were applied)

If `manage.py migrate` ran new migrations, restore from the pre-upgrade
backup (see `docs\operator\BACKUP.md` §4):

```powershell
# Stop all services if still running
# Then restore:
psql -U postgres -c "DROP DATABASE rastatime;"
psql -U postgres -c "CREATE DATABASE rastatime OWNER rastatime;"
psql -U postgres -d rastatime -f C:\rastatime\backups\pre-upgrade-rastatime.sql
```

### 4.4 Reinstall the venv for the old version

```powershell
Remove-Item -Recurse -Force C:\rastatime\.venv
python -m venv C:\rastatime\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # fresh Windows: policy Restricted
C:\rastatime\.venv\Scripts\Activate.ps1
# Full dependency sequence (INSTALL.md §4 Step 4) — requirements.txt
# alone is not enough:
pip install -r requirements.txt
pip install psycopg2-binary
pip install -e backend/shared
pip install -e backend/api-client
pip install -e backend/api
pip install -e backend/playout
pip install -e backend/analyzer
```

### 4.5 Restart services

```powershell
nssm start RASTATIME-API
nssm start RASTATIME-WORKER
nssm start RASTATIME-ICECAST
nssm start RASTATIME-LIQUIDSOAP
nssm start RASTATIME-PLAYOUT
nssm start RASTATIME-ANALYZER
nssm start RASTATIME-APACHE
powershell -File C:\rastatime\infra\nssm\status.ps1
```

---

## 5. Version Compatibility Notes

| Component | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | 64-bit; 3.12/3.13 supported |
| PostgreSQL | 14 | 17 recommended; `pg_dump` for migration between PG versions |
| Liquidsoap | 2.4.4 | at `C:\Tools\liquidsoap\` (production playout engine) |
| RabbitMQ | 4.x | requires Erlang OTP; vhost `/rastatime` |
| NSSM | 2.24 | 64-bit build |
| Django | pinned in `requirements.txt` | check release notes for ORM changes |

---

## 6. Related Documentation

| Document | Description |
|---|---|
| `docs\operator\BACKUP.md` | Database and config backup procedures |
| `docs\operator\CRASH_RECOVERY.md` | Recovery from unexpected crashes |
| `docs\operator\RESTART_ORDER.md` | Service startup/shutdown order |
| `docs\operator\INSTALL.md` | Fresh installation guide |
| `infra\nssm\status.ps1` | Live health check helper |
