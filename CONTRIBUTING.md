# Contributing to RASTATIME

Thank you for your interest in RASTATIME.

RASTATIME is a **Windows-first functional fork of LibreTime**.  This document
defines the design constraints every change must respect, and how to set up
a development environment, run the tests and submit a change.

---

## Table of contents

1. [Project identity and goals](#project-identity-and-goals)
2. [Non-goals](#non-goals)
3. [Source-of-truth order](#source-of-truth-order)
4. [Platform rules](#platform-rules)
5. [Core architecture rules](#core-architecture-rules)
6. [Language and naming rules](#language-and-naming-rules)
7. [Implementation style](#implementation-style)
8. [Documentation](#documentation)
9. [Development environment](#development-environment)
10. [Running tests](#running-tests)
11. [Code style](#code-style)
12. [Continuous integration](#continuous-integration)
13. [Releasing](#releasing)
14. [Branching and commit conventions](#branching-and-commit-conventions)
15. [Pull request checklist](#pull-request-checklist)
16. [License](#license)

---

## Project identity and goals

The goal is **not** a generic radio automation system from scratch and
**not** a direct port of Airtime.  LibreTime is the functional baseline;
Airtime is only a secondary historical reference when older architecture,
widgets or undocumented behaviour need clarification.

1. Preserve the **core user-visible functionality and workflows of
   LibreTime** as far as practical.
2. Replace Linux-bound runtime layers with **Windows 11 compatible
   implementations**.
3. Use **Liquidsoap (savonet Windows build) as the playout engine**, driven
   by the playout service over telnet; Icecast carries the streams.
4. Keep the system **English-first** in code, config, API design, internal
   docs and default UI wording.
5. Ship the UI and the manual in **English, German, French and Spanish**;
   every other language is a translation layer only.
6. Favour **small, reversible, low-risk implementation steps**.

---

## Non-goals

The following are explicit non-goals.  Pull requests that move in these
directions will be closed:

- Making RASTATIME run on Linux (Windows 11 is the only supported platform)
- Reintroducing Celery as the task runner
- Adding `systemd`, `systemctl` or Linux-only shell scripts as a primary
  runtime mechanism
- Replacing the playout engine without an architecture decision record
- Reintroducing Airtime-specific legacy behaviour unless required to
  preserve LibreTime-compatible functionality
- Large speculative refactors without a clear, task-linked need
- Introducing optional platform targets (macOS, WSL) as first-class concerns

If you are uncertain whether a change fits the project direction, open an
issue first.

---

## Source-of-truth order

When reasoning about architecture and implementation, use this order:

1. `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` (the living architecture document,
   section 23 holds the decision log)
2. The documents under `docs/architecture/`
3. LibreTime official documentation
4. LibreTime official repository
5. LibreTime community forum / discussions
6. Airtime documentation / forum only for historical gaps or widget behaviour

If sources conflict, prefer the project architecture document for
target-state decisions and the official LibreTime sources for current-state
behaviour; treat Airtime as reference only.

---

## Platform rules

- Primary target: **Windows 11**.  Development and runtime decisions must be
  valid for Windows 11 first.
- The system must start automatically after a reboot; **NSSM** is the
  service wrapper unless the architecture document says otherwise.
- Linux-specific service or deployment behaviour is not portable by default.
  Do not introduce or depend on `systemd`, `systemctl`, Linux-only path
  conventions, Linux-only shell scripts as the primary runtime mechanism, or
  UNIX-only servers where a Windows-safe alternative is required.  When
  Linux-specific code is encountered: isolate it, document it, replace or
  abstract it.

---

## Core architecture rules

**Functional baseline.**  Preserve shows, scheduling, playlists, webstreams,
calendar behaviour, media library behaviour, playout history and reporting,
and the core radio automation workflows.

**Playout engine.**  Liquidsoap renders the programme (files, webstreams,
line-in, DJ harbor) and feeds Icecast and the local sound card.  The playout
service owns the schedule and drives Liquidsoap over telnet.  Do not
reintroduce a second engine; changes to the engine contract need an entry in
the architecture document.

**RASTATIME-specific features.**  Windows-first features that LibreTime
does not have as first-class features are required target features, not
experiments: multiple local **stereo line-in** sources, the **Soundcard**
settings page, explicit local input/output device mapping, the
Windows-native service startup model, planned restarts for 24/7 programmes.

---

## Language and naming rules

**English** is the canonical language for code, filenames, folder names,
classes, functions, variables, enums, API routes, database fields, migration
names, config keys, internal documentation, commit messages and default UI
labels.

UI languages: English (default), German, French and Spanish, implemented as
translation layers (`frontend/legacy/locale/`, Django `.po` files).  The
operator manual under `docs/manual/` exists in the same four languages;
English is written first, the other three follow from it.

Avoid mixed-language identifiers, non-English database field names or API
paths, and ambiguous abbreviations unless already well established in the
project.

---

## Implementation style

**Work in very small steps.**  Prefer small atomic commits, reversible edits,
narrow implementation slices, minimal viable scaffolding first and
validation after each meaningful change.  Avoid giant all-in-one rewrites,
changing many subsystems at once unless required, and mixing architecture
redesign with feature delivery in one step.

**Before coding**: state the objective, identify the affected modules and
files, identify prerequisites, note risks or ambiguities.  Architecture
choices get a short written evaluation (feasibility, architectural impact,
effort, duration, benefit, risk, recommendation) before any code.

**After coding**: summarise what changed, list the validation steps performed
or still needed, note open issues, and update `CHANGELOG.md`.

**Decision policy** when a choice is unclear: choose the smallest reversible
implementation, prefer explicit abstractions over hidden coupling, prefer
Windows-safe solutions, preserve LibreTime-compatible behaviour where
practical, document ambiguity instead of pretending certainty.  Add a new
feature only if the architecture document requires it; otherwise mark it as
a recommendation.

**Testing expectations**: unit tests for isolated business logic,
integration tests for API behaviour, smoke tests for startup and runtime
wiring, and written manual validation steps for audio, device and stream
behaviour where automation is not yet practical.  Do not leave validation
implicit.

---

## Documentation

Project documentation stays in Markdown:

- `README.md` - overview and quick start
- `CONTRIBUTING.md` - this file
- `CHANGELOG.md` - every code or architecture change gets an entry (Added /
  Changed / Fixed / Removed / Security, with date and reason).  Do not skip
  this.
- `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` - architecture and decision log;
  bump the document version for architecture-relevant changes
- `BACKLOG.md` - evaluated but not yet implemented topics
- `docs/operator/` - install, upgrade, migration and runbooks
- `docs/manual/` - the operator manual in four languages

The repository separates backend, frontend, playout, audio/soundcard
abstractions, worker/background jobs, infrastructure/service scripts, docs
and tests at the top level.

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
git clone https://github.com/vibesbuilder/RASTATIME.git C:\RASTATIME
cd C:\RASTATIME

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install all backend packages in editable mode
pip install -e "backend\shared"
pip install -e "backend\api-client"
pip install -e "backend\api[dev]"
pip install -e "backend\playout"
pip install -e "backend\analyzer"
# (the worker runs from the checkout: python -m rastatime_worker with
#  C:\RASTATIME\backend on PYTHONPATH)

# 4. Runtime configuration
Copy-Item config\rastatime.conf.example C:\rastatime\config\rastatime.conf
# Edit C:\rastatime\config\rastatime.conf with your local DB/RabbitMQ credentials

# 5. Database
$env:RASTATIME_CONFIG_FILEPATH = "C:\rastatime\config\rastatime.conf"
cd backend\api
python manage.py migrate
cd ..\..
```

---

## Running tests

The runner `scripts\run_tests.ps1` sets the environment the suites need
(`RASTATIME_CONFIG_FILEPATH`, `PYTHONUTF8=1`, `PYTHONPATH`, a writable
`--basetemp`) and runs the three suites:

```powershell
.\scripts\run_tests.ps1               # api + playout + unit
.\scripts\run_tests.ps1 -Suite unit   # one suite
.\scripts\run_tests.ps1 -Suite api -Path rastatime_api/storage -PytestArgs -x
```

Individually:

```powershell
# Unit tests (no server or database required)
python -m pytest tests\unit\ -v

# Shared-package tests
$env:PYTHONPATH = "backend\shared"
python -m pytest backend\shared\tests\ -v

# Django API tests (requires PostgreSQL)
cd backend\api
$env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.testing"
python -m pytest rastatime_api -v
cd ..\..

# Playout tests
cd backend\playout
python -m pytest tests -v
cd ..\..
```

All CI-relevant tests must pass before a pull request is merged.

---

## Code style

### Python

- Follow **PEP 8** with a line length of **100 characters**.
- Use **type hints** on all new public functions and methods.
- Use `snake_case` for functions, variables and module names; `PascalCase`
  for classes.
- Do not use Linux-only imports (`grp`, `pwd`, `fcntl`, ...) without a
  Windows fallback.
- Run `ruff check backend` and `ruff format --check backend` before pushing.
  Both are enforced by CI (see [Continuous integration](#continuous-integration)).

### PHP (frontend/legacy)

- Match the existing code style in `frontend/legacy/`.
- Do not introduce new Linux-only shell calls (`exec('systemctl ...')`,
  `shell_exec('which ...')`).
- Service status checks must use `sc query <RASTATIME-SERVICE-NAME>`.
- Classes under `frontend/legacy/application/` are found through the
  Composer classmap: after adding or renaming a class run
  `php composer.phar dump-autoload` in `frontend/legacy`.

### General

- **English only** for code, identifiers, comments, commit messages and
  documentation.
- Windows paths use forward slashes in Python strings or raw strings
  (`r"C:\..."`).  Never hard-code `/etc`, `/var`, `/srv` or other Linux paths.

---

## Continuous integration

Two GitHub Actions workflows run on every push and pull request:

| Workflow | File | Hard-fails on |
|---|---|---|
| `python` | `.github/workflows/python.yml` | `ruff` lint or format violations in `backend/`; failing pytest in `analyzer`, `api-client`, `playout`, `shared` |
| `php`    | `.github/workflows/php.yml`    | `composer install` failure; PHP syntax errors anywhere in `frontend/legacy/application/` |

The `api` and `worker` Python packages are not in CI yet - they need
PostgreSQL / RabbitMQ service containers, which we add once the test
fixtures stabilise.  PHPUnit currently runs as **warning-only** for the
same reason.

Ruff configuration lives in `/.ruff.toml` (repo root).  Override it locally
only if you really must - match the CI default to avoid "works on my
machine" surprises.

---

## Releasing

RASTATIME follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **Major** (`X.0.0`) - breaking changes to the operator-facing surface
  (config layout, NSSM service names, schema).  Pre-1.0 we may break
  freely, but call it out clearly in `CHANGELOG.md`.
- **Minor** (`0.Y.0`) - new features, backwards-compatible.
- **Patch** (`0.0.Z`) - bug fixes only.

### Cutting a release

1. Move the `[Unreleased]` block in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading.  Add a fresh empty `[Unreleased]`
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
6. Verify the release page on GitHub.  If anything is off, re-run the
   release workflow manually from *Actions -> release -> Run workflow*.

---

## Branching and commit conventions

### Branch names

```
feat/<task-id>-<short-description>    # new feature
fix/<task-id>-<short-description>     # bug fix
refactor/<task-id>-<short-description>
docs/<short-description>
```

### Commit messages

Use the imperative mood, present tense:

```
Add WASAPI system output to shared config model
Remove ALSASystemOutput and PortAudioSystemOutput
Fix sc query service check in check.php
```

- First line: <= 72 characters, no trailing period.
- Optional body after a blank line explaining *why*, not *what*.
- Reference the task or backlog item when applicable.

---

## Pull request checklist

Before requesting a review, confirm:

- [ ] All existing tests pass (`.\scripts\run_tests.ps1`)
- [ ] New code is covered by at least one test
- [ ] No `systemctl`, `systemd`, ALSA, PortAudio or Celery references introduced
- [ ] No Linux-only paths (`/etc`, `/srv`, `/var`) introduced
- [ ] `config/rastatime.conf` is **not** included in the commit
- [ ] `CHANGELOG.md` has an entry; the manual is updated in all four
      languages when operator-visible behaviour changed
- [ ] Commit messages follow the conventions above
- [ ] The non-goals above are respected

---

## License

By contributing to RASTATIME you agree that your contributions will be
licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**,
the same license that covers the project.  See [`LICENSE`](LICENSE) for the
full text.

RASTATIME is a derivative work of LibreTime, which is also licensed under
AGPL-3.0.
