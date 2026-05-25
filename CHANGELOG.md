# Changelog

All notable changes to RASTATIME are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Playout: tail-flush wait raised from 200 ms to 500 ms —
  Seamless-Bus-Mix Phase 1 follow-up 2** (operator follow-up
  2026-05-25).  After commit 2b2a787 the operator confirmed
  the wait now greift (visible in playout-stdout.log as a
  202 ms gap between the scheduler `STOP` event and `mpv
  stop`), but tails of longer tracks were still being clipped
  by a few seconds.  Operator decision: bump the wait to
  500 ms on all four stop sites (`_on_file_start`,
  `_on_webstream_start`, `_on_linein_start`, `_on_stop`).
  Math on a 9.9 s-cue_out track: `9.9 − 0.5 (mpv-start
  latency after parallel-stops) + 0.5 (tail wait) ≈ 9.9 s`
  effective playback.

  Operator preference recorded for future iterations: every
  track should play to its configured cue_out regardless of
  duration; a short pause on track transitions is acceptable.

- **Playout: short-track tail cut — Seamless-Bus-Mix Phase 1
  follow-up** (operator follow-up 2026-05-25).  After the
  initial Phase-1 commit landed, the operator still heard
  the tail-cut on the 10.1-s `TOH-Jingle 12 Uhr` (cue_out
  9.9 s) — clipped at ~8.4 s.  Two root causes that the
  first commit didn't cover:

  1. The `_on_stop` handler (the second track-end stop
     path, fired by the track-end Timer in parallel with
     `_on_*_start` for the next event) hard-stopped mpv
     and the FFmpeg streamers without the new
     `wait_until_stopped` guard.  Because Python's
     `threading.Timer` makes no ordering guarantee for two
     timers firing on the same wallclock instant, `_on_stop`
     fired first about half the time and set the engine to
     STOPPED before `_on_file_start`'s wait ever saw a
     non-stopped state.  Added the same bounded 200 ms
     `wait_until_stopped` in `_on_stop` so this path also
     gives the previous file a brief grace period.
  2. `_stop_streamers()` ran the three FfmpegStreamer
     `stop()` calls sequentially — each costing ~500 ms for
     its graceful 'q'-exit handshake — for a total of
     ~1.5 s of latency injected into the next track's
     mpv-start.  That latency was the dominant component
     of the ~8.4 s observed clip on the 9.9 s-cue_out
     jingle (9.9 − 1.5 ≈ 8.4).  Switched to threaded
     parallel stops with a 4-s join timeout per thread;
     the total cost is now bounded by the slowest single
     streamer (~500 ms) instead of the sum.

  Expected effect: short tracks should now play
  consistently up to (or very close to) their configured
  cue_out, since the next-track mpv-start latency drops
  from ~1.5 s to ~0.5 s and both stop paths respect the
  200 ms decode-tail flush.

- **Playout: short-track tail cut at next-track time —
  Seamless-Bus-Mix Phase 1** (operator request 2026-05-25).
  Symptom: short tracks (4–10 s) regularly lost their last
  1–2 s of audio in the Icecast output, most noticeable on
  the transition from a scheduled track to a scheduled
  webstream item.

  Root cause: `playout_scheduler.py::_on_*_start` (file,
  webstream, line-in) hard-stopped mpv and all three
  FfmpegStreamer instances the instant the scheduler-clock
  reached the next track's start time, regardless of whether
  mpv had actually finished decoding (and ffmpeg's `-re`-
  paced read had actually finished encoding) the previous
  file's tail.  On short files the gap between scheduler-
  clock and mpv's `end-file` event was large enough to clip
  audibly.

  Fix: new `PlayoutEngine.wait_until_stopped(timeout)`
  method, overridden in `MpvPlayoutEngine` with a real
  blocking wait on a `threading.Event` that is set by the
  libmpv `end-file` event callback and cleared on
  `loadfile`.  All three `_on_*_start` paths now call
  `wait_until_stopped(timeout=0.2)` immediately before their
  hard-stop, giving the previous file up to 200 ms to flush
  its tail.  Common case (previous track already ended
  naturally) returns immediately, no perceptible delay.

  Phase 2 of the Seamless-Bus-Mix work (persistent
  Icecast-PUT connection so listeners don't get kicked on
  every track change) is parked on `BACKLOG.md` for a
  separate dedicated session — A vs. B architecture
  decision happens at that kickoff.

### Added

- **Smart Block: within-block spread for the exclude-played-
  lately filters** (operator request 2026-05-25).  The two
  exclude filters (`exclude_played_lately` for tracks +
  `exclude_artists_lately` for artists) so far only kept the
  candidate pool clean of items that played in the last N h
  via `cc_playout_history`.  That SQL filter does not look at
  what the smart block itself is about to play, so the block
  could still hold e.g. two Beatles tracks back-to-back inside
  the same generation.

  New second pass `Block::applyWithinBlockSpread()` runs after
  the track-list build in `getListOfFilesUnderLimit`.  For each
  slot of the originally-selected track list:
    1. Try the original track first.
    2. If it conflicts with the elapsed-time spread window of
       the tracks already placed, pull a non-conflicting
       replacement from the broader SQL-filtered pool
       (up to 500 tracks).
    3. If no non-conflicting replacement is left, place the
       original anyway and emit a `Logging::warn` so the
       operator sees in `legacy.log` when the pool was too
       narrow for the configured spread (operator decision
       2026-05-25 — "Track stehen lassen + Warnung loggen").

  Block length stays the same (same slot count, original
  block-limit honoured); only the track choice shifts.
  Replacement order is deterministic (first non-conflicting
  track in the pool order), so re-generating the same block
  on the same inputs yields the same result.

  Artist lookups for the broader pool are done in a single
  `SELECT id, artist_name FROM cc_files WHERE id IN (...)`
  query at the start of the pass, so the spread loop itself
  is in-memory only.  No schema change.

### Changed

- **Weekly Schedule widget scaled up to 670 px width**
  (operator request 2026-05-25).  Container `max-width` raised
  from 400 px to 670 px, all other dimensions scaled
  proportionally (≈ 1.67× factor):
    - Body `font-size` 1em → 1.2em (em-based padding / gap
      values inherit the new scale automatically).
    - Header `padding-bottom` + `margin-bottom` 6px → 10px;
      nav buttons `padding` 2/8 → 4/14, `font-size` 1.1em →
      1.3em.
    - Tab strip `margin-bottom` 6 → 10, tab `padding` 4 → 8,
      active-tab border-bottom 2 → 3 px, day-of-month
      `font-size` 1em → 1.15em.
    - Content area `min-height` 120 → 200 px; day-panel
      `max-height` 470 → 790 px (matches the new iframe
      height); scrollbar 6 → 8 px wide.
    - Row `padding` 6/8 → 10/12, `gap` 0.8em → 1em, current-
      show left-border 3 → 4 px.

  Settings page (Settings → Widgets → Weekly Schedule)
  iframe + embed-snippet defaults raised from `width="400"
  height="560"` to `width="670" height="940"` so the preview
  + the copy-paste embed code match the new dimensions out of
  the box.  Operator-doc width line updated in WIDGETS.md
  EN/DE/FR/ES.

### Changed

- **Dashboard header: `source-info-block` → `status-info-block`,
  new Auto-DJ shortcut button** (operator request 2026-05-24).
  Four edits to the master panel header partial:
    1. `<h3>Source Streams</h3>` → `<h3>Status</h3>`.
    2. CSS class `.source-info-block` renamed to
       `.status-info-block` throughout the template, both
       stylesheets (`styles.css`, `masterpanel.css`, 27 hits
       combined) and the layout partial that injects the
       header.
    3. Tighter `padding-top` on the source-status `<ul>`
       (10 px → 2 px) — operator wanted the Master / Show /
       Auto-DJ rows closer together to make room for the new
       button without stretching the header.
    4. New `<li class="auto-dj-item">` row under Show Source
       with a small dark pill-button "⚙ AUTO DJ" linking to
       `/preference/auto-dj` (same tab, same window).  A 2-px
       red underline below the button is shown via the
       `.auto-dj-active` class on the `<li>` only when
       `Application_Model_Preference::GetAutoDjEnabled()`
       returned true at render time — operator-visible
       Auto-DJ status from any dashboard page at a glance.

  The Auto-DJ status is read at page-render time, not
  AJAX-polled — toggling Auto-DJ from the Preferences page
  surfaces in the header on the next page navigation.  No
  extra HTTP round-trips per page load.

### Fixed

