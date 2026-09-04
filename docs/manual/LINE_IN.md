# Line-In

> **Where you are in the manual.** This chapter covers the
> **Line-In** library item type — named live audio inputs you
> can drag onto playlists and shows. For the operator-machine
> sound-card configuration that makes a line-in physically
> available, see [Local Machine](./LOCAL_MACHINE.md). For the
> emergency procedure when a line-in goes silent or noisy,
> see [`docs/operator/LINE_IN_BROKEN.md`](../operator/LINE_IN_BROKEN.md).

A **Line-In** is a named live audio input from a sound-card
device on the operator's machine — a microphone, a mixer
output, a CD player, an external audio interface — that
RASTATIME exposes as a library item. Once configured, you can
drag it into playlists and onto shows exactly the same way you
drag a track.

Line-Ins are new in RASTATIME (2026-05-12). They replace the
single hardcoded "Line In" slot the upstream LibreTime had,
and add named, persistent, drag-and-droppable, library-listed
behaviour.

---

## 1. Concept overview

A Line-In has two layers:

| Layer | What it is | Where it lives |
|---|---|---|
| **Physical device** | The actual sound-card input — a USB microphone, a built-in line jack, an XLR interface, etc. Identified by its OS-side device ID. | The operator-machine sound-card setup; see [Local Machine](./LOCAL_MACHINE.md). |
| **Named Line-In** | A library row that *references* a physical device by ID, plus a display name and configuration. | `rastatime_linein` table; visible in Library + on the Line-In Library page. |

A single physical device can back **at most one** Line-In at a
time. Re-binding the same device to a second Line-In
overrides the first.

---

## 2. The Line-In Library page

Settings → **Line-In Library** (or click the green Line-In
chip in the main Library page).

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Line-Ins                                          + New     │
   ├──────────────────────────────────────────────────────────────┤
   │  Name             │ Device                  │ Default Length │
   ├───────────────────┼─────────────────────────┼────────────────┤
   │  Studio Mic       │ USB Mic (Default Input) │  ∞              │
   │  Mixer Out        │ Behringer X-AIR Output  │  01h 00m 00s    │
   │  CD Player        │ Front Mic-In            │  03m 00s        │
   │  Phone-Line       │ Realtek HD Audio In #2  │  10m 00s        │
   └───────────────────┴─────────────────────────┴────────────────┘
```

Each row is a named Line-In. The table columns:

| Column | Meaning |
|---|---|
| **Name** | The display name. Used everywhere the Line-In appears (Library list, drag chip, schedule item, Now-Playing widget). |
| **Device** | The sound-card device the Line-In references. The label is the device's OS-side name. |
| **Default Length** | The default duration a Line-In row occupies when dragged into a playlist or show. `∞` means "play until told to stop"; a finite duration means the row schedules for exactly that long. |

The toolbar:

| Button | What it does |
|---|---|
| **+ New** | Open the new-Line-In dialog. |
| **Edit** (row context menu) | Open the edit dialog for that Line-In. |
| **Enable / Disable** | Toggle the Line-In's available state without deleting. Disabled Line-Ins do not appear in the drag library. |
| **Delete** | Remove the Line-In. Schedule rows referencing it are removed too. |

> **How it works under the hood.** All mutating actions are
> thin pass-throughs from
> `application/controllers/LineinController.php` to the
> Django REST API at `/api/v2/audio/linein[/<id>]`. The
> controller only enforces ACL (Admin + Super Admin); the
> Python side at `backend/api/libretime_api/linein/` owns
> validation and persistence in `rastatime_linein`. See
> ARCHITECTURE §14.

---

## 3. Creating a Line-In

Line-In Library → **+ New**.

```
   ┌──────────────────────────────────────────────────────────────┐
   │  New Line-In                                                 │
   ├──────────────────────────────────────────────────────────────┤
   │   Name:           [                       ]                  │
   │   Device:         [Select a device... ▾]                     │
   │     Input channels are chosen in Settings → Local Machine    │
   │   Default Length: [10m 00s   ]    (use 00s for infinite)     │
   │  ☑  Enabled                                                  │
   ├──────────────────────────────────────────────────────────────┤
   │                                       [Cancel ]  [ Save  ]   │
   └──────────────────────────────────────────────────────────────┘
