<?php

class Assets
{
    // RASTATIME 2026-08-31 (BACKLOG "Asset-Cache-Buster"): the upstream
    // implementation read the ?<hash> suffix from a static assets.json
    // generated once at build time — editing a css/js file never changed
    // its URL, and since Apache sends no Cache-Control/Expires for
    // static assets, browsers kept stale copies under heuristic caching
    // for days (operators had to hard-reload after every UI fix).
    //
    // The checksum is now derived from the live file's mtime + size, so
    // every edit yields a new URL on the next page load; unchanged files
    // keep a stable hash and stay cached.  One stat() per asset per
    // request (~30 links/page) is noise next to the un-opcached PHP
    // parse this stack already does.
    private static $cache = [];

    private static function getChecksum($path)
    {
        if (array_key_exists($path, self::$cache)) {
            return self::$cache[$path];
        }

        $file = dirname(APPLICATION_PATH) . '/public/' . $path;
        $stat = @stat($file);

        if ($stat === false) {
            // Same behaviour as the upstream missing-entry branch: log
            // loudly and return an uncacheable per-request value so a
            // broken path is noticed rather than pinned forever.
            Logging::error("Missing asset file for checksum: '{$path}'");

            return strval(time());
        }

        $sum = substr(md5($stat['mtime'] . ':' . $stat['size']), 0, 12);
        self::$cache[$path] = $sum;

        return $sum;
    }

    public static function url($path)
    {
        $base_url = Config::getBasePath();

        return $base_url . $path . '?' . self::getChecksum($path);
    }
}
