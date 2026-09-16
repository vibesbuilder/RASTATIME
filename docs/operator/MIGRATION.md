# Migration to a New Studio Machine

> **Audience.** Operators replacing the RASTATIME studio computer
> (CPU upgrade, hardware refresh, broken-machine emergency).
> Specifically written for the **2026-05-29 Lenovo ThinkCentre
> M70s Gen 5 / Core i5-14400 / 2× SSD** migration scenario, but
> the procedure generalises to any same-OS hardware swap.
>
> **What this document is.** Step-by-step recipe for moving an
> existing running RASTATIME deployment to fresh hardware with
> minimal listener downtime.
>
> **What this document is NOT.** Fresh-install instructions —
> see [`INSTALL.md`](INSTALL.md) for that.  Day-to-day backup —
> see [`BACKUP.md`](BACKUP.md) for the routine procedure (this
> doc reuses BACKUP.md mechanisms).
>
> **Revised 2026-06-16.** Validated by an isolated backup→restore dry-run on
> the live machine and corrected accordingly: there is **one** live database
> (`rastatime`; `libretime` is a stale leftover — §4.1), the media path
> rewrite runs on **`rastatime.cc_files`** and there is **no `cc_music_dirs`
> table** (§4.4c), and this run targets a **new IP/hostname** (§4.8).

---

## TL;DR — five phases

1. **Old machine**: take a full backup bundle (15-30 min)
2. **New machine**: install Windows + RASTATIME stack from
   [`INSTALL.md`](INSTALL.md) (1-2 h)
3. **New machine**: restore database + configs + media library
   from the backup (30-60 min)
4. **Cutover**: stop services on old, start on new, point DJ tools
   + DNS at new machine (5-15 min — listener downtime here)
5. **Post-migration**: 24-48 h monitoring on new machine, then
   decommission old

Total operator-effort: **~4-6 h** spread across 1-2 days
(can be done overnight to minimise listener impact).

---

## 1. Preconditions

### 1.1 Both machines accessible
- Old machine: running, networked, you can RDP / log in
- New machine: assembled, Windows installed and updated, networked
- Same LAN if possible (file copy via network) OR external SSD/HDD
  for transport

### 1.2 New machine hardware verified
- **CPU**: Intel i5-14400 or equivalent (Phase-D Stück-B 2026-05-28
  determined that the prior i3-1315U notebook chip caused catchup-
  hell under Liquidsoap-pipeline load; the i5-14400 65 W desktop
  CPU has 10 cores and ~70 % more sustained throughput).
- **RAM**: 16 GB minimum
- **Storage**: 2× SSD
  - SSD-A (NVMe boot): Windows + RASTATIME stack + recordings
  - SSD-B (NVMe / SATA): **dedicated Media Library disk** —
    separates the random-read I/O of MP3 loading from the
    sequential-write I/O of recording + OS updates + AV scans.
- **Network**: 1 Gbit, static IP or DHCP-reservation
- **UPS**: same as before, just plug the new machine in

### 1.3 Migration window planned
- Listener downtime during cutover: **5-15 minutes**
- Pick a low-traffic time slot (typically 03:00-05:00 local)
- Notify any live DJs about the IP/credentials change beforehand

### 1.4 Both machines on the same SOFTWARE version
- RASTATIME repo: commit the new machine should run.  Same commit
  on both = no migration scripts needed.
- If old is `master` and you want `master` on new: that's the
  default.

---

## 2. Phase A — Backup bundle on old machine

This bundles everything the new machine needs: database, configs,
media, recordings, repo, and NSSM service configurations.

### 2.1 Database dump for the migration

> **Revised 2026-08-27.** Earlier drafts claimed the BACKUP.md §6 script
> produces a `C:\rastatime-backup\<date>\` bundle with custom-format
> dumps — it does not: BACKUP.md §6 writes **plain-SQL** dumps to
> `C:\rastatime-backups\db\rastatime-<date>.sql` plus dated config
> copies.  Plain SQL cannot be fed to `pg_restore` (§4.1).  For the
> migration, make a dedicated **custom-format** dump directly into the
> bundle:

```powershell
New-Item -ItemType Directory -Path C:\rastatime-migration -Force | Out-Null
$env:PGPASSWORD = '<db-password>'
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" `
    -h 127.0.0.1 -U rastatime -d rastatime -Fc `
    -f C:\rastatime-migration\pg-rastatime.dump
Remove-Item Env:\PGPASSWORD
```

