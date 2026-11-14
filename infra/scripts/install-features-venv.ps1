<#
.SYNOPSIS
    Create or update the separate Python environment for tempo / key analysis.

.DESCRIPTION
    RASTATIME 2026-11-15 (audio features, stage 2).  Tempo and key are measured
    with librosa, which pulls numpy, scipy, numba and llvmlite.  They live in
    their own virtual environment, <Root>\.venv-features, so the production
    environment (<Root>\.venv) and its services never see them.  The API's
    analyze_audio_features command (task RASTATIME-AudioFeatures) starts
    backend\features\tempo_key.py with this environment's python; without it,
    tempo and key are simply skipped.

    Run once (about 420 MB from PyPI), and again after
    backend\features\requirements.txt changed.  No service has to be stopped
    or restarted, no elevation needed:

      powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\install-features-venv.ps1

    -Python names the base interpreter; by default the one the production
    environment was created from (pyvenv.cfg "home").
#>
[CmdletBinding()]
param(
    [string] $Root = 'C:\RASTATIME',
    [string] $Python = '',
    [string] $Ffmpeg = 'C:\ffmpeg\bin\ffmpeg.exe'
)
$ErrorActionPreference = 'Stop'

$venv = Join-Path $Root '.venv-features'
$requirements = Join-Path $Root 'backend\features\requirements.txt'
$worker = Join-Path $Root 'backend\features\tempo_key.py'

if (-not $Python) {
    $cfg = Join-Path $Root '.venv\pyvenv.cfg'
    if (Test-Path $cfg) {
        $home_ = (Get-Content $cfg | Where-Object { $_ -match '^\s*home\s*=' } | Select-Object -First 1) -replace '^\s*home\s*=\s*', ''
        if ($home_) { $Python = Join-Path $home_.Trim() 'python.exe' }
    }
}
if (-not $Python -or -not (Test-Path $Python)) {
    throw "No base Python found - pass -Python C:\path\to\python.exe"
}
Write-Host "Base interpreter: $Python"

$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating $venv"
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed ($LASTEXITCODE)" }
}

Write-Host "Installing $requirements"
& $venvPython -m pip install --disable-pip-version-check --no-input --require-virtualenv -r $requirements
if ($LASTEXITCODE -ne 0) { throw "pip install failed ($LASTEXITCODE)" }

# smoke test: the worker must start, warm up and announce itself
if (-not (Test-Path $Ffmpeg)) { $Ffmpeg = 'ffmpeg' }
$ready = '' | & $venvPython -I $worker --ffmpeg $Ffmpeg | Select-Object -First 1
if ($ready -notmatch '"ready": true') { throw "tempo_key.py did not start: $ready" }
Write-Host "OK: $ready"
