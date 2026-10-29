"""
RASTATIME 2026-09-10 — ``PlayoutScheduler.kick_dj_source`` goes to the
Liquidsoap harbor (``engine.dj_kick``) instead of the Icecast admin
``killsource`` of the deleted mpv path, which could not reach a DJ at
all (since Phase C4 the DJs connect to the harbor on port 8001).
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from rastatime_playout.engine.interface import PlayoutEngine, PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
import rastatime_playout.playout_scheduler as ps


def _scheduler(engine):
    engine.get_state.return_value = PlayoutState.STOPPED
    with patch("rastatime_playout.playout_scheduler.FfmpegLineinCapture"):
        return ps.PlayoutScheduler(engine=engine, api_client=MagicMock())


@pytest.mark.parametrize("kind,source", [
    ("master", "master"), ("master_dj", "master"), ("MASTER", "master"),
    ("show", "show"), ("live_dj", "show"), ("dj", "show"),
])
def test_kick_maps_the_kind_to_the_harbor(kind, source):
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    s = _scheduler(engine)

    s.kick_dj_source(kind)

    engine.dj_kick.assert_called_once_with(source)


def test_unknown_kind_is_ignored():
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    s = _scheduler(engine)

    s.kick_dj_source("bogus")

    engine.dj_kick.assert_not_called()


def test_engine_without_dj_kick_is_tolerated(caplog):
    engine = MagicMock(spec=PlayoutEngine)     # the ABC has no dj_kick
    s = _scheduler(engine)

    with caplog.at_level(logging.WARNING):
        s.kick_dj_source("show")               # must not raise

    assert "cannot kick" in caplog.text


def test_no_icecast_helpers_left():
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    s = _scheduler(engine)
    for name in ("_kick_icecast_source", "_build_icecast_input_url",
                 "set_listener_credentials", "_start_streamers", "_stop_streamers",
                 "_reload_stream_outputs_if_changed"):
        assert not hasattr(s, name), name
