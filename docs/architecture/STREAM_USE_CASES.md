# RASTATIME — Stream Use Cases

**Version:** 1.0  
**Status:** Authoritative specification (T9.1)  
**Informs:** T9.2 (capability matrix), T10.1–T10.4 (egress implementation),
T11.1–T11.2 (ingress implementation)

---

## 1. Purpose

This document enumerates every streaming use case that RASTATIME must satisfy,
may satisfy, or explicitly defers.  It answers:

* What actors want to send audio out, receive audio in, or monitor a stream.
* What must happen at each step (trigger → flow → postcondition).
* Which mechanism RASTATIME will use, and how that differs from LibreTime's
  Liquidsoap/Icecast model.
* Which use cases are in scope for the current milestone (M9/M10/M11) and
  which are deferred.

Implementors of the egress layer (`streams/egress/`, T10.x) and the ingress
layer (`streams/ingress/`, T11.x) **must** conform to this document.  Where
this document and code disagree, this document is correct until deliberately
revised.

---

## 2. Terminology

| Term | Definition |
|---|---|
| **Egress** | Audio flowing *out* of RASTATIME to a streaming server or file. |
| **Ingress** | Audio flowing *in* to RASTATIME from an external live source. |
| **Mount point** | An Icecast or SHOUTcast endpoint path (e.g. `/main.mp3`). |
| **Source client** | A program that pushes an audio stream *to* Icecast (e.g. RASTATIME, Mixxx, BUTT). |
| **Listener** | An end-user who pulls audio *from* Icecast (via media player or browser). |
| **Show Source** | A per-show live input: the DJ's stream overrides playout for their scheduled slot. |
| **Master Source** | A persistent live input: the DJ's stream overrides all playout regardless of schedule. |
| **libVLC sout** | libVLC's stream-output (`sout`) transcoding and delivery chain. |
| **ICY metadata** | The in-stream metadata protocol used by MP3/SHOUTcast sources to update the now-playing title in Icecast and SHOUTcast. |
| **HLS** | HTTP Live Streaming — Apple's adaptive segment-based streaming format. |

---

## 3. Use Case Catalogue

### 3.1 Summary table

| UC ID | Title | Group | Priority | Milestone | Mechanism |
|---|---|---|---|---|---|
| UC-O1 | MP3 → Icecast | Egress | **P1** | M10 (T10.1) | libVLC sout |
| UC-O2 | OGG Vorbis → Icecast | Egress | **P1** | M10 (T10.1) | libVLC sout |
| UC-O3 | OGG Opus → Icecast | Egress | P2 | M10 (T10.2) | libVLC sout |
| UC-O4 | AAC-LC → Icecast | Egress | P2 | M10 (T10.2) | libVLC sout (if AAC module present) |
| UC-O5 | MP3 / AAC → SHOUTcast | Egress | P2 | M10 (T10.2) | libVLC sout |
| UC-O6 | Multiple simultaneous streams | Egress | P2 | M10 (T10.3) | libVLC multi-sout |
| UC-O7 | Real-time metadata push | Egress | **P1** | M10 (T10.1) | ICY metadata / Icecast HTTP API |
| UC-O8 | Auto-reconnect after disconnect | Egress | **P1** | M10 (T10.1) | Reconnect loop in `StreamConnection` |
| UC-O9 | Archive to local file | Egress | P3 | M10 (T10.4) | libVLC sout file sink |
| UC-O10 | HLS output | Egress | P3 | Post-M11 | libVLC sout HLS, or external packager |
| UC-I1 | Show Source (per-slot DJ override) | Ingress | P2 | M11 (T11.1) | Icecast ingress + QueueManager preempt |
| UC-I2 | Master Source (persistent DJ override) | Ingress | P2 | M11 (T11.2) | Icecast ingress + QueueManager preempt |
| UC-I3 | Web stream as QueueItem | Ingress | **P1** | M11 (T11.1) | libVLC HTTP source (already partially works) |
| UC-I4 | Local audio device (line-in) | Ingress | P3 | T12+ (reserved) | libVLC audio capture (Phase 7) |
| UC-M1 | Stream connection status | Monitoring | **P1** | M10 (T10.1) | Internal state + Icecast HTTP API |
| UC-M2 | Listener count query | Monitoring | P2 | M10 (T10.3) | Icecast HTTP `/admin/stats` API |
| UC-M3 | Listener statistics history | Monitoring | P3 | Post-M11 | Poll + persist to Django API |

