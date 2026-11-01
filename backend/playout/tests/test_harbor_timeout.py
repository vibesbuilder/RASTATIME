"""
RASTATIME 2026-09-09 - input.harbor ``timeout`` rendered as 5 s.  The
Windows build notices a DJ client that merely closes its socket only when
this timeout expires (Liquidsoap default 30 s); PLAYOUT pushes no tracks
while it believes a DJ is live, so a hang-up meant up to 25 s of an
empty queue.  5 s matches the harbor buffer (replica: reported after
5.06 s).
"""

from __future__ import annotations

from rastatime_playout import liquidsoap_config as lc


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


def _harbor_blocks(active: str):
    """Text of each input.harbor(...) call."""
    blocks = []
    start = 0
    while True:
        i = active.find("input.harbor(", start)
        if i < 0:
            return blocks
        j = active.index("\n)", i)
        blocks.append(active[i:j])
        start = j


def test_default_timeout_is_five_seconds_on_both_harbors():
    assert lc.DEFAULT_HARBOR_TIMEOUT_SECONDS == 5.0
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_show_password="b",
        )
    )
    blocks = _harbor_blocks(out)
    assert len(blocks) == 2
    for block in blocks:
        assert "timeout=5.0," in block
        assert "icy=true," in block


def test_custom_timeout_is_rendered():
    out = _active(
        lc.render_rastatime_liq(
            [_stream()],
            harbor_main_password="a",
            harbor_timeout_seconds=3.0,
        )
    )
    (block,) = _harbor_blocks(out)
    assert "timeout=3.0," in block
    assert "timeout=5.0" not in block


def test_write_wrapper_forwards_the_timeout(tmp_path):
    target = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(
        target,
        [_stream()],
        harbor_main_password="a",
        harbor_timeout_seconds=2.5,
    )
    assert "timeout=2.5," in target.read_text(encoding="utf-8")


def test_no_harbor_no_timeout_line():
    out = _active(lc.render_rastatime_liq([_stream()]))
    assert _harbor_blocks(out) == []
    assert "input.harbor(" not in out
