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
| **Track** | A single audio file (MP3, M4A, OGG, Opus, ...; WAV and FLAC are converted to MP3 on import by default). | `cc_files` |
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
> *Duration in time* is picked the same way (operator decision
> 2026-10-06): 12 minutes are 12 minutes **on air**, not the sum of the
> tracks, so a station ID after three such blocks sits at 12:00, 24:xx
> and 36:xx of the hour. A jingle placed between two music tracks costs
> its own length plus the 3 s overlap it breaks.

### Free-text search

The **Search** box runs across **title, creator, album, genre,
filename** for tracks; **name** for blocks / playlists /
webstreams / line-ins. It uses a substring match — typing
`bowie` matches "David Bowie", "BOWIE", and "bowie-heroes.mp3".

**Active-filter indicator (since 2026-10-09).** While search text or
any field of the advanced search is set, the search box gets an
accent-coloured border and shows, at its right end, how many items of
the selected kind match ("13 of 11,108 tracks", "0 of 32 smart
blocks"; since 2026-10-18 the count names the kind - tracks,
playlists, smart blocks, webstreams, podcasts, line inputs). The **×**
next to that count clears the search text and every advanced-search
field in one go.

**Podcasts (since 2026-10-21).** The podcast list has the same search
box: it matches the podcast **title** and **creator**, case-insensitive,
and shows "X of N podcasts" and the **×** the same way.  The
advanced-search caret is hidden there - it belongs to the other kinds.

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
any browser and computer. Since 2026-10-24 the **visible columns
are kept per media type**: Tracks, Playlists, Smart Blocks,
Webstreams and Line-Ins each remember their own set, and the
**Columns** button always edits the set of the tab you are on. A
tab you have never adjusted starts with a sensible default
(tracks: cover, title, creator, type, genre, length, uploaded;
playlists and smart blocks: title, description, length, creator,
last modified; webstreams: title, description, website, length,
creator, last modified; line-ins: title, description, length,
last modified). The track table on the dashboard and
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
| **File** | Any of: MP3, M4A, MP4, AAC, OGG, OGA, Opus, FLAC, WAV, MP2, MP1, AU - since 2026-10-14 the same list the Local Import Folder and the FTP import take. Lossless files are converted to MP3 on import by default (see *File formats on import* below). |
| **Owner** | Defaults to you. Admins can override. |

The upload runs the analyzer (metadata + playability check) and
adds the row to the library. Large files may take a few seconds
to appear because the playability decode runs the full file end-
to-end.

> **Where the file ends up (since 2026-10-24).**  The analyzer files
> every track under `imported/<artist>/<album>/` inside the media
> library (artist and album as tagged; without an album tag just
> `imported/<artist>/`).  A file **without an artist tag** goes to
> `imported/tagless/` - before 2026-10-24 such files sat directly in
> `imported/`.  The folder is only the storage place; the library
> shows the track by its tags either way, so tag the file first if
> you want it filed under its artist.
>
> **Covers.**  An embedded cover is stored as five JPG sizes
> (32 to 512 px) under `imported/artwork/`; nothing else is written
> for it since 2026-10-24.  The small cover thumbnails in the
> library and the editor are built from those JPGs when the page
> asks for them.

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

### File formats on import (since 2026-10-14)

Whichever way a track arrives - upload, Local Import Folder, FTP
import or bulk import - the analyzer looks at the audio inside the
file (not at its extension) before it files it:

- **MP3, MP2, MP1, AAC in M4A / MP4, OGG Vorbis and Opus** are
  imported as they are and never re-encoded.
- **Raw AAC (`.aac`)** is always repacked into an `.m4a` without
  re-encoding: a raw AAC file has no index, so its length can only
  be estimated, and it cannot carry tags.
- **Lossless audio** - WAV, FLAC, AU, Apple Lossless in M4A - is
  converted to **MP3 at 320 kbps** while Settings → **Local
  Machine** → **Import Format** is on (the default).  The lossless
  original is not kept; tags, the Expiry and Enable dates, the
  Country and an embedded cover are carried over.  If a conversion fails, the original is imported
  unchanged.  Details: [Local Machine](./LOCAL_MACHINE.md), section 5.
- **Tags are read from every format.**  Besides ID3 in MP3 files, the
  analyzer reads the tags inside WAV files (ID3 chunk and RIFF INFO),
  the comments of FLAC, OGG and Opus files and the fields of M4A
  files, including a description / comment, the dates and the
  country (next section).  Before 2026-10-14 the tags inside WAV files were
  not read, and a raw `.aac` with an ID3 tag failed to import.

