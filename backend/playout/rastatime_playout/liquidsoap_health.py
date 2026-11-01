"""
liquidsoap_health — what the preflight scanner needs to know about the
running Liquidsoap process.

RASTATIME 2026-09-05.  Two probes, both read-only:

* :func:`liquidsoap_process_info` — PID, start time and private bytes
  of ``liquidsoap.exe`` via PowerShell ``Get-Process`` (no extra
  dependency; the playout venv has no psutil).  Drives the
  ``liquidsoap_memory_high`` warning: the savonet Windows build leaks
  in ``Unix.select`` (see the template's ``request.queue_sync``
  comment), so an instance that grows past the threshold must be
  restarted before it exhausts the machine.

* :func:`render_endpoint_sessions` — which Windows render endpoint
  holds an audio session of a given process, via the Core Audio
  session API (``pycaw``/``comtypes``).  Drives the
  ``main_output_session_missing`` warning: on 2026-09-05 the live
  instance played its Main Output to the Realtek onboard jack for
  hours because the PortAudio device index had shifted between
  PLAYOUT's probe and Liquidsoap's open; nobody could see it.

Every function swallows its own errors and returns ``None`` — a probe
that cannot run must not turn into a warning.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

#: Private-bytes threshold (MB) above which the preflight warns.
MEMORY_WARN_ENV = "RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB"
DEFAULT_MEMORY_WARN_MB = 2048

#: Do not judge the output session before the process is this old —
#: PortAudio opens the device a few seconds after start.
MIN_PROCESS_AGE_SECONDS = 90.0


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    private_mb: float
    age_seconds: float
    #: The .liq the instance runs (from its command line), "" when
    #: unknown.  RASTATIME 2026-09-09: the standby source is a second
    #: liquidsoap.exe, so callers must tell the instances apart.
    script: str = ""


def memory_warn_threshold_mb() -> int:
    raw = os.environ.get(MEMORY_WARN_ENV, "").strip()
    if not raw:
        return DEFAULT_MEMORY_WARN_MB
    try:
        return max(256, int(raw))
    except ValueError:
        logger.warning(
            "%s=%r is not an integer — using %d.", MEMORY_WARN_ENV, raw, DEFAULT_MEMORY_WARN_MB
        )
        return DEFAULT_MEMORY_WARN_MB


_PS_QUERY = (
    # Command lines come from WMI (Get-Process has none), keyed by PID as
    # a string because Get-Process.Id is Int32 and WMI's ProcessId UInt32.
    "$cl = @{}; "
    "Get-CimInstance Win32_Process -Filter \"name='liquidsoap.exe'\" | "
    "ForEach-Object { $cl[[string]$_.ProcessId] = $_.CommandLine }; "
    "$ps = Get-Process liquidsoap -ErrorAction SilentlyContinue; "
    "foreach ($p in $ps) { "
    "$age = [math]::Round(((Get-Date) - $p.StartTime).TotalSeconds); "
    "$script = ''; $c = $cl[[string]$p.Id]; "
    "if ($c -and ($c -match '([^\\s\"]+\\.liq)')) { $script = $matches[1] }; "
    "Write-Output ($p.Id.ToString() + ' ' + "
    "[math]::Round($p.PrivateMemorySize64/1MB).ToString() + ' ' + "
    "$age.ToString() + ' ' + $script) }"
)


def liquidsoap_process_info(
    runner=subprocess.run,
) -> Optional[list[ProcessInfo]]:
    """
    All ``liquidsoap.exe`` processes, or None on error.  Since the
    standby source (2026-09-09) there are normally two; each carries
    the script it runs so :func:`main_instances` can pick the main one.
    """
    if sys.platform != "win32":
        return None
    try:
        proc = runner(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_QUERY],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Get-Process liquidsoap failed: %s", exc)
        return None
    if proc.returncode != 0:
        logger.debug("Get-Process liquidsoap exited %s: %s", proc.returncode, proc.stderr)
        return None
    infos: list[ProcessInfo] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split(None, 3)
        if len(parts) not in (3, 4):
            continue
        script = parts[3].strip() if len(parts) == 4 else ""
        try:
            infos.append(ProcessInfo(int(parts[0]), float(parts[1]), float(parts[2]), script))
        except ValueError:
            continue
    return infos


#: The main instance's script: the basename of
#: ``RASTATIME_LIQUIDSOAP_CONFIG_PATH`` (default rastatime.liq).
MAIN_SCRIPT_ENV = "RASTATIME_LIQUIDSOAP_CONFIG_PATH"
DEFAULT_MAIN_SCRIPT_NAME = "rastatime.liq"


def main_script_name() -> str:
    """Lower-case basename of the main instance's .liq."""
    raw = os.environ.get(MAIN_SCRIPT_ENV, "").strip()
    name = os.path.basename(raw.replace("\\", "/")) if raw else ""
    return (name or DEFAULT_MAIN_SCRIPT_NAME).lower()


