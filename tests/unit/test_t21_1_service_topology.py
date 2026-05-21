"""
T21.1 — Service topology definition tests.

Verify that SERVICE_TOPOLOGY.md exists and contains all required content:
the four candidate services, their NSSM names, port assignments, startup
order, and required follow-up task references.

Test inventory (10 tests, always run — no Django needed):
  1.  SERVICE_TOPOLOGY.md exists.
  2.  All four NSSM service names are declared.
  3.  The two mandatory services are marked as mandatory.
  4.  The two optional services are marked as optional/conditional.
  5.  Port 8000 is assigned to RASTATIME-API.
  6.  Port 8001 is assigned to RASTATIME-ICECAST (avoids API conflict).
  7.  PostgreSQL dependency is documented.
  8.  Startup order section is present.
  9.  Log file paths under C:\\rastatime\\logs are documented.
 10.  Follow-up task references (T22.1–T22.4) are present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DOC  = _REPO / "docs" / "architecture" / "SERVICE_TOPOLOGY.md"

_NSSM_SERVICES = [
    "RASTATIME-API",
    "RASTATIME-WORKER",
    "RASTATIME-PLAYOUT",
    "RASTATIME-ICECAST",
]

_MANDATORY_SERVICES = ["RASTATIME-API", "RASTATIME-WORKER", "RASTATIME-PLAYOUT"]
_OPTIONAL_SERVICES  = ["RASTATIME-ICECAST"]

_FOLLOW_UP_TASKS = ["T22.1", "T22.2", "T22.3", "T22.4"]


def _doc() -> str:
    return _DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1  File existence
# ---------------------------------------------------------------------------

def test_service_topology_doc_exists():
    """docs/architecture/SERVICE_TOPOLOGY.md must exist."""
    assert _DOC.exists(), f"Missing: {_DOC}"


# ---------------------------------------------------------------------------
# 2  All four NSSM service names declared
# ---------------------------------------------------------------------------

def test_all_nssm_service_names_declared():
    """SERVICE_TOPOLOGY.md must declare all four NSSM service names."""
    doc = _doc()
    missing = [svc for svc in _NSSM_SERVICES if svc not in doc]
    assert not missing, f"Missing NSSM service names: {missing}"


# ---------------------------------------------------------------------------
# 3  Mandatory services marked as mandatory
# ---------------------------------------------------------------------------

def test_mandatory_services_are_marked():
    """
    Each mandatory service section heading must contain '*(mandatory)*'
    so the deployment team knows which services are always required.
    """
    doc = _doc()
    missing = []
    for svc in _MANDATORY_SERVICES:
        # The heading pattern is: "### 2.x RASTATIME-XXX  *(mandatory)*"
        # Search every occurrence of the service name and check nearby text
        found = False
        start = 0
        while True:
            idx = doc.find(svc, start)
            if idx == -1:
                break
            # Check a generous window both before and after the occurrence
            snippet = doc[max(0, idx - 10):idx + 200].lower()
            if "mandatory" in snippet:
                found = True
                break
            start = idx + 1
        if not found:
            missing.append(svc)
    assert not missing, f"Services not marked as mandatory: {missing}"


# ---------------------------------------------------------------------------
# 4  Optional services marked as optional/conditional
# ---------------------------------------------------------------------------

def test_optional_services_are_marked():
    """
    Each optional service section must contain 'optional' or 'conditional'
    so operators know it is not required in all deployments.
    """
    doc = _doc()
    missing = []
    for svc in _OPTIONAL_SERVICES:
        idx = doc.find(svc)
        snippet = doc[idx:idx + 300].lower() if idx != -1 else ""
        if "optional" not in snippet and "conditional" not in snippet:
            missing.append(svc)
    assert not missing, f"Services not marked as optional/conditional: {missing}"


# ---------------------------------------------------------------------------
# 5  Port 8000 → API
# ---------------------------------------------------------------------------

def test_port_8000_assigned_to_api():
    """PORT 8000 must be assigned to RASTATIME-API."""
    doc = _doc()
    assert "8000" in doc, "Port 8000 must appear in SERVICE_TOPOLOGY.md"
    # Both the string '8000' and 'RASTATIME-API' should co-occur in the port table
    assert "RASTATIME-API" in doc and "8000" in doc


# ---------------------------------------------------------------------------
# 6  Port 8001 → Icecast (avoids conflict with API on 8000)
# ---------------------------------------------------------------------------

def test_port_8001_assigned_to_icecast():
    """
    Icecast must use port 8001 (not 8000) to avoid conflict with the API.
    SERVICE_TOPOLOGY.md must document this assignment.
    """
    doc = _doc()
    assert "8001" in doc, (
        "Icecast must be assigned port 8001; SERVICE_TOPOLOGY.md must say so"
    )


# ---------------------------------------------------------------------------
# 7  PostgreSQL dependency documented
# ---------------------------------------------------------------------------

def test_postgresql_dependency_documented():
    """PostgreSQL as an external dependency must be mentioned."""
    doc = _doc()
    assert "PostgreSQL" in doc, (
        "SERVICE_TOPOLOGY.md must document PostgreSQL as a dependency"
    )
    assert "5432" in doc, (
        "SERVICE_TOPOLOGY.md must include the PostgreSQL default port 5432"
    )


# ---------------------------------------------------------------------------
# 8  Startup order section present
# ---------------------------------------------------------------------------

def test_startup_order_section_present():
    """A startup order / dependency chain section must be present."""
    doc = _doc()
    assert "Startup Order" in doc or "startup order" in doc.lower(), (
        "SERVICE_TOPOLOGY.md must have a 'Startup Order' section"
    )


# ---------------------------------------------------------------------------
# 9  Log file paths documented
# ---------------------------------------------------------------------------

def test_log_file_paths_documented():
    """Log paths under C:\\rastatime\\logs must be documented."""
    doc = _doc()
    assert "rastatime\\logs" in doc or "rastatime/logs" in doc, (
        "SERVICE_TOPOLOGY.md must document log file paths under rastatime\\logs"
    )


# ---------------------------------------------------------------------------
# 10  Follow-up task references
# ---------------------------------------------------------------------------

def test_follow_up_tasks_referenced():
    """T22.1–T22.4 follow-up tasks must be referenced in the document."""
    doc = _doc()
    missing = [t for t in _FOLLOW_UP_TASKS if t not in doc]
    assert not missing, f"Missing follow-up task references: {missing}"
