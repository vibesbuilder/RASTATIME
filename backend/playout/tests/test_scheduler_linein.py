"""
RASTATIME 2026-05-29 — Unit tests for PlayoutScheduler's linein
hooks in Liquidsoap-Mode (Phase F).

Scheduled line-input items use Liquidsoap's dedicated ``input.http``
source bound to FfmpegLineinCapture's local Icecast mount
(FfmpegLineinCapture is the Python subprocess that captures the
device through the MME feeder):

  FfmpegLineinCapture → /linein-capture → Liquidsoap input.http
                                          → bus → Icecast (×3)
                                          → output.file (recording)

(The legacy mpv + FfmpegStreamer consumer path was deleted on
2026-09-10.)

These tests verify:
  * ``_on_linein_start`` — feeder vs. direct-dshow decision, gates
  * ``_on_stop`` — linein-specific teardown via linein_stop()
  * ``_on_linein_capture_restart`` — the watchdog re-arms input.http
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rastatime_playout.engine.interface import PlayoutState
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.player.events import EventKind, LineinEvent


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


def _patched_scheduler():
    """
    Build a PlayoutScheduler with a mocked FfmpegLineinCapture so the
    test doesn't try to spawn an actual ffmpeg subprocess.
    """
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    api_client = MagicMock()

    # Patch FfmpegLineinCapture constructor to return a mock that
    # behaves like a working capture (start/stop succeed, is_running
    # reports the spawning state).
    with patch(
        "rastatime_playout.playout_scheduler.FfmpegLineinCapture"
    ) as mock_capture_cls:
        capture_instance = MagicMock()
        capture_instance.is_running = False
        capture_instance.listen_url = "http://localhost:8000/linein-capture"
        mock_capture_cls.return_value = capture_instance

        sched = PlayoutScheduler(
            engine=engine,
            api_client=api_client,
        )
        # Patch the device resolver so it doesn't try to use the
        # WindowsAudioDeviceManager.  Returns the input device_id
        # unchanged (no GUID-mismatch fallback test scenario).
        sched._resolve_linein_device = lambda evt: evt.device_id
        return sched, engine, capture_instance


@pytest.fixture
def liquidsoap_scheduler():
    return _patched_scheduler()


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


# ---- _on_stop: Liquidsoap linein teardown -----------------------------


def test_on_stop_liquidsoap_linein_calls_linein_stop_and_capture_stop(
    liquidsoap_scheduler,
):
    """
    In Liquidsoap-Mode, when a LineinEvent is the current event,
    _on_stop must take it off air and tear it down.  Since 2026-09-04
    (Paket 2) that is two steps: the bus GATE closes at once (the switch
    fades the line-in out under the successor while its buffered tail
    plays), and FfmpegLineinCapture + the input.http source are stopped
    only after the drain.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()
    sched._on_linein_start("key1", event)
    engine.reset_mock()
    capture.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    sched._on_stop("key1")

    engine.linein_gate.assert_called_once_with(False)
    capture.stop.assert_not_called()        # the tail is still draining
    engine.linein_stop.assert_not_called()
    engine.stop.assert_not_called()
    assert sched._playing_key is None
    assert sched._current_event is None

    sched._drained_linein_stop(sched._linein_generation)
    capture.stop.assert_called_once()
    engine.linein_stop.assert_called_once()


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
    the line-in source DURING A's teardown window, the generation
    counter moves and A must not touch the source - since Paket 2 that
    means it must not even close the gate (the newer show owns it).
    Simulated by bumping the counter from the cue-sheet hook, which runs
    between the generation snapshot and the guards.
    """
    sched, engine, capture = liquidsoap_scheduler
    event = _make_linein_event()
    sched._on_linein_start("key1", event)  # gen -> 1, playing key1
    assert sched._linein_generation == 1
    engine.reset_mock()
    capture.reset_mock()
    engine.get_state.return_value = PlayoutState.PLAYING

    def _bump(*_args, **_kwargs):
        sched._linein_generation += 1
    sched._cue_item_end = _bump

    sched._on_stop("key1")

    engine.linein_gate.assert_not_called()
    engine.linein_stop.assert_not_called()
    capture.stop.assert_not_called()


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

from rastatime_playout.player.events import FileEvent, WebStreamEvent
from rastatime_playout.playout_scheduler import LINEIN_FOLLOW_UP_WINDOW_SECONDS


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
    the ending line-in on air through the whole show in between.  Now
    the line-in is released (gate) and torn down after the drain."""
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

    engine.linein_gate.assert_called_once_with(False)
    assert sched._playing_key is None
    assert sched._current_event is None
    sched._drained_linein_stop(sched._linein_generation)
    capture.stop.assert_called_once()
    engine.linein_stop.assert_called_once()


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

    class _ArmedEvents(dict):
        # The follow-up scan iterates _armed_events between the top check
        # and the ownership re-check: the moment PLAY(B) can take the
        # spotlight.  (Until 2026-09-10 the cue end marker sat there and
        # served as the injection point; it now runs after the re-check.)
        def items(self):
            sched._playing_key = "B"
            sched._current_event = _file_event(datetime.utcnow())
            return dict.items(self)

    sched._armed_events = _ArmedEvents(sched._armed_events)

    sched._on_stop("A")

    assert sched._playing_key == "B"
    assert isinstance(sched._current_event, FileEvent)
    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    engine.stop.assert_not_called()


