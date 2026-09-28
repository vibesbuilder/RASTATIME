# Settings

> **Where you are in the manual.** This chapter is the
> hub-and-spoke index for the Settings menu. Each section
> below points at a dedicated chapter (where one exists) or
> documents the page inline (where the page is too small for
> its own chapter).

The Settings menu is the per-station configuration surface.
Visible only to **Admin** and **Super Admin** in full;
**Program Manager** sees a subset. See
[Users and Roles](./USERS_AND_ROLES.md) §5 for the full
permission matrix.

This chapter:

1. Lists every Settings sub-page with a one-line purpose.
2. Documents inline the smaller pages (General Preferences,
   System Status, Tools).
3. Points at the dedicated manual chapter for the larger
   ones (Streams, Local Machine, Auto DJ, Show Templates,
   Manage Users, Localisation).

---

## 1. The Settings menu

Top-bar Settings → opens the sub-menu:

```
   ┌──────────────────────────┐
   │  Settings                │
   ├──────────────────────────┤
   │  General Preferences     │
   │  Local Machine           │
   │  Streams                 │
   │  Line-In Library         │
   │  Auto DJ                 │
   │  Show Templates          │
   │  Manage Users            │
   │  Localisation            │
   │  System Status           │
   │  Tools  ▾                │
   └──────────────────────────┘
```

### Page-by-page

| Page | Purpose | Manual chapter |
|---|---|---|
| **General Preferences** | Station name, default language, default colours, dashboard look-ahead, default import owner, track and show crossfade durations, favicon, station logo. | This chapter §2 |
| **Local Machine** | Sound-card output / input devices, Local Import Folder, Local Recording Folder. | [Local Machine](./LOCAL_MACHINE.md) |
| **Streams** | Up to four output streams, per-stream bitrate / mountpoint / codec, source authentication. | [Streams](./STREAMS.md) |
| **Line-In Library** | Named live audio inputs from sound-card devices. | [Line-In](./LINE_IN.md) |
| **Auto DJ** | Background gap-filler + incomplete-show top-up. | [Auto DJ](./AUTO_DJ.md) |
| **Show Templates** | Reusable show form snapshots. | [Show Templates](./SHOW_TEMPLATES.md) |
| **Manage Users** | Create / edit / deactivate users, reset passwords, manage API keys. | [Users and Roles](./USERS_AND_ROLES.md) |
| **Localisation** | UI language selection, locale generation. | [Languages](./I18N.md) |
| **System Status** | Live service health, preflight warnings, service restart widget. | This chapter §3 |
| **Tools** | Sub-menu: DB Console, Log Viewer, Cache Reset. | This chapter §4 |

---

## 2. General Preferences

Settings → **General Preferences**.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  General Preferences                                  [ Save ]  │
   ├─────────────────────────────────────────────────────────────────┤
   │  Station                                                        │
   │    Station Name:        [ My Community Radio                  ] │
   │    Station Description: [ A community radio station for ...    ]│
   │    Station Logo:        [ Choose File ▾ ] (currently set)       │
   │    Station Favicon:     [ Choose File ▾ ] (currently set)       │
   │    Time Zone:           [ Europe/Berlin ▾ ]                     │
   │    Week Starts On:      [ Monday ▾ ]                            │
   │                                                                 │
   │  Defaults                                                       │
   │    Default Language:    [ English (en_US) ▾ ]                   │
   │    Default Track Crossfade: [ 1.0 ] seconds                     │
   │    Default Show Crossfade:  [ 1.0 ] seconds                     │
   │    Default Track Type:  [ Music ▾ ]                             │
   │    Default Import Owner:[ admin ▾ ]                             │
   │    Default Recording:   [ ☐ Record all new shows by default ]   │
   │                                                                 │
   │  Dashboard                                                      │
   │    Lookahead:           [ 5 ] upcoming items                    │
   │    Refresh interval:    [ 5 ▾ ] seconds                         │
   │                                                                 │
   │  Email (for password reset)                                     │
   │    SMTP server:         [                                     ] │
   │    SMTP port:           [ 587 ]   Use TLS: [ ☑ ]                │
   │    SMTP user / pass:    [          ] [          ]               │
   │    From address:        [ noreply@my-station.example.com      ] │
   └─────────────────────────────────────────────────────────────────┘
