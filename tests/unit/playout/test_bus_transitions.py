"""
Bus-switch gates + input transitions (RASTATIME 2026-09-04, "Paket 2"
Teil A).  The rendered .liq must

  * declare the two gates with default true (plain is_ready behaviour
    for a Pypo that never touches them),
  * AND the gates into the webstream / line-in predicates,
  * render a crossfade transition for D > 0 and a ducking transition
    for D = 0, on the programme arms only (DJ arms stay instant),
  * bound transition_length by the fade length.
"""

import re

import pytest

from libretime_playout.liquidsoap_config import (
    DEFAULT_INPUT_DUCK_FADE_SECONDS,
    _render_bus_source_block,
    render_rastatime_liq,
)

_STREAMS = [
    {"type": "mp3", "host": "localhost", "port": 8000, "mount": "m",
     "pass": "x", "bitrate": 128},
]


def _bus(**kw):
    return _render_bus_source_block(main_enabled=True, show_enabled=True, **kw)


def test_gates_are_declared_open_by_default():
    block = _bus(transition_seconds=1.0)
    assert 'webstream_live = interactive.bool("webstream_live", true)' in block
    assert 'linein_live = interactive.bool("linein_live", true)' in block


def test_gates_are_anded_into_the_programme_predicates():
    block = _bus(transition_seconds=1.0)
    assert "({webstream_live() and source.is_ready(webstream)}, webstream)" in block
    assert "({linein_live() and source.is_ready(linein)}, linein)" in block
    # DJ arms are untouched
    assert "({source.is_ready(master_dj)}, master_dj)" in block
    assert "({source.is_ready(show_dj)}, show_dj)" in block


def test_positive_duration_renders_a_crossfade():
    block = _bus(transition_seconds=1.0)
    assert "fade.out(duration=1.0, old)" in block
    assert "fade.in(duration=1.0, new)" in block
    assert "# input transitions: crossfade 1.0 s" in block


def test_zero_duration_renders_ducking_with_the_fixed_fade():
    block = _bus(transition_seconds=0.0)
    assert f"fade.out(duration={DEFAULT_INPUT_DUCK_FADE_SECONDS:.1f}, old)," in block
    # the new source gets only a 50 ms click-free ramp (= "at once"); it
    # also keeps both add() elements the same source type, which the
    # switch's transition signature requires (2.4.4 type error otherwise)
    assert "fade.in(duration=0.05, new)" in block
    assert "fade.in(duration=1" not in block
    assert "ducking" in block


def test_transition_list_is_aligned_with_the_arms():
    block = _bus(transition_seconds=1.0)
    trans = re.search(r"transitions=\[\n(.*?)\n  \],", block, re.DOTALL).group(1)
    arms = re.search(r"\],\n  \[\n(.*?)\n  \]\n\)", block, re.DOTALL).group(1)
    t = [x.strip().rstrip(",") for x in trans.splitlines()]
    a = [x.strip() for x in arms.splitlines()]
    assert len(t) == len(a) == 5
    assert t == ["bus_instant", "bus_instant", "bus_transition", "bus_transition", "bus_transition"]


def test_transition_length_bounds_the_fade():
    assert "transition_length=1.5," in _bus(transition_seconds=1.0)
    assert "transition_length=2.5," in _bus(transition_seconds=2.0)
    assert f"transition_length={DEFAULT_INPUT_DUCK_FADE_SECONDS + 0.5:.1f}," in _bus(transition_seconds=0.0)


@pytest.mark.parametrize("duration", [0.0, 1.0])
def test_full_render_threads_the_house_crossfade_into_the_bus(duration):
    liq = render_rastatime_liq(_STREAMS, crossfade_duration=duration)
    assert "linein_live = interactive.bool" in liq
    if duration > 0:
        assert f"fade.out(duration={duration:.1f}, old)" in liq
    else:
        assert "ducking" in liq
