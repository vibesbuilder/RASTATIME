<?php

/**
 * Subj class.
 *
 * users + groups
 * with "linearized recursive membership" ;)
 *   (allow adding users to groups or groups to groups)
 *
 * @copyright 2010 Sourcefabric O.P.S.
 * @license https://www.gnu.org/licenses/gpl.txt
 */
class Application_Model_Subjects
{
    // ======================================================= public methods

    public static function increaseLoginAttempts($login)
    {
        // RASTATIME 2026-10-06 - counter restarts when the previous failure
        // lies outside the user window (brute-force brake, constants.php)
        $sql = 'UPDATE cc_subjs SET login_attempts = CASE'
            . ' WHEN login_attempt_at IS NULL OR login_attempt_at < now() - make_interval(mins => '
            . (int) RASTATIME_LOGIN_USER_WINDOW_MIN . ') THEN 1'
            . ' ELSE COALESCE(login_attempts, 0) + 1 END,'
            . ' login_attempt_at = now()'
            . ' WHERE login=:login';

        $map = [':login' => $login];

        $res = Application_Common_Database::prepareAndExecute(
            $sql,
            $map,
            Application_Common_Database::EXECUTE
        );

        return intval($res) > 0;
    }

    public static function resetLoginAttempts($login)
    {
        $sql = "UPDATE cc_subjs SET login_attempts = '0', login_attempt_at = NULL"
            . ' WHERE login=:login';
        $map = [':login' => $login];

        $res = Application_Common_Database::prepareAndExecute(
            $sql,
            $map,
            Application_Common_Database::EXECUTE
        );

        return true;
    }

    public static function getLoginAttempts($login)
    {
        $sql = 'SELECT login_attempts FROM cc_subjs WHERE login=:login';
        $map = [':login' => $login];

        $res = Application_Common_Database::prepareAndExecute(
            $sql,
            $map,
            Application_Common_Database::COLUMN
        );

        return ($res !== false) ? $res : 0;
    }
} // class Subjects
