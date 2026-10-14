<?php

/**
 * RASTATIME 2026-10-13 - podcasts.csv (Section 23.56): subscribed feeds.
 *
 * Columns: url, title, auto_ingest, auto_expiry_enabled, auto_expiry_days,
 * album_override, default_track_type.  Episodes are not exported - the
 * feed delivers them again.  Import subscribes through
 * Application_Service_PodcastService::createFromFeedUrl (fetches the feed)
 * and then sets the ingest options.  The feed URL is the key.
 */
class Application_Service_ImportExportPodcasts extends Application_Service_ImportExportType
{
    public function type(): string
    {
        return 'podcasts';
    }

    public function fileName(): string
    {
        return 'podcasts.csv';
    }

    public function label(): string
    {
        return _('Podcasts');
    }

    public function columns(): array
    {
        return ['url', 'title', 'auto_ingest', 'auto_expiry_enabled', 'auto_expiry_days', 'album_override', 'default_track_type'];
    }

    public function columnHelp(): array
    {
        return [
            'url' => 'feed URL (key); the feed is fetched on import',
            'title' => 'informational - the feed title is used',
            'auto_ingest' => 'yes/no - download new episodes automatically',
            'auto_expiry_enabled' => 'yes/no - delete downloaded episodes after auto_expiry_days',
            'auto_expiry_days' => 'integer, only with auto_expiry_enabled',
            'album_override' => 'yes/no - use the podcast title as album',
            'default_track_type' => 'track type code (Settings -> Track Types), empty = none',
        ];
    }

    public function exampleRows(): array
    {
        return [[
            'url' => 'https://example.org/feed.xml',
            'title' => 'Example podcast',
            'auto_ingest' => 'yes',
            'auto_expiry_enabled' => 'yes',
            'auto_expiry_days' => '30',
            'album_override' => 'no',
            'default_track_type' => 'show',
        ]];
    }

    public function count(): int
    {
        return (int) ImportedPodcastQuery::create()->count();
    }

    public function parse(string $content): array
    {
        $parsed = Application_Service_ImportExportService::csvParse($content);
        $records = [];
        foreach ($parsed['rows'] as $row) {
            $rec = [
                'line' => $row['line'],
                'url' => $row['url'] ?? '',
                'name' => $row['title'] !== '' && isset($row['title']) ? $row['title'] : ($row['url'] ?? ''),
                'auto_ingest' => self::toBool($row['auto_ingest'] ?? '', true),
                'auto_expiry_enabled' => self::toBool($row['auto_expiry_enabled'] ?? ''),
                'auto_expiry_days' => (int) ($row['auto_expiry_days'] ?? 0),
                'album_override' => self::toBool($row['album_override'] ?? ''),
                'default_track_type' => trim((string) ($row['default_track_type'] ?? '')),
                '_errors' => [],
            ];
            if ($rec['url'] === '' || !preg_match('#^https?://#i', $rec['url'])) {
                $rec['_errors'][] = _('url must start with http:// or https://');
            }
            if ($rec['auto_expiry_enabled'] && $rec['auto_expiry_days'] < 1) {
                $rec['_errors'][] = _('auto_expiry_days must be at least 1 when auto_expiry_enabled is yes');
            }
            $rec['summary'] = $rec['url'];
            $records[] = $rec;
        }

        return $records;
    }

    private static function findPodcastIdByUrl(string $url): ?int
    {
        $con = Propel::getConnection();
        $st = $con->prepare('SELECT p.id FROM podcast p JOIN imported_podcast ip ON ip.podcast_id = p.id WHERE p.url = :u ORDER BY p.id LIMIT 1');
        $st->execute([':u' => $url]);
        $id = $st->fetchColumn();

        return $id === false ? null : (int) $id;
    }

    private static function trackTypeId(string $code): ?int
    {
        if ($code === '') {
            return null;
        }
        $con = Propel::getConnection();
        $st = $con->prepare('SELECT id FROM cc_track_types WHERE lower(code) = lower(:c) LIMIT 1');
        $st->execute([':c' => $code]);
        $id = $st->fetchColumn();

        return $id === false ? null : (int) $id;
    }

