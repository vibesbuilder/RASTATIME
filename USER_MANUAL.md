# RASTATIME — User Manual

> 🌐 **Languages:** **English** ·
> [Deutsch](./docs/manual/de/USER_MANUAL.md) ·
> [Français](./docs/manual/fr/USER_MANUAL.md) ·
> [Español](./docs/manual/es/USER_MANUAL.md)

> **About this manual.** RASTATIME is a Windows-first fork of LibreTime
> for operating a community / small commercial radio station. This
> document is the operator-facing companion to the technical
> [ARCHITECTURE](./RASTATIME_ARCHITECTURE_DRAFT_v0.1.md) and
> [INSTALL](./docs/operator/INSTALL.md) guides. It covers **how to
> run a station on RASTATIME day-to-day**, not how to install or
> debug the server.

---

## Audience and conventions

This manual is written for two readers in parallel:

* **Operators** — Station managers, programme managers, hosts, DJs.
  You log into the web UI in the morning, schedule the day, push
  "Save", and move on. Everything you need to do this lives in the
  main body of each chapter.

* **Technicians** — Admins, engineers, integrators. You also need
  to know what is happening underneath: which database column the
  UI writes to, which API endpoint the button fires, which service
  needs to be alive for the feature to work. Look for the boxed
  **How it works under the hood** sections; they cover the
  internals without bloating the operator flow.

### Visual conventions used in this manual

| Mark | Meaning |
|---|---|
| **Bold** | Button label, menu item, or field name as it appears in the UI. |
| `code` | Literal value the operator types or that the system displays verbatim — a filename, a configuration key, a stream URL. |
| > Quote block | Side note, caveat, or operator tip. Safe to skim on a first read. |
| **How it works under the hood** | Boxed technical aside — database table, API endpoint, scheduler decision. Operators may skip. |
| **Why it works this way** | Boxed design-decision aside — points back to the corresponding ARCHITECTURE section number when relevant. |

### Default URLs and paths assumed throughout

Unless your installation overrides them in `config/rastatime.conf`:

| What | Default |
|---|---|
| Web UI (Apache front-end) | `http://<station-host>/` |
| Django REST API | `http://localhost:8765/api/v2/` |
| Icecast streaming server | `http://localhost:8000/` |
| Install root | `C:\rastatime\` |
| Log directory | `C:\rastatime\logs\` |
| Media library on disk | `C:\rastatime\media\` |
| Operator-local audio cache | `C:\rastatime\scheduler\` |
| Configuration file | `C:\rastatime\config\rastatime.conf` |

If your station uses different paths, substitute throughout.

---

## How RASTATIME is organised

RASTATIME is **calendar-driven**. Everything that goes on air is
either:

1. A **show** placed on the calendar at a specific time, or
2. The **fallback** that fills airtime when no show is current.

A show is a slot on the calendar; the slot is *filled* with
content (tracks, smart blocks, webstreams, line-ins) either
manually in the show-builder, automatically via an autoloading
playlist, or both. When the slot starts, the playout engine
plays the filled content. When the slot ends, the engine moves
on to whatever is next.

The **dashboard** in the top-right corner shows what is
currently on air, what is coming up, and which output streams
are healthy.

```
   ┌──────────────────────────┐         ┌────────────────────────────────┐
   │      OPERATOR (you)      │         │     CALENDAR (the schedule)    │
   │                          │ creates │                                │
   │  • plans the schedule    │────────▶│  • shows pinned at times       │
   │  • fills shows           │         │  • each show is one row in     │
   │  • manages the library   │         │    cc_show_instances           │
   └──────────────────────────┘         └─────────────────┬──────────────┘
              ▲                                           │
              │ sees in dashboard                         │ scheduler dispatches
              │                                           ▼
   ┌──────────┴───────────────┐         ┌────────────────────────────────┐
   │   NOW PLAYING (output)   │◀────────│   PLAYOUT ENGINE (VLC core)    │
   │                          │  feeds  │                                │
   │  • Icecast :8000         │         │  • plays files / webstreams    │
   │  • optional record file  │         │  • switches to live source     │
   │  • optional studio out   │         │  • emits start/end events      │
   └──────────────────────────┘         └────────────────────────────────┘
