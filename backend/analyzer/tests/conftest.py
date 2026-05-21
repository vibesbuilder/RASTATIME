import os
import shutil
from pathlib import Path

import pytest
from libretime_shared.logging import setup_logger

from .fixtures import fixtures_path

setup_logger("debug")

AUDIO_FILENAME = "s1-stereo-tagged.mp3"
AUDIO_FILE = fixtures_path / AUDIO_FILENAME
AUDIO_IMPORT_DEST = f"Test Artist/Test Album/{AUDIO_FILENAME}"


# RASTATIME 2026-05-14 — ensure FFMPEG_PATH is set before any test
# module imports libretime_analyzer.pipeline._ffmpeg.  Without this,
# ``shutil.which("ffmpeg")`` returns None on the dev box (the binary
# lives at ``C:\ffmpeg\bin\ffmpeg.exe`` but is not on the test runner's
# PATH), and the playability test would silently fail open and stop
# catching the broken-file cases it's meant to guard.
if not os.environ.get("FFMPEG_PATH"):
    _candidates = [
        os.environ.get("RASTATIME_FFMPEG_PATH", ""),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        shutil.which("ffmpeg") or "",
    ]
    for _cand in _candidates:
        if _cand and Path(_cand).is_file():
            os.environ["FFMPEG_PATH"] = _cand
            break


@pytest.fixture()
def dest_dir(tmp_path: Path):
    dest = tmp_path / "dest"
    dest.mkdir()
    yield dest


@pytest.fixture()
def src_dir(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(AUDIO_FILE, src)
    yield src