```

| Field | Notes |
|---|---|
| **Name** | Required. Unique. The visible label everywhere. |
| **Device** | Required. Dropdown lists every input device the OS sees right now. If your device is missing from the dropdown, see [Local Machine](./LOCAL_MACHINE.md) → device probing. |
| **Default Length** | Required. Format `HHh MMm SSs` (the same parser as Webstreams). For "play until told to stop" use `0h 0m 0s` (displays as `∞`). |
| **Enabled** | Defaults to on. Untick to create the Line-In but suppress it from the drag library. |

> **Where are the input channels?** This quick editor deliberately
> stays lean — the **Input Channels** picker (and the Priority /
> full management table) lives in the full editor under
> **Settings → Local Machine → Line-In Sources**; the dialog links
> there. A Line-In created here captures channels 1/2 until you pick
> a different pair in the full editor.

### Multichannel interfaces: one Line-In per studio

If the station's audio interface has more than two inputs (e.g. a
16-input Tascam US-16x08 with several studios wired to it), create
**one Line-In per studio** — same **Device**, different **Input
Channels** (picked in **Settings → Local Machine → Line-In
Sources**):

- `Studio A` → Device `US-16x08`, Input Channels `Stereo 1/2`
- `Studio B` → Device `US-16x08`, Input Channels `Stereo 5/6`
- `Studio C guest mic` → Device `US-16x08`, Input Channels `Mono 7`

Each Line-In then behaves like its own source in the Library and in
shows; back-to-back shows from different studios on the same
interface switch cleanly at the show boundary.

> **How it works under the hood.** Every Line-In — `Stereo 1/2`
> included, since 2026-09-03 — runs through a small capture feeder.
> The feeder reads the device over the MME API (the one Windows API
> that demonstrably delivers all channels without touching system
> settings), extracts the selected channels, and feeds them through
> the local `/linein-capture` mount into the stream engine. Until
> 2026-09-03 plain `Stereo 1/2` took a direct DirectShow path
> instead; that path addresses the device by its Windows audio
> endpoint GUID, which DirectShow does not recognise, so on a
> multichannel interface it failed to open the device and the slot
> stayed silent. Any other channel selection could never use it
> anyway — the DirectShow pin of a multichannel interface only ever
> offers two channels. The feeder needs the device's display name
> stored on the row, so **Line-Ins saved before this feature exist
> must be re-saved once**; without the name they fall back to the
> old DirectShow path and may play silence.

Click **Save**. The Line-In appears immediately in the
Library page's Line-In chip filter.

### The default length matters

The Default Length is the duration a Line-In row reserves in
a show:

- For a **microphone** in a normal talk-only studio, set
  Default Length to the typical talk-segment length (5 min
  is common).
- For a **mixer output** that drives the entire show, set
  Default Length to the full show length (e.g. 60 min) or
  infinite.
- For a **CD player** or other timed source, set Default
  Length to the typical track length (3 min).

The operator can always override the duration per use in the
show-builder; the Default Length is just the starting value.

---

## 4. Using a Line-In in a show

Two paths:

### 4.1 Direct drag onto a show

Show-builder → drag the Line-In row from the Library panel
onto the show. A schedule item appears with the Line-In's
name and the Line-In's Default Length.

Click the item → **Edit** → set the override duration for
this specific use, or change the cue-in delay.

### 4.2 Inside a playlist

Playlist editor → drag the Line-In from the Library. The
playlist row carries the Line-In's reference + its Default
Length, and behaves like any other playlist item.

When the playlist is later scheduled into a show (via
drag-and-drop or via an autoloading playlist), the Line-In
becomes a schedule item exactly as in path 4.1.

> **How it works under the hood.** Migration 0054
> (2026-05-19) added `cc_playlistcontents.linein_id` as a
> nullable foreign key into `rastatime_linein`, plus a CHECK
> constraint that exactly one of `file_id` / `stream_id` /
> `block_id` / `linein_id` is non-NULL per row. Type 3 in
> `cc_playlistcontents.type` indicates a Line-In row.
> ARCHITECTURE §23.18 covers the schema decision.

### What plays when the Line-In's slot starts?

**Liquidsoap engine path (production default since 2026-05-29):**

1. Pypo starts the FfmpegLineinCapture subprocess for the
   configured sound-card device (MME capture feeder → MP3 → local
   Icecast mount at `http://localhost:8000/linein-capture`).
2. Pypo sends a single telnet command to Liquidsoap:
   `linein.start` — telling the dedicated `input.http` source
   to begin consuming the local capture mount.
3. Liquidsoap buffers a short amount of audio (1.0 s since
   2026-09-04).  Once `source.is_ready` flips true, the
   bus-switch routes audio to the linein source — listeners hear
   the microphone.  The `input.http` companion is armed *in
   parallel* with the capture start, so its buffer fills while the
   capture is warming up instead of strictly afterwards.
