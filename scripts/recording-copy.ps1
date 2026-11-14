# RASTATIME 2026-11-14 - copies finished show recordings to the folder set
# under Settings -> Local Machine -> Show Recording -> "Copy finished
# recordings to" (usually a network folder where the show makers pick up
# their recordings).
#
# Fired every two minutes by the Windows task RASTATIME-RecordingCopy.
# Register it ONCE, in an elevated PowerShell, under an account that may
# write to the target (the RASTATIME services run as SYSTEM, which has no
# access to a network share):
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\register-recording-copy.ps1 -User <account>
#
# The command copies each recording once (ledger in cc_pref), never
# deletes or overwrites anything at the target and does nothing while the
# setting is empty.  Lines for copied files and errors are appended to
# logs\recording-copy.log; an idle run writes nothing.

$ErrorActionPreference = "Continue"
$env:RASTATIME_CONFIG_FILEPATH = "C:\RASTATIME\config\rastatime.conf"
$env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.prod"
$env:PYTHONPATH = "C:\RASTATIME"
$env:PYTHONIOENCODING = "utf-8"
$python = "C:\RASTATIME\.venv\Scripts\python.exe"
$manage = "C:\RASTATIME\backend\api\rastatime_api\manage.py"
$log    = "C:\RASTATIME\logs\recording-copy.log"

$output = & $python $manage recording_copy 2>&1
$code = $LASTEXITCODE
$lines = @($output | ForEach-Object { "$_" } | Where-Object { $_.Trim() -ne "" -and $_ -notmatch "Soundcard manager" })
if ($lines.Count -gt 0 -or $code -ne 0) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    foreach ($line in $lines) {
        "[$stamp] $line" | Out-File -FilePath $log -Append -Encoding utf8
    }
    if ($code -ne 0 -and $lines.Count -eq 0) {
        "[$stamp] recording_copy ended with exit code $code" | Out-File -FilePath $log -Append -Encoding utf8
    }
}
exit $code
