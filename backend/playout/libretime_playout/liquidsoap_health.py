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
from typing import Dict, List, Optional

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


def memory_warn_threshold_mb() -> int:
    raw = os.environ.get(MEMORY_WARN_ENV, "").strip()
    if not raw:
        return DEFAULT_MEMORY_WARN_MB
    try:
        return max(256, int(raw))
    except ValueError:
        logger.warning("%s=%r is not an integer — using %d.", MEMORY_WARN_ENV, raw, DEFAULT_MEMORY_WARN_MB)
        return DEFAULT_MEMORY_WARN_MB


_PS_QUERY = (
    "$ps = Get-Process liquidsoap -ErrorAction SilentlyContinue; "
    "foreach ($p in $ps) { "
    "$age = [math]::Round(((Get-Date) - $p.StartTime).TotalSeconds); "
    "Write-Output ($p.Id.ToString() + ' ' + "
    "[math]::Round($p.PrivateMemorySize64/1MB).ToString() + ' ' + $age.ToString()) }"
)


def liquidsoap_process_info(
    runner=subprocess.run,
) -> Optional[List[ProcessInfo]]:
    """All ``liquidsoap.exe`` processes (usually one), or None on error."""
    if sys.platform != "win32":
        return None
    try:
        proc = runner(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_QUERY],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Get-Process liquidsoap failed: %s", exc)
        return None
    if proc.returncode != 0:
        logger.debug("Get-Process liquidsoap exited %s: %s", proc.returncode, proc.stderr)
        return None
    infos: List[ProcessInfo] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        try:
            infos.append(ProcessInfo(int(parts[0]), float(parts[1]), float(parts[2])))
        except ValueError:
            continue
    return infos


def render_endpoint_sessions() -> Optional[Dict[str, List[int]]]:
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
            CLSID_MMDeviceEnumerator,
            DEVICE_STATE,
            EDataFlow,
        )
        from pycaw.pycaw import AudioUtilities  # noqa: PLC0415
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Core Audio session API unavailable: %s", exc)
        return None

    result: Dict[str, List[int]] = {}
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
            pids: List[int] = []
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


def endpoints_holding(sessions: Dict[str, List[int]], pids: List[int]) -> List[str]:
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
    if got.startswith(exp) and got[len(exp):].lstrip().startswith("("):
        return True
    return exp.startswith(got) and exp[len(got):].lstrip().startswith("(")
