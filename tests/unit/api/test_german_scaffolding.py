"""
T20.2 — German translation scaffolding tests.

Verify that:
  * frontend/locales/en/common.json and de/common.json exist and are valid JSON.
  * de/common.json has exactly the same top-level keys and sub-keys as en/common.json.
  * Every leaf value in de/common.json is non-empty (no accidental empty strings).
  * backend/api/locale/de/LC_MESSAGES/django.po exists and has the required headers.
  * django.mo exists and is readable by Python's gettext module.
  * _internal.py defines LOCALE_PATHS.
  * RASTATIME-specific translations are present in the .mo (smoke-check).

Test inventory
--------------
JSON locale files (4, always run):
  1.  en/common.json is valid JSON with expected top-level sections.
  2.  de/common.json is valid JSON with expected top-level sections.
  3.  de/common.json key structure matches en/common.json exactly.
  4.  No leaf value in de/common.json is an empty string.

Django .po / .mo files (4, always run — no Django needed):
  5.  django.po exists and contains required PO headers (Language, Content-Type).
  6.  django.mo exists (compiled from django.po).
  7.  django.mo is parseable by Python's gettext module.
  8.  Key RASTATIME model strings are translated in django.mo.

Settings wire-up (1, always run):
  9.  _internal.py defines LOCALE_PATHS pointing at backend/api/locale.

Django-gated (1):
 10.  settings.LOCALE_PATHS contains the expected path.

(10 tests total)
"""

from __future__ import annotations

import gettext
import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO           = Path(__file__).resolve().parents[3]
_LOCALES        = _REPO / "frontend" / "locales"
_EN_JSON        = _LOCALES / "en" / "common.json"
_DE_JSON        = _LOCALES / "de" / "common.json"
_DJANGO_PO      = _REPO / "backend" / "api" / "locale" / "de" / "LC_MESSAGES" / "django.po"
_DJANGO_MO      = _REPO / "backend" / "api" / "locale" / "de" / "LC_MESSAGES" / "django.mo"
_INTERNAL_PY    = _REPO / "backend" / "api" / "libretime_api" / "settings" / "_internal.py"

_EXPECTED_SECTIONS = {"nav", "status", "lineIn", "soundcard", "playbackHistory", "common"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _leaf_values(obj, prefix="") -> dict[str, str]:
    """Recursively collect all leaf (non-dict) values with dotted key paths."""
    result: dict[str, str] = {}
    for k, v in obj.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_leaf_values(v, path))
        else:
            result[path] = v
    return result


# ---------------------------------------------------------------------------
# 1–4  JSON locale files
# ---------------------------------------------------------------------------


def test_en_common_json_valid_and_has_expected_sections():
    """en/common.json must be valid JSON with all required top-level sections."""
    data = json.loads(_EN_JSON.read_text(encoding="utf-8"))
    missing = _EXPECTED_SECTIONS - set(data.keys())
    assert not missing, f"en/common.json missing sections: {missing}"


def test_de_common_json_valid_and_has_expected_sections():
    """de/common.json must be valid JSON with all required top-level sections."""
    data = json.loads(_DE_JSON.read_text(encoding="utf-8"))
    missing = _EXPECTED_SECTIONS - set(data.keys())
    assert not missing, f"de/common.json missing sections: {missing}"


def test_de_common_json_key_structure_matches_en():
    """
    de/common.json must have exactly the same nested key structure as en/common.json.
    Missing or extra keys in DE indicate an incomplete or stale translation.
    """
    en = json.loads(_EN_JSON.read_text(encoding="utf-8"))
    de = json.loads(_DE_JSON.read_text(encoding="utf-8"))

    en_keys = set(_leaf_values(en).keys())
    de_keys = set(_leaf_values(de).keys())

    missing_in_de = en_keys - de_keys
    extra_in_de   = de_keys - en_keys

    assert not missing_in_de, f"de/common.json is missing keys: {sorted(missing_in_de)}"
    assert not extra_in_de,   f"de/common.json has unexpected extra keys: {sorted(extra_in_de)}"


