<?php

/**
 * Class Application_Service_ShowShiftService.
 *
 * RASTATIME 2026-06-15 — Show-Shift / "Allow delayed start", Phase 3a + 3b.
 *
 * Lets a show start LATER than its calendar slot when the preceding show
 * overran, instead of having the preceding show's tail clamped away.
 *
 * A cascade starts at an overbooking show A (its scheduled content ends after
 * its slot).  Walking forward from A with A's content end held constant:
 *
 *   - GAP / no successor — the content reaches no following show: A plays to
 *     its content end (into the gap).
 *   - ANCHOR — the next show is NOT opted in (cc_show.allow_delayed_start):
 *     it is the hard anchor.  A's content is clamped at the anchor's start;
 *     nothing past it moves.
 *   - CLEARING — the next show is opted in and COMPLETELY overrun
 *     (A's content reaches its slot end): its cc_schedule items are emptied,
 *     the empty slot stays as a "skipped" marker, and the cascade continues
 *     with the SAME content end (A plays through the emptied slot).
 *   - SHIFT — the next show is opted in and only PARTIALLY overrun: it is
 *     moved to A's content end (its END stays fixed, its items move with it;
 *     what no longer fits is clamped by the playout — or, with a filler
 *     playlist configured, swapped for fillers, see fillShiftedTail()) and
 *     the cascade ends — that show absorbs the rest, its successor starts on
 *     time.  A repeated show changes only the affected episode (marked
 *     delayed_start_from, see MARKER below).
 *
 * Finally A.ends is extended to where its content settled, so A's last item is
 * "inside" its instance and the backend playout serializer stops clamping it —
 * A airs in full with no playout-path change.  A is extended ONLY when the
 * cascade actually cleared or shifted a flagged show, so a plain overrun into
 * a gap or a non-flagged anchor keeps the current clamp behaviour.
 *
 * Forward-only per operator decision (2026-06-15): a shift is never walked back
 * automatically.  Deltas are whole seconds (strtotime), so a re-evaluated chain
 * computes sub-second deltas that floor to no-ops.
 *
 * MARKER (RASTATIME 2026-09-27, migration 0058): a shifted or cleared instance
 * carries cc_show_instances.delayed_start_from = the slot start it was moved
 * away from (NULL otherwise).  The June design used modified_instance = true
 * instead — upstream's "this occurrence was deleted" flag, which every
 * what's-on query (dashboard, live-info, widgets, calendar, show builder,
 * overlap check) filters out; the first live run showed the shifted show
 * vanish from all of them while the playout played it.  Now:
 *   - SHIFT sets delayed_start_from only, so the moved show stays visible
 *     everywhere at its new time;
 *   - CLEARING additionally keeps modified_instance = true: an emptied,
 *     never-airing occurrence IS a deleted one in upstream terms, and hiding
 *     it avoids two "current" shows (the extended A and the empty slot);
 *   - trigger shows are filtered delayed_start_from IS NULL (idempotency —
 *     an already-shifted show is not re-triggered as a new overrun origin)
 *     and modified_instance = false (deleted occurrences never trigger).
 *   ShowService::getInstance() also matches on delayed_start_from, so editing
 *   the show while an occurrence is shifted updates that occurrence instead of
 *   creating a duplicate at the series time.
 *
 * cc_show.allow_delayed_start / cc_show_instances.delayed_start_from have no
 * Propel accessors (raw-SQL migrations 0056 / 0058), so they are read and
 * written via raw SQL here, matching the rest of the feature.
 */
class Application_Service_ShowShiftService
{
    /**
     * @var int how far ahead, in seconds, a show may start before the engine
     *          acts on its overrun.  Keeps far-future shows (which may still be
     *          edited) untouched.  Env-overridable.
     */
    public const DEFAULT_LEAD_SECONDS = 900;  // 15 minutes

