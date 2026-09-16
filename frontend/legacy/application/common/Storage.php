<?php

class Application_Common_Storage
{
    public static function splitFilePath($p_filepath)
    {
        $storage_path = Config::getStoragePath();

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
        $root = rtrim(str_replace('\\', '/', (string) Config::getStoragePath()), '/') . '/';
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
        return rtrim(str_replace('\\', '/', (string) Config::getStoragePath()), '/') . '/' . ltrim($norm, '/');
    }

    public static function isAbsolute($path)
    {
        return (bool) preg_match('#^([A-Za-z]:/|//|/)#', (string) $path)
            && !preg_match('#^/imported/#i', (string) $path);
    }
}
