<?php

/**
 * RASTATIME 2026-10-18 - "Repeat of show": a show B that is the repeat of a
 * show A gets the content of A's last aired instance copied in shortly
 * before B starts (same lead as the autoloading build, which then fills the
 * remaining time).  Operator decisions 2026-10-18: fill shortly before the
 * start (not at A's end); the last ENDED instance of A, otherwise the
 * autoloading alone; tracks whose track type has "Copy into Repeats" off
 * (jingles, teasers) stay out; chains (C repeats B repeats A) are allowed,
 * loops are refused; a track that B still needs cannot be deleted.
 *
 * The columns come with legacy migration 0071 and are read / written with
 * raw SQL (Propel classes are not regenerated); every reader tolerates the
 * missing columns so the code can go live before the migration.
 */
class Application_Service_RepeatFillService
{
    /** Seconds before the start within which a repeat instance is filled. */
    public const LEAD_SECONDS = 3900; // 65 min: one pass ahead of the 60-min autoloading build

    /** Longest accepted chain when looking for a loop. */
    private const MAX_CHAIN = 50;

    private static $columnsReady;

    /** True once migration 0071 added cc_show.repeat_of_show_id. */
    public static function columnsReady(): bool
    {
        if (self::$columnsReady === null) {
            try {
                $row = Application_Common_Database::prepareAndExecute(
                    "SELECT 1 AS ok FROM information_schema.columns WHERE table_name = 'cc_show' AND column_name = 'repeat_of_show_id'",
                    [],
                    Application_Common_Database::SINGLE
                );
                self::$columnsReady = !empty($row);
            } catch (Exception $e) {
                self::$columnsReady = false;
            }
        }

        return self::$columnsReady;
    }

    /** The source show id of $showId, or null. */
    public static function getRepeatOf($showId): ?int
    {
        if (!self::columnsReady()) {
            return null;
        }
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT repeat_of_show_id FROM cc_show WHERE id = :id',
            [':id' => (int) $showId],
            Application_Common_Database::SINGLE
        );