    /**
     * @var int overruns / residual airtimes shorter than this (seconds) are
     *          treated as zero.  Also the idempotency floor: a re-evaluated
     *          chain computes sub-second deltas that fall below this.
     */
    public const MIN_OVERRUN_SECONDS = 1;

    /**
     * Apply every pending delayed start.
     *
     * Trigger shows A (cascade origins): an instance that overruns its slot, is
     * not itself a moved/modified instance, whose overrun still lies in the
     * future, and which has started or starts within the lead window.  Each
     * cascade runs in its own transaction so one failure cannot roll back the
     * others.
     *
     * @return int the number of cascades that changed something (0 = nothing)
     */
    public static function applyDelayedStarts()
    {
        $leadSeconds = (int) (getenv('RASTATIME_SHOW_SHIFT_LEAD_SECONDS')
            ?: self::DEFAULT_LEAD_SECONDS);

        $nowUtc = gmdate('Y-m-d H:i:s');
        $horizonUtc = gmdate('Y-m-d H:i:s', time() + $leadSeconds);
        $lowerUtc = gmdate('Y-m-d H:i:s', time() - 86400);  // 1 day back (perf bound)

        // content_end computed once per row via LATERAL.
        $triggers = Application_Common_Database::prepareAndExecute(
            "SELECT a.id, a.starts, a.ends, ce.content_end
               FROM cc_show_instances a
               JOIN LATERAL (
                   SELECT MAX(ends) AS content_end
                     FROM cc_schedule WHERE instance_id = a.id
               ) ce ON true
              WHERE a.delayed_start_from IS NULL
                AND a.modified_instance = false
                AND a.starts >= :lower
                AND a.starts <= :horizon
                AND ce.content_end IS NOT NULL
                AND ce.content_end > a.ends
                AND ce.content_end > :now
              ORDER BY a.starts ASC",
            [':lower' => $lowerUtc, ':horizon' => $horizonUtc, ':now' => $nowUtc],
            Application_Common_Database::ALL
        );

        $changed = 0;
        foreach ($triggers as $a) {
            $changed += self::cascadeFrom($a);
        }

        if ($changed > 0) {
            // Tell pypo/Liquidsoap the schedule changed (same as a calendar move).
            Application_Model_RabbitMq::PushSchedule();
        }

        return $changed;
    }

