"""
RASTATIME 2026-11-05 - /api/v2/now-playing reads the schedule from the
database instead of a process-level singleton that production never fills
(ARCHITECTURE 23.91).  Pure helpers are tested with stand-ins; the view's
fail-soft path and the empty-database path need no fixtures.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from datetime import timezone as dt_tz
from types import SimpleNamespace

import pytest

pytest.importorskip("django")
pytest.importorskip("rastatime_api")

from rastatime_api import now_playing as np  # noqa: E402

UTC = UTC


def _row(**kw):
    base = dict(
        starts_at=datetime(2026, 11, 5, 12, 15, tzinfo=UTC),
        ends_at=datetime(2026, 11, 5, 12, 45, tzinfo=UTC),
        length=timedelta(seconds=1800),
        file=None,
        stream=None,
        linein=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_file_item_has_credit_fields_only():
    file = SimpleNamespace(
        id=25613,
        track_title="Example Episode",
        artist_name="Example Host",
        album_title="Podcast",
        genre="Talk",
        date="2026",
        artwork="artwork/abc",
        filepath="D:/stor/secret.mp3",
        md5="deadbeef",
        owner_id=1,
    )
    item = np.item_from_schedule(_row(file=file))
    assert item == {
        "type": "file",
        "id": 25613,
        "title": "Example Episode",
        "artist": "Example Host",
        "album": "Podcast",
        "genre": "Talk",
        "year": "2026",
        "length_seconds": 1800.0,
        "has_artwork": True,
        "starts_at": "2026-11-05T12:15:00+00:00",
        "ends_at": "2026-11-05T12:45:00+00:00",
    }
    assert "filepath" not in item and "md5" not in item and "owner_id" not in item


def test_webstream_and_linein_items():
    ws = np.item_from_schedule(
        _row(stream=SimpleNamespace(id=1, name="BBC World Service News (Live)"))
    )
    assert ws["type"] == "webstream" and ws["title"].startswith("BBC") and ws["artist"] is None
    li = np.item_from_schedule(_row(linein=SimpleNamespace(id=3, name="Studio")))
    assert li["type"] == "linein" and li["title"] == "Studio"
    assert np.item_from_schedule(_row()) is None


def test_show_from_instance_prefers_the_episode_description():
    show = SimpleNamespace(
        id=1172, name="Example Talk", description="series", url="https://x", genre="Talk"
    )
    inst = SimpleNamespace(
        show=show,
        description="episode",
        starts_at=datetime(2026, 11, 5, 12, 15, tzinfo=UTC),
        ends_at=datetime(2026, 11, 5, 12, 45, tzinfo=UTC),
    )
    s = np.show_from_instance(inst)
    assert s["name"] == "Example Talk" and s["description"] == "episode" and s["id"] == 1172
    assert np.show_from_instance(None) is None


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_playout_source_reads_the_dj_flags():
    def opener(req, timeout=None):
        return _Resp(json.dumps({"master_connected": False, "show_connected": True}).encode())

    assert np.playout_source(opener) == "live_dj"

    def opener_master(req, timeout=None):
        return _Resp(json.dumps({"master_connected": True, "show_connected": True}).encode())

    assert np.playout_source(opener_master) == "master_dj"

    def opener_down(req, timeout=None):
        raise OSError("refused")

    assert np.playout_source(opener_down) == "scheduled"


def test_view_answers_idle_when_the_database_is_not_readable(monkeypatch):
    from django.test import RequestFactory

    def boom(now):
        raise RuntimeError("no database")

    monkeypatch.setattr(np, "_snapshot", boom)
    body = json.loads(np.now_playing(RequestFactory().get("/api/v2/now-playing")).content)
    assert body["is_playing"] is False and body["item"] is None and body["started_at"] is None
    assert body["source"] == "scheduled" and body["now"]


@pytest.mark.django_db
def test_view_on_an_empty_schedule_is_idle(monkeypatch):
    from django.test import RequestFactory

    monkeypatch.setattr(np, "playout_source", lambda opener=None: "scheduled")
    body = json.loads(np.now_playing(RequestFactory().get("/api/v2/now-playing")).content)
    assert body["is_playing"] is False and body["item"] is None
    assert set(body) == {"is_playing", "now", "source", "started_at", "item", "show", "next"}
