"""
RASTATIME 2026-11-03 - alerts stage 1 in the playout (operator go
2026-11-03): dead air, services down, pre-flight warnings, by e-mail and
Telegram (senders and state machine in ``rastatime_shared.alerts``).

* **Dead air** - ``blank.detect`` on the broadcast bus in rastatime.liq
  posts ``/audio-event?state=blank`` after ``alerts_dead_air_seconds`` of
  silence and ``state=noise`` when audio is back (playout HTTP listener,
  :meth:`PlayoutAlerts.on_audio_event`).  The silence fallback IS silence,
  so it is caught too; a planned Liquidsoap restart suppresses raises
  for a short window (:meth:`suppress`).
* **Services** - every minute: the API (``/api/v2/version``), Apache
  (``/login``), Icecast (``status-json.xsl``) over HTTP, Analyzer and
  Worker through ``sc query``; two misses in a row raise, one hit clears.
  Liquidsoap is covered by the pre-flight warning ``liquidsoap_unavailable``.
* **Pre-flight warnings** - every minute the warning table (API
  ``/api/v2/preflight/warnings``); a warning type that appears raises
  ``preflight:<type>``, one that disappears clears it.

Settings come from ``cc_pref`` (``alerts_*``, Settings -> Alerts) through
the Django ORM and are re-read every 30 s, so a save applies without a
restart; the dead-air threshold alone is baked into rastatime.liq and
follows with the planned restart (settings fingerprint).
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from typing import Optional

from rastatime_shared.alerts import AlertManager, AlertSettings, settings_from_entries

logger = logging.getLogger(__name__)

PREFLIGHT_TITLES: dict[str, str] = {
    "liquidsoap_unavailable": "Audio engine (Liquidsoap) unreachable",
    "liquidsoap_memory_high": "Audio engine memory high",
    "linein_device_unavailable": "Line-In device unavailable",
    "main_output_session_missing": "Main output session missing",
    "storage_root_unavailable": "Storage root unavailable",
    "stereotool_unavailable": "Stereo Tool unavailable",
    "autoplaylist_missing": "Autoloading playlist missing",
    "imports_failed": "Imports failed",
}

SERVICE_TITLES: dict[str, str] = {
    "RASTATIME-API": "API service not responding",
    "RASTATIME-APACHE": "Web interface (Apache) not responding",
    "RASTATIME-ICECAST": "Icecast not responding",
    "RASTATIME-ANALYZER": "Analyzer service not running",
    "RASTATIME-WORKER": "Worker service not running",
}


def read_alert_settings_from_db() -> AlertSettings:
    """``cc_pref`` rows ``alerts_*`` plus the station name, through the Django ORM."""
    try:
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]  # noqa: PLC0415

        entries = dict(
            Preference.site.filter(key__startswith="alerts_").values_list("key", "value")
        )
        name = (
            Preference.site.filter(key="station_name").values_list("value", flat=True).first() or ""
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("alert settings unavailable: %s", exc)
        return settings_from_entries({})
    return settings_from_entries(entries, station_name=str(name))


def _http_ok(url: str, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - localhost only
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        return exc.code < 500
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def service_running(name: str, timeout: float = 10.0) -> bool:
    """``sc query <name>`` says RUNNING (Windows service control manager)."""
    try:
        out = subprocess.run(
            ["sc", "query", name],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        ).stdout
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    for line in out.splitlines():
        if "STATE" in line.upper():
            return "RUNNING" in line.upper()
    return False


def default_service_checks(
    api_url: str = "http://127.0.0.1:8765/api/v2/version",
    web_url: str = "http://127.0.0.1/login",
    icecast_url: str = "http://127.0.0.1:8000/status-json.xsl",
) -> list[tuple[str, Callable[[], bool]]]:
    return [
        ("RASTATIME-API", lambda: _http_ok(api_url)),
        ("RASTATIME-APACHE", lambda: _http_ok(web_url)),
        ("RASTATIME-ICECAST", lambda: _http_ok(icecast_url)),
        ("RASTATIME-ANALYZER", lambda: service_running("RASTATIME-ANALYZER")),
        ("RASTATIME-WORKER", lambda: service_running("RASTATIME-WORKER")),
    ]


class PlayoutAlerts:
    """The alert sources of the playout process and the loop that runs them."""

    INTERVAL_SECONDS = 60.0
    SETTINGS_TTL_SECONDS = 30.0
    MISSES_TO_RAISE = 2

    def __init__(
        self,
        api_client: Optional[object] = None,
        settings_loader: Callable[[], AlertSettings] = read_alert_settings_from_db,
        service_checks: Optional[list[tuple[str, Callable[[], bool]]]] = None,
        warnings_loader: Optional[Callable[[], Optional[list]]] = None,
        clock: Callable[[], float] = time.time,
        **manager_kwargs,
    ) -> None:
        self._api_client = api_client
        self._loader = settings_loader
        self._clock = clock
        self._settings: Optional[AlertSettings] = None
        self._settings_at = 0.0
        self.manager = AlertManager(
            self.settings, clock=clock, source="RASTATIME-PLAYOUT", **manager_kwargs
        )
        self._service_checks = (
            service_checks if service_checks is not None else default_service_checks()
        )
        self._warnings_loader = warnings_loader or self._fetch_warnings
        self._misses: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.dead_air_since: Optional[float] = None

    # -- settings ------------------------------------------------------

    def settings(self) -> AlertSettings:
        now = self._clock()
        if self._settings is None or now - self._settings_at > self.SETTINGS_TTL_SECONDS:
            try:
                self._settings = self._loader()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("alert settings reload failed: %s", exc)
                self._settings = self._settings or settings_from_entries({})
            self._settings_at = now
        return self._settings

    def refresh_settings(self) -> AlertSettings:
        self._settings_at = 0.0
        return self.settings()

    # -- events --------------------------------------------------------

    def on_audio_event(self, state: str) -> bool:
        """``blank`` / ``noise`` from rastatime.liq's blank.detect."""
        if state == "blank":
            self.dead_air_since = self._clock()
            secs = self.settings().dead_air_seconds
            return self.manager.raise_alert(
                "dead_air",
                "Dead air",
                f"No audio on the broadcast bus for {secs} s.",
            )
        if state == "noise":
            since = self.dead_air_since
            self.dead_air_since = None
            lasted = f" (after {int(self._clock() - since)} s)" if since else ""
            return self.manager.clear_alert("dead_air", f"Audio is back{lasted}.")
        return False

    def suppress(self, seconds: float) -> None:
        self.manager.suppress(seconds)

    def send_test(self, channel: str) -> str:
        self.refresh_settings()
        return self.manager.send_test(channel)

    # -- periodic checks ----------------------------------------------

    def check_services(self) -> None:
        for name, check in self._service_checks:
            try:
                ok = bool(check())
            except Exception:  # pylint: disable=broad-exception-caught
                ok = False
            key = f"service:{name}"
            if ok:
                self._misses[name] = 0
                self.manager.clear_alert(key, f"{name} answers again.")
                continue
            self._misses[name] = self._misses.get(name, 0) + 1
            if self._misses[name] >= self.MISSES_TO_RAISE:
                self.manager.raise_alert(
                    key,
                    SERVICE_TITLES.get(name, f"{name} down"),
                    f"{name} did not answer {self._misses[name]} checks in a row.",
                )

    def _fetch_warnings(self) -> Optional[list]:
        if self._api_client is None:
            return None
        try:
            resp = self._api_client.session.get("/api/v2/preflight/warnings", timeout=5)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data if isinstance(data, list) else data.get("results", data.get("warnings"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("preflight warnings unavailable for alerts: %s", exc)
            return None

    def check_preflight(self) -> None:
        rows = self._warnings_loader()
        if rows is None:
            return
        groups: dict[str, list] = {}
        for row in rows:
            wtype = str(row.get("warning_type") or "")
            if wtype:
                groups.setdefault(wtype, []).append(row)
        for wtype, items in groups.items():
            first = items[0].get("detail") or {}
            text = first.get("message") or first.get("reason") or first.get("text") or ""
            detail = f"{len(items)} warning(s) on the dashboard."
            if text:
                detail += f" First: {str(text)[:200]}"
            self.manager.raise_alert(
                f"preflight:{wtype}", PREFLIGHT_TITLES.get(wtype, wtype), detail
            )
        for key in list(self.manager.open_alerts()):
            if key.startswith("preflight:") and key[len("preflight:") :] not in groups:
                self.manager.clear_alert(key, "The warning is gone from the dashboard.")

    def tick(self) -> None:
        settings = self.settings()
        if settings.enabled and settings.services:
            self.check_services()
        if settings.enabled and settings.preflight:
            self.check_preflight()
        self.manager.tick()

    # -- thread --------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="rastatime-alerts", daemon=True)
        self._thread.start()
        logger.info("alerts: monitor started (every %.0f s)", self.INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # first checks after a grace period so a fresh boot does not alarm
        self._stop.wait(self.INTERVAL_SECONDS)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("alerts: tick failed: %s", exc, exc_info=True)
            self._stop.wait(self.INTERVAL_SECONDS)
