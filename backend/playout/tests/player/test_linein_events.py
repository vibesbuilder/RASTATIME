"""
RASTATIME 2026-10-02 - generate_linein_events carries the per-line-in
input gain from the line-in API record into the LineinEvent.
"""

from datetime import datetime, timedelta

from libretime_playout.player.events import LineinEvent
from libretime_playout.player.schedule import generate_linein_events

START = datetime(2026, 10, 2, 18, 0)


def _events_for(linein: dict) -> LineinEvent:
    events: dict = {}
    generate_linein_events(
        events,
        {"id": 7, "starts_at": START, "ends_at": START + timedelta(minutes=30)},
        linein,
        42,
        {"name": "Studio Show"},
    )
    (event,) = events.values()
    return event


def _linein(**extra) -> dict:
    return {
        "id": "uuid-1", "name": "Studio A", "device_id": "dev-1",
        "device_name": "Line (US-16x08)", "channel_mapping": [4, 5], **extra,
    }


def test_input_gain_is_carried_into_the_event():
    assert _events_for(_linein(input_gain_db=6.5)).input_gain_db == 6.5


def test_an_api_without_the_gain_means_unity():
    assert _events_for(_linein()).input_gain_db is None
