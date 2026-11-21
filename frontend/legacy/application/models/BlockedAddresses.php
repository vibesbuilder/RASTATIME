<?php

/**
 * RASTATIME 2026-10-06 - the operator's view of the brute-force brakes.
 *
 * Three layers keep their own state:
 *   web       cc_login_attempts (per address) / cc_subjs (per user name),
 *             written by LoginController + Application_Model_LoginAttempts
 *   harbor    the playout's RejectThrottle (DJ dial-in), read and cleared
 *             over the loopback listener 127.0.0.1:8770
 *   firewall  Windows Firewall rules "RASTATIME-Block <ip>" created by the
 *             watcher script (infra/scripts/rt-firewall-watch.ps1); Apache
 *             runs as LocalSystem, so PowerShell may list and remove them
 *
 * listAll() merges them for the System Status page and rt-blocks.ps1,
 * unblock() clears one address (or one user name, key "user:<login>")
 * on every layer.
 */
class Application_Model_BlockedAddresses
{
    const PLAYOUT_BLOCKS_URL = 'http://127.0.0.1:8770/dj-auth/blocks';
    const PLAYOUT_UNBLOCK_URL = 'http://127.0.0.1:8770/dj-auth/unblock';
    const FIREWALL_PREFIX = 'RASTATIME-Block ';
    // RASTATIME 2026-11-21 - Unblock times for the firewall watcher
    const UNBLOCKED_FILE = 'unblocked.txt';
    const UNBLOCKED_KEEP_SECONDS = 172800;

    /**
     * @return array rows: layer (web|web-user|harbor|firewall), key,
     *               address, user, seconds_left (0 = counting only),
     *               count, detail
     */
    public static function listAll()
    {
        $rows = [];
        foreach (Application_Model_LoginAttempts::listWindows() as $w) {
            $rows[] = $w;
        }
        foreach (self::harborBlocks() as $h) {
            $rows[] = $h;
        }
        foreach (self::firewallBlocks() as $f) {
            $rows[] = $f;
        }

        return $rows;
    }

    /**
     * Clears the address (or "user:<login>") on every layer.
     *
     * @return array what happened per layer
     */
    public static function unblock($key)
    {
        $key = trim((string) $key);
        $result = ['key' => $key, 'web' => false, 'harbor' => false, 'firewall' => false];
        if ($key === '') {
            return $result;
        }
        if (strpos($key, 'user:') === 0) {
            $login = substr($key, 5);
            if ($login !== '') {
                Application_Model_Subjects::resetLoginAttempts($login);
                $result['web'] = true;
                Logging::info("blocked-addresses: operator cleared the login counter of user '{$login}'");
            }

            return $result;
        }
        if (!self::looksLikeAddress($key)) {
            return $result;
        }
        Application_Model_LoginAttempts::resetAttempts($key);
        $result['web'] = true;
        $result['harbor'] = self::harborUnblock($key);
        $result['firewall'] = self::firewallUnblock($key);
        $result['recorded'] = self::recordUnblock($key);
        Logging::info("blocked-addresses: operator unblocked {$key} (harbor "
            . ($result['harbor'] ? 'cleared' : 'nothing') . ', firewall '
            . ($result['firewall'] ? 'rule removed' : 'no rule') . ', watcher '
            . ($result['recorded'] ? 'told' : 'NOT told') . ')');

        return $result;
    }

    /** @return string path of unblocked.txt next to rastatime.conf (and allowlist.txt) */
    public static function unblockedPath()
    {
        return rtrim(dirname(RASTATIME_CONFIG_FILEPATH), '/\\') . DIRECTORY_SEPARATOR . self::UNBLOCKED_FILE;
    }

