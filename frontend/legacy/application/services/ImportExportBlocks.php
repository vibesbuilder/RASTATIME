<?php

/**
 * RASTATIME 2026-10-13 - blocks.json (Section 23.52).
 *
 * Smart block criteria are a small tree (OR groups of rules, limit, sort,
 * switches), so this type travels as JSON, one object per block:
 *
 *   {"name": "...", "description": "...", "type": "dynamic"|"static",
 *    "limit": {"value": 20, "modifier": "items"|"minutes"|"hours"|"remaining"},
 *    "sort": "random"|"newest"|"oldest"|...,
 *    "repeat_tracks": false, "overflow_tracks": false, "only_unplayed": false,
 *    "only_with_expiry": false, "use_requests": false,
 *    "exclude_played_lately": false, "exclude_played_lately_hours": 0,
 *    "exclude_artists_played_lately": false, "exclude_artists_played_lately_hours": 0,
 *    "criteria": [{"group": 0, "field": "genre", "modifier": "is", "value": "Jazz", "extra": ""}, ...]}
 *
 * Import feeds Application_Model_Block::saveSmartBlockCriteria with the
 * same name/value list the smart block editor posts.
 */
class Application_Service_ImportExportBlocks extends Application_Service_ImportExportType
{
    const SWITCHES = ['repeat_tracks', 'overflow_tracks', 'only_unplayed', 'only_with_expiry', 'use_requests',
        'exclude_played_lately', 'exclude_artists_played_lately', ];
    const HOURS = ['exclude_played_lately_hours', 'exclude_artists_played_lately_hours'];

    public function type(): string
    {
        return 'blocks';
    }

    public function fileName(): string
    {
        return 'blocks.json';
    }

    public function label(): string
    {
        return _('Smart Blocks');
    }

    public function columns(): array
    {
        return [];
    }

    public function columnHelp(): array
    {
        return [
            'name' => 'unique name (key)',
            'type' => 'dynamic (criteria evaluated at playout) or static (contents generated in the editor)',
            'limit' => '{"value": n, "modifier": "items" | "minutes" | "hours" | "remaining"}',
            'sort' => 'random | newest | oldest | ... (as offered by the editor)',
            'switches' => implode(', ', self::SWITCHES) . ' (true/false); the two *_hours values are integers',
            'criteria' => 'list of {"group": n, "field": "<criterion>", "modifier": "<modifier>", "value": "...", "extra": "..."}; rules in the same group are ANDed, groups are ORed',
        ];
    }

    public function exampleRows(): array
    {
        return [[
            'name' => 'Morning Music',
            'description' => 'Up-tempo tracks, newest first',
            'type' => 'dynamic',
            'limit' => ['value' => 60, 'modifier' => 'minutes'],
            'sort' => 'random',
            'repeat_tracks' => false,
            'overflow_tracks' => false,
            'only_unplayed' => false,
            'only_with_expiry' => false,
            'use_requests' => false,
            'exclude_played_lately' => true,
            'exclude_played_lately_hours' => 24,
            'exclude_artists_played_lately' => false,
            'exclude_artists_played_lately_hours' => 0,
            'criteria' => [
                ['group' => 0, 'field' => 'genre', 'modifier' => 'is', 'value' => 'Pop', 'extra' => ''],
                ['group' => 0, 'field' => 'bpm', 'modifier' => 'is greater than', 'value' => '110', 'extra' => ''],
                ['group' => 1, 'field' => 'genre', 'modifier' => 'is', 'value' => 'Electronic', 'extra' => ''],
            ],
        ]];
    }

    public function count(): int
    {
        return (int) CcBlockQuery::create()->count();
    }

    public function parse(string $content): array
    {
        $data = json_decode(ltrim($content, "\xEF\xBB\xBF"), true);
        if (!is_array($data)) {
            return [['line' => 1, 'name' => basename($this->fileName()), '_errors' => [_('blocks.json is not a JSON list')], 'summary' => '']];
        }
        if (isset($data['name'])) {
            $data = [$data];                            // a single object is fine too
        }
        $known = array_keys(BlockCriteria::criteriaMap());
        $records = [];
        foreach (array_values($data) as $i => $b) {
            $rec = ['line' => $i + 1, 'name' => trim((string) ($b['name'] ?? '')), 'description' => (string) ($b['description'] ?? ''),
                'block_type' => strtolower((string) ($b['type'] ?? 'dynamic')), 'criteria' => [], 'etc' => [], '_errors' => [], ];
            if (!is_array($b)) {
                $rec['_errors'][] = _('entry is not an object');
                $records[] = $rec;
                continue;
            }
            if ($rec['name'] === '') {
                $rec['_errors'][] = _('name is empty');
            }
            if (!in_array($rec['block_type'], ['dynamic', 'static'], true)) {
                $rec['_errors'][] = _('type must be dynamic or static');
            }
            $limit = $b['limit'] ?? ['value' => 0, 'modifier' => 'items'];
            $rec['etc']['sp_type'] = $rec['block_type'] === 'static' ? '1' : '0';
            $rec['etc']['sp_limit_value'] = (string) (int) ($limit['value'] ?? 0);
            $rec['etc']['sp_limit_options'] = (string) ($limit['modifier'] ?? 'items');
            if (!in_array($rec['etc']['sp_limit_options'], ['items', 'minutes', 'hours', 'remaining'], true)) {
                $rec['_errors'][] = _('limit.modifier must be items, minutes, hours or remaining');
            }
            $rec['etc']['sp_sort_options'] = (string) ($b['sort'] ?? 'random');
            foreach (self::SWITCHES as $sw) {
                $rec['etc']['sp_' . $sw] = self::toBool($b[$sw] ?? false) ? '1' : '0';
            }
            foreach (self::HOURS as $hk) {
                $rec['etc']['sp_' . $hk] = (string) (int) ($b[$hk] ?? 0);
            }
            foreach (($b['criteria'] ?? []) as $c) {
                $field = (string) ($c['field'] ?? '');
                if (!in_array($field, $known, true)) {
                    $rec['_errors'][] = sprintf(_('unknown criterion "%s"'), $field);
                    continue;
                }
                if (trim((string) ($c['modifier'] ?? '')) === '') {
                    $rec['_errors'][] = sprintf(_('criterion "%s" has no modifier'), $field);
                    continue;
                }
                $rec['criteria'][] = [
                    'group' => (int) ($c['group'] ?? 0),
                    'field' => $field,
                    'modifier' => (string) $c['modifier'],
                    'value' => (string) ($c['value'] ?? ''),
                    'extra' => (string) ($c['extra'] ?? ''),
                ];
            }
            if (count($rec['criteria']) > 100) {
                $rec['_errors'][] = _('at most 10 groups of 10 rules are supported');
            }
            $rec['summary'] = sprintf(_('%s, %d rules'), $rec['block_type'], count($rec['criteria']));
            $records[] = $rec;
        }

        return $records;
    }

