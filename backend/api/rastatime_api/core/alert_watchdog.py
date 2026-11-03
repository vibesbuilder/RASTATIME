"""
RASTATIME 2026-11-03 - alerts stage 1, the API side: a process cannot
report its own death, so the API service watches the playout (the playout
watches everything else, ``rastatime_playout.alerts``).

Every minute: the playout's HTTP listener (``/source-state`` on
127.0.0.1:8770) must answer, or ``sc query RASTATIME-PLAYOUT`` must say
RUNNING; two misses in a row raise ``service:RASTATIME-PLAYOUT``, one hit
clears it.  Settings (``alerts_*`` in cc_pref) and the senders are the
shared ones (``rastatime_shared.alerts``).  Started by the Waitress entry
point only (never by manage.py commands).
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from typing import Optional

from rastatime_shared.alerts import AlertManager, AlertSettings, settings_from_entries

logger = logging.getLogger(__name__)

PLAYOUT_STATE_URL = "http://127.0.0.1:8770/source-state"
PLAYOUT_SERVICE = "RASTATIME-PLAYOUT"


def read_alert_settings() -> AlertSettings:
    from rastatime_api.core.models import Preference  # noqa: PLC0415

    entries = dict(Preference.site.filter(key__startswith="alerts_").values_list("key", "value"))
    name = Preference.site.filter(key="station_name").values_list("value", flat=True).first() or ""
    return settings_from_entries(entries, station_name=str(name))


def playout_listener_ok(url: str = PLAYOUT_STATE_URL, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - localhost only
            return resp.status == 200
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def service_running(name: str = PLAYOUT_SERVICE, timeout: float = 10.0) -> bool:
    try:
        out = subprocess.run(
            ["sc", "query", name], capture_output=True, text=True, timeout=timeout, check=False
        ).stdout
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    for line in out.splitlines():
        if "STATE" in line.upper():
            return "RUNNING" in line.upper()
    return False


class PlayoutWatchdog:
    INTERVAL_SECONDS = 60.0
    SETTINGS_TTL_SECONDS = 30.0
    MISSES_TO_RAISE = 2

    def __init__(
        self,
        settings_loader: Callable[[], AlertSettings] = read_alert_settings,
        listener_check: Callable[[], bool] = playout_listener_ok,
        service_check: Callable[[], bool] = service_running,
        clock: Callable[[], float] = time.time,
        **manager_kwargs,
    ) -> None:
        self._loader = settings_loader
        self._listener_check = listener_check
        self._service_check = service_check
        self._clock = clock
        self._settings: Optional[AlertSettings] = None
        self._settings_at = 0.0
        self.manager = AlertManager(
            self.settings, clock=clock, source="RASTATIME-API", **manager_kwargs
        )
        self.misses = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def settings(self) -> AlertSettings:
        now = self._clock()
        if self._settings is None or now - self._settings_at > self.SETTINGS_TTL_SECONDS:
            try:
                self._settings = self._loader()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("alert settings unavailable: %s", exc)
                self._settings = self._settings or settings_from_entries({})
            self._settings_at = now
        return self._settings

    def tick(self) -> None:
        settings = self.settings()
        if settings.enabled and settings.services:
            ok = self._listener_check() or self._service_check()
            if ok:
                self.misses = 0
                self.manager.clear_alert(f"service:{PLAYOUT_SERVICE}", "The playout answers again.")
            else:
                self.misses += 1
                if self.misses >= self.MISSES_TO_RAISE:
                    self.manager.raise_alert(
                        f"service:{PLAYOUT_SERVICE}",
                        "Playout service not responding",
                        f"Neither the playout listener nor the Windows service answered ({self.misses} checks in a row).",
                    )
        self.manager.tick()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="rastatime-alert-watchdog", daemon=True
        )
        self._thread.start()
        logger.info(
            "alert watchdog: watching %s every %.0f s", PLAYOUT_SERVICE, self.INTERVAL_SECONDS
        )

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        self._stop.wait(self.INTERVAL_SECONDS)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("alert watchdog: tick failed: %s", exc, exc_info=True)
            self._stop.wait(self.INTERVAL_SECONDS)


_watchdog: Optional[PlayoutWatchdog] = None


def start_watchdog() -> Optional[PlayoutWatchdog]:
    """Start the singleton unless ``RASTATIME_ALERT_WATCHDOG=0``."""
    global _watchdog  # noqa: PLW0603
    if os.environ.get("RASTATIME_ALERT_WATCHDOG", "1").strip().lower() in (
        "0",
        "false",
        "off",
        "no",
    ):
        logger.info("alert watchdog: disabled by RASTATIME_ALERT_WATCHDOG")
        return None
    if _watchdog is None:
        _watchdog = PlayoutWatchdog()
        _watchdog.start()
    return _watchdog
