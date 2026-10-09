<#
.SYNOPSIS
    RASTATIME firewall watcher: turn persistent scanners and password
    hammering into temporary Windows Firewall rules.

.DESCRIPTION
    RASTATIME 2026-10-06 (go-live follow-up (c)).  Runs every 5 minutes
    from the Task Scheduler as SYSTEM.  Looks at the last 60 minutes (default) of
      * the HTTP logs  C:\Tools\Apache24\logs\access_log (port 80) and
                       C:\RASTATIME\logs\https-access-YYYYMMDD.log (port 443,
                       daily rotatelogs slices since 2026-10-09),
      * the playout log C:\RASTATIME\logs\playout-stdout.log (DJ harbor),
    and blocks a remote address for 24 hours when it
      * answered 4xx 50 times or more (401 "not signed in" does not count:
        a browser tab whose session expired polls the dashboard every
        minute and collected 60 x 401 in an hour - operator locked out
        2026-10-07), or
      * asked for 3 or more typical scanner paths (/.git, /.env, /wp-, ...), or
      * had 5 or more DJ logins rejected for a WRONG PASSWORD
        (too-early logins - "no-show" / "not-host" - never count).
    Rules are named "RASTATIME-Block <ip>" with "until=<time>; reason=..."
    in the description; expired rules are removed on every run.  Private
    (LAN) and loopback addresses are never blocked.  Everything is logged
    to C:\RASTATIME\logs\firewall-watch.log.

    Register (elevated):
      schtasks /create /tn "RASTATIME-FirewallWatch" /sc minute /mo 5 /ru SYSTEM /rl HIGHEST ^
        /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\rt-firewall-watch.ps1"
    Unblock by hand: System Status -> Blocked addresses, or rt-blocks.ps1 -Unblock <ip>.
#>
[CmdletBinding()]
param(
    [int] $WindowMinutes = 60,   # 2026-10-06: 10 caught nothing, scanners knock spread out
    [int] $BlockHours = 24,
    [int] $ErrorLimit = 50,
    [int] $ScannerLimit = 3,
    [int] $BadPasswordLimit = 5,
    [string] $AllowListPath = 'C:\RASTATIME\config\allowlist.txt',   # 2026-10-08: written by System Status -> Allowed addresses
    [switch] $DryRun
)
$ErrorActionPreference = 'Continue'
$log = 'C:\RASTATIME\logs\firewall-watch.log'
$prefix = 'RASTATIME-Block '
$now = Get-Date
$since = $now.AddMinutes(-$WindowMinutes)
$scannerPattern = '(/\.git|/\.env|/\.htpasswd|/\.aws|/wp-(admin|login|includes|content)|phpmyadmin|/cgi-bin/|/vendor/phpunit|/\.well-known/(?!acme-challenge)|/actuator|/solr/|/HNAP1|/boaform|/shell\?)'

function Write-Log([string] $msg) {
    Add-Content -Path $log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg)
}