**Priority key:**  
P1 = required for M10 baseline; P2 = full-featured M10; P3 = post-M10 enhancement.

---

## 4. Output (Egress) Use Cases

### UC-O1 — Single MP3 Stream to Icecast

**Actor:** Station operator (configures stream); RASTATIME playout engine
(initiates).

**Trigger:** Playout begins (engine transitions from STOPPED to PLAYING) and an
MP3 Icecast stream is configured.

**Main flow:**
1. The `StreamConnection` manager reads the active `IcecastOutput` configuration
   (host, port, mount, password, bitrate).
2. A libVLC `sout` chain is constructed:
   `transcode{acodec=mp3,ab=<bitrate>}:shout{host=…,port=…,mnt=…,pwd=…}`.
3. The libVLC instance activates the sout chain; libVLC connects to Icecast and
   begins pushing the transcoded stream.
4. On every `TrackChangedEvent`, the stream metadata (title, artist) is updated
   via ICY metadata injection (see UC-O7).
5. When playout ends or the stream is explicitly stopped, the sout chain is
   released and the Icecast source connection is dropped.

**Postcondition:** Listeners connected to the Icecast mount point hear the
playout audio; now-playing metadata is correct.

**RASTATIME mechanism:** libVLC `sout` with the `shout` access module.  
**LibreTime mechanism:** Liquidsoap `output.icecast` operator feeding an
Icecast server.

**Notes:**
- The `shout` libVLC access module targets Icecast 2.x.  Compatibility with
  Icecast 2.3+ (which supports Opus) should be verified in T9.2.
- libVLC's MP3 encoding uses the `twolame` or `lame` codec module, which must
  be present in the libVLC Windows build.
- Icecast acts as a relay/delivery server; libVLC is the source client.
  Icecast itself is optional (ADR-003) — a future enhancement could skip
  Icecast and serve listeners directly from libVLC's built-in HTTP server,
  but multi-listener reliability makes Icecast strongly preferred.

---

### UC-O2 — Single OGG Vorbis Stream to Icecast

**Actor / Trigger:** Same as UC-O1.

**Main flow:** Identical to UC-O1 except the sout chain uses
`transcode{acodec=vorb,ab=<bitrate>}`.  OGG Vorbis streams require Icecast
(Shoutcast does not support OGG).

**RASTATIME mechanism:** libVLC sout with OGG Vorbis codec.  
**LibreTime mechanism:** Liquidsoap `output.icecast` with `%vorbis`.

**Notes:**
- OGG Vorbis metadata is transported via Vorbis comment headers (not ICY);
  Icecast handles metadata extraction natively.
- Royalty-free; preferred format for stations that do not require hardware
  player compatibility.

---

### UC-O3 — Single OGG Opus Stream to Icecast

**Actor / Trigger:** Same as UC-O1.

**Main flow:** sout chain uses `transcode{acodec=opus,ab=<bitrate>}`.
Requires Icecast ≥ 2.4.

**RASTATIME mechanism:** libVLC sout with Opus codec.  
**LibreTime mechanism:** Liquidsoap `%opus`.

**Notes:**
- Opus at 64 kbps is suitable for music; 32 kbps for voice.
- Icecast 2.4 is required for Opus; the T9.2 matrix must confirm the libVLC
  Windows build includes `libopus`.

---

### UC-O4 — Single AAC-LC Stream to Icecast

**Actor / Trigger:** Same as UC-O1.

**Main flow:** sout chain uses `transcode{acodec=mp4a,ab=<bitrate>}`.

**RASTATIME mechanism:** libVLC sout with the `mp4a` audio codec (FDK AAC or
FFmpeg AAC, depending on the libVLC build).  
**LibreTime mechanism:** Liquidsoap with `%fdkaac`; AAC support requires a
custom Liquidsoap build (the stock Debian/Ubuntu Liquidsoap lacks AAC — see
LibreTime docs).

**Notes:**
- AAC codec availability depends on the libVLC Windows build (patent-licensed;
  may not be present in all distributions).
- T9.2 must empirically confirm whether the bundled VLC Windows installer
  includes a working AAC encoder module.
- If AAC is unavailable via libVLC sout, a fallback via FFmpeg subprocess
  piped to Icecast's source protocol is acceptable.

