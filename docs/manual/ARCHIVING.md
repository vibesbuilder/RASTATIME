# Archiving: Editorial Team, Episodes, Online Archive, Participants

> **Where you are in the manual.** Settings → **Editorial Team** and
> **CBA Accounts**; Calendar → show form, section **Archiving**;
> Calendar → right-click an instance → **Episode...**; Analytics →
> **Participants**.  Read [Calendar](./CALENDAR.md) and
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
| 1 | Editorial team, show defaults, episode data, participants | since 2026-11-03 |
| 2 | Archive an episode online by hand from the calendar | since 2026-11-03 |
| 3 | Archive every episode automatically after the recording | since 2026-11-03 |

---

## 1. Editorial team profiles

**Settings → Editorial Team** lists the people behind the shows.

| Field | Meaning |
|---|---|
| **Name** | As it should appear on cba.media and in the statistics. |
| **Email (optional)** | For your own reference. |
| **User (optional)** | Links the profile to a RASTATIME login. A profile needs no login - most editors never sign in. |
| **Active** | Only active profiles are offered in the show form.  Switching a profile off keeps it in the shows it already belongs to. |

**Edit** fills the form above the table with the profile; **Delete**
removes the profile from every show's team after a confirmation.  The
column **Shows** counts the shows a profile belongs to.

Program Managers and Admins open this page.

---

## 2. CBA accounts

Every show is archived under a cba.media user - the episodes appear
under that user's name.  **Settings → CBA Accounts** holds these users;
only Admins open the page.

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
open the section **Archiving**, between **Who** and **Style**.  The
values apply to every episode of the show unless an episode sets its
own.

| Field | Meaning |
|---|---|
| **Editorial team** | Tick the profiles of the people behind the show. They are sent to cba.media as editors and appear in the Participants overview. |
| **People involved** | How many people usually take part in an episode (0-999). Counts in Analytics → Participants. |
| **CBA account** | The CBA user the episodes are archived under (§2). |
| **Visibility on cba.media** | *Public* (listed), *Unlisted* (reachable by its address only) or *Private* (visible to the CBA user only). |
| **CBA podcast ID** | The number of the podcast (series) on cba.media the episodes belong to. Without it, cba.media keeps the post private. |
| **Licence** | Licence of the episodes. The help icon shows which licence answers the questions of the CBA web form (see below). |
| **CBA topic** | The topic (category) on cba.media, chosen from the list RASTATIME fetches once a day. Before the first fetch the field takes the number. |
| **Languages** | Up to three language codes the CBA knows, e.g. `de, en`. |
| **Tags** | Comma-separated tags for cba.media. |
| **Default teaser** | Used for every episode without a teaser of its own. |
| **Contains copyrighted music (AKM)** | The episodes usually contain music subject to copyright; cba.media then restricts the download. |
| **Archive automatically** | Archive every new episode on cba.media by itself (§5, *Automatically*). Needs a CBA account, topic, language and licence; next to the box: since when it is on. |

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

The section is not shown in **Edit Instance**: it belongs to the whole
show.  The data of a single episode is edited in **Episode...** (§4).

> **Where does the podcast number come from?**  Open the podcast on
> cba.media; the number is part of its address or listed on its page
> (the CBA lists the podcasts of a station only to signed-in users).

---

## 4. Episode data: "Episode..."

Right-click an instance in the calendar → **Episode...**.  The entry is
there before and after the show aired - you can add the image after the
broadcast - for Admins, Program Managers and the hosts of the show.

| Field | Meaning |
|---|---|
| **Title** | Empty: the show's name and the date, shown greyed as a suggestion. |
| **Teaser** | A short summary. Empty: the show's default teaser. |
| **Description** | The text of the episode, on cba.media the text of the post. Empty: the description of the show. This is the only place to edit it (Edit Instance no longer shows it). |
| **People involved** | Only when this episode differs from the show, e.g. with guests. The show's value is shown greyed. |
| **Production date** | Required by cba.media. Empty: the day of the broadcast. Set it when the episode was produced earlier. |
| **Do not archive this episode automatically** | For tests, cancelled episodes or rights problems. Takes effect with automatic archiving (§5); archiving by hand stays possible. |
| **Episode image** | Optional, JPG or PNG up to 10 MB. Choosing a file uploads it at once; **Remove image** deletes it. Without an image, cba.media shows the image of the podcast. |
| **Image licence** / **Image caption** | Licence and credit of the image (e.g. the photographer), caption up to 500 characters. |

