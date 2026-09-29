<?php

/**
 * RASTATIME 2026-09-29 - the interface's primary (accent) colour, a
 * station-wide setting under Settings -> General (operator wish; it was a
 * hard-coded orange, #ff5d1a, in some 90 places).
 *
 * The stylesheets read the colour from CSS custom properties.  This class
 * derives the shades the old hard-coded oranges used (hover, visited,
 * gradients, the two selected-row tones) and the text colours for use ON
 * the accent, and prints them as a style block in every page head.  The
 * default palette is repeated in styles.css (:root) as the fallback for a
 * page without the block; keep the two in step.
 */
class Application_Model_AccentColor
{
    public const DEFAULT_COLOR = '#ff5d1a';

    private static $current;

    /**
     * @param mixed $hex
     *
     * @return null|string '#rrggbb' in lower case, null for anything else
     */
    public static function normalize($hex)
    {
        if (!is_string($hex) || !preg_match('/^#?([0-9a-fA-F]{6})$/', trim($hex), $m)) {
            return null;
        }

        return '#' . strtolower($m[1]);
    }

    /**
     * @return string the configured colour, or the default
     */
    public static function current()
    {
        if (self::$current === null) {
            self::$current = self::normalize(Application_Model_Preference::GetUiAccentColor())
                ?? self::DEFAULT_COLOR;
        }

        return self::$current;
    }

    /**
     * @param string $hex
     *
     * @return array CSS custom property => value
     */
    public static function palette($hex)
    {
        $rgb = sscanf(self::normalize($hex) ?? self::DEFAULT_COLOR, '#%02x%02x%02x');
        $luminance = self::luminance($rgb);

        return [
            '--rt-accent' => self::toHex($rgb),
            // for rgba(var(--rt-accent-rgb), alpha)
            '--rt-accent-rgb' => implode(', ', $rgb),
            // selected rows (even / odd), light gradient tops, hover fills
            '--rt-accent-soft' => self::toHex(self::mix($rgb, [255, 255, 255], 0.12)),
            '--rt-accent-light' => self::toHex(self::mix($rgb, [255, 255, 255], 0.25)),
            // visited links, gradient bottoms, pressed states, borders
            '--rt-accent-dark' => self::toHex(self::mix($rgb, [0, 0, 0], 0.18)),
            '--rt-accent-darker' => self::toHex(self::mix($rgb, [0, 0, 0], 0.35)),
            // Text ON the accent.  -fg where the orange design had white
            // text, -fg-dark where it had black; each flips only when the
            // colour is too light / too dark for it.  The default orange
            // (luminance 0.29) keeps white and black respectively.
            '--rt-accent-fg' => $luminance > 0.45 ? '#000' : '#fff',
            '--rt-accent-fg-dark' => $luminance < 0.18 ? '#fff' : '#000',
        ];
    }

    /**
     * @param null|string $hex the colour to print, default: the configured one
     *
     * @return string a <style> element defining the palette on :root
     */
    public static function styleTag($hex = null)
    {
        $css = '';
        foreach (self::palette($hex ?? self::current()) as $name => $value) {
            $css .= $name . ':' . $value . ';';
        }

        // :root:root outranks the :root fallback in styles.css wherever the
        // block lands relative to the stylesheet links.
        return '<style id="rt-accent">:root:root{' . $css . '}</style>';
    }

    private static function mix(array $rgb, array $with, $amount)
    {
        $out = [];
        foreach ($rgb as $i => $channel) {
            $out[] = (int) round($channel * (1 - $amount) + $with[$i] * $amount);
        }

        return $out;
    }

    private static function toHex(array $rgb)
    {
        return vsprintf('#%02x%02x%02x', $rgb);
    }

    // WCAG relative luminance, 0 (black) .. 1 (white)
    private static function luminance(array $rgb)
    {
        $lin = [];
        foreach ($rgb as $channel) {
            $c = $channel / 255;
            $lin[] = $c <= 0.03928 ? $c / 12.92 : (($c + 0.055) / 1.055) ** 2.4;
        }

        return 0.2126 * $lin[0] + 0.7152 * $lin[1] + 0.0722 * $lin[2];
    }
}
