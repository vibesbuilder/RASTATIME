<?php

/**
 * RASTATIME 2026-11-08 - Analytics -> Music by Country (operator go
 * 2026-11-08, ARCHITECTURE 23.100): where the music that aired in a year
 * comes from, the station's "music quota".
 *
 * Basis: the playout history (cc_playout_history, one row per aired
 * schedule row with its actual start and end) of tracks whose track type
 * has the code 'music'.  Tracks of any other type or without a type do not
 * count.  The country is the track's country column (migration 0081, read
 * from the COUNTRY tag on import, editable in Edit Track), as it is today -
 * a later correction counts for past plays too.  A track without a country
 * counts as "No country".  A country written as a combination
 * ("Germany/Switzerland") is a row of its own (operator 2026-11-08).
 *
 * Not in the history and so not counted: music DJs play live, line-ins and
 * webstreams, and plays of tracks that were deleted since.
 */
class Application_Service_MusicCountryReportService
{
    public const UNTAGGED_LIMIT = 25;

    /** Years from the first history row to the current one, newest first. */
    public static function years(): array
    {
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone() ?: 'UTC');
        $now = (int) (new DateTime('now', $tz))->format('Y');
        $first = $now;
        try {
            $min = Application_Common_Database::prepareAndExecute(
                'SELECT min(starts) AS m FROM cc_playout_history',
                [],
                Application_Common_Database::SINGLE
            );
            if ($min && $min['m']) {
                $first = (int) (new DateTime($min['m'], new DateTimeZone('UTC')))->setTimezone($tz)->format('Y');
            }
        } catch (Exception $e) {
            Logging::warn('MusicCountryReportService::years: ' . $e->getMessage());
        }

