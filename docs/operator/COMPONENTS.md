# COMPONENTS.md — Third-Party Components: Inventory, Classes, Update Procedure

**Status:** Accepted (operator decision 2026-10-09)
**Date:** 2026-10-09
**Applies to:** the production machine (RASTATIME runs from the Git checkout
`C:\RASTATIME`, see `ASSISTANT.local.md` / `WINDOWS_24_7.md`)

`UPGRADE.md` covers RASTATIME releases themselves.  This document covers
everything RASTATIME runs on: which version is installed, where it comes
from, how fast it has to follow upstream, how it is updated and how it is
rolled back.  `scripts\update_check.py` compares the installed versions
with the upstream release feeds and is the first step of every maintenance
window.

---

## 1. Inventory (checked 2026-10-09)

| Component | Class | Installed | Source / feed | Update path | Rollback |
|---|---|---|---|---|---|
| Windows 11 Pro | A | 26200 | Windows Update, policy from `WINDOWS_24_7.md` (no automatic reboot) | Windows Update in the maintenance window, reboot by the operator | system restore point |
| Apache httpd | A | 2.4.68 | Apache Lounge (VS18 x64 zip); feed: endoflife.date/apache | unzip beside `C:\Tools\Apache24`, copy `conf\` + `modules\mod_fcgid.so`, `httpd -t`, restart `RASTATIME-APACHE` | rename `Apache24.prev` back |
| PHP | A | 8.3.33 | windows.php.net (NTS x64 zip); feed: endoflife.date/php (8.3 security fixes until 2027-12-31) | unzip beside `C:\Tools\PHP`, copy `php.ini` + `ext\` choices, `php -v`, restart Apache | rename `PHP.prev` back |
| win-acme | A | 2.2.9 | GitHub win-acme/win-acme | unzip, re-run the renewal task once | keep the previous folder |
| PostgreSQL | C | 17.7 | EDB installer; feed: endoflife.date/postgresql (17 until 2029-11) | minor releases via installer in the window, with a fresh backup; major upgrades (18) are a project (dump/restore, `MIGRATION.md`) | backup restore |
| Python | C | 3.13.14 | python.org; feed: endoflife.date/python | patch releases: install over, `.venv` keeps working; minor (3.14) = rebuild the venv | previous installer |
| Django | C | 4.2.30 | PyPI; feed: endoflife.date/django | pin in `backend\api\requirements.txt`, `pip install -r`, restart API + PLAYOUT (both import the ORM) | `pip install` the previous pin |
| DRF, django-filter, django-cors-headers, waitress, psycopg2-binary, requests, urllib3, PyYAML, mutagen | C | see `update_check.py` | PyPI | same as Django, within the pinned lines; `pip-audit` monthly | same |
| Legacy PHP packages (zf1s Zend 1, Propel 1, getID3, SimplePie, Symfony 5.4 yaml/config, phpseclib …) | C | `frontend\legacy\composer.lock` (99 packages) | Packagist; `composer audit` | `composer update <pkg>` in a worktree, PHP lint + TEST_PLAN UI checks, commit the lock file | `git checkout composer.lock` + `composer install` |
| Icecast | B | 2.4.4 | icecast.org (last release 2022, project dormant); the public stream goes through the Apache reverse proxy | none expected; only on a published fix | keep the previous folder |
| Liquidsoap | B | 2.4.4 | GitHub savonet/liquidsoap, asset `liquidsoap-<ver>-win64.zip` (official build, OCaml 4.14, stereotool/portaudio/ffmpeg inside) | bench on a second instance first (`liquidsoap --check`, 40 s run with Stereo Tool, memory, shutdown), then swap `C:\Tools\liquidsoap` in a quiet moment with the standby instance up | rename the previous folder back |
| ffmpeg | B | 9.0.1 | gyan.dev essentials build; feed: endoflife.date/ffmpeg | unzip over `C:\ffmpeg` in the window (used by the analyzer, cue-point detection, line-in capture) | keep the previous folder |
| Stereo Tool library | B | 11.05 | thimeo.com (licence pending) | only together with a preset/licence change; the lockout fallback restarts without it if the fresh instance dies | previous DLL |
| nssm, Autologon64 | – | stable | nssm.cc, Sysinternals | practically never | – |

The installed column goes stale; `scripts\update_check.py` is the truth.

## 2. Classes and tempo

**Class A — exposed to the network (Apache, PHP, win-acme, Windows).**
Security releases within one to two weeks.  Apache Lounge and PHP are zip
drop-ins: keep the old folder as `.prev`, unpack the new one, carry the
configuration over, test (`httpd -t`, `php -v`), restart, run the short
TEST_PLAN checks.  Rollback is a rename.

**Class B — the audio chain (Liquidsoap, Icecast, ffmpeg, Stereo Tool).**
Only on demand: a published fix for a problem we have, or a feature we
want.  Never on principle.  Liquidsoap only after a bench on a second
instance (the Stereo Tool rehearsal of 2026-10-02 is the template), swapped
in a quiet moment with the standby instance keeping the listeners.  Icecast
is frozen; its exposure is covered by the reverse proxy.

**Class C — code dependencies (pip, composer, PostgreSQL, Python).**
Monthly: `update_check.py`, `pip-audit`, `composer audit`.  Patch releases
inside the pinned lines go in with the next window after the test suites
(`pytest backend\playout\tests`, `pytest backend\api` with
`PYTHONUTF8=1`, `pytest tests\unit`).  A new major line (Django LTS,
PostgreSQL major, Python minor) is a project with its own evaluation,
dry run in a scratch venv and BACKLOG entry.

## 3. The maintenance window

Monthly, in the morning after the nightly restart and the 03:30 backup
(e.g. the first working day after Patch Tuesday), when nothing is on air
or only files play:

1. `git status` clean, `git tag live-YYYY-MM-DD` (assistant.local rule 1).
2. `python scripts\update_check.py` → decide per component.
3. Fresh database backup (Settings → Backup, or wait for the 03:30 run).
4. Updates in the order Class A, Class C, Class B (B only if planned).
5. Restart order from `RESTART_ORDER.md`; verify with the short checks of
   `TEST_PLAN.md` (stream reachable, DJ login, a scheduled track, line-in,
   24/7 recording writing).
6. Note the new versions in §1 and commit.

Anything that fails: rename the `.prev` folder back or reinstall the
previous pin, restart, then investigate.

## 4. Known lore

- `pytest backend\api` on this machine needs `PYTHONUTF8=1`: the test
  database setup fails with a `UnicodeDecodeError` otherwise (German
  PostgreSQL messages in the console code page).
- The Liquidsoap Windows build leaks ~5 KB per `Unix.select`
  (`docs\upstream\2026-09-05-...`); a new release does not fix this unless
  the OCaml runtime changes — check `--build-config` after an update.
- Django 4.2 LTS left extended support on 2026-04-07; the 5.2 LTS dry run of
  2026-10-09 (scratch venv, API/playout/unit suites) was clean — see
  `BACKLOG.md`.
