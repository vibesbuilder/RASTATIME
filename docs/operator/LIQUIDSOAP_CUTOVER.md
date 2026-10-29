# Liquidsoap Cutover — switching the playout engine permanently

> **Note (2026-08-27).** Historical runbook from the 2026-05 cutover.
> Recording paths have since moved: `C:\Users\studio\Music\Show Recordings`
> (per-show), `Permanent Recordings` (24/7), `Import` (inbox) — the
> `Music\Recording` folder named below is no longer used
> (Record-per-Hour, 2026-06-06).
>
> **Audience.** Operators who set up RASTATIME and decide whether the
> station runs on the legacy mpv engine (default) or the Liquidsoap
> engine (production-recommended since 2026-05-28, Phase-C5).
>
> **What this document is.** A step-by-step recipe for the cutover
> from "default install (mpv)" to "Liquidsoap is the production
> playout engine".  Covers env-var, NSSM service, antivirus
> exclusion, smoke test, rollback.
>
> **What this document is NOT.** Architectural reasoning (see
> ARCHITECTURE §23.13.bis), nor a feature comparison from a
> programme-director perspective (see the User-Manual
> [Playout Engine](../manual/SETTINGS.md) section).

---

## TL;DR — five commands

If you know what you're doing, here it is:

```powershell
# 1) Antivirus exclusion FIRST (otherwise long recordings lose audio)
#    See Bitdefender / Defender steps in docs/manual/RECORD_PER_SHOW.md §3.5

# 2) Install + start the Liquidsoap NSSM service (one-time)
& "C:\rastatime\.venv\Scripts\python.exe" `
    "C:\RASTATIME\backend\playout\config\nssm-install-liquidsoap.ps1"

# 3) Set the env-var on the RASTATIME-PLAYOUT NSSM service
$nssm = "C:\Tools\nssm\nssm.exe"
$lines = @(& $nssm get RASTATIME-PLAYOUT AppEnvironmentExtra |
    Where-Object { $_ -and ($_ -notmatch '^RASTATIME_PLAYOUT_ENGINE=') })
$lines += "RASTATIME_PLAYOUT_ENGINE=liquidsoap"
& $nssm set RASTATIME-PLAYOUT AppEnvironmentExtra $lines

# 4) Restart Pypo (renders rastatime.liq), then Liquidsoap (loads it)
Restart-Service RASTATIME-PLAYOUT
Start-Sleep -Seconds 5
Restart-Service RASTATIME-LIQUIDSOAP

# 5) Smoke-test
& "C:\rastatime\.venv\Scripts\python.exe" -c "from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient; c=LiquidsoapTelnetClient(); print('uptime:', c.send_command('uptime'))"
```

Read the rest if any step fails, or if this is a fresh install.

---

## 1. Before you start — preconditions

### 1.1 Hardware sanity
- RASTATIME stack already running on mpv (legacy default) and
  serving audio to listeners.  This cutover changes the engine, not
  the schedule or content — your shows keep airing throughout.

### 1.2 Bitdefender / Antivirus exclusion (MANDATORY)
- Add the recording folder to your AV's exception list **before**
  the first show recording on the Liquidsoap engine.  Otherwise long
  shows (>30 min) lose audio due to real-time scan-lock on the
  growing .mp3.
- See [`docs/manual/RECORD_PER_SHOW.md` §3.5](../manual/RECORD_PER_SHOW.md)
  for the GUI steps for Bitdefender and Windows Defender.

### 1.3 Liquidsoap 2.4.4 Windows build
- The savonet Liquidsoap 2.4.4 zip must be unpacked at
  `C:\Tools\liquidsoap\` (or wherever you configured —
  `nssm-install-liquidsoap.ps1` knows the path).
- The `liquidsoap.exe` must run standalone:
  ```powershell
  & "C:\Tools\liquidsoap\liquidsoap.exe" --version
  ```
  should print `Liquidsoap 2.4.4`.

### 1.4 NSSM tool
- `nssm.exe` somewhere on disk (we use `C:\Tools\nssm\nssm.exe` in
  examples).  The Pypo NSSM-service must already be installed (it
  is, if RASTATIME was set up with the standard `INSTALL.md`
  procedure).

### 1.5 Recording folder
- Operator-configurable in **Settings → Local Machine → Recording
  Folder**.  Default in test deployments is
  `C:\Users\<user>\Music\Recording\` (NOT `C:\rastatime\recordings\`).
- Whatever path you pick must be in the AV exception list (see 1.2).

---

## 2. Install the Liquidsoap NSSM service

The Liquidsoap subprocess is managed as its own NSSM service
(`RASTATIME-LIQUIDSOAP`), independent of `RASTATIME-PLAYOUT` (Pypo).
This separation means a Liquidsoap restart doesn't drag Pypo down
and vice versa.

```powershell
& "C:\rastatime\.venv\Scripts\python.exe" `
    "C:\RASTATIME\backend\playout\config\nssm-install-liquidsoap.ps1"
```

