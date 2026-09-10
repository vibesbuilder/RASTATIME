# LINE_IN_BROKEN.md — Line-In Audio Source Not Working

**Status:** Accepted  
**Task:** T23.3  
**Date:** 2026-04-30  
**Applies to:** RASTATIME-PLAYOUT; line-in input device configuration

---

## 1. Symptom

A line-in source is configured in RASTATIME (Settings → Line-In) but one
or more of the following problems occur:

| Symptom | Likely cause |
|---|---|
| Silence when line-in source is active | Device not connected / disabled; wrong channel mapping |
| "Device not found" in the UI | `stable_id` no longer matches an active capture endpoint |
| Distorted or phase-inverted audio | Wrong channel mapping indices |
| Line-in source shows as active but no playback history is written | `LineInEventMapper` not wired to the playout loop |
| RASTATIME-PLAYOUT log shows `DeviceUnavailableError` | Input device physically absent or driver reset |

---

## 2. Background: Line-In Architecture

A **line-in source** in RASTATIME is a Django `LineIn` model object with:

- `name` — human-readable label (e.g. `"Drum Kit"`, `"Live DJ"`)
- `device_id` — the **stable_id** of the Windows audio capture endpoint  
  (normalised GUID: lowercase, no braces, e.g. `b3f20d11-9c13-4a6f-8e21-cc97432e7a04`)
- `channel_mapping` — comma-separated **0-based** channel indices  
  (e.g. `"0,1"` for stereo left+right; `"2,3"` for the third and fourth channels on a multi-channel interface)
- `priority` — routing priority when multiple line-ins are active simultaneously
- `enabled` — boolean; disabled sources are ignored by the playout loop

The playout engine activates a line-in source by calling
`LineInEventMapper.on_linein_started(linein_id, name, device_id)`, which
begins tracking playback history.  Deactivation calls `on_linein_stopped`.

Line-in events are stored in `PlaybackEvent` with `source_type="linein"`
and `uri="linein://<device_id>"`.

Capture endpoints are enumerated from:
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture\{GUID}
```

Only endpoints with `DeviceState == DEVICE_STATE_ACTIVE (0x00000001)` are
returned by `WindowsAudioDeviceManager.list_inputs()`.

---

## 3. Diagnosis

### Step 1 — Check service and API health

```powershell
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\status.ps1
```

### Step 2 — Read the playout log

```powershell
Get-Content C:\rastatime\logs\playout-stderr.log -Tail 50
Get-Content C:\rastatime\logs\playout-stdout.log -Tail 30
```

Look for:
- `DeviceUnavailableError: Audio device '<stable_id>' is not available`
  → the capture device is physically absent (see §4 Path A or B)
- `on_linein_started called for ... but it is already active`
  → duplicate activation; the playout loop has a logic error (see §6)
- Absence of `LineInEventMapper: started line-in` log entry
  → the line-in source was never activated (check `enabled` flag in UI)

### Step 3 — List active capture (input) devices

```powershell
# Option A: PowerShell PnP
Get-PnpDevice -Class AudioEndpoint | Where-Object Status -eq 'OK' |
    Select-Object FriendlyName, Status, DeviceID

# Option B: Windows registry — matches what RASTATIME reads
$path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
Get-ChildItem $path | ForEach-Object {
    $state = (Get-ItemProperty $_.PSPath).DeviceState
    if ($state -eq 1) {
        $props = Join-Path $_.PSPath "Properties"
        $name  = (Get-ItemProperty $props -ErrorAction SilentlyContinue)."{a45c254e-df1c-4efd-8020-67d146a850e0},2"
        [PSCustomObject]@{
            GUID         = $_.PSChildName
            FriendlyName = $name
            State        = "Active"
        }
    }
} | Format-Table -AutoSize
```

### Step 4 — Check Windows Recording devices

1. Right-click the speaker icon → **Sounds** → **Recording** tab
2. Verify the expected device is listed and **not disabled**
3. Right-click the device → **Properties** → **Levels** tab
   - Ensure the input level is not muted or set to 0
4. Speak/play audio into the interface — the level meter must respond

### Step 5 — Verify the line-in configuration in RASTATIME

Open the RASTATIME web UI → **Settings → Line-In**.  For the affected source:

- **Device:** should show the device name (not "Device not found")
- **Channel Mapping:** check the indices are correct (see §5)
- **Enabled:** must be checked/true for the source to activate
- **Priority:** ensure no higher-priority source is blocking this one

To inspect the raw configuration via the REST API:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/v2/linein/ | Format-List
# Each entry shows: id, name, device_id, channel_mapping, priority, enabled
```

---

## 4. Recovery Paths

### Path A — Device physically absent: reconnect

1. Reconnect the audio interface cable (check USB / TRS / XLR connections)
2. Verify the device appears in Windows Recording devices (Step 4)
3. Restart RASTATIME-PLAYOUT:
   ```powershell
   nssm restart RASTATIME-PLAYOUT
   ```
4. Activate the line-in source in the RASTATIME scheduler or UI
5. Confirm the playout log shows:
   ```
   LineInEventMapper: started line-in 'Drum Kit' ...
   ```

### Path B — Device replaced: reassign to new stable_id

1. In the RASTATIME web UI → **Settings → Line-In**, click **Edit** for the source
2. In the **Input Device** dropdown, select the replacement device
3. Adjust **Channel Mapping** if the new device has a different channel layout (see §5)
4. Click **Save**
5. Restart RASTATIME-PLAYOUT:
   ```powershell
   nssm restart RASTATIME-PLAYOUT
   ```

To reassign via the REST API (headless):

