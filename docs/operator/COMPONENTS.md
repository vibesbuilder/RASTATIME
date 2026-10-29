# COMPONENTS.md — Third-Party Components: Inventory, Classes, Update Procedure

**Status:** Accepted (operator decision 2026-10-09)
**Date:** 2026-10-09
**Applies to:** the production machine (RASTATIME runs from the Git checkout
`C:\RASTATIME`, see `WINDOWS_24_7.md`)

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
| Windows 11 Pro | A | 25H2, 26200.9711 (2026-10-23); BIOS M5OKT41A 1.65 | Windows Update, policy from `WINDOWS_24_7.md` (no automatic reboot) | Windows Update in the maintenance window, reboot by the operator | system restore point |
| RabbitMQ Server / Erlang OTP | A | 4.3.5 / 28.5.0.5 (erts 16.4.0.5), base `C:\ProgramData\RabbitMQ`, node `rabbit@RASTATIME` - the computer is named STUDIO, so the old name resolves through `drivers\etc\hosts` (127.0.0.1 / ::1, 2026-10-24); without that entry the broker boot-loops with `no_epmd_port` | rabbitmq.com installer | installer over the old version in the maintenance window, `Restart-Service RabbitMQ` | previous installer |
| Apache httpd | A | 2.4.68 | Apache Lounge (VS18 x64 zip); feed: endoflife.date/apache | unzip beside `C:\Tools\Apache24`, copy `conf\` + `modules\mod_fcgid.so`, `httpd -t`, restart `RASTATIME-APACHE` | rename `Apache24.prev` back |
| PHP | A | 8.5.12 (since 2026-10-22; OPcache loaded but `opcache.enable=0`, `session.upload_progress.enabled = Off`, see INSTALL_APACHE §3.2) | downloads.php.net/~windows/releases (NTS x64 zip + `sha256sum.txt`); feed: endoflife.date/php (8.5 security fixes until 2029-12-31) | unzip beside `C:\Tools\PHP` as `C:\Tools\PHP-<ver>`, copy `php.ini` + `cacert.pem` (the only own files), test the CLI with `-d extension_dir=` / `curl.cainfo=` pointing at the new folder; stop Apache with `infra\scripts\rt-apache-restart.ps1 -StopOnly` (waits for Stopped and stops orphaned `php-cgi.exe`, which lock the folder; INSTALL_APACHE §5.1/5.2), rename the folders, `rt-apache-restart.ps1 -StartOnly` (waits for Running, login 200), `php-cgi.exe` file version + smoke test | rename `C:\Tools\PHP-<previous>` back (8.3.36 kept as `C:\Tools\PHP-8.3.36`, 8.3.33 as `C:\Tools\PHP-8.3.33`) |
| win-acme | A | 2.2.9 | GitHub win-acme/win-acme | unzip, re-run the renewal task once | keep the previous folder |
| PostgreSQL | C | 17.7 | EDB installer; feed: endoflife.date/postgresql (17 until 2029-11) | minor releases via installer in the window, with a fresh backup; major upgrades (18) are a project (dump/restore, `MIGRATION.md`) | backup restore |
| Python | C | 3.13.14 | python.org; feed: endoflife.date/python | patch releases: install over, `.venv` keeps working; minor (3.14) = rebuild the venv | previous installer |
| Django | C | 5.2.18 (since 2026-10-10) | PyPI; feed: endoflife.date/django (5.2 LTS until 2028-04) | pin in `backend\api\requirements.txt`, `pip install -r`, restart API + PLAYOUT (both import the ORM) | `pip install` the previous pin |
| DRF 3.16, django-filter 25, django-cors-headers, waitress, psycopg2-binary, requests, urllib3, PyYAML, mutagen, bcrypt 5.0 (password hashes since 2026-10-27, `setup.py` of the API) | C | see `update_check.py` | PyPI | same as Django, within the pinned lines; `pip-audit` monthly | same |
| Legacy PHP packages (zf1s Zend 1, Propel 1, getID3, SimplePie, Symfony 5.4 yaml/config, phpseclib …) | C | `frontend\legacy\composer.lock` (99 packages); Composer 2.10.3 at `C:\Tools\composer\composer.phar` (`php C:\Tools\composer\composer.phar audit` in `frontend\legacy`); first audit 2026-10-10: phpseclib and symfony/yaml updated the same day, audit clean. CAUTION: most vendor folders are git-sourced checkouts owned by another Windows user (`vendor/<pkg>/.git`); composer cannot update them in place (`git show-ref` fails and the whole batch aborts, UI 500). Before updating such a package: delete its vendor folder, then `composer install --prefer-dist`; afterwards check `C:\Tools\Apache24\logs\error_log` for `PHP Fatal` (2026-10-10: the app answered 500 for 40 minutes while composer worked) | Packagist; `composer audit` | `composer update <pkg>` in a worktree, PHP lint + TEST_PLAN UI checks, commit the lock file | `git checkout composer.lock` + `composer install` |
| Icecast | B | 2.5.0 (win64, since 2026-10-24 14:02) in `C:\Tools\Icecast-2.5.0`; service RASTATIME-ICECAST points at it (NSSM Application + AppDirectory), config `config/icecast.xml` (git-ignored) with `<charset>UTF-8</charset>` on every output mount (the Windows build sends empty ICY titles without it) and an absolute `<mime-types>` | icecast.org / xiph.org downloads (SHA512SUMS.txt), installer unsigned - verify the hash | install beside into a new folder, test on port 8010 with `C:/Temp/optd/icecast25/ice25_test.py`, then `nssm set` Application/AppDirectory + `Restart-Service` (stop RASTATIME-STANDBY first, it depends on Icecast) | 2.4.4 kept in `C:\Tools\Icecast` + `config/icecast.xml.2.4.4-backup`: point the two NSSM values back, restore the file, restart |
| Liquidsoap | B | 2.4.6 on RASTATIME-LIQUIDSOAP (`C:\Tools\liquidsoap-v2.4.6`, since 2026-10-10) and on RASTATIME-STANDBY (same binary, since 2026-10-21); 2.4.4 stays in `C:\Tools\liquidsoap` as the fallback and the home of the scripts (`rastatime.liq`, `standby.liq`) | GitHub savonet/liquidsoap, asset `liquidsoap-<ver>-win64.zip` (official build, OCaml 4.14, stereotool/portaudio/ffmpeg inside) | bench on a second instance first (`liquidsoap --check`, 40 s run with Stereo Tool, memory, shutdown), then swap `C:\Tools\liquidsoap` in a quiet moment with the standby instance up | rename the previous folder back |
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
in a quiet moment with the standby instance keeping the listeners.  Icecast moved to 2.5.0 on
2026-10-24 after a test instance on port 8010; its exposure is covered by the reverse proxy.

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

1. `git status` clean, `git tag live-YYYY-MM-DD` (live-operation rule 1).
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

- A growing library slows every API call that counts it: after the 2026-10-09
  bulk import (198k files) `GET /api/v2/storage/location` took 2 s and the
  playout armed its start timers 1.7 s late.  Since 2026-10-10 the size is
  served from a 900 s cache and recounted in the background, and the playout
  takes its timer clock reference right before arming.  The refresh log line
  (`armed=... timers armed X s after the clock reference`) is the control.
- `pytest backend\api` on this machine needs `PYTHONUTF8=1`: the test
  database setup fails with a `UnicodeDecodeError` otherwise (German
  PostgreSQL messages in the console code page) - and
  `RASTATIME_CONFIG_FILEPATH=C:\RASTATIME\config\rastatime.conf`, because
  the testing settings otherwise fall back to the upstream default
  credentials and every `django_db` test errors.  `scripts\run_tests.ps1`
  sets both (plus `PYTHONPATH` and `--basetemp`) for all three suites.
- The legacy PHP test suite (`frontend\legacy\tests`, PHPUnit 4 era,
  `PHPUnit_Framework_TestCase`) is not runnable: PHPUnit is not installed
  and the tests predate PHP 8.  Legacy logic is verified with bootstrapped
  probe scripts (`C:\Temp\optd\*.php`, pattern `importexport_test.php`);
  reviving PHPUnit is a BACKLOG item (🟡).
- The Liquidsoap Windows build leaks ~5 KB per `Unix.select`
  (`docs\upstream\2026-09-05-...`); a new release does not fix this unless
  the OCaml runtime changes — check `--build-config` after an update.
- Django 4.2 LTS left extended support on 2026-04-07; upgraded to 5.2 LTS on
  2026-10-10 after a clean dry run (scratch venv, API/playout/unit suites).
  The pins live in `backend\api\setup.py`; `requirements.txt` is generated
  from it (edit both, then `pip install --no-deps -e backend\api` so the
  editable metadata follows).