4. At the configured duration Pypo sends `linein.stop` plus
   stops FfmpegLineinCapture; the switch falls back to
   scheduled.  Since 2026-09-04 the hand-over is a **mix, not a
   cut**: the Line-In is taken off air through a *gate* in the
   Liquidsoap bus, the bus fades it out under the successor over
   the Default Crossfade Duration (Settings → General; 0 = the
   successor starts at full level at once and the Line-In fades
   out underneath, "ducking"), and only then are the capture and
   the source stopped — so the presenter's last words, which are
   still in the pipeline, are heard instead of lost.  Whatever
   follows — a jingle, a webstream — releases the Line-In the same
   way when it starts, so the microphone can never stay on air past
   its slot.  The one exception is a **true back-to-back** follow-up
   on the same device (the next Line-In starting within ~2 s): that
   one inherits the running capture without a bounce.

**Recording behaviour (new since Phase F, 2026-05-29):**
Scheduled line-inputs now flow through the Liquidsoap internal
bus that `output.file` taps, so they land in the per-show
`.mp3` recording archive — same coverage you get for tracks
and webstreams.  Pre-Phase F, line-input-only shows had
silent recordings.

**Why we keep FfmpegLineinCapture instead of Liquidsoap's
`input.portaudio`:** input.portaudio has no `set_device`
method at runtime, no auto-reconnect on USB-cable unplug,
and uses PortAudio-integer-indices instead of the Windows
audio endpoint GUIDs the frontend library tracks.
FfmpegLineinCapture's watchdog handles unplug-replug
transparently; Liquidsoap consumes its local Icecast mount
without caring about device identity.

**Latency — start of the slot and end of the slot:** the line-in
path has an end-to-end latency: what is spoken at studio time *t*
reaches the stream at *t + L*.  Two consequences: the start of a
slot is silent for roughly L while the pipeline fills, and at the
end of the slot the last L seconds are still in the pipeline when
the source is closed — **they never reach the stream**.  Measured
on air 2026-09-04 (counting seconds into the microphone): L was
~6 s.  Five of those seconds were FFmpeg's *format autodetection*
on the capture mount — a listener joins the Icecast mount
mid-stream with no header in sight, so the decoder scanned for
~5 s before it locked on.  Since 2026-09-04 the format is forced
(`format="mp3"`, the capture always muxes MP3), the `input.http`
buffer is 1.0 s (env-tunable via
`RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS`) and the
capture's start-up health check is 0.75 s.  Measured after that:
start gap 2 s, end-of-slot loss 2 s.

Both remaining seconds are addressed since 2026-09-04 (evening):
**pre-warm** — 10 s before a Line-In slot the playout already
starts the capture and connects the Liquidsoap source with the
bus gate closed, so at the slot start only the gate opens and the
Line-In is on air within a frame; and the **gate-off mix** at the
slot end (see step 4 above), which plays the buffered tail under
the successor instead of discarding it.  Pre-warming is skipped
when another Line-In is on air (one capture at a time) or when
the row has no stored device name; such slots start the normal way
(~2 s).

**Legacy mpv / VLC engine paths (only when
`RASTATIME_PLAYOUT_ENGINE=mpv` or `=vlc`):**
mpv opens the FfmpegLineinCapture listen URL directly and
FfmpegStreamer re-encodes to Icecast.  No recording for
line-in-only shows in this mode.

When the slot's duration elapses, the engine sends a
`LINEIN_END` event and the source switcher returns to the
schedule.

> **Operator tip.** If a Line-In is configured for "infinite"
> duration in a slot, the playout engine plays it until the
> *show* ends — not literally forever. The slot ends with the
> show.

---

## 5. Editing or removing a Line-In

### Edit

Line-In Library → click the row → **Edit**. Change name,
device, default length, or enabled state. Click **Save**.

Effects:

- **Name change** propagates to the Library list and to the
  Now-Playing widget on the next refresh. Existing schedule
  items keep the old name until the next build cycle.
- **Device change** propagates to *every* future use,
  including schedule items already in upcoming shows.
- **Default Length change** affects only *new* uses; existing
  schedule items keep their configured duration.
- **Enabled = off** removes the Line-In from the drag library
  immediately. Already-scheduled uses still play (use Delete
  if you want to remove them too).

### Disable

The fastest way to "stop using this Line-In for now":

Row context menu → **Disable**. The Line-In stays in the
library page (you can re-enable later) but disappears from
the drag-source library.

### Delete

Row context menu → **Delete**. Confirm. The Line-In is
removed *and* every `cc_playlistcontents` and `cc_schedule`
row referencing it is removed (CASCADE).

> **Operator tip.** Prefer **Disable** over **Delete** unless
> you are sure you will never use the Line-In again. Disable
> is reversible; Delete cascades into shows you may not have
> noticed.

---

## 6. The physical-device dependency

A Line-In references a sound-card device by **OS-side ID**.
That ID is stable across reboots as long as:

