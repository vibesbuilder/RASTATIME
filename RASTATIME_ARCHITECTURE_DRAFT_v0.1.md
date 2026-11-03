
# RASTATIME — Architecture Draft
**Windows 11 LibreTime Fork with VLC/libVLC Main Playout Engine**  
Draft version: 0.112
Date: 2026-11-03

> **Revision history**
> - **0.112 (2026-11-03)** - **Archiving, stage 3** (§23.81): "Archive automatically" per show; the
>   worker queues each new episode a waiting time after its end (recording, data complete, no
>   rebroadcast, nothing caught up), gives up after 24 h and warns on the dashboard; migration 0076.
> - **0.111 (2026-11-03)** - **Archiving, stage 2** (§23.80): the feature is renamed "Archiving"; CBA
>   accounts (admins), "Archive online" by hand from the Episode dialog, RASTATIME-WORKER uploads with
>   a bandwidth limit and never repeats an unclear upload; migration 0075.
> - **0.110 (2026-11-03)** - **Publishing, stage 1** (§23.79): editorial team profiles, per-show
>   publishing defaults, per-episode title / teaser / image (calendar "Episode..."), Analytics ->
>   Participants; legacy migration 0074 (four tables), nothing uploaded yet.
> - **0.109 (2026-11-02)** - **Fresh-machine rehearsal fixes** (§23.78): output.icecast state reported
>   to Settings -> Streams via PLAYOUT `/stream-event`, Main Output "Off" (no portaudio), unplanned
>   Liquidsoap restart re-arms the running item, installer / status script hardening.
> - **0.108 (2026-11-01)** - **Library-wide cue-point re-detection**
>   (§23.45): CLI script on the legacy model, 19,975 files applied;
>   detect() without a shell (`!`/`%` paths).
> - **0.107 (2026-11-01)** - **Cue points were never measured by the
>   analyzer** (addendum to the cue-point section): ffmpeg's
>   `Parsed_silencedetect` prefix; parser fixed, analyzer suite green.
> - **0.106 (2026-11-01)** - **Line-in input drains before it is
>   detached** (§23.68 addendum): the start+stop reaper looped every
>   2 s on a sleeping zombie input; stop now completes while armed.
> - **0.105 (2026-11-01)** - **Brand stage B, phase 2** (§23.77): the
>   bridge is removed after three nights without a hit; only the
>   `rastatime_*` / `RASTATIME_*` names are read (hard cut).
> - **0.104 (2026-10-29)** - **Bridge instrumentation** (§23.77): every
>   use of a former name or variable is logged; phase 2 moved forward
>   to 2026-11-01/02 (operator).
> - **0.103 (2026-10-29)** - **Brand stage B** (§23.77): the Python
>   packages, commands, environment variables, config file, gettext
>   domain and PHP classes carry the product name; a five-day bridge
>   keeps the former names working (end moved to 2026-11-01/02 in 0.104).
> - **0.102 (2026-10-28)** - **Undo after deleting a show** (§23.76): the
>   calendar's delete waits ten seconds client-side with an Undo toast;
>   server unchanged.
> - **0.101 (2026-10-28)** - **Failed imports** (§23.75): reason on the Upload
>   page, "Clear" takes the organize/ original along, "Download", preflight
>   `imports_failed`, repair of ID3-before-RIFF containers.
> - **0.100 (2026-10-28)** - **Cue sidecars of the repeated hour** (§23.34
>   addendum): one sidecar per real hour when the autumn clock change
>   repeats a wall-clock hour.
> - **0.99 (2026-10-28)** - **Deleted autoloading playlists** (§23.74): the
>   library delete names the shows and clears their flag, the preflight
>   scan warns about shows with the flag and no playlist.
> - **0.98 (2026-10-28)** - **bcrypt password hashes** (§23.73): the legacy
>   login adapter, the DJ check and the Django hasher share one algorithm,
>   legacy md5 values migrate on the next login.
> - **0.97 (2026-10-27)** - **Legacy CSRF check enforced** (§23.72 addendum):
>   phase 2 - a legacy write without a valid token is refused (403); plain
>   form posts carry the token as the hidden field `csrf`.
> - **0.96 (2026-10-26)** - **Overrun rule of the autoloading fill** (exact-fill
>   addendum): the first item that does not fit may run past the show's end
>   when the next show has "Allow delayed start", within 5 s, or with the
>   block's "Allow last track to exceed time limit".
> - **0.95 (2026-10-26)** - **Filler outro after the content; Auto DJ waits
>   for the show's own fill** (exact-fill and §23.20 addenda): an outro with a
>   "time remaining" block follows the content against the rest; the
>   fill-pass skips unbuilt autoloading shows and pending repeat copies.
> - **0.94 (2026-10-26)** - **UI secondary colour as a setting** (§23.43
>   addendum): `--rt-secondary` palette next to the primary one, same style
>   block; buttons darkened only to WCAG AA contrast for white text.
> - **0.93 (2026-10-25)** - **Super Admin retired** (§23.72 addendum): four
>   roles; migration 0073 turns S accounts into Admins; the installation
>   account `admin` cannot be deleted (legacy and API v2).
> - **0.92 (2026-10-25)** - **Icecast without input mounts** (§23.72 addendum):
>   `/main` and `/show` and their URL-auth endpoints removed; port 8000 is
>   for local clients only (listeners via Apache `/stream/`).
> - **0.91 (2026-10-25)** - **Role audit: role checks and the legacy CSRF
>   check** (§23.72): shared PM+/owner helpers, REST session vs. API key,
>   `@internal_only` Django views, the X-CSRF-Token convention for every
>   legacy write (phase 1 logs only).
> - **0.90 (2026-10-25)** - **Users in Import / Export** (§23.56 addendum):
>   users.csv first in the bundle, no passwords in the export, password
>   for new users only, guards for super admin / own account / last admin.
> - **0.89 (2026-10-24)** - **Tagless folder, JPG-only artwork** (SS23.71):
>   uploads without an artist tag are filed under `imported/tagless/`, and a
>   cover is stored as its five JPG sizes only, Data URIs built on demand.
> - **0.88 (2026-10-24)** - **Podcast downloads queue their loudness
>   measurement** (SS23.41 addendum): the API publishes the analyzer's
>   loudness-only job for every downloaded episode.
> - **0.87 (2026-10-24)** - **Visible columns per media type** (SS23.42
>   addendum): the library keeps a visibility profile per media type on top
>   of the per-user table layout.
> - **0.86 (2026-10-23)** - **Played-lately windows in minutes, picks of the
>   same expansion excluded** (SS23.21 addendum): `*_minutes` criteria rows
>   (old `*_hours` rows read x 60), and a playlist expanded block by block
>   leaves out what earlier blocks of the same expansion gathered.
> - **0.85 (2026-10-22)** — **Schedule reload** (§23.70): `/reload-schedule`
>   answers at once, refreshes coalesce in the background; one API request
>   per show instance / show per fetch.
> - **0.84 (2026-10-21)** — **Re-read Tags** (§23.69): tag columns refreshed
>   from the files on disk on request; API endpoint + Library button.
> - **0.83 (2026-10-21)** — **WMA import** (§23.57 addendum): Windows
>   Media Audio always transcoded to MP3 320; `.wma` accepted everywhere.
> - **0.82 (2026-10-21)** — **Stereo Tool preset "R128 transparent"**
>   (§23.47 addendum): shipped preset, true-peak limiter at −1 dBTP,
>   unity gain; library without preset found fully transparent.
> - **0.81 (2026-10-21)** — **Line-in: fresh input.http per slot** (§23.68):
>   the reused companion source did not reconnect on its second start;
>   source.dynamic arm like the webstreams.
> - **0.80 (2026-10-20)** — **Repeat of show, stage 2** (§23.67): live
>   rows of the original become slices of its imported recording;
>   scheduler honours explicit cue values on an item.
> - **0.79 (2026-10-19)** — **Copy show recordings into the library**
>   (§23.66): the playout reports a closed per-show recording, legacy
>   imports a tagged copy as track type "Recordings" linked to the
>   instance; opt-in checkbox under Local Machine.
> - **0.78 (2026-10-18)** — **Repeat of show** (§23.65): content copy of
>   the source's last aired instance shortly before the repeat starts;
>   migration 0071, delete guard (track-type flag dropped again by 0072).
> - **0.77 (2026-10-18)** — **Show recording format selectable** (§23.64):
>   `${SHOW_RECORDING_ENCODER}` in the template, cc_pref
>   `local_recording_format/bitrate`, extension of the last render.
> - **0.76 (2026-10-16)** — **Teaser automation stage 2** (§23.63): calendar
>   dialog "Teasers" (ScheduleController teaser-* actions, link table edits
>   per show).
> - **0.75 (2026-10-16)** — **Teaser automation stage 1** (§23.63):
>   `cc_files.teaser_show_id` / `teaser_type` (migration 0069), virtual
>   smart block criteria, `Block::setFillContext`, planned rows in the
>   exclude filters.
> - **0.74 (2026-10-16)** — **Wall-clock show ends across DST**
>   (§23.62): `ShowService::wallClockEnd`, used by
>   `createUTCStartEndDateTime` for repeats, single shows and rebroadcasts.
> - **0.73 (2026-10-14)** — **Stream metadata per file and track type**
>   (§23.61): `cc_files.icy_forward` / `cc_track_types.icy_forward`
>   (migration 0068), `icy_hide` packet, label builder branch.
> - **0.72 (2026-10-14)** — **Month selection for monthly repeats**
>   (§23.59): `cc_show_days.month_mask` (migration 0067), generator and
>   edit path honour it; **Dangerous Options → Clear Calendar** (§23.60):
>   from now on, on the "this and all following" path.
> - **0.71.1 (2026-10-14)** — `Block::deleteAllFilesFromBlock` gets a
>   balanced transaction like its playlist twin (§23.58).
> - **0.71 (2026-10-14)** — **Smart block query brackets per row, atomic
>   import rows** (§23.58): one criterion chain per field (rows ANDed,
>   "+" rows ORed inside), balanced transaction in
>   `Playlist::deleteAllFilesFromPlaylist`, shared
>   `ImportExportType::atomically()` for playlist and smart block rows.
> - **0.70 (2026-10-14)** — **Import format normalization** (§23.57): new
>   analyzer step `convert_format` - raw ADTS AAC always repacked to M4A,
>   lossless audio transcoded to MP3 320 kbps CBR (setting, default on,
>   original not kept), decision by codec; tags from every format via an
>   ffprobe fill pass; `cc_files.source_md5` (migration 0066) for the
>   duplicate check; `convert_lossless` command for files already in the
>   library; import folder moves failed files to `_failed` instead of
>   deleting them, one extension list for every import path (§23.12
>   addendum); review fixes: original deleted only after filing, encoder
>   cut to 64, analyzer heartbeat 1800 s, migration lock timeout.
> - **0.69.1 (2026-10-14)** — **Import/Export smart block rules**
>   (§23.56 addendum): group semantics as the query applies them (same
>   field in one group = OR, the rest AND), relative dates as number +
>   `unit`, absolute dates in the user timezone, the editor's rule checks
>   in the preview, one transaction per block.
> - **0.69 (2026-10-13)** — **Settings -> Import/Export** (§23.56): calendar
>   objects as CSV/JSON bundle or single files, preview step, dependency
>   order, shows through the New-Show forms, own ZIP reader/writer.
> - **0.68 (2026-10-08)** — **Playout history survives deleted tracks**
>   (§23.55): `cc_playout_history.file_id` ON DELETE SET NULL (migration
>   0065) and the file fields snapshotted into the row's metadata.
> - **0.67 (2026-10-06)** — **Remaining time laid out** (§23.54):
>   `time_filled` = show start to the end of the last row; the show
>   builder picks a "time remaining" smart block against the laid-out
>   budget between its neighbours (picker shared with the autoloading
>   build); "duration in time" blocks fill their duration on air.
> - **0.66 (2026-10-06)** — **Login brute-force brake** (§23.53): fixed
>   windows per address and per user name in the legacy login (429 +
>   Retry-After), reject throttle per address in the DJ harbor auth.
> - **0.65 (2026-10-04)** — **Go-live stage 1: internal URL, listener
>   stream through Apache, TLS host as repo files** (§23.52):
>   `general.internal_url` splits the inside address from `public_url`,
>   outputs on the local Icecast are published as `/stream/<mount>`,
>   Apache includes under `infra/apache/`, Django host/CSRF/proxy
>   settings.
> - **0.64 (2026-10-03)** — **Short jingles, part two** (§23.51):
>   the held-back row is queued when the jingle starts; a refresh in the
>   row's start second no longer catches it up a second time nor tears
>   the ending predecessor down.
> - **0.63 (2026-10-03)** — **Queue-ahead keeps an armed earlier row**
>   (§23.50): consecutive jingles shorter than the lead window were
>   swapped and doubled on air (2026-10-02 23:36).
> - **0.62 (2026-10-02)** — **Per-line-in input gain** (§23.49):
>   `rastatime_linein.input_gain_db` (−20…+20 dB), applied by an
>   `amplify` around the line-in arm (`var.set linein.gain`), pushed on
>   every path that puts a line-in on air.  Closes the deferred item of
>   §23.10.
> - **0.61 (2026-10-02)** — **Catch-up after a planned restart at a track
>   boundary** (§23.48): the track that follows enters its audio by the
>   time the restart took, so a file chain no longer inherits the delay
>   (17:20 test show: +3.9 s to its end).  §23.47 addendum: Stereo Tool
>   live since 17:20 (free version, default preset).
> - **0.60 (2026-10-02)** — **Output processing with Stereo Tool** (§23.47):
>   optional, off by default; `stereotool()` on the whole bus before the
>   outputs, settings in cc_pref, lockout fallback when the fresh
>   instance dies at start, preflight warning.
> - **0.59 (2026-10-01)** — **In-app user manual, RASTATIME-only help
>   menu** (§23.46): `ManualController` renders the repository's
>   Markdown manuals (EN/DE/FR/ES) with Parsedown inside the layout,
>   rewrites the relative links to `/manual/<lang>/<CHAPTER>`; the help
>   menu drops the LibreTime forum and points contribute / what's new at
>   the GitHub project.
> - **0.58 (2026-10-01)** — **Quiet tails play out** (§23.44 addendum):
>   the `old.db_level < -50.` shortcut of the transition function is gone;
>   it dropped a quietly ending track's whole buffered tail and shifted
>   the rest of the show 3 s ahead of its rows.
> - **0.57 (2026-10-01)** — **Exact row times in both directions**
>   (§23.44 addendum): a file after a live item, a live item after a
>   live item and the stop of a live item wait for the row's exact time.
> - **0.56 (2026-10-01)** — **Exact autoloading fill** (§23.19 addendum):
>   intro → outro (real) → autoloading against the laid-out remaining
>   time, strictly in order, never beyond the end; the trial insert,
>   the 5-s margin and the tail trims are gone; the overlap-aware
>   budget for "time remaining" smart blocks closes the gap the
>   crossfade layout opened since 2026-09-29.
> - **0.55 (2026-10-01)** — **Player follows the Stream Label; default
>   cover** (§23.22 addendum): with "Station - Show" the player names
>   the show and shows its image, never a track cover; a default cover
>   (Settings → Widgets → Player, 256 px PNG in cc_pref) closes the chain.
> - **0.54 (2026-09-30)** — **Show image as the fallback cover**
>   (§23.22 addendum): the Stream Player and Now Playing - Track show
>   the running show's image when the on-air item has no artwork
>   (webstream, line-in, cover-less track).
> - **0.53 (2026-09-30)** — **"No Fade during Crossover" as a track type
>   preset** (§23.44 addendum): cc_track_types.no_fade_crossfade
>   (migration 0063), inherited by tracks set to "As the track type"; the
>   playout resolves the effective flag from file + serializer field, no
>   row re-layout (the overlap is unchanged).
> - **0.52 (2026-09-30)** — **Cue points** (§23.45): detection from the
>   library (ffmpeg silencedetect in the legacy app), cue in / out kept
>   inside the file, changes copied into the rows of the upcoming shows
>   and laid out again.
> - **0.51 (2026-09-29)** — **Live item after a file track** (§23.44,
>   addendum): events carry the rows' exact times; a pre-warmed
>   webstream / line-in opens its gate when the file track's audio is
>   over, the stop of a file track lets it run out.
> - **0.50 (2026-09-29)** — **Crossfade per track type, "Exclude from
>   Crossover"** (§23.44): the overlap is decided per transition by one
>   pair rule shared by the row layout and the playout; rows are stored
>   with microseconds and started rows are never re-timed.
> - **0.49 (2026-09-29)** — **UI primary colour as a setting** (§23.43):
>   the hard-coded accent oranges are CSS custom properties fed from
>   Settings → General; PHP derives the shades and the text colours on
>   the accent; single-colour icon images become CSS masks.
> - **0.48 (2026-09-29)** — **Per-user table layouts** (§23.42): the
>   library and timeline layouts (column order and visibility, rows per
>   page, sort) are a per-user preference on the server again - the 1.9
>   state callbacks were dead on DataTables 1.13; the advanced search no
>   longer detours over the saved ColReorder map.  Same day: the state
>   load is synchronous (an async load broke the post-init layout), the
>   library's decorated cells are column renderers (ColReorder rewrites
>   cells from the data), sticky column headers.
> - **0.47 (2026-09-29)** — **Per-track gain on the queue** (§23.41): the
>   gain is applied in front of the crossfade; a bus-level
>   `amplify(override=...)` kept the first track's gain across
>   crossfade transitions (no track marks).  True-peak cap for boosts only.
> - **0.46 (2026-09-28)** — **Loudness Normalization, EBU R128 stage 1**
>   (§23.41): per-file R128 measurement in the analyzer (ebur128), a
>   three-way mode with target loudness and true-peak ceiling in Settings
>   → Streams, gain = target − loudness in the playout, a bus limiter in
>   R128 mode, a re-measurement job for the existing library.
> - **0.45 (2026-09-28)** — **Catch-up at the offset, re-timed running
>   rows** (§23.40): the catch-up enters an in-progress track at its
>   offset; a schedule item's identity is row id + medium (no start), a
>   re-timed running row is rebound instead of restarted, one moved into
>   the future stops and starts again at its new start.
> - **0.44 (2026-09-28)** — **Crossfade metadata** (§23.37): `add()` forwards
>   only the first source's metadata and `cross` replays the ending
>   track's metadata on its tail; the new track now leads every `add`
>   shape and the tail carries no metadata (stream title and Live Text
>   lagged one track).  Patch bump: rendering detail, no new component.
> - **0.43 (2026-09-28)** — **Live Text Info** (§23.39): the "now playing"
>   line as a text file, built by Liquidsoap (`label_for` with its own
>   format, POSTed to `/live-text`), written by the playout into the
>   public web folder, an optional file and an FTP/FTPS/SFTP server; the
>   Stream Label fallback for live sources without metadata is
>   "Station name - Show name" in every format.
> - **0.42 (2026-09-28)** — **TuneIn now-playing from the playout**
>   (§23.38): `TuneInPusher` sends title/artist at every track start,
>   the show name for live inputs and a keep-alive every refresh; the
>   legacy notify push and the Pypo keep-alive are retired.
> - **0.41 (2026-09-28)** — **DJ hand-over fade** (§23.20 transitions):
>   Settings → Streams "Switch Transition Fade" shapes the DJ arms of the
>   bus switch (`bus_dj`: DJ at once, programme fades out under it) and
>   the hand-back (programme arms use `bus_dj` when the outgoing source
>   is a DJ); the field had no effect before.
> - **0.40 (2026-09-27)** — **Show-boundary crossfade** (§23.37): two
>   operator values (track crossfade = real crossfade inside a show,
>   show crossfade = old show fades out while the new show's first
>   track starts at full level; the show value also shapes every input
>   switch), a per-track "No Fade during Crossover" flag (migrations
>   0059/0060: the flagged track keeps the overlap but is not faded),
>   `cross()` around the request queue with a shape variable set by the
>   playout, queue-ahead pushes; the old skip-then-push order (a butt
>   splice in practice) is gone.
> - **0.39 (2026-09-17)** — **Backup stage 3: automatic backups**
>   (§23.35 addendum): a once-registered Windows scheduled task runs
>   `manage.py backup_auto` daily; the command checks due-ness from
>   the UI settings (every N days), reuses the BackupJob and prunes
>   ZIPs past the retention (newest survives).  Slim restore hint on
>   the page; still no scheduler in the code.
> - **0.38 (2026-09-17)** — **Import from FTP server** (§23.36): a
>   second import source; a PHP task fetches audio from an
>   FTP/FTPS/SFTP server into the local Import Folder (mailbox
>   semantics, remote quiet rule), the existing import chain does the
>   rest.
> - **0.37 (2026-09-17)** — **Backup stage 2: media mirror** (§23.35
>   addendum): opt-in robocopy /MIR of the library into
>   `<backup folder>/media`, incremental with purge, verified
>   file-by-file after every run, cancellable and resumable; job
>   phases database → media → verifying with progress in the state.
> - **0.36 (2026-09-16)** — **Manual backup via the UI** (§23.35):
>   Settings → Backup writes one self-contained ZIP (pg_dump custom
>   format streamed into the archive + every config file + manifest)
>   per run into an operator-chosen folder; job state in cc_pref with
>   PID/heartbeat, download proxied through PHP, restore stays the
>   documented offline procedure.
> - **0.35 (2026-09-16)** — **Rendered settings applied by the playout**
>   (§23.34): a fingerprint of the settings baked into `rastatime.liq`
>   (24/7 recording, Main Output, crossfade, stream outputs) is compared
>   every refresh; a change re-renders and restarts LIQUIDSOAP through the
>   planned-restart path (quiet moment or track boundary).
> - **0.34 (2026-09-16)** — **Storage location as a setting** (§23.33):
>   `local_storage_folder` overrides `storage.path`; PHP, API and playout
>   resolve it at run time; a copy → verify → switch job behind Settings →
>   Local Machine moves the library without restarts or database changes.
> - **0.33 (2026-09-16)** — **Media library layout** (§23.32): no
>   `imported/<owner-id>/` level, every stored path root-relative
>   (`cc_files.filepath`/`artwork`, `cc_show.image_path`, the auto-dj
>   logo preference); one-time `storage_flatten` command.  Stage 1 of
>   the operator-selectable storage location.
> - **0.32 (2026-09-15)** — **Scheduler poll fallback removed** (§23.31):
>   the webstream watchdog has one home, the frame counter inside
>   Liquidsoap; the PLAYOUT telnet poll, its machine setting
>   `RASTATIME_WEBSTREAM_WATCHDOG` and the "older render loaded" stop-gap
>   are gone after a quiet week.
> - **0.31 (2026-09-14)** — **Main Output kept open** (§23.30): the local
>   `output.portaudio` never stops (`mksafe` behind the bridge,
>   `fallible=false`), so a bridge underrun no longer re-opens the device
>   with the stale PortAudio device list (crashes, silent wrong device); the
>   bridge is `buffer.adaptative` (drift compensation, switchable).
> - **0.30 (2026-09-13)** — **Stream metadata** (§23.29): the Stream
>   Label, the Off Air Metadata text and the show on air reach the
>   listeners.  The label is written into the packet on the bus
>   (`metadata.map`), the silence fallback announces itself, the live
>   arms insert the show name on the transition source; PLAYOUT pushes
>   the Settings values over telnet on change.
> - **0.29 (2026-09-10)** — **Legacy mpv engine removed** (§23.28).
>   Liquidsoap is the only playout engine; `RASTATIME_PLAYOUT_ENGINE`
>   accepts only `liquidsoap`.  The DJ kick goes to the harbor over
>   telnet (`master_dj.stop` / `show_dj.stop`) instead of the Icecast
>   admin `killsource`; the line-in capture restart callback and the
>   webstream resume re-arm the Liquidsoap sources instead of pushing
>   URLs into the request queue.
> - **0.28 (2026-09-10)** — **DJ logins checked against the UI**
>   (§23.27, addendum 2026-09-10).  The harbors' `auth` callback asks
>   PLAYOUT (`/dj-auth`), PLAYOUT asks the legacy
>   `check-live-stream-auth` (Master Source credentials, the running
>   show's Live Stream Input or registered hosts); the static harbor
>   password is only the fallback while PLAYOUT is unreachable.  Harbor
>   ports and mounts come from `stream.inputs`, i.e. what Settings →
>   Streams shows.
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
>   `rastatime_playout/engine/portaudio_output.py` maps the Windows
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
>   to `<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM-SS> - <show-name>.mp3`.
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
### Step-by-Step Conversion Plan

This section intentionally breaks the project into **small, low-risk tasks**.  
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

To keep tasks small and coherent, use this milestone order:

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
`rastatime_playout.source_switcher` that queries Icecast's
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
and main-output restoration (`rastatime_playout/__main__.py`).

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
LC_MESSAGES/rastatime.po` into a binary `rastatime.mo` at install time
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

*Addendum 2026-10-02:* since the Liquidsoap engine (Phase E,
2026-05-29) the gain is no longer an FFmpeg filter — the .liq wraps
the webstream arm in `amplify({webstream_gain()}, webstream_raw)`
(`interactive.float("webstream.gain", 1.0)`) and PLAYOUT sends
`var.set webstream.gain = 10^(dB/20)` (unity when unset) at every
webstream start (`LiquidsoapPlayoutEngine.webstream_start`); schema, API,
event model and UI below are unchanged.

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
  **Built 2026-10-02 (§23.49)**, in Liquidsoap like the webstream gain
  of today, not through FFmpeg.
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

> **2026-09-17 — quiet-period guard.**  `scanOnce` only imports files
> whose mtime is at least `QUIET_SECONDS` (60 s) old; younger files are
> counted as "settling" and picked up by a later scan.  Precondition
> for network or FTP delivery into the folder: without it a slow upload
> could be moved away mid-write and a failed attempt deletes the source.

> **2026-10-14 — `_failed` quarantine, one extension list (§23.57).**  A
> failed hand-over no longer deletes the source: the file is moved to
> `<folder>/_failed/<same relative path>`, which the scan never enters.
> The scan's own `AUDIO_EXTENSIONS` list is gone; the import folder, the
> FTP fetch, the upload dialog and `CcFiles::createAndImport` share
> `FileDataHelper::getUploadAudioExtensions()`.  The "deletes the source"
> statements below describe the behaviour until 2026-10-13.

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
       <recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM-SS> - <show-name>.mp3
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
`<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM-SS> - <show-name>.mp3` from
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
telnet> var.set recording_path = C:/.../<YYYY-MM-DD HH-MM-SS> - <show>.mp3
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
from `engine.ffmpeg_recorder` to the new `rastatime_playout/
recording_path.py` module; the format is still
`<folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM-SS> - <show-name>.mp3` with
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
| `rastatime.conf` → `general.public_url` | `http://192.168.1.192` | interpolated into RSS feeds, episode download URLs, image URLs, etc. |

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
| **`rastatime.conf` → `public_url`** | Switch from `http://192.168.1.192` to `https://radio.example.com`.  Interpolated into RSS feed self-links, podcast-episode `download_url`, station-image URLs, and a handful of UI-side absolute links. | 5 min + full service restart |
| **Mixed-Content for Icecast streams** | The HTTPS frontend cannot embed `http://localhost:8000/<mount>` audio — browsers block it.  Solve by either (a) Icecast 2.4 native TLS (fiddly on Windows), (b) Apache reverse-proxy `https://radio.example.com/stream/<mount>` → `http://localhost:8000/<mount>` (cleanest), or (c) let Cloudflare/Caddy proxy the streams. | 2-6 h — biggest single chunk |
| **Cookie / session domain** | Currently IP-scoped; Zend usually handles this automatically once `public_url` changes, but verify. | 30 min |
| **API-key + login hardening** | Replace the placeholder `rastatime-api-key-change-before-production` in `rastatime.conf`; verify the `login_attempts` table's brute-force throttle is wired in; consider 2FA (not currently implemented). | 1-2 h |
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
* The placeholder `api_key` in `rastatime.conf` MUST be regenerated
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
| Schema    | `backend/api/rastatime_api/legacy/migrations/0053_add_show_template.py` |
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
| Schema | `backend/api/rastatime_api/legacy/migrations/0054_add_playlistcontents_linein_id.py` | ALTER TABLE ADD COLUMN |
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

**Addendum 2026-10-01 - the exact fill replaces the reserve (operator
specification).**  The operator's rule: intro first, outro second, the
autoloading playlist third, each against the remaining show time,
never overbooked, the last row at most 4 s before the end.  Two findings
against the v8 build above: (1) the remaining time was the sum of the
clip lengths (`cc_show_instances.time_filled`) - since the pair-based
layout of 2026-09-29 the rows overlap by their crossfade, so a show
"100 % full" by sum ended Σ overlaps early (15 music tracks ≈ 42 s of
silence before the outro); the 5-s margin came on top.  (2) The
post-outro cleanup deleted rows by raw SQL without a re-layout, leaving
a hole before the outro.

`AutoPlaylistManager::fillInstance()` now plans with the scheduler's
own pair rule: `chainEnd()` lays a row list out as
`Scheduler::calculateCrossfades` would (`crossfadeOverlapBetween`),
`expandPlaylist()` turns a playlist into the rows it would schedule
(files, static blocks, dynamic blocks via `getListOfFilesUnderLimit`
against the laid-out budget), `insertFitting()` takes the longest
prefix that ends before the show's end - strictly in order, stopping
at the first item that does not fit (variant a) - and inserts it
through the new `Scheduler::scheduleFilesAfter()` (prepared rows,
playlist cue points kept, one transaction).  Order: intro after row 0,
outro after the last row, autoloading after the intro's last row (the
outro shifts later as the scheduler re-lays), then up to four top-up
rounds with the playlist's "time remaining" blocks against the gap
that is left.  No trial insert (no `is_scheduled` poisoning, no
measurement variance), no margin, no trim: `trimTailToReserve` /
`trimTailExcept` are removed, `setReservedSeconds` stays as an unused
scheduler option.  "Repeat until full" repeats the autoloading pass
while it adds rows.