---

### UC-O5 — MP3 or AAC Stream to SHOUTcast

**Actor / Trigger:** Same as UC-O1, with a `ShoutcastOutput` configuration.

**Main flow:** sout chain targets a SHOUTcast v2 server using the `shout`
access module with the SHOUTcast protocol variant.  Supported formats: MP3,
AAC.

**RASTATIME mechanism:** libVLC sout `shout` module (SHOUTcast mode).  
**LibreTime mechanism:** Liquidsoap `output.shoutcast`.

**Notes:**
- SHOUTcast does not support OGG Vorbis or Opus.
- SHOUTcast metadata uses ICY protocol (same as MP3/Icecast).
- Differences between SHOUTcast v1 and v2 authentication must be tested in T9.2.

---

### UC-O6 — Multiple Simultaneous Streams

**Actor:** Station operator (configures N stream profiles).

**Trigger:** Playout begins with more than one `StreamOutput` configuration active.

**Main flow:**
1. The `StreamConnection` manager reads all active stream configurations.
2. One libVLC sout chain per stream is constructed; each chain has its own
   codec, bitrate, and server destination.
3. libVLC activates all sout chains simultaneously; audio is transcoded and
   pushed to each server independently.
4. Metadata updates (UC-O7) are sent to each active stream.

**Postcondition:** All configured streams are simultaneously active; listeners
can connect to any configured mount point.

**RASTATIME mechanism:** Multiple libVLC sout chains, or one `duplicate{}`
sout with multiple destinations.  
**LibreTime mechanism:** Liquidsoap `output.icecast` called once per stream;
multiple can coexist.

**Notes:**
- libVLC's `duplicate{}` sout is more efficient than N independent transcode
  chains when the source audio is the same (one decode, N encodes).
- Up to 3 simultaneous streams is the expected typical deployment; more than
  5 is unusual.
- T9.2 must measure CPU overhead of 3 simultaneous MP3+OGG+Opus encodes on a
  typical Windows station PC.

---

### UC-O7 — Real-Time Metadata Push

**Actor:** RASTATIME playout engine (automatic on `TrackChangedEvent`).

**Trigger:** `TrackChangedEvent.current_item` changes (new track starts).

**Main flow:**
1. The `NowPlayingState` subscriber fires the metadata update.
2. For Icecast/SHOUTcast with MP3 stream: an ICY metadata update is sent to
   Icecast's source protocol connection (title formatted as
   `Artist - Title` or just `Title` if artist is blank).
3. For Icecast with OGG/Opus stream: Icecast reads metadata from the Vorbis
   comment headers embedded in the stream by the libVLC sout chain.
4. For Icecast: the `PUT /admin/metadata` HTTP endpoint may be used as an
   alternative or supplement for richer metadata (album, show name).

**Postcondition:** Icecast's `/status-json.xsl` and the ICY title shown in
player software reflect the current track within ≤ 2 seconds of the track change.

**RASTATIME mechanism:**
- ICY title via libVLC `sout` or via explicit HTTP call to Icecast metadata API.
- OGG/Opus: automatic via Vorbis comment injection in sout.

**LibreTime mechanism:** Liquidsoap injects metadata per track via
`annotate:` and its own ICY/Icecast metadata channel.

**Notes:**
- ICY metadata maximum length is 255 bytes (×16 characters); long titles must
  be truncated.
- Unicode title support: libVLC encodes in UTF-8; Icecast ≥ 2.4 handles UTF-8
  correctly for all stream types.  Older Icecast versions may need the
  `<charset>UTF-8</charset>` mount option (see LibreTime stream-configuration
  upstream doc).
- When the engine is IDLE (fallback or silence), metadata should be set to the
  station name or a configured "on-air" string, not an empty value.

---

### UC-O8 — Auto-Reconnect After Connection Loss

**Actor:** RASTATIME `StreamConnection` manager (automatic).

**Trigger:** The sout chain's connection to Icecast drops (network error,
Icecast restart, timeout).

**Main flow:**
1. The `StreamConnection` manager detects the disconnect (libVLC sout error
   event or health-check failure — see UC-M1).
2. After a configurable backoff delay (default: 5 s, increasing exponentially
   to a maximum of 60 s), a new sout chain is constructed and connected.
3. Reconnection attempts continue indefinitely until the connection succeeds
   or the stream is explicitly stopped.
