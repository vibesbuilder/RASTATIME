"""
T20.3 — Line-In and Soundcard menu entries with i18n tests.

de_DE is the canonical German locale for RASTATIME (ADR-004).
de_AT is an existing LibreTime community locale; RASTATIME does not
assert its coverage in the test suite.

Verify that:
  * navigation.php contains both Soundcard and Line-In menu entries.
  * de_DE .po file translates nav labels and all page/JS strings.
  * soundcard-setting.phtml emits an AIRTIME.i18n script block.
  * linein/index.phtml emits an AIRTIME.linein.i18n script block.
  * ACL entry for 'linein' resource exists.
  * LineinController.php exists with indexAction.
  * PreferenceController.php contains soundcardSettingAction.

Test inventory
--------------
Navigation (2, always run):
  1.  navigation.php has _('Soundcard') under Settings.
  2.  navigation.php has _('Line-In') under Settings.

de_DE .po translations — nav labels (2, always run):
  3.  de_DE translates 'Soundcard' → 'Soundkarte'.
  4.  de_DE translates 'Line-In' → 'Line-In'.

de_DE .po translations — page + JS strings (1, always run):
  5.  de_DE has all RASTATIME page and JS i18n strings.

JS i18n script blocks (2, always run):
  6.  soundcard-setting.phtml contains AIRTIME.i18n inline script override.
  7.  linein/index.phtml contains AIRTIME.linein.i18n inline script override.

Controller / ACL wiring (3, always run):
  8.  LineinController.php exists with indexAction.
  9.  PreferenceController.php contains soundcardSettingAction.
 10.  ACL.php grants 'linein' resource access.

(10 tests total)
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO       = Path(__file__).resolve().parents[2]
_LEGACY     = _REPO / "frontend" / "legacy"
_NAV        = _LEGACY / "application" / "configs" / "navigation.php"
_ACL        = _LEGACY / "application" / "configs" / "acl.php"
_SOUNDCARD_VIEW = _LEGACY / "application" / "views" / "scripts" / "preference" / "soundcard-setting.phtml"
_LINEIN_VIEW    = _LEGACY / "application" / "views" / "scripts" / "linein" / "index.phtml"
_LINEIN_CTRL    = _LEGACY / "application" / "controllers" / "LineinController.php"
_PREF_CTRL      = _LEGACY / "application" / "controllers" / "PreferenceController.php"
_DE_DE_PO   = _LEGACY / "locale" / "de_DE" / "LC_MESSAGES" / "libretime.po"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _po_pairs(po_text: str) -> dict[str, str]:
    """Return all active (non-obsolete) msgid→msgstr pairs from a .po file."""
    active = "\n".join(
        line for line in po_text.splitlines() if not line.startswith("#~")
    )
    pairs: dict[str, str] = {}
    for m in re.finditer(r'msgid "(.+?)"\nmsgstr "(.+?)"', active, re.DOTALL):
        pairs[m.group(1)] = m.group(2)
    return pairs


def _po_has(po_text: str, msgid: str) -> bool:
    """Return True if po_text has an active non-empty msgstr for msgid."""
    pairs = _po_pairs(po_text)
    return msgid in pairs and bool(pairs[msgid])


# ---------------------------------------------------------------------------
# 1–2  Navigation entries
# ---------------------------------------------------------------------------

def test_navigation_has_soundcard_entry():
    """navigation.php must register a Soundcard menu entry under Settings."""
    nav = _read(_NAV)
    assert "_('Soundcard')" in nav, (
        "navigation.php must have _('Soundcard') as a Settings sub-entry"
    )


def test_navigation_has_linein_entry():
    """navigation.php must register a Line-In menu entry under Settings."""
    nav = _read(_NAV)
    assert "_('Line-In')" in nav, (
        "navigation.php must have _('Line-In') as a Settings sub-entry"
    )


# ---------------------------------------------------------------------------
# 3–4  de_DE nav label translations
# ---------------------------------------------------------------------------

def test_de_de_translates_soundcard_nav_label():
    """de_DE must translate 'Soundcard' → 'Soundkarte'."""
    pairs = _po_pairs(_read(_DE_DE_PO))
    assert pairs.get("Soundcard") == "Soundkarte", (
        f"de_DE: expected msgstr 'Soundkarte' for 'Soundcard', "
        f"got {pairs.get('Soundcard')!r}"
    )


def test_de_de_translates_linein_nav_label():
    """de_DE must have a non-empty translation for 'Line-In'."""
    assert _po_has(_read(_DE_DE_PO), "Line-In"), (
        "de_DE must have a non-empty msgstr for msgid 'Line-In'"
    )


# ---------------------------------------------------------------------------
# 5  de_DE page + JS string coverage
# ---------------------------------------------------------------------------

_PAGE_MSGIDS = [
    # soundcard view — server-rendered labels
    "Soundcard Settings",
    "Main Output",
    "Preview / Monitor Output",
    "Line-In Inputs",
    "Add Line-In Device",
    "Configured Line-Ins",
    # linein view — server-rendered labels
    "Line-In Sources",
    "New Line-In",
    "Device",
    "Priority",
    "Input Device",
    "Channel Mapping",
    # JS i18n — soundcard
    "Soundcard settings saved.",
    "Could not save soundcard settings.",
    "No line-in devices configured.",
    "Device not found",
    # JS i18n — linein
    "No line-in sources configured yet.",
    "New Line-In Source",
    "Edit Line-In Source",
    "Create",
    "Line-in source created.",
    "Line-in source deleted.",
    "Delete this line-in source? This cannot be undone.",
]


def test_de_de_has_all_rastatime_page_and_js_strings():
    """de_DE must have non-empty translations for all T20.3 page and JS strings."""
    po = _read(_DE_DE_PO)
    missing = [mid for mid in _PAGE_MSGIDS if not _po_has(po, mid)]
    assert not missing, f"de_DE is missing translations for: {missing}"


# ---------------------------------------------------------------------------
# 6–7  JS i18n inline script blocks
# ---------------------------------------------------------------------------

def test_soundcard_view_has_airtime_i18n_script_block():
    """
    soundcard-setting.phtml must emit AIRTIME.i18n = { ... } so
    soundcardsetting.js reads PHP-translated strings at runtime.
    """
    view = _read(_SOUNDCARD_VIEW)
    assert "AIRTIME.i18n = {" in view, (
        "soundcard-setting.phtml must contain 'AIRTIME.i18n = {' script block"
    )
    assert "soundcardSaved" in view, (
        "AIRTIME.i18n block must include the 'soundcardSaved' key"
    )


def test_linein_view_has_airtime_linein_i18n_script_block():
    """
    linein/index.phtml must emit AIRTIME.linein.i18n = { ... } so
    linein.js reads PHP-translated strings at runtime.
    """
    view = _read(_LINEIN_VIEW)
    assert "AIRTIME.linein.i18n = {" in view, (
        "linein/index.phtml must contain 'AIRTIME.linein.i18n = {' script block"
    )
    assert "confirmDelete" in view, (
        "AIRTIME.linein.i18n block must include the 'confirmDelete' key"
    )


# ---------------------------------------------------------------------------
# 8–10  Controller / ACL wiring
# ---------------------------------------------------------------------------

def test_linein_controller_exists_with_index_action():
    """LineinController.php must exist and declare indexAction."""
    ctrl = _read(_LINEIN_CTRL)
    assert "class LineinController" in ctrl
    assert "public function indexAction" in ctrl


def test_preference_controller_has_soundcard_action():
    """PreferenceController.php must declare soundcardSettingAction."""
    assert "soundcardSettingAction" in _read(_PREF_CTRL)


def test_acl_grants_linein_resource():
    """acl.php must register and grant access to the 'linein' resource."""
    acl = _read(_ACL)
    assert "'linein'" in acl or '"linein"' in acl
