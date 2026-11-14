"""RASTATIME 2026-11-14 - copy finished show recordings to a second folder."""

import os
import sys
import time

import pytest

from .. import recording_copy as rc

NOW = 1_800_000_000.0
SINCE = NOW - 3600
BIG = b"x" * (rc.MIN_BYTES + 10)


def _recording(folder, name, age=600.0, data=BIG, day="2026-11-14"):
    """A file in ``<folder>/<day>/`` whose last write lies ``age`` s before NOW."""
    day_dir = folder / day
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / name
    path.write_bytes(data)
    os.utime(path, (NOW - age, NOW - age))
    return path


def _run(source, target, state=None, **kwargs):
    kwargs.setdefault("locked", lambda _path: False)
    return rc.run(str(source), str(target), SINCE, state or rc.empty_state(), now=NOW, **kwargs)


@pytest.fixture
def folders(tmp_path):
    source, target = tmp_path / "shows", tmp_path / "pickup"
    source.mkdir()
    target.mkdir()
    return source, target


def test_copies_a_finished_recording_flat_and_keeps_its_name(folders):
    source, target = folders
    _recording(source, "2026-11-14 08-15-00 - Morning Live.mp3")
    lines = []
    state = _run(source, target, log=lines.append)
    copied = target / "2026-11-14 08-15-00 - Morning Live.mp3"
    assert copied.read_bytes() == BIG
    assert not list(target.glob("*.part"))
    assert [p.name for p in target.iterdir()] == [copied.name]  # no day folder
    assert state["ok"] is True and state["message"] == ""
    assert state["last_file"] == copied.name and state["copied_total"] == 1
    assert "2026-11-14/2026-11-14 08-15-00 - Morning Live.mp3" in state["ledger"]
    assert lines == [f"copied {copied.name} ({len(BIG)} bytes)"]
    assert int(copied.stat().st_mtime) == int(NOW - 600)  # the recording's own time


def test_leaves_out_what_is_old_tiny_fresh_foreign_or_still_open(folders):
    source, target = folders
    _recording(source, "old.mp3", age=7200)  # finished before the switch-on
    _recording(source, "tiny.mp3", data=b"x" * 100)  # sentinel / aborted
    _recording(source, "fresh.mp3", age=rc.SETTLE_SECONDS - 5)  # may still be flushed
    _recording(source, "notes.txt")  # no audio
    _recording(source, "running.mp3")
    state = _run(source, target, locked=lambda path: path.name == "running.mp3")
    assert list(target.iterdir()) == []
    assert state["ok"] is True and state["ledger"] == {} and state["copied_total"] == 0


def test_a_recording_is_copied_once_even_when_it_was_taken_away(folders):
    source, target = folders
    _recording(source, "show.mp3")
    state = _run(source, target)
    (target / "show.mp3").unlink()  # the show maker moved it to their own folder
    again = _run(source, target, state)
    assert list(target.iterdir()) == []
    assert again["copied_total"] == 1 and again["last_file"] == "show.mp3"


def test_never_overwrites_a_different_file_of_the_same_name(folders):
    source, target = folders
    _recording(source, "show.mp3")
    (target / "show.mp3").write_bytes(b"someone else's file")
    state = _run(source, target)
    assert (target / "show.mp3").read_bytes() == b"someone else's file"
    assert (target / "show (2).mp3").read_bytes() == BIG
    assert state["last_file"] == "show (2).mp3"


def test_same_name_and_size_at_the_target_counts_as_copied(folders):
    source, target = folders
    _recording(source, "show.mp3")
    (target / "show.mp3").write_bytes(BIG)
    before = (target / "show.mp3").stat().st_mtime
    lines = []
    state = _run(source, target, log=lines.append)
    assert (target / "show.mp3").stat().st_mtime == before  # untouched
    assert "2026-11-14/show.mp3" in state["ledger"]
    assert lines == ["already at the target, not copied again: show.mp3"]


def test_unreachable_target_reports_and_copies_nothing(folders, tmp_path):
    source, _target = folders
    _recording(source, "show.mp3")
    lines = []
    state = rc.run(
        str(source), str(tmp_path / "gone"), SINCE, rc.empty_state(), now=NOW, log=lines.append
    )
    assert state["ok"] is False and "target folder not reachable" in state["message"]
    assert state["ledger"] == {} and state["last_run"] == rc.utc_iso(NOW)
    assert lines and lines[0].startswith("ERROR target folder not reachable")
    # the next run with the target back copies it
    assert _run(source, folders[1], state)["copied_total"] == 1


