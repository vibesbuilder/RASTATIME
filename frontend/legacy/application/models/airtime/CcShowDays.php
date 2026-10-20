<?php

/**
 * Skeleton subclass for representing a row from the 'cc_show_days' table.
 *
 * You should add additional methods to this class to meet the
 * application requirements.  This class will only be generated as
 * long as it does not already exist in the output directory.
 */
class CcShowDays extends BaseCcShowDays
{
    /**
     * RASTATIME 2026-05-17 — locale-safe override of the auto-generated
     * getDbStartTime().
     *
     * The Propel-generated BaseCcShowDays::getDbStartTime() uses the
     * default format `'%X'`, which is `strftime`'s "preferred time
     * representation" and **locale-dependent**: on a 12-hour locale
     * (en_US default) it returns strings like `"12:00:00 AM"` instead
     * of `"00:00:00"`.  That string then propagates through callers
     * like:
     *
     *   $origStartTime = explode(':', $row->getDbStartTime());
     *   $localShowStartHour = $origStartTime[0];   // "12" instead of "00"
     *
     * which made `Application_Service_ShowService::getInstance()` look
     * up an instance at 12:00 local time (10:00 UTC) instead of 00:00
     * local time (22:00 UTC the previous day), silently failed to find
     * it, threw "Could not find show instance with start time: ...",
     * rolled back the entire edit-show transaction (including the show
     * rename), and returned to the caller as if nothing had happened.
     *
     * Forcing the default to the unambiguous 24-hour `H:i:s` format
     * here fixes all 29+ call sites in one place WITHOUT having to
     * touch the auto-generated `BaseCcShowDays` (which a future
     * `propel-gen` would overwrite).  Callers that explicitly pass a
     * format string (or null) are unaffected — we only change the
     * default.
     */
    public function getDbStartTime($format = 'H:i:s')
    {
        return parent::getDbStartTime($format);
    }

    public function isRepeating()
    {
        return $this->getDbRepeatType() != -1;
    }

    public function getUTCStartDateAndTime()
    {
        $dt = new DateTime(
            "{$this->getDbFirstShow()} {$this->getDbStartTime()}",
            new DateTimeZone($this->getDbTimezone())
        );
        $dt->setTimezone(new DateTimeZone('UTC'));

        return $dt;
    }

    // Returns the start of a show in the timezone it was created in
    public function getLocalStartDateAndTime()
    {
        return new DateTime(
            "{$this->getDbFirstShow()} {$this->getDbStartTime()}",
            new DateTimeZone($this->getDbTimezone())
        );

        // set timezone to that of the show
        // $dt->setTimezone(new DateTimeZone($this->getDbTimezone()));
    }

    /**
     * Returns the end of a show in the timezone it was created in.
     */
    public function getLocalEndDateAndTime()
    {
        // RASTATIME 2026-10-20 - wall-clock end (ShowService::wallClockEnd,
        // the same rule the instances are built with): the edit form of a
        // show whose first day crosses the autumn change showed "00:00 -
        // 04:00" for a 05:00 duration because the interval was added as
        // elapsed time.
        return Application_Service_ShowService::wallClockEnd(
            $this->getLocalStartDateAndTime(),
            $this->getDbDuration()
        );
    }

    public function isShowStartInPast()
    {
        return $this->getUTCStartDateAndTime()->format('Y-m-d H:i:s') < gmdate('Y-m-d H:i:s');
    }

    public function formatDuration()
    {
        $info = explode(':', $this->getDbDuration());

        return str_pad(intval($info[0]), 2, '0', STR_PAD_LEFT) . 'h ' . str_pad(intval($info[1]), 2, '0', STR_PAD_LEFT) . 'm';
    }
} // CcShowDays
