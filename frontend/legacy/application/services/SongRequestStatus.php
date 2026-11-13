<?php

/**
 * RASTATIME 2026-11-13 - read-only figures about song requests for the
 * Widgets -> Song Request page and the listener widget's search box.
 *
 * "Requestable" uses the same filter as the public catalogue
 * (`/api/v2/song-requests/search`): cc_files.requestable (kept in step
 * with the pool by RequestablePoolSyncTask), on disk, not disabled.
 */
class Application_Service_SongRequestStatus
{
    /** Tracks a listener can request right now. */
    public static function requestableCount(): int
    {
        try {
            return (int) Application_Common_Database::prepareAndExecute(
                'SELECT COUNT(*) FROM cc_files
                  WHERE requestable = true AND file_exists = true AND disabled = false',
                [],
                Application_Common_Database::COLUMN
            );
        } catch (Throwable $e) {
            Logging::warn('SongRequestStatus::requestableCount: ' . $e->getMessage());

            return 0;
        }
    }

    /**
     * Everything the settings page shows.
     *
     * @return array{pool: array<int, array{id: int, name: string}>, requestable: int,
     *               pending: int, queued: int, last_request: ?string,
     *               request_blocks: array<int, array{id: int, name: string}>,
     *               request_shows: string[], covers: bool}
     */
    public static function overview(): array
    {
        $DB = 'Application_Common_Database';
        $poolIds = Application_Model_Preference::getRequestablePoolBlockIds();
        $pool = [];
        if ($poolIds) {
            $rows = $DB::prepareAndExecute(
                'SELECT id, name FROM cc_block WHERE id IN (' . implode(',', array_map('intval', $poolIds)) . ') ORDER BY name',
                [],
                $DB::ALL
            );
            foreach ($rows as $r) {
                $pool[] = ['id' => (int) $r['id'], 'name' => (string) $r['name']];
            }
        }

        $counts = ['pending' => 0, 'queued' => 0];
        $last = null;
        try {
            foreach ($DB::prepareAndExecute(
                "SELECT status, COUNT(*) AS n FROM rastatime_song_request
                  WHERE status IN ('pending', 'queued') GROUP BY status",
                [],
                $DB::ALL
            ) as $r) {
                $counts[$r['status']] = (int) $r['n'];
            }
            // station time, minutes
            $last = $DB::prepareAndExecute(
                "SELECT to_char(MAX(created_at) AT TIME ZONE :tz, 'YYYY-MM-DD HH24:MI')
                   FROM rastatime_song_request",
                [':tz' => Application_Model_Preference::GetDefaultTimezone()],
                $DB::COLUMN
            ) ?: null;
        } catch (Throwable $e) {
            Logging::warn('SongRequestStatus::overview: ' . $e->getMessage());
        }

        // smart blocks with the "Use requests" criterion, and the shows whose
        // autoloading playlist holds one of them (= request shows)
        $blocks = [];
        foreach ($DB::prepareAndExecute(
            "SELECT DISTINCT b.id, b.name FROM cc_block b
               JOIN cc_blockcriteria c ON c.block_id = b.id
              WHERE c.criteria = 'use_requests' AND c.value = '1'
              ORDER BY b.name",
            [],
            $DB::ALL
        ) as $r) {
            $blocks[] = ['id' => (int) $r['id'], 'name' => (string) $r['name']];
        }
        $shows = [];
        if ($blocks) {
            $ids = implode(',', array_map(static fn ($b) => (int) $b['id'], $blocks));
            foreach ($DB::prepareAndExecute(
                "SELECT DISTINCT s.name FROM cc_show s
                   JOIN cc_playlistcontents pc ON pc.playlist_id = s.autoplaylist_id
                  WHERE COALESCE(s.has_autoplaylist, false) AND pc.block_id IN ({$ids})
                  ORDER BY s.name",
                [],
                $DB::ALL
            ) as $r) {
                $shows[] = (string) $r['name'];
            }
        }

        return [
            'pool' => $pool,
            'requestable' => self::requestableCount(),
            'pending' => $counts['pending'],
            'queued' => $counts['queued'],
            'last_request' => $last,
            'request_blocks' => $blocks,
            'request_shows' => $shows,
            // the widget's covers come from /api/track, which answers only
            // with Settings -> General -> Public RASTATIME API on
            'covers' => Application_Model_Preference::GetAllow3rdPartyApi() === '1',
        ];
    }
}
