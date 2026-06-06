# Record-per-Show

> **Where you are in the manual.** This is a per-show toggle
> on the show-edit form (see [Calendar](./CALENDAR.md) §2.3).
> The feature replaces the upstream "Record from Line In?"
> checkbox with a broader "record everything that goes on air
> during the show" capture. Section 23.13 in ARCHITECTURE
> covers the technical decisions.

**Record-per-Show** writes a file of everything that went on
air during a show — the music, the live mic, the webstream
relay, all of it — for archive, replay, podcast, or
compliance use.

The recording is a parallel **output-tap**: it does not change
anything about how the show is scheduled or played. The
recorder simply listens to the public Icecast output and
writes it to a file for the duration of the show.

---

## 1. Why it works this way

### What the upstream did

The upstream LibreTime "Record from Line In?" feature
recorded *only* the line-in source (one specific physical
input), using Liquidsoap. The recording started when the
show began and stopped when it ended; the recorded content
was always exactly the line-in audio.

This was useful for "a host with a mic in the studio" but
broken for everything else:

- A show that switched between tracks and a mic only
  captured the mic portion.
- A show that played pre-recorded segments did not record
  them.
- A show with no line-in source could not be recorded at all.

### What RASTATIME does

The new model records the **full on-air output** — whatever
the listeners hear during the show, regardless of source.

> **Architecture update — Phase-C5 (2026-05-28).**  The
> recording pipeline migrated from a separate FFmpeg-Icecast-
> tap subprocess to a Liquidsoap `output.file` block tapping
> the internal audio bus directly.  Both architectures
> deliver the same operator-visible behaviour (per-show
> recording into a folder); the bus-tap is just simpler,
> more reliable, and uses higher-quality fixed 320 kbps MP3.
> See ARCHITECTURE §23.13.bis for the technical detail.

The implementation is a Liquidsoap `output.file(id="recording")`
block in the long-running Liquidsoap subprocess.  It taps
the same internal audio bus that feeds the public Icecast
outputs and encodes it to MP3 at a fixed 320 kbps:

```liquidsoap
output.file(
  id="recording",
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="320k")),
  {recording_path()},
  fallible=true,
  bus,
)
```

Pypo's per-show start/stop hooks drive the lifecycle over
the Liquidsoap telnet interface:

```
recording.stop
var.set recording_path = C:/.../<YYYY-MM-DD HH-MM> - <show>.mp3
recording.start
```

This gives:

| Property | Value |
|---|---|
| **CPU cost** | ~3 % of one core on Intel i3-1315U (one libmp3lame encoder) |
| **Quality** | Fixed 320 kbps MP3 — archive-grade, identical to the main Icecast stream |
| **Source switches** | Picked up automatically (recording taps the same internal bus as the live stream) |
| **Failure isolation** | `fallible=true` on `output.file` lets a single output failure (disk full, AV-scan-lock) not propagate up the source graph |

> **Operator setting that previously controlled the recording
> bitrate** (`PlayoutConfig.record_bitrate`, defaulted to 256
> kbps) is now ignored.  All recordings are MP3 @ 320 kbps —
> archive-grade quality, fixed by operator decision 2026-05-27.

> **Recording requires the Liquidsoap engine.**  Phase-C5
> Teil 2d deleted the legacy FfmpegRecorder code path that
> previously handled recording for the mpv/VLC engine modes.
> If `RASTATIME_PLAYOUT_ENGINE` is set to `mpv` or `vlc`,
> show-record-start events are logged but no recording happens
> (the show plays normally, only the recording is missing).

---

## 2. Enabling Record-per-Show

Per show, on the show-edit form. Two ways to reach it:

### 2.1 On a new show

Calendar → New Show → expand **Record** section → tick
**Record this show:** → Save.

### 2.2 On an existing show

Calendar → click the show → **Edit Show** → expand **Record**
section → tick **Record this show:** → Save.

The toggle takes effect from the *next* instance to start.
A show that has already started does not retroactively
record (the FFmpeg subprocess only starts when the show
begins).

> **Operator tip.** Many stations record every show by
> default. The fastest way to set this up across the whole
> station: tick **Record this show:** on a template, save
> as a Show Template named "Recorded Show" or similar, then
> apply that template to every show. See
> [Show Templates](./SHOW_TEMPLATES.md).

> **How it works under the hood.** The toggle sets
> `cc_show.record = TRUE`. At show start, the playout
> engine's schedule builder emits a `SHOW_RECORD_START`
> event with the show's id + name + start time. The
> handler in `backend/playout/libretime_playout/playout_scheduler.py`
> sends a `recording.start` command to the Liquidsoap
> telnet, which opens the per-show .mp3 file. At show end,
> the engine emits `SHOW_RECORD_END` and the handler sends
> `recording.stop` to close the file cleanly. See
> ARCHITECTURE §23.13 (original FFmpeg design) and
> §23.13.bis (Phase-C5 Liquidsoap migration).

---

## 3. Where the recording lives

By default, recordings are written to:

