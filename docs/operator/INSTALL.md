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
- A `rastatime.conf` configuration file pointing at your PostgreSQL database
- All seven NSSM Windows services registered and running
- A rendered Liquidsoap production script (`C:\Tools\liquidsoap\rastatime.liq`)
- A healthy API confirmed by `status.ps1`

Estimated time: **2–4 hours** on a clean machine (incl. RabbitMQ,
Apache/PHP, Icecast and Liquidsoap).

---

## 2. Prerequisites

Install these tools before starting.  The **bootstrap checker** will verify
them automatically (§4).

### 2.0 Windows preparation

On a fresh Windows machine, do these two things before installing anything:

1. **Turn Smart App Control OFF** (Windows Security → App & browser control).
   Enforced SAC blocks unsigned binaries such as `httpd.exe` and
   `php-cgi.exe` — they exit silently with no error.  SAC can only be
   switched off interactively, and the change is irreversible without
   reinstalling Windows, so do it first.
2. **Assign a static IP address** (or a DHCP reservation) before any
   config file references the machine's address.  A silent DHCP lease
   change breaks stream URLs and configs and is painful to debug.

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

> **Note:** Use the 64-bit build.  The production stack (PostgreSQL,
> psycopg2, Liquidsoap tooling) is 64-bit throughout.

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

### 2.3 Liquidsoap 2.4.6

Liquidsoap has been the production playout engine since the 2026-05
cutover and the only one since 2026-09-10.  **VLC/libVLC and mpv are
not required** — their legacy code paths were deleted.

