import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# RASTATIME: mutagen is not installed on Windows by default.
# Guard the import so this module can be safely imported without it.
try:
    import mutagen
    from mutagen.easyid3 import EasyID3

    _MUTAGEN_AVAILABLE = True
except ImportError:
    mutagen = None  # type: ignore[assignment]
    EasyID3 = None  # type: ignore[assignment, misc]
    _MUTAGEN_AVAILABLE = False

from rastatime_shared.files import compute_md5

from ._ffmpeg import ffprobe_json
from ._utils import positive_float, positive_int

logger = logging.getLogger(__name__)


def flatten(xss):
    return [x for xs in xss for x in xs]


def comment_get(id3, _):
    comments = [v.text for k, v in id3.items() if "COMM" in k or "comment" in k]

    return flatten(comments)


if _MUTAGEN_AVAILABLE:
    EasyID3.RegisterKey("comment", comment_get)


def _parse_expiry(raw: str, filepath: Path) -> Optional[datetime]:
    """Parse an Expiry tag value (YYYY-MM-DD); None (with a warning) otherwise."""
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        logger.warning(
            "Expiry tag value %r in %s is not ISO 8601 date (YYYY-MM-DD); ignoring",
            raw,
            filepath,
        )
        return None


def _extract_expiry_tag(filepath: Path) -> Optional[datetime]:
    """
    RASTATIME 2026-05-16 - Read a custom ID3v2 TXXX frame named "Expiry"
    and parse its value as an ISO-8601 date (YYYY-MM-DD).

    Used by the Track-Expiry feature.  Returns a timezone-naive datetime
    at midnight UTC on the parsed date, or None if:
      * the file has no ID3v2 metadata,
      * no TXXX frame with description "Expiry" exists,
      * the value does not parse as YYYY-MM-DD.

    Mutagen's EasyID3 does not expose generic TXXX frames, so we read
    the raw ID3 here via mutagen.id3.ID3.  Other tag formats (Vorbis
    comments in OGG/FLAC, MP4 atoms, the ID3 chunk of a WAV file) are read
    from the ffprobe tags in analyze_metadata (RASTATIME 2026-10-14).
    """
    if not _MUTAGEN_AVAILABLE:
        return None

    try:
        # Lazy-import to keep the legacy import path light.
        from mutagen.id3 import ID3, ID3NoHeaderError  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None

    try:
        id3 = ID3(filepath)
    except (ID3NoHeaderError, Exception):  # pylint: disable=broad-exception-caught
        # File has no ID3v2 tag (typical for OGG/FLAC/M4A) — silently
        # skip.  This is the dominant path for non-MP3 uploads.
        return None

    for frame in id3.getall("TXXX"):
        desc = getattr(frame, "desc", "") or ""
        if desc.strip().lower() == "expiry":
            # TXXX.text is a list[str]; we take the first non-empty entry.
            for raw in frame.text:
                raw = str(raw).strip()
                if not raw:
                    continue
                return _parse_expiry(raw, filepath)
            return None

    return None


# RASTATIME 2026-10-14 - fields still missing after the mutagen pass are
# filled from the ffprobe tags (format tags merged with the first audio
# stream's tags, keys lower-cased).  ffprobe reads what mutagen's easy mode
# does not: the ID3 chunk of a WAV file (mutagen returns raw ID3 frame keys
# there), RIFF INFO, Vorbis DESCRIPTION, MP4 freeform atoms, and the tags of
# a raw ADTS file whose ID3v2 header makes mutagen give up.
# (ffprobe tag keys, metadata keys) - the first non-empty tag key wins.
_FFPROBE_TAGS_MAPPING = [
    (("title",), ("track_title",)),
    (("artist",), ("artist_name",)),
    (("album",), ("album_title",)),
    (("genre",), ("genre",)),
    (("comment", "description", "©cmt"), ("comment", "comments", "description")),
    (("date", "year"), ("year",)),
    (("composer",), ("composer",)),
    (("copyright",), ("copyright",)),
    (("label", "organization", "publisher"), ("label",)),
    (("isrc", "tsrc"), ("isrc",)),
    (("bpm", "tbpm"), ("bpm",)),
    (("language", "tlan"), ("language",)),
    # cc_files.encoder holds the encoding software: ID3 TSSE / Vorbis
    # ENCODER ("encoder") before TENC ("encoded_by", a person or company)
    (("encoder", "encoded_by"), ("encoder",)),
    (("mood", "tmoo"), ("mood",)),
    (("website",), ("website",)),
]

_FFPROBE_TIMEOUT_S = 60.0

# RASTATIME 2026-10-14 - cc_files columns the legacy app stores WITHOUT
# cutting them to length (they are no fields of the track editor, whose
# limits CcFiles::validateFileArray applies).  A longer value - TSSE strings
# like "Audiograbber 1.83.01, LAME dll 3.92, 320 Kbit/s, Joint Stereo,
# Normal quality" are common in old rips, and the ffprobe pass now fills
# encoder for almost every file - made PostgreSQL reject the import
# callback, and the track ended as a failed import.
_COLUMN_MAX_LENGTHS = {"encoder": 64}


