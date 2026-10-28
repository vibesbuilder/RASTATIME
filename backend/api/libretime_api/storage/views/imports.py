"""
RASTATIME 2026-10-28 - failed imports and what they left behind.

    GET /api/v2/storage/imports/failed
    {
      "failed": [{"id", "name", "comment", "utime", "age_seconds"}, ...],
      "leftovers": [{"file", "size", "age_seconds", "file_id", "row": "failed" | "pending" | "missing"}, ...],
      "organize_dir": "D:/stor/organize"
    }

``failed`` are the library rows with ``import_status = 2`` (the Upload
page's "Failed" filter); ``leftovers`` are the files still sitting in
``<root>/organize/`` - the analyzer's staging folder - with the state of the
row their ``<id>-`` prefix points at.  The playout's preflight scan turns
both into the dashboard warning ``imports_failed``; the Upload page's
"Clear" removes the row and its leftover together.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from rest_framework.response import Response
from rest_framework.views import APIView

from .. import root as storage_root
from ..models import File

IMPORT_STATUS_FAILED = 2
IMPORT_STATUS_PENDING = 1
_ID_PREFIX = re.compile(r"^(\d+)-")


def organize_dir(root: str | None = None) -> Path:
    return Path(root or storage_root.get_storage_root()) / "organize"


def failed_imports_payload(root: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    failed = []
    for row in File.objects.filter(import_status=IMPORT_STATUS_FAILED).order_by("-created_at", "-id")[:200]:
        utime = row.created_at
        if utime is not None and utime.tzinfo is None:
            utime = utime.replace(tzinfo=timezone.utc)  # cc_files.utime is stored in UTC
        age = int((now - utime).total_seconds()) if utime else None
        failed.append({
            "id": row.id,
            "name": row.track_title or row.name or "",
            "comment": (row.comment or "")[:300],
            "utime": utime.isoformat() if utime else None,
            "age_seconds": age,
        })

    leftovers = []
    folder = organize_dir(root)
    if folder.is_dir():
        now_ts = time.time()
        for entry in sorted(folder.iterdir()):
            if not entry.is_file():
                continue
            try:
                st = entry.stat()
            except OSError:
                continue
            match = _ID_PREFIX.match(entry.name)
            file_id = int(match.group(1)) if match else None
            state = "missing"
            if file_id is not None:
                status = File.objects.filter(pk=file_id).values_list("import_status", flat=True).first()
                if status == IMPORT_STATUS_FAILED:
                    state = "failed"
                elif status == IMPORT_STATUS_PENDING:
                    state = "pending"
                elif status is not None:
                    state = "imported"
            leftovers.append({
                "file": entry.name,
                "size": st.st_size,
                "age_seconds": int(now_ts - st.st_mtime),
                "file_id": file_id,
                "row": state,
            })
    return {"failed": failed, "leftovers": leftovers, "organize_dir": str(folder)}


class FailedImportsView(APIView):
    def get(self, request):
        return Response(failed_imports_payload())
