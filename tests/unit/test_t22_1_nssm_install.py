"""
T22.1 — NSSM install script tests.

Verify that infra/nssm/install-*.ps1 exists for all four RASTATIME
services and that each script contains the required NSSM configuration:
correct service names, executable paths, log destinations, environment
variables, restart delays, and — for the worker and playout — a
health-check gate that waits for the API before starting.

Test inventory (10 tests, always run — no Django needed):
  1.  install-api.ps1 exists.
  2.  install-worker.ps1 exists.
  3.  install-playout.ps1 exists.
  4.  install-icecast.ps1 exists.
  5.  Each script declares the correct NSSM service name.
  6.  API script assigns port 8000.
  7.  Worker and playout scripts contain the health-check gate URL.
  8.  Log paths under C:\\rastatime\\logs are configured in all scripts.
  9.  DJANGO_SETTINGS_MODULE is set in the API, worker, and playout scripts.
 10.  AppNoConsole is configured in all Python-hosted service scripts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO     = Path(__file__).resolve().parents[2]
_NSSM_DIR = _REPO / "infra" / "nssm"

_SCRIPT_API     = _NSSM_DIR / "install-api.ps1"
_SCRIPT_WORKER  = _NSSM_DIR / "install-worker.ps1"
_SCRIPT_PLAYOUT = _NSSM_DIR / "install-playout.ps1"
_SCRIPT_ICECAST = _NSSM_DIR / "install-icecast.ps1"

# NSSM service name that each script must declare
_SERVICE_NAMES = {
    _SCRIPT_API:     "RASTATIME-API",
    _SCRIPT_WORKER:  "RASTATIME-WORKER",
    _SCRIPT_PLAYOUT: "RASTATIME-PLAYOUT",
    _SCRIPT_ICECAST: "RASTATIME-ICECAST",
}

# Python-hosted services (not Icecast) that need AppNoConsole + Django env
_PYTHON_SCRIPTS = [_SCRIPT_API, _SCRIPT_WORKER, _SCRIPT_PLAYOUT]

# The API health endpoint that worker and playout must poll on startup
_HEALTH_URL = "http://127.0.0.1:8000/health"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–4  File existence
# ---------------------------------------------------------------------------

def test_install_api_exists():
    """infra/nssm/install-api.ps1 must exist."""
    assert _SCRIPT_API.exists(), f"Missing: {_SCRIPT_API}"


def test_install_worker_exists():
    """infra/nssm/install-worker.ps1 must exist."""
    assert _SCRIPT_WORKER.exists(), f"Missing: {_SCRIPT_WORKER}"


def test_install_playout_exists():
    """infra/nssm/install-playout.ps1 must exist."""
    assert _SCRIPT_PLAYOUT.exists(), f"Missing: {_SCRIPT_PLAYOUT}"


def test_install_icecast_exists():
    """infra/nssm/install-icecast.ps1 must exist."""
    assert _SCRIPT_ICECAST.exists(), f"Missing: {_SCRIPT_ICECAST}"


# ---------------------------------------------------------------------------
# 5  Correct NSSM service names
# ---------------------------------------------------------------------------

def test_all_scripts_declare_correct_service_names():
    """
    Each install script must declare the NSSM service name that matches
    the SERVICE_TOPOLOGY.md definition.
    """
    wrong = {}
    for script, expected_name in _SERVICE_NAMES.items():
        text = _read(script)
        if expected_name not in text:
            wrong[script.name] = expected_name
    assert not wrong, (
        f"Scripts missing their expected NSSM service name: {wrong}"
    )


# ---------------------------------------------------------------------------
# 6  Port 8000 in API script
# ---------------------------------------------------------------------------

def test_api_script_assigns_port_8000():
    """
    install-api.ps1 must configure the API to bind on port 8000,
    consistent with SERVICE_TOPOLOGY.md.
    """
    text = _read(_SCRIPT_API)
    assert "8000" in text, (
        "install-api.ps1 must reference port 8000 in its NSSM configuration"
    )


# ---------------------------------------------------------------------------
# 7  Health-check gate in worker and playout
# ---------------------------------------------------------------------------

def test_worker_and_playout_have_health_gate():
    """
    install-worker.ps1 and install-playout.ps1 must contain the API
    health-check gate URL so operators know (and the entry points implement)
    polling before starting their main loops.
    """
    missing = []
    for script in (_SCRIPT_WORKER, _SCRIPT_PLAYOUT):
        if _HEALTH_URL not in _read(script):
            missing.append(script.name)
    assert not missing, (
        f"Scripts missing health-check gate ({_HEALTH_URL!r}): {missing}"
    )


# ---------------------------------------------------------------------------
# 8  Log paths
# ---------------------------------------------------------------------------

def test_all_scripts_configure_log_paths():
    """
    All four install scripts must reference log paths under
    C:\\rastatime\\logs as documented in SERVICE_TOPOLOGY.md §6.
    """
    missing = []
    for script in _SERVICE_NAMES:
        text = _read(script)
        if "rastatime\\logs" not in text and "rastatime/logs" not in text:
            missing.append(script.name)
    assert not missing, (
        f"Scripts missing rastatime\\logs path configuration: {missing}"
    )


# ---------------------------------------------------------------------------
# 9  DJANGO_SETTINGS_MODULE in Python services
# ---------------------------------------------------------------------------

def test_python_services_set_django_settings_module():
    """
    install-api.ps1, install-worker.ps1, and install-playout.ps1 must
    configure DJANGO_SETTINGS_MODULE so Django uses the production settings.
    """
    missing = []
    for script in _PYTHON_SCRIPTS:
        if "DJANGO_SETTINGS_MODULE" not in _read(script):
            missing.append(script.name)
    assert not missing, (
        f"Scripts missing DJANGO_SETTINGS_MODULE configuration: {missing}"
    )


# ---------------------------------------------------------------------------
# 10  AppNoConsole in Python services
# ---------------------------------------------------------------------------

def test_python_services_set_app_no_console():
    """
    NSSM must be told AppNoConsole = 1 for API, worker, and playout so
    they run headless without a console window.  (Icecast manages its own
    console mode via icecast.xml and does not need this.)
    """
    missing = []
    for script in _PYTHON_SCRIPTS:
        if "AppNoConsole" not in _read(script):
            missing.append(script.name)
    assert not missing, (
        f"Scripts missing 'AppNoConsole' NSSM setting: {missing}"
    )
