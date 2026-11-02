# INSTALL_PROBE.md — Fresh-machine installation rehearsal

> GitHub publication, phase 5 (2026-11-01).  Nobody has installed RASTATIME
> from `INSTALL.md` since the baseline; the studio machine grew by hand.
> Before the repository goes public, one installation on a **fresh
> Windows 11 VM** follows the documentation to the letter.  Every
> deviation is a documentation bug (fix the docs, not the VM) or a product
> bug (BACKLOG).  This file is the protocol: fill the right-hand columns
> while you go, keep it in the repo afterwards.

## 0. Rules of the rehearsal

- The VM is not the studio machine: no production secrets, no real
  listener URLs, a throw-away database.  Use the placeholder values from
  `config\rastatime.conf.example` except where INSTALL.md says to generate
  a secret (generate throw-away ones).
- Follow `docs\operator\INSTALL.md` top to bottom, then
  `INSTALL_APACHE.md` where it points there.  Do not improvise: when a
  step is unclear or fails, write it down (section, what happened, what
  you did instead) and continue with the fix.
- Time every section; the total tells the next operator what to expect.
- Checkpoint the VM before Step 9 (services) so a failed service round
  can be retried without reinstalling the prerequisites.

## 0b. How to run it on a VirtualBox VM with coding assistant (2026-11-01)

The operator does the parts that need a human hand (installers, GitHub
login, browser); a coding assistant session **inside the VM** does the
command-line parts of INSTALL §4-§6 and fills the protocol.  The split
keeps the rehearsal honest: assistant knows the code and would paper over a
documentation gap without noticing, so its brief is to follow INSTALL.md
literally and to stop and report instead of improvising.

**A. The VM (operator, ~30 min + Windows setup).**  VirtualBox 7.x on a
machine that is not the studio computer.  New VM: Windows 11, 4 CPUs,
8 GB RAM, 80 GB disk, EFI + Secure Boot + TPM 2.0 enabled, audio controller
on (Intel HD Audio, output to the host), network **NAT** (internet for
downloads and the clone; everything is tested from inside the VM, so no
Host-Only or Bridged adapter).  Install Windows 11 with a local account,
run Windows Update once, install the Guest Additions (clipboard, shared
folder), snapshot `01-clean`.

**B. Git, clone, prerequisites (operator, ~1.5 h).**  Install Git for
Windows (default options), then in PowerShell:

```powershell
git clone https://github.com/vibesbuilder/RASTATIME.git C:\rastatime
```

The repository is private: Git Credential Manager opens a browser login
once.  Then work through INSTALL.md §2.0-§2.8 and INSTALL_APACHE.md by
hand - every installer and download is yours (the table in §2 below lists
versions and sources).  Finish with the checker:

```powershell
cd C:\rastatime
powershell -ExecutionPolicy Bypass -File infra\scripts\dev\bootstrap.ps1
```

All ten required lines `[PASS]`, exit 0.  Snapshot `02-prereqs`.  Note the
minutes of every §2 section in the protocol table (§3 below).

