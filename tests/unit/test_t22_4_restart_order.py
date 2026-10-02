"""
T22.4 — RESTART_ORDER.md tests.

Verify that docs/operator/RESTART_ORDER.md exists and contains all
required content: startup and shutdown sequences, per-service recovery
procedures, health verification steps, the API health endpoint, all
four NSSM service names, port references, log file paths, and
references to the T22.1–T22.3 tooling scripts.

Test inventory (10 tests, always run — no Django needed):
  1.  RESTART_ORDER.md exists.
  2.  All four NSSM service names are present.
  3.  Startup order section is present.
  4.  Shutdown order section is present.
  5.  API health endpoint URL is documented.
  6.  Port 8765 (API; 8000 is Icecast's since the 2026-08 machine
      migration - test updated 2026-10-02) and port 5432 (PostgreSQL)
      are referenced.
  7.  Log file paths under C:\\rastatime\\logs are referenced.
  8.  Per-service recovery procedure is documented.
  9.  References to T22.1 install scripts are present.
 10.  References to T22.3 status script are present.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DOC  = _REPO / "docs" / "operator" / "RESTART_ORDER.md"

_SERVICE_NAMES = [
    "RASTATIME-API",
    "RASTATIME-WORKER",
    "RASTATIME-PLAYOUT",
    "RASTATIME-ICECAST",
]

_HEALTH_URL = "http://127.0.0.1:8765/health"


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1  File existence
# ---------------------------------------------------------------------------

def test_restart_order_doc_exists():
    """docs/operator/RESTART_ORDER.md must exist."""
    assert _DOC.exists(), f"Missing: {_DOC}"


# ---------------------------------------------------------------------------
# 2  All four NSSM service names
# ---------------------------------------------------------------------------

def test_all_service_names_present():
    """RESTART_ORDER.md must reference all four RASTATIME service names."""
    doc = _doc()
    missing = [svc for svc in _SERVICE_NAMES if svc not in doc]
    assert not missing, f"Missing service names: {missing}"


# ---------------------------------------------------------------------------
# 3  Startup order section
# ---------------------------------------------------------------------------

def test_startup_order_section_present():
    """A startup order section must be documented."""
    doc = _doc().lower()
    assert "startup" in doc or "start order" in doc, (
        "RESTART_ORDER.md must contain a startup order section"
    )


# ---------------------------------------------------------------------------
# 4  Shutdown order section
# ---------------------------------------------------------------------------

def test_shutdown_order_section_present():
    """A shutdown order section must be documented."""
    doc = _doc().lower()
    assert "shutdown" in doc or "stop order" in doc, (
        "RESTART_ORDER.md must contain a shutdown order section"
    )


# ---------------------------------------------------------------------------
# 5  API health endpoint URL
# ---------------------------------------------------------------------------

def test_api_health_url_documented():
    """The API health endpoint must be referenced for verification steps."""
    assert _HEALTH_URL in _doc(), (
        f"RESTART_ORDER.md must reference the health URL: {_HEALTH_URL!r}"
    )


# ---------------------------------------------------------------------------
# 6  Port references
# ---------------------------------------------------------------------------

def test_port_references_present():
    """Ports 8765 (API) and 5432 (PostgreSQL) must be referenced."""
    doc = _doc()
    assert "8765" in doc, "RESTART_ORDER.md must reference port 8765 (API)"
    assert "5432" in doc, "RESTART_ORDER.md must reference port 5432 (PostgreSQL)"


# ---------------------------------------------------------------------------
# 7  Log file paths
# ---------------------------------------------------------------------------

def test_log_file_paths_referenced():
    """Log paths under C:\\rastatime\\logs must appear for recovery guidance."""
    doc = _doc()
    assert "rastatime\\logs" in doc or "rastatime/logs" in doc, (
        "RESTART_ORDER.md must reference log paths under rastatime\\logs"
    )


# ---------------------------------------------------------------------------
# 8  Per-service recovery procedure
# ---------------------------------------------------------------------------

def test_per_service_recovery_documented():
    """
    Recovery procedures must be documented per service.
    Check for 'recovery' or 'recover' in the document.
    """
    doc = _doc().lower()
    assert "recover" in doc, (
        "RESTART_ORDER.md must document per-service recovery procedures"
    )


# ---------------------------------------------------------------------------
# 9  T22.1 install script references
# ---------------------------------------------------------------------------

def test_install_script_references_present():
    """
    References to the T22.1 install scripts (install-*.ps1) must appear
    so operators know how to reinstall a failed service.
    """
    doc = _doc()
    assert "install-" in doc and ".ps1" in doc, (
        "RESTART_ORDER.md must reference the T22.1 install-*.ps1 scripts"
    )


# ---------------------------------------------------------------------------
# 10  T22.3 status script reference
# ---------------------------------------------------------------------------

def test_status_script_reference_present():
    """
    A reference to status.ps1 (T22.3) must appear so operators know
    how to verify the service stack after a restart or recovery.
    """
    assert "status.ps1" in _doc(), (
        "RESTART_ORDER.md must reference status.ps1 (T22.3 health helper)"
    )