1. Download the official Windows build **2.4.6** (`liquidsoap-2.4.6-win64.zip`
   from the savonet/liquidsoap GitHub releases; it ships ffmpeg, portaudio
   and the Stereo Tool plugin) and unzip it to `C:\Tools\liquidsoap\`
   so that `C:\Tools\liquidsoap\liquidsoap.exe` exists.  The rendered
   scripts `rastatime.liq` / `standby.liq` live in the same folder.
2. Verify:
   ```powershell
   & C:\Tools\liquidsoap\liquidsoap.exe --version
   # Expected: Liquidsoap 2.4.6
   ```

> The production script `C:\Tools\liquidsoap\rastatime.liq` is rendered
> from a template plus database settings later in the install (§4 Step 9).

### 2.4 RabbitMQ 4.x + Erlang OTP

RabbitMQ is a **required** prerequisite: the analyzer service consumes a
RabbitMQ queue, and the PHP frontend dispatches a message to it for
every uploaded media file.  Without RabbitMQ, uploads stay at
"Pending Import" forever.

1. Install Erlang OTP (64-bit), then RabbitMQ 4.x
2. RASTATIME expects vhost `/rastatime` on port **5672** with the
   user/password from the `rabbitmq:` section of `rastatime.conf`
3. Verify:
   ```powershell
   Get-Service RabbitMQ
   # Expected: Running
   ```

> **Windows service quirk:** if the installer ran as a normal user, the
> LocalSystem service can crash on start.  Re-register the service with
> an explicit base directory:
> ```powershell
> $env:RABBITMQ_BASE = "C:\ProgramData\RabbitMQ"
> rabbitmq-service.bat remove
> rabbitmq-service.bat install
> ```

### 2.5 NSSM — Non-Sucking Service Manager

NSSM (ADR-005) wraps the Python processes as Windows services.

1. Download from <https://nssm.cc/download>
2. Extract `nssm.exe` (64-bit) to `C:\Tools\nssm\` — the install scripts
   fall back to `C:\Tools\nssm\nssm.exe` when NSSM is not on PATH
3. Add `C:\Tools\nssm\` to the system PATH — the fallback only covers
   the install/remove/status scripts; the bare `nssm` commands later in
   this guide (§4 Step 9d/9h, §5, §7, §8) need it on PATH
4. Verify:
   ```
   nssm version
   # Expected: NSSM 2.24 (or later)
   ```

### 2.6 Apache 2.4 + PHP 8.5 (frontend)

The legacy PHP frontend runs on Apache 2.4 with `mod_fcgid` and PHP CGI.

> ⚠️  **Do NOT register Apache as a Windows service via `httpd -k install`.**
> RASTATIME wraps Apache in NSSM (like every other RASTATIME service) so
> service stop/restart times are bounded.  The native Apache service has
> no equivalent knob and routinely takes 15+ seconds to stop.

For the full host setup (binaries, `httpd.conf`, `php.ini`, NSSM wrap),
see **[INSTALL_APACHE.md](INSTALL_APACHE.md)**.  Production layout:
Apache Lounge 2.4.x Win64 at `C:\Tools\Apache24`, PHP 8.5 NTS x64 at
`C:\Tools\PHP`.

> **Install the latest Visual C++ Redistributable (x64) FIRST.**  The
> Apache Lounge VS18 build and PHP 8.5 both depend on it — without it
> `httpd.exe` / `php-cgi.exe` exit silently with no error message.

**Composer 2** installs the frontend's PHP packages (§4 Step 4b).  Download
`composer.phar` from https://getcomposer.org/download/ to
`C:\Tools\composer\composer.phar` and verify:
```powershell
& C:\Tools\PHP\php.exe C:\Tools\composer\composer.phar --version
# Expected: Composer version 2.x
```
> The release frontend zip (`rastatime-frontend-legacy-vX.Y.Z.zip`) already
> contains `vendor\`; Composer is only needed for a checkout from git.

Beyond the base setup in INSTALL_APACHE.md, `httpd.conf` needs:

1. `LoadModule` lines for `rewrite_module`, `proxy_module`, and
   `proxy_http_module`
2. The ZF1 front-controller rewrite in the `<Directory>` block of the
   frontend public dir — the `HTTP_AUTHORIZATION` line is essential
   (mod_fcgid strips the Authorization header otherwise, breaking
   Basic-auth endpoints such as `icecast-listener-allow`):
   ```apache
   RewriteEngine On
   RewriteRule ^ - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
   RewriteCond %{REQUEST_FILENAME} -s [OR]
   RewriteCond %{REQUEST_FILENAME} -l [OR]
   RewriteCond %{REQUEST_FILENAME} -d
   RewriteRule ^.*$ - [NC,L]
   RewriteRule ^.*$ index.php [NC,L]
   ```
3. A server-scope reverse proxy to the API:
   ```apache
   ProxyPreserveHost On
   ProxyPass        /api/v2/   http://127.0.0.1:8765/api/v2/
   ProxyPassReverse /api/v2/   http://127.0.0.1:8765/api/v2/
   ProxyPass        /api-auth/ http://127.0.0.1:8765/api-auth/
   ProxyPassReverse /api-auth/ http://127.0.0.1:8765/api-auth/
   ```

### 2.7 Icecast 2.5.0 (streaming)

Production runs Icecast **2.5.0** (since 2026-10-24).  DJ passwords are
not checked by Icecast at all: the Liquidsoap harbor asks PLAYOUT, which
asks the web application (Settings → Streams).  `icecast.xml` only
carries the source/relay/admin passwords, the output mounts with their
`-standby` fallbacks and, optionally, 2.5 `<event-bindings>` that report
source connects to PLAYOUT.  Start from `config\icecast.xml.example`;
keep `<charset>UTF-8</charset>` on every output mount (the Windows build
sends empty ICY titles without it).

1. Download the Icecast 2.5.0 Windows build from icecast.org / xiph.org
   and verify its SHA512 against `SHA512SUMS.txt` (the installer is unsigned)
2. Install or copy the tree to `C:\Tools\Icecast\` so that
   `C:\Tools\Icecast\bin\icecast.exe` exists with its `web\` and
   `admin\` siblings under `C:\Tools\Icecast\`
3. Register the service later (§4 Step 9) with
   `install-icecast.ps1 -IcecastExe 'C:\Tools\Icecast\bin\icecast.exe'`
   — the script's built-in default points at `C:\Program Files\Icecast`,
   which is NOT where production installs it

### 2.8 FFmpeg

The analyzer uses FFmpeg for the ReplayGain and cue-point pipeline
steps; the playout keeps it on PATH for the legacy fallback paths.

1. Extract an FFmpeg release build so that `C:\ffmpeg\bin\ffmpeg.exe`
   exists — the service install scripts prepend exactly `C:\ffmpeg\bin`
   to each service's `PATH`
2. Verify:
   ```powershell
   & C:\ffmpeg\bin\ffmpeg.exe -version
   ```

---

## 3. Directory Layout

RASTATIME uses `C:\rastatime` as its standard install root.

```
C:\rastatime\
├── backend\
│   ├── analyzer\          — Media import pipeline (rastatime_analyzer)
│   ├── api\               — Django REST API (rastatime_api)
│   ├── api-client\        — Shared API client library
│   ├── playout\           — Playout scheduler (rastatime_playout) + Liquidsoap config
│   ├── rastatime_worker\  — Background job runner (no pyproject; runs via PYTHONPATH)
│   └── shared\            — Shared library modules
├── config\
│   ├── rastatime.conf   — Main RASTATIME configuration file
│   └── icecast.xml      — Icecast config (optional)
├── logs\             — All service log files (created automatically)
├── playout\          — Playout working files
└── .venv\            — Python virtual environment
```

> If you deploy to a non-standard path, pass `-InstallRoot D:\rastatime`
> to all `infra\nssm\install-*.ps1` and `remove-*.ps1` scripts.

> Third-party binaries live under `C:\Tools\`:
> `C:\Tools\nssm`, `C:\Tools\liquidsoap`, `C:\Tools\Icecast`,
> `C:\Tools\Apache24`, `C:\Tools\PHP`.

---

## 4. Step-by-Step Installation

### Step 1 — Clone or deploy the codebase

```powershell
# Option A: clone from version control
git clone https://github.com/vibesbuilder/RASTATIME.git C:\rastatime

