# INSTALL.md — RASTATIME Installation Guide

**Status:** Accepted  
**Task:** T23.1  
**Date:** 2026-04-30  
**Platform:** Windows 10 / Windows 11 / Windows Server 2022 (64-bit)

---

## 1. Overview

This guide walks a system operator through a complete RASTATIME installation
on a fresh Windows machine.  By the end you will have:

- All prerequisites installed and verified
- The RASTATIME codebase deployed to `C:\rastatime`
- A Python virtual environment with all dependencies
- A `libretime.conf` configuration file pointing at your PostgreSQL database
- All four NSSM Windows services registered and running
- A healthy API confirmed by `status.ps1`

Estimated time: **45–90 minutes** on a clean machine.

---

## 2. Prerequisites

Install these tools before starting.  The **bootstrap checker** will verify
them automatically (§4).

### 2.1 Python 3.11 or later

RASTATIME requires Python **3.11** as the minimum version.
Python 3.12 or 3.13 are supported.

1. Download the 64-bit installer from <https://www.python.org/downloads/>
2. Run the installer — tick **"Add Python to PATH"**
3. Verify:
   ```
   python --version
   # Expected: Python 3.11.x  (or higher)
   ```

> **Note:** Use the 64-bit build.  libVLC (ADR-002) requires a 64-bit
> Python process to load `libvlc.dll`.

### 2.2 PostgreSQL 17

RASTATIME uses PostgreSQL as its sole database (port **5432**).

1. Download from <https://www.postgresql.org/download/windows/>
2. Run the installer; note the superuser password you set
3. Ensure **"PostgreSQL Server"** is selected as a component
4. Add `<PostgreSQL>\bin` to PATH so `psql` and `pg_isready` are available
5. Verify:
   ```
   pg_isready -h 127.0.0.1 -p 5432
   # Expected: 127.0.0.1:5432 - accepting connections
   ```

### 2.3 VLC / libVLC (64-bit)

The RASTATIME playout engine uses **libVLC** (ADR-002) for audio output.
VLC must be installed in its standard location so `libvlc.dll` is present.

1. Download the **64-bit** installer from <https://www.videolan.org/vlc/>
2. Install to the default path: `C:\Program Files\VideoLAN\VLC\`
3. Verify:
   ```powershell
   Test-Path "C:\Program Files\VideoLAN\VLC\libvlc.dll"
   # Expected: True
   ```

> **Warning:** Do NOT install the 32-bit VLC build on a 64-bit machine.
> python-vlc will fail to load libvlc.dll and RASTATIME-PLAYOUT will not start.

### 2.4 NSSM — Non-Sucking Service Manager

NSSM (ADR-005) wraps the Python processes as Windows services.

1. Download from <https://nssm.cc/download>
2. Extract `nssm.exe` (64-bit) to a permanent location, e.g. `C:\nssm\`
3. Add `C:\nssm\` to the system PATH
4. Verify:
   ```
   nssm version
   # Expected: NSSM 2.24 (or later)
   ```

### 2.5 Apache 2.4 + PHP 8.3 (frontend)

The legacy PHP frontend runs on Apache 2.4 with `mod_fcgid` and PHP CGI.

> ⚠️  **Do NOT register Apache as a Windows service via `httpd -k install`.**
> RASTATIME wraps Apache in NSSM (like every other RASTATIME service) so
> service stop/restart times are bounded.  The native Apache service has
> no equivalent knob and routinely takes 15+ seconds to stop.

For the full host setup (binaries, `httpd.conf`, `php.ini`, NSSM wrap),
see **[INSTALL_APACHE.md](INSTALL_APACHE.md)**.

---

## 3. Directory Layout

RASTATIME uses `C:\rastatime` as its standard install root.

```
C:\rastatime\
├── backend\
│   ├── api\          — Django REST API (libretime_api)
│   └── shared\       — Shared library modules
├── config\
│   ├── libretime.conf   — Main RASTATIME configuration file
│   └── icecast.xml      — Icecast config (optional)
├── logs\             — All service log files (created automatically)
├── playout\          — Playout working files
└── .venv\            — Python virtual environment
```

> If you deploy to a non-standard path, pass `-InstallRoot D:\rastatime`
> to all `infra\nssm\install-*.ps1` and `remove-*.ps1` scripts.

---

## 4. Step-by-Step Installation

### Step 1 — Clone or deploy the codebase

```powershell
# Option A: clone from version control
git clone https://github.com/your-org/rastatime.git C:\rastatime

# Option B: extract a release archive
Expand-Archive rastatime-0.22.4.zip -DestinationPath C:\rastatime
```

### Step 2 — Run the bootstrap checker

The bootstrap checker verifies all required dependencies before you proceed.

```powershell
cd C:\rastatime
powershell -ExecutionPolicy Bypass -File infra\scripts\dev\bootstrap.ps1
```

Expected output: `All required dependencies found.`

Fix any `[FAIL]` items before continuing.

### Step 3 — Create the Python virtual environment

```powershell
cd C:\rastatime
python -m venv .venv
.venv\Scripts\Activate.ps1

