"""RASTATIME 2026-11-03 - alerts stage 1: settings, manager state machine, senders."""

import json
from email import message_from_bytes

import pytest
from rastatime_shared import alerts as A


def _settings(**over):
    base = {
        "alerts_enabled": "true",
        "alerts_smtp_host": "mail.example",
        "alerts_mail_from": "studio@example",
        "alerts_mail_to": "a@example, b@example",
        "alerts_telegram_token": "123:abc",
        "alerts_telegram_chats": "42",
        "alerts_repeat_minutes": "30",
    }
    base.update(over)
    return A.settings_from_entries(base, station_name="Radio Test")


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Spy:
    def __init__(self, fail=False):
        self.mails = []
        self.tgs = []
        self.fail = fail

    def mail(self, settings, subject, body):
        if self.fail:
            raise RuntimeError("smtp down")
        self.mails.append((subject, body))

    def telegram(self, settings, text):
        if self.fail:
            raise RuntimeError("tg down")
        self.tgs.append(text)


def _manager(spy, clock, settings=None):
    s = settings or _settings()
    return A.AlertManager(
        lambda: s,
        clock=clock,
        send_mail_fn=spy.mail,
        send_telegram_fn=spy.telegram,
        source="playout",
    )


def test_settings_from_entries_defaults_and_parsing():
    s = A.settings_from_entries({})
    assert not s.enabled and s.smtp_port == 587 and s.smtp_security == "starttls"
    assert s.dead_air_seconds == 30 and s.repeat_minutes == 30 and s.services and s.preflight
    s = _settings(
        alerts_smtp_port="x",
        alerts_smtp_security="weird",
        alerts_dead_air_seconds="1",
        alerts_mail_to="x@y;z@w",
    )
    assert s.smtp_port == 587 and s.smtp_security == "starttls" and s.dead_air_seconds == 5
    assert (
        s.mail_to == ["x@y", "z@w"]
        and s.mail_ready
        and s.telegram_ready
        and s.station_name == "Radio Test"
    )


def test_raise_sends_once_and_clear_sends_ok():
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock)
    assert m.raise_alert("dead_air", "Dead air", "no audio for 30 s") is True
    assert m.raise_alert("dead_air", "Dead air", "still") is False  # already notified
    assert len(spy.mails) == 1 and len(spy.tgs) == 1
    assert spy.mails[0][0] == "[Radio Test] ALERT: Dead air"
    assert "no audio for 30 s" in spy.mails[0][1] and "Reported by: playout" in spy.tgs[0]
    assert m.clear_alert("dead_air", "audio is back") is True
    assert spy.mails[1][0] == "[Radio Test] OK: Dead air" and "Open since" in spy.mails[1][1]
    assert not m.is_open("dead_air")


def test_clear_without_notification_is_silent():
    spy, clock = Spy(fail=True), Clock()
    m = _manager(spy, clock)
    assert m.raise_alert("svc", "Service down") is False  # both channels failed
    assert m.is_open("svc") and m.last_errors["mail"] == "smtp down"
    spy.fail = False
    assert m.clear_alert("svc") is False  # nobody was told, nothing to clear
    assert not spy.mails


def test_failed_raise_is_retried_on_tick_and_repeated_later():
    spy, clock = Spy(fail=True), Clock()
    m = _manager(spy, clock)
    m.raise_alert("svc", "Service down", "API")
    spy.fail = False
    assert m.tick() == 1  # the pending raise goes out
    assert spy.mails[-1][0].endswith("ALERT: Service down")
    clock.t += 29 * 60
    assert m.tick() == 0
    clock.t += 2 * 60
    assert m.tick() == 1
    assert (
        spy.mails[-1][0] == "[Radio Test] STILL OPEN: Service down"
        and "reminder" in spy.mails[-1][1]
    )


def test_repeat_disabled_with_zero_minutes():
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock, _settings(alerts_repeat_minutes="0"))
    m.raise_alert("x", "X")
    clock.t += 24 * 3600
    assert m.tick() == 0


def test_suppression_window_holds_raises_but_not_clears():
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock)
    m.raise_alert("a", "A")
    m.suppress(120)
    assert m.raise_alert("b", "B") is False and m.is_open("b")
    assert m.clear_alert("a") is True  # clears still go out
    clock.t += 121
    assert m.tick() == 1  # the held raise goes out after the window
    assert spy.mails[-1][0].endswith("ALERT: B")


def test_disabled_or_unconfigured_sends_nothing():
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock, _settings(alerts_enabled="false"))
    assert m.raise_alert("a", "A") is False and m.is_open("a")
    m2 = _manager(spy, clock, _settings(alerts_smtp_host="", alerts_telegram_token=""))
    assert m2.raise_alert("a", "A") is False
    assert not spy.mails and not spy.tgs


