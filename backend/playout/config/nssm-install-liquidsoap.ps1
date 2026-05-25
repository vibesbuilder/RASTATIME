# =====================================================================
# nssm-install-liquidsoap.ps1
#
# RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase B.
#
# Installs Liquidsoap as a Windows service via NSSM, parallel to the
# existing RASTATIME-PLAYOUT service.  Operator decision 2026-05-25:
# eigener NSSM-Service (NICHT Pypo-spawned subprocess) — Liquidsoap
# kann unabhängig starten/stoppen, Crash isoliert von Pypo, NSSM
# restartet automatisch.
#
# Prerequisites:
#   * NSSM at C:\Tools\nssm\nssm.exe (or adjust $nssm below)
#   * Liquidsoap installed at C:\Tools\liquidsoap\
#   * rastatime.liq production script at C:\Tools\liquidsoap\rastatime.liq
#     (filled in Phase C from the template at
#      backend/playout/config/rastatime.liq.template)
#   * Log directory C:\rastatime\logs\ exists + is writable
#
# Run as Administrator:
#   .\nssm-install-liquidsoap.ps1
#
# To uninstall later:
#   & "C:\Tools\nssm\nssm.exe" remove RASTATIME-LIQUIDSOAP confirm
# =====================================================================

# ---- Configuration ----------------------------------------------------

$nssm        = "C:\Tools\nssm\nssm.exe"
$serviceName = "RASTATIME-LIQUIDSOAP"
$liquidsoap  = "C:\Tools\liquidsoap\liquidsoap.exe"
$script      = "C:\Tools\liquidsoap\rastatime.liq"
$workingDir  = "C:\Tools\liquidsoap"
$logDir      = "C:\rastatime\logs"

# ---- Sanity checks ----------------------------------------------------

if (-not (Test-Path $nssm)) {
    Write-Error "NSSM not found at $nssm.  Download from https://nssm.cc/ and unzip to C:\Tools\nssm\."
    exit 1
}
if (-not (Test-Path $liquidsoap)) {
    Write-Error "Liquidsoap not found at $liquidsoap.  See docs/operator/LIQUIDSOAP_PHASE0.md."
    exit 1
}
if (-not (Test-Path $script)) {
    Write-Warning "Production script not found at $script.  Service will install but fail to start until Phase C ships the real rastatime.liq."
}
if (-not (Test-Path $logDir)) {
    Write-Host "Creating log directory $logDir ..."
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

# ---- Install service --------------------------------------------------

Write-Host "Installing service $serviceName ..."
& $nssm install $serviceName $liquidsoap $script

# ---- Configure service ------------------------------------------------

# Working directory — Liquidsoap puts its cache here by default,
# so it must be writable by the service account.
& $nssm set $serviceName AppDirectory $workingDir

# Logging: stdout / stderr to rotated files in the central log dir
# (same dir Pypo + Icecast log to).
& $nssm set $serviceName AppStdout "$logDir\liquidsoap-stdout.log"
& $nssm set $serviceName AppStderr "$logDir\liquidsoap-stderr.log"
& $nssm set $serviceName AppRotateFiles 1
& $nssm set $serviceName AppRotateOnline 1
& $nssm set $serviceName AppRotateBytes 10485760    # 10 MB
& $nssm set $serviceName AppRotateSeconds 86400     # daily

# Auto-start with Windows; restart on crash with throttling so a
# crash-loop doesn't hammer Icecast.
& $nssm set $serviceName Start SERVICE_AUTO_START
& $nssm set $serviceName AppExit Default Restart
& $nssm set $serviceName AppRestartDelay 5000       # 5 s between restart attempts
& $nssm set $serviceName AppThrottle 10000          # if it restarts within 10 s, NSSM considers it failed

# Description shown in Windows services.msc.
& $nssm set $serviceName Description "RASTATIME Liquidsoap audio backend (Seamless-Bus-Mix Phase 2)"
& $nssm set $serviceName DisplayName "RASTATIME Liquidsoap"

# Optional: depend on Icecast service (if installed as service).
# Uncomment if your Icecast runs as a service named "Icecast2":
# & $nssm set $serviceName DependOnService "Icecast2"

# ---- Done — manual start ---------------------------------------------

Write-Host ""
Write-Host "Service '$serviceName' installed."
Write-Host "Inspect with: & '$nssm' status $serviceName"
Write-Host "Start with:   & '$nssm' start $serviceName"
Write-Host "             (or via services.msc)"
Write-Host ""
Write-Host "Then point Pypo at it by setting environment variable"
Write-Host "  RASTATIME_PLAYOUT_ENGINE=liquidsoap"
Write-Host "on the RASTATIME-PLAYOUT service and restarting it."
