"""
RASTATIME 2026-10-28 - /api/v2/storage/imports/failed: failed library rows
and the files the analyzer left in organize/.
"""

import os
import time
from datetime import UTC, datetime, timedelta, timezone

import pytest
from django.conf import settings
from model_bakery import baker

from rastatime_api.storage import root as sr
from rastatime_api.storage.views import imports as imports_view


@pytest.fixture
def root(tmp_path, monkeypatch):
    stor = tmp_path / "stor"
    (stor / "organize").mkdir(parents=True)
    monkeypatch.setattr(sr, "get_storage_root", lambda refresh=False: str(stor))
    return stor


@pytest.mark.django_db
def test_payload_lists_failed_rows_and_leftovers(root):
    now = datetime.now(tz=UTC)
    failed = baker.make(
        "storage.File",
        import_status=2,
        track_title="Broken Song.mp3",
        comment="ffprobe could not read the file",
        created_at=now - timedelta(hours=3),
        filepath="",
    )
    baker.make("storage.File", import_status=0, track_title="Fine", created_at=now)
    pending = baker.make("storage.File", import_status=1, track_title="Pending", created_at=now)

    leftover_failed = root / "organize" / f"{failed.id}-Broken Song.mp3"
    leftover_failed.write_bytes(b"x" * 10)
    old = time.time() - 3 * 86400
    os.utime(leftover_failed, (old, old))
    (root / "organize" / f"{pending.id}-Pending.mp3").write_bytes(b"y")
    (root / "organize" / "orphan-without-id.mp3").write_bytes(b"z")

    data = imports_view.failed_imports_payload()
    assert [f["id"] for f in data["failed"]] == [failed.id]
    assert data["failed"][0]["comment"] == "ffprobe could not read the file"
    assert data["failed"][0]["age_seconds"] >= 3 * 3600 - 5
    by_name = {row["file"]: row for row in data["leftovers"]}
    assert by_name[f"{failed.id}-Broken Song.mp3"]["row"] == "failed"
    assert by_name[f"{failed.id}-Broken Song.mp3"]["age_seconds"] >= 3 * 86400 - 5
    assert by_name[f"{pending.id}-Pending.mp3"]["row"] == "pending"
    assert by_name["orphan-without-id.mp3"]["row"] == "missing"
    assert by_name["orphan-without-id.mp3"]["file_id"] is None
    assert data["organize_dir"].endswith("organize")


@pytest.mark.django_db
def test_endpoint_needs_the_api_key(client, root):
    assert client.get("/api/v2/storage/imports/failed").status_code == 403
    resp = client.get(
        "/api/v2/storage/imports/failed",
        HTTP_AUTHORIZATION=f"Api-Key {settings.CONFIG.general.api_key}",
    )
    assert resp.status_code == 200
    assert resp.json() == {"failed": [], "leftovers": [], "organize_dir": str(root / "organize")}


@pytest.mark.django_db
def test_missing_organize_folder_is_fine(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "get_storage_root", lambda refresh=False: str(tmp_path / "nowhere"))
    data = imports_view.failed_imports_payload()
    assert data["leftovers"] == []
