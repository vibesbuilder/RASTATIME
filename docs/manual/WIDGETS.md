# Public Embed Widgets

> **Where you are in the manual.** This chapter covers the
> drop-in widgets that an external website (your station's
> public homepage, a partner site, an info screen) can
> embed via a plain `<iframe>`. The widgets pull from
> RASTATIME's live data and require no login — they are
> designed to be visible to the public.

RASTATIME ships a small family of HTML widgets that
external sites can embed to show what is currently on
air, what is coming up next, the weekly programme, and so
on. Each widget is a self-contained iframe URL that you
drop into your homepage's HTML.

This chapter is the operator reference: which widgets
exist, what URL parameters they accept, and how to embed
them on an external site.

---

## 1. The widget family

| Widget | URL | Purpose |
|---|---|---|
| **Now Playing — Show** | `/embed/now-playing-show` | Two-line text widget. Current show name + remaining duration; next show name + start–end times. |
| **Now Playing — Track** | `/embed/now-playing-track` | Two-line text widget. Current track "Artist - Title" + remaining duration; next track + start–end times. |
| **Next Shows** | `/embed/next-shows` | List widget. Show title + chronological list of upcoming instances of one recurring show. |
| **Latest Shows** | `/embed/latest-shows` | List widget. Show title + reverse-chronological list of most recent past instances of one recurring show. |
| **On Air Today** | `/embed/on-air-today` | Day-grid widget. Header band + today's current + upcoming shows, each row "HH:MM – HH:MM   Show name (link)". |
| **Weekly Schedule** | `/embed/weekly-program` | Seven-day tab widget. Header with ◀ / ▶ week-navigation + date-range label; day tabs; per-tab row list with HH:MM – HH:MM + show name (link). Optional background-image via `?bg=URL`. |
| **Multi-View Schedule** | `/embed/multi-view-schedule` | Calendar-style widget powered by FullCalendar 6 (locally hosted). Operator-switchable Day / 2-Day / Week views via in-widget buttons or `?view=`. Show slots coloured from `cc_show.background_color`. Click → modal with show description + URL button. Auto-scrolls to the now-line. |
| **Track History** | `/embed/track-history` | Recent-track playout log (last 7 days). HTML5 date-picker + time-picker + Now button + pagesize dropdown (10/20/50/100). Rows show "HH:MM - HH:MM Artist - Title"; click → modal with show context + URL link. Load-more button capped at 1000 rows total. |
| **Stream Player** | `/embed/player` | Listen-live button with now-playing / next lines and a volume slider. Card and full-width bottom-bar layouts. Picks the first browser-decodable stream, falls back if one is down. |

More widgets are planned (see [BACKLOG.md](../../BACKLOG.md)).

---

## 2. Now Playing — Show widget

Drop-in iframe:

```html
<iframe src="https://your-station.example/embed/now-playing-show"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

Two lines, each with a name on the left and a time on the right:

```
Morning Show                                              -25:14
Music Hour                                          10:00 - 11:30
```

- **Line 1**: current show name + countdown to end (`-MM:SS` or `-H:MM:SS`)
- **Line 2**: next show name + its `HH:MM - HH:MM` window

The countdown updates every second on the client side, so
the display looks smooth. The underlying data refreshes
every 60 seconds (configurable — see §7).

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Text colour. `auto` follows the embedding browser's `prefers-color-scheme`. Background is always transparent. |
| `cache` | integer seconds, 10–3600 | `60` | Server-side HTTP cache TTL. Lower = fresher data + more backend hits. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | What to do with show / track names wider than the 340 px widget. `ellipsis` truncates with `…`; `marquee` scrolls left over 24 s so the operator can read the whole title. |
| `timezone` | any standard timezone (`Europe/Berlin`) | station default | All times rendered in this zone. |

> **Note.** The widget body is capped at **340 px wide** to fit
> common sidebar layouts on station websites.  Set the iframe
> width to 340 in the embedding HTML for a flush fit; a wider
> iframe will show white space around the widget.  (Next-Shows /
> Latest-Shows widgets are capped at 300 px — they serve a
> narrower sidebar use-case.)

---

## 3. Now Playing — Track widget

Drop-in iframe:

```html
<iframe src="https://your-station.example/embed/now-playing-track"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

Same two-line layout as the show widget, but for tracks:

```
The Beatles - Hey Jude                                    -02:14
Pink Floyd - Comfortably Numb                       16:00 - 17:30
```

- **Line 1**: current track `Artist - Title` + countdown to end
- **Line 2**: next track `Artist - Title` + its `HH:MM - HH:MM` window

If a track has no artist metadata, only the title is shown
(and vice versa). If neither is available, the line shows
"No track playing" / "No upcoming track" in muted style.

### URL parameters

Same as the show widget — see §2.

---

## 4. Next-Shows / Latest-Shows widgets

