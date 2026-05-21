#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Remove the RASTATIME-PLAYOUT Windows service managed by NSSM.

.DESCRIPTION
    T22.2 - Idempotent NSSM remove script for RASTATIME-PLAYOUT.

    Stops the service (if running), then removes it from the Windows
    service registry via 'nssm remove'.  Log files are preserved by
    default; pass -PurgeLogs for a fully clean uninstall.

    Running this script when the service does not exist is safe - it
    prints a notice and exits 0 without error.

    Note: stopping the playout service interrupts on-air audio output.
    Ensure this is intended before running in a live environment.

.PARAMETER InstallRoot
    RASTATIME production install directory (used to locate logs).
    Default: C:\rastatime

.PARAMETER NssmExe
    Path to nssm.exe.  Searched on PATH and at C:\Tools\nssm\nssm.exe if omitted.

.PARAMETER PurgeLogs
    If present, delete the log files for this service after removal:
        C:\rastatime\logs\playout-stdout.log
        C:\rastatime\logs\playout-stderr.log

.PARAMETER Force
    Skip the confirmation prompt before removing the service.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-playout.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-playout.ps1 `
        -Force -PurgeLogs

.NOTES
    CAUTION: removing this service stops on-air audio output immediately.
    Run this script only during a scheduled maintenance window.

    Recommended shutdown sequence (see T22.4 - RESTART_ORDER.md):
        1. RASTATIME-PLAYOUT  (this script - stop audio first)
        2. RASTATIME-WORKER   (remove-worker.ps1)
        3. RASTATIME-API      (remove-api.ps1)
        4. RASTATIME-ICECAST  (remove-icecast.ps1 - optional, independent)

    Reverse operation: infra\nssm\install-playout.ps1
    See docs/architecture/SERVICE_TOPOLOGY.md §2.3 for service specification.
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
$ServiceName = "RASTATIME-PLAYOUT"
$LogDir      = "$InstallRoot\logs"
$LogFiles    = @(
    "$LogDir\playout-stdout.log",
    "$LogDir\playout-stderr.log"
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
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service remove: $ServiceName  (T22.2)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  CAUTION: this will stop on-air audio output." -ForegroundColor DarkYellow
Write-Host ""

$nssm = Find-Nssm

# Check if the service is registered - idempotent
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Warn "'$ServiceName' is not registered - nothing to remove."
    Write-Info "This is normal if the service was never installed or already removed."
    exit 0
}

Write-Host "  Service '$ServiceName' found.  Status: $($svc.Status)" -ForegroundColor Gray
Write-Host "  Log directory: $LogDir" -ForegroundColor Gray
Write-Host ""

# Confirmation
if (-not $Force) {
    $answer = Read-Host "  Remove '$ServiceName' from Windows services? [y/N]"
    if ($answer -notmatch '^[Yy]') {
        Write-Warn "Aborted by user."
        exit 0
    }
}

# Stop first (stops audio output)
if ($svc.Status -ne 'Stopped') {
    Write-Step "Stopping '$ServiceName'  (audio output will stop)..."
    & $nssm stop $ServiceName confirm 2>&1 | Out-Null
    $waited = 0
    while ($waited -lt 20) {
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

# Optional log purge
if ($PurgeLogs) {
    Write-Step "Purging log files..."
    foreach ($log in $LogFiles) {
        if (Test-Path $log) {
            Remove-Item $log -Force
            Write-OK "Deleted: $log"
        } else {
            Write-Info "Not found (skipped): $log"
        }
    }
} else {
    Write-Host ""
    Write-Host "  Log files retained in $LogDir" -ForegroundColor DarkYellow
    Write-Host "  Re-run with -PurgeLogs to delete them:" -ForegroundColor Gray
    foreach ($log in $LogFiles) {
        Write-Info $log
    }
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
