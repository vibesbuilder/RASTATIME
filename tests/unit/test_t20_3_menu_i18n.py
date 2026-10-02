"""
T20.3 — Local Machine / Line-In menu entries with i18n tests.

de_DE is the canonical German locale for RASTATIME (ADR-004).
de_AT is an existing LibreTime community locale; RASTATIME does not
assert its coverage in the test suite.

History (tests updated 2026-10-02):
  * 2026-05-16 — the Settings entry "Soundcard" was renamed to
    "Local Machine"; the controller action stays ``soundcard-setting``
    and the page now lives in ``preference/local-machine.phtml``.
  * 2026-05-16 / 2026-08-31 / 2026-09-17 — the standalone ``/linein``
    page went away: first folded into the Local Machine page (1f60295),
    then consolidated into the Library's Line-Input dialog (e836c26).
    The settings-side "Line-In" navigation entry is gone with it; the
    ``/linein/*`` controller routes stay for the AJAX endpoints.

Verify that:
  * navigation.php has the Local Machine entry and no Line-In entry.
  * de_DE .po file translates the page/JS strings still in use.
  * local-machine.phtml emits an AIRTIME.i18n script block.
  * ACL entry for 'linein' resource exists.
  * LineinController.php exists with indexAction.
  * PreferenceController.php contains soundcardSettingAction.

Test inventory
--------------
Navigation (2, always run):
  1.  navigation.php has 'Local Machine' under Settings.
  2.  navigation.php has no 'Line-In' Settings entry any more.

de_DE .po translations — labels (2, always run):
  3.  de_DE translates the 'Soundcard' section heading → 'Soundkarte'.
  4.  de_DE translates the 'Local Machine' nav label (known gap, xfail).

de_DE .po translations — page + JS strings (2, always run):
  5.  de_DE has the Local Machine page and JS strings that are translated.
  6.  de_DE still lacks the strings added with the rename (known gap, xfail).

JS i18n script block (1, always run):
  7.  local-machine.phtml contains the AIRTIME.i18n inline script override.

Controller / ACL wiring (3, always run):
  8.  LineinController.php exists with indexAction.
  9.  PreferenceController.php contains soundcardSettingAction.
 10.  ACL.php grants 'linein' resource access.

(10 tests total)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO       = Path(__file__).resolve().parents[2]
_LEGACY     = _REPO / "frontend" / "legacy"
_NAV        = _LEGACY / "application" / "configs" / "navigation.php"
_ACL        = _LEGACY / "application" / "configs" / "acl.php"
_LOCAL_MACHINE_VIEW = _LEGACY / "application" / "views" / "scripts" / "preference" / "local-machine.phtml"
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

def test_navigation_has_local_machine_entry():
    """navigation.php must register the Local Machine entry under Settings
    (renamed from "Soundcard" on 2026-05-16; nav labels are plain strings
    that Zend_Navigation runs through the translator)."""
    nav = _read(_NAV)
    assert "'label' => 'Local Machine'" in nav, (
        "navigation.php must have the 'Local Machine' Settings sub-entry"
    )


def test_navigation_has_no_linein_entry():
    """The settings-side Line-In entry was removed when the line-in editor
    moved into the Library dialog (e836c26); a re-appearing entry would
    point at a page that no longer exists."""
    nav = _read(_NAV)
    assert "'label' => 'Line-In'" not in nav, (
        "navigation.php must not register a 'Line-In' Settings entry - "
        "line-ins are edited in the Library dialog"
    )


# ---------------------------------------------------------------------------
# 3–4  de_DE label translations
# ---------------------------------------------------------------------------

def test_de_de_translates_soundcard_section_heading():
    """de_DE must translate 'Soundcard' → 'Soundkarte' (still the section
    heading on the Local Machine page)."""
    pairs = _po_pairs(_read(_DE_DE_PO))
    assert pairs.get("Soundcard") == "Soundkarte", (
        f"de_DE: expected msgstr 'Soundkarte' for 'Soundcard', "
        f"got {pairs.get('Soundcard')!r}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="de_DE has no entry for the nav label 'Local Machine' (gap found "
    "2026-10-02; the German menu shows it in English) - drop this marker "
    "once it is translated",
)
def test_de_de_translates_local_machine_nav_label():
    """de_DE must have a non-empty translation for 'Local Machine'."""
    assert _po_has(_read(_DE_DE_PO), "Local Machine")


# ---------------------------------------------------------------------------
# 5–6  de_DE page + JS string coverage
# ---------------------------------------------------------------------------

#: Strings the Local Machine page renders (server side or via its
#: AIRTIME.i18n block) that de_DE translates.
_PAGE_MSGIDS = [
    # server-rendered labels
    "Soundcard",
    "Main Output",
    # JS i18n (AIRTIME.i18n block)
    "No line-in devices configured.",
    "Device not found",
    "Could not load device list from the server.",
]

#: Strings the page renders that de_DE does not know yet - they came
#: with the 2026-05-16 rename and the 2026-09-03 restart button.
_UNTRANSLATED_PAGE_MSGIDS = [
    "Local Machine settings saved.",
    "Could not save Local Machine settings.",
    "Restarting audio chain …",
    "Could not restart the audio chain.",
]


def test_de_de_has_translated_local_machine_strings():
    """de_DE must keep non-empty translations for the page strings it has."""
    po = _read(_DE_DE_PO)
    missing = [mid for mid in _PAGE_MSGIDS if not _po_has(po, mid)]
    assert not missing, f"de_DE is missing translations for: {missing}"


@pytest.mark.xfail(
    strict=True,
    reason="de_DE lacks the Local Machine strings added with the 2026-05-16 "
    "rename and the 2026-09-03 restart button (gap found 2026-10-02) - "
    "drop this marker once they are translated",
)
def test_de_de_has_the_newer_local_machine_strings():
    """de_DE must translate every string the Local Machine page renders."""
    po = _read(_DE_DE_PO)
    missing = [mid for mid in _UNTRANSLATED_PAGE_MSGIDS if not _po_has(po, mid)]
    assert not missing, f"de_DE is missing translations for: {missing}"


# ---------------------------------------------------------------------------
# 7  JS i18n inline script block
# ---------------------------------------------------------------------------

def test_local_machine_view_has_airtime_i18n_script_block():
    """
    local-machine.phtml must emit AIRTIME.i18n = { ... } so the page's
    JS reads PHP-translated strings at runtime.
    """
    view = _read(_LOCAL_MACHINE_VIEW)
    assert "AIRTIME.i18n = {" in view, (
        "local-machine.phtml must contain 'AIRTIME.i18n = {' script block"
    )
    assert "soundcardSaved" in view, (
        "AIRTIME.i18n block must include the 'soundcardSaved' key"
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
