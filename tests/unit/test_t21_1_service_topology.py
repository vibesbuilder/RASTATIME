"""
T21.1 — Service topology definition tests.

Verify that SERVICE_TOPOLOGY.md exists and contains all required content:
the four candidate services, their NSSM names, port assignments, startup
order, and required follow-up task references.

Since the Liquidsoap cutover Icecast is part of the production stack
(public streams + DJ input mounts) rather than an optional add-on, and
the API moved to port 8765 so that Icecast keeps its conventional 8000
(RASTATIME 2026-08 machine migration; tests updated 2026-10-02).

Test inventory (10 tests, always run — no Django needed):
  1.  SERVICE_TOPOLOGY.md exists.
  2.  All four NSSM service names are declared.
  3.  The three mandatory services are marked as mandatory.
  4.  RASTATIME-ICECAST is documented as part of the production stack.
  5.  Port 8765 is assigned to RASTATIME-API.
  6.  Port 8000 is assigned to RASTATIME-ICECAST.
  7.  PostgreSQL dependency is documented.
  8.  Startup order section is present.
  9.  Log file paths under C:\\rastatime\\logs are documented.
 10.  Follow-up task references (T22.1–T22.4) are present.
"""

from __future__ import annotations

import re
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
# 4  Icecast is part of the production stack
# ---------------------------------------------------------------------------

def test_icecast_is_part_of_the_production_stack():
    """
    Icecast used to be the one optional service; since the Liquidsoap
    cutover it carries the public streams and the DJ input mounts, so
    the "Optional / Conditional Components" table must say so instead
    of calling it optional - an operator must not skip installing it.
    """
    doc = _doc()
    start = doc.find("## 4.")
    assert start != -1, "SERVICE_TOPOLOGY.md must keep section 4 (components)"
    end = doc.find("\n## ", start + 1)
    section = doc[start:end if end != -1 else None]
    assert "RASTATIME-ICECAST" in section, (
        "Section 4 must list RASTATIME-ICECAST"
    )
    assert "production stack" in section.lower(), (
        "Section 4 must document RASTATIME-ICECAST as part of the production stack"
    )


# ---------------------------------------------------------------------------
# 5  Port 8765 → API
# ---------------------------------------------------------------------------

def test_port_8765_assigned_to_api():
    """The port summary must assign 8765 to RASTATIME-API."""
    doc = _doc()
    assert re.search(r"RASTATIME-API\s*\|\s*8765\b", doc), (
        "SERVICE_TOPOLOGY.md port summary must assign 8765 to RASTATIME-API"
    )


# ---------------------------------------------------------------------------
# 6  Port 8000 → Icecast
# ---------------------------------------------------------------------------

def test_port_8000_assigned_to_icecast():
    """The port summary must assign Icecast's conventional 8000 to RASTATIME-ICECAST."""
    doc = _doc()
    assert re.search(r"RASTATIME-ICECAST\s*\|\s*8000\b", doc), (
        "SERVICE_TOPOLOGY.md port summary must assign 8000 to RASTATIME-ICECAST"
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
