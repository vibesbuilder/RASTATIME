"""
RASTATIME 2026-05-14 - one-shot playability re-scanner.

Walks every row in ``cc_files``, builds the absolute on-disk path from
``storage.path`` + ``cc_files.filepath``, runs the same FFmpeg-based
playability check that ``libretime_analyzer.pipeline.analyze_playability``
uses at import time, and reports which existing files are broken or
have soft warnings.

This covers the "files already in the library before the FFmpeg-based
check was added" case (the old Liquidsoap-based check silently no-op'd
on RASTATIME / Windows, so all pre-existing imports skipped playability
verification).

Output: one line per problematic file on stdout, plus a summary block
at the end.  Exit code 0 always (this is a reporting tool, not a CI
gate).

Usage (PowerShell, no admin needed)::

    $env:LIBRETIME_CONFIG_FILEPATH = "C:\\rastatime\\config\\libretime.conf"
    & "C:\\RASTATIME\\.venv\\Scripts\\python.exe" `
        "C:\\RASTATIME\\infra\\scripts\\maintenance\\rescan-playability.py"

The script reads the storage root and DB credentials directly from
``libretime.conf`` so it does not need Django's full settings stack.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
import yaml


def _read_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _connect(db_cfg: dict):
    return psycopg2.connect(
        host=db_cfg.get("host", "localhost"),
        port=int(db_cfg.get("port", 5432)),
        dbname=db_cfg.get("name", "rastatime"),
        user=db_cfg.get("user", "rastatime"),
        password=db_cfg.get("password", "rastatime"),
    )


def _probe(ffmpeg: str, path: Path, timeout_s: int) -> tuple[int, str]:
    """Return (returncode, stderr-tail) for an ``ffmpeg -v error -i ... -f null -`` run."""
    try:
        completed = subprocess.run(
            [
                ffmpeg, "-v", "error",
                "-i", str(path),
                "-f", "null", "-",
                "-hide_banner", "-nostats",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError:
        return -1, "ffmpeg not found"
    except subprocess.TimeoutExpired:
        return -2, "timed out"
    return completed.returncode, (completed.stderr or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--config",
        default=r"C:\rastatime\config\libretime.conf",
        help="Path to libretime.conf (default: %(default)s)",
    )
    parser.add_argument(
        "--ffmpeg",
        default=r"C:\ffmpeg\bin\ffmpeg.exe",
        help="Path to ffmpeg.exe (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Per-file decode-verify timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Stop after N files; 0 = all rows.  Useful for spot-check runs.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        print(f"ERROR: config not found: {config_path}", file=sys.stderr)
        return 1

    if not Path(args.ffmpeg).is_file():
        print(f"ERROR: ffmpeg not found: {args.ffmpeg}", file=sys.stderr)
        return 1

    cfg = _read_config(config_path)
    storage_root = Path(cfg.get("storage", {}).get("path", ""))
    if not storage_root.is_dir():
        print(f"ERROR: storage root not found: {storage_root!r}", file=sys.stderr)
        return 1

    db_cfg = cfg.get("database", {})
    print(f"Storage root: {storage_root}")
    print(f"FFmpeg:       {args.ffmpeg}")
    print(f"DB:           {db_cfg.get('user')}@{db_cfg.get('host')}/{db_cfg.get('name')}")
    print()

    conn = _connect(db_cfg)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, filepath FROM cc_files "
        "WHERE file_exists = TRUE AND hidden = FALSE "
        "ORDER BY id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if args.limit > 0:
        rows = rows[: args.limit]
    total = len(rows)

    # Tallies
    n_ok = 0
    n_softwarn = 0
    n_hardfail = 0
    n_missing = 0
    n_inaccessible = 0
    started = time.time()

    for idx, (file_id, rel_path) in enumerate(rows, 1):
        # Strip leading slashes / backslashes before joining: pathlib
        # treats those as absolute-path indicators and would silently
        # drop storage_root.  A handful of legacy cc_files rows start
        # with "/imported/..." instead of "imported/..." (likely from
        # an older importer revision); without this normalisation
        # they show up as MISSING even when the file exists.
        rel_clean = rel_path.lstrip("/\\")
        abs_path = storage_root / rel_clean
        if not abs_path.is_file():
            n_missing += 1
            print(f"MISSING  id={file_id:<6}  {rel_path}")
            continue

        # File exists — distinguish "readable" from "ACL-denied".  On
        # Windows a file placed by a service-account user (e.g.
        # RASTATIME-WORKER running under SYSTEM) can be visible to
        # everyone via dir/ls but block read access via NTFS ACL.
        # FFmpeg then reports "Permission denied" which would otherwise
        # be conflated with "audio data is broken".
        #
        # Python's ``os.access(path, os.R_OK)`` is unreliable on
        # Windows (it inspects POSIX-mode bits which always permit on
        # NTFS).  A real open() with a 1-byte read is the only way to
        # confirm read access from the current user's token.
        try:
            with open(abs_path, "rb") as _fh:
                _fh.read(1)
        except PermissionError:
            n_inaccessible += 1
            print(
                f"INACCESS id={file_id:<6}  (NTFS ACL denies read for "
                f"current user)  {rel_path}"
            )
            continue
        except OSError as exc:
            # Other I/O error - report as inaccessible too so it doesn't
            # masquerade as a corrupt audio file.
            n_inaccessible += 1
            print(f"INACCESS id={file_id:<6}  ({exc.__class__.__name__}: {exc})  {rel_path}")
            continue

        rc, tail = _probe(args.ffmpeg, abs_path, args.timeout)
        if rc == 0 and not tail:
            n_ok += 1
        elif rc == 0 and tail:
            n_softwarn += 1
            first_line = tail.splitlines()[0][:140] if tail else "(no detail)"
            print(f"SOFTWARN id={file_id:<6}  {rel_path}")
            print(f"         {first_line}")
        else:
            n_hardfail += 1
            first_line = tail.splitlines()[0][:140] if tail else "(no detail)"
            print(f"HARDFAIL id={file_id:<6}  rc={rc}  {rel_path}")
            print(f"         {first_line}")

        # Progress every 100 files
        if idx % 100 == 0:
            elapsed = time.time() - started
            rate = idx / elapsed if elapsed > 0 else 0
            print(f"  [progress] {idx}/{total} scanned, {rate:.1f} files/s")

    elapsed = time.time() - started
    print()
    print("=" * 60)
    print("Summary")
    print("-" * 60)
    print(f"  Total scanned:        {total}")
    print(f"  Clean (OK):           {n_ok}")
    print(f"  Soft-warnings:        {n_softwarn}   (file plays, has decoder warnings)")
    print(f"  Hard failures:        {n_hardfail}   (file cannot be decoded by ffmpeg)")
    print(f"  Inaccessible (ACL):   {n_inaccessible}   (file exists but read access denied)")
    print(f"  Missing on disk:      {n_missing}   (DB row exists, file gone)")
    print(f"  Elapsed:              {elapsed:.1f}s")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