    /**
     * RASTATIME 2026-11-21 - tell the firewall watcher about an Unblock.  The
     * watcher counts the lines of the last hour; without this it found the
     * same old lines again on its next run (at most 5 min later) and blocked
     * the address once more - a DJ was cut off four times on 2026-11-21.
     * One line per address, "<address> <ISO time>"; the watcher ignores that
     * address's lines up to that time.  Lines older than two days (far beyond
     * the watcher's window) are dropped on every write.  A failed write never
     * fails the Unblock itself.
     *
     * @return bool true when the line is written
     */
    public static function recordUnblock($address, $path = null, $now = null)
    {
        if (!self::looksLikeAddress($address)) {
            return false;
        }
        $path = $path ?? self::unblockedPath();
        $now = $now ?? time();
        try {
            $keep = [];
            $old = is_file($path) ? @file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) : [];
            foreach ($old ?: [] as $line) {
                $parts = preg_split('/\s+/', trim($line), 2);
                if (count($parts) !== 2 || $parts[0] === $address) {
                    continue;
                }
                $at = strtotime($parts[1]);
                if ($at !== false && $now - $at <= self::UNBLOCKED_KEEP_SECONDS) {
                    $keep[] = $parts[0] . ' ' . $parts[1];
                }
            }
            $keep[] = $address . ' ' . date('c', $now);

            return @file_put_contents($path, implode("\n", $keep) . "\n", LOCK_EX) !== false;
        } catch (Throwable $e) {
            Logging::warn('blocked-addresses: cannot record the unblock for the watcher: ' . $e->getMessage());

            return false;
        }
    }

    public static function looksLikeAddress($value)
    {
        return filter_var($value, FILTER_VALIDATE_IP) !== false;
    }

    // ---- harbor (playout) -------------------------------------------------

    private static function harborBlocks()
    {
        $ctx = stream_context_create(['http' => ['method' => 'GET', 'timeout' => 1.0, 'ignore_errors' => true]]);
        $resp = @file_get_contents(self::PLAYOUT_BLOCKS_URL, false, $ctx);
        $data = $resp === false ? null : json_decode($resp, true);
        if (!is_array($data) || !isset($data['blocks']) || !is_array($data['blocks'])) {
            return [];
        }
        $rows = [];
        foreach ($data['blocks'] as $b) {
            $rows[] = [
                'layer' => 'harbor',
                'key' => (string) ($b['address'] ?? ''),
                'address' => (string) ($b['address'] ?? ''),
                'user' => '',
                'seconds_left' => (int) ($b['blocked_seconds_left'] ?? 0),
                'count' => (int) ($b['rejections_in_window'] ?? 0),
                'detail' => sprintf('%d/%d', (int) ($b['rejections_in_window'] ?? 0), (int) ($b['limit'] ?? 0)),
            ];
        }

        return $rows;
    }

    private static function harborUnblock($address)
    {
        $ctx = stream_context_create(['http' => [
            'method' => 'POST',
            'timeout' => 1.0,
            'ignore_errors' => true,
            'header' => "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => http_build_query(['address' => $address]),
        ]]);
        $resp = @file_get_contents(self::PLAYOUT_UNBLOCK_URL, false, $ctx);
        $data = $resp === false ? null : json_decode($resp, true);

        return is_array($data) && !empty($data['cleared']);
    }

    // ---- firewall (watcher rules) ------------------------------------------

    private static function firewallBlocks()
    {
        $cmd = 'powershell.exe -NoProfile -NonInteractive -Command "'
            . "Get-NetFirewallRule -DisplayName '" . self::FIREWALL_PREFIX . "*' -ErrorAction SilentlyContinue"
            . ' | Select-Object DisplayName, Description, Enabled | ConvertTo-Json -Compress"';
        $out = [];
        $code = 1;
        @exec($cmd, $out, $code);
        $json = trim(implode("\n", $out));
        if ($code !== 0 || $json === '') {
            return [];
        }
        $data = json_decode($json, true);
        if (!is_array($data)) {
            return [];
        }
        if (isset($data['DisplayName'])) {
            $data = [$data];   // a single rule is not wrapped in a list
        }
        $rows = [];
        foreach ($data as $rule) {
            $name = (string) ($rule['DisplayName'] ?? '');
            if (strpos($name, self::FIREWALL_PREFIX) !== 0) {
                continue;
            }
            $address = trim(substr($name, strlen(self::FIREWALL_PREFIX)));
            $desc = (string) ($rule['Description'] ?? '');
            $left = 0;
            if (preg_match('/until=([0-9T:\-+. ]+)/', $desc, $m)) {
                $until = strtotime(trim($m[1]));
                if ($until !== false) {
                    $left = max(0, $until - time());
                }
            }
            $rows[] = [
                'layer' => 'firewall',
                'key' => $address,
                'address' => $address,
                'user' => '',
                'seconds_left' => (int) $left,
                'count' => 0,
                'detail' => $desc,
            ];
        }

        return $rows;
    }

    private static function firewallUnblock($address)
    {
        if (!self::looksLikeAddress($address)) {
            return false;
        }
        $name = self::FIREWALL_PREFIX . $address;
        $cmd = 'powershell.exe -NoProfile -NonInteractive -Command "'
            . "if (Get-NetFirewallRule -DisplayName '" . $name . "' -ErrorAction SilentlyContinue) { "
            . "Remove-NetFirewallRule -DisplayName '" . $name . "'; 'removed' } else { 'none' }\"";
        $out = [];
        $code = 1;
        @exec($cmd, $out, $code);

        return $code === 0 && trim(implode('', $out)) === 'removed';
    }
}