# Option B: a GitHub release (Releases page) ships one wheel per backend
# package plus rastatime-frontend-legacy-vX.Y.Z.zip (frontend incl. vendor\);
# unzip the frontend to C:\rastatime\frontend\legacy and pip-install the
# wheels instead of the editable installs in Step 4.
```

### Step 2 — Run the bootstrap checker

The bootstrap checker verifies all required dependencies before you proceed.

```powershell
cd C:\rastatime
powershell -ExecutionPolicy Bypass -File infra\scripts\dev\bootstrap.ps1
```

Expected output: `All required dependencies found.`

Fix any `[FAIL]` items before continuing.

> **Note:** `bootstrap.ps1` (2026-11-01) checks every component of §2 as
> **required** — Python 3.11+, PostgreSQL, Liquidsoap, RabbitMQ, NSSM,
> Apache, PHP, Icecast, FFmpeg/FFprobe at the production paths of §3 (or on
> PATH); a missing one is a `[FAIL]` and the script exits 1.  Composer and
> Git are reported as optional (`[SKIP]` when absent).

### Step 3 — Create the Python virtual environment

```powershell
cd C:\rastatime
python -m venv .venv
# A fresh Windows 11 runs no PowerShell scripts (policy Restricted), so
# Activate.ps1 would fail; allow scripts for this window only:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1

# Verify the venv is active:
python --version
where.exe python
# First line must be: C:\rastatime\.venv\Scripts\python.exe
```

> The `Process` scope ends with the window: every new PowerShell that
> activates the venv (Step 4, Step 7, §7) needs the `Set-ExecutionPolicy`
> line again.  `where.exe`, not `where` - in PowerShell `where` is the
> alias of `Where-Object` and prints nothing.

### Step 4 — Install Python dependencies

```powershell
# With the venv active (pip cannot replace its own pip.exe on Windows,
# hence python -m):
python -m pip install --upgrade pip
pip install -r requirements.txt

