"""
RASTATIME 2026-10-24 - tracks without an artist tag are filed under
imported/tagless/ (no fixtures needed: organise_file only moves files).
"""

from pathlib import Path

import pytest
from rastatime_analyzer.pipeline.organise_file import TAGLESS_DIR, organise_file


def _incoming(tmp_path: Path, name: str = "track.mp3") -> Path:
    src = tmp_path / "incoming" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"not really audio")
    return src


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"artist_name": ""},
        {"artist_name": "   "},
        {"album_title": "Only An Album"},
    ],
)
def test_no_artist_goes_to_tagless(tmp_path: Path, metadata):
    src = _incoming(tmp_path)
    dest_root = tmp_path / "stor" / "imported"
    result = organise_file(str(src), str(dest_root), "track.mp3", dict(metadata))
    assert Path(result["full_path"]) == dest_root / TAGLESS_DIR / "track.mp3"
    assert (dest_root / TAGLESS_DIR / "track.mp3").is_file()
    assert not (dest_root / "track.mp3").exists()


def test_artist_and_album_folders_as_before(tmp_path: Path):
    src = _incoming(tmp_path)
    dest_root = tmp_path / "stor" / "imported"
    result = organise_file(
        str(src),
        str(dest_root),
        "track.mp3",
        {"artist_name": "Caribou", "album_title": "Up in Flames"},
    )
    assert Path(result["full_path"]) == dest_root / "Caribou" / "Up in Flames" / "track.mp3"


def test_artist_without_album(tmp_path: Path):
    src = _incoming(tmp_path)
    dest_root = tmp_path / "stor" / "imported"
    result = organise_file(str(src), str(dest_root), "track.mp3", {"artist_name": "Caribou"})
    assert Path(result["full_path"]) == dest_root / "Caribou" / "track.mp3"
