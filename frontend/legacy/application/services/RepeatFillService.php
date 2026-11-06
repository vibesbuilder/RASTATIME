<?php

/**
 * RASTATIME 2026-10-18 - "Repeat of show": a show B that is the repeat of a
 * show A gets the content of A's last aired instance copied in shortly
 * before B starts (same lead as the autoloading build, which then fills the
 * remaining time).  Operator decisions 2026-10-18: fill shortly before the
 * start (not at A's end); the last ENDED instance of A, otherwise the
 * autoloading alone; jingles are carried over like everything else (the
 * per-type "Copy into Repeats" flag was removed again the same day);
 * chains (C repeats B repeats A) are allowed,
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
    // RASTATIME 2026-10-20 - stage 2: a source with live rows waits for its
    // recording to be imported, but never closer than this to the repeat's start
    public const RECORDING_WAIT_MARGIN_SECONDS = 300;

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
     * has an instance still to come (or running), plus a show that has aired
     * within the last 60 days only if its last ended instance - the one
     * fillDue() would copy - repeats completely: tracks only, or its
     * recording is imported.  RASTATIME 2026-10-27 (operator): a past live
     * show without a recording is no longer offered; a source should be
     * chosen before it airs.  $keepId (the stored source of the show being
     * edited) is always listed, or saving the form would silently drop it.
     * Label: name plus the next start, else the last one ("last ...").
     * $excludeId = the show being edited.
     */
    public static function sourceOptions($excludeId = null, $keepId = null): array
    {
        $opts = [0 => _('None')];
        $sql = "SELECT s.id, s.name, n.next_start, l.starts AS last_start
                  FROM cc_show s
                  LEFT JOIN LATERAL (
                       SELECT MIN(i.starts) AS next_start FROM cc_show_instances i
                        WHERE i.show_id = s.id AND i.modified_instance = FALSE
                          AND i.ends > NOW() AT TIME ZONE 'UTC') n ON TRUE
                  LEFT JOIN LATERAL (
                       SELECT i.id, i.starts, i.ends, i.file_id FROM cc_show_instances i
                        WHERE i.show_id = s.id AND i.modified_instance = FALSE AND i.rebroadcast = 0
                          AND i.ends <= NOW() AT TIME ZONE 'UTC'
                        ORDER BY i.ends DESC LIMIT 1) l ON TRUE
                 WHERE n.next_start IS NOT NULL
                    OR s.id = :keep
                    OR (l.ends > (NOW() AT TIME ZONE 'UTC') - INTERVAL '60 days'
                        AND ((EXISTS (SELECT 1 FROM cc_schedule c WHERE c.instance_id = l.id)
                              AND NOT EXISTS (SELECT 1 FROM cc_schedule c WHERE c.instance_id = l.id
                                                 AND (c.linein_id IS NOT NULL OR c.stream_id IS NOT NULL)))
                             OR EXISTS (SELECT 1 FROM cc_files f WHERE f.id = l.file_id AND f.import_status = 0
                                           AND f.file_exists AND f.length > INTERVAL '0')))
                 ORDER BY LOWER(s.name), s.id";
        try {
            $tz = new DateTimeZone(Application_Model_Preference::GetDefaultTimezone() ?: 'UTC');
            foreach (Application_Common_Database::prepareAndExecute($sql, [':keep' => (int) $keepId], 'all') as $r) {
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
     * RASTATIME 2026-10-21 - (show id => source show name) of every repeat,
     * one query; the calendar feed marks repeats with their own icon.
     */
    public static function repeatSourceNames(): array
    {
        if (!self::columnsReady()) {
            return [];
        }
        $out = [];
        foreach (Application_Common_Database::prepareAndExecute(
            'SELECT s.id, src.name FROM cc_show s JOIN cc_show src ON src.id = s.repeat_of_show_id',
            [],
            'all'
        ) as $r) {
            $out[(int) $r['id']] = (string) $r['name'];
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
        // RASTATIME 2026-10-20 - stage 2: a file is also needed as the recording of
        // the source instance (a.file_id), which stands in for its live rows.
        // RASTATIME 2026-11-06 - the filter as EXISTS on the indexed cc_schedule
        // columns instead of a LEFT JOIN with an OR filter: the join made the
        // planner scan all instances and run the correlated "last instance"
        // subquery for each of them - 1.8-2.0 s per file, minutes for a bulk
        // delete (measured 2026-11-06: 1970 ms -> 33 ms, results identical on
        // 75 ids).  Same semantics: an instance qualifies when it recorded the
        // file or one of its rows played the file / stream.
        $cond = $fileId
            ? '(a.file_id = :id OR EXISTS (SELECT 1 FROM cc_schedule sch WHERE sch.instance_id = a.id AND sch.file_id = :id))'
            : 'EXISTS (SELECT 1 FROM cc_schedule sch WHERE sch.instance_id = a.id AND sch.stream_id = :id)';
        $sql = "SELECT b.name, MIN(bi.starts) AS starts
                  FROM cc_show_instances a
                  JOIN cc_show b ON b.repeat_of_show_id = a.show_id
                  JOIN cc_show_instances bi ON bi.show_id = b.id
                 WHERE {$cond}
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
            // RASTATIME 2026-10-20 - stage 2: live rows are replaced by the
            // source's recording; wait for its import while there is time
            $wait = self::recordingWait((int) $src['id'], (string) $d['starts']);
            if ($wait !== null) {
                Logging::info(sprintf(
                    'RepeatFillService: show "%s" (instance %d) waits for the recording of instance %d (%s)',
                    $d['name'], $d['instance_id'], $src['id'], $wait
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
     * RASTATIME 2026-10-20 - stage 2: the imported recording of a source
     * instance (cc_show_instances.file_id, "Copy Show Recordings into
     * Library"), ready for scheduling: [id, length] (seconds), or null when
     * the instance was not recorded, the file is not imported yet or missing.
     */
    public static function recordingOf(int $srcInstanceId): ?array
    {
        $row = Application_Common_Database::prepareAndExecute(
            'SELECT a.record, a.file_id, f.import_status, f.file_exists, f.length
               FROM cc_show_instances a
               LEFT JOIN cc_files f ON f.id = a.file_id
              WHERE a.id = :id',
            [':id' => $srcInstanceId],
            Application_Common_Database::SINGLE
        );
        if (!$row || !$row['file_id'] || (int) $row['import_status'] !== 0 || !self::pg($row['file_exists'])) {
            return null;
        }
        $length = (float) Application_Common_DateHelper::playlistTimeToSeconds((string) $row['length']);
        if ($length <= 0) {
            return null;
        }

        return ['id' => (int) $row['file_id'], 'length' => $length];
    }

    /**
     * Why the fill of a repeat starting at $dstStartsUtc should wait for the
     * recording of $srcInstanceId (a reason), or null to go ahead: the source
     * was recorded, has live rows (or no rows at all) that only the recording
     * can replace, the recording is not imported yet, and the repeat starts
     * more than RECORDING_WAIT_MARGIN_SECONDS from now.
     */
    public static function recordingWait(int $srcInstanceId, string $dstStartsUtc): ?string
    {
        $src = Application_Common_Database::prepareAndExecute(
            'SELECT a.record, a.file_id,
                    (SELECT COUNT(*) FROM cc_schedule s WHERE s.instance_id = a.id) AS rows_total,
                    (SELECT COUNT(*) FROM cc_schedule s WHERE s.instance_id = a.id AND (s.linein_id IS NOT NULL OR s.stream_id IS NOT NULL)) AS rows_live
               FROM cc_show_instances a WHERE a.id = :id',
            [':id' => $srcInstanceId],
            Application_Common_Database::SINGLE
        );
        if (!$src || (int) $src['record'] !== 1) {
            return null;
        }
        if ((int) $src['rows_live'] === 0 && (int) $src['rows_total'] > 0) {
            return null;                        // nothing a recording would replace
        }
        if (self::recordingOf($srcInstanceId) !== null) {
            return null;                        // imported and usable
        }
        $starts = new DateTime($dstStartsUtc, new DateTimeZone('UTC'));
        $left = $starts->getTimestamp() - time();
        if ($left <= self::RECORDING_WAIT_MARGIN_SECONDS) {
            return null;                        // out of time: fill without it
        }

        return $src['file_id']
            ? sprintf('recording file %d not imported yet, %d s left', (int) $src['file_id'], $left)
            : sprintf('no recording imported yet, %d s left', $left);
    }

    /**
     * The rows to schedule into a repeat of $srcInstanceId: files and
     * webstreams in their order; a line-in or webstream row becomes the
     * matching slice of the source's recording (cue in/out = the row's
     * offsets from the source start) when the recording is imported (a
     * webstream without one is copied as a live row, a line-in left out); a
     * recorded source without any rows is repeated from the recording alone.
     *
     * @return array [files, missing, live_left_out, live_replaced]
     */
    public static function planRows(int $srcInstanceId): array
    {
        $src = Application_Common_Database::prepareAndExecute(
            'SELECT starts FROM cc_show_instances WHERE id = :id',
            [':id' => $srcInstanceId],
            Application_Common_Database::SINGLE
        );
        $srcStart = $src ? new DateTime($src['starts'], new DateTimeZone('UTC')) : null;
        $recording = self::recordingOf($srcInstanceId);
        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT sch.file_id, sch.stream_id, sch.linein_id, sch.starts, sch.ends, sch.clip_length, sch.cue_in, sch.cue_out,
                    sch.fade_in, sch.fade_out, f.file_exists, f.import_status
               FROM cc_schedule sch
               LEFT JOIN cc_files f ON f.id = sch.file_id
              WHERE sch.instance_id = :src
              ORDER BY sch.starts, sch.id',
            [':src' => $srcInstanceId],
            'all'
        );
        $files = [];
        $skipped = 0;
        $live = 0;
        $replaced = 0;
        if (!$rows && $recording !== null) {
            // a live show without rows: the whole recording
            $files[] = self::recordingSlice($recording, 0.0, $recording['length']);

            return [$files, 0, 0, 1];
        }
        foreach ($rows as $r) {
            // RASTATIME 2026-10-21 - webstream rows too (operator go): a repeat
            // plays what went out, not the stream again; without a recording a
            // webstream is copied as a live row as before, a line-in left out
            if ($r['linein_id'] || ($r['stream_id'] && $recording !== null && $srcStart !== null)) {
                if ($recording === null || $srcStart === null) {
                    ++$live;

                    continue;
                }
                $from = self::secondsBetween($srcStart, (string) $r['starts']);
                $to = self::secondsBetween($srcStart, (string) $r['ends']);
                $from = max(0.0, min($from, $recording['length']));
                $to = max($from, min($to, $recording['length']));
                if ($to - $from < 1.0) {
                    ++$live;                    // the recording does not cover this row

                    continue;
                }
                $files[] = self::recordingSlice($recording, $from, $to);
                ++$replaced;

                continue;
            }
            if ($r['file_id']) {
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

        return [$files, $skipped, $live, $replaced];
    }

    /** A file item for the recording between two offsets (seconds). */
    private static function recordingSlice(array $recording, float $from, float $to): array
    {
        return [
            'type' => 0, 'id' => $recording['id'],
            'cliplength' => Application_Common_DateHelper::secondsToPlaylistTime($to - $from),
            'cuein' => Application_Common_DateHelper::secondsToPlaylistTime($from),
            'cueout' => Application_Common_DateHelper::secondsToPlaylistTime($to),
            'fadein' => '00.000000', 'fadeout' => '00.000000',
        ];
    }

    private static function secondsBetween(DateTime $from, string $toUtc): float
    {
        $to = new DateTime($toUtc, new DateTimeZone('UTC'));
        $micro = (float) $to->format('u') / 1000000 - (float) $from->format('u') / 1000000;

        return (float) ($to->getTimestamp() - $from->getTimestamp()) + $micro;
    }

    /**
     * Copy the rows of $srcInstanceId into the (empty) $dstInstanceId (see
     * planRows): files and webstreams in their order, live rows as slices of
     * the source's recording when it is imported, else left out; missing
     * files are counted as skipped.
     */
    public static function copyInstance(int $srcInstanceId, int $dstInstanceId, string $label = ''): bool
    {
        [$files, $skipped, $live, $replaced] = self::planRows($srcInstanceId);
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
            'RepeatFillService: "%s" instance %d filled from instance %d - %d rows, %d missing, %d live inputs replaced by the recording, %d left out',
            $label, $dstInstanceId, $srcInstanceId, count($files), $skipped, $replaced, $live
        ));

        return count($files) > 0;
    }

    private static function pg($v): bool
    {
        return $v === true || $v === 't' || $v === 1 || $v === '1' || $v === 'true';
    }
}
