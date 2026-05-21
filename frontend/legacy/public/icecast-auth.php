<?php
/**
 * RASTATIME 2026-05-14 — ultra-light Icecast URL-auth endpoint.
 *
 * Replaces /api/icecast-listener-allow (which routes through Zend) for
 * the Icecast-side webhook.  Apache serves this file directly from the
 * DocumentRoot, so the response avoids:
 *
 *   * the full Zend Framework bootstrap (~150-300 ms per request),
 *   * the 3-4 PHP Deprecated warnings each of those bootstraps logs
 *     into Apache's error_log (which has grown to 176 MB in a day
 *     and slows down concurrent requests through I/O contention),
 *   * any session / DB lookup.
 *
 * Why this matters
 * ----------------
 * When the playout switches to /main or /show, FOUR listener-add
 * webhooks fire in parallel (mpv + 3 FfmpegStreamer instances).
 * Through the heavy Zend route, mod_fcgid's worker pool occasionally
 * stalled and Apache itself answered "401 -" (no body) for the first
 * couple of requests — visible in access_log as
 *
 *   "POST /api/icecast-listener-allow HTTP/1.1" 401 -
 *
 * which Icecast then logged as a failed listener-add and rejected the
 * FFmpeg streamers (mpv usually got through on retry; the streamers'
 * default reconnect budget ran out first).  Result: output mounts
 * /rastatime192 etc. disappeared the moment a DJ source connected.
 *
 * Hardcoded credentials
 * ---------------------
 * Must match ``stream.internal_listener.user/password`` in
 * ``libretime.conf``.  If those rotate, update here too.
 *
 * Localhost admin bypass is for ``/admin/killsource`` (Cancel-Show
 * workflow) — mirrors the same condition in the Zend
 * ApiController::icecastListenerAllowAction.
 */

declare(strict_types=1);

// Read params: Icecast 2.4 sends a POST body; tests sometimes use GET.
$user = $_POST['user'] ?? $_GET['user'] ?? '';
$pass = $_POST['pass'] ?? $_GET['pass'] ?? '';
$ip   = $_POST['ip']   ?? $_GET['ip']   ?? '';

// Must match libretime.conf -> stream.internal_listener.{user,password}.
const RT_LISTENER_USER = 'rastatime-playout';
const RT_LISTENER_PASS = 'change-me-internal-listener-secret';

// Icecast admin creds (icecast.xml <admin-user>/<admin-password>),
// only honoured when the request originates from localhost.
const RT_ICECAST_ADMIN_USER = 'admin';
const RT_ICECAST_ADMIN_PASS = 'admin';

function rt_allow(string $reason): void
{
    // Icecast 2.4's auth URL parser reads ONLY the response header
    // "icecast-auth-user: 1" — body content and Content-Type were
    // irrelevant in 2.4 (Icecast 2.5 changed that, but we're back on
    // 2.4 now).  Set Content-Type: text/plain explicitly because
    // PHP defaults to text/html and there were anecdotal reports of
    // Icecast 2.4 choking on the default text/html Content-Type from
    // PHP, resulting in the listener-add returning 400 (Bad Request)
    // instead of 200/401.  Empty body keeps the response minimal.
    header('Content-Type: text/plain');
    header('icecast-auth-user: 1');
    header('icecast-auth-message: ' . $reason);
    exit;
}

function rt_deny(string $reason): void
{
    http_response_code(401);
    header('Content-Type: text/plain');
    header('icecast-auth-message: ' . $reason);
    exit;
}

// Normal RASTATIME-PLAYOUT relay: matches the configured creds.
if ($user === RT_LISTENER_USER && $pass === RT_LISTENER_PASS) {
    rt_allow('rastatime-playout');
}

// Localhost admin bypass — Cancel-Show / killsource invocations.
if ($ip === '127.0.0.1' && $user === RT_ICECAST_ADMIN_USER && $pass === RT_ICECAST_ADMIN_PASS) {
    rt_allow('localhost-admin');
}

rt_deny('credentials rejected');
