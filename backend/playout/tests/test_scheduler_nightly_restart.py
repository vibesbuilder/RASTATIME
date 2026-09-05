"""
RASTATIME 2026-09-05 — PlayoutScheduler nightly quiet-window restart.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.liquidsoap_service import NightlyRestartPolicy
from libretime_playout.player.events import EventKind, WebStreamEvent


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
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(), streaming_handled_externally=True,
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


def test_after_restart_retries_reset_gates_until_telnet_is_back(sched):
    sched.reset_gates = MagicMock(side_effect=[ConnectionError("down"), ConnectionError("down"), None])
    sched._playing_key = None
    sched._after_liquidsoap_restart(attempts=5, delay=0.0)
    assert sched.reset_gates.call_count == 3


def test_disabled_policy_is_a_noop(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(), streaming_handled_externally=True,
        nightly_restart=NightlyRestartPolicy(start=None),
    )
    assert not s._maybe_nightly_restart(now_local=IN_WINDOW)
    restart.assert_not_called()
