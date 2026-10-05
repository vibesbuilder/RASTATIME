# WINDOWS_24_7.md — Windows Hardening for Unattended 24/7 Operation

**Status:** Accepted (operator decision 2026-10-03, BACKLOG item 17a)
**Date:** 2026-10-03
**Applies to:** the production machine (Windows 11 Pro 10.0.26200, static
192.168.1.64), services installed per `INSTALL.md`

---

## 1. Goal

RASTATIME runs permanently on this machine.  Windows must therefore

1. **never restart on its own** (no update reboots, no sleep, no
   hibernation),
2. **never install updates on its own** — updates are installed by the
   operator, in a maintenance window after the 03:30 backup,
3. **sign a user in automatically** after every boot, so the desktop
   audio endpoints (Tascam / MME feeders) and the desktop tools come up
   without anyone at the keyboard.  (The RASTATIME services themselves
   start as services and do not need a sign-in.)

Every step below changes a system or security setting and is therefore
done **by the operator in an elevated PowerShell** ("Run as
administrator").  Section 6 is the read-only verification assistant can run
afterwards.

## 2. State before (2026-10-03, read-only check)

| Setting | Found |
|---|---|
| Windows Update policy (`HKLM\...\Policies\...\WindowsUpdate\AU`) | none — Windows may download, install and reboot on its own |
| "Get the latest updates as soon as they're available" | not set |
| Automatic sign-in (`AutoAdminLogon`) | 0 (off), `DefaultUserName = studio` |
| "Require Windows Hello sign-in" (`DevicePasswordLessBuildVersion`) | 2 (on — hides the netplwiz checkbox) |
| Fast startup (`HiberbootEnabled`) | 0 (off) — good |
| Power scheme | High performance; sleep **never**, hibernate **never** — good |
| Display off | after 15 min (AC) |
| USB selective suspend | default (on) |
| Hibernation file | present (`powercfg /a`: Ruhezustand available) |
| Local accounts | `admin`, `studio` (enabled) |

## 3. Windows Update: notify only, never reboot

Run in an **elevated** PowerShell.  The policy keys are honoured by
Windows 11 Pro (no domain needed); afterwards Settings → Windows Update
shows "Some settings are managed by your organization".

```powershell
$au = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
$wu = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
New-Item -Path $au -Force | Out-Null
# 2 = notify before download and before install: nothing is downloaded
#     or installed until the operator clicks it
Set-ItemProperty -Path $au -Name AUOptions -Type DWord -Value 2
Set-ItemProperty -Path $au -Name NoAutoUpdate -Type DWord -Value 0
# never reboot while a user is signed in (with auto sign-in that is always)
Set-ItemProperty -Path $au -Name NoAutoRebootWithLoggedOnUsers -Type DWord -Value 1
Set-ItemProperty -Path $au -Name AlwaysAutoRebootAtScheduledTime -Type DWord -Value 0
# keep Windows Update away from the audio drivers (Tascam / ASIO / MME)
Set-ItemProperty -Path $wu -Name ExcludeWUDriversInQualityUpdate -Type DWord -Value 1
# no "get the latest updates as soon as they're available"
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings' -Name IsContinuousInnovationOptedIn -Type DWord -Value 0 -ErrorAction SilentlyContinue
gpupdate /force
```

Then in **Settings → Windows Update → Advanced options**: set the active
hours to the broadcast day (e.g. 06:00–22:00 — a belt-and-braces measure,
the policy above already blocks the reboot) and leave "Notify me when a
restart is required" on.

**Installing updates from now on:** Settings → Windows Update → *Check
for updates* → *Download* → *Install*, then restart the machine in the
maintenance window (after the 03:30 backup, outside the programme; see
`RESTART_ORDER.md` for the service order on the way back up).

## 4. Automatic sign-in

Use Sysinternals **Autologon**: it stores the password as an LSA secret
(encrypted), not as clear text in the registry, and sets
`AutoAdminLogon` for you.

1. Download `Autologon64.exe` from
   <https://learn.microsoft.com/sysinternals/downloads/autologon>
   (or `https://live.sysinternals.com/Autologon64.exe`) to
   `C:\Tools\Autologon64.exe`.
2. Allow the setting to take effect — "Require Windows Hello sign-in"
   hides the classic option (elevated PowerShell):

   ```powershell
   Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device' -Name DevicePasswordLessBuildVersion -Type DWord -Value 0
   ```
3. Run `C:\Tools\Autologon64.exe` (as administrator), fill in
   *Username* `studio`, *Domain* `.` (the machine name), the account's
   password, click **Enable**.  Type the password into the tool's
   window only — never on a command line (it would land in the shell
   history).  The tool does not accept a sign-in without a password; if
   `studio` has none, set one first (`Ctrl+Alt+Del → Change a password`).
4. Optional, for a studio where the screen is reachable by others: lock
   the desktop right after the automatic sign-in.  The user session,
   its audio endpoints and the tools keep running behind the lock screen.
   Task Scheduler → *Create Task* → trigger *At log on* of `studio`,
   action `rundll32.exe user32.dll,LockWorkStation`.

To undo: run Autologon64.exe again and click **Disable** (clears the
secret and `AutoAdminLogon`).

## 5. Power and hardware

Elevated PowerShell:

```powershell
# no hibernation file at all (no hybrid states, no "wake into a half-booted machine")
powercfg /h off
# the Tascam is a USB device: never let Windows power-manage the port
powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
powercfg /setdcvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
# PCI Express link state power management off
powercfg /setacvalueindex SCHEME_CURRENT 501a4d13-42af-4429-9fd1-a8218c268e20 ee12f906-d277-404b-b6da-e5fa1a576df5 0
# sleep / hibernate idle stay "never" (already 0); display off is the operator's call:
#   powercfg /change monitor-timeout-ac 0      -> never off
#   powercfg /change monitor-timeout-ac 15     -> current value
powercfg /setactive SCHEME_CURRENT
```

Display-off note: on 2026-09-06/07 a sleeping display made the DELL
HD-Audio endpoint disappear and shifted the PortAudio indexes; since
2026-09-07 the Tascam is addressed **by name** (see
`DEVICE_MISSING.md`), so a dark monitor is harmless again.  Leaving the
display timeout at 15 min is fine; set it to 0 only if an endpoint
problem shows up again.

**BIOS / UEFI** (operator, at the machine): *AC Power Recovery / After
Power Loss* = **Power On**; *Wake on LAN* as wished; boot order = the
Windows disk first; no USB boot ahead of it (a forgotten stick must not
block a boot).

## 6. Verification (read-only, assistant can run it)

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' | Select-Object AUOptions, NoAutoUpdate, NoAutoRebootWithLoggedOnUsers, AlwaysAutoRebootAtScheduledTime
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' | Select-Object ExcludeWUDriversInQualityUpdate
$wl = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'; "AutoAdminLogon=$($wl.AutoAdminLogon) user=$($wl.DefaultUserName)"
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device').DevicePasswordLessBuildVersion
powercfg /a
```

Expected: `AUOptions 2`, `NoAutoUpdate 0`, `NoAutoRebootWithLoggedOnUsers
1`, `AlwaysAutoRebootAtScheduledTime 0`, `ExcludeWUDriversInQualityUpdate
1`, `AutoAdminLogon=1 user=studio`, `DevicePasswordLessBuildVersion 0`,
`powercfg /a` lists hibernation as unavailable.

## 7. Acceptance: one test restart in a quiet window

1. Pick a slot without a show (or between two file shows, after the
   03:30 backup).  Note the time.
2. `Restart-Computer` (elevated) — or Start → Power → Restart.
3. Do **not** touch the keyboard.  Expected within ~2 minutes:
   - the desktop of `studio` appears (locked if §4 step 4 was set up),
   - all ten services are *Running* (`Get-Service RASTATIME-*,
     postgresql-x64-17, RabbitMQ`),
   - the Tascam output and the Line-In feeders are back
     (`http://192.168.1.64/systemstatus`, Settings → Local Machine),
   - the stream is audible on Icecast and the master panel shows the
     right show.
4. assistant checks the playout log for the boot (`Playout started`, device
   re-enumeration, first PLAY) and the Icecast access log for the
   reconnect.

If a service is missing after the boot: `RESTART_ORDER.md` §5.

## 8. Rollback

```powershell
Remove-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Recurse -Force
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device' -Name DevicePasswordLessBuildVersion -Type DWord -Value 2
powercfg /h on
```

plus Autologon64.exe → **Disable**.
