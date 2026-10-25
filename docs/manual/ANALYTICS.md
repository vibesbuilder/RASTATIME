# Analytics

> **Where you are in the manual.** This is an **Output and
> infrastructure** chapter, a companion to
> [Streams](./STREAMS.md). Streams covers *configuring* your
> outputs and watching them live; this chapter covers the
> **rear-view mirror** — what actually went on air, and how many
> people were listening while it did.

The **Analytics** menu in the top navigation bundles four pages:

| Page | Question it answers |
|---|---|
| **Playout History** | What did the station actually broadcast, minute by minute? |
| **History Templates** | Which columns should the history log record and export? |
| **Listener Stats** | How many listeners were connected to each stream, over time? |
| **Show Listener Stats** | How did each *show* perform in listener numbers? |

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
* **Show Summary** — the same window grouped **per show instance**.
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
**per show instance**: for each show in the picked range you get the
**average** and the **maximum** number of concurrent listeners while
it was on air.

This is the page for programming decisions — compare a show's
numbers across weeks, or two shows in the same slot.

> **Show numbers need show data.** A show that aired before listener
> collection started (or while playout was down) shows zeros — the
> aggregation can only fold data points that exist in
> `cc_listener_count` for the show's time window.
