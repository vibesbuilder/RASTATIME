# RASTATIME 2026-09-18 - nightly log janitor (operator request LOGGING).
# Register ONCE in the Windows Task Scheduler (elevated):
#
#   $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
#       -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\scripts\log-janitor.ps1"
#   $trigger = New-ScheduledTaskTrigger -Daily -At 03:50
#   Register-ScheduledTask -TaskName "RASTATIME-LogJanitor" -Action $action `
#       -Trigger $trigger -User "SYSTEM" -RunLevel Highest
#   # pin to local wall-clock time (the cmdlet stores a UTC offset -> DST drift):
#   $task = Get-ScheduledTask -TaskName "RASTATIME-LogJanitor"
#   $task.Triggers[0].StartBoundary = (Get-Date -Format yyyy-MM-dd) + "T03:50:00"
#   Set-ScheduledTask -InputObject $task | Out-Null
#
# What it does, every night at 03:50 (after the 03:30 backup):
#   1. NSSM-rotated service slices (*-stdout-*.log / *-stderr-*.log) and
#      ffmpeg capture logs older than $KeepRawDays move into the monthly
#      ZIP logs\archive\logs-YYYY-MM.zip and the raw file is deleted.
#   2. Unrotated singles (liquidsoap.log, access.log, legacy.log, ...)
#      are swept the same way once they exceed $SweepOverMB - but only
#      when nothing holds them open (a locked file is skipped silently
#      and picked up after the next service restart frees it).
#   3. Monthly ZIPs older than $KeepArchiveDays are deleted.
# A one-line summary is appended to logs\log-janitor.log.

$ErrorActionPreference = "Continue"

$LogsDir         = "C:\RASTATIME\logs"
$ArchiveDir      = Join-Path $LogsDir "archive"
$JanitorLog      = Join-Path $LogsDir "log-janitor.log"
$KeepRawDays     = 7      # rotated slices stay readable this long
$SweepOverMB     = 50     # unrotated singles are swept above this size
$KeepArchiveDays = 183    # ~6 months of compressed history

if (-not (Test-Path $ArchiveDir)) { New-Item -ItemType Directory -Force $ArchiveDir | Out-Null }

function Test-Locked([string]$Path) {
    try {
        $fs = [System.IO.File]::Open($Path, 'Open', 'ReadWrite', 'None')
        $fs.Close()
        return $false
    } catch {
        return $true
    }
}

$now      = Get-Date
$swept    = 0
$sweptMB  = 0.0
$skipped  = 0

# ---- collect candidates -----------------------------------------------------
$cutoff = $now.AddDays(-$KeepRawDays)
# RASTATIME 2026-10-09 - the HTTPS host logs in daily rotatelogs slices
# (https-error-YYYYMMDD.log / https-access-YYYYMMDD.log): finished slices
# are archived like the service slices.  2026-10-14: the port-80 host too
# (http-error-YYYYMMDD.log / http-access-YYYYMMDD.log, httpd.conf).
$slices = Get-ChildItem $LogsDir -File -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match '-(stdout|stderr)-\d{8}T' -or $_.Name -like 'ffmpeg-*.log' -or $_.Name -match '^https?-(error|access)-\d{8}\.log$') -and
    $_.LastWriteTime -lt $cutoff
}
$singles = Get-ChildItem $LogsDir -File -Filter *.log -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -notmatch '-(stdout|stderr)-\d{8}T' -and
    $_.Name -notmatch '^https?-(error|access)-\d{8}\.log$' -and
    $_.Name -notlike 'ffmpeg-*' -and
    $_.Name -ne 'log-janitor.log' -and
    $_.Length -gt ($SweepOverMB * 1MB)
}

foreach ($f in @($slices) + @($singles)) {
    if ($null -eq $f) { continue }
    if (Test-Locked $f.FullName) { $skipped++; continue }
    $zip = Join-Path $ArchiveDir ("logs-{0:yyyy-MM}.zip" -f $now)
    # Unique entry name so repeated sweeps of e.g. liquidsoap.log never
    # collide inside the monthly ZIP.
    $entry = "{0}-swept-{1:yyyyMMdd-HHmmss}{2}" -f `
        [System.IO.Path]::GetFileNameWithoutExtension($f.Name), $now, $f.Extension
    $tmp = Join-Path $LogsDir $entry
    try {
        Rename-Item $f.FullName $tmp -ErrorAction Stop
        Compress-Archive -Path $tmp -DestinationPath $zip -Update -ErrorAction Stop
        Remove-Item $tmp -Force -Confirm:$false
        $swept++
        $sweptMB += [math]::Round($f.Length / 1MB, 1)
    } catch {
        # Put the file back if the rename worked but the zip failed.
        if ((Test-Path $tmp) -and -not (Test-Path $f.FullName)) {
            try { Rename-Item $tmp $f.FullName -ErrorAction Stop } catch {}
        }
        $skipped++
    }
}

# ---- prune old archives -----------------------------------------------------
$pruned = 0
Get-ChildItem $ArchiveDir -Filter "logs-*.zip" -File -ErrorAction SilentlyContinue | Where-Object {
    $_.LastWriteTime -lt $now.AddDays(-$KeepArchiveDays)
} | ForEach-Object { Remove-Item $_.FullName -Force -Confirm:$false; $pruned++ }

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$stamp] swept $swept file(s) / $sweptMB MB, skipped $skipped (locked/failed), pruned $pruned archive(s)" |
    Out-File -FilePath $JanitorLog -Append -Encoding utf8
