"""RASTATIME 2026-11-21 - library scan for damaged files (no database: the
checking and the report run on synthetic files)."""

import csv
import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ....management.commands import scan_damaged_files as sdf

FFMPEG = shutil.which(os.environ.get("FFMPEG_PATH") or "ffmpeg") or (
    "C:/ffmpeg/bin/ffmpeg.exe" if Path("C:/ffmpeg/bin/ffmpeg.exe").is_file() else None
)
requires_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not found")


def _sine(path: Path, *codec, seconds=30) -> Path:
    subprocess.run(
        [FFMPEG, "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency=440:duration={seconds}", "-ac", "2", *codec, str(path)],
        check=True,
    )  # fmt: skip
    return path


def _cut(src: Path, fraction: float, name: str) -> Path:
    dest = src.with_name(name)
    data = src.read_bytes()
    dest.write_bytes(data[: int(len(data) * fraction)])
    return dest


@pytest.fixture(name="mp3")
def _mp3(tmp_path):
    return _sine(tmp_path / "full.mp3", "-c:a", "libmp3lame", "-b:a", "128k")


@pytest.mark.parametrize(
    ("length", "cue_out", "end"),
    [
        (30.0, 28.5, 28.5),
        (30.0, None, 30.0),
        (30.0, 0.0, 30.0),
        (None, None, None),
        (0.0, 0.0, None),
    ],
)
def test_the_playout_end_is_the_cue_out_else_the_length(length, cue_out, end):
    assert sdf.playout_end(length, cue_out) == end


@requires_ffmpeg
def test_a_full_file_is_ok(mp3):
    result = sdf.check_file(str(mp3), 30.0, FFMPEG)
    assert result.status == "ok" and result.decoded == pytest.approx(30.0, abs=0.2)


@requires_ffmpeg
def test_a_cut_file_is_reported(mp3):
    result = sdf.check_file(str(_cut(mp3, 0.4, "cut.mp3")), 30.0, FFMPEG)
    assert result.status == "truncated" and result.decoded == pytest.approx(12.0, abs=0.5)


@requires_ffmpeg
def test_a_cut_file_whose_cue_out_lies_inside_the_audio_is_fine(mp3):
    # the playout ends at the cue-out: nothing is missing before it
    result = sdf.check_file(str(_cut(mp3, 0.4, "cut.mp3")), sdf.playout_end(30.0, 11.0), FFMPEG)
    assert result.status == "ok"


@requires_ffmpeg
def test_a_cut_m4a_is_reported(tmp_path):
    m4a = _sine(tmp_path / "full.m4a", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart")
    assert sdf.check_file(str(m4a), 30.0, FFMPEG).status == "ok"
    assert sdf.check_file(str(_cut(m4a, 0.6, "cut.m4a")), 30.0, FFMPEG).status in (
        "truncated",
        "unplayable",
    )


@requires_ffmpeg
def test_a_missing_and_an_undecodable_file(tmp_path):
    assert sdf.check_file(str(tmp_path / "gone.mp3"), 30.0, FFMPEG).status == "missing"
    junk = tmp_path / "junk.mp3"
    junk.write_bytes(b"not audio at all" * 100)
    assert sdf.check_file(str(junk), 30.0, FFMPEG).status == "unplayable"


@requires_ffmpeg
def test_the_report_lists_only_the_problems_and_the_run_can_resume(tmp_path, mp3):
    root = tmp_path
    _cut(mp3, 0.4, "cut.mp3")
    rows = [
        (1, "full.mp3", "A", "Full", 30.0, None),
        (2, "cut.mp3", "B", "Cut", 30.0, 29.5),
        (3, "gone.mp3", "C", "Gone", 30.0, None),
    ]
    report = tmp_path / "out" / "report.csv"
    progress = report.with_name("report.csv.progress")
    out = io.StringIO()
    cmd = sdf.Command(stdout=out)
    cmd._scan(rows, str(root), FFMPEG, report, progress, append=False, track=True)
    with report.open(encoding="utf-8-sig", newline="") as fh:
        lines = list(csv.reader(fh, delimiter=";"))
    assert lines[0] == list(sdf.FIELDS)
    assert [(r[0], r[1]) for r in lines[1:]] == [("2", "truncated"), ("3", "missing")]
    cut = lines[1]
    assert cut[2:4] == ["B", "Cut"] and cut[6] == "29.5" and float(cut[8]) > 15
    assert progress.read_text(encoding="ascii") == "3"
    assert "1 cut short" in out.getvalue() and "1 missing" in out.getvalue()
    # a resumed run appends without a second header
    cmd._scan([(4, "cut.mp3", "D", "Cut again", 30.0, None)], str(root), FFMPEG, report, progress,
              append=True, track=True)  # fmt: skip
    with report.open(encoding="utf-8-sig", newline="") as fh:
        lines = list(csv.reader(fh, delimiter=";"))
    assert [r[0] for r in lines] == ["id", "2", "3", "4"]
    assert progress.read_text(encoding="ascii") == "4"


def test_the_default_report_lies_in_the_logs_folder_next_to_the_config(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "logs").mkdir()
    monkeypatch.setenv("RASTATIME_CONFIG_FILEPATH", str(tmp_path / "config" / "rastatime.conf"))
    path = sdf.default_report()
    assert path.parent == (tmp_path / "logs").resolve()
    assert path.name.startswith("damaged-files-") and path.suffix == ".csv"
