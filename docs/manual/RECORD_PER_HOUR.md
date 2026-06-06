# 24/7 Recording (Record-per-Hour)

> **Where you are in the manual.** This is the station-wide
> **24/7 Recording** feature, configured in
> [Settings → Local Machine](./LOCAL_MACHINE.md). It is the
> always-on companion to the per-show
> [Record-per-Show](./RECORD_PER_SHOW.md) feature.

**24/7 Recording** continuously records everything that goes
on air — around the clock, independent of shows — and splits
it into one file per clock hour. It captures the gaps that
per-show recording misses (AutoDJ filler, silence between
shows, unscheduled content, emergencies), which makes it the
right tool for **compliance archives, listen-again / catch-up,
and emergency backup**.

Like the per-show recorder, it is a parallel **output-tap** on
the internal Liquidsoap bus: it changes nothing about how the
station is scheduled or played — it just listens to the on-air
audio and writes it to disk.

---

## 1. 24/7 Recording vs. Record-per-Show

The two recorders are independent and can run at the same
time, into **separate folders**.

| | Record-per-Show | 24/7 Recording |
|---|---|---|
| **Scope** | One file per show flagged "Record this show" | One file per clock hour, always on |
| **Covers** | Only while a recorded show is on air | Everything aired, 24/7 (incl. gaps, filler, emergencies) |
| **Configured** | Per show (Calendar) | Once (Settings → Local Machine) |
| **Filename** | `<YYYY-MM-DD HH-MM> - <show>.mp3` | `<YYYY-MM-DD HH>-00.<ext>` |
| **Quality** | Fixed 320 kbps MP3 | Operator-chosen format + bitrate (default 192 kbps MP3) |
| **Cue sidecars** | No | Yes (`.cues.json` per hour) |

> **Why two recorders?** Per-show gives you a clean,
> show-titled file for the shows you care about. 24/7 gives
> you an unbroken archive of the whole broadcast for
> compliance and catch-up. Many stations run both.

---

## 2. How it works

A second Liquidsoap `output.file` block taps the same internal
audio bus that feeds the public Icecast outputs, and rotates to
a new file at each clock-hour boundary:

```liquidsoap
output.file(
  id="recording_hourly",
  reopen_when=rec247_reopen,   # true when the wall-clock hour changes
  fallible=true,
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="192k")),
  {rec247_path()},             # <folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.mp3
  bus,
)
```

The block is rendered into the running Liquidsoap script
**only when you enable the feature** in Settings; otherwise it
is a no-op comment and the live stream is untouched.

> **Requires the Liquidsoap engine.** Like per-show recording,
> 24/7 recording is provided by Liquidsoap's `output.file`. If
> `RASTATIME_PLAYOUT_ENGINE` is `mpv` or `vlc`, no 24/7
> recording happens (the stream plays normally).

---

## 3. Enabling 24/7 Recording

**Settings → Local Machine → "24/7 Recording Folder"** (the
section directly above "Show Recording Folder"):

| Field | Meaning |
|---|---|
| **Enable** | Master on/off. A folder is required when enabled. |
| **Folder path** | Absolute path on this machine — created automatically on save if it does not exist. Inside or outside the project tree (e.g. `C:\rastatime\recordings-247` or `D:\rec247`). Keep it **separate** from the Show Recording Folder. |
| **Format** | MP3 / AAC / OGG (Vorbis) / Opus. Default **MP3**. |
| **Bitrate** | 96–320 kbps. Default **192** (archive-grade-enough, ~half the disk of 320). |
| **Delete after (days)** | Automatic cleanup window. `0` = keep forever. |

