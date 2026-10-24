"""RASTATIME 2026-09-28 - EBU R128 measurement (analyzer stage 1)."""
from queue import Queue
from subprocess import CompletedProcess

import pytest

from libretime_analyzer.pipeline import _ffmpeg
from libretime_analyzer.pipeline.analyze_loudness import LOUDNESS_KEYS, analyze_loudness
from libretime_analyzer.pipeline.pipeline import Pipeline

from ..fixtures import fixtures_path

SUMMARY = """[Parsed_ebur128_0 @ 0000] Summary:

  Integrated loudness:
    I:         -14.2 LUFS
    Threshold: -24.5 LUFS

  Loudness range:
    LRA:         5.3 LU
    Threshold: -34.6 LUFS
    LRA low:   -17.9 LUFS
    LRA high:  -12.6 LUFS

  True peak:
    Peak:       -0.4 dBFS
"""


def _fake_ffmpeg(stderr):
    def run(*args, **kwargs):
        return CompletedProcess(args, 0, stdout="", stderr=stderr)
    return run


def test_summary_is_parsed(monkeypatch):
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg("noise\n" + SUMMARY))
    assert _ffmpeg.compute_loudness("x.mp3") == {
        "loudness_lufs": -14.2, "true_peak_dbtp": -0.4, "loudness_range_lu": 5.3,
    }
    metadata = analyze_loudness("x.mp3", {"track_title": "t"})
    assert metadata["loudness_lufs"] == -14.2 and metadata["track_title"] == "t"


def test_ffmpeg_output_is_read_tolerantly(monkeypatch):
    """2026-09-29: a tag byte outside the console code page killed the reader
    thread (library file 648) - both measurements pass errors=backslashreplace."""
    seen = []

    def run(*args, **kwargs):
        seen.append(kwargs)
        return CompletedProcess(args, 0, stdout="", stderr=SUMMARY + " track_gain = -5.10 dB\n")

    monkeypatch.setattr(_ffmpeg, "_ffmpeg", run)
    assert _ffmpeg.compute_loudness("x.mp3")["loudness_lufs"] == -14.2
    assert _ffmpeg.compute_replaygain("x.mp3") == -5.1
    assert [k.get("errors") for k in seen] == ["backslashreplace", "backslashreplace"]


def test_silence_and_garbage_are_not_measurable(monkeypatch):
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg(SUMMARY.replace("-14.2 LUFS", "-inf LUFS")))
    assert _ffmpeg.compute_loudness("x.mp3") is None
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg(SUMMARY.replace("-14.2 LUFS", "-70.0 LUFS")))
    assert _ffmpeg.compute_loudness("x.mp3") is None
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg("no summary here"))
    assert analyze_loudness("x.mp3", {"a": 1}) == {"a": 1}     # keys stay absent


# the parametrised FILES fixtures (s1-*.mp3 etc.) are not present in this
# checkout (the ReplayGain / cue-point tests fail on them as well); the
# three flac fixtures that exist are measured for real
REAL_FILES = [p for p in (fixtures_path / n for n in ("s1.flac", "s2.flac", "s3.flac")) if p.is_file()]


@pytest.mark.parametrize("filepath", [pytest.param(str(p), id=p.name) for p in REAL_FILES])
def test_measure_fixture_files(filepath):
    metadata = analyze_loudness(filepath, {})
    for key in LOUDNESS_KEYS:
        assert key in metadata
    assert -40.0 < metadata["loudness_lufs"] < 0.0
    assert metadata["true_peak_dbtp"] < 3.0
    assert metadata["loudness_range_lu"] >= 0.0


def test_s1_matches_ffmpeg_summary():
    """s1.flac measured by hand with ffmpeg 9: I -11.6 LUFS, LRA 20.2 LU, peak -0.3 dBFS."""
    if not REAL_FILES:
        pytest.skip("fixture files missing")
    metadata = analyze_loudness(str(fixtures_path / "s1.flac"), {})
    assert metadata["loudness_lufs"] == pytest.approx(-11.6, abs=0.3)
    assert metadata["loudness_range_lu"] == pytest.approx(20.2, abs=0.5)
    assert metadata["true_peak_dbtp"] == pytest.approx(-0.3, abs=0.2)


def test_run_loudness_reports_only_the_measurement():
    if not REAL_FILES:
        pytest.skip("fixture files missing")
    queue: Queue = Queue()
    Pipeline.run_loudness(queue, str(REAL_FILES[0]))
    metadata = queue.get()
    assert set(metadata) == set(LOUDNESS_KEYS)
    assert "import_status" not in metadata


# RASTATIME 2026-10-24 - damaged MP3 frames re-initialise ffmpeg's filter
# graph: several Summary blocks, the first one real, the rest stubs.  Such a
# file is measured again from a normalised stream (one summary).
def test_multiple_summaries_measure_again_from_a_normalised_stream(monkeypatch):
    stub = SUMMARY.replace("-14.2 LUFS", "-70.0 LUFS").replace("-0.4 dBFS", "26.4 dBFS")
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg("noise" + chr(10) + SUMMARY + chr(10) + stub + chr(10) + stub))
    calls = []
    monkeypatch.setattr(
        _ffmpeg,
        "_loudness_text_normalised",
        lambda path, timeout=600.0: calls.append(path) or SUMMARY.replace("-14.2 LUFS", "-13.7 LUFS").replace("-0.4 dBFS", "6.4 dBFS"),
    )
    result = _ffmpeg.compute_loudness("x.mp3")
    assert calls == ["x.mp3"]
    assert result["loudness_lufs"] == -13.7
    assert result["true_peak_dbtp"] == 6.4


def test_single_summary_never_measures_twice(monkeypatch):
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg("noise" + chr(10) + SUMMARY))
    monkeypatch.setattr(_ffmpeg, "_loudness_text_normalised", lambda *a, **k: pytest.fail("not expected"))
    assert _ffmpeg.compute_loudness("x.mp3")["loudness_lufs"] == -14.2


def test_failed_second_measurement_is_not_measurable(monkeypatch):
    stub = SUMMARY.replace("-14.2 LUFS", "-70.0 LUFS")
    monkeypatch.setattr(_ffmpeg, "_ffmpeg", _fake_ffmpeg(SUMMARY + chr(10) + stub))
    monkeypatch.setattr(_ffmpeg, "_loudness_text_normalised", lambda *a, **k: "")
    assert _ffmpeg.compute_loudness("x.mp3") is None
