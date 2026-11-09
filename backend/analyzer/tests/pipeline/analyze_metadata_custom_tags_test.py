"""
RASTATIME 2026-11-08 - the custom tags read on import: "Expiry" /
"Expiry Date", "Enable Date" / "Enabled From" and "Country", in any
spelling of the name, with the dates as YYYY-MM-DD or YYYYMMDD; since
2026-11-09 the "Media Type" (ID3 TMED, MEDIATYPE / MEDIA elsewhere).
"""

import logging
from pathlib import Path

import pytest
from rastatime_analyzer.pipeline.analyze_metadata import (
    _custom_tag_values,
    analyze_metadata,
    read_custom_tags,
)

from ._synth import requires_ffmpeg, sine


@pytest.mark.parametrize(
    "name",
    ["Expiry", "Expiry Date", "EXPIRY DATE", "expiry_date", "Expiry-Date", "expirydate"],
)
def test_expiry_names(name: str):
    assert _custom_tag_values([(name, "2027-01-31")], Path("x.mp3")) == {"expires_at": "2027-01-31"}


@pytest.mark.parametrize("name", ["Enable Date", "ENABLE_DATE", "Enabled From", "enabledfrom"])
def test_enable_names(name: str):
    assert _custom_tag_values([(name, "20270115")], Path("x.mp3")) == {"enabled_from": "2027-01-15"}


@pytest.mark.parametrize("raw", ["2027-01-31", "20270131", " 2027-01-31 "])
def test_both_date_formats(raw: str):
    assert _custom_tag_values([("Expiry", raw)], Path("x.mp3"))["expires_at"] == "2027-01-31"


@pytest.mark.parametrize(
    "raw",
    [
        "31.01.2027",
        "2027-1-31",
        "2027131",
        "2027-02-30",
        "20271340",
        "next week",
        "2027-01-31 10:00",
    ],
)
def test_other_values_are_no_date(raw: str, caplog):
    with caplog.at_level(logging.WARNING):
        assert not _custom_tag_values([("Expiry Date", raw)], Path("x.mp3"))
    assert "no date" in caplog.text


def test_first_usable_value_wins():
    pairs = [
        ("Expiry", "soon"),
        ("Expiry Date", "20270131"),
        ("Expiry", "2028-01-01"),
        ("Country", "  "),
        ("COUNTRY", "Germany /  Switzerland"),
        ("Country", "Austria"),
        ("MusicBrainz Album Release Country", "AT"),
        ("Enable", "2027-01-01"),
    ]
    assert _custom_tag_values(pairs, Path("x.mp3")) == {
        "expires_at": "2027-01-31",
        "country": "Germany / Switzerland",
    }


def _mp3_with_txxx(path: Path, frames: dict[str, str]) -> Path:
    from mutagen.id3 import ID3, TXXX

    sine(path, "-c:a", "libmp3lame")
    id3 = ID3(path)
    for desc, text in frames.items():
        id3.add(TXXX(encoding=3, desc=desc, text=text))
    id3.save(path)
    return path


@requires_ffmpeg
def test_mp3_txxx(tmp_path: Path):
    path = _mp3_with_txxx(
        tmp_path / "notice.mp3",
        {"Expiry Date": "20270131", "Enable Date": "2027-01-15", "COUNTRY": "Austria"},
    )

    found = analyze_metadata(str(path), {})

    assert found["expires_at"] == "2027-01-31"
    assert found["enabled_from"] == "2027-01-15"
    assert found["country"] == "Austria"
    assert read_custom_tags(str(path)) == {
        "expires_at": "2027-01-31",
        "enabled_from": "2027-01-15",
        "country": "Austria",
    }


@requires_ffmpeg
def test_mp3_invalid_date_warns_once(tmp_path: Path, caplog):
    path = _mp3_with_txxx(tmp_path / "bad.mp3", {"Expiry Date": "31.01.2027"})

    with caplog.at_level(logging.WARNING):
        found = analyze_metadata(str(path), {})

    assert "expires_at" not in found
    assert caplog.text.count("no date") == 1


@requires_ffmpeg
def test_flac_vorbis_comments(tmp_path: Path):
    path = sine(
        tmp_path / "notice.flac",
        *("-metadata", "EXPIRY DATE=20270228"),
        *("-metadata", "ENABLE DATE=20270201"),
        *("-metadata", "COUNTRY=UK"),
    )

    found = analyze_metadata(str(path), {})

    assert found["expires_at"] == "2027-02-28"
    assert found["enabled_from"] == "2027-02-01"
    assert found["country"] == "UK"
    assert read_custom_tags(str(path)) == {
        "expires_at": "2027-02-28",
        "enabled_from": "2027-02-01",
        "country": "UK",
    }


