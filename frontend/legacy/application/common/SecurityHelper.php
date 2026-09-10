<?php

class SecurityHelper
{
    public static function htmlescape_recursive(&$arr)
    {
        foreach ($arr as $key => $val) {
            if (is_array($val)) {
                self::htmlescape_recursive($arr[$key]);
            } elseif (is_string($val)) {
                $arr[$key] = htmlspecialchars($val, ENT_QUOTES);
            }
        }

        return $arr;
    }

    public static function verifyCSRFToken($observedToken)
    {
        // RASTATIME 2026-09-10: constant-time comparison, and a missing or
        // non-string token on either side is a failure.  The old `==` accepted
        // null == null, i.e. a session without a token plus a request without
        // one passed the check.
        if (!is_string($observedToken) || $observedToken === '') {
            return false;
        }
        $current_namespace = new Zend_Session_Namespace('csrf_namespace');
        $expected_csrf_token = $current_namespace->authtoken;
        if (!is_string($expected_csrf_token) || $expected_csrf_token === '') {
            return false;
        }

        return hash_equals($expected_csrf_token, $observedToken);
    }
}
