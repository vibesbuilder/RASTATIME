<#
.SYNOPSIS
    Register (or re-register) the scheduled task RASTATIME-AudioFeatures.

.DESCRIPTION
    RASTATIME 2026-11-14 (ARCHITECTURE 23.115).  The task runs
    scripts\audio-features.ps1 every ten minutes: it measures energy and
    brightness of library tracks that have none yet (new uploads; after
    legacy migration 0085 once the whole library).  The library is local,
    so the task runs as SYSTEM like the other RASTATIME tasks, below normal
    priority.  Import and playout do not depend on it: when the task is off,
    new tracks simply get no values.

    Register after legacy migration 0085, in an elevated PowerShell:

      powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\register-audio-features.ps1

    Remove:

      Unregister-ScheduledTask -TaskName RASTATIME-AudioFeatures -Confirm:$false

    -ShowXml prints the task definition without registering anything.

    The trigger carries no UTC offset (wall-clock time), so the daylight
    saving change does not move it.
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'RASTATIME-AudioFeatures',
    [string] $Script = 'C:\RASTATIME\scripts\audio-features.ps1',
    [int] $EveryMinutes = 10,
    [switch] $ShowXml
)
$ErrorActionPreference = 'Stop'

$scriptXml = [Security.SecurityElement]::Escape($Script)

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>RASTATIME</Author>
    <Description>Measures energy and brightness of library tracks that have none yet (ffmpeg, below normal priority). Values set by hand in Edit Track stay. See scripts\audio-features.ps1.</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT${EveryMinutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:05:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
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
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
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

Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
$t = Get-ScheduledTask -TaskName $TaskName
Write-Output ("{0}: {1}, runs as {2} every {3} min" -f $t.TaskName, $t.State, $t.Principal.UserId, $EveryMinutes)

# One run as a check: it measures what is waiting (or nothing) and logs a
# summary line to logs\audio-features.log when it did something.
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 20
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Output ("last run: {0}, result 0x{1:X} (0 = fine, 0x41301 = still running)" -f $info.LastRunTime, $info.LastTaskResult)
if (Test-Path 'C:\RASTATIME\logs\audio-features.log') { Get-Content 'C:\RASTATIME\logs\audio-features.log' -Tail 3 }
