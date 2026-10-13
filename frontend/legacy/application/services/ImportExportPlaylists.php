<?php

/**
 * RASTATIME 2026-10-13 - playlists.csv (Section 23.52).
 *
 * Columns: name, description, items.  "items" lists the contents in
 * order, separated by "|": file:<library path>, block:<name>,
 * webstream:<name>, linein:<name>.  Cue points and fades come from the
 * file / the defaults, as when the item is dropped into a playlist.
 */
class Application_Service_ImportExportPlaylists extends Application_Service_ImportExportType
{
    /** item prefix => (library type for addAudioClips, cc_playlistcontents.type) */
    const KINDS = ['file' => 'audioclip', 'webstream' => 'stream', 'block' => 'block', 'linein' => 'linein'];

    public function type(): string
    {
        return 'playlists';
    }

    public function fileName(): string
    {
        return 'playlists.csv';
    }

    public function label(): string
    {
        return _('Playlists');
    }

    public function columns(): array
    {
        return ['name', 'description', 'items'];
    }

    public function columnHelp(): array
    {
        return [
            'name' => 'unique name (key)',
            'description' => 'free text',
            'items' => 'contents in order, separated by "|": file:<path below the library root> | block:<smart block name> | webstream:<name> | linein:<line-in name>',
        ];
    }

    public function exampleRows(): array
    {
        return [[
            'name' => 'Morning Show',
            'description' => 'Intro, news stream, music block',
            'items' => 'file:imported/Example Radio/StationID/Intro.mp3|webstream:BBC World Service|block:Morning Music',
        ]];
    }

    public function count(): int
    {
        return (int) CcPlaylistQuery::create()->count();
    }

    public function parse(string $content): array
    {
        $parsed = Application_Service_ImportExportService::csvParse($content);
        $records = [];
        foreach ($parsed['rows'] as $row) {
            $rec = ['line' => $row['line'], 'name' => $row['name'] ?? '', 'description' => $row['description'] ?? '', 'items' => [], '_errors' => []];
            if ($rec['name'] === '') {
                $rec['_errors'][] = _('name is empty');
            }
            $raw = trim((string) ($row['items'] ?? ''));
            if ($raw !== '') {
                foreach (explode('|', $raw) as $part) {
                    $part = trim($part);
                    if ($part === '') {
                        continue;
                    }
                    $pos = strpos($part, ':');
                    $kind = $pos === false ? '' : strtolower(trim(substr($part, 0, $pos)));
                    $ref = $pos === false ? '' : trim(substr($part, $pos + 1));
                    if (!isset(self::KINDS[$kind]) || $ref === '') {
                        $rec['_errors'][] = sprintf(_('item "%s" must be file:<path>, block:<name>, webstream:<name> or linein:<name>'), $part);
                        continue;
                    }
                    $rec['items'][] = ['kind' => $kind, 'ref' => $ref];
                }
            }
            $rec['summary'] = sprintf(_('%d items'), count($rec['items']));
            $records[] = $rec;
        }

        return $records;
    }

    /** @return array{0:array,1:string[]} resolved [[id, type], ...] and messages for unresolved items */
    private function resolveItems(array $record, array $ctx): array
    {
        $resolved = [];
        $messages = [];
        foreach ($record['items'] as $item) {
            $id = null;
            switch ($item['kind']) {
                case 'file':
                    $id = self::findFileIdByPath($item['ref']);
                    break;
                case 'webstream':
                    $id = $ctx['created']['webstreams'][$item['ref']] ?? self::findWebstreamIdByName($item['ref']);
                    if ($id === null && in_array($item['ref'], $ctx['pending']['webstreams'], true)) {
                        $id = 0;                       // created earlier in this import
                    }
                    break;
                case 'block':
                    $id = $ctx['created']['blocks'][$item['ref']] ?? self::findBlockIdByName($item['ref']);
                    if ($id === null && in_array($item['ref'], $ctx['pending']['blocks'], true)) {
                        $id = 0;
                    }
                    break;
                case 'linein':
                    $id = self::findLineinIdByName($item['ref']);
                    break;
            }
            if ($id === null) {
                $messages[] = sprintf(_('%s "%s" not found'), $item['kind'], $item['ref']);
                continue;
            }
            $resolved[] = [$id, self::KINDS[$item['kind']]];
        }

        return [$resolved, $messages];
    }

