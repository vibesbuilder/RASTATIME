# RASTATIME

[![python](https://github.com/vibesbuilder/RASTATIME/actions/workflows/python.yml/badge.svg)](https://github.com/vibesbuilder/RASTATIME/actions/workflows/python.yml)
[![php](https://github.com/vibesbuilder/RASTATIME/actions/workflows/php.yml/badge.svg)](https://github.com/vibesbuilder/RASTATIME/actions/workflows/php.yml)

**Radio automation for Windows: schedule, play out, stream and archive a
radio station from one Windows 11 PC.**

https://github.com/user-attachments/assets/489b8b19-715e-468f-bb66-f58e321b40c6

*A three-minute tour of RASTATIME (v1.4.0): dashboard, scheduling, library, playlists and
smart blocks, sources, Auto DJ, playout and streams, widgets, archiving, reporting, operations,
four languages.*

RASTATIME runs the whole on-air chain of a community or small station: a
calendar of shows, a media library with playlists and smart blocks,
automatic filling, a Liquidsoap playout engine with crossfades and
loudness normalisation, live DJs, line-in hardware sources, webstreams,
recording and streaming through Icecast.  Every part runs as a Windows
service; the web interface and the user manual are available in English,
German, French and Spanish.

RASTATIME started as a fork of [LibreTime](https://github.com/libretime/libretime)
4.5.0 and is developed for continuous 24/7 operation.

**Latest release:** [GitHub Releases](https://github.com/vibesbuilder/RASTATIME/releases)

---

## Features

**Scheduling**
- Calendar with recurring shows, show templates, repeats that copy the
  latest episode, linked shows and drag-and-drop.
- Delayed show start: an opted-in show may start late when the show
  before it overran.
- Show ends stay on the wall clock across daylight-saving changes.

**Filling the air**
- Autoloading playlists fill every episode exactly: intro, then outro,
  then the playlist against the remaining time; a single episode can get
  its own autoloading settings.
- Auto DJ creates shows in calendar gaps and tops up incomplete ones.
- Teasers for upcoming shows, song requests from a public widget and
  short-notice traffic bulletins that air inside the running show.

**Playout**
- Liquidsoap 2.4 engine with separate track and show crossfades, cue
  points and EBU R128 loudness normalisation (-23 LUFS).
- A standby instance keeps listeners connected while the engine restarts;
  optional planned restarts in a quiet moment for 24/7 programmes.
- Optional Stereo Tool output processing.

**Sources and outputs**
- Files, webstreams (with a buffer per stream), several line-in hardware
  inputs and live DJs over the Liquidsoap harbor, with DJ logins managed
  in the web interface.
- Up to four Icecast output streams with track metadata, plus local
  sound-card output.
- Recording per show or per hour; recordings can be copied into the
  library.

**Library**
- Upload and drop-folder import with format normalisation (lossless to
  MP3 320), tags from all common formats, cover art, cue-point detection,
  *Re-read Tags* and a quarantine for failed uploads.

**Archiving and reporting**
- Episodes uploaded to [cba.media](https://cba.media) by hand or
  automatically after the broadcast, with an archive status page.
- Playout history and log sheets, listener statistics per stream and per
  show, Programme Minutes and People Involved of the own productions for
  the yearly reporting.

**Operations**
- Backups from the web interface and a nightly run; import and export of
  users, shows, playlists, smart blocks, webstreams and podcasts as
  CSV/JSON.
- Alerts by e-mail and Telegram for dead air, stopped services and
  pre-flight warnings.
- Public embed widgets (now playing, weekly programme, player) and a
  read-only public API; four user roles (Admin, Program Manager, DJ,
  Guest).

---

## Requirements

| Component | Version | Notes |
|---|---|---|
| Windows | 11 (64-bit) | The only supported platform |
| Python | 3.11 or later | Production runs 3.13; CI tests 3.11 and 3.13 |
| PostgreSQL | 17 | The only database |
| RabbitMQ | 4.x with Erlang OTP | vhost `/rastatime`; the analyzer queue |
| Apache httpd | 2.4 with `mod_fcgid` | Web interface, wrapped by NSSM |
| PHP | 8.3 or later | Production runs 8.5 |
| Liquidsoap | 2.4.6 | Official `win64` build from savonet/liquidsoap |
| Icecast | 2.5.0 | Streaming server |
| FFmpeg | current release build | Expected in `C:\ffmpeg\bin` |
| NSSM | 2.24 | Windows service wrapper |

The installed versions and their update path are tracked in
[`docs/operator/COMPONENTS.md`](docs/operator/COMPONENTS.md).

---

## Getting started

The complete walkthrough is [`docs/operator/INSTALL.md`](docs/operator/INSTALL.md).
In short:

1. Install the prerequisites above (INSTALL §2).
2. Get the code: clone the repository, or download a release (one wheel
   per backend package plus the frontend zip with `vendor\`).
3. Create the virtual environment and install the backend packages.
4. Create `C:\rastatime\config\rastatime.conf` from
   [`config/rastatime.conf.example`](config/rastatime.conf.example) and
   change every secret (INSTALL Step 5).
5. Create the PostgreSQL database and the RabbitMQ vhost, then apply the
   migrations.
6. Install the Windows services and check them.

```powershell
git clone https://github.com/vibesbuilder/RASTATIME.git C:\rastatime
cd C:\rastatime
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # fresh Windows: scripts are blocked
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install psycopg2-binary
python -m pip install -e backend\shared -e backend\api-client -e backend\api -e backend\playout -e backend\analyzer
```

```powershell
# After the services are installed (elevated PowerShell):
powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/health
```

Environment variables with the `RASTATIME_` prefix override values of
`rastatime.conf` (e.g. `RASTATIME_GENERAL_API_KEY`).

### Upgrading

Follow [`docs/operator/UPGRADE.md`](docs/operator/UPGRADE.md): backup,
stop all services, update the code, reinstall the packages, migrate,
restart in order.  Stop the services before `pip install`: the running
analyzer locks its executable and the reinstall fails halfway.

---

## Services

| Service | Role |
|---|---|
| `RASTATIME-API` | Django REST API (Waitress, `127.0.0.1:8765`) |
| `RASTATIME-PLAYOUT` | Scheduler: reads the schedule, renders the Liquidsoap script and drives the engine over telnet |
| `RASTATIME-LIQUIDSOAP` | Playout engine: mixing, crossfades, loudness, line-in, harbor for live DJs, outputs |
| `RASTATIME-STANDBY` | Second Liquidsoap instance that keeps listeners connected while the engine restarts |
| `RASTATIME-ICECAST` | Streaming server |
| `RASTATIME-APACHE` | Web interface (PHP) and reverse proxy for `/api/v2/` |
| `RASTATIME-ANALYZER` | Analyses uploads (tags, loudness, cue points) from the RabbitMQ queue |
| `RASTATIME-WORKER` | Background jobs: uploads to cba.media and the daily topic list |

The services are installed by `infra\nssm\install-*.ps1` (API, worker,
playout, analyzer, Apache, Icecast) and by
`backend\playout\config\nssm-install-liquidsoap.ps1` /
`nssm-install-standby.ps1`; `infra\nssm\status.ps1` shows all eight with
HTTP probes.  All scripts need an elevated PowerShell prompt.  For the
restart order and continuous operation see
[`RESTART_ORDER.md`](docs/operator/RESTART_ORDER.md) and
[`WINDOWS_24_7.md`](docs/operator/WINDOWS_24_7.md).

---

## Documentation

| Document | Content |
|---|---|
| [User manual](USER_MANUAL.md) | Day-to-day operation, one chapter per area; also in [Deutsch](docs/manual/de/USER_MANUAL.md), [Français](docs/manual/fr/USER_MANUAL.md), [Español](docs/manual/es/USER_MANUAL.md) |
| [Operator guides](docs/operator/) | Installation, upgrade, components, backup, 24/7 operation, crash recovery |
| [Architecture](RASTATIME_ARCHITECTURE_DRAFT_v0.1.md) | Design and decisions, with a changelog per section; ADRs in [`docs/architecture/decisions`](docs/architecture/decisions) |
| [Release notes](docs/releases/) | One file per release |
| [`CHANGELOG.md`](CHANGELOG.md) | Detailed change history (German) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development setup, tests, releasing |

---

## Repository layout

```
RASTATIME/
├── backend/
│   ├── api/               # Django REST API (Waitress, port 8765)
│   ├── api-client/        # Python client for the API
│   ├── analyzer/          # Media analyzer (RabbitMQ consumer)
│   ├── playout/           # Playout scheduler, Liquidsoap script template, engine service installers
│   ├── shared/            # Configuration, logging and alerts shared by the services
│   └── rastatime_worker/  # Background jobs (python -m rastatime_worker, not pip-installed)
├── frontend/
│   └── legacy/            # PHP web interface (Zend 1 / Propel)
├── audio/                 # Line-in and sound-card device handling
├── playout/, streams/     # Engine interface, now-playing state, stream types
├── infra/                 # NSSM service scripts, Apache config, maintenance scripts, health checks
├── config/                # Templates: rastatime.conf, icecast.xml, apache-site.conf; Stereo Tool preset
├── scripts/               # Test runner, component update check, backup and log maintenance
├── docs/
│   ├── manual/            # User manual (English; de/, fr/, es/)
│   ├── operator/          # Installation and operation guides
│   ├── architecture/      # Architecture notes and ADRs
│   ├── releases/          # Release notes
│   ├── dev/               # Developer notes
│   └── upstream/          # LibreTime reference documentation
└── tests/
    └── unit/              # Cross-package tests
```

---

## Running tests

`scripts\run_tests.ps1` sets the environment the suites need and runs
them; the unit suite needs neither a database nor running services:

```powershell
.\scripts\run_tests.ps1                # api + playout + unit
.\scripts\run_tests.ps1 -Suite unit    # one suite: api, playout, unit, analyzer, shared
```

The individual `pytest` commands are in
[`CONTRIBUTING.md`](CONTRIBUTING.md#running-tests).

---

## Upstream attribution

RASTATIME is a derivative work based on **LibreTime 4.5.0**
(commit `f429339bfc6ef13e125f1251bddf9e32bb822231`).

LibreTime is copyright its respective contributors and is published under
the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).
RASTATIME inherits this license. See [`LICENSE`](LICENSE) for the full text.

LibreTime upstream: <https://github.com/libretime/libretime>

---

## Security

See [`SECURITY.md`](SECURITY.md) for the supported versions, how to report a
vulnerability and the operator hardening guides.

---

## License

AGPL-3.0 — see [`LICENSE`](LICENSE).
