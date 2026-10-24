<?php

class Application_Model_ShowInstance
{
    private $_instanceId;
    private $_showInstance;

    public function __construct($instanceId)
    {
        $this->_instanceId = $instanceId;
        $this->_showInstance = CcShowInstancesQuery::create()->findPK($instanceId);

        if (is_null($this->_showInstance)) {
            throw new Exception();
        }
    }

    public function getShowId()
    {
        return $this->_showInstance->getDbShowId();
    }

    /* TODO: A little inconsistent because other models have a getId() method
        to get PK --RG */
    public function getShowInstanceId()
    {
        return $this->_instanceId;
    }

    public function getShow()
    {
        return new Application_Model_Show($this->getShowId());
    }

    public function deleteRebroadcasts()
    {
        $timestamp = gmdate(DEFAULT_TIMESTAMP_FORMAT);
        $instance_id = $this->getShowInstanceId();
        $sql = <<<'SQL'
DELETE FROM cc_show_instances
WHERE starts > :timestamp::TIMESTAMP
AND instance_id = :instanceId
AND rebroadcast = 1;
SQL;
        Application_Common_Database::prepareAndExecute($sql, [
            ':instanceId' => $instance_id,
            ':timestamp' => $timestamp,
        ], 'execute');
    }

    /* This function is weird. It should return a boolean, but instead returns
     * an integer if it is a rebroadcast, or returns null if it isn't. You can convert
     * it to boolean by using is_null(isRebroadcast), where true means isn't and false
     * means that it is. */
    public function isRebroadcast()
    {
        return $this->_showInstance->getDbOriginalShow();
    }

    public function isRecorded()
    {
        return $this->_showInstance->getDbRecord();
    }

