"""
RASTATIME 2026-09-09 - option d: the harbor sources report DJ connects
and disconnects to PLAYOUT's /source-event listener (``on_connect`` /
``on_disconnect`` -> ``http.post`` from a detached task), so PLAYOUT no
longer polls ``master_dj.status`` / ``show_dj.status`` over telnet every
5 s (every telnet command leaks ~87 KB on the Windows build).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from rastatime_playout import liquidsoap_config as lc

LIQUIDSOAP_EXE = Path("C:/Tools/liquidsoap/liquidsoap.exe")

MASTER_ON = (
    'master_dj.on_connect(synchronous=true, fun (_) -> rastatime_source_event("master", "on", 0.))'
)
MASTER_OFF = 'master_dj.on_disconnect(synchronous=true, fun () -> rastatime_source_event("master", "off", 0.))'
# 2026-11-16: with the PLAYOUT login check the show callbacks also move the
# early-login hold into the gate (show_dj_from) and clear it
SHOW_ON = (
    "show_dj.on_connect(synchronous=true, fun (_) -> begin\n"
    "  show_dj_from.set(show_dj_hold_pending())\n"
    "  show_dj_hold_pending.set(0.)\n"
    '  rastatime_source_event("show", "on", show_dj_from())\n'
    "end)"
)
SHOW_OFF = (
    "show_dj.on_disconnect(synchronous=true, fun () -> begin\n"
    "  show_dj_from.set(0.)\n"
    '  rastatime_source_event("show", "off", 0.)\n'
    "end)"
)
PROBE = 'server.register(namespace="rastatime", '


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


def _active(rendered: str) -> str:
    """The rendered script without comment lines."""
    return "\n".join(ln for ln in rendered.splitlines() if not ln.lstrip().startswith("#"))


def test_main_only_renders_master_callbacks_only():
    out = _active(lc.render_rastatime_liq([_stream()], harbor_main_password="pw"))
    assert "def rastatime_source_event(src, status, hold) =" in out
    assert MASTER_ON in out
    assert MASTER_OFF in out
    assert "show_dj.on_connect" not in out
    assert "show_dj.on_disconnect" not in out
    # default target, short timeout, POSTed from a detached task
    assert 'http.post(timeout=2.0, data="",' in out
    assert '"http://127.0.0.1:8770/source-event?source=#{src}&status=#{status}&from=#{hold}"' in out
    assert "thread.run(fun () ->" in out


def test_both_harbors_render_four_callbacks():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_show_password="b",
        )
    )
    for line in (MASTER_ON, MASTER_OFF, SHOW_ON, SHOW_OFF):
        assert line in out
    assert out.count("def rastatime_source_event") == 1


def test_probe_command_is_registered_with_the_callbacks():
    out = _active(lc.render_rastatime_liq([_stream()], harbor_main_password="pw"))
    assert PROBE in out
    assert '"source_events", fun (_) -> "on")' in out
    assert out.index(PROBE) < out.index(MASTER_ON)


def test_no_harbor_renders_no_callbacks_and_the_probe_answers_none():
    out = _active(lc.render_rastatime_liq([_stream()]))
    assert "rastatime_source_event" not in out
    # 2026-09-28: the Live Text hook has its own http.post (/live-text);
    # only the harbor callbacks must be absent here
    assert "/source-event" not in out
    # 2026-11-02: the probe stays and answers "none" so PLAYOUT knows this
    # is a setting (no DJ harbor), not an older render
    assert PROBE in out
    assert '"source_events", fun (_) -> "none")' in out


def test_source_event_url_none_disables_callbacks():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="pw",
            source_event_url=None,
        )
    )
    assert "master_dj = input.harbor" in out
    assert "rastatime_source_event" not in out
    assert PROBE not in out


def test_custom_listener_url_is_rendered():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="pw",
            source_event_url="http://127.0.0.1:8771/source-event",
        )
    )
    assert '"http://127.0.0.1:8771/source-event?source=#{src}&status=#{status}&from=#{hold}"' in out
    assert "127.0.0.1:8770/source-event" not in out


def test_callbacks_follow_the_harbor_definitions_and_precede_the_bus():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_show_password="b",
        )
    )
    assert out.index("master_dj = input.harbor") < out.index("show_dj = input.harbor")
    assert out.index("show_dj = input.harbor") < out.index("def rastatime_source_event")
    assert out.index("def rastatime_source_event") < out.index(MASTER_ON)
    assert out.index(SHOW_OFF) < out.index("bus = switch(")


def test_post_failures_are_caught_not_raised():
    out = _active(lc.render_rastatime_liq([_stream()], harbor_main_password="a"))
    block = out[out.index("def rastatime_source_event") : out.index(MASTER_ON)]
    assert "try" in block
    assert "catch err do" in block
    assert 'label="rastatime.source_event"' in block


def test_write_wrapper_forwards_the_url(tmp_path):
    target = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(
        target,
        [_stream()],
        harbor_main_password="pw",
        source_event_url="http://127.0.0.1:8772/source-event",
    )
    assert "127.0.0.1:8772/source-event?source=#{src}" in target.read_text(encoding="utf-8")


def test_early_show_login_hold_is_applied_on_connect_not_in_the_auth():
    """RASTATIME 2026-11-16 - a host of the next show may log in 5 min early.
    The auth only keeps PLAYOUT's 'ok <unix time>' (Liquidsoap runs it before
    the mount-taken check), on_connect moves it into the gate, the bus arm
    waits for the time."""
    out = _active(
        lc.render_rastatime_liq([_stream()], harbor_main_password="a", harbor_show_password="b")
    )
    assert out.count("show_dj_hold_pending = ref(0.)") == 1
    assert out.count('show_dj_from = interactive.float("show_dj_from", 0.)') == 1
    assert 'if verdict == "ok" or string.contains(prefix="ok ", verdict) then' in out
    assert 'if kind == "show" then show_dj_hold_pending.set(hold) end' in out
    assert 'if ok and kind == "show" then show_dj_hold_pending.set(0.) end' in out
    # the auth never touches the gate itself
    auth = out[out.index("def rastatime_dj_auth") : out.index("def rastatime_source_event")]
    assert "show_dj_from.set" not in auth
    assert SHOW_ON in out and SHOW_OFF in out
    assert "({source.is_ready(show_dj) and time() >= show_dj_from()}, show_dj)" in out
    # refs exist before the auth function, the gate before the bus
    assert out.index("show_dj_hold_pending = ref(0.)") < out.index("def rastatime_dj_auth")
    assert out.index("show_dj_from = interactive.float") < out.index("bus = switch(")


def test_no_early_login_without_the_login_check_or_the_show_harbor():
    plain = _active(
        lc.render_rastatime_liq(
            [_stream()], harbor_main_password="a", harbor_show_password="b", dj_auth_url=None
        )
    )
    assert "show_dj_from" not in plain and "show_dj_hold_pending" not in plain
    assert "({source.is_ready(show_dj)}, show_dj)" in plain
    assert (
        'show_dj.on_connect(synchronous=true, fun (_) -> rastatime_source_event("show", "on", 0.))'
        in plain
    )
    master_only = _active(lc.render_rastatime_liq([_stream()], harbor_main_password="a"))
    assert "show_dj_from" not in master_only and "show_dj_hold_pending" not in master_only
    assert 'if verdict == "ok" or string.contains(prefix="ok ", verdict) then' in master_only


@pytest.mark.skipif(not LIQUIDSOAP_EXE.exists(), reason="liquidsoap.exe not installed")
def test_full_render_with_both_harbors_typechecks(tmp_path):
    """The callbacks and the probe must type-check on the installed build."""
    liq = tmp_path / "optd.liq"
    liq.write_text(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_show_password="b",
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(LIQUIDSOAP_EXE), "--check", str(liq)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
