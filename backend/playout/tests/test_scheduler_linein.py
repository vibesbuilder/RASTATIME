"""
RASTATIME 2026-05-29 — Unit tests for PlayoutScheduler's linein
hooks in Liquidsoap-Mode (Phase F).

In Liquidsoap-Mode (``streaming_handled_externally=True``) scheduled
line-input items use Liquidsoap's dedicated ``input.http`` source bound
to FfmpegLineinCapture's local Icecast mount.  FfmpegLineinCapture
itself (the Python subprocess that captures dshow audio) is unchanged
— only the downstream consumer side is migrated:

  Legacy:    FfmpegLineinCapture → /linein-capture → mpv + 3× FfmpegStreamer
  Phase F:   FfmpegLineinCapture → /linein-capture → Liquidsoap input.http
                                                     → bus → Icecast (×3)
                                                     → output.file (recording)

These tests verify the branch logic in:
  * ``_on_linein_start`` — branch on streaming_handled_externally
  * ``_on_stop`` — linein-specific teardown via linein_stop()
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.engine.interface import PlayoutEngine, PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import EventKind, LineinEvent


# ---- Helpers -----------------------------------------------------------


def _make_linein_event(
    *,
    device_id: str = "0fb30b0b-c875-432b-a48f-dbb5208995c9",
    device_name: str = "Mikrofon (Jabra USB)",
    name: str = "Studio Mic Left",
    show_name: str = "Test Linein Show",
    duration_seconds: int = 600,
    row_id: int = 12345,
    id_: int = 42,
) -> LineinEvent:
    """Build a LineinEvent without going through the API."""
    from datetime import timedelta
    start = datetime(2026, 5, 29, 10, 0)
    end = start + timedelta(seconds=duration_seconds)
    return LineinEvent(
        type=EventKind.LINEIN_START,
        start=start,
        end=end,
        row_id=row_id,
        id=id_,
        show_name=show_name,
        device_id=device_id,
        device_name=device_name,
        name=name,
    )


def _patched_scheduler(streaming_handled_externally: bool):
    """
    Build a PlayoutScheduler with a mocked FfmpegLineinCapture so the
    test doesn't try to spawn an actual ffmpeg subprocess.
    """
    from libretime_playout.playout_scheduler import PlayoutScheduler

    if streaming_handled_externally:
        engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    else:
        engine = MagicMock(spec=PlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    api_client = MagicMock()

    # Patch FfmpegLineinCapture constructor to return a mock that
    # behaves like a working capture (start/stop succeed, is_running
    # reports the spawning state).
    with patch(
        "libretime_playout.playout_scheduler.FfmpegLineinCapture"
    ) as mock_capture_cls:
        capture_instance = MagicMock()
        capture_instance.is_running = False
        capture_instance.listen_url = "http://localhost:8000/linein-capture"
        mock_capture_cls.return_value = capture_instance

        sched = PlayoutScheduler(
            engine=engine,
            api_client=api_client,
            streaming_handled_externally=streaming_handled_externally,
        )
        # Patch the device resolver so it doesn't try to use the
        # WindowsAudioDeviceManager.  Returns the input device_id
        # unchanged (no GUID-mismatch fallback test scenario).
        sched._resolve_linein_device = lambda evt: evt.device_id
        return sched, engine, capture_instance


@pytest.fixture
def liquidsoap_scheduler():
    return _patched_scheduler(streaming_handled_externally=True)


@pytest.fixture
def legacy_scheduler():
    return _patched_scheduler(streaming_handled_externally=False)


# ---- _on_linein_start: Liquidsoap path --------------------------------


def test_linein_start_liquidsoap_opens_dshow_via_engine(
    liquidsoap_scheduler,
):
    """
    Phase-F-2: In Liquidsoap-Mode, _on_linein_start opens the dshow
    device DIRECTLY via engine.linein_start(dshow_spec) — NO
    FfmpegLineinCapture subprocess.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    # Phase-F-2: FfmpegLineinCapture is NOT started in the Liquidsoap
    # path — input.ffmpeg opens the dshow device directly.
    capture.start.assert_not_called()
    # engine.linein_start was called with the dshow alternative-name
    # spec built from the device GUID.
    from libretime_playout.engine.ffmpeg_linein_capture import (
        _stable_id_to_dshow_audio,
    )
    expected_spec = _stable_id_to_dshow_audio(event.device_id)
    engine.linein_start.assert_called_once_with(expected_spec)
    # Legacy engine.play MUST NOT be called in this path
    engine.play.assert_not_called()


def test_linein_start_liquidsoap_clears_request_queue_first(
    liquidsoap_scheduler,
):
    """
    Before linein_start, the Liquidsoap path issues engine.stop()
    (= request.queue.skip) so the previous scheduled track doesn't
    linger in the background while input.http buffers.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    # engine.stop must be called BEFORE linein_start
    method_names = [c[0] for c in engine.mock_calls]
    assert "stop" in method_names
    assert "linein_start" in method_names
    assert method_names.index("stop") < method_names.index("linein_start")


def test_linein_start_liquidsoap_updates_playing_event(
    liquidsoap_scheduler,
):
    """Bookkeeping (playing_key, current_event) is updated."""
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    assert sched._playing_key == "key1"
    assert sched._current_event is event
    assert sched._current_audio_path == capture.listen_url


# ---- _on_linein_start: Legacy mpv/VLC path ----------------------------


def test_linein_start_legacy_uses_engine_play(legacy_scheduler):
    """
    Legacy mpv/VLC path: unchanged — capture.start + engine.play
    + start_streamers.  No engine.linein_start in this path.
    """
    sched, engine, capture = legacy_scheduler
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    capture.start.assert_called_once_with(event.device_id)
    engine.play.assert_called_once_with(capture.listen_url, cue_in=0.0)
    # Legacy engine does not have linein_start (it's on the Liquidsoap
    # spec only) — verifying via mock attribute presence is fragile
    # since MagicMock auto-generates attrs.  Instead: confirm the
    # PlayoutEngine-spec mock was used (no linein_start attribute when
    # spec is enforced).
    assert not hasattr(engine, "linein_start") or not engine.linein_start.called


# ---- _on_stop: Liquidsoap linein teardown -----------------------------


def test_on_stop_liquidsoap_linein_calls_linein_stop_and_capture_stop(
    liquidsoap_scheduler,
):
    """
    In Liquidsoap-Mode, when a LineinEvent is the current event,
    _on_stop must:
      1. Stop FfmpegLineinCapture (dshow subprocess shutdown).
      2. Call engine.linein_stop() to close the input.http source.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()
    sched._on_linein_start("key1", event)

    engine.reset_mock()
    capture.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    sched._on_stop("key1")

    # FfmpegLineinCapture stop was called (dshow subprocess shutdown)
    capture.stop.assert_called_once()
    # linein_stop was called (input.http source closed)
    engine.linein_stop.assert_called_once()
    # generic engine.stop must NOT be called for a linein
    engine.stop.assert_not_called()
    # Bookkeeping cleared
    assert sched._playing_key is None
    assert sched._current_event is None


def test_on_stop_legacy_linein_does_not_call_linein_stop(legacy_scheduler):
    """
    In legacy mode, _on_stop calls engine.stop() (the regular path)
    + capture.stop().  No engine.linein_stop call (that's Liquidsoap-only).
    """
    sched, engine, capture = legacy_scheduler
    event = _make_linein_event()
    sched._on_linein_start("key1", event)

    engine.reset_mock()
    capture.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    sched._on_stop("key1")

    capture.stop.assert_called_once()
    # Legacy path takes engine.stop, not linein_stop
    engine.stop.assert_called_once()
