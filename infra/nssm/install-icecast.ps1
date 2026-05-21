#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install or reinstall the RASTATIME-ICECAST Windows service via NSSM.

.DESCRIPTION
    T22.1 - Idempotent NSSM install script for RASTATIME-ICECAST.

    RASTATIME-ICECAST is the OPTIONAL Icecast 2.x stream server.
    Install it only if the deployment requires:
      * Outgoing public audio streams (HTTP/Opus/MP3 for internet listeners)
      * Incoming remote live-stream ingress (source client -> Icecast mount
        -> RASTATIME-PLAYOUT)

    When Icecast is absent, audio reaches listeners only through the local
    soundcard.  The rest of the RASTATIME stack does not depend on Icecast.

    Port assignment (see docs/architecture/SERVICE_TOPOLOGY.md §5):
        RASTATIME-API runs on port 8765, so Icecast can use the standard
        Icecast default port 8000 for HTTP streams (and admin UI on the
        same port via /admin/).  Configured in icecast.xml.

    Service properties (see docs/architecture/SERVICE_TOPOLOGY.md §2.4):
        NSSM name  : RASTATIME-ICECAST
        Executable : icecast.exe
        Arguments  : -c C:\rastatime\config\icecast.xml
        Port       : 8000  (HTTP streams + admin UI, configurable in icecast.xml)
        Log        : C:\rastatime\logs\error.log + access.log
                     (via <logdir> in icecast.xml)
        Restart    : automatic, 15 000 ms delay

    Running this script a second time is safe: the existing service is
    stopped, removed, and reinstalled with the current parameters.

.PARAMETER InstallRoot
    RASTATIME production install directory.
    Default: C:\rastatime

.PARAMETER IcecastExe
    Path to icecast.exe.
    Default: C:\Program Files\Icecast\icecast.exe
    (Adjust if Icecast was installed to a non-default location.)

.PARAMETER IcecastConfig
    Path to the Icecast XML config file.
    Default: <InstallRoot>\config\icecast.xml

.PARAMETER NssmExe
    Path to nssm.exe.  If omitted the script searches PATH and then
    C:\Tools\nssm\nssm.exe.

.PARAMETER StartService
    If present, start the service immediately after installation.
    By default the service is installed but not started.

.EXAMPLE
    # Install with defaults:
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-icecast.ps1

.EXAMPLE
    # Custom Icecast path, start immediately:
    powershell -ExecutionPolicy Bypass -File infra\nssm\install-icecast.ps1 `
        -IcecastExe "D:\icecast\icecast.exe" -StartService

.NOTES
    OPTIONAL service - only install if streaming is required.
    Icecast is independent of the RASTATIME stack; it can be started at
    any time without affecting the API, worker, or playout services.

    Default Icecast port is 8000 (separate from RASTATIME-API on 8765).
    The <logdir> in icecast.xml should be set to C:/rastatime/logs so
    Icecast's own access.log and error.log live alongside the other
    RASTATIME service logs.

    See docs/architecture/SERVICE_TOPOLOGY.md §2.4 for full specification.
    See T22.2 (remove-icecast.ps1) to cleanly uninstall this service.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $InstallRoot    = "C:\rastatime",
    [string] $IcecastExe     = "C:\Program Files\Icecast\bin\icecast.exe",
    [string] $IcecastRoot    = "",
    [string] $IcecastConfig  = "",
    [string] $NssmExe        = "",
    [switch] $StartService
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$ServiceName    = "RASTATIME-ICECAST"
$LogDir         = "$InstallRoot\logs"
# Icecast writes its own log via icecast.xml <logdir>; NSSM captures any
# process stdout/stderr in a separate file in case Icecast crashes on start.
$StdoutLog      = "$LogDir\icecast-nssm-stdout.log"
$StderrLog      = "$LogDir\icecast-nssm-stderr.log"
$RestartDelayMs = 15000         # 15 s - per SERVICE_TOPOLOGY.md §2.4
$ThrottleMs     = 5000
$RotateBytesMax = 10485760      # 10 MB
$RotateFilesMax = 5

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
# Resolve Icecast config
# ---------------------------------------------------------------------------
function Resolve-IcecastConfig {
    if ($IcecastConfig -ne "") { return $IcecastConfig }
    return "$InstallRoot\config\icecast.xml"
}

# ---------------------------------------------------------------------------
# Verify Icecast binary
# ---------------------------------------------------------------------------
function Test-IcecastPresent {
    if (Test-Path $IcecastExe) {
        Write-OK "icecast.exe found: $IcecastExe"
        return $true
    }
    Write-Warn "icecast.exe not found at: $IcecastExe"
    Write-Warn "Download Icecast from https://icecast.org/#download (Windows binary)."
    Write-Warn "Service will be registered but cannot start until icecast.exe is present."
    return $false
}

# ---------------------------------------------------------------------------
# Main installation
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME  -  NSSM service install: $ServiceName  (T22.1)" -ForegroundColor Cyan
Write-Host "  [OPTIONAL - install only if streaming is required]" -ForegroundColor DarkYellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$nssm      = Find-Nssm
$iceCfg    = Resolve-IcecastConfig
# Icecast working directory: the install root (parent of bin\), so it can
# resolve its web\ and admin\ subdirectories relative to AppDirectory.
if ($IcecastRoot -ne "") {
    $workDir = $IcecastRoot
} else {
    $workDir = Split-Path (Split-Path $IcecastExe -Parent) -Parent
}

Write-Host "  Install root    : $InstallRoot"  -ForegroundColor Gray
Write-Host "  NSSM            : $nssm"         -ForegroundColor Gray
Write-Host "  icecast.exe     : $IcecastExe"   -ForegroundColor Gray
Write-Host "  Icecast config  : $iceCfg"       -ForegroundColor Gray
Write-Host "  Port            : 8000 (streams + admin, configured in icecast.xml)" -ForegroundColor Gray
Write-Host ""

$null = Test-IcecastPresent

# Ensure log directory exists
Write-Step "Ensuring log directory: $LogDir"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
Write-OK "Log directory: $LogDir (also set <logdir> in icecast.xml to rastatime\logs)"

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

# Install - executable is icecast.exe, not python.exe
Write-Step "Installing '$ServiceName'..."
& $nssm install $ServiceName $IcecastExe "-c `"$iceCfg`""
if ($LASTEXITCODE -ne 0) {
    Write-Err "nssm install failed (exit $LASTEXITCODE)."
    exit 1
}
Write-OK "Service installed."

