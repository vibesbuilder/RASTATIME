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
| **Audio Player** | `/embed/player` | (Existing) Inline HTML5 audio player for the public stream. |

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
        width="400" height="340" frameborder="0"
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
| `week_offset` | integer -52..52 | `0` | Pin the rendered window to ±N weeks from today's rolling 7-day block.  Default 0 = today + 6 upcoming days.  Server-clamped at ±52. |
| `theme` | `auto`, `dark`, `light` | `auto` | Same as the other widgets — see §2. |
| `cache` | integer seconds 10..3600 | `60` | Same as the other widgets — see §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Behaviour of show names wider than the 400 px widget body. |
| `link` | `underline`, `plain` | `plain` | Show-name link rendering (see the On-Air-Today widget §5 for details — same convention). |
| `bg` | URL of an image | none | Optional background image (cover-positioned) instead of the default transparent fill.  Operator hosts the image themselves — typically on the station's own site.  Cross-origin image loads work fine for CSS backgrounds. |
| `timezone` | any IANA zone | station default | All times rendered in this zone. |

> **Width.** The Weekly Schedule widget body is **400 px wide**
> (wider than the other Wave-1 widgets — it consumes more
> horizontal space per row to fit the time + name without
> truncation).  Set the iframe width to 400 in the embedding
> HTML for a flush fit.

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

## 7. Customising the empty-state labels

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

## 8. The `cache` parameter — what is the right TTL?

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

## 9. Theming

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

## 10. Authentication

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

## 11. Cross-origin embedding

Iframes work cross-origin out of the box — no extra
configuration needed. Your station's homepage can embed
the widget regardless of which host serves the homepage.

If you previously tried embedding via JavaScript snippet
and ran into CORS errors, switching to the iframe approach
(this chapter) sidesteps the problem entirely.

---

## 12. Troubleshooting

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
