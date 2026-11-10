# Delayed Show Start

> **Where you are in the manual.** This is a
> **Day-to-day broadcast operation** chapter, a companion to
> [Calendar](./CALENDAR.md). Read the Calendar chapter first — the
> single switch this feature adds lives in the **When** section of
> the New / Edit Show form, right below **Repeats?**.

Normally every show starts exactly at its calendar slot, and a show
that has **more content scheduled than fits its slot** simply has its
last track cut off at the slot end (the solid-red tip on the
[calendar fill bar](./CALENDAR.md#1-the-calendar-page)). The
following show still starts on time.

**Delayed start** changes that for shows you opt in. When the show
*before* yours overruns, an opted-in show **slides later** so the
previous show can finish, instead of the previous show being cut off.
You tick one box per show; a background task does the rest, a few
minutes before air.

> **This is opt-in and forward-only.** A show only ever slides if
> **its own** box is ticked. The slide is never undone automatically
> — see §6. If you change your mind, untick the box (future overruns
> stop sliding it) or drag the episode back on the calendar.

---

## 1. The big picture

```
   Slot:    │ Show A (1h slot) │ Show B (1h slot) │ Show C │
            08:00            09:00              10:00    11:00

   A is overbooked — its content actually runs to 09:10.

   Without delayed start (B not ticked):
            │ Show A ……✂ cut │ Show B           │ Show C │
            08:00         09:00                 10:00
            A's last track is trimmed at 09:00; B starts on time.

   With delayed start (B ticked):
            │ Show A ……………… │ Show B        │ Show C │
            08:00          09:10           10:00    11:00
            A airs in full to 09:10. B keeps its END (10:00) and moves
            its START to 09:10, so B is 50 min instead of 60 and its
            own last track may be trimmed. C still starts at 10:00.
```

Two rules make the whole feature:

1. **The overrunning show airs in full.** Show A's slot end is
   stretched to where its content actually ends (09:10), so the
   playout no longer trims A's last track.
2. **The opted-in next show keeps its END fixed and moves its
   START.** Show B now runs 09:10 → 10:00 instead of 09:00 → 10:00.
   Its scheduled items move with it; whatever no longer fits before
   10:00 is cut at the end (the same accepted trade-off as any
   overbooked show).

A show **without** the box is a hard stop: it always starts on time,
and the show before it is trimmed at its start (rule 1 does not apply
across a non-opted-in boundary).

---

## 2. Turning it on

Open **New Show** or **Edit Show** and expand the **When** section.
Directly under **Repeats?** is:

```
   When
   ─────────────────────────────
   Start  [2026-06-15] [08:00]
   …
   Repeats?               [ ]
   Allow delayed start?   [x]   ◀── tick to let THIS show slide
```

Tick **Allow delayed start?** on any show that is allowed to begin
late when the preceding show overran. Leave it unticked on shows that
must begin exactly on time (news on the hour, a network feed, a
fixed-time live link) — those become the anchors that stop a slide
(§4).

For a **repeating** show the box is part of the show definition, so it
applies to every episode. When an actual overrun shifts one episode,
only **that** episode is changed (it becomes a per-occurrence
override); the other episodes keep their normal slot.

> **How it works under the hood.** The tick is stored in the new
> `cc_show.allow_delayed_start` boolean (legacy migration 0056). It
> has no Propel accessor — the form reads and writes it via raw SQL,
> the same pattern as the song-request columns. Nothing else about
> the show changes when you tick it; the box only matters to the
> background task in §6.

### The filler playlist (Settings → General)

Since 2026-09-27 there is a second, optional switch for the whole
station: **Settings → General → Show-Shift Filler Playlist**.  Pick
one of your playlists — ideally music of assorted lengths — and the
delayed start stops cutting show tracks: the tracks that no longer
fit are swapped for filler tracks instead.  §3 explains exactly what
that does.  Leave it at *(none — cut the last track)* to keep the
plain behaviour.

---

## 3. What happens when a show overruns

When the background task sees that show A's scheduled content ends
**after** A's slot, and the next show B has **Allow delayed start**
ticked:

| | Before | After |
|---|---|---|
| **A's end** | 09:00 (slot) | 09:10 (extended to content end) |
| **B's start** | 09:00 | 09:10 (= A's content end) |
| **B's end** | 10:00 | **10:00 (unchanged)** |
| **B's items** | 09:00 … | shifted +10 min |

So A airs every track it had scheduled, and B starts right when A
actually finishes. Because B's **end stays fixed**, B is effectively
ten minutes shorter, and if B was already full its last track is
trimmed at 10:00 — exactly what would have happened to A without the
feature. The cut-off simply moves to the show that opted in to absorb
it.

> **Why keep B's end fixed?** So one overrun cannot ripple
> unboundedly into the rest of the day. B gives up its first ten
> minutes but still hands over to whatever follows at 10:00. This was
> a deliberate choice over "push B's end out too" (which would shift
> every later show). See ARCHITECTURE §23.24.

### Filler instead of a cut (since 2026-09-27)

With a filler playlist configured, the shifted show B is not simply
clamped.  Once B has moved to A's content end, the task looks at what
now sticks out past B's end and does three things:

1. **The outro stays where it belongs.**  If B ends with its outro
   playlist — the show's own *Select Outro Playlist*, or the station
   default from Settings → General — those outro tracks are pinned to
   B's end and are never touched.  The tracks *before* the outro are
   what gets replaced.  (Whether the last rows really are the outro is
   verified against the playlist's tracks, never assumed: a manually
   filled show without an outro simply has no protected tail.)
2. **Every track that no longer fits goes** — one or several, from the
   end of B's body backwards — until the remaining content fits before
   the outro (or before B's end when there is no outro).
3. **The gap is filled from the filler playlist** with the combination
   of tracks whose total length covers the gap with the least
   overshoot.  The *last* filler is clamped at the gap end.  So the
   air never falls silent, and the only track ever cut short is a
   filler — never one of B's own.  That holds even when the gap is
   shorter than the shortest filler: the shortest one plays and is
   cut.

The swap happens inside the same database transaction as the shift,
so either everything lands or nothing does.  The playout, the
Dashboard, the widgets and the track history all see the result as
ordinary schedule rows.  Only the shifted show B is treated this way;
show A's own tail is still clamped at a non-opted-in anchor (§4).

> **Example.**  B is 10:00–11:00, ends with a 30-second outro jingle,
> and A overruns by four minutes.  B now starts at 10:04.  Its last
> music track would end at 11:03:30 — it goes.  The remaining body
> ends at 10:59:10, so the gap to the outro (which must start at
> 10:59:30) is 20 seconds: the shortest filler plays and is faded out
> at 10:59:30, the outro runs in full, and whatever follows starts at
> 11:00 on the dot.

---

## 4. The cascade and the anchor

A big overrun can reach past more than one show. The delay **ripples
forward** across consecutive opted-in shows:

```
   Slot:  │ A (overbooked → 09:40) │  B  │      C      │ D │
          08:00                  09:00 09:30         10:30

   A's content runs to 09:40.

   • B (09:00–09:30, ticked)  fully buried (09:40 > 09:30)
                              → CLEARED, slot left as "skipped"
   • C (09:30–10:30, ticked)  partly buried (09:40 < 10:30)
                              → SLID to 09:40, keeps its end 10:30;
                                ripple STOPS here
   • D (10:30, …)             unaffected → starts on time at 10:30
```

A **show without the box** would instead have stopped the ripple at
its own start: it is a hard **anchor** that always begins on time, and
the overrunning content before it is trimmed at the anchor's start.

Two things can happen to each opted-in show the overrun reaches:

- **Partly buried → it slides.** If the show still has time left
  after the overrun (the overrun ends before the show's own end), it
  slides to the overrun's end, keeps its end, and the ripple **stops
  there** — that show absorbs the rest.
- **Completely buried → it is cleared.** If the overrun covers the
  show's whole slot, the show cannot air at all. Its content is
  emptied and the empty slot is left on the calendar as a **"skipped"
  marker** (§5). The ripple continues to the next show.

The ripple always ends at the **first show without the box** — the
**hard anchor**. The anchor starts exactly on time; the overrunning
content before it is trimmed at the anchor's start. So you control how
far a delay can travel simply by leaving the box unticked on the next
fixed-time show.

> **Operator tip.** Put an un-ticked anchor at every point in the day
> that must not move — the top-of-hour news, a syndicated feed, the
> start of the breakfast show. Everything between two anchors may
> slide; nothing crosses an anchor.

---

## 5. A completely-overrun show: the skipped slot

When a show is entirely buried by an earlier overrun, it is **cleared,
not deleted**:

- its scheduled items are removed (the slot's fill bar drops to 0 %),
- the empty slot **stays on the calendar** so you can see that the
  show was skipped rather than silently vanishing,
- a repeating show only has **that one episode** cleared; the series
  is untouched.

The earlier show simply plays through the skipped slot's airtime. The
marker is there for you to notice after the fact — e.g. to apologise
on air, or to tighten the overbooked show next time.

> **How it works under the hood.** Clearing a buried episode mirrors
> the **Clear Schedule** action for one episode: its `cc_schedule`
> rows are deleted, `time_filled` is zeroed, the episode is flagged
> `modified_instance` — upstream's "deleted occurrence" mark, fitting
> for a slot that never airs — plus `delayed_start_from` (since
> 2026-09-27, see below), and `cc_files.is_scheduled` is dropped for
> any track no longer scheduled anywhere.

---

## 6. When — and how often — the shift happens

The shifting is done by a background task, **not** at the moment you
save a show:

- A task (`ShowShiftTask`) runs every **2 minutes**.
- It only acts on overruns whose affected show starts within the next
  **15 minutes** (the *lead*). Far-future shows, which you may still
  be editing, are left untouched until they come close.
- It works off the **scheduled content** (`cc_schedule`), so it
  applies equally to shows you filled by hand and shows an autoloading
  playlist filled.

The task is **idempotent and forward-only**:

- Running it again changes nothing once a show already sits at the
  overrun's end — it never drifts a show further on repeat polls.
- A slide is **never undone automatically.** If you later trim the
  overbooked show so it no longer overruns, the show that already slid
  stays where it is until you move it back (drag it on the calendar)
  or the slot is regenerated. This "forward-only" behaviour was chosen
  to keep the feature simple and predictable; there is no hidden state
  remembering each show's original slot.

> **Playout history stays correct automatically.** The shift happens
> *before* air, and the playout history records what **actually**
> played and when (wall-clock), not the planned slot times. So a show
> that aired late is logged at its real airtime with no extra
> bookkeeping.

> **How it works under the hood.**
> `Application_Service_ShowShiftService::applyDelayedStarts()` selects
> overbooking episodes that are neither deleted occurrences
> (`modified_instance`) nor already shifted (`delayed_start_from`),
> whose slot end is within the lead window, then walks each one
> forward: clearing
> completely-overrun ticked shows, sliding the first partly-overrun
> ticked show (start → content end, end fixed, items shifted via
> `SchedulerService::updateScheduleStartTime`, marked
> `delayed_start_from` = the slot start it was moved away from), and
> stopping at the first un-ticked anchor.
>
> **Why its own marker (2026-09-27).**  The first live run showed the
> June design's marker — `modified_instance`, upstream's "this
> occurrence was deleted" flag — hiding the shifted show from the
> dashboard, live-info, every widget, the calendar, the show builder
> and the overlap check while the playout played it.  Migration 0058
> added `cc_show_instances.delayed_start_from`; a shifted show now stays
> visible everywhere at its new time.  Storing the original slot (not
> just a flag) also lets the repeat regenerator find the moved
> occurrence when you edit the show, instead of creating a duplicate
> at the series time.
> The overbooking show's own end is extended to where its content
> settled. Interval and lead are overridable with
> `RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` (default 120) and
> `RASTATIME_SHOW_SHIFT_LEAD_SECONDS` (default 900). See
> ARCHITECTURE §23.24.

---

## 7. Things to know

**Shows without the switch end their predecessor at the boundary
(since 2026-11-06).**  The playout takes "Allow delayed start" literally:
before a show that does *not* allow it, whatever is still playing is
ended at the show start.  The ending track's last seconds are faded out
over 0.3 s so that the new show begins exactly on its row; an overrun
of up to 0.3 s is left alone.  Before this change a predecessor could
run up to about 4.5 s into the next show.  Shows *with* the switch keep
the gentle hand-over described above.

**A show never starts early either (since 2026-11-07).**  When the
show before yours ends its last track a few seconds before your slot (an
autoloading playlist often leaves a second or three free at the end),
the playout no longer pulls your first track forward to fill the gap.
The old show fades out as usual, the gap is **silence**, and your first
track starts exactly on its row - with or without "Allow delayed start".
Gaps shorter than 0.3 s are still bridged seamlessly.


- **An already-shifted show is not itself a slide origin.** A show
  the task has moved (`delayed_start_from` set) is never treated as
  the *source* of a new ripple, and a deleted occurrence
  (`modified_instance`) is skipped entirely — but a show you simply
  dragged on the calendar is an ordinary episode and can still slide,
  be cleared, or (if it overruns) trigger a slide itself. This keeps
  the engine idempotent without fighting your manual edits, consistent
  with how
  hand-edited episodes are left alone by other automatic passes.
- **Only the next show's box matters at each step.** Whether show A
  itself is ticked is irrelevant to whether A's overrun pushes B —
  what matters is B's box. (A's box matters only when the show
  *before* A overruns into A.)
- **Autoloading can create the overrun (since 2026-10-26).**  An
  episode longer than its slot is placed in full when the next
  show has the box ticked - so the box is all it takes for such
  episodes to air completely.  Before a show without the box it is
  cut at the end (up to 5 s always, more only with "Allow last
  track to exceed time limit" in its smart block); see
  [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4.
- **A gap absorbs an overrun for free.** If there is empty time after
  the overbooked show, its content simply plays into the gap; no
  following show needs to move, and nothing is changed.

---

## 8. Operator checklist

To let a block of the schedule slide when a show overruns:

1. **Tick "Allow delayed start?"** on each show that may begin late —
   in the **When** section of its New / Edit Show form.
2. **Leave it unticked** on every fixed-time show that must start on
   the dot (news, feeds, live links). Those are your anchors.
3. That's all. A few minutes before air, an overrun in front of a
   ticked show slides it automatically; the cut-off lands on the
   ticked show instead of the overbooked one, and nothing crosses an
   un-ticked anchor.

There is nothing to configure beyond the per-show box.

---

## 9. Frequently-asked

### "I ticked the box but my show still started on time."

Then the show in front of it did not overrun (its content fit its
slot), or there was a gap that absorbed the overrun, or the overrun
was shorter than a second. The box only does something when the
previous show actually runs past its slot **into** yours.

### "My show slid later and its last track got cut."

That is the design: the slid show keeps its **end** fixed, so it is
shorter and trims its tail — the cut-off moves from the overbooked
show to the one that opted in to absorb it. Schedule a little less
content, or accept the trim.

### "A whole show was skipped — its slot is empty."

It was completely buried by an earlier overrun and was **cleared** to
a skipped-slot marker (§5). The earlier show played through its
airtime. Tighten the overbooked show, or put an un-ticked anchor
sooner so the overrun is trimmed before it reaches that show.

### "I shortened the overbooked show but the next one is still late."

Slides are forward-only (§6) — they are not walked back
automatically. Drag the slid show back to its slot on the calendar, or
wait for the slot to be regenerated.

### "How far can one overrun push the schedule?"

Up to the first show **without** the box. Everything between two
un-ticked anchors may slide; nothing crosses an anchor. Place anchors
to bound the ripple.

### "Does a late show mess up the playout history / now-playing?"

No. The shift happens before air and the history logs real airtimes,
so a late show is reported at the time it actually played.

---

## Where to go next

* [Calendar](./CALENDAR.md) — the show form, the **When** section, the
  fill bar whose red tip marks an overbooked show.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — a common way a
  show ends up overbooked (a dramaturgy that slightly overfills).
* [Show Templates](./SHOW_TEMPLATES.md) — bake "Allow delayed start"
  into a template so a whole class of shows opts in at once.
