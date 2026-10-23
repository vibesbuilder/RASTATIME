<?php

class AutoPlaylistManager
{
    /**
     * @var int how often, in seconds, to check for and ingest new podcast episodes
     */
    private static $_AUTOPLAYLIST_POLL_INTERVAL_SECONDS = 60;  // 10 minutes

    /**
     * @var int RASTATIME 2026-06-16 — Mid-Show Song Requests (incremental
     *          fill).  How far ahead of the play head, in seconds, the
     *          request fill resolves dramaturgy positions on each poll.
     *          MUST exceed the RequestShowFillTask poll interval (2 min) so a
     *          show never runs dry between polls.  Larger = more dead-air-safe;
     *          smaller = "use requests" blocks draw fresher requests.
     *          Env-overridable via RASTATIME_REQUEST_FILL_AHEAD_SECONDS.
     */
    private static $_REQUEST_FILL_AHEAD_SECONDS = 300;  // 5 minutes

    /**
     * Check whether $_AUTOPLAYLIST_POLL_INTERVAL_SECONDS have passed since the last call to
     * buildAutoPlaylist.
     *
     * @return bool true if $_AUTOPLAYLIST_POLL_INTERVAL_SECONDS has passed since the last check
     */
    public static function hasAutoPlaylistPollIntervalPassed()
    {
        $lastPolled = Application_Model_Preference::getAutoPlaylistPollLock();

        return empty($lastPolled) || (microtime(true) > $lastPolled + self::$_AUTOPLAYLIST_POLL_INTERVAL_SECONDS);
    }

    /**
     * Find all shows with autoplaylists who have yet to have their playlists built and added to the schedule.
     *
     * RASTATIME 2026-05-21 — Section 23.20.  Two Auto-DJ hooks bookend
     * the existing per-show build loop:
     *
     *   pre-pass  → AutoDjService::runPrePass() creates a new show in
     *               the next 1-h calendar gap (if any) so the loop
     *               below picks it up in the SAME poll cycle.
     *   fill-pass → AutoDjService::runFillPass() appends the Auto-DJ
     *               playlist to any upcoming instance that ended up
     *               more than 5 s short of its slot after the build.
     *
     * Both hooks are guarded by the cc_pref Auto-DJ-enabled flag and
     * by the configured playlist id; they are no-ops when the
     * operator has not opted in.
     */
    public static function buildAutoPlaylist()
    {
        // RASTATIME 2026-05-21 — Section 23.20 pre-pass.
        try {
            Application_Service_AutoDjService::runPrePass();
        } catch (Throwable $e) {
            Logging::warn('AutoDjService::runPrePass crashed: ' . $e->getMessage());
        }

        $autoPlaylists = static::_upcomingAutoPlaylistShows();
        foreach ($autoPlaylists as $autoplaylist) {
            // creates a ShowInstance object to build the playlist in from the ShowInstancesQuery Object
            $si = new Application_Model_ShowInstance($autoplaylist->getDbId());
            $playlistid = $si->GetAutoPlaylistId();

            // RASTATIME 2026-06-07 — Song Requests: a show whose autoload
            // playlist contains a "use requests" smart block is a REQUEST
            // show — filled incrementally + just-in-time by
            // RequestShowFillTask, NOT pre-filled to 100% here.  Skip it
            // so listeners' just-in-time requests still have room to land.
            // RASTATIME 2026-06-16 — Traffic Alerts: likewise a show whose
            // autoload playlist contains the configured traffic-alert block is
            // filled incrementally (so alerts imported mid-show still land in
            // it); skip the one-pass fill here too.
            if (self::playlistContainsRequestBlock($playlistid)
                || self::playlistContainsTrafficBlock($playlistid)
            ) {
                continue;
            }

            // RASTATIME 2026-10-01 - exact fill (operator specification):
            // intro at the start, outro at the end, the autoloading playlist
            // in between against the REAL layout time - never beyond the
            // show's end, the last row at most FILL_TOLERANCE_SECS before it.
            $sid = $si->getShowId();
            $show = new Application_Model_Show($sid);
            $introplaylistid = $show->getHasOverrideIntroPlaylist()
                ? $show->getIntroPlaylistId()
                : Application_Model_Preference::GetIntroPlaylist();
            $outroplaylistid = $show->getHasOverrideOutroPlaylist()
                ? $show->getOutroPlaylistId()
                : Application_Model_Preference::GetOutroPlaylist();

            try {
                self::fillInstance(
                    (int) $autoplaylist->getDbId(),
                    $introplaylistid ?: null,
                    $outroplaylistid ?: null,
                    $playlistid ?: null,
                    (bool) $show->getAutoPlaylistRepeat()
                );
            } catch (Throwable $e) {
                Logging::warn(
                    'AutoPlaylistManager: fill failed for show_instance_id='
                    . $autoplaylist->getDbId() . ': ' . $e->getMessage()
                );
            }
            $si->setAutoPlaylistBuilt(true);

            // now trim excessively overbooked shows so the display isn't cluttered with myriads of red off-time blocks
            if (Application_Model_Preference::getScheduleTrimOverbooked()) {
                $si->trimOverbooked();
            }
        }

        // RASTATIME 2026-05-21 — Section 23.20 fill-pass.  Runs after
        // the per-show autoplaylist build loop above.  No-op unless
        // the operator has both Auto-DJ AND "Automatically fill any
        // show" enabled (see AutoDjService::runFillPass).
        try {
            Application_Service_AutoDjService::runFillPass();
        } catch (Throwable $e) {
            Logging::warn('AutoDjService::runFillPass crashed: ' . $e->getMessage());
        }

        Application_Model_Preference::setAutoPlaylistPollLock(microtime(true));
    }

