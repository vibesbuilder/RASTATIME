<?php

final class Application_Model_Locale
{
    private static $domains = ['libretime'];

    // RASTATIME 2026-05-15 - Reduced from the upstream 22-language list to the
    // four languages we actually maintain.  Adding a language back requires:
    //   1. an entry here,
    //   2. a populated .po (+ compiled .mo) under locale/<LANG>/LC_MESSAGES/,
    //   3. matching files under public/js/datatables/i18n/<LANG>.txt and
    //      public/js/plupload/i18n/<LANG>.js,
    //   4. a row in locale/locale.gen (informational on Linux installs).
    public static $locales = [
        'en_US' => 'English',
        'de_DE' => 'Deutsch',
        'fr_FR' => 'Français',
        'es_ES' => 'Español',
    ];

    public static function getLocales()
    {
        return self::$locales;
    }

    public static function configureLocalization($locale = null)
    {
        $codeset = 'UTF-8';

        // RASTATIME 2026-05-15 - Resolve $locale up front.  The upstream code
        // only built $lang inside the is_null() branch and then ran
        // putenv("LANGUAGE={$locale}") with $locale still null, so every call
        // from PageLayoutInitPlugin (which passes no argument) silently emptied
        // LANGUAGE.  gettext then fell back to whatever LC_MESSAGES the PHP
        // worker process happened to carry from a prior request, which on
        // recycled Apache/fcgid workers produced a sticky-stale locale (the
        // "UI keeps showing German even after switching to English" symptom).
        if (is_null($locale)) {
            $locale = Application_Model_Preference::GetLocale();
        }
        $lang = $locale . '.' . $codeset;

        putenv("LANGUAGE={$locale}");

        // RASTATIME 2026-05-15 - Try multiple setlocale variants so the call
        // succeeds on Windows hosts that do not expose POSIX-style locale
        // names like "en_US.UTF-8" (Windows wants e.g. "en-US" or
        // "english_united-states.utf8").  gettext's actual .mo lookup is
        // driven by the LANGUAGE env var above and bindtextdomain() below,
        // so setlocale here primarily affects PHP's own LC_* state.
        $variants = [$lang, $locale, str_replace('_', '-', $locale)];
        $setlocaleOk = false;
        foreach ($variants as $variant) {
            if (setlocale(LC_ALL, $variant) !== false) {
                $setlocaleOk = true;
                break;
            }
        }
        if (!$setlocaleOk) {
            Logging::warn('setlocale rejected all variants for ' . $locale
                . ' (tried: ' . implode(', ', $variants) . ')');
        }

        // RASTATIME 2026-05-15 - Use an absolute path resolved from this
        // file's location instead of "../locale".  Apache/fcgid does not
        // guarantee a stable CWD, so the relative path made the lookup
        // brittle.  __DIR__ is application/models/, so locale/ is three
        // levels up.
        $localeDir = realpath(__DIR__ . '/../../locale');
        foreach (self::$domains as $domain) {
            bindtextdomain($domain, $localeDir);
            bind_textdomain_codeset($domain, $codeset);
        }

        textdomain('libretime');
    }

    /**
     * We need this function for the case where a user has logged out, but
     * has an airtime_locale cookie containing their locale setting.
     *
     * If the user does not have an airtime_locale cookie set, we default
     * to the station locale.
     *
     * When the user logs in, the value set in the login form will be passed
     * into the airtime_locale cookie. This cookie is also updated when
     * a user updates their user settings.
     */
    public static function getUserLocale()
    {
        $request = Zend_Controller_Front::getInstance()->getRequest();

        return $request->getCookie('airtime_locale', Application_Model_Preference::GetLocale());
    }
}