# psycopg2 is not declared by any backend package but is required by the
# API (and the Liquidsoap config renderer) — install it explicitly:
pip install psycopg2-binary

# Editable installs of the backend packages, in dependency order:
pip install -e backend/shared
pip install -e backend/api-client
pip install -e backend/api
pip install -e backend/playout
pip install -e backend/analyzer

# Verify key packages are installed:
python -c "import django; print('Django', django.__version__)"
python -c "import importlib.metadata as m; print('Waitress', m.version('waitress'))"
python -c "import psycopg2; print('psycopg2 OK')"
```

> `backend\rastatime_worker` has **no** `pyproject.toml` on purpose — the
> worker runs as `python -m rastatime_worker` with `C:\rastatime\backend`
> on `PYTHONPATH` (set by `install-worker.ps1`); it is not pip-installed.

> `requirements.txt` still lists `python-vlc` (legacy fallback engine).
> It installs fine without VLC — VLC itself is no longer required.

### Step 4b — Install PHP dependencies (frontend)

The legacy frontend needs its Composer packages (`frontend\legacy\vendor\`,
ignored by git).  Skip this step when the frontend came from the release
zip, which already contains `vendor\`.

```powershell
cd C:\rastatime\frontend\legacy
& C:\Tools\PHP\php.exe C:\Tools\composer\composer.phar install --no-dev --no-interaction --prefer-dist
Test-Path .\vendor\autoload.php   # must be True
```

> `composer.lock` pins the 52 packages; `composer install` reproduces them
> exactly.  After pulling a change under `application\common\` run
> `composer.phar dump-autoload` (classmap), see UPGRADE.md.

### Step 5 — Create the configuration file

Copy the example file and edit it for your environment:

```powershell
Copy-Item C:\rastatime\config\rastatime.conf.example `
          C:\rastatime\config\rastatime.conf
```

Open `C:\rastatime\config\rastatime.conf` in a text editor.  The file
is **YAML**; set at minimum:

```yaml
general:
  public_url: http://<your-host>
  api_key: <generate — see below>
  secret_key: <generate — see below>
  timezone: Europe/Berlin

storage:
  path: C:/rastatime/media

database:
  host: localhost
  port: 5432
  name: rastatime
  user: rastatime
  password: <your-db-password>

rabbitmq:
  host: localhost
  port: 5672
  vhost: /rastatime
  user: rastatime
  password: <your-rabbitmq-password>
```

> `storage.path` is the **initial** location of the media library.  Since
> 2026-09-16 Settings → Local Machine → **Media Library Location** overrides it
> once the operator has moved the library; keep the configured folder in
> place (it may be empty) because the web application checks at start that
> it exists.

> The API port is NOT set in this file — it defaults to **8765** via the
> `-ApiPort` parameter of `install-api.ps1` and is injected into the
> services as an environment variable.

> The configuration file path is injected into every **Python** service
> (API, worker, playout, analyzer) via the `RASTATIME_CONFIG_FILEPATH`
> environment variable (set automatically by their install scripts).
> Apache/PHP uses its built-in default path, Icecast gets the config as
> a `-c` argument, and Liquidsoap gets its rendered script as argument.

#### Secrets that MUST be changed before production

The example file ships with placeholder values that are safe for a fresh
install on a local LAN but **must** be replaced before the host is
reachable from the public internet:

> **Note:** the `stream:` section (`stream.inputs`, `stream.harbor`) is
> present in `rastatime.conf.example` as a commented block — uncomment it
> and set the harbor fallback passwords when you configure the DJ inputs.
> `stream.internal_listener` is obsolete since 2026-10-25 (nothing reads
> it any more; an old file that still carries it keeps validating).

| Setting | Where | Why |
|---|---|---|
| `general.api_key` | `rastatime.conf` | Authenticates inter-service API calls and the v1 legacy notify hook. |
| `general.secret_key` | `rastatime.conf` | Django session / CSRF signing key. Must be at least 50 random chars. |
| `<source-password>` | `C:\rastatime\config\icecast.xml` | Icecast admin / relay / source password. Default value is `admin`. Replace with a long random string. |
| Master DJ password | `cc_pref` row `live_stream_master_password` (set via Settings → Streams in the frontend) | Authenticates the master-source DJ at `/main`. |