4. On successful reconnect, metadata is pushed immediately for the currently
   playing item.

**Postcondition:** The stream resumes after a transient server or network
failure without operator intervention.

**RASTATIME mechanism:** Custom reconnect loop in `StreamConnection`; libVLC
does not auto-reconnect sout chains natively.  
**LibreTime mechanism:** Liquidsoap's `output.icecast` has a built-in
`fallible=true` / reconnect model.

**Notes:**
- During the reconnect window, listeners on the Icecast mount will experience
  a stream interruption.  This is unavoidable without a secondary standby
  connection.
- Icecast's own `<mount><fallback-mount>` feature can mitigate the listener
  experience: Icecast can serve a fallback mount during source disconnect.
  This is a server-side configuration outside RASTATIME's scope.

---

### UC-O9 — Archive to Local File

**Actor:** Station operator (configures archive recording); RASTATIME
(automatic during playout).

**Trigger:** A local file archive is configured and playout is active.

**Main flow:**
1. A libVLC sout file-sink chain is constructed alongside any active network
   streams: `duplicate{dst=std{access=file,dst=<path>},...}`.
2. Audio is recorded continuously to the configured path; a new file may be
   created per day / per hour / per show according to configuration.
3. The recording stops when playout stops or the archive is unconfigured.

**Postcondition:** A local audio file on the Windows machine contains the
archived playout audio.

**RASTATIME mechanism:** libVLC sout file sink.  
**LibreTime mechanism:** Liquidsoap `output.file`; archive scheduling via the
LibreTime "Record" checkbox on a show.

**Notes:**
- File format is typically MP3 or WAV; MP3 requires the encoder module.
- File rotation (hourly, daily, per-show) is implemented in RASTATIME's
  archive manager, not in libVLC itself.
- Disk space management (delete old files, enforce quota) is a future task.
- This use case is lower priority (P3) because it does not block the core
  streaming milestone.

---

### UC-O10 — HLS Output

**Actor:** Station operator; end-users connecting via web browser.

**Trigger:** An HLS output is configured and playout is active.

**Main flow:**
1. libVLC sout produces segmented `.ts` files and an `.m3u8` playlist in a
   local directory.
2. A lightweight HTTP server (e.g. Waitress serving static files, or a
   dedicated HLS server) serves the segments to clients.
3. Modern web browsers (Safari, Chrome, Firefox with MSE) play the HLS stream
   without a plugin.

**Postcondition:** Listeners can tune in via a browser-native HLS URL; the
stream adapts to network conditions via segment-based delivery.

**RASTATIME mechanism:** libVLC sout HLS module, or external packager (FFmpeg).  
**LibreTime mechanism:** Not natively supported by LibreTime; HLS is the
Icecast successor in the LibreTime architecture diagram but is not yet
implemented upstream.

**Notes:**
- HLS adds significant complexity (segment management, playlist rotation, CDN
  integration).
- Deferred to post-M11; not required for the M10 streaming baseline.
- If libVLC's HLS sout module proves insufficient, an FFmpeg subprocess
  approach is a viable alternative.

---

## 5. Input (Ingress) Use Cases

### UC-I1 — Show Source (Per-Slot DJ Override)

**Actor:** A DJ or remote contributor using software such as Mixxx, BUTT, or
any Icecast-compatible source client.

**Trigger:** A scheduled show with a "live" flag is about to begin; the DJ
connects their stream to the Show Source mount point.

**Main flow:**
1. Icecast listens on the Show Source mount point (e.g. `/show`).
2. The DJ's source client connects to Icecast with the show-specific
   credentials before or at `show.start_at`.
3. The `IngresMonitor` detects the incoming connection (polls Icecast `/admin/
   stats` or listens for Icecast relay events).
4. The `QueueManager` is notified: it calls `start_show([], HARD)` with an
   ingress-type item pointing to the Icecast relay URL, overriding the
   scheduled file items.
5. libVLC plays the Icecast relay stream (libVLC → Icecast pull → DJ audio).
6. At `show.end_at`, the `PlayoutScheduler` fires `end_show()`; the ingress
   item is stopped; fallback or the next show takes over.

**Postcondition:** Listeners hear the DJ's live audio for the show's duration;
scheduling and fallback resume automatically at `end_at`.

