#Requires -Version 5.1
<#
.SYNOPSIS
    RASTATIME bootstrap checker: are the prerequisites of INSTALL.md §2 in place?

.DESCRIPTION
    Verifies the third-party components a RASTATIME machine needs before the
    code is installed (INSTALL.md §4 Step 2).  RASTATIME 2026-11-01: the
    check follows the production stack of INSTALL.md §2; the VLC check of
    the first developer setups is gone (Liquidsoap is the only playout
    engine since 2026-09-10).

    Required (a missing one is a [FAIL] and the script exits 1):
        - Python 3.11 or later                       INSTALL §2.1
        - PostgreSQL (psql on PATH, service or install dir)   §2.2
        - Liquidsoap  C:\Tools\liquidsoap\liquidsoap.exe      §2.3
        - RabbitMQ (Windows service or rabbitmq-server on PATH) §2.4
        - NSSM        C:\Tools\nssm\nssm.exe                  §2.5
        - Apache      C:\Tools\Apache24\bin\httpd.exe         §2.6
        - PHP         C:\Tools\PHP\php.exe                    §2.6
        - Icecast     C:\Tools\Icecast\bin\icecast.exe        §2.7
        - FFmpeg      C:\ffmpeg\bin\ffmpeg.exe + ffprobe.exe  §2.8

    Optional (reported, never fatal):
        - Composer    C:\Tools\composer\composer.phar (needed for a git
          checkout, not for the release frontend zip)       §2.6 / Step 4b
        - Git on PATH (clone / update)                       Step 1

    Tool paths follow INSTALL.md's production layout; a tool found on PATH
    instead is accepted and reported with its location.

.EXAMPLE
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
# Minimum versions and production paths (INSTALL.md §2 / §3)
# ---------------------------------------------------------------------------
$MIN_PYTHON_MAJOR = 3
$MIN_PYTHON_MINOR = 11

