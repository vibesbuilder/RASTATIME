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

### 2.1 Run the BACKUP.md "Full Backup Script"

See [`BACKUP.md` §6](BACKUP.md) for the canonical full-backup
PowerShell script.  Run it; it produces:

```
C:\rastatime-backup\<YYYY-MM-DD>\
    pg-rastatime.dump      (PostgreSQL custom format)
    pg-libretime.dump
    libretime.conf
    icecast.xml
    .env-files
    media-library-tree.csv  (file inventory)
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

# 4) NSSM service configurations (env-vars, paths, restart policies)
#    "nssm dump" produces a "nssm install" + "nssm set" script
#    that recreates the service identically on the new machine.
$nssm = "C:\Tools\nssm\nssm.exe"
foreach ($svc in @(
    "RASTATIME-APACHE",
    "RASTATIME-API",
    "RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP",
    "RASTATIME-PLAYOUT",
    "RASTATIME-WORKER"
)) {
    & $nssm dump $svc 2>&1 | Out-File "$BUNDLE\nssm-$svc.txt" -Encoding UTF8
}

# 5) Recordings (operator content — important to preserve)
robocopy "C:\Users\studio\Music\Recording" "$BUNDLE\Recording" /MIR

# 6) Media library (the bulk — easily 10-100 GB)
#    This is the slow part.  ~30 GB takes ~5 min on Gigabit LAN.
#    The real storage path is C:\rastatime\media (libretime.conf
#    storage.path) — NOT C:\rastatime\stor (that path never existed;
#    earlier drafts of this doc were wrong).  Verify with:
#      (Get-Content C:\rastatime\config\libretime.conf | Select-String 'path:')
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
- Configure network: static IP or DHCP-reservation matching the
  old machine if possible (so DNS/firewall rules carry over)

### 3.2 Bitdefender install + MANDATORY exclusions

Install Bitdefender **before** the RASTATIME stack so first-run-
scan doesn't fight the installer.

**Exclusion list** (Settings → Antivirus → Manage Exceptions):

```
Paths:
  C:\RASTATIME
  C:\Tools
  C:\Program Files\PostgreSQL\17\data
  C:\Users\studio\Music\Recording             ← Operator's recording folder
  C:\rastatime                                ← runtime, scheduler cache, logs
  D:\stor                                     ← media library on SSD-B (new!)

Processes:
  C:\Tools\liquidsoap\liquidsoap.exe
  C:\Tools\nssm\nssm.exe
  C:\rastatime\.venv\Scripts\python.exe
  C:\Program Files\Icecast\Icecast2.exe
  C:\Program Files\PostgreSQL\17\bin\postgres.exe
  C:\xampp\php\php-cgi.exe                    ← or wherever PHP-CGI lives
  C:\Apache24\bin\httpd.exe
```

Set Bitdefender update-check interval to **24h** (Settings → Update).
The default "every 30 min" produces I/O spikes that catchup the
Liquidsoap pipeline (Phase-D learning 2026-05-29).

### 3.3 Run INSTALL.md

Follow [`INSTALL.md`](INSTALL.md) §4 step-by-step to install:
- PostgreSQL 17
- Python 3.13 + venv at `C:\rastatime\.venv`
- Apache + PHP
- Icecast
- NSSM (`C:\Tools\nssm\nssm.exe`)
- All 6 RASTATIME NSSM services (APACHE, API, ICECAST,
  LIQUIDSOAP, PLAYOUT, WORKER)
- FFmpeg (for legacy mpv fallback path + Pypo audio analyzer)

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

### 4.1 PostgreSQL databases

```powershell
# Stop the API + Worker services while DB is being restored
Stop-Service RASTATIME-API, RASTATIME-WORKER

$pgrestore = "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe"
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"

# Drop the empty databases created by INSTALL.md
& $psql -U postgres -c "DROP DATABASE IF EXISTS rastatime;"
& $psql -U postgres -c "DROP DATABASE IF EXISTS libretime;"
& $psql -U postgres -c "CREATE DATABASE rastatime;"
& $psql -U postgres -c "CREATE DATABASE libretime;"

