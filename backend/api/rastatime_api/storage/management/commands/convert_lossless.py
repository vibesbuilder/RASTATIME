"""
RASTATIME 2026-10-14 - convert the lossless files already in the media
library to MP3 320 kbps (package 2 of the import format normalisation).

New imports are converted by the analyzer when Settings -> Local Machine ->
"Convert lossless audio ... to MP3 320 kbps on import" is on; this command
handles the files that were imported before (2026-10-14: id 603 FLAC and
604 WAV).

A candidate is an imported (import_status 0) ``file_exists`` row whose
stored file probes as lossless (``probe_audio`` + ``is_lossless`` of the
analyzer's convert_format module) or as Windows Media Audio (``is_wma``,
since 2026-10-21) - whatever its mime column says.  Files
that begin with an MPEG audio frame (after an optional ID3v2 tag) cannot be
lossless and are not probed, so a dry run over the whole library takes
seconds instead of one ffprobe per MP3.

Dry run by default: lists the candidates and touches nothing.  ``--yes``
converts them; ``--ids`` restricts the run to the given ids.  Per file:

* skipped while it is in cc_schedule with ``ends > now`` and
  ``starts < now + 6 h`` (the playout plays straight from the library);
* transcoded next to the original as ``<stem>.mp3`` (``<stem> (2).mp3`` ...
  when taken), tags from the database row (the database is the truth), the
  cover copied from the source;
* one transaction updates filepath, name, mime, md5, source_md5 (the old
  md5, so the duplicate check still knows the original), filesize,
  bit_rate, sample_rate, channels and mtime (as the analyzer's import
  callback would) plus the R128 loudness measured on the MP3 (its true peak
  can sit higher than the original's); id and cue points stay, the length
  only changes when the MP3 differs by more than 0.1 s (a cue-out beyond
  the new length is pulled back to it);
* a title that is just the file name (what the legacy app gives an untagged
  upload, "Interview.wav") is not written into the MP3 and becomes the new
  file name ("Interview.mp3"), as for a file converted on import;
* the original is deleted after the commit (operator decision: the lossless
  original is not kept); a failed database update deletes the MP3 and keeps
  the original;
* nothing is converted while the media library is being moved (Settings ->
  Local Machine -> Media Library Location).

ffmpeg / ffprobe are found like the analyzer finds them (FFMPEG_PATH /
FFPROBE_PATH or PATH); ``--ffmpeg-dir C:\\ffmpeg\\bin`` helps when the shell
has neither.
"""
from __future__ import annotations

import importlib
import os
import shutil
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from rastatime_shared.files import compute_md5

from ....schedule.models import Schedule
from ... import move as storage_move
from ...models import File

CONVERTER_MODULE = "rastatime_analyzer.pipeline.convert_format"
MP3_MIME = "audio/mp3"
MP3_SUFFIX = ".mp3"
SCHEDULE_GUARD = timedelta(hours=6)
LENGTH_TOLERANCE_SECONDS = 0.1


def load_converter():
    """The analyzer's convert_format module (imported late: ffmpeg paths
    may be set by --ffmpeg-dir first, and tests pass a fake instead)."""
    return importlib.import_module(CONVERTER_MODULE)


@dataclass
class Candidate:
    file_id: int
    filepath: str  # as stored (root-relative)
    path: Path  # absolute
    probe: Any  # convert_format.AudioProbe
    size: int = 0


@dataclass
class Scan:
    rows: int = 0
    candidates: List[Candidate] = field(default_factory=list)
    not_lossless: int = 0
    missing: List[str] = field(default_factory=list)
    unreadable: List[str] = field(default_factory=list)
    # --ids: why a requested id is not a candidate
    notes: List[str] = field(default_factory=list)


@dataclass
class Outcome:
    status: str  # converted | skipped | failed
    message: str


class _Skip(Exception):
    """Scheduled meanwhile - abort the transaction, keep the original."""


