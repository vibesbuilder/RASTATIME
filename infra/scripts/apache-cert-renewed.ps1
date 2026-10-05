<#
.SYNOPSIS
    win-acme installation step: restart Apache after a certificate renewal.

.DESCRIPTION
    RASTATIME 2026-10-05 (go-live stage 2).  win-acme writes the renewed
    PEM files into C:\RASTATIME\certs (store plugin "pemfiles"); Apache
    only reads them at start-up, so the renewal task calls this script
    (installation plugin "script").  Runs as the win-acme scheduled task
    (SYSTEM), hence no elevation prompt.

    Registered by:
      wacs.exe ... --installation script --script "C:\RASTATIME\infra\scripts\apache-cert-renewed.ps1"
    (win-acme runs .ps1 files through PowerShell itself.)

    2026-10-05: the first version ran httpd -t with 2>&1 under
    $ErrorActionPreference = 'Stop'; httpd prints "Syntax OK" on STDERR,
    PowerShell turned that into a terminating error and logged
    "restart FAILED: Syntax OK".  The config test now runs through cmd.exe
    so only the exit code counts.
#>
$log = 'C:\RASTATIME\logs\cert-renewal.log'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$httpd = 'C:\Tools\Apache24\bin\httpd.exe'

$ErrorActionPreference = 'Continue'
$test = cmd.exe /c "`"$httpd`" -t 2>&1"
$code = $LASTEXITCODE
if ($code -ne 0) {
    Add-Content $log "$stamp apache config test FAILED (exit $code), not restarting: $($test -join ' ')"
    exit 1
}

try {
    $ErrorActionPreference = 'Stop'
    Restart-Service RASTATIME-APACHE
    $svc = Get-Service RASTATIME-APACHE
    Add-Content $log "$stamp certificate renewed, Apache restarted (config test: $($test -join ' '); service $($svc.Status))"
    exit 0
} catch {
    Add-Content $log "$stamp restart FAILED: $($_.Exception.Message)"
    exit 1
}