Generate strong values e.g. with PowerShell (cryptographic random, 48
bytes, about 62 alphanumeric characters - enough for the 50 of
`secret_key`):

```powershell
$b = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b) -replace '[+/=]', ''
```

> Until 2026-11-01 this read `(1..36 | ForEach-Object { Get-Random ... })`:
> 46-48 characters, below the 50 `secret_key` needs, and `Get-Random` is
> not a cryptographic generator (fresh-machine rehearsal, INSTALL_PROBE.md).

### Step 6 — Create the PostgreSQL database

```powershell
# Connect as the PostgreSQL superuser:
psql -U postgres -h 127.0.0.1 -p 5432

-- Inside psql:
CREATE USER rastatime WITH PASSWORD '<your-db-password>';
CREATE DATABASE rastatime OWNER rastatime;
\q
```

### Step 6b — Create the RabbitMQ vhost and user

```powershell
rabbitmqctl add_user rastatime <your-rabbitmq-password>
rabbitmqctl add_vhost /rastatime
rabbitmqctl set_permissions -p /rastatime rastatime ".*" ".*" ".*"
```

The values must match the `rabbitmq:` section of `rastatime.conf`.

### Step 7 — Run database migrations

```powershell
# With the venv active:
cd C:\rastatime\backend\api\rastatime_api
$env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.prod"
$env:RASTATIME_CONFIG_FILEPATH = "C:\rastatime\config\rastatime.conf"
$env:PYTHONPATH = "C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime"

python manage.py migrate
```

> `manage.py` lives at `backend\api\rastatime_api\manage.py` (not at the
> package root).  Against a database restored from a backup, `migrate`
> correctly reports `No migrations to apply`.
> There is no `collectstatic` step — the prod settings define no
> `STATIC_ROOT` and none is needed.

### Step 8 — Create the log directory

The NSSM install scripts create this automatically, but you can create it
now to verify filesystem permissions:

```powershell
New-Item -ItemType Directory -Path C:\rastatime\logs -Force
```

### Step 9 — Install the Windows services

Run the install scripts as **Administrator**, in dependency order:

```powershell
# Open an elevated PowerShell prompt, then:

# 9a — API (mandatory; start immediately)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-api.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\rastatime.conf `
    -StartService

# Wait for the API health gate before continuing:
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
# Expected: StatusCode 200

# 9b — Worker (mandatory)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-worker.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\rastatime.conf `
    -StartService

# 9c — Playout (mandatory; do NOT start yet — engine env vars follow in 9d)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-playout.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\rastatime.conf

# 9d — Playout engine environment variables
# install-playout.ps1 does NOT set the engine selection.  `nssm set`
# REPLACES the whole environment block, so repeat the six variables the
# script sets and append the engine extras.  PYTHONUTF8=1 is set by every
# install script since 2026-11-01 (German PostgreSQL messages and file
# names outside the code page otherwise break logging).  The three
# RASTATIME_LIQUIDSOAP_RESTART_* / MEMORY_WARN values are the planned
# restart of a 24/7 programme (ARCHITECTURE §23.27 and §23.48) -
# optional, the values below are the studio machine's:
nssm set RASTATIME-PLAYOUT AppEnvironmentExtra `
    "DJANGO_SETTINGS_MODULE=rastatime_api.settings.prod" `
    "RASTATIME_CONFIG_FILEPATH=C:\rastatime\config\rastatime.conf" `
    "RASTATIME_API_URL=http://127.0.0.1:8765" `
    "PYTHONPATH=C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime" `
    "PATH=C:\ffmpeg\bin;%PATH%" `
    "PYTHONUTF8=1" `
    "RASTATIME_MPV_LOG_LEVEL=warn" `
    "RASTATIME_PLAYOUT_ENGINE=liquidsoap" `
    "RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0" `
    "RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS=7" `
    "RASTATIME_LIQUIDSOAP_RESTART_AT_MB=2560" `
    "RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB=2816"
