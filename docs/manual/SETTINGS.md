# Settings

> **Where you are in the manual.** This chapter is the index of the
> Settings menu.  It documents the *General* and *Status* pages inline
> and points at the dedicated chapter for every other page.  Reviewed
> against the interface on 2026-10-25.

The Settings menu is the station's configuration surface.  Most pages
belong to **Admins**; a **Program Manager** sees
*My Profile*, *Show Templates*, *Auto DJ* and the producers of
*Archiving*; Guests and DJs see *My
Profile* only.  See [Users and Roles](./USERS_AND_ROLES.md) §2 for the
full permission matrix.

---

## 1. The Settings menu

Left navigation → **Settings** opens the sub-menu:

| Page | Purpose | Who | Manual chapter |
|---|---|---|---|
| **General** | Station name and description, language, week start, public API, radio page, logo, landing page background, favicon, primary colour, crossfades, upload track type, automation playlists, Live Text Info, Radioplayer Feed, TuneIn, Dangerous Options. | Admin | This chapter §2 |
| **My Profile** | Your own name, e-mail, password, interface language and time zone. | everyone | [Users and Roles](./USERS_AND_ROLES.md) §4 |
| **Users** | Create, edit and delete users and set their user type. | Admin | [Users and Roles](./USERS_AND_ROLES.md) §3 |
| **Track Types** | Track types with their crossfade, crossover and stream-metadata presets and their cue point analysis on import. | Admin | [Library](./LIBRARY.md) |
| **Show Templates** | Overview of the saved show templates: rename, delete. | Program Manager, Admin | [Show Templates](./SHOW_TEMPLATES.md) |
| **Archiving** | Producers of the shows - one person or a team each (name, optional login; one per show, chosen under Archiving); for Admins below them the cba.media users the shows are archived under (user name, application password), connection test, upload limit, waiting time of the automatic archiving. Until 2026-11-03 two entries, *Editorial Team* and *CBA Accounts*. | Program Manager (producers), Admin | [Archiving](./ARCHIVING.md) |
| **Auto DJ** | Gap filler and top-up of incomplete shows. | Program Manager, Admin | [Auto DJ](./AUTO_DJ.md) |
| **Streams** | Output streams (bitrate, mount, codec), live dial-in inputs, Master login. | Admin | [Streams](./STREAMS.md) |
| **Local Machine** | Sound card, import folder and format, recording folder and format, library location. | Admin | [Local Machine](./LOCAL_MACHINE.md) |
| **Alerts** | Messages by e-mail and Telegram on dead air, services down and pre-flight warnings; one switch per channel. Since 2026-11-03; below Local Machine since 2026-11-04. | Admin | This chapter §6 |
| **Import / Export** | Users, shows, playlists, smart blocks, webstreams and podcast subscriptions as CSV/JSON files, with a preview step on import. | Admin | [Import / Export](./IMPORT_EXPORT.md) |
| **Backup** | Database and configuration backups, the media mirror, automatic backups, restoring. | Admin | [Backup](./BACKUP.md) |
| **Status** | Service health, disk space, service restarts, allowed and blocked addresses. | Admin | This chapter §3 |

Line-In sources are managed under **Dashboard → Line Inputs** (see
[Line-In](./LINE_IN.md)); the interface languages are covered in
[Languages](./I18N.md).

---

## 2. General

Settings → **General**.

The page is divided into **collapsed segments** (since 2026-10-08): the
station name and description stay on top, below them *Station*,
*Styling*, *Playout* and *Automation*, then *Live Text Info*, *TuneIn
Settings* and *Dangerous Options*.  Click a heading to open it; a
segment that holds a validation error after **Save** opens by itself.

### Top of the page

| Field | Notes |
|---|---|
| **Station Name** | Visible everywhere - page title, stream metadata, radio page. |
| **Station Description** | Free text, used in podcast feeds and on the radio page. |

### Station