```

### Station

| Field | Notes |
|---|---|
| **Station Name** | Visible everywhere — page title, ICY metadata, email From-name. |
| **Station Description** | Free-text description. Used in podcast feeds and the ICY metadata. |
| **Station Logo** | Image shown in the top-left of every page. Max 200 KB, JPG / PNG / GIF. |
| **Station Favicon** | Image shown in the browser tab. Max 200 KB, JPG / PNG / GIF / ICO. Rendered as a data: URI; no file writes to public/. |
| **Time Zone** | The operator timezone for all calendar / schedule display. Stored per-show in `cc_show_days.timezone` so changing this here does not retroactively affect existing shows. |
| **Week Starts On** | Monday / Sunday. Affects the Calendar's week view layout. |

### Defaults

| Field | Notes |
|---|---|
| **Default Language** | UI language for new users + the login screen. Existing users keep their per-user language preference (set via the user dropdown). |
| **Default Track Crossfade Duration** | The crossfade between two consecutive tracks **of the same show**: the outgoing track fades out while the incoming one fades in over this many seconds (1 second is typical; 0 = the tracks follow each other without overlap; up to 10 seconds for soft transitions). The schedule lays consecutive rows out with exactly this overlap. |
| **Default Show Crossfade Duration** | The transition **at a show boundary** (since 2026-09-27): the old show fades out over this many seconds while the first track of the new show starts at full level at once — so a show that begins with a jingle or ID is heard from its first beat. The same shape and value apply to every switch between **inputs** (track ↔ webstream ↔ Line-In): the incoming source is at full level immediately, the outgoing one fades out underneath; 0 = a hard switch. A webstream or Line-In that is scheduled in both shows keeps playing seamlessly. Start value 1 s. Both crossfade values are applied by the audio chain a few seconds after saving (planned restart at a quiet moment or track boundary); "Apply now" in Settings → Local Machine forces it. |
| **Default Track Type** | The track-type assigned to new uploads when the operator does not explicitly set one. Affects smart-block filters. |
| **Default Import Owner** | The user account credited as owner for files imported via the Local Import Folder. Defaults to `admin`. |
| **Default Recording** | When ticked, new shows have **Record this show:** pre-ticked. See [Record-per-Show](./RECORD_PER_SHOW.md). |

### Dashboard

| Field | Notes |
|---|---|
| **Lookahead** | How many upcoming shows the Dashboard's "Coming Up Next" panel displays. 3-5 is typical. |
| **Refresh interval** | How often the Dashboard polls for updated state. 5 s is the default. 1 s is responsive but expensive on slow networks. 30 s is light but laggy. |

### TuneIn Settings

Collapsible section below General Preferences. Since 2026-09-28 the
playout sends the "now playing" information to TuneIn itself; before,
only file starts were pushed and the display went blank after five
minutes.

| Field | Notes |
|---|---|
| **Push metadata to your station on TuneIn?** | Master switch. When on, the playout sends title and artist at every start of a track and the show name at the start of a webstream or Line-In, and repeats the last update every four minutes (TuneIn removes a display that stays quiet for five minutes). Saving with the switch on tests the credentials against TuneIn and refuses invalid ones. |
| **Station ID**, **Partner Id**, **Partner Key** | From your TuneIn partner account (AIR API). The key never appears in a log. |

A changed setting is picked up at the next push; no restart. A live DJ
(Master / Show Source) is not announced; the last track stays on the
display until the next scheduled item.

### Email (password reset)

If configured, the Manage Users → Reset Password → Send Email
flow sends one-time-link emails. If left blank, the only
reset path is "set temporary password".

| Field | Notes |
|---|---|
| **SMTP server / port** | Your station's outgoing mail server. |
| **TLS** | Recommended on; modern SMTP servers reject unencrypted connections. |
| **From address** | Used as the email's From header. Often required to match the SMTP account. |

> **How it works under the hood.** Settings are written to
> the `cc_pref` table as key/value rows. Most settings
> reload immediately; the SMTP settings require a restart of
> the worker service to pick up. See ARCHITECTURE §11.

---

## 3. System Status

Settings → **System Status**.

Health overview of every component RASTATIME depends on.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  System Status                          [ Refresh ]             │
   ├─────────────────────────────────────────────────────────────────┤
   │  Services                                                       │
   │   ● RASTATIME-API        Running (PID 4321, uptime 4d 12h)      │
   │   ● RASTATIME-WORKER     Running (PID 4322, uptime 4d 12h)      │
   │   ● RASTATIME-PLAYOUT    Running (PID 4323, uptime 4d 12h)      │
   │   ● RASTATIME-ANALYZER   Running (PID 4324, uptime 4d 12h)      │
   │   ● Icecast2             Running (PID 4325, uptime 4d 12h)      │
   │   ● Apache               Running (PID 4326, uptime 4d 12h)      │
   │                                                                 │
   │  Connectivity                                                   │
   │   ✓ Database (PostgreSQL)      Connected, 2 ms response         │
   │   ✓ Icecast source connection  Connected, /rastatime active     │
   │   ⚠ Local Import Folder         3 failed imports — review        │
   │                                                                 │
   │  Preflight warnings                                             │
   │   ⚠ FFmpeg not in PATH (analyzer fell back to bundled copy)     │
   │   ⚠ Postgres host 'db1.example.com' unreachable — using local   │
   │                                                                 │
   │  Service controls                                               │
   │   [ Restart API ] [ Restart Worker ] [ Restart Playout ] [ ... ]│
   └─────────────────────────────────────────────────────────────────┘
```

