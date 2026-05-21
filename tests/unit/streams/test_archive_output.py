"""
T10.4 — ArchiveOutput and SoutBuilder.for_archive() unit tests.

Verifies the file archive sink (UC-O9) without requiring a running VLC
instance or a real filesystem write.  All tests are pure Python.

Test inventory
--------------
SoutBuilder.for_archive() — chain content (8):
 1.  Chain starts with "#transcode{".
 2.  Chain contains "access=file" (not "access=shout").
 3.  MP3 archive: acodec=mp3, mux=dummy.
 4.  OGG Vorbis archive: acodec=vorb, mux=ogg.
 5.  Opus archive: acodec=opus, samplerate=48000.
 6.  Bitrate is embedded as ab=<value>.
 7.  Destination path is embedded in dst=<path>.
 8.  Unsupported codec raises ValueError.

ArchiveOutput — data class behaviour (5):
 9.  Construction with all fields stores them correctly.
10.  codec, bitrate, enabled have sensible defaults.
11.  str path argument is coerced to pathlib.Path.
12.  Frozen: assigning an attribute raises FrozenInstanceError.
13.  Two identical ArchiveOutputs compare equal (frozen dataclass).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from streams.egress._archive import ArchiveOutput
from streams.egress._sout import SoutBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEST_WIN = Path(r"C:\archive\broadcast.mp3")
_DEST_POSIX = Path("/tmp/archive/broadcast.mp3")


# ---------------------------------------------------------------------------
# 1–8  SoutBuilder.for_archive()
# ---------------------------------------------------------------------------

def test_for_archive_starts_with_transcode():
    chain = SoutBuilder.for_archive(_DEST_WIN)
    assert chain.startswith("#transcode{")


def test_for_archive_uses_access_file_not_shout():
    chain = SoutBuilder.for_archive(_DEST_WIN)
    assert "access=file" in chain
    assert "access=shout" not in chain


def test_for_archive_mp3_codec_params():
    chain = SoutBuilder.for_archive(_DEST_WIN, codec="mp3")
    assert "acodec=mp3" in chain
    assert "mux=dummy" in chain


def test_for_archive_ogg_vorbis_codec_params():
    chain = SoutBuilder.for_archive(_DEST_WIN, codec="vorbis")
    assert "acodec=vorb" in chain
    assert "mux=ogg" in chain


def test_for_archive_opus_codec_params():
    chain = SoutBuilder.for_archive(_DEST_WIN, codec="opus")
    assert "acodec=opus" in chain
    assert "samplerate=48000" in chain


def test_for_archive_bitrate_embedded():
    chain = SoutBuilder.for_archive(_DEST_WIN, codec="mp3", bitrate=192)
    assert "ab=192" in chain


def test_for_archive_destination_path_in_chain():
    dest = Path("/tmp/show.mp3")
    chain = SoutBuilder.for_archive(dest, codec="mp3")
    assert str(dest) in chain


def test_for_archive_unsupported_codec_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        SoutBuilder.for_archive(_DEST_WIN, codec="flac")


# ---------------------------------------------------------------------------
# 9–13  ArchiveOutput data class
# ---------------------------------------------------------------------------

def test_archive_output_stores_all_fields():
    out = ArchiveOutput(
        id="arc-1",
        name="Daily Archive",
        path=Path("/archive/today.mp3"),
        codec="vorbis",
        bitrate=192,
        enabled=False,
    )
    assert out.id == "arc-1"
    assert out.name == "Daily Archive"
    assert out.path == Path("/archive/today.mp3")
    assert out.codec == "vorbis"
    assert out.bitrate == 192
    assert out.enabled is False


def test_archive_output_defaults():
    out = ArchiveOutput(id="arc-2", name="Default", path=Path("/tmp/out.mp3"))
    assert out.codec == "mp3"
    assert out.bitrate == 128
    assert out.enabled is True


def test_archive_output_str_path_coerced_to_path():
    out = ArchiveOutput(id="arc-3", name="Str Path", path="/tmp/cast.mp3")
    assert isinstance(out.path, Path)
    assert out.path == Path("/tmp/cast.mp3")


def test_archive_output_is_frozen():
    out = ArchiveOutput(id="arc-4", name="Frozen", path=Path("/tmp/f.mp3"))
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        out.codec = "ogg"  # type: ignore[misc]


def test_archive_output_equality():
    p = Path("/tmp/eq.mp3")
    a = ArchiveOutput(id="arc-5", name="EQ", path=p)
    b = ArchiveOutput(id="arc-5", name="EQ", path=p)
    assert a == b