# Restore from the dumps
& $pgrestore -U postgres -d rastatime C:\rastatime-migration\pg-rastatime.dump
& $pgrestore -U postgres -d libretime C:\rastatime-migration\pg-libretime.dump

Start-Service RASTATIME-API, RASTATIME-WORKER
```

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
# Icecast credentials, the lot)
Copy-Item C:\rastatime-migration\libretime.conf C:\rastatime\etc\ -Force

# Icecast config
Copy-Item C:\rastatime-migration\Icecast\icecast.xml `
    "C:\Program Files\Icecast\" -Force
```

### 4.4 Storage cleanup — new root + drop the owner-id subfolder

The migration is the right moment to clean up two storage warts that
can't be changed safely on a live machine:

1. **New root `D:\stor`** (SSD-B) instead of `C:\rastatime\media`
   inside the project folder.  Keeps the media library off the system
   drive and out of the repo tree.
2. **Drop the `imported/<owner-id>/` level.**  On the old machine the
   audio library lives under `media\imported\2\<artist>\<album>\...`
   where `2` is the importing operator's user-id.  For a single-
   operator station that level is pointless; the new layout is
   `D:\stor\imported\<artist>\<album>\...`.

This is a coordinated **code + data + DB** change.  Do all three in
this maintenance window — never piecemeal on a live machine.

**(a) Code patch — stop the importer re-creating the owner-id level.**
On the new machine, in the restored repo, edit
`frontend/legacy/application/services/MediaService.php` (the
`importFileToLibrary` method):

```php
// OLD:
$importedStorageDirectory = Config::getStoragePath() . '/imported/' . $fileOwnerId;
// NEW (drop the owner-id segment):
$importedStorageDirectory = Config::getStoragePath() . '/imported';
```

> Without this patch the importer would re-create `imported/<owner-id>/`
> for every new upload on the new machine, undoing the cleanup.
> (Show-images and auto-dj-logos keep their own `imported/<owner-id>/…`
> subtrees — they're tiny and out of scope here; bereinige sie später
> falls gewünscht.)

**(b) Config — point the storage path at the new root.**
Edit `C:\rastatime\config\libretime.conf`:

```yaml
storage:
  path: D:/stor          # was C:/rastatime/media on the old machine
```

**(c) DB — update the storage dir + every file path in one transaction.**
`cc_music_dirs.directory` holds the storage root; `cc_files.filepath`
holds each track's path **relative to that root** (e.g.
`imported/2/Artist/Album/track.mp3`).  Both must change: new root, and
the `2/` segment removed.

```powershell
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
& $psql -U postgres -d libretime -v ON_ERROR_STOP=1 -c @"
BEGIN;
-- 1) storage root (the 'stor'-type music dir)
UPDATE cc_music_dirs
   SET directory = 'D:/stor/'
 WHERE type = 'stor';
-- 2) cc_pref storage_path mirror (if present)
UPDATE cc_pref SET valstr = 'D:/stor' WHERE keystr = 'storage_path';
-- 3) drop the 'imported/<digits>/' owner-id level from every file path
UPDATE cc_files
   SET filepath = regexp_replace(filepath, '^imported/[0-9]+/', 'imported/')
 WHERE filepath LIKE 'imported/%';
COMMIT;
"@
```

> The `regexp_replace` only rewrites the leading `imported/<digits>/`
> prefix — artist/album/file parts are untouched.  Run it once; it's
> idempotent (a second run finds no `imported/<digits>/` left to match).

### 4.5 Restore media library into the new flattened layout

```powershell
# The backup bundle has the OLD layout: ...\media\imported\2\<artist>\...
# Move the CONTENTS of imported\2\ up one level into D:\stor\imported\.
mkdir D:\stor\imported -Force

# Everything under the owner-id folder → D:\stor\imported\ (flattened)
robocopy C:\rastatime-migration\media\imported\2 D:\stor\imported /MIR

# Any non-owner-id entries that already sat directly under imported\
# (rare, but copy them too if present):
Get-ChildItem C:\rastatime-migration\media\imported -Directory |
    Where-Object { $_.Name -notmatch '^\d+$' } |
    ForEach-Object {
        robocopy $_.FullName "D:\stor\imported\$($_.Name)" /MIR
    }