### Services

Live PID + uptime for each NSSM-managed Windows service. A
red badge here is the signal to check the service via
`Get-Service RASTATIME-*` in PowerShell or the
[`CRASH_RECOVERY`](../operator/CRASH_RECOVERY.md) runbook.

### Connectivity

Live check of each external dependency:

- **Database (PostgreSQL)** — response time (round-trip
  to `SELECT 1`).
- **Icecast source connection** — playout-engine-side
  source-connection state (mirrors the Streams page).
- **Local Import Folder** — recent scan result; a yellow
  badge means files failed playability checks; review the
  `.failed/` directory.

### Preflight warnings

Persisted warnings from the start-up preflight check. Things
like "FFmpeg not in PATH" or "expected port already in use".
Each warning has a click-through with mitigation advice.

> **How it works under the hood.** Driven by the
> `/api/v2/preflight/warnings` endpoint backed by the
> `rastatime_preflight_warning` table. The startup
> `preflight.py` runs ~30 checks and inserts a row per
> failure; the page lists them and the operator can
> dismiss / resolve.

### Service controls (Admin+ only)

One-button restart for each Windows service. Replaces the
need to RDP and run `Restart-Service RASTATIME-PLAYOUT`.

Effects vary per service:

| Service | Restart effect |
|---|---|
| **API** | ~2 s outage of the REST API. UI calls may fail mid-action. |
| **Worker** | Background jobs pause (~10 s). No user-facing effect. |
| **Playout** | **The stream goes silent for ~10 s.** Use sparingly during airtime. |
| **Analyzer** | Local Import Folder pauses (~5 s). |
| **Icecast** | All listeners disconnect; reconnect ~30 s later. |
| **Apache** | The web UI is unreachable for ~5 s. Operators are bounced to the login page. |

> **Operator tip.** Restart only the service that is
> actually misbehaving. Restarting all six in sequence
> works (it is the standard
> [`RESTART_ORDER`](../operator/RESTART_ORDER.md)) but is
> overkill for a single-component issue.

---

## 4. Tools

Settings → **Tools** → sub-menu.

