"""
RASTATIME 2026-09-16 - manual backup via the UI (work-order point 10,
stage 1): folder validation, the backup job (stubbed pg_dump writing to
stdout), the endpoints behind Settings -> Backup.
"""
from __future__ import annotations

import json
import os
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from django.urls import reverse

from rastatime_api.core.models import Preference
from rastatime_api.storage import backup as sb
from rastatime_api.storage import root as sr

WINDOWS = sys.platform == "win32"


@pytest.fixture(autouse=True)
def _fresh_caches(db):
    # cc_pref is unmanaged - the transactional-test flush skips it, so the
    # committed folder/state of a job test would leak into the next test.
    def wipe():
        sr.invalidate()
        Preference.site.filter(key__in=[sb.BACKUP_FOLDER_KEY, sb.BACKUP_STATE_KEY, sb.INCLUDE_MEDIA_KEY, sb.AUTO_KEY]).delete()

    wipe()
    yield
    wipe()


@pytest.fixture
def target(tmp_path):
    d = tmp_path / "backups"
    return str(d).replace("\\", "/")


@pytest.fixture
def fake_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "rastatime.conf").write_text("general:\n  api_key: secret\n", encoding="utf-8")
    (cfg / "icecast.xml").write_text("<icecast/>", encoding="utf-8")
    monkeypatch.setattr(sb, "config_dir", lambda: str(cfg))
    return cfg


@pytest.fixture
def fake_pg_dump(monkeypatch):
    """pg_dump stand-in: a Python one-liner that writes bytes to stdout."""
    argv = [
        sys.executable, "-c",
        "import sys; sys.stdout.buffer.write(b'PGDMP-fake' * 1000)",
    ]
    monkeypatch.setattr(sb, "_pg_dump_command", lambda: (argv, os.environ.copy()))
    monkeypatch.setattr(sb, "_pg_dump_version", lambda _b: "pg_dump (fake) 17.0")
    return argv


def wait_state(*done_states, timeout=15.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        state = sb.JOB.status()
        if state.get("state") in done_states:
            return state
        time.sleep(0.05)
    raise AssertionError(f"job did not reach {done_states}: {sb.JOB.status()}")


# ---- validation -------------------------------------------------------------


@pytest.mark.django_db
def test_validate_rejects_relative_network_and_empty_paths():
    assert not sb.validate_folder("")["ok"]
    assert not sb.validate_folder("backups")["ok"]
    assert not sb.validate_folder("//nas/backups")["ok"]


@pytest.mark.django_db
def test_validate_rejects_a_folder_inside_the_library(tmp_path, monkeypatch):
    root = str(tmp_path / "stor").replace("\\", "/")
    os.makedirs(root)
    monkeypatch.setattr(sr, "get_storage_root", lambda refresh=False: root)
    inside = sb.validate_folder(root + "/backups")
    assert not inside["ok"]
    assert "media library" in " ".join(inside["errors"])


@pytest.mark.django_db
@pytest.mark.skipif(not WINDOWS, reason="drive-letter validation")
def test_validate_accepts_and_creates_a_good_folder(target):
    check = sb.validate_folder(target)
    assert check["ok"], check["errors"]
    assert os.path.isdir(target)


# ---- job --------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_backup_job_writes_a_complete_zip(target, fake_config, fake_pg_dump):
    sb.set_backup_folder(target)
    sb.JOB.start()
    state = wait_state("done", "failed")
    assert state["state"] == "done", state.get("error")
    assert state["file"].startswith("rastatime-backup-") and state["bytes"] > 0
    path = os.path.join(target, state["file"])
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        assert names == {"db.dump", "config/rastatime.conf", "config/icecast.xml", "manifest.json"}
        assert zf.read("db.dump") == b"PGDMP-fake" * 1000
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["pg_dump"].startswith("pg_dump")
        assert "config/rastatime.conf" in manifest["contents"]
    listed = sb.list_backups(target)
    assert [e["name"] for e in listed] == [state["file"]]


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_failed_pg_dump_leaves_no_half_zip(target, fake_config, monkeypatch):
    argv = [sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(1)"]
    monkeypatch.setattr(sb, "_pg_dump_command", lambda: (argv, os.environ.copy()))
    sb.set_backup_folder(target)
    sb.JOB.start()
    state = wait_state("done", "failed")
    assert state["state"] == "failed"
    assert "boom" in state["error"]
    assert sb.list_backups(target) == []


@pytest.mark.django_db
def test_start_without_a_folder_is_refused():
    with pytest.raises(sb.InvalidFolder):
        sb.JOB.start()


@pytest.mark.django_db
def test_a_running_backup_blocks_a_second_start(target, monkeypatch):
    sb.set_backup_folder(target)
    os.makedirs(target, exist_ok=True)
    sb.save_state({"state": "running", "pid": os.getpid(), "heartbeat": sb._now()})
    monkeypatch.setattr(sb.JOB, "_alive", lambda _s: True)
    with pytest.raises(sb.BackupInProgress):
        sb.JOB.start()


@pytest.mark.django_db
def test_a_dead_job_shows_as_interrupted():
    stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec="seconds")
    sb.save_state({"state": "running", "pid": 99999999, "heartbeat": stale})
    assert sb.JOB.status()["state"] == "interrupted"


# ---- stage 2: media mirror (RASTATIME 2026-09-17) ---------------------------


@pytest.fixture
def library(tmp_path, monkeypatch):
    src = tmp_path / "stor"
    for rel in ("imported/Artist/a.mp3", "imported/artwork/a", "imported/b.mp3"):
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * (1024 + len(rel)))
    root = str(src).replace("\\", "/")
    monkeypatch.setattr(sr, "get_storage_root", lambda refresh=False: root)
    return src


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="real robocopy")
def test_media_mirror_is_copied_and_verified(target, fake_config, fake_pg_dump, library):
    sb.set_backup_folder(target)
    sb.set_include_media(True)
    sb.JOB.start()
    state = wait_state("done", "failed", timeout=60.0)
    assert state["state"] == "done", state.get("error")
    assert state["media_synced_at"]
    mirror = os.path.join(target, "media")
    copied = sorted(
        os.path.relpath(os.path.join(d, f), mirror).replace("\\", "/")
        for d, _dirs, files in os.walk(mirror) for f in files
    )
    assert copied == ["imported/Artist/a.mp3", "imported/artwork/a", "imported/b.mp3"]
    assert state["media_done_files"] == 3
    # the ZIP is still complete alongside the mirror
    assert sb.list_backups(target)[0]["name"] == state["file"]


