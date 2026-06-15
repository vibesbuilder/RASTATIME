<?php

/**
 * Class Application_Service_ShowShiftService.
 *
 * RASTATIME 2026-06-15 — Show-Shift / "Allow delayed start", Phase 3a.
 *
 * Lets a show start LATER than its calendar slot when the preceding show
 * overran, instead of having the preceding show's tail clamped away.
 *
 * Mechanism (per following show B that opted in via cc_show.allow_delayed_start):
 *
 *   A = the instance immediately before B.
 *   contentEnd(A) = MAX(cc_schedule.ends) of A's scheduled items.
 *   If A's content runs past B's start (contentEnd > B.starts) AND B keeps
 *   positive remaining airtime (contentEnd < B.ends):
 *     1. Extend A.ends to contentEnd.  This makes A's last item "inside"
 *        its instance, so the backend playout serializer no longer clamps
 *        it at the old slot end — A airs in full.  No playout-path change.
 *     2. Move B.starts to contentEnd, keep B.ends FIXED, and shift B's
 *        cc_schedule items by the same delta.  B's last track is then
 *        clamped at B.ends by the existing overbook logic (the accepted
 *        cut-off).  B is stamped modified_instance = true so a repeated
 *        show only changes the one affected episode.
 *
 * Forward-only by operator decision (2026-06-15): a shift is never walked
 * back automatically, so no "original slot" needs to be stored.  The engine
 * is still safe to run repeatedly: the delta is computed in whole seconds
 * (strtotime), so once B sits at A's content end the next pass computes a
 * sub-second delta that floors to 0 and is skipped — idempotent and
 * drift-free without "+= delta" accumulation.
 *
 * Phase 3a is a SINGLE shift per following show.  When several opted-in
 * shows are back-to-back inside the lead window the ascending-by-start
 * iteration already cascades them (B's predecessor X was itself shifted, so
 * X's content end has moved).  The EXPLICIT cascade guarantee beyond the
 * lead window and the clearing of completely-overrun shows
 * (contentEnd >= B.ends) are Phase 3b.
 *
 * cc_show.allow_delayed_start has no Propel accessor (raw-SQL migration
 * 0056), so it is read via raw SQL here, matching the rest of the feature.
 */
class Application_Service_ShowShiftService
{
    /**
     * @var int how far ahead, in seconds, a following show may start before
     *          the engine will shift it.  Keeps far-future shows (which may
     *          still be edited) untouched.  Env-overridable.
     */
    public const DEFAULT_LEAD_SECONDS = 900;  // 15 minutes

    /**
     * @var int an overrun shorter than this (seconds) is ignored.  Also the
     *          idempotency floor: after a shift, B sits at A's content end so
     *          the residual sub-second difference floors below this and the
     *          show is left alone.
     */
    public const MIN_OVERRUN_SECONDS = 1;

    /**
     * Shift every opted-in show that a preceding overrun pushes into.
     *
     * Read-only candidate scan first (no transaction); each shift then runs
     * in its own transaction so one failure cannot roll back the others.
     *
     * @return int the number of shows shifted (0 if nothing to do)
     */
    public static function applyDelayedStarts()
    {
        $leadSeconds = (int) (getenv('RASTATIME_SHOW_SHIFT_LEAD_SECONDS')
            ?: self::DEFAULT_LEAD_SECONDS);

        $nowUtc = gmdate('Y-m-d H:i:s');
        $horizonUtc = gmdate('Y-m-d H:i:s', time() + $leadSeconds);

        // Candidate following shows B: opted in, starting in the future but
        // within the lead window, not yet begun.  Ascending by start so a
        // back-to-back chain shifts front to back in one pass.
        $candidates = Application_Common_Database::prepareAndExecute(
            "SELECT i.id, i.starts, i.ends
               FROM cc_show_instances i
               JOIN cc_show s ON s.id = i.show_id
              WHERE s.allow_delayed_start = true
                AND i.starts > :now
                AND i.starts <= :horizon
              ORDER BY i.starts ASC",
            [':now' => $nowUtc, ':horizon' => $horizonUtc],
            Application_Common_Database::ALL
        );

        $shifted = 0;
        foreach ($candidates as $b) {
            if (self::shiftIfPredecessorOverruns($b)) {
                ++$shifted;
            }
        }

        if ($shifted > 0) {
            // Tell pypo/Liquidsoap the schedule changed (same as a calendar move).
            Application_Model_RabbitMq::PushSchedule();
        }

        return $shifted;
    }