The right column shows what the episode takes from the show (editorial
team, CBA account, podcast, licence, visibility); the line at the top
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

The bottom block of **Episode...** - **Online archive (cba.media)** -
shows the state of the episode on cba.media.  Admins and Program
Managers archive from here; hosts see the state.

1. Fill in what the block lists under *Before this episode can be
   archived* - typically the CBA account, topic, language and licence of
   the show and a description.
2. Click **Archive online...**, choose the audio:
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
| *The upload failed: reason* | Missing data, or cba.media refused (e.g. wrong application password, unknown topic). Fix the cause and **Archive online...** again. |
| *Unclear whether the post was created* | The connection broke off during the upload. The post may exist - look on cba.media, then **Link existing post** or archive again. RASTATIME never repeats this case by itself, so no episode appears twice. |

**Link existing post** takes the number of a post on cba.media (or its
address with `?p=<number>`), e.g. for an episode you uploaded by hand
before; an empty field removes the link.  A linked episode counts as
archived.

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
2. After the waiting time (Settings → CBA Accounts, default 30 minutes)
   the background service checks the episode and queues the upload,
   with the visibility of the show.
3. If something is still missing (a description, the recording ...), the
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

**Episode...** shows in the block *Online archive* what the automatic
run plans for the episode, e.g. *Archived automatically from
2026-11-10 14:30, once nothing below is missing*.

When an automatic upload fails, stays unclear or is given up, the
warning banner at the top of the page lists the episode for seven days,
until it is archived by hand or its post is linked.

> **Not recognised:** a replacement programme that ran instead of a live
> show (the presenter did not come) is archived like the show.  Switch
> the automatic run on for shows that run reliably; when it happens,
> delete the post on cba.media.

---

## 6. Participants overview

**Analytics → Participants** counts the people involved per show and
year (station time) - the figures for the yearly statistics.

* **Year** - the current year shows the count so far.
* **Only shows without a value** - the shows that aired but have no
  *People involved* yet.  Work through this list once; set `0` for
  automated or relayed programmes.
* **Download CSV** - the table and the totals as a spreadsheet file.

Counted are the episodes that **aired** in the year (ended, not
deleted).  Rebroadcasts of the old LibreTime kind are left out; shows
set up as [Repeat of another show](./CALENDAR.md) are listed with the
tag **Repeat** - set their value to `0` when their people already count
in the original.

| Column / total | Meaning |
|---|---|
| **Episodes aired** | Episodes of the show in the year. |
| **People involved** | The show's value; the total adds the values of all shows. |
| **Episodes with own value** | Episodes whose dialog sets a different number. |
| **Participations** | The people of every episode added up (an episode with its own value counts with that value). |
| **Editorial team profiles** (total) | Distinct profiles in the teams of the shows that aired - every person once. |
| **Shows without a value** (total) | Shown in orange while there are any. |

A person in several shows counts once per show in **People involved**;
the profile total counts each person once.

Program Managers and Admins open this page.

---

## 7. Frequently asked

### "Archive online... is missing."

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

### "I ticked profiles but they do not appear in the overview."

The overview only lists shows that **aired** in the chosen year.  A new
show appears after its first episode has ended.

### "The Archiving section is missing or greyed out."

It is missing in **Edit Instance** - the section belongs to the whole
show; use **Episode...** for one episode.  It is greyed out when you are
not a Program Manager or Admin.

### "An episode was not archived automatically."

Open **Episode...**: the block *Online archive* says why - the switch is
off, the box *Do not archive* is ticked, the episode ended before the
switch was turned on, it waits for something, or the run gave up and
why.  Archive it by hand from there.

---

## Where to go next

* [Calendar](./CALENDAR.md) - the show form and the context menu.
* [Record-per-Show](./RECORD_PER_SHOW.md) - the recording that becomes
  the episode's audio.
* [Analytics](./ANALYTICS.md) - the other statistics pages.
* [Settings](./SETTINGS.md) - every page of the Settings menu.
