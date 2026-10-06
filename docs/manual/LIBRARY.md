# Library

> **Where you are in the manual.** This is one of the
> **Content and library** chapters. For per-input-type detail
> see also [Webstreams](./WEBSTREAMS.md) and
> [Line-In](./LINE_IN.md), which are tracked as library items
> in their own right.

The **Library** is the inventory of every piece of audio
RASTATIME can put on air. It has five item types:

| Type | What it is | Where the rows live |
|---|---|---|
| **Track** | A single audio file (MP3, FLAC, OGG, WAV, AAC). | `cc_files` |
| **Smart Block** | A *query* — "pick N tracks where genre = pop and BPM > 100", evaluated at build time. | `cc_block` + `cc_blockcontents` (criteria) |
| **Playlist** | An ordered list of items: tracks, smart blocks, webstreams, or line-ins. | `cc_playlist` + `cc_playlistcontents` |
| **Webstream** | A URL pointing at another Icecast / Shoutcast / plain HTTP audio source. | `cc_webstream` |
| **Line-In** | A named live audio input on the operator's machine. | `rastatime_linein` |

The Library is what you drag from when filling a show.

---

## 1. The Library page

Library → opens the table view with one row per item.

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  Library                                            ▼  Upload   │
  ├─────────────────────────────────────────────────────────────────┤
  │  Filter:  [type ▾]  [creator ▾]  [genre ▾]  [length ▾]          │
  │  Search:  [_______________________________]                     │
  ├──┬──────────┬────────────────┬──────────┬──────────┬─────────┬──┤
  │  │ Type     │ Title          │ Creator  │ Length   │ Owner   │  │
  ├──┼──────────┼────────────────┼──────────┼──────────┼─────────┼──┤
  │ ◯│ Track    │ Song A         │ Artist 1 │ 03:42    │ admin   │  │
  │ ◯│ Track    │ Song B         │ Artist 2 │ 04:15    │ admin   │  │
  │ ◯│ Smart B. │ Hot pop        │ —        │ ~30:00   │ admin   │  │
  │ ◯│ Playlist │ Morning Show   │ —        │ 60:00    │ host1   │  │
  │ ◯│ Webstream│ BBC Radio 1    │ —        │ 60:00    │ admin   │  │
  │ ◯│ Line-In  │ Studio Mixer   │ —        │ ∞        │ admin   │  │
  └──┴──────────┴────────────────┴──────────┴──────────┴─────────┴──┘
