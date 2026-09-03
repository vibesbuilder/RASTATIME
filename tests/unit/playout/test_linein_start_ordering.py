"""
Lever 2 of the line-in start-gap fix (RASTATIME 2026-09-03):
``_on_linein_start`` must arm the ``input.http`` companion BEFORE the
blocking feeder start, so its connect + buffer-fill overlaps the
feeder's ~1.5 s health-check window instead of running strictly after
it.  And if the feeder never comes up, it must stop that source again
so it does not poll a dead mount for the rest of the slot (the b4cd37b
guard).

These are ordering/lifecycle contracts that would regress silently, so
they get a focused test even though the scheduler has few unit tests.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from libretime_playout.player.events import EventKind, LineinEvent
from libretime_playout.playout_scheduler import PlayoutScheduler


def _make_scheduler():
    engine = MagicMock(name="engine")
    scheduler = PlayoutScheduler(
        engine, MagicMock(name="api"), streaming_handled_externally=True
    )
    # Replace the real capture with a controllable stand-in.
    capture = MagicMock(name="capture")
    capture.listen_url = "http://127.0.0.1:8000/linein-capture"
    scheduler._linein_capture = capture
    # No DJ source active -> SCHEDULED path.
    scheduler._switcher = None
    scheduler._current_event = None
    # Skip side-effectful bookkeeping unrelated to the ordering contract.
    scheduler._resolve_linein_device = MagicMock(return_value="resolved-guid")
    scheduler._cue_item_start = MagicMock()
    scheduler._notify_media_started = MagicMock()
    return scheduler, engine, capture


def _linein_event():
    now = datetime.utcnow()
    return LineinEvent(
        type=EventKind.LINEIN_START,
        start=now,
        end=now + timedelta(minutes=6),
        row_id=1,
        id=1,
        show_name="Gap Test",
        device_id="dev-guid",
        name="Tascam 3-4",
        device_name="Mikrofon",       # non-empty -> feeder path allowed
        channel_mapping=[2, 3],        # != [0,1] -> feeder path
    )


def test_http_source_is_armed_before_the_blocking_feeder_start():
    scheduler, engine, capture = _make_scheduler()
    capture.is_running = True

    order = []
    engine.linein_start_http.side_effect = lambda: order.append("http_start")
    capture.start.side_effect = lambda *a, **k: order.append("feeder_start")

    scheduler._on_linein_start("k", _linein_event())

    assert order == ["http_start", "feeder_start"], (
        "input.http must be armed BEFORE the blocking feeder start so the "
        "buffer-fill overlaps the feeder health-check window"
    )
    capture.start.assert_called_once()
    engine.linein_stop.assert_not_called()  # happy path never tears down


def test_http_source_is_stopped_when_the_feeder_never_comes_up():
    scheduler, engine, capture = _make_scheduler()
    capture.is_running = False  # feeder gave up quietly

    scheduler._on_linein_start("k", _linein_event())

    engine.linein_start_http.assert_called_once()
    # The pre-armed source must be torn down so it can't 404-poll a dead
    # mount for the rest of the slot.
    engine.linein_stop.assert_called_once()


def test_http_source_is_stopped_when_the_feeder_start_raises():
    scheduler, engine, capture = _make_scheduler()
    capture.start.side_effect = RuntimeError("boom")

    scheduler._on_linein_start("k", _linein_event())

    engine.linein_start_http.assert_called_once()
    engine.linein_stop.assert_called_once()
