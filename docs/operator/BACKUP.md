# BACKUP.md — RASTATIME Backup and Restore

**Status:** Accepted  
**Task:** T23.2  
**Date:** 2026-04-30

---

## 1. Overview

A complete RASTATIME backup covers three categories:

| Category | Contents | Criticality |
|---|---|---|
| **Database** | All schedule, media metadata, user, and history data | Critical |
| **Configuration** | `rastatime.conf`, `icecast.xml`, environment overrides | Critical |
| **Media library** | Audio files managed by RASTATIME | High (may be large) |

Log files under `C:\rastatime\logs` are **not** backed up — they are
operational artifacts that can be recreated.  The Python venv and source
code are also excluded (restored from version control or a release archive).

---

## 2. Backup Location

Store backups outside the `C:\rastatime\` tree so they survive a
`Remove-Item -Recurse C:\rastatime` uninstall.

Recommended layout:

```
C:\rastatime-backups\
├── db\
│   ├── rastatime-2026-04-30T0200.sql
│   └── rastatime-2026-04-29T0200.sql
├── config\
│   ├── rastatime.conf.2026-04-30
│   └── icecast.xml.2026-04-30
└── media\           (optional; may be on a separate volume)
```

---

## 3. Database Backup

RASTATIME stores all state in PostgreSQL (port **5432**).  Use `pg_dump`
to produce a consistent, portable SQL backup.

### 3.1 Manual backup

```powershell
# Substitute your actual database name, user, and password:
$Date   = Get-Date -Format "yyyy-MM-ddTHHmm"
$OutDir = "C:\rastatime-backups\db"
$File   = "$OutDir\rastatime-$Date.sql"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# Plain-text SQL dump (portable, human-readable):
pg_dump `
    --host=127.0.0.1 `
    --port=5432 `
    --username=rastatime `
    --dbname=rastatime `
    --file=$File `
    --format=plain `
    --no-password    # set PGPASSWORD env var instead of interactive prompt

Write-Host "Backup written to $File  ($([math]::Round((Get-Item $File).Length/1MB, 1)) MB)"
```

Set `PGPASSWORD` to avoid the interactive password prompt:

```powershell
$env:PGPASSWORD = "your-db-password"
pg_dump --host=127.0.0.1 --port=5432 --username=rastatime `
        --dbname=rastatime --file=$File --format=plain
Remove-Item Env:\PGPASSWORD   # clear from environment afterwards
```

### 3.2 Custom (compressed) format

The custom format is faster to restore for large databases:

```powershell
pg_dump `
    --host=127.0.0.1 --port=5432 `
    --username=rastatime --dbname=rastatime `
    --file="$OutDir\rastatime-$Date.dump" `
    --format=custom --compress=9
```

Restore with `pg_restore` (see §4.1).

### 3.3 Scheduled nightly backup (Task Scheduler)

> **Since 2026-09-17 the recommended path is the built-in automatic
> backup**: configure it under Settings → Backup (frequency,
> retention, optional media mirror) and register the ready-made
> runner `scripts\backup-auto.ps1` once as a daily task (the exact
> command is in the script header and in the user manual's Backup
> chapter).  It produces the same self-contained ZIPs as the Backup
> page and prunes old ones itself.  The recipe below remains for a
> plain pg_dump without the UI.


Create a PowerShell script at `C:\rastatime\scripts\backup-db.ps1`:

```powershell
$env:PGPASSWORD = "your-db-password"
$Date  = Get-Date -Format "yyyy-MM-ddTHHmm"
$Out   = "C:\rastatime-backups\db\rastatime-$Date.sql"
New-Item -ItemType Directory -Path "C:\rastatime-backups\db" -Force | Out-Null
pg_dump --host=127.0.0.1 --port=5432 --username=rastatime `
        --dbname=rastatime --file=$Out --format=plain
Remove-Item Env:\PGPASSWORD

# Prune backups older than 30 days:
Get-ChildItem "C:\rastatime-backups\db\*.sql" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force
```

Register in Windows Task Scheduler to run at 02:00 daily:

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
               -Argument "-NonInteractive -File C:\rastatime\scripts\backup-db.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
Register-ScheduledTask -TaskName "RASTATIME-DB-Backup" `
    -Action $action -Trigger $trigger `
    -RunLevel Highest -Force
```

---

## 4. Configuration Backup

Configuration files are small and must always be backed up alongside the
database so a restore produces a fully consistent system.

### 4.1 Files to back up

| File | Location | Notes |
|---|---|---|
| `rastatime.conf` | `C:\rastatime\config\rastatime.conf` | DB credentials, API settings |
| `icecast.xml` | `C:\rastatime\config\icecast.xml` | Stream server config (optional) |
| NSSM env overrides | export via `nssm get` (see below) | Supplement to install scripts |

### 4.2 Backup command

```powershell
$Date    = Get-Date -Format "yyyy-MM-dd"
$CfgOut  = "C:\rastatime-backups\config"
New-Item -ItemType Directory -Path $CfgOut -Force | Out-Null

