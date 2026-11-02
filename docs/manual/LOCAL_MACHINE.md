# Local Machine

> **Where you are in the manual.** This chapter covers the
> Settings → **Local Machine** page, which owns every concern
> tied to the *operator's machine itself* — sound-card
> output, line-in input devices, the import format and the
> Local Import Folder.
> For the network-side outbound streams, see
> [Streams](./STREAMS.md). For the Library item type that
> *references* a sound-card input, see [Line-In](./LINE_IN.md).

The **Local Machine** page is where you tell RASTATIME about
the physical resources on the operator-machine: which speaker
output to play through, which devices count as line-in
candidates, in which format lossless files enter the library,
and which folder the analyzer should watch for imported
tracks.

The page replaces the upstream LibreTime "Soundcard" page and
adds the Import Folder feature. The legacy URL still works;
only the page title and the slug change.

---

## 1. The page

Settings → **Local Machine**.

**One Save for the page** *(since 2026-10-27)*: the **Save** button
at the top right and the same one at the bottom save every section
you changed - Soundcard, Import Format, Import Folder (with the
bulk-import checkbox), FTP import, 24/7 Recording and Show
Recording - one after the other; untouched sections are not saved
again.  Each section reports its result on its own line, a summary
appears next to the button.  The buttons that act at once - Apply
now, Scan Now, Fetch now, Check, Move library - stay in their
sections.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Local Machine Settings                              [   Save   ]│
   ├─────────────────────────────────────────────────────────────────┤
   │  Soundcard                                                      │
   ├─────────────────────────────────────────────────────────────────┤
   │  Output Devices              │  Input Devices                   │
   │  ─────────────────            ──────────────                    │
   │  ◉  Speakers (Realtek)        ☑  Microphone (USB)               │
   │  ◯  Headphones (Realtek)      ☐  Line-In (Realtek)              │
   │  ◯  USB Headset                ☑  Mixer-Out (Behringer)          │
   │                                                                 │
   │  Default output for cue/monitor: [Speakers (Realtek) ▾]         │
   ├─────────────────────────────────────────────────────────────────┤
   │  Import Format                                                  │
   ├─────────────────────────────────────────────────────────────────┤
   │  ☑ Convert lossless audio (WAV, FLAC, ...) to MP3 320 kbps (?)  │
   ├─────────────────────────────────────────────────────────────────┤
   │  Local Import Folder                                            │
   ├─────────────────────────────────────────────────────────────────┤
   │  Folder path:    [C:\rastatime\import\                  ]        │
   │  Last scanned:   2026-05-21 14:32 — found 0 new files           │
   │                                                                 │
   │  [ Scan Now ]                                                   │
   └─────────────────────────────────────────────────────────────────┘
