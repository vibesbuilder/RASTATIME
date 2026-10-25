<?php

/**
 * RASTATIME 2026-10-13 - Settings -> Import/Export (Section 23.56).
 *
 * One bundle, five object types, importable together or one at a time:
 *
 *   webstreams.csv   blocks.json   playlists.csv   podcasts.csv   shows.csv
 *   logos/<file>     show logos referenced by shows.csv
 *
 * Import runs in dependency order (webstreams -> smart blocks -> playlists
 * -> podcasts -> shows) because playlists reference streams and blocks,
 * and shows reference playlists.  The upload is staged in a temp folder
 * under a token; the preview validates every row without writing, the
 * operator ticks the rows, and the import re-validates each row right
 * before creating it (overlaps may have appeared meanwhile).
 *
 * The export writes the same files, so an export is a valid import.
 */
class Application_Service_ImportExportService
{
    /** Import order = dependency order. */
    // RASTATIME 2026-10-25 - users first: shows.csv names its DJs by login
    const ORDER = ['users', 'webstreams', 'blocks', 'playlists', 'podcasts', 'shows'];
    const LOGO_PREFIX = 'logos/';
    const TOKEN_TTL_SECONDS = 6 * 3600;

    /** @var Application_Service_ImportExportType[] type => handler */
    private static $handlers;

    /** @return Application_Service_ImportExportType[] type => handler, in import order */
    public static function handlers(): array
    {
        if (self::$handlers === null) {
            $list = [
                new Application_Service_ImportExportUsers(),
                new Application_Service_ImportExportWebstreams(),
                new Application_Service_ImportExportBlocks(),
                new Application_Service_ImportExportPlaylists(),
                new Application_Service_ImportExportPodcasts(),
                new Application_Service_ImportExportShows(),
            ];
            self::$handlers = [];
            foreach ($list as $h) {
                self::$handlers[$h->type()] = $h;
            }
        }

        return self::$handlers;
    }

    public static function handler(string $type): Application_Service_ImportExportType
    {
        $all = self::handlers();
        if (!isset($all[$type])) {
            throw new InvalidArgumentException("unknown import/export type '{$type}'");
        }

        return $all[$type];
    }

    // ------------------------------------------------------------------
    // CSV
    // ------------------------------------------------------------------

    /**
     * Parse CSV text into assoc rows keyed by the (lower-cased, trimmed)
     * header.  Delimiter auto-detected (; , or tab), UTF-8 BOM stripped,
     * CRLF tolerated.  Returns ['columns' => [...], 'rows' => [[line => n, ...]]].
     */
    public static function csvParse(string $text): array
    {
        if (substr($text, 0, 3) === "\xEF\xBB\xBF") {
            $text = substr($text, 3);
        }
        $text = str_replace("\r\n", "\n", $text);
        $lines = explode("\n", $text);
        // first non-empty line is the header
        $headerLine = '';
        $headerIndex = 0;
        foreach ($lines as $i => $l) {
            if (trim($l) !== '') {
                $headerLine = $l;
                $headerIndex = $i;
                break;
            }
        }
        $delim = ',';
        $best = substr_count($headerLine, ',');
        foreach ([';', "\t"] as $cand) {
            $n = substr_count($headerLine, $cand);
            if ($n > $best) {
                $best = $n;
                $delim = $cand;
            }
        }
        // re-read with fgetcsv semantics (quotes, embedded newlines)
        $fh = fopen('php://temp', 'r+');
        fwrite($fh, implode("\n", array_slice($lines, $headerIndex)));
        rewind($fh);
        $columns = fgetcsv($fh, 0, $delim, '"', '\\');
        $columns = array_map(static fn ($c) => strtolower(trim((string) $c)), $columns ?: []);
        $rows = [];
        $line = $headerIndex + 1;
        while (($cells = fgetcsv($fh, 0, $delim, '"', '\\')) !== false) {
            ++$line;
            if ($cells === [null] || (count($cells) === 1 && trim((string) $cells[0]) === '')) {
                continue;                               // blank line
            }
            $row = ['line' => $line];
            foreach ($columns as $i => $col) {
                if ($col === '') {
                    continue;
                }
                $row[$col] = isset($cells[$i]) ? trim((string) $cells[$i]) : '';
            }
            $rows[] = $row;
        }
        fclose($fh);

        return ['columns' => $columns, 'rows' => $rows];
    }

