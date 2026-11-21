from datetime import timedelta
from pathlib import Path
from queue import Queue

import pytest
from rastatime_analyzer.pipeline import Pipeline, PipelineOptions
from rastatime_analyzer.pipeline import pipeline as pipeline_module
from rastatime_analyzer.pipeline.pipeline import tagged_track_type

from ..conftest import AUDIO_FILENAME, AUDIO_IMPORT_DEST
from ._synth import requires_ffmpeg


def test_run_analysis(src_dir: Path, dest_dir: Path):
    queue = Queue()
    Pipeline.run_analysis(
        queue,
        str(src_dir / AUDIO_FILENAME),
        str(dest_dir),
        AUDIO_FILENAME,
        PipelineOptions(),
    )
    metadata = queue.get()

    assert metadata["track_title"] == "Test Title"
    assert metadata["artist_name"] == "Test Artist"
    assert metadata["album_title"] == "Test Album"
    assert metadata["year"] == "1999"
    assert metadata["genre"] == "Test Genre"
    assert metadata["mime"] == "audio/mp3"
    assert metadata["length_seconds"] == pytest.approx(15.0, abs=0.1)
    assert metadata["length"] == str(timedelta(seconds=metadata["length_seconds"]))
    assert (dest_dir / AUDIO_IMPORT_DEST).exists()


# RASTATIME 2026-10-14 - format normalization inside the import pipeline
def _tagged_flac(src_dir: Path) -> Path:
    from ._synth import sine

    return sine(
        src_dir / "42-Lossless.flac",
        *("-metadata", "title=Lossless Title"),
        *("-metadata", "artist=Lossless Artist"),
        *("-metadata", "album=Lossless Album"),
        *("-metadata", "EXPIRY=2027-05-31"),
    )


@requires_ffmpeg
def test_run_analysis_converts_lossless_to_mp3(tmp_path: Path, dest_dir: Path):
    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    src = _tagged_flac(src_dir)
    queue = Queue()

    Pipeline.run_analysis(
        queue,
        str(src),
        str(dest_dir),
        "Lossless.flac",
        PipelineOptions(convert_lossless=True),
    )
    metadata = queue.get()

    imported = dest_dir / "Lossless Artist" / "Lossless Album" / "Lossless.mp3"
    assert metadata["full_path"] == str(imported)
    assert imported.exists()
    assert list(src_dir.iterdir()) == []  # neither the FLAC nor a temp file
    assert metadata["mime"] == "audio/mp3"
    assert metadata["bit_rate"] == 320000
    assert len(metadata["source_md5"]) == 32
    assert metadata["source_md5"] != metadata["md5"]
    assert metadata["track_title"] == "Lossless Title"
    assert metadata["expires_at"] == "2027-05-31"
    assert metadata["length_seconds"] == pytest.approx(3.0, abs=0.1)
    assert float(metadata["cueout"]) == pytest.approx(3.0, abs=0.1)
    assert metadata["loudness_lufs"] is not None


@requires_ffmpeg
def test_run_analysis_keeps_lossless_by_default(tmp_path: Path, dest_dir: Path):
    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    src = _tagged_flac(src_dir)
    queue = Queue()

    Pipeline.run_analysis(
        queue,
        str(src),
        str(dest_dir),
        "Lossless.flac",
        PipelineOptions(),
    )
    metadata = queue.get()

    assert metadata["full_path"].endswith("Lossless.flac")
    assert metadata["mime"] == "audio/flac"
    assert "source_md5" not in metadata


@requires_ffmpeg
def test_failed_import_after_conversion_keeps_the_original(
    tmp_path: Path, dest_dir: Path, monkeypatch
):
    # RASTATIME 2026-10-14 - review: the original is deleted only once the
    # conversion is filed; a later failure (or an analyzer restart, after
    # which RabbitMQ redelivers the message) must still find it.
    from rastatime_analyzer.pipeline import pipeline as pipeline_module

    def broken_organise(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pipeline_module, "organise_file", broken_organise)
    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    src = _tagged_flac(src_dir)
    data = src.read_bytes()
    queue = Queue()

    with pytest.raises(OSError):
        Pipeline.run_analysis(
            queue,
            str(src),
            str(dest_dir),
            "Lossless.flac",
            PipelineOptions(convert_lossless=True),
        )

    # RASTATIME 2026-10-28 - the failure record (reason for the Upload page)
    # is the only thing in the queue
    record = queue.get_nowait()
    assert record["import_status"] == 2 and "disk full" in record["comments"]
    assert queue.empty()
    assert [p.name for p in src_dir.iterdir()] == [src.name]  # no MP3 left over
    assert src.read_bytes() == data