    /**
     * Run one cascade from an overbooking show A.
     *
     * @param array $a cc_show_instances row for A (id, starts, ends, content_end as UTC strings)
     *
     * @return int 1 if the cascade changed something, 0 otherwise
     */
    private static function cascadeFrom($a)
    {
        $con = Propel::getConnection();
        $con->beginTransaction();

        try {
            $aId = (int) $a['id'];
            $contentEnd = $a['content_end'];
            $contentEndTs = strtotime($contentEnd . ' UTC');

            $curStarts = $a['starts'];   // walk pointer
            $finalEnd = $contentEnd;     // where A's content ultimately settles
            $acted = false;              // did we clear or shift a flagged show?

            while (true) {
                $next = Application_Common_Database::prepareAndExecute(
                    'SELECT i.id, i.starts, i.ends, s.allow_delayed_start::int AS flagged
                       FROM cc_show_instances i
                       JOIN cc_show s ON s.id = i.show_id
                      WHERE i.starts > :cs
                        AND i.modified_instance = false
                      ORDER BY i.starts ASC LIMIT 1',
                    [':cs' => $curStarts],
                    Application_Common_Database::SINGLE
                );
                if (empty($next)) {
                    $finalEnd = $contentEnd;  // no successor; A plays to content end
                    break;
                }

                $nextStartsTs = strtotime($next['starts'] . ' UTC');
                if ($contentEndTs - $nextStartsTs < self::MIN_OVERRUN_SECONDS) {
                    $finalEnd = $contentEnd;  // no overrun into next (gap); A plays to content end
                    break;
                }

                if ((int) $next['flagged'] !== 1) {
                    $finalEnd = $next['starts'];  // ANCHOR: clamp A at the anchor's start
                    break;
                }

                // flagged & overrun
                $nextEndsTs = strtotime($next['ends'] . ' UTC');
                if ($nextEndsTs - $contentEndTs < self::MIN_OVERRUN_SECONDS) {
                    // CLEARING: completely overrun → empty it, cascade continues
                    if (self::clearInstance((int) $next['id']) > 0) {
                        $acted = true;
                    }
                    $curStarts = $next['starts'];

                    continue;
                }

                // SHIFT: partially overrun → move to content end (ends fixed), chain ends
                $diff = $contentEndTs - $nextStartsTs;
                $newStarts = gmdate('Y-m-d H:i:s', $nextStartsTs + $diff);  // = content end (whole sec)
                Application_Common_Database::prepareAndExecute(
                    'UPDATE cc_show_instances
                        SET delayed_start_from = starts, starts = :ns
                      WHERE id = :id',
                    [':ns' => $newStarts, ':id' => (int) $next['id']],
                    Application_Common_Database::EXECUTE
                );
                Application_Service_SchedulerService::updateScheduleStartTime(
                    [(int) $next['id']],
                    $diff
                );
                // RASTATIME 2026-09-27 — instead of leaving the shifted show's
                // tail to the playout clamp, swap the tracks that no longer
                // fit for filler tracks (operator decisions, see method doc).
                self::fillShiftedTail((int) $next['id'], $newStarts, $next['ends']);
                $acted = true;
                $finalEnd = $contentEnd;
                break;
            }

            $changed = 0;
            if ($acted) {
                // Extend A.ends to where its content settled so A's last item is
                // "inside" its instance.  Skip the write if it's already there.
                if (abs(strtotime($a['ends'] . ' UTC') - strtotime($finalEnd . ' UTC')) >= 1) {
                    Application_Common_Database::prepareAndExecute(
                        'UPDATE cc_show_instances SET ends = :fe WHERE id = :id',
                        [':fe' => $finalEnd, ':id' => $aId],
                        Application_Common_Database::EXECUTE
                    );
                }
                $changed = 1;
            }

            $con->commit();

            if ($changed) {
                Logging::info(
                    "ShowShiftService: cascade from instance {$aId} "
                    . "(content to {$contentEnd}, settled at {$finalEnd})"
                );
            }

            return $changed;
        } catch (Throwable $e) {
            $con->rollback();
            Logging::error(
                'ShowShiftService cascade failed for instance ' . ($a['id'] ?? '?')
                . ': ' . $e->getMessage()
            );

            return 0;
        }
    }

    /**
     * Empty a completely-overrun instance, leaving the slot as a "skipped"
     * marker.  Mirrors the essential steps of SchedulerService::emptyShowContent
     * for a SINGLE instance (no linked-instance fan-out): delete its schedule,
     * zero its fill, mark the episode, and drop is_scheduled for tracks no
     * longer scheduled anywhere.
     *
     * @param int $instanceId
     *
     * @return int number of cc_schedule rows deleted
     */
    // ------------------------------------------------------------------
    // RASTATIME 2026-09-27 — Filler instead of cut (Show-Shift extension)
    // ------------------------------------------------------------------

