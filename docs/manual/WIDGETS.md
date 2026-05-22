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
| **Weekly Program** | `/embed/weekly-program` | (Existing) Seven-day calendar grid view of the station schedule. |
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
every 60 seconds (configurable — see §4).

### URL parameters

| Param | Values | Default | Effect |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Text colour. `auto` follows the embedding browser's `prefers-color-scheme`. Background is always transparent. |
| `cache` | integer seconds, 10–3600 | `60` | Server-side HTTP cache TTL. Lower = fresher data + more backend hits. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | What to do with show / track names wider than the 300 px widget. `ellipsis` truncates with `…`; `marquee` scrolls left over 24 s so the operator can read the whole title. |
| `timezone` | any standard timezone (`Europe/Berlin`) | station default | All times rendered in this zone. |

> **Note.** The widget body is capped at **300 px wide** to fit
> common sidebar layouts on station websites.  Set the iframe
> width to 300 in the embedding HTML for a flush fit; a wider
> iframe will show white space around the widget.

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

## 4. Customising the empty-state labels

When there is no current or upcoming show / track, the widget
falls back to a short placeholder text.  Operators can customise
all four placeholders without touching code under:

**Settings → Widgets → Current Show/Track**

| Field | Default text |
|---|---|
| Label when no show is on air | `No show on air` |
| Label when there is no upcoming show | `No upcoming show` |
| Label when no track is playing | `No track playing` |
| Label when there is no upcoming track | `No upcoming track` |

Edits are persisted in `cc_pref` and picked up by the widget
within one cache TTL (default 60 seconds).  Leave a field blank
to fall back to the English default shown in its placeholder.

The same Settings page hosts:

- a **live preview** of both widgets side-by-side so you can
  see how a label change looks immediately after saving;
- the **ready-made `<iframe>` embed code** for each widget
  with the station's absolute URL pre-filled, ready to paste
  into the homepage HTML.

---

## 5. The `cache` parameter — what is the right TTL?

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

## 6. Theming

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

## 7. Authentication

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

## 8. Cross-origin embedding

Iframes work cross-origin out of the box — no extra
configuration needed. Your station's homepage can embed
the widget regardless of which host serves the homepage.

If you previously tried embedding via JavaScript snippet
and ran into CORS errors, switching to the iframe approach
(this chapter) sidesteps the problem entirely.

---

## 9. Troubleshooting

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

---

## Where to go next

* [Dashboard](./DASHBOARD.md) — the internal version of
  the same data, with full operator controls.
* [Streams](./STREAMS.md) — the underlying audio
  streams the widgets describe.
* [BACKLOG.md](../../BACKLOG.md) — upcoming widget waves
  (Next Shows / Latest Shows, Weekly Program enhancements,
  Track History).
