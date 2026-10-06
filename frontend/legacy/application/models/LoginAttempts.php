<?php

/**
 * Failed web logins per source address and per user name.
 *
 * RASTATIME 2026-10-06 - brute-force protection for the public login
 * (https://radio.example.org since the go-live).  LibreTime kept these
 * counters but never read them, and the per-IP INSERT stored the literal
 * ':ip'.  Now: a fixed window per address (cc_login_attempts.attempts +
 * last_attempt) - once the limit is reached inside the window the address
 * is blocked for a while and the login page answers 429 without touching
 * the password check.  A user name gets a SOFT brake only (shorter block
 * after many more failures), so that hammering the admin's name from many
 * addresses cannot lock the admin out for good.  Thresholds: constants.php
 * (RASTATIME_LOGIN_*).  Successful logins clear both counters.
 */
class Application_Model_LoginAttempts
{
    /**
     * Seconds the address still has to wait, 0 when it may try.
     */
    public static function blockedSecondsForIp($ip)
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT attempts, last_attempt FROM cc_login_attempts WHERE ip = :ip',
            [':ip' => (string) $ip],
            Application_Common_Database::SINGLE
        );
        if (!$row || $row['attempts'] === null || !$row['last_attempt']) {
            return 0;
        }

        return self::remainingBlock(
            (int) $row['attempts'],
            $row['last_attempt'],
            RASTATIME_LOGIN_IP_LIMIT,
            RASTATIME_LOGIN_IP_BLOCK_MIN
        );
    }

    /**
     * Seconds the user name still has to wait, 0 when it may try.
     */
    public static function blockedSecondsForUser($login)
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT login_attempts, login_attempt_at FROM cc_subjs WHERE login = :login',
            [':login' => (string) $login],
            Application_Common_Database::SINGLE
        );
        if (!$row || !$row['login_attempt_at']) {
            return 0;
        }

        return self::remainingBlock(
            (int) $row['login_attempts'],
            $row['login_attempt_at'],
            RASTATIME_LOGIN_USER_LIMIT,
            RASTATIME_LOGIN_USER_BLOCK_MIN
        );
    }

    /**
     * Records one failed login for the address: the counter restarts when
     * the previous failure lies outside the window.
     */
    public static function increaseAttempts($ip)
    {
        $ip = (string) $ip;
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT attempts, last_attempt FROM cc_login_attempts WHERE ip = :ip',
            [':ip' => $ip],
            Application_Common_Database::SINGLE
        );
        if ($row) {
            $inWindow = $row['last_attempt'] && self::ageSeconds($row['last_attempt']) <= RASTATIME_LOGIN_IP_WINDOW_MIN * 60;
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_login_attempts SET attempts = :attempts, last_attempt = now() WHERE ip = :ip',
                [':attempts' => $inWindow ? (int) $row['attempts'] + 1 : 1, ':ip' => $ip],
                Application_Common_Database::EXECUTE
            );
        } else {
            Application_Common_Database::prepareAndExecute(
                'INSERT INTO cc_login_attempts (ip, attempts, last_attempt) VALUES (:ip, 1, now())',
                [':ip' => $ip],
                Application_Common_Database::EXECUTE
            );
        }
        $attempts = $row ? ($inWindow ? (int) $row['attempts'] + 1 : 1) : 1;
        if ($attempts >= RASTATIME_LOGIN_IP_LIMIT) {
            Logging::warn("login: address {$ip} blocked for " . RASTATIME_LOGIN_IP_BLOCK_MIN
                . " min after {$attempts} failed logins");
        }
    }

    public static function getAttempts($ip)
    {
        $res = Application_Common_Database::prepareAndExecute(
            'SELECT attempts FROM cc_login_attempts WHERE ip = :ip',
            [':ip' => (string) $ip],
            Application_Common_Database::COLUMN
        );

        return $res ? (int) $res : 0;
    }

    public static function resetAttempts($ip)
    {
        Application_Common_Database::prepareAndExecute(
            'DELETE FROM cc_login_attempts WHERE ip = :ip',
            [':ip' => (string) $ip],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * Seconds left of a block: limit reached and the last failure younger
     * than the block length.  A failure older than the window never blocks
     * (the counter is stale and restarts on the next failure).
     */
    private static function remainingBlock($attempts, $lastAttempt, $limit, $blockMinutes)
    {
        if ($attempts < $limit) {
            return 0;
        }
        $age = self::ageSeconds($lastAttempt);
        $remaining = $blockMinutes * 60 - $age;

        return $remaining > 0 ? (int) ceil($remaining) : 0;
    }

    private static function ageSeconds($timestamp)
    {
        // cc_* timestamps are naive and written with now() by the same
        // PostgreSQL session; compare in the database's clock domain.
        $age = Application_Common_Database::prepareAndExecute(
            'SELECT EXTRACT(EPOCH FROM (now() - :ts::timestamp))',
            [':ts' => $timestamp],
            Application_Common_Database::COLUMN
        );

        return $age === false || $age === null ? PHP_INT_MAX : (float) $age;
    }
}
