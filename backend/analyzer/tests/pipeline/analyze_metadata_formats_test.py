"""
RASTATIME 2026-10-14 - tag reading in all formats: mutagen first, then the
fields still missing from ffprobe (WAV ID3 chunk, RIFF INFO, Vorbis
DESCRIPTION, MP4 freeform, raw ADTS with an ID3v2 header, Opus).
"""

from pathlib import Path

import pytest
from rastatime_analyzer.pipeline.analyze_metadata import analyze_metadata

from ._synth import SECONDS, raw_adts, raw_adts_with_id3, requires_ffmpeg, sine

pytestmark = requires_ffmpeg


def test_wav_with_id3_chunk(tmp_path: Path):
    from mutagen.id3 import (
        COMM,
        TALB,
        TBPM,
        TCOM,
        TCON,
        TCOP,
        TDRC,
        TIT2,
        TLAN,
        TPE1,
        TPUB,
        TRCK,
        TSRC,
        TXXX,
    )
    from mutagen.wave import WAVE

    path = sine(tmp_path / "id3.wav")
    wave = WAVE(path)
    wave.add_tags()
    for frame in (
        TIT2(encoding=3, text="Wav Title"),
        TPE1(encoding=3, text="Wav Artist"),
        TALB(encoding=3, text="Wav Album"),
        TCON(encoding=3, text="Reggae"),
        COMM(encoding=3, lang="eng", desc="", text="Wav Comment"),
        TDRC(encoding=3, text="2021"),
        TRCK(encoding=3, text="3/12"),
        TCOM(encoding=3, text="Wav Composer"),
        TCOP(encoding=3, text="(c) Wav"),
        TPUB(encoding=3, text="Wav Label"),
        TSRC(encoding=3, text="ATXX12345678"),
        TBPM(encoding=3, text="120"),
        TLAN(encoding=3, text="deu"),
        TXXX(encoding=3, desc="Expiry", text="2027-01-31"),
    ):
        wave.tags.add(frame)
    wave.save()

    found = analyze_metadata(str(path), {})

    assert found["mime"] == "audio/wav"
    assert found["track_title"] == "Wav Title"
    assert found["artist_name"] == "Wav Artist"
    assert found["album_title"] == "Wav Album"
    assert found["genre"] == "Reggae"
    assert found["comment"] == found["comments"] == found["description"] == "Wav Comment"
    assert found["year"] == "2021"
    assert found["track_number"] == "3"
    assert found["track_total"] == "12"
    assert found["composer"] == "Wav Composer"
    assert found["copyright"] == "(c) Wav"
    assert found["label"] == "Wav Label"
    assert found["isrc"] == "ATXX12345678"
    assert found["bpm"] == "120"
    assert found["language"] == "deu"
    assert found["expires_at"] == "2027-01-31"
    assert found["length_seconds"] == pytest.approx(SECONDS, abs=0.1)


def test_wav_with_riff_info(tmp_path: Path):
    path = sine(
        tmp_path / "info.wav",
        *("-metadata", "title=Info Title"),
        *("-metadata", "artist=Info Artist"),
        *("-metadata", "album=Info Album"),
        *("-metadata", "comment=Info Comment"),
        *("-metadata", "date=2020"),
        *("-metadata", "genre=Dub"),
        *("-metadata", "track=4"),
        *("-metadata", "copyright=(c) Info"),
    )

    found = analyze_metadata(str(path), {})

    assert found["track_title"] == "Info Title"
    assert found["artist_name"] == "Info Artist"
    assert found["album_title"] == "Info Album"
    assert found["comment"] == "Info Comment"
    assert found["year"] == "2020"
    assert found["genre"] == "Dub"
    assert found["track_number"] == "4"
    assert "track_total" not in found
    assert found["copyright"] == "(c) Info"
    assert "expires_at" not in found


