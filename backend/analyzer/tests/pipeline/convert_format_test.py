"""
RASTATIME 2026-10-14 - format normalization: raw ADTS -> M4A (always),
lossless -> MP3 320 kbps (convert_lossless), fallback to the original.
"""

import os
import subprocess
from pathlib import Path

import pytest

from rastatime_analyzer.pipeline import _ffmpeg, convert_format as cf
from rastatime_analyzer.pipeline.analyze_metadata import analyze_metadata
from rastatime_analyzer.pipeline.convert_format import (
    AudioProbe,
    ConversionError,
    convert_format,
    is_lossless,
    is_raw_adts,
    is_wma,
    probe_audio,
    remux_adts_to_m4a,
    transcode_to_mp3,
)

from ._synth import (
    SECONDS,
    audio_stream,
    flac_with_cover,
    png_cover,
    raw_adts,
    raw_adts_with_id3,
    requires_ffmpeg,
    sine,
)

TAGS = {
    "track_title": "Tïtle",
    "artist_name": "Ärtist",
    "album_title": "Älbum",
    "genre": "Reggae",
    "comment": "A comment",
    "comments": "A comment",
    "description": "A comment",
    "year": "2001",
    "track_number": "2",
    "track_total": "9",
    "composer": "Composer",
    "copyright": "(c) 2001",
    "label": "Label",
    "isrc": "ATXX00000001",
    "bpm": "123",
    "language": "deu",
    "expires_at": "2027-02-28",
}


def _probe(**overrides) -> AudioProbe:
    values = {
        "codec": "flac",
        "format_name": "flac",
        "sample_rate": 44100,
        "channels": 2,
        "bits": 16,
        "has_cover": False,
        "cover_codec": None,
    }
    values.update(overrides)
    return AudioProbe(**values)


@pytest.mark.parametrize(
    "codec,expected",
    [
        ("flac", True),
        ("alac", True),
        ("wavpack", True),
        ("ape", True),
        ("tta", True),
        ("pcm_s16le", True),
        ("pcm_s24le", True),
        ("pcm_f32le", True),
        ("mp3", False),
        ("aac", False),
        ("vorbis", False),
        ("opus", False),
    ],
)
def test_is_lossless(codec, expected):
    assert is_lossless(_probe(codec=codec)) is expected


def test_is_raw_adts():
    assert is_raw_adts(_probe(codec="aac", format_name="aac"))
    assert not is_raw_adts(_probe(codec="aac", format_name="mov,mp4,m4a,3gp,3g2,mj2"))


@pytest.mark.parametrize(
    "codec,expected",
    [("wmav2", True), ("wmav1", True), ("wmapro", True), ("wmalossless", True), ("mp3", False), ("flac", False)],
)
def test_is_wma(codec, expected):
    assert is_wma(_probe(codec=codec, format_name="asf")) is expected


@requires_ffmpeg
@pytest.mark.parametrize("convert_lossless", [True, False])
def test_wma_is_always_transcoded_to_mp3(tmp_path: Path, convert_lossless: bool):
    """RASTATIME 2026-10-21 - Windows Media Audio becomes MP3 320 whether the
    lossless checkbox is on or off; the original stays for the caller."""
    src = sine(tmp_path / "song.wma", "-c:a", "wmav2", "-b:a", "128k")
    metadata = analyze_metadata(str(src), {})
    metadata["md5"] = "0123456789abcdef0123456789abcdef"

    new_path, new_name, result = convert_format(
        str(src), "song.wma", metadata, convert_lossless=convert_lossless
    )

    assert new_name == "song.mp3"
    assert Path(new_path).suffix == ".mp3" and Path(new_path).exists()
    assert src.exists()  # the caller removes the original
    stream = audio_stream(Path(new_path))
    assert stream["codec_name"] == "mp3"
    assert int(stream["bit_rate"]) >= 300000
    assert result["source_md5"] == metadata["md5"]


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Song.flac", "Song.mp3"),
        ("Song.FLAC", "Song.mp3"),
        ("12-Song.wav", "12-Song.mp3"),
        ("Live 1.2 Mix", "Live 1.2 Mix.mp3"),
        ("NoSuffix", "NoSuffix.mp3"),
    ],
)
def test_with_suffix(name, expected):
    assert cf._with_suffix(name, ".mp3") == expected  # pylint: disable=protected-access


