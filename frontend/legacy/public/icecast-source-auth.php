<?php
/**
 * RASTATIME 2026-05-14 — Icecast source-auth endpoint.
 *
 * Wired into icecast.xml's <authentication type="url"> as the
 * ``stream_auth`` URL for /main and /show.  ``mount_add`` and
 * ``mount_remove`` are NOT routed through this PHP — they hit the
 * playout's source-switcher directly at :8770 (see icecast.xml).
 * This file only handles pre-admission authentication.
 *
 * Why a separate light PHP (no Zend bootstrap)
 * --------------------------------------------
 * Icecast 2.4's auth URL has a ~3 s timeout, and the full Zend stack
 * was breaching that under concurrent load.  Same reason as
 * public/icecast-auth.php — see that file for the backstory.
 *
 * stream_auth POST body (from Icecast 2.4)
 * ----------------------------------------
 *   action=stream_auth
 *   mount=/main | /show
 *   ip=<source-client-ip>
 *   server=localhost
 *   port=8000
 *   user=<source-client-user>
 *   pass=<source-client-pass>
 *   admin=1                  (only for admin/metadata requests)
 *
 * Response: ``icecast-auth-user: 1`` header → admit, HTTP 401 → reject.
 *
 * Auth rules
 * ----------
 * /main (Master Source):
 *   * cc_pref.live_stream_master_username + live_stream_master_password
 *     (plain comparison; cc_pref stores these in clear text).
 *   * (The built-in fallback logins source/master-secret and
 *     source/show-secret were removed 2026-10-25, role audit S5.)
 *
 * /show (Show DJ Source) — STRICT mode, Variant A:
 *   * An unmodified show instance MUST be running right now.
 *     Within that:
 *     - cc_show.live_stream_using_custom_auth = true → user+pass must
 *       match cc_show.live_stream_user / live_stream_pass exactly.
 *     - cc_show.live_stream_using_airtime_auth = true → user must
 *       be in cc_subjs JOIN cc_show_hosts for this show, and
 *       md5(pass) === cc_subjs.pass (Legacy LibreTime hash format).
 *   * Anything else → 401 reject.
 */

declare(strict_types=1);

// RASTATIME 2026-10-25 (role audit S5) - only Icecast on this machine calls
// this file; it sits in the public web root, so any other caller could try
// DJ passwords here.  Others get 403.
$rtPeer = (string) ($_SERVER['REMOTE_ADDR'] ?? '');
if (stripos($rtPeer, '::ffff:') === 0) {
    $rtPeer = substr($rtPeer, 7);
}
if ($rtPeer !== '::1' && strpos($rtPeer, '127.') !== 0) {
    http_response_code(403);
    header('Content-Type: text/plain');
    echo "local callers only\n";
    exit;
}

// ---------------------------------------------------------------------
// Action dispatch
// ---------------------------------------------------------------------
$action = $_POST['action'] ?? '';
$mount  = $_POST['mount']  ?? '';
$user   = $_POST['user']   ?? '';
$pass   = $_POST['pass']   ?? '';

if ($action !== 'stream_auth') {
    // mount_add / mount_remove are wired direct-to-:8770 in icecast.xml;
    // this PHP only handles pre-admission auth.  Anything else: reject.
    http_response_code(400);
    header('Content-Type: text/plain');
    header('icecast-auth-message: only stream_auth accepted here');
    exit;
}

if ($mount === '/main') {
    rt_check_main_auth($user, $pass);
} elseif ($mount === '/show') {
    rt_check_show_auth($user, $pass);
} else {
    rt_deny('unknown mount');
}

// =====================================================================
// Auth rules
// =====================================================================
function rt_check_main_auth(string $user, string $pass): void
{
    // (1) Primary path — cc_pref values configured via the Frontend.
    $expectedUser = rt_get_pref('live_stream_master_username') ?? '';
    $expectedPass = rt_get_pref('live_stream_master_password') ?? '';

    if ($expectedUser !== ''
        && $user === $expectedUser
        && $pass === $expectedPass) {
        rt_allow('master via cc_pref');
    }

    // RASTATIME 2026-10-25 (role audit S5) - the built-in fallback login
    // source/master-secret is gone: it was valid next to every rotated
    // password.  The Harbor has its own configured fallback password.

    rt_deny('master credentials rejected');
}

function rt_check_show_auth(string $user, string $pass): void
{
    // RASTATIME 2026-10-25 (role audit S5) - built-in fallback login
    // source/show-secret removed (see rt_check_main_auth).

    $pdo = rt_db();

    // (1) Find the currently-running, unmodified show instance.
    //     modified_instance = TRUE marks deleted/edited ghost rows.
    $stmt = $pdo->prepare("
        SELECT id, instance_id AS show_instance_id, show_id
        FROM cc_show_instances
        WHERE starts <= (now() AT TIME ZONE 'UTC')
          AND ends   >  (now() AT TIME ZONE 'UTC')
          AND modified_instance = FALSE
        ORDER BY starts DESC
        LIMIT 1
    ");
    $stmt->execute();
    $instance = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$instance) {
        rt_deny('no active show — strict mode (Variant A)');
    }

    // (2) Fetch the show settings.
    $stmt = $pdo->prepare("
        SELECT live_stream_user, live_stream_pass,
               live_stream_using_custom_auth, live_stream_using_airtime_auth
        FROM cc_show WHERE id = ?
    ");
    $stmt->execute([$instance['show_id']]);
    $show = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$show) {
        rt_deny('show row missing');
    }

    // (3) Custom show-level credentials (plain comparison).
    if ($show['live_stream_using_custom_auth']
        && $user !== ''
        && $user === $show['live_stream_user']
        && $pass === $show['live_stream_pass']) {
        rt_allow('show via custom show creds');
    }

    // (4) LibreTime host user.  cc_subjs.pass is md5-hashed
    //     (Legacy LibreTime); compare md5($pass) === stored hash.
    if ($show['live_stream_using_airtime_auth']) {
        $stmt = $pdo->prepare("
            SELECT s.pass
            FROM cc_subjs AS s
            JOIN cc_show_hosts AS h ON h.subjs_id = s.id
            WHERE s.login   = ?
              AND h.show_id = ?
        ");
        $stmt->execute([$user, $instance['show_id']]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        if ($row && md5($pass) === $row['pass']) {
            rt_allow('show via libretime host user');
        }
    }

    rt_deny('show credentials rejected (or user not host of active show)');
}

// =====================================================================
// Helpers
// =====================================================================
function rt_db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO(
            'pgsql:host=localhost;port=5432;dbname=rastatime',
            'rastatime',
            'rastatime',
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
    }
    return $pdo;
}

function rt_get_pref(string $key): ?string
{
    $stmt = rt_db()->prepare('SELECT valstr FROM cc_pref WHERE keystr = ?');
    $stmt->execute([$key]);
    $v = $stmt->fetchColumn();
    return ($v === false) ? null : (string) $v;
}

function rt_allow(string $reason): void
{
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
