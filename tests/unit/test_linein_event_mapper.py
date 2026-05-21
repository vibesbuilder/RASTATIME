"""
T19.2 — LineInEventMapper unit tests.

All tests run without Django (no DB, no ORM).

Test inventory
--------------
Started-state tracking (3):
  1.  ``on_linein_started`` marks the source as active.
  2.  ``is_active`` returns False before start and True after.
  3.  Duplicate ``on_linein_started`` (same ID) is ignored; only one
      pending entry exists.

Stopped-state handling (4):
  4.  ``on_linein_stopped`` for an unknown ID is a silent no-op.
  5.  ``on_linein_stopped`` removes the ID from active set.
  6.  Completed event has correct ``source_type="linein"``.
  7.  URI follows the ``linein://<device_id>`` convention.

PlaybackEvent field correctness (3):
  8.  ``item_id`` is the linein domain UUID.
  9.  ``title`` is the linein name (no artist).
 10.  ``duration_played`` is correct.

Multiple simultaneous line-ins (2):
 11.  Two different line-ins tracked independently.
 12.  Stopping one does not affect the other.

No-op / resilience (2):
 13.  ``write_fn=None`` → silent skip, no exception.
 14.  Exception from write_fn is swallowed.

(14 tests total; no Django required)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from playout.now_playing.linein_mapper import LineInEventMapper
from playout.now_playing.playback_event import PlaybackEvent, PlaybackSourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 4, 30, 14, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1–3  Started-state tracking
# ---------------------------------------------------------------------------


def test_on_linein_started_marks_source_as_active():
    mapper = LineInEventMapper()
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc())
    assert "li-001" in mapper.active_linein_ids()


def test_is_active_false_before_start_true_after():
    mapper = LineInEventMapper()
    assert not mapper.is_active("li-001")
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc")
    assert mapper.is_active("li-001")


def test_duplicate_start_is_ignored():
    """A second on_linein_started for the same ID must not create a second entry."""
    mapper = LineInEventMapper()
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc(minute=0))
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc(minute=5))
    # Still only one active entry
    assert mapper.active_linein_ids().count("li-001") == 1


# ---------------------------------------------------------------------------
# 4–7  Stopped-state handling
# ---------------------------------------------------------------------------


def test_stop_unknown_id_is_noop():
    """on_linein_stopped with an ID that was never started must not raise."""
    mapper = LineInEventMapper(write_fn=lambda e: None)
    mapper.on_linein_stopped("no-such-id")  # must not raise


def test_stop_removes_id_from_active_set():
    mapper = LineInEventMapper()
    mapper.on_linein_started("li-001", "Mic", "dev-xyz")
    mapper.on_linein_stopped("li-001")
    assert not mapper.is_active("li-001")


def test_completed_event_has_linein_source_type():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc(minute=0))
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=5))
    assert written[0].source_type == PlaybackSourceType.LINEIN


def test_completed_event_uri_follows_convention():
    """URI must be ``linein://<device_id>`` so infer_source_type works."""
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc())
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=1))
    assert written[0].uri == "linein://dev-abc"


# ---------------------------------------------------------------------------
# 8–10  PlaybackEvent field correctness
# ---------------------------------------------------------------------------


def test_item_id_is_linein_domain_uuid():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("my-linein-uuid", "Mic", "dev-x", started_at=_utc())
    mapper.on_linein_stopped("my-linein-uuid", ended_at=_utc(second=30))
    assert written[0].item_id == "my-linein-uuid"


def test_title_is_linein_name_and_artist_is_empty():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Drum Kit", "dev-abc", started_at=_utc())
    mapper.on_linein_stopped("li-001", ended_at=_utc(second=10))
    evt = written[0]
    assert evt.title  == "Drum Kit"
    assert evt.artist == ""


def test_duration_played_is_correct():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Mic", "dev-x",
                             started_at=_utc(minute=0, second=0))
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=2, second=30))
    assert written[0].duration_played == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# 11–12  Multiple simultaneous line-ins
# ---------------------------------------------------------------------------


def test_two_lineins_tracked_independently():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Drum Kit", "dev-a", started_at=_utc(minute=0))
    mapper.on_linein_started("li-002", "Interview Mic", "dev-b", started_at=_utc(minute=1))
    assert set(mapper.active_linein_ids()) == {"li-001", "li-002"}


def test_stopping_one_linein_does_not_affect_other():
    written: List[PlaybackEvent] = []
    mapper = LineInEventMapper(write_fn=written.append)
    mapper.on_linein_started("li-001", "Drum Kit", "dev-a", started_at=_utc(minute=0))
    mapper.on_linein_started("li-002", "Mic", "dev-b", started_at=_utc(minute=0))
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=5))
    assert mapper.is_active("li-002")
    assert not mapper.is_active("li-001")
    assert len(written) == 1
    assert written[0].item_id == "li-001"


# ---------------------------------------------------------------------------
# 13–14  No-op / resilience
# ---------------------------------------------------------------------------


def test_no_write_fn_is_silent_noop():
    mapper = LineInEventMapper(write_fn=None)
    mapper.on_linein_started("li-001", "Mic", "dev-x", started_at=_utc())
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=1))
    # No exception means test passes


def test_exception_in_write_fn_is_swallowed():
    def _raiser(evt: PlaybackEvent) -> None:
        raise OSError("disk full")

    mapper = LineInEventMapper(write_fn=_raiser)
    mapper.on_linein_started("li-001", "Mic", "dev-x", started_at=_utc())
    mapper.on_linein_stopped("li-001", ended_at=_utc(minute=1))
    # Must not raise
