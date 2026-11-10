# Archiving: Producers, Episodes, Online Archive, People Involved

> **Where you are in the manual.** Settings → **Archiving** (producers,
> CBA accounts); Calendar → show form, section **Archiving**;
> Calendar → right-click an instance → **Extras** → **Archive Online**; Analytics →
> **People Involved** and **Archive Status**.  Read [Calendar](./CALENDAR.md) and
> [Record-per-Show](./RECORD_PER_SHOW.md) first - the audio of an
> archived episode is the show's recording.
>
> **What this feature does.** It archives the episodes of your shows on
> [cba.media](https://cba.media) (the archive of the Austrian community
> radios) without uploading them by hand, and counts the people who make
> the programme for the yearly statistics.
>
> **Why "Archiving".** "Publish" in RASTATIME means the station podcast
> (My Podcast).  Putting an episode on cba.media is called *archiving
> online* to keep the two apart.

An *episode* is one instance of a show in the calendar: next Monday's
"Morning Show" is one episode, the Monday after is the next.

**Where the stages stand.**

| Stage | What | State |
|---|---|---|
| 1 | Producer, show defaults, episode data, participants | since 2026-11-03 |
| 2 | Archive an episode online by hand from the calendar | since 2026-11-03 |
| 3 | Archive every episode automatically after the recording | since 2026-11-03 |

---

## 1. Producers

**Settings → Archiving** lists in its upper part, **Producers**, who
makes the shows - one person or a team each.  Each show chooses one
producer (§3).  (Until 2026-11-04 *Editorial Teams*; cba.media calls
them *editors*.)

| Field | Meaning |
|---|---|
| **Name** | As it should appear on cba.media (as editor) and in the statistics. |
| **Email (optional)** | For your own reference. |
| **User (optional)** | Links the producer to a RASTATIME login, e.g. of the person in charge. A producer needs no login. |
| **Active** | Only active producers are offered in the show form.  Switching one off keeps it in the shows that have it already. |

**Edit** fills the form above the table with the producer; **Delete**
removes the producer from every show after a confirmation.  The column
**Shows** counts the shows of a producer.

Program Managers and Admins open this page; Program Managers see only
this part.

---

## 2. CBA accounts

Every show is archived under a cba.media user - the episodes appear
under that user's name.  The lower part of **Settings → Archiving**,
**CBA Accounts**, holds these users; only Admins see it.

| Field | Meaning |
|---|---|
| **Account name** | Your name for the account, e.g. the person or the station. |
| **CBA user name** | The user name on cba.media. |
| **Application password** | Created on cba.media in the profile of the user (WordPress *application password*, not the login password). RASTATIME stores it and never shows it again; leave the field empty to keep the stored one. |

* **Test connection** asks cba.media with the stored data who the user
  is and whether the user may upload (roles admin, author, podcaster,
  station manager, channel manager).  Nothing is uploaded.
* **Delete** removes the account; the shows using it have no account
  any more until you choose another.
* **Upload limit** - the upload shares the internet line with the
  listener streams, so RASTATIME sends at most this rate (default
  4 Mbit/s: one hour of 320 kbit/s audio takes about five minutes).
* **Automatic archiving** - how many minutes after the end of an episode
  the shows with *Archive automatically* (§3) upload it (default 30):
  time to complete the episode or to tick *Do not archive this episode
  automatically*.

---

## 3. Show defaults: section "Archiving"

Edit a show (calendar → right-click → **Edit Show**, or a new show) and
open the section **Archiving**, between **Who** and **Style** - like
the other sections it comes up collapsed; click its heading.  The values
apply to every episode of the show unless an episode sets its own.

| Field | Meaning |
|---|---|
| **Producer** | Who makes the show - one person or a team, chosen from the list (one per show, §1). The name is sent to cba.media as editor and appears in Analytics → People Involved. |
| **CBA account** | The CBA user the episodes are archived under (§2). |
| **Visibility on cba.media** | *Public* (listed), *Unlisted* (reachable by its address only) or *Private* (visible to the CBA user only). |
| **CBA podcast ID** | The number of the podcast (series) on cba.media the episodes belong to. Without it, cba.media keeps the post private. |
| **Licence** | Licence of the episodes. The help icon shows which licence answers the questions of the CBA web form (see below). |
| **CBA topic** | The topic (category) on cba.media, chosen from the list RASTATIME fetches once a day. Before the first fetch the field takes the number. |
| **Languages** | Up to three language codes the CBA knows, e.g. `de, en`. |
| **Tags** | Comma-separated tags for cba.media. |
| **Default teaser** | Used for every episode without a teaser of its own. |
| **Contains copyrighted music** | The episodes usually contain music subject to copyright (AKM); cba.media then restricts the download. |
| **Archive automatically** | Archive every new episode on cba.media by itself (§5, *Automatically*). Needs a CBA account, topic, language and licence; next to the box: since when it is on. If the show has no description, a note below the box says that an episode without its own then gets the show name as its text. |

