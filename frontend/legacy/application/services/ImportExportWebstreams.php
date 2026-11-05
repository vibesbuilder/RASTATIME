<?php

/**
 * RASTATIME 2026-10-13 - webstreams.csv (Section 23.56).
 *
 * Columns: name, description, url, length (HH:MM:SS), input_gain_db,
 * bridge_seconds, bridge_max_seconds (RASTATIME 2026-11-05, empty = default).
 * Import goes through Application_Model_Webstream::analyzeFormData (the
 * same URL probe the dialog runs) and ::save; the name is the key.
 */
class Application_Service_ImportExportWebstreams extends Application_Service_ImportExportType
{
    public function type(): string
    {
        return 'webstreams';
    }

    public function fileName(): string
    {
        return 'webstreams.csv';
    }

    public function label(): string
    {
        return _('Webstreams');
    }

    public function columns(): array
    {
        return ['name', 'description', 'url', 'length', 'input_gain_db', 'bridge_seconds', 'bridge_max_seconds'];
    }

    public function columnHelp(): array
    {
        return [
            'name' => 'unique name (key)',
            'description' => 'free text',
            'url' => 'stream or playlist URL (http/https, .m3u/.pls allowed) - probed on import like in the dialog',
            'length' => 'default length HH:MM:SS (used when the stream is scheduled)',
            'input_gain_db' => 'input gain in dB, e.g. -2 or 1.5; empty = 0',
            'bridge_seconds' => 'buffer before the stream starts to play, seconds; empty = default (5)',
            'bridge_max_seconds' => 'buffer maximum = added delay and reserve, seconds; empty = default (10)',
        ];
    }

    public function exampleRows(): array
    {
        return [[
            'name' => 'BBC World Service',
            'description' => 'News on the hour',
            'url' => 'http://stream.live.vc.bbcmedia.co.uk/bbc_world_service',
            'length' => '00:05:05',
            'input_gain_db' => '-2',
            'bridge_seconds' => '',
            'bridge_max_seconds' => '',
        ]];
    }

    public function count(): int
    {
        return (int) CcWebstreamQuery::create()->count();
    }

    public function parse(string $content): array
    {
        $parsed = Application_Service_ImportExportService::csvParse($content);
        $records = [];
        foreach ($parsed['rows'] as $row) {
            $rec = [
                'line' => $row['line'],
                'name' => $row['name'] ?? '',
                'description' => $row['description'] ?? '',
                'url' => $row['url'] ?? '',
                'length' => $row['length'] ?? '',
                'input_gain_db' => $row['input_gain_db'] ?? '',
                'bridge_seconds' => trim($row['bridge_seconds'] ?? ''),
                'bridge_max_seconds' => trim($row['bridge_max_seconds'] ?? ''),
                '_errors' => [],
            ];
            if ($rec['name'] === '') {
                $rec['_errors'][] = _('name is empty');
            }
            if ($rec['url'] === '' || !preg_match('#^https?://#i', $rec['url'])) {
                $rec['_errors'][] = _('url must start with http:// or https://');
            }
            $seconds = self::intervalToSeconds($rec['length']);
            if ($rec['length'] === '' || $seconds <= 0) {
                $rec['_errors'][] = _('length must be HH:MM:SS and greater than zero');
            }
            if ($rec['input_gain_db'] !== '' && !is_numeric(str_replace(',', '.', $rec['input_gain_db']))) {
                $rec['_errors'][] = _('input_gain_db must be a number');
            }
            foreach (['bridge_seconds', 'bridge_max_seconds'] as $col) {
                if ($rec[$col] !== '' && !is_numeric(str_replace(',', '.', $rec[$col]))) {
                    $rec['_errors'][] = $col . ' ' . _('must be a number of seconds');
                }
            }
            $rec['summary'] = $rec['url'];
            $records[] = $rec;
        }

        return $records;
    }

    private static function formParameters(array $record, int $id): array
    {
        $seconds = self::intervalToSeconds($record['length']);

        return [
            'id' => $id,
            'name' => $record['name'],
            'description' => $record['description'],
            'url' => $record['url'],
            'length' => sprintf('%02dh %02dm %02ds', intdiv($seconds, 3600), intdiv($seconds % 3600, 60), $seconds % 60),
            'input_gain_db' => $record['input_gain_db'] === '' ? '0' : str_replace(',', '.', $record['input_gain_db']),
            'bridge_seconds' => $record['bridge_seconds'] === '' ? null : (float) str_replace(',', '.', $record['bridge_seconds']),
            'bridge_max_seconds' => $record['bridge_max_seconds'] === '' ? null : (float) str_replace(',', '.', $record['bridge_max_seconds']),
        ];
    }

    public function validate(array $record, array &$ctx): array
    {
        $existing = self::findWebstreamIdByName($record['name']);
        if ($existing !== null && $ctx['conflict'] !== 'replace') {
            return self::skip(sprintf(_('a webstream named "%s" exists already'), $record['name']));
        }
        if (in_array($record['name'], $ctx['pending']['webstreams'], true)) {
            return self::error(_('the same name appears twice in the file'));
        }
        [$analysis] = Application_Model_Webstream::analyzeFormData(self::formParameters($record, $existing ?? -1));
        $messages = [];
        foreach ($analysis as $field => $info) {
            if (!$info[0]) {
                $messages[] = $field . ': ' . $info[1];
            }
        }
        if ($messages) {
            return self::error($messages);
        }

        return self::ok($existing !== null ? [_('will replace the existing webstream')] : []);
    }

    public function create(array $record, array &$ctx): array
    {
        $existing = self::findWebstreamIdByName($record['name']);
        $params = self::formParameters($record, $existing ?? -1);
        [$analysis, $mime, $mediaUrl, $di] = Application_Model_Webstream::analyzeFormData($params);
        foreach ($analysis as $field => $info) {
            if (!$info[0]) {
                return self::error($field . ': ' . $info[1]);
            }
        }
        $id = Application_Model_Webstream::save($params, $mime, $mediaUrl, $di);

        return ['status' => self::STATUS_OK, 'messages' => [$existing !== null ? _('replaced') : _('created')], 'id' => (int) $id];
    }

    public function export(array &$files): string
    {
        $con = Propel::getConnection();
        $st = $con->query('SELECT name, description, url, length, input_gain_db, bridge_seconds, bridge_max_seconds FROM cc_webstream ORDER BY lower(name)');
        $num = function ($v) { return $v === null ? '' : rtrim(rtrim(number_format((float) $v, 2, '.', ''), '0'), '.'); };
        $rows = [];
        foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $rows[] = [
                'name' => $r['name'],
                'description' => (string) $r['description'],
                'url' => $r['url'],
                'length' => self::secondsToHms(max(0, self::intervalToSeconds($r['length']))),
                'input_gain_db' => $num($r['input_gain_db']),
                'bridge_seconds' => $num($r['bridge_seconds']),
                'bridge_max_seconds' => $num($r['bridge_max_seconds']),
            ];
        }

        return Application_Service_ImportExportService::csvBuild($this->columns(), $rows);
    }
}
