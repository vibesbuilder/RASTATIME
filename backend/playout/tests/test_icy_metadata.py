"""
RASTATIME 2026-09-13 — ICY metadata: Stream Label, Off Air Metadata, show
names for live sources, mount genre/url (work-order point 8).

Covers the preference parser, the rendered ICY block + per-arm bus
transitions, the Icecast block extras, the telnet wire forms, the engine
wrappers and the scheduler's refresh-time sync.  A full render is type-
checked with the installed liquidsoap.exe when available.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from libretime_playout import icy_metadata as im
from libretime_playout import liquidsoap_config as lc
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
from libretime_playout.player.events import EventKind, FileEvent, WebStreamEvent
import libretime_playout.playout_scheduler as ps

LIQUIDSOAP_EXE = Path("C:/Tools/liquidsoap/liquidsoap.exe")


def _stream(**over):
    out = {
        "type": "mp3", "host": "localhost", "port": 8000, "mount": "rastatime",
        "pass": "hackme", "user": "source", "bitrate": 128,
        "name": "RASTATIME", "description": "Live stream",
    }
    out.update(over)
    return out


# ---- preference parsing ------------------------------------------------


def test_parse_defaults_for_missing_keys():
    prefs = im.parse_icy_preferences({})
    assert prefs == im.IcyPreferences(0, "Offline", "RASTATIME")


def test_parse_reads_the_three_keys():
    prefs = im.parse_icy_preferences({
        "stream_label_format": "2",
        "off_air_meta": "  RASTATIME back on air soon ",
        "station_name": "Example Radio",
    })
    assert prefs.label_format == 2
    assert prefs.offair_text == "RASTATIME back on air soon"
    assert prefs.station_name == "Example Radio"


@pytest.mark.parametrize("raw", ["", None, "x", "7", "-1"])
def test_parse_bad_format_falls_back_to_zero(raw):
    assert im.parse_icy_preferences({"stream_label_format": raw}).label_format == 0


def test_parse_collapses_line_breaks():
    prefs = im.parse_icy_preferences({"off_air_meta": "back\r\non\nair"})
    assert prefs.offair_text == "back on air"


# ---- renderer: ICY block, outputs, bus arms -----------------------------


def test_icy_block_renders_defaults_and_label_function():
    out = lc._render_icy_metadata_block(1, 'Back "soon"', "Example Radio")
    assert 'icy_format = interactive.int("icy_format", 1)' in out
    assert 'offair_text = interactive.string("offair_text", "Back \\"soon\\"")' in out
    assert 'station_name = interactive.string("station_name", "Example Radio")' in out
    assert 'bus_show = interactive.string("bus_show", "")' in out
    assert "def icy_label(m) =" in out
    assert "def icy_rewrite(m) =" in out and "def icy_song_title(m) =" in out
    assert 'namespace="icy"' in out


def test_icy_block_rejects_unknown_format():
    assert 'interactive.int("icy_format", 0)' in lc._render_icy_metadata_block(9, "x", "y")


def test_icecast_block_has_icy_song_genre_url():
    out = lc._render_icecast_block(_stream(genre="Community", url="https://example.org"))
    assert "  icy_song=icy_song_title,\n" in out
    assert "icy_metadata" not in out
    assert '  genre="Community",\n' in out
    assert '  url="https://example.org",\n' in out


def test_icecast_block_falls_back_to_the_station_name():
    out = lc._render_icecast_block(_stream(name="", description=""), station_name="Example Radio")
    assert '  name="Example Radio",\n' in out
    assert '  description="Example Radio live stream",\n' in out
    assert "genre=" not in out and "url=" not in out


def test_icecast_block_without_icy_song_for_the_standby_script():
    out = lc._render_icecast_block(_stream(), icy_song=None)
    assert "icy_song" not in out and "icy_metadata" not in out
    standby = lc.render_standby_liq([_stream()])
    assert "icy_song" not in standby and "icy_label" not in standby


def test_full_render_has_icy_block_and_offair_fallback():
    out = lc.render_rastatime_liq(
        [_stream()], icy_label_format=2, icy_offair_text="Pause", icy_station_name="Example Radio",
    )
    assert "${ICY_METADATA_BLOCK}" not in out
    assert 'interactive.int("icy_format", 2)' in out
    assert 'interactive.string("offair_text", "Pause")' in out
    assert "def offair_mark() =" in out
    assert "transitions=[scheduled_keep, scheduled_offair]" in out
    assert 'bus = metadata.map(id="icy_rewrite"' in out
    assert out.index("def icy_rewrite(m) =") < out.index('metadata.map(id="icy_rewrite"')
    assert out.index("def icy_label(m) =") < out.index("def offair_mark() =") < out.index("\noutput.icecast(\n")
    assert '  name="RASTATIME",\n' in out          # the stream's own name wins


def test_bus_block_wraps_every_arm():
    out = lc._render_bus_source_block(
        main_enabled=True, show_enabled=True, webstream_enabled=True, linein_enabled=True,
    )
    for name, source in (("bus_arm_master", "master_dj"), ("bus_arm_show", "show_dj"),
                         ("bus_arm_webstream", "webstream"), ("bus_arm_linein", "linein")):
        assert f"def {name}(old, new) =  # {source}" in out
    assert out.count('  s.insert_metadata([("show_name", bus_show())])') == 4
    assert "def bus_arm_scheduled(old, new) =" in out
    assert "  if not source.is_ready(scheduled_q) then" in out
    assert '    s.insert_metadata([("off_air", "true"), ("title", offair_text())])' in out
    assert "transitions=[\n    bus_arm_master,\n    bus_arm_show,\n    bus_arm_webstream,\n    bus_arm_linein,\n    bus_arm_scheduled,\n  ]" in out


def test_bus_block_without_upstream_arms_is_unchanged():
    out = lc._render_bus_source_block(
        main_enabled=False, show_enabled=False, webstream_enabled=False, linein_enabled=False,
    )
    assert out == "bus = scheduled\n"


@pytest.mark.skipif(not LIQUIDSOAP_EXE.exists(), reason="liquidsoap.exe not installed")
def test_full_render_with_all_arms_typechecks(tmp_path):
    liq = tmp_path / "icy.liq"
    liq.write_text(
        lc.render_rastatime_liq(
            [_stream(genre="Community", url="https://example.org")],
            harbor_main_password="a", harbor_show_password="b",
            webstream_enabled=True, linein_enabled=True,
            icy_label_format=1, icy_offair_text="Back soon", icy_station_name="Example Radio",
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(LIQUIDSOAP_EXE), "--check", str(liq)],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---- telnet wire forms ---------------------------------------------------


def test_var_set_string_sends_raw_one_line_text():
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=1)
    client.send_command = MagicMock(return_value="Variable offair_text set.")
    client.var_set_string("offair_text", "  Back\r\non air  ")
    client.send_command.assert_called_once_with("var.set offair_text = Back on air")


def test_var_set_string_replaces_the_separator():
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=1)
    client.send_command = MagicMock(return_value="ok")
    client.var_set_string("bus_show", "A = B")
    client.send_command.assert_called_once_with("var.set bus_show = A - B")


def test_var_set_int_and_icy_status():
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=1)
    client.send_command = MagicMock(return_value="ok")
    client.var_set_int("icy_format", 2)
    client.icy_status()
    assert [c.args[0] for c in client.send_command.call_args_list] == [
        "var.set icy_format = 2", "icy.status",
    ]


# ---- engine wrappers ---------------------------------------------------


def _engine():
    telnet = MagicMock(spec=LiquidsoapTelnetClient)
    telnet._host, telnet._port = "127.0.0.1", 1234
    return LiquidsoapPlayoutEngine(telnet_client=telnet), telnet


def test_engine_icy_settings_pushes_three_variables():
    engine, telnet = _engine()
    engine.icy_settings(1, "Back soon", "Example Radio")
    telnet.var_set_int.assert_called_once_with("icy_format", 1)
    assert [c.args for c in telnet.var_set_string.call_args_list] == [
        ("offair_text", "Back soon"), ("station_name", "Example Radio"),
    ]


def test_engine_icy_settings_and_bus_show_are_fail_soft():
    engine, telnet = _engine()
    telnet.var_set_int.side_effect = ConnectionError("down")
    telnet.var_set_string.side_effect = ConnectionError("down")
    engine.icy_settings(0, "x", "y")          # must not raise
    engine.bus_show_set("Morning Show")       # must not raise


def test_engine_bus_show_set():
    engine, telnet = _engine()
    engine.bus_show_set("Morning Show")
    telnet.var_set_string.assert_called_once_with("bus_show", "Morning Show")


# ---- scheduler: refresh-time sync -------------------------------------


def _file_event(start, minutes=10, show="Morning Show", row_id=1):
    return FileEvent(
        type=EventKind.FILE, row_id=row_id, start=start, end=start + timedelta(minutes=minutes),
        uri=f"http://api/files/{row_id}", id=row_id, show_name=show,
        fade_in=0.0, fade_out=0.0, cue_in=0.0, cue_out=60.0, mime="audio/mp3",
        replay_gain=0.0, filesize=1,
    )


def _scheduler(monkeypatch, read_prefs):
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    with patch("libretime_playout.playout_scheduler.FfmpegLineinCapture"):
        s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), read_icy_preferences=read_prefs)
    return s, engine


def _refresh(sched, events):
    with patch("libretime_playout.playout_scheduler.get_schedule", return_value=events):
        sched.refresh()
    sched._cancel_all_timers()


def test_refresh_pushes_preferences_once_and_again_on_change(monkeypatch):
    prefs = [im.IcyPreferences(0, "Back soon", "RASTATIME")]
    s, engine = _scheduler(monkeypatch, lambda: prefs[0])
    _refresh(s, {})
    _refresh(s, {})
    engine.icy_settings.assert_called_once_with(0, "Back soon", "RASTATIME")
    prefs[0] = im.IcyPreferences(2, "Back soon", "RASTATIME")
    _refresh(s, {})
    assert engine.icy_settings.call_count == 2
    assert engine.icy_settings.call_args.args == (2, "Back soon", "RASTATIME")


def test_refresh_sets_bus_show_from_the_item_on_air(monkeypatch):
    s, engine = _scheduler(monkeypatch, None)
    now = datetime.utcnow()
    events = {"a": _file_event(now - timedelta(minutes=2), show="Morning Show"),
              "b": _file_event(now + timedelta(minutes=30), show="Later Show", row_id=2)}
    _refresh(s, events)
    engine.bus_show_set.assert_called_once_with("Morning Show")
    engine.icy_settings.assert_not_called()      # no reader -> nothing pushed
    _refresh(s, {})                              # nothing on air any more
    assert engine.bus_show_set.call_args.args == ("",)


def test_slot_start_sets_bus_show_only_on_change(monkeypatch):
    s, engine = _scheduler(monkeypatch, None)
    now = datetime.utcnow()
    for name in ("_cue_item_start", "_notify_media_started", "_close_predecessor_source",
                 "_arm_stop_timer", "_ensure_file_cached"):
        setattr(s, name, MagicMock(return_value="C:/cache/1.mp3"))
    s._on_file_start("k1", _file_event(now, show="Morning Show"))
    s._on_file_start("k2", _file_event(now, show="Morning Show", row_id=2))
    engine.bus_show_set.assert_called_once_with("Morning Show")
    s._on_webstream_start("k3", WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START, row_id=3, id=3, start=now,
        end=now + timedelta(minutes=5), uri="http://stream.example/x", show_name="Web Show",
    ))
    assert engine.bus_show_set.call_args.args == ("Web Show",)


def test_liquidsoap_restart_repushes_the_values(monkeypatch):
    s, engine = _scheduler(monkeypatch, lambda: im.IcyPreferences(1, "Back soon", "RASTATIME"))
    _refresh(s, {})
    engine.icy_settings.assert_called_once()
    s._apply_initial_liquidsoap_state()          # what a detected restart runs
    _refresh(s, {})
    assert engine.icy_settings.call_count == 2


def test_engine_without_icy_methods_is_skipped(monkeypatch):
    from libretime_playout.engine.interface import PlayoutEngine
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=PlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    with patch("libretime_playout.playout_scheduler.FfmpegLineinCapture"):
        s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(),
                                read_icy_preferences=lambda: im.IcyPreferences())
    _refresh(s, {})                              # no AttributeError
