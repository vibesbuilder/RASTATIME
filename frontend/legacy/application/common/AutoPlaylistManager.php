<?php

class AutoPlaylistManager
{
    /**
     * @var int how often, in seconds, to check for and ingest new podcast episodes
     */
    private static $_AUTOPLAYLIST_POLL_INTERVAL_SECONDS = 60;  // 10 minutes

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
