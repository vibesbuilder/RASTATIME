"""
RASTATIME 2026-11-03 - alerts by e-mail (SMTP) and Telegram, stage 1
(operator go 2026-11-03: dead air, services down, pre-flight warnings).

Shared by the playout (dead air from Liquidsoap, pre-flight warnings,
the other services) and the API service (watches the playout).  Only the
standard library is used so both processes can import it.

Settings live in ``cc_pref`` (keys ``alerts_*``, Settings -> Alerts);
:func:`settings_from_entries` turns the key/value rows into
:class:`AlertSettings`.  :class:`AlertManager` keeps the state of every
alert (``raise_alert`` / ``clear_alert``), repeats open alerts every
``repeat_minutes``, rate-limits the channels and honours a suppression
window around planned restarts.  The senders raise on failure; the
manager logs and keeps the alert open so the next tick tries again.
"""

from __future__ import annotations

import json
import logging
import smtplib
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

PREF_PREFIX = "alerts_"


def tls_context() -> ssl.SSLContext:
    """The system trust store plus the ``certifi`` bundle.

    RASTATIME 2026-11-04 (Telegram acceptance): Python reads the Windows
    certificate store as it is, and Windows loads many root certificates only
    on demand through its own TLS stack - api.telegram.org chains to a GoDaddy
    root that was missing on the studio machine ("self-signed certificate in
    certificate chain").  The certifi bundle (installed with ``requests``)
    fills the gap; without it the system store alone is used.
    """
    ctx = ssl.create_default_context()
    try:
        import certifi  # pylint: disable=import-outside-toplevel

        ctx.load_verify_locations(cafile=certifi.where())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("alerts: certifi bundle not loaded (%s)", exc)
    return ctx


#: cc_pref keys and their defaults (strings as stored)
DEFAULTS: dict[str, str] = {
    "alerts_enabled": "false",
    "alerts_smtp_host": "",
    "alerts_smtp_port": "587",
    "alerts_smtp_security": "starttls",  # starttls | ssl | none
    "alerts_smtp_user": "",
    "alerts_smtp_password": "",
    "alerts_mail_from": "",
    "alerts_mail_to": "",
    "alerts_telegram_token": "",
    "alerts_telegram_chats": "",
    "alerts_dead_air_seconds": "30",
    "alerts_repeat_minutes": "30",
    "alerts_services": "true",
    "alerts_preflight": "true",
}

#: never more than this many messages per channel and hour
RATE_LIMIT_PER_HOUR = 20


@dataclass
class AlertSettings:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "starttls"
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_to: list[str] = field(default_factory=list)
    telegram_token: str = ""
    telegram_chats: list[str] = field(default_factory=list)
    dead_air_seconds: int = 30
    repeat_minutes: int = 30
    services: bool = True
    preflight: bool = True
    station_name: str = "RASTATIME"

    @property
    def mail_ready(self) -> bool:
        return bool(self.smtp_host and self.mail_from and self.mail_to)

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_token and self.telegram_chats)

    @property
    def any_channel(self) -> bool:
        return self.mail_ready or self.telegram_ready


def _as_bool(value: object) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "t", "yes", "on")


def _as_int(value: object, default: int, lo: int, hi: int) -> int:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _as_list(value: object) -> list[str]:
    return [
        p.strip()
        for p in str(value or "").replace(";", ",").replace("\n", ",").split(",")
        if p.strip()
    ]


def settings_from_entries(entries: dict[str, object], station_name: str = "") -> AlertSettings:
    """cc_pref rows (key -> value) to :class:`AlertSettings`; missing keys take the defaults."""
    get = lambda k: entries.get(k) if entries.get(k) not in (None, "") else DEFAULTS[k]  # noqa: E731
    sec = str(get("alerts_smtp_security")).strip().lower()
    return AlertSettings(
        enabled=_as_bool(get("alerts_enabled")),
        smtp_host=str(get("alerts_smtp_host")).strip(),
        smtp_port=_as_int(get("alerts_smtp_port"), 587, 1, 65535),
        smtp_security=sec if sec in ("starttls", "ssl", "none") else "starttls",
        smtp_user=str(get("alerts_smtp_user")).strip(),
        smtp_password=str(entries.get("alerts_smtp_password") or ""),
        mail_from=str(get("alerts_mail_from")).strip(),
        mail_to=_as_list(get("alerts_mail_to")),
        telegram_token=str(get("alerts_telegram_token")).strip(),
        telegram_chats=_as_list(get("alerts_telegram_chats")),
        dead_air_seconds=_as_int(get("alerts_dead_air_seconds"), 30, 5, 3600),
        repeat_minutes=_as_int(get("alerts_repeat_minutes"), 30, 0, 1440),
        services=_as_bool(get("alerts_services")),
        preflight=_as_bool(get("alerts_preflight")),
        station_name=(station_name or "RASTATIME").strip() or "RASTATIME",
    )


