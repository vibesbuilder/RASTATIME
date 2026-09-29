"""
RASTATIME 2026-09-07 - the webstream watchdog lives inside Liquidsoap
(frame counter on the bus, rendered into rastatime.liq).

2026-09-15: the scheduler's telnet poll of 2026-09-06, its machine
setting ``RASTATIME_WEBSTREAM_WATCHDOG`` and the "older render still
loaded" stop-gap were removed after a quiet week.  The tests below cover
the rendered block and guard against the removed switch coming back.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout import __main__ as main
from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
from libretime_playout.liquidsoap_config import (
    DEFAULT_WEBSTREAM_WATCHDOG_CHECK_FRAMES,
    DEFAULT_WEBSTREAM_WATCHDOG_STARVE_CHECKS,
    _render_webstream_watchdog_block,
    render_rastatime_liq,
)

STREAMS = [{"type": "mp3", "host": "127.0.0.1", "port": 8000, "mount": "x", "pass": "x", "bitrate": 128}]


# ---------------------------------------------------------------------------
# renderer
# ---------------------------------------------------------------------------

def test_default_render_carries_the_in_process_watchdog():
    liq = render_rastatime_liq(STREAMS, harbor_main_password="x", harbor_show_password="y")
    assert "bus.on_frame(synchronous=true" in liq
    assert f"mod {DEFAULT_WEBSTREAM_WATCHDOG_CHECK_FRAMES} == 0" in liq
    assert f"webstream_wd_starved() >= {DEFAULT_WEBSTREAM_WATCHDOG_STARVE_CHECKS}" in liq
    assert "if webstream_started() then" in liq            # 2026-09-08: fresh source per slot
    assert "ignore(webstream_stop())" in liq and "ignore(webstream_start())" in liq
    assert "webstream_raw.is_started()" not in liq
    assert "thread.run(webstream_wd_reconnect)" in liq
    assert '"watchdog", fun (_) ->' in liq                 # telnet webstream.watchdog (diagnostic)
    assert '"ready", fun (_) -> string(source.is_ready(webstream))' in liq   # diagnostic kept
    # the block must come after the final bus definition (bus.on_frame needs it)
    assert liq.index("${LOUDNESS_BLOCK}" if "${LOUDNESS_BLOCK}" in liq else "loudness limiter") < liq.index("bus.on_frame(")
    # ... and before the outputs that consume the bus (line start: the
    # template's header comment also mentions output.icecast)
    assert liq.index("bus.on_frame(") < liq.index("\noutput.icecast(")


def test_dropped_inputs_are_remembered_and_reaped():
    """2026-09-08 22:23: input.http loses a stop while polling a dead server;
    the dropped input reconnects on its own and holds a listener slot.  The
    template remembers such inputs and reaps them (start+stop) once they
    report connected."""
    liq = render_rastatime_liq(STREAMS, harbor_main_password="x", harbor_show_password="y")
    assert "webstream_zombies = ref([])" in liq
    assert 'if status_fn() != "stopped" then' in liq
    assert "[(webstream_current_name(), status_fn, webstream_reaper())]" in liq
    assert "def webstream_reap() =" in liq
    assert 'elsif string.contains(prefix="connected", st) then' in liq
    assert "reaping (start+stop)" in liq
    # the reaper closure really is start followed by stop
    i = liq.index("webstream_reaper.set(fun () -> begin")
    assert "s.start()" in liq[i:i + 120] and "s.stop()" in liq[i:i + 120]
    # reaped on every watchdog check, counters exposed
    assert "  webstream_reap()\n" in liq
    assert "zombies=#{list.length(webstream_zombies())} reaped=#{webstream_reaped()}" in liq


def test_no_webstream_input_means_no_watchdog():
    liq = render_rastatime_liq(STREAMS, webstream_enabled=False)
    assert "bus.on_frame(" not in liq
    assert "no webstream input is rendered" in liq


def test_block_clamps_silly_parameters():
    block = _render_webstream_watchdog_block(webstream_enabled=True, check_frames=0, starve_checks=-3)
    assert "mod 1 == 0" in block
    assert "webstream_wd_starved() >= 1" in block


# ---------------------------------------------------------------------------
# 2026-09-15: the scheduler poll fallback is gone - guard the removal
# ---------------------------------------------------------------------------

def test_render_has_no_scheduler_mode_any_more():
    liq = render_rastatime_liq(STREAMS, harbor_main_password="x", harbor_show_password="y")
    assert "RASTATIME_WEBSTREAM_WATCHDOG" not in liq
    assert "in-process webstream watchdog: disabled" not in liq
    with pytest.raises(TypeError):
        _render_webstream_watchdog_block(enabled=True, webstream_enabled=True)
    with pytest.raises(TypeError):
        render_rastatime_liq(STREAMS, webstream_watchdog_in_liquidsoap=False)


def test_scheduler_has_no_telnet_poll_any_more():
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    with pytest.raises(TypeError):
        ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), webstream_watchdog="scheduler")
    for name in (
        "_start_webstream_watchdog", "_stop_webstream_watchdog", "_arm_webstream_watchdog",
        "_webstream_watchdog_tick", "_reconnect_stalled_webstream",
        "_liquidsoap_has_internal_watchdog",
    ):
        assert not hasattr(ps.PlayoutScheduler, name), name
    for name in ("WEBSTREAM_WATCHDOG_LIQUIDSOAP", "WEBSTREAM_WATCHDOG_SCHEDULER",
                 "WEBSTREAM_WATCHDOG_INTERVAL_SECONDS", "WEBSTREAM_WATCHDOG_STARVE_TICKS"):
        assert not hasattr(ps, name), name


def test_main_has_no_machine_setting_any_more():
    assert not hasattr(main, "_webstream_watchdog_mode")
    assert not hasattr(main, "WEBSTREAM_WATCHDOG_ENV")


def test_engine_presence_probe_is_gone_but_the_diagnostics_stay():
    assert not hasattr(LiquidsoapPlayoutEngine, "webstream_watchdog_present")
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=1)
    client.send_command = MagicMock(return_value="checks=12 reconnects=0")
    assert client.webstream_watchdog() == "checks=12 reconnects=0"
    client.send_command.assert_called_once_with("webstream.watchdog")
    client.send_command = MagicMock(return_value="true")
    assert client.webstream_ready() == "true"
    client.send_command.assert_called_once_with("webstream.ready")


def test_webstream_start_no_longer_arms_a_poll():
    """A webstream start must only touch the engine's stream calls - no
    timer, no readiness probe."""
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock())
    assert not any(k.startswith("_webstream_watchdog") for k in vars(s)), "poll state survived"
    assert "_liquidsoap_watchdog_present" not in vars(s)