- **Smart Block: Save button silently fails for blocks with the
  exclude-artists filter** (operator report 2026-05-24).
  `cc_blockcriteria.criteria` is `VARCHAR(32)`.  The criteria
  names introduced on 2026-05-23 were 29 and 35 characters long:
  the `..._hours` row hit PDO 22001 ("Wert zu lang für Typ
  character varying(32)"), Propel aborted the whole
  `saveSmartBlockCriteria()` transaction, the JSON response
  never arrived, and the frontend stayed stuck on the loading
  icon — operator could not see the updated track-match count
  and had to re-open the block to edit again.

  Fix in `Application_Model_Block::storeCriteriaIntoDb()`:
  rename the persisted criteria from
  `exclude_artists_played_lately` / `..._hours` to
  `exclude_artists_lately` / `..._hours` (22 / 28 chars, both
  fit in VARCHAR(32)).  Load path accepts both names so any
  rows the operator already managed to insert with the v1 name
  are still honoured.  Save path runs a `DELETE FROM
  cc_blockcriteria WHERE criteria IN (v1-names)` cleanup first
  so the next save returns to a clean two-row state.  Internal
  `$storedCrit` keys (`exclude_artists_played_lately[_hours]`)
  stay unchanged so the rest of the code (form fields, WHERE
  clause) needed no edits.

  No schema migration — chose the rename over a column widen
  because (a) zero downtime, (b) consistent with the existing
  `exclude_played_lately` / `..._hours` names (27 / 21 chars,
  both well within 32), (c) the operator's existing
  `exclude_played_lately` filter was never affected because
  the longest name there is 27 chars.

### Added

- **Smart Block: "Exclude artists played lately" filter**
  (operator request 2026-05-23).  Companion to the existing
  "Exclude tracks played lately" toggle, identical UI shape:
  a master checkbox that reveals an "Exclude tracks played in
  the last hours" input (1..8760 h, default 24).  Filters the
  pool by `cc_files.artist_name` instead of `cc_files.lptime`
  — drops any track whose artist was heard via _any_ other
  track in the last N hours.

  Use case: a smart block with hundreds of Beatles tracks
  should not still play two Beatles tracks back-to-back just
  because the second one has never aired specifically.  The
  two filters compose AND-wise: activating both gives "no
  recent track AND no recent artist".

  NULL / empty `artist_name` is intentionally never matched
  (passes the filter as-is) — a single track with a blank
  artist would otherwise exclude every other blank-artist
  track globally.

  Implementation: two new `cc_block_criteria` rows
  (`exclude_artists_played_lately` master + `..._hours`
  window), same persistence + load pattern as the per-track
  filter so missing rows = disabled (backwards-compatible).
  WHERE clause uses a `NOT EXISTS` subquery against
  `cc_playout_history JOIN cc_files` so cost is bounded even
  with a large history table.

  Files: `application/forms/SmartBlockCriteria.php`,
  `application/models/Block.php` (save/load + WHERE),
  `application/views/scripts/form/smart-block-criteria.phtml`,
  `public/js/airtime/playlist/smart_blockbuilder.js`, docs
  in EN/DE/FR/ES `LIBRARY.md`.

### Changed

- **Track-history Title/Artist mapping for webstream + line-in
  swapped** (operator follow-up 2026-05-23 v18.4).  v18.3 put
  `description` into the Artist column and `name` into the
  Title column; operator preferred the opposite — short `name`
  in the Artist column (like a band name), longer `description`
  in the Title column (like a song title).

    Webstream:  title = cc_webstream.description (fallback: name)
                artist = cc_webstream.name
    Line-In:    title = rastatime_linein.description (fallback: name)
                artist = rastatime_linein.name

  Same fallback rule as before: when `description` is empty
  (NULL or trimmed-empty), `name` is used so Title is never
  blank.  Artist is always the short `name` and therefore
  never blank.

  De-dupe SQL switched from matching on `description` (v18.3)
  to matching on `name` (v18.4) — `name` is the stable
  identifier across this swap and stays the same regardless
  of how the operator edits the description later.

- **Track-history Artist column now carries the `description`
  field for webstream + line-in entries** (operator request
  2026-05-23 v18.3).  Previously the synthetic block entries
  written by `HistoryService::insertPlayedItem()` for scheduled
  webstream and scheduled line-in items duplicated the short
  name into both `track_title` and `artist_name`.  Operator
  feedback: the Artist column should carry the longer-form
  `description` (Webstream: `cc_webstream.description`,
  Line-In: `rastatime_linein.description`) — leaving Title as
  the short label gives a two-line "Title — Artist" view with
  meaningful information on both lines, instead of repeating
  the same string.

  Fallback: when `description` is empty (NULL or trimmed-empty
  string), we keep writing `name` into the Artist column so
  the field is never blank.

  Surfaces in the Track-History widget AND the Analytics
  Playout-History dashboard (both read from
  `cc_playout_history` without further interpretation of
  what's in `track_title` vs `artist_name`).

  De-dupe SQL in both branches updated to look up the new
  Artist value, so a Liquidsoap restart firing the same
  notify still produces only one row per slot.

### Fixed

- **`Object of class DateTime could not be converted to string`
  in `insertPlayedItem` de-dupe SQL** (operator second follow-up
  2026-05-23 v18.2).  Both the v18 webstream branch and the
  v18.1 line-in branch bound `$recordStart` (a `DateTime` object
  from `CcSchedule::getDbStarts(null)`) directly to a PDO
  `:starts` placeholder.  Under PHP 8 `PDO::bindValue()` no
  longer auto-stringifies the object — it throws a fatal Error,
  which the `insertPlayedItem` `try`/`catch` rolls back (`con->
  rollback`) before re-throwing.  The outer `notifyMediaItem-
  StartPlayAction` `catch` logs and continues, but the
  history row is gone.  Net effect: every webstream-as-show-
  content and every line-in-as-show-content notify silently
  produced zero history rows.

  First production trigger was today's 09:55:00 `PLAY (line-in)
  name='Jabra-Mikro' show=test-line-in` event, which threw three
  identical exceptions visible in `logs/legacy.log` at 07:55:00
  / 08:01:06 / 08:07:00 UTC.

  Fix: pre-format `$recordStart` once into `$recordStartStr`
  (`'Y-m-d H:i:s'`) and bind the string to both `:starts`
  placeholders.  The Propel `setDbStarts($recordStart)` calls
  on the new `CcPlayoutHistory` row stay unchanged — Propel
  accepts `DateTime` directly.

  Same hotfix: the v18.1 `Logging::debug` line in
  `insertPlayedItem` printing `(file_id, stream_id, linein_id)`
  is promoted to `Logging::info` so it shows up in production
  logs without flipping the log level.  Future regressions in
  this code path will be diagnosable from a single `grep
  insertPlayedItem` over `legacy.log` without touching the
  PHP-frontend log config.

- **Scheduled Line-In items now appear in cc_playout_history**
  (operator follow-up 2026-05-23 v18.1).  The v18 commit
  earlier the same day covered scheduled file plays
  (`cc_schedule.file_id`) and scheduled webstream items
  (`cc_schedule.stream_id`), but silently missed the third
  shape RastaTime supports: scheduled Line-In items
  (`cc_schedule.linein_id`, RastaTime-only column added by
  legacy migration 0047 in the Line-In Library Phase A).
  Operator example that exposed the gap: a show with a
  "Jabra-Mikro" line-in slot inside — `notifyMediaItem-
  StartPlayAction` fired (Liquidsoap's `_on_linein_start`
  calls `_notify_media_started(row_id)` just like the file
  and webstream paths), but `insertPlayedItem` had no
  `linein_id` branch and dropped the call without writing
  any history row.

  Fix: `HistoryService::insertPlayedItem()` now reads
  `cc_schedule.linein_id` via raw SQL (the Propel-generated
  `CcSchedule` class doesn't know about the column because
  it was added after the ORM sources were generated, and
  we deliberately don't regenerate Propel sources just for
  one column) and, when set, writes a synthetic "block"
  history row analogous to the webstream branch: `file_id
  = NULL`, `instance_id` from the schedule, `track_title
  = artist_name = rastatime_linein.name`, plus `showname`.
  De-duped on `(instance_id, starts, artist_name)` so
  Liquidsoap restarts that re-fire the notify don't
  double-insert.  Surfaces in both the Track History
  widget and the Analytics Playout History dashboard.

  Also added in the same hotfix:
    - Debug-level `Logging::debug` line printing the
      `(file_id, stream_id, linein_id)` triple at the
      start of every `insertPlayedItem` call, so future
      bug reports against this code path can be diagnosed
      from the legacy log without re-instrumenting.
    - Explicit `Logging::warn` when the webstream branch
      hits `getCcWebstream() === null` (previously the
      branch silently exited with no trace), and when a
      schedule row arrives with none of the three FK
      columns set.
    - Track History widget manual (EN/DE/FR/ES) updated
      from "Five kinds of rows" to **Six kinds of rows**
      with the new scheduled-line-in path described.

### Added

- **Live-Show + Webstream content in cc_playout_history**
  (operator request 2026-05-23 v18).  Closes two gaps in
  the v17 Line-Input logging:

  1. **Webstream AS show content** — when an operator
     drops a `cc_webstream` row into a show's schedule
     (operator example: "Event Calendar" running
     for the duration of a show slot), the schedule item
     starting previously generated no history row at all
     (`HistoryService::insertPlayedItem` had a "don't add
     webstreams" early-return).  Now writes a synthetic
     "block" row with `file_id = NULL` + `instance_id` +
     starts/ends from `cc_schedule`, plus three metadata
     rows: `track_title = artist_name = cc_webstream.name`
     + `showname`.  De-duped on
     `(instance_id, starts, artist_name)` so a Liquidsoap
     restart that re-fires the notify call doesn't double-
     insert.  Surfaces in both the Track History widget
     and the internal Analytics Playout History dashboard.
  2. **Live show with no scheduled items** — when an
     operator creates a show slot but schedules nothing
     in it (so `cc_show_instances.time_filled =
     '00:00:00'`), Liquidsoap auto-switches to master_dj
     for the slot duration.  This path bypasses the
     Dashboard-source-switch hook from v17 entirely.  Now
     covered by a new `HistoryService::
     ensureLiveShowLogged()` opportunistic side-effect
     called from `ApiController::liveInfoAction` and
     `liveInfoV2Action` (both hot-path endpoints polled
     by every now-playing widget).  Writes one row per
     live-show instance with `file_id = NULL`,
     `track_title = operator label`, `artist_name =
     "Live Show"` (distinguishes from the manual-switch
     "Master Source" / "Show Source" labels), guarded by
     an idempotent `(instance_id + file_id IS NULL)` lookup
     so polling traffic can't cause duplicates.  Failure
     wrapped in try/catch + `Logging::warn` so a history-
     write error never breaks the live-info response.

  After v18 the Track History widget + Analytics Playout
  History dashboard now show **five row kinds**:
  scheduled file plays, scheduled webstream items (NEW),
  per-track webstream ICY metadata, live-show sessions
  (NEW), and manual Dashboard source switches.

- **AutoDjService: max auto-show duration raised from
  12 h to 24 h** (operator request 2026-05-23 v18).
  Original 12 h cap (operator Q2 from 2026-05-21) was
  too low for long-form live events and overnight blocks
  that legitimately need to fill a full day before the
  next manually-scheduled show kicks in.  Code change
  is one constant + 3 comment-updates in
  `AutoDjService.php`; the rest of the fill / cleanup
  logic is unchanged.

- **Line-Input session logging in cc_playout_history**
  (operator request 2026-05-22 v17).  Master Source +
  Show Source switches (= Line-In + remote-DJ) now write
  history rows whenever the Dashboard source-switch toggles
  ON, with `ends` set when the switch goes OFF.  Surfaces
  in both the Track History widget AND the internal
  Analytics Playout History dashboard (both read from
  `cc_playout_history`).

  Operator-explicit scope: do NOT pull real stream
  metadata from Liquidsoap (Line-In is raw audio with no
  ICY data anyway); just log the source label as the
  display title.  Operator-configurable via the new
  `widget_line_input_label` Preference (default "Line
  Input"), editable under Settings → Widgets → Track
  History → "Line-Input label".

  Implementation:
    - `application/models/Preference.php`: new
      `GetWidgetLineInputLabel` / `SetWidgetLineInputLabel`.
    - `application/services/HistoryService.php`: new
      `insertLineInLog($sourcename, $startDT)` and
      `endLineInLog($sourcename, $endDT)`.  insertLineIn-
      Log binds to the currently-airing show instance
      (best-effort via `Application_Model_Show::
      GetCurrentShow`), writes `file_id = NULL` (same
      shape as a webstream entry), and stores three
      metadata rows: `track_title` (= operator label),
      `artist_name` (= "Master Source" / "Show Source"
      so a future UI can differentiate the two), and
      `showname` (when bound to a show).  Wrapped in
      try/catch + Logging::warn so a history-write
      failure can never break the on-air state.  endLineIn-
      Log closes the most-recent matching open row
      (file_id NULL + ends NULL + artist_name match) —
      idempotent, safe to call multiple times.
    - `application/controllers/DashboardController.php`:
      Source-switch handler picks up new HistoryService
      calls for master_dj / live_dj (scheduled_play
      stays out of this path — it goes through
      `HistoryService::insertPlayedItem` per item start).
    - `application/forms/WidgetTrackHistory.php`: new
      `line_input_label` text input.
    - `application/controllers/EmbeddablewidgetsController.php`:
      populate + persist for the new Preference.
    - `application/views/scripts/embeddablewidgets/
      track-history.phtml`: caption explains what the
      label is for + which source switches it covers.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      source-table description now lists the three row
      kinds (scheduled / webstream / line-in).
    - `BACKLOG.md`: the "Line-In Metadaten" deferred
      item flipped to DONE with the implementation
      scope + a note on the one known limitation
      (direct Liquidsoap-Source-Connect bypasses the
      Dashboard hook).

  Known limitation: the hook fires only on Dashboard-UI
  source-switches.  A DJ connecting directly to the
  Icecast source endpoint won't trigger the history
  write — that would need a Liquidsoap/Pypo bridge
  extension.  Standard operator workflow is via the
  Dashboard though, so in practice this rarely matters.

- **Public Embed Widget: Track History** (operator request
  2026-05-22, BACKLOG widget-wave 3).  Recent-track playout
  log for the last 7 days — visitor picks a day from a
  date-picker (HTML5 native), chooses a page size
  (10/20/50/100), and the widget lists the played tracks in
  reverse-chronological order.  Click any row → modal with
  the track's metadata + show context + click-through link
  to the show URL when configured.

      <iframe src=".../embed/track-history"
              width="100%" height="500" frameborder="0"></iframe>

  URL parameters: `date` (clamped to -6..0 days from
  today), `pagesize` (10/20/50/100, default 10), `theme`,
  `cache`, `bg`, `bgcolor`, `timezone`.

  Pagination: "Load more" button at the footer appends the
  next page in-place.  Hard-capped at 10 pages × 100
  pagesize = 1000 rows total — operators who need a deeper
  history-browser use the internal Playout History
  dashboard.

  Files:
    - `application/controllers/EmbedController.php` —
      `trackHistoryAction` + `trackHistoryDataAction` +
      `_resolveTrackHistoryDay` + `_fetchTrackHistoryRows`.
      SQL: cc_playout_history JOIN cc_files LEFT JOIN
      cc_show_instances → cc_show.  Tracks without a
      file_id (some auto-DJ filler entries) are filtered
      out — they have no usable display data.  hasMore
      detection via a +1 lookup (lighter than SELECT
      COUNT(*)).
    - `application/views/scripts/embed/track-history.phtml`
      — header band (date-picker + Today + pagesize),
      `<ul>` list, footer (Load-more + status), modal
      scaffolding.
    - `application/controllers/EmbeddablewidgetsController.php`
      — new `trackHistoryAction` settings page.
    - `application/forms/WidgetTrackHistory.php` — single
      empty-state label input.
    - `application/views/scripts/embeddablewidgets/track-history.phtml`
      — settings page: label form + preview iframe (dark
      backdrop) + two embed-code snippets (pagesize 10 + 50).
    - `application/configs/navigation.php` — new "Track
      History" submenu entry under Widgets, next to On Air
      Today.
    - `application/models/Preference.php` — new
      `GetWidgetNoTrackHistory` / `SetWidgetNoTrackHistory`
      pair with English fallback.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-track-history` block: header band, list, load-
      more footer, modal styling.  Kantig + accent-colour
      conventions match the Wave-2 widgets.
    - `public/js/airtime/embed/track-history-widget.js` —
      vanilla JS runtime (~260 LoC): date / pagesize
      handlers, Load-more appender, row-click modal,
      hour-without-leading-zero formatter.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §8 chapter, family table row added, downstream
      sections renumbered 9-14.

- **Public Embed Widget: Multi-View Schedule** (operator
  request 2026-05-22, BACKLOG widget-wave 2 second half).
  Calendar-style iframe widget powered by FullCalendar 6.1.10
  (locally vendored, no CDN dependency).  Sister widget to
  the simpler Weekly-Schedule tab widget; sits under it in
  the **Settings → Widgets** submenu.

      <iframe src=".../embed/multi-view-schedule"
              width="100%" height="600" frameborder="0"></iframe>

  Three operator-switchable views: **Day**, **2-Day**,
  **Week**.  In-widget header band with ◀ / ▶ navigation,
  centred date-range label, **Today** button (snaps view +
  re-runs auto-scroll), and DAY / 2-DAY / WEEK toggle.

  Show slots are coloured from each show's configured
  `cc_show.background_color`; empty colours fall back to a
  soft accent fill.  Clicking a show opens a modal with the
  show's name, time range, description, and a click-through
  link to the show URL (if configured).  The currently-
  airing show is outlined with an accent ring, and on
  first paint (or after a Today click) the calendar auto-
  scrolls the now-indicator line into the centre of the
  viewport.

  URL parameters: `view=day|2day|week`, `theme`, `cache`
  (default 300 s = 5 min — bigger than the other widgets
  because the calendar payload is larger and refreshes
  less often), `bg`, `bgcolor`, `timezone`.

  Inspired by the operator's existing radio-calendar
  prototype (https://example.org/radio-calendar/), reworked
  to source from RASTATIME's cc_show_instances + cc_show
  instead of the original Outlook calendar bridge.

  Files:
    - `application/controllers/EmbedController.php` —
      two new actions (`multiViewScheduleAction`,
      `multiViewScheduleDataAction`) + one helper
      (`_fetchMultiViewEvents`).  `_resolveCacheTtl` picks
      up an optional `$defaultSeconds` parameter so this
      widget can default to 300 s instead of 60 s.
    - `application/views/scripts/embed/multi-view-schedule.phtml`
      — vanilla shell with FullCalendar mount point + header
      band markup + modal scaffolding.
    - `application/controllers/EmbeddablewidgetsController.php`
      — new `multiViewScheduleAction` settings page.
    - `application/forms/WidgetMultiViewSchedule.php` —
      single empty-state label input.
    - `application/views/scripts/embeddablewidgets/multi-view-schedule.phtml`
      — settings page: label form + dark-backdrop preview
      iframe + ready-made embed-code snippets for all three
      default views.
    - `application/configs/navigation.php` — new submenu
      entry "Multi-View Schedule" right under "Weekly
      Schedule" (operator-requested placement).
    - `application/models/Preference.php` — new
      `GetWidgetNoMultiViewSchedule` /
      `SetWidgetNoMultiViewSchedule` pair with English
      fallback.
    - `public/js/libs/fullcalendar/index.global.min.js`
      (~282 KB) — vendored FullCalendar 6.1.10 bundle (core
      + day-grid + time-grid + list views; CSS injected at
      runtime, no separate stylesheet).
    - `public/js/libs/fullcalendar/locales-all.global.min.js`
      (~26 KB) — all 80+ locales bundled.
    - `public/js/libs/fullcalendar/VERSION.txt` — pinned
      version + upgrade instructions.
    - `public/js/airtime/embed/multi-view-schedule-widget.js`
      — vanilla JS runtime (~350 LoC): FullCalendar init +
      lazy event-fetch + custom header wiring + modal +
      auto-scroll-to-now + current-event marking.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-multi-view-schedule` block (~200 LoC): header
      band, view switcher, FullCalendar theme integration,
      kantig (zero border-radius) overrides, accent-coloured
      now-indicator, modal styling, light/dark theme
      variants.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §7 chapter; family table updated; downstream
      sections renumbered 8-13.

- **Public Embed Widget: Weekly Schedule v2**
  (operator request 2026-05-22, BACKLOG widget-wave 2 first
  half).  Modernised replacement for the upstream jQuery 1.8.3
  + Handlebars schedule embed.  Same `/embed/weekly-program`
  endpoint, fully Wave-1-styled internals:
    * Vanilla JS (no jQuery, no Handlebars).
    * Transparent background blends into the embedding page.
    * Wave-1 URL parameters: `theme` (auto/dark/light),
      `cache` (10..3600 s), `overflow` (ellipsis/marquee),
      `link` (plain/underline, default plain), `timezone`.
    * New `?week_offset=-52..52` parameter for ±N week
      navigation.  ◀ / ▶ buttons in the widget header
      update the URL parameter in-place via
      `history.pushState` and reload.
    * New `?bg=URL` parameter — optional cover-positioned
      background image (operator hosts the image themselves,
      typically on the station's own site).
    * Show names linked to a `cc_show.url` render as
      click-through links opening in a new tab.
    * "Powered by LibreTime" footer removed.
    * Operator-configurable empty-state label "No shows
      scheduled on this day" (per-day-tab placeholder when
      a particular day has no scheduled shows).

  Settings page at **Settings → Widgets → Weekly Schedule**
  hosts the empty-state label, a live preview on a dark
  backdrop, and a ready-made embed-code snippet.

  Width is 400 px (wider than the 340 px now-playing /
  on-air-today widgets — the row layout needs more horizontal
  space for the HH:MM-HH:MM cell + the show-name cell without
  truncation).

  Files:
    - `application/controllers/EmbedController.php` —
      modernised `weeklyProgramAction` reuses the existing
      `_resolveCacheTtl` / `_resolveTimezone` / `_emitCacheHeaders`
      helpers, threads new view-vars for the Wave-1 conventions.
    - `application/common/WidgetHelper.php` — new optional
      `$weekOffset` parameter on `getWeekInfoV2`; behaviour
      identical to pre-2026-05-22 when offset is 0.
    - `application/views/scripts/embed/weekly-program.phtml` —
      complete rewrite: vanilla JS shell, JSON `<script>`
      data block, transparent BG, optional `--np-bg-image`
      inline CSS variable.
    - `application/controllers/EmbeddablewidgetsController.php` —
      modernised `scheduleAction` (now a form + preview +
      embed-code page like the other widget settings).
    - `application/forms/WidgetWeeklySchedule.php` — single
      label input + Save submit.
    - `application/views/scripts/embeddablewidgets/schedule.phtml` —
      mirror layout of the other widget settings pages.
    - `application/models/Preference.php` — new
      `GetWidgetNoWeeklyShows` / `SetWidgetNoWeeklyShows`
      with English fallback.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-weekly-schedule` block: header band with
      navigation buttons, day-tab strip, per-day row list.
      Inherits the .np-widget theme variables.
    - `public/js/airtime/embed/weekly-schedule-widget.js` —
      new vanilla JS runtime (~280 LoC): parses the JSON
      payload, builds the tabs + panels, wires ◀ / ▶ to
      history.pushState + reload, pre-selects today's tab
      when week_offset is 0.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §6 chapter for the modernised widget; family
      table row updated; renumbered downstream sections
      7-12.

- **Public Embed Widget: On Air Today** (operator request
  2026-05-22, BACKLOG widget-wave 1 third half — added on top
  of the Now-Playing / Next-Latest pairs).  A compact day-grid
  widget that lists today's schedule from the currently-airing
  show through the next several upcoming shows.  Capped at the
  station's midnight so the widget never spills into tomorrow's
  programme:

      <iframe src=".../embed/on-air-today"
              width="300" height="250" frameborder="0"></iframe>

  Each row reads "HH:MM - HH:MM  Show name", with the
  currently-airing row in bold and show names linked to their
  `cc_show.url` opening in a new tab (`target="_blank"
  rel="noopener noreferrer"`).

  Code-side default = 6 total rows (1 current + 5 upcoming),
  changeable via the `ON_AIR_TODAY_DEFAULT_LIMIT` class
  constant on `EmbedController`.  Operators can override per-
  embed with `?limit=N` (clamped 1..20).

  URL parameters: `limit`, `day` (YYYY-MM-DD, optional —
  pin any specific day for historical or upcoming overviews),
  `theme`, `cache`, `overflow`, `timezone`.

  Day boundary follows the station's calendar day (00:00 to
  24:00 in the resolved timezone).  A show that started
  yesterday 23:30 and is still on air at 14:00 today counts
  as the current row; a show starting tomorrow 00:30 is
  never listed even if `limit` would leave room.  Same
  `modified_instance` filtering as the Next/Latest Shows
  widgets so cancelled / moved instances do not leave
  phantom rows.

  Refresh model: identical to the other widgets — JS poll
  cadence matches the HTTP cache TTL, with an early refresh
  fired within ~1 s when the currently-airing row's end
  passes so the bold highlight migrates to the next row
  without waiting out the cache TTL.

  Settings page at **Settings → Widgets → On Air Today**
  hosts: a single empty-state label (default "No shows on
  air today"), a live preview iframe on a dark backdrop,
  and a ready-made `<iframe>` embed code block.  No show
  picker — the widget auto-pulls the live schedule.

  Files:
    - `application/controllers/EmbedController.php`
        Two new actions: `onAirTodayAction`,
        `onAirTodayDataAction`.  Plus private helpers
        `_prepareOnAirTodayView`, `_resolveOnAirTodayLimit`,
        `_resolveOnAirTodayWindow`, `_fetchOnAirTodayShows`.
        New class constant `ON_AIR_TODAY_DEFAULT_LIMIT = 6`.
    - `application/views/scripts/embed/on-air-today.phtml`
        Header band + `<ul>` of `<li>` rows with time-of-day
        cell + name cell (anchor-wrapped when URL non-empty).
    - `application/controllers/EmbeddablewidgetsController.php`
        New `onAirTodayAction` settings page.
    - `application/forms/WidgetOnAirToday.php`
        One text input (empty-state label) + Save submit.
    - `application/views/scripts/embeddablewidgets/on-air-today.phtml`
        Mirror layout of the other widget settings pages.
    - `application/configs/navigation.php`
        New submenu entry "On Air Today" under Widgets.
    - `application/models/Preference.php`
        New `GetWidgetNoOnAirToday` / `SetWidgetNoOnAirToday`
        with English-fallback.  Backed by `cc_pref` key
        `widget_no_on_air_today`.
    - `public/css/embed/now-playing-widget.css`
        Extended with `.np-on-air-today` block: header band,
        list rows with time-left/name-right flex layout,
        bold current-row treatment, inherit-coloured
        underlined links.
    - `public/js/airtime/embed/on-air-today-widget.js`
        New runtime: per-second `paintTimes()` + periodic
        `pollOnce()` + early-poll on current-row end
        crossover for today's view.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/`
        New §5 "On-Air-Today widget" plus new
        troubleshooting entry; renumbered downstream
        sections 6–11.

- **Public Embed Widgets: Next Shows + Latest Shows**
  (operator request 2026-05-22, BACKLOG widget-wave 1 second
  half).  Two new drop-in iframe widgets that list multiple
  instances of a single recurring show — sibling widgets to
  the Now-Playing pair but for the "next four episodes" /
  "last three episodes" use case typical on a per-show
  sidebar of a station's public website.

      <iframe src=".../embed/next-shows?show_id=42"
              width="300" height="140" frameborder="0"></iframe>
      <iframe src=".../embed/latest-shows?show_id=42"
              width="300" height="120" frameborder="0"></iframe>

  Both widgets share a single template (`shows-list.phtml`),
  a single JSON endpoint (`/embed/shows-data`), and a single
  300 px-wide CSS layout.  The only structural difference is
  ASC vs DESC ordering of the instances list and the default
  `limit` (4 for next, 3 for latest).

  Show identification:
    - `?show_id=N` — preferred, stable across renames; all
      instances of a recurring show share the same
      `cc_show.id`.
    - `?show=Name` — case-sensitive fallback used when
      `show_id` is absent.  `show_id` wins when both are set.

  URL parameters: `show_id` / `show`, `limit` (1..20),
  `theme` (auto / dark / light), `cache` (10..3600 s,
  default 60), `overflow` (ellipsis / marquee), `timezone`.

  Modified / cancelled instances
  (`cc_show_instances.modified_instance = TRUE`) are filtered
  out, matching the convention `Application_Model_Show::
  getNextShows` already uses on the internal Dashboard, so a
  single postponed episode does not leave a phantom row in
  the public widget.

  Refresh model: identical to the Now-Playing widgets — JS
  poll cadence matches the HTTP cache TTL, and a slipped
  topmost row (Next Shows) triggers an immediate refresh
  within ~1 s so the widget flips on time even under long
  cache TTLs.

  Files:
    - `application/controllers/EmbedController.php`
        Three new actions: `nextShowsAction`,
        `latestShowsAction`, `showsDataAction`.  Plus private
        helpers `_prepareShowsListView`, `_resolveShowsLimit`,
        `_resolveShowId`, `_fetchShowMeta`,
        `_fetchShowInstances`.  Reuses `_resolveCacheTtl`,
        `_resolveTimezone`, `_emitCacheHeaders`,
        `_formatTimestamp` from the Now-Playing block below.
    - `application/views/scripts/embed/shows-list.phtml`
        Shared template for both `next-shows` and
        `latest-shows` actions; renders the title row plus
        the `<ul>` of instances.
    - `application/controllers/EmbeddablewidgetsController.php`
        New `nextLatestShowsAction` settings page with a
        show-picker dropdown (cc_show ordered by name), the
        two empty-state labels, live preview iframes on a
        dark backdrop, and the ready-made embed-code blocks
        with `show_id` baked in.
    - `application/forms/WidgetNextLatestShows.php`
        New form: `preview_show_id` select +
        `widget_no_next_shows` + `widget_no_latest_shows`
        text inputs + Save submit.
    - `application/views/scripts/embeddablewidgets/next-latest-shows.phtml`
        Mirror-layout of the Current Show/Track page —
        800 px max-width, preview iframes only render once
        a show is picked.
    - `application/configs/navigation.php`
        New submenu entry "Next/Latest Shows" under Widgets.
    - `application/models/Preference.php`
        Two new getters/setters with English-fallback pattern:
        `GetWidgetNoNextShows`, `SetWidgetNoNextShows`,
        `GetWidgetNoLatestShows`, `SetWidgetNoLatestShows`.
        Backed by `cc_pref` keys `widget_no_next_shows` and
        `widget_no_latest_shows`.
    - `public/css/embed/now-playing-widget.css`
        Extended with `.np-shows-list .np-list-row` /
        `.np-list-date` / `.np-list-time` / `.np-list-empty`
        rules.  Inherits theme variables + transparency from
        the base `.np-widget` ruleset above.
    - `public/js/airtime/embed/shows-list-widget.js`
        New runtime: per-second `paintRows()` to re-render the
        date / time cells from the absolute timestamps in
        `data-starts` / `data-ends`, periodic `pollOnce()` to
        rebuild the `<ul>`, plus the early-poll mechanism
        keyed on the topmost upcoming instance for the
        Next-Shows widget.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/`
        New §4 "Next-Shows / Latest-Shows widgets" plus new
        troubleshooting entry; renumbered downstream sections
        5–10.

- **Public Embed Widgets: Now Playing — Show + Now Playing —
  Track** (operator request 2026-05-22, BACKLOG widget-wave 1
  first half).  Two new drop-in iframe widgets for external
  station homepages.  Two-line text layout, transparent
  background, no auth required:

      <iframe src=".../embed/now-playing-show?theme=dark"
              width="100%" height="50" frameborder="0"></iframe>

  Each widget shows the current item on line 1 (name left,
  end-countdown right) and the next item on line 2 (name left,
  start–end window right).  Track widget renders as
  "Artist - Title"; show widget as the show name.

  URL parameters: `theme` (auto / dark / light), `cache`
  (server-side HTTP TTL in seconds, 10–3600, default 60),
  `timezone` (any standard IANA zone, defaults to station).

  Both widgets share a single JSON feed at
  `/embed/now-playing-data` (cached identically to the iframe
  HTML).  The in-iframe JS recomputes the countdown every
  second client-side from absolute ISO timestamps and
  proactively re-polls when the current item's end-time
  passes — so a `cache=300` embed still flips to the next
  track within ~1 s of it starting, the staleness only ever
  affects the first display after a long idle pause.

  Files:
    - `application/controllers/EmbedController.php`
        Three new actions: `nowPlayingShowAction`,
        `nowPlayingTrackAction`, `nowPlayingDataAction`.
        Plus private helpers `_renderNowPlayingWidget`,
        `_resolveCacheTtl`, `_resolveTimezone`,
        `_emitCacheHeaders`, `_buildNowPlayingPayload`,
        `_slimShow`, `_slimTrack`, `_formatTimestamp`.
        Data source: `Application_Model_Schedule::GetPlayOrderRange()`
        (same as `/api/live-info` but trimmed payload).
    - `application/views/scripts/embed/now-playing-show.phtml`
    - `application/views/scripts/embed/now-playing-track.phtml`
    - `public/css/embed/now-playing-widget.css`
        Two-line flexbox layout, three theme variants,
        prefers-color-scheme media query for the auto theme,
        muted state for stale/empty data.
    - `public/js/airtime/embed/now-playing-widget.js`
        Vanilla JS (no jQuery), ~250 LoC.  Per-second
        countdown tick + cache-TTL polling + early re-poll
        on item end-time crossing + jittered poll cadence
        so massively-embedded widgets don't synchronise.

  Documentation: new `docs/manual/{en,de,fr,es}/WIDGETS.md`
  chapter; master USER_MANUAL TOC updated in all four
  languages.  ARCHITECTURE.md gets a new Section 23.22.

- **Smart Block: new "Exclude tracks played lately" pool-restriction
  toggle** (operator request 2026-05-21).  Sits between the existing
  `Allow only tracks not played yet` and `Allow only tracks with
  expiry date` toggles in the Advanced-options section of the
  New/Edit Smart Block dialog.  When enabled, the smart block's
  candidate pool is narrowed to tracks whose `cc_files.lptime` is
  either `NULL` (never played — included by operator decision
  2026-05-21) or older than the configured hours-back window.
  Companion field "Exclude tracks played in the last hours" accepts
  an integer 1..8760 (1 hour up to 1 year, operator decision
  2026-05-21); validator rejects empty / out-of-range values when
  the master checkbox is on.  Defaults to 24 h on first
  toggle-on.  Compositional with all existing criteria — common
  pairing is `Sort: Random` + `Exclude played lately: 24 h` for
  fresh-rotation auto-build content.

  Persisted in two new `cc_block_criteria` rows
  (`exclude_played_lately`, `exclude_played_lately_hours`) — no
  schema change.  Backwards-compatible: existing smart blocks
  without these rows behave exactly as before.

  Files:
    - `application/forms/SmartBlockCriteria.php` — checkbox +
      number-input form elements with Between(1, 8760) validator.
    - `application/models/Block.php` — save (2 rows), load (2
      elseif clauses), and `getListOfFilesUnderLimit()` WHERE
      clause `cc_files.lptime IS NULL OR cc_files.lptime <
      NOW() - INTERVAL 'X hours'`.  Server-side clamp of the
      hours value to [1, 8760] as defence-in-depth against a
      hand-crafted POST.
    - `application/views/scripts/form/smart-block-criteria.phtml`
      — two separate `<dl>` rows mirroring the podcast
      Auto-Expiry pattern (operator request 2026-05-22): the
      first row holds the master checkbox; the second row
      (own label + own input) is hidden by default and shown
      only when the master is on.  Initial visibility is
      computed server-side from the persisted checkbox value
      so the row does not flash visible before
      smart_blockbuilder.js takes over.
    - `public/js/airtime/playlist/smart_blockbuilder.js` —
      show/hide of the entire second dl-row (selector
      `#sp_exclude_played_lately_hours_wrap`) based on master
      checkbox; auto-fills 24 on first toggle-on so the
      active state is never empty.

  Documentation updated in all four languages under
  `docs/manual/{en,de,fr,es}/LIBRARY.md` (Smart Blocks section)
  and ARCHITECTURE.md Section 23.

### Changed

- **Track History: webstream entries + "Played in the show:"
  modal caption** (operator request 2026-05-22 v16, two
  items in one shot):

  1. **Webstream plays included in the history**.  Previous
     versions used an `INNER JOIN cc_files` which silently
     dropped all rows with `file_id IS NULL` — the shape
     that `HistoryService::insertWebstreamMetadata()`
     writes when Liquidsoap reports a webstream metadata
     update via `/api/notify-webstream-data`.

     Fix: `LEFT JOIN cc_files` plus a fallback lookup
     against `cc_playout_history_metadata` (correlated
     subquery with the `track_title` / `artist_name`
     constants from `MDATA_KEY_TITLE` / `MDATA_KEY_CREATOR`).
     For webstream entries the `artist` field carries the
     webstream's display name (`cc_webstream.name`,
     typically the operator-set label like "BBC News Live")
     and the `title` carries whatever ICY-/Now-Playing-
     metadata the upstream stream server sent at the time.
     New `isWebstream` flag exposed in the JSON payload so
     future UI passes can decorate streaming entries
     differently.

     Line-In plays still don't write any metadata to
     `cc_playout_history` — Liquidsoap treats Line-In as
     raw audio without a metadata stream, so the playout
     engine would need a configuration extension to emit
     anything.  Tracked in BACKLOG.md as a defer item with
     a documented solution path.

  2. **Modal: "Played in the show:" caption** added between
     the time-range line and the show-name line.  Operator
     request — labels the show-context for clarity.  When
     a webstream entry has no instance binding (e.g. the
     stream wasn't part of a scheduled show), the caption
     + show-name pair is hidden via a `np-th-no-show` body
     class so the modal doesn't show an orphan label.

  Files:
    - `application/controllers/EmbedController.php` —
      SQL rewrite in `_fetchTrackHistoryRows`: INNER JOIN
      → LEFT JOIN; COALESCE on cc_files + correlated
      subquery to cc_playout_history_metadata; new
      `is_webstream` flag in the row output.
    - `application/views/scripts/embed/track-history.phtml`
      — new `<p class="np-th-modal-show-intro">Played in
      the show:</p>` between time and show in the modal.
    - `public/css/embed/now-playing-widget.css` —
      `.np-th-modal-show-intro` muted-caps caption style;
      `.np-th-no-show` toggle rule that hides both the
      intro and show lines when no show context exists.
    - `public/js/airtime/embed/track-history-widget.js` —
      replaced inline `style.display` toggle with
      `body.classList.toggle('np-th-no-show')` so a single
      CSS rule covers both elements.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      §8 source-table description updated for the LEFT
      JOIN + webstream fallback; modal section mentions
      the new caption + show-context-hide rule.
    - `BACKLOG.md` — new "Line-In Metadaten in Track
      History" deferred entry with a documented solution
      path (Liquidsoap-skript erweitern + insertLineIn-
      Metadata helper).

- **Track History: 'Today' button renamed to 'Now'**
  (operator request 2026-05-22 v15).  Semantically more
  accurate — the button snaps BOTH date and time to the
  current wall-clock value (v14), so "Now" reads truer
  than "Today" (which suggested only the date would
  change).  Rename applied across the rendered button
  label, the CSS class name (`np-th-today` → `np-th-now`),
  the `data-np` attribute (`today` → `now`), the JS state
  variable (`todayBtn` → `nowBtn`), the inline comments,
  and the manual in all four languages.  No behavioural
  change — pure label rename.  Asset hashes auto-bump.

- **Track History v14 polish — 5 operator-requested items**
  (2026-05-22 v14):

  1. **Exclude-short-tracks filter**: drops jingles / station
     IDs / silence-tail entries from the public log.  Toggle
     on by default with a 60 s threshold.  Two new
     Preferences (`widget_track_history_exclude_short`,
     `widget_track_history_min_seconds`).  Per-embed
     `?exclude_short=0|1` + `?min_sec=N` URL parameters
     override the global setting.  SQL adds
     `EXTRACT(EPOCH FROM (ph.ends - ph.starts)) >= :min_sec`
     when the filter is on.

  2. **Time-of-day picker**: new `<input type="time">`
     between the date input and the Today button.
     Semantics: upper-bound — the widget lists tracks that
     ended BEFORE the picked moment, most recent first.
     Default seeds the picker to "now" on first paint so
     the widget opens on the most-recently-played slice.
     `?time=HH:MM` URL parameter for pre-pinned embeds.

  3. **Today button snaps date + time**: clicking Today
     now sets both the date AND the time to the current
     wall-clock value (operator request: "Datum + Uhrzeit
     auf jetzt").

  4. **End-time in row display**: rows now read
     `HH:MM - HH:MM Artist - Title` (was `HH:MM Artist -
     Title`).  Row-time column widened from `min-width:
     3.5em` to `7.5em` to comfortably hold the range.

  5. **Bold artist - title**: `font-weight: 700` on the
     `.np-th-row-title` so the artist / title reads as the
     primary content of each row.

  Settings page (Settings → Widgets → Track History) gets
  the new Exclude-short-tracks checkbox + threshold input,
  with the threshold field showing / hiding client-side
  based on the checkbox state — Auto-Expiry-style toggle
  pattern lifted from the podcast settings.

  Files:
    - `application/models/Preference.php` — 2 new
      Preference accessor pairs.
    - `application/controllers/EmbedController.php` —
      `_resolveTrackHistoryUpperBound`,
      `_resolveTrackHistoryTime`,
      `_resolveExcludeShortFlag`,
      `_resolveMinSecondsThreshold`; SQL `durationClause`
      added in `_fetchTrackHistoryRows`.
    - `application/views/scripts/embed/track-history.phtml`
      — `<input type="time">` + `data-time-local` attribute.
    - `application/controllers/EmbeddablewidgetsController.php`
      — form populate / persist for the two new Preferences.
    - `application/forms/WidgetTrackHistory.php` — checkbox
      + number input elements.
    - `application/views/scripts/embeddablewidgets/track-history.phtml`
      — inline JS toggle for the show/hide behaviour;
      embed-code parameter list updated with `time`,
      `exclude_short`, `min_sec`.
    - `public/css/embed/now-playing-widget.css` —
      `.np-th-time` style; `.np-th-row-time` `min-width`
      bumped to 7.5em; `.np-th-row-title` `font-weight: 700`.
    - `public/js/airtime/embed/track-history-widget.js` —
      `currentTime` state + time-input change handler +
      Today button now snaps date+time to now + row render
      uses `fmtTimeRange` for the start-end display.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      §8 parameter table extended with `time`,
      `exclude_short`, `min_sec`; layout description
      updated for the bold title + start-end-time format.

- **Multi-View Schedule v11 follow-up** (operator-reported that
  the v10 attempt didn't fully land for items 2 + 3 of the
  polish trio below):

  - **Full-width events**: `slotEventOverlap: false` alone
    wasn't enough — FullCalendar 6 treats touch-boundary
    events (event A ends 12:07, event B starts 12:07) as
    "shared columns" and packs them into half-width slots
    even though they don't actually overlap.  Fix: CSS
    override on `.fc-timegrid-event-harness` pinning
    `inset-inline-start: 0`, `inset-inline-end: 0`,
    `width: 100%` with `!important`.  Inspected the live
    payload — zero real overlaps, all boundaries are TOUCH
    or gap, so the override never hides a genuinely
    overlapping show.

  - **Hour format without leading zero**: `clockFormat()`
    was using the FullCalendar object form
    `{ hour: 'numeric', ... }` which gets silently coerced
    back to 2-digit padding in some locale + meridiem
    combinations.  Switched to the explicit string form
    (`'H:mm'` for 24h, `'h:mm a'` for 12h) which is
    deterministic.  The modal's `fmtTimeRange` ported to
    manual fmt24/fmt12 functions for the same reason.

- **All widgets: time format polish trio** (operator request
  2026-05-22 v10).  Three independent UX items:

  1. **Multi-View Schedule: event padding** — `.fc-event`
     vertical padding dropped from `2px 4px` to `0 4px` so
     sub-15-min shows have room for the time + name on one
     line (the standard layout for short events) without
     the text feeling crushed.

  2. **Multi-View Schedule: `slotEventOverlap: false`** —
     FullCalendar's default packs back-to-back events into
     half-width columns when their boundaries kiss
     (e.g. show A ends 12:07, show B starts 12:07).
     Setting `slotEventOverlap: false` renders each event
     in the full column width unless they genuinely
     overlap in time (which is rare in a radio schedule).
     The operator reported the indented layout was
     confusing — full-width events read cleaner.

  3. **All five widgets: hour format without leading zero**
     — `9:00` instead of `09:00`.  Minute stays 2-digit
     (`9:05`, not `9:5`).  Applied to:
     * `now-playing-widget.js` (`fmtTimeOfDay`)
     * `shows-list-widget.js` (`fmtTimeRange.fmt`)
     * `on-air-today-widget.js` (`fmtTimeRange.fmt`)
     * `weekly-schedule-widget.js` (`fmtTimeOfDay`)
     * `multi-view-schedule-widget.js` (`clockFormat`
       helper drives slotLabelFormat + eventTimeFormat,
       plus `fmtTimeRange` for the modal) — uses
       `hour: 'numeric'` instead of `'2-digit'` in the
       FullCalendar / Intl format objects.

  Files: `public/css/embed/now-playing-widget.css` (event
  padding); `public/js/airtime/embed/multi-view-schedule-
  widget.js` (slotEventOverlap, clockFormat,
  fmtTimeRange); `public/js/airtime/embed/now-playing-
  widget.js`, `shows-list-widget.js`,
  `on-air-today-widget.js`, `weekly-schedule-widget.js`
  (per-widget time-format helpers).  Asset hashes auto-
  bump via Assets::url() mtime versioning so visitors
  pick up the new layout on the next iframe reload.

- **Multi-View Schedule: infinite-loop fix + ?clock parameter**
  (operator bug report + UX request 2026-05-22 v9).

  Bug fix: the browser's "page unresponsive" warning was
  popping up every minute or so on the Multi-View Schedule
  settings preview, and the calendar showed no events / no
  navigation.  Root cause was an event-render infinite
  loop:

      eventsSet → markCurrentEvent → ev.setExtendedProp →
        re-render → eventsSet → ...

  FullCalendar's `setExtendedProp` triggers a re-render of
  the mutated event, which fires the `eventsSet` callback,
  which called `markCurrentEvent` again, which mutated every
  event again — a tight loop that froze the browser thread
  until it crossed the unresponsive-script threshold.

  Fix: drop `markCurrentEvent` entirely.  `eventClassNames`
  (already called by FullCalendar on every event render)
  now evaluates `Date.now()` directly against the event's
  start/end and returns `['np-mv-event-current']` or `[]`.
  No mutation, no loop.

  Trade-off: the "currently airing" highlight no longer
  walks with the wall clock once the page is loaded — if
  the operator leaves the iframe open for a full hour the
  highlight stays on the show that was airing at first
  paint.  Re-evaluated on every view change / navigation /
  Today click, which catches 99 % of real-world use.  A
  proper live-update would need a setInterval that
  periodically dirties the calendar, heavier than the
  value.

  New feature: `?clock=24|12|auto` URL parameter to
  control the time-of-day format on the hour axis, in
  show slots, and in the modal.  Default `24` (operator
  preference — the previous locale-default behaviour gave
  `5 PM` for english locales, confusing for European
  stations).  `12` forces AM/PM.  `auto` keeps the
  legacy locale-default behaviour.  Threaded through
  `slotLabelFormat` + `eventTimeFormat` on the
  FullCalendar config, plus the modal's `fmtTimeRange`
  helper.

  Files: `application/controllers/EmbedController.php`
  (new `?clock` param with strict validation); `application/
  views/scripts/embed/multi-view-schedule.phtml`
  (data-clock attribute); `public/js/airtime/embed/multi-
  view-schedule-widget.js` (loop removal + `clockFormat`
  helper + `isCurrentEvent` predicate + modal time-range
  format); `application/views/scripts/embeddablewidgets/
  multi-view-schedule.phtml` (URL params list extended
  with `clock`); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (new `clock` row in the §7 parameter table).

- **Weekly Schedule v2: iframe height bump 340 → 560 px**
  (operator request 2026-05-22 v8).  Pure sizing change —
  no behaviour difference.  The panel `max-height`
  follows up from 250 to 470 px so the show list takes
  advantage of the extra room instead of leaving
  whitespace below.  Updated the iframe height in all six
  places that reference it: the settings page preview
  iframe, the settings page embed-code snippet, and the
  drop-in iframe examples in `docs/manual/WIDGETS.md` +
  `de/` + `fr/` + `es/`.  Operators with existing embeds
  who want to keep the old height can still override via
  the iframe's `height` attribute — the widget body
  doesn't enforce a minimum.

- **Weekly Schedule v2: auto-scroll to the currently-airing
  show** (operator request 2026-05-22 v7).  When the today-tab
  is active, the widget centres the show that is on air
  right now in the panel viewport, so the visitor lands
  directly on "what's playing now" instead of having to
  scroll past the early-morning programme.

  Implementation:
    * `.np-ws-day` becomes its own scroll container
      (`max-height: 250px; overflow-y: auto;`) so the show
      list can grow without spilling outside the 340 px
      iframe (which has `scrolling="no"`).
    * Subtle scrollbar styling (matches `--np-fg-muted`,
      thin on Firefox, 6 px on WebKit).
    * Client-side: each row gets the `.np-ws-row-current`
      class when `Date.now()` falls in `[starts, ends)` —
      same boundary semantics as the On-Air-Today widget.
    * `.np-ws-row-current` is marked with an accent left-
      border (`--np-accent`) so the visitor spots it after
      the scroll; rows reserve a 3 px transparent border-
      left on every line so the layout stays stable.
    * On `activate()` of any day-panel, `scrollToCurrent`
      runs — finds the current row (if any) and computes
      `panel.scrollTop` to centre it.  Skipped when the
      activated day has no airing show, or when the
      visitor switches to a non-today tab (no
      `.np-ws-row-current` is present there).
    * Uses `requestAnimationFrame` so the panel is laid
      out (display:block via `.np-ws-day-active`) before
      reading `offsetTop` / `clientHeight` — avoids the
      first-paint zero-height race.
    * Manual `panel.scrollTop` instead of
      `scrollIntoView({block:'center'})` — the latter walks
      all scroll ancestors and would scroll the embedding
      iframe too in some browsers.

  Files: `public/css/embed/now-playing-widget.css`
  (`.np-ws-day` scroll container + scrollbar styling +
  `.np-ws-row-current` accent border); `public/js/airtime/
  embed/weekly-schedule-widget.js` (current-row marker in
  render + `scrollToCurrent` helper called from
  `activate`); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (new note block about the auto-scroll behaviour).

- **Weekly Schedule v2: kantig look + accent colour + tight
  navigation cap + bgcolor parameter** (operator request
  2026-05-22 v6, five polish items on the just-shipped v2
  widget):

  1. **"Kantig" styling**: the today indicator switches from
     a rounded pill ring (`border-radius: 999px`) to a solid
     accent-coloured rectangle, matching the legacy schedule
     widget's blocky LibreTime-teal look.  Nav buttons and
     day tabs lose their rounded edges everywhere.

  2. **Accent colour as a CSS variable**: `--np-accent`
     (default `#459B8F`, the LibreTime teal) plus
     `--np-accent-hover` (the same colour at 40 % alpha)
     are exposed on the `.np-weekly-schedule` block so a
     future per-station brand override is a one-line change.

  3. **Navigation tightened from ±52 to -2 / +4 weeks**:
     server clamp + JS clamp + view-vars supplied to the
     template; ◀ / ▶ buttons get the `disabled` attribute
     at the boundaries (CSS dims them to 30 % opacity and
     switches the cursor to `not-allowed`).

  4. **Hover states with the accent colour**: day tabs and
     navigation buttons light up at `--np-accent-hover`
     when hovered; show-name links in the row list switch
     to the full `--np-accent` on hover.  Today's tab keeps
     its solid accent on hover (so the highlight doesn't
     fade away on mouse-over).

  5. **`?bgcolor=#hex` URL parameter** for an optional
     background colour, controlled via the `--np-bg-color`
     CSS variable analogous to the existing `--np-bg-image`
     for `?bg=URL`.  Both can stack (colour shows through
     transparent regions of the image, or acts as a fallback
     while the image loads).  Validated against a strict
     `/^#[0-9a-fA-F]{3,8}$/` regex so the value can't
     smuggle CSS via the inline style attribute.

  Files: `application/controllers/EmbedController.php`
  (clamp + bgcolor validation); `application/views/scripts/
  embed/weekly-program.phtml` (data-week-offset-min/max
  attrs + --np-bg-color CSS variable); `public/js/airtime/
  embed/weekly-schedule-widget.js` (clamp + disabled-state
  on the navigation buttons); `public/css/embed/now-playing-
  widget.css` (kantig look + --np-accent + hover states +
  --np-bg-color rule); `application/views/scripts/
  embeddablewidgets/schedule.phtml` (URL params list updated
  to mention bgcolor + new -2..4 range); `docs/manual/
  WIDGETS.md` + `de/` + `fr/` + `es/` (week_offset range,
  bgcolor row, new note about today-tab + active-tab
  styling).

- **Widget width: Now-Playing + On-Air-Today bumped to 340 px**
  (operator request 2026-05-22 v5).  The Current Show, Current
  Track, and On-Air-Today widgets now have a 340 px-wide body
  instead of the previous uniform 300 px — more breathing room
  for the bold show names and the time-of-day cells.

  Next-Shows / Latest-Shows widgets stay at 300 px (they
  serve a narrower sidebar use-case where the tighter body
  reads cleaner).

  Implementation:
  * New marker class `np-now-playing` added to both
    Now-Playing templates so the CSS can target them
    explicitly (`np-on-air-today` already existed).
  * Width cap moved from the unconditional `.np-widget`
    rule into per-family overrides: base default stays
    300 px (covers shows-list), the two wider families
    bump to 340 via `.np-widget.np-now-playing,
    .np-widget.np-on-air-today { max-width: 340px; }`.
  * Marquee animation end-offset parameterised through a
    `--np-marquee-end` CSS variable: 280 px for the narrow
    300 px widgets (default), 320 px for the wider 340 px
    widgets.  Single `@keyframes np-marquee-scroll` works
    for both via `var(--np-marquee-end, 280px)`.
  * Settings-page preview iframes and embed-code snippets
    updated to `width="340"` on both Current Show/Track
    and On-Air-Today pages.

  Files: `application/controllers/EmbedController.php`
  (unchanged); `application/views/scripts/embed/now-
  playing-{show,track}.phtml` (added `np-now-playing` to
  body class); `application/views/scripts/embeddablewidgets/
  current-show-track.phtml` + `on-air-today.phtml`
  (iframe width 300 → 340); `public/css/embed/now-playing-
  widget.css` (per-family max-width override + marquee
  variable); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (Now-Playing & On-Air-Today iframe snippets + Note
  about widget cap updated; Next/Latest still 300 px noted).

- **On-Air-Today: typography & link-default polish**
  (operator request 2026-05-22 v4).  Three small visual
  changes to make the widget more legible at sidebar embed
  sizes:
    * `?link` parameter default flipped from `underline` to
      `plain`.  The underline competed with the (now bold)
      show names; operators who want the classic hyperlink
      affordance back can opt in with `?link=underline`.
    * Row height roughly doubled — `padding: 12px 0` (was
      `3px 0`) and `line-height: 1.6` (was `1.4`), so each
      row reads as a distinct band instead of a tight stack.
    * Uniform bold: header + every row now uses
      `font-weight: 700` and a `1.1em` (rows) / `1.2em`
      (header) font-size.  Operator explicitly asked for
      "all bold, all bigger".  Current-row weight flourish
      removed (would collide with the new uniform weight);
      the `.np-row-current` selector kept live but empty as
      a clean attachment point if the operator later wants
      the current row distinguished by colour or background.
  Files: `application/controllers/EmbedController.php` (link
  default), `public/css/embed/now-playing-widget.css` (the
  size / weight / padding block), `docs/manual/WIDGETS.md`
  + `de/` + `fr/` + `es/` (updated `?link` default in the §5
  parameter table).

- **Public Embed Widget polish trio** (operator request 2026-05-22 v3,
  three small UX changes on top of the wave-1 widgets).

  1. **On-Air-Today: `?link=plain` URL parameter.**  Optional
     URL param to drop the underline from the show-name links
     when the operator prefers a clean text-only look.  Default
     `underline` keeps the previous behaviour and the standard
     hyperlink affordance.  CSS class `.np-link-plain` on the
     widget body.

  2. **Next/Latest Shows: manual show-name input + dropdown
     grouping by name.**  The Settings → Widgets → Next/Latest
     Shows page now offers two ways to identify the show:
       * The existing dropdown — but **grouped by name** so a
         station with seven shows all called "BBC News" sees
         one dropdown entry "BBC News (7 shows)" instead of
         seven near-identical lines.  Single-instance names
         still resolve to `?show_id=N`; multi-instance groups
         use `?show=Name` (semantic change below).
       * A new **manual show-name text input** for operators
         who want to generate embed snippets for shows not (yet)
         in the database, or who prefer to filter by string.
         Tooltips explain that the dropdown takes precedence
         over the manual field (mirrors the `?show_id` >
         `?show` rule the public widget URL uses).

  3. **Next/Latest Shows: light-theme time-cell colour
     alignment.**  The time-of-day cell in the list rows now
     uses the full `--np-fg` colour instead of the muted
     variant, matching the corresponding cell in the
     On-Air-Today widget.  Previously the cell read as
     mid-grey on the light theme that was harder to scan than
     the date cell next to it.

  **Semantic change** (worth noting for existing embeds):
  `?show=Name` on the next-shows / latest-shows widgets now
  matches **every** cc_show row that shares the name, rather
  than silently taking only the first id.  Operators with
  multiple same-named shows (e.g. one per weekday) get a
  merged timeline; operators whose show names are unique see
  identical behaviour.  Backend pivots from
  `_resolveShowId` (single int) to `_resolveShowIds` (int
  array) and switches the WHERE clause from `show_id = :sid`
  to `show_id = ANY(:sids)`.

  Files:
    - `application/controllers/EmbedController.php` —
      `_resolveShowIds`, multi-id WHERE in `_fetchShowMeta`
      and `_fetchShowInstances`, new `?link` parameter for
      On-Air-Today widget.
    - `application/controllers/EmbeddablewidgetsController.php`
      — group-by-name dropdown via ARRAY_AGG SQL, parse the
      "name:..." marker on submit, expose previewShowName +
      manualShowName to the view.
    - `application/forms/WidgetNextLatestShows.php` — new
      `manual_show_name` Zend_Form_Element_Text with tooltip.
    - `application/views/scripts/embeddablewidgets/next-latest-shows.phtml`
      — show-id OR show-name preview/embed URL generator,
      precedence explanation in the form description.
    - `application/views/scripts/embed/on-air-today.phtml` —
      thread the `linkClass` view-var into the body.
    - `public/css/embed/now-playing-widget.css` —
      `.np-link-plain` rule for On-Air-Today links;
      `.np-shows-list .np-list-time` colour from muted to
      full `--np-fg`.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      `?link` parameter row in §5, `?show=Name` description
      updated to reflect multi-match semantics.

- **Public Embed Widgets: Next/Latest Shows theme contrast fix**
  (operator request 2026-05-22).  Bug report: all three themes
  (auto / dark / light) on the new shows-list widgets looked
  visually identical — the theme switch had no obvious effect.
  Root cause: every list row used `color: var(--np-fg-muted)`,
  which renders as a mid-grey in both dark (`#bbb`) and light
  (`#555`) themes — close enough on most embedding backdrops
  that the operator perceived them as the same shade.

  Fix: realign the shows-list colour palette with the Now-Playing
  widget's "current row" convention from wave 1.
    * `.np-row-title` and `.np-list-row .np-list-date` now use
      the full `var(--np-fg)` colour (near-white in dark, near-
      black in light) instead of the muted variant — so the
      theme switch flips text contrast clearly.
    * `.np-list-time` and `.np-list-empty` keep `var(--np-fg-
      muted)` to preserve the "primary date, secondary time-of-
      day" reading hierarchy that mirrors the start–end cell in
      the Now-Playing widget.
  File: `public/css/embed/now-playing-widget.css`.

- **Settings → Widgets → Current Show/Track: page polish**
  (operator request 2026-05-22).  Pure UX cleanup — no
  behaviour change.
  * Page container capped at `max-width: 800px` to match the
    Weekly Schedule settings page so the Widgets section reads
    consistently.
  * Preview iframes forced to `?theme=dark` so the previews
    sit on a dark backdrop that matches the rest of the admin
    UI (the actual embed code at the bottom of the page does
    NOT force a theme, so the public widget keeps following
    the visitor's `prefers-color-scheme`).
  * Section heading renamed `Empty-state labels` → `Labels`
    (shorter, less jargon).
  * Four input labels shortened from `Label when no show is
    on air:` etc. to the actual configured strings
    (`No show on air:`, `No upcoming show:`, `No track
    playing:`, `No upcoming track:`).  The form now reads as
    a list of the outputs rather than meta-descriptions of
    them.
  * Input widths reduced from full-row to `18em` (about 30 %
    of previous width).  Manual tables in
    `docs/manual/{en,de,fr,es}/WIDGETS.md` updated to match
    the new UI labels.

- **Now-Playing widgets: 300 px width cap + truncate / marquee
  overflow handling + operator-configurable empty-state labels
  + dedicated Widgets → Current Show/Track settings page**
  (operator request 2026-05-22).  Three coupled polish items
  that ship together because they all touch the same widget
  pair.

  Width: the widget body is now `max-width: 300 px` to fit
  common station-website sidebar layouts.  An embedding page
  that sets the iframe to 300 px wide gets a flush widget; a
  wider iframe shows white space around the widget.

  Overflow: long show / track names that exceed the 300 px
  body now have a per-embed strategy picked via
  `?overflow=ellipsis|marquee` URL parameter.  `ellipsis`
  (default) truncates with `…`; `marquee` scrolls the text
  left over 24 s so the operator can still read the whole
  title.  Pure CSS animation — no extra JS.

  Empty-state labels: the four placeholder texts that the
  widgets show when a current / next show / track is missing
  are now operator-configurable via four new cc_pref keys
  (`widget_no_current_show`, `widget_no_upcoming_show`,
  `widget_no_current_track`, `widget_no_upcoming_track`).
  Each Preference getter falls back to the English source
  string when blank so an unconfigured station behaves
  exactly as before.  Labels are shipped both in the
  server-rendered HTML (`data-label-no-current` /
  `data-label-no-upcoming` body attrs) and in the JSON
  refresh payload (`labels` key), so an operator's label edit
  surfaces within one cache TTL without a manual iframe
  reload.

  Settings UI: new submenu entry **Widgets → Current
  Show/Track** alongside Player and Weekly Schedule.  The
  page combines a live side-by-side iframe preview, the
  four label inputs, and the ready-made `<iframe>` embed
  code for both widgets with the absolute station URL
  pre-filled.

  Files:
    - `application/controllers/EmbedController.php`
        New `?overflow=` parameter parsing; `emptyLabels`
        view variable populated from `Preference::GetWidget*`
        getters; `labels` block added to the JSON payload.
    - `application/controllers/EmbeddablewidgetsController.php`
        New `currentShowTrackAction` that handles GET (form
        seeding from cc_pref) and POST (label persistence
        via `Preference::SetWidget*`).
    - `application/forms/WidgetCurrentShowTrack.php`
        New Zend_Form with four text inputs (one per
        label).  Allow-empty + placeholder-as-default
        pattern so a cleared field falls back to the
        English source string at render time.
    - `application/models/Preference.php`
        Eight new static methods (`GetWidgetNo*` +
        `SetWidgetNo*`) using the same blank-fallback
        pattern as `GetAutoDjShowName`.
    - `application/views/scripts/embed/now-playing-show.phtml`
    - `application/views/scripts/embed/now-playing-track.phtml`
        Body class now carries both `themeClass` and
        `overflowClass`; new `data-label-no-current` /
        `data-label-no-upcoming` body attrs hold the
        server-rendered labels for the JS-side fallback.
    - `application/views/scripts/embeddablewidgets/current-show-track.phtml`
        New settings page with three fieldsets: live
        preview, four-input label form, embed-code blocks.
    - `application/configs/navigation.php`
        New "Current Show/Track" entry under the existing
        Widgets parent.
    - `public/css/embed/now-playing-widget.css`
        `max-width: 300px` on `.np-widget`; new
        `.np-overflow-marquee` class with a 24 s CSS
        animation; documented kick-off conditions in the
        block comment.
    - `public/js/airtime/embed/now-playing-widget.js`
        Reads labels from data-attrs on boot, then
        refreshes them from each poll's `labels` payload
        so the JS-side no longer carries hard-coded
        English defaults.

  Documentation: `docs/manual/{en,de,fr,es}/WIDGETS.md`
  extended with two new sections (max-width note in §2 +
  empty-state labels in §4), URL-parameter table extended
  with the `overflow` row.  Subsequent section numbers
  shifted by one in all four languages.

### Fixed

- **Now-Playing widgets: 500 Internal Server Error on the two
  iframe widget URLs** (bug reported + fixed 2026-05-22, same
  day as the feature shipped).  Both `/embed/now-playing-show`
  and `/embed/now-playing-track` returned the Zend error page
  while `/embed/now-playing-data` (the shared JSON endpoint)
  worked fine.  Root cause: the shared `_renderNowPlayingWidget`
  helper called `$this->_helper->viewRenderer->setScript(...)`
  to pick the template — but `setScript()` does not exist on
  Zend-1's `Zend_Controller_Action_Helper_ViewRenderer` (the
  correct API is `setScriptAction()`, or simpler: rely on the
  default convention `actionName → action-name.phtml`).  Fix:
  rename the helper to `_prepareNowPlayingView`, drop the
  setScript call, let Zend's default view resolution turn
  `nowPlayingShowAction` into `now-playing-show.phtml` on its
  own.  Plus a secondary polish in `_slimShow` /
  `_slimTrack`: the upstream Schedule model returns a stub
  `{ name: "", starts: null, ends: null }` for "no next show",
  which the template's `?? 'No upcoming show'` fallback failed
  to catch (empty string is not null).  Normalised both
  helpers to return a single null in the empty case so the
  template stays simple.

- **Smart Block: "Exclude tracks played lately" pool count
  was inflated by broken OR-grouping in the WHERE clause**
  (bug reported + fixed 2026-05-22).  When the operator's
  Search Criteria already contained an OR-chain (typical
  case: "Genre is X or Y or Z"), enabling the new
  `Exclude tracks played lately` filter caused the
  `N tracks match your search criteria` counter to *grow*
  instead of shrink — sometimes returning more tracks than
  the unfiltered query.  Root cause: the WHERE string
  `cc_files.lptime IS NULL OR cc_files.lptime < NOW() -
  INTERVAL '24 hours'` was appended to the assembled query
  with `AND` but without an outer set of parens around the
  OR-pair.  SQL operator precedence (AND binds tighter than
  OR) then re-parsed the whole WHERE as `... OR (last_genre
  AND lptime IS NULL) OR (lptime < INTERVAL...)`, which let
  every track with `lptime` older than the window slip back
  in regardless of genre.  Fix: wrap the OR-expression in
  explicit parens so it remains a single conjunctive group.
  Other filters (`only_unplayed`, `only_with_expiry`) are
  single-atom predicates so they were not affected by the
  same precedence trap.

### Fixed

- **Calendar: per-show fill bar auto-refreshes every 60 s.**
  The fill indicator drawn in `eventRender()` reflects
  `cc_show_instances.time_filled` via the `event.percent`
  property delivered by the `Schedule/event-feed` endpoint.
  Pre-2026-05-20 the calendar only refetched events on direct
  user actions (drag/drop, edit, delete) — so an autoplaylist
  that ran 1 h before show start (AutoPlaylistManager's 60 s
  polling job) filled `time_filled` in the DB but the visual
  fill bar stayed at 0 % until the operator manually reloaded
  the page.  Added a single `setInterval(refetchEvents, 60_000)`
  in `full-calendar-functions.js` so the calendar pulls
  fresh events on the same cadence as the auto-build polling.
  The poll is gated on `$cal.is(":visible")` to avoid wasted
  AJAX when the operator is on a different tab.

- **Settings → Streams: "Streaming Server status" no longer
  stuck on "Getting information from the server…".**  The
  `Preference/get-liquidsoap-status` endpoint queries Icecast's
  `status-json.xsl` to determine each output's connected/
  inactive/waiting state.  Two Windows-specific failures were
  combined into a complete silence on the front-end side:
  (1) the configured stream host defaults to `localhost`, and
      Windows' resolver returns the IPv6 `::1` for that name
      before the IPv4 `127.0.0.1`; Icecast on this fork binds
      to IPv4 only, so every status check sat through the full
      2 s socket timeout before falling back.
  (2) the timeout produced an `E_WARNING` from
      `file_get_contents`, which the global error handler
      promotes into an `ErrorException` — and `@` does NOT
      suppress error-handler-mediated exceptions.  The whole
      action then HTTP 500'd and the JS poll silently
      discarded the response, leaving the page on its
      initial "Getting information…" placeholder forever.
  Fix in `PreferenceController::getLiquidsoapStatusAction()`:
  rewrite `localhost` → `127.0.0.1` when building the
  Icecast status URL (forces IPv4 directly, no resolver
  round-trip), and wrap the `file_get_contents` call in
  `try { … } catch (Throwable)` so any future transient
  hiccup degrades to status `waiting` instead of nuking the
  whole JSON response.  No schema change.

- **Embed Player widget: mobile-flag categorisation no longer
  broken.**  The `/embed/player?stream=auto` endpoint built the
  available-stream list straight from `cc_pref`.  The `mobile`
  flag is stored as the literal string `"false"` (not boolean
  false) because the cc_pref persistence layer serialises
  everything as strings, and `"false"` is truthy in PHP — so
  the `if ($s['mobile']) { mobile-queue } else { desktop-queue }`
  branch silently routed every stream into the mobile queue and
  left the desktop player with nothing to play.  Fix in
  `EmbedController::playerAction()`: normalise the flag to a real
  boolean with explicit string comparison
  (`$m === true || $m === 'true' || $m === '1' || $m === 1`).
  Note: stream URL itself is **not** rewritten — operators are
  expected to configure a publicly-reachable host in
  Settings → Streams (Icecast `host` field) for LAN / external
  embedding.  A first version of this fix auto-rewrote
  `localhost` / `127.0.0.1` in the URL to the request host name,
  but that was reverted on operator request — settings should be
  the single source of truth.

- **Settings → Show Templates: left sidebar sub-navigation no
  longer collapses.**  Every other Settings page assigns
  `parent_page = 'Settings'` to the Zend layout (the layout
  uses that key to keep the General / My Profile / Users /
  Track Types / Show Templates / Streams / Local Machine /
  Status sub-nav visible).  The
  `PreferenceController::showTemplatesAction` shipped without
  that assignment when the Show-Templates page landed in
  Section 23.16, so opening it collapsed the sub-nav and the
  operator had to click the parent Settings entry again to
  navigate away.  One-line fix.

- **Autoloading Playlist: margin capped at 5 s, post-outro
  cleanup pass added** (Section 23.19 v8, 2026-05-20).
  Operator policy clarification:
    * margin ≤ 5 s (any "silence" tail visible to listeners
      must stay small),
    * over-fill must be avoided,
    * if measured-vs-real outro divergence pushes the show
      beyond the slot anyway, trim autoplaylist tail tracks
      (not the outro!) until the overbook is gone.
  Implementation:
    * The safety margin reverts from 10 s (v7) to 5 s.
    * Before the real outro insert,
      `MAX(cc_schedule.id)` for the instance is snapshotted.
    * After the insert, the new helper
      `ShowInstance::trimTailExcept($excludeAboveId, $reserve)`
      runs and trims schedule rows with `id <= snapshot`
      (= autoplaylist tail) until `getSecondsRemaining() >= 0`.
      The outro rows are protected by the id filter.
    * Skipped in the "outro > slot" edge case (operator
      explicitly wants overbook in that branch).
  Result: in the worst case where the smart-block-pick divergence
  exceeds the 5 s margin, the autoplaylist becomes a bit shorter
  than ideal but the show never overbooks.

- **Autoloading Playlist: 5 s safety margin bumped to 10 s
  on the outro reserve** (Section 23.19 v7, 2026-05-20).
  *Reverted in v8 — operator policy capped margin at 5 s and
  introduced a post-outro cleanup pass instead.*
  v6 used 5 s but the Auto+Outro variant (no intro)
  still showed a 4 s overbook in operator testing — the
  trial-measured outro length and the real outro length
  diverged enough (smart-block random pick) that 5 s was not
  always enough.

- **Autoloading Playlist: 5 s safety margin on the outro
  reserve** (Section 23.19 v6, 2026-05-20).  Operator testing
  on the "Time remaining in show" autoplaylist smart-block
  variant flagged a consistent 4 s overbook: the SSP-best-fit
  picker in `Block::getListOfFilesUnderLimit()` maximises the
  subset sum against the strict ≤ target, but the Scheduler's
  later crossfade pass adjusts the actual schedule timestamps
  by a few hundred milliseconds per transition, and those
  shifts do not line up exactly with what the SSP saw.  Result:
  an autoplaylist sized to fit (slot − measured_outro) lands a
  few seconds over the slot boundary, pushing the outro into
  overbook territory.  v6 adds a defensive 5 s cushion on top
  of the measured outro length when computing the reserve.
  Sacrifices at most ~5 s of slot fill but eliminates the
  overbook the operator flagged as unacceptable (under-fill ≤ 5 s
  is OK; over-fill is not).  This does not touch the
  fixed-time-limit Smart Block path — those blocks ignore the
  reserve and run against their own time limit, so a slot with
  a 9 min Fixed-Time-Limit autoplaylist and a 10 min slot will
  always have ~60 s of unscheduled tail.  Operators who want
  the whole slot filled should configure their autoplaylist
  smart block as "Limit to: Time remaining in show".

- **Autoloading Playlist: trial-insert no longer poisons
  `cc_files.is_scheduled`, outro is no longer skipped on the
  edge case** (Section 23.19 v5, 2026-05-20).  Two follow-up
  problems shipped together with the v4 trial-insert
  measurement:
  (1) `Scheduler::insertAfter()` flips
      `cc_files.is_scheduled = TRUE` for every file it adds to
      `cc_schedule`, and the DELETE on roll-back does NOT walk
      that flag back.  After the trial pass the outro's track
      pool was marked "already scheduled".  Subsequent smart-
      block expansions reading the flag would see a poisoned
      pool — empirically the autoplaylist kept picking the same
      tiny subset across all tests because everything else was
      flagged.  v5 snapshots
      `SELECT id FROM cc_files WHERE is_scheduled = TRUE` *after*
      the intro insert (so intro tracks are in the snapshot and
      are not reset), runs the trial, then resets the flag for
      any cc_files row that is TRUE *and* not in the snapshot,
      *before* deleting the trial schedule rows (order matters:
      drop the flag before removing the row that justifies it).
  (2) The v2/v3/v4 edge-case branch *skipped* the outro
      entirely when its length was greater than the show slot —
      so a too-long outro turned into a fully-filled autoplaylist
      and an empty 30 s tail.  Operator policy revised
      2026-05-20: "Es ist besser, die Show ist überfüllt, als
      zu wenig befüllt".  The outro is now always inserted; the
      edge-case branch only zeroes the reserve so the autoplaylist
      fills the entire slot, and the outro overbooks on top.
  Plus a one-off DB heal recomputed `cc_files.is_scheduled` from
  the actual `cc_schedule` rows to clean up the poisoning that
  v4 had already inflicted on the test installation (67 rows
  fixed; should be a no-op on a fresh database).

- **Autoloading Playlist: outro length is now measured by a
  trial-insert + roll-back** (Section 23.19 v4, 2026-05-20).
  Reading `cc_playlist.length` directly (v1–v3) works only for
  static playlists.  Any playlist that contains a smart block
  reports `length = 00:00:00` because Propel does not aggregate
  the smart-block contribution into the parent playlist's length
  column — empirically verified on the operator's 8
  "Tagesplaylist <Genre> Outro" playlists, all of which carry
  one smart block and all of which had `length = 0:00:00`.  With
  length=0 the previous reserve was 0 and the trim was a no-op,
  so the outro continued to overbook the slot.  The new approach
  inserts the outro temporarily *after* the intro, reads the
  before/after delta of `cc_show_instances.time_filled` to get the
  *actual* smart-block-expanded outro duration, then deletes the
  trial rows by `id > max_id_before` and re-aggregates time_filled
  via a new public helper `ShowInstance::refreshScheduleStatus()`.
  The measured length then feeds both the in-Scheduler reserve
  (layer 3) for time-remaining smart blocks in the autoplaylist
  and the post-loop tail trim (layer 4) for static playlists /
  fixed-time-limit smart blocks.  Approximation note: a dynamic
  smart block in the outro may pick a different track set on the
  second (real) insert than on the trial pass; the variance is
  bounded by the smart block's own length limit and any residual
  overflow is caught by `trimOverbooked` later.

- **Autoloading Playlist: outro silently overbooked the show when
  Intro + Auto + Outro were all configured** (Section 23.19).
  The upstream `AutoPlaylistManager::buildAutoPlaylist()` filled the
  entire remaining slot with the autoplaylist (including any
  time-remaining smart blocks expanded against
  `getSecondsRemaining()`) and only then appended the outro — which
  therefore spilled past the show's end time.  The upstream
  comment in the code even acknowledged it: *"it will always
  overbook shows that have repeat until full enabled"*.  With only
  Intro + Auto the bug was invisible because the loop terminated
  at the ">100 %" check before the entire slot was full.  Fix:
  pre-compute the outro length from `cc_playlist.length` *before*
  the auto-loop (via a direct `CcPlaylistQuery::findPK` Propel
  call — `Application_Model_Playlist` has no public `getDbLength()`
  wrapper, calling it raised a fatal `Error: Call to undefined
  method` and left every Intro+Auto+Outro show empty for an hour of
  polling — fixed before ship), then (a) terminate the auto-loop
  as soon as the unscheduled tail is ≤ the outro length, and (b)
  pass the outro length as a new `reservedSecs` reserve to
  `ShowInstance::addPlaylistToShow($pl_id, $checkPerm, $reservedSecs)`
  so that any time-remaining smart block inside the autoplaylist
  is sized against `(slot − outro)` instead of the full slot.  New
  scheduler-side setter `Application_Model_Scheduler::setReservedSeconds($n)`
  subtracts the reserve in `retrieveMediaFiles()` when computing
  the per-call smart-block limit.  Edge case (operator-revised
  2026-05-20): outro length ≥ show slot → **outro is skipped**, the
  autoplaylist still fills the slot (auto > outro priority).  The
  skip is logged at `WARN` level so the operator can find the
  misconfiguration in `legacy.log`.  Throwable-level catch around
  the outro-length read so any future `Error` here cannot empty
  every upcoming show again.

  Smart-block-reserve alone is not enough for two upstream
  expansion paths that ignore the scheduler's `$showLimit`:
  static playlists (every track inserted at full length, no trim)
  and fixed-duration smart blocks (honour their own
  `cc_block.length`, not `$showLimit`).  Both produce a slot that
  is filled (or overbooked) before the outro is inserted.  New
  helper `ShowInstance::trimTailToReserve($reservedSecs)` deletes
  tail items (filter `starts > NOW() AT TIME ZONE 'UTC'` so an
  already-playing track is never touched) until the required
  reserve is free; the auto-loop calls it once before the outro
  insertion.  An earlier draft of the helper used
  `playout_status = 0` as the safety filter — that is the
  "overbooked" marker set by `CcShowInstances::updateScheduleStatus()`
  *after* the schedule pass, and in-slot future tracks have
  `playout_status = 1`, so the original filter matched zero rows
  and silently trimmed nothing in every realistic Intro+Auto+Outro
  test.  The `starts > NOW()` formulation is intent-based
  (don't touch the past) instead of relying on an enum that means
  something different than the helper's safety goal.  This makes the outro fit
  even for static playlists and fixed-time-limit smart blocks at
  the cost of trimming whole tail tracks of the autoplaylist —
  acceptable trade-off because tracks cannot be cut mid-stream
  and the autoplaylist length is operator-chosen, so a slightly
  shorter autoplaylist is a better outcome than an out-of-slot
  outro.

  No schema change.  Affects only the auto-build-1h-before-show
  path; the manual Show-Builder add-from-Library workflow already
  worked because it inserts items one-at-a-time and never tries
  to "fill" a slot.

- **Show-Logo upload silently failed on Windows.**  Selecting a
  logo in Calendar → New/Edit Show → Style and saving completed
  *without* error in the browser but the file was never written to
  `<storage>/imported/<owner-id>/show-images/<show-id>/` and
  `cc_show.image_path` stayed NULL — no DB row in the entire
  installation ever had a logo since RASTATIME setup.  Root cause:
  `ShowImageController::copyFileToStor()` built the destination
  filename via
  `substr($tempFilePath, strrpos($tempFilePath, '/'))` which
  assumes a POSIX upload tempfile like `/tmp/phpXYZ.tmp`.  On
  Windows the upload tempfile path uses backslashes (e.g.
  `C:\Temp\Python\phpD254.tmp`), so `strrpos('/')` returns `false`,
  `substr(s, false)` is coerced to `substr(s, 0)` and returns the
  *entire* path — the resulting "newFileName" embedded a drive
  letter and `@rename()` failed silently.  Replaced with
  `basename($tempFilePath)`, which handles both separators on every
  platform.  No schema change.

- **Dashboard: drag-and-drop from Library into the Playlist /
  Smart-Block editor tabs was silently broken** (only the
  double-click "Add" path worked).  Root cause was in
  `library_showbuilder.js::fnDrawCallback`: it chose
  `connectToSortable` as *either* `#show_builder_table` (Scheduled
  Shows timeline) *or* `.active-tab .spl_sortable` (Playlist /
  Block editor) with an if-else, but in the Dashboard
  (`showbuilder/index.phtml`) `#show_builder_table` is always
  present in the DOM as the initial "Scheduled Shows" tab — so the
  if-branch always won and the Playlist editor was never
  registered as a drop target.  Double-click still worked because
  it bypasses the sortable receive-handler and calls
  `AIRTIME.playlist.fnAddItems()` directly.  Fix: pass both
  selectors as a single comma-separated string to
  `connectToSortable`; jQuery UI resolves each independently and
  delegates the drop to whichever container is the actual visible
  target.  Affects all Library item types (Track, Smart Block,
  Webstream, Line-Input).

### Changed

- **Podcasts → Edit Podcast: Auto-Expiry helper text moved into
  a hover tooltip** (operator request 2026-05-21).  The grey
  inline span next to the days input field
  (`"Episodes expire this many days after download."`) was
  visually noisy and pushed the row width to the right.  Replaced
  with a `?` help-icon at the same position; the same wording
  surfaces as a qtip on hover.  Same hover convention as
  `.album_names.help_icon` already used inside the podcast edit
  dialog, so the visual style stays uniform.  Pure UX change —
  the underlying `auto_expiry_days` semantics are unchanged.
  Files: `application/views/scripts/podcast/podcast.phtml`,
  `public/js/airtime/library/podcast.js`.

- **Calendar New/Edit Show: minor label polishing**
  (operator request 2026-05-19).
  * Templates section: "Save as Template" button moved onto its
    own row below the Load-Template dropdown row for breathing
    room (`margin-bottom: 0.8em` between the two rows).
  * Record section: `Record this show` → `Record this show:`
    (trailing colon for consistency with the other "Name:" /
    "Description:" / "Default Length:" labels).
  * Autoloading Playlist section: `Add Autoloading Playlist ?` →
    `Add Autoloading Playlist?` (removed stray space before `?`).
  * Live Stream Input section: `Use LibreTime Authentication:` →
    `Use RASTATIME Authentication:`.  Hard-coded brand string in
    `AddShowLiveStream` only; the global `PRODUCT_NAME` constant
    stays "LibreTime" per the upstream-sync-tracking comment in
    `constants.php` (2026-05-16) so all other PRODUCT_NAME
    consumers (Powered-by footer, Help/About pages, file-not-
    found API errors, …) are unaffected.  Element id
    `cb_airtime_auth` is unchanged so JS selectors, template_data
    JSON keys and Icecast source-config remain compatible.

- **Calendar New/Edit Show: Templates promoted to a proper
  collapsible section.**  The Template "Load Template" dropdown,
  "Load" button (was "Apply") and "Save as Template" button used to
  live in a raw `<div>` above the "What" section; they're now
  enclosed in a standard `Templates` collapsible section that
  matches the visual pattern of every other section in the dialog
  (What, When, Record, Autoloading Playlist, Live Stream Input,
  Who, Style).  Default state is **collapsed**, in line with the
  other "advanced" sections, so the operator's eye is drawn to the
  required fields (What / When) on open and Templates is reachable
  with one click when needed.  No functional change beyond the
  Apply → Load button rename.
- **Calendar New/Edit Show: Record section is now default-
  collapsed.**  The Record section used to come up expanded
  because of a stale selector in `openAddShowForm()`: the
  legacy hide-list referenced `#schedule-record-rebroadcast`,
  which no longer exists at the top level since the
  record-per-show refactor (Section 23.13) renamed the section
  to `#schedule-show-record`.  Added the correct id to the
  initial-hide list while leaving the legacy selector in place
  as a harmless no-op.  Operator request 2026-05-19.

- **Webstream "Default Length" now accepts seconds** (Section 23.17).
  The Webstream edit dialog's Default-Length field previously
  validated only `HH+MM` (e.g. `01h 05m`) and silently dropped any
  sub-minute precision.  It now also accepts an optional seconds
  component (e.g. `01h 05m 05s`), matching the granularity of the
  Line-Input dialog so an operator preparing a short, time-critical
  stream entry no longer has to round to whole minutes.  Backwards-
  compatible (`01h 05m` without the seconds suffix is still valid by
  operator decision 2026-05-19).  The Edit-dialog readback always
  shows all three components, including zero seconds, for visual
  consistency (operator decision 2026-05-19).  The Library list shows
  the same `HHh MMm SSs` formatting because `LengthFormatter`
  pass-through preserves the Webstream-specific string unchanged.
  Scope: `Application_Model_Webstream` only — Line-Input and Smart
  Block were already seconds-aware; consolidating the three
  independent parsers into a shared helper was deferred (operator
  decision 2026-05-19, "nur Webstream anfassen").
  DB: `cc_webstream.length` is a Postgres `interval` so it already
  carries seconds at the storage layer — no migration needed; pre-
  2026-05-19 rows come back as `HH:MM:00` from the driver and
  validate as `00s` in the Edit dialog.

### Fixed

- **Auto DJ: shortening an auto-created show failed with
  "Cannot schedule overlapping shows", End-Time displayed one
  minute too early** (Section 23.20 v6, 2026-05-21).  Both
  symptoms shared one root cause: the gap returned by
  `findNextGap()` carries sub-minute timestamps (the preceding
  Operator show often ends at `:34` or similar due to
  crossfade-rounding), so the auto-created show inherited
  sub-minute `starts` / `ends` / `start_time` / `duration`
  values.  The Edit-Show form works at minute granularity and
  could not round-trip those values cleanly — End-Time
  rendered one minute short of the real end (16:59 for a
  17:00:00 ends), and `AddShowWhen`'s overlap-check refused
  to save a shortened version of the show because the form's
  recomputed end timestamp shifted relative to the original
  `cc_show_instances` row.  Fix in
  `AutoDjService::createGapFillingShow()`: round the gap
  start UP to the next whole minute (never earlier than the
  gap start, protects the preceding show) and round the gap
  end DOWN to the previous whole minute (never later than the
  gap end, protects the following show).  Shows now have
  whole-minute starts / ends / durations and survive the
  Edit-Show round-trip.  Forfeits at most ~59 s at each end
  of a gap.  If the rounded gap drops below the 60 s minimum
  the show is skipped.

- **Auto DJ: Edit-Show dialog showed wrong start/end time for
  auto-created shows** (Section 23.20 v5, 2026-05-21).  v3/v4
  wrote `cc_show_days.start_time` and `.timezone` as UTC,
  which made the calendar render correctly (because
  `cc_show_instances.starts` is the authoritative UTC
  timestamp and the calendar converts that to local) but the
  Edit-Show dialog reads the operator-local representation
  from `cc_show_days` directly — on a UTC+2 system an
  Auto-DJ show created for 15:08 local was displayed as 13:08
  in Edit-Show (and 14:59 as End Time for the 17:00 end).
  Fix: convert the UTC gap-start to the operator's
  `Application_Model_Preference::GetDefaultTimezone()` and
  store both `start_time` and `timezone` in that zone, the
  same convention `ShowService::setCcShowDays()` uses.  The
  `cc_show_instances.starts/ends` columns keep storing UTC.
  No schema change; only auto-created shows are affected.

- **Auto DJ chopped long gaps into a chain of 1–4 min sub-shows**
  (Section 23.20 v4, 2026-05-21).  `findNextGap()` bounded its
  Postgres query by `starts < lookahead_end` (= `NOW() + 1h`),
  which silently broke any gap whose follow-on show started
  beyond the lookahead window.  Example from operator's log:
  poll at 13:31:51 saw the 14:07–15:00 gap (53 min) but did
  NOT see the 15:00 show that bounds it (outside lookahead),
  so the cursor walked to `lookahead_end` (14:31:51) and the
  tail-gap branch returned a 25-min gap.  60 s later the next
  poll saw the rest (14:31:51–14:32:51) and created a 1-min
  show, and so on for 17 polls.  Fixed by widening the query
  to ALL upcoming instances (with a 200-row safety LIMIT) so
  the cursor sees the real next-show boundary, while still
  enforcing the operator-Q1 "only auto-create a show whose
  gap STARTS inside the lookahead window" rule.  The 12 h
  show-length cap in `createGapFillingShow()` still applies
  for the (mostly theoretical) "empty for a whole day" case.

- **Auto DJ Settings: Logo preview rendered as an `<img>`
  instead of a raw filesystem path.**  Previous version
  displayed the absolute server path in a `<code>` block; the
  browser cannot fetch absolute server paths so the operator
  had no visual confirmation that the upload actually
  produced a usable image.  Now the controller reads the
  configured logo file via `file_get_contents()` + base64,
  packages it as a `data:` URI and the view renders it as an
  `<img>` (max 200×200 px) — same pattern as
  `ShowFormService::imagePathToDataUri()` already uses for
  per-show logos.

- **Auto DJ pre-pass still failed after v2 — rewritten to direct
  Propel insertion** (Section 23.20 v3, 2026-05-21).  v2 swapped
  the auth storage to `Zend_Auth_Storage_NonPersistent` to dodge
  the session-write strict-mode guard, but
  `ShowService::addUpdateShow()` touches *additional* session-
  backed state internally (RabbitMQ helpers, intro/outro
  lookups, UserService construction) that ALSO trips the guard
  from a polling-job context — every poll continued to log
  `"You must explicitly start the session with Zend_Session::start()"`
  and no gap-filling show was ever created.  v3 abandons the
  ShowService path entirely and writes the three required rows
  (`cc_show` + `cc_show_days` + `cc_show_instances`) via Propel
  setters in a single transaction.  These are the only rows
  AutoPlaylistManager's `_upcomingAutoPlaylistShows()` query and
  the calendar event-feed need to find the show; no hosts, no
  rebroadcasts, no linked-show machinery — Auto-DJ shows stay
  intentionally bare.  Removed the `withAdminContext()` helper
  along with the unused ShowService dependency.  No schema
  change.

- **Auto DJ pre-pass crashed on every poll with "must explicitly
  start the session with Zend_Session::start()"** (Section 23.20
  v2, 2026-05-21).  v1 of `AutoDjService::withAdminContext()`
  swapped the Zend_Auth identity by writing into the *current*
  session storage adapter (`$auth->getStorage()->write($info)`).
  The polling-job context (PageLayoutInitPlugin) had read the
  session but not opened it for writing, so the write attempt
  hit Zend's strict-mode session guard and threw on every
  60 s poll — gap-filling shows were never actually created.
  v2 swaps the *storage adapter itself* for a
  `Zend_Auth_Storage_NonPersistent` (in-memory only) and
  restores the original adapter on exit (incl. via `finally`).
  No session is touched and the admin identity exists only for
  the duration of the show-create call — invisible to every
  other concurrent request.

### Added

- **Auto DJ Settings: "Show Logo" help-icon tooltip.**
  Added a `.help_icon` tooltip next to the "Show Logo" label
  carrying "Upload a JPG / PNG / GIF (max 2 MB)." — same
  pattern as the "Default Playlist" tooltip introduced in v3.

- **Auto DJ Settings UI polish** (Section 23.20 v4,
  2026-05-21).  Cumulative cosmetic pass after operator
  testing:
  * Tooltip-icon class unified to `.help_icon` (the same PNG
    "ⓘ" glyph used by `stream_username_help_icon` in
    Settings → Streams), no more inline unicode character.
  * Tooltip on "Default Playlist" carries both the short
    "what's this for" sentence and the longer "use a Smart
    Block with Limit to: Time remaining in show" tip — the
    tip used to be a paragraph under the dropdown but the
    hover surface is cleaner.
  * Colour-input labels trimmed to "Background Color" /
    "Text Color" (was "… (6-digit hex, without #)").
  * "No default logo set …" sentence moved below the Upload
    button so the upload-flow is the first thing the
    operator sees when the field is empty.
  * Button labels shortened to "Upload" / "Save".

- **Auto DJ Settings UI tweaks** (Section 23.20 v3,
  2026-05-21).  "Default Playlist" now appears as the first
  field inside "Auto DJ Show Defaults" (previously buried
  between the colour pickers and the fill-checkbox).  Long
  in-line label "Default Playlist (used as autoplaylist for
  created shows)" trimmed to just "Default Playlist" with a
  small ⓘ icon next to it — hovering opens a qtip tooltip
  with the longer explanation, same pattern as the
  `show_record_help_icon` in the Calendar's New-Show dialog.

- **Auto DJ: extended show-detail defaults** (Section 23.20 v2,
  2026-05-21).  Five additional cc_pref keys plus matching
  Settings → Auto DJ form fields so the operator can pre-stamp
  every auto-created show with URL, Genre, Description,
  Background Color and Text Color.  The values are passed
  straight through to `ShowService::setCcShow` and end up on
  the new cc_show row.  Empty defaults are safe — Propel just
  stores them as NULL/empty.  Form section renamed from
  "Defaults" to "Auto DJ Show Defaults", "State" to "Status",
  "Default Auto DJ Show Name" to "Show Name", and the
  Show-Logo upload moved from its own section into the
  Auto-DJ-Show-Defaults section as the final field.

- **Auto DJ** (Section 23.20).  New Settings → Auto DJ page plus
  a service that auto-creates and auto-fills shows in calendar
  gaps.  Operator workflow:
  1. Configure under Settings → Auto DJ:
     * **Enabled** (master switch)
     * **Default Auto DJ Show Name** (e.g. "Auto DJ")
     * **Default Playlist** (any cc_playlist; recommended: a
       playlist that wraps a smart block with
       "Limit to: Time remaining in show" so the slot fills
       exactly — same trick that powers Section 23.19)
     * **Automatically fill any show** (also tops up shows that
       end up incomplete after the per-show autoplaylist build)
     * **Default Auto DJ Show Logo** (uploads to
       `<storage>/imported/<owner>/auto-dj-logos/`)
  2. Every 60 s — same cadence as `AutoPlaylistManager` — the
     pre-pass scans the next hour of the calendar for the first
     unscheduled gap ≥ 60 s and auto-creates a single
     non-repeating show inside it, capped at 12 h length.  The
     new show has `has_autoplaylist = true` so the existing
     autoplaylist build loop in the same poll cycle picks it up
     and fills the slot.
  3. After the build loop, the fill-pass walks the next hour of
     upcoming instances; any whose unscheduled tail is more than
     5 s gets a final `addPlaylistToShow($auto_dj_playlist)`
     pass.

  Architecture notes:
  * No schema change.  Five new keys in `cc_pref`
    (auto_dj_enabled, auto_dj_show_name, auto_dj_playlist_id,
    auto_dj_fill_any_show, auto_dj_logo_path).
  * New `Application_Service_AutoDjService` is the central
    place.  Two public entry points (`runPrePass`, `runFillPass`)
    are called from
    `AutoPlaylistManager::buildAutoPlaylist()` — bookending
    the existing per-show build loop.
  * Programmatic show creation goes through
    `Application_Service_ShowService::addUpdateShow()` under
    `Zend_Auth` admin-context swap (via
    `Application_Model_User::getFirstAdmin()`) because that
    service hard-rejects non-Admin/PM callers.
  * Show defaults: no recording, no rebroadcast, no host, no
    intro/outro override, no linking — strictly minimal filler
    shows.
  * Logo upload re-uses the show-image MIME validation pattern
    (JPG/PNG/GIF, 2 MB client-side limit) but persists a single
    global path rather than per-show.

- **Line-In entries in Playlists** (Section 23.18, migration 0054).
  Operators can now drop a Line-In item from the Library into a
  Playlist editor (Doppelklick or drag-and-drop), the same way
  Tracks, Smart Blocks and Webstreams already worked.  When the
  Playlist is later scheduled into a Show, the Line-In slot becomes
  a live-source switch on the playout side — same end-result as if
  the operator had scheduled the Line-In directly into a Show
  (which was the only path before).
  * Migration 0054 adds `cc_playlistcontents.linein_id INTEGER`
    (no hard FK to `rastatime_linein` — Django/Propel ownership
    boundary, same call as `cc_schedule.linein_id` in migration
    0047).
  * New `cc_playlistcontents.type = 3` discriminator (was 0=file,
    1=stream, 2=block before).  Watch out: the SCHEDULE-side type
    enum is different (file=0, stream=1, linein=2); the Scheduler
    maps playlist-type 3 → schedule-type 2.
  * `Playlist::buildEntry()` gains a `linein` branch that fetches
    `rastatime_linein` via raw SQL (Propel skip-regen pattern, same
    as Webstream `input_gain_db`).  Default slot length 30 min when
    the Library record left `length` NULL.
  * `Playlist::insertPlaylistElement()` saves the row via Propel for
    the common fields, then writes `linein_id` via a follow-up raw
    SQL UPDATE (the Propel `CcPlaylistcontents` model was not
    regenerated for the new column).
  * `Playlist::getContents()` gains a fourth `UNION ALL` arm
    joining `rastatime_linein` so the Playlist editor sees Line-In
    rows alongside files / streams / blocks.
  * `Scheduler::scheduleItemsInPlaylistBranch` (the `type === 'playlist'`
    branch) gains a `type == 3` mapping that produces a schedule
    row with `type = 2` (linein) and zero-length fades — fades on a
    live mic source make no sense.
  * `update.phtml` renders the Line-In row with a disabled signal
    icon (no browser preview is possible for a server-local
    hardware input).
  * Doppelklick + DnD already worked because the Library already
    classified `ftype === "linein"` as `lib-stream` (same CSS class
    as Webstream) and the Library toolbar / DnD glue does not
    filter by item type.  The only thing that was blocking the
    flow was the server side throwing "Unknown file type" in
    `Playlist::buildEntry()` — that's now handled.

- **Show Templates.**  New feature for reusing show configurations
  across the Calendar's New-Show dialog and a Settings page.
  Operator workflow:
  1. Fill in a show's fields in the **New Show** dialog (name, URL,
     genre, description, duration, repeats, days, end date, record
     flag, autoloading playlist trio, auth flags, host list, BG /
     text colour, logo path).
  2. Click "Save as Template" — the show name becomes the template
     name (with overwrite-confirmation if the name already exists).
  3. Next time a New Show is opened, pick the template from the
     "Load Template" dropdown and click "Apply" — every captured
     field is populated.  Start date / start time are deliberately
     left alone so a click into the calendar still wins.
  4. The Settings → "Show Templates" page lists every template
     and allows rename / delete.

  Architecture & decisions (Section 23.16):
  * New table `cc_show_template` (migration 0053) with
    `template_data JSONB` snapshot.
  * Templates are **station-wide** (no per-user filter).
  * One-way stamp model: editing a template does NOT propagate to
    existing shows; templates are just blueprints.
  * `cb_custom_auth` live-stream password is **explicitly excluded**
    from the template payload (security).
  * Hosts are stored as `cc_subjs.login` strings, not as surrogate
    IDs, so a template survives the deletion-and-recreation of a
    user; missing logins at apply-time are silently skipped with
    an `INFO`-level log.
  * Show logo is stored as a path reference to the existing file
    in `cc_files`; if the source image is later deleted the
    template loses its image (operator's explicit choice 2026-05-19
    to keep storage flat).
  * Schema drift on `cc_show`: missing fields in older templates
    fall back to the show-form defaults at apply time; superfluous
    fields are silently ignored.  Operator-confirmed strategy
    "use defaults, manually refresh templates if needed".
  * Five new JSON actions on `ScheduleController`: list / get /
    save / rename / delete; the New-Show dialog and the Settings
    page share the same backend.
  * UI is rendered in **New-Show and Edit-Show** dialogs (operator
    follow-up 2026-05-19); deliberately omitted from the
    **Edit-Instance** dialog because a single repeating-show
    instance is a per-occurrence override and re-stamping it with a
    template would either silently propagate to the linked siblings
    or have no visible effect on them — both confusing.  In
    Edit-Show, Apply re-stamps the in-flight form values from the
    chosen template but does NOT auto-submit — the operator still
    has to click "Update show".  `start_date` / `start_time` are
    still skipped (one-way stamp model — Apply must never silently
    reschedule an existing show).

### Fixed

- **Show Templates: Apply inverted the "Repeats?" checkbox.**
  jQuery 1.8.3's default-action simulation for click events on form
  controls toggles the native checked state of a checkbox *after* the
  user handlers run.  The earlier `setCheck()` did
  `$el.prop("checked", on).trigger("click")` which (1) set the desired
  value, then (2) ran the existing click handler (which toggled the
  visibility fieldset correctly), then (3) the default-action
  simulation flipped the checkbox state back — leaving the box
  un-checked but the repeat-options fieldset visible.  Replaced the
  trigger-based approach with a single `prop("checked", on)` per
  field plus a new `syncDependentVisibility(form)` pass at the end of
  `applyShowTemplate()` that recomputes all toggle-driven UI sections
  (Repeats, Record/Rebroadcast, Autoplaylist, Custom auth, End-date,
  Repeat-type → day-picker / monthly-picker).
- **Show Templates: Linked-show state was sometimes lost after Apply.**
  Symptom of the same `.trigger("click")` problem above (linked was
  also a setCheck), plus an ordering issue: `add_show_record` was set
  *after* `add_show_linked`, and Record's click handler force-clears
  + disables Linked as a domain rule (a recorded show cannot be
  linked).  Both fixed in the single sync pass at the end of
  `applyShowTemplate()`, which evaluates the post-write Record state
  exactly once.
- **Show Templates: Add-this-Show stopped working after Save-as-
  Template.**  The two template-control buttons live inside
  `<form id="add-show-form">`; their click handlers did not stop
  propagation, so the click bubbled into the form and (depending on
  browser timing) left the form in a state where the subsequent
  Add-this-Show / Update-show click was discarded.  Added explicit
  `event.preventDefault() + event.stopPropagation() + return false`
  to both `#show-template-apply` and `#show-template-save` click
  handlers, and pinned the Save-as-Template payload to
  `$("#add-show-form").serializeArray()` instead of the broader
  `$("form")` selector that could pick up sibling forms on the page.

- **Smart Blocks: "Allow only tracks with expiry date" checkbox.**
  New entry in the Smart Block edit dialog's Advanced Options,
  directly under "Allow only tracks not played yet".  Adds a
  `WHERE cc_files.expires_at IS NOT NULL` filter to the candidate
  pool, restricting the block to perishable content (dated news
  segments, time-limited trailers, podcast episodes with auto-
  expiry).  Pairs naturally with the new "Earliest expiry first"
  sort: enable both for a block that always airs the most-urgent
  short-lived content first.  Persisted as a single
  `cc_block_criteria` row with `criteria='only_with_expiry'`
  (`value='0'/'1'`) — same pattern as `only_unplayed`.  Default off;
  backwards-compatible (missing row treated as off).
- **Smart Blocks: shortened "Allow only tracks not played yet"
  label** (was "Allow only selecting tracks not played yet") to
  match the new sibling checkbox's pattern and reduce visual noise
  in the Advanced Options panel.

- **Smart Blocks: "Earliest expiry first" sort option.**  New entry
  in the Smart Block edit dialog's Advanced Options → Sort Tracks
  dropdown, alongside "Randomly", "Newest", "Oldest", "Most
  recently played" and "Least recently played".  Sorts the
  candidate-pool query by `cc_files.expires_at ASC NULLS LAST`:
  tracks with the closest expiry date are picked first so the
  Smart Block airs them before the hourly pruner auto-disables
  them; tracks without an expiry go to the end of the queue so
  they do not dilute the air-before-expiry intent.  `filepath` is
  used as a stable secondary sort key for tracks sharing the same
  expiry second (e.g. a batch of episodes auto-expired by the same
  podcast setting).  Pairs naturally with the existing Track-Expiry
  / Podcast Auto-Expiry feature (ARCHITECTURE 23.11).

- **Smart Blocks: "Allow only selecting tracks not played yet"
  checkbox.**  New entry in the Smart Block edit dialog's "Advanced
  options" section (between "Allow last track to exceed time limit"
  and "Sort Tracks").  When enabled, the SQL projection in
  `Block::getListofFilesMeetCriteria()` adds a
  `WHERE cc_files.lptime IS NULL` filter, restricting the candidate
  pool to tracks the playout has never logged.  Useful for
  discovery / new-content-rotation blocks.  Persisted as a single
  `cc_block_criteria` row with `criteria='only_unplayed'`,
  `value='0'/'1'` — same pattern as the existing `repeat_tracks` and
  `overflow_tracks` toggles.  Default off; backwards-compatible with
  existing blocks (missing row treated as off).

- **Per-podcast default Track-Type.**  New dropdown "Track Type:" in
  the New / Edit Podcast dialog.  When set, every episode imported
  from that podcast (manual download or auto-ingest) gets
  `cc_files.track_type_id` pre-filled with the chosen value at
  download time, independent of the analyzer's ID3-based inference.
  Empty = no override (existing behaviour).  Existing already-imported
  episodes are not retroactively changed.
  Implementation pattern mirrors the Auto-Expiry feature
  (migration 0049 / 2026-05-16):
  * New column `imported_podcast.default_track_type_id` (FK to
    `cc_track_types.id`) via migration 0050.
  * Python model + `download_episode()` get the optional kwarg.
  * PHP `PodcastService` reads/writes the column via raw SQL
    (Propel regen not yet pulled).
  * Frontend `podcast.phtml` renders the dropdown options from the
    `podcast.track_type_options` field that
    `PodcastService::getPodcastById` now embeds directly into the
    podcast JSON payload — `Application_Model_Tracktype::getTracktypes()`
    is queried server-side once per editor open, no extra REST
    round-trip and no fragile `<script>` tag inside server-rendered
    HTML that is later injected via jQuery's `.html()`.

### Fixed

- **Library context-menu "Publish..." item re-enabled.**  Was
  hard-disabled upstream as part of the
  [LibreTime issue #1320](https://github.com/libretime/libretime/issues/1320)
  podcast-feature lockdown (which targeted the
  SoundCloud-integration and the Celery/RabbitMQ paths — neither of
  which exist in RASTATIME).  Now restored as a normal entry next
  to "Delete" and "Edit..." in the file context menu.  The Library
  toolbar's "Publish" button already worked the same way; both
  paths bottom out in `AIRTIME.publish.openPublishDialog`.

- **Publish-to-Station-Podcast: every save threw HTTP 400 with no
  episode created.**  `Application_Service_PodcastEpisodeService::
  publish()` called `_buildEpisode($id, $url, $guid, date('r'))`
  without passing `$title` or `$description`, so both got the
  default `null` and PostgreSQL rejected the INSERT with
  SQLSTATE[23502] (`NULL-Wert in Spalte »episode_title« ... verletzt
  Not-Null-Constraint`).  Now reads `cc_files.track_title` (fallback
  to `cc_files.name`, last-resort `"Track <id>"`) for the title and
  `cc_files.description` (fallback to `""`) for the description and
  passes both into `_buildEpisode`.  Existing call sites for
  RSS-feed-imported episodes were already passing real values and
  are unaffected.

- **Edit Track form: silent save-everything-fails when no Track-Type
  is chosen.**  `FileDataHelper::sanitizeData()` ran
  `intval($data['track_type_id'])` on the POSTed value, which
  collapses the empty-string placeholder (`''` = "Select a Type" in
  the Edit-Track dropdown) to `0`.  But `0` is not in the dropdown's
  Multi-Options list (valid IDs start at 1), so Zend's `InArray`
  validator silently rejected the WHOLE form.  Result: the dialog
  closed as if "Save" had worked, but NO field (Expiry, Description,
  Genre, etc.) was actually persisted, for every track without a
  chosen Track-Type.  Discovered while debugging a report that the
  Expiry field disappeared after save — turned out to be a much
  bigger bug that just nobody noticed because most tracks carry a
  Track-Type.  `sanitizeData` now keeps empty/null as an empty string
  (matches the placeholder option), and the existing
  `StoredFile::setDbColMetadata` mapping converts that back to `NULL`
  at DB-write time, so the storage shape is unchanged.  Also added a
  `WARN`-level log of `Zend_Form::getMessages()` on validation
  failure in `editFileMdAction` so the next silent-validation bug
  leaves a breadcrumb in `legacy.log`.
- **Edit Track form: `expires_at` UPDATE was a no-op on PostgreSQL.**
  The raw-SQL UPDATE that writes the operator-entered Expiry date
  reused the same `:exp` named placeholder twice (once for the value,
  once for the `disabled` flag's comparison).  PostgreSQL's PDO with
  native prepared statements (`ATTR_EMULATE_PREPARES=false`, the
  default) rejects same-name double-bound placeholders, the
  prepare/execute silently failed, no DB row was updated, no
  exception bubbled up.  Split into two distinct placeholders
  (`:exp_set` / `:exp_cmp`) that get bound to the same value;
  semantically identical SQL, but PDO now accepts it.  Latent bug
  that would have surfaced once the Track-Type validation fix above
  let the save actually reach this code path.

- **Smart Block: adding a dynamic block to a show timed out with
  HTTP 500 and the show stayed empty.**
  `Block::getListOfFilesUnderLimit()`'s "repeat tracks until limit
  reached" loop had no safety against the case where no remaining
  track fits the time-left budget (overflow off, shortest track in
  pool > time-to-limit).  `addTrack()` silently no-ops, `totalTime`
  stops growing, the `while` predicate never flips, PHP spins
  forever, mod_fcgid eventually kills it on its pipe-read timeout
  (~40 s), and the caller gets HTTP 500 with zero diagnostics in
  `legacy.log` because no `Throwable` is ever raised.  The
  operator's report 2026-05-18 triggered it with a Smart Block on
  two ~30-min episodes, 4 h limit, repeat=on, overflow=off — two
  tracks at a time cannot fill the residual cleanly.  Bounded the
  loop two ways: (a) precompute the minimum track length in the
  pool and bail out as soon as `(blockTime - totalTime) < minLen`
  since no track can ever fit again; (b) a hard 1000-iteration
  spin-guard as paranoia fallback that emits a `WARN` if it ever
  trips.  Pre-existing upstream LibreTime bug; not a RASTATIME
  regression.
- **showbuilder/schedule-add: PHP `Error` (not just `Exception`)
  now surfaces in operator log.**
  `ShowbuilderController::scheduleAddAction` only caught `Exception`,
  so PHP 7+ `Error` instances (`TypeError`, undefined-method, etc.)
  bubbled up as opaque HTTP 500 with no log entry.  Now catches
  `Throwable` (covers both) and logs class name + file + line +
  full stack trace.  Also bumped the request-parameter
  `Logging::debug` to `Logging::info` and added a `Logging::info('
  success')` marker on the happy path so every schedule-add is
  greppable in `legacy.log` for future diagnostics.

- **Calendar — New/Edit Show: DJs / Hosts selected under "Who" were
  silently dropped on save.**  The "Schedule" form submit used
  `$(...).attr("checked")` to extract checkbox state for the hosts
  list, days-of-week list, and several rebroadcast / record / live-
  link toggles.  Since jQuery 1.6 `.attr("checked")` returns the
  static HTML attribute (i.e. only the initial state, typically
  undefined), not the runtime DOM property — so every user-toggled
  checkbox was treated as unchecked at submit time.  Switched all
  19 affected sites in `add-show.js` to `.prop("checked")` / `.prop
  ("checked", true|false)`.  Fixes the DJ-save bug and likely also
  several latent rebroadcast / record / linked-show toggle bugs that
  no one had reported yet.
- **Calendar — Schedule Tracks dialog now always opens on the
  "Tracks" tab.**  Upstream picked whichever Library tab the
  operator was on most recently (via `location.hash`), so a previous
  click on Playlists / Smart Blocks / Webstreams / Podcasts persisted
  into the dialog.  `highlightMediaTypeSelector` in `schedule.js`
  now explicitly sets `#tracks` on every dialog open.
- **Calendar — Edit Show (non-repeating): renaming silently dropped
  due to locale-dependent `strftime` time format.**  The Propel-
  generated `BaseCcShowDays::getDbStartTime()` defaults to format
  `'%X'` ("preferred time representation"), which is locale-
  dependent.  On a 12-hour-clock locale (en_US default) `'%X'`
  applied to a start_time of `00:00:00` returns the string
  `"12:00:00 AM"` instead of `"00:00:00"`.  Callers that did
  `explode(':', $row->getDbStartTime())` then read the hour as
  `"12"` instead of `"0"`, and
  `Application_Service_ShowService::getInstance()` looked up the
  cc_show_instances row at 12:00 local time (10:00 UTC) instead of
  00:00 local time (22:00 UTC of the previous day).  The lookup
  failed, `createNonRepeatingInstance` threw "Could not find show
  instance with start time: ...", and the entire transaction rolled
  back — including the just-written name update.  The operator saw
  the dialog close successfully, but on reopen the old name was
  back.  Fixed by overriding `getDbStartTime()` in the
  hand-written `CcShowDays` subclass to default to the unambiguous
  24-hour `'H:i:s'` format.  One-line fix that corrects all 29+
  call sites in the codebase without touching Propel-generated
  code (which a future schema regen would overwrite).

- **Calendar — "Edit Instance" dialog: show name stays read-only.**
  The show name lives on cc_show (one row per series), not on the
  per-instance cc_show_instances row, so a name change made from
  the "Edit Instance" dialog would silently rename every other
  instance of the series too — confusing because the operator only
  opened the dialog for one specific instance.  `AddShowWhat::
  makeReadonly()` now greys out `add_show_name` along with every
  other "What" field.  Operators who want to rename the whole
  series use the separate "Edit Show" menu entry (which routes
  through editShowAction / addUpdateShow / setCcShow and now
  works correctly thanks to the getDbStartTime fix above).
- **Podcasts: imported episodes showed "0 sec" in the Library.**
  The Library DataTable computes a track's displayed length as
  `cueout - cuein` (StoredFile.php SQL projection), not by reading
  `cc_files.length` directly.  The standard analyzer pipeline sets
  `cue_in=0` and `cue_out=length` at import time so the subtraction
  yields the real length.  `download_episode()` bypassed the
  analyzer and forgot to set them, so every podcast episode showed
  `0:00` in the Library (Calendar ShowContent, which reads `length`
  directly, was correct).  Now sets `cue_in=0` and
  `cue_out=length` at episode import.  Migration
  `0052_backfill_podcast_cuein_cueout` back-fills the same two
  columns on every existing podcast-referenced cc_files row with
  NULL cuein/cueout — limited to rows referenced by
  `podcast_episodes.file_id` so non-podcast files with deliberately
  empty cue points (e.g. webstreams) are not disturbed.

- **Podcasts: episodes whose download failed were stuck on the
  spinning "downloading" icon forever.**  When the PHP frontend's
  synchronous `/api/v2/podcast-episodes/{id}/download` call returned
  an error, `_download()` just `return`ed without touching the
  placeholder `podcast_episodes` row that `addPlaceholder()` had
  just inserted — so the row stayed with `file_id IS NULL`, and the
  UI's `_getImportedPodcastEpisodeArray()` reported `ingested=-1`
  (pending) indefinitely.  Removing the stuck placeholder on failure
  flips the UI back to "not imported" so the operator can simply
  click Download again.  Already-imported episodes (`file_id` set)
  are never touched.  Migration `0051_cleanup_stuck_podcast_episodes`
  also one-shot deletes any rows that accumulated BEFORE this fix
  went in, so the operator's library does not stay polluted with
  permanently-spinning ghosts (`DELETE FROM podcast_episodes
  WHERE file_id IS NULL`).

### Changed

- **Edit Show form — Record section help-icon text shortened** from
  the long "When enabled, the show's on-air output..." paragraph to
  "When enabled, the Show is recorded to the folder configured in
  Settings → Local Machine".

- **Record-per-Show: recorder now writes its FFmpeg stderr to a
  per-recording log.**  Previously the recorder's subprocess sent
  stderr to `DEVNULL`, so a mid-show crash (rc=3419392776 in a
  recent test) left no diagnosable trace — only the playout's own
  log saying "already exited".  Now each `start()` opens
  `C:\rastatime\logs\ffmpeg-recorder-show<id>-<YYYYMMDD-HHMMSS>.log`
  and writes the full FFmpeg command line as a header, then captures
  every stderr line for the lifetime of that recording.  On
  non-zero exit the playout log now also includes the last ~2 KB of
  stderr inline so the failure is visible without hunting for the
  log file.  Pattern lifted 1:1 from `FfmpegStreamer` and
  `FfmpegLineinCapture` so all three FFmpeg subprocess types share
  the same log-dir convention (`RASTATIME_LOG_DIR` env override).

### Fixed

- **Record-per-Show: long source-switch gaps (~16 s) still produced
  short recordings.**  The mid-show watchdog poll-interval was 5 s
  and respawned the recorder exactly once per detected death.  When
  the recorder respawn _also_ died within the early-death window
  (e.g. `/rastatime` returning 404 because the Line-In Capture
  Tascam-race was still failing during a master->scheduled switch),
  the outer 5 s poll meant another 5-7 s of lost audio before the
  next attempt.  Two tightenings:
  * Poll interval 5 s -> 2 s so the watchdog notices a death within
    a few seconds.
  * Inner retry loop on each respawn: up to 8 attempts with the same
    3 s early-death window and 1 s backoff as the initial-start
    retry, so up to ~32 s of source unavailability are bridged
    without falling back to the outer poll.  Sufficient for the
    longest observed source-switch gap (~16 s for scheduled<->master
    with Line-In Capture flake).

- **Record-per-Show: recording was truncated when the upstream source
  briefly dropped mid-show.**  When `/rastatime` had a transient
  source-loss (Webstream AAC decode error + mpv reconnect,
  scheduled→master switch, Icecast hiccup, FFmpeg-streamer restart),
  the recorder's `-reconnect_*` flags gave up after roughly 3 reconnect
  rounds (~10 s of tries) and FFmpeg exited cleanly with rc=0.  The
  resulting .mp3 ended at the moment the drop started — operators saw
  11-second files from 5-minute shows (193) or 2:34 from 5:00 (194).
  Replaced the one-shot retry thread with a full per-show lifecycle
  thread in `playout_scheduler._show_record_lifecycle`: phase 1 is the
  existing initial-start retry (Line-In warmup 404 window); phase 2 is
  a new mid-show watchdog that polls FFmpeg every 5 s and, on death,
  respawns it in MP3-**append-mode** so the new segment concatenates
  byte-by-byte onto the same .mp3 (MP3 is frame-based and has no
  container header when written with `-write_id3v2 0 -write_xing 0`,
  so no post-processing is needed — every player decodes the joined
  file end-to-end).  The watchdog retries unlimited until SHOW_RECORD_END
  per operator decision; a dauerhaft source-loss log-spams once per
  5 s but the recording resumes the moment Icecast is back.
- **FfmpegLineinCapture: sporadic immediate-death on first dshow open
  killed Line-In shows.**  Tascam USB-audio + Windows dshow occasionally
  fails the very first open with rc=0xCCCC1008 — a known
  kernel-driver-handle-release race.  Added an initial-spawn retry
  (max 3 attempts, 1 s backoff) inside `FfmpegLineinCapture.start()`
  so a single transient failure is recovered before the Line-In show
  starts.  Distinct from the existing post-start watchdog (which only
  kicks in once the capture has been healthy at least once).

- **Record-per-Show: Line-In recordings reliably produced no file
  because FFmpeg gave up after 3 initial-open 404s.**  FFmpeg's HTTP
  demuxer has a hard 3-attempt limit on `avformat_open_input` when
  the server returns an HTTP error; the `-reconnect_*` flags only
  apply AFTER a successful connection.  The Line-In source warmup
  (FfmpegLineinCapture spawn + dshow handshake + mpv attach + 3
  streamer spawns) takes ~1.5-2 s, during which `/rastatime` returns
  404 — the entire 3-retry window expires inside the warmup.  Added
  a Python-side retry thread in `playout_scheduler._on_show_record_start`
  that respawns the recorder if it dies within a 3-second
  early-death window, up to 8 attempts (~32 s total).  The thread
  aborts cleanly if a back-to-back follow-up show has taken over
  the recorder slot.  Required two small `FfmpegRecorder` API
  additions: `current_show_id` property (so the retry thread can
  tell "died" apart from "another show took over") and idempotent
  cleanup of stale state in `start()` when called after a previous
  attempt died asynchronously.  No effect on file / webstream shows
  — those connect on the first attempt and the retry loop returns
  immediately.

- **Record-per-Show: Line-In show recordings silently crashed mid-show.**
  When a Line-In show followed another show, the playout engine's
  source-switch tore down and respawned the three FFmpeg streamers
  from scratch, leaving the `/rastatime` Icecast mountpoint without a
  source for ~2 seconds.  The recorder's FFmpeg saw an EOF on the
  body stream and the default behaviour is to terminate (exit code
  3419392776 in the log).  The recording file ended up zero bytes /
  missing.  Added `-reconnect_at_eof 1` and
  `-reconnect_on_network_error 1` to the recorder command so it
  rides out short Icecast gaps the same way the source-side mpv
  engine already does (those flags were already on mpv's
  `stream_lavf_o` line but missing from the recorder).
- **Record-per-Show: recording typically ~500 ms short of show length.**
  At SHOW_RECORD_END the recorder was stopped synchronously, so the
  tail of the Icecast output that had already been pushed by the
  streamer but not yet consumed by the recorder was lost.  Added a
  1-second post-roll: the deferred stop checks `stop_if_recording
  (show_id)` so a back-to-back follow-up recording is never
  interrupted by the previous show's post-roll timer.

- **Record-per-Show: filename used UTC instead of local time.**  The
  scheduler hands `show_starts_at` to the recorder as a naive UTC
  datetime, and `build_output_path()` formatted it directly — a show
  scheduled at 13:00 local time (Europe/Berlin, CEST = UTC+2) ended
  up as `... 11-00 - <show>.mp3` on disk, off by the operator's UTC
  offset.  Re-attached UTC tzinfo and called `.astimezone()` to
  render in the system's local timezone.  DST-safe: a 13:00 show
  produces `13-00` in both summer (CEST = UTC+2) and winter
  (CET = UTC+1).
- **Dashboard On-Air light + source switches lagged ~3-4 s behind
  reality.**  The dashboard polled `Schedule/get-current-playlist`
  every 5 seconds, so a sub-second backend state change (Icecast
  mount_add when a show starts, mount_remove when it stops) only
  surfaced on the next poll.  Lowered the interval to 2 s; the
  request load on the local Apache is negligible (small JSON
  endpoint), worst-case lag drops from ~5 s to ~2 s.  A push-based
  SSE/WebSocket fix would be cleaner but is a much larger change.

- **Record-per-Show: recorder never started — recording folder
  endpoint shadowed by REST detail route.**  The new
  `LocalRecordingFolderView` was registered at
  `/api/v2/preferences/local-recording-folder`, but
  `router.register("preferences", PreferenceViewSet)` already claims
  the entire `/preferences/<pk>` subtree for its REST detail route.
  DRF treated the path as `pk="local-recording-folder"`, found no
  integer-pk match, and 404'd before the explicit `path()` was ever
  consulted.  The playout's `_fetch_recording_folder()` saw the 404,
  returned `None`, and the show-record handler logged
  "no recording folder configured" and skipped silently — even
  though `cc_pref.local_recording_folder` was populated.  Moved the
  endpoint out of the `preferences/` subtree to `/api/v2/recording-folder`
  (router.py) and updated the client URL in
  `playout_scheduler._fetch_recording_folder` to match.
- **Record-per-Show: file showed 0 bytes during a live recording.**
  FFmpeg buffered output in RAM and only flushed on graceful exit, so
  the operator had no way to monitor the recording mid-show and a
  crash would have lost everything.  Added `-flush_packets 1` to the
  output side of the recorder command so each packet is written to
  disk as it arrives.
- **Record-per-Show: first ~7 seconds of every show were missing.**
  The recorder reached the Icecast mountpoint a few hundred
  milliseconds before the streamer pushed its first packet; the
  resulting 404 triggered FFmpeg's reconnect loop, which then waited
  up to 5 s before retrying.  Lowered `-reconnect_delay_max` from 5 s
  to 1 s so the worst-case loss is roughly one reconnect attempt.

- **Record-per-Show: schedule builder read wrong JSON key.**  The
  Django `ShowInstance` model exposes the `record` DB column under
  the Python attribute name `record_enabled`, and
  `ModelSerializer(fields="__all__")` puts the Python attribute name
  in the JSON.  The schedule builder checked
  `show_instance.get("record")` which was always `None`, so
  `generate_show_record_events()` was never invoked even after the
  endpoint issue above is resolved.  Fixed by reading
  `show_instance.get("record_enabled")` in
  `libretime_playout.player.schedule.get_schedule`.
- **Calendar: recording-enabled shows lost their fill-bar + content
  icons.**  `full-calendar-functions.js` gated the per-show progress
  bar and the empty / partial-filled / overbooked icons on
  `event.record === 0` — a Linein-era assumption that a "recorded
  show" had no schedule.  Under RASTATIME's parallel record-tap
  semantic, the show still has a normal schedule, so both gates are
  dropped; recording shows now render identically to non-recording
  shows.

### Changed

- **Edit Show form: Record section laid out like Autoloading
  Playlist.**  The previous inline paragraph above the checkbox was
  replaced with an info-icon (`.show_record_help_icon`) that opens
  the same explanatory text on hover via qtip2 — same component
  pattern as the existing Add-Autoloading-Playlist help-icon.  The
  checkbox + label + icon now sit on a single `<dt>/<dd>` row inside
  a `<fieldset>/<dl>`, so spacing, alignment and visual weight match
  the other collapsible sections of the Edit Show form.

- **`cc_show_instances.record` flag semantic broadened.**
  Upstream LibreTime used the record flag to mean "this show IS a
  Liquidsoap line-in recording": the dashboard rendered "Recording
  From Line In", the calendar context menu hid Schedule Tracks /
  View / Clear / Cancel, the showbuilder refused all editing on
  recorded-show rows, and the "Record" checkbox locked itself once
  saved.  RASTATIME's Phase B Record-per-Show feature redefines
  the flag as "tap the on-air output to a parallel MP3 recorder"
  — the show is otherwise a normal scheduled show.  All the
  Linein-specific code paths that gated normal operation on
  isRecorded() were dropped: Dashboard.php no longer returns the
  show's own name as a recording placeholder when no schedule
  items exist; CalendarService.php's full menu (Schedule Tracks /
  View / Clear / Cancel) is always available; ShowBuilder.php no
  longer early-returns isAllowed() for si_record == 1 and no
  longer sets row['record'] = true; ScheduleController.php and
  ShowFormService.php no longer disable the checkbox post-save.
  The isRecorded() method itself is preserved (used by form
  pre-fill and the calendar rebroadcast-conflict check).  See
  architecture **Section 23.13**.

### Added

- **Record-per-Show (per-show on-air recording).**  Shows flagged as
  "Record this show" in the Edit Show form now produce a single MP3
  of the on-air output, written to
  `<recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3`.
  Implementation taps the first configured Icecast output mountpoint
  (e.g. `http://localhost:8000/rastatime`) with FFmpeg `-c copy` —
  1-2 % CPU cost, no re-encode, recording quality matches what
  listeners hear, source switches (file track / web stream /
  line-in / master) captured automatically.  New event types
  `SHOW_RECORD_START` / `SHOW_RECORD_END` decouple the recorder
  lifecycle from the per-source event chain.  Recording folder is
  configured under Settings -> Local Machine (new "Recording
  Folder" section below the Import Folder), exposed to the playout
  via new endpoint `GET /api/v2/preferences/local-recording-folder`.
  The old Line-In-only label "Record from Line In?" on the show
  form is renamed to plain "Record this show".  See architecture
  **Section 23.13** for the full plumbing, considered alternatives,
  and operator-visible failure modes.

- **Local Import Folder (drop-folder semantics) under
  Settings -> Local Machine.**  Operator configures a single
  absolute folder path on the RASTATIME host; every 5 minutes a
  TaskManager job (`LocalImportScanTask`) walks the folder, hands
  every audio file to the standard `CcFiles::createAndImport`
  pipeline (organize -> analyzer -> cc_files), and deletes the
  source after each attempt — successful OR failed.  A "Scan Now"
  button bypasses the 5-minute throttle for immediate verification
  after configuring a new folder.  Reuses existing infrastructure
  end-to-end: no new analyzer, no new storage code, no schema
  change.  Audio formats recognised: mp3, wav, m4a, flac, ogg, oga,
  aac, opus; non-audio files are left untouched (operator may have
  placed them intentionally).  The Settings -> Soundcard page is
  renamed in the navigation to Settings -> Local Machine to cover
  both the existing audio-device sections and the new Import Folder
  section; the controller action is unchanged so existing
  bookmarks/links survive.  See architecture **Section 23.12**.

- **Track Expiry + Podcast Auto-Expiry feature with a shared
  hourly pruner.**  Operators can now attach an expiry date to any
  file in the library through one of three input pipelines:
  (1) a custom ID3v2 TXXX frame named `Expiry` with an
  ISO-8601 date value (`Expiry: 2026-12-21`), read by the analyzer
  on manual uploads; (2) per-podcast auto-expiry: the Edit-Podcast
  form gains an "Auto-Expiry" checkbox and a "Days" field, and
  the Django `download_episode` view computes
  `expires_at = now() + days` on every episode imported from that
  podcast (per design decision B, this overrides any ID3 tag the
  publisher set — subscribers own retention); (3) manual edit on
  the Library's Edit Audio MD form, with a YYYY-MM-DD text field.
  An hourly `TrackExpiryTask` (TaskManager) flips
  `cc_files.disabled = true` on every row where
  `expires_at < NOW()`.  Disabled tracks stay visible in the
  Library and in already-built Smartblocks (so scheduled shows
  keep playing them) but are excluded from NEW Smartblock
  evaluations via a `disabled = false` clause on the criteria
  query.  Two new optional columns in the library DataTable
  ("Expiry Date" and "Disabled") let the operator sort and bulk-
  delete the expired set at their leisure.  Migration
  `0049_add_track_expiry_and_podcast_auto_expiry`.  See
  architecture **Section 23.11** for the full design and the
  rationale for precedence decision B and disable-vs-delete
  decision A.

- **Per-webstream static input-gain.**  New column
  `cc_webstream.input_gain_db` (default 0, range -20..+20 dB) lets
  operators compensate for chronically quiet or loud third-party
  webstream feeds without leaning on the upstream feed operator to
  re-normalise.  Applied by the FFmpeg streamer and the mpv local
  monitor as a single `-af volume=<dB>dB` audio filter for the
  lifetime of the webstream event, using the same mechanism as the
  existing file-track ReplayGain pipeline (Section 23.8).  The
  webstream edit dialog gains an "Input Gain (dB)" numeric field
  between Default-Length and Save; legacy webstreams without a value
  fall back to 0 = no change to behaviour.  Migration
  `0048_add_cc_webstream_input_gain_db`.  See architecture
  **Section 23.10** for the full plumbing and the engine-parameter
  generalisation (`replay_gain_db` -> `gain_db`).

- **Distinct `RASTATIME_VERSION` constant for the fork.**  Introduced in
  `application/configs/constants.php` (currently `0.5`, in lockstep with
  the ARCHITECTURE.md version-history).  Settings -> Status now displays
  "RASTATIME Version 0.5" in the top row instead of the upstream
  LibreTime release.  The upstream version (from `frontend/legacy/VERSION`)
  is still available as `Config::getConfig()['airtime_version']` for
  callers that need upstream-sync tracking, API-response compatibility,
  etc.

- **Service-restart UI on Settings -> Status (admin-only).**  Adds a per-
  service Restart button for each of the six RASTATIME NSSM services
  (ANALYZER, API, APACHE, ICECAST, PLAYOUT, WORKER) plus a "Restart All
  Services" button.  Each row carries a short "what this service does
  and when to restart it" hint so the operator does not need to leave
  the page to make the right call.  All requests are CSRF-protected,
  POST-only, and the service name is matched against a constant
  whitelist before reaching the shell; the page itself is ACL-gated to
  the Admin role via the existing `systemstatus` resource entry.
  The upper status table's six RASTATIME-service rows now display a
  pure-icon running-state cell (green check via the existing `.check`
  class on RUNNING, red cross via the new `.fail` class otherwise),
  matching the look of the Postgres / Database / RabbitMQ dependency
  rows.  The previous `sc query` / `sc start` recovery hints were
  removed from those cells; the Restart button in the lower table is
  now the canonical recovery path.

  Apache restarts (single or as part of restart-all) are scheduled
  through a self-deleting temp .bat file spawned via
  `wmic process call create`, NOT via `start /B`.  `start /B` leaves the
  child in the same console as the Apache worker that issued it; when
  Windows tears down Apache's job object during the restart, the child
  goes with it and Apache hangs in SERVICE_STOP_PENDING
  ("Wird beendet") with nothing left to fire `nssm start` afterwards.
  This was the cause of the first restart-all hang on 2026-05-16 (only
  recoverable via `taskkill /F /IM httpd.exe`).  WMI spawns the child
  outside Apache's job object, and the batch file includes a short
  ping-based pre-delay so the JSON response to the operator reaches
  the browser before nssm reaches into Apache.  Restart-all also
  reorders services so Apache is restarted LAST, after a 6s delay
  (other services get 2s).  The JS auto-reload waits 15s before
  refreshing the status page.

- **ReplayGain is now actually applied** to scheduled file tracks.  The
  precomputed dB offset (``cc_files.replay_gain`` + ``cc_pref.replay_gain_modifier``)
  has been summed onto ``FileEvent.replay_gain`` since the early
  schedule-builder was written, but neither the FFmpeg streamers nor
  the mpv local-monitor consumed the value — it ran into the void.
  Both engines now accept a ``replay_gain_db`` parameter and apply
  it as a single ``volume=<dB>dB`` audio filter (FFmpeg: ``-af
  volume=...`` between input and encoder; mpv: ``af`` property
  ``lavfi=[volume=...]`` reset on every ``play()`` so live sources
  don't inherit a previous track's gain).  ``PlayoutScheduler``
  threads the value through from ``_on_file_start`` and caches it
  on ``_current_replay_gain_db`` so the resume path (DJ-disconnect
  fallback, hot-reload restart, schedule refresh mid-track) keeps
  the right correction in place.  Live sources (linein, webstream,
  master/show) pass ``None`` and are not gain-modified.  5 new unit
  tests in ``backend/playout/tests/engine/test_ffmpeg_streamer_replay_gain.py``
  cover the filter-emission paths.
- **FFmpeg-based playability check at file import time.** The upstream
  `analyze_playability` step required Liquidsoap on PATH; since RASTATIME
  intentionally ships without Liquidsoap (ADR-002), the check was a silent
  no-op on this platform and broken or partially-corrupted audio files were
  only surfaced at actual playout time (mid-show "Header missing" log
  spam, briefly muted last frames).  The new check runs
  `ffmpeg -v error -i <file> -f null -` against every imported file:
  - exit 0 + empty stderr → clean (no log)
  - exit 0 + decoder warnings → soft-warn (logged at WARNING; import
    allowed; typical "trailing-frame Header missing" pattern from
    poorly-encoded MP3s)
  - exit non-zero → hard reject via `UnplayableFileError` (existing
    upstream behaviour, importer skips the file)
- **Re-scan tool for the existing library**:
  `infra/scripts/maintenance/rescan-playability.py`.  Walks every
  ``cc_files`` row, applies the same FFmpeg-based check, and reports
  hard failures / soft warnings / missing-on-disk entries.  Run via the
  project venv's Python; reads storage root and DB creds from
  ``libretime.conf``.  Smoke-test on a 10-row slice surfaced 4 pre-
  existing soft-warn files plus one DB-row-without-file (id=1) in the
  current library.

- **Per-DJ source authentication against the LibreTime database** (Phase B.4
  #2).  Replaces the previous "single shared password per mount" model with
  Icecast 2.4's `stream_auth` URL-auth callback (Apache → light PHP at
  `public/icecast-source-auth.php`, no Zend bootstrap).  The PHP validates
  the source against `cc_pref` (master DJ) or the active show's
  `cc_subjs ∪ cc_show_hosts` set with md5 password comparison (show DJs,
  Legacy LibreTime hash format).  Operator-override fallback credentials
  (`source` / `master-secret` / `show-secret`) remain valid as a DB-down
  escape hatch.  Strict mode (Variant A): no active show → /show is
  rejected, no DJ may pre-connect.
- **`GET /source-state` endpoint** on the playout listener (`:8770`).
  Returns JSON `{master_connected, show_connected, current_state}` with a
  process-internal-state read; consumed by the legacy dashboard's "On Air"
  indicator instead of stale `cc_pref.{master_dj,live_dj}_switch` columns.
- **Reconciliation watchdog** in `libretime_playout.source_switcher`.  A
  daemon thread polls Icecast's `/admin/listmounts` every 10 s and syncs
  the `SourceSwitcher` state with whatever Icecast actually reports — auto-
  heals stuck `master_connected=True` / `show_connected=True` states caused
  by missed `mount_remove` notifications.  Worst-case stuck-state
  duration: ~10 s.
- **Direct-to-`:8770` source-event wiring** in `icecast.xml`.  Mount-level
  `mount_add` and `mount_remove` URL options now point straight at the
  playout's source-event listener, bypassing PHP.  PHP's async
  `popen('start /B …')` + curl path turned out to be unreliable on
  Windows fcgid — the curl child was reported as spawned (`popen=ok`) but
  did not consistently reach `:8770`.  Icecast 2.4 itself does proper
  outbound HTTP for these URLs, which we trust as the fast path; the
  reconciliation watchdog above is the slow safety net.
- **Friendly-name fallback for unstable USB audio endpoint GUIDs**
  (Phase B.4 #4).  Empirically, Windows can reassign the WASAPI endpoint
  GUID of a USB audio device after reboot / driver update / port re-
  enumeration — observed with Jabra USB headsets.  Both `rastatime_linein`
  and `rastatime_soundcard_settings` now carry a `device_name`-style
  column alongside the `device_id` stable-ID.  The shared resolver
  `WindowsAudioDeviceManager.find_device_by_id_or_name()` tries the saved
  GUID first and falls back to a case-insensitive friendly-name match,
  logging a WARNING that prompts the operator to re-save the picker
  once.  Migrations: `linein/0004_linein_device_name`,
  `soundcard/0002_add_output_device_names`.

### Changed

- **Playout engine gain parameter generalised from `replay_gain_db`
  to `gain_db`.**  The mechanism (single FFmpeg `volume` filter
  before the encoder, or mpv `af` property `lavfi=[volume=...]` for
  the local monitor) is unchanged, but the parameter now carries
  whatever per-event dB value applies for the current event type:
  precomputed ReplayGain sum for file events,
  `cc_webstream.input_gain_db` for webstream events, `None` for
  live sources (Master/Show/Linein).  The scheduler picks the
  right source value per event and passes the result.  Affected
  symbols: `PlayoutEngine.play()`, `FfmpegStreamer.start()`,
  `MpvPlayoutEngine.play()`, `VlcPlayoutEngine.play()`,
  `PlayoutScheduler._start_streamers()`, and the cached
  `PlayoutScheduler._current_replay_gain_db` field (renamed to
  `_current_gain_db`).  Test file
  `test_ffmpeg_streamer_replay_gain.py` renamed to
  `test_ffmpeg_streamer_gain.py` with the same five assertions
  updated to the new keyword; the tests do not depend on which
  feature the gain originated from.

- **`Preference::GetSourceStatus()` / `GetSourceSwitchStatus()` (legacy
  frontend)** now fetch live state from the playout's `/source-state`
  endpoint with a per-request static cache and a 500 ms timeout, falling
  back to `off` on playout unreachability.  Previously these read from
  `cc_pref.{master_dj,live_dj}` and `cc_pref.{master_dj,live_dj}_switch`
  columns that nobody writes anymore since the icecast-hook refactor,
  resulting in a permanently-dark "On Air" indicator.

### Fixed

- **Windows-service health probe was locale-dependent.**
  `check_windows_service()` ran `sc query <name>` and matched the literal
  string "RUNNING" in the output to decide whether a service was up.
  On any non-English Windows install (e.g. German "WIRD AUSGEFÜHRT")
  the match silently failed and the Settings -> Status table rendered
  a red-cross indicator for healthy services.  Two text-parsing
  iterations were tried (anchor on the literal label "STATE :",
  then parse by value-line position) and both regressed in subtle
  locale-specific ways because sc.exe localises labels, separators,
  and header lines independently.  Final fix switches the probe to
  PowerShell `Get-Service`, whose `.Status` property is the .NET
  ServiceControllerStatus enum --- its member names ("Running",
  "Stopped", "Paused", ...) are language-invariant regardless of OS
  display language.  Two further snags surfaced during deployment:
  (a) PowerShell on Windows defaults to UTF-16 LE output with a BOM,
  which PHP's exec() reads as NUL-interleaved bytes that never compare
  equal to the ASCII string `'Running'`; fixed by forcing
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` in the
  PowerShell command line.  (b) The Apache/NSSM service worker can run
  with a stripped-down PATH that does not contain
  `C:\Windows\System32\WindowsPowerShell\v1.0\` (NSSM service-account
  environment is not the same as the interactive user shell --- nssm.exe
  itself happened to be on PATH which masked this issue); fixed by
  resolving an absolute path via `getenv('SystemRoot')` with explicit
  fallbacks.  Results are static-cached for the lifetime of the request
  and pre-warmed with a single batched PowerShell call so the
  Settings -> Status page pays one process-start cost (~500ms) instead
  of six.  Affects all six RASTATIME NSSM service rows.

- **Settings -> Status icons (.check / .fail) were invisible because
  the empty status TD collapsed below the background image's height.**
  Added explicit `min-height: 24px; min-width: 24px` to
  `.solution.check, .solution.fail` in `config-check.css` so the cell
  is always tall enough to render the 16-pixel accept/delete glyph.
  Latent upstream issue that became visible the moment we added the
  six RASTATIME-service icon rows.

- **Playlist row preview silently no-op'd from the Library context menu.**
  Two compounding bugs:
  1. `Application_Model_StoredFile::searchFiles()` had a copy-paste typo —
     the per-row recompute block used `$r` (undefined) instead of `$row`
     (the loop's reference variable), so `Application_Model_Playlist::getLength()`
     and the Smart-Block `bl_type` flag never made it into the
     DataTables response.
  2. The icon-click and context-menu "Play" callbacks in `library.js`
     guarded the playlist branch with `data.length !== "0.0"`.  Combined
     with the typo above, every legacy playlist whose `cc_playlist.length`
     DB column was `00:00:00` (most of them) formatted to the literal
     string `"0.0"` and silently failed the guard.
  Both addressed: `$r → $row` rename, plus the strict-equality length
  check dropped from both JS callbacks (an empty player popup is better
  UX than a click that does nothing).
- **Dashboard header showed bare "," for active Line-In schedule rows.**
  `Schedule::getPreviousCurrentNextMedia()` only inspected `cc_schedule.file_id`
  and `cc_schedule.stream_id`, so Line-In rows (which carry their reference
  in `cc_schedule.linein_id`) fell into the "unknown type" branch with an
  empty `name`.  Dashboard JS then printed `name + ","` giving the
  observed comma-only display.  Added a raw-SQL bridge
  `_fetchLineinForScheduleId()` (Propel's CcSchedule base class isn't
  aware of `linein_id`; the legacy schema.xml was extended but the
  generated classes were never regenerated) and use it in the previous /
  current / next branches to populate `name` with the operator-given
  Line-In label (e.g. `"Jabra-Mikro"`) and `type='linein'`.
- **Library "Delete" button silently no-op on Line-In rows.**  The dashboard's
  "Delete" button and the row-level context menu's "Delete" entry both
  forwarded `{type: 'linein', id: ...}` to `library/delete`, but
  `LibraryController::deleteAction()` only handled `audioclip` / `playlist` /
  `block` / `stream` types.  Line-In items fell through the type-dispatch
  with no DELETE call and no error, leaving the row in the table.  Added a
  dedicated branch that calls `DELETE /api/v2/audio/linein/<pk>` on the
  Django API and surfaces non-2xx responses as a "Could not delete some
  Line-In sources" message.
- **"Stuck `master_connected=True`" state** that left the playout pointing
  FFmpeg streamers at an empty `/main` mount after a brief BUTT connection
  to `/main` was followed by a disconnect that Icecast 2.4 occasionally
  failed to surface via `mount_remove`.  Output mounts then carried
  silence even though the scheduler thought everything was healthy.
  Addressed by the reconciliation watchdog described above.
- **Per-DJ accountability on `/show` source connections**.  Pre-refactor,
  any client knowing the shared static `<password>show-secret>` could
  push to `/show` as any username with no DB check.  Now the URL-auth
  layer rejects sources whose user is not a configured host of the
  currently-running show (or the show's custom auth user, when the show
  has `live_stream_using_custom_auth`).

- **Settings -> General -> "Default Language" silently flipped the
  operator's UI language back to whatever the global default happens
  to be, on every save that did not touch the language dropdown.**
  The form pre-filled the language dropdown with `GetDefaultLocale()`
  (the global cc_pref.locale row, used as the seed value for new
  users).  Combined with the three-source-sync save handler
  introduced earlier on this date, any save where the operator
  changed an unrelated field (e.g. uploading a favicon) round-tripped
  the global default through `SetUserLocale()` and the
  `airtime_locale` cookie, overwriting the operator's own per-user
  language preference.  Fix: pre-fill the dropdown with
  `GetLocale()` (the operator's effective locale) so an untouched
  dropdown is a no-op on save.  Non-logged-in users still see the
  global default because `GetLocale()` falls back to it when no
  session user is set.

- **Settings -> General -> "Default Language" never visibly took effect**
  for the operator who flipped it.  Three issues compounded, all
  uncovered the moment the new `.po -> .mo` pipeline produced
  real translations to bind against:

  1. `PreferenceController::indexAction()` only wrote `cc_pref.locale`
     (the global default for new users).  RASTATIME has three Locale
     source surfaces and `GetLocale()` for a logged-in user prefers
     the per-user `cc_pref.user_locale` row, which the form save
     never updated.  The `airtime_locale` cookie additionally out-
     prioritises both in the pre-login and Edit-User paths and was
     also not refreshed.  Fix: the save now writes `SetDefaultLocale`,
     `SetUserLocale`, the cookie, and re-runs
     `configureLocalization()` inline so the "Preferences updated"
     confirmation and the re-rendered form labels are already in the
     newly selected language.

  2. `Application_Model_Locale::configureLocalization($locale = null)`
     contained a use-after-null bug: when called without an argument
     (the `PageLayoutInitPlugin` hot path on every request), it built
     `$lang` from `Preference::GetLocale()` correctly but then ran
     `putenv("LANGUAGE={$locale}")` with `$locale` still null,
     silently emptying the LANGUAGE env var that drives gettext's
     `.mo` lookup.  gettext then fell back to whatever LC_MESSAGES
     the Apache/fcgid worker carried from a previous request, which
     on a recycled worker pinned the UI to the first locale ever
     bound in that process ("sticky-stale German even after
     switching to English").  Fix: resolve `$locale` before the
     `putenv` call.  Also added a multi-format `setlocale` retry
     (`en_US.UTF-8` -> `en_US` -> `en-US`) for Windows hosts that
     reject POSIX locale names, and switched `bindtextdomain` to an
     absolute path so CWD churn under Apache/fcgid cannot
     misdirect the lookup.

  3. `application/configs/navigation.php` is loaded at Bootstrap
     time, before `configureLocalization()` runs.  It was calling
     `_('Calendar')`, `_('Settings')`, etc. directly while building
     the Zend_Navigation container, which translated against the
     half-set worker locale state and stored the translated text in
     the container.  `views/scripts/menu.phtml` then ran
     `_($page->getLabel())` at render time, but the label was
     already in the target language (e.g. "Kalender") and gettext
     msgid keys are always English, so the second pass was a no-op
     fallback.  Symptom: top-nav labels like "Calendar" / "Kalender"
     never changed when the operator switched language, while
     correctly-bound strings inside view scripts (e.g. "Smart Block"
     in `layout.phtml`) did switch.  Fix: navigation.php now stores
     plain English source strings; the .po extraction tools still
     pick up these msgids from the many other .phtml files that
     reference them.  Header comment in `navigation.php` updated to
     match the actual design.

### Added

- **Service restart controls on Settings -> Status (admin-only).**
  A new "Service Management" block underneath the existing status table
  exposes one "Restart" button per RASTATIME Windows service
  (ANALYZER, API, APACHE, ICECAST, PLAYOUT, WORKER) plus a
  "Restart All Services" button.  Each row carries a short description
  of what the service does and a one-line "when to restart" hint so
  the operator does not have to memorise which service owns which
  function.  Backend: `SystemstatusController::restartServiceAction`
  and `restartAllAction` shell out to `nssm restart <name>` after a
  POST + CSRF + whitelist check (only the six service names above
  are accepted; anything else is rejected before reaching exec).
  Apache restarts run detached (`start /B "" nssm restart ...`)
  because the Apache worker hosting the request would otherwise be
  killed mid-response; the UI shows a warning and auto-reloads after
  a 12-second delay.  ACL inherits from the existing `systemstatus`
  resource which is already restricted to role `A` (Admin) and
  above.  Also: the status table was extended to display health for
  the analyzer, icecast, and apache services that were previously
  not covered by `checkExternalServices()`.

- **Custom station favicon upload in Settings -> General.**  Operators can
  now upload a `.png`, `.jpg`, `.gif`, or `.ico` (<= 200 KB) and it
  replaces the bundled `public/favicon.ico` for every page in the
  legacy frontend (dashboard, library, login, radio page, etc.).
  Storage follows the same pattern as the existing station-logo upload:
  base64 blob in `cc_pref.station_favicon` plus a separate
  `cc_pref.station_favicon_mime` row.  Render path emits a `data:` URI
  in the `<link rel="icon">` tag, so no writes to `public/` happen at
  request time.  `PageLayoutInitPlugin` and `LoginController` both
  query `Preference::GetStationFaviconHref()` and fall back to the
  static `favicon.ico` when no custom upload exists.  Live preview
  on the form mirrors the station-logo upload, and a Remove button
  clears both cc_pref rows.

- **Operator-facing localisation guide** at
  `frontend/legacy/locale/README.md`.  Step-by-step instructions for
  editing a single translation, ratifying fuzzy entries, adding a new
  language (Locale.php + locale.gen + datatables-i18n + plupload-i18n
  + build script), and a short troubleshooting list for "string
  stubbornly in the wrong language".  Architecture **Section 23.9**
  links to it as the lower-abstraction operator reference.

- **Windows-native `.po → .mo` build pipeline for the legacy frontend
  locales.**  `infra/scripts/maintenance/build-locales.ps1` compiles
  every active language's `libretime.po` into a binary `libretime.mo`
  using mlocati's standalone `gettext-iconv-windows` distribution (no
  MSYS2 / Cygwin / WSL).  Until now, RASTATIME shipped the upstream
  `.po` source files but never the compiled `.mo` artefacts the PHP
  gettext extension actually reads — every language selection on
  Settings → General silently fell back to the English source string.
  See architecture **Section 23.9** for the toolchain choice and the
  rationale against MSYS2 / Chocolatey / pre-compile-at-CI.

### Changed

- **Filled all 234 previously-empty `msgstr` entries in `de_DE/libretime.po`**
  (Phase G).  225 strings went through a user-reviewed translation pass via
  `C:\Temp\rastatime-de-DE-translations-review.md` (HIGH/MEDIUM/LOW
  confidence buckets); 9 additional multi-line `msgid` blocks that the
  single-line extractor had missed (UsabilityHints linked-show banner,
  three embeddable-widget pre-flight checklists, the
  "cannot schedule outside a show" hint, the third-party-API description,
  and three password-reset email templates) were translated with
  best-effort and flagged for follow-up review.  `de_DE.mo` now contains
  985 translated entries; `msgfmt --check-format --check-domain` builds
  it without warnings.

- **Ratified three fuzzy translations in `fr_FR/libretime.po`.**
  Upstream had marked them `#, fuzzy` (translator-suggested but
  unconfirmed) so `msgfmt` excluded them from the compiled `.mo` and
  the strings rendered in English.  All three (`"Retreiving data from
  the server..."`, `"Select Track Type"`, `"Select track type"`) had
  accurate French translations already; we removed the fuzzy flag so
  they are now active.

- **Reduced the legacy frontend's language dropdown from 22 to 4
  maintained locales** (`en_US`, `de_DE`, `fr_FR`, `es_ES`).  The other
  18 entries were inherited Transifex / Weblate translations of varying
  staleness with no RASTATIME support pathway.  `Locale.php $locales`
  array trimmed, `locale.gen` updated, and the 18 unused
  `locale/<LANG>/` directories plus the matching
  `public/js/datatables/i18n/<LANG>.txt` and
  `public/js/plupload/i18n/<LANG>.js` files removed via the one-shot
  delete script `C:\Temp\delete-scripts\rastatime-delete-unused-locales.ps1`.
  Re-adding a language requires synchronised edits documented in
  `Locale.php`.

### Removed

- **Phantom "Feature Previews" setting on Settings → General.**  The radio-
  button pair stored a value to `cc_pref.feature_preview_mode` but the
  getter `Application_Model_Preference::GetFeaturePreviewMode()` was called
  in exactly one place — the form rebuilding its own current value on
  re-render — and the setter only by the form's save handler.  No feature
  anywhere in RASTATIME (or upstream) ever gated on the value, so toggling
  the radio had no observable effect.  Removed: form element +
  `preferences_general.phtml` render line + `PreferenceController` save
  line + `Preference::{Get,Set}FeaturePreviewMode` accessors.  The
  `cc_pref` row with `keystr = 'feature_preview_mode'` is left in place
  for legacy data preservation; nothing reads it now.

- **"Preview (coming in Phase B)" placeholder on Line-In Library rows.**
  Earlier the context menu installed a permanently-disabled "Preview"
  entry to signal a planned feature.  Product decision: don't offer
  Preview for Line-In at all.  A meaningful preview would require a
  per-row Preview-on-Demand FFmpeg capture-to-Icecast pipeline (start
  on right-click, stop on popup-close); the cost / benefit ratio
  doesn't justify it.  The menu entry is now ``unset`` for `linein`
  rows so operators see Edit + Delete only.

- **Phantom "Auto Switch On" / "Auto Switch Off" UI on Settings → Streams →
  Live Broadcasting.**  Both checkboxes saved a value to `cc_pref` but the
  only code path that consumed those values was
  `ApiController::updateSourceStatusAction()`, which dispatched RabbitMQ
  messages to the Liquidsoap-based Pypo playout — both removed in ADR-002.
  The replacement `libretime_playout.source_switcher.SourceSwitcher`
  performs Master > Show > Scheduled priority transitions
  unconditionally, so the operator-controllable gate the upstream
  checkboxes used to provide no longer has a dispatch target.
  Removed: form fields, view template fragments, qtip help popovers,
  `Application_Model_Preference::{Set,Get}{AutoTransition,AutoSwitch}` helpers,
  the `PreferenceController::liveStreamAction` save lines for them.
  Reduced `ApiController::updateSourceStatusAction()` to a no-op stub
  (kept for v1 API client backwards compatibility).  `cc_pref` rows
  with `keystr = 'auto_transition' / 'auto_switch'` are left in place
  for legacy data preservation; nothing reads them now.

- **FFmpeg-Streamer listener-auth via PHP** (`listener_add` URL option) on
  `/main` and `/show` — Icecast 2.4 was rejecting ~50 % of the playout's
  parallel listener-add bursts under load with HTTP 400 even when the
  Apache-side PHP responded 200.  Since `/main` and `/show` are
  `<hidden>1</hidden>` + `<public>0</public>` and Windows-firewall-bound
  to 127.0.0.1, the only realistic listeners are the playout's own mpv +
  FFmpeg streamers; static-password source-auth and `stream_auth` cover
  the authentication need without `listener_add`.

- **FFmpeg-based Icecast streaming.** Replaces VLC's broken sout/shout chain
  on Windows with a per-mount FFmpeg subprocess that reads the same audio
  file VLC plays locally and pushes it to Icecast via the built-in
  `icecast://` protocol. Stable across MP3, Ogg Vorbis, Opus, and AAC.
- **Multi-stream output.** Up to three simultaneous Icecast streams with
  independent codec, bitrate, sample rate, and mountpoint per stream
  (Settings → Streams).
- **Opus codec support** in stream outputs. Frontend dropdown, Backend
  encoder pipeline, and a sample-rate guard that forces 48 kHz when Opus is
  selected (libopus does not accept 44.1 kHz).
- **Sample-rate selector** (44.1 / 48 kHz) per stream output. The Frontend
  greys out 44.1 kHz when the codec is Opus; the Backend additionally
  clamps invalid values with a warning so misconfigured sources never
  reach Icecast.
- **Stream-config hot reload.** Stream-output settings are re-read from
  `cc_pref` on every schedule poll (≤120 s). When a track is playing, the
  new streamers re-attach mid-track at the correct seek position — no
  service restart required.
- **NSSM install / remove scripts** for `RASTATIME-API`, `RASTATIME-WORKER`,
  `RASTATIME-PLAYOUT`, and `RASTATIME-ICECAST` under `infra/nssm/`. All
  services run unattended at boot, with auto-restart, log rotation, and
  log files under `C:\rastatime\logs\`.
- **VLC playout engine (libVLC / `python-vlc`)** as the local-playback
  layer. Catch-up logic re-attaches to in-progress tracks across service
  restarts so a crash mid-show does not silence the air signal.
- **Per-mountpoint FFmpeg stderr logs** (`C:\rastatime\logs\ffmpeg-<mount>.log`)
  capture connection failures and encoder warnings that would otherwise
  vanish into a closed pipe.
- **Legacy v1 API notify** for the dashboard "On Air" indicator. The
  scheduler hits `/api/notify-media-item-start-play` on each track start
  so the red light flips on without depending on Liquidsoap.
- **GitHub Actions CI** (`python.yml`, `php.yml`). Ruff lint and format
  checks are hard-fails for `backend/`; per-package pytest jobs run for
  `analyzer`, `api-client`, `playout`, and `shared`. PHP CI runs
  `composer install` and `php -l` over `frontend/legacy/application/`.
- **Line-In sources** as a first-class equivalent to webstreams: multiple
  local hardware inputs that can be scheduled like any other source.
- **Soundcard settings** page (Settings → Soundcard) for explicit local
  input/output device mapping.
- **German UI translation** alongside the English default.

### Changed

- **Playout engine: Liquidsoap → libVLC → mpv (libmpv).** Liquidsoap is no
  longer required on Windows. All scheduling, queue management, and
  source switching go through the engine-agnostic `PlayoutScheduler`
  (renamed from `VlcScheduler` after the libVLC → mpv migration of
  May 2026) which talks to the `PlayoutEngine` interface — currently
  satisfied by the mpv-backed implementation in
  `libretime_playout.engine.mpv_engine`.
- **Worker: Celery → plain Python task runner.** Removes the RabbitMQ /
  AMQP broker hard-dependency from the worker process.
- **WSGI server: Gunicorn → Waitress** on port 8765, native to Windows.
- **Service manager: systemd → NSSM.** All four services use NSSM with
  identical install / remove / status scripts.
- **Audio output: ALSA / PortAudio / PulseAudio → WASAPI** via libVLC.
- **Filesystem layout.** Linux paths (`/etc`, `/srv`, `/var/log`) replaced
  with Windows paths (`C:\rastatime\config`, `C:\rastatime\media`,
  `C:\rastatime\logs`) repo-wide.
- **Default UI port (operator-facing):** Apache on port 80 (frontend),
  RASTATIME-API on port 8765 (no longer 8000), Icecast on port 8000.

### Removed

- **Liquidsoap dependency.** No `*.liq` template is generated or evaluated
  at runtime; the bundled fixtures remain only as upstream-snapshot
  references for diff'ing with LibreTime.
- **Linux-only installers / packaging** — no `.deb`, no systemd unit
  files, no `apt`-based bootstrapper.

### Notes for upgraders from LibreTime

- RASTATIME is a **functional fork**, not a drop-in replacement. The
  Postgres schema is compatible (LibreTime media libraries can be
  imported), but the playout / streaming subsystems are rewritten from
  scratch. Do not point a running LibreTime install at RASTATIME services.
- Legacy `cc_pref` keys (`stream_output_1..3`) are reused as the source of
  truth for stream-output settings. The Liquidsoap-era keys
  (`use_stream_output_*`, `output_sound_device`) are still read for
  backwards compatibility but are no longer the operative source for
  Icecast egress.

---

<!--
Future releases will go below this line, with the most recent at the top.
Each entry should follow the Keep-a-Changelog grouping:

  ### Added       — new features
  ### Changed     — changes to existing functionality
  ### Deprecated  — soon-to-be removed features
  ### Removed     — features removed in this release
  ### Fixed       — bug fixes
  ### Security    — vulnerability fixes (highlight in release notes!)
-->

[Unreleased]: https://github.com/RASTATIME/rastatime/compare/v0.0.0...HEAD
