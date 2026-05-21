# Local Machine

> **Where you are in the manual.** This chapter covers the
> Settings → **Local Machine** page, which owns every concern
> tied to the *operator's machine itself* — sound-card
> output, line-in input devices, and the Local Import Folder.
> For the network-side outbound streams, see
> [Streams](./STREAMS.md). For the Library item type that
> *references* a sound-card input, see [Line-In](./LINE_IN.md).

The **Local Machine** page is where you tell RASTATIME about
the physical resources on the operator-machine: which speaker
output to play through, which devices count as line-in
candidates, and which folder the analyzer should watch for
imported tracks.

The page replaces the upstream LibreTime "Soundcard" page and
adds the Import Folder feature. The legacy URL still works;
only the page title and the slug change.

---

## 1. The page

Settings → **Local Machine**.

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
   │  Local Import Folder                                            │
   ├─────────────────────────────────────────────────────────────────┤
   │  Folder path:    [C:\rastatime\import\                  ]        │
   │  Last scanned:   2026-05-21 14:32 — found 0 new files           │
   │                                                                 │
   │  [ Scan Now ]                                                   │
   └─────────────────────────────────────────────────────────────────┘
```

Three sections, each independent.

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

---

## 3. Soundcard — Input Devices

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

This page only marks devices as candidates. To actually use a
device as a scheduling source, create a named Line-In via
Settings → **Line-In Library** → **+ New**. See
[Line-In](./LINE_IN.md).

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

## 5. Local Import Folder

The Local Import Folder is a directory on the operator-machine
that the analyzer watches for new files. Anything dropped
into the folder is automatically imported into the Library on
the next analyzer poll cycle (every 60 s by default).

### Configuring the folder

| Field | Notes |
|---|---|
| **Folder path** | An absolute path on the operator-machine. Must exist and be readable by the RASTATIME-ANALYZER service. Default: `C:\rastatime\import\`. Leave blank to disable the feature. |
| **Last scanned** | When the analyzer last ran a scan + summary of the result. Refresh the page to see the latest. |

The **Scan Now** button triggers an immediate scan without
waiting for the 60 s poll. Use it after dropping a batch
into the folder to import without delay.

### How files are processed

For each new file the analyzer finds:

1. The file is moved (not copied) into a staging area
   (`C:\rastatime\import\.staging\`).
2. The analyzer runs ffprobe (metadata) + ffmpeg playability
   check.
3. On success, the file is moved to
   `C:\rastatime\media\<owner>\<year>\<month>\<filename>` and
   a `cc_files` row is inserted.
4. On hard failure, the file is moved to
   `C:\rastatime\import\.failed\` with a sidecar `.err`
   text file explaining the error.
5. On soft failure (decoder warnings but full decode), the
   file is imported with a yellow warning badge.

The operator's import folder itself is left empty after each
poll — every file is either imported or moved to `.failed`.

### Subfolders

Subfolders are scanned recursively. Files in subfolders are
imported, and the **subfolder name** becomes the imported
track's `album` metadata field if the file's own ID3 album
tag is empty. This is the common operator pattern:

```
   C:\rastatime\import\
     ├─ 2026-05-21 morning show/
     │   ├─ intro-jingle.mp3       → album = "2026-05-21 morning show"
     │   ├─ track1.mp3              → album = ditto
     │   └─ outro.mp3               → album = ditto
     └─ stings/
         ├─ news-bumper.mp3         → album = "stings"
         └─ weather-bumper.mp3      → album = ditto
```

### Ownership

Imported files are owned by the configured **default import
owner** (set under General Preferences → Default Import
Owner). Defaults to `admin`. To attribute imports to a
specific DJ, change the owner before triggering the import.

> **How it works under the hood.** The Local Import Folder
> poller is one of the `RASTATIME-WORKER` service's
> background jobs (the `LocalImportJob`). It runs every
> 60 s via the `BackgroundRunner` framework, scans the
> configured directory, queues files into the analyzer
> pipeline, and updates `cc_pref` keys `local_import_last_run`
> and `local_import_last_status`. See ARCHITECTURE §16.

---

## 6. Local Recording Folder (related)

Hidden under Settings → General Preferences but worth
mentioning here: the **Local Recording Folder** is where
[Record-per-Show](./RECORD_PER_SHOW.md) writes its captured
files.

Default: `C:\rastatime\recordings\`.

This is *not* a candidate for the Library — recordings are
saved as standalone files for download / archive, and are
not auto-imported. To put a recording back into the Library
as a track, manually drag it from the recordings folder into
the Local Import Folder.

---

## 7. Frequently-asked

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
2. The `RASTATIME-ANALYZER` service is running.
3. The `RASTATIME-WORKER` service is running (it owns the
   poller).
4. Check **Last scanned** — if it shows "found N new files,
   N failed", the files are being processed and failing the
   playability check. Look in
   `C:\rastatime\import\.failed\` for the `.err` files.

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
