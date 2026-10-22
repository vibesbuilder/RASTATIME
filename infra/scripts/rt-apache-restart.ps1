<#
.SYNOPSIS
    RASTATIME: stop / start / restart RASTATIME-APACHE safely.

.DESCRIPTION
    RASTATIME 2026-10-22 (BACKLOG "Apache-Stopp dauert 30 s", option D).
    A `nssm start` while the service is still stopping fails with "Es wird
    bereits eine Instanz des Dienstes ausgeführt" and Apache then stays down
    (2026-10-22 09:27).  This script never starts before the service is
    really Stopped, and checks the result:

      1. `httpd -t` - with a broken config nothing is stopped (exit 2).
      2. Stop and WAIT until the service is Stopped (-StopTimeoutSeconds).
      3. php-cgi.exe left without a live httpd parent: reported, and stopped
         by rt-php-cgi-reaper.ps1 (the RASTATIME-PhpCgiReaper task does the
         same on the NSSM events; running it here makes the result visible).
      4. Start and WAIT until Running (-StartTimeoutSeconds).
      5. GET https://<RT_PUBLIC_HOST>/login via 127.0.0.1 until it answers
         200 (-HealthTimeoutSeconds).

    -StopOnly runs 1-3 (e.g. to swap the PHP folder), -StartOnly runs 4-5.
    Needs an elevated PowerShell.  One summary line per run goes to
    C:\RASTATIME\logs\apache-restart.log.  Exit 0 = OK, 1 = failed, 2 = config
    test failed (nothing stopped).

      powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\rt-apache-restart.ps1
#>
[CmdletBinding()]
param(
    [switch] $StopOnly,
    [switch] $StartOnly,
    [string] $ServiceName = 'RASTATIME-APACHE',
    [string] $ApacheRoot = 'C:\Tools\Apache24',
    [string] $PhpDir = 'C:\Tools\PHP',
    [int] $StopTimeoutSeconds = 90,
    [int] $StartTimeoutSeconds = 60,
    [int] $HealthTimeoutSeconds = 30
)
$ErrorActionPreference = 'Stop'
$log = 'C:\RASTATIME\logs\apache-restart.log'
$started = Get-Date
$mode = if ($StopOnly) { 'stop' } elseif ($StartOnly) { 'start' } else { 'restart' }
$notes = New-Object System.Collections.Generic.List[string]

function Say([string] $msg) { Write-Host ("{0:HH:mm:ss} {1}" -f (Get-Date), $msg) }
function Finish([int] $code, [string] $result) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} mode={1} result={2} took={3:N1}s {4}" -f $started, $mode, $result, ((Get-Date) - $started).TotalSeconds, ($notes -join '; ')
    try { Add-Content -Path $log -Value $line.TrimEnd() } catch { }
    Say "$result ($mode)"
    exit $code
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Run this in an elevated PowerShell (Run as administrator).'
    exit 1
}
$svc = Get-Service -Name $ServiceName   # a ServiceController: Refresh / Stop / Start / WaitForStatus

if (-not $StartOnly) {
    # 1. Config test.  httpd prints "Syntax OK" on stderr, so go through cmd
    # (see apache-cert-renewed.ps1).
    $httpd = Join-Path $ApacheRoot 'bin\httpd.exe'
    $test = cmd.exe /c "`"$httpd`" -t 2>&1"
    if ($LASTEXITCODE -ne 0) {
        $test | ForEach-Object { Write-Host "  $_" }
        $notes.Add('httpd -t failed')
        Finish 2 'CONFIG-ERROR'
    }
    Say 'httpd -t: Syntax OK'

    # 2. Stop and wait.
    $svc.Refresh()
    if ($svc.Status -ne 'Stopped') {
        if ($svc.Status -ne 'StopPending') { Say "stopping $ServiceName ..."; $svc.Stop() }
        try {
            $svc.WaitForStatus('Stopped', [TimeSpan]::FromSeconds($StopTimeoutSeconds))
        } catch {
            $svc.Refresh()
            $notes.Add("still $($svc.Status) after ${StopTimeoutSeconds}s")
            Finish 1 'STOP-TIMEOUT'
        }
    }
    $notes.Add(("stopped after {0:N1}s" -f ((Get-Date) - $started).TotalSeconds))
    Say $notes[$notes.Count - 1]

    # 3. Orphaned php-cgi.exe.
    Start-Sleep -Seconds 1
    $reaper = Join-Path $PSScriptRoot 'rt-php-cgi-reaper.ps1'
    $reaped = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reaper -ServiceName $ServiceName -PhpDir $PhpDir -WaitSeconds 0 -Trigger 'rt-apache-restart'
    $notes.Add("reaper: $reaped")
    Say "reaper: $reaped"
    if ($StopOnly) { Finish 0 'OK' }
}

# 4. Start and wait.
$svc.Refresh()
if ($svc.Status -eq 'StopPending') {
    try { $svc.WaitForStatus('Stopped', [TimeSpan]::FromSeconds($StopTimeoutSeconds)) } catch { $notes.Add('never reached Stopped'); Finish 1 'STOP-TIMEOUT' }
    $svc.Refresh()
}
if ($svc.Status -ne 'Running') {
    if ($svc.Status -ne 'StartPending') { Say "starting $ServiceName ..."; $svc.Start() }
    try {
        $svc.WaitForStatus('Running', [TimeSpan]::FromSeconds($StartTimeoutSeconds))
    } catch {
        $svc.Refresh()
        $notes.Add("still $($svc.Status) after ${StartTimeoutSeconds}s")
        Finish 1 'START-TIMEOUT'
    }
}
Say "$ServiceName is Running"

# 5. Health check through the public host name, resolved to this machine.
$publicHost = $null
$httpsConf = 'C:\RASTATIME\infra\apache\rastatime-https.conf'
if (Test-Path $httpsConf) {
    $m = Select-String -Path $httpsConf -Pattern '^\s*Define\s+RT_PUBLIC_HOST\s+(\S+)' | Select-Object -First 1
    if ($m) { $publicHost = $m.Matches[0].Groups[1].Value }
}
$url = if ($publicHost) { "https://$publicHost/login" } else { 'http://127.0.0.1/login' }
$resolve = if ($publicHost) { @('--resolve', "${publicHost}:443:127.0.0.1") } else { @() }
$deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
$code = '000'
while ((Get-Date) -lt $deadline) {
    $code = & curl.exe -s -o NUL -m 5 -w '%{http_code}' @resolve $url
    if ($code -eq '200') { break }
    Start-Sleep -Seconds 1
}
$notes.Add("login $code")
if ($code -ne '200') { Finish 1 'HEALTH-FAILED' }
Say "login: $code"
Finish 0 'OK'
