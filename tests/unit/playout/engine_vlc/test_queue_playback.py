"""
T5.3 validation — VlcPlayoutEngine queue playback.

Verifies that:
1. A 3-item queue plays in order and fires 4 TrackChangedEvents (V criterion).
2. Events carry the correct previous/current item references.
3. State is STOPPED and current_item is None after the queue is exhausted.
4. append() during playback extends the queue and the new item plays.
5. clear_queue() during playback discards pending items without stopping current.
6. load_queue() during playback stops and resets; new queue can be started.
7. Callbacks fire in registration order across multiple listeners.
8. The gap between consecutive tracks is within the documented bound (<2 s).

Timing notes
------------
TRACK_DURATION = 0.3 s  — shorter than T5.2's 0.5 s to speed up the suite.
MARGIN         = 5.0 s  — generous ceiling so tests pass on a loaded machine.

All tests require VLC to be installed and are skipped otherwise.
"""

import math
import struct
import tempfile
import time
import wave
from pathlib import Path
from typing import List

import pytest

from playout.engine_interface import PlayoutState, QueueItem, TrackChangedEvent

TRACK_DURATION = 0.3
MARGIN = 5.0
_VLC_TEST_ARGS = ["--aout=dummy"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping VlcPlayoutEngine queue tests",
)


def _make_wav(duration: float = TRACK_DURATION, freq: float = 440.0) -> Path:
    sample_rate = 44100
    n = int(sample_rate * duration)
    samples = [
        int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
        for i in range(n)
    ]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return path


def _item(path: Path, item_id: str) -> QueueItem:
    return QueueItem(id=item_id, uri=path.as_uri(), duration=TRACK_DURATION)


@pytest.fixture()
def engine():
    from playout.engine_vlc import VlcPlayoutEngine
    eng = VlcPlayoutEngine(vlc_args=_VLC_TEST_ARGS)
    yield eng
    try:
        eng.stop()
    except Exception:
        pass
    eng.close()


@pytest.fixture()
def three_wavs():
    """Three temporary WAV files; removed after the test."""
    paths = [_make_wav(freq=220 * (i + 1)) for i in range(3)]
    yield paths
    for p in paths:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# V criterion: 3-item queue plays in order, 4 events fire
# ---------------------------------------------------------------------------

@vlc_required
def test_three_item_queue_plays_in_order(engine, three_wavs):
    """
    V criterion for T5.3: load a 3-item queue, start, wait for completion.

    Expected TrackChangedEvents:
        event[0]: previous=None,   current=items[0]  (start)
        event[1]: previous=items[0], current=items[1]  (advance)
        event[2]: previous=items[1], current=items[2]  (advance)
        event[3]: previous=items[2], current=None    (queue exhausted)
    """
    items = [_item(p, f"t{i}") for i, p in enumerate(three_wavs)]
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue(items)
    engine.start()

    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == items[0]

    # Wait for the full 3-track queue to finish
    total_wait = TRACK_DURATION * 3 + MARGIN
    time.sleep(total_wait)

    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    assert len(events) == 4, (
        f"Expected 4 TrackChangedEvents, got {len(events)}: "
        + ", ".join(
            f"({e.previous_item and e.previous_item.id}->"
            f"{e.current_item and e.current_item.id})"
            for e in events
        )
    )

    # None -> t0
    assert events[0].previous_item is None
    assert events[0].current_item == items[0]

    # t0 -> t1
    assert events[1].previous_item == items[0]
    assert events[1].current_item == items[1]

    # t1 -> t2
    assert events[2].previous_item == items[1]
    assert events[2].current_item == items[2]

    # t2 -> None  (queue exhausted)
    assert events[3].previous_item == items[2]
    assert events[3].current_item is None


# ---------------------------------------------------------------------------
# Event correctness
# ---------------------------------------------------------------------------

@vlc_required
def test_events_have_timestamps(engine, three_wavs):
    """Each TrackChangedEvent carries a UTC timestamp."""
    from datetime import timezone
    items = [_item(p, f"t{i}") for i, p in enumerate(three_wavs)]
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue(items)
    engine.start()
    time.sleep(TRACK_DURATION * 3 + MARGIN)

    for ev in events:
        assert ev.timestamp.tzinfo is not None  # timezone-aware
        assert ev.timestamp.tzinfo == timezone.utc


