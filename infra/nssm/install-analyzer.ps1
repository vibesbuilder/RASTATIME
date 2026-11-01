#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install or reinstall the RASTATIME-ANALYZER Windows service via NSSM.

.DESCRIPTION
    Idempotent NSSM install script for RASTATIME-ANALYZER.

    RASTATIME-ANALYZER is the file-import processor.  It listens on a
    RabbitMQ queue for messages dispatched by the PHP frontend whenever
    an operator uploads a media file.  For each message it runs the
    rastatime_analyzer pipeline:

        1. Extract ID3 / metadata tags
        2. Compute duration and (optionally) cue points
        3. Compute ReplayGain
        4. Verify playability
        5. Move the file from stor/organize/ to stor/imported/<owner_id>/
        6. Push the resulting metadata back to the API so cc_files moves
           from "Pending Import" (status=1) to "Ready" (status=0).

    Without this service running, every file uploaded via the Web UI
    sits in stor/organize/ forever and stays at "Pending Import" in
    Recent Uploads.

    Service properties:
        NSSM name  : RASTATIME-ANALYZER
        Executable : rastatime-analyzer.exe (from the install-root venv)
        Port       : None (subscribes to RabbitMQ)
        Logs       : C:\rastatime\logs\analyzer-stdout.log
                     C:\rastatime\logs\analyzer-stderr.log
        Restart    : automatic, 10 000 ms delay

    Running this script a second time is safe: the existing service is
    stopped, removed, and reinstalled with the current parameters.

.PARAMETER InstallRoot
    RASTATIME production install directory.
    Default: C:\rastatime

.PARAMETER ConfigFile
    Path to rastatime.conf.
    Default: <InstallRoot>\config\rastatime.conf

.PARAMETER NssmExe
    Path to nssm.exe.  If omitted the script searches PATH and then
    C:\Tools\nssm\nssm.exe.

.PARAMETER StartService
    If present, start the service immediately after installation.
    By default the service is installed but not started.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-analyzer.ps1 -StartService

.NOTES
    Requires:
      - RabbitMQ running on the host configured in rastatime.conf
        (PHP would already fail uploads if RabbitMQ were down).
      - FFmpeg on PATH (used by analyze_replaygain and analyze_cuepoint).
      - The rastatime-analyzer console script in the RASTATIME venv
        (installed by `pip install -e backend/analyzer`).
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
$ServiceName    = "RASTATIME-ANALYZER"
$LogDir         = "$InstallRoot\logs"
$StdoutLog      = "$LogDir\analyzer-stdout.log"
$StderrLog      = "$LogDir\analyzer-stderr.log"
$RestartDelayMs = 10000
$ThrottleMs     = 15000
$RotateBytesMax = 10485760

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Step([string]$Msg) { Write-Host "  [....] $Msg" -ForegroundColor Cyan }
function Write-OK([string]$Msg)   { Write-Host "  [ OK ] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "  [WARN] $Msg" -ForegroundColor DarkYellow }
function Write-Err([string]$Msg)  { Write-Host "  [FAIL] $Msg" -ForegroundColor Red }

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

# ---------------------------------------------------------------------------
# Locate rastatime-analyzer.exe (entry point installed by pip)
# ---------------------------------------------------------------------------
function Find-Analyzer {
    $candidates = @(
        "$InstallRoot\.venv\Scripts\rastatime-analyzer.exe",
        "$InstallRoot\.venv\bin\rastatime-analyzer.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    $onPath = Get-Command rastatime-analyzer -ErrorAction SilentlyContinue
    if ($onPath) {
        Write-Warn "Analyzer not in venv; falling back to PATH: $($onPath.Source)"
        return $onPath.Source
    }
    Write-Err "rastatime-analyzer.exe not found.  Run:"
    Write-Err "  pip install -e $InstallRoot\backend\analyzer"
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve config file
# ---------------------------------------------------------------------------
function Resolve-ConfigFile {
    if ($ConfigFile -ne "") { return $ConfigFile }
    return "$InstallRoot\config\rastatime.conf"
}

# ---------------------------------------------------------------------------
# Main installation
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service install: $ServiceName"          -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$nssm     = Find-Nssm
$analyzer = Find-Analyzer
$cfgFile  = Resolve-ConfigFile
$workDir  = "$InstallRoot\backend\analyzer"

Write-Host "  Install root : $InstallRoot" -ForegroundColor Gray
Write-Host "  NSSM         : $nssm"        -ForegroundColor Gray
Write-Host "  Analyzer     : $analyzer"    -ForegroundColor Gray
Write-Host "  Config file  : $cfgFile"     -ForegroundColor Gray
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

# Install — analyzer entry point takes --config and --log-level via env or flags.
# We rely on RASTATIME_CONFIG_FILEPATH for the config path so we do not have to
# repeat -f arguments here, matching how RASTATIME-API and RASTATIME-PLAYOUT
# discover their config.
Write-Step "Installing '$ServiceName'..."
& $nssm install $ServiceName $analyzer
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm install failed (exit $LASTEXITCODE)."
    exit 1
}
Write-OK "Service installed."

# Working directory
Write-Step "Setting AppDirectory = $workDir"
& $nssm set $ServiceName AppDirectory $workDir

# Stdout / stderr logs
Write-Step "Configuring log files..."
& $nssm set $ServiceName AppStdout $StdoutLog
& $nssm set $ServiceName AppStderr $StderrLog
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateOnline 1
& $nssm set $ServiceName AppRotateBytes $RotateBytesMax
Write-OK "Log files: $StdoutLog / $StderrLog"

# Run headless
& $nssm set $ServiceName AppNoConsole 1

# Restart policy
Write-Step "Setting restart policy (${RestartDelayMs} ms delay)..."
& $nssm set $ServiceName AppRestartDelay $RestartDelayMs
& $nssm set $ServiceName AppThrottle $ThrottleMs
& $nssm set $ServiceName AppExit Default Restart

# Auto-start at boot
& $nssm set $ServiceName Start SERVICE_AUTO_START

# Environment variables — analyzer reads rastatime.conf from this path,
# and PATH must include FFmpeg for the replaygain / cuepoint pipeline steps.
Write-Step "Configuring environment variables (FFmpeg on PATH)..."
& $nssm set $ServiceName AppEnvironmentExtra `
    "RASTATIME_CONFIG_FILEPATH=$cfgFile" `
    "PATH=C:\ffmpeg\bin;%PATH%" `
    "PYTHONUTF8=1"
Write-OK "Environment variables set."

Write-Host ""

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
        Write-Host "  The analyzer now consumes the 'analyzer' RabbitMQ queue." -ForegroundColor Green
        Write-Host "  Pending uploads in stor/organize/ should clear within seconds." -ForegroundColor Green
    } else {
        $status = if ($svc) { $svc.Status } else { "not found" }
        Write-Warn "$ServiceName status after start: $status"
        Write-Warn "Check $StderrLog for details."
    }
} else {
    Write-Host "  Service installed but NOT started." -ForegroundColor DarkYellow
    Write-Host "  To start:  nssm start $ServiceName" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