def test_channel_switches_2026_11_04():
    # never saved: both follow the old master switch
    s = _settings()
    assert s.enabled and s.mail_enabled and s.telegram_enabled
    assert not _settings(alerts_enabled="false").telegram_enabled
    # one switch per channel; the master switch no longer matters once they are saved
    s = _settings(
        alerts_enabled="false", alerts_mail_enabled="false", alerts_telegram_enabled="true"
    )
    assert s.enabled and not s.mail_active and s.telegram_active
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock, s)
    assert m.raise_alert("a", "A") is True
    assert not spy.mails and len(spy.tgs) == 1
    # both off: nothing is sent, the state is still tracked
    off = _settings(alerts_mail_enabled="false", alerts_telegram_enabled="false")
    assert not off.enabled
    m2 = _manager(spy, clock, off)
    assert m2.raise_alert("b", "B") is False and m2.is_open("b")
    assert len(spy.tgs) == 1
    # switched on but not set up: not active
    assert not _settings(alerts_mail_enabled="true", alerts_smtp_host="").mail_active
    # the test message ignores the switches (it tests the stored channel)
    assert _manager(spy, clock, off).send_test("mail") == ""
    assert len(spy.mails) == 1


def test_rate_limit_per_channel():
    spy, clock = Spy(), Clock()
    m = _manager(spy, clock)
    for i in range(25):
        m.raise_alert(f"k{i}", f"K{i}")
    assert len(spy.mails) == A.RATE_LIMIT_PER_HOUR and len(spy.tgs) == A.RATE_LIMIT_PER_HOUR
    clock.t += 3601
    assert m.raise_alert("late", "Late") is True


def test_send_test_reports_errors():
    spy, clock = Spy(fail=True), Clock()
    m = _manager(spy, clock)
    assert m.send_test("mail") == "smtp down"
    assert m.send_test("nope").startswith("unknown channel")
    spy.fail = False
    assert m.send_test("telegram") == "" and spy.tgs[-1].startswith(
        "[Radio Test] TEST: Test message"
    )


def test_send_mail_uses_starttls_and_login(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            calls.append(("connect", host, port))

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, context=None):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user, password))

        def send_message(self, msg):
            calls.append(("send", msg["To"], msg["Subject"], msg.get_content()))

        def quit(self):
            calls.append(("quit",))

    monkeypatch.setattr(A.smtplib, "SMTP", FakeSMTP)
    s = _settings(alerts_smtp_user="u", alerts_smtp_password="p")
    A.send_mail(s, "Subj", "Body")
    kinds = [c[0] for c in calls]
    assert kinds == ["connect", "ehlo", "starttls", "ehlo", "login", "send", "quit"]
    assert calls[0][1:] == ("mail.example", 587) and calls[4][1:] == ("u", "p")
    assert calls[5][1] == "a@example, b@example" and calls[5][3].strip() == "Body"


def test_send_mail_refuses_without_configuration():
    with pytest.raises(RuntimeError):
        A.send_mail(_settings(alerts_smtp_host=""), "s", "b")


def test_send_telegram_posts_json_per_chat():
    seen = []

    class Resp:
        def __init__(self, ok):
            self._ok = ok

        def read(self):
            return json.dumps({"ok": self._ok, "description": "bad"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def opener(req, timeout=None):
        body = json.loads(req.data.decode())
        seen.append((req.full_url, body["chat_id"], body["text"]))
        return Resp(body["chat_id"] != "99")

    s = _settings(alerts_telegram_chats="42, 7")
    A.send_telegram(s, "hello", opener=opener)
    assert [x[1] for x in seen] == ["42", "7"] and seen[0][0].endswith("/bot123:abc/sendMessage")
    with pytest.raises(RuntimeError, match="chat 99"):
        A.send_telegram(_settings(alerts_telegram_chats="99"), "hello", opener=opener)


def test_message_is_plain_text_email():
    # the real EmailMessage round trip: UTF-8 subject and body survive
    import smtplib as _s  # noqa: PLC0415

    captured = {}

    class FakeSMTP:
        def __init__(self, *a, **k):
            pass

        def ehlo(self):
            pass

        def starttls(self, context=None):
            pass

        def send_message(self, msg):
            captured["raw"] = msg.as_bytes()

        def quit(self):
            pass

    import pytest as _p  # noqa: PLC0415

    mp = _p.MonkeyPatch()
    mp.setattr(_s, "SMTP", FakeSMTP)
    try:
        A.send_mail(_settings(), "[Radio Test] ALERT: Stille", "Kein Ton seit 30 s – Übergabe")
    finally:
        mp.undo()
    parsed = message_from_bytes(captured["raw"])
    assert "Stille" in str(parsed["Subject"]) and "Übergabe" in parsed.get_payload(
        decode=True
    ).decode("utf-8")
