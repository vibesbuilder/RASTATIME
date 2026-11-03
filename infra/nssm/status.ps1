#Requires -Version 5.1
<#
.SYNOPSIS
    Show the live status and health of all RASTATIME Windows services.

.DESCRIPTION
    T22.3 - Status and health helper for the RASTATIME service stack.

    For each of the eight RASTATIME NSSM services (API, WORKER, PLAYOUT,
    ANALYZER, APACHE, ICECAST, LIQUIDSOAP, STANDBY) this script reports:
        * Windows SCM status (Running / Stopped / not installed)
        * PID, start time and uptime of the service process and - for the
          NSSM-wrapped services - of the child process NSSM runs (the real
          engine); a child younger than 120 s under an older service is
          flagged "[WARN] restarted <n> s ago" (crash loop still reads
          Running otherwise)
        * Recent log tail (configurable line count) with the log file's
          last write time and age

    Additionally, live HTTP probes:
        * RASTATIME-API     : http://127.0.0.1:8765/health   (expect 200)
        * RASTATIME-APACHE  : http://127.0.0.1:80/           (expect 200)
        * RASTATIME-ICECAST : http://127.0.0.1:8000/         (expect 200)

    Does NOT require administrator privileges for read-only status.
    Run as administrator to use 'nssm status' for richer NSSM detail.

.PARAMETER InstallRoot
    RASTATIME production install directory (used to locate logs).
    Default: C:\rastatime

.PARAMETER ApiHost
    IP/hostname of the RASTATIME-API for the health check.
    Default: 127.0.0.1

.PARAMETER ApiPort
    Port of the RASTATIME-API (must match SERVICE_TOPOLOGY.md §2.1).
    Default: 8765

.PARAMETER IcecastPort
    Stream port of RASTATIME-ICECAST (must match icecast.xml).
    Default: 8000

.PARAMETER LogLines
    Number of recent log lines to display per service.
    Set to 0 to suppress log output.
    Default: 15

.PARAMETER HealthTimeoutSec
    Seconds to wait for the API health response before timing out.
    Default: 5

.PARAMETER NssmExe
    Path to nssm.exe for richer status output (optional; falls back to
    Get-Service alone if omitted or not found).

.EXAMPLE
    # Quick status with default settings:
    powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1

.EXAMPLE
    # Show 30 log lines, custom install root:
    powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1 `
        -InstallRoot D:\rastatime -LogLines 30

.EXAMPLE
    # Health check only (no log output):
    powershell -ExecutionPolicy Bypass -File infra\nssm\status.ps1 `
        -LogLines 0

.NOTES
    See docs/architecture/SERVICE_TOPOLOGY.md for service definitions.
    See T22.4 (RESTART_ORDER.md) for restart and recovery procedures.
    See infra\nssm\install-*.ps1 to install a missing service.
#>

