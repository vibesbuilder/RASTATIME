"""
RASTATIME 2026-09-16 - the storage root as a setting (stage 2): resolver,
target validation, the move job (real robocopy on a temp tree) and the
endpoints behind Settings -> Local Machine -> Media Library Location.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest
from django.urls import reverse

from libretime_api.core.models import Preference
from libretime_api.storage import move as sm
from libretime_api.storage import root as sr

WINDOWS = sys.platform == "win32"


@pytest.fixture(autouse=True)
def _fresh_caches():
    sr.invalidate()
    yield
    sr.invalidate()


@pytest.fixture
def library(tmp_path):
    src = tmp_path / "media"
    for rel in ("imported/Artist/Album/a.mp3", "imported/artwork/a", "imported/podcast_ep1.mp3"):
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 1000)
    return src


def _point_root_at(library, monkeypatch):
    monkeypatch.setattr(sr, "config_root", lambda: sr.normalize(str(library)))
    sr.invalidate()
    sm.save_state({"state": "idle"})
    sr.set_storage_root_setting(None)
    return sr.normalize(str(library))


@pytest.fixture
def as_root(db, library, monkeypatch):
    return _point_root_at(library, monkeypatch)


@pytest.fixture
def as_root_tx(transactional_db, library, monkeypatch):
    """The move job writes from its own thread - needs a real transaction boundary."""
    return _point_root_at(library, monkeypatch)


# ---- resolver ----------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("D:\\stor\\", "D:/stor"), ("D:/stor/", "D:/stor"), (" D:/stor ", "D:/stor"),
    ("D:", "D:/"), ("D:/", "D:/"), ("", ""),
])
def test_normalize(value, expected):
    assert sr.normalize(value) == expected


def test_root_falls_back_to_the_configuration(as_root):
    assert sr.get_storage_root() == as_root
    assert sr.root_info()["source"] == "config"


def test_setting_wins_and_set_invalidates_the_cache(as_root, tmp_path):
    new = tmp_path / "elsewhere"
    new.mkdir()
    sr.set_storage_root_setting(str(new) + "\\")
    assert sr.get_storage_root() == sr.normalize(str(new))
    info = sr.root_info()
    assert info["source"] == "setting" and info["exists"] and info["writable"]
    assert Preference.site.get(key=sr.STORAGE_ROOT_KEY).value == sr.normalize(str(new))
    sr.set_storage_root_setting(None)
    assert sr.get_storage_root() == as_root


def test_missing_setting_root_is_reported_not_hidden(as_root, tmp_path):
    sr.set_storage_root_setting(str(tmp_path / "gone"))
    info = sr.root_info()
    assert info["source"] == "setting" and info["exists"] is False
    assert sr.get_storage_root() == sr.normalize(str(tmp_path / "gone"))


def test_library_size_counts_files_and_bytes(as_root):
    assert sr.library_size(as_root, refresh=True) == (3, 3000)


# ---- validation ----------------------------------------------------------------

def test_validate_rejects_bad_targets(as_root, tmp_path):
    def errors(path, size=0):
        return sm.validate_target(path, as_root, size)["errors"]

    assert errors("")[0].startswith("Enter a folder path")
    assert "Network paths" in errors("//nas/share")[0]
    assert "absolute path" in errors("stor")[0]
    assert "does not exist" in errors("Q:/stor")[0] or "Drive" in errors("Q:/stor")[0]
    assert "current location" in errors(as_root)[0]
    assert "inside the current" in errors(as_root + "/sub")[0]
    assert "lies inside the new" in errors(str(tmp_path))[0]
    assert "free space" in errors(str(tmp_path / "ok"), 10 ** 15)[0]


def test_validate_accepts_and_creates_a_good_target(as_root, tmp_path):
    result = sm.validate_target(str(tmp_path / "new" / "stor"), as_root, 3000)
    assert result["ok"] and result["errors"] == []
    assert os.path.isdir(tmp_path / "new" / "stor")
    assert result["free_bytes"] > result["needed_bytes"] > 3000


# ---- job ---------------------------------------------------------------------

def _wait(job, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        state = job.status()
        if state["state"] not in sm.ACTIVE_STATES:
            return state
        time.sleep(0.2)
    raise AssertionError("move did not finish: %r" % job.status())


@pytest.mark.skipif(not WINDOWS, reason="robocopy")
def test_move_copies_verifies_and_switches(as_root_tx, tmp_path):
    as_root = as_root_tx
    from libretime_api.storage.models import File
    from libretime_api.storage.tests.test_storage_flatten import _file

    _file("imported/Artist/Album/a.mp3")
    job = sm.MoveJob()
    target = tmp_path / "new"
    state = job.start(str(target))
    assert state["state"] == "copying" and state["total_files"] == 3
    assert job.is_locked()
    final = _wait(job)
    assert final["state"] == "switched", final
    assert final["old_copy"] == as_root and final["done_files"] == 3
    assert (target / "imported" / "Artist" / "Album" / "a.mp3").read_bytes() == b"x" * 1000
    assert sr.get_storage_root() == sr.normalize(str(target))
    assert (as_root and os.path.isfile(os.path.join(as_root, "imported", "podcast_ep1.mp3")))   # old copy kept
    assert not job.is_locked()
    assert File.objects.count() == 1


@pytest.mark.skipif(not WINDOWS, reason="robocopy")
def test_move_fails_when_a_library_row_is_missing_at_the_target(as_root_tx, tmp_path):
    as_root = as_root_tx
    from libretime_api.storage.tests.test_storage_flatten import _file

    _file("imported/not-on-disk.mp3")
    job = sm.MoveJob()
    job.start(str(tmp_path / "new"))
    final = _wait(job)
    assert final["state"] == "failed" and "missing at the target" in final["error"]
    assert sr.get_storage_root() == as_root                      # not switched


def test_double_start_and_bad_target_raise(as_root, tmp_path, monkeypatch):
    job = sm.MoveJob()
    with pytest.raises(sm.InvalidTarget) as exc:
        job.start("//nas/x")
    assert exc.value.errors
    sm.save_state({"state": "copying", "pid": os.getpid(), "heartbeat": sm._now()})
    monkeypatch.setattr(job, "_alive", lambda state: True)
    with pytest.raises(sm.MoveInProgress):
        job.start(str(tmp_path / "new"))


def test_dead_process_marks_the_move_interrupted(as_root):
    stale = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(timespec="seconds")
    sm.save_state({"state": "copying", "pid": 1, "heartbeat": stale, "source": "a", "target": "b"})
    job = sm.MoveJob()
    state = job.status()
    assert state["state"] == "interrupted" and "resume" in state["error"]
    assert json.loads(Preference.site.get(key=sr.MOVE_STATE_KEY).value)["state"] == "interrupted"
    assert not job.is_locked()


def test_fresh_heartbeat_of_another_process_still_counts_as_running(as_root):
    sm.save_state({"state": "verifying", "pid": 1, "heartbeat": sm._now(), "source": "a", "target": "b"})
    assert sm.MoveJob().is_locked()


# ---- endpoints ---------------------------------------------------------------

def test_location_endpoint(api_client, as_root):
    resp = api_client.get(reverse("storage-location"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["root"] == as_root and data["source"] == "config"
    assert data["library_files"] == 3 and data["library_bytes"] == 3000
    assert data["move"]["state"] == "idle"


def test_validate_and_start_endpoints_reject_bad_paths(api_client, as_root):
    resp = api_client.post(reverse("storage-move-validate"), {"path": "//nas/x"}, format="json")
    assert resp.status_code == 200 and resp.json()["ok"] is False
    resp = api_client.post(reverse("storage-move-start"), {"path": "//nas/x"}, format="json")
    assert resp.status_code == 400 and resp.json()["errors"]
    assert api_client.get(reverse("storage-move-status")).json()["move"]["state"] == "idle"


def test_start_endpoint_refuses_while_a_move_runs(api_client, as_root, tmp_path, monkeypatch):
    sm.save_state({"state": "copying", "pid": 1, "heartbeat": sm._now(), "source": "a", "target": "b"})
    resp = api_client.post(reverse("storage-move-start"), {"path": str(tmp_path / "n")}, format="json")
    assert resp.status_code == 409


def test_endpoints_need_credentials(as_root):
    from rest_framework.test import APIClient

    assert APIClient().get(reverse("storage-location")).status_code in (401, 403)