def test_file_start_closes_a_linein_predecessor_itself(liquidsoap_scheduler):
    """Whoever takes the spotlight from a line-in releases it: the gate
    closes before the queue is touched, so the bus fades the line-in
    out under the jingle; the capture is stopped only after the drain."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._ensure_file_cached = lambda evt: "C:/rastatime/scheduler/1.mp3"
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()

    sched._on_file_start("B", _file_event(datetime.utcnow()))

    engine.linein_gate.assert_called_once_with(False)
    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    names = [c[0] for c in engine.mock_calls]
    assert names.index("linein_gate") < names.index("stop") < names.index("play")
    assert sched._playing_key == "B"


def test_webstream_start_closes_a_linein_predecessor_itself(liquidsoap_scheduler):
    """11:06 symptom: when the webstream ended, the switch fell straight
    back onto the line-in it had been masking.  The webstream releases
    the line-in (gate) and opens its own gate after connecting."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()

    sched._on_webstream_start("B", _webstream_event(datetime.utcnow()))

    engine.linein_gate.assert_called_once_with(False)
    capture.stop.assert_not_called()
    engine.webstream_start.assert_called_once()
    engine.webstream_gate.assert_called_with(True)


def test_linein_start_closes_a_webstream_predecessor_itself(liquidsoap_scheduler):
    """A webstream outranks the line-in in the bus switch, so the line-in
    must release it itself: gate closed at once (the bus fades it out),
    source stopped after the drain."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._playing_key = "A"
    sched._current_event = _webstream_event(datetime.utcnow() - timedelta(minutes=5))
    capture.is_running = True

    sched._on_linein_start("B", _make_linein_event())

    engine.webstream_gate.assert_called_once_with(False)
    engine.webstream_stop.assert_not_called()
    engine.linein_start_http.assert_called_once()
    engine.linein_gate.assert_called_with(True)
    sched._drained_webstream_stop(sched._webstream_generation)
    engine.webstream_stop.assert_called_once()


def test_file_start_after_a_file_touches_no_exclusive_source(liquidsoap_scheduler):
    """File -> file is the hot path; it must stay a plain stop + play."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._playing_key = "A"
    sched._current_event = _file_event(datetime.utcnow() - timedelta(seconds=40))
    sched._ensure_file_cached = lambda evt: "C:/rastatime/scheduler/1.mp3"
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()

    sched._on_file_start("B", _file_event(datetime.utcnow(), row_id=778))

    capture.stop.assert_not_called()
    engine.linein_stop.assert_not_called()
    engine.webstream_stop.assert_not_called()


# --- Option A: identity instead of keys --------------------------------

