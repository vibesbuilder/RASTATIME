
# RASTATIME — Architecture Draft
**Windows 11 LibreTime Fork with VLC/libVLC Main Playout Engine**  
Draft version: 0.27
Date: 2026-09-09

> **Revision history**
> - **0.27 (2026-09-09)** — **Event-driven source switcher** (§23.3 note,
>   §23.27 addendum 2026-09-09 b).  `input.harbor` reports DJ connects
>   and disconnects to PLAYOUT's listener (`on_connect`/`on_disconnect`
>   → `http.post`); PLAYOUT verifies once per event and every 120 s
>   instead of polling telnet every 5 s — the ~150 MB/h idle leak goes
>   with the poll.  An older render without the callbacks is detected
>   (`rastatime.source_events`) and polled as before.
> - **0.26 (2026-09-09)** — **Planned LIQUIDSOAP restart for a 24/7
>   programme** (§23.27, addendum 2026-09-09).  Triggers: window, every
>   N days by process age, soft memory limit in the window, hard limit
>   any time; execution in a quiet moment or else between two file
>   tracks.  A standby Liquidsoap (`standby.liq`, rendered by PLAYOUT)
>   feeds Icecast fallback mounts so listeners are moved, not
>   disconnected, while the main instance restarts.
> - **0.25 (2026-09-08)** — **A fresh `input.http` per webstream slot**
>   (§23.27, addendum 2026-09-08).  A reused `input.http` reconnects
>   through one Duppy async task whose pipe wake-up is unreliable on
>   the Windows build under normal load (starts hung 20–110 s in four
>   of five production-like replica runs; Phase D 2026-09-08 lost a
>   slot).  The bus arm is now a `source.dynamic`; every
>   `webstream.start` opens a new input with its own bridge, the
>   watchdog recovers the same way, and the stale-bridge remnant at
>   slot start is gone with it.  PLAYOUT's telnet contract is unchanged.
> - **0.24 (2026-09-07)** — **Webstream watchdog moves into Liquidsoap**
>   (§23.27, addendum 2026-09-07 evening).  The 2026-09-06 scheduler
>   poll cost ~87 KB of leaked memory per telnet command on the Windows
>   build; a frame counter on `bus.on_frame` inside the engine does the
>   same check for free (measured flat over 15 min).  PLAYOUT keeps the
>   poll as an opt-in fallback and as a stop-gap while an older render
>   is still loaded.
> - **0.23 (2026-09-07)** — **Nightly-restart hardening** (§23.27,
>   addendum 2026-09-07).  Both nightly restarts so far crash-looped
>   LIQUIDSOAP until the morning: PortAudio's device list is built once
>   per process, the display's HD-Audio endpoint was gone at 04:01, and
>   the stale index opened the wrong device.  Now: re-enumeration before
>   every resolution, automatic restarts only for a by-name render,
>   `nssm restart` verified by observation plus a stays-up check, and
>   the `liquidsoap_unavailable` preflight warning.
> - **0.22 (2026-09-05)** — **Liquidsoap process hygiene on Windows**
>   (§23.27).  The savonet Windows build leaks ~5 KB per `Unix.select`;
>   the scheduled queue becomes a *synchronous* `request.queue` copy
>   (no Duppy retry poller), the Main Output is rendered by exact
>   PortAudio **name** instead of index (indices drift after boot),
>   PLAYOUT restarts LIQUIDSOAP itself inside the boot window and once
>   a night in a quiet window, and the preflight watches the process
>   memory and the Main Output audio session.  `sync="auto"` on the
>   monitor clock ends the "Latency is too high" spam.
> - **0.21 (2026-09-04)** — **Seamless input switching** (§23.26).  The
>   Liquidsoap bus switch gains per-source **gates** (`webstream_live`,
>   `linein_live`, interactive bools ANDed into the predicates) and
>   **transition functions**: a crossfade of the house duration, or
>   "ducking" when that duration is 0.  The house duration is now the
>   Settings → General "Default Crossfade Duration" (cc_pref), read at
>   render time; the env var is a fallback.  The playout **pre-warms**
>   line-ins and webstreams 10 s before their slot behind a closed gate
>   and opens the gate at the slot start; at the slot end it closes the
>   gate and stops the source only after the transition has drained,
>   so a line-in's buffered tail (~2 s of the presenter's last words)
>   is heard under the successor instead of being cut.  Same-day
>   groundwork: every scheduled line-in on the MME feeder (dshow only
>   as a legacy fallback), `format="mp3"` on the capture source (FFmpeg
>   autodetection cost ~5 s of latency), successor-side release of
>   line-in/webstream predecessors, identity-based catch-up.
> - **0.20 (2026-09-03)** — The **Main Output** setting now actually
>   drives the Liquidsoap local monitor.  Until now the value was
>   stored and pushed to playout but discarded by a no-op
>   (`LiquidsoapPlayoutEngine.set_audio_device`), and
>   `output.portaudio` rendered without a device argument, so the
>   monitor always followed the Windows default endpoint.  New module
>   `libretime_playout/engine/portaudio_output.py` maps the Windows
>   endpoint to a PortAudio index which is rendered as `device_id=`
>   into rastatime.liq at playout start.  The mapping **probes** host
>   APIs rather than assuming one, using PortAudio's BLOCKING api (what
>   Liquidsoap uses; a callback-mode probe once approved WDM-KS and
>   crashed Liquidsoap at device-open).  Measured: a USB headset opens
>   via MME; the Tascam US-16x08 opens via WASAPI — but only once its
>   Windows shared-mode format matches Liquidsoap's 44.1 kHz (at the
>   factory 48 kHz it refused every host API and looked dead).  Order
>   is WASAPI → MME → DirectSound → WDM-KS, with an OS-default
>   fallback and a targeted "set the endpoint format to 44100 Hz" hint
>   when a candidate rejects the sample rate.  Because the device is
>   baked in at render time, applying a change needs PLAYOUT then
>   LIQUIDSOAP restarted — exposed as a deliberate, confirmed
>   "Apply now" button (`preference/restart-audio-chain`) rather than
>   an implicit restart on Save, and kept in the authenticated legacy
>   PHP layer because the Django API binds 0.0.0.0 without auth.
>   Side finding: one interface can serve output (WASAPI shared) and
>   line-in capture (MME) simultaneously, with other applications
>   coexisting (refuting the earlier "full duplex only via ASIO"
>   note); output-to-input coupling measures ~45-65 dB down — no
>   feedback risk.
> - **0.19 (2026-08-31)** — Line-In channel selection on multichannel
>   interfaces (Sections 13.3-13.5 follow-up).  A line-in now selects
>   WHICH input channels of its device it captures (`channel_mapping`,
>   a stereo pair or one mono channel — the field existed through
>   DB/domain/API/UI but was never applied by any capture layer), so a
>   16-input interface (Tascam US-16x08) can serve one studio per
>   pair.  Plain `(0, 1)` keeps the proven paths untouched: direct
>   `input.ffmpeg(format="dshow")` in Liquidsoap mode, dshow
>   FfmpegLineinCapture on the legacy path.  Any other mapping routes
>   through a new `linein_feeder` subprocess (sounddevice/**MME** —
>   measured: WASAPI shared is capped at the endpoint's 2-ch mix
>   format, WASAPI exclusive is rejected, DirectSound delivers
>   silence, WDM-KS lacks blocking reads, while MME delivers all 16
>   REAL channels, verified by per-lane bit-comparison) piping s16le
>   stereo into FfmpegLineinCapture's ffmpeg (`-f s16le -i pipe:0`,
>   shutdown via feeder-EOF instead of 'q'), which pushes
>   /linein-capture as before; in Liquidsoap mode a second fixed-URL
>   `input.http(id="linein_http")` source (the original Phase-F
>   pattern, kept alongside Phase-F-2) consumes that mount, folded
>   with the dshow source into the single `linein` switch arm via
>   `fallback`.  Same-device transitions now also compare the
>   mapping (two studios on one card must bounce);
>   the line-in resume path re-arms the Liquidsoap sources instead of
>   pushing a capture URL through the request queue (pre-F-2 leftover).
>   UI: the free-text "0,1" field became a picker fed by the device's
>   channel count ("Stereo 1/2" … "Mono N"); domain now rejects
>   mappings longer than 2.  New runtime dependency `sounddevice`
>   (bundled PortAudio, pip-only).  Minor-bump: additive sources +
>   subprocess, no schema change (column already existed).
> - **0.18 (2026-06-16)** — Traffic Alerts (Section 23.25).  Short-notice
>   traffic MP3s air within a ~10-min SLA with no change to the Python
>   playout path.  An operator designates ONE smart block as the source
>   (Settings, `cc_pref` `traffic_alert_block_id`); a show carrying that
>   block in its autoload dramaturgy is filled INCREMENTALLY like a request
>   show (reusing the Mid-Show R1 engine), so a traffic slot picks up alerts
>   imported WHILE the show is already on air — no insert-after-current and
>   no following-item shift.  Each slot draws the oldest not-yet-scheduled
>   alert (FIFO by `utime`, no random fallback, no double-airing).  The SLA
>   is held by dramaturgy density (operator decision B); an active
>   deadline-skip is deferred to the backlog with a precondition.
> - **0.17 (2026-06-16)** — Mid-Show Song Requests / incremental fill
>   (Section 23.23 update).  A request show now resolves its dramaturgy
>   INCREMENTALLY across the 2-min polls, only up to
>   `RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (default 300 s) ahead of the
>   play head, instead of one-pass at T-lead.  A "use requests" block
>   later in the dramaturgy is resolved only when its slot is about to
>   play, so it draws requests submitted WHILE the show is on air — they
>   air in the same show.  A persistent per-instance position cursor
>   `cc_show_instances.autoplaylist_cursor` (legacy migration 0057, raw
>   SQL) carries fill progress across polls; once the dramaturgy is done
>   the trailing time-remaining block is filled completely, bounding the
>   dead-air window to the short dramaturgy.  No playout change (pypo
>   picks the mid-show append up at start-time).  Minor-bump for the new
>   per-show fill behaviour + the additive schema column.
> - **0.16 (2026-06-15)** — Delayed Show Start (Section 23.24).  An
>   opt-in `cc_show.allow_delayed_start` boolean (legacy migration
>   0056, no Propel accessor — raw-SQL read/write like the
>   song-request columns) lets a show begin later than its slot when
>   the preceding show overran, instead of trimming that show.  A
>   background `ShowShiftTask` (TaskManager, 2 min poll, 15 min lead)
>   extends the overbooking show's end to its content end (so it airs
>   in full with NO change to the Python playout path), slides the next
>   opted-in show's START to that point while keeping its END fixed
>   (items move with it, last track clamped = accepted cut-off),
>   cascades across consecutive opted-in shows — clearing
>   completely-overrun ones to "skipped" empty slots — and stops at the
>   first un-ticked anchor, which always begins on time.  Forward-only
>   by operator decision (no original-slot column / migration);
>   idempotent via whole-second deltas + a `modified_instance` trigger
>   filter.  Minor-bump for the new per-show scheduling behaviour + the
>   additive schema column; no new public/external surface, otherwise
>   additive.
> - **0.15 (2026-06-08)** — Song Requests (Section 23.23).  Listeners
>   request tracks from a public embed widget; the tracks air
>   automatically inside a "request show" — any autoloading-playlist
>   show whose playlist contains a "Use requests" smart block (an
>   IMPLICIT marker, no per-show flag, avoiding ~47 Propel touchpoints
>   a `cc_show` column would have cost).  New Django-managed table
>   `rastatime_song_request` plus a `cc_files` aggregate cache
>   (`requested` / `requested_at` / `request_count` / `requestable`,
>   legacy migration 0055).  Public intake `/api/v2/song-requests`
>   (search + submit, no auth, rate-limited + de-duped, salted-IP
>   hash only).  The in-show fill walks the autoload playlist POSITION
>   BY POSITION (Option C-onepass) so several "Use requests" blocks
>   each draw a *different* request, with a random catalogue fallback
>   for empty slots and a trailing time-remaining block for the rest;
>   `RequestShowFillTask` (2 min poll, 8 min lead).  Lifecycle tasks
>   `RequestPlayedTask` (schedule-based, no playout hook) +
>   `RequestExpiryTask` (8 h TTL).  Minor-bump for the new public
>   surface (widget + 2 API endpoints + new table); the rest is
>   additive (one smart-block criterion, scheduler reuse, no schema
>   change beyond the additive cache columns + new table).
> - **0.14 (2026-05-22)** — Public Now-Playing Embed Widgets
>   (Section 23.22).  Two new public iframe widgets
>   (`/embed/now-playing-show`, `/embed/now-playing-track`)
>   for external station homepages.  Configurable HTTP
>   cache TTL (10–3600 s, default 60).  No auth required
>   — payload is intentionally limited to what a listener
>   would see in the player anyway.  Vanilla-JS in-iframe
>   client with per-second countdown + early re-poll on
>   item end-time crossing.
> - **0.13 (2026-05-21)** — Smart Block "Exclude tracks played
>   lately" filter (Section 23.21).  Third pool-restriction
>   toggle in the Advanced section of the Smart Block dialog;
>   excludes tracks whose `cc_files.lptime` is newer than the
>   operator-set hours window (1..8760 h).  Never-played
>   tracks are included.  No schema change — two new
>   `cc_block_criteria` rows.
> - **0.12 (2026-05-21)** — Auto DJ feature (Section 23.20).
>   New `Application_Service_AutoDjService` with two passes that
>   bookend the existing per-show autoplaylist build loop in
>   `AutoPlaylistManager`: a pre-pass auto-creates a single
>   non-repeating show in the next 1 h calendar gap (≥ 60 s,
>   ≤ 12 h, with `has_autoplaylist = true` so the same poll
>   cycle fills it), and an opt-in fill-pass appends the
>   Auto-DJ playlist to upcoming instances whose unscheduled
>   tail is > 5 s.  Settings page under
>   Settings → Auto DJ persists five `cc_pref` keys; logo
>   upload re-uses the show-image MIME-validation pattern.
>   Programmatic show creation uses the existing
>   `ShowService::addUpdateShow()` under a `Zend_Auth` admin-
>   context swap because that service hard-rejects non-Admin/PM
>   callers.  Minor-bump because of new public surface
>   (`AutoDjService` + 5 `Preference` getters/setters +
>   2 new controller actions); otherwise additive only.  No
>   schema change.
> - **0.11.1 (2026-05-20)** — Autoloading Playlist outro-reserve
>   fix (Section 23.19).  Adds a new scheduler-side
>   `setReservedSeconds()` hook and an optional `$reservedSecs`
>   third parameter to `ShowInstance::addPlaylistToShow()` so the
>   auto-build path can pre-reserve the outro playlist's length
>   *before* expanding any time-remaining smart blocks in the
>   autoplaylist.  Existing callers are unaffected (default
>   reserve = 0 = upstream behaviour).  Pure backend; no UI
>   change, no schema change, no API change.  Patch-bump.
> - **0.11 (2026-05-19)** — Line-In entries in Playlists
>   (Section 23.18, migration 0054).  Adds
>   `cc_playlistcontents.linein_id INTEGER` and a new `type = 3`
>   discriminator so the Library's Line-In rows can be dropped into
>   a Playlist alongside Tracks / Webstreams / Smart Blocks.  When
>   such a Playlist is later scheduled into a Show, the Scheduler's
>   `type === 'playlist'` branch maps playlist-type 3 → schedule-
>   type 2, producing the same `cc_schedule` row a direct
>   Show-Line-In would have produced (Section 23.A linein-in-show
>   flow, migration 0047).  Minor-bump because of the new table
>   column; otherwise additive only.
> - **0.10.2 (2026-05-19)** — Webstream "Default Length" field now
>   accepts an optional trailing seconds component (`01h 05m 05s`)
>   to match the Line-Input dialog's granularity (Section 23.17).
>   Backwards-compatible — the pre-existing `01h 05m` form still
>   validates.  Single-file patch (`Application_Model_Webstream`);
>   no schema change (the DB column is already a Postgres `interval`),
>   no API change.  A larger refactor unifying the three independent
>   duration parsers (Webstream, Line-In, Smart Block) into a shared
>   helper was considered and deferred — recorded as future work.
>   Patch-bump.
> - **0.10.1 (2026-05-19)** — Show-Templates follow-up fixes
>   (Section 23.16): the Apply path is now click-trigger-free
>   (jQuery 1.8.3's default-action simulation on checkbox click was
>   inverting the Repeats / Linked state on every Apply), and a
>   single `syncDependentVisibility(form)` pass at the end of
>   `applyShowTemplate()` recomputes every collapsible section from
>   the post-write checkbox state.  Apply + Save-as-Template buttons
>   now explicitly `preventDefault + stopPropagation` so they cannot
>   submit the surrounding `<form id="add-show-form">` and block the
>   next Add-this-Show click.  Template UI rendered in New Show and
>   Edit Show; deliberately suppressed in Edit Instance (re-stamping
>   one occurrence of a repeating show would either silently
>   propagate to siblings or have no effect — both confusing).
>   Patch-bump (no schema changes, no new endpoints).
> - **0.10 (2026-05-19)** — Show-Templates feature (Section 23.16).
>   New table `cc_show_template` (migration 0053) stores reusable
>   show configurations as JSON snapshots; the Calendar's New-Show
>   dialog gains "Load Template" / "Save as Template" controls, and
>   Settings → "Show Templates" lists / renames / deletes existing
>   templates.  One-way stamp model (template-edit does not propagate
>   to existing shows), station-wide scope, hosts stored as login
>   strings (graceful degradation when a user is removed), live-
>   stream passwords excluded from the snapshot.  Minor-bump
>   because of the new table; otherwise additive only.
> - **0.9.2 (2026-05-18)** — Documented a future-work item
>   (Section 23.15) capturing the operator's 2026-05-18 evaluation of
>   exposing RASTATIME to the public Internet over HTTPS: three
>   tunneling/proxy options (direct Apache HTTPS + port-forwarding;
>   Cloudflare Tunnel; external VPS with Caddy), the RASTATIME-side
>   changes that every option entails (public_url, Mixed-Content for
>   Icecast streams, login hardening, cookie/session domain), and an
>   estimated setup-time + annual cost for each.  Decision: deferred
>   — operator wants to keep RASTATIME LAN-only for now.  Pure docs
>   change; no code touched.
> - **0.9.1 (2026-05-17)** — Documented a future-work item (Section
>   23.14): every source switch in the current architecture restarts
>   all three FFmpeg streamers from scratch, leaving the
>   `/rastatime` Icecast mountpoint sourceless for ~2-4 s.  Listeners
>   are forced to reconnect.  Bugfix-only otherwise (recorder
>   reconnect_at_eof / reconnect_on_network_error for surviving the
>   gap; recorder post-roll for full-length files; UTC→local-time
>   filename; faster dashboard polling).
> - **0.9 (2026-05-17)** — Record-per-Show feature: shows flagged
>   `cc_show.record = true` produce a single MP3 of the on-air output
>   to `<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3`.
>   Implementation taps the first configured Icecast output mountpoint
>   with FFmpeg `-c copy` (1–2 % CPU on i3-1315U, no re-encode), so
>   recording quality matches what listeners actually hear AND source
>   switches (file track → web stream → line-in → master) are picked
>   up automatically without scheduler-side coordination.  Two new
>   event types (`SHOW_RECORD_START` / `SHOW_RECORD_END`) keep the
>   recorder lifecycle independent from the per-source event chain.
>   See **Section 23.13**.
> - **0.8 (2026-05-16)** — Local Import Folder feature (drop-folder
>   semantics): operator configures a single absolute path under
>   Settings -> Local Machine (renamed from "Soundcard"); a 5-minute
>   TaskManager scan plus a manual "Scan Now" button walk the folder
>   and hand every audio file to the standard
>   `CcFiles::createAndImport` pipeline (organize -> analyzer ->
>   cc_files); source files are deleted after each attempt,
>   successful or failed.  Reuses existing infrastructure end-to-end
>   (no new analyzer, no new storage, no schema change).  See
>   **Section 23.12**.
> - **0.7 (2026-05-16)** — Track Expiry + Podcast Auto-Expiry feature,
>   plus a shared per-track pruner.  Operators can attach an expiry
>   date to any file (via ID3 TXXX:Expiry tag, manual edit, or
>   per-podcast auto-expiry), and an hourly TaskManager job marks
>   expired tracks `cc_files.disabled = true`.  Disabled tracks stay
>   visible in the Library and in already-built Smartblocks (so
>   scheduled shows keep playing them) but are excluded from NEW
>   Smartblock evaluations.  Per-podcast auto-expiry takes precedence
>   over ID3 tags (subscribers own retention, not publishers).  See
>   **Section 23.11**.
> - **0.6 (2026-05-16)** — Per-webstream input-gain feature, plus a
>   generalisation of the playout engine's gain parameter.  New column
>   `cc_webstream.input_gain_db` (default 0, range -20..+20) is applied
>   by the FFmpeg streamer and mpv local monitor as a `-af volume=<dB>dB`
>   filter for the lifetime of the webstream event.  The existing
>   `replay_gain_db` parameter on `PlayoutEngine.play()` /
>   `FfmpegStreamer.start()` / `PlayoutScheduler._start_streamers()`
>   was renamed to `gain_db`: same plumbing, but the value's source
>   now depends on event type (file = ReplayGain sum, webstream =
>   `input_gain_db`, live sources = None).  See **Section 23.10**.
> - **0.5 (2026-05-15)** — Settings → General audit: removed the phantom
>   "Feature Previews" radio (a `cc_pref` key with no consumer); reduced
>   the language dropdown from 22 to 4 maintained locales (`en_US`,
>   `de_DE`, `fr_FR`, `es_ES`); added a Windows-native `.po → .mo` build
>   pipeline (`infra/scripts/maintenance/build-locales.ps1` driven by
>   mlocati's standalone gettext binary) so translations actually take
>   effect — upstream LibreTime never shipped compiled `.mo` files on
>   this branch, leaving every locale silently English at runtime.
>   Activating the pipeline immediately uncovered three latent upstream
>   bugs (PreferenceController wrote only one of three locale surfaces;
>   `configureLocalization()` use-after-null silently emptied LANGUAGE;
>   `navigation.php` translated at Bootstrap time before
>   `configureLocalization()` ran) — all three fixed in the same
>   release.  See **Section 23.9**.
> - **0.4 (2026-05-15)** — ReplayGain wired end-to-end: the precomputed
>   per-track dB offset (``cc_files.replay_gain`` + global modifier)
>   is now actually applied by the mpv local-monitor and by every
>   FFmpeg streamer.  Previously the value was summed into
>   ``FileEvent.replay_gain`` by the scheduler but neither engine
>   consumed it; the UI looked functional but produced no audible
>   effect.  See **Section 23.8**.
> - **0.3 (2026-05-14)** — Phase B.4 follow-up: replaced the
>   Liquidsoap-dependent file-import playability check with an
>   FFmpeg-based decode-verify (closes the long-running silent gap
>   where RASTATIME imported files without playability validation);
>   removed the phantom "Auto Switch On / Off" UI from Live
>   Broadcasting preferences (their only consumer path was the now-
>   defunct Liquidsoap/Pypo dispatcher).  See **Sections 23.6 and 23.7**.
> - **0.2 (2026-05-14)** — Phase B.4 stabilisation: per-DJ source auth via
>   Icecast 2.4 `stream_auth`, direct-to-:8770 source-event wiring, internal
>   reconciliation watchdog against Icecast's actual mount list, live
>   on-air state read endpoint, and a friendly-name fallback layer for
>   Windows USB endpoint-GUID instability.  See **Section 23 — Phase B.4
>   Stabilisation Decisions** for the architectural rationale.
> - **0.1 (2026-04-23)** — initial draft.

---

## 1. Scope and Design Intent

RASTATIME is planned as a **functional fork of LibreTime**, not as a literal technical port of the current Linux deployment. The main goal is to preserve the **user-visible behavior and core radio automation feature set of LibreTime** while replacing Linux-bound runtime layers with components that run reliably on **Windows 11**.

This document is written in **English** on purpose:

- English is the canonical language for backend commands, identifiers, config keys, enums, API routes, logs, and internal architecture documentation.
- The frontend should be **English-first** as well.
- **German** is the only additional frontend language required in phase 1.

The target platform is a **Windows 11 studio machine**. RASTATIME should automatically start after reboot by running its required processes as Windows services via **NSSM** in the first implementation phase.

### 1.1 Functional Baseline

RASTATIME should copy the existing functional scope of LibreTime as far as feasible, including:

- schedule/calendar management
- show management
- playout and fallback behavior
- media library and playlists
- webstreams
- podcasts / ingestion
- history / logging / reports
- stream configuration
- user-visible operational workflows already known from LibreTime

### 1.2 Explicit Additional Features Beyond LibreTime

In addition to LibreTime compatibility, RASTATIME requires the following new Windows-focused capabilities:

1. **Line-In Sources**
   - Multiple local stereo line inputs from the Windows soundcard / audio interface
   - Dedicated **Line-In** menu entry
   - Add/edit dialog structurally similar to **Webstream**
   - Device/channel selection instead of URL entry

2. **Stereo Line-Out / Soundcard Routing**
   - Local playout must be routable to stereo outputs on the local soundcard
   - Under **Settings**, after **Streams**, add a new submenu:
     - **Settings**
       - Streams
       - **Soundcard**
   - The **Soundcard** submenu manages local input/output device selection

3. **Windows 11 Runtime**
   - No Linux-only service assumptions
   - Automatic service startup after reboot via **NSSM**
   - Windows-native install, update, and recovery workflow

### 1.3 Playout and Streaming Rule

RASTATIME must use **VLC / libVLC as the main playout engine**.

If **libVLC alone is not sufficient** for all required stream-ingress or stream-egress scenarios, **Icecast may be used as an auxiliary streaming layer** for:

- outgoing streams
- incoming network streams
- relay / mount based compatibility cases

However, even in that case:

> **libVLC remains the authoritative main playout engine.**

---

## 2. Source Basis and Design Inputs

This draft combines three kinds of source material:

### 2.1 User-Provided Internal Reference Documents

The previous STUDIO architecture documents are used here primarily as **style and structure references** for the desired output format and implementation breakdown:

- `STUDIO_ARCHITECTURE v2.1`
- `STUDIO_ARCHITECTURE v3.0`

These documents are especially useful for:
- chapter structure
- implementation sequencing
- configuration philosophy
- device settings concepts
- i18n conventions
- stepwise development planning

### 2.2 Primary External Product Sources

Primary product understanding should prefer the following sources in this order:

1. **LibreTime official docs**
2. **LibreTime official GitHub repository**
3. **LibreTime community forum**

Secondary context sources:

4. **AirTime documentation and forum archives**
5. existing AirTime/LibreTime widget discussions for calendar and now-playing behavior

### 2.3 Working Assumption

Where LibreTime and AirTime differ, **LibreTime is authoritative**.

AirTime material may be used only when:
- LibreTime documentation is incomplete,
- AirTime provides a more detailed explanation of inherited behavior,
- legacy widgets or feature semantics need historical clarification.

---

## 3. Feasibility Matrix: Porting the LibreTime / AirTime Stack to Windows 11

LibreTime today is operationally Linux-centric and assumes Linux paths, Linux service lifecycle, and Liquidsoap-centered audio/runtime structure. Therefore, RASTATIME should not be treated as a trivial 1:1 port.

The correct framing is:

- **Domain and feature fork:** yes
- **Runtime and deployment rewrite:** partially yes, and required

### 3.1 Component Feasibility Matrix

| Component | Current Role in LibreTime / AirTime | Windows 11 Feasibility | Target Strategy in RASTATIME | Decision |
|---|---|---:|---|---|
| **PostgreSQL** | Primary relational database | High | Keep | **Keep** |
| **RabbitMQ** | Broker / async infrastructure | High | Keep if still useful in the selected worker architecture | **Keep if beneficial** |
| **Django / Python app layer** | API, models, business logic, admin behavior | High | Keep and refactor where Linux assumptions exist | **Keep + Refactor** |
| **Legacy PHP layer** | Historical UI / migration / legacy features | Medium | Evaluate feature-by-feature; preserve only if still needed | **Selective keep / reduce** |
| **Liquidsoap** | Core playout, mixing, stream dispatch, inputs/outputs | Medium as software, but not aligned with project goal | Replace with libVLC-centered playout design | **Replace** |
| **libVLC / VLC** | New main playout engine | High | Introduce as primary playout core | **Adopt** |
| **Icecast** | Streaming server for public outputs and related workflows | High | Keep as optional auxiliary stream layer for ingress/egress | **Optional supporting component** |
| **Gunicorn** | UNIX-oriented app server | Low | Replace with Windows-suitable serving approach | **Replace** |
| **Celery** | Background workers / async task execution | Low for supported Windows usage | Replace with Windows-native background runner or alternative task layer | **Replace** |
| **nginx** | Reverse proxy / serving | Medium, but weak fit on Windows | Replace with a more Windows-appropriate serving model or simplify architecture | **Replace** |
| **Linux installer** | OS-level setup automation | Low | Replace completely with Windows installer / scripted bootstrap | **Replace** |
| **systemd / systemctl** | Service lifecycle and orchestration | Low | Replace completely with NSSM + Windows services | **Replace** |
| **Remote live inputs** | Network-based live contribution inputs | High at feature level | Re-implement via libVLC and/or Icecast-supporting stream ingress | **Keep functionally** |
| **Local soundcard output** | Hardware audio output | Partial in current LibreTime model | Expand into explicit Windows Soundcard module | **Replace / Extend** |
| **Multiple local line-ins** | Local hardware contribution inputs | Not present as first-class feature | New subsystem | **New** |

### 3.2 General Feasibility Conclusion

A Windows 11 fork is **feasible**, but not as a “compile and run” port.

The following areas are technically realistic to keep:

- core domain logic
- schedule/calendar semantics
- user workflows
- PostgreSQL
- much of the Python/Django layer
- optionally RabbitMQ
- optionally Icecast

The following areas must be re-architected:

- playout core
- audio I/O abstraction
- worker execution model
- Windows service lifecycle
- installer/bootstrap process
- soundcard input/output handling

Therefore the project should be positioned as:

> **A Windows-first functional fork of LibreTime with a new runtime substrate.**

---

## 4. Target Architecture and Replacement Strategy

### 4.1 Objective

RASTATIME should preserve LibreTime’s scheduling and operational behavior while replacing Linux-bound runtime layers with Windows-native or Windows-tolerant components.

The core design rule is:

> **Keep LibreTime behavior where possible. Replace Linux-bound execution layers where necessary. Extend only where Windows audio workflows require it.**

### 4.2 Architectural Principles

#### 4.2.1 Functional Fork, not Literal Port

RASTATIME is a **functional LibreTime fork**.

Target:
- preserve product behavior,
- preserve operator mental model,
- preserve workflows where sensible,

but do **not** preserve Linux implementation details merely for ideological parity.

#### 4.2.2 libVLC as Main Playout Engine

All primary playout actions must be controlled by **VLC / libVLC**:

- scheduled playout start
- scheduled playout stop
- queue control
- fallback/default playout
- current track state
- now-playing metadata
- local soundcard output routing
- playout event callbacks

If another component is introduced for streaming, it must not replace libVLC as the primary playout engine.

#### 4.2.3 Icecast as Optional Auxiliary Stream Layer

If libVLC does not provide sufficient reliability or flexibility for all stream ingress/egress scenarios, RASTATIME may use **Icecast** as an auxiliary component for:

- outgoing public streams
- outgoing relay/encoder mounts
- incoming remote live stream connections
- interoperability with legacy stream workflows

Icecast should be considered **secondary** to the main playout architecture.

#### 4.2.4 English-First System Language

Canonical language rules:

- backend code and commands: **English**
- config keys: **English**
- enum values: **English**
- API routes: **English**
- logs and architecture docs: **English**
- frontend default: **English**
- additional frontend language in phase 1: **German**

#### 4.2.5 Windows-First Runtime

The operating model assumes:

- Windows 11
- local studio deployment
- service start after reboot
- low-friction recovery after crashes
- no dependence on `systemctl`, Linux package managers, or Linux path conventions

### 4.3 Target Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Windows 11 Studio PC                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    RASTATIME Core Platform                     │  │
│  │                                                                │  │
│  │  ┌────────────────────┐    ┌───────────────────────────────┐   │  │
│  │  │ Web UI             │    │ API / Scheduling / Domain     │   │  │
│  │  │ EN default, DE     │◄──►│ Logic                         │   │  │
│  │  └────────────────────┘    └───────────────────────────────┘   │  │
│  │                                      │                         │  │
│  │                                      ▼                         │  │
│  │                        ┌───────────────────────────────┐       │  │
│  │                        │ Background Runner / Jobs      │       │  │
│  │                        │ imports, generation, tasks    │       │  │
│  │                        └───────────────────────────────┘       │  │
│  │                                      │                         │  │
│  │            ┌────────────────┐        │        ┌─────────────┐ │  │
│  │            │ PostgreSQL     │◄───────┼───────►│ RabbitMQ    │ │  │
│  │            │ persistent     │                 │ optional    │ │  │
│  │            │ application DB │                 │ broker      │ │  │
│  │            └────────────────┘                 └─────────────┘ │  │
│  │                                      │                         │  │
│  │                                      ▼                         │  │
│  │                    ┌──────────────────────────────────────┐     │  │
│  │                    │ Main Playout Core                   │     │  │
│  │                    │ VLC / libVLC                        │     │  │
│  │                    │ - queue                             │     │  │
│  │                    │ - scheduled playback                │     │  │
│  │                    │ - fallback/default playout          │     │  │
│  │                    │ - track change events               │     │  │
│  │                    └──────────────────────────────────────┘     │  │
│  │                           │                    │                │  │
│  │                           ▼                    ▼                │  │
│  │             ┌──────────────────────┐   ┌────────────────────┐  │  │
│  │             │ Soundcard I/O Layer  │   │ Optional Stream    │  │  │
│  │             │ - line-out           │   │ Gateway            │  │  │
│  │             │ - line-in sources    │   │ Icecast            │  │  │
│  │             │ - device mapping     │   │ - outgoing mounts  │  │  │
│  │             └──────────────────────┘   │ - incoming mounts  │  │  │
│  │                                        └────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│      Automatic startup after reboot via NSSM / Windows services      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.4 Replacement Strategy by Layer

| Current Layer | RASTATIME Target | Strategy | Decision |
|---|---|---|---|
| Schedule/calendar domain | Preserve behavior | Reuse conceptually | **Keep** |
| Playout engine (Liquidsoap) | libVLC playout runtime | Full replacement | **Replace** |
| Remote stream inputs | libVLC and/or Icecast ingress layer | Re-implement | **Replace implementation, keep function** |
| Stream outputs | libVLC where sufficient, Icecast where needed | Hybrid strategy | **Adapt** |
| Hardware audio output | Windows Soundcard module | Replace and extend | **Replace / Extend** |
| Local audio inputs | New Line-In subsystem | New subsystem | **New** |
| Async workers | Windows-compatible background runner | Replace | **Replace** |
| Linux service management | NSSM-managed Windows services | Replace | **Replace** |
| Web/API layer | Django/Python application layer | Refactor | **Keep + Refactor** |
| DB layer | PostgreSQL | Preserve | **Keep** |

### 4.5 Stream Handling Strategy

#### 4.5.1 Local Playout

Local on-air playout is always driven by **libVLC**.

#### 4.5.2 Outgoing Streams

Use the following priority:

1. **Preferred**: libVLC-driven output when stable and operationally sufficient
2. **Fallback / compatibility**: Icecast when:
   - mount-based output is preferable,
   - relay/server metadata handling is better through Icecast,
   - multiple public outputs are required,
   - operational separation between playout and public delivery is desired

#### 4.5.3 Incoming Remote Streams

Use the following priority:

1. direct stream handling if feasible in the selected playout/ingress architecture
2. Icecast-based ingress if this is more stable or more compatible with existing contribution tools

#### 4.5.4 Local Hardware Inputs

Local line inputs are not modeled as URLs.  
They are modeled as **first-class local audio sources**.

This requires:

- a new **Line-In** menu
- add/edit dialogs similar to **Webstream**
- device/channel selection
- persistent metadata for each local line input source

### 4.6 Soundcard Architecture

#### 4.6.1 Menu Structure

Under **Settings**, add:

- Streams
- **Soundcard**

#### 4.6.2 Soundcard Responsibilities

The Soundcard area manages:

- main playout output device
- optional preview / secondary output
- local stereo input devices
- logical naming of line inputs
- channel/device mapping
- future input/output test tools

#### 4.6.3 Abstraction Rule

Business logic must not depend directly on Windows device strings or unstable driver names.

A dedicated **Soundcard abstraction layer** must isolate:

- device enumeration
- persistence of selected devices
- internal stable identifiers
- mapping from logical channels to physical hardware

**Stable-ID secondary identifier (added in 0.2):** the original assumption
that the WASAPI endpoint GUID is a permanently stable identifier turned out
to be wrong for USB-class audio devices.  Windows can reassign the endpoint
GUID across reboots, driver updates, or port re-enumerations even when the
same physical device is plugged in.  The Soundcard abstraction therefore
persists a **friendly-name fallback** alongside every stable-ID
(`device_name` in `rastatime_linein`, `main_output_name` /
`preview_output_name` in `rastatime_soundcard_settings`).  The resolver
`WindowsAudioDeviceManager.find_device_by_id_or_name()` tries the saved
stable-ID first and falls back to a case-insensitive friendly-name match,
restoring the routing without operator intervention.  See **Section 23.4**
for the full rationale.

---

## 5. Detailed Implementation Sequence
### Step-by-Step Conversion Plan for assistant

This section intentionally breaks the project into **small, low-risk, assistant-friendly tasks**.  
Each task should be implementable, reviewable, and testable in isolation.

### 5.1 General Rules for the Build Process

1. Prefer **small pull requests / small commits**.
2. Do not change domain logic and runtime architecture in the same task if avoidable.
3. Keep the system bootable/runnable after each completed milestone whenever possible.
4. Introduce **abstractions first**, then switch implementations behind them.
5. Add Windows-specific code through **new adapters**, not through scattered inline conditionals.
6. Treat all Linux-specific runtime assumptions as technical debt to be isolated early.
7. Preserve LibreTime feature semantics before optimizing.

---

## 6. Phase 0 — Project Preparation

### 6.1 Create Fork and Freeze Baseline
**Goal:** establish a reproducible starting point.

Tasks:
1. Fork the LibreTime repository.
2. Create a dedicated branch naming convention:
   - `main`
   - `windows-port`
   - feature branches per task
3. Tag the baseline import commit.
4. Write a short `FORK_NOTES.md` describing:
   - source version/tag
   - current upstream version
   - known reasons for the fork
   - Windows-first direction
5. Record which LibreTime modules exist at baseline:
   - API
   - worker
   - playout
   - analyzer
   - legacy
   - stream-related services
6. Add a top-level `docs/architecture/` folder.

**Deliverable:** reproducible fork baseline.

### 6.2 Create Architecture Guardrails
**Goal:** avoid uncontrolled rewrites.

Tasks:
1. Add `docs/architecture/decisions/`.
2. Create initial ADRs:
   - ADR-001: Windows-first target
   - ADR-002: libVLC main playout engine
   - ADR-003: Icecast auxiliary only
   - ADR-004: English-first identifiers and UI default
   - ADR-005: NSSM for first service strategy
3. Add a `RATIONALE.md` summarizing why the fork is not a direct Linux port.

**Deliverable:** architecture decision baseline.

---

## 7. Phase 1 — Inventory and Isolation

### 7.1 Inventory Linux-Coupled Code Paths
**Goal:** identify what must be replaced before implementing Windows runtime.

Tasks:
1. Search for:
   - `systemctl`
   - `/etc/`
   - `/var/`
   - `/srv/`
   - `nginx`
   - `gunicorn`
   - `celery`
   - `liquidsoap`
   - ALSA / OSS / PortAudio assumptions
2. Create a matrix:
   - file/module
   - Linux dependency type
   - keep/refactor/delete status
3. Classify each item:
   - **domain logic**
   - **runtime binding**
   - **deployment script**
   - **audio-specific**
   - **legacy UI**

**Deliverable:** Windows migration inventory.

### 7.2 Build Runtime Interfaces Before Replacing Implementations
**Goal:** decouple the system from concrete Linux components.

Create explicit interfaces / service boundaries for:
1. playout engine
2. stream ingress manager
3. stream egress manager
4. audio device manager
5. background task runner
6. service lifecycle / health reporting

**Deliverable:** interface layer committed without behavior change.

---

## 8. Phase 2 — Windows Development Bootstrap

### 8.1 Get the Existing Codebase Running in a Minimal Windows Dev Mode
**Goal:** create a non-production Windows dev baseline.

Tasks:
1. Run database layer on Windows.
2. Run core application server in dev mode.
3. Disable or stub unsupported runtime modules temporarily.
4. Document current blockers in `WINDOWS_DEV_STATUS.md`.

**Deliverable:** partial Windows dev startup, even with playout disabled.

### 8.2 Add Local Developer Bootstrap Scripts
**Goal:** one-command-ish setup for contributors.

Tasks:
1. Create PowerShell bootstrap scripts:
   - `scripts/dev/bootstrap.ps1`
   - `scripts/dev/run-api.ps1`
   - `scripts/dev/run-worker.ps1`
2. Add environment validation:
   - Python version
   - PostgreSQL presence
   - VLC/libVLC presence
   - optional RabbitMQ presence
3. Add readable failure messages.

**Deliverable:** repeatable Windows dev bootstrap.

---

## 9. Phase 3 — Playout Abstraction First

### 9.1 Introduce a Playout Engine Interface
**Goal:** stop direct coupling to Liquidsoap-style execution.

Define an internal interface such as:

- start
- stop
- pause
- load queue
- append queue items
- clear queue
- get state
- get current item
- get remaining duration
- register track change callbacks
- register error callbacks
- select output device

**Deliverable:** implementation-neutral playout contract.

### 9.2 Add a Temporary Null / Mock Playout Engine
**Goal:** enable the rest of the system to compile and run while libVLC work is ongoing.

Tasks:
1. Implement a no-audio mock engine.
2. Simulate:
   - state
   - current item
   - queue behavior
   - next-track events
3. Wire it behind a config flag.

**Deliverable:** safe scaffolding for integration work.

---

## 10. Phase 4 — libVLC Core Integration

### 10.1 Create the libVLC Adapter
**Goal:** introduce the real main playout engine.

Tasks:
1. Add libVLC binding dependency.
2. Implement `LibVlcPlayoutEngine`.
3. Support:
   - file playback
   - playlist/queue playback
   - track change callbacks
   - playback state retrieval
   - stop / pause / resume
4. Keep the first version intentionally minimal:
   - no advanced routing yet
   - no optional stream encoding yet

**Deliverable:** basic playout engine using libVLC.

### 10.2 Connect Scheduler to the New Engine
**Goal:** prove real scheduled playback works.

Tasks:
1. Route playout dispatch through the playout interface.
2. Map current scheduling actions to:
   - soft start
   - hard start
   - stop current
   - load next queue
3. Verify:
   - scheduled playback starts
   - track metadata updates
   - fallback playout can start after show content ends

**Deliverable:** scheduled playback works through libVLC.

### 10.3 Move “Current Track” and “Now Playing” to Engine Callbacks
**Goal:** replace old playout event assumptions.

Tasks:
1. Subscribe to libVLC events.
2. Feed:
   - now-playing data
   - history/logging
   - dashboard updates
3. Normalize track event payloads so the rest of the system is engine-agnostic.

**Deliverable:** playout status pipeline based on libVLC callbacks.

---

## 11. Phase 5 — Default Rotation and Queue Semantics

### 11.1 Recreate LibreTime-Compatible Fallback Behavior
**Goal:** preserve operator expectations around scheduled playout and fallback.

Tasks:
1. define queue priority rules
2. define scheduled show queue behavior
3. define fallback/default rotation behavior
4. document exact switching rules

**Deliverable:** written behavior contract.

### 11.2 Implement Queue Manager
**Goal:** centralize queue logic outside raw libVLC calls.

Tasks:
1. create queue manager module
2. distinguish:
   - active show queue
   - fallback/default queue
3. expose:
   - refill checks
   - queue-empty actions
   - show-end transitions
4. add unit tests

**Deliverable:** deterministic queue orchestration layer.

---

## 12. Phase 6 — Streaming Architecture

### 12.1 Build a Stream Capability Matrix
**Goal:** decide what libVLC can do directly and where Icecast is needed.

Tasks:
1. list all stream-related LibreTime use cases:
   - outgoing public streams
   - multiple output streams
   - incoming live contribution streams
   - metadata propagation
   - reconnect behavior
2. test each use case against libVLC capabilities
3. classify each:
   - supported directly by libVLC
   - better handled by Icecast
   - needs custom bridge logic

**Deliverable:** implementation decision matrix.

### 12.2 Implement Outgoing Stream Layer
**Goal:** keep public streaming capability.

Tasks:
1. define stream output model
2. implement first output path
3. choose runtime:
   - direct libVLC if sufficient
   - Icecast-backed if better
4. expose output status in system UI/API

**Deliverable:** one working outgoing stream path.

### 12.3 Implement Incoming Remote Stream Layer
**Goal:** preserve live contribution features.

Tasks:
1. define input source model for remote streams
2. decide per source type:
   - direct ingestion
   - Icecast mount based ingress
3. add authentication/config persistence where required
4. connect switching logic to playout runtime

**Deliverable:** one working remote live input path.

---

## 13. Phase 7 — Soundcard and Local Line-In/Line-Out

### 13.1 Create Device Enumeration Service
**Goal:** introduce stable Windows audio hardware discovery.

Tasks:
1. create audio device service
2. list:
   - output devices
   - input devices
   - channel counts
   - stable internal identifiers
3. expose API endpoint(s)
4. cache the normalized device list if needed

**Deliverable:** device enumeration API.

### 13.2 Add Soundcard Settings Submenu
**Goal:** provide operator-level hardware mapping.

Tasks:
1. add **Settings → Soundcard**
2. add fields for:
   - main output
   - preview output (optional)
   - line-in devices
3. persist selected devices
4. handle “device missing after reboot” gracefully

**Deliverable:** configurable soundcard UI and persistence.

### 13.3 Add Line-In Domain Model
**Goal:** represent local line inputs as proper system entities.

Suggested fields:
- id
- name
- device_id
- channel_mapping
- enabled
- description
- priority / switching metadata (if needed later)

**Deliverable:** local line-in model + persistence.

### 13.4 Add Line-In UI
**Goal:** match the requested UX.

Tasks:
1. add **Line-In** menu entry
2. create list view
3. create add/edit dialog similar to **Webstream**
4. replace URL input with:
   - device selection
   - channel mapping
   - logical name
5. add enable/disable support

**Deliverable:** Line-In UI feature.

### 13.5 Add Actual Local Input Routing
**Goal:** make local hardware inputs usable in runtime.

Tasks:
1. define how a line-in is activated
2. define source priority vs scheduled playout
3. define fade/switch behavior
4. integrate with the stream/pllout source selection model

**Deliverable:** one working local line-in path.

---

## 14. Phase 8 — Worker and Background Task Replacement

### 14.1 Isolate All Background Jobs
**Goal:** remove hard dependency on the current unsupported worker model.

Tasks:
1. list background jobs:
   - media scan
   - podcast checks
   - import tasks
   - scheduled generation
   - cleanup
   - push/export tasks
2. separate short jobs from long-running jobs
3. identify retry behavior needs

**Deliverable:** worker workload inventory.

### 14.2 Implement Windows-Compatible Background Runner
**Goal:** replace Celery-centric assumptions.

Tasks:
1. create a Windows-friendly job runner process/service
2. define:
   - job registry
   - retry rules
   - logging
   - status reporting
3. port jobs one by one
4. keep broker integration optional, not mandatory, unless clearly beneficial

**Deliverable:** background runner operating without Celery dependency.

---

## 15. Phase 9 — Web/API Runtime Simplification

### 15.1 Remove UNIX-Only Serving Assumptions
**Goal:** stop depending on gunicorn/nginx-specific deployment expectations.

Tasks:
1. remove gunicorn-only deployment assumptions from docs and scripts
2. define Windows-oriented web serving strategy
3. keep first production model simple:
   - application server
   - optional reverse proxy only if really needed
4. update health endpoints

**Deliverable:** Windows-oriented serving model.

### 15.2 Keep URLs, API Semantics, and User Behavior Stable
**Goal:** minimize migration shock.

Tasks:
1. preserve existing route semantics where practical
2. preserve response shape unless there is a clear reason to change it
3. add compatibility shims when helpful

**Deliverable:** stable integration surface.

---

## 16. Phase 10 — Data, Metadata, and History

### 16.1 Preserve Core Domain Schema First
**Goal:** avoid accidental feature regressions.

Tasks:
1. keep show/media/history-related schema compatible where possible
2. add only the new tables/entities that are required for:
   - line-ins
   - soundcard mappings
   - Windows runtime settings
3. avoid unnecessary schema churn

**Deliverable:** controlled schema evolution.

### 16.2 Rebind History Logging to New Runtime Events
**Goal:** replace playout history generation tied to old engine assumptions.

Tasks:
1. define normalized playback event record
2. map libVLC callbacks to history events
3. map stream/live-switch events to history where relevant
4. verify exports/reports still work

**Deliverable:** playout history restored on new runtime.

---

## 17. Phase 11 — Frontend Language and UX Consolidation

### 17.1 Normalize UI Language
**Goal:** make English the canonical system wording.

Tasks:
1. set frontend default locale to English
2. keep German as the only additional locale in phase 1
3. align terminology across UI, docs, and API references

**Deliverable:** English-first UI baseline.

### 17.2 Add New Menus Without Breaking Familiar LibreTime Navigation
**Goal:** preserve user orientation.

Add or revise:
- Line-In
- Settings → Soundcard

Do not casually rename existing LibreTime concepts unless there is a real clarity gain.

**Deliverable:** feature-complete phase-1 menu structure.

---

## 18. Phase 12 — Windows Service and Operations Layer

### 18.1 Define Service Split
**Goal:** decide which processes become separate Windows services.

Candidate services:
- web/API service
- background runner
- playout runtime
- optional stream gateway / Icecast service
- optional broker service

**Deliverable:** service topology definition.

### 18.2 Add NSSM Service Definitions
**Goal:** enable auto-start after reboot.

Tasks:
1. create service install scripts
2. create service remove scripts
3. create service status helper scripts
4. define restart order and dependencies
5. document logs and recovery steps

**Deliverable:** repeatable Windows service setup.

### 18.3 Add Operator Documentation
**Goal:** make local maintenance practical.

Write:
- install guide
- upgrade guide
- backup guide
- crash recovery guide
- “audio device missing after reboot” guide
- “line-in stopped working” guide

**Deliverable:** minimum operational docs.

---

## 19. Phase 13 — Final Hardening

### 19.1 Kill Leftover Linux Assumptions
**Goal:** avoid hidden runtime breakage.

Tasks:
1. remove dead Linux-specific code
2. remove obsolete Liquidsoap references where no longer needed
3. remove obsolete deployment notes
4. clean environment variables and config defaults

**Deliverable:** Windows-first codebase.

### 19.2 Test Matrix
**Goal:** validate the fork as a product, not just as code.

Test areas:
- reboot recovery
- missing audio device handling
- scheduled playout
- fallback playout
- outgoing stream continuity
- incoming stream switching
- local line-in switching
- history/log integrity
- settings persistence
- language switching
- service restart behavior

**Deliverable:** release-readiness checklist.

---

## 20. Recommended Milestone Order

To keep assistant tasks small and coherent, use this milestone order:

1. **Fork baseline + ADRs**
2. **Linux dependency inventory**
3. **Windows dev bootstrap**
4. **Playout interface**
5. **Mock playout engine**
6. **libVLC basic playback**
7. **Scheduler → libVLC integration**
8. **Track callbacks / now-playing**
9. **Queue manager + fallback**
10. **Device enumeration**
11. **Soundcard settings**
12. **Line-In model + UI**
13. **Local line-in runtime**
14. **Outgoing stream capability matrix**
15. **Outgoing stream implementation**
16. **Incoming stream implementation**
17. **Background runner replacement**
18. **History/report rebinding**
19. **Windows service automation via NSSM**
20. **Hardening, docs, packaging**

This order minimizes cross-coupled changes and allows each milestone to build on stable abstractions.

---

## 21. Final Architectural Position

RASTATIME should be implemented as a:

> **Windows-first, LibreTime-compatible, libVLC-centered radio automation fork**

with the following non-negotiable rules:

1. **LibreTime is the functional baseline**
2. **libVLC is the mandatory main playout engine**
3. **Icecast is optional and auxiliary**
4. **Windows 11 is the primary runtime target**
5. **English is the canonical system language**
6. **German is the first optional frontend translation**
7. **NSSM is the first service-start strategy**
8. **Local Line-In and Soundcard routing are first-class Windows features**

---

## 22. External Reference Notes

These external references are the main evidence base for the technical direction of this draft:

- LibreTime official architecture docs
- LibreTime official configuration docs
- LibreTime user documentation for Streams / soundcard output / input streams
- LibreTime installer docs and Linux deployment assumptions
- LibreTime GitHub releases and repository
- official docs for PostgreSQL, RabbitMQ, Icecast, libVLC, Django, Celery, nginx, NSSM

This draft intentionally uses those sources to support a **Windows-first adaptation strategy**, not to imply that current upstream LibreTime already supports this target natively.

---

## 23. Phase B.4 Stabilisation Decisions (2026-05-14)

Phase B.4 hardened the source-handling and audio-device-routing subsystems
after empirical issues surfaced on the production-class Windows 11 + Icecast
2.4.4 + Apache/PHP-fcgid stack.  The four decisions below are now binding;
older sections of this document have been amended in-place where they
described the previous architecture.

### 23.1 Per-DJ Source Authentication via `stream_auth`

**Decision.** Source clients (BUTT and equivalent) authenticate against
Icecast's `<authentication type="url">` block using the `stream_auth`
option only — **not** `mount_add` as a primary auth callback.

**Rationale.**  Icecast 2.4's `mount_add` URL is a post-admission
notification with no identity payload (only `action`, `mount`, `server`,
`port` are POSTed) and cannot serve as a real auth gate.  `stream_auth`
fires before admission and forwards `user` + `pass` + `mount` + `ip`,
allowing a true per-DJ check.  Confirmed against the bundled Icecast 2.4
docs (`/c/Tools/Icecast/doc/auth.html`).

**Implementation.**  A light PHP at `public/icecast-source-auth.php` (no
Zend bootstrap, to fit inside Icecast's ~3 s auth timeout) validates
against:

* `/main` → `cc_pref.live_stream_master_username` + `live_stream_master_password`
  (plain comparison) **or** operator-override `source` / `master-secret`
  for DB-down recovery.
* `/show` → strict mode (Variant A): an unmodified show must be running
  right now, then either the show's custom credentials
  (`live_stream_user`/`live_stream_pass` plain) or a host of the show
  (`cc_subjs ∪ cc_show_hosts`) with the Legacy LibreTime md5 password
  hash.

### 23.2 Direct-to-Playout Source-Event Wiring

**Decision.**  Icecast's `mount_add` and `mount_remove` URLs point
**directly** at the playout's HTTP listener (`http://127.0.0.1:8770/source-event`).
PHP is **not** in this path.

**Rationale.**  An earlier attempt routed these events through the same
PHP that handles `stream_auth`, with the PHP firing async curls to
`:8770`.  Empirically the async pattern (`popen('start /B …')` on
Windows fcgid) reported success (`popen=ok`) but the detached curl child
did not consistently deliver to `:8770` — observed many times in the
debug log under `C:\Temp\icecast-source-auth.log`.  Icecast itself
performs proper outbound HTTP for these URLs and is treated as the
trusted notifier.

The query string carries `source=master|show` and `status=on|off` (XML-
escaped as `&amp;`); the playout listener reads from `urlparse(self.path).query`
and ignores the POST body Icecast also sends.

### 23.3 Reconciliation Watchdog

**Decision.**  The playout runs a 10 s polling watchdog inside
`libretime_playout.source_switcher` that queries Icecast's
`/admin/listmounts` (admin Basic auth) and reconciles the in-memory
`SourceSwitcher` state with whatever Icecast actually reports.

**Rationale.**  Icecast 2.4's `mount_remove` notification is empirically
unreliable on this stack — a source disconnect occasionally does not
result in the configured URL being called.  Without the watchdog, the
SourceSwitcher's `master_connected` / `show_connected` flags drift away
from reality and the playout keeps pointing FFmpeg streamers at empty
mounts.  Worst-case stuck-state duration with the watchdog: ~10 s.

`/admin/listmounts` was chosen over the public `/status-json.xsl`
because `/main` and `/show` are `<hidden>1</hidden>` and never appear in
the public JSON listing.

**Liquidsoap engine (Phase C4, revised 2026-09-09).**  With
`input.harbor` owning `/main` and `/show`, the watchdog polled
`master_dj.status` / `show_dj.status` over telnet every 5 s instead.
Since option d (§23.27, addendum 2026-09-09 b) the harbor callbacks
report every connect and disconnect to `/source-event` themselves and
the telnet round is only a verification — one second after each event
and every `RASTATIME_DJ_RECONCILE_SECONDS` (120 s) otherwise.

### 23.4 Friendly-Name Fallback for Stable IDs

**Decision.**  Every persisted audio-device reference carries both a
stable-ID and the OS-reported friendly name.  The resolver
`WindowsAudioDeviceManager.find_device_by_id_or_name()` tries the saved
stable-ID first and falls back to a case-insensitive name match.

**Rationale.**  WASAPI endpoint GUIDs are not actually stable for USB-class
audio devices.  Windows can reassign the GUID after reboots, driver
updates, or port re-enumerations even when the same physical device is
plugged in (observed with a Jabra USB headset).  Section 4.6.3's
"internal stable identifiers" assumption was therefore weakened in
practice.  Persisting the friendly name and using it as a fallback
restores routing without operator intervention.  A WARNING in the
service log nudges the operator to re-save the picker so the new GUID
is persisted and future starts don't need the fallback step.

Implementation: `rastatime_linein.device_name` (migration `0004`),
`rastatime_soundcard_settings.main_output_name` /
`preview_output_name` (migration `0002`).  Resolver is generic and
used by both linein capture (`PlayoutScheduler._resolve_linein_device`)
and main-output restoration (`libretime_playout/__main__.py`).

### 23.5 Dashboard "On Air" Indicator — Live Source-State Read

**Decision.**  The legacy Dashboard's "On Air" indicator reads source
state live from the playout's `/source-state` endpoint, not from
`cc_pref.{master_dj,live_dj,master_dj_switch,live_dj_switch}` columns.

**Rationale.**  The cc_pref columns used to be flipped by the
Liquidsoap-era PHP path
(`/api/update-source-status`), which is no longer wired up — the
direct-to-:8770 refactor removed the only remaining writer.  Reading
from those columns now would always return "off".  The playout's
in-memory `SourceSwitcher` is the source of truth; the
`Preference::GetSourceStatus()` /
`Preference::GetSourceSwitchStatus()` helpers fetch from
`http://127.0.0.1:8770/source-state` with a per-request static cache
(one HTTP call per dashboard poll, not per source-name lookup) and a
500 ms timeout.

### 23.6 File-Import Playability Check via FFmpeg

**Decision.**  The pipeline's `analyze_playability` step decode-verifies
every imported audio file with FFmpeg.  The upstream Liquidsoap-based
check is no longer used.

**Rationale.**  Liquidsoap was removed from the runtime in ADR-002, so
the original Liquidsoap-dependent playability check silently no-op'd
on every RASTATIME import.  Broken or partially-corrupted files were
therefore admitted to the library and only surfaced their issues at
actual playout time (typical symptom: `mpv[ffmpeg/audio/error]
mp3float: Header missing` on the last frame of poorly-encoded MP3s,
prematurely ending the schedule slot and producing a barely-audible
glitch).  FFmpeg is already in the runtime for streaming and capture,
so the replacement check adds no new dependency.

**Behaviour.**  `ffmpeg -v error -i <file> -f null -` is invoked with
a 120 s timeout per file.  Exit-code semantics:

| FFmpeg result                         | Action                                       |
|---------------------------------------|----------------------------------------------|
| exit 0, empty stderr                  | clean — import as normal                     |
| exit 0, stderr lines                  | soft-warn — log WARNING, import allowed      |
| exit ≠ 0                              | hard-reject — raise `UnplayableFileError`    |
| FFmpeg binary missing or timeout      | fail-open — log WARNING, import allowed      |

The fail-open branch for "FFmpeg missing" preserves the upstream
"missing tool ⇒ don't block uploads" semantic the Liquidsoap branch
had.

A standalone re-scan tool at
`infra/scripts/maintenance/rescan-playability.py` applies the same
check to the existing library to surface pre-existing soft-warn /
broken files that were imported before this check was wired in.

### 23.7 Removal of Phantom Auto-Switch UI

**Decision.**  The "Auto Switch On" and "Auto Switch Off" checkboxes
in Settings → Streams → Live Broadcasting are removed.

**Rationale.**  Both checkboxes saved a value to `cc_pref` but the
only code path that ever consumed those values was
`ApiController::updateSourceStatusAction()`, which sent RabbitMQ
messages to the Liquidsoap-based Pypo playout — both removed in
ADR-002.  The post-ADR-002 `SourceSwitcher` performs the equivalent
Master > Show > Scheduled priority transitions unconditionally; there
is no dispatch target left for an operator gate.  Leaving the
checkboxes visible was actively misleading — operators reasonably
expected them to do something, and they did not.

Reintroducing operator-controlled gates would require non-trivial
architectural work in `SourceSwitcher` (per-transition skip flags,
new HTTP endpoints to flip them at runtime, dashboard UI hooks); no
concrete operator use-case justifies that work today.  If a real
use-case surfaces, the gates can be reintroduced with a focused
ADR.

The `cc_pref` rows themselves (`keystr = 'auto_transition' /
'auto_switch'`) are left in the database for legacy-data
preservation; nothing reads them now.  The `updateSourceStatusAction`
controller method is reduced to a no-op stub (kept for v1-API-client
back-compat) rather than being deleted outright.

### 23.8 ReplayGain End-to-End

**Decision.**  The precomputed per-track ReplayGain offset is applied
at the playout-engine boundary: both the mpv local-monitor and every
FFmpeg streamer accept a ``replay_gain_db`` argument on ``play()`` /
``start()`` and emit a single ``volume=<dB>dB`` audio filter.  Live
sources (line-in, master, show, webstream) pass ``None`` and are
not gain-modified — those don't have a per-track value to apply.

**Rationale.**  The analyzer-pipeline step ``analyze_replaygain.py``
has been writing per-track dB values into ``cc_files.replay_gain``
all along.  The scheduler reads ``cc_pref.replay_gain_modifier``
(operator global preamp) plus the per-track value and writes the
sum onto ``FileEvent.replay_gain`` in ``player/schedule.py``.  Before
this commit, neither the mpv engine nor the FFmpeg streamers
referenced that field — the configured ReplayGain UI ran into the
void: setting persisted, no audio change.

**Implementation.**
* ``PlayoutEngine.play()`` interface gains an optional
  ``replay_gain_db`` keyword argument (defaults to ``None``).
* ``MpvPlayoutEngine.play()`` sets the libmpv ``af`` property:
  - non-``None`` and non-zero ⇒ ``lavfi=[volume=<dB>dB]``;
  - else ⇒ ``""`` (clears any previous filter so live sources don't
    inherit a previous track's gain).
* ``FfmpegStreamer.start()`` injects ``-af volume=<dB>dB`` between
  ``-i`` and the encoder args.  Near-zero (|dB| < 0.001) is treated
  as no-op so the FFmpeg filter chain is omitted entirely.
* ``PlayoutScheduler`` plumbs ``event.replay_gain`` into both
  ``engine.play()`` and ``_start_streamers()`` at file-event start,
  and caches it on ``self._current_replay_gain_db`` so the resume
  path (DJ-disconnect fallback, hot-reload, schedule refresh) keeps
  the right correction applied.
* ``VlcPlayoutEngine.play()`` accepts the parameter for interface
  compatibility but does not apply it — the libVLC backend is no
  longer the default engine since ADR-002 and a libVLC-native
  ReplayGain path would conflict with mpv's filter-graph approach.

Out of scope for this change (deferred to a follow-up):
* Static per-source input gain for live sources (Linein, Webstream,
  Master/Show) — a different feature with the same FFmpeg filter
  mechanism but per-source configuration; only worth implementing
  if an operational need surfaces.
* EBU R128 real-time loudness normalisation at the output stage
  — planned as the next loudness step.

### 23.9 Localisation Pipeline on Windows

**Context.**  Upstream LibreTime relies on the GNU gettext toolchain on
the deployment host to compile each `frontend/legacy/locale/<LANG>/
LC_MESSAGES/libretime.po` into a binary `libretime.mo` at install time
(see the existing `frontend/legacy/locale/Makefile`).  Without the `.mo`
the PHP `gettext` extension's lookup misses and returns the English
source string — the language dropdown silently has no effect.

On a typical Linux Debian/Ubuntu LibreTime install the `gettext` package
is a transitive dependency and the Makefile fires from the installer.
RASTATIME's Windows install path has neither piece: `gettext` is not a
Windows OS package, and the upstream Makefile is GNU-make + Bash and
does not run on plain PowerShell.  Result: every locale we shipped was
inert.

**Decision.**  We adopt mlocati's `gettext-iconv-windows` standalone
binary distribution (a ~6 MB ZIP, single-folder extract, no installer
and no MSYS2/Cygwin dependency) and ship a small PowerShell driver
script that compiles only the locales we actually maintain.

**Why this over alternatives.**

| Option | Why not |
|---|---|
| MSYS2 / Cygwin | ~500 MB toolchain for a single CLI tool we invoke once per change to `.po` files.  Adds a parallel POSIX environment that nothing else in the RASTATIME stack needs. |
| WSL | Hard veto by product (RASTATIME stays Windows-native; WSL adds a Linux VM the operator must manage). |
| Chocolatey/winget `gettext` | Works, but introduces an external package-manager dependency for one binary.  We prefer a checked-in download instruction. |
| Bake `.mo` files into the repo | Compiled binaries from `.po` files; mixes generated artefacts with source.  Re-build is cheap; storing the source is enough. |
| Pre-compile at CI time | Reasonable future direction, but no CI runner yet exists for RASTATIME; deferring. |

**Implementation.**
* `infra/scripts/maintenance/build-locales.ps1` searches `msgfmt.exe` on
  PATH, then at the recommended mlocati install location
  (`C:\Tools\gettext-iconv\bin\msgfmt.exe`), then at the `Program Files`
  fallback paths, then accepts an explicit `-MsgfmtPath` argument.
* The script's `$activeLanguages` array must stay in sync with the
  `$locales` map in `frontend/legacy/application/models/Locale.php`; both
  call out the constraint in comments.
* `msgfmt` runs with `--check-format --check-domain` so a malformed `.po`
  fails the build instead of producing a silently broken `.mo`.
* `.mo` files are written next to the source `.po`.  They are an
  intentionally-tracked artefact in the repo: the operator runs the
  script after pulling translation updates and commits both source and
  compiled file together.  Rationale: avoids requiring the gettext
  toolchain on production Windows hosts that only need to *run* RASTATIME.

**Operator workflow.**
1. One-time setup: download mlocati ZIP, extract to
   `C:\Tools\gettext-iconv\`.
2. After any `.po` edit (translation update, new translatable string):
   `powershell -ExecutionPolicy Bypass -File infra\scripts\maintenance\build-locales.ps1`
3. Restart Apache (httpd) so the PHP gettext cache invalidates.

Step-by-step instructions for editing individual translations and for
adding a new language are kept in
`frontend/legacy/locale/README.md` (operator-facing, lower abstraction
level than this section).

**Language-set reduction.**  The upstream `Locale.php $locales` array
exposed 22 entries.  In practice we maintain four (`en_US`, `de_DE`,
`fr_FR`, `es_ES`); the other 18 were inherited Transifex/Weblate
translations of varying staleness and offered no support pathway from
RASTATIME.  All 18 `.po` directories plus their matching
`public/js/datatables/i18n/*.txt` and `public/js/plupload/i18n/*.js`
files are deleted from the repo.  Re-adding a language requires four
synchronised edits documented in `Locale.php`.

**Known runtime quirk on Windows.**  PHP's `setlocale(LC_MESSAGES, ...)`
returns `false` for many UTF-8 locale identifiers on Windows hosts that
do not have the corresponding system locale installed — this is logged
as a warning by `Application_Model_Locale::configureLocalization()`.
The warning is tolerable: the `LANGUAGE` env var (set unconditionally
on line 51 of `Locale.php`) is sufficient for gettext's `bindtextdomain`
lookup to find the right `.mo` file regardless of the OS-level locale
table.  We do not depend on `setlocale` for translation correctness.
Even so, `configureLocalization()` now tries multiple setlocale
variants (`<locale>.UTF-8`, bare `<locale>`, BCP47 `<locale>` with
underscore-to-hyphen substitution) so the call succeeds when
possible.

**Three upstream-inherited bugs uncovered by activating the
pipeline.**  Producing real `.mo` artefacts exposed three latent
defects in the legacy frontend that had been invisible while the
pipeline was inert (every `_()` fell through to the English source
string regardless of which locale was selected):

1. **`PreferenceController` only wrote one of three locale surfaces.**
   RASTATIME carries three sources of locale truth: the
   `airtime_locale` cookie (priority 1 in pre-login and Edit-User
   paths), `cc_pref.user_locale` rows (priority for logged-in users),
   and the global `cc_pref.locale` row (fallback / default for new
   users).  The Settings → General form save only updated the global
   row, so an admin flipping "Default Language" saw no UI change.
   The save now writes all three surfaces in one transaction and
   re-runs `configureLocalization()` inline so even the
   confirmation message lands in the new language.

2. **`configureLocalization($locale = null)` use-after-null.**  When
   called without an argument (the `PageLayoutInitPlugin` hot path),
   it ran `putenv("LANGUAGE={$locale}")` with `$locale` still null,
   silently emptying the env var that drives gettext's `.mo`
   lookup.  gettext then fell back to whatever locale state the
   Apache/fcgid worker carried from a previous request, producing a
   sticky-stale UI ("German never goes away after switching to
   English").  Fix: resolve `$locale` before the `putenv` call.

3. **`navigation.php` translated at Bootstrap time.**  The legacy
   navigation config builds the top-nav Zend_Navigation container at
   Bootstrap time — strictly before `configureLocalization()` runs —
   using direct `_('Calendar')`, `_('Settings')` etc. calls.  Whatever
   half-initialised locale state the worker held was baked into the
   container; `views/scripts/menu.phtml`'s later
   `_($page->getLabel())` pass could not reverse-translate because
   msgid keys are always English.  The file's own header comment
   already acknowledged that translation was supposed to happen in
   menu.phtml, but the code did not match that intent.  Fix:
   `navigation.php` now stores plain English source strings; the
   single `_()` pass in menu.phtml is the only translation point.
   The strings are still referenced from other view scripts, so the
   gettext extraction toolchain continues to pick up their msgids
   from those locations without a separate noop marker function.

### 23.10 Per-Webstream Input-Gain and Gain Parameter Generalisation

**Context.**  Section 23.8 wired ReplayGain end-to-end for scheduled
file tracks: `cc_files.replay_gain` plus the global
`cc_pref.replay_gain_modifier` were summed in the scheduler, threaded
through `FfmpegStreamer.start(replay_gain_db=...)` /
`MpvPlayoutEngine.play(replay_gain_db=...)`, and emitted as a single
`-af volume=<dB>dB` audio filter before the encoder/output stage.
Live sources (linein, master/show, webstream) passed `None` and were
not gain-modified — there was no per-source gain concept on this
branch.

The operator-facing pain point that triggered this change: webstreams
from third-party feeds (community-radio relays, news bulletins,
weather audio) frequently arrive at substantially different levels
than the rest of the schedule.  RASTATIME's only previous workaround
was to ask the upstream feed operator to renormalise their stream, or
to manually re-encode the feed through a relay — neither pleasant.

**Decision.**  Add a per-webstream static input-gain field, applied
through the same FFmpeg `volume` filter mechanism already proven for
ReplayGain.  Same code path, same audio quality, same CPU cost
profile.  This also opens the door to an equivalent per-line-in gain
later (deliberately not built yet because the line-in level is more
naturally adjusted at the soundcard input-gain stage on Windows, but
the plumbing would be identical if we change our minds).

**Schema.**
* New column `cc_webstream.input_gain_db NUMERIC DEFAULT 0` (Django
  migration `0048_add_cc_webstream_input_gain_db`).  Range enforced
  at the UI and controller layers as `-20.0` to `+20.0` dB; the DB
  column itself is unconstrained NUMERIC for forward-compat.
* The Propel `CcWebstream` class is **not** regenerated for this
  column — the legacy frontend's existing setter chain in
  `Application_Model_Webstream::save()` does a `$webstream->save()`
  via the existing Propel model and then issues a raw-SQL UPDATE for
  the new column.  Symmetric raw-SQL read via
  `Webstream::getInputGainDbForId($id)` for the edit form's
  pre-fill.  Rationale: regenerating Propel classes touches many
  files (om/ base classes) and risks unintended drift in unrelated
  models; the dual-write (Propel + raw SQL) for one column is the
  same workaround used for `cc_schedule.linein_id` in section 23 of
  Phase A.

**API.**  `WebstreamSerializer.Meta.fields = "__all__"` automatically
exposes the new column to the playout's REST client.

**Event model.**
* `WebStreamEvent` gains `input_gain_db: Optional[float] = None`.
* `player/schedule.py::generate_webstream_events` reads
  `webstream["input_gain_db"]` (graceful `None` fallback for older
  API responses) and stamps it on **every** event of the stream
  (BUFFER_START / OUTPUT_START / BUFFER_END / OUTPUT_END) — the
  scheduler's resume path reads it back from `_current_event` after
  a DJ-disconnect.

**Engine parameter generalisation.**  The existing
`replay_gain_db` parameter on the engine `play()` /
`FfmpegStreamer.start()` / `PlayoutScheduler._start_streamers()`
boundary is renamed to **`gain_db`**.  The mechanism is unchanged
(same FFmpeg `volume` filter), but the parameter name now reflects
that the value's source depends on the calling event type:

| Event type | Value source |
|---|---|
| `FileEvent` | precomputed ReplayGain sum (`cc_files.replay_gain` + `cc_pref.replay_gain_modifier`) |
| `WebStreamEvent` | `cc_webstream.input_gain_db` |
| `LineinEvent` | `None` (no per-source gain feature yet) |
| Live source `/main` / `/show` | `None` |

The scheduler picks the right source value when constructing the
event and passes the result.  The streamer and the mpv engine treat
`None` or `0.0` as a no-op (no filter added to the chain).

The cached `_current_replay_gain_db` field on `PlayoutScheduler` is
likewise renamed to `_current_gain_db` and now stores whichever event
type's gain is active, so the resume path (DJ-disconnect, hot-reload)
re-emits the correct filter when restarting the streamers.

Considered alternatives, rejected:
* **Keep `replay_gain_db` and silently overload it to also carry
  webstream input-gain.**  Lexically clean, semantically dishonest;
  a future maintainer would read `replay_gain_db` and assume the
  value originated from ReplayGain analysis.
* **Add a parallel `input_gain_db` parameter alongside
  `replay_gain_db`.**  Two parameters that the streamer would
  internally sum; gives the scheduler false flexibility (when would
  it ever pass both?) and makes the FFmpeg-filter emission code
  branch unnecessarily.

**UI.**  The webstream edit dialog (`webstream.phtml`) gets a
numeric input "Input Gain (dB)" between Default-Length and the
Save/Cancel buttons.  Pre-filled from
`Webstream::getInputGainDbForId()`; saved via the existing
`webstream/save` AJAX endpoint as a new `input_gain_db` parameter.
The controller clamps to `[-20, +20]` and falls back to 0 on
non-numeric input.

**Tests.**  The five existing tests in
`test_ffmpeg_streamer_replay_gain.py` are renamed to
`test_ffmpeg_streamer_gain.py` and use the new `gain_db` keyword.
Same assertion coverage (no-op when None / near-zero, positive
emission, negative emission with sign preservation, filter ordering
before encoder).  The tests do not depend on whether the value
originated as ReplayGain or input-gain — they exercise the streamer's
filter emission only.

**Out of scope for this change** (deferred):
* Per-line-in static gain — same one-line plumbing once the operator
  decides whether the soundcard-side input-gain stage covers it.
* A live in-UI dB meter at the Add-Webstream stage (would require an
  async server-side FFmpeg sampling probe and a websocket back to the
  UI; not enough operator value to justify the complexity).

### 23.11 Track Expiry and Podcast Auto-Expiry

**Context.**  RASTATIME stations frequently subscribe to podcasts that
publish daily or weekly episodes (news, weather, community bulletins).
After a few months the library accumulates hundreds of stale podcast
episodes that no one wants to schedule any more but that nobody has
time to delete manually.  Disk space starts mattering, and worse, the
Smartblocks that match on track-type tags begin to dredge up year-old
episodes when an operator wanted "recent" ones.

The complementary problem: occasional one-off tracks (timed campaigns,
holiday spots, "valid until election day" PSAs) have a known expiry
even when uploaded manually.  The operator wants those flagged for
removal without having to remember the date on a sticky note.

**Decision.**  Introduce a single `cc_files.expires_at TIMESTAMP NULL`
column that drives a shared hourly pruner.  Two input pipelines write
to it:

1. **ID3-tag pipeline** (manual upload, generic file).  The analyzer's
   `analyze_metadata` step now reads a custom ID3v2 TXXX frame whose
   `Description` is exactly `Expiry` and whose value is an ISO-8601
   date string (`YYYY-MM-DD`).  Tools like Mp3tag and Kid3 set this
   trivially.  Other tag formats (Vorbis comments, MP4 atoms) are not
   currently scanned — operator workflow on this branch is
   dominantly MP3 + ID3v2 and adding more formats is straightforward
   when needed.

2. **Podcast Auto-Expiry pipeline** (podcast subscription).  The
   `imported_podcast` table gains
   `auto_expiry_enabled BOOLEAN DEFAULT false` and
   `auto_expiry_days INTEGER NULL`.  When auto-expiry is on, the
   Django `download_episode` view (which receives the new columns
   from `ImportedPodcast`) computes
   `expires_at = now() + auto_expiry_days` and writes it on the
   `cc_files` row at the same time the file is moved into the media
   store.

**Precedence (decision B, 2026-05-16):** Podcast Auto-Expiry **wins**
over any ID3 `Expiry` tag the upstream publisher embedded.
Subscribers own retention; publishers don't.  The implementation is
naturally this way: the Podcast download path writes `expires_at`
directly on `File()` construction, without ever invoking the analyzer
that would read the ID3 tag.  For non-podcast uploads the analyzer
runs and reads ID3 as the sole source.

**Action on expiry — `disabled` flag, not deletion (decision A,
2026-05-16, modified):** A separate `cc_files.disabled BOOLEAN DEFAULT
false` column captures the expired state.  The pruner only ever
flips false → true; it never removes rows or files.  Disabled tracks:

* **stay visible in the Library** (so the operator can sort, filter,
  bulk-select, and manually delete them at their leisure — they get
  a Disabled column in the library DataTable that can be enabled via
  the column-picker and used as a sort key);
* **stay in already-built Smartblocks** (so currently-scheduled
  shows keep playing them — neither the pruner nor any other
  background job touches `cc_blockcontents`);
* **are excluded from NEW Smartblock evaluations** via an additional
  `disabled = false` clause in `Block::generateSmartBlock()`'s
  criteria query, immediately after the existing `file_exists = true`
  and `hidden = false` clauses;
* **may still be scheduled directly into a Show via Showbuilder** —
  no schedule-level block.  The operator stays in control.

The distinction between `cc_files.hidden` (upstream's own
library-visibility flag for special system files) and
`cc_files.disabled` (RASTATIME's expiry marker) is deliberate;
collapsing them would tangle two unrelated concerns.

**Pruner.**  `TrackExpiryTask` in
`frontend/legacy/application/common/TaskManager.php`.  Runs hourly
via the existing TaskManager piggyback (every page hit checks
`shouldBeRun()` against
`cc_pref.track_expiry_last_run + 3600s`).  Single atomic SQL:

```sql
UPDATE cc_files
SET disabled = true
WHERE expires_at IS NOT NULL
  AND expires_at < NOW()
  AND disabled = false
```

The `rowCount()` is logged as `TrackExpiryTask: disabled N expired
files`.  No per-row loop, no schedule-conflict check, no cascade —
the design keeps the pruner trivially correct.

**Manual edit.**  The Library's Edit Audio MD form gains an "Expiry
Date" text field (YYYY-MM-DD, optional).  Empty clears.  Saving a
value back-dated to the past also flips `disabled` immediately;
saving a future date re-enables a previously-disabled file (the
`UPDATE … SET disabled = (CAST(:exp AS TIMESTAMP) < NOW())` clause
in `StoredFile::setDbColMetadata`).  Symmetric round-trip semantics.

**Read paths.**

* `StoredFile::getDbColMetadata` reads `expires_at` via raw SQL
  (Propel class is not regenerated for the new column) and exposes
  it as a `YYYY-MM-DD` string in the metadata map for the edit form.
* The library DataTable picks up `expires_at` and `disabled` through
  `StoredFile::getLibraryColumns()` and surfaces them as two new
  optional columns in `library.js`.  Hidden by default; the
  operator enables them via the standard column-picker.

**Why not regenerate the Propel classes:** same rationale as
Section 23.10 (webstream input-gain).  The `om/BaseCcFiles.php`
generator touches dozens of methods across many other files and
risks unintended drift in unrelated models for the benefit of one
column.  The two-column dual-write (Propel for everything else, raw
SQL for `expires_at` and `disabled`) is the same workaround used
elsewhere in the legacy frontend and stays isolated to two
identifiable code blocks.

**Migration.**  `0049_add_track_expiry_and_podcast_auto_expiry`:

```sql
ALTER TABLE cc_files ADD COLUMN expires_at TIMESTAMP NULL;
ALTER TABLE cc_files ADD COLUMN disabled BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE imported_podcast ADD COLUMN auto_expiry_enabled BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE imported_podcast ADD COLUMN auto_expiry_days INTEGER NULL;
```

Existing rows get `expires_at = NULL` and `disabled = false`, so the
feature is inactive until the operator enables it on a podcast or
edits a track's expiry — backwards-compatible.

**Out of scope for this change** (deferred):

* Hard-delete instead of disable — the disabled marker plus a
  manual Library bulk-delete is a safer first move and the
  operator already asked for that workflow.
* Vorbis/MP4 tag scanning for non-MP3 uploads — trivial to add
  later when a workflow shows up.
* "Expiring soon" notifications in the Dashboard — possible but
  not asked for; the Library column gives operators a sortable
  view that covers the day-to-day need.
* Per-Show "no expired tracks" guard at schedule-render time —
  current design lets the operator hand-schedule a disabled track
  on purpose (e.g. one last play before retirement).  Adding a
  warning is a 5-minute follow-up if it turns out to surprise people.

### 23.12 Local Import Folder

**Context.**  RASTATIME operators frequently produce or receive audio
on the same Windows host where the station runs — recordings from
external software, files downloaded by hand, conversion outputs from
batch tools.  The upload-via-Plupload UI path requires opening the
Library, drag-and-dropping each file, waiting for the analyzer.  That
is fine for one or two files at a time, but tedious for the "drop a
batch in a folder and walk away" workflow.

**Decision (Option A, modified 2026-05-16).**  A single configured
absolute folder on the RASTATIME host acts as a drop-folder.  Every
5 minutes (and on-demand via a "Scan Now" button), a TaskManager job
walks the folder, hands each audio file to the standard
`CcFiles::createAndImport` pipeline, and deletes the source after the
attempt — successful OR failed.

Deliberately rejected alternatives:

* **Option B — "Reference in place" (Watch-Folder).**  The original
  upstream Watched-Folders pattern: leave files where they are,
  `cc_files.filepath` points to the external path.  Operator
  considered it too fragile — renaming or moving the file outside
  RASTATIME breaks the playback path silently.  Drop-folder semantics
  with copy-to-storage are safer: once a file enters the Library it
  has a stable identity in `<storage>/imported/`, independent of
  whatever happens to the source folder afterwards.
* **Option C — Multiple folders, per-folder mode (copy vs. reference).**
  Flagged as a possible future extension; not built now because the
  single-folder drop pattern covers the announced operator workflow
  and Option C would add UI complexity (folder list, per-row mode
  picker, per-folder rescan/remove buttons) for a use-case nobody has
  asked for yet.

**Schema.**  None.  The feature is config-only, persisted in
`cc_pref`:

| Key | Type | Meaning |
|---|---|---|
| `local_import_folder` | string | absolute folder path; empty disables the scan |
| `local_import_last_run` | UNIX timestamp | drives the 5-min throttle |
| `local_import_last_status` | string | last-scan summary surfaced in the UI |

No `cc_music_dirs` row is created — the drop-folder is not a
permanent Library location, only a transient staging area.  Imported
files end up under `<storage>/imported/<owner>/` like any other
upload, indistinguishable downstream.

**Pipeline reuse.**  The scan calls
`CcFiles::createAndImport([], $fullPath, $name, $copyFile=false)`,
which is the same entry point Plupload eventually reaches.  This
gives the drop-folder importer **free**, in order:

1. A `cc_files` row with `import_status = PENDING` and `hidden = true`.
2. A `rename()` of the source into `<storage>/organize/` — atomic
   when the import folder is on the same drive as `<storage>`,
   transparent copy+delete otherwise.
3. A RabbitMQ message to the analyzer, which runs the full pipeline:
   `analyze_metadata` (incl. RASTATIME's ID3 `Expiry`-tag reader,
   Section 23.11), `analyze_playability` (Section 23.6),
   `analyze_cuepoint`, `analyze_replaygain`.
4. A PUT back to `/rest/media/<file_id>` flipping
   `import_status = SUCCESS`, `hidden = false`, and any extracted
   metadata (including `expires_at`, Section 23.11).

Because `moveFileToStor()` uses `rename()`, the source file is
**removed by the move itself** on success — no explicit `unlink()`
needed.  On failure (bad extension, permission denied, analyzer
signal failure) the helper does an explicit `@unlink($fullPath)` so a
permanently-broken file does not pile up forever in the drop-folder
and re-trigger on every scan.

**Throttle + on-demand entry.**  `LocalImportScanTask::scanOnce()` is
the single import method.  Called from two paths:

* `LocalImportScanTask::run()` — TaskManager-driven, 5-minute interval
  via the existing `cc_pref.local_import_last_run` throttle pattern
  (same shape as `TrackExpiryTask` from Section 23.11).
* `PreferenceController::localImportScanNowAction()` — the
  "Scan Now" button bypasses the throttle by calling `scanOnce()`
  directly.  Useful right after configuring a new folder so the
  operator does not have to wait up to 5 minutes for verification.

Both paths persist the same `last_run` timestamp and a human-readable
`last_status` string that the UI surfaces ("imported 3, failed 0,
skipped 1").

**UI.**  The Settings -> Soundcard page is renamed to
**Settings -> Local Machine** in `navigation.php`.  The page now
covers both audio devices (existing Output + Line-In sections) and a
new **Import Folder** section: a single text input for the absolute
path, a "Save Folder" button (validates the path is a directory AND
writable — we need to delete after import), a "Scan Now" button
disabled when no folder is configured, and a status line showing
"Last scan: <timestamp>" plus the last-status string.  The
controller action keeps its old name (`soundcard-setting`) so
existing bookmarks / links survive the rename.

**Audio file types.**  The scan recognises
`mp3, wav, m4a, flac, ogg, oga, aac, opus`.  Non-audio extensions
are silently skipped (operator may have placed them intentionally;
we do not own arbitrary files in the drop-folder).

**Out of scope** (deferred):

* **Option C — multiple folders with per-folder mode** (copy vs.
  reference, drop-folder vs. watch-folder).  Spec-ready, would
  re-activate the `cc_music_dirs` Multi-Row schema, would need a
  proper UI list with per-row controls.  Estimated +4–6 h on top of
  this section's baseline if/when the workflow demands it.
* **Sub-folder recursion.**  Currently flat: only the top level of
  the configured folder is scanned.  Recursive walk is a trivial
  one-line change in `scanOnce()` but was not asked for.
* **Network mount support.**  Should work without changes (SMB
  drives like `\\\\NAS\\Audio` are valid Windows paths), but is not
  tested.  Network reliability quirks belong in the optional
  Watch-Folder mode (Option C) if/when that lands.

### 23.13 Record-per-Show

**Context.**  Operators routinely want to keep an archive of what
actually went on air — for compliance (some jurisdictions require a
broadcast log), for re-publication as podcast / catchup, or simply
to recover a recording the host forgot to make.  The upstream
LibreTime feature was a Liquidsoap-driven Line-In recorder
(checkbox label literally "Record from Line In?"); the wider
"record whatever is on air" use case was never available on this
branch.

**Decision.**  Cross-source recording via **output-tap with
`-c copy`** on the first configured Icecast mountpoint.  The
recorder is an independent FFmpeg subprocess; it inherits the
Icecast stream as a single MP3 stream and writes it verbatim to a
file, without re-encoding.  This deliberately ties recording
quality to the stream's quality (typically 192 k or 320 k MP3),
but in exchange:

* **CPU cost is ~1–2 %** of one core on Intel i3-1315U — well below
  the next-cheapest option (Internal-Bus separate encoder at
  10–15 %).
* **Source switches are picked up automatically.**  When the
  scheduler hands the air over from a scheduled file track to a
  webstream to a line-in to a master/show DJ, the Icecast mountpoint
  reflects that transition; the recorder, being a passive listener,
  records the new source without any coordination logic of its own.
  In particular: no need to interact with the `SourceSwitcher`,
  no need to add per-event recording fan-out, no race conditions
  during transition windows.
* **Failure isolation.**  An incomplete recording (Icecast crash,
  FFmpeg crash, disk full) never affects the live stream — the
  recorder shares no process or file handle with the streamer.

Considered alternatives, rejected:

* **(b) Internal-Bus separate encoder.**  Higher recording quality
  possible (FLAC, 320 k MP3 from PCM source), but requires teaching
  the recorder which source is active at any moment (file path /
  webstream URL / dshow handle / Icecast listen-URL).  ~10× the
  code, ~10× the CPU.  Quality gain over a 320 k MP3 tap is
  borderline-imperceptible for spoken radio.
* **(c) Tee-filter inside the existing FfmpegStreamer.**  CPU-cheap
  but couples recording failure to streaming failure (a single
  FFmpeg process is now responsible for both); rejected on
  failure-domain grounds.
* **Liquidsoap-style internal pipeline.**  Not available — the
  Liquidsoap stack was removed in ADR-002.

**Event model.**  Two new event types in `EventKind`:

* `SHOW_RECORD_START` — emitted by the schedule builder at
  `show_instance.starts_at` for every show instance whose
  `record == true`.
* `SHOW_RECORD_END` — emitted at `show_instance.ends_at` for the
  same instance.

Both are carried by a new `ShowRecordEvent` Pydantic model with
fields `show_id`, `show_name`, `show_starts_at`.  `start == end`
(point-in-time events).  The schedule builder emits both events
inside `generate_show_record_events()`, which is called when the
top-level scheduler loop sees `show_instance.get("record")` truthy.
Multiple schedule items per show instance produce identical
`ShowRecordEvent`s, which `insert_event` dedupes on structural
equality — so we end up with exactly one START + one END per show
instance regardless of how many tracks are in the show.

The PlayoutScheduler arms a single timer per event in
`_arm_show_record_event` (point-in-time, so no separate stop timer
is needed); the timer's callback dispatches to
`_on_show_record_start` or `_on_show_record_end`.

**Recorder lifecycle (`FfmpegRecorder`).**  Single instance on the
PlayoutScheduler, instantiated eagerly so a missing `ffmpeg`
binary surfaces at startup, not at first show-start.  Static
state: `subprocess.Popen` handle, output path, current show id,
threading lock.  `start()` is idempotent w.r.t. an
already-running prior recording (which should never happen given
RASTATIME's non-overlapping schedule, but is handled defensively
— prior is stopped first).  `stop()` sends `q\n` to FFmpeg's stdin
for a graceful exit; falls back to `kill()` after 5 s.

The recorder command:

```
ffmpeg -reconnect 1 -reconnect_streamed 1
       -reconnect_on_http_error 4xx,5xx -reconnect_delay_max 5
       -loglevel warning
       -i http://localhost:8000/<first-mountpoint>
       -c copy -vn -y
       <recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3
```

Reconnect options ride out short Icecast hiccups without dying;
`-c copy` skips re-encoding; `-y` overwrites a half-written file
left over from a prior crashed run (which would be unusable
anyway).

**Configuration surface.**  Two cc_pref keys:

| Key | Meaning |
|---|---|
| `local_recording_folder` | absolute folder path; empty disables recording |
| (none for source URL) | derived dynamically from the first
                          `cc_pref` stream-output config |

The recording-folder string is exposed to the playout via a new
read-only API endpoint `GET /api/v2/preferences/local-recording-folder`
returning `{"folder": "<path>"}`.  The playout fetches it once per
SHOW_RECORD_START fire (~1 KB request, <50 ms typical) rather than
caching globally — operators can change the folder mid-day in the
UI and the next-show recording picks up the new value.

The source URL is derived dynamically from
`self._current_stream_configs[0]` (the first entry of the
hot-reloaded stream-output config) as
`http://{host}:{port}/{mount}`.  If the operator changes the
mountpoint name or port in Settings → Streams, the recorder follows
on the next show-start without any restart.

**Filename construction.**  `build_output_path()` composes
`<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3` from
`show_starts_at` (UTC-naive, as carried in the event) plus a
sanitized show name.  Sanitization strips Windows-illegal characters
(`<>:"/\|?*` plus control chars) and replaces them with `_`; Umlauts,
spaces, and dashes are kept verbatim per operator spec.  Per-day
subfolder gives the operator a natural archive layout.  Start time
in the filename guarantees uniqueness even for shows that air
multiple times per day.

**UI.**  Two surface changes:

1. **Settings → Local Machine** gains a "Recording Folder" section
   below the existing Import Folder section.  Simple text input
   + Save button.  Server-side save validates the path is a
   directory AND writable (the recorder creates per-day subfolders
   and writes .mp3 into them).
2. **Edit Show** form: the existing `add_show_record` checkbox
   label is renamed from upstream's "Record from Line In?" to
   simply "Record this show" — Line-In is no longer special, the
   recorder captures whatever is on air.

**Operator-visible failure modes** (all logged at WARNING, none
crash the playout):

| Precondition | Behaviour |
|---|---|
| No `local_recording_folder` configured | Show plays normally; log: "no recording folder configured" |
| No stream outputs configured | Show plays; log: "no output stream configured" |
| `ffmpeg.exe` missing at startup | `_show_recorder = None`; all subsequent SHOW_RECORD_START skip with log |
| Icecast unreachable at recording start | FFmpeg's reconnect logic retries; if persistent, recording file is empty or 0 bytes; log shows non-zero rc on stop |
| Disk full mid-recording | FFmpeg exits with error; partial file kept (unusable); log shows the rc; no retry attempted |
| Show cancelled mid-air | SHOW_RECORD_END fires earlier than scheduled; recording file is shorter than the originally-planned show duration |
| Multiple shows at the same `starts_at` (should not happen per RASTATIME's schedule model) | First `start()` wins; subsequent ones stop the prior recorder and replace it; log warning |

**Disk-space management** is intentionally out of scope for this
feature.  At 320 k MP3 a 1-hour show is ~140 MB; a typical 12-h
broadcast day is ~1.7 GB; an unattended station fills a 1 TB disk
in ~6 months.  Cleanup of old recordings is the job of the 7-day
catchup feature (Section 23.x, future) or a simple operator
cron / scheduled task; the recorder itself never deletes
anything.

**Out of scope for this change** (deferred):

* Internal-Bus mode for archive-quality recording (FLAC, 320 k
  with re-encode from PCM).  Operator can ask for it later if the
  output-tap quality turns out to be insufficient.
* Recordings showing up as `cc_files` entries in the Library.
  Per spec, recordings live in their own folder structure outside
  the Library — they are NOT auto-imported.  A future "publish
  this recording to the Library" UI action would be a follow-up
  if the use case shows up.
* Per-show choice of recording format / bitrate.  Currently
  inherits the source mountpoint.  Adding a per-show override
  would mean falling back to (b) Internal-Bus per show; not
  worth the complexity yet.
* Automated cleanup of old recordings (covered by future Catchup
  feature #9).

#### 23.13.bis — Phase-C5 Migration to Liquidsoap output.file (2026-05-28)

**Context shift.**  When the Seamless-Bus-Mix Phase-C migration moved
the whole playout pipeline to Liquidsoap (ADR-002 reversed; Section
23.x Seamless-Bus-Mix), the original FFmpeg-Icecast-tap recorder
became architecturally redundant: Liquidsoap already had the audio
on an internal bus, so a separate HTTP tap was wasteful (extra
decode/encode round-trip, 404-race during bring-up, mid-show watchdog
respawn machinery for transient HTTP source drops).  Phase-C5
deletes the FfmpegRecorder + lifecycle code (~693 LoC net) and
replaces it with a single Liquidsoap `output.file(id="recording", …)`
block tapping the internal bus directly.

**New decision.**  Recording is a Liquidsoap `output.file` block that
encodes the bus into MP3 at 320 kbps and writes to a path set
dynamically per show via the telnet interactive variable
`recording_path`.

```liquidsoap
recording_path = interactive.string(
  "recording_path",
  "C:/rastatime/recordings/_uninitialized.mp3"
)
output.file(
  id="recording",
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="320k")),
  {recording_path()},
  fallible=true,
  bus,
)
```

Per-show path-switching uses **Mechanismus B** (verified 2026-05-27
in `test_c5_mechanism_b.py`):

```
telnet> recording.stop
telnet> var.set recording_path = C:/.../<YYYY-MM-DD HH-MM> - <show>.mp3
telnet> recording.start
```

The triple-command forces Liquidsoap to re-evaluate the filename
function on the new start, opening the new file.  v1 (single `var.set`
with `reopen_when` callback) had a ~30 s polling lag because
`reopen_when` is only evaluated on frame boundaries.  Mechanismus B
is sub-second (telnet roundtrip ~30 ms).

**Why MP3@320kbps fixed** (operator decision 2026-05-27): archive-
grade quality, eliminates "the recording is worse than the stream"
class of operator complaints.  CPU cost on i3-1315U: ~3 % (one
libmp3lame encoder vs. the prior `-c copy` zero-encode tap), well
within budget.  ReplayGain is applied upstream (`amplify(override=
"replaygain_track_gain", bus)`) so the recording mirrors the stream.

**Why not internal-bus-with-format-override (operator-configurable
bitrate/codec)?** Considered but rejected for C5 scope; fixed
320 kbps MP3 keeps the configuration surface minimal.  Per-show
choice of codec/bitrate stays in the deferred-list at the end of
this section.

**Failure isolation revisited.**  The old FfmpegRecorder was isolated
from the streaming pipeline because it was a separate process.  The
new Liquidsoap output.file is INSIDE the Liquidsoap process — a
Liquidsoap crash now also kills the recording.  Mitigations:

- `fallible=true` on `output.file` lets a single output failure
  (disk full, AV scan-lock) not propagate up the source graph.
- Recording activity is on the same main clock as the Icecast
  outputs; both share the same failure-recovery patterns (NSSM
  auto-restart on Liquidsoap-process-death).
- PortAudio (local-monitor output) is in its own clock with a
  `buffer(2.0)`-bridge (Phase-C5 Side-Fix 2026-05-28) so its
  underflows don't take down recording.

**Bitdefender / antivirus interaction.**  The C5 reality-test
2026-05-28 caught a 12 % audio loss in a 60-min show that
correlated with a burst of Liquidsoap latency-catchup events
(96 catchups in one hour vs. 21–28 in neighbouring hours).
Root cause: Bitdefender's real-time scan locked the growing
recording .mp3 on every write, blocking the encoder for milliseconds
per scan-tick.  Over 60 min and ~140 MB those locks accumulated to
~7 min of dropped audio frames.  **Mitigation: the recording-folder
MUST be in the antivirus's exception list.**  After adding the
exception, the same 30-min direct telnet recording produced 100.3 %
of expected duration (1804 s of 1800 s expected at 320 kbps).
Documented in `docs/manual/RECORD_PER_SHOW.md` (and DE/FR/ES
translations).

**Operator-Pfad (Liquidsoap-only).**  Phase-C5 Teil 2d deleted
FfmpegRecorder, which means recording is **only** available when
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` is set.  In the legacy
mpv / VLC engine paths, `_on_show_record_start` logs a warning
and silently skips; the show plays normally, only the recording
is missing.  This is intentional — the operator committed to
Liquidsoap as the recording-pipeline-of-record (no pun) on
2026-05-27.

**Hook code paths.**  Same `ShowRecordEvent` + `_arm_show_record_event`
machinery as Section 23.13 above, but the callbacks now route to:

* `_on_show_record_start` → `engine.recording_start(forward_slash_path)`
  (the LiquidsoapPlayoutEngine wrapper sends the stop+set+start triple).
* `_on_show_record_end` → `engine.recording_stop()` (synchronous,
  no post-roll Timer needed because the bus-tap has no HTTP-buffering
  lag).

No lifecycle thread, no watchdog respawn, no retry-on-404, no
post-roll Timer.

**Filename construction unchanged.**  `build_output_path` was moved
from `engine.ffmpeg_recorder` to the new `libretime_playout/
recording_path.py` module; the format is still
`<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3` with
the same Windows-illegal-character sanitization.


### 23.14 Continuous Output Stream (Future Work, deferred)

**Status:** Open / not implemented.  Documented here so the
constraint is not lost between Phase B and whichever future feature
picks it up.

**Observation (2026-05-17, surfaced by Record-per-Show testing):**
Every source switch in the current playout architecture rebuilds
the entire output pipeline from scratch:

1. `mpv` is told to stop the current input URI.
2. The three FFmpeg streamers feeding the three Icecast mountpoints
   (`/rastatime` MP3-320, `/rastatime-aac` AAC-320, `/rastatime-ogg`
   Opus-128) are signaled with `q`, terminate, and exit (PIDs
   disappear).
3. The new source is set up — a track file path, a webstream URI, or
   a Line-In capture via `FfmpegLineinCapture` to
   `/linein-capture`.
4. `mpv` is told to play the new URI.
5. Three new FFmpeg streamer subprocesses are spawned and connect to
   Icecast (new PIDs).

Total wall-clock gap on `/rastatime` between step 2 and the first
streamer becoming ready in step 5: **~2 s for file→webstream, ~3-4
s for any transition involving Line-In** (because Line-In also
needs to spawn its own dshow capture process between steps 3 and 4).
During this gap Icecast reports zero source for the mountpoint;
every connected listener (web player, mobile app, third-party
re-streamer) sees the stream end and has to reconnect.  Recording
clients are affected the same way — fixed in the recorder side by
adding `-reconnect_at_eof 1` and `-reconnect_on_network_error 1`,
but the public-listener side has no equivalent recourse.

This is **not** a regression caused by Record-per-Show; it has been
true since the VLC/mpv playout engine replaced Liquidsoap in
Phase 2 (ADR-002, Section 19.1).  Record-per-Show only made it
visible in operator testing because the recording-side EOF caused
empty MP3 files, which forced us to look.

**Operator-stated goal:** the public-facing output stream should
behave like a real radio station — **always on**.  Listeners stay
connected 24/7; whether a show is currently scheduled is irrelevant
to whether the stream is up.  Between shows the stream carries
silence (or eventually a station ident loop / news / etc.).  This
is also how upstream LibreTime's Liquidsoap mountpoint behaved.

**Candidate approaches** (none of them implemented yet — to be
re-evaluated when this feature is scheduled):

1. **Continuous streamers + silence source.**  The three FFmpeg
   streamer subprocesses are spawned once at playout startup and
   kept running for the lifetime of the service.  Their input is a
   permanent audio pipeline (either an FFmpeg `anullsrc` silence
   generator that mpv's actual playback is mixed into, or a
   named-pipe / Windows FIFO that mpv writes to and the streamers
   read from).  Source switches only re-target the mpv side;
   streamers never restart, Icecast source never drops, listeners
   never reconnect.  Off-air-meta ("RASTATIME back on air soon")
   keeps working — it's already a separate cc_pref string.
   - Pro: cleanest solution; matches upstream Liquidsoap behaviour;
     also fixes the recorder gap, so the
     `-reconnect_at_eof` / `-reconnect_on_network_error` workaround
     becomes redundant.
   - Con: largest implementation surface; touches mpv-Engine
     wiring, all three FfmpegStreamer instances, source_switcher,
     and the schedule-event loop.  Requires careful Windows
     named-pipe handling (or an in-process audio bus).
   - Estimated effort: 3-5 days, comparable to one Phase B
     stabilisation item.

2. **Silence-filler at transitions only.**  Streamers still restart
   on every source switch, but between the old mpv source ending
   and the new mpv source becoming ready, a short silence buffer
   (~5 s) is pushed to the streamers so Icecast never sees source
   loss.  Smaller change, but the source-switch logic gets
   complicated and the streamer-restart cost is still paid.
   - Pro: focused fix; the Icecast `<burst-on-connect>` machinery
     does most of the smoothing for free if combined with a
     larger `<burst-size>`.
   - Con: leaves the source-switch architecturally fragile; doesn't
     help if the streamer itself ever crashes during a show.

3. **Permanent streamer reading from a Windows named-pipe.**  A
   subset of (1): no silence generator, no audio mixer, just a
   single permanent OS-level pipe between mpv and the three
   streamers, with mpv writing whatever audio it has (silence
   between shows is just mpv playing a generated silence URI).
   - Pro: smaller than (1).
   - Con: Windows named-pipe handling from FFmpeg subprocesses is
     fiddly (we'd need either the `\\\\.\\pipe\\<name>` syntax on
     stdin or `pipe:0` redirection); needs spike before commitment.

**Recommendation, when the time comes:** option (1).  The 24/7
output-stream semantics aligns with operator expectations and with
how every other broadcast station behaves; the recorder workaround
becomes redundant; and the source-switch logic becomes simpler
(only mpv is restarted, not the whole pipeline).  Until then,
listeners will continue to see a 2-4 s reconnect on every source
boundary, and the recorder will continue to need its reconnect
flags.

**Decision recorded 2026-05-17:** deferred.  Operator wants Phase B
/ Feature #8 (Record-per-Show) closed out first; the continuous-
stream rework gets its own feature ticket and is scheduled separately.

### 23.15 HTTPS / Public-Internet Access (Future Work, deferred)

**Status:** Open / not implemented.  Captured here so the trade-off
matrix from the 2026-05-18 evaluation does not have to be redone
when this feature is scheduled.

**Today's topology (LAN-only):**

| Component | Listens on | Notes |
|---|---|---|
| Apache 2.4 + PHP (mod_fcgid) | `http://192.168.1.192/` | the operator UI |
| Backend API (Django/Uvicorn) | `http://127.0.0.1:8765` | localhost only |
| Playout HTTP listener | `http://127.0.0.1:8770` | localhost only |
| Icecast | `http://localhost:8000/<mount>` | public streams + admin |
| `libretime.conf` → `general.public_url` | `http://192.168.1.192` | interpolated into RSS feeds, episode download URLs, image URLs, etc. |

Everything is plain HTTP, no certificate management, no
auth-hardening assumptions beyond "trusted LAN."

**Operator goal (2026-05-18):** be able to use RASTATIME's web UI
from the public Internet, ideally over HTTPS.  This pulls in three
unrelated concerns at once:

1. **Network reachability** — get traffic from the Internet to the
   Windows host (NAT/CGNAT, dynamic IP, port forwarding, …).
2. **TLS termination + certificate lifecycle** — Let's Encrypt or
   equivalent, automatic renewal.
3. **RASTATIME-internal adjustments** — see below; not optional in
   any of the three approaches.

#### Three architecture options (compared)

##### Option A — Direct Apache HTTPS + Router port-forwarding

Apache binds 443 in addition to 80, router forwards 80/443 from the
public IP to the Windows host, [`win-acme`](https://www.win-acme.com/)
fetches and rotates the certificate via Let's Encrypt's ACME HTTP-01
challenge.

- **Pros:** full control, no third party, cost = domain registration
  only.
- **Cons:** entire RASTATIME stack directly exposed; requires static
  IP or DynDNS; router port-forward must stay in sync with ACME
  renewals; Icecast on port 8000 needs its own HTTPS story
  separately.

##### Option B — Cloudflare Tunnel  *(recommended)*

`cloudflared` daemon runs on the Windows host (NSSM-friendly) and
establishes an outbound TLS tunnel to Cloudflare's edge.  Public DNS
points `radio.example.com` at Cloudflare; Cloudflare terminates TLS
and forwards plain HTTP through the tunnel to the local Apache.

- **Pros:** no port-forward (works through NAT/CGNAT), Cloudflare's
  WAF/rate-limiting in front of RASTATIME's auth layer, certificate
  fully managed off-host, free tier sufficient for small stations,
  optional Cloudflare Access for email-OTP / SSO as a second login
  gate without writing code.
- **Cons:** Cloudflare dependency; audio-stream egress bandwidth
  counts against the free tier (generous but bounded); ~30-80 ms
  added latency on the operator UI; live-stream egress at scale may
  need a separate path.

##### Option C — External VPS reverse proxy (Caddy/Nginx)

A small Linux VPS (Hetzner CX11-class, ~5 €/month) runs Caddy or
Nginx with Let's Encrypt auto-cert.  A Wireguard or SSH reverse
tunnel from the Windows host carries traffic from the VPS back to
the local Apache.

- **Pros:** no Cloudflare dependency; Caddy's automatic
  HTTPS-by-default is famously low-friction; VPS can also cache /
  fan-out the public Icecast streams.
- **Cons:** ~60 €/year recurring; one more host to keep patched;
  tunnel reliability needs monitoring.

#### RASTATIME-side adjustments (apply to all three options)

Independent of the tunneling choice, the following internal changes
are required.  None of them are optional — without them the
HTTPS-from-outside experience is broken in subtle ways:

| Concern | Change | Effort |
|---|---|---|
| **`libretime.conf` → `public_url`** | Switch from `http://192.168.1.192` to `https://radio.example.com`.  Interpolated into RSS feed self-links, podcast-episode `download_url`, station-image URLs, and a handful of UI-side absolute links. | 5 min + full service restart |
| **Mixed-Content for Icecast streams** | The HTTPS frontend cannot embed `http://localhost:8000/<mount>` audio — browsers block it.  Solve by either (a) Icecast 2.4 native TLS (fiddly on Windows), (b) Apache reverse-proxy `https://radio.example.com/stream/<mount>` → `http://localhost:8000/<mount>` (cleanest), or (c) let Cloudflare/Caddy proxy the streams. | 2-6 h — biggest single chunk |
| **Cookie / session domain** | Currently IP-scoped; Zend usually handles this automatically once `public_url` changes, but verify. | 30 min |
| **API-key + login hardening** | Replace the placeholder `rastatime-api-key-change-before-production` in `libretime.conf`; verify the `login_attempts` table's brute-force throttle is wired in; consider 2FA (not currently implemented). | 1-2 h |
| **BUTT / DJ source auth** | DJ passwords were chosen for LAN use; rotate to long random values before exposing. | configuration, no code |
| **CORS / CSRF** | If streams end up on a different subdomain than the UI, CORS headers must be set in Apache (or Cloudflare/Caddy). | 1 h if needed |

#### Effort + cost matrix

| Option | Setup time | Recurring (€/yr) | Operational complexity |
|---|---|---|---|
| **A** Apache HTTPS direct | 1-2 days | ~10 (domain) | medium — router NAT + ACME renewal both need to keep working |
| **B** Cloudflare Tunnel ⭐ | 4-8 h | ~10 (domain), CF free tier | low — `cloudflared` runs as NSSM service like the others |
| **C** External VPS + Caddy | 4-8 h | ~70 (domain + VPS) | medium — separate host to keep patched |

Plus, for any option, the ~2-6 h to solve Mixed-Content on the
Icecast streams.

#### Security considerations

Exposing a CMS-style application to the public Internet shifts the
threat surface considerably:

* LibreTime has had CVEs historically; staying on LAN-only meant
  these never mattered.  Going public means each one must be
  evaluated.
* The Library upload path becomes a possible malware-upload vector
  if an attacker gets a valid login.  Today only the operator has a
  login, so blast radius is bounded — but credentials must be
  strong.
* Icecast admin (port 8000 `/admin/`) MUST NOT be public.  Whatever
  proxy/tunnel layer is chosen has to expose only the chosen mount
  paths, never the admin URL.
* The placeholder `api_key` in `libretime.conf` MUST be regenerated
  before any external exposure.

#### Recommendation

**Option B (Cloudflare Tunnel)** is the recommended starting point
for RASTATIME because:

* No router/NAT changes — works on residential connections with
  CGNAT.
* `cloudflared` slots into the existing NSSM-service pattern.
* Certificate lifecycle is entirely off-host.
* Cloudflare's free tier (WAF, basic rate-limiting, Tunnel) covers
  small-station traffic.
* Optional Cloudflare Access provides MFA without writing any code.

If the streams ever outgrow Cloudflare's free-tier egress, Option C
becomes attractive as a stream-fanout layer while keeping the UI
behind Cloudflare.

#### Open questions to resolve before implementation

1. Domain name registrar + DNS provider (Cloudflare itself is fine).
2. Expected concurrent external listener count (drives Option B vs.
   B+C hybrid).
3. Whether the operator wants Cloudflare Access (email-OTP / SSO
   in front of the RASTATIME login) or just the built-in login.
4. Whether DJ-source ingest (BUTT / show / master mounts) is part
   of the "external" scope or stays LAN-only.

**Decision recorded 2026-05-18:** deferred.  Operator wants to keep
RASTATIME LAN-only for now; will revisit once feature stabilisation
work has concluded.

### 23.16 Show Templates

**Status:** Shipped (migration 0053, frontend + backend
2026-05-19).

**Operator goal.**  Reuse the configuration of a typical show — a
DJ slot, a music hour, a news segment, a podcast slot — across
many calendar entries without re-entering the same dozen fields
each time.

**Data model (one new table).**

```sql
CREATE TABLE cc_show_template (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(255) NOT NULL UNIQUE,
    template_data  JSONB NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);
```

`template_data` is a JSON dictionary keyed by show-form field
names (`add_show_name`, `add_show_genre`, `add_show_duration`,
`add_show_record`, `add_show_autoplaylist_id`, `cb_airtime_auth`,
…) — a deliberate near-1:1 mapping to the existing show-form
payload so apply-time logic stays trivial.

**Fields captured / not captured.**

Captured (operator-confirmed list, 2026-05-19):
* What:  name, url, genre, description
* When:  duration, repeats, linked, repeat_type, monthly_repeat_type,
         day_check[], end_date, no_end
         (start_date and start_time are deliberately NOT captured —
         they're per-use and inherited from the calendar click that
         opened the New-Show dialog)
* Record:  record flag
* Autoloading Playlist:  has_autoplaylist, autoplaylist_id,
         autoplaylist_repeat, intro_playlist_id, outro_playlist_id
* Live Stream Input:  cb_airtime_auth, cb_custom_auth,
         custom_username
* Who:   list of host LOGIN strings (NOT cc_subjs.id)
* Style: background colour, text colour, show-logo PATH reference

Explicitly **not** captured:
* `custom_password` — security; a template stored anywhere visible
  must not leak the DJ password
* per-instance description — the per-show description is for the
  template itself
* `add_show_start_date`, `add_show_start_time` — see above
* `add_show_id`, `add_show_instance_id` — only meaningful for an
  existing show

**Design decisions (operator-confirmed 2026-05-19).**

1. **One-way stamp model.**  A template is a blueprint, not a
   parent.  Editing a template later does NOT affect any show
   that was previously created from it.  The alternative
   (live binding with a `cc_show.template_id` FK and propagation
   on template-save) was rejected as too surprising — it would
   silently mutate scheduled shows including their recordings.
2. **Station-wide scope.**  No `created_by` column; any
   admin / program-manager can apply and edit any template.  A
   per-user scoping could be added later without a schema break
   (just a nullable `subjs_id` column + UI filter).
3. **UI in New-Show and Edit-Show flows; suppressed in
   Edit-Instance** (revised 2026-05-19 after the operator asked
   to re-stamp existing shows from a template, then noticed the
   controls also appearing in the Edit-Instance variant).  The
   shared `schedule/add-show-form.phtml` partial gates the
   template block on `$this->action !== 'edit-repeating-show-instance'`,
   so the controls render in New Show, Edit Show, but NOT in Edit
   Instance.  Rationale: a single repeating-show instance is a
   per-occurrence override; applying a template to one occurrence
   would either silently propagate to the linked siblings (which
   violates the one-way stamp model) or have no effect on them
   (which would mislead the operator).  Operators who want
   template-driven changes to a series should use the Edit Show
   path on the master, which acts on all linked instances.
   In Edit-Show, Apply writes every captured field onto the
   in-flight form values but does NOT auto-submit — the operator
   still has to click "Update show" to persist.  `start_date` /
   `start_time` are skipped per the one-way-stamp rule (a template
   must never silently reschedule an existing show).
   Save-as-Template from an Edit-Show form is also enabled and
   behaves identically to the New-Show flow (the show name becomes
   the template name, with overwrite-confirm).
4. **Schema drift.**  When new columns are added to `cc_show`
   later, existing templates will simply not have those keys in
   their JSON.  `applyShowTemplate` only writes keys that exist
   in the template; missing keys fall back to the show-form's
   default value.  Templates with stale keys (e.g. a column we
   later remove) silently ignore the extra keys.  Operator
   accepted this "defaults win" behaviour over a stricter
   "templates must be refreshed after schema changes" model.
5. **Hosts stored as logins, not IDs.**  Surrogate IDs are
   meaningless if the user is later deleted + recreated, and
   `cc_subjs.login` is unique and human-meaningful.  Apply-time
   missing logins are silently skipped with a `Logging::info`.
6. **Show logo as a path reference, not a copy.**  When the
   referenced image is deleted, the template loses its logo; the
   alternative (copying the image into a templates/ folder) was
   rejected to avoid duplicate storage.

**Component map.**

| Layer     | Files                                                  |
|-----------|--------------------------------------------------------|
| Schema    | `backend/api/libretime_api/legacy/migrations/0053_add_show_template.py` |
| Service   | `frontend/legacy/application/services/ShowTemplateService.php` |
| Controller | `ScheduleController` — 5 new JSON actions: list / get / save / rename / delete |
| Settings UI | `PreferenceController::showTemplatesAction` + `views/scripts/preference/show-templates.phtml` |
| Show-Dialog UI | `views/scripts/schedule/add-show-form.phtml` (controls), `public/js/airtime/schedule/add-show.js` (`setupShowTemplateControls` + `applyShowTemplate`) |
| Navigation | `application/configs/navigation.php` (Settings → "Show Templates") |

**Apply-time UI sync (lessons learned, 2026-05-19).**

The first iteration of `applyShowTemplate()` re-used the existing
checkbox-click handlers to trigger the dependent UI toggles
(Repeats? → fieldset visibility, Record? → Rebroadcast checkbox
visibility, …) by doing
`$el.prop("checked", on).trigger("click").trigger("change")`.
This appeared to work for trivial cases but produced two bugs in
combination with jQuery 1.8.3's *default-action simulation* for
click events on form controls:

1. **Repeats inverted.**  jQuery's `.trigger("click")` runs the
   user handlers first, then simulates the browser default action
   for the event type.  On a checkbox, that means *toggling the
   native checked state* — so the sequence was: write the value,
   run the toggle handler (visibility flips correctly), then the
   default-action flipped the checkbox back.  End state:
   checkbox un-checked, visibility "on".
2. **Linked lost after Record was set.**  Setting Linked first
   then Record triggered Record's click handler, which has a
   domain-rule branch that force-clears Linked and disables it
   (a recorded show cannot be linked — the per-instance audio is
   unique).  So a template with `record=false, linked=true` ended
   up with Linked un-checked depending on the order of setCheck
   calls.

Fix (in this section's component-map files only):
`applyShowTemplate()` now writes values (no triggers, no clicks)
and ends with a single pass through `syncDependentVisibility(form)`
that reads the post-write state and explicitly toggles every
collapsible section.  This is the same set of show/hide rules
that the New-Show form's individual click handlers contain, just
expressed as a one-shot recompute instead of a chain of toggles.
Adding a new toggle-driven section in the future means adding both
the click handler (for normal user interaction) AND a line in
`syncDependentVisibility` (for the template-apply path).

**Form-submit isolation for the template buttons.**

Apply and Save-as-Template both live inside the
`<form id="add-show-form">` wrapper from `schedule/index.phtml`.
Even with `type="button"` on the buttons themselves, a bubbling
click event into the form was occasionally enough to leave the
form in a "mid-click" state where the subsequent Add-this-Show
click was discarded.  Both handlers now explicitly call
`event.preventDefault() + event.stopPropagation() + return false`,
and the Save-as-Template payload is built from
`$("#add-show-form").serializeArray()` (specific) instead of
`$("form").serializeArray()` (which would also include any sibling
forms the page happens to host).

**Out-of-scope / possible future work.**

* Editing template_data directly in the Settings UI (currently the
  only edit path is "open a show, modify, save with same template
  name") — could be added with a JSON-editor widget if operators
  ever need to tweak a single field without re-running the New-Show
  flow.
* Importing / exporting template JSON to disk for sharing between
  installations.
* Per-user template scoping with a `created_by` nullable column.

### 23.17 Webstream Default-Length with Seconds

**Status:** Shipped (2026-05-19, `Application_Model_Webstream` only).

**Operator goal.**  Bring the Webstream edit dialog's "Default
Length" field up to the same granularity the Line-Input dialog
already had — seconds — so operators can configure short, time-
critical stream entries (news jingles, sponsor IDs, sub-minute
breakaways) without rounding up to the next whole minute.

**Before / after.**

| | Input format | DB stored | Edit readback |
|---|---|---|---|
| Pre-2026-05-19 | `01h 05m` (regex `/^(?:(\d{1,2})h)?\s*(?:(\d{1,2})m)?$/`) | `HH:MM:00` (`%H:%I` written, Postgres `interval` pads) | `01h 05m` (`%Hh %Im`) |
| Now | `01h 05m 05s` (regex extended with optional `\s*(?:(\d{1,2})s)?`) | `HH:MM:SS` (`%H:%I:%S`) | `01h 05m 05s` (`%Hh %Im %Ss`) |

The "s"-group is **fully optional** so any pre-existing input
(`01h 05m`, `05m`, `30s`, `2h`) still validates — backwards-
compatible by operator decision 2026-05-19 (Frage 1).  The
Edit-dialog readback always renders all three components,
including a zero seconds tail, for visual consistency (operator
decision 2026-05-19, Frage 2a).

**DB.**  `cc_webstream.length` is a Postgres `interval` type
(see `schema.sql`).  It already round-trips `HH:MM:SS` end-to-end
regardless of the format string the application chose to write;
pre-2026-05-19 rows written as `%H:%I` come back from the driver
as `HH:MM:00` and parse identically in `getDefaultLength()`.  No
migration needed.

**Validation rule change.**  The pre-2026-05-19 validator
rejected length=0 with the message "Length needs to be greater
than 0 minutes".  The new validator computes total seconds and
rejects only the all-zero case, with the friendlier wording
"Length needs to be greater than zero" — so `30s` is now a valid
half-minute webstream entry.

**Scheduler / playout.**  No changes.  `Scheduler.php` reads
`$stream->getDbLength()` directly (raw `HH:MM:SS` from Propel,
not the human-readable string from `getDefaultLength()`), so the
seconds precision flows through to `cc_schedule.clip_length` and
the FfmpegStreamer naturally.

**Library list cosmetic note.**  `LibraryController` runs every
object's `getLength()` through `LengthFormatter::format()`.  The
formatter parses `HH:MM:SS.x` and re-formats it for display, but
the Webstream-specific `01h 05m 05s` string does not match its
regex and is therefore passed through unchanged — so the Library
list shows the same `HHh MMm SSs` format the Edit dialog uses.
This is consistent with the pre-2026-05-19 behaviour (Webstreams
already broke from the Tracks/Blocks/Playlists convention by
showing `HHh MMm` instead of `H:MM:SS.x`).

**Decisions log (2026-05-19).**

| Question | Decision | Rationale |
|---|---|---|
| Validator backwards-compat for `01h 05m`? | Yes — `s`-group optional | Avoid breaking every existing stream on next save |
| Edit readback: always three components vs. only when seconds > 0? | Always three (`01h 05m 00s`) | Visual consistency; operator expectation matches the displayed input format |
| Refactor scope — extract shared duration parser? | No, deferred | Three independent parsers exist (Webstream, Line-In `LineinController::_parseHmsToSeconds`, Smart Block in `SmartBlockCriteria`), each with a different I/O convention (`00h 00m`, `HH:MM:SS`, `HH:MM:SS` strict).  Unifying them is its own project; out-of-scope here |

**Files touched.**

* `frontend/legacy/application/models/Webstream.php` — five hot
  spots, all annotated with `RASTATIME 2026-05-19 — Section 23.17`:
  `getDefaultLength()` (readback format), `analyzeFormData()` (regex
  + 3-group capture, normalisation, error wording), `save()`
  (`%H:%I:%S` instead of `%H:%I`).

**Out-of-scope / possible future work.**

* Unify the Webstream, Line-Input and Smart-Block duration parsers
  into a single helper that accepts both human-readable
  (`01h 05m 05s`) and clock (`HH:MM:SS`) formats.  Today each of
  the three dialogs has its own validator; consolidating would
  remove the format-inconsistency between Library entries
  (Webstream shows `01h 05m 05s`; Tracks/Blocks/Playlists show
  `1:05:05.0`) but requires touching three live consumers and is
  not justified just for the seconds-precision request.
* Add a placeholder / help-text to the Webstream "Default Length"
  input showing the accepted format examples.  The Edit-dialog
  template (`webstream/webstream.phtml`) currently has no hint;
  the new format is only discoverable via the validation error.

### 23.18 Line-In Entries in Playlists

**Status:** Shipped (migration 0054, frontend + backend
2026-05-19).

**Operator goal.**  Make Line-In sources first-class playlist
members the same way Tracks, Webstreams and Smart Blocks already
were.  Until 2026-05-19 a Line-In could only be scheduled
*directly* into a Show timeline (`cc_schedule.linein_id`, added
Phase A 2026-05-12, migration 0047).  Operators wanted to bundle
Line-In intros / mic windows / interview slots into reusable
playlists alongside their tracks and webstreams so that a "Monday
Morning Show" playlist can carry "intro music → live mic → news
webstream → music block" as one composable unit.

**Data model.**

```sql
-- Migration 0054
ALTER TABLE cc_playlistcontents
  ADD COLUMN linein_id INTEGER DEFAULT NULL;
```

No hard FK to `rastatime_linein` — the same call as 0047 for
`cc_schedule.linein_id`: Django and Propel each manage their own
migration history, and putting cross-system FK constraints in
either side leads to drop-order problems on schema reset (and
confuses Propel's reverse-engineering tools).  Referential
integrity for the new column lives at the ORM layer on the Django
side; the SQL column itself is a plain nullable INTEGER.

**Two parallel type-enums that are easy to confuse.**

| Context              | type=0 | type=1 | type=2 | type=3 |
|----------------------|--------|--------|--------|--------|
| `cc_playlistcontents`| file   | stream | block  | **linein** ← new 2026-05-19 |
| `cc_schedule`        | file   | stream | linein | — |

The Scheduler maps between them when a Playlist is expanded into
a schedule (`Scheduler.php` `type === 'playlist'` branch, around
line 296):

```
playlist  type=0  ─→  schedule  type=0   (file)
playlist  type=1  ─→  schedule  type=1   (stream)
playlist  type=2  ─→  schedule  type=0   (block expands to files)
playlist  type=3  ─→  schedule  type=2   (linein)   ← new
```

The `cc_schedule` INSERT in `Scheduler::insertAfter()` then uses
the schedule-side type to populate exactly one of `file_id`,
`stream_id`, `linein_id` — the others stay SQL `null`.  The
type-discriminator overload between the two tables is unfortunate
historical baggage (the schedule-side type was rewritten when
line-in landed in Phase A and reused the `2` slot; the playlist-
side started counting at `3`) and is worth keeping in mind for
future feature work: changing one side does NOT automatically
change the other.

**Propel skip-regen pattern.**

`cc_playlistcontents` follows the same pattern as the other
RASTATIME-added columns (`cc_schedule.linein_id`,
`cc_webstream.input_gain_db`): the Propel model classes are NOT
regenerated.  Reading goes through `Application_Common_Database::
prepareAndExecute()` (raw SQL) — already needed for the multi-
table UNION in `Playlist::getContents()` anyway.  Writing the
common columns goes through Propel (`CcPlaylistcontents->save()`),
then a single raw-SQL `UPDATE … SET linein_id = …` populates the
new column after the insert returned an id.  This keeps Propel
regen out of the change list, which has been our policy across
every RASTATIME-added column to date.

**Files touched (per layer).**

| Layer | File | What |
|---|---|---|
| Schema | `backend/api/libretime_api/legacy/migrations/0054_add_playlistcontents_linein_id.py` | ALTER TABLE ADD COLUMN |
| Model — write | `Application_Model_Playlist::buildEntry()` | new `linein` branch (raw SELECT from rastatime_linein, build $entry directly) |
| Model — write | `Application_Model_Playlist::insertPlaylistElement()` | type=3 + raw UPDATE to set linein_id after Propel save |
| Model — read | `Application_Model_Playlist::getContents()` | 4th UNION ALL arm joining rastatime_linein |
| Scheduler | `Application_Model_Scheduler` `type === 'playlist'` branch | new type==3 mapping → schedule type=2 |
| View | `application/views/scripts/playlist/update.phtml` | type==3 row renders disabled signal icon (no browser preview possible for a server-local hardware input) |

No frontend JS changes were necessary: the Library already
classified `ftype === "linein"` as `lib-stream` (same draggable
class as Webstream) and the toolbar / DnD code paths do not
filter by item type — the only blocker was the
`throw new Exception('Unknown file type')` in `buildEntry()`,
which is now handled.

**Default slot length.**  When the operator's Library record
left `rastatime_linein.length` NULL, the playlist entry defaults
to 30 minutes — same call the Scheduler's existing in-show
line-in branch makes.  The operator can override the duration by
editing the Line-In's "Default Length" in the Library before
adding it to the playlist.

**Fades.**  Line-In entries get fixed `00:00:00` fade-in/fade-out
in both `buildEntry()` and the Scheduler mapping — fades on a
live microphone input have no defined meaning (the source is
already mixed; there is no source-side ramp to apply).

**Out-of-scope / possible future work.**

* Per-entry custom slot length on the playlist row (today the
  duration is fixed to the Library default at add-time).  Would
  need a UI cue-editor for type=3 rows in `update.phtml`.
* Per-entry fade-in / fade-out for line-in entries (e.g. when
  the playout side gains a soft-cut path for live sources).
  Today fades are pinned to zero for line-in.
* Visual preview / level meter in the Library when a Line-In is
  selected — would help operators verify a device is actually
  delivering audio before they save it into a playlist.

### 23.19 Autoloading-Playlist Outro Reserve

**Status:** Shipped (2026-05-20, frontend `legacy/` only — no
schema, no API, no UI surface changed).

**Operator goal.**  When a show is configured with an Intro
Playlist + an Autoloading Playlist + an Outro Playlist, the three
should fit *inside* the show's slot in that order — Intro first,
Autoloading filling the middle, Outro at the end.  Before this
section the outro silently spilled past the show's end whenever
the autoplaylist's expansion happened to fill (or overflow) the
remaining time.

**Where the bug lived.**

`Application_Common_AutoPlaylistManager::buildAutoPlaylist()` ran
the three insertions sequentially:

1. Intro inserted at start of slot (always exactly one pass).
2. Autoloading playlist inserted in a `while`-loop — each pass
   either expands a static playlist (whose tracks have known
   lengths) or expands a smart block.  A smart block's
   "time-remaining" mode sizes itself against
   `ShowInstance::getSecondsRemaining()`, which returns
   `showDuration − currentScheduled` — i.e. the entire unfilled
   tail of the slot.
3. Outro inserted at the end as an unconditional append after the
   loop exited.

When only Intro + Auto was configured, the loop's
`getPercentScheduled() > 100` early-exit kept the slot from being
filled to the brim (the smart block's expansion clamped at the
remaining time, then the loop terminated), so no overbook was
visible.  When Outro was added, step 3 was a "best-effort
afterthought" — the upstream comment in the code even
acknowledged it: *"it will always overbook shows that have repeat
until full enabled because they will never have time remaining
for the outroplaylist to be added"*.

**The fix in four layers + one measurement step.**

1. **`AutoPlaylistManager`** measures the outro length by
   **trial-inserting** the outro immediately after the intro,
   reading the before/after delta of
   `cc_show_instances.time_filled` to capture the actual
   smart-block-expanded outro duration, then deleting the trial
   rows (`WHERE id > maxIdBefore`) and re-aggregating
   `time_filled` via the new
   `ShowInstance::refreshScheduleStatus()` helper.
   The trial-insert is necessary because
   `cc_playlist.length` reports `00:00:00` for any playlist
   that contains a smart block — Propel does not aggregate the
   smart-block contribution into the parent playlist's length
   column.  This was the source of an embarrassing v1–v3 chain
   of fixes that all relied on reading the length statically;
   see the bug-history block below.
   With the measured length in hand the auto-loop:
   * passes `outroLenSecs` as a `$reservedSecs` reserve into
     `addPlaylistToShow($pl_id, $checkPerm, $reservedSecs)`, and
   * terminates as soon as
     `$si->getSecondsRemaining() <= $outroLenSecs`
     (replaces the old `getPercentScheduled() > 100` check).

2. **`Application_Model_ShowInstance::addPlaylistToShow()`** gains
   an optional third parameter `$reservedSecs = 0` and forwards
   it to the scheduler via the new setter.  Existing callers
   (manual Library "Add to current playlist" toolbar button etc.)
   are unaffected because the default reserve is 0.

3. **`Application_Model_Scheduler`** gains
   `setReservedSeconds(int $n)` and a `private $reservedSecs = 0`
   member.  `retrieveMediaFiles()` now computes
   `$showLimit = max(0, $showInstance->getSecondsRemaining() - $this->reservedSecs)`
   before passing it to `$bl->getListOfFilesUnderLimit($showLimit)`
   for dynamic smart blocks inside playlist contents.  The
   `max(0, …)` clamp is defensive — a caller that over-reserves
   simply produces an empty smart-block expansion instead of a
   negative limit.

4. **`Application_Model_ShowInstance::trimTailToReserve(int $n)`**
   — RASTATIME 2026-05-20 v3.  Deletes `cc_schedule` rows from
   the tail of this show instance (highest-`starts` first, filter
   `starts > NOW() AT TIME ZONE 'UTC'` so already-playing or
   already-played tracks are never touched) until at least `$n`
   seconds of unscheduled tail remain.
   Called by the auto-loop *once*, immediately before the outro
   insertion.  This is the "post-trim" half of the fix: the
   pre-reserve in layer 3 covers the *fill-remaining* smart-block
   case, but two upstream paths ignore the `$showLimit` parameter
   and overbook the slot anyway —
   (a) static playlists (every track inserted at full length;
       `Scheduler::retrieveMediaFiles` foreach has no trim);
   (b) fixed-duration smart blocks (they honour their own
       `cc_block.length` limit, not `$showLimit`).
   `trimTailToReserve()` is the safety net that removes whole
   tail tracks until the outro fits.  Trade-off: a fixed-duration
   smart block whose last track does not fit gets that *whole*
   track removed (no mid-track cut), so the auto-content can be
   noticeably shorter than the configured smart-block length when
   tracks are long compared to the outro reserve.  Operators who
   want exact slot fill should use a fill-remaining smart block
   instead — the layer-3 reserve sizes that one perfectly.

**Edge case — outro length ≥ show slot.**

Operator-confirmed 2026-05-20 **v3** (revised again after the v2
test pass showed the "skip outro" semantics created a visible
38 s gap at the tail of every test slot): **the outro is always
inserted**, even when it overbooks.  Operator policy:
*Es ist besser, die Show ist überfüllt, als zu wenig befüllt*.
The edge-case branch now only zeroes the reserve (so the
autoplaylist fills the entire slot instead of bailing
immediately with `remaining ≤ outroLenSecs`), and the outro is
still inserted on top — overbooking the slot.  The overbook is
logged at `WARN` level so the operator can find the
misconfiguration in `legacy.log`.

**UI surface.**  Operator-confirmed 2026-05-20 (Q3):
**no UI hint** is rendered.  The behaviour is pure backend magic;
this section is the contract.

**Pre-2026-05-20 behaviour vs. now.**

| Configuration | Pre-2026-05-20 | After Section 23.19 |
|---|---|---|
| Intro only | OK | OK (unchanged) |
| Auto only | OK | OK (unchanged) |
| Intro + Auto (no Outro) | OK (loop stops at >100 %) | OK (loop stops at remaining ≤ 0) |
| Outro only | OK if outro ≤ slot | OK if outro ≤ slot (unchanged) |
| **Intro + Auto + Outro** | **Outro silently overbooks** | **All three fit inside slot** ✅ |
| Intro + Auto + Outro, Repeat-Until-Full | Worst case — Auto fills entire slot, Outro always overbooks | Auto terminates at `remaining ≤ outro`, Outro fits |
| Outro > slot | Outro overbooks, Auto fills slot first | **Auto fills slot, Outro inserted + overbooks + WARN logged** (operator policy: overfilled is better than underfilled) |

**Component map.**

| File | Change |
|---|---|
| `frontend/legacy/application/common/AutoPlaylistManager.php` | Trial-insert + roll-back outro length measurement (after intro), Throwable-catch fallback, edge-case skip (outro > slot), reserved-secs in loop, new termination check, `trimTailToReserve()` call before outro insert |
| `frontend/legacy/application/models/ShowInstance.php` | `addPlaylistToShow()` gains optional 3rd parameter `$reservedSecs = 0`; new `trimTailToReserve($n)` and `refreshScheduleStatus()` helpers |
| `frontend/legacy/application/models/Scheduler.php` | New `private $reservedSecs = 0`, `setReservedSeconds()` setter, `max(0, … - reservedSecs)` in `retrieveMediaFiles()` |

**Hot bug-history (2026-05-20).**

The first ship of Section 23.19 used
`new Application_Model_Playlist($outroplaylistid)->getDbLength()`
to read the outro length.  The wrapper has no `getDbLength()`
public method (the Propel call is on its internal `$this->pl`
member), so this raised a fatal `Error: Call to undefined
method` and the catch was `catch (Exception)` — which in PHP 7+
does NOT catch `Error`.  Result: every Intro+Auto+Outro show
left its entire slot empty for an hour of failed polls.  Two
small follow-ups landed the same day:
(a) read the length via `CcPlaylistQuery::findPK(...)
->getDbLength()` instead of via the wrapper, and
(b) widen the catch to `Throwable` so any future read failure
falls back to a no-reserve build instead of bricking the auto
path.  Test feedback also forced an edge-case revision (the v1
"outro > slot → keep outro, skip auto" decision was the wrong
way round; the operator wanted auto > outro priority — see
table above) and the addition of layer 4 (post-trim) for the
static-playlist / fixed-duration smart-block cases the
in-Scheduler reserve cannot cover.

A fourth hot-fix the same day swapped the safety filter on the
layer-4 tail-trim helper from `playout_status = 0` (which means
"overbooked", set by `updateScheduleStatus()` *after* the auto-
loop's inserts — in-slot future tracks have `playout_status = 1`,
not 0) to `starts > NOW() AT TIME ZONE 'UTC'`.  The original
filter matched zero rows in every realistic test, so the trim
helper silently did nothing and the outro continued to land
out-of-slot.  Lesson learned for future Postgres time-window
deletes: prefer a timestamp-based filter ("don't touch the
past") to a status-enum filter ("don't touch already-played")
unless we genuinely need the enum semantics — the enum is set
by code paths we do not control and means something different
than the safety goal.

A fifth hot-fix the same day (v4) replaced the static
`cc_playlist.length` read with a **trial-insert + roll-back**
measurement of the outro.  Empirical test on the operator's
8 "Tagesplaylist <Genre> Outro" playlists showed all 8 had
`cc_playlist.length = 0:00:00` because each carried one smart
block, and Propel does not aggregate smart-block contributions
into the parent playlist's length column.  With length=0 the
reserve was 0 and the layer-4 trim — even with the corrected
filter — was a no-op, so the outro continued to overbook the
slot.  The trial-insert approach captures the actual smart-
block-expanded outro length (modulo dynamic-block track-set
variance between the trial and final inserts, which is bounded
by the smart block's own length limit).  Lesson learned:
**any code that reads a length out of `cc_playlist` /
`cc_block` should expect 0 / NULL for smart-block-containing
rows and have a fallback path** — Propel's length aggregation
is not transitive across the playlist/smart-block boundary.

An eighth hot-fix (v6) added a defensive 5-second safety
margin on top of the measured outro length when computing the
reserve.  Operator testing on the "Time remaining in show"
autoplaylist smart-block variant showed a consistent 4 s
overbook: the SSP best-fit picker maximises subset sum ≤
target, but the Scheduler's later crossfade pass shifts the
real schedule timestamps by a few hundred ms per transition,
and those shifts do not line up exactly with what the SSP saw.
The margin sacrifices at most ~5 s of slot fill but eliminates
the overbook on the "Time remaining" path.  It does not affect
fixed-time-limit smart blocks (e.g. "Limit to: 9 minutes"):
those blocks ignore the reserve and run against their own
limit, so a 9 min autoplaylist in a 10 min slot will always
have ~60 s of unscheduled tail — by design, not a bug.

A ninth hot-fix (v7) briefly bumped the margin to 10 s after
the Auto+Outro variant still showed a 4 s overbook on a
smart-block outro (where the trial pass and the real pass
pick different tracks).  The operator immediately reverted
that policy: max-5 s margin is non-negotiable (any "silence"
tail audible to listeners must stay small).

A tenth hot-fix (v8) kept the margin at 5 s and instead added
a **post-outro cleanup pass**: snapshot `MAX(cc_schedule.id)`
before the real outro insert, then after the insert call
`ShowInstance::trimTailExcept($snapshot, 0)` — a variant of
`trimTailToReserve()` that filters by `id <= $snapshot` so it
only ever trims autoplaylist tail rows (never the just-
inserted outro rows).  The cleanup is **skipped** in the
"outro > slot" edge case because that branch deliberately
overbooks (operator policy: oversized outro is a config
choice, not a bug to fix).  Worst case after v8: an
unusually large trial-vs-real divergence on a smart-block
outro produces an autoplaylist that is a few tracks shorter
than ideal — but the show never overbooks.

A sixth and seventh hot-fix landed together the same day (v5):
**`cc_files.is_scheduled` cleanup after the trial insert**, and
**edge-case revision: always insert the outro** even when it
overbooks.  The trial-insert in v4 went through
`Scheduler::insertAfter()`, which flips
`cc_files.is_scheduled = TRUE` for every file it adds.  The
roll-back DELETE on `cc_schedule` did NOT touch the
`cc_files` flag, so the outro pool ended up marked
"already scheduled" — autoplaylist smart blocks that read the
flag later were picking from a poisoned pool and the
autoplaylist effectively shrank.  v5 snapshots the TRUE-set
before the trial, then on roll-back resets the flag for any
row that is TRUE but not in the snapshot, before deleting the
trial schedule rows.  Order matters: drop the flag first so a
concurrent reader never sees `is_scheduled = TRUE` without a
backing `cc_schedule` row.  The same release reverted the
"skip outro when outro > slot" edge-case behaviour to "always
insert the outro" (operator policy 2026-05-20:
*Es ist besser, die Show ist überfüllt, als zu wenig
befüllt*).  Lesson learned for future Scheduler callers that
roll their own roll-back: **the
`Scheduler::insertAfter()` → `BasePeer::doUpdate(is_scheduled)`
side effect is implicit and easy to miss**; any caller that
deletes schedule rows it just inserted must also reset the
`cc_files.is_scheduled` flag, or smart-block selection
downstream will silently misbehave.

**Why not change `getSecondsRemaining()` itself?**

That would have been simpler, but `getSecondsRemaining()` is read
by lots of other code paths (the Show Builder UI overlap warning,
the dashboard "minutes remaining" display, the trim-overbooked
helper, …) and quietly subtracting a reserve from all of them
would be a much larger surface change.  Passing the reserve only
through the one Scheduler call that needs it keeps the blast
radius small and lets `getSecondsRemaining()` keep its existing
"unscheduled tail in seconds" contract.

**Two "by-design" behaviours that look like bugs but are not.**

1. **Deterministic Smart-Block track selection at fixed time
   limits.**  `Block::getListOfFilesUnderLimit()` runs through
   `SSPSolution::solve($tracks, $target)` (Block.php
   l. 1942–1992) when the smart block uses a time-based
   limit + random sort + `overflow_tracks = 0`.  The solver
   shuffles the track list 50 times and runs a greedy fill +
   local improvement against each shuffle, then returns the
   subset whose summed length is closest to (but ≤) the target.
   With a pool that has one near-optimal 2-track subset
   (e.g. *Dogs* 4:22 + *Roxanne* 4:30 ≈ 9 min target), the
   solver lands on it on essentially every run regardless of
   the shuffle.  Operators who want more variety should pick
   "Time remaining in show" instead of a fixed minutes limit —
   the time-remaining path takes whatever shuffle the SSP
   produces in the trial that filled the largest fraction of
   the slot, which has more degrees of freedom.

2. **Fixed-time-limit autoplaylist leaves a tail gap.**  A
   smart block configured "Limit to: 9 minutes" produces ~9 min
   of content regardless of the show's slot length — that's
   the operator's stated cap, not a bug.  In a 10 min slot
   this leaves ~60 s of unscheduled tail (~9 min content +
   outro + safety reserve = ~9 min 40 s, then a ~20–60 s gap
   to slot end).  If the operator wants a fully filled slot,
   the autoplaylist's smart block must use
   "Limit to: Time remaining in show" instead.  The reserve
   mechanism (layer 3) keeps that variant safe inside the
   slot; the fixed-limit variant is intentionally bounded by
   its own limit.

**Out-of-scope / possible future work.**

* Same reserve mechanism for the **Intro** playlist when the
  autoplaylist insertion happens before the intro for some
  reason.  Today the order is hard-coded Intro → Auto → Outro,
  so this would only matter for a future "Outro before Intro"
  configuration that nobody has asked for.
* A "weaken SSP determinism" mode that adds randomness to the
  best-fit picker so the same track combination is not picked
  on every run when the optimal subset is unique.  Today the
  operator can work around this by switching to
  "Time remaining" limit.  A future option could pick from the
  top-N best fits rather than the strictly best.
* A "best-effort outro shortening" mode that automatically trims
  the outro to fit when the configured outro is longer than the
  remaining tail after Auto.  Today the over-long outro is
  skipped entirely (Section 23.19 v2 edge case) and the operator
  gets a `WARN` log line; auto-trimming would silently mutate
  operator content and is therefore deliberately *not*
  implemented.
* Per-show override of the reserve granularity (e.g. "leave at
  least 30 s gap before outro for clean transitions") — would be
  one more `cc_show` column; not requested.

### 23.20 Auto DJ

**Status:** Shipped (2026-05-21, frontend `legacy/` only — no
schema, no API, no playout-side change).

**Operator goal.**  Eliminate two manual chores: (a) filling
calendar gaps between operator-scheduled shows, and (b) topping
up shows that the autoplaylist build left incomplete.  Both run
automatically on the same 60 s poll the existing
`AutoPlaylistManager` already uses, so the operator's only
touch-point is the new Settings → Auto DJ page.

**Operator decisions (2026-05-21, Q1–Q7).**

| Question | Decision |
|---|---|
| **Q1** Gap-search window | next 1 h only (same window AutoPlaylistManager uses for autoplaylist builds) |
| **Q2** Max length of an auto-created show | 12 h (single show per gap; if a gap is larger only the first 12 h are filled) |
| **Q3** Show owner | first admin (`Application_Model_User::getFirstAdmin()`) — the auto-create code path runs in a `Zend_Auth` admin-context swap so the existing ShowService permission check passes regardless of who originally triggered the poll |
| **Q4** Auto-created show name | the configured `auto_dj_show_name` verbatim, no timestamp suffix |
| **Q5** Fill-pass insertion point | end of existing schedule (uses the standard `ShowInstance::addPlaylistToShow()` "after-last" path) |
| **Q6** Templates | not used — only the 5 settings fields; `record = false` is hardcoded for auto-created shows so the operator can never accidentally fill the disk with auto-DJ recordings |
| **Q7** Minimum gap | 60 s — gaps shorter than that are left alone (typical "show-to-show breathing room" should not get a 30 s pseudo-show) |

**Data model.**

No schema change.  Ten new `cc_pref` keys (five from v1 plus
five additional show-detail defaults from v2):

| Key | Type | Default | Meaning |
|---|---|---|---|
| `auto_dj_enabled` | bool-as-string | `false` | master on/off |
| `auto_dj_show_name` | string | `"Auto DJ"` | name for auto-created shows |
| `auto_dj_playlist_id` | int | NULL | filler playlist (cc_playlist.id) |
| `auto_dj_fill_any_show` | bool-as-string | `false` | enables runFillPass() |
| `auto_dj_logo_path` | string | empty | absolute path to default logo |
| `auto_dj_show_url` | string | empty | default URL pre-stamped on each auto-created show |
| `auto_dj_show_genre` | string | empty | default genre |
| `auto_dj_show_description` | string | empty | default description |
| `auto_dj_show_bg_color` | string (6-hex) | empty | default background colour (no leading `#`) |
| `auto_dj_show_text_color` | string (6-hex) | empty | default text colour (no leading `#`) |

Helpers in `Application_Model_Preference` follow the existing
`Get*` / `Set*` pair pattern.

**Service-layer architecture.**

```
AutoPlaylistManager::buildAutoPlaylist()
├── AutoDjService::runPrePass()           ← Section 23.20, pre-hook
│   ├── findNextGap(now, now+1h, ≥60 s)
│   └── createGapFillingShow(gap, playlist_id)
│       └── withAdminContext(
│             ShowService::addUpdateShow(showData)
│           )
├── [existing per-show autoplaylist build loop — Section 23.19]
└── AutoDjService::runFillPass()          ← Section 23.20, post-hook
    └── for each upcoming-1h instance with tail > 5 s:
        ShowInstance::addPlaylistToShow(playlist_id, checkPerm=false, reserve=0)
```

Both passes are no-ops unless `auto_dj_enabled = true` *and*
`auto_dj_playlist_id` is set.  `runFillPass()` further requires
`auto_dj_fill_any_show = true`.  Each pass is wrapped in
`try { … } catch (Throwable)` in the AutoPlaylistManager caller
so a crash in either Auto-DJ branch can never block the
normal autoplaylist build for other shows.

**Why ShowService instead of direct Propel writes?**

Programmatic show creation needs to touch `cc_show`,
`cc_show_days`, `cc_show_hosts`, `cc_show_rebroadcast` and
`cc_show_instances` in a single transaction; the
existing `ShowService::addUpdateShow()` already orchestrates
that correctly (including timezone conversion, the
`storeInstanceIds`/`delegateInstanceCreation` sequence, and the
RabbitMQ schedule-push).  Re-implementing that in
`AutoDjService` would have duplicated several hundred lines
of validation and edge-case handling.  The only friction is
the `if (!$currentUser->isAdminOrPM()) throw …` guard at
the top of `addUpdateShow()`, which we side-step with a
small `withAdminContext()` helper.

**v1 → v2 → v3 — three attempts at the show-create path.**

v1 used `ShowService::addUpdateShow()` and wrote the admin
identity straight into the current session adapter
(`Zend_Auth::getInstance()->getStorage()->write($info)`).
The polling-job context (`PageLayoutInitPlugin`) had read the
session but had not opened it for writing, and Zend's strict-
mode session guard threw on every write attempt:
*"You must explicitly start the session with Zend_Session::start()
when session options are set to strict."*  Every poll logged a
`WARN`; gap-filling shows were never created.

v2 kept the ShowService approach but swapped the *auth-storage
adapter itself* for a `Zend_Auth_Storage_NonPersistent`
(in-memory only) and restored the original adapter via
`try { … } finally { … }`.  Fixed the explicit session-write
in the identity swap.  Did NOT fix the symptom: ShowService
internally calls `UserService::__construct` (which reads
auth-storage — still OK with NonPersistent), `RabbitMq::PushSchedule`
and intro/outro lookup helpers — at least one of those touches
`Zend_Session_Namespace` and the strict-mode guard fires again.
The poll continued to log the same WARN; no shows created.

v3 abandons the ShowService dependency entirely and writes the
three required rows (`cc_show` + `cc_show_days` +
`cc_show_instances`) via Propel setters in a single transaction.
These are the only rows AutoPlaylistManager's
`_upcomingAutoPlaylistShows()` query and the calendar
event-feed need to find the show — no hosts, no rebroadcasts,
no linked-show machinery, no RabbitMQ publish, no
intro/outro override lookups.  Auto-DJ shows are intentionally
bare filler, so the simpler path is also semantically the
right one.  `withAdminContext()` deleted; no auth-storage
manipulation needed because the direct Propel path never
queries the current user.  Pattern worth remembering: for any
"background job that needs to create an admin-only resource"
case in this codebase, prefer the direct Propel path over an
auth-context swap — the session-strict-mode guard fires at
multiple unexpected internal call sites of the Service
classes.

**Gap detection (`findNextGap`).**

Single SQL query against `cc_show_instances` for the lookahead
window, ordered by `starts`.  A cursor walks the instances
front-to-back; the first gap between the cursor and the next
instance's `starts` that is ≥ `MIN_GAP_SECS` (60 s) is
returned.  A "tail gap" between the last instance's `ends`
and the lookahead end is considered if no inter-show gap
was found.  Only one gap is returned per call — the operator-
defined "one new show per poll" rule (Q1).  No locking is
needed: the next poll naturally picks up the next gap after
the just-inserted show has materialised in
`cc_show_instances`.

**Show creation data (`createGapFillingShow`).**

```
add_show_name             ← Preference::GetAutoDjShowName()
add_show_has_autoplaylist ← 1
add_show_autoplaylist_id  ← Preference::GetAutoDjPlaylistId()
add_show_autoplaylist_repeat ← 1   (so the build loop fills the slot)
add_show_record           ← 0      (Q6 — hardcoded off)
add_show_repeats          ← 0      (non-repeating, single occurrence)
add_show_linked           ← 0
add_show_start_date       ← gap['starts']->format('Y-m-d')   (UTC)
add_show_start_time       ← gap['starts']->format('H:i')      (UTC)
add_show_duration         ← min(gap_secs, 12h) → "HH:MM"
add_show_timezone         ← 'UTC'
add_show_intro_playlist_id ← 0  (use the global default)
add_show_outro_playlist_id ← 0  (use the global default)
```

The logo path (if configured) is written directly to
`cc_show.image_path` after `addUpdateShow()` returns the new
show id, because the standard show-image upload flow is a
second AJAX request from the operator's browser — not
available in the polling-job context.

**Fill-pass scope.**

SQL:
```sql
SELECT si.id FROM cc_show_instances si
WHERE si.starts > NOW()
  AND si.starts < NOW() + INTERVAL '1 hour'
  AND si.modified_instance = FALSE
  AND EXTRACT(EPOCH FROM (si.ends - si.starts) - COALESCE(si.time_filled, INTERVAL '0')) > 5
```

For each match: `addPlaylistToShow($playlist_id, false, 0)`.
`checkUserPerm = false` because we're in a polling-job
context; `reservedSecs = 0` because the fill-pass runs *after*
any outro the show has, so no extra reserve is needed.

**Settings UI.**

`PreferenceController::autoDjAction` renders `preference/auto-dj.phtml`,
which is a single `<form>` POST-back-to-self plus two
sibling AJAX endpoints for the logo:

* `Preference/auto-dj-upload-logo` (multipart POST, replaces the
  current logo and writes the resulting path to
  `cc_pref.auto_dj_logo_path`)
* `Preference/auto-dj-remove-logo` (one-line: clears the cc_pref
  entry; the file on disk is left in place so a re-upload of
  the same filename doesn't collide)

**Component map.**

| Layer | File | Purpose |
|---|---|---|
| Preferences | `application/models/Preference.php` (5 new getter/setter pairs) | cc_pref-backed Auto-DJ settings |
| Service | `application/services/AutoDjService.php` (NEW) | runPrePass / runFillPass / findNextGap / createGapFillingShow / withAdminContext |
| Hook | `application/common/AutoPlaylistManager.php` | calls pre-pass before + fill-pass after the per-show build loop |
| Controller | `application/controllers/PreferenceController.php` (3 new actions) | autoDjAction + autoDjUploadLogoAction + autoDjRemoveLogoAction |
| View | `application/views/scripts/preference/auto-dj.phtml` (NEW) | settings form + inline JS for the logo upload AJAX |
| Navigation | `application/configs/navigation.php` | new "Auto DJ" entry under Settings |

**Edge cases and lessons learned.**

1. **Polling races.**  Two PageLayoutInitPlugin polls cannot
   land within `AUTOPLAYLIST_POLL_INTERVAL_SECONDS` of each
   other (`hasAutoPlaylistPollIntervalPassed()` guards that
   for the whole autoplaylist build, including our hooks).
   So no separate Auto-DJ lock is needed; the existing
   `auto_playlist_poll_lock` covers us.

2. **Empty admin database.**  If the system somehow has no
   admin user (e.g. fresh install with only DJ-type users),
   `getFirstAdmin()` returns NULL and `withAdminContext()`
   throws.  Caught in `runPrePass()` and logged at WARN;
   neither Auto-DJ nor the rest of `buildAutoPlaylist()`
   crashes.

3. **No playlist selected.**  Pre-pass and fill-pass both
   early-return when `auto_dj_playlist_id` is NULL or 0 — no
   surprise show creation.

4. **12 h cap.**  If the gap is larger than 12 h (e.g. an empty
   weekend), the auto-created show fills the first 12 h and
   the rest stays empty.  Next poll the cursor finds the next
   gap (= the rest of the weekend) and creates another 12 h
   show.  Effectively chunks long gaps into 12 h blocks.

5. **Race with operator-scheduled show.**  Operator schedules
   a manual show in a calendar gap between two polls.  Next
   poll the gap is gone → `findNextGap` returns null → no
   surprise show.  Conflict-free.

6. **Show name uniqueness.**  Per Q4 every auto-created show
   has the same name.  Operator can identify them in the
   calendar by that constant name; if they prefer
   timestamp-uniqueness later, a one-line change in
   `createGapFillingShow` is enough.

**Out-of-scope / possible future work.**

* Per-weekday autoplaylist (e.g. "Rock on Saturday nights, Jazz
  on Sunday mornings").  Today there is only one global
  auto_dj_playlist_id.
* Random rotation of multiple playlists (would still need a
  Smart Block to pick tracks; could just be a Smart Block over
  multiple playlists, no Auto-DJ change required).
* Operator confirmation before auto-creating a show.  Today the
  show appears in the calendar without prompt; a future opt-in
  "preview mode" could surface "5 gaps detected, 1 show would
  be auto-created — proceed?" instead.
* Auto-DJ-show colour theme (a dim grey background to make them
  visually distinct from operator shows).  Currently they use
  the calendar default colour.
* Recording opt-in.  Today `record = false` is hardcoded; a
  future preference could re-expose it for operators that
  intentionally want auto-DJ recordings.

---

### 23.21 Smart Block: Exclude-Played-Lately Filter

**Context.**  Even with the existing `only_unplayed` toggle
(Section 23.x), operators repeatedly hit the case where a
smart block was supposed to avoid *recent* plays without
forbidding *every* prior play.  The classic pattern:

> "Pick 30 minutes of pop music, but no track that already
> aired in the last 4 hours."

`only_unplayed` was too strict (excludes a track forever once
it has aired once); the existing time-based criteria
(`played_within`) was an inclusive filter, not an exclusive
one.  Operators worked around it by manually editing a
playlist after each rotation cycle.

**Decision.**  Add a third pool-restriction toggle to the
Advanced section of the Smart Block dialog, named
`Exclude tracks played lately`, with a companion
hours-back input.  The filter expands to

```sql
cc_files.lptime IS NULL OR cc_files.lptime < NOW() - INTERVAL 'N hours'
```

where N is the operator-set hours window.  `IS NULL`
(never-played) tracks are explicitly **included** by operator
decision 2026-05-21 — a never-played track cannot have been
played "lately", so it would be perverse to exclude it.

**Persistence.**  No schema change.  Two new rows in
`cc_block_criteria`:

| criteria | value |
|---|---|
| `exclude_played_lately` | `0` or `1` (master flag) |
| `exclude_played_lately_hours` | `1..8760` (the window) |

The hours value is persisted even when the master flag is
off so toggling the flag back on restores the operator's
last typed value.  Server-side clamp to `[1, 8760]` in
`Block::saveSmartBlockCriteria()` as defence-in-depth
against hand-crafted POSTs.

**Validation.**  Two-layer:

1. **Form-side** (`SmartBlockCriteria.php`): `Zend_Validate_Int`
   + `Zend_Validate_Between(1, 8760)`.  Allow-empty + not
   required so a deactivated checkbox + empty field passes
   cleanly.
2. **Server-side** (`Block.php`): re-clamps and defaults to
   24 h if the form-validator was somehow bypassed.

**UX.**  Two separate dl-rows mirroring the podcast
Auto-Expiry pattern (operator request 2026-05-22): the
first row holds the master checkbox; the second row (own
label `Exclude tracks played in the last hours:` + own
input) is hidden by default and shown only when the master
is on.  Initial visibility is computed server-side from the
persisted checkbox value so the second row does not flash
visible before `smart_blockbuilder.js` takes over.  Runtime
toggle handled by the JS via `#sp_exclude_played_lately_hours_wrap`
selector on the second dl element.  On first toggle-on the
hours input auto-fills with 24 so the active state is
never visually empty.  Earlier 2026-05-21 iterations
(single-line `[x] label: [input] hours` and stacked
inline-block inside one dd) were both rejected by the
operator as visually too dense — the row pair is the
final layout.

**Bug fix 2026-05-22 — WHERE-OR grouping.**  The first
shipping cut of this filter appended its WHERE string
without outer parens around the `IS NULL OR < INTERVAL`
pair.  When the operator's Search Criteria already used
`addOr()` (typical case: "Genre is X or Y or Z"), SQL
operator precedence (AND > OR) re-parsed the assembled
WHERE as

```sql
... (... OR last_genre AND lptime IS NULL) OR (lptime < INTERVAL ...)
```

— letting every track with `lptime` older than the window
slip back in regardless of genre.  Pool count
*grew* instead of shrank when the filter was toggled on.
Fix: wrap the OR-expression in explicit parens so it
remains a single conjunctive group.  The two existing
pool-restriction toggles (`only_unplayed`,
`only_with_expiry`) are single-atom predicates so they
were not affected by the same trap — but the lesson for
any future raw-SQL `->where()` filter is: **always wrap
multi-clause expressions in explicit parens** because
Propel does not group them for you.

**Compositional behaviour.**  The filter is a single
additional `->where()` call on the Propel query, so it
composes naturally with every other criterion.  Common
pairings:

| Configuration | Effect |
|---|---|
| `Exclude played lately: 4 h` + `Sort: Random` | Fresh-rotation auto-build for a one-hour show |
| `Exclude played lately: 168 h` (1 week) + `Genre = News` + `Earliest expiry first` | Weekly news rotation with shortest-lived items first |
| `only_unplayed` + `Exclude played lately: 24 h` | Redundant — `only_unplayed` already implies "never played", the lately filter is a no-op subset.  Allowed for clarity; no error. |

**Out-of-scope.**  A per-show "lately" window (different
hours for different shows using the same block) would
require either per-show smart-block overrides or a
template-style copy-on-edit, neither of which exist in
RASTATIME today.

**Files touched.**

* `frontend/legacy/application/forms/SmartBlockCriteria.php`
* `frontend/legacy/application/models/Block.php`
* `frontend/legacy/application/views/scripts/form/smart-block-criteria.phtml`
* `frontend/legacy/public/js/airtime/playlist/smart_blockbuilder.js`
* `CHANGELOG.md` + `docs/manual/{en,de,fr,es}/LIBRARY.md`

---

### 23.22 Public Now-Playing Embed Widgets

**Context.**  Stations want a small, drop-in "what is on
air right now" surface for their public homepage that does
not require any of the visitor-side machinery RASTATIME's
internal Dashboard depends on (login, jQuery 1.x, full
Angular bootstrap, large now-playing payload).  The
existing `/embed/player` and `/embed/weekly-program` cover
the audio player and the seven-day schedule grid, but
neither shows the current item.

**Decision.**  Two new iframe-only widgets sharing one
data feed.  iframe (not JS-snippet) because:

* Same-origin context inside the iframe sidesteps CORS
  entirely — the JS poll fires against the station's own
  host, regardless of where the embedding page lives.
* No JS-conflict risk with the embedding page's stack
  (which may itself be jQuery-heavy or React-based).
* Drop-in deployment for non-technical operators (paste
  HTML, done).

The widgets are intentionally **public**: no API key, no
session cookie.  This is safe because the exposed payload
is limited to show / track name + start/end timestamps
— the same data a listener would see in the audio
player's `now-playing` overlay anyway.  Listener counts,
source-switch state, operator names, recording state and
internal IDs are NOT exposed.

**Endpoint surface.**

```
GET /embed/now-playing-show?theme=...&cache=...&timezone=...
GET /embed/now-playing-track?theme=...&cache=...&timezone=...
GET /embed/now-playing-data?cache=...&timezone=...
```

The first two return self-contained HTML pages (CSS + JS
linked from `public/`).  The third returns JSON with the
trimmed Now-Playing payload that both widgets poll.

**Data pipeline.**

`Application_Model_Schedule::GetPlayOrderRange()` — the
same call that backs `/api/live-info` — provides the
station's `shows.current/next` + `tracks.current/next`.
EmbedController's `_slimShow` / `_slimTrack` helpers strip
that down to the four fields the widgets actually render
(name/label + starts + ends + timezone-normalised ISO
strings).  Final JSON payload size: ~1-2 kB rather than
the ~20 kB live-info response.

**Caching strategy.**

Two layers, both keyed on the operator-set `cache=N`
parameter (10–3600 s, default 60):

1. **Server-side HTTP headers**: `Cache-Control: public,
   max-age=N` + matching `Expires` header on every
   widget response.  Apache and any CDN in front cache
   the response identically.
2. **In-iframe JS polling cadence**: matches `N` (with
   ±10 % jitter so massively-deployed widgets do not
   synchronise their backend hits to the second).  Each
   poll hits the browser cache first; only after `N`
   seconds does it actually round-trip to the backend.

**Staleness compensation.**

The in-iframe JS holds the absolute end-time of the
current item as an ISO string (from the most recent
payload).  Per second it computes the remaining duration
client-side; when the remaining duration crosses zero
(item ended) the JS fires an immediate out-of-band poll
to grab the new "current" item.  Net effect: even with
`cache=300` (5 min server cache), the widget flips to
the next track within ~1 s of it actually starting.

**Theming.**

Three CSS modes selected via `?theme=`:
- `auto` (default) — `prefers-color-scheme` media query
- `dark` — light text, transparent background
- `light` — dark text, transparent background

Background is always transparent so the widget integrates
with whatever the embedding page's layout is.  Font stack
defaults to the embedding page's system font.

**Files touched.**

* `frontend/legacy/application/controllers/EmbedController.php`
  — three new public actions + private payload helpers
* `frontend/legacy/application/views/scripts/embed/now-playing-show.phtml`
* `frontend/legacy/application/views/scripts/embed/now-playing-track.phtml`
* `frontend/legacy/public/css/embed/now-playing-widget.css`
* `frontend/legacy/public/js/airtime/embed/now-playing-widget.js`
* `CHANGELOG.md`
* `docs/manual/{en,de,fr,es}/WIDGETS.md` (new chapter in
  all four languages) + master `USER_MANUAL.md` TOC updates

**Out-of-scope / planned for later widget waves.**

* Welle 1 / second half: Next Shows + Latest Shows widget
  (by show-name filter)
* Welle 2: Weekly Program polish (±2-Wochen-Buttons,
  link-embedding) + Day/2-Day/Week view switcher
* Welle 3: Track History widget with date-range search

All tracked in `BACKLOG.md`.

---

### 23.23 Song Requests

**Context.**  Stations want listeners to request tracks from
a public web surface and have those tracks air automatically,
in the radio.co mould, but without a moderation desk or a new
"request" content type.  RASTATIME already has the two
primitives that make this possible: smart blocks (criteria →
track set) and autoloading playlists (playlist → show).  The
feature is assembled from those plus a public intake; it adds
exactly one new table and four additive `cc_files` columns.

**Data model (decision A2).**  A single Django-managed table
`rastatime_song_request` is the authoritative per-request audit
log (one row per listener wish, `status` ∈ pending / queued /
played / expired, salted `ip_hash`, `created_at`, `played_at`,
no cross-system FK — same policy as `rastatime_linein`).  A
denormalised **aggregate cache** lives on `cc_files` (legacy
migration 0055): `requested` (bool — has an open request),
`requested_at`, `request_count`, and `requestable` (bool — is a
pool member).  The cache exists so the hot smart-block path
filters/sorts on indexed `cc_files` columns instead of joining
the request table.

**Implicit request-show marker (decision).**  A show is a
"request show" iff its autoload playlist contains a smart block
with the `use_requests` criterion — there is **no per-show
flag**.  A `cc_show` column was rejected because the Propel
model would have needed ~47 touchpoints (peer/query/map/om
regeneration) for a boolean the playlist already implies.  The
marker is detected with one SQL join
(`AutoPlaylistManager::playlistContainsRequestBlock()`).

**Components.**

* **Pool sync** — `RequestablePoolSyncTask` (TaskManager,
  5 min) expands the union of the operator-selected pool blocks
  (`Preference::getRequestablePoolBlockIds`, cc_pref
  `requestable_pool_block_ids`) with the request filter
  *ignored* (`Block::getListofFilesMeetCriteria($limit, true)`)
  and atomically rewrites `cc_files.requestable`.
* **Smart-block consumption** — a new `use_requests` criterion
  (`SmartBlockCriteria` + `Block.php`) restricts the block to
  `cc_files.requested = true`; sort orders `oldestrequest`
  (`requested_at ASC NULLS LAST`) and `mostrequested`
  (`request_count DESC`).
* **Public intake** — Django `song_request_api.py`:
  `GET /api/v2/song-requests/search` (catalogue, whole pool when
  `q` absent) and `POST /api/v2/song-requests` (submit).  Both
  `@permission_classes([AllowAny])`; submit throttled 5/h,
  de-duped 30 min by `ip_hash`, validates `requestable`.  The
  raw IP is never stored (salted SHA-256).
* **Listener widget** — `/Embed/song-request` (EmbedController),
  a self-contained vanilla-JS iframe rendering a scrollable
  table; covers via `/api/track?return=artwork-*` (gated on
  `GetAllow3rdPartyApi`).  The list endpoint returns
  `has_artwork` so cover-less tracks stay text-only (a 0-byte
  200 from the artwork endpoint would otherwise hang an `<img>`).
* **In-show fill (Option C-onepass)** —
  `AutoPlaylistManager::fillRequestShows()` →
  `_fillRequestShowByPositions()` walks `cc_playlistcontents`
  **position by position**, appending each file/block with
  `ShowInstance::addAutoloadItemToShow()` and running
  `_consumeScheduledRequests()` between slots (clears
  `requested`, flips the request to `queued`).  Because each
  smart block is resolved on its own snapshot, several
  `use_requests` blocks in one playlist draw *different* tracks
  — appending the whole playlist at once would resolve them all
  against one snapshot and draw the same oldest track.  An empty
  request slot falls back to a random track from the block's
  catalogue (`_appendRandomFromBlockPool`).  The dramaturgy runs
  once; a trailing fill block (by convention a time-remaining
  smart block) is repeated to top up the remainder, never the
  whole dramaturgy (which would pile up jingle/ID blocks).
  `RequestShowFillTask` polls every 2 min with an 8 min lead
  (`RASTATIME_REQUEST_FILL_*` env overrides).  The normal
  `AutoPlaylistTask` skips request shows so the two never fight.

**Scheduler reuse note.**  `addAutoloadItemToShow()` mirrors
`addPlaylistToShow()` (anchor on `getLastAudioItemId()` +
`updateScheduleStatus()` after each append) and builds the
`Scheduler` with `checkUserPermissions=false` passed to the
**constructor** — the constructor calls
`Application_Model_User::getCurrentUser()` whenever checking is
on, which needs a Zend session a background task does not have.
The one-shot `addFileToShow()` could not be reused for the loop.

**Lifecycle (decision: no playout hook).**
`RequestPlayedTask` (2 min) marks a `queued` request `played`
once its track sat in a `cc_schedule` slot that has ended
(after the request was made) — a schedule-based detection rather
than a playout-side `_on_file_start` hook, so the live broadcast
path is never modified for an audit-only status.
`RequestExpiryTask` (10 min) first re-pends "queued corpses": a
`queued` request whose track is in NO `cc_schedule` row (its show was
deleted before airing) returns to `pending` so the next request show
retries it — only genuine corpses, never a still-scheduled track, so a
live queued request is not duplicated.  It then expires `pending`
requests older than the TTL (default 8 h,
`RASTATIME_REQUEST_EXPIRY_HOURS`; this also sweeps up a re-pended wish
already past the TTL) and recomputes the `cc_files` aggregate from the
surviving pending rows.  Timestamp comparisons use `AT TIME ZONE 'UTC'` so they
are independent of the PDO session timezone (`cc_schedule.ends`
is `timestamp WITHOUT tz` holding UTC; `created_at` is
`timestamp WITH tz`).

**Trade-off, and its 2026-06-16 resolution (Mid-Show R1).**  The
original one-pass fill at T-lead was dead-air-safe but meant a request
arriving after the fill (≲ 8 min before start, or mid-show) landed in
the next request show.  Mid-Show R1 lifted this:
`_fillRequestShowByPositions` now resolves the dramaturgy INCREMENTALLY
across the 2-min polls, only up to
`now + RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (default 300 s) ahead of
the play head, persisting the next position in
`cc_show_instances.autoplaylist_cursor` (legacy migration 0057, raw
SQL).  A "use requests" block later in the dramaturgy is thus resolved
only when its slot is about to play, drawing requests submitted while
the show is on air; once the dramaturgy is exhausted the trailing
time-remaining block is filled COMPLETELY to the show end, bounding the
dead-air window to the short dramaturgy (the fill-ahead exceeds the
poll interval).  No playout change — `PypoLiqQueue` replaces its future
deque on each `PushSchedule` and pushes at start-time, so it picks the
mid-show append up.  `RASTATIME_REQUEST_FILL_AHEAD_SECONDS` is the
freshness/dead-air lever.  A request arriving after a show's LAST
request slot has resolved still falls to the next request show, so
dramaturgies should spread request slots through the show rather than
front-load them.  Verified live (a request made at T+~3 min, after the
pre-start fill, aired in the same show via the mid-show-resolved slot).

### 23.24 Delayed Show Start ("Allow delayed start")

**Context.**  When a show's scheduled content runs past its slot, the
backend playout serializer clamps the last item at the slot end
(`get_cue_out` / `get_ends_at` in `schedule.py`) and the following
show starts on time — the overbooked show is simply trimmed.  Stations
wanted the opposite for selected slots: let the overbooked show finish
and have the *following* show start late, without touching the live
playout path.

**Opt-in flag (decision).**  One additive boolean
`cc_show.allow_delayed_start` (legacy migration 0056,
`BOOLEAN DEFAULT false NOT NULL`).  Propel is **not** regenerated for
it — the legacy frontend reads/writes it via raw SQL
(`Application_Common_Database`), the same precedent as the `cc_files`
request columns (0055) and `expires_at` / `disabled` (0049), avoiding
the ~47 Propel touchpoints a regenerated column costs.  The flag is
per *show* (definition), so it applies to every episode; an actual
shift only ever modifies the affected *instance*.

**The core trick — extend, don't clamp.**  The overbooking show's own
`cc_show_instances.ends` is pushed out to its content end
(`MAX(cc_schedule.ends)`).  That makes its last item "inside" its
instance, so the existing serializer no longer clamps it — the show
airs in full **with no change to the Python playout path**.  This is
the whole reason the feature needs no playout-side code.

**The shift (decision: end fixed).**  The next opted-in show keeps its
`ends` FIXED and moves its `starts` to the overbooking show's content
end; its `cc_schedule` items shift by the same whole-second delta
(`SchedulerService::updateScheduleStartTime`), and its now-overflowing
last track is clamped at its own slot end by the existing overbook
logic (the accepted cut-off).  The instance is stamped
`modified_instance = true` so a repeated show changes only the
affected episode and the repeat regenerator leaves it alone.  Keeping
the end fixed bounds the ripple: a show absorbs the delay by losing
its head, then hands over on time.

**Cascade + clearing (Phase 3b).**
`Application_Service_ShowShiftService::cascadeFrom()` walks forward
from the overbooking instance holding its content end constant:

* **anchor** — the next show is not opted in: clamp the content at the
  anchor's start and stop.
* **clearing** — an opted-in show is COMPLETELY overrun (content end ≥
  its slot end): empty it (delete `cc_schedule`, zero `time_filled`,
  mark `modified_instance`, drop `cc_files.is_scheduled` where no
  longer scheduled — a single-instance mirror of `emptyShowContent`),
  leave the empty slot as a "skipped" marker, and continue the cascade
  with the same content end.
* **shift** — an opted-in show is PARTIALLY overrun: slide it (above)
  and stop; it absorbs the rest.

The overbooking show's `ends` is extended to where the content settled
**only** if a flagged show was actually cleared or shifted, so a plain
overrun into a gap or a non-flagged anchor keeps the current clamp
behaviour.

**Trigger + idempotency.**  `ShowShiftTask` (TaskManager,
auto-discovered via the `AirtimeTask` interface) runs every
`RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` (default 120), gated on a
`cc_pref` `show_shift_last_run` timestamp.  `applyDelayedStarts()`
selects cascade origins: overbooking, `modified_instance = false`
instances whose slot is within `RASTATIME_SHOW_SHIFT_LEAD_SECONDS`
(default 900) ahead — the lead window means only imminent shows move,
manually-filled shows included (it works off `cc_schedule`, not how it
was filled).  Forward-only by operator decision: a slide is never
walked back, so no original-slot column is stored.  Idempotency comes
from (a) whole-second deltas (`strtotime`), so an already-shifted show
computes a sub-second delta that floors to a no-op, and (b) the
`modified_instance = false` trigger filter, so a show already shifted
(modified) is never re-taken as a new ripple origin — at the cost that
an operator-moved instance is not itself an origin, though it is still
shifted/cleared when an earlier show overruns into it (consistent with
how `modified_instance` excludes instances from other automatic
passes).

**Playout history (decision: no intervention).**  The shift happens
before air; playout history records actual wall-clock play times from
`TrackChangedEvent.timestamp`, not schedule times, so a show aired
late is logged correctly with no extra code.

**Verification.**  PHP-lint; rollback-transaction logic tests (single
shift; cascade A→B cleared→C shifted→D untouched; direct anchor leaves
the origin's end untouched; clearing-then-anchor clamps the origin's
end at the anchor; idempotent re-runs); production smoke (the task
runs on session-less API polls); and an isolated end-to-end live test
(dedicated far-future test shows, real `applyDelayedStarts()` commit,
full teardown) — all six post-conditions confirmed.

### 23.25 Traffic Alerts

**Context.**  Traffic bulletins arrive at very short notice as MP3 files
and must air within a hard ~10-minute SLA.  The requirement is the same
mid-show-insert family as Song Requests: get a freshly-imported file
into the *running* show without touching the time-based Python playout
path (pypo re-fetches `cc_schedule` on every `PushSchedule` and pushes
each item at its start time, so a mid-show schedule change is honoured
as long as the item sits a few seconds ahead — see 23.23).

**Source (decision: a Settings smart block).**  The operator designates
ONE smart block as the traffic source under **Settings → General**
(`cc_pref` `traffic_alert_block_id`, single-select; `0` = disabled).
New bulletins are simply imported into the library so they match that
block's criteria (e.g. a "Traffic" genre/folder).  No new media path, no
`.liq` change — bulletins play through the normal `scheduled` queue and
appear in history/calendar like any track.

**The core decision — incremental fill, not insert-and-shift.**  The
original design (BACKLOG "Weg A") detected new members and inserted them
into `cc_schedule` right after the current track, shifting every
following item back (Show-Shift-style).  The operator simplified this
(2026-06-16): a show that carries the traffic block in its **autoload
dramaturgy** is filled **incrementally, exactly like a request show**,
reusing the Mid-Show R1 engine (`AutoPlaylistManager::
_fillRequestShowByPositions`).  Because the dramaturgy is resolved only
just ahead of the play head, a traffic position is resolved shortly
before its slot airs and picks up whatever was imported in the meantime
— so an alert imported mid-show airs at the **next traffic slot**, and
since the following items are not resolved yet, **nothing has to be
shifted**.  The whole insert + ripple problem dissolves.

**Detection + routing.**  `playlistContainsTrafficBlock()` (false when
the feature is disabled) marks a show as a traffic show; such shows are
skipped from the one-pass `buildAutoPlaylist()` and picked up by the
incremental `RequestShowFillTask` instead — the same dual treatment
request shows get.  The positions query gains an `is_traffic_block`
flag; `_appendPosition()` routes a flagged position to
`_appendTrafficAlert()` instead of the normal block resolve, and the
trailing time-remaining top-up never uses the traffic block as a
dead-air filler.

**Selection (decision: FIFO, exclude-scheduled, no fallback).**
`_appendTrafficAlert()` resolves the block's pool, then airs the bulletin
that is (a) **not already scheduled anywhere in this instance** — so the
same alert never airs twice across several traffic slots — and (b)
**imported earliest** (FIFO by `cc_files.utime`, the alert closest to its
deadline first).  One SQL does the `IN (pool)` + `NOT IN (scheduled)` +
`ORDER BY utime`.  Unlike a request slot there is **no random fallback**:
an empty traffic slot simply airs nothing and the following dramaturgy
item plays.  No new "consume" marker is needed — the exclude-scheduled
query is the idempotency, and the 2-min poll is naturally re-runnable.

**SLA (operator decision B: dramaturgy density).**  Because a bulletin
airs at its dramaturgy position, the 10-minute budget is held by placing
traffic slots densely enough in the show (≤ SLA apart) and keeping the
track immediately before a slot short.  An **active deadline-skip** —
`source.skip` on the current track over the existing Liquidsoap telnet
link when the next item is a late traffic alert — was **deferred to the
backlog** with a precondition: build it only if live operation shows
density alone is insufficient.

**Disable path.**  Setting the Settings field back to "(none)" makes
`playlistContainsTrafficBlock()` return false: the show is no longer
taken for incremental fill, and the block (if still in a dramaturgy) is
resolved once by the ordinary one-pass `buildAutoPlaylist()` — a clean
fallback, no orphaned state.

**Shared base (the Operator-wish-4 payoff).**  Mid-Show Requests and
Traffic Alerts now run through ONE incremental fill engine; the only
difference is how a slot resolves — request draw + random fallback
(`_appendRandomFromBlockPool`) versus FIFO-without-fallback
(`_appendTrafficAlert`).  Feature 2 added ~150 lines on top of Feature 1
and no new schema.

**Verification.**  PHP-lint; CLI read-only logic checks in a fresh
process (both new methods registered — lint cannot catch a missing
method; `playlistContainsTrafficBlock` correct on the disabled / enabled
/ contains / not-contains paths with the pref saved & restored; the
`is_traffic_block` flag marks exactly the traffic position; the
candidate SQL is valid PostgreSQL and returns the oldest-`utime`
unscheduled file).  The block-resolve reuses the exact shape already
proven by `_appendRandomFromBlockPool`.  The live airing test (a real
bulletin imported mid-show and aired at the next slot) is the
operator-run end-to-end test, mirroring the Mid-Show R1 live test.


### 23.26 Seamless Input Switching — Gates, Transitions, Pre-warm (2026-09-04)

**Context.**  With the show-transition fixes of 2026-09-04 the bus
switched *correctly* between files, webstreams and line-ins, but every
switch was a hard cut on the next frame.  Two audible consequences
remained after the line-in latency package: ~2 s of silence at the start
of a line-in or webstream slot (the pipeline has to come up), and the
last ~2 s of a line-in show never reaching the stream (they were still
in the pipeline when the source was killed).  The operator's guiding
principle is a seamless mix between all input kinds.

**Decision.**  Three mechanisms, all in Liquidsoap-mode only and each
with a fallback that reproduces the previous behaviour:

1. *Gates.*  `webstream_live` and `linein_live` are `interactive.bool`
   variables (default `true`) ANDed into the bus predicates
   (`{linein_live() and source.is_ready(linein)}`).  A Pypo that never
   touches them gets the old `is_ready` behaviour.  Telnet: `var.set`.
2. *Transitions.*  The bus `switch` carries `transitions=[...]`,
   index-aligned with its arms: DJ arms hand over instantly
   (`bus_instant`), the programme arms (webstream, line-in, scheduled)
   go through `bus_transition`.  With the house crossfade D > 0 that is
   `add(normalize=false, [fade.out(duration=D, old), fade.in(duration=D, new)])`;
   with D = 0 it is "ducking": the new source at full level after a
   50 ms ramp (click-free; also keeps both `add` elements the same
   source type, which the 2.4.4 typer demands), the old source fading
   out underneath over `DEFAULT_INPUT_DUCK_FADE_SECONDS` (1 s).
   `transition_length` is the fade length + 0.5 s.  Verified in
   isolation on the exact rendered block: two sines, gate flipped over
   telnet, spectral analysis of the recording — both shapes act at the
   flip, not at `transition_length`.
3. *Scheduling.*  `PREPARE_LEAD_SECONDS` (10 s) before a line-in or
   webstream slot the scheduler connects and buffers the source with
   its gate closed (`_on_linein_prepare` / `_on_webstream_prepare`); at
   the slot start it only opens the gate.  At the slot end — and when a
   successor takes over — it closes the gate at once and stops capture
   + source after the drain (fade + 0.5 s), guarded by the line-in /
   webstream generation counters so an older drain never kills a newer
   source.  One pre-warm at a time; none while a line-in is on air
   (single capture) or a webstream plays (single source); a pre-warm
   whose item leaves the schedule is undone at the next refresh;
   startup opens both gates.

**House crossfade.**  Settings → General "Default Crossfade Duration"
(cc_pref `default_crossfade_duration`) is read via the Django ORM at
render time and drives the queue's track crossfade, the bus transitions
and the scheduler's drain.  `RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS`
remains the fallback for a missing/invalid key.  A change takes effect
at the next PLAYOUT + LIQUIDSOAP restart.

**Rejected.**  Delaying the successor by the latency ("drain without
mixing"): every following item would start late, jingles and
top-of-hour would drift.  Shrinking the webstream clock-bridge buffer
below 5 s: the Phase-E experience is "Buffer emptied" flapping on
jittery upstreams; pre-warming removes the start gap without touching
the buffer.

### 23.27 Liquidsoap Process Hygiene on Windows — Leak, Device Index, Restarts (2026-09-05)

**Context.**  The day after the seamless-switching package the live
Liquidsoap instance (started 11:15 after a reboot) had grown to 3.4 GB
of private memory by 13:25 while the OCaml heap stayed at 78 MB, and
its Main Output had been playing to the Realtek onboard jack for
hours although the setting said Tascam.  Two independent defects of
the Windows deployment, one investigation.

**Findings.**

1. *Memory.*  A read-only scan of the process showed NT-heap segments
   full of 5136-byte units whose function pointer resolves (COFF
   symbol table of `liquidsoap.exe`) to `read_pipe_poll`, the worker
   of OCaml 4.14's `Unix.select` emulation (`win32unix/select.c`);
   the fields are the Windows HANDLEs of the Duppy scheduler's fd set.
   Every `Unix.select` of the scheduler thread leaks its SELECTDATA
   (savonet/liquidsoap #1122, open since 2020).  Replica bisection:
   a fresh instance is flat; an explicit `scheduled.push` starts
   `request.dynamic`'s asynchronous fetch task, which then re-arms
   itself every `retry_delay` (0.1 s) once the queue is empty or a
   request failed — forever.  50–100 KB/s per instance; the live one
   ran at 33 selects/s idle.
2. *Device index.*  PortAudio indices on the studio machine are not
   stable: endpoints appear late after boot and come and go (Jabra
   USB, HDMI).  The Tascam WASAPI entry was index 14 at 11:15, 18 at
   12:10, 15 at 12:33.  PLAYOUT resolved 14 at 11:15:18, Liquidsoap
   opened 14 at 11:15:28 — by then a Realtek entry.  Worse, a stale
   index that now points at an input or a WDM-KS entry is an
   unhandled exception in the clock thread: the process exits and NSSM
   restarts it with the same file (instance #1 at 11:15:22 did exactly
   that; a coincidental re-render saved the day).
3. *Latency warnings.*  `output.portaudio` is self-synced (blocking
   writes pace the clock at the device's sample clock); with
   `sync="cpu"` the clock also tried to hold wall time and logged
   "Latency is too high" every second whenever the output really
   played.  The warnings vanished after the reboot only because the
   instance sat on a DirectSound entry — whose blocking write is an
   unimplemented stub in PortAudio: no sound, no error.
4. *"Possible source leak".*  `settings.clock.leak_warning` defaults
   to 50; the chain has ~45 static sources plus 10–13 short-lived ones
   per transition that are collected again.  Not a leak.

**Decisions.**

- *Synchronous scheduled queue.*  The template carries a verbatim
  copy of the 2.4.4 stdlib `request.queue` as `request.queue_sync`
  with `request.dynamic(synchronous=true)` and `timeout=5.0`.  The
  push resolves inline in the telnet handler (local files:
  milliseconds); no Duppy task, no poller.  Replicas: flat memory,
  every push prepared at once, also after a failed push.  The 5-s
  resolution timeout bounds a broken file so Pypo's telnet call is
  never held for the default 20 s.  `settings.clock.leak_warning` is
  raised to 200.
- *Main Output by name.*  `output.portaudio(device_name=)` matches
  the exact PortAudio name at Liquidsoap's own start (first equal name
  in enumeration order, MME → DirectSound → WASAPI → WDM-KS; MME names
  are truncated to 31 characters).  The resolver still probes as
  before and then checks the entry the *name* would select: it must be
  an output, on MME or WASAPI (DirectSound's blocking write is a
  silent stub, WDM-KS has no blocking API), and it must open in the
  same blocking probe.  Only then `device_name=` is rendered; otherwise
  `device_id=` as before, with the reason in the log.  For the Tascam
  (30-character name) this selects the MME entry — 8 channels,
  Windows resampling, index-independent.
- *Boot-window restart.*  When PLAYOUT's render at start changed the
  file and the machine booted less than 10 minutes ago, PLAYOUT runs
  `nssm restart RASTATIME-LIQUIDSOAP` itself (it runs as LocalSystem);
  nothing is on air that early.  Outside the window the manual rule
  stays: PLAYOUT first, then LIQUIDSOAP.  Env
  `RASTATIME_LIQUIDSOAP_BOOT_RESTART=0` disables it.
- *Nightly quiet-window restart.*  `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`
  (default `04:00`, `off` disables) opens a 60-minute window; on the
  first schedule refresh inside it with nothing on air, nothing
  pre-warmed and no item starting within 5 minutes, the scheduler
  re-renders `rastatime.liq` (fresh device resolution and cc_pref),
  restarts LIQUIDSOAP, waits for telnet and resets the gates.  One
  attempt per day.  Safety net for the wake-ups that remain (telnet,
  harbor, http).
- *Preflight watchdogs.*  Every 15 minutes: `liquidsoap_memory_high`
  when private bytes exceed `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`
  (default 2048; error at twice that), and `main_output_session_missing`
  when no Liquidsoap process older than 90 s holds a Core Audio
  session on the configured Main Output endpoint (pycaw/comtypes,
  Windows-only, guarded).  Both surface in the dashboard banner.
- *Monitor clock.*  `clock.assign_new(id="portaudio_clock", sync="auto")`;
  the `buffer()` bridge absorbs the drift between device clock and
  main clock, which is what it was built for.

**Rejected / deferred.**  `retry_delay` as the lever: 2.0 s cuts the
leak to a tenth but a push after a decoder failure waits up to
`retry_delay` (measured 5 s at 5.0) — not acceptable for just-in-time
pushes.  A Windows scheduled task for the nightly restart: not
schedule-aware and needs an admin step; the scheduler knows what is
on air.  An OCaml-5 build or a socketpair-based Duppy wake-up:
upstream work, reported (docs/upstream/2026-09-05-…).

**Addendum 2026-09-05 (evening) — webstream recovery ("Option 1",
operator-go).**  The cloud DEVA stream (`DEVAStreamServer 1.4`,
`Event Calendar`, live signal) stalled silently a few seconds
into fresh connections on 09/02, 09/04 and 09/05, each time costing
20–50 s of dead air because `input.http` waited 10 s before giving
up, polled every 2 s and re-detected the format, while the clock
bridge held 5 s.  Two plain probes from the studio (6 min continuous,
15 min with a fresh connection every 90 s) were clean; a deliberately
slow reader was starved after 48 s and reset after 328 s, so the
appliance stops feeding a client that does not drain.  Decision:
`timeout` 10 → 3 s, `poll_delay` 2 → 0.5 s, bridge 5 → 10 s
(`max` 20 s), and webstreams pre-warm 20 s before the slot instead of
10 s (`WEBSTREAM_PREPARE_LEAD_SECONDS`; line-ins keep 10 s) so the
longer fill-up is paid before the gate opens.  Recovery budget after a
stall ≈ 5–9 s < 10 s bridge → no "Buffer emptied" for stalls up to
roughly 10 s.  Verified against a local pacing server that stalls 6 s
every 60 s (old settings: dropouts; new: none) — see CHANGELOG.  The
appliance side (listener limit, per-client buffer, logs) is checked by
the operator, who runs the DEVA.

**Addendum 2026-09-06 (evening) — the Option-1 revert and the webstream
watchdog.**  The 2026-09-05 recovery tuning ("Option 1") was tested live
on 2026-09-06 and made things worse: three of eight cloud slots went
dead until the slot end, two started on the wrong (previous) stream.
The real cause, measured against the DEVA directly: the server is
healthy (one connection is flawless; listener limit 10, the eleventh
gets `503`), but `input.http` does not detect a silent mid-stream stall
— after "Buffer emptied" no reconnect is logged until the slot ends, and
the lingering zombie connection occupies one of the ten DEVA slots, so
after a few dead slots fresh pre-warms get `503` (the failures worsen
over the run).  Backpressure and the ffmpeg `reconnect` options were
ruled out (the latter wedge input.http in a reconnect loop).  Fix: a
**scheduler watchdog** polls `source.is_ready(webstream)` (registered as
`webstream.ready`) every 2 s while a webstream is on air and, after two
not-ready polls following a ready one, forces a clean `webstream.stop` +
`webstream.start` — a fresh connection is back in <200 ms and the clean
stop frees the server slot.  Proven end-to-end against a permanently
silent server (two stalls, two ~6 s recoveries).  The Option-1
inflation (bridge 10 s/20 s, pre-warm 20 s) is reverted to 5 s/10 s and
10 s; `timeout` 3 s / `poll` 0.5 s stay.  The stale-bridge "wrong stream
for ~5 s at the slot start" is only reduced, not eliminated — a separate
follow-up (flush the bridge on a stream change).

**Addendum 2026-09-07 — nightly-restart hardening after the 04:02–08:21
crash loop.**  The nightly restart of this section failed on both
nights it ran (2026-09-06 and 2026-09-07, 04:01): the fresh instance
died within 2 s ("Portaudio error in open_device: Invalid number of
channels") and NSSM throttled it into a restart loop (a `LOG START`
every ~4 min) until the operator restarted at 08:21 — programme output
and all Icecast mounts dead for four hours while the preflight reported
"no warnings active".  Root cause, in order: (1) PortAudio enumerates
devices once per process, so PLAYOUT (up for days) resolved against the
list from its own start; (2) at 04:01 the studio display slept and its
HD-Audio endpoint (`DELL U2419HC`) was absent from all four host APIs,
shifting every later index; (3) the by-name probe used the stale MME id
of the Tascam entry → "device ID out of range" (MME error 2) → the
resolver fell back to `device_id=18`; (4) the fresh Liquidsoap, with a
fresh list, found another endpoint at 18; (5) `nssm restart` exited 1
(the started app died inside NSSM's throttle window, reported as
`SERVICE_PAUSED`), PLAYOUT retried three times and killed each fresh
instance again; (6) `main_output_session_missing` judges only processes
older than 90 s — a crash loop has none.  Fixes: `refresh_device_list`
(`sounddevice._terminate/_initialize` before every resolution);
`RenderOutcome.main_output_mode` and the rule *name-safe or not at all*
for the boot-window and the nightly restart (an index render keeps the
running instance and logs why); `restart_liquidsoap_service(verify=)`
polls the telnet `uptime` for a fresh instance (< 120 s) before it would
retry, followed by a 10 s stays-up check; and the preflight type
`liquidsoap_unavailable` (no `liquidsoap.exe`, or a new young PID on
consecutive scans).  Lesson: an automatic restart must prove the new
instance is alive — NSSM's exit code and a cached device list are not
evidence.

*Telnet cost of the leak, measured the same morning (production
instance, nothing on air):* every telnet **connection** grows the
Liquidsoap process by ~262 KB, every **command** over an open
connection by ~87 KB (≈17 `Unix.select` calls at ~5 KB) — an idle
open connection costs nothing.  PLAYOUT's client is persistent, so the
idle growth (~66 MB/h) is the SourceSwitcher's 5 s status poll, and the
webstream watchdog's 2 s poll adds ~157 MB per webstream hour; a
per-second external poller (the Phase-C probe) added ~340 MB in 20 min.
Until the upstream fix, the daily reset by the nightly restart is what
bounds this; the cheaper designs (longer poll intervals, or a watchdog
inside Liquidsoap via `thread.run.recurrent` + `source.is_ready`, ~9
MB/h) are in the BACKLOG awaiting an operator decision.

**Addendum 2026-09-07 (evening) — the webstream watchdog moves into
Liquidsoap.**  Four replicas of the production render ran 15 minutes
side by side: nothing polling (+0.9 MB), a `thread.run.recurrent` timer
checking `source.is_ready(webstream)` every second (+25 MB, ~31 KB per
tick — the timer wakes the Duppy scheduler, whose `Unix.select` leaks),
a frame counter on `bus.on_frame` doing the same check every 50th frame
(+0.1 MB — the callback runs in the streaming thread and never touches
the scheduler), and an external persistent telnet client asking
`webstream.ready` every second (+57 MB, 66 KB per command; 87 KB on the
production instance).  The scheduler's 2026-09-06 poll therefore cost
~157 MB per webstream hour, the "~9 MB/h" timer estimate of the
previous addendum was wrong (the per-select leak scales with the fd
set), and the frame counter is free.  Design (operator go): the
renderer emits a `${WEBSTREAM_WATCHDOG_BLOCK}` right after the final
`bus` definition — refs for frames/checks/seen-ready/starved/
reconnects, a check every 100 frames (2 s) while `webstream_raw` is
started, the scheduler watchdog's semantics (a not-ready right after
start does not count; two not-ready checks after a ready one →
`stop` + `start` from a one-shot `thread.run`, never from the streaming
thread), and a telnet `webstream.watchdog` reporting the counters.
PLAYOUT: `RASTATIME_WEBSTREAM_WATCHDOG=liquidsoap|scheduler` selects
where the watchdog lives (the render and the scheduler read the same
switch so both never run); in the default mode the scheduler probes
once per Liquidsoap instance whether the loaded .liq answers
`webstream.watchdog` and, if not (older render still loaded after a
PLAYOUT-only restart), polls itself as a stop-gap.  End-to-end in the
replica against a stalling server: two stalls, two reconnects after
3–4 s, bus back on the stream after ~11 s (bridge refill included).
The idle growth of the production instance (~150 MB/h, the
SourceSwitcher's status poll) is untouched by decision.

**Addendum 2026-09-08 — a fresh `input.http` per webstream slot.**  The
live stall test (DEVA power-cycled twice) recovered as designed, but the
cloud test phase right after it did not: two pre-warm starts decoded
only after 48 s and 97 s, the BBC slot never came on air, and afterwards
every `webstream.start` on the production instance sat in `starting`
for more than 90 s while `stop` sat in `stopping`.  Read against
`ffmpeg_io.ml` (2.4.4): `input.http` (re)connects through one
`Duppy.Async` task that is woken by a byte written to a pipe; on this
Windows build that wake-up is unreliable under ordinary load — the task
runs late (`starting`) or `Av.open_input` stalls (`polling`), and two
queued wake-up bytes make it run twice, the second run failing the
`assert (status = Starting)` at line 121 and leaving a "connected"
container that is not started (a zombie upstream connection).  Replica
bisection: the bare render was fast in 12/12 start/stop cycles; with
the Icecast outputs or with PLAYOUT's 5 s telnet poll present, four of
five runs hung one or two starts for 20–110 s, and waiting for
`stopped` before the next `start` did not help.  The first start of a
*fresh* source, however, was fast in 9/9 cycles under the same load.
Design (operator go, "Plan A"): the bus arm becomes
`source.dynamic(id="webstream")`; `webstream.start` creates a new
`input.http` (`webstream_in_N`, `start=true`) with its own 5 s bridge
(`webstream_bridge_N`) and swaps it in, `webstream.stop` stops and
drops it (`source.fail()` in between, so the switch falls through as
before), and the in-process watchdog recovers with a fresh source too.
The telnet contract is registered by the template itself and stays
byte-for-byte what PLAYOUT sends.  Side effect: no stale bridge, so the
remnant of the previous stream ("Hacker") at a slot start is gone.
Cost: about one lingering thread per slot until the nightly restart.
Plan B (a relay in PLAYOUT pushing the stream into `input.harbor`)
stays documented in the BACKLOG should Plan A disappoint.

*Live stall test under Plan A (22:20, DEVA power-cycled twice) and the
reaper.*  Both stalls recovered through fresh sources 6–7 s after the
DEVA returned (silence 29 s and 58 s, i.e. the outage plus the bridge).
But the dropped inputs kept polling, reconnected on their own when the
DEVA came back and then held one listener slot each without being on
the bus: `input.http` loses a stop while it polls a dead server — its
connect task overwrites `Stopping` with `Starting` after every failed
attempt, and a later `stop` is a no-op because the `Start_stop` layer
already believes the source is stopped.  A second `start` (a no-op
while connected) followed by `stop` disconnects such a source for good
(verified on both live zombies).  The template therefore records every
input whose stop did not take (`webstream_zombies`), and the frame
counter reaps each one the moment it reports `connected`
(`webstream_reap`, rendered in both watchdog modes); `webstream.watchdog`
exposes `zombies=` and `reaped=`.  Replica: three stalls, every dropped
input gone within 3 s.

**Addendum 2026-09-09 — the planned restart under a 24/7 programme.**
The nightly restart of §23.27 requires a quiet moment; with a
continuous programme it is postponed every poll and dropped when the
window closes, and the ~150–180 MB/h idle leak then runs unbounded.
Two changes (operator go a+b): *triggers* — `NightlyRestartPolicy.reason_due`
decides from the process age and private bytes
(`liquidsoap_health.liquidsoap_process_info` every scheduler cycle):
every N days inside the window (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`,
1 = daily as before), a soft memory limit inside the window
(`RASTATIME_LIQUIDSOAP_RESTART_AT_MB`, 1536), a hard limit at any time
(`RASTATIME_LIQUIDSOAP_RESTART_HARD_MB`, 3072); failed attempts are
rate-limited to one per 30 min.  *Execution* — in a quiet moment as
before; otherwise the scheduler arms `_boundary_restart_pending` and
`_on_file_start` performs the restart between two file tracks (a
webstream or line-in on either side keeps waiting), so the gap replaces
a crossfade instead of punching a hole into a track; the stays-up check
runs asynchronously there.  *Listeners* — a second, tiny Liquidsoap
(`standby.liq`, rendered by PLAYOUT from the same stream outputs with
the same encoders, no telnet, silence or a configured loop) feeds
`/<mount>-standby`; `icecast.xml` gives every public mount a
`<fallback-mount>` with `<fallback-override>`, so Icecast moves the
listeners to the standby mount during the 1–2 s the main sources are
gone and back afterwards.  The standby service is never restarted on
purpose (only when the stream outputs change) and, having no scheduler
wake-ups, does not grow.  Remaining goal (BACKLOG "Option d"): remove
the idle leak itself, after which the interval can be raised to weeks.

**Addendum 2026-09-09 b — the event-driven source switcher (option d).**
The last periodic telnet consumer was the SourceSwitcher: two status
commands every 5 s, ~87 KB each on the Windows build, i.e. the whole
~150 MB/h idle growth that forced a daily restart.  The harbor sources
now tell PLAYOUT themselves: `_render_harbor_source_events` renders
`master_dj.on_connect`/`on_disconnect` (and the show pair) with
`synchronous=true`, so a quick connect/disconnect pair keeps its
order, while the `http.post` to
`http://127.0.0.1:8770/source-event?source=…&status=…` runs in a
detached `thread.run` task with a 2-s timeout and a caught error — a
slow or absent listener never stalls the harbor handler.  PLAYOUT
applies the event at once and asks its reconciler
(`SourceSwitcher.request_reconcile`) to verify the state over telnet
one second later; otherwise the reconciler sleeps on that event for
`RASTATIME_DJ_RECONCILE_SECONDS` (default 120 s, floor 5 s) as the
safety net for a lost POST, and the scheduler requests a verification
after every Liquidsoap restart (the old process cannot report the
connections that died with it).  The loop probes
`rastatime.source_events` once per instance: an older render without
the callbacks is polled every 5 s as before, so the restart order does
not matter.  Replica: connect events arrive within milliseconds and a
kick (`show_dj.stop`) is reported at once; a client that merely closes
its socket is noticed only when the harbor's 30-s read timeout expires
— the Windows build does not see the FIN in `select` — which is the
latency the status poll had as well (BACKLOG idea: a shorter harbor
`timeout`).  Cost after the change: two telnet commands per DJ event
and per 120 s, ~125 MB/day, instead of 1,440 commands per hour.
First live measurement (10:20–10:50, nothing on air): 14 MB/h instead
of ~150 MB/h; the remainder was the telnet server dropping PLAYOUT's
silent clients after 30 s (`settings.server.timeout`), so both clients
reconnected every 2 min at ~262 KB each (~16 MB/h).  The template now
sets `settings.server.timeout.set(-1.)`; only loopback clients exist,
and Windows closes their sockets when PLAYOUT exits.
The second measurement (11:27–11:57) still read 14 MB/h: the reconnects
were gone, the remaining growth was the three telnet commands per
cycle (scheduler `uptime`, two status verifications).  Third step
(operator go): the scheduler detects a Liquidsoap restart from the
process table (PID / age of the main instance, read once per cycle and
shared with the planned-restart triggers; telnet `uptime` only as the
fallback), the DJ verification interval defaults to 600 s, and the
process probe distinguishes the main instance from the standby by
script name (`liquidsoap_health.main_instances`) — until then "the
oldest liquidsoap.exe" had been the standby since its installation,
which would have blinded the memory triggers and the
`liquidsoap_unavailable` check.
Same evening: the harbor `timeout` is rendered as 5 s (default 30;
`RASTATIME_HARBOR_TIMEOUT_SECONDS`).  The Windows build only notices a
client that merely closes its socket when that timeout expires, and
PLAYOUT pushes no tracks while it believes a DJ is live, so a hang-up
meant up to 25 s of an empty queue; with 5 s the state flips when the
harbor buffer runs out (replica: 5.06 s).
