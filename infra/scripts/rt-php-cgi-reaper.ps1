<#
.SYNOPSIS
    RASTATIME: stop php-cgi.exe processes that a stopped Apache left behind.

.DESCRIPTION
    RASTATIME 2026-10-22 (BACKLOG "Verwaiste php-cgi.exe nach Apache-Stopp",
    operator go for option (a)).  NSSM 2.24 stops RASTATIME-APACHE with
    Ctrl+C; the httpd child process shuts down, its mod_fcgid php-cgi.exe
    children do not, and NSSM's process-tree kill walks parent PIDs and no
    longer reaches them once the httpd child is gone.  The orphans serve
    nothing but keep memory, the old php.ini and file locks on C:\Tools\PHP
    (they blocked the folder swap of the PHP updates on 2026-10-21/22).

    A php-cgi.exe from -PhpDir counts as an orphan when its parent process
    is gone, is not httpd.exe, or started after it (a reused PID).  The
    php-cgi children of a running Apache are never touched, so the script
    is safe to run at any time.

    Before looking, it waits until -ServiceName has left StartPending /
    StopPending (at most -WaitSeconds): the stop trigger fires when NSSM
    receives STOP, and the httpd children go away up to 30 s later.

    Runs from the Task Scheduler as SYSTEM, triggered by the NSSM events of
    RASTATIME-APACHE in the Application log (1040 STOP/START control, 1008
    started - also after NSSM restarts a crashed Apache); see
    register-php-cgi-reaper.ps1.  Logs to C:\RASTATIME\logs\php-cgi-reaper.log.
    Always exits 0.
#>
[CmdletBinding()]
param(
    [string] $PhpDir = 'C:\Tools\PHP',
    [string] $ServiceName = 'RASTATIME-APACHE',
    [int] $WaitSeconds = 120,
    [string] $Trigger = 'manual',
    [switch] $DryRun
)
$ErrorActionPreference = 'Continue'
$log = 'C:\RASTATIME\logs\php-cgi-reaper.log'

function Write-Log([string] $msg) {
    try { Add-Content -Path $log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg) } catch { }
}

try {
    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    $status = 'unknown'
    while ($true) {
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        $status = if ($svc) { [string] $svc.Status } else { 'missing' }
        if ($status -notlike '*Pending' -or (Get-Date) -ge $deadline) { break }
        Start-Sleep -Seconds 2
    }

    $prefix = ($PhpDir.TrimEnd('\') + '\').ToLowerInvariant()
    $httpd = @{}
    Get-Process -Name httpd -ErrorAction SilentlyContinue | ForEach-Object { $httpd[$_.Id] = $_.StartTime }

    $orphans = @()
    $kept = 0
    foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='php-cgi.exe'" -ErrorAction SilentlyContinue)) {
        if (-not $p.ExecutablePath -or -not $p.ExecutablePath.ToLowerInvariant().StartsWith($prefix)) { continue }
        $parentStart = $httpd[[int] $p.ParentProcessId]
        if ($parentStart -and $parentStart -le $p.CreationDate) { $kept++; continue }
        $orphans += $p
    }

    $stopped = @()
    foreach ($p in $orphans) {
        $age = [int] ((Get-Date) - $p.CreationDate).TotalMinutes
        $what = "pid $($p.ProcessId) (parent $($p.ParentProcessId), $age min)"
        if ($DryRun) { $stopped += "$what [dry run]"; continue }
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            $stopped += $what
        } catch {
            $stopped += "$what FAILED: $($_.Exception.Message)"
        }
    }

    $line = "trigger=$Trigger service=$status kept=$kept orphans=$($orphans.Count)"
    if ($stopped) { $line += ' stopped: ' + ($stopped -join '; ') }
    Write-Log $line
    Write-Output $line
} catch {
    Write-Log "trigger=$Trigger ERROR $($_.Exception.Message)"
}
exit 0
