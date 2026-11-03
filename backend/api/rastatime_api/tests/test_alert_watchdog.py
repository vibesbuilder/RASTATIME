"""RASTATIME 2026-11-03 - alerts stage 1: the API watches the playout."""

from rastatime_shared.alerts import settings_from_entries

from rastatime_api.core import alert_watchdog as aw


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Spy:
    def __init__(self):
        self.mails = []

    def mail(self, settings, subject, body):
        self.mails.append((subject, body))

    def telegram(self, settings, text):
        raise RuntimeError("no telegram")


def _settings(**over):
    base = {
        "alerts_enabled": "true",
        "alerts_smtp_host": "h",
        "alerts_mail_from": "f@x",
        "alerts_mail_to": "t@x",
    }
    base.update(over)
    return settings_from_entries(base, station_name="Radio Test")


def _watchdog(state, spy, clock, settings=None):
    s = settings or _settings()
    return aw.PlayoutWatchdog(
        settings_loader=lambda: s,
        listener_check=lambda: state["listener"],
        service_check=lambda: state["service"],
        clock=clock,
        send_mail_fn=spy.mail,
        send_telegram_fn=spy.telegram,
    )


def test_playout_down_raises_after_two_misses_and_clears():
    state = {"listener": False, "service": False}
    spy, clock = Spy(), Clock()
    w = _watchdog(state, spy, clock)
    w.tick()
    assert not spy.mails and w.misses == 1
    w.tick()
    assert spy.mails[-1][0] == "[Radio Test] ALERT: Playout service not responding"
    assert "Reported by: RASTATIME-API" in spy.mails[-1][1]
    state["service"] = True  # the Windows service is back (listener still booting)
    w.tick()
    assert spy.mails[-1][0] == "[Radio Test] OK: Playout service not responding" and w.misses == 0


def test_listener_alone_counts_as_alive():
    state = {"listener": True, "service": False}
    spy, clock = Spy(), Clock()
    w = _watchdog(state, spy, clock)
    w.tick()
    w.tick()
    assert not spy.mails


def test_services_switch_off_stops_the_check():
    state = {"listener": False, "service": False}
    spy, clock = Spy(), Clock()
    w = _watchdog(state, spy, clock, _settings(alerts_services="false"))
    w.tick()
    w.tick()
    assert not spy.mails and w.misses == 0


def test_service_running_parses_sc_output(monkeypatch):
    class R:
        def __init__(self, stdout):
            self.stdout = stdout

    monkeypatch.setattr(aw.subprocess, "run", lambda *a, **k: R("   STATE : 4  RUNNING\n"))
    assert aw.service_running("x") is True
    monkeypatch.setattr(aw.subprocess, "run", lambda *a, **k: R("   STATE : 1  STOPPED\n"))
    assert aw.service_running("x") is False


def test_start_watchdog_respects_env(monkeypatch):
    monkeypatch.setenv("RASTATIME_ALERT_WATCHDOG", "0")
    aw._watchdog = None
    assert aw.start_watchdog() is None