    /**
     * After a SHIFT moved show B later by the overrun, B's content now sticks
     * out past B.ends.  The plain behaviour leaves that to the playout clamp,
     * which cuts B's last track mid-word.  With a filler playlist configured
     * (Settings → General → "Show-Shift Filler Playlist") this method instead:
     *
     *   1. keeps B's OUTRO pinned to the slot end, if B ends with its outro
     *      playlist (the show's own "Select Outro Playlist" or the global
     *      default) — verified by matching the outro's tracks as a suffix of
     *      B's rows, never assumed;
     *   2. removes, from the end of the remaining body, every row that no
     *      longer fits before the outro (or before B.ends) — one or several
     *      (operator decision D3);
     *   3. fills the resulting gap with filler tracks whose combined length
     *      is >= the gap with the smallest overshoot; the LAST filler is
     *      clamped at the gap end.  So the air never goes silent and only a
     *      filler is ever cut, never a show track (D2).  Applies even when the
     *      gap is shorter than the shortest filler.
     *
     * Only the SHIFT case is touched (D4: A's own clamp in the ANCHOR case is
     * left as is).  Runs inside the cascade's transaction; on any problem it
     * throws and the whole cascade rolls back to the untouched schedule.
     * With no playlist configured, an empty playlist or nothing sticking out
     * it is a no-op.
     *
     * @param int    $instanceId B's instance id (already shifted)
     * @param string $startsUtc  B's new start (UTC, whole seconds)
     * @param string $endsUtc    B's slot end (UTC) — unchanged by the shift
     *
     * @return int number of filler rows inserted (0 = nothing done)
     */
    private static function fillShiftedTail($instanceId, $startsUtc, $endsUtc)
    {
        $playlistId = Application_Model_Preference::getShowShiftFillerPlaylistId();
        if ($playlistId <= 0) {
            return 0;
        }

        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT id, starts, ends, file_id
               FROM cc_schedule
              WHERE instance_id = :id
              ORDER BY starts ASC, id ASC',
            [':id' => $instanceId],
            Application_Common_Database::ALL
        );
        if (empty($rows)) {
            return 0;
        }

        $endsTs = self::utcToTs($endsUtc);
        $contentEndTs = 0.0;
        foreach ($rows as $r) {
            $contentEndTs = max($contentEndTs, self::utcToTs($r['ends']));
        }
        if ($contentEndTs - $endsTs < self::MIN_OVERRUN_SECONDS) {
            return 0;   // fits after all
        }

        $pool = self::fillerPool($playlistId);
        if (empty($pool)) {
            Logging::warn(
                "ShowShiftService: filler playlist {$playlistId} has no playable "
                . "tracks — instance {$instanceId} keeps the plain clamp"
            );
            return 0;
        }

        // 1. outro protection
        $protected = self::matchOutroSuffix($rows, self::effectiveOutroFileIds($instanceId));
        $tail = $protected > 0 ? array_slice($rows, -$protected) : [];
        $body = array_slice($rows, 0, count($rows) - $protected);
        $tailLen = 0.0;
        if ($protected > 0) {
            $tailLen = self::utcToTs($tail[$protected - 1]['ends'])
                - self::utcToTs($tail[0]['starts']);
        }
        $bodyTargetTs = $endsTs - $tailLen;   // where the body must end

        // 2. rows that no longer fit
        $keep = [];
        $remove = [];
        foreach ($body as $r) {
            if (self::utcToTs($r['ends']) > $bodyTargetTs + 0.5) {
                $remove[] = $r;
            } else {
                $keep[] = $r;
            }
        }
        $gapStartTs = !empty($keep)
            ? self::utcToTs($keep[count($keep) - 1]['ends'])
            : self::utcToTs($startsUtc);
        $gap = $bodyTargetTs - $gapStartTs;

        // 3. pick fillers (sum >= gap, minimal overshoot; the last one is cut)
        $picked = $gap >= 1.0 ? self::pickFillers($pool, $gap) : [];

        // ---- apply ---------------------------------------------------------
        $removedFileIds = [];
        foreach ($remove as $r) {
            Application_Common_Database::prepareAndExecute(
                'DELETE FROM cc_schedule WHERE id = :id',
                [':id' => (int) $r['id']],
                Application_Common_Database::EXECUTE
            );
            if ($r['file_id'] !== null) {
                $removedFileIds[(int) $r['file_id']] = true;
            }
        }