# RASTATIME 2026-10-28 - "Backup Now" walked the library and the mirror
# inside the request (minutes on a USB disk) and the UI gave up after 20 s.
# The sizes are now measured by the job thread, so start() returns at once.
@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="real robocopy")
def test_start_with_media_returns_before_the_sizes_are_known(target, fake_config, fake_pg_dump, library, monkeypatch):
    slow = {"calls": 0}
    real_walk = sr.walk_size

    def slow_walk(root):
        slow["calls"] += 1
        time.sleep(0.6)
        return real_walk(root)

    monkeypatch.setattr(sr, "walk_size", slow_walk)
    sb.set_backup_folder(target)
    sb.set_include_media(True)
    t0 = time.monotonic()
    state = sb.JOB.start()
    assert time.monotonic() - t0 < 0.5
    assert state["state"] == "running"
    assert state["media_total_bytes"] is None  # not measured yet
    final = wait_state("done", "failed", timeout=60.0)
    assert final["state"] == "done", final.get("error")
    assert final["media_total_files"] == 3
    assert slow["calls"] >= 1


@pytest.mark.django_db(transaction=True)
def test_media_without_free_space_fails_the_job_with_a_message(target, fake_config, fake_pg_dump, library, monkeypatch):
    sb.set_backup_folder(target)
    sb.set_include_media(True)
    # a library far bigger than any disk: the folder itself passes the
    # start-time check, the mirror sizing in the job refuses
    monkeypatch.setattr(sr, "library_size", lambda root, refresh=False: (3, 10**18))
    sb.JOB.start()
    state = wait_state("done", "failed", timeout=60.0)
    assert state["state"] == "failed"
    assert "Not enough free space" in state["error"]
    # the database ZIP exists all the same
    assert sb.list_backups(target)[0]["name"] == state["file"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="real robocopy")