Podcast episodes are not part of this: they are downloaded straight
into the library (section 2.3) and keep their format. Since
2026-10-24 every downloaded episode is still **measured for
loudness** (EBU R128) right after the download, so the playout
applies its real per-track gain instead of an approximation.
Episodes downloaded before that date are caught up with
**Settings → Streams → Measure loudness**, which only measures
files that have no values yet.

### Dates and country from the tags (since 2026-11-08)

Three fields of the track editor are filled from the file's own tags
on import - ID3 `TXXX` frames in MP3 files, and the same names as FLAC,
OGG and Opus comments, M4A freeform fields or in the ID3 chunk of a WAV
file:

| Tag name | Field | Format |
|---|---|---|
| `Expiry` or `Expiry Date` | **Expiry Date** | `2026-11-08` or `20261108` |
| `Enable Date` or `Enabled From` | **Enabled From** | `2026-11-08` or `20261108` |
| `Country` | **Country** | free text as in the tag, e.g. `Austria` |

Upper and lower case, blanks, underscores and hyphens in the tag name
do not matter (`EXPIRY_DATE` is `Expiry Date`).  A date in any other
format is ignored; the analyzer log names the file.  An expiry date
that has been reached or an enable date still ahead disables the track
right away.  The country is only filled when the track has none yet.

**Re-read Tags** takes the country from the file too (a file without
the tag clears it), but never the two dates: a date set in RASTATIME
stays.  Tracks imported before 2026-11-08 get their country from their
tags once with `manage.py backfill_country --yes` on the station
machine; it fills only empty countries, and without `--yes` it only
counts.

### Track type from the Media Type tag (since 2026-11-09)

A file can bring its own track type: when its **Media Type** tag names
a track type RASTATIME knows, the track gets exactly that type on
import.

- **Where the tag sits:** the standard ID3 frame `TMED` (Media Type)
  in MP3 files; `MEDIATYPE` - or `MEDIA`, as MusicBrainz Picard writes
  it - in FLAC, OGG and Opus comments and M4A freeform fields; `TMED`
  in the ID3 chunk of a WAV file.  The genre (`TCON`) stays the genre.
- **What it must say:** the code or the name of a track type, in any
  case - `Jingles`, `JINGLES` and `jngl` all mean *Jingles*.  Only the
  types the upload dialog offers count (Settings → Track Types,
  *Visibility* enabled).
- **What it wins over:** the type chosen in the upload dialog and the
  Track Type Upload Default (which the Import Folder uses too).
- **Cue points follow it:** whether the import detects cue points is a
  setting of the track type (*Analyze cue points*); with the tag, the
  tagged type decides.
- **Anything else is ignored:** an empty tag, a misspelt type
  (`Jingle`) or a value like `CD` or `Digital Media`, which MusicBrainz
  writes into the same frame, changes nothing; the track gets the type
  it would get without the tag, and the analyzer log names the file.

**Re-read Tags** sets the type too when the tag names a known type; an
unknown or missing tag leaves the type as it is.  A lossless file that
is converted to MP3 keeps the tag.  On 2026-11-09 no track in the
library carried the tag, so existing tracks are unchanged.

### Editing track metadata

Click a track row → **Edit Metadata** in the row's action menu.  If a save is refused (for example a date in the wrong format), the editor stays open and lists the reason above the fields (since 2026-11-08).