    /**
     * RASTATIME 2026-10-01 - the show's last row may end this many seconds
     * before the show's end; closer is not attempted.
     */
    const FILL_TOLERANCE_SECS = 4;

    /** Top-up rounds with the autoloading playlist's "time remaining" blocks. */
    const FILL_TOPUP_ROUNDS = 4;

    /**
     * RASTATIME 2026-10-01 - fill one show instance (operator specification,
     * replaces the 2026-05-20 trial-insert / reserve / trim-tail build):
     *
     *   1. the intro playlist at the start, once;
     *   2. the outro playlist at the end, once - inserted for real, so its
     *      length is known exactly (no trial insert, no safety margin);
     *   3. the autoloading playlist between the two, against the time that
     *      is really left in the LAYOUT (the rows overlap by their crossfade,
     *      which the sum of the clip lengths does not show);
     *   4. top-up rounds with the autoloading playlist's "time remaining"
     *      smart blocks until the gap at the end is within
     *      FILL_TOLERANCE_SECS, because only after the insert is it known
     *      how many transitions - and so how much overlap - the fill made.
     *
     * Every list is taken strictly in order and stops at the first item
     * that does not fit (operator decision, variant a); nothing is ever
     * inserted beyond the show's end, so nothing has to be trimmed.
     * "Repeat until full" repeats step 3 while it makes progress.
     *
     * @param int      $instanceId
     * @param null|int $introId
     * @param null|int $outroId
     * @param null|int $autoId
     * @param bool     $repeat
     */
    public static function fillInstance($instanceId, $introId, $outroId, $autoId, $repeat)
    {
        $si = new Application_Model_ShowInstance($instanceId);
        $showStart = (float) $si->getShowInstanceStart(null)->format('U.u');
        $showEnd = (float) $si->getShowInstanceEnd(null)->format('U.u');
        $house = [
            'track' => (float) Application_Model_Preference::GetDefaultCrossfadeDuration(),
            'show' => (float) Application_Model_Preference::GetDefaultShowCrossfadeDuration(),
        ];
        $counts = ['intro' => 0, 'outro' => 0, 'auto' => 0, 'topup' => 0];

        // RASTATIME 2026-10-16 - fill context (teaser criterion, planned-rows
        // exclusion): the instance, its show and the slot the rows will play
        // in - the show start for the intro, the show end for the outro, the
        // current chain end for the content.  Cleared in the finally below.
        $showId = (int) $si->getShowId();
        $slotAt = function ($epoch) {
            return new DateTime('@' . (int) floor((float) $epoch));
        };

        try {
        // 1. intro at the start
        if ($introId !== null) {
            $rows = self::instanceRows($instanceId);
            $gap = $showEnd - self::chainEnd($rows, $showStart, $house);
            Application_Model_Block::setFillContext($instanceId, $showId, $slotAt($showStart));
            $counts['intro'] = self::insertFitting(
                $si, $rows, 0, self::expandPlaylist($introId, $gap, false, false, self::neighbourFile($rows, 0)), $showStart, $showEnd, $house, 'intro'
            );
        }

        // 2. outro at the end
        if ($outroId !== null) {
            $rows = self::instanceRows($instanceId);
            $gap = $showEnd - self::chainEnd($rows, $showStart, $house);
            Application_Model_Block::setFillContext($instanceId, $showId, $slotAt($showEnd));
            $counts['outro'] = self::insertFitting(
                $si, $rows, count($rows), self::expandPlaylist($outroId, $gap, false, self::neighbourFile($rows, count($rows) - 1), false), $showStart, $showEnd, $house, 'outro'
            );
        }

        // 3. the autoloading playlist between intro and outro, in order
        if ($autoId !== null) {
            $passes = 0;
            do {
                $rows = self::instanceRows($instanceId);
                $gap = $showEnd - self::chainEnd($rows, $showStart, $house);
                if ($gap <= self::FILL_TOLERANCE_SECS) {
                    break;
                }
                $at = count($rows) - $counts['outro'];
                Application_Model_Block::setFillContext($instanceId, $showId, $slotAt(self::chainEnd(array_slice($rows, 0, $at), $showStart, $house)));
                $added = self::insertFitting(
                    $si, $rows, $at,
                    self::expandPlaylist($autoId, $gap, false, self::neighbourFile($rows, $at - 1), self::neighbourFile($rows, $at)),
                    $showStart, $showEnd, $house, 'auto'
                );
                $counts['auto'] += $added;
                ++$passes;
            } while ($repeat && $added > 0 && $passes < 50);

            // 4. top-up: the "time remaining" blocks against the gap the
            //    overlaps left
            for ($round = 0; $round < self::FILL_TOPUP_ROUNDS; ++$round) {
                $rows = self::instanceRows($instanceId);
                $gap = $showEnd - self::chainEnd($rows, $showStart, $house);
                if ($gap <= self::FILL_TOLERANCE_SECS) {
                    break;
                }
                $at = count($rows) - $counts['outro'];
                Application_Model_Block::setFillContext($instanceId, $showId, $slotAt(self::chainEnd(array_slice($rows, 0, $at), $showStart, $house)));
                $candidates = self::expandPlaylist($autoId, $gap, true, self::neighbourFile($rows, $at - 1), self::neighbourFile($rows, $at));
                if (empty($candidates)) {
                    break;
                }
                $added = self::insertFitting($si, $rows, $at, $candidates, $showStart, $showEnd, $house, 'top-up');
                if ($added === 0) {
                    break;
                }
                $counts['topup'] += $added;
            }
        }
        } finally {
            Application_Model_Block::clearFillContext();
        }

        $rows = self::instanceRows($instanceId);
        $gap = $showEnd - self::chainEnd($rows, $showStart, $house);
        Logging::info(sprintf(
            'AutoPlaylistManager: show_instance_id=%d filled - intro %d, outro %d, auto %d (+%d top-up) rows, %.1f s free at the end',
            $instanceId, $counts['intro'], $counts['outro'], $counts['auto'], $counts['topup'], $gap
        ));
    }