        return ($row && $row['repeat_of_show_id'] !== null) ? (int) $row['repeat_of_show_id'] : null;
    }

    public static function setRepeatOf($showId, $sourceId): void
    {
        if (!self::columnsReady()) {
            if ($sourceId) {
                Logging::warn('RepeatFillService::setRepeatOf: migration 0071 pending, source not stored');
            }

            return;
        }
        $sourceId = (int) $sourceId;
        if ($sourceId > 0 && $sourceId === (int) $showId) {
            $sourceId = 0;
        }
        Application_Common_Database::prepareAndExecute(
            'UPDATE cc_show SET repeat_of_show_id = ' . ($sourceId > 0 ? ':src' : 'NULL') . ' WHERE id = :id',
            $sourceId > 0 ? [':src' => $sourceId, ':id' => (int) $showId] : [':id' => (int) $showId],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * True if making $sourceId the source of $showId would close a loop
     * (the chain starting at $sourceId reaches $showId).
     */
    public static function wouldLoop($showId, $sourceId): bool
    {
        $showId = (int) $showId;
        $cur = (int) $sourceId;
        for ($i = 0; $i < self::MAX_CHAIN && $cur > 0; ++$i) {
            if ($cur === $showId) {
                return true;
            }
            $cur = (int) self::getRepeatOf($cur);
        }

        return false;
    }

    /** True if a show with this id exists. */
    public static function showExists($showId): bool
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT 1 AS ok FROM cc_show WHERE id = :id',
            [':id' => (int) $showId],
            Application_Common_Database::SINGLE
        );

        return !empty($row);
    }

    /**
     * Options of the "Repeat of show" select: 0 => None, then every show that
     * has an upcoming instance or one within the last 60 days - a source has
     * usually aired already, so recent past instances count too.  Label: name plus the next start, else the last
     * one ("last ...").  $excludeId = the show being edited.
     */
    public static function sourceOptions($excludeId = null): array
    {
        $opts = [0 => _('None')];
        $sql = "SELECT s.id, s.name,
                       (SELECT MIN(i.starts) FROM cc_show_instances i
                         WHERE i.show_id = s.id AND i.modified_instance = FALSE AND i.ends > NOW() AT TIME ZONE 'UTC') AS next_start,
                       (SELECT MAX(i.starts) FROM cc_show_instances i
                         WHERE i.show_id = s.id AND i.modified_instance = FALSE AND i.ends <= NOW() AT TIME ZONE 'UTC') AS last_start
                  FROM cc_show s
                 WHERE EXISTS (SELECT 1 FROM cc_show_instances i WHERE i.show_id = s.id AND i.modified_instance = FALSE
                                  AND i.ends > (NOW() AT TIME ZONE 'UTC') - INTERVAL '60 days')
                 ORDER BY LOWER(s.name), s.id";
        try {
            $tz = new DateTimeZone(Application_Model_Preference::GetDefaultTimezone() ?: 'UTC');
            foreach (Application_Common_Database::prepareAndExecute($sql, [], 'all') as $r) {
                if ($excludeId && (int) $r['id'] === (int) $excludeId) {
                    continue;
                }
                $label = (string) $r['name'];
                $when = $r['next_start'] ?: $r['last_start'];
                if ($when) {
                    $dt = new DateTime($when, new DateTimeZone('UTC'));
                    $dt->setTimezone($tz);
                    $label .= $r['next_start']
                        ? ' (' . $dt->format('D H:i') . ')'
                        : ' (' . sprintf(_('last %s'), $dt->format('D d.m. H:i')) . ')';
                }
                $opts[(int) $r['id']] = $label;
            }
        } catch (Exception $e) {
            Logging::warn('RepeatFillService::sourceOptions: ' . $e->getMessage());
        }

        return $opts;
    }

    /** Source show name for a show id (export, messages). */
    public static function showName($showId): string
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT name FROM cc_show WHERE id = :id',
            [':id' => (int) $showId],
            Application_Common_Database::SINGLE
        );

        return $row ? (string) $row['name'] : '';
    }

    /** First show id with this name (case-insensitive), or null - import. */
    public static function findShowIdByName(string $name): ?int
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT id FROM cc_show WHERE lower(name) = lower(:n) ORDER BY id LIMIT 1',
            [':n' => trim($name)],
            Application_Common_Database::SINGLE
        );

        return $row ? (int) $row['id'] : null;
    }

    /** All (show id => source show id) pairs - export. */
    public static function allRepeatOf(): array
    {
        if (!self::columnsReady()) {
            return [];
        }
        $out = [];
        foreach (Application_Common_Database::prepareAndExecute(
            'SELECT id, repeat_of_show_id FROM cc_show WHERE repeat_of_show_id IS NOT NULL',
            [],
            'all'
        ) as $r) {
            $out[(int) $r['id']] = (int) $r['repeat_of_show_id'];
        }

        return $out;
    }

    /**
     * The instance a repeat instance was filled from, with the source show
     * name, its local start and the number of left-out rows - the View Show
     * dialog.  Null when the instance is no filled repeat.
     */
    public static function filledFrom($instanceId): ?array
    {
        if (!self::columnsReady()) {
            return null;
        }
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT b.filled_from_instance_id AS src, b.repeat_skipped AS skipped, a.starts AS src_starts, s.name AS src_name
               FROM cc_show_instances b
               JOIN cc_show_instances a ON a.id = b.filled_from_instance_id
               JOIN cc_show s ON s.id = a.show_id
              WHERE b.id = :id',
            [':id' => (int) $instanceId],
            Application_Common_Database::SINGLE
        );
        if (!$row) {
            return null;
        }

        return [
            'instance_id' => (int) $row['src'],
            'name' => (string) $row['src_name'],
            'starts' => new DateTime($row['src_starts'], new DateTimeZone('UTC')),
            'skipped' => (int) $row['skipped'],
        ];
    }

    /**
     * The repeat that still needs this media: a future, empty, not yet
     * filled instance of a show B whose source A aired the file / stream in
     * its last ended instance.  Returns [name, local start DateTime] or null.
     * Used by the delete guards (StoredFile::delete, Webstream::deleteStreams).
     */
    public static function neededByPendingRepeat($fileId = null, $streamId = null): ?array
    {
        if (!self::columnsReady() || (!$fileId && !$streamId)) {
            return null;
        }
        $col = $fileId ? 'sch.file_id' : 'sch.stream_id';
        $sql = "SELECT b.name, MIN(bi.starts) AS starts
                  FROM cc_schedule sch
                  JOIN cc_show_instances a ON a.id = sch.instance_id
                  JOIN cc_show b ON b.repeat_of_show_id = a.show_id
                  JOIN cc_show_instances bi ON bi.show_id = b.id
                 WHERE {$col} = :id
                   AND a.modified_instance = FALSE
                   AND a.ends <= now() AT TIME ZONE 'UTC'
                   AND a.id = (SELECT l.id FROM cc_show_instances l
                                WHERE l.show_id = a.show_id AND l.modified_instance = FALSE AND l.ends <= now() AT TIME ZONE 'UTC'
                                ORDER BY l.ends DESC LIMIT 1)
                   AND bi.modified_instance = FALSE
                   AND bi.rebroadcast = 0
                   AND bi.starts > now() AT TIME ZONE 'UTC'
                   AND bi.filled_from_instance_id IS NULL
                   AND NOT EXISTS (SELECT 1 FROM cc_schedule x WHERE x.instance_id = bi.id)
                 GROUP BY b.id, b.name
                 ORDER BY MIN(bi.starts)
                 LIMIT 1";
        $row = Application_Common_Database::prepareAndExecute(
            $sql,
            [':id' => (int) ($fileId ?: $streamId)],
            Application_Common_Database::SINGLE
        );
        if (!$row) {
            return null;
        }
        $starts = new DateTime($row['starts'], new DateTimeZone('UTC'));
        $starts->setTimezone(new DateTimeZone(Application_Model_Preference::GetDefaultTimezone() ?: 'UTC'));

        return ['name' => (string) $row['name'], 'starts' => $starts];
    }

    /** The message of the delete guard. */
    public static function neededMessage(array $info): string
    {
        return sprintf(
            _('Cannot delete: still needed for the repeat "%s" on %s.'),
            $info['name'],
            $info['starts']->format('Y-m-d H:i')
        );
    }

    /**
     * Fill the repeat instances that start within LEAD_SECONDS (the task).
     *
     * @return int number of instances filled
     */
    public static function fillDue(): int
    {
        if (!self::columnsReady()) {
            return 0;
        }
        $due = Application_Common_Database::prepareAndExecute(
            "SELECT b.id AS instance_id, b.starts, s.id AS show_id, s.name, s.repeat_of_show_id AS source_show_id
               FROM cc_show_instances b
               JOIN cc_show s ON s.id = b.show_id
              WHERE s.repeat_of_show_id IS NOT NULL
                AND b.modified_instance = FALSE
                AND b.rebroadcast = 0
                AND b.filled_from_instance_id IS NULL
                AND b.starts > now() AT TIME ZONE 'UTC'
                AND b.starts < (now() AT TIME ZONE 'UTC') + make_interval(secs => :lead)
                AND NOT EXISTS (SELECT 1 FROM cc_schedule x WHERE x.instance_id = b.id)
              ORDER BY b.starts",
            [':lead' => self::LEAD_SECONDS],
            'all'
        );
        $filled = 0;
        foreach ($due as $d) {
            $src = Application_Common_Database::prepareAndExecute(
                "SELECT id FROM cc_show_instances
                  WHERE show_id = :src AND modified_instance = FALSE AND rebroadcast = 0
                    AND ends <= now() AT TIME ZONE 'UTC' AND ends <= :starts
                  ORDER BY ends DESC LIMIT 1",
                [':src' => (int) $d['source_show_id'], ':starts' => $d['starts']],
                Application_Common_Database::SINGLE
            );
            if (!$src) {
                Logging::debug(sprintf(
                    'RepeatFillService: show "%s" (instance %d) - no ended instance of source show %d, autoloading only',
                    $d['name'], $d['instance_id'], $d['source_show_id']
                ));

                continue;
            }

            try {
                $filled += self::copyInstance((int) $src['id'], (int) $d['instance_id'], (string) $d['name']) ? 1 : 0;
            } catch (Throwable $e) {
                Logging::warn(sprintf(
                    'RepeatFillService: copy into instance %d of "%s" failed: %s',
                    $d['instance_id'], $d['name'], $e->getMessage()
                ));
            }
        }

        return $filled;
    }

    /**
     * Copy the rows of $srcInstanceId into the (empty) $dstInstanceId:
     * files and webstreams in their order with the aired cue / fade values,
     * line-ins (live input) and files whose track type has "Copy into
     * Repeats" off are left out, missing files are counted as skipped.
     */
    public static function copyInstance(int $srcInstanceId, int $dstInstanceId, string $label = ''): bool
    {
        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT sch.file_id, sch.stream_id, sch.linein_id, sch.clip_length, sch.cue_in, sch.cue_out, sch.fade_in, sch.fade_out,
                    f.file_exists, f.import_status, COALESCE(tt.repeat_copy, TRUE) AS repeat_copy
               FROM cc_schedule sch
               LEFT JOIN cc_files f ON f.id = sch.file_id
               LEFT JOIN cc_track_types tt ON tt.id = f.track_type_id
              WHERE sch.instance_id = :src
              ORDER BY sch.starts, sch.id',
            [':src' => $srcInstanceId],
            'all'
        );
        $files = [];
        $skipped = 0;
        $excluded = 0;
        $live = 0;
        foreach ($rows as $r) {
            if ($r['linein_id']) {
                ++$live;

                continue;
            }
            if ($r['file_id']) {
                if (!self::pg($r['repeat_copy'])) {
                    ++$excluded;

                    continue;
                }
                if (!self::pg($r['file_exists']) || (int) $r['import_status'] !== 0) {
                    ++$skipped;

                    continue;
                }
                $files[] = [
                    'type' => 0, 'id' => (int) $r['file_id'],
                    'cliplength' => $r['clip_length'], 'cuein' => $r['cue_in'], 'cueout' => $r['cue_out'],
                    'fadein' => $r['fade_in'], 'fadeout' => $r['fade_out'],
                ];
            } elseif ($r['stream_id']) {
                $files[] = [
                    'type' => 1, 'id' => (int) $r['stream_id'],
                    'cliplength' => $r['clip_length'], 'cuein' => $r['cue_in'], 'cueout' => $r['cue_out'],
                    'fadein' => $r['fade_in'], 'fadeout' => $r['fade_out'],
                ];
            }
        }

        if ($files) {
            $si = new Application_Model_ShowInstance($dstInstanceId);
            $si->addFilesAfter(0, $files);
        }
        Application_Common_Database::prepareAndExecute(
            'UPDATE cc_show_instances SET filled_from_instance_id = :src, repeat_skipped = :skipped WHERE id = :dst',
            [':src' => $srcInstanceId, ':skipped' => $skipped, ':dst' => $dstInstanceId],
            Application_Common_Database::EXECUTE
        );
        Logging::info(sprintf(
            'RepeatFillService: "%s" instance %d filled from instance %d - %d rows copied, %d excluded by track type, %d missing, %d live inputs left out',
            $label, $dstInstanceId, $srcInstanceId, count($files), $excluded, $skipped, $live
        ));

        return count($files) > 0;
    }

    private static function pg($v): bool
    {
        return $v === true || $v === 't' || $v === 1 || $v === '1' || $v === 'true';
    }
}