> `rastatime` is the **only** live database (§4.1) — there is no
> `pg-libretime.dump` to make.  Also copy the two config files the
> restore (§4.3) expects:

```powershell
Copy-Item C:\rastatime\config\libretime.conf C:\rastatime-migration\
Copy-Item C:\rastatime\config\icecast.xml    C:\rastatime-migration\
```

### 2.2 Additional migration-only items (NOT in BACKUP.md)

```powershell
$BUNDLE = "C:\rastatime-migration"
New-Item -ItemType Directory -Path $BUNDLE -Force | Out-Null

# 1) RASTATIME source repo (in case the new machine has no Git remote)
#    NOTE: media\ is EXCLUDED here — the media library is backed up
#    separately in step 6 (it's huge + gets a new home on D:\stor).
robocopy C:\RASTATIME "$BUNDLE\RASTATIME" /MIR `
    /XD .git\objects\pack-cache __pycache__ node_modules media `
    /XF *.pyc

# 2) Liquidsoap install (binary + DLLs)
robocopy C:\Tools\liquidsoap "$BUNDLE\Tools\liquidsoap" /MIR

# 3) NSSM tool itself (in case the new machine doesn't have it)
robocopy C:\Tools\nssm "$BUNDLE\Tools\nssm" /MIR

# 4) NSSM service environments.  NOTE (2026-08-27): the deployed NSSM
#    2.24 has NO "dump" command (that is a 2.25-prerelease feature) —
#    earlier drafts of this step produced empty files.  Services are
#    re-created fresh on the new machine via the install scripts (§4.7);
#    export only the partly operator-maintained env blocks as reference
#    (esp. RASTATIME-PLAYOUT's engine vars):
$nssm = "C:\Tools\nssm\nssm.exe"
foreach ($svc in @(
    "RASTATIME-ANALYZER",
    "RASTATIME-APACHE",
    "RASTATIME-API",
    "RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP",
    "RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) {
    & $nssm get $svc AppEnvironmentExtra 2>&1 |
        Out-File "$BUNDLE\nssm-env-$svc.txt" -Encoding UTF8
}

# 5) Recordings + import inbox (operator content — important to preserve)
#    Three folders since Record-per-Hour (2026-06-06); the live values are the
#    cc_pref keys local_recording_folder / local_247_recording_folder /
#    local_import_folder.
robocopy "C:\Users\studio\Music\Show Recordings"      "$BUNDLE\Show Recordings"      /MIR
robocopy "C:\Users\studio\Music\Permanent Recordings" "$BUNDLE\Permanent Recordings" /MIR
robocopy "C:\Users\studio\Music\Import"               "$BUNDLE\Import"               /MIR

# 6) Media library (the bulk — easily 10-100 GB)
#    This is the slow part.  ~30 GB takes ~5 min on Gigabit LAN.
#    The real storage path is C:\rastatime\media (libretime.conf
#    storage.path) — NOT C:\rastatime\stor (that path never existed;
#    earlier drafts of this doc were wrong).  Verify with:
#      (Get-Content C:\rastatime\config\libretime.conf | Select-String 'path:')
# ⚠️ Run this media copy from an ELEVATED shell (Administrator).  Verified
#    2026-06-17: the podcast-feature downloads (imported/2/podcast_ep*.mp3,
#    ~33 files in cc_files) carry a restrictive ACL with NO access for the
#    `studio` user — a non-elevated robocopy SILENTLY skips them (exit >=8,
#    "Zugriff verweigert").  Administrators have full access and copy them.
#    See BACKLOG "Podcast-Downloads: ACL sperrt den studio-User aus".
robocopy C:\rastatime\media "$BUNDLE\media" /MIR

# 7) Operator-specific PowerShell scripts / monitoring tools
#    (the burnin_2026-05-28_02-48.log helpers etc., if you keep them)
if (Test-Path "C:\rastatime\test_c5_mechanism_b.py") {
    Copy-Item "C:\rastatime\test_c5_mechanism_b.py" $BUNDLE -Force
}

# Size check
Write-Host "`n=== Bundle size ===" -ForegroundColor Cyan
(Get-ChildItem $BUNDLE -Recurse | Measure-Object Length -Sum).Sum / 1GB
```

### 2.3 Transfer to new machine

**Option A — Gigabit-LAN (recommended, ~5 min/GB)**: share
`C:\rastatime-migration` from old machine, copy from new machine.

**Option B — external USB-SSD**: copy bundle to USB SSD, plug
into new machine.

**Option C — split**: 30 GB media-library via USB-SSD overnight,
the rest (few hundred MB) via LAN on the cutover morning.

---

## 3. Phase B — Fresh RASTATIME install on new machine

Don't try to "restore an image" of the old Windows install.  Fresh
Windows + fresh install of the RASTATIME stack avoids inheriting
years of registry cruft, driver-conflicts, AV exclusion drift.

### 3.1 Fresh Windows install
- Windows 11 Pro (or Server if you license it)
- Latest updates **before** RASTATIME install (so they don't fight
  during operation — see Phase-D 2026-05-29 00:15-00:30 lesson)
- Disable Auto-Sleep, Hibernate, Screensaver (system always on)
- Set time-zone correctly (same as old machine)
- **Smart App Control: OFF.**  Enforced SAC silently blocks unsigned
  binaries (php-cgi.exe, httpd.exe exit without a trace).  Switching it
  off is only possible interactively in Windows Security and is
  irreversible without a reinstall — do it now, before any stack
  component runs.
- Configure network **first**: static IP or DHCP-reservation **before**
  any config references the address — a silent DHCP lease change after
  the configs were written cost real debugging time (2026-08 run).
  For a same-IP swap, match the old machine (so DNS/firewall rules
  carry over).  For a **new IP/hostname** (this migration), pick the
  new address now and apply the config touchpoints in §4.8.

### 3.2 Bitdefender install + MANDATORY exclusions

Install Bitdefender **before** the RASTATIME stack so first-run-
scan doesn't fight the installer.

**Exclusion list** (Settings → Antivirus → Manage Exceptions):

```
Paths:
  C:\RASTATIME
  C:\Tools
  C:\Program Files\PostgreSQL\17\data
  C:\Users\studio\Music\Show Recordings        ← show recordings (Record-per-Hour)
  C:\Users\studio\Music\Permanent Recordings   ← 24/7 recordings
  C:\Users\studio\Music\Import                 ← import inbox
  C:\rastatime                                ← runtime, scheduler cache, logs
  D:\stor                                     ← only once the second SSD exists
                                                (see BACKLOG storage cleanup)

