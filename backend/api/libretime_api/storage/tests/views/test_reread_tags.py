"""
RASTATIME 2026-10-21 - the "Re-read Tags" endpoint: tag columns follow the
file on disk, RASTATIME-owned columns stay, missing files are skipped.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from model_bakery import baker
from mutagen.id3 import ID3, TBPM, TIT2, TMOO, TPE1

from libretime_api._fixtures import AUDIO_FILENAME
from libretime_api.storage import root as sr
from libretime_api.storage.models import File

FIXTURE = Path(__file__).resolve().parents[3] / "_fixtures" / AUDIO_FILENAME


@pytest.fixture
def root(tmp_path, monkeypatch, db):
    media = tmp_path / "media"
    (media / "imported").mkdir(parents=True)
    monkeypatch.setattr(sr, "config_root", lambda: sr.normalize(str(media)))
    sr.invalidate()
    sr.set_storage_root_setting(None)
    yield media
    sr.invalidate()


def _tagged_copy(root: Path, name: str, **tags) -> Path:
    path = root / "imported" / name
    shutil.copy(FIXTURE, path)
    id3 = ID3()
    id3.add(TIT2(encoding=3, text=tags.get("title", "")))
    id3.add(TPE1(encoding=3, text=tags.get("artist", "")))
    if "bpm" in tags:
        id3.add(TBPM(encoding=3, text=str(tags["bpm"])))
    if "mood" in tags:
        id3.add(TMOO(encoding=3, text=tags["mood"]))
    id3.save(path)
    return path


@pytest.mark.django_db
def test_reread_updates_tag_columns_and_keeps_rastatime_columns(api_client, root):
    _tagged_copy(root, "song.mp3", title="New Title", artist="New Artist", bpm=128, mood="Calm")
    file = baker.make(
        "storage.File", filepath="imported/song.mp3", exists=True, mime="audio/mp3",
        track_title="Old Title", artist_name="Old Artist", bpm=90, mood=None,
        genre="Keep?", teaser_type="today", cue_in="00:00:01", md5="0" * 32, size=1,
    )
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert response.status_code == 200, response.content
    body = response.json()
    assert (body["read"], body["changed"], body["skipped"]) == (1, 1, 0)
    changes = body["files"][0]["changes"]
    assert changes["track_title"] == ["Old Title", "New Title"]
    assert changes["artist_name"] == ["Old Artist", "New Artist"]
    assert changes["bpm"] == [90, 128]
    assert changes["mood"] == [None, "Calm"]
    assert changes["genre"] == ["Keep?", None]       # no genre tag in the file: cleared
    assert "md5" in changes and "size" in changes       # file facts follow the file
    file.refresh_from_db()
    assert (file.track_title, file.artist_name, file.bpm, file.mood) == ("New Title", "New Artist", 128, "Calm")
    assert file.teaser_type == "today"                  # RASTATIME-owned: untouched
    assert str(file.cue_in).startswith("0:00:01")
    assert file.md5 != "0" * 32 and file.size > 1


@pytest.mark.django_db
def test_reread_reports_unchanged_and_missing_files(api_client, root):
    _tagged_copy(root, "same.mp3", title="Same", artist="Same Artist")
    same = baker.make("storage.File", filepath="imported/same.mp3", exists=True, mime="audio/mp3",
                      track_title="Same", artist_name="Same Artist")
    gone = baker.make("storage.File", filepath="imported/gone.mp3", exists=True, mime="audio/mp3")
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [same.id, gone.id]}, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["read"] == 2 and body["skipped"] == 1
    by_id = {e["id"]: e for e in body["files"]}
    assert "changes" not in by_id[same.id] or not any(
        k in by_id[same.id].get("changes", {}) for k in ("track_title", "artist_name")
    )
    assert by_id[gone.id]["skipped"] == "file missing"


@pytest.mark.django_db
def test_reread_rejects_bad_input(api_client, root):
    assert api_client.post("/api/v2/files/reread-tags", {"ids": []}, format="json").status_code == 400
    assert api_client.post("/api/v2/files/reread-tags", {"ids": ["x"]}, format="json").status_code == 400