| Field | Notes |
|---|---|
| **Default Language** | Interface language for new users and the login screen, and the language of all widgets (dates, weekdays, buttons; since 2026-10-25). Every user keeps their own language from My Profile. |
| **Station Timezone** | Shown for information only.  The station time zone is set in `config/rastatime.conf` (`general.timezone`); each user can choose a display time zone in My Profile. |
| **Week Starts On** | First day of the week in the calendar and in the widgets (Weekly Schedule, Multi-View Schedule). |
| **Public RASTATIME API** | *Enabled* lets external widgets embedded in other websites read the schedule data. Required for the embeddable schedule widgets. |
| **Display login button on your Radio Page?** | Shows a login button on the public radio page. |
| **Disable the public radio page and redirect to the login page?** | Visitors of the station address go straight to the login. |

### Styling

| Field | Notes |
|---|---|
| **Station Logo** | Image shown in the top-left of every page. Up to 1 MB, JPG / PNG / GIF / WebP; **Remove** deletes it. |
| **Landing page background** | The photo behind the public landing page (`/`). JPG, PNG or WebP up to 5 MB; 1920 px wide and 1 MB or less recommended. Stored as a file under `landing/` in the media library location (so the nightly backup mirror carries it); **Remove** returns to the built-in image. Takes effect on the next load of the landing page (the browser caches the image for a week, a new upload gets a new address). Since 2026-10-07. |
| **Station Favicon** | Image shown in the browser tab. Up to 200 KB, PNG / JPG / GIF / ICO. Rendered as a data: URI; no file writes to public/. |
| **Primary Color** | The accent colour of the whole interface, the radio page and the widgets — links, highlights, selected rows, the active menu entry and the active tab in Playout History, progress and storage bars, scrollbars, section arrows, the stream player's play button and volume slider, the widgets' tabs, buttons and highlights, the error-page graphic. Enter `#rrggbb` or use the colour picker next to the field; **Reset to default** restores the orange (`#ff5d1a`). Takes effect on the next page load. Choose a colour that stands out against the dark grey background; text on the colour switches between white and black by itself. Signal colours (errors, warnings, the show colours in the calendar) and the fill bar of the show slots in the calendar (always orange) stay as they are. |
| **Secondary Color** | The second colour of the interface (since 2026-10-26): the show progress bar in the header, the marker on the right edge of the active entry in the dashboard menu (Tracks, Playlists, Smart Blocks, …) and in the sub-menus of Settings, Analytics, Help and Widgets, the current track in the dashboard's Scheduled Shows, and the buttons Upload, New Show, New Log Entry, Add, New and the like. Enter `#rrggbb` or use the colour picker next to the field; **Reset to default** restores the light blue (`#1adeff`). The buttons carry white text: for them the colour is darkened only as far as legibility needs (default: `#0e7a8c`, was `#246b86`); text on the current track's row switches between black and white by itself. Takes effect on the next page load. |

### Playout

