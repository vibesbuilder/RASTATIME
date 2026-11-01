"""RASTATIME 2026-09-28 - TuneIn now-playing pushes from the playout."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.player.events import EventKind, FileEvent
from rastatime_playout.tunein import KEEPALIVE_SECONDS, TuneInConfig, TuneInPusher

OK_XML = "<RadioTime><head><status>200</status></head></RadioTime>"
BAD_XML = (
    "<RadioTime><head><status>403</status><fault>Invalid partner key</fault></head></RadioTime>"
)


class FakeSession:
    def __init__(self, status=200, text=OK_XML, raise_exc=None):
        self.calls = []
        self.status, self.text, self.raise_exc = status, text, raise_exc

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        if self.raise_exc:
            raise self.raise_exc
        return SimpleNamespace(status_code=self.status, text=self.text)


def _cfg(enabled=True, **kw):
    base = dict(station_id="s123", partner_id="p1", partner_key="secret-key")
    base.update(kw)
    return TuneInConfig(enabled=enabled, **base)


def _pusher(cfg, session=None, clock=None):
    t = {"now": 1000.0}
    return TuneInPusher(
        lambda: cfg,
        session=session or FakeSession(),
        clock=clock or (lambda: t["now"]),
        api_url="https://tunein.test/Playing.ashx",
    ), t


def test_push_sends_credentials_and_metadata():
    session = FakeSession()
    p, _ = _pusher(_cfg(), session)
    assert p.push("Song", "Band") is True
    url, params, timeout = session.calls[0]
    assert url == "https://tunein.test/Playing.ashx"
    assert params == {
        "partnerId": "p1",
        "partnerKey": "secret-key",
        "id": "s123",
        "title": "Song",
        "artist": "Band",
        "commercial": "false",
    }
    assert timeout == 10.0
    assert p.last_ok is True


def test_disabled_or_incomplete_settings_send_nothing(caplog):
    session = FakeSession()
    p, _ = _pusher(_cfg(enabled=False), session)
    assert p.push("Song", "Band") is False
    p2, _ = _pusher(_cfg(partner_key=""), session)
    assert p2.push("Song", "Band") is False
    assert p2.push("Song", "Band") is False  # warning only once
    assert session.calls == []
    assert sum("incomplete" in r.getMessage() for r in caplog.records) == 1
    p3, _ = _pusher(None, session)
    assert p3.push("Song", "Band") is False


def test_rejections_and_network_errors_are_logged_without_the_key(caplog):
    p, _ = _pusher(_cfg(), FakeSession(text=BAD_XML))
    assert p.push("Song", "Band") is False
    assert any("Invalid partner key" in r.getMessage() for r in caplog.records)
    p2, _ = _pusher(_cfg(), FakeSession(raise_exc=RuntimeError("timeout")))
    assert p2.push("Song", "Band") is False
    p3, _ = _pusher(_cfg(), FakeSession(status=500, text="oops"))
    assert p3.push("Song", "Band") is False
    p4, _ = _pusher(_cfg(), FakeSession(text="<html>not xml"))
    assert p4.push("Song", "Band") is False
    assert not any("secret-key" in r.getMessage() for r in caplog.records)


def test_keepalive_resends_after_the_interval_only():
    session = FakeSession()
    p, t = _pusher(_cfg(), session)
    p.keepalive()  # nothing on air yet
    assert session.calls == []
    p.push("Song", "Band")
    t["now"] += KEEPALIVE_SECONDS - 1
    p.keepalive()
    for th in threading.enumerate():
        if th.name == "tunein-push":
            th.join(2)
    assert len(session.calls) == 1
    t["now"] += 2
    p.keepalive()
    for th in threading.enumerate():
        if th.name == "tunein-push":
            th.join(2)
    assert len(session.calls) == 2
    assert session.calls[1][1]["title"] == "Song"


def test_now_playing_cleans_and_remembers_the_payload():
    session = FakeSession()
    p, _ = _pusher(_cfg(), session)
    p.now_playing("  Song\n  Title ", None, kind="track")
    for th in threading.enumerate():
        if th.name == "tunein-push":
            th.join(2)
    assert session.calls[0][1]["title"] == "Song Title"
    assert session.calls[0][1]["artist"] == ""
    assert p._last_payload == ("Song Title", "")
    p.now_playing("", "", kind="webstream")
    assert p._last_payload == ("n/a", "")


# ---------------------------------------------------------------------------
# scheduler integration
# ---------------------------------------------------------------------------


def _file(start, row_id, title="t", artist="a"):
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=180),
        row_id=row_id,
        id=row_id,
        uri="C:/media/a.mp3",
        show_name="night",
        cue_in=0.0,
        cue_out=180.0,
        track_title=title,
        artist_name=artist,
        replay_gain=None,
        fade_in=0.0,
        fade_out=0.0,
        mime="audio/mpeg",
        filesize=1000,
    )


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    engine.playing_remaining_seconds.return_value = None
    tunein = MagicMock(spec=TuneInPusher)
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), tunein=tunein)
    s.reset_gates = MagicMock()
    s._switcher = None
    s._ensure_file_cached = MagicMock(return_value="C:/cache/a.mp3")
    s._notify_media_started = MagicMock()
    s._set_bus_show = MagicMock()
    return s, tunein


def test_file_start_pushes_title_and_artist(sched):
    s, tunein = sched
    s._on_file_start("k", _file(datetime.utcnow(), 1, "Song", "Band"))
    tunein.now_playing.assert_called_once_with("Song", "Band", kind="track")


def test_live_inputs_push_the_show_name(sched):
    s, tunein = sched
    s._tunein_now_playing("webstream", title=None, artist=None, show="Morning Show")
    tunein.now_playing.assert_called_with("Morning Show", "", kind="webstream")


def test_refresh_hook_calls_keepalive(sched):
    s, tunein = sched
    s._tunein_keepalive()
    tunein.keepalive.assert_called_once()
    s._tunein = None
    s._tunein_keepalive()  # no pusher: no error
