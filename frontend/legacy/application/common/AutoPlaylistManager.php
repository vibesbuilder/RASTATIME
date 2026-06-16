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

            // call the addPlaylist to show function and don't check for user permission to avoid call to non-existant user object
            $sid = $si->getShowId();
            $playlistrepeat = new Application_Model_Show($sid);
            if ($playlistrepeat->getHasOverrideIntroPlaylist()) {
                $introplaylistid = $playlistrepeat->getIntroPlaylistId();
            } else {
                $introplaylistid = Application_Model_Preference::GetIntroPlaylist();
            }

            if ($playlistrepeat->getHasOverrideOutroPlaylist()) {
                $outroplaylistid = $playlistrepeat->getOutroPlaylistId();
            } else {
                $outroplaylistid = Application_Model_Preference::GetOutroPlaylist();
            }

            // we want to check and see if we need to repeat this process until the show is 100% scheduled
            // so we create a while loop and break it immediately if repeat until full isn't enabled
            // otherwise we continue to go through adding playlists, including the intro and outro if enabled
            $full = false;
            $repeatuntilfull = $playlistrepeat->getAutoPlaylistRepeat();
            $tempPercentScheduled = 0;
            $si = new Application_Model_ShowInstance($autoplaylist->getDbId());

            // the intro playlist should be added exactly once
            if ($introplaylistid != null) {
                // Logging::info('adding intro');
                $si->addPlaylistToShowStart($introplaylistid, false);
            }

            // RASTATIME 2026-05-20 — Section 23.19 v5.  Measure the
            // outro length by a trial-insert + roll-back, then
            // restore `cc_files.is_scheduled` for the files that the
            // trial transiently flipped to TRUE.
            //
            // v1 tried to read `cc_playlist.length` directly — broke
            // for smart-block-bearing playlists (length stays 0).
            // v2/v3 fixed the edge case + filter bugs but still hit
            // the length=0 problem.
            // v4 introduced the trial-insert measurement, which works
            // for length — but left a side effect: the scheduler's
            // INSERT pass calls `BasePeer::doUpdate(..., IS_SCHEDULED=TRUE)`
            // on every cc_files row it adds to the schedule.  The
            // subsequent DELETE on cc_schedule does NOT walk back
            // that flag, so after the trial pass the outro's track
            // pool was marked "already scheduled".  Smart blocks
            // configured with "only_unplayed = true" or sort modes
            // that exclude scheduled tracks then picked from a
            // poisoned pool and the autoplaylist could not fill the
            // slot — empirically observed as the same 2 tracks
            // ("Dogs", "Roxanne") repeating across every test
            // because those were the only tracks not yet flagged.
            //
            // v5 snapshots the set of cc_files.id with is_scheduled
            // = TRUE *before* the trial insert (= AFTER the intro
            // insert, so intro tracks are already in the snapshot
            // and are not reset), runs the trial, identifies the
            // newly-scheduled files (now TRUE but not in the
            // snapshot), and resets them to FALSE *before* the
            // DELETE on cc_schedule.  Order matters: reset the flag
            // first because the DELETE removes the schedule rows
            // that justify the TRUE flag in the first place; if we
            // ran the DELETE first a concurrent reader could see
            // is_scheduled=TRUE without a corresponding cc_schedule
            // row.
            //
            // Trade-off: dynamic smart blocks may pick a different
            // track set on the second (real) insert than on the
            // trial pass, so the measured length is approximate.  We
            // accept the approximation because (a) the variance is
            // bounded by the smart block's own length limit and (b)
            // any small overflow is intentionally kept (see edge
            // case below — operator decision 2026-05-20 v3:
            // "overfilled is better than underfilled").
            $instanceId = $autoplaylist->getDbId();
            $outroLenSecs = 0;
            if ($outroplaylistid != null) {
                try {
                    // Snapshot cc_files.is_scheduled (TRUE rows) before
                    // the trial insert.
                    $beforeRows = Application_Common_Database::prepareAndExecute(
                        'SELECT id FROM cc_files WHERE is_scheduled = TRUE',
                        [],
                        Application_Common_Database::ALL
                    );
                    $beforeIsScheduledIds = array_map(
                        function ($r) { return (int) $r['id']; },
                        is_array($beforeRows) ? $beforeRows : []
                    );

                    $row = Application_Common_Database::prepareAndExecute(
                        'SELECT COALESCE(MAX(id), 0) AS max_id '
                        . 'FROM cc_schedule WHERE instance_id = :id',
                        [':id' => $instanceId],
                        Application_Common_Database::SINGLE
                    );
                    $maxIdBefore = (int) ($row['max_id'] ?? 0);
                    $beforeFilled = $si->getTimeScheduledSecs();

                    // Trial insert
                    $si->addPlaylistToShow($outroplaylistid, false);
                    $afterFilled = $si->getTimeScheduledSecs();
                    // RASTATIME 2026-05-20 v8 — safety margin on top
                    // of the measured outro length so the
                    // autoplaylist's reserve absorbs crossfade
                    // shifts the Scheduler applies later when items
                    // are actually scheduled.  v7 used 10 s but
                    // operator policy capped it back at 5 s:
                    //   * margin ≤ 5 s (any "silence" tail visible
                    //     to listeners must stay small)
                    //   * over-fill must be avoided
                    //   * if measured-vs-real divergence pushes the
                    //     show beyond the slot anyway, a post-outro
                    //     cleanup pass (see below) trims the
                    //     autoplaylist tail until the overbook is
                    //     gone — sacrificing autoplaylist length is
                    //     acceptable; overbook is not.
                    $outroLenSecs = (int) max(0, ceil($afterFilled - $beforeFilled)) + 5;

                    // Reset cc_files.is_scheduled for the files the
                    // trial transiently flipped to TRUE.  IN-list is
                    // built directly because every value was explicitly
                    // cast to (int) when the snapshot was taken, so
                    // no Injection vector exists and we avoid the PDO
                    // /Postgres int-array parameter-binding awkwardness.
                    // Sentinel "0" keeps the SQL legal when the
                    // snapshot was empty (no previously-scheduled files).
                    $idsCsv = empty($beforeIsScheduledIds)
                        ? '0'
                        : implode(',', $beforeIsScheduledIds);
                    Application_Common_Database::prepareAndExecute(
                        'UPDATE cc_files SET is_scheduled = FALSE '
                        . 'WHERE is_scheduled = TRUE '
                        . '  AND id NOT IN (' . $idsCsv . ')',
                        [],
                        Application_Common_Database::EXECUTE
                    );

                    // Roll back trial schedule rows
                    Application_Common_Database::prepareAndExecute(
                        'DELETE FROM cc_schedule '
                        . 'WHERE instance_id = :id AND id > :max_id',
                        [':id' => $instanceId, ':max_id' => $maxIdBefore],
                        Application_Common_Database::EXECUTE
                    );
                    $si->refreshScheduleStatus();
                } catch (Throwable $e) {
                    Logging::warn(
                        'AutoPlaylistManager: outro trial-measure failed for '
                        . 'playlist_id=' . $outroplaylistid
                        . ': ' . $e->getMessage()
                        . ' — autoplaylist will not reserve outro slot'
                    );
                    $outroLenSecs = 0;
                }
            }

            // Edge-case: outro length >= show slot.  Operator-confirmed
            // 2026-05-20 v3 (revised after the v2 test pass showed
            // the "skip outro" semantics created a 38 s gap):
            // **Always insert the outro**, even if that overbooks.
            // Operator policy: "Es ist besser, die Show ist
            // überfüllt, als zu wenig befüllt".  When the outro
            // alone would not fit, we still drop the reserve to
            // zero so the auto-loop fills the entire slot (otherwise
            // the loop would terminate immediately and leave the
            // auto unfilled), and then insert the outro on top
            // (overbooks).
            //
            // RASTATIME 2026-05-20 v8 — track the edge case in a
            // flag so the post-outro cleanup pass below does NOT
            // trim the autoplaylist tail when the operator
            // intentionally overbooks with an oversized outro.
            $showDurationSecs = $si->getDurationSecs();
            $outroOverbookByDesign = false;
            if ($outroLenSecs > 0 && $outroLenSecs >= $showDurationSecs) {
                Logging::warn(
                    'AutoPlaylistManager: outro length (' . $outroLenSecs . 's) >= '
                    . 'show slot (' . $showDurationSecs . 's) for show_instance_id='
                    . $instanceId
                    . ' — autoplaylist will fill the slot, outro will overbook'
                );
                $outroLenSecs = 0;
                $outroOverbookByDesign = true;
            }
            while (!$full) {
                // we do not want to try to schedule an empty playlist
                if ($playlistid != null) {
                    // RASTATIME 2026-05-20 — pass outroLenSecs as the
                    // scheduler-side reserve so any time-remaining
                    // smart block inside the autoplaylist is sized
                    // against (slot - outro) instead of the full slot.
                    $si->addPlaylistToShow($playlistid, false, $outroLenSecs);
                }
                $ps = $si->getPercentScheduled();
                $remainingSecs = $si->getSecondsRemaining();
                // RASTATIME 2026-05-20 — Section 23.19.  Replace the
                // upstream "ps > 100" termination with a check that
                // also respects the reserved outro slot: stop as soon
                // as the unscheduled tail is too small for one more
                // autoplaylist pass to fit before the outro.  When
                // outroLenSecs == 0 (no outro, or outro skipped per
                // the edge-case branch above) this degrades to
                // "stop when nothing more fits", which matches the
                // pre-2026-05-20 termination semantics.
                if ($remainingSecs <= $outroLenSecs) {
                    $full = true;
                } elseif (!$repeatuntilfull) {
                    break;
                }
                // we want to avoid an infinite loop if all of the playlists are null
                if ($playlistid == null) {
                    break;
                }
                // another possible issue would be if the show isn't increasing in length each loop
                // ie if all of the playlists being added are zero lengths this could cause an infinite loop
                if ($tempPercentScheduled == $ps) {
                    break;
                }
                // now reset it to the current percent scheduled
                $tempPercentScheduled = $ps;
            }
            // RASTATIME 2026-05-20 — Section 23.19.  Pre-2026-05-20 the
            // outro overbooked the show whenever Repeat-Until-Full was
            // on (or whenever the autoplaylist length happened to fill
            // the slot exactly).
            //
            // The in-Scheduler reserve passed into addPlaylistToShow
            // above shrinks time-remaining smart blocks against the
            // (slot − outro) limit, which is enough for the
            // "fill remaining" smart-block case.  But two upstream
            // expansion paths ignore that reserve:
            //
            //   - Static playlists are inserted at their full length
            //     (Scheduler::retrieveMediaFiles foreach on cc_playlistcontents,
            //     no trim).
            //   - Fixed-duration smart blocks honour their own
            //     cc_block.length limit, not the $showLimit parameter
            //     passed to getListOfFilesUnderLimit().
            //
            // In both cases the auto-loop ends up with
            // getSecondsRemaining() <= 0 (or, exactly enough room only
            // for the outro to start *at* the show's end timestamp,
            // which still puts the outro out-of-slot).
            //
            // ShowInstance::trimTailToReserve() handles those two
            // upstream paths by deleting tail items until at least
            // $outroLenSecs of unscheduled tail remains.  It is a
            // no-op when outroLenSecs <= 0, so the path without an
            // outro and the edge-case "outro > slot" path (which
            // also zeroes the reserve, see above) are unaffected.
            if ($outroplaylistid != null) {
                $si->trimTailToReserve($outroLenSecs);

                // RASTATIME 2026-05-20 v8 — snapshot max(id) before
                // the real outro insert so the post-outro cleanup
                // can identify "outro rows we just inserted" by
                // `id > maxIdBeforeOutro`, and never trim them.
                $row = Application_Common_Database::prepareAndExecute(
                    'SELECT COALESCE(MAX(id), 0) AS max_id '
                    . 'FROM cc_schedule WHERE instance_id = :id',
                    [':id' => $instanceId],
                    Application_Common_Database::SINGLE
                );
                $maxIdBeforeOutro = (int) ($row['max_id'] ?? 0);

                $si->addPlaylistToShow($outroplaylistid, false);

                // Post-outro cleanup: if the real outro insertion
                // overshot the slot — because the smart block picked
                // a different (longer) track on the real insert than
                // on the trial — trim autoplaylist tail items
                // (`id <= maxIdBeforeOutro`) until the show no
                // longer overbooks.  The outro itself is protected
                // by the id filter.
                //
                // Skipped in the "outro > slot" edge case (above)
                // because there the operator EXPECTS overbook —
                // the policy explicitly is "overfilled is better
                // than underfilled" when the outro is oversized.
                if (!$outroOverbookByDesign) {
                    $si->trimTailExcept($maxIdBeforeOutro, 0);
                }
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
