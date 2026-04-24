# RASTATIME — Windows Development Status

**Date:** 2026-04-24
**Version:** 0.2.3
**Phase:** M3 complete (Windows dev bootstrap)

This document is the honest record of what works, what is stubbed, and what
is blocked on a Windows 11 developer machine. It is updated at the end of
every Milestone. Do not prettify — keep it accurate.

---

## 1. Environment

| Item | Status | Notes |
|---|---|---|
| Python 3.13.13 | **Working** | Minimum required: 3.11 |
| Virtual env (`.venv`) | **Working** | `python -m venv .venv` |
| `libretime-api` (editable) | **Working** | `pip install -e backend\api` |
| `libretime-shared` (editable) | **Working** | `pip install -e backend\shared` |
| `psycopg2-binary` | **Working** | Installed manually; not in requirements |
| `pydantic` | **Working** | Constraint relaxed to `>=2.9` in `backend\shared\setup.py` — upstream had `<2.8` which has no Python 3.13 wheel |
| `gunicorn` | **NOT INSTALLED** | Unix-only; listed in `backend\api\requirements.txt` but skipped — replaced by Django dev server for now |
| `psycopg[c]` / `psycopg` (v3) | **NOT INSTALLED** | Requires Rust/MSVC to build on Windows; `psycopg2-binary` used instead |
| `uvicorn` | **Not tested** | In requirements; not used in current dev flow |

---

## 2. What Works

### 2.1 Interface layer (M2 — all green, 75 unit tests)

| Module | File | Status |
|---|---|---|
| PlayoutEngine ABC | `playout/engine_interface/` | **Interface only — no implementation** |
| StreamEgressManager ABC | `streams/egress/interface.py` | **Interface only** |
| StreamIngressManager ABC | `streams/ingress/interface.py` | **Interface only** |
| AudioDeviceManager ABC | `audio/soundcard/interface.py` | **Interface only** |
| JobRunner ABC | `backend/rastatime_worker/interface.py` | **Interface only** |
| ServiceHealth ABC | `infra/service_health/interface.py` | **Interface only** |

### 2.2 Dev scripts (M3)

| Script | Command | Status |
|---|---|---|
| Bootstrap checker | `.\infra\scripts\dev\bootstrap.ps1` | **Working** — checks Python, PostgreSQL, VLC, RabbitMQ |
| API dev server | `.\infra\scripts\dev\run-api.ps1` | **Working** — Django dev server on 127.0.0.1:8000 |
| Worker dev stub | `.\infra\scripts\dev\run-worker.ps1` | **Working** — logs "idle" heartbeat |

### 2.3 API server

| Feature | Status | Notes |
|---|---|---|
| `GET /health` | **Working** | Returns `{"status":"ok","service":"rastatime-api","version":"4.5.0"}` |
| `GET /api/v2/schema/swagger-ui` | **Not tested** | Requires DB (SQLite) with migrations applied |
| All other API routes | **Blocked** | Require `python manage.py migrate` first |
| Settings module | `libretime_api.settings.dev` | **Working** — no config file needed; SQLite by default |

### 2.4 Worker stub

| Feature | Status | Notes |
|---|---|---|
| `python -m rastatime_worker` | **Working** | Logs "idle" within 1s of start |
| Real job execution | **Not implemented** | Concrete `JobRunner` planned for Phase 8 (T16.x) |

---

## 3. What Is Stubbed or Disabled

| Component | Upstream Role | Current Status | Planned Fix |
|---|---|---|---|
| **Liquidsoap** | Core playout, stream dispatch | **Not started** — all `backend/playout/libretime_playout/liquidsoap/` code still present but untouched | Replace with libVLC (Phase 4, T6.x) |
| **Celery worker** | Background task execution | **Not started** — `backend/worker/libretime_worker/` uses Celery; not runnable on Windows without RabbitMQ + prefork | Replace with `rastatime_worker` (Phase 8, T16.x) |
| **Gunicorn** | WSGI server | **Skipped in dev** — Django dev server used instead | Replace with Waitress (T17.1) |
| **LibreTime playout** | `backend/playout/` | **Untouched** — Liquidsoap-dependent; not imported by dev server | Full replacement in Phase 4 |
| **LibreTime analyzer** | `backend/analyzer/` | **Untouched** — `_liquidsoap.py` pipeline step is Linux-only | Targeted stub in T3.5 |