[CmdletBinding()]
param(
    [string] $InstallRoot       = "C:\rastatime",
    [string] $ApiHost           = "127.0.0.1",
    [int]    $ApiPort           = 8765,
    [int]    $IcecastPort       = 8000,
    [int]    $LogLines          = 15,
    [int]    $HealthTimeoutSec  = 5,
    [string] $NssmExe           = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'   # non-fatal; show all services even if one fails

# ---------------------------------------------------------------------------
# Service definitions  (name, log files, optional flag)
# ---------------------------------------------------------------------------
# Log files live under C:\rastatime\logs by default (see SERVICE_TOPOLOGY.md §6).
# Override with -InstallRoot if the deployment uses a non-standard path.
$ApiHealthUrl   = "http://${ApiHost}:${ApiPort}/health"
$ApacheUrl      = "http://${ApiHost}:80/"
$IcecastUrl     = "http://${ApiHost}:${IcecastPort}/"

$Services = @(
    [PSCustomObject]@{
        Name        = "RASTATIME-API"
        Logs        = @("$InstallRoot\logs\api-stdout.log",
                        "$InstallRoot\logs\api-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $ApiHealthUrl
        InstallHint = "infra\nssm\install-api.ps1"
    },
    [PSCustomObject]@{
        # Since 2026-11-03 (archiving stage 2) the worker uploads the
        # episodes archived on cba.media and fetches the CBA topic list; it
        # was an optional placeholder before.  Stopping it only pauses the
        # uploads, the broadcast does not depend on it.
        Name        = "RASTATIME-WORKER"
        Logs        = @("$InstallRoot\logs\worker-stdout.log",
                        "$InstallRoot\logs\worker-stderr.log")
        Optional    = $false
        Note        = "archive uploads to cba.media"
        HttpUrl     = $null
        InstallHint = "infra\nssm\install-worker.ps1"
    },
    [PSCustomObject]@{
        Name        = "RASTATIME-PLAYOUT"
        Logs        = @("$InstallRoot\logs\playout-stdout.log",
                        "$InstallRoot\logs\playout-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $null
        InstallHint = "infra\nssm\install-playout.ps1  (then re-apply the engine env vars - MIGRATION.md 4.7)"
    },
    [PSCustomObject]@{
        Name        = "RASTATIME-ANALYZER"
        Logs        = @("$InstallRoot\logs\analyzer-stdout.log",
                        "$InstallRoot\logs\analyzer-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $null
        InstallHint = "infra\nssm\install-analyzer.ps1"
    },
    [PSCustomObject]@{
        Name        = "RASTATIME-APACHE"
        Logs        = @("$InstallRoot\logs\apache-nssm-stdout.log",
                        "$InstallRoot\logs\apache-nssm-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $ApacheUrl
        InstallHint = "infra\nssm\install-apache.ps1"
    },
    [PSCustomObject]@{
        Name        = "RASTATIME-ICECAST"
        Logs        = @("$InstallRoot\logs\icecast-nssm-stdout.log",
                        "$InstallRoot\logs\icecast-nssm-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $IcecastUrl
        InstallHint = "infra\nssm\install-icecast.ps1 -IcecastExe 'C:\Tools\Icecast\bin\icecast.exe'"
    },
    [PSCustomObject]@{
        Name        = "RASTATIME-LIQUIDSOAP"
        Logs        = @("$InstallRoot\logs\liquidsoap-stdout.log",
                        "$InstallRoot\logs\liquidsoap-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $null
        InstallHint = "backend\playout\config\nssm-install-liquidsoap.ps1"
    },
    [PSCustomObject]@{
        # Standby Liquidsoap feeding the Icecast -standby fallback mounts
        # (listeners stay connected while RASTATIME-LIQUIDSOAP restarts).
        # nssm-install-standby.ps1 routes stderr into standby-stdout.log as
        # well, so the stderr file may not exist.
        Name        = "RASTATIME-STANDBY"
        Logs        = @("$InstallRoot\logs\standby-stdout.log",
                        "$InstallRoot\logs\standby-stderr.log")
        Optional    = $false
        Note        = $null
        HttpUrl     = $null
        InstallHint = "backend\playout\config\nssm-install-standby.ps1"
    }
)

# ---------------------------------------------------------------------------
# Locate NSSM (optional - used only for richer detail)
# ---------------------------------------------------------------------------
function Find-NssmOptional {
    if ($NssmExe -ne "" -and (Test-Path $NssmExe)) { return $NssmExe }
    $onPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $fallback = "C:\Tools\nssm\nssm.exe"
    if (Test-Path $fallback) { return $fallback }
    return $null
}

$Nssm = Find-NssmOptional

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Hr([string]$Char = "-", [int]$Width = 64) {
    Write-Host ($Char * $Width) -ForegroundColor DarkGray
}

function Write-SvcHeader([string]$Name, [bool]$Optional) {
    Write-Host ""
    Write-Hr "=" 64
    $label = if ($Optional) { "$Name  [optional]" } else { $Name }
    Write-Host "  $label" -ForegroundColor Cyan
    Write-Hr "=" 64
}

function Format-Status([string]$Status) {
    switch ($Status) {
        "Running"       { return "Running       " }
        "Stopped"       { return "Stopped       " }
        "StartPending"  { return "StartPending  " }
        "StopPending"   { return "StopPending   " }
        default         { return "$Status       " }
    }
}

function Get-StatusColor([string]$Status) {
    if ($Status -eq "Running")  { return "Green" }
    if ($Status -eq "Stopped")  { return "Red" }
    return "DarkYellow"
}

# Compact age / uptime text: "45 s", "94 min", "5 h 12 min", "3 d 02 h".
function Format-Age([TimeSpan]$Span) {
    if ($Span.TotalSeconds -lt 120)  { return ("{0} s" -f [int][math]::Floor($Span.TotalSeconds)) }
    if ($Span.TotalMinutes -lt 120)  { return ("{0} min" -f [int][math]::Floor($Span.TotalMinutes)) }
    if ($Span.TotalHours -lt 48)     { return ("{0} h {1:D2} min" -f [int][math]::Floor($Span.TotalHours), $Span.Minutes) }
    return ("{0} d {1:D2} h" -f $Span.Days, $Span.Hours)
}

# ---------------------------------------------------------------------------
# Tail a log file
# ---------------------------------------------------------------------------
function Show-LogTail([string]$LogPath, [int]$Lines) {
    if ($Lines -le 0) { return }
    if (-not (Test-Path $LogPath)) {
        Write-Host "    [log not found: $LogPath]" -ForegroundColor DarkGray
        return
    }
    # Header with the file's last write (local time) and age: a stderr tail
    # often shows stale lines from an earlier start.
    $item = Get-Item $LogPath -ErrorAction SilentlyContinue
    if ($item) {
        $lastWrite = $item.LastWriteTime
        $age = Format-Age ((Get-Date) - $lastWrite)
        Write-Host "    [log: $LogPath - last write $($lastWrite.ToString('yyyy-MM-dd HH:mm:ss')), $age ago]" -ForegroundColor DarkGray
    }
    # The services write UTF-8; @() keeps .Count valid for a one-line file
    # under Set-StrictMode (Get-Content returns a bare string then).
    $content = @(Get-Content $LogPath -Encoding UTF8 -ErrorAction SilentlyContinue)
    if ($content.Count -eq 0) {
        Write-Host "    [empty]" -ForegroundColor DarkGray
        return
    }
    $tail = @($content | Select-Object -Last $Lines)
    foreach ($line in $tail) {
        Write-Host "    $line" -ForegroundColor Gray
    }
}

# ---------------------------------------------------------------------------
# Process start time / uptime of the service process and NSSM's child
# ---------------------------------------------------------------------------
function Show-ProcessUptime([string]$SvcName) {
    # NSSM is the service process; the child it runs is the real engine.  A
    # crash loop keeps the SCM status at Running while the child is restarted,
    # so a young child under an old service process is flagged.
    $wsvc = Get-CimInstance Win32_Service -Filter "Name='$SvcName'" -ErrorAction SilentlyContinue
    if (-not $wsvc -or -not $wsvc.ProcessId -or $wsvc.ProcessId -eq 0) { return }
    $svcPid  = [int]$wsvc.ProcessId
    $svcProc = Get-CimInstance Win32_Process -Filter "ProcessId=$svcPid" -ErrorAction SilentlyContinue
    if (-not $svcProc -or -not $svcProc.CreationDate) {
        Write-Host "  PID         : $svcPid" -ForegroundColor Gray
        return
    }
    $now    = Get-Date
    $svcUp  = $now - $svcProc.CreationDate
    Write-Host ("  PID         : {0}  ({1})  started {2:yyyy-MM-dd HH:mm:ss}  uptime {3}" -f `
        $svcPid, $svcProc.Name, $svcProc.CreationDate, (Format-Age $svcUp)) -ForegroundColor Gray

    # Console programs (Icecast, Liquidsoap) also get a conhost.exe child - skip it.
    $child = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$svcPid" -ErrorAction SilentlyContinue |
               Where-Object { $_.CreationDate -and $_.Name -ne 'conhost.exe' } | Sort-Object CreationDate) | Select-Object -First 1
    if (-not $child) { return }
    $childUp = $now - $child.CreationDate
    Write-Host ("  Child PID   : {0}  ({1})  started {2:yyyy-MM-dd HH:mm:ss}  uptime {3}" -f `
        $child.ProcessId, $child.Name, $child.CreationDate, (Format-Age $childUp)) -ForegroundColor Gray -NoNewline
    # Young child under a service process that is itself older than the
    # threshold = NSSM restarted the engine (crash or planned restart).
    if ($childUp.TotalSeconds -lt 120 -and $svcUp.TotalSeconds -ge 120) {
        Write-Host ("  [WARN] restarted {0} s ago" -f [int][math]::Floor($childUp.TotalSeconds)) -ForegroundColor DarkYellow
    } else {
        Write-Host ""
    }
}

# ---------------------------------------------------------------------------
# HTTP probe (API health endpoint, Apache frontend, Icecast status page)
# ---------------------------------------------------------------------------
function Invoke-HttpProbe([string]$Url, [string]$SvcName) {
    Write-Host ""
    Write-Host "  HTTP probe      : $Url" -ForegroundColor DarkCyan
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing `
                    -TimeoutSec $HealthTimeoutSec -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Host "  HTTP status     : 200  OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  HTTP status     : $($resp.StatusCode) - unexpected (expected 200)" -ForegroundColor DarkYellow
            return $false
        }
    } catch {
        Write-Host "  HTTP status     : UNREACHABLE - $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  (Is $SvcName running and bound on this port?)" -ForegroundColor DarkYellow
        return $false
    }
}

# ---------------------------------------------------------------------------
# Per-service status block
# ---------------------------------------------------------------------------
function Show-ServiceStatus([PSCustomObject]$Svc) {
    Write-SvcHeader -Name $Svc.Name -Optional $Svc.Optional

    # SCM status via Get-Service
    $svcObj = Get-Service -Name $Svc.Name -ErrorAction SilentlyContinue
    if (-not $svcObj) {
        if ($Svc.Optional) {
            Write-Host "  Status : Not installed  (optional - OK)" -ForegroundColor DarkYellow
        } else {
            Write-Host "  Status : Not installed  [REQUIRED - install with $($Svc.InstallHint)]" `
                       -ForegroundColor Red
        }
        return
    }

    $color = Get-StatusColor $svcObj.Status
    Write-Host "  Status      : $(Format-Status $svcObj.Status)" -ForegroundColor $color -NoNewline
    Write-Host "  StartType: $($svcObj.StartType)" -ForegroundColor Gray
    if ($Svc.Note) {
        Write-Host "  Note        : $($Svc.Note)" -ForegroundColor DarkYellow
    }

    # NSSM richer detail (if available)
    if ($Nssm) {
        $nssmStatus = & $Nssm status $Svc.Name 2>&1
        if ($nssmStatus -and "$nssmStatus".Trim() -ne "") {
            Write-Host "  NSSM status : $nssmStatus" -ForegroundColor Gray
        }
    }

    # PID, start time and uptime of the service process and NSSM's child
    if ($svcObj.Status -eq 'Running') {
        try { Show-ProcessUptime -SvcName $Svc.Name } catch { <# non-fatal #> }
    }

    # HTTP probe (API / Apache / Icecast)
    if ($Svc.HttpUrl) {
        $null = Invoke-HttpProbe -Url $Svc.HttpUrl -SvcName $Svc.Name
    }

    # Log tail
    if ($LogLines -gt 0) {
        Write-Host ""
        Write-Host "  Last $LogLines lines - stdout log:" -ForegroundColor DarkCyan
        Show-LogTail -LogPath $Svc.Logs[0] -Lines $LogLines
        Write-Host ""
        Write-Host "  Last $LogLines lines - stderr log:" -ForegroundColor DarkCyan
        Show-LogTail -LogPath $Svc.Logs[1] -Lines $LogLines
    }
}

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
function Show-Summary([System.Collections.Generic.List[PSCustomObject]]$Results) {
    Write-Host ""
    Write-Hr "=" 64
    Write-Host "  SUMMARY" -ForegroundColor Cyan
    Write-Hr "=" 64
    Write-Host ""

    $allMandatoryOk = $true
    foreach ($r in $Results) {
        $optLabel = if ($r.Optional) { "[optional]" } else { "          " }
        $statusPad = $r.Status.PadRight(14)
        $color = if ($r.Healthy) { "Green" } else {
                     if ($r.Optional) { "DarkYellow" } else { "Red" }
                 }
        Write-Host "  $optLabel  $($r.Name.PadRight(24))  $statusPad" `
                   -ForegroundColor $color -NoNewline
        if ($r.HttpOk -ne $null) {
            $hLabel = if ($r.HttpOk) { "HTTP 200 healthy" } else { "HTTP probe FAIL" }
            $hColor = if ($r.HttpOk) { "Green" } else { "Red" }
            Write-Host "  $hLabel" -ForegroundColor $hColor
        } else {
            Write-Host ""
        }
        if (-not $r.Optional -and -not $r.Healthy) { $allMandatoryOk = $false }
    }

    Write-Host ""
    Write-Host "  Ports:" -ForegroundColor DarkCyan
    Write-Host "    RASTATIME-APACHE     : port 80    (HTTP, web UI; proxies /api/v2/ to $ApiPort)" -ForegroundColor Gray
    Write-Host "    RASTATIME-API        : port $ApiPort  (HTTP, Waitress)" -ForegroundColor Gray
    Write-Host "    RASTATIME-ICECAST    : port $IcecastPort  (HTTP, listener streams + admin)" -ForegroundColor Gray
    # 8001 is only open when stream.harbor is configured (rastatime.conf).
    $harbor = Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($harbor) {
        Write-Host "    RASTATIME-LIQUIDSOAP : port 8001  (DJ harbor - /main + /show share it), telnet 1234 (localhost)" -ForegroundColor Gray
    } else {
        Write-Host "    RASTATIME-LIQUIDSOAP : telnet 1234 (localhost); DJ harbor 8001 not listening (no stream.harbor configured)" -ForegroundColor Gray
    }
    Write-Host "    RASTATIME-STANDBY    : no port (feeds the Icecast -standby mounts)" -ForegroundColor Gray
    Write-Host "    RabbitMQ             : port 5672 (managed externally)" -ForegroundColor Gray
    Write-Host "    PostgreSQL           : port 5432 (managed externally)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Log directory : $InstallRoot\logs" -ForegroundColor Gray
    Write-Host ""

    if ($allMandatoryOk) {
        Write-Host "  All mandatory services are Running." -ForegroundColor Green
    } else {
        Write-Host "  One or more mandatory services are NOT Running." -ForegroundColor Red
        Write-Host "  Run infra\nssm\install-<service>.ps1 to reinstall." -ForegroundColor DarkYellow
    }
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  Service Status  (T22.3)" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd  HH:mm:ss')" -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Cyan

$results = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($svc in $Services) {
    Show-ServiceStatus -Svc $svc

    # Collect result for summary
    $svcObj    = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    $isRunning = $svcObj -and $svcObj.Status -eq 'Running'
    $httpOk    = $null

    if ($svc.HttpUrl -and $isRunning) {
        try {
            $r = Invoke-WebRequest -Uri $svc.HttpUrl -UseBasicParsing `
                     -TimeoutSec $HealthTimeoutSec -ErrorAction Stop
            $httpOk = ($r.StatusCode -eq 200)
        } catch {
            $httpOk = $false
        }
    }

    $results.Add([PSCustomObject]@{
        Name       = $svc.Name
        Status     = if ($svcObj) { "$($svcObj.Status)" } else { "Not installed" }
        Healthy    = $isRunning
        Optional   = $svc.Optional
        HttpOk     = $httpOk
    }) | Out-Null
}

Show-Summary -Results $results
