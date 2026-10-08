"""
T-GH-3 - Replace systemctl with Windows SC (Windows-only).

RASTATIME runs exclusively on Windows. All Linux/systemd service checks are
removed. The PHP UI queries NSSM service status directly — no conditional
branching, no dead code.  The original `sc query` call became a batched
PowerShell `Get-Service` on 2026-05-16 (one process start for all
services instead of one per service; see check.php) — test updated
2026-10-02.

Test inventory (10 tests):
  1.  check.php has no 'systemctl' calls anywhere.
  2.  check.php has no 'with_systemd' function.
  3.  check.php defines check_windows_service() backed by 'Get-Service'.
  4.  check.php's checkExternalServices() returns RASTATIME-PLAYOUT unconditionally.
  5.  check.php's checkExternalServices() returns RASTATIME-WORKER unconditionally.
  6.  check.php's checkExternalServices() returns RASTATIME-API unconditionally.
  7.  config-check.php has no 'systemctl' references.
  8.  config-check.php has no '$systemd' variable.
  9.  index.phtml has no 'systemctl' references.
  10. index.phtml has no '$systemd' variable.
"""

from __future__ import annotations

from pathlib import Path

_REPO    = Path(__file__).resolve().parents[2]
_LEGACY  = _REPO / "frontend" / "legacy" / "application"
_CHECK   = _LEGACY / "check.php"
_CFG_CHK = _LEGACY / "configs" / "config-check.php"
_STATUS  = _LEGACY / "views" / "scripts" / "systemstatus" / "index.phtml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1-2  check.php — systemd gone
# ---------------------------------------------------------------------------

def test_check_php_has_no_systemctl():
    """check.php must not call systemctl anywhere."""
    assert "systemctl" not in _text(_CHECK), (
        "check.php still contains systemctl calls"
    )


def test_check_php_has_no_with_systemd():
    """check.php must not define or call with_systemd()."""
    assert "with_systemd" not in _text(_CHECK), (
        "check.php still contains with_systemd()"
    )


# ---------------------------------------------------------------------------
# 3-6  check.php — the Windows service manager is the only code path
# ---------------------------------------------------------------------------

def test_check_php_defines_check_windows_service_with_get_service():
    """check.php must define check_windows_service() backed by PowerShell
    'Get-Service' (replaced 'sc query' on 2026-05-16: one batched call
    pre-warms the status of every RASTATIME service)."""
    text = _text(_CHECK)
    assert "function check_windows_service" in text, (
        "check.php missing check_windows_service() function"
    )
    assert "Get-Service" in text, (
        "check_windows_service() does not use PowerShell 'Get-Service'"
    )
    assert "sc query" not in text, (
        "check.php must not fall back to 'sc query' (replaced by Get-Service)"
    )


def test_check_php_checkexternalservices_has_rastatime_playout():
    """checkExternalServices() must always check RASTATIME-PLAYOUT."""
    assert "RASTATIME-PLAYOUT" in _text(_CHECK), (
        "check.php does not reference RASTATIME-PLAYOUT"
    )


def test_check_php_checkexternalservices_has_rastatime_worker():
    """checkExternalServices() must always check RASTATIME-WORKER."""
    assert "RASTATIME-WORKER" in _text(_CHECK), (
        "check.php does not reference RASTATIME-WORKER"
    )


def test_check_php_checkexternalservices_has_rastatime_api():
    """checkExternalServices() must always check RASTATIME-API."""
    assert "RASTATIME-API" in _text(_CHECK), (
        "check.php does not reference RASTATIME-API"
    )


# ---------------------------------------------------------------------------
# 7-8  config-check.php — systemd gone
# ---------------------------------------------------------------------------

def test_config_check_has_no_systemctl():
    """config-check.php must not contain any systemctl references."""
    assert "systemctl" not in _text(_CFG_CHK), (
        "config-check.php still contains systemctl references"
    )


def test_config_check_has_no_systemd_variable():
    """config-check.php must not declare or use the $systemd variable."""
    assert "$systemd" not in _text(_CFG_CHK), (
        "config-check.php still uses the $systemd variable"
    )


# ---------------------------------------------------------------------------
# 9-10  index.phtml — systemd gone
# ---------------------------------------------------------------------------

def test_index_phtml_has_no_systemctl():
    """index.phtml must not contain any systemctl references."""
    assert "systemctl" not in _text(_STATUS), (
        "index.phtml still contains systemctl references"
    )


def test_index_phtml_has_no_systemd_variable():
    """index.phtml must not declare or use the $systemd variable."""
    assert "$systemd" not in _text(_STATUS), (
        "index.phtml still uses the $systemd variable"
    )
