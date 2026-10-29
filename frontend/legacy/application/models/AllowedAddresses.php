<?php

/**
 * RASTATIME 2026-10-08 - addresses the brute-force brakes leave alone.
 *
 * Operator request: a blocked address can be turned into an allowed one
 * with one click ("Allow" in System Status -> Blocked addresses), and the
 * list can be edited there ("Allowed addresses": address or CIDR network,
 * Remove).  An allowed address is never braked by the web login, never
 * throttled by the DJ harbor and never turned into a firewall rule by the
 * watcher; private (LAN) addresses are exempt anyway.
 *
 * The list lives in cc_pref (key allowed_addresses, JSON list of strings)
 * and is mirrored into <config dir>/allowlist.txt - one entry per line -
 * for the two readers outside PHP: the playout (dj_auth.AllowList) and
 * the watcher task (rt-firewall-watch.ps1).  The mirror is rewritten on
 * every change; readers reload it when its modification time changes.
 */
class Application_Model_AllowedAddresses
{
    const MIRROR_FILE = 'allowlist.txt';

    /** @return string[] entries as stored, in insertion order */
    public static function all()
    {
        return Application_Model_Preference::GetAllowedAddresses();
    }

    /** @return string path of the mirror file next to rastatime.conf */
    public static function mirrorPath()
    {
        return rtrim(dirname(RASTATIME_CONFIG_FILEPATH), '/\\') . DIRECTORY_SEPARATOR . self::MIRROR_FILE;
    }

    /**
     * An IPv4/IPv6 address or a CIDR network (10.1.0.0/16, 2001:db8::/32).
     */
    public static function isValidEntry($entry)
    {
        $entry = trim((string) $entry);
        if ($entry === '') {
            return false;
        }
        if (strpos($entry, '/') === false) {
            return filter_var($entry, FILTER_VALIDATE_IP) !== false;
        }
        [$net, $bits] = explode('/', $entry, 2);
        if (!ctype_digit($bits) || filter_var($net, FILTER_VALIDATE_IP) === false) {
            return false;
        }
        $max = strpos($net, ':') !== false ? 128 : 32;

        return (int) $bits >= 0 && (int) $bits <= $max;
    }

    /** Normalised form: lower case, no spaces; a /32 or /128 becomes the plain address. */
    public static function normalise($entry)
    {
        $entry = strtolower(trim((string) $entry));
        if (preg_match('#^(.+)/(\d+)$#', $entry, $m)) {
            $max = strpos($m[1], ':') !== false ? 128 : 32;
            if ((int) $m[2] === $max) {
                return $m[1];
            }
        }

        return $entry;
    }

    /**
     * @return bool whether the address matches an entry of the list
     */
    public static function isAllowed($address)
    {
        $address = trim((string) $address);
        if ($address === '' || filter_var($address, FILTER_VALIDATE_IP) === false) {
            return false;
        }
        foreach (self::all() as $entry) {
            if (self::matches($address, $entry)) {
                return true;
            }
        }

        return false;
    }

    public static function matches($address, $entry)
    {
        $entry = self::normalise($entry);
        if (strpos($entry, '/') === false) {
            return strtolower($address) === $entry
                || (@inet_pton($address) !== false && @inet_pton($entry) !== false && inet_pton($address) === inet_pton($entry));
        }
        [$net, $bits] = explode('/', $entry, 2);
        $a = @inet_pton($address);
        $n = @inet_pton($net);
        if ($a === false || $n === false || strlen($a) !== strlen($n)) {
            return false;
        }
        $bits = (int) $bits;
        $bytes = intdiv($bits, 8);
        if ($bytes > 0 && substr($a, 0, $bytes) !== substr($n, 0, $bytes)) {
            return false;
        }
        $rest = $bits % 8;
        if ($rest === 0) {
            return true;
        }
        $mask = (0xFF << (8 - $rest)) & 0xFF;

        return (ord($a[$bytes]) & $mask) === (ord($n[$bytes]) & $mask);
    }

    /**
     * Adds an entry (idempotent) and rewrites the mirror.
     *
     * @return bool false when the entry is not an address or network
     */
    public static function add($entry)
    {
        if (!self::isValidEntry($entry)) {
            return false;
        }
        $entry = self::normalise($entry);
        $list = self::all();
        if (!in_array($entry, $list, true)) {
            $list[] = $entry;
            Application_Model_Preference::SetAllowedAddresses($list);
            self::writeMirror($list);
            Logging::info("allowed-addresses: operator allowed {$entry}");
        }

        return true;
    }

    /** Removes an entry and rewrites the mirror. */
    public static function remove($entry)
    {
        $entry = self::normalise($entry);
        $list = array_values(array_filter(self::all(), function ($e) use ($entry) {
            return self::normalise($e) !== $entry;
        }));
        Application_Model_Preference::SetAllowedAddresses($list);
        self::writeMirror($list);
        Logging::info("allowed-addresses: operator removed {$entry}");

        return true;
    }

    /** Writes the mirror file for the playout and the watcher. */
    public static function writeMirror($list = null)
    {
        $list = $list === null ? self::all() : $list;
        $path = self::mirrorPath();
        $body = "# RASTATIME allowed addresses - written by the web UI (System Status), do not edit\n"
            . implode("\n", $list) . (empty($list) ? '' : "\n");
        if (@file_put_contents($path, $body) === false) {
            Logging::warn('allowed-addresses: cannot write ' . $path);

            return false;
        }

        return true;
    }
}
