"""
RASTATIME 2026-10-24 - delete the Data-URI text copies of the covers.

Up to 2026-10-24 the legacy wrote ten files per cover into
``imported/artwork/``: the original picture as a Data-URI text file
(``<name>``, no extension), five JPG sizes (``<name>-32.jpg`` ...
``<name>-512.jpg``) and four Data-URI text copies of those
(``<name>-32`` ... ``<name>-256``).  Since then only the JPGs are written
and the Data URIs are built from them on demand
(FileDataHelper::getArtworkData).  This removes the text files that have a
``<name>-512.jpg`` next to them; a cover without its JPG set is left alone.

    manage.py artwork_prune_datauri          dry run: counts and bytes
    manage.py artwork_prune_datauri --yes    deletes
"""

import os
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from ...root import get_storage_root

SIZED_TEXT_RE = re.compile(r"^(?P<base>.+)-(32|64|128|256)$")
JPG_RE = re.compile(r"^(?P<base>.+)-(32|64|128|256|512)\.jpg$", re.IGNORECASE)


def classify(folder: Path):
    """Return (text files to delete, kept) over the artwork folder."""
    names = os.listdir(folder)
    name_set = set(names)
    delete = []
    kept = 0
    for name in names:
        if JPG_RE.match(name):
            kept += 1
            continue
        m = SIZED_TEXT_RE.match(name)
        base = m.group("base") if m else name
        if f"{base}-512.jpg" in name_set and (folder / name).is_file():
            delete.append(folder / name)
        else:
            kept += 1
    return delete, kept


class Command(BaseCommand):
    help = "Delete the Data-URI text copies of covers that have their JPG set (dry run without --yes)."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--yes", action="store_true", help="Delete (default: dry run).")
        parser.add_argument("--root", help="Storage root (default: the effective library root).")

    def handle(self, *args, **options):
        out = self.stdout.write
        root = Path(options["root"] or get_storage_root())
        folder = root / "imported" / "artwork"
        if not folder.is_dir():
            out(f"no artwork folder at {folder}")
            return
        delete, kept = classify(folder)
        total_bytes = sum(p.stat().st_size for p in delete)
        out(f"{folder}: {len(delete)} Data-URI text file(s) with a JPG set ({total_bytes / 1e6:.0f} MB), {kept} file(s) kept")
        if not options["yes"]:
            out("dry run - add --yes to delete")
            return
        removed = failed = 0
        for path in delete:
            try:
                path.unlink()
                removed += 1
            except OSError as exc:
                failed += 1
                out(f"  FAILED {path.name}: {exc}")
        out(f"deleted {removed}, failed {failed}")
