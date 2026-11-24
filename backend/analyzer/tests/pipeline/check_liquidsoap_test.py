"""RASTATIME 2026-11-24 - the import asks Liquidsoap whether it can decode a file."""

import shutil
from pathlib import Path
from queue import Queue

import pytest
from rastatime_analyzer.pipeline import Pipeline, PipelineOptions
from rastatime_analyzer.pipeline import check_liquidsoap as cl
from rastatime_shared.files import compute_md5

from ..conftest import AUDIO_FILE, AUDIO_FILENAME
from ._synth import requires_ffmpeg

REAL_LIQUIDSOAP = cl.liquidsoap_binary()
requires_liquidsoap = pytest.mark.skipif(not REAL_LIQUIDSOAP, reason="no Liquidsoap binary")


def _answers(monkeypatch, *answers):
    """liquidsoap_decodes answers one value per call, in this order."""
    calls = []
    queue = list(answers)

    def fake(paths, binary=None):
        calls.append(list(paths))
        return [queue.pop(0)]

    monkeypatch.setattr(cl, "liquidsoap_decodes", fake)
    return calls


def test_parse_results():
    out = "noise\nRESULT 2 true\nRESULT 1 false\nRESULT 9 true\nRESULT x true\n"
    assert cl.parse_results(out, 3) == [False, True, None]
    assert cl.parse_results("", 2) == [None, None]


def test_no_binary_lets_the_file_through(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cl, "liquidsoap_binary", lambda: None)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    assert cl.check_liquidsoap_decode(str(src), {"md5": "x"}) == (str(src), {"md5": "x"})
    assert cl.liquidsoap_decodes([str(src)]) == [None]


def test_a_decodable_file_is_unchanged(tmp_path: Path, monkeypatch):
    calls = _answers(monkeypatch, True)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    path, metadata = cl.check_liquidsoap_decode(str(src), {"md5": "x"}, binary="ls")
    assert (path, metadata) == (str(src), {"md5": "x"})
    assert calls == [[str(src)]]


def test_no_answer_lets_the_file_through(tmp_path: Path, monkeypatch):
    _answers(monkeypatch, None)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    assert cl.check_liquidsoap_decode(str(src), {}, binary="ls")[0] == str(src)
    assert [p.name for p in tmp_path.iterdir()] == ["a.mp3"]


@requires_ffmpeg
def test_undecodable_file_is_remuxed(tmp_path: Path, monkeypatch):
    calls = _answers(monkeypatch, False, True)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    data = src.read_bytes()

    path, metadata = cl.check_liquidsoap_decode(str(src), {"md5": "old", "x": 1}, binary="ls")

    remux = Path(path)
    assert remux.name == "a.remux.mp3" and remux.is_file()
    assert calls == [[str(src)], [str(remux)]]
    assert metadata["source_md5"] == "old"
    assert metadata["md5"] != "old" and metadata["filesize"] == remux.stat().st_size
    assert metadata["x"] == 1
    assert src.read_bytes() == data  # the original stays for the pipeline


@requires_ffmpeg
def test_a_converted_file_keeps_the_source_md5_of_the_upload(tmp_path: Path, monkeypatch):
    _answers(monkeypatch, False, None)  # second check without an answer: remux taken
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    _path, metadata = cl.check_liquidsoap_decode(
        str(src), {"md5": "conv", "source_md5": "upload"}, binary="ls"
    )
    assert metadata["source_md5"] == "upload"


@requires_ffmpeg
def test_refused_when_the_remux_does_not_help(tmp_path: Path, monkeypatch):
    _answers(monkeypatch, False, False)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    with pytest.raises(cl.LiquidsoapUndecodableError, match="not even after a lossless remux"):
        cl.check_liquidsoap_decode(str(src), {}, binary="ls")
    assert [p.name for p in tmp_path.iterdir()] == ["a.mp3"]


def test_refused_when_the_remux_fails(tmp_path: Path, monkeypatch):
    _answers(monkeypatch, False)

    def broken(_src, _dest):
        raise OSError("ffmpeg remux failed (exit 1)")

    monkeypatch.setattr(cl, "remux_copy", broken)
    src = tmp_path / "a.mp3"
    shutil.copy(AUDIO_FILE, src)
    with pytest.raises(cl.LiquidsoapUndecodableError, match="remux failed"):
        cl.check_liquidsoap_decode(str(src), {}, binary="ls")


def test_remux_target_is_numbered(tmp_path: Path):
    src = tmp_path / "a.mp3"
    (tmp_path / "a.remux.mp3").write_bytes(b"x")
    assert cl.remux_target(src).name == "a.remux2.mp3"


@requires_ffmpeg
def test_pipeline_files_the_remux_and_removes_the_upload(
    src_dir: Path, dest_dir: Path, monkeypatch
):
    monkeypatch.setattr(cl, "liquidsoap_binary", lambda: "ls")
    _answers(monkeypatch, False, True)
    upload = src_dir / AUDIO_FILENAME
    upload_md5 = compute_md5(upload)
    queue = Queue()

    Pipeline.run_analysis(queue, str(upload), str(dest_dir), AUDIO_FILENAME, PipelineOptions())

    metadata = queue.get()
    assert metadata["import_status"] == 0
    filed = list(dest_dir.rglob("*.mp3"))
    assert [p.name for p in filed] == [AUDIO_FILENAME]  # filed under the upload's name
    assert metadata["source_md5"] == upload_md5
    assert metadata["md5"] == compute_md5(filed[0])
    assert list(src_dir.iterdir()) == []  # upload and remux both gone from organize


@requires_ffmpeg
def test_pipeline_refusal_keeps_the_upload(src_dir: Path, dest_dir: Path, monkeypatch):
    monkeypatch.setattr(cl, "liquidsoap_binary", lambda: "ls")
    _answers(monkeypatch, False, False)
    upload = src_dir / AUDIO_FILENAME
    queue = Queue()

    with pytest.raises(cl.LiquidsoapUndecodableError):
        Pipeline.run_analysis(queue, str(upload), str(dest_dir), AUDIO_FILENAME, PipelineOptions())

    record = queue.get_nowait()
    assert record["import_status"] == 2
    assert record["comments"].startswith("The file could not be played: the playout engine")
    assert [p.name for p in src_dir.iterdir()] == [AUDIO_FILENAME]


@requires_liquidsoap
def test_real_liquidsoap_answers(tmp_path: Path):
    good = tmp_path / "good ä.mp3"
    shutil.copy(AUDIO_FILE, good)
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"this is not audio" * 100)
    assert cl.liquidsoap_decodes([str(good), str(bad)]) == [True, False]
