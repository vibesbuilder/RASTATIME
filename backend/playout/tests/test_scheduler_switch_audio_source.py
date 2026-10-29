"""
RASTATIME 2026-05-27 — Unit tests for PlayoutScheduler.switch_audio_source
(Phase-C4 Teil 2b), trimmed on 2026-09-10 when the legacy mpv relay path
was deleted.

Liquidsoap handles DJ-source switching internally via
``switch(track_sensitive=true, [(source.is_ready(master_dj),
master_dj), …])``, so Pypo must NOT push HTTP-stream relays into the
queue for MASTER / SHOW; only SCHEDULED resumes the in-progress item.

We build a minimal PlayoutScheduler with mocked dependencies and call
``switch_audio_source`` for each SourceState.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rastatime_playout.engine.interface import PlayoutEngine
from rastatime_playout.source_switcher import SourceState


@pytest.fixture
def minimal_scheduler():
    """
    PlayoutScheduler with a mocked PlayoutEngine.  Side-effects on the
    schedule loop are stubbed out so we can call switch_audio_source in
    isolation.
    """
    from rastatime_playout.playout_scheduler import PlayoutScheduler
    engine = MagicMock(spec=PlayoutEngine)
    api_client = MagicMock()
    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
    )
    # Patch _resume_scheduled_locked to a recordable stub so we can
    # assert it's called for SCHEDULED but NOT for MASTER/SHOW.
    sched._resume_scheduled_locked = MagicMock()
    return sched, engine


def test_master_does_not_call_engine_play(minimal_scheduler):
    """MASTER state must not trigger engine.play()."""
    sched, engine = minimal_scheduler
    sched.switch_audio_source(SourceState.MASTER)
    engine.play.assert_not_called()
    engine.stop.assert_not_called()  # also no spurious stop


def test_show_does_not_call_engine_play(minimal_scheduler):
    """SHOW state must not trigger engine.play()."""
    sched, engine = minimal_scheduler
    sched.switch_audio_source(SourceState.SHOW)
    engine.play.assert_not_called()
    engine.stop.assert_not_called()


def test_scheduled_calls_resume(minimal_scheduler):
    """
    SCHEDULED STILL calls _resume_scheduled_locked — after a DJ-off,
    Pypo pushes / re-arms the in-progress item so the Liquidsoap
    fallback finds something when it switches back from blank() to
    scheduled.
    """
    sched, engine = minimal_scheduler
    sched.switch_audio_source(SourceState.SCHEDULED)
    sched._resume_scheduled_locked.assert_called_once_with()


def test_state_transitions_dont_leak(minimal_scheduler):
    """
    Cycle through SHOW → MASTER → SCHEDULED — only SCHEDULED triggers
    a resume call; the DJ-source transitions stay silent on the engine.
    """
    sched, engine = minimal_scheduler
    sched.switch_audio_source(SourceState.SHOW)
    sched.switch_audio_source(SourceState.MASTER)
    sched.switch_audio_source(SourceState.SCHEDULED)
    # Only one resume — only for SCHEDULED.
    assert sched._resume_scheduled_locked.call_count == 1
    # Engine never touched in MASTER/SHOW.
    engine.play.assert_not_called()
    engine.stop.assert_not_called()


def test_legacy_streaming_flag_is_gone():
    """The mpv-era ``streaming_handled_externally`` kwarg no longer exists."""
    from rastatime_playout.playout_scheduler import PlayoutScheduler
    with pytest.raises(TypeError):
        PlayoutScheduler(
            engine=MagicMock(spec=PlayoutEngine), api_client=MagicMock(),
            streaming_handled_externally=False,
        )