```
   C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Example:

```
   C:\rastatime\recordings\1234-2026-05-21_14-00-00.mp3
```

The directory and the filename pattern are configured in
`config\libretime.conf` under the `[recording]` section:

```ini
[recording]
output_dir = C:\rastatime\recordings
filename_template = {show_id}-{starts_at:%Y-%m-%d_%H-%M-%S}.mp3
```

Available placeholders: `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

> **Operator tip.** Keep the show_id at the start of the
> filename. The OS sorts by filename, so show_id-first means
> the recordings stay in chronological order even when sorted
> alphabetically.

---

## 3.5 Antivirus exclusion is REQUIRED

> ⚠️ **Important — applies to every studio computer running
> RASTATIME.**

Real-time antivirus software (Bitdefender, Windows Defender,
Kaspersky, McAfee, ESET, …) scans every file write — including
the growing .mp3 file being recorded.  For long shows (>30 min),
the scan-lock-per-write cost accumulates to the point where
Liquidsoap's audio pipeline drops frames trying to keep up.

Reality-test 2026-05-28: a 60-min show without antivirus
exclusion recorded only 52 min 53 s of audio (~88 % of the
scheduled duration); the same recording-pipeline with the
folder excluded from the antivirus reproducibly hit 100 %.

**Mitigation: add the recording folder to your antivirus's
exception list.**