@requires_ffmpeg
def test_probe_audio_flac_with_cover(tmp_path: Path):
    path = flac_with_cover(tmp_path / "c.flac", png_cover(tmp_path / "c.png"))

    probe = probe_audio(path)

    assert probe.codec == "flac"
    assert probe.format_name == "flac"
    assert probe.sample_rate == 44100
    assert probe.channels == 2
    assert probe.bits == 16
    assert probe.has_cover
    assert probe.cover_codec == "png"
    assert probe.duration == pytest.approx(SECONDS, abs=0.1)


@requires_ffmpeg
def test_probe_audio_unreadable(tmp_path: Path):
    path = tmp_path / "broken.flac"
    path.write_bytes(b"fLaC" + os.urandom(2000))

    with pytest.raises(ConversionError):
        probe_audio(path)


@requires_ffmpeg
def test_flac_with_cover_to_mp3_keeps_cover_and_tags(tmp_path: Path):
    from mutagen.id3 import ID3

    src = flac_with_cover(
        tmp_path / "17-Song.flac",
        png_cover(tmp_path / "cover.png"),
        "-metadata",
        "title=Flac Title",
    )
    metadata = analyze_metadata(str(src), {})
    metadata.update(TAGS)
    original_md5 = metadata["md5"]

    new_path, new_name, result = convert_format(
        str(src), "Song.flac", metadata, convert_lossless=True
    )

    assert new_path == str(tmp_path / "17-Song.mp3")
    assert new_name == "Song.mp3"
    # the original stays until the pipeline has filed the MP3 (remove_original)
    assert src.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["17-Song.flac", "17-Song.mp3", "cover.png"]

    assert result["source_md5"] == original_md5
    assert result["md5"] != original_md5 and len(result["md5"]) == 32
    assert result["mime"] == "audio/mp3"
    assert result["bit_rate"] == 320000
    assert result["sample_rate"] == 44100
    assert result["channels"] == 2
    assert result["filesize"] == Path(new_path).stat().st_size
    assert result["length_seconds"] == pytest.approx(SECONDS, abs=0.1)
    assert result["track_title"] == TAGS["track_title"]

    id3 = ID3(new_path)
    assert id3.version == (2, 3, 0)
    assert str(id3["TIT2"]) == "Tïtle"
    assert str(id3["TPE1"]) == "Ärtist"
    assert str(id3["TALB"]) == "Älbum"
    assert str(id3["TCON"]) == "Reggae"
    assert str(id3["COMM::eng"]) == "A comment"
    assert str(id3["TDRC"]) == "2001"
    assert str(id3["TRCK"]) == "2/9"
    assert str(id3["TCOM"]) == "Composer"
    assert str(id3["TCOP"]) == "(c) 2001"
    assert str(id3["TPUB"]) == "Label"
    assert str(id3["TSRC"]) == "ATXX00000001"
    assert str(id3["TBPM"]) == "123"
    assert str(id3["TLAN"]) == "deu"
    assert str(id3["TXXX:Expiry"]) == "2027-02-28"
    pictures = id3.getall("APIC")
    assert len(pictures) == 1
    assert pictures[0].mime == "image/png"
    assert pictures[0].type == 3  # front cover
    assert pictures[0].data == (tmp_path / "cover.png").read_bytes()

    # the import reads the new file back the same way
    again = analyze_metadata(new_path, {})
    for key in ("track_title", "artist_name", "album_title", "isrc", "label", "expires_at"):
        assert again[key] == TAGS[key]


@requires_ffmpeg
def test_hires_flac_is_resampled_to_44100(tmp_path: Path):
    src = sine(
        tmp_path / "hi.flac",
        *("-c:a", "flac"),
        *("-sample_fmt", "s32"),
        sample_rate=96000,
    )
    assert probe_audio(src).bits == 24

    new_path, _, result = convert_format(str(src), "hi.flac", analyze_metadata(str(src), {}), convert_lossless=True)

    assert new_path.endswith(".mp3")
    stream = audio_stream(Path(new_path))
    assert stream["codec_name"] == "mp3"
    assert int(stream["sample_rate"]) == 44100
    assert result["sample_rate"] == 44100


