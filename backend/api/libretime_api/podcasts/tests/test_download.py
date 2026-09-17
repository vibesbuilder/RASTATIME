"""
Tests for podcasts.download.download_episode.

Regression focus (2026-08-27): the downloaded episode must be written to
a temp file INSIDE the destination import directory, never in %TEMP%.
Under the NSSM service account a %TEMP%-born file keeps that directory's
restrictive ACL across a same-volume rename (NTFS keeps the security
descriptor), producing library files that non-elevated backups silently
skip — see BACKLOG "Podcast-Downloads: ACL sperrt den studio-User aus".
"""

import tempfile
from pathlib import Path

import pytest
from requests import RequestException

from libretime_api.podcasts import download as download_mod
from libretime_api.podcasts.download import download_episode

AUDIO_BYTES = b"ID3" + b"\x00" * 64 + b"fake-mp3-payload" * 32


class FakeResponse:
    """Minimal stand-in for requests.get(..., stream=True)."""

    def __init__(self, url="http://feed.example/episode.mp3"):
        self.url = url
        self.headers = {}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=65536):
        yield AUDIO_BYTES

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture(name="spy_tempfile")
def _spy_tempfile(monkeypatch):
    """Record the kwargs download_episode passes to NamedTemporaryFile."""
    calls = []
    real = tempfile.NamedTemporaryFile

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(download_mod, "NamedTemporaryFile", spy)
    return calls


def test_download_writes_temp_file_inside_import_dir(
    db, monkeypatch, tmp_path, spy_tempfile
):
    monkeypatch.setattr(
        download_mod.requests, "get", lambda *a, **kw: FakeResponse()
    )

    result = download_episode(
        episode_id=99,
        episode_url="http://feed.example/episode.mp3",
        episode_title="Test Episode",
        podcast_name="Test Podcast",
        override_album=True,
        storage_path=str(tmp_path),
        owner_id=None,
    )

    assert result["status"] == 1, result.get("error")
    # RASTATIME 2026-09-17 - one folder per podcast under imported/.
    import_dir = tmp_path / "imported" / "Test Podcast"

    # The regression guard: the temp file was born in the destination
    # directory (ACL inheritance), not in the system temp directory.
    assert len(spy_tempfile) == 1
    assert Path(spy_tempfile[0]["dir"]) == import_dir

    # Final file is in place, no temp remnants left behind.
    dest = import_dir / "podcast_ep99_episode.mp3"
    assert dest.is_file()
    assert dest.read_bytes() == AUDIO_BYTES
    assert list(import_dir.glob("podcast_tmp_*")) == []

    # cc_files row exists with the storage-relative path.
    from libretime_api.storage.models import File

    db_file = File.objects.get(id=result["fileid"])
    assert db_file.filepath == "imported/Test Podcast/podcast_ep99_episode.mp3"


def test_download_failure_leaves_no_file(db, monkeypatch, tmp_path):
    def boom(*a, **kw):
        raise RequestException("connection refused")

    monkeypatch.setattr(download_mod.requests, "get", boom)

    result = download_episode(
        episode_id=100,
        episode_url="http://feed.example/episode.mp3",
        episode_title=None,
        podcast_name="Test Podcast",
        override_album=False,
        storage_path=str(tmp_path),
        owner_id=None,
    )

    assert result["status"] == 0
    assert "download failed" in result["error"]
    import_dir = tmp_path / "imported" / "Test Podcast"
    assert not import_dir.exists() or list(import_dir.iterdir()) == []


# ---- per-podcast folder names (RASTATIME 2026-09-17) ------------------------


def test_podcast_folder_is_windows_safe():
    from libretime_api.podcasts.download import _podcast_folder

    assert _podcast_folder("Reading Hour") == "Reading Hour"
    assert _podcast_folder('Radio: "Nacht" <live>?') == "Radio Nacht live"
    assert _podcast_folder(r"a/b\c|d") == "a b c d"
    assert _podcast_folder("  spaced   out  ") == "spaced out"
    assert _podcast_folder("Dots and spaces . . ") == "Dots and spaces"
    assert _podcast_folder("") == "Podcast"
    assert _podcast_folder("???") == "Podcast"
    assert len(_podcast_folder("x" * 300)) <= 80
