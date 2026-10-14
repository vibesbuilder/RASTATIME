# Calendar

> **Where you are in the manual.** This is one of the
> **Day-to-day broadcast operation** chapters. Many other
> chapters in the manual end with "drag from the library onto
> a show in the calendar" — this is the chapter that explains
> the receiving side. Read [Library](./LIBRARY.md) first if you
> have not yet.

The **Calendar** is where you plan what goes on air. Every
slot of broadcast time is either:

- A **show** you put on the calendar, or
- Air the [Auto DJ](./AUTO_DJ.md) fills (when enabled), or
- The configured fallback / silence (when neither of the above
  applies).

This chapter covers everything you can do *with* the calendar.
What plays *inside* a show — tracks, smart blocks, playlists —
is covered in [Library](./LIBRARY.md) and per-feature chapters.

---

## 1. The Calendar page

Calendar → opens the week view by default.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ◀ Today ▶              May 18 – 24, 2026             [day][week][month] │
  ├──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
  │      │   Mon 18 │   Tue 19 │   Wed 20 │   Thu 21 │   Fri 22 │   Sat 23 │
  ├──────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
  │ 08   │■ Morning ■        │■ Morning  │■ Morning  │■ Morning  │          │
  │      │■ Show    ■        │■ Show     │■ Show     │■ Show     │          │
  │ 09   │           │           │           │           │           │          │
  │ 10   │■ Music    │           │           │■ News     │■ Music    │          │
  │      │■ Hour     │           │           │■ Brief    │■ Hour     │          │
  │ 11   │           │           │           │           │           │          │
  │      │           │           │           │           │           │          │
  └──────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Switching views

| Button | What you see |
|---|---|
| **Day** | One day, hour rows, large gaps for empty slots. Best for "what is on today" planning. |
| **Week** | Seven days, default. Best for weekly programme planning. |
| **Month** | A month grid, shows shown as coloured bars across days. Best for "is the week of X full?" overview. |

The arrow buttons step by the visible range (one day / one week
/ one month at a time). The **Today** button jumps back to the
current period.

### What the colours mean