A "time remaining" smart block fills by the SUM of its tracks, so a
pick that meets the budget ends (tracks × overlap) early.
`expandPlaylist` picks up to eight times, each with the budget raised
by the overlap of the previous pick (computed with the real neighbour
rows: the join to a jingle is 0, to music 3 s), and keeps the pick
whose laid-out length comes closest to the budget without exceeding
it; the solver (`SSPSolution`, 50 randomised trials) decides the rest.
Rehearsals on temporary instances (`C:/Temp/optd/ap_fill_test.php
--live`, show 231/232/237/229/230, 8-60 min): 0.0-3.0 s free at the
end in most runs, about 6 s at worst, never an overbook; the 65-min
webstream of test outro 49 is left out as "does not fit".

**Addendum 2026-10-26 - a filler outro follows the content.**  An outro
playlist that contains a "time remaining" smart block (the station's
"Tagesplaylist ... Outro" fillers, alone or behind an outro jingle) is
no fixed end: placed first (step 2) it filled the whole slot and the
autoloading content found no room (23 shows; "Vinyl Hour 247", 59:53
in 60 min, and four shows since 2026-10-23 without any content).
`fillInstance()` now inserts such an outro as step 5, after the content
and the top-up rounds, in its own order against what is left - the
LibreTime order (content, outro jingle, music to the end).
`playlistContainsRemainingBlock()` decides; fixed outros keep step 2.

**Addendum 2026-10-26 (2) - the overrun rule.**  Variant a left the first
item that did not fit out; for an episode show that emptied the show and
Auto DJ filled it (seven shows since 2026-10-23, three of them 0.2-1 s too
long).  The delayed start could not help: it reacts to an overbooking
(`ShowShiftService`, content end past the slot end, next show ticked) and
the exact fill never overbooked.  `insertFitting()` now still accepts that
item as the last row (an overbooking) when `overrunReason()` allows it: a
single item (playlist file / webstream / line-in, static block, block
limited by items) before a directly following show with
`allow_delayed_start` (`nextShowMaySlide()`, gap < 1 s) or within
`OVERRUN_TOLERANCE_SECS` (5); an item of a block with `overflow_tracks`
before such a show or when at least half of it plays before the end.  In
front of rows that stay at the end (a fixed outro) only the sliding next
show allows it.  `expandPlaylist()` tags dynamic-block candidates with
`timed` (time-limited block) and `overflow`.  The overrun is then either
absorbed by the delayed start (A extended, B slid) or cut at A's end like
any overbooking.

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


**Addendum 2026-10-26 - the fill-pass waits for the show's own fill.**
The autoloading build and the fill-pass both select instances starting
within the next hour, but the fill-pass queries later in the same
cycle: when the 1-h mark falls between the two queries, the fill-pass
sees an empty instance the build has not seen yet and fills it with
the Auto-DJ playlist; the build then finds it full (2026-10-26
15:00:00 / 15:01:30, "Vinyl Hour").  The fill-pass query now skips
instances of autoloading shows whose `autoplaylist_built` is still false
- which also keeps it away from request and traffic-alert shows, which
the build deliberately never marks built - and repeat instances without
`filled_from_instance_id` while `RepeatFillService` may still copy into
them (start more than `RECORDING_WAIT_MARGIN_SECONDS` away).
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

**Addendum 2026-10-23 - minutes, and picks of the same expansion.**
Operator request: a window of 30 minutes.  The window of both filters
is now stored in **minutes**: criteria rows `exclude_played_lately_minutes`
and `exclude_artists_lately_minutes` (both within VARCHAR(32)), range
`1..525600` (`Block::EXCLUDE_MAX_MINUTES`), default `1440` (the old 24 h).
Old `*_hours` rows stay readable: `Block::excludeWindowMinutes()` returns
the minutes row, else hours x 60, else the default, and every consumer
(the SQL `INTERVAL 'N minutes'`, the within-block spread, the form value,
the export) goes through it; the next save writes minutes rows (the save
deletes all criteria rows of the block first).  No migration.  Form
elements / ids `sp_exclude_played_lately_minutes` and
`sp_exclude_artists_played_lately_minutes`, inline label "... in the last
N minutes" (`minutes` is an existing gettext string).  Import/Export
writes `*_minutes` keys and still reads `*_hours` keys (x 60).

Second part: a playlist is expanded **block by block in memory** and
inserted afterwards (AutoPlaylistManager::expandPlaylist,
Scheduler::retrieveMediaFiles), so the planned-rows part of the filter
(2026-10-16) could not see what an earlier block of the same expansion
picked - the two "Dayteaser" blocks of one BBC News playlist chose the
same teaser.  The fill context now carries the file ids gathered so far
(`Block::setPickedInFill()`, reset with `setFillContext()` /
`clearFillContext()`); with the tracks filter on they are excluded
(`cc_files.id NOT IN (...)`), with the artists filter on their artists
are.  Both expansions register the ids before every dynamic pick.
Side effect to know: late in the day the "fits today" teaser pool can be
a single file, then the second block picks nothing instead of a repeat.

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

**Addendum 2026-09-30 - the show image as the fallback cover.**  The
operator asked for a cover on webstreams and line-ins "shown in the
stream".  The Icecast stream itself carries text metadata only, so a
picture can appear only where RASTATIME renders: the player, the
now-playing widgets, the radio page.  Rather than a new image per
source (columns on cc_webstream and rastatime_linein, two upload forms,
a serving endpoint), the widgets fall back to the image the running
SHOW already has (`cc_show.image_path`, `/api/show-logo?id=`): the
now-playing payload's `show.current` carries `id` and `hasImage`, and
`paintCover()` in the player and in now-playing-widget.js takes the
track's artwork first, else the show image, else nothing.  The
show-logo endpoint answers a missing file with a redirect to the
station logo, never with 0 bytes, so the <img> cannot hang (the trap
the artwork endpoint has).  The image is served as uploaded - no
thumbnail - which the manual says to keep modest.  A per-source cover
stays an option on top of this (declined for now as not needed).

**Addendum 2026-10-01 - the player follows the Stream Label; the default
cover.**  The Stream Label (Settings → Streams, `stream_label_format`:
0 Artist - Title, 1 Show - Artist - Title, 2 Station name - Show name)
is the operator's decision which level the listener sees; the player's
picture and headline now show the same level.  With 2 the headline is
the show, the station name sits underneath, the *Next* line names the
next show, and the cover chain is show image → default cover - a track
cover never, because the track is deliberately not named.  With 0 / 1
the chain is track artwork → show image → default cover.  The default
cover is the operator's choice over the station logo: an upload on
Settings → Widgets → Player, scaled by GD to at most 256 px and
re-encoded as PNG (base64 in `cc_pref.widget_default_cover`, ~80 KB
for a 1024² photo), served by the public `embed/default-cover` with a
day of caching and a content hash in the URL; without one the route
answers 404 and the chain ends with no picture.  The Now Playing -
Track widget takes the default cover as its last link too but keeps
the track-first order (a track widget by definition).

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
   go through `bus_transition`.  Since 2026-09-27 (§23.37) there is
   one shape, driven by the Default SHOW Crossfade Duration D: the new
   source at full level after a 50 ms ramp (click-free; also keeps
   both `add` elements the same source type, which the 2.4.4 typer
   demands), the old source fading out underneath over D seconds
   (D = 0 → a 50 ms cut).  The earlier "crossfade when D > 0" branch
   (both sources fading over D) is gone.  Since 2026-09-28 the DJ arms
   are not instant any more: `bus_dj` has the same shape with Settings
   → Streams "Switch Transition Fade" as its length (DJ at once, the
   programme fades out under it), and a programme arm taking over FROM
   a DJ (`source.id(old)` is `master_dj` / `show_dj`) uses `bus_dj` as
   well, so a leaving DJ fades out over the same value while the
   programme is back at once.  `transition_length` is the longer of the
   two fades + 0.5 s.  Verified in
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

**House crossfade.**  Settings → General "Default Track Crossfade
Duration" (cc_pref `default_crossfade_duration`) and "Default Show
Crossfade Duration" (`default_show_crossfade_duration`, since
2026-09-27) are read via the Django ORM at render time; the track value
shapes in-show queue transitions, the show value the show boundaries,
the bus transitions and the scheduler's drain (§23.37).
`RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS` /
`RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS` remain the fallbacks for a
missing/invalid key.  A change is applied by the settings fingerprint
(§23.34) or the next PLAYOUT + LIQUIDSOAP restart.

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
  Since 2026-09-15 every scan also logs the main instance's memory
  (`preflight: Liquidsoap memory: PID … MB, … h old, +… MB since the
  first sample … h ago, … MB/h`), so the trend is in the playout log.
- *Monitor clock.*  `clock.assign_new(id="portaudio_clock", sync="auto")`;
  the `buffer()` bridge absorbs the drift between device clock and
  main clock, which is what it was built for.  Correction 2026-09-14
  (§23.30): a plain `buffer()` does not absorb drift, it runs dry; the
  bridge is now `buffer.adaptative` behind `mksafe`.

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
PLAYOUT-only restart), polls itself as a stop-gap *(switch and stop-gap
removed on 2026-09-15 — §23.31)*.  End-to-end in the
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

**Addendum 2026-09-10 — DJ logins: the UI is the source of truth.**
Since Phase C4 the harbors accepted one static password per mount
(user `source`, `stream.harbor.*_password` in rastatime.conf) and
listened on 8001, while Settings → Streams displayed `stream.inputs`
(port 8000, an Icecast-era value) and the Master Source credentials
nobody checked.  Now every login attempt runs through the harbor's
`auth` callback (`_render_dj_auth_function`): a form POST to PLAYOUT's
listener `/dj-auth`; PLAYOUT's `DjAuthenticator` POSTs to the legacy
`check-live-stream-auth` endpoint (api_key-exempt, localhost), which
holds the rules the operator sees — master username/password from
Settings, and for the show mount the show on air right now: a
registered host's login or the show's custom Live Stream Input
credentials.  Verdicts: `ok` / `denied` / `error`; the callback falls
back to the static password only for `error` or an empty body (a
refused connection does not raise in `http.post`), so a DJ can still
broadcast while PLAYOUT or the web application is down.  Passwords
travel in POST bodies on loopback and never reach a log.  The harbor
port and mount are rendered from `stream.inputs.main/show`, so the
readonly fields of Settings → Streams and the rendered script cannot
drift apart; a port already used by an Icecast output is refused with
a warning (Liquidsoap would fail to bind and die).

### 23.28 Legacy mpv Engine Removed — Liquidsoap Only (2026-09-10)

**Context.**  Since the Phase-D cutover (2026-05-28) PLAYOUT has run with
`streaming_handled_externally=True`: Liquidsoap owns local playback, the
Icecast outputs, the DJ harbors, the webstream / line-in inputs and the
recording.  The mpv engine (libmpv monitor plus three FfmpegStreamer
subprocesses re-encoding the same file to Icecast, the Icecast admin
`killsource`, the hot reload of stream outputs and the listener
credentials for relaying /main and /show) stayed in the tree as a
fallback that was never exercised again — about 1,600 lines of dead
code with an `if` at every scheduler entry point.  BACKLOG
"Legacy-mpv-Code-Delete", operator Go 2026-09-10 (work-order point 15).

**Change.**

1. Deleted `engine/mpv_engine.py`, `engine/ffmpeg_streamer.py` and the
   streamer test; `engine/__init__.py` exports only the interface.
   `engine/ffmpeg_linein_capture.py` stays: since option B (2026-09-03)
   it is the active MME feeder path of every scheduled line-in, not a
   legacy remnant, so `_stable_id_to_dshow_audio` did not have to move.
2. `PlayoutScheduler` lost the `stream_outputs`, `read_stream_outputs`
   and `streaming_handled_externally` parameters and every branch behind
   the flag: `_start_streamers` / `_stop_streamers`,
   `_reload_stream_outputs_if_changed`, the mpv relay in
   `switch_audio_source`, `_kick_icecast_source`,
   `_build_icecast_input_url`, `set_listener_credentials`.
3. `__main__` accepts `RASTATIME_PLAYOUT_ENGINE` only as `liquidsoap`
   (unset counts as liquidsoap; anything else aborts the start with a
   CRITICAL line, `_require_liquidsoap_engine`); the `RASTATIME_MPV_*`
   variables are ignored.  `source_switcher.start_listener` has no
   `engine_kind`; the Icecast `listmounts` reconciler is gone.
4. DJ kick over the harbor: `kick_dj_source` →
   `LiquidsoapPlayoutEngine.dj_kick` → `LiquidsoapTelnetClient.harbor_stop`
   → `master_dj.stop` / `show_dj.stop`.  The former Icecast `killsource`
   could not reach a harbor DJ at all (since Phase C4 the DJs connect to
   port 8001); the harbor's `on_disconnect` callback then drives the
   switcher and the resume exactly as for a voluntary hang-up.
5. Two remaining mpv-shaped paths were corrected while removing the
   flag: the line-in capture's watchdog restart callback used to push
   the listen URL through `engine.play` (a request-queue push of the
   mount); it now re-arms the `input.http` companion
   (`linein_start_http` + gate).  The webstream resume after a DJ
   hang-up did the same and now calls `webstream_start` + gate +
   watchdog (`webstream.start` on the same URL answers "already
   started" in the .liq, so a source still running underneath the DJ
   is left alone).

**Consequences.**  One engine, one code path per schedule item type;
the scheduler no longer needs to know which engine it is talking to.
Stream-output changes reach the air only through the re-render of
rastatime.liq plus a LIQUIDSOAP restart (planned restart or operator)
— the Pypo-side hot reload that rebuilt FfmpegStreamer subprocesses is
gone with them.  `stream.internal_listener` in rastatime.conf stays for
the PHP listener-auth endpoint; PLAYOUT no longer reads it.  An
installed service environment that still says
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` keeps working unchanged;
`RASTATIME_MPV_LOG_LEVEL` may be removed at leisure.  The rollback to
mpv described in LIQUIDSOAP_CUTOVER §9 no longer exists; "fix forward"
is the only path, as it has been in practice since June.

### 23.29 Stream Metadata — Stream Label, Off-Air Text, Show Names (2026-09-13)

**Context.**  Settings → Streams has always offered a *Stream Label*
(Artist - Title / Show - Artist - Title / Station name - Show name) and
an *Off Air Metadata* text, and Settings → General the station name.
None of it reached the Liquidsoap script: the PHP side published a
RabbitMQ message that nothing in RASTATIME consumes, and the rendered
script had no off-air handling at all.  Listeners saw Liquidsoap's
default `artist - title` (which happens to equal format 0) and, while
nothing was on air, the last track's title for hours; the AAC and OGG
mounts announced "Unspecified name" because their Name/Description
fields were empty.  Work-order point 8, operator Go 2026-09-13.

**Findings on the replica (what the Liquidsoap 2.4.4 build really does).**

1. `output.icecast`'s `icy_song` hook receives only the standard
   fields (title, artist, genre, comment, ...) - never custom keys,
   whatever `icy_metadata` lists.  A label that needs `show_name` or an
   off-air flag cannot be computed there.
2. `insert_metadata` reaches the bus only when called on the source that
   actually produces the frames the consumer pulls: on the silence
   `blank()` inside its own `fallback` transition, and on the transition
   source (the `add` of the two fades) of the bus `switch`.  An insert on
   an arm that is an operator (`amplify`, `fallback`) or on the source
   under it never shows up.
3. `fallback(replay_metadata=true)` (the default) replays an old packet
   when the arm changes; with the off-air mark in play that ordering is
   not worth having, so the queue/silence fallback runs with
   `replay_metadata=false`.

**Design.**

- `icy_metadata.py`: `IcyPreferences(label_format, offair_text,
  station_name)` parsed from `cc_pref` (`stream_label_format`,
  `off_air_meta`, `station_name`); tolerant parser, ORM reader.
- The renderer writes the values as defaults into the
  `${ICY_METADATA_BLOCK}`: `interactive.int icy_format`,
  `interactive.string offair_text / station_name / bus_show`, the label
  function `icy_label(m)` (0/1/2; `off_air` packets yield the text;
  packets without title, artist, show_name or off_air are left alone),
  `icy_rewrite` = `metadata.map` on the bus writing the label into
  `title` and clearing `artist`, `icy_song_title` as every output's
  `icy_song`, and `icy.status` for diagnostics.  One rewrite on the bus
  means MP3/AAC (ICY), OGG (in-band comments) and the recording tags all
  carry the same label.
- Silence announces itself: `silence_fallback = blank()`; the
  queue/silence `fallback` inserts `off_air=true` + the text in its
  transition to silence, once at startup, and the bus arm
  `bus_arm_scheduled` inserts it on its transition source when the queue
  is not ready.  Live arms (`bus_arm_master/show/webstream/linein`)
  insert `show_name = bus_show()` on their transition source, so a DJ
  or webstream without titles of its own is labelled with the show.
- PLAYOUT: `PlayoutScheduler._sync_icy_metadata` runs every refresh -
  the three values go out over telnet only when they changed
  (`var.set`, raw text after `=`, one line, `=` replaced), `bus_show`
  follows the item on air and every `_on_*_start`; a detected Liquidsoap
  restart resets the "pushed" memory so the fresh instance gets them
  again.  Every telnet command leaks on the Windows build, hence the
  change-only pushes.
- Mounts: empty Name/Description fall back to the station name; Genre
  and URL are rendered.

**Consequences.**  A Settings change is on air within one refresh
(≤ 2 min) with no restart; the script change itself needs one
PLAYOUT + LIQUIDSOAP restart.  Recordings' title tags now carry the
label (artist empty) - the recording is the stream.  Webstream titles
from the source pass through as title/artist packets and are labelled
like tracks.  The replica E2E (`C:/Temp/optd/run_e2e_icy.py`, a test
mount on the production Icecast) covers startup, three formats, queue
drain, the webstream arm via gate and a text change; `probe_song.py`
and `probe_insert.py` are the two findings above as runnable evidence.


### 23.30 Main Output Kept Open — mksafe Bridge with Drift Compensation (2026-09-14)

**Problem.**  The local monitor/Tascam path was `bus → buffer(2.0) →
output.portaudio(fallible=true)` on its own `portaudio_clock` (§23.27).  The
Tascam's sample clock runs about 50 ppm faster than the main clock, so the
bridge ran dry every 10–12 h.  A fallible output stops on an empty source and
re-opens the device once the source is ready again.  PortAudio enumerates the
devices once per process, and the studio display's HD-Audio endpoint appears
and disappears with the display, so the list used for the re-open is stale.
A shorter list gives `MMSYSERR_BADDEVICEID` ("device ID out of range") →
`Invalid_argument("option is None")` in the clock thread → exit 2 → NSSM
restart (2026-09-07, -08, -09, -14).  A different list lets the stale
host-API device id open another device without any error (2026-09-10 21:38,
after a start with the short post-reboot list: Main Output preflight warning
for about 30 h).  Every underrun was also a gap of about 2 s on the Tascam.

**Decision.**
- `output.portaudio(fallible=false, …, mksafe(id="portaudio_safe",
  bus_for_portaudio))`.  Silence fills an underrun; the output is opened once
  per process and never stopped or re-opened.  `fallible=false` turns a
  missing `mksafe` into a start error ("That source is fallible") — the type
  check (`liquidsoap --check`) does not see fallibility, hence the render
  test `test_local_output_bridge.py`.
- Bridge `buffer.adaptative(id="portaudio_buffer", fallible=true, buffer=2.0,
  limit=1.001)`: resampling by at most 0.1 % holds the level, so drift no
  longer empties it.  Flagged experimental in 2.4.4, therefore
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false` renders the plain
  `buffer(buffer=2.0, bus)` again (still behind `mksafe`).  PLAYOUT logs the
  choice at every render.

**Rejected.**  A setting that makes streaming errors non-fatal (not present in
2.4.4, and it would leave a dead output running silently).  An external audio
feeder instead of PortAudio (large, not needed for this).  Disabling the
display's audio endpoint in Windows only makes list changes rarer (reboots
and USB devices remain) — an optional operator measure, not the fix.

**Consequences.**  A device that really vanishes while open still fails the
write and restarts the engine with a fresh list (unchanged behaviour).
`[portaudio_buffer:3] Buffer emptied` should no longer appear from drift; if
a long main-clock stall still empties the bridge, the Tascam hears a short
silence instead of a re-open.  Evidence: the evaluation in the BACKLOG item,
the runtime probe `C:/Temp/optd/bridge_probe.py` (Realtek device, silence,
forced underrun — both bridges start and run dry without stopping the output;
without `mksafe` the engine refuses to start) and the render tests.


### 23.31 Scheduler Poll Fallback of the Webstream Watchdog Removed (2026-09-15)

**Context.**  The 2026-09-07 addendum of §23.27 moved the webstream
watchdog into Liquidsoap (frame counter on `bus.on_frame`) and kept the
scheduler's telnet poll of 2026-09-06 as an opt-in fallback
(`RASTATIME_WEBSTREAM_WATCHDOG=scheduler`) plus a stop-gap: PLAYOUT
probed once per Liquidsoap instance whether the loaded script answered
`webstream.watchdog` and polled itself if not.  The operator's condition
for removing both was a quiet week after Plan A (fresh `input.http` per
slot, 2026-09-08).

**Evidence (2026-09-09 → 2026-09-15).**  No `upstream stalled`; one reap
(2026-09-14 08:15, right after a slot end — the dropped input had
reconnected on its own, which is what the reaper is for); 15 webstream
starts, 14 decoded within 3 s, one in 8 s (2026-09-11 17:06: the first
connection attempt to the cloud encoder failed, the second succeeded 3 s
before the slot, on air on time); nightly restarts clean on 09-12 and
09-13 and correctly skipped otherwise (instance younger than a day).

**Decision.**  Removed from PLAYOUT: the machine setting and
`_webstream_watchdog_mode` (`__main__`); the scheduler's mode switch,
timer poll (`_start/_stop/_arm_webstream_watchdog`,
`_webstream_watchdog_tick`, `_reconnect_stalled_webstream`) and presence
probe (`_liquidsoap_has_internal_watchdog`,
`LiquidsoapPlayoutEngine.webstream_watchdog_present`); from the renderer
the `webstream_watchdog_in_liquidsoap` parameter and its reaper-only
stub.  The default render is byte-identical (before/after comparison).
The telnet commands `webstream.ready` and `webstream.watchdog` stay as
diagnostics.

**Consequences.**  One watchdog, one code path.  A PLAYOUT restarted
against an older loaded script no longer polls; the render warning already
asks the operator to restart LIQUIDSOAP in that case.  Effective after a
PLAYOUT restart; LIQUIDSOAP untouched.


### 23.32 Media Library Layout — No Owner-Id Level, Root-Relative Paths (2026-09-16)

