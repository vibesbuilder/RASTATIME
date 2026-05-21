import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

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

from libretime_shared.files import compute_md5

logger = logging.getLogger(__name__)


def flatten(xss):
    return [x for xs in xss for x in xs]


def comment_get(id3, _):
    comments = [v.text for k, v in id3.items() if "COMM" in k or "comment" in k]

    return flatten(comments)


if _MUTAGEN_AVAILABLE:
    EasyID3.RegisterKey("comment", comment_get)


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
    comments in OGG/FLAC, MP4 atoms) are not currently scanned because
    operator workflow is dominantly MP3 -> ID3v2.
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
                try:
                    parsed = datetime.strptime(raw, "%Y-%m-%d")
                    return parsed
                except ValueError:
                    logger.warning(
                        "Expiry tag value %r in %s is not ISO 8601 date "
                        "(YYYY-MM-DD); ignoring",
                        raw, filepath,
                    )
                    return None
            return None

    return None


def analyze_metadata(filepath_: str, metadata: Dict[str, Any]):
    """
    Extract audio metadata from tags embedded in the file using mutagen.
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
            filepath, metadata["expires_at"],
        )

    # Get file properties
    metadata["filesize"] = filepath.stat().st_size
    metadata["md5"] = compute_md5(filepath)

    # Get audio file metadata
    extracted = mutagen.File(filepath, easy=True)
    if extracted is None:
        logger.warning("no metadata were extracted for %s", filepath)
        return metadata

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

    return metadata