def starts_with_mpeg_audio(path: Path) -> bool:
    """
    True when the file begins - after an optional ID3v2 tag - with an MPEG
    audio frame header (11 sync bits, layer bits not 00; raw ADTS AAC has
    layer 00 and is not matched).  Such a file cannot be lossless.  Any
    doubt answers False, which only costs an ffprobe call.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(10)
            if len(head) == 10 and head[:3] == b"ID3":
                size = (
                    (head[6] & 0x7F) << 21
                    | (head[7] & 0x7F) << 14
                    | (head[8] & 0x7F) << 7
                    | (head[9] & 0x7F)
                )
                footer = 10 if head[5] & 0x10 else 0
                handle.seek(10 + size + footer)
                head = handle.read(2)
    except OSError:
        return False
    return (
        len(head) >= 2
        and head[0] == 0xFF
        and (head[1] & 0xE0) == 0xE0
        and (head[1] & 0x06) != 0
    )


def resolve(root: Path, filepath: str) -> Path:
    # Strip the leading "/" - on Windows Path() / "/foo" discards the root.
    return root / filepath.lstrip("/")


def unique_target(src: Path, suffix: str = MP3_SUFFIX) -> Path:
    """``<stem><suffix>`` next to ``src``; ``<stem> (2)<suffix>`` ... when taken."""
    target = src.with_suffix(suffix)
    number = 2
    while target.exists():
        target = src.with_name(f"{src.stem} ({number}){suffix}")
        number += 1
    return target


def sibling_filepath(stored: str, new_name: str) -> str:
    """The stored (root-relative) path with its last component replaced."""
    head, sep, _name = stored.replace("\\", "/").rpartition("/")
    return f"{head}{sep}{new_name}"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def tags_from_row(row: File) -> Dict[str, str]:
    """
    The tags written into the MP3, from the database row (the operator may
    have edited the metadata after the import).  Legacy stores 0 for an
    unknown track number / bpm / year; those are left out like empty values.
    """

    def known_number(value: Any) -> str:
        text = _text(value)
        return "" if text in ("", "0", "0000") else text

    tags = {
        "track_title": _text(row.track_title),
        "artist_name": _text(row.artist_name),
        "album_title": _text(row.album_title),
        "genre": _text(row.genre),
        "comment": _text(row.comment) or _text(row.description),
        "year": known_number(row.date),
        "track_number": known_number(row.track_number),
        "composer": _text(row.composer),
        "copyright": _text(row.copyright),
        "label": _text(row.label),
        "isrc": _text(row.isrc),
        "bpm": known_number(row.bpm),
        "language": _text(row.language),
        "expires_at": row.expires_at.strftime("%Y-%m-%d") if row.expires_at else "",
    }
    return {key: value for key, value in tags.items() if value}


def is_file_name_title(title: str, src: Path) -> bool:
    """
    True when the title is just the stored file's name with its extension
    ("Interview.wav") - what the legacy app sets for an untagged upload.
    """
    suffix = src.suffix.lower()
    return bool(suffix) and len(title) > len(suffix) and title.lower().endswith(suffix)


def scheduled_soon(file_id: int, now=None) -> bool:
    """In cc_schedule now or within the next SCHEDULE_GUARD hours."""
    now = now or timezone.now()
    return Schedule.objects.filter(
        file_id=file_id,
        ends_at__gt=now,
        starts_at__lt=now + SCHEDULE_GUARD,
    ).exists()


def find_candidates(root: Path, conv, ids: Optional[Sequence[int]] = None) -> Scan:
    scan = Scan()
    # Only finished imports: a pending row may still be in the analyzer's hands.
    rows = (
        File.objects.filter(exists=True, import_status=File.ImportStatus.SUCCESS)
        .exclude(filepath__isnull=True)
        .exclude(filepath="")
    )
    if ids:
        rows = rows.filter(pk__in=list(ids))
        found = set(rows.values_list("id", flat=True))
        for missing_id in sorted(set(ids) - found):
            scan.notes.append(f"{missing_id}: no imported row with file_exists and a filepath")
    for file_id, filepath in rows.order_by("id").values_list("id", "filepath"):
        scan.rows += 1
        path = resolve(root, filepath)
        if not path.is_file():
            scan.missing.append(f"{file_id}: {filepath}")
            continue
        if starts_with_mpeg_audio(path):
            scan.not_lossless += 1
            if ids:
                scan.notes.append(f"{file_id}: not lossless (MPEG audio)")
            continue
        try:
            probe = conv.probe_audio(path)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            scan.unreadable.append(f"{file_id}: {filepath} ({exc})")
            continue
        # RASTATIME 2026-10-21 - Windows Media Audio too (the analyzer converts
        # it on import since the same day; 36 files slipped in before its restart)
        if conv.is_lossless(probe) or conv.is_wma(probe):
            scan.candidates.append(
                Candidate(file_id, filepath, path, probe, path.stat().st_size)
            )
        else:
            scan.not_lossless += 1
            if ids:
                scan.notes.append(f"{file_id}: not lossless ({probe.codec})")
    return scan


def _read_mp3(path: Path) -> Dict[str, Any]:
    """The facts the analyzer would store for the new file."""
    # pylint: disable=import-outside-toplevel
    from mutagen.mp3 import MP3

    info = MP3(path).info
    return {
        "md5": compute_md5(path),
        "size": path.stat().st_size,
        "bit_rate": int(info.bitrate),
        "sample_rate": int(info.sample_rate),
        # Same rule as analyze_metadata: mode 3 = mono, everything else 2
        "channels": 1 if getattr(info, "mode", None) == 3 else 2,
        "length_seconds": float(info.length),
    }


def _measure_loudness(path: Path) -> Dict[str, Any]:
    """
    EBU R128 of the new MP3 with the analyzer's own step.  The integrated
    loudness barely moves, but the MP3's true peak can sit higher than the
    lossless original's, and the playout caps a positive track gain by it.
    A failed measurement keeps the stored values (empty result).
    """
    # pylint: disable=import-outside-toplevel
    try:
        from rastatime_analyzer.pipeline.analyze_loudness import analyze_loudness

        measured = analyze_loudness(str(path), {})
    except Exception:  # pylint: disable=broad-exception-caught
        return {}
    return {key: value for key, value in measured.items() if value is not None}


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def convert_candidate(
    cand: Candidate,
    conv,
    now_fn: Callable = timezone.now,
    read_mp3: Callable[[Path], Dict[str, Any]] = _read_mp3,
    measure_loudness: Optional[Callable[[Path], Dict[str, Any]]] = None,
) -> Outcome:
    """Convert one file; the original is only touched after the commit."""
    measure_loudness = measure_loudness or _measure_loudness
    if scheduled_soon(cand.file_id, now_fn()):
        return Outcome("skipped", "scheduled now or within the next 6 hours")

    row = File.objects.get(pk=cand.file_id)
    old_md5 = _text(row.md5) or compute_md5(cand.path)
    dest = unique_target(cand.path)
    new_filepath = sibling_filepath(cand.filepath, dest.name)
    tags = tags_from_row(row)
    if is_file_name_title(tags.get("track_title", ""), cand.path):
        del tags["track_title"]  # a file name is no title tag

    try:
        conv.transcode_to_mp3(cand.path, dest, tags, probe=cand.probe)
        facts = read_mp3(dest)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _remove(dest)
        return Outcome("failed", f"conversion failed, original kept: {exc}")
    loudness = measure_loudness(dest)

    changes: Dict[str, Any] = {}
    old_length = None
    try:
        with transaction.atomic():
            current = File.objects.select_for_update().get(pk=cand.file_id)
            if current.filepath != cand.filepath:
                raise RuntimeError(f"filepath changed meanwhile to {current.filepath!r}")
            if scheduled_soon(cand.file_id, now_fn()):
                raise _Skip()
            old_length = current.length
            changes = {
                "filepath": new_filepath,
                "name": dest.name,
                "mime": MP3_MIME,
                "md5": facts["md5"],
                "source_md5": _text(current.md5) or old_md5,
                "size": facts["size"],
                "bit_rate": facts["bit_rate"],
                "sample_rate": facts["sample_rate"],
                "channels": facts["channels"],
                "updated_at": now_fn(),
                **loudness,
            }
            title = _text(current.track_title)
            if is_file_name_title(title, cand.path):
                changes["track_title"] = title[: -len(cand.path.suffix)] + MP3_SUFFIX
            new_length = timedelta(seconds=facts["length_seconds"])
            if current.length is None or abs(
                (new_length - current.length).total_seconds()
            ) > LENGTH_TOLERANCE_SECONDS:
                changes["length"] = new_length
                # Cue-out never beyond the length (same rule as the Cue Points editor)
                if current.cue_out is not None and current.cue_out > new_length:
                    changes["cue_out"] = new_length
            File.objects.filter(pk=cand.file_id).update(**changes)
    except _Skip:
        _remove(dest)
        return Outcome("skipped", "got scheduled during the conversion, MP3 discarded")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _remove(dest)
        return Outcome("failed", f"database update failed, original kept: {exc}")

    note = ""
    if "length" in changes:
        note = f", length {old_length} -> {changes['length']}"
    try:
        cand.path.unlink()
    except OSError as exc:
        return Outcome(
            "converted",
            f"-> {new_filepath}{note}; WARNING original not deleted ({exc}), remove it by hand",
        )
    return Outcome("converted", f"-> {new_filepath}{note}")


def _use_ffmpeg_dir(directory: str) -> None:
    os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
    for env, name in (("FFMPEG_PATH", "ffmpeg"), ("FFPROBE_PATH", "ffprobe")):
        exe = shutil.which(name, path=directory)
        if exe and not os.environ.get(env):
            os.environ[env] = exe


def _require_tool(env: str, name: str) -> None:
    if shutil.which(os.environ.get(env) or name) is None:
        raise CommandError(
            f"{name} not found - set {env}, put ffmpeg on PATH or pass --ffmpeg-dir"
        )


class Command(BaseCommand):
    help = "Convert lossless files already in the library (WAV, FLAC, ...) to MP3 320 kbps."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--yes", action="store_true", help="Convert (default: dry run).")
        parser.add_argument("--ids", nargs="+", type=int, help="Only these cc_files ids.")
        parser.add_argument("--root", help="Storage root (default: the effective library root).")
        parser.add_argument("--ffmpeg-dir", help="Directory holding ffmpeg and ffprobe.")

    def handle(self, *args, **options):
        out = self.stdout.write
        if options.get("ffmpeg_dir"):
            _use_ffmpeg_dir(options["ffmpeg_dir"])
        _require_tool("FFPROBE_PATH", "ffprobe")
        if options.get("yes"):
            _require_tool("FFMPEG_PATH", "ffmpeg")

        from ...root import get_storage_root  # noqa: PLC0415

        root = Path(options.get("root") or get_storage_root(refresh=True))
        if not root.is_dir():
            raise CommandError(f"storage root does not exist: {root}")
        if options.get("yes") and storage_move.JOB.is_locked():
            raise CommandError(
                "the media library is being moved - run this again once the move has finished"
            )
        conv = load_converter()

        scan = find_candidates(root, conv, options.get("ids"))
        out(f"storage root: {root}")
        out(
            f"rows scanned: {scan.rows}  lossless: {len(scan.candidates)}  "
            f"not lossless: {scan.not_lossless}  missing on disk: {len(scan.missing)}  "
            f"unreadable: {len(scan.unreadable)}"
        )
        for line in scan.notes + scan.missing[:10] + scan.unreadable[:10]:
            out(f"  {line}")
        for cand in scan.candidates:
            probe = cand.probe
            out(
                f"  {cand.file_id}: {probe.codec}, {probe.sample_rate} Hz, {probe.channels} ch, "
                f"{cand.size / 1e6:.1f} MB  {cand.filepath}"
            )
        if not options.get("yes"):
            out("DRY RUN - nothing changed (use --yes to convert)")
            return
        if not scan.candidates:
            out("nothing to do")
            return

        counts = {"converted": 0, "skipped": 0, "failed": 0}
        for cand in scan.candidates:
            if storage_move.JOB.is_locked():  # a move started meanwhile
                outcome = Outcome("skipped", "the media library is being moved")
            else:
                outcome = convert_candidate(cand, conv)
            counts[outcome.status] += 1
            out(f"{cand.file_id}: {outcome.status.upper()} {outcome.message}")
        out(
            f"done: {counts['converted']} converted, {counts['skipped']} skipped, "
            f"{counts['failed']} failed"
        )
        if counts["failed"]:
            raise CommandError(f"{counts['failed']} file(s) failed - originals kept")