def test_de_common_json_no_empty_leaf_values():
    """Every leaf value in de/common.json must be a non-empty string."""
    de = json.loads(_DE_JSON.read_text(encoding="utf-8"))
    empty_keys = [k for k, v in _leaf_values(de).items() if not v]
    assert not empty_keys, f"de/common.json has empty values for keys: {empty_keys}"


# ---------------------------------------------------------------------------
# 5–8  Django .po / .mo files
# ---------------------------------------------------------------------------


def test_django_po_exists_and_has_required_headers():
    """
    backend/api/locale/de/LC_MESSAGES/django.po must exist and contain the
    mandatory PO metadata headers.
    """
    po_text = _DJANGO_PO.read_text(encoding="utf-8")
    assert "Language: de" in po_text, "django.po must declare Language: de"
    assert "Content-Type: text/plain; charset=UTF-8" in po_text, (
        "django.po must declare UTF-8 Content-Type"
    )
    assert "Plural-Forms:" in po_text, "django.po must declare Plural-Forms"


def test_django_mo_exists():
    """
    backend/api/locale/de/LC_MESSAGES/django.mo must exist.

    Run  python scripts/compile_messages.py  to compile it from the .po source.
    """
    assert _DJANGO_MO.exists(), (
        f"{_DJANGO_MO} not found.  Run: python scripts/compile_messages.py"
    )


def test_django_mo_is_parseable_by_gettext():
    """django.mo must be parseable by Python's built-in gettext module."""
    with _DJANGO_MO.open("rb") as fh:
        cat = gettext.GNUTranslations(fh)
    # A valid catalogue object will at least return its own meta-string.
    assert cat is not None


def test_django_mo_rastatime_strings_translated():
    """
    Key RASTATIME-specific strings must be present and translated in django.mo.
    Checks a representative sample — not exhaustive.
    """
    with _DJANGO_MO.open("rb") as fh:
        cat = gettext.GNUTranslations(fh)

    checks = {
        "Soundcard Settings": "Soundkarteneinstellungen",
        "Line-In Source":     "Line-In-Quelle",
        "Line-In Sources":    "Line-In-Quellen",
        "Playback Event":     "Wiedergabeereignis",
        "Playback Events":    "Wiedergabeereignisse",
        "Audio file":         "Audiodatei",
        "Web stream":         "Webstream",
    }
    failures = {}
    for msgid, expected in checks.items():
        got = cat.gettext(msgid)
        if got != expected:
            failures[msgid] = f"expected {expected!r}, got {got!r}"

    assert not failures, f"Translation mismatches: {failures}"


# ---------------------------------------------------------------------------
# 9  Settings wire-up
# ---------------------------------------------------------------------------


def test_internal_py_defines_locale_paths():
    """
    _internal.py must define LOCALE_PATHS (pointing at backend/api/locale/).

    A bare ``LOCALE_PATHS`` assignment at the start of a line is the signal.
    """
    src = _INTERNAL_PY.read_text(encoding="utf-8")
    assert re.search(r"^LOCALE_PATHS\s*=", src, re.MULTILINE), (
        "_internal.py must define LOCALE_PATHS"
    )
    # Also verify the locale directory name appears in the value
    assert '"locale"' in src or "'locale'" in src or '/ "locale"' in src or "/ 'locale'" in src or '"locale"' in src, (
        "_internal.py LOCALE_PATHS must reference the 'locale' directory"
    )


# ---------------------------------------------------------------------------
# 10  Django-gated
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
def test_settings_locale_paths_contains_backend_locale():
    """settings.LOCALE_PATHS must include backend/api/locale/."""
    import django
    from django.conf import settings

    if not settings.configured:
        django.setup()

    locale_strs = [str(p) for p in settings.LOCALE_PATHS]
    assert any("locale" in p for p in locale_strs), (
        f"settings.LOCALE_PATHS {locale_strs!r} must contain a path with 'locale'"
    )
