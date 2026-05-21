<?php

class RabbitMqPlugin extends Zend_Controller_Plugin_Abstract
{
    public function dispatchLoopShutdown()
    {
        if (Application_Model_RabbitMq::$doPush) {
            // The side effects of this function are still required to fill the schedule, we
            // don't use the returned schedule.
            Application_Model_Schedule::getSchedule();

            // RASTATIME: the legacy SendMessageToPypo() was a RabbitMQ
            // notify aimed at Liquidsoap-era Pypo.  We don't run Pypo
            // anymore.  Instead, we ping the playout's own HTTP listener
            // so PlayoutScheduler.refresh() picks up the schedule change
            // immediately — without it, the operator would have to wait
            // up to ~120 s before a freshly created / edited show goes
            // on-air.
            Application_Model_RabbitMq::NotifyPlayoutScheduleChanged();
        }

        if (memory_get_peak_usage() > 30 * 2 ** 20) {
            Logging::debug('Peak memory usage: '
                . (memory_get_peak_usage() / 1000000)
                . ' MB while accessing URI ' . $_SERVER['REQUEST_URI']);
            Logging::debug('Should try to keep memory footprint under 25 MB');
        }
    }
}
