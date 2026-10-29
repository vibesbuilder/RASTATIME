"""
RASTATIME 2026-10-28 - repair a container that ffprobe rejects.

The case seen on 2026-10-20: a ``.mp3`` upload that was really a RIFF/WAV
file with MP3 payload and an ID3v2 block glued in FRONT of the RIFF header
(a tagging tool wrote the tag as if the file were a plain MP3).  ffprobe
sees ``ID3`` first, finds a RIFF header where MPEG frames should be and
gives up ("invalid start code ID3 in RIFF header"); the import failed and
the original stayed in ``organize/``.

``repair_container`` runs before ``analyze_metadata``.  It does nothing
(returns its inputs) unless the file starts with ``ID3`` AND a
``RIFF....WAVE`` header follows within the first megabyte (whether ffprobe
copes with the small ones or not - the 39 KB block of the real case made
it give up).  Then it writes a sibling copy without the leading block:

* payload codec ``mp3`` -> the MP3 stream is copied out as ``<stem>.mp3``
  (no re-encode; ffmpeg ``-c:a copy``), the original filename gets ``.mp3``;
* any other payload (PCM ...) -> ``<stem>.wav`` with the stripped bytes,
  original filename ``.wav`` (convert_format then treats it like any WAV).

The original is left in place - the pipeline removes it only after the
repaired file is filed (same rule as convert_format), so a failure later
on still finds it in ``organize/``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, Tuple

from rastatime_shared.files import compute_md5

from ._ffmpeg import FFMPEG, ffprobe_json, low_priority_creationflags

logger = logging.getLogger(__name__)

SEARCH_BYTES = 1024 * 1024
RIFF_WAVE = b"WAVE"


def _riff_offset(head: bytes) -> int:
    """Offset of a ``RIFF....WAVE`` header behind a leading ID3 block, or -1."""
    if not head.startswith(b"ID3"):
        return -1
    pos = head.find(b"RIFF", 3)
    while pos >= 0:
        if head[pos + 8:pos + 12] == RIFF_WAVE:
            return pos
        pos = head.find(b"RIFF", pos + 4)
    return -1


def repair_container(audio_file_path: str, original_filename: str, metadata: Dict) -> Tuple[str, str, Dict]:
    """
    Pipeline step.  Returns (audio_file_path, original_filename, metadata):
    unchanged inputs when there is nothing to repair, else the repaired
    sibling file and the original filename with the payload's suffix.
    ``metadata['source_md5']`` is set to the md5 of the broken original so
    the duplicate check still recognises it.
    """
    src = Path(audio_file_path)
    try:
        with open(src, "rb") as handle:
            head = handle.read(SEARCH_BYTES)
    except OSError:
        return audio_file_path, original_filename, metadata
    offset = _riff_offset(head)
    if offset < 0:
        return audio_file_path, original_filename, metadata

    stripped = src.with_name(src.stem + ".repaired.wav")
    try:
        with open(src, "rb") as handle, open(stripped, "wb") as out:
            handle.seek(offset)
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        probe = ffprobe_json(stripped, timeout=60.0)
    except (OSError, subprocess.SubprocessError, ValueError) as exception:
        logger.warning("repair_container: stripped copy of %s is not readable either: %s", src.name, exception)
        stripped.unlink(missing_ok=True)
        return audio_file_path, original_filename, metadata

    audio = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {})
    codec = str(audio.get("codec_name") or "").lower()
    stem = Path(original_filename).stem
    if codec == "mp3":
        target = src.with_name(src.stem + ".repaired.mp3")
        cmd = [FFMPEG, "-hide_banner", "-nostats", "-loglevel", "error", "-y", "-i", str(stripped), "-vn", "-c:a", "copy", "-f", "mp3", str(target)]
        completed = subprocess.run(cmd, check=False, capture_output=True, stdin=subprocess.DEVNULL, timeout=600.0, creationflags=low_priority_creationflags())
        stripped.unlink(missing_ok=True)
        if completed.returncode != 0 or not target.is_file():
            logger.warning("repair_container: MP3 extraction of %s failed: %s", src.name, completed.stderr.decode("utf-8", "replace")[-200:])
            target.unlink(missing_ok=True)
            return audio_file_path, original_filename, metadata
        new_name = stem + ".mp3"
    else:
        target = stripped
        new_name = stem + ".wav"

    metadata.setdefault("source_md5", compute_md5(src))
    logger.info(
        "repair_container: %s had an ID3 block in front of its RIFF header (%d bytes, payload %s) - importing the repaired copy %s",
        original_filename, offset, codec or "?", target.name,
    )
    return str(target), new_name, metadata