        return range($now, min($first, $now));
    }

    /**
     * Music by country of one year (station time).
     *
     * Returns ['year', 'ready' => country column present, 'music_type' =>
     * the type name or null, 'rows' => per country (country or null, plays,
     * minutes, share_plays, share_minutes) by minutes, "No country" last,
     * 'months' => 1..12 (plays, minutes, minutes_tagged, share_tagged),
     * 'matrix' => country => 1..12 minutes (for the CSV), 'totals' => (plays,
     * minutes, countries, plays_tagged, minutes_tagged, share_tagged,
     * first_play), 'untagged' => the most played music tracks without a
     * country (id, title, artist, plays, minutes)].  Minutes are rounded
     * per row from the summed seconds; the shares are of the summed seconds
     * and plays.
     */
    public static function report(int $year): array
    {
        $tzName = Application_Model_Preference::GetTimezone() ?: 'UTC';
        $tz = new DateTimeZone($tzName);
        $utc = new DateTimeZone('UTC');
        $from = (new DateTime(sprintf('%04d-01-01 00:00:00', $year), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');
        $to = (new DateTime(sprintf('%04d-01-01 00:00:00', $year + 1), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');
        $ready = Application_Model_StoredFile::fileColumnReady('country');

        $out = ['year' => $year, 'ready' => $ready, 'music_type' => null, 'rows' => [], 'months' => [], 'matrix' => [],
            'untagged' => [], 'totals' => [
                'plays' => 0, 'minutes' => 0, 'countries' => 0, 'plays_tagged' => 0, 'minutes_tagged' => 0,
                'share_tagged' => 0.0, 'first_play' => null,
            ]];
        for ($m = 1; $m <= 12; ++$m) {
            $out['months'][$m] = ['plays' => 0, 'minutes' => 0, 'minutes_tagged' => 0, 'share_tagged' => 0.0];
        }
        $type = Application_Common_Database::prepareAndExecute(
            "SELECT type_name FROM cc_track_types WHERE code = 'music' ORDER BY id LIMIT 1",
            [],
            Application_Common_Database::SINGLE
        );
        if (!$type) {
            return $out;
        }
        $out['music_type'] = (string) $type['type_name'];

        $country = $ready ? "NULLIF(TRIM(f.country), '')" : 'NULL::text';
        $base = "WITH plays AS (
                    SELECT f.id AS file_id, {$country} AS country, h.starts,
                           GREATEST(EXTRACT(EPOCH FROM (h.ends - h.starts)), 0) AS secs,
                           EXTRACT(MONTH FROM ((h.starts AT TIME ZONE 'UTC') AT TIME ZONE :tz))::int AS month
                      FROM cc_playout_history h
                      JOIN cc_files f ON f.id = h.file_id
                      JOIN cc_track_types tt ON tt.id = f.track_type_id
                     WHERE tt.code = 'music'
                       AND h.starts >= :from AND h.starts < :to
                 )";
        $params = [':tz' => $tzName, ':from' => $from, ':to' => $to];

        $cells = Application_Common_Database::prepareAndExecute(
            $base . ' SELECT country, month, count(*) AS plays, SUM(secs) AS secs, min(starts) AS first_play
                        FROM plays GROUP BY country, month',
            $params,
            'all'
        );
        $byCountry = [];
        $secsTotal = 0.0;
        $secsTagged = 0.0;
        $monthSecs = array_fill(1, 12, 0.0);
        $monthTagged = array_fill(1, 12, 0.0);
        foreach ($cells as $c) {
            $key = $c['country'] === null ? '' : (string) $c['country'];
            $month = (int) $c['month'];
            $secs = (float) $c['secs'];
            $plays = (int) $c['plays'];
            $byCountry[$key]['plays'] = ($byCountry[$key]['plays'] ?? 0) + $plays;
            $byCountry[$key]['secs'] = ($byCountry[$key]['secs'] ?? 0.0) + $secs;
            $byCountry[$key]['months'][$month] = ($byCountry[$key]['months'][$month] ?? 0.0) + $secs;
            $out['totals']['plays'] += $plays;
            $secsTotal += $secs;
            $monthSecs[$month] += $secs;
            $out['months'][$month]['plays'] += $plays;
            if ($key !== '') {
                $out['totals']['plays_tagged'] += $plays;
                $secsTagged += $secs;
                $monthTagged[$month] += $secs;
            }
            if ($out['totals']['first_play'] === null || $c['first_play'] < $out['totals']['first_play']) {
                $out['totals']['first_play'] = $c['first_play'];
            }
        }
        if ($out['totals']['first_play'] !== null) {
            $out['totals']['first_play'] = (new DateTime($out['totals']['first_play'], $utc))->setTimezone($tz)->format('Y-m-d');
        }

        $share = static fn ($part, $whole) => $whole > 0 ? round(100 * $part / $whole, 1) : 0.0;
        uksort($byCountry, static function ($a, $b) use ($byCountry) {
            if ($a === '' || $b === '') {
                return $a === '' ? 1 : -1; // "No country" last
            }

            return [$byCountry[$b]['secs'], $a] <=> [$byCountry[$a]['secs'], $b];
        });
        foreach ($byCountry as $key => $v) {
            $out['rows'][] = [
                'country' => $key === '' ? null : $key,
                'plays' => $v['plays'],
                'minutes' => (int) round($v['secs'] / 60),
                'share_plays' => $share($v['plays'], $out['totals']['plays']),
                'share_minutes' => $share($v['secs'], $secsTotal),
            ];
            $months = [];
            for ($m = 1; $m <= 12; ++$m) {
                $months[$m] = (int) round(($v['months'][$m] ?? 0) / 60);
            }
            $out['matrix'][$key] = $months;
        }
        $out['totals']['minutes'] = (int) round($secsTotal / 60);
        $out['totals']['minutes_tagged'] = (int) round($secsTagged / 60);
        $out['totals']['share_tagged'] = $share($secsTagged, $secsTotal);
        $out['totals']['countries'] = count(array_filter(array_keys($byCountry), static fn ($k) => $k !== ''));
        for ($m = 1; $m <= 12; ++$m) {
            $out['months'][$m]['minutes'] = (int) round($monthSecs[$m] / 60);
            $out['months'][$m]['minutes_tagged'] = (int) round($monthTagged[$m] / 60);
            $out['months'][$m]['share_tagged'] = $share($monthTagged[$m], $monthSecs[$m]);
        }

        $untagged = Application_Common_Database::prepareAndExecute(
            $base . ' SELECT p.file_id, f.track_title, f.artist_name, count(*) AS plays, SUM(p.secs) AS secs
                        FROM plays p JOIN cc_files f ON f.id = p.file_id
                       WHERE p.country IS NULL
                       GROUP BY p.file_id, f.track_title, f.artist_name
                       ORDER BY count(*) DESC, SUM(p.secs) DESC, p.file_id
                       LIMIT ' . self::UNTAGGED_LIMIT,
            $params,
            'all'
        );
        foreach ($untagged as $u) {
            $out['untagged'][] = [
                'id' => (int) $u['file_id'],
                'title' => (string) $u['track_title'],
                'artist' => (string) $u['artist_name'],
                'plays' => (int) $u['plays'],
                'minutes' => (int) round(((float) $u['secs']) / 60),
            ];
        }

        return $out;
    }
}
