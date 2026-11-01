"""
RASTATIME 2026-09-10 - "UI wird zur Wahrheit": the harbors check DJ logins
through PLAYOUT (auth callback -> /dj-auth -> legacy check-live-stream-auth)
instead of a static password; the static password only counts while
PLAYOUT is unreachable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from rastatime_playout import liquidsoap_config as lc

LIQUIDSOAP_EXE = Path("C:/Tools/liquidsoap/liquidsoap.exe")


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
    return "\n".join(ln for ln in rendered.splitlines() if not ln.lstrip().startswith("#"))


def test_auth_callback_is_rendered_once_before_the_harbors():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="mpw",
            harbor_show_password="spw",
        )
    )
    assert out.count("def rastatime_dj_auth(kind, static_password) =") == 1
    assert out.index("def rastatime_dj_auth") < out.index("master_dj = input.harbor(")
    assert 'auth=rastatime_dj_auth("master", "mpw"),' in out
    assert 'auth=rastatime_dj_auth("show", "spw"),' in out
    assert '"http://127.0.0.1:8770/dj-auth"' in out
    assert "elsif verdict" in out  # Liquidsoap keyword, not elif
    assert 'login.user == "source" and login.password == static_password' in out


def test_custom_auth_url_and_no_auth():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="mpw",
            dj_auth_url="http://127.0.0.1:8771/dj-auth",
        )
    )
    assert '"http://127.0.0.1:8771/dj-auth"' in out
    off = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="mpw",
            dj_auth_url=None,
        )
    )
    assert "rastatime_dj_auth" not in off
    assert 'password="mpw"' in off  # the static password remains the check


def test_no_harbor_no_auth_function():
    out = _active(lc.render_rastatime_liq([_stream()]))
    assert "rastatime_dj_auth" not in out


def test_ports_and_mounts_are_taken_from_the_arguments():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_show_password="b",
            harbor_main_port=8011,
            harbor_show_port=8011,
            harbor_main_mount="master-in",
            harbor_show_mount="show-in",
        )
    )
    assert '"master-in",' in out and '"show-in",' in out
    assert out.count("port=8011,") == 2


def test_write_wrapper_forwards_the_auth_url(tmp_path):
    target = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(
        target,
        [_stream()],
        harbor_main_password="pw",
        dj_auth_url="http://127.0.0.1:8772/dj-auth",
    )
    assert "127.0.0.1:8772/dj-auth" in target.read_text(encoding="utf-8")


@pytest.mark.skipif(not LIQUIDSOAP_EXE.exists(), reason="liquidsoap.exe not installed")
def test_full_render_with_auth_typechecks(tmp_path):
    liq = tmp_path / "auth.liq"
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
