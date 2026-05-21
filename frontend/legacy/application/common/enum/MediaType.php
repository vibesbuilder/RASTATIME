<?php

final class MediaType
{
    public const __default = self::FILE;

    public const FILE = 1;
    public const PLAYLIST = 2;
    public const BLOCK = 3;
    public const WEBSTREAM = 4;
    public const PODCAST = 5;
    // RASTATIME 2026-05-12 — Line-In as a fifth library media type.
    public const LINEIN = 6;

    public static function getDefault()
    {
        return self::__default;
    }
}
