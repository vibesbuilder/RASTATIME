<?php

/**
 * RASTATIME 2026-11-14 - the listener texts of the song request widget
 * (/embed/song-request), each replaceable on Widgets -> Song Request.
 *
 * Stored as one JSON preference (`widget_song_request_texts`, key => text);
 * an empty or missing text keeps the translated standard text, which
 * follows the station language like every widget.  Counts are written as
 * tokens: {total} (requestable tracks in the pool) and {shown} (rows on
 * screen) - the standard texts carry gettext placeholders, converted here
 * so the widget script knows one format only.
 */
class Application_Service_SongRequestTexts
{
    /** Longest text the page accepts (the button is cut to BUTTON_MAX). */
    public const TEXT_MAX = 200;
    public const BUTTON_MAX = 40;

    /** Texts that take a count, and the tokens they understand. */
    public const TOKENS = [
        'search' => ['{total}'],
        'more' => ['{shown}', '{total}'],
        'refine' => ['{shown}'],
    ];

    /**
     * The standard texts in the current gettext language, in the order
     * the settings page lists them.
     *
     * @return array<string, string>
     */
    public static function defaults(): array
    {
        return [
            'search' => str_replace('%s', '{total}', _('Search %s tracks…')),
            'loading' => _('Loading available tracks…'),
            'no_tracks' => _('No tracks are available for requests right now.'),
            'no_matches' => _('No tracks match your search.'),
            'more' => str_replace(
                ['%1$s', '%2$s'],
                ['{shown}', '{total}'],
                _('Showing the first %1$s of %2$s tracks - use the search to find the others.')
            ),
            'refine' => str_replace('%s', '{shown}', _('Showing the first %s matches - refine your search to find more.')),
            'request' => _('Request'),
            'success' => _('Thanks! Your request has been received.'),
            'duplicate' => _('You already requested this track recently.'),
            'ratelimit' => _('You have reached the request limit. Please try again later.'),
            'error' => _('Something went wrong. Please try again.'),
            'unavailable' => _('Song requests are currently unavailable.'),
        ];
    }

    /**
     * The standard texts as the widget shows them: in the station language,
     * also when the person on the settings page uses another one.
     *
     * @return array<string, string>
     */
    public static function stationDefaults(): array
    {
        $station = Application_Model_Preference::GetDefaultLocale();
        if ($station === Application_Model_Preference::GetLocale()) {
            return self::defaults();
        }

        try {
            Application_Model_Locale::configureLocalization($station);

            return self::defaults();
        } finally {
            // back to the language the page is rendered in (as PageLayoutInitPlugin sets it)
            Application_Model_Locale::configureLocalization();
        }
    }

    /**
     * The operator's own texts, '' where the standard text applies.
     *
     * @return array<string, string>
     */
    public static function custom(): array
    {
        $stored = Application_Model_Preference::GetWidgetSongRequestTexts();
        $out = [];
        foreach (array_keys(self::defaults()) as $key) {
            $out[$key] = isset($stored[$key]) && is_string($stored[$key]) ? trim($stored[$key]) : '';
        }

        return $out;
    }

    /**
     * What the widget shows: the own text, otherwise the standard text in
     * the current gettext language (the widget runs in the station language).
     *
     * @return array<string, string>
     */
    public static function effective(): array
    {
        $out = self::defaults();
        foreach (self::custom() as $key => $text) {
            if ($text !== '') {
                $out[$key] = $text;
            }
        }

        return $out;
    }

    /**
     * Keeps the known keys, trims, cuts to the length limits and drops
     * empty texts (the standard text applies again).
     *
     * @param array<string, mixed> $values
     */
    public static function save(array $values): void
    {
        $keep = [];
        foreach (array_keys(self::defaults()) as $key) {
            $text = trim((string) ($values[$key] ?? ''));
            if ($text === '') {
                continue;
            }
            $max = $key === 'request' ? self::BUTTON_MAX : self::TEXT_MAX;
            $keep[$key] = mb_substr($text, 0, $max, 'UTF-8');
        }
        Application_Model_Preference::SetWidgetSongRequestTexts($keep);
    }
}
