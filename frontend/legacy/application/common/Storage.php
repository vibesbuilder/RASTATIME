<?php

class Application_Common_Storage
{
    private static $rootCache = null;

    /**
     * RASTATIME 2026-09-16 - the effective storage root WITH a trailing
     * slash (the shape the configuration accessor always had): the site
     * preference `local_storage_folder` when set (Settings -> Local Machine
     * -> Media Library Location), else `storage.path` from rastatime.conf.
     * Cached per request.
     */
    public static function root()
    {
        if (self::$rootCache !== null) {
            return self::$rootCache;
        }
        $root = '';
        try {
            $root = trim((string) Application_Model_Preference::getLocalStorageFolder());
        } catch (Throwable $e) {
            $root = '';
        }
        if ($root === '') {
            $root = (string) Config::getStoragePath();
        }
        self::$rootCache = rtrim(str_replace('\\', '/', $root), '/') . '/';
        return self::$rootCache;
    }

    /** Decoded JSON of the move job state (cc_pref local_storage_move). */
    public static function moveState()
    {
        try {
            $raw = (string) Application_Model_Preference::getLocalStorageMoveState();
        } catch (Throwable $e) {
            return ['state' => 'idle'];
        }
        $data = $raw !== '' ? json_decode($raw, true) : null;
        return is_array($data) && !empty($data['state']) ? $data : ['state' => 'idle'];
    }

    public static function isMoving()
    {
        return in_array(self::moveState()['state'], ['copying', 'verifying'], true);
    }

    /** Imports and uploads must not write into a library that is being copied. */
    public static function assertNotMoving()
    {
        if (self::isMoving()) {
            throw new Exception('The media library is being moved - imports and uploads are paused until it is done.');
        }
    }

    public static function splitFilePath($p_filepath)
    {
        $storage_path = self::root();

        if (strpos($p_filepath, $storage_path) !== 0) {
            return null;
        }

        return [$storage_path, substr($p_filepath, strlen($storage_path))];
    }

    /**
     * RASTATIME 2026-09-16 - paths stored in the database are relative to the
     * storage root (forward slashes, no leading slash) so the root can move
     * (Settings -> Local Machine, stage 2).  An absolute path under the root
     * is converted; anything else is returned unchanged.
     */
    public static function toRelative($path)
    {
        if ($path === null || $path === '') {
            return $path;
        }
        $norm = str_replace('\\', '/', (string) $path);
        $root = rtrim(str_replace('\\', '/', (string) self::root()), '/') . '/';
        if (strncasecmp($norm, $root, strlen($root)) === 0) {
            $norm = substr($norm, strlen($root));
        }
        if (self::isAbsolute($norm)) {
            return $norm;                       // outside the root: keep as is
        }
        return ltrim($norm, '/');
    }

    /**
     * RASTATIME 2026-09-16 - the absolute path of a database path: a
     * root-relative value is joined with the storage root, an absolute value
     * (legacy rows, files outside the root) is returned unchanged.
     */
    public static function toAbsolute($path)
    {
        if ($path === null || $path === '') {
            return $path;
        }
        $norm = str_replace('\\', '/', (string) $path);
        if (self::isAbsolute($norm)) {
            return $norm;
        }
        return rtrim(str_replace('\\', '/', (string) self::root()), '/') . '/' . ltrim($norm, '/');
    }

    public static function isAbsolute($path)
    {
        return (bool) preg_match('#^([A-Za-z]:/|//|/)#', (string) $path)
            && !preg_match('#^/imported/#i', (string) $path);
    }
}
