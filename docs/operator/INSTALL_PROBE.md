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

## 2. Downloads to prepare (versions as on the studio machine, 2026-11-01)

| Component | Version | Source | INSTALL section |
|---|---|---|---|
| Visual C++ Redistributable x64 | latest | Microsoft | 2.6 |
| Python | 3.13 (3.11 minimum) | python.org, "Add to PATH" | 2.1 |
| PostgreSQL | 17 | EnterpriseDB installer | 2.2 |
| Liquidsoap | 2.4.6 win64 zip | github.com/savonet/liquidsoap/releases | 2.3 |
| Erlang OTP + RabbitMQ | 4.x | rabbitmq.com | 2.4 |
| NSSM | 2.24 | nssm.cc | 2.5 |
| Apache httpd | 2.4.68 Win64 VS18 | Apache Lounge | 2.6 / INSTALL_APACHE |
| mod_fcgid | current VS18 build | Apache Lounge | INSTALL_APACHE |
| PHP | 8.5 NTS x64 zip | windows.php.net | 2.6 / INSTALL_APACHE |
| Composer | 2.x `composer.phar` | getcomposer.org | 2.6 |
| Icecast | 2.5.0 win64 | icecast.org (verify SHA512) | 2.7 |
| FFmpeg | current release build | ffmpeg.org / gyan.dev | 2.8 |
| Git for Windows | current | git-scm.com | Step 1 |
| CA bundle for PHP | current `cacert.pem` | curl.se | INSTALL_APACHE §3.1 |

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
