# Song Requests

> **Where you are in the manual.** Read [Library](./LIBRARY.md)
> → §3 Smart Blocks and
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) first — song
> requests are built entirely from those two primitives plus a
> public listener widget. No new "request" object type is
> introduced.

**Song requests** let your listeners ask for tracks from a public
web widget, and have those tracks air automatically inside a normal
show — without a host clicking anything. The whole feature is
assembled from pieces you already know:

- a **smart block** marked *Use requests* draws the tracks listeners
  actually asked for;
- an **autoloading playlist** containing that block turns an ordinary
  show into a **request show**;
- a small **embed widget** on your public website collects the
  requests.

There is no per-show "accepts requests" switch and no separate
request queue to moderate. A show *is* a request show when its
autoload playlist contains a *Use requests* block — nothing else.

---

## 1. The big picture

```
   LISTENER                 RASTATIME                     ON AIR
   ┌─────────┐   request    ┌──────────────────────┐
   │ Widget  │─────────────▶│ rastatime_song_request│
   │ (iframe)│   /api/v2    │  status = pending     │
   └─────────┘              │ cc_files.requested=t  │
                            └──────────┬────────────┘
                                       │  request show fills
                                       │  incrementally, on air
                            ┌──────────▼────────────┐   ┌──────────┐
                            │ "Use requests" block   │──▶│  Show    │
                            │  draws pending requests │   │ schedule │
                            │  oldest-first, 1 each   │   └──────────┘
                            └────────────────────────┘
```

Two independent halves meet in the middle:

1. **Listeners** open the widget, see the catalogue of requestable
   tracks, and submit a request. The request is recorded and the
   track is flagged as "wanted".
2. **A request show** — any show whose autoload playlist contains a
   *Use requests* smart block — fills itself from those wanted tracks
   incrementally as it airs, so a request made during the show can
   still play in it.

The two halves are linked only by the request **pool** (§2) and the
*Use requests* criterion (§3). You configure them once; after that
the feature runs unattended.

---

## 2. The request pool — what listeners may ask for

The **pool** is the catalogue of tracks a listener is allowed to
request. It is defined by one or more smart blocks.

Open **Settings → General → Song-Request Pool (Smart Blocks)**. The
field is a dropdown styled like the Library *Columns* picker: click
**Smart Blocks**, tick one or more blocks, click elsewhere to close.

```
   Song-Request Pool (smart blocks)   [ Smart Blocks ▾ ]
                                      ┌────────────────────┐
                                      │ ☑ Indie / Alt pool │
                                      │ ☐ Jingles          │
                                      │ ☑ Request catalogue│
                                      │ …                  │
                                      └────────────────────┘
```

The pool is the **union** of every ticked block's catalogue — the
tracks each block's criteria match (genre, album, …), *ignoring*
whether they have been requested yet. Tick none to disable song
requests entirely: the widget then shows "currently unavailable".

> **How it works under the hood.** A background task
> (`RequestablePoolSyncTask`, every 5 min) expands the union of the
> selected blocks with the request filter *ignored* and writes
> `cc_files.requestable = true` for every member, clearing it for
> everything else. The public catalogue-search endpoint filters on
> that flag. The selected block ids live in the cc_pref key
> `requestable_pool_block_ids`.

---

## 3. The "Use requests" smart block

A smart block becomes a **request source** when you tick **Use
requests** in the Smart Block dialog (Library → edit a smart block →
advanced criteria).

This changes what the block draws:

| State | What the block selects |
|---|---|
| **Use requests OFF** (normal) | All tracks matching its criteria (genre, album, …). |
| **Use requests ON** | Only tracks matching its criteria **and** with an open listener request (`cc_files.requested = true`). |

Two sort orders are available and matter for request blocks:

- **Oldest request first** — fair queue: whoever asked earliest airs
  first.
- **Most requested first** — popularity: the track with the most
  pending requests airs first.

> **Operator tip.** The *same* block usually plays both roles: you
> select it as the **pool** in Settings (which uses its catalogue,
> request filter ignored) *and* place it in a request show's playlist
> (where the *Use requests* criterion makes it draw the actual
> requests). Keep its catalogue criteria (e.g. `genre = Indie or
> Alternative`) sensible — they limit **both** what may be requested
> and what is drawn.

---

## 4. Building a request show

A request show is just an [autoloading-playlist](./AUTOLOADING_PLAYLISTS.md)
show whose playlist contains at least one *Use requests* block. You
compose the playlist as a **dramaturgy** — a fixed running order the
fill walks through once:

```
   Autoload playlist "Request Hour"
   ─────────────────────────────────
   1. Smart block · Use requests · 1 item   ◀── request A
   2. Smart block · StationID    · 1 item
   3. Smart block · Use requests · 1 item   ◀── request B (different!)
   4. Smart block · StationID    · 1 item
   5. Smart block · Use requests · 1 item   ◀── request C (different!)
   6. Smart block · Music · Limit "time remaining in show"  ◀── fills the rest
```

