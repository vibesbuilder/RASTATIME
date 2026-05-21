#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install or reinstall the RASTATIME-WORKER Windows service via NSSM.

.DESCRIPTION
    T22.1 - Idempotent NSSM install script for RASTATIME-WORKER.

    RASTATIME-WORKER is the mandatory background job runner (APScheduler-
    based; replaces Celery).  It must not start its main loop until the
    RASTATIME-API is healthy.  This script configures NSSM and documents
    the health-check gate that the worker entry point must implement.

    Health-check gate:
        Before entering its main loop, rastatime_worker/__main__.py
        must poll http://127.0.0.1:8000/health with exponential backoff
        until a HTTP 200 response is received (or a timeout elapses).
        This ensures the API is ready to accept DB connections before
        the worker starts scheduling jobs.

    Service properties (see docs/architecture/SERVICE_TOPOLOGY.md §2.2):
        NSSM name  : RASTATIME-WORKER
        Executable : python.exe  (from the install-root venv)
        Arguments  : -m rastatime_worker
        Port       : None (no external port)
        Logs       : C:\rastatime\logs\worker-stdout.log
                     C:\rastatime\logs\worker-stderr.log
        Restart    : automatic, 10 000 ms delay

    Running this script a second time is safe: the existing service is
    stopped, removed, and reinstalled with the current parameters.

.PARAMETER InstallRoot
    RASTATIME production install directory.
    Default: C:\rastatime

.PARAMETER ConfigFile
    Path to libretime.conf.
    Default: <InstallRoot>\config\libretime.conf

.PARAMETER NssmExe
    Path to nssm.exe.  If omitted the script searches PATH and then
    C:\Tools\nssm\nssm.exe.

.PARAMETER StartService
    If present, start the service immediately after installation.
    By default the service is installed but not started.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-worker.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-worker.ps1 `
        -InstallRoot D:\rastatime -StartService

.NOTES
    Start RASTATIME-API first; this service depends on the API being healthy.
    See T22.1 health-check gate requirement: http://127.0.0.1:8000/health

    See docs/architecture/SERVICE_TOPOLOGY.md §2.2 for full specification.
    See T22.2 (remove-worker.ps1) to cleanly uninstall this service.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $InstallRoot = "C:\rastatime",
    [string] $ConfigFile  = "",
    [string] $NssmExe     = "",
    [switch] $StartService
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$ServiceName    = "RASTATIME-WORKER"
$LogDir         = "$InstallRoot\logs"
$StdoutLog      = "$LogDir\worker-stdout.log"
$StderrLog      = "$LogDir\worker-stderr.log"
$RestartDelayMs = 10000         # 10 s - per SERVICE_TOPOLOGY.md §2.2
$ThrottleMs     = 15000         # extra startup throttle: API needs ~5 s first
$RotateBytesMax = 10485760      # 10 MB
$RotateFilesMax = 5

# Health-check gate - documented here; implemented in rastatime_worker/__main__.py
$ApiHealthUrl   = "http://127.0.0.1:8765/health"
$HealthTimeout  = 120           # seconds to wait for API to become healthy

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Step([string]$Msg) {
    Write-Host "  [....] $Msg" -ForegroundColor Cyan
}

function Write-OK([string]$Msg) {
    Write-Host "  [ OK ] $Msg" -ForegroundColor Green
}

function Write-Warn([string]$Msg) {
    Write-Host "  [WARN] $Msg" -ForegroundColor DarkYellow
}

function Write-Err([string]$Msg) {
    Write-Host "  [FAIL] $Msg" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Health-check gate helper
# Polls $ApiHealthUrl until HTTP 200 or timeout.
# Used during post-install validation; must also be implemented in the
# Python entry point (rastatime_worker/__main__.py).
# ---------------------------------------------------------------------------
function Wait-ApiHealth([int]$TimeoutSecs = $HealthTimeout) {
    Write-Step "Waiting for API health gate: $ApiHealthUrl  (timeout ${TimeoutSecs}s)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSecs)
    $delay    = 2

    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $ApiHealthUrl -UseBasicParsing `
                        -TimeoutSec 4 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Write-OK "API is healthy (HTTP 200)."
                return $true
            }
        } catch {
            # Not yet healthy - keep polling
        }
        Start-Sleep -Seconds $delay
        if ($delay -lt 30) { $delay = [math]::Min($delay * 2, 30) }
    }

    Write-Warn "API did not respond at $ApiHealthUrl within ${TimeoutSecs}s."
    Write-Warn "The worker service will still be installed.  Start it after the API is up."
    return $false
}

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
# Locate Python
# ---------------------------------------------------------------------------
function Find-Python {
    $venvPython = "$InstallRoot\.venv\Scripts\python.exe"
    if (Test-Path $venvPython) { return $venvPython }

    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath) {
        Write-Warn "Venv python not found at $venvPython - using PATH python."
        return $onPath.Source
    }

    Write-Err "python.exe not found.  Install Python 3.11+ or create the venv."
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve config file
# ---------------------------------------------------------------------------
function Resolve-ConfigFile {
    if ($ConfigFile -ne "") { return $ConfigFile }
    return "$InstallRoot\config\libretime.conf"
}

