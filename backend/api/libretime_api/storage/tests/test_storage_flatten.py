"""
RASTATIME 2026-09-16 - ``storage_flatten``: drop the imported/<owner-id>/
level and make every stored path root-relative (stage 1 of the storage
location work).  Dry run touches nothing; --apply moves entries and rewrites
rows together and undoes both on failure.
"""
from __future__ import annotations

import os
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from libretime_api.core.models import Preference
from libretime_api.schedule.models import Show
from libretime_api.storage.management.commands import storage_flatten as sf
from libretime_api.storage.models import File


def _file(filepath, artwork=None):
    now = timezone.now()
    zero = timedelta(0)
    return File.objects.create(
        filepath=filepath, artwork=artwork, size=1, exists=True, mime="audio/mp3",
        import_status=File.ImportStatus.SUCCESS, hidden=False, accessed=0, scheduled=False,
        part_of_list=False, disabled=False, created_at=now, updated_at=now,
        name="x", track_title="x", cue_in=zero, cue_out=zero,
    )


def _show_image(pk):
    with connection.cursor() as cur:
        cur.execute("SELECT image_path FROM cc_show WHERE id = %s", [pk])
        return cur.fetchone()[0]


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "media"
    owner = root / "imported" / "2"
    for rel in ("Artist/Album/a.mp3", "artwork/a", "show-images/5/p.png", "auto-dj-logos/l.png", "podcast_ep1.mp3"):
        p = owner / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    (root / "organize").mkdir()
    return root


@pytest.fixture
def rows(db, library):
    root = str(library)
    f1 = _file("imported/2/Artist/Album/a.mp3", artwork="imported/2/artwork/a")
    f2 = _file("/imported/2/podcast_ep1.mp3")
    f3 = _file(None)
    show = Show.objects.create(name="s", linked=False, linkable=True, auto_playlist_enabled=False,
                               auto_playlist_repeat=False, override_intro_playlist=False,
                               override_outro_playlist=False,
                               image=root.replace("/", "\\") + "\\imported\\2\\show-images\\5\\p.png")
    Preference.objects.create(key=sf.AUTO_DJ_LOGO_KEY, value=root + "/imported/2/auto-dj-logos/l.png")
    return f1, f2, f3, show


def _run(root, apply=False):
    out = StringIO()
    args = ["--root", str(root)] + (["--apply"] if apply else [])
    call_command("storage_flatten", *args, stdout=out)
    return out.getvalue()


# ---- relative_path -----------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("imported/2/Artist/a.mp3", "imported/Artist/a.mp3"),
    ("/imported/2/podcast.mp3", "imported/podcast.mp3"),
    ("imported/2/artwork/x", "imported/artwork/x"),
    ("imported/Artist/a.mp3", "imported/Artist/a.mp3"),                      # already flat
    ("C:/media/imported/2/show-images/5\\p.png", "imported/show-images/5/p.png"),
    ("c:\\MEDIA\\imported\\2\\auto-dj-logos\\l.png", "imported/auto-dj-logos/l.png"),  # case, backslashes
    ("D:/elsewhere/x.png", "D:/elsewhere/x.png"),                              # outside the root
    ("imported/2026/Song.mp3", "imported/2026/Song.mp3"),                       # numeric artist stays
    ("imported/7/Song.mp3", "imported/7/Song.mp3"),                             # not a known owner id
    (None, None), ("", ""),
])
def test_relative_path(value, expected):
    assert sf.relative_path(value, "C:/media", owner_ids=["2"]) == expected


# ---- dry run -----------------------------------------------------------------

def test_dry_run_reports_and_changes_nothing(rows, library):
    f1, f2, f3, show = rows
    text = _run(library)
    assert "DRY RUN" in text
    assert "entries to move: 5   conflicts: 0" in text
    assert "cc_files.filepath 2, cc_files.artwork 1, cc_show.image_path 1, cc_pref.auto_dj_logo_path 1" in text
    assert "rows with a path: 2, resolvable now: 2, resolvable after: 2" in text
    assert (library / "imported" / "2" / "Artist" / "Album" / "a.mp3").is_file()
    f1.refresh_from_db()
    assert f1.filepath == "imported/2/Artist/Album/a.mp3"
    assert _show_image(show.pk).endswith("\\p.png")


# ---- apply -------------------------------------------------------------------

def test_apply_moves_entries_and_rewrites_rows(rows, library):
    f1, f2, f3, show = rows
    text = _run(library, apply=True)
    assert "APPLIED - verify: 2 of 2 cc_files paths resolve on disk" in text
    for rel in ("Artist/Album/a.mp3", "artwork/a", "show-images/5/p.png", "auto-dj-logos/l.png", "podcast_ep1.mp3"):
        assert (library / "imported" / rel).is_file(), rel
    assert not (library / "imported" / "2").exists()
    f1.refresh_from_db(); f2.refresh_from_db(); f3.refresh_from_db()
    assert f1.filepath == "imported/Artist/Album/a.mp3" and f1.artwork == "imported/artwork/a"
    assert f2.filepath == "imported/podcast_ep1.mp3"
    assert f3.filepath is None
    assert _show_image(show.pk) == "imported/show-images/5/p.png"
    assert Preference.objects.get(key=sf.AUTO_DJ_LOGO_KEY).value == "imported/auto-dj-logos/l.png"
    # idempotent: a second run finds nothing
    assert "nothing to do" in _run(library, apply=True)


def test_conflict_aborts_before_anything_moves(rows, library):
    f1 = rows[0]
    clash = library / "imported" / "Artist"
    clash.mkdir()
    with pytest.raises(CommandError, match="conflicts"):
        _run(library, apply=True)
    assert (library / "imported" / "2" / "Artist" / "Album" / "a.mp3").is_file()
    f1.refresh_from_db()
    assert f1.filepath == "imported/2/Artist/Album/a.mp3"


def test_failure_undoes_rows_and_moves(rows, library, monkeypatch):
    f1, f2, f3, show = rows
    real_rename = os.rename
    calls = []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 3:
            raise OSError("disk went away")
        real_rename(src, dst)

    monkeypatch.setattr(sf.os, "rename", flaky)
    with pytest.raises(OSError):
        _run(library, apply=True)
    # rows rolled back, entries back in place
    f1.refresh_from_db()
    assert f1.filepath == "imported/2/Artist/Album/a.mp3"
    assert _show_image(show.pk).endswith("\\p.png")
    for rel in ("Artist/Album/a.mp3", "artwork/a", "show-images/5/p.png", "auto-dj-logos/l.png", "podcast_ep1.mp3"):
        assert (library / "imported" / "2" / rel).is_file(), rel
    assert not any(p.name != "2" for p in (library / "imported").iterdir())


def test_rows_of_a_vanished_owner_dir_need_the_owner_id_option(db, tmp_path):
    root = tmp_path / "media"
    (root / "imported" / "Artist").mkdir(parents=True)
    (root / "imported" / "Artist" / "a.mp3").write_bytes(b"x")
    f = _file("imported/2/Artist/a.mp3")
    assert "cc_files.filepath 0," in _run(root)                       # id 2 unknown: untouched
    out = StringIO()
    call_command("storage_flatten", "--root", str(root), "--owner-id", "2", "--apply", stdout=out)
    f.refresh_from_db()
    assert f.filepath == "imported/Artist/a.mp3"
    assert "verify: 1 of 1" in out.getvalue()


def test_missing_root_is_an_error(db, tmp_path):
    with pytest.raises(CommandError, match="does not exist"):
        _run(tmp_path / "nope")
