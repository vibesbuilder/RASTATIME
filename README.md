# RASTATIME

[![python](https://github.com/RASTATIME/rastatime/actions/workflows/python.yml/badge.svg)](https://github.com/RASTATIME/rastatime/actions/workflows/python.yml)
[![php](https://github.com/RASTATIME/rastatime/actions/workflows/php.yml/badge.svg)](https://github.com/RASTATIME/rastatime/actions/workflows/php.yml)

**Windows-first radio automation — functional fork of [LibreTime](https://github.com/libretime/libretime) 4.5.0**

RASTATIME preserves the core user-visible feature set of LibreTime — schedule management, shows, playlists, media library, webstreams, podcasts, history and reporting — while replacing every Linux-bound runtime layer with components that run reliably on **Windows 11**.

---

## What is different from LibreTime

| LibreTime | RASTATIME |
|---|---|
| Liquidsoap playout engine | libVLC / `python-vlc` *(in development)* |
| Celery background worker | Plain Python task runner |
| Gunicorn WSGI server | Waitress (port **8765**) |
| systemd / systemctl | NSSM Windows services |
| ALSA / PortAudio / PulseAudio | WASAPI via libVLC |
| Linux paths (`/etc`, `/srv`) | Windows paths (`C:\rastatime\…`) |
| Linux-only installer | PowerShell bootstrap + NSSM scripts |

New features not present in LibreTime:

- **Line-In sources** — multiple local stereo hardware inputs, managed like webstreams
- **Soundcard settings** — explicit local input/output device mapping (Settings → Soundcard)
- **German UI** — built-in translation alongside the English default

---

## Requirements

| Component | Minimum version | Notes |
|---|---|---|
| Windows | 11 | Only supported platform |
| Python | 3.12 | 3.13 tested and working |
| PostgreSQL | 14 | Windows installer or Chocolatey |
| RabbitMQ | 3.x | With management plugin |
| PHP | 8.1 | For the legacy web frontend |
| NSSM | 2.24 | Windows service wrapper |

---

## Repository layout

```
RASTATIME/
├── backend/
│   ├── api/           # Django REST API (Waitress, port 8765)
│   ├── api-client/    # Python API client library
│   ├── analyzer/      # Media file analyzer
│   ├── playout/       # Playout engine (VLC adapter in development)
│   ├── shared/        # Shared config models and utilities
│   └── worker/        # Background task runner (plain Python)
├── frontend/
│   └── legacy/        # PHP/JS web UI (LibreTime-compatible)
├── audio/
│   └── soundcard/     # Windows audio device manager (WASAPI)
├── infra/
│   └── nssm/          # PowerShell scripts to install/remove Windows services
├── config/
│   └── libretime.conf # Runtime configuration (created during setup)
├── docs/
│   └── upstream/      # LibreTime reference documentation
└── tests/
    └── unit/          # Cross-package verification tests
```

---

## Quick start

### 1. Clone

```powershell
git clone https://github.com/<your-org>/rastatime.git C:\RASTATIME
cd C:\RASTATIME
```

### 2. Create a Python virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install backend packages

```powershell
pip install -e "backend\shared"
pip install -e "backend\api-client"
pip install -e "backend\api[dev]"
pip install -e "backend\worker"
pip install -e "backend\playout"
pip install -e "backend\analyzer"
```

### 4. Create directories and configuration

```powershell
New-Item -ItemType Directory -Force -Path C:\rastatime\media
New-Item -ItemType Directory -Force -Path C:\rastatime\config
New-Item -ItemType Directory -Force -Path C:\rastatime\logs
```

Copy `config\libretime.conf.example` to `C:\rastatime\config\libretime.conf` and edit the database, RabbitMQ, and API key values.

### 5. Set up the database

```powershell
# As the PostgreSQL superuser:
psql -U postgres -c "CREATE USER rastatime WITH PASSWORD 'rastatime' CREATEDB;"
psql -U postgres -c "CREATE DATABASE rastatime OWNER rastatime;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE rastatime TO rastatime;"
```

```powershell
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"
cd backend\api
python manage.py migrate
```

### 6. Install Windows services

```powershell
# Run each script from an elevated PowerShell prompt
powershell -ExecutionPolicy Bypass -File infra\nssm\install-api.ps1
powershell -ExecutionPolicy Bypass -File infra\nssm\install-worker.ps1
powershell -ExecutionPolicy Bypass -File infra\nssm\install-playout.ps1
```

### 7. Verify

```powershell
# Check service status
powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1

# Test API health
Invoke-WebRequest -Uri http://127.0.0.1:8765/health
```

---

## Service management

| Script | Action |
|---|---|
| `infra\nssm\install-api.ps1` | Install RASTATIME-API service |
| `infra\nssm\install-worker.ps1` | Install RASTATIME-WORKER service |
| `infra\nssm\install-playout.ps1` | Install RASTATIME-PLAYOUT service |
| `infra\nssm\status.ps1` | Show status of all services |
| `infra\nssm\remove-api.ps1` | Uninstall RASTATIME-API service |
| `infra\nssm\remove-worker.ps1` | Uninstall RASTATIME-WORKER service |
| `infra\nssm\remove-playout.ps1` | Uninstall RASTATIME-PLAYOUT service |

All scripts require an **elevated (Administrator) PowerShell** prompt.

---

## Running tests

Unit tests do not require a running database or services:

```powershell
python -m pytest tests\unit\ -v
```

Django API tests (require a running PostgreSQL instance):

```powershell
cd backend\api
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.testing"
python -m pytest tests\ -v
```

---

## Configuration reference

The runtime configuration file (`C:\rastatime\config\libretime.conf`) uses YAML:

```yaml
general:
  public_url: http://localhost
  api_key: change-before-production
  secret_key: change-before-production
  timezone: Europe/Berlin

storage:
  path: C:/rastatime/media

database:
  host: localhost
  port: 5432
  name: rastatime
  user: rastatime
  password: rastatime

rabbitmq:
  host: localhost
  port: 5672
  vhost: /rastatime
  user: rastatime
  password: rastatime
```

Environment variable overrides follow the `LIBRETIME_` prefix convention, e.g. `LIBRETIME_GENERAL_API_KEY`.

---

## Upstream attribution

RASTATIME is a derivative work based on **LibreTime 4.5.0**
(commit `f429339bfc6ef13e125f1251bddf9e32bb822231`).

LibreTime is copyright its respective contributors and is published under
the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).
RASTATIME inherits this license. See [`LICENSE`](LICENSE) for the full text.

LibreTime upstream: <https://github.com/libretime/libretime>

---

## License

AGPL-3.0 — see [`LICENSE`](LICENSE).
