# Webstreams

> **Where you are in the manual.** Webstreams are a Library
> item type alongside tracks, smart blocks, playlists, and
> line-ins. See [Library](./LIBRARY.md) for the overall
> Library tour; this chapter covers the Webstream-specific
> bits.

A **Webstream** is a URL pointing at another HTTP audio
source — typically an Icecast or Shoutcast stream operated by
someone else. When scheduled into a show, the playout engine
connects to the URL and broadcasts its content for the
configured duration.

Webstreams are the simplest way to syndicate external
content: a hourly news bulletin relayed from the BBC, a
local weather feed, an automated music service. The remote
source does all the heavy lifting; your station only needs to
include the URL on the schedule.

---

## 1. The Webstream library entry

Library → filter chip **Webstream** (orange).

```
   ┌───────────────────────────────────────────────────────────────┐
   │  Type      │ Title          │ URL                     │ Length│
   ├────────────┼────────────────┼─────────────────────────┼───────┤
   │  Webstream │ BBC Radio 1    │ http://stream.bbc.co.uk/│ 60:00 │
   │  Webstream │ FIP Live       │ http://icecast.radiofra/│ 30:00 │
   │  Webstream │ Weather Hourly │ http://wx.example.com/m/│ 03:00 │
   └────────────┴────────────────┴─────────────────────────┴───────┘
```

Each webstream has:

| Column | Meaning |
|---|---|
| **Title** | Display name. Used everywhere. |
| **URL** | The HTTP(S) source URL. |
| **Length** | Default duration when scheduled — how long the webstream plays per use. Format `01h 05m 05s` since 2026-05-19. |

The Length is the *only* time-sensitive parameter — a
webstream "plays forever" from the remote source's
perspective; RASTATIME's Length tells the playout when to
disconnect and move on to the next schedule item.

---

## 2. Creating a Webstream

Library → **+ New** → **Webstream**.

```
   ┌───────────────────────────────────────────────────────────────┐
   │  New Webstream                                                │
   ├───────────────────────────────────────────────────────────────┤
   │   Name:             [                                       ] │
   │   Source URL:       [                                       ] │
   │   Default Length:   [01h 00m 00s   ]                          │
   │   Description:      [                                       ] │
   │   Mime Type:        [auto-detect ▾]                           │
   ├───────────────────────────────────────────────────────────────┤
   │                                       [Cancel ]  [ Save  ]    │
   └───────────────────────────────────────────────────────────────┘
```

| Field | Notes |
|---|---|
| **Name** | Required. The visible label in the library and on the schedule. |
| **Source URL** | Required. The HTTP(S) URL of the audio stream. Direct stream URL, not a player landing page. Examples: `http://stream.bbc.co.uk/...`, `http://icecast.example.com:8000/mountpoint`. |
| **Default Length** | Required. `HHh MMm SSs` format. See §3 for the seconds-precision detail. Since 2026-09-30 a changed length follows into the rows of the upcoming shows that schedule the webstream (rows that have already started are left alone), and those shows are laid out again - a relay that should fill a show no longer needs the shows refilled. |
| **Description** | Free-text, optional. Shown in the library row tooltip and on the public schedule export. |
| **Mime Type** | Auto-detect by default; override only if the source mis-reports its MIME type. |

Click **Save**. The webstream appears in the library
immediately and can be scheduled at any future time.

> **Operator tip.** Test the URL in a browser or with
> `curl -I` before saving. RASTATIME does not pre-flight the
> URL at save time — a broken URL only surfaces when the
> webstream is actually scheduled and the playout tries to
> connect.

> **How it works under the hood.** Webstreams live in
> `cc_webstream` (id, name, description, url, length,
> creator_id, mtime). When scheduled, a `cc_schedule` row
> references the webstream via `stream_id`. At play time, the
> playout engine opens an HTTP source via libVLC and
> publishes its decoded PCM to the output mixer. See
> ARCHITECTURE §10.

---

## 3. Default Length with seconds precision (Section 23.17)