Each show carries its own background colour and text colour
(set on the show's edit form). Use this to:

- Distinguish recurring shows from one-offs (e.g. all recurring
  shows on a dark background).
- Highlight programmes by genre (news = red, music = blue,
  community = green).
- Mark special programming (live remote = yellow).

The colour has no functional meaning — it is purely visual.

### The per-show fill bar

Inside each show block is a thin horizontal bar at the bottom.
It shows the **fill level** — what percentage of the show's
duration is actually scheduled.

| Fill bar | Meaning |
|---|---|
| (empty) | 0 % scheduled — the show will fall through to fallback / silence |
| Half-filled | About half the duration is scheduled |
| Full | 100 % — every second of the show has content |
| Solid red tip | Over 100 % — items would have run past the slot end and were trimmed |

> **Operator tip.** The fill bar refreshes automatically every
> 60 seconds, so when an [Autoloading
> Playlist](./AUTOLOADING_PLAYLISTS.md) builds a show in the
> background you can watch the bar move from empty to full
> without reloading the page. Pre-2026-05-20 you had to
> reload manually; this was fixed in 9484db6.

> **How it works under the hood.** The bar's percentage is
> `cc_show_instances.time_filled / (ends_at − starts_at)` ×
> 100, fetched via the `/Schedule/event-feed` JSON endpoint.
> The 60 s refresh is `setInterval(refetchEvents, 60_000)` in
> `full-calendar-functions.js`, gated on
> `$cal.is(":visible")` so the AJAX poll pauses when the
> operator is on a different tab.

> Since 2026-10-06 `time_filled` is the laid-out length (show start to
> the end of the last row, crossfade overlaps included), so a show the
> bar calls full really is full.

---

## 2. Creating a show

Two routes:

### 2.1 From the calendar grid

Click any empty cell on the calendar.

- Single click on a **week** or **day** view cell opens
  **New Show** at that hour.
- Single click on a **month** view day opens **New Show** at
  that day's 09:00.
- Right-click any empty cell shows a context menu with
  **New Show** + **Apply Template**.

### 2.2 From the toolbar

Calendar → **+ New Show** in the top-right of the page.
Defaults to "now + 1 hour" with a 60 minute duration.

### The New-Show form

The form is divided into collapsible sections. **What** and
**When** are mandatory; the rest can be left at defaults.

| Section | Purpose |
|---|---|
| **Templates** | Pre-fill the form from a saved [Show Template](./SHOW_TEMPLATES.md), or save the current form as a template after you finish. Hidden when editing a single instance of a repeating show. |
| **What** | Name, URL, genre, description, hosts, background / text colours, show image. The visible label on the calendar. |
| **When** | Start date / time, duration, end date, repeats, **Allow delayed start** (let this show begin late when the previous one overran — see [Delayed Show Start](./DELAYED_START.md)). |
| **Live Stream Input** | Allow remote hosts to take the show via Show DJ (per-show username + password). |
| **Record** | Tick to record the show's on-air output to a file. See [Record-per-Show](./RECORD_PER_SHOW.md). |
| **Autoloading Playlist** | Attach a playlist to fill every instance automatically. See [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md). |
| **Who** | Additional hosts beyond the primary one set under What. |
| **Style** | Background colour, text colour, show image (visible only here for one-off shows; for recurring shows these stay constant across instances). |

> **Operator tip.** If you are about to fill in the same name,
> hosts, colours, and autoloading playlist as last week, stop
> and check the **Templates** dropdown first. If the template
> exists, picking it pre-fills six of the seven sections in
> one click. If it does not, create it now via the **Save as
> Template** button at the bottom of the section.

### Why the form rejects your save

Common reasons:

| Error | Cause |
|---|---|
| "Cannot schedule overlapping shows." | Another show already occupies one or more seconds of the slot. RASTATIME does not allow overlapping shows. |
| "Start time must be in the future." | One-off shows must start at least 1 minute from now. |
| "End time must be after start time." | Self-explanatory; check duration and end date. |
| "You are not allowed to schedule show *X*." | You picked another DJ as host but you are not an Admin. DJs can only set themselves as host. |

If the form rejects with a generic "Save failed" toast and no
visible per-field message, check the operator log
(`C:\rastatime\logs\error.log`). RASTATIME 2026-05-17 added
diagnostic logging for the sub-form pass/fail state so
"validateShowForms FALSE: what=1 when=0 …" should appear,
pointing at the offending sub-form.

---

## 3. Editing an existing show

Click the show → context menu → choose an action.

### Action menu

| Action | Effect | Available when |
|---|---|---|
| **Schedule Tracks** | Open the show-builder to add / remove / re-order items. | Always |
| **Apply Template** | Stamp a [Show Template](./SHOW_TEMPLATES.md) onto this show; replaces the form fields. | Future shows only |
| **Save as Template** | Save the current show settings as a new template. | Always |
| **View** | Read-only view of the show's metadata + schedule. | Always |
| **Edit Show** | Edit the show definition (name, time, repeats, etc.). | Future or current shows |
| **Edit Instance** | Edit only this one occurrence of a recurring show. | Recurring shows only |
| **Cancel Show** | End the show *now* — only meaningful for the currently-playing show. | Current show only |
| **Delete Show** | Remove the entire show + all its instances. | Future shows only |
| **Delete this instance** | Remove only this one occurrence of a recurring show. | Recurring shows, future only |
| **Clear Schedule** | Wipe the show's scheduled content but keep the empty slot. | Future shows only |

> **Why "Edit Show" vs "Edit Instance".** A weekly show is one
> *definition* with many *instances*. Editing the definition
> changes every future instance (e.g. moving the show from
> Mondays to Tuesdays). Editing a single instance creates a
> per-occurrence override (e.g. this one week, the host is
> different). The instance override survives the next
> definition edit but does not propagate to siblings.

### What "Edit Instance" cannot do

- Cannot apply a Show Template. Templates only apply to entire
  shows because stamping a template onto one instance would
  either silently propagate to siblings (violating the one-way
  stamp model) or have no effect on them (which would mislead
  the operator). RASTATIME 2026-05-19 suppresses the Templates
  section in the Edit-Instance form for this reason.
- Cannot change the start/end of the instance to a time outside
  the parent show's repeat pattern.

---

## 4. Recurring shows

A recurring show is one definition with many instances eagerly
materialised out to a configurable horizon (default ~3 months).

### Creating a recurring show

In the **When** section, tick **Repeats**. Three sub-fields appear:

| Field | Meaning |
|---|---|
| **Repeat Type** | Weekly / Bi-Weekly / Tri-Weekly / Monthly. |
| **Select Months** (since 2026-10-14) | Monthly repeats only: tick the months in which the show takes place, all twelve by default. Untick July and August for a summer break, or keep every third month for a quarterly show. Combined with *Repeat By* (day of the month / day of the week). Deselecting a month on an existing show removes its future instances in that month. |
| **Days** | Which days of the week (for Weekly / Bi-Weekly / Tri-Weekly). |
| **End Date** | Optional — when the recurrence stops. Leave blank to recur indefinitely. |

> **Operator tip.** A monthly show that recurs "on the third
> Friday" is *not* directly supported. The closest is "weekly,
> Friday, but linked to a 4-week cycle" — easier to schedule
> the four monthly occurrences as one-off shows.

### Editing a recurring show

- **Edit Show** changes the definition: every future instance
  picks up the change. Past instances stay as they were.
- **Edit Instance** creates a per-occurrence override (see
  above).
- **Delete this instance** removes only that one occurrence.
- **Delete Show** removes the entire series including all
  future instances.

> **How it works under the hood.** Recurring shows write one
> `cc_show` row + one `cc_show_days` row per repeat-day +
> `cc_show_instances` rows for every materialised
> occurrence. The materialisation horizon is configured under
> Settings → General Preferences. Extending the horizon is
> O(N) on existing recurring shows; the upgrade runbook
> covers how to handle this.

---

## 5. Drag-and-drop

Two kinds of drag are supported on the calendar:

### 5.1 Move a show

Click and drag any future show block to a different time / day.

- Snap is 15 minutes by default (configurable under General
  Preferences).
- The drag respects the no-overlap rule: dropping onto an
  occupied slot is rejected with a red flash.
- For a recurring show, only *this instance* is moved — the
  rest of the series stays.

### 5.2 Resize a show

Hover the bottom edge of a show; the cursor turns into a
double-arrow. Drag down to lengthen, up to shorten.

- Snap is 15 minutes by default.
- A resize cannot push the show past a neighbouring show
  (would overlap) or below 5 minutes (the minimum show
  duration).

### What cannot be dragged

- Past shows (cannot retroactively change history).
- The currently-on-air show (use **Cancel Show** instead).
- Shows you do not own (unless you are a Program Manager or
  Admin).

---

## 6. The calendar context menu — full reference

Right-click any show:

| Group | Items |
|---|---|
| Content | Schedule Tracks, Clear Schedule |
| Editing | Edit Show, Edit Instance, Apply Template, Save as Template |
| Lifecycle | Cancel Show (current only), Delete Show, Delete this instance |
| Info | View Show, View Recorded File (if a recording exists) |

The menu adapts to the show's state — e.g. **View Recorded
File** only appears after the recording finished writing.

---

## 7. The Now Line

A thin red line crosses the calendar at the current time. The
line updates every minute. Shows fully to the left of the line
are past; shows the line is currently crossing are on air.

> **Operator tip.** If you are debugging "why is the wrong
> show playing now" — eyeball the now-line against the
> calendar. The on-air show is whichever block the now-line
> intersects. If there is no block, the [Auto DJ](./AUTO_DJ.md)
> takes over (if enabled) or fallback / silence plays.

---

## 8. Bulk operations

Calendar → **Bulk Actions** dropdown at the top-right:

| Action | Effect |
|---|---|
| **Apply Template to selected shows** | Tick multiple future shows on the grid; the bulk action restamps each from the same template. |
| **Delete selected shows** | Delete each selected show. Confirmation summary lists each one. |

For larger reschedules (e.g. "shift everything next week one
hour later because of daylight-saving"), the calendar does
not currently support a bulk-shift action. The workaround is
to define the shifted week as a separate Show Template and
apply it.

---

## 9. Frequently-asked

### "I scheduled a show but nothing plays at the start time."

Three possibilities:

1. The show is empty (fill bar shows 0 %). Open Schedule
   Tracks and add at least one item.
2. The show has an [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md)
   but the playlist is empty.
3. The **RASTATIME-PLAYOUT** service is not running. Check
   with `Get-Service RASTATIME-PLAYOUT`. See
   [`CRASH_RECOVERY`](../operator/CRASH_RECOVERY.md) if so.

### "Can a show contain another show?"

No. Shows are flat. A show contains schedule items (tracks,
smart blocks, webstreams, line-ins). To group related content,
use a playlist (which can be nested inside another playlist
via reference).

### "Can two shows overlap if they are different DJs?"

No. The "no overlap" rule is station-wide because there is
only one output. To handle "two simultaneous productions",
use two output streams: each show targets a specific stream.

### "What is the maximum show duration?"

Technically 24 hours. Operationally you should split anything
over a few hours into multiple shows — the show-builder is
designed for shows of typical duration (15 min – 4 h).

### "Can I import / export the calendar as ICS?"

Yes — read-only ICS export at `/Calendar/ics/format/ics`.
Useful for syndicating the public programme schedule to a
website or another calendar system. Import is not supported.

---

## Where to go next

* [Show Templates](./SHOW_TEMPLATES.md) — stop typing the same
  show settings every week.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — let
  shows fill themselves from a playlist.
* [Auto DJ](./AUTO_DJ.md) — let the system fill calendar gaps
  for you.
* [Record-per-Show](./RECORD_PER_SHOW.md) — capture what went
  on air to a file.