```

The sections are independent of each other; the page holds
more of them further down (FTP import, media library
location, recording folders).

---

## 2. Soundcard — Output Devices

The list shows every audio output device the operator-machine
exposes (built-in speakers, USB headset, HDMI audio, etc.).

### Default output (the "monitor")

The selected device is the **monitor / cue** output:

- The dashboard's **Listen** button plays through it.
- The library's **Preview** button (click a track to hear a
  10 s sample) plays through it.
- The show-builder's preview also plays through it.

> **What it is NOT.** The default output is *not* the public
> stream. Listeners do not hear what plays here. The public
> stream is the Icecast output configured in
> [Streams](./STREAMS.md), which is fed by the playout
> engine entirely separately from this device.

### Why pick a specific device

- **Single-operator stations** with just one set of
  speakers — leave at default; the OS-default device works.
- **Dual-monitor stations** with an "air check" speaker (for
  monitoring the public stream) and an "internal" speaker
  (for previewing tracks before they go live) — pick the
  internal speaker here so previews do not interrupt the
  air-check.
- **Headphones-only stations** — pick the headphones device
  so previews never leak into the studio mic.

### "(System default)" pseudo-device

The first entry in the dropdown is always **(System default)**.
This follows whatever the Windows / Linux system has marked as
the default audio output. Useful when:

- The operator unplugs / re-plugs the USB headset and wants
  RASTATIME to follow the OS choice.
- The operator-machine is shared across multiple users with
  different headphone preferences.

> **How it works under the hood.** Devices are enumerated via
> `audio.soundcard.windows_manager` (WASAPI on Windows,
> portaudio on Linux). The selected device is persisted in
> `cc_pref` as `default_output_device_id` (`(System default)`
> is the empty string). The actual playback uses the libVLC
> audio output module with the device ID set per output. See
> ARCHITECTURE §9.

### "Off - stream only" (since 2026-11-02)

The **Main Output** list has a permanent entry **Off - stream only (no
local monitor output)**. Choose it on a machine without a usable sound
device - a virtual machine, a headless server, a studio that monitors
the Icecast stream instead: the playout engine then renders no local
output at all. Why it matters: a buffer underflow of a local output can
stop the whole engine, streams included (seen twice on a virtual sound
card during the fresh-machine rehearsal). Apply it like any other Main
Output change ("Apply now" below); the status line then reads
**off (stream only)**.

### Applying a change — "Apply now"

> **Since 2026-09-16 this happens by itself.** After Save the playout
> notices the changed device at its next schedule refresh (within two
> minutes) and restarts the audio chain in the next quiet moment - or,
> with a 24/7 programme, between two file tracks. Listeners stay
> connected via the standby mounts. The same applies to the 24/7
> recording, the track and show crossfade durations and the stream outputs. **Apply
> now** remains the way to force it immediately.

Saving stores the device; it does **not** move the local
monitor yet. The playout engine compiles the chosen device
into its Liquidsoap script when the service starts, and
Liquidsoap reads that script only when *it* starts. Applying
a change therefore needs both services restarted, in that
order.

Rather than restarting silently on Save — which would drop the
public stream without warning — the page offers a deliberate
button under the picker:

**Apply now (restarts audio chain)** — restarts
RASTATIME-PLAYOUT (which re-renders the script with the new
device) and then RASTATIME-LIQUIDSOAP (which loads it).

Above the button the page states **which output is really
driving the monitor right now**, read back from the rendered
Liquidsoap script rather than from the stored setting. If the two
differ — because the change has not been applied yet, or because
the device could not be opened — the line says so in amber. A
saved value alone is not proof that it is in use.


> **On-air impact.** The second restart drops the Icecast
> source connections for a few seconds; listeners hear a short
> gap. Do it between shows. The button asks for confirmation
> first.

> **How the device is matched.** PortAudio lists the same
> endpoint once per Windows host API (MME, DirectSound,
> WASAPI, WDM-KS), and which copy actually works is
> device-specific. RASTATIME therefore *probes* the
> candidates at startup — using PortAudio's **blocking** API,
> the one Liquidsoap itself uses — and takes the first that
> really opens. Measured at 44.1 kHz on the studio machine:
> MME and DirectSound work for a USB headset; WASAPI works when
> the endpoint's Windows format matches (see the next note), and
> WDM-KS offers no blocking support at all. If no candidate opens,
> RASTATIME keeps the OS-default endpoint and records every
> failure reason in the playout log.

> **The device goes into the script by name, not by number.**
> PortAudio numbers its devices in enumeration order, and on a
> machine where endpoints appear late after a reboot or come and
> go (USB headsets, HDMI audio) those numbers shift. Since
> 2026-09-05 the script therefore names the endpoint
> (`device_name="…"`); Liquidsoap looks the name up when *it*
> starts, so a number that changed between the two service starts
> can no longer send the monitor to the wrong jack. The name is
> only used when the entry it selects is known to play (MME or
> WASAPI, opened in the same test as above); otherwise RASTATIME
> falls back to the number and says why in the playout log. The
> active-output line above shows which one is in use.

> **The device's Windows format must match 44.1 kHz.** Liquidsoap
> runs at 44.1 kHz, and WASAPI shared mode insists on the endpoint's
> configured mix rate. A device whose Windows default format is set
> to 48 kHz is refused by every host API and looks dead — measured on
> the Tascam US-16x08, which came up unusable and worked the moment
> its format was set to 44.1 kHz (Windows Sound settings → the
> output → Advanced → default format). The playout log points at
> this fix when it sees a sample-rate rejection. A driver reinstall
> can reset the format; the active-output line above then shows the
> mismatch. Output and Line-In capture on the same interface work
> simultaneously.

### Automatic restarts and health warnings

Two situations restart the audio engine without the button, and
three dashboard warnings watch it (since 2026-09-05; the safeguard
and the third warning since 2026-09-07):

- **After a reboot.** Both services start in parallel, and the
  engine may load the previous script before the playout has
  rendered the new one. When the playout finds that its render
  changed the script within the first ten minutes after boot, it
  restarts RASTATIME-LIQUIDSOAP itself. Nothing is on air that
  early. Later changes still need the button or the manual
  order: playout first, then Liquidsoap.
- **Planned restart.** The Windows build of Liquidsoap slowly leaks
  memory while it runs, so the playout restarts it on purpose. When:
  inside a window that opens at 04:00 (machine setting
  `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`, `HH:MM` or `off`) once the
  engine is older than N days (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`,
  default 1, `0` = off) or uses more than
  `RASTATIME_LIQUIDSOAP_RESTART_AT_MB` (default 1536); and at any time
  of day above `RASTATIME_LIQUIDSOAP_RESTART_HARD_MB` (default 3072).
  How (since 2026-09-09): in a quiet moment when nothing is on air,
  or, with a 24/7 programme, between two tracks of the running
  playlist, so the gap of about two seconds replaces a crossfade
  instead of cutting into a track. A webstream or line-in on either
  side of the boundary makes it wait for the next one. Since 2026-10-02
  the track that follows the restart enters its audio by the few seconds
  the restart took, so the show keeps its times instead of running that
  much late to its end.
  Since 2026-09-09 the DJ sources report their connects and
  disconnects themselves, so the playout no longer polls the engine
  every five seconds; that poll was the main source of the growth.
  Once a week of memory readings stays flat,
  `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS` can be raised (7 to 30).
  Mind the soft memory limit as well: with Stereo Tool enabled the
  engine already starts at about 1000 MB, and a full music day adds
  16 to 19 MB per hour (about half a megabyte per played track), so
  the default 1536 MB is reached after roughly 30 hours and the memory
  trigger restarts the engine every second night no matter what the
  interval says. Raise `RASTATIME_LIQUIDSOAP_RESTART_AT_MB` to leave
  room above that baseline (2560 MB on a machine with 16 GB of RAM);
  the hard limit of 3072 MB keeps protecting the machine. Move the
  dashboard warning `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB` up with it
  (2816 MB, between the two limits), or the banner shows for the last
  day before every planned restart.
