<#
.SYNOPSIS
    Run the RASTATIME test suites with the environment this machine needs.

.DESCRIPTION
    RASTATIME 2026-10-16.  The suites need a few environment variables that
    are easy to forget:
      * LIBRETIME_CONFIG_FILEPATH - the API tests build their test database
        from the real libretime.conf (user, password, host); without it the
        testing settings fall back to the upstream defaults and every
        django_db test errors with "password authentication failed".
      * PYTHONUTF8=1 - the test-database setup otherwise dies with a
        UnicodeDecodeError on the German PostgreSQL messages.
      * PYTHONPATH - the root unit tests and the playout tests import the
        packages from the checkout, not from the editable install.
      * --basetemp - pytest's default temp dir is not writable here.
    Nothing is printed from the configuration file.

.PARAMETER Suite
    api | playout | unit | all (default all).

.PARAMETER Path
    Optional test path or node id inside the suite, e.g.
    libretime_api/storage/tests/management/commands/test_bulk_import.py

.PARAMETER PytestArgs
    Extra arguments handed to pytest unchanged (e.g. -k name, -x).

.EXAMPLE
    .\scripts\run_tests.ps1 -Suite api
    .\scripts\run_tests.ps1 -Suite api -Path libretime_api/storage -PytestArgs -x
    .\scripts\run_tests.ps1            # all three suites
#>
param(
    [ValidateSet('api', 'playout', 'unit', 'all')]
    [string]$Suite = 'all',
    [string]$Path = '',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "venv python not found: $python" }

$config = Join-Path $root 'config\libretime.conf'
if (-not (Test-Path $config)) { throw "libretime.conf not found: $config" }

$baseTemp = Join-Path $env:TEMP ('rastatime-pytest-' + [IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force $baseTemp | Out-Null

$env:LIBRETIME_CONFIG_FILEPATH = $config
$env:PYTHONUTF8 = '1'

$failed = 0
function Invoke-Suite($name, $workDir, $pythonPath, $target) {
    Write-Host "== $name" -ForegroundColor Cyan
    $env:PYTHONPATH = $pythonPath
    Push-Location (Join-Path $root $workDir)
    try {
        $args = @('-m', 'pytest', $target, '-q', '-p', 'no:logging', "--basetemp=$baseTemp\$name") + $script:PytestArgs
        & $python @args
        if ($LASTEXITCODE -ne 0) { $script:failed++ }
    } finally {
        Pop-Location
    }
}

$sep = [IO.Path]::PathSeparator
if ($Suite -in @('api', 'all')) {
    $target = if ($Path) { $Path } else { 'libretime_api' }
    Invoke-Suite 'api' 'backend\api' '' $target
}
if ($Suite -in @('playout', 'all')) {
    $target = if ($Path) { $Path } else { 'tests' }
    Invoke-Suite 'playout' 'backend\playout' ((Join-Path $root 'backend\playout') + $sep + (Join-Path $root 'backend\api') + $sep + (Join-Path $root 'backend\shared')) $target
}
if ($Suite -in @('unit', 'all')) {
    $target = if ($Path) { $Path } else { 'tests\unit' }
    Invoke-Suite 'unit' '.' ((Join-Path $root 'backend\api') + $sep + (Join-Path $root 'backend\shared') + $sep + $root) $target
}

Remove-Item -Recurse -Force $baseTemp -ErrorAction SilentlyContinue
if ($failed -gt 0) { Write-Host "$failed suite(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'all requested suites passed' -ForegroundColor Green
