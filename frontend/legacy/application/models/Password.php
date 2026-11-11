<?php

/**
 * RASTATIME 2026-10-27 - password hashing for cc_subjs.pass.
 *
 * Up to 2026-10-27 the column held md5(password) without a salt (upstream
 * LibreTime: Zend_Auth_Adapter_DbTable with "MD5(?)", User::setPassword,
 * the DJ harbor check, the Django API hasher).  A database or backup leak
 * therefore gave every password away through rainbow tables.
 *
 * New hashes are bcrypt (password_hash, PASSWORD_BCRYPT, cost 12, "$2y$"
 * prefix).  The Django API writes the same algorithm with the python
 * bcrypt package ("$2b$" prefix); both sides verify both prefixes.
 *
 * Until 2026-11-11 an old 32-character hex value was still accepted and
 * re-hashed on the next login.  Every account had migrated by then, so the
 * md5 fallback is gone (CodeQL py/weak-sensitive-data-hashing): an md5
 * value - e.g. from a restored pre-2026-10-27 backup - never matches; the
 * account needs a new password (`manage.py password_hashes` names them).
 */
class Application_Model_Password
{
    public const BCRYPT_COST = 12;

    /** Hash a plain password for storage. */
    public static function hash(string $plain): string
    {
        return password_hash($plain, PASSWORD_BCRYPT, ['cost' => self::BCRYPT_COST]);
    }

    /** True when $stored is an unsalted md5 of the pre-2026-10-27 era (no longer accepted). */
    public static function isLegacyMd5(?string $stored): bool
    {
        return $stored !== null && preg_match('/^[0-9a-f]{32}$/i', $stored) === 1;
    }

    /** True when $stored is a bcrypt hash (PHP "$2y$" or python "$2b$" / "$2a$"). */
    public static function isBcrypt(?string $stored): bool
    {
        return $stored !== null && preg_match('/^\$2[aby]\$\d{2}\$[.\/0-9A-Za-z]{53}$/', $stored) === 1;
    }

    /**
     * Check a plain password against the stored bcrypt value.  Anything
     * else - empty (header-auth placeholder accounts), a legacy md5 - never
     * matches.
     */
    public static function verify(string $plain, ?string $stored): bool
    {
        if ($stored === null || !self::isBcrypt($stored)) {
            return false;
        }

        return password_verify($plain, $stored);
    }

    /** True when a verified password should be stored again with the current algorithm. */
    public static function needsRehash(?string $stored): bool
    {
        if (!self::isBcrypt($stored)) {
            return true;
        }

        return password_needs_rehash($stored, PASSWORD_BCRYPT, ['cost' => self::BCRYPT_COST]);
    }
}
