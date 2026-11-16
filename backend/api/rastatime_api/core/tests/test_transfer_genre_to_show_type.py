"""RASTATIME 2026-11-16 - manage.py transfer_genre_to_show_type (ARCHITECTURE 23.120)."""

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from ...schedule.models import Show


def _show(name, genre):
    return Show.objects.create(
        name=name,
        genre=genre,
        linked=False,
        linkable=True,
        auto_playlist_enabled=False,
        auto_playlist_repeat=False,
        override_intro_playlist=False,
        override_outro_playlist=False,
    )


def _type_id(code):
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM cc_show_types WHERE code = %s", [code])
        return cur.fetchone()[0]


def _state(show):
    with connection.cursor() as cur:
        cur.execute("SELECT genre, show_type_id FROM cc_show WHERE id = %s", [show.id])
        return cur.fetchone()


def _run(*args):
    out = StringIO()
    call_command("transfer_genre_to_show_type", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_dry_run_reports_and_writes_nothing():
    live = _show("A", "Live")
    text = _run("--dry-run")
    assert "'Live' -> show type 'Live': 1 shows" in text
    assert "dry run: 1 shows would get a show type" in text
    assert _state(live) == ("Live", None)


@pytest.mark.django_db
def test_without_a_map_the_genre_matches_label_or_code():
    a = _show("A", "  live ")
    b = _show("B", "Repeat")
    c = _show("C", "partner")  # the code of "Partner show"
    d = _show("D", "Jazz")
    text = _run()
    assert _state(a) == ("  live ", _type_id("live"))
    assert _state(b) == ("Repeat", _type_id("repeat"))
    assert _state(c) == ("partner", _type_id("partner"))
    assert _state(d) == ("Jazz", None)
    assert "'Jazz': no show type (1 shows, genre stays)" in text


@pytest.mark.django_db
def test_map_clear_genre_backup_and_typed_shows(tmp_path):
    musik = _show("M1", "Musik")
    music = _show("M2", "Music")
    news = _show("N", "News")
    jazz = _show("J", "Jazz")
    typed = _show("T", "Musik")
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE cc_show SET show_type_id = %s WHERE id = %s", [_type_id("live"), typed.id]
        )
    backup = tmp_path / "backup.json"
    text = _run(
        "--map",
        "Musik=music",
        "--map",
        "Music=Music",
        "--map",
        "News=news",
        "--clear-genre",
        "--backup",
        str(backup),
    )
    assert _state(musik) == ("", _type_id("music"))
    assert _state(music) == ("", _type_id("music"))
    assert _state(news) == ("", _type_id("news"))
    assert _state(jazz) == ("Jazz", None)  # not in the map: untouched
    assert _state(typed) == ("Musik", _type_id("live"))  # already typed: left alone
    assert "1 shows already have a show type" in text
    saved = json.loads(backup.read_text(encoding="utf-8"))
    assert {r["name"] for r in saved} == {"M1", "M2", "N"}
    assert {r["genre"] for r in saved} == {"Musik", "Music", "News"}
    # --overwrite takes the typed show too
    _run("--map", "Musik=music", "--overwrite")
    assert _state(typed) == ("Musik", _type_id("music"))


@pytest.mark.django_db
def test_bad_map_entries_stop_before_anything_changes():
    show = _show("A", "Live")
    with pytest.raises(CommandError):
        _run("--map", "Live")
    with pytest.raises(CommandError):
        _run("--map", "Live=nonexistent")
    assert _state(show) == ("Live", None)
