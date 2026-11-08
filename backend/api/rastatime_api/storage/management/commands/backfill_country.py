"""
RASTATIME 2026-11-08 - fill cc_files.country (legacy migration 0081) once
from the COUNTRY tag of the files already in the media library.

New imports get the country from the analyzer.  This command reads the tag
of every imported file whose country is still empty - ID3v2 TXXX, MP4
freeform atom or Vorbis comment, the same names as on import
(``read_custom_tags`` of the analyzer, no ffprobe, no checksum) - and
writes it.  A country that is already set (by hand, by an earlier run or by
an import) is never replaced, and the modification time stays as it is.

Dry run by default: counts what it would write and lists the values.
``--yes`` writes; ``--ids`` restricts the run to the given ids.

Unlike Re-read Tags (which replaces every tag column of the chosen tracks
with what the file says) this touches nothing but empty country columns.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q

from ...models import File
from ...root import get_storage_root


def _empty_country() -> Q:
    return Q(country__isnull=True) | Q(country="")


class Command(BaseCommand):
    help = "Fill the empty country of library tracks from their COUNTRY tag (dry run by default)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--yes", action="store_true", help="write the values")
        parser.add_argument("--ids", nargs="+", type=int, help="only these file ids")

    def handle(self, *args: Any, **options: Any) -> None:
        # pylint: disable=import-outside-toplevel
        from rastatime_analyzer.pipeline.analyze_metadata import read_custom_tags

        write: bool = options["yes"]
        ids: Sequence[int] | None = options.get("ids")
        root = Path(str(get_storage_root()))

        files = File.objects.filter(_empty_country(), import_status=0).exclude(
            filepath__isnull=True
        )
        if ids:
            files = files.filter(pk__in=ids)

        checked = missing = written = 0
        values: Counter[str] = Counter()
        for file_id, filepath in files.order_by("pk").values_list("pk", "filepath").iterator():
            checked += 1
            rel = (filepath or "").lstrip("/").replace("\\", "/")
            path = root / rel
            if not rel or not path.is_file():
                missing += 1
                continue
            country = read_custom_tags(str(path)).get("country")
            if not country:
                continue
            values[country] += 1
            if write:
                # the condition again: an edit since the query wins
                written += File.objects.filter(_empty_country(), pk=file_id).update(country=country)

        found = sum(values.values())
        self.stdout.write(
            f"checked {checked} tracks without country, {found} with a COUNTRY tag, "
            f"{missing} files missing"
        )
        for value, count in values.most_common():
            self.stdout.write(f"  {count:6d}  {value}")
        if write:
            self.stdout.write(self.style.SUCCESS(f"wrote the country of {written} tracks"))
        else:
            self.stdout.write("dry run - nothing written (--yes writes)")