        $inserted = 0;
        $cursor = $gapStartTs;
        $n = count($picked);
        foreach ($picked as $i => $f) {
            $isLast = ($i === $n - 1);
            $len = (float) $f['seconds'];
            if ($isLast || $cursor + $len > $bodyTargetTs) {
                $len = max(1.0, $bodyTargetTs - $cursor);   // clamp at the gap end
            }
            $cueIn = (float) $f['cuein'];
            Application_Common_Database::prepareAndExecute(
                'INSERT INTO cc_schedule
                    (starts, ends, cue_in, cue_out, fade_in, fade_out,
                     clip_length, position, instance_id, file_id, playout_status)
                 VALUES
                    (:starts, :ends, :cue_in, :cue_out, :fade_in, :fade_out,
                     :clip, 0, :inst, :file, 1)',
                [
                    ':starts'   => self::tsToUtc($cursor),
                    ':ends'     => self::tsToUtc($cursor + $len),
                    ':cue_in'   => Application_Common_DateHelper::secondsToPlaylistTime($cueIn),
                    ':cue_out'  => Application_Common_DateHelper::secondsToPlaylistTime($cueIn + $len),
                    ':fade_in'  => (string) $f['fadein'],
                    ':fade_out' => (string) $f['fadeout'],
                    ':clip'     => Application_Common_DateHelper::secondsToPlaylistTime($len),
                    ':inst'     => $instanceId,
                    ':file'     => (int) $f['file_id'],
                ],
                Application_Common_Database::EXECUTE
            );
            $cursor += $len;
            $inserted++;
            unset($removedFileIds[(int) $f['file_id']]);
            if ($cursor >= $bodyTargetTs - 0.5) {
                break;   // gap closed (the DP may over-provision by design)
            }
        }

        // 1b. pin the outro back to the slot end
        if ($protected > 0) {
            $back = self::utcToTs($tail[0]['starts']) - $bodyTargetTs;
            if (abs($back) >= 0.5) {
                foreach ($tail as $r) {
                    Application_Common_Database::prepareAndExecute(
                        'UPDATE cc_schedule SET starts = :s, ends = :e WHERE id = :id',
                        [
                            ':s'  => self::tsToUtc(self::utcToTs($r['starts']) - $back),
                            ':e'  => self::tsToUtc(self::utcToTs($r['ends']) - $back),
                            ':id' => (int) $r['id'],
                        ],
                        Application_Common_Database::EXECUTE
                    );
                }
            }
        }