Processes:
  C:\Tools\liquidsoap\liquidsoap.exe
  C:\Tools\nssm\nssm.exe
  C:\rastatime\.venv\Scripts\python.exe
  C:\Tools\Icecast\bin\icecast.exe
  C:\Program Files\PostgreSQL\17\bin\postgres.exe
  C:\Tools\PHP\php-cgi.exe
  C:\Tools\Apache24\bin\httpd.exe
  C:\Program Files\Erlang OTP\erts-*\bin\erl.exe   ← RabbitMQ runtime
```

Set Bitdefender update-check interval to **24h** (Settings → Update).
The default "every 30 min" produces I/O spikes that catchup the
Liquidsoap pipeline (Phase-D learning 2026-05-29).

### 3.3 Run INSTALL.md

Follow [`INSTALL.md`](INSTALL.md) §4 step-by-step to install:
- Visual C++ Redistributable x64 (latest) — needed **before** Apache/PHP;
  without it httpd.exe / php-cgi.exe exit silently
- PostgreSQL 17
- Python 3.13 + venv at `C:\rastatime\.venv`
- RabbitMQ 4.x + Erlang OTP — the analyzer's message queue (the PHP
  frontend dispatches upload messages to it).  Create vhost `/rastatime`
  + the user/password from `libretime.conf`'s `rabbitmq` section (port
  5672).  Windows quirk: (re)install the service with an explicit
  `RABBITMQ_BASE` (e.g. `C:\ProgramData\RabbitMQ`) via
  `rabbitmq-service.bat remove` / `install`, otherwise the LocalSystem
  service can crash on start when the installer ran as a normal user.
- Apache (Apache Lounge 2.4.x Win64 at `C:\Tools\Apache24`) + PHP 8.3
  NTS x64 at `C:\Tools\PHP`
- Icecast **2.4.4** at `C:\Tools\Icecast` (deliberate — the live
  `icecast.xml` relies on Icecast-2.4 auth semantics; 2.5 replaced them
  with event-bindings and is a separate future upgrade, see BACKLOG)
- NSSM (`C:\Tools\nssm\nssm.exe`)
- All 7 RASTATIME NSSM services (ANALYZER, APACHE, API, ICECAST,
  LIQUIDSOAP, PLAYOUT, WORKER)
- FFmpeg (line-in MME feeder + audio analysis)

**Skip these INSTALL.md steps** (they're done by the restore in
Phase C instead):
- Database initialisation (Phase C restores instead)
- cc_pref defaults (restored from old database)
- libretime.conf creation (restored from backup)

### 3.4 Liquidsoap install

Copy from bundle:

```powershell
robocopy C:\rastatime-migration\Tools\liquidsoap C:\Tools\liquidsoap /MIR
& "C:\Tools\liquidsoap\liquidsoap.exe" --version
# Expected: Liquidsoap 2.4.4
```

### 3.5 Media-library disk (SSD-B)

Format SSD-B as NTFS, assign drive letter **D:**, mount point
`D:\stor` for the media library:

```powershell
# After Windows recognises SSD-B
# Disk Management → format NTFS → assign D:
mkdir D:\stor
```

Update `libretime.conf` to point the storage path at the new
location (we'll do this in Phase C step 4.4).

---

## 4. Phase C — Restore from backup bundle

### 4.1 PostgreSQL database

> **Validated 2026-06-16 (isolated backup→restore dry-run).** `rastatime`
> is the **only** live database — the legacy PHP frontend *and* the Django
> API both use it (it holds `django_migrations`; 47 tables, ~4100 schedule
> rows).  The `libretime` database is a **stale leftover** from before the
> `rastatime` rename (separate owner, **zero** connections) and does **not**
> need restoring.  If the backup bundle still contains `pg-libretime.dump`,
> ignore it (and optionally drop the empty `libretime` DB on the new box).

```powershell
# Stop the API + Worker services while DB is being restored
Stop-Service RASTATIME-API, RASTATIME-WORKER

