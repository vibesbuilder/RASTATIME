#Requires -Version 5.1
<#
.SYNOPSIS
    Start the RASTATIME API in production mode via Waitress.

.DESCRIPTION
    T17.1 — Replaces gunicorn/uvicorn with Waitress, a pure-Python,
    Windows-compatible WSGI server.

    This script is intended for:
      - Manual production testing ("does it serve on this machine?")
      - NSSM service hosting (point NSSM's Program at this script)
      - CI smoke testing

    It configures environment variables, sets DJANGO_SETTINGS_MODULE to
    the production settings module, and invokes Waitress via
    ``python -m libretime_api.waitress_serve``.

    For development (DEBUG=True, SQLite DB, no config file required) use
    ``run-api.ps1`` instead.

.PARAMETER Host
    Bind address. Default: 127.0.0.1
    Use 0.0.0.0 to accept connections from the local network.

.PARAMETER Port
    Bind port. Default: 8000

.PARAMETER Threads
    Number of Waitress worker threads. Default: 4
    Tune to expected concurrency. For a radio station control plane 4-8
    threads is typically sufficient.

.PARAMETER ConfigFile
    Path to the RASTATIME configuration file (libretime.conf).
    Required by production settings (libretime_api.settings.prod).
    Defaults to <repo_root>\config\libretime.conf if it exists.

.EXAMPLE
    # From the repo root — serve on localhost with defaults:
    powershell -ExecutionPolicy Bypass -File infra\scripts\serve-api.ps1

.EXAMPLE
    # Bind to all interfaces, 8 threads, explicit config:
    powershell -ExecutionPolicy Bypass -File infra\scripts\serve-api.ps1 `
        -Host 0.0.0.0 -Port 8000 -Threads 8 `
        -ConfigFile C:\rastatime\config\libretime.conf

.NOTES
    Prerequisites:
        - Python 3.11+ with venv at <repo_root>\.venv (or on PATH)
        - waitress installed: pip install waitress
        - Django and all API dependencies installed
        - A valid libretime.conf config file

    NSSM service registration example:
        nssm install rastatime-api `
            "C:\rastatime\.venv\Scripts\python.exe" `
            "-m libretime_api.waitress_serve --host 127.0.0.1 --port 8000"
        nssm set rastatime-api AppDirectory "C:\rastatime\backend\api"
        nssm set rastatime-api AppEnvironmentExtra `
            "DJANGO_SETTINGS_MODULE=libretime_api.settings.prod" `
            "LIBRETIME_CONFIG_FILEPATH=C:\rastatime\config\libretime.conf"
        nssm start rastatime-api

    See ADR-005 and ADR-006 for service architecture decisions.
    See docs\operator\INSTALL.md for full setup instructions.
#>

[CmdletBinding()]
param(
    [string]$BindHost = "127.0.0.1",
    [int]   $Port     = 8000,
    [int]   $Threads  = 4,
    [string]$ConfigFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve repo root (script lives at infra\scripts\)
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..\')).Path

# ---------------------------------------------------------------------------
# Locate python
# ---------------------------------------------------------------------------
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (Test-Path $VenvPython) {
    $Python = $VenvPython
    Write-Host "  [venv]  Using $Python" -ForegroundColor DarkCyan
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) { $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $PythonCmd) {
        Write-Host "[ERROR] python not found. Run bootstrap.ps1 or activate your venv." -ForegroundColor Red
        exit 1
    }
    $Python = $PythonCmd.Source
    Write-Host "  [PATH]  Using $Python" -ForegroundColor DarkYellow
}

# ---------------------------------------------------------------------------
# Verify Waitress is installed
# ---------------------------------------------------------------------------
$WaitressCheck = & $Python -c "import waitress; print(waitress.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Waitress is not installed." -ForegroundColor Red
    Write-Host "        Run: pip install waitress" -ForegroundColor Yellow
    exit 1
}
Write-Host "  [ok]    Waitress $WaitressCheck installed." -ForegroundColor DarkCyan

# ---------------------------------------------------------------------------
# PYTHONPATH — make libretime_api importable
# ---------------------------------------------------------------------------
$ApiSrc    = Join-Path $RepoRoot 'backend\api'
$SharedSrc = Join-Path $RepoRoot 'backend\shared'
$ExistingPath = if ($env:PYTHONPATH) { $env:PYTHONPATH } else { "" }
$env:PYTHONPATH = "$ApiSrc;$SharedSrc;$RepoRoot;$ExistingPath"

# ---------------------------------------------------------------------------
# Django settings — production
# ---------------------------------------------------------------------------
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.prod"

# ---------------------------------------------------------------------------
# Config file
# ---------------------------------------------------------------------------
if ($ConfigFile -ne "") {
    $env:LIBRETIME_CONFIG_FILEPATH = $ConfigFile
    Write-Host "  [cfg]   Config: $ConfigFile" -ForegroundColor DarkCyan
} else {
    $DefaultCfg = Join-Path $RepoRoot 'config\libretime.conf'
    if (Test-Path $DefaultCfg) {
        $env:LIBRETIME_CONFIG_FILEPATH = $DefaultCfg
        Write-Host "  [cfg]   Config: $DefaultCfg (default)" -ForegroundColor DarkCyan
    } else {
        Write-Host "  [warn]  No config file found. Set -ConfigFile or" -ForegroundColor DarkYellow
        Write-Host "          create config\libretime.conf." -ForegroundColor DarkYellow
        Write-Host "          Production settings require a valid config file." -ForegroundColor DarkYellow
    }
}

# ---------------------------------------------------------------------------
# Print startup banner
# ---------------------------------------------------------------------------
$HealthUrl  = "http://${BindHost}:${Port}/health"
$SwaggerUrl = "http://${BindHost}:${Port}/api/v2/schema/swagger-ui"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME API  — Waitress production server  (T17.1)" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Settings  : libretime_api.settings.prod" -ForegroundColor Gray
Write-Host "  Bind      : ${BindHost}:${Port}" -ForegroundColor White
Write-Host "  Threads   : $Threads" -ForegroundColor Gray
Write-Host "  Health    : $HealthUrl" -ForegroundColor Green
Write-Host "  Swagger   : $SwaggerUrl" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# ---------------------------------------------------------------------------
# Launch Waitress
# ---------------------------------------------------------------------------
& $Python -m libretime_api.waitress_serve `
    --host $BindHost `
    --port $Port `
    --threads $Threads
