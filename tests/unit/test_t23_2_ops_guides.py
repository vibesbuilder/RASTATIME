"""
T23.2 — Upgrade, backup, and crash-recovery guide tests.

Verify that all three operator guide documents exist and contain the
required content for each operational scenario.

Test inventory (10 tests, always run — no Django needed):
  1.  UPGRADE.md exists.
  2.  BACKUP.md exists.
  3.  CRASH_RECOVERY.md exists.
  4.  UPGRADE.md documents stopping services before the upgrade.
  5.  UPGRADE.md references database migration (manage.py migrate).
  6.  BACKUP.md documents pg_dump for database backup.
  7.  BACKUP.md references rastatime.conf (config file backup).
  8.  CRASH_RECOVERY.md references status.ps1 for initial assessment.
  9.  CRASH_RECOVERY.md references RESTART_ORDER.md.
 10.  All three documents reference C:\\rastatime as the install directory.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OPS  = _REPO / "docs" / "operator"

_UPGRADE   = _OPS / "UPGRADE.md"
_BACKUP    = _OPS / "BACKUP.md"
_RECOVERY  = _OPS / "CRASH_RECOVERY.md"

_ALL_THREE = [_UPGRADE, _BACKUP, _RECOVERY]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–3  File existence
# ---------------------------------------------------------------------------

def test_upgrade_guide_exists():
    """docs/operator/UPGRADE.md must exist."""
    assert _UPGRADE.exists(), f"Missing: {_UPGRADE}"


def test_backup_guide_exists():
    """docs/operator/BACKUP.md must exist."""
    assert _BACKUP.exists(), f"Missing: {_BACKUP}"


def test_crash_recovery_guide_exists():
    """docs/operator/CRASH_RECOVERY.md must exist."""
    assert _RECOVERY.exists(), f"Missing: {_RECOVERY}"


# ---------------------------------------------------------------------------
# 4  UPGRADE.md — services stopped before upgrade
# ---------------------------------------------------------------------------

def test_upgrade_documents_stopping_services():
    """
    UPGRADE.md must document stopping services before the upgrade so
    no in-flight requests are lost and file locks do not block the update.
    """
    doc = _read(_UPGRADE).lower()
    assert "stop" in doc and ("service" in doc or "nssm" in doc), (
        "UPGRADE.md must document stopping services before upgrading"
    )


# ---------------------------------------------------------------------------
# 5  UPGRADE.md — database migration step
# ---------------------------------------------------------------------------

def test_upgrade_references_database_migration():
    """
    UPGRADE.md must reference 'manage.py migrate' so operators know
    to apply schema changes as part of every upgrade.
    """
    assert "migrate" in _read(_UPGRADE), (
        "UPGRADE.md must reference 'manage.py migrate' (or 'migrate')"
    )


# ---------------------------------------------------------------------------
# 6  BACKUP.md — pg_dump for database backup
# ---------------------------------------------------------------------------

def test_backup_documents_pg_dump():
    """
    BACKUP.md must document pg_dump as the PostgreSQL backup tool so
    operators can produce consistent, restorable database snapshots.
    """
    assert "pg_dump" in _read(_BACKUP), (
        "BACKUP.md must document pg_dump for database backup"
    )


# ---------------------------------------------------------------------------
# 7  BACKUP.md — rastatime.conf backup
# ---------------------------------------------------------------------------

def test_backup_references_config_file():
    """
    BACKUP.md must include rastatime.conf in the backup scope so the
    entire RASTATIME configuration is preserved alongside the database.
    """
    assert "rastatime.conf" in _read(_BACKUP), (
        "BACKUP.md must reference rastatime.conf as a backup target"
    )


# ---------------------------------------------------------------------------
# 8  CRASH_RECOVERY.md — status.ps1 for assessment
# ---------------------------------------------------------------------------

def test_crash_recovery_references_status_script():
    """
    CRASH_RECOVERY.md must reference status.ps1 (T22.3) as the first
    diagnostic step after a crash or unexpected restart.
    """
    assert "status.ps1" in _read(_RECOVERY), (
        "CRASH_RECOVERY.md must reference status.ps1 for initial assessment"
    )


# ---------------------------------------------------------------------------
# 9  CRASH_RECOVERY.md — RESTART_ORDER.md
# ---------------------------------------------------------------------------

def test_crash_recovery_references_restart_order():
    """
    CRASH_RECOVERY.md must reference RESTART_ORDER.md (T22.4) so
    operators know where to find per-service recovery procedures.
    """
    assert "RESTART_ORDER" in _read(_RECOVERY), (
        "CRASH_RECOVERY.md must reference RESTART_ORDER.md"
    )


# ---------------------------------------------------------------------------
# 10  All three documents reference C:\rastatime
# ---------------------------------------------------------------------------

def test_all_guides_reference_install_directory():
    """
    All three operator guides must reference C:\\rastatime so paths in
    commands are unambiguous and match the standard install layout.
    """
    missing = []
    for doc in _ALL_THREE:
        text = _read(doc)
        if r"C:\rastatime" not in text and "C:\\rastatime" not in text:
            missing.append(doc.name)
    assert not missing, (
        f"Guides missing C:\\rastatime install directory reference: {missing}"
    )
