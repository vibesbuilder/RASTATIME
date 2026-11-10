# Analytics

> **Where you are in the manual.** This is an **Output and
> infrastructure** chapter, a companion to
> [Streams](./STREAMS.md). Streams covers *configuring* your
> outputs and watching them live; this chapter covers the
> **rear-view mirror** — what actually went on air, and how many
> people were listening while it did.

The **Analytics** menu in the top navigation bundles eight pages:

| Page | Question it answers |
|---|---|
| **Playout History** | What did the station actually broadcast, minute by minute? |
| **History Templates** | Which columns should the history log record and export? |
| **Listener Stats** | How many listeners were connected to each stream, over time? |
| **Show Listener Stats** | How did each *show* perform in listener numbers? |
| **Music by Country** | Where does the music that aired come from (music quota)? One year at a time, CSV. See § 7 (since 2026-11-08). |
| **Programme Minutes** | How many minutes of own productions went on air in a year? One year at a time, CSV. See § 5 (since 2026-11-03; until 2026-11-04 part of the "Yearly Report"). |
| **People Involved** | How many people made the station's own productions in a year? See § 6 and [Archiving](./ARCHIVING.md) § 6 (since 2026-11-03, own menu entry since 2026-11-04). |
| **Archive Status** | Did every episode reach cba.media? Uploads running and waiting, what the automatic archiving has ahead, problems, history, CSV. See [Archiving](./ARCHIVING.md) § 7 (since 2026-11-04). |

The first two exist for **accountability** — royalty reporting,
regulator log sheets, "what was that track at 14:32?" phone calls.
The last two exist for **programming decisions** — which slots and
shows actually draw an audience.

---

## 1. Playout History

**Analytics → Playout History** shows everything the playout engine
actually pushed to air, regardless of how it got scheduled (calendar
show, Auto DJ, manual override, live DJ).

At the top, a **date/time range picker** with **Filter History**
narrows every view to a window — it defaults to the current day.

Three tabs below it (DJs see only the third, with the shows they
host; there they add, edit and delete entries - Program Managers and
Admins edit every entry):

* **Log Sheet** — the raw airing log, one row per played item, with
  its start / end time and the metadata columns your active template
  defines (see §2). This is the view you export for royalty
  collecting societies.
* **File Summary** — the same window aggregated **per track**: how
  often each file aired in the range. Sortable by any column.
* **Show Summary** — the same window grouped **per episode**.
  Expand a show to see what aired inside it.

> **Operator tip.** The Log Sheet records what the *engine* played.
> A live DJ talking over the stream leaves no rows here — only
> file and webstream playback is logged.

> **How it works under the hood.** The playout service writes one
> row per aired item into `cc_playout_history` (plus
> `cc_playout_history_metadata`) at the moment the item starts.
> The three tabs are DataTables views over
> `/playouthistory/{playout-history-feed,file-history-feed,show-history-feed}`,
> all filtered by the picked range on the server side.

> **Deleting a track keeps its history (since 2026-10-08).** Every
> file row carries title, creator, length, composer and copyright of
> the moment it aired. Deleting the track from the library clears the
> file reference and the row stays, shown from those values - the
> same way webstream and line-in rows are shown. The *File Summary*
> tab counts tracks that still exist. Before, LibreTime deleted the
> history rows together with the track.

---

## 2. History Templates

**Analytics → History Templates** controls **which metadata columns**
the Log Sheet and File Summary record and display. Two template
kinds exist — **Log Sheet Template** and **File Summary Template** —
and exactly one of each can be the active default.

Add fields by name and type (string / integer / date …), order them,
then **Set Default Template**. New history rows record the fields of
the template active *at airtime*; changing templates does not rewrite
old rows.

> **Operator tip.** Set your template up **once, before** you need
> your first royalty report, and leave it alone. The stock fields
> (artist, title, played date/time) satisfy most reporting duties.

---

## 3. Listener Stats

**Analytics → Listener Stats** charts the number of **concurrently
connected listeners per stream mount** over the picked time range,
one coloured line per mount (e.g. `rastatime`, `rastatime-aac`).
Use the same date/time picker as in Playout History; the legend's
checkboxes toggle individual mounts.

The numbers come from your streaming server, so they count *direct*
stream listeners. Listeners behind a relay, CDN or aggregator appear
as **one** connection.

> **How it works under the hood.** The playout service polls each
> configured Icecast server's `/admin/stats.xml` every **120
> seconds** with the admin credentials from that stream's
> configuration, and stores one data point per mount in
> `cc_listener_count`. Only streams whose **Admin Password** is set
> in **Settings → Streams** are polled; streams without one are
> skipped with a warning in `logs/playout.log`.
> *(Restored on Windows in RASTATIME 2026-08-30 — on earlier builds
> this chart stayed empty because no collector was running.)*

