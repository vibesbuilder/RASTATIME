#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Remove the RASTATIME-ICECAST Windows service managed by NSSM.

.DESCRIPTION
    T22.2 - Idempotent NSSM remove script for RASTATIME-ICECAST.

    RASTATIME-ICECAST is an OPTIONAL service.  Removing it stops outgoing
    internet audio streams and incoming live-stream ingress, but leaves the
    core RASTATIME stack (API, worker, playout) fully operational.  Studio
    audio continues to reach listeners through the local soundcard.

    Stops the service (if running), then removes it from the Windows
    service registry via 'nssm remove'.  The icecast.xml config file and
    log files in C:\rastatime\logs are preserved by default; pass -PurgeLogs
    to delete the NSSM-captured log files as part of a clean uninstall.
    The icecast.xml config itself is never deleted by this script.

    Running this script when the service does not exist is safe - it
    prints a notice and exits 0 without error.

.PARAMETER InstallRoot
    RASTATIME production install directory (used to locate logs).
    Default: C:\rastatime

.PARAMETER NssmExe
    Path to nssm.exe.  Searched on PATH and at C:\Tools\nssm\nssm.exe if omitted.

.PARAMETER PurgeLogs
    If present, delete the NSSM-captured log files for this service:
        C:\rastatime\logs\icecast-nssm-stdout.log
        C:\rastatime\logs\icecast-nssm-stderr.log
    The Icecast application log (set via icecast.xml <logdir>) is NOT
    deleted - remove it manually if required.

.PARAMETER Force
    Skip the confirmation prompt before removing the service.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-icecast.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-icecast.ps1 `
        -Force -PurgeLogs

.NOTES
    OPTIONAL service - the rest of the RASTATIME stack is unaffected.
    Removing this service stops public streaming and remote source ingress.

    Reverse operation: infra\nssm\install-icecast.ps1
    See docs/architecture/SERVICE_TOPOLOGY.md §2.4 for service specification.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $InstallRoot = "C:\rastatime",
    [string] $NssmExe     = "",
    [switch] $PurgeLogs,
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$ServiceName = "RASTATIME-ICECAST"
$LogDir      = "$InstallRoot\logs"
# NSSM-captured stdout/stderr (Icecast application log is separate via icecast.xml)
$LogFiles    = @(
    "$LogDir\icecast-nssm-stdout.log",
    "$LogDir\icecast-nssm-stderr.log"
)

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Step([string]$Msg) { Write-Host "  [....] $Msg" -ForegroundColor Cyan }
function Write-OK([string]$Msg)   { Write-Host "  [ OK ] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "  [WARN] $Msg" -ForegroundColor DarkYellow }
function Write-Err([string]$Msg)  { Write-Host "  [FAIL] $Msg" -ForegroundColor Red }
function Write-Info([string]$Msg) { Write-Host "         $Msg" -ForegroundColor Gray }

# ---------------------------------------------------------------------------
# Locate NSSM
# ---------------------------------------------------------------------------
function Find-Nssm {
    if ($NssmExe -ne "") {
        if (Test-Path $NssmExe) { return $NssmExe }
        Write-Err "NssmExe '$NssmExe' not found."
        exit 1
    }
    $onPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $fallback = "C:\Tools\nssm\nssm.exe"
    if (Test-Path $fallback) { return $fallback }
    Write-Err "nssm.exe not found on PATH or at $fallback."
    Write-Err "Download NSSM from https://nssm.cc/download and add it to PATH."
    exit 1
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service remove: $ServiceName  (T22.2)" -ForegroundColor Cyan
Write-Host "  [OPTIONAL service - core stack is unaffected by removal]" -ForegroundColor DarkYellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$nssm = Find-Nssm

# Check if the service is registered - idempotent
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Warn "'$ServiceName' is not registered - nothing to remove."
    Write-Info "RASTATIME-ICECAST is optional; it may not have been installed."
    exit 0
}

Write-Host "  Service '$ServiceName' found.  Status: $($svc.Status)" -ForegroundColor Gray
Write-Host "  Log directory: $LogDir" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOTE: Removing this optional service stops public audio streams." -ForegroundColor DarkYellow
Write-Host "        The API, worker, and playout services are NOT affected." -ForegroundColor DarkYellow
Write-Host ""

# Confirmation
if (-not $Force) {
    $answer = Read-Host "  Remove '$ServiceName' from Windows services? [y/N]"
    if ($answer -notmatch '^[Yy]') {
        Write-Warn "Aborted by user."
        exit 0
    }
}

# Stop first
if ($svc.Status -ne 'Stopped') {
    Write-Step "Stopping '$ServiceName'  (public streams will be interrupted)..."
    & $nssm stop $ServiceName confirm 2>&1 | Out-Null
    $waited = 0
    while ($waited -lt 15) {
        Start-Sleep -Seconds 1
        $waited++
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $svc -or $svc.Status -eq 'Stopped') { break }
    }
    Write-OK "Service stopped."
}

# Remove
Write-Step "Removing '$ServiceName' via nssm remove..."
& $nssm remove $ServiceName confirm
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm remove exited with code $LASTEXITCODE."
    exit 1
}
Write-OK "Service '$ServiceName' removed."

# Verify
$check = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($check) {
    Write-Warn "Service still appears in SCM - a reboot may be required."
} else {
    Write-OK "Confirmed: '$ServiceName' is no longer registered."
}

# Optional NSSM log purge (Icecast application log is not touched)
if ($PurgeLogs) {
    Write-Step "Purging NSSM-captured log files..."
    foreach ($log in $LogFiles) {
        if (Test-Path $log) {
            Remove-Item $log -Force
            Write-OK "Deleted: $log"
        } else {
            Write-Info "Not found (skipped): $log"
        }
    }
    Write-Info "Icecast application log (set via icecast.xml <logdir>) was NOT deleted."
    Write-Info "Remove it manually from $LogDir if required."
} else {
    Write-Host ""
    Write-Host "  NSSM-captured log files retained in $LogDir" -ForegroundColor DarkYellow
    Write-Host "  Re-run with -PurgeLogs to delete them:" -ForegroundColor Gray
    foreach ($log in $LogFiles) {
        Write-Info $log
    }
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host "  To reinstate streaming: run infra\nssm\install-icecast.ps1" -ForegroundColor Gray
Write-Host ""