# ---------------------------------------------------------------------------
# senders (raise on failure)
# ---------------------------------------------------------------------------


def send_mail(settings: AlertSettings, subject: str, body: str, timeout: float = 15.0) -> None:
    """One e-mail to every address of ``mail_to`` over SMTP (STARTTLS, SSL or plain)."""
    if not settings.mail_ready:
        raise RuntimeError("mail is not configured (SMTP host, sender and recipients)")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = ", ".join(settings.mail_to)
    msg.set_content(body)
    if settings.smtp_security == "ssl":
        client = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=timeout,
            context=tls_context(),
        )
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
    try:
        client.ehlo()
        if settings.smtp_security == "starttls":
            client.starttls(context=tls_context())
            client.ehlo()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(msg)
    finally:
        try:
            client.quit()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


def send_telegram(
    settings: AlertSettings, text: str, timeout: float = 15.0, opener: Optional[Callable] = None
) -> None:
    """``sendMessage`` of the Bot API to every chat of ``telegram_chats``."""
    if not settings.telegram_ready:
        raise RuntimeError("Telegram is not configured (bot token and chat ids)")
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    if opener is None:
        ctx = tls_context()

        def open_(req, timeout=None):
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)

    else:
        open_ = opener
    errors = []
    for chat in settings.telegram_chats:
        data = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode(
            "utf-8"
        )
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with open_(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8") or "{}")
            if not payload.get("ok", False):
                errors.append(f"chat {chat}: {payload.get('description', 'not ok')}")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:200]
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            errors.append(f"chat {chat}: HTTP {exc.code} {body}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"chat {chat}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))


# ---------------------------------------------------------------------------
# the manager
# ---------------------------------------------------------------------------


@dataclass
class _Open:
    key: str
    title: str
    detail: str
    since: float
    last_sent: float
    notified: bool  # at least one channel got the raise


