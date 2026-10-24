# Password rotation: Harbor fallback, Icecast source, database

Runbook for backlog points 1 and 2 of "Stand vor dem Live-Betrieb"
(2026-10-24).  Two parts, meant for one maintenance window of about
twenty minutes.  The operator types every secret; assistant never sees,
echoes or logs a value.  Rules from `ASSISTANT.local.md` apply: `git tag`
before a live change is not needed here (no code changes), but the
nightly 03:30 backup must have run, and nothing of this happens inside a
show boundary.

## 0. Before you start

- [ ] Newest ZIP in `E:\backups` is from this night (`rastatime-backup-<today>T0330.zip`).
- [ ] Pick the moment: inside a file or playlist show, no live DJ, no
      Line-In slot, at least 15 minutes to the next show boundary.
      Part A costs a few seconds of silence (Liquidsoap restart) and one
      listener reconnect (Icecast restart); part B costs nothing audible.
- [ ] Generate four passwords up front (password manager, 24+ characters).
      Avoid `"`, `\`, `#`, `!`, `:` and leading/trailing spaces - the
      values go into YAML and XML.  Every value in `libretime.conf` is
      written **in double quotes**.

| # | What | Used by |
|---|------|---------|
| P1 | Harbor main fallback | `stream.harbor.main_password` |
| P2 | Harbor show fallback | `stream.harbor.show_password` |
| P3 | Icecast source password | `icecast.xml` `<source-password>`, Settings -> Streams "Source Password" of every output |
| P4 | Database role `rastatime` | PostgreSQL, `database.password` |

(Optional P5: the Icecast admin password, if it is still the shipped
default - `icecast.xml` `<admin-password>` and Settings -> Streams "Admin
Password".  The playout reads listener statistics with it.)

## A. Harbor fallback + Icecast source password (backlog point 2)

Why: `stream.harbor.main_password` / `show_password` are still the
installation placeholders.  Since the UI logins (2026-09-10) they are only
used when PLAYOUT's `/dj-auth` is unreachable - exactly in an emergency.
The Icecast source password is still the shipped default as well.

1. [ ] `C:\RASTATIME\config\libretime.conf`, block `stream.harbor` (around
       line 80): set `main_password: "<P1>"` and `show_password: "<P2>"`.
2. [ ] `C:\Tools\Icecast\icecast.xml`, `<authentication>` block (around
       line 42): `<source-password><P3></source-password>` (and
       `<admin-password><P5></admin-password>` if you rotate it too).
       `<relay-password>` is unused, may stay.
3. [ ] Browser, Settings -> Streams: for **every** output stream
       (stream 1, 2, 3 ...) set "Source Password" = P3 (and "Admin
       Password" = P5 if rotated).  Save.  The playout renders
       `rastatime.liq` and `standby.liq` from these settings.
4. [ ] Elevated PowerShell, in this order (service names are NSSM
       services, `Restart-Service` works):

   ```powershell
   Restart-Service RASTATIME-ICECAST      # new source password active
   Restart-Service RASTATIME-PLAYOUT      # re-renders rastatime.liq + standby.liq
   ```

   Wait until `C:\RASTATIME\logs\playout-stdout.log` shows the start-up
   lines (Main Output resolved, Line-In capture ready), then:

   ```powershell
   Restart-Service RASTATIME-LIQUIDSOAP   # picks up the rendered file now, not at the next track boundary
   Restart-Service RASTATIME-STANDBY
   ```

5. [ ] Verification (assistant does this from the logs, read-only):
   - `liquidsoap-stdout.log`: `Connection setup was successful` for
     `/rastatime`, `/rastatime-aac` and the standby mounts; no
     `401`/`Unauthorized` lines.
   - `playout-stdout.log`: `harbor` lines without `static harbor password`
     warnings; listener stats poll keeps running (every 120 s).
   - Operator: one DJ login with BUTT through the UI credentials
     (Master or show host) still works - it goes through `/dj-auth`, the
     new fallback values are never typed.
6. [ ] Record in CHANGELOG ("Security"), BACKLOG point 2 -> done.  No
       value, no hint of a value, anywhere in git.

## B. Database password (backlog point 1)

Why: the active password of the PostgreSQL role `rastatime` was printed
in the Apache error log on 2026-10-04 (Symfony YAML parse error, an
unquoted `!`).  That file (`C:\Tools\Apache24\logs\error_log`) no longer
exists, the daily `http-error-*.log` files only go back seven days, and
the janitor's monthly archive `logsrchive\logs-2026-10.zip` holds no
error log of 2026-10-04 (checked 2026-10-24).  The exposure on disk is
over - the rotation is hygiene, not an emergency.

Who reads the password: every service through `libretime.conf`
(RASTATIME-API, -WORKER, -PLAYOUT, -ANALYZER), the legacy PHP on every
request (no restart needed), the backup task on every run
(`backup-auto.ps1` -> API), `infra\scripts\rt-blocks.ps1` on every run.
There is no `pgpass.conf` and no second copy.

1. [ ] Change the role's password **inside psql with `\password`** -
       it prompts twice and never echoes, nothing lands in a shell
       history or log:

   ```powershell
   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U rastatime -d rastatime
   ```

   then at the `rastatime=>` prompt:

   ```
   \password rastatime
   \q
   ```

   (A role may change its own password; the current password is asked
   once at connect.)
2. [ ] `C:\RASTATIME\config\libretime.conf`, block `database` (line 26):
       `password: "<P4>"`.  Keep the quotes.
3. [ ] Elevated PowerShell, in the start-up order of `RESTART_ORDER.md`:

   ```powershell
   Restart-Service RASTATIME-API
   Restart-Service RASTATIME-WORKER
   Restart-Service RASTATIME-PLAYOUT
   Restart-Service RASTATIME-ANALYZER
   ```

   Apache / legacy PHP need no restart (the file is read per request).
   PLAYOUT's restart again re-renders the `.liq` files; nothing changes
   in them for this step, so Liquidsoap keeps running.
4. [ ] Verification:
   - Browser: log out, log in, open the calendar and Dashboard -> Tracks
     (legacy PHP with the new password).
   - assistant: `playout-stdout.log` shows `refreshing schedule from API`
     with `armed=N` after the restart; `api` service log without
     `password authentication failed`; analyzer log idle without errors.
   - Settings -> Backup -> "Backup now" (manual ZIP, a few seconds) ->
     a new ZIP in `E:\backups`.
   - Optional: `infra\scripts\rt-blocks.ps1` once (reads the new value
     from the file).
5. [ ] Record in CHANGELOG ("Security"), BACKLOG point 1 -> done, memory
       reminder removed.

## C. Rollback

- Part A: put the old values back in `libretime.conf` / `icecast.xml` /
  Settings -> Streams and repeat step A4.
- Part B: `\password rastatime` again with the old value, restore line 26,
  repeat step B3.  Nothing else holds the password.
