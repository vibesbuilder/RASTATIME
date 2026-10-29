# RASTATIME legacy frontend locales

This directory holds the gettext `.po` source files and compiled `.mo`
binaries for the legacy (Zend Framework 1) frontend.  At runtime PHP's
`gettext` extension reads `.mo` files; the `.po` files are the human-
editable source.  Each `_()` call in PHP / `.phtml` and the JS i18n
strings emitted by `LocaleController.php` are looked up against the
currently-bound locale's `rastatime.mo`.

## Active languages

RASTATIME maintains four:

| Code | Display name | Status |
|---|---|---|
| `en_US` | English | source language |
| `de_DE` | Deutsch | maintained |
| `fr_FR` | Français | maintained |
| `es_ES` | Español | maintained |

The list is hard-coded in two places that must stay in sync:
- `frontend/legacy/application/models/Locale.php` (`$locales` array)
- `frontend/legacy/locale/locale.gen` (informational)

## Editing a single translation

When a translated string is missing or wrong:

1. Open the language's `.po` file in a text editor or in
   [Poedit](https://poedit.net/) (a free GUI translation editor that
   keeps the file format clean — recommended for non-programmers).
   - With a text editor: `frontend/legacy/locale/<LANG>/LC_MESSAGES/rastatime.po`
   - With Poedit: `File → Open` and pick the `.po`.

2. Find the entry.  Each entry looks like:
   ```
   #: application/path/to/source.php:42
   msgid "English source string"
   msgstr "Übersetzter Text"
   ```
   - `msgid` is the original English source.  **Never edit `msgid`** —
     it is the lookup key against the source code.
   - `msgstr` is the translated text.  Edit this.

3. If a translation is marked `#, fuzzy` it means an upstream import
   inherited a candidate translation that needs a human review.
   Verify the text is still accurate for the current `msgid`, then
   **delete the `#, fuzzy` line** to ratify it.  Translations that
   remain fuzzy are ignored by `msgfmt` and the UI shows the English
   source string instead.

4. Rebuild the `.mo` binaries:
   ```
   powershell -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\maintenance\build-locales.ps1
   ```

5. Restart Apache so PHP picks up the new `.mo`:
   ```
   nssm restart RASTATIME-APACHE
   ```

6. Hard-reload the browser (`Ctrl+F5`) and verify.

### Multi-line translations

Long strings use the line-continuation form.  Both `msgid` and `msgstr`
start with an empty `""` and the actual text follows on continuation
lines:

```
msgid ""
"This is the first line of the source string. "
"This is the second line."
msgstr ""
"Dies ist die erste Zeile des Quelltextes. "
"Dies ist die zweite Zeile."
```

Mind the trailing spaces inside the quotes — they matter.

## Adding a new language

Five steps.  Replace `<LANG>` with a POSIX locale code such as `it_IT`
or `nl_NL`.

1. **Create the `.po` file.**  Copy the most relevant existing language
   as a template (e.g. copy `es_ES` if adding Italian):
   ```
   mkdir frontend\legacy\locale\<LANG>\LC_MESSAGES
   copy frontend\legacy\locale\es_ES\LC_MESSAGES\rastatime.po ^
        frontend\legacy\locale\<LANG>\LC_MESSAGES\rastatime.po
   ```
   Then open the new `.po` in Poedit, set `Language` to the new code
   in `Catalog → Properties`, and translate all msgstr (or empty them
   out and start fresh).

2. **Add the JavaScript i18n files.**  The DataTables and Plupload
   widgets read translations from their own files:
   ```
   frontend\legacy\public\js\datatables\i18n\<LANG>.txt
   frontend\legacy\public\js\plupload\i18n\<LANG>.js
   ```
   Copy from an existing language and translate the values.  See the
   existing `de_DE.txt` / `de_DE.js` for the schema.

3. **Register the language in `Locale.php`.**  Add an entry to the
   `$locales` array in
   `frontend/legacy/application/models/Locale.php`.  The key is the
   locale code, the value is the display name shown in the dropdown:
   ```php
   public static $locales = [
       'en_US' => 'English',
       'de_DE' => 'Deutsch',
       'fr_FR' => 'Français',
       'es_ES' => 'Español',
       '<LANG>' => 'Display Name In Its Own Language',
   ];
   ```

4. **Register the language in the build script.**  Add the code to the
   `$activeLanguages` array in
   `infra/scripts/maintenance/build-locales.ps1`.  This array drives
   which `.po` files get compiled to `.mo`.

5. **Add an entry to `locale.gen`** in this directory.  This file is
   informational — it lists which OS-level locales the legacy
   `make`-based Linux installer used to provision via `locale-gen`.
   On Windows it is not consumed at runtime, but we keep it in sync
   for documentation:
   ```
   <LANG>.UTF-8 UTF-8
   ```

Then run the build + restart sequence:
```
powershell -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\maintenance\build-locales.ps1
nssm restart RASTATIME-APACHE
```

Reload the browser and pick the new language in Settings → General →
Default Language.

## How the runtime lookup works

`gettext` looks up a translation in this order:

1. The `LANGUAGE` env var (set by
   `Application_Model_Locale::configureLocalization()` to the
   user's chosen locale).
2. The directory bound via `bindtextdomain('libretime', <abs_path>)`
   — for RASTATIME this is `frontend/legacy/locale/` resolved by
   `realpath()` from `Locale.php`.
3. The `rastatime.mo` inside `<dir>/<LANG>/LC_MESSAGES/`.
4. If the msgid is not found in the `.mo`, gettext returns the
   `msgid` itself.  English source strings therefore "fall back"
   to English automatically when a translation is missing.

If a UI element stubbornly stays in the wrong language even after a
rebuild, suspect one of these:

- Apache has not been restarted (PHP gettext caches per worker).
- The user's browser still holds an old `airtime_locale` cookie.
- The string is built at Bootstrap time (`navigation.php`) — these
  are always stored as plain English source strings, then translated
  in `views/scripts/menu.phtml`.  Do not add `_()` calls to
  `navigation.php`; see the header comment in that file for why.