**Which licence?**  The CBA web form asks three questions; the licence
answers them:

| Licence | Credit the author? | Commercial use? | Adaptations? |
|---|---|---|---|
| CC BY | yes | yes | yes |
| CC BY-NC | yes | no | yes |
| CC BY-ND | yes | yes | no |
| CC BY-NC-ND | yes | no | no |
| CC0 | no | yes | yes |

*All rights reserved* allows none of it without asking; *CC Sampling+*
lets others reuse samples, the whole work only non-commercially;
*Public domain* keeps no rights at all.

The number of people involved is not in this section any more (since
2026-11-04): it sits in the section **What**, below **Own production**,
as **Hosts involved** (0-999; called *Number of involved people* until
2026-11-07), and appears once **Own production** is ticked - it counts
in Analytics → People Involved (§6).

In **Edit Instance** the section is shown **read-only** with the values
of the show (since 2026-11-04; before, it was not shown): it belongs to
the whole show.  The data of a single episode is edited in **Archive
Online** (§4).

> **Where does the podcast number come from?**  Open the podcast on
> cba.media; the number is part of its address or listed on its page
> (the CBA lists the podcasts of a station only to signed-in users).

---

## 4. Episode data: "Archive Online"

Right-click an instance in the calendar → **Extras** → **Archive Online** (until
2026-11-03 *Episode...*).  The entry is
there before and after the show aired - you can add the image after the
broadcast - for Admins, Program Managers and the hosts of the show.

| Field | Meaning |
|---|---|
| **Title** | Empty: the show's name and the date, shown greyed as a suggestion. |
| **Teaser** | A short summary. Empty: the show's default teaser. |
| **Description** | The text of the episode, on cba.media the text of the post. Empty: the description of the show, or the show name when the show has none (shown greyed). This is the only place to edit it (Edit Instance no longer shows it). |
| **Guests involved** | The guests of this one episode (0-999), counted on top of the show's hosts (since 2026-11-07; before, the field was called *People involved* and replaced the show's value). Empty means no guests; the line below the field shows the show's hosts. |
| **Production date** | Required by cba.media. Empty: the day of the broadcast. Set it when the episode was produced earlier. |
| **Do not archive this episode automatically** | For tests, cancelled episodes or rights problems. Takes effect with automatic archiving (§5); archiving by hand stays possible. |
| **Episode image** | Optional, JPG or PNG up to 10 MB. Choosing a file uploads it at once; **Remove image** deletes it. Without an image, cba.media shows the image of the podcast. |
| **Image licence** / **Image caption** | Licence and credit of the image (e.g. the photographer), caption up to 500 characters. |

The right column shows what the episode takes from the show (producer,
CBA account, podcast, licence, visibility); the line at the top
tells whether the episode aired and whether its recording is in the
library.

**Save** stores the text fields; the image is stored as soon as it is
chosen.  Episode images live in the library folder under
`imported/episode-images/<instance>/` and are part of the media mirror
of the [Backup](./BACKUP.md).

> **Plan close to the broadcast.**  When the repeat pattern of a show
> changes, the calendar recreates its future instances, and their
> episode data goes with them.  (**Edit Instance** of a single episode
> keeps it.)  Enter titles and images for the next few weeks rather
> than months ahead.

---

## 5. Archive online

The bottom block of **Archive Online** - **Online archive (cba.media)** -
shows the state of the episode on cba.media.  Admins and Program
Managers archive from here; hosts see the state.

1. Fill in what the block lists under *Before this episode can be
   archived* - typically the CBA account, topic, language and licence of
   the show.  A description is not required: without one on the episode
   or the show, the show name becomes the text of the post.
2. Click **Archive online now**, choose the audio:
   * **The recording of this episode** - the copy that
     [Record-per-Show](./RECORD_PER_SHOW.md) put into the library;
   * **A library file** - search by title or creator, e.g. the
     pre-produced file without jingles (MP3, OGG and Opus only; the CBA
     takes no M4A).
3. **Start upload**.  The background service (RASTATIME-WORKER) picks
   the job up within about 15 seconds; the block shows the progress and
   then the link to the post.

