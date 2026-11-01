"""
RASTATIME 2026-10-14 - import format normalization.

Runs right after analyze_metadata, before any other measurement, so the
duration, cue points, ReplayGain and loudness are taken from the file that
ends up in the library:

* A raw ADTS AAC stream (ffprobe format "aac", whatever the extension) is
  ALWAYS repacked losslessly into an MP4 container (.m4a, stream copy).
  ADTS has no index - its duration is only estimated from the bitrate
  (about 1.9 s too long on the files that showed it) - and it cannot carry
  tags.
* Lossless audio (PCM in WAV/AIFF, FLAC, ALAC, WavPack, APE, TTA) is
  transcoded to MP3 320 kbps CBR when the import message asks for it
  (Settings -> Local Machine, "convert_lossless_to_mp3", default on).  The
  lossless original is not kept (operator decision 2026-10-14): the
  pipeline deletes it with remove_original() once the converted file is
  filed in the library, and drops the conversion with discard_converted()
  when a later step fails - the original then stays in organize/ as it
  would without the conversion.

Any conversion failure falls back to importing the original file unchanged.

The API package (management command convert_lossless) uses probe_audio,
is_lossless and transcode_to_mp3 for files already in the library - keep
these signatures stable.
"""

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import date, datetime
from functools import partial
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from . import _ffmpeg
from ._utils import positive_float, positive_int
from .analyze_metadata import analyze_metadata

logger = logging.getLogger(__name__)

LOSSLESS_CODECS = frozenset({"flac", "alac", "wavpack", "ape", "tta"})

# RASTATIME 2026-10-21 - Windows Media Audio (operator go): always
# transcoded to MP3, lossy or lossless, like raw ADTS is always repacked -
# browsers cannot preview WMA and it would be the one unnormalised format.
WMA_CODECS = frozenset({"wmav1", "wmav2", "wmapro", "wmalossless", "wmavoice"})

# Embedded covers ffmpeg can copy into an ID3 APIC frame as they are.
COVER_CODECS = frozenset({"mjpeg", "png"})

# MP3 sample rates (MPEG-1) kept as they are; anything else (88.2 / 96 /
# 192 kHz, 22.05 kHz, ...) is resampled to 44.1 kHz.
MP3_SAMPLE_RATES = (32000, 44100, 48000)

MP3_BITRATE = "320k"

_PROBE_TIMEOUT_S = 60.0
_MIN_TIMEOUT_S = 120.0
_TIMEOUT_DURATION_FACTOR = 1.5
# Timeout fallback when the duration is unknown: 100 kB/s is far below
# what even an uncompressed CD-quality file needs (176 kB/s).
_TIMEOUT_BYTES_PER_SECOND = 100_000

# A virus scanner may hold a freshly written file for a moment: deleting
# the original and renaming the finished output are retried this often.
_UNLINK_ATTEMPTS = 3
_UNLINK_RETRY_S = 0.5

# Keys written back into cc_files from the converted file ("encoder": the
# original's encoder string would describe the wrong file).
_FILE_PROPERTY_KEYS = (
    "mime",
    "filesize",
    "md5",
    "bit_rate",
    "sample_rate",
    "channels",
    "length_seconds",
    "length",
    "encoder",
)

_EXTENSION_RE = re.compile(r"^[A-Za-z0-9]{1,5}$")


class ConversionError(Exception):
    pass


@dataclass
class AudioProbe:
    codec: str
    format_name: str
    sample_rate: Optional[int]
    channels: Optional[int]
    bits: Optional[int]
    has_cover: bool
    cover_codec: Optional[str]
    # Container duration in seconds (None when unknown); only used for the
    # subprocess timeout and the output sanity check.
    duration: Optional[float] = None