def test_flac_description_and_expiry(tmp_path: Path):
    # ffmpeg writes the comment as the Vorbis comment DESCRIPTION
    path = sine(
        tmp_path / "desc.flac",
        *("-metadata", "title=Flac Title"),
        *("-metadata", "comment=Flac Comment"),
        *("-metadata", "EXPIRY=2027-02-28"),
        *("-metadata", "ISRC=ATXX00000001"),
        *("-metadata", "LABEL=Flac Label"),
        *("-metadata", "TRACKNUMBER=7"),
        *("-metadata", "TRACKTOTAL=9"),
    )

    found = analyze_metadata(str(path), {})

    assert found["mime"] == "audio/flac"
    assert found["track_title"] == "Flac Title"
    assert found["comment"] == found["comments"] == found["description"] == "Flac Comment"
    assert found["isrc"] == "ATXX00000001"
    assert found["label"] == "Flac Label"
    assert found["track_number"] == "7"
    assert found["track_total"] == "9"
    assert found["expires_at"] == "2027-02-28"


def test_flac_invalid_expiry_is_ignored(tmp_path: Path):
    path = sine(tmp_path / "bad-expiry.flac", "-metadata", "EXPIRY=next week")

    found = analyze_metadata(str(path), {})

    assert "expires_at" not in found


def test_m4a_freeform_expiry(tmp_path: Path):
    from mutagen.mp4 import MP4, MP4FreeForm

    path = sine(tmp_path / "f.m4a", "-c:a", "aac")
    mp4 = MP4(path)
    mp4["----:com.apple.iTunes:Expiry"] = [MP4FreeForm(b"2027-04-30")]
    mp4.save()

    found = analyze_metadata(str(path), {})

    assert found["mime"] == "audio/mp4"
    assert found["expires_at"] == "2027-04-30"
    # the MP4 stream language "und" (undetermined) is no language
    assert "language" not in found


def test_raw_adts_without_id3(tmp_path: Path):
    path = raw_adts(tmp_path / "raw.aac")

    found = analyze_metadata(str(path), {})

    assert found["mime"] in ("audio/x-aac", "audio/aac")
    assert found["sample_rate"] == 44100
    assert found["channels"] == 2
    assert found["length_seconds"] == pytest.approx(SECONDS, abs=0.2)


def test_raw_adts_with_id3_header_does_not_abort(tmp_path: Path):
    from mutagen.id3 import TIT2, TPE1, TXXX

    path = raw_adts_with_id3(
        tmp_path / "id3.aac",
        [
            TIT2(encoding=3, text="Aac Title"),
            TPE1(encoding=3, text="Aac Artist"),
            TXXX(encoding=3, desc="Expiry", text="2027-03-31"),
        ],
    )

    # mutagen raises HeaderNotFoundError ("can't sync to MPEG frame") here
    found = analyze_metadata(str(path), {})

    assert len(found["md5"]) == 32
    assert found["mime"] == "audio/aac"
    assert found["track_title"] == "Aac Title"
    assert found["artist_name"] == "Aac Artist"
    assert found["expires_at"] == "2027-03-31"
    assert found["sample_rate"] == 44100
    assert found["channels"] == 2
    assert found["bit_rate"] > 0
    assert found["length_seconds"] == pytest.approx(SECONDS, abs=0.2)


def test_opus_gets_sample_rate_and_bit_rate(tmp_path: Path):
    path = sine(
        tmp_path / "o.opus", "-c:a", "libopus", "-b:a", "96k", "-metadata", "title=Opus Title"
    )

    found = analyze_metadata(str(path), {})

    assert found["track_title"] == "Opus Title"
    assert found["sample_rate"] == 48000
    assert found["bit_rate"] > 0
    assert found["channels"] == 2
    assert found["length_seconds"] == pytest.approx(SECONDS, abs=0.1)


def test_long_encoder_is_cut_to_the_column_length(tmp_path: Path):
    # RASTATIME 2026-10-14 - review: cc_files.encoder is VARCHAR(64) and the
    # legacy app does not cut it; a longer TSSE failed the whole import.
    from mutagen.id3 import ID3, TENC, TSSE

    path = sine(tmp_path / "rip.mp3", "-c:a", "libmp3lame", "-b:a", "128k")
    tsse = (
        "Exact Audio Copy (Secure mode) + LAME 3.100 -V 0 --vbr-new "
        "--noreplaygain --nohist --id3v2-only"
    )
    id3 = ID3(path)
    id3.add(TSSE(encoding=3, text=tsse))
    id3.add(TENC(encoding=3, text="Some Person"))
    id3.save(path)

    found = analyze_metadata(str(path), {})

    assert len(tsse) > 64
    assert found["encoder"] == tsse[:64].rstrip()  # TSSE, the software, wins
