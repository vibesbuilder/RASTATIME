"""
RASTATIME 2026-10-21 - "Re-read Tags": refresh the tag-derived columns of
library files from the files on disk (operator go 2026-10-21).

RASTATIME never re-reads a file after the import; the database is the
truth for the library and the playout.  A file edited afterwards in
Windows (title, artist, ...) therefore keeps its old row until the
operator asks for it: the Library's "Re-read Tags" button posts the
selected ids here (via the legacy proxy that adds the API key).

Per file the analyzer's own tag reader (``analyze_metadata``, the same
mapping every import uses) is run on the stored file; only the columns a
tag can carry are compared and written (``TAG_FIELDS``) - the columns
RASTATIME owns (track type, teaser, cue points, loudness, expiry,
requests, flags) are never touched.  The checksum, size and modification
time follow the file so the duplicate check and the library stay in
step.  Reading is harmless for a file that is on air; nothing is written
to the file.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import File
from ..root import get_storage_root

logger = logging.getLogger(__name__)

# analyzer key -> File model field.  A tag that is absent from the file
# clears the column (the file is the truth the operator asked for).
TAG_FIELDS: dict[str, str] = {
    "track_title": "track_title",
    "artist_name": "artist_name",
    "album_title": "album_title",
    "genre": "genre",
    "year": "date",
    "track_number": "track_number",
    "comment": "comment",
    "composer": "composer",
    "copyright": "copyright",
    "label": "label",
    "isrc": "isrc",
    "bpm": "bpm",
    "language": "language",
    "mood": "mood",
}
# file facts that follow the file (never cleared)
FILE_FIELDS: dict[str, str] = {
    "md5": "md5",
    "filesize": "size",
    "bit_rate": "bit_rate",
    "sample_rate": "sample_rate",
    "channels": "channels",
}
MAX_IDS = 500


def _normalise(field: str, value: Any) -> Any:
    if value in ("", None):
        return None
    if field in ("track_number", "bpm", "size", "bit_rate", "sample_rate", "channels"):
        try:
            return int(str(value).strip().split("/")[0])
        except (TypeError, ValueError):
            return None
    text = str(value).strip()
    limit = (
        File._meta.get_field(field).max_length
        if hasattr(File._meta.get_field(field), "max_length")
        else None
    )
    if limit and len(text) > limit:
        text = text[:limit].rstrip()
    return text or None


def _reread_one(file: File, root: Path) -> tuple[dict[str, list[Any]], Optional[str]]:
    """(changes {field: [old, new]}, skip reason)."""
    from rastatime_analyzer.pipeline.analyze_metadata import analyze_metadata

    rel = (file.filepath or "").lstrip("/").replace("\\", "/")
    if not rel:
        return {}, "no path"
    path = root / rel
    if not path.is_file():
        return {}, "file missing"
    try:
        found = analyze_metadata(str(path), {})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {}, f"unreadable ({exc})"
    changes: dict[str, list[Any]] = {}
    for key, field in TAG_FIELDS.items():
        new = _normalise(field, found.get(key))
        old = _normalise(field, getattr(file, field))
        if new != old:
            changes[field] = [old, new]
    for key, field in FILE_FIELDS.items():
        if key not in found:
            continue
        new = _normalise(field, found.get(key))
        old = _normalise(field, getattr(file, field))
        if new is not None and new != old:
            changes[field] = [old, new]
    return changes, None


class RereadTagsView(APIView):
    """POST {"ids": [...]} -> per-file report; writes the changed columns."""

    def post(self, request):
        ids = request.data.get("ids") if isinstance(request.data, dict) else None
        if not isinstance(ids, list) or not ids:
            return Response(
                {"errors": ["ids: a non-empty list is required"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ids = [int(i) for i in ids][:MAX_IDS]
        except (TypeError, ValueError):
            return Response({"errors": ["ids: integers only"]}, status=status.HTTP_400_BAD_REQUEST)
        root = Path(str(get_storage_root()))
        report = []
        changed_files = 0
        for file in File.objects.filter(pk__in=ids).order_by("pk"):
            changes, skip = _reread_one(file, root)
            entry: dict[str, Any] = {"id": file.pk, "title": file.track_title or file.name}
            if skip:
                entry["skipped"] = skip
            elif changes:
                values = {field: new for field, (_, new) in changes.items()}
                values["updated_at"] = datetime.now(UTC)
                with transaction.atomic():
                    File.objects.filter(pk=file.pk).update(**values)
                changed_files += 1
                entry["changes"] = changes
                logger.info("reread-tags: file %s (%s): %s", file.pk, entry["title"], changes)
            report.append(entry)
        return Response(
            {
                "read": len(report),
                "changed": changed_files,
                "skipped": sum(1 for e in report if "skipped" in e),
                "files": report,
            }
        )
