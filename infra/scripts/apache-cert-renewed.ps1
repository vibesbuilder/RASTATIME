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
      wacs.exe ... --installation script --script "powershell.exe"
        --scriptparameters "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\apache-cert-renewed.ps1"
#>
$ErrorActionPreference = 'Stop'
$log = 'C:\RASTATIME\logs\cert-renewal.log'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
try {
    $test = & 'C:\Tools\Apache24\bin\httpd.exe' -t 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-Content $log "$stamp apache config test FAILED, not restarting: $test"
        exit 1
    }
    Restart-Service RASTATIME-APACHE
    Add-Content $log "$stamp certificate renewed, Apache restarted"
} catch {
    Add-Content $log "$stamp restart FAILED: $($_.Exception.Message)"
    exit 1
}