Click **Save**, then **restart the playout service** to apply
(see [§5](#5-applying-changes)). The status line reminds you.

> **How it works under the hood.** Save stores the cc_pref keys
> `local_247_recording_{enabled,folder,format,bitrate,retention_days}`.
> At playout startup these are read and rendered into
> `rastatime.liq`; the cleanup daemon and the cue writer read
> them too.

---

## 4. Where the recordings live

```
   <folder>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.<ext>
   <folder>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.cues.json
```

Example (folder `C:\rastatime\recordings-247`, MP3):

```
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.mp3
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.cues.json
```

Times are the **studio computer's local wall-clock**, so the
filename matches what was on air. Files rotate on the hour;
the transition is seamless (no audible gap between hours).

### 4.1 Cue sidecars

Next to each hour's audio file sits a JSON **cue sidecar** that
marks what happened during that hour, so a future catch-up
player can seek straight to a show or track:

```json
{
  "version": 1,
  "recording": "2026-06-05 14-00.mp3",
  "hour_start": "2026-06-05T14:00:00",
  "marks": [
    {"t": 0.0,   "kind": "show",  "event": "start", "name": "Afternoon Drive"},
    {"t": 0.0,   "kind": "track", "event": "start", "show": "Afternoon Drive",
                 "title": "Song A", "artist": "Artist A"},
    {"t": 183.4, "kind": "track", "event": "end"},
    {"t": 600.0, "kind": "webstream", "event": "start", "show": "News"}
  ]
}
```

`t` is the offset **in seconds from the top of the hour**.
`kind` is `track` / `show` / `webstream` / `linein`; `event` is
`start` / `end`. Show boundaries are derived from a change of
show, so they cover every show with content. A track that
spans the top of the hour has its `start` in the previous
hour's sidecar and its `end` in the new one.

---

## 5. Applying changes

The 24/7 settings are read when the playout starts and baked
into the Liquidsoap script. After you Save a change (enable,
folder, format, bitrate), **restart the playout service** so
it re-renders the script:

- Restart the **RASTATIME-PLAYOUT** Windows service (it
  re-renders `rastatime.liq` and restarts
  **RASTATIME-LIQUIDSOAP**).
- Pick a low-listener moment — the restart causes a brief
  (~5 s) stream reconnect.

The **Delete after (days)** value is the exception: the cleanup
daemon re-reads it every cycle, so changing only the retention
window takes effect within the hour without a restart.

> **Rollback.** Untick **Enable**, Save, and restart — the
> recorder block is no longer rendered and the stream behaves
> exactly as before. Already-recorded files stay on disk.

---

## 6. Automatic cleanup (retention)

When **Delete after (days)** is greater than 0, a daemon inside
the playout service prunes whole per-day folders once they are
that many days old. It runs about once an hour.

It only ever touches `YYYY-MM-DD`-named day folders **inside the
24/7 folder** — your Show Recording Folder and any other files
are never affected. `0` disables cleanup (keep forever).

---

## 7. Antivirus exclusion is REQUIRED

> ⚠️ Same caveat as [Record-per-Show §3.5](./RECORD_PER_SHOW.md#35-antivirus-exclusion-is-required)
> — and it matters even more here, because the 24/7 recorder
> writes **continuously**.

Real-time antivirus (Bitdefender, Windows Defender, …) scans
every write to the growing file and can lock the encoder long
enough to drop audio. **Add the 24/7 folder to your antivirus's
exclusion list** before enabling the recorder.

If an hour file comes out short while everything else is fine,
the usual causes are antivirus scanning or the machine being
overloaded (Liquidsoap "latency catch-up" under heavy CPU/disk
load can drop recording audio). The first file after you enable
the recorder is always a partial hour — that is expected.

---

## 8. Disk planning

24/7 recording never stops, so size the disk for the full day
× the retention window:

| Bitrate | 1 hour | 1 day | 1 week |
|---|---|---|---|
| 128 kbps | ~58 MB | ~1.4 GB | ~9.5 GB |
| 192 kbps *(default)* | ~86 MB | ~2.1 GB | ~14 GB |
| 320 kbps | ~145 MB | ~3.4 GB | ~24 GB |

With **Delete after (days)** set, the footprint is bounded:
roughly `1-day size × retention days`. The cue sidecars are
tiny (a few KB per hour).

---

## 9. Frequently asked

### "Why is the first file shorter than an hour?"

The recorder starts when you enable it + restart, which is
usually mid-hour, so the first file covers only the rest of
that hour. Every subsequent file is a full clock hour.

### "One hour came out a few minutes short — bug?"

Almost always external load, not the recorder: an antivirus
scan (see [§7](#7-antivirus-exclusion-is-required)) or the
machine being overloaded so Liquidsoap drops audio during
latency catch-up. A 1–3 second mismatch is normal MP3 frame
alignment.

### "Can I record 24/7 and per-show at the same time?"

Yes. They are independent `output.file` taps on the same bus,
writing to separate folders. Both run together with no extra
coordination.

### "Does it capture live DJ / webstream / line-in?"

Yes — it taps the on-air bus, so whatever the listeners hear is
recorded, regardless of source. (Cue marks for a live DJ
harbor take-over are a known v1 gap — the audio is still
recorded, the live segment just may not get its own cue mark.)

### "Can I change the format / bitrate later?"

Yes — change it in Settings and restart the playout service.
Existing files keep their original format; new hours use the
new setting.

---

## Where to go next

* [Record-per-Show](./RECORD_PER_SHOW.md) — the per-show
  companion recorder.
* [Settings → Local Machine](./LOCAL_MACHINE.md) — where you
  configure both recorders.
* [Streams](./STREAMS.md) — the on-air output that both
  recorders tap.
* [`docs/operator/BACKUP.md`](../operator/BACKUP.md) —
  retention / off-machine-copy policy.