| Field | Where it ends up |
|---|---|
| **Title** | `cc_files.track_title` |
| **Creator (Artist)** | `cc_files.artist_name` |
| **Album** | `cc_files.album_title` |
| **Genre** | `cc_files.genre` |
| **Year** | `cc_files.year` |
| **Country** (since 2026-11-08) | `cc_files.country` - free text, from the `Country` tag on import; the field suggests the countries already in use. The base of Analytics → [Music by Country](./ANALYTICS.md); smart blocks can filter on it (criterion *Country*). Library column *Country* (hidden by default, searchable). |
| **BPM** | `cc_files.bpm` |
| **Track type** | `cc_files.track_type` — used by smart-block filters |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — trim the start / end without re-encoding. Since 2026-09-30 the values are kept inside the file: a cue out past the file length is capped at the length, a cue in below zero becomes zero. A change is copied into the rows of the upcoming shows that schedule the track (rows that have already started are left alone), and those shows are laid out again - no refilling needed. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — used by the playout engine for level normalisation |
| **Play Count** | Library column (hidden by default, columns picker), read-only: how often the track aired - one count per row of the playout history, the same number as Playout History → File Summary. Sortable; the advanced search takes a range. Since 2026-10-07. |
| **ID** | Library column (visible by default, columns picker), read-only: the database id of the file, the number the REST API and the playout logs use. Only files carry it - playlists, smart blocks and webstreams have their own number ranges and show an empty cell. Sortable; the advanced search takes a range. Since 2026-10-16. |
| **Teaser** / **Teaser for shows**, **Teaser type** | The show(s) a jingle announces and how (show teaser, day teaser "today", day teaser "tomorrow"); two fields of the track editor and the bulk edit, shown as `Show name · today` in the library column *Teaser* (hidden by default, searchable). Smart blocks pick the fitting jingles with the criterion *Teaser: fits the schedule* - see [Teaser Automation](./TEASERS.md). Since 2026-10-16. |
| **Crossover** | How this track meets its neighbours (since 2026-09-29 one three-way field; the two exceptions exclude each other). **As the track type** (default): the track overlaps and fades as its track type says - Settings → Track Types → *Crossfade Duration* - or, without a value there, as the Default Track Crossfade Duration; since 2026-09-30 it also inherits the type's *No Fade during Crossover* preset. **No Fade during Crossover** (`cc_files.no_fade_crossfade`): the overlap stays, but this track keeps its full level while the other one fades; at an overbooked show boundary a flagged outgoing track is cut instead of faded. **Exclude from Crossover** (`cc_files.exclude_crossfade`): this track never overlaps a neighbour - it starts at the end of the previous track and the next one starts at its end. Changing to or from *Exclude* re-lays the rows of the upcoming shows that schedule the track. |
| **Stream Metadata** (since 2026-10-14) | Whether artist and title of this track reach the listeners' players (ICY) and the Live Text. **As the track type** (default): the preset of Settings → Track Types → *Forward Metadata to the Stream*. **Forward to the stream** / **Do not forward**: the track's own choice. While a track without forwarding plays, the stream shows "Station name - Show name" in every Stream Label format, like a live source without metadata. Meant for jingles, station IDs and promos; the Playout History is not affected. |
| **Enabled From** (since 2026-11-08) | `cc_files.enabled_from`, format YYYY-MM-DD, empty = no enable date. The track stays disabled until 00:00 of that day; then the hourly run enables it, unless it was disabled by hand. Must lie before the expiry date. From the `Enable Date` tag on import. Library column *Enabled From* (hidden by default). |
| **Expiry Date** | `cc_files.expires_at`, format YYYY-MM-DD, empty = no expiry. The date counts from 00:00 of that day: once it is reached, the hourly expiry run ticks **Track disabled**. A later or empty date enables the track again, unless it was disabled by hand. From the `Expiry` / `Expiry Date` tag on import. |
| **Track disabled** (since 2026-11-08) | `cc_files.disabled`. Tick it by hand, or it is ticked automatically while the enable date lies ahead and once the expiry date is reached. A disabled track is no longer picked by smart blocks; shows that already have it keep playing it, and you can still schedule it by hand. In the editor the fields follow each other before you save: an expiry date up to and including today or an enable date after today ticks the box; changing or clearing the dates unticks it again unless you ticked it by hand; unticking the box empties an expiry date that has been reached and an enable date still ahead. Saving without the tick while a date still disables the track is refused with a message. A tick by hand is stored on its own (`cc_files.disabled_by_hand`), so a track you disabled stays disabled when its dates change. Library column *Disabled* (hidden by default, columns picker). |

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

