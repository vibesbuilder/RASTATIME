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
repository is its only context.

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
| Windows 11 edition / build | |
| CPU / RAM / disk | |
| Network: internet during install (downloads) | yes / no |
| Audio device present (playout output test) | |
| Date of the rehearsal | |
| Commit / tag installed (`git rev-parse --short HEAD`) | |

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
open a new PowerShell.  Check: `pg_isready -h 127.0.0.1 -p 5432`.

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
Windows service itself.  Check: `Get-Service RabbitMQ` is Running.  If the
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
INSTALL_APACHE §3 (upload limits), §3.1 (CA bundle: `cacert.pem` from
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
| 2.6 | Apache + PHP + Composer (INSTALL_APACHE) | | | |
| 2.7 | Icecast 2.5.0 | | | |
| 2.8 | FFmpeg | | | |
| 4 / 1 | Clone or release archive | | | |
| 4 / 2 | bootstrap.ps1 (all §2 components, exit 0) | | | |
| 4 / 3 | venv | | | |
| 4 / 4 | Python dependencies, editable installs | | | |
| 4 / 4b | composer install (frontend) | | | |
| 4 / 5 | rastatime.conf from the example | | | |
| 4 / 6 | PostgreSQL user + database | | | |
| 4 / 6b | RabbitMQ vhost + user | | | |
| 4 / 7 | migrate | | | |
| 4 / 8 | log directory | | | |
| 4 / 9a | API service + health 200 | | | |
| 4 / 9b | Worker | | | |
| 4 / 9c-d | Playout + engine variables | | | |
| 4 / 9e | Analyzer | | | |
| 4 / 9f | Apache | | | |
| 4 / 9g | Icecast | | | |
| 4 / 9h | Liquidsoap (rendered rastatime.liq present?) | | | |
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
