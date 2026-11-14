# RASTATIME 2026-11-14 - measures energy and brightness of library tracks
# that have none yet (manage.py analyze_audio_features, ARCHITECTURE 23.115):
# new uploads a few minutes after the import, the whole library once after
# legacy migration 0085.
#
# Fired every ten minutes by the Windows task RASTATIME-AudioFeatures.
# Register it ONCE, in an elevated PowerShell:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\register-audio-features.ps1
#
# One run measures at most 1000 tracks or stops after 5 minutes (about 0.1 s
# per track, ffmpeg below normal priority).  A value set by hand in Edit
# Track is never replaced.  Lines for tracks that could not be measured and
# one summary line per busy run are appended to logs\audio-features.log; an
# idle run writes nothing.

param(
    [int] $Limit = 1000,
    [int] $MaxSeconds = 300
)
$ErrorActionPreference = "Continue"
$env:RASTATIME_CONFIG_FILEPATH = "C:\RASTATIME\config\rastatime.conf"
$env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.prod"
$env:PYTHONPATH = "C:\RASTATIME"
$env:PYTHONIOENCODING = "utf-8"
$python = "C:\RASTATIME\.venv\Scripts\python.exe"
$manage = "C:\RASTATIME\backend\api\rastatime_api\manage.py"
$log    = "C:\RASTATIME\logs\audio-features.log"

# ffmpeg where the analyzer and playout services find it (their PATH)
$ffmpegArgs = @()
if (Test-Path "C:\ffmpeg\bin\ffmpeg.exe") { $ffmpegArgs = @("--ffmpeg-dir", "C:\ffmpeg\bin") }

$output = & $python $manage analyze_audio_features --limit $Limit --max-seconds $MaxSeconds @ffmpegArgs 2>&1
$code = $LASTEXITCODE
$lines = @($output | ForEach-Object { "$_" } | Where-Object { $_.Trim() -ne "" -and $_ -notmatch "Soundcard manager" })
if ($lines.Count -gt 0 -or $code -ne 0) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    foreach ($line in $lines) {
        "[$stamp] $line" | Out-File -FilePath $log -Append -Encoding utf8
    }
    if ($code -ne 0 -and $lines.Count -eq 0) {
        "[$stamp] analyze_audio_features ended with exit code $code" | Out-File -FilePath $log -Append -Encoding utf8
    }
}
exit $code