def test_pipeline_options_convert_lossless():
    # an import message without the key (older legacy app) converts nothing
    assert PipelineOptions().convert_lossless is False
    assert PipelineOptions(**{"analyze_cue_points": True}).convert_lossless is False
    assert PipelineOptions(
        **{"analyze_cue_points": True, "convert_lossless": True}
    ).convert_lossless


# RASTATIME 2026-11-09 - the Media Type tag (ID3 TMED) sets the track type
TYPES = [
    {"id": 2, "code": "music", "name": "Music", "analyze_cue_points": True},
    {"id": 3, "code": "jngl", "name": "Jingles", "analyze_cue_points": True},
    {"id": 4, "code": "news", "name": "News", "analyze_cue_points": False},
]


def test_pipeline_options_track_types():
    # an import message without the key (older legacy app): no track types
    assert PipelineOptions().track_types == []
    options = PipelineOptions(**{"analyze_cue_points": True, "track_types": TYPES})
    assert [t.code for t in options.track_types] == ["music", "jngl", "news"]
    nameless = PipelineOptions(track_types=[{"id": 6, "code": "recs", "name": None}])
    assert nameless.track_types[0].name is None


@pytest.mark.parametrize(
    "raw, code",
    [("Jingles", "jngl"), ("jngl", "jngl"), ("NEWS", "news"), ("CD", None), ("", None)],
)
def test_tagged_track_type(raw, code):
    metadata = {"media_type": raw, "track_title": "x"}
    found = tagged_track_type(metadata, PipelineOptions(track_types=TYPES), "x.mp3")
    assert (found.code if found else None) == code
    assert metadata == {"track_title": "x"}  # the raw text never reaches the callback


def test_tagged_track_type_needs_the_types():
    metadata = {"media_type": "Jingles"}
    assert tagged_track_type(metadata, PipelineOptions(), "x.mp3") is None
    assert "media_type" not in metadata


def _run_tagged(tmp_path: Path, dest_dir: Path, monkeypatch, tmed: str, options: PipelineOptions):
    from mutagen.id3 import ID3, TMED

    from ._synth import sine

    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    src = sine(src_dir / "7-Tagged.mp3", "-c:a", "libmp3lame")
    id3 = ID3(src)
    id3.add(TMED(encoding=3, text=tmed))
    id3.save(src)
    cue_calls = []

    def fake_cuepoint(path, metadata):
        cue_calls.append(path)
        return metadata

    monkeypatch.setattr(pipeline_module, "analyze_cuepoint", fake_cuepoint)
    queue = Queue()
    Pipeline.run_analysis(queue, str(src), str(dest_dir), "Tagged.mp3", options)
    return queue.get(), cue_calls


@requires_ffmpeg
def test_tag_type_decides_the_cue_points(tmp_path: Path, dest_dir: Path, monkeypatch):
    # uploaded as News (no cue points), tagged Jingles (cue points)
    metadata, cue_calls = _run_tagged(
        tmp_path,
        dest_dir,
        monkeypatch,
        "Jingles",
        PipelineOptions(analyze_cue_points=False, track_types=TYPES),
    )
    assert metadata["track_type_code"] == "jngl"
    assert "media_type" not in metadata
    assert len(cue_calls) == 1


@requires_ffmpeg
def test_tag_type_can_switch_cue_points_off(tmp_path: Path, dest_dir: Path, monkeypatch):
    metadata, cue_calls = _run_tagged(
        tmp_path,
        dest_dir,
        monkeypatch,
        "news",
        PipelineOptions(analyze_cue_points=True, track_types=TYPES),
    )
    assert metadata["track_type_code"] == "news"
    assert cue_calls == []


@requires_ffmpeg
def test_unknown_tag_keeps_the_upload_type(tmp_path: Path, dest_dir: Path, monkeypatch):
    metadata, cue_calls = _run_tagged(
        tmp_path,
        dest_dir,
        monkeypatch,
        "Digital Media",
        PipelineOptions(analyze_cue_points=True, track_types=TYPES),
    )
    assert "track_type_code" not in metadata
    assert "media_type" not in metadata
    assert len(cue_calls) == 1


# ---- RASTATIME 2026-11-13: loudness analysis per track type --------------


def test_analyze_loudness_option_defaults_to_measuring():
    assert PipelineOptions().analyze_loudness is True  # an old message
    assert PipelineOptions(analyze_loudness=False).analyze_loudness is False
    types = PipelineOptions(track_types=TYPES).track_types
    assert all(t.analyze_loudness for t in types)  # types sent without the key
    spots = PipelineOptions(
        track_types=[{"id": 9, "code": "spot", "name": "Spots", "analyze_loudness": False}]
    )
    assert spots.track_types[0].analyze_loudness is False


