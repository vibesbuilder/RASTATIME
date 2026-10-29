"""
T23.1 — Install guide tests.

Verify that docs/operator/INSTALL.md exists and contains all required
content: prerequisite software with version requirements, the standard
install directory, venv and dependency setup, database initialisation,
service installation via the T22.1 scripts, first-run verification via
status.ps1, and the rastatime.conf configuration file reference.

Test inventory (10 tests, always run — no Django needed):
  1.  INSTALL.md exists.
  2.  All four prerequisite tools are documented
      (Python, PostgreSQL, VLC, NSSM).
  3.  Python minimum version (3.11) is stated.
  4.  PostgreSQL port 5432 is referenced.
  5.  VLC / libVLC is referenced (ADR-002 dependency).
  6.  The C:\\rastatime install directory is documented.
  7.  rastatime.conf is referenced as the required config file.
  8.  The T22.1 install scripts (install-*.ps1) are referenced.
  9.  status.ps1 (T22.3) is referenced for post-install verification.
 10.  A virtual environment (venv) setup step is documented.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DOC  = _REPO / "docs" / "operator" / "INSTALL.md"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1  File existence
# ---------------------------------------------------------------------------

def test_install_guide_exists():
    """docs/operator/INSTALL.md must exist."""
    assert _DOC.exists(), f"Missing: {_DOC}"


# ---------------------------------------------------------------------------
# 2  All four prerequisites documented
# ---------------------------------------------------------------------------

def test_all_prerequisites_documented():
    """
    INSTALL.md must document all four prerequisite tools:
    Python, PostgreSQL, VLC (libVLC), and NSSM.
    """
    doc = _doc()
    missing = []
    for tool in ("Python", "PostgreSQL", "VLC", "NSSM"):
        if tool not in doc:
            missing.append(tool)
    assert not missing, f"Missing prerequisite documentation: {missing}"


# ---------------------------------------------------------------------------
# 3  Python 3.11 minimum version
# ---------------------------------------------------------------------------

def test_python_311_minimum_documented():
    """INSTALL.md must state Python 3.11 as the minimum required version."""
    assert "3.11" in _doc(), (
        "INSTALL.md must document Python 3.11 as the minimum version"
    )


# ---------------------------------------------------------------------------
# 4  PostgreSQL port 5432
# ---------------------------------------------------------------------------

def test_postgresql_port_5432_referenced():
    """INSTALL.md must reference port 5432 (PostgreSQL default)."""
    assert "5432" in _doc(), (
        "INSTALL.md must reference PostgreSQL default port 5432"
    )


# ---------------------------------------------------------------------------
# 5  VLC / libVLC referenced
# ---------------------------------------------------------------------------

def test_vlc_libvlc_referenced():
    """
    INSTALL.md must reference libVLC (the playout engine dependency,
    ADR-002) so operators know to install the 64-bit VLC build.
    """
    doc = _doc()
    assert "libVLC" in doc or "libvlc" in doc.lower(), (
        "INSTALL.md must reference libVLC as a required dependency"
    )


# ---------------------------------------------------------------------------
# 6  C:\rastatime install directory
# ---------------------------------------------------------------------------

def test_install_directory_documented():
    """
    INSTALL.md must document C:\\rastatime as the standard install
    directory so operators know where to place the application files.
    """
    doc = _doc()
    assert "C:\\rastatime" in doc or r"C:\rastatime" in doc, (
        "INSTALL.md must document the C:\\rastatime install directory"
    )


# ---------------------------------------------------------------------------
# 7  rastatime.conf config file
# ---------------------------------------------------------------------------

def test_libretime_conf_referenced():
    """
    INSTALL.md must reference rastatime.conf as the required
    configuration file (set via RASTATIME_CONFIG_FILEPATH).
    """
    assert "rastatime.conf" in _doc(), (
        "INSTALL.md must reference rastatime.conf as the config file"
    )


# ---------------------------------------------------------------------------
# 8  T22.1 install scripts referenced
# ---------------------------------------------------------------------------

def test_install_scripts_referenced():
    """
    INSTALL.md must reference the T22.1 install-*.ps1 scripts so
    operators know how to register the Windows services.
    """
    doc = _doc()
    assert "install-" in doc and ".ps1" in doc, (
        "INSTALL.md must reference the T22.1 install-*.ps1 scripts"
    )


# ---------------------------------------------------------------------------
# 9  status.ps1 referenced for verification
# ---------------------------------------------------------------------------

def test_status_ps1_referenced():
    """
    INSTALL.md must reference status.ps1 (T22.3) so operators can
    verify the installation is healthy before going live.
    """
    assert "status.ps1" in _doc(), (
        "INSTALL.md must reference infra\\nssm\\status.ps1 for verification"
    )


# ---------------------------------------------------------------------------
# 10  venv setup documented
# ---------------------------------------------------------------------------

def test_venv_setup_documented():
    """
    INSTALL.md must document creating a Python virtual environment (venv)
    so dependencies are isolated from the system Python installation.
    """
    doc = _doc()
    assert "venv" in doc, (
        "INSTALL.md must document the Python venv setup step"
    )