nssm start RASTATIME-PLAYOUT

# 9e — Analyzer (mandatory — uploads stay at "Pending Import" without it)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-analyzer.ps1 `
    -InstallRoot C:\rastatime `
    -ConfigFile C:\rastatime\config\rastatime.conf `
    -StartService

# 9f — Apache (frontend; httpd.conf per §2.6 / INSTALL_APACHE.md)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-apache.ps1 `
    -InstallRoot C:\rastatime `
    -ApacheRoot C:\Tools\Apache24 `
    -StartService

# 9g — Icecast (streaming; note the explicit exe path)
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-icecast.ps1 `
    -InstallRoot C:\rastatime `
    -IcecastExe 'C:\Tools\Icecast\bin\icecast.exe' `
    -StartService

# 9h — Install and start the Liquidsoap service.
# The production script C:\Tools\liquidsoap\rastatime.liq was already
# rendered by RASTATIME-PLAYOUT at its startup (9d) — the playout's
# startup render is the authoritative one: it includes the stream.harbor
# DJ passwords and the crossfade setting from the service environment.
Test-Path C:\Tools\liquidsoap\rastatime.liq   # must be True; if False,
                                              # restart RASTATIME-PLAYOUT

powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\backend\playout\config\nssm-install-liquidsoap.ps1
nssm start RASTATIME-LIQUIDSOAP
```

> Stream outputs are rendered from the **database** (`cc_pref` rows
> `stream_output_N`, maintained via Settings → Streams) — not from
> `rastatime.conf`.  After any stream-setting change:
> `nssm restart RASTATIME-PLAYOUT` (re-renders the `.liq` at startup,
> incl. harbor credentials), then `nssm restart RASTATIME-LIQUIDSOAP`.
> Avoid the manual CLI render
> (`python -m rastatime_playout.liquidsoap_config render`) on a
> configured system — it does not read `stream.harbor` and would strip
> the DJ harbor inputs from the rendered script.

### Step 10 — Verify the installation

Run the T22.3 status helper to confirm all services are healthy:

```powershell
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\status.ps1
```

Expected output (all seven services; HTTP probes for API, Apache and
Icecast):
```
  RASTATIME-API         Running    HTTP 200 healthy
  RASTATIME-WORKER      Running
  RASTATIME-PLAYOUT     Running
  RASTATIME-ANALYZER    Running
  RASTATIME-APACHE      Running    HTTP 200 healthy
  RASTATIME-ICECAST     Running    HTTP 200 healthy
  RASTATIME-LIQUIDSOAP  Running
  All mandatory services are Running.
```

If any mandatory service shows `Stopped` or `Not installed`, see §5
(Troubleshooting) or `docs\operator\RESTART_ORDER.md` §5 for per-service
recovery procedures.

---

## 5. Troubleshooting

### 5.1 API does not start — `rastatime.conf` not found

```
Error: RASTATIME_CONFIG_FILEPATH is not set or the file does not exist.
```

**Fix:** Ensure `C:\rastatime\config\rastatime.conf` exists and the path
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
Check the `[database]` section of `rastatime.conf` for correct credentials.

### 5.3 Liquidsoap does not start — rastatime.liq missing

```
liquidsoap-stderr.log: ... rastatime.liq: no such file
```

**Fix:** Restart the playout (its startup render writes the script,
incl. DJ harbor credentials), then Liquidsoap:
```powershell
nssm restart RASTATIME-PLAYOUT
nssm restart RASTATIME-LIQUIDSOAP
```
Also confirm the engine selection on the playout service:
```powershell
nssm get RASTATIME-PLAYOUT AppEnvironmentExtra
# Must contain RASTATIME_PLAYOUT_ENGINE=liquidsoap
```
If the variable is missing, re-apply the full environment block from
§4 Step 9d (`nssm set` replaces the whole block).

