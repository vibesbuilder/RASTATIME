"""
RASTATIME 2026-09-16 - flatten the owner-id level of the media library
(stage 1 of "storage location as a Local Machine setting").

Layout before::

    <root>/imported/<owner-id>/<artist>/<album>/track.mp3
    <root>/imported/<owner-id>/artwork/<name>
    <root>/imported/<owner-id>/show-images/<show-id>/<file>
    <root>/imported/<owner-id>/auto-dj-logos/<file>

Layout after: the same without the ``<owner-id>`` level.  Database values
become root-relative with forward slashes and no leading slash:
``cc_files.filepath``, ``cc_files.artwork``, ``cc_show.image_path`` and the
``auto_dj_logo_path`` preference (the last two used to hold absolute paths
under the root, which every root change would have broken).

Dry run by default: prints what would move and what would be rewritten and
touches nothing.  ``--apply`` moves the directory entries and rewrites the
rows in one transaction; a failure rolls the rows back and moves the entries
back.  Run it once, in a quiet moment, with the database dumped beforehand.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, transaction

from ...models import File

AUTO_DJ_LOGO_KEY = "auto_dj_logo_path"


def _norm(value: str) -> str:
    return value.replace("\\", "/")


def relative_path(value: Optional[str], root: str, owner_ids=()) -> Optional[str]:
    """
    Root-relative form of a database path: forward slashes, no leading
    slash, root prefix stripped (case-insensitive - Windows), and the
    ``imported/<owner-id>/`` level dropped for the given owner ids only - a
    purely numeric artist folder (``imported/2026/...``) is not an owner id.
    ``None``/empty and paths outside the root come back unchanged.
    """
    if value is None or value == "":
        return value
    norm = _norm(value)
    root_norm = _norm(root).rstrip("/") + "/"
    if norm.lower().startswith(root_norm.lower()):
        norm = norm[len(root_norm):]
    if re.match(r"^([A-Za-z]:/|//)", norm):
        return norm                                   # outside the root
    norm = norm.lstrip("/")
    for owner in owner_ids:
        prefix = f"imported/{owner}/"
        if norm.startswith(prefix):
            return "imported/" + norm[len(prefix):]
    return norm


@dataclass
class Plan:
    root: Path
    owner_dirs: List[Path] = field(default_factory=list)
    owner_ids: List[str] = field(default_factory=list)
    moves: List[Tuple[Path, Path]] = field(default_factory=list)
    conflicts: List[Tuple[Path, Path]] = field(default_factory=list)
    files: List[Tuple[int, str, str]] = field(default_factory=list)      # id, old, new filepath
    artworks: List[Tuple[int, str, str]] = field(default_factory=list)
    shows: List[Tuple[int, str, str]] = field(default_factory=list)
    prefs: List[Tuple[str, str]] = field(default_factory=list)           # old, new
    resolvable_before: int = 0
    resolvable_after: int = 0
    with_path: int = 0

    @property
    def row_changes(self) -> int:
        return len(self.files) + len(self.artworks) + len(self.shows) + len(self.prefs)


def build_plan(root: Path, extra_owner_ids=()) -> Plan:
    plan = Plan(root=root, owner_ids=list(extra_owner_ids))
    imported = root / "imported"
    if imported.is_dir():
        for entry in sorted(imported.iterdir()):
            if entry.is_dir() and entry.name.isdigit():
                plan.owner_dirs.append(entry)
                if entry.name not in plan.owner_ids:
                    plan.owner_ids.append(entry.name)
                for child in sorted(entry.iterdir()):
                    target = imported / child.name
                    (plan.conflicts if target.exists() else plan.moves).append((child, target))

    root_s = str(root)
    for pk, filepath, artwork in File.objects.order_by("id").values_list("id", "filepath", "artwork"):
        if filepath:
            plan.with_path += 1
            new = relative_path(filepath, root_s, plan.owner_ids)
            if (root / filepath.lstrip("/")).is_file():
                plan.resolvable_before += 1
            if (root / new).is_file() or any(
                str(root / new).lower().startswith(str(t).lower()) for _, t in plan.moves
            ):
                plan.resolvable_after += 1
            if new != filepath:
                plan.files.append((pk, filepath, new))
        if artwork:
            new = relative_path(artwork, root_s, plan.owner_ids)
            if new != artwork:
                plan.artworks.append((pk, artwork, new))

    with connection.cursor() as cur:
        cur.execute("SELECT id, image_path FROM cc_show WHERE image_path IS NOT NULL AND image_path <> '' ORDER BY id")
        for pk, image in cur.fetchall():
            new = relative_path(image, root_s, plan.owner_ids)
            if new != image:
                plan.shows.append((pk, image, new))
        cur.execute("SELECT valstr FROM cc_pref WHERE keystr = %s", [AUTO_DJ_LOGO_KEY])
        for (value,) in cur.fetchall():
            if value:
                new = relative_path(value, root_s, plan.owner_ids)
                if new != value:
                    plan.prefs.append((value, new))
    return plan


def apply_plan(plan: Plan, log) -> None:
    """Rows in one transaction, entries moved inside it; any failure undoes both."""
    moved: List[Tuple[Path, Path]] = []
    try:
        with transaction.atomic():
            for pk, _old, new in plan.files:
                File.objects.filter(pk=pk).update(filepath=new)
            for pk, _old, new in plan.artworks:
                File.objects.filter(pk=pk).update(artwork=new)
            with connection.cursor() as cur:
                for pk, _old, new in plan.shows:
                    cur.execute("UPDATE cc_show SET image_path = %s WHERE id = %s", [new, pk])
                for old, new in plan.prefs:
                    cur.execute("UPDATE cc_pref SET valstr = %s WHERE keystr = %s AND valstr = %s",
                                [new, AUTO_DJ_LOGO_KEY, old])
            for src, dst in plan.moves:
                os.rename(src, dst)
                moved.append((src, dst))
                log(f"moved  {src}  ->  {dst}")
    except Exception:
        for src, dst in reversed(moved):
            try:
                os.rename(dst, src)
                log(f"undone {dst}  ->  {src}")
            except OSError as exc:            # pragma: no cover - reported, not hidden
                log(f"UNDO FAILED {dst} -> {src}: {exc}")
        raise
    for owner in plan.owner_dirs:
        try:
            owner.rmdir()
            log(f"removed empty {owner}")
        except OSError:
            log(f"kept non-empty {owner}")


def verify(root: Path) -> Tuple[int, int, List[str]]:
    """(rows with a path, rows whose file exists, first missing paths)."""
    total = found = 0
    missing: List[str] = []
    for filepath in File.objects.exclude(filepath__isnull=True).exclude(filepath="").values_list("filepath", flat=True):
        total += 1
        if (root / filepath.lstrip("/")).is_file():
            found += 1
        elif len(missing) < 10:
            missing.append(filepath)
    return total, found, missing


class Command(BaseCommand):
    help = "Drop the imported/<owner-id>/ level of the media library and make every stored path root-relative."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--apply", action="store_true", help="Move entries and rewrite rows (default: dry run).")
        parser.add_argument("--root", help="Storage root (default: storage.path from the configuration).")
        parser.add_argument("--owner-id", action="append", default=[],
                            help="Owner id to strip from rows even when its directory is gone (repeatable).")

    def handle(self, *args, **options):
        from ...root import get_storage_root  # noqa: PLC0415
        root = Path(options.get("root") or get_storage_root(refresh=True))
        if not root.is_dir():
            raise CommandError(f"storage root does not exist: {root}")
        plan = build_plan(root, options.get("owner_id") or [])
        out = self.stdout.write
        out(f"storage root: {root}")
        out(f"owner-id directories: {[str(d) for d in plan.owner_dirs]}  owner ids: {plan.owner_ids}")
        out(f"entries to move: {len(plan.moves)}   conflicts: {len(plan.conflicts)}")
        for src, dst in plan.conflicts:
            out(f"  CONFLICT {src} -> {dst} exists")
        out(f"rows to rewrite: cc_files.filepath {len(plan.files)}, cc_files.artwork {len(plan.artworks)}, "
            f"cc_show.image_path {len(plan.shows)}, cc_pref.{AUTO_DJ_LOGO_KEY} {len(plan.prefs)}")
        for pk, old, new in (plan.files[:3] + plan.artworks[:2] + plan.shows[:2]):
            out(f"  {pk}: {old!r} -> {new!r}")
        for old, new in plan.prefs:
            out(f"  pref: {old!r} -> {new!r}")
        out(f"cc_files rows with a path: {plan.with_path}, resolvable now: {plan.resolvable_before}, "
            f"resolvable after: {plan.resolvable_after}")
        if plan.conflicts:
            raise CommandError("conflicts - nothing done")
        if not options.get("apply"):
            out("DRY RUN - nothing changed (use --apply)")
            return
        if not plan.moves and not plan.row_changes:
            out("nothing to do")
            return
        apply_plan(plan, out)
        total, found, missing = verify(root)
        out(f"APPLIED - verify: {found} of {total} cc_files paths resolve on disk")
        for m in missing:
            out(f"  missing: {m}")
