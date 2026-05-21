"""
compile_messages.py — compile .po files to .mo without external gettext tools.

Usage:
    python scripts/compile_messages.py

Finds all .po files under backend/api/locale/ and compiles each to a
sibling .mo file using Python's struct module (pure Python, no msgfmt needed).

This is the Windows-safe alternative to:
    python manage.py compilemessages

The generated .mo files are git-ignored; run this script after pulling new
translations or before starting the Django dev server in a language other
than English.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal .po parser
# ---------------------------------------------------------------------------

def _parse_po(text: str) -> list[tuple[str, str]]:
    """
    Parse a .po file and return a list of (msgid, msgstr) pairs.

    Only single-line msgid/msgstr are handled.  Multi-line continuations
    (lines starting with ``"``) are concatenated.  Header entry (msgid "")
    is included so Django can read the metadata.
    """
    pairs: list[tuple[str, str]] = []
    msgid: str | None = None
    msgstr: str | None = None

    def _flush() -> None:
        if msgid is not None and msgstr is not None:
            pairs.append((msgid, msgstr))

    def _unescape(s: str) -> str:
        return (
            s.replace("\\n", "\n")
             .replace("\\t", "\t")
             .replace('\\"', '"')
             .replace("\\\\", "\\")
        )

    state = "none"
    buf = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            if state != "none":
                if state == "msgid":
                    msgid = buf
                elif state == "msgstr":
                    msgstr = buf
                    _flush()
                    msgid = msgstr = None
                state = "none"
                buf = ""
            continue

        if line.startswith("msgid "):
            if state == "msgstr":
                msgstr = buf
                _flush()
            elif state == "msgid":
                msgid = buf
            state = "msgid"
            buf = _unescape(line[7:-1])  # strip msgid " and trailing "
        elif line.startswith("msgstr "):
            if state == "msgid":
                msgid = buf
            state = "msgstr"
            buf = _unescape(line[8:-1])
        elif line.startswith('"') and line.endswith('"'):
            buf += _unescape(line[1:-1])

    # flush last entry
    if state == "msgstr":
        msgstr = buf
        _flush()
    elif state == "msgid":
        msgid = buf

    return pairs


# ---------------------------------------------------------------------------
# Minimal .mo writer
# ---------------------------------------------------------------------------

def _write_mo(pairs: list[tuple[str, str]], dest: Path) -> None:
    """
    Write a GNU .mo binary file from a list of (msgid, msgstr) pairs.

    Format reference: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
    """
    # Sort by msgid (required by the .mo format for binary search)
    pairs = sorted(pairs, key=lambda p: p[0].encode())

    n = len(pairs)
    # Header size: magic(4) + revision(4) + count(4) + o_offset(4) + t_offset(4)
    #              + hash_size(4) + hash_offset(4) = 28 bytes
    header_size = 28
    # Two tables of n * 2 ints (length + offset) each
    table_size = n * 8

    # Compute offsets
    o_table_offset = header_size
    t_table_offset = header_size + table_size
    strings_offset = t_table_offset + table_size

    # Encode strings
    encoded_originals = [p[0].encode("utf-8") for p in pairs]
    encoded_translated = [p[1].encode("utf-8") for p in pairs]

    # Build string block and record offsets
    orig_offsets: list[tuple[int, int]] = []
    trans_offsets: list[tuple[int, int]] = []
    string_block = bytearray()

    cur = strings_offset
    for s in encoded_originals:
        orig_offsets.append((len(s), cur))
        string_block += s + b"\x00"
        cur += len(s) + 1

    for s in encoded_translated:
        trans_offsets.append((len(s), cur))
        string_block += s + b"\x00"
        cur += len(s) + 1

    # Assemble the file
    magic = 0x950412DE  # little-endian magic
    buf = struct.pack(
        "<IIIIIII",
        magic,       # magic number
        0,           # file format revision
        n,           # number of strings
        o_table_offset,
        t_table_offset,
        0,           # hash table size (0 = no hash table)
        0,           # hash table offset
    )
    for length, offset in orig_offsets:
        buf += struct.pack("<II", length, offset)
    for length, offset in trans_offsets:
        buf += struct.pack("<II", length, offset)
    buf += bytes(string_block)

    dest.write_bytes(buf)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    locale_root = repo_root / "backend" / "api" / "locale"

    po_files = list(locale_root.rglob("*.po"))
    if not po_files:
        print("No .po files found under", locale_root)
        return 0

    errors = 0
    for po_path in po_files:
        mo_path = po_path.with_suffix(".mo")
        try:
            text = po_path.read_text(encoding="utf-8")
            pairs = _parse_po(text)
            pairs = [(mid, mstr) for mid, mstr in pairs if mstr]  # skip untranslated
            _write_mo(pairs, mo_path)
            print(f"  compiled  {po_path.relative_to(repo_root)}  ->  {mo_path.name}  ({len(pairs)} strings)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR     {po_path.relative_to(repo_root)}: {exc}", file=sys.stderr)
            errors += 1

    return errors


if __name__ == "__main__":
    sys.exit(main())
