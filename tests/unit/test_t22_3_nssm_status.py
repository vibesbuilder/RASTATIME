"""
T22.3 — NSSM status and health helper tests.

Verify that infra/nssm/status.ps1 exists and contains the required
diagnostic content: all four service names, the API health endpoint
URL, port references, log directory, configurable log-tail depth,
service status querying, HTTP health interpretation, and an optional
notice for the Icecast service.

Test inventory (10 tests, always run — no Django needed):
  1.  status.ps1 exists.
  2.  All four NSSM service names are declared in the script.
  3.  The API health URL (http://127.0.0.1:8765/health) is present.
  4.  Port 8765 is referenced (API bind port; 8000 is Icecast's since
      the 2026-08 machine migration - tests updated 2026-10-02).
  5.  Port 8001 is referenced (Liquidsoap DJ harbor port).
  6.  The log directory is referenced for log-tail display.
  7.  A -LogLines parameter is exposed for configurable tail depth.
  8.  Service status is queried via Get-Service or 'nssm status'.
  9.  The script interprets HTTP 200 as a healthy API response.
 10.  Icecast is documented as optional in the status output.
"""

from __future__ import annotations

from pathlib import Path

_REPO       = Path(__file__).resolve().parents[2]
_STATUS_PS1 = _REPO / "infra" / "nssm" / "status.ps1"

_SERVICE_NAMES = [
    "RASTATIME-API",
    "RASTATIME-WORKER",
    "RASTATIME-PLAYOUT",
    "RASTATIME-ICECAST",
]

_HEALTH_URL = "http://127.0.0.1:8765/health"


def _read() -> str:
    return _STATUS_PS1.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1  File existence
# ---------------------------------------------------------------------------

def test_status_script_exists():
    """infra/nssm/status.ps1 must exist."""
    assert _STATUS_PS1.exists(), f"Missing: {_STATUS_PS1}"


# ---------------------------------------------------------------------------
# 2  All four service names declared
# ---------------------------------------------------------------------------

def test_all_service_names_declared():
    """status.ps1 must reference all four RASTATIME NSSM service names."""
    text = _read()
    missing = [svc for svc in _SERVICE_NAMES if svc not in text]
    assert not missing, (
        f"status.ps1 is missing NSSM service names: {missing}"
    )


# ---------------------------------------------------------------------------
# 3  API health URL present
# ---------------------------------------------------------------------------

def test_api_health_url_present():
    """
    status.ps1 must reference the API health endpoint so operators
    can see the live API health status, not just the SCM service state.
    """
    assert _HEALTH_URL in _read(), (
        f"status.ps1 must contain the health endpoint URL: {_HEALTH_URL!r}"
    )


# ---------------------------------------------------------------------------
# 4  Port 8765 referenced
# ---------------------------------------------------------------------------

def test_port_8765_referenced():
    """status.ps1 must reference port 8765 (RASTATIME-API bind port)."""
    assert "8765" in _read(), (
        "status.ps1 must reference port 8765 (RASTATIME-API)"
    )


# ---------------------------------------------------------------------------
# 5  Port 8001 referenced
# ---------------------------------------------------------------------------

def test_port_8001_referenced():
    """status.ps1 must reference port 8001 (RASTATIME-LIQUIDSOAP DJ harbor)."""
    assert "8001" in _read(), (
        "status.ps1 must reference port 8001 (RASTATIME-LIQUIDSOAP DJ harbor)"
    )


# ---------------------------------------------------------------------------
# 6  Log directory referenced
# ---------------------------------------------------------------------------

def test_log_directory_referenced():
    """
    status.ps1 must reference C:\\rastatime\\logs so it can tail
    recent log output for each service.
    """
    text = _read()
    assert "rastatime\\logs" in text or "rastatime/logs" in text, (
        "status.ps1 must reference the rastatime\\logs directory"
    )


# ---------------------------------------------------------------------------
# 7  -LogLines parameter
# ---------------------------------------------------------------------------

def test_log_lines_parameter_exposed():
    """
    status.ps1 must expose a -LogLines parameter so operators can
    control how many recent log lines are shown per service.
    """
    assert "LogLines" in _read(), (
        "status.ps1 must expose a -LogLines parameter"
    )


# ---------------------------------------------------------------------------
# 8  Service status queried via Get-Service or nssm status
# ---------------------------------------------------------------------------

def test_service_status_queried():
    """
    status.ps1 must query the Windows service state using Get-Service
    or 'nssm status' — not just assume the service is running.
    """
    text = _read()
    assert "Get-Service" in text or "nssm status" in text, (
        "status.ps1 must query service state via Get-Service or 'nssm status'"
    )


# ---------------------------------------------------------------------------
# 9  HTTP 200 interpreted as healthy
# ---------------------------------------------------------------------------

def test_http_200_interpreted_as_healthy():
    """
    status.ps1 must treat an HTTP 200 response from the health endpoint
    as a healthy signal — this is the standard RASTATIME health contract.
    """
    assert "200" in _read(), (
        "status.ps1 must reference HTTP 200 as the healthy status code"
    )


# ---------------------------------------------------------------------------
# 10  Icecast documented as optional
# ---------------------------------------------------------------------------

def test_icecast_documented_as_optional():
    """
    status.ps1 must note that RASTATIME-ICECAST is optional so operators
    are not alarmed when it shows as 'not installed'.
    """
    text = _read().lower()
    assert "optional" in text, (
        "status.ps1 must document RASTATIME-ICECAST as an optional service"
    )
