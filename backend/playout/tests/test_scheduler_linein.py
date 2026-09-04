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


def test_linein_start_liquidsoap_plain_stereo_uses_feeder_and_http(
    liquidsoap_scheduler,
):
    """
    Phase-F-2 opened the dshow device directly for plain stereo.  Since
    2026-09-03 ("Option B") EVERY row that carries a device name goes
    through the FfmpegLineinCapture feeder + the linein_http companion:
    the direct dshow path addresses the device by an endpoint GUID that
    DirectShow does not know and broadcast silence on the Tascam.
    """
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    capture.start.assert_called_once_with(
        event.device_id, channel_mapping=(0, 1), device_name=event.device_name,
    )
    engine.linein_start_http.assert_called_once()
    # The by-GUID dshow source must NOT be used for a row with a name.
    engine.linein_start.assert_not_called()
    # Legacy engine.play MUST NOT be called in this path
    engine.play.assert_not_called()


def test_linein_start_liquidsoap_clears_request_queue_first(
    liquidsoap_scheduler,
):
    """
    Before the line-in source is armed, the Liquidsoap path issues
    engine.stop() (= flush pending + deferred request.queue.skip) so
    the previous scheduled track doesn't linger in the background while
    input.http buffers.
    """
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True
    event = _make_linein_event()

    sched._on_linein_start("key1", event)

    # engine.stop must be called BEFORE the http companion is armed
    method_names = [c[0] for c in engine.mock_calls]
    assert "stop" in method_names
    assert "linein_start_http" in method_names
    assert method_names.index("stop") < method_names.index("linein_start_http")


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
    # start() is mocked, so simulate the capture coming up — the
    # scheduler checks is_running before arming linein_http
    # (RASTATIME 2026-09-01 guard).
    capture.is_running = True

    sched._on_linein_start("key1", event)

    capture.start.assert_called_once_with(
        event.device_id,
        channel_mapping=(4, 5),
        device_name="Mikrofon (US-16x08)",
    )
    engine.linein_start_http.assert_called_once_with()
    engine.linein_start.assert_not_called()


def test_linein_start_liquidsoap_feeder_gave_up_stops_prearmed_http(
    liquidsoap_scheduler,
):
    """
    RASTATIME 2026-09-01: capture.start() gives up quietly after its
    retry ladder (no exception) - Liquidsoap must not end up polling a
    missing mount with a 404 every poll_delay for the rest of the slot.

    Since 2026-09-03 (Lever 2 of the start-gap fix) the http companion
    is armed BEFORE the blocking feeder start so its buffer fills during
    the feeder health-check; the guard therefore now reads "armed, then
    stopped again", not "never armed".
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event(
        device_name="Mikrofon (US-16x08)", channel_mapping=[4, 5]
    )
    capture.is_running = False  # start() ran but nothing came up

    sched._on_linein_start("key1", event)

    capture.start.assert_called_once()
    engine.linein_start_http.assert_called_once()
    engine.linein_stop.assert_called_once()
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


# =====================================================================
# RASTATIME 2026-09-04 - show-transition fixes after the 11:00 incident
# (line-in stayed on air through a jingle + webstream show, stale
# jingles spilled out 7 min late, a key shift killed the running
# line-in).  See CHANGELOG 2026-09-04.
# =====================================================================

import threading
from datetime import timedelta

from libretime_playout.player.events import FileEvent, WebStreamEvent
from libretime_playout.playout_scheduler import LINEIN_FOLLOW_UP_WINDOW_SECONDS


def _arm_fake_timer(sched, key, event):
    """Register ``event`` as armed with a live (never-firing) start timer."""
    t = threading.Timer(3600, lambda: None)
    t.daemon = True
    t.start()
    sched._timers[key] = (t, None)
    sched._armed_events[key] = event
    return t


def _playing_linein(sched, capture, key="A", **kw):
    event = _make_linein_event(**kw)
    sched._playing_key = key
    sched._current_event = event
    sched._current_audio_path = capture.listen_url
    capture.is_running = True
    return event


def _file_event(start, row_id=777):
    return FileEvent(
        type=EventKind.FILE,
        start=start,
        end=start + timedelta(seconds=50),
        row_id=row_id,
        id=1,
        uri="file:///C:/rastatime/scheduler/1.mp3",
        show_name="bbc",
        track_title="Jingle",
        artist_name="Radio",
        mime="audio/mpeg",
        filesize=1,
        cue_in=0.0,
        cue_out=50.0,
        fade_in=0.0,
        fade_out=0.0,
        replay_gain=None,
    )


def _webstream_event(start, row_id=888):
    return WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START,
        start=start,
        end=start + timedelta(minutes=5),
        row_id=row_id,
        uri="http://stream.example/bbc",
        id=2,
        show_name="bbc",
    )


# --- Fix 1: follow-up rule needs a TRUE back-to-back successor ---------

def test_on_stop_tears_down_linein_when_same_device_follow_up_is_minutes_away(
    liquidsoap_scheduler,
):
    """The 11:00 incident: a same-device line-in armed 7 min later kept
    the ending line-in on air through the whole show in between."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    later = _make_linein_event(row_id=99999).model_copy(update={
        "start": datetime.utcnow() + timedelta(minutes=7),
        "end": datetime.utcnow() + timedelta(minutes=12),
    })
    t = _arm_fake_timer(sched, "B", later)
    try:
        sched._on_stop("A")
    finally:
        t.cancel()

    capture.stop.assert_called_once()
    engine.linein_stop.assert_called_once()
    assert sched._playing_key is None
    assert sched._current_event is None


