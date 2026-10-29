"""Minimal .po -> .mo compiler for the legacy frontend catalogs.

RASTATIME 2026-09-27.  The canonical tool is GNU ``msgfmt`` (see
infra/scripts/maintenance/build-locales.ps1), but the studio machine has no
gettext install.  The legacy catalogs are simple - no plurals, no message
contexts, no fuzzy entries - so this stand-in covers them completely:

    python scripts/po2mo.py frontend/legacy/locale/de_DE/LC_MESSAGES/rastatime.po
    python scripts/po2mo.py --all            # every <lang>/LC_MESSAGES/rastatime.po

Format notes (GNU MO, little endian, revision 0): the string table MUST be
sorted by msgid bytes - PHP's gettext binary-searches it.  No hash table is
written (size 0), which every reader treats as "do a binary search".
Obsolete entries (``#~``) and fuzzy entries (``#, fuzzy``) are skipped like
msgfmt does; ``msgid_plural`` / ``msgctxt`` raise so a catalog that grows
those features is compiled with the real tool instead.
"""

import struct
import sys
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


def _unquote(line: str) -> str:
    s = line.strip()
    if not (s.startswith('"') and s.endswith('"')):
        raise ValueError(f"bad string line: {line!r}")
    s = s[1:-1]
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(_ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_po(path: Path) -> dict:
    """Return {msgid: msgstr} for non-fuzzy, non-obsolete entries."""
    catalog = {}
    msgid = msgstr = None
    target = None          # which field continuation lines extend
    fuzzy = False

    def flush():
        nonlocal msgid, msgstr, target, fuzzy
        if msgid is not None and msgstr is not None and not fuzzy:
            if msgstr != "" or msgid == "":      # untranslated entries are dropped
                catalog[msgid] = msgstr
        msgid = msgstr = target = None
        fuzzy = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#~"):
            flush()
            continue
        if line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in line:
                fuzzy = True
            continue
        if line.startswith("msgctxt") or line.startswith("msgid_plural"):
            raise SystemExit(f"{path}: {line.split()[0]} is not supported - use msgfmt")
        if line.startswith("msgid "):
            flush()
            msgid = _unquote(line[6:])
            target = "id"
        elif line.startswith("msgstr "):
            msgstr = _unquote(line[7:])
            target = "str"
        elif line.startswith('"'):
            if target == "id":
                msgid += _unquote(line)
            elif target == "str":
                msgstr += _unquote(line)
    flush()
    return catalog


def write_mo(catalog: dict, out: Path) -> int:
    keys = sorted(catalog.keys(), key=lambda k: k.encode("utf-8"))
    ids = b""
    strs = b""
    offsets = []
    for k in keys:
        kb = k.encode("utf-8")
        vb = catalog[k].encode("utf-8")
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b"\0"
        strs += vb + b"\0"
    n = len(keys)
    header = 7 * 4
    id_table = header
    str_table = id_table + n * 8
    ids_start = str_table + n * 8
    strs_start = ids_start + len(ids)
    body = struct.pack("<7I", 0x950412DE, 0, n, id_table, str_table, 0, 0)
    for o_id, l_id, o_str, l_str in offsets:
        body += struct.pack("<2I", l_id, ids_start + o_id)
    for o_id, l_id, o_str, l_str in offsets:
        body += struct.pack("<2I", l_str, strs_start + o_str)
    body += ids + strs
    out.write_bytes(body)
    return n


def compile_one(po: Path) -> None:
    mo = po.with_suffix(".mo")
    n = write_mo(parse_po(po), mo)
    print(f"{mo}: {n} entries")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--all"]:
        for po in sorted(LOCALE_DIR.glob("*/LC_MESSAGES/rastatime.po")):
            compile_one(po)
    elif args:
        for a in args:
            compile_one(Path(a))
    else:
        raise SystemExit(__doc__)
