"""
RASTATIME 2026-10-14 - ``convert_lossless``: lossless files already in the
library become MP3 320 kbps.  The analyzer's convert_format module is
replaced by a fake (probe by magic bytes, "transcode" = copy the fixture
MP3), so the tests need neither ffmpeg nor real lossless files.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.query import QuerySet
from django.utils import timezone
from model_bakery import baker

from rastatime_api._fixtures import AUDIO_FILENAME, fixture_path
from rastatime_api.storage.management.commands import convert_lossless as cl
from rastatime_api.storage.models import File
from rastatime_shared.files import compute_md5

FIXTURE_MP3 = fixture_path / AUDIO_FILENAME
FIXTURE_LENGTH = 40.81312925170068  # mutagen, song.mp3


@dataclass
class FakeProbe:
    codec: str
    format_name: str
    sample_rate: Optional[int] = 44100
    channels: Optional[int] = 2
    bits: Optional[int] = 16
    has_cover: bool = False
    cover_codec: Optional[str] = None


class FakeConverter:
    """Stands in for rastatime_analyzer.pipeline.convert_format."""

    class ConversionError(Exception):
        pass

    def __init__(self):
        self.probed = []
        self.transcoded = []
        self.on_transcode = None

    def probe_audio(self, path: Path) -> FakeProbe:
        self.probed.append(path)
        head = path.read_bytes()[:4]
        if head == b"fLaC":
            return FakeProbe("flac", "flac")
        if head == b"RIFF":
            return FakeProbe("pcm_s16le", "wav")
        if head == b"OggS":
            return FakeProbe("vorbis", "ogg")
        raise self.ConversionError(f"cannot probe {path.name}")

    @staticmethod
    def is_lossless(probe: FakeProbe) -> bool:
        return probe.codec in ("flac", "alac", "wavpack", "ape", "tta") or probe.codec.startswith("pcm_")

    @staticmethod
    def is_wma(probe: FakeProbe) -> bool:
        # RASTATIME 2026-10-21 (5179636): the command also converts Windows
        # Media Audio; mirrors convert_format.is_wma (WMA_CODECS).
        return probe.codec.startswith("wma")

    def transcode_to_mp3(self, src, dest, tags, *, probe=None):
        self.transcoded.append((Path(src), Path(dest), dict(tags), probe))
        if self.on_transcode is not None:
            self.on_transcode(Path(src), Path(dest))
            return
        shutil.copyfile(FIXTURE_MP3, dest)


def _file(filepath, exists=True, **extra):
    now = timezone.now()
    values = dict(
        filepath=filepath, size=1, exists=exists, mime="audio/flac", md5="0" * 32,
        import_status=File.ImportStatus.SUCCESS, hidden=False, accessed=0, scheduled=False,
        part_of_list=False, disabled=False, created_at=now, updated_at=now,
        name="x", track_title="x", cue_in=timedelta(seconds=0.5),
        cue_out=timedelta(seconds=40), length=timedelta(seconds=FIXTURE_LENGTH),
        loudness_lufs=Decimal("-10.10"), true_peak_dbtp=Decimal("-0.50"),
        loudness_range_lu=Decimal("6.00"), bit_rate=897662, sample_rate=44100, channels=2,
    )
    values.update(extra)
    return File.objects.create(**values)


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture(name="conv")
def _conv(monkeypatch):
    fake = FakeConverter()
    monkeypatch.setattr(cl, "load_converter", lambda: fake)
    monkeypatch.setattr(cl, "_require_tool", lambda *_args: None)
    # no ffmpeg in unit tests: an unmeasurable file keeps the stored loudness
    monkeypatch.setattr(cl, "_measure_loudness", lambda _path: {})
    return fake


@pytest.fixture(name="library")
def _library(db, tmp_path):
    root = tmp_path / "media"
    flac = _write(root / "imported/Artist/Album/01 - Song.flac", b"fLaC" + b"\0" * 64)
    wav = _write(root / "imported/03 - Track.wav", b"RIFF" + b"\0" * 64)
    mp3 = root / "imported/Artist/Album/02 - Other.mp3"
    shutil.copyfile(FIXTURE_MP3, mp3)
    ogg = _write(root / "imported/Artist/04 - Vorbis.ogg", b"OggS" + b"\0" * 64)
    _write(root / "imported/gone.flac", b"fLaC")
    rows = SimpleNamespace(
        root=root,
        flac=_file("imported/Artist/Album/01 - Song.flac", md5=compute_md5(flac),
                   track_title="Song", artist_name="Artist", album_title="Album",
                   genre="Pop", track_number=1, date="2013", bpm=0,
                   comment=None, description="from the description"),
        wav=_file("imported/03 - Track.wav", md5=compute_md5(wav), mime="audio/wav"),
        # wrong mime on purpose: the probe decides, not the column
        mp3=_file("imported/Artist/Album/02 - Other.mp3", mime="audio/flac"),
        ogg=_file("imported/Artist/04 - Vorbis.ogg", mime="audio/ogg"),
        missing=_file("imported/Artist/missing.flac"),
        not_exists=_file("imported/gone.flac", exists=False),
    )
    rows.paths = SimpleNamespace(flac=flac, wav=wav, mp3=mp3, ogg=ogg)
    return rows


def _run(*args, **options):
    out = StringIO()
    call_command("convert_lossless", *args, stdout=out, **options)
    return out.getvalue()


def _schedule(file_row, starts, ends):
    return baker.make("schedule.Schedule", file=file_row, starts_at=starts, ends_at=ends,
                      cue_in=timedelta(0), cue_out=ends - starts)


# --- helpers (no database) ------------------------------------------------


def test_starts_with_mpeg_audio(tmp_path):
    assert cl.starts_with_mpeg_audio(FIXTURE_MP3)
    # ID3v2 tag (syncsafe size 20) in front of the first frame
    tagged = _write(tmp_path / "tagged.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x14" + b"\0" * 20 + b"\xff\xfb\x90d")
    assert cl.starts_with_mpeg_audio(tagged)
    # ID3v2 tag in front of FLAC: probe it
    assert not cl.starts_with_mpeg_audio(
        _write(tmp_path / "tagged.flac", b"ID3\x03\x00\x00\x00\x00\x00\x02\0\0fLaC")
    )
    assert not cl.starts_with_mpeg_audio(_write(tmp_path / "a.flac", b"fLaC\0\0"))
    assert not cl.starts_with_mpeg_audio(_write(tmp_path / "a.wav", b"RIFF\0\0\0\0WAVE"))
    # raw ADTS AAC: layer bits 00
    assert not cl.starts_with_mpeg_audio(_write(tmp_path / "a.aac", b"\xff\xf1\x50\x80"))
    assert not cl.starts_with_mpeg_audio(_write(tmp_path / "empty.mp3", b""))
    assert not cl.starts_with_mpeg_audio(tmp_path / "does-not-exist.mp3")


def test_unique_target(tmp_path):
    src = _write(tmp_path / "Song.wav", b"RIFF")
    assert cl.unique_target(src) == tmp_path / "Song.mp3"
    _write(tmp_path / "Song.mp3", b"x")
    assert cl.unique_target(src) == tmp_path / "Song (2).mp3"
    _write(tmp_path / "Song (2).mp3", b"x")
    assert cl.unique_target(src) == tmp_path / "Song (3).mp3"
    # lossless content behind an .mp3 name never overwrites itself
    odd = _write(tmp_path / "odd.mp3", b"fLaC")
    assert cl.unique_target(odd) == tmp_path / "odd (2).mp3"


def test_sibling_filepath():
    assert cl.sibling_filepath("imported/A/B/x.flac", "x.mp3") == "imported/A/B/x.mp3"
    assert cl.sibling_filepath("/imported/x.wav", "x (2).mp3") == "/imported/x (2).mp3"
    assert cl.sibling_filepath("x.wav", "x.mp3") == "x.mp3"
    assert cl.sibling_filepath("imported\\A\\x.wav", "x.mp3") == "imported/A/x.mp3"


def test_tags_from_row():
    row = File(
        track_title="Plansch", artist_name="Bilderbuch", album_title="Feinste Seide",
        genre="Alternative", comment="", description="dLs", date="2013", track_number=4,
        composer="", copyright=None, label="Maschin", isrc="ATX", bpm=0, language="de",
        expires_at=datetime(2027, 1, 31, tzinfo=dt_timezone.utc),
    )
    assert cl.tags_from_row(row) == {
        "track_title": "Plansch",
        "artist_name": "Bilderbuch",
        "album_title": "Feinste Seide",
        "genre": "Alternative",
        "comment": "dLs",
        "year": "2013",
        "track_number": "4",
        "label": "Maschin",
        "isrc": "ATX",
        "language": "de",
        "expires_at": "2027-01-31",
    }
    unknown = File(date="0", track_number=0, bpm=0)
    assert cl.tags_from_row(unknown) == {}


# --- candidate selection / dry run -----------------------------------------


def test_dry_run_lists_candidates_and_changes_nothing(library, conv):
    before = {row.id: (row.filepath, row.md5, row.mime) for row in File.objects.all()}

    output = _run(root=str(library.root))

    assert f"  {library.flac.id}: flac," in output
    assert f"  {library.wav.id}: pcm_s16le," in output
    assert f"{library.mp3.id}: pcm" not in output and f"{library.ogg.id}: vorbis" not in output
    assert "lossless: 2" in output
    assert "missing on disk: 1" in output
    assert "DRY RUN" in output
    # the MP3 is recognised by its frame header and never probed
    assert library.paths.mp3 not in conv.probed
    assert library.paths.ogg in conv.probed
    assert conv.transcoded == []
    assert {row.id: (row.filepath, row.md5, row.mime) for row in File.objects.all()} == before
    assert library.paths.flac.is_file() and library.paths.wav.is_file()


def test_ids_restrict_the_scan(library, conv):
    pending = _file("imported/03 - Track.wav", import_status=File.ImportStatus.PENDING)

    output = _run(
        root=str(library.root), ids=[library.flac.id, library.mp3.id, pending.id, 999999]
    )

    assert "lossless: 1" in output
    assert f"  {library.flac.id}: flac," in output
    assert f"{library.mp3.id}: not lossless (MPEG audio)" in output
    # a pending import may still be in the analyzer's hands
    assert f"{pending.id}: no imported row with file_exists and a filepath" in output
    assert "999999: no imported row with file_exists and a filepath" in output
    assert library.paths.wav not in conv.probed


def test_unreadable_file_is_reported_not_converted(library, conv):
    _write(library.paths.flac, b"junk" * 4)

    output = _run(root=str(library.root), ids=[library.flac.id], yes=True)

    assert "unreadable: 1" in output
    assert "nothing to do" in output
    assert conv.transcoded == []


# --- conversion ------------------------------------------------------------


def test_convert_updates_row_in_place_and_deletes_original(library, conv):
    old_md5 = library.flac.md5

    output = _run(root=str(library.root), ids=[library.flac.id], yes=True)

    row = File.objects.get(pk=library.flac.id)
    new_path = library.root / "imported/Artist/Album/01 - Song.mp3"
    assert f"{library.flac.id}: CONVERTED -> imported/Artist/Album/01 - Song.mp3" in output
    assert "done: 1 converted, 0 skipped, 0 failed" in output
    assert row.filepath == "imported/Artist/Album/01 - Song.mp3"
    assert row.mime == "audio/mp3"
    assert row.md5 == compute_md5(new_path)
    assert row.source_md5 == old_md5
    assert row.size == new_path.stat().st_size
    assert (row.bit_rate, row.sample_rate, row.channels) == (128000, 44100, 2)
    # kept: cue points, loudness, length (within 0.1 s)
    assert row.cue_in == timedelta(seconds=0.5)
    assert row.cue_out == timedelta(seconds=40)
    assert row.loudness_lufs == Decimal("-10.10")
    assert row.length == timedelta(seconds=FIXTURE_LENGTH)
    assert not library.paths.flac.exists()
    assert new_path.is_file()
    # tags from the database row, the probe handed through for the cover
    src, dest, tags, probe = conv.transcoded[0]
    assert (src, dest) == (library.paths.flac, new_path)
    assert tags == {
        "track_title": "Song", "artist_name": "Artist", "album_title": "Album",
        "genre": "Pop", "comment": "from the description", "year": "2013", "track_number": "1",
    }
    assert probe.codec == "flac"
    # the other lossless file is untouched
    assert File.objects.get(pk=library.wav.id).filepath == "imported/03 - Track.wav"


def test_convert_stores_the_loudness_measured_on_the_mp3(library, conv, monkeypatch):
    measured = {"loudness_lufs": -10.4, "true_peak_dbtp": 0.3, "loudness_range_lu": 5.2}
    monkeypatch.setattr(cl, "_measure_loudness", lambda _path: measured)

    _run(root=str(library.root), ids=[library.flac.id], yes=True)

    row = File.objects.get(pk=library.flac.id)
    assert row.loudness_lufs == Decimal("-10.40")
    assert row.true_peak_dbtp == Decimal("0.30")
    assert row.loudness_range_lu == Decimal("5.20")


def test_convert_takes_a_free_name_and_updates_a_different_length(library, conv):
    taken = _write(library.root / "imported/03 - Track.mp3", b"someone else")
    File.objects.filter(pk=library.wav.id).update(
        length=timedelta(seconds=FIXTURE_LENGTH + 2), cue_out=timedelta(seconds=FIXTURE_LENGTH + 1)
    )

    output = _run(root=str(library.root), ids=[library.wav.id], yes=True)

    row = File.objects.get(pk=library.wav.id)
    assert row.filepath == "imported/03 - Track (2).mp3"
    assert abs(row.length.total_seconds() - FIXTURE_LENGTH) < 0.001
    assert row.cue_out == row.length  # clamped to the new length
    assert "length" in output
    assert taken.read_bytes() == b"someone else"
    assert not library.paths.wav.exists()


def test_skip_when_scheduled_within_six_hours(library, conv):
    now = timezone.now()
    _schedule(library.flac, now + timedelta(hours=5), now + timedelta(hours=5, minutes=4))
    # playing right now
    _schedule(library.wav, now - timedelta(minutes=1), now + timedelta(minutes=3))

    output = _run(root=str(library.root), yes=True)

    assert f"{library.flac.id}: SKIPPED" in output
    assert f"{library.wav.id}: SKIPPED" in output
    assert "done: 0 converted, 2 skipped, 0 failed" in output
    assert conv.transcoded == []
    assert library.paths.flac.is_file() and library.paths.wav.is_file()
    assert File.objects.get(pk=library.flac.id).mime == "audio/flac"


def test_past_and_later_schedules_do_not_block(library, conv):
    now = timezone.now()
    _schedule(library.flac, now - timedelta(hours=2), now - timedelta(hours=1, minutes=56))
    _schedule(library.flac, now + timedelta(hours=7), now + timedelta(hours=7, minutes=4))

    output = _run(root=str(library.root), ids=[library.flac.id], yes=True)

    assert f"{library.flac.id}: CONVERTED" in output


def test_scheduled_during_conversion_discards_the_mp3(library, conv):
    def schedule_meanwhile(_src, dest):
        shutil.copyfile(FIXTURE_MP3, dest)
        now = timezone.now()
        _schedule(library.flac, now + timedelta(minutes=30), now + timedelta(minutes=34))

    conv.on_transcode = schedule_meanwhile

    output = _run(root=str(library.root), ids=[library.flac.id], yes=True)

    assert f"{library.flac.id}: SKIPPED got scheduled during the conversion" in output
    assert library.paths.flac.is_file()
    assert not (library.root / "imported/Artist/Album/01 - Song.mp3").exists()
    assert File.objects.get(pk=library.flac.id).filepath.endswith(".flac")


def test_failed_transcode_keeps_the_original(library, conv):
    def broken(_src, dest):
        dest.write_bytes(b"partial")
        raise conv.ConversionError("ffmpeg exited with 1")

    conv.on_transcode = broken

    with pytest.raises(CommandError, match="1 file\\(s\\) failed"):
        _run(root=str(library.root), ids=[library.flac.id], yes=True)

    assert library.paths.flac.is_file()
    assert not (library.root / "imported/Artist/Album/01 - Song.mp3").exists()
    row = File.objects.get(pk=library.flac.id)
    assert (row.filepath, row.mime, row.source_md5) == (library.flac.filepath, "audio/flac", None)


def test_failed_database_update_deletes_the_mp3_and_keeps_the_original(library, conv, monkeypatch):
    real_update = QuerySet.update

    def failing_update(self, **kwargs):
        if "source_md5" in kwargs:
            raise RuntimeError("database is gone")
        return real_update(self, **kwargs)

    monkeypatch.setattr(QuerySet, "update", failing_update)

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("convert_lossless", root=str(library.root), ids=[library.flac.id],
                     yes=True, stdout=out)

    assert "database update failed, original kept: database is gone" in out.getvalue()
    assert library.paths.flac.is_file()
    assert not (library.root / "imported/Artist/Album/01 - Song.mp3").exists()
    row = File.objects.get(pk=library.flac.id)
    assert (row.filepath, row.md5, row.source_md5) == (library.flac.filepath, library.flac.md5, None)


def test_original_that_cannot_be_deleted_is_reported(library, conv, monkeypatch):
    real_unlink = Path.unlink

    def locked_unlink(self, *args, **kwargs):
        if self == library.paths.flac:
            raise PermissionError("in use")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked_unlink)

    output = _run(root=str(library.root), ids=[library.flac.id], yes=True)

    assert "WARNING original not deleted (in use)" in output
    assert File.objects.get(pk=library.flac.id).filepath.endswith("01 - Song.mp3")
    assert library.paths.flac.is_file()


def test_missing_root_is_an_error(db, conv, tmp_path):
    with pytest.raises(CommandError, match="storage root does not exist"):
        _run(root=str(tmp_path / "nowhere"))


def test_missing_ffprobe_is_an_error(monkeypatch):
    monkeypatch.setenv("FFPROBE_PATH", "")
    monkeypatch.setattr(cl.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(CommandError, match="ffprobe not found"):
        cl._require_tool("FFPROBE_PATH", "ffprobe")  # pylint: disable=protected-access


def test_ffmpeg_dir_sets_the_tool_paths(monkeypatch, tmp_path):
    for name in ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"):
        _write(tmp_path / name, b"")
        (tmp_path / name).chmod(0o755)
    # setenv (not delenv) so that the values the helper sets are undone too
    monkeypatch.setenv("FFMPEG_PATH", "")
    monkeypatch.setenv("FFPROBE_PATH", "")
    monkeypatch.setenv("PATH", "elsewhere")

    cl._use_ffmpeg_dir(str(tmp_path))  # pylint: disable=protected-access

    assert cl.os.environ["PATH"].startswith(str(tmp_path))
    assert Path(cl.os.environ["FFMPEG_PATH"]).parent == tmp_path
    assert Path(cl.os.environ["FFPROBE_PATH"]).parent == tmp_path



# --- review fixes 2026-10-14 ------------------------------------------------


def test_is_file_name_title():
    src = Path("imported/03 - Track.wav")
    assert cl.is_file_name_title("03 - Track.wav", src)
    assert cl.is_file_name_title("Interview.WAV", src)
    assert not cl.is_file_name_title("Track", src)
    assert not cl.is_file_name_title(".wav", src)
    assert not cl.is_file_name_title("", src)
    assert not cl.is_file_name_title("Song.flac", src)


def test_convert_sets_name_and_mtime_like_an_import(library, conv):
    before = File.objects.get(pk=library.flac.id).updated_at

    _run(root=str(library.root), ids=[library.flac.id], yes=True)

    row = File.objects.get(pk=library.flac.id)
    assert row.name == "01 - Song.mp3"
    assert row.updated_at > before
    assert row.track_title == "Song"  # a real title stays


def test_file_name_title_becomes_the_new_file_name(library, conv):
    File.objects.filter(pk=library.wav.id).update(track_title="03 - Track.wav")

    _run(root=str(library.root), ids=[library.wav.id], yes=True)

    row = File.objects.get(pk=library.wav.id)
    assert row.track_title == "03 - Track.mp3"
    _src, _dest, tags, _probe = conv.transcoded[0]
    assert "track_title" not in tags  # a file name is not written as TIT2


def test_no_conversion_while_the_library_is_moved(library, conv, monkeypatch):
    monkeypatch.setattr(cl.storage_move.JOB, "is_locked", lambda: True)

    with pytest.raises(CommandError, match="being moved"):
        _run(root=str(library.root), yes=True)
    assert conv.transcoded == []
    # the dry run still lists
    assert "lossless: 2" in _run(root=str(library.root))


def test_move_started_during_the_run_skips_the_rest(library, conv, monkeypatch):
    answers = iter([False, False, True])  # handle(), first file, second file
    monkeypatch.setattr(cl.storage_move.JOB, "is_locked", lambda: next(answers))

    output = _run(root=str(library.root), yes=True)

    assert "done: 1 converted, 1 skipped, 0 failed" in output
    assert "the media library is being moved" in output
    assert len(conv.transcoded) == 1
