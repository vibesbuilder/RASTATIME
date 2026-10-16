<?php

/**
 * RASTATIME 2026-10-13 - blocks.json (Section 23.56).
 *
 * Smart block criteria are a small tree (editor rows of rules, limit, sort,
 * switches), so this type travels as JSON, one object per block:
 *
 *   {"name": "...", "description": "...", "type": "dynamic"|"static",
 *    "limit": {"value": 20, "modifier": "items"|"minutes"|"hours"|"remaining"},
 *    "sort": "random"|"newest"|"oldest"|...,
 *    "repeat_tracks": false, "overflow_tracks": false, "only_unplayed": false,
 *    "only_with_expiry": false, "use_requests": false,
 *    "exclude_played_lately": false, "exclude_played_lately_hours": 0,
 *    "exclude_artists_played_lately": false, "exclude_artists_played_lately_hours": 0,
 *    "criteria": [{"group": 0, "field": "genre", "modifier": "is", "value": "Jazz", "extra": ""},
 *                 {"group": 1, "field": "utime", "modifier": "after", "value": "30", "unit": "day", "extra": ""}, ...]}
 *
 * A group is one row of the smart block editor.  Block::getListofFilesMeetCriteria
 * ORs rules of the same field within one group (the editor's "+" rows) and
 * ANDs everything else - different groups, and different fields even within
 * one group.
 *
 * Relative dates (utime/mtime/lptime with before/after/between) travel as a
 * whole number plus "unit" / "extra_unit", the editor's number field and
 * unit select; the database keeps "<n> <unit> ago".  Absolute dates travel in
 * the user's timezone, as the editor shows them; the database keeps UTC.
 *
 * Import feeds Application_Model_Block::saveSmartBlockCriteria with the
 * same name/value list the smart block editor posts, inside one transaction
 * per block (2026-10-14: storeCriteriaIntoDb deletes the old rules first, so
 * a failure half way used to leave a block without rules).
 */