| Field | Notes |
|---|---|
| **Default Track Crossfade Duration (s)** | The crossfade between two consecutive tracks **of the same show**: the outgoing track fades out while the incoming one fades in over this many seconds (1 second is typical; 0 = the tracks follow each other without overlap; up to 10 seconds for soft transitions). The schedule lays consecutive rows out with exactly this overlap. |
| **Default Show Crossfade Duration (s)** | The transition **at a show boundary** (since 2026-09-27): the old show fades out over this many seconds while the first track of the new show starts at full level at once — so a show that begins with a jingle or ID is heard from its first beat. The same shape and value apply to every switch between **inputs** (track ↔ webstream ↔ Line-In): the incoming source is at full level immediately, the outgoing one fades out underneath; 0 = a hard switch. A webstream or Line-In that is scheduled in both shows keeps playing seamlessly. Start value 1 s. Both crossfade values are applied by the audio chain a few seconds after saving (planned restart at a quiet moment or track boundary); "Apply now" in Settings → Local Machine forces it. |
| *Crossfade per track type* | Settings → Track Types → *Crossfade Duration (s)* (since 2026-09-29) overrides the house value for every track of that type; empty = house value. Between two tracks the **smaller** of the two values applies, so a type with 0 always butts against its neighbours - the stock *Jingles* type starts with 0, because short, exactly timed elements must not be shortened by a music-length crossfade. At a switch between a track and a webstream or Line-In the smaller of the track's value and the Default Show Crossfade Duration applies. A change of the house values or of a track type re-lays the rows of all upcoming shows automatically; rows that have already started are never touched. |
| *No Fade per track type* | Settings → Track Types → *No Fade during Crossover* (since 2026-09-30) is the type's preset for the track editor's *Crossover* field: every track of the type that is set to *As the track type* keeps its full level while the neighbouring track fades in or out - the overlap itself stays as the type's Crossfade Duration says. Meant for jingles or IDs that should cut through the end of a song. A single track can still be set differently in the track editor; a track excluded from the crossover has no overlap to keep its level in. A change reaches the playout with the next schedule push; no rows are re-laid because the overlap does not change. |
| *Forward Metadata per track type* | Settings → Track Types → *Forward Metadata to the Stream* (since 2026-10-14) is the type's preset for the track editor's *Stream Metadata* field: unticked, every track of the type set to *As the track type* plays without artist / title on the stream - the players show "Station name - Show name" instead (jingles, station IDs, promos). A track can override it in its editor. |
| *Cue points per track type* | Settings → Track Types → (open a type) → *Analyze cue points*: whether the import detects the cue in and cue out (silence at the head and the tail) of tracks of that type. Decided once, at import, by the track's type - since 2026-11-09 the type a Media Type tag names. The Track Types list does not show the setting; open the type to see it. A track imported without cue points can get them later with **Cue Points** in the Library toolbar. |
| **Track Type Upload Default** | The track type assigned to new uploads that do not set one. Affects smart-block filters. Since 2026-11-09 a **Media Type** tag in the file that names a track type wins over it and over the type chosen in the upload dialog (Library → *Track type from the Media Type tag*). |
| **Trim overbooked shows after autoloading?** | Cuts the content of an autoloaded show that runs longer than the show. |
| *Import owner* | There is no setting: files picked up by the background scan of the Local Import Folder belong to the first administrator account (`admin`), files imported with **Scan Now** to the operator who clicked it. |

### Automation

| Field | Notes | Chapter |
|---|---|---|
| **Intro / Outro Autoloading Playlist** | Played at the start / end of every show with autoloading. | [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) |
| **Song-Request Pool (smart blocks)** | The smart blocks whose tracks listeners may request. | [Song Requests](./SONG_REQUESTS.md) |
| **Traffic-Alert Smart Block** | The block for traffic announcements. | [Traffic Alerts](./TRAFFIC_ALERTS.md) |
| **Show-Shift Filler Playlist** | Fills the gap when a show is shifted. | [Delayed Show Start](./DELAYED_START.md) |
| **Overwrite Podcast Episode Metatags** | Sets artist, title and album of downloaded episodes from the podcast feed. | [Library](./LIBRARY.md) |
| **Generate a smartblock and a playlist upon creation of a new podcast** | Creates a matching smart block and playlist for every new podcast subscription. | [Library](./LIBRARY.md) |

### Live Text Info

Collapsible section below General Preferences (since 2026-09-28). The
"now playing" line as a text file for other systems (website, displays,
aggregators): one UTF-8 line, always replaced, written by the playout at
every change of track, webstream, Line-In or DJ.

