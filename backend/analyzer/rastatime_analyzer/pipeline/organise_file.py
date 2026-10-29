import logging
import re
import shutil
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

MAX_DIR_LEN = 48
MAX_FILE_LEN = 48

# RASTATIME 2026-10-09 - the artist / album folders are built from tag text,
# and Windows refuses the characters < > : " / \ | ? * and control characters
# in a path component as well as a trailing dot or space ("Why Not?!",
# "The Getaway: Black Monday" failed 19 imports of the first bulk batch with
# WinError 123 / 267).  Replace them so the track lands next to its album.
_RESERVED = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# RASTATIME 2026-10-24 - folder for tracks without an artist tag
TAGLESS_DIR = "tagless"


def safe_component(name: str) -> str:
    """Return *name* as a path component every file system accepts."""
    cleaned = _RESERVED.sub("_", name).rstrip(". ")
    return cleaned or "_"


def organise_file(
    filepath_: str,
    storage_url: str,
    original_filename: str,
    metadata: dict,
) -> dict:
    """
    Move the incoming file into the storage, while preserving the original filename.

    If you import multiple copies of the same file, the behavior is:
    - The first filename is preserved.
    - The next filenames receive an uuid append to the name.
    """
    filepath = Path(filepath_)

    orig_filename = Path(original_filename)
    dest_path = Path(storage_url)

    # Building import path
    # RASTATIME 2026-10-24 - a track without an artist tag goes to
    # imported/tagless/ instead of directly into imported/ (operator: 63
    # untagged uploads sat next to the artist folders).  Album folders are
    # kept only under an artist.
    artist = str(metadata.get("artist_name") or "").strip()
    if artist:
        dest_path /= safe_component(artist[0:MAX_DIR_LEN])
        album = str(metadata.get("album_title") or "").strip()
        if album:
            dest_path /= safe_component(album[0:MAX_DIR_LEN])
    else:
        dest_path /= TAGLESS_DIR

    dest_path /= safe_component(orig_filename.stem[0:MAX_FILE_LEN]) + orig_filename.suffix

    # Handle when a file already exists
    if dest_path.is_file():
        if filepath.samefile(dest_path):
            metadata["full_path"] = str(dest_path)
            return metadata

        dest_path = dest_path.with_name(f"{dest_path.stem}_{uuid4()}{dest_path.suffix}")
        logger.warning("found existing file, using new filepath %s", dest_path)

    # Import
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug("moving %s to %s", filepath, dest_path)
    shutil.move(filepath, dest_path)

    metadata["full_path"] = str(dest_path)
    return metadata
