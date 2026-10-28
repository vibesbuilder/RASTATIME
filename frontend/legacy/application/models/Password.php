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
 * bcrypt package ("$2b$" prefix); both sides verify both prefixes.  An old
 * 32-character hex value is still accepted by verify() so that every
 * account keeps working and is re-hashed on its next successful login
 * (Application_Model_User::verifyPassword, the login adapter).
 */
class Application_Model_Password
{
    public const BCRYPT_COST = 12;

    /** Hash a plain password for storage. */
    public static function hash(string $plain): string
    {
        return password_hash($plain, PASSWORD_BCRYPT, ['cost' => self::BCRYPT_COST]);
    }

    /** True when $stored is an unsalted md5 of the pre-2026-10-27 era. */
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
     * Check a plain password against the stored value: bcrypt, or the
     * legacy md5 as a fallback.  An empty stored value never matches
     * (header-auth placeholder accounts).
     */
    public static function verify(string $plain, ?string $stored): bool
    {
        if ($stored === null || $stored === '') {
            return false;
        }
        if (self::isBcrypt($stored)) {
            return password_verify($plain, $stored);
        }
        if (self::isLegacyMd5($stored)) {
            return hash_equals(strtolower($stored), md5($plain));
        }

        return false;
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
