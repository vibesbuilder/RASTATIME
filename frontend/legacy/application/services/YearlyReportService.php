<?php

/**
 * RASTATIME 2026-11-03 - Analytics -> Yearly Report: programme minutes of
 * the station's own productions (operator go 2026-11-03, for the reporting
 * to the authorities), next to the participants overview of the archiving
 * module (Application_Service_ArchivingService::participantsReport).
 *
 * "Own production" is a checkbox of the show (cc_show.own_production,
 * migration 0077).  Counted are the instances that aired in the year
 * (station time; ended by now, not deleted, no legacy rebroadcast) with
 * their scheduled duration; shows set up as "Repeat of another show"
 * (cc_show.repeat_of_show_id) are kept in a column of their own because
 * authorities usually report first broadcasts and repeats separately.
 *
 * The column is read through to_jsonb(cc_show) ->> 'own_production', which
 * is NULL until migration 0077 ran, so every reader works before and after
 * the migration (Propel classes are not regenerated).
 */
class Application_Service_YearlyReportService
{
    private static $columnReady;

    /** True once migration 0077 added cc_show.own_production. */
    public static function columnReady(): bool
    {
        if (self::$columnReady === null) {
            try {
                $row = Application_Common_Database::prepareAndExecute(
                    "SELECT 1 AS ok FROM information_schema.columns WHERE table_name = 'cc_show' AND column_name = 'own_production'",
                    [],
                    Application_Common_Database::SINGLE
                );
                self::$columnReady = !empty($row);
            } catch (Exception $e) {
                self::$columnReady = false;
            }
        }

        return self::$columnReady;
    }

    /** The show's "Own production" flag (false until the migration ran). */
    public static function ownProduction($showId): bool
    {
        $row = Application_Common_Database::prepareAndExecute(
            "SELECT (to_jsonb(s) ->> 'own_production') AS v FROM cc_show s WHERE s.id = :id",
            [':id' => (int) $showId],
            Application_Common_Database::SINGLE
        );

        return $row && in_array($row['v'], ['true', 't', '1'], true);
    }

    public static function setOwnProduction($showId, $value): void
    {
        if (!self::columnReady()) {
            if ($value) {
                Logging::warn('YearlyReportService::setOwnProduction: migration 0077 pending, flag not stored');
            }

            return;
        }
        Application_Common_Database::prepareAndExecute(
            'UPDATE cc_show SET own_production = ' . ($value ? 'TRUE' : 'FALSE') . ' WHERE id = :id',
            [':id' => (int) $showId],
            Application_Common_Database::EXECUTE
        );
    }

    /** Years from the first instance to the current one, newest first. */
    public static function years(): array
    {
        return Application_Service_ArchivingService::reportYears();
    }

    /**
     * Programme minutes of one year (station time).
     *
     * Returns ['year', 'rows' => per show (id, name, own_production, is_repeat,
     * episodes, minutes), 'months' => 1..12 (episodes, minutes_first,
     * minutes_repeat - own productions only), 'totals' => (shows_own,
     * episodes_own, minutes_first, minutes_repeat, minutes_own, minutes_other,
     * episodes_other)].  Minutes are rounded per show / month from the
     * summed seconds.
     */
    public static function minutesReport(int $year): array
    {
        $tzName = Application_Model_Preference::GetTimezone() ?: 'UTC';
        $tz = new DateTimeZone($tzName);
        $utc = new DateTimeZone('UTC');
        $from = (new DateTime(sprintf('%04d-01-01 00:00:00', $year), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');
        $to = (new DateTime(sprintf('%04d-01-01 00:00:00', $year + 1), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');

        $inst = "WITH inst AS (
                    SELECT si.id, si.show_id,
                           EXTRACT(EPOCH FROM (si.ends - si.starts)) AS secs,
                           EXTRACT(MONTH FROM ((si.starts AT TIME ZONE 'UTC') AT TIME ZONE :tz))::int AS month
                      FROM cc_show_instances si
                     WHERE si.modified_instance = FALSE
                       AND COALESCE(si.rebroadcast, 0) = 0
                       AND si.starts >= :from AND si.starts < :to
                       AND si.ends <= (now() AT TIME ZONE 'UTC')
                 ), shows AS (
                    SELECT s.id, s.name,
                           COALESCE((to_jsonb(s) ->> 'own_production')::boolean, FALSE) AS own_production,
                           (s.repeat_of_show_id IS NOT NULL) AS is_repeat
                      FROM cc_show s
                 )";
        $params = [':tz' => $tzName, ':from' => $from, ':to' => $to];

        $rows = Application_Common_Database::prepareAndExecute(
            $inst . " SELECT sh.id, sh.name, sh.own_production, sh.is_repeat,
                             count(i.id) AS episodes, ROUND(SUM(i.secs) / 60.0) AS minutes
                        FROM inst i JOIN shows sh ON sh.id = i.show_id
                       GROUP BY sh.id, sh.name, sh.own_production, sh.is_repeat
                       ORDER BY sh.own_production DESC, lower(sh.name), sh.id",
            $params,
            'all'
        );
        $months = Application_Common_Database::prepareAndExecute(
            $inst . " SELECT i.month, count(i.id) AS episodes,
                             ROUND(SUM(CASE WHEN sh.is_repeat THEN 0 ELSE i.secs END) / 60.0) AS minutes_first,
                             ROUND(SUM(CASE WHEN sh.is_repeat THEN i.secs ELSE 0 END) / 60.0) AS minutes_repeat
                        FROM inst i JOIN shows sh ON sh.id = i.show_id
                       WHERE sh.own_production
                       GROUP BY i.month ORDER BY i.month",
            $params,
            'all'
        );

        $out = ['year' => $year, 'rows' => [], 'months' => [], 'totals' => [
            'shows_own' => 0, 'episodes_own' => 0, 'minutes_first' => 0, 'minutes_repeat' => 0,
            'minutes_own' => 0, 'minutes_other' => 0, 'episodes_other' => 0,
        ]];
        foreach ($rows as $r) {
            $own = in_array($r['own_production'], [true, 't', '1', 'true'], true);
            $rep = in_array($r['is_repeat'], [true, 't', '1', 'true'], true);
            $row = [
                'id' => (int) $r['id'], 'name' => (string) $r['name'], 'own_production' => $own, 'is_repeat' => $rep,
                'episodes' => (int) $r['episodes'], 'minutes' => (int) $r['minutes'],
            ];
            $out['rows'][] = $row;
            if ($own) {
                ++$out['totals']['shows_own'];
                $out['totals']['episodes_own'] += $row['episodes'];
                $out['totals'][$rep ? 'minutes_repeat' : 'minutes_first'] += $row['minutes'];
            } else {
                $out['totals']['episodes_other'] += $row['episodes'];
                $out['totals']['minutes_other'] += $row['minutes'];
            }
        }
        $out['totals']['minutes_own'] = $out['totals']['minutes_first'] + $out['totals']['minutes_repeat'];
        $byMonth = [];
        foreach ($months as $m) {
            $byMonth[(int) $m['month']] = $m;
        }
        for ($m = 1; $m <= 12; ++$m) {
            $out['months'][$m] = [
                'episodes' => isset($byMonth[$m]) ? (int) $byMonth[$m]['episodes'] : 0,
                'minutes_first' => isset($byMonth[$m]) ? (int) $byMonth[$m]['minutes_first'] : 0,
                'minutes_repeat' => isset($byMonth[$m]) ? (int) $byMonth[$m]['minutes_repeat'] : 0,
            ];
        }

        return $out;
    }
}