- **Standby fallback for listeners.** A second, tiny Liquidsoap
  (service RASTATIME-STANDBY, script `standby.liq` rendered by the
  playout with the same encoders) streams silence to a `-standby`
  copy of every public mount, and `icecast.xml` points each public
  mount at it as a fallback. During the two seconds of a restart
  Icecast moves the listeners to the standby mount and back again;
  nobody is disconnected. Install once as administrator with
  `backend/playout/config/nssm-install-standby.ps1` after the
  playout has rendered `standby.liq`, then restart Icecast once so
  it reads the fallback mounts. Set `RASTATIME_STANDBY_AUDIO` to an
  audio file if you prefer a station bed over silence. When you rename
  or add a stream output, the standby side follows by itself (restart
  RASTATIME-STANDBY when the playout log asks for it), but Icecast's
  fallback blocks do not: add a matching block for the new mount in
  `icecast.xml` and restart Icecast. The playout warns in its log at
  every start about public mounts without a fallback.
- **Name-safe or not at all.** Right before either automatic
  restart the playout re-reads the sound-card list and addresses
  the Main Output by device *name*. When that is not possible at
  that moment (the studio display is asleep and its HD-Audio
  endpoint has vanished, the device was renamed, or only a
  DirectSound/WDM-KS entry matches), the automatic restart is
  skipped and the running engine keeps playing; the playout log
  says why. Restart manually once the device is back. Background:
  on 2026-09-06 and 2026-09-07 the 04:01 restart used a device
  index taken while the display slept, the fresh engine opened the
  wrong endpoint, died within two seconds and was restarted in a
  loop until the morning.