**C. coding assistant in the VM (operator, ~10 min).**  Install the coding assistant
for Windows following the current setup page
((the assistant's setup guide) Git for Windows from
step B is a prerequisite), start it in `C:\rastatime` and sign in with
your own account.  The VM session has no memory of the studio machine: the
repository is its only context.  Give the clone a commit identity first -
a fresh Git for Windows has none, and the session's first commit fails with
`Author identity unknown` (2026-11-01):
`git -C C:\rastatime config user.name "..."` and `... config user.email "..."`
(repo-local, not `--global`).

**D. The brief for the VM session (copy as the first message).**

> Run the installation rehearsal described in docs/operator/INSTALL_PROBE.md.
> The prerequisites of INSTALL.md §2 are installed and bootstrap.ps1 is
> green.  Do INSTALL.md §4 Step 1 (already cloned) to Step 10 and the §6
> checklist **exactly as written**.  Rules: do not improvise and do not
> repair anything silently - when a step is unclear, fails or does not
> match the machine, stop, write the row into the protocol table of
> INSTALL_PROBE.md (result `doc` or `bug`, what happened) and ask me before
> you continue.  Time every step.  Downloads and installers are mine, ask
> me.  Secrets: generate throw-away values with the command in Step 5,
> never show them in the chat.  Work on a branch `probe/vm-2026-11`,
> commit the protocol and every documentation fix there, push when I say
> so.

**E. Browser acceptance (operator, in the VM's browser, ~20 min).**  After
Step 10: `http://localhost/` - login `admin` / `admin`, change the password
(Settings → Users); upload a short MP3 (Library → Upload) and watch it
leave "Pending Import", then open its track editor: cue in / cue out must
not be 0 / full length; create a show for the next quarter hour with that
file (Calendar), then `http://localhost:8000/` shows the mount with the
title while it plays; finally `Restart-Computer` and `status.ps1` after
the boot.  Tell the VM session the results, it writes §4 of the protocol.

**F. Hand-back (operator + studio session).**  The VM session pushes
`probe/vm-2026-11`; the studio session reviews the protocol and the fixes,
merges them into `master` and files product bugs in BACKLOG.md.  Keep the
VM (snapshot `03-installed`) until phase 6 - the release test runs on it.

## 1. The machine

| Item | Value |
|---|---|
| Windows 11 edition / build | Windows 11 Pro N, 26200.6584 (VirtualBox VM) |
| CPU / RAM / disk | i3-1315U, 4 vCPU / **4 GB** (§0b A asks for 8) / 80 GB, 44 GB free after §2 |
| Network: internet during install (downloads) | yes |
| Audio device present (playout output test) | yes (High Definition Audio) |
| Date of the rehearsal | 2026-11-01 |
| Commit / tag installed (`git rev-parse --short HEAD`) | `ee7ccbb9` (master) |

## 2. Prerequisites, tool by tool (versions as on the studio machine, 2026-11-01)

Two kinds of components: **installers** that may keep their default
location (Program Files), and **zips / single files** that RASTATIME
expects at a fixed path under `C:\Tools\` or `C:\ffmpeg\` because the
service installers, `bootstrap.ps1` and the Apache/PHP configuration
point there.  Where the installer offers a destination, the line below
says which one to pick.  Run every installer **as administrator**; the
order is the order of INSTALL.md §2.

**T0 Windows (INSTALL §2.0).**  Smart App Control off (Windows Security →
App & browser control) before anything else; on the VM a static address is
not needed (NAT).

**T1 Visual C++ Redistributable x64 (INSTALL_APACHE §1).**  Microsoft
`vc_redist.x64.exe`, latest.  Installer, default location.  Needed by
Apache, PHP and Liquidsoap - without it they exit silently.

**T2 Git for Windows (Step 1).**  git-scm.com installer, default
location (`C:\Program Files\Git`), default options.  Brings Git Bash,
which the analyzer fixture generator and coding assistant use.  Check:
`git --version`.

**T3 Python 3.13 (INSTALL §2.1).**  python.org 64-bit installer.  Tick
**"Add python.exe to PATH"**, choose **"Install for all users"**
(services run as LocalSystem), otherwise defaults.  Check:
`python --version`.

**T4 PostgreSQL 17 (INSTALL §2.2).**  EnterpriseDB installer, default
location `C:\Program Files\PostgreSQL\17`, components **PostgreSQL Server**
and **Command Line Tools** (pgAdmin optional, skip Stack Builder), port
5432, locale default.  Note the superuser password you set (throw-away on
the VM).  Afterwards add `C:\Program Files\PostgreSQL\17\bin` to the
**system** PATH (Settings → System → Advanced → Environment variables) and
open a new PowerShell.  Set `listen_addresses = 'localhost'` in
`data\postgresql.conf` and restart the service (INSTALL §2.2 step 5).
Check: `pg_isready -h 127.0.0.1 -p 5432`.

**T5 Liquidsoap 2.4.6 (INSTALL §2.3).**  Zip
`liquidsoap-2.4.6-win64.zip` from github.com/savonet/liquidsoap/releases.
No installer: create `C:\Tools\liquidsoap\` and extract so that
`C:\Tools\liquidsoap\liquidsoap.exe` exists **directly** in that folder
(if the zip unpacks into a sub-folder, move its content one level up).
The folder also receives the rendered `rastatime.liq` later.  Check:
`& C:\Tools\liquidsoap\liquidsoap.exe --version`.

**T6 Erlang OTP, then RabbitMQ 4.x (INSTALL §2.4).**  Two installers from
rabbitmq.com (Erlang first, the version the RabbitMQ page names), both at
their default locations, defaults throughout; RabbitMQ registers its
Windows service itself.  Then the RabbitMQ `sbin` folder onto the system
PATH, the service's Erlang cookie into your profile and a
`rabbitmq.conf` with the loopback listener (INSTALL §2.4 steps 3-5,
elevated).  Check: `Get-Service RabbitMQ` is Running and
`rabbitmqctl status` exits 0.  If the
service crashes at start, re-register it with `RABBITMQ_BASE` as in
INSTALL §2.4.  The vhost and user come later (Step 6b).

**T7 NSSM 2.24 (INSTALL §2.5).**  Zip from nssm.cc.  No installer: copy
`win64\nssm.exe` to `C:\Tools\nssm\nssm.exe` and add `C:\Tools\nssm` to the
system PATH.  Check: `nssm version`.

**T8 Apache 2.4 + mod_fcgid (INSTALL §2.6, INSTALL_APACHE §1-§2).**  Two
zips from apachelounge.com/download: `httpd-2.4.x-win64-VS18.zip` and the
matching `mod_fcgid` zip.  No installer: the httpd zip contains an
`Apache24` folder - extract it to `C:\Tools\` so that
`C:\Tools\Apache24\bin\httpd.exe` exists; copy `mod_fcgid.so` from the
second zip into `C:\Tools\Apache24\modules\`.  Then edit `httpd.conf` as
INSTALL_APACHE §2 describes.  Check: `& C:\Tools\Apache24\bin\httpd.exe -v`
and later `httpd -t`.

**T9 PHP 8.5 NTS x64 (INSTALL §2.6, INSTALL_APACHE §1, §3).**  Zip
`php-8.5.x-nts-Win32-vs17-x64.zip` from windows.php.net/download.  No
installer: extract so that `C:\Tools\PHP\php.exe` and `php-cgi.exe` exist
directly in the folder.  Copy `php.ini-production` to `php.ini` and apply
INSTALL_APACHE §3 (`extension_dir`, eight extensions, upload limits), §3.1 (CA bundle: `cacert.pem` from
curl.se to `C:\Tools\PHP\cacert.pem`, two php.ini keys) and §3.2 (PHP 8.5
settings).  Check: `& C:\Tools\PHP\php.exe -v`.

**T10 Composer 2 (INSTALL §2.6).**  Single file `composer.phar` from
getcomposer.org/download (the "manual download" link; do **not** use the
Windows installer, it would register a different PHP).  Save it as
`C:\Tools\composer\composer.phar`.  Check:
`& C:\Tools\PHP\php.exe C:\Tools\composer\composer.phar --version`.

**T11 Icecast 2.5.0 (INSTALL §2.7).**  Windows installer from icecast.org
(verify the SHA512 against `SHA512SUMS.txt`, the installer is unsigned).
When it asks for the destination, choose **`C:\Tools\Icecast`** instead of
Program Files, so that `C:\Tools\Icecast\bin\icecast.exe` with its `web\`
and `admin\` siblings exists.  Do not start it from the installer; the
service comes in Step 9g with `config\icecast.xml` (from the example).
Check: `& C:\Tools\Icecast\bin\icecast.exe -v`.

**T12 FFmpeg (INSTALL §2.8).**  Release build zip, e.g. the
"essentials" build from gyan.dev (linked from ffmpeg.org/download).  No
installer: the zip unpacks into `ffmpeg-<version>-essentials_build\`;
rename or move that folder to `C:\ffmpeg` so that
`C:\ffmpeg\bin\ffmpeg.exe` and `ffprobe.exe` exist.  The service
installers prepend exactly `C:\ffmpeg\bin` to the services' PATH.  Check:
`& C:\ffmpeg\bin\ffmpeg.exe -version`.

**T13 Checker.**  `powershell -ExecutionPolicy Bypass -File
C:\rastatime\infra\scripts\dev\bootstrap.ps1` - ten `[PASS]`, exit 0.

Summary of the fixed paths: `C:\Tools\liquidsoap`, `C:\Tools\nssm`,
`C:\Tools\Apache24`, `C:\Tools\PHP`, `C:\Tools\composer`,
`C:\Tools\Icecast`, `C:\ffmpeg`.  Everything else (VC++, Git, Python,
PostgreSQL, Erlang, RabbitMQ) stays where its installer puts it.

The repository is private until the end of the publication: the clone
needs a GitHub login on the VM (Git Credential Manager asks once) or a
release zip + wheels from the Releases page (INSTALL Step 1, option B).

## 3. Protocol

Fill one row per INSTALL section.  Result: `ok` / `doc` (documentation
had to be corrected) / `bug` (product problem) / `skip` (with reason).

| INSTALL § | Step | Result | Minutes | Notes (what deviated, what you did) |
|---|---|---|---|---|
| 2.0 | Windows preparation | | | |
| 2.1 | Python | | | |
| 2.2 | PostgreSQL 17 | | | |
| 2.3 | Liquidsoap 2.4.6 | | | |
| 2.4 | RabbitMQ + Erlang | | | |
| 2.5 | NSSM | | | |
| 2.6 | Apache + PHP + Composer (INSTALL_APACHE) | doc | op: ? / session: T8 edit 7, T9 edit 8 (incl. both stops) | Operator extracted Apache 2.4.69 VS18, mod_fcgid, PHP 8.5.12, Composer and fetched `cacert.pem` (curl.se, 2026-10-20); the session made the `httpd.conf` / `php.ini` edits by the letter of INSTALL_APACHE §2-§3.2. (1) `httpd -t` failed: `AH00526: Syntax error on line 542 ... FcgidMaxRequestLen takes one argument` - the §2 fcgid block put `# 512 MiB = ...` after the value; Apache has no end-of-line comments. Fixed in httpd.conf and §2 (comment on its own line), `Syntax OK`. (2) The stock Apache Lounge file sets `Define SRVROOT "C:/Apache24"` + `ServerRoot "${SRVROOT}"`; §2 named only `ServerRoot`, leaving the cgi-bin alias (and `${SRVROOT}/logs` in `infra\apache\rastatime-https.conf`) on `C:/Apache24`. Fixed: §2 now changes `SRVROOT`. (3) `DirectoryIndex` stays `index.html`, `public\` has only `index.php` - check at Step 9f whether `/` shows the login page. (4) §3.1 check fails: `Unable to find the wrapper "https"`, `bool(false)`. §3 enables no extension: `php.ini-production` has every `extension=` commented out and `extension_dir` resolves to `C:\php\ext`; `curl.cainfo` / `openssl.cafile` stay unregistered (`ini_get` false). Composer.lock hard-requires `ext-mbstring` and `ext-sockets` (php-amqplib); the code uses PDO pgsql, curl, gettext, fileinfo. Operator agreed: `extension_dir = "C:\Tools\PHP\ext"` (absolute, php-cgi runs elsewhere under mod_fcgid) + `curl fileinfo gettext mbstring openssl pdo_pgsql sockets zip`; §3 now says so and also that `php.ini` is a copy of `php.ini-production` (INSTALL_APACHE never said it). `php -m` lists all eight, both CA keys set, §3.1 check `bool(true)`. `RASTATIME-APACHE` restart in §3.1 not applicable yet (service comes in Step 9f). (5) No Git identity on the VM, first commit failed: repo-local identity set on the operator's word, §0b C now says so. |
| 2.7 | Icecast 2.5.0 | | | |
| 2.8 | FFmpeg | | | |
| 4 / 1 | Clone or release archive | ok | 0 | Cloned by the operator in §0b B (option A), `ee7ccbb9`. |
| 4 / 2 | bootstrap.ps1 (all §2 components, exit 0) | ok | <1 | Ten required `[PASS]`, Composer 2.11.1 and Git 2.56.0 optional `[PASS]`, exit 0 (4 s). Note: it was green before the 2.6 fixes too - it only runs `httpd.exe -v` / `php.exe -v`, not `httpd -t` or a check of the PHP extensions (BACKLOG candidate). |
| 4 / 3 | venv | doc | 1 | `python -m venv .venv` ok (Python 3.13.0). (1) `.venv\Scripts\Activate.ps1` fails in an operator's PowerShell: the effective execution policy of a fresh Windows 11 is `Restricted` (`Die Datei ... Activate.ps1 kann nicht geladen werden, da die Ausführung von Skripts auf diesem System deaktiviert ist`). It worked in the assistant session only because its shell runs with `Process = Bypass`. (2) `where python` prints nothing: in PowerShell `where` is the alias of `Where-Object`; `where.exe python` shows `C:\rastatime\.venv\Scripts\python.exe` first. Operator chose: Step 3 now sets `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before `Activate.ps1` (window only, nothing persistent; note that Step 4 / 7 / §7 need it again) and uses `where.exe`. |
| 4 / 4 | Python dependencies, editable installs | doc | 3 | Block run as written (venv activated as in the corrected Step 3). `pip install --upgrade pip` exits 1: `ERROR: To modify pip, please run the following command: C:\rastatime\.venv\Scripts\python.exe -m pip install --upgrade pip` - on Windows pip cannot replace its own `pip.exe`; pip stays 24.2 (26.2.2 available). The rest of the block (requirements, psycopg2-binary, five editable installs) exits 0 with pip 24.2; checks print `Django 5.2.18`, `Waitress 3.0.2`, `psycopg2 OK`. Operator chose: Step 4 now says `python -m pip install --upgrade pip`; run afterwards: pip 26.2.2, `pip check` clean. |
| 4 / 4b | composer install (frontend) | doc | 1 | Exit 0 in 49 s, `vendor\autoload.php` True; 52 packages, all `Extracting archive` (dist, no git fallback - the `zip` extension of 2.6 at work); one notice `Skipped installation of bin generator/bin/propel-gen.bat for package libretime/propel1: name conflicts with an existing file`, harmless. The note says "`composer.lock` pins the 99 packages" - the lock has 52 (`packages-dev` 0); COMPONENTS.md said 99 too. Both corrected to 52 on the operator's word. |
| 4 / 5 | rastatime.conf from the example | doc | 1 | Copied; placeholders of the example kept (public_url `http://localhost`, DB and RabbitMQ password `rastatime`) as §0 says, `api_key` / `secret_key` generated with the Step 5 command and written without display. The command yields 46-48 characters (11 runs: 47 47 46 48 47 47 48 48 46 48 48) - the table above it demands at least 50 for `secret_key` (Django `check --deploy` W009). `Get-Random` is also not a cryptographic generator. Watch item: `storage.path` `C:/rastatime/media` must exist at the web application's start (note under the YAML block), but no step and no install script creates it. Operator chose: Step 5 now generates with `RandomNumberGenerator`, 48 bytes (11 runs: 61-64 characters); both values regenerated with it, without display. |
| 4 / 6 | PostgreSQL user + database | ok | 9 | Operator typed superuser password and the two statements in a terminal tab the session opened (`psql` prompts interactively; the session's shell has no input). Password = example placeholder `rastatime`, as in `rastatime.conf`. `CREATE ROLE`, `CREATE DATABASE`; login as `rastatime` from the session ok, owner `rastatime`, UTF8, collation `English_United States.1252` (installer default). psql prints `WARNING: Console code page (437) differs from Windows code page (1252)` - harmless for the ASCII statements. The minutes include a terminal panel that did not draw the password prompt at first (tooling, not INSTALL). |
| 4 / 6b | RabbitMQ vhost + user | doc | 11 | (1) `rabbitmqctl add_user ...`: `Die Benennung "rabbitmqctl" wurde nicht ... erkannt` - the RabbitMQ 4.4.0 installer puts nothing on PATH; the tool is `C:\Program Files\RabbitMQ Server\rabbitmq_server-4.4.0\sbin\rabbitmqctl.bat` (§2.4's `rabbitmq-service.bat` sits there too). (2) Read-only probe with the full path, `rabbitmqctl status`: exit 69, `TCP connection succeeded but Erlang distribution failed`, `check if the Erlang cookie is identical` - the node runs (service LocalSystem, Running; 5672/4369/25672 listening), but the CLI uses `C:\Users\admin\.erlang.cookie`, the service the LocalSystem cookie in `C:\Windows\System32\config\systemprofile\` (unreadable without elevation). INSTALL §2.4 / Step 6b mention neither. Operator chose: §2.4 gets step 3 (`sbin` onto the system PATH) and step 4 (copy the LocalSystem cookie into the profile, elevated) and `rabbitmqctl status` in the check; the operator did both by hand. Then `rabbitmqctl status` exit 0 (4.4.0, OTP 28) and the three Step 6b commands exit 0 (password = placeholder `rastatime`), `list_permissions -p /rastatime`: `rastatime .* .* .*`. The minutes include the operator's PATH and cookie work. Watch item for A1.5: AMQP 5672 listens on `[::]` and `0.0.0.0`, INSTALL configures no loopback bind. |
| 4 / 7 | migrate | ok | 1 | As written (venv activated per the corrected Step 3, three `$env:` lines): exit 0 in 29 s, 97 migrations `... OK` (auth, contenttypes, legacy, linein, playback, preflight, sessions, song_request, soundcard), no warning. |
| 4 / 8 | log directory | ok | <1 | `C:\rastatime\logs` did not exist, created; git-ignored (`.gitignore:78`). Later (9f): Step 8 now also creates `C:\rastatime\media`. |
| 4 / 9a | API service + health 200 | ok | 1 | coding assistant restarted as administrator for Step 9 (operator; VM snapshot before it). `install-api.ps1` exit 0 in 10 s, `RASTATIME-API` Running / Automatic (NSSM prints its lines as UTF-16, cosmetic; one `Unexpected status SERVICE_START_PENDING`, then Running). `/health`: 200, `{"status": "ok", "service": "rastatime-api", "version": "4.5.0"}`; `api-stderr.log` empty. **A1.5 mismatch:** the script's default `-ApiHost 0.0.0.0` (Step 9a passes none) binds `0.0.0.0:8765`; PostgreSQL (`listen_addresses = '*'`, installer default) and RabbitMQ 5672 listen on `0.0.0.0` and `::` too - INSTALL sets no loopback bind for any of the three, TEST_PLAN A1.5 wants them on 127.0.0.1 only. Operator chose to fix it now (+4 min): §2.2 step 5 `listen_addresses = 'localhost'` + restart (5432 on 127.0.0.1 / ::1); §2.4 step 5 `rabbitmq.conf` with `listeners.tcp.default = 127.0.0.1:5672` beside `advanced.config` in `%APPDATA%\RabbitMQ` + restart (a restart reads the new file; 5672 on 127.0.0.1, `authenticate_user` ok); Step 9a passes `-ApiHost 127.0.0.1`, script re-run (idempotent), 8765 on 127.0.0.1, health 200. BACKLOG candidate: `install-api.ps1` defaults to `0.0.0.0`, and CRASH_RECOVERY.md / RESTART_ORDER.md re-install the API without `-ApiHost` - the default should be `127.0.0.1`. Not in A1.5, still on all interfaces: epmd 4369 and Erlang distribution 25672. |
| 4 / 9b | Worker | ok | 1 | `install-worker.ps1` exit 0 in 11 s, `API is healthy (HTTP 200)`, then `[WARN] RASTATIME-WORKER status after start: StartPending` - Running ~20 s after the start (00:30:12), so the script checks a few seconds too early; §5.4 covers only a worker that *stays* StartPending. `worker-stderr.log` empty; stdout: `Mode : dev stub (no real handlers registered)`, `Runner : none (JobRunner ABC not yet instantiated)`, then `idle` every 5 s - the worker does no work yet (observation for the studio, not a deviation from INSTALL). Two `python.exe -m rastatime_worker` = venv launcher + interpreter. |
| 4 / 9c-d | Playout + engine variables | doc | 3 | 9c: `install-playout.ps1` exit 0, Stopped / Automatic; it sets exactly the six variables 9d repeats. 9d: `nssm set` exit 0; `nssm start` prints `Unexpected status SERVICE_START_PENDING in response to START control` and exits 1 - Running 15 s later (00:33:43); 9d names no expected output. `playout-stdout.log`: `Health gate: API healthy (HTTP 200)`, `Rendered C:\Tools\liquidsoap\rastatime.liq` (54 KB) and `standby.liq`; stderr empty. Until 9h telnet `127.0.0.1:1234` refused (expected), and the playout tries three times to restart the not yet installed Liquidsoap service: `ERROR ... nssm restart RASTATIME-LIQUIDSOAP exited 3: Can't open service!` (planned restart, "rastatime.liq changed at the playout start"); it keeps running afterwards. **Gap:** it also logs `RESTART the RASTATIME-STANDBY NSSM service` - the standby Liquidsoap for the Icecast `-standby` fallback mounts (`backend\playout\config\nssm-install-standby.ps1`, production since 2026-09-09, referenced by `icecast.xml.example`, RESTART_ORDER, COMPONENTS) has no step in INSTALL §4. Operator chose: 9d gets a note (the `nssm start` message, the check, the expected errors until 9h); new Step 9i installs RASTATIME-STANDBY after 9g/9h (§1 now says eight services; Step 10 and §6 check STANDBY with `Get-Service`, since `status.ps1` lists only seven). BACKLOG candidates: the playout restarts a Liquidsoap service that is not installed (three ERROR lines on every fresh install); `status.ps1` does not know RASTATIME-STANDBY. |
| 4 / 9e | Analyzer | doc | 1 | `install-analyzer.ps1` exit 0 in 9 s, again `[WARN] ... StartPending` too early (Running from 00:45:47). `Listening for messages...`; `airtime-uploads` 0 messages, 1 consumer; connection `rastatime@127.0.0.1` running. **Side effect of the 9a/A1.5 fix of §2.4:** `rastatime.conf` says `rabbitmq.host: localhost`, pika tries `::1` first - `Socket failed to connect ... ('::1', 5672)`, `ConnectionRefusedError(10061)`, three ERROR lines and 2 s - then connects via 127.0.0.1, because the new `rabbitmq.conf` listens on 127.0.0.1 only (PostgreSQL's `'localhost'` binds both). Operator chose: listen on both - `listeners.tcp.1 = 127.0.0.1:5672`, `listeners.tcp.2 = ::1:5672` in `rabbitmq.conf` and §2.4 step 5; RabbitMQ and analyzer restarted: 5672 on 127.0.0.1 and ::1, the analyzer connects via `::1` at once, no ERROR line, 1 consumer (+6 min). |
| 4 / 9f | Apache | doc | 7 | `install-apache.ps1` exit 0 in 11 s, `RASTATIME-APACHE` Running, port 80 on `0.0.0.0` / `::`; NSSM 2.24 prints `Invalid parameter "AppKillProcessTree"` plus its whole parameter list (announced in INSTALL_APACHE §5, alarming on screen); the script removes an existing NSSM service without asking (INSTALL_APACHE §5 says it "offers" to). **Frontend not reachable:** `http://localhost/` -> 200 `Index of /` (directory listing: `DirectoryIndex index.html`, `public\` has `index.php`, `Options Indexes`); `/login` and `/index.php` -> 403 Forbidden (239 bytes), nothing in `error_log` at `LogLevel warn`. Hypothesis: mod_fcgid runs `fcgid-script` only where `Options ExecCGI` is set, and the INSTALL_APACHE §2 DocumentRoot block has `Options Indexes FollowSymLinks`. Operator chose: prove first. `LogLevel info` + one request: still no line (an authz denial would log `AH01630`, a missing file is 404) - LogLevel back to `warn`; then `ExecCGI` alone: `/index.php` and `/login` 200 - confirmed. `DirectoryIndex index.php index.html`: `/` reaches `index.php` too. INSTALL_APACHE §2 now has both lines with the reason. **Next stop:** every URL answers 200 with the 66-byte body `the configured storage.path 'C:/rastatime/media/' does not exists!` - the Step 5 watch item: no step creates `C:\rastatime\media`. Operator chose: Step 8 now creates it (heading "log and media directories"); created on the VM: `/login` 200, 8.5 KB, RASTATIME login form; `/` 200, 23 KB, RASTATIME page without a login form; `error_log` clean. BACKLOG candidate: the web application could create `storage.path` itself (or name the fix in its message, which also says "does not exists"). Minutes include both stops. |
| 4 / 9g | Icecast | doc | 4 | Run as written: `install-icecast.ps1` exit 0 in 10 s, banner `[OPTIONAL - install only if streaming is required]`, `[ OK ] RASTATIME-ICECAST is Running`. But `config\icecast.xml` does not exist - no step creates it (§2.7 only says "Start from `config\icecast.xml.example`"), and the script does not check it: `icecast.exe -c C:\rastatime\config\icecast.xml` hangs (session 0, 2 threads, ~0 CPU, no window), port 8000 never listens, no log line anywhere, NSSM shows Running. The example holds four `CHANGEME` passwords (source, relay, admin, master) - the Step 5 table says "Default value is `admin`" - and `<hostname>192.168.1.64</hostname>`; paths (`C:/rastatime/logs`, `C:/Tools/Icecast/web` / `admin`) and the single `<listen-socket>` 8000 fit the VM. Operator chose: Step 9g now copies the example, replaces the four `CHANGEME` and `<hostname>`, and checks `status-json.xsl`; the Step 5 table names the four `CHANGEME`. On the VM: copied, four generated passwords (61-64 chars, not displayed), hostname `localhost` (no studio address on the VM), 9g re-run (idempotent): port 8000 on `::` (dual-stack, 127.0.0.1 answers), `status-json.xsl` 200 `Icecast 2.5.0`. Icecast `error.log` warns `unable to open file "C:/Tools/Icecast/web/rastatime-standby"` (and -aac, -ogg) until 9i. BACKLOG candidate: `install-icecast.ps1` should refuse a missing `icecast.xml`, and its banner calls Icecast `[OPTIONAL]` although INSTALL treats it as part of the stack. |
| 4 / 9h | Liquidsoap (rendered rastatime.liq present?) | ok | 1 | `rastatime.liq` present (54 KB, rendered by PLAYOUT in 9d). `nssm-install-liquidsoap.ps1` exit 0; `nssm start` again `Unexpected status SERVICE_START_PENDING` / exit 1 (as in 9d), Running from 01:09:44, same PID 40 s later. Telnet 1234 on 127.0.0.1 only (A1.5 ok), `output.portaudio` up, `liquidsoap-stderr.log` empty; PLAYOUT: `Connected to Liquidsoap telnet at 127.0.0.1:1234`. Then PLAYOUT warns `the loaded rastatime.liq has no harbor source events (older render)` - the render is current, it simply has no harbor because `stream.harbor` is commented out (example default, Step 5 note); port 8001 therefore does not listen (A1.5 watch item). BACKLOG candidates: that warning's wording; the rendered script uses the deprecated `audio_to_stereo` (two `lang.deprecated` warnings) and registers `scheduled.flush_and_skip` twice (`already registered! Previous definition replaced`). |
| 4 / 9i | Standby source RASTATIME-STANDBY (added in this rehearsal) | doc | 2 | First run of the new step: `nssm-install-standby.ps1` exit 0, `SERVICE_RUNNING`, `Get-Service` Running; one start, same PID 30 s later. `standby.liq` (870 bytes, rendered in 9d) has no output (`no stream outputs configured in cc_pref - Liquidsoap will run idle`); log only `Warning 4: Unused variable bus`. `/rastatime-standby` -> 404. So on a fresh install the `-standby` mounts stay without a source until stream outputs exist (Settings -> Streams) and PLAYOUT re-renders `standby.liq` - my 9g note ("until 9i") was wrong. Operator agreed: the 9g note now says "until stream outputs exist", 9i explains the idle standby and the restart order once outputs are configured (PLAYOUT, then STANDBY). The `EROR util/util.c Input string does not parse as KVA` at 01:14:09 came from the session's own test request. |
| 4 / 10 | status.ps1: seven services Running | | | |
| 6 | Post-installation checklist (every box) | | | first login admin / admin, password changed |

## 4. Acceptance (from TEST_PLAN.md, the parts a fresh machine can show)

| Check | Expected | Result |
|---|---|---|
| A1.1 services | all RASTATIME-* services Running, start type Automatic | |
| A1.3 playout health gate | `playout-stdout.log`: `Health gate: API healthy`, Liquidsoap config rendered | |
| A1.5 loopback binds | 5432, 5672, 8765, 1234 only on 127.0.0.1; 80, 8000, 8001 on 0.0.0.0 | |
| Upload round trip | a file uploaded in the UI leaves "Pending Import", lands in the library with cue points (not 0 / length) | |
| Schedule + playout | a show with that file plays on the Icecast mount (`http://localhost:8000/status-json.xsl` shows the title) | |
| Reboot | `Restart-Computer`, all services back without hands | |

## 5. Outcome

| Item | Value |
|---|---|
| Total time | |
| Documentation fixes committed (hashes) | |
| Product bugs found (BACKLOG items) | |
| Verdict for phase 6 (release v1.0.0) | go / not yet |