@requires_ffmpeg
@pytest.mark.parametrize("sample_rate", [32000, 48000])
def test_mp3_sample_rates_are_kept(tmp_path: Path, sample_rate: int):
    src = sine(tmp_path / "keep.wav", sample_rate=sample_rate)

    new_path, _, _ = convert_format(str(src), "keep.wav", analyze_metadata(str(src), {}), convert_lossless=True)

    assert int(audio_stream(Path(new_path))["sample_rate"]) == sample_rate


@requires_ffmpeg
def test_surround_is_downmixed_mono_is_kept(tmp_path: Path):
    surround = sine(tmp_path / "surround.flac", channels=6)
    mono = sine(tmp_path / "mono.wav", channels=1)

    surround_path, _, _ = convert_format(str(surround), "s.flac", analyze_metadata(str(surround), {}), convert_lossless=True)
    mono_path, _, _ = convert_format(str(mono), "m.wav", analyze_metadata(str(mono), {}), convert_lossless=True)

    assert audio_stream(Path(surround_path))["channels"] == 2
    assert audio_stream(Path(mono_path))["channels"] == 1


@requires_ffmpeg
def test_wav_and_alac_are_transcoded(tmp_path: Path):
    wav = sine(tmp_path / "w.wav")
    alac = sine(tmp_path / "a.m4a", "-c:a", "alac")

    for src, name in ((wav, "w.wav"), (alac, "a.m4a")):
        new_path, new_name, result = convert_format(str(src), name, analyze_metadata(str(src), {}), convert_lossless=True)
        assert new_name == Path(name).stem + ".mp3"
        assert audio_stream(Path(new_path))["codec_name"] == "mp3"
        assert result["mime"] == "audio/mp3"
        assert src.exists()  # removed by the pipeline after organise_file


@requires_ffmpeg
def test_convert_lossless_false_leaves_flac_untouched(tmp_path: Path):
    src = sine(tmp_path / "keep.flac")
    metadata = analyze_metadata(str(src), {})
    before = dict(metadata)

    result = convert_format(str(src), "keep.flac", metadata, convert_lossless=False)

    assert result == (str(src), "keep.flac", before)
    assert src.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["keep.flac"]


@requires_ffmpeg
@pytest.mark.parametrize(
    "name,args",
    [
        ("lossy.mp3", ("-c:a", "libmp3lame", "-b:a", "128k")),
        ("lossy.ogg", ("-c:a", "libvorbis")),
        ("lossy.opus", ("-c:a", "libopus")),
        ("lossy.m4a", ("-c:a", "aac")),
    ],
)
def test_lossy_files_are_never_reencoded(tmp_path: Path, name: str, args):
    src = sine(tmp_path / name, *args)
    data = src.read_bytes()
    metadata = analyze_metadata(str(src), {})

    new_path, new_name, result = convert_format(str(src), name, metadata, convert_lossless=True)

    assert (new_path, new_name) == (str(src), name)
    assert result is metadata
    assert "source_md5" not in result
    assert src.read_bytes() == data
    assert [p.name for p in tmp_path.iterdir()] == [name]


@requires_ffmpeg
@pytest.mark.parametrize("convert_lossless", [True, False])
def test_raw_adts_is_always_repacked_to_m4a(tmp_path: Path, convert_lossless: bool):
    from mutagen.id3 import TIT2, TPE1, TXXX
    from mutagen.mp4 import MP4

    src = raw_adts_with_id3(
        tmp_path / "5-show.aac",
        [
            TIT2(encoding=3, text="Aac Title"),
            TPE1(encoding=3, text="Aac Artist"),
            TXXX(encoding=3, desc="Expiry", text="2027-03-31"),
        ],
    )
    source_stream = audio_stream(src)
    metadata = analyze_metadata(str(src), {})
    original_md5 = metadata["md5"]

    new_path, new_name, result = convert_format(str(src), "show.aac", metadata, convert_lossless=convert_lossless)

    assert new_path == str(tmp_path / "5-show.m4a")
    assert new_name == "show.m4a"
    assert src.exists()  # removed by the pipeline after organise_file
    stream = audio_stream(Path(new_path))
    assert stream["codec_name"] == "aac"
    assert stream["sample_rate"] == source_stream["sample_rate"]  # stream copy
    assert result["source_md5"] == original_md5
    assert result["mime"] == "audio/mp4"
    assert result["length_seconds"] == pytest.approx(SECONDS, abs=0.1)

    mp4 = MP4(new_path)
    assert mp4["©nam"] == ["Aac Title"]
    assert mp4["©ART"] == ["Aac Artist"]
    assert bytes(mp4["----:com.apple.iTunes:Expiry"][0]) == b"2027-03-31"
    assert analyze_metadata(new_path, {})["expires_at"] == "2027-03-31"