def test_same_scheduled_item_identity():
    from rastatime_playout.playout_scheduler import PlayoutScheduler as S
    now = datetime.utcnow()
    a = _make_linein_event(row_id=5)
    assert S._same_scheduled_item(a, a.model_copy())
    assert not S._same_scheduled_item(a, a.model_copy(update={"row_id": 6}))
    assert not S._same_scheduled_item(a, a.model_copy(update={"device_id": "other"}))
    assert not S._same_scheduled_item(a, a.model_copy(update={"channel_mapping": [2, 3]}))
    f = _file_event(now)
    assert S._same_scheduled_item(f, f.model_copy())
    # 2026-09-28: the start is no longer part of the identity (a show-builder
    # edit re-times the running row); the medium (file id) is
    assert S._same_scheduled_item(f, f.model_copy(update={"start": now + timedelta(seconds=1)}))
    assert not S._same_scheduled_item(f, f.model_copy(update={"id": 99}))
    assert not S._same_scheduled_item(f, a)
    assert not S._same_scheduled_item(None, f)
    w = _webstream_event(now)
    assert not S._same_scheduled_item(
        w, w.model_copy(update={"type": EventKind.WEB_STREAM_BUFFER_START})
    )


def _refresh_with(sched, events):
    """Run refresh() against a canned schedule; cancel the timers it arms."""
    with patch("rastatime_playout.playout_scheduler.get_schedule", return_value=events):
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


# =====================================================================
# RASTATIME 2026-09-04 - Paket 2: pre-warm + bus gates + drained stop
# =====================================================================

from rastatime_playout.playout_scheduler import PREPARE_LEAD_SECONDS


class _FakeTimer:
    """Records what would be scheduled; .fire() runs it synchronously."""
    instances = []

    def __init__(self, interval, function, args=()):
        self.interval, self.function, self.args = interval, function, tuple(args)
        self.daemon = False
        self.cancelled = False
        _FakeTimer.instances.append(self)

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True

    def is_alive(self):
        return not self.cancelled

    def join(self, *_):
        pass

    def fire(self):
        self.function(*self.args)


@pytest.fixture
def fake_timer():
    _FakeTimer.instances = []
    with patch("rastatime_playout.playout_scheduler.threading.Timer", _FakeTimer):
        yield _FakeTimer


def _future_linein(seconds_ahead, **kw):
    now = datetime.utcnow()
    return _make_linein_event(**kw).model_copy(update={
        "start": now + timedelta(seconds=seconds_ahead),
        "end": now + timedelta(seconds=seconds_ahead + 300),
    })


