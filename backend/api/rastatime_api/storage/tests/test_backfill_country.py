"""
RASTATIME 2026-11-08 - ``manage.py backfill_country``: empty country columns
are filled from the COUNTRY tag, set values stay, a dry run writes nothing.
"""

from __future__ import annotations

import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from model_bakery import baker
from mutagen.id3 import ID3, TIT2, TXXX

from rastatime_api._fixtures import AUDIO_FILENAME
from rastatime_api.storage import root as sr
from rastatime_api.storage.models import File

FIXTURE = Path(__file__).resolve().parents[2] / "_fixtures" / AUDIO_FILENAME


@pytest.fixture
def root(tmp_path, monkeypatch, db):
    media = tmp_path / "media"
    (media / "imported").mkdir(parents=True)
    monkeypatch.setattr(sr, "config_root", lambda: sr.normalize(str(media)))
    sr.invalidate()
    sr.set_storage_root_setting(None)
    yield media
    sr.invalidate()


def _track(root: Path, name: str, country_tag: str | None, **row) -> File:
    path = root / "imported" / name
    shutil.copy(FIXTURE, path)
    id3 = ID3()
    id3.add(TIT2(encoding=3, text=name))
    if country_tag is not None:
        id3.add(TXXX(encoding=3, desc="COUNTRY", text=country_tag))
    id3.save(path)
    return baker.make(
        "storage.File",
        filepath=f"imported/{name}",
        exists=True,
        mime="audio/mp3",
        import_status=0,
        **row,
    )


def _run(*args: str) -> str:
    out = StringIO()
    call_command("backfill_country", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_backfill_fills_only_empty_countries(root):
    empty = _track(root, "a.mp3", "Austria", country=None)
    blank = _track(root, "b.mp3", "USA", country="")
    kept = _track(root, "c.mp3", "Germany", country="France")
    untagged = _track(root, "d.mp3", None, country=None)
    gone = baker.make(
        "storage.File", filepath="imported/gone.mp3", exists=True, mime="audio/mp3", import_status=0
    )

    dry = _run()
    assert "checked 4 tracks without country, 2 with a COUNTRY tag, 1 files missing" in dry
    assert "dry run" in dry
    assert File.objects.get(pk=empty.pk).country is None

    out = _run("--yes")
    assert "wrote the country of 2 tracks" in out
    countries = dict(File.objects.values_list("pk", "country"))
    assert countries[empty.pk] == "Austria"
    assert countries[blank.pk] == "USA"
    assert countries[kept.pk] == "France"  # set values are never replaced
    assert countries[untagged.pk] is None
    assert countries[gone.pk] is None


@pytest.mark.django_db
def test_backfill_ids(root):
    first = _track(root, "a.mp3", "Austria", country=None)
    second = _track(root, "b.mp3", "UK", country=None)

    _run("--yes", "--ids", str(second.pk))

    assert File.objects.get(pk=first.pk).country is None
    assert File.objects.get(pk=second.pk).country == "UK"