def test_second_run_mirrors_deletions(target, fake_config, fake_pg_dump, library):
    sb.set_backup_folder(target)
    sb.set_include_media(True)
    sb.JOB.start()
    assert wait_state("done", "failed", timeout=60.0)["state"] == "done"
    (library / "imported" / "b.mp3").unlink()
    (library / "imported" / "c.mp3").write_bytes(b"y" * 2048)
    sb.JOB.start()
    state = wait_state("done", "failed", timeout=60.0)
    assert state["state"] == "done", state.get("error")
    mirror = os.path.join(target, "media", "imported")
    assert not os.path.exists(os.path.join(mirror, "b.mp3"))       # /MIR purged it
    assert os.path.isfile(os.path.join(mirror, "c.mp3"))


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_media_flag_off_leaves_the_library_alone(target, fake_config, fake_pg_dump, library):
    sb.set_backup_folder(target)
    sb.set_include_media(False)
    sb.JOB.start()
    state = wait_state("done", "failed", timeout=60.0)
    assert state["state"] == "done", state.get("error")
    assert not os.path.exists(os.path.join(target, "media"))
    assert "media_synced_at" not in state


@pytest.mark.django_db
def test_cancel_outside_the_media_phase_is_a_no_op(target):
    sb.save_state({"state": "done", "file": "x"})
    assert sb.JOB.cancel()["state"] == "done"


# ---- name safety ------------------------------------------------------------


@pytest.mark.django_db
def test_download_names_are_traversal_safe(target):
    sb.set_backup_folder(target)
    os.makedirs(target, exist_ok=True)
    good = "rastatime-backup-2026-09-16T1800.zip"
    open(os.path.join(target, good), "wb").write(b"zip")
    assert sb.backup_file_path(good) == os.path.join(target, good)
    assert sb.backup_file_path("../../secret.zip") is None
    assert sb.backup_file_path("rastatime-backup-..\\..\\x.zip") is None
    assert sb.backup_file_path("other.zip") is None
    assert sb.backup_file_path("") is None


# ---- endpoints --------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_endpoints_roundtrip(api_client, target, fake_config, fake_pg_dump):
    url = reverse("storage-backup")
    data = api_client.get(url).json()
    assert data["configured"] is False and data["backups"] == []

    check = api_client.post(reverse("storage-backup-validate"), {"path": "relative"}, format="json")
    assert check.json()["ok"] is False

    saved = api_client.post(reverse("storage-backup-folder"), {"path": target}, format="json")
    assert saved.status_code == 200 and saved.json()["configured"] is True
    # include_media travels through the folder endpoint (2026-09-17: the PHP
    # proxy dropped it and no test caught that - the API side is covered now)
    on = api_client.post(reverse("storage-backup-folder"),
                         {"path": target, "include_media": True}, format="json")
    assert on.json()["include_media"] is True
    off = api_client.post(reverse("storage-backup-folder"),
                          {"path": target, "include_media": "false"}, format="json")
    assert off.json()["include_media"] is False

    bad = api_client.post(reverse("storage-backup-folder"), {"path": "nope"}, format="json")
    assert bad.status_code == 400

    run = api_client.post(reverse("storage-backup-run"))
    assert run.status_code == 202
    state = wait_state("done", "failed")
    assert state["state"] == "done", state.get("error")

    data = api_client.get(url).json()
    assert data["job"]["state"] == "done"
    assert len(data["backups"]) == 1

    name = data["backups"][0]["name"]
    dl = api_client.get(reverse("storage-backup-download"), {"name": name})
    assert dl.status_code == 200
    assert dl.headers["Content-Type"] == "application/zip"
    assert name in dl.headers.get("Content-Disposition", "")
    dl.close()

    missing = api_client.get(reverse("storage-backup-download"), {"name": "rastatime-backup-2000-01-01T0000.zip"})
    assert missing.status_code == 404


# ---- stage 3: automatic backups (RASTATIME 2026-09-17) ----------------------


@pytest.mark.django_db
def test_auto_config_roundtrip_and_defaults():
    cfg = sb.get_auto_config()
    assert cfg == {"enabled": False, "every_days": 1, "retention_days": 30}
    sb.set_auto_config({"enabled": True, "every_days": 0, "retention_days": -5})
    cfg = sb.get_auto_config()
    assert cfg["enabled"] is True
    assert cfg["every_days"] == 1          # clamped
    assert cfg["retention_days"] == 0      # clamped