        // housekeeping: positions, time_filled, is_scheduled
        $ordered = Application_Common_Database::prepareAndExecute(
            'SELECT id FROM cc_schedule WHERE instance_id = :id ORDER BY starts ASC, id ASC',
            [':id' => $instanceId],
            Application_Common_Database::ALL
        );
        foreach ($ordered as $pos => $r) {
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_schedule SET position = :p WHERE id = :id',
                [':p' => $pos, ':id' => (int) $r['id']],
                Application_Common_Database::EXECUTE
            );
        }
        Application_Common_Database::prepareAndExecute(
            "UPDATE cc_show_instances
                SET time_filled = COALESCE(
                    (SELECT SUM(clip_length) FROM cc_schedule WHERE instance_id = :id),
                    '00:00:00'::interval)
              WHERE id = :id",
            [':id' => $instanceId],
            Application_Common_Database::EXECUTE
        );
        $fillerIds = array_map(function ($f) { return (int) $f['file_id']; }, array_slice($picked, 0, $inserted));
        if (!empty($fillerIds)) {
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_files SET is_scheduled = true WHERE id IN (' . implode(',', $fillerIds) . ')',
                [],
                Application_Common_Database::EXECUTE
            );
        }
        if (!empty($removedFileIds)) {
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_files SET is_scheduled = false
                  WHERE id IN (' . implode(',', array_keys($removedFileIds)) . ')
                    AND NOT EXISTS (SELECT 1 FROM cc_schedule s WHERE s.file_id = cc_files.id)',
                [],
                Application_Common_Database::EXECUTE
            );
        }

        Logging::info(sprintf(
            'ShowShiftService: filler for instance %d — removed %d row(s), gap %.1f s, '
            . 'inserted %d filler(s) from playlist %d, outro rows pinned: %d',
            $instanceId, count($remove), $gap, $inserted, $playlistId, $protected
        ));

        return $inserted;
    }

    /**
     * Playable file rows of the filler playlist: file_id, effective length in
     * seconds (cue-aware cliplength), cue-in seconds and the fade strings.
     * Blocks / streams / missing files are skipped.
     */
    private static function fillerPool($playlistId)
    {
        $rows = Application_Common_Database::prepareAndExecute(
            "SELECT c.file_id,
                    EXTRACT(EPOCH FROM c.cliplength) AS seconds,
                    EXTRACT(EPOCH FROM c.cuein)      AS cuein,
                    c.fadein::text  AS fadein,
                    c.fadeout::text AS fadeout
               FROM cc_playlistcontents c
               JOIN cc_files f ON f.id = c.file_id
              WHERE c.playlist_id = :pid
                AND c.type = 0
                AND f.file_exists = true
                AND f.hidden = false
              ORDER BY c.position",
            [':pid' => (int) $playlistId],
            Application_Common_Database::ALL
        );
        $pool = [];
        foreach ($rows as $r) {
            if ((float) $r['seconds'] >= 1.0) {
                $pool[] = $r;
            }
        }
        return $pool;
    }

    /**
     * Effective outro playlist of the instance's show: the show's own
     * "Select Outro Playlist" when overridden, else the global default
     * (Settings → General).  Returns the playlist's file ids in order, or [].
     */
    private static function effectiveOutroFileIds($instanceId)
    {
        $show = Application_Common_Database::prepareAndExecute(
            'SELECT s.override_outro_playlist::int AS ovr, s.outro_playlist_id
               FROM cc_show_instances i JOIN cc_show s ON s.id = i.show_id
              WHERE i.id = :id',
            [':id' => $instanceId],
            Application_Common_Database::SINGLE
        );
        $pid = 0;
        if (!empty($show)) {
            $pid = ((int) $show['ovr'] === 1)
                ? (int) $show['outro_playlist_id']
                : (int) Application_Model_Preference::GetOutroPlaylist();
        }
        if ($pid <= 0) {
            return [];
        }
        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT file_id FROM cc_playlistcontents
              WHERE playlist_id = :pid AND type = 0 ORDER BY position',
            [':pid' => $pid],
            Application_Common_Database::ALL
        );
        return array_map(function ($r) { return (int) $r['file_id']; }, $rows);
    }

    /**
     * Number of trailing schedule rows that ARE the outro (file ids match the
     * outro playlist as a suffix, in order).  0 when they don't — then nothing
     * is protected and the literal last track goes (D1).
     */
    public static function matchOutroSuffix(array $rows, array $outroFileIds)
    {
        $k = count($outroFileIds);
        if ($k === 0 || $k > count($rows)) {
            return 0;
        }
        $tail = array_slice($rows, -$k);
        foreach ($tail as $i => $r) {
            if ((int) $r['file_id'] !== $outroFileIds[$i]) {
                return 0;
            }
        }
        return $k;
    }

    /**
     * Choose filler tracks whose total length is >= $gap with the smallest
     * overshoot (ties: fewer tracks); the caller clamps the last one.  Pure
     * function — 0/1 knapsack over whole seconds on a shuffled pool (the
     * shuffle is the only source of variety for now).  When the whole pool is
     * shorter than the gap, every track is used once and the longest ones are
     * repeated until the gap is covered.
     *
     * @param array $pool items with 'seconds' (float) — extra keys pass through
     * @param float $gap  seconds to cover
     *
     * @return array chosen items in play order
     */
    public static function pickFillers(array $pool, $gap)
    {
        $need = (int) ceil($gap);
        if ($need <= 0 || empty($pool)) {
            return [];
        }
        $items = array_values($pool);
        shuffle($items);
        $lens = array_map(function ($f) { return max(1, (int) round((float) $f['seconds'])); }, $items);
        $total = array_sum($lens);

        if ($total < $need) {
            // shortfall: everything once, then repeat the longest
            $out = $items;
            $sum = $total;
            usort($items, function ($a, $b) { return (float) $b['seconds'] <=> (float) $a['seconds']; });
            while ($sum < $need) {
                $out[] = $items[0];
                $sum += max(1, (int) round((float) $items[0]['seconds']));
            }
            return $out;
        }

        // dp[s] = [count, lastIndex, prevSum] for exactly-reachable sums s
        $maxSum = $need + max($lens);
        $dp = [0 => [0, -1, -1]];
        foreach ($lens as $idx => $len) {
            $next = $dp;
            foreach ($dp as $s => $info) {
                $ns = $s + $len;
                if ($ns > $maxSum) {
                    continue;
                }
                $cnt = $info[0] + 1;
                if (!isset($next[$ns]) || $next[$ns][0] > $cnt) {
                    $next[$ns] = [$cnt, $idx, $s];
                }
            }
            $dp = $next;
        }
        $best = null;
        foreach ($dp as $s => $info) {
            if ($s < $need) {
                continue;
            }
            if ($best === null || $s < $best || ($s === $best && $info[0] < $dp[$best][0])) {
                $best = $s;
            }
        }
        $chosen = [];
        for ($s = $best; $s > 0; $s = $dp[$s][2]) {
            $chosen[] = $items[$dp[$s][1]];
        }
        return array_reverse($chosen);
    }

    private static function utcToTs($utc)
    {
        // cc_schedule keeps microseconds; strtotime drops them, so parse by hand.
        $sec = strtotime(substr($utc, 0, 19) . ' UTC');
        $frac = (strlen($utc) > 20) ? (float) ('0' . substr($utc, 19)) : 0.0;
        return $sec + $frac;
    }

    private static function tsToUtc($ts)
    {
        $whole = (int) floor($ts);
        $micro = (int) round(($ts - $whole) * 1000000);
        if ($micro >= 1000000) {
            $whole++;
            $micro -= 1000000;
        }
        return gmdate('Y-m-d H:i:s', $whole) . sprintf('.%06d', $micro);
    }

    private static function clearInstance($instanceId)
    {
        $fileRows = Application_Common_Database::prepareAndExecute(
            'SELECT DISTINCT file_id FROM cc_schedule
              WHERE instance_id = :id AND file_id IS NOT NULL',
            [':id' => $instanceId],
            Application_Common_Database::ALL
        );

        $deleted = (int) Application_Common_Database::prepareAndExecute(
            'DELETE FROM cc_schedule WHERE instance_id = :id',
            [':id' => $instanceId],
            Application_Common_Database::ROW_COUNT
        );

        if ($deleted > 0) {
            // Empty-slot marker: zero the fill; modified_instance = true is
            // upstream's "deleted occurrence" (the slot never airs — A plays
            // through it), delayed_start_from records why (see class doc).
            Application_Common_Database::prepareAndExecute(
                "UPDATE cc_show_instances
                    SET time_filled = '00:00:00',
                        modified_instance = true,
                        delayed_start_from = starts
                  WHERE id = :id",
                [':id' => $instanceId],
                Application_Common_Database::EXECUTE
            );

            // Drop is_scheduled for tracks that are no longer scheduled anywhere.
            $ids = [];
            foreach ($fileRows as $r) {
                $ids[(int) $r['file_id']] = true;
            }
            if (!empty($ids)) {
                $idList = implode(',', array_keys($ids));
                Application_Common_Database::prepareAndExecute(
                    "UPDATE cc_files SET is_scheduled = false
                      WHERE id IN ({$idList})
                        AND NOT EXISTS (
                            SELECT 1 FROM cc_schedule s WHERE s.file_id = cc_files.id)",
                    [],
                    Application_Common_Database::EXECUTE
                );
            }
        }

        return $deleted;
    }
}
