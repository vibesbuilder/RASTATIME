<?php

/**
 * RASTATIME 2026-05-21 — Auto-DJ Service (Section 23.20).
 *
 * Two passes called from {@see AutoPlaylistManager::buildAutoPlaylist()}
 * once per 60 s poll:
 *
 *   1. {@see runPrePass()}
 *      Scans the calendar for unscheduled gaps in the next 1 h and
 *      auto-creates a single "Auto DJ" show in the FIRST gap found.
 *      The new show has has_autoplaylist = TRUE and uses the
 *      operator-configured playlist as its autoplaylist, so the
 *      subsequent autoplaylist build pass in AutoPlaylistManager
 *      picks it up and fills it.
 *
 *   2. {@see runFillPass()}
 *      Walks the next 1 h of show instances; for every instance whose
 *      time_filled is more than 5 s short of the slot, appends the
 *      auto-dj playlist to the tail of that instance so the slot ends
 *      up complete.  Only runs when the operator has the
 *      "Automatically fill any show" preference enabled.
 *
 * Configuration (cc_pref keys, see Preference::Get/SetAutoDj*):
 *   - auto_dj_enabled        master on/off switch
 *   - auto_dj_show_name      default name for auto-created shows
 *   - auto_dj_playlist_id    cc_playlist.id of the filler playlist
 *   - auto_dj_fill_any_show  enables runFillPass()
 *   - auto_dj_logo_path      absolute path to default show logo (optional)
 *
 * Owner / permissions: programmatic show-creation needs an admin
 * user in the Zend_Auth session because ShowService::addUpdateShow()
 * hard-rejects non-Admin/PM callers.  {@see withAdminContext()}
 * temporarily swaps the session identity to the first available
 * admin (Application_Model_User::getFirstAdmin()) for the duration
 * of the create call and restores it afterwards.
 *
 * Operator-confirmed design decisions (2026-05-21, Q1–Q7):
 *   Q1 — search only the next 1 h (same window AutoPlaylistManager uses)
 *   Q2 — single show per gap, max 12 h
 *   Q3 — first admin as owner
 *   Q4 — same default name for every auto-created show, no timestamp
 *   Q5 — fill-pass appends at the end of existing schedule
 *   Q6 — no templates, only the 5 settings fields
 *   Q7 — minimum gap is 60 s
 */
class Application_Service_AutoDjService
{
    /** Max show length for an auto-created show.  Operator Q2 = 12 h. */
    private const MAX_SHOW_DURATION_SECS = 12 * 3600;

    /** Minimum gap that triggers a gap-filling show.  Operator Q7 = 60 s. */
    private const MIN_GAP_SECS = 60;

    /** Look-ahead window for both passes.  Operator Q1 = 1 h. */
    private const LOOKAHEAD_SECS = 3600;

    /**
     * Fill-pass threshold: a show counts as "incomplete" when more than
     * this many seconds of its slot are unscheduled.  Matches the
     * Section-23.19 outro reserve safety margin (5 s).
     */
    private const FILL_THRESHOLD_SECS = 5;

    /**
     * Pre-pass: find the next gap within LOOKAHEAD_SECS and create a
     * single Auto-DJ show inside it.  Safe to call on every
     * AutoPlaylistManager poll — no-op when the feature is disabled,
     * when no playlist is configured, or when no gap exists.
     */
    public static function runPrePass()
    {
        if (!Application_Model_Preference::GetAutoDjEnabled()) {
            return;
        }
        $playlistId = Application_Model_Preference::GetAutoDjPlaylistId();
        if (!$playlistId) {
            return;
        }

        $now = new DateTime('now', new DateTimeZone('UTC'));
        $end = (clone $now)->add(new DateInterval('PT' . self::LOOKAHEAD_SECS . 'S'));

        $gap = self::findNextGap($now, $end, self::MIN_GAP_SECS);
        if ($gap === null) {
            return;
        }

        try {
            self::createGapFillingShow($gap, (int) $playlistId);
        } catch (Throwable $e) {
            Logging::warn(
                'AutoDjService::runPrePass: failed to create gap-filling '
                . 'show for gap ' . $gap['starts']->format('c') . '–'
                . $gap['ends']->format('c') . ': ' . $e->getMessage()
            );
        }
    }

