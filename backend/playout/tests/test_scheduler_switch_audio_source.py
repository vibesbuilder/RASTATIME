"""
RASTATIME 2026-05-27 — Unit tests for PlayoutScheduler.switch_audio_source
in the Liquidsoap-engine path (Phase-C4 Teil 2b).

The legacy mpv/VLC path is well-exercised in production for over a year;
this test file focuses on the new ``streaming_handled_externally=True``
branch where Pypo must NOT push HTTP-stream-relays into the queue
because Liquidsoap handles DJ-source switching internally via
``switch(track_sensitive=true, [(source.is_ready(master_dj),
master_dj), …])``.

We build a minimal PlayoutScheduler with mocked dependencies and call
``switch_audio_source`` for each SourceState — asserting no
``engine.play()`` happens for MASTER / SHOW in Liquidsoap mode.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.interface import PlayoutEngine, PlayoutState
from libretime_playout.source_switcher import SourceState


@pytest.fixture
def minimal_scheduler_liquidsoap():
    """
    PlayoutScheduler with streaming_handled_externally=True + a mocked
    PlayoutEngine.  Side-effects on the schedule loop are stubbed out
    so we can call switch_audio_source in isolation.
    """
    from libretime_playout.playout_scheduler import PlayoutScheduler
    engine = MagicMock(spec=PlayoutEngine)
    api_client = MagicMock()
    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
        streaming_handled_externally=True,
    )
    # Patch _resume_scheduled_locked to a recordable stub so we can
    # assert it's called for SCHEDULED but NOT for MASTER/SHOW.
    sched._resume_scheduled_locked = MagicMock()
    return sched, engine


@pytest.fixture
def minimal_scheduler_legacy():
    """PlayoutScheduler in legacy mpv-mode for comparison."""
    from libretime_playout.playout_scheduler import PlayoutScheduler
    engine = MagicMock(spec=PlayoutEngine)
    api_client = MagicMock()
    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
        streaming_handled_externally=False,
    )
    # Stub out the resume + DJ-relay helpers.
    sched._resume_scheduled_locked = MagicMock()
    sched._build_icecast_input_url = MagicMock(side_effect=lambda mount: f"http://x@127.0.0.1:8000/{mount}")
    sched._start_streamers = MagicMock()
    sched._stop_streamers = MagicMock()
    return sched, engine


# ---- Liquidsoap path: MASTER + SHOW skip engine.play() ------------------


def test_liquidsoap_master_does_not_call_engine_play(minimal_scheduler_liquidsoap):
    """In Liquidsoap mode, MASTER state must not trigger engine.play()."""
    sched, engine = minimal_scheduler_liquidsoap
    sched.switch_audio_source(SourceState.MASTER)
    engine.play.assert_not_called()
    engine.stop.assert_not_called()  # also no spurious stop


def test_liquidsoap_show_does_not_call_engine_play(minimal_scheduler_liquidsoap):
    """In Liquidsoap mode, SHOW state must not trigger engine.play()."""
    sched, engine = minimal_scheduler_liquidsoap
    sched.switch_audio_source(SourceState.SHOW)
    engine.play.assert_not_called()
    engine.stop.assert_not_called()


def test_liquidsoap_scheduled_calls_resume(minimal_scheduler_liquidsoap):
    """
    SCHEDULED state in Liquidsoap mode STILL calls _resume_scheduled_locked
    — after a DJ-off, Pypo pushes the in-progress track so the
    Liquidsoap fallback finds something in the queue when it switches
    back from blank() to scheduled.
    """
    sched, engine = minimal_scheduler_liquidsoap
    sched.switch_audio_source(SourceState.SCHEDULED)
    sched._resume_scheduled_locked.assert_called_once_with()


def test_liquidsoap_state_transitions_dont_leak(minimal_scheduler_liquidsoap):
    """
    Cycle through SHOW → MASTER → SCHEDULED — only SCHEDULED triggers
    a resume call; the DJ-source transitions stay silent on the engine.
    """
    sched, engine = minimal_scheduler_liquidsoap
    sched.switch_audio_source(SourceState.SHOW)
    sched.switch_audio_source(SourceState.MASTER)
    sched.switch_audio_source(SourceState.SCHEDULED)
    # Only one resume — only for SCHEDULED.
    assert sched._resume_scheduled_locked.call_count == 1
    # Engine never touched in MASTER/SHOW.
    engine.play.assert_not_called()
    engine.stop.assert_not_called()


# ---- Legacy mpv path: MASTER + SHOW still relay via engine.play() ------


def test_legacy_master_still_calls_engine_play(minimal_scheduler_legacy):
    """Sanity-check: mpv/VLC path's MASTER relay is unchanged."""
    sched, engine = minimal_scheduler_legacy
    sched.switch_audio_source(SourceState.MASTER)
    engine.play.assert_called_once()
    args, _ = engine.play.call_args
    assert args[0] == "http://x@127.0.0.1:8000/main"


def test_legacy_show_still_calls_engine_play(minimal_scheduler_legacy):
    """Sanity-check: mpv/VLC path's SHOW relay is unchanged."""
    sched, engine = minimal_scheduler_legacy
    sched.switch_audio_source(SourceState.SHOW)
    engine.play.assert_called_once()
    args, _ = engine.play.call_args
    assert args[0] == "http://x@127.0.0.1:8000/show"


def test_legacy_scheduled_calls_resume(minimal_scheduler_legacy):
    """Legacy path SCHEDULED still resumes."""
    sched, _ = minimal_scheduler_legacy
    sched.switch_audio_source(SourceState.SCHEDULED)
    sched._resume_scheduled_locked.assert_called_once_with()
