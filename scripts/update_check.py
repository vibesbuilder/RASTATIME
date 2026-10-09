#!/usr/bin/env python3
"""
RASTATIME 2026-10-09 - component update check (read-only).

Compares the versions installed on this machine with the newest releases
published by each upstream and prints a table: installed, newest in the
same release line, newest overall, end-of-life date, verdict.  Nothing is
downloaded or changed; the script only reads local version strings and
public release feeds (endoflife.date, PyPI, GitHub releases).

Usage:
    python scripts/update_check.py            # table
    python scripts/update_check.py --json     # machine-readable
    python scripts/update_check.py --offline  # installed versions only

The classes (A exposed, B audio chain, C code dependencies) and the
maintenance procedure are described in docs/operator/COMPONENTS.md.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

TOOLS = Path(r"C:\Tools")
VENV_PY = Path(r"C:\RASTATIME\.venv\Scripts\python.exe")
FFMPEG = Path(r"C:\ffmpeg\bin\ffmpeg.exe")
TIMEOUT = 15
USER_AGENT = "rastatime-update-check/1.0"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT,
                             errors="replace")
        return (out.stdout or "") + (out.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def first_version(text: str, pattern: str = r"(\d+\.\d+(?:\.\d+)?)") -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - fixed public URLs
        return json.loads(resp.read().decode("utf-8"))


def vtuple(v: Optional[str]) -> tuple:
    if not v:
        return ()
    return tuple(int(x) for x in re.findall(r"\d+", v))


def same_line(a: Optional[str], b: Optional[str], parts: int = 2) -> bool:
    return bool(a and b) and vtuple(a)[:parts] == vtuple(b)[:parts]


# ---------------------------------------------------------------------------
# installed versions
# ---------------------------------------------------------------------------

def installed_apache() -> Optional[str]:
    return first_version(run([str(TOOLS / "Apache24" / "bin" / "httpd.exe"), "-v"]), r"Apache/(\d+\.\d+\.\d+)")


def installed_php() -> Optional[str]:
    return first_version(run([str(TOOLS / "PHP" / "php.exe"), "-v"]), r"PHP (\d+\.\d+\.\d+)")


def installed_icecast() -> Optional[str]:
    return first_version(run([str(TOOLS / "Icecast" / "bin" / "icecast.exe"), "-v"]), r"Icecast (\d+\.\d+\.\d+)")


def installed_liquidsoap() -> Optional[str]:
    return first_version(run([str(TOOLS / "liquidsoap" / "liquidsoap.exe"), "--version"]), r"Liquidsoap (\d+\.\d+\.\d+)")


def installed_postgres() -> Optional[str]:
    return first_version(run(["psql", "--version"]), r"PostgreSQL\)? (\d+\.\d+)")


def installed_python() -> Optional[str]:
    return first_version(run([str(VENV_PY), "--version"]), r"Python (\d+\.\d+\.\d+)")


def installed_ffmpeg() -> Optional[str]:
    return first_version(run([str(FFMPEG), "-version"]), r"ffmpeg version (\d+\.\d+(?:\.\d+)?)")


def installed_winacme() -> Optional[str]:
    exe = next(TOOLS.glob("win-acme/wacs.exe"), None)
    if exe is None:
        return None
    text = run([str(exe), "--version"])
    return first_version(text, r"v?(\d+\.\d+\.\d+(?:\.\d+)?)")


_PIP_CACHE: dict[str, str] = {}


def installed_pip(name: str) -> Optional[str]:
    if not _PIP_CACHE:
        text = run([str(VENV_PY), "-m", "pip", "list", "--format=json", "--disable-pip-version-check"])
        try:
            for row in json.loads(text[text.index("["):]):
                _PIP_CACHE[row["name"].lower()] = row["version"]
        except (ValueError, KeyError):
            pass
    return _PIP_CACHE.get(name.lower())


# ---------------------------------------------------------------------------
# upstream feeds
# ---------------------------------------------------------------------------

def feed_endoflife(product: str, installed: Optional[str], line_parts: int = 2):
    """endoflife.date: newest release of the installed line, newest overall, EOL of the line."""
    rows = fetch_json(f"https://endoflife.date/api/{product}.json")
    newest_overall = rows[0].get("latest") if rows else None
    line, eol = None, None
    for row in rows:
        cycle = str(row.get("cycle"))
        if installed and same_line(cycle, installed, line_parts) and vtuple(cycle) == vtuple(installed)[:len(vtuple(cycle))]:
            line, eol = row.get("latest"), row.get("eol")
            break
    return line, newest_overall, eol


def feed_pypi(name: str, installed: Optional[str], line_parts: int = 2):
    data = fetch_json(f"https://pypi.org/pypi/{name}/json")
    newest = data["info"]["version"]
    releases = [v for v, files in data["releases"].items()
                if files and not any(f.get("yanked") for f in files) and re.fullmatch(r"\d+(\.\d+)*", v)]
    line = max((v for v in releases if same_line(v, installed, line_parts)), key=vtuple, default=None)
    return line, newest, None


def feed_github(repo: str, installed: Optional[str], line_parts: int = 2, asset: Optional[str] = None,
                tags: bool = False):
    """GitHub releases (or tags, for projects that publish none - Icecast)."""
    if tags:
        rows = [{"tag_name": t.get("name", ""), "assets": []}
                for t in fetch_json(f"https://api.github.com/repos/{repo}/tags?per_page=50")]
    else:
        rows = fetch_json(f"https://api.github.com/repos/{repo}/releases?per_page=30")
    versions = []
    for row in rows:
        if row.get("draft") or row.get("prerelease"):
            continue
        v = first_version(row.get("tag_name", ""), r"v?(\d+\.\d+\.\d+)")
        if v and not re.search(r"(beta|rc|alpha)", row.get("tag_name", ""), re.I):
            versions.append((v, row))
    newest = max(versions, key=lambda t: vtuple(t[0]), default=(None, None))
    line = max((v for v, _ in versions if same_line(v, installed, line_parts)), key=vtuple, default=None)
    note = None
    if asset and newest[1]:
        names = [a["name"] for a in newest[1].get("assets", []) if asset in a["name"].lower()]
        note = f"asset {names[0]}" if names else f"no {asset} asset"
    return line, newest[0], note


# ---------------------------------------------------------------------------
# the component table
# ---------------------------------------------------------------------------

@dataclass
class Component:
    name: str
    cls: str
    installed_fn: Callable[[], Optional[str]]
    feed: Optional[Callable[[Optional[str]], tuple]] = None
    source: str = ""
    installed: Optional[str] = None
    line: Optional[str] = None
    newest: Optional[str] = None
    eol: Optional[str] = None
    note: Optional[str] = None
    verdict: str = "?"
    extra: dict = field(default_factory=dict)


COMPONENTS: list[Component] = [
    Component("Apache httpd", "A", installed_apache, lambda v: feed_endoflife("apache", v), "Apache Lounge zip"),
    Component("PHP", "A", installed_php, lambda v: feed_endoflife("php", v), "windows.php.net zip (NTS x64)"),
    Component("win-acme", "A", installed_winacme, lambda v: feed_github("win-acme/win-acme", v, 1), "GitHub release zip"),
    Component("PostgreSQL", "C", installed_postgres, lambda v: feed_endoflife("postgresql", v, 1), "EDB installer"),
    Component("Python", "C", installed_python, lambda v: feed_endoflife("python", v), "python.org installer"),
    Component("Django", "C", lambda: installed_pip("Django"), lambda v: feed_endoflife("django", v), "pip"),
    Component("djangorestframework", "C", lambda: installed_pip("djangorestframework"), lambda v: feed_pypi("djangorestframework", v), "pip"),
    Component("django-filter", "C", lambda: installed_pip("django-filter"), lambda v: feed_pypi("django-filter", v, 1), "pip"),
    Component("django-cors-headers", "C", lambda: installed_pip("django-cors-headers"), lambda v: feed_pypi("django-cors-headers", v, 1), "pip"),
    Component("waitress", "C", lambda: installed_pip("waitress"), lambda v: feed_pypi("waitress", v, 1), "pip"),
    Component("psycopg2-binary", "C", lambda: installed_pip("psycopg2-binary"), lambda v: feed_pypi("psycopg2-binary", v), "pip"),
    Component("requests", "C", lambda: installed_pip("requests"), lambda v: feed_pypi("requests", v), "pip"),
    Component("urllib3", "C", lambda: installed_pip("urllib3"), lambda v: feed_pypi("urllib3", v, 1), "pip"),
    Component("Icecast", "B", installed_icecast, lambda v: feed_github("xiph/Icecast-Server", v, tags=True), "icecast.org zip (project dormant)"),
    Component("Liquidsoap", "B", installed_liquidsoap, lambda v: feed_github("savonet/liquidsoap", v, 2, asset="win64.zip"), "GitHub release win64 zip"),
    Component("ffmpeg", "B", installed_ffmpeg, lambda v: feed_endoflife("ffmpeg", v, 1), "gyan.dev essentials build"),
]


def evaluate(c: Component, offline: bool) -> None:
    c.installed = c.installed_fn()
    if offline or c.feed is None:
        c.verdict = "installed" if c.installed else "not found"
        return
    if not c.installed:
        c.verdict = "not found"
        return
    try:
        c.line, c.newest, extra = c.feed(c.installed)
    except Exception as exc:  # noqa: BLE001 - a feed down must not stop the table
        c.verdict = f"feed error: {exc.__class__.__name__}"
        return
    if isinstance(extra, str) and re.match(r"\d{4}-\d{2}-\d{2}", extra):
        c.eol = extra
    elif extra:
        c.note = str(extra)
    inst, line, newest = vtuple(c.installed), vtuple(c.line), vtuple(c.newest)
    if c.eol and c.eol < __import__("datetime").date.today().isoformat():
        c.verdict = "EOL - line unsupported"
    elif line and inst < line:
        c.verdict = "UPDATE in line"
    elif newest and inst < newest:
        c.verdict = "ok (newer line exists)"
    else:
        c.verdict = "ok"


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    as_json = "--json" in argv
    for c in COMPONENTS:
        evaluate(c, offline)
    if as_json:
        print(json.dumps([{k: v for k, v in c.__dict__.items() if k not in ("installed_fn", "feed", "extra")}
                          for c in COMPONENTS], indent=2))
        return 0
    head = f"{'component':22} {'cls':3} {'installed':10} {'in line':10} {'newest':10} {'EOL':11} verdict"
    print(head)
    print("-" * len(head))
    worst = 0
    for c in COMPONENTS:
        print(f"{c.name:22} {c.cls:3} {c.installed or '-':10} {c.line or '-':10} {c.newest or '-':10} "
              f"{c.eol or '-':11} {c.verdict}{'  (' + c.note + ')' if c.note else ''}")
        worst = max(worst, 2 if c.verdict.startswith("EOL") else 1 if c.verdict.startswith("UPDATE") else 0)
    print()
    print("verdicts: ok | ok (newer line exists) = major upgrade is a project | UPDATE in line = patch release "
          "available | EOL = the installed line gets no fixes any more.  See docs/operator/COMPONENTS.md.")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
