"""RASTATIME 2026-11-03 - alerts stage 1 in the playout: monitor, listener, Liquidsoap block."""

from __future__ import annotations

import json
from urllib.parse import urlparse

from rastatime_playout import alerts as pa
from rastatime_playout import liquidsoap_config as lc
from rastatime_shared.alerts import settings_from_entries


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
        raise RuntimeError("no telegram in tests")


def _settings(**over):
    base = {
        "alerts_enabled": "true",
        "alerts_smtp_host": "h",
        "alerts_mail_from": "f@x",
        "alerts_mail_to": "t@x",
        "alerts_dead_air_seconds": "45",
    }
    base.update(over)
    return settings_from_entries(base, station_name="Radio Test")


def _alerts(clock, spy, checks=None, warnings=None, settings=None):
    s = settings or _settings()
    return pa.PlayoutAlerts(
        api_client=None,
        settings_loader=lambda: s,
        service_checks=checks or [],
        warnings_loader=(lambda: warnings) if warnings is not None else (lambda: None),
        clock=clock,
        send_mail_fn=spy.mail,
        send_telegram_fn=spy.telegram,
    )


def test_dead_air_raise_and_clear():
    clock, spy = Clock(), Spy()
    a = _alerts(clock, spy)
    assert a.on_audio_event("blank") is True
    assert spy.mails[-1][0] == "[Radio Test] ALERT: Dead air" and "45 s" in spy.mails[-1][1]
    assert a.on_audio_event("blank") is False  # still the same alert
    clock.t += 70
    assert a.on_audio_event("noise") is True
    assert spy.mails[-1][0] == "[Radio Test] OK: Dead air" and "after 70 s" in spy.mails[-1][1]
    assert a.on_audio_event("weird") is False


def test_services_raise_after_two_misses_and_clear():
    clock, spy = Clock(), Spy()
    state = {"api": False}
    a = _alerts(clock, spy, checks=[("RASTATIME-API", lambda: state["api"])])
    a.check_services()
    assert not spy.mails  # one miss is tolerated
    a.check_services()
    assert spy.mails[-1][0] == "[Radio Test] ALERT: API service not responding"
    state["api"] = True
    a.check_services()
    assert spy.mails[-1][0] == "[Radio Test] OK: API service not responding"


def test_preflight_warnings_raise_per_type_and_clear():
    clock, spy = Clock(), Spy()
    rows = [
        {"warning_type": "liquidsoap_unavailable", "detail": {"message": "telnet refused"}},
        {"warning_type": "imports_failed", "detail": {}},
        {"warning_type": "imports_failed", "detail": {}},
    ]
    a = _alerts(clock, spy, warnings=rows)
    a.check_preflight()
    subjects = [m[0] for m in spy.mails]
    assert "[Radio Test] ALERT: Audio engine (Liquidsoap) unreachable" in subjects
    assert "[Radio Test] ALERT: Imports failed" in subjects
    assert any("2 warning(s)" in m[1] for m in spy.mails)
    rows.clear()
    a.check_preflight()
    assert spy.mails[-1][0].startswith("[Radio Test] OK:") and len(a.manager.open_alerts()) == 0


def test_tick_respects_the_switches():
    clock, spy = Clock(), Spy()
    calls = {"n": 0}

    def check():
        calls["n"] += 1
        return False

    s = _settings(alerts_services="false", alerts_preflight="false")
    a = _alerts(
        clock,
        spy,
        checks=[("RASTATIME-WORKER", check)],
        warnings=[{"warning_type": "x"}],
        settings=s,
    )
    a.tick()
    assert calls["n"] == 0 and not spy.mails


def test_suppress_holds_dead_air_raise():
    clock, spy = Clock(), Spy()
    a = _alerts(clock, spy)
    a.suppress(180)
    assert a.on_audio_event("blank") is False and a.manager.is_open("dead_air")
    assert not spy.mails
    clock.t += 200
    a.manager.tick()
    assert spy.mails and spy.mails[-1][0].endswith("ALERT: Dead air")


def test_send_test_uses_fresh_settings():
    clock, spy = Clock(), Spy()
    a = _alerts(clock, spy)
    assert a.send_test("mail") == ""
    assert spy.mails[-1][0] == "[Radio Test] TEST: Test message"
    assert (
        a.send_test("telegram") == "no telegram in tests"
    )  # the sender's own error text comes back


def test_listener_audio_event_and_alert_test(monkeypatch):
    from rastatime_playout import source_switcher as ss

    clock, spy = Clock(), Spy()
    a = _alerts(clock, spy)
    monkeypatch.setattr(ss._EventHandler, "alerts", a, raising=False)
    sent = []

    class H(ss._EventHandler):
        def __init__(self):  # pylint: disable=super-init-not-called
            pass

        def _send(self, code, body):
            sent.append((code, body))

        def _send_json(self, code, payload):
            sent.append((code, json.dumps(payload)))

    h = H()
    h._handle_audio_event(urlparse("/audio-event?state=blank"))
    assert sent[-1][0] == 200 and a.manager.is_open("dead_air")
    h._handle_audio_event(urlparse("/audio-event?state=nope"))
    assert sent[-1][0] == 400
    h._handle_alert_test(urlparse("/alert-test?channel=mail"))
    assert sent[-1][0] == 200 and json.loads(sent[-1][1]) == {"ok": True, "error": ""}
    h._handle_alert_test(urlparse("/alert-test?channel=sms"))
    assert sent[-1][0] == 400


def test_render_alert_blank_block():
    out = lc._render_alert_blank_block("http://127.0.0.1:8770/audio-event", 45)
    assert (
        'blank.detect(id="dead_air", max_blank=45., min_noise=2., threshold=-50., track_sensitive=false, bus)'
        in out
    )
    assert "audio-event?state=blank" in out and "audio-event?state=noise" in out
    assert "on_blank(synchronous=false" in out and "on_noise(synchronous=false" in out
    assert lc._render_alert_blank_block(None, 30).startswith("#")
    assert "max_blank=5." in lc._render_alert_blank_block("http://x/y", 1)


def test_full_render_contains_the_block_only_with_url():
    def _stream():
        return {
            "enabled": True,
            "type": "mp3",
            "bitrate": 128,
            "host": "h",
            "port": 8000,
            "mount": "m",
            "user": "source",
            "pass": "x",
            "name": "",
            "description": "",
            "genre": "",
            "url": "",
            "samplerate": 44100,
        }

    out = lc.render_rastatime_liq(
        [_stream()], alert_blank_url="http://127.0.0.1:8770/audio-event", alert_dead_air_seconds=30
    )
    assert "${ALERT_BLANK_BLOCK}" not in out and 'id="dead_air"' in out
    out2 = lc.render_rastatime_liq([_stream()])
    assert "${ALERT_BLANK_BLOCK}" not in out2 and 'id="dead_air"' not in out2


def test_service_running_parses_sc_output(monkeypatch):
    class R:
        def __init__(self, stdout):
            self.stdout = stdout

    monkeypatch.setattr(
        pa.subprocess,
        "run",
        lambda *a, **k: R("SERVICE_NAME: x\n        STATE              : 4  RUNNING\n"),
    )
    assert pa.service_running("x") is True
    monkeypatch.setattr(
        pa.subprocess, "run", lambda *a, **k: R("        STATE              : 1  STOPPED\n")
    )
    assert pa.service_running("x") is False
