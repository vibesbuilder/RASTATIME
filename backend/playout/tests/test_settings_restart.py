"""
RASTATIME 2026-09-16 - settings baked into rastatime.liq (24/7 recording,
Main Output, crossfade, stream outputs) are applied by the playout: a
fingerprint change at refresh arms the planned-restart path (quiet moment
at once, otherwise the next file-to-file boundary); a successful restart
records the new baseline.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.liquidsoap_service import NightlyRestartPolicy

NOW = datetime(2026, 9, 16, 12, 0, 0)


@pytest.fixture
def sched(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.liquidsoap_uptime_seconds.return_value = 5.0
    restart = MagicMock(return_value=True)
    monkeypatch.setattr(ps, "restart_liquidsoap_service", restart)
    monkeypatch.setattr(ps.time, "sleep", lambda _s: None)
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info",
                        MagicMock(return_value=[SimpleNamespace(pid=1, private_mb=300.0, age_seconds=3600.0)]))
    fingerprint = MagicMock(return_value="a")
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(),
        render_liquidsoap=MagicMock(return_value=True),
        render_settings_fingerprint=fingerprint,
        nightly_restart=NightlyRestartPolicy(start=dtime(4, 0), quiet_margin_seconds=300),
    )
    s.reset_gates = MagicMock()
    s._confirm_liquidsoap_stays_up = MagicMock(return_value=True)
    s._after_liquidsoap_restart = MagicMock()
    s._test = {"restart": restart, "fingerprint": fingerprint}
    return s


def test_first_refresh_only_records_the_baseline(sched):
    assert sched._maybe_settings_restart(NOW) is False
    assert sched._rendered_fingerprint == "a"
    sched._test["restart"].assert_not_called()


def test_unchanged_settings_do_nothing(sched):
    sched._maybe_settings_restart(NOW)
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=2)) is False
    sched._test["restart"].assert_not_called()


def test_changed_settings_restart_at_once_when_quiet(sched):
    sched._maybe_settings_restart(NOW)
    sched._test["fingerprint"].return_value = "b"
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=2)) is True
    sched._test["restart"].assert_called_once()
    reason = sched._test["restart"].call_args[0][0]
    assert "settings changed" in reason and "quiet moment" in reason
    assert sched._rendered_fingerprint == "b"          # new baseline after the restart
    # no second restart for the same change
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=4)) is False
    assert sched._test["restart"].call_count == 1


def test_changed_settings_wait_for_the_track_boundary_when_on_air(sched):
    sched._maybe_settings_restart(NOW)
    sched._test["fingerprint"].return_value = "b"
    sched._current_event = SimpleNamespace(start=NOW)   # anything on air
    sched._playing_key = "k"
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=2)) is False
    sched._test["restart"].assert_not_called()
    assert sched._boundary_restart_pending == ps.PlayoutScheduler.SETTINGS_RESTART_REASON
    # a second refresh does not re-arm or restart
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=4)) is False


def test_failed_attempt_is_retried_after_thirty_minutes(sched):
    sched._maybe_settings_restart(NOW)
    sched._test["fingerprint"].return_value = "b"
    sched._test["restart"].return_value = False        # nssm failed
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=2)) is True
    assert sched._rendered_fingerprint == "a"          # not applied
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=10)) is False
    assert sched._test["restart"].call_count == 1
    sched._test["restart"].return_value = True
    assert sched._maybe_settings_restart(NOW + timedelta(minutes=40)) is True
    assert sched._rendered_fingerprint == "b"


def test_no_fingerprint_function_means_no_detection(monkeypatch):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    s = ps.PlayoutScheduler(engine=engine, api_client=MagicMock(), render_liquidsoap=MagicMock())
    assert s._maybe_settings_restart(NOW) is False
    assert s._rendered_fingerprint is None


def test_fingerprint_errors_and_none_are_ignored(sched):
    sched._test["fingerprint"].side_effect = RuntimeError("db down")
    assert sched._maybe_settings_restart(NOW) is False
    sched._test["fingerprint"].side_effect = None
    sched._test["fingerprint"].return_value = None
    assert sched._maybe_settings_restart(NOW) is False
    assert sched._rendered_fingerprint is None


def test_main_fingerprint_hashes_the_rendered_settings(monkeypatch):
    from libretime_playout import __main__ as main

    monkeypatch.setattr(main, "_resolve_crossfade_seconds", lambda: 1.0)
    monkeypatch.setattr(main, "_read_stream_outputs", lambda: [{"mount": "a"}])
    import sys
    fake_models = SimpleNamespace(SoundcardSettings=SimpleNamespace(
        get_settings=lambda: SimpleNamespace(main_output_id="id1", main_output_name="Tascam")))
    monkeypatch.setitem(sys.modules, "libretime_api.soundcard.models", fake_models)
    from libretime_playout import liquidsoap_config as lc
    cfg = {"enabled": True, "folder": "X", "format": "mp3", "bitrate": 128}
    monkeypatch.setattr(lc, "read_hourly_recording_config_from_db", lambda: cfg)
    first = main._render_settings_fingerprint()
    assert isinstance(first, str) and len(first) == 40
    cfg["bitrate"] = 192
    assert main._render_settings_fingerprint() != first
    cfg["bitrate"] = 128
    assert main._render_settings_fingerprint() == first
    monkeypatch.setattr(lc, "read_hourly_recording_config_from_db", MagicMock(side_effect=RuntimeError("x")))
    assert main._render_settings_fingerprint() is None
