"""
T20.1 — Default locale tests.

Verify that English is the canonical RASTATIME system locale and that
the PHP fallback guard is in place.

Test inventory
--------------
File-based checks (4, always run — no Django needed):
  1.  ``_internal.py`` defines ``LANGUAGE_CODE = "en-us"``.
  2.  ``_internal.py`` defines ``TIME_ZONE = "UTC"``.
  3.  ``data.sql`` seeds ``cc_pref`` with ``locale = 'en_US'``.
  4.  ``data.sql`` seeds ``cc_pref`` with ``user_locale = 'en_US'`` for admin.

PHP-fallback check (1, always run — no PHP interpreter needed):
  5.  ``Preference.php::GetDefaultLocale`` has the ``empty($locale) ? 'en_US'``
      guard so a missing ``cc_pref`` row still returns English.

Dev/prod settings redundancy checks (2, always run):
  6.  ``dev.py`` does NOT define ``LANGUAGE_CODE`` locally (uses _internal).
  7.  ``prod.py`` does NOT define ``LANGUAGE_CODE`` locally (uses _internal).

Django-gated checks (3):
  8.  ``settings.LANGUAGE_CODE`` equals ``"en-us"``.
  9.  ``settings.USE_I18N`` is ``True``.
 10.  ``settings.USE_TZ`` is ``True`` and ``settings.TIME_ZONE`` equals ``"UTC"``.

(10 tests total)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[3]
_INTERNAL_PY = _REPO / "backend/api/rastatime_api/settings/_internal.py"
_DEV_PY      = _REPO / "backend/api/rastatime_api/settings/dev.py"
_PROD_PY     = _REPO / "backend/api/rastatime_api/settings/prod.py"
_DATA_SQL    = _REPO / "backend/api/rastatime_api/legacy/migrations/sql/data.sql"
_PREF_PHP    = _REPO / "frontend/legacy/application/models/Preference.php"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–2  _internal.py defines locale constants
# ---------------------------------------------------------------------------


def test_internal_defines_language_code():
    """_internal.py must set LANGUAGE_CODE = 'en-us' (canonical source)."""
    src = _read(_INTERNAL_PY)
    assert re.search(r'^LANGUAGE_CODE\s*=\s*"en-us"', src, re.MULTILINE), (
        "_internal.py must define LANGUAGE_CODE = 'en-us'"
    )


def test_internal_defines_time_zone_utc():
    """_internal.py must set TIME_ZONE = 'UTC'."""
    src = _read(_INTERNAL_PY)
    assert re.search(r'^TIME_ZONE\s*=\s*"UTC"', src, re.MULTILINE), (
        "_internal.py must define TIME_ZONE = 'UTC'"
    )


# ---------------------------------------------------------------------------
# 3–4  data.sql seeds locale rows
# ---------------------------------------------------------------------------


def test_data_sql_seeds_default_locale():
    """data.sql must insert locale = 'en_US' into cc_pref."""
    sql = _read(_DATA_SQL)
    assert "'locale', 'en_US'" in sql, (
        "data.sql must seed cc_pref with locale = 'en_US'"
    )


def test_data_sql_seeds_user_locale_for_admin():
    """data.sql must insert user_locale = 'en_US' for the admin user."""
    sql = _read(_DATA_SQL)
    assert "'user_locale', 'en_US'" in sql, (
        "data.sql must seed cc_pref with user_locale = 'en_US' for admin"
    )


# ---------------------------------------------------------------------------
# 5  PHP fallback guard in GetDefaultLocale
# ---------------------------------------------------------------------------


def test_php_get_default_locale_has_en_us_fallback():
    """
    Preference.php GetDefaultLocale() must guard against a missing cc_pref
    row by returning 'en_US' when the DB value is empty/null.
    """
    src = _read(_PREF_PHP)
    # Look for the pattern:  empty($locale) ? 'en_US'
    assert re.search(r"empty\(\$locale\)\s*\?\s*'en_US'", src), (
        "GetDefaultLocale() must have: empty($locale) ? 'en_US' : $locale"
    )


# ---------------------------------------------------------------------------
# 6–7  dev.py and prod.py do NOT re-define LANGUAGE_CODE locally
# ---------------------------------------------------------------------------


def test_dev_py_does_not_define_language_code_locally():
    """
    After T20.1, dev.py must import LANGUAGE_CODE from _internal rather than
    redefine it.  A bare assignment ``LANGUAGE_CODE = ...`` must not exist
    outside the import block.
    """
    src = _read(_DEV_PY)
    # Strip the import block to avoid false positives
    # A bare assignment at start-of-line (not inside a comment/string) is the signal.
    bare_assignments = re.findall(
        r'^LANGUAGE_CODE\s*=\s*(?!.*#\s*noqa)',  # assignment not commented out
        src,
        re.MULTILINE,
    )
    assert bare_assignments == [], (
        "dev.py must not define LANGUAGE_CODE locally; import it from _internal"
    )


def test_prod_py_does_not_define_language_code_locally():
    """prod.py must import LANGUAGE_CODE from _internal, not redefine it."""
    src = _read(_PROD_PY)
    bare_assignments = re.findall(
        r'^LANGUAGE_CODE\s*=\s*(?!.*#\s*noqa)',
        src,
        re.MULTILINE,
    )
    assert bare_assignments == [], (
        "prod.py must not define LANGUAGE_CODE locally; import it from _internal"
    )


# ---------------------------------------------------------------------------
# 8–10  Django-gated: live settings values
# ---------------------------------------------------------------------------

try:
    import django  # noqa: F401
    _DJANGO_AVAILABLE = True
except ImportError:
    _DJANGO_AVAILABLE = False

_django_only = pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="Django not importable in this environment",
)


@_django_only
def test_settings_language_code_is_en_us():
    """settings.LANGUAGE_CODE must equal 'en-us'."""
    import django
    from django.conf import settings

    if not settings.configured:
        django.setup()

    assert settings.LANGUAGE_CODE == "en-us"


@_django_only
def test_settings_use_i18n_is_true():
    """settings.USE_I18N must be True so the i18n machinery is active."""
    import django
    from django.conf import settings

    if not settings.configured:
        django.setup()

    assert settings.USE_I18N is True


@_django_only
def test_settings_use_tz_and_time_zone():
    """settings.USE_TZ must be True and TIME_ZONE must be 'UTC'."""
    import django
    from django.conf import settings

    if not settings.configured:
        django.setup()

    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"
