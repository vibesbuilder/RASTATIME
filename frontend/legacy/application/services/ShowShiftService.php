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
 *     moved to A's content end (its END stays fixed, its items move with it,
 *     its last track is clamped at the slot end = the accepted cut-off) and
 *     the cascade ends — that show absorbs the rest, its successor starts on
 *     time.  A repeated show changes only the affected episode
 *     (modified_instance = true).
 *
 * Finally A.ends is extended to where its content settled, so A's last item is
 * "inside" its instance and the backend playout serializer stops clamping it —
 * A airs in full with no playout-path change.  A is extended ONLY when the
 * cascade actually cleared or shifted a flagged show, so a plain overrun into
 * a gap or a non-flagged anchor keeps the current clamp behaviour.
 *
 * Forward-only per operator decision (2026-06-15): a shift is never walked back
 * automatically, so no "original slot" column / migration is needed.  Trigger
 * shows are filtered modified_instance = false, which (a) keeps the engine
 * idempotent — an already-shifted show sits at modified_instance = true and is
 * not re-triggered as a new overrun origin — and (b) leaves operator-moved
 * instances alone as cascade origins (they are still shifted/cleared when an
 * earlier show overruns INTO them).  Deltas are whole seconds (strtotime), so a
 * re-evaluated chain computes sub-second deltas that floor to no-ops.
 *
 * cc_show.allow_delayed_start has no Propel accessor (raw-SQL migration 0056),
 * so it is read via raw SQL here, matching the rest of the feature.
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
              WHERE a.modified_instance = false
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
                        SET starts = :ns, modified_instance = true
                      WHERE id = :id',
                    [':ns' => $newStarts, ':id' => (int) $next['id']],
                    Application_Common_Database::EXECUTE
                );
                Application_Service_SchedulerService::updateScheduleStartTime(
                    [(int) $next['id']],
                    $diff
                );
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
            // Empty-slot marker: zero the fill, mark the episode as modified so
            // the repeat regenerator leaves the skipped slot alone.
            Application_Common_Database::prepareAndExecute(
                "UPDATE cc_show_instances
                    SET time_filled = '00:00:00', modified_instance = true
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
