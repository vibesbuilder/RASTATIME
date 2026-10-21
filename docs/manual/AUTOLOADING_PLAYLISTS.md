# Autoloading Playlists

> **Where you are in the manual.** Read [Library](./LIBRARY.md)
> and [Calendar](./CALENDAR.md) first — autoloading playlists
> connect a Library item (the playlist) to a Calendar item
> (the show). The distinct [Auto DJ](./AUTO_DJ.md) feature is
> *not* the same thing; see §8 for the difference.

An **autoloading playlist** is a Library playlist *attached to
a show definition* so every instance of the show is filled
from that playlist automatically. You manage the playlist once;
every Monday's show at 09:00 picks up whatever the playlist
currently holds.

This is the most powerful labour-saver in RASTATIME for
stations with regular programming. A "Morning Show" with an
autoloading playlist of smart blocks needs zero per-week
attention: edit the smart-block criteria once a season, and
the show fills itself every weekday.

---

## 1. The basics

A show with an autoloading playlist gets built **once per
instance** by the background autoplaylist builder. The build
typically happens 60 seconds before the instance starts —
just-in-time so the show reflects the very latest playlist
state.

The build sequence for each instance is:

1. (Optional) **Intro playlist** added at the start.
2. **Body playlist** items added in order; smart blocks
   expand here.
3. (Optional) **Outro playlist** added at the end.
4. If the slot still has more than 5 s of unscheduled tail
   and **Repeat until full** is on, the body repeats until
   it fills (re-evaluating smart blocks each cycle).
5. The trailing seconds past the outro slot are trimmed so
   no item runs over.

If the operator manually scheduled anything into the show
before the autoplaylist build ran, the autoplaylist build
sees the slot as already filled and does nothing.

---

## 2. Attaching an autoloading playlist to a show

Open the show on the calendar → **Edit Show** → expand
**Autoloading Playlist**.

```
   ┌─────────────────────────────────────────────────────────┐
   │  Autoloading Playlist                                   │
   ├─────────────────────────────────────────────────────────┤
   │  ☑  Add Autoloading Playlist?                           │
   │                                                         │
   │   Intro Playlist:    [Select... ▾]                      │
   │   Main Playlist:     [Select... ▾]  ◀── mandatory       │
   │   Outro Playlist:    [Select... ▾]                      │
   │                                                         │
   │  ☐  Repeat until full                                   │
   └─────────────────────────────────────────────────────────┘
```

| Field | What it does |
|---|---|
| **Add Autoloading Playlist?** | Master switch. Unticked = no auto-build. |
| **Intro Playlist** | Added at the very start of the show. Optional. Plays exactly once. |
| **Main Playlist** | The body content. Required if the master switch is on. Smart blocks inside this playlist expand at build time using the slot's remaining-seconds as the limit if configured. |
| **Outro Playlist** | Added at the very end of the show. Optional. Plays exactly once. |
| **Repeat until full** | If on, the main playlist's items repeat (re-evaluating smart blocks each cycle) while that still adds rows (strictly in order, stopping at the first item that does not fit). If off, the main playlist plays once; a tail is filled by its "time remaining" smart blocks, otherwise it is silence. |

Save the show. The autoplaylist builder picks up the
attachment on its next poll (every 60 s by default) and
builds future instances accordingly.

---

> **Repeat of show (since 2026-10-18).**  The form section right
> above, **Repeat** (its own section since 2026-10-21), carries
> **Repeat of show**: pick the original, and the content it
> aired last is copied into this show shortly before it starts; the
> autoloading playlist then fills only the remaining time.  Details in
> [Calendar](./CALENDAR.md) § 4 "Repeat of another show".

## 3. The 60-second build cadence

The autoplaylist builder runs every 60 seconds. For each
upcoming instance of an autoloading-playlist show:

- If the instance starts in **less than ~60 s** and has not
  yet been built, build it now.
- Otherwise, leave it for the next cycle.

This means the build is *always* a build of the playlist's
**current** state, not a stale snapshot. If you edit the
playlist at 08:58 for a 09:00 show, the 09:00 show gets the
edited version.