def _clip_to_columns(metadata: dict[str, Any]) -> None:
    for key, max_length in _COLUMN_MAX_LENGTHS.items():
        value = metadata.get(key)
        if isinstance(value, str) and len(value) > max_length:
            metadata[key] = value[:max_length].rstrip()


def _is_missing(metadata: dict[str, Any], key: str) -> bool:
    return metadata.get(key) in (None, "")


def _split_track(value: str) -> tuple[str, Optional[str]]:
    """'3/12' -> ('3', '12'); '3-12' -> ('3', '12'); '3' -> ('3', None)."""
    for separator in ("/", "-"):
        if separator in value:
            number, total = value.split(separator, 1)
            return number.strip(), (total.strip() or None)
    return value.strip(), None


def _probe_with_ffprobe(
    filepath: Path,
) -> Optional[tuple[dict[str, Any], dict[str, Any], dict[str, str]]]:
    """
    (format, first audio stream, merged lower-case tags) from ffprobe, or
    None when ffprobe is missing, fails or finds no audio stream.
    """
    try:
        data = ffprobe_json(filepath, timeout=_FFPROBE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError, ValueError) as exception:
        logger.warning("ffprobe could not read %s: %s", filepath, exception)
        return None

    streams = data.get("streams") or []
    audio = next(
        (s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"),
        None,
    )
    if audio is None:
        return None

    fmt = data.get("format") or {}
    tags: dict[str, str] = {}
    for source in (fmt.get("tags"), audio.get("tags")):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            key = str(key).strip().lower()
            value = "" if value is None else str(value).strip()
            if key == "language" and value.lower() == "und":
                continue  # MP4/MKV stream language "undetermined"
            if key and value and key not in tags:
                tags[key] = value
    return fmt, audio, tags


def _mime_from_probe(format_name: str, codec: str) -> Optional[str]:
    """A mime type the legacy app knows, for a file mutagen could not read."""
    names = set(format_name.split(","))
    if "mp3" in names or codec == "mp3":
        return "audio/mp3"
    if "flac" in names:
        return "audio/flac"
    if "wav" in names:
        return "audio/wav"
    if "aac" in names:
        return "audio/aac"
    if "mp4" in names or "mov" in names:
        return "audio/mp4"
    if "ogg" in names:
        if codec == "opus":
            return "audio/opus"
        if codec == "vorbis":
            return "audio/vorbis"
        return "audio/ogg"
    return None


def _fill_from_ffprobe(
    filepath: Path,
    metadata: dict[str, Any],
    probe: tuple[dict[str, Any], dict[str, Any], dict[str, str]],
) -> None:
    fmt, audio, tags = probe

    for tag_keys, metadata_keys in _FFPROBE_TAGS_MAPPING:
        value = next((tags[k] for k in tag_keys if tags.get(k)), None)
        if value is None:
            continue
        for metadata_key in metadata_keys:
            if _is_missing(metadata, metadata_key):
                metadata[metadata_key] = value

    if tags.get("track"):
        number, total = _split_track(tags["track"])
        if number and _is_missing(metadata, "track_number"):
            metadata["track_number"] = number
        if total and _is_missing(metadata, "track_total"):
            metadata["track_total"] = total
    if _is_missing(metadata, "track_total"):
        total = tags.get("tracktotal") or tags.get("totaltracks")
        if total:
            metadata["track_total"] = total

    # Technical properties mutagen did not report (Opus has no sample_rate
    # and no bitrate in mutagen; a raw ADTS file with an ID3v2 header gives
    # nothing at all).
    if not metadata.get("sample_rate"):
        sample_rate = positive_int(audio.get("sample_rate"))
        if sample_rate:
            metadata["sample_rate"] = sample_rate
    if not metadata.get("bit_rate"):
        bit_rate = positive_int(audio.get("bit_rate")) or positive_int(fmt.get("bit_rate"))
        if bit_rate:
            metadata["bit_rate"] = bit_rate
    if not metadata.get("channels"):
        channels = positive_int(audio.get("channels"))
        if channels:
            metadata["channels"] = channels
    if not metadata.get("length_seconds"):
        length = positive_float(fmt.get("duration")) or positive_float(audio.get("duration"))
        if length:
            metadata["length_seconds"] = length
            metadata["length"] = str(timedelta(seconds=length))
    if not metadata.get("mime"):
        mime = _mime_from_probe(
            str(fmt.get("format_name") or ""),
            str(audio.get("codec_name") or ""),
        )
        if mime:
            metadata["mime"] = mime

    if "expires_at" not in metadata and tags.get("expiry"):
        expiry = _parse_expiry(tags["expiry"], filepath)
        if expiry is not None:
            metadata["expires_at"] = expiry.strftime("%Y-%m-%d")
            logger.info(
                "Expiry tag found in %s: %s",
                filepath,
                metadata["expires_at"],
            )


def _extract_with_mutagen(filepath: Path, metadata: dict[str, Any]) -> None:
    # RASTATIME 2026-10-14 - a mutagen error (e.g. HeaderNotFoundError "can't
    # sync to MPEG frame" for a raw ADTS .aac with an ID3v2 header) no longer
    # aborts the import: the ffprobe pass fills the metadata instead.
    if not _MUTAGEN_AVAILABLE:
        return
    try:
        extracted = mutagen.File(filepath, easy=True)
    except Exception as exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "mutagen could not read %s (%s: %s); using ffprobe only",
            filepath,
            type(exception).__name__,
            exception,
        )
        return
    if extracted is None:
        logger.warning("no metadata were extracted for %s", filepath)
        return

    metadata["mime"] = extracted.mime[0]

    info = extracted.info
    if hasattr(info, "sample_rate"):
        metadata["sample_rate"] = info.sample_rate

    if hasattr(info, "bitrate"):
        metadata["bit_rate"] = info.bitrate

    if hasattr(info, "length"):
        metadata["length_seconds"] = info.length
        metadata["length"] = str(timedelta(seconds=info.length))

    try:
        # Special handling for the number of channels in mp3 files.
        # 0=stereo, 1=joint stereo, 2=dual channel, 3=mono
        if metadata["mime"] in ("audio/mpeg", "audio/mp3"):
            metadata["channels"] = 1 if info.mode == 3 else 2
        else:
            metadata["channels"] = info.channels
    except (AttributeError, KeyError):
        pass

    try:
        track_number = extracted["tracknumber"]

        if isinstance(track_number, list):
            track_number = track_number[0]

        track_number_tokens = track_number
        if "/" in track_number:
            track_number_tokens = track_number.split("/")
            track_number = track_number_tokens[0]
        elif "-" in track_number:
            track_number_tokens = track_number.split("-")
            track_number = track_number_tokens[0]
        metadata["track_number"] = track_number
        track_total = track_number_tokens[1]
        metadata["track_total"] = track_total
    except (AttributeError, KeyError, IndexError):
        pass

    extracted_tags_mapping = [
        ("title", "track_title"),
        ("artist", "artist_name"),
        ("album", "album_title"),
        ("bpm", "bpm"),
        ("composer", "composer"),
        ("conductor", "conductor"),
        ("copyright", "copyright"),
        ("comment", "comment"),
        ("comment", "comments"),
        ("comment", "description"),
        ("encoded_by", "encoder"),
        ("genre", "genre"),
        ("isrc", "isrc"),
        ("label", "label"),
        ("organization", "label"),
        # ("length", "length"),
        ("language", "language"),
        ("last_modified", "last_modified"),
        ("mood", "mood"),
        ("bit_rate", "bit_rate"),
        ("replay_gain", "replaygain"),
        # ("tracknumber", "track_number"),
        # ("track_total", "track_total"),
        ("website", "website"),
        ("date", "year"),
        # ("mime_type", "mime"),
    ]

    for extracted_key, metadata_key in extracted_tags_mapping:
        try:
            metadata[metadata_key] = extracted[extracted_key]
            if isinstance(metadata[metadata_key], list):
                if len(metadata[metadata_key]):
                    metadata[metadata_key] = metadata[metadata_key][0]
                else:
                    metadata[metadata_key] = ""
        except KeyError:
            continue


