"""
Tests for podcasts.download.download_episode.

Regression focus (2026-08-27): the downloaded episode must be written to
a temp file INSIDE the destination import directory, never in %TEMP%.
Under the NSSM service account a %TEMP%-born file keeps that directory's
restrictive ACL across a same-volume rename (NTFS keeps the security
descriptor), producing library files that non-elevated backups silently
skip — see BACKLOG "Podcast-Downloads: ACL sperrt den studio-User aus".
"""

import json
import tempfile
from pathlib import Path

import pytest
from requests import RequestException

from rastatime_api.podcasts import download as download_mod
from rastatime_api.podcasts.download import download_episode


# RASTATIME 2026-10-24 - no test may publish to the real broker: the
# loudness queue is stubbed for every test here; the two tests below
# that look at the hook replace the stub with their own recorder.
@pytest.fixture(autouse=True)
def _stub_loudness_queue(monkeypatch):
    monkeypatch.setattr(
        download_mod, "queue_loudness_measurement", lambda file_id, path: True
    )

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
    from rastatime_api.storage.models import File

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
    from rastatime_api.podcasts.download import _podcast_folder

    assert _podcast_folder("Reading Hour") == "Reading Hour"
    assert _podcast_folder('Radio: "Nacht" <live>?') == "Radio Nacht live"
    assert _podcast_folder(r"a/b\c|d") == "a b c d"
    assert _podcast_folder("  spaced   out  ") == "spaced out"
    assert _podcast_folder("Dots and spaces . . ") == "Dots and spaces"
    assert _podcast_folder("") == "Podcast"
    assert _podcast_folder("???") == "Podcast"
    assert len(_podcast_folder("x" * 300)) <= 80


# RASTATIME 2026-10-24 - the download queues the analyzer's loudness-only
# measurement for the new file; a broker failure never fails the download.
def test_download_queues_loudness_measurement(db, monkeypatch, tmp_path):
    monkeypatch.setattr(
        download_mod.requests, "get", lambda *a, **kw: FakeResponse()
    )
    calls = []
    monkeypatch.setattr(
        download_mod,
        "queue_loudness_measurement",
        lambda file_id, path: calls.append((file_id, path)) or True,
    )

    result = download_episode(
        episode_id=100,
        episode_url="http://feed.example/episode.mp3",
        episode_title="Measured Episode",
        podcast_name="Test Podcast",
        override_album=False,
        storage_path=str(tmp_path),
        owner_id=None,
    )

    assert result["status"] == 1, result.get("error")
    assert result["loudness_queued"] is True
    assert calls == [
        (
            result["fileid"],
            str(tmp_path / "imported" / "Test Podcast" / "podcast_ep100_episode.mp3"),
        )
    ]


def test_download_survives_queue_failure(db, monkeypatch, tmp_path):
    monkeypatch.setattr(
        download_mod.requests, "get", lambda *a, **kw: FakeResponse()
    )
    monkeypatch.setattr(
        download_mod, "queue_loudness_measurement", lambda file_id, path: False
    )

    result = download_episode(
        episode_id=101,
        episode_url="http://feed.example/episode.mp3",
        episode_title="Unqueued Episode",
        podcast_name="Test Podcast",
        override_album=False,
        storage_path=str(tmp_path),
        owner_id=None,
    )

    assert result["status"] == 1
    assert result["loudness_queued"] is False


def test_queue_loudness_measurement_publishes_the_analyzer_message(monkeypatch):
    from rastatime_api.podcasts import loudness_queue

    published = {}

    class FakeChannel:
        def exchange_declare(self, **kwargs):
            published["exchange"] = kwargs

        def basic_publish(self, **kwargs):
            published["publish"] = kwargs

    class FakeConnection:
        def __init__(self, params):
            published["params"] = params

        def channel(self):
            return FakeChannel()

        def close(self):
            published["closed"] = True

    import pika

    monkeypatch.setattr(pika, "BlockingConnection", FakeConnection)

    assert loudness_queue.queue_loudness_measurement(42, "D:/stor/imported/P/ep.mp3")
    assert published["exchange"]["exchange"] == "airtime-uploads"
    assert published["exchange"]["durable"] is True
    body = json.loads(published["publish"]["body"])
    assert body == {
        "file_id": 42,
        "tmp_file_path": "D:/stor/imported/P/ep.mp3",
        "import_directory": "",
        "original_filename": "ep.mp3",
        "options": {"loudness_only": True},
    }
    assert published["publish"]["exchange"] == "airtime-uploads"
    assert published["closed"] is True


def test_queue_loudness_measurement_reports_broker_failure(monkeypatch):
    from rastatime_api.podcasts import loudness_queue
    import pika

    def boom(params):
        raise ConnectionError("no broker")

    monkeypatch.setattr(pika, "BlockingConnection", boom)
    assert loudness_queue.queue_loudness_measurement(1, "x.mp3") is False
