# FORK_NOTES — RASTATIME

## Source

| Field | Value |
|---|---|
| Upstream project | LibreTime |
| Upstream repository | https://github.com/libretime/libretime |
| Upstream tag imported | `4.5.0` |
| Upstream commit | f429339bfc6ef13e125f1251bddf9e32bb822231 |
| Import date | 2026-04-24 |
| Import method | Shallow clone at tag 4.5.0 → copy into RASTATIME structure (Option A) |

## License

LibreTime is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.
RASTATIME inherits this license as a derivative work.
The `LICENSE` file at the repository root contains the full AGPL-3.0 text.
AGPL-3.0 compliance for distribution/deployment is under review.

## Why This Fork Exists

LibreTime is a Linux-first radio automation system that assumes:
- Linux service lifecycle (systemd/systemctl)
- Liquidsoap as the primary playout engine
- Celery + gunicorn + nginx as the runtime stack
- Linux audio backends (ALSA/PortAudio)
- Linux-specific filesystem paths (/etc, /var, /srv)

**RASTATIME redefines the runtime substrate while preserving LibreTime's functional scope.**

The goal is a **Windows 11 studio machine deployment** with:
- libVLC as the mandatory main playout engine
- Windows-native service startup via NSSM
- Windows audio I/O (WASAPI via libVLC)
- New first-class features: local Line-In sources, Soundcard settings
- English-first, German as the only additional UI language in phase 1

This is a **functional fork**, not a literal port.
See `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` for the full target architecture.

## What Was Imported

| RASTATIME path | From LibreTime (tag 4.5.0) | Notes |
|---|---|---|
| `backend/api/` | `api/` | Django REST API — keep + refactor |
| `backend/api-client/` | `api-client/` | API client library — keep + refactor |
| `backend/analyzer/` | `analyzer/` | Media analyzer — keep + refactor |
| `backend/playout/` | `playout/` | Liquidsoap playout — **to be replaced** with libVLC |
| `backend/shared/` | `shared/` | Shared Python modules — keep + refactor |
| `backend/worker/` | `worker/` | Celery worker — **to be replaced** with Windows-native runner |
| `frontend/legacy/` | `legacy/` | PHP/JS legacy UI — keep + refactor |
| `infra/upstream/` | `installer/`, `docker/`, `Makefile`, etc. | Linux/Docker reference only — **not for production use in RASTATIME** |
| `docs/upstream/` | `docs/`, `CHANGELOG.md` | LibreTime documentation reference |
| `LICENSE` | `LICENSE` | AGPL-3.0 — inherited |

## What Was Not Imported

| Skipped | Reason |
|---|---|
| `Vagrantfile` | Linux VM setup — not relevant |
| `cloud-init.yml` | Linux cloud provisioning — not relevant |
| `codecov.yml` | CI coverage config — can be re-added if CI is set up |
| `.pre-commit-config.yaml` | Linux-centric pre-commit hooks — can be adapted later |
| `.github/` | Linux/Docker-focused CI workflows — not applicable |

## Branch Naming Convention

| Branch | Purpose |
|---|---|
| `master` | Main integration branch for RASTATIME |
| Feature branches | `feat/<task-id>-<short-description>` |

## Known Divergence Points (summary)

The following LibreTime subsystems will be replaced in RASTATIME:
- Liquidsoap → libVLC playout adapter
- Celery → Windows-native background runner
- gunicorn → Waitress (or equivalent Windows-safe WSGI server)
- nginx → to be decided (optional reverse proxy)
- systemd/systemctl → NSSM + Windows service scripts
- ALSA/PortAudio → Windows audio API via libVLC

See `IMPLEMENTATION_PLAN.md` for the full phase and task breakdown.
