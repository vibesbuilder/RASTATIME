# Streams

> **Where you are in the manual.** This chapter covers
> **outbound streams** — what RASTATIME publishes for
> listeners. For **inbound** (other people's streams that
> RASTATIME relays into a show), see
> [Webstreams](./WEBSTREAMS.md). For the operator-machine
> sound-card output, see [Local Machine](./LOCAL_MACHINE.md).

A **stream** is one Icecast (or Shoutcast) mountpoint that
RASTATIME broadcasts to listeners. A station can configure up
to **four output streams**, typically used for:

- **Main quality** (192-320 kbps) for desktop / fixed
  listeners.
- **Mobile quality** (96-128 kbps) for cellular listeners
  with limited data.
- **Lossless / archive** (FLAC) for high-end listening or
  contribution to a syndicator.
- **Spare / standby** for failover or testing.

Each stream has its own bitrate, codec, mountpoint, and can
even point at a different Icecast server (e.g. a local
Icecast for the main stream and a cloud relay for the
mobile stream).

---

## 1. The Streams settings page

Settings → **Streams**.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Stream Settings                              [   Save Changes  ]│
   ├─────────────────────────────────────────────────────────────────┤
   │  Stream 1   ☑  Enabled              Status: ● Connected         │
   │    Type:        [Icecast ▾]                                     │
   │    Server:      [localhost            ]   Port:  [8000  ]        │
   │    Mount:       [/rastatime            ]                         │
   │    Source User: [source                ]                         │
   │    Password:    [********              ]                         │
   │    Format:      [MP3 ▾]   Bitrate: [192 kbps ▾]                 │
   │    Channels:    [Stereo ▾]                                      │
   │    Sample Rate: [44.1 kHz ▾]                                    │
   │    Stream Name: [My Radio Station                    ]           │
   │    Stream URL:  [https://my-station.example.com      ]           │
   │    Genre:       [Various                             ]           │
   │    Description: [My community radio station          ]           │
   │                                                                 │
   │  Stream 2   ☐  Enabled                                          │
   │  Stream 3   ☐  Enabled                                          │
   │  Stream 4   ☐  Enabled                                          │
   └─────────────────────────────────────────────────────────────────┘
```

Each of the four stream cards has the same field set; only
**Stream 1** is enabled by default (the install default).

### Per-stream fields

| Field | Notes |
|---|---|
| **Enabled** | Master switch for this stream. When off, the playout does not connect. |
| **Type** | **Icecast** (recommended; modern, free, widely supported), **Shoutcast** (legacy; pre-2010 listeners), **Custom** (raw HTTP MP3 push to a non-standard target). |
| **Server / Port** | Where the Icecast server is. `localhost:8000` for the default install. Use a remote IP / hostname if streaming to a cloud Icecast. |
| **Listener URL** (read-only) | Since 2026-10-04 an output on the local Icecast is published as `<public URL>/stream/<mount>` (e.g. `https://rastatime.example.org/stream/rastatime`): the web server hands `/stream/` to Icecast, so the player, the widgets and the embed codes use the same address in the LAN and on the internet and port 8000 stays internal. An output on a remote Icecast keeps its own `http://host:port/mount`. |
| **Mount** | The mountpoint URL path, with leading `/`. e.g. `/rastatime` becomes `http://<server>:<port>/rastatime`. Must be unique per Icecast server. |
| **Source User / Password** | Credentials Icecast expects from a source client. Set in the Icecast config file (`config/icecast.xml`); the default install uses `source` / `hackme`. Change both for production. |
| **Format** | **MP3** (universal compatibility), **AAC** (better quality at low bitrates), **OGG Vorbis** (free, less ubiquitous), **OPUS** (modern, very efficient), **FLAC** (lossless, very large). |
| **Bitrate** | Kbps. Picking the right value is the most consequential per-stream decision; see §2. |
| **Channels** | **Stereo** (default), **Mono** (saves ~30 % bandwidth for talk-only). |
| **Sample Rate** | 22.05 / 32 / 44.1 / 48 kHz. 44.1 kHz is the universal default. |
| **Stream Name / URL / Genre / Description** | ICY metadata advertised to listeners. Appears in their player as the station's name + click-through. Since 2026-09-13 all four are rendered; an empty Name or Description falls back to the station name (Icecast used to show "Unspecified name"). |

### Stream Label and Off Air Metadata

What listeners see as the "now playing" title in their player.  Both
fields sit on the Streams page above the per-stream blocks; the station
name comes from Settings → General.

| Source on air | Artist - Title | Show - Artist - Title | Station name - Show name |
|---|---|---|---|
| Scheduled track | Artist - Title | Show - Artist - Title | RASTATIME - Show |
| Webstream with its own titles | title of the source stream | Show - title of the source stream | RASTATIME - Show |
| Webstream without titles, Line-In | RASTATIME - Show | RASTATIME - Show | RASTATIME - Show |
| DJ (BUTT / Mixxx) | title sent by the DJ software, else RASTATIME - Show | Show - title sent by the DJ software, else RASTATIME - Show | RASTATIME - Show |
| Nothing scheduled | Off Air Metadata text | Off Air Metadata text | Off Air Metadata text |

- **Off Air Metadata** replaces the last track's title as soon as
  nothing is on air (before 2026-09-13 the old title stayed for hours).
- Changes to either field take effect within one schedule refresh
  (about two minutes), no restart needed.
- The label is written into the stream's title metadata, so it applies
  to MP3/AAC (ICY), to OGG (in-band comments) and to the recordings.

### Loudness Normalization (ReplayGain / EBU R128)

Evens out the level of scheduled tracks so that a quiet folk recording
and a loud club mix reach listeners at the same loudness.  Three modes,
selected on the Streams page; every description is available as a help
icon next to its field.

Since 2026-10-08 the loudness settings and the Output Processing (Stereo
Tool) below share the segment **Audio Processing**, under Stream Label
and Off Air Metadata.  Like the segments under Settings → General it
starts collapsed: click its bar to open it.  After a save with an
invalid value it opens by itself.  The *Replay Gain Modifier* slider
(ReplayGain mode only) sits directly under the mode.

| Mode | What it does |
|---|---|
| **Off** | Every track plays at its own level. |
| **ReplayGain** | The ReplayGain value measured at import plus the *Replay Gain Modifier* slider (the behaviour of earlier versions). |
| **EBU R128** | Every track is measured by the broadcast loudness standard (ITU BS.1770 / EBU R128) and played at the **Target Loudness**; a peak limiter on the output bus keeps the **True Peak Ceiling**. |

Settings for EBU R128:

- **Target Loudness (LUFS)** — the integrated loudness every track is
  played at.  EBU R128 specifies −23 LUFS for broadcast; web streams
  commonly use louder targets between −18 and −16 LUFS.  The value is
  free; −23 is the default.
- **True Peak Ceiling (dBTP)** — the level no peak may exceed (default
  −1 dBTP).  A quiet track is boosted only as far as its measured true
  peak allows; the limiter on the bus catches the rest.
- **Loudness measurement** — files imported from now on are measured
  automatically.  *Measure missing files now* queues every file without
  a measurement for the analyzer; *Re-measure all* queues the whole
  library.  Measurement runs in the background, a few seconds per file;
  the line "Measured: N of M files" shows the state after a page reload.
  Until a track is measured it plays with its ReplayGain value shifted
  to the target.

Notes:

- A change of mode, target or ceiling takes effect at the next schedule
  refresh (about two minutes) for the track gains; the bus limiter is
  applied by the playout's planned restart at the next track boundary.
- Live sources (DJ, webstream, Line-In) are not affected by this stage;
  their level is what the source delivers.
- The measured values are stored per file (integrated loudness, true
  peak, loudness range) and survive re-imports of the settings.

### Output Processing (Stereo Tool)

Optional, off by default.  When enabled, the playout runs the whole
output - every Icecast stream, the 24/7 recording and the Main Output -
through [Stereo Tool](https://www.thimeo.com/stereo-tool/) by way of
Liquidsoap's `stereotool()` operator: a broadcast processor with a
BS.1770 loudness controller, multiband processing and a final limiter.
This is the stage that makes the stream a distribution partner measures
R128-compliant regardless of its source; the Loudness Normalization above
only evens out the files.  Every field's explanation is available as a
help icon: next to the switch, and right of the label for the three
fields below it.

| Field | Meaning |
|---|---|
| **Output Processing (Stereo Tool)** | The switch.  Off by default; a station without Stereo Tool simply leaves it off. |
| **Stereo Tool library (DLL)** | Full path of the 64-bit Stereo Tool library for Liquidsoap on the studio machine (from the Stereo Tool download page).  The page shows whether the file exists; the setting is used only when it does. |
| **Stereo Tool preset (.sts)** | Optional.  A preset exported from the Stereo Tool application; without one the library starts with its defaults, which process nothing at all.  RASTATIME ships `config/stereotool/rastatime-r128-transparent.sts` *(since 2026-10-21)*: no processing, only a true-peak limiter at −1 dBTP with unity gain - the peak side of EBU R128, while the loudness side comes from the levelled sources.  See the README next to it for the measurements. |
| **Stereo Tool licence key** | The key from your Stereo Tool account.  Stored on the server, never shown again; leave blank to keep the stored key, enter `CLEAR` to remove it.  Without a licence the library runs with the restrictions of the free version. |

Notes:

- A change is applied by the playout's planned Liquidsoap restart (quiet
  moment or next track boundary), like every other setting that is baked
  into the Liquidsoap script.
- Safety net: a missing library file leaves the output untouched, and if
  the fresh Liquidsoap instance does not stay up after a start with
  Stereo Tool (incompatible library, refused licence), the playout
  restarts it **without** Stereo Tool, keeps it off until the next
  PLAYOUT restart and raises the preflight warning
  `stereotool_unavailable`.  The broadcast never depends on the plugin.
- Stereo Tool adds processing latency to everything downstream; the
  schedule is not affected, every output shifts by the same amount.

### Stream status badge

The badge to the right of each enabled stream's name:

| Badge | Meaning |
|---|---|
| ● **Connected** (green) | Playout connected; broadcasting. Listeners can tune in. |
| ◐ **Connecting** (yellow) | Mid-connection attempt. Should transition within a few seconds. |
| ● **Disconnected** (red) | Playout cannot connect. Common causes: Icecast not running, wrong credentials, port blocked. |
| ◯ **Disabled** (grey) | Stream is configured but the master switch is off. |

The badge refreshes every 5 seconds via the
`/api/v2/streams` endpoint.

> **Operator tip.** A red badge on Stream 1 means listeners
> hear nothing. Check Icecast (`Get-Service icecast2`),
> verify credentials, confirm port 8000 is reachable. See
> [`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md).

---

## 2. Picking a bitrate

The single most-consulted setting. Guideline:

| Use case | Format | Bitrate | Channels | Sample Rate |
|---|---|---|---|---|
| Music, main quality | MP3 | 192 kbps | Stereo | 44.1 kHz |
| Music, premium / FLAC fans | MP3 | 320 kbps | Stereo | 44.1 kHz |
| Music, FLAC archive | FLAC | (variable, ~700-1000 kbps) | Stereo | 44.1 kHz |
| Talk show / spoken | MP3 | 96 kbps | Mono | 44.1 kHz |
| Mobile / cellular | AAC | 64 kbps | Stereo | 44.1 kHz |
| Spare / debug | MP3 | 128 kbps | Stereo | 44.1 kHz |

### Why these and not others

- **AAC is better than MP3 at low bitrates** (< 128 kbps).
  At 64 kbps stereo, AAC produces clearly better quality
  than MP3.
- **MP3 above 192 kbps stereo** is the sweet spot for
  ubiquity + quality. Anything more is hard to hear the
  difference on most playback setups.
- **OPUS is the technically-best modern codec** but some
  legacy hardware players do not support it. Use OPUS only
  if you control your listener base.
- **OGG Vorbis** is fine but provides little advantage over
  MP3 for most listeners and worse compatibility.
- **FLAC** is huge and only worth running for archives or
  contributions to other broadcasters.

### Bandwidth math

Each enabled stream uses bandwidth equal to
`bitrate × max_concurrent_listeners`. A 192 kbps stream with
50 concurrent listeners uses ~9.6 Mbps outbound.

If your operator-machine internet uplink is 10 Mbps, that
192 kbps stream cannot scale past ~50 listeners. Solutions:

- Run a **mobile** stream at 96 kbps for capacity (200
  listeners on a 10 Mbps link).
- Use a **cloud Icecast relay** that handles many more
  listeners than your home uplink can.

---

## 3. Live Sources

In addition to the scheduled content, RASTATIME accepts two
**live source** connections per show:

| Source | Purpose |
|---|---|
| **Show DJ** | Per-show login. The show's primary host connects from anywhere and takes the show live. Username + password set on the show's edit form (**Live Stream Input** section). |
| **Master DJ** | Station-wide login. A producer / engineer can take over any time, overriding whatever is on air. Username + password set under Settings → Stream Settings → **Master Source**. |

When either live source connects, the source switcher routes
its audio to the output mixer in place of the scheduler's
content. When the live source disconnects, the source
switcher reverts to the schedule.

Since 2026-09-09 the engine itself reports every connect and
disconnect to the playout the moment it happens, so the switch is
immediate; the playout only double-checks over its command link
(machine setting `RASTATIME_DJ_RECONCILE_SECONDS`, default 600
seconds). A DJ who simply closes the connection is noticed within
the engine's network timeout of 5 seconds (machine setting
`RASTATIME_HARBOR_TIMEOUT_SECONDS`); a DJ whose connection stalls for
longer is dropped and has to reconnect, which BUTT does on its own.
Disconnecting a DJ from the Dashboard takes effect immediately.

> **Operator tip.** Master DJ takes precedence over Show DJ.
> A station engineer can step in mid-show via the Master
> source and the Show DJ is muted (still connected, just not
> on air) until the Master disconnects.

**Switch Transition Fade (s)** (Settings → Streams, since 2026-09-28,
start value 1 s) shapes the hand-over: when a DJ connects, the DJ is on
air at once and the programme fades out underneath over this many
seconds; when the DJ disconnects, the DJ fades out over the same time
and the programme returns at full level at once. 0 = a hard switch. The
value is applied by the audio chain a few seconds after saving (planned
restart at a quiet moment or track boundary). Before 2026-09-28 the
field had no effect; both directions were a 50 ms switch.

On the Streams page the **Live Broadcasting** section has three blocks:
**DJ Hand-over** (the fade above), **Master Source** and **Show Source**
(the connection data, see *Connecting as a Live Source* below).  Since
2026-10-08 each block's one-line explanation is a help icon right of
its title.

### Connecting as a Live Source

Hosts use any audio-broadcasting software (BUTT, Mixxx, RadioDJ,
SAM Broadcaster) configured with:

| Field | Value |
|---|---|
| Server | The station's public hostname or IP |
| Port | The **Master Source Port** / **Show Source Port** shown under Settings → Streams (8001 by default; 8000 is the listener port) |
| Mount | The **Master Source Mount** / **Show Source Mount** shown under Settings → Streams (`main` and `show` by default) |
| Username | Master DJ: the username under Settings → Streams → **Master Source**. Show DJ: a registered host's RASTATIME login, or the custom username of the show's **Live Stream Input** section |
| Password | The matching password |
| Format | MP3 (matching the station's main stream format is preferred) |

Once connected, the audio appears on the output stream
within ~1 second.

> **How it works under the hood.** The source-input port is a
> Liquidsoap harbor inside the playout engine. Every login is
> checked the moment the client connects (since 2026-09-10): the
> engine asks the playout, the playout asks the web application,
> which applies the settings above. For the Show DJ that means
> the show on air right now, so a Show DJ cannot log in before
> the show starts. Only while the playout itself is unreachable
> does the engine fall back to the static harbor password from
> `libretime.conf`. See ARCHITECTURE §23.27 (addendum 2026-09-10).

---

## 4. Monitoring stream health

### From the UI

Settings → Streams shows the badge per stream. The
**System Status** page (Help → System Status) summarises:

- Per-stream connection state.
- Current listener count per stream.
- Peak listener count today.
- Bytes sent today.

### From the Icecast admin interface

`http://<server>:8001/admin/` (default user `admin`,
password set in `config/icecast.xml`).

The Icecast admin shows a wealth of per-listener data:

- Each listener's IP, user-agent, connection duration.
- Per-mount byte rate.
- Listener kick / source-disconnect controls.

### From the API

`GET /api/v2/streams` returns the full state of every
configured stream as JSON. Useful for external monitoring
(Prometheus, Nagios, Uptime Robot).

```json
{
  "streams": [
    {
      "id": 1,
      "enabled": true,
      "state": "connected",
      "server": "localhost",
      "port": 8000,
      "mount": "/rastatime",
      "listener_count": 23,
      "peak_today": 47
    },
    ...
  ]
}
```

> **Operator tip.** Wire the `/api/v2/streams` endpoint into
> your existing monitoring. A red Stream 1 means listeners
> hear nothing — this is the #1 alert you want.

---

## 5. Stream Auth (listener-side)

By default, all streams are **public** — any HTTP client
can tune in.

To restrict listening to authenticated users:

1. Configure listener auth in `config/icecast.xml`:
   ```xml
   <mount>
     <mount-name>/rastatime</mount-name>
     <authentication type="url">
       <option name="listener_add" value="http://<station>/icecast-auth.php"/>
     </authentication>
   </mount>
   ```
2. Restart Icecast.
3. The `icecast-auth.php` script (shipped with RASTATIME)
   authenticates against `cc_subjs`.

Listeners are then prompted for their RASTATIME username +
password when tuning in.

> **Why this is rarely used.** Most community / commercial
> stations want a public stream. Listener auth makes sense
> for paid subscriber stations or internal /
> staff-only feeds. The default install ships listener auth
> off; turn it on per-mount as needed.

---

## 6. Multiple Icecast servers

Each of the four streams can target a **different Icecast
server**. This is the standard setup for:

- **Local + cloud**: Stream 1 to local Icecast (low-latency
  for the operator's own monitoring), Stream 2 to a cloud
  Icecast (high listener capacity).
- **Geographic distribution**: Stream 1 to EU Icecast,
  Stream 2 to US Icecast (each serves its region's
  listeners).

The playout encodes once (per stream) and pushes
independently. Failure of one server does not affect the
others.

> **How it works under the hood.** Each stream maps to one
> `libvlc_VLM` source with its own
> `#transcode{}:standard{access=shout,...}` output chain.
> The streams run as independent threads inside the
> RASTATIME-PLAYOUT service. See ARCHITECTURE §10.

---

## 7. Frequently-asked

### "How many concurrent listeners can RASTATIME handle?"

RASTATIME itself only encodes once per stream. Listener
capacity depends on:

- **Icecast** — handles thousands of concurrent listeners per
  server on modest hardware.
- **Network uplink** — bitrate × listener_count must fit
  within the operator-machine's outbound capacity.

For more than ~50-100 listeners, run Icecast on a
cloud server with a fat uplink, not the operator's home
internet connection.

### "Can I have an HLS / DASH stream output?"

Not directly — RASTATIME outputs Icecast / Shoutcast HTTP
streams. To get HLS, run an external repackager
(`ffmpeg -i icecast-url -hls_time 6 ...`) reading from the
Icecast mountpoint.

### "Why is my stream's listener count always 0?"

Three possibilities:

1. No one is listening (most common — verify by checking
   the Icecast admin).
2. The badge is wrong (try refreshing the page; the badge
   refreshes every 5 s but can lag).
3. Listeners are connecting to a different mountpoint than
   the one configured (verify the mount path matches).

### "I changed the bitrate but listeners say it sounds the same."

Most player software caches the connection for the duration
of the listen session. Listeners need to reconnect to pick
up the new bitrate. Tell them to refresh / reload the
station URL.

### "Can I change the stream's bitrate while it's playing?"

Yes. Save the new bitrate; the playout engine reconnects
the stream with the new parameters. Listeners see ~5 s of
silence during the reconnect.

### "How do I add ICY metadata (now-playing track title)?"

It is there already: the playout labels every metadata packet
according to **Stream Label** (see §1), shows the **Off Air
Metadata** text while nothing is on air, and passes the titles a
webstream or a DJ's broadcasting software sends through the same
label.  A live source without titles of its own is labelled with the
show on air.

### "Why does the same stream URL play differently on different players?"

Different player software handles buffer-underrun,
reconnect, and metadata differently. Test with VLC (a
reference player) for ground truth. iTunes, Winamp,
browser-based players each have their own quirks.

---

## Where to go next

* [Local Machine](./LOCAL_MACHINE.md) — the
  operator-machine sound-card output (separate from streams).
* [Dashboard](./DASHBOARD.md) — quick stream health visible
  on every page.
* [Webstreams](./WEBSTREAMS.md) — the *inbound* counterpart
  (relaying other people's streams into your shows).
* [`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md)
  — when a stream goes red.