class AlertManager:
    """
    State of the alerts of one process.

    ``settings_loader`` returns fresh :class:`AlertSettings` (read from the
    database by the caller); it is consulted on every send so a saved
    setting applies without a restart.  ``send_mail_fn`` / ``send_telegram_fn``
    exist for the tests.
    """

    def __init__(
        self,
        settings_loader: Callable[[], AlertSettings],
        clock: Callable[[], float] = time.time,
        send_mail_fn: Callable = send_mail,
        send_telegram_fn: Callable = send_telegram,
        source: str = "",
    ) -> None:
        self._load = settings_loader
        self._clock = clock
        self._send_mail = send_mail_fn
        self._send_telegram = send_telegram_fn
        self._source = source
        self._open: dict[str, _Open] = {}
        self._suppress_until = 0.0
        self._sent_times: dict[str, list[float]] = {"mail": [], "telegram": []}
        self._lock = threading.RLock()
        self.last_errors: dict[str, str] = {}

    # -- state ---------------------------------------------------------

    def open_alerts(self) -> dict[str, _Open]:
        with self._lock:
            return dict(self._open)

    def is_open(self, key: str) -> bool:
        with self._lock:
            return key in self._open

    def suppress(self, seconds: float) -> None:
        """No raises for ``seconds`` (planned restarts); clears still go out."""
        with self._lock:
            self._suppress_until = max(self._suppress_until, self._clock() + max(0.0, seconds))
        logger.info("alerts: suppressed for %.0f s", seconds)

    def suppressed(self) -> bool:
        return self._clock() < self._suppress_until

    def raise_alert(self, key: str, title: str, detail: str = "") -> bool:
        """
        Open (or keep open) the alert ``key``.  Sends the message the first
        time, and again when the previous attempt reached no channel.
        Returns True when a message went out.
        """
        with self._lock:
            now = self._clock()
            entry = self._open.get(key)
            if entry is None:
                entry = _Open(
                    key=key, title=title, detail=detail, since=now, last_sent=0.0, notified=False
                )
                self._open[key] = entry
                logger.warning("alert raised: %s - %s %s", key, title, detail)
            else:
                entry.title, entry.detail = title, detail
            if entry.notified or self.suppressed():
                if not entry.notified:
                    logger.info("alert %s raised during a suppression window - not sent", key)
                return False
            sent = self._send("ALERT", entry.title, entry.detail, entry.since)
            if sent:
                entry.notified = True
                entry.last_sent = now
            return sent

    def clear_alert(self, key: str, detail: str = "") -> bool:
        """Close the alert ``key``; sends the all-clear when the raise had been sent."""
        with self._lock:
            entry = self._open.pop(key, None)
            if entry is None:
                return False
            logger.info("alert cleared: %s %s", key, detail)
            if not entry.notified:
                return False
            return self._send("OK", entry.title, detail or "cleared", entry.since, cleared=True)

    def tick(self) -> int:
        """Repeat the open alerts every ``repeat_minutes`` (0 = never); returns the number sent."""
        sent = 0
        with self._lock:
            settings = self._load()
            if settings.repeat_minutes <= 0:
                return 0
            now = self._clock()
            for entry in self._open.values():
                if not entry.notified:
                    if not self.suppressed() and self._send(
                        "ALERT", entry.title, entry.detail, entry.since
                    ):
                        entry.notified = True
                        entry.last_sent = now
                        sent += 1
                    continue
                if now - entry.last_sent >= settings.repeat_minutes * 60:
                    if self._send("STILL", entry.title, entry.detail, entry.since):
                        entry.last_sent = now
                        sent += 1
        return sent

    # -- sending -------------------------------------------------------

    def send_test(self, channel: str) -> str:
        """A test message over ``mail`` or ``telegram``; returns '' or the error text."""
        settings = self._load()
        text = self._format(
            "TEST",
            "Test message",
            f"sent from {self._source or 'RASTATIME'}",
            self._clock(),
            settings,
        )
        try:
            if channel == "mail":
                self._send_mail(settings, self._subject("TEST", "Test message", settings), text)
            elif channel == "telegram":
                self._send_telegram(settings, text)
            else:
                return f"unknown channel {channel}"
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("alert test (%s) failed: %s", channel, exc)
            return str(exc)
        return ""

    def _subject(self, kind: str, title: str, settings: AlertSettings) -> str:
        word = {"ALERT": "ALERT", "STILL": "STILL OPEN", "OK": "OK", "TEST": "TEST"}.get(kind, kind)
        return f"[{settings.station_name}] {word}: {title}"

    def _format(
        self,
        kind: str,
        title: str,
        detail: str,
        since: float,
        settings: AlertSettings,
        cleared: bool = False,
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        since_s = datetime.fromtimestamp(since).strftime("%Y-%m-%d %H:%M:%S")
        head = self._subject(kind, title, settings)
        lines = [head, f"Time: {now}"]
        if kind == "OK":
            lines.append(f"Open since: {since_s}")
        elif kind == "STILL":
            lines.append(f"Open since: {since_s} (reminder)")
        if detail:
            lines.append(detail)
        if self._source:
            lines.append(f"Reported by: {self._source}")
        return "\n".join(lines)

    def _rate_ok(self, channel: str, now: float) -> bool:
        times = [t for t in self._sent_times[channel] if now - t < 3600]
        self._sent_times[channel] = times
        if len(times) >= RATE_LIMIT_PER_HOUR:
            logger.warning(
                "alerts: rate limit of %d/h reached for %s", RATE_LIMIT_PER_HOUR, channel
            )
            return False
        times.append(now)
        return True

    def _send(
        self, kind: str, title: str, detail: str, since: float, cleared: bool = False
    ) -> bool:
        settings = self._load()
        if not settings.enabled or not settings.any_channel:
            return False
        now = self._clock()
        text = self._format(kind, title, detail, since, settings, cleared=cleared)
        subject = self._subject(kind, title, settings)
        ok = False
        if settings.mail_ready and self._rate_ok("mail", now):
            try:
                self._send_mail(settings, subject, text)
                ok = True
                self.last_errors.pop("mail", None)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.last_errors["mail"] = str(exc)
                logger.warning("alert mail failed: %s", exc)
        if settings.telegram_ready and self._rate_ok("telegram", now):
            try:
                self._send_telegram(settings, text)
                ok = True
                self.last_errors.pop("telegram", None)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.last_errors["telegram"] = str(exc)
                logger.warning("alert telegram failed: %s", exc)
        return ok
