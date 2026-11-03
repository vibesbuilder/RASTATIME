# Publishing: Editorial Team, Episodes, Participants

> **Where you are in the manual.** Settings → **Editorial Team**;
> Calendar → show form, section **Publishing**; Calendar → right-click
> an instance → **Episode...**; Analytics → **Participants**.  Read
> [Calendar](./CALENDAR.md) and [Record-per-Show](./RECORD_PER_SHOW.md)
> first - the episode audio is the show's recording.
>
> **What this feature prepares.** Publishing every episode on
> [cba.media](https://cba.media) (the archive of the Austrian community
> radios) without uploading it by hand, and the yearly count of the
> people who make the programme.

Since 2026-11-03 RASTATIME keeps the data a published episode needs:
who makes a show, the defaults of its podcast on cba.media, and per
episode a title, a teaser, a description and an optional image.  The
same data feeds the **Participants** overview for the yearly
statistics.

**Nothing is uploaded yet.**  Sending episodes to cba.media - by hand
from the calendar and automatically after the recording - follows in
the next stages; this chapter grows with them.

An *episode* is one instance of a show in the calendar: next Monday's
"Morning Show" is one episode, the Monday after is the next.

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

## 2. Show defaults: section "Publishing"

Edit a show (calendar → right-click → **Edit Show**, or a new show) and
open the section **Publishing**, between **Who** and **Style**.  The
values apply to every episode of the show unless an episode sets its
own.

| Field | Meaning |
|---|---|
| **Editorial team** | Tick the profiles of the people behind the show. They are sent to cba.media as editors and appear in the Participants overview. |
| **People involved** | How many people usually take part in an episode (0-999). Counts in Analytics → Participants. |
| **CBA podcast ID** | The number of the podcast (series) on cba.media the episodes belong to. |
| **Licence** | Default licence of the episodes: All rights reserved, CC BY-NC-ND, CC BY-ND, CC BY-NC, CC BY-SA, CC BY, CC0, Public domain. |
| **CBA topic ID** | The number of the topic (category) on cba.media. |
| **Languages** | Up to three language codes, e.g. `de, en`. |
| **Tags** | Comma-separated tags for cba.media. |
| **Default teaser** | Used for every episode without a teaser of its own. |
| **Contains copyrighted music (AKM)** | The episodes usually contain music subject to copyright. |

The section is not shown in **Edit Instance**: it belongs to the whole
show.  The data of a single episode is edited in the **Episode...**
dialog (§3).

> **Where do the CBA numbers come from?**  Open the podcast or the
> topic on cba.media; the number is part of its address or listed on
> its page.  The next stage will offer a list to pick from.

---

## 3. Episode data: "Episode..."

Right-click an instance in the calendar → **Episode...**.  The entry is
there before and after the show aired - you can add the image after the
broadcast - for Admins, Program Managers and the hosts of the show.

| Field | Meaning |
|---|---|
| **Title** | Empty: the show's name and the date, shown greyed as a suggestion. |
| **Teaser** | A short summary. Empty: the show's default teaser. |
| **Description** | The text of the episode - the same field as **Instance Description** in the show form. |
| **People involved** | Only when this episode differs from the show, e.g. with guests. The show's value is shown greyed. |
| **Episode image** | Optional, JPG or PNG up to 10 MB. Choosing a file uploads it at once; **Remove image** deletes it. Without an image, cba.media shows the image of the podcast. |
| **Image licence** / **Image caption** | Licence and credit of the image (e.g. the photographer). |

The right column also shows what the episode takes from the show
(editorial team, CBA podcast ID, licence) and the line at the top tells
whether the episode aired and whether its recording is in the library.

**Save** stores the text fields; the image is stored as soon as it is
chosen.  Episode images live in the library folder under
`imported/episode-images/<instance>/` and are part of the media mirror
of the [Backup](./BACKUP.md).

> **Plan close to the broadcast.**  When the repeat pattern of a show
> changes, the calendar recreates its future instances, and their
> episode data goes with them.  Enter titles and images for the next
> few weeks rather than months ahead.

---

## 4. Participants overview

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

## 5. Frequently asked

### "I ticked profiles but they do not appear in the overview."

The overview only lists shows that **aired** in the chosen year.  A new
show appears after its first episode has ended.

### "The Publishing section is missing or greyed out."

It is missing in **Edit Instance** - the section belongs to the whole
show; use **Episode...** for one episode.  It is greyed out when you are
not a Program Manager or Admin.

### "Episode... is missing in the menu."

It is shown to Admins, Program Managers and the hosts of the show, and
not on the rebroadcast instances of the old LibreTime kind.

---

## Where to go next

* [Calendar](./CALENDAR.md) - the show form and the context menu.
* [Record-per-Show](./RECORD_PER_SHOW.md) - the recording that becomes
  the episode's audio.
* [Analytics](./ANALYTICS.md) - the other statistics pages.
* [Settings](./SETTINGS.md) - every page of the Settings menu.
