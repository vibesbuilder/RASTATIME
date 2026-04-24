#Requires -Version 5.1
<#
.SYNOPSIS
    Start the RASTATIME background worker in development mode.

.DESCRIPTION
    Activates the repo virtual environment (or uses PATH python), adds the
    backend packages to PYTHONPATH, and runs the rastatime_worker package as
    a module (python -m rastatime_worker).

    In dev mode the worker is a stub that logs "idle" every few seconds.
    A real JobRunner implementation replaces this in Phase 8 (T16.x).

.PARAMETER IdleInterval
    Seconds between idle heartbeat log lines. Default: 5

.EXAMPLE
    # From the repo root:
    .\infra\scripts\dev\run-worker.ps1

.NOTES
    EXECUTION POLICY - see bootstrap.ps1 .NOTES for unblock options.
    This script does NOT require Administrator rights.
#>

[CmdletBinding()]
param(
    [double]$IdleInterval = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve repo root (script lives at infra\scripts\dev\)
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..\..')).Path

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
        Write-Host '[ERROR] python not found. Run bootstrap.ps1 for details.' -ForegroundColor Red
        exit 1
    }
    $Python = $PythonCmd.Source
    Write-Host "  [PATH]  Using $Python" -ForegroundColor DarkYellow
    Write-Host '          Tip: create a venv with python -m venv .venv and install deps.' -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# PYTHONPATH - make rastatime_worker and libretime_shared importable
# ---------------------------------------------------------------------------
$BackendSrc = Join-Path $RepoRoot 'backend'
$SharedSrc  = Join-Path $RepoRoot 'backend\shared'

$existingPythonPath = if ($env:PYTHONPATH) { $env:PYTHONPATH } else { '' }
$env:PYTHONPATH = $BackendSrc + ';' + $SharedSrc + ';' + $existingPythonPath

# ---------------------------------------------------------------------------
# Print startup banner
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '======================================================' -ForegroundColor Cyan
Write-Host '  RASTATIME Worker  - development stub               ' -ForegroundColor Cyan
Write-Host '======================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "  Module        : rastatime_worker" -ForegroundColor Gray
Write-Host "  Mode          : dev stub (idle heartbeat loop)" -ForegroundColor Gray
Write-Host "  Idle interval : $IdleInterval s" -ForegroundColor Gray
Write-Host ''
Write-Host '  Press Ctrl+C to stop.' -ForegroundColor Gray
Write-Host ''

# ---------------------------------------------------------------------------
# Launch worker
# ---------------------------------------------------------------------------
& $Python -m rastatime_worker --idle-interval $IdleInterval