# RASTATIME 2026-10-08 - the allow list (one address or CIDR network per
# line, '#' comments) from System Status -> Allowed addresses.  IPv4 networks
# are matched by prefix, IPv6 entries by exact address.
$allowEntries = @()
if (Test-Path $AllowListPath) {
    $allowEntries = @(Get-Content $AllowListPath -ErrorAction SilentlyContinue | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
}
function ConvertTo-IPv4Number([string] $dotted) {
    $b = ([IPAddress] $dotted).GetAddressBytes()
    return ([uint64] $b[0] * 16777216) + ([uint64] $b[1] * 65536) + ([uint64] $b[2] * 256) + [uint64] $b[3]
}
function Test-AllowedAddress([string] $ip) {
    $isV4 = $ip -match '^\d+\.\d+\.\d+\.\d+$'
    foreach ($entry in $allowEntries) {
        if ($entry -eq $ip) { return $true }
        if (-not $isV4) { continue }
        $m = [regex]::Match($entry, '^(\d+\.\d+\.\d+\.\d+)/(\d+)$')
        if (-not $m.Success) { continue }
        $bits = [int] $m.Groups[2].Value
        if ($bits -lt 0 -or $bits -gt 32) { continue }
        try { $net = ConvertTo-IPv4Number $m.Groups[1].Value; $addr = ConvertTo-IPv4Number $ip } catch { continue }
        $mask = if ($bits -eq 0) { [uint64] 0 } else { ([uint64] 4294967295 -shl (32 - $bits)) -band [uint64] 4294967295 }
        if (($net -band $mask) -eq ($addr -band $mask)) { return $true }
    }
    return $false
}

function Test-PrivateAddress([string] $ip) {
    if ($ip -match '^(127\.|10\.|192\.168\.|169\.254\.|0\.)') { return $true }
    if ($ip -match '^172\.(1[6-9]|2[0-9]|3[01])\.') { return $true }
    if ($ip -eq '::1' -or $ip -like 'fe80:*' -or $ip -like 'fc*' -or $ip -like 'fd*') { return $true }
    return $false
}

function Read-Tail([string] $path, [int] $lines = 20000) {
    if (-not (Test-Path $path)) { return @() }
    try { return Get-Content -Path $path -Tail $lines -ErrorAction Stop } catch { return @() }
}

# ---- 1. expire old rules ----------------------------------------------------
$active = @{}
foreach ($r in (Get-NetFirewallRule -DisplayName "$prefix*" -ErrorAction SilentlyContinue)) {
    $ip = $r.DisplayName.Substring($prefix.Length).Trim()
    $until = $null
    if ($r.Description -match 'until=([0-9T:\-+. ]+)') { try { $until = [datetime]::Parse($Matches[1].Trim()) } catch {} }
    if ($until -and $until -lt $now) {
        if (-not $DryRun) { $r | Remove-NetFirewallRule }
        Write-Log "expired: $ip (was until $until)"
    } else {
        $active[$ip] = $true
    }
}

# ---- 2. HTTP logs (Apache "common" / "combined") ----------------------------
$errors = @{}
$scanner = @{}
$months = @{ Jan=1; Feb=2; Mar=3; Apr=4; May=5; Jun=6; Jul=7; Aug=8; Sep=9; Oct=10; Nov=11; Dec=12 }
# RASTATIME 2026-10-09 - the HTTPS access log is written in daily slices
# (rotatelogs, https-access-YYYYMMDD.log): read the slices touched inside the
# window (today, and yesterday around midnight), plus the old single file
# while it still exists.
$httpsSlices = @(Get-ChildItem 'C:\RASTATIME\logs\https-access-*.log' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $since.AddDays(-1) } | Sort-Object LastWriteTime | Select-Object -ExpandProperty FullName)
foreach ($file in @('C:\Tools\Apache24\logs\access_log', 'C:\RASTATIME\logs\https-access.log') + $httpsSlices) {
    foreach ($line in (Read-Tail $file)) {
        if ($line -notmatch '^(\S+) \S+ \S+ \[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) [^\]]+\] "(?:\S+) (\S+)[^"]*" (\d{3})') { continue }
        $ip = $Matches[1]
        try { $ts = Get-Date -Year $Matches[4] -Month $months[$Matches[3]] -Day $Matches[2] -Hour $Matches[5] -Minute $Matches[6] -Second $Matches[7] } catch { continue }
        if ($ts -lt $since) { continue }
        if (Test-PrivateAddress $ip) { continue }
        $path = $Matches[8]
        $status = [int]$Matches[9]
        # 401 = the app's own "not signed in" answer to a stale tab's polls, never a scanner (2026-10-07)
        if ($status -ge 400 -and $status -lt 500 -and $status -ne 401) { $errors[$ip] = 1 + [int]$errors[$ip] }
        if ($path -match $scannerPattern) { $scanner[$ip] = 1 + [int]$scanner[$ip] }
    }
}

# ---- 3. playout: DJ logins rejected for a wrong password --------------------
$badpw = @{}
foreach ($line in (Read-Tail 'C:\RASTATIME\logs\playout-stdout.log' 5000)) {
    if ($line -notmatch '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*dj-auth: .* from (\S+) rejected \(bad password\)') { continue }
    try { $ts = [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss', $null) } catch { continue }
    if ($ts -lt $since) { continue }
    $ip = $Matches[2]
    if (Test-PrivateAddress $ip) { continue }
    $badpw[$ip] = 1 + [int]$badpw[$ip]
}

# ---- 4. decide and block -----------------------------------------------------
$candidates = @{}
foreach ($ip in $errors.Keys)  { if ($errors[$ip]  -ge $ErrorLimit)       { $candidates[$ip] = "4xx x$($errors[$ip]) in $WindowMinutes min" } }
foreach ($ip in $scanner.Keys) { if ($scanner[$ip] -ge $ScannerLimit)     { $candidates[$ip] = "scanner paths x$($scanner[$ip])" } }
foreach ($ip in $badpw.Keys)   { if ($badpw[$ip]   -ge $BadPasswordLimit) { $candidates[$ip] = "DJ bad password x$($badpw[$ip])" } }

$blocked = 0
foreach ($ip in $candidates.Keys) {
    if ($active.ContainsKey($ip)) { continue }
    if (-not ($ip -as [ipaddress])) { continue }
    if (Test-AllowedAddress $ip) { Write-Log "skipped $ip (allowed address; $($candidates[$ip]))"; continue }
    $until = $now.AddHours($BlockHours)
    $desc = "until=$($until.ToString('yyyy-MM-ddTHH:mm:ss')); reason=$($candidates[$ip])"
    if ($DryRun) {
        Write-Log "DRY RUN would block $ip ($desc)"
    } else {
        try {
            New-NetFirewallRule -DisplayName "$prefix$ip" -Direction Inbound -Action Block -RemoteAddress $ip -Profile Any -Description $desc -ErrorAction Stop | Out-Null
            Write-Log "blocked $ip ($desc)"
            $blocked++
        } catch {
            Write-Log "FAILED to block $ip : $($_.Exception.Message)"
        }
    }
}
Write-Log ("run: window {0} min, http addresses {1}, candidates {2}, new blocks {3}, active rules {4}{5}" -f $WindowMinutes, ($errors.Keys.Count + $scanner.Keys.Count), $candidates.Count, $blocked, $active.Count, $(if ($DryRun) { ' (dry run)' } else { '' }))
