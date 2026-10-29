"""
T-GH-6 - .gitignore, LICENSE and CONTRIBUTING.md.

Verify that all three repository-hygiene files exist and contain the
required content.  No server, database, or installed packages needed.

Test inventory (10 tests):
  1.  .gitignore exists at the repository root.
  2.  .gitignore excludes config/rastatime.conf (the secret-bearing file).
  3.  .gitignore excludes the .venv/ virtual-environment directory.
  4.  .gitignore excludes *.log files.
  5.  .gitignore excludes the runtime media/ directory.
  6.  LICENSE exists at the repository root.
  7.  LICENSE contains the GNU Affero General Public License text.
  8.  CONTRIBUTING.md exists at the repository root.
  9.  CONTRIBUTING.md mentions RASTATIME as the project name.
  10. CONTRIBUTING.md mentions Windows 11 as the only supported platform.
"""

from __future__ import annotations

from pathlib import Path

_REPO         = Path(__file__).resolve().parents[2]
_GITIGNORE    = _REPO / ".gitignore"
_LICENSE      = _REPO / "LICENSE"
_CONTRIBUTING = _REPO / "CONTRIBUTING.md"


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------

def test_gitignore_exists():
    """.gitignore must exist at the repository root."""
    assert _GITIGNORE.exists(), ".gitignore not found at repository root"


def test_gitignore_excludes_real_config():
    """.gitignore must exclude config/rastatime.conf (contains secrets)."""
    text = _GITIGNORE.read_text(encoding="utf-8")
    assert "config/rastatime.conf" in text, (
        ".gitignore does not exclude config/rastatime.conf"
    )


def test_gitignore_excludes_venv():
    """.gitignore must exclude .venv/ (virtual environment)."""
    text = _GITIGNORE.read_text(encoding="utf-8")
    assert ".venv/" in text, ".gitignore does not exclude .venv/"


def test_gitignore_excludes_log_files():
    """.gitignore must exclude *.log files."""
    text = _GITIGNORE.read_text(encoding="utf-8")
    assert "*.log" in text, ".gitignore does not exclude *.log"


def test_gitignore_excludes_media_directory():
    """.gitignore must exclude the runtime media/ directory."""
    text = _GITIGNORE.read_text(encoding="utf-8")
    assert "media/" in text, ".gitignore does not exclude media/"


# ---------------------------------------------------------------------------
# LICENSE
# ---------------------------------------------------------------------------

def test_license_exists():
    """LICENSE must exist at the repository root."""
    assert _LICENSE.exists(), "LICENSE not found at repository root"


def test_license_is_agpl():
    """LICENSE must contain the GNU Affero General Public License text."""
    text = _LICENSE.read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text.upper(), (
        "LICENSE does not appear to be the AGPL"
    )


# ---------------------------------------------------------------------------
# CONTRIBUTING.md
# ---------------------------------------------------------------------------

def test_contributing_exists():
    """CONTRIBUTING.md must exist at the repository root."""
    assert _CONTRIBUTING.exists(), "CONTRIBUTING.md not found at repository root"


def test_contributing_mentions_rastatime():
    """CONTRIBUTING.md must mention RASTATIME as the project name."""
    text = _CONTRIBUTING.read_text(encoding="utf-8")
    assert "RASTATIME" in text, "CONTRIBUTING.md does not mention RASTATIME"


def test_contributing_mentions_windows():
    """CONTRIBUTING.md must name Windows 11 as the only supported platform."""
    text = _CONTRIBUTING.read_text(encoding="utf-8")
    assert "Windows 11" in text, (
        "CONTRIBUTING.md does not mention Windows 11 as the supported platform"
    )
