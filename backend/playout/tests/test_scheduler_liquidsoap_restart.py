"""
RASTATIME 2026-09-07 - detect a LIQUIDSOAP restart under a running
PLAYOUT (uptime drop) and re-apply the initial state so the fresh
instance does not keep recording the _uninitialized.mp3 sentinel.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine


@pytest.fixture
def sched():
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), streaming_handled_externally=True)
    s.reset_gates = MagicMock()
    # constructor already ran one _apply_initial_liquidsoap_state (uptime 1000)
    engine.recording_stop.reset_mock()
    return s, engine


def test_uptime_drop_triggers_reinit(sched):
    s, engine = sched
    assert s._last_liquidsoap_uptime == 1000.0        # seeded by the constructor
    engine.liquidsoap_uptime_seconds.return_value = 12.0   # fresh instance
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_called_once()
    assert s.reset_gates.call_count == 1
    assert s._last_liquidsoap_uptime == 12.0          # re-seeded to the new instance


def test_monotonic_uptime_is_a_noop(sched):
    s, engine = sched
    engine.liquidsoap_uptime_seconds.return_value = 1120.0   # 120 s later, same instance
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()
    assert s._last_liquidsoap_uptime == 1120.0


def test_small_jitter_within_margin_is_not_a_restart(sched):
    s, engine = sched
    engine.liquidsoap_uptime_seconds.return_value = 997.0    # 3 s < 5 s margin
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()


def test_unreachable_uptime_is_a_noop(sched):
    s, engine = sched
    engine.liquidsoap_uptime_seconds.return_value = None
    s._maybe_reinit_after_liquidsoap_restart()
    engine.recording_stop.assert_not_called()
    assert s._last_liquidsoap_uptime == 1000.0        # baseline unchanged


def test_failed_reinit_keeps_old_baseline_for_retry(sched):
    s, engine = sched
    engine.liquidsoap_uptime_seconds.return_value = 12.0
    engine.recording_stop.side_effect = ConnectionError("telnet not up yet")
    s._maybe_reinit_after_liquidsoap_restart()
    # baseline NOT advanced -> next poll retries
    assert s._last_liquidsoap_uptime == 1000.0


def test_uptime_parsing():
    engine = MagicMock()
    real = LiquidsoapPlayoutEngine.liquidsoap_uptime_seconds
    telnet = MagicMock()
    engine._telnet = telnet
    telnet.uptime.return_value = "0d 00h 03m 25s"
    assert real(engine) == pytest.approx(205.0)
    telnet.uptime.return_value = "1d 02h 00m 00s"
    assert real(engine) == pytest.approx(93600.0)
    telnet.uptime.return_value = "garbage"
    assert real(engine) is None
    telnet.uptime.side_effect = RuntimeError("down")
    assert real(engine) is None