- **Memory warning.** The dashboard banner shows *Liquidsoap uses
  N MB* when the engine's memory exceeds 2048 MB (machine setting
  `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`). Restart the playout and
  then Liquidsoap in a quiet moment. Since 2026-09-15 the playout log
  also records the engine's memory every 15 minutes, with the growth
  since the engine started; search `playout-stdout.log` for
  `Liquidsoap memory` to see the trend.
- **Main Output warning.** The banner shows *Main Output: Liquidsoap
  plays to … instead of …* when the engine holds no audio session
  on the chosen output device although it has been running for a
  while. The monitor is then on the wrong jack; restart the
  playout and then Liquidsoap.
- **Main Output stays open.** Since 2026-09-14 the engine opens the
  Main Output once when it starts and never closes it while it runs.
  The small buffer in front of the device used to run empty about
  twice a day; the engine then reopened the device from an outdated
  device list and either stopped or played to another device. Now a
  short silence fills such a moment, and the buffer adjusts the
  playback speed by an inaudible fraction so that it stays full.
  Should you ever suspect this adjustment, set the machine setting
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE` to `false` and restart
  the playout and then Liquidsoap; the output then stays open with a
  fixed buffer.
- **Engine-down warning.** The banner shows *Liquidsoap is not
  running* or *Liquidsoap keeps restarting (crash loop)* when no
  engine process exists or a new one appears on every scan. Read
  the newest `logs/liquidsoap-stdout-*.log` slice (usually the
  Main Output device), fix the cause,
  then restart the playout and then Liquidsoap.

---

## 3. Soundcard — Input Devices

> **Note (2026-10-20):** the input-device list is no longer on this page.
> The capture device of a Line-In is chosen in the Line-In entry itself
> (Library → Line-In → create or edit, see [LINE_IN.md](./LINE_IN.md)).
> The rest of this section describes the former list for reference.

The list shows every audio input device the operator-machine
exposes (built-in microphones, USB mics, mixer outputs, line-
in jacks, etc.). The checkbox controls which of those are
**candidates** for use as named Line-Ins.

### Which to enable

| Device | Tick? | Why |
|---|---|---|
| **Studio microphone** | Yes | The reason most stations have a line-in. |
| **Mixer output** (XLR / TRS via interface) | Yes | The full studio mix as a single source. |
| **Built-in microphone** | Only if used | Unticking suppresses it from the Line-In creation dropdown to avoid accidental selection. |
| **Webcam mic** | No (usually) | Low quality, often gets selected by accident. |
| **Line-in jack on the back** (if not in use) | No | Same accident-prevention. |

Ticking / unticking does **not** disable the device at the OS
level — Windows still sees it. RASTATIME just removes it from
the Line-In creation dropdown.

### Going from input device to named Line-In

To use a device as a scheduling source, create a named Line-In
in the Library under **Line Inputs → + New** — since 2026-09-17
that dialog is the one complete editor (name, device,
channels); the former Line-In Sources section on this page is
gone.  See [Line-In](./LINE_IN.md).

> **Operator tip.** A device must be ticked here *before* it
> appears in the new-Line-In dialog's device dropdown. If
> you cannot find your USB microphone in the Line-In dialog,
> the most common reason is that it is unticked on this
> page.

---

## 4. Default output for cue / monitor

The dropdown below the output device list re-states the
default in single-row form. The selection is the same data
as the radio button above; both stay in sync.

(Operationally redundant; kept for one-click discovery by
operators who scroll past the device list and look for a
"set default" control.)

---

## 5. Import Format

*(Since 2026-10-14.)*  One checkbox: **Convert lossless audio
(WAV, FLAC, ...) to MP3 320 kbps on import** — **on** by default.
It applies to every way a track enters the library: the browser
upload, the Local Import Folder, the FTP import and the bulk-import
command.  Click **Save** (top right or at the bottom); the next import
follows the new value, no restart is needed.

What the import does with each file:

| Audio inside the file | What happens |
|---|---|
| MP3, MP2, MP1, AAC in M4A / MP4, OGG Vorbis, Opus | Imported as it is — never re-encoded. |
| Raw AAC (`.aac`) | Always repacked into an `.m4a`, **without** re-encoding, whether the checkbox is on or off. A raw AAC file has no index, so its length can only be estimated (about 2 s too long on the files we checked), and it cannot carry tags. |
| Windows Media Audio (`.wma`, lossy or lossless) *(since 2026-10-21)* | Always converted to MP3 at 320 kbps, whether the checkbox is on or off; browsers cannot play WMA and it would be the one unnormalised format in the library.  The original is not kept. |
| Lossless: WAV, FLAC, AU, Apple Lossless (ALAC) in M4A | Checkbox **on**: converted to MP3 at 320 kbps before it enters the library; the lossless original is **not kept**.  Checkbox **off**: imported as it is. |

- **The audio counts, not the extension.**  An `.m4a` that holds
  Apple Lossless is converted; a `.wav` that holds MP3 data is not.
- **Tags and cover travel along.**  Title, artist, album, genre, year,
  track number, composer, copyright, label, ISRC, BPM, language,
  comment and the **Expiry** date are written into the MP3, and an
  embedded JPEG or PNG cover is kept.  The file keeps its name with
  the new extension (`Interview.wav` becomes `Interview.mp3`); a file
  without a title tag shows that new name as its title, like any
  untagged upload.
- **Sample rate and channels.**  32, 44.1 and 48 kHz stay as they
  are; other rates (for example 96 kHz) become 44.1 kHz.  More than
  two channels are mixed down to stereo.
- **Measured after the conversion.**  Length, cue points, ReplayGain
  and loudness are taken from the file that ends up in the library.
- **A failed conversion never costs the import**: the original file
  is then imported unchanged.
- The conversion runs at low priority, so a large batch does not take
  processing power from the playout; a converted track simply appears
  in the library a little later.
- **Podcast episodes are not converted** — they are downloaded
  straight into the library without passing the import analysis.

> **Why it works this way.**  The streams are lossy anyway, and a
> FLAC or WAV takes about three to four and a half times the space of
> a 320 kbps MP3.  MP3 is what the rest of the library is made of, and
> it carries the **Expiry** date reliably; in an M4A many tools lose
> it.  Lossy audio (MP3, AAC, Ogg Vorbis, Opus) is left alone because
> re-encoding one lossy format into another only costs quality.  See
> ARCHITECTURE §23.57.

> **Tracks imported before 2026-10-14.**  Lossless files that were
> already in the library are converted once by a technician with the
> `convert_lossless` command (a dry run first; a track that is on air
> or scheduled within the next six hours is skipped, and nothing is
> converted while the media library is being moved).  The track keeps
> its id, its place in playlists and shows and its Cue In; its
> loudness is measured again on the MP3.

> **How it works under the hood.**  The setting is the `cc_pref` key
> `convert_lossless_to_mp3` (absent = on).  The web application sends
> it with every import message to the analyzer
> (`options.convert_lossless`); the analyzer's `convert_format` step
> runs right after the tags are read.  A converted track keeps the md5
> of its original in `cc_files.source_md5`, so the bulk import still
> recognises the same WAV or FLAC as already imported.  Only the bulk
> import checks md5 at all; the upload page and the import folder never
> did.  Since 2026-10-16 `bulk_import --allow-duplicates` imports such a
> file anyway (same audio, different tags) instead of skipping it.

---

## 6. Local Import Folder

The Local Import Folder is a directory on the operator-machine
that the analyzer watches for new files. Anything dropped
into the folder is automatically imported into the Library on
the next analyzer poll cycle (every 60 s by default).

**Bulk Import: allow importing duplicates** (checkbox below the folder path, since 2026-10-16, saved with
the page's **Save** since 2026-10-27).  It is the default of the command-line bulk
import (`bulk_import`): off, a file whose md5 - or the md5 of its
lossless original - is already in the library is skipped; on, it is
imported as a second track, for example the same audio with different
tags.  The upload page and this Import Folder never check for
duplicates, so the checkbox changes nothing for them.  The switch
`--allow-duplicates` turns it on for a single run.

### Configuring the folder

| Field | Notes |
|---|---|
| **Folder path** | An absolute path on the operator-machine. Must exist and be readable by the RASTATIME-ANALYZER service. Default: `C:\rastatime\import\`. Leave blank to disable the feature. |
| **Last scanned** | When the analyzer last ran a scan + summary of the result. Refresh the page to see the latest. |

The **Scan Now** button triggers an immediate scan without
waiting for the 60 s poll. Use it after dropping a batch
into the folder to import without delay.

### How files are processed

The scanner runs every 5 minutes (and immediately on **Scan Now**).
For every file lying directly in the folder:

1. **Non-audio files are skipped** and left in place — the scanner
   only owns audio files (`mp3`, `wav`, `m4a`, `mp4`, `flac`, `ogg`,
   `oga`, `aac`, `opus`, `mp2`, `mp1`, `au`; since 2026-10-14 exactly
   the list the browser upload accepts).  The status line reports them
   as "non-audio files left alone".
2. **Files still settling are left for later (since 2026-09-17).**
   A file modified within the last 60 seconds may still be being
   written (slow copy, FTP upload); the status line reports it as
   "still being copied" and a later scan picks it up.
3. Every audio file at rest is handed to the **standard upload
   pipeline**: a library row is created, the file is **moved** (not
   copied) into the library's `organize` area, and the analyzer takes
   it from there — metadata read, conversion as set under
   **Import Format** (section 5), playability check, final place in
   the library.  From then on it behaves exactly like a file uploaded
   through the web UI.
4. **If the hand-over fails, the file is moved to the `_failed`
   subfolder** of the import folder (since 2026-10-14; until then it
   was deleted).  It keeps its relative path there
   (`Album/Song.wav` becomes `_failed/Album/Song.wav`; if that name is
   taken, a number is added: `Song (2).wav`).  The scanner never looks
   into `_failed`, so a broken file is not retried on every scan — and
   a refused file is never deleted.  Should even the move fail, the
   file stays where it is and the next scan tries again.

The folder therefore empties itself of audio files after each scan —
moved into the library on success, into `_failed` on failure.
Non-audio files stay.  The status line says how many files went to
`_failed` ("2 failed (moved to _failed)").

### Subfolders and large batches (since 2026-10-08)

Subfolders are **walked**: every audio file in the import folder and
in any subfolder is imported, folder by folder in path order, and a
subfolder the moves leave empty is removed.  The `_failed` subfolder
is the exception: it is never walked and never removed.  The folder
structure is not carried into the library (the library organises files
by their metadata), so tag the files before you copy them.

A scan also hands over nothing while **300 or more files** are still
queued at the analyzer (it processes about one file per second); the
status line shows that queue.  This keeps the library free of rows
that wait so long that the hourly clean-up marks them as failed.

One scan hands over at most **300 files** and stops after **20
seconds**; the rest waits for the next run (every 5 minutes, or
**Scan Now**), and the status line says how many are waiting.  This
keeps a scan inside PHP's request limit - a scan that died mid-move
used to leave half a file behind.  The analyzer then works through
the queue one file at a time; on this machine a four-minute MP3 takes
about 1.1 s (probe of 50 files, 2026-10-08), so expect roughly
3,000 tracks per hour end to end and plan a 20,000-track import for
about seven hours.  Put the import folder on the same drive as the media library
(the move is then instant and atomic), set *Track Type Upload Default*
first (the owner needs no setting: background imports belong to the
first administrator, Scan Now imports to you), and copy in batches of
a few thousand.

### Ownership

With **Scan Now** the imported files belong to the operator who
clicked the button.  Files picked up by the background scan belong to
the first administrator account.

> **How it works under the hood.**  The scanner is the
> `LocalImportScanTask` in the legacy PHP frontend's task manager: it
> piggy-backs on normal web requests, runs at most every 300 s, and
> updates the `cc_pref` keys `local_import_last_run` and
> `local_import_last_status` (the status line on this page).  See
> ARCHITECTURE §23.12 and, for the `_failed` folder and the shared
> extension list, §23.57.

### Import from FTP server

Below the Import Folder sits a second import source (since
2026-09-17): RASTATIME fetches audio files from an FTP, FTPS or SFTP
server every 5 minutes (or immediately with **Fetch now**) and feeds
them through the Import Folder above — which must therefore be
configured.  Enable it with the checkbox, fill in server, port
(empty = protocol default), account and the **absolute** remote
folder, then **Save**.

- **Mailbox semantics.**  After a verified download the remote file
  is deleted — the account needs delete permission.  If the delete
  fails, the file is imported anyway and the status warns, because
  the next cycle would fetch a duplicate.
- **Uploads in progress are safe.**  A file is only fetched when its
  size has been unchanged for at least a minute across two checks,
  and the size is verified again after the download.  Until then the
  status counts it as "settling".
- **Non-audio files stay on the server.**  Only the audio extensions
  of the Import Folder are fetched.  A remote entry named `_failed` is
  left alone.
- **Prefer FTPS or SFTP** — plain FTP sends the password
  unencrypted.  The password is stored in the settings database like
  the other service passwords, so the fetch can log in unattended;
  the page never shows it again.
- Each cycle starts new downloads for at most one minute; anything
  beyond that is picked up by the next cycle ("left for the next
  run" in the status).

---

## 7. Media Library Location

Since 2026-09-16 the folder that holds the media library (imported
tracks, covers, show images) is a setting on this page, not a line in
`rastatime.conf`. The configuration file only supplies the initial
value; once you have moved the library, the setting wins.

The section shows the **current location**, where that value comes
from (the setting or the configuration file), the number of files and
the size of the library. To move it:

1. Enter the **new location** - an absolute path on a local drive of
   this machine, for example `D:\stor`. The folder is created if it
   does not exist. Network paths are not supported.
2. Click **Check**. RASTATIME confirms that it can write there and
   that the drive has enough free space (the library plus ten percent).
3. Click **Move library** and confirm. A progress bar follows the
   copy.

What happens during the move:

- The stream, the schedule, recordings and the local monitor keep
  running; nothing is on air from the library folder itself, the
  playout plays from its cache.
- Imports pause: uploads, the Local Import Folder scan, podcast
  downloads and image uploads refuse with a short message until the
  move is done.
- RASTATIME copies the library with robocopy, then verifies that every
  file arrived with the right size and that every track in the
  database can be found at the new place. Only then does it switch
  the setting. The web application and the API follow at once, the
  playout at its next schedule refresh (within two minutes).
- The **previous copy stays on disk**. Delete it yourself once you are
  satisfied - and delete only its contents, not the folder named in
  `rastatime.conf`, because the web application checks at start that
  this folder exists.

If the RASTATIME-API service restarts while a copy is running, the
section shows the move as *interrupted*. Enter the same target and
move again: the copy resumes where it stopped, files already copied
are skipped. **Cancel move** stops a running copy; what was copied so
far stays at the target and a later move resumes from there.

Should the configured location ever be missing or read-only - a drive
that is not mounted, a renamed folder - the dashboard banner shows
*Media library location … is missing* until it is back.

---

## 8. Recording folders (related)

Settings → Local Machine has **two** recording-output folders:

### Show Recording

Where [Record-per-Show](./RECORD_PER_SHOW.md) writes one file
per show flagged "Record this show". *(Renamed from "Recording
Folder" when 24/7 Recording was added — 2026-06-06.)*

Default: `C:\rastatime\recordings\`.

**Format** and **Bitrate (kbps)** *(since 2026-10-18)*: MP3
(default) / AAC / OGG Vorbis / Opus, 96–320 kbps (default 320).
The playout applies a change in its next quiet moment (or at the
next track boundary); files already written keep their format,
new files get the matching extension.

**Copy Show Recordings into Library** *(since 2026-10-19)*: when
ticked, a tagged copy of every finished show recording is imported
into the library (track type "Recordings", title `<show> <date
time>`, linked to the show instance); the file in the recording
folder stays untouched.  Details in
[Record-per-Show, section 3.6](./RECORD_PER_SHOW.md).  Saved with
the page's **Save**; the playout needs one restart
after the update, afterwards the switch works immediately.

### 24/7 Recording Folder

Where the always-on [24/7 Recording](./RECORD_PER_HOUR.md)
writes one file per clock hour (plus a `.cues.json` cue
sidecar), independent of shows. Enable it, pick a format /
bitrate, and set an automatic-delete window right in this
section. Keep it **separate** from the Show Recording Folder so
the retention cleanup never touches per-show files. The folder
is created automatically on save if it does not yet exist.

Neither folder is a candidate for the Library — recordings are
standalone files for download / archive, not auto-imported. To
put a recording back into the Library as a track, manually drag
it into the Local Import Folder.

> **Apply changes by restarting the playout service.** The
> recorder settings are baked into the Liquidsoap script at
> startup, so after changing them, restart **RASTATIME-PLAYOUT**
> (the Save dialog reminds you). Only the 24/7
> **Delete after (days)** value takes effect without a restart.

---

## 9. Frequently-asked

### "My USB mic shows up in Windows but not in RASTATIME."

Three things to check:

1. The mic is **ticked** on the Input Devices list on this
   page.
2. The `RASTATIME-API` service is running and the
   `/api/v2/audio/devices` endpoint returns the mic — test
   with `curl http://localhost:8765/api/v2/audio/devices`.