# Verify the track count matches the DB
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
& $psql -U postgres -d libretime -t -c "SELECT count(*) FROM cc_files WHERE filepath LIKE 'imported/%';"
(Get-ChildItem D:\stor\imported -Recurse -File | Measure-Object).Count
```

> **Verification before go-live:** pick 3 tracks in the UI, hit play
> on each.  If they play, the path rewrite + file move line up.  If a
> track 404s, the `cc_files.filepath` and the on-disk path disagree —
> re-check step 4.4(c) and the robocopy source/target.

**Show-images / auto-dj-logos note:** these still live under
`imported/<owner-id>/show-images/` and `imported/<owner-id>/auto-dj-logos/`.
The robocopy in this step flattened `imported/2/` wholesale, so those
subtrees moved to `D:\stor\imported\show-images\` etc. — but the DB
columns that reference them (`cc_show.image_path`, the auto-dj-logo
preference) still contain the `2/` segment.  Either leave those two
features' images as-is (re-upload on demand) or extend step 4.4(c)
with the matching `regexp_replace` on those columns.

### 4.6 Restore recordings

```powershell
robocopy C:\rastatime-migration\Recording "C:\Users\studio\Music\Recording" /MIR
```

### 4.7 Restore NSSM service configurations

The `nssm-*.txt` files from §2.2 are PowerShell-runnable scripts
that recreate each service with the exact same env-vars, paths,
and restart policies:

```powershell
# Stop old services first if they exist (from INSTALL.md fresh-install)
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT","RASTATIME-WORKER"
)) {
    Stop-Service $svc -ErrorAction SilentlyContinue
    & "C:\Tools\nssm\nssm.exe" remove $svc confirm
}

# Re-create each from the dump
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT","RASTATIME-WORKER"
)) {
    & powershell.exe -File "C:\rastatime-migration\nssm-$svc.txt"
}
```

Verify the env-vars came across (especially the Liquidsoap engine flag):

```powershell
& "C:\Tools\nssm\nssm.exe" get RASTATIME-PLAYOUT AppEnvironmentExtra
# Expected (3 lines):
#   RASTATIME_MPV_LOG_LEVEL=warn
#   RASTATIME_PLAYOUT_ENGINE=liquidsoap
#   RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0
```

---

## 5. Phase D — Smoke test (BEFORE cutover)

**On the new machine, with the old machine still serving listeners:**

### 5.1 Start all services

```powershell
foreach ($svc in @(
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT","RASTATIME-WORKER"
)) {
    Start-Service $svc
}
Start-Sleep -Seconds 30
Get-Service RASTATIME-* | Format-Table Name, Status -AutoSize
# All should be Running.
```

### 5.2 Web-UI loads
- Open `http://<new-machine-ip>/` in a browser
- Login with operator credentials (from the restored database)
- Calendar shows your schedule
- Settings → Streams shows configured outputs
- Settings → Local Machine shows recording folder

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
    "RASTATIME-APACHE","RASTATIME-API","RASTATIME-ICECAST",
    "RASTATIME-LIQUIDSOAP","RASTATIME-PLAYOUT","RASTATIME-WORKER"
)) {
    Stop-Service $svc
}
```

### 6.3 DNS / IP cutover
- **If you use DNS** (e.g. `radio.example.org` points at the machine):
  update the A-record to new IP, wait for TTL (usually 5 min).
- **If listeners connect directly to IP**: change the new machine
  to the old machine's IP (you may need a brief network
  reconfiguration).
- **Firewall rules**: forward ports 8000 (Icecast), 8001 (DJ
  harbor), 80/443 (web UI) to the new machine.

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
- Disk usage: media library on D:, recordings on C: (or wherever
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
foreach ($svc in @(...)) { Stop-Service $svc }
```

### 8.2 Restart old machine services
```powershell
# On the OLD machine
foreach ($svc in @(...)) { Start-Service $svc }
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
  cutover (the env-var setup of Phase B §4.7)
- [`CRASH_RECOVERY.md`](CRASH_RECOVERY.md) — if the new machine
  crashes mid-migration
- ARCHITECTURE §23 — system design context (file paths, service
  topology, why the components exist)
