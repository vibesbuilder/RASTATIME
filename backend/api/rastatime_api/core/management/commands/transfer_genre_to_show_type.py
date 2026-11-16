"""
RASTATIME 2026-11-16 - move show types out of the genre field (ARCHITECTURE
23.120).

Until show types existed (migration 0088), stations wrote "Live", "Repeat"
and the like into a show's genre.  This command gives each such show the
matching show type and, with ``--clear-genre``, empties the genre so it is
free for a real genre.

    manage.py transfer_genre_to_show_type --dry-run
    manage.py transfer_genre_to_show_type --map Musik=music --map Music=music \\
        --clear-genre --backup C:/Temp/show_genre_backup.json

``--map GENRE=TYPE``: a genre value (case and blanks ignored) and the label
or code of a show type.  Without any ``--map`` a genre matches a show type of
the same label or code.  Shows that already have a type are left alone
unless ``--overwrite``.  ``--backup`` writes id, name, genre and type of
every changed show as JSON before anything is written; one transaction.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


def _norm(value: str | None) -> str:
    return " ".join((value or "").split()).lower()


class Command(BaseCommand):
    help = "Give shows the show type named in their genre field (and empty the genre)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--map",
            action="append",
            default=[],
            metavar="GENRE=TYPE",
            help="genre value = show type label or code (repeatable)",
        )
        parser.add_argument(
            "--clear-genre", action="store_true", help="empty the genre of the moved shows"
        )
        parser.add_argument(
            "--overwrite", action="store_true", help="also shows that have a show type already"
        )
        parser.add_argument("--dry-run", action="store_true", help="only report what would change")
        parser.add_argument("--backup", metavar="PATH", help="JSON backup of the changed shows")

    def handle(self, *args, **options):
        out = self.stdout.write
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'cc_show_types'"
            )
            if cur.fetchone() is None:
                raise CommandError("cc_show_types is missing - run migration 0088 first")
            cur.execute("SELECT id, code, type_name FROM cc_show_types ORDER BY sort_order, id")
            types = cur.fetchall()
        by_key: dict[str, tuple[int, str]] = {}
        for tid, code, name in types:
            by_key.setdefault(_norm(name), (tid, name))
            by_key.setdefault(_norm(code), (tid, name))

        mapping: dict[str, tuple[int, str]] = {}
        for item in options["map"]:
            genre, sep, target = item.partition("=")
            if not sep or not _norm(genre) or not _norm(target):
                raise CommandError(f"--map needs GENRE=TYPE, got {item!r}")
            if _norm(target) not in by_key:
                raise CommandError(
                    f"--map {item!r}: no show type with the label or code {target!r}"
                )
            mapping[_norm(genre)] = by_key[_norm(target)]
        if not options["map"]:
            mapping = dict(by_key)

        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, name, genre, show_type_id FROM cc_show "
                "WHERE NULLIF(btrim(COALESCE(genre, '')), '') IS NOT NULL ORDER BY id"
            )
            shows = cur.fetchall()

        changes = []
        skipped_typed = 0
        unmapped: dict[str, int] = {}
        for sid, name, genre, type_id in shows:
            target = mapping.get(_norm(genre))
            if target is None:
                unmapped[genre.strip()] = unmapped.get(genre.strip(), 0) + 1
                continue
            if type_id is not None and not options["overwrite"]:
                skipped_typed += 1
                continue
            changes.append((sid, name, genre, type_id, target[0], target[1]))

        per_pair: dict[tuple[str, str], int] = {}
        for _sid, _name, genre, _old, _tid, tname in changes:
            key = (genre.strip(), tname)
            per_pair[key] = per_pair.get(key, 0) + 1
        for (genre, tname), n in sorted(per_pair.items(), key=lambda kv: (-kv[1], kv[0])):
            out(f"  {genre!r} -> show type {tname!r}: {n} shows")
        for genre, n in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0])):
            out(f"  {genre!r}: no show type ({n} shows, genre stays)")
        if skipped_typed:
            out(
                f"  {skipped_typed} shows already have a show type (left alone, --overwrite to change)"
            )

        verb = "would get" if options["dry_run"] else "got"
        clear = " and an empty genre" if options["clear_genre"] else ""
        if options["dry_run"]:
            out(f"dry run: {len(changes)} shows {verb} a show type{clear}")
            return

        if options["backup"] and changes:
            Path(options["backup"]).write_text(
                json.dumps(
                    [
                        {"id": sid, "name": name, "genre": genre, "show_type_id": old}
                        for sid, name, genre, old, _tid, _tn in changes
                    ],
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
            out(f"backup: {options['backup']} ({len(changes)} shows)")

        with transaction.atomic(), connection.cursor() as cur:
            for sid, _name, _genre, _old, tid, _tn in changes:
                if options["clear_genre"]:
                    cur.execute(
                        "UPDATE cc_show SET show_type_id = %s, genre = '' WHERE id = %s", [tid, sid]
                    )
                else:
                    cur.execute("UPDATE cc_show SET show_type_id = %s WHERE id = %s", [tid, sid])
        out(f"{len(changes)} shows {verb} a show type{clear}")