- **Bitdefender** (most common on RASTATIME deployments):
  Bitdefender GUI → **Protection** → **Antivirus** →
  **Settings** → **Manage Exceptions** → add the recording
  folder path (e.g. `C:\Users\studio\Music\Recording\` or
  whatever you configured in Settings → Local Machine →
  Show Recording Folder).
- **Windows Defender**: Settings → **Update & Security** →
  **Windows Security** → **Virus & threat protection** →
  **Manage settings** → **Add or remove exclusions** → add
  the recording folder.
- **Other AVs**: consult their documentation; the option is
  usually called "Exclusion", "Exception", or "Whitelist".

After adding the exception, no restart is needed; the next
show recording will run at full quality.

> **Operator tip.** Add the exception during initial RASTATIME
> setup BEFORE the first show records.  Otherwise you may
> have a few hours of short recordings before you notice the
> issue.

---

## 4. Finding and downloading a recording

### From the calendar

Click the show → **View Recorded File** in the context menu.
Only appears after the recording finished writing (typically
a few seconds after show end).

The dialog shows:

| Field | Value |
|---|---|
| **Filename** | `1234-2026-05-21_14-00-00.mp3` |
| **Size** | `144.5 MB` |
| **Duration** | `01:00:00` |
| **Bitrate** | `320 kbps` |
| **Download** | Direct download link |

### From the file system

Browse `C:\rastatime\recordings\` directly. The directory is
not exposed via the web UI for security; only the per-show
"View Recorded File" dialog gives access through the UI.

> **How it works under the hood.** The dialog calls
> `/api/v2/recordings/<show-instance-id>` which returns the
> file metadata (probed via ffprobe). The download is served
> via the storage endpoint with a streaming response.

---

## 5. Archive size planning

Recordings accumulate. Plan disk capacity accordingly.

Approximate size for a 1-hour recording at typical bitrates:

| Stream bitrate | 1-hour size |
|---|---|
| 96 kbps MP3 | ~43 MB |
| 128 kbps MP3 | ~58 MB |
| 192 kbps MP3 | ~86 MB |
| 256 kbps MP3 | ~115 MB |
| 320 kbps MP3 | ~145 MB |

A station running 24/7 at 192 kbps with all shows recorded
fills about **2 GB per day** or **730 GB per year**.

Recordings are not auto-deleted. To rotate them, set up a
scheduled task on the operator machine:

```powershell
# Delete recordings older than 90 days (PowerShell)
Get-ChildItem "C:\rastatime\recordings\" -File |
   Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
   Remove-Item
```

See [`docs/operator/BACKUP.md`](../operator/BACKUP.md) for
the recording-retention policy template.

---

## 6. What recordings include

The recorder captures **whatever the Icecast mountpoint is
broadcasting** during the show:

| Source | Included? |
|---|---|
| Scheduled tracks | Yes |
| Webstreams | Yes |
| Line-ins | Yes |
| Show DJ (live remote source) | Yes |
| Master DJ (station-wide live source) | Yes |
| Auto-DJ fallback | Yes (if it kicked in) |
| Silence (the fallback when nothing is scheduled) | Yes (as actual silence in the file) |

The recording also includes any operator-side mistakes —
"silent gap because I forgot to schedule track 3" appears as
silent gap in the recording. The recorder makes no
judgement; it records what was on air.

### What recordings do NOT include

- **Pre-fader audio** from the studio. Only the post-Icecast
  audio is captured.
- **Multiple stream variants.** If you have a 192 kbps main
  stream and a 96 kbps mobile stream, only the **first
  configured** stream is recorded (typically the main).
- **Output stream metadata** (ICY title updates). The MP3
  file has its own ID3 tags written by FFmpeg, not the live
  ICY metadata.

---

## 7. Using recordings as podcasts / catchup

A common follow-on workflow:

1. Recordings written to `C:\rastatime\recordings\`.
2. A scheduled task copies them to a web-accessible directory
   (e.g. nginx public root).
3. An RSS feed generator (separate tool) produces a podcast
   feed pointing at the copied files.
4. Listeners subscribe to the feed.

RASTATIME does not ship a built-in RSS generator for
recordings (podcasts in the library are **inbound**
subscriptions, not outbound). The
[`docs/operator/UPGRADE.md`](../operator/UPGRADE.md) backlog
mentions a planned `outbound-podcast` feature; not yet
implemented.

---

## 8. Compliance recording

Some jurisdictions require broadcast stations to keep a
broadcast log for N days. Record-per-Show with every show
recorded + a per-day archive copy is sufficient for most
regulations, but:

- Verify the **bitrate** is acceptable to your regulator
  (some require lossless or near-lossless).
- Set up **off-machine storage** for resilience to disk
  failure.
- Document the **chain of custody** — who has access to the
  archive, who can delete files, etc.

> **Operator tip.** If your regulator requires lossless
> archival, the Record-per-Show output (which is `-c copy`
> of the lossy Icecast stream) is not enough. The
> alternative is the internal-bus encoder route, which is
> not in RASTATIME currently. Talk to your regulator about
> accepting the lossy archive as a working compromise; many
> do, given the de-facto industry practice.

---

## 9. Disabling Record-per-Show

Edit the show → expand **Record** section → untick **Record
this show:** → Save.

Effects:

- Already-recorded instances are unaffected (the files
  remain on disk).
- Future instances do not start the FFmpeg subprocess.
- The **View Recorded File** menu item disappears for
  future shows.

---

## 10. Frequently-asked

### "Why does the recording start a few seconds before the show?"

The FFmpeg subprocess takes ~1-2 seconds to spin up and
attach to the Icecast stream. To avoid clipping the very
first second of the show, the recorder launches ~3 seconds
*before* `starts_at`. The recorded file includes those
pre-show seconds (typically the tail of the previous show
or fallback).

To remove the pre-show pad post-hoc, trim the file with
ffmpeg:

```
ffmpeg -ss 00:00:03 -i input.mp3 -c copy output.mp3
```

### "Why is the recording silent?"

If the whole recording is silent, the recorder attached to
the stream but the stream itself was silent during the
show. Verify the stream's audio by listening at
`http://<host>:8000/rastatime` during a live show.

If only parts are silent, those are gaps in the schedule
(no item playing) that were recorded as-is.

### "Can I record only part of a show?"

No. The toggle is per-show; the recorder runs for the full
show duration or not at all. To get partial recording, edit
the show definition to split it into two shorter shows and
toggle recording on only one.

### "Can two simultaneously-airing shows on different outputs both record?"

RASTATIME's schedule model is single-show: at most one show
is on air at any moment, on all of the configured output
streams in parallel.  The recording taps the internal
Liquidsoap bus (which is the same audio source that feeds
all the Icecast outputs), so "different shows on different
outputs" isn't an architecturally-supported case.

### "Does Record-per-Show capture the Live DJ source?"

Yes. As long as the Live DJ source is on air (audible on
the public stream), it is captured. The recording does not
distinguish source — it is whatever the Icecast mountpoint
broadcasts.

### "Why is the recording's file size larger than the show duration × bitrate?"

The MP3 frame structure has a few bytes of overhead per
frame. For a 320 kbps 1-hour file the actual size is
typically 144-145 MB rather than the math-only 144 MB.

### "Why is a long recording shorter than the scheduled show duration?"

Almost certainly your antivirus is scanning the growing .mp3
file and blocking the Liquidsoap encoder long enough to drop
frames.  See [Section 3.5](#35-antivirus-exclusion-is-required)
— adding the recording folder to your antivirus's exception
list fixes this.

A small residual mismatch (1–3 seconds in a 1-hour show) is
normal and comes from MP3 frame boundary alignment.

### "Can I record at a different bitrate than the stream?"

Not via the UI. The recording bitrate is fixed at MP3 @
320 kbps (operator decision Phase-C5, 2026-05-27 — archive-
grade quality regardless of what the public Icecast streams
are configured to). The recording is a separate Liquidsoap
`output.file` block with its own libmp3lame encoder, so the
recording bitrate is independent of the public-stream bitrate.

To change it, edit `backend/playout/config/rastatime.liq.template`
and replace `b="320k"` in the recording block with your
desired bitrate; then restart RASTATIME-PLAYOUT (re-renders
the .liq) and RASTATIME-LIQUIDSOAP (loads the new template).

---

## Where to go next

* [Streams](./STREAMS.md) — the output stream that
  Record-per-Show taps.
* [Calendar](./CALENDAR.md) — where you enable / disable
  per show.
* [Show Templates](./SHOW_TEMPLATES.md) — stamp recording on
  every new show via a template.
* [`docs/operator/BACKUP.md`](../operator/BACKUP.md) —
  recording-retention policy template.
