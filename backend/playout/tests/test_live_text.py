"""RASTATIME 2026-09-28 - Live Text Info (now-playing text file)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from rastatime_playout import live_text as lt
from rastatime_playout.live_text import (
    LiveTextConfig,
    LiveTextFtp,
    LiveTextWriter,
    parse_live_text_config,
)


def test_parse_config_defaults_and_ftp_json():
    cfg = parse_live_text_config({})
    assert cfg == LiveTextConfig()
    cfg = parse_live_text_config(
        {
            "live_text_enabled": "1",
            "live_text_format": "2",
            "live_text_web_enabled": "0",
            "live_text_file_path": "D:/share/now.txt",
            "live_text_ftp_config": json.dumps(
                {
                    "enabled": True,
                    "protocol": "ftps",
                    "host": "ftp.example.org",
                    "port": "2121",
                    "username": "u",
                    "password": "p",
                    "path": "/pub/",
                }
            ),
        }
    )
    assert cfg.enabled and cfg.label_format == 2 and cfg.web_enabled is False
    assert cfg.file_path == "D:/share/now.txt"
    assert cfg.ftp == LiveTextFtp(True, "ftps", "ftp.example.org", 2121, "u", "p", "/pub/")
    assert cfg.ftp.remote_path() == "/pub/now-playing.txt"
    assert LiveTextFtp(path="live.txt").remote_path() == "/live.txt"
    bad = parse_live_text_config({"live_text_format": "7", "live_text_ftp_config": "{not json"})
    assert bad.label_format == 0 and bad.ftp.enabled is False


def _writer(tmp_path: Path, cfg: LiveTextConfig, uploads=None):
    uploads = uploads if uploads is not None else []
    w = LiveTextWriter(
        lambda: cfg,
        web_dir=tmp_path / "web",
        ftp_upload=lambda f, p: uploads.append((f, p.read_text(encoding="utf-8"))),
    )
    return w, uploads


def test_update_writes_web_file_and_local_file_and_ignores_repeats(tmp_path):
    cfg = LiveTextConfig(
        enabled=True, web_enabled=True, file_path=str(tmp_path / "share" / "now.txt")
    )
    w, _ = _writer(tmp_path, cfg)
    assert w.update("  Artist  -\n Title ", wait=True) is True
    assert (tmp_path / "web" / "now-playing.txt").read_text(encoding="utf-8") == "Artist - Title\n"
    assert (tmp_path / "share" / "now.txt").read_text(encoding="utf-8") == "Artist - Title\n"
    assert not (tmp_path / "web" / "now-playing.txt.tmp").exists()
    assert w.update("Artist - Title", wait=True) is False  # same line: nothing
    assert w.update("", wait=True) is False


def test_disabled_settings_write_nothing(tmp_path):
    w, _ = _writer(tmp_path, LiveTextConfig(enabled=False))
    assert w.update("Artist - Title", wait=True) is False
    assert not (tmp_path / "web").exists()
    w2 = LiveTextWriter(lambda: None, web_dir=tmp_path / "web")
    assert w2.update("x", wait=True) is False


def test_ftp_push_on_change_and_failure_logged(tmp_path, caplog):
    ftp = LiveTextFtp(enabled=True, protocol="ftp", host="h", username="u", password="p", path="/")
    cfg = LiveTextConfig(enabled=True, web_enabled=True, ftp=ftp)
    w, uploads = _writer(tmp_path, cfg)
    w.update("A - B", wait=True)
    assert uploads == [(ftp, "A - B\n")]
    w.update("A - B", wait=True)
    assert len(uploads) == 1  # no change, no push
    failing = LiveTextWriter(
        lambda: cfg,
        web_dir=tmp_path / "web2",
        ftp_upload=MagicMock(side_effect=RuntimeError("530 login")),
    )
    failing.update("C - D", wait=True)
    assert failing.last_error == "ftp: 530 login"
    assert any("530 login" in r.getMessage() for r in caplog.records)
    assert not any("p" == r.getMessage() for r in caplog.records)


def test_ftp_only_uses_a_staging_file(tmp_path):
    ftp = LiveTextFtp(enabled=True, host="h", username="u", path="/x/")
    cfg = LiveTextConfig(enabled=True, web_enabled=False, ftp=ftp)
    w, uploads = _writer(tmp_path, cfg)
    w.update("Only FTP", wait=True)
    assert uploads[0][1] == "Only FTP\n"
    assert not (tmp_path / "web" / "now-playing.txt").exists()


def test_liquidsoap_settings_follow_the_config(tmp_path):
    w, _ = _writer(tmp_path, LiveTextConfig(enabled=True, label_format=1))
    assert w.liquidsoap_settings() == (True, 1)
    assert LiveTextWriter(lambda: None, web_dir=tmp_path).liquidsoap_settings() is None


def test_sftp_needs_a_curl_with_libssh2(monkeypatch, tmp_path):
    monkeypatch.setattr(lt, "_find_curl_with_libssh2", lambda: None)
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    try:
        lt.upload_ftp(LiveTextFtp(enabled=True, protocol="sftp", host="h", username="u"), f)
    except RuntimeError as exc:
        assert "libssh2" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


# ---------------------------------------------------------------------------
# render + listener + scheduler
# ---------------------------------------------------------------------------


def test_icy_block_renders_label_for_and_live_text_hook():
    from rastatime_playout import liquidsoap_config as lc

    block = lc._render_icy_metadata_block(
        0, "Back soon", "RASTATIME", live_text_url="http://127.0.0.1:8770/live-text"
    )
    assert "def label_for(fmt, m) =" in block
    assert "def icy_label(m) =\n  label_for(icy_format(), m)\nend" in block
    # no artist/title on a live source: station - show (2026-09-28, all formats)
    # RASTATIME 2026-10-14: a third "Station name - Show name" branch for icy_hide packets
    assert (
        block.count('if show != "" then "#{station_name()} - #{show}" else station_name() end') == 3
    )
    assert 'livetext_enabled = interactive.bool("livetext_enabled", false)' in block
    assert 'livetext_format = interactive.int("livetext_format", 0)' in block
    assert 'http.post(timeout=2.0, data=label, "http://127.0.0.1:8770/live-text")' in block
    off = lc._render_icy_metadata_block(0, "Back soon", "RASTATIME", live_text_url=None)
    assert "def livetext_report(_) = () end" in off


def test_full_render_hooks_live_text_on_the_bus():
    from rastatime_playout import liquidsoap_config as lc

    out = lc.render_rastatime_liq(
        [{"type": "mp3", "host": "h", "port": 8000, "mount": "m", "pass": "x", "bitrate": 128}],
    )
    assert "bus.on_metadata(synchronous=true, livetext_report)" in out
    assert out.index("bus.on_metadata(synchronous=true, livetext_report)") < out.index(
        'bus = metadata.map(id="icy_rewrite"'
    )


def test_listener_endpoint_feeds_the_writer():
    from rastatime_playout import source_switcher as ss

    writer = MagicMock(spec=LiveTextWriter)
    ss._EventHandler.live_text = writer
    handler = ss._EventHandler.__new__(ss._EventHandler)
    handler.headers = {"Content-Length": "14"}
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = b"Artist - Title"
    sent = []
    handler._send = lambda code, body: sent.append((code, body))
    handler._handle_live_text()
    writer.update.assert_called_once_with("Artist - Title")
    assert sent == [(200, "ok")]
    ss._EventHandler.live_text = None
    handler._handle_live_text()
    assert sent[-1][0] == 503


def test_scheduler_pushes_live_text_settings_on_change(monkeypatch):
    from rastatime_playout import playout_scheduler as ps
    from rastatime_playout.engine.interface import PlayoutState
    from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine

    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    writer = MagicMock(spec=LiveTextWriter)
    writer.liquidsoap_settings.return_value = (True, 2)
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), live_text=writer)
    s._sync_live_text_settings()
    engine.live_text_settings.assert_called_once_with(True, 2)
    s._sync_live_text_settings()
    engine.live_text_settings.assert_called_once()  # unchanged: no second push
    writer.liquidsoap_settings.return_value = (False, 2)
    s._sync_live_text_settings()
    assert engine.live_text_settings.call_count == 2


def test_start_listener_wires_the_live_text_writer(monkeypatch):
    """Regression 2026-09-28: the attribute set before start_listener() was
    overwritten by its own default - /live-text answered 503 in production."""
    from rastatime_playout import source_switcher as ss

    started = {}

    class FakeServer:
        def __init__(self, addr, handler):
            started["addr"] = addr

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr(ss, "ThreadingHTTPServer", FakeServer)
    monkeypatch.setattr(ss.threading, "Thread", lambda **kw: MagicMock())
    writer = MagicMock(spec=LiveTextWriter)
    ss.start_listener(MagicMock(), host="127.0.0.1", port=0, live_text=writer)
    assert ss._EventHandler.live_text is writer
    ss._EventHandler.live_text = None
