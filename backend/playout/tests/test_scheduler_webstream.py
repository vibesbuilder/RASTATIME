"""
RASTATIME 2026-05-29 — Unit tests for PlayoutScheduler's webstream
hooks in Liquidsoap-Mode (Phase E).

Scheduled webstream items use Liquidsoap's dedicated ``input.http``
source (``LiquidsoapPlayoutEngine.webstream_start`` / ``webstream_stop``);
the legacy ``engine.play(url)`` + FfmpegStreamer re-encoding path was
deleted on 2026-09-10.

These tests verify:
  * ``_on_webstream_start`` — source start, gates, same-stream hand-over
  * ``_on_stop`` — webstream-specific teardown via webstream_stop()
  * ``_resume_scheduled_locked`` — the DJ-off resume re-arms the source
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import EventKind, WebStreamEvent


# ---- Helpers -----------------------------------------------------------


def _make_webstream_event(
    *,
    uri: str = "http://stream.example.com/test.mp3",
    input_gain_db=None,
    show_name: str = "Test Webstream Show",
    duration_seconds: int = 600,
    type_: EventKind = EventKind.WEB_STREAM_OUTPUT_START,
    row_id: int = 12345,
    id_: int = 42,
) -> WebStreamEvent:
    """Build a WebStreamEvent without going through the API."""
    start = datetime(2026, 5, 29, 10, 0)
    end = start + timedelta(seconds=duration_seconds)
    return WebStreamEvent(
        type=type_,
        start=start,
        end=end,
        row_id=row_id,
        id=id_,
        uri=uri,
        show_name=show_name,
        input_gain_db=input_gain_db,
    )


# ---- Fixtures -----------------------------------------------------------


@pytest.fixture
def liquidsoap_scheduler():
    """
    PlayoutScheduler with a mocked
    LiquidsoapPlayoutEngine (so engine.webstream_start / _stop exist on
    the mock per spec=).
    """
    from libretime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    api_client = MagicMock()

    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
    )
    return sched, engine


# ---- _on_webstream_start: Liquidsoap path ------------------------------


def test_webstream_start_liquidsoap_path_calls_engine_webstream_start(
    liquidsoap_scheduler,
):
    """
    _on_webstream_start MUST call engine.webstream_start(uri, gain_db)
    — NOT engine.play() (the request queue).
    """
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event(
        uri="http://stream.example.com/test.mp3",
        input_gain_db=3.0,
    )

    sched._on_webstream_start("key1", event)

    # New Liquidsoap webstream_start was called with the URL + gain
    engine.webstream_start.assert_called_once_with(
        "http://stream.example.com/test.mp3", gain_db=3.0,
    )
    # Legacy engine.play MUST NOT be called in this path
    engine.play.assert_not_called()


def test_webstream_start_liquidsoap_path_clears_request_queue_first(
    liquidsoap_scheduler,
):
    """
    Before calling webstream_start, the Liquidsoap path issues
    engine.stop() (== request.queue.skip) so the previous scheduled
    track doesn't linger in the background while input.http buffers.
    """
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event()

    sched._on_webstream_start("key1", event)

    # engine.stop() must be called BEFORE webstream_start (Python
    # method-call ordering is captured in mock_calls)
    method_names = [c[0] for c in engine.mock_calls]
    assert "stop" in method_names
    assert "webstream_start" in method_names
    assert method_names.index("stop") < method_names.index("webstream_start")


def test_webstream_start_liquidsoap_path_with_none_gain(
    liquidsoap_scheduler,
):
    """gain_db=None is passed straight through (engine decides the default)."""
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event(input_gain_db=None)

    sched._on_webstream_start("key1", event)

    engine.webstream_start.assert_called_once_with(
        event.uri, gain_db=None,
    )


def test_webstream_start_liquidsoap_path_updates_playing_event(
    liquidsoap_scheduler,
):
    """The webstream event bookkeeping (playing_key, current_event) is updated."""
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event()

    sched._on_webstream_start("key1", event)

    assert sched._playing_key == "key1"
    assert sched._current_event is event
    assert sched._current_audio_path == event.uri


# ---- _on_stop: Liquidsoap webstream teardown ----------------------------


def test_on_stop_liquidsoap_webstream_calls_webstream_stop(
    liquidsoap_scheduler,
):
    """
    In Liquidsoap-Mode, when a WebStreamEvent is the current event,
    _on_stop must take it off air via the bus GATE (since 2026-09-04,
    Paket 2: the switch fades it out under the successor) and call
    engine.webstream_stop() only after the drain - NEVER engine.stop()
    (request.queue.skip would not close input.http).
    """
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event()
    sched._on_webstream_start("key1", event)

    # Reset mock so we only see what _on_stop does next
    engine.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    sched._on_stop("key1")

    engine.webstream_gate.assert_called_once_with(False)
    engine.webstream_stop.assert_not_called()   # draining
    engine.stop.assert_not_called()
    assert sched._playing_key is None
    assert sched._current_event is None

    sched._drained_webstream_stop(sched._webstream_generation)
    engine.webstream_stop.assert_called_once()


def test_on_stop_liquidsoap_file_event_unchanged(liquidsoap_scheduler):
    """
    File events still use the unchanged engine.stop() path in
    Liquidsoap-Mode — no regression to the webstream branch.
    """
    sched, engine = liquidsoap_scheduler
    # Manually set a non-webstream current event to simulate a file
    # currently playing.
    from libretime_playout.player.events import EventKind, FileEvent
    file_event = FileEvent(
        type=EventKind.FILE,
        start=datetime(2026, 5, 29, 10, 0),
        end=datetime(2026, 5, 29, 10, 3),
        row_id=99,
        id=99,
        uri="file:///C:/test.mp3",
        show_name="Test Show",
        fade_in=0.0,
        fade_out=0.0,
        cue_in=0.0,
        cue_out=180.0,
        mime="audio/mpeg",
        filesize=4_000_000,
    )
    sched._playing_key = "filekey"
    sched._current_event = file_event
    engine.get_state.return_value = PlayoutState.PLAYING

    sched._on_stop("filekey")

    # The generic engine.stop() must be called (request.queue.skip)
    engine.stop.assert_called_once()
    # webstream_stop must NOT be called for a file event
    engine.webstream_stop.assert_not_called()


# ---- Edge cases --------------------------------------------------------


def test_on_stop_already_handed_off_to_next_event(liquidsoap_scheduler):
    """
    Race fix: if _playing_key has already been swapped (next event
    already armed), _on_stop returns early without touching the engine.
    """
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event()
    sched._on_webstream_start("key1", event)

    # Simulate the next event having stolen the spotlight
    sched._playing_key = "key2"
    engine.reset_mock()

    sched._on_stop("key1")

    # Nothing should have been called on the engine
    engine.webstream_stop.assert_not_called()
    engine.stop.assert_not_called()


# ---- DJ-off resume (RASTATIME 2026-09-10) -------------------------------


def test_resume_webstream_rearms_the_source_instead_of_engine_play(
    liquidsoap_scheduler,
):
    """
    After a DJ hang-up the in-progress webstream is re-armed through
    webstream_start + gate + watchdog (webstream.start on the same URL
    answers "already started" in the .liq, so a still-running source is
    left alone).  The deleted mpv wiring pushed the URL into the request
    queue via engine.play.
    """
    sched, engine = liquidsoap_scheduler
    event = _make_webstream_event(input_gain_db=-2.0, duration_seconds=10 ** 8)
    sched._playing_key = "key1"
    sched._current_event = event
    sched._current_audio_path = event.uri
    sched._current_gain_db = event.input_gain_db

    sched._resume_scheduled_locked()

    engine.webstream_start.assert_called_once_with(event.uri, gain_db=-2.0)
    engine.webstream_gate.assert_called_once_with(True)
    engine.play.assert_not_called()
