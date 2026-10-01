# Getting Started

> **Where you are in the manual.** This chapter assumes RASTATIME
> is already installed and the web UI is reachable. If neither is
> true yet, go through [`docs/operator/INSTALL.md`](../operator/INSTALL.md)
> first.
>
> **Reading time.** ~15 minutes for the operator track, ~25 with
> the technical asides.

This chapter walks a brand-new operator through their first
login, the first screen they see, the role of each top-level
menu, and the minimum sequence to put a track on air. By the
end you will have:

1. Logged in with the default credentials and changed your
   password.
2. Identified which user role you have and what it lets you do.
3. Found the Library, Calendar, and Dashboard.
4. Created and aired your first scheduled track.
5. Verified the output stream is reaching listeners.

---

## 1. First login

Open `http://<station-host>/` in any modern browser
(Chrome, Edge, Firefox; Internet Explorer is *not* supported).

The default super-admin credentials shipped by a fresh install
are:

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin` |

> **Change this now.** As soon as you have logged in, go to
> **Settings → Manage Users**, click `admin`, and set a real
> password. RASTATIME does not force a password change on first
> login — it cannot, because some installs script the first
> login. The default account is a known attack vector if the
> server is reachable from outside your studio LAN.

> **How it works under the hood.** Credentials live in
> `cc_subjs`. Passwords are hashed (bcrypt). The session cookie
> is `PHPSESSID`; Zend session storage is in
> `C:\rastatime\runtime\sessions\` by default. A login also
> records `last_login` for the user — visible on the Manage
> Users page.

If you cannot log in: the [`CRASH_RECOVERY`](../operator/CRASH_RECOVERY.md)
runbook covers the case where Apache, mod_fcgid, or the API
service is down. Until those are running, no login can succeed.

---

## 2. The top bar and what each item does

After login you land on the **Calendar** by default. The top
navigation bar holds every other area of the application:

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RASTATIME  │  Dashboard  Calendar  Library  Settings  Help │ user ▾│
  └─────────────────────────────────────────────────────────────────────┘
```

| Menu | What lives there |
|---|---|
| **Dashboard** | What is on air right now, what is coming up, source state (scheduler / line-in / master DJ / show DJ), and a manual override panel. See [Dashboard](./DASHBOARD.md). |
| **Calendar** | The schedule grid. Create / edit / delete shows. Drag-and-drop shows around. See [Calendar](./CALENDAR.md). |
| **Library** | All your tracks, smart blocks, playlists, webstreams, and line-ins. Search and filter. See [Library](./LIBRARY.md). |
| **Settings** | Streams, Local Machine (sound-card + import folder), Auto DJ, Show Templates, General Preferences, Manage Users, Localisation. Each is a separate sub-document in this manual. |
| **Help** | **Getting Started** (the three-step quick start), **User Manual** (this manual, readable in the browser in English, German, French and Spanish — since 2026-10-01), **Contribute to RASTATIME** (the GitHub project) and **What's New?** (the GitHub release notes). |
| **User dropdown** (top-right) | Logout, switch language, view your own profile, your API key (for scripts). |

> **Operator tip.** The Calendar is the centre of gravity. You
> can do almost everything from the Calendar's context menu —
> create a show, fill it from the library, attach a template,
> open it for editing. The other top-level menus are mostly for
> one-off configuration.

---

## 3. Roles — who you are decides what you see

Every user has exactly one **role**. The role is set on the
Manage Users page and is the only thing that controls what the
UI lets you do.

| Role | Can see / do |
|---|---|
| **Guest (G)** | Read-only Dashboard. No Calendar, no Library, no Settings. Used for monitoring dashboards or info screens at reception. |
| **DJ (H)** | Their own shows + own files only. Can fill their own shows, upload their own tracks. Cannot create shows. Cannot see other DJs' files. |
| **Program Manager (P)** | Full Calendar and Library access. Can create and edit shows for any DJ. Cannot change station-wide settings. |
| **Admin (A)** | Everything a Program Manager can do, plus station-wide settings (Streams, Local Machine, Auto DJ, Show Templates, Localisation). |
| **Super Admin (S)** | Everything. Plus the ability to create and demote other Admins. Reserved for the station owner / technical admin. |

