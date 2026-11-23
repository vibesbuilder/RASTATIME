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
 *
 * RASTATIME 2026-11-23 - each entry can carry a comment (whose address,
 * why it is allowed) and the date it was added, so a stale entry can be
 * found and removed later.  They live in a second cc_pref key
 * (allowed_address_notes, JSON object entry -> {comment, added}); the list,
 * the mirror file and its readers do not know about them.
 */
class Application_Model_AllowedAddresses
{
    const MIRROR_FILE = 'allowlist.txt';

    /** longest comment kept, in characters */
    const COMMENT_MAX = 200;

    /** @return string[] entries as stored, in insertion order */
    public static function all()
    {
        return Application_Model_Preference::GetAllowedAddresses();
    }

    /**
     * The list with comment and date, in list order.
     *
     * @return array<int, array{entry: string, comment: string, added: string}>
     */
    public static function details()
    {
        $notes = Application_Model_Preference::GetAllowedAddressNotes();
        $out = [];
        foreach (self::all() as $entry) {
            $note = $notes[$entry] ?? ['comment' => '', 'added' => ''];
            $out[] = ['entry' => $entry, 'comment' => $note['comment'], 'added' => $note['added']];
        }

        return $out;
    }

    /** One line of plain text: no control characters, single spaces, at most COMMENT_MAX characters. */
    public static function cleanComment($comment)
    {
        $comment = preg_replace('/[[:cntrl:]]+/u', ' ', (string) $comment);
        $comment = trim(preg_replace('/\s+/u', ' ', (string) $comment));

        return mb_substr($comment, 0, self::COMMENT_MAX, 'UTF-8');
    }

    /** today in the station's time zone, Y-m-d */
    private static function today()
    {
        try {
            $tz = new DateTimeZone(Application_Model_Preference::GetDefaultTimezone() ?: 'UTC');
        } catch (Exception $e) {
            $tz = new DateTimeZone('UTC');
        }

        return (new DateTime('now', $tz))->format('Y-m-d');
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
     * Adds an entry (idempotent) and rewrites the mirror.  A new entry gets
     * today's date; a non-empty comment is stored (on an existing entry it
     * replaces the old one, an empty comment keeps it - "Allow" in the
     * blocked list never wipes a note).
     *
     * @return bool false when the entry is not an address or network
     */
    public static function add($entry, $comment = null)
    {
        if (!self::isValidEntry($entry)) {
            return false;
        }
        $entry = self::normalise($entry);
        $comment = $comment === null ? '' : self::cleanComment($comment);
        $list = self::all();
        $notes = Application_Model_Preference::GetAllowedAddressNotes();
        $isNew = !in_array($entry, $list, true);
        if ($isNew) {
            $list[] = $entry;
            Application_Model_Preference::SetAllowedAddresses($list);
            self::writeMirror($list);
            Logging::info("allowed-addresses: operator allowed {$entry}");
        }
        if ($isNew || $comment !== '') {
            $note = $notes[$entry] ?? ['comment' => '', 'added' => ''];
            if ($isNew) {
                $note['added'] = self::today();
            }
            if ($comment !== '') {
                $note['comment'] = $comment;
            }
            $notes[$entry] = $note;
            Application_Model_Preference::SetAllowedAddressNotes(self::pruneNotes($notes, $list));
        }

        return true;
    }

    /**
     * Sets (or with '' clears) the comment of an entry on the list.
     *
     * @return bool false when the entry is not on the list
     */
    public static function setComment($entry, $comment)
    {
        $wanted = self::normalise($entry);
        $list = self::all();
        $entry = null;
        foreach ($list as $e) {
            if (self::normalise($e) === $wanted) {
                $entry = $e;
                break;
            }
        }
        if ($entry === null) {
            return false;
        }
        $notes = Application_Model_Preference::GetAllowedAddressNotes();
        $note = $notes[$entry] ?? ['comment' => '', 'added' => ''];
        $note['comment'] = self::cleanComment($comment);
        $notes[$entry] = $note;
        Application_Model_Preference::SetAllowedAddressNotes(self::pruneNotes($notes, $list));

        return true;
    }

    /** Removes an entry (and its comment) and rewrites the mirror. */
    public static function remove($entry)
    {
        $entry = self::normalise($entry);
        $list = array_values(array_filter(self::all(), function ($e) use ($entry) {
            return self::normalise($e) !== $entry;
        }));
        Application_Model_Preference::SetAllowedAddresses($list);
        self::writeMirror($list);
        $notes = Application_Model_Preference::GetAllowedAddressNotes();
        unset($notes[$entry]);
        Application_Model_Preference::SetAllowedAddressNotes(self::pruneNotes($notes, $list));
        Logging::info("allowed-addresses: operator removed {$entry}");

        return true;
    }

    /** Only notes of entries still on the list, without empty ones. */
    private static function pruneNotes(array $notes, array $list)
    {
        $out = [];
        foreach ($list as $entry) {
            if (isset($notes[$entry]) && ($notes[$entry]['comment'] !== '' || $notes[$entry]['added'] !== '')) {
                $out[$entry] = $notes[$entry];
            }
        }

        return $out;
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
