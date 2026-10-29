<#
.SYNOPSIS
    RASTATIME brute-force brakes: list blocked addresses, unblock one.

.DESCRIPTION
    RASTATIME 2026-10-06.  The same view as System Status -> "Blocked
    addresses", for the PowerShell (e.g. when the UI itself is what you are
    locked out of).  Three layers:
      web       cc_login_attempts (per address) / cc_subjs (per user name)
      harbor    the playout's DJ dial-in brake (127.0.0.1:8770/dj-auth/blocks)
      firewall  Windows Firewall rules "RASTATIME-Block <ip>" (watcher)

    Thresholds mirror constants.php (RASTATIME_LOGIN_*): address 10 failures
    / 15 min -> 15 min, user 20 / 60 min -> 5 min.

.EXAMPLE
    .\rt-blocks.ps1                      # list
    .\rt-blocks.ps1 -Unblock 203.0.113.5 # clear the address on every layer
    .\rt-blocks.ps1 -Unblock user:hostuser  # clear a user name's counter
#>
[CmdletBinding()]
param(
    [string] $Unblock = ''
)
$ErrorActionPreference = 'Stop'
$conf = 'C:\RASTATIME\config\rastatime.conf'
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'

function Get-DbPassword {
    # database: block of rastatime.conf; the value may be quoted
    $inDb = $false
    foreach ($line in Get-Content $conf) {
        if ($line -match '^\s*database:\s*$') { $inDb = $true; continue }
        if ($inDb -and $line -match '^\S') { $inDb = $false }
        if ($inDb -and $line -match '^\s*password:\s*(.+)$') {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    throw "database.password not found in $conf"
}

function Invoke-Sql([string] $sql) {
    $env:PGPASSWORD = Get-DbPassword
    try {
        & $psql -h localhost -U rastatime -d rastatime -At -F '|' -c $sql
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Get-WebRows {
    $rows = @()
    $ips = Invoke-Sql "SELECT ip, attempts, GREATEST(0, CEIL(15*60 - EXTRACT(EPOCH FROM (now() - last_attempt))))::int AS left_s FROM cc_login_attempts WHERE last_attempt > now() - interval '15 minutes' ORDER BY last_attempt DESC;"
    foreach ($l in $ips) {
        if (-not $l) { continue }
        $p = $l.Split('|')
        $left = if ([int]$p[1] -ge 10) { [int]$p[2] } else { 0 }
        $rows += [pscustomobject]@{ Layer = 'web'; Key = $p[0]; Failures = "$($p[1])/10"; Remaining = $left }
    }
    $users = Invoke-Sql "SELECT login, login_attempts, GREATEST(0, CEIL(5*60 - EXTRACT(EPOCH FROM (now() - login_attempt_at))))::int FROM cc_subjs WHERE login_attempt_at > now() - interval '60 minutes' AND COALESCE(login_attempts,0) > 0 ORDER BY login_attempt_at DESC;"
    foreach ($l in $users) {
        if (-not $l) { continue }
        $p = $l.Split('|')
        $left = if ([int]$p[1] -ge 20) { [int]$p[2] } else { 0 }
        $rows += [pscustomobject]@{ Layer = 'web-user'; Key = "user:$($p[0])"; Failures = "$($p[1])/20"; Remaining = $left }
    }
    return $rows
}

function Get-HarborRows {
    try {
        $d = Invoke-RestMethod -Uri 'http://127.0.0.1:8770/dj-auth/blocks' -TimeoutSec 2
    } catch { return @() }
    $rows = @()
    foreach ($b in $d.blocks) {
        $rows += [pscustomobject]@{ Layer = 'harbor'; Key = $b.address; Failures = "$($b.rejections_in_window)/$($b.limit)"; Remaining = [int]$b.blocked_seconds_left }
    }
    return $rows
}

function Get-FirewallRows {
    $rows = @()
    foreach ($r in (Get-NetFirewallRule -DisplayName 'RASTATIME-Block *' -ErrorAction SilentlyContinue)) {
        $ip = $r.DisplayName.Substring('RASTATIME-Block '.Length).Trim()
        $left = 0
        if ($r.Description -match 'until=([0-9T:\-+. ]+)') {
            try { $left = [int][Math]::Max(0, ([datetime]::Parse($Matches[1].Trim()) - (Get-Date)).TotalSeconds) } catch {}
        }
        $rows += [pscustomobject]@{ Layer = 'firewall'; Key = $ip; Failures = ($r.Description -replace '.*reason=', ''); Remaining = $left }
    }
    return $rows
}

if ($Unblock -ne '') {
    $key = $Unblock.Trim()
    if ($key -like 'user:*') {
        $login = $key.Substring(5).Replace("'", "''")
        Invoke-Sql "UPDATE cc_subjs SET login_attempts = 0, login_attempt_at = NULL WHERE login = '$login';" | Out-Null
        Write-Host "web: counter of user '$($key.Substring(5))' cleared"
    } elseif ($key -as [ipaddress]) {
        Invoke-Sql "DELETE FROM cc_login_attempts WHERE ip = '$key';" | Out-Null
        Write-Host "web: address cleared"
        try {
            $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8770/dj-auth/unblock' -Method Post -Body @{ address = $key } -TimeoutSec 2
            Write-Host ("harbor: " + $(if ($r.cleared) { 'cleared' } else { 'was not blocked' }))
        } catch { Write-Host "harbor: playout not reachable ($($_.Exception.Message))" }
        $rule = Get-NetFirewallRule -DisplayName "RASTATIME-Block $key" -ErrorAction SilentlyContinue
        if ($rule) { $rule | Remove-NetFirewallRule; Write-Host "firewall: rule removed" } else { Write-Host "firewall: no rule" }
    } else {
        throw "not an address and not user:<login>: $key"
    }
    Write-Host ''
}

$all = @(Get-WebRows) + @(Get-HarborRows) + @(Get-FirewallRows)
if ($all.Count -eq 0) {
    Write-Host 'No addresses are blocked or counting at the moment.'
} else {
    $all | ForEach-Object {
        $_ | Add-Member -NotePropertyName State -NotePropertyValue $(if ($_.Remaining -gt 0) { "blocked, $([Math]::Ceiling($_.Remaining / 60)) min left" } else { 'counting' }) -PassThru
    } | Format-Table Layer, Key, Failures, State -AutoSize
}

# RASTATIME 2026-10-08 - the allow list (System Status -> Allowed addresses;
# mirror file written by the web UI, change it there)
$allowFile = 'C:\RASTATIME\config\allowlist.txt'
$allowed = @()
if (Test-Path $allowFile) {
    $allowed = @(Get-Content $allowFile -ErrorAction SilentlyContinue | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
}
Write-Host ''
if ($allowed.Count -eq 0) {
    Write-Host 'Allowed addresses: none (System Status -> Allowed addresses).'
} else {
    Write-Host ('Allowed addresses (never braked, throttled or blocked): ' + ($allowed -join ', '))
}