When the show fills (§5), each *Use requests* slot draws a
**different** request, and the trailing **time-remaining** block
fills whatever is left with music. Attach the playlist to a show the
normal way (**Edit Show → Add Autoloading Playlist?**), and that
show is now a request show.

> **You may reuse one block.** Putting the *same* *Use requests*
> block at positions 1, 3 and 5 works — the fill resolves each
> position on its own, so three placements draw three different
> requests. You do not need three separate blocks.

> **Why a trailing "time remaining" block.** Without a block that
> fills the remainder, a request show with only a handful of pending
> requests would leave dead air after the last request. The
> time-remaining music block is the safety net. Give it
> **Repeat tracks = yes** (or a large enough catalogue) so it fills
> the whole remainder in one pass; with repeat off it fills with as
> much variety as its pool allows and may leave a small gap that the
> playout's own fallback covers.

---

## 5. How and when a request show fills

A request show fills itself **incrementally while it is on air** — its
dramaturgy is resolved a little ahead of the play head, not all at once
before the show starts. That is what lets a request submitted *during*
the show still air in it.

- A background task (`RequestShowFillTask`, every 2 min) starts on a
  request show when it enters a **lead** window
  (`RASTATIME_REQUEST_FILL_LEAD_SECONDS`, default 8 min before start)
  and keeps processing it while it is on air.
- It walks the playlist **position by position**, but resolves
  positions only a short way **ahead of the play head**
  (`RASTATIME_REQUEST_FILL_AHEAD_SECONDS`, default 5 min). After each
  slot it takes the drawn request out of the pool, so the **next**
  *Use requests* slot draws a different track.
- A per-show cursor remembers how far the dramaturgy has been resolved,
  so the next poll continues instead of re-filling from the start. A
  *Use requests* block later in the dramaturgy is therefore resolved
  only when its slot is about to play — drawing the requests that
  arrived **since the show went on air**.
- Once the dramaturgy is exhausted, the trailing time-remaining block
  fills the rest of the show **completely** to the end.

This stays **dead-air-safe**: the show is always filled ahead of the
play head (the fill-ahead window comfortably exceeds the 2-min poll),
and the long music tail is filled completely as soon as the dramaturgy
is placed.

> **Where late requests land.** A request airs in the running show **if
> a *Use requests* slot is still ahead of the play head** when it
> arrives. Spread your request slots through the dramaturgy rather than
> front-loading them: a request submitted at minute 20 needs a request
> slot that plays *after* minute 20. A request that arrives after the
> last request slot of a show has already been resolved lands in the
> next request show.

> **Empty request slot → random track.** If a *Use requests* slot
> has no pending request at fill time, it does **not** leave a hole.
> It airs a **random** track from that block's own catalogue (its
> genre/criteria, request filter ignored). So a request show with
> zero requests still plays a normal, on-format hour; as requests
> come in, they replace the random picks slot by slot.

> **Freshness vs. dead-air safety.** `RASTATIME_REQUEST_FILL_AHEAD_SECONDS`
> is the lever: smaller resolves each slot closer to its play time
> (fresher requests) but leaves a thinner buffer ahead of the play head;
> larger resolves slots earlier (safer). Keep it above the 2-minute poll
> interval.

> **How it works under the hood.** `AutoPlaylistManager::`
> `fillRequestShows()` processes instances already on air (not yet
> ended) as well as imminent ones. `_fillRequestShowByPositions()`
> resolves `cc_playlistcontents` from the persisted
> `cc_show_instances.autoplaylist_cursor` up to `now +`
> `RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (default 300), appending each
> file/block with `addAutoloadItemToShow()` and consuming on schedule
> between slots, then saves the cursor so the next poll continues. The
> backend playout (pypo) picks the mid-show append up at its start time,
> so no playout change is needed. The normal autoplaylist builder
> deliberately **skips** request shows. See ARCHITECTURE §23.23.

---

## 6. The listener widget

The public widget lives at:

```
   http://<your-station>/Embed/song-request
   http://<your-station>/Embed/song-request?theme=dark
```

Embed it in an `<iframe>` on your website (themes: `light`, `dark`,
`auto`). It shows a scrollable table of every requestable track —
cover · artist / title · a **Request** button — with no search box
and no pagination:

```
   ┌──────────────────────────────────────────────┐
   │ [cover] Robb — Down with It          [Request]│
   │ [cover] Leyya — Butter               [Request]│
   │         Viech — Steuermann           [Request]│
   │ …                                             │
   └──────────────────────────────────────────────┘