    /** Build CSV text (UTF-8 with BOM, ";" delimiter - opens cleanly in Excel). */
    public static function csvBuild(array $columns, array $rows): string
    {
        $fh = fopen('php://temp', 'r+');
        fputcsv($fh, $columns, ';', '"', '\\');
        foreach ($rows as $row) {
            $cells = [];
            foreach ($columns as $c) {
                $v = $row[$c] ?? '';
                $cells[] = is_bool($v) ? ($v ? 'yes' : 'no') : (string) $v;
            }
            fputcsv($fh, $cells, ';', '"', '\\');
        }
        rewind($fh);
        $text = stream_get_contents($fh);
        fclose($fh);

        return "\xEF\xBB\xBF" . str_replace("\n", "\r\n", $text);
    }

    // ------------------------------------------------------------------
    // staging (token folder under the system temp dir)
    // ------------------------------------------------------------------

    public static function tempRoot(): string
    {
        return rtrim(sys_get_temp_dir(), '/\\') . DIRECTORY_SEPARATOR . 'rastatime-importexport';
    }

    private static function tokenDir(string $token): string
    {
        if (!preg_match('/^[a-f0-9]{16}$/', $token)) {
            throw new InvalidArgumentException('bad token');
        }

        return self::tempRoot() . DIRECTORY_SEPARATOR . $token;
    }

    private static function cleanupStale(): void
    {
        $root = self::tempRoot();
        if (!is_dir($root)) {
            return;
        }
        foreach (glob($root . DIRECTORY_SEPARATOR . '*', GLOB_ONLYDIR) ?: [] as $dir) {
            if (filemtime($dir) < time() - self::TOKEN_TTL_SECONDS) {
                self::rmdirRecursive($dir);
            }
        }
    }

    private static function rmdirRecursive(string $dir): void
    {
        foreach (glob($dir . DIRECTORY_SEPARATOR . '{,.}*', GLOB_BRACE) ?: [] as $f) {
            $b = basename($f);
            if ($b === '.' || $b === '..') {
                continue;
            }
            is_dir($f) ? self::rmdirRecursive($f) : @unlink($f);
        }
        @rmdir($dir);
    }

    /**
     * Detect the type of a single (non-ZIP) upload: forced type, else the
     * file name, else the header columns.
     */
    private static function detectType(string $originalName, ?string $forcedType, string $content): ?string
    {
        $all = self::handlers();
        if ($forcedType && isset($all[$forcedType])) {
            return $forcedType;
        }
        $base = strtolower(basename(str_replace('\\', '/', $originalName)));
        foreach ($all as $type => $h) {
            if ($base === strtolower($h->fileName())) {
                return $type;
            }
        }
        $trim = ltrim($content, "\xEF\xBB\xBF \t\r\n");
        if ($trim !== '' && $trim[0] === '[') {
            return 'blocks';
        }
        $parsed = self::csvParse($content);
        $cols = $parsed['columns'];
        $bestType = null;
        $bestScore = 0;
        foreach ($all as $type => $h) {
            $want = $h->columns();
            if (!$want) {
                continue;
            }
            $score = count(array_intersect($want, $cols));
            if ($score > $bestScore) {
                $bestScore = $score;
                $bestType = $type;
            }
        }

        return $bestScore >= 2 ? $bestType : null;
    }