> **Operator tip.** If you need to push a same-minute edit
> (e.g. swap a track at 08:59:30 for a 09:00 show), force a
> manual build: open the show → **Clear Schedule** → close.
> The next poll cycle (within 60 s) will rebuild from the
> updated playlist.

> **How it works under the hood.** The builder is the
> `AutoPlaylistManager.buildAutoPlaylist()` static method,
> invoked by the worker job runner's `SchedulePollJob` every
> 60 s. Each cycle it walks every upcoming show with
> `cc_show_autoplaylist.has_autoplaylist = TRUE`, checks
> whether the instance's schedule is already populated, and
> builds otherwise. See ARCHITECTURE §17 for the full pipeline.

---

## 4. How the slot is filled (since 2026-10-01)

The builder fills a show in three steps, always against the
time that is **really** left in the slot:

1. The **Intro Playlist** goes to the start, exactly once.
2. The **Outro Playlist** goes to the end, exactly once — it is
   placed for real, so its length is known exactly (the
   trial-insert-and-measure of the earlier builds is gone, and
   with it the 5-second margin).
3. The **Autoloading Playlist** fills the space between the two.

Every list is taken **strictly in its order**, and it stops at
the first item that does not fit before the show's end
(operator decision, "variant a"): nothing is ever placed beyond
the end, so nothing has to be trimmed afterwards. An intro or
outro longer than the slot is cut the same way (the items that
do not fit are left out; the log says how many).