def test_missing_source_reports(folders, tmp_path):
    state = rc.run(str(tmp_path / "nope"), str(folders[1]), SINCE, rc.empty_state(), now=NOW)
    assert state["ok"] is False and "recording folder not reachable" in state["message"]
    state = rc.run(None, str(folders[1]), SINCE, rc.empty_state(), now=NOW)
    assert "(not set)" in state["message"]


def test_a_failed_copy_stops_the_run_and_is_retried(folders, monkeypatch):
    source, target = folders
    _recording(source, "a.mp3", age=900)
    _recording(source, "b.mp3", age=600)
    real = rc.copy_one

    def failing(path, target_dir):
        if path.name == "a.mp3":
            raise OSError("network name no longer available")
        return real(path, target_dir)

    monkeypatch.setattr(rc, "copy_one", failing)
    state = _run(source, target)
    assert state["ok"] is False and state["message"].startswith("a.mp3: network name")
    assert state["pending"] == 2 and state["ledger"] == {}
    monkeypatch.setattr(rc, "copy_one", real)
    state = _run(source, target, state)
    assert state["ok"] is True and state["copied_total"] == 2
    assert sorted(p.name for p in target.iterdir()) == ["a.mp3", "b.mp3"]


def test_a_leftover_part_file_is_replaced_and_a_short_copy_is_refused(folders, monkeypatch):
    source, target = folders
    _recording(source, "show.mp3")
    (target / "show.mp3.part").write_bytes(b"half")
    _run(source, target)
    assert (target / "show.mp3").read_bytes() == BIG
    assert not (target / "show.mp3.part").exists()

    _recording(source, "cut.mp3")
    monkeypatch.setattr(rc.shutil, "copyfileobj", lambda src, dst, _n: dst.write(b"short"))
    state = _run(source, target)
    assert state["ok"] is False and "copied 5 of" in state["message"]
    assert not (target / "cut.mp3").exists() and not (target / "cut.mp3.part").exists()


def test_ledger_forgets_recordings_that_left_the_recording_folder(folders):
    source, target = folders
    path = _recording(source, "show.mp3")
    state = _run(source, target)
    path.unlink()  # retention removed the recording
    assert _run(source, target, state)["ledger"] == {}


def test_oldest_first_and_state_survives_json(folders):
    source, target = folders
    _recording(source, "second.mp3", age=300)
    _recording(source, "first.mp3", age=900)
    lines = []
    state = _run(source, target, log=lines.append)
    assert [line.split()[1] for line in lines] == ["first.mp3", "second.mp3"]
    loaded = rc.load_state(rc.json.dumps(state))
    assert loaded == state
    assert rc.load_state("not json") == rc.empty_state()
    assert rc.load_state(None)["ledger"] == {}


def test_parse_utc_and_utc_iso_round_trip():
    assert rc.utc_iso(0) == "1970-01-01T00:00:00Z"
    assert rc.parse_utc("1970-01-01T00:00:10Z") == 10.0
    assert rc.parse_utc("1970-01-01T01:00:00+01:00") == 0.0
    assert rc.parse_utc("1970-01-01T00:00:10") == 10.0  # no zone = UTC
    assert rc.parse_utc("") is None and rc.parse_utc("yesterday") is None
    assert rc.parse_utc(rc.utc_iso(NOW)) == NOW


@pytest.mark.skipif(sys.platform != "win32", reason="the open-file test is a Windows share mode")
def test_is_locked_sees_a_file_another_handle_has_open(tmp_path):
    path = tmp_path / "running.mp3"
    path.write_bytes(BIG)
    assert rc.is_locked(path) is False
    with open(path, "ab"):  # a writer, like the running recording
        assert rc.is_locked(path) is True
    with open(path, "rb"):  # a reader (library import, virus scanner) does not count
        assert rc.is_locked(path) is False
    assert rc.is_locked(path) is False
    assert rc.is_locked(tmp_path / "missing.mp3") is True  # cannot be opened: not ours to copy


def test_find_candidates_uses_the_real_clock_by_default(folders):
    source, _target = folders
    path = _recording(source, "show.mp3")
    os.utime(path, (time.time() - 60, time.time() - 60))
    found = rc.find_candidates(source, time.time() - 3600, {}, time.time(), lambda _p: False)
    assert found == [path]
