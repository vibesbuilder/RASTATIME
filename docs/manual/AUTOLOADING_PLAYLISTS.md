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
| **Repeat until full** | If on, the main playlist's items repeat (re-evaluating smart blocks each cycle) until the slot is filled minus the outro reserve. If off, the main playlist plays once and any remaining tail is silence. |

Save the show. The autoplaylist builder picks up the
attachment on its next poll (every 60 s by default) and
builds future instances accordingly.

---

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

## 4. The outro reserve (Section 23.19)

This is the operationally trickiest part of autoloading and
worth understanding.

### The problem

Suppose your **Main Playlist** uses a smart block with
*Limit to: Time remaining in show*, and you have an
**Outro Playlist** with a 60 s station ID.

Without an outro reserve, the smart-block expansion sees
"time remaining = 60 minutes" (the full show), picks 60
minutes of tracks, and the subsequent outro insert either:

- Fails because the slot is now full, or
- Pushes the outro past the slot end, causing a 60 s overbook
  that the playout will hard-cut.

### The fix

Before expanding any smart block in the main playlist, the
builder:

1. **Trial-inserts** the outro into the slot.
2. Measures its length (this is the only reliable way to
   measure smart-block-bearing playlists, whose `length`
   column stays at 0 because the blocks expand later).
3. Rolls back the trial-insert.
4. Restores any `cc_files.is_scheduled` side effects the
   trial transiently flipped to TRUE.
5. Tells the scheduler to **reserve** that many seconds from
   the slot before expanding any smart block.

So a smart block with "time remaining" now sees
*(slot total) − (outro length) − (5 s margin)* and picks
the right number of tracks. The outro then inserts cleanly
at the end.

### The 5-second margin

The reserve is capped at the measured outro length plus a
**5 s margin** (operator decision 2026-05-20, v8). Without
the margin, smart-block selection rounding would sometimes
leave a sub-second gap before the outro that the operator
heard as a tiny pause. With 5 s of slack, the auto-build
keeps slot utilisation near 100 % while never overbooking.

> **Why 5 s and not more?** Operators preferred high
> utilisation (more music, less silence) over an over-cautious
> reserve. A larger reserve (e.g. 30 s) would mean a 60-min
> show only plays 59:30 of music + 30 s of dead air before the
> outro — perceptible and unloved. See ARCHITECTURE §23.19
> for the version-by-version evolution.

### Post-build cleanup

After the body builds and the outro inserts, a final pass
trims any item whose end-time would run past the outro's
start. Items entirely inside the outro slot are left alone
(the outro plays unmodified). This catches the edge case
where smart-block rounding put the last body item half-way
past the reserve boundary.

> **How it works under the hood.** The reserve is
> `Application_Model_Scheduler::setReservedSeconds()`. The
> trim is `Application_Model_Scheduler::trimTailExcept($outroStart)`.
> Both ride inside `AutoPlaylistManager.buildAutoPlaylist()`.
> See commit ed57399.

---

## 5. Picking the right playlist for autoloading

### What works well

- **Smart-block-only playlists** with *Limit to: Time remaining
  in show*. The single most common pattern: one smart block,
  one filter ("genre = pop and bpm > 100"), one limit.
  Combined with the outro reserve this fills any slot length
  cleanly.

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
  expanded, until the slot is full minus the outro reserve.
- The cycle re-evaluates smart blocks each iteration, so a
  *dynamic* smart block picks a different selection each
  repeat — varied content within one slot.
- Track-only playlists also repeat, so the same tracks play
  again. If you want varied content, use smart blocks.

When unticked:

- The main playlist plays through once.
- Any remaining tail past the body but before the outro is
  silence.

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

Yes, but smart blocks inside intro / outro playlists do
*not* get the outro-reserve treatment — they expand as if
they had the full slot. If the intro's smart block has
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
selections in one show, put a smart block in the body that
unions two criteria sets via the smart-block OR group.

---

## Where to go next

* [Auto DJ](./AUTO_DJ.md) — the station-wide automation
  that complements per-show autoloading.
* [Show Templates](./SHOW_TEMPLATES.md) — capture the
  autoloading-playlist attachment as part of a template so
  every new show gets the same setup.
* [Library](./LIBRARY.md) → §3 Smart Blocks — the most
  powerful body-playlist primitive.
