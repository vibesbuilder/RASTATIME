"""
RASTATIME 2026-09-09 - standby.liq: the Icecast fallback source rendered from
the same stream outputs as rastatime.liq (same encoders, mounts + "-standby",
no telnet, silence or a configured loop).
"""
from __future__ import annotations

import re

from libretime_playout.liquidsoap_config import (
    render_rastatime_liq,
    render_standby_liq,
    standby_mount,
    write_standby_liq,
)

STREAMS = [
    {"type": "mp3", "host": "127.0.0.1", "port": 8000, "mount": "/rastatime", "pass": "x", "bitrate": 320, "name": "Rastatime"},
    {"type": "aac", "host": "127.0.0.1", "port": 8000, "mount": "rastatime-aac", "pass": "x", "bitrate": 320},
    {"type": "ogg", "host": "127.0.0.1", "port": 8000, "mount": "/rastatime-ogg", "pass": "x", "bitrate": 128},
]


def _encoders(liq: str) -> list:
    # active lines only - the template carries a commented %ffmpeg example
    return [l.strip() for l in liq.splitlines() if l.strip().startswith("%ffmpeg(format=")]


def test_standby_mount_suffix():
    assert standby_mount("/rastatime") == "/rastatime-standby"
    assert standby_mount("rastatime-aac") == "/rastatime-aac-standby"


def test_standby_uses_the_main_encoders_on_standby_mounts():
    main = render_rastatime_liq(STREAMS)
    standby = render_standby_liq(STREAMS)
    # the main render's first three encoder lines are the Icecast outputs
    # (the fourth is the recording output.file) - same codec / rate / bitrate
    assert _encoders(standby) == _encoders(main)[:3]
    assert re.findall(r'mount="([^"]+)"', standby) == [
        "/rastatime-standby", "/rastatime-aac-standby", "/rastatime-ogg-standby",
    ]
    assert 'name="Rastatime (standby)"' in standby
    assert "settings.server.telnet.set(false)" in standby   # nothing that leaks
    assert 'bus = blank(id="standby_silence")' in standby
    assert "input.http" not in standby and "server.register" not in standby


def test_standby_loop_file_is_made_safe():
    standby = render_standby_liq(STREAMS, audio_file="C:/rastatime/media/bed.mp3")
    assert 'bus = mksafe(single(id="standby_loop", "C:/rastatime/media/bed.mp3"))' in standby


def test_write_standby_is_idempotent(tmp_path):
    p = tmp_path / "standby.liq"
    assert write_standby_liq(p, STREAMS) is True
    assert write_standby_liq(p, STREAMS) is False
    assert write_standby_liq(p, STREAMS, audio_file="C:/x/bed.mp3") is True
    assert "standby_loop" in p.read_text(encoding="utf-8")