Copy-Item C:\rastatime\config\rastatime.conf "$CfgOut\rastatime.conf.$Date"

if (Test-Path C:\rastatime\config\icecast.xml) {
    Copy-Item C:\rastatime\config\icecast.xml "$CfgOut\icecast.xml.$Date"
}

# Export current NSSM environment for each service (all 7):
foreach ($svc in "RASTATIME-API","RASTATIME-WORKER","RASTATIME-PLAYOUT",
                 "RASTATIME-ANALYZER","RASTATIME-APACHE","RASTATIME-ICECAST",
                 "RASTATIME-LIQUIDSOAP") {
    $envOut = "$CfgOut\nssm-env-$svc.$Date.txt"
    nssm get $svc AppEnvironmentExtra 2>&1 | Out-File $envOut -Encoding utf8
}

# RASTATIME-PLAYOUT's AppEnvironmentExtra is partly operator-maintained
# (engine selection: RASTATIME_PLAYOUT_ENGINE, RASTATIME_MPV_LOG_LEVEL,
# RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS).  install-playout.ps1 does NOT
# recreate those three values — this export is the only record of them.

Write-Host "Config backup complete: $CfgOut"
```

---

## 5. Media Library Backup

The RASTATIME media library may be several hundred GB.  Back it up to a
separate storage volume or NAS using robocopy or a dedicated backup tool.

> ⚠️ **Run the media copy from an ELEVATED shell (Administrator).**
> Verified 2026-06-17: the podcast-feature downloads
> (`imported/podcast_ep*.mp3` — `imported/2/…` before 2026-09-16, ~33 files in `cc_files`) carry a
> restrictive ACL with **no** access for the `studio` user — a
> non-elevated robocopy **silently skips them** (exit code >= 8,
> "Zugriff verweigert" in the log).  Administrators have full access
> and copy them.  See BACKLOG "Podcast-Downloads: ACL sperrt den
> studio-User aus".

```powershell
# Mirror the media directory to a backup volume (adjust paths):
robocopy C:\rastatime\media  D:\backup\rastatime-media `
    /MIR /R:3 /W:10 /LOG:C:\rastatime-backups\media-robocopy.log

# The /MIR flag keeps the destination in sync (deletes files removed from source).
# Remove /MIR and use /E if you want an accumulating backup instead.
```

> Media files are large — schedule this backup during off-peak hours and
> confirm the destination volume has sufficient free space before running.

---

## 6. Full Backup Script

Combine the above into a single scheduled backup:

```powershell
# C:\rastatime\scripts\backup-full.ps1
$Date = Get-Date -Format "yyyy-MM-ddTHHmm"
$Root = "C:\rastatime-backups"

# 1 — Database
$env:PGPASSWORD = "your-db-password"
$DbOut = "$Root\db\rastatime-$Date.sql"
New-Item -ItemType Directory -Path "$Root\db" -Force | Out-Null
pg_dump --host=127.0.0.1 --port=5432 --username=rastatime `
        --dbname=rastatime --file=$DbOut --format=plain
Remove-Item Env:\PGPASSWORD

# 2 — Config
$CfgOut = "$Root\config"
New-Item -ItemType Directory -Path $CfgOut -Force | Out-Null
Copy-Item C:\rastatime\config\rastatime.conf "$CfgOut\rastatime.conf.$Date"
if (Test-Path C:\rastatime\config\icecast.xml) {
    Copy-Item C:\rastatime\config\icecast.xml "$CfgOut\icecast.xml.$Date"
}

# 3 — Prune DB backups older than 30 days
Get-ChildItem "$Root\db\*.sql" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force

Write-Host "$Date  Full backup complete."
```

---

## 7. Restore Procedures

### 7.1 Restore the database (plain SQL)

```powershell
# Stop all RASTATIME services that write to the database first
# (incl. Apache — the PHP frontend holds DB connections, which would
#  make DROP DATABASE fail with "database is being accessed"):
nssm stop RASTATIME-APACHE   confirm
nssm stop RASTATIME-PLAYOUT  confirm
nssm stop RASTATIME-ANALYZER confirm
nssm stop RASTATIME-WORKER   confirm
nssm stop RASTATIME-API      confirm

# Drop and recreate the database:
$env:PGPASSWORD = "superuser-password"
psql -U postgres -h 127.0.0.1 -p 5432 -c "DROP DATABASE IF EXISTS rastatime;"
psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE rastatime OWNER rastatime;"