@requires_ffmpeg
def test_m4a_freeform(tmp_path: Path):
    from mutagen.mp4 import MP4, MP4FreeForm

    path = sine(tmp_path / "f.m4a", "-c:a", "aac")
    mp4 = MP4(path)
    mp4["----:com.apple.iTunes:Enable Date"] = [MP4FreeForm(b"20270401")]
    mp4["----:com.apple.iTunes:COUNTRY"] = [MP4FreeForm(b"USA")]
    mp4.save()

    found = analyze_metadata(str(path), {})

    assert found["enabled_from"] == "2027-04-01"
    assert found["country"] == "USA"
    assert "expires_at" not in found
    assert read_custom_tags(str(path)) == {"enabled_from": "2027-04-01", "country": "USA"}


@requires_ffmpeg
def test_long_country_is_cut_to_the_column_length(tmp_path: Path):
    path = _mp3_with_txxx(tmp_path / "long.mp3", {"Country": "X" * 80})

    assert analyze_metadata(str(path), {})["country"] == "X" * 64


def test_unreadable_file_has_no_custom_tags(tmp_path: Path):
    path = tmp_path / "empty.mp3"
    path.write_bytes(b"")

    assert not read_custom_tags(str(path))


# RASTATIME 2026-11-09 - Media Type (the track type on import)
@pytest.mark.parametrize(
    "name", ["TMED", "tmed", "Media Type", "MEDIATYPE", "media_type", "MEDIA", "media"]
)
def test_media_type_names(name: str):
    assert _custom_tag_values([(name, " Jingles ")], Path("x.mp3")) == {"media_type": "Jingles"}


def _mp3_with_frames(path: Path, frames: list) -> Path:
    from mutagen.id3 import ID3

    sine(path, "-c:a", "libmp3lame")
    id3 = ID3(path)
    for frame in frames:
        id3.add(frame)
    id3.save(path)
    return path


@requires_ffmpeg
def test_mp3_tmed(tmp_path: Path):
    from mutagen.id3 import TMED

    path = _mp3_with_frames(tmp_path / "jingle.mp3", [TMED(encoding=3, text="Jingles")])

    assert analyze_metadata(str(path), {})["media_type"] == "Jingles"
    assert read_custom_tags(str(path)) == {"media_type": "Jingles"}


@requires_ffmpeg
def test_mp3_tmed_wins_over_a_txxx_of_the_same_name(tmp_path: Path):
    from mutagen.id3 import TMED, TXXX

    path = _mp3_with_frames(
        tmp_path / "both.mp3",
        [TXXX(encoding=3, desc="MEDIATYPE", text="Music"), TMED(encoding=3, text="news")],
    )

    assert analyze_metadata(str(path), {})["media_type"] == "news"


@requires_ffmpeg
def test_mp3_empty_tmed_is_absent(tmp_path: Path):
    from mutagen.id3 import TMED

    path = _mp3_with_frames(tmp_path / "empty.mp3", [TMED(encoding=3, text=" ")])

    assert "media_type" not in analyze_metadata(str(path), {})


@requires_ffmpeg
def test_flac_mediatype(tmp_path: Path):
    path = sine(tmp_path / "n.flac", *("-metadata", "MEDIATYPE=News"))

    assert analyze_metadata(str(path), {})["media_type"] == "News"


@requires_ffmpeg
def test_m4a_mediatype_freeform(tmp_path: Path):
    from mutagen.mp4 import MP4, MP4FreeForm

    path = sine(tmp_path / "a.m4a", "-c:a", "aac")
    mp4 = MP4(path)
    mp4["----:com.apple.iTunes:MEDIATYPE"] = [MP4FreeForm(b"ads")]
    mp4.save()

    assert analyze_metadata(str(path), {})["media_type"] == "ads"


@requires_ffmpeg
def test_wav_id3_chunk_tmed(tmp_path: Path):
    from mutagen.id3 import TMED
    from mutagen.wave import WAVE

    path = sine(tmp_path / "w.wav")
    wave = WAVE(path)
    wave.add_tags()
    wave.tags.add(TMED(encoding=3, text="Jingles"))
    wave.save()

    assert analyze_metadata(str(path), {})["media_type"] == "Jingles"