@requires_ffmpeg
def test_raw_adts_is_detected_by_content_not_extension(tmp_path: Path):
    src = raw_adts(tmp_path / "misnamed.mp3")

    new_path, new_name, _ = convert_format(str(src), "misnamed.mp3", analyze_metadata(str(src), {}), convert_lossless=False)

    assert new_path == str(tmp_path / "misnamed.m4a")
    assert new_name == "misnamed.m4a"


@requires_ffmpeg
def test_remux_adts_to_m4a_writes_tags(tmp_path: Path):
    from mutagen.mp4 import MP4

    src = raw_adts(tmp_path / "plain.aac")
    dest = tmp_path / "plain.m4a"

    remux_adts_to_m4a(src, dest, TAGS)

    mp4 = MP4(dest)
    assert mp4["©nam"] == ["Tïtle"]
    assert mp4["©ART"] == ["Ärtist"]
    assert mp4["©alb"] == ["Älbum"]
    assert mp4["trkn"] == [(2, 9)]
    assert mp4["tmpo"] == [123]
    assert bytes(mp4["----:com.apple.iTunes:ISRC"][0]) == b"ATXX00000001"
    assert src.exists()  # the source is never touched here


@requires_ffmpeg
def test_output_name_clash_gets_a_unique_name(tmp_path: Path):
    src = sine(tmp_path / "clash.flac")
    (tmp_path / "clash.mp3").write_bytes(b"someone else's file")

    new_path, new_name, _ = convert_format(str(src), "clash.flac", analyze_metadata(str(src), {}), convert_lossless=True)

    assert new_path != str(tmp_path / "clash.mp3")
    assert Path(new_path).name.startswith("clash_") and new_path.endswith(".mp3")
    assert new_name == "clash.mp3"
    assert (tmp_path / "clash.mp3").read_bytes() == b"someone else's file"


@requires_ffmpeg
def test_missing_ffmpeg_falls_back_to_the_original(tmp_path: Path, monkeypatch):
    src = sine(tmp_path / "fallback.flac")
    data = src.read_bytes()
    metadata = analyze_metadata(str(src), {})
    before = dict(metadata)
    monkeypatch.setattr(_ffmpeg, "FFMPEG", str(tmp_path / "no-such-ffmpeg.exe"))

    result = convert_format(str(src), "fallback.flac", metadata, convert_lossless=True)

    assert result == (str(src), "fallback.flac", before)
    assert src.read_bytes() == data
    assert [p.name for p in tmp_path.iterdir()] == ["fallback.flac"]


@requires_ffmpeg
def test_corrupt_file_falls_back_to_the_original(tmp_path: Path):
    src = tmp_path / "corrupt.flac"
    src.write_bytes(b"fLaC" + os.urandom(5000))
    metadata = {"md5": "x" * 32}

    result = convert_format(str(src), "corrupt.flac", metadata, convert_lossless=True)

    assert result == (str(src), "corrupt.flac", {"md5": "x" * 32})
    assert [p.name for p in tmp_path.iterdir()] == ["corrupt.flac"]


@requires_ffmpeg
def test_failed_transcode_leaves_no_partial_file(tmp_path: Path, monkeypatch):
    src = sine(tmp_path / "partial.wav")
    probe = probe_audio(src)

    def broken_tags(*_args, **_kwargs):
        raise RuntimeError("tag writer broke")

    monkeypatch.setattr(cf, "_write_id3_tags", broken_tags)

    with pytest.raises(ConversionError):
        transcode_to_mp3(src, tmp_path / "partial.mp3", TAGS, probe=probe)

    assert [p.name for p in tmp_path.iterdir()] == ["partial.wav"]


@requires_ffmpeg
def test_truncated_output_is_rejected(tmp_path: Path, monkeypatch):
    src = sine(tmp_path / "long.wav")
    probe = probe_audio(src)
    probe.duration = SECONDS + 30.0  # the encode comes out 30 s "short"

    with pytest.raises(ConversionError):
        transcode_to_mp3(src, tmp_path / "long.mp3", TAGS, probe=probe)

    assert [p.name for p in tmp_path.iterdir()] == ["long.wav"]