Sister widgets that list multiple instances of **a single recurring
show** rather than the "what is on right now" envelope of the two
Now-Playing widgets.  Useful for a show-detail page on your station
site: drop the widget in the sidebar and listeners see the next four
episodes (or the last three, depending on which widget you embed).

Drop-in iframe (next shows):

```html
<iframe src="https://your-station.example/embed/next-shows?show_id=42"
        width="300" height="140" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

Drop-in iframe (latest shows):

```html
<iframe src="https://your-station.example/embed/latest-shows?show_id=42"
        width="300" height="120" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

```
Morning Show
Tue 21 May                                  06:00 - 08:00
Wed 22 May                                  06:00 - 08:00
Thu 23 May                                  06:00 - 08:00
Fri 24 May                                  06:00 - 08:00
```

- **Title row**: the show's name from `cc_show.name`
- **List rows**: one line per instance, `Weekday DD Mon` on the
  left, `HH:MM - HH:MM` on the right

The list refreshes every `cache` seconds (see §7).  When the topmost
row of a Next-Shows widget slips into the past (the show has
actually started), an early refresh fires within ~1 s so the widget
drops the row without waiting out the cache TTL.

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `show_id` | integer (cc_show.id) | — | Identifies the show. Stable across renames and across recurring-instance changes — every instance of a recurring show shares this id. **Recommended over `show`.** |
| `show` | string (cc_show.name) | — | Fallback when `show_id` is absent.  Case-sensitive exact match — **matches every show that shares the name**, so a station with one "BBC News" show per weekday can list them all with a single `?show=BBC%20News` embed.  `show_id` wins when both are set. |
| `limit` | integer 1..20 | 4 (next), 3 (latest) | How many instances to list. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the two-line widgets — see §2. |
| `cache` | integer seconds 10..3600 | `60` | Same as the two-line widgets — see §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Behaviour of the show title when wider than 300 px. |
| `timezone` | any standard timezone | station default | All times rendered in this zone. |

> **Tip.** Pick the show from the dropdown in the Settings page
> (next section) rather than typing the id by hand — the page
> shows a live preview and copies a ready-made iframe snippet with
> the id pre-filled.

### Modified / cancelled instances

Single instances that the operator moved or cancelled
(`cc_show_instances.modified_instance = TRUE`) are filtered out
of the list, matching the convention `Application_Model_Show::
getNextShows` uses on the internal Dashboard.  A single
postponed episode therefore does not leave a phantom row in
the public widget.

---

## 5. On-Air-Today widget

A compact day-grid widget that lists today's schedule from the
currently-airing show through the next few upcoming shows —
capped at the station's midnight so the widget never spills
into tomorrow's programme.

Drop-in iframe:

```html
<iframe src="https://your-station.example/embed/on-air-today"
        width="340" height="250" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

```
On Air Today                       ← header band
────────────────────────────────
16:00 - 16:30    Newslink           ← current row (bold)
16:30 - 17:00    Pages of History (EN)
17:00 - 17:30    L'Info Chez-Vous
17:30 - 04:00    Pages d'histoire
18:30 - 19:00    Choices (EN)
19:00 - 19:30    L'Info chez vous (FR)
```

- **Header**: "On Air Today" (or "On Air *<date>*" when a
  specific day is pinned via the `?day` parameter)
- **Rows**: `HH:MM - HH:MM` on the left, show name on the
  right.  The currently-airing row is rendered in **bold**
  so the operator (and listener) sees at a glance which row
  is live right now.
- **Links**: a show with a configured **Show → Edit → URL**
  renders its name as a clickable link that opens in a new
  tab (`target="_blank" rel="noopener noreferrer"`).  Shows
  without a URL render as plain text.

The list refreshes every `cache` seconds (see §7).  When the
currently-airing row's end-time passes, an early refresh fires
within ~1 s so the bold highlight migrates to the next row
without waiting out the cache TTL.

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `limit` | integer 1..20 | `6` | Total rows (current + upcoming).  Default = 1 current + 5 upcoming. |
| `day` | `YYYY-MM-DD` | today | Pin a specific day (in the resolved timezone) to render historical or upcoming day overviews.  When omitted or equal to today, the widget filters out shows that have already aired; for any other day it lists every show whose start falls inside that day's 24-hour window. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the other widgets — see §2. |
| `cache` | integer seconds 10..3600 | `60` | Same as the other widgets — see §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Behaviour of show names wider than 340 px. |
| `link` | `underline`, `plain` | `plain` | Link rendering for show names: `plain` (default) drops the underline so the names blend into the bold row text; `underline` opts back into the classic hyperlink affordance.  With `plain` the link affordance survives only through the cursor pointer on hover. |
| `timezone` | any IANA zone | station default | Defines "today" and renders all times in this zone. |

> **Day boundary.** "Today" is the station's calendar day —
> 00:00 to 24:00 in the station's timezone (or in `?timezone`
> when overridden).  A show that started yesterday 23:30 and
> is still on air at 14:00 today counts as the current row.
> A show that starts tomorrow 00:30 is **not** listed even if
> the `limit` would otherwise leave room — the cap is hard.

### Modified / cancelled instances

Same convention as the Next-Shows / Latest-Shows widgets —
rows with `cc_show_instances.modified_instance = TRUE` are
filtered out so a single postponed / cancelled instance does
not leave a phantom row in the public widget.

### Settings page

**Settings → Widgets → On Air Today** hosts:

- A single configurable empty-state label (default `No shows
  on air today`, falls back to the English default when blank).
- A live preview iframe on a dark backdrop.
- The ready-made `<iframe>` embed code with the station's
  absolute URL pre-filled.

No show picker — the widget pulls from the live schedule
for the whole station day automatically.

---

## 6. Weekly Schedule widget

A 7-day tab widget — the modernised replacement for the legacy
jQuery + Handlebars schedule embed.  Compact header with
◀ / ▶ navigation, day-of-week tabs, and a per-day row list of
shows.

Drop-in iframe:

```html
<iframe src="https://your-station.example/embed/weekly-program"
        width="400" height="560" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