Title, teaser, description, image and the show's defaults are read when
the upload starts.  **Changes after the upload are made on cba.media** -
the CBA interface has no way to change or replace a post.

| State | Meaning, what to do |
|---|---|
| *Waiting for the upload* | Queued; the worker starts it shortly. |
| *Uploading to cba.media: n %* | Running, limited to the upload limit (§2). |
| *Archived on cba.media as post n* | Done; the number links to the post. |
| *Waiting for another attempt* | cba.media could not be reached or was busy; RASTATIME tries again after 2, 5, 15, 30 minutes ... for up to 24 hours. |
| *The upload failed: reason* | Missing data, or cba.media refused (e.g. wrong application password, unknown topic). Fix the cause and **Archive online now** again. |
| *Unclear whether the post was created* | The connection broke off during the upload. The post may exist - look on cba.media, then **Link existing post** or archive again. RASTATIME never repeats this case by itself, so no episode appears twice. |

**Link existing post** is for a post that is on cba.media already -
uploaded there by hand, or after an *unclear* upload.  Enter its number
(or its address with `?p=<number>`) and click the button: RASTATIME
marks the episode as archived and uploads nothing.  An empty field
removes the link.  The help icon next to the button says the same.

> **Stopping the worker** only pauses the uploads; the broadcast is not
> affected.  A job that was running is checked after the restart: if no
> byte had left, it starts again, otherwise it ends as *unclear*.

### Automatically

With **Archive automatically** ticked in the section *Archiving* of the
show (§3), RASTATIME archives every new episode by itself, always with
the recording:

1. The episode ends; [Record-per-Show](./RECORD_PER_SHOW.md) puts the
   recording into the library within seconds (the show must record, and
   *Copy Show Recordings into Library* must be on under Settings → Local
   Machine).
2. After the waiting time (Settings → Archiving, default 30 minutes)
   the background service checks the episode and queues the upload,
   with the visibility of the show.
3. If something is still missing (the recording, a topic ...), the
   episode waits and is checked again every five minutes, for up to 24
   hours.  Then the run gives up; the dialog shows *The automatic
   archiving gave up* with the reason.

Never archived automatically:

* episodes that ended **before** the box was ticked - nothing is caught
  up; archive older episodes by hand;
* rebroadcasts and shows set up as *Repeat of another show*;
* episodes with **Do not archive this episode automatically** (§4);
* episodes that are archived or linked already, or that someone started
  by hand - the automatic run leaves those alone;
* episodes whose recording covers less than half of the show (e.g. a
  recording that broke off).

**Archive Online** shows in the block *Online archive* what the automatic
run plans for the episode, e.g. *Archived automatically from
2026-11-10 14:30, once nothing below is missing*.

When an automatic upload fails, stays unclear or is given up, the
warning banner at the top of the page lists the episode for seven days,
until it is archived by hand or its post is linked; Program Managers
and Admins find a link to **Analytics → Archive Status** (§7) there.

> **Not recognised:** a replacement programme that ran instead of a live
> show (the presenter did not come) is archived like the show.  Switch
> the automatic run on for shows that run reliably; when it happens,
> delete the post on cba.media.

---

## 6. People Involved

**Analytics → People Involved** counts the people involved per own
production and year (station time) - the figures for the yearly
statistics.  Only shows with **Own production** (Edit Show → What)
count.  A show whose tick is removed keeps its numbers but is left out.

Since 2026-11-07 the count follows the people, not the episodes:

* **Hosts involved** (Edit Show → What, right below **Own production**)
  are the people who are the same in every episode.  They count **once
  per show and year**, however many episodes aired.
* **Guests involved** (Archive Online in the calendar) are the guests of
  one episode.  They count **in every episode** and add up.
* **People involved** = hosts + guests.

Example: a weekly show with 2 hosts aired 40 times; three episodes had
guests (1, 2 and 1).  People involved: 2 + 4 = 6.

* **Year** - the current year shows the count so far.
* **Only shows without a value** - the own productions that aired but
  have no *Hosts involved* yet.  Work through this list once; set `0`
  for automated or relayed programmes.
* **Download CSV** - the table and the totals as a spreadsheet file.

Counted are the episodes that **aired** in the year (ended, not
deleted).  Rebroadcasts of the old LibreTime kind are left out.  Shows
set up as [Repeat of another show](./CALENDAR.md) are listed with the
tag **Repeat** and count nothing: their people were already counted
with the original.  They never appear under *Shows without a value*.

