<#
.SYNOPSIS
    Register (or re-register) the scheduled task RASTATIME-PhpCgiReaper.

.DESCRIPTION
    RASTATIME 2026-10-22.  NSSM 2.24 has no event hooks (AppEvents came with
    the 2.24-101 pre-releases), so rt-php-cgi-reaper.ps1 is started by the
    Task Scheduler instead: an event trigger on the Application log entries
    NSSM writes for RASTATIME-APACHE -
      1040  "received START/STOP control"  (service stop, start, restart)
      1008  "Started httpd.exe"            (also after NSSM restarts a crashed Apache)
    The reaper waits until the service has left the *Pending state and then
    stops only php-cgi.exe processes without a live httpd parent.  Several
    events in a row queue up (one restart = STOP, START, Started).
    No <ValueQueries> (e.g. passing Data[2] = START/STOP to the script): with
    them the trigger never fired on this machine (tested 2026-10-22); the
    logged service state (Stopped / Running) tells the events apart anyway.

    Run once in an elevated PowerShell:
      powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\register-php-cgi-reaper.ps1
    Remove:
      Unregister-ScheduledTask -TaskName RASTATIME-PhpCgiReaper -Confirm:$false
    -ShowXml prints the task definition without registering anything.
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'RASTATIME-PhpCgiReaper',
    [string] $ServiceName = 'RASTATIME-APACHE',
    [string] $Script = 'C:\RASTATIME\infra\scripts\rt-php-cgi-reaper.ps1',
    [switch] $ShowXml
)
$ErrorActionPreference = 'Stop'

# The subscription is XML inside XML: escape it once for the task definition.
$query = "<QueryList><Query Id=`"0`" Path=`"Application`"><Select Path=`"Application`">" +
    "*[System[Provider[@Name='nssm'] and (EventID=1040 or EventID=1008)]] and *[EventData[Data='$ServiceName']]" +
    "</Select></Query></QueryList>"
$subscription = [Security.SecurityElement]::Escape($query)

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>RASTATIME</Author>
    <Description>Stops php-cgi.exe left behind by a stopped or restarted $ServiceName (NSSM 2.24 does not reach them). Triggered by the NSSM events 1040/1008 of the service. See infra\scripts\rt-php-cgi-reaper.ps1.</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>$subscription</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>Queue</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
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
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -ExecutionPolicy Bypass -File "$Script" -ServiceName $ServiceName -Trigger event</Arguments>
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
Write-Output ("{0}: {1}, runs as {2}" -f $t.TaskName, $t.State, $t.Principal.UserId)
# One manual run as a check: with Apache running it only logs "orphans=0".
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5
Get-Content 'C:\RASTATIME\logs\php-cgi-reaper.log' -Tail 1
