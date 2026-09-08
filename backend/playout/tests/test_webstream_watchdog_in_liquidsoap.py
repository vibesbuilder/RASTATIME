"""
RASTATIME 2026-09-07 - the webstream watchdog moves into Liquidsoap
(frame counter on the bus, rendered into rastatime.liq); the scheduler's
telnet poll stays as an opt-in fallback (RASTATIME_WEBSTREAM_WATCHDOG=
scheduler).  Both sides must agree, so the renderer and the scheduler
are tested against the same switch.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
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
    assert '"watchdog", fun (_) ->' in liq                 # telnet webstream.watchdog
    assert '"ready", fun (_) -> string(source.is_ready(webstream))' in liq   # probe kept
    # the block must come after the final bus definition (bus.on_frame needs it)
    assert liq.index('bus = amplify(override="replaygain_track_gain", 1., bus)') < liq.index("bus.on_frame(")
    # ... and before the outputs that consume the bus (line start: the
    # template's header comment also mentions output.icecast)
    assert liq.index("bus.on_frame(") < liq.index("\noutput.icecast(")


def test_scheduler_mode_renders_a_reaper_only_frame_hook():
    liq = render_rastatime_liq(STREAMS, harbor_main_password="x", harbor_show_password="y",
                               webstream_watchdog_in_liquidsoap=False)
    assert "in-process webstream watchdog: disabled" in liq
    assert "RASTATIME_WEBSTREAM_WATCHDOG=scheduler" in liq
    # no stall detection ...
    assert "def webstream_wd_check()" not in liq and "webstream_wd_reconnect" not in liq
    # ... but the zombie reaper still runs on the frame counter (2026-09-08)
    assert "bus.on_frame(" in liq and "then webstream_reap() end" in liq
    assert '"ready", fun (_) -> string(source.is_ready(webstream))' in liq   # the poll still has its probe


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
    block = _render_webstream_watchdog_block(enabled=True, webstream_enabled=True,
                                             check_frames=0, starve_checks=-3)
    assert "mod 1 == 0" in block
    assert "webstream_wd_starved() >= 1" in block


# ---------------------------------------------------------------------------
# scheduler switch
# ---------------------------------------------------------------------------

def _sched(**kw):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.webstream_is_ready.return_value = True
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), streaming_handled_externally=True, **kw)
    s._arm_webstream_watchdog = MagicMock()
    return s


def test_default_mode_does_not_start_the_telnet_poll():
    s = _sched()
    assert s._webstream_watchdog_mode == ps.WEBSTREAM_WATCHDOG_LIQUIDSOAP
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_not_called()


def test_scheduler_mode_starts_the_telnet_poll():
    s = _sched(webstream_watchdog=ps.WEBSTREAM_WATCHDOG_SCHEDULER)
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_called_once()


def test_unknown_mode_falls_back_to_liquidsoap(caplog):
    s = _sched(webstream_watchdog="telepathy")
    assert s._webstream_watchdog_mode == ps.WEBSTREAM_WATCHDOG_LIQUIDSOAP
    assert any("Unknown webstream watchdog mode" in r.message for r in caplog.records)


@pytest.mark.parametrize("raw,expected", [
    ("liquidsoap", "liquidsoap"), ("scheduler", "scheduler"), (" Scheduler ", "scheduler"),
    ("", "liquidsoap"), ("nonsense", "liquidsoap"),
])
def test_main_env_switch(monkeypatch, raw, expected):
    from libretime_playout import __main__ as main
    monkeypatch.setenv(main.WEBSTREAM_WATCHDOG_ENV, raw)
    assert main._webstream_watchdog_mode() == expected


# ---------------------------------------------------------------------------
# stop-gap: the running Liquidsoap still has an older render
# ---------------------------------------------------------------------------

def test_liquidsoap_mode_falls_back_to_the_poll_when_the_render_lacks_the_watchdog(caplog):
    s = _sched()
    s._engine.webstream_watchdog_present.return_value = False
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_called_once()
    assert any("no in-process webstream watchdog" in r.message for r in caplog.records)
    # cached: the probe is not repeated for the same instance
    s._start_webstream_watchdog()
    assert s._engine.webstream_watchdog_present.call_count == 1


def test_liquidsoap_mode_stays_quiet_when_the_render_has_the_watchdog():
    s = _sched()
    s._engine.webstream_watchdog_present.return_value = True
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_not_called()
    assert s._liquidsoap_watchdog_present is True


def test_unreachable_probe_is_not_cached_and_does_not_poll():
    s = _sched()
    s._engine.webstream_watchdog_present.return_value = None
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_not_called()
    assert s._liquidsoap_watchdog_present is None          # probed again next time


def test_fresh_instance_resets_the_probe_cache():
    s = _sched()
    s._liquidsoap_watchdog_present = False
    s._engine.recording_stop.return_value = None
    s._engine.liquidsoap_uptime_seconds.return_value = 3.0
    s.reset_gates = MagicMock()
    ok, _ = s._apply_initial_liquidsoap_state()
    assert ok
    assert s._liquidsoap_watchdog_present is None


def test_engine_probe_parses_the_three_answers():
    from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine as E
    engine = MagicMock()
    telnet = MagicMock()
    engine._telnet = telnet
    telnet.webstream_watchdog.return_value = "checks=12 reconnects=0 started=true ready=true seen_ready=true starved=0"
    assert E.webstream_watchdog_present(engine) is True
    telnet.webstream_watchdog.return_value = 'ERROR: unknown command, type "help" to get a list of commands.'
    assert E.webstream_watchdog_present(engine) is False
    telnet.webstream_watchdog.side_effect = ConnectionError("down")
    assert E.webstream_watchdog_present(engine) is None