# Working directory
Write-Step "Setting AppDirectory = $workDir"
& $nssm set $ServiceName AppDirectory $workDir

# NSSM captures process stdout/stderr separately from icecast.xml log
Write-Step "Configuring NSSM stdout/stderr capture..."
& $nssm set $ServiceName AppStdout $StdoutLog
& $nssm set $ServiceName AppStderr $StderrLog
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateOnline 1
& $nssm set $ServiceName AppRotateBytes $RotateBytesMax
Write-OK "NSSM capture logs: $StdoutLog / $StderrLog"
Write-Host "         Icecast application log: set <logdir> in icecast.xml to $LogDir" -ForegroundColor Gray

# Restart on crash - 15 s delay (Icecast is standalone; no rush)
Write-Step "Setting restart policy (${RestartDelayMs} ms delay)..."
& $nssm set $ServiceName AppRestartDelay $RestartDelayMs
& $nssm set $ServiceName AppThrottle $ThrottleMs
& $nssm set $ServiceName AppExit Default Restart

# Auto-start at boot (operator can change to DEMAND_START if preferred)
& $nssm set $ServiceName Start SERVICE_AUTO_START

Write-Host ""
Write-Host "  Required values in icecast.xml:" -ForegroundColor DarkCyan
Write-Host "    <port>8000</port>                      <!-- streams + admin UI -->" -ForegroundColor Gray
Write-Host "    <sources>8</sources>                   <!-- inside <limits>, must cover all enabled streams -->" -ForegroundColor Gray
Write-Host "    <source-password>...</source-password> <!-- must match cc_pref stream password -->" -ForegroundColor Gray
Write-Host "    <logdir>$LogDir</logdir>"             -ForegroundColor Gray
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
        Write-Host "  Stream / Status URL : http://localhost:8000/"      -ForegroundColor Green
        Write-Host "  Admin URL           : http://localhost:8000/admin/" -ForegroundColor Gray
    } else {
        $status = if ($svc) { $svc.Status } else { "not found" }
        Write-Warn "$ServiceName status after start: $status"
        Write-Warn "Check $StdoutLog / icecast.xml <logdir> for details."
    }
} else {
    Write-Host "  Service installed but NOT started." -ForegroundColor DarkYellow
    Write-Host "  RASTATIME-ICECAST is independent - start it at any time." -ForegroundColor DarkYellow
    Write-Host "  To start:  nssm start $ServiceName" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
