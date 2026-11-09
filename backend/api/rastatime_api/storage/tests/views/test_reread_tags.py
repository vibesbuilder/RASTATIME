"""
RASTATIME 2026-10-21 - the "Re-read Tags" endpoint: tag columns follow the
file on disk, RASTATIME-owned columns stay, missing files are skipped.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from model_bakery import baker
from mutagen.id3 import ID3, TBPM, TIT2, TMED, TMOO, TPE1, TXXX

from rastatime_api._fixtures import AUDIO_FILENAME
from rastatime_api.storage import root as sr
from rastatime_api.storage.models import File

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
    if "media_type" in tags:
        id3.add(TMED(encoding=3, text=tags["media_type"]))
    for desc, text in tags.get("txxx", {}).items():
        id3.add(TXXX(encoding=3, desc=desc, text=text))
    id3.save(path)
    return path


@pytest.mark.django_db
def test_reread_updates_tag_columns_and_keeps_rastatime_columns(api_client, root):
    _tagged_copy(root, "song.mp3", title="New Title", artist="New Artist", bpm=128, mood="Calm")
    file = baker.make(
        "storage.File",
        filepath="imported/song.mp3",
        exists=True,
        mime="audio/mp3",
        track_title="Old Title",
        artist_name="Old Artist",
        bpm=90,
        mood=None,
        genre="Keep?",
        teaser_type="today",
        cue_in="00:00:01",
        md5="0" * 32,
        size=1,
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
    assert changes["genre"] == ["Keep?", None]  # no genre tag in the file: cleared
    assert "md5" in changes and "size" in changes  # file facts follow the file
    file.refresh_from_db()
    assert (file.track_title, file.artist_name, file.bpm, file.mood) == (
        "New Title",
        "New Artist",
        128,
        "Calm",
    )
    assert file.teaser_type == "today"  # RASTATIME-owned: untouched
    assert str(file.cue_in).startswith("0:00:01")
    assert file.md5 != "0" * 32 and file.size > 1


@pytest.mark.django_db
def test_reread_reports_unchanged_and_missing_files(api_client, root):
    _tagged_copy(root, "same.mp3", title="Same", artist="Same Artist")
    same = baker.make(
        "storage.File",
        filepath="imported/same.mp3",
        exists=True,
        mime="audio/mp3",
        track_title="Same",
        artist_name="Same Artist",
    )
    gone = baker.make("storage.File", filepath="imported/gone.mp3", exists=True, mime="audio/mp3")
    response = api_client.post(
        "/api/v2/files/reread-tags", {"ids": [same.id, gone.id]}, format="json"
    )
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
    assert (
        api_client.post("/api/v2/files/reread-tags", {"ids": []}, format="json").status_code == 400
    )
    assert (
        api_client.post("/api/v2/files/reread-tags", {"ids": ["x"]}, format="json").status_code
        == 400
    )


@pytest.mark.django_db
def test_reread_takes_the_country_but_not_the_dates(api_client, root):
    # RASTATIME 2026-11-08 - operator decision: Re-read Tags takes the country
    # from the file; expiry and enable date set in RASTATIME stay
    _tagged_copy(
        root,
        "notice.mp3",
        title="Notice",
        artist="Station",
        txxx={"COUNTRY": "Austria", "Expiry Date": "20300101", "Enable Date": "2029-01-01"},
    )
    file = baker.make(
        "storage.File",
        filepath="imported/notice.mp3",
        exists=True,
        mime="audio/mp3",
        track_title="Notice",
        artist_name="Station",
        country="UK",
        expires_at=None,
        enabled_from=None,
    )
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert response.status_code == 200, response.content
    changes = response.json()["files"][0]["changes"]
    assert changes["country"] == ["UK", "Austria"]
    assert "expires_at" not in changes and "enabled_from" not in changes
    file.refresh_from_db()
    assert file.country == "Austria"
    assert file.expires_at is None and file.enabled_from is None


def _types():
    # codes no seeded track type uses
    return (
        baker.make(
            "storage.Library", code="t_music", description="", name="Test Music", enabled=True
        ),
        baker.make(
            "storage.Library", code="t_jngl", description="", name="Test Jingles", enabled=True
        ),
        baker.make(
            "storage.Library", code="t_off", description="", name="Test Hidden", enabled=False
        ),
    )


def _typed_file(root: Path, name: str, media_type: str, library) -> File:
    _tagged_copy(root, name, title="Jingle", artist="Station", media_type=media_type)
    return baker.make(
        "storage.File",
        filepath=f"imported/{name}",
        exists=True,
        mime="audio/mp3",
        track_title="Jingle",
        artist_name="Station",
        library=library,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("media_type", ["Test Jingles", "TEST JINGLES", "t_jngl", " t_JNGL "])
def test_reread_takes_the_track_type_from_the_media_type_tag(api_client, root, media_type):
    # RASTATIME 2026-11-09 - operator decision: code or name, any case
    music, jngl, _ = _types()
    file = _typed_file(root, "jingle.mp3", media_type, music)
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["files"][0]["changes"]["track_type"] == ["t_music", "t_jngl"]
    file.refresh_from_db()
    assert file.library_id == jngl.pk


@pytest.mark.django_db
@pytest.mark.parametrize("media_type", ["Test Jingle", "CD", "Digital Media", "Test Hidden"])
def test_reread_keeps_the_track_type_for_an_unknown_or_hidden_type(api_client, root, media_type):
    music, _, _ = _types()
    file = _typed_file(root, "other.mp3", media_type, music)
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert response.status_code == 200, response.content
    assert "track_type" not in response.json()["files"][0].get("changes", {})
    file.refresh_from_db()
    assert file.library_id == music.pk


@pytest.mark.django_db
def test_reread_without_media_type_keeps_the_track_type(api_client, root):
    music, _, _ = _types()
    _tagged_copy(root, "plain.mp3", title="Plain", artist="Station")
    file = baker.make(
        "storage.File",
        filepath="imported/plain.mp3",
        exists=True,
        mime="audio/mp3",
        track_title="Old",
        artist_name="Station",
        library=music,
    )
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert "track_type" not in response.json()["files"][0]["changes"]
    file.refresh_from_db()
    assert file.library_id == music.pk


@pytest.mark.django_db
def test_reread_sets_a_type_on_a_track_without_one(api_client, root):
    _, jngl, _ = _types()
    file = _typed_file(root, "untyped.mp3", "Test Jingles", None)
    response = api_client.post("/api/v2/files/reread-tags", {"ids": [file.id]}, format="json")
    assert response.json()["files"][0]["changes"]["track_type"] == [None, "t_jngl"]
    file.refresh_from_db()
    assert file.library_id == jngl.pk
