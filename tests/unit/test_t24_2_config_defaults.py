"""
T24.2 — Config defaults audit.

Verify that Linux-specific filesystem path defaults have been replaced
with Windows-appropriate defaults across Python shared config and PHP
frontend config files.

Files audited (§4 of docs/architecture/LINUX_INVENTORY.md):
  - backend/shared/rastatime_shared/config/_base.py
      DEFAULT_CONFIG_FILEPATH: /etc/libretime/config.yml → C:\\rastatime\\config\\rastatime.conf
  - backend/api/rastatime_api/manage.py
      RASTATIME_CONFIG_FILEPATH default: same substitution
  - backend/shared/rastatime_shared/config/_models.py
      StorageConfig.path default: /srv/libretime → C:\\rastatime\\media
  - frontend/legacy/application/configs/constants.php
      RASTATIME_LOG_DIR fallback: /var/log/libretime → C:/rastatime/logs
      RASTATIME_CONFIG_DIR fallback: /etc/libretime → C:/rastatime/config
  - frontend/legacy/application/configs/conf.php
      storage.path default: /srv/libretime/ → C:/rastatime/media/
  - frontend/legacy/application/configs/airtime-conf.php
      comment: /var/www/html/build/runtime-conf.xml → updated to Windows path

Test inventory (10 tests, always run — no Django needed):
  1.  _base.py uses sys.platform for a platform-conditional config default.
  2.  _base.py references C:\\rastatime\\config as the Windows default path.
  3.  manage.py uses sys.platform for a platform-conditional config default.
  4.  manage.py references C:\\rastatime\\config as the Windows default path.
  5.  _models.py uses sys.platform for a platform-conditional storage default.
  6.  _models.py references C:\\rastatime\\media as the Windows storage default.
  7.  constants.php does not fall back to /var/log/libretime.
  8.  constants.php does not fall back to /etc/libretime.
  9.  conf.php does not default to /srv/libretime as the storage path.
 10.  airtime-conf.php does not reference /var/www/html.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

_CONFIG_BASE  = _REPO / "backend" / "shared" / "rastatime_shared" / "config" / "_base.py"
_MANAGE       = _REPO / "backend" / "api" / "rastatime_api" / "manage.py"
_MODELS       = _REPO / "backend" / "shared" / "rastatime_shared" / "config" / "_models.py"
_CONSTANTS    = _REPO / "frontend" / "legacy" / "application" / "configs" / "constants.php"
_CONF         = _REPO / "frontend" / "legacy" / "application" / "configs" / "conf.php"
_AIRTIME_CONF = _REPO / "frontend" / "legacy" / "application" / "configs" / "airtime-conf.php"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–2  _base.py — DEFAULT_CONFIG_FILEPATH
# ---------------------------------------------------------------------------

def test_config_base_uses_platform_conditional():
    """
    _base.py must use sys.platform to select the platform-appropriate
    DEFAULT_CONFIG_FILEPATH so the Linux default is not blindly applied on Windows.
    """
    assert "sys.platform" in _read(_CONFIG_BASE), (
        "_base.py must use sys.platform for a platform-conditional DEFAULT_CONFIG_FILEPATH"
    )


def test_config_base_windows_path():
    """
    _base.py must reference C:\\rastatime\\config as the Windows branch of
    DEFAULT_CONFIG_FILEPATH, replacing the upstream /etc/libretime/config.yml default.
    """
    # Raw string r"C:\rastatime\config\rastatime.conf" in the source file
    # contains literal backslashes; search for the Windows path substring.
    assert r"C:\rastatime\config" in _read(_CONFIG_BASE), (
        "_base.py must reference C:\\rastatime\\config as the Windows default config path"
    )


# ---------------------------------------------------------------------------
# 3–4  manage.py — RASTATIME_CONFIG_FILEPATH setdefault
# ---------------------------------------------------------------------------

def test_manage_uses_platform_conditional():
    """
    manage.py must use sys.platform so the RASTATIME_CONFIG_FILEPATH default
    is Windows-appropriate when manage.py is invoked directly on Windows.
    """
    assert "sys.platform" in _read(_MANAGE), (
        "manage.py must use sys.platform for a platform-conditional RASTATIME_CONFIG_FILEPATH"
    )


def test_manage_windows_path():
    """
    manage.py must reference C:\\rastatime\\config as the Windows default for
    RASTATIME_CONFIG_FILEPATH, replacing /etc/libretime/config.yml.
    """
    assert r"C:\rastatime\config" in _read(_MANAGE), (
        "manage.py must reference C:\\rastatime\\config as the Windows config path default"
    )


# ---------------------------------------------------------------------------
# 5–6  _models.py — StorageConfig.path default
# ---------------------------------------------------------------------------

def test_models_storage_uses_platform_conditional():
    """
    _models.py must use sys.platform so StorageConfig.path defaults to a
    Windows path rather than /srv/libretime on Windows.
    """
    assert "sys.platform" in _read(_MODELS), (
        "_models.py must use sys.platform for a platform-conditional StorageConfig.path default"
    )


def test_models_storage_windows_path():
    """
    _models.py must reference C:\\rastatime\\media as the Windows storage default,
    replacing /srv/libretime.
    """
    assert r"C:\rastatime\media" in _read(_MODELS), (
        "_models.py must reference C:\\rastatime\\media as the Windows storage default"
    )


# ---------------------------------------------------------------------------
# 7–8  constants.php — log and config directory fallbacks
# ---------------------------------------------------------------------------

def test_constants_no_linux_log_dir():
    """
    constants.php must not fall back to /var/log/libretime.
    The RASTATIME_LOG_DIR fallback must be a Windows path (C:/rastatime/logs).
    """
    assert "/var/log/libretime" not in _read(_CONSTANTS), (
        "constants.php still falls back to /var/log/libretime — must use C:/rastatime/logs"
    )


def test_constants_no_linux_config_dir():
    """
    constants.php must not fall back to /etc/libretime.
    The RASTATIME_CONFIG_DIR fallback must be a Windows path (C:/rastatime/config).
    """
    assert "/etc/libretime" not in _read(_CONSTANTS), (
        "constants.php still falls back to /etc/libretime — must use C:/rastatime/config"
    )


# ---------------------------------------------------------------------------
# 9  conf.php — storage.path default
# ---------------------------------------------------------------------------

def test_conf_no_linux_storage_default():
    """
    conf.php must not default storage.path to /srv/libretime.
    The Symfony Config TreeBuilder default must reference the Windows path.
    """
    assert "/srv/libretime" not in _read(_CONF), (
        "conf.php still defaults storage.path to /srv/libretime — must use C:/rastatime/media"
    )


# ---------------------------------------------------------------------------
# 10  airtime-conf.php — comment
# ---------------------------------------------------------------------------

def test_airtime_conf_no_linux_path_comment():
    """
    airtime-conf.php must not reference /var/www/html.
    The Propel generation comment pointing to a Linux runtime-conf.xml path
    must be updated to remove the Linux filesystem reference.
    """
    assert "/var/www/html" not in _read(_AIRTIME_CONF), (
        "airtime-conf.php still references /var/www/html — Linux path comment must be updated"
    )