This script:
- Creates / updates the `RASTATIME-LIQUIDSOAP` NSSM service
- Sets the working directory and stdout/stderr log destinations
- Configures the service for auto-start at boot
- Sets a 5-second restart delay on crash (NSSM `AppRestartDelay`)

Verify:

```powershell
Get-Service RASTATIME-LIQUIDSOAP | Format-List Name, Status, StartType
```

Expected:
```
Name      : RASTATIME-LIQUIDSOAP
Status    : Running
StartType : Automatic
```

---

## 3. Set the Pypo env-var for Liquidsoap mode

```powershell
$nssm = "C:\Tools\nssm\nssm.exe"

# Read existing env-vars (preserves other entries like RASTATIME_MPV_LOG_LEVEL)
$existing = & $nssm get RASTATIME-PLAYOUT AppEnvironmentExtra

# Remove any prior RASTATIME_PLAYOUT_ENGINE= line, add the new one
$lines = @($existing | Where-Object {
    $_ -and ($_ -notmatch '^RASTATIME_PLAYOUT_ENGINE=')
})
$lines += "RASTATIME_PLAYOUT_ENGINE=liquidsoap"
& $nssm set RASTATIME-PLAYOUT AppEnvironmentExtra $lines

# Verify
& $nssm get RASTATIME-PLAYOUT AppEnvironmentExtra
```

Expected output should include the line:
```
RASTATIME_PLAYOUT_ENGINE=liquidsoap
```

If the `nssm set` command's multi-line argument is fiddly in your
PowerShell session, the GUI alternative is:

```powershell
& $nssm edit RASTATIME-PLAYOUT
# → "Environment" tab → add: RASTATIME_PLAYOUT_ENGINE=liquidsoap → OK
```

---

## 4. Restart sequence

**Order matters:** Pypo first (renders `rastatime.liq` from the
template + cc_pref stream-outputs), then Liquidsoap (loads the
new .liq file).

```powershell
Restart-Service RASTATIME-PLAYOUT
Start-Sleep -Seconds 5    # give Pypo time to write rastatime.liq
Restart-Service RASTATIME-LIQUIDSOAP
```

You may see PowerShell `WARNUNG: Warten auf Start des Diensts …`
messages repeated 4-8 times for each service — that's just NSSM
taking time to bring the process up; not an error.

Verify both are running:

```powershell
Get-Service RASTATIME-PLAYOUT, RASTATIME-LIQUIDSOAP |
    Format-Table Name, Status, StartType -AutoSize
```

---

## 5. Verify Pypo loaded the Liquidsoap engine

```powershell
# Latest playout log (filename pattern depends on NSSM config)
Get-Content C:\rastatime\logs\playout-stdout.log -Tail 30 |
    Select-String -Pattern "Local-playback engine|streaming handled externally|FfmpegRecorder|recording.stop"
```

Expected (key lines, in order):

```
INFO __main__: Local-playback engine: Liquidsoap (Phase-C2+C3+C6 fully wired). Telnet target 127.0.0.1:1234.
INFO rastatime_playout.playout_scheduler: PlayoutScheduler: streaming handled externally — FFmpeg streamers SKIPPED (N cc_pref output(s) delegated to the Liquidsoap subprocess).
INFO rastatime_playout.playout_scheduler: PlayoutScheduler: streaming handled externally — recording is owned by Liquidsoap output.file from the internal bus (FfmpegRecorder was deleted in C5).
INFO rastatime_playout.engine.liquidsoap_engine: Liquidsoap recording_stop: closed current recording
INFO rastatime_playout.playout_scheduler: PlayoutScheduler: initial recording.stop sent to Liquidsoap (silences sentinel-file write from boot until first scheduled show).
```