While the server deletes, the table shows its loading overlay and
the **Delete** button reads "Deleting N item(s)…"; both clear when
the request has finished.  Deleting many tracks at once is quick
(since 2026-11-06 the check whether a repeat still needs a track
takes milliseconds instead of about two seconds per file).  Should
the request fail or time out, a message asks you to reload the page
to see which items were removed.

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
| **Criteria** | Add rows: *artist contains "Bowie"*, *bpm is in the range 100 to 130*, *genre is pop*, etc. Rows combine with AND; the **+** next to a row adds an alternative for the same field (OR), e.g. *genre is pop* **+** *genre is rock*. Since 2026-11-08 also *Country* (e.g. *country is Austria*; *is* and *is not* compare exactly, *is not* and *does not contain* include tracks without a country). Details under [Import / Export → blocks.json](./IMPORT_EXPORT.md#blocksjson). |
| **Limit to** | One of: **Number of tracks** (e.g. 10), **Duration in time** (e.g. 30:00), **Time remaining in show** (let the smart block fill exactly to the show's end). |
| **Sort** | Random / newest first / by artist / by play count / etc. |

> **Operator tip.** The **"Time remaining in show"** limit is
> the most useful for autoloading playlists. Combined with an
> intro + outro playlist, you can build a one-hour show by
> stamping a 30 s intro + a `*` smart block + a 60 s outro, and
> the auto-build will sandwich the right number of tracks
> between them.

### Why a smart block can return fewer tracks than you asked for

Smart blocks search the **whole library** for every role - a
DJ's smart block also draws on other users' tracks.  To limit
a block to your own tracks, add the **Owner** criterion.

If you set "Limit to 10 tracks" but only 4 tracks in the
library match the criteria, you get 4. The block does not
error.

**Disabled tracks** are never picked.  Since 2026-11-08 a smart
block judges this at the time the slot airs, not at the time it is
filled: autoloading fills a show about an hour ahead, so a track
whose **Enabled From** is the day of a 00:07 show is picked for it,
and a track whose **Expiry Date** is that day is not.  A track
disabled by hand is never picked.

> **How it works under the hood.** Criteria are stored in
> `cc_blockcriteria`. At build time, `BlockExpander.expand()`
> assembles a PostgreSQL `SELECT … WHERE … LIMIT …` over
> `cc_files`. Time-remaining limits convert to a duration cap
> via the episode's `getSecondsRemaining()` — since
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
| **Exclude tracks played lately** | Tracks where `lptime` is `NULL` *or* older than the configured look-back window, in **minutes** since 2026-10-23 (1..525600 min, default 1440 = 24 h; a window saved in hours is shown as minutes). Use this when you want to avoid recent re-rotation without forbidding every prior play. Companion input "Exclude tracks played in the last minutes" appears when the toggle is on.  Since 2026-10-16 the window is measured from the slot the block is expanded for and **planned rows count too**: a track scheduled inside the window - before or after the slot, including rows an earlier block of the same fill placed in the same show - is excluded although it has not played yet.  Since 2026-10-23 this also holds **within one playlist**: a playlist is expanded block by block before anything is inserted, and a track (or, for the artists filter, an artist) an earlier block or fixed item of the same playlist already gathered is left out by the later blocks - two "Dayteaser" blocks in one playlist no longer pick the same teaser. |
| **Exclude artists played lately** | Tracks whose `artist_name` is NULL / empty *or* has not been heard via any other track in the configured look-back window, in **minutes** since 2026-10-23 (1..525600 min, default 1440). Use this when you want to avoid two tracks by the same artist clustering together — independent of which specific track was played. Companion input "Exclude artists played in the last minutes" appears when the toggle is on. |
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
> .lptime < NOW() - INTERVAL 'N minutes'` clause to the Propel
> query. The hours value is persisted in
> `cc_block_criteria` (criteria = `exclude_played_lately_minutes`)
> alongside the master flag (criteria = `exclude_played_lately`).
> `Exclude artists played lately` adds a `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts > NOW() -
> INTERVAL 'N minutes')` — `NOT EXISTS` short-circuits on the
> first hit so cost stays bounded even with a large history
> table. Persisted as a second criteria pair
> (`exclude_artists_played_lately` + `..._minutes`).
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

### "Allow last track to exceed time limit" (Advanced options)

With a time limit (minutes, hours, time remaining) the block keeps
adding tracks until the limit is reached, and with this box the
last one may run past it.  For the **autoloading fill** (since
2026-10-26) the box also means: the block's last track may run
past the **show's end** - in full when the next show has "Allow
delayed start", otherwise cut at the end when at least half of it
plays.  For an episode block ("limit: 1 item") the box is only
needed in front of a show that must start on time; see
[Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

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
Instead of dragging you can also select items and click **Add to
current playlist** in the library toolbar, or choose **Add to
Playlist** in a row's context menu (tracks, smart blocks, webstreams,
line inputs; since 2026-10-21).  Both refer to the editor tab that is
active; with **Scheduled Shows** active the button adds to the show
instead.

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

### Deleting a playlist that shows still use (since 2026-10-28)

When you delete a playlist from the library, RASTATIME first looks up
which shows use it as their **autoloading**, **intro** or **outro**
playlist, or whether it is the station default intro / outro from
Settings → General.  The delete question then lists those shows.  If
you confirm, the shows lose the playlist **and** their *Add Autoloading
Playlist* tick is switched off, so the calendar shows the real state
instead of a show that looks filled and runs silent.  Pick another
playlist in the show dialog afterwards.  Before 2026-10-28 the tick
stayed on and the show stayed empty; the dashboard now also warns about
such shows up to 48 hours ahead (see
[Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), section 7).

### Using a playlist in a show

Two paths:

1. **One-off**: drag the playlist onto an empty show in the
   show-builder. The playlist's items are *flattened* into the
   schedule at the drag point. The original playlist is not
   linked to the show — editing the playlist later does not
   affect the schedule.

2. **Autoloading**: attach the playlist to the show definition
   on the show-edit form's **Autoloading Playlist** section.
   Every future episode of the show will have the playlist's
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
| **Edit** | One track selected: its editor tab, as before. **Two or more tracks selected (since 2026-10-08): one dialog for all of them** - creator, album, genre, year, track type, language, mood, label, composer, conductor, copyright, country (since 2026-11-08), enabled from and expiry date (`none` clears them), track disabled (*Yes* / *No*; since 2026-11-08, *No* also clears expiry dates that have been reached and enable dates still ahead), description. Empty fields stay unchanged, a filled field is written to every selected track; title, track number, BPM, cue points and artwork stay per track. Database only, like the single editor (tags inside the files are read at import and never rewritten). Tracks you may not edit are skipped and counted in the result. |
| **Move to Owner** | Reassign ownership (Admins only). Used when a DJ leaves and their files should pass to the station account. |
| **Cue Points** | Detect the cue points of the selected tracks from their audio (the same silence detection the analyzer runs at import: quieter than −60 dB for at least 0.3 s at the head or the tail) and store them. Upcoming shows that schedule the tracks follow the new values and are laid out again. Tracks longer than 15 minutes are skipped - the action is meant for jingles and other short elements. Since 2026-09-30. |
| **Re-read Tags** *(since 2026-10-21)* | Re-read the tags of the selected tracks from the files on disk - for files you edited in Windows after the import.  RASTATIME never re-reads a file on its own: the database is the truth for the library and the playout.  The button replaces title, artist, album, genre, year, track number, composer, copyright, label, ISRC, BPM, mood, language, comment and (since 2026-11-08) country with what the file carries (a tag missing in the file clears the column), sets the track type a **Media Type** tag names (since 2026-11-09; an unknown or missing tag leaves the type) and refreshes the checksum and size; everything else set only in RASTATIME (teaser, cue points, loudness, expiry and enable date, requests) stays.  Admins and programme managers for every file, others for their own.  The file is only read, so a track on air is safe - but edit a file in Windows only while it is not scheduled, the playout plays straight from the library. |

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

> **Failed uploads (since 2026-10-28).**  The filter on the Upload page
> reads **Failed (N)** as soon as something failed, and the row says
> *why* (the analyzer's reason, e.g. "ffprobe could not read the file").
> **Download** gives you the original as it was uploaded, so you can look
> at it or repair it; **Clear** removes the row together with the
> original that the analyzer keeps in `organize/` for failed imports.
> The dashboard warns when failed uploads older than an hour are waiting
> or when files older than a day are left in `organize/`.  One kind of
> damage is repaired automatically: a WAV file with an ID3 tag block in
> front of its RIFF header is cut free and imported.

### "I uploaded a WAV file and the library shows an MP3."

That is intended: lossless files are converted to MP3 320 kbps on
import (section 2, *File formats on import*).  To keep a file
lossless, switch off Settings → **Local Machine** → **Import Format**
before you upload it.

### "Why is my smart block returning the same tracks every time?"

You probably picked **Static** instead of **Dynamic**. Edit the
block and switch the type; the next build will re-query.

### "Can I import a folder structure preserving subfolder names?"

The Local Import Folder preserves subfolder names as the
imported tracks' **album** field if no ID3 album tag is set.
This is the most common operator pattern for a long-tail music
archive.  Inside the media library the file is then filed under
`imported/<artist>/<album>/`; a file without an artist tag goes
to `imported/tagless/` (since 2026-10-24).

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
