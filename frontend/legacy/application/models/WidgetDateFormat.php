<?php

/**
 * RASTATIME 2026-11-10 - date and time labels of the Next / Latest Shows
 * widgets, rendered on the server in the station language.
 *
 * The widget script used to build them in the browser
 * (toLocaleDateString), so the rows stayed empty where scripts do not run
 * (an iframe with sandbox="", which some CMS editors add by themselves)
 * and the language depended on the visitor's browser settings.  Now the
 * page and the JSON feed carry finished labels; the script only shows
 * them.
 *
 * Four formats (Settings -> Widgets -> Next/Latest Shows, "Date format"),
 * each built from an ICU skeleton so the order and separators follow the
 * station language; the German examples:
 *   locale   - "Di., 15. Dez."   (default, the former browser format)
 *   short    - "Di, 15. Dez"     (abbreviation dots removed)
 *   numeric  - "Di, 15.12."
 *   dayMonth - "15.12."
 * Times are "H:mm - H:mm" (hour without leading zero, operator convention
 * 2026-05-22).
 */
class Application_Model_WidgetDateFormat
{
    public const FORMATS = ['locale', 'short', 'numeric', 'dayMonth'];
    public const DEFAULT_FORMAT = 'locale';

    private const SKELETONS = [
        'locale'   => 'EEEdMMM',
        'short'    => 'EEEdMMM',
        'numeric'  => 'EEEddMM',
        'dayMonth' => 'ddMM',
    ];

    private const FALLBACK_PATTERNS = [
        'locale'   => 'EEE, d MMM',
        'short'    => 'EEE, d MMM',
        'numeric'  => 'EEE, dd.MM.',
        'dayMonth' => 'dd.MM.',
    ];

    /** @var array<string, IntlDateFormatter|false> */
    private static $formatters = [];

    public static function normalize($format): string
    {
        $format = (string) $format;

        return in_array($format, self::FORMATS, true) ? $format : self::DEFAULT_FORMAT;
    }

    /**
     * Date label of one instant, e.g. "Di, 15. Dez".
     */
    public static function date(DateTimeInterface $when, string $format, string $locale, string $timezone): string
    {
        $format = self::normalize($format);
        $formatter = self::formatter($format, $locale, $timezone);
        if ($formatter === false) {
            return self::fallback($when, $format, $timezone);
        }
        $text = $formatter->format($when);
        if ($text === false) {
            return self::fallback($when, $format, $timezone);
        }
        if ($format === 'short' || $format === 'numeric') {
            // abbreviation dots ("Di." / "Dez.") go, date dots ("15.12.") stay
            $text = preg_replace('/(?<=\p{L})\./u', '', $text);
        }

        return $text;
    }

    /**
     * "16:07 - 17:00" in the given zone; "… - 17:00" / "16:07 - …" when one
     * end is missing.
     */
    public static function timeRange(?string $startIso, ?string $endIso, string $timezone): string
    {
        $a = self::clock($startIso, $timezone);
        $b = self::clock($endIso, $timezone);
        if ($a === '' && $b === '') {
            return '';
        }
        if ($a === '') {
            return '… - ' . $b;
        }
        if ($b === '') {
            return $a . ' - …';
        }

        return $a . ' - ' . $b;
    }

    /**
     * Adds date_label / time_label to every instance (['starts', 'ends']
     * ISO strings), for the page and the JSON feed alike.
     */
    public static function labelInstances(array $instances, string $format, string $locale, string $timezone): array
    {
        foreach ($instances as $i => $inst) {
            $starts = self::parse($inst['starts'] ?? null);
            $instances[$i]['date_label'] = $starts ? self::date($starts, $format, $locale, $timezone) : '';
            $instances[$i]['time_label'] = self::timeRange($inst['starts'] ?? null, $inst['ends'] ?? null, $timezone);
        }

        return $instances;
    }

    /**
     * format => example label, for the settings dropdown.
     */
    public static function examples(string $locale, string $timezone): array
    {
        $sample = new DateTime('2026-12-15 12:00:00', new DateTimeZone($timezone ?: 'UTC'));
        $out = [];
        foreach (self::FORMATS as $format) {
            $out[$format] = self::date($sample, $format, $locale, $timezone);
        }

        return $out;
    }

    private static function formatter(string $format, string $locale, string $timezone)
    {
        $key = $format . '|' . $locale . '|' . $timezone;
        if (array_key_exists($key, self::$formatters)) {
            return self::$formatters[$key];
        }
        $formatter = false;
        if (class_exists('IntlDateFormatter')) {
            $pattern = self::FALLBACK_PATTERNS[$format];
            if (class_exists('IntlDatePatternGenerator')) {
                $generated = (new IntlDatePatternGenerator($locale))->getBestPattern(self::SKELETONS[$format]);
                if (is_string($generated) && $generated !== '') {
                    $pattern = $generated;
                }
            }
            try {
                $formatter = new IntlDateFormatter(
                    $locale,
                    IntlDateFormatter::NONE,
                    IntlDateFormatter::NONE,
                    $timezone ?: 'UTC',
                    IntlDateFormatter::GREGORIAN,
                    $pattern
                );
            } catch (Throwable $e) {
                $formatter = false;
            }
        }

        return self::$formatters[$key] = $formatter;
    }

    private static function fallback(DateTimeInterface $when, string $format, string $timezone): string
    {
        $d = DateTime::createFromInterface($when)->setTimezone(new DateTimeZone($timezone ?: 'UTC'));
        switch ($format) {
            case 'numeric':
                return $d->format('D, d.m.');

            case 'dayMonth':
                return $d->format('d.m.');

            default:
                return $d->format('D, j M');
        }
    }

    private static function parse(?string $iso): ?DateTime
    {
        if ($iso === null || $iso === '') {
            return null;
        }
        try {
            return new DateTime($iso);
        } catch (Throwable $e) {
            return null;
        }
    }

    private static function clock(?string $iso, string $timezone): string
    {
        $d = self::parse($iso);
        if ($d === null) {
            return '';
        }
        $d->setTimezone(new DateTimeZone($timezone ?: 'UTC'));

        return $d->format('G:i');
    }
}