    /**
     * The file id of row $index for the planner's neighbour rule: null for
     * a live row, false when there is no such row.
     *
     * @return false|null|int
     */
    private static function neighbourFile(array $rows, $index)
    {
        if ($index < 0 || $index >= count($rows)) {
            return false;
        }

        return $rows[$index]['fileId'];
    }

    /**
     * The instance's rows in play order, as the planner needs them.
     *
     * @return array<int, array{id: int, fileId: null|int, secs: float}>
     */
    private static function instanceRows($instanceId)
    {
        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT id, file_id, clip_length FROM cc_schedule WHERE instance_id = :id ORDER BY starts, position, id',
            [':id' => (int) $instanceId],
            Application_Common_Database::ALL
        );
        $out = [];
        foreach (is_array($rows) ? $rows : [] as $r) {
            $out[] = [
                'id' => (int) $r['id'],
                'fileId' => $r['file_id'] === null ? null : (int) $r['file_id'],
                'secs' => (float) Application_Common_DateHelper::playlistTimeToSeconds($r['clip_length']),
            ];
        }

        return $out;
    }

    /**
     * Where a chain of rows ends when laid out from the show's start with
     * the pair rule of Scheduler::calculateCrossfades (each row starts at
     * the end of its predecessor minus their overlap).
     *
     * @param array<int, array{fileId: null|int, secs: float}> $rows
     * @param float                                             $showStart epoch
     * @param array{track: float, show: float}                  $house
     * @param null|array<int, array{exclude: bool, d: null|float}> $info crossfade info, fetched when null
     *
     * @return float epoch
     */
    public static function chainEnd(array $rows, $showStart, array $house, $info = null)
    {
        if (empty($rows)) {
            return (float) $showStart;
        }
        if ($info === null) {
            $info = Application_Model_Scheduler::crossfadeInfoForFiles(array_column($rows, 'fileId'));
        }
        $total = 0.0;
        $n = count($rows);
        foreach ($rows as $i => $row) {
            $total += (float) $row['secs'];
            if ($i + 1 < $n) {
                $total -= Application_Model_Scheduler::crossfadeOverlapBetween(
                    $row['fileId'], $rows[$i + 1]['fileId'], $info, $house['track'], $house['show']
                );
            }
        }

        return (float) $showStart + $total;
    }

    /**
     * Expand a playlist into the items it would schedule, in order: files
     * and static blocks as they are, a dynamic smart block as the tracks it
     * picks against the budget that is left (a "time remaining" block takes
     * the budget, a fixed-length block its own length).  With
     * $remainingBlocksOnly only the "time remaining" blocks are expanded
     * (the top-up rounds).
     *
     * @param int            $playlistId
     * @param float          $budgetSecs
     * @param bool           $remainingBlocksOnly
     * @param false|null|int $prevFileId         the row before the insertion point: a file id,
     *                                           null for a live row, false for none
     * @param false|null|int $nextFileId         the row after it, likewise
     *
     * @return array<int, array{type: int, id: int, secs: float, cliplength: string, cuein: string, cueout: string, fadein: string, fadeout: string}>
     */
    private static function expandPlaylist($playlistId, $budgetSecs, $remainingBlocksOnly = false, $prevFileId = false, $nextFileId = false)
    {
        $pl = new Application_Model_Playlist($playlistId);
        $out = [];
        // the laid-out seconds the items gathered so far take from the budget
        // (Scheduler::laidOutLength: overlaps, joins to the neighbours)
        $rowsOf = function (array $list) {
            return array_map(function ($c) {
                return ['fileId' => $c['type'] === 0 ? $c['id'] : null, 'secs' => $c['secs']];
            }, $list);
        };
        $lastOf = function (array $list) use ($prevFileId) {
            if (empty($list)) {
                return $prevFileId;
            }
            $c = end($list);

            return $c['type'] === 0 ? $c['id'] : null;
        };
        $fadeIn = Application_Model_Preference::GetDefaultFadeIn();
        $fadeOut = Application_Model_Preference::GetDefaultFadeOut();
        $secsOf = function ($len) {
            return (float) Application_Common_DateHelper::playlistTimeToSeconds($len);
        };

        foreach ($pl->getContents() as $item) {
            $type = (int) $item['type'];
            if ($type === 2) {
                $bl = new Application_Model_Block($item['item_id']);
                if ($bl->isStatic()) {
                    if ($remainingBlocksOnly) {
                        continue;
                    }
                    foreach ($bl->getContents() as $track) {
                        $secs = $secsOf($track['length']);
                        $out[] = [
                            'type' => 0, 'id' => (int) $track['item_id'], 'secs' => $secs,
                            'cliplength' => $track['length'], 'cuein' => $track['cuein'], 'cueout' => $track['cueout'],
                            'fadein' => $track['fadein'], 'fadeout' => $track['fadeout'],
                        ];
                    }

                    continue;
                }
                [, $limitModifier] = $bl->getLimitValueAndModifier() ?: [null, null];
                if ($remainingBlocksOnly && $limitModifier !== 'remaining') {
                    continue;
                }
                // RASTATIME 2026-10-06 - the budget is what is laid out so far,
                // and a "time remaining" block is picked against it between its
                // real neighbours (Scheduler::pickRemainingBlock, shared with the
                // show builder; insertFitting() still checks the real end).
                $budget = max(0.0, (float) $budgetSecs - Application_Model_Scheduler::laidOutLength($rowsOf($out), $prevFileId, $nextFileId));
                // RASTATIME 2026-10-23 - the files gathered so far are out for
                // the block's "played lately" filters (Block::setPickedInFill)
                Application_Model_Block::setPickedInFill(array_map(function ($c) {
                    return $c['type'] === 0 ? (int) $c['id'] : 0;
                }, $out));
                $picked = Application_Model_Scheduler::pickDynamicBlock($bl, $budget, $lastOf($out), $nextFileId);
                foreach ($picked as $f) {
                    $file = CcFilesQuery::create()->findPk((int) $f['id']);
                    if ($file === null || !$file->visible()) {
                        continue;
                    }
                    $cuein = (float) Application_Common_DateHelper::calculateLengthInSeconds($file->getDbCuein());
                    $cueout = (float) Application_Common_DateHelper::calculateLengthInSeconds($file->getDbCueout());
                    $secs = max(0.0, $cueout - $cuein);
                    $out[] = [
                        'type' => 0, 'id' => (int) $file->getDbId(), 'secs' => $secs,
                        'cliplength' => Application_Common_DateHelper::secondsToPlaylistTime($secs),
                        'cuein' => $file->getDbCuein(), 'cueout' => $file->getDbCueout(),
                        'fadein' => $fadeIn, 'fadeout' => $fadeOut,
                    ];
                }

                continue;
            }
            if ($remainingBlocksOnly) {
                continue;
            }
            $secs = $secsOf($item['length']);
            if ($type === 0) {
                $out[] = [
                    'type' => 0, 'id' => (int) $item['item_id'], 'secs' => $secs,
                    'cliplength' => $item['length'], 'cuein' => $item['cuein'], 'cueout' => $item['cueout'],
                    'fadein' => $item['fadein'], 'fadeout' => $item['fadeout'],
                ];
            } elseif ($type === 1) {
                // webstream (schedule discriminator 1)
                $out[] = [
                    'type' => 1, 'id' => (int) $item['item_id'], 'secs' => $secs,
                    'cliplength' => $item['length'], 'cuein' => $item['cuein'], 'cueout' => $item['cueout'],
                    'fadein' => '00.500000', 'fadeout' => '00.500000',
                ];
            } elseif ($type === 3) {
                // line-in (playlist type 3 = schedule discriminator 2, no fades)
                $out[] = [
                    'type' => 2, 'id' => (int) $item['item_id'], 'secs' => $secs,
                    'cliplength' => $item['length'], 'cuein' => $item['cuein'] ?? '00:00:00',
                    'cueout' => $item['cueout'] ?? $item['length'],
                    'fadein' => '00:00:00.000000', 'fadeout' => '00:00:00.000000',
                ];
            } else {
                continue;
            }
        }

        return $out;
    }

    /**
     * Insert the longest prefix of $candidates that fits before the show's
     * end when placed after row index $at (0 = at the start), in one
     * scheduler call.  Strictly in order: the first item that does not fit
     * ends the list (variant a).
     *
     * @return int rows inserted
     */
    private static function insertFitting(
        Application_Model_ShowInstance $si,
        array $rows,
        $at,
        array $candidates,
        $showStart,
        $showEnd,
        array $house,
        $label
    ) {
        if (empty($candidates)) {
            return 0;
        }
        $at = max(0, min((int) $at, count($rows)));
        $ids = array_merge(array_column($rows, 'fileId'), array_map(function ($c) {
            return $c['type'] === 0 ? $c['id'] : null;
        }, $candidates));
        $info = Application_Model_Scheduler::crossfadeInfoForFiles($ids);

        $accepted = [];
        foreach ($candidates as $c) {
            $trial = array_merge(
                array_slice($rows, 0, $at),
                $accepted,
                [['fileId' => $c['type'] === 0 ? $c['id'] : null, 'secs' => $c['secs']]],
                array_slice($rows, $at)
            );
            if (self::chainEnd($trial, $showStart, $house, $info) > $showEnd + 0.0005) {
                break;
            }
            $accepted[] = ['fileId' => $c['type'] === 0 ? $c['id'] : null, 'secs' => $c['secs'], 'file' => $c];
        }
        if (count($accepted) < count($candidates)) {
            Logging::info(sprintf(
                'AutoPlaylistManager: %s - %d of %d items fit, the rest is left out (show_instance_id=%d)',
                $label, count($accepted), count($candidates), $si->getShowInstanceId()
            ));
        }
        if (empty($accepted)) {
            return 0;
        }
        $afterRowId = $at > 0 ? (int) $rows[$at - 1]['id'] : 0;
        $files = array_map(function ($a) {
            $f = $a['file'];
            unset($f['secs']);

            return $f;
        }, $accepted);
        $si->addFilesAfter($afterRowId, $files);

        return count($accepted);
    }

    /**
     * RASTATIME 2026-06-07 — Song Requests: true if cc_playlist $playlistId
     * contains at least one smart block with the "use requests" criterion
     * (cc_blockcriteria.criteria = 'use_requests', value = '1').  This is
     * the IMPLICIT marker that turns an autoload-playlist show into a
     * "request show" handled by the incremental just-in-time fill below
     * (no separate per-show flag — operator decision 2026-06-07).
     */
    public static function playlistContainsRequestBlock($playlistId)
    {
        if (empty($playlistId)) {
            return false;
        }
        $sql = "SELECT 1
                FROM cc_playlistcontents pc
                JOIN cc_blockcriteria bc ON bc.block_id = pc.block_id
                WHERE pc.playlist_id = :pid
                  AND pc.block_id IS NOT NULL
                  AND bc.criteria = 'use_requests'
                  AND bc.value = '1'
                LIMIT 1";
        $row = Application_Common_Database::prepareAndExecute(
            $sql,
            [':pid' => (int) $playlistId],
            'column'
        );

        return !empty($row);
    }

    /**
     * RASTATIME 2026-06-16 — Traffic Alerts: does this autoload playlist place
     * the Settings-configured traffic-alert smart block into a show's
     * dramaturgy?  Such a show is filled incrementally (like a request show) so
     * that traffic alerts imported while it is already on air are picked up at
     * the next traffic slot.  Returns false when the feature is disabled
     * (no traffic block configured, id 0).
     */
    public static function playlistContainsTrafficBlock($playlistId)
    {
        if (empty($playlistId)) {
            return false;
        }
        $trafficBlockId = Application_Model_Preference::getTrafficAlertBlockId();
        if ($trafficBlockId <= 0) {
            return false;  // feature disabled — no traffic block selected
        }
        $row = Application_Common_Database::prepareAndExecute(
            "SELECT 1
                FROM cc_playlistcontents pc
                WHERE pc.playlist_id = :pid
                  AND pc.block_id = :bid
                LIMIT 1",
            [':pid' => (int) $playlistId, ':bid' => (int) $trafficBlockId],
            'column'
        );

        return !empty($row);
    }

    /**
     * RASTATIME 2026-06-07 — Song Requests: request-show fill (Option
     * C-onepass).  For every request show (has_autoplaylist + an autoload
     * playlist that containsRequestBlock) that is currently running OR
     * starts within $leadSecs, fill its schedule by walking the autoload
     * playlist POSITION BY POSITION (see _fillRequestShowByPositions): each
     * position is resolved on its own and a Phase 6a consume runs in
     * between, so several "use requests" blocks in one playlist each draw a
     * DIFFERENT track (the operator's fixed dramaturgy, e.g. jingle · track ·
     * request · jingle · music · request · … · music-time-remaining).
     *
     * We deliberately do NOT set autoplaylist_built; the fill is idempotent
     * (a full show is a no-op) so it is safe to re-run every poll.  Append-
     * only (never insert): nothing already scheduled is pushed back, so a
     * following show is never overbooked.
     */
    public static function fillRequestShows($leadSecs)
    {
        $now = new DateTime('now', new DateTimeZone('UTC'));
        $future = clone $now;
        $future->add(new DateInterval('PT' . (int) $leadSecs . 'S'));

        // Instances not yet ended that have already started or start
        // within the lead window, restricted to shows with an autoload
        // playlist.  (Request-show-ness is confirmed per-instance below.)
        $instances = CcShowInstancesQuery::create()
            ->filterByDbModifiedInstance(false)
            ->filterByDbEnds($now, Criteria::GREATER_THAN)
            ->filterByDbStarts($future, Criteria::LESS_THAN)
            ->useCcShowQuery('a', 'left join')
                ->filterByDbHasAutoPlaylist(true)
            ->endUse()
            ->find();

        foreach ($instances as $instance) {
            $si = new Application_Model_ShowInstance($instance->getDbId());
            $playlistId = $si->GetAutoPlaylistId();
            if (empty($playlistId)
                || (!self::playlistContainsRequestBlock($playlistId)
                    && !self::playlistContainsTrafficBlock($playlistId))
            ) {
                continue;  // neither a request nor a traffic show — leave it to buildAutoPlaylist
            }
            self::_fillRequestShowByPositions($si, $playlistId);
        }
    }

    /**
     * RASTATIME 2026-06-16 — Mid-Show Song Requests (incremental fill,
     * Variante a).  Fill a request-show instance by walking its autoload
     * playlist POSITION BY POSITION (cc_playlistcontents order) — but
     * INCREMENTALLY across the 2-minute poll cycles, only a little ahead of
     * the play head, instead of resolving the whole dramaturgy in one pass.
     *
     * A persistent per-instance cursor (cc_show_instances.autoplaylist_cursor)
     * remembers the next UNRESOLVED dramaturgy position, so each poll continues
     * where the last one stopped rather than re-filling from position 0 (which
     * would double the dramaturgy).  Because a "use requests" block placed
     * later in the dramaturgy is now resolved only when its slot is about to
     * play, it draws the requests that arrived WHILE the show was already on
     * air — the whole point of mid-show requests.
     *
     * Dead-air safety: dramaturgy positions are resolved up to
     * now + _REQUEST_FILL_AHEAD_SECONDS (default 5 min, > the 2-min poll
     * interval) so the show stays filled ahead of the play head between polls.
     * Once the dramaturgy is exhausted (cursor at its end) the trailing
     * time-remaining block is topped up COMPLETELY to the show end — the long
     * music tail has no freshness requirement and must never risk dead air.
     *
     * Resolving one element at a time — with a Phase-6a consume after each —
     * is also what makes several "use requests" blocks draw DIFFERENT tracks.
     * An empty request slot falls back to a random catalogue track
     * (_appendPosition).  A fixed-file final slot is not repeated.
     *
     * RASTATIME 2026-06-16 — Traffic Alerts reuse the very same incremental
     * walk: a position pointing at the Settings-configured traffic-alert block
     * is resolved by _appendTrafficAlert (newest queued alert, exclude already
     * scheduled, no random fallback) instead of the request path.  Because the
     * dramaturgy is resolved only just ahead of the play head, an alert
     * imported mid-show is picked up at the next traffic slot — no following
     * item has to be pushed back, so there is no schedule-shift to undo.
     */
    private static function _fillRequestShowByPositions($si, $playlistId)
    {
        // The Settings-configured traffic-alert block (0 = feature disabled);
        // a position pointing at it is resolved as a traffic slot below.
        $trafficBlockId = Application_Model_Preference::getTrafficAlertBlockId();

        $positions = Application_Common_Database::prepareAndExecute(
            "SELECT pc.type, pc.file_id, pc.block_id, pc.stream_id, pc.position,
                    (EXISTS (
                        SELECT 1 FROM cc_blockcriteria bc
                         WHERE bc.block_id = pc.block_id
                           AND bc.criteria = 'use_requests' AND bc.value = '1'
                    ))::int AS is_request_block,
                    COALESCE((pc.block_id = :tbid)::int, 0) AS is_traffic_block
               FROM cc_playlistcontents pc
              WHERE pc.playlist_id = :pid
              ORDER BY pc.position",
            [':pid' => (int) $playlistId, ':tbid' => (int) $trafficBlockId],
            Application_Common_Database::ALL
        );
        if (empty($positions)) {
            return;
        }

        $instanceId = $si->getShowInstanceId();
        $startTs = $si->getShowInstanceStart(null)->getTimestamp();
        $endTs = $si->getShowInstanceEnd(null)->getTimestamp();

        // Resolve the dramaturgy this far ahead of the play head this poll.
        $fillAhead = (int) (getenv('RASTATIME_REQUEST_FILL_AHEAD_SECONDS')
            ?: self::$_REQUEST_FILL_AHEAD_SECONDS);
        $fillUntilTs = max(time(), $startTs) + $fillAhead;

        $count = count($positions);

        // Persistent cursor: the next UNRESOLVED dramaturgy position.  Clamped
        // in case the playlist was edited shorter mid-show.
        $cursor = min(self::_getAutoplaylistCursor($instanceId), $count);

        // --- Dramaturgy: resolve positions from the cursor, ahead of the play
        //     head, drawing the CURRENT requests for each slot.
        $guard = 0;
        while ($cursor < $count && $guard < 200) {
            $filledTo = $startTs + $si->getTimeScheduledSecs();
            if ($filledTo >= $endTs) {
                $cursor = $count;  // show already full — dramaturgy effectively done
                break;
            }
            if ($filledTo >= $fillUntilTs) {
                break;  // filled far enough ahead; the next poll continues here
            }
            self::_appendPosition($si, $positions[$cursor]);
            // Phase 6a: consume the request track(s) just scheduled so the NEXT
            // request block draws a different (and now possibly newer) track.
            self::_consumeScheduledRequests($instanceId);
            $cursor++;
            $guard++;
        }

        self::_setAutoplaylistCursor($instanceId, $cursor);

        // --- Tail: dramaturgy done → top up the remainder with the trailing
        //     time-remaining block, all the way to the show end.  Only repeated
        //     if it is a smart block (a fixed file would be spammed).  No
        //     freshness concern, so it is filled completely (dead-air-safe).
        $fill = end($positions);
        // The trailing time-remaining block tops up to the show end — but never
        // the traffic block (alerts are not a dead-air filler).
        $canTopUp = ((int) $fill['type'] === 2) && !empty($fill['block_id'])
            && (int) ($fill['is_traffic_block'] ?? 0) !== 1;
        if ($cursor >= $count && $canTopUp) {
            $guard = 0;
            while ($guard < 200) {
                if (($startTs + $si->getTimeScheduledSecs()) >= $endTs) {
                    break;  // filled to the end
                }
                $before = $si->getTimeScheduledSecs();
                self::_appendPosition($si, $fill);
                self::_consumeScheduledRequests($instanceId);
                if ($si->getTimeScheduledSecs() <= $before) {
                    break;  // fill block exhausted — stop (no dead-air spin)
                }
                $guard++;
            }
        }
    }

    /**
     * Read cc_show_instances.autoplaylist_cursor (the next unresolved
     * dramaturgy position).  No Propel accessor — column added by raw-SQL
     * migration 0057 — so it is read directly.
     */
    private static function _getAutoplaylistCursor($instanceId)
    {
        $v = Application_Common_Database::prepareAndExecute(
            'SELECT autoplaylist_cursor FROM cc_show_instances WHERE id = :id',
            [':id' => (int) $instanceId],
            Application_Common_Database::COLUMN
        );

        return $v === false || $v === null ? 0 : (int) $v;
    }

    private static function _setAutoplaylistCursor($instanceId, $cursor)
    {
        Application_Common_Database::prepareAndExecute(
            'UPDATE cc_show_instances SET autoplaylist_cursor = :cur WHERE id = :id',
            [':cur' => (int) $cursor, ':id' => (int) $instanceId],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * Append a single autoload-playlist position to the show instance,
     * resolved against the CURRENT pool state.  Files and smart blocks are
     * supported (the request dramaturgy is built from those); stream / line-
     * in positions are skipped with a warning rather than aborting the fill.
     */
    private static function _appendPosition($si, array $pos)
    {
        $type = (int) $pos['type'];
        if ($type === 0 && !empty($pos['file_id'])) {
            $si->addAutoloadItemToShow('audioclip', (int) $pos['file_id'], false);
        } elseif ($type === 2 && !empty($pos['block_id'])) {
            $blockId = (int) $pos['block_id'];
            if ((int) ($pos['is_traffic_block'] ?? 0) === 1) {
                // Traffic-alert block: air the next queued alert (FIFO, and
                // never one already scheduled in this show).  Deliberately NO
                // random fallback — an empty traffic slot airs nothing and the
                // following dramaturgy item simply plays.
                self::_appendTrafficAlert($si, $blockId);

                return;
            }
            $before = $si->getTimeScheduledSecs();
            $si->addAutoloadItemToShow('block', $blockId, false);
            // If a "use requests" block drew nothing — no open request right
            // now — keep the dramaturgy slot filled with a RANDOM track from
            // the block's own catalogue pool (its criteria minus the request
            // filter), rather than leaving a gap.
            if ((int) ($pos['is_request_block'] ?? 0) === 1
                && $si->getTimeScheduledSecs() <= $before
            ) {
                self::_appendRandomFromBlockPool($si, $blockId);
            }
        } else {
            Logging::warn(
                'RequestShowFill: skipping unsupported autoload position type '
                . $type . ' (only file and smart-block positions are filled)'
            );
        }
    }

    /**
     * RASTATIME 2026-06-08 — Song Requests: random catalogue fallback for an
     * empty request slot.  When a "use requests" block draws nothing (no open
     * listener request at fill time), resolve the SAME block once with the
     * request filter ignored — i.e. its plain catalogue pool (genre etc.) —
     * and append ONE random track from it, so the request position still airs
     * a fitting track instead of leaving a hole in the show.
     */
    private static function _appendRandomFromBlockPool($si, $blockId)
    {
        try {
            $block = new Application_Model_Block($blockId);
            $info = $block->getListofFilesMeetCriteria(null, true);
        } catch (Exception $e) {
            Logging::warn(
                'RequestShowFill: random fallback could not load block '
                . $blockId . ': ' . $e->getMessage()
            );

            return;
        }

        $files = $info['files'] ?? null;
        if ($files === null || $files->isEmpty()) {
            return;  // the catalogue pool is empty too — leave the slot
        }

        // Collect candidate file ids (capped) and append one at random.
        $ids = [];
        $files->getFirst();
        $iterator = $files->getIterator();
        while ($iterator->valid() && count($ids) < 1000) {
            $ids[] = (int) $iterator->current()->getDbId();
            $iterator->next();
        }
        if (empty($ids)) {
            return;
        }
        $si->addAutoloadItemToShow('audioclip', $ids[array_rand($ids)], false);
    }

    /**
     * RASTATIME 2026-06-16 — Traffic Alerts: resolve the configured traffic-
     * alert smart block at one dramaturgy position.  Traffic alerts are short
     * MP3s imported at very short notice that must air within ~10 minutes; the
     * operator designates ONE smart block as their source in Settings and
     * places it into a show's dramaturgy wherever an alert may interrupt.
     *
     * Because the show is filled INCREMENTALLY (only a little ahead of the play
     * head), a traffic position is resolved just before its slot airs — so it
     * picks up alerts imported WHILE the show is already on air, the whole
     * point of the feature, and no following item ever has to be pushed back.
     *
     * Selection: from the block's current pool, air the queued alert that is
     * (a) not already scheduled anywhere in this instance — so the same alert
     * never airs twice across several traffic positions — and (b) imported
     * earliest (FIFO: the alert closest to its 10-min deadline goes first).
     * If every queued alert is already scheduled (or the block is empty) the
     * slot stays empty — unlike a request slot there is NO random fallback.
     */
    private static function _appendTrafficAlert($si, $blockId)
    {
        try {
            $block = new Application_Model_Block($blockId);
            $info = $block->getListofFilesMeetCriteria(null, false);
        } catch (Exception $e) {
            Logging::warn(
                'TrafficAlertFill: could not load traffic block '
                . $blockId . ': ' . $e->getMessage()
            );

            return;
        }

        $files = $info['files'] ?? null;
        if ($files === null || $files->isEmpty()) {
            return;  // no traffic alert queued in the block — leave the slot empty
        }

        // Candidate alert ids from the block's pool (capped defensively).
        $ids = [];
        $iterator = $files->getIterator();
        while ($iterator->valid() && count($ids) < 1000) {
            $ids[] = (int) $iterator->current()->getDbId();
            $iterator->next();
        }
        if (empty($ids)) {
            return;
        }

        // Pick the earliest-imported alert NOT already scheduled in this show.
        // One SQL does the exclude (cc_schedule of this instance) + the FIFO
        // ordering (cc_files.utime = library import time).
        $inClause = [];
        $params = [];
        foreach ($ids as $i => $fid) {
            $key = ':a' . $i;
            $inClause[] = $key;
            $params[$key] = (int) $fid;
        }
        $params[':inst'] = (int) $si->getShowInstanceId();
        $fileId = Application_Common_Database::prepareAndExecute(
            'SELECT f.id FROM cc_files f
              WHERE f.id IN (' . implode(',', $inClause) . ')
                AND f.id NOT IN (
                    SELECT s.file_id FROM cc_schedule s
                     WHERE s.instance_id = :inst AND s.file_id IS NOT NULL
                )
              ORDER BY f.utime ASC, f.id ASC
              LIMIT 1',
            $params,
            Application_Common_Database::COLUMN
        );
        if (empty($fileId)) {
            return;  // every queued alert is already scheduled in this show
        }

        $si->addAutoloadItemToShow('audioclip', (int) $fileId, false);
    }

    /**
     * RASTATIME 2026-06-07 — Song Requests, Phase 6a (consume on schedule).
     *
     * Once a request track has been written into a show's schedule it must
     * leave the request pool, otherwise the next "use requests" block draws
     * the same (oldest) track again and the show fills with duplicates.
     *
     * For every requestable track now scheduled in $instanceId we therefore
     * (1) clear the cc_files aggregate cache (requested / request_count /
     * requested_at) — the smart-block pool filter is `requested = true`, so
     * this takes the track out of any further draw — and (2) flip its still-
     * pending listener requests to 'queued' in the rastatime_song_request
     * audit log.  Both run as plain SQL, the same cross-table approach the
     * submit endpoint already uses to maintain the aggregate.
     *
     * Idempotent: a track already consumed has requested = false and is not
     * matched again.  A track pulled in by an ordinary (non-request) block is
     * consumed too — that is correct, the listener's wish aired either way.
     */
    private static function _consumeScheduledRequests($instanceId)
    {
        $rows = Application_Common_Database::prepareAndExecute(
            "SELECT DISTINCT s.file_id
               FROM cc_schedule s
               JOIN cc_files f ON f.id = s.file_id
              WHERE s.instance_id = :inst
                AND f.requested = true",
            [':inst' => (int) $instanceId],
            Application_Common_Database::ALL
        );
        if (empty($rows)) {
            return;
        }

        $fileIds = [];
        foreach ($rows as $r) {
            $fileIds[] = (int) $r['file_id'];
        }
        // Integers only (cast above) — safe to inline; PDO named params do
        // not expand to a variable-length IN (...) list.
        $idList = implode(',', $fileIds);

        // 1. Take the tracks out of the request pool (aggregate cache).
        Application_Common_Database::prepareAndExecute(
            "UPDATE cc_files
                SET requested = false, request_count = 0, requested_at = NULL
              WHERE id IN ({$idList})",
            [],
            Application_Common_Database::EXECUTE
        );

        // 2. Mark the listeners' still-pending requests as queued.
        Application_Common_Database::prepareAndExecute(
            "UPDATE rastatime_song_request
                SET status = 'queued'
              WHERE status = 'pending' AND file_id IN ({$idList})",
            [],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * Find all show instances starting in the next hour with autoplaylists not yet added to the schedule.
     *
     * @return PropelObjectCollection collection of ShowInstance objects
     *                                that have unbuilt autoplaylists
     */
    protected static function _upcomingAutoPlaylistShows()
    {
        // setting now so that past shows aren't referenced
        $now = new DateTime('now', new DateTimeZone('UTC'));
        // only build playlists for shows that start up to an hour from now
        $future = clone $now;
        $future->add(new DateInterval('PT1H'));

        return CcShowInstancesQuery::create()
            ->filterByDbModifiedInstance(false)
            ->filterByDbStarts($now, Criteria::GREATER_THAN)
            ->filterByDbStarts($future, Criteria::LESS_THAN)
            ->useCcShowQuery('a', 'left join')
            ->filterByDbHasAutoPlaylist(true)
            ->endUse()
            ->filterByDbAutoPlaylistBuilt(false)
            ->find();
    }
}
