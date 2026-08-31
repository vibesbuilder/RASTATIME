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
    channel_mapping=None,
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
        channel_mapping=list(channel_mapping or [0, 1]),
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

    # RASTATIME 2026-08-31 — start() now carries the channel selection
    # (default plain stereo) and the friendly-name hint for the feeder.
    capture.start.assert_called_once_with(
        event.device_id,
        channel_mapping=(0, 1),
        device_name=event.device_name,
    )
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


# ---- _on_stop: Phase-F-2 race fix #3 (device-switch) ------------------


def test_on_stop_linein_device_switch_does_not_kill_new_source(
    liquidsoap_scheduler,
):
    """
    Phase-F-2 race fix #3: when show B (different device) has already
    taken over via its own _on_linein_start before show A's late _on_stop
    fires, A must NOT call linein_stop — that would mute B's freshly
    started source (the live 2026-05-29 21:15:00 device-switch silence,
    where the jabra-show start was followed 2 ms later by the tascam-show
    stop).  Covered by the race-fix-#1 _playing_key guard at the top of
    _on_stop, here exercised in the device-SWITCH context.
    """
    sched, engine, capture = liquidsoap_scheduler
    event_a = _make_linein_event(
        device_id="0fb30b0b-c875-432b-a48f-dbb5208995c9", id_=1, row_id=111,
    )
    event_b = _make_linein_event(
        device_id="eae46b8b-2949-46ee-a1ca-c8ab319f1eee", id_=2, row_id=222,
    )

    # Show A starts, then show B (different device) takes over.
    sched._on_linein_start("keyA", event_a)
    sched._on_linein_start("keyB", event_b)
    assert sched._playing_key == "keyB"
    assert sched._linein_generation == 2  # bumped once per (re)start

    engine.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    # A's stop fires late.
    sched._on_stop("keyA")

    # A is no longer the playing event → no teardown of B's source.
    engine.linein_stop.assert_not_called()
    # B's bookkeeping survives intact.
    assert sched._playing_key == "keyB"
    assert sched._current_event is event_b


def test_on_stop_linein_skips_stop_when_generation_bumped_mid_teardown(
    liquidsoap_scheduler,
):
    """
    Phase-F-2 race fix #3 (final guard): if a follow-up show (re)starts
    the line-in source DURING A's teardown window — after A cleared its
    bookkeeping but before it calls linein_stop — the generation counter
    moves and A must skip linein_stop.  Simulated by bumping the counter
    from capture.stop()'s side effect, which runs between the generation
    snapshot and the final guard.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()
    sched._on_linein_start("key1", event)  # gen -> 1, playing key1
    assert sched._linein_generation == 1

    engine.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    # Simulate a racing follow-up _on_linein_start that bumps the
    # generation (and reclaims the spotlight) mid-teardown.
    def _bump(*_args, **_kwargs):
        sched._linein_generation += 1
        sched._playing_key = "key2"

    capture.stop.side_effect = _bump

    sched._on_stop("key1")

    capture.stop.assert_called_once()
    # Final guard tripped → the new show's source is left running.
    engine.linein_stop.assert_not_called()


# ---- RASTATIME 2026-08-31: multichannel line-in (channel selection) ----


def test_linein_start_liquidsoap_multichannel_uses_feeder_and_http(
    liquidsoap_scheduler,
):
    """
    A channel_mapping other than plain stereo routes through the
    FfmpegLineinCapture (MME feeder -> /linein-capture) and arms the
    linein_http companion source — NOT the direct dshow source.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event(
        device_name="Mikrofon (US-16x08)", channel_mapping=[4, 5]
    )

    sched._on_linein_start("key1", event)

    capture.start.assert_called_once_with(
        event.device_id,
        channel_mapping=(4, 5),
        device_name="Mikrofon (US-16x08)",
    )
    engine.linein_start_http.assert_called_once_with()
    engine.linein_start.assert_not_called()


def test_linein_start_liquidsoap_multichannel_without_name_falls_back(
    liquidsoap_scheduler,
):
    """
    A multichannel mapping on a legacy row without a stored
    device_name cannot run the feeder (no PortAudio lookup key) —
    falls back to the direct dshow source instead of staying silent.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event(device_name="", channel_mapping=[4, 5])

    sched._on_linein_start("key1", event)

    capture.start.assert_not_called()
    engine.linein_start_http.assert_not_called()
    engine.linein_start.assert_called_once()


def test_linein_same_device_different_mapping_is_not_a_transition(
    liquidsoap_scheduler,
):
    """
    Back-to-back shows on the SAME interface but different channel
    pairs (two studios on one multichannel card) must NOT ride the
    same-device-transition shortcut — the second show needs its own
    capture with its own mapping.
    """
    sched, engine, capture = liquidsoap_scheduler
    first = _make_linein_event(
        device_name="Mikrofon (US-16x08)", channel_mapping=[4, 5]
    )
    sched._current_event = first
    capture.is_running = True

    second = _make_linein_event(
        device_name="Mikrofon (US-16x08)", channel_mapping=[6, 7]
    )
    sched._on_linein_start("key2", second)

    # No shortcut: the http companion is (re)armed for the new pair.
    capture.start.assert_called_once_with(
        second.device_id,
        channel_mapping=(6, 7),
        device_name="Mikrofon (US-16x08)",
    )
    engine.linein_start_http.assert_called_once_with()
