"""
T24.1 — Delete dead Linux code.

Verify that Linux-only files have been removed and Linux-specific code
blocks have been deleted from the Windows codebase.

Dead-code categories addressed:
  - Shell scripts (.sh) — not executable on Windows
  - gunicorn.py / uvicorn worker — replaced by Waitress (T17.1)
  - chmod / chown / chgrp calls in PHP test helper
  - Debian-package detection in Preference.php

Test inventory (10 tests, always run — no Django needed):
  1.  gunicorn.py (dead Gunicorn/UvicornWorker config) does not exist.
  2.  test-hook-script.sh does not exist.
  3.  generate.sh exists again (2026-11-01: the analyzer fixture generator,
      run by the Makefile and the CI).
  4.  runtests.sh does not exist.
  5.  ftp-upload-hook.sh does not exist.
  6.  AirtimeInstall.php does not call chown().
  7.  AirtimeInstall.php does not call chgrp().
  8.  Preference.php does not reference /var/lib/dpkg.
  9.  Preference.php does not reference debian_install.
 10.  Preference.php does not reference airtime-easy-setup.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Deleted files
# ---------------------------------------------------------------------------

_GUNICORN        = _REPO / "backend" / "api" / "rastatime_api" / "gunicorn.py"
_TEST_HOOK       = _REPO / "backend" / "analyzer" / "tools" / "test-hook-script.sh"
_GENERATE        = _REPO / "backend" / "analyzer" / "tests" / "fixtures" / "generate.sh"
_RUNTESTS        = _REPO / "frontend" / "legacy" / "tests" / "runtests.sh"
_FTP_HOOK        = _REPO / "backend" / "analyzer" / "tools" / "ftp-upload-hook.sh"

# ---------------------------------------------------------------------------
# Edited files
# ---------------------------------------------------------------------------

_AIRTIME_INSTALL = (
    _REPO / "frontend" / "legacy" / "tests" / "application"
    / "helpers" / "AirtimeInstall.php"
)
_PREFERENCE      = _REPO / "frontend" / "legacy" / "application" / "models" / "Preference.php"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 1–5  Deleted files must not exist
# ---------------------------------------------------------------------------

def test_gunicorn_py_deleted():
    """backend/api/rastatime_api/gunicorn.py must be deleted (replaced by Waitress)."""
    assert not _GUNICORN.exists(), (
        f"{_GUNICORN.name} still exists — dead Gunicorn/UvicornWorker config must be removed"
    )


def test_test_hook_script_sh_deleted():
    """backend/analyzer/tools/test-hook-script.sh must be deleted."""
    assert not _TEST_HOOK.exists(), (
        "test-hook-script.sh still exists — bash-only script must be removed"
    )


def test_generate_sh_reinstated():
    """backend/analyzer/tests/fixtures/generate.sh is back on purpose.

    RASTATIME 2026-11-01: the analyzer tests need the 59 derived audio
    fixtures (git-ignored); the script derives them with ffmpeg and runs
    in the Windows runner's bash as well as in Git Bash locally.  The
    Makefile's `fixtures` target points at it.
    """
    assert _GENERATE.exists(), "generate.sh missing - the analyzer fixtures cannot be derived"
    makefile = (_REPO / "backend" / "analyzer" / "Makefile").read_text(encoding="utf-8")
    assert "tests/fixtures/generate.sh" in makefile


def test_runtests_sh_deleted():
    """frontend/legacy/tests/runtests.sh must be deleted."""
    assert not _RUNTESTS.exists(), (
        "runtests.sh still exists — bash/rabbitmqctl test runner must be removed"
    )


def test_ftp_upload_hook_sh_deleted():
    """backend/analyzer/tools/ftp-upload-hook.sh must be deleted."""
    assert not _FTP_HOOK.exists(), (
        "ftp-upload-hook.sh still exists — Linux-only bash upload hook must be removed"
    )


# ---------------------------------------------------------------------------
# 6–7  AirtimeInstall.php — chmod / chown / chgrp removed
# ---------------------------------------------------------------------------

def test_airtime_install_no_chown():
    """
    AirtimeInstall.php must not call chown().
    The chown() call in CreateZendPhpLogFile() is Linux-only and has no
    meaning on Windows; it must be removed.
    """
    text = _read(_AIRTIME_INSTALL)
    assert "chown(" not in text, (
        "AirtimeInstall.php still contains chown() — Linux-only call must be removed"
    )


def test_airtime_install_no_chgrp():
    """
    AirtimeInstall.php must not call chgrp().
    The chgrp() call in CreateZendPhpLogFile() is Linux-only and has no
    meaning on Windows; it must be removed.
    """
    text = _read(_AIRTIME_INSTALL)
    assert "chgrp(" not in text, (
        "AirtimeInstall.php still contains chgrp() — Linux-only call must be removed"
    )


# ---------------------------------------------------------------------------
# 8–10  Preference.php — Debian detection block removed
# ---------------------------------------------------------------------------

def test_preference_no_dpkg_path():
    """
    Preference.php must not reference /var/lib/dpkg.
    The GetInstallMethod() Debian detection block is Linux-only dead code.
    """
    text = _read(_PREFERENCE)
    assert "/var/lib/dpkg" not in text, (
        "Preference.php still references /var/lib/dpkg — Debian detection must be removed"
    )


def test_preference_no_debian_install_string():
    """
    Preference.php must not contain the string 'debian_install'.
    This string exists only in the dead GetInstallMethod() Debian detection block.
    """
    text = _read(_PREFERENCE)
    assert "debian_install" not in text, (
        "Preference.php still contains 'debian_install' — Debian detection must be removed"
    )


def test_preference_no_easy_setup_path():
    """
    Preference.php must not reference airtime-easy-setup.
    The /usr/bin/airtime-easy-setup path check is Linux/Debian-specific dead code.
    """
    text = _read(_PREFERENCE)
    assert "airtime-easy-setup" not in text, (
        "Preference.php still references airtime-easy-setup — Debian detection must be removed"
    )