- The device stays plugged in.
- No other audio software has been installed that re-assigns
  device IDs (rare on Windows, occasional on Linux).

If the device goes missing (unplugged, driver crashed,
operator-machine rebooted with the device powered off):

- The Line-In is still in the Library.
- The Line-In's row in the Settings → Line-In Library page
  shows a **red exclamation** badge next to the device
  column.
- Any schedule that tries to play the Line-In skips it with
  a "Device not found" warning in the playout log.
- The fallback (silence or fallback loop) plays for the
  duration of the slot.

See [`docs/operator/DEVICE_MISSING.md`](../operator/DEVICE_MISSING.md)
for the recovery runbook.

> **How it works under the hood.** The playout engine checks
> device availability via `audio.soundcard.windows_manager`
> before opening the input. The device list comes from a live
> WASAPI / portaudio enumeration on Windows. The "red
> exclamation" UI cue is driven by the
> `/api/v2/audio/devices` endpoint comparing the persisted
> ID against the current enumeration.

---

## 7. Permissions

Only **Admin (A)** and **Super Admin (S)** roles can create,
edit, or delete Line-Ins. Reasons:

- A Line-In references a physical device on the operator's
  machine. Changes can break the schedule of every DJ.
- Sound-card configuration is station-wide.

DJs (H) and Program Managers (P) can drag existing Line-Ins
into their own playlists / shows, but cannot create or
modify the underlying Line-In definitions.

> **How it works under the hood.** ACL enforced in
> `application/configs/ACL.php` resource `linein-controller`.

---

## 8. Frequently-asked

### "Where is the upstream 'Show Source' / 'Master Source' / 'Line In' setting?"

Upstream LibreTime had three hardcoded inputs ("Show Source",
"Master Source", "Line In") configured in
**Settings → Live Sources**. RASTATIME keeps Show Source and
Master Source (these are remote-DJ inputs over Icecast — see
[Streams](./STREAMS.md) → §3 Sources) but replaces the
single hardcoded "Line In" with the named-Line-In feature
documented here.

If you have legacy data from a LibreTime / Airtime install,
the old "Line In" toggle is dropped during migration. The
upstream "Record from Line In?" checkbox is repurposed (see
[Record-per-Show](./RECORD_PER_SHOW.md)).

### "Can two Line-Ins reference the same physical device?"

Yes, but only one will succeed at any moment. Most sound-card
drivers grant exclusive access to the first opener; a second
Line-In trying to open the same device at the same time fails
with "device busy". Useful only for "the same physical
device under two different names" cases — typically rare.

### "Why does my microphone show up as 'Microphone (USB Audio CODEC)'?"

That is the OS-side device name. Windows assigns the name
based on the driver's reported product ID. The display name
in RASTATIME is the **Line-In's Name** (you set this on the
new-Line-In dialog), not the OS-side device name — so call
it "Studio Mic" or "Anna's Mic" and ignore the OS label.

### "Can a Line-In be the autoloading playlist's only content?"

Yes. Create a playlist containing exactly one Line-In row
with Default Length = the show length (or infinite). Attach
this playlist as the show's autoloading playlist. Every
instance of the show will play exclusively from the
Line-In.

### "Is the Line-In's audio recorded if Record-per-Show is on?"

Yes (since Phase F, 2026-05-29).  In the Liquidsoap engine
mode, the line-in audio flows through the same internal
audio bus that `output.file` taps for the per-show MP3
archive, so it gets captured natively — alongside any
regular tracks or scheduled webstreams in the same show.
See [Record-per-Show](./RECORD_PER_SHOW.md).

(In the deprecated mpv/VLC engine modes, recording is not
available — see [Settings → Playout Engine](./SETTINGS.md).)

### "Can I add a network audio source (e.g. AES67 / Dante) as a Line-In?"

Only if the source presents as a Windows sound-card input
device — many AES67 / Dante drivers ship a virtual
sound-card. If it shows up in Settings → Local Machine's
input-device dropdown, it works as a Line-In.

---

## Where to go next

* [Local Machine](./LOCAL_MACHINE.md) — physical sound-card
  configuration on the operator's machine.
* [Library](./LIBRARY.md) — Line-Ins appear in the main
  Library too; the chip filter shows them.
* [Dashboard](./DASHBOARD.md) → Source state — see which
  Line-In is currently on air.
* [`docs/operator/LINE_IN_BROKEN.md`](../operator/LINE_IN_BROKEN.md)
  — emergency procedure when a Line-In goes silent or noisy.
* [`docs/operator/DEVICE_MISSING.md`](../operator/DEVICE_MISSING.md)
  — when the underlying sound-card device disappears.