def test_on_stop_keeps_linein_alive_for_a_back_to_back_same_device_follow_up(
    liquidsoap_scheduler,
):
    """Back-to-back shows sharing a mic still hand the capture over
    without a bounce (Phase B.4 race fix #2 preserved)."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    nxt = _make_linein_event(row_id=99999).model_copy(update={
        "start": datetime.utcnow() + timedelta(seconds=0.5),
        "end": datetime.utcnow() + timedelta(minutes=5),
    })
    assert 0.5 < LINEIN_FOLLOW_UP_WINDOW_SECONDS
    t = _arm_fake_timer(sched, "B", nxt)
    try:
        sched._on_stop("A")
    finally:
        t.cancel()

    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    # bookkeeping deliberately left in place for B's same-device check
    assert sched._playing_key == "A"


# --- Fix 4: ownership re-check + successor closes the predecessor -----

def test_on_stop_bails_when_superseded_mid_teardown(liquidsoap_scheduler):
    """STOP(A) passed its top check, then PLAY(B) took the spotlight
    before A reset the bookkeeping (11:00:09 race).  A must neither wipe
    B's bookkeeping nor touch B's sources."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")

    def _b_takes_over(*_a, **_k):
        sched._playing_key = "B"
        sched._current_event = _file_event(datetime.utcnow())
    # _cue_item_end runs between the top check and the reset
    sched._cue_item_end = _b_takes_over

    sched._on_stop("A")

    assert sched._playing_key == "B"
    assert isinstance(sched._current_event, FileEvent)
    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    engine.stop.assert_not_called()


def test_file_start_closes_a_linein_predecessor_itself(liquidsoap_scheduler):
    """Whoever takes the spotlight from a line-in closes it: a line-in
    that stays up outranks every scheduled track in the bus switch."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._ensure_file_cached = lambda evt: "C:/rastatime/scheduler/1.mp3"
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()
    sched._start_streamers = MagicMock()
    sched._stop_streamers = MagicMock()

    sched._on_file_start("B", _file_event(datetime.utcnow()))

    capture.stop.assert_called_once()
    engine.linein_stop.assert_called_once()
    names = [c[0] for c in engine.mock_calls]
    assert names.index("linein_stop") < names.index("stop") < names.index("play")
    assert sched._playing_key == "B"


def test_webstream_start_closes_a_linein_predecessor_itself(liquidsoap_scheduler):
    """11:06 symptom: when the webstream ended, the switch fell straight
    back onto the line-in it had been masking."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()

    sched._on_webstream_start("B", _webstream_event(datetime.utcnow()))

    capture.stop.assert_called_once()
    engine.linein_stop.assert_called_once()
    engine.webstream_start.assert_called_once()


def test_linein_start_closes_a_webstream_predecessor_itself(liquidsoap_scheduler):
    """A webstream outranks the line-in in the bus switch, so a racing
    _on_stop that bails would leave the line-in inaudible."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._playing_key = "A"
    sched._current_event = _webstream_event(datetime.utcnow() - timedelta(minutes=5))
    capture.is_running = True

    sched._on_linein_start("B", _make_linein_event())

    engine.webstream_stop.assert_called_once()
    engine.linein_start_http.assert_called_once()


def test_file_start_after_a_file_touches_no_exclusive_source(liquidsoap_scheduler):
    """File -> file is the hot path; it must stay a plain stop + play."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._playing_key = "A"
    sched._current_event = _file_event(datetime.utcnow() - timedelta(seconds=40))
    sched._ensure_file_cached = lambda evt: "C:/rastatime/scheduler/1.mp3"
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()
    sched._start_streamers = MagicMock()
    sched._stop_streamers = MagicMock()

    sched._on_file_start("B", _file_event(datetime.utcnow(), row_id=778))

    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    engine.webstream_stop.assert_not_called()


# --- Option A: identity instead of keys --------------------------------

def test_same_scheduled_item_identity():
    from libretime_playout.playout_scheduler import PlayoutScheduler as S
    now = datetime.utcnow()
    a = _make_linein_event(row_id=5)
    assert S._same_scheduled_item(a, a.model_copy())
    assert not S._same_scheduled_item(a, a.model_copy(update={"row_id": 6}))
    assert not S._same_scheduled_item(a, a.model_copy(update={"device_id": "other"}))
    assert not S._same_scheduled_item(a, a.model_copy(update={"channel_mapping": [2, 3]}))
    f = _file_event(now)
    assert S._same_scheduled_item(f, f.model_copy())
    assert not S._same_scheduled_item(f, f.model_copy(update={"start": now + timedelta(seconds=1)}))
    assert not S._same_scheduled_item(f, a)
    assert not S._same_scheduled_item(None, f)
    w = _webstream_event(now)
    assert not S._same_scheduled_item(
        w, w.model_copy(update={"type": EventKind.WEB_STREAM_BUFFER_START})
    )