$pgrestore = "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe"
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"

# Drop the empty database created by INSTALL.md and recreate it
& $psql -U postgres -c "DROP DATABASE IF EXISTS rastatime;"
& $psql -U postgres -c "CREATE DATABASE rastatime OWNER rastatime;"

# Restore the single live database
& $pgrestore -U postgres -d rastatime C:\rastatime-migration\pg-rastatime.dump

Start-Service RASTATIME-API, RASTATIME-WORKER
```

> **DB-restore round-trip was validated** on 2026-06-16 by dumping the live
> `rastatime` DB, restoring into an isolated temp DB and diffing every table:
> **47/47 tables identical, zero pg_restore errors.**

### 4.2 Source repo

```powershell
# If you use Git: clone fresh + check out the same commit
git clone https://your-git-host/rastatime.git C:\RASTATIME
cd C:\RASTATIME
git checkout <commit-hash-from-old-machine>

# OR: restore from backup bundle (works offline)
robocopy C:\rastatime-migration\RASTATIME C:\RASTATIME /MIR
```

### 4.3 Configuration files

```powershell
# libretime.conf (contains DB credentials, harbor passwords,
# Icecast credentials, the lot).  Live location is C:\rastatime\config\
# (NOT \etc\ — verified 2026-06-16).
Copy-Item C:\rastatime-migration\libretime.conf C:\rastatime\config\ -Force

