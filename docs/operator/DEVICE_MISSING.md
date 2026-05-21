# DEVICE_MISSING.md — Audio Output Device Not Found

**Status:** Accepted  
**Task:** T23.3  
**Date:** 2026-04-30  
**Applies to:** RASTATIME-PLAYOUT; soundcard output and preview output devices

---

## 1. Symptom

RASTATIME-PLAYOUT starts but produces no audio, and the playout log
contains one of these messages:

```
DeviceUnavailableError: Audio device '<stable_id>' is not available
Audio output opened: <stable_id>   ← absent (never logged)
OSError: CDLL libvlc.dll ...        ← different issue — see INSTALL.md §5.3
```

In the RASTATIME web UI (Settings → Soundcard), the configured main output
or preview output shows as **"Device not found"** (`deviceMissing` i18n key).

**Effect:** Playout engine falls back to the OS default output device (if
configured to do so) or produces silence.  The playout scheduling loop
continues — only audio output is interrupted.

---

## 2. Background: Stable IDs

RASTATIME identifies audio devices by a **stable_id** — a normalised
Windows audio endpoint GUID stored in the `rastatime_soundcard_settings`
database table.

Example stable_id: `9ab29437-d4ec-473d-9a94-1ad46a86e9ff`

The stable_id is derived from the Windows MMDevice registry key:

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\{GUID}
```

A stable_id remains constant across reboots and minor driver updates.  It
changes if:

- The physical device is **removed and a different device** takes its slot
- The device driver is **fully reinstalled** and the GUID is regenerated
- A USB audio interface is plugged into a **different USB port** on some
  hardware/driver combinations

When the stored stable_id no longer matches any active
(`DEVICE_STATE_ACTIVE`) endpoint, `WindowsAudioDeviceManager.lookup_by_stable_id`
returns `None` and `DeviceUnavailableError` is raised.

---

## 3. Diagnosis

### Step 1 — Confirm the service and health state

```powershell
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\status.ps1
```

Look for RASTATIME-PLAYOUT status.  If it is `Stopped`, read the log:

```powershell
Get-Content C:\rastatime\logs\playout-stderr.log -Tail 50
Get-Content C:\rastatime\logs\playout-stdout.log -Tail 30
```

Confirm the exact stable_id that is missing from the log output.

### Step 2 — List active output devices on the system

```powershell
# Option A: PowerShell (no admin required)
Get-PnpDevice -Class AudioEndpoint | Where-Object Status -eq 'OK' |
    Select-Object FriendlyName, Status, DeviceID

# Option B: Windows registry (matches what RASTATIME reads internally)
$path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
Get-ChildItem $path | ForEach-Object {
    $state = (Get-ItemProperty $_.PSPath).DeviceState
    if ($state -eq 1) {   # DEVICE_STATE_ACTIVE = 0x00000001
        $props = Join-Path $_.PSPath "Properties"
        $name  = (Get-ItemProperty $props -ErrorAction SilentlyContinue)."
{a45c254e-df1c-4efd-8020-67d146a850e0},2"
        [PSCustomObject]@{
            GUID         = $_.PSChildName
            FriendlyName = $name
            State        = "Active"
        }
    }
} | Format-Table -AutoSize
```

Compare the listed GUIDs (normalised: lowercase, strip `{}`) with the
stable_id in the error log.  If the stored ID is absent, the device is
physically missing or disabled.

### Step 3 — Check Windows Sound settings

1. Right-click the speaker icon in the system tray → **Sounds**
2. Select the **Playback** tab
3. Verify that the expected device is listed and **not disabled**

If the device appears as greyed out or labelled "Disconnected":
- Reconnect the USB/audio cable
- Right-click the device → **Enable**

---

## 4. Recovery Paths

### Path A — Reconnect the original device (same hardware)

1. Reconnect the audio interface or cable
2. Verify it appears in Windows Playback devices (Step 3 above)
3. Restart RASTATIME-PLAYOUT:
   ```powershell
   nssm restart RASTATIME-PLAYOUT
   ```
4. Verify audio resumes:
   ```powershell
   Get-Content C:\rastatime\logs\playout-stdout.log -Tail 10
   # Expected: "Audio output opened: <stable_id>"
   ```

### Path B — Reassign to a replacement device (different hardware)

Use this when the original device is permanently unavailable.

1. Open the RASTATIME web UI → **Settings → Soundcard**
2. In the **Main Output** dropdown, select the replacement device
3. Click **Save**
4. Restart RASTATIME-PLAYOUT:
   ```powershell
   nssm restart RASTATIME-PLAYOUT
   ```

The soundcard settings page reads live device data from
`WindowsAudioDeviceManager.list_outputs()` so only currently active
devices appear in the dropdown.

> **Note:** After saving, the new stable_id is written to the singleton
> `rastatime_soundcard_settings` row in PostgreSQL.  The playout service
> reads this row on startup.

### Path C — Reassign via the API (headless / scripted)

```powershell
# List available output devices via the REST API:
Invoke-RestMethod http://127.0.0.1:8000/api/v2/soundcard/devices/outputs/ |
    Select-Object stable_id, name, channels | Format-Table

# Update the main output (replace <new-stable-id> with the chosen device):
$body = @{ main_output_id = "<new-stable-id>" } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/v2/soundcard/settings/ `
    -Method Patch -ContentType "application/json" -Body $body
```

### Path D — Fall back to OS default

If no specific device is required and the OS default is acceptable:

1. Open Settings → Soundcard in the web UI
2. Select **"(OS default)"** from the Main Output dropdown
3. Click **Save**
4. Restart RASTATIME-PLAYOUT

The playout engine will use whatever Windows designates as the default
playback device at startup.

---

## 5. Preview / Monitor Output Device Missing

The preview output (`preview_output_id`) follows the same recovery paths.
A missing preview output does **not** interrupt on-air audio — it only
affects the DJ monitor/cue mix.

The web UI shows **"Device not found"** in the Preview Output section.
Follow Path A or B above, selecting the replacement in the
**Preview / Monitor Output** dropdown instead of Main Output.

---

## 6. Preventing Recurrence

| Measure | Detail |
|---|---|
| Use a **dedicated USB port** | USB audio endpoints may get a new GUID if moved to a different hub or port |
| Label the port | Physical label on the machine identifying which port the audio interface must use |
| Use **PCI / integrated audio** | Card-based endpoints have more stable GUIDs than USB |
| Keep a device list | Run the registry query (§3 Step 2) and save the output as a reference |
| Schedule a weekly `status.ps1` check | Catches silent device disconnections before a broadcast |

---

## 7. Related Documentation

| Document | Description |
|---|---|
| `docs\operator\LINE_IN_BROKEN.md` | Input / line-in device missing runbook |
| `docs\operator\RESTART_ORDER.md` | Service restart sequence (T22.4) |
| `docs\operator\CRASH_RECOVERY.md` | Broader crash recovery procedures |
| `infra\nssm\status.ps1` | Live service and health status (T22.3) |
| `audio\soundcard\windows_manager.py` | `WindowsAudioDeviceManager` source — device enumeration logic |
| `audio\soundcard\settings_model.py` | `SoundcardSettings` domain model — `stable_id` field definition |
