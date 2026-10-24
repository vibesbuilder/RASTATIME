# Backup

> **Where you are in the manual.** This chapter covers the
> Settings → **Backup** page: one-click backups of the database and
> the configuration into a folder you choose, and downloading them
> through the browser.  Restoring a backup is a deliberate offline
> procedure and is documented for administrators in
> `docs/operator/BACKUP.md` — it is not a button.

Everything RASTATIME knows — shows, schedule, library metadata, users,
settings — lives in the PostgreSQL database; the service passwords and
ports live in a handful of configuration files.  The **Backup** page
writes both into a single self-contained ZIP per run.

The media library (the audio files themselves) is never zipped — it
is many gigabytes.  Instead, enable **Include media library** and it
is mirrored server-side next to the ZIPs; see section 3.

## 1. The backup folder

Enter an absolute path on a local drive, for example
`D:\rastatime-backups`, then click **Check** and **Save settings**.

- The folder is created if it does not exist.
- It must not lie inside the media library.
- Ideally it sits on a **different drive** than the database, so one
  failing disk cannot take both.
- Network paths are not supported.

## 2. Back up now

**Back up now** starts the backup on the server and reports below the
buttons; a few seconds later the new file appears under **Existing
backups**.  Each backup is one ZIP named after its creation time:

```
rastatime-backup-2026-09-16T1830.zip
    db.dump          the full database (pg_dump custom format)
    config/…         every configuration file (libretime.conf, …)
    manifest.json    what is inside, created when, with which pg_dump
```

A backup that fails (for example because PostgreSQL is unreachable)
leaves **no** half-written ZIP behind; the message under the buttons
shows the reason.  A backup interrupted by a service restart shows as
interrupted — simply run it again.

## 3. Including the media library

Tick **Include media library** and click **Save settings**.  From then
on every run also synchronises the library into the subfolder `media`
next to the ZIPs:

- **Incremental.**  Only new and changed files are copied; files you
  deleted from the library disappear from the mirror too.  The mirror
  is always *the current* library, not a history.
- **Verified.**  After every run each library file is checked against
  the mirror (existence and size); a mismatch fails the backup.
- **First run.**  Copies everything and can take a while — the
  progress bar shows how far it is.  **Cancel** stops the mirror (the
  database ZIP is already complete at that point); the next run simply
  resumes where it stopped.

The mirror never travels through the browser.  To restore media, copy
the contents of `media` back into the library root shown under
[Local Machine](./LOCAL_MACHINE.md).

## 4. Existing backups

The table lists every backup in the folder, newest first, with size
and creation time.  **Download** saves the ZIP through the browser —
useful for keeping an off-machine copy.  The files on disk stay
untouched; delete old ones by hand when you no longer need them.

## 5. Automatic backups

Tick **Enable automatic backups**, choose how often (**Run every** N
days) and how long to keep old ZIPs (**Keep backups for** N days,
0 = keep everything), then **Save automatic backups**.

The clockwork is a Windows scheduled task that an administrator
registers **once** (elevated PowerShell):

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\scripts\backup-auto.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 03:30
Register-ScheduledTask -TaskName "RASTATIME-Backup" -Action $action `
    -Trigger $trigger -User "SYSTEM" -RunLevel Highest
```

The task fires daily, but the run itself decides whether a backup is
due from the settings on this page - so "every 7 days" works with a
daily task.  Each run uses the same folder and media setting as the
manual backup, appends its outcome to `logs\backup-auto.log`, and
afterwards deletes ZIPs older than the retention period.  The newest
backup always survives, whatever its age; the media mirror is a single
mirror and is never pruned.

## 6. Restoring

Restoring replaces the running database and is therefore a deliberate,
documented offline procedure — services stopped, database restored
with `pg_restore`, services started.  Follow
`docs/operator/BACKUP.md`, section 7.  The `db.dump` inside the ZIP is
exactly what `pg_restore` expects.  On the Backup page this note is
the first section, above Manual Backup.

## 7. Good practice

- Back up before anything you would hate to redo: bulk deletions,
  big schedule changes, version updates.
- Download a copy to another machine now and then — a backup on the
  same computer does not survive that computer.
- The configuration files inside the ZIP contain service passwords.
  Treat downloaded backups like the passwords they contain.