**Context.**  The operator wants the library's location to be a setting
under Settings → Local Machine (like the Import Folder) rather than a
hand-edited `storage.path` in `rastatime.conf`, with the move to the new
`D:` disk as the first use.  A movable root needs one invariant: every
path the database holds is relative to the root.  It was not: show images
(`cc_show.image_path`, 29 rows) and the auto-dj logo preference held
absolute paths under `C:/rastatime/media`, 36 podcast rows carried a
leading slash, and the upstream `imported/<owner-id>/` level (the
importing user's id) was created in five places — the upload path
(`MediaService.php`), the artwork writer (`CcFiles.php`), show-image
uploads and deletes (`ShowImageController.php`), the auto-dj logo upload
(`PreferenceController.php`) and podcast downloads
(`podcasts/download.py`).

**Decision.**
- Layout `<root>/imported/<artist>/<album>/…`, `<root>/imported/artwork/…`,
  `<root>/imported/show-images/<show-id>/…`,
  `<root>/imported/auto-dj-logos/…`, podcast episodes directly under
  `<root>/imported/`.  No owner-id level anywhere (single-operator station;
  `cc_files.owner_id` keeps the ownership).
- Stored paths are root-relative, forward slashes, no leading slash.  PHP
  gets `Application_Common_Storage::toRelative()` / `toAbsolute()`; writers
  store relative, readers (show-logo endpoint, show form preview, auto-dj
  preview) resolve on read and still accept absolute legacy values.  The
  API, the playout (`Path(root) / filepath.lstrip("/")`) and the analyzer
  already joined relative paths with the root.
- One-time migration: the Django management command `storage_flatten`
  (dry run by default, `--apply` moves the entries of `imported/<id>/` one
  level up and rewrites the four kinds of rows in a single transaction;
  a failure rolls the rows back and moves the entries back).  Only owner
  ids that exist as directories (or are named with `--owner-id`) are
  stripped, so a purely numeric artist folder can never be mistaken for
  an owner id and the command is safe to re-run.

**Consequences.**  Stage 2 (the setting and a copy → verify → switch job)
can move the root without touching a single row.  `MIGRATION.md`
§4.4/§4.5 now point at the command instead of hand-written SQL and
robocopy.  Effective for new imports as soon as the PHP files are live
(no OpCache) and, for podcast downloads, after a RASTATIME-API restart; the
migration itself is run once in a quiet moment with a database dump
beforehand.


### 23.33 Storage Location as a Setting — Copy, Verify, Switch (2026-09-16)

**Context.**  With every stored path root-relative (§23.32) the root can
move.  The operator wants to choose it under Settings → Local Machine
like the Import Folder, with the move to the new `D:` RAID disk as the
first use.

**Decision.**
- *Truth:* site preference `local_storage_folder`; empty means
  `storage.path` from `rastatime.conf`, which is thereby the initial
  value only.  `conf.php` keeps checking at bootstrap that the configured
  folder exists, so the old root directory stays (empty) after a move.
- *Resolvers:* PHP `Application_Common_Storage::root()` (per request,
  trailing slash like the config accessor had; all former
  `Config::getStoragePath()` readers switched); API
  `storage.root.get_storage_root()` (15 s cache; file download/destroy,
  podcast download, `storage_flatten`); PLAYOUT `_refresh_storage_root()`
  every refresh from `GET /api/v2/storage/location` (direct file access;
  the API download remains the fallback); the analyzer gets its target
  per import message from PHP.
- *Job* (`storage.move.MoveJob`, one per API process, state persisted as
  JSON in `local_storage_move` with pid + heartbeat): validate (absolute
  local path, no UNC, not nested either way, creatable/writable probe,
  free space ≥ library × 1.1 + 100 MB) → `copying` with robocopy
  `/E /COPY:DAT /DCOPY:T /R:2 /W:2` (resumable) and a progress walk every
  3 s → `verifying` (every source file present at the target with the
  same size, every `cc_files` path resolvable) → `switched` (setting set,
  `old_copy` recorded).  `failed`/`cancelled` leave the partial target for
  a resume; a dead process (API restart) shows as `interrupted`.
- *Import pause* while `copying`/`verifying`: PHP
  `Application_Common_Storage::assertNotMoving()` in the upload path,
  show-image and auto-dj logo uploads, `LocalImportScanTask::shouldBeRun`;
  the API refuses podcast downloads with 409.
- *Access:* the page calls PHP actions behind login + CSRF
  (`preference/storage-location-*`) which proxy to the API on localhost
  with the API key; the API endpoints use the default permission (API
  key or session) — unlike the unauthenticated soundcard endpoints.
- *Watchdog:* preflight `storage_root_unavailable` (error) when the
  effective root is missing or read-only; dashboard banner branch.

**Rejected.**  A delete button for the old copy (operator deletes by
hand); network paths in v1; moving the recording and import folders
along (separate settings, operator changes them by hand).

**Consequences.**  A move needs no `rastatime.conf` edit, no restart
and no database change; the stream is unaffected, imports pause for
the copy.  The first production move (C:\rastatime\media → D:\stor)
is the acceptance test of this section.

### 23.34 Rendered Settings Applied by the Playout (2026-09-16)

**Context.**  Four operator settings are compiled into `rastatime.liq`
at render time: the 24/7 recording (enabled, folder, format, bitrate),
the Main Output device, the crossfade duration and the stream outputs.
A change therefore needed RASTATIME-PLAYOUT (re-render) and
RASTATIME-LIQUIDSOAP (reload) restarted by hand; the UI said so after
Save, and the Main Output had an explicit "Apply now" button that
restarts the chain immediately.

**Decision.**  `__main__._render_settings_fingerprint()` hashes those
settings from cheap database reads (no PortAudio probe).
`PlayoutScheduler._maybe_settings_restart()` runs after every schedule
refresh: the first value after a start is the baseline (the start just
rendered it); a different value arms the existing planned-restart path
(§23.27): `_perform_planned_restart` at once when nothing is on air and
nothing starts within the quiet margin, otherwise `_boundary_restart_pending`
and the restart at the next file-to-file boundary in `_on_file_start`.
The re-render happens in-process (`render_for_restart`), so only
LIQUIDSOAP restarts; the standby source keeps the listeners.  A failed
attempt is retried after 30 minutes; a successful restart records the
current fingerprint as the new baseline.  "Apply now" stays for the
immediate case.

**Consequences.**  Save is enough for the four settings; the change is
live within two minutes plus the wait for a quiet moment or track
boundary (the same guarantees as the nightly restart: name-safe Main
Output or no restart, verified service state).  The first 24/7 hour
after such a restart is a partial file (`audio_start` in the sidecar).

**Addendum (same day).**  The first live run (bitrate 128 → 192,
restart 10:32:35–38) showed that `output.file` truncated the running
hour file on reopen.  `append=true` does not help: the %ffmpeg muxer
truncates regardless (measured), and the build has no native `%mp3`.  The
recorder therefore never opens an existing hour file - it continues in
`<hour>-00.2.<ext>` - and the cue sidecar lists the `parts` with their
creation times.

**Addendum 2026-10-28 - the repeated hour of the autumn clock change.**
The sidecar is keyed by the wall-clock hour the recorder names files by;
on 2026-10-25 both passes of 02:xx (CEST, then CET) landed in
`2026-10-25 02-00.cues.json` - 39 marks with `t` from the same nominal
hour and two `parts` at offset 0, nothing a reader could attribute.
`CueWriter` now works with the instant as well as the wall clock: `now_fn`
may return an aware datetime (its offset is used) or a naive local one
(`astimezone()` honours `fold`, so `datetime.now()` is right in the second
pass too).  Every sidecar gets `hour_start_utc` and `utc_offset`.  When the
primary sidecar of the wall-clock hour carries a different `hour_start_utc`,
the marks go to `<hour>-00.N.cues.json` (`sidecar_part: N`, `recording` =
its own audio part), mirroring the recorder's `.N.<ext>` files; `parts`
of the `.N` sidecar lists only files created from its hour on (60 s
grace), the primary one stops before its sibling.  A sidecar without the
UTC fields (written before this change) is continued as the same hour, a
restart inside a normal hour still adds a part to the one sidecar, and
the spring change needs nothing (the hour is skipped).  Tests:
`tests/test_cue_writer_fold.py` (both passes, part split, normal restart,
old sidecar, naive clock, offset text).  First live case 2027-10-31.  A script changed
by the startup render outside the boot window is applied through the
same path (`render_restart_pending` → reason "rastatime.liq changed at
the playout start"), which closes the last manual restart case: a
template or code update needs only the PLAYOUT restart.

### 23.35 Manual Backup via the UI (2026-09-16)

**Context.**  Backup was CLI-only (`docs/operator/BACKUP.md`): pg_dump,
config copies and a Task-Scheduler recipe.  Work-order point 10 asked
for a Settings page.  The 2026-05-31 evaluation stalled on the missing
async-job infrastructure; the storage move job (§23.33) has since
established exactly that pattern, so stage 1 (manual backup of
database + configuration) reuses it wholesale.

**Design.**  A `BackupJob` singleton in the API process (sibling of
`MoveJob`, `storage/backup.py`): state JSON in the site preference
`local_backup_state` with PID and heartbeat, so the page, a second
API worker and a restarted API agree on what is running; a dead job
surfaces as `interrupted`.  The backup folder is the site preference
`local_backup_folder`, validated like the move target (absolute local
path, created on demand, write-probed, refused inside the media
library).  One run produces one self-contained
`rastatime-backup-<YYYY-MM-DDTHHMM>.zip`:

- `db.dump` — `pg_dump --format=custom`, **streamed straight into the
  ZIP member** (no temp files).  Credentials come from Django's
  database settings — production fills them from `rastatime.conf`
  (operator decision) — and the password travels only as `PGPASSWORD`
  in the child environment.  The binary is found on `PATH` or under
  `C:\Program Files\PostgreSQL\*\bin`.
- `config/<files>` — every file directly inside the config folder.
- `manifest.json` — creation time, database, pg_dump version, contents.

A failed run deletes the partial ZIP, so the list never shows a
half backup.  Five API routes under `/api/v2/storage/backup*`
(status+list, validate, folder, run, download); the download endpoint
only serves names matching the strict backup pattern inside the
configured folder (traversal-safe by construction).  The legacy page
(Settings → Backup, `preference/backup`) talks to PHP proxy actions
(operator login + CSRF; API key server-side); the download is buffered
through PHP — stage-1 archives are megabytes, and media backups
(stage 2) will never travel through the browser.

**Stage 2 addendum (2026-09-17).**  The opt-in **media mirror**
(`local_backup_include_media`): after the ZIP, the job mirrors the
library into `<backup folder>/media` with robocopy `/MIR` (same flags
as the storage move job) — incremental by construction, deletions
purged, so the mirror is always the current library, not a history.
Then it verifies file-by-file (reusing `move.verify_copy`; a mismatch
fails the run).  The job state carries phases (`database` → `media` →
`verifying`) and mirror progress sampled every 3 s; a free-space check
before the run demands library × 1.1 minus what is already mirrored.
Cancel terminates only the mirror (the ZIP is complete by then) and
the next run resumes; a failed run keeps the partial mirror but still
deletes half ZIPs.  The mirror never travels through the browser.

**Stage 3 addendum (2026-09-17).**  Automatic backups follow the
plan above verbatim: the UI stores `local_backup_auto` (enabled,
every_days, retention_days); a **Windows scheduled task** registered
once by the operator runs `scripts/backup-auto.ps1` daily, which
calls the management command `backup_auto`.  The command decides
due-ness itself (newest ZIP older than the interval, one hour of
slack for early task fires), runs the very same `BackupJob` (waiting
for the daemon thread) and then prunes ZIPs older than the retention
- the newest backup always survives and the media mirror is never
pruned.  The page gained a slim Restoring box pointing at the
offline procedure.

**Deliberately not built.**  No restore endpoint: restoring replaces
the running database and stays the documented offline procedure
(BACKUP.md §7, `pg_restore` reads `db.dump` as-is).  No scheduler:
auto-backup (stage 3) will store its settings in cc_pref and run
through a management command registered once in the Windows Task
Scheduler — the worker service remains an idle stub and is not the
place for a first scheduler.

### 23.36 Import from FTP Server (2026-09-17)

**Context.**  Operator wish: a second import source next to the drop
folder, remote suppliers deliver to an FTP server.  FTP has no push,
so RASTATIME polls: `FtpImportScanTask` (legacy PHP task manager, the
same 5-minute piggy-back as the drop-folder scan, plus "Fetch now").

**Design.**  The task downloads audio files from the configured
remote folder **into the local Import Folder** and lets the existing
chain (quiet period, organize, analyzer) do everything else - one
import path, not two.  Transfers run through PHP-curl, which on this
build speaks `ftp`, explicit-TLS `ftps` (AUTH TLS via
`CURLOPT_USE_SSL`, verified against the CA bundle from §INSTALL_APACHE
3.1) and `sftp`.  Config is one JSON site preference
(`local_ftp_import_config`: enabled, protocol, host, port, username,
password, absolute remote path); the password is write-only in the UI
and never logged.

**Mailbox semantics.**  After a download whose byte count matches a
size probe, the remote original is deleted (QUOTE `DELE`/`rm` with
the absolute path); the account therefore needs delete permission - a
failed delete keeps the local copy and warns about the coming
duplicate.  Non-audio files stay on the server.

**Remote quiet rule.**  The replica with a growing file showed that a
post-download size probe alone misses bursty uploads (the probe can
land between two appends).  A file is therefore only fetched when its
size matches a sighting recorded at least 60 s earlier
(`local_ftp_import_pending`, {name: {size, seen_at}}); the
post-download probe stays as the second layer.  Servers that cannot
report sizes fall back to the probe layer alone.

**Bounds.**  Each cycle starts new downloads for at most 60 s
(RUN_BUDGET_SECONDS) so a piggy-backed web request is not held for
long; per-file timeout 240 s with a low-speed abort; the rest is
counted as "left for the next run".

### 23.37 Show-Boundary Crossfade and "No Fade during Crossover" (2026-09-27)

**Context.**  One crossfade value shaped every transition, and — as the
production log showed — the queue "crossfade" was a butt splice: PLAYOUT
skipped the playing track and pushed the next one afterwards, so
Liquidsoap's `cross` fell into the silence arm for a frame
(`Analysis … / -infdB`, then `-infdB / …` one second later) and the two
tracks never overlapped.  Operator decisions (2026-09-27): a real
crossfade inside a show; at a show boundary the old show fades out
while the new show's first track starts at full level at once; the show
value also governs Line-In / webstream switches (the same stream in both
shows stays seamless); start value 1 s; a per-track flag instead of the
never-active 8-second rule - first "Exclude from Crossover", the same
evening refined to "No Fade during Crossover" (the flagged track keeps
the overlap but is not faded itself); the LibreTime Fade-In / Fade-Out
fields disappear.

**Settings.**  `default_crossfade_duration` = Default TRACK Crossfade
Duration (renamed), `default_show_crossfade_duration` = Default SHOW
Crossfade Duration (new, `'1'`).  Both are in the render fingerprint
(§23.34), so a save is applied by the planned-restart path.
`cc_files.no_fade_crossfade` (legacy migrations 0059 + 0060, raw SQL in
`StoredFile`, checkbox in the metadata editor, exposed through the
Django `File` model to the playout).

**Metadata in the transition (2026-09-28).**  `add()` forwards the
metadata of the FIRST source in its list only, and `cross` replays the
ending track's metadata on its buffered tail.  With the tail in front
the new track's packet was lost and the replayed old one passed, so the
ICY title and the Live Text showed the previous track until the next
transition.  Every `add` shape therefore lists the new track first and
the tail is wrapped in `drop_metadata`; the `sequence` shape (show) was
never affected.  Bench (`on_metadata` on the bus, three tones): the
packet now arrives at the audible start of the new track in all five
shapes.

**Liquidsoap.**  `scheduled_x = cross(duration=BUFFER, rt_transition,
scheduled_q)` wraps the request queue ONLY; the silence arm stays
outside (`fallback([scheduled_x, silence_fallback])`), so a track that
ends into silence plays out and a track out of silence starts at once.
BUFFER = max(track, show, 0.5 s) is the tail `cross` buffers from every
track.  The transition function reads the shape from the interactive
string `rt_cross` and the flagged side from `rt_nofade` (old | new |
both | -), both set by PLAYOUT over telnet before each push / skip:

| shape | when | old track | new track |
|---|---|---|---|
| `track` | in-show, natural end | `fade.out(duration=T, delay=BUFFER-T)` — its last T seconds | waits `BUFFER-T`, then `fade.in(T)` — starts at its row start |
| `show` | show boundary, natural end | fades over its last S seconds | follows at the old track's end (`sequence`) |
| `show_skip` | overbook at a show boundary | `fade.out(S, max_duration(S, tail))` from now | `fade.in(0.05)` — at once |
| `track_skip` | in-show skip (layout off) | `fade.out(T, max_duration(T, tail))` | `fade.in(T)` |
| `instant` | silent or empty partner, or asked for | 50 ms | 50 ms |

"No Fade during Crossover" keeps the shape and the overlap: a flagged
NEW track comes in at full level (50 ms ramp) while the old one fades;
a flagged OLD track keeps its level to its end in the natural shapes (a
1 ms `fade.out` with a delay the tail never reaches - `fade.out` fades
whenever its delay is reached OR the remaining time is down to its
duration, and stays silent afterwards) and is cut with a 50 ms ramp in
the skip shapes, where it has to end now.  Both flagged = a plain
overlap.

Bench findings that shaped this (four test tones, left/right channel
separated, 100-ms RMS envelope of the recorded output): (a) a per-track
`liq_cross_duration` on the NEW track sets its head buffer in 2.4, not
the old track's tail — hence the fixed BUFFER and shape variable; (b)
`cross` pre-buffers the tail, so a skip also has a tail — as long as the
track has played longer than BUFFER (a track skipped within its first
seconds is cut hard); (c) `fade.out` on the buffered tail fades from the
tail's start, so the natural shapes use `delay=` (and a `blank` in front
of the new track) to fade the LAST T seconds; (d) `cross` runs its
end-of-track transition alone when the next request is not on the queue
when the tail window opens — the partner must be queued BEFORE
`end - BUFFER`.

**PLAYOUT.**  (d) leads to queue-ahead: `_arm_queue_ahead` fires
`BUFFER + 5 s` before a file row's start (the margin covers copying the
file into the cache, ~2 s, and row layouts whose overlap is shorter than
the buffer); when a file track is on air with audio left,
`engine.enqueue()` sets `rt_cross` and pushes the next track without
skipping (`_queued_ahead`, plus the predecessor it was queued behind).
At the row start `_on_file_start` adopts it.  Whether the predecessor is
cut is decided from the ENGINE's measurement: telnet
`scheduled.remaining` answers `"<rid> <seconds>"` for the request the
queue is on (rid tracked with `on_track`).  If that rid is the queued
successor, cross has already pulled it - the hand-over has happened and
nothing is skipped; otherwise a predecessor with more than
`BUFFER + 1.5 s` left is cut (overbook, `_skip` shape).  The row-based
estimate (`start + cue_out - cue_in`; never the row end, which the API
clips to the show end) is the fallback when the engine cannot answer.
`_on_stop` of the predecessor leaves the queue alone when a successor is
queued ahead (its `engine.stop()` would flush the successor; on clipped
rows STOP and PLAY fire at the same instant).  Without a queued track
the normal path pushes FIRST and skips only on overbook - a skip on an
idle queue would hit the new track.  Shape decision `_cross_mode` returns `<shape>/<nofade>`: different
`FileEvent.instance_id` → show/show_skip, else track/track_skip;
`nofade` = old | new | both | - from the tracks' flags.
`input_transition_seconds` (drain, bus) is the show value.

**Cue points.**  Found in the rehearsals: Liquidsoap 2.4 applies cue
points during request resolution from `liq_cue_in` / `liq_cue_out`
only; the LibreTime names `cue_in` / `cue_out` the engine annotated
since the migration were ignored (every track played from 0 to its end).
Now native keys.  Because the API clips `cue_out` of a track that runs
past its show to the show end, such a track ends by itself at the
boundary and the natural `show` shape runs (old fades over its last S
seconds, new on time) - the `show_skip` path is for tracks whose rows
were not clipped (manual layouts, late starts).

**Legacy scheduler.**  Unchanged: rows keep overlapping by the track
crossfade next to a flagged track as well (the flag changes the fade,
not the timing).  The interim "no offset next to an excluded track"
layout rule of the first version was withdrawn the same evening.

**Known edges.**  A track skipped within its first BUFFER seconds has
no tail to fade; foreign row producers that lay rows adjacent (no
overlap) get the crossfade T seconds early with a bounded,
non-cumulative drift; after an anomaly that leaves the queue idle (a
track shorter than its row) the queued-ahead successor starts up to
`BUFFER + 5 s` early.  Event starts are whole seconds
(`event_isoparse`) while rows carry microseconds, hence the 1.5 s skip
tolerance.

**Rehearsals 2026-09-27.**  Four runs with two test shows (three tracks
overlapping by the track crossfade, an overbooked boundary, a jingle
flagged for the crossover between adjacent rows).  Run 1 found
the clipped-row STOP/PLAY race and the queue flush; run 2 the ignored
cue points and the 1 s start rounding; run 3 the ambiguous remaining
(the measurement belonged to the successor cross had already pulled -
the skip hit it); run 4 passed: `track` at the true end of each track,
`show` with the old track fading over its last second and the new show
on time, the flagged jingle played out in full, `track` at the last
change.  The no-fade shapes were then verified in the bench (four
tones, left/right separated): flagged old track full to its end while
the new one fades in, flagged new track at full level at once while the
old fades, both flagged = plain overlap, overbook = hard cut.

### 23.38 TuneIn Now-Playing from the Playout (2026-09-28)

**Context.**  Settings → TuneIn Settings existed from LibreTime but was
only half wired in RASTATIME: the legacy `notify-media-item-start-play`
pushed file starts, the four-minute keep-alive lived in the old Pypo
fetcher (no longer running - TuneIn drops a display that stays quiet
for five minutes), webstreams and line-ins were never announced, and an
unreachable TuneIn threw inside the notify request.

**Design.**  `rastatime_playout/tunein.py` owns the push.  The scheduler
calls `TuneInPusher.now_playing()` where it writes the cue marker for a
new item (track: title + artist; webstream / line-in: the show name) and
`keepalive()` from the schedule refresh (re-sends the last payload when
the previous push is older than 240 s).  Settings are re-read from
`cc_pref` before every push (a save takes effect at the next item), the
HTTP GET to `air.radiotime.com/Playing.ashx` runs on a daemon thread with
a 10 s timeout, the XML answer's `head/status` decides success, failures
are logged without the partner key and back off until the next
keep-alive.  The legacy PHP push is removed; `update-metadata-on-tunein`
stays as a no-op for older clients.  A live DJ is not announced (the
switcher knows no title); the last item stays on the display.

### 23.39 Live Text Info (2026-09-28)

**Context.**  Other systems (website, displays, aggregators) want the
"now playing" line as a plain text file that is always current.  The
playout only knows title/artist of scheduled files; DJ titles (harbor
ICY) and webstream titles exist in Liquidsoap alone, and the operator
wants the file to match what listeners hear.

**Design.**  Liquidsoap builds the line: the ICY label function is
generalised to `label_for(fmt, m)` (formats 0/1/2, Off Air text, and -
new - "Station name - Show name" for a live source without artist and
title in every format), `icy_label` is `label_for(icy_format(), m)`, and
`livetext_report(m)` = `label_for(livetext_format(), m)` POSTed to the
playout listener `/live-text` for every metadata packet on the bus
(`bus.on_metadata`, hooked before the ICY rewrite so the raw fields are
seen).  `livetext_enabled` / `livetext_format` are interactive variables
the scheduler sets over telnet when the settings change (same refresh
hook as the ICY preferences).  `LiveTextWriter` (playout) dedups
identical lines, writes atomically (tmp + replace) into the public web
folder (`/live/now-playing.txt`, served statically by Apache: the
DocumentRoot is the legacy public folder and the rewrite rule skips
existing files), into an optional local file, and uploads to FTP / FTPS
(`ftplib`, PROT P) or SFTP (a curl with libssh2 - the Windows built-in
curl is Schannel-only) on a worker thread; a stale upload is skipped when
a newer line arrived.  Settings live in `cc_pref` (`live_text_*`, the FTP
block as one JSON row like the FTP import), edited in a new subform on
Settings → General above TuneIn; the FTP password never returns to the
browser.

### 23.40 Catch-up at the Offset, Re-timed Running Rows (2026-09-28)

**Context.**  Two audible restarts of the running track were traced in
the 2026-09-28 log.  (a) After a PLAYOUT restart the catch-up branch of
`_arm_file_event` started the in-progress track from its top ('Fade',
141 s in; the next track then measured 140 s of audio left where the
rows said 2 s and cut it with `track_skip`).  (b) A show-builder edit
of the running show (`POST /showbuilder/schedule-remove`) re-times the
rows that follow, including the running one: row 6252 kept its id but
moved 9 s and got a 2.18 s cue-in.  `_same_scheduled_item` compared row
id AND start, so the refresh declared the row "removed from schedule",
stopped it, and the catch-up restarted the same track from the top one
second before the successor took over.

**Decision.**  (a) The catch-up passes the offset (`now - start`) to
`_on_file_start(key, event, seek)`, which adds it to the cue-in - the
same `liq_cue_in` seek the DJ hand-back resume used all along.  An
offset past the audio plays nothing (the next row follows on its own
timer); a queued-ahead copy of the same track is dropped when the
offset exceeds 1 s, since it would start at the top.  (b) The identity
of a schedule item is row id + medium (`id`: file, webstream or line-in
configuration; line-ins additionally device + channel mapping); the
start is no longer part of it - row ids are serial and never reused.
`refresh()` rebinds a re-timed running row to its new key without a
teardown and keeps the event object that is actually on air (its
timing is the audio truth for the crossfade maths); a running row moved
INTO the future is treated as gone (stop now, it starts again at its
new start).  A stop from the refresh also clears the queued-ahead
bookkeeping, because `engine.stop()` flushes pending requests.  The
queue-ahead re-enqueues a successor whose cues or uri changed under
the same row (the queued request carries the old cues).

**Verification.**  Render/scheduler tests (`test_catchup_offset.py`);
live: PLAYOUT restart mid-track ("Catch-up … entering at +N s",
Liquidsoap seeks) and a show-builder removal on the running show
("rebinding, no teardown" instead of "removed from schedule").

### 23.41 Loudness Normalization — EBU R128, Stage 1 (2026-09-28)

**Context.**  The only level processing was ReplayGain per file, and
the analyzer measured it with ffmpeg's `replaygain` filter — the
ReplayGain **1.0** algorithm (RMS, 89 dB reference), not the BS.1770
measurement behind EBU R128.  Live sources ran unregulated and the bus
had no limiter.  The operator asked for R128 as an option; the
evaluation (BACKLOG) proposed three stages, stage 1 got the Go with a
freely settable target (−23 LUFS as the R128 default).

**Measurement.**  `analyze_loudness` runs after the ReplayGain step:
`ffmpeg -filter ebur128=peak=true` and the summary's integrated
loudness (LUFS), true peak (dBFS, used as dBTP) and loudness range (LU)
land in `cc_files.loudness_lufs / true_peak_dbtp / loudness_range_lu`
(legacy migration 0061; Propel is not regenerated, so
`CcFiles::updateFromArray` persists the three keys via raw SQL, the
Django `File` model carries matching fields for the API).  A silent or
undecodable file keeps the keys absent (NULL = not measured).  The
existing library is measured on demand: Settings → Streams "Measure
missing files now" / "Re-measure all" publish one analyzer message per
file with `options.loudness_only = true` and the file's absolute path;
the analyzer's `Pipeline.run_loudness` measures in place — no metadata
extraction, no move, no import status — and PUTs only the three keys
back (a failure reports nothing).  The ReplayGain 1.0 value stays as it
was; both live side by side.

**Settings and gain.**  cc_pref `loudness_mode` (off | replaygain |
r128; an old database derives it from `enable_replay_gain`, and setting
the mode keeps that switch in step for the legacy readers),
`loudness_target_lufs`, `loudness_true_peak_dbtp`.  `StreamPreferences`
(API `/stream/preferences`) exposes them; `loudness_mode` may be null
for a payload from before the setting.  The playout's
`file_gain_db(file, prefs)` computes the annotate
`replaygain_track_gain`: off → unity; replaygain → value + modifier (as
before); r128 → target − loudness, capped so that the file's measured
true peak never exceeds the ceiling; a file without a measurement uses
its ReplayGain value shifted by (target + 18), the 1.0 reference sitting
around −18 LUFS.  A settings change re-fills the schedule (legacy
`getSchedule()` + `update_schedule` to the playout) like the ReplayGain
modifier did.

**Liquidsoap.**  `${LOUDNESS_BLOCK}` after the replay-gain `amplify`:
in R128 mode `bus = limit(threshold=loudness_ceiling, attack=5.,
release=80., ratio=20., bus)` with `loudness_ceiling` an interactive
float — a sample-peak safety net (true-peak proper needs oversampling;
at a −23 LUFS target the headroom is large).  Mode and ceiling are part
of the settings fingerprint (§23.34), so a change is applied by the
planned restart.  Bench on the installed Windows build
(`xbench/bench_r128.liq`): `lufs()` metering, `normalize(lufs=true)` and
the ffmpeg `loudnorm` filter graph all run; the latter two are reserved
for stage 2 (live sources) and deliberately not on the bus.

**Where the gain is applied (2026-09-29).**  The per-track gain sits on
the request queue in front of the crossfade: `scheduled_g =
amplify(id="track_gain", override="replaygain_track_gain", 1.,
scheduled_q)` and `cross(..., scheduled_g)`.  `amplify(override=...)`
takes the value at a TRACK START; the bus-level amplify of the earlier
layout saw metadata without track marks at the crossfade transitions
(§23.37), so every track of a continuous run played with the gain of
the first one - for ReplayGain since 2026-09-27 and for R128 alike
(bench `xbench/bench_gain.py`: C annotated −4 dB played at A's −10 dB;
with the gain on the queue A −19.7 / B −29.6 / C −13.7 LUFS).  On the
queue each side of a crossfade carries its own gain.  Side effect: the
transition's silence test (`old.db_level < -50`) sees post-gain audio.
The true-peak cap of `file_gain_db` applies to BOOSTS only: MP3s
routinely measure +1..+2 dBTP and a decoder glitch read +15.2 in the
library; attenuating further for that would play the track below the
target, the bus limiter takes the peaks.

**Rejected for stage 1.**  Real-time `loudnorm` over the whole bus
(dynamic single-pass mode pumps on music, adds an ffmpeg clock to the
air chain, makes the per-file measurement pointless); replacing
ReplayGain with the R128 value (the two modes coexist so the operator
can switch back).

**Addendum 2026-10-24 - podcast downloads are measured too.**  The API
downloads episodes itself (`podcasts/download.py`) and writes the
`cc_files` row without the analyzer, so 109 of 134 episodes carried no
loudness values and played with the fallback gain (ReplayGain shifted to
the target, i.e. a flat -5 dB for a row without ReplayGain).  A codec probe
over all 134 files found MP3 (132) and OGG Vorbis (2) only, so the format
normalisation of the analyzer is not needed on this path; the gap was the
measurement.  `podcasts/loudness_queue.py` now publishes the same
`loudness_only` message the Settings button sends
(`SendLoudnessMeasurementToAnalyzer`: exchange `airtime-uploads`, topic,
durable, keys file_id / tmp_file_path / import_directory /
original_filename / options) right after the row is saved; the analyzer
measures and reports through `/rest/media/<id>` as for the button.  A
broker failure is logged and returned as `loudness_queued: false`, the
download succeeds regardless.  The existing episodes are backfilled with
Settings -> Streams -> "Measure loudness" (files without values only).

### 23.42 Per-User Table Layouts for the Library and the Timeline (2026-09-29)

**Context.**  Since the DataTables 1.13 switch (?jq3, retired as a flag
in 3d02d50) the library and timeline tables ignored their state
callbacks: 1.13 knows `fnStateSaveCallback` / `fnStateLoadCallback`,
not the 1.9 names `fnStateSave` / `fnStateLoad`.  DataTables fell back
to its built-in state - browser localStorage per page, dropped after
`iStateDuration` = 2 hours - so column order, visible columns and rows
per page came back as defaults (operator report).  The server copy
(`usersettings/set-library-datatable`) was no longer written.

**Decision.**  The layout is a per-user preference on the server, the
single source of truth: `rtDatatableServerState()` (common.js) loads it
before the first draw and posts it as the DataTables state JSON;
`iStateDuration: 0` (no expiry).  The load is a SYNCHRONOUS request, as
in upstream: with an asynchronous `fnStateLoadCallback` DataTables builds
the table only after the response, while the code right after
`$(...).dataTable()` expects it built - the library's post-init scroll
wrapper then enclosed the whole table with toolbar and pager (they
scrolled away) and the Buttons column pickers found no toolbar (seen
live the same day, fixed the same day).  DataTables saves on every
draw (the timeline redraws on its refresh timer), so only a changed
layout is posted.  Three `cc_pref` user values (JSON; the old
PHP-serialized 1.9 values do not decode and read as "no layout"):
`library_datatable` (dashboard, 38 columns), `library_builder_datatable`
(Schedule Tracks dialog, 37 columns - no Actions column, DataTables
rejects a state with a different column count) and `timeline_datatable`
(the same table on the dashboard and in the dialog).  Searches and the
current page are stripped: a page saved days ago can lie beyond today's
result set.

The advanced search pairs `sSearch_{i}` with `mDataProp_{i}` directly
(`Application_Model_Datatables::findEntries`).  The detour over the saved
`ColReorder` map existed for the 1.9 columnFilter plugin, which searched
a column's ORIGINAL position; the 1.13 filter (`liveColIndex`) searches
its current position, so with a real column order saved again the map
would pair a term with the wrong column.  `getOrderingMap()` is gone.

The library's decorated cells (checkbox, preview icon, cover image,
track type code, scheduled icon, actions) are column renderers
(`mRender`), no longer `fnCreatedRow` edits.  ColReorder rewrites every
cell from the row data (`rows().invalidate("data")`) after a reorder -
a drag, or the saved layout applied after the first draw - and a column
hidden while the rows were created is not in `nRow`; both showed the raw
data (track type id, artwork path, an empty but clickable preview cell).
`fnCreatedRow` only binds the click handlers, on its `cells` argument
(every cell, hidden ones included); the td elements survive an
invalidate.  The column headers of the scrolled tables are
`position: sticky` (dashboard.css).

**Verification.**  Live on the studio machine: dashboard and dialog load
their layout from the server after a reload (`oLoadedState`), no post
for an unchanged layout, the dialog keeps its own 37-column layout; a
hidden-then-shown column and a reordered layout (saved and dragged)
render decorated; toolbar, column headers and pager stay in place while
the rows scroll; the advanced search finds the 241 jingles by track type
in the default and in a reordered column order.

**Addendum 2026-10-24 - visible columns per media type.**  Operator wish
2026-10-23: Line-Ins, Webstreams, Playlists and Smart Blocks need other
columns than Tracks.  The DataTables state above stays the base layout
(column order, sort, rows per page, and the visibility of the type shown
last).  On top of it `library.js` keeps a profile `{type: {mDataProp:
bool}}` per user and per table, stored as `library_columns_by_type` /
`library_builder_columns_by_type` through
`usersettings/get-library-columns` and `set-library-columns` (same
`setDatatableSetting` validation, `table=builder` for the Schedule Tracks
dialog).  `applyColumnProfile()` runs inside `setCurrentTable()` for the
library table - i.e. at page load and on every media-type switch - and sets
each non-fixed column (`ftype`, `checkbox`, `image`, `options` never
change) to the saved value or, without a profile, to the type's default
(`COLUMN_PROFILE_DEFAULTS`: tracks cover/title/creator/type/genre/length/
uploaded/id; playlists + blocks title/description/length/owner/mtime/id;
webstreams the same plus website; line-ins title/description/length/mtime/
id), then rebuilds the advanced-search fields.  A `column-visibility.dt`
event outside the apply writes the current map into the active type's
profile and posts it (debounced 400 ms); the DataTables state save still
runs, so the base layout and the profile agree for the type on screen.

### 23.43 UI Primary Colour as a Setting (2026-09-29)

**Context.**  The interface accent was a hard-coded orange in some 90
places: `#ff5d1a` (RASTATIME), `#ff6f01` (LibreTime, radio page and
preview players), `#ff611f`, a dozen hand-picked shades for hovers,
gradients and the two selected-row tones, a jQuery-UI icon sprite in
orange for icon hovers, and orange PNGs (section arrows, the master
panel's progress strip).  The operator wants a station colour
(Settings → General), everywhere including the radio page and the
player widget.

**Decision.**  CSS custom properties.  `Application_Model_AccentColor`
reads `cc_pref.ui_accent_color` (station-wide, `#rrggbb`, empty =
default `#ff5d1a`) and derives the palette: `--rt-accent`,
`--rt-accent-rgb` (for `rgba()`), `--rt-accent-soft` / `-light` (12 % /
25 % white: the selected-row tones, light gradient tops),
`--rt-accent-dark` / `-darker` (18 % / 35 % black: visited links,
gradient bottoms, borders), and two text colours for use ON the
accent - `--rt-accent-fg` where the orange design had white text,
`--rt-accent-fg-dark` where it had black; each flips only when the
colour's relative luminance makes it unreadable (> 0.45 resp. < 0.18),
so the default orange (0.29) keeps both.  `styleTag()` prints the
palette as `<style id="rt-accent">:root:root{...}</style>` in all six
layouts and in the stand-alone embed views (player, weekly programme);
`:root:root` outranks the default palette that `styles.css` keeps in
`:root` as the fallback, wherever the block lands.  PHP computes the
shades, so no `color-mix()` dependency; the canvas-drawn waveform
timeline reads the variable via `getComputedStyle`.

Single-colour images become CSS masks filled with the accent: the
section arrow sprite (`arrows_collapse.png`) and the icon hovers that
swapped to the orange jQuery-UI sprite (mask = the white sprite at the
icon's position).  The progress strip PNG is a gradient over the accent.

**Out of scope.**  Signal and category colours (Bootstrap warning
orange, the stream-status info box, the static-smart-block legend, the
soundcard mismatch hint, the per-show calendar colours, the show slots'
fill bar in the calendar - fixed orange by operator decision); multi-colour
icons with orange parts (crossfade / fade / cue graphics, operator
decision); the installer's `setup-config.css` (runs before the database
exists).  The widgets' own accents (Now Playing / Weekly Programme /
Multi-View / Track History teal `#459B8F`, Song Request blue) follow the
primary colour too (operator decision the same day): their `--np-accent`
/ `--sr-accent` read `--rt-accent` (fallback: the default orange), the
text on solid accent fills uses `--rt-accent-fg`, and all embed views
print the style block.

