"""
T20.3 — Local Machine / Line-In menu entries with i18n tests.

de_DE is the canonical German locale for RASTATIME (ADR-004); fr_FR and
es_ES are the other maintained locales (frontend/legacy/locale/README.md).
de_AT is an existing LibreTime community locale; RASTATIME does not
assert its coverage in the test suite.

History (tests updated 2026-10-02 / 2026-10-03):
  * 2026-05-16 — the Settings entry "Soundcard" was renamed to
    "Local Machine"; the controller action stays ``soundcard-setting``
    and the page now lives in ``preference/local-machine.phtml``.
  * 2026-05-16 / 2026-08-31 / 2026-09-17 — the standalone ``/linein``
    page went away: first folded into the Local Machine page (1f60295),
    then consolidated into the Library's Line-Input dialog (e836c26).
    The settings-side "Line-In" navigation entry is gone with it; the
    ``/linein/*`` controller routes stay for the AJAX endpoints.
  * 2026-10-03 — the whole Local Machine page (94 strings) is translated
    in de_DE / fr_FR / es_ES; until then only the May soundcard strings
    had German entries and fr/es had none.  Test 5 now walks every
    ``_()`` string of the view so a new section cannot ship untranslated.

Verify that:
  * navigation.php has the Local Machine entry and no Line-In entry.
  * every string the Local Machine page renders is translated in all
    three maintained locales.
  * local-machine.phtml emits an AIRTIME.i18n script block.
  * ACL entry for 'linein' resource exists.
  * LineinController.php exists with indexAction.
  * PreferenceController.php contains soundcardSettingAction.

Test inventory
--------------
Navigation (2, always run):
  1.  navigation.php has 'Local Machine' under Settings.
  2.  navigation.php has no 'Line-In' Settings entry any more.

Translations (3, always run):
  3.  de_DE translates the 'Soundcard' section heading → 'Soundkarte'.
  4.  The 'Local Machine' nav label is translated in de_DE / fr_FR / es_ES.
  5.  Every _() string of local-machine.phtml is translated in all three.

JS i18n script block (1, always run):
  6.  local-machine.phtml contains the AIRTIME.i18n inline script override.

Controller / ACL wiring (3, always run):
  7.  LineinController.php exists with indexAction.
  8.  PreferenceController.php contains soundcardSettingAction.
  9.  ACL.php grants 'linein' resource access.

(9 tests total)
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
_LOCAL_MACHINE_VIEW = _LEGACY / "application" / "views" / "scripts" / "preference" / "local-machine.phtml"
_LINEIN_CTRL    = _LEGACY / "application" / "controllers" / "LineinController.php"
_PREF_CTRL      = _LEGACY / "application" / "controllers" / "PreferenceController.php"
_LOCALE_DIR = _LEGACY / "locale"
_DE_DE_PO   = _LOCALE_DIR / "de_DE" / "LC_MESSAGES" / "libretime.po"

#: The maintained translations (frontend/legacy/locale/README.md).
_MAINTAINED_LOCALES = ("de_DE", "fr_FR", "es_ES")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _po_catalog(po_text: str) -> dict[str, str]:
    """Active msgid→msgstr pairs of a .po file, both as runtime text.

    Handles continuation lines and gettext escapes (``\\"``, ``\\\\``,
    ``\\n``) so a msgid with a Windows path or a quoted word compares
    equal to what PHP passes to ``_()``.  Obsolete (``#~``) entries are
    skipped like msgfmt does.
    """
    entries: dict[str, str] = {}
    key = None
    buf = ""
    current_id = None
    msgid = None
    for line in po_text.splitlines():
        if line.startswith("#~"):
            continue
        m = re.match(r'^(msgid|msgstr) "(.*)"$', line)
        if m:
            if key == "msgstr" and msgid is not None:
                entries[msgid] = buf
            key = m.group(1)
            buf = m.group(2)
            if key == "msgid":
                msgid = None
                current_id = buf
            else:
                msgid = current_id
            continue
        m = re.match(r'^"(.*)"$', line)
        if m and key is not None:
            buf += m.group(1)
            if key == "msgid":
                current_id = buf
            continue
    if key == "msgstr" and msgid is not None:
        entries[msgid] = buf

    def unescape(s: str) -> str:
        return s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")

    return {unescape(k): unescape(v) for k, v in entries.items()}


def _po_has(po_text: str, msgid: str) -> bool:
    """Return True if po_text has an active non-empty msgstr for msgid."""
    return bool(_po_catalog(po_text).get(msgid))


_PHP_CALL = re.compile(r"""_\(\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")\s*\)""")
_PHP_DQ_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "$": "$"}


def _php_double_quoted(raw: str) -> str:
    out = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            out.append(_PHP_DQ_ESCAPES.get(raw[i + 1], "\\" + raw[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _page_strings(view_text: str) -> list[str]:
    """Every distinct literal passed to ``_()`` in a view, as runtime text."""
    found: list[str] = []
    for m in _PHP_CALL.finditer(view_text):
        if m.group(1) is not None:
            s = m.group(1).replace("\\'", "'").replace("\\\\", "\\")
        else:
            s = _php_double_quoted(m.group(2))
        if s not in found:
            found.append(s)
    return found


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
# 3–5  Translations
# ---------------------------------------------------------------------------

def test_de_de_translates_soundcard_section_heading():
    """de_DE must translate 'Soundcard' → 'Soundkarte' (still the section
    heading on the Local Machine page)."""
    catalog = _po_catalog(_read(_DE_DE_PO))
    assert catalog.get("Soundcard") == "Soundkarte", (
        f"de_DE: expected msgstr 'Soundkarte' for 'Soundcard', "
        f"got {catalog.get('Soundcard')!r}"
    )


def test_local_machine_nav_label_translated_in_all_maintained_locales():
    """The Settings entry must not show up in English in a localized UI
    (it did until 2026-10-03)."""
    missing = [
        loc for loc in _MAINTAINED_LOCALES
        if not _po_has(_read(_LOCALE_DIR / loc / "LC_MESSAGES" / "libretime.po"), "Local Machine")
    ]
    assert not missing, f"'Local Machine' nav label untranslated in: {missing}"


def test_local_machine_page_strings_translated_in_all_maintained_locales():
    """Every ``_()`` string of local-machine.phtml must have a non-empty
    msgstr in de_DE, fr_FR and es_ES.

    Until 2026-10-03 the page carried 94 strings of which de_DE knew 13
    and fr/es 5 - every section added since May (import folder, FTP
    import, library location, 24/7 and per-show recording) had shipped
    without translations.  Walking the view keeps that from recurring.
    """
    strings = _page_strings(_read(_LOCAL_MACHINE_VIEW))
    assert len(strings) >= 90, f"expected the full page, found only {len(strings)} strings"
    report = {}
    for loc in _MAINTAINED_LOCALES:
        catalog = _po_catalog(_read(_LOCALE_DIR / loc / "LC_MESSAGES" / "libretime.po"))
        missing = [s for s in strings if not catalog.get(s)]
        if missing:
            report[loc] = missing
    assert not report, "untranslated Local Machine page strings:\n" + "\n".join(
        f"  {loc}: {len(items)} missing, e.g. {items[:3]!r}" for loc, items in report.items()
    )


# ---------------------------------------------------------------------------
# 6  JS i18n inline script block
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
# 7–9  Controller / ACL wiring
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