    public function getName()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbName();
    }

    public function getImagePath()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbImagePath();
    }

    public function getGenre()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbGenre();
    }

    public function hasAutoPlaylist()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbHasAutoPlaylist();
    }

    public function getAutoPlaylistId()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbAutoPlaylistId();
    }

    public function getAutoPlaylistRepeat()
    {
        $show = CcShowQuery::create()->findPK($this->getShowId());

        return $show->getDbAutoPlaylistRepeat();
    }

    /**
     * Return the start time of the Show (UTC time).
     *
     * @param mixed $format
     *
     * @return string in format DEFAULT_TIMESTAMP_FORMAT (PHP time notation)
     */
    public function getShowInstanceStart($format = DEFAULT_TIMESTAMP_FORMAT)
    {
        return $this->_showInstance->getDbStarts($format);
    }

    /**
     * Return the end time of the Show (UTC time).
     *
     * @param mixed $format
     *
     * @return string in format DEFAULT_TIMESTAMP_FORMAT (PHP time notation)
     */
    public function getShowInstanceEnd($format = DEFAULT_TIMESTAMP_FORMAT)
    {
        return $this->_showInstance->getDbEnds($format);
    }

    public function getStartDate()
    {
        $showStart = $this->getShowInstanceStart();
        $showStartExplode = explode(' ', $showStart);

        return $showStartExplode[0];
    }

    public function getStartTime()
    {
        $showStart = $this->getShowInstanceStart();
        $showStartExplode = explode(' ', $showStart);

        return $showStartExplode[1];
    }

    public function getRecordedFile()
    {
        $file_id = $this->_showInstance->getDbRecordedFile();

        if (isset($file_id)) {
            $file = Application_Model_StoredFile::RecallById($file_id);

            if (isset($file)) {
                $filePaths = $file->getFilePaths();
                if (file_exists($filePaths[0])) {
                    return $file;
                }
            }
        }

        return null;
    }

    public function setShowStart($start)
    {
        $this->_showInstance->setDbStarts($start)
            ->save();
        Application_Model_RabbitMq::PushSchedule();
    }

    public function setShowEnd($end)
    {
        $this->_showInstance->setDbEnds($end)
            ->save();
        Application_Model_RabbitMq::PushSchedule();
    }

    public function setAutoPlaylistBuilt($bool)
    {
        $this->_showInstance->setDbAutoPlaylistBuilt($bool)
            ->save();
    }

    public function updateScheduledTime()
    {
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->updateDbTimeFilled($con);
    }

    public function isDeleted()
    {
        $this->_showInstance->getDbModifiedInstance();
    }

    /*
     * @param $dateTime
     *      php Datetime object to add deltas to
     *
     * @param $deltaDay
     *      php int, delta days show moved
     *
     * @param $deltaMin
     *      php int, delta mins show moved
     *
     * @return $newDateTime
     *      php DateTime, $dateTime with the added time deltas.
     */
    public static function addDeltas($dateTime, $deltaDay, $deltaMin)
    {
        $newDateTime = clone $dateTime;

        $days = abs($deltaDay);
        $mins = abs($deltaMin);

        $dayInterval = new DateInterval("P{$days}D");
        $minInterval = new DateInterval("PT{$mins}M");

        if ($deltaDay > 0) {
            $newDateTime->add($dayInterval);
        } elseif ($deltaDay < 0) {
            $newDateTime->sub($dayInterval);
        }

        if ($deltaMin > 0) {
            $newDateTime->add($minInterval);
        } elseif ($deltaMin < 0) {
            $newDateTime->sub($minInterval);
        }

        return $newDateTime;
    }

    /**
     * Add a playlist as the last item of the current show.
     *
     * @param mixed $pl_id
     * @param mixed $checkUserPerm
     * @param int   $reservedSecs RASTATIME 2026-05-20 — Section 23.19.
     *              Seconds to reserve at the tail end of the show
     *              instance when computing the smart-block time
     *              limit, so a time-remaining smart block inside
     *              ``$pl_id`` cannot consume slots that the caller
     *              intends to fill afterwards (e.g. an outro
     *              playlist).  Default 0 = pre-existing behaviour.
     */
    public function addPlaylistToShow($pl_id, $checkUserPerm = true, $reservedSecs = 0)
    {
        $ts = intval($this->_showInstance->getDbLastScheduled('U')) ?: 0;
        $id = $this->_showInstance->getDbId();
        $lastid = $this->getLastAudioItemId();
        $scheduler = new Application_Model_Scheduler($checkUserPerm);
        $scheduler->setReservedSeconds($reservedSecs);
        $scheduler->scheduleAfter(
            [['id' => $lastid, 'instance' => $id, 'timestamp' => $ts]],
            [['id' => $pl_id, 'type' => 'playlist']]
        );
        // doing this to update the database schedule so that subsequent adds will work.
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->updateScheduleStatus($con);
    }

    /**
     * Add a playlist as the first item of the current show.
     *
     * @param mixed $pl_id
     * @param mixed $checkUserPerm
     */
    public function addPlaylistToShowStart($pl_id, $checkUserPerm = true)
    {
        $ts = intval($this->_showInstance->getDbLastScheduled('U')) ?: 0;
        $id = $this->_showInstance->getDbId();
        $scheduler = new Application_Model_Scheduler($checkUserPerm);
        $scheduler->scheduleAfter(
            [['id' => 0, 'instance' => $id, 'timestamp' => $ts]],
            [['id' => $pl_id, 'type' => 'playlist']]
        );
        // doing this to update the database schedule so that subsequent adds will work.
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->updateScheduleStatus($con);
    }

    /**
     * RASTATIME 2026-10-01 - insert prepared rows after a schedule row of
     * this instance (0 = at the start); see Scheduler::scheduleFilesAfter.
     * The instance's last_scheduled stamp is read fresh, so repeated calls
     * during one build never trip the out-of-date check.
     *
     * @param int   $afterRowId
     * @param array $files
     */
    public function addFilesAfter($afterRowId, array $files)
    {
        $fresh = CcShowInstancesQuery::create()->findPk($this->_instanceId);
        $ts = $fresh ? (intval($fresh->getDbLastScheduled('U')) ?: 0) : 0;
        $scheduler = new Application_Model_Scheduler(false);
        $scheduler->scheduleFilesAfter(
            [['id' => (int) $afterRowId, 'instance' => $this->_instanceId, 'timestamp' => $ts]],
            $files
        );
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->reload();
        $this->_showInstance->updateScheduleStatus($con);
    }

    /**
     * Add a media file as the last item in the show.
     *
     * @param int   $file_id
     * @param mixed $checkUserPerm
     */
    public function addFileToShow($file_id, $checkUserPerm = true)
    {
        $ts = intval($this->_showInstance->getDbLastScheduled('U')) ?: 0;
        $id = $this->_showInstance->getDbId();

        $scheduler = new Application_Model_Scheduler();
        $scheduler->setCheckUserPermissions($checkUserPerm);
        $scheduler->scheduleAfter(
            [['id' => 0, 'instance' => $id, 'timestamp' => $ts]],
            [['id' => $file_id, 'type' => 'audioclip']]
        );
    }

    /**
     * RASTATIME 2026-06-07 — Song Requests (Option C-onepass).  Append a
     * single autoload item — a file ('audioclip') or a smart 'block',
     * resolved ONCE against the current pool state — to the END of this
     * instance's schedule.  AutoPlaylistManager's request-show fill walks a
     * request playlist position-by-position and resolves one item at a time
     * (with a Phase 6a consume in between) so that several "use requests"
     * blocks each draw a DIFFERENT track.  A 'block' position's item/time
     * limit is applied by the Scheduler via getSecondsRemaining(), so a
     * "time remaining" block correctly fills to the show end.
     *
     * This mirrors addPlaylistToShow() — NOT addFileToShow() — because the
     * request fill appends REPEATEDLY in one loop, and that needs two things
     * a one-shot UI add does not:
     *  - anchor on getLastAudioItemId() (the current last item) so each
     *    append lands at the END, in dramaturgy order; id=0 makes successive
     *    inserts pile up at the start and scrambles the running order.
     *  - call updateScheduleStatus() afterwards so last_scheduled advances;
     *    otherwise the next append passes a stale timestamp and the Scheduler
     *    rejects it with OutDatedScheduleException ("previously updated").
     * checkUserPermissions is passed to the CONSTRUCTOR (not the setter):
     * the constructor calls Application_Model_User::getCurrentUser(), which
     * needs a Zend session a background TaskManager poll does not have.
     *
     * @param string $schedType 'audioclip' (file) or 'block'
     * @param int    $item_id   cc_files.id or cc_block.id
     * @param bool   $checkUserPerm
     */
    public function addAutoloadItemToShow($schedType, $item_id, $checkUserPerm = false)
    {
        $ts = intval($this->_showInstance->getDbLastScheduled('U')) ?: 0;
        $id = $this->_showInstance->getDbId();
        $lastid = $this->getLastAudioItemId();

        $scheduler = new Application_Model_Scheduler($checkUserPerm);
        $scheduler->scheduleAfter(
            [['id' => $lastid, 'instance' => $id, 'timestamp' => $ts]],
            [['id' => $item_id, 'type' => $schedType]]
        );

        // Refresh last_scheduled so the next append in the loop anchors after
        // this item and clears the "previously updated" guard — exactly what
        // addPlaylistToShow does, and for the same reason.
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->updateScheduleStatus($con);
    }

    /**
     * Add the given playlists to the show.
     *
     * @param array $plIds
     *                     An array of playlist IDs
     */
    public function scheduleShow($plIds)
    {
        foreach ($plIds as $plId) {
            $this->addPlaylistToShow($plId);
        }
    }

    public function clearShow()
    {
        CcScheduleQuery::create()
            ->filterByDbInstanceId($this->_instanceId)
            ->delete();
        Application_Model_RabbitMq::PushSchedule();
        $this->updateScheduledTime();
    }

    private function checkToDeleteShow($showId)
    {
        // UTC DateTime object
        $showsPopUntil = Application_Model_Preference::GetShowsPopulatedUntil();

        $showDays = CcShowDaysQuery::create()
            ->filterByDbShowId($showId)
            ->findOne();

        $showEnd = $showDays->getDbLastShow();

        // there will always be more shows populated.
        if (is_null($showEnd)) {
            return false;
        }

        $lastShowStartDateTime = new DateTime("{$showEnd} {$showDays->getDbStartTime()}", new DateTimeZone($showDays->getDbTimezone()));
        // end dates were non inclusive.
        $lastShowStartDateTime = self::addDeltas($lastShowStartDateTime, -1, 0);

        // there's still some shows left to be populated.
        if ($lastShowStartDateTime->getTimestamp() > $showsPopUntil->getTimestamp()) {
            return false;
        }

        // check if there are any non deleted show instances remaining.
        $showInstances = CcShowInstancesQuery::create()
            ->filterByDbShowId($showId)
            ->filterByDbModifiedInstance(false)
            ->filterByDbRebroadcast(0)
            ->find();

        if (is_null($showInstances)) {
            return true;
        }
        // only 1 show instance left of the show, make it non repeating.
        if (count($showInstances) === 1) {
            $showInstance = $showInstances[0];

            $showDaysOld = CcShowDaysQuery::create()
                ->filterByDbShowId($showId)
                ->find();

            $tz = $showDaysOld[0]->getDbTimezone();

            $startDate = new DateTime($showInstance->getDbStarts(), new DateTimeZone('UTC'));
            $startDate->setTimeZone(new DateTimeZone($tz));
            $endDate = self::addDeltas($startDate, 1, 0);

            // make a new rule for a non repeating show.
            $showDayNew = new CcShowDays();
            $showDayNew->setDbFirstShow($startDate->format('Y-m-d'));
            $showDayNew->setDbLastShow($endDate->format('Y-m-d'));
            $showDayNew->setDbStartTime($startDate->format('H:i:s'));
            $showDayNew->setDbTimezone($tz);
            $showDayNew->setDbDay($startDate->format('w'));
            $showDayNew->setDbDuration($showDaysOld[0]->getDbDuration());
            $showDayNew->setDbRepeatType(-1);
            $showDayNew->setDbShowId($showDaysOld[0]->getDbShowId());
            $showDayNew->setDbRecord($showDaysOld[0]->getDbRecord());
            $showDayNew->save();

            // delete the old rules for repeating shows
            $showDaysOld->delete();

            // remove the old repeating deleted instances.
            $showInstances = CcShowInstancesQuery::create()
                ->filterByDbShowId($showId)
                ->filterByDbModifiedInstance(true)
                ->delete();
        }

        return false;
    }

    public function delete($rabbitmqPush = true)
    {
        // see if it was recording show
        $recording = $this->isRecorded();
        // get show id
        $showId = $this->getShowId();

        $show = $this->getShow();

        $current_timestamp = gmdate(DEFAULT_TIMESTAMP_FORMAT);

        if ($current_timestamp <= $this->getShowInstanceEnd()) {
            if ($show->isRepeating()) {
                CcShowInstancesQuery::create()
                    ->findPK($this->_instanceId)
                    ->setDbModifiedInstance(true)
                    ->save();

                if ($this->isRebroadcast()) {
                    return;
                }

                // delete the rebroadcasts of the removed recorded show.
                if ($recording) {
                    CcShowInstancesQuery::create()
                        ->filterByDbOriginalShow($this->_instanceId)
                        ->delete();
                }

                // Automatically delete all files scheduled in cc_schedules table.
                CcScheduleQuery::create()
                    ->filterByDbInstanceId($this->_instanceId)
                    ->delete();

                if ($this->checkToDeleteShow($showId)) {
                    CcShowQuery::create()
                        ->filterByDbId($showId)
                        ->delete();
                }
            } else {
                if ($this->isRebroadcast()) {
                    $this->_showInstance->delete();
                } else {
                    $show->delete();
                }
            }
        }

        if ($rabbitmqPush) {
            Application_Model_RabbitMq::PushSchedule();
        }
    }

    public function setRecordedFile($file_id)
    {
        $showInstance = CcShowInstancesQuery::create()
            ->findPK($this->_instanceId);
        $showInstance->setDbRecordedFile($file_id)
            ->save();

        $rebroadcasts = CcShowInstancesQuery::create()
            ->filterByDbOriginalShow($this->_instanceId)
            ->find();

        foreach ($rebroadcasts as $rebroadcast) {
            try {
                $rebroad = new Application_Model_ShowInstance($rebroadcast->getDbId());
                $rebroad->addFileToShow($file_id, false);
            } catch (Exception $e) {
                Logging::info($e->getMessage());
            }
        }
    }

    public function getTimeScheduled()
    {
        $time = $this->_showInstance->getDbTimeFilled();

        if ($time != '00:00:00' && !empty($time)) {
            $time_arr = explode('.', $time);
            if (count($time_arr) > 1) {
                $time_arr[1] = '.' . $time_arr[1];
                $milliseconds = number_format(round($time_arr[1], 2), 2);
                $time = $time_arr[0] . substr($milliseconds, 1);
            } else {
                $time = $time_arr[0] . '.00';
            }
        } else {
            $time = '00:00:00.00';
        }

        return $time;
    }

    public function getTimeScheduledSecs()
    {
        // RASTATIME 2026-10-06 - from the raw column, not the display value:
        // getTimeScheduled() rounds the fraction to 2 digits and a .997
        // became "1.00" with the second dropped (59.997 s read as 59.00 s).
        $time_filled = $this->_showInstance->getDbTimeFilled();
        if (empty($time_filled)) {
            return 0.0;
        }

        return (float) Application_Common_DateHelper::playlistTimeToSeconds($time_filled);
    }

    public function getDurationSecs()
    {
        $ends = $this->getShowInstanceEnd(null);
        $starts = $this->getShowInstanceStart(null);

        return intval($ends->format('U')) - intval($starts->format('U'));
    }

    // should return the amount of seconds remaining to be scheduled in a show instance
    public function getSecondsRemaining()
    {
        return $this->getDurationSecs() - $this->getTimeScheduledSecs();
    }

    public function getPercentScheduled()
    {
        $durationSeconds = $this->getDurationSecs();
        $timeSeconds = $this->getTimeScheduledSecs();

        if ($durationSeconds != 0) { // Prevent division by zero if the show duration is somehow zero.
            $percent = ceil(($timeSeconds / $durationSeconds) * 100);
        } else {
            $percent = 0;
        }

        return $percent;
    }

    public function getShowLength()
    {
        $start = $this->getShowInstanceStart(null);
        $end = $this->getShowInstanceEnd(null);

        $interval = $start->diff($end);
        $days = $interval->format('%d');
        $hours = sprintf('%02d', $interval->format('%h'));

        if ($days > 0) {
            $totalHours = $days * 24 + $hours;
            // $interval object does not have milliseconds so hard code to .00
            $returnStr = $totalHours . ':' . $interval->format('%I:%S') . '.00';
        } else {
            $returnStr = $hours . ':' . $interval->format('%I:%S') . '.00';
        }

        return $returnStr;
    }

    public static function getContentCount($p_start, $p_end)
    {
        $sql = <<<'SQL'
SELECT instance_id,
       count(*) AS instance_count
FROM cc_schedule
WHERE ends > :p_start::TIMESTAMP
  AND starts < :p_end::TIMESTAMP
GROUP BY instance_id
SQL;

        $counts = Application_Common_Database::prepareAndExecute($sql, [
            ':p_start' => $p_start->format('Y-m-d G:i:s'),
            ':p_end' => $p_end->format('Y-m-d G:i:s'),
        ], 'all');

        $real_counts = [];
        foreach ($counts as $c) {
            $real_counts[$c['instance_id']] = $c['instance_count'];
        }

        return $real_counts;
    }

    public static function getIsFull($p_start, $p_end)
    {
        $sql = <<<'SQL'
SELECT id, ends-starts-'00:00:05' < time_filled as filled
from cc_show_instances
WHERE ends > :p_start::TIMESTAMP
AND starts < :p_end::TIMESTAMP
SQL;

        $res = Application_Common_Database::prepareAndExecute($sql, [
            ':p_start' => $p_start->format('Y-m-d G:i:s'),
            ':p_end' => $p_end->format('Y-m-d G:i:s'),
        ], 'all');

        $isFilled = [];
        foreach ($res as $r) {
            $isFilled[$r['id']] = $r['filled'];
        }

        return $isFilled;
    }

    public static function getShowHasAutoplaylist($p_start, $p_end)
    {
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $con->beginTransaction();

        try {
            // query the show instances to find whether a show instance has an autoplaylist
            // RASTATIME 2026-10-24 - every instance that OVERLAPS the window, like
            // getIsFull (ends > start, starts < end).  Upstream took only
            // instances strictly inside it, so a show ending exactly at the
            // calendar's range end (Sunday 21:00-00:00 with the week ending
            // Monday 00:00) or starting at its range start (Monday 00:00) lost
            // the flag and showed the red "empty" icon instead of the
            // autoplaylist one (operator, seven shows).
            $showInstances = CcShowInstancesQuery::create()
                ->filterByDbEnds($p_start->format(DEFAULT_TIMESTAMP_FORMAT), Criteria::GREATER_THAN)
                ->filterByDbStarts($p_end->format(DEFAULT_TIMESTAMP_FORMAT), Criteria::LESS_THAN)
                ->leftJoinCcShow()
                ->where('CcShow.has_autoplaylist = ?', 'true')
                ->find($con);
            $hasAutoplaylist = [];
            foreach ($showInstances->toArray() as $ap) {
                $hasAutoplaylist[$ap['DbId']] = true;
            }

            return $hasAutoplaylist;
        } catch (Exception $e) {
            $con->rollback();
            Logging::info("Couldn't query show instances for calendar to find which had autoplaylists");
            Logging::info($e->getMessage());
        }
    }

    public function showEmpty()
    {
        $sql = <<<'SQL'
SELECT s.starts
FROM cc_schedule AS s
WHERE s.instance_id = :instance_id
  AND s.playout_status >= 0
  AND ((s.stream_id IS NOT NULL)
       OR (s.file_id IS NOT NULL)) LIMIT 1
SQL;
        // TODO : use prepareAndExecute properly
        $res = Application_Common_Database::prepareAndExecute(
            $sql,
            [':instance_id' => $this->_instanceId],
            'all'
        );
        // TODO : A bit retarded. fix this later
        foreach ($res as $r) {
            return false;
        }

        return true;
    }

    public function getShowListContent($timezone = null)
    {
        $con = Propel::getConnection();

        // RASTATIME 2026-10-23 - "length" is the ROW's length (cue-out minus
        // cue-in of the schedule row, as the show builder shows it), not the
        // medium's raw length: the "View" dialog listed a cued file with its
        // full file length next to cue-aware start times (operator).  Live
        // rows (webstream, line-in) carry cue_in 0 and cue_out = clip length.

        // RASTATIME 2026-05-13 — third UNION branch for Line-In items
        // (cc_schedule.linein_id → rastatime_linein).  Mirrors the
        // shape used by the file/stream branches: track_title carries
        // the Line-In's display name, album carries the description,
        // and length falls back to 30 min when the row has no
        // explicit length set.  ``type`` = 2 keeps the same numeric
        // convention used in Scheduler::insertAfter / makeScheduledItemRow.
        $sql = <<<'SQL'
SELECT *
FROM (
        (SELECT s.starts,
                0::INTEGER as type ,
                f.id           AS item_id,
                f.track_title,
                f.album_title  AS album,
                f.genre        AS genre,
                (s.cue_out - s.cue_in) AS length,
                f.artist_name  AS creator,
                f.file_exists  AS EXISTS,
                f.filepath     AS filepath,
                f.mime         AS mime
         FROM cc_schedule AS s
         LEFT JOIN cc_files AS f ON f.id = s.file_id
         WHERE s.instance_id = :instance_id1
           AND s.playout_status >= 0
           AND s.file_id IS NOT NULL
           AND f.hidden = 'false')
      UNION
        (SELECT s.starts,
                1::INTEGER as type,
                ws.id AS item_id,
                (ws.name || ': ' || ws.url) AS track_title,
                null            AS album,
                null            AS genre,
                (s.cue_out - s.cue_in) AS length,
                sub.login       AS creator,
                't'::boolean    AS EXISTS,
                ws.url          AS filepath,
                ws.mime as mime
         FROM cc_schedule AS s
         LEFT JOIN cc_webstream AS ws ON ws.id = s.stream_id
         LEFT JOIN cc_subjs AS sub ON ws.creator_id = sub.id
         WHERE s.instance_id = :instance_id2
           AND s.playout_status >= 0
           AND s.stream_id IS NOT NULL)
      UNION
        (SELECT s.starts,
                2::INTEGER as type,
                li.id           AS item_id,
                li.name         AS track_title,
                li.description  AS album,
                null            AS genre,
                (s.cue_out - s.cue_in) AS length,
                ''::varchar     AS creator,
                't'::boolean    AS EXISTS,
                null::varchar   AS filepath,
                null::varchar   AS mime
         FROM cc_schedule AS s
         JOIN rastatime_linein AS li ON li.id = s.linein_id
         WHERE s.instance_id = :instance_id3
           AND s.playout_status >= 0
           AND s.linein_id IS NOT NULL)) AS temp
ORDER BY starts;
SQL;

        $stmt = $con->prepare($sql);
        $stmt->execute([
            ':instance_id1' => $this->_instanceId,
            ':instance_id2' => $this->_instanceId,
            ':instance_id3' => $this->_instanceId,
        ]);
        $results = $stmt->fetchAll(PDO::FETCH_ASSOC);

        if (isset($timezone)) {
            $displayTimezone = new DateTimeZone($timezone);
        } else {
            $userTimezone = Application_Model_Preference::GetUserTimezone();
            $displayTimezone = new DateTimeZone($userTimezone);
        }

        $utcTimezone = new DateTimeZone('UTC');

        foreach ($results as &$row) {
            $dt = new DateTime($row['starts'], $utcTimezone);
            $dt->setTimezone($displayTimezone);
            $row['starts'] = $dt->format(DEFAULT_TIMESTAMP_FORMAT);

            if (isset($row['length'])) {
                $formatter = new LengthFormatter($row['length']);
                $row['length'] = $formatter->format();
            }
        }

        return $results;
    }

    public function getLastAudioItemId()
    {
        $con = Propel::getConnection();

        $sql = 'SELECT id FROM cc_schedule '
            . 'WHERE instance_id = :instanceId '
            . 'ORDER BY ends DESC '
            . 'LIMIT 1';

        $query = Application_Common_Database::prepareAndExecute(
            $sql,
            [':instanceId' => $this->_instanceId],
            'column'
        );

        return ($query !== false) ? $query : null;
    }

    public function getLastAudioItemEnd()
    {
        $con = Propel::getConnection();

        $sql = 'SELECT ends FROM cc_schedule '
            . 'WHERE instance_id = :instanceId '
            . 'ORDER BY ends DESC '
            . 'LIMIT 1';

        $query = Application_Common_Database::prepareAndExecute(
            $sql,
            [':instanceId' => $this->_instanceId],
            'column'
        );

        return ($query !== false) ? $query : null;
    }

    public static function GetLastShowInstance($p_timeNow)
    {
        $sql = <<<'SQL'
SELECT si.id
FROM cc_show_instances si
WHERE si.ends < :timeNow::TIMESTAMP
  AND si.modified_instance = 'f'
ORDER BY si.ends DESC LIMIT 1;
SQL;
        $id = Application_Common_Database($sql, [
            ':timeNow' => $p_timeNow,
        ], 'column');

        return $id ? new Application_Model_ShowInstance($id) : null;
    }

    public static function GetCurrentShowInstance($p_timeNow)
    {
        /* Orderby si.starts descending, because in some cases
         * we can have multiple shows overlapping each other. In
         * this case, the show that started later is the one that
         * is actually playing, and so this is the one we want.
         */

        $sql = <<<'SQL'
SELECT si.id
FROM cc_show_instances si
WHERE si.starts <= :timeNow1::TIMESTAMP
  AND si.ends > :timeNow2::TIMESTAMP
  AND si.modified_instance = 'f'
ORDER BY si.starts DESC LIMIT 1
SQL;

        $id = Application_Common_Database($sql, [
            ':timeNow1' => $p_timeNow,
            ':timeNow2' => $p_timeNow,
        ], 'column');

        return $id ? new Application_Model_ShowInstance($id) : null;
    }

    public static function GetNextShowInstance($p_timeNow)
    {
        $sql = <<<'SQL'
SELECT si.id
FROM cc_show_instances si
WHERE si.starts > :timeNow::TIMESTAMP
AND si.modified_instance = 'f'
ORDER BY si.starts
LIMIT 1
SQL;
        $id = Application_Common_Database::prepareAndExecute(
            $sql,
            ['timeNow' => $p_timeNow],
            'column'
        );

        return $id ? new Application_Model_ShowInstance($id) : null;
    }

    // returns number of show instances that ends later than $day
    public static function GetShowInstanceCount($day)
    {
        $sql = <<<'SQL'
SELECT count(*) AS cnt
FROM cc_show_instances
WHERE ends < :day
SQL;

        return Application_Common_Database::prepareAndExecute(
            $sql,
            [':day' => $day],
            'column'
        );
    }

    // this returns end timestamp of all shows that are in the range and has live DJ set up
    public static function GetEndTimeOfNextShowWithLiveDJ($p_startTime, $p_endTime)
    {
        $sql = <<<'SQL'
SELECT ends
FROM cc_show_instances AS si
JOIN cc_show AS sh ON si.show_id = sh.id
WHERE si.ends > :startTime::TIMESTAMP
  AND si.ends < :endTime::TIMESTAMP
  AND (sh.live_stream_using_airtime_auth
       OR live_stream_using_custom_auth)
ORDER BY si.ends
SQL;

        return Application_Common_Database::prepareAndExecute($sql, [
            ':startTime' => $p_startTime,
            ':endTime' => $p_endTime,
        ], 'all');
    }

    public function isRepeating()
    {
        return $this->getShow()->isRepeating();
    }

    /**
     * RASTATIME 2026-05-20 — Section 23.19 v4.
     *
     * Re-aggregate ``cc_show_instances.time_filled`` from the current
     * ``cc_schedule`` rows for this instance.  Used by callers that
     * manipulate ``cc_schedule`` directly (raw SQL DELETE / INSERT)
     * and need {@see getSecondsRemaining()} / {@see getTimeScheduled()}
     * to reflect the change without going through Propel's save hooks.
     */
    public function refreshScheduleStatus()
    {
        $con = Propel::getConnection(CcShowInstancesPeer::DATABASE_NAME);
        $this->_showInstance->updateScheduleStatus($con);
    }

    public function trimOverbooked()
    {
        // Remove all scheduled items that start time after the show has ended
        $sql = <<<'SQL'
        delete
        from
            cc_schedule
        where
            id in (
            select
                s.id
            from
                cc_schedule s
            left join cc_show_instances si on
                s.instance_id = si.id
            where
                si.id = :instance_id
                and si.ends < s.starts
                and s.playout_status = 0 -- playout_status = 0 double check that si.ends < s.starts
        );
        SQL;

        return Application_Common_Database::prepareAndExecute(
            $sql,
            [':instance_id' => $this->_instanceId],
            'execute'
        );
    }
}