**RASTATIME mechanism:** Icecast ingress mount + libVLC HTTP playback of the
relay URL.  Icecast is **required** for this use case (ADR-003 qualifying
scenario).  
**LibreTime mechanism:** Liquidsoap `harbor` source; Liquidsoap listens
directly for the source connection without a separate Icecast instance.

**Notes:**
- The `HarborInput` config model from LibreTime's `rastatime_shared` is the
  reference shape; it is replaced by a new `ShowSourceConfig` in RASTATIME.
- Icecast must be installed and running on the same machine or accessible over
  the network for this use case.
- Auto-connect: if the DJ fails to connect by `start_at`, scheduled file
  playout continues normally until the DJ does connect.

---

### UC-I2 — Master Source (Persistent DJ Override)

**Actor:** A DJ or broadcast engineer using a source client.

**Trigger:** The DJ connects to the Master Source mount point at any time.

**Main flow:**
1. Icecast listens on the Master Source mount point (e.g. `/master`).
2. The DJ connects; the `IngresMonitor` detects the connection.
3. The `QueueManager` immediately preempts whatever is playing (regardless of
   schedule) via `start_show([ingress_item], HARD)`.
4. The DJ's audio plays until the Master Source disconnects.
5. On disconnect, the `IngresMonitor` detects the drop; the `QueueManager`
   falls back to the scheduled show or fallback content.

**Postcondition:** The DJ's audio overrides all scheduled playout for as long
as the Master Source is connected; normal playout resumes on disconnect.

**RASTATIME mechanism:** Same as UC-I1; Master Source has higher authority
than Show Source (mirrors the LibreTime priority model).  
**LibreTime mechanism:** Liquidsoap `harbor` with a master source priority
above all scheduled queues.

**Notes:**
- The priority ordering in QUEUE_BEHAVIOR.md §2 lists Priority 1 (live input)
  as "reserved for T12+"; UC-I2 brings that forward to M11 via the ingress
  model.
- A Master Source disconnect during a show that has its own Show Source should
  fall back to the Show Source, not to the scheduled file items.

---

### UC-I3 — Web Stream as QueueItem

**Actor:** Station scheduler (via `ScheduledShow.items`).

**Trigger:** A `QueueItem` with a `uri` pointing to an HTTP audio stream
(e.g. `http://stream.example.com:8000/stream.ogg`) is loaded into the
playout engine.

**Main flow:**
1. The `QueueItem` is loaded into the `VlcPlayoutEngine` as a normal item.
2. libVLC opens the HTTP URI using its `http` access module; it buffers and
   plays the incoming audio.
3. Track-change events fire as for a local file: `TrackChangedEvent` with the
   `QueueItem` (duration may be unknown — `None`).
4. If the HTTP source disconnects mid-play, libVLC fires an error event;
   the engine transitions to ERROR state and the `QueueManager` handles it
   per the normal error flow.

**Postcondition:** Listeners hear the remote HTTP audio stream as if it were a
local file; the station's output stream (egress) carries this relay audio.

**RASTATIME mechanism:** libVLC HTTP source — this is already partially
functional (noted in QUEUE_BEHAVIOR.md §6.7); no additional code required
beyond testing.  
**LibreTime mechanism:** `WebStreamEvent` in Liquidsoap; a dedicated input
type with reconnect logic.

**Notes:**
- HTTP stream duration is unknown (`item.duration = None`); the queue does not
  auto-advance until the stream ends or errors.
- For scheduled shows, the operator must set `end_at` explicitly; when
  `end_at` is reached, the `PlayoutScheduler` calls `end_show()` regardless
  of whether the stream is still active.
- HTTPS streams (`https://`) are supported natively by libVLC.
- Redirected streams (m3u, pls, xspf playlists) require libVLC to resolve the
  playlist first; this is automatic for VLC-supported playlist formats.

---

### UC-I4 — Local Audio Device (Line-In)

**Actor:** A DJ or presenter connected via a physical audio interface (XLR,
USB audio, sound card line-in).

**Trigger:** A Line-In source entity is activated via the RASTATIME UI or API.

**Main flow:**
1. libVLC opens the local audio capture device using `dshow://` (DirectShow
   on Windows) or `wasapi://` as the input URI.
2. The captured audio is played through the engine queue exactly like a stream.
3. An egress sout chain (UC-O1 through UC-O5) picks up the same audio and
   pushes it to Icecast.