**Verification.**  Default palette renders the previous orange on the
dashboard, library selection, pager, storage bar, scrollbars, Upload
heading, New Show form (focus border, arrows), radio page player; a
substituted palette (blue) in the browser switched all of them.

**Addendum 2026-10-26 - secondary colour.**  The operator listed the
blue elements as the "secondary colour": the show progress bar in the
header (`#02cef9` + PNG strip), the active-entry marker of the dashboard
menu and the sub-menus (`#1adeff`), the current track in Scheduled Shows
(`#1adeff`) and the `.btn-new` buttons (`#246b86` / hover `#185b6e`).
Settings → General → Secondary Color (`cc_pref.ui_secondary_color`,
empty = `#1adeff`) works like the primary colour; the same class derives
`--rt-secondary`, `--rt-secondary-fg` (black, white only below luminance
0.18) and, for the buttons' white text, `--rt-secondary-button`: the
colour mixed with black in 5 % steps until white reaches WCAG AA 4.5:1
(a dark colour stays as it is; the default gives `#0e7a8c`), plus a
15 % darker hover.  `styleTag()` prints both palettes in the one
existing block, so no layout changed; `styles.css` repeats the default
secondary palette in `:root`.  The progress strip PNG became the same
white sheen over the colour as the song bar.  Other blues (Bootstrap,
category / signal colours, the bandwidth bar, the widgets' own accents)
are out of scope.

### 23.44 Crossfade per Track Type and "Exclude from Crossover" (2026-09-29)

**Context.**  One house value (Default Track Crossfade Duration, 3 s)
shaped every in-show transition.  The hourly block TOH jingle → day
teaser → news intro → BBC relay is laid out butt to butt; Liquidsoap
started each transition 3 s before the end of the old track, so every
successor ran 2–3 s ahead of its row, and after two transitions the
intro ended 5 s before the relay's row started: silence, every hour
(24/7 recording, 2026-09-29 10:01).  Re-filling the show would have
overlapped the rows by 3 s instead - no silence, but the block 9 s
shorter, the intro cut by the relay and the short jingles all fade.
The operator chose both remedies: a crossfade per track type as the
default and a per-track exception.

**Data.**  `cc_track_types.crossfade_duration` (NULL = house value; the
stock Jingles type starts with 0) and `cc_files.exclude_crossfade`
(legacy migration 0062).  The track editor offers ONE three-way field
"Crossover" - as the track type / No Fade during Crossover / Exclude
from Crossover - that writes `no_fade_crossfade` and
`exclude_crossfade` together, so the two exceptions exclude each other.

**The pair rule** (one rule, two implementations that must agree:
`Application_Model_Scheduler::crossfadeOverlapBetween` and
`PlayoutScheduler._pair_crossfade`):

| Pair | Overlap |
|---|---|
| file → file | the smaller of the two tracks' values (type value, else house track value; 0 for an excluded track) |
| file ↔ webstream / line-in | the smaller of the file's value and the house SHOW value (the bus switch fades with the show value) |
| live → live | the show value |

Never more than the crossfade buffer (max of the house track and show
values, at least 0.5 s) - that is all the tail `cross` holds.

**Row layout (legacy).**  `calculateCrossfades()` lays an instance out
pair by pair and runs after every insert, move and removal.  It stores
the times with raw SQL and microseconds (the Propel setters store whole
seconds; a row that loses its fraction starts before its audio and the
rows drift ahead over a long show), writes only rows that change, and
leaves every row that has already STARTED alone - the playout plays
from those times (`removeGaps()` follows the same rule).
`relayoutFutureInstances([fileId])` runs it for every instance that has
not ended: after a change of a track type's value, of a track's Exclude
mode, or of the house values (which never re-laid anything before - the
origin of the mismatch).

**Playout and Liquidsoap.**  The transition mode grows a third field
when the overlap differs from the house value (`track/-/0.00`); the
engine sends it as `rt_dur` (−1 = house value) next to `rt_cross` and
`rt_nofade`.  The in-show shapes read `d = rt_dur()` at run time:
d < 0.05 → `sequence([old, new])` (the old track plays out, the new one
follows at its end), else the known overlap shape with
`wait = buffer − d`.  A track that takes no crossfade is not faded at a
show boundary either.  Bench (three tones): with d = 0 the successor
starts exactly at the predecessor's end, no gap and no level dip; with
1 s and with the house value it starts that much earlier.

**Tools.**  `C:/Temp/optd/xf_layout_dryrun.php` (the pair rule without a
database; the layout of given instances or of a synthetic mix inside a
transaction that is rolled back) and `xf_relayout.php` (dry run or
`--apply` for all upcoming instances).

**Addendum (2026-09-29): a live item after a file track.**  Event
`start` / `end` stay whole seconds (keys, timers, identity), the rows'
exact times travel next to them as `start_exact` / `end_exact`.  The
audio of a file track leaves the air at *exact row start + clip + chain
lag*; the lag (audio position against the rows) is measured at the push
that starts a chain - onto an idle queue, after a cut, or a catch-up,
where the offset counts - and tracks queued behind it follow
sample-accurately.  The engine is not asked: inside its last BUFFER
seconds a track sits in the cross operator's tail and
`scheduled.remaining` reports nothing for it.  `_hold_for_file_tail()`
delays the gate of a pre-warmed webstream / line-in until that end minus
the overlap of the pair (file to live: the smaller of the track's value
and the show value); `_let_file_run_out()` does the same for the stop of
a file track.  Both give up above `FILE_TAIL_HOLD_MAX_SECONDS` (4 s,
overbook: cut now), while a DJ is on air, and for a cold start (which
has its own start-up time); after the wait they check that no other
item has taken the spotlight.

**Addendum (2026-10-01): the other direction.**  The same whole-second
effect shifted everything after a live item: the file pushed after the
relay started up to a second before its row, the relay's gate closed up
to a second early, and the rest of the show moved forward by that much.
`_wait_for_exact_time(key, when, what)` waits for `start_exact` /
`end_exact` (at most `EXACT_TIME_HOLD_MAX_SECONDS` = 1.5 s; a larger
delay is a late timer or an odd row, acted on at once; nothing while a
DJ is on air) and reports whether the key still owns the spotlight.  It
runs (1) in `_on_file_start` for a fresh push after a non-file
predecessor - not for a catch-up, and not behind a playing file, where
the queue holds the push and an early push is free; (2) in
`_hold_live_start` (the renamed `_hold_for_file_tail`) for a pre-warmed
live item whose predecessor is not a file; (3) in `_on_stop` for a live
item, after the file branch.  Cold live starts keep their start-up
time.  The stop and the successor's start both wait for the same
instant and race there as they did on the whole second.  Measured
2026-10-01 10:00 before the fix: Showteaser 0.6 s before its row, gate
closed 0.8 s early.

**Addendum (2026-10-01): quiet tails.**  The transition function had
inherited a shortcut from the old crossfade: a tail quieter than -50 dB
(`old.db_level`, cross's analysis of the buffered last BUFFER seconds)
was handed over like an empty one - `rt_instant`, a 50-ms fade - which
discards the whole buffered tail, not only its silent part.  A track
ending in a long fade therefore handed over 3 s early, every later row
ran 3 s ahead of the schedule and the playout's row-based model
(`_file_audio_end`, the holds) was 3 s wrong: on 2026-10-01 the relay's
gate opened 2.6 s after the intro was over.  With the R128 gain on the
queue the condition fires on most fade-outs.  The shortcut is removed;
only an explicit `instant` or a tail with less than 0.15 s left takes
the 50-ms path.  A quiet tail is part of the row and plays out - the
cue points (§23.45) are the place to trim it.  Found with an envelope
correlation of the recording against the files (every track of the
preceding show +0.9 to +1.4 s behind its row, the one after the fade
-1.6 s) and reproduced in the bench (`xbench/bench_quiet_tail*.liq`).

**Addendum 2026-09-30 - "No Fade during Crossover" as a type preset
(migration 0063).**  The operator asked for an "Exclude from Crossover"
checkbox on the track type; that preset already exists as Crossfade
Duration = 0 (both give a side value of 0 in `crossfadeOverlapBetween`
and `_track_crossfade`), so it was declined.  What the type level did not
have was the other exception: `cc_track_types.no_fade_crossfade`.  The
effective flag of a track is resolved ONCE, in the playout
(`schedule._effective_no_fade`): the track's own `no_fade_crossfade`
wins; an excluded track never takes the preset (no overlap to keep its
level in); a track set to "As the track type" takes
`track_type_no_fade`, a read-only field of the file serializer next to
`track_type_crossfade`.  The row layout is untouched - the preset
changes the fade shape, not the overlap - so a change of the preset
only pushes the schedule (`Tracktype::save()` reports which of the two
presets changed; a changed duration still re-lays the upcoming rows).
The track editor's three-way field keeps its options; "As the track
type" now inherits both the duration and the preset.

### 23.45 Cue Points: Detection, Validation, Propagation (2026-09-30)

**Context.**  The analyzer detects cue points once, at import
(`analyze_cuepoint`: ffmpeg `silencedetect`, quieter than -60 dB for at
least 0.3 s at the head or the tail).  The schedule keeps its own copy of
a file's cue points in every row (`cc_schedule.cue_in / cue_out /
clip_length`, taken when the row is inserted), and the track editor
accepted any cue out (6.90 s on a 5.97 s file).  Since the crossfade per
track type (§23.44) lays jingles out without an overlap, every silent
tail is heard: all 24 TOH jingles end about a second before their cue
out.  Fixing that by hand meant editing 24 files and refilling every
show that schedules them.

**Model.**  `Application_Model_CuePoints` (legacy):
- `detect(path, length)` runs ffmpeg with the analyzer's filter chain and
  parses `silence_start` / `silence_end`; a silence that reaches the end
  of the file has no end line and counts as open.  The analyzer's rule
  applies: only a silence at the top moves the cue in, only one that
  reaches the end moves the cue out.  The binary comes from
  `FFMPEG_PATH`, else `C:/ffmpeg/bin/ffmpeg.exe`, else the PATH.
- `clamp(cuein, cueout, length)`: cue in never below 0, cue out never past
  the length, at least 50 ms between them (else the whole file).
- `applyToFutureRows(fileId)`: one UPDATE ... FROM cc_files that copies
  the file's cue points into its rows of upcoming instances (`starts >
  now`, `modified_instance = false`) and returns the instance ids.
  `ends` is not touched: `relayoutInstances(ids)` runs
  `calculateCrossfades()` (§23.44, reads `clip_length`) per instance and
  pushes the schedule once.  Started rows are never re-timed.

**Entry points.**  (1) The track editor: `StoredFile::setDbColMetadata`
clamps cue in / out against the length before the save and, when they
changed, propagates and re-lays afterwards.  (2) The library toolbar
button **Cue Points** (`LibraryController::redetectCuePointsAction`,
`library/redetect-cue-points`, selected tracks as `media[]` like
`delete`): detect, store with raw SQL (Propel classes unchanged), collect
the instances of all changed files, one re-layout pass, JSON summary
(measured / changed / skipped).  Files longer than
`DETECT_MAX_SECONDS` (15 min) are skipped - a full decode of an hour
takes about 10 s, and the action exists for jingles.  Detection of a
10-s jingle takes ~0.1 s.

**Decision (operator, 2026-09-30).**  Detection inside the legacy app
("way A") rather than the analyzer with an API-to-legacy callback ("way
B"): one place for measurement, propagation and layout, deterministic
and immediately visible; the price is the detection logic existing twice
(Python at import, PHP on demand) with the same parameters.

**Tools.**  `C:/Temp/optd/cue_dryrun.php`: unit checks of the parser,
the rule and the clamp; detection on library files by id (read-only);
apply + re-layout of one file inside a transaction that is rolled back.

**Addendum (2026-09-30): webstream length.**  A webstream's Default
Length is copied into the rows the same way, so
`applyWebstreamLengthToFutureRows(streamId)` (same UPDATE ... FROM
pattern on `cc_webstream.length` -> `clip_length`, `cue_out`) runs from
`Application_Model_Webstream::save()` for an existing webstream, followed
by `relayoutInstances()`.  A longer relay can push rows past the show
end; the layout does not cut them (the API clips `ends_at` / `cue_out`
for the playout as before), the tool `ws_length_apply.php` reports such
rows before anything is saved.

**Addendum 2026-11-01 - the analyzer never measured cue points on this
machine.**  The ffmpeg build logs the silence filter as
`[Parsed_silencedetect_N @ ...]`; the upstream regex in
`pipeline/_ffmpeg.py` matched `[silencedetect @ ...]` only, so
`compute_silences()` returned an empty list without an error and every
import kept `cue_in = 0`, `cue_out = length` (24,857 of 24,999 library
files, from the first imports in May on).  The Library button above
measures through the legacy PHP path and was therefore the only working
route.  The pattern accepts both prefixes since `686ad377` (regression
test `silencedetect_parse_test.py`); the analyzer suite, now part of
`run_tests.ps1` and of the CI matrix, would have caught it.

**Library-wide re-detection (2026-11-01 15:58, operator go).**
`frontend/legacy/scripts/cue_redetect_all.php` runs the model above from
the command line: `--dry-run` (shardable by `id % N`, retry of skipped
rows from earlier reports) measures and writes a CSV with old and new
values plus outlier flags (cue in > 10 s, silent tail > 30 s, clip < 1 s);
`--apply [--skip-flagged] <csv...>` writes the reviewed numbers in one
transaction with the button's UPDATE, `applyToFutureRows()` per file and
one `relayoutInstances()` pass; `--restore <csv...>` writes the old values
back the same way.  Measured 4 s per hour of audio; the whole library
(1,775 h) took 40 min in four parallel shards.  Result: 19,997 of 24,857
files change, 22 flagged outliers left to the operator, 19,975 applied in
10 s, 65 upcoming instances laid out again, every upcoming row equal to
its file afterwards.  Finding on the way: `escapeshellarg()` turns `!`
and `%` into spaces on Windows, so `detect()` failed on 383 paths (the
button too); it now runs ffmpeg through `proc_open` with an argument
array and reads stderr only (stdout to the null device - reading two
pipes in sequence deadlocked once stderr filled).

### 23.46 In-App User Manual and the RASTATIME-only Help Menu (2026-10-01)

**Context.**  Help -> User Manual opened libretime.org, "Get Help Online"
the LibreTime forum, "Contribute" and "What's New?" the LibreTime
project - none of which describes this fork any more, while the real
manual (EN/DE/FR/ES Markdown under `docs/manual/`, index `USER_MANUAL.md`
at the repository root) was readable only in the repository.

**Decision (operator, 2026-10-01).**  Serve the manuals in-app, rendered
server-side with Parsedown 1.7.4 (`frontend/legacy/library/Parsedown.php`,
one MIT file, frozen, no composer step - the first and only Markdown
renderer in the legacy stack).  Alternatives weighed: an own minimal
renderer (edge cases, maintenance), marked.js client-side (same
dependency question, empty page without JS), static pre-rendering (a
build step every doc change would have to remember).

**Routes.**  `/manual` -> index in the user's UI locale; `/manual/<lang>`
index; `/manual/<lang>/<CHAPTER>` -> `docs/manual[/<lang>]/<CHAPTER>.md`;
`/manual/doc/<repo path>` for any other Markdown below `docs/` (operator
runbooks) and the two root documents the manuals link to.  There is
deliberately **no router route**: the navigation menu assembles every
link with the route that matched the current request, so a custom route
broke the whole menu ("Cannot assemble. Reversed route is not
specified").  The default module route delivers `/manual/de/LIBRARY` as
action `de`; `ManualController::__call()` catches every `*Action` and
reads the path from `getPathInfo()` itself.  Unknown chapters redirect to
the language index; the doc path is whitelisted (`docs/` or the two
root files, `[A-Za-z0-9_./-]`, no `..`).

**Rendering.**  Relative links are resolved against the file's
directory and rewritten to the routes above (fragments kept); anything
outside the whitelist goes to the GitHub blob on `main`.  Headings get
GitHub-style ids (lower case, punctuation dropped, spaces to dashes,
duplicates numbered) so the manuals' `#section` links work.  A language
bar offers the same chapter in every language that has it.  Styles:
`.manual-content` in styles.css (reading-sized type, dark tables, code,
quotes); the layout's sub-menu stays (parent_page Help).  ACL resource
`manual`, allowed for every role.

**Help menu.**  Getting Started (text now "RASTATIME", links the in-app
manual; `PRODUCT_NAME` stays "LibreTime" for API compatibility), User
Manual (in-app), Contribute to RASTATIME (`RASTATIME_GITHUB_URL`),
What's New? (`RASTATIME_RELEASES_URL`); "Get Help Online" removed.
`USER_MANUAL_URL` is now `/manual` (its JS copy and the Streams help
link follow).  Catalogues: "Contribute to RASTATIME" and the revived
"For more detailed help, read the %suser manual%s." in all four
locales (`po2mo.py --all`, Apache restart by the operator).

### 23.47 Output Processing with Stereo Tool (2026-10-02)

**Context.**  EBU R128 stage 1 (§23.41) normalises *files*; live sources
get a static input gain, the bus only a true-peak limiter.  The output is
R128-compliant by construction as long as every source is normalised -
a DJ show is not.  Distribution partners must receive a compliant stream
regardless of source, and the operator wants a defined broadcast sound:
Stereo Tool, as an optional plugin, off by default, because the project
will be offered to stations without a licence.

**Design.**  Liquidsoap 2.4.4 (this build) ships the `stereotool()`
operator (`library_file`, `license_key`, `preset`, `load_type`).  The
renderer puts it on the whole bus after the per-track gain and the
loudness limiter and before the ICY rewrite, so every output - Icecast
streams, the 24/7 recording, the Main Output - carries the processed
signal: `${STEREOTOOL_BLOCK}` in the template, `_render_stereotool_block`
in `liquidsoap_config`.  Settings in `cc_pref`
(`stereotool_enabled|library|preset|license_key`), edited under Settings
-> Streams -> Output Processing; the playout reads them through the ORM
(`_resolve_stereotool`) - the licence key stays out of the HTTP API and
the logs ("licence set / not set") and is written into `rastatime.liq`
like the harbor passwords.  The settings fingerprint carries the key as a
short hash, so a change is applied by the planned Liquidsoap restart.

**Safety (reliability before modernity).**  `liquidsoap --check` does not
load the library (bench 2026-10-02: rc 0 with a non-existent path, the
start fails with "File not found"), and an instance that dies at start is
an NSSM crash loop.  Three nets: (1) the block is rendered only when the
library file exists; (2) `PlayoutScheduler._settle_after_restart` - the
stays-up check after every planned restart - renders again *without*
Stereo Tool and restarts once more when the outcome had it active and the
instance is gone, setting `STEREOTOOL_LOCKOUT` for the rest of the PLAYOUT
run; (3) the preflight scan `stereotool_unavailable` reports whenever the
setting is on but the last render left it off (`STEREOTOOL_STATE`, written
by the renderer).  The broadcast never depends on the plugin.

**Addendum 2026-10-02 17:20 - live.**  Bench with the real library
(`libStereoTool_64.dll`, 111 MB; the `.lib` beside it is the import library
for compiling, not needed): loads, "Valid license: true" without a key
(free version, no licensed features in use), Stereo Tool 11.05 / API 256,
latency 0.09 s, about +3 % of a core.  `liquidsoap --check` still passes
with a missing DLL.  The operator enabled it in Settings -> Streams; the
fingerprint armed the restart, which ran at the 17:20 show boundary: the old
instance shut down cleanly, the fresh one was back after 3 s with all mounts,
no lockout.  Test show (six tracks, default preset, no licence): every track
-23.3..-23.5 LUFS, whole show -23.4 LUFS, true peak -10.2..-11.6 dBTP (the
default preset limits ~10 dB below the R128 ceiling - preset choice open).
Memory: private bytes ~1000 MB (+10 MB/h as before; the preflight metric),
working set trimmed to 300 MB after the start - the soft restart trigger
(1536 MB in the window) is reached after ~2 days instead of ~6.

**Open.**  The licence (the operator buys one next week), the preset by
ear, the memory trend over a week.  Stage 2 (live regulator, §23.41) only
if still needed afterwards.

**Preset (2026-10-21).**  The library without a preset processes nothing
(offline run: a +2.1 dBTP square passes untouched; live: a line-in at
−14.7 LUFS reached the recording unchanged), so the 2026-10-02 figures
were the programme's own peaks.  The operator wants an R128-conformant
stream without an AGC: `config/stereotool/rastatime-r128-transparent.sts`
enables only the Final Limiter (`Pre-amp` 1.135 = +1.1 dB) with
`[Common] Hard limit output=1`, `Oversample limiters=1` and
`Post amplifier` 0.881 (−1.1 dB): unity gain below the ceiling, true
peaks at −1.0 dBTP.  A preset only sets the keys it names; the keys and
sections are those of the standalone application's `stereo_tool.ini`
(`Pre amplifier=10` there explains a +17 dB first attempt; `[HD] R128
mode` is a loudness ceiling and was rejected).  Loudness conformity
(−23 LUFS) stays with the sources: per-track gain for files, Input Gain
for webstreams and line-ins.  Harness `C:/Temp/optd/stpreset/st_run.liq`
+ `st_measure.sh`; README next to the preset.  The Liquidsoap limiter
ahead of Stereo Tool stays as the safety net of the fallback path.

### 23.48 Catch-up after a Planned Restart at a Track Boundary (2026-10-02)

**Observation.**  The 17:20 test show (the first one after the Stereo Tool
activation) ran +3.9 s behind its rows from the first track to the
StationID at its end (envelope correlation of every track head against
the 24/7 recording; the 08:00 block without a restart: +0.30 s).  Stereo
Tool adds 0.09 s, so it was not the cause.

**Cause.**  `_on_file_start` performs an armed boundary restart
synchronously (§23.27: stop, start, back after ~3.8 s) and then pushed the
track at its cue-in, as if no time had passed.  Every later track of the
file chain starts when its predecessor's audio ends (§23.44), so the chain
inherited the delay; a live item or a layout gap would have re-synchronised
it (§23.44 addenda), a pure file chain never does.

**Decision.**  Operator: (a) catch up - the track enters its audio by the
time the restart took, the show keeps its times; (b) leave the chain late
until the next live item - declined.  `_catch_up_after_boundary_restart`
returns the elapsed time since the row's exact start as the catch-up seek
when it exceeds `BOUNDARY_RESTART_CATCHUP_MIN_SECONDS` (0.5 s, timer
granularity); the existing seek path (§23.40) does the rest: cue-in offset,
clip length, chain lag noted at 0.  Nothing changes for a late PLAY without
a restart.  Tests: `test_catchup_offset.py` (restart of 3.8 s -> cue-in
+3.8 s, clip shortened, chain lag 0; 0.3 s -> untouched; no restart ->
untouched).  The nightly restart (§23.27) and the settings restart
(§23.34) use the same path, so a show after the 04:00 window keeps its
times too.

### 23.49 Per-Line-In Input Gain (2026-10-02)

**Request.**  Operator: the webstream input gain (§23.10) for line-ins as
well.  At the R128 level acceptance (2026-10-02) the webstream gain was the
lever that brought every source to −23 ± 1 LUFS; a studio feed could only
be trimmed at the mixer or the interface.

**Decision.**  Operator (option A): the gain lives in Liquidsoap, the same
pattern as `webstream.gain`.  Declined (B): an FFmpeg `volume` filter in
the MME feeder - it would cover the feeder path only (not the dshow
fallback), act in the int16 path before the MP3 encode (a boost clips
there), and change only with a feeder restart (no new value on a
same-device transition, no later live trim).

**Schema / API.**  `rastatime_linein.input_gain_db` FLOAT, default 0
(migration `linein 0005`; a RunPython step keeps the DB default on
PostgreSQL, because Django 4.2 drops it after AddField and an API process
on the previous code would otherwise violate NOT NULL on create).  Domain
`LineIn.input_gain_db`: finite number, −20…+20 dB, kept by every `with_*`
builder, in `to_dict` / `from_dict` (missing key = 0).  REST create and
PATCH accept it optionally (400 outside the range), GET returns it.
Legacy: `Application_Model_Linein::getInputGainDb()`, the dialog field
"Input Gain (dB)" (the webstream dialog's field and strings, translated
DE/FR/ES now for both dialogs), `LineinController::saveAction` clamps like
`WebstreamController`.

**Playout.**  `LineinEvent.input_gain_db` (`None` from an API without the
column = unity).  The .liq wraps the folded arm:
`linein_gain = interactive.float("linein.gain", 1.0)`,
`linein = amplify({linein_gain()}, fallback(…))` - before the bus switch,
so the switch fades, the R128 limiter and Stereo Tool see the trimmed
level.  `engine.linein_set_gain(dB)` converts to linear (unity for
`None` / 0, so no value carries over) and sends `var.set linein.gain`; a
.liq rendered before this answers "variable not found" -> one warning, the
line-in plays at unity.  `PlayoutScheduler._apply_linein_gain` runs on
every path that puts a line-in on air: `_on_linein_start` before its early
returns (a same-device transition keeps the capture but takes the new
value; a DJ-held or pre-warmed line-in opens later with the right one),
the DJ resume (`_resume_scheduled_locked`) and
`_apply_initial_liquidsoap_state` (a fresh Liquidsoap starts at unity).
Not at the T−10 s pre-warm: the gate is closed then and the slot start
sets the value before it opens.

**Effect timing.**  The schedule refresh (120 s) cancels and re-arms every
timer with fresh events, so a changed gain reaches every slot that starts
after the next refresh; a line-in on air keeps its value until its slot
ends (live trim: BACKLOG 💡).

**Tests.**  `tests/unit/audio/test_linein_input_gain.py` (domain range and
type, builders, dict round trip, API create/patch/serialise),
`test_scheduler_linein.py` (start, unity reset, same-device transition,
DJ-held start, resume, fresh Liquidsoap), `test_liquidsoap_engine.py`
(dB -> linear, unity, old script, telnet error, wire form),
`player/test_linein_events.py`, the render test, and the existing
`liquidsoap --check` of the full script with every arm.  Round trip
POST -> PATCH -> GET against a scratch database with the migration,
reverse migration included.

### 23.50 Queue-ahead and Rows Shorter than the Lead Window (2026-10-03)

**Observation.**  The night measurement of 2026-10-02/03 (every file row of
two test shows correlated against the hourly recordings) found the file
chains on their rows to within 0.5 s over seven hours, with one exception:
at 23:36 the layout Sweetlove -> StationID tief (3.2 s) -> StationID Kreisky
(4.9 s) -> Butter aired as Kreisky, tief, 0.2 s of dead air, Kreisky again,
Butter 2.9 s late (and the chain with it to the show end).

**Cause.**  `_on_file_queue_ahead` (§23.44) runs BUFFER + 5 s before a
row's start and, finding a different row on the queue, took it for stale
(a removed or re-cued row) and flushed it.  With rows shorter than those
8 s the queue-ahead of the second jingle fires while the first is queued
and correct, the third's fires while the second is queued; each flush
displaced the real successor, and the displaced rows' own start timers
pushed them afresh behind whatever was playing.  The log shows exactly two
such replacements since the queue-ahead exists, both that night.

**Fix (abbcba2).**  A queued row that is still armed (`_armed_events`,
compared by schedule identity, not key) and starts no later than the new
row stays on the queue; the new row returns and starts the normal way at
its own timer, behind the jingle then playing.  A queued row that vanished
from the armed set, or that moved behind the new row, is still replaced
(the 2026-09-28 re-cue case).  Tests: `test_crossfade_shapes.py` (armed
earlier row stays; vanished row replaced; later row replaced).

### 23.51 Short Jingles, Part Two: Deferred Queue-ahead and the Refresh Race (2026-10-03)

**Observation (test show 12:15, three single StationIDs of 2.7-4.9 s between
tracks).**  The 23.50 fix held: "stays queued ahead" three times, no swap.
Two new defects: (1) behind the 2.7 s jingle 0.6 s of digital silence
(12:40:23) - the music row's own PLAY at its row time left Liquidsoap
0.3 s to resolve the request, cross had no partner; behind the 4.9 s jingle
it worked (+0.21 s, no gap).  (2) At 12:17:55 the 120 s schedule refresh
landed in the start second of a 3.9 s jingle: the refresh declared the
predecessor (end 0.08 s ago) "truncated to past" and stopped it, flushing
the queued jingle, then found the jingle "in progress, started 0 s ago" and
caught it up while its timer PLAY was executing - the jingle aired twice and
the chain ran 3.5 s late until a skip at 12:26.  First occurrence in the
log; with timers on whole seconds and a drifting refresh phase it recurs.

**Fix (1) - deferred queue-ahead.**  `_on_file_queue_ahead` remembers the
row it holds back (`_deferred_queue_ahead`); `_on_file_start` runs
`_queue_deferred_ahead` in its `finally`, which queues that row behind the
now-playing jingle when it is still armed and not the current row.  The
refresh clears the memo (`_cancel_all_timers`); the re-armed queue-ahead
timers rebuild it.

**Fix (2) - the refresh race.**  `_on_file_start` is a wrapper that marks
the row in `_starting` for the duration of `_on_file_start_impl`; the
catch-up branch of `_arm_file_event` skips a row that is starting right now
(schedule identity).  The teardown of a playing row whose end lies less
than 1.5 s in the past is skipped while its successor is queued ahead: the
STOP timer and the queue hand over by themselves.  A row truncated longer
ago (a cancelled show) is still torn down.  Tests: `test_catchup_offset.py`
sections E and F (six tests).


### 23.52 Go-Live Stage 1: Internal URL, Listener Streams via Apache, TLS Host (2026-10-04)

**Context.**  Way A (BACKLOG "Internet-Erreichbarkeit via HTTPS"): the
studio machine itself serves `https://rastatime.example.org` (fixed
public IP), the DJ dial-in stays plain HTTP on :8001.  Stage 0 rotated
every secret and bound PostgreSQL, RabbitMQ and the API to the loopback.
Before stage 2 can point `general.public_url` at the https name, three
things had to stop depending on it.

**Internal URL.**  The backend services called the legacy web app
through `general.public_url` (playout v1 client for the "On Air" light,
DJ login check `check-live-stream-auth`, analyzer import callback
`/rest/media/<id>`, notify).  With a public https name that call would
leave the machine, need hairpin NAT and TLS, and fail when the uplink is
down.  New optional `general.internal_url` in all three schemas (shared
pydantic `GeneralConfig`, legacy Symfony `conf.php` - the `general` node
rejects unknown keys -, `rastatime.conf.example`) and
`GeneralConfig.internal_base_url()`: `RASTATIME_INTERNAL_URL` >
`internal_url` > `http://127.0.0.1` + the path of `public_url`.  The
playout's `_dj_auth_web_url()` follows the same chain (its own YAML read,
no pydantic at that point); `RASTATIME_DJ_AUTH_WEB_URL` still overrides.

**Listener streams.**  `StreamSetting` built `http://host:port/mount`
from the output's Icecast host - `127.0.0.1:8000` for the local one,
useless for any listener.  An output on the local Icecast is now
published as `<public_url>/stream/<mount>`; `infra/apache/
rastatime-stream-proxy.conf` hands `/stream/` to `127.0.0.1:8000` (no
retry blacklisting, 30-s timeout, status/admin/playlists denied), included
by the :80 server and the TLS host (ProxyPass is not inherited).  One
address in the LAN and on the internet, port 8000 never forwarded.
Remote Icecast outputs keep their own URL.

**TLS host as files in the repo.**  `rastatime-https.conf` (443, TLS 1.2/
1.3 with the Mozilla intermediate suite, HTTP/2, HSTS, `X-Forwarded-Proto`,
the API proxies, the stream proxy, http → https redirect only when the
request carries the public host name - the LAN keeps `http://192.168.1.164`)
and `rastatime-acme.conf` (Alias for the Let's Encrypt HTTP-01 challenge
with the front-controller rewrite switched off).  Certificates come from
win-acme's "pemfiles" store into `C:\RASTATIME\certs` (git-ignored).
Apache's `httpd.conf` stays outside the repo; it gains three `Include`
lines (stage 2 for the TLS host).

**Django.**  `ALLOWED_HOSTS` is no longer `*`: public host, internal host,
`localhost`, `127.0.0.1`, `[::1]` and `RASTATIME_API_EXTRA_HOSTS`;
`CSRF_TRUSTED_ORIGINS` from the public origin; `SECURE_PROXY_SSL_HEADER`
and `USE_X_FORWARDED_HOST` so the API behind the proxy knows the real
scheme and host.  Found on the way: the upstream origin slice cut
`http://192.168.1.164` to `http://192.168.1.16` (path `/`), so the CORS origin
never matched; `urlparse` now.  The legacy PHP needs nothing - Apache
terminates TLS natively, `$_SERVER['HTTPS']` is set and
`session.cookie_secure` follows.

**Next.**  Stage 2 (operator): DNS, router 80/443/8001, win-acme, the
three includes, `public_url = https://...`, hairpin NAT or split DNS.
Stage 3: acceptance from outside.

### 23.53 Login Brute-Force Brake (2026-10-06)

**Context.**  With the UI public (go-live 2026-10-06) scanners arrived
within hours.  LibreTime's login counted failures per address
(`cc_login_attempts`) and per user (`cc_subjs.login_attempts`) and never
read either; the per-address INSERT stored the literal `':ip'`.  Windows
has no fail2ban.

**Design.**  Two independent brakes, both without sleeping in the request
(a `sleep()` would pin fcgid workers and be a denial-of-service lever):

- *Per address* (hard): `RASTATIME_LOGIN_IP_LIMIT` = 10 failures inside
  `RASTATIME_LOGIN_IP_WINDOW_MIN` = 15 minutes → `RASTATIME_LOGIN_IP_BLOCK_MIN`
  = 15 minutes.  Fixed window: the counter restarts when the previous
  failure lies outside the window; a block lasts from the last failure.
  `Application_Model_LoginAttempts::blockedSecondsForIp()` and
  `increaseAttempts()` (raw SQL, timestamps compared in the database
  clock via `EXTRACT(EPOCH FROM now() - ts)`).
- *Per user name* (soft): 20 failures inside 60 minutes → 5 minutes
  (`Subjects::increaseLoginAttempts` keeps the window in
  `login_attempt_at`).  Deliberately short so that distributed hammering
  of an administrator's name cannot lock the administrator out.
- `LoginController::indexAction` checks both before any password work on a
  POST and answers **429** with `Retry-After` and a translated message;
  the normal login flow is skipped, the page renders with a fresh CSRF
  hash.  Success clears both counters.  Blocked attempts are logged with
  the address for the planned firewall watcher.
- *DJ harbor*: `dj_auth.RejectThrottle` (limit 5 / window 600 s / block
  900 s, monotonic clock, in-memory per playout process): a blocked
  address is refused before the web application is asked; an accepted
  login clears the address.  A playout restart forgets the state, which a
  brake can afford.

**Schema.**  Legacy migration 0064: `cc_login_attempts.last_attempt`,
`cc_subjs.login_attempt_at` (both TIMESTAMP, nullable); Django models
mirror the columns (`LoginAttempt.last_attempt`, `User.login_attempt_at`),
the API does not use them.  `REMOTE_ADDR` is the real client address:
Apache terminates TLS itself, no proxy in front.

**Addendum (2026-10-06, package c).**  *Reasons:* the legacy check
answers refusals with `X-Rastatime-Auth-Reason` (`no-show`, `not-host`,
`bad-password`); `DjAuthenticator` counts only `bad-password`, so a DJ
dialling in before the show can never be blocked (the header is seen by
the playout only - the client gets accept/deny).  *Visibility:*
`RejectThrottle.snapshot()/unblock()` behind `GET /dj-auth/blocks` and
`POST /dj-auth/unblock` on the loopback listener; the legacy
`Application_Model_BlockedAddresses` merges web (per address / user),
harbor and the watcher's firewall rules for System Status ("Blocked
addresses", unblock per entry, CSRF) and for `rt-blocks.ps1`.  Apache runs
as LocalSystem, so PHP may `Get-/Remove-NetFirewallRule` through
PowerShell (~0.7 s per call; the page refreshes every 30 s).  *Watcher:*
`rt-firewall-watch.ps1` as a 5-minute task (SYSTEM) reads both Apache
access logs and the playout log for the last 10 minutes and creates
`RASTATIME-Block <ip>` rules (24 h, description `until=…; reason=…`),
expiring them itself; private addresses are never blocked.  Still open:
2FA / allow-lists for administrator accounts.

**Addendum (2026-10-08, allow list).**  Operator request after a false
positive locked their home address out: `Application_Model_AllowedAddresses`
(cc_pref `allowed_addresses`, JSON; address or CIDR, IPv4/IPv6 matched by
prefix) is honoured by all three layers - `LoginAttempts` neither counts
nor brakes an allowed address, the playout's `dj_auth.AllowList` (reads the
mirror `config/allowlist.txt` on every mtime change) skips the throttle,
and `rt-firewall-watch.ps1` skips candidates on the list (`skipped … allowed
address`).  System Status: **Allow** on a blocked row (unblock everywhere +
add) and the table *Allowed addresses* (add by hand, Remove); `rt-blocks.ps1`
prints the list.  LAN addresses stay exempt by the watcher's private-address
rule regardless.