def _run_measured(tmp_path: Path, dest_dir: Path, monkeypatch, options: PipelineOptions, tmed=None):
    from mutagen.id3 import ID3, TMED

    from ._synth import sine

    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    src = sine(src_dir / "8-Spot.mp3", "-c:a", "libmp3lame")
    if tmed is not None:
        id3 = ID3(src)
        id3.add(TMED(encoding=3, text=tmed))
        id3.save(src)
    calls = []

    def fake_replaygain(path, metadata):
        calls.append("replaygain")
        metadata["replay_gain"] = "1.0"
        return metadata

    def fake_loudness(path, metadata):
        calls.append("loudness")
        metadata["loudness_lufs"] = -20.0
        return metadata

    monkeypatch.setattr(pipeline_module, "analyze_replaygain", fake_replaygain)
    monkeypatch.setattr(pipeline_module, "analyze_loudness", fake_loudness)
    queue = Queue()
    Pipeline.run_analysis(queue, str(src), str(dest_dir), "Spot.mp3", options)
    return queue.get(), calls


@requires_ffmpeg
def test_upload_type_with_the_loudness_analysis_off_measures_nothing(
    tmp_path: Path, dest_dir: Path, monkeypatch
):
    metadata, calls = _run_measured(
        tmp_path, dest_dir, monkeypatch, PipelineOptions(analyze_loudness=False)
    )
    assert calls == []
    assert "replay_gain" not in metadata
    assert "loudness_lufs" not in metadata
    assert metadata["import_status"] == 0  # imported all the same


@requires_ffmpeg
def test_measuring_is_the_default(tmp_path: Path, dest_dir: Path, monkeypatch):
    metadata, calls = _run_measured(tmp_path, dest_dir, monkeypatch, PipelineOptions())
    assert calls == ["replaygain", "loudness"]
    assert metadata["loudness_lufs"] == -20.0


@requires_ffmpeg
def test_tag_type_decides_the_loudness_analysis(tmp_path: Path, dest_dir: Path, monkeypatch):
    types = [
        {"id": 2, "code": "music", "name": "Music", "analyze_cue_points": True},
        {"id": 9, "code": "spot", "name": "Spots", "analyze_loudness": False},
    ]
    # uploaded as a measuring type, tagged as the type with the analysis off
    metadata, calls = _run_measured(
        tmp_path, dest_dir, monkeypatch, PipelineOptions(track_types=types), tmed="Spots"
    )
    assert metadata["track_type_code"] == "spot"
    assert calls == []


@requires_ffmpeg
def test_tag_type_can_switch_the_loudness_analysis_back_on(
    tmp_path: Path, dest_dir: Path, monkeypatch
):
    types = [
        {"id": 2, "code": "music", "name": "Music", "analyze_cue_points": True},
        {"id": 9, "code": "spot", "name": "Spots", "analyze_loudness": False},
    ]
    metadata, calls = _run_measured(
        tmp_path,
        dest_dir,
        monkeypatch,
        PipelineOptions(analyze_loudness=False, track_types=types),
        tmed="music",
    )
    assert metadata["track_type_code"] == "music"
    assert calls == ["replaygain", "loudness"]


@requires_ffmpeg
def test_truncated_file_is_refused_with_its_reason(tmp_path: Path, dest_dir: Path):
    # RASTATIME 2026-11-21 - a file that decodes well short of its declared
    # length is a failed import; the reason reaches the Upload page and the
    # file stays where it was (nothing filed in the library).
    from rastatime_analyzer.pipeline.analyze_playability import TruncatedFileError

    from ._synth import sine

    src_dir = tmp_path / "organize"
    src_dir.mkdir()
    full = sine(tmp_path / "full.mp3", "-c:a", "libmp3lame", "-b:a", "128k", seconds=30)
    src = src_dir / "Cut.mp3"
    data = full.read_bytes()
    src.write_bytes(data[: len(data) * 4 // 10])
    queue = Queue()

    with pytest.raises(TruncatedFileError):
        Pipeline.run_analysis(queue, str(src), str(dest_dir), "Cut.mp3", PipelineOptions())

    record = queue.get_nowait()
    assert record["import_status"] == 2
    assert record["comments"].startswith("The file could not be played: it decodes only")
    assert "of its 30.0 s (damaged or cut short)" in record["comments"]
    assert queue.empty()
    assert [p.name for p in src_dir.iterdir()] == ["Cut.mp3"]
    assert not any(dest_dir.rglob("*.mp3"))
