# Import/Export

> **Where you are in the manual.** Settings → **Import/Export** moves
> calendar objects in and out of RASTATIME as files: shows, playlists,
> smart blocks, webstreams and podcast subscriptions. Read
> [Calendar](./CALENDAR.md) and [Show Templates](./SHOW_TEMPLATES.md)
> first if the New-Show dialog is new to you — the import creates
> shows exactly as that dialog would.
>
> **What this feature replaces.** Building a whole programme schedule
> through the New-Show dialog, one show at a time, and retyping it when
> the station moves to a new RASTATIME.

The page has two halves. **Export** writes the current objects as
CSV (and JSON for smart blocks). **Import** takes such files back —
one ZIP bundle with everything, or a single file with one type — and
always shows a **preview** first: every row is checked, you tick the
rows you want, and only those are written. A row whose time overlaps
an existing show is never imported.

Only Administrators see the page.

---

## 1. Export

1. Tick the types you want. The number in brackets is how many rows
   the export will contain; the file name is the one the import
   expects back.
2. Click **Export selected types**.
   * One type gives a single file (`shows.csv`, `playlists.csv`,
     `webstreams.csv`, `podcasts.csv` or `blocks.json`).
   * Several types give a ZIP with all files, a `logos/` folder with
     the show logos and a `README.txt` that explains every column.
3. **Download template bundle** gives the same ZIP with the column
   headers, one example row per type and the README — the quickest
   way to start a spreadsheet from scratch.

The show export contains the shows that still have upcoming
broadcasts. Each row starts at the show's **next** broadcast, so an
exported file can be imported again without touching the past.

CSV files are UTF-8 with a `;` delimiter and open cleanly in Excel or
LibreOffice; on import `,` and TAB are accepted as well. Switch
columns take `yes`/`no`.

## 2. Import

1. Choose the file: the ZIP bundle, or one CSV/JSON file. Leave
   **Type** on *detect from file* unless your file has an unusual name.
2. **Existing names**: *skip* (default) leaves an object whose name
   already exists untouched; *replace* overwrites playlists, smart
   blocks, webstreams and the options of a podcast subscription.
   Shows are never replaced — a show that would overlap simply fails.
3. Click **Preview**. The table lists every row with its status:
   * **ready** — valid, will be created when you import;
   * **skipped** — exists already (with *skip*), or not selected;
   * **error** — the note says why (unknown playlist, overlap, bad
     date …). Fix the file and upload it again, or import the other
     rows.
4. Untick what you do not want and click **Import selected rows**.
   Rows are created in dependency order — webstreams, smart blocks,
   playlists, podcasts, shows — so a playlist may reference a block
   from the same bundle, and a show a playlist from the same bundle.
5. The result table shows what was created, skipped or failed. The
   calendar and the playout pick the new shows up on their next
   refresh (about two minutes).

Every row is checked a second time right before it is written, so a
show that became overlapping while you looked at the preview is still
refused.

## 3. The files

### shows.csv

| Column | Meaning |
|---|---|
| `name`, `url`, `genre`, `description` | as in the dialog; only `name` is required |
| `start_date`, `start_time`, `end_date`, `end_time` | first broadcast; `end_date` may stay empty (same day, or next day when the end lies before the start) |
| `timezone` | IANA name such as `Europe/Berlin`; empty = the station's timezone |
| `allow_delayed_start` | yes/no, see [Delayed Start](./DELAYED_START.md) |
| `repeats`, `repeat_type` | `none`, `weekly`, `biweekly`, `every_3_weeks`, `every_4_weeks`, `monthly_date`, `monthly_weekday` |
| `days` | for the weekly types: `Mon,Tue,Wed,Thu,Fri,Sat,Sun` (German short names work too); empty = the weekday of `start_date` |
| `repeat_end_date`, `no_end` | last broadcast date, or `no_end = yes` |
| `linked`, `record` | yes/no |
| `content`, `content_repeat` | the name of a playlist used as the show's **autoloading playlist**, and whether it repeats until the show is full — see [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md). A playlist can hold tracks, smart blocks, webstreams and line-in inputs, so this fills every instance of the show automatically. |
| `intro_playlist`, `outro_playlist` | playlist names; empty = the station defaults |
| `rastatime_auth`, `custom_auth`, `custom_username` | live DJ authentication as in the dialog |
| `djs` | DJ logins, comma separated; only users of type DJ can be assigned |
| `background_color`, `text_color` | six hex digits without `#` |
| `logo` | file name inside the bundle's `logos/` folder (jpg, png, gif) |