# Restore from plain SQL backup:
$env:PGPASSWORD = "rastatime-password"
psql -U rastatime -h 127.0.0.1 -p 5432 -d rastatime `
     -f C:\rastatime-backups\db\rastatime-2026-04-30T0200.sql

Remove-Item Env:\PGPASSWORD

# Restart services:
nssm start RASTATIME-API
nssm start RASTATIME-WORKER
nssm start RASTATIME-ANALYZER
nssm start RASTATIME-PLAYOUT
nssm start RASTATIME-APACHE
```

### 7.2 Restore the database (custom format)

```powershell
pg_restore --host=127.0.0.1 --port=5432 `
           --username=rastatime --dbname=rastatime `
           --format=custom --clean --if-exists `
           C:\rastatime-backups\db\rastatime-2026-04-30T0200.dump
```

### 7.3 Restore configuration

```powershell
Copy-Item C:\rastatime-backups\config\rastatime.conf.2026-04-30 `
          C:\rastatime\config\rastatime.conf

# Restart API so it picks up the restored config:
nssm restart RASTATIME-API
```

### 7.4 Restore drill (TEST_PLAN A6.2, quarterly)

Proves that a UI/nightly backup ZIP (`D:\backups`, see the manual's
Backup chapter) restores, **without touching the live database and
without stopping a service**: the dump goes into a scratch database next
to `rastatime`.  The `rastatime` role may create databases, so no
superuser password is needed.  `psql`/`pg_restore` ask for the
`rastatime` password in their own prompt (it is the `database:` password
in `config\rastatime.conf`); never put it on the command line.

```powershell
$pg  = "C:\Program Files\PostgreSQL\17\bin"
$zip = Get-ChildItem D:\backups\rastatime-backup-*.zip | Sort-Object Name | Select-Object -Last 1
$tmp = "D:\backups\restore-drill"

# 1 - unpack the newest ZIP (it holds config files with passwords: delete $tmp at the end)
Expand-Archive $zip.FullName -DestinationPath $tmp -Force
Get-Content "$tmp\manifest.json"

# 2 - scratch database
& "$pg\psql.exe" -h 127.0.0.1 -U rastatime -d postgres -c "CREATE DATABASE rastatime_restore OWNER rastatime;"

# 3 - restore into the scratch database (NOT into rastatime; no --clean)
& "$pg\pg_restore.exe" -h 127.0.0.1 -U rastatime -d rastatime_restore --format=custom --no-owner "$tmp\db.dump"

# 4 - check: schema version = live (System Status shows it), counts plausible, a show of today present
& "$pg\psql.exe" -h 127.0.0.1 -U rastatime -d rastatime_restore -c "SELECT valstr AS schema_version FROM cc_pref WHERE keystr = 'schema_version';" `
    -c "SELECT (SELECT count(*) FROM cc_show) shows, (SELECT count(*) FROM cc_show_instances) instances, (SELECT count(*) FROM cc_files) files, (SELECT count(*) FROM cc_schedule) rows;" `
    -c "SELECT s.name, i.starts FROM cc_show_instances i JOIN cc_show s ON s.id = i.show_id WHERE i.starts::date = current_date ORDER BY i.starts LIMIT 3;"

# 5 - clean up
& "$pg\psql.exe" -h 127.0.0.1 -U rastatime -d postgres -c "DROP DATABASE rastatime_restore;"
Remove-Item -Recurse -Force $tmp
```

Pass: `pg_restore` ends without errors, the schema version equals the
live one, the counts are in the live order of magnitude (the ZIP is from
03:30, so slightly lower), today's shows are listed.  Record the date in
TEST_PLAN / the quarterly check.  A real restore then follows 7.2
(services stopped, into `rastatime`), which is never rehearsed on the
live system.

---

## 8. Backup Verification

Test your backups periodically — an untested backup is not a backup.

```powershell
# Verify the plain SQL file is non-empty and ends correctly:
$f = "C:\rastatime-backups\db\rastatime-2026-04-30T0200.sql"
Get-Item $f | Select-Object Name, Length, LastWriteTime
Select-String "PostgreSQL database dump complete" $f
# Expected: one match at the end of the file

# Verify the media robocopy copied everything (it must have run elevated):
# robocopy exit codes >= 8 mean at least one file FAILED to copy.
Select-String -Pattern "ERROR 5","Zugriff verweigert","Access is denied" `
    -Path C:\rastatime-backups\media-robocopy.log
# Expected: no matches.  Hits here almost always mean the copy ran
# non-elevated and the ACL-restricted podcast downloads were silently
# skipped (see the warning in section 5).
```

---

## 9. Related Documentation

| Document | Description |
|---|---|
| `docs\operator\UPGRADE.md` | Upgrade procedure (includes pre-upgrade backup step) |
| `docs\operator\CRASH_RECOVERY.md` | Recovery from unexpected crashes using backups |
| `docs\operator\RESTART_ORDER.md` | Service startup / shutdown sequence |
| `docs\operator\INSTALL.md` | Fresh installation (includes database creation) |
