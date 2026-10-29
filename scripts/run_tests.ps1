<#
.SYNOPSIS
    Run the RASTATIME test suites with the environment this machine needs.

.DESCRIPTION
    RASTATIME 2026-10-16.  The suites need a few environment variables that
    are easy to forget:
      * RASTATIME_CONFIG_FILEPATH - the API tests build their test database
        from the real rastatime.conf (user, password, host); without it the
        testing settings fall back to the upstream defaults and every
        django_db test errors with "password authentication failed".
      * PYTHONUTF8=1 - the test-database setup otherwise dies with a
        UnicodeDecodeError on the German PostgreSQL messages.
      * PYTHONPATH - the root unit tests and the playout tests import the
        packages from the checkout, not from the editable install.
      * --basetemp - pytest's default temp dir is not writable here.
      * log_cli=false - the api and playout pyproject.toml switch live
        DEBUG logging on; the runner turns it off per run (and keeps the
        logging plugin, i.e. the caplog fixture, loaded).
    Nothing is printed from the configuration file.

.PARAMETER Suite
    api | playout | unit | all (default all).

.PARAMETER Path
    Optional test path or node id inside the suite, e.g.
    rastatime_api/storage/tests/management/commands/test_bulk_import.py

.PARAMETER PytestArgs
    Extra arguments handed to pytest unchanged (e.g. -k name, -x).

.EXAMPLE
    .\scripts\run_tests.ps1 -Suite api
    .\scripts\run_tests.ps1 -Suite api -Path rastatime_api/storage -PytestArgs -x
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

# A pre-set RASTATIME_CONFIG_FILEPATH wins (a git worktree has no config\
# of its own); otherwise the checkout's rastatime.conf.
$config = if ($env:RASTATIME_CONFIG_FILEPATH) { $env:RASTATIME_CONFIG_FILEPATH } else { Join-Path $root 'config\rastatime.conf' }
if (-not (Test-Path $config)) { throw "rastatime.conf not found: $config" }

$baseTemp = Join-Path $env:TEMP ('rastatime-pytest-' + [IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force $baseTemp | Out-Null

$env:RASTATIME_CONFIG_FILEPATH = $config
$env:PYTHONUTF8 = '1'

$failed = 0
function Invoke-Suite($name, $workDir, $pythonPath, $target) {
    Write-Host "== $name" -ForegroundColor Cyan
    $env:PYTHONPATH = $pythonPath
    Push-Location (Join-Path $root $workDir)
    try {
        # backend\api and backend\playout set log_cli = true (DEBUG) in their
        # pyproject.toml, which floods the console with live log lines.
        # Turn that option off instead of unloading pytest's logging plugin
        # ('-p no:logging', 2026-10-16 .. 2026-10-22): the plugin also owns
        # the caplog fixture, and without it every caplog-based test errors.
        $args = @('-m', 'pytest', $target, '-q', '-o', 'log_cli=false', "--basetemp=$baseTemp\$name") + $script:PytestArgs
        & $python @args
        if ($LASTEXITCODE -ne 0) { $script:failed++ }
    } finally {
        Pop-Location
    }
}

$sep = [IO.Path]::PathSeparator
if ($Suite -in @('api', 'all')) {
    $target = if ($Path) { $Path } else { 'rastatime_api' }
    Invoke-Suite 'api' 'backend\api' '' $target
}
if ($Suite -in @('playout', 'all')) {
    $target = if ($Path) { $Path } else { 'tests' }
    Invoke-Suite 'playout' 'backend\playout' ((Join-Path $root 'backend\playout') + $sep + (Join-Path $root 'backend\api') + $sep + (Join-Path $root 'backend\shared')) $target
}
if ($Suite -in @('unit', 'all')) {
    $target = if ($Path) { $Path } else { 'tests\unit' }
    # backend\playout as well: the root unit tests import rastatime_playout,
    # which must come from THIS checkout (a worktree), not from the editable
    # install that points at C:\RASTATIME.
    Invoke-Suite 'unit' '.' ((Join-Path $root 'backend\api') + $sep + (Join-Path $root 'backend\shared') + $sep + (Join-Path $root 'backend\playout') + $sep + $root) $target
}

Remove-Item -Recurse -Force $baseTemp -ErrorAction SilentlyContinue
if ($failed -gt 0) { Write-Host "$failed suite(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'all requested suites passed' -ForegroundColor Green
