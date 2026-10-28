"""
RASTATIME 2026-10-28 - repair_container: an ID3v2 block glued in front of a
RIFF/WAV header (the 2026-10-20 upload) is cut away and the payload imported.
"""

from pathlib import Path
from queue import Queue

import pytest

from libretime_analyzer.pipeline import Pipeline, PipelineOptions
from libretime_analyzer.pipeline import repair_container as rc

from ._synth import ffmpeg, requires_ffmpeg, sine

ID3_BLOCK = b"ID3\x03\x00\x00\x00\x00\x00\x1f" + b"TIT2\x00\x00\x00\x05\x00\x00\x00test" + b"\x00" * 10


def _riff_with_id3(tmp_path: Path, codec: str) -> Path:
    """A RIFF/WAV file whose payload is `codec` (mp3 or pcm), with an ID3 block in front."""
    clean = tmp_path / "clean.wav"
    if codec == "mp3":
        mp3 = sine(tmp_path / "payload.mp3", "-b:a", "128k")
        ffmpeg("-i", str(mp3), "-c:a", "copy", str(clean))
    else:
        sine(clean)
    broken = tmp_path / "7-Broken Song.mp3"
    broken.write_bytes(ID3_BLOCK + clean.read_bytes())
    return broken


def test_riff_offset_detection():
    assert rc._riff_offset(ID3_BLOCK + b"RIFF\x00\x00\x00\x00WAVEfmt ") == len(ID3_BLOCK)
    assert rc._riff_offset(b"RIFF\x00\x00\x00\x00WAVE") == -1          # no ID3 in front: nothing to do
    assert rc._riff_offset(b"ID3\x03\x00" + b"\x00" * 100) == -1        # ID3 but no RIFF
    assert rc._riff_offset(b"ID3" + b"RIFF\x00\x00\x00\x00AVI ") == -1  # RIFF but not WAVE


def test_untouched_file_is_returned_unchanged(tmp_path):
    plain = tmp_path / "plain.mp3"
    plain.write_bytes(b"\xff\xfb\x90\x00" * 100)
    path, name, meta = rc.repair_container(str(plain), "plain.mp3", {})
    assert (path, name, meta) == (str(plain), "plain.mp3", {})


@requires_ffmpeg
def test_mp3_payload_is_extracted_without_reencoding(tmp_path):
    broken = _riff_with_id3(tmp_path, "mp3")
    path, name, meta = rc.repair_container(str(broken), "Broken Song.mp3", {})
    repaired = Path(path)
    assert repaired != broken and repaired.is_file()
    assert repaired.suffix == ".mp3" and name == "Broken Song.mp3"
    assert "source_md5" in meta and len(meta["source_md5"]) == 32
    assert broken.is_file()                       # the original stays until the pipeline files the copy
    assert not list(tmp_path.glob("*.repaired.wav"))  # the intermediate is gone
    from ._synth import audio_stream
    assert audio_stream(repaired)["codec_name"] == "mp3"


@requires_ffmpeg
def test_pcm_payload_becomes_a_wav(tmp_path):
    broken = _riff_with_id3(tmp_path, "pcm")
    path, name, _ = rc.repair_container(str(broken), "Broken Song.mp3", {})
    assert Path(path).suffix == ".wav" and name == "Broken Song.wav"
    from ._synth import audio_stream
    assert audio_stream(Path(path))["codec_name"].startswith("pcm")


@requires_ffmpeg
def test_pipeline_imports_the_repaired_file_and_removes_the_original(tmp_path):
    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    dest_dir = tmp_path / "imported"
    broken = _riff_with_id3(src_dir, "mp3")
    queue = Queue()
    Pipeline.run_analysis(queue, str(broken), str(dest_dir), "Broken Song.mp3", PipelineOptions())
    metadata = queue.get()
    assert metadata["import_status"] == 0
    assert metadata["mime"] == "audio/mp3"
    assert Path(metadata["full_path"]).is_file()
    assert not broken.exists()                    # filed: the broken original is removed
    assert not list(src_dir.glob("*.repaired.*"))  # no intermediate left behind


def test_failure_record_carries_the_reason():
    import subprocess

    exc = subprocess.CalledProcessError(1, ["C:/ffmpeg/bin/ffprobe.exe", "-i", "x"], b"", b"[wav] invalid start code ID3[3] in RIFF header\nx.mp3: Invalid data found when processing input\n")
    text = Pipeline.describe(exc)
    assert text.startswith("ffprobe.exe could not read the file:")
    assert "Invalid data found" in text
    record = Pipeline.failure(text)
    assert record["import_status"] == 2
    assert record["comments"] == text
    assert len(Pipeline.failure("x" * 1000)["comments"]) == Pipeline.REASON_MAX
    assert Pipeline.describe(ValueError("boom")) == "ValueError: boom"


def test_failing_pipeline_puts_the_reason_in_the_queue(tmp_path):
    bad = tmp_path / "3-bad.mp3"
    bad.write_bytes(b"not audio at all")
    queue = Queue()
    with pytest.raises(Exception):
        Pipeline.run_analysis(queue, str(bad), str(tmp_path / "imported"), "bad.mp3", PipelineOptions())
    record = queue.get_nowait()
    assert record["import_status"] == 2
    assert record["comments"].startswith("ffprobe could not read the file (exit ")
    assert "damaged container" in record["comments"]
    assert "KeyError" not in record["comments"] and "Command" not in record["comments"]
    assert bad.is_file()  # the original stays in organize/