    /**
     * Shift one following show B if its immediate predecessor overruns into it.
     *
     * @param array $b cc_show_instances row for B (id, starts, ends as UTC strings)
     *
     * @return bool true if B was shifted
     */
    private static function shiftIfPredecessorOverruns($b)
    {
        $con = Propel::getConnection();
        $con->beginTransaction();

        try {
            $bId = (int) $b['id'];
            $bStarts = $b['starts'];
            $bEnds = $b['ends'];

            // A = the instance immediately before B (greatest start before B's).
            $a = Application_Common_Database::prepareAndExecute(
                'SELECT id, ends FROM cc_show_instances
                  WHERE starts < :bstarts
                  ORDER BY starts DESC LIMIT 1',
                [':bstarts' => $bStarts],
                Application_Common_Database::SINGLE
            );
            if (empty($a)) {
                $con->commit();

                return false;
            }
            $aId = (int) $a['id'];

            // contentEnd(A) = end of A's last scheduled item.
            $contentEnd = Application_Common_Database::prepareAndExecute(
                'SELECT ends FROM cc_schedule
                  WHERE instance_id = :aid
                  ORDER BY ends DESC LIMIT 1',
                [':aid' => $aId],
                Application_Common_Database::COLUMN
            );
            if ($contentEnd === false || $contentEnd === null) {
                // A has no scheduled content → nothing can overrun.
                $con->commit();

                return false;
            }

            $diffSeconds = strtotime($contentEnd . ' UTC') - strtotime($bStarts . ' UTC');

            // No meaningful overrun into B (also the idempotency floor: a
            // already-shifted B sits at A's content end, leaving a sub-second
            // residue that floors below MIN_OVERRUN_SECONDS).
            if ($diffSeconds < self::MIN_OVERRUN_SECONDS) {
                $con->commit();

                return false;
            }

            // B completely overrun (no positive airtime left) → Phase 3a leaves
            // it on its slot (current clamp behaviour); Phase 3b clears it.
            if (strtotime($contentEnd . ' UTC') >= strtotime($bEnds . ' UTC')) {
                $con->commit();

                return false;
            }

            // 1. Extend A.ends to its content end so A's last item is "inside"
            //    its instance and the playout serializer stops clamping it.
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_show_instances SET ends = :ce WHERE id = :aid',
                [':ce' => $contentEnd, ':aid' => $aId],
                Application_Common_Database::EXECUTE
            );

            // 2. Move B.starts forward by the whole-second delta (kept in sync
            //    with the items it shifts), keep B.ends fixed, mark the episode.
            $newBStarts = gmdate('Y-m-d H:i:s', strtotime($bStarts . ' UTC') + $diffSeconds);
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_show_instances
                    SET starts = :ns, modified_instance = true
                  WHERE id = :bid',
                [':ns' => $newBStarts, ':bid' => $bId],
                Application_Common_Database::EXECUTE
            );

            // 3. Shift B's scheduled items by the same delta.  Uses the same
            //    Propel connection, so it joins this transaction.
            Application_Service_SchedulerService::updateScheduleStartTime(
                [$bId],
                $diffSeconds
            );

            $con->commit();

            Logging::info(
                "ShowShiftService: shifted instance {$bId} by {$diffSeconds}s "
                . "(predecessor {$aId} runs to {$contentEnd})"
            );

            return true;
        } catch (Throwable $e) {
            $con->rollback();
            Logging::error(
                'ShowShiftService failed for instance ' . ($b['id'] ?? '?')
                . ': ' . $e->getMessage()
            );

            return false;
        }
    }
}