Pre-2026-05-19 the Default Length field accepted only hours
and minutes ("01h 05m"). The underlying database column is a
PostgreSQL `interval` which always stored "HH:MM:SS"
internally, but the seconds component was hard-zero and the
form's parser would not accept it.

Since 2026-05-19, the form accepts an **optional third
seconds component**:

```
   01h 05m 05s    ← 1 hour 5 minutes 5 seconds
   01h 05m        ← 1 hour 5 minutes (seconds optional)
        05m       ← 5 minutes (hours optional)
            45s   ← 45 seconds (a 45 s station ID via webstream)
```

The display readback always shows all three components
("01h 05m 00s") for visual consistency — operator decision
2026-05-19. The validator is fully backwards-compatible: any
pre-2026-05-19 input ("01h 05m") still parses.

> **Why this matters.** Short stings, station IDs, and
> jingles served via a webstream URL previously had to be
> rounded up to one minute. A 30 s jingle scheduled as "1
> minute" played the jingle followed by 30 s of silence (or
> 30 s of the next playlist iteration). With seconds
> precision the jingle slot is exactly 30 s and the next
> item starts on time.

> **How it works under the hood.** Three hot spots in
> `application/models/Webstream.php` carry the seconds
> handling:
>
> - `getDefaultLength()` formats with `%H:%I:%S`.
> - `analyzeFormData()` regex grows an optional `(<n>s)`
>   group; the parser is `^(?:([0-9]{1,2})h)?\s*(?:([0-9]{1,2})m)?\s*(?:([0-9]{1,2})s)?$`.
> - `save()` writes the `DateInterval` as `%H:%I:%S` so the
>   persisted value reflects the new precision.
>
> See ARCHITECTURE §23.17 + commit fae0fc5.

> **Out-of-scope unification.** The same duration concept
> shows up in three other places: Line-Ins (uses its own
> parser via `LineinController::_parseHmsToSeconds`), Smart
> Blocks (`SmartBlockCriteria` strict `HH:MM:SS`), and the
> show-edit form. Unifying all four into one helper would
> remove the inconsistency (Webstream displays
> "01h 05m 05s" while Tracks display "1:05:05.0") but
> requires touching three live consumers and is deferred.

---

## 4. Scheduling a Webstream

Same as any library item:

### 4.1 Directly onto a show

Show-builder → drag the webstream row onto the show. A
schedule item appears with the webstream's name and Default
Length.

Click the item → **Edit** → override the duration for this
specific use if you need a different length than the
default.

### 4.2 Inside a playlist

Playlist editor → drag the webstream onto the playlist. The
playlist row carries the webstream + its Default Length and
behaves like any other playlist item.

### What plays when the slot starts?

**Liquidsoap engine path (production default since 2026-05-29):**

1. Pypo sends three telnet commands to Liquidsoap:
   - `webstream.url <URL>` — sets the HTTP URL on the
     dedicated `input.http` source.
   - `var.set webstream.gain = <factor>` — sets the
     per-stream amplify factor (dB → linear conversion
     happens in Pypo).
   - `webstream.start` — tells the source to connect.
2. Liquidsoap's `input.http` source opens the HTTP
   connection and buffers a few seconds of audio (5 s clock
   bridge, up to 10 s stream buffer).  Since 2026-09-04 this
   already happens **10 s before the slot** ("pre-warm") with the
   bus *gate* closed, so the buffer is full when the slot starts.
3. At the slot start Pypo opens the gate; the bus-switch routes
   audio to the webstream source within a frame — listeners
   hear the stream.  The **same** stream in the next show simply
   keeps playing (hand-over of the bookkeeping only, no bounce).  A
   *different* webstream directly after a webstream cannot be
   pre-warmed (one stream source): it connects at the slot start
   and is on air once its buffer is full, ~5 s.