> **Why it works this way.** Role-based ACL is enforced server-
> side in `configs/ACL.php`. Hiding menu items in the UI is
> only a convenience — the back-end re-checks every action
> against the user's role. A DJ cannot edit another DJ's show
> even by crafting the URL by hand. See ARCHITECTURE §11 for
> the full role matrix.

[`USERS_AND_ROLES`](./USERS_AND_ROLES.md) covers role assignment
and the resource-by-resource permission matrix.

---

## 4. The first ten minutes: from blank station to on-air track

A brand-new RASTATIME install has an empty library, an empty
calendar, and Icecast running but with no audio reaching it.
This section walks the shortest possible path to fix all three.

### 4.1 Confirm the output stream exists

Settings → **Streams**.

The default install ships with **Stream 1** configured to:

| Field | Default |
|---|---|
| Type | Icecast |
| Server | `localhost` |
| Port | `8000` |
| Mount | `/rastatime` |
| Format | MP3, 192 kbps, 44.1 kHz, stereo |

The **Connected** column should already show a green badge if
the playout service is running. If it shows red ("Disconnected"),
the playout has not started — verify with
`Get-Service RASTATIME-PLAYOUT` in PowerShell.

> **How it works under the hood.** The web UI does not push the
> stream itself — the **RASTATIME-PLAYOUT** Windows service does.
> It reads the stream config from `cc_pref` on startup and on
> every save, opens an Icecast source connection, and starts
> publishing silence (or the fallback content) immediately. The
> green / red badge is driven by the `/api/v2/streams` endpoint
> which checks the live `libvlc` source-output state.

To listen, open in another tab:
`http://<station-host>:8000/rastatime`. You should hear silence
or the fallback loop if one is configured. If you hear nothing
at all and the badge is green, the operator-machine output
device is the next thing to check — see
[Local Machine](./LOCAL_MACHINE.md).

### 4.2 Upload one track

Library → **Upload**.

Drag any MP3, FLAC, or WAV file onto the upload area. The
analyzer runs the file through ffprobe (metadata) and ffmpeg
(playability — decode the whole file to `null` to confirm it
plays end-to-end), then the row appears in the library list.

> **Operator tip.** If you have a folder of music to import, do
> not drag-and-drop them one at a time. Set the
> **Local Import Folder** under Settings → Local Machine to a
> directory on the server; anything dropped into that directory
> is auto-imported on the next analyzer poll (every 60 s by
> default). See [Local Machine](./LOCAL_MACHINE.md).

> **How it works under the hood.** Upload writes to a staging
> directory under `C:\rastatime\import\`, then queues an analyzer
> job. The analyzer parses metadata (ID3 / Vorbis tags) and
> verifies playability via `ffmpeg -v error -i <file> -f null -`;
> see ARCHITECTURE §23.14. On success the file is moved to the
> media library at `C:\rastatime\media\<owner>\<year>\<month>\`
> and a `cc_files` row is inserted. On hard failure (decode
> error) the upload is rejected with "File is unplayable". On
> soft failure (decoder warnings but full decode) the import
> succeeds with a yellow warning badge.

### 4.3 Create a show

Calendar → click any empty cell in the next hour → **New Show**.

Fill in:

| Field | Suggested value |
|---|---|
| **Name** | `Test` |
| **Start date / time** | Now + 2 minutes |
| **Duration** | 10 minutes |
| **Genre** | leave blank |
| **Hosts** | yourself |

Leave everything else at defaults. Click **Save**.

The show appears on the calendar as a coloured block.

> **How it works under the hood.** Saving the form writes one
> row to `cc_show` (the show definition) and at least one row
> to `cc_show_instances` (each occurrence). For a one-off show
> like this you get one of each. A repeating show creates the
> instances eagerly out to the configured horizon (~3 months by
> default).

### 4.4 Fill the show with the track

Calendar → click the show → **Schedule Tracks**.

The show-builder opens with the show on the left and the
library on the right. Drag your uploaded track from the library
onto the show. It appears as the first scheduled item.

Click **Save** at the top of the show-builder.

> **Operator tip.** You can also right-click an empty show on
> the calendar and pick **Apply Template** to fill it from a
> reusable [Show Template](./SHOW_TEMPLATES.md), or attach an
> [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md) so every
> instance fills itself.

### 4.5 Wait for the show to start

At the show's start time:

1. The Dashboard's **Now Playing** widget switches from
   "Fallback" (or "Silent") to the track's title.
2. The Icecast stream at `http://<station-host>:8000/rastatime`
   starts playing your track.