| Column / total | Meaning |
|---|---|
| **Own productions aired** (total) | Own productions with at least one aired episode in the year, repeats included. |
| **Episodes aired** | Episodes of the show in the year. |
| **Hosts involved** | The show's hosts, once per year; the total adds the hosts of all shows. |
| **Guests involved** | The guests of all aired episodes of the show added up. |
| **People involved** | Hosts + guests; the total is the figure for the statistics. |
| **Shows without a value** (total) | Own productions (no repeats) without *Hosts involved*; shown in orange while there are any. |

A person in several shows counts once per show; a guest who comes back
counts in every episode.  The figures are numbers, not names - RASTATIME
cannot tell that two shows share a host.  The producers are not counted.

Program Managers and Admins open this page.

---

## 7. Archive Status

**Analytics → Archive Status** (since 2026-11-04) shows on one page
whether the episodes reach cba.media.  Program Managers and Admins open
it; the warning banner links to it.

* **Running and waiting** - the upload in progress (the share sent,
  updated every few seconds) and those waiting: for the background
  service, or for another attempt after a connection problem (time and
  reason).  **Cancel** stops a waiting upload.  A running upload cannot
  be cancelled - it belongs to the background service until it ends.
* **Ahead (automatic archiving)** - the episodes of shows with *Archive
  automatically* from the next 7 days and those that aired but are not
  queued yet, with the time they are due:

  | Status | Meaning |
  |---|---|
  | *Not aired yet - due ...* | The episode is still to come. |
  | *Aired - due ...* | The waiting time (Settings → Archiving) runs. |
  | *Due - queued at the next check* | Nothing is missing; the background service queues it within five minutes. |
  | *Waiting, at the latest until ...* | Something is missing (column **Missing**); after that time the automatic run gives up. |
  | *Not archived automatically: ...* | *Do not archive this episode automatically* is ticked. |

  Before the broadcast, **Missing** already lists what the show lacks
  (CBA account, topic, language, licence) - time to complete the show.
* **Problems (last 30 days)** - uploads by hand or automatic that
  failed, stayed unclear or were given up, as long as the episode has no
  post.  **Archive again** queues the same audio once more (the
  recording, if that file is gone).  After an *unclear* upload the page
  asks first, because the post may exist: look on cba.media and use
  **Link post…** (number or address) if it is there.  The line goes
  away once the episode is archived or linked.
* **History** - every upload with time, show, episode, who started it
  (*Automatic* or the login), state, link to the post, audio, size,
  duration and note.  Filter by year, month, state, started by and show
  name; **Download CSV** takes the whole filtered list (the page shows
  the newest 500).

The page reloads by itself when an upload starts or ends.

---

## 8. Frequently asked

### "Archive online now is missing."

The button is shown to Admins and Program Managers, and only while the
episode is neither archived nor waiting for an upload.

### "Test connection says the user name or password is refused."

Use the *application password* from the profile on cba.media, not the
password you sign in with; spaces in it do not matter.  Check the user
name for typos.

### "The topic is a number field, not a list."

The background service fetches the topic list once a day.  After a new
installation or before RASTATIME-WORKER ran, the field takes the number.

### "Comments on cba.media?"

The CBA upload interface has no setting for comments; the default of the
CBA user applies.

### "I chose a producer but the show does not appear in the overview."

The overview only lists shows that **aired** in the chosen year.  A new
show appears after its first episode has ended.

### "The Archiving section is greyed out."

In **Edit Instance** it is read-only - the section belongs to the whole
show; use **Archive Online** for one episode.  It is greyed out too when
you are not a Program Manager or Admin.

### "An episode was not archived automatically."

Open **Archive Online**: the block *Online archive* says why - the switch is
off, the box *Do not archive* is ticked, the episode ended before the
switch was turned on, it waits for something, or the run gave up and
why.  Archive it by hand from there.  **Analytics → Archive Status**
(§7) lists all such episodes at once.

### "Where are Editorial Team and CBA Accounts?"

Since 2026-11-03 both are on one page, **Settings → Archiving**: the
producers on top (until 2026-11-04 called *Editorial Teams*), the CBA accounts with the upload limit and the
waiting time below (Admins only).

---

## Where to go next

* [Calendar](./CALENDAR.md) - the show form and the context menu.
* [Record-per-Show](./RECORD_PER_SHOW.md) - the recording that becomes
  the episode's audio.
* [Analytics](./ANALYTICS.md) - the other statistics pages.
* [Settings](./SETTINGS.md) - every page of the Settings menu.