### 5.4 Worker or playout stay in `StartPending`

The health-check gate in the worker/playout entry points is waiting for
the API to return HTTP 200.  Check the API is healthy:
```powershell
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
```
If the API is not healthy, resolve it first (see §5.2 and
`docs\operator\RESTART_ORDER.md` §5.1).

### 5.5 Status script shows wrong venv

The install scripts derive the venv python from `-InstallRoot`
(`<InstallRoot>\.venv\Scripts\python.exe`, falling back to `python` on
PATH).  If the wrong python is registered, re-run the install script
with the correct `-InstallRoot` and inspect:
```powershell
nssm get RASTATIME-API Application
# Should show the python.exe from your venv
```

### 5.6 Uploads stay at "Pending Import"

The analyzer is not consuming the RabbitMQ queue.  Check both services:
```powershell
Get-Service RabbitMQ, RASTATIME-ANALYZER
```
If the RabbitMQ service crashes on start, re-register it with an
explicit `RABBITMQ_BASE` (see §2.4).

### 5.7 Podcast episode list stays empty (DataTables `guid` warning)

Opening an imported podcast shows a spinning loader, no episodes and a
DataTables warning "Requested unknown parameter 'guid' for row 0".
`/rest/podcast/<id>/episodes` answers `201` with an empty list because
PHP cannot verify the feed's HTTPS certificate: PHP on Windows has no CA
bundle.  Install one as described in
[INSTALL_APACHE.md §3.1](INSTALL_APACHE.md#31-ca-bundle-for-outbound-https-podcast-feeds)
and restart `RASTATIME-APACHE`.  Auto-ingest of new episodes is affected
the same way (the feed is read by PHP, only the download runs in the
analyzer).

### 5.8 Frontend answers 500 or a blank page on every URL (`vendor\` missing)

Apache serves `index.php` but PHP dies before any output because
`frontend\legacy\vendor\autoload.php` does not exist (the PHP error log
`logs\http-error-*.log` shows the failed `require`).  Run §4 Step 4b.

---

## 6. Post-Installation Checklist

After completing §4, verify each item:

- [ ] `status.ps1` shows all seven services `Running` (incl. the HTTP probes)
- [ ] `Get-Service RabbitMQ` shows `Running`
- [ ] `http://127.0.0.1:8765/health` returns HTTP 200
- [ ] `http://127.0.0.1:8765/api/v2/schema/swagger-ui` loads the API docs
- [ ] The web UI loads at `http://<host>/` (Apache) and login works — a fresh
      database has one account, **`admin` / `admin`** (seeded by the legacy
      migration); change the password under Settings → Users before anything else
- [ ] A test upload leaves "Pending Import" and becomes "Ready" (analyzer round-trip)
- [ ] Podcasts → open an imported podcast: the episode list fills (needs the PHP CA bundle, INSTALL_APACHE.md §3.1)
- [ ] `C:\rastatime\logs\` contains `api-stdout.log` (non-empty after first request)
- [ ] `pg_isready -h 127.0.0.1 -p 5432` succeeds
- [ ] All services survive a `Restart-Computer` (auto-start verified)
- [ ] Soundcard settings are visible in the RASTATIME web UI (Settings → Soundcard)
- [ ] Icecast status page reachable at `http://localhost:8000/` (port 8001 is the Liquidsoap DJ harbor — `/main` and `/show` share it —, NOT Icecast)

---

## 7. Updating an Existing Installation

To update RASTATIME to a new version:

```powershell
# 1. Stop services in reverse order
nssm stop RASTATIME-LIQUIDSOAP confirm
nssm stop RASTATIME-ICECAST    confirm
nssm stop RASTATIME-APACHE     confirm
nssm stop RASTATIME-ANALYZER   confirm
nssm stop RASTATIME-PLAYOUT    confirm
nssm stop RASTATIME-WORKER     confirm
nssm stop RASTATIME-API        confirm

# 2. Pull the new code
cd C:\rastatime
git pull

# 3. Update Python dependencies
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Editable installs pick up code changes automatically; re-run
# `pip install -e backend/<pkg>` only if a pyproject.toml changed.

# 3b. PHP dependencies (only if composer.lock changed; classmap always)
cd C:\rastatime\frontend\legacy
& C:\Tools\PHP\php.exe C:\Tools\composer\composer.phar install --no-dev --no-interaction --prefer-dist
& C:\Tools\PHP\php.exe C:\Tools\composer\composer.phar dump-autoload

# 4. Run any new migrations (env vars as in §4 Step 7)
cd C:\rastatime\backend\api\rastatime_api
python manage.py migrate

# 5. Restart services in dependency order
nssm start RASTATIME-API
# (wait for HTTP 200 on http://127.0.0.1:8765/health)
nssm start RASTATIME-WORKER
nssm start RASTATIME-PLAYOUT
nssm start RASTATIME-ANALYZER
nssm start RASTATIME-APACHE
nssm start RASTATIME-ICECAST
# If the playout/Liquidsoap templates changed, re-render first:
#   python -m rastatime_playout.liquidsoap_config render --out C:/Tools/liquidsoap/rastatime.liq
nssm start RASTATIME-LIQUIDSOAP

# 6. Verify
powershell -File C:\rastatime\infra\nssm\status.ps1
```

---

## 8. Uninstalling RASTATIME

```powershell
# Remove services (preserves logs and config)
nssm stop   RASTATIME-LIQUIDSOAP confirm
nssm remove RASTATIME-LIQUIDSOAP confirm
powershell -File infra\nssm\remove-icecast.ps1  -Force
powershell -File infra\nssm\remove-apache.ps1   -Force
powershell -File infra\nssm\remove-analyzer.ps1 -Force
powershell -File infra\nssm\remove-playout.ps1  -Force
powershell -File infra\nssm\remove-worker.ps1   -Force
powershell -File infra\nssm\remove-api.ps1      -Force

# Optional: purge logs
powershell -File infra\nssm\remove-api.ps1 -Force -PurgeLogs
# ... repeat for each service

# Optional: drop the database
psql -U postgres -c "DROP DATABASE rastatime;"
psql -U postgres -c "DROP USER rastatime;"

# Optional: delete the install directory
Remove-Item -Recurse -Force C:\rastatime
```

---

## 9. Related Documentation

| Document | Description |
|---|---|
| `docs\architecture\SERVICE_TOPOLOGY.md` | Service definitions, ports, log layout (T21.1) |
| `docs\operator\RESTART_ORDER.md` | Startup / shutdown / recovery procedures (T22.4) |
| `docs\operator\WINDOWS_24_7.md` | Windows hardening for unattended 24/7 operation: no automatic updates or reboots, automatic sign-in, power settings, test restart (2026-10-03) |
| `docs\operator\COMPONENTS.md` | Third-party components: inventory, update classes (exposed / audio chain / code dependencies), monthly maintenance window, `scripts\update_check.py` (2026-10-09) |
| `docs\operator\GO_LIVE_HTTPS.md` | Internet reachability via HTTPS, way A: secrets rotation and localhost binds (stage 0), code, DNS/certificate/Apache TLS, acceptance (2026-10-04) |
| `docs\operator\TEST_PLAN.md` | Acceptance checklist (services, schedule, DJ, streams/HTTPS, protection, data), recurring checks, rehearsal tools (2026-10-06) |
| `infra\nssm\install-*.ps1` | Service install scripts (T22.1) |
| `backend\playout\config\nssm-install-liquidsoap.ps1` | RASTATIME-LIQUIDSOAP service install script |
| `infra\nssm\remove-*.ps1` | Service remove scripts (T22.2) |
| `infra\nssm\status.ps1` | Live status and health helper (T22.3) |
| `infra\scripts\dev\bootstrap.ps1` | Dependency checker (T3.1) |
