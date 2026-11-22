"""
RASTATIME 2026-11-21 - automatic level of the live DJ inputs (Settings ->
Streams "Level live DJ inputs", operator Go: on by default, -23 LUFS fixed).

The DJ arms get Liquidsoap's ``normalize`` (LUFS mode) in front of the bus
switch; the raw harbors keep their ids for the callbacks, telnet commands and
arm conditions, the levelled sources carry their own ids for the transitions.
Without the setting (``dj_level=None``) the bus renders exactly as before.
"""

from __future__ import annotations

import pytest
from rastatime_playout import liquidsoap_config as lc

_SHOW_HOLD = (
    "source.is_ready(show_dj) and time() >= show_dj_from()"
    " and (show_dj_until() <= 0. or time() < show_dj_until())"
)


def _bus(**kw):
    base = {
        "main_enabled": True,
        "show_enabled": True,
        "webstream_enabled": True,
        "linein_enabled": True,
        "transition_seconds": 1.0,
        "dj_fade_seconds": 1.0,
        "show_hold": True,
    }
    base.update(kw)
    return lc._render_bus_source_block(**base)


def test_without_the_setting_the_bus_is_what_it_was():
    off = _bus()
    assert _bus(dj_level=None) == off
    assert "dj_level" not in off and "_lv" not in off
    assert "({source.is_ready(master_dj)}, master_dj)" in off
    assert "({" + _SHOW_HOLD + "}, show_dj)" in off


@pytest.mark.parametrize("enabled", [True, False])
def test_the_dj_arms_carry_the_levelled_sources(enabled):
    bus = _bus(dj_level=enabled)
    default = "true" if enabled else "false"
    assert f'dj_level_enabled = interactive.bool("dj_level.enabled", {default})\n' in bus
    assert 'master_dj_lv = rt_dj_level("master_dj_level", master_dj)\n' in bus
    assert 'show_dj_lv = rt_dj_level("show_dj_level", show_dj)\n' in bus
    # conditions on the raw harbors, sources levelled
    assert "({source.is_ready(master_dj)}, master_dj_lv)" in bus
    assert "({" + _SHOW_HOLD + "}, show_dj_lv)" in bus
    # the level is defined before the switch uses it
    assert bus.index("master_dj_lv = ") < bus.index("bus = switch(")


def test_the_transitions_recognise_the_levelled_dj_arms():
    bus = _bus(dj_level=True)
    assert 'source.id(old) == "master_dj_level" or source.id(old) == "show_dj_level"' in bus
    assert 'source.id(old) == "master_dj" ' not in bus


def test_the_normalize_parameters():
    block = lc._render_dj_level_block(main_enabled=True, show_enabled=False, enabled=True)
    assert "amplify(id=lid, 1.," in block
    assert (
        f'normalize(id="#{{lid}}_norm", lufs=true, window={lc.DJ_LEVEL_WINDOW_S:.1f}, '
        "target=-23.0," in block
    )
    assert (lc.DJ_LEVEL_WINDOW_S, lc.DJ_LEVEL_UP_S, lc.DJ_LEVEL_DOWN_S) == (2.0, 10.0, 0.7)
    assert lc.DJ_LEVEL_THRESHOLD_LUFS == -45.0
    assert f"up={lc.DJ_LEVEL_UP_S:.1f}, down={lc.DJ_LEVEL_DOWN_S:.1f}" in block
    assert "track_sensitive=false, enabled=dj_level_enabled" in block
    assert "show_dj_lv" not in block and "master_dj_lv" in block
    assert lc.DJ_LEVEL_TARGET_LUFS == -23.0


def test_only_the_existing_dj_arms_are_levelled():
    bus = _bus(dj_level=True, main_enabled=False)
    assert "master_dj_lv" not in bus and "show_dj_lv = " in bus


def test_no_dj_arm_no_level():
    bus = _bus(dj_level=True, main_enabled=False, show_enabled=False)
    assert "dj_level" not in bus and "rt_dj_level" not in bus


def test_with_the_schedule_under_a_dj_the_consumer_keeps_the_raw_conditions():
    bus = _bus(dj_level=True, schedule_under_dj=True)
    assert "  (source.is_ready(master_dj)) or (" + _SHOW_HOLD + ")\n" in bus


@pytest.mark.parametrize(
    ("value", "on"),
    [
        (None, True),
        ("", True),
        ("1", True),
        ("true", True),
        ("On", True),
        ("0", False),
        ("false", False),
        (" off ", False),
        ("no", False),
    ],
)
def test_the_setting_is_on_unless_explicitly_off(value, on):
    assert lc.dj_level_from_prefs(value) is on
