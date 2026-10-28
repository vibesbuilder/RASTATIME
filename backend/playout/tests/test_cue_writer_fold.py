"""
RASTATIME 2026-10-28 - cue sidecars across the repeated hour of the autumn
clock change: the wall clock shows 02:xx twice (CEST, then CET); each real
hour gets its own sidecar, like the recorder's audio files.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from libretime_playout import cue_writer as cw_mod
from libretime_playout.cue_writer import CueWriter

CEST = timezone(timedelta(hours=2))
CET = timezone(timedelta(hours=1))
DAY = "2026-10-25"
BASE = f"{DAY} 02-00"


def _cw(tmp_path, now):
    cfg = {"enabled": True, "folder": str(tmp_path), "format": "mp3"}
    return CueWriter(lambda: cfg, now_fn=lambda: now)


def _read(tmp_path, name):
    return json.loads((tmp_path / DAY / name).read_text(encoding="utf-8"))


def test_first_pass_writes_the_primary_sidecar_with_utc_fields(tmp_path):
    _cw(tmp_path, datetime(2026, 10, 25, 2, 10, 0, tzinfo=CEST)).item_start("track", show="Night", title="a")
    data = _read(tmp_path, f"{BASE}.cues.json")
    assert data["hour_start"] == "2026-10-25T02:00:00"
    assert data["hour_start_utc"] == "2026-10-25T00:00:00+00:00"
    assert data["utc_offset"] == "+02:00"
    assert "sidecar_part" not in data
    assert data["marks"][-1]["t"] == 600.0


def test_second_pass_goes_to_its_own_sidecar(tmp_path):
    _cw(tmp_path, datetime(2026, 10, 25, 2, 10, 0, tzinfo=CEST)).item_start("track", show="Night", title="a", item=1)
    _cw(tmp_path, datetime(2026, 10, 25, 2, 55, 0, tzinfo=CEST)).item_start("track", show="Night", title="b", item=2)
    # clocks went back: 02:05 CET is 01:05 UTC, a new real hour
    _cw(tmp_path, datetime(2026, 10, 25, 2, 5, 0, tzinfo=CET)).item_start("track", show="Night", title="c", item=3)
    _cw(tmp_path, datetime(2026, 10, 25, 2, 30, 0, tzinfo=CET)).item_end("track", item=3)

    first = _read(tmp_path, f"{BASE}.cues.json")
    second = _read(tmp_path, f"{BASE}.2.cues.json")
    assert [m.get("item") for m in first["marks"] if m["kind"] == "track"] == [1, 2]
    assert [m.get("item") for m in second["marks"] if m["kind"] == "track"] == [3, 3]
    assert [m["t"] for m in second["marks"] if m["kind"] == "track"] == [300.0, 1800.0]
    assert second["hour_start"] == "2026-10-25T02:00:00"
    assert second["hour_start_utc"] == "2026-10-25T01:00:00+00:00"
    assert second["utc_offset"] == "+01:00"
    assert second["sidecar_part"] == 2
    assert second["recording"] == f"{BASE}.2.mp3"
    assert first["hour_start_utc"] == "2026-10-25T00:00:00+00:00"
    assert not (tmp_path / DAY / f"{BASE}.2.cues.json.tmp").exists()


def test_parts_are_split_between_the_two_sidecars(tmp_path, monkeypatch):
    day = tmp_path / DAY
    day.mkdir()
    (day / f"{BASE}.mp3").write_bytes(b"x")
    (day / f"{BASE}.2.mp3").write_bytes(b"x")
    created = {
        f"{BASE}.mp3": datetime(2026, 10, 25, 0, 0, 0, tzinfo=timezone.utc),     # 02:00 CEST
        f"{BASE}.2.mp3": datetime(2026, 10, 25, 1, 0, 0, tzinfo=timezone.utc),   # 02:00 CET
    }
    monkeypatch.setattr(CueWriter, "_created_utc", staticmethod(lambda p: created.get(Path(p).name)))

    _cw(tmp_path, datetime(2026, 10, 25, 2, 10, 0, tzinfo=CEST)).item_start("track", show="N", title="a")
    _cw(tmp_path, datetime(2026, 10, 25, 2, 10, 0, tzinfo=CET)).item_start("track", show="N", title="b")
    # a late mark of the first pass is written after the sibling exists
    _cw(tmp_path, datetime(2026, 10, 25, 2, 59, 0, tzinfo=CEST)).item_end("track")

    first = _read(tmp_path, f"{BASE}.cues.json")
    second = _read(tmp_path, f"{BASE}.2.cues.json")
    assert [p["file"] for p in first["parts"]] == [f"{BASE}.mp3"]
    assert [p["file"] for p in second["parts"]] == [f"{BASE}.2.mp3"]
    assert second["recording"] == f"{BASE}.2.mp3"


def test_restart_inside_a_normal_hour_keeps_one_sidecar(tmp_path):
    day = tmp_path / "2026-06-05"
    day.mkdir()
    (day / "2026-06-05 14-00.mp3").write_bytes(b"x")
    (day / "2026-06-05 14-00.2.mp3").write_bytes(b"x")
    tz = timezone(timedelta(hours=2))
    _cw(tmp_path, datetime(2026, 6, 5, 14, 10, 0, tzinfo=tz)).item_start("track", show="A", title="a")
    _cw(tmp_path, datetime(2026, 6, 5, 14, 40, 0, tzinfo=tz)).item_start("track", show="A", title="b")
    data = json.loads((day / "2026-06-05 14-00.cues.json").read_text(encoding="utf-8"))
    assert len(data["parts"]) == 2
    assert not (day / "2026-06-05 14-00.2.cues.json").exists()


def test_old_sidecar_without_utc_fields_is_continued(tmp_path):
    day = tmp_path / DAY
    day.mkdir()
    (day / f"{BASE}.cues.json").write_text(json.dumps({
        "version": 1, "recording": f"{BASE}.mp3", "hour_start": "2026-10-25T02:00:00",
        "marks": [{"t": 1.0, "kind": "track", "event": "start"}],
    }), encoding="utf-8")
    _cw(tmp_path, datetime(2026, 10, 25, 2, 20, 0, tzinfo=CEST)).item_end("track")
    data = _read(tmp_path, f"{BASE}.cues.json")
    assert len(data["marks"]) == 2
    assert data["hour_start_utc"] == "2026-10-25T00:00:00+00:00"
    assert not (day / f"{BASE}.2.cues.json").exists()


def test_naive_now_still_works(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 10, 30)).item_start("track", show="A", title="a")
    data = json.loads((tmp_path / "2026-06-05" / "2026-06-05 14-00.cues.json").read_text(encoding="utf-8"))
    assert data["hour_start"] == "2026-06-05T14:00:00"
    assert data["marks"][-1]["t"] == 630.0
    assert "hour_start_utc" in data and "utc_offset" in data


def test_offset_text():
    assert cw_mod._offset_text(timedelta(hours=2)) == "+02:00"
    assert cw_mod._offset_text(timedelta(hours=-5, minutes=-30)) == "-05:30"
    assert cw_mod._offset_text(timedelta(0)) == "+00:00"
