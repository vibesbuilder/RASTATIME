# RASTATIME 2026-09-17 - automatic backup runner (work-order point 10,
# stage 3).  Register ONCE in the Windows Task Scheduler (elevated):
#
#   $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
#       -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\scripts\backup-auto.ps1"
#   $trigger = New-ScheduledTaskTrigger -Daily -At 03:30
#   Register-ScheduledTask -TaskName "RASTATIME-Backup" -Action $action `
#       -Trigger $trigger -User "SYSTEM" -RunLevel Highest
#
# The task may fire daily - the backup_auto command itself decides
# whether a run is due (Settings -> Backup -> Automatic backups) and
# prunes old ZIPs per the configured retention.  Output is appended to
# logs\backup-auto.log.

$ErrorActionPreference = "Continue"
$env:RASTATIME_CONFIG_FILEPATH = "C:\RASTATIME\config\rastatime.conf"
$env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.prod"
# Repo root on the module path so the soundcard app finds the shared
# "audio" package (cosmetic for backups, but keeps the log clean).
$env:PYTHONPATH = "C:\RASTATIME"
$python = "C:\RASTATIME\.venv\Scripts\python.exe"
$manage = "C:\RASTATIME\backend\api\rastatime_api\manage.py"
$log    = "C:\RASTATIME\logs\backup-auto.log"

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$stamp] backup_auto starting" | Out-File -FilePath $log -Append -Encoding utf8
& $python $manage backup_auto 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
$code = $LASTEXITCODE
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$stamp] backup_auto finished with exit code $code" | Out-File -FilePath $log -Append -Encoding utf8
exit $code
