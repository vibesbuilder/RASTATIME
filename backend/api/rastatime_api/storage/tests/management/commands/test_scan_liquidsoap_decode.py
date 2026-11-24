"""RASTATIME 2026-11-24 - library scan with Liquidsoap's own decoder (no database:
the batching, the report and the repair run against fakes and temp files)."""

import csv
from datetime import date
from pathlib import Path

import pytest

from ....management.commands import scan_liquidsoap_decode as sld

pytestmark = pytest.mark.skipif(sld.cl is None, reason="analyzer not installed")


def test_backup_path(tmp_path: Path):
    got = sld.backup_path(tmp_path, 42, Path("D:/stor/a b/x.mp3"), date(2026, 11, 24))
    assert got == tmp_path / "_replaced" / "remux-2026-11-24" / "42-x.mp3"


def _command(tmp_path, monkeypatch, answers):
    calls = []

    def fake_decodes(paths, binary=None):
        calls.append(len(paths))
        return [answers[Path(p).name] for p in paths]

    monkeypatch.setattr(sld.cl, "liquidsoap_decodes", fake_decodes)
    cmd = sld.Command()
    out = []
    cmd.stdout.write = out.append  # type: ignore[method-assign]
    return cmd, calls, out


def test_scan_batches_and_reports(tmp_path: Path, monkeypatch):
    for name in ("a.mp3", "b.mp3", "c.mp3"):
        (tmp_path / name).write_bytes(b"x")
    answers = {"a.mp3": True, "b.mp3": False, "c.mp3": None}
    cmd, calls, out = _command(tmp_path, monkeypatch, answers)
    rows = [
        (1, "a.mp3", "A", "t1"),
        (2, "b.mp3", "B", "t2"),
        (3, "gone.mp3", "G", "t3"),
        (4, "c.mp3", "C", "t4"),
    ]
    report = tmp_path / "r.csv"

    cmd._scan(rows, tmp_path, "ls", "", report, batch=2)

    assert calls == [2, 1]  # missing files are not sent to Liquidsoap
    with report.open(encoding="utf-8-sig") as fh:
        lines = list(csv.reader(fh, delimiter=";"))
    assert lines[0] == list(sld.FIELDS)
    assert [(r[0], r[1]) for r in lines[1:]] == [
        ("2", "undecodable"),
        ("3", "missing"),
        ("4", "unknown"),
    ]
    assert "ok 1" in out[-1] and "undecodable 1" in out[-1]


def test_nothing_found_writes_no_report(tmp_path: Path, monkeypatch):
    (tmp_path / "a.mp3").write_bytes(b"x")
    cmd, _calls, out = _command(tmp_path, monkeypatch, {"a.mp3": True})
    report = tmp_path / "r.csv"
    cmd._scan([(1, "a.mp3", "", "")], tmp_path, "ls", "", report, batch=10)
    assert not report.exists() and "nothing found" in out[-1]


def test_repair_is_called_only_with_ffmpeg(tmp_path: Path, monkeypatch):
    (tmp_path / "b.mp3").write_bytes(b"x")
    cmd, _calls, _out = _command(tmp_path, monkeypatch, {"b.mp3": False})
    repaired = []
    monkeypatch.setattr(
        sld, "repair_file", lambda fid, *_a, **_k: repaired.append(fid) or ("repaired", "ok")
    )
    cmd._scan([(2, "b.mp3", "", "")], tmp_path, "ls", "", tmp_path / "r1.csv", batch=5)
    assert repaired == []
    cmd._scan([(2, "b.mp3", "", "")], tmp_path, "ls", "ffmpeg", tmp_path / "r2.csv", batch=5)
    assert repaired == [2]


def test_repair_skips_a_file_on_air_soon(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sld, "scheduled_soon", lambda *_a: True)
    path = tmp_path / "b.mp3"
    path.write_bytes(b"x")
    assert sld.repair_file(2, path, tmp_path, "ls", "ffmpeg")[0] == "skipped"
    assert path.read_bytes() == b"x"


def test_repair_keeps_the_original_when_the_remux_does_not_help(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sld, "scheduled_soon", lambda *_a: False)
    monkeypatch.setattr(
        sld.cl, "remux_copy", lambda src, dest, _ff=None: dest.write_bytes(b"remux")
    )
    monkeypatch.setattr(sld.cl, "liquidsoap_decodes", lambda paths, binary=None: [False])
    path = tmp_path / "b.mp3"
    path.write_bytes(b"orig")
    status, detail = sld.repair_file(2, path, tmp_path, "ls", "ffmpeg")
    assert status == "repair_failed" and "original kept" in detail
    assert path.read_bytes() == b"orig"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b.mp3"]
