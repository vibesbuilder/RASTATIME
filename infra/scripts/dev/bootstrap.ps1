#Requires -Version 5.1
<#
.SYNOPSIS
    RASTATIME development environment bootstrap checker.

.DESCRIPTION
    Verifies that all required and optional dependencies are present on a
    Windows 11 developer machine.

    Required:
        - Python 3.11 or later
        - PostgreSQL (psql reachable on PATH or installed as a service)
        - RabbitMQ  (analyzer message queue + frontend upload dispatch)

    Optional:
        - VLC / libVLC  (not used: Liquidsoap is the only playout engine
          since 2026-09-10; the check is kept for older checkouts)

    Run once after cloning, and again after any major system change.

.EXAMPLE
    # Standard run (may need policy unblock first  - see NOTES)
    powershell -ExecutionPolicy Bypass -File infra\scripts\dev\bootstrap.ps1

.NOTES
    EXECUTION POLICY
    ----------------
    Windows may block unsigned scripts by default. Unblock with one of:

      A) Per-session bypass (safest, no system change):
            powershell -ExecutionPolicy Bypass -File infra\scripts\dev\bootstrap.ps1

      B) Current user only (persists, only affects your profile):
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

      C) Unblock this file only:
            Unblock-File -Path infra\scripts\dev\bootstrap.ps1
            .\infra\scripts\dev\bootstrap.ps1

    Exit codes:
        0  - all required dependencies found
        1  - one or more required dependencies missing
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Minimum versions
# ---------------------------------------------------------------------------
$MIN_PYTHON_MAJOR = 3
$MIN_PYTHON_MINOR = 11

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Banner {
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  RASTATIME  - Development Environment Bootstrap Check " -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-SectionHeader([string]$Title) {
    Write-Host ""
    Write-Host "  $Title" -ForegroundColor DarkCyan
    Write-Host "  $('-' * $Title.Length)" -ForegroundColor DarkCyan
}

function Write-Pass([string]$Label, [string]$Detail = "") {
    $suffix = if ($Detail) { "  ($Detail)" } else { "" }
    Write-Host "  [PASS] $Label$suffix" -ForegroundColor Green
}

function Write-Fail([string]$Label, [string]$Detail = "") {
    $suffix = if ($Detail) { "  ($Detail)" } else { "" }
    Write-Host "  [FAIL] $Label$suffix" -ForegroundColor Red
}

function Write-Skip([string]$Label, [string]$Detail = "") {
    $suffix = if ($Detail) { "  ($Detail)" } else { "" }
    Write-Host "  [SKIP] $Label$suffix" -ForegroundColor DarkYellow
}

function Write-Info([string]$Message) {
    Write-Host "         $Message" -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------

function Test-Python {
    <#
    Returns $true if a suitable python.exe is on PATH and meets the minimum
    version. Prints pass/fail with discovered version.
    #>
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        $cmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $cmd) {
        Write-Fail "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" "not found on PATH"
        Write-Info "Install from https://www.python.org/downloads/ (add to PATH)."
        return $false
    }

    $rawVersion = & $cmd.Source --version 2>&1
    # Output: "Python 3.x.y"
    if ($rawVersion -match 'Python\s+(\d+)\.(\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        $patch = [int]$Matches[3]
        $vstr  = "$major.$minor.$patch"
        if ($major -gt $MIN_PYTHON_MAJOR) {
            Write-Pass "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" "$vstr at $($cmd.Source)"
            return $true
        }
        if ($major -eq $MIN_PYTHON_MAJOR -and $minor -ge $MIN_PYTHON_MINOR) {
            Write-Pass "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" "$vstr at $($cmd.Source)"
            return $true
        }
        Write-Fail "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" "found $vstr  - too old"
        Write-Info "Upgrade from https://www.python.org/downloads/."
        return $false
    }

    Write-Fail "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" "could not parse version: $rawVersion"
    return $false
}


function Test-PostgreSQL {
    <#
    Returns $true if PostgreSQL is detectable via:
      1. psql / pg_isready on PATH, or
      2. a running Windows service matching 'postgresql*', or
      3. a default install directory under Program Files.
    #>

    # 1  - psql on PATH
    $psql = Get-Command psql -ErrorAction SilentlyContinue
    if ($psql) {
        $rawVer = & $psql.Source --version 2>&1
        Write-Pass "PostgreSQL (psql on PATH)" "$rawVer"
        return $true
    }

    # 2  - pg_isready on PATH (lighter check, no auth needed)
    $pgReady = Get-Command pg_isready -ErrorAction SilentlyContinue
    if ($pgReady) {
        Write-Pass "PostgreSQL (pg_isready on PATH)" $pgReady.Source
        return $true
    }

    # 3  - Windows service
    $svc = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue
    if ($svc) {
        $first = $svc | Select-Object -First 1
        Write-Pass "PostgreSQL (Windows service)" "$($first.Name)  - status: $($first.Status)"
        return $true
    }

    # 4  - Default install directory
    $pgBase = Join-Path $env:ProgramFiles 'PostgreSQL'
    if (Test-Path $pgBase) {
        $latest = Get-ChildItem $pgBase -Directory | Sort-Object Name -Descending | Select-Object -First 1
        if ($latest) {
            Write-Pass "PostgreSQL (install directory)" "$($latest.FullName)"
            return $true
        }
    }

    Write-Fail "PostgreSQL" "not found on PATH, not a service, not in Program Files"
    Write-Info "Download from https://www.postgresql.org/download/windows/"
    Write-Info "After install, add <PostgreSQL>\bin to PATH and restart this terminal."
    return $false
}


