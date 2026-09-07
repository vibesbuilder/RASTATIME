"""
liquidsoap_service — restart the RASTATIME-LIQUIDSOAP NSSM service
from the playout, and decide *when* that is safe.

RASTATIME 2026-09-05.  Two callers:

1. **Boot window** (``__main__``): after a reboot LIQUIDSOAP starts in
   parallel with PLAYOUT and loads the *previous* ``rastatime.liq``
   before PLAYOUT has rendered the fresh one (BACKLOG "Boot-Race").
   On 2026-09-05 the stale render pointed ``output.portaudio`` at a
   device index that had become a WDM-KS entry; the instance died at
   device-open and NSSM restarted it with the same file — only the
   coincidental re-render by PLAYOUT saved the station from a restart
   loop.  When PLAYOUT's render at start changed the file *and* the
   machine booted less than :data:`BOOT_WINDOW_SECONDS` ago, PLAYOUT
   restarts LIQUIDSOAP itself.  Nothing is on air that early.

2. **Nightly quiet-window restart** (``PlayoutScheduler``): the
   savonet Windows build leaks memory in ``Unix.select``
   (see ``liquidsoap_config`` / the template's ``request.queue_sync``
   comment).  The template fix removes the only permanent poller, but
   telnet commands, harbor and http sources still cost a few KB per
   wake-up, so a daily restart in a quiet window is the safety net.
   :class:`NightlyRestartPolicy` says whether now is inside the window
   and today's restart is still due; the scheduler adds the "nothing
   on air / nothing about to start" check because only it knows.

Both go through :func:`restart_liquidsoap_service`, which shells out to
``nssm restart`` (PLAYOUT runs as LocalSystem, so it may).  The
function never raises: a failed restart is logged and reported as
``False`` — the caller keeps running on the old instance.
"""

from __future__ import annotations

import ctypes
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)

#: Path of the NSSM binary that manages the RASTATIME services.
NSSM_EXE = os.environ.get("RASTATIME_NSSM_EXE", r"C:\Tools\nssm\nssm.exe")

#: NSSM service name of the Liquidsoap process.
LIQUIDSOAP_SERVICE = os.environ.get(
    "RASTATIME_LIQUIDSOAP_SERVICE", "RASTATIME-LIQUIDSOAP"
)

#: Seconds after boot during which a changed render may restart
#: LIQUIDSOAP automatically.  Later changes keep the manual rule
#: (the operator restarts PLAYOUT, then LIQUIDSOAP).
BOOT_WINDOW_SECONDS = 600.0

#: Environment switch for the boot-window restart ("0" disables).
BOOT_RESTART_ENV = "RASTATIME_LIQUIDSOAP_BOOT_RESTART"

#: Environment variable holding the nightly restart time ("HH:MM",
#: local time) or "off".  Unset means the default below.
NIGHTLY_RESTART_ENV = "RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART"
DEFAULT_NIGHTLY_RESTART = "04:00"

#: How many seconds ``nssm restart`` may take before we give up on
#: one attempt; and how many attempts (the SCM refuses control
#: requests while a service is still START_PENDING right after boot).
RESTART_TIMEOUT_SECONDS = 60.0
RESTART_ATTEMPTS = 3
RESTART_RETRY_DELAY_SECONDS = 5.0


