#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Remove the RASTATIME-APACHE Windows service managed by NSSM.

.DESCRIPTION
    Idempotent NSSM remove script for RASTATIME-APACHE.

    Stops the service (if running), then removes it from the Windows
    service registry via 'nssm remove'.  Apache's own log files under
    <ApacheRoot>\logs\ are preserved.  NSSM-side capture logs are
    preserved by default; pass -PurgeLogs to delete them.

    If the service is the native Apache one (not NSSM-managed), this
    script aborts and points you at `httpd -k uninstall -n RASTATIME-APACHE`.

    Running this script when the service does not exist is safe — it
    prints a notice and exits 0 without error.

.PARAMETER InstallRoot
    RASTATIME production install directory (used to locate logs).
    Default: C:\rastatime

.PARAMETER NssmExe
    Path to nssm.exe.  Searched on PATH and at C:\Tools\nssm\nssm.exe if omitted.

.PARAMETER PurgeLogs
    Delete the NSSM stdout/stderr log files for this service after removal:
        C:\rastatime\logs\apache-nssm-stdout.log
        C:\rastatime\logs\apache-nssm-stderr.log
    Apache's own access_log / error_log are NEVER touched.

.PARAMETER Force
    Skip the confirmation prompt before removing the service.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-apache.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\remove-apache.ps1 `
        -Force -PurgeLogs

.NOTES
    Reverse operation: infra\nssm\install-apache.ps1
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
$ServiceName = "RASTATIME-APACHE"
$LogDir      = "$InstallRoot\logs"
$LogFiles    = @(
    "$LogDir\apache-nssm-stdout.log",
    "$LogDir\apache-nssm-stderr.log"
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
    exit 1
}

function Test-IsNssmManaged([string]$Name) {
    $nssmTool = Find-Nssm
    & $nssmTool get $Name Application 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service remove: $ServiceName"           -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$nssm = Find-Nssm

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Warn "'$ServiceName' is not registered — nothing to remove."
    exit 0
}

if (-not (Test-IsNssmManaged $ServiceName)) {
    Write-Err "'$ServiceName' is registered as the NATIVE Apache service, not via NSSM."
    Write-Err "Use Apache's own uninstall command instead:"
    Write-Err '    & "C:\Tools\Apache24\bin\httpd.exe" -k uninstall -n RASTATIME-APACHE'
    exit 1
}

Write-Host "  Service '$ServiceName' found.  Status: $($svc.Status)" -ForegroundColor Gray
Write-Host "  Log directory: $LogDir" -ForegroundColor Gray
Write-Host ""

if (-not $Force) {
    $answer = Read-Host "  Remove '$ServiceName' from Windows services? [y/N]"
    if ($answer -notmatch '^[Yy]') {
        Write-Warn "Aborted by user."
        exit 0
    }
}

if ($svc.Status -ne 'Stopped') {
    Write-Step "Stopping '$ServiceName'..."
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

Write-Step "Removing '$ServiceName' via nssm remove..."
& $nssm remove $ServiceName confirm
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm remove exited with code $LASTEXITCODE."
    exit 1
}
Write-OK "Service '$ServiceName' removed."

$check = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($check) {
    Write-Warn "Service still appears in SCM — a reboot may be required."
} else {
    Write-OK "Confirmed: '$ServiceName' is no longer registered."
}

if ($PurgeLogs) {
    Write-Step "Purging NSSM capture log files..."
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
    Write-Host "  NSSM capture logs retained in $LogDir" -ForegroundColor DarkYellow
    Write-Host "  Apache's own access_log / error_log are at <ApacheRoot>\logs\" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
