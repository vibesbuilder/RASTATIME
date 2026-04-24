#Requires -Version 5.1
<#
.SYNOPSIS
    Start the RASTATIME API in development mode.

.DESCRIPTION
    Activates the repo virtual environment (or uses PATH python), sets
    DJANGO_SETTINGS_MODULE to the dev settings (no config file required),
    adds the API and shared packages to PYTHONPATH, and launches Django's
    built-in dev server.

    The health endpoint is available at http://<host>:<port>/health
    without database access, so it responds even before migrations run.

.PARAMETER Host
    Bind address. Default: 127.0.0.1

.PARAMETER Port
    Bind port. Default: 8000

.EXAMPLE
    # From the repo root:
    powershell -ExecutionPolicy Bypass -File infra\scripts\dev\run-api.ps1

.EXAMPLE
    # Bind to all interfaces (useful for LAN testing):
    powershell -ExecutionPolicy Bypass -File infra\scripts\dev\run-api.ps1 -Host 0.0.0.0 -Port 8080

.NOTES
    Prerequisites (run bootstrap.ps1 if unsure):
        - Python 3.11+
        - PostgreSQL reachable at localhost:5432 (for all API routes other than /health)
        - Dependencies installed:  pip install -e backend\api -e backend\shared

    PostgreSQL credentials default to LibreTime's out-of-the-box values:
        host=localhost  port=5432  name=libretime  user=libretime  password=libretime
    Override via environment variables:
        RASTATIME_DB_HOST, RASTATIME_DB_PORT, RASTATIME_DB_NAME,
        RASTATIME_DB_USER, RASTATIME_DB_PASSWORD

    EXECUTION POLICY — see bootstrap.ps1 .NOTES for unblock options.
#>

[CmdletBinding()]
param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve repo root (script lives at infra\scripts\dev\)
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..\..\')).Path

# ---------------------------------------------------------------------------
# Locate python
# ---------------------------------------------------------------------------
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (Test-Path $VenvPython) {
    $Python = $VenvPython
    Write-Host "  [venv]  Using $Python" -ForegroundColor DarkCyan
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $PythonCmd) {
        Write-Host "[ERROR] python not found. Run bootstrap.ps1 for details." -ForegroundColor Red
        exit 1
    }
    $Python = $PythonCmd.Source
    Write-Host "  [PATH]  Using $Python" -ForegroundColor DarkYellow
    Write-Host "          Tip: create a venv with 'python -m venv .venv' and install deps." -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# PYTHONPATH — make libretime_api and libretime_shared importable without
# requiring an editable install.  An editable install is preferred because
# it also registers package metadata (importlib.metadata.version); without
# it VERSION falls back to "dev".
# ---------------------------------------------------------------------------
$ApiSrc    = Join-Path $RepoRoot 'backend\api'
$SharedSrc = Join-Path $RepoRoot 'backend\shared'

$existingPythonPath = if ($env:PYTHONPATH) { $env:PYTHONPATH } else { "" }
$env:PYTHONPATH = "$ApiSrc;$SharedSrc;$existingPythonPath"

# ---------------------------------------------------------------------------
# Django settings
# ---------------------------------------------------------------------------
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.dev"
$env:LIBRETIME_DEBUG         = "true"

# ---------------------------------------------------------------------------
# Print startup banner
# ---------------------------------------------------------------------------
$HealthUrl = "http://${BindHost}:${Port}/health"
$SwaggerUrl = "http://${BindHost}:${Port}/api/v2/schema/swagger-ui"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  RASTATIME API — development server                  " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Settings  : libretime_api.settings.dev" -ForegroundColor Gray
Write-Host "  Health    : $HealthUrl" -ForegroundColor Green
Write-Host "  Swagger   : $SwaggerUrl" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOTE: /health works without PostgreSQL." -ForegroundColor DarkYellow
Write-Host "        All other API routes require a running database." -ForegroundColor DarkYellow
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# ---------------------------------------------------------------------------
# Launch Django dev server
# ---------------------------------------------------------------------------
$ManagePy = Join-Path $ApiSrc 'libretime_api\manage.py'

if (-not (Test-Path $ManagePy)) {
    Write-Host "[ERROR] manage.py not found at: $ManagePy" -ForegroundColor Red
    exit 1
}

$bindAddr = $BindHost + ':' + $Port
& $Python $ManagePy runserver $bindAddr