class Application_Service_ImportExportBlocks extends Application_Service_ImportExportType
{
    const SWITCHES = ['repeat_tracks', 'overflow_tracks', 'only_unplayed', 'only_with_expiry', 'use_requests',
        'exclude_played_lately', 'exclude_artists_played_lately', ];
    const HOURS = ['exclude_played_lately_hours', 'exclude_artists_played_lately_hours'];
    const DATE_FIELDS = ['utime', 'mtime', 'lptime'];
    const RELATIVE = ['before', 'after', 'between'];
    const RANGE = ['between', 'is in the range'];
    const UNITS = ['minute', 'hour', 'day', 'week', 'month', 'year'];
    // "7", "7 day", "7 days", "7 day ago" (the stored form, and what exports before 2026-10-14 wrote)
    const RELATIVE_RE = '/^(\d+)(?:\s*(minute|hour|day|week|month|year)s?)?(?:\s+ago)?$/i';

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
            'criteria' => 'list of {"group": n, "field": "<criterion>", "modifier": "<modifier>", "value": "...", "extra": "..."}; extra is the second value of "between" and "is in the range"',
            'groups' => 'a group is one row of the smart block editor: rules with the same group AND the same field are alternatives (OR, the rows the editor\'s + button adds); everything else is combined with AND - different groups, and different fields even within one group. A field may appear in several groups, each with its own alternatives: (A or B) and (C or D)',
            'dates' => 'utime, mtime, lptime with before / after / between: a whole number in value (and extra) plus "unit" (and "extra_unit"): minute, hour, day, week, month or year, counted back from now; with the other modifiers: an absolute date YYYY-MM-DD or YYYY-MM-DD HH:MM:SS in your user timezone',
        ];
    }

    public function exampleRows(): array
    {
        return [[
            'name' => 'Morning Music',
            'description' => 'Pop or Electronic above 110 BPM, uploaded in the last 90 days',
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
                ['group' => 0, 'field' => 'genre', 'modifier' => 'is', 'value' => 'Electronic', 'extra' => ''],
                ['group' => 1, 'field' => 'bpm', 'modifier' => 'is greater than', 'value' => '110', 'extra' => ''],
                ['group' => 2, 'field' => 'utime', 'modifier' => 'after', 'value' => '90', 'unit' => 'day', 'extra' => ''],
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
        $map = BlockCriteria::criteriaMap();
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
                if (!isset($map[$field])) {
                    $rec['_errors'][] = sprintf(_('unknown criterion "%s"'), $field);
                    continue;
                }
                $modifier = strtolower(trim((string) ($c['modifier'] ?? '')));
                if ($modifier === '') {
                    $rec['_errors'][] = sprintf(_('criterion "%s" has no modifier'), $field);
                    continue;
                }
                if (!in_array($modifier, $map[$field]->getModifiers(), true)) {
                    $rec['_errors'][] = sprintf(_('criterion "%s": modifier "%s" does not fit this criterion'), $field, $modifier);
                    continue;
                }
                $rule = [
                    'group' => (int) ($c['group'] ?? 0),
                    'field' => $field,
                    'modifier' => $modifier,
                    'value' => trim((string) ($c['value'] ?? '')),
                    'extra' => in_array($modifier, self::RANGE, true) ? trim((string) ($c['extra'] ?? '')) : '',
                    'unit' => '',
                    'extra_unit' => '',
                ];
                $error = self::checkRule($rule, $c, $map[$field]);
                if ($error !== null) {
                    $rec['_errors'][] = $error;
                    continue;
                }
                // RASTATIME 2026-10-16 - teaser criteria travel by name / keyword
                if ($field === 'teaser_show') {
                    $showId = self::findShowIdByName($rule['value']);
                    if ($showId === null) {
                        $rec['_errors'][] = sprintf(_('criterion "teaser_show": unknown show "%s"'), $rule['value']);
                        continue;
                    }
                    $rule['value'] = (string) $showId;
                } elseif ($field === 'teaser_type' && !in_array($rule['value'], Application_Model_StoredFile::TEASER_TYPES, true)) {
                    $rec['_errors'][] = sprintf(_('criterion "teaser_type": "%s" is not show, today or tomorrow'), $rule['value']);
                    continue;
                } elseif ($field === 'teaser_fits' && $rule['value'] !== 'yes') {
                    $rec['_errors'][] = _('criterion "teaser_fits": the value must be "yes"');
                    continue;
                }
                $rec['criteria'][] = $rule;
            }
            if (count($rec['criteria']) > 100) {
                $rec['_errors'][] = _('at most 10 groups of 10 rules are supported');
            }
            $rec['summary'] = sprintf(_('%s, %d rules'), $rec['block_type'], count($rec['criteria']));
            $records[] = $rec;
        }

        return $records;
    }

    /**
     * The checks of the smart block editor (Application_Form_SmartBlockCriteria::isValid)
     * that would otherwise fail only at import time or at playout.  Splits a
     * relative date into number + unit.  Returns an error text or null.
     */
    private static function checkRule(array &$rule, array $c, BlockCriteria $criterion): ?string
    {
        $field = $rule['field'];
        $modifier = $rule['modifier'];
        $type = $criterion->type;
        $column = CcFilesPeer::getTableMap()->getColumnByPhpName($criterion->peer);
        $size = $column->getType() === PropelColumnTypes::VARCHAR ? (int) $column->getSize() : 0;
        $maxLength = $size > 0 ? min(512, $size) : 512;     // cc_blockcriteria.value / extra are VARCHAR(512)
        if ($rule['value'] === '') {
            return sprintf(_('criterion "%s" has an empty value'), $field);
        }
        $keys = ['value' => 'unit'];
        if (in_array($modifier, self::RANGE, true)) {
            if ($rule['extra'] === '') {
                return sprintf(_('criterion "%s": modifier "%s" needs a second value in "extra"'), $field, $modifier);
            }
            $keys['extra'] = 'extra_unit';
        }
        foreach ($keys as $vk => $uk) {
            $v = $rule[$vk];
            if (mb_strlen($v) > $maxLength) {
                return sprintf(_('criterion "%s": the value is longer than %d characters'), $field, $maxLength);
            }
            if ($type === ModifierType::DATE && in_array($modifier, self::RELATIVE, true)) {
                $unit = rtrim(strtolower(trim((string) ($c[$uk] ?? ''))), 's');
                if (!preg_match(self::RELATIVE_RE, $v, $m)) {
                    return sprintf(_('criterion "%s": a relative date needs a whole number and a unit (minute, hour, day, week, month or year)'), $field);
                }
                $inline = strtolower($m[2] ?? '');
                if ($unit === '') {
                    $unit = $inline;
                }
                if (!in_array($unit, self::UNITS, true) || ($inline !== '' && $inline !== $unit)) {
                    return sprintf(_('criterion "%s": a relative date needs a whole number and a unit (minute, hour, day, week, month or year)'), $field);
                }
                $rule[$vk] = (string) (int) $m[1];
                $rule[$uk] = $unit;
            } elseif ($type === ModifierType::DATE) {
                $p = date_parse($v);
                if (!preg_match('/^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/', $v)
                    || $p['error_count'] > 0 || !checkdate((int) $p['month'], (int) $p['day'], (int) $p['year'])) {
                    return sprintf(_('criterion "%s": "%s" is not a date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'), $field, $v);
                }
            } elseif (in_array($field, ['length', 'cuein', 'cueout'], true)) {
                if (!preg_match('/^\d{2}:\d{2}:\d{2}/', $v)) {
                    return sprintf(_('criterion "%s": "%s" is not a duration (HH:MM:SS)'), $field, $v);
                }
            } elseif (in_array($type, [ModifierType::NUMBER, ModifierType::TRACK_TYPE], true) && !is_numeric($v)) {
                return sprintf(_('criterion "%s": "%s" is not a number'), $field, $v);
            }
        }

        return null;
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
                if ($c['unit'] !== '') {
                    $post[] = ['name' => "sp_criteria_datetime_select_{$g}_{$i}", 'value' => $c['unit']];
                }
                if ($c['extra'] !== '') {
                    $post[] = ['name' => "sp_criteria_extra_{$g}_{$i}", 'value' => $c['extra']];
                }
                if ($c['extra_unit'] !== '') {
                    $post[] = ['name' => "sp_criteria_extra_datetime_select_{$g}_{$i}", 'value' => $c['extra_unit']];
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
        // all or nothing: storeCriteriaIntoDb deletes the old rules before it
        // writes the new ones, and a new block row exists before its rules
        return self::atomically(function () use ($record, $ctx) {
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
        }, ['CcBlockPeer', 'CcBlockcriteriaPeer', 'CcPlaylistPeer', 'CcPlaylistcontentsPeer']);
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
                    $entry['criteria'][] = self::exportRule([
                        'group' => (int) ($r['criteria_group'] ?? 0),
                        'field' => (string) ($r['criteria'] ?? $field),
                        'modifier' => (string) ($r['modifier'] ?? ''),
                        'value' => (string) ($r['value'] ?? ''),
                        'extra' => (string) ($r['extra'] ?? ''),
                    ]);
                }
            }
            usort($entry['criteria'], static fn ($a, $b) => $a['group'] <=> $b['group']);
            $out[] = $entry;
        }

        return json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }

    /** RASTATIME 2026-10-16 - show id of an exact show name (first match by id). */
    private static function findShowIdByName(string $name): ?int
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT id FROM cc_show WHERE name = :n ORDER BY id LIMIT 1', [':n' => $name], Application_Common_Database::SINGLE
        );

        return $row ? (int) $row['id'] : null;
    }

    /** A stored date rule in the form the editor shows and the import reads. */
    private static function exportRule(array $rule): array
    {
        // RASTATIME 2026-10-16 - teaser_show is exported as the show's name
        if ($rule['field'] === 'teaser_show') {
            $row = Application_Common_Database::prepareAndExecute(
                'SELECT name FROM cc_show WHERE id = :id', [':id' => (int) $rule['value']], Application_Common_Database::SINGLE
            );
            $rule['value'] = $row ? (string) $row['name'] : $rule['value'];

            return $rule;
        }
        if (!in_array($rule['field'], self::DATE_FIELDS, true)) {
            return $rule;
        }
        if (!in_array($rule['modifier'], self::RELATIVE, true)) {
            foreach (['value', 'extra'] as $vk) {
                if ($rule[$vk] !== '') {
                    try {
                        $rule[$vk] = Application_Common_DateHelper::UTCStringToUserTimezoneString($rule[$vk]);
                    } catch (Exception $e) {
                        // left as stored; the preview of a re-import names it
                    }
                }
            }

            return $rule;
        }
        $out = ['group' => $rule['group'], 'field' => $rule['field'], 'modifier' => $rule['modifier']];
        foreach (['value' => 'unit', 'extra' => 'extra_unit'] as $vk => $uk) {
            $out[$vk] = $rule[$vk];
            if (preg_match(self::RELATIVE_RE, $rule[$vk], $m) && ($m[2] ?? '') !== '') {
                $out[$vk] = $m[1];
                $out[$uk] = strtolower($m[2]);
            }
        }

        return $out;
    }
}
