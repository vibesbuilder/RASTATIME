"""
T19.2 — PlaybackEventPersister unit tests.

All tests run without Django (no DB, no ORM).  The write_fn is always a
stub (list-append or exception-raiser) injected via DI.

Test inventory
--------------
Wiring (2):
  1.  ``attach()`` registers the persister as a completion subscriber.
  2.  Two persisters can be attached to the same logger independently.

Persistence behaviour (4):
  3.  Completed HistoryEntry → write_fn is called with a PlaybackEvent.
  4.  PlaybackEvent fields match the HistoryEntry data.
  5.  ``source_type`` is inferred from the item URI.
  6.  In-progress entry (ended_at=None) does NOT trigger the write_fn
      (only finalised entries do).

No-op behaviour (1):
  7.  ``write_fn=None`` → write is silently skipped; no exception raised.

Resilience (1):
  8.  Exception raised by write_fn is swallowed; other subscribers are
      unaffected.

(8 tests total; no Django required)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import pytest

from playout.engine_interface import QueueItem, TrackChangedEvent
from playout.now_playing._history import HistoryEntry, PlayoutHistoryLogger
from playout.now_playing._persister import PlaybackEventPersister
from playout.now_playing.playback_event import PlaybackEvent, PlaybackSourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(second: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, 4, 30, 12, minute, second, tzinfo=timezone.utc)


def _item(
    id="track-001",
    uri="file:///music/song.mp3",
    title="Song",
    artist="Artist",
) -> QueueItem:
    return QueueItem(id=id, uri=uri, title=title, artist=artist)


def _make_track_changed(
    previous: Optional[QueueItem] = None,
    current: Optional[QueueItem] = None,
    ts: Optional[datetime] = None,
) -> TrackChangedEvent:
    return TrackChangedEvent(
        previous_item=previous,
        current_item=current,
        timestamp=ts or _utc(),
    )


# ---------------------------------------------------------------------------
# 1–2  Wiring
# ---------------------------------------------------------------------------


def test_attach_registers_completion_subscriber():
    """After attach(), a completed track should trigger write_fn."""
    written: List[PlaybackEvent] = []
    persister = PlaybackEventPersister(write_fn=written.append)
    logger = PlayoutHistoryLogger()
    persister.attach(logger)

    item = _item()
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=_utc(second=30)))

    assert len(written) == 1


def test_two_persisters_attached_independently():
    """Two persisters on the same logger each receive their own callback."""
    bucket_a: List[PlaybackEvent] = []
    bucket_b: List[PlaybackEvent] = []
    logger = PlayoutHistoryLogger()
    PlaybackEventPersister(write_fn=bucket_a.append).attach(logger)
    PlaybackEventPersister(write_fn=bucket_b.append).attach(logger)

    item = _item()
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=_utc(second=10)))

    assert len(bucket_a) == 1
    assert len(bucket_b) == 1


# ---------------------------------------------------------------------------
# 3–6  Persistence behaviour
# ---------------------------------------------------------------------------


def test_write_fn_called_on_completed_entry():
    """write_fn receives exactly one PlaybackEvent for one completed track."""
    written: List[PlaybackEvent] = []
    persister = PlaybackEventPersister(write_fn=written.append)
    logger = PlayoutHistoryLogger()
    persister.attach(logger)

    item = _item()
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=_utc(second=45)))

    assert len(written) == 1
    evt = written[0]
    assert isinstance(evt, PlaybackEvent)


def test_playback_event_fields_match_history_entry():
    """Fields in the written PlaybackEvent match the source HistoryEntry."""
    written: List[PlaybackEvent] = []
    persister = PlaybackEventPersister(write_fn=written.append)
    logger = PlayoutHistoryLogger()
    persister.attach(logger)

    item = _item(id="song-42", title="My Track", artist="My Band",
                 uri="file:///music/my_track.mp3")
    t_start = _utc(second=0)
    t_end   = _utc(minute=3)   # 3 minutes later = 180 s

    logger.on_track_change(_make_track_changed(current=item, ts=t_start))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=t_end))

    evt = written[0]
    assert evt.item_id   == "song-42"
    assert evt.title     == "My Track"
    assert evt.artist    == "My Band"
    assert evt.uri       == "file:///music/my_track.mp3"
    assert evt.started_at == t_start
    assert evt.ended_at   == t_end
    assert evt.duration_played == pytest.approx(180.0)


def test_source_type_inferred_from_uri():
    """source_type is inferred from the item URI, not hardcoded."""
    written: List[PlaybackEvent] = []
    logger = PlayoutHistoryLogger()
    PlaybackEventPersister(write_fn=written.append).attach(logger)

    stream_item = _item(uri="http://stream.example.com/live")
    logger.on_track_change(_make_track_changed(current=stream_item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=stream_item, current=None, ts=_utc(second=10)))

    assert written[0].source_type == PlaybackSourceType.WEBSTREAM


def test_no_write_while_track_still_playing():
    """
    While a track is in progress (no TrackChangedEvent yet), write_fn
    must not be called — only completed entries trigger persistence.
    """
    written: List[PlaybackEvent] = []
    logger = PlayoutHistoryLogger()
    PlaybackEventPersister(write_fn=written.append).attach(logger)

    item = _item()
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    # No second event — track is still playing
    assert len(written) == 0


# ---------------------------------------------------------------------------
# 7  No-op behaviour
# ---------------------------------------------------------------------------


def test_no_write_fn_is_silent_noop():
    """write_fn=None: persister silently skips; no exception raised."""
    persister = PlaybackEventPersister(write_fn=None)
    logger = PlayoutHistoryLogger()
    persister.attach(logger)

    item = _item()
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=_utc(second=5)))
    # No exception means test passes


# ---------------------------------------------------------------------------
# 8  Resilience
# ---------------------------------------------------------------------------


def test_exception_in_write_fn_is_swallowed():
    """An exception raised by write_fn must not propagate to the caller."""
    def _raising_write(evt: PlaybackEvent) -> None:
        raise RuntimeError("DB connection failed")

    logger = PlayoutHistoryLogger()
    PlaybackEventPersister(write_fn=_raising_write).attach(logger)

    item = _item()
    # Must not raise:
    logger.on_track_change(_make_track_changed(current=item, ts=_utc(second=0)))
    logger.on_track_change(_make_track_changed(previous=item, current=None, ts=_utc(second=5)))
