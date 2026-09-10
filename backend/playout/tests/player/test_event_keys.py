"""
RASTATIME 2026-09-10 - event keys with identity: ``<timestamp>#<tag>``.
"""
from __future__ import annotations

from datetime import datetime

from libretime_playout.player.events import (
    EVENT_KEY_SEPARATOR,
    datetime_to_event_key,
    event_key_to_datetime,
    make_event_key,
)
from libretime_playout.player.schedule import insert_event


def test_make_event_key_joins_timestamp_and_tag():
    key = make_event_key(datetime(2026, 9, 10, 10, 0, 0), "file-4711")
    assert key == "2026-09-10-10-00-00#file-4711"
    assert EVENT_KEY_SEPARATOR == "#"


def test_keys_sort_chronologically_and_deterministically():
    keys = [
        make_event_key(datetime(2026, 9, 10, 10, 0, 0), "ws-play-5"),
        make_event_key(datetime(2026, 9, 10, 9, 59, 59), "file-9"),
        make_event_key(datetime(2026, 9, 10, 10, 0, 0), "file-6"),
        make_event_key(datetime(2026, 9, 10, 10, 0, 0), "ws-buffer-5"),
    ]
    assert sorted(keys) == [
        "2026-09-10-09-59-59#file-9",
        "2026-09-10-10-00-00#file-6",
        "2026-09-10-10-00-00#ws-buffer-5",
        "2026-09-10-10-00-00#ws-play-5",
    ]


def test_event_key_to_datetime_ignores_tag_and_legacy_suffix():
    stamp = datetime(2026, 9, 10, 10, 0, 0)
    assert event_key_to_datetime("2026-09-10-10-00-00#file-4711") == stamp
    assert event_key_to_datetime("2026-09-10-10-00-00_0") == stamp
    assert event_key_to_datetime("2026-09-10-10-00-00") == stamp
    assert datetime_to_event_key(stamp) == "2026-09-10-10-00-00"


def test_insert_event_keeps_the_suffix_fallback_and_dedupes():
    events = {}
    insert_event(events, "k#file-1", "a")
    insert_event(events, "k#file-1", "a")            # identical -> ignored
    insert_event(events, "k#file-1", "b")            # same key, other event -> fallback
    assert events == {"k#file-1": "a", "k#file-1_0": "b"}