@requires_ffmpeg
def test_subprocesses_run_below_normal_with_a_timeout(tmp_path: Path, monkeypatch):
    src = sine(tmp_path / "prio.wav")
    calls = []
    real_run = subprocess.run

    def spy(cmd, *args, **kwargs):
        calls.append((Path(cmd[0]).stem.lower(), kwargs))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)

    convert_format(str(src), "prio.wav", {"md5": "x" * 32}, convert_lossless=True)

    assert {name for name, _ in calls} >= {"ffmpeg", "ffprobe"}
    expected_flags = 0x00004000 if os.name == "nt" else 0
    for name, kwargs in calls:
        assert kwargs.get("creationflags") == expected_flags, name
        assert kwargs.get("timeout"), name
    ffmpeg_timeouts = [kwargs["timeout"] for name, kwargs in calls if name == "ffmpeg"]
    assert min(ffmpeg_timeouts) >= 120


@requires_ffmpeg
def test_non_ascii_file_names(tmp_path: Path):
    folder = tmp_path / "Ärger & Söhne"
    folder.mkdir()
    src = sine(folder / "7-Café Olé – 夜.flac")

    new_path, new_name, result = convert_format(
        str(src), "Café Olé – 夜.flac", analyze_metadata(str(src), {}), convert_lossless=True
    )

    assert new_path == str(folder / "7-Café Olé – 夜.mp3")
    assert new_name == "Café Olé – 夜.mp3"
    assert result["mime"] == "audio/mp3"
    cf.remove_original(src)
    assert not src.exists()


# RASTATIME 2026-10-14 - review fixes


@requires_ffmpeg
def test_untagged_file_gets_its_new_name_as_title(tmp_path: Path):
    # createAndImport titled the row "Bare Track.flac"; the analyzer must
    # not leave the old extension in the title of what is now an MP3
    src = sine(tmp_path / "9-Bare Track.flac")
    metadata = analyze_metadata(str(src), {})
    assert "track_title" not in metadata

    _, new_name, result = convert_format(str(src), "Bare Track.flac", metadata, convert_lossless=True)

    assert new_name == "Bare Track.mp3"
    assert result["track_title"] == "Bare Track.mp3"


@requires_ffmpeg
def test_a_title_tag_is_kept(tmp_path: Path):
    src = sine(tmp_path / "t.flac", "-metadata", "title=Real Title")

    _, _, result = convert_format(str(src), "t.flac", analyze_metadata(str(src), {}), convert_lossless=True)

    assert result["track_title"] == "Real Title"


@requires_ffmpeg
def test_encoder_describes_the_new_file(tmp_path: Path):
    src = sine(tmp_path / "enc.flac")
    metadata = analyze_metadata(str(src), {})
    metadata["encoder"] = "reference libFLAC 1.4.3 20230623"

    _, _, result = convert_format(str(src), "enc.flac", metadata, convert_lossless=True)

    assert result.get("encoder") != "reference libFLAC 1.4.3 20230623"


def test_remove_original_and_discard_converted(tmp_path: Path):
    original = tmp_path / "o.flac"
    converted = tmp_path / "o.mp3"
    original.write_bytes(b"x")
    converted.write_bytes(b"y")

    cf.remove_original(original)
    cf.discard_converted(converted)
    # both are quiet when the file is already gone
    cf.remove_original(original)
    cf.discard_converted(converted)

    assert list(tmp_path.iterdir()) == []


def test_replace_retries_a_briefly_locked_file(tmp_path: Path, monkeypatch):
    tmp = tmp_path / "a.part-1.mp3"
    dest = tmp_path / "a.mp3"
    tmp.write_bytes(b"mp3")
    real_replace = os.replace
    calls = []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 1:
            raise PermissionError("held by a virus scanner")
        real_replace(src, dst)

    monkeypatch.setattr(cf.os, "replace", flaky)
    monkeypatch.setattr(cf, "_UNLINK_RETRY_S", 0)

    cf._replace(tmp, dest)

    assert len(calls) == 2
    assert dest.read_bytes() == b"mp3" and not tmp.exists()
