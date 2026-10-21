import logging
from pathlib import Path
from typing import List, Optional

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q
from libretime_shared.files import compute_md5

from ....core.models import Preference
from ...models import File, Library

logger = logging.getLogger(__name__)

# RASTATIME 2026-10-16 - Settings -> Local Machine -> Import Folder checkbox
# "Bulk import: also import files whose audio is already in the library"
ALLOW_DUPLICATES_PREF_KEY = "bulk_import_allow_duplicates"


def allow_duplicates_from_preference() -> bool:
    """True when the operator switched duplicates on in the settings page."""
    value = (
        Preference.site.filter(key=ALLOW_DUPLICATES_PREF_KEY)
        .values_list("value", flat=True)
        .first()
    )
    return str(value or "").strip().lower() in ("true", "1", "on", "yes")

# RASTATIME 2026-10-14 - aligned with the extensions the import folder /
# FTP scan and CcFiles::createAndImport accept (raw .aac is repacked to
# .m4a by the analyzer, .oga is an Ogg container).
DEFAULT_ALLOWED_EXTENSIONS = [
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",  # RASTATIME 2026-10-21 - transcoded to MP3 by the analyzer
]


class Command(BaseCommand):
    help = "Bulk file upload."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--path",
            help="Path to the directory to scan.",
            required=True,
        )
        parser.add_argument(
            "--library",
            help="Library for the new files.",
        )
        parser.add_argument(
            "--allowed-extensions",
            help="Allowed file extensions.",
            action="append",
            default=DEFAULT_ALLOWED_EXTENSIONS,
        )
        parser.add_argument(
            "--delete-after-upload",
            help="Delete file if upload succeeded.",
            action="store_true",
        )
        parser.add_argument(
            "--delete-if-exists",
            help="Delete file if it already exists.",
            action="store_true",
        )
        # RASTATIME 2026-10-16 - operator wish: a file whose md5 is already
        # in the library is imported anyway (same audio, different tags).
        parser.add_argument(
            "--allow-duplicates",
            help=(
                "Import a file even when its md5 is already in the library "
                "(default: the checkbox under Settings -> Local Machine -> "
                "Import Folder)."
            ),
            action="store_true",
        )

    def handle(self, *args, **options):
        url = settings.CONFIG.general.public_url
        auth_key = settings.CONFIG.general.api_key

        delete_after_upload = options.get("delete_after_upload", False)
        delete_if_exists = options.get("delete_if_exists", False)
        allow_duplicates = options.get("allow_duplicates", False)
        if not allow_duplicates and allow_duplicates_from_preference():
            allow_duplicates = True
            logger.info("duplicates allowed by the settings page")

        path = options.get("path")
        library = options.get("library", None)
        allowed_extensions = options.get("allowed_extensions")

        importer = Importer(
            url,
            auth_key,
            delete_after_upload,
            delete_if_exists,
            allow_duplicates,
        )
        importer.import_dir(Path(path).resolve(), library, allowed_extensions)


class Importer:
    def __init__(
        self,
        url: str,
        auth_key: str,
        delete_after_upload: bool = False,
        delete_if_exists: bool = False,
        allow_duplicates: bool = False,
    ) -> None:
        self.url = url
        self.auth_key = auth_key

        self.delete_after_upload = delete_after_upload
        self.delete_if_exists = delete_if_exists
        self.allow_duplicates = allow_duplicates

    def _check_file_md5(self, filepath: Path) -> bool:
        file_md5 = compute_md5(filepath)

        # RASTATIME 2026-10-14 - a lossless original converted to MP3 on
        # import is stored with the md5 of the MP3; its own md5 is kept in
        # source_md5 (legacy migration 0066), so the same WAV / FLAC is
        # still recognised as already imported.
        return File.objects.filter(Q(md5=file_md5) | Q(source_md5=file_md5)).exists()

    def _upload_file(self, filepath: Path, library: Optional[str]) -> None:
        try:
            resp = requests.post(
                f"{self.url}/rest/media",
                auth=(self.auth_key, ""),
                files=[
                    ("file", (filepath.name, filepath.open("rb"))),
                ],
                timeout=30,
                cookies={"tt_upload": library} if library is not None else {},
            )
            resp.raise_for_status()

        except requests.exceptions.HTTPError as exception:
            raise RuntimeError(f"could not upload {filepath}") from exception

    def _delete_file(self, filepath: Path) -> None:
        logger.info("deleting %s", filepath)
        filepath.unlink()

    def _handle_file(self, filepath: Path, library: Optional[str]) -> None:
        logger.debug("handling file %s", filepath)

        if not filepath.is_file():
            raise ValueError(f"provided path {filepath} is not a file")

        if self._check_file_md5(filepath):
            if self.allow_duplicates:
                logger.info("found similar md5sum, importing anyway %s", filepath)
            else:
                logger.info("found similar md5sum, ignoring %s", filepath)
                if self.delete_if_exists:
                    self._delete_file(filepath)
                return

        self._upload_file(filepath, library)

        if self.delete_after_upload:
            self._delete_file(filepath)

    def _walk_dir(
        self,
        path: Path,
        library: Optional[str],
        allowed_extensions: List[str],
    ) -> None:
        if not path.is_dir():
            raise ValueError(f"provided path {path} is not a directory")

        for sub_path in path.iterdir():
            if sub_path.is_dir():
                self._walk_dir(sub_path, library, allowed_extensions)
                continue

            if sub_path.suffix.lower() not in allowed_extensions:
                continue

            self._handle_file(sub_path.resolve(), library)

    def _check_library(self, library: str) -> bool:
        return Library.objects.filter(code=library).exists()

    def import_dir(
        self,
        path: Path,
        library: Optional[str],
        allowed_extensions: List[str],
    ) -> None:
        if library is not None and not self._check_library(library):
            raise ValueError(f"provided library {library} does not exist")

        allowed_extensions = [
            (x if x.startswith(".") else "." + x) for x in allowed_extensions
        ]

        self._walk_dir(path, library, allowed_extensions)
