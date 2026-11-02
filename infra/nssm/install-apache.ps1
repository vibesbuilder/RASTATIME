#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install or reinstall the RASTATIME-APACHE Windows service via NSSM.

.DESCRIPTION
    Idempotent NSSM install script for RASTATIME-APACHE.

    Wraps Apache 2.4 (httpd.exe) as an NSSM-managed Windows service so
    service stop / restart times stay bounded.  All other RASTATIME
    services use NSSM; this brings Apache in line.

    PRECONDITION: if RASTATIME-APACHE is currently registered as the
    native Apache service (via httpd -k install), uninstall it FIRST:

        & "C:\Tools\Apache24\bin\httpd.exe" -k uninstall -n RASTATIME-APACHE

    The script will refuse to overwrite a non-NSSM service with the
    same name to avoid surprises.

.PARAMETER InstallRoot
    RASTATIME production install directory (used for log paths).

.PARAMETER ApacheRoot
    Apache 2.4 installation directory (httpd.exe lives in <ApacheRoot>\bin\).

.PARAMETER NssmExe
    Path to nssm.exe.

.PARAMETER StartService
    Start the service immediately after installation.

.NOTES
    See docs/operator/INSTALL_APACHE.md for the complete host setup.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $InstallRoot = "C:\rastatime",
    [string] $ApacheRoot  = "C:\Tools\Apache24",
    [string] $NssmExe     = "",
    [switch] $StartService
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Constants
$ServiceName    = "RASTATIME-APACHE"
$LogDir         = "$InstallRoot\logs"
$StdoutLog      = "$LogDir\apache-nssm-stdout.log"
$StderrLog      = "$LogDir\apache-nssm-stderr.log"
$RestartDelayMs = 5000
$ThrottleMs     = 5000
$RotateBytesMax = 10485760
$StopMethodMs   = 5000
$ApacheExe      = "$ApacheRoot\bin\httpd.exe"

function Write-Step([string]$Msg) { Write-Host "  [....] $Msg" -ForegroundColor Cyan }
function Write-OK([string]$Msg)   { Write-Host "  [ OK ] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "  [WARN] $Msg" -ForegroundColor DarkYellow }
function Write-Err([string]$Msg)  { Write-Host "  [FAIL] $Msg" -ForegroundColor Red }

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

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service install: $ServiceName"          -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$nssm = Find-Nssm

if (-not (Test-Path $ApacheExe)) {
    Write-Err "httpd.exe not found at: $ApacheExe"
    Write-Err "Adjust -ApacheRoot or install Apache 2.4."
    exit 1
}

Write-Host "  Install root : $InstallRoot" -ForegroundColor Gray
Write-Host "  NSSM         : $nssm"        -ForegroundColor Gray
Write-Host "  Apache root  : $ApacheRoot"  -ForegroundColor Gray
Write-Host "  httpd.exe    : $ApacheExe"   -ForegroundColor Gray
Write-Host ""

Write-Step "Ensuring log directory: $LogDir"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
Write-OK "Log directory ready."

# Refuse to overwrite a NATIVE Apache service silently - the operator
# must uninstall it first with `httpd -k uninstall -n RASTATIME-APACHE`.
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing -and -not (Test-IsNssmManaged $ServiceName)) {
    Write-Err "'$ServiceName' is registered as the native Apache service."
    Write-Err "Uninstall it first, then re-run this script:"
    Write-Err "    & `"$ApacheExe`" -k uninstall -n $ServiceName"
    exit 1
}

# Existing NSSM service: idempotent reinstall - stop and remove first.
if ($existing) {
    Write-Step "Existing NSSM service detected (status: $($existing.Status)); removing for reinstall..."
    if ($existing.Status -ne 'Stopped') {
        & $nssm stop $ServiceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 3
    }
    & $nssm remove $ServiceName confirm 2>&1 | Out-Null
    Write-OK "Removed existing NSSM service."
}

Write-Step "Installing '$ServiceName' as NSSM service..."
& $nssm install $ServiceName $ApacheExe
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm install failed (exit $LASTEXITCODE)."
    exit 1
}
Write-OK "Service installed."

Write-Step "Setting AppDirectory = $ApacheRoot"
& $nssm set $ServiceName AppDirectory $ApacheRoot

Write-Step "Configuring NSSM stdout/stderr capture..."
& $nssm set $ServiceName AppStdout $StdoutLog
& $nssm set $ServiceName AppStderr $StderrLog
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateOnline 1
& $nssm set $ServiceName AppRotateBytes $RotateBytesMax
Write-OK "NSSM capture logs: $StdoutLog / $StderrLog"

& $nssm set $ServiceName AppNoConsole 1

Write-Step "Configuring bounded stop methods (${StopMethodMs} ms each)..."
& $nssm set $ServiceName AppStopMethodConsole $StopMethodMs
& $nssm set $ServiceName AppStopMethodWindow  $StopMethodMs
& $nssm set $ServiceName AppStopMethodThreads $StopMethodMs
& $nssm set $ServiceName AppKillProcessTree 1
Write-OK "Stop methods bounded."

Write-Step "Setting restart policy (${RestartDelayMs} ms delay)..."
& $nssm set $ServiceName AppRestartDelay $RestartDelayMs
& $nssm set $ServiceName AppThrottle $ThrottleMs
& $nssm set $ServiceName AppExit Default Restart

& $nssm set $ServiceName Start SERVICE_AUTO_START

Write-Host ""

if ($StartService) {
    Write-Step "Starting '$ServiceName'..."
    & $nssm start $ServiceName
    # Poll up to 30 s (every 2 s) until the service reports Running.
    $svc = $null
    $waited = 0
    while ($waited -lt 30) {
        Start-Sleep -Seconds 2
        $waited += 2
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') { break }
    }

    if ($svc -and $svc.Status -eq 'Running') {
        Write-OK "$ServiceName is Running."
        Write-Host "  Frontend URL : http://localhost/"        -ForegroundColor Green
        Write-Host "  Apache logs  : $ApacheRoot\logs\"        -ForegroundColor Gray
        Write-Host "  NSSM logs    : $StdoutLog / $StderrLog"  -ForegroundColor Gray
    } else {
        $status = if ($svc) { $svc.Status } else { "not found" }
        Write-Warn "$ServiceName status after start: $status"
        Write-Warn "Check $StderrLog and $ApacheRoot\logs\error_log for details."
    }
} else {
    Write-Host "  Service installed but NOT started." -ForegroundColor DarkYellow
    Write-Host "  To start:  nssm start $ServiceName" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