def _script_basename(info) -> str:
    return os.path.basename((getattr(info, "script", "") or "").replace("\\", "/")).lower()


def main_instances(infos, script_name: Optional[str] = None) -> list[ProcessInfo]:
    """
    The processes that run the main script (RASTATIME 2026-09-09).

    Until the standby source there was one liquidsoap.exe and "the
    oldest process" was the production instance; the standby service
    started earlier than every later restart of the main one, so the
    planned-restart triggers and the preflight would have judged the
    standby.  Processes whose script is known and is not the main one
    are dropped.  When no process reports a script at all (older query,
    command line unavailable) every process counts, as before; when
    scripts are known but none is the main one, only the processes
    without a script remain candidates.
    """
    if not infos:
        return []
    wanted = (script_name or main_script_name()).lower()
    named = [i for i in infos if getattr(i, "script", "")]
    if not named:
        return list(infos)
    matching = [i for i in named if _script_basename(i) == wanted]
    if matching:
        return matching
    return [i for i in infos if not getattr(i, "script", "")]


def render_endpoint_sessions() -> Optional[dict[str, list[int]]]:
    """
    ``{endpoint friendly name: [pids with an audio session on it]}`` for
    every active render endpoint, or None when the Core Audio session
    API is unavailable (non-Windows, pycaw missing, COM error).
    """
    if sys.platform != "win32":
        return None
    try:
        import comtypes  # noqa: PLC0415
        from comtypes import CLSCTX_ALL  # noqa: PLC0415
        from pycaw.api.audiopolicy import (  # noqa: PLC0415
            IAudioSessionControl2,
            IAudioSessionManager2,
        )
        from pycaw.api.mmdeviceapi import IMMDeviceEnumerator  # noqa: PLC0415
        from pycaw.constants import (  # noqa: PLC0415
            DEVICE_STATE,
            CLSID_MMDeviceEnumerator,
            EDataFlow,
        )
        from pycaw.pycaw import AudioUtilities  # noqa: PLC0415
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Core Audio session API unavailable: %s", exc)
        return None

    result: dict[str, list[int]] = {}
    try:
        comtypes.CoInitialize()
        enumerator = comtypes.CoCreateInstance(
            CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
        )
        collection = enumerator.EnumAudioEndpoints(
            EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value
        )
        for i in range(collection.GetCount()):
            dev = collection.Item(i)
            name = AudioUtilities.CreateDevice(dev).FriendlyName or f"endpoint-{i}"
            pids: list[int] = []
            try:
                manager = dev.Activate(
                    IAudioSessionManager2._iid_, CLSCTX_ALL, None
                ).QueryInterface(IAudioSessionManager2)
                sessions = manager.GetSessionEnumerator()
                for j in range(sessions.GetCount()):
                    ctl = sessions.GetSession(j).QueryInterface(IAudioSessionControl2)
                    pid = int(ctl.GetProcessId())
                    if pid:
                        pids.append(pid)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("session enumeration failed for %s: %s", name, exc)
            result[name] = pids
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("render endpoint enumeration failed: %s", exc)
        return None
    return result


def endpoints_holding(sessions: dict[str, list[int]], pids: list[int]) -> list[str]:
    """Names of the endpoints on which any of ``pids`` has a session."""
    wanted = set(pids)
    return [name for name, holders in sessions.items() if wanted.intersection(holders)]


def endpoint_matches(expected: str, endpoint_name: str) -> bool:
    """
    Does the Core Audio endpoint ``endpoint_name`` denote the configured
    Main Output ``expected``?

    Settings → Local Machine stores the endpoint's short name
    (``"Tascam-Lautsprecher"``), the session API reports the friendly
    name with the device description appended
    (``"Tascam-Lautsprecher (US-16x08)"``).  Live 2026-09-05 17:51 an
    exact comparison flagged a correctly wired Tascam as missing.  So:
    equal, or the endpoint name continues the expected one with the
    parenthesised description, or the expected one is the full name.
    """
    exp = (expected or "").strip().lower()
    got = (endpoint_name or "").strip().lower()
    if not exp or not got:
        return False
    if exp == got:
        return True
    if got.startswith(exp) and got[len(exp) :].lstrip().startswith("("):
        return True
    return exp.startswith(got) and exp[len(got) :].lstrip().startswith("(")
