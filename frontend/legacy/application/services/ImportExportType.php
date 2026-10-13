<?php

/**
 * RASTATIME 2026-10-13 - one object type of the Import/Export bundle
 * (Section 23.52).  Each subclass knows its file in the bundle, how to
 * parse it into records, how to validate and create one record, and how
 * to export the current rows.
 *
 * A record is a plain array with at least 'line' (source line or index,
 * 1-based, for the preview) and 'name' (what the preview shows).  The
 * shared context ($ctx) carries the conflict mode, the user, the staged
 * logo files, the names that earlier rows of the same bundle will create
 * ('pending') and the ids created so far ('created').
 */
abstract class Application_Service_ImportExportType
{
    const STATUS_OK = 'ok';
    const STATUS_SKIP = 'skip';
    const STATUS_ERROR = 'error';

    /** @return string bundle key: webstreams | blocks | playlists | podcasts | shows */
    abstract public function type(): string;

    /** @return string file name inside the bundle (shows.csv, blocks.json, ...) */
    abstract public function fileName(): string;

    /** @return string translated label for the preview */
    abstract public function label(): string;

    /** @return string[] CSV columns in order (empty for JSON types) */
    abstract public function columns(): array;

    /** @return array example rows for the template (list of column => value) */
    abstract public function exampleRows(): array;

    /** @return string[] column descriptions for the README (column => text) */
    abstract public function columnHelp(): array;

    /**
     * Parse the file content into records.  Problems that make a line
     * unusable become an 'error' message on that record (not an exception),
     * so the preview can show them next to the other rows.
     *
     * @return array list of records
     */
    abstract public function parse(string $content): array;

    /**
     * @return array{status:string,messages:string[]} without touching the database
     */
    abstract public function validate(array $record, array &$ctx): array;

    /**
     * Create the object.  Called only for records the operator selected
     * after a successful validate() in the same run.
     *
     * @return array{status:string,messages:string[],id:?int}
     */
    abstract public function create(array $record, array &$ctx): array;

    /**
     * @param array<string,string> $files extra bundle files to add (e.g. logos/x.png => bytes)
     *
     * @return string the file content for fileName()
     */
    abstract public function export(array &$files): string;

    /** @return string[] notes shown above the preview and in the README */
    public function notices(): array
    {
        return [];
    }

    /** @return int number of rows that an export would contain (for the page) */
    abstract public function count(): int;

    // ------------------------------------------------------------------
    // helpers shared by the handlers
    // ------------------------------------------------------------------

    protected static function ok(array $messages = []): array
    {
        return ['status' => self::STATUS_OK, 'messages' => $messages];
    }

    protected static function skip(string $message): array
    {
        return ['status' => self::STATUS_SKIP, 'messages' => [$message]];
    }

    protected static function error($messages): array
    {
        return ['status' => self::STATUS_ERROR, 'messages' => is_array($messages) ? $messages : [$messages]];
    }

    /** yes/no/1/0/true/false/ja/nein -> bool; empty -> default */
    protected static function toBool($value, bool $default = false): bool
    {
        $v = strtolower(trim((string) $value));
        if ($v === '') {
            return $default;
        }

        return in_array($v, ['1', 'yes', 'y', 'true', 'ja', 'j', 'x', 'on'], true);
    }

    protected static function boolOut(bool $value): string
    {
        return $value ? 'yes' : 'no';
    }

    /** "a, b; c" -> ['a','b','c'] */
    protected static function splitList($value): array
    {
        $parts = preg_split('/[,;|]+/', (string) $value);
        $out = [];
        foreach ($parts as $p) {
            $p = trim($p);
            if ($p !== '') {
                $out[] = $p;
            }
        }

        return $out;
    }

    /** Postgres interval / "HH:MM:SS(.fff)" / "HH:MM" -> seconds */
    protected static function intervalToSeconds($value): int
    {
        $v = trim((string) $value);
        if ($v === '') {
            return 0;
        }
        if (preg_match('/^(\d+):(\d{1,2})(?::(\d{1,2})(?:\.\d+)?)?$/', $v, $m)) {
            return (int) $m[1] * 3600 + (int) $m[2] * 60 + (int) ($m[3] ?? 0);
        }
        if (preg_match('/^(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?$/i', $v, $m) && $v !== '') {
            return (int) ($m[1] ?? 0) * 3600 + (int) ($m[2] ?? 0) * 60 + (int) ($m[3] ?? 0);
        }

        return -1;
    }

    protected static function secondsToHms(int $seconds): string
    {
        $seconds = max(0, $seconds);

        return sprintf('%02d:%02d:%02d', intdiv($seconds, 3600), intdiv($seconds % 3600, 60), $seconds % 60);
    }

    /** The logged-in user's id (the creator of imported objects). */
    protected static function currentUserId(): int
    {
        $info = Zend_Auth::getInstance()->getStorage()->read();

        return isset($info->id) ? (int) $info->id : 0;
    }

    protected static function findPlaylistIdByName(string $name): ?int
    {
        if ($name === '') {
            return null;
        }
        $pl = CcPlaylistQuery::create()->filterByDbName($name)->orderByDbId()->findOne();

        return $pl ? (int) $pl->getDbId() : null;
    }

    protected static function findBlockIdByName(string $name): ?int
    {
        if ($name === '') {
            return null;
        }
        $bl = CcBlockQuery::create()->filterByDbName($name)->orderByDbId()->findOne();

        return $bl ? (int) $bl->getDbId() : null;
    }

    protected static function findWebstreamIdByName(string $name): ?int
    {
        if ($name === '') {
            return null;
        }
        $ws = CcWebstreamQuery::create()->filterByDbName($name)->orderByDbId()->findOne();

        return $ws ? (int) $ws->getDbId() : null;
    }

    protected static function findLineinIdByName(string $name): ?int
    {
        if ($name === '') {
            return null;
        }
        $con = Propel::getConnection();
        $st = $con->prepare('SELECT id FROM rastatime_linein WHERE name = :n AND enabled = TRUE ORDER BY id LIMIT 1');
        $st->execute([':n' => $name]);
        $id = $st->fetchColumn();

        return $id === false ? null : (int) $id;
    }

    protected static function findFileIdByPath(string $path): ?int
    {
        $path = trim(str_replace('\\', '/', $path));
        if ($path === '') {
            return null;
        }
        if (Application_Common_Storage::isAbsolute($path)) {
            $path = Application_Common_Storage::toRelative($path);
        }
        $path = ltrim($path, '/');
        $con = Propel::getConnection();
        $st = $con->prepare('SELECT id FROM cc_files WHERE filepath = :p AND file_exists = TRUE ORDER BY id LIMIT 1');
        $st->execute([':p' => $path]);
        $id = $st->fetchColumn();

        return $id === false ? null : (int) $id;
    }
}