    /**
     * Fill-pass: append the auto-dj playlist to upcoming show instances
     * that are still incomplete after AutoPlaylistManager has run.
     * Skipped unless the operator has explicitly opted in via the
     * "Automatically fill any show" preference.
     */
    public static function runFillPass()
    {
        if (!Application_Model_Preference::GetAutoDjEnabled()) {
            return;
        }
        if (!Application_Model_Preference::GetAutoDjFillAnyShow()) {
            return;
        }
        $playlistId = Application_Model_Preference::GetAutoDjPlaylistId();
        if (!$playlistId) {
            return;
        }

        // Upcoming instances that have more than FILL_THRESHOLD seconds
        // of unscheduled tail.  We compare in seconds to avoid
        // interval-arithmetic pitfalls on the Propel side.
        $sql = "SELECT si.id FROM cc_show_instances si "
            . "WHERE si.starts > (NOW() AT TIME ZONE 'UTC') "
            . "  AND si.starts < (NOW() AT TIME ZONE 'UTC' + INTERVAL '"
            . self::LOOKAHEAD_SECS . " seconds') "
            . "  AND si.modified_instance = FALSE "
            . "  AND EXTRACT(EPOCH FROM (si.ends - si.starts) - COALESCE(si.time_filled, INTERVAL '0')) > :threshold";
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                $sql,
                [':threshold' => self::FILL_THRESHOLD_SECS],
                Application_Common_Database::ALL
            );
        } catch (Throwable $e) {
            Logging::warn('AutoDjService::runFillPass: query failed: ' . $e->getMessage());
            return;
        }
        if (empty($rows)) {
            return;
        }

        foreach ($rows as $row) {
            $instanceId = (int) $row['id'];
            try {
                $si = new Application_Model_ShowInstance($instanceId);
                // checkUserPerm = false because we are running in the
                // task-manager polling context; reserve = 0 because
                // there is no outro to protect (fill-pass runs *after*
                // the autoplaylist build, including outro insertion).
                $si->addPlaylistToShow((int) $playlistId, false, 0);
            } catch (Throwable $e) {
                Logging::warn(
                    'AutoDjService::runFillPass: failed to fill '
                    . 'instance_id=' . $instanceId . ': ' . $e->getMessage()
                );
            }
        }
    }

    /**
     * Find the earliest unscheduled gap that *starts* within
     * [$from, $lookaheadEnd] and is at least $minGapSecs long.
     * Returns null if no such gap exists.
     *
     * RASTATIME 2026-05-21 v4 — the v3 query bounded the search by
     * `starts < :end_dt` (= lookahead window end).  That had a
     * subtle and very visible bug: for a long gap (e.g. 14:07–15:00,
     * 53 min) where the next scheduled show after the gap (15:00)
     * was *outside* the 1 h lookahead window, the query returned
     * no row for that follow-on show, the cursor walked to
     * `$lookaheadEnd` (14:31:51 on the 13:31:51 poll), and the
     * tail-gap branch returned the gap clamped to that lookahead
     * end.  The auto-loop created a 25-min show.  60 s later the
     * next poll saw the rest of the gap (14:31:51–...) and
     * created a tiny 1-min show.  Repeat 17 times.
     *
     * v4 widens the query to *all* upcoming instances (with a
     * safety LIMIT) so the cursor sees the real next-show boundary
     * even when it sits beyond the lookahead window.  The lookahead
     * is still used as the "only return a gap that *starts* before
     * here" filter so we never auto-create shows further than 1 h
     * ahead.  The 12 h cap in `createGapFillingShow()` still
     * applies when the gap itself is longer than 12 h.
     *
     * @return array{starts: DateTime, ends: DateTime, duration_secs: int}|null
     */
    private static function findNextGap(DateTime $from, DateTime $lookaheadEnd, $minGapSecs)
    {
        $sql = "SELECT starts, ends FROM cc_show_instances "
            . "WHERE ends > :from_dt "
            . "  AND modified_instance = FALSE "
            . "ORDER BY starts ASC "
            . "LIMIT 200";  // safety; far above any realistic day's show count
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                $sql,
                [':from_dt' => $from->format('Y-m-d H:i:s')],
                Application_Common_Database::ALL
            );
        } catch (Throwable $e) {
            Logging::warn('AutoDjService::findNextGap: query failed: ' . $e->getMessage());
            return null;
        }

        $cursor = clone $from;
        if (is_array($rows)) {
            foreach ($rows as $row) {
                $startsAt = new DateTime($row['starts'], new DateTimeZone('UTC'));
                $endsAt   = new DateTime($row['ends'], new DateTimeZone('UTC'));

                if ($startsAt > $cursor) {
                    // Gap from $cursor to $startsAt.  Only return if it
                    // STARTS within the lookahead window — preserves
                    // operator Q1 ("only the next gap inside 1 h").
                    if ($cursor < $lookaheadEnd) {
                        $gapSecs = $startsAt->getTimestamp() - $cursor->getTimestamp();
                        if ($gapSecs >= $minGapSecs) {
                            return [
                                'starts'        => clone $cursor,
                                'ends'          => $startsAt,
                                'duration_secs' => $gapSecs,
                            ];
                        }
                    } else {
                        // The first remaining gap starts after the
                        // lookahead window — no relevant gaps for
                        // this poll.
                        return null;
                    }
                }
                if ($endsAt > $cursor) {
                    $cursor = $endsAt;
                }
            }
        }

        // No more known shows.  Tail-gap = from $cursor until "no
        // show ever".  Bound it by MAX_SHOW_DURATION_SECS as a
        // safety net so we don't auto-create a single multi-day
        // show for an empty calendar.  Same operator Q1 guard:
        // only return when the gap starts within the lookahead.
        if ($cursor < $lookaheadEnd) {
            $tailEnd = (clone $cursor)->add(new DateInterval(
                'PT' . self::MAX_SHOW_DURATION_SECS . 'S'
            ));
            $tailSecs = $tailEnd->getTimestamp() - $cursor->getTimestamp();
            if ($tailSecs >= $minGapSecs) {
                return [
                    'starts'        => clone $cursor,
                    'ends'          => $tailEnd,
                    'duration_secs' => $tailSecs,
                ];
            }
        }
        return null;
    }

    /**
     * Create a non-repeating Auto-DJ show inside the given gap.
     * Duration is clamped to MAX_SHOW_DURATION_SECS per operator Q2.
     *
     * RASTATIME 2026-05-21 v3 — direct Propel insertion path,
     * replaces the v1/v2 ShowService::addUpdateShow() approach.
     * Reason: ShowService and its internal helpers touch session-
     * backed state (RabbitMQ helpers, intro/outro lookups,
     * UserService::getCurrentUser) that trip Zend strict-mode
     * session guards from a polling-job context — neither writing
     * to the existing session storage (v1) nor swapping the auth
     * storage adapter (v2) was enough to silence them.  The v3
     * path writes only the three rows the calendar event-feed and
     * AutoPlaylistManager need to discover the show:
     *     cc_show + cc_show_days + cc_show_instances
     * No hosts, no rebroadcasts, no linked-show machinery —
     * Auto-DJ shows are intentionally bare filler.
     *
     * @param array{starts: DateTime, ends: DateTime, duration_secs: int} $gap
     * @param int $playlistId  cc_playlist.id of the filler playlist
     *
     * @return int the new show id
     */
    private static function createGapFillingShow(array $gap, $playlistId)
    {
        $startsUtc = clone $gap['starts'];
        $startsUtc->setTimezone(new DateTimeZone('UTC'));
        $endsUtc   = clone $gap['ends'];
        $endsUtc->setTimezone(new DateTimeZone('UTC'));

        // RASTATIME 2026-05-21 v6 — round the slot boundaries to
        // whole minutes.  Pre-v6 a gap that started at e.g.
        // 15:08:34 produced a show with sub-minute start/end
        // timestamps, which the Edit-Show form (minute-granularity)
        // could not round-trip cleanly:
        //   - the End-Time field rendered one minute short of the
        //     real end (e.g. 16:59 for a 17:00:00 ends),
        //   - and AddShowWhen's overlap check then refused to save
        //     a shortened version of the show ("Cannot schedule
        //     overlapping shows"), because the form's recomputed
        //     end timestamp shifted by 34 s relative to the
        //     original cc_show_instances row.
        //
        // Round start UP to the next whole minute (never earlier
        // than the gap start — protects the preceding show) and
        // round end DOWN to the previous whole minute (never later
        // than the gap end — protects the following show).  This
        // forfeits at most ~59 s at each end but produces shows
        // the rest of the legacy form/model code can safely edit.
        $startSecs = (int) $startsUtc->format('s');
        if ($startSecs > 0) {
            $startsUtc->add(new DateInterval('PT' . (60 - $startSecs) . 'S'));
        }
        $endsUtc->setTime(
            (int) $endsUtc->format('H'),
            (int) $endsUtc->format('i'),
            0
        );

        $durationSecs = $endsUtc->getTimestamp() - $startsUtc->getTimestamp();
        // After rounding the gap may be too small to host a show.
        if ($durationSecs < self::MIN_GAP_SECS) {
            return 0;
        }
        // Apply the 12 h cap (operator Q2).
        if ($durationSecs > self::MAX_SHOW_DURATION_SECS) {
            $durationSecs = self::MAX_SHOW_DURATION_SECS;
            $endsUtc = (clone $startsUtc)->add(
                new DateInterval('PT' . $durationSecs . 'S')
            );
        }

        // RASTATIME 2026-05-21 v5 — store cc_show_days.start_time +
        // .timezone in the *operator's* timezone, NOT in UTC.  v3/v4
        // wrote both fields as UTC, which made the calendar render
        // correctly (because cc_show_instances.starts is the
        // authoritative UTC timestamp) but the Edit-Show dialog
        // reads the operator-local representation from cc_show_days
        // and was showing the show 2 h earlier than the operator
        // expected on UTC+2 systems.  ShowService::setCcShowDays()
        // already follows this convention (line 1788–1791); we
        // mirror it here so an Auto-DJ show round-trips correctly
        // through the Edit dialog.
        $opTz = Application_Model_Preference::GetDefaultTimezone();
        if (empty($opTz)) {
            $opTz = 'UTC';
        }
        $startsLocal = clone $startsUtc;
        $startsLocal->setTimezone(new DateTimeZone($opTz));

        // Duration string "HH:MM:00" — by v6 we always have whole
        // minutes (rounded above) so the seconds slot is always 00.
        $h = intdiv($durationSecs, 3600);
        $m = intdiv($durationSecs % 3600, 60);
        $durationStr = sprintf('%02d:%02d:00', $h, $m);

        // Pull all defaults from cc_pref.
        $showName    = Application_Model_Preference::GetAutoDjShowName();
        $logoPath    = Application_Model_Preference::GetAutoDjLogoPath();
        $showUrl     = Application_Model_Preference::GetAutoDjShowUrl();
        $showGenre   = Application_Model_Preference::GetAutoDjShowGenre();
        $showDesc    = Application_Model_Preference::GetAutoDjShowDescription();
        $showBgColor = Application_Model_Preference::GetAutoDjShowBgColor();
        $showFgColor = Application_Model_Preference::GetAutoDjShowTextColor();

        $con = Propel::getConnection();
        $con->beginTransaction();
        try {
            // 1. cc_show — the show definition the calendar renders.
            $ccShow = new CcShow();
            $ccShow->setDbName($showName);
            $ccShow->setDbDescription($showDesc);
            $ccShow->setDbUrl($showUrl);
            $ccShow->setDbGenre($showGenre);
            if ($showFgColor !== '') {
                $ccShow->setDbColor($showFgColor);
            }
            if ($showBgColor !== '') {
                $ccShow->setDbBackgroundColor($showBgColor);
            }
            $ccShow->setDbLiveStreamUsingAirtimeAuth(false);
            $ccShow->setDbLiveStreamUsingCustomAuth(false);
            $ccShow->setDbLinked(false);
            $ccShow->setDbHasAutoPlaylist(true);
            $ccShow->setDbAutoPlaylistRepeat(true);
            $ccShow->setDbAutoPlaylistId($playlistId);
            $ccShow->setDbOverrideIntroPlaylist(false);
            $ccShow->setDbOverrideOutroPlaylist(false);
            if (!empty($logoPath)) {
                $ccShow->setDbImagePath($logoPath);
            }
            $ccShow->save($con);
            $showId = (int) $ccShow->getDbId();

            // 2. cc_show_days — one row, single-occurrence,
            //    repeat_type = -1 ("no repeat").  first_show /
            //    last_show / start_time / day are stored in the
            //    operator's timezone (matches the convention in
            //    ShowService::setCcShowDays); the absolute
            //    starts/ends timestamps on cc_show_instances stay
            //    in UTC below.
            $ccShowDays = new CcShowDays();
            $ccShowDays->setDbFirstShow($startsLocal->format('Y-m-d'));
            $ccShowDays->setDbLastShow($startsLocal->format('Y-m-d'));
            $ccShowDays->setDbStartTime($startsLocal->format('H:i:s'));
            $ccShowDays->setDbTimezone($opTz);
            $ccShowDays->setDbDuration($durationStr);
            $ccShowDays->setDbDay((int) $startsLocal->format('w'));
            $ccShowDays->setDbRepeatType(-1);
            $ccShowDays->setDbShowId($showId);
            $ccShowDays->setDbRecord(0);
            $ccShowDays->save($con);

            // 3. cc_show_instances — the concrete future occurrence.
            //    AutoPlaylistManager::_upcomingAutoPlaylistShows()
            //    walks this table; until the row exists the show is
            //    invisible to the autoplaylist build loop.
            $ccShowInstance = new CcShowInstances();
            $ccShowInstance->setDbShowId($showId);
            $ccShowInstance->setDbStarts($startsUtc);
            $ccShowInstance->setDbEnds($endsUtc);
            $ccShowInstance->setDbRecord(0);
            $ccShowInstance->setDbRebroadcast(0);
            $ccShowInstance->setDbModifiedInstance(false);
            $ccShowInstance->setDbAutoPlaylistBuilt(false);
            // setDbCreated may be auto-set in preInsert; set
            // explicitly to be safe.
            $ccShowInstance->setDbCreated(
                new DateTime('now', new DateTimeZone('UTC'))
            );
            $ccShowInstance->save($con);

            $con->commit();
        } catch (Throwable $e) {
            $con->rollback();
            throw $e;
        }

        Logging::info(
            'AutoDjService: created gap-filling show id=' . $showId
            . ' name=' . $showName
            . ' starts=' . $startsUtc->format('c')
            . ' duration_secs=' . $durationSecs
            . ' playlist_id=' . $playlistId
        );

        return $showId;
    }

}