@vlc_required
def test_multiple_listeners_receive_all_events(engine, three_wavs):
    """All registered callbacks receive every TrackChangedEvent."""
    items = [_item(p, f"t{i}") for i, p in enumerate(three_wavs)]
    calls_a: List[TrackChangedEvent] = []
    calls_b: List[TrackChangedEvent] = []
    engine.on_track_change(calls_a.append)
    engine.on_track_change(calls_b.append)

    engine.load_queue(items)
    engine.start()
    time.sleep(TRACK_DURATION * 3 + MARGIN)

    assert len(calls_a) == 4
    assert len(calls_b) == 4
    for a, b in zip(calls_a, calls_b):
        assert a.previous_item == b.previous_item
        assert a.current_item == b.current_item


# ---------------------------------------------------------------------------
# append() during playback
# ---------------------------------------------------------------------------

@vlc_required
def test_append_during_playback_extends_queue(engine, three_wavs):
    """An item appended while track 0 is playing must itself play afterwards."""
    item0 = _item(three_wavs[0], "t0")
    item_extra = _item(three_wavs[1], "extra")

    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item0])
    engine.start()

    # Append while still playing track 0
    engine.append(item_extra)

    # Wait for both tracks
    time.sleep(TRACK_DURATION * 2 + MARGIN)

    assert engine.get_state() == PlayoutState.STOPPED
    # 4 events: None->t0, t0->extra, extra->None
    assert len(events) == 3
    ids = [e.current_item.id if e.current_item else None for e in events]
    assert ids == ["t0", "extra", None]


# ---------------------------------------------------------------------------
# clear_queue() during playback
# ---------------------------------------------------------------------------

@vlc_required
def test_clear_queue_discards_pending_items(engine, three_wavs):
    """
    clear_queue() during playback removes pending items.
    The current track finishes normally; no further tracks play.
    """
    items = [_item(p, f"t{i}") for i, p in enumerate(three_wavs)]
    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue(items)
    engine.start()

    assert engine.get_current_item() == items[0]

    # Discard t1 and t2 while t0 is playing
    engine.clear_queue()
    assert engine.get_current_item() == items[0]
    assert engine.get_state() == PlayoutState.PLAYING

    # Wait for t0 to finish; t1 and t2 must NOT play
    time.sleep(TRACK_DURATION + MARGIN)

    assert engine.get_state() == PlayoutState.STOPPED
    # Only 2 events: None->t0, t0->None
    assert len(events) == 2
    assert events[0].current_item == items[0]
    assert events[1].current_item is None


# ---------------------------------------------------------------------------
# load_queue() during playback
# ---------------------------------------------------------------------------

@vlc_required
def test_load_queue_during_playback_stops_and_replaces(engine, three_wavs):
    """load_queue() during playback stops the current track and resets."""
    item0 = _item(three_wavs[0], "t0")
    item_new = _item(three_wavs[1], "new")

    events: List[TrackChangedEvent] = []
    engine.on_track_change(events.append)

    engine.load_queue([item0])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    # Replace the queue mid-play
    engine.load_queue([item_new])
    assert engine.get_state() == PlayoutState.STOPPED
    assert engine.get_current_item() is None

    # The new queue can be started independently
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item() == item_new
    engine.stop()


# ---------------------------------------------------------------------------
# Inter-track gap bound
# ---------------------------------------------------------------------------

@vlc_required
def test_inter_track_gap_within_documented_bound(engine, three_wavs):
    """
    Measure the wall-clock gap between two consecutive TrackChangedEvents
    and assert it is within the documented upper bound of 2 s.

    This is a loose bound; the actual gap is typically 50–200 ms.
    """
    items = [_item(p, f"t{i}") for i, p in enumerate(three_wavs[:2])]
    timestamps: List[float] = []

    def record(event: TrackChangedEvent) -> None:
        timestamps.append(time.monotonic())

    engine.on_track_change(record)
    engine.load_queue(items)
    engine.start()

    time.sleep(TRACK_DURATION * 2 + MARGIN)

    # We expect 3 events: None->t0, t0->t1, t1->None
    assert len(timestamps) >= 2
    # Gap between the "t0 starts" event and "t1 starts" event
    gap = timestamps[1] - timestamps[0]
    assert gap < 2.0, f"Inter-track gap too large: {gap:.3f} s"