```

### Filter chips

The chips above the table narrow the visible rows. They combine
with **AND**: setting *type = Track* and *genre = pop* shows
only pop tracks. Clear any chip with its **×**.

| Chip | What it filters by |
|---|---|
| **Type** | Track / Smart Block / Playlist / Webstream / Line-In. The five-coloured chip set in the column header mirrors this. |
| **Creator** | The track's metadata creator (artist), not the upload owner. |
| **Genre** | Metadata genre tag. |
| **Length** | Coarse buckets (< 30 s, 30 s – 2 min, 2 – 10 min, > 10 min, ∞). |
| **Owner** | The RASTATIME user who imported the item. DJs are restricted to their own items; Admins see everything. |

> **Operator tip.** The chips also colour the row badges. After
> a few weeks of using the same set, you stop reading the *Type*
> column and just read the colours: blue = track, green = line-in,
> yellow = block, orange = stream, purple = playlist.

> **Remaining time and crossfades (since 2026-10-06).** Music rows
> overlap by their crossfade (house value 3 s, or the track type's;
> jingles 0), so a show's remaining time is the *laid-out* time: from
> the end of the last row to the show's end — the number the show
> builder's footer shows. A "time remaining" smart block is picked
> against that time, between its real neighbours, so the last row ends
> within a second or so of the show's end (the block's solver is
> randomised; the pool decides what is possible). A block limited by
> *Duration in time* still counts the sum of its tracks: 12 minutes of
> four music tracks air about 9 s shorter. A jingle placed between two
> music tracks costs its own length plus the 3 s overlap it breaks.

### Free-text search

The **Search** box runs across **title, creator, album, genre,
filename** for tracks; **name** for blocks / playlists /
webstreams / line-ins. It uses a substring match — typing
`bowie` matches "David Bowie", "BOWIE", and "bowie-heroes.mp3".

> **How it works under the hood.** Search is server-side via
> `LibraryController::contentsFeedAction`. The DataTable widget
> sends the search term + the current chip state as URL
> parameters; the controller assembles a PostgreSQL `ILIKE`
> query against the relevant columns. Pagination is server-
> side too, so a library of 100 000 tracks does not load 100 000
> rows into the browser.

### Sort columns

Click any column header to sort ascending; click again for
descending. The default sort is **title, ascending**.

### Table layout

Drag a column by its header to move it; the **Columns** button
(list icon) above the table shows or hides columns, and the
**Show** selector below it sets the rows per page. RASTATIME
remembers this layout — column order, visible columns, rows per
page and sort — **per user on the server**, so it follows you to
any browser and computer. The track table on the dashboard and
the one in the calendar's **Schedule Tracks** dialog each keep a
layout of their own (the dialog has no *Actions* column); the
*Scheduled Shows* table next to them shares one layout between
both places. Searches and the current page are not remembered —
the table always opens on page 1. While you scroll through the
rows, the search line, the column headers and the pager stay in
view.

---

## 2. Tracks

### Importing tracks

Three ways:

#### 2.1 Browser upload (one-off)

Library → **Upload** → drag files onto the upload area or
click to pick.

| Field | Notes |
|---|---|
| **File** | Any of: MP3, FLAC, OGG, WAV, AAC, M4A. |
| **Owner** | Defaults to you. Admins can override. |

The upload runs the analyzer (metadata + playability check) and
adds the row to the library. Large files may take a few seconds
to appear because the playability decode runs the full file end-
to-end.

#### 2.2 Local Import Folder (batch)

Configure Settings → **Local Machine** → **Local Import Folder**
once. Then drop files into that directory on the server; they
appear in the library on the next analyzer poll (default
every 60 s). Subfolders are scanned recursively. See
[Local Machine](./LOCAL_MACHINE.md).

> **Operator tip.** Use the Local Import Folder for any batch
> over a dozen files. The browser uploader keeps the request
> open until the analyzer finishes; a 200-file batch can hold
> the request open for many minutes and the operator gives up.

#### 2.3 Podcast subscription (recurring)

Settings → **Podcasts** → **Subscribe**. Paste an RSS feed URL,
optionally a default track type, an auto-expiry policy
(delete episodes older than N days). New episodes are
downloaded by the worker job runner and imported as tracks
exactly like a manual upload.

> **Episode files (since 2026-09-17)** land in one folder per
> podcast inside the media library: `imported/<podcast name>/`.
> Renaming a podcast starts a new folder for future episodes;
> existing files stay where they are.
>
> **How it works under the hood.** Podcast fetching used to rely
> on Celery; on RASTATIME (Windows) the download runs
> synchronously in the API (triggered from the web UI or the
> feed check) and writes the file plus its library row directly.

### Editing track metadata

Click a track row → **Edit Metadata** in the row's action menu.

| Field | Where it ends up |
|---|---|
| **Title** | `cc_files.track_title` |
| **Creator (Artist)** | `cc_files.artist_name` |
| **Album** | `cc_files.album_title` |
| **Genre** | `cc_files.genre` |
| **Year** | `cc_files.year` |
| **BPM** | `cc_files.bpm` |
| **Track type** | `cc_files.track_type` — used by smart-block filters |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — trim the start / end without re-encoding. Since 2026-09-30 the values are kept inside the file: a cue out past the file length is capped at the length, a cue in below zero becomes zero. A change is copied into the rows of the upcoming shows that schedule the track (rows that have already started are left alone), and those shows are laid out again - no refilling needed. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — used by the playout engine for level normalisation |
| **Crossover** | How this track meets its neighbours (since 2026-09-29 one three-way field; the two exceptions exclude each other). **As the track type** (default): the track overlaps and fades as its track type says - Settings → Track Types → *Crossfade Duration* - or, without a value there, as the Default Track Crossfade Duration; since 2026-09-30 it also inherits the type's *No Fade during Crossover* preset. **No Fade during Crossover** (`cc_files.no_fade_crossfade`): the overlap stays, but this track keeps its full level while the other one fades; at an overbooked show boundary a flagged outgoing track is cut instead of faded. **Exclude from Crossover** (`cc_files.exclude_crossfade`): this track never overlaps a neighbour - it starts at the end of the previous track and the next one starts at its end. Changing to or from *Exclude* re-lays the rows of the upcoming shows that schedule the track. |

> **Operator tip.** Set **Cue In** on radio promos / stings that
> have a few seconds of silence at the head. The cue point is
> a non-destructive trim — the file on disk is unchanged, but
> playback starts at the cue.
>
> Since jingles are laid out without an overlap (Settings → Track
> Types → *Crossfade Duration* = 0), a silent tail is heard as a
> pause. Select the jingles in the library and use **Cue Points**
> in the toolbar (section 6) to trim all of them at once.

### Deleting a track

Row → **Delete**. The track is removed from the library *and*
from any playlist it was a part of. If the track is currently
scheduled in any upcoming show, you get a warning and can choose
to abort or proceed (the schedule rows are removed too).

> **How it works under the hood.** Delete removes the
> `cc_files` row and any `cc_playlistcontents` / `cc_schedule`
> rows that reference it (CASCADE). The file on disk is moved
> to `C:\rastatime\media\.trash\` rather than being unlinked,
> so an operator who deleted by accident can restore for 7
> days. See [`docs/operator/BACKUP.md`](../operator/BACKUP.md)
> for the trash-cleanup cron.

---

## 3. Smart Blocks

A **smart block** is a query. When the block is scheduled
inside a show, the query is evaluated at build time and expanded
into a concrete set of tracks. Smart blocks are how you build
shows that say "play 30 minutes of upbeat pop tracks from after
2010" without manually picking each track.

### Creating a smart block

Library → **+ New** → **Smart Block**.

| Field | Meaning |
|---|---|
| **Name** | Visible in the library and on the calendar. |
| **Type** | **Static** — picks once at creation time; the set never changes. **Dynamic** — re-picks every time the block is scheduled. |
| **Criteria** | Add rows: *artist contains "Bowie"*, *bpm between 100 and 130*, *genre is pop*, etc. Each row AND-combines with the others; an OR group can be created by adding a nested group. |
| **Limit to** | One of: **Number of tracks** (e.g. 10), **Duration in time** (e.g. 30:00), **Time remaining in show** (let the smart block fill exactly to the show's end). |
| **Sort** | Random / newest first / by artist / by play count / etc. |

> **Operator tip.** The **"Time remaining in show"** limit is
> the most useful for autoloading playlists. Combined with an
> intro + outro playlist, you can build a one-hour show by
> stamping a 30 s intro + a `*` smart block + a 60 s outro, and
> the auto-build will sandwich the right number of tracks
> between them.

### Why a smart block can return fewer tracks than you asked for

Smart blocks respect the operator's **library scope**:

- The owning DJ sees only their own tracks.
- A Program Manager sees the whole library.

If you set "Limit to 10 tracks" but only 4 tracks in the
library match the criteria, you get 4. The block does not
error.

> **How it works under the hood.** Criteria are stored in
> `cc_blockcriteria`. At build time, `BlockExpander.expand()`
> assembles a PostgreSQL `SELECT … WHERE … LIMIT …` over
> `cc_files`. Time-remaining limits convert to a duration cap
> via the show instance's `getSecondsRemaining()` — since
> 2026-10-06 the laid-out free time (`time_filled` = start to the end
> of the last row); the pick is `Scheduler::pickRemainingBlock()`. See
> ARCHITECTURE §23.19 for the outro-reserve interaction with
> time-remaining smart blocks.

### Pool-restriction toggles (Advanced section)

The **Advanced options** drawer at the bottom of the Smart
Block dialog hosts three pool-restriction toggles that
narrow the candidate set *before* the sort + limit run:

| Toggle | What it restricts the pool to |
|---|---|
| **Allow only tracks not played yet** | Tracks where `cc_files.lptime` is `NULL` (the playout has never logged them). Useful for discovery / new-content rotation blocks. |
| **Exclude tracks played lately** | Tracks where `lptime` is `NULL` *or* older than the configured hours-back window (1..8760 h, default 24). Use this when you want to avoid recent re-rotation without forbidding every prior play. Companion input "Exclude tracks played in the last hours" appears when the toggle is on. |
| **Exclude artists played lately** | Tracks whose `artist_name` is NULL / empty *or* has not been heard via any other track in the configured hours-back window (1..8760 h, default 24). Use this when you want to avoid two tracks by the same artist clustering together — independent of which specific track was played. Companion input "Exclude tracks played in the last hours" appears when the toggle is on. |
| **Allow only tracks with expiry date** | Tracks where `cc_files.expires_at IS NOT NULL`. Useful for blocks that should only draw from short-lived / perishable content (dated news segments, trailers). |

All four compose AND-wise and combine with every criterion
in the main Criteria section.

> **Operator tip.** The "Exclude tracks played lately" toggle
> is the right answer to "play 30 min of pop, but nothing
> from the last 4 hours." Pair it with `Sort: Random` for a
> fresh-rotation auto-build that never sounds repetitive
> within the configured window. Never-played tracks are
> *included* by the filter — a track that has never aired
> obviously cannot have aired "lately".
>
> The **"Exclude artists played lately"** companion is the
> answer to "don't follow a Beatles track with another
> Beatles track for at least 6 hours, even if I have 50
> Beatles tracks in the pool". The two filters compose:
> activate both to get "no recent track AND no recent
> artist" at the same time.

> **How it works under the hood.** `Exclude played lately`
> adds a single `WHERE cc_files.lptime IS NULL OR cc_files
> .lptime < NOW() - INTERVAL 'N hours'` clause to the Propel
> query. The hours value is persisted in
> `cc_block_criteria` (criteria = `exclude_played_lately_hours`)
> alongside the master flag (criteria = `exclude_played_lately`).
> `Exclude artists played lately` adds a `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts > NOW() -
> INTERVAL 'N hours')` — `NOT EXISTS` short-circuits on the
> first hit so cost stays bounded even with a large history
> table. Persisted as a second criteria pair
> (`exclude_artists_played_lately` + `..._hours`).
> No schema change for either filter — backwards-compatible
> with smart blocks created before the respective feature
> (missing rows = disabled). See ARCHITECTURE §23.21.
>
> **Within-block spread (2026-05-25).** The SQL filter above
> keeps the candidate pool free of artists / tracks that ran
> in the last N h *outside* the block.  But the block itself
> can still hold two Beatles tracks back-to-back — the SQL
> only looks at history, not at what the block is about to
> play.  A second pass runs after the track-list build in
> `Block::applyWithinBlockSpread()`: for each slot of the
> originally-selected list, the original track is tried first;
> if its artist (or file id, depending on which filter is
> active) sits inside the elapsed-time window of the tracks
> already placed in the block, the engine pulls a non-
> conflicting replacement from the broader SQL-filtered pool
> (up to 500 tracks) instead.  Block length stays the same;
> only the track choice shifts.  If no non-conflicting
> replacement is left in the pool, the original is placed
> anyway and a `Logging::warn` entry lands in `legacy.log`
> so the operator can see when the pool was too narrow for
> the configured spread.

### Editing a smart block

Click the block → **Edit**. Changing criteria does *not*
retroactively change shows that were already built — only
future evaluations.

---

## 4. Playlists

A **playlist** is an ordered list of items, where each item is
a track, a smart block, a webstream, or a line-in. Playlists
are the building blocks of show content.

### Creating a playlist

Library → **+ New** → **Playlist**.

The playlist editor opens with the playlist on the left and the
library on the right. Drag library items onto the playlist;
re-order with drag-and-drop. Set crossfades and cue-points per
item if needed.

| Item type behaviour |  |
|---|---|
| **Track** | Plays as configured (cue in / out, fade in / out). |
| **Smart Block** | Expands at build time, not at playlist edit time. |
| **Webstream** | Plays for the playlist row's configured duration (default 60 min, can be overridden). See [Webstreams](./WEBSTREAMS.md). |
| **Line-In** | Plays for the playlist row's configured duration. See [Line-In](./LINE_IN.md). |

### Default Length

Each playlist has a **Default Length** that shows up as the
playlist's nominal duration in the library. For a track-only
playlist this is the sum of the track durations. For a playlist
containing smart blocks / webstreams / line-ins, the default
length is what *would* play if every variable item ran for its
configured duration.

### Using a playlist in a show

Two paths:

1. **One-off**: drag the playlist onto an empty show in the
   show-builder. The playlist's items are *flattened* into the
   schedule at the drag point. The original playlist is not
   linked to the show — editing the playlist later does not
   affect the schedule.

2. **Autoloading**: attach the playlist to the show definition
   on the show-edit form's **Autoloading Playlist** section.
   Every future instance of the show will have the playlist's
   items built into its schedule automatically. Editing the
   playlist *does* affect future builds. See
   [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md).

> **Operator tip.** A single playlist can serve double duty:
> drag it onto an ad-hoc show and also attach it as the
> autoloading playlist for a recurring show. The two uses are
> independent.

---

## 5. Webstreams and Line-Ins as library items

Both [Webstreams](./WEBSTREAMS.md) and [Line-Ins](./LINE_IN.md)
appear in the library and behave like tracks when scheduled:
drag them onto a show or into a playlist exactly the same way.

Their per-feature chapters cover the specifics (URL format,
authentication, device probing, etc.). The Library entry-point
is the same as for any other item.

---

## 6. Bulk actions

Tick the checkbox at the start of each row, then use the
toolbar that appears at the bottom of the table:

| Action | Effect |
|---|---|
| **Add to Playlist** | Append the selected rows to an existing playlist of your choice. |
| **Delete** | Delete the selected rows. Same confirm-on-scheduled-use semantics as single-row delete. |
| **Edit Metadata** | Open a batch-edit dialog. Only applies to tracks. |
| **Move to Owner** | Reassign ownership (Admin / Super Admin only). Used when a DJ leaves and their files should pass to the station account. |
| **Cue Points** | Detect the cue points of the selected tracks from their audio (the same silence detection the analyzer runs at import: quieter than −60 dB for at least 0.3 s at the head or the tail) and store them. Upcoming shows that schedule the tracks follow the new values and are laid out again. Tracks longer than 15 minutes are skipped - the action is meant for jingles and other short elements. Since 2026-09-30. |

---

## 7. Frequently-asked

### "I uploaded a track and it never appeared."

Check the upload status badge:

- **Yellow (Warning)**: the file imported but the playability
  check produced warnings (typically a poorly-encoded MP3 with
  trailing-frame issues). The file *will* play; you can ignore
  the warning.
- **Red (Failed)**: the file is unplayable or the metadata
  parser crashed. The row is suppressed from the library list
  (filter chip **Failed imports** in the upload status page
  shows them).
- **No badge but no row** either: the analyzer service is not
  running. Check `Get-Service RASTATIME-ANALYZER`.

### "Why is my smart block returning the same tracks every time?"

You probably picked **Static** instead of **Dynamic**. Edit the
block and switch the type; the next build will re-query.

### "Can I import a folder structure preserving subfolder names?"

The Local Import Folder preserves subfolder names as the
imported tracks' **album** field if no ID3 album tag is set.
This is the most common operator pattern for a long-tail music
archive.

### "What's the maximum file size?"

The browser uploader is limited by Apache's
`LimitRequestBody` — default 100 MB. The Local Import Folder
has no practical limit (files are read off disk, not POSTed).

---

## Where to go next

* [Calendar](./CALENDAR.md) — how to put library items on air.
* [Show Templates](./SHOW_TEMPLATES.md) — reusing show settings.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — letting
  shows fill themselves from a playlist.
* [Webstreams](./WEBSTREAMS.md) and [Line-In](./LINE_IN.md) for
  the per-type detail on the two newer item types.