$TOOLS = 'C:\Tools'

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
function Write-Banner {
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  RASTATIME  - Bootstrap Check (INSTALL.md section 2)  " -ForegroundColor Cyan
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


function Test-RabbitMQ {
    <#
    Required check: the analyzer consumes a RabbitMQ queue and the PHP
    frontend dispatches upload messages to it (vhost /rastatime, port
    5672, credentials in rastatime.conf's rabbitmq section).
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
    Write-Info "(credentials in rastatime.conf's rabbitmq section).  If the service"
    Write-Info "crashes at start, reinstall it with an explicit RABBITMQ_BASE"
    Write-Info "(e.g. C:\ProgramData\RabbitMQ) via rabbitmq-service.bat remove/install."
    return $false
}


function Test-Tool {
    <#
    Generic check for a third-party binary (RASTATIME 2026-11-01).

    Looks at the production path from INSTALL.md first, then on PATH.  With
    -VersionArgs the binary is run and the first line of its output is
    shown.  -Optional turns a miss into [SKIP] instead of [FAIL].  Returns
    $true when the tool was found.
    #>
    param(
        [Parameter(Mandatory)] [string] $Label,
        [Parameter(Mandatory)] [string] $ExpectedPath,
        [string]   $PathCommand = '',
        [string[]] $VersionArgs = @(),
        [string]   $Hint = '',
        [string]   $Section = '',
        [switch]   $Optional
    )
    $found = $null
    if (Test-Path $ExpectedPath) {
        $found = $ExpectedPath
    } elseif ($PathCommand) {
        $cmd = Get-Command $PathCommand -ErrorAction SilentlyContinue
        if ($cmd) { $found = $cmd.Source }
    }
    $tag = if ($Section) { "$Label  [INSTALL $Section]" } else { $Label }
    if ($found) {
        $detail = $found
        if ($VersionArgs.Count -gt 0) {
            try {
                $out = & $found @VersionArgs 2>&1 | Select-Object -First 1
                if ($out) { $detail = "$found  - $out" }
            } catch {
                # a version probe that fails is not a missing tool
            }
        }
        Write-Pass $tag $detail
        return $true
    }
    if ($Optional) {
        Write-Skip "$tag [optional]" "not at $ExpectedPath$(if ($PathCommand) { " and not on PATH" })"
    } else {
        Write-Fail $tag "not at $ExpectedPath$(if ($PathCommand) { " and not on PATH" })"
    }
    if ($Hint) { Write-Info $Hint }
    return $false
}


function Test-ComposerPhar {
    <#
    Composer is a .phar run through PHP, so the version probe needs php.exe.
    Optional: the release frontend zip ships vendor\, a git checkout needs
    composer for INSTALL Step 4b.
    #>
    $phar = Join-Path $TOOLS 'composer\composer.phar'
    $php  = Join-Path $TOOLS 'PHP\php.exe'
    if (Test-Path $phar) {
        $detail = $phar
        if (Test-Path $php) {
            try {
                $out = & $php $phar --version 2>&1 | Select-Object -First 1
                if ($out) { $detail = "$phar  - $out" }
            } catch { }
        }
        Write-Pass "Composer  [INSTALL 2.6 / Step 4b] [optional]" $detail
        return $true
    }
    $cmd = Get-Command composer -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Pass "Composer (on PATH)  [INSTALL 2.6 / Step 4b] [optional]" $cmd.Source
        return $true
    }
    Write-Skip "Composer  [INSTALL 2.6 / Step 4b] [optional]" "not at $phar and not on PATH"
    Write-Info "Needed for a git checkout (frontend\legacy vendor\); the release frontend zip ships vendor\."
    return $false
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Banner

Write-SectionHeader "Required dependencies"

$pythonOk    = Test-Python
$postgresOk  = Test-PostgreSQL
$liquidsoapOk = Test-Tool -Label 'Liquidsoap 2.4.6' -Section '2.3' `
    -ExpectedPath (Join-Path $TOOLS 'liquidsoap\liquidsoap.exe') -PathCommand 'liquidsoap' -VersionArgs @('--version') `
    -Hint 'Unzip the official win64 build to C:\Tools\liquidsoap\ (rastatime.liq is rendered into the same folder).'
$rabbitOk    = Test-RabbitMQ
$nssmOk      = Test-Tool -Label 'NSSM' -Section '2.5' `
    -ExpectedPath (Join-Path $TOOLS 'nssm\nssm.exe') -PathCommand 'nssm' `
    -Hint 'Download from https://nssm.cc/ and unzip the win64 nssm.exe to C:\Tools\nssm\.'
$apacheOk    = Test-Tool -Label 'Apache httpd 2.4' -Section '2.6' `
    -ExpectedPath (Join-Path $TOOLS 'Apache24\bin\httpd.exe') -PathCommand 'httpd' -VersionArgs @('-v') `
    -Hint 'Apache Lounge Win64 VS18 zip to C:\Tools\Apache24 (INSTALL_APACHE.md); needs the VC++ redistributable.'
$phpOk       = Test-Tool -Label 'PHP 8.x' -Section '2.6' `
    -ExpectedPath (Join-Path $TOOLS 'PHP\php.exe') -PathCommand 'php' -VersionArgs @('-v') `
    -Hint 'PHP NTS x64 zip to C:\Tools\PHP (INSTALL_APACHE.md).'
$icecastOk   = Test-Tool -Label 'Icecast 2.5' -Section '2.7' `
    -ExpectedPath (Join-Path $TOOLS 'Icecast\bin\icecast.exe') -PathCommand 'icecast' -VersionArgs @('-v') `
    -Hint 'Icecast win64 build to C:\Tools\Icecast\ so that bin\icecast.exe exists.'
$ffmpegOk    = Test-Tool -Label 'FFmpeg' -Section '2.8' `
    -ExpectedPath 'C:\ffmpeg\bin\ffmpeg.exe' -PathCommand 'ffmpeg' -VersionArgs @('-version') `
    -Hint 'Extract a release build so that C:\ffmpeg\bin\ffmpeg.exe exists (the service installers prepend exactly that folder to PATH).'
$ffprobeOk   = Test-Tool -Label 'FFprobe (analyzer durations)' -Section '2.8' `
    -ExpectedPath 'C:\ffmpeg\bin\ffprobe.exe' -PathCommand 'ffprobe' -VersionArgs @('-version')

Write-SectionHeader "Optional dependencies"

$null = Test-ComposerPhar
$null = Test-Tool -Label 'Git' -Section 'Step 1' -ExpectedPath 'C:\Program Files\Git\cmd\git.exe' -PathCommand 'git' -VersionArgs @('--version') -Optional `
    -Hint 'Only needed to clone or update a checkout; a release archive needs no git.'

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "  ====================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "  ====================================================" -ForegroundColor Cyan
Write-Host ""

$failed = @()
if (-not $pythonOk)     { $failed += "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+" }
if (-not $postgresOk)   { $failed += "PostgreSQL" }
if (-not $liquidsoapOk) { $failed += "Liquidsoap" }
if (-not $rabbitOk)     { $failed += "RabbitMQ" }
if (-not $nssmOk)       { $failed += "NSSM" }
if (-not $apacheOk)     { $failed += "Apache httpd" }
if (-not $phpOk)        { $failed += "PHP" }
if (-not $icecastOk)    { $failed += "Icecast" }
if (-not $ffmpegOk)     { $failed += "FFmpeg" }
if (-not $ffprobeOk)    { $failed += "FFprobe" }

if ($failed.Count -eq 0) {
    Write-Host "  All required dependencies found." -ForegroundColor Green
    Write-Host "  Next steps (INSTALL.md section 4):" -ForegroundColor Green
    Write-Host "    3. Create a virtual env:  python -m venv .venv" -ForegroundColor Gray
    Write-Host "    4. Install the backend:   pip install -r requirements.txt, then the editable packages" -ForegroundColor Gray
    Write-Host "    4b. Frontend packages:    composer install in frontend\legacy" -ForegroundColor Gray
    Write-Host "    5. Configuration:         config\rastatime.conf from the example" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "  Missing required dependencies:" -ForegroundColor Red
    foreach ($dep in $failed) {
        Write-Host "    - $dep" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  Fix the items above (INSTALL.md section 2) and re-run this script." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
