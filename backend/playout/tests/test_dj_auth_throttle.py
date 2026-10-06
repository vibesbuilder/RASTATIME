"""
RASTATIME 2026-10-06 - brute-force brake for the DJ harbor: after `limit`
rejections inside `window` seconds an address is refused for `block`
seconds without asking the web application; an accepted login clears it.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from libretime_playout.dj_auth import DjAuthenticator, RejectThrottle


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


def _session(status=401, header="0"):
    session = MagicMock()
    session.post.return_value = SimpleNamespace(status_code=status, headers={"icecast-auth-user": header})
    return session


def test_block_after_limit_inside_window():
    clock = Clock()
    t = RejectThrottle(limit=5, window=600, block=900, clock=clock)
    for i in range(4):
        assert t.rejected("1.2.3.4") is False
        clock.now += 10
    assert t.rejected("1.2.3.4") is True          # fifth inside 10 min
    assert 0 < t.blocked_for("1.2.3.4") <= 900
    clock.now += 899
    assert t.blocked_for("1.2.3.4") > 0
    clock.now += 2
    assert t.blocked_for("1.2.3.4") == 0          # block expired


def test_old_rejections_fall_out_of_the_window():
    clock = Clock()
    t = RejectThrottle(limit=5, window=600, block=900, clock=clock)
    for _ in range(4):
        t.rejected("5.6.7.8")
    clock.now += 601                               # the four are stale now
    assert t.rejected("5.6.7.8") is False
    assert t.blocked_for("5.6.7.8") == 0


def test_addresses_are_independent_and_accept_clears():
    clock = Clock()
    t = RejectThrottle(limit=2, window=600, block=900, clock=clock)
    t.rejected("a")
    t.rejected("b")
    assert t.rejected("a") is True
    assert t.blocked_for("b") == 0
    t.accepted("a")
    assert t.blocked_for("a") == 0


def test_authenticator_refuses_blocked_address_without_calling_the_web_app(caplog):
    clock = Clock()
    throttle = RejectThrottle(limit=2, window=600, block=900, clock=clock)
    session = _session(401, "0")
    auth = DjAuthenticator("http://127.0.0.1", session=session, throttle=throttle)
    assert auth.check("show", "dj", "wrong", "9.9.9.9") == "denied"
    assert auth.check("show", "dj", "wrong", "9.9.9.9") == "denied"   # triggers the block
    calls = session.post.call_count
    with caplog.at_level("WARNING"):
        assert auth.check("show", "dj", "right?", "9.9.9.9") == "denied"
    assert session.post.call_count == calls                           # not asked
    assert any("blocked for another" in r.getMessage() for r in caplog.records)
    # another address is unaffected
    assert auth.check("show", "dj", "wrong", "8.8.8.8") == "denied"
    assert session.post.call_count == calls + 1


def test_accept_clears_the_counter():
    clock = Clock()
    throttle = RejectThrottle(limit=3, window=600, block=900, clock=clock)
    session = _session(401, "0")
    auth = DjAuthenticator("http://127.0.0.1", session=session, throttle=throttle)
    auth.check("show", "dj", "wrong", "7.7.7.7")
    auth.check("show", "dj", "wrong", "7.7.7.7")
    session.post.return_value = SimpleNamespace(status_code=200, headers={"icecast-auth-user": "1"})
    assert auth.check("show", "dj", "right", "7.7.7.7") == "ok"
    session.post.return_value = SimpleNamespace(status_code=401, headers={"icecast-auth-user": "0"})
    assert auth.check("show", "dj", "wrong", "7.7.7.7") == "denied"
    assert throttle.blocked_for("7.7.7.7") == 0                       # counter restarted


def _session_reason(reason):
    session = MagicMock()
    session.post.return_value = SimpleNamespace(
        status_code=401, headers={"icecast-auth-user": "0", "x-rastatime-auth-reason": reason}
    )
    return session


def test_no_show_and_not_host_do_not_count(caplog):
    clock = Clock()
    throttle = RejectThrottle(limit=2, window=600, block=900, clock=clock)
    auth = DjAuthenticator("http://127.0.0.1", session=_session_reason("no-show"), throttle=throttle)
    with caplog.at_level("INFO"):
        for _ in range(5):
            assert auth.check("show", "dj", "pw", "4.4.4.4") == "denied"
    assert throttle.blocked_for("4.4.4.4") == 0
    assert any("no-show, not counted" in r.getMessage() for r in caplog.records)
    auth2 = DjAuthenticator("http://127.0.0.1", session=_session_reason("not-host"), throttle=throttle)
    for _ in range(5):
        auth2.check("show", "dj", "pw", "4.4.4.4")
    assert throttle.blocked_for("4.4.4.4") == 0
    # a real bad password still counts - and the missing header too
    auth3 = DjAuthenticator("http://127.0.0.1", session=_session_reason("bad-password"), throttle=throttle)
    auth3.check("show", "dj", "pw", "4.4.4.4")
    auth3.check("show", "dj", "pw", "4.4.4.4")
    assert throttle.blocked_for("4.4.4.4") > 0


def test_snapshot_and_unblock():
    clock = Clock()
    t = RejectThrottle(limit=2, window=600, block=900, clock=clock)
    t.rejected("1.1.1.1")                      # counting only
    t.rejected("2.2.2.2"); t.rejected("2.2.2.2")   # blocked
    rows = {r["address"]: r for r in t.snapshot()}
    assert rows["1.1.1.1"]["blocked_seconds_left"] == 0 and rows["1.1.1.1"]["rejections_in_window"] == 1
    assert rows["2.2.2.2"]["blocked_seconds_left"] == 900
    assert t.unblock("2.2.2.2") is True
    assert t.blocked_for("2.2.2.2") == 0
    assert t.unblock("9.9.9.9") is False
    clock.now += 601
    assert t.snapshot() == []                  # stale counters disappear