    /**
     * Stage an upload and run the preview.
     *
     * @return array{token:string,rows:array,notices:string[],files:string[]}
     */
    public function stageUpload(string $tmpPath, string $originalName, ?string $forcedType, string $conflict): array
    {
        self::cleanupStale();
        $token = bin2hex(random_bytes(8));
        $dir = self::tokenDir($token);
        if (!mkdir($dir, 0700, true) && !is_dir($dir)) {
            throw new RuntimeException('cannot create the staging folder ' . $dir);
        }
        $entries = [];
        if (Application_Common_Zip::isZip($tmpPath)) {
            $entries = Application_Common_Zip::extract($tmpPath);
        } else {
            $content = file_get_contents($tmpPath);
            $type = self::detectType($originalName, $forcedType, (string) $content);
            if ($type === null) {
                self::rmdirRecursive($dir);
                throw new RuntimeException(_('Cannot tell what this file contains. Name it like the template (users.csv, shows.csv, playlists.csv, webstreams.csv, podcasts.csv, blocks.json) or choose the type.'));
            }
            $entries[self::handler($type)->fileName()] = (string) $content;
        }

        $records = [];
        $files = [];
        $logos = [];
        $notices = [];
        $all = self::handlers();
        foreach ($entries as $name => $content) {
            $base = strtolower(basename($name));
            if (strpos(strtolower($name), self::LOGO_PREFIX) === 0 || preg_match('#(^|/)logos/#i', $name)) {
                $logoName = basename($name);
                if (!preg_match('/\.(jpe?g|png|gif|webp)$/i', $logoName)) {   // WebP since 2026-10-25
                    continue;                           // README.txt and the like
                }
                $logoDir = $dir . DIRECTORY_SEPARATOR . 'logos';
                if (!is_dir($logoDir)) {
                    mkdir($logoDir, 0700, true);
                }
                file_put_contents($logoDir . DIRECTORY_SEPARATOR . $logoName, $content);
                $logos[] = $logoName;
                continue;
            }
            $matched = false;
            foreach ($all as $type => $h) {
                if ($base === strtolower($h->fileName())) {
                    $records[$type] = $h->parse($content);
                    $files[] = $h->fileName();
                    $matched = true;
                    break;
                }
            }
            if (!$matched && $base !== 'readme.txt' && $base !== 'readme.md') {
                $notices[] = sprintf(_('Ignored file in the archive: %s'), $name);
            }
        }
        if (!$records) {
            self::rmdirRecursive($dir);
            throw new RuntimeException(_('The archive contains none of the known files (users.csv, shows.csv, playlists.csv, webstreams.csv, podcasts.csv, blocks.json).'));
        }
        $conflict = $conflict === 'replace' ? 'replace' : 'skip';
        file_put_contents($dir . DIRECTORY_SEPARATOR . 'bundle.json', json_encode([
            'records' => $records,
            'conflict' => $conflict,
            'logos' => $logos,
            'original' => basename($originalName),
            'staged_at' => date('c'),
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));

        // RASTATIME 2026-10-18 - the rows come back unchecked ('pending'): the
        // page validates them in batches (validateRows) and imports in batches
        // too.  A single request for 373 shows took > 120 s and mod_fcgid cut
        // it off (FcgidIOTimeout) while PHP went on creating shows.
        $preview = $this->pendingRows($bundleFor = ['records' => $records]);
        foreach ($all as $type => $h) {
            if (isset($records[$type])) {
                foreach ($h->notices() as $n) {
                    $notices[] = $n;
                }
            }
        }

        return ['token' => $token, 'rows' => $preview, 'notices' => array_values(array_unique($notices)), 'files' => $files, 'logos' => $logos];
    }

    private static function loadBundle(string $token): array
    {
        $file = self::tokenDir($token) . DIRECTORY_SEPARATOR . 'bundle.json';
        if (!is_file($file)) {
            throw new RuntimeException(_('The uploaded file is no longer staged - please upload it again.'));
        }
        $bundle = json_decode((string) file_get_contents($file), true);
        if (!is_array($bundle) || !isset($bundle['records'])) {
            throw new RuntimeException('staged bundle unreadable');
        }

        return $bundle;
    }

    private static function newContext(string $token, array $bundle): array
    {
        $logoDir = self::tokenDir($token) . DIRECTORY_SEPARATOR . 'logos';
        $logos = [];
        foreach ($bundle['logos'] ?? [] as $name) {
            $logos[$name] = $logoDir . DIRECTORY_SEPARATOR . $name;
        }

        return [
            'conflict' => $bundle['conflict'] ?? 'skip',
            'userId' => (int) (Zend_Auth::getInstance()->getStorage()->read()->id ?? 0),
            'logos' => $logos,
            'pending' => ['users' => [], 'webstreams' => [], 'blocks' => [], 'playlists' => [], 'podcasts' => [], 'shows' => []],
            'created' => ['users' => [], 'webstreams' => [], 'blocks' => [], 'playlists' => [], 'podcasts' => [], 'shows' => []],
        ];
    }

    /** Validate every staged record without writing. */
    /**
     * RASTATIME 2026-10-18 - every staged row with status 'pending' and no
     * messages, in import order; the page validates them in batches.
     */
    private function pendingRows(array $bundle): array
    {
        $rows = [];
        foreach (self::ORDER as $type) {
            if (!isset($bundle['records'][$type])) {
                continue;
            }
            $h = self::handler($type);
            foreach ($bundle['records'][$type] as $i => $record) {
                $rows[] = [
                    'id' => $type . ':' . $i,
                    'type' => $type,
                    'label' => $h->label(),
                    'line' => $record['line'] ?? ($i + 1),
                    'name' => $record['name'] ?? '',
                    'summary' => $record['summary'] ?? '',
                    'status' => 'pending',
                    'messages' => [],
                ];
            }
        }

        return $rows;
    }

    /**
     * RASTATIME 2026-10-18 - validate a batch of staged rows (ids like
     * "shows:12") in import order.  The names of the rows found ok so far
     * are kept in state.json of the staging folder, so a later batch sees a
     * playlist's block from an earlier batch as pending - as the one-shot
     * preview did.  Nothing is written to the database.
     */
    public function validateRows(string $token, array $ids): array
    {
        $bundle = self::loadBundle($token);
        $ctx = self::newContext($token, $bundle);
        $stateFile = self::tokenDir($token) . DIRECTORY_SEPARATOR . 'state.json';
        if (is_file($stateFile)) {
            $state = json_decode((string) file_get_contents($stateFile), true);
            if (is_array($state['pending'] ?? null)) {
                $ctx['pending'] = array_merge($ctx['pending'], $state['pending']);
            }
        }
        $wanted = array_fill_keys(array_map('strval', $ids), true);
        $rows = [];
        foreach (self::ORDER as $type) {
            if (!isset($bundle['records'][$type])) {
                continue;
            }
            $h = self::handler($type);
            foreach ($bundle['records'][$type] as $i => $record) {
                $id = $type . ':' . $i;
                if (!isset($wanted[$id])) {
                    continue;
                }
                $result = !empty($record['_errors'])
                    ? ['status' => Application_Service_ImportExportType::STATUS_ERROR, 'messages' => $record['_errors']]
                    : $h->validate($record, $ctx);
                if ($result['status'] === Application_Service_ImportExportType::STATUS_OK) {
                    $ctx['pending'][$type][] = $record['name'] ?? '';
                }
                $rows[] = [
                    'id' => $id,
                    'type' => $type,
                    'label' => $h->label(),
                    'line' => $record['line'] ?? ($i + 1),
                    'name' => $record['name'] ?? '',
                    'summary' => $record['summary'] ?? '',
                    'status' => $result['status'],
                    'messages' => $result['messages'],
                ];
            }
        }
        file_put_contents($stateFile, json_encode(['pending' => $ctx['pending']], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));

        return $rows;
    }

    public function preview(string $token): array
    {
        $bundle = self::loadBundle($token);
        $ctx = self::newContext($token, $bundle);
        $rows = [];
        foreach (self::ORDER as $type) {
            if (!isset($bundle['records'][$type])) {
                continue;
            }
            $h = self::handler($type);
            foreach ($bundle['records'][$type] as $i => $record) {
                $result = !empty($record['_errors'])
                    ? ['status' => Application_Service_ImportExportType::STATUS_ERROR, 'messages' => $record['_errors']]
                    : $h->validate($record, $ctx);
                if ($result['status'] === Application_Service_ImportExportType::STATUS_OK) {
                    $ctx['pending'][$type][] = $record['name'] ?? '';
                }
                $rows[] = [
                    'id' => $type . ':' . $i,
                    'type' => $type,
                    'label' => $h->label(),
                    'line' => $record['line'] ?? ($i + 1),
                    'name' => $record['name'] ?? '',
                    'summary' => $record['summary'] ?? '',
                    'status' => $result['status'],
                    'messages' => $result['messages'],
                ];
            }
        }

        return $rows;
    }

    /**
     * Create the selected rows (ids "type:index"), in dependency order,
     * re-validating each right before writing.
     */
    /**
     * @param bool $finish       remove the staging folder afterwards (false for all
     *                           but the last batch of a batched import)
     * @param bool $onlySelected return only the selected rows (batched import),
     *                           not every staged row with "not selected"
     */
    public function import(string $token, array $selected, bool $finish = true, bool $onlySelected = false): array
    {
        $bundle = self::loadBundle($token);
        $ctx = self::newContext($token, $bundle);
        $wanted = array_fill_keys(array_map('strval', $selected), true);
        $rows = [];
        foreach (self::ORDER as $type) {
            if (!isset($bundle['records'][$type])) {
                continue;
            }
            $h = self::handler($type);
            foreach ($bundle['records'][$type] as $i => $record) {
                $id = $type . ':' . $i;
                $row = ['id' => $id, 'type' => $type, 'label' => $h->label(), 'line' => $record['line'] ?? ($i + 1), 'name' => $record['name'] ?? ''];
                if (!isset($wanted[$id])) {
                    if ($onlySelected) {
                        continue;
                    }
                    $row['status'] = Application_Service_ImportExportType::STATUS_SKIP;
                    $row['messages'] = [_('not selected')];
                    $rows[] = $row;
                    continue;
                }
                try {
                    $check = !empty($record['_errors'])
                        ? ['status' => Application_Service_ImportExportType::STATUS_ERROR, 'messages' => $record['_errors']]
                        : $h->validate($record, $ctx);
                    if ($check['status'] !== Application_Service_ImportExportType::STATUS_OK) {
                        $row['status'] = $check['status'];
                        $row['messages'] = $check['messages'];
                        $rows[] = $row;
                        continue;
                    }
                    $result = $h->create($record, $ctx);
                    if ($result['status'] === Application_Service_ImportExportType::STATUS_OK && isset($result['id'])) {
                        $ctx['created'][$type][$record['name'] ?? ''] = $result['id'];
                        $ctx['pending'][$type][] = $record['name'] ?? '';
                    }
                    $row['status'] = $result['status'];
                    $row['messages'] = $result['messages'];
                    $row['created_id'] = $result['id'] ?? null;
                } catch (Exception $e) {
                    Logging::error('import/export: ' . $type . ' line ' . ($record['line'] ?? '?') . ': ' . $e->getMessage());
                    $row['status'] = Application_Service_ImportExportType::STATUS_ERROR;
                    $row['messages'] = [$e->getMessage()];
                }
                $rows[] = $row;
            }
        }
        if ($finish) {
            self::rmdirRecursive(self::tokenDir($token));
        }

        return $rows;
    }

    // ------------------------------------------------------------------
    // export / template
    // ------------------------------------------------------------------

    /**
     * @param string[] $types subset of ORDER
     *
     * @return array{filename:string,content:string,mime:string}
     */
    public function export(array $types): array
    {
        $types = array_values(array_intersect(self::ORDER, $types));
        if (!$types) {
            throw new InvalidArgumentException(_('Choose at least one type to export.'));
        }
        $files = [];
        foreach ($types as $type) {
            $h = self::handler($type);
            $files[$h->fileName()] = $h->export($files);
        }
        $stamp = date('Ymd-Hi');
        if (count($types) === 1 && count($files) === 1) {
            $h = self::handler($types[0]);
            $isJson = substr($h->fileName(), -5) === '.json';

            return [
                'filename' => preg_replace('/\.(csv|json)$/', '', $h->fileName()) . '-' . $stamp . ($isJson ? '.json' : '.csv'),
                'content' => $files[$h->fileName()],
                'mime' => $isJson ? 'application/json; charset=utf-8' : 'text/csv; charset=utf-8',
            ];
        }
        $files['README.txt'] = $this->readme($types, true);

        return [
            'filename' => 'rastatime-export-' . $stamp . '.zip',
            'content' => Application_Common_Zip::build($files),
            'mime' => 'application/zip',
        ];
    }

    /** A bundle with the headers, one example row per type and the README. */
    public function template(): array
    {
        $files = [];
        foreach (self::ORDER as $type) {
            $h = self::handler($type);
            if ($h->columns()) {
                $files[$h->fileName()] = self::csvBuild($h->columns(), $h->exampleRows());
            } else {
                $files[$h->fileName()] = json_encode($h->exampleRows(), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            }
        }
        $files['logos/README.txt'] = "Put the show logos referenced by shows.csv (column 'logo') into this folder.\r\n";
        $files['README.txt'] = $this->readme(self::ORDER, false);

        return [
            'filename' => 'rastatime-import-template.zip',
            'content' => Application_Common_Zip::build($files),
            'mime' => 'application/zip',
        ];
    }

    private function readme(array $types, bool $isExport): string
    {
        $out = [];
        $out[] = 'RASTATIME Import/Export bundle' . ($isExport ? ' (export of ' . date('Y-m-d H:i') . ')' : ' (template)');
        $out[] = '';
        $out[] = 'Upload this ZIP, or any single file of it, under Settings -> Import/Export.';
        $out[] = 'Files are imported in this order: users.csv, webstreams.csv, blocks.json, playlists.csv, podcasts.csv, shows.csv.';
        $out[] = 'CSV: UTF-8, first line = column names, delimiter ";" (also "," or TAB), yes/no for switches.';
        $out[] = 'Names are the keys: an object whose name already exists is skipped (or replaced, if you choose so).';
        $out[] = '';
        foreach ($types as $type) {
            $h = self::handler($type);
            $out[] = '== ' . $h->fileName() . ' (' . $h->label() . ')';
            foreach ($h->columnHelp() as $col => $help) {
                $out[] = '  ' . $col . ': ' . $help;
            }
            foreach ($h->notices() as $n) {
                $out[] = '  NOTE: ' . $n;
            }
            $out[] = '';
        }

        return implode("\r\n", $out) . "\r\n";
    }
}