---

## 4. Known Blockers

### B1 — No PostgreSQL in dev by default
- **Impact:** All API routes except `/health` are non-functional without a running PostgreSQL instance.
- **Workaround:** Dev settings use SQLite. Run `python manage.py migrate` once to create the schema, then all routes work.
- **Resolution:** T3.5 / Phase 8 — document PostgreSQL setup in operator docs.

### B2 — gunicorn in `requirements.txt`
- **Impact:** `pip install -r backend\api\requirements.txt` fails on Windows (gunicorn is Unix-only).
- **Workaround:** Use `pip install -e backend\api -e backend\shared` (editable install resolves deps individually; gunicorn installs but is simply not called).
- **Resolution:** T17.1 — replace gunicorn with Waitress; update requirements.

### B3 — psycopg v3 has no pre-built Windows wheel (at the pinned version)
- **Impact:** `psycopg[c]` listed in `requirements.txt` requires MSVC + Rust on Windows.
- **Workaround:** `pip install psycopg2-binary` installed manually.
- **Resolution:** Add `psycopg2-binary` (or `psycopg` pure-Python) to `requirements.txt` as a Windows-compatible alternative.

### B4 — Liquidsoap code not yet stubbed
- **Impact:** Importing `backend/playout/` or `backend/analyzer/` raises errors (Liquidsoap is not installed on Windows).
- **Workaround:** These modules are not imported by the dev API server (`libretime_api.settings.dev` does not load them).
- **Resolution:** T3.5 — add import guards / feature flags so these modules degrade gracefully.

### B5 — Celery worker not runnable
- **Impact:** `backend/worker/` depends on Celery prefork which is unreliable on Windows.
- **Workaround:** `run-worker.ps1` uses the new `rastatime_worker` stub instead.
- **Resolution:** Phase 8 (T16.x) — implement concrete `JobRunner` with APScheduler or equivalent.

### B6 — No libVLC / python-vlc installed
- **Impact:** Playout is entirely non-functional.
- **Workaround:** Playout is not started in the current dev flow.
- **Resolution:** Phase 4 (T6.x) — install VLC, add `python-vlc` to requirements, implement `VlcPlayoutEngine`.

---

## 5. Next Steps (Phase 3 onward)

| Task | Description |
|---|---|
| **T3.5** | Stub Liquidsoap/Celery import paths so `import libretime_playout` does not crash |
| **T4.1** | Implement `MockPlayoutEngine` (satisfies `PlayoutEngine` ABC, no audio) |
| **T4.2** | Config flag `PLAYOUT_ENGINE = "mock" \| "libvlc"` |
| **T6.x** | Implement `VlcPlayoutEngine` using python-vlc |
| **T16.x** | Implement concrete `JobRunner` (APScheduler-based) |
| **T17.1** | Replace gunicorn with Waitress |

---

## 6. Quick-Start for New Contributors

```powershell
# 1. Clone and enter repo
cd C:\RASTATIME

# 2. Check dependencies
.\infra\scripts\dev\bootstrap.ps1

# 3. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 4. Install packages
pip install -e backend\api -e backend\shared
pip install psycopg2-binary   # Windows workaround for B3

# 5. Apply SQLite migrations (one-time)
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.dev"
$env:PYTHONPATH = "backend\api;backend\shared"
python backend\api\libretime_api\manage.py migrate

# 6. Start API server (separate terminal)
.\infra\scripts\dev\run-api.ps1

# 7. Verify health
Invoke-RestMethod http://127.0.0.1:8000/health

# 8. Start worker stub (separate terminal)
.\infra\scripts\dev\run-worker.ps1
```