**Stream Data Collection Status** (the box on the right, since
2026-10-26): one line per enabled stream with its mount.  **OK** means
the last query worked.  Otherwise the line names the cause and since
when: Icecast rejects the admin user/password (check them in
**Settings → Streams**), is not reachable, does not answer in time,
sends an unreadable statistics page, or answers with another error.
With the first successful query after the problem the line returns to
OK by itself - before 2026-10-26 an error stayed on the page for good
and always read "check admin user/password".  A stream without an
Admin Password says that no statistics are collected for it.

**Empty chart?** In order of likelihood:

1. The **RASTATIME-PLAYOUT** service is not running (it hosts the
   collector).
2. The stream's **Admin Password** in **Settings → Streams** is
   empty or wrong — check `logs/playout.log` for a skip warning or
   HTTP 401.
3. You are looking at a range before stats collection started —
   data only accumulates from the moment the collector first ran.

---

## 4. Show Listener Stats

**Analytics → Show Listener Stats** folds the same listener data
**per episode**: for each show in the picked range you get the
**average** and the **maximum** number of concurrent listeners while
it was on air.

This is the page for programming decisions — compare a show's
numbers across weeks, or two shows in the same slot.

> **Show numbers need show data.** A show that aired before listener
> collection started (or while playout was down) shows zeros — the
> aggregation can only fold data points that exist in
> `cc_listener_count` for the show's time window.

## 5. Programme Minutes (since 2026-11-03)

The figures for the yearly reporting to the authorities are on two
pages, each with a year selector (station time; the current year up to
today): **Analytics → Programme Minutes** (this section) and
**Analytics → People Involved** (§ 6).  Until 2026-11-04 both were one
page, the "Yearly Report".

Tick **Own production** in a show (Edit Show → What; the help icon next
to it explains it in short; one-off or recurring, templates and
Import/Export carry it as `own_production`).  The page counts the episodes of flagged shows that
aired in the year - ended, not deleted, no legacy rebroadcast - with
their **scheduled** duration, rounded to minutes per show and month.
Shows set up as [Repeat of another show](./CALENDAR.md) are kept in a
column of their own (first broadcasts vs. repeats), because most
authorities report them separately.  Shows without the flag appear
greyed with their minutes under "other shows (not counted)" so you can
see what is left out.  A table per month and **Download CSV (minutes)**
(per show with genre and category, totals, per month) complete the section.

**By genre and category** (since 2026-11-10): below the months, the
same minutes grouped by the shows' **Genre**, **Category** or **Genre
and category** (choose under *Group by*), with the columns episodes of
own productions, minutes of own productions as first broadcasts and as
repeats, minutes of other shows and the total.  Values are grouped
ignoring upper / lower case and surrounding blanks and shown in their
most used spelling; shows without a value form the row *No genre* /
*No category*.  **Download CSV** exports the chosen grouping.  Minutes
are rounded per group, so a sum can differ from the per-show totals by
a minute or two.  The category is set in the show (Edit Show → What,
free text with suggestions; database migration 0082).

Program Managers and Admins open this page.

## 6. People Involved (since 2026-11-03)

**Analytics → People Involved** counts the people who made the
station's **own productions** in a year.  Since 2026-11-07:
**People involved** = the show's **Hosts involved** (Edit Show → What,
below **Own production**; the field appears once the box is ticked),
counted **once per year**, + the **Guests involved** of every aired
episode (Extras → People Involved in the calendar), counted **per episode**.
Only shows with **Own production** count - a show without the tick
keeps its number but is left out until it is ticked again; repeat shows
(*Repeat of*) are listed but count nothing.  **Only shows without a
value** and **Download CSV** help with the yearly reporting.  The
details are in [Archiving](./ARCHIVING.md) § 6.

Program Managers and Admins open this page.

## 7. Music by Country (since 2026-11-08)

**Analytics → Music by Country** shows where the music that went on
air in a year comes from - the station's music quota.  One year at a
time (station time; the current year up to today).

Counted are the plays in the [Playout History](#1-playout-history) of
tracks whose track type has the code `music` (Settings → Track Types);
tracks of any other type or without a type do not count.  Each play
counts with the country of its track as it is today (Edit Track →
**Country**, read from the `Country` tag on import - see
[Library](./LIBRARY.md)), so correcting a country corrects the past
plays too.  A track without a country counts as **No country**; a
combination such as `Germany/Switzerland` is a row of its own.

The page shows the minutes of music, the plays, the number of
countries and the share of minutes with a country; a table per country
(plays and minutes with their shares, sorted by minutes, *No country*
last); a table per month (plays, minutes, minutes with a country and
their share); and the **25 most played music tracks without a
country** - enter their country to make the report more complete.
**Download CSV** adds a table of the minutes per country and month.

Not counted, because they are not in the Playout History: music DJs
play live, line-ins and webstreams, and plays of tracks deleted since.
The history begins with the first play logged on the installation; the
page says so when it starts later in the year.

Program Managers and Admins open this page.