def probe_audio(path: Path) -> AudioProbe:
    """Probe the first audio stream (and an embedded cover) with ffprobe."""
    path = Path(path)
    try:
        data = _ffmpeg.ffprobe_json(path, timeout=_PROBE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError, ValueError) as exception:
        raise ConversionError(f"ffprobe could not read {path}: {exception}") from exception

    streams = [s for s in (data.get("streams") or []) if isinstance(s, dict)]
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise ConversionError(f"no audio stream in {path}")

    # Only the FIRST video stream counts - that is the one "-map 0:v:0" takes.
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_cover = bool(video and (video.get("disposition") or {}).get("attached_pic"))
    cover_codec = None
    if has_cover and video is not None:
        cover_codec = str(video.get("codec_name") or "").lower() or None

    fmt = data.get("format") or {}
    return AudioProbe(
        codec=str(audio.get("codec_name") or "").lower(),
        format_name=str(fmt.get("format_name") or "").lower(),
        sample_rate=positive_int(audio.get("sample_rate")),
        channels=positive_int(audio.get("channels")),
        bits=positive_int(audio.get("bits_per_raw_sample"))
        or positive_int(audio.get("bits_per_sample")),
        has_cover=has_cover,
        cover_codec=cover_codec,
        duration=positive_float(fmt.get("duration")) or positive_float(audio.get("duration")),
    )


def is_lossless(p: AudioProbe) -> bool:
    return p.codec in LOSSLESS_CODECS or p.codec.startswith("pcm_")


def is_raw_adts(p: AudioProbe) -> bool:
    return p.format_name == "aac"


def is_wma(p: AudioProbe) -> bool:
    return p.codec in WMA_CODECS


def _timeout_for(src: Path, probe: AudioProbe) -> float:
    if probe.duration:
        return max(_MIN_TIMEOUT_S, _TIMEOUT_DURATION_FACTOR * probe.duration)
    try:
        size = src.stat().st_size
    except OSError:
        size = 0
    return max(_MIN_TIMEOUT_S, size / _TIMEOUT_BYTES_PER_SECOND)


def _run_ffmpeg(args: list[str], timeout: float) -> None:
    cmd = [_ffmpeg.FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y", *args]
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            creationflags=_ffmpeg.low_priority_creationflags(),
        )
    except OSError as exception:
        raise ConversionError(f"could not run {cmd[0]}: {exception}") from exception
    except subprocess.TimeoutExpired as exception:
        raise ConversionError(f"ffmpeg timed out after {timeout:.0f} s") from exception

    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ConversionError(f"ffmpeg failed (exit {completed.returncode}): {stderr[-500:]}")


def _temp_path(dest: Path) -> Path:
    """A temporary name next to dest (same folder, so os.replace is a rename)."""
    return dest.with_name(f"{dest.stem}.part-{uuid4().hex[:8]}{dest.suffix}")