```powershell
# List available input devices:
Invoke-RestMethod http://127.0.0.1:8765/api/v2/soundcard/devices/inputs/ |
    Select-Object stable_id, name, channels | Format-Table

# Patch the line-in source (replace <linein-uuid> and <new-stable-id>):
$body = @{
    device_id       = "<new-stable-id>"
    channel_mapping = "0,1"
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8765/api/v2/linein/<linein-uuid>/ `
    -Method Patch -ContentType "application/json" -Body $body
```

### Path C — Device present but disabled in Windows

1. Right-click the speaker icon → **Sounds** → **Recording** tab
2. Right-click the device → **Enable**
3. Restart RASTATIME-PLAYOUT:
   ```powershell
   nssm restart RASTATIME-PLAYOUT
   ```

### Path D — Source is enabled in the DB but not activating

Check the `enabled` flag and that the playout loop is calling the activate
signal.  Temporarily enable debug logging in the playout service:

> **⚠ `nssm set … AppEnvironmentExtra` REPLACES the whole environment
> block.**  Setting only the three variables below would silently drop
> `RASTATIME_PLAYOUT_ENGINE=liquidsoap`, `PYTHONPATH`, the FFmpeg
> `PATH` and `RASTATIME_API_URL` — the playout would not find its
> modules or the API on restart.  Always read the current block first and
> re-set it in full, with `RASTATIME_LOG_LEVEL=DEBUG` appended:

```powershell
# 1. Show the current block — copy every line from the output:
nssm get RASTATIME-PLAYOUT AppEnvironmentExtra

# 2. Re-set the FULL block (all lines from step 1) plus the override:
nssm set RASTATIME-PLAYOUT AppEnvironmentExtra `
    "DJANGO_SETTINGS_MODULE=libretime_api.settings.prod" `
    "LIBRETIME_CONFIG_FILEPATH=C:\rastatime\config\libretime.conf" `
    "RASTATIME_API_URL=http://127.0.0.1:8765" `
    "PYTHONPATH=C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime" `
    "PATH=C:\ffmpeg\bin;%PATH%" `
    "RASTATIME_MPV_LOG_LEVEL=warn" `
    "RASTATIME_PLAYOUT_ENGINE=liquidsoap" `
    "RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=1.0" `
    "RASTATIME_LOG_LEVEL=DEBUG"
nssm restart RASTATIME-PLAYOUT

Get-Content C:\rastatime\logs\playout-stdout.log -Tail 100 |
    Select-String "linein"
```

Remove `RASTATIME_LOG_LEVEL=DEBUG` again afterwards (same procedure —
re-set the block without that line).

---

## 5. Channel Mapping Reference

Channel mapping is stored as a comma-separated string of **0-based** integer
indices that select which physical channels to read from the device.

| Configuration | Meaning | Use case |
|---|---|---|
| `"0,1"` | Channels 0 and 1 (left + right) | Standard stereo input |
| `"0"` | Channel 0 only (mono left) | Mono microphone on left channel |
| `"2,3"` | Channels 2 and 3 | Inputs 3 and 4 on a multi-channel interface |
| `"0,1,2,3"` | All four channels of a quad interface | Multi-channel live feed |

**Common mistakes:**

| Mistake | Symptom | Fix |
|---|---|---|
| `"1,2"` instead of `"0,1"` | Silence (channel 1 is index 0) | Change to `"0,1"` |
| `"0"` on a stereo-only source | Mono audio (no right channel) | Change to `"0,1"` |
| Indices exceed device channel count | Silence or error | Check device channels in device list |
| Wrong device selected | Audio from wrong source | Reassign device in Settings → Line-In |

To check how many channels a capture device has:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/v2/soundcard/devices/inputs/ |
    Select-Object stable_id, name, channels
# The 'channels' field shows the physical channel count of the device
```

---

## 6. Multiple Line-In Sources

RASTATIME supports multiple simultaneous line-in sources (one per
`LineIn` DB record).  `WindowsAudioDeviceManager.open_input` allows
multiple inputs to be open simultaneously.

If two sources share the same device but different channel mappings,
only the first activation will call `open_input` for that device; the
second will reuse the already-open handle.

**Priority** determines which source is preferred when two sources are
assigned to the same time slot.  Ensure priorities are unique to avoid
ambiguous routing.

---

## 7. Preventing Recurrence

| Measure | Detail |
|---|---|
| Label physical ports | Match cable labels to `LineIn.name` in the DB |
| Use dedicated channels | Avoid sharing channels between line-in sources |
| Set `priority` explicitly | Prevents unexpected routing changes |
| Keep `enabled = false` for unused sources | Reduces false-positive activations |
| Run `status.ps1` before broadcasts | Confirms RASTATIME-PLAYOUT is healthy |
| Weekly device list audit | Compare active capture GUIDs against stored `device_id` values |

---

## 8. Related Documentation

| Document | Description |
|---|---|
| `docs\operator\DEVICE_MISSING.md` | Output / soundcard device missing runbook |
| `docs\operator\RESTART_ORDER.md` | Service restart sequence (T22.4) |
| `docs\operator\CRASH_RECOVERY.md` | Broader crash and recovery procedures |
| `infra\nssm\status.ps1` | Live service and health status (T22.3) |
| `playout\now_playing\linein_mapper.py` | `LineInEventMapper` — activation / deactivation logic |
| `audio\soundcard\windows_manager.py` | `WindowsAudioDeviceManager` — capture endpoint enumeration |
| `audio\soundcard\settings_model.py` | `SoundcardSettings.line_in_device_ids` field definition |