    /** The name/value list the smart block editor posts. */
    private static function criteriaPost(array $record): array
    {
        $post = [];
        $byGroup = [];
        foreach ($record['criteria'] as $c) {
            $byGroup[$c['group']][] = $c;
        }
        ksort($byGroup);
        $g = 0;
        foreach ($byGroup as $rules) {
            $i = 0;
            foreach ($rules as $c) {
                $post[] = ['name' => "sp_criteria_field_{$g}_{$i}", 'value' => $c['field']];
                $post[] = ['name' => "sp_criteria_modifier_{$g}_{$i}", 'value' => $c['modifier']];
                $post[] = ['name' => "sp_criteria_value_{$g}_{$i}", 'value' => $c['value']];
                if ($c['extra'] !== '') {
                    $post[] = ['name' => "sp_criteria_extra_{$g}_{$i}", 'value' => $c['extra']];
                }
                ++$i;
                if ($i > 9) {
                    break;
                }
            }
            ++$g;
            if ($g > 9) {
                break;
            }
        }
        foreach ($record['etc'] as $k => $v) {
            $post[] = ['name' => $k, 'value' => $v];
        }

        return $post;
    }

    public function validate(array $record, array &$ctx): array
    {
        $existing = self::findBlockIdByName($record['name']);
        if ($existing !== null && $ctx['conflict'] !== 'replace') {
            return self::skip(sprintf(_('a smart block named "%s" exists already'), $record['name']));
        }
        if (in_array($record['name'], $ctx['pending']['blocks'], true)) {
            return self::error(_('the same name appears twice in the file'));
        }

        return self::ok($existing !== null ? [_('will replace the existing block and its criteria')] : []);
    }

    public function create(array $record, array &$ctx): array
    {
        $existing = self::findBlockIdByName($record['name']);
        if ($existing !== null) {
            $bl = new Application_Model_Block($existing);
        } else {
            $bl = new Application_Model_Block();
            $bl->setName($record['name']);
            $bl->setCreator($ctx['userId']);
        }
        $bl->setDescription($record['description']);
        $bl->saveSmartBlockCriteria(self::criteriaPost($record));

        return ['status' => self::STATUS_OK, 'messages' => [$existing !== null ? _('replaced') : _('created')], 'id' => (int) $bl->getId()];
    }

    public function export(array &$files): string
    {
        $out = [];
        foreach (CcBlockQuery::create()->orderByDbName()->find() as $cc) {
            $bl = new Application_Model_Block($cc->getDbId());
            $crit = $bl->getCriteria();
            $entry = [
                'name' => $cc->getDbName(),
                'description' => (string) $cc->getDbDescription(),
                'type' => $cc->getDbType() === 'static' ? 'static' : 'dynamic',
                'limit' => ['value' => (int) ($crit['limit']['value'] ?? 0), 'modifier' => (string) ($crit['limit']['modifier'] ?? 'items')],
                'sort' => (string) ($crit['sort']['value'] ?? 'random'),
            ];
            foreach (self::SWITCHES as $sw) {
                $entry[$sw] = ((string) ($crit[$sw]['value'] ?? '0')) === '1';
            }
            foreach (self::HOURS as $hk) {
                $entry[$hk] = (int) ($crit[$hk]['value'] ?? 0);
            }
            $entry['criteria'] = [];
            foreach ($crit['crit'] ?? [] as $field => $rules) {
                foreach ($rules as $r) {
                    $entry['criteria'][] = [
                        'group' => (int) ($r['criteria_group'] ?? 0),
                        'field' => (string) ($r['criteria'] ?? $field),
                        'modifier' => (string) ($r['modifier'] ?? ''),
                        'value' => (string) ($r['value'] ?? ''),
                        'extra' => (string) ($r['extra'] ?? ''),
                    ];
                }
            }
            usort($entry['criteria'], static fn ($a, $b) => $a['group'] <=> $b['group']);
            $out[] = $entry;
        }

        return json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
}