```
◀  21 May – 27 May 2026                ▶            ← header band
MON  TUE  WED  THU  FRI  SAT  SUN                   ← day tabs
 21   22   23   24   25   26   27                      (today is circled)
─────────────────────────────────────────────────
06:00 - 08:00    Morning Show                       ← row list
08:00 - 10:00    Newslink                              (per active tab)
...
```

- **Header band**: ◀ button → previous week, week-range label
  centred (e.g. "21 May – 27 May 2026"; year-boundary windows
  show the year twice), ▶ button → next week.  Clicking a
  button updates the iframe URL's `week_offset` parameter in
  place via `history.pushState` and reloads — browser cache
  deduplicates back-and-forth navigation.
- **Day tabs**: 7 tabs (Mon … Sun in the visitor's locale).
  Today's tab is decorated with a subtle pill ring on the
  day-of-month number.  Clicking a tab swaps the visible
  panel — no network round-trip.
- **Row list**: per tab, one row per scheduled show.  Time
  on the left, show name on the right.  Names linked to a
  configured `cc_show.url` render as click-through links
  opening in a new tab.

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `week_offset` | integer -2..4 | `0` | Pin the rendered window to ±N weeks from today's rolling 7-day block.  Default 0 = today + 6 upcoming days.  Tight clamp (-2 / +4) because public-homepage use-cases rarely need a wider range; the ◀ / ▶ buttons disable at the boundary so the operator sees they've hit the limit. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the other widgets — see §2. |
| `cache` | integer seconds 10..3600 | `60` | Same as the other widgets — see §8. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Behaviour of show names wider than the 400 px widget body. |
| `link` | `underline`, `plain` | `plain` | Show-name link rendering (see the On-Air-Today widget §5 for details — same convention). |
| `bg` | URL of an image | none | Optional background image (cover-positioned) instead of the default transparent fill.  Operator hosts the image themselves — typically on the station's own site.  Cross-origin image loads work fine for CSS backgrounds. |
| `bgcolor` | hex colour, e.g. `#222222` | none | Optional background colour as a hex string (3, 6, or 8 chars including alpha — e.g. `#fff`, `#112233`, `#11223388`).  Renders behind `?bg` when both are set (useful as a fallback while the image loads, or to fill transparent regions of a PNG).  Non-hex values are rejected for security. |
| `timezone` | any IANA zone | station default | All times rendered in this zone. |

> **Today's day-tab + active state.**  The day-of-week tab
> matching today's calendar date is filled with the
> accent colour (default LibreTime teal `#459B8F`) so the
> operator sees at a glance where they are in the week.
> The currently-active panel's tab gets an accent-coloured
> underline.  Hovering any tab or the ◀ / ▶ buttons lights
> up the same accent at low alpha as a subtle interactive
> cue.

> **Auto-scroll to the currently-airing show.**  When the
> active tab is today, the widget scrolls the show that
> is on air right now into the centre of the panel
> viewport — so the visitor lands directly on "what's
> playing now" instead of having to scroll past the early-
> morning programme.  The same show is marked with an
> accent left-border so the visitor can spot it after the
> scroll.  No-op when today has a programme gap (no
> currently-airing show), or when the active tab is any
> other day.

> **Width.** The Weekly Schedule widget body is **670 px wide**
> (raised from 400 px on 2026-05-25 per operator request — all
> fonts, paddings, and the day-panel max-height scaled
> proportionally; the iframe in the recommended embed snippet
> is `width="670" height="670"`).  Set the iframe to these
> values in the embedding HTML for a flush fit.

### Modified / cancelled instances

Same convention as the other widgets — rows with
`cc_show_instances.modified_instance = TRUE` are filtered out
so a moved / cancelled instance doesn't leave a phantom row.

### Settings page

**Settings → Widgets → Weekly Schedule** hosts the empty-state
label customisation ("No shows scheduled on this day" by
default), a live preview iframe on a dark backdrop, and the
ready-made `<iframe>` embed code with the station's absolute
URL pre-filled.

---

## 7. Multi-View Schedule widget

A calendar-style widget powered by **FullCalendar 6.1.10**
(locally vendored, no CDN dependency).  Three operator-
switchable views: **Day**, **2-Day**, **Week**.  Sits next to
the Weekly Schedule widget as a richer alternative: time-grid
layout with coloured show slots, a "now" indicator line,
auto-scroll to the currently-airing show, and a click-to-open
modal with show description + URL link.

Drop-in iframe (~600 px tall so the 24-hour grid fits
comfortably):

```html
<iframe src="https://your-station.example/embed/multi-view-schedule"
        width="100%" height="600" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

```
◀  Fri 22 May 2026             ▶   Today  [DAY 2DAY WEEK]   ← header
─────────────────────────────────────────────────────────
06:00  ┌──────────────────────────────┐
       │ Morning Show                 │  ← coloured slot
07:00  │ 06:00 – 08:00                │     from cc_show.background_color
       └──────────────────────────────┘
08:00  ┌──────────────────────────────┐
══════ │ Newslink                     │ ════ now-indicator line
       │ 08:00 – 08:30                │      (accent colour)
08:30  └──────────────────────────────┘
...
```

- **Header band**: ◀ / ▶ navigation, centred date-range
  label, **Today** button (snaps the view back to now and
  re-runs the auto-scroll), and the view switcher
  (DAY / 2-DAY / WEEK).
- **Time grid**: 24-hour, 15-min slots, 60-min hour labels.
  Now-indicator line in the accent colour.
- **Show slots**: rendered from `cc_show_instances` JOIN
  `cc_show`.  Background colour comes from the show's
  configured `background_color` (Calendar → Show → Edit →
  Style); empty colours fall back to a soft accent fill.
  The currently-airing show gets an accent ring.
- **Click**: opens a modal with the show's name, time
  range, description, and a click-through link to the
  show URL (if one is configured).

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `view` | `day`, `2day`, `week` | `day` | Initial view.  The visitor can still switch via the in-widget buttons; this only controls the starting state. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the other widgets — see §2. |
| `clock` | `24`, `12`, `auto` | `24` | Time-of-day format on the hour axis, in show slots, and in the modal.  `24` forces `17:00`-style regardless of locale; `12` forces `5 PM`-style; `auto` lets FullCalendar pick from the resolved locale (so e.g. `en` gets AM/PM and `de` gets 24h). |
| `cache` | integer seconds 10..3600 | `300` (5 min) | Server-side HTTP cache TTL for the JSON event feed.  Higher default than the other widgets — the schedule rarely shifts mid-day and the payload is larger, so a 5-min cache is appropriate. |
| `bg` | URL of an image | none | Same as the Weekly Schedule widget — see §6. |
| `bgcolor` | hex colour | none | Same as the Weekly Schedule widget — see §6. |
| `timezone` | any IANA zone | station default | All times rendered in this zone; also defines what "today" means for the auto-scroll. |

> **Day-boundary semantics.**  The grid is 00:00 to 24:00
> in the resolved timezone.  Shows that span midnight
> appear in both days they overlap.

### Data feed

Internal JSON endpoint at `/Embed/multi-view-schedule-data`,
called by FullCalendar's lazy-loading callback for the
currently-visible date range.  Output shape matches
FullCalendar's documented event format:

```json
{
  "success": true,
  "events": [
    {
      "id": 620,
      "title": "Morning Show",
      "start": "2026-05-22T06:00:00+02:00",
      "end":   "2026-05-22T08:00:00+02:00",
      "url":   "https://...",
      "backgroundColor": "#1f8a70",
      "borderColor":     "#1f8a70",
      "textColor":       "#ffffff",
      "extendedProps": { "description": "...", "showId": 42 }
    }
  ]
}
```

Modified / cancelled instances (`modified_instance = TRUE`)
are filtered out, matching the convention all the other
widgets use.

### Settings page

**Settings → Widgets → Multi-View Schedule** hosts:
- the operator-configurable empty-state label,
- a live preview iframe on a dark backdrop,
- ready-made `<iframe>` embed-code snippets for all
  three default views (Day / 2-Day / Week).

### Performance notes

- **FullCalendar locally hosted**: `/js/libs/fullcalendar/
  index.global.min.js` (~282 KB) + `locales-all.global.min.js`
  (~26 KB).  No CDN round-trip, no external network
  dependency, works behind corporate firewalls and in
  air-gapped environments.  See
  `frontend/legacy/public/js/libs/fullcalendar/VERSION.txt`
  for the pinned version + upgrade instructions.
- **CSS is bundled into the JS** by FullCalendar 6 (injected
  into `<head>` at runtime) — no separate stylesheet load.
- **Browser cache** absorbs the initial 308 KB hit after the
  first page-view of any visitor.
- **Lazy event-fetch**: FullCalendar requests events for
  exactly the visible date range, not the whole month —
  keeps each round-trip small.

---

## 8. Track History widget

Recent-track playout log — the visitor picks a day from the
last 7, chooses a page size (10 / 20 / 50 / 100), and the
widget renders the tracks that played in chronological-
descending order.  Click any row → modal popover with the
track's full metadata + show context + click-through link
to the show's URL when one is configured.

Drop-in iframe (~500 px tall to comfortably show 10 rows
plus header + load-more footer):

```html
<iframe src="https://your-station.example/embed/track-history"
        width="100%" height="500" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### What it shows

```
[2026-05-22 ▾] [22:30 ▾] [Today] [10 ▾]             ← header
──────────────────────────────────────────────
22:14 - 22:18   Leyya - Butter
22:09 - 22:12   78plus - Hurrycan
22:04 - 22:08   Pizzera & Jaus - Nochbarn
...
                  [ Load more ]                     ← footer
```

- **Header**: HTML5 date-picker (capped to last 7 days),
  HTML5 time-picker (upper-bound for which tracks to list),
  Now shortcut button (snaps BOTH date and time to the
  current wall-clock),
  and a page-size dropdown.  Changing any of them resets
  to page 1 and re-fetches.
- **Rows**: `HH:MM - HH:MM Artist - Title` — start + end
  time on the left in tabular numerics, then the artist /
  title in bold.  Title-only / artist-only tracks render
  with just the available field.  Empty-both rows are
  filtered server-side, as are tracks shorter than the
  `min_sec` threshold when the exclude-short filter is on.
- **Load more**: appends another page (same size) below the
  existing list.  Hidden when there are no more rows;
  disabled while a fetch is in flight.  Hard-capped at
  10 pages × 100 pagesize = 1000 rows total.
- **Modal**: opens on row click with title, artist, time
  range, a **"Played in the show:"** caption + the show
  name, and an "Open show page →" button when the parent
  show has a configured URL.  The show name itself stays
  plain text — only the dedicated button is the click
  affordance.  When a webstream entry has no instance
  binding, the show-context block is hidden entirely.

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | today | Day to load.  Clamped to `[today - 6 days, today]` — values outside snap to the nearest valid bound rather than erroring. |
| `time` | `HH:MM` (24h) | now (today) / 23:59 (past day) | Upper-bound time-of-day.  The widget shows tracks that ended BEFORE this point, most recent first.  Default seeds the picker to "now" so the widget opens on the most-recently-played slice. |
| `pagesize` | `10`, `20`, `50`, `100` | `10` | How many tracks load per page.  The visitor can still change it in-widget; this only controls the initial state. |
| `exclude_short` | `0`, `1` | Preference (default `1`) | Drop tracks shorter than `min_sec` seconds — catches jingles / station IDs / silence-tail entries.  When the URL parameter is absent the operator-configured Preference (Settings → Widgets → Track History) wins. |
| `min_sec` | integer 1..3600 | Preference (default `60`) | Duration threshold in seconds for the exclude-short filter.  Only relevant when `exclude_short=1`. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the other widgets — see §2. |
| `cache` | integer seconds 10..3600 | `60` | Server-side HTTP cache TTL for the JSON feed. |
| `bg` | URL of an image | none | Same as the Weekly Schedule widget — see §6. |
| `bgcolor` | hex colour | none | Same as the Weekly Schedule widget — see §6. |
| `timezone` | any IANA zone | station default | All times rendered in this zone. |

> **7-day cap rationale.**  The widget is meant for "what
> just played" curiosity, not a long-term archive.
> Operators with a deeper history-browser need would use the
> internal Playout History dashboard instead, which has no
> public-facing scope cap.

### Data feed

Internal JSON endpoint at `/Embed/track-history-data`,
called by the JS runtime on every date / pagesize change
and on Load-more.  Output shape:

```json
{
  "success": true,
  "tracks": [
    {
      "id": 820,
      "title": "Butter",
      "artist": "Leyya",
      "starts": "2026-05-22T20:55:36+02:00",
      "ends":   "2026-05-22T20:59:04+02:00",
      "show": {
        "id":    322,
        "name":  "Auto DJ",
        "url":   "",
        "color": "#919088"
      }
    }
  ],
  "hasMore":  true,
  "page":     1,
  "pagesize": 10,
  "dayLocal": "2026-05-22",
  "timezone": "Europe/Berlin"
}
```

Source: `cc_playout_history` LEFT JOIN `cc_files`
(track_title, artist_name) LEFT JOIN
`cc_show_instances` → `cc_show` for the show context.
**Six kinds of rows** land in the table:

1. **Scheduled file plays** (`file_id IS NOT NULL`) —
   title / artist live on `cc_files` and the JOIN picks
   them up directly.
2. **Scheduled webstream items** (`file_id IS NULL`,
   metadata-only) — written by
   `HistoryService::insertPlayedItem()` when Liquidsoap
   fires `notifyMediaItemStartPlayAction` for a
   `cc_schedule` item with `stream_id`.  Writes a
   synthetic "block" entry with `title =
   cc_webstream.description` (falls back to `name` if
   description is empty) and `artist =
   cc_webstream.name` so the slot is recorded even
   when the stream server sends no ICY data (operator
   example: title="Tägliche Event-Ansagen für die
   kommende Woche" / artist="Event Calendar").
3. **Scheduled line-in items** (`file_id IS NULL`,
   metadata-only — **RASTATIME-only**, requires
   migration 0047 column `cc_schedule.linein_id`) —
   written by `HistoryService::insertPlayedItem()` when
   Liquidsoap fires `notifyMediaItemStartPlayAction` for
   a `cc_schedule` item with `linein_id` (operator
   dragged a line-in from the Library into a show
   schedule, e.g. "Jabra-Mikro").  Writes a synthetic
   "block" entry with `title =
   rastatime_linein.description` (free-text context,
   e.g. "Drahtloses Bluetooth-Headset im Studio A",
   falls back to the short name when description is
   empty) and `artist = rastatime_linein.name` (short
   label, e.g. "Jabra-Mikro").  `linein_id` is read
   via raw SQL because the Propel ORM sources were
   generated before the RastaTime migration and don't
   know the column.
4. **Webstream tracks** (`file_id IS NULL`, metadata-
   only) — written by
   `HistoryService::insertWebstreamMetadata()` when
   Liquidsoap calls `/api/notify-webstream-data`.
   Per-track granularity: when the upstream stream
   forwards ICY-/Now-Playing metadata, each metadata
   change produces one row.  The two webstream paths
   coexist — operators see both the "block" entry for
   the whole slot AND any per-track entries inside.
5. **Live-Show sessions** (`file_id IS NULL`, metadata-
   only) — written by
   `HistoryService::ensureLiveShowLogged()` as a
   side-effect on every `/api/live-info(-v2)` call.
   Catches `cc_show_instances` rows with `time_filled =
   '00:00:00'` (= operator created the show slot but
   scheduled no items, so Liquidsoap auto-switches to
   master_dj for the slot duration).  `artist = "Live
   Show"` distinguishes this path from the manual
   Dashboard-switch path below.  Idempotent — guarded
   by an `instance_id + file_id IS NULL` lookup.
6. **Manual Dashboard source switches** (`file_id IS
   NULL`, metadata-only) — written by
   `HistoryService::insertLineInLog()` when the
   operator toggles a Master Source or Show Source
   switch in the Dashboard.  `artist = "Master Source"`
   for master_dj, `"Show Source"` for live_dj, so a
   future UI pass could differentiate the two.

For all six kinds the optional show binding (via
`instance_id`) drives the "Played in the show:" caption
in the modal.  The display label (used as `track_title`
for kinds 5 + 6) is operator-configurable under
**Settings → Widgets → Track History → "Line-Input
label"** (default `"Line Input"`).  Kind 3 uses the
per-line-in `name` from `rastatime_linein` instead,
which the operator sets in the Line-In Library.

### Settings page

**Settings → Widgets → Track History** hosts:
- The operator-configurable empty-state label,
- An **Exclude short tracks** checkbox (default on) plus
  the corresponding **Exclude tracks shorter than (s)**
  threshold (default 60 s, shown only when the checkbox is
  on — same Auto-Expiry-style toggle as the podcast
  settings),
- A live preview iframe on a dark backdrop,
- Two ready-made embed-code snippets (pagesize 10 + 50).

Per-embed `?exclude_short=` and `?min_sec=` URL parameters
override the Preference for a specific iframe without
changing the global setting.

---

## Stream Player widget (`/embed/player`)

> Rebuilt 2026-09-18 in the wave style — the 2015 jQuery player is
> gone.  Old embed URLs keep working unchanged.

Listen-live button for the public homepage.  Plays the streams
enabled under **Settings → Streams**: the widget prefers mobile
streams on small screens, keeps only formats the visitor's browser
can decode, and automatically falls back to the next stream when
one is down.  The now-playing line, the current-show line and the
**Next** line refresh themselves from the widget data endpoint
(no public-API toggle needed); a localhost-configured Icecast host
is rewritten to the page host for remote listeners.

Two layouts:

* **card** (default) — compact panel, same footprint family as the
  Now-Playing widgets; includes a volume slider (remembered per
  browser).
* **bar** — full-width 56-px bar, meant to sit fixed at the bottom
  of the page (the station homepage uses it).

URL parameters (all optional):

| Parameter | Values | Meaning |
|---|---|---|
| `title` | text | Header text; without it the header row is hidden. |
| `theme` | `auto` / `dark` / `light` | Same theming as every widget. |
| `layout` | `card` / `bar` | Layout; the legacy `style=premium` still maps to `bar`. |
| `stream` | `auto` / stream name | Pin one configured stream instead of the automatic pick. |
| `cache` | `10`..`3600` | Metadata-poll cache in seconds. |

Embed codes with a live preview are on **Settings → Widgets →
Player**.  The empty-state wording of the metadata lines is shared
with the Now-Playing widgets (section 9).

---

## 9. Customising the empty-state labels

When there is no current or upcoming show / track, the widget
falls back to a short placeholder text.  Operators can customise
all four placeholders without touching code under:

**Settings → Widgets → Current Show/Track**

| Setting label | Default value |
|---|---|
| No show on air: | `No show on air` |
| No upcoming show: | `No upcoming show` |
| No track playing: | `No track playing` |
| No upcoming track: | `No upcoming track` |

Edits are persisted in `cc_pref` and picked up by the widget
within one cache TTL (default 60 seconds).  Leave a field blank
to fall back to the English default shown in its placeholder.

The same Settings page hosts:

- a **live preview** of both widgets side-by-side so you can
  see how a label change looks immediately after saving;
- the **ready-made `<iframe>` embed code** for each widget
  with the station's absolute URL pre-filled, ready to paste
  into the homepage HTML.

The Next-Shows / Latest-Shows widgets have their own labels page
under:

**Settings → Widgets → Next/Latest Shows**

| Setting label | Default value |
|---|---|
| No upcoming shows: | `No upcoming shows` |
| No past shows: | `No past shows` |

That page also hosts a **show picker dropdown** that drives the
preview iframes and the embed-code snippets — pick the show, hit
Save, and copy the generated `<iframe ...>` block with the
`show_id` already baked into the URL.

---

## 10. The `cache` parameter — what is the right TTL?

The server caches the underlying data for `cache` seconds
before regenerating it. The JS poll inside the iframe
matches this cadence, so under heavy load each visitor hits
the **browser cache** rather than your backend.

Recommended values:

| `cache=` | When |
|---|---|
| `30` | High-accuracy display, e.g. lobby screen at the station. Burns ~2 backend hits/min per browser. |
| `60` (default) | Public homepage with moderate traffic. Good balance of freshness and load. |
| `120`–`300` | Very high-traffic embed (popular news site referring listeners). Trade up to 5 min staleness for an order of magnitude fewer backend hits. |
| `> 600` | Not recommended — the displayed show / track will often already have ended by the time the browser polls again. |

> **Operator tip.** The widget compensates for stale data:
> when the current item's end-time passes (computed
> client-side from the absolute timestamps in the payload),
> the JS fires an immediate poll without waiting for the
> next interval. So a `cache=300` embed still flips to the
> next track within ~1 s of it actually starting — the
> staleness only affects the first display after a long
> idle pause.

> **How it works under the hood.** Both widget endpoints
> set `Cache-Control: public, max-age=<cache>`. Apache
> serves the iframe HTML; the in-iframe JS polls
> `/embed/now-playing-data` (same cache TTL) for refresh
> payloads. The JSON endpoint pulls from
> `Application_Model_Schedule::GetPlayOrderRange()` — the
> same source `/api/live-info` uses — but trimmed to ~1-2
> kB of payload so the round-trip stays cheap.

---

## Cover artwork (`?art=`)

> Added 2026-09-18.

Three widgets can show the cover of the track they are talking
about: the **Stream Player** (both layouts), the **Track History**
rows, and the **Now Playing — Track** widget.

| Widget | Default | Turn it off / on |
|---|---|---|
| Stream Player | **on** | `?art=off` |
| Track History | **on** | `?art=off` |
| Now Playing — Track | **off** | `?art=on` |

Now Playing defaults to *off* on purpose: that widget is documented
with `height="50"`, and covers are opt-in so no existing embed
changes on its own. With `?art=on` the box grows to about 48 px, so
give the iframe `height="56"` or more.

Two things are worth knowing:

* **Only tracks that actually have a cover show one.** Everything
  else keeps its text-only look — a Track-History row without a
  cover keeps an empty slot so the columns stay aligned, and the
  player simply hides the image. Webstreams and Line-Ins never have
  a cover.
* **Covers need the public API.** They are served by the same
  endpoint the Song-Request widget uses, which is gated by
  Settings → Preferences → *Public API*. With that toggle off the
  widgets still work, just without pictures.

If covers rarely appear, the cause is almost always the library
rather than the widget: only files whose artwork was imported have
one. Settings → Library shows the artwork per track.

---

## 11. Theming

Three modes, controlled via the `theme` URL parameter:

| `theme=` | Effect |
|---|---|
| `auto` (default) | Light text on dark embedding pages, dark text on light ones. Detected via the browser's `prefers-color-scheme` media query. |
| `dark` | Force light text (use this if your embedding page is dark themed but the visitor's OS is set to light). |
| `light` | Force dark text. |

The widget's background is **always transparent** so it
blends into whatever the embedding page looks like. The
font stack defaults to the embedding page's system font so
the widget feels native to its surroundings rather than
imposing a typography.

If you need custom CSS, the simplest path is to wrap the
iframe in your own styled container and rely on the
transparent background:

```html
<div class="my-station-now-playing-card">
    <iframe src=".../embed/now-playing-show?theme=dark" ...></iframe>
</div>
```

---

## 12. Authentication

None. The Now-Playing widgets are intentionally public:
the whole point is that any visitor on your station's
public website can see what is on air. There is no API key,
no session cookie, no per-visitor auth.

This is safe because the widgets expose only the data a
listener would see in the player anyway (show / track name
+ times). They do **not** expose:

- Listener counts
- Stream source state (Show DJ / Master DJ / Auto DJ)
- Operator names
- Recording state
- Internal IDs

If you need a richer authenticated widget (e.g. showing
which DJ is on air right now), open the password-protected
[Dashboard](./DASHBOARD.md) instead.

---

## 13. Cross-origin embedding

Iframes work cross-origin out of the box — no extra
configuration needed. Your station's homepage can embed
the widget regardless of which host serves the homepage.

If you previously tried embedding via JavaScript snippet
and ran into CORS errors, switching to the iframe approach
(this chapter) sidesteps the problem entirely.

---

## 14. Troubleshooting

### "Widget shows 'No show on air' but a show is running"

- Verify the show is actually playing — check the
  internal [Dashboard](./DASHBOARD.md) or the
  station's main stream.
- The server-side cache may still have stale data.
  Wait up to `cache` seconds (default 60) or hard-reload
  the iframe's parent page.

### "Widget shows nothing at all (blank iframe)"

- Verify the iframe URL is reachable from the embedding
  page's browser context. Open the URL directly in a new
  tab — it should render the widget standalone.
- Check the browser console (right-click iframe → Inspect
  Element → Console) for JS errors.
- Ensure RASTATIME's Apache is serving the iframe URL on
  the public hostname configured under Settings →
  General Preferences. The URL must be reachable from
  the visitor's browser, not just from the station's LAN.

### "Widget background is white but I want dark"

Add `?theme=dark` to the iframe URL. If you want it to
follow the visitor's OS preference, use `?theme=auto`
(the default).

### "Countdown shows -00:00 and stays there"

The current item's end-time has passed but the widget has
not yet picked up the new data. This auto-recovers within
~1 s thanks to the early-poll mechanism. If it persists
longer, the playout engine may have stopped — check
`Get-Service RASTATIME-PLAYOUT`.

### "On Air Today widget is empty even though shows are scheduled"

- Check that *today* in your station's timezone still has
  upcoming shows: late at night the widget legitimately becomes
  empty until the next station-midnight rolls over.  If you
  want to look ahead, pin a specific day via
  `?day=YYYY-MM-DD`.
- Verify the shows are actually scheduled in the Calendar —
  cancelled (`modified_instance = TRUE`) instances are
  filtered out by design.
- If the iframe URL contains `?timezone=...`, that overrides
  the station timezone for the "today" boundary calculation.
  A `?timezone=Asia/Tokyo` embed will show Tokyo's today,
  which may already be tomorrow at the station.

### "Next / Latest Shows widget shows the empty placeholder"

- Verify the iframe URL contains `?show_id=N` (preferred)
  or `?show=Name`.  The Settings page (§5) generates the
  snippet with the id baked in — copy it from there rather
  than hand-crafting the URL.
- Confirm the show actually has future instances in the
  Calendar (for Next Shows) or has aired at least once
  (for Latest Shows).  A brand-new show with no aired
  episodes shows the empty placeholder on the Latest
  widget until the first episode finishes.
- `modified_instance = TRUE` rows are filtered out by
  design (matches the internal Dashboard).  A show whose
  only upcoming instance has been moved or cancelled
  shows empty until a fresh instance is generated.

---

## Where to go next

* [Dashboard](./DASHBOARD.md) — the internal version of
  the same data, with full operator controls.
* [Streams](./STREAMS.md) — the underlying audio
  streams the widgets describe.
* [BACKLOG.md](../../BACKLOG.md) — upcoming widget waves
  (Next Shows / Latest Shows, Weekly Program enhancements,
  Track History).