def system_uptime_seconds() -> Optional[float]:
    """Seconds since the machine booted (Windows), ``None`` elsewhere."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.GetTickCount64.restype = ctypes.c_ulonglong
        return float(kernel32.GetTickCount64()) / 1000.0
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("GetTickCount64 failed: %s", exc)
        return None


def within_boot_window(
    uptime_seconds: Optional[float] = None,
    window_seconds: float = BOOT_WINDOW_SECONDS,
) -> bool:
    """True when the machine booted less than ``window_seconds`` ago."""
    if uptime_seconds is None:
        uptime_seconds = system_uptime_seconds()
    if uptime_seconds is None:
        return False
    return 0.0 <= uptime_seconds < window_seconds


def boot_restart_enabled() -> bool:
    return os.environ.get(BOOT_RESTART_ENV, "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


#: How the last render addressed the Main Output - the renderer reports
#: it so automatic restarts can refuse the one mode that is unsafe
#: across a device-list change (RASTATIME 2026-09-07).
MAIN_OUTPUT_BY_NAME = "name"      # output.portaudio(device_name=...) - index-independent
MAIN_OUTPUT_BY_INDEX = "index"    # output.portaudio(device_id=N) - valid for one device list only
MAIN_OUTPUT_DEFAULT = "default"   # no device argument - OS default endpoint


def restart_liquidsoap_service(
    reason: str,
    *,
    nssm_exe: str = NSSM_EXE,
    service: str = LIQUIDSOAP_SERVICE,
    attempts: int = RESTART_ATTEMPTS,
    retry_delay: float = RESTART_RETRY_DELAY_SECONDS,
    runner: Callable[..., "subprocess.CompletedProcess[str]"] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    verify: Optional[Callable[[], bool]] = None,
) -> bool:
    """
    ``nssm restart <service>``, retried a few times.  Never raises.

    Returns True when NSSM reported success - or, when ``verify`` is
    given, when it confirms the service is back although NSSM exited
    non-zero.  ``runner``/``sleep``/``verify`` are injectable for tests.

    RASTATIME 2026-09-07: ``nssm restart`` exited 1 on every nightly
    restart so far ("STOP: ... erfolgreich beendet" followed by
    "Unexpected status SERVICE_PAUSED in response to START control")
    even though the stop and the start had both happened - the
    started instance died within NSSM's throttle window, which NSSM
    reports as *paused*.  Retrying blindly then killed each fresh
    instance again.  So: on a non-zero exit, ask the caller's
    ``verify`` (telnet back, uptime small) before retrying; a retry is
    only for a restart that demonstrably did not happen.
    """
    if not os.path.exists(nssm_exe):
        logger.error(
            "Cannot restart %s (%s): NSSM binary %s not found.",
            service, reason, nssm_exe,
        )
        return False

    for attempt in range(1, max(1, attempts) + 1):
        logger.warning(
            "Restarting %s (%s) — attempt %d/%d.",
            service, reason, attempt, attempts,
        )
        try:
            proc = runner(
                [nssm_exe, "restart", service],
                capture_output=True,
                text=True,
                timeout=RESTART_TIMEOUT_SECONDS,
                check=False,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("nssm restart %s raised: %s", service, exc)
            proc = None
        if proc is not None and proc.returncode == 0:
            logger.warning("%s restarted (%s).", service, reason)
            return True
        if proc is not None:
            # NSSM prints UTF-16 on some builds; keep whatever decodes.
            detail = (proc.stdout or "") + (proc.stderr or "")
            logger.error(
                "nssm restart %s exited %s: %s",
                service, proc.returncode, detail.replace("\x00", "").strip()[:300],
            )
            if verify is not None:
                try:
                    verified = bool(verify())
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug("restart verification raised: %s", exc)
                    verified = False
                if verified:
                    logger.warning(
                        "%s is back after the restart (%s) although nssm exited %s "
                        "- treating the restart as done, not retrying.",
                        service, reason, proc.returncode,
                    )
                    return True
        if attempt < attempts:
            sleep(retry_delay)
    return False


def wait_for_telnet(
    host: str,
    port: int,
    timeout: float = 30.0,
    *,
    sleep: Callable[[float], None] = time.sleep,
    connector: Callable[..., object] = socket.create_connection,
) -> bool:
    """Poll until Liquidsoap's telnet server accepts connections."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            conn = connector((host, port), timeout=2.0)
            try:
                close = getattr(conn, "close", None)
                if close:
                    close()
            finally:
                pass
            return True
        except OSError:
            if time.monotonic() >= deadline:
                return False
            sleep(0.5)


@dataclass(frozen=True)
class NightlyRestartPolicy:
    """
    When is the daily quiet-window restart due?

    ``start`` is local wall-clock time; the window lasts
    ``window_minutes``.  ``quiet_margin_seconds`` is how far the next
    scheduled item must be away before the scheduler may restart.
    """

    start: Optional[dtime]
    window_minutes: int = 60
    quiet_margin_seconds: float = 300.0

    @classmethod
    def from_env(cls, value: Optional[str] = None) -> "NightlyRestartPolicy":
        raw = (
            value if value is not None
            else os.environ.get(NIGHTLY_RESTART_ENV, DEFAULT_NIGHTLY_RESTART)
        )
        raw = (raw or "").strip().lower()
        if raw in ("", "off", "0", "false", "no", "none"):
            return cls(start=None)
        try:
            hh, mm = raw.split(":")
            return cls(start=dtime(int(hh), int(mm)))
        except (ValueError, TypeError):
            logger.warning(
                "%s=%r is not HH:MM or 'off' — nightly restart disabled.",
                NIGHTLY_RESTART_ENV, raw,
            )
            return cls(start=None)

    @property
    def enabled(self) -> bool:
        return self.start is not None

    def window_for(self, now_local: datetime) -> Optional[tuple]:
        """(window_start, window_end) of today's window, or None."""
        if self.start is None:
            return None
        begin = datetime.combine(now_local.date(), self.start)
        return begin, begin + timedelta(minutes=self.window_minutes)

    def due(self, now_local: datetime, last_done: Optional[date]) -> bool:
        """True inside today's window when today's restart is still open."""
        window = self.window_for(now_local)
        if window is None:
            return False
        begin, end = window
        if not begin <= now_local < end:
            return False
        return last_done != now_local.date()