```

A click posts the request and shows a status line: thanks, "already
requested recently", or "request limit reached".

Built-in guardrails (no moderation queue needed):

| Guardrail | Default |
|---|---|
| **Rate limit** | 5 requests per hour per listener |
| **De-duplication** | the same listener cannot re-request the same track within 30 min |
| **Catalogue restriction** | only pool tracks (§2) are listable / requestable |

> **Covers need the 3rd-party API.** The cover thumbnails come from
> the track-artwork endpoint, which is gated by **Settings → … →
> Allow 3rd party API**. With it off, the table renders text-only
> (artist / title), which is perfectly usable. Tracks that simply
> have no artwork stay text-only too.

> **How it works under the hood.** The widget is a self-contained
> vanilla-JS iframe page (`/Embed/song-request`) talking to two
> public Django endpoints: `GET /api/v2/song-requests/search`
> (the catalogue) and `POST /api/v2/song-requests` (submit). No
> login, no cookie. The raw listener IP is never stored — only a
> salted hash, used for rate-limiting and de-duplication.

---

## 7. The request lifecycle

Every request moves through four states:

| State | Set when | Means |
|---|---|---|
| **pending** | listener submits it | waiting in the pool to be drawn |
| **queued** | the fill schedules its track | drawn into a show; out of the pool |
| **played** | the track has aired | done (kept for history) |
| **expired** | TTL passed un-aired | never drawn; swept from the pool |

- When a request is **scheduled**, its track leaves the pool
  (`cc_files.requested` cleared) so the next slot draws something
  else, and the request becomes **queued**.
- A schedule-based task marks **played** once the track's slot has
  passed (`RequestPlayedTask`, every 2 min) — chosen over a
  playout-side hook so the live broadcast path is never touched.
- If a **request show is deleted** before its tracks air, its scheduled
  requests are not stranded: the same sweep returns them to **pending**
  (their track is no longer in any schedule), so the next request show
  retries the wish.
- The expiry sweep (`RequestExpiryTask`, every 10 min) expires any
  request still **pending** after the TTL — default **8 hours**,
  override with `RASTATIME_REQUEST_EXPIRY_HOURS` — and recomputes the
  pool aggregate so a track whose last request expired drops out of
  the catalogue cleanly.

---

## 8. Operator checklist

To stand up song requests from scratch:

1. **Make a request smart block.** Library → new smart block →
   set its catalogue criteria (e.g. `genre = Indie or Alternative`),
   tick **Use requests**, set **Sort: Oldest request first**,
   **Limit: 1 item**. Save.
2. **Select it as the pool.** Settings → General → **Song-Request
   Pool** → tick the block. (Within 5 min its tracks become
   requestable.)
3. **Compose the dramaturgy playlist** (§4): your request block at a
   few positions, jingles/IDs between, a **time-remaining** music
   block last (with **Repeat tracks = yes**).
4. **Attach it to a show** as an autoloading playlist (§4).
5. **Embed the widget** (§6) on your website, optionally enable
   **Allow 3rd party API** for cover art.

That is the whole setup. From then on, listeners request, and the
show fills itself incrementally as it airs — picking up requests that
arrive while it is on the air, as long as a request slot is still
ahead of the play head.

---

## 9. Frequently-asked

### "The widget shows no tracks."

The pool is empty. Either no block is selected in **Settings →
Song-Request Pool**, or the selected block's criteria match nothing,
or the 5-minute pool-sync has not run yet. Check the block in the
Library shows tracks; wait one sync cycle.

### "My request show aired but played no requested tracks."

Most likely there were no *open* requests at the moment each *Use
requests* slot was resolved (a few minutes before that slot played),
so it fell back to a random catalogue track (§5). Submit a request
while a request slot is still ahead of the play head and it will be
drawn; otherwise it airs in the next request show. Also confirm the
playlist's request block has **Use requests** ticked and its criteria
match the requested tracks' genre.

### "Several request slots played the same song."

That should not happen — the fill consumes each request as it
schedules it, so successive slots draw different tracks. If you see
duplicates, the playlist is probably appending the *whole* playlist
repeatedly via the old behaviour; make sure you are on a build with
position-by-position fill (ARCHITECTURE §23.23).

### "There is dead air at the end of a request show."

The trailing time-remaining block ran out of eligible tracks. Give
it **Repeat tracks = yes**, widen its genre criteria, or relax any
*exclude artists played lately* window so it can fill the full
remainder.

### "Requests appear after the show already started — do they air?"

Yes — if a *Use requests* slot is still ahead of the play head when
the request arrives. The show fills **incrementally** (§5), so a slot
resolved later in the dramaturgy draws requests that came in while the
show was on air. A request that arrives after the show's last request
slot has already been resolved airs in the next request show — so
spread the request slots through the dramaturgy to give late requests
a slot to land in.

### "Can I moderate requests before they air?"

There is no moderation queue by design. The guardrails are the pool
restriction (only catalogue tracks), the rate limit and the
de-duplication window (§6). If you need tighter control, narrow the
pool block's criteria.

---

## Where to go next

* [Library](./LIBRARY.md) → §3 Smart Blocks — the *Use requests*
  criterion and sort orders live here.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — the
  dramaturgy playlist and its trailing time-remaining fill block.
* [Public Embed Widgets](./WIDGETS.md) — embedding the request
  widget alongside the other public widgets.
* [Settings](./SETTINGS.md) — the Song-Request Pool picker and the
  Allow-3rd-party-API toggle.