# Icecast config — the RASTATIME-ICECAST service reads it from
# C:\rastatime\config\ (nssm AppParameters:
#   -c C:\rastatime\config\icecast.xml), NOT from the Icecast
# install folder (C:\Tools\Icecast).
Copy-Item C:\rastatime-migration\icecast.xml C:\rastatime\config\ -Force
```

### 4.4 Storage cleanup — new root + drop the owner-id subfolder

> **2026-09-16:** the owner-id level is gone from the code and the
> live library (stage 1 of the selectable storage location, see
> ARCHITECTURE §23.32).  New installs and restores follow the flat
> layout `imported/<artist>/<album>/…` automatically.  The steps below
> are only needed when restoring a backup bundle that still carries the
> old `imported/<owner-id>/` layout.

**Flat layout on a restored bundle — one command, no hand-written SQL:**

```powershell
# After 4.1 (database) and 4.3 (configuration) - the storage root of
# libretime.conf must exist and hold the restored media\imported\<id>\...
C:\rastatime\.venv\Scripts\python.exe -m libretime_api.manage storage_flatten          # dry run, prints the plan
C:\rastatime\.venv\Scripts\python.exe -m libretime_api.manage storage_flatten --apply  # moves entries, rewrites rows
```

Run it from `C:\rastatime\backend\api` with the API service environment
(`DJANGO_SETTINGS_MODULE=libretime_api.settings.prod`,
`LIBRETIME_CONFIG_FILEPATH`).  The dry run lists the entries to move and
the rows to rewrite (`cc_files.filepath`, `cc_files.artwork`,
`cc_show.image_path`, the auto-dj logo preference) and how many file
paths resolve on disk before and after; `--apply` does both in one
transaction and undoes both on failure.  Only owner ids that exist as
directories under `imported\` are stripped (`--owner-id N` names one
whose directory is already gone), so a purely numeric artist folder is
never mistaken for an owner id and the command may be re-run.

**New root (`D:\stor`):** until the Local Machine setting exists (stage
2), point `storage.path` in `libretime.conf` at the new root, copy the
library there (`robocopy <old> <new> /MIR`), restart RASTATIME-API,
RASTATIME-WORKER, RASTATIME-ANALYZER and RASTATIME-PLAYOUT, and verify
three tracks, a cover and the show image in the UI.  No database change
is needed any more: every stored path is relative to the root.

### 4.5 Restore media library into the new flattened layout

Superseded by the `storage_flatten` command in §4.4: restore the bundle
as it is (`robocopy <bundle>\media <root> /MIR`), then run the command.

### 4.6 Restore recordings

```powershell
robocopy "C:\rastatime-migration\Show Recordings"      "C:\Users\studio\Music\Show Recordings"      /MIR
robocopy "C:\rastatime-migration\Permanent Recordings" "C:\Users\studio\Music\Permanent Recordings" /MIR
robocopy "C:\rastatime-migration\Import"               "C:\Users\studio\Music\Import"               /MIR
```

### 4.7 Install the NSSM services

> **Revised 2026-08-27.** Earlier drafts restored services by running
> `nssm dump` output as PowerShell — that never worked: the deployed
> NSSM **2.24 has no `dump` command** (a 2.25-prerelease feature; on
> 2.24 it just opens the NSSM GUI), and `powershell.exe -File` refuses
> `.txt` files outright.  Services are installed **fresh** via the
> install scripts — the path the 2026-08-26 migration actually took.
> The `nssm-env-*.txt` exports from §2.2 serve as reference for the
> env blocks, nothing more.

```powershell
# The six infra scripts (services install stopped; Phase D starts them):
foreach ($s in @('api','worker','playout','analyzer','apache')) {
    powershell -ExecutionPolicy Bypass `
        -File "C:\rastatime\infra\nssm\install-$s.ps1"
}
# Icecast needs the explicit exe path (production layout C:\Tools\Icecast):
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\infra\nssm\install-icecast.ps1 `
    -IcecastExe 'C:\Tools\Icecast\bin\icecast.exe'
# Liquidsoap has its own script:
powershell -ExecutionPolicy Bypass `
    -File C:\rastatime\backend\playout\config\nssm-install-liquidsoap.ps1
```

Caveat: `install-playout.ps1` does **not** set the engine variables.
After it runs, set the **full** `AppEnvironmentExtra` on
RASTATIME-PLAYOUT yourself — `nssm set` **replaces** the whole env
block, so repeat the five script-set vars *and* add the three extras:

```powershell
& "C:\Tools\nssm\nssm.exe" set RASTATIME-PLAYOUT AppEnvironmentExtra `
    "DJANGO_SETTINGS_MODULE=libretime_api.settings.prod" `
    "LIBRETIME_CONFIG_FILEPATH=C:\rastatime\config\libretime.conf" `
    "RASTATIME_API_URL=http://127.0.0.1:8765" `
    "PYTHONPATH=C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime" `
    "PATH=C:\ffmpeg\bin;%PATH%" `
    "RASTATIME_MPV_LOG_LEVEL=warn" `
    "RASTATIME_PLAYOUT_ENGINE=liquidsoap" `
    "RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0"
```

Verify the env-vars are complete (especially the Liquidsoap engine flag):

```powershell
& "C:\Tools\nssm\nssm.exe" get RASTATIME-PLAYOUT AppEnvironmentExtra
# Must contain, BESIDES the five install-script vars
# (DJANGO_SETTINGS_MODULE=libretime_api.settings.prod,
#  LIBRETIME_CONFIG_FILEPATH=..., RASTATIME_API_URL=http://127.0.0.1:8765,
#  PYTHONPATH=..., PATH=C:\ffmpeg\bin;%PATH%), the three engine extras:
#   RASTATIME_MPV_LOG_LEVEL=warn
#   RASTATIME_PLAYOUT_ENGINE=liquidsoap
#   RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0
```

### 4.8 New IP / hostname adjustments

> **This migration moves to a NEW IP/hostname** (operator decision
> 2026-06-16 — not the old machine's address).  The restored configs still
> point at the old IP; update every reference **before** the smoke test so
> the new machine is self-consistent.  (For a same-IP swap, skip this
> section — that is the doc's default assumption elsewhere.)

- **`libretime.conf` → `general.public_url`** — set to the new address
  (`http://<new-ip>` or `https://<new-host>`).  It is interpolated into
  RSS/podcast self-links, episode `download_url`, station-image URLs and
  UI-side absolute links — a wrong value breaks feeds + embeds.
- **Icecast** (`icecast.xml`) — `<hostname>` and any per-mount public URL
  to the new address; restart Icecast afterwards.
- **Windows Firewall** — open the stream/DJ/web ports on the **new**
  machine: 8000 (Icecast), 8001 (Liquidsoap DJ harbor — `/main` and
  `/show` share it; 8002 is only its ICY companion listener), 80/443
  (web UI).
- **External references** (off the box) — website `<audio src>`, the
  request-/now-playing-widget iframes, external monitoring (Uptime-Robot),
  and any DNS A-record must point at the new address.
- **DJ tools** (BUTT / Mixxx / Traktor) — new server-host; port, mount and
  password stay the same.

After these, the new machine streams on its own IP independently of the old
one — verify in §5.4.

### 4.9 `rastatime.liq` — rendered by the playout, not by hand

The Liquidsoap production script `C:\Tools\liquidsoap\rastatime.liq` is
**machine-generated**: rendered from the template plus the stream
outputs stored in the restored DB (`cc_pref` keys `stream_output_N` —
**not** `libretime.conf`).  Any copy that came over in the bundle still
embeds the old machine's values.

**RASTATIME-PLAYOUT re-renders the script at every startup** — with the
`stream.harbor` DJ passwords from `libretime.conf` and the crossfade
setting from its service environment.  So in the §5.1 smoke test, after
all services are up, restart Liquidsoap **once** so it loads the script
the playout just rendered:

```powershell
nssm restart RASTATIME-LIQUIDSOAP
# Then verify the DJ harbors are listening:
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8001,8002 }
```

> **Do NOT use the manual CLI render**
> (`python -m libretime_playout.liquidsoap_config render`) on a
> configured system: it does not read `stream.harbor` and strips the DJ
> harbor inputs from the script (found the hard way on 2026-08-27 —
> the DJ harbor on 8001 was dead until a Liquidsoap restart with the
> playout-rendered script; `/main` and `/show` share port 8001).  The same rule applies after **any**
> Settings → Streams change: `nssm restart RASTATIME-PLAYOUT`, then
> `nssm restart RASTATIME-LIQUIDSOAP`.

---

## 5. Phase D — Smoke test (BEFORE cutover)

**On the new machine, with the old machine still serving listeners:**

### 5.1 Start all services

```powershell
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ANALYZER",
    "RASTATIME-ICECAST","RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) {
    Start-Service $svc
}
Start-Sleep -Seconds 30
Get-Service RASTATIME-* | Format-Table Name, Status -AutoSize
# All 7 should be Running.

# API health gate — the API listens on 8765 (port 8000 is Icecast):
curl.exe -i http://127.0.0.1:8765/health
# Expect HTTP 200.
```

### 5.2 Web-UI loads
- Open `http://<new-machine-ip>/` in a browser
- Login with operator credentials (from the restored database)
- Calendar shows your schedule
- Settings → Streams shows configured outputs
- Settings → Local Machine shows the three folders (show recordings,
  permanent recordings, import inbox)

### 5.3 Telnet sanity-check
```powershell
& "C:\rastatime\.venv\Scripts\python.exe" -c "from libretime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient; c=LiquidsoapTelnetClient(); print('uptime:', c.send_command('uptime')); print('engine OK')"
```

### 5.4 Listen on the new machine's stream (PRIVATE TEST URL)
```
http://<new-machine-ip>:8000/rastatime
```
You should hear audio (whatever is currently scheduled, or
silence if nothing).  This is **independent** of the old machine
which is still serving the public stream — they're separate
Icecast instances on separate IPs.

### 5.5 Test recording (optional but recommended)

Schedule a 5-min show with `record = true` for the next few
minutes.  Verify the .mp3 lands in the recording folder with
correct duration via ffprobe.

If any smoke-test fails → **don't cutover**.  Fix on the new
machine while the old machine keeps the public stream alive.

---

## 6. Phase E — Cutover (listener downtime here)

Pick a low-traffic time slot.  Expected downtime: **5-15 min**.

### 6.1 Notify any live DJs
DJ-side config (BUTT, Mixxx, Traktor) must point at the new
machine's IP.  Tell them now.

### 6.2 Stop old machine services
```powershell
# On the OLD machine
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ANALYZER",
    "RASTATIME-ICECAST","RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) {
    Stop-Service $svc
}
```

### 6.3 DNS / IP cutover
- **New IP/hostname (this migration):** the new machine keeps its **own**
  address — the in-box configs were already pointed at it in §4.8.  Here you
  only repoint the **outside** world: DNS A-record → new IP, and every
  external embed/widget/monitor (see §4.8) → new address.  No need to steal
  the old machine's IP.
- **If you use DNS** (e.g. `radio.example.org` points at the machine):
  update the A-record to new IP, wait for TTL (usually 5 min).
- **If a same-IP swap instead**: change the new machine to the old
  machine's IP (brief network reconfiguration; then §4.8 is not needed).
- **Firewall rules**: forward ports 8000 (Icecast), 8001 (Liquidsoap
  DJ harbor — both mounts; 8002 = ICY companion), 80/443 (web UI) to
  the new machine.

### 6.4 DJ-tool reconfiguration
- BUTT / Mixxx / Traktor: update server-host to new machine's
  IP/hostname.  Port + mount + password stay the same.

### 6.5 Listener-side reconnect
Public listeners will reconnect within 10-30 s of the old
machine's Icecast going down (player's standard retry).  If the
new machine is reachable on the same DNS/IP, no listener action
required.

---

## 7. Phase F — Post-migration

### 7.1 Verify (next 24-48 h)
- Audio continuity: spot-check the stream every few hours
- Show-record files: verify they appear with correct duration
- Liquidsoap log: no `Latency is too high` catchups (this was the
  whole point of the hardware upgrade)
- Pypo log: no errors, schedule refreshes happen on time
- Disk usage: media library on D: (or still `C:\rastatime\media` while
  the §4.4 storage cleanup is pending), recordings on C: (or wherever
  configured), no disk filling up unexpectedly

### 7.2 Decommission old machine
After **2 weeks of stable new-machine operation**:
- Stop old machine's services permanently
- Disconnect from network
- Keep powered off but accessible for **at least 30 days** as
  emergency-rollback option
- After 30 days: wipe disks, re-purpose hardware

### 7.3 Update operator documentation
- Note the new machine's IP in your operator handbook
- Update any external monitoring (Uptime-Robot etc.) to new
  hostname
- Backup-job destination: update if the old backup target was
  the old machine

---

## 8. Rollback path (if migration fails)

If the new machine has issues within the first 24 h:

### 8.1 Stop new machine services
```powershell
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ANALYZER",
    "RASTATIME-ICECAST","RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) { Stop-Service $svc }
```

### 8.2 Restart old machine services
```powershell
# On the OLD machine
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ANALYZER",
    "RASTATIME-ICECAST","RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) { Start-Service $svc }
```

### 8.3 DNS/IP back to old machine
Reverse step §6.3.

### 8.4 DJ-tools back to old IP/hostname
Tell DJs.

### 8.5 Diagnose new machine without time pressure
With the public stream back on the old machine, you have all the
time you need to debug the new one.

---

## 9. Related documentation

- [`INSTALL.md`](INSTALL.md) — fresh-install procedure (referenced
  in Phase B)
- [`BACKUP.md`](BACKUP.md) — routine backup procedure (referenced
  in Phase A)
- [`LIQUIDSOAP_CUTOVER.md`](LIQUIDSOAP_CUTOVER.md) — engine-mode
  cutover (the env-var setup of Phase C §4.7)
- [`CRASH_RECOVERY.md`](CRASH_RECOVERY.md) — if the new machine
  crashes mid-migration
- ARCHITECTURE §23 — system design context (file paths, service
  topology, why the components exist)