4. At the configured duration Pypo closes the gate: the bus
   fades the webstream out under the next item over the Default
   Show Crossfade Duration (Settings → General; the next item is at
   full level at once, 0 = a hard switch), then
   sends `webstream.stop`.  The next item starts on time instead
   of waiting for the buffer to drain.

**Upstream stalls (since 2026-09-06):** some stream servers stop
sending mid-stream without closing the connection — Liquidsoap does
not notice on its own, and the slot would stay silent until it ends.
A watchdog now guards every on-air webstream: if the source stops
producing audio for a few seconds, the playout reconnects it (a clean
stop + start).  A fresh connection is back on air within a few
seconds, and the clean stop frees the listener slot on the server so
its connection limit is not filled up by dead connections.  A server
that refuses new connections still produces silence until it accepts
one again.  Since 2026-09-07 the watchdog runs inside the audio
engine itself: a frame counter checks the source every two seconds
and reconnects after two silent checks, without any polling traffic
between playout and engine (the Windows build of Liquidsoap leaks
memory on every such poll).  The playout-side poll of 2026-09-06 was
removed on 2026-09-15 after a quiet week.  Since 2026-09-08 every
webstream slot, and every reconnect, opens a brand-new connection with its own buffer instead of
reusing one long-lived input: on the Windows build a reused input
sometimes took a minute or more to reconnect, and a slot could start
with a few seconds of the previous stream still in the buffer.  Both
are gone; a slot now starts on its own stream, and the pre-warm ten
seconds before the slot gives the fresh connection time to fill up.  A
dropped connection that comes back on its own after an outage is
closed again within seconds, so the stream server never keeps a
listener slot occupied by a connection nobody is listening to.

**Recording behaviour (new since Phase E, 2026-05-29):**
Scheduled webstreams now land in the per-show `.mp3`
recording archive — the audio flows through the Liquidsoap
internal bus that `output.file` taps, so it gets captured
alongside any regular tracks in the same show.  Pre-Phase E,
webstream-only shows had silent recordings.

**Initial-show latency:** with pre-warming (since 2026-09-04)
a webstream slot starts without a gap — the stream was connected
and buffered 10 s earlier.  Only a webstream that could not be
pre-warmed (see step 3) still needs ~5 s to buffer.  Listener-side
players add their own ~10 s buffer, so the effective
end-listener-perceived delay is dominated by the player-side
buffer.

### What happens if the URL is unreachable?

`input.http` retries the connection every **2 seconds**
(`poll_delay`) with a **10-second timeout** per attempt
(`timeout`). While the retries run, `source.is_ready` stays
false and the bus-switch falls through to scheduled
(silence). The retries continue for the full duration of
the scheduled slot.

The Liquidsoap log captures every failed connection attempt:

```
[input.http:3] Connection refused: <url>
[input.http:3] Connecting to <url> ...
```

Operator-visible symptom: the show plays silence for its
full duration. No warning popup in the dashboard; check the
Liquidsoap log — since 2026-09-18 the newest
`C:/rastatime/logs/liquidsoap-stdout-*.log` slice — if a
scheduled webstream stayed silent.

> **Operator tip.** A webstream that "sometimes plays
> nothing" usually means the source's URL changed and the
> webstream library row points at the old one. Verify the
> URL in a browser. Many news / weather feeds rotate URLs
> daily — bookmark the persistent direct-stream URL, not the
> dynamically-redirecting player page.

---

## 5. Editing or deleting a Webstream

Same actions as any library item:

| Action | Effect |
|---|---|
| **Edit** | Open the dialog. Saves propagate to *all* future scheduled uses (the URL change takes effect on the next play). Existing playlist references keep their Default Length unless the operator edits the playlist too. |
| **Delete** | Remove the webstream. All `cc_playlistcontents` and `cc_schedule` rows referencing it are removed (CASCADE). |

---

## 6. Stream gain (per-stream input gain)

Webstreams from third-party sources are often louder or
quieter than the rest of your library. To normalise the
loudness:

Edit the webstream → **Input Gain (dB)** → set a positive
value to boost or negative to attenuate.