    public function validate(array $record, array &$ctx): array
    {
        $existing = self::findPlaylistIdByName($record['name']);
        if ($existing !== null && $ctx['conflict'] !== 'replace') {
            return self::skip(sprintf(_('a playlist named "%s" exists already'), $record['name']));
        }
        if (in_array($record['name'], $ctx['pending']['playlists'], true)) {
            return self::error(_('the same name appears twice in the file'));
        }
        [, $messages] = $this->resolveItems($record, $ctx);
        if ($messages) {
            return self::error($messages);
        }

        return self::ok($existing !== null ? [_('will replace the existing playlist and its contents')] : []);
    }

    public function create(array $record, array &$ctx): array
    {
        [$items, $messages] = $this->resolveItems($record, $ctx);
        if ($messages) {
            return self::error($messages);
        }
        foreach ($items as $it) {
            if ($it[0] === 0) {
                return self::error(_('a referenced object of this import was not created'));
            }
        }
        $existing = self::findPlaylistIdByName($record['name']);
        if ($existing !== null) {
            $pl = new Application_Model_Playlist($existing);
            $pl->deleteAllFilesFromPlaylist();
        } else {
            $pl = new Application_Model_Playlist();
            $pl->setName($record['name']);
            $pl->setCreator($ctx['userId']);
        }
        $pl->setDescription($record['description']);
        if ($items) {
            $pl->addAudioClips($items);
        }

        return ['status' => self::STATUS_OK, 'messages' => [$existing !== null ? _('replaced') : _('created')], 'id' => (int) $pl->getId()];
    }

    public function export(array &$files): string
    {
        $con = Propel::getConnection();
        $sql = <<<'SQL'
            SELECT p.id, p.name, p.description,
                   pc.position, pc.type,
                   f.filepath, ws.name AS ws_name, bl.name AS bl_name, li.name AS li_name
              FROM cc_playlist p
         LEFT JOIN cc_playlistcontents pc ON pc.playlist_id = p.id
         LEFT JOIN cc_files f ON f.id = pc.file_id
         LEFT JOIN cc_webstream ws ON ws.id = pc.stream_id
         LEFT JOIN cc_block bl ON bl.id = pc.block_id
         LEFT JOIN rastatime_linein li ON li.id = pc.linein_id
             ORDER BY lower(p.name), p.id, pc.position
SQL;
        $rows = [];
        foreach ($con->query($sql)->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $id = (int) $r['id'];
            if (!isset($rows[$id])) {
                $rows[$id] = ['name' => $r['name'], 'description' => (string) $r['description'], '_items' => []];
            }
            if ($r['position'] === null) {
                continue;
            }
            $item = null;
            switch ((int) $r['type']) {
                case 0: $item = $r['filepath'] !== null ? 'file:' . $r['filepath'] : null; break;
                case 1: $item = $r['ws_name'] !== null ? 'webstream:' . $r['ws_name'] : null; break;
                case 2: $item = $r['bl_name'] !== null ? 'block:' . $r['bl_name'] : null; break;
                case 3: $item = $r['li_name'] !== null ? 'linein:' . $r['li_name'] : null; break;
            }
            if ($item !== null) {
                $rows[$id]['_items'][] = $item;
            }
        }
        $out = [];
        foreach ($rows as $r) {
            $out[] = ['name' => $r['name'], 'description' => $r['description'], 'items' => implode('|', $r['_items'])];
        }

        return Application_Service_ImportExportService::csvBuild($this->columns(), $out);
    }
}
