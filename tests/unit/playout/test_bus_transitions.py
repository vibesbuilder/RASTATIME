"""
Bus-switch gates + input transitions (RASTATIME 2026-09-04, "Paket 2"
Teil A; reshaped 2026-09-27).  The rendered .liq must

  * declare the two gates with default true (plain is_ready behaviour
    for a Pypo that never touches them),
  * AND the gates into the webstream / line-in predicates,
  * render ONE input-switch shape on the programme arms: the incoming
    source at full level at once (50 ms ramp), the outgoing one fading
    out under it over the Default SHOW Crossfade Duration (0 -> 50 ms
    cut); DJ arms stay instant,
  * bound transition_length by the fade length.
"""

import re

import pytest

from libretime_playout.liquidsoap_config import (
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


def test_positive_duration_fades_the_old_source_under_the_new_one():
    """2026-09-27: the show crossfade shape - new at once, old fades out."""
    block = _bus(transition_seconds=1.0)
    assert "fade.out(duration=1.0, old)" in block
    assert "fade.in(duration=0.05, new)" in block
    assert "fade.in(duration=1.0, new)" not in block
    assert "# input transitions: new at once, old fades out over 1.0 s" in block


def test_zero_duration_is_a_click_free_cut():
    block = _bus(transition_seconds=0.0)
    assert "fade.out(duration=0.05, old)," in block
    assert "fade.in(duration=0.05, new)" in block
    assert "fade.in(duration=1" not in block


def test_transition_list_is_aligned_with_the_arms():
    block = _bus(transition_seconds=1.0)
    trans = re.search(r"transitions=\[\n(.*?)\n  \],", block, re.DOTALL).group(1)
    arms = re.search(r"\],\n  \[\n(.*?)\n  \]\n\)", block, re.DOTALL).group(1)
    t = [x.strip().rstrip(",") for x in trans.splitlines()]
    a = [x.strip() for x in arms.splitlines()]
    assert len(t) == len(a) == 5
    # RASTATIME 2026-09-13: per-arm wrappers (ICY show_name insert / off-air mark)
    # around the shared shapes; 2026-09-28: DJ arms use bus_dj, programme
    # arms pick bus_dj when the outgoing source is a DJ.
    assert t == ["bus_arm_master", "bus_arm_show", "bus_arm_webstream", "bus_arm_linein", "bus_arm_scheduled"]
    assert block.count("s = bus_dj(old, new)") == 2 and block.count("else bus_transition(old, new) end") == 3


def test_transition_length_bounds_the_fade():
    assert "transition_length=1.5," in _bus(transition_seconds=1.0)
    assert "transition_length=2.5," in _bus(transition_seconds=2.0)
    assert "transition_length=0.55," in _bus(transition_seconds=0.0, dj_fade_seconds=0.0)
    # the DJ fade counts as well (2026-09-28): the longer of the two + 0.5 s
    assert "transition_length=1.5," in _bus(transition_seconds=0.0, dj_fade_seconds=1.0)


@pytest.mark.parametrize("duration", [0.0, 1.0, 2.5])
def test_full_render_threads_the_show_crossfade_into_the_bus(duration):
    """The bus follows the SHOW crossfade, not the track crossfade."""
    liq = render_rastatime_liq(
        _STREAMS, crossfade_duration=7.0, show_crossfade_duration=duration,
    )
    assert "linein_live = interactive.bool" in liq
    expected = duration if duration >= 0.05 else 0.05
    assert f"fade.out(duration={expected}, old)" in liq
    assert "fade.out(duration=7.0, old)" not in liq


def test_dj_arms_use_the_switch_transition_fade():
    """2026-09-28: Settings -> Streams "Switch Transition Fade" shapes the DJ
    hand-over - DJ at once, programme fades out under it; the same
    add-of-fades shape as the other arms (the 2.4.4 typer wants a
    homogeneous transition list - live outage 2026-09-04 19:26)."""
    block = _bus(transition_seconds=1.0, dj_fade_seconds=2.5)
    assert "def bus_dj(old, new) =" in block
    assert "fade.out(duration=2.5, old),\n                        fade.in(duration=0.05, new)" in block
    assert "def bus_arm_master(old, new) =  # master_dj\n  s = bus_dj(old, new)" in block
    assert "def bus_arm_show(old, new) =  # show_dj\n  s = bus_dj(old, new)" in block
    assert "= new end" not in block
    # transition_length covers the longer of the two fades
    assert "transition_length=3.0," in block


def test_programme_arms_fade_a_leaving_dj_with_the_dj_fade():
    """Hand-back: a programme arm taking over FROM a DJ uses bus_dj (the DJ
    fades out over the Switch Transition Fade), otherwise bus_transition."""
    block = _bus(transition_seconds=1.0, dj_fade_seconds=2.5)
    cond = 'if source.id(old) == "master_dj" or source.id(old) == "show_dj" then bus_dj(old, new) else bus_transition(old, new) end'
    assert block.count(cond) == 3          # webstream, linein, scheduled
    assert "bus_instant" not in block.split("def bus_instant(old, new) =")[1].split("end", 1)[1]


def test_dj_fade_zero_is_a_click_free_cut():
    block = _bus(transition_seconds=1.0, dj_fade_seconds=0.0)
    assert "def bus_dj(old, new) =\n  add(normalize=false, [fade.out(duration=0.05, old)," in block
