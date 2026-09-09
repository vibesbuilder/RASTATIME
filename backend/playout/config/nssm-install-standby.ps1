# =====================================================================
# nssm-install-standby.ps1
#
# RASTATIME 2026-09-09 - standby source for the Icecast fallback mounts.
#
# A second, tiny Liquidsoap streams silence (or a configured loop) to
# /<mount>-standby for every configured stream output, with the same
# encoders as rastatime.liq.  icecast.xml points each public mount at
# its standby mount (<fallback-mount> + <fallback-override>), so when
# RASTATIME-LIQUIDSOAP restarts (planned restart at a track boundary,
# nightly window, memory limit) Icecast moves the listeners to the
# standby mount and back again instead of disconnecting them.
#
# The script standby.liq is rendered by RASTATIME-PLAYOUT at startup
# (libretime_playout.liquidsoap_config.render_standby_liq); this
# service only needs a restart when PLAYOUT logs that standby.liq
# changed (i.e. when the stream outputs change).
#
# Prerequisites:
#   * NSSM at C:\Tools\nssm\nssm.exe
#   * Liquidsoap at C:\Tools\liquidsoap\liquidsoap.exe
#   * C:\Tools\liquidsoap\standby.liq (rendered by PLAYOUT - start
#     PLAYOUT once with the new code before installing this service)
#   * icecast.xml with the three fallback mounts (see config/icecast.xml)
#
# Run as Administrator:
#   .\nssm-install-standby.ps1
#
# To uninstall later:
#   & "C:\Tools\nssm\nssm.exe" remove RASTATIME-STANDBY confirm
# =====================================================================

$nssm        = "C:\Tools\nssm\nssm.exe"
$serviceName = "RASTATIME-STANDBY"
$liquidsoap  = "C:\Tools\liquidsoap\liquidsoap.exe"
$script      = "C:\Tools\liquidsoap\standby.liq"
$workingDir  = "C:\Tools\liquidsoap"
$logDir      = "C:\rastatime\logs"

if (-not (Test-Path $nssm)) {
    Write-Error "NSSM not found at $nssm."
    exit 1
}
if (-not (Test-Path $liquidsoap)) {
    Write-Error "Liquidsoap not found at $liquidsoap."
    exit 1
}
if (-not (Test-Path $script)) {
    Write-Error "standby.liq not found at $script - start RASTATIME-PLAYOUT once (it renders the file), then rerun."
    exit 1
}
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

Write-Host "Installing service $serviceName ..."
& $nssm install $serviceName $liquidsoap $script
& $nssm set $serviceName AppDirectory $workingDir
& $nssm set $serviceName DisplayName "RASTATIME-STANDBY"
& $nssm set $serviceName Description "Streams silence to the /*-standby Icecast mounts so listeners survive a RASTATIME-LIQUIDSOAP restart."
& $nssm set $serviceName Start SERVICE_AUTO_START
& $nssm set $serviceName AppStdout "$logDir\standby-stdout.log"
& $nssm set $serviceName AppStderr "$logDir\standby-stdout.log"
& $nssm set $serviceName AppRotateFiles 1
& $nssm set $serviceName AppRotateBytes 10485760
& $nssm set $serviceName AppExit Default Restart
& $nssm set $serviceName AppRestartDelay 2000
& $nssm set $serviceName DependOnService RASTATIME-ICECAST

Write-Host "Starting service $serviceName ..."
& $nssm start $serviceName
& $nssm status $serviceName
Write-Host "Done.  The *-standby mounts are hidden (icecast.xml), so they do NOT appear on"
Write-Host "status-json.xsl; verify with http://127.0.0.1:8000/admin/listmounts (admin login)"
Write-Host "or a listener request such as  curl -s -o NUL -w '%{http_code}' --max-time 2 http://127.0.0.1:8000/rastatime-standby"
