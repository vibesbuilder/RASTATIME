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

The media library (the audio files themselves) is **not** included in
this stage.  It is many gigabytes and is backed up server-side; see
[Local Machine](./LOCAL_MACHINE.md) for where the library lives.

## 1. The backup folder

Enter an absolute path on a local drive, for example
`D:\rastatime-backups`, then click **Check** and **Save folder**.

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

## 3. Existing backups

The table lists every backup in the folder, newest first, with size
and creation time.  **Download** saves the ZIP through the browser —
useful for keeping an off-machine copy.  The files on disk stay
untouched; delete old ones by hand when you no longer need them.

## 4. Restoring

Restoring replaces the running database and is therefore a deliberate,
documented offline procedure — services stopped, database restored
with `pg_restore`, services started.  Follow
`docs/operator/BACKUP.md`, section 7.  The `db.dump` inside the ZIP is
exactly what `pg_restore` expects.

## 5. Good practice

- Back up before anything you would hate to redo: bulk deletions,
  big schedule changes, version updates.
- Download a copy to another machine now and then — a backup on the
  same computer does not survive that computer.
- The configuration files inside the ZIP contain service passwords.
  Treat downloaded backups like the passwords they contain.