def _refresh_with(sched, events):
    """Run refresh() against a canned schedule; cancel the timers it arms."""
    sched._reload_stream_outputs_if_changed = MagicMock()
    with patch("libretime_playout.playout_scheduler.get_schedule", return_value=events):
        sched.refresh()
    sched._cancel_all_timers()


def test_refresh_rebinds_the_playing_linein_when_its_key_shifts(
    liquidsoap_scheduler,
):
    """11:08:17 incident: the running line-in came back under another
    key and was torn down as 'removed from schedule'."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    now = datetime.utcnow()
    running = _make_linein_event().model_copy(update={
        "start": now - timedelta(seconds=78), "end": now + timedelta(minutes=4),
    })
    sched._playing_key = "2026-09-04-09-07-00_0"
    sched._current_event = running
    sched._current_audio_path = capture.listen_url
    capture.is_running = True

    _refresh_with(sched, {"2026-09-04-09-07-00": running.model_copy()})

    assert sched._playing_key == "2026-09-04-09-07-00"
    capture.stop.assert_not_called()
    engine.stop.assert_not_called()
    engine.linein_start_http.assert_not_called()  # no catch-up bounce either


def test_refresh_still_tears_down_a_really_removed_item(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    now = datetime.utcnow()
    running = _make_linein_event().model_copy(update={
        "start": now - timedelta(seconds=78), "end": now + timedelta(minutes=4),
    })
    sched._playing_key = "K"
    sched._current_event = running
    sched._current_audio_path = capture.listen_url
    capture.is_running = True
    # a DIFFERENT item now sits under our old key; ours is gone.  It
    # starts in the future so it is merely armed (an in-progress one
    # would legitimately trigger a catch-up on top of the teardown).
    other = _make_linein_event(row_id=4242).model_copy(update={
        "start": now + timedelta(minutes=2), "end": now + timedelta(minutes=6),
    })

    _refresh_with(sched, {"K": other})

    capture.stop.assert_called_once()
    engine.stop.assert_called_once()
    assert sched._current_event is None
    assert sched._playing_key is None


def test_file_catch_up_rebinds_instead_of_replaying_the_same_item(
    liquidsoap_scheduler,
):
    sched, engine, capture = liquidsoap_scheduler
    now = datetime.utcnow()
    playing = _file_event(now - timedelta(seconds=9))
    sched._playing_key = "X_1"
    sched._current_event = playing
    with patch.object(sched, "_on_file_start") as on_start:
        sched._arm_file_event("X", playing.model_copy(), now)
        start_t, stop_t = sched._timers["X"]
        stop_t.cancel()
    on_start.assert_not_called()
    assert start_t is None
    assert sched._playing_key == "X"


def test_webstream_catch_up_rebinds_instead_of_reconnecting(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    now = datetime.utcnow()
    playing = _webstream_event(now - timedelta(seconds=30))
    sched._playing_key = "W_0"
    sched._current_event = playing
    with patch.object(sched, "_on_webstream_start") as on_start:
        sched._arm_webstream_event("W", playing.model_copy(), now)
        start_t, stop_t = sched._timers["W"]
        stop_t.cancel()
    on_start.assert_not_called()
    assert start_t is None
    assert sched._playing_key == "W"


def test_re_arming_the_playing_key_itself_logs_no_rebinding(
    liquidsoap_scheduler, caplog
):
    """First live run of ff567ce (2026-09-04 15:12:52): the identity
    branch fired for the playing key itself and logged a no-op
    'Catch-up skipped (X -> X); rebinding' on every refresh."""
    import logging
    sched, engine, capture = liquidsoap_scheduler
    now = datetime.utcnow()
    playing = _webstream_event(now - timedelta(seconds=30))
    sched._playing_key = "W_0"
    sched._current_event = playing
    with caplog.at_level(logging.INFO), patch.object(sched, "_on_webstream_start") as on_start:
        sched._arm_webstream_event("W_0", playing.model_copy(), now)
        sched._timers["W_0"][1].cancel()
    on_start.assert_not_called()
    assert sched._playing_key == "W_0"
    assert "rebinding" not in caplog.text

    track = _file_event(now - timedelta(seconds=9))
    sched._playing_key = "F_0"
    sched._current_event = track
    caplog.clear()
    with caplog.at_level(logging.INFO), patch.object(sched, "_on_file_start") as on_start:
        sched._arm_file_event("F_0", track.model_copy(), now)
        sched._timers["F_0"][1].cancel()
    on_start.assert_not_called()
    assert "rebinding" not in caplog.text
