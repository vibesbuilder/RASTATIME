# Traffic Alerts

> **Where you are in the manual.** Read [Library](./LIBRARY.md)
> → §3 Smart Blocks and
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) first, and ideally
> [Song Requests](./SONG_REQUESTS.md) — traffic alerts reuse the *same*
> incremental, on-air fill mechanism. No new object type is introduced.

**Traffic alerts** let a short-notice MP3 — a traffic bulletin handed to
you minutes before it must air — play inside the **running show**,
automatically, within about ten minutes, without a host clicking
anything and without interrupting the playout engine.

The whole feature is assembled from pieces you already know:

- a **smart block** that matches your traffic bulletins is named, once,
  as the **traffic source** in Settings;
- an **autoloading playlist** that contains that block, placed at a few
  points in a show, turns an ordinary show into a **traffic-aware show**;
- importing a new bulletin into the library is all it takes to put it on
  air at the next traffic slot.

There is no separate "alert queue" and no playout-side change. A show
*becomes* traffic-aware when its autoload playlist contains the
configured traffic block — nothing else.

---

## 1. The big picture

```
   NEWSROOM                 RASTATIME                       ON AIR
   ┌──────────┐  import     ┌────────────────────────┐
   │ traffic  │────────────▶│ Library: the file now   │
   │  .mp3    │             │  matches the traffic blk │
   └──────────┘             └───────────┬─────────────┘
                                        │  the running show fills
                                        │  incrementally, on air
                            ┌───────────▼─────────────┐   ┌──────────┐
                            │ Traffic-Alert block at   │──▶│  Show    │
                            │  the NEXT dramaturgy slot │   │ schedule │
                            │  oldest-first, aired once │   └──────────┘
                            └──────────────────────────┘
```

The mechanism is the one Song Requests already use (see
[Song Requests](./SONG_REQUESTS.md) §5): a traffic-aware show is filled
**incrementally as it airs**, only a little ahead of the play head.
Each traffic slot in the show is resolved shortly before it plays — so
it picks up whatever bulletins were imported in the meantime. A bulletin
imported *during* the show therefore airs at the **next** traffic slot;
nothing already scheduled is pushed back.

You configure the source once (§2–§3) and place the block in your shows
(§4); after that the feature runs unattended (§5).

---

## 2. The traffic smart block

A traffic bulletin is just an audio file. The "traffic block" is an
ordinary [smart block](./LIBRARY.md) whose criteria match those files
and nothing else. Typical setup:

- **Criteria** that select only bulletins — for example *Genre is
  Traffic*, or *Folder/Path contains `/traffic/`*, whatever cleanly
  isolates them in your library.
- **Sort: Newest first** is natural, but the airing order does not
  depend on it — the system always airs the **oldest un-aired** bulletin
  first (the one closest to its deadline; see §5).
- **Exclude tracks played lately** (optional, recommended): once a
  bulletin has aired it drops out of the block, so a stale bulletin is
  never picked up again on a later day.
- **No tight item limit.** Leave room for several bulletins so that if
  two arrive close together, both are candidates.

> **Tip.** Keep this block dedicated to traffic. Do not reuse a music
> block — every file the block matches is treated as an airable
> bulletin.

---

## 3. Select it in Settings

Open **Settings → General Preferences** and find **Traffic-Alert Smart
Block**. Choose your traffic block from the list and save.

- The list holds every smart block in your library.
- **`(none — disabled)`** is the default and turns the feature off
  completely — a show that still contains the block then just plays it
  once as an ordinary block.

Only **one** block can be the traffic source at a time. This is the
single switch that arms the feature.

---

## 4. Building a traffic-aware show

Add the traffic block to a show's **autoloading playlist**, the same way
you would add any block — but place it at **several points** along the
show's dramaturgy, not just once. For example:

```
   jingle · music · TRAFFIC · music · music · TRAFFIC · music · …
```

Each `TRAFFIC` entry is a slot where a bulletin *may* interrupt. If no
bulletin is waiting when the slot is reached, the slot airs nothing and
the next item simply plays — so empty slots cost you nothing.

**How densely to place them is how you meet the ten-minute deadline**
(see §6). As a rule of thumb, a traffic slot every five to seven minutes
of programme, with no very long track immediately before one, keeps any
bulletin comfortably inside its SLA.

