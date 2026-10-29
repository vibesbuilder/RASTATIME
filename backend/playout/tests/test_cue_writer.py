"""
RASTATIME 2026-06-05 — Unit tests for cue_writer (Record-per-Hour stage 5):
the per-hour cue sidecars next to the 24/7 archive recordings.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rastatime_playout.cue_writer import CueWriter


def _cw(tmp_path, now, *, enabled=True, fmt="mp3"):
    cfg = {"enabled": enabled, "folder": str(tmp_path), "format": fmt}
    return CueWriter(lambda: cfg, now_fn=lambda: now)


def _read(tmp_path, base="2026-06-05 14-00", day="2026-06-05"):
    return json.loads(
        (tmp_path / day / f"{base}.cues.json").read_text(encoding="utf-8")
    )


def test_item_start_writes_sidecar(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 10, 30)).item_start(
        "track", show="Morning", title="Song A", artist="Artist A"
    )
    data = _read(tmp_path)
    assert data["version"] == 1
    assert data["recording"] == "2026-06-05 14-00.mp3"
    assert data["hour_start"] == "2026-06-05T14:00:00"
    track = [m for m in data["marks"] if m["kind"] == "track"][0]
    assert track["event"] == "start"
    assert track["t"] == 630.0
    assert track["title"] == "Song A"
    assert track["artist"] == "Artist A"
    assert track["show"] == "Morning"


def test_first_item_emits_derived_show_start(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0)).item_start(
        "track", show="Morning", title="t"
    )
    marks = _read(tmp_path)["marks"]
    assert {"t": 0.0, "kind": "show", "event": "start", "name": "Morning"} in marks


def test_show_change_emits_end_then_start(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0))
    cw.item_start("track", show="ShowA", title="t1")
    cw.item_start("track", show="ShowB", title="t2")
    seq = [(m["kind"], m["event"], m.get("name")) for m in _read(tmp_path)["marks"]]
    assert ("show", "start", "ShowA") in seq
    assert ("show", "end", "ShowA") in seq
    assert ("show", "start", "ShowB") in seq


def test_same_show_no_duplicate_show_start(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0))
    cw.item_start("track", show="ShowA", title="t1")
    cw.item_start("track", show="ShowA", title="t2")
    starts = [
        m for m in _read(tmp_path)["marks"]
        if m["kind"] == "show" and m["event"] == "start"
    ]
    assert len(starts) == 1


def test_item_end(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 5, 0)).item_end("track")
    ends = [m for m in _read(tmp_path)["marks"] if m["event"] == "end"]
    assert ends and ends[0]["kind"] == "track" and ends[0]["t"] == 300.0


def test_marks_append_to_one_sidecar(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0))
    cw.item_start("track", show="A", title="t1")
    cw.item_end("track")
    cw.item_start("track", show="A", title="t2")
    # show start + track start + track end + track start = 4 marks, one file
    assert len(_read(tmp_path)["marks"]) == 4
    assert list((tmp_path / "2026-06-05").glob("*.cues.json")) != []


def test_disabled_writes_nothing(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0), enabled=False).item_start(
        "track", show="X", title="t"
    )
    assert not (tmp_path / "2026-06-05").exists()


def test_no_folder_writes_nothing(tmp_path):
    CueWriter(
        lambda: {"enabled": True, "folder": "", "format": "mp3"},
        now_fn=lambda: datetime(2026, 6, 5, 14, 0, 0),
    ).item_start("track", show="X")
    assert list(tmp_path.iterdir()) == []


def test_format_ext_and_no_tmp_leftover(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0), fmt="opus").item_start(
        "track", show="A"
    )
    assert _read(tmp_path)["recording"] == "2026-06-05 14-00.opus"
    assert not list((tmp_path / "2026-06-05").glob("*.tmp"))


def test_none_and_empty_meta_omitted(tmp_path):
    _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 0)).item_start(
        "track", show="A", title=None, artist=""
    )
    track = [m for m in _read(tmp_path)["marks"] if m["kind"] == "track"][0]
    assert "title" not in track
    assert "artist" not in track


def test_never_raises_on_bad_config(tmp_path):
    # get_config returns junk / an unwritable drive -> logged, never raised.
    CueWriter(lambda: None).item_start("track", show="A")
    CueWriter(
        lambda: {"enabled": True, "folder": "Z:/no/such/path", "format": "mp3"},
        now_fn=lambda: datetime(2026, 6, 5, 14, 0, 0),
    ).item_start("track", show="A")
    CueWriter(lambda: {"enabled": True, "folder": str(tmp_path)}).item_end("track")


# ---- RASTATIME 2026-09-10 - item identity on start and end markers ----------


def test_item_markers_carry_the_item_id(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 5))
    cw.item_start("track", show="Morning", item=4711, title="Song A")
    cw.item_end("track", item=4711)
    marks = [m for m in _read(tmp_path)["marks"] if m["kind"] == "track"]
    assert [(m["event"], m["item"]) for m in marks] == [("start", 4711), ("end", 4711)]


def test_item_end_without_meta_is_unchanged(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 5))
    cw.item_end("webstream")
    (mark,) = [m for m in _read(tmp_path)["marks"] if m["kind"] == "webstream"]
    assert mark == {"t": 5.0, "kind": "webstream", "event": "end"}


# ---- audio_start (RASTATIME 2026-09-16) --------------------------------------

def test_audio_start_is_taken_from_the_audio_file(tmp_path):
    import os
    day = tmp_path / "2026-06-05"
    day.mkdir()
    audio = day / "2026-06-05 14-00.mp3"
    audio.write_bytes(b"x")
    created = datetime(2026, 6, 5, 14, 7, 30).timestamp()
    os.utime(audio, (created, created))          # mtime; birthtime is "now" on Windows
    _cw(tmp_path, datetime(2026, 6, 5, 14, 10, 0)).item_start("track", show="A", title="t")
    data = _read(tmp_path)
    assert "audio_start" in data and "audio_start_offset" in data
    start = datetime.fromisoformat(data["audio_start"])
    assert (start - datetime(2026, 6, 5, 14, 0, 0)).total_seconds() == data["audio_start_offset"]
    assert data["marks"][-1]["t"] == 600.0


def test_audio_start_is_added_on_a_later_mark_when_the_file_appears(tmp_path):
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 0, 5))
    cw.item_start("track", show="A", title="first")
    data = _read(tmp_path)
    assert "audio_start" not in data                 # no audio yet
    (tmp_path / "2026-06-05" / "2026-06-05 14-00.mp3").write_bytes(b"x")
    cw.item_end("track")
    data = _read(tmp_path)
    assert "audio_start" in data and data["audio_start_offset"] >= 0
    assert len(data["marks"]) == 3                   # show start, track start, track end


def test_audio_start_is_written_once(tmp_path):
    (tmp_path / "2026-06-05").mkdir()
    (tmp_path / "2026-06-05" / "2026-06-05 14-00.mp3").write_bytes(b"x")
    cw = _cw(tmp_path, datetime(2026, 6, 5, 14, 1, 0))
    cw.item_start("track", show="A", title="t")
    first = _read(tmp_path)["audio_start"]
    cw.item_end("track")
    assert _read(tmp_path)["audio_start"] == first


def test_parts_list_every_file_of_the_hour(tmp_path):
    import os
    day = tmp_path / "2026-06-05"
    day.mkdir()
    first = day / "2026-06-05 14-00.mp3"
    second = day / "2026-06-05 14-00.2.mp3"
    other_hour = day / "2026-06-05 15-00.mp3"
    for f in (first, second, other_hour):
        f.write_bytes(b"x")
    (day / "2026-06-05 14-00.cues.json").write_text("{}", encoding="utf-8")   # not a part
    _cw(tmp_path, datetime(2026, 6, 5, 14, 40, 0)).item_start("track", show="A", title="t")
    data = _read(tmp_path)
    names = [p["file"] for p in data["parts"]]
    assert names == ["2026-06-05 14-00.mp3", "2026-06-05 14-00.2.mp3"] or set(names) == {
        "2026-06-05 14-00.mp3", "2026-06-05 14-00.2.mp3"}
    assert all("start" in p and "offset" in p for p in data["parts"])
    assert data["audio_start"] == min(p["start"] for p in data["parts"])
    assert "15-00" not in json.dumps(data["parts"])


def test_audio_start_respects_the_format_extension(tmp_path):
    (tmp_path / "2026-06-05").mkdir()
    (tmp_path / "2026-06-05" / "2026-06-05 14-00.ogg").write_bytes(b"x")
    _cw(tmp_path, datetime(2026, 6, 5, 14, 1, 0), fmt="ogg").item_start("track", show="A", title="t")
    assert "audio_start" in _read(tmp_path)