**If you see `Local-playback engine: mpv (libmpv) [DEPRECATED]` instead**,
the env-var didn't take effect.  Most common cause: the `nssm set`
command in step 3 didn't persist because of multi-line argument
encoding.  Re-run step 3 (try the GUI variant) and restart again.

**If you see a `DeprecationWarning`** for `mpv` or `vlc`, that's
expected on the legacy engines — see the
[Deprecated section](../../CHANGELOG.md) of the CHANGELOG.

---

## 6. Smoke-test the telnet interface

```powershell
& "C:\rastatime\.venv\Scripts\python.exe" -c @"
from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
c = LiquidsoapTelnetClient()
print('uptime :', c.send_command('uptime'))
print('status :', c.recording_status())
print('path   :', c.send_command('var.get recording_path'))
"@
```

Expected:

```
uptime : 0d 00h XX m XXs
status : off
path   : C:/rastatime/recordings/_uninitialized.mp3
```

- `uptime` should be > 0 (= Liquidsoap is up).
- `status` should be `off` (= Pypo's init-stop took effect; the
  sentinel-file isn't growing).
- `path` is the default sentinel; will be overwritten when the next
  scheduled record=true show starts.

If `status` is `on` and `path` is the sentinel: Liquidsoap was
restarted after Pypo, so Pypo's init-stop hit the wrong instance.
Solve by sending a manual stop:

```powershell
& "C:\rastatime\.venv\Scripts\python.exe" -c "from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient; c=LiquidsoapTelnetClient(); print(c.recording_stop())"
```

---

## 7. End-to-end smoke test (recommended)

Schedule a small test show with **Record this show** ticked, in the
next 5-10 minutes, for 5 minutes duration.  Pick a smart-block or a
couple of file tracks as content.

After the show ends:

```powershell
$today = Get-Date -Format "yyyy-MM-dd"

# Recording file present?
Get-ChildItem "C:\Users\studio\Music\Recording\$today\" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3 |
    Format-Table Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime

# Duration matches?
$ffp = (Get-Command ffprobe.exe -EA SilentlyContinue).Source
$newest = Get-ChildItem "C:\Users\studio\Music\Recording\$today\" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $ffp -v error -show_entries format=duration -of csv=p=0 "$($newest.FullName)"
```

For a 5-minute (300 s) show:
- File size: ~12 MB (320 kbps × 300 s = 12 MB ± 5 %)
- Duration: 295-305 s

If duration is significantly less (e.g. 250 s) → **antivirus
exclusion is missing**.  Re-check 1.2.

Pypo-log for the show-record events:

```powershell
Select-String -Path C:\rastatime\logs\playout-stdout.log -Pattern "show-record" |
    Select-Object -Last 6
```

Expected: one `PLAY (show-record start, Liquidsoap)` line at show
start, one `STOP (show-record end, Liquidsoap)` line at show end,
plus `Liquidsoap recording_start` / `recording_stop` confirmation
lines.

---

## 8. Listen-in on the public stream

While the test show is on air, open the Icecast mountpoint in
your browser or VLC:

```
http://localhost:8000/rastatime
```

You should hear continuous audio with native Liquidsoap crossfades
between tracks (~2 s, configurable via
`RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS` env-var).  No clicks at
track boundaries, no 1-2 s tail-cut on short tracks, no
listener-reconnect when the track changes — these were the
mpv-stack pain points that Phase-C migration fixed.

---

## 9. Rollback (if you need to go back to mpv)

> **Obsolete since 2026-09-10:** the mpv engine was deleted from the
> code base (BACKLOG "Legacy-mpv-Code-Delete"); there is nothing to
> roll back to.  Kept for the history of the cutover — "fix forward"
> is the only path.

If something goes wrong and you need the legacy mpv path back:

```powershell
$nssm = "C:\Tools\nssm\nssm.exe"
$lines = @(& $nssm get RASTATIME-PLAYOUT AppEnvironmentExtra |
    Where-Object { $_ -and ($_ -notmatch '^RASTATIME_PLAYOUT_ENGINE=') })
& $nssm set RASTATIME-PLAYOUT AppEnvironmentExtra $lines

Restart-Service RASTATIME-PLAYOUT
# RASTATIME-LIQUIDSOAP can keep running idle, or you can stop it:
Stop-Service RASTATIME-LIQUIDSOAP
```

**What you lose by rolling back:**
- Recording — the legacy FfmpegRecorder code was deleted in C5
  Teil 2d (2026-05-28).  `cc_show.record = TRUE` shows will log a
  warning and silently skip the recording in mpv mode.  Restoring
  recording on mpv requires checking out the pre-C5-Teil-2d commit
  (`git log --oneline --grep "FfmpegRecorder"`).
- DJ-source switching via Liquidsoap `input.harbor` — DJ clients
  on ports 8001/8002 won't be received.  Master/Show DJ would need
  to point back at the Icecast `/source` endpoint, which the
  Liquidsoap-mode pre-Phase-C4 setup also handled differently.
- Gapless transitions, persistent Icecast PUTs, native crossfades
  — the things you switched to Liquidsoap for.

For most reasons-to-rollback, "fix forward" (debug the Liquidsoap
issue) is the better option.  Rollback is an emergency lever, not
a regular operation.

---

## 10. What about Webstreams and Line-Inputs?

> **Not yet migrated to Liquidsoap.** Schedule items of type
> `WEB_STREAM` (Icecast/Shoutcast HTTP relay) and `LINEIN` (Tascam
> / USB sound card / Windows-dshow microphone) still use the
> legacy mpv playback path even when
> `RASTATIME_PLAYOUT_ENGINE=liquidsoap` is set.  Pypo runs both
> engines side-by-side: Liquidsoap for file tracks + DJ-sources,
> mpv for webstreams + line-inputs.

This is intentional for now (operator-decision 2026-05-28).
Webstream + Line-Input migration to Liquidsoap is tracked as
Phase-E and Phase-F in `BACKLOG.md` — they will replace the mpv
playback path entirely once landed.

**Side-effect today:** recording of a show whose airtime is
entirely a webstream or line-input is silent / 0-bytes, because
the Liquidsoap recording taps the internal bus and webstreams
don't currently route through that bus.  Documented as a known
limitation in
[`docs/manual/RECORD_PER_SHOW.md`](../manual/RECORD_PER_SHOW.md)
§6 "What recordings include".

---

## 11. Status of related operator docs

| Doc | Purpose | Still current? |
|---|---|---|
| `LIQUIDSOAP_PHASE0.md` | Operator-sanity-test that Liquidsoap-Windows-build runs | Historical reference (Phase-0 done) |
| `LIQUIDSOAP_PHASE_A.md` | POC burn-in instructions (sine generator) | Historical (Phase-A done) |
| `LIQUIDSOAP_PHASE_C4_DJ_CUTOVER.md` | DJ-source migration (input.harbor) | Current — still applies |
| `LIQUIDSOAP_PHASE_C8.md` | Phase-C8 reality-test recipe | Historical |
| `LIQUIDSOAP_PHASE_C_BURNIN.md` | Burn-In test recipe | Current, useful for re-validation after large config changes |
| `LIQUIDSOAP_CUTOVER.md` (this doc) | **Permanent cutover to Liquidsoap engine** | Current |

The Phase-A / Phase-C8 docs stay in the repo as historical
reference; if you've cutover and are happy, you don't need to
re-read them.

---

## 12. Where to go next

- `docs/manual/RECORD_PER_SHOW.md` — per-show recording semantics
  + the mandatory antivirus exclusion (Section 3.5).
- `docs/manual/SETTINGS.md` — "Playout Engine" section, briefly
  describing what each engine is and why we picked Liquidsoap.
- `BACKLOG.md` — Phase-E (Webstreams → Liquidsoap) and Phase-F
  (Line-Inputs → Liquidsoap) for the path forward.
- `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` §23.13.bis — technical
  decision record for the recording-pipeline migration.
- `CHANGELOG.md` — the `[Unreleased]` section's `Deprecated` and
  `Changed` entries for 2026-05-28.
