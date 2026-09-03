"""
Line-in start-gap tuning (RASTATIME 2026-09-03).

A scheduled line-in on the multichannel feeder path had ~7 s of dead
air before the first audible audio (measured 14:20 show: mount alive at
+1.8 s, Liquidsoap switched the source in at +7.0 s).  The dominant
cause was ``input.http``'s ``max_buffer`` — the source only becomes
ready once that many real seconds of audio are buffered.

Lever 1 lowers the http companion's ``max_buffer`` (4.0 -> 1.5, env
overridable) and its ``poll_delay`` (2.0 -> 0.5), so a source armed in
parallel with the feeder connects the moment the mount appears.  These
tests pin those rendered values and the env-facing thread so a refactor
cannot silently restore the long gap.
"""

import re

from libretime_playout.liquidsoap_config import (
    DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
    DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS,
    render_rastatime_liq,
)

_STREAMS = [
    {"type": "mp3", "host": "localhost", "port": 8000, "mount": "m",
     "pass": "x", "bitrate": 128},
]


def _http_block(liq: str) -> str:
    start = liq.index("linein_http_raw = input.http(")
    end = liq.index("linein_http = audio_to_stereo")
    return liq[start:end]


def _num(block: str, key: str) -> float:
    m = re.search(rf"{key}=([0-9.]+)", block)
    assert m, f"{key} not found in http block"
    return float(m.group(1))


def test_defaults_are_low_latency():
    assert DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS == 1.5
    assert DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS == 0.5


def test_rendered_http_block_uses_the_low_defaults():
    block = _http_block(render_rastatime_liq(_STREAMS))
    assert _num(block, "max_buffer") == 1.5
    assert _num(block, "poll_delay") == 0.5


def test_max_buffer_is_env_facing_and_overridable():
    """The operator A/B-tests 1.0 vs 1.5 by env var + restart; the value
    must thread all the way into the rendered script."""
    block = _http_block(
        render_rastatime_liq(_STREAMS, linein_http_max_buffer_seconds=1.0)
    )
    assert _num(block, "max_buffer") == 1.0
    # poll_delay is independent and stays low.
    assert _num(block, "poll_delay") == 0.5


def test_poll_delay_is_separately_tunable():
    block = _http_block(
        render_rastatime_liq(_STREAMS, linein_http_poll_delay_seconds=0.25)
    )
    assert _num(block, "poll_delay") == 0.25


def test_http_max_buffer_is_not_the_dshow_max_buffer():
    """The dshow path (linein_raw) and the http path (linein_http) have
    independent buffers; tuning one must not move the other."""
    liq = render_rastatime_liq(
        _STREAMS,
        linein_max_buffer_seconds=2.0,
        linein_http_max_buffer_seconds=1.0,
    )
    assert _num(_http_block(liq), "max_buffer") == 1.0
    # the dshow source keeps its own value
    dshow = liq[liq.index("linein_raw = input.ffmpeg"):liq.index("linein_dshow =")]
    assert "max_buffer=2." in dshow
