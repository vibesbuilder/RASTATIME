import shutil
from pathlib import Path

import pytest
from rastatime_analyzer.pipeline.organise_file import TAGLESS_DIR, organise_file, safe_component

from ..conftest import AUDIO_FILENAME


def organise_file_args_factory(filepath: Path, dest_dir: Path):
    return (
        str(filepath),
        str(dest_dir),
        AUDIO_FILENAME,
        {},
    )


# RASTATIME 2026-10-24: a file without an artist tag lands in <storage>/tagless/
def test_organise_file(src_dir: Path, dest_dir: Path):
    organise_file(*organise_file_args_factory(src_dir / AUDIO_FILENAME, dest_dir))
    assert (dest_dir / TAGLESS_DIR / AUDIO_FILENAME).exists()


def test_organise_file_samefile(src_dir: Path):
    metadata = organise_file(*organise_file_args_factory(src_dir / AUDIO_FILENAME, src_dir))
    dest = Path(metadata["full_path"])
    assert dest == src_dir / TAGLESS_DIR / AUDIO_FILENAME and dest.exists()
    # organising the file from its storage place again is a no-op
    again = organise_file(*organise_file_args_factory(dest, src_dir))
    assert Path(again["full_path"]) == dest and dest.exists()


def test_organise_file_duplicate_file(src_dir: Path, dest_dir: Path):
    for i in range(1, 4):
        # Make a copy so we can reuse the file
        filename = f"{i}_{AUDIO_FILENAME}"
        shutil.copy(src_dir / AUDIO_FILENAME, src_dir / filename)

        metadata = organise_file(*organise_file_args_factory(src_dir / filename, dest_dir))

        full_path = Path(metadata["full_path"])
        assert full_path.exists()
        if i == 1:
            assert full_path.name == AUDIO_FILENAME
        else:
            assert len(full_path.name) == len(AUDIO_FILENAME) + 1 + 36  # _ + UUID size


def test_organise_file_bad_permissions_dest_dir(src_dir: Path, tmp_path: Path):
    # RASTATIME 2026-11-01: platform-neutral replacement for the Linux-only
    # /sys target - a regular file where the storage directory should be
    # makes every mkdir fail on Windows and Linux alike.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    with pytest.raises(OSError):
        organise_file(
            *organise_file_args_factory(
                src_dir / AUDIO_FILENAME,
                blocker / "storage",
            )
        )


# RASTATIME 2026-10-09 - tag text with characters a Windows path refuses
def test_organise_file_reserved_characters(src_dir: Path, dest_dir: Path):
    metadata = organise_file(
        str(src_dir / AUDIO_FILENAME),
        str(dest_dir),
        AUDIO_FILENAME,
        {"artist_name": "Amon Tobin", "album_title": "The Getaway: Black Monday?!"},
    )
    full_path = Path(metadata["full_path"])
    assert full_path.exists()
    assert full_path.name == AUDIO_FILENAME
    assert full_path.parent.name == "The Getaway_ Black Monday_!"
    assert full_path.parent.parent.name == "Amon Tobin"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Why Not?!", "Why Not_!"),
        ("What's Next?!", "What's Next_!"),
        ("S.A.C.", "S.A.C"),
        ("trailing space ", "trailing space"),
        ("...", "_"),
        ('a<b>c:d"e/f|g*h', "a_b_c_d_e_f_g_h"),
        ("[2007] Robyn", "[2007] Robyn"),
    ],
)
def test_safe_component(name: str, expected: str):
    assert safe_component(name) == expected