**Postcondition:** The presenter's microphone or mixer output is broadcast
live.

**RASTATIME mechanism:** libVLC DirectShow/WASAPI capture source.  
**LibreTime mechanism:** Liquidsoap `input.alsa` or `input.jack`.

**Notes:**
- **Deferred to T12+ (Phase 7).** This use case requires the Soundcard device
  manager (T12.1) and the Line-In domain layer (T13.x–T15.x) to be built
  first.
- Listed here for completeness and to establish that the ingress layer
  (T11.x) must not assume that all live sources arrive via network.

---

## 6. Monitoring Use Cases

### UC-M1 — Stream Connection Status Reporting

**Actor:** RASTATIME `StreamConnection` manager (automatic); station operator
(reads the status API).

**Trigger:** Stream connection state changes (connected, disconnected, error).

**Main flow:**
1. The `StreamConnection` manager maintains an internal state machine:
   `DISCONNECTED → CONNECTING → CONNECTED → DISCONNECTED`.
2. On each state transition, the manager publishes a `StreamStatusEvent`
   to registered callbacks (e.g. the API layer, the dashboard).
3. The API endpoint `GET /api/v2/stream-status` returns a JSON snapshot of
   all configured streams and their current state.

**Postcondition:** The operator dashboard shows a green/red indicator per
stream; the API is queryable by external monitoring tools.

**RASTATIME mechanism:** Internal state machine in `StreamConnection`; Icecast
HTTP `/status-json.xsl` as a secondary confirmation source.  
**LibreTime mechanism:** Liquidsoap telnet status queries; LibreTime API
exposes stream health via the settings and status pages.

---

### UC-M2 — Listener Count Query

**Actor:** Station operator; analytics dashboard.

**Trigger:** Operator opens the listener stats page, or a background poll fires.

**Main flow:**
1. RASTATIME polls Icecast's `GET /admin/stats.xml` endpoint (requires admin
   credentials) at a configurable interval (default: 60 s).
2. The listener count per mount point is extracted and stored in the Django
   API history tables.
3. The API endpoint `GET /api/v2/listener-stats` returns current and recent
   listener counts.

**Postcondition:** The operator can see how many listeners are tuned in per
stream, in near-real-time.

**RASTATIME mechanism:** HTTP poll of Icecast admin API; stored in existing
`history/` Django app.  
**LibreTime mechanism:** Liquidsoap telnet + Icecast stats API; stored in
LibreTime's listener stats database.

**Notes:**
- Listener count is only available when Icecast is used (UC-O1–O6).
  If RASTATIME is configured to push directly without Icecast (not recommended
  for multi-listener scenarios), listener count is unavailable.
- SHOUTcast provides listener stats via its own API (`/admin.cgi?mode=viewxml`);
  format differs from Icecast.

---

### UC-M3 — Listener Statistics History

**Actor:** Station operator reviewing analytics.

**Trigger:** Operator queries the historical listener stats for a date range.

**Main flow:**
1. The `StatisticsCollector` service polls UC-M2 at regular intervals and
   appends records to the Django history tables.
2. The operator uses the LibreTime-inherited Analytics → Listener Stats view
   (inherited from the Django `history/` app) to view charts.

**Postcondition:** The operator can review listener trends over hours, days,
or weeks.

**RASTATIME mechanism:** Periodic poll + Django history persistence.  
**LibreTime mechanism:** Identical — LibreTime uses the same poll-and-persist
approach.

**Notes:**
- Deferred to post-M11; listener stats require a working stream (M10) before
  meaningful data can be collected.

---

## 7. Implementation Scope per Milestone

| Milestone | Tasks | Use cases addressed |
|---|---|---|
| **M9** (this milestone) | T9.1 (this doc), T9.2 (capability matrix) | All: enumerated and classified; none implemented |
| **M10** (egress) | T10.1–T10.4 | UC-O1, O2, O7, O8 (T10.1); UC-O3, O4, O5 (T10.2); UC-O6, M1, M2 (T10.3); UC-O9 (T10.4) |
| **M11** (ingress) | T11.1–T11.2 | UC-I1, I3 (T11.1); UC-I2 (T11.2) |
| **Post-M11** | Future | UC-O10 (HLS), UC-M3 (history), UC-I4 (line-in, deferred to T12+) |