function Test-VLC {
    <#
    Returns $true if VLC / libVLC is detectable via:
      1. vlc.exe on PATH, or
      2. default install path under Program Files\VideoLAN\VLC, or
      3. registry key HKLM:\SOFTWARE\VideoLAN\VLC.
    libvlc.dll in the same directory confirms the SDK is present.
    #>

    # 1  - vlc on PATH
    $vlcCmd = Get-Command vlc -ErrorAction SilentlyContinue
    if ($vlcCmd) {
        $vlcDir = Split-Path $vlcCmd.Source
        $hasSdk = Test-Path (Join-Path $vlcDir 'libvlc.dll')
        $sdkNote = if ($hasSdk) { 'libvlc.dll present' } else { 'libvlc.dll NOT found' }
        if ($hasSdk) {
            Write-Pass "VLC on PATH [optional]" "$($vlcCmd.Source)  - $sdkNote"
        } else {
            Write-Skip "VLC on PATH [optional]" "$($vlcCmd.Source)  - $sdkNote (only needed for legacy engines)"
        }
        return $hasSdk
    }

    # 2  - Default install path
    $defaultPath = Join-Path $env:ProgramFiles 'VideoLAN\VLC\vlc.exe'
    if (Test-Path $defaultPath) {
        $vlcDir = Split-Path $defaultPath
        $hasSdk = Test-Path (Join-Path $vlcDir 'libvlc.dll')
        $sdkNote = if ($hasSdk) { 'libvlc.dll present' } else { 'libvlc.dll NOT found' }
        Write-Pass "VLC (Program Files) [optional]" "$defaultPath  - $sdkNote"
        return $hasSdk
    }

    # 3  - Registry
    $regPath = 'HKLM:\SOFTWARE\VideoLAN\VLC'
    if (Test-Path $regPath) {
        $installDir = (Get-ItemProperty $regPath -ErrorAction SilentlyContinue).InstallDir
        if ($installDir -and (Test-Path $installDir)) {
            $hasSdk = Test-Path (Join-Path $installDir 'libvlc.dll')
            $sdkNote = if ($hasSdk) { 'libvlc.dll present' } else { 'libvlc.dll NOT found' }
            Write-Pass "VLC (registry) [optional]" "$installDir  - $sdkNote"
            return $hasSdk
        }
    }

    Write-Skip "VLC / libVLC [optional]" "not found  - not needed (Liquidsoap is the only playout engine)"
    Write-Info "Production playout uses Liquidsoap; VLC is not required."
    return $false
}


function Test-RabbitMQ {
    <#
    Required check: the analyzer consumes a RabbitMQ queue and the PHP
    frontend dispatches upload messages to it (vhost /rastatime, port
    5672, credentials in libretime.conf's rabbitmq section).
    Detects via Windows service 'RabbitMQ' or rabbitmq-server on PATH.
    #>

    $svc = Get-Service -Name 'RabbitMQ' -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Pass "RabbitMQ (Windows service)" "status: $($svc.Status)"
        return $true
    }

    $cmd = Get-Command rabbitmq-server -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Pass "RabbitMQ (on PATH)" $cmd.Source
        return $true
    }

    Write-Fail "RabbitMQ" "not found (Windows service or rabbitmq-server on PATH)"
    Write-Info "Install RabbitMQ 4.x + Erlang OTP; create vhost /rastatime on port 5672"
    Write-Info "(credentials in libretime.conf's rabbitmq section).  If the service"
    Write-Info "crashes at start, reinstall it with an explicit RABBITMQ_BASE"
    Write-Info "(e.g. C:\ProgramData\RabbitMQ) via rabbitmq-service.bat remove/install."
    return $false
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Banner

Write-SectionHeader "Required dependencies"

$pythonOk    = Test-Python
$postgresOk  = Test-PostgreSQL
$rabbitOk    = Test-RabbitMQ

Write-SectionHeader "Optional dependencies"

$null = Test-VLC   # result not used in pass/fail count (legacy engines only)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "  ====================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "  ====================================================" -ForegroundColor Cyan
Write-Host ""

$failed = @()
if (-not $pythonOk)   { $failed += "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" }
if (-not $postgresOk) { $failed += "PostgreSQL" }
if (-not $rabbitOk)   { $failed += "RabbitMQ" }

if ($failed.Count -eq 0) {
    Write-Host "  All required dependencies found." -ForegroundColor Green
    Write-Host "  Next steps:" -ForegroundColor Green
    Write-Host "    1. Create a virtual env:  python -m venv .venv" -ForegroundColor Gray
    Write-Host "    2. Activate it:           .venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "    3. Install deps:          pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "    4. Run the API:           .\infra\scripts\dev\run-api.ps1" -ForegroundColor Gray
    Write-Host "    5. Run the worker:        .\infra\scripts\dev\run-worker.ps1" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "  Missing required dependencies:" -ForegroundColor Red
    foreach ($dep in $failed) {
        Write-Host "    - $dep" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  Fix the items above and re-run this script." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