# Verify the venv is active:
python --version
where python
# Should show: C:\rastatime\.venv\Scripts\python.exe
```

### Step 4 — Install Python dependencies

```powershell
# With the venv active:
pip install --upgrade pip
pip install -r requirements.txt

# Verify key packages are installed:
python -c "import django; print('Django', django.__version__)"
python -c "import waitress; print('Waitress', waitress.__version__)"
python -c "import vlc; print('python-vlc OK')"
```

> If `import vlc` fails: ensure VLC 64-bit is installed at
> `C:\Program Files\VideoLAN\VLC\` and the 64-bit Python venv is active.

### Step 5 — Create the configuration file

Copy the template and edit it for your environment:

```powershell
Copy-Item C:\rastatime\config\libretime.conf.template `
          C:\rastatime\config\libretime.conf
```

Open `C:\rastatime\config\libretime.conf` in a text editor and set at
minimum:

```ini
[database]
host     = 127.0.0.1
port     = 5432
name     = rastatime
user     = rastatime_user
password = <your-db-password>

[api]
host = 0.0.0.0
port = 8000

[general]
timezone = UTC
```

> The configuration file path is injected into every service via the
> `LIBRETIME_CONFIG_FILEPATH` environment variable (set automatically by
> the install scripts).

#### Secrets that MUST be changed before production

The template ships with placeholder values that are safe for a fresh
install on a local LAN but **must** be replaced before the host is
reachable from the public internet:

| Setting | Where | Why |
|---|---|---|
| `general.api_key` | `libretime.conf` | Authenticates inter-service API calls and the v1 legacy notify hook. |
| `general.secret_key` | `libretime.conf` | Django session / CSRF signing key. Must be at least 50 random chars. |
| `stream.internal_listener.password` | `libretime.conf` | Service-to-service password the playout uses to listen to `/main` and `/show` for relay. Default value is `change-me-internal-listener-secret`. Replace with a long random string (32+ chars). After changing, restart **both** `RASTATIME-APACHE` and `RASTATIME-PLAYOUT` — they each cache the value at startup. |
| `<source-password>` | `C:\rastatime\config\icecast.xml` | Icecast admin / relay / source password. Default value is `admin`. Replace with a long random string. |
| Master DJ password | `cc_pref` row `live_stream_master_password` (set via Settings → Streams in the frontend) | Authenticates the master-source DJ at `/main`. |

Generate strong values e.g. with PowerShell:

```powershell
[System.Convert]::ToBase64String((1..36 | ForEach-Object { Get-Random -Min 0 -Max 255 })) -replace '[+/=]', ''
```

### Step 6 — Create the PostgreSQL database

```powershell
# Connect as the PostgreSQL superuser:
psql -U postgres -h 127.0.0.1 -p 5432

-- Inside psql:
CREATE USER rastatime_user WITH PASSWORD '<your-db-password>';
CREATE DATABASE rastatime OWNER rastatime_user;
\q
```

### Step 7 — Run database migrations

```powershell
# With the venv active:
cd C:\rastatime\backend\api
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.prod"
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"
$env:PYTHONPATH = "C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime"

python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 8 — Create the log directory

The NSSM install scripts create this automatically, but you can create it
now to verify filesystem permissions:

```powershell
New-Item -ItemType Directory -Path C:\rastatime\logs -Force
```

### Step 9 — Install the Windows services

Run the T22.1 install scripts as **Administrator**, in dependency order:

```powershell
# Open an elevated PowerShell prompt, then:

# 9a — API (mandatory; start immediately)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-api.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\libretime.conf `
    -StartService

# Wait for the API health gate before continuing:
# (install-api.ps1 does NOT poll health automatically; check manually)
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
# Expected: StatusCode 200

# 9b — Worker (mandatory)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-worker.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\libretime.conf `
    -StartService

# 9c — Playout (mandatory)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-playout.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\libretime.conf `
    -VlcPluginPath "C:\Program Files\VideoLAN\VLC\plugins" `
    -StartService

# 9d — Icecast (optional — only if public streaming is required)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-icecast.ps1 `
    -InstallRoot C:\rastatime `
    -StartService
```

### Step 10 — Verify the installation

Run the T22.3 status helper to confirm all services are healthy:

```powershell
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\status.ps1
```

Expected output:
```
  RASTATIME-API     Running    HTTP 200 healthy
  RASTATIME-WORKER  Running
  RASTATIME-PLAYOUT Running
  RASTATIME-ICECAST Running  (or: Not installed  — optional)

  All mandatory services are Running.
```