    public function validate(array $record, array &$ctx): array
    {
        $existing = self::findPodcastIdByUrl($record['url']);
        if ($existing !== null && $ctx['conflict'] !== 'replace') {
            return self::skip(_('this feed is subscribed already'));
        }
        if (in_array($record['url'], $ctx['pending']['podcasts'], true)) {
            return self::error(_('the same url appears twice in the file'));
        }
        if ($record['default_track_type'] !== '' && self::trackTypeId($record['default_track_type']) === null) {
            return self::error(sprintf(_('track type "%s" not found'), $record['default_track_type']));
        }

        return self::ok($existing !== null ? [_('will update the options of the existing subscription')] : [_('the feed is fetched on import')]);
    }

    private static function applyOptions(int $podcastId, array $record): void
    {
        $ip = ImportedPodcastQuery::create()->filterByDbPodcastId($podcastId)->findOne();
        if ($ip !== null) {
            $ip->setDbAutoIngest($record['auto_ingest']);
            $ip->setDbAlbumOverride($record['album_override']);
            $ip->save();
        }
        $con = Propel::getConnection();
        $st = $con->prepare('UPDATE imported_podcast SET auto_expiry_enabled = :e, auto_expiry_days = :d, default_track_type_id = :t WHERE podcast_id = :pid');
        $st->bindValue(':e', $record['auto_expiry_enabled'], PDO::PARAM_BOOL);
        $st->bindValue(':d', $record['auto_expiry_enabled'] ? $record['auto_expiry_days'] : null, $record['auto_expiry_enabled'] ? PDO::PARAM_INT : PDO::PARAM_NULL);
        $tt = self::trackTypeId($record['default_track_type']);
        $st->bindValue(':t', $tt, $tt === null ? PDO::PARAM_NULL : PDO::PARAM_INT);
        $st->bindValue(':pid', $podcastId, PDO::PARAM_INT);
        $st->execute();
    }

    public function create(array $record, array &$ctx): array
    {
        $existing = self::findPodcastIdByUrl($record['url']);
        if ($existing !== null) {
            self::applyOptions($existing, $record);

            return ['status' => self::STATUS_OK, 'messages' => [_('options updated')], 'id' => $existing];
        }
        try {
            $podcast = Application_Service_PodcastService::createFromFeedUrl($record['url']);
        } catch (Exception $e) {
            return self::error(sprintf(_('feed could not be subscribed: %s'), $e->getMessage()));
        }
        $id = (int) ($podcast['id'] ?? 0);
        if ($id <= 0) {
            return self::error(_('feed could not be subscribed'));
        }
        self::applyOptions($id, $record);

        return ['status' => self::STATUS_OK, 'messages' => [_('subscribed')], 'id' => $id];
    }

    public function export(array &$files): string
    {
        $con = Propel::getConnection();
        $sql = <<<'SQL'
            SELECT p.url, p.title, ip.auto_ingest, ip.auto_expiry_enabled, ip.auto_expiry_days, ip.album_override, tt.code AS track_type
              FROM podcast p
              JOIN imported_podcast ip ON ip.podcast_id = p.id
         LEFT JOIN cc_track_types tt ON tt.id = ip.default_track_type_id
             ORDER BY lower(p.title)
SQL;
        $rows = [];
        foreach ($con->query($sql)->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $rows[] = [
                'url' => $r['url'],
                'title' => (string) $r['title'],
                'auto_ingest' => self::boolOut($r['auto_ingest'] === true || $r['auto_ingest'] === 't' || $r['auto_ingest'] === '1'),
                'auto_expiry_enabled' => self::boolOut($r['auto_expiry_enabled'] === true || $r['auto_expiry_enabled'] === 't' || $r['auto_expiry_enabled'] === '1'),
                'auto_expiry_days' => $r['auto_expiry_days'] === null ? '' : (string) $r['auto_expiry_days'],
                'album_override' => self::boolOut($r['album_override'] === true || $r['album_override'] === 't' || $r['album_override'] === '1'),
                'default_track_type' => (string) ($r['track_type'] ?? ''),
            ];
        }

        return Application_Service_ImportExportService::csvBuild($this->columns(), $rows);
    }
}