```

Everything in this manual hangs off one of those four boxes.

---

## The manual at a glance

Each link below opens a focused sub-document in
[`docs/manual/`](./docs/manual/). Read them in any order — the
master document above is the only thing they all assume.

### Day-to-day broadcast operation

| Chapter | What's in it |
|---|---|
| [Getting Started](./docs/manual/GETTING_STARTED.md) | First login, dashboard tour, basic concepts, role overview. Read this first if you have never used RASTATIME. |
| [Dashboard](./docs/manual/DASHBOARD.md) | Now-Playing widget, source state, manual override, taking the station live from a microphone. |
| [Calendar](./docs/manual/CALENDAR.md) | Creating shows, editing, drag-and-drop, recurring shows, repeats, hosts. |
| [Show Templates](./docs/manual/SHOW_TEMPLATES.md) | Reusing show settings without re-typing them every week. |
| [Archiving](./docs/manual/ARCHIVING.md) | Archiving episodes on cba.media: producers and CBA accounts (Settings → Archiving), the archiving defaults of a show, per-episode title, teaser and image, "Archive Online" from the calendar, the people involved per own production and the Archive Status page. |
| [Import / Export](./docs/manual/IMPORT_EXPORT.md) | Exporting users, shows, playlists, smart blocks, webstreams and podcast subscriptions as CSV/JSON, keeping them in a spreadsheet and importing them again with a preview. |
| [Delayed Show Start](./docs/manual/DELAYED_START.md) | Letting an opted-in show start late when the show before it overran, instead of trimming that show. The delay ripples across consecutive opted-in shows up to the first fixed-time anchor. |

### Content and library

| Chapter | What's in it |
|---|---|
| [Library](./docs/manual/LIBRARY.md) | Tracks, smart blocks, playlists. Searching, importing, organising. |
| [Webstreams](./docs/manual/WEBSTREAMS.md) | Including the seconds-precise default length added in 2026-05-19. |
| [Line-In](./docs/manual/LINE_IN.md) | The combined Library + Playlists view of named live inputs. |

### Automation

| Chapter | What's in it |
|---|---|
| [Autoloading Playlists](./docs/manual/AUTOLOADING_PLAYLISTS.md) | Letting a playlist build itself for every episode of a show, including outro-reserve handling. |
| [Auto DJ](./docs/manual/AUTO_DJ.md) | The background filler that creates shows in calendar gaps and tops up incomplete shows. |
| [Song Requests](./docs/manual/SONG_REQUESTS.md) | Letting listeners request tracks from a public widget that air automatically inside a request show. |
| [Record-per-Show](./docs/manual/RECORD_PER_SHOW.md) | Capturing the full on-air output of a show to a file. |

### Output and infrastructure

| Chapter | What's in it |
|---|---|
| [Streams](./docs/manual/STREAMS.md) | Configuring up to four output streams, monitoring listener counts, troubleshooting. |
| [Analytics](./docs/manual/ANALYTICS.md) | Playout History (what actually aired, exportable log sheets), History Templates, Listener Stats (audience per stream and per show over time), People Involved and Programme Minutes of the own productions (yearly reporting), Archive Status. |
| [Local Machine](./docs/manual/LOCAL_MACHINE.md) | Sound-card output, line-in input, import format (lossless to MP3), local import drop-folder. |
| [Backup](./docs/manual/BACKUP.md) | One-click backups of database + configuration into a chosen folder; downloading them; the documented restore path. |
| [Public Embed Widgets](./docs/manual/WIDGETS.md) | Drop-in widgets for your station's public website (Now Playing — Show / Track, Weekly Program, Player). |
| [API](./docs/manual/API.md) | The public read endpoints (programme, now playing, history), the Public RASTATIME API switch the widgets depend on, API v2 with Swagger after login, and why the single API key never leaves the station. |

### Administration

| Chapter | What's in it |
|---|---|
| [Users and Roles](./docs/manual/USERS_AND_ROLES.md) | Admin, Program Manager, DJ, Guest — what each role can do. |
| [Settings](./docs/manual/SETTINGS.md) | Tour of every page under the Settings menu. |
| [Languages (i18n)](./docs/manual/I18N.md) | Switching the UI language; adding a translation. |

---

## When something breaks

This manual covers the **normal happy path**. When something does
not behave the way the manual describes, the recovery procedures
live elsewhere:

* [`docs/operator/DEVICE_MISSING.md`](./docs/operator/DEVICE_MISSING.md)
  — A configured sound-card or line-in is no longer plugged in.
* [`docs/operator/LINE_IN_BROKEN.md`](./docs/operator/LINE_IN_BROKEN.md)
  — Line-in present but produces silence or noise.
* [`docs/operator/CRASH_RECOVERY.md`](./docs/operator/CRASH_RECOVERY.md)
  — A service has crashed; restart order; how to confirm recovery.
* [`docs/operator/RESTART_ORDER.md`](./docs/operator/RESTART_ORDER.md)
  — Cold-start the whole stack in the right order.
* [`docs/operator/BACKUP.md`](./docs/operator/BACKUP.md)
  — Take, verify, and restore a backup.
* [`docs/operator/UPGRADE.md`](./docs/operator/UPGRADE.md)
  — Upgrade to a new RASTATIME release.

These runbooks are written for the same audience as this manual.
If you need to call an engineer at 03:00, the runbooks are what
they will use.

---

## Where to go next

* If you have **just installed** RASTATIME and want to put a
  station on air for the first time, start with
  [Getting Started](./docs/manual/GETTING_STARTED.md), then
  [Calendar](./docs/manual/CALENDAR.md), then
  [Streams](./docs/manual/STREAMS.md).

* If you are **migrating from LibreTime / Airtime**, the
  differences worth knowing first are:
  [Record-per-Show](./docs/manual/RECORD_PER_SHOW.md) (now
  captures the whole on-air output, not just the line-in),
  [Auto DJ](./docs/manual/AUTO_DJ.md) (new in RASTATIME), and
  [Local Machine](./docs/manual/LOCAL_MACHINE.md) (replaces the
  old "Soundcard" page and adds the import-folder feature).

* If you need to **install RASTATIME** from scratch,
  this manual is not the right document — see
  [`docs/operator/INSTALL.md`](./docs/operator/INSTALL.md).

* If you need to **understand why** a feature was designed the
  way it is, every section here cross-references the
  corresponding chapter number in
  [ARCHITECTURE](./RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).

---

## Glossary

| Term | Meaning |
|---|---|
| **Show** | A slot on the calendar with a start, end, name, and (usually) some scheduled content. Persisted in `cc_show` + `cc_show_instances`. |
| **Episode** | One concrete occurrence of a show (internally a *show instance*). A daily show is one `cc_show` row + many `cc_show_instances` rows. |
| **Schedule item** | One row inside an episode's playlist — typically a file, but also a smart block, webstream, or line-in. Persisted in `cc_schedule`. |
| **Playlist** | A reusable ordered list of items. Persisted in `cc_playlist` + `cc_playlistcontents`. |
| **Smart block** | A query inside a playlist that expands into a set of tracks at build time, optionally limited to "time remaining in the show". Persisted in `cc_block`. |
| **Webstream** | A URL pointing at another Icecast / Shoutcast / HTTP MP3/AAC source. Persisted in `cc_webstream`. |
| **Line-In** | A named live audio input on the operator's machine (a microphone, a mixer, an external CD player). Persisted in `rastatime_linein`. |
| **Autoloading playlist** | A playlist attached to a *show definition* so every episode of the show gets the playlist's contents built into its schedule automatically. |
| **Auto DJ** | A background process that creates shows in calendar gaps and tops up incomplete shows. Distinct from autoloading playlists. |
| **Delayed start** | A per-show opt-in (`cc_show.allow_delayed_start`) that lets a show begin later than its calendar slot when the preceding show overran, keeping its own end fixed. A background task applies it a few minutes before air. |
| **Song request** | A listener-submitted track wish, collected by a public widget and aired automatically by a request show (an autoloading-playlist show with a *Use requests* smart block). Persisted in `rastatime_song_request`. |
| **Output stream** | One of up to four Icecast mountpoints the playout broadcasts to. Configured under Settings → Streams. |
| **Source switcher** | The internal mechanism that decides which audio source (scheduler, line-in, master DJ, show DJ) is currently on air. |
| **Fallback queue** | A configured loop that plays when no show is scheduled and Auto DJ is disabled. |
| **Local Import Folder** | A directory on the operator's machine that the analyzer watches for new files; anything dropped here is auto-imported into the library. |

---

*This document is version-controlled in the RASTATIME repository.
See the [CHANGELOG](./CHANGELOG.md) for what changed in the
manual itself; see the per-chapter sub-documents for what changed
in each feature.*
