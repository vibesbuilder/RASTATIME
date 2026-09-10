"""
RASTATIME 2026-09-10 - cue-sheet end markers are written by the item's
owner only, and carry the schedule row id.  Before, a STOP that had been
superseded by its successor still stamped an "end" marker ~30 ms behind
the successor's "start" (start(B) -> end(B) in the sidecar).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from libretime_playout import playout_scheduler as ps
from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from libretime_playout.player.events import EventKind, FileEvent


class _Cues:
    def __init__(self):
        self.marks = []

    def item_start(self, kind, **meta):
        self.marks.append(("start", kind, meta))

    def item_end(self, kind, **meta):
        self.marks.append(("end", kind, meta))


def _file_event(start: datetime, row_id: int) -> FileEvent:
    return FileEvent(
        type=EventKind.FILE, start=start, end=start + timedelta(minutes=3),
        row_id=row_id, id=row_id, uri="C:/media/a.mp3", show_name="night",
        cue_in=0.0, cue_out=180.0, track_title="t", artist_name="a",
        replay_gain=None, fade_in=0.0, fade_out=0.0, mime="audio/mpeg",
        filesize=1000,
    )


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setattr(ps.liquidsoap_health, "liquidsoap_process_info", lambda: [])
    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.get_state.return_value = PlayoutState.STOPPED
    engine.recording_stop.return_value = None
    engine.liquidsoap_uptime_seconds.return_value = 1000.0
    s = ps.PlayoutScheduler(
        engine=engine, api_client=MagicMock(), streaming_handled_externally=True,
    )
    s.reset_gates = MagicMock()
    cues = _Cues()
    s.set_cue_writer(cues)
    return s, engine, cues


def test_owner_stop_writes_the_end_marker_with_the_item_id(sched):
    s, engine, cues = sched
    event = _file_event(datetime(2026, 9, 10, 10, 0, 0), row_id=4711)
    s._playing_key = "A"
    s._current_event = event
    s._on_stop("A")
    assert cues.marks == [("end", "track", {"item": 4711})]
    assert s._playing_key is None
    assert s._current_event is None


def test_stop_of_a_superseded_key_writes_nothing(sched):
    s, engine, cues = sched
    s._playing_key = "B"                       # the successor already owns the spotlight
    s._current_event = _file_event(datetime(2026, 9, 10, 10, 3, 0), row_id=4712)
    s._on_stop("A")
    assert cues.marks == []
    assert s._playing_key == "B"               # untouched


def test_end_marker_is_written_after_the_ownership_re_check(sched):
    """The re-check sits between the top check and the marker: a
    successor that grabs the key in between must suppress our marker."""
    s, engine, cues = sched
    event = _file_event(datetime(2026, 9, 10, 10, 0, 0), row_id=4711)
    s._current_event = event

    # Simulate the successor taking over while _on_stop runs: the first
    # read of _playing_key (the top check) sees "A", every later read
    # (the re-check) sees "B".  A data descriptor on the class shadows
    # the instance attribute.
    reads = {"n": 0}

    class _Key:
        def __get__(self, obj, objtype=None):
            reads["n"] += 1
            return "A" if reads["n"] == 1 else "B"

        def __set__(self, obj, value):
            obj.__dict__["_playing_key_shadow"] = value

    cls = type(s)
    try:
        setattr(cls, "_playing_key", _Key())
        s._on_stop("A")
    finally:
        delattr(cls, "_playing_key")
    assert reads["n"] >= 2                      # the re-check did run
    assert cues.marks == []                     # superseded during teardown -> no end marker
