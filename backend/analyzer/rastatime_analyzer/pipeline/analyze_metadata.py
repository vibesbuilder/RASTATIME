import logging
import re
import subprocess
from collections.abc import Iterable
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


# RASTATIME 2026-11-08 - the custom tags read on import, by metadata key
# (= cc_files column).  A tag name counts in any spelling: lower case,
# without blanks, underscores and hyphens, so "Expiry Date", "EXPIRY_DATE"
# and "expirydate" are one name (see _tag_name).
_CUSTOM_TAGS: dict[str, tuple[str, ...]] = {
    "expires_at": ("expiry", "expirydate"),
    "enabled_from": ("enabledate", "enabledfrom"),
    "country": ("country",),
}
_DATE_KEYS = ("expires_at", "enabled_from")
_DATE_LABELS = {"expires_at": "Expiry", "enabled_from": "Enable Date"}
# YYYY-MM-DD or YYYYMMDD, nothing else (2026-11-08 or 20261108)
_DATE_FORMATS = (
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{8}$"), "%Y%m%d"),
)
_CUSTOM_KEY_BY_NAME = {name: key for key, names in _CUSTOM_TAGS.items() for name in names}


def _tag_name(name: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(name)).lower()


def _parse_tag_date(raw: str, key: str, filepath: Path) -> Optional[str]:
    """A date tag value as YYYY-MM-DD; None (with a warning) otherwise."""
    text = str(raw).strip()
    for pattern, fmt in _DATE_FORMATS:
        if pattern.match(text):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                break  # 2026-02-30, 20261340
    logger.warning(
        "%s tag value %r in %s is no date (YYYY-MM-DD or YYYYMMDD); ignoring",
        _DATE_LABELS.get(key, key),
        text,
        filepath,
    )
    return None


def _custom_tag_values(pairs: Iterable[tuple[Any, Any]], filepath: Path) -> dict[str, str]:
    """
    {metadata key: value} from (tag name, value) pairs.  The first usable
    value of a key wins; a date that does not parse counts as absent.
    """
    found: dict[str, str] = {}
    for name, raw in pairs:
        key = _CUSTOM_KEY_BY_NAME.get(_tag_name(name))
        if key is None or key in found:
            continue
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if key in _DATE_KEYS:
            date_text = _parse_tag_date(text, key, filepath)
            if date_text is not None:
                found[key] = date_text
        else:
            found[key] = text
    return found


def _read_txxx(filepath: Path) -> Optional[list[tuple[str, str]]]:
    """
    (description, first non-empty text) of every ID3v2 TXXX frame; None when
    the file has no ID3v2 tag (OGG/FLAC/M4A, the ID3 chunk of a WAV file).

    Mutagen's EasyID3 does not expose generic TXXX frames, so the raw ID3 is
    read here.  Files without an ID3v2 tag get their custom tags from the
    ffprobe pass (RASTATIME 2026-10-14).
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
        return None

    pairs = []
    for frame in id3.getall("TXXX"):
        desc = getattr(frame, "desc", "") or ""
        text = next((str(t).strip() for t in frame.text if str(t).strip()), "")
        if text:
            pairs.append((desc, text))
    return pairs


def read_custom_tags(filepath_: str) -> dict[str, str]:
    """
    RASTATIME 2026-11-08 - expires_at / enabled_from (YYYY-MM-DD) and country
    from the file's own tags, without ffprobe and without a checksum: ID3v2
    TXXX frames, MP4 freeform atoms, Vorbis comments.  Used by the one-time
    country backfill; the import reads the same tags in analyze_metadata.
    """
    filepath = Path(filepath_)
    pairs = _read_txxx(filepath)
    if pairs is not None:
        return _custom_tag_values(pairs, filepath)
    if not _MUTAGEN_AVAILABLE:
        return {}
    try:
        extracted = mutagen.File(filepath)
    except Exception:  # pylint: disable=broad-exception-caught
        return {}
    if extracted is None or not extracted.tags:
        return {}
    pairs = []
    for name, value in extracted.tags.items():
        name = str(name)
        if name.startswith("----:"):
            name = name.rsplit(":", 1)[-1]  # ----:com.apple.iTunes:COUNTRY
        if isinstance(value, list):
            value = value[0] if value else ""
        if isinstance(value, bytes):  # MP4FreeForm is a bytes subclass
            value = bytes(value).decode("utf-8", "replace")
        pairs.append((name, value))
    return _custom_tag_values(pairs, filepath)


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
_COLUMN_MAX_LENGTHS = {"encoder": 64, "country": 64}


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


def _fill_custom_tags_from_ffprobe(
    filepath: Path, metadata: dict[str, Any], tags: dict[str, str]
) -> None:
    """Custom tags of a file without ID3v2 tag (Vorbis, MP4 freeform, WAV ID3 chunk)."""
    for key, value in _custom_tag_values(tags.items(), filepath).items():
        if _is_missing(metadata, key):
            metadata[key] = value
            logger.info("%s tag found in %s: %s", key, filepath, value)


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

    # RASTATIME 2026-05-16 / 2026-11-08 - custom ID3 TXXX tags: "Expiry" /
    # "Expiry Date" (Track Expiry), "Enable Date" / "Enabled From" (the track
    # stays disabled until that day) and "Country" (Music by Country).
    # The dates go out as plain YYYY-MM-DD (also when the tag says
    # YYYYMMDD): the EditAudioMD form validator expects exactly that on the
    # round-trip, the concept is a day, and PostgreSQL's
    # CAST(... AS TIMESTAMP) reads the plain date as midnight on that date.
    txxx = _read_txxx(filepath)
    if txxx is not None:
        for key, value in _custom_tag_values(txxx, filepath).items():
            metadata[key] = value
            logger.info("%s tag found in %s: %s", key, filepath, value)

    # Get file properties
    metadata["filesize"] = filepath.stat().st_size
    metadata["md5"] = compute_md5(filepath)

    # Get audio file metadata
    _extract_with_mutagen(filepath, metadata)

    probe = _probe_with_ffprobe(filepath)
    if probe is not None:
        _fill_from_ffprobe(filepath, metadata, probe)
        # a file WITH an ID3v2 tag was read above; ffprobe shows the same
        # TXXX frames, which would only repeat an invalid date's warning
        if txxx is None:
            _fill_custom_tags_from_ffprobe(filepath, metadata, probe[2])

    _clip_to_columns(metadata)
    return metadata