### 23.54 Remaining Time: Laid-Out `time_filled` and the Smart-Block Budget in the Show Builder (2026-10-06)

**Context.**  The operator filled a show with a "time remaining" smart
block (three music tracks) and saw −6 s free; a 6-s jingle in the middle
made it +3 s over, at the end 0 s.  The footer was right: rows overlap by
their crossfade (pair rule of 2026-09-29), and the jingle (crossfade 0)
breaks one 3-s overlap.  Wrong was the starting point:
`cc_show_instances.time_filled` was `SUM(clip_length)`, so
`getSecondsRemaining()` - and with it the budget of a "time remaining"
block in the show builder (`Scheduler::retrieveMediaFiles`), the
calendar's fill bar, `getIsFull()` and the Auto DJ threshold - ignored
the overlaps: a sum-exact fill ends (music pairs × 3 s) early.  The
operator's standard hour (3 × 12-minute block, StationID between, "time
remaining" last) rehearsed at 27 s free with `time_filled` = 3600 s
("full").

**Decision.**  (1) `time_filled` is the laid-out length: `MAX(ends) −
starts` of the instance (`CcShowInstances::computeDbTimeFilled`;
`ShowShiftService` writes the same expression), computed after
`calculateCrossfades()` has laid the rows out, so the footer, the fill
bar, "is full" and `getSecondsRemaining()` agree.  (2) The show builder
picks a "time remaining" block the way the autoloading build does:
`Scheduler::pickRemainingBlock()` (moved out of
`AutoPlaylistManager::expandPlaylist`, now shared) raises the budget by
the overlap of the previous pick, up to 8 rounds, and keeps the laid-out
closest fit ≤ budget (the least overbook when nothing fits - the caller
checks the real end).  `laidOutLength()` lays a candidate list out between
the real neighbours of the insertion point (`neighboursOfInsertionPoint`,
the cursor row handed down from `insertAfter`), and the tally over a
playlist's items uses it instead of the clip sum.  Blocks limited by
*Duration in time* keep the sum semantics (an operator's "12 minutes" is
the sum of the tracks); the last block absorbs the difference.

**Rehearsal.**  `remaining_probe.php` (C:\Temp\optd; temporary blocks and
a temporary playlist on a temporary instance of show 534): before, 3600 s
sum / 3573 s laid out / "full"; after, a 12-minute playlist and a bare
"time remaining" block end 0.02 s before the show's end with
`time_filled` 1799.98 s; the autoloading fill is unchanged (3.0 s free on
a 10-minute slot).

**Addendum (2026-10-06, evening).**  *"Duration in time" is on-air
time.*  With the end of the show exact, the operator's station IDs still
drifted 9/18/27 s early in the hour because a 12-minute block counted the
sum of its tracks (three 3-s overlaps lost).  Operator decision: "12
minutes" means 12 minutes on air.  `pickDynamicBlock()` now hands a
"minutes"/"hours" block to `pickRemainingBlock()` with its own duration as
the budget (`$asDuration`), and `Block::getListOfFilesUnderLimit($show,
$timeOverride)` / `getListofFilesMeetCriteria(…, $timeOverride)` let the
raised budget replace the stored duration limit; "number of tracks" blocks
are untouched.  Rehearsal of the standard hour: station IDs at 12:00.0,
24:06.9 and 36:18.8 (each block 720.0 s laid out), 0.02 s free at the
end.  A block's length shown in a playlist (`getDynamicBlockLength`,
the limit itself) now equals what it airs.

### 23.55 Playout History Survives Deleted Tracks (2026-10-08)

**Context.**  The operator noticed in LibreTime that deleting a track from
the library removes its rows from the playout history, and ruled that
deleting a track, a webstream or a line-in must never touch the history.
RASTATIME inherited the cause: `cc_playout_history.file_id` was declared
`ON DELETE CASCADE`, and a file row carried nothing but the show name -
title, creator, length, composer and copyright were read live from
`cc_files` by the report.  Webstream and line-in rows were already safe:
no foreign key, name and label copied into the metadata when they air.

**Decision.**  Two parts in one legacy migration (0065, schema 65): the
foreign key becomes `ON DELETE SET NULL`, and the five file fields the two
default templates show (Log Sheet: title, creator; File Summary: title,
creator, played, length, composer, copyright) are copied into
`cc_playout_history_metadata` for every existing file row that lacks
them.  `HistoryService::insertPlayedItem` writes the same five keys for
every new file row.  A deleted track's row thus falls into the report's
"null file" branch and renders from the metadata, exactly like a webstream
row; the *File Summary* keeps grouping by `file_id`, so it counts tracks
that still exist.  The Django model keeps `on_delete=DO_NOTHING` (the
database rule decides, as before); no Propel regeneration.  The library's
*Play Count* column counts rows with a file reference, unchanged.

**Operation.**  The migration runs on the operator's go, after a fresh
backup and outside a show boundary (`manage.py migrate`, then API
restart); the writer change is live immediately and harmless before the
migration (extra metadata keys).

### 23.56 Settings → Import/Export (2026-10-13)

**Decision (operator 2026-10-11/13).**  Building the calendar through the
New-Show dialog does not scale; the operator asked for a CSV import of
shows with every dialog field, an export of equal rank, logos in a ZIP
(variant a), a `content` column (stage 1: the autoloading playlist), the
custom live password never in the file, and the same for playlists, smart
blocks, webstreams and podcast subscriptions - importable together or one
type at a time.  Menu: Settings → Import/Export (admin resource
`importexport`).

**Shape.**  `ImportexportController` (index, preview, import, export,
template) → `Application_Service_ImportExportService` (bundle parsing,
CSV with delimiter detection and BOM, token staging under the system temp
folder, preview, import, export, template, README) → one
`Application_Service_ImportExportType` per object type: `Webstreams`
(`Webstream::analyzeFormData/save`), `Blocks` (JSON; criteria rebuilt as
the editor's name/value list for `Block::saveSmartBlockCriteria`, read
back via `getCriteria`), `Playlists` (`items` as `kind:ref` list,
`Playlist::addAudioClips`), `Podcasts` (`PodcastService::createFromFeedUrl`
+ imported_podcast options), `Shows` (the dialog's field array →
`ShowFormService::validateShowForms` incl. `checkOverlappingShows` →
`ShowService::addUpdateShow`; logo copied like `Rest_ShowImageController`).
Import order = dependency order webstreams → blocks → playlists →
podcasts → shows; objects created earlier in the same run are resolvable
by later rows ('pending' names in the preview, 'created' ids on import).
Names are the keys; conflict mode skip|replace (never for shows).  Every
row is validated twice: for the preview and right before it is written.

**Why an own ZIP class.**  The station's PHP has no ext-zip and the
feature must run on a plain install: `Application_Common_Zip` writes
deflated entries and reads stored/deflated ones (no ZIP64, no
encryption).  New classes under `application/common/` need `composer
dump-autoload` (Composer classmap), unlike services/controllers/forms,
which the Zend resource autoloader finds - noted in UPGRADE.md.

**Export semantics.**  Shows with an upcoming instance, each row starting
at its next instance (so an export is importable without touching the
past); `repeat_end_date` is inclusive (cc_show_days.last_show is
exclusive); the custom password is omitted.  Podcast episodes are not
exported (the feed delivers them).  Static block contents are not
exported, only their criteria.

**Verified 2026-10-13.**  CLI probe (`C:/Temp/optd/importexport_test.php`,
non-persistent auth + unit-test session): template (7 entries), full
export (5/32/24/4/25 rows), round-trip preview (every existing name
skipped, every existing show refused with the dialog's overlap message),
synthetic bundle imported (webstream with gain, block with two OR groups,
playlist file+stream+block+line-in, 2027 show with Mon/Wed days, 10
instances, DJ, logo, autoloading playlist, random custom password) and the
overlapping second row refused at import time; cleanup left nothing.
Open: content stage 2 (explicit item list per instance), replace for
shows, podcast episodes.

**Addendum 2026-10-14 - smart block rules (operator Go 2026-10-14).**
Two findings in `blocks.json`, both reproduced with throwaway blocks.
(1) The README and the manual said "same group AND, groups OR".
`Block::getListofFilesMeetCriteria` keys the rules by field
(`getCriteria`; the field+group key of `getCriteriaGrouped` only feeds
the editor), sorts each field's rules by group and calls `addOr` while
the group repeats, else `addAnd`: rules of the same field in one group
are alternatives (the editor's "+" rows, which keep the row's field),
everything else is ANDed.  Measured on editor-made blocks: Rock + Indie
in one row 10,312 = 5,210 + 5,102, as two rows 0.  Propel attaches
`addAnd`/`addOr` to the existing criterion of the same column, so a field
in two groups that both carry alternatives nests to the left:
(Rock + Indie) / (Electronic + World) gave 2,923 = World alone, i.e.
((A or B) and C) or D.  That is an editor-level limitation; it is
documented and the query fix deferred (BACKLOG, no live block has the
pattern).  The template example (Pop and BPM in group 0, Electronic in
group 1) selected nothing; it now reads (Pop or Electronic) and BPM > 110
and uploaded in the last 90 days.
(2) `storeCriteriaIntoDb` appends `' ' . $datetimeunit . ' ago'` for
before/after/between, the unit coming from `sp_criteria_datetime_select`,
which the import never posted.  The undefined variable became an
ErrorException (global handler), and because the method deletes the old
rules first and a new block row exists before its rules, the failed row
left a block without rules (= the whole library, 21,651 files); with
*replace* the existing block's rules were gone.  The export wrote the
stored "7 day ago" (which would have stored "7 day ago  ago" = seven days
in the future) and absolute dates in UTC, which the import read as user
time (a round trip moved them by the UTC offset).
Fix, all in `ImportExportBlocks`, `Block.php` untouched: relative dates
travel as `value` + `unit` (+ `extra_unit` for between), the stored and
earlier exported "<n> <unit> ago" is still read; absolute dates are
exported in the user timezone, as the editor shows them; `parse()` runs
the editor's rule checks (modifier fits the criterion's type, empty
value, second value for between / is in the range, relative number +
unit, dates, `HH:MM:SS` durations, numbers, length against the column)
so the preview names them; `create()` runs in one Propel transaction.
Verified with the CLI probe loading the worktree class: all 32 live
blocks pass the checks (replace preview); a round trip of an editor-made
block (after 7 days, between 30 and 7 days, mtime > 2026-01-01) stores
exactly the original rows; the legacy forms ("7 day ago", "30 Days",
"Before"/"Hours") normalise; 13 malformed rules are each named in the
preview; a rule that fails at the INSERT (600 characters) rolls back -
the replaced block keeps its 14 rows, a new block leaves nothing; one
"uploaded in the last 7 days" rule selects 21,330 files, as SQL does.

**Addendum 2026-10-25 - users.csv.**  `Application_Service_ImportExportUsers`
(columns `login, type, first_name, last_name, email, cell_phone, skype,
jabber, password`; the login is the key) is the first type in `ORDER`,
because `shows.csv` names its DJs by login; a show row whose DJ the same
bundle creates gets a note in the preview instead of "DJ not found".  The
export never contains passwords (the column stays empty; the stored values
are unsalted MD5, see BACKLOG).  On import the column sets the password of
new users only, hashed through `Application_Model_User::setPassword`;
without it the account gets a random one.  *replace* updates names,
e-mail, phone, Skype, Jabber and type of an existing login, never its
password; it refuses the super admin, a type change of the importing
admin's own account and taking the admin type from the last admin (checked
again right before each write, so a bundle that demotes both admins stops
at the second).  Type values `admin`, `program_manager`, `dj`, `guest`
(empty = guest); `superadmin` is unknown.  The page stays admin-only (ACL
`importexport`).  Verified with the service in one rolled-back
transaction: export without passwords, create with and without password,
duplicate login, bad e-mail, super admin, skip vs. replace (password hash
unchanged), own account, last admin.  Same day: logos `.webp` are staged
from a bundle and accepted by the show import (WebP logos, 2026-10-25).

### 23.57 Import Format Normalization (2026-10-14)

**Context.**  Operator question 2026-10-14: which files in the library are
FLAC or WAV, and should they be converted and imported again?  A
read-only probe by codec (ffprobe, not the mime column) found two: id 603
(FLAC) and id 604 (WAV).  The import path showed three further gaps.
(1) A raw ADTS `.aac` was filed as it came: ADTS has no index, so its
length is estimated from the bitrate (about 1.9 s too long on the files
that showed it - the row is laid out with the wrong length), it cannot
carry tags, and one with an ID3v2 header failed the import outright
(mutagen `HeaderNotFoundError`).  (2) mutagen's easy mode reads no tags
from a WAV file (it returns raw ID3 frame keys there), no RIFF INFO, no
Vorbis DESCRIPTION and no MP4 freeform atoms; the Expiry reader (§23.11)
only knew the ID3 TXXX frame.  (3) The import-folder scan accepted
`.oga`, `CcFiles::createAndImport` refused it, and the scan then deleted
the refused source (§23.12).

**Decisions (operator 2026-10-14).**

* **Lossless audio is converted on import, to MP3 320 kbps CBR with
  ID3v2.3 tags.**  AAC in M4A was the other candidate (smaller for the
  same quality), but the Expiry tag (§23.11) has no standard home in MP4:
  a `com.apple.iTunes` freeform atom is a best effort that other tools
  drop.  MP3 keeps Expiry as the TXXX frame the reader has always used,
  and almost the whole library is MP3 already.
* **The lossless original is not kept.**  It is deleted once the verified
  conversion is filed in the library; no archive folder.
* **Default on.**  cc_pref `convert_lossless_to_mp3`; while the key is
  absent the setting reads as on.
* **Lossy audio (MP3, AAC, Ogg Vorbis, Opus) is never re-encoded** - lossy
  to lossy only costs quality.
* **Decided by codec, not by extension.**  The codec of the first audio
  stream as ffprobe reports it: PCM (`pcm_*`), FLAC, ALAC, WavPack, APE
  and TTA count as lossless, so an `.m4a` holding ALAC is converted and a
  `.wav` holding MP3 data is not.  Raw ADTS is recognised by the ffprobe
  format name `aac`, whatever the extension.
* **Raw ADTS is always repacked into `.m4a`**, whether the setting is on
  or off: a stream copy, no quality cost, a real index and tags.
* **BELOW_NORMAL priority** for the step's ffmpeg and ffprobe processes:
  a batch import must not take CPU from Liquidsoap and Stereo Tool on the
  on-air machine.  Timeout max(120 s, 1.5 x length); when the length is
  unknown it is estimated from the file size at 100 kB/s.
* **Fallback: import the original unchanged.**  The conversion must never
  cost an import; any error (probe, ffmpeg, output check, tag write) is
  logged as a warning, a partial output is removed, the pipeline goes on
  with the original.
* **Podcasts are out of scope.**  Episodes are downloaded by the API and
  written straight into the library (no analyzer run), and feeds deliver
  MP3 or M4A in practice (BACKLOG).

**Pipeline.**  One new step, `convert_format`
(`rastatime_analyzer/pipeline/convert_format.py`), between
`analyze_metadata` and `analyze_duration`:

```
analyze_metadata -> convert_format -> analyze_duration -> [analyze_cuepoint]
  -> analyze_replaygain -> analyze_loudness -> analyze_playability -> organise_file
```

Every later step measures the file that ends up in the library.  The step
may hand back a new path and file name (`Song.flac` -> `Song.mp3`;
`organise_file` keeps the stem and takes the new suffix).  It writes to a
temporary `<stem>.part-xxxxxxxx<suffix>` next to the target, checks the
result (codec; for MP3 the length within max(1 s, 1 %) of the source - not
for ADTS, whose source length is the estimate being corrected), writes the
tags into the temporary file and renames it with `os.replace` (three
tries 0.5 s apart, a virus scanner may hold a fresh file).  The step
itself never deletes the original: `run_analysis` deletes it
(`remove_original`, same retries) only after `organise_file` has filed the
converted file, and when any later step fails - or the analyzer is
stopping - it removes the converted file (`discard_converted`) and leaves
the original in `organize/` exactly as without the conversion.  So a
failed import keeps the original, and a message RabbitMQ redelivers after
an analyzer restart still finds it (review finding 2026-10-14: the first
version deleted it right after the conversion).  The result carries
`source_md5` (the md5 of the original) and the re-read properties of the
new file (mime, filesize, md5, bit_rate, sample_rate, channels, length,
encoder); a property of the original never survives.  A file without a
title tag gets the name it is filed under as `track_title`
(`Interview.mp3`) - the legacy app titled the row with the hand-over name
(`Interview.wav`), which no longer fits.  MP3 details: `libmp3lame -b:a 320k`, `-map_metadata -1`
plus explicit tags from the metadata dict (title, artist, album, genre,
year, track, composer, copyright, label, ISRC, BPM, language, comment,
Expiry as TXXX), a JPEG / PNG cover copied as APIC "Cover (front)",
32 / 44.1 / 48 kHz kept, other rates resampled to 44.1 kHz, more than two
channels mixed down to stereo.  M4A details: `-c:a copy -movflags
+faststart`, tags via EasyMP4, Expiry, ISRC, LABEL and LANGUAGE as
freeform atoms.

**Tags from every format.**  `analyze_metadata` keeps the mutagen pass
but no longer lets a mutagen exception abort the import; afterwards
ffprobe (format tags merged with the first audio stream's tags, keys
lower-cased) fills every field that is still empty - title, artist,
album, genre, comment / description, year, composer, copyright, label,
ISRC, BPM, language, mood, website, encoder, track number / total - plus
sample rate, bitrate, channels, length and mime when mutagen gave none
(Opus, a raw ADTS file with an ID3v2 header).  Expiry falls back to an
`expiry` tag in any format, validated like the ID3 path.  The MP4 / MKV
stream language `und` is ignored.  Side effect: `encoder` is now filled
for almost every file ("Lavf...", "LAME...").  It prefers TSSE / Vorbis
ENCODER (the software) over TENC ("encoded by", a person) and is cut to
64 characters: `cc_files.encoder` is VARCHAR(64), and the legacy app cuts
only the track editor's fields - a longer TSSE ("Audiograbber 1.83.01,
LAME dll 3.92, 320 Kbit/s, ...") made PostgreSQL reject the import
callback (400, no retry, the row ended as a failed import).
`CcFiles::validateFileArray` cuts `encoder` (64) and `encoded_by` (255)
as well, so the legacy app is safe whatever an analyzer sends.

**Setting and message.**  Settings -> Local Machine -> **Import Format**
(a section above Import Folder): one checkbox, saved through
`POST /preference/import-format-save` (CSRF-checked, returns
`{ok, convert_lossless}`).  `RabbitMq::SendMessageToAnalyzer` puts
`options.convert_lossless` into every import message, so the setting
applies to every import path - upload, import folder, FTP fetch and the
`bulk_import` command all end there - with the next message and without a
restart.  `PipelineOptions.convert_lossless` defaults to `False`: a
message without the option behaves as before.  The loudness-only message
(`run_loudness`, §23.41) never converts.

**Duplicate check: `cc_files.source_md5`.**  After a conversion
`cc_files.md5` is the md5 of the MP3, so a second import of the same WAV
or FLAC would no longer be recognised.  Legacy migration 0066 (schema
66) adds `source_md5 VARCHAR(32)` with the index
`cc_files_source_md5_idx`; NULL means the stored file is the original.
The legacy app stores the analyzer's value in `CcFiles::updateFromArray`
via raw SQL (Propel is not regenerated, precedent 0061), only a
well-formed 32-hex value, and - unlike the loudness precedent - inside a
try/catch: a missing column costs this value, never the import.  The
Django `File` model (unmanaged) gets the field; `bulk_import` counts a
file as imported when its md5 matches `md5` OR `source_md5`.  Because the
file serializer uses `fields="__all__"`, the API selects the column as
soon as it restarts: the migration must run before the API restart.

**Files already in the library: `convert_lossless`.**  A management
command (API package) reusing `probe_audio`, `is_lossless` and
`transcode_to_mp3` of the analyzer module.  Dry run by default; `--yes`
converts, `--ids` restricts, `--root` overrides the library root (default:
`get_storage_root(refresh=True)`, as `storage_flatten`), `--ffmpeg-dir`
because ffmpeg is not on the PATH of an ordinary shell on the station.
Candidates are rows with `file_exists` and `import_status` 0 (pending
rows belong to the analyzer) whose file probes as lossless - the mime
column is ignored; a file that starts with an MPEG audio frame (after an
optional ID3v2 tag) is skipped without a probe, which keeps a dry run over
the whole library at seconds.  Per file: skipped while it is in
`cc_schedule` now or within the next 6 hours (checked before the
conversion and again inside the transaction); transcoded next to the
original as `<stem>.mp3` (`<stem> (2).mp3` when taken) with the tags of
the **database row** (the UI edits only the database, so the row is the
truth) and the cover of the source; one transaction updates filepath,
mime `audio/mp3`, md5, source_md5 (the old md5), filesize, bit_rate,
sample_rate and channels (`-ac 2` can mix down) plus the EBU R128 values
measured on the MP3 with the analyzer's own step (the integrated loudness
barely moves, but the MP3's true peak can sit a few tenths of a dB higher
and the playout caps a positive gain by it).  The id and cue-in stay; the
length changes only when it differs by more than
0.1 s, and a cue-out beyond the new length is pulled back.  In place
rather than delete + re-import because the id carries playlists, smart
block contents, schedule rows and the play history.  The original is
deleted after the commit; a failed database update deletes the MP3 and
keeps the original; a locked original is reported.  Exit code 1 when any
file failed.  Like the analyzer's import callback the update also sets
`name` (the new basename) and `mtime`; a `track_title` that is just the
old file name ("Interview.wav", what an untagged upload gets) becomes the
new one and is not written as TIT2.  `--yes` refuses while the media
library is being moved (`storage.move.JOB.is_locked()`, the guard the
podcast download uses), and a move that starts during the run skips the
remaining files.  The legacy `disk_usage` preference is not adjusted:
nothing reads it (the UI shows the real disk usage).

