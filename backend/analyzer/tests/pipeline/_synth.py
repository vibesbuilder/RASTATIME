"""
RASTATIME 2026-10-14 - small synthetic audio files for the format tests,
generated with ffmpeg into the test's tmp dir (no binary fixtures in git).
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from libretime_analyzer.pipeline import _ffmpeg


def _resolve(binary: str) -> str:
    if Path(binary).is_file():
        return binary
    return shutil.which(binary) or ""


FFMPEG_BIN = _resolve(os.environ.get("FFMPEG_PATH", _ffmpeg.FFMPEG))
FFPROBE_BIN = _resolve(os.environ.get("FFPROBE_PATH", _ffmpeg.FFPROBE))

requires_ffmpeg = pytest.mark.skipif(
    not (FFMPEG_BIN and FFPROBE_BIN),
    reason="ffmpeg / ffprobe not found",
)

SECONDS = 3


def ffmpeg(*args) -> None:
    subprocess.run(
        [FFMPEG_BIN, "-nostdin", "-y", "-v", "error", *map(str, args)],
        check=True,
        capture_output=True,
    )


def sine(
    path: Path,
    *output_args,
    sample_rate: int = 44100,
    channels: int = 2,
    seconds: float = SECONDS,
) -> Path:
    """A sine tone in the format the suffix / output args select."""
    layout = {1: "mono", 2: "stereo", 6: "5.1"}[channels]
    ffmpeg(
        *("-f", "lavfi"),
        *("-i", f"sine=frequency=440:duration={seconds}:sample_rate={sample_rate}"),
        *("-af", f"aformat=channel_layouts={layout}"),
        *output_args,
        path,
    )
    return path


def png_cover(path: Path) -> Path:
    ffmpeg(*("-f", "lavfi"), *("-i", "color=c=red:s=64x64:d=1"), *("-frames:v", "1"), path)
    return path


def flac_with_cover(path: Path, cover: Path, *metadata_args) -> Path:
    tone = sine(path.with_name("tone-for-cover.wav"))
    ffmpeg(
        *("-i", tone),
        *("-i", cover),
        *("-map", "0:a"),
        *("-map", "1:v"),
        *("-c:a", "flac"),
        *("-c:v", "png"),
        *("-disposition:v", "attached_pic"),
        *metadata_args,
        path,
    )
    tone.unlink()
    return path


def raw_adts(path: Path) -> Path:
    return sine(path, "-c:a", "aac", "-b:a", "128k", "-f", "adts")


def raw_adts_with_id3(path: Path, frames) -> Path:
    """Raw ADTS stream behind an ID3v2 header (mutagen: can't sync to MPEG frame)."""
    from mutagen.id3 import ID3  # pylint: disable=import-outside-toplevel

    adts = raw_adts(path.with_name("plain-for-id3.aac"))
    id3 = ID3()
    for frame in frames:
        id3.add(frame)
    id3.save(path, v2_version=3)
    with open(path, "ab") as handle:
        handle.write(adts.read_bytes())
    adts.unlink()
    return path


def probe(path: Path) -> dict:
    return _ffmpeg.ffprobe_json(path)


def audio_stream(path: Path) -> dict:
    return next(s for s in probe(path)["streams"] if s["codec_type"] == "audio")
