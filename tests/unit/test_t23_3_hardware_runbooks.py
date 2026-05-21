"""
T23.3 — Device-missing and line-in-broken runbook tests.

Verify that both hardware troubleshooting runbooks exist and contain the
required content: playout log references, stable ID concept, service names,
channel mapping, status.ps1, and the standard install directory.

Test inventory (10 tests, always run — no Django needed):
  1.  DEVICE_MISSING.md exists.
  2.  LINE_IN_BROKEN.md exists.
  3.  DEVICE_MISSING.md references the playout log path.
  4.  DEVICE_MISSING.md documents the stable_id concept.
  5.  DEVICE_MISSING.md references RASTATIME-PLAYOUT.
  6.  LINE_IN_BROKEN.md references channel mapping.
  7.  LINE_IN_BROKEN.md references line-in (or linein).
  8.  LINE_IN_BROKEN.md references RASTATIME-PLAYOUT.
  9.  Both documents reference status.ps1 for initial assessment.
 10.  Both documents reference C:\\rastatime as the install directory.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OPS  = _REPO / "docs" / "operator"

_DEVICE_MISSING = _OPS / "DEVICE_MISSING.md"
_LINE_IN_BROKEN = _OPS / "LINE_IN_BROKEN.md"

_BOTH = [_DEVICE_MISSING, _LINE_IN_BROKEN]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–2  File existence
# ---------------------------------------------------------------------------

def test_device_missing_runbook_exists():
    """docs/operator/DEVICE_MISSING.md must exist."""
    assert _DEVICE_MISSING.exists(), f"Missing: {_DEVICE_MISSING}"


def test_line_in_broken_runbook_exists():
    """docs/operator/LINE_IN_BROKEN.md must exist."""
    assert _LINE_IN_BROKEN.exists(), f"Missing: {_LINE_IN_BROKEN}"


# ---------------------------------------------------------------------------
# 3  DEVICE_MISSING — playout log path
# ---------------------------------------------------------------------------

def test_device_missing_references_playout_log():
    """
    DEVICE_MISSING.md must reference the playout log so operators
    know where to find the DeviceUnavailableError trace.
    """
    text = _read(_DEVICE_MISSING)
    assert "playout" in text.lower() and "log" in text.lower(), (
        "DEVICE_MISSING.md must reference the playout log file"
    )


# ---------------------------------------------------------------------------
# 4  DEVICE_MISSING — stable_id concept
# ---------------------------------------------------------------------------

def test_device_missing_documents_stable_id():
    """
    DEVICE_MISSING.md must document the stable_id concept (the Windows
    audio endpoint GUID used to identify devices persistently) so operators
    understand why a device ID changes when hardware is swapped.
    """
    text = _read(_DEVICE_MISSING)
    assert "stable_id" in text or "stable id" in text.lower(), (
        "DEVICE_MISSING.md must explain the stable_id device identifier"
    )


# ---------------------------------------------------------------------------
# 5  DEVICE_MISSING — RASTATIME-PLAYOUT service
# ---------------------------------------------------------------------------

def test_device_missing_references_playout_service():
    """DEVICE_MISSING.md must reference the RASTATIME-PLAYOUT service."""
    assert "RASTATIME-PLAYOUT" in _read(_DEVICE_MISSING), (
        "DEVICE_MISSING.md must reference the RASTATIME-PLAYOUT service"
    )


# ---------------------------------------------------------------------------
# 6  LINE_IN_BROKEN — channel mapping
# ---------------------------------------------------------------------------

def test_line_in_broken_references_channel_mapping():
    """
    LINE_IN_BROKEN.md must reference channel mapping so operators
    know how to correct 0-based channel index configuration errors.
    """
    text = _read(_LINE_IN_BROKEN).lower()
    assert "channel" in text and "mapping" in text, (
        "LINE_IN_BROKEN.md must document channel mapping"
    )


# ---------------------------------------------------------------------------
# 7  LINE_IN_BROKEN — line-in reference
# ---------------------------------------------------------------------------

def test_line_in_broken_references_line_in():
    """LINE_IN_BROKEN.md must reference 'line-in' or 'linein'."""
    text = _read(_LINE_IN_BROKEN).lower()
    assert "line-in" in text or "linein" in text, (
        "LINE_IN_BROKEN.md must reference line-in audio sources"
    )


# ---------------------------------------------------------------------------
# 8  LINE_IN_BROKEN — RASTATIME-PLAYOUT service
# ---------------------------------------------------------------------------

def test_line_in_broken_references_playout_service():
    """LINE_IN_BROKEN.md must reference the RASTATIME-PLAYOUT service."""
    assert "RASTATIME-PLAYOUT" in _read(_LINE_IN_BROKEN), (
        "LINE_IN_BROKEN.md must reference the RASTATIME-PLAYOUT service"
    )


# ---------------------------------------------------------------------------
# 9  Both documents reference status.ps1
# ---------------------------------------------------------------------------

def test_both_runbooks_reference_status_script():
    """Both runbooks must reference status.ps1 as the first diagnostic step."""
    missing = [p.name for p in _BOTH if "status.ps1" not in _read(p)]
    assert not missing, (
        f"Runbooks missing status.ps1 reference: {missing}"
    )


# ---------------------------------------------------------------------------
# 10  Both documents reference C:\rastatime
# ---------------------------------------------------------------------------

def test_both_runbooks_reference_install_directory():
    """Both runbooks must reference C:\\rastatime for unambiguous log paths."""
    missing = []
    for p in _BOTH:
        text = _read(p)
        if r"C:\rastatime" not in text and "C:\\rastatime" not in text:
            missing.append(p.name)
    assert not missing, (
        f"Runbooks missing C:\\rastatime install directory reference: {missing}"
    )