If any mandatory service shows `Stopped` or `Not installed`, see §5
(Troubleshooting) or `docs\operator\RESTART_ORDER.md` §5 for per-service
recovery procedures.

---

## 5. Troubleshooting

### 5.1 API does not start — `libretime.conf` not found

```
Error: LIBRETIME_CONFIG_FILEPATH is not set or the file does not exist.
```

**Fix:** Ensure `C:\rastatime\config\libretime.conf` exists and the path
is correctly set in the NSSM service:
```powershell
nssm get RASTATIME-API AppEnvironmentExtra
```
Reinstall with the `-ConfigFile` parameter if necessary.

### 5.2 API does not start — database connection refused

```
django.db.OperationalError: could not connect to server: Connection refused
```

**Fix:** Ensure PostgreSQL is running and accepting connections on port 5432:
```powershell
Get-Service postgresql*
pg_isready -h 127.0.0.1 -p 5432
```
Check the `[database]` section of `libretime.conf` for correct credentials.

### 5.3 Playout does not start — libVLC not found

```
OSError: CDLL libvlc.dll could not be loaded
```

**Fix:** Confirm that 64-bit VLC is installed:
```powershell
Test-Path "C:\Program Files\VideoLAN\VLC\libvlc.dll"
```
Reinstall RASTATIME-PLAYOUT with the correct `-VlcPluginPath` if needed.

### 5.4 Worker or playout stay in `StartPending`

The health-check gate in the worker/playout entry points is waiting for
the API to return HTTP 200.  Check the API is healthy:
```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```
If the API is not healthy, resolve it first (see §5.2 and
`docs\operator\RESTART_ORDER.md` §5.1).

### 5.5 Status script shows wrong venv

The install scripts default to `C:\rastatime\.venv\Scripts\python.exe`.
If you used a different venv path, pass `-NssmExe` and inspect:
```powershell
nssm get RASTATIME-API Application
# Should show the python.exe from your venv
```

---

## 6. Post-Installation Checklist

After completing §4, verify each item:

- [ ] `status.ps1` shows all mandatory services `Running`
- [ ] `http://127.0.0.1:8000/health` returns HTTP 200
- [ ] `http://127.0.0.1:8000/api/v2/schema/swagger-ui` loads the API docs
- [ ] `C:\rastatime\logs\` contains `api-stdout.log` (non-empty after first request)
- [ ] `pg_isready -h 127.0.0.1 -p 5432` succeeds
- [ ] All services survive a `Restart-Computer` (auto-start verified)
- [ ] Soundcard settings are visible in the RASTATIME web UI (Settings → Soundcard)
- [ ] (Optional) Icecast stream accessible at `http://localhost:8001/`

---

## 7. Updating an Existing Installation

To update RASTATIME to a new version:

```powershell
# 1. Stop services in reverse order
nssm stop RASTATIME-ICECAST confirm   # optional
nssm stop RASTATIME-PLAYOUT confirm
nssm stop RASTATIME-WORKER  confirm
nssm stop RASTATIME-API     confirm

# 2. Pull the new code
cd C:\rastatime
git pull

# 3. Update Python dependencies
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Run any new migrations
cd C:\rastatime\backend\api
python manage.py migrate

# 5. Restart services in dependency order
nssm start RASTATIME-API
# (wait for health)
nssm start RASTATIME-WORKER
nssm start RASTATIME-PLAYOUT
nssm start RASTATIME-ICECAST   # optional

# 6. Verify
powershell -File C:\rastatime\infra\nssm\status.ps1
```

---

## 8. Uninstalling RASTATIME

```powershell
# Remove services (preserves logs and config)
powershell -File infra\nssm\remove-playout.ps1 -Force
powershell -File infra\nssm\remove-worker.ps1  -Force
powershell -File infra\nssm\remove-api.ps1     -Force
powershell -File infra\nssm\remove-icecast.ps1 -Force

# Optional: purge logs
powershell -File infra\nssm\remove-api.ps1 -Force -PurgeLogs
# ... repeat for each service

# Optional: drop the database
psql -U postgres -c "DROP DATABASE rastatime;"
psql -U postgres -c "DROP USER rastatime_user;"

# Optional: delete the install directory
Remove-Item -Recurse -Force C:\rastatime
```

---

## 9. Related Documentation

| Document | Description |
|---|---|
| `docs\architecture\SERVICE_TOPOLOGY.md` | Service definitions, ports, log layout (T21.1) |
| `docs\operator\RESTART_ORDER.md` | Startup / shutdown / recovery procedures (T22.4) |
| `infra\nssm\install-*.ps1` | Service install scripts (T22.1) |
| `infra\nssm\remove-*.ps1` | Service remove scripts (T22.2) |
| `infra\nssm\status.ps1` | Live status and health helper (T22.3) |
| `infra\scripts\dev\bootstrap.ps1` | Dependency checker (T3.1) |
