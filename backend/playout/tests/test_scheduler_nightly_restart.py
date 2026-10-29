"""
RASTATIME 2026-09-05 — PlayoutScheduler nightly quiet-window restart.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from unittest.mock import MagicMock

import pytest

from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.liquidsoap_service import NightlyRestartPolicy
from rastatime_playout.player.events import EventKind, WebStreamEvent


def _webstream_event(start_in_seconds: float) -> WebStreamEvent:
    start = datetime.utcnow() + timedelta(seconds=start_in_seconds)
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START, start=start,
        end=start + timedelta(minutes=5), row_id=1, id=1,
        uri="http://example/stream", show_name="x", input_gain_db=None,
    )


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    render = MagicMock(return_value=True)
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    # 2026-09-09: the planned-restart probe would run PowerShell against
    # the real process - no process here keeps the daily-window semantics
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
        render_liquidsoap=render,
        nightly_restart=NightlyRestartPolicy(start=dtime(4, 0), quiet_margin_seconds=300),
    )
    s.reset_gates = MagicMock()
    s._test = {"render": render, "restart": restart, "engine": engine}
    return s


IN_WINDOW = datetime(2026, 9, 6, 4, 10)


def test_restarts_once_inside_window_when_quiet(sched):
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    assert sched._test["render"].call_count == 1
    sched._test["restart"].assert_called_once()
    assert sched.reset_gates.call_count == 1
    assert sched._nightly_restart_done == IN_WINDOW.date()
    # same day again -> nothing
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW + timedelta(minutes=20))
    sched._test["restart"].assert_called_once()


def test_outside_window_nothing_happens(sched):
    assert not sched._maybe_nightly_restart(now_local=datetime(2026, 9, 6, 12, 0))
    sched._test["restart"].assert_not_called()
    assert sched._nightly_restart_done is None


def test_postponed_while_something_is_on_air(sched):
    sched._playing_key = "2026-09-06-04-00-00_0"
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_not_called()
    assert sched._nightly_restart_done is None      # still due later in the window


def test_postponed_while_pre_warmed(sched):
    sched._prepared = ("k", object())
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_not_called()


def test_postponed_when_next_item_is_close(sched):
    sched._armed_events["soon"] = _webstream_event(120)
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_not_called()


def test_restarts_when_next_item_is_far_enough(sched):
    sched._armed_events["later"] = _webstream_event(900)
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_called_once()


def test_render_failure_does_not_block_restart(sched):
    sched._test["render"].side_effect = RuntimeError("no orm")
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched._test["restart"].assert_called_once()


def test_failed_restart_is_not_retried_today(sched):
    sched._test["restart"].return_value = False
    assert sched._maybe_nightly_restart(now_local=IN_WINDOW)
    sched.reset_gates.assert_not_called()
    assert sched._nightly_restart_done == IN_WINDOW.date()
    assert not sched._maybe_nightly_restart(now_local=IN_WINDOW + timedelta(minutes=5))


def test_after_restart_retries_until_telnet_is_back(sched):
    """recording.stop is the readiness probe (it raises while telnet is
    down); gates are reset once it succeeded."""
    engine = sched._test["engine"]
    engine.recording_stop.reset_mock()
    engine.recording_stop.side_effect = [ConnectionError("down"), ConnectionError("down"), None]
    sched.reset_gates.reset_mock()
    sched._after_liquidsoap_restart(attempts=5, delay=0.0)
    assert engine.recording_stop.call_count == 3
    assert sched.reset_gates.call_count == 1


def test_after_restart_gives_up_after_attempts(sched):
    engine = sched._test["engine"]
    engine.recording_stop.reset_mock()
    engine.recording_stop.side_effect = ConnectionError("down")
    sched.reset_gates.reset_mock()
    sched._after_liquidsoap_restart(attempts=3, delay=0.0)
    assert engine.recording_stop.call_count == 3
    sched.reset_gates.assert_not_called()


# RASTATIME 2026-09-06 - initial state with retries (startup race)

def test_constructor_success_makes_ensure_a_noop(sched):
    engine = sched._test["engine"]
    assert sched._initial_state_ok is True          # MagicMock recording_stop succeeded
    calls = engine.recording_stop.call_count
    assert sched.ensure_liquidsoap_initial_state(background=False) is True
    assert engine.recording_stop.call_count == calls


def test_ensure_retries_after_a_failed_constructor_attempt(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.side_effect = [ConnectionError("not up"), ConnectionError("not up"), None]
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock())
    assert s._initial_state_ok is False
    assert engine.recording_stop.call_count == 1
    s.reset_gates = MagicMock()
    assert s.ensure_liquidsoap_initial_state(background=False, attempts=5, delay=0.0) is True
    assert engine.recording_stop.call_count == 3
    sched_gates = s.reset_gates.call_count
    assert sched_gates == 1
    assert s._initial_state_ok is True


def test_ensure_gives_up_after_the_timeout(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.side_effect = ConnectionError("never")
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock())
    assert s.ensure_liquidsoap_initial_state(background=False, attempts=4, delay=0.0) is False
    assert engine.recording_stop.call_count == 1 + 4
    assert s._initial_state_ok is False


def test_ensure_is_none_when_the_engine_has_no_recording_stop():
    from rastatime_playout.engine.interface import PlayoutEngine
    engine = MagicMock(spec=PlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock())
    assert s.ensure_liquidsoap_initial_state(background=False) is None


def test_disabled_policy_is_a_noop(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
        nightly_restart=NightlyRestartPolicy(start=None),
    )
    assert not s._maybe_nightly_restart(now_local=IN_WINDOW)
    restart.assert_not_called()
