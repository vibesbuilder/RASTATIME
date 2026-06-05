"""
RASTATIME 2026-06-05 — Unit tests for recording_retention (Record-per-Hour
stage 3): automatic cleanup of old 24/7 archive day-folders.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from libretime_playout.recording_retention import (
    RecordingRetentionThread,
    prune_old_recordings,
)

TODAY = date(2026, 6, 15)


def _make_day(folder: Path, day: str, *, files=("12-00.mp3",)) -> Path:
    d = folder / day
    d.mkdir(parents=True)
    for f in files:
        (d / f).write_bytes(b"x")
    return d


# ---- prune_old_recordings ----------------------------------------------


def test_prune_deletes_old_keeps_recent(tmp_path):
    old = _make_day(tmp_path, "2026-06-01")           # 14 days
    edge = _make_day(tmp_path, "2026-06-08")          # 7 days
    recent = _make_day(tmp_path, "2026-06-10")        # 5 days
    today_folder = _make_day(tmp_path, "2026-06-15")  # 0 days

    deleted = prune_old_recordings(tmp_path, 7, today=TODAY)

    assert old in deleted
    assert edge in deleted          # exactly 7 days old -> deleted
    assert recent not in deleted
    assert not old.exists()
    assert not edge.exists()
    assert recent.exists()
    assert today_folder.exists()


def test_prune_boundary_off_by_one(tmp_path):
    six = _make_day(tmp_path, "2026-06-09")    # 6 days -> kept
    seven = _make_day(tmp_path, "2026-06-08")  # 7 days -> deleted
    deleted = prune_old_recordings(tmp_path, 7, today=TODAY)
    assert seven in deleted and not seven.exists()
    assert six not in deleted and six.exists()


def test_prune_retention_zero_keeps_everything(tmp_path):
    d = _make_day(tmp_path, "2020-01-01")
    assert prune_old_recordings(tmp_path, 0, today=TODAY) == []
    assert d.exists()


def test_prune_negative_keeps_everything(tmp_path):
    d = _make_day(tmp_path, "2020-01-01")
    assert prune_old_recordings(tmp_path, -5, today=TODAY) == []
    assert d.exists()


def test_prune_ignores_non_date_dirs(tmp_path):
    # A nested per-show recordings folder (different name) must be untouched.
    show = tmp_path / "show-recordings"
    show.mkdir()
    (show / "keep.mp3").write_bytes(b"x")
    junk = tmp_path / "not-a-date"
    junk.mkdir()

    deleted = prune_old_recordings(tmp_path, 7, today=TODAY)

    assert deleted == []
    assert show.exists() and (show / "keep.mp3").exists()
    assert junk.exists()


def test_prune_ignores_loose_files(tmp_path):
    f = tmp_path / "2026-06-01.txt"   # a *file*, not a YYYY-MM-DD dir
    f.write_bytes(b"x")
    assert prune_old_recordings(tmp_path, 7, today=TODAY) == []
    assert f.exists()


def test_prune_nonexistent_folder(tmp_path):
    assert prune_old_recordings(tmp_path / "nope", 7, today=TODAY) == []


# ---- RecordingRetentionThread._run_once --------------------------------


def test_thread_noop_when_disabled(tmp_path):
    old = _make_day(tmp_path, "2020-01-01")
    cfg = {"enabled": False, "folder": str(tmp_path), "retention_days": 7}
    RecordingRetentionThread(lambda: cfg, today_fn=lambda: TODAY)._run_once()
    assert old.exists()  # recorder disabled -> nothing pruned


def test_thread_noop_when_retention_zero(tmp_path):
    old = _make_day(tmp_path, "2020-01-01")
    cfg = {"enabled": True, "folder": str(tmp_path), "retention_days": 0}
    RecordingRetentionThread(lambda: cfg, today_fn=lambda: TODAY)._run_once()
    assert old.exists()


def test_thread_noop_when_no_folder(tmp_path):
    old = _make_day(tmp_path, "2020-01-01")
    cfg = {"enabled": True, "folder": "", "retention_days": 7}
    RecordingRetentionThread(lambda: cfg, today_fn=lambda: TODAY)._run_once()
    assert old.exists()


def test_thread_prunes_when_enabled(tmp_path):
    old = _make_day(tmp_path, "2020-01-01")
    recent = _make_day(tmp_path, "2026-06-14")
    cfg = {"enabled": True, "folder": str(tmp_path), "retention_days": 7}
    RecordingRetentionThread(lambda: cfg, today_fn=lambda: TODAY)._run_once()
    assert not old.exists()
    assert recent.exists()


def test_thread_survives_bad_config():
    # get_config returns junk -> _run_once must not raise.
    RecordingRetentionThread(lambda: None, today_fn=lambda: TODAY)._run_once()
    RecordingRetentionThread(
        lambda: {"enabled": True, "folder": "Z:/does/not/exist", "retention_days": "oops"},
        today_fn=lambda: TODAY,
    )._run_once()
