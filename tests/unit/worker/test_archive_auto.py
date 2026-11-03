"""
RASTATIME 2026-11-03 - archiving stage 3: the decisions of the automatic run
(backend/rastatime_worker/archive_auto.py) without a database.  The SQL side
(which episodes are candidates at all) is covered by the live probe
C:/Temp/optd/archive_auto_probe.py on a test show.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.rastatime_worker import archive_auto


@pytest.mark.parametrize(
    "file_id, status, rec, slot, expected",
    [
        (None, None, None, 3600, "not in the library"),
        (7, 1, 3600, 3600, "still being imported"),
        (7, 2, 3600, 3600, "import of the recording failed"),
        (7, 0, 1700, 3600, "less than half of the show (28 of 60 min)"),
        (7, 0, None, 900, "less than half of the show (0 of 15 min)"),
    ],
)
def test_recording_problems(file_id, status, rec, slot, expected):
    problems = archive_auto.recording_problems(file_id, status, rec, slot)
    assert len(problems) == 1 and expected in problems[0], problems


@pytest.mark.parametrize("rec", [1800, 3590, 3600, 3620])
def test_recording_usable(rec):
    assert archive_auto.recording_problems(7, 0, rec, 3600) == []


def test_decide():
    due = datetime(2026, 11, 3, 14, 0, tzinfo=UTC)
    assert archive_auto.decide([], due, due) == "queue"
    assert archive_auto.decide(["x"], due, due) == "wait"
    assert archive_auto.decide(["x"], due, due + timedelta(hours=23, minutes=59)) == "wait"
    assert archive_auto.decide(["x"], due, due + timedelta(hours=24)) == "skip"
    # nothing missing any more after a long wait: still archived
    assert archive_auto.decide([], due, due + timedelta(days=2)) == "queue"


def test_warning_rows():
    starts = datetime(2026, 11, 3, 12, 15)  # naive UTC, as cc_show_instances keeps it
    rows = archive_auto.warning_rows(
        [
            {
                "id": 12,
                "instance_id": 30801,
                "status": "skipped",
                "last_error": "the recording is not in the library",
                "show_id": 1292,
                "starts": starts,
                "show_name": "Example Show",
            }
        ]
    )
    assert rows == [
        {
            "severity": "warning",
            "show_id": 1292,
            "show_instance_id": 30801,
            "starts_at": starts.replace(tzinfo=UTC),
            "detail": {
                "job_id": 12,
                "show_name": "Example Show",
                "status": "skipped",
                "reason": "the recording is not in the library",
            },
        }
    ]


def test_delay_is_clamped(monkeypatch):
    for stored, expected in [("30", 30), (None, 30), ("abc", 30), ("-5", 0), ("99999", 1440)]:
        monkeypatch.setattr(archive_auto.archive_jobs, "_pref", lambda key, v=stored: v)
        assert archive_auto.auto_delay_min() == expected