def analyze_metadata(filepath_: str, metadata: dict[str, Any]):
    """
    Extract audio metadata from tags embedded in the file using mutagen,
    then fill what is still missing from ffprobe (RASTATIME 2026-10-14).
    """
    filepath = Path(filepath_)

    # Airtime <= 2.5.x required fields
    metadata["ftype"] = "audioclip"
    metadata["hidden"] = False

    # RASTATIME 2026-05-16 - Track Expiry: read custom ID3 TXXX 'Expiry'
    # tag if present.  ISO 8601 date (YYYY-MM-DD).  None ⇒ no expiry from
    # tag (the parent Podcast service may still set one for auto-expiry
    # podcasts, which takes precedence per design decision B).
    #
    # We emit the date as plain YYYY-MM-DD (not a full datetime).  Two
    # reasons: (1) the EditAudioMD form validator expects exactly that
    # format on the round-trip; (2) Expiry is a day-granularity concept,
    # not a per-second one, and PostgreSQL's CAST(... AS TIMESTAMP)
    # interprets the plain-date string as midnight on that date.
    expiry = _extract_expiry_tag(filepath)
    if expiry is not None:
        metadata["expires_at"] = expiry.strftime("%Y-%m-%d")
        logger.info(
            "Expiry tag found in %s: %s",
            filepath,
            metadata["expires_at"],
        )

    # Get file properties
    metadata["filesize"] = filepath.stat().st_size
    metadata["md5"] = compute_md5(filepath)

    # Get audio file metadata
    _extract_with_mutagen(filepath, metadata)

    probe = _probe_with_ffprobe(filepath)
    if probe is not None:
        _fill_from_ffprobe(filepath, metadata, probe)

    _clip_to_columns(metadata)
    return metadata