def test_prepare_timer_is_armed_ten_seconds_before_the_slot(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._arm_linein_event("K", _future_linein(60), datetime.utcnow())
    prep = [t for t in fake_timer.instances if t.function == sched._on_linein_prepare]
    assert len(prep) == 1
    assert abs(prep[0].interval - (60 - PREPARE_LEAD_SECONDS)) < 0.5
    assert sched._prepare_timers["K"] is prep[0]


def test_no_prepare_timer_when_the_slot_is_too_close(liquidsoap_scheduler, fake_timer):
    """Below MIN_PREPARE_SECONDS a pre-warm cannot finish; the slot starts
    the normal way.  (Inside the 10 s lead window but above that minimum
    the pre-warm fires at once - see the 2026-09-05 test further down.)"""
    sched, engine, capture = liquidsoap_scheduler
    sched._arm_linein_event("K", _future_linein(1.5), datetime.utcnow())
    assert not [t for t in fake_timer.instances if t.function == sched._on_linein_prepare]


def test_cancel_all_timers_cancels_prepare_timers(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._arm_linein_event("K", _future_linein(60), datetime.utcnow())
    sched._cancel_all_timers()
    assert sched._prepare_timers == {}
    assert all(t.cancelled for t in fake_timer.instances)


def test_linein_prepare_brings_the_source_up_with_the_gate_closed(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True
    event = _future_linein(10)

    sched._on_linein_prepare("K", event)

    engine.linein_gate.assert_called_with(False)
    engine.linein_start_http.assert_called_once()
    capture.start.assert_called_once()
    assert sched._prepared is not None and sched._prepared[0] == "K"
    names = [c[0] for c in engine.mock_calls]
    assert names.index("linein_gate") < names.index("linein_start_http")


def test_linein_prepare_is_skipped_while_a_line_in_is_on_air(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched._current_event = _make_linein_event(row_id=1)
    sched._on_linein_prepare("K", _future_linein(10, row_id=2))
    capture.start.assert_not_called()
    engine.linein_gate.assert_not_called()
    assert sched._prepared is None


def test_linein_prepare_failure_reopens_the_gate(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = False
    sched._on_linein_prepare("K", _future_linein(10))
    engine.linein_stop.assert_called_once()
    engine.linein_gate.assert_called_with(True)
    assert sched._prepared is None


def test_prepared_linein_start_only_opens_the_gate(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    capture.is_running = True
    event = _future_linein(0)
    sched._prepared = ("K", event)

    sched._on_linein_start("K", event.model_copy())

    engine.linein_gate.assert_called_with(True)
    engine.linein_start_http.assert_not_called()
    capture.start.assert_not_called()
    engine.stop.assert_called_once()   # queue cleared as usual
    assert sched._prepared is None
    assert sched._playing_key == "K"


def test_unprepared_linein_start_opens_the_gate_on_the_normal_path(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    capture.is_running = True
    sched._on_linein_start("K", _make_linein_event())
    engine.linein_start_http.assert_called_once()
    engine.linein_gate.assert_called_with(True)


def test_slot_end_closes_the_gate_and_stops_after_the_drain(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")

    sched._on_stop("A")

    engine.linein_gate.assert_called_once_with(False)
    engine.linein_stop.assert_not_called()      # not yet - the tail is draining
    capture.stop.assert_not_called()
    drain = [t for t in fake_timer.instances if t.function == sched._drained_linein_stop]
    assert len(drain) == 1
    assert abs(drain[0].interval - sched._drain_seconds) < 1e-6
    drain[0].fire()
    engine.linein_stop.assert_called_once()
    capture.stop.assert_called_once()


def test_drained_stop_is_skipped_when_a_newer_line_in_took_over(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._on_stop("A")
    drain = [t for t in fake_timer.instances if t.function == sched._drained_linein_stop][0]
    sched._linein_generation += 1   # e.g. the next line-in's prepare/start
    drain.fire()
    engine.linein_stop.assert_not_called()
    capture.stop.assert_not_called()


def test_successor_releases_a_line_in_through_the_gate(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    _playing_linein(sched, capture, key="A")
    sched._ensure_file_cached = lambda evt: "C:/rastatime/scheduler/1.mp3"
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()

    sched._on_file_start("B", _file_event(datetime.utcnow()))

    engine.linein_gate.assert_called_once_with(False)
    capture.stop.assert_not_called()
    names = [c[0] for c in engine.mock_calls]
    assert names.index("linein_gate") < names.index("stop") < names.index("play")


def test_drain_seconds_follow_the_show_crossfade():
    """2026-09-27: input_transition_seconds is the SHOW crossfade; the
    drain is that fade plus a margin (0 -> a 50 ms cut, drain 0.5 s)."""
    s1, _, _ = _patched_scheduler()
    assert s1._drain_seconds == 2.0 + 0.5      # default input_transition_seconds
    from rastatime_playout.playout_scheduler import PlayoutScheduler
    with patch("rastatime_playout.playout_scheduler.FfmpegLineinCapture"):
        s2 = PlayoutScheduler(engine=MagicMock(), api_client=MagicMock(),
                              input_transition_seconds=0.0)
        s3 = PlayoutScheduler(engine=MagicMock(), api_client=MagicMock(),
                              input_transition_seconds=1.0, track_crossfade_seconds=2.5)
    assert s2._drain_seconds == 0.5
    assert s3._drain_seconds == 1.5
    assert s3._cross_buffer_seconds == 2.5     # max(track, show, floor)


def test_webstream_prepare_start_and_release(liquidsoap_scheduler, fake_timer):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()
    event = _webstream_event(datetime.utcnow() + timedelta(seconds=10))

    sched._on_webstream_prepare("W", event)
    engine.webstream_gate.assert_called_with(False)
    engine.webstream_start.assert_called_once()
    assert sched._prepared[0] == "W"

    sched._on_webstream_start("W", event.model_copy())
    engine.webstream_start.assert_called_once()          # no reconnect
    engine.webstream_gate.assert_called_with(True)
    assert sched._prepared is None

    sched._on_stop("W")
    engine.webstream_gate.assert_called_with(False)
    engine.webstream_stop.assert_not_called()
    drain = [t for t in fake_timer.instances if t.function == sched._drained_webstream_stop]
    assert len(drain) == 1
    drain[0].fire()
    engine.webstream_stop.assert_called_once()


def test_refresh_undoes_a_pre_warm_whose_item_vanished(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    capture.is_running = True
    event = _future_linein(8)
    sched._prepared = ("K", event)

    _refresh_with(sched, {})   # empty schedule

    engine.linein_stop.assert_called_once()
    capture.stop.assert_called_once()
    engine.linein_gate.assert_called_with(True)
    assert sched._prepared is None


def test_reset_gates_opens_both(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    sched.reset_gates()
    engine.linein_gate.assert_called_once_with(True)
    engine.webstream_gate.assert_called_once_with(True)


# --- 2026-09-05 follow-ups after the 19:50-20:22 live run -----------------

from rastatime_playout.playout_scheduler import MIN_PREPARE_SECONDS


def test_prepare_fires_at_once_when_the_refresh_lands_inside_the_lead_window(
    liquidsoap_scheduler, fake_timer
):
    """20:16:49 refresh for a 20:17:00 slot: the pre-warm was dropped and
    the slot started with the normal 2 s gap."""
    sched, engine, capture = liquidsoap_scheduler
    sched._arm_linein_event("K", _future_linein(6), datetime.utcnow())
    prep = [t for t in fake_timer.instances if t.function == sched._on_linein_prepare]
    assert len(prep) == 1
    assert prep[0].interval == 0.0


def test_min_prepare_seconds_is_below_the_lead(liquidsoap_scheduler, fake_timer):
    """The boundary the older 'too close' test relies on."""
    assert 0 < MIN_PREPARE_SECONDS < PREPARE_LEAD_SECONDS


def test_linein_prepare_is_idempotent_for_the_same_item(liquidsoap_scheduler):
    """A refresh re-arms the prepare of an item that is already pre-warmed;
    the second call must not bounce the http source."""
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True
    event = _future_linein(10)
    sched._on_linein_prepare("K", event)
    sched._on_linein_prepare("K2", event.model_copy())   # same item, shifted key
    engine.linein_start_http.assert_called_once()
    capture.start.assert_called_once()


def test_same_webstream_next_show_is_a_bookkeeping_hand_over(liquidsoap_scheduler):
    """20:12 live: releasing + restarting the same URL cost a ~1 s dip."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()
    now = datetime.utcnow()
    prev = _webstream_event(now - timedelta(minutes=5), row_id=1)
    sched._playing_key = "A"
    sched._current_event = prev
    nxt = _webstream_event(now, row_id=2)          # same uri, same gain

    sched._on_webstream_start("B", nxt)

    engine.webstream_gate.assert_called_once_with(True)
    engine.webstream_start.assert_not_called()
    engine.webstream_stop.assert_not_called()
    assert sched._playing_key == "B" and sched._current_event is nxt


def test_different_webstream_next_show_hard_stops_the_old_one(liquidsoap_scheduler):
    """2026-09-05 11:44:30 regression: the drained release left the old
    stream playing through the whole new slot (set_url + start on a
    running input.http does not reconnect; the drained stop was skipped).
    With one stream source a different stream needs stop, then start."""
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    sched._cue_item_start = MagicMock()
    sched._notify_media_started = MagicMock()
    now = datetime.utcnow()
    sched._playing_key = "A"
    sched._current_event = _webstream_event(now - timedelta(minutes=5), row_id=1)
    other = _webstream_event(now, row_id=2).model_copy(update={"uri": "http://other.example/x"})

    sched._on_webstream_start("B", other)

    engine.webstream_stop.assert_called_once()
    engine.webstream_start.assert_called_once()
    names = [c[0] for c in engine.mock_calls]
    assert names.index("webstream_stop") < names.index("webstream_start")
    # no drained release for this case: the gate is only opened, never closed
    assert not any(c == ("webstream_gate", (False,), {}) for c in engine.mock_calls)
    engine.webstream_gate.assert_called_with(True)


def test_on_stop_keeps_the_stream_for_a_same_stream_back_to_back_follow_up(
    liquidsoap_scheduler
):
    sched, engine, capture = liquidsoap_scheduler
    sched._switcher = None
    now = datetime.utcnow()
    sched._playing_key = "A"
    sched._current_event = _webstream_event(now - timedelta(minutes=5), row_id=1)
    nxt = _webstream_event(now + timedelta(seconds=0.5), row_id=2)
    t = _arm_fake_timer(sched, "B", nxt)
    try:
        sched._on_stop("A")
    finally:
        t.cancel()
    engine.webstream_gate.assert_not_called()
    engine.webstream_stop.assert_not_called()
    assert sched._playing_key == "A"      # bookkeeping left for B's hand-over


# RASTATIME 2026-09-06 - webstreams pre-warm via WEBSTREAM_PREPARE_LEAD
# (reverted to 10 s from the 2026-09-05 "Option 1" 20 s); it must use
# the webstream constant, not accidentally hard-code the line-in one.
def test_prepare_timer_for_a_webstream_uses_the_webstream_lead(liquidsoap_scheduler, fake_timer):
    from rastatime_playout.playout_scheduler import WEBSTREAM_PREPARE_LEAD_SECONDS
    from rastatime_playout.player.events import EventKind, WebStreamEvent

    sched, engine, capture = liquidsoap_scheduler
    now = datetime.utcnow()
    event = WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START, start=now + timedelta(seconds=60),
        end=now + timedelta(seconds=360), row_id=7, id=7,
        uri="http://cloud.example/", show_name="cloud", input_gain_db=None,
    )
    sched._arm_webstream_event("W", event, now)
    prep = [t for t in fake_timer.instances if t.function == sched._on_webstream_prepare]
    assert len(prep) == 1
    assert WEBSTREAM_PREPARE_LEAD_SECONDS == 10.0
    assert abs(prep[0].interval - (60 - WEBSTREAM_PREPARE_LEAD_SECONDS)) < 0.5


# ---- capture watchdog restart callback (RASTATIME 2026-09-10) ----------
#
# The mpv cleanup replaced the callback's engine.play(listen_url) wiring
# (a request-queue push of the mount) with the Liquidsoap re-arm of the
# input.http companion.


def test_capture_restart_rearms_the_http_companion(liquidsoap_scheduler):
    sched, engine, _capture = liquidsoap_scheduler
    sched._playing_key = "key1"
    sched._current_event = _make_linein_event()      # stored device name -> feeder

    sched._on_linein_capture_restart()

    engine.linein_start_http.assert_called_once_with()
    engine.linein_gate.assert_called_once_with(True)
    engine.play.assert_not_called()


def test_capture_restart_is_a_noop_without_a_playing_linein(liquidsoap_scheduler):
    sched, engine, _capture = liquidsoap_scheduler

    sched._on_linein_capture_restart()

    engine.linein_start_http.assert_not_called()
    engine.play.assert_not_called()


def test_capture_restart_is_a_noop_while_a_dj_is_live(liquidsoap_scheduler):
    from rastatime_playout.source_switcher import SourceState

    sched, engine, _capture = liquidsoap_scheduler
    sched._current_event = _make_linein_event()
    switcher = MagicMock()
    switcher.current_state = SourceState.SHOW
    sched.set_source_switcher(switcher)

    sched._on_linein_capture_restart()

    engine.linein_start_http.assert_not_called()
    engine.linein_gate.assert_not_called()


def test_capture_restart_is_a_noop_for_direct_dshow_rows(liquidsoap_scheduler):
    sched, engine, _capture = liquidsoap_scheduler
    sched._current_event = _make_linein_event(device_name="")

    sched._on_linein_capture_restart()

    engine.linein_start_http.assert_not_called()
    engine.play.assert_not_called()


# =====================================================================
# RASTATIME 2026-10-02 - per-line-in input gain: every path that puts a
# line-in on air pushes rastatime_linein.input_gain_db to the .liq
# (engine.linein_set_gain -> var.set linein.gain).
# =====================================================================


def _running_linein_event(**kw) -> LineinEvent:
    """A line-in whose slot is running right now (resume needs end > now)."""
    now = datetime.utcnow().replace(microsecond=0)
    return _make_linein_event(**kw).model_copy(
        update={"start": now - timedelta(seconds=60), "end": now + timedelta(seconds=600)},
    )


def test_linein_start_pushes_the_input_gain(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True
    event = _make_linein_event().model_copy(update={"input_gain_db": 6.0})

    sched._on_linein_start("key1", event)

    engine.linein_set_gain.assert_called_once_with(6.0)
    # set before the source is armed, so the first frames already carry it
    names = [c[0] for c in engine.mock_calls]
    assert names.index("linein_set_gain") < names.index("linein_start_http")


def test_linein_start_without_gain_resets_to_unity(liquidsoap_scheduler):
    """None reaches the engine, which sets unity - no carry-over."""
    sched, engine, capture = liquidsoap_scheduler
    capture.is_running = True

    sched._on_linein_start("key1", _make_linein_event())

    engine.linein_set_gain.assert_called_once_with(None)


def test_same_device_transition_still_applies_the_new_gain(liquidsoap_scheduler):
    """Two line-ins on one device and pair keep the capture, but the
    second one's gain must replace the first one's."""
    sched, engine, capture = liquidsoap_scheduler
    sched._current_event = _make_linein_event(name="Studio A").model_copy(
        update={"input_gain_db": 6.0},
    )
    capture.is_running = True
    second = _make_linein_event(name="Studio A guest").model_copy(
        update={"input_gain_db": -3.0},
    )

    sched._on_linein_start("key2", second)

    engine.linein_set_gain.assert_called_once_with(-3.0)
    capture.start.assert_not_called()          # shortcut taken
    engine.linein_start_http.assert_not_called()


def test_linein_start_while_a_dj_is_live_sets_the_gain_for_the_resume(
    liquidsoap_scheduler,
):
    from rastatime_playout.source_switcher import SourceState

    sched, engine, _capture = liquidsoap_scheduler
    switcher = MagicMock()
    switcher.current_state = SourceState.SHOW
    sched.set_source_switcher(switcher)

    sched._on_linein_start(
        "key1", _make_linein_event().model_copy(update={"input_gain_db": 4.5}),
    )

    engine.linein_set_gain.assert_called_once_with(4.5)
    engine.linein_start_http.assert_not_called()


def test_resume_after_dj_reapplies_the_linein_gain(liquidsoap_scheduler):
    sched, engine, capture = liquidsoap_scheduler
    event = _running_linein_event().model_copy(update={"input_gain_db": 2.5})
    sched._current_event = event
    sched._current_audio_path = capture.listen_url

    sched._resume_scheduled_locked()

    engine.linein_set_gain.assert_called_once_with(2.5)
    engine.linein_start_http.assert_called_once_with()


def test_fresh_liquidsoap_gets_the_gain_of_the_linein_on_air(liquidsoap_scheduler):
    """A restarted Liquidsoap starts with linein.gain = 1.0."""
    sched, engine, _capture = liquidsoap_scheduler
    sched._current_event = _make_linein_event().model_copy(update={"input_gain_db": -6.0})
    engine.reset_mock()

    ok, _exc = sched._apply_initial_liquidsoap_state()

    assert ok
    engine.linein_set_gain.assert_called_once_with(-6.0)


def test_fresh_liquidsoap_without_a_linein_leaves_the_gain_alone(liquidsoap_scheduler):
    sched, engine, _capture = liquidsoap_scheduler
    sched._current_event = None
    engine.reset_mock()

    sched._apply_initial_liquidsoap_state()

    engine.linein_set_gain.assert_not_called()