### M10 baseline (T10.1) — minimum viable streaming

T10.1 must deliver:
* UC-O1 — MP3 stream to Icecast (proves the sout chain works end-to-end)
* UC-O2 — OGG Vorbis stream (proves codec flexibility)
* UC-O7 — Metadata updates (essential for station branding)
* UC-O8 — Auto-reconnect (essential for unattended operation)
* UC-M1 — Connection status (essential for operator awareness)

Everything else in M10 builds on this baseline.

---

## 8. How RASTATIME Diverges from LibreTime

| Concern | LibreTime | RASTATIME |
|---|---|---|
| **Playout engine** | Liquidsoap (DSP language runtime) | libVLC Python API |
| **Encoding** | Liquidsoap built-in operators (`%mp3`, `%vorbis`, etc.) | libVLC `sout` transcode chain |
| **Source protocol** | Liquidsoap `output.icecast` / `output.shoutcast` | libVLC `shout` access module |
| **Live input** | Liquidsoap `harbor` (listens directly for source) | Icecast mount point + libVLC HTTP pull (ingress via Icecast relay) |
| **Metadata** | Liquidsoap `annotate:` per track | ICY protocol injection via sout + Icecast metadata API |
| **Multi-stream** | Multiple Liquidsoap `output.*` operators | libVLC `duplicate{}` sout or multiple sout chains |
| **HLS** | Not implemented upstream | libVLC HLS sout (deferred) |
| **AAC** | Custom Liquidsoap build required | libVLC AAC module (availability TBC in T9.2) |
| **Auto-reconnect** | Liquidsoap built-in with `fallible=true` | Custom reconnect loop in `StreamConnection` |
| **Icecast role** | Primary stream delivery (always used) | Optional auxiliary (ADR-003); required for UC-I1/I2 |
| **SHOUTcast** | `output.shoutcast` operator | libVLC sout `shout` module (SHOUTcast mode) |
| **Stream monitoring** | Liquidsoap telnet status | Internal state machine + Icecast HTTP API |

### Key architectural difference

LibreTime's Liquidsoap acts as both playout engine *and* stream encoder/dispatcher.
A single Liquidsoap process:
1. Reads the schedule from the playout daemon.
2. Plays audio items (from files or live sources).
3. Encodes and pushes each configured output stream.
4. Manages fallback between sources.

RASTATIME separates these concerns:
1. **libVLC** (`playout/`) — plays audio items; is the source of audio data.
2. **`StreamConnection` manager** (`streams/egress/`) — attaches sout chains
   to the libVLC instance; encodes and pushes streams.
3. **`IngressMonitor`** (`streams/ingress/`) — watches Icecast for incoming
   live sources; notifies `QueueManager`.
4. **`QueueManager`** (`playout/queue_manager/`) — arbitrates what plays;
   is the authority for priority preemption.

This separation means RASTATIME can run playout without any stream output
(useful for studio-local-only mode), and stream output without a live DJ
(unattended automation), independently.

---

## 9. Open Questions for T9.2

The following questions must be answered empirically in T9.2 before
implementation work begins:

1. **libVLC `sout` on Windows**: Does the `shout` access module ship with the
   standard VLC Windows installer?  Which bitrates and formats are confirmed
   working?
2. **MP3 encoder**: Is `twolame` or `lame` available in the Windows libVLC build?
   If neither, is `FFmpeg` the fallback encoder for MP3 egress?
3. **AAC encoder**: Is `FDK AAC` or `FFmpeg AAC` available in the Windows libVLC
   build?
4. **Opus in sout**: Can libVLC's sout produce an OGG Opus stream that Icecast 2.4
   accepts as a valid source?
5. **ICY metadata via sout**: Can libVLC inject ICY title metadata into an MP3
   sout stream without breaking the Icecast connection?
6. **Multiple sout chains**: What is the CPU overhead of three simultaneous
   encode-and-push chains on a typical studio PC (≥ i5 / Ryzen 5 equivalent)?
7. **SHOUTcast v2 protocol**: Does the `shout` module correctly handle
   SHOUTcast v2 session handshake vs. SHOUTcast v1?
8. **Auto-reconnect**: Does releasing and re-creating a libVLC sout chain
   cleanly reconnect to Icecast, or does a full libVLC instance restart become
   necessary?

---

## 10. Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-04-25 | Initial use case enumeration (T9.1). |
