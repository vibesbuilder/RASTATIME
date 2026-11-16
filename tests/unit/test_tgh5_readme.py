"""
T-GH-5 - README.md for GitHub.

Verify that the root README.md exists and contains the required sections,
key factual claims, and no references to Linux-only tooling as the primary
runtime. Also checks that a config example file exists.

Test inventory (9 tests):
  1.  README.md exists at the repository root.
  2.  README.md mentions RASTATIME as the project name.
  3.  README.md mentions LibreTime as the upstream fork source.
  4.  README.md mentions Windows 11 as the target platform.
  5.  README.md mentions Liquidsoap as the production playout engine.
  6.  README.md mentions NSSM (Windows service management).
  7.  README.md contains an installation / quick-start section.
  8.  README.md references the AGPL-3.0 license.
  9.  config/rastatime.conf.example exists for safe version-control inclusion.

RASTATIME 2026-11-16 - the WASAPI test is gone: the README was rewritten on
2026-11-05 (eadec826) to describe production, which names no audio API (the
local output is PortAudio, chosen by device name; in production the MME
endpoint), so "WASAPI as the audio backend" was no longer true.
"""

from __future__ import annotations

from pathlib import Path

_REPO   = Path(__file__).resolve().parents[2]
_README = _REPO / "README.md"
_EXAMPLE = _REPO / "config" / "rastatime.conf.example"


def _text() -> str:
    return _README.read_text(encoding="utf-8")


def test_readme_exists():
    """README.md must exist at the repository root."""
    assert _README.exists(), "README.md not found at repository root"


def test_readme_mentions_rastatime():
    """README.md must mention RASTATIME as the project name."""
    assert "RASTATIME" in _text(), "README.md does not mention RASTATIME"


def test_readme_mentions_libretime_fork():
    """README.md must identify LibreTime as the upstream fork source."""
    text = _text().lower()
    assert "libretime" in text, "README.md does not mention LibreTime"


def test_readme_mentions_windows():
    """README.md must mention Windows 11 as the target platform."""
    assert "Windows 11" in _text(), "README.md does not mention Windows 11"


def test_readme_mentions_liquidsoap():
    """README.md must mention Liquidsoap as the production playout engine."""
    text = _text().lower()
    assert "liquidsoap" in text, (
        "README.md does not mention Liquidsoap as the playout engine"
    )


def test_readme_mentions_nssm():
    """README.md must mention NSSM as the Windows service manager."""
    assert "NSSM" in _text(), "README.md does not mention NSSM"


def test_readme_has_quickstart_section():
    """README.md must contain a quick-start or installation section."""
    text = _text().lower()
    assert "quick start" in text or "installation" in text or "install" in text, (
        "README.md has no installation or quick-start section"
    )


def test_readme_mentions_agpl_license():
    """README.md must reference the AGPL-3.0 license."""
    text = _text()
    assert "AGPL" in text or "Affero" in text, (
        "README.md does not mention the AGPL license"
    )


def test_config_example_file_exists():
    """config/rastatime.conf.example must exist for safe version-control inclusion."""
    assert _EXAMPLE.exists(), (
        "config/rastatime.conf.example not found — "
        "safe example config missing from repository"
    )
