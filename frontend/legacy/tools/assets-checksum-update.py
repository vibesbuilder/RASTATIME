#!/usr/bin/env python3

# Extract the checksum for all the assets in the public directory.
import hashlib
import json
from pathlib import Path

legacy_root = Path(__file__).parent.parent

scan_dir = legacy_root / "public"
dest_file = legacy_root / "application/assets.json"
result = {}


def compute_md5(filepath: Path) -> str:
    with filepath.open("rb") as file:
        buffer = hashlib.md5()  # nosec
        while True:
            blob = file.read(8192)
            if not blob:
                break
            buffer.update(blob)

        return buffer.hexdigest()


def compute_md5_foreach_asset_in(root: Path):
    for path in root.iterdir():
        if path.is_dir():
            compute_md5_foreach_asset_in(path)
        else:
            if path.suffix in (".js", ".css"):
                # POSIX separators so the keys match Assets::url() lookups
                # (e.g. "css/styles.css") on every host.  On Windows str(path)
                # yields backslash keys ("css\styles.css") which break every
                # lookup; relative_to(...).as_posix() is OS-independent.
                result_key = path.relative_to(scan_dir).as_posix()
                result[result_key] = compute_md5(path)


compute_md5_foreach_asset_in(scan_dir)
dest_file.write_text(json.dumps(dict(sorted(result.items())), indent=2) + "\n")