| Setting | Effect |
|---|---|
| `0.0` (default) | No gain change. |
| `+3.0` | Boost by 3 dB. |
| `-6.0` | Attenuate by 6 dB. |

The gain is applied at the playout engine before the audio
hits the output mixer; the operator-machine speakers and the
output stream both receive the adjusted level.

> **Operator tip.** Use a loudness-meter pass over a few
> minutes of the webstream's content to set the right gain.
> A common operator workflow: schedule the webstream as a
> test for 10 minutes, monitor the output stream with a
> level meter (e.g. VLC's audio meter), adjust gain, repeat.

> **How it works under the hood.** Migration 0048 added
> `cc_webstream.input_gain_db` (FLOAT).  The stream engine
> wraps the webstream source in an `amplify`; the playout sets
> its factor (`var.set webstream.gain`, converted from dB as
> 10^(dB/20), e.g. `-6` dB → `0.50`) every time a webstream
> starts — at the pre-warm 10 s before the slot, or at the slot
> start — and after a DJ hands back.  A webstream without a
> gain gets the factor `1.0` explicitly, so no stream inherits
> the previous one's level.  Until the Liquidsoap engine took
> over (2026-05-29) the playout applied an FFmpeg `volume`
> filter instead.  See ARCHITECTURE §23.10.

---

## 7. Webstreams in autoloading playlists

A webstream can be the entire body of an autoloading
playlist — useful for "every Monday 14:00 we relay X" without
manually scheduling the URL each week.

Limitations:

- A webstream inside a **Repeat until full** body produces
  repeated short connection attempts as each "iteration" of
  the body fires. Avoid — use a single long-duration
  webstream row instead.
- Smart blocks inside a webstream-bearing playlist do not
  get the outro-reserve treatment the same way they would
  in a track-only body. Schedule conservatively.

See [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §5
for the general "what works / what does not" guidance.

---

## 8. Frequently-asked

### "Why is my webstream cutting off after a few seconds?"

Most likely the **Default Length** is set very short. Check
the library row's Length column.

### "Can I schedule the same webstream on two shows simultaneously?"

No. There is one playout engine and one output mixer. Two
shows cannot run at the same time on the same output. (You
*can* have two different output streams play different
content — see [Streams](./STREAMS.md).)

### "Why does the webstream sound bad / glitchy?"

Common causes:

- The webstream URL is intermittent (source-side problem).
- The source is in a codec the playout engine cannot decode
  cleanly. Check the MIME type and try setting it explicitly.
- Network latency to the source exceeds the buffer. Try a
  shorter URL or a closer source.
- The operator-machine network has packet loss. Verify with
  `Test-Connection -Continuous <hostname>`.

### "Can I record a webstream's content with Record-per-Show?"

Yes. The recorder taps the on-air output; whatever is
playing (track, webstream, line-in) is captured. See
[Record-per-Show](./RECORD_PER_SHOW.md).

### "How do I authenticate to a password-protected source?"

Inline credentials in the URL:

```
   http://user:password@stream.example.com/private
```

RASTATIME passes these directly to libVLC's HTTP client. For
sources requiring a Bearer token or a session cookie, you
will need to set up a small relay (e.g. a local nginx that
proxies the authenticated source) and point the webstream
at the relay.

### "Can I use an HLS (.m3u8) URL?"

Yes — libVLC handles HLS. Use the .m3u8 master playlist URL
as the Source URL. The default Mime Type "auto-detect" picks
HLS correctly.

### "Can I use a YouTube live URL?"

Not directly — YouTube does not expose a stable direct
stream URL. Operator workaround: use `yt-dlp` to resolve the
current stream URL and update the webstream library row on a
cron. Not officially supported.

---

## Where to go next

* [Library](./LIBRARY.md) — overall Library tour.
* [Calendar](./CALENDAR.md) — scheduling library items.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  webstreams as autoloaded content.
* [Streams](./STREAMS.md) — the *outbound* side; webstreams
  here are the *inbound* side.
