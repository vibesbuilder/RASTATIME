# My Podcast

> **Where you are in the manual.** Read [Library](./LIBRARY.md) first:
> what you publish to My Podcast is an ordinary track of the library.
> Not to be confused with **Podcasts** in the main menu (feeds of
> *other* podcasts you subscribe to and download) or with
> [Archiving](./ARCHIVING.md) (episodes on cba.media).

**My Podcast** is the station's own podcast: an RSS feed of tracks
from your library that listeners subscribe to in any podcast app.
Publishing a track adds it to the feed; unpublishing removes it.
Since 2026-11-14 a track can also carry the **last day it stays
published** - RASTATIME then withdraws it by itself.

Publishing is for Program Managers and Admins (see
[Users and Roles](./USERS_AND_ROLES.md)).

---

## 1. Publishing a track

1. In **Tracks**, open the context menu of the track and choose
   **Publish...**.  The publishing dialog opens in its own tab.
2. Under **Publish to:**, tick **My Podcast**.
3. Optional: enter **Published until:** - the last day the track
   stays in the podcast (YYYY-MM-DD, or pick it in the calendar that
   opens).  Leave it empty for no end.  The earliest date is today.
4. Click **Publish**.

The track now appears under **Published on:** in the same dialog,
with its date (or *no end date*) next to it.

Title, creator and description in the feed come from the track's
metadata - **Edit Metadata...** in the dialog opens the track editor.

---

## 2. Changing the date or unpublishing

Open **Publish...** again for a published track:

- **Change the date:** edit the date next to *My Podcast* and click
  **Save date**.  An empty field plus **Save date** removes the end -
  the track then stays published until you unpublish it.  A date in
  the past is refused.
- **Unpublish:** click **Unpublish**.  The track leaves the feed at
  once.

---

## 3. Automatic withdrawal ("Published until")

The date is **inclusive**: a track published until 31 December is
still in the podcast on 31 December and is withdrawn **shortly after
midnight** (station time zone), at the latest about seven minutes
after 00:00.

Withdrawal is exactly the same as clicking **Unpublish**:

- the episode leaves the **feed**;
- its **download link** stops working - podcast apps can no longer
  fetch the file;
- it disappears from the episode list on the My Podcast page.

The track itself stays in the library.  To bring it back, publish it
again - it then counts as a new publication and appears at the top in
podcast apps.  Copies that listeners already downloaded stay on their
devices; nobody can take those back.

Podcast apps fetch a feed every few hours, so an app may show a
withdrawn episode until its next fetch - the download no longer works
in the meantime.

Each automatic withdrawal is written to the legacy log
(`StationPodcastExpiryTask: unpublished episode ...`).

---

## 4. The My Podcast page

**My Podcast** in the main menu shows the podcast's settings on the
left and its episodes on the right.

- **General Fields / iTunes Fields** - name, description, language,
  author, category and so on, as podcast apps show them.  Click
  **Save** after changes.
- **Privacy Settings** - **Public** (anyone with the feed address) or
  **Private** (only with the feed address that carries the sharing
  key).  **Feed URL** and **View Feed** show the address to hand out.
- **Episode list** - every published track with its **Published
  until** date (empty = no end).  Select episodes and click
  **Unpublish** to remove them.

---

## See also

- [Library](./LIBRARY.md) - the tracks you publish.
- [Archiving](./ARCHIVING.md) - putting episodes on cba.media instead.
- [Users and Roles](./USERS_AND_ROLES.md) - who may publish.
