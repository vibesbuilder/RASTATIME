<#
.SYNOPSIS
    Register (or re-register) the scheduled task RASTATIME-RecordingCopy.

.DESCRIPTION
    RASTATIME 2026-11-14.  The task runs scripts\recording-copy.ps1 every two
    minutes: it copies finished show recordings to the folder set under
    Settings -> Local Machine -> Show Recording -> "Copy finished recordings
    to".  That folder is usually on a network drive, which the SYSTEM account
    of the other RASTATIME tasks cannot reach - so this task runs under a
    user account that may write there, whether that user is logged on or not.

    Windows asks for the account's password once and keeps it itself
    (Task Scheduler credential store); RASTATIME never sees or stores it.
    After a password change, run this script again.

    Run in an elevated PowerShell:

      powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\register-recording-copy.ps1 -User <account>

    Remove:

      Unregister-ScheduledTask -TaskName RASTATIME-RecordingCopy -Confirm:$false

    -ShowXml prints the task definition without registering anything.

    The trigger carries no UTC offset (wall-clock time), so the daylight
    saving change does not move it; a two-minute repetition would not care
    either way.
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'RASTATIME-RecordingCopy',
    [string] $User = $env:USERNAME,
    [string] $Script = 'C:\RASTATIME\scripts\recording-copy.ps1',
    [int] $EveryMinutes = 2,
    [switch] $ShowXml
)
$ErrorActionPreference = 'Stop'

if ($User -notmatch '\\') { $User = "$env:COMPUTERNAME\$User" }
$userXml = [Security.SecurityElement]::Escape($User)
$scriptXml = [Security.SecurityElement]::Escape($Script)

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>RASTATIME</Author>
    <Description>Copies finished show recordings to the folder set under Settings - Local Machine - Show Recording (once each, never deletes at the target). Runs as a user account because SYSTEM cannot reach the network share.</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT${EveryMinutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <BootTrigger>
      <Repetition>
        <Interval>PT${EveryMinutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <Enabled>true</Enabled>
      <Delay>PT2M</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$userXml</UserId>
      <LogonType>Password</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$scriptXml"</Arguments>
    </Exec>
  </Actions>
</Task>
"@
if ($ShowXml) { Write-Output $xml; return }

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run this in an elevated PowerShell (Run as administrator).'
}

# Windows asks for the password here; it goes straight to the Task Scheduler.
$credential = Get-Credential -UserName $User -Message "Password of $User for the task $TaskName (kept by Windows, not by RASTATIME)"
if ($null -eq $credential) { Write-Error 'No password entered - nothing registered.' }

Register-ScheduledTask -TaskName $TaskName -Xml $xml -User $User -Password $credential.GetNetworkCredential().Password -Force | Out-Null
$t = Get-ScheduledTask -TaskName $TaskName
Write-Output ("{0}: {1}, runs as {2} every {3} min" -f $t.TaskName, $t.State, $t.Principal.UserId, $EveryMinutes)

# One run as a check.  With the setting empty it does nothing; otherwise the
# status line under Settings -> Local Machine -> Show Recording shows the result.
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 15
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Output ("last run: {0}, result 0x{1:X} (0 = fine, 0x41301 = still running)" -f $info.LastRunTime, $info.LastTaskResult)
if (Test-Path 'C:\RASTATIME\logs\recording-copy.log') { Get-Content 'C:\RASTATIME\logs\recording-copy.log' -Tail 3 }
