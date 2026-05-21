# Contributing to RASTATIME

Thank you for your interest in RASTATIME.

RASTATIME is a **Windows-first functional fork of LibreTime**. Before contributing, please read this document and `AGENTS.md` carefully — both define the design constraints that all changes must respect.

---

## Table of contents

1. [Non-goals — read before opening a PR](#non-goals)
2. [Development environment](#development-environment)
3. [Running tests](#running-tests)
4. [Code style](#code-style)
5. [Branching and commit conventions](#branching-and-commit-conventions)
6. [Pull request checklist](#pull-request-checklist)
7. [License](#license)

---

## Non-goals

The following are **explicit non-goals** for this project. Pull requests that move in these directions will be closed:

- Making RASTATIME run on Linux (Windows 11 is the only supported platform)
- Reintroducing Liquidsoap as the primary playout engine
- Reintroducing Celery as the task runner
- Adding `systemd`, `systemctl`, or Linux-only shell scripts as a primary runtime mechanism
- Large speculative refactors without a clear, task-linked need
- Introducing optional platform targets (e.g. macOS, WSL) as first-class concerns

If you are uncertain whether a change fits the project direction, open an issue first.

---

## Development environment

### Prerequisites

| Tool | Notes |
|---|---|
| Windows 11 | Only supported platform |
| Python 3.12+ | 3.13 tested |
| PostgreSQL 14+ | Windows installer |
| RabbitMQ 3.x | With management plugin |
| PHP 8.1+ | For the legacy frontend |
| Git | Any recent version |

### Setup

```powershell
# 1. Clone
git clone https://github.com/<your-org>/rastatime.git C:\RASTATIME
cd C:\RASTATIME

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install all backend packages in editable mode
pip install -e "backend\shared"
pip install -e "backend\api-client"
pip install -e "backend\api[dev]"
pip install -e "backend\worker"
pip install -e "backend\playout"
pip install -e "backend\analyzer"

# 4. Runtime configuration
Copy-Item config\libretime.conf.example C:\rastatime\config\libretime.conf
# Edit C:\rastatime\config\libretime.conf with your local DB/RabbitMQ credentials

# 5. Database
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"
cd backend\api
python manage.py migrate
cd ..\..
```

---

## Running tests

### Unit tests (no server or database required)

```powershell
python -m pytest tests\unit\ -v
```

### Shared-package tests

```powershell
$env:PYTHONPATH = "backend\shared"
python -m pytest backend\shared\tests\ -v
```

### Django API tests (requires PostgreSQL)

```powershell
cd backend\api
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.testing"
python -m pytest tests\ -v
cd ..\..
```

### Worker tests

```powershell
$env:PYTHONPATH = "backend\worker"
python -m pytest backend\worker\tests\ -v
```

All CI-relevant tests must pass before a pull request is merged.

---

## Code style

### Python

- Follow **PEP 8** with a line length of **100 characters**.
- Use **type hints** on all new public functions and methods.
- Use `snake_case` for functions, variables, and module names; `PascalCase` for classes.
- Do not use Linux-only imports (`grp`, `pwd`, `fcntl`, etc.) without a Windows fallback.
- Run `ruff check backend` and `ruff format --check backend` before pushing.
  Both are enforced by CI (see [Continuous integration](#continuous-integration)).

### PHP (frontend/legacy)

- Match the existing code style in `frontend/legacy/`.
- Do not introduce new Linux-only shell calls (`exec('systemctl …')`, `shell_exec('which …')`).
- Service status checks must use `sc query <RASTATIME-SERVICE-NAME>`.

---

## Continuous integration

Two GitHub Actions workflows run on every push and pull request:

| Workflow | File | Hard-fails on |
|---|---|---|
| `python` | `.github/workflows/python.yml` | `ruff` lint or format violations in `backend/`; failing pytest in `analyzer`, `api-client`, `playout`, `shared` |
| `php`    | `.github/workflows/php.yml`    | `composer install` failure; PHP syntax errors anywhere in `frontend/legacy/application/` |

The `api` and `worker` Python packages are not in CI yet — they need
PostgreSQL / RabbitMQ service containers, which we add once the test
fixtures stabilise.  PHPUnit currently runs as **warning-only** for the
same reason.

Ruff configuration lives in `/.ruff.toml` (repo root).  Override it
locally only if you really must — match the CI default to avoid
"works on my machine" surprises.

---

## Releasing

RASTATIME follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **Major** (`X.0.0`) — breaking changes to the operator-facing surface
  (config layout, NSSM service names, schema).  Pre-1.0 we may break
  freely, but call it out clearly in `CHANGELOG.md`.
- **Minor** (`0.Y.0`) — new features, backwards-compatible.
- **Patch** (`0.0.Z`) — bug fixes only.

### Cutting a release

1. Move the `[Unreleased]` block in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading. Add a fresh empty `[Unreleased]`
   on top.
2. Update the comparison link at the bottom of `CHANGELOG.md`.
3. Commit:
   ```
   git commit -am "release: vX.Y.Z"
   ```
4. Tag and push:
   ```
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```
5. The `release` workflow (`.github/workflows/release.yml`) takes over:
   - Builds wheels for every package in `backend/`.
   - Zips the legacy PHP frontend with `vendor/` included.
   - Creates the GitHub release, pulling the matching `CHANGELOG.md`
     section as release notes, and attaches all wheels + the frontend
     zip as downloadable assets.
6. Verify the release page on GitHub. If anything is off, you can
   re-run the release workflow manually from
   *Actions → release → Run workflow*.

### General

- **English only** for code, identifiers, comments, commit messages, and documentation.
- German appears only in translation files (`frontend/legacy/locale/`, Django `.po` files).
- Windows paths use forward slashes in Python strings or raw strings (`r"C:\…"`).
  Never hard-code `/etc`, `/var`, `/srv`, or other Linux paths.

---

## Branching and commit conventions

### Branch names

```
feat/<task-id>-<short-description>    # new feature
fix/<task-id>-<short-description>     # bug fix
refactor/<task-id>-<short-description>
docs/<short-description>
```

Examples:

```
feat/t-gh-7-github-actions-ci
fix/t-op-3-api-port-conflict
```

### Commit messages

Use the imperative mood, present tense:

```
Add WASAPI system output to shared config model
Remove ALSASystemOutput and PortAudioSystemOutput
Fix sc query service check in check.php
```

- First line: ≤ 72 characters, no trailing period.
- Optional body after a blank line explaining *why*, not *what*.
- Reference the task ID when applicable: `Closes T-GH-4`.

---

## Pull request checklist

Before requesting a review, confirm:

- [ ] All existing unit tests pass (`python -m pytest tests\unit\ -v`)
- [ ] New code is covered by at least one test
- [ ] No `systemctl`, `systemd`, ALSA, PortAudio, Liquidsoap, or Celery references introduced
- [ ] No Linux-only paths (`/etc`, `/srv`, `/var`) introduced
- [ ] `config/libretime.conf` is **not** included in the commit
- [ ] Commit messages follow the conventions above
- [ ] `AGENTS.md` non-goals are respected

---

## License

By contributing to RASTATIME you agree that your contributions will be licensed
under the **GNU Affero General Public License v3.0 (AGPL-3.0)**, the same
license that covers the project. See [`LICENSE`](LICENSE) for the full text.

RASTATIME is a derivative work of LibreTime, which is also licensed under AGPL-3.0.