3. The Windows audio driver is still allowing input access
   (some Windows updates re-set this; check Settings →
   Privacy → Microphone).

### "Local Import Folder doesn't import anything."

Diagnostic order:

1. The folder path is correct and exists.
2. The web frontend is running (`RASTATIME-APACHE`) — the scanner
   piggy-backs on web requests, so **Last scanned** only advances
   while the UI sees traffic.  **Scan Now** forces a run.
3. A file modified within the last 60 seconds counts as "still
   being copied" — wait a minute and scan again.
4. "N failed (moved to _failed)" in the status line means the
   hand-over failed and the file now lies in the `_failed` subfolder
   (see the next question).  Check the file in another player and
   look into `logs\legacy.log` for the reason; the
   `RASTATIME-ANALYZER` service must be running for the import to
   finish.

### "What do I do with the files in `_failed`?"

Every file there could not be handed over to the library.  Search
`logs\legacy.log` for its name to see why, check it in another
player, repair or re-export it if needed, and move it back into the
import folder — anywhere outside `_failed`; the next scan imports it.
Delete what you no longer need: RASTATIME never empties `_failed`
itself.

### "I imported a WAV or FLAC file and the library shows an MP3."

That is the **Import Format** setting (section 5): lossless files are
converted to MP3 320 kbps on import, and the lossless original is not
kept.  To import lossless files unchanged, untick the checkbox and
click **Save** *before* you import them.

