"""
Lever 2 of the line-in start-gap fix (RASTATIME 2026-09-03):
``_on_linein_start`` must arm the ``input.http`` companion BEFORE the
blocking feeder start, so its connect + buffer-fill overlaps the
feeder's startup health-check window instead of running strictly after
it.  And if the feeder never comes up, it must stop that source again
so it does not poll a dead mount for the rest of the slot (the b4cd37b
guard).

These are ordering/lifecycle contracts that would regress silently, so
they get a focused test even though the scheduler has few unit tests.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.player.events import EventKind, LineinEvent
from libretime_playout.playout_scheduler import PlayoutScheduler


def _make_scheduler():
    engine = MagicMock(name="engine")
    scheduler = PlayoutScheduler(
        engine, MagicMock(name="api")
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
        channel_mapping=[2, 3],
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


# ---------------------------------------------------------------------
# Option B (RASTATIME 2026-09-03): plain stereo goes through the feeder
# too.  The direct-dshow source addresses the device by WASAPI endpoint
# GUID, which DirectShow does not know -- live proof was a silent 15:20
# "Tascam 1-2" show.  The feeder resolves by friendly name and works on
# every channel pair, so it is now the only path for rows that stored a
# device name.
# ---------------------------------------------------------------------


def _plain_stereo_event(device_name="Mikrofon"):
    now = datetime.utcnow()
    return LineinEvent(
        type=EventKind.LINEIN_START,
        start=now,
        end=now + timedelta(minutes=6),
        row_id=2,
        id=2,
        show_name="Studio",
        device_id="dev-guid",
        name="Tascam 1-2",
        device_name=device_name,
        channel_mapping=[0, 1],
    )


def test_plain_stereo_also_uses_the_feeder():
    scheduler, engine, capture = _make_scheduler()
    capture.is_running = True

    scheduler._on_linein_start("k", _plain_stereo_event())

    capture.start.assert_called_once()
    assert capture.start.call_args.kwargs["channel_mapping"] == (0, 1)
    engine.linein_start_http.assert_called_once()
    # The direct dshow source must NOT be used for a row that has a
    # device name -- that is the path that produced silence live.
    engine.linein_start.assert_not_called()


def test_legacy_row_without_device_name_still_falls_back_to_dshow():
    """The feeder cannot resolve a PortAudio device from a GUID alone,
    so rows saved before device_name existed keep the dshow source."""
    scheduler, engine, capture = _make_scheduler()
    capture.is_running = True

    scheduler._on_linein_start("k", _plain_stereo_event(device_name=""))

    capture.start.assert_not_called()
    engine.linein_start.assert_called_once()


# ---------------------------------------------------------------------
# Catch-up must not bounce a line-in that is already on air.  A schedule
# refresh handed the same in-progress slot back under a different key
# ("<ts>_2" -> "<ts>"), catch-up re-played it, and the http source was
# torn down and rebuilt mid-show = an audible ~1 s dropout at 15:16.
# ---------------------------------------------------------------------


def _arm(scheduler, key, event, started_ago_s):
    """Arm an already-running slot and settle its timers.

    Catch-up fires through ``threading.Timer(0, ...)``, so the callback
    runs on another thread -- join it (rather than sleeping) to keep the
    assertions deterministic, and cancel the stop timer so the test does
    not leave a ~5 min timer behind.
    """
    now = event.start + timedelta(seconds=started_ago_s)
    with patch.object(scheduler, "_on_linein_start") as on_start:
        scheduler._arm_linein_event(key, event, now)
        start_t, stop_t = scheduler._timers[key]
        if start_t is not None:
            start_t.join(5)
        if stop_t is not None:
            stop_t.cancel()
    return on_start


def test_catch_up_skips_a_line_in_already_on_air_with_the_same_device():
    scheduler, _engine, capture = _make_scheduler()
    capture.is_running = True
    event = _linein_event()
    scheduler._current_event = event
    scheduler._playing_key = "2026-09-03-13-15-00_2"

    on_start = _arm(scheduler, "2026-09-03-13-15-00", event, 71)

    on_start.assert_not_called()
    # The new key must be adopted, or the stop timer armed under it would
    # hit _on_stop's stale-key guard and the show would never end.
    assert scheduler._playing_key == "2026-09-03-13-15-00"
    assert scheduler._timers["2026-09-03-13-15-00"][0] is None


def test_catch_up_still_fires_for_a_different_device():
    scheduler, _engine, capture = _make_scheduler()
    capture.is_running = True
    scheduler._current_event = _linein_event()
    scheduler._playing_key = "other-key"

    event = _linein_event()
    event.device_id = "a-different-device"
    on_start = _arm(scheduler, "new-key", event, 71)

    on_start.assert_called_once()


def test_catch_up_still_fires_when_the_capture_died():
    """Same device, but nothing is actually streaming -- catch-up is
    exactly what should rescue the remaining minutes of the slot."""
    scheduler, _engine, capture = _make_scheduler()
    capture.is_running = False
    scheduler._current_event = _linein_event()
    scheduler._playing_key = "old-key"

    on_start = _arm(scheduler, "new-key", _linein_event(), 71)

    on_start.assert_called_once()


def test_resume_after_liquidsoap_restart_also_uses_the_feeder():
    """The resume path makes the same feeder-vs-dshow decision as
    ``_on_linein_start`` and must stay in lockstep with it: if it still
    sent plain stereo to dshow, a Liquidsoap restart mid-show would drop
    a studio slot back onto the by-GUID path that plays silence."""
    scheduler, engine, capture = _make_scheduler()
    capture.is_running = True
    scheduler._current_event = _plain_stereo_event()
    scheduler._current_audio_path = "http://127.0.0.1:8000/linein-capture"

    scheduler._resume_scheduled_locked()

    engine.linein_start_http.assert_called_once()
    engine.linein_start.assert_not_called()
    capture.start.assert_called_once()