| Tool | Purpose |
|---|---|
| **DB Console** | Read-only PostgreSQL query interface. Super Admin only. Hidden by default; enable in `config/libretime.conf` with `[tools] db_console = true`. |
| **Log Viewer** | Tail the last 200 lines of `C:\rastatime\logs\error.log`, `api-stderr.log`, `playout-stderr.log`. Auto-refresh every 5 s. |
| **Cache Reset** | Clear server-side caches (the Locale string cache, the Library DataTable cache). Use after editing translation files or after a bulk-import. |
| **Rescan Library Playability** | Run the analyzer playability check across every existing track. Slow (minutes on a large library); use after upgrading FFmpeg. Backed by the `infra/scripts/maintenance/rescan-playability.py` script. |

These are *not* daily tools. Most stations never open the
Tools sub-menu.

> **Why DB Console is hidden by default.** A read-only DB
> console can leak credentials in WHERE clauses, dump
> personal data via SELECT, and become a foothold if the
> Super Admin's credentials are compromised. Enable only
> when actively debugging a data question.

---

## 5. Frequently-asked

### "I changed a setting but nothing happens."

Most settings take effect immediately. Exceptions:

| Setting | Requires |
|---|---|
| SMTP | Worker service restart |
| Stream credentials | Playout service restart |
| Sound-card device | Playout service restart |
| Time zone | Hard refresh of the browser (the timezone is cached client-side) |
| Default Language | Logout / login (the language is set per session at login) |

### "Where does Settings store its values?"

Mostly in `cc_pref` (key / value table). Per-user settings
(language, API key) live in `cc_subjs`. Service configuration
that cannot live in the DB (PostgreSQL credentials,
filesystem paths) lives in `config/libretime.conf`.

### "Can I version-control my Settings?"

Indirectly:

- `config/libretime.conf` is a text file — commit it (after
  redacting credentials).
- `cc_pref` rows are not version-controlled. To back up,
  use `pg_dump --table=cc_pref`. See
  [`docs/operator/BACKUP.md`](../operator/BACKUP.md).

### "Can I restore Settings from a backup without touching the database?"

For `cc_pref`-stored settings: only by restoring the
`cc_pref` table from the backup. For
`config/libretime.conf` settings: copy the file.

### "Why are some settings only visible to Super Admin?"

The DB Console, the ability to create other Admins, and the
right to view other users' API keys are reserved for Super
Admin because they grant access escalation. See
[Users and Roles](./USERS_AND_ROLES.md) §1.

---

## 6. Playout Engine (Liquidsoap)

> **Service-level setting**, not a UI setting.  The RASTATIME-PLAYOUT
> NSSM service may carry `RASTATIME_PLAYOUT_ENGINE=liquidsoap` in its
> environment; that is the only accepted value.  Operator-only; not
> exposed in the web UI.

Since 2026-09-10 Liquidsoap is the **only** playout engine.  The
earlier mpv engine (with its FFmpeg streamers for the Icecast outputs)
and the never-finished VLC plan were removed from the code base after
Liquidsoap had carried every schedule item type (files, webstreams,
line-inputs, recording, DJ sources) in production since 2026-05-28.

What Liquidsoap provides:

- **Recording** is captured from the internal audio bus
  (post-switch, post-crossfade, post-amplify) — bit-identical
  to what listeners hear.  Recording bitrate is a fixed 320 kbps MP3,
  archive-grade.
- **Listener experience**: the Icecast mountpoints stay open
  through track/show changes — no reconnect, no counter reset.
- **DJ-Source routing** uses Liquidsoap's `input.harbor` +
  `switch(...)` natively — Master / Show DJ clients connect
  directly to the Liquidsoap-managed harbor (port 8001 by
  default, see [Streams](./STREAMS.md)).

**If the service refuses to start** with

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

the service environment still names the removed engine: set
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` (or remove the variable) in the
NSSM environment of `RASTATIME-PLAYOUT` and start the service again.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` are ignored and can
be removed.

**The engine start is visible in the playout log:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## Where to go next

* Follow the per-page link in the table above to the
  dedicated chapter for any large Settings page.
* [Users and Roles](./USERS_AND_ROLES.md) — permissions
  matrix gating each Settings page.
* [`docs/operator/INSTALL.md`](../operator/INSTALL.md) —
  the initial settings configured at install time.
