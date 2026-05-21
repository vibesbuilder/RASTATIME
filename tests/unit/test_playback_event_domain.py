"""
T19.1 — PlaybackEvent domain model tests.

Verify the pure-Python domain layer for normalized playback events.
No Django, no database, no I/O — all tests run in the root venv.

Test inventory
--------------
infer_source_type (5):
  1.  Empty URI → ``unknown``.
  2.  ``file://`` URI → ``file``.
  3.  Bare path with slash → ``file``.
  4.  ``http://`` URI → ``webstream``.
  5.  ``linein://`` URI → ``linein``.

PlaybackEvent construction (4):
  6.  All required fields accepted; optional defaults applied.
  7.  ``duration_played`` returns None while ``ended_at`` is None.
  8.  ``duration_played`` returns correct seconds when ``ended_at`` is set.
  9.  ``is_completed`` is False / True based on ``ended_at``.

PlaybackEvent.to_dict (3):
 10.  Keys present: event_id, source_type, item_id, title, artist, uri,
      started_at, ended_at, duration_played.
 11.  ``started_at`` is ISO-8601 string.
 12.  ``ended_at`` is None when not yet completed.

PlaybackEvent.from_history_entry (4):
 13.  Factory builds a PlaybackEvent from a HistoryEntry.
 14.  ``event_id`` override is respected.
 15.  ``source_type`` is inferred from the item URI.
 16.  ``duration_played`` is correct for a completed entry.

PlaybackSourceType (2):
 17.  ``is_valid`` returns True for all defined constants.
 18.  ``is_valid`` returns False for unknown strings.

(18 tests total; all run without Django)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytest

from playout.now_playing.playback_event import (
    PlaybackEvent,
    PlaybackSourceType,
    infer_source_type,
)
from playout.engine_interface import QueueItem


# ---------------------------------------------------------------------------
# Helpers — lightweight stubs that mirror HistoryEntry without importing it
# ---------------------------------------------------------------------------

def _utc(year=2026, month=4, day=29, hour=12, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@dataclass
class _FakeHistoryEntry:
    """Minimal stand-in for playout.now_playing._history.HistoryEntry."""
    item: QueueItem
    started_at: datetime
    ended_at: Optional[datetime] = None


def _make_item(
    id="track-001",
    uri="file:///music/song.mp3",
    title="Test Track",
    artist="Test Artist",
    duration: Optional[float] = 180.0,
    metadata: Optional[dict] = None,
) -> QueueItem:
    return QueueItem(
        id=id,
        uri=uri,
        title=title,
        artist=artist,
        duration=duration,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1–5  infer_source_type
# ---------------------------------------------------------------------------


def test_infer_source_type_empty_uri():
    assert infer_source_type("") == PlaybackSourceType.UNKNOWN


def test_infer_source_type_file_scheme():
    assert infer_source_type("file:///music/song.mp3") == PlaybackSourceType.FILE


def test_infer_source_type_bare_path():
    assert infer_source_type("/var/music/song.mp3") == PlaybackSourceType.FILE


def test_infer_source_type_http_stream():
    assert infer_source_type("http://stream.example.com:8000/live") == PlaybackSourceType.WEBSTREAM


def test_infer_source_type_linein_scheme():
    assert infer_source_type("linein://device-abc") == PlaybackSourceType.LINEIN


# ---------------------------------------------------------------------------
# 6–9  PlaybackEvent construction
# ---------------------------------------------------------------------------


def test_playback_event_construction_defaults():
    """All required fields accepted; metadata defaults to empty dict."""
    event = PlaybackEvent(
        event_id="evt-001",
        source_type=PlaybackSourceType.FILE,
        item_id="track-001",
        title="My Song",
        artist="My Artist",
        uri="file:///music/my_song.mp3",
        started_at=_utc(),
    )
    assert event.event_id == "evt-001"
    assert event.source_type == PlaybackSourceType.FILE
    assert event.ended_at is None
    assert event.metadata == {}


def test_duration_played_is_none_while_in_progress():
    event = PlaybackEvent(
        event_id="evt-002",
        source_type=PlaybackSourceType.FILE,
        item_id="t",
        title="",
        artist="",
        uri="file:///x.mp3",
        started_at=_utc(second=0),
        ended_at=None,
    )
    assert event.duration_played is None


def test_duration_played_correct_when_ended():
    event = PlaybackEvent(
        event_id="evt-003",
        source_type=PlaybackSourceType.FILE,
        item_id="t",
        title="",
        artist="",
        uri="file:///x.mp3",
        started_at=_utc(minute=0, second=0),
        ended_at=_utc(minute=1, second=30),  # 90 seconds later
    )
    assert event.duration_played == pytest.approx(90.0)


def test_is_completed_false_and_true():
    base = dict(
        event_id="e", source_type=PlaybackSourceType.FILE,
        item_id="t", title="", artist="", uri="file:///x.mp3",
        started_at=_utc(),
    )
    in_progress = PlaybackEvent(**base, ended_at=None)
    completed   = PlaybackEvent(**base, ended_at=_utc(second=30))
    assert not in_progress.is_completed
    assert completed.is_completed


# ---------------------------------------------------------------------------
# 10–12  PlaybackEvent.to_dict
# ---------------------------------------------------------------------------


_EXPECTED_DICT_KEYS = frozenset({
    "event_id", "source_type", "item_id", "title", "artist",
    "uri", "started_at", "ended_at", "duration_played",
})


def test_to_dict_has_all_keys():
    event = PlaybackEvent(
        event_id="e", source_type=PlaybackSourceType.WEBSTREAM,
        item_id="s", title="Stream", artist="",
        uri="http://example.com/live",
        started_at=_utc(),
    )
    assert set(event.to_dict().keys()) == _EXPECTED_DICT_KEYS


def test_to_dict_started_at_is_iso_string():
    started = _utc()
    event = PlaybackEvent(
        event_id="e", source_type=PlaybackSourceType.FILE,
        item_id="t", title="", artist="", uri="file:///x.mp3",
        started_at=started,
    )
    d = event.to_dict()
    assert d["started_at"] == started.isoformat()
    assert isinstance(d["started_at"], str)


def test_to_dict_ended_at_is_none_in_progress():
    event = PlaybackEvent(
        event_id="e", source_type=PlaybackSourceType.FILE,
        item_id="t", title="", artist="", uri="file:///x.mp3",
        started_at=_utc(), ended_at=None,
    )
    assert event.to_dict()["ended_at"] is None


# ---------------------------------------------------------------------------
# 13–16  PlaybackEvent.from_history_entry
# ---------------------------------------------------------------------------


def test_from_history_entry_builds_event():
    """Factory builds a well-formed PlaybackEvent from a HistoryEntry stub."""
    item = _make_item()
    entry = _FakeHistoryEntry(item=item, started_at=_utc())
    event = PlaybackEvent.from_history_entry(entry)

    assert event.item_id == item.id
    assert event.title == item.title
    assert event.artist == item.artist
    assert event.uri == item.uri
    assert event.started_at == entry.started_at
    assert event.ended_at is None
    assert isinstance(event.event_id, str) and len(event.event_id) == 36  # UUID4


def test_from_history_entry_event_id_override():
    """Explicit event_id kwarg is respected and used verbatim."""
    item = _make_item()
    entry = _FakeHistoryEntry(item=item, started_at=_utc())
    event = PlaybackEvent.from_history_entry(entry, event_id="fixed-id-001")
    assert event.event_id == "fixed-id-001"


def test_from_history_entry_source_type_inferred():
    """source_type is inferred from the item URI, not set manually."""
    file_item   = _make_item(uri="file:///music/song.mp3")
    stream_item = _make_item(uri="http://stream.example.com/live")
    linein_item = _make_item(uri="linein://mic-input")

    assert PlaybackEvent.from_history_entry(
        _FakeHistoryEntry(file_item, _utc())
    ).source_type == PlaybackSourceType.FILE

    assert PlaybackEvent.from_history_entry(
        _FakeHistoryEntry(stream_item, _utc())
    ).source_type == PlaybackSourceType.WEBSTREAM

    assert PlaybackEvent.from_history_entry(
        _FakeHistoryEntry(linein_item, _utc())
    ).source_type == PlaybackSourceType.LINEIN


def test_from_history_entry_duration_correct_for_completed():
    """duration_played is correct when ended_at is set."""
    item = _make_item()
    entry = _FakeHistoryEntry(
        item=item,
        started_at=_utc(minute=0, second=0),
        ended_at=_utc(minute=2, second=0),  # 120 seconds later
    )
    event = PlaybackEvent.from_history_entry(entry)
    assert event.duration_played == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# 17–18  PlaybackSourceType helpers
# ---------------------------------------------------------------------------


def test_source_type_is_valid_for_all_constants():
    for val in (
        PlaybackSourceType.FILE,
        PlaybackSourceType.WEBSTREAM,
        PlaybackSourceType.LINEIN,
        PlaybackSourceType.LIVE,
        PlaybackSourceType.UNKNOWN,
    ):
        assert PlaybackSourceType.is_valid(val), f"is_valid({val!r}) should be True"


def test_source_type_is_valid_rejects_unknown_strings():
    for val in ("", "mp3", "radio", "FILE"):
        assert not PlaybackSourceType.is_valid(val), (
            f"is_valid({val!r}) should be False"
        )
