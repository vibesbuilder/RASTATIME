# Teaser Automation

> **Where you are in the manual.** Library → track editor, fields
> **Teaser for show** and **Teaser type**; Library → Smart Blocks,
> criteria **Teaser: show**, **Teaser: type**, **Teaser: fits the
> schedule**.  Read [Library](./LIBRARY.md) § 3 (smart blocks) and
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) first - the
> automation is a smart block criterion that autoloading plays out.
>
> **What this feature replaces.** Placing the "today" and "tomorrow"
> jingles of every show by hand, day after day, before and after the
> news and in the music shows.

A station has three kinds of teasers: a **show teaser** that just
announces a show ("Around the World - every Thursday at 11"), a
**day teaser "today"** ("Around the World - today at 11") and a
**day teaser "tomorrow"**.  Which one fits depends on the day the jingle
plays on and on the calendar.  Since 2026-10-16 the library knows which
show a jingle announces and how, and a smart block criterion picks the
jingles that fit the day of the show being filled.

---

## 1. Linking a jingle to its show

Open the jingle in the track editor (Library → pencil, or double-click)
and set

| Field | Meaning |
|---|---|
| **Teaser type** | **Show teaser (any day)**, **Day teaser: "today"** or **Day teaser: "tomorrow"**.  Choose it first: the shows list below stays greyed out until a type is set, and a save with shows but no type is refused. |
| **Teaser for shows** | the shows this jingle announces - the **Shows** button opens the same checkbox panel as the Song-Request Pool; tick one or several, the button shows the count.  The list holds every show with an upcoming broadcast, each with its next airing (`bbc (Sat 12:00)`) so shows that share a name can be told apart; the hourly news slots are separate shows and one "BBC today" jingle can announce them all.  Nothing selected = no teaser; setting the type back to *None* empties the list. |

For many jingles at once select them in the library and use **Edit**
(bulk edit): the same two fields; nothing selected keeps a field,
*None* clears the links, selected shows replace the list - and need a
type in the same save, because the selected tracks need not have one yet.  The library column **Teaser** (columns picker,
hidden by default) shows `Show name · today` (`· tomorrow`; show teasers carry no suffix) and is searchable, so
"Teaser contains Worldwide" lists every jingle of that show.

A jingle has one type and announces one or more shows; it fits as soon
as one of its shows fits.  Two jingles may of course announce the same
show with different types.

## 2. The smart block criteria

| Criterion | Modifiers | Value | Matches |
|---|---|---|---|
| **Teaser: show** | is / is not | a show | jingles that announce that show (among others) |
| **Teaser: type** | is / is not | show teaser, today, tomorrow | jingles of that type |
| **Teaser: fits the schedule** | is | the day of the show being filled | see below |

**Teaser: fits the schedule** is the automation.  "The day" is the
calendar day (station timezone) of the *slot* the block is expanded
for: the start of the show for an autoloading intro playlist, the end
of the show for the outro, the current position for the content
playlist, and - when you drag a block into a show by hand - the end of
the row you drop it after.  With that day *D* and the moment *T* of the
slot:

* a **"today"** teaser fits when its show has a broadcast on *D* that
  starts after *T*;
* a **"tomorrow"** teaser fits when its show has a broadcast on *D + 1*;
* a **show teaser** fits on any day - unless its show is *over for
  today*: it had a broadcast on *D* that ended before *T* and has no
  later one on *D*;
* a jingle never fits the show whose instance is being filled - a show
  does not tease itself.

A cancelled or moved broadcast therefore takes its day teasers with it:
the criterion looks at the calendar at fill time, not at a fixed list.

## 3. Rotation: no jingle twice in a show

Combine the criterion with **Exclude tracks played lately** (for
example 3 hours).  Since 2026-10-16 that filter also counts **planned**
rows: a track scheduled inside the window - before or after the slot,
including rows an earlier block of the same fill has just placed in the
same show - is excluded although it has not played yet.  Two teaser
blocks in one show therefore never draw the same jingle, and a jingle
planned in the show before does not come back in the next one.  This
holds for every smart block with the filter on, music included.

## 4. Recipes

**News block (e.g. the hourly BBC show).**  Give the show an autoloading
intro playlist and an outro playlist, each with one dynamic smart block:
*1 item*, criterion *Teaser: fits the schedule is the day of the show
being filled*, *Exclude tracks played lately 3 h*.  The slot must have
room for the jingles: a 7-minute show with a 7-minute stream has none.

**Music shows.**  Replace the hand-made day-teaser blocks in their
autoloading playlists by the same block.  Keep a second block *Teaser:
type is Show teaser* for shows that have no day teasers yet.

**One show only.**  *Teaser: show is Worldwide* together with *Teaser:
fits the schedule* gives that show's jingles only when they fit.

## 5. Teasers from the calendar

Right-click (or click) a show in the [Calendar](./CALENDAR.md) and pick
**Extras** → **Teasers** (a submenu since 2026-11-10): the dialog lists every jingle that announces this show
with its type and the other shows it announces, lets you change the
type in place, remove a jingle from the show with the cross, and link
further jingles: type two characters of a title or creator, pick the
jingle, choose a type (or keep the jingle's own) and click **Link to
this show**.  The type belongs to the jingle, so changing it here
changes it for all its shows.  Administrators and programme managers
only; the entry exists for past shows as well, since the link is to
the show, not to the broadcast.

## 6. Import / Export

[Import / Export](./IMPORT_EXPORT.md) carries the criteria in
`blocks.json`: `teaser_show` by show name (the first show of that name
on import), `teaser_type` as `show`, `today` or `tomorrow`,
`teaser_fits` with the value `yes`.  The jingles' own links are
metadata of the files and are not part of the bundle.

## 7. Frequently-asked

### "Generate in the smart block editor shows other jingles than the show gets."

The editor has no slot: it uses *now* as the moment and excludes no
show.  The real pick happens when the show is filled.

### "A show vanished from the list."

The list holds shows with an upcoming broadcast.  A jingle keeps its
link to a show that has none any more; the editor still shows it, the
criterion simply finds no fitting day.

### "Nothing is picked at all."

Check that the jingles carry a show and a type, that the show really
has a broadcast on that day, and that the block's other criteria (track
type, genre) do not exclude them.  Until the database migrations 0069 and
0070 have run, the criterion yields an empty pool and the log says so.

## See also

* [Library](./LIBRARY.md) § 3 - smart block criteria, limits and the
  exclude filters.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) - intro, outro
  and content playlists that carry the teaser blocks.
* [Calendar](./CALENDAR.md) - the broadcasts the criterion reads.
