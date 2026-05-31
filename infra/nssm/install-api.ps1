#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install or reinstall the RASTATIME-API Windows service via NSSM.

.DESCRIPTION
    T22.1 - Idempotent NSSM install script for RASTATIME-API.

    RASTATIME-API is the mandatory Django/Waitress REST API service.
    It binds on port 8000 and must be running before the worker and
    playout services are started.

    Service properties (see docs/architecture/SERVICE_TOPOLOGY.md §2.1):
        NSSM name  : RASTATIME-API
        Executable : python.exe  (from the install-root venv)
        Arguments  : -m libretime_api.waitress_serve --host 0.0.0.0 --port 8000 --threads 8
        Port       : 8000  (HTTP, Waitress)
        Logs       : C:\rastatime\logs\api-stdout.log
                     C:\rastatime\logs\api-stderr.log
        Restart    : automatic, 5 000 ms delay

    Running this script a second time is safe: the existing service is
    stopped, removed, and reinstalled with the current parameters.

.PARAMETER InstallRoot
    RASTATIME production install directory.
    Default: C:\rastatime

.PARAMETER ConfigFile
    Path to libretime.conf.
    Default: <InstallRoot>\config\libretime.conf

.PARAMETER ApiHost
    IP address for Waitress to bind on.
    Default: 0.0.0.0

.PARAMETER ApiPort
    TCP port for the Waitress WSGI server.
    Default: 8000

.PARAMETER ApiThreads
    Number of Waitress worker threads.
    Default: 8

.PARAMETER NssmExe
    Path to nssm.exe.  If omitted the script searches PATH and then
    C:\Tools\nssm\nssm.exe (a common manual-install location).

.PARAMETER StartService
    If present, start the service immediately after installation.
    By default the service is installed but not started so that the
    operator can start all services in the correct order.

.EXAMPLE
    # Install with defaults:
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-api.ps1

.EXAMPLE
    # Custom root, start immediately:
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-api.ps1 `
        -InstallRoot D:\rastatime -StartService

.NOTES
    Startup order: start this service first (after PostgreSQL), then
    install-worker.ps1 and install-playout.ps1.

    See docs/architecture/SERVICE_TOPOLOGY.md for the full service topology.
    See T22.2 (remove-api.ps1) to cleanly uninstall this service.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $InstallRoot = "C:\rastatime",
    [string] $ConfigFile  = "",
    [string] $ApiHost     = "0.0.0.0",
    [int]    $ApiPort     = 8765,
    [int]    $ApiThreads  = 8,
    [string] $NssmExe     = "",
    [switch] $StartService
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$ServiceName    = "RASTATIME-API"
$LogDir         = "$InstallRoot\logs"
$StdoutLog      = "$LogDir\api-stdout.log"
$StderrLog      = "$LogDir\api-stderr.log"
$RestartDelayMs = 5000          # 5 s - per SERVICE_TOPOLOGY.md §2.1
$ThrottleMs     = 5000          # startup throttle (same as restart delay)
$RotateBytesMax = 10485760      # 10 MB per log file

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

$nssm      = Find-Nssm
$python    = Find-Python
$cfgFile   = Resolve-ConfigFile
$workDir   = "$InstallRoot\backend\api"
$pythonPath = "$InstallRoot\backend\api;$InstallRoot\backend\shared;$InstallRoot"

Write-Host "  Install root : $InstallRoot" -ForegroundColor Gray
Write-Host "  NSSM         : $nssm"        -ForegroundColor Gray
Write-Host "  Python       : $python"      -ForegroundColor Gray
Write-Host "  Config file  : $cfgFile"     -ForegroundColor Gray
Write-Host "  Bind         : ${ApiHost}:${ApiPort}  threads=$ApiThreads" -ForegroundColor Gray
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

# Compose Waitress arguments
$svcArgs = "-m libretime_api.waitress_serve --host $ApiHost --port $ApiPort --threads $ApiThreads"

# Install
Write-Step "Installing '$ServiceName'..."
& $nssm install $ServiceName $python $svcArgs
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
# Log rotation: 10 MB per file (NSSM has no max-file-count cap)
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateOnline 1
& $nssm set $ServiceName AppRotateBytes $RotateBytesMax
Write-OK "Log files: $StdoutLog / $StderrLog"

# Run headless - no console window
& $nssm set $ServiceName AppNoConsole 1

# Auto-restart on crash
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
    "RASTATIME_API_HOST=$ApiHost" `
    "RASTATIME_API_PORT=$ApiPort" `
    "RASTATIME_API_THREADS=$ApiThreads" `
    "PYTHONPATH=$pythonPath"
Write-OK "Environment variables set."

# ---------------------------------------------------------------------------
# Optional: start now
# ---------------------------------------------------------------------------
if ($StartService) {
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
    Write-Host ""
    Write-Host "  Service installed but NOT started." -ForegroundColor DarkYellow
    Write-Host "  Start order: PostgreSQL -> $ServiceName -> RASTATIME-WORKER -> RASTATIME-PLAYOUT" -ForegroundColor DarkYellow
    Write-Host "  To start:  nssm start $ServiceName" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done.  Health endpoint will be at http://${ApiHost}:${ApiPort}/health" -ForegroundColor Green
Write-Host ""