| Field | Notes |
|---|---|
| **Write the "now playing" line to a text file?** | Master switch. |
| **Live Text Format** | Same three variants as the Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) with the same fallbacks: a live source without artist and title shows *Station name - Show name*, silence shows the Off Air Metadata text. Independent of the Stream Label. |
| **Publish on the web** | The file is served at `http://<host>/live/now-playing.txt` (static file, no login, independent of the Public API switch). Reachable from the internet as soon as the web server is, like the widgets. |
| **Also write to file** | Optional absolute path (this machine or a network share). |
| **Push to an FTP server** | The connection fields appear once the switch is on.  On every change the file is uploaded via FTP, FTPS (explicit TLS) or SFTP to the remote path; own credentials, separate from the FTP import. SFTP needs a `curl` with libssh2 (the one shipped with Git for Windows; the Windows built-in curl cannot). Failures are logged; the next change retries. |
| **Delay (s)** | Since 2026-11-10.  The listener hears a change some seconds after the playout reports it (audio processing, stream buffers, the provider's relay, the player).  Every line is held back this many seconds and written at its own time, in order - a jingle followed by the next track within the delay still shows for its turn.  0 = at once (default), 0..60.  Measure the offset once: note when `/live/now-playing.txt` changes and when the new track is heard on a typical player. |

The line is built by the audio engine from the metadata it actually
sends to the stream, so DJ titles and webstream titles are included. A
changed setting takes effect at the next change, no restart.

### Radioplayer Feed

Collapsible section below Live Text Info (since 2026-11-10).
Distribution partners (for example a public broadcaster's audio app)
show stations that are not on the Radioplayer platform from a JSON feed
in the format of the Radioplayer "events" lookup, which they poll every
few seconds.  RASTATIME answers it at
`https://<host>/embed/radioplayer-events` - independent of Live Text
Info and of the Public API switch.

| Field | Notes |
|---|---|
| **Provide the "now playing" feed (Radioplayer events)?** | Master switch.  Off = the address answers 404. |
| **Access key** | Optional.  When set, the feed answers only with `?key=<value>` in the address (otherwise 403); give the partner the full address shown under the switch.  Letters, digits, `-` and `_`. |
| **Station ID (rpId)** | The ID the partner assigned, if any; otherwise empty. |
| **Station description** | `serviceDescription` of every entry; empty = the station description of this page. |
| **Number of previous tracks** | How many of the last played tracks are listed (0..20, default 7). |
| **Leave out tracks shorter than (s)** | Jingles and station IDs stay out of the previous tracks and out of "now" (default 60, 0 = everything). |
| **Suggested polling interval (s)** | Sent as `pollNext` (5..120, default 6). |
| **Delay (s)** | Since 2026-11-10.  The feed answers as of this many seconds ago, so now, next and the previous tracks change later (0..60, default 0).  The partner's polling, the 5 s cache and the partner's own systems already add a few seconds - start with 0 and set a value only after comparing the partner's app with what is heard. |

What the feed contains:

* **previous** - the last played file tracks from the playout history
  (what really went out), oldest first, as songs (`PE_E`) with title,
  artist, start and end time.
* **now** - the running file track as a song with its cover.  For a
  webstream, a Line-In, a live DJ or a jingle the running **show**
  (`PI`, name and description of the show, its start and end); with
  nothing on air the station itself (`SI`).
* **next** - the next track of the running show, else the next show.
* **Pictures** - the track's cover, else the show image, else the
  default cover (Settings → Widgets → Player).  Covers and show
  images are only linked while the Public API switch serves them
  (§2); otherwise the default cover.
* "now" follows the schedule like the Stream Player widget; at a
  transition it can be a few seconds off what is heard.  Changes on
  this page apply at once (the feed is cached for 5 s).

### TuneIn Settings

Collapsible section below General Preferences. Since 2026-09-28 the
playout sends the "now playing" information to TuneIn itself; before,
only file starts were pushed and the display went blank after five
minutes.

| Field | Notes |
|---|---|
| **Push metadata to your station on TuneIn?** | Master switch. When on, the playout sends title and artist at every start of a track and the show name at the start of a webstream or Line-In, and repeats the last update every four minutes (TuneIn removes a display that stays quiet for five minutes). Saving with the switch on tests the credentials against TuneIn and refuses invalid ones. |
| **Station ID**, **Partner Id**, **Partner Key** | From your TuneIn partner account (AIR API). The key never appears in a log. |

A changed setting is picked up at the next push; no restart. A live DJ
(Master / Show Source) is not announced; the last track stays on the
display until the next scheduled item.

### Dangerous Options

Collapsed by default; both buttons ask for confirmation and are for
administrators only.

| Button | Effect |
|---|---|
| **Delete All Tracks in Library** | Removes every track from the library and from future schedules (upstream). |
| **Clear Calendar** (since 2026-10-14) | Removes every show that has **not started yet**, with its content, and ends all repeats. The show on air and everything in the past stay, so the Playout History keeps its show names. A show without any instance left is deleted. The confirmation reports how many instances and shows went. |

> **How it works under the hood.** The values are rows of the
> `cc_pref` table (key / value).  Per-user values (language, time zone,
> table layouts) are `cc_pref` rows bound to the user.  Service
> configuration that cannot live in the database (database credentials,
> paths, station time zone, API key) is in `config/rastatime.conf`.

---

## 3. Status

Settings → **Status**.  From top to bottom:

| Section | Content |
|---|---|
| **RASTATIME Version** | The installed version. |
| **Components** | PDO and PostgreSQL libraries, database and RabbitMQ configuration, and the Windows services RASTATIME-PLAYOUT, -WORKER, -API, -ANALYZER, -ICECAST and -APACHE with their state. A service shown as stopped is the signal to look at it (`Get-Service RASTATIME-*` in PowerShell, or the [`CRASH_RECOVERY`](../operator/CRASH_RECOVERY.md) runbook). |
| **Disk Space** | Free and used space of the storage. |
| **Service restarts** | One **Restart** button per service (Analyzer, API, Apache, Icecast, Playout, Worker), each with what the service does and when a restart helps, plus **Restart All Services** (the interface is unreachable for about 10 seconds). |
| **Allowed addresses** | Addresses and networks that no login brake ever blocks. |
| **Blocked addresses** | Every currently blocked address or user per layer (web login, DJ dial-in, firewall) with **Unblock** and **Allow**. |

The two address lists are described in
[Users and Roles](./USERS_AND_ROLES.md) §8.

What a restart costs:

| Service | Effect of a restart |
|---|---|
| **Playout** | The schedule driver restarts; plan it outside a live show.  The audio engine (Liquidsoap) is a service of its own (RASTATIME-LIQUIDSOAP) and keeps playing what it has queued. |
| **Icecast** | Every listener and every source is disconnected; the outputs reconnect within seconds, listeners have to reconnect. Only in a quiet window. |
| **Apache** | The web interface is unreachable for a few seconds. |
| **API**, **Worker**, **Analyzer** | Background work pauses briefly; no effect on the stream. |

> **Operator tip.** Restart only the service that misbehaves.  The full
> sequence is in [`RESTART_ORDER`](../operator/RESTART_ORDER.md).

**Preflight warnings** are not a section of this page: they appear as a
banner on every page.  One example: **Podcast download failed** (since
2026-10-08) - when an automatic or manual episode download fails, a
warning names the podcast, the episode, the number of attempts, the last
attempt and the reason (HTTP code or "API unreachable").  It clears by
itself when the download succeeds later or the podcast is removed.
Check the feed and the episode's download address under Library →
Podcasts.

---

## 4. Frequently asked

### "I changed a setting but nothing happens."

Most settings take effect immediately or with the next page load.
Exceptions:

| Setting | Takes effect |
|---|---|
| Crossfades, streams, sound card | When the audio chain restarts - planned automatically at a quiet moment; **Apply now** in Settings → Local Machine forces it. |
| Primary and secondary colour, logo, favicon | With the next page load (F5). |
| Your own language | With the next page load; the login screen uses the Default Language. |
| Live Text Info, TuneIn | At the next change of track or source (the Live Text delay counts from that change). |
| Radioplayer Feed | At once (the feed is cached for 5 s). |

### "Is there a Tools menu, a log viewer or a DB console?"

No.  Maintenance scripts live on the station machine under
`infra\scripts` (for example
`infra\scripts\maintenance\rescan-playability.py`) and are described in
the operator documentation.  Logs are in `C:\RASTATIME\logs`.

### "How do I back up or restore the settings?"

Settings → **Backup** saves the database (with every `cc_pref` row) and
the configuration; see [Backup](./BACKUP.md) for restoring.
`config/rastatime.conf` carries passwords - never put it into version
control as it is.

### "Which settings can a Program Manager open?"

*My Profile*, *Show Templates*, *Auto DJ* and the producers of
*Archiving*.  Everything else under
Settings belongs to Admins.  See [Users and Roles](./USERS_AND_ROLES.md) §1-§2.

---

## 5. Playout Engine (Liquidsoap)

> **Service-level setting**, not a UI setting.  The RASTATIME-PLAYOUT
> NSSM service may carry `RASTATIME_PLAYOUT_ENGINE=liquidsoap` in its
> environment; that is the only accepted value.  Operator-only; not
> exposed in the web UI.

Since 2026-09-10 Liquidsoap is the **only** playout engine.  The
earlier mpv engine (with its FFmpeg streamers for the Icecast outputs)
and the never-finished VLC plan were removed from the code base after
Liquidsoap had carried every schedule item type (files, webstreams,
line-inputs, recording, DJ sources) in production since 2026-05-28.

What Liquidsoap provides:

- **Recording** is captured from the internal audio bus
  (post-switch, post-crossfade, post-amplify) — bit-identical
  to what listeners hear.  Format and bitrate follow Settings → Local
  Machine → Show Recording (default MP3 320 kbps).
- **Listener experience**: the Icecast mountpoints stay open
  through track/show changes — no reconnect, no counter reset.
- **DJ-Source routing** uses Liquidsoap's `input.harbor` +
  `switch(...)` natively — Master / Show DJ clients connect
  directly to the Liquidsoap-managed harbor (port 8001 by
  default, see [Streams](./STREAMS.md)).

**If the service refuses to start** with

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

the service environment still names the removed engine: set
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` (or remove the variable) in the
NSSM environment of `RASTATIME-PLAYOUT` and start the service again.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` are ignored and can
be removed.

**The engine start is visible in the playout log:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## 6. Alerts (since 2026-11-03)

Settings → **Alerts** (Admins).  RASTATIME sends a message when the
broadcast goes silent, when a service stops answering or when a
pre-flight warning appears, and an all-clear when the problem is gone.

| Field | Meaning |
|---|---|
| **Dead air after (seconds)** | Silence on the broadcast bus (below -50 dB, the silence fallback included) for this long raises *Dead air*; audio back for 2 s clears it.  5 to 3600, default 30.  The threshold is compiled into the audio engine and applies with its next planned restart. |
| **Reminder every (minutes)** | While a problem stays open; 0 = no reminders.  At most 20 messages per channel and hour. |
| **Services** | Playout (watched by the API service), API, Apache, Icecast, Analyzer and Worker, checked once a minute; two misses in a row raise an alert. |
| **Pre-flight warnings** | Every warning type of the dashboard banner raises an alert once and clears when it is gone. |
| **Send alerts by e-mail** | Switches the e-mail channel on (since 2026-11-04; before, one master switch for both channels).  The fields of the channel appear while it is ticked; saving refuses it without a server, a sender and a recipient. |
| **E-mail (SMTP)** | Server, port, encryption (STARTTLS, SSL/TLS, none), user name and password (login with authentication; the password is write-only), sender, comma-separated recipients.  The password-reset mail of the login page is not affected. |
| **Send alerts by Telegram** | Switches the Telegram channel on (since 2026-11-04), its fields appear while it is ticked; saving refuses it without a bot token and a chat id. |
| **Telegram** | Bot token from @BotFather (write-only) and comma-separated chat ids; the bot must be a member of the chat or group and have received one message.  A group id starts with a minus. |
| **Send test e-mail / message** | After saving: a test message with the stored settings, sent by the playout service. |

Both channels off: nothing is sent, the state is still tracked.  Settings
saved before 2026-11-04 keep working: a channel counts as switched on
while the old master switch was on and the channel is set up.  The
playout and the API service read the per-channel switches after their
next restart; until then they follow the old master switch, which is
on while any channel is.

Messages look like `[Station] ALERT: Dead air` with the time, the
detail and the reporting service, `STILL OPEN` for reminders and `OK`
for the all-clear.  Planned restarts of the audio engine (nightly,
settings) suppress new alerts for three minutes.

What is not covered yet: a dead uplink (no channel can leave the
studio), the web interface being slow rather than down, and Signal,
WhatsApp or SMS (see BACKLOG).

## Where to go next

* Follow the link in the table of §1 to the dedicated chapter of a
  Settings page.
* [Users and Roles](./USERS_AND_ROLES.md) — who may open which page.
* [`docs/operator/INSTALL.md`](../operator/INSTALL.md) — the settings
  made at installation.