3. The Calendar's fill bar for the show turns from grey
   ("0 %") to coloured ("100 %" if the track filled the whole
   slot, less if it did not).

If any of those does not happen, the
[`CRASH_RECOVERY`](../operator/CRASH_RECOVERY.md) runbook covers
the diagnostic path.

---

## 5. Common first-day operations

You now know enough to do the day-to-day work. Here is where to
find each common task in the rest of the manual:

| I want to… | Go to |
|---|---|
| Upload a batch of tracks | [Library](./LIBRARY.md) |
| Plan tomorrow's schedule | [Calendar](./CALENDAR.md) |
| Make a recurring weekly show | [Calendar](./CALENDAR.md) → Recurring shows |
| Use the same show config every week | [Show Templates](./SHOW_TEMPLATES.md) |
| Have a show fill itself | [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) |
| Fill calendar gaps automatically | [Auto DJ](./AUTO_DJ.md) |
| Take the station live from a microphone | [Dashboard](./DASHBOARD.md) → Live Source |
| Add a guest's external Icecast stream as a webstream | [Webstreams](./WEBSTREAMS.md) |
| Add the studio mixer as a named line-in | [Line-In](./LINE_IN.md) |
| Record what was on air today | [Record-per-Show](./RECORD_PER_SHOW.md) |
| Archive the whole broadcast around the clock | [24/7 Recording](./RECORD_PER_HOUR.md) |
| Add a second output stream (e.g. low-bitrate mobile) | [Streams](./STREAMS.md) |
| Add a new DJ | [Users and Roles](./USERS_AND_ROLES.md) |
| Change the UI language | [Languages](./I18N.md) |
| Tour the Settings menu | [Settings](./SETTINGS.md) |

---

## 6. Three habits to avoid pain later

These are not optional. They will save you a long evening at
some point.

1. **Use Show Templates from day two.** If you find yourself
   typing the same name / hosts / colours twice, save it as a
   template. Hosts who learn this never look back.
   See [Show Templates](./SHOW_TEMPLATES.md).

2. **Set the Local Import Folder.** Drag-and-drop browser
   uploads are fine for one or two files, but a 200-track
   batch import will time out the browser and frustrate you.
   The Local Import Folder polls the directory on the server
   every 60 s and never times out.
   See [Local Machine](./LOCAL_MACHINE.md).

3. **Make a backup the day you go live.** RASTATIME ships a
   one-command backup script that captures the database, the
   uploaded media, and the config. Set it to run nightly on
   the same machine, and once a week to off-machine storage.
   See [`docs/operator/BACKUP.md`](../operator/BACKUP.md).

---

## Where to go next

* If you only have time for one more chapter today, read
  [Calendar](./CALENDAR.md) — the calendar is where most of
  your time will be spent.
* For the technical reader who wants to understand the system
  end-to-end before continuing, the
  [ARCHITECTURE](../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)
  document gives the full picture in one read.
* For an operator going live for the first time, also work
  through [`docs/operator/INSTALL.md`](../operator/INSTALL.md)
  §6 ("Smoke test") to confirm every service is healthy
  before announcing the station.
