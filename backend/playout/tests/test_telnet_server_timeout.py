"""
RASTATIME 2026-09-09 - the Liquidsoap telnet server must not drop idle
clients.  PLAYOUT keeps two persistent telnet clients (scheduler and
source switcher); with the default 30-s server timeout both reconnected
every two minutes, and every new telnet connection leaks ~262 KB on the
Windows build - the whole idle growth left after the event-driven source
switcher (measured 14 MB/h, 30 reconnects in 30 min).
"""

from __future__ import annotations

from rastatime_playout import liquidsoap_config as lc

LINE = "settings.server.timeout.set(-1.)"


def _stream():
    return {
        "type": "mp3",
        "host": "localhost",
        "port": 8000,
        "mount": "rastatime",
        "pass": "hackme",
        "user": "source",
        "bitrate": 128,
        "name": "RASTATIME",
        "description": "Live stream",
    }


def test_render_disables_the_telnet_server_timeout():
    out = lc.render_rastatime_liq([_stream()])
    active = [ln.strip() for ln in out.splitlines() if not ln.lstrip().startswith("#")]
    assert LINE in active
    # settings block: right after the telnet server is enabled, before the log settings
    assert out.index("settings.server.telnet.set(true)") < out.index(LINE)
    assert out.index(LINE) < out.index("settings.log.file.path.set(")


def test_standby_render_has_no_telnet_and_no_timeout_line():
    out = lc.render_standby_liq([_stream()])
    assert "settings.server.telnet.set(false)" in out or "settings.server.telnet := false" in out
    assert LINE not in out
