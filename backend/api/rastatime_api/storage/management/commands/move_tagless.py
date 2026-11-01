"""
RASTATIME 2026-10-24 - move the tracks that sit directly in ``imported/``
into ``imported/tagless/``.

The analyzer files a track under ``imported/<artist>/<album>/``; without an
artist tag the track used to land directly in ``imported/`` (63 files on
2026-10-24).  Since the same day the analyzer puts such tracks into
``imported/tagless/`` (organise_file.TAGLESS_DIR); this command moves the
existing ones and updates ``cc_files.filepath``.

    manage.py move_tagless            dry run: lists what would move
    manage.py move_tagless --yes      moves the files

A track with a schedule row from two hours ago to three hours ahead is
skipped (the playout may hold or queue it); run again later for those.
"""

import shutil
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from ....schedule.models import Schedule
from ...models import File
from ...root import get_storage_root

TAGLESS_DIR = "tagless"
SKIP_BEFORE = timedelta(hours=2)
SKIP_AFTER = timedelta(hours=3)


def candidates():
    """File rows whose path is ``imported/<name>`` with nothing in between."""
    rows = File.objects.filter(exists=True, filepath__startswith="imported/").exclude(
        filepath__startswith=f"imported/{TAGLESS_DIR}/"
    )
    return [f for f in rows if f.filepath.count("/") == 1]


def scheduled_soon(file_id: int) -> bool:
    now = timezone.now()
    return Schedule.objects.filter(
        file_id=file_id, starts_at__gte=now - SKIP_BEFORE, starts_at__lte=now + SKIP_AFTER
    ).exists()


class Command(BaseCommand):
    help = (
        "Move tracks that sit directly in imported/ into imported/tagless/ (dry run without --yes)."
    )

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--yes", action="store_true", help="Move (default: dry run).")
        parser.add_argument("--root", help="Storage root (default: the effective library root).")

    def handle(self, *args, **options):
        out = self.stdout.write
        root = Path(options["root"] or get_storage_root())
        target_dir = root / "imported" / TAGLESS_DIR
        rows = candidates()
        out(f"storage root {root}; {len(rows)} track(s) directly in imported/")
        moved = skipped = missing = 0
        for row in rows:
            src = root / row.filepath
            if not src.is_file():
                out(f"  MISSING  {row.id}  {row.filepath}")
                missing += 1
                continue
            if scheduled_soon(row.id):
                out(f"  SKIP     {row.id}  {row.filepath}  (scheduled around now)")
                skipped += 1
                continue
            dest = target_dir / src.name
            if dest.exists():
                dest = dest.with_name(f"{dest.stem}_{uuid4()}{dest.suffix}")
            new_rel = f"imported/{TAGLESS_DIR}/{dest.name}"
            if not options["yes"]:
                out(f"  WOULD    {row.id}  {row.filepath}  ->  {new_rel}")
                moved += 1
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            with transaction.atomic():
                shutil.move(str(src), str(dest))
                try:
                    File.objects.filter(pk=row.id).update(filepath=new_rel)
                except Exception:
                    shutil.move(str(dest), str(src))
                    raise
            out(f"  MOVED    {row.id}  {row.filepath}  ->  {new_rel}")
            moved += 1
        verb = "moved" if options["yes"] else "would move"
        out(f"{verb} {moved}, skipped {skipped}, missing {missing}")
        if not options["yes"] and moved:
            out("dry run - add --yes to move")