**Import folder: one extension list, `_failed` instead of delete.**
`FileDataHelper::getUploadAudioExtensions()` is the one list of importable
extensions (`ogg, mp3, aac, m4a, mp4, flac, wav, mp2, mp1, au, opus,
oga`): the upload dialog (`PageLayoutInitPlugin`), `createAndImport`, the
import-folder scan and the FTP fetch use it, so a file a scan picks up can
no longer be refused for its extension.  The scans therefore also take
`.mp4`, `.mp2`, `.mp1` and `.au`, which uploads always accepted (the
alternative, restricting uploads to the old scan list, would have dropped
formats from the upload).  Check the live import folder for such files
before the deploy - a video `.mp4` lying there would be imported as
audio.  A file whose hand-over fails is moved to
`<folder>/_failed/<same relative path>` (" (2)", " (3)" ... on a name
clash, `..` segments dropped); when even that move fails it stays in place
and is tried again by the next scan - nothing is deleted any more.  That
includes the hand-over itself: `StoredFile::moveFileToStor` deleted the
source when its rename into `organize/` failed (meant for an upload's
temporary copy); `createAndImport` passes `$fromImportFolder` through
`MediaService::importFileToLibrary`, so an import-folder file stays and
is quarantined.  The
directory walk (`RecursiveCallbackFilterIterator`) never enters the
top-level `_failed` (any letter case), so its files are never re-tried
and the empty-subfolder clean-up never removes its folders.  The status
line and the Scan Now result report `N failed (moved to _failed)`.  The
FTP fetch only ever deletes its own `.ftp-*.part` temporary files (the
remote original stays for the next cycle) and skips a remote `_failed`
entry.

**Rejected alternatives.**  Keeping the originals in an archive folder
(operator: not wanted; two truths, double space).  Keeping lossless in
the library (the streams are lossy anyway; FLAC or WAV takes about three
to four and a half times the space of a 320 kbps MP3).
AAC / M4A as the target (Expiry, above).  Normalising every file to one
format (lossy to lossy).  Converting in the legacy PHP before the
hand-over (it would hold the upload request and eat the scan's
20-second budget; the analyzer is the one place every import passes).

**Analyzer connection.**  The pipeline runs inside the pika callback of a
`BlockingConnection`, which neither sends nor checks heartbeats while the
callback runs; with the broker's default of 60 s an import that took
longer (an hour-long WAV converted and measured) lost the connection, the
ack failed and RabbitMQ delivered the message again - and the second run,
finding the file gone, reported a failure over the first run's success.
`message_listener` now asks for a heartbeat of 1800 s (RabbitMQ's default
`consumer_timeout`, the limit for an unacknowledged delivery anyway; the
broker runs on the same machine), and a redelivered import (not a
loudness-only message) whose file is no longer in `organize/` is
acknowledged without a report.

**Operation.**  Deploy order: tag `live-YYYY-MM-DD` and a fresh backup.
Run migration 0066 FIRST - from the branch (`PYTHONPATH` on the worktree's
`backend\api`, the API service environment), outside the 03:30 backup;
the running code never reads the new column, so this is invisible, and
the migration sets `lock_timeout` 5 s so it gives up (run it again)
instead of queueing every `cc_files` read behind a long transaction.
Check `schema_version` 66 and the column.  Then merge (legacy PHP is live
at once), restart RASTATIME-API (the file serializer selects
`source_md5` from the restart on; RASTATIME-WORKER also runs Django on
the File model - harmless once 0066 exists), restart RASTATIME-ANALYZER
when the `airtime-uploads` queue is empty and no import is pending, and
restart Apache for the three new strings (.mo).  Merging first and
migrating right after also works; the risk is only an API or worker
restart (or a reboot) inside that window.  The window between the merge
and the analyzer restart is harmless: an analyzer without this change
builds `PipelineOptions(**options)`, and pydantic's default (`extra`
ignored) drops `convert_lossless` - checked against the live package - so
an import in between is filed unconverted, not failed; stopping the
analyzer first (messages wait in RabbitMQ) avoids even that.  Existing files:
`python -m rastatime_api.manage convert_lossless --ffmpeg-dir C:\ffmpeg\bin`
from `backend\api` with the API service environment (dry run), then the
same with `--ids 603 604 --yes`.  The `_failed` folder appears in the
live import folder on the first failed hand-over.

**Verified 2026-10-14 (worktree and scratch only).**  Analyzer: 53 new
tests (`convert_format_test` 42, `analyze_metadata_formats_test` 8,
pipeline 3) on synthetic ffmpeg files, also without `PYTHONUTF8` and with
non-ASCII names; on a copy with regenerated fixtures 271 passed, the 45
failures that existed before unchanged (silence threshold 0.3 s, mono
M4A fixture, a POSIX-only permission test).  API: 21 new tests
(`test_convert_lossless` 18 with a fake converter, `test_bulk_import` 3)
in an SQLite harness, 134 passed, the 6 earlier preference failures
unchanged; one end-to-end run of the command with the real analyzer
module and `C:\ffmpeg\bin` on a temporary root: a FLAC with PNG cover
became a 320 kbps MP3 with cover, title, artist, publisher, track and
Expiry, a 96 kHz / 24-bit / 6-channel WAV a 44.1 kHz stereo MP3, an MP3
stayed untouched.  Legacy: `php -l` on the 8 changed files, helper check
69/69 (extension list, relative paths, `_failed` detection, target names,
real moves, filtered walk), the new section measured in EN/DE/FR/ES at
700/900/1200 px.  Not yet verified: the migration, the live acceptance
(upload of a FLAC, a WAV and a raw AAC; ids 603 / 604), the real "ADTS
1.9 s too long" case (the synthetic files estimate close to the truth).
Review fixes (same day, two independent reviews): analyzer 65 new tests
in all (283 passed on the regenerated-fixture copy, the same 45 earlier
failures), API 26 new tests (139 passed, the same 6 earlier failures),
`test_migration_baseline` 12/12 at legacy 0066, a PHP stub check 10/10
(`moveFileToStor` keeps an import-folder file, `encoder` cut on a
character boundary), the reviewers' end-to-end script unchanged apart
from the refreshed `encoder` of a repacked ADTS file, and their
"fail after the conversion" probe now leaves only the original FLAC in
`organize/`.

**Open.**  Podcast downloads bypass the analyzer (no conversion, no tag
fill).  Expiry in an M4A is a best effort (freeform atom).
`bulk_import --allowed-extensions` appends to the default list, so the
list can only be extended.  Only the new subprocesses run at
BELOW_NORMAL; ReplayGain, EBU R128, silence detection, playability and
the duration probe still run at normal priority.  A `.au` file imported with the setting off gets no mime
type (pre-existing for uploads).  Noticed on the way: the MP3 stream output runs at
48 kHz while the mix is 44.1 kHz; the nightly media mirror lives on D:
like the library, so with no originals kept it does not protect against
a disk failure (both BACKLOG).

**WMA (2026-10-21, operator go).**  Windows Media Audio (`wmav1`,
`wmav2`, `wmapro`, `wmalossless`, `wmavoice`) is transcoded to MP3 320
unconditionally (`is_wma`, before the lossless branch), like raw ADTS is
repacked unconditionally: browsers cannot preview WMA and it would be
the one unnormalised format.  `.wma` is back in the legacy extension
list (the upstream `unset` is gone) and in the bulk importer's default
list.  Trigger: 36 WMA files in the import folder (20 lossless at
1152 kbit/s, 16 v2 at 128 kbit/s) the scanner skipped.

### 23.58 Smart Block Query: One Bracketed Chain per Field; Atomic Import Rows (2026-10-14)

**Decision (operator Go 2026-10-14, from the BACKLOG defer of the same
day).**  Fix the nesting of the smart block query in the core and make
Import/Export *replace* of playlists all or nothing, as for smart blocks
(§23.56 addendum).

**Query.**  `Block::getListofFilesMeetCriteria` keys the rules by field
and sorts them by group.  It used to hand each rule to
`$qry->addAnd()` (new group) or `$qry->addOr()` (same group).  Propel's
`addAnd/addOr` with `preferColumnCondition` attach to the criterion that
already exists for the column, so all rules of a field formed one
left-nested chain: (A or B) and C or D = ((A or B) and C) or D whenever a
later group had alternatives.  Now the loop builds the chain itself with
`getNewCriterion`: the first rule of a group starts a criterion that is
ANDed to the field's chain, its "+" rules are ORed onto that group
criterion, and the finished field criterion goes into the query once
(`addAnd`, so fields stay ANDed).  Propel brackets every criterion that
has clauses, giving ((A or B) and (C or D)).  The rest is unchanged:
value conversion, the "or IS NULL" companion of the first NOT rule of a
field, custom SQL for ranges and relative dates.  A field without that
pattern produces the same SQL string as before, and the measurement
showed it: all 32 blocks on the station return the same tracks (count +
SHA-1 over the sorted file ids, old and new code in two runs); the seven
pattern blocks match their expected SQL counts with the new code, four
of them were wrong before (e.g. two genre rows with alternatives 2,923
instead of 0, a BPM range row with alternatives 180 instead of 3).  The
vendored Propel's debug mode (`useDebug`) fails on PHP 8
(`incrementQueryCount()` returns nothing), hence the result comparison
instead of an SQL diff.

**Atomic import rows.**  `Playlist::deleteAllFilesFromPlaylist` ended with
a bare `$this->con->commit()` and no `beginTransaction()`: harmless alone
(PropelPDO ignores a commit at depth 0), but inside a caller's
transaction it committed that transaction early, so wrapping the
Import/Export replace (delete, then `addAudioClips`) did not protect
anything - measured: a failure after the delete left the playlist empty
with the old model.  The method now has its own balanced transaction
(unchanged behaviour in the editor).  `ImportExportType::atomically($fn,
$peers)` runs a playlist or smart block row in one transaction, rolls
back to the depth it started at - also when a PHP Error (not an
Exception) skipped a nested model method's own rollback - and clears the
instance pools of the given peers, because Propel keeps the objects of
the rolled-back row with the values that failed (a stale `CcPlaylist`
looped `save()` until the memory limit in the probe).
`Block::deleteAllFilesFromBlock` had the same bare commit; it only runs in
the editor ("Empty" and "Generate" of static blocks, outside any
transaction) and was first left as is - balanced as well on the same day
(0.71.1, operator 2026-10-14): measured with a static block inside a
caller's transaction, the old method left depth 0 and the caller's
rollback found 0 of 5 items, the new one keeps depth 1 and the rollback
restores all 5; "Empty" and "Generate" behave as before.  Every method of
`Block.php` and `Playlist.php` now pairs `beginTransaction()` with
`commit()`.

**Verified 2026-10-14** with probes loading the worktree classes:
playlist new / replace / failure after the delete / Exception inside
`addAudioClips` / PHP Error with an open nested transaction / failing new
playlist / editor delete outside a transaction - contents and
description intact after every failure, connection back at depth 0, no
row left by a failed new playlist; the full service path (upload,
preview, import, replace) for a playlist and the smart block round trip
and rollback of §23.56 unchanged; cleanup left nothing.

### 23.59 Month Selection for Monthly Repeats (2026-10-14)

**Decision (operator Go 2026-10-14, chosen over "every 2 / 3 months").**
A monthly repeat (repeat types 2 and 3) gets twelve month boxes next
to *Repeat By*, all ticked by default.  The mask covers the 2- and
3-monthly rhythms and also summer breaks or "January to June".

**Storage.** `cc_show_days.month_mask INTEGER NOT NULL DEFAULT 4095`
(bit m−1 = month m; 4095 = every month = the old behaviour).  Migration
0067 (`legacy`), raw SQL; the Propel class is not regenerated.  Reads and
writes live in `Application_Service_ShowService` (`getMonthMask`,
`setMonthMask`, `monthMaskFromForm`, `monthsFromMask`, `monthSelected`);
the Django `ShowDays` model carries the matching field.  Both helpers
survive a database without the column (every month, a warning on write),
so the live code was safe before the migration ran.

**Generator.** `createMonthlyRepeatInstances` reads the mask once per
rule and adds `monthSelected($mask, $start)` (local time of the show) to
the condition that creates an instance; the loop still advances month by
month, so a skipped month costs nothing.  **Edit.** `setCcShowDays`
writes the mask after the rule's save and, on an update with a mask
below 4095, deletes the future, untouched instances of the deselected
months (`EXTRACT(MONTH FROM (starts AT TIME ZONE 'UTC') AT TIME ZONE
tz)`), the way a removed weekday drops its instances.  **Form.**
`Application_Form_AddShowRepeats` (`add_show_month_check`), shown with
the monthly radio by `add-show.js`; `ShowFormService` pre-fills it from
the mask when editing.  Nothing ticked means every month.

### 23.60 Dangerous Options → Clear Calendar (2026-10-14)

**Decision (operator: variant A).**  "Clear Calendar" empties the
calendar *from now on*: for every show the earliest instance that has
not started yet goes through `deleteShow(instance, false)` - the "this
and all following" path, which marks the instances removed, deletes
their schedule rows, sets `last_show` of the repeat rule and deletes the
show when no instance is left - and a show without any instance left is
deleted.  The instance on air and the past stay, so the Playout History
(instance_id, SET NULL since 0065) keeps its show names.  Variant B
(everything, including the past) was declined because the history
would lose the show names.  `ShowService::clearCalendarFromNow($onlyShowIds
= null)`; the optional restriction serves rehearsals on the test show
(534: temporary future instance removed, the past one and the show
stayed).  Endpoint `preference/clear-calendar` (POST, CSRF, admin), a
confirm dialog and the result in the four languages.

### 23.61 Stream Metadata per File and Track Type (2026-10-14)