"Really left" means the laid-out time: since 2026-09-29 the
rows overlap by their crossfade (house value 3 s, or the track
type's), and the sum of the clip lengths no longer tells where
the last row ends. The builder lays the rows out with the same
pair rule the scheduler uses, so a 60-minute show with fifteen
music tracks does **not** end 42 seconds early any more.

A smart block with *Limit to: Time remaining in show* is given
that laid-out time as its budget — raised by the overlap its own
selection will make, which the builder tries several times and
keeps the closest fit. After the fill, a top-up pass runs the
playlist's "time remaining" blocks against whatever gap is
left, until the last row ends within **4 seconds** of the
show's end or nothing fits any more. In the rehearsals of
2026-10-01 the gap was 0–3 s in most runs and about 6 s at
worst (the block's solver is randomised; the pool decides what
is possible), never an overbook.

> **How it works under the hood.** `AutoPlaylistManager::fillInstance()`
> expands the playlists itself (`expandPlaylist`), plans with
> `chainEnd()` — the pair rule of `Scheduler::calculateCrossfades`
> — and inserts only the rows that fit through
> `Scheduler::scheduleFilesAfter()`. The log line
> "show_instance_id=N filled - intro a, outro b, auto c (+d top-up)
> rows, x s free at the end" sums up every build; `ap_fill_test.php`
> (C:\Temp\optd) rehearses a fill on a temporary instance.

---

## 5. Picking the right playlist for autoloading

### What works well

- **Smart-block-only playlists** with *Limit to: Time remaining
  in show*. The single most common pattern: one smart block,
  one filter ("genre = pop and bpm > 100"), one limit.
  Laid out against the real remaining time this fills any slot
  length to within a few seconds.

- **Intro + smart block + outro** for shows with a station-ID
  intro and a station-ID outro. The intro plays exactly once,
  the smart block fills the body, the outro plays exactly
  once.

- **Static playlists for short shows** under 5 minutes where
  smart blocks would be overkill. A 60 s "News Brief" show
  with three explicit clip references is fine without smart
  blocks.

### What does not work well

- **Mixing static tracks and "repeat until full" smart blocks**
  — the smart blocks will keep adding tracks even after the
  static tracks would have filled the slot. Predictable to
  the builder, surprising to the operator.

- **Webstreams or line-ins in the body** when **Repeat until
  full** is on. Webstream and line-in items have a
  configured duration (default 60 min) but the playout treats
  them as "play forever until told to stop"; the auto-builder
  sees the configured duration but the actual time consumed
  is whatever the show allows. Generally use webstreams /
  line-ins as the *whole* body, not mixed.

- **Very long playlists** (1000+ items) — the auto-build is
  fast, but you usually want a smart block over a long static
  playlist for re-evaluation each cycle.

---

## 6. Repeat-until-full behaviour

When **Repeat until full** is ticked:

- The main playlist's items are inserted, smart blocks
  expanded, and the playlist is run again while that still adds
  rows — strictly in order, stopping at the first item that does
  not fit.
- The cycle re-evaluates smart blocks each iteration, so a
  *dynamic* smart block picks a different selection each
  repeat — varied content within one slot.
- Track-only playlists also repeat, so the same tracks play
  again. If you want varied content, use smart blocks.

When unticked:

- The main playlist plays through once.
- A tail that the body leaves is filled by the playlist's "time
  remaining" smart blocks (the top-up pass runs either way);
  without such a block it stays silence.

> **Operator tip.** Always tick **Repeat until full** for a
> smart-block body. Without it, a 60-min show with a smart
> block "Limit to 10 tracks" plays ~40 min of music and 20
> min of silence before the outro.

---

## 7. Removing an autoloading playlist

Edit the show → expand **Autoloading Playlist** → untick
**Add Autoloading Playlist?** → Save.

Future instances will no longer auto-build. Already-built
instances keep their built content (no retroactive change).
To clear an already-built instance, open the show on the
calendar → **Clear Schedule**.

---

## 8. Autoloading playlists vs Auto DJ

These two features are easy to confuse. Quick reference:

| | Autoloading Playlist | Auto DJ |
|---|---|---|
| **Where attached** | A specific show's edit form | Settings → Auto DJ (station-wide) |
| **When it fills** | Per show instance, 60 s before start | (a) Creates new shows in calendar gaps. (b) Tops up incomplete upcoming shows. |
| **What it fills with** | The configured playlist (any structure) | One configured Auto-DJ playlist |
| **Affects which shows** | Only the show it is attached to | All shows + creates new ones |
| **Needs a host?** | No | No |
| **Disabled by default** | Yes | Yes |

Use autoloading playlists for **regular programming** (the
Morning Show always uses the Morning Playlist). Use Auto DJ
for **unplanned airtime** (whatever you forgot to schedule,
the Auto DJ catches).

See [Auto DJ](./AUTO_DJ.md) for the full feature.

---

## 9. Frequently-asked

### "I attached a playlist but the show stayed empty."

Three possibilities:

1. The instance has already started — the auto-build only
   touches *future* instances.
2. The instance was already manually filled. The auto-build
   skips any show that already has scheduled items.
3. The worker job runner is not running. Check
   `Get-Service RASTATIME-WORKER`.

### "How do I see if the auto-build ran for a specific instance?"

Open the show on the calendar; the calendar fill bar should
be > 0 %. If it is 0 % seconds before start time, the
auto-build has not yet run. Wait 60 s and reload, or use
**Clear Schedule** + reopen to force the next poll cycle to
treat the instance as fresh.

### "Can the intro playlist contain a smart block?"

Yes, but the intro is placed first, against the whole free
slot, and the outro right after it. If the intro's smart block has
"time remaining" limit, it will gobble the whole show. Use
fixed-duration smart blocks ("Limit to 30 s") or static
tracks for intro / outro.

### "Why does the auto-build sometimes pick the same track twice?"

If the body playlist uses **Repeat until full** with a
static playlist, the same tracks repeat. To avoid this,
either:

- Use a smart block with type **Dynamic** so each repeat
  re-queries.
- Set "Sort: Random" inside the smart block so each repeat
  picks a different random ordering.

### "Can I have two autoloading playlists on one show?"

No. The model is **intro + body + outro**, and only the body
is the "main" autoloading playlist. To get two distinct
selections in one show, put two smart blocks — one per
selection — into the body playlist. A single smart block can
only offer alternatives of the same field (e.g. genre Jazz or
Blues); see [Import/Export → blocks.json](./IMPORT_EXPORT.md#blocksjson).

---

## Where to go next

* [Teaser Automation](./TEASERS.md) — the smart block
  criterion that puts the right "today" / "tomorrow" jingles
  into the intro, outro and content playlists.
* [Auto DJ](./AUTO_DJ.md) — the station-wide automation
  that complements per-show autoloading.
* [Show Templates](./SHOW_TEMPLATES.md) — capture the
  autoloading-playlist attachment as part of a template so
  every new show gets the same setup.
* [Library](./LIBRARY.md) → §3 Smart Blocks — the most
  powerful body-playlist primitive.
