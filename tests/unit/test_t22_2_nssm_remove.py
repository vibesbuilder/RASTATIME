"""
T22.2 — NSSM remove script tests.

Verify that infra/nssm/remove-*.ps1 exists for all four RASTATIME
services and that each script meets the required safety and correctness
criteria: correct service name, graceful handling of an already-absent
service (idempotency), use of the 'nssm remove' command, optional log
purge capability, and proper documentation of the optional Icecast service.

Test inventory (10 tests, always run — no Django needed):
  1.  remove-api.ps1 exists.
  2.  remove-worker.ps1 exists.
  3.  remove-playout.ps1 exists.
  4.  remove-icecast.ps1 exists.
  5.  All scripts declare the correct NSSM service name.
  6.  All scripts contain the 'nssm remove' command.
  7.  All scripts handle a non-existent service gracefully (idempotent).
  8.  All scripts reference the log directory for optional cleanup.
  9.  remove-icecast.ps1 documents its optional nature.
 10.  All scripts expose a -PurgeLogs switch parameter.
"""

from __future__ import annotations

from pathlib import Path

_REPO     = Path(__file__).resolve().parents[2]
_NSSM_DIR = _REPO / "infra" / "nssm"

_SCRIPT_API     = _NSSM_DIR / "remove-api.ps1"
_SCRIPT_WORKER  = _NSSM_DIR / "remove-worker.ps1"
_SCRIPT_PLAYOUT = _NSSM_DIR / "remove-playout.ps1"
_SCRIPT_ICECAST = _NSSM_DIR / "remove-icecast.ps1"

_ALL_SCRIPTS = [_SCRIPT_API, _SCRIPT_WORKER, _SCRIPT_PLAYOUT, _SCRIPT_ICECAST]

_SERVICE_NAMES = {
    _SCRIPT_API:     "RASTATIME-API",
    _SCRIPT_WORKER:  "RASTATIME-WORKER",
    _SCRIPT_PLAYOUT: "RASTATIME-PLAYOUT",
    _SCRIPT_ICECAST: "RASTATIME-ICECAST",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–4  File existence
# ---------------------------------------------------------------------------

def test_remove_api_exists():
    """infra/nssm/remove-api.ps1 must exist."""
    assert _SCRIPT_API.exists(), f"Missing: {_SCRIPT_API}"


def test_remove_worker_exists():
    """infra/nssm/remove-worker.ps1 must exist."""
    assert _SCRIPT_WORKER.exists(), f"Missing: {_SCRIPT_WORKER}"


def test_remove_playout_exists():
    """infra/nssm/remove-playout.ps1 must exist."""
    assert _SCRIPT_PLAYOUT.exists(), f"Missing: {_SCRIPT_PLAYOUT}"


def test_remove_icecast_exists():
    """infra/nssm/remove-icecast.ps1 must exist."""
    assert _SCRIPT_ICECAST.exists(), f"Missing: {_SCRIPT_ICECAST}"


# ---------------------------------------------------------------------------
# 5  Correct NSSM service names
# ---------------------------------------------------------------------------

def test_all_scripts_declare_correct_service_names():
    """Each remove script must declare the NSSM service name it targets."""
    wrong = {}
    for script, expected_name in _SERVICE_NAMES.items():
        if expected_name not in _read(script):
            wrong[script.name] = expected_name
    assert not wrong, (
        f"Scripts missing their expected NSSM service name: {wrong}"
    )


# ---------------------------------------------------------------------------
# 6  'nssm remove' command present
# ---------------------------------------------------------------------------

def test_all_scripts_contain_nssm_remove_command():
    """
    Each script must invoke 'nssm remove' to unregister the Windows service.
    'nssm stop' alone is not sufficient — the service must be fully removed.
    """
    missing = [s.name for s in _ALL_SCRIPTS if "nssm remove" not in _read(s)]
    assert not missing, (
        f"Scripts missing 'nssm remove' command: {missing}"
    )


# ---------------------------------------------------------------------------
# 7  Idempotent — graceful when service does not exist
# ---------------------------------------------------------------------------

def test_all_scripts_handle_absent_service_gracefully():
    """
    If the service is not registered, the script must not crash.
    Check for Get-Service ... -ErrorAction SilentlyContinue (or equivalent)
    so a second run or a partial-install state does not produce an error.
    """
    missing = [
        s.name for s in _ALL_SCRIPTS
        if "SilentlyContinue" not in _read(s)
    ]
    assert not missing, (
        f"Scripts lack ErrorAction SilentlyContinue (not idempotent): {missing}"
    )


# ---------------------------------------------------------------------------
# 8  Log directory referenced for cleanup
# ---------------------------------------------------------------------------

def test_all_scripts_reference_log_directory():
    """
    All remove scripts must mention the log directory so operators know
    logs are not automatically deleted and can use -PurgeLogs if desired.
    """
    missing = []
    for s in _ALL_SCRIPTS:
        text = _read(s)
        if "rastatime\\logs" not in text and "rastatime/logs" not in text:
            missing.append(s.name)
    assert not missing, (
        f"Scripts do not reference the log directory: {missing}"
    )


# ---------------------------------------------------------------------------
# 9  Icecast optional notice
# ---------------------------------------------------------------------------

def test_remove_icecast_documents_optional_nature():
    """
    remove-icecast.ps1 must mention that Icecast is an optional service
    so operators are not alarmed when removing it.
    """
    text = _read(_SCRIPT_ICECAST).lower()
    assert "optional" in text, (
        "remove-icecast.ps1 must document that RASTATIME-ICECAST is optional"
    )


# ---------------------------------------------------------------------------
# 10  -PurgeLogs switch parameter
# ---------------------------------------------------------------------------

def test_all_scripts_expose_purge_logs_switch():
    """
    All remove scripts must expose a -PurgeLogs switch so operators can
    optionally delete log files as part of a clean uninstall.
    """
    missing = [s.name for s in _ALL_SCRIPTS if "PurgeLogs" not in _read(s)]
    assert not missing, (
        f"Scripts missing -PurgeLogs switch parameter: {missing}"
    )