**Decision (operator Go 2026-10-14).**  Whether a track's artist and
title reach the listeners' players (ICY) and the Live Text is a choice
per track type (preset) and per file (override), the way the crossover
mode is: the type carries a boolean "Forward Metadata to the Stream"
(`cc_track_types.icy_forward`, default true), the file a three-way
"Stream Metadata" (`cc_files.icy_forward`: NULL = as the track type,
1 = forward, 0 = do not forward).  Two values per file, as first
sketched, would have made the type preset meaningless.  Migration 0068,
raw SQL in `Application_Model_StoredFile` (`icy_mode`, `icyModeOf`) and
`Application_Model_Tracktype` (`setIcyForward` / `getIcyForward`, part
of `save()`'s change report); both tolerate a database without the
columns.  The Django models carry the fields and the file serializer
adds `track_type_icy_forward` next to `track_type_no_fade`, so the
playout gets the preset with the file.

**Playout.**  `_effective_icy_hidden(file)` (schedule.py) resolves the
flag - the file's own value wins, else the type's preset, a feed
without the fields forwards - into `FileEvent.icy_hidden`.
`_track_metadata` then sends the packet without `title` / `artist` but
with `icy_hide=true` and the `show_name`.  **Liquidsoap.**  `label_for`
treats `icy_hide` like a live source without metadata: "Station name -
Show name" (or the station name alone) in every Stream Label format,
before the format branches; `known` includes the flag so the packet is
never ignored.  The Live Text line uses the same label; the Playout
History is written from the schedule and does not change.  Effective
after migration 0068 and a PLAYOUT + LIQUIDSOAP restart (the script is
rendered at PLAYOUT start).

### 23.62 Wall-Clock Show Ends Across DST (2026-10-16)

**Problem.**  Show instances are stored in UTC and generated from a local
definition (`cc_show_days`: first_show, start_time, duration, timezone).
The start of every instance was already a wall-clock time (`DateTime` in
the show's timezone, advanced by `P7D` etc.), but the end was computed as
`start + DateInterval("PT{h}H{m}M")`, which PHP ≥ 8.1 treats as elapsed
time.  A show "22:00 for 8 h" therefore ended at 05:00 local in the
autumn night (one-hour gap before the 06:00 show, fallback source on air)
and at 07:00 local in the spring night (one-hour overlap with the 06:00
show, two instances active at once).  The New-Show form's overlap check
already worked with wall-clock ends (it converts the form's end time), so
validation and generation disagreed on those two nights.

**Change.**  `Application_Service_ShowService::wallClockEnd(DateTime
$localStart, $duration)` adds the duration on a DST-free clock (the local
wall-clock string re-read as UTC), then re-reads the result in the show's
timezone.  `createUTCStartEndDateTime` uses it for every instance it
creates: weekly/biweekly/monthly repeats, single shows, edited shows and
rebroadcasts.  The playout, the autoloading fill and the crossfade logic
are untouched; they consume `cc_show_instances.starts/ends` in UTC as
before.

**Edge cases of the transition hour** (Europe/Berlin, probed with
`C:/Temp/optd/dst_wallclock_probe.php`):

| Definition | Result |
|---|---|
| 22:00 + 8 h, autumn night | ends 06:00 CET, 9 real hours |
| 22:00 + 8 h, spring night | ends 06:00 CEST, 7 real hours |
| 00:00 + 24 h | ends 00:00 next day, 25 / 23 real hours (no gap, no overlap with the next instance) |
| 01:30 + 1 h, autumn | ends at the *first* 02:30 (CEST), 1 h: an ambiguous wall-clock end takes the first occurrence after the start |
| 01:30 + 1 h, spring | ends 03:30 CEST, 1 h: a non-existent end is moved forward by PHP |
| 02:00 + 1 h, spring | start and end collapse to 03:00 CEST → elapsed duration, 1 h; never a zero-length instance |

**Not changed.**  Existing instances are not rewritten (none crossed a
transition on 2026-10-16); the generator produces the new ends for every
instance it creates or re-saves from now on.  `Application_Model_Show::
updateDurationTime` (SQL `ends = starts + duration`) is dead code and was
left alone.  The duration stored by the form for a show *created* on a
transition day is still the wall-clock difference the form computes.

### 23.63 Teaser Automation Stage 1 (2026-10-16)

**Model.**  A jingle announces one or more shows in one way: the link
table `cc_file_teaser (file_id, show_id)` (both FKs `ON DELETE CASCADE`,
migration 0070 - the operator's acceptance of 0069 asked for several
shows per jingle, the hourly "bbc" slots being separate shows) and
`cc_files.teaser_type` (`show` | `today` | `tomorrow`, migration 0069,
which also adds the index `cc_schedule (file_id, starts)`; its
single-show column was carried into the table and dropped by 0070).
`StoredFile::teaserOf` returns the id list and the type, the editors use
a multiselect (`teaser_show_id[]`, collected into a list by both
controllers; a hidden `teaser_shows_sent` marks an empty selection), the
library column aggregates the show names with `string_agg`, and the
criteria test `EXISTS (SELECT 1 FROM cc_file_teaser ft WHERE ft.file_id =
cc_files.id AND ...)` - one fitting linked show is enough.  Propel classes are not regenerated;
`StoredFile::teaserOf / setDbColMetadata` read and write the columns by
raw SQL and `StoredFile::teaserColumnsReady()` (information_schema, cached
per request) keeps the library query and the criteria harmless until the
migration has run.  The Django `File` model gets the two fields
(`FileSerializer` uses `__all__`).

**UI.**  Track editor (`EditAudioMD`): selects *Teaser for show* (shows
with an upcoming instance plus the file's current one, labelled with the
next airing because several shows share a name) and *Teaser type*; the
same two fields in the bulk editor (`''` = unchanged, `none` = clear).
Library column `teaser` (`"Show name (type)"`, LEFT JOIN `cc_show`,
searchable text).  The layout plugin injects `TEASER_SHOWS` (id → label)
next to `TRACKTYPES` for the block editor.

**Criteria.**  Three virtual `BlockCriteria` (`teaser_show`,
`teaser_type`, `teaser_fits`) with new `ModifierType`s; their `peer`
points at a VARCHAR column only so the generic validators have a size.
`Block::getListofFilesMeetCriteria` turns them into SQL
(`Block::teaserCriterionSql`) and feeds it as a `Criteria::CUSTOM`
criterion on `cc_files.id`, so it takes part in the per-field AND / OR
grouping like any rule.  The editor (`SmartBlockCriteria`,
`smart_blockbuilder.js`) renders a select for the value, as for the track
type.  Import/Export maps `teaser_show` to and from the show name.

**Fill context.**  `Block::setFillContext(instanceId, showId, slotUtc)` /
`clearFillContext()` (static, request-scoped).  `AutoPlaylistManager::
fillInstance` sets it around each expansion: show start for the intro,
show end for the outro, the current chain end for the content and
top-up passes (`try / finally`).  `Scheduler::retrieveMediaFiles` sets it
to the end of the row the material is inserted after (else the instance
start) and clears it before returning.  Without a context (editor
"Generate") the slot is now and no show is excluded.

**`teaser_fits` rule.**  With the slot's day *D* in the station timezone
(`(i.starts AT TIME ZONE 'UTC') AT TIME ZONE tz)::date`) and the slot *T*:
`today` ⇔ ∃ instance of the show on *D* with `starts > T`; `tomorrow` ⇔
∃ instance on *D+1*; `show` ⇔ ¬(∃ instance on *D* with `ends <= T` ∧
¬∃ later one on *D*); and `teaser_show_id <> <show being filled>`.
`modified_instance = FALSE` throughout.

**Exclude filters.**  "Exclude tracks played lately" now reads
`((lptime IS NULL OR lptime < slot - H) AND NOT EXISTS (cc_schedule row
of the file with starts in (slot - H, slot + H)))`; the artist variant
adds the same NOT EXISTS over `cc_schedule JOIN cc_files` on
`artist_name`.  Rows an earlier block of the same fill inserted are
already in `cc_schedule` when the next block expands, which is what makes
two teaser blocks in one show disjoint.  The within-block spread
(`applyWithinBlockSpread`, 2026-05-25) is unchanged.

**Verification.**  `C:/Temp/optd/teaser_probe.php` (readiness, live run
of a block with the exclude filter, SQL of the three criteria) and a
psycopg transaction that applies the migration DDL, links three files to
a show airing later that day and checks the matches (today / tomorrow /
show, "over for today" → 0, self-teaser → 0), then rolls back.  Stage 2
(calendar dialog "Teasers…", per-show listing) follows.

**Stage 2 (2026-10-16).**  The calendar context menu gets **Teasers**
(admin / PM, past shows too): `ScheduleController::teaserDialogAction`
renders `schedule/teaser-dialog.phtml` into the usual `json.dialog`
(`buildTeaserDialog` in schedule.js, like the View dialog); the view's
inline script calls `teaser-link` (file, show, optional type - the type is
written to the jingle, `COALESCE(:t, teaser_type, 'show')`), `teaser-unlink`
(a jingle without any show left loses its type) and `teaser-search` (title
/ artist ILIKE, files not yet linked to the show, 20 rows).  Mutations are
POST + CSRF (session namespace token embedded in the dialog) + admin/PM;
helpers `StoredFile::teasersOfShow / teaserLink / teaserUnlink /
teaserSearch` work on `cc_file_teaser` directly and never touch the other
shows of a jingle.

### 23.64 Show Recording Format Selectable (2026-10-18)

**Before.**  `output.file(id="recording")` in `rastatime.liq.template`
carried a fixed `%ffmpeg(format="mp3", ... b="320k")` (operator decision
2026-05-27); only the 24/7 recorder had a format/bitrate choice.

**Now.**  Settings → Local Machine → "Show Recording" stores
`local_recording_format` (mp3 / aac / ogg / opus) and
`local_recording_bitrate` (96–320) in `cc_pref` next to the folder
(`PreferenceController::localRecordingSaveAction`, validated lists).
The template placeholder `${SHOW_RECORDING_ENCODER}` is filled by
`liquidsoap_config._render_show_recording_encoder` from the same
`_ENCODER_FOR_TYPE` table as the stream outputs (Opus clamped to 48 kHz,
unknown formats fall back to MP3 so a bad value never leaves the
station without a recorder).  `read_show_recording_config_from_db`
feeds both the render (`__main__._render_rastatime_liq_outcome`) and the
settings fingerprint, so a change is applied by the planned restart in
the next quiet moment like the other baked-in settings (§23.4x).

**File extension.**  `recording_path.build_output_path(..., extension)`
names the file after the encoder of the *last render*: `__main__` keeps
`_RENDERED_SHOW_RECORDING_FORMAT`, the scheduler receives it as the
`recording_extension` callback and asks at every `SHOW_RECORD_START`.
Reading the setting of the moment instead would mislabel a recording
between Save and the restart (AAC bytes in an `.mp3`).
`/api/v2/recording-folder` returns `format` and `bitrate` for
information only.  Tests: `test_liquidsoap_config.py` (encoder, render,
extension map) and `test_scheduler_recording.py` (extension callback,
fallback to mp3).

### 23.65 Repeat of Show (2026-10-18)

**Model.**  `cc_show.repeat_of_show_id` (FK cc_show, ON DELETE SET NULL,
migration 0071) names the source show A of a show B.  Per instance,
`cc_show_instances.filled_from_instance_id` (FK, SET NULL) records the
A instance the content came from and `repeat_skipped` how many rows were
left out for a missing file.  (A per-type flag `cc_track_types.repeat_copy`
was added by 0071 and dropped again by 0072 the same day - operator: not
needed, jingles travel with the repeat.)  Propel classes
are not regenerated; `Application_Service_RepeatFillService` reads and
writes the columns with raw SQL and every reader tolerates their absence
(`columnsReady()` via information_schema, cached per request).

**Fill.**  `RepeatFillTask` (TaskManager, 60-s poll lock
`repeat_fill_poll_lock`, declared before `AutoPlaylistTask` so one pass
copies first) calls `fillDue()`: B instances starting within
`LEAD_SECONDS` (3900 s, one pass ahead of the 60-min autoloading build)
that are unmodified, no rebroadcast, not yet filled and EMPTY (an
instance filled by hand is never touched).  Source = the last ENDED
instance of A (`ends <= now` and `<= B.starts`); none → the instance is
left to its autoloading ("autoloading only", operator decision).
`copyInstance()` reads A's rows in order, drops line-ins (live input),
counts rows whose file
is missing (`file_exists = FALSE` or import_status ≠ 0), and inserts the
rest through `ShowInstance::addFilesAfter(0, …)` with the aired
`clip_length / cue_in / cue_out / fade_in / fade_out` - the scheduler's
own layout, crossfade and overlap logic apply, B's autoloading then
fills the remaining time, overbooking is cut at B's end as usual.

**Form.**  `AddShowAutoPlaylist` carries the select `add_show_repeat_of`
(options `sourceOptions()` = shows with upcoming instances via
`StoredFile::teaserShows`, InArray validator off; a stored source without
upcoming instance is re-added when the form is populated).
`ShowFormService::validateShowForms` refuses a missing show, self,
loops (`wouldLoop()` walks the chain, 50 steps) and the combination with
"Link" (linked instances would receive the copy per instance).
`ShowService::setCcShow` stores the value; templates
(`ShowTemplateService` whitelist, add-show.js apply) and
Import/Export (column `repeat_of` = show name, resolved against existing
shows, unknown name → note) carry it.

**Delete guard.**  `cc_schedule.file_id / stream_id` cascade on delete,
so a deleted track would silently vanish from the copy.
`neededByPendingRepeat()` finds a future, empty, unfilled B instance
whose source A aired the media in its last ended instance;
`StoredFile::delete` and `Webstream::deleteStreams` refuse with
"Cannot delete: still needed for the repeat "B" on <date>", the
LibraryController shows that message.  (Migration 0065 only protects the
playout HISTORY, not the schedule.)

**Display.**  `ScheduleController::showContentDialogAction` sets
`additionalShowInfo` "Repeat of show A from <date> at <time>" (+ "(N
items of the source were left out: file missing)") from `filledFrom()`.

**Stage 2** - built 2026-10-20, see §23.67 (the recording import of
§23.66 was its precondition).

### 23.66 Copy Show Recordings into the Library (2026-10-19)

**Why.**  The operator wanted the per-show recording folder to act as a
second library folder.  Every one of the 21,700 `cc_files.filepath`
values is relative to the single storage root (`Application_Common_
Storage::root()`, API `storage/root.py`, the playout cache, the
analyzer's `import_directory`, the move job and the backup mirror), so
a second root would touch every reader.  Instead the finished recording
is imported as a copy - which is also precondition 2 of "Repeat of show,
stage 2" (recorded live shows).

**Signal.**  `ShowRecordEvent` now carries `instance_id`
(`generate_show_record_events`).  `PlayoutScheduler._on_show_record_start`
remembers `(instance_id, path)` as `_open_show_recording`;
`_on_show_record_end` stops Liquidsoap's `output.file`, then
`_report_recording_finished` (daemon thread) waits until the file size is
stable (2 s polls, 30 s cap) and POSTs `api/recording-finished`
(`instanceid`, `path`) through the legacy v1 client
(`notify_recording_finished`, Api-Key), three attempts 20 s apart.  A
PLAYOUT restarted mid-show knows no path and only logs.

**Import.**  `ApiController::recordingFinishedAction` ->
`Application_Service_ShowRecordingService::import`.  Gate: preference
`local_recording_copy_to_library` (checkbox in Settings -> Local Machine
-> Show Recording, saved by `localRecordingSaveAction`).  Checks: file
exists and is non-empty, extension mp3/aac/ogg/opus, `realpath` inside
the configured Show Recording folder (case-insensitive); an instance
that already has a recorded file, or a library row whose `md5` or
`source_md5` equals the source's md5, is only (re)linked.  The copy is
tagged with ffmpeg (`-c copy -map_metadata -1`, title
`<show> <YYYY-MM-DD HH:MM>` in station time, artist = show, album
"Show Recordings") into the temp dir and handed to
`CcFiles::createFromRecording` (-> `createAndImport` with a track-type
override: "Recordings", found by name, created on demand with code `recs`) which moves it
to `organize/` and messages the analyzer; without ffmpeg the original is
copied and the analyzer's file-name title applies.  The pending row is
labelled and its `source_md5` set; `ShowInstance::setRecordedFile`
links `cc_show_instances.file_id` (and rebroadcasts).  The file in the
recording folder is never modified.

**Tests.**  `test_scheduler_recording.py` (+5: instance id on both
events, report after settle, three retries, quiet without open
recording/client, failed start leaves nothing open);
`C:/Temp/optd/recording_import_probe.php` (gating, rejections, live
import + duplicate, probe row deleted).  Live: endpoint 401 without
key, 405 on GET, `{"ok":true,"skipped":"disabled"}` with the box off.

### 23.67 Repeat of Show, Stage 2: Live Rows from the Recording (2026-10-20)

**Why.**  A live segment (line-in between two tracks, or a whole live
show) has no rows a repeat could copy; stage 1 left it out and the
repeat had a hole.  With §23.66 the original's recording is in the
library and linked to its instance, so the repeat can play exactly the
live minutes.

**Planning.**  `RepeatFillService::planRows(src)` builds the item list
of `copyInstance`: file and webstream rows as before; a line-in row
becomes the recording (`recordingOf(src)`: `cc_show_instances.file_id`
imported, existing, length > 0) with `cuein`/`cueout` = the row's
`starts`/`ends` minus the instance start (microseconds kept, clamped to
the recording length, rows the recording does not cover stay out); an
instance with no rows at all becomes the whole recording.  The recorder
opens its file at the show start, so the offsets line up within a
second.

**Webstreams (2026-10-21, operator go).**  A webstream row is treated
like a line-in row when the source has a recording - the repeat plays
what went out, not the stream again (stage 1 copied it as a live row,
which replayed, say, BBC News of the repeat's hour).  Without a
recording the webstream is still copied as a live row.  `recordingWait`
counts webstream rows as live rows.

**Waiting.**  `recordingWait(src, dstStarts)`: a recorded source with
live rows (or none) whose recording is not imported yet makes `fillDue`
skip the instance this pass and log why - until five minutes before the
repeat starts (`RECORDING_WAIT_MARGIN_SECONDS`), then the fill goes
ahead without it.  Sources with files only never wait.

**Scheduling.**  `Scheduler::retrieveMediaFiles` now receives the item
and, when it names `cuein`/`cueout` (and `fadein`/`fadeout`), schedules
those instead of the file's defaults.  Stage 1's "aired cue values" were
silently replaced by the file defaults before; copied rows are now
exact, including the recording slice (the playout seeks by `cue_in`).

**Delete guard.**  `neededByPendingRepeat` matches a file when it is a
row of the source's last ended instance OR that instance's recording
(`a.file_id`), left-joining the rows so a rowless live show is covered.

**Verification.**  `C:/Temp/optd/repeat2_probe.php` (planning for
yesterday's instances: 25455 -> track, slice 00:02:22-00:12:22 of
file 22358, track; 13221 without import -> waits with 2 h left, not
with 2 min), `repeat2_e2e_probe.php` (throwaway show B, delete guard on
the recording, fill, rows == plan, guard released, idempotent, B
deleted).

### 23.68 Line-In: a Fresh input.http per Slot (2026-10-21)

**Symptom.**  Two recorded test shows with a line-in between two tracks
(2026-10-20 21:12, 2026-10-21 08:42) went silent for the whole line-in
slot: the FfmpegLineinCapture feeder opened the Tascam device and
streamed ten minutes at 192 kbit/s to `/linein-capture`, but Liquidsoap
logged `Switch to silence_fallback` at the gate opening and no decoder
line for the mount until the slot ended.  The successful slots (2026-10-19
14:32, 2026-10-21 08:15) were each the FIRST start of the companion
source after a Liquidsoap restart; the failing ones were second starts
after a stop.  The reused `input.http` reconnects through one Duppy async
task whose wake-up is unreliable on this Windows build - the finding
that led to Plan A for the webstreams (§23.4x, 2026-09-08).

**Change.**  `_render_linein_input_block` now renders the companion as a
`source.dynamic(id="linein_http")` arm over `linein_http_current`; every
`linein_http.start` creates a fresh `input.http(id="linein_http_in_#{n}",
start=true, format=mp3, max_buffer 1 s, poll_delay 0.5 s)` and sets it,
`linein_http.stop` stops it, drops the arm back to `source.fail()` and
parks a stop that did not take as a zombie (reaped on reconnect inside
`webstream_wd_check`, like the webstream zombies).  `linein_http.status`
is new.  No bridge buffer: the line-in keeps its low latency, the dshow
fallback arm and `fallback(track_sensitive=false, [linein_dshow,
linein_http])` are unchanged, PLAYOUT's engine sequence (`linein.stop`,
`linein_http.stop`, `linein_http.start`, gate) is untouched.

**Verification.**  `test_liquidsoap_config.py` (100 passed, assertions on
the new block), the rendered script passes `liquidsoap --check` with the
same single pre-existing warning as the live file.  Live acceptance: a
recorded show with a line-in after the PLAYOUT restart, then its repeat.

**Addendum 2026-11-01 - the stop must happen while the input is armed.**
`linein_http_stop()` used to call `s.stop()` and immediately swap the
`source.dynamic` arm to `source.fail()`.  Replica probes with Liquidsoap
2.4.6 against a mock mount show why that left zombies: an `input.http`
that falls asleep (detached from every output) never processes a stop,
its status stays `connected` and it keeps streaming.  The old reaper then
fired `start()` + `stop()` on it every watchdog tick, which only
reconnected it - one request per 2 s per zombie since 2026-10-29 (69,000
log lines on 2026-10-30), and after the feeder stopped on 2026-11-01
10:26 a 404 flood (18,000 Icecast lines in 1.5 h) that pushed the
Liquidsoap leak from 21 MB/h to 87 MB/h.  A zombie cannot be rescued
afterwards (re-arming it trips an ffmpeg assertion), so the fix is on
the stop path: the input stays armed, a `thread.run.recurrent` checks
its status every 0.5 s and detaches the arm once it reports `stopped`
(5 s cap, then detached anyway with one WARN).  The gate `linein_live`
keeps the draining input off air.  A `linein_http.start` that arrives
while the previous input drains (PLAYOUT sends stop+start back to back
for the next slot) parks the new input as `linein_http_next` and arms
it when the drain finishes - unarmed, it has not started connecting, so
nothing is lost.  Probe results (`reaper_probe5.liq`): plain stop
detached after one check; stop+start armed the successor after 2 s and
it connected; stop while the mount answered 404 reached `stopped` and
nothing reconnected when the mount returned.  The watchdog no longer
calls a line-in reaper; the webstream path keeps its reaper for now
(no loop seen in its logs since 2026-10-27) and is noted in BACKLOG.md
as the same latent pattern.  Tests: `test_liquidsoap_config.py` asserts
the drain block and the absence of the reaper.

### 23.69 Re-read Tags (2026-10-21)

**Why.**  RASTATIME never re-reads a file after the import; the database is
the truth for the library and the playout.  A file edited in Windows
afterwards kept its old row.  The operator asked for a counterpart of the
"Cue Points" button; an automatic scan was rejected (it would silently
overwrite edits made in the editor).

**Endpoint.**  `POST /api/v2/files/reread-tags` `{"ids": [...]}` (Api-Key,
`storage/views/reread_tags.py`).  Per file: the stored path under the
storage root, `rastatime_analyzer.pipeline.analyze_metadata` (the same
reader and mapping every import uses, mutagen with the ffprobe fallback),
then a comparison against `TAG_FIELDS` (title, artist, album, genre,
year, track number, comment, composer, copyright, label, ISRC, BPM,
language, mood) and `FILE_FIELDS` (md5, size, bit rate, sample rate,
channels).  Changed columns are written in one update with `mtime`; a tag
missing in the file clears its column (the file is the truth the operator
asked for), file facts are never cleared.  RASTATIME-owned columns (track
type, teaser, cue points, loudness, expiry, requests, flags, artwork) are
not in the lists and never touched.  Missing or unreadable files are
reported as skipped; at most 500 ids per call.  Nothing is written to the
file, so a track on air is safe.

**Legacy.**  `LibraryController::rereadTagsAction` (POST `media[]` like
the cue-point action) keeps the ownership rule (admins / programme
managers everything, others their own files), proxies to the API on
localhost with the API key (`rastatimeApi`, the storage-location pattern)
and words the report (`n read, m changed`, changed titles, skipped).  The
button "Re-read Tags" sits next to "Cue Points" in the library toolbar of
the Library and Show Builder pages, enabled for a file selection,
guarded by a confirmation that lists the fields.

**Tests.**  `storage/tests/views/test_reread_tags.py`: tagged copy of the
fixture -> columns follow the tags, teaser/cue stay, md5/size follow;
unchanged and missing files reported; bad input 400.

### 23.70 Schedule Reload: Immediate Reply, Coalesced Refresh (2026-10-22)

**Why.**  Every calendar or show edit calls the playout listener
(`RabbitMq::NotifyPlayoutScheduleChanged`, `POST
127.0.0.1:8770/reload-schedule`, 2-s timeout).  The listener ran
`scheduler.refresh()` before answering.  Since the 24-h window grew on
2026-10-19 a refresh took 2.7-5 s (median), up to 19 s: PHP gave up on
almost every call (140 of 145 on 2026-10-21, WARN + ERR in `legacy.log`),
every save waited 2 s, and a show move fired several reloads within
seconds that ran in parallel with the 120-s poll and the pre-flight scans.
The refresh itself happened anyway.

**Listener.**  `/reload-schedule` answers `200 ok` at once and hands the
work to `_CoalescingRunner` (`source_switcher.py`): one run at a time on a
background thread; requests during a run collapse into exactly one more
run afterwards, so the last edit is always followed by a complete
refresh.  A run is `refresh()` and then a request to a second runner for
the pre-flight rescan (B.4 #2), which coalesces the same way.  Failures
are logged in the playout log only; the reply no longer reports them (PHP
only ever logged it).  `500` stays for a listener without a scheduler.

**Fetch.**  `player.schedule.get_schedule` asked the API for the show
instance and the show of every row: 30 rows of 5 instances were 60 such
requests (~40 ms each).  It now requests each instance and show once per
fetch and gives each row a shallow copy (live shows rewrite the instance
times per row): 35 instead of 91 requests, ~1.3 s instead of ~3.6 s
against the live API.  The cost now grows with the number of shows in the
window instead of the number of rows.

**PHP.**  The `@`-suppressed warning of a failed notify stayed in
`error_get_last()` and `Logging::loggingShutdownCallback()` logged it
again as ERR; `error_clear_last()` after the WARN (also in
`NotifyDisconnectSource`).

**Tests.**  `tests/test_reload_schedule_listener.py` (immediate return,
collapse into one more run, failure logged and later runs, handler 200
before the refresh ends, real HTTP listener with three quick calls -> two
refreshes); `tests/player/schedule_test.py` (one request per instance and
show, including a live show with three rows).

### 23.71 Tagless Folder and JPG-only Artwork (2026-10-24)

**Context.**  Two operator questions of 2026-10-24 about the media
library on disk.  (1) The analyzer's `organise_file` builds the target
path `imported/<artist>/<album>/<file>` from the tags; a file without an
artist tag (and therefore without the album step either, the album is
nested under the artist) landed directly in `imported/`, next to the
artist folders - 63 files, mostly podcast episodes and untagged
recordings.  (2) `FileDataHelper::saveArtworkData` wrote ten files per
embedded cover into `imported/artwork/`: the original picture as a
Data-URI text file (`<name>`, no extension), five JPG sizes
(`<name>-32.jpg` ... `<name>-512.jpg`) and four Data-URI text copies of
those (`<name>-32` ... `<name>-256`).  183,359 files / 8.5 GB, of which
the text copies made up about half the files and 4.35 GB.  The Data-URI
text files were read by exactly one consumer, `getArtworkData` (library
rows 32 px, editor and Now Playing 256 px); the JPGs by the API endpoints
and the widgets.

**Decision.**  (1) Fallback folder `imported/tagless/` (operator's name).
`organise_file` tests the raw artist tag before `safe_component` - the
sanitiser turns an empty component into `_`, so the test has to come
first - and appends `tagless` instead of the artist/album steps.  A file
with an artist but no album tag still goes to `imported/<artist>/`.  (2)
Only the five JPGs are written.  `resizeGroupFromBlob($base, $blob)`
decodes the picture held in memory with GD (`imagecreatefromstring`, so
PNG/GIF/BMP/WebP covers become JPGs as before), scales it to
32/64/128/256/512 px and returns whether the 512 px file exists; an
unreadable picture yields the small "Error loading cover" image as the
legacy did.  `saveArtworkData` (analyzer import), `resetArtwork`
(re-read from the file) and `setArtwork` (upload in the editor, a Data
URI decoded once after the comma) all use it.  `getArtworkData($base,
$size)` builds `data:image/jpeg;charset=utf-8;base64,...` from
`<base>-<size>.jpg`, falls back to the old text file for covers that
still have one, and returns the no-cover URL otherwise.  The API
variants `artwork-data` / `artwork-data-32` now render the 512 / 32 px
JPG instead of the text file.  `resizeGroup($file, $ext)` stays for
callers that hand over a file on disk and delegates to the blob version.

**Migration.**  Two Django management commands in
`storage/management/commands/`, both dry run by default.
`move_tagless` lists the `cc_files` rows whose `filepath` is
`imported/<name>` with nothing in between, and with `--yes` moves each
file to `imported/tagless/` and updates `filepath` inside a transaction
(the file is moved back if the update fails; UUID suffix on a name
collision).  A track with a schedule row from two hours ago to three
hours ahead is skipped, because the playout may hold or queue its path;
the command is rerun later for those.  `artwork_prune_datauri` deletes
the Data-URI text files (`<base>`, `<base>-32/64/128/256`) only where a
`<base>-512.jpg` exists next to them; a cover without its JPG set is
left alone so `getArtworkData`'s fallback still finds it.  Dry runs of
2026-10-24: 63 files to move, none skipped or missing; 91,677 text files
/ 4,353 MB to delete, 91,682 files kept.

**Verification.**  Analyzer: `tests/pipeline/organise_tagless_test.py`
(6 cases on `tmp_path`, no audio fixtures: no tags, empty or
whitespace-only artist, album without artist, artist + album, artist
only).  Legacy: PHP probe
against a real cover (32 and 256 px Data URIs built from the JPGs,
missing cover -> no-cover URL, blob resize of JPG/PNG/garbage into a
temp folder), then in the logged-in UI: library rows carry a JPEG Data
URI of 3,649 characters or the no-cover URL, the editor renders the
256 px cover, Now Playing carries its cover, and
`/api/track?id=N&return=artwork-64|artwork-data|artwork-data-32|
artwork-128|artwork-512` answer 200 image/jpeg.  The analyzer change
takes effect after a RASTATIME-ANALYZER restart.

### 23.72 Role Audit: Role Checks and the Legacy CSRF Check (2026-10-25)

**Context.**  The role audit "who may do what"
(`docs/operator/ROLE_AUDIT_2026-10.md`) found seven immediate holes
(S1-S7) and thirteen role gaps (R1-R13); the operator agreed a target
matrix and five packages.  This section records the conventions the fixes
introduced, so new code follows them.

**Legacy role checks.**  `Application_Model_User::isAdminOrPM()` (Program
Manager, Admin, Super Admin) and `requireAdminOrPM()` (throws a 403
`Zend_Controller_Action_Exception`, logged by the ErrorController) are the
shared check; a controller-wide rule goes into `preDispatch()` (widgets
POST, playout-history edits), an ownership rule next to the object load
(`PlaylistController::requireOwnerOrPM`, the metadata editor).  The ACL
(`configs/ACL.php`) stays the coarse layer: show logos, podcasts,
webstreams and Line-Ins moved from Guest/DJ to Program Manager.  DJs and
guests work with tracks only - the library feed (`searchLibraryFiles`)
returns no webstream/Line-In rows for them and `playlist/add-items` /
`showbuilder/schedule-add` refuse those types.  DJs edit the playout
history of the shows they host (the entry's and the target instance's
show, checked in `PlayouthistoryController::preDispatch`).

**REST and API callers.**  In the REST module a call with the API key has
no Zend_Auth identity (`Application_Model_User::getCurrentUser() ===
null`); role and ownership checks apply to session callers only, and
storage fields (`full_path`, `artwork`) stay with the API key.  In
`ApiController` a session is accepted only for the actions listed in
`SESSION_ACTIONS`; everything else needs the key.  Django function views
without DRF permissions are wrapped in `@internal_only` (Api-Key, or a
loopback caller without `X-Forwarded-For`); Waitress trusts the local
Apache for that header only (`waitress_serve.PROXY_OPTIONS`), so
`REMOTE_ADDR` is the real client.

**Legacy CSRF (package 3).**  The session cookie is `SameSite=Lax;
HttpOnly` (`Zend_Session::setOptions` in `Bootstrap.php`; new cookies, i.e.
from the next login).  Every page defines `CSRF_TOKEN` (the session's
`csrf_namespace` token, `PageLayoutInitPlugin::_initCsrfNamespace`), and
`airtime_bootstrap.js` adds it as `X-CSRF-Token` to every same-origin
jQuery request that is not GET/HEAD/OPTIONS (`$.ajaxPrefilter`).
`Acl_plugin` compares the header (else `csrf_token`, else the form field
`csrf`) for every non-REST write of a logged-in user; the REST check
accepts the header too.  **Phase 1** only logs a write without a valid
token (`CSRF monitor: ...` WARN in `legacy.log`, with controller/action
and Origin), so senders that bypass jQuery (plain form posts, `fetch`)
show up; **phase 2** sets `Acl_plugin::LEGACY_CSRF_ENFORCE` to true (403).
New code that writes without jQuery sends the header itself.

**Phase 2 (0.97, 2026-10-27).**  `LEGACY_CSRF_ENFORCE` is true: a legacy
write of a logged-in user without a valid token gets 403 (`ERROR: CSRF
token mismatch.`) and a `CSRF refused: ...` WARN in `legacy.log`.  The
monitor log of 2026-10-25 to 27 showed one remaining sender: the seven
widget settings pages (`EmbeddablewidgetsController`), plain Zend form
posts.  Their forms carry a `Zend_Form_Element_Hidden('csrf')` with the
`csrf_namespace` token (decorator `ViewHelper` only, so it renders inside
the form), the pattern for every plain form post.  Live: a jQuery POST
passes, a `fetch` POST without the header gets 403 and one `CSRF refused`
line.

**Icecast (package 4, 0.92).**  Icecast carries only output mounts (the
three public streams, their `-standby` fallbacks) and the local
`/linein-capture`.  The input mounts `/main` and `/show` with URL auth
(`public/icecast-source-auth.php`, `icecast-auth.php`,
`api/icecast-listener-allow`) are gone - DJs connect to the Liquidsoap
harbor (8001) and are checked by PLAYOUT `/dj-auth` ->
`api/check-live-stream-auth` on loopback.  Port 8000 serves local clients
only: Apache relays the listener streams (`/stream/`), Liquidsoap and
the playout talk to `localhost`.  Icecast keeps listening on `::` (the
services resolve `localhost`, possibly to `::1`); the inbound firewall
rules for 8000 / icecast.exe are what closes it from outside.

**Four roles (0.93).**  The Airtime role Super Admin (`S`) is retired:
migration `0073_retire_super_admin` turns such accounts into Admins (and
marks a station already in use as set up, since the first-run language /
time zone dialog now goes to Admins), external group mappings (LDAP /
FreeIPA, header auth) sign the super-admin group in as Admins, and the
legacy special cases are gone.  `S` stays in `ACL.php` and `constants.php`
as a harmless alias of `A`; the API v2 never knew it.  What the role used
to protect is now an explicit rule: the installation account `admin`
cannot be deleted - `Application_Model_User::PROTECTED_LOGIN` /
`isProtectedLogin()` in the user page, `PROTECTED_USERNAME` in the API's
`UserViewSet.destroy` (403).

**Verification.**  Read-only CLI probes per role
(`C:/Temp/optd/role_audit_p2_probe.php`, `role_audit_p2b_probe.php`:
ACL matrix G/H/P/A/S, helpers, ownership, history host rules, library
feed per role), API tests for `@internal_only` and the Waitress proxy
options, and live checks: refused paths 401/403 from outside, the admin
UI unchanged; the new cookie carries `HttpOnly; SameSite=Lax`; a jQuery
POST passes the monitor silently, a `fetch` POST without the header
yields one `CSRF monitor` line.

### 23.73 Password Hashes: bcrypt on Both Sides, md5 Migrates on Login (2026-10-27)

**Context.**  Upstream LibreTime stored `cc_subjs.pass` as `md5(password)`
without a salt, and four code paths agreed on it: the web login
(`Zend_Auth_Adapter_DbTable` with `setCredentialTreatment('MD5(?)')`, the
comparison ran inside SQL), the DJ dial-in check in
`ApiController::checkLiveStreamAuth` (`md5($password)` against the stored
value), the Django API (`core.User.set_password` / `check_password` with
`hashlib.md5`, used by DRF's Basic and Session authentication) and every
place that sets a password (users dialog, own profile, password reset by
mail, users import, `create_user`).  Ten accounts, all md5.  A leaked
database or backup ZIP (the nightly backup contains the dump) would have
handed every password over through rainbow tables.

**Decision.**  bcrypt with cost 12 on both sides, one verification rule,
transparent migration.

* PHP: `Application_Model_Password` - `hash()` (`password_hash`,
  `PASSWORD_BCRYPT`, cost 12, prefix `$2y$`), `verify()` (bcrypt via
  `password_verify`, a 32-character hex value via `hash_equals` against
  `md5()`, an empty value never), `isLegacyMd5()`, `isBcrypt()` (prefixes
  `$2a$`/`$2b$`/`$2y$`), `needsRehash()` (anything that is not bcrypt at
  the current cost).
* Web login: `Rastatime_Auth_Adaptor_Password` replaces the DbTable
  adapter.  It fetches the row by login, verifies in PHP, re-hashes and
  saves when `needsRehash()` says so, and offers `getResultRowObject()`
  like the DbTable adapter (the row's columns as a stdClass without the
  password; the session identity needs `id` and `login`).  The
  `Zend_Db::factory` connection the old adapter opened per login is gone;
  the header-auth and FreeIPA adapters are untouched.
* DJ dial-in: `Application_Model_User::verifyPassword()` with the same
  rule and re-hash; `setPassword()` writes bcrypt; the password reset in
  `LoginController` likewise.
* Django: `core.models.user` gains `hash_password` / `verify_password` /
  `is_bcrypt_hash` / `is_legacy_md5_hash` on the `bcrypt` package
  (`$2b$`); `check_password` accepts the legacy md5 once and stores bcrypt
  through an `update()` on the row; `has_usable_password` counts bcrypt and
  legacy md5, nothing else.  PHP verifies `$2b$`, python verifies `$2y$`
  (checked on both sides before the change).
* `manage.py password_hashes` lists every account's hash kind, so the
  operator sees who has not logged in since the change.

**Consequences.**  Login costs one bcrypt verification (~0.25 s at cost
12), which the brute-force brake (§23.53) makes irrelevant for abuse.
Accounts migrate only on a successful login; md5 values survive in backups
taken before the change, so a new password for the admin accounts is the
operator's recommended follow-up.  The composer classmap had to be
regenerated for the two new PHP classes (`composer dump-autoload -o`,
the usual rule for new legacy classes).

**Verification.**  PHP probe on a throw-away account (14 checks: adapter
refuses a wrong password and an unknown login, accepts legacy md5 and
re-hashes to `$2y$12$`, accepts bcrypt and a python `$2b$` hash, result
row without the password, `verifyPassword` on all three hash kinds,
`setPassword` writes bcrypt, empty stored value never matches); Django
tests (`core/tests/models/test_user.py`: bcrypt stored, `$2y$` verified,
legacy md5 accepted and upgraded, empty unusable; API suite 185 green);
HTTPS login with a throw-away md5 account: POST `/login` → 302 to the
dashboard, the row then carries a `$2y$12$` hash.  Live after an API
service restart; the legacy side was live at once.

### 23.74 Deleted Autoloading Playlists: Warn, Detach, Preflight (2026-10-28)

**Context.**  `cc_show.autoplaylist_id`, `intro_playlist_id` and
`outro_playlist_id` reference `cc_playlist` with `ON DELETE SET NULL`.
Deleting a playlist therefore left `has_autoplaylist = TRUE` with no
playlist: the calendar drew the show as autoloading, the builder had
nothing to build, the slot ran silent.  After the library clean-up of
2026-10-23 this hit 34 shows, 20 with upcoming instances (the operator
re-assigned the urgent ones by hand).  The schedule-based Line-In scan
of the preflight never saw them: an empty slot has no schedule rows.

**Decision (operator: both halves).**

* **Warn and detach on delete.**  `Application_Model_Playlist::
  usageByShows(ids)` returns, per playlist, the shows that use it and in
  which role (one SQL over the three FK columns) plus whether it is the
  station default intro / outro (`cc_pref` `intro_playlist` /
  `outro_playlist`).  `LibraryController::playlistUsageAction`
  (`library/playlist-usage`, JSON) serves it; `library.js`
  `confirmDeleteWithUsage` asks it for the selected playlists before the
  delete question and lists the shows ("show (autoloading)", "station
  default outro").  The lookup fails open: an error or an 8 s timeout
  falls back to the plain question, the library is never blocked.
  `deletePlaylists` calls `detachFromShows(ids)` right before the row
  delete: `has_autoplaylist` goes FALSE for the shows whose autoloading
  playlist is being deleted (the FK still nulls the id), the station
  default is reset when it pointed at one of the playlists, both with a
  WARN line in the legacy log.  The editor's own delete (`spl.js
  fnDelete`) only removes untitled empty playlists on tab close and keeps
  no dialog.
* **Preflight warning `autoplaylist_missing`.**  `PreflightChecker.
  _scan_autoplaylist_missing` runs with the other scans every 15 min:
  `GET /api/v2/show-instances?starts_after=now&starts_before=now+48h&
  modified=false` (new `ShowInstanceFilter` on the viewset: `starts`,
  `ends` ranges and `modified`; the plain list was every instance ever
  scheduled), then `auto_playlist_enabled and auto_playlist is None` on
  the cached show.  One warning per instance, severity error, detail
  `show_name` + message.  A 404 (old API) or an unreachable API submits
  nothing, so the type keeps its last state like the storage-root scan.
  `common.js` renders the type ("Autoloading is on, but the show has no
  playlist: *show* - the show would run silent ...").

**Strings.**  Eight new `$.i18n._()` strings registered in
`LocaleController::generalTranslationTableAction` and translated in the
DE/FR/ES `.po` files (`po2mo.py --all`, Apache restart for pick-up).

**Verification.**  PHP probe (throw-away playlist attached to the test
show "tests" and set as default outro: usage lists both, delete clears
the flag and the default, unknown id → empty); playout tests
(`tests/test_preflight_autoplaylist.py`: flagged / healthy / 404 / down /
wired into `scan_once`); API test (`schedule/tests/views/
test_show_instance.py`: range + modified filter, unfiltered list); JS
syntax of `library.js` and `common.js` via `new Function`.  The dialog
itself is accepted by the operator on the throw-away playlist
"pwprobe-autoload"; the scan runs after a PLAYOUT restart.

### 23.75 Failed Imports: Reason, Leftovers, Preflight, Container Repair (2026-10-28)

**Context.**  An upload of 2026-10-20 failed in the analyzer (a RIFF/WAV
file with MP3 payload and a 39 KB ID3v2 block glued in front of the RIFF
header; ffprobe: "invalid start code ID3 in RIFF header").  The row went
to `import_status = 2`, hidden; the original stayed in
`<root>/organize/<id>-<name>` - by design, so a failure loses nothing - and
nobody noticed for eight days.  The Upload page did have a "Failed"
filter, but it carried no count, the newest 25 rows buried the failure,
the row showed no reason (upstream's `StatusReporter.report_failure` wrote
"An error occurred while importing this file" into a field `comment`,
which does not exist - the column is `comments`), and "Clear" deleted the
row only (`StoredFile::delete` removes the physical file for successful
imports, a failed row has no `filepath`).

**Decision (operator: (a)-(d)).**

* **(a) Reason.**  `Pipeline.run_analysis` puts a failure record
  `{import_status: 2, comments: <reason>}` into the result queue before it
  re-raises (`Pipeline.failure` / `Pipeline.describe`: ffprobe/ffmpeg
  stderr tail for `CalledProcessError`, the message of
  `UnplayableFileError`, else `Type: text`, 300 characters);
  `spawn_analyzer_process` takes it from the queue (fallback: the
  exception text) and the usual success report carries it to
  `PUT /rest/media/<id>`.  `report_failure` writes `comments` too.  The
  Upload table renders the reason under "Import failed." (rows arrive
  html-escaped).
* **(b) Leftovers.**  `CcFiles::organizeLeftovers(id)` lists
  `<root>/organize/<id>-*`; `deleteOrganizeLeftovers` removes them, called
  by `StoredFile::delete` for rows with `IMPORT_STATUS_FAILED` ("Clear",
  `DELETE /rest/media/<id>`).  `PluploadController::downloadFailedAction`
  (`plupload/download-failed/id/<n>`) streams the first leftover of a
  failed row to its owner, a Program Manager or an Admin; the Upload table
  shows "Download | Clear" for failed rows.
* **(c) Visibility.**  `recent-uploads` returns `numFailed` / `numPending`,
  the filter labels read "Failed (N)" / "Pending (N)".  New
  `GET /api/v2/storage/imports/failed` (`storage/views/imports.py`): the
  failed rows (id, name, comment, utime, age) and every file in
  `organize/` with size, age and the state of the row its `<id>-` prefix
  names (failed / pending / imported / missing).  `PreflightChecker.
  _scan_imports_failed` turns failures older than an hour and leftovers
  older than a day whose row is not pending into one warning
  `imports_failed` (counts, first names, message); `common.js` renders it
  with a link to the Upload page.  A 404 (old API) submits nothing.
* **(d) Repair.**  `pipeline/repair_container.py` runs first in the
  pipeline: a file that starts with `ID3` and has a `RIFF....WAVE` header
  within the first MB is copied without the leading block; an MP3 payload
  is extracted with `ffmpeg -c:a copy` into `<stem>.repaired.mp3` (original
  filename → `.mp3`), anything else continues as `<stem>.repaired.wav`
  (→ `.wav`, handled by `convert_format` like any WAV).  The pipeline
  treats the repaired file like a conversion: the broken original is
  removed only after `organise_file` filed the copy (`remove_original`),
  a later failure discards the copy and keeps the original; `source_md5`
  is the original's md5 for the duplicate check.  The repair is applied
  whenever the pattern is present, not only when ffprobe fails - small
  blocks ffprobe tolerates, the 39 KB one it did not, and the cut is
  harmless either way.

**Verification.**  Analyzer tests (`repair_container_test.py`: offset
detection, untouched file, MP3 payload copied without re-encode, PCM →
WAV, pipeline files the repaired copy and removes the original, failure
record and `describe`, failing pipeline leaves the record in the queue;
`pipeline_test` adjusted to the record), API tests (`test_imports.py`:
payload with failed row, leftovers of three kinds, key required, missing
folder), playout tests (`test_preflight_imports_failed.py`: counts and
age thresholds, clean state clears, 404, down, wired into `scan_once`),
JS syntax of `plupload.js` / `common.js`; live: `recent-uploads` carries
the counts, `download-failed` answers 404 for unknown and imported rows.
End-to-end (broken file and an ID3-before-RIFF file through the Import
Folder) after the ANALYZER restart.

### 23.76 Calendar: Undo for Ten Seconds after Deleting a Show (2026-10-28)

**Context.**  The calendar's left-click menu offers *Delete*, *Delete
Instance* and *Delete Instance and All Following*.  Each posted
`schedule/delete-show-instance` or `schedule/delete-show` the moment it
was clicked, with no confirmation.  The server side (ShowService::
deleteShow) marks the instance `modified_instance`, hard-deletes its
`cc_schedule` rows, deletes the `cc_show` row (cascading to days, hosts,
teaser links) when no instance is left, removes the show logos from
storage and pushes the schedule to the playout.  A wrong click was final
within seconds.

**Decision.**  Variant A, "delayed delete": nothing changes on the
server; the browser waits.  Variant B (snapshot + restore after a real
delete) was rejected: restoring hard-deleted rows, cascades, logo files
and the series end date is a day or two of work with the failure mode
pointing the wrong way (overlapping instances, half-restored plans, a
running track re-entered).  Variant A fails safe: whatever breaks before
the POST, the show is not deleted and reappears on the next refetch.

**Mechanics (`public/js/airtime/schedule/undo-delete.js`).**
`rtUndoDelete.defer(url, event, mode)` is what the three menu callbacks
in `schedule.js` now call.  It collects the affected instance ids
(`single`: the clicked one; `following`: every FC6 event of the same
show starting at or after it; `show`: every event of the show), adds
`rt-pending-delete` (display:none, `schedule-fc6.css`) to their chips,
appends a toast to `#rt-undo-toasts` (fixed, bottom centre) with the
show title, a one-second countdown from ten and an *Undo* link, and
keeps the job in a pending map.  Countdown end: the original `$.post`
with `{format: json, id}` and `scheduleRefetchEvents` on success; on
failure the chips come back and the calendar refetches.  Undo: timer
cleared, chips shown, nothing sent.  `pagehide`: every pending job goes
out as `navigator.sendBeacon` with `csrf_token` in the body (Acl_plugin
accepts the body token; same pattern as the page-layout save).  FC6
re-renders chips on its own, so `eventDidMount` (`schedule-fc6.js`)
re-applies the class for ids `isPending()`; it also puts the event
title into the chip's `data("event")` for the toast.  *Cancel Show* for
the show on air is untouched: immediate effect is the point there.

**Strings.**  Five JS strings via `LocaleController` and the three .po
files (`po2mo.py --all`); the toast substitutes `%s` by `.replace`, the
convention of `common.js` / `library.js`.

**Verification.**  Harness in the built-in browser with the served
`undo-delete.js`, `schedule-fc6.css`, jQuery and jquery.i18n and a fake
`scheduleFc6`: single hides one chip, undo restores without a POST;
show hides all three chips of the show and none of another; following
hides the clicked and the later instance, not the earlier one; after
ten seconds exactly one POST (`/schedule/delete-show`, id 1) and one
refetch; flushAll sends one beacon per pending job with
`format=json&id=4&csrf_token=…` and removes the toast.  Live: the new
script and stylesheet are served (200).

### 23.77 Brand Stage B: Product Name in Identifiers, Five-Day Bridge (2026-10-29)

**Decision.** Stage A (2026-10-03) renamed what the operator sees; stage B
renames the identifiers with a runtime binding, because the GitHub
publication (§ BACKLOG) makes them visible to other developers.  The
operator chose a bridge over a cut: the former names keep working for five
days (planned until 2026-11-03, moved forward to 2026-11-01/02 on
2026-10-29 after the live switch), then the bridge is removed (publication phase 2).

**Renamed.**  Python packages `rastatime_api`, `rastatime_playout`,
`rastatime_analyzer`, `rastatime_shared`, `rastatime_api_client`
(distributions `rastatime-*`, console scripts `rastatime-api`,
`rastatime-playout-notify`, `rastatime-analyzer`); environment prefix
`RASTATIME_` (`DEFAULT_ENV_PREFIX`, `RASTATIME_CONFIG_FILEPATH`,
`RASTATIME_LOG_*`); configuration file `config/rastatime.conf` and its
`.example`; gettext domain `rastatime` (`locale/<lang>/LC_MESSAGES/rastatime.po/.mo`,
`Locale.php`, `po2mo.py`); PHP classes `Rastatime_Auth_Adaptor_Password/Header/FreeIpa`,
`Rastatime_Model_FreeIpa`, `RastatimeFileNotFoundException` (Composer
classmap regenerated); Zend session namespace `rastatime` (every browser
session is logged out once); `public/js/wavesurfer/rastatime.js`; nssm
installers, `run_tests.ps1`, `backup-auto.ps1`, CI workflows, tests and the
operator docs.  Django app labels are the short last components
(`core`, `legacy`, ...), so the database (migrations, content types) is
untouched.  Not renamed: the upstream reference copies (`docs/upstream`,
`infra/upstream`), the upstream URL constants (`LIBRETIME_*_URL`,
`LIBRETIME_VERSION` = baseline release), the Composer package
`libretime/propel1`, history (CHANGELOG, `docs/dev/history`) and the
product name LibreTime in attribution prose.

**Bridge (2026-10-29 to 2026-11-01, removed in phase 2).**
- *Import names.*  Five stub packages `backend/shared/libretime_*`
  (shipped by `rastatime-shared`) call
  `rastatime_shared.compat.legacy_names.alias_package()`, which installs one
  meta path finder in front of `sys.meta_path` and replaces the stub in
  `sys.modules` with the real package.  The finder answers every
  `libretime_x.y` import with the already-imported `rastatime_x.y` module
  object (same object, so Django sees each model once), restores the real
  `__spec__` after `module_from_spec()`, and implements `get_code()` so
  `python -m libretime_playout` / `-m libretime_api.waitress_serve` still
  start under runpy.  Pickles and `DJANGO_SETTINGS_MODULE=libretime_api.settings.prod`
  load through the same path.
- *Environment.*  `BaseConfig` loads `LIBRETIME_*` underneath `RASTATIME_*`
  (`deep_merge_dict`, the current prefix wins); the click `--config` option
  reads both variable names; `prod.py`, `manage.py`, the playout
  `__main__`, `backup.py` and `dj_auth.py` fall back to the former name;
  `constants.php` and `conf.php` do the same and accept a `libretime.conf`
  when no `rastatime.conf` exists.
- *Commands.*  `libretime-api`, `libretime-playout-notify`,
  `libretime-analyzer` remain as second console-script entry points.
- *Live checkout.*  Until the services restart, four directory junctions
  (`backend/api/libretime_api` -> `rastatime_api`, ...) keep the former
  package paths resolvable for the running processes' lazy imports; they are
  local only (`.git/info/exclude`) and removed by the switch script.
  `find_packages(exclude=["libretime_*"])` in the four `setup.py` files keeps
  them out of the editable installs.

**Switch (operator, quiet window).**  `C:\Temp\optd\stufe_b_switch.ps1`:
back up the nssm parameters, stop PLAYOUT/WORKER/ANALYZER/API, reinstall
`rastatime-analyzer` (its EXE was locked), remove the junctions, set
`-m rastatime_api.waitress_serve`, `-m rastatime_playout`,
`rastatime-analyzer.exe`, `DJANGO_SETTINGS_MODULE=rastatime_api.settings.prod`
and `RASTATIME_CONFIG_FILEPATH=C:\rastatime\config\rastatime.conf`, drop
`libretime.conf` once identical to `rastatime.conf`, start API/ANALYZER/WORKER/PLAYOUT.
Rollback = the old parameters from the backup file (the bridge keeps them
valid).

**Live switch (2026-10-29 14:12-14:16).**  The four Python services run
with `-m rastatime_*`, `rastatime-analyzer.exe`,
`DJANGO_SETTINGS_MODULE=rastatime_api.settings.prod` and
`RASTATIME_CONFIG_FILEPATH=...\rastatime.conf`; the local path junctions
are gone and `libretime.conf` was deleted (hash-identical copy).  The
rendered `rastatime.liq`/`standby.liq` changed in comment lines only, so
Liquidsoap took its planned boundary restart and the standby needs none.
Inventory afterwards: no scheduled task, environment variable, Apache
directive or other service refers to a former name; the analyzer retry
queue is empty; the operator's probe tools in `C:\Temp\optd` were swept.

**Instrumentation (2026-10-29, second half).**  Because nothing in
production needs the bridge any more, its remaining job is to prove that:
`legacy_names.report()` logs one WARNING per process and former top-level
name (`legacy name used (stage B bridge)`) with the requesting file and
line, skipping importlib and the stub packages; `config._base.
report_legacy_env()` logs once which `LIBRETIME_*` variables are present
(names only, never values) from `config_filepath_from_env()` and
`BaseConfig.__init__`; `constants.php` writes `stage B bridge` lines to
the PHP error log (Apache `http-error-*.log`) when a former variable or
`libretime.conf` is used.  Current names stay silent (tested).  Zero hits
across the nightly cycle and a weekend are the go for phase 2.

**Phase 2 (done 2026-11-01, operator go after the log check).**  The
instrumented bridge logged no use between 2026-10-29 14:16 and
2026-11-01 09:30 (three nights with backup, janitor and the weekend;
`Select-String -Pattern "stage B bridge"` over `logs/*.log` empty, the
four service logs free of errors).  Removed: the five stub packages
`backend/shared/libretime_*`, `rastatime_shared.compat` (finder, loader,
probe), `LEGACY_ENV_PREFIX` with `report_legacy_env()` and the second
`EnvLoader` pass in `BaseConfig`, the click `--config` second envvar, the
`LIBRETIME_CONFIG_FILEPATH` / `LIBRETIME_LOG_FILEPATH` fallbacks in
`manage.py`, `settings/prod.py`, `storage/backup.py`, playout `__main__`
and `dj_auth.py`, the PHP fallbacks and `rastatime_bridge_used()` in
`constants.php` / `conf.php`, the `libretime-*` console entry points and
the `find_packages` exclusion in three `setup.py`, the `.gitignore` line
for `config/libretime.conf`, and the bridge tests (shared 45 -> 36).
`config_filepath_from_env()` now reads `RASTATIME_CONFIG_FILEPATH` only.
A process started under a former name fails at import time; a former
variable is not read.  The editable installs were refreshed so the
`libretime-*.exe` launchers are gone; `rastatime-analyzer.exe` was locked
by the running service, so the analyzer dist is re-installed when the
service is restarted (a path entry keeps the package importable until
then).  Rollback: `git revert` of the phase 2 commit + restart of the
four Python services (no migration, no nssm change).

**Verification.**  Suites green after the rename (api 195, playout 845,
unit 739 + the migration baseline moved to 0073, shared incl. four bridge
tests: translation table, same module object, finder on legacy submodule,
`-m` under both names).  Dry runs with the live nssm environment and the
former names: `manage.py check` (both names), `-m libretime_api.waitress_serve --help`,
`libretime-analyzer.exe --help`, `rastatime_worker` import; PHP login page
200 after classmap regeneration, `.mo` catalogs rebuilt (de 1475, es 1440,
fr 1439 entries).

### 23.78 Fresh-Machine Rehearsal Fixes: Stream State to the UI, Main Output Off, Restart Re-Arm (2026-11-02)

**Context.**  GitHub phase 5 installed RASTATIME on a fresh Windows 11 VM
by the letter of INSTALL (`docs/operator/INSTALL_PROBE.md`).  Besides 15
documentation fixes it produced 14 product findings; the operator gave
a Go per finding and all were built the same day.  Three of them changed
the architecture.

**Stream state reaches the UI (finding 6).**  Every rendered
`output.icecast` is now bound to `rt_stream_N` (N = the slot of
`stream_output_N`, carried as `stream_id` by `_read_stream_outputs(numbered=True)`)
and registers two callbacks: `on_connect` posts `ok`, `on_error` posts
the error text (`error.message(err)`; the record form `"#{err}"` carried
the OCaml source positions into the UI) and keeps
the stdlib retry with `restart_in(3.)`.  Both go through
`rastatime_stream_event(n, status, message)`, an `http.post` from a
detached `thread.run` to PLAYOUT's listener
`/stream-event?stream=N&status=ok|error&message=...` (new handler in
`source_switcher._EventHandler`).  `stream_status.StreamStatusReporter`
deduplicates per slot (the error callback fires every retry) and forwards
the message on a daemon thread to the legacy v1 endpoint
`api/update-liquidsoap-status` (stream_id `sN`, boot_time empty so the
legacy "older than the last save" guard never hides it); the web
application stores `cc_pref` `stream_liquidsoap_status:N`, returns it from
`get-liquidsoap-status` whenever Icecast answers but the mount is missing,
and clears all three on every save of the page.  The standby script
renders plain outputs (`status_url=None`).  Why not `output.icecast`'s
deprecated `on_error` argument: 2.4.6 wants the source method, and the
type was verified with `liquidsoap --check` before rendering.

**Main Output "Off" (finding 3).**  `output.portaudio` has no
`on_error` in 2.4.6 and `settings.clock.allow_streaming_errors` no
longer exists, so a PortAudio write error (`Output underflowed`, twice on
the VM's virtual HD Audio) is fatal for the whole engine, Icecast outputs
included; the 2026-09-14 bridge (`buffer.adaptative` + `mksafe`, §23.23)
absorbs underruns on the Liquidsoap side but not the device's own error
codes.  The Main Output picker (Settings -> Local Machine) therefore has
a permanent option **Off - stream only**, stored as `main_output_id =
"none"` (`liquidsoap_service.MAIN_OUTPUT_OFF_ID`).  `__main__` resolves it
to `local_output_enabled=False` with mode `MAIN_OUTPUT_OFF`; the render
emits no `output.portaudio` and the marker `# rastatime-main-output: none`,
which `check.php` reads so the page shows "off (stream only)" as the
active monitor.  The machine variable `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false`
renders the same marker.  Headless and virtual installs pick Off; the
studio keeps its Tascam monitor.

**Unplanned Liquidsoap restart re-arms the running item (finding 2).**
The restart detectors (`_maybe_reinit_by_process`, uptime fallback,
§23.27) re-sent `recording.stop`, reopened the gates and forgot the
queued-ahead successor, but kept `_playing_key` / `_current_event`: the
fresh instance sat on `silence_fallback` while the scheduler believed the
item was on air (rehearsal 02:28, ~6 min of silence after the operator's
`nssm restart` landed a few seconds after PLAYOUT's own start catch-up).
`_forget_current_after_restart()` now clears the same bookkeeping the
planned-restart path clears (`_after_liquidsoap_restart`), and because the
detector runs at the top of `refresh()`, the same pass re-arms the item
through the existing catch-up (`Catch-up: in-progress event ... entering
at +N s`).  `_on_file_start` additionally logs an unexpected exception of
its Timer thread instead of losing it to stderr.  The VM's log then
explained the "hang" after `Liquidsoap stop (deferred up to 0.5s)`: the
planned restart at the PLAYOUT start ran concurrently with the start
catch-up (Timer thread), the push landed in the dying instance, and
`_after_liquidsoap_restart` cleared the scheduler's bookkeeping but not
the engine's own mirror (`_current_uri`, `PLAYING`).  The catch-up two
minutes later called `stop()` + `play(<same file>)`, and `play()` took
the deferred-stop idempotency shortcut ("re-issue, keeping current
track") without pushing.  `LiquidsoapPlayoutEngine.forget_playback_state()`
now drops that mirror on both restart paths (planned and detected), and
`_schedule_refresh_soon()` re-arms the running item one second after a
planned restart instead of at the next 120-s poll; for an UNPLANNED
restart the first `/stream-event ok` of a reconnected output calls
`request_refresh_soon()` (coalesced, 2 s), so the detection no longer waits
for the poll (studio probe 12:10: 68 s of silence before this).  The Settings ->
Streams page re-populates its sub-forms from the posted values after a
refused save (`isValid()` cannot map the flat `sN_data[field]` keys onto
`elementsBelongTo`, so the fields came back empty and looked deleted).

**Off-air mark after a gate switch (studio finding 12:15).**  The bus-arm
transition `bus_arm_scheduled` marked off-air at once when `scheduled_q`
was not ready; PLAYOUT closes the previous arm's gate a few ms before it
pushes the next track (webstream -> file), so the mark overtook the
track's title and listeners saw the off-air text for a whole track.  The
check now repeats 0.5 s later (`thread.run(delay=0.5)`) and marks the
silence arm itself (`offair_mark()`) only if the queue is still empty.

**Smaller changes.**  `restart_liquidsoap_service` asks `nssm status`
first and logs INFO for a service that is not registered yet (fresh
install between INSTALL 9d and 9h) instead of three ERROR lines.  A render
without DJ harbor registers `rastatime.source_events` answering `none`;
`_probe_source_events` distinguishes on / none / absent and the
reconciler logs once at INFO.  `stereo()` replaces the deprecated
`audio_to_stereo`; the template no longer registers `flush_and_skip`
(the stdlib's `telnet.liq` does it on the underlying `request.dynamic`).
Settings -> Streams validates enabled streams (mount, port, source
password) and answers `valid` as a real boolean.  `conf.php` creates
`storage.path`.  `install-api.ps1` defaults to 127.0.0.1,
`install-icecast.ps1` refuses a missing or `CHANGEME` `icecast.xml`, all
installers poll up to 30 s for Running, `status.ps1` lists STANDBY, shows
service and child-process uptime with a restart warning, the age of each
log tail, reads UTF-8 and marks WORKER optional; `bootstrap.ps1` runs
`httpd -t` and checks the eight PHP extensions.

**Verification.**  playout suite 863 passed (new
`test_rehearsal_fixes_2026_11.py`: callbacks, Off marker, probe `none`,
`/stream-event`, reporter dedup, restart re-arm, engine mirror reset,
Timer-thread logging;
service probe tests), ruff clean, two rendered scripts (`harbor + line-in
+ webstream`, `no harbor + Off`) type-check with `liquidsoap --check`
2.4.6, `php -l` on six files, `status.ps1` and `bootstrap.ps1` run on the
studio machine.  Rollback: `git revert` of the commit + PLAYOUT restart;
no migration, no nssm change.

### 23.79 Publishing, Stage 1: Editorial Team, Episode Data, Participants (2026-11-03)

**Why.**  The operator publishes every show on cba.media (the Austrian
community-radio archive) by hand and reports the people involved in the
programme once a year.  Stage 1 of the CBA publishing plan (BACKLOG "CBA-
Anbindung", operator go 2026-11-03) stores what a published episode and
the yearly count need; nothing is uploaded yet.  Stage 2 adds the upload
(RASTATIME-WORKER as job runner, CBA credentials under Settings), stage 3
the automatic upload after the recording import (§23.66).

**Model (legacy migration 0074, target 74).**  Four tables, raw SQL in
the legacy frontend (no Propel classes), every reader tolerates their
absence (`PublishingService::tablesReady()`):
`cc_editor_profile` (name, optional email, optional `subjs_id` -> cc_subjs
SET NULL, active), `cc_show_editor_profile` (N:M, both CASCADE),
`cc_show_publishing` (one row per show, created on the first save:
participants 0-999, CBA series id, licence key, CBA category id, up to
three language codes, tags, default teaser, contains_copyright) and
`cc_episode` (one row per instance, CASCADE with the instance: title,
teaser, image path relative to the storage root, image licence and
caption, participants override).  The episode description is the
existing `cc_show_instances.description` ("Instance Description").
Licence keys are those of the CBA zipupload (`copyright`, `cc by-nc-nd`
... `pd`).

**Show form.**  `Application_Form_AddShowPublishing` is a sixth subform
(`ShowFormService::createShowForms()['publishing']`), rendered as section
"Publishing" between Who and Style, not in Edit Instance (the section
is show-level).  The editorial-team boxes travel as a separate
`editorProfiles` parameter like the hosts (a multi-checkbox collapses in
the controller's flat name/value list).  `validateShowForms()` checks the
section only when its fields came along, `ScheduleController::
savePublishing()` stores it after `addUpdateShow()`; a failure there is
logged and does not undo the show save.

**Episode dialog.**  Calendar context menu "Episode..." (CalendarService
`addEpisodeItem`, past and future instances, not legacy rebroadcasts,
admins / PMs / hosts of the show) -> `schedule/episode-dialog` (JSON,
view `episode-dialog.phtml` with inline script, dialog built by
`buildEpisodeDialog` in schedule.js).  Writes are POST + CSRF + role
check (`episodeMutationAllowed`): `episode-save`,
`episode-image-upload` (JPG/PNG by finfo MIME, at most 10 MiB, stored as
`<storage root>/imported/episode-images/<instance>/<stamp>-<rand>.<ext>`,
the previous file is deleted), `episode-image-delete`; `episode-image`
serves the file for the preview.  Episode images sit in the media mirror
of the backup.  Future instances that the calendar recreates after a
change of the repeat pattern lose their episode row (CASCADE) - the
manual tells operators to enter episode data close to the broadcast.

**Pages.**  `PublishingController` (ACL resource `publishing`, Program
Managers and Admins): Settings -> Editorial Team (`editors`, classic
POST + redirect, CSRF by the Acl plugin) and Analytics -> Participants
(`participants`, `participants-csv`).  The overview counts instances of
the year in station time that ended, are not deleted
(`modified_instance`) and are no legacy rebroadcast; per show the show
value, the number of episode overrides and the sum of the effective
values (participations); totals: shows, episodes, sum of the show
values, participations, distinct profiles of the aired shows, shows
without a value.  "Repeat of show" shows (§23.65) carry a tag.

**Verification.**  `C:/Temp/optd/publishing_probe.php <admin> <test show>
[--write]`: show form renders the section (order Who < Publishing <
Style, nine help icons, absent in Edit Instance), validation, context
menu entry, episode dialog (editable and read-only), both pages; with
`--write` profile / show settings / episode / image round trip on the
test show, everything removed again.  API suite 195 passed (test
database migrated through 0074).  Unauthenticated curl on the new routes
302 to the login.  Rollback: `git revert`; the four tables stay unused
(or `DROP TABLE cc_episode, cc_show_publishing, cc_show_editor_profile,
cc_editor_profile` and schema_version 73).

### 23.80 Archiving, Stage 2: CBA Accounts, "Archive Online" by Hand, the Worker as Job Runner (2026-11-03)

**Renamed.**  The operator renamed the feature of §23.79 "Archiving"
("Publish" is My Podcast's word): UI section, menu texts, manual chapter
`ARCHIVING.md`, and in the code `Application_Service_ArchivingService`,
`Application_Form_AddShowArchiving`, `ArchivingController` (routes
`archiving/*`, ACL resource `archiving`), table `cc_show_archiving`
(migration 0075 renames `cc_show_publishing`).

**CBA answer (2026-11-03).**  Upload = `POST cba.media/wp-json/cba/v1/
zipupload`, HTTP Basic with the CBA user name and a WordPress application
password; every show is archived under its own CBA user.  Required meta:
title, content, languages (CBA list, max. 3), production_date (past),
category_id; status defaults to private, licence to CC BY - so RASTATIME
requires a licence.  No endpoint changes or deletes a post.

**Model (migration 0075).**  `cc_cba_account` (label, user name,
application password - write-only in the UI, admins only; never returned
by `accounts()`), `cc_show_archiving.cba_account_id / cba_status`,
`cc_episode.production_date / no_archive / cba_post_id / cba_archived_at`
(caption widened to 500), `cc_cba_upload` (one row per job: status queued
| running | done | failed | unclear | cancelled, attempts,
next_attempt_at, give_up_at = +24 h, last_error, bytes_total/sent, a
partial unique index allows one open job per instance), `cc_pref
cba_upload_kbit` (4000).

**Legacy.**  Settings → CBA Accounts (`archiving/accounts`: save, delete,
test = `GET wp/v2/users/me?context=edit` with the stored credentials by
curl, role check; upload limit).  The Archiving section gains the
account, the visibility, the topic as a list (from `cc_pref
cba_categories_json`, else the number field) and the licence matrix as an
HTML tooltip (`data-rt-tip-html`, bound in add-show.js and the dialog);
the licence list is the specification's (no `cc by-sa`, `cc sampling+`
added).  The Episode dialog gains production date, "do not archive" and
the "Online archive" block: state (polled every 5 s while a job is open),
`precheck()` reasons, "Archive online..." with the audio choice
(recording or a library MP3/OGG/Opus, `archiveFileSearch`), "Link
existing post" (`linkPost`, number or `?p=` address); actions
`episode-archive`, `episode-archive-link` (admins / PMs, POST + CSRF),
`episode-archive-state`, `episode-archive-files`.  Edit Instance no
longer carries the instance description (the dialog is the only place);
`ShowService::editRepeatingShowInstance` keeps the stored text and moves
the episode row and the jobs to the new instance (`moveEpisode`) - Edit
Instance creates a new instance, the stage 1 data stayed on the hidden
original before.

**Worker.**  RASTATIME-WORKER stops being a placeholder (`__main__`):
Django setup with the service's settings (retried every 60 s, tables
checked), `recover_interrupted()` at start (running + no byte sent →
queued, else unclear), every 15 s `refresh_categories()` (daily) and
`run_once()` until no job is due.  `archive_jobs` reads with raw SQL,
`cba.build_meta()` checks and builds the meta (title show + date,
content = episode or show description as HTML paragraphs, teaser
fallback, production date = broadcast day, broadcast date = instance
start in station time, editors from the profiles, image fields only with
an image), `cba.write_body()` writes the ZIP (`audio.<ext>`,
`image.<ext>`, stored) as its own file and copies it into the multipart
body temp file (written straight into the body, `zipfile` keeps absolute
positions - PHP's ZipArchive on cba.media refused that, fixed 2026-11-03),
`ThrottledReader` streams it with Content-Length at the upload limit and
reports progress every 5 s.  Outcome: success → post id on the episode;
connection refused / connect timeout / 429 / 503 → retry after 2, 5, 15,
30, 60, 120, 240 min until give_up_at; 4xx and `success:false` → failed;
5xx, read timeout, connection lost after the first byte → unclear (never
retried automatically: the post may exist and the API cannot remove a
duplicate).  Nothing is logged of the password.

**Verification.**  `tests/unit/worker/test_cba_upload.py` (meta, missing
items, body + ZIP, throttle with a fake clock, classification, upload
outcomes with fake sessions, end-to-end against a local HTTP server:
Content-Length, Basic auth, parts) - worker suite 123 passed.
`C:/Temp/optd/archive_worker_probe.py 534`: the job paths on the live
database with a stand-in session (done, duplicate refused, retry later,
give up, no text, interrupted jobs), state restored.
`C:/Temp/optd/archiving_probe.php 1 534 --write`: 75 checks incl.
accounts (password never rendered or returned), precheck, queue, one open
job, link / unlink, Edit Instance without the description.  Live with the
CBA: accepted 2026-11-03 by the operator - three test episodes archived by
hand (private and public, one post each); on the way the account page lost
its messages (the legacy session is closed before the controller runs:
redirects carry a fixed code now), the role check knew `stationmanager`
only (cba.media says `station_manager`) and the ZIP fix above.  Rollback:
stop RASTATIME-WORKER (uploads pause), `git revert`; the tables stay.

### 23.81 Archiving, Stage 3: Archive Automatically (2026-11-03)

**Decision (operator go 2026-11-03).**  The rules agreed before stage 2
(BACKLOG), plus three answers: (A) a replacement programme that ran
instead of a live show is not recognised - RASTATIME keeps no history of
the on-air source per instance, and building one in the playout was
deferred (the switch is per show and off by default; "only for shows that
run reliably"); (B) the waiting time is one station setting next to the
upload limit; (C) failed, unclear and given-up automatic uploads appear as
a dashboard warning.

**Model (migration 0076).**  `cc_show_archiving.auto_archive` (the
switch) and `auto_since` (UTC like `cc_show_instances.ends`; set when the
switch goes on, kept while it stays on, cleared when it goes off),
`cc_cba_upload.status` + `skipped`, `cc_pref cba_auto_delay_min` (30).

**Worker (`archive_auto`).**  Every 300 s, before the job loop:
`candidates()` = instances of shows with the switch on that ended after
`auto_since` and at least the waiting time ago, not hidden (modified),
no rebroadcast, no "repeat of" show, no "do not archive", no post and
**no job of any kind** - an upload started by hand keeps the automatic
run out, and every instance is decided at most once.  Per candidate:
the recording (`si.file_id`, imported, at least half of the slot), then
`cba.build_meta()` on `load_episode()`.  Nothing missing → a job with
trigger `auto` (the unique index catches a parallel manual job); still
missing 24 h after it was due → a `skipped` row with the reasons; else it
waits (logged once per process).  The job runner of §23.80 uploads it
unchanged.  `refresh_warning()` writes `PreflightWarning` rows of type
`archive_failed` directly through the Django model (the worker has the
API's settings; no playout restart): automatic jobs failed / unclear /
skipped in the last 7 days whose episode has no post and no later job,
at most 10, rewritten only when the set of job ids changed; the dashboard
banner (`common.js`) names the show and the reason and points to
Episode... .

**Legacy.**  Archiving section: "Archive automatically" with "on since"
(station time); validation requires account, topic, language and licence
when it is ticked; `saveShow()` keeps `auto_since` in the upsert (`CASE`
on the old row).  Settings → CBA Accounts: waiting time (0-1440 min).
Episode dialog: one line from `autoState()` (off / archived / job /
never / excluded / before / scheduled with the due time / waiting with
the give-up time and a short-recording note) and the state `skipped`.

**Verification.**  `tests/unit/worker/test_archive_auto.py` (recording
rules, decide, warning rows, delay clamp) - worker suite 135, unit suite
786 passed.  `C:/Temp/optd/archive_auto_probe.py` on the live database in
one rolled-back transaction: candidate selection, queue with the
recording, wait and skip by time, no second decision, warning written /
unchanged / cleared by a linked post, nothing left afterwards.
`C:/Temp/optd/archive_auto_ui_probe.php 1 534 <instance> --write`: form,
validation, `autoState()` cases, `auto_since` set / kept / cleared,
waiting time stored and clamped, restored.  The stage 1/2 probe (75
checks) still passes.  Live: accepted 2026-11-03 by the operator - a test
show with the switch, a recording and a waiting time of 5 min; the episode
first waited with its reason (no description on the episode or the show),
the next scan after the description was added queued it (trigger `auto`)
and the job runner archived it publicly in one attempt.  Rollback: untick
the switch (nothing new is queued) or stop RASTATIME-WORKER; `git revert`;
the columns stay.