def _remove_quietly(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exception:
        logger.warning("could not remove %s: %s", path, exception)


def remove_original(path) -> None:
    """
    Delete the original of a conversion that is filed in the library (the
    pipeline calls this after organise_file).  A virus scanner may hold a
    fresh file for a moment, so retry briefly before leaving it behind with
    a warning.
    """
    src = Path(path)
    for attempt in range(_UNLINK_ATTEMPTS):
        try:
            src.unlink()
            return
        except FileNotFoundError:
            return
        except OSError as exception:
            if attempt + 1 == _UNLINK_ATTEMPTS:
                logger.warning(
                    "convert_format: could not remove the original %s: %s", src, exception
                )
                return
            time.sleep(_UNLINK_RETRY_S)


def discard_converted(path) -> None:
    """Delete a converted file whose import failed in a later step."""
    _remove_quietly(Path(path))


def _replace(tmp: Path, dest: Path) -> None:
    """os.replace, retried briefly: a virus scanner may still hold the file
    ffmpeg / mutagen just wrote."""
    for attempt in range(_UNLINK_ATTEMPTS):
        try:
            os.replace(tmp, dest)
            return
        except PermissionError:
            if attempt + 1 == _UNLINK_ATTEMPTS:
                raise
            time.sleep(_UNLINK_RETRY_S)


def _verify_output(path: Path, codec: str, src_probe: AudioProbe, check_duration: bool) -> None:
    out = probe_audio(path)
    if out.codec != codec:
        raise ConversionError(f"output codec is {out.codec!r}, expected {codec!r}")
    if not out.duration:
        raise ConversionError("output has no duration")
    if check_duration and src_probe.duration:
        tolerance = max(1.0, 0.01 * src_probe.duration)
        if abs(out.duration - src_probe.duration) > tolerance:
            raise ConversionError(
                f"output is {out.duration:.2f} s long, the source {src_probe.duration:.2f} s"
            )


def _text(value: Any) -> Optional[str]:
    """A tag value as text; None for empty values."""
    if isinstance(value, (list, tuple)):
        value = next((v for v in value if v not in (None, "")), None)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value == 0:
            return None  # legacy stores 0 for an unknown track number / bpm
        if isinstance(value, float) and value.is_integer():
            value = int(value)
    text = str(value).strip()
    return text or None


def _first_text(tags: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        text = _text(tags.get(key))
        if text:
            return text
    return None


def _expiry_text(value: Any) -> Optional[str]:
    """expires_at as YYYY-MM-DD (the analyzer emits that, the DB a timestamp)."""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = _text(value)
    if text and re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    return None


def _track_text(tags: dict[str, Any]) -> Optional[str]:
    number = _text(tags.get("track_number"))
    if not number:
        return None
    total = _text(tags.get("track_total"))
    return f"{number}/{total}" if total else number


def _write_id3_tags(path: Path, tags: dict[str, Any]) -> None:
    """Write the metadata (cc_files names) into the MP3 as ID3v2.3."""
    # pylint: disable=import-outside-toplevel
    from mutagen.id3 import (
        COMM,
        ID3,
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
        ID3NoHeaderError,
    )

    try:
        id3 = ID3(path)  # keeps the APIC frame ffmpeg wrote
    except ID3NoHeaderError:
        id3 = ID3()

    frames = [
        (TIT2, _first_text(tags, "track_title")),
        (TPE1, _first_text(tags, "artist_name")),
        (TALB, _first_text(tags, "album_title")),
        (TCON, _first_text(tags, "genre")),
        (TDRC, _first_text(tags, "year")),
        (TRCK, _track_text(tags)),
        (TCOM, _first_text(tags, "composer")),
        (TCOP, _first_text(tags, "copyright")),
        (TPUB, _first_text(tags, "label")),
        (TSRC, _first_text(tags, "isrc")),
        (TBPM, _first_text(tags, "bpm")),
        (TLAN, _first_text(tags, "language")),
        (
            partial(COMM, lang="eng", desc=""),
            _first_text(tags, "comment", "comments", "description"),
        ),
        (partial(TXXX, desc="Expiry"), _expiry_text(tags.get("expires_at"))),
    ]
    for make_frame, text in frames:
        if not text:
            continue
        try:
            id3.add(make_frame(encoding=3, text=text))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            # one odd value (e.g. a year mutagen cannot parse) costs that tag only
            logger.warning("ID3 tag %r skipped: %s", text, exception)

    # v2.3: mutagen writes the UTF-8 frames as UTF-16 and TDRC as TYER
    id3.save(path, v2_version=3)


def _write_mp4_tags(path: Path, tags: dict[str, Any]) -> None:
    """Write the metadata (cc_files names) into the M4A."""
    # pylint: disable=import-outside-toplevel
    from mutagen.easymp4 import EasyMP4
    from mutagen.mp4 import MP4, MP4FreeForm

    easy = EasyMP4(path)
    values = [
        ("title", _first_text(tags, "track_title")),
        ("artist", _first_text(tags, "artist_name")),
        ("album", _first_text(tags, "album_title")),
        ("genre", _first_text(tags, "genre")),
        ("comment", _first_text(tags, "comment", "comments", "description")),
        ("date", _first_text(tags, "year")),
        ("tracknumber", _track_text(tags)),
        ("composer", _first_text(tags, "composer")),
        ("copyright", _first_text(tags, "copyright")),
        ("bpm", _first_text(tags, "bpm")),
    ]
    for key, text in values:
        if not text:
            continue
        try:
            easy[key] = text
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.warning("tag %s=%r skipped: %s", key, text, exception)
    easy.save()

    freeform = [
        ("Expiry", _expiry_text(tags.get("expires_at"))),
        ("ISRC", _first_text(tags, "isrc")),
        ("LABEL", _first_text(tags, "label")),
        ("LANGUAGE", _first_text(tags, "language")),
    ]
    if any(text for _, text in freeform):
        mp4 = MP4(path)
        for name, text in freeform:
            if text:
                mp4[f"----:com.apple.iTunes:{name}"] = [MP4FreeForm(text.encode("utf-8"))]
        mp4.save()


def transcode_to_mp3(
    src: Path,
    dest: Path,
    tags: dict,
    *,
    probe: Optional[AudioProbe] = None,
) -> None:
    """
    Transcode src to MP3 320 kbps CBR at dest (an embedded JPEG / PNG cover
    is copied as the front cover) and write the tags.  dest only appears
    once it is complete.  Raises ConversionError; never leaves a partial
    file behind.
    """
    src, dest = Path(src), Path(dest)
    if probe is None:
        probe = probe_audio(src)

    args = ["-i", str(src), "-map", "0:a:0"]
    if probe.has_cover and probe.cover_codec in COVER_CODECS:
        args += [
            *("-map", "0:v:0"),
            *("-c:v", "copy"),
            *("-disposition:v", "attached_pic"),
            # -map_metadata -1 also drops the picture type: front cover
            *("-metadata:s:v:0", "comment=Cover (front)"),
        ]
    args += [
        *("-c:a", "libmp3lame"),
        *("-b:a", MP3_BITRATE),
        *("-map_metadata", "-1"),
        *("-id3v2_version", "3"),
    ]
    if probe.sample_rate not in MP3_SAMPLE_RATES:
        args += ["-ar", "44100"]
    if probe.channels and probe.channels > 2:
        args += ["-ac", "2"]

    tmp = _temp_path(dest)
    args += ["-f", "mp3", str(tmp)]
    try:
        _run_ffmpeg(args, _timeout_for(src, probe))
        _verify_output(tmp, "mp3", probe, check_duration=True)
        _write_id3_tags(tmp, tags)
        _replace(tmp, dest)
    except ConversionError:
        _remove_quietly(tmp)
        raise
    except Exception as exception:
        _remove_quietly(tmp)
        raise ConversionError(f"MP3 conversion of {src} failed: {exception}") from exception


def remux_adts_to_m4a(src: Path, dest: Path, tags: dict) -> None:
    """
    Repack a raw ADTS AAC stream into an M4A without re-encoding and write
    the tags.  Raises ConversionError; never leaves a partial file behind.
    """
    src, dest = Path(src), Path(dest)
    probe = probe_audio(src)

    tmp = _temp_path(dest)
    args = [
        *("-i", str(src)),
        *("-map", "0:a:0"),
        *("-c:a", "copy"),
        *("-map_metadata", "-1"),
        *("-movflags", "+faststart"),
        *("-f", "ipod", str(tmp)),
    ]
    try:
        _run_ffmpeg(args, _timeout_for(src, probe))
        # No duration check: the ADTS duration is the bitrate estimate this
        # repack is meant to correct.
        _verify_output(tmp, "aac", probe, check_duration=False)
        _write_mp4_tags(tmp, tags)
        _replace(tmp, dest)
    except ConversionError:
        _remove_quietly(tmp)
        raise
    except Exception as exception:
        _remove_quietly(tmp)
        raise ConversionError(f"M4A repack of {src} failed: {exception}") from exception


def _without_extension(name: str) -> str:
    """'Song.flac' -> 'Song'; 'Live 1.2 Mix' stays (' Mix' is no extension)."""
    base, dot, extension = name.rpartition(".")
    if dot and base and _EXTENSION_RE.match(extension):
        return base
    return name


def _with_suffix(name: str, suffix: str) -> str:
    """'Song.flac' -> 'Song.mp3'; 'Live 1.2 Mix' -> 'Live 1.2 Mix.mp3'."""
    if not name:
        return name
    return _without_extension(name) + suffix


def _output_path(src: Path, suffix: str) -> Path:
    dest = src.with_name(_with_suffix(src.name, suffix))
    if dest == src or dest.exists():
        dest = src.with_name(f"{_without_extension(src.name)}_{uuid4().hex[:8]}{suffix}")
    return dest


def convert_format(
    audio_file_path: str,
    original_filename: str,
    metadata: dict,
    *,
    convert_lossless: bool,
) -> tuple[str, str, dict]:
    """
    Pipeline step: repack raw ADTS to M4A (always), transcode Windows Media
    Audio to MP3 320 kbps (always) and lossless audio to MP3 320 kbps (when
    convert_lossless).  Returns
    (audio_file_path, original_filename, metadata) - for a converted file the
    new path next to the old one, the name with the new suffix, and the
    metadata with source_md5 (the md5 of the original) plus the file
    properties of the new file.  Any failure returns the inputs unchanged.

    The original is left in place: the caller deletes it (remove_original)
    once the converted file is filed, so a failure in a later step - or an
    analyzer restart before organise_file - still finds it (a redelivered
    message is retried with the original).
    """
    src = Path(audio_file_path)
    try:
        probe = probe_audio(src)
    except ConversionError as exception:
        logger.warning("convert_format: %s - importing %s as it is", exception, original_filename)
        return audio_file_path, original_filename, metadata

    if is_raw_adts(probe):
        suffix, what = ".m4a", "repacked raw ADTS AAC to M4A"
    elif is_wma(probe):
        suffix, what = (
            ".mp3",
            f"transcoded {probe.codec} (Windows Media Audio) to MP3 {MP3_BITRATE}bit/s",
        )
    elif convert_lossless and is_lossless(probe):
        suffix, what = ".mp3", f"transcoded {probe.codec} to MP3 {MP3_BITRATE}bit/s"
    else:
        return audio_file_path, original_filename, metadata

    dest = _output_path(src, suffix)
    try:
        if suffix == ".m4a":
            remux_adts_to_m4a(src, dest, metadata)
        else:
            transcode_to_mp3(src, dest, metadata, probe=probe)
        properties = analyze_metadata(str(dest), {})
    except Exception as exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "convert_format: %s could not be converted (%s) - importing the original",
            original_filename,
            exception,
        )
        _remove_quietly(dest)
        return audio_file_path, original_filename, metadata

    result = dict(metadata)
    if metadata.get("md5"):
        result["source_md5"] = metadata["md5"]
    for key in _FILE_PROPERTY_KEYS:
        if key in properties:
            result[key] = properties[key]
        else:
            result.pop(key, None)  # a value of the original must not survive

    new_filename = _with_suffix(original_filename, suffix)
    # A file without a title tag keeps the title the legacy app gave it at
    # the hand-over - its file name, here with the OLD extension
    # ("Interview.wav" for what is now an MP3).  Use the name it is filed
    # under, as for any untagged upload.
    if not _text(result.get("track_title")) and new_filename:
        result["track_title"] = new_filename
    logger.info(
        "convert_format: %s %s -> %s (%s bytes -> %s bytes)",
        what,
        original_filename,
        new_filename,
        metadata.get("filesize"),
        result.get("filesize"),
    )
    return str(dest), new_filename, result
