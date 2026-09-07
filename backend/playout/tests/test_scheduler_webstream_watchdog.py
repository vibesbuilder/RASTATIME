"""
RASTATIME 2026-09-06 - webstream watchdog: detect a silent upstream
stall (source not ready after having been ready) and force a clean
stop+start.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import EventKind, WebStreamEvent
from libretime_playout.source_switcher import SourceState


def _webstream_event(uri="http://cloud.example/", gain=None):
    start = datetime(2026, 9, 6, 19, 0)
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START, start=start,
        end=start + timedelta(minutes=4), row_id=7, id=7,
        uri=uri, show_name="cloud", input_gain_db=gain,
    )


@pytest.fixture
def wd():
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.webstream_is_ready.return_value = True
    # the scheduler-side poll is now the opt-in fallback (2026-09-07);
    # these tests cover exactly that path
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), streaming_handled_externally=True,
                            webstream_watchdog=ps.WEBSTREAM_WATCHDOG_SCHEDULER)
    # no real timers - record re-arms instead of scheduling them
    s._arm_webstream_watchdog = MagicMock()
    s._current_event = _webstream_event()
    s._switcher = None                      # SCHEDULED (webstream audible)
    s._webstream_watchdog_id = 1
    s._webstream_watchdog_seen_ready = False
    s._webstream_watchdog_starved_ticks = 0
    return s, engine


def tick(s, n=1):
    for _ in range(n):
        s._webstream_watchdog_tick(s._webstream_watchdog_id)


def test_reconnects_after_sustained_starvation(wd):
    s, engine = wd
    engine.webstream_is_ready.side_effect = [True, False, False]
    tick(s)                                 # ready -> seen
    assert s._webstream_watchdog_seen_ready
    tick(s)                                 # starved 1
    engine.webstream_stop.assert_not_called()
    tick(s)                                 # starved 2 -> reconnect
    engine.webstream_stop.assert_called_once()
    engine.webstream_start.assert_called_once_with("http://cloud.example/", gain_db=None)
    engine.webstream_gate.assert_called_with(True)


def test_initial_bufferup_never_ready_does_not_reconnect(wd):
    s, engine = wd
    engine.webstream_is_ready.return_value = False   # never became ready
    tick(s, 5)
    engine.webstream_stop.assert_not_called()
    engine.webstream_start.assert_not_called()


def test_ready_again_resets_the_starvation_counter(wd):
    s, engine = wd
    engine.webstream_is_ready.side_effect = [True, False, True, False, True]
    tick(s, 5)
    engine.webstream_stop.assert_not_called()
    assert s._webstream_watchdog_starved_ticks == 0


def test_one_starved_tick_then_ready_is_not_a_reconnect(wd):
    s, engine = wd
    engine.webstream_is_ready.side_effect = [True, False, True]
    tick(s, 3)
    engine.webstream_stop.assert_not_called()


def test_reconnect_bumps_generation_and_resets_seen_ready(wd):
    s, engine = wd
    gen0 = s._webstream_generation
    engine.webstream_is_ready.side_effect = [True, False, False]
    tick(s, 3)
    assert s._webstream_generation == gen0 + 1     # a pending drained stop won't fire
    assert s._webstream_watchdog_seen_ready is False
    assert s._webstream_watchdog_starved_ticks == 0


def test_stale_watchdog_id_stops_without_probing(wd):
    s, engine = wd
    s._webstream_watchdog_tick(999)                 # not the current id
    engine.webstream_is_ready.assert_not_called()
    s._arm_webstream_watchdog.assert_not_called()


def test_non_webstream_event_stops_the_watchdog(wd):
    s, engine = wd
    s._current_event = None
    tick(s)
    engine.webstream_is_ready.assert_not_called()
    s._arm_webstream_watchdog.assert_not_called()   # no re-arm -> self-cancels


def test_dj_on_air_skips_the_probe(wd):
    s, engine = wd
    s._switcher = MagicMock()
    s._switcher.current_state = SourceState.MASTER
    s._webstream_watchdog_seen_ready = True
    s._webstream_watchdog_starved_ticks = 5
    tick(s)
    engine.webstream_is_ready.assert_not_called()
    assert s._webstream_watchdog_starved_ticks == 0  # reset while hidden
    s._arm_webstream_watchdog.assert_called_once()   # keeps watching


def test_probe_exception_is_fail_safe(wd):
    s, engine = wd
    engine.webstream_is_ready.side_effect = RuntimeError("telnet down")
    s._webstream_watchdog_seen_ready = True
    tick(s)
    engine.webstream_stop.assert_not_called()        # do not reconnect on a probe error
    s._arm_webstream_watchdog.assert_called_once()   # but keep watching


def test_start_watchdog_bumps_id_and_resets(wd):
    s, engine = wd
    s._arm_webstream_watchdog = MagicMock()
    s._webstream_watchdog_seen_ready = True
    s._webstream_watchdog_starved_ticks = 3
    before = s._webstream_watchdog_id
    s._start_webstream_watchdog()
    assert s._webstream_watchdog_id == before + 1
    assert s._webstream_watchdog_seen_ready is False
    assert s._webstream_watchdog_starved_ticks == 0
    s._arm_webstream_watchdog.assert_called_once()


def test_legacy_engine_has_no_watchdog(monkeypatch):
    from libretime_playout.engine.interface import PlayoutEngine
    engine = MagicMock(spec=PlayoutEngine)      # no webstream_is_ready
    engine.get_state.return_value = PlayoutState.STOPPED
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), streaming_handled_externally=False)
    s._arm_webstream_watchdog = MagicMock()
    s._start_webstream_watchdog()
    s._arm_webstream_watchdog.assert_not_called()