### "Why move and not copy in the Local Import Folder?"

A copy-based workflow leaves the operator with two copies of
every imported file and no clear ownership. A move-based
workflow guarantees the file is in exactly one place after
import. Operators who want to keep the original should drop
a copy into the import folder, not the original.

### "Can the Local Import Folder be on a network share?"

Yes, with two caveats:

- The share must be mounted at the path RASTATIME sees
  (e.g. `Z:\import\`). UNC paths `\\server\share\import` are
  *not* reliable with NSSM-launched services on Windows.
- The RASTATIME-ANALYZER service account must have read +
  write + delete permission on the share.

### "Can I have multiple Local Import Folders?"

No. The poller scans one configured directory. If you need
multiple drop points, mount them all under a single root
(e.g. `Z:\imports\` with subdirectories for each source).

### "What's the difference between the Local Import Folder and the upload button?"

| | Upload button | Local Import Folder |
|---|---|---|
| Origin | Browser-side | Server-side filesystem |
| Best for | One or two files | Batches of many files |
| Timeout | Browser may time out on large batches | No timeout (server-side poller) |
| Ownership | Logged-in user | Configured default owner |

### "Does the Output Device selection affect what listeners hear?"

No. The Output Device on this page is the **monitor / cue**
output. Listeners hear the [Streams](./STREAMS.md) output
which is sent to Icecast and is unrelated to this device.

---

## Where to go next

* [Line-In](./LINE_IN.md) — turning a ticked input device
  into a named, schedulable library item.
* [Library](./LIBRARY.md) → §2 — alternatives to the Local
  Import Folder (browser upload, podcast subscription).
* [Streams](./STREAMS.md) — the listener-side audio output.
* [`docs/operator/DEVICE_MISSING.md`](../operator/DEVICE_MISSING.md)
  — when a previously-configured device disappears.