**The custom live password is never part of the file.** The export
leaves it out, and the import gives a show with custom authentication
a random password that nobody knows. Set the real password in the
Calendar afterwards; the preview and the result say so on every such
row.

### playlists.csv

`name`, `description` and `items`. `items` lists the contents in
order, separated by `|`:

```
file:imported/Example Radio/StationID/Intro.mp3|webstream:BBC World Service|block:Morning Music|linein:Studio A
```

Files are referenced by their path below the library root (as the
export writes it), everything else by name. Cue points and fades come
from the file and the defaults, as when you drop an item into a
playlist.

### blocks.json

A JSON list, one object per smart block: `name`, `description`,
`type` (`dynamic` or `static`), `limit` (`value` and `modifier`:
items, minutes, hours, remaining), `sort`, the switches
(`repeat_tracks`, `overflow_tracks`, `only_unplayed`,
`only_with_expiry`, `use_requests`, `exclude_played_lately` with its
hours, `exclude_artists_played_lately` with its hours) and `criteria`,
a list of rules with `group`, `field`, `modifier`, `value` and `extra`
(the second value of `between` and *is in the range*).

**How rules combine.** A `group` is one row of the smart block editor.
Rules with the same group **and** the same field are alternatives
(OR) — the rows the **+** button next to a criterion adds. Everything
else is combined with AND: different groups, and different fields even
within one group. Example — *genre is Pop or Electronic, and above
110 BPM*:

```json
"criteria": [
  {"group": 0, "field": "genre", "modifier": "is", "value": "Pop"},
  {"group": 0, "field": "genre", "modifier": "is", "value": "Electronic"},
  {"group": 1, "field": "bpm", "modifier": "is greater than", "value": "110"}
]
```

"Either A and B, or C" across different fields cannot be expressed in
one block; put two smart blocks into a playlist instead. If the same
field appears in several groups, give alternatives only to its first
group — otherwise the selection nests as ((A or B) and C) or D. The
editor behaves the same way.

**Dates.** For *Uploaded* (`utime`), *Last Modified* (`mtime`) and
*Last Played* (`lptime`):

* `before`, `after` and `between` count back from now: a whole number
  in `value` plus `unit` — `minute`, `hour`, `day`, `week`, `month` or
  `year`; `between` also takes `extra` with `extra_unit`.
  `{"field": "utime", "modifier": "after", "value": "30", "unit": "day"}` = uploaded in the last 30 days. Exports made before
  2026-10-14 wrote `"7 day ago"` into `value`; that form is still
  accepted.
* The other modifiers take an absolute date `YYYY-MM-DD` or
  `YYYY-MM-DD HH:MM:SS` in your user timezone, as the editor shows it.

The preview checks every rule as the editor does — modifier fits the
criterion, numbers, durations (`HH:MM:SS`), dates, length — and lists
what is wrong. A block is written completely or not at all.

### webstreams.csv

`name`, `description`, `url`, `length` (`HH:MM:SS`) and `input_gain_db`.
The URL is probed on import, as the webstream dialog does.

### podcasts.csv

`url` (the feed), `title`, `auto_ingest`, `auto_expiry_enabled`,
`auto_expiry_days`, `album_override`, `default_track_type` (the code
from Settings → Track Types). The feed is fetched on import; episodes
are not exported — the feed delivers them again.

## 4. Tips

* Export first, even on an empty station: the file carries the exact
  headers and the README.
* Keep one spreadsheet per station and re-import it after changes;
  with *skip* only new rows are created.
* Two rows of the same file that overlap each other: the first is
  created, the second fails at import time with the overlap message.
* Large logos: the upload limit of the server is shown below the
  file field.

## 5. See also

* [Calendar](./CALENDAR.md) — the New-Show dialog whose rules the
  import applies.
* [Show Templates](./SHOW_TEMPLATES.md) — reuse settings inside the
  dialog.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — what the
  `content` column switches on.
* [Backup](./BACKUP.md) — the full database backup; Import/Export is
  the readable, editable companion.