# ---------------------------------------------------------------------------
# Main installation
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service install: $ServiceName  (T22.1)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$nssm       = Find-Nssm
$python     = Find-Python
$cfgFile    = Resolve-ConfigFile
$workDir    = "$InstallRoot\backend"
$pythonPath = "$InstallRoot\backend\api;$InstallRoot\backend\shared;$InstallRoot"

Write-Host "  Install root : $InstallRoot"   -ForegroundColor Gray
Write-Host "  NSSM         : $nssm"          -ForegroundColor Gray
Write-Host "  Python       : $python"        -ForegroundColor Gray
Write-Host "  Config file  : $cfgFile"       -ForegroundColor Gray
Write-Host "  Health gate  : $ApiHealthUrl"  -ForegroundColor Gray
Write-Host ""

# Ensure log directory exists
Write-Step "Ensuring log directory: $LogDir"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
Write-OK "Log directory ready."

# Idempotent: stop and remove existing service
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Step "Stopping existing '$ServiceName' service..."
    if ($existing.Status -ne 'Stopped') {
        & $nssm stop $ServiceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 3
    }
    Write-Step "Removing existing '$ServiceName' service..."
    & $nssm remove $ServiceName confirm 2>&1 | Out-Null
    Write-OK "Removed existing service."
}

# Install
Write-Step "Installing '$ServiceName'..."
& $nssm install $ServiceName $python "-m libretime_worker"
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm install failed (exit $LASTEXITCODE)."
    exit 1
}
Write-OK "Service installed."

# Working directory
Write-Step "Setting AppDirectory = $workDir"
& $nssm set $ServiceName AppDirectory $workDir

# Stdout / stderr log files
Write-Step "Configuring log files..."
& $nssm set $ServiceName AppStdout $StdoutLog
& $nssm set $ServiceName AppStderr $StderrLog
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateOnline 1
& $nssm set $ServiceName AppRotateBytes $RotateBytesMax
& $nssm set $ServiceName AppRotateFilesMax $RotateFilesMax
Write-OK "Log files: $StdoutLog / $StderrLog"

# Run headless
& $nssm set $ServiceName AppNoConsole 1

# Restart on crash - 10 s delay (longer than API to let it restart first)
Write-Step "Setting restart policy (${RestartDelayMs} ms delay)..."
& $nssm set $ServiceName AppRestartDelay $RestartDelayMs
& $nssm set $ServiceName AppThrottle $ThrottleMs
& $nssm set $ServiceName AppExit Default Restart

# Auto-start at boot
& $nssm set $ServiceName Start SERVICE_AUTO_START

# Environment variables
Write-Step "Configuring environment variables..."
& $nssm set $ServiceName AppEnvironmentExtra `
    "DJANGO_SETTINGS_MODULE=libretime_api.settings.prod" `
    "LIBRETIME_CONFIG_FILEPATH=$cfgFile" `
    "PYTHONPATH=$pythonPath"
Write-OK "Environment variables set."

Write-Host ""
Write-Host "  NOTE: The worker entry point (rastatime_worker/__main__.py) must" -ForegroundColor DarkYellow
Write-Host "        poll $ApiHealthUrl with exponential backoff" -ForegroundColor DarkYellow
Write-Host "        before entering the main scheduling loop." -ForegroundColor DarkYellow
Write-Host ""

# ---------------------------------------------------------------------------
# Optional: start now
# ---------------------------------------------------------------------------
if ($StartService) {
    $null = Wait-ApiHealth -TimeoutSecs $HealthTimeout
    Write-Step "Starting '$ServiceName'..."
    & $nssm start $ServiceName
    Start-Sleep -Seconds 4

    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq 'Running') {
        Write-OK "$ServiceName is Running."
    } else {
        $status = if ($svc) { $svc.Status } else { "not found" }
        Write-Warn "$ServiceName status after start: $status"
        Write-Warn "Check $StdoutLog / $StderrLog for details."
    }
} else {
    Write-Host "  Service installed but NOT started." -ForegroundColor DarkYellow
    Write-Host "  Ensure RASTATIME-API is healthy before starting this service." -ForegroundColor DarkYellow
    Write-Host "  To start:  nssm start $ServiceName" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
