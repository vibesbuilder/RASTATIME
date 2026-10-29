"""
RASTATIME 2026-09-09 - option d: after a Liquidsoap restart the scheduler
asks the SourceSwitcher's reconciler to verify the DJ state over telnet.
The harbor callbacks of the old process cannot report the connections
that died with it, and the fresh process only reports new ones.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rastatime_playout import playout_scheduler as ps
from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.source_switcher import SourceSwitcher


@pytest.fixture
def sched(monkeypatch):
    # uptime-drop tests: the process-table detector (2026-09-09) is muted
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
    )
    s.reset_gates = MagicMock()
    switcher = SourceSwitcher(switch_callback=lambda _state: None)
    s.set_source_switcher(switcher)
    assert switcher.wait_reconcile(0) is False
    return s, engine, switcher


def test_uptime_drop_requests_a_reconcile(sched):
    s, engine, switcher = sched
    engine.liquidsoap_uptime_seconds.return_value = 3.0      # fresh instance
    s._maybe_reinit_after_liquidsoap_restart()
    assert switcher.wait_reconcile(0) is True


def test_no_restart_no_reconcile(sched):
    s, engine, switcher = sched
    engine.liquidsoap_uptime_seconds.return_value = 1500.0
    s._maybe_reinit_after_liquidsoap_restart()
    assert switcher.wait_reconcile(0) is False


def test_failed_reinit_does_not_request_yet(sched):
    s, engine, switcher = sched
    engine.liquidsoap_uptime_seconds.return_value = 3.0
    engine.recording_stop.side_effect = ConnectionError("telnet not ready")
    s._maybe_reinit_after_liquidsoap_restart()
    assert switcher.wait_reconcile(0) is False


def test_planned_restart_requests_a_reconcile_once_liquidsoap_is_back(sched, monkeypatch):
    s, engine, switcher = sched
    monkeypatch.setattr(s, "_retry_initial_liquidsoap_state", lambda *a, **k: True)
    s._after_liquidsoap_restart()
    assert switcher.wait_reconcile(0) is True


def test_planned_restart_without_telnet_does_not_request(sched, monkeypatch):
    s, engine, switcher = sched
    monkeypatch.setattr(s, "_retry_initial_liquidsoap_state", lambda *a, **k: False)
    s._after_liquidsoap_restart()
    assert switcher.wait_reconcile(0) is False


def test_switcher_without_request_reconcile_is_tolerated(sched):
    s, engine, _switcher = sched
    s.set_source_switcher(object())
    engine.liquidsoap_uptime_seconds.return_value = 3.0
    s._maybe_reinit_after_liquidsoap_restart()             # must not raise


def test_no_switcher_is_tolerated(sched):
    s, engine, _switcher = sched
    s.set_source_switcher(None)
    engine.liquidsoap_uptime_seconds.return_value = 3.0
    s._maybe_reinit_after_liquidsoap_restart()             # must not raise