The show needs **Autoloading playlist** enabled (it is what makes the
show fill itself). Nothing else on the show needs special settings.

---

## 5. How and when a bulletin airs

When a traffic-aware show is on air, the fill task (every two minutes)
resolves its dramaturgy a little ahead of the play head. When it reaches
a traffic slot it picks **one** bulletin, by these rules:

1. **Oldest first (FIFO).** Among the waiting bulletins it airs the one
   **imported earliest** — the one closest to its ten-minute deadline.
2. **Aired once.** A bulletin already scheduled anywhere in this show is
   never picked again, so the same alert cannot air twice even though
   the block sits at several slots.
3. **No filler.** If no fresh bulletin is waiting, the slot airs
   **nothing** — there is deliberately no random-track fallback (unlike a
   request slot). The following programme item plays instead.

So the normal day-to-day workflow is simply: **import the bulletin into
the library** (into the folder/genre your block matches). Within a poll
cycle it becomes a candidate, and it airs at the next traffic slot of the
running show.

> **Under the hood.** Traffic alerts and song requests share one
> incremental fill engine. The only difference is how a slot resolves:
> a request slot draws listener requests and falls back to a random
> track; a traffic slot draws the oldest un-aired bulletin and falls
> back to *nothing*. Both write into the normal show schedule, which the
> playout engine picks up on its next refresh — there is no change to the
> live audio path, and the bulletin shows up in history and the calendar
> like any track.

---

## 6. The ten-minute deadline is yours to hold

Because a bulletin airs at its **dramaturgy slot**, how quickly it airs
depends on how you built the show — not on the system cutting into a
track. RASTATIME does **not** skip the currently-playing track to rush a
bulletin out (that automatic *deadline-skip* is a planned future option,
held back until live operation shows it is actually needed).

You hold the SLA with two habits:

- **Place traffic slots densely** — no more than your deadline apart, so
  the next slot is always near.
- **Keep the track before a slot short.** A fifteen-minute mix right
  before a traffic slot can by itself push the slot past ten minutes.

If your programming genuinely cannot guarantee a slot within the
deadline (very long-form shows, say), tell your RASTATIME maintainer —
the active deadline-skip can then be built and enabled.

---

## 7. Operator checklist

1. **Once:** build a smart block that matches only your traffic
   bulletins (§2).
2. **Once:** Settings → General → **Traffic-Alert Smart Block** → select
   it (§3).
3. **Per show:** add that block at several points in the show's
   autoloading playlist, ≤ your deadline apart (§4).
4. **Each bulletin:** import the MP3 into the library so it matches the
   block — it airs at the next slot (§5).
5. **To pause the feature:** Settings → set the block back to
   `(none — disabled)`.

---

## 8. Frequently-asked

### "I imported a bulletin but it didn't air."
Check three things: the file actually **matches the traffic block**
(open the block and confirm it appears); the **block is selected** in
Settings; and the **running show contains the block** in its autoload
playlist. If all three hold, it airs at the next traffic slot — which may
be a few minutes away depending on your dramaturgy (§6).

### "The same bulletin aired twice."
It should not — a bulletin already scheduled in the show is excluded from
later slots. If it genuinely repeated, the two airings are in *different
shows* (a new show's slots see it as fresh until it has actually played;
enable *Exclude tracks played lately* on the block to stop that).

### "A traffic slot played nothing."
That is expected when no fresh bulletin was waiting — a traffic slot has
no filler, so the next programme item just plays. Empty slots are free;
place as many as you like.

### "Two bulletins arrived at once — which airs first?"
The **oldest import** first, then the next at the following traffic slot.
Each slot airs one bulletin, so give them enough slots to drain.

### "How fast will a bulletin air?"
At the next traffic slot of the running show. With slots placed within
your ten-minute deadline and no over-long track in front of one, that is
inside the SLA. RASTATIME does not interrupt the current track to do it
(§6).

### "Can I turn it off?"
Yes — Settings → **Traffic-Alert Smart Block** → `(none — disabled)`. A
show that still carries the block then simply plays it once as an
ordinary block.

---

## Where to go next

- [Song Requests](./SONG_REQUESTS.md) — the same incremental on-air fill,
  for listener requests.
- [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — how a show fills
  itself from playlists and blocks.
- [Library](./LIBRARY.md) → §3 Smart Blocks — building the block that
  matches your bulletins.