@pytest.mark.django_db
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_auto_due_logic(target):
    sb.set_backup_folder(target)
    os.makedirs(target, exist_ok=True)
    sb.set_auto_config({"enabled": False, "every_days": 1, "retention_days": 0})
    assert sb.auto_backup_due()[0] is False            # disabled
    sb.set_auto_config({"enabled": True, "every_days": 1, "retention_days": 0})
    assert sb.auto_backup_due() == (True, "no backup yet")
    fresh = os.path.join(target, "rastatime-backup-2026-09-17T1200.zip")
    open(fresh, "wb").write(b"zip")
    assert sb.auto_backup_due()[0] is False            # just created
    two_days_ago = time.time() - 2 * 86400
    os.utime(fresh, (two_days_ago, two_days_ago))
    assert sb.auto_backup_due()[0] is True


@pytest.mark.django_db
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_retention_prunes_old_zips_but_keeps_the_newest(target):
    sb.set_backup_folder(target)
    os.makedirs(target, exist_ok=True)
    old_days = time.time() - 40 * 86400
    for name in ("rastatime-backup-2026-08-01T0300.zip",
                 "rastatime-backup-2026-08-02T0300.zip"):
        path = os.path.join(target, name)
        open(path, "wb").write(b"zip")
        os.utime(path, (old_days, old_days))
    newest = os.path.join(target, "rastatime-backup-2026-09-17T0300.zip")
    open(newest, "wb").write(b"zip")
    deleted = sb.prune_old_backups(target, 30)
    assert sorted(deleted) == ["rastatime-backup-2026-08-01T0300.zip",
                               "rastatime-backup-2026-08-02T0300.zip"]
    assert [e["name"] for e in sb.list_backups(target)] == ["rastatime-backup-2026-09-17T0300.zip"]
    # retention 0 = keep everything; the newest always survives even when old
    os.utime(newest, (old_days, old_days))
    assert sb.prune_old_backups(target, 0) == []
    assert sb.prune_old_backups(target, 30) == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_backup_auto_command_runs_when_due_and_prunes(target, fake_config, fake_pg_dump):
    from io import StringIO

    from django.core.management import call_command

    sb.set_backup_folder(target)
    os.makedirs(target, exist_ok=True)
    sb.set_auto_config({"enabled": True, "every_days": 1, "retention_days": 30})
    stale = os.path.join(target, "rastatime-backup-2026-08-01T0300.zip")
    open(stale, "wb").write(b"zip")
    old_days = time.time() - 40 * 86400
    os.utime(stale, (old_days, old_days))

    out = StringIO()
    call_command("backup_auto", stdout=out)
    text = out.getvalue()
    assert "backup done" in text
    assert "retention: deleted rastatime-backup-2026-08-01T0300.zip" in text
    names = [e["name"] for e in sb.list_backups(target)]
    assert len(names) == 1 and names[0] != "rastatime-backup-2026-08-01T0300.zip"

    out = StringIO()
    call_command("backup_auto", stdout=out)
    assert "nothing to do" in out.getvalue()           # fresh backup exists


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_backup_auto_command_reports_failure(target, fake_config, monkeypatch):
    from django.core.management import call_command

    argv = [sys.executable, "-c", "import sys; sys.stderr.write('kaput'); sys.exit(1)"]
    monkeypatch.setattr(sb, "_pg_dump_command", lambda: (argv, os.environ.copy()))
    sb.set_backup_folder(target)
    sb.set_auto_config({"enabled": True, "every_days": 1, "retention_days": 0})
    with pytest.raises(SystemExit):
        call_command("backup_auto")


@pytest.mark.django_db
@pytest.mark.skipif(not WINDOWS, reason="windows paths")
def test_auto_endpoint_saves_and_reports(api_client, target):
    saved = api_client.post(reverse("storage-backup-auto"),
                            {"enabled": True, "every_days": 7, "retention_days": 60},
                            format="json")
    assert saved.status_code == 200
    assert saved.json()["auto"] == {"enabled": True, "every_days": 7, "retention_days": 60}
    bad = api_client.post(reverse("storage-backup-auto"),
                          {"enabled": True, "every_days": "week"}, format="json")
    assert bad.status_code == 400
