# RASTATIME locale build script.
#
# Compiles every legacy .po translation under
#   frontend/legacy/locale/<LANG>/LC_MESSAGES/rastatime.po
# into the corresponding binary .mo file that PHP gettext reads at runtime.
#
# Requires gettext's `msgfmt.exe` on PATH or at one of the fallback locations
# probed below.  Recommended install on Windows: mlocati gettext-iconv-windows
# (standalone, no MSYS2 / Cygwin required).  Download:
#   https://mlocati.github.io/articles/gettext-iconv-windows.html
# Recommended extract location: C:\Tools\gettext-iconv\
# (also probed: C:\Program Files\gettext-iconv\, C:\Program Files (x86)\...)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File infra\scripts\maintenance\build-locales.ps1
#
# After a successful run, restart Apache so PHP picks up the new .mo files
# (PHP's gettext extension caches them per-process).

param(
    [string]$MsgfmtPath = ''
)

$ErrorActionPreference = 'Stop'

# Locate msgfmt.exe.  Priority:
#   1. explicit -MsgfmtPath argument
#   2. on PATH
#   3. known fallback install locations
$candidates = @()
if ($MsgfmtPath -ne '') { $candidates += $MsgfmtPath }
$onPath = Get-Command msgfmt -ErrorAction SilentlyContinue
if ($onPath) { $candidates += $onPath.Source }
$candidates += 'C:\Tools\gettext-iconv\bin\msgfmt.exe'
$candidates += 'C:\Program Files\gettext-iconv\bin\msgfmt.exe'
$candidates += 'C:\Program Files (x86)\gettext-iconv\bin\msgfmt.exe'

$msgfmt = $null
foreach ($c in $candidates) {
    if (Test-Path $c) { $msgfmt = $c; break }
}
if ($null -eq $msgfmt) {
    Write-Host 'ERROR: msgfmt.exe not found.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Install one of:'
      Write-Host '  - mlocati gettext-iconv-windows (recommended, ~6 MB ZIP)'
    Write-Host '    https://mlocati.github.io/articles/gettext-iconv-windows.html'
    Write-Host '    Extract to: C:\Tools\gettext-iconv\'
    Write-Host '  - Chocolatey:  choco install gettext'
    Write-Host '  - winget:      winget install --id=GnuWin32.GetText'
    Write-Host ''
    Write-Host 'Or pass an explicit path:'
    Write-Host "  build-locales.ps1 -MsgfmtPath 'C:\path\to\msgfmt.exe'"
    exit 1
}

Write-Host "Using msgfmt: $msgfmt"

# Resolve repository root from this script's location:
#   <repo>\infra\scripts\maintenance\build-locales.ps1
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir '..\..\..')
$localeDir = Join-Path $repoRoot 'frontend\legacy\locale'

if (-not (Test-Path $localeDir)) {
    Write-Host "ERROR: locale directory not found at $localeDir" -ForegroundColor Red
    exit 1
}

# Active languages must stay in sync with
# frontend/legacy/application/models/Locale.php $locales.
$activeLanguages = @('en_US', 'de_DE', 'fr_FR', 'es_ES')

$built = 0
$skipped = 0
$failed = 0
foreach ($lang in $activeLanguages) {
    $po = Join-Path $localeDir "$lang\LC_MESSAGES\rastatime.po"
    $mo = Join-Path $localeDir "$lang\LC_MESSAGES\rastatime.mo"
    if (-not (Test-Path $po)) {
        Write-Host "  [SKIP]  $lang  (no .po file)" -ForegroundColor Yellow
        $skipped++
        continue
    }
    Write-Host "  [BUILD] $lang  $po"
    & $msgfmt --check-format --check-domain -o $mo $po
    if ($LASTEXITCODE -eq 0) {
        $built++
    } else {
        Write-Host "  [FAIL]  $lang  (msgfmt exit $LASTEXITCODE)" -ForegroundColor Red
        $failed++
    }
}

Write-Host ''
Write-Host "Done. built=$built skipped=$skipped failed=$failed"
if ($failed -gt 0) { exit 1 }

Write-Host ''
Write-Host 'Restart Apache (httpd) so PHP picks up the new .mo files.'
