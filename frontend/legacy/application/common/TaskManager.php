<?php

/**
 * Class TaskManager.
 *
 * Background class for 'asynchronous' task management for Airtime stations
 */
final class TaskManager
{
    /**
     * @var array tasks to be run. Maps task names to a boolean value denoting
     *            whether the task has been checked/run
     */
    private $_taskList;

    /**
     * @var TaskManager singleton instance object
     */
    private static $_instance;

    /**
     * @var int TASK_INTERVAL_SECONDS how often, in seconds, to run the TaskManager tasks
     */
    public const TASK_INTERVAL_SECONDS = 30;

    /**
     * @var PDO Propel connection object
     */
    private $_con;

    /**
     * Private constructor so class is uninstantiable.
     */
    private function __construct()
    {
        foreach (TaskFactory::getTasks() as $k => $task) {
            $this->_taskList[$task] = false;
        }
    }

    /**
     * Get the singleton instance of this class.
     *
     * @return TaskManager the TaskManager instance
     */
    public static function getInstance()
    {
        if (!self::$_instance) {
            self::$_instance = new TaskManager();
        }

        return self::$_instance;
    }

    /**
     * Run a single task.
     *
     * @param string $taskName the ENUM name of the task to be run
     */
    public function runTask($taskName)
    {
        $task = TaskFactory::getTask($taskName);
        if ($task && $task->shouldBeRun()) {
            Logging::debug("running task {$taskName}");
            $task->run();
        }
        // Mark that the task has been checked/run.
        // This is important for prioritized tasks that
        // we need to run on every request (such as the
        // schema check/upgrade)
        $this->_taskList[$taskName] = true;
    }

    /**
     * Run all tasks that need to be run.
     *
     * To prevent blocking and making too many requests to the database,
     * we implement a row-level, non-blocking, read-protected lock on a
     * timestamp that we check each time the application is bootstrapped,
     * which, assuming enough time has passed, is updated before running
     * the tasks.
     */
    public function runTasks()
    {
        // If there is data in auth storage, this could be a user request
        // so we should just return to avoid blocking
        if ($this->_isUserSessionRequest()) {
            return;
        }
        $this->_con = Propel::getConnection(CcPrefPeer::DATABASE_NAME);
        $this->_con->beginTransaction();

        try {
            $lock = $this->_getLock();
            if ($lock && (microtime(true) < ($lock['valstr'] + self::TASK_INTERVAL_SECONDS))) {
                // Propel caches the database connection and uses it persistently, so if we don't
                // use commit() here, we end up blocking other queries made within this request
                $this->_con->commit();

                return;
            }
            $this->_updateLock($lock);
            $this->_con->commit();
        } catch (PDOException $e) {
            // We get here if there are simultaneous requests trying to fetch the lock row
            $this->_con->rollBack();

            // Do not log 'could not obtain lock' exception
            // SQLSTATE[55P03]: Lock not available: 7 ERROR:  could not obtain lock on row in relation "cc_pref"
            if ($e->getCode() != '55P03') {
                Logging::warn($e->getMessage());
            }

            return;
        }
        foreach ($this->_taskList as $task => $hasTaskRun) {
            if (!$hasTaskRun) {
                $this->runTask($task);
            }
        }
    }

    /**
     * Check if the current session is a user request.
     *
     * @return bool true if there is a Zend_Auth object in the current session,
     *              otherwise false
     */
    private function _isUserSessionRequest()
    {
        if (!Zend_Session::isStarted()) {
            return false;
        }
        $auth = Zend_Auth::getInstance();
        $data = $auth->getStorage()->read();

        return !empty($data);
    }

    /**
     * Get the task_manager_lock from cc_pref with a row-level lock for atomicity.
     *
     * The lock is exclusive (prevent reads) and will only last for the duration
     * of the transaction. We add NOWAIT so reads on the row during the transaction
     * won't block
     *
     * @return array|bool an array containing the row values, or false on failure
     */
    private function _getLock()
    {
        $sql = "SELECT * FROM cc_pref WHERE keystr='task_manager_lock' LIMIT 1 FOR UPDATE NOWAIT";
        $st = $this->_con->prepare($sql);
        $st->execute();

        return $st->fetch();
    }

    /**
     * Update and commit the new lock value, or insert it if it doesn't exist.
     *
     * @param $lock array cc_pref lock row values
     */
    private function _updateLock($lock)
    {
        $sql = empty($lock) ? "INSERT INTO cc_pref (keystr, valstr) VALUES ('task_manager_lock', :value)"
            : "UPDATE cc_pref SET valstr=:value WHERE keystr='task_manager_lock'";
        $st = $this->_con->prepare($sql);
        $st->execute([':value' => microtime(true)]);
    }
}

/**
 * Interface AirtimeTask Interface for task operations.
 */
interface AirtimeTask
{
    /**
     * Check whether the task should be run.
     *
     * @return bool true if the task needs to be run, otherwise false
     */
    public function shouldBeRun();

    /**
     * Run the task.
     */
    public function run();
}

/**
 * Class CeleryTask.
 *
 * Checks the Celery broker task queue and runs callbacks for completed tasks
 */
class CeleryTask implements AirtimeTask
{
    /**
     * Check the ThirdPartyTrackReferences table to see if there are any pending tasks.
     *
     * @return bool true if there are pending tasks in ThirdPartyTrackReferences
     */
    public function shouldBeRun()
    {
        return !CeleryManager::isBrokerTaskQueueEmpty();
    }

    /**
     * Poll the task queue for any completed Celery tasks.
     */
    public function run()
    {
        CeleryManager::pollBrokerTaskQueue();
    }
}

/**
 * Class AutoPlaylistTask.
 *
 * Checks for shows with an autoplaylist that needs to be filled in
 */
class AutoPlaylistTask implements AirtimeTask
{
    /**
     * Checks whether or not the autoplaylist polling interval has passed.
     *
     * @return bool true if the autoplaylist polling interval has passed
     */
    public function shouldBeRun()
    {
        return AutoPlaylistManager::hasAutoPlaylistPollIntervalPassed();
    }

    /**
     *  Schedule the autoplaylist for the shows.
     */
    public function run()
    {
        AutoPlaylistManager::buildAutoPlaylist();
    }
}

/**
 * Class PodcastTask.
 *
 * Checks podcasts marked for automatic ingest and downloads any new episodes
 * since the task was last run
 */
class PodcastTask implements AirtimeTask
{
    /**
     * Check whether or not the podcast polling interval has passed.
     *
     * @return bool true if the podcast polling interval has passed
     */
    public function shouldBeRun()
    {
        $overQuota = Application_Model_Systemstatus::isDiskOverQuota();

        return !$overQuota && PodcastManager::hasPodcastPollIntervalPassed();
    }

    /**
     * Download the latest episode for all podcasts flagged for automatic ingest.
     */
    public function run()
    {
        PodcastManager::downloadNewestEpisodes();
    }
}

/**
 * Class ImportTask.
 */
class ImportCleanupTask implements AirtimeTask
{
    /**
     * Check if there are any files that have been stuck
     * in Pending status for over an hour.
     *
     * @return bool true if there are any files stuck pending,
     *              otherwise false
     */
    public function shouldBeRun()
    {
        return Application_Service_MediaService::areFilesStuckInPending();
    }

    /**
     * Clean up stuck imports by changing their import status to Failed.
     */
    public function run()
    {
        Application_Service_MediaService::clearStuckPendingImports();
    }
}

/**
 * Class StationPodcastTask.
 *
 * Checks the Station podcast rollover timer and resets allotted
 * downloads if enough time has passed (default: 1 month)
 */
class StationPodcastTask implements AirtimeTask
{
    public const STATION_PODCAST_RESET_TIMER_SECONDS = 2.628e+6;  // 1 month

    /**
     * Check whether or not the download counter for the station podcast should be reset.
     *
     * @return bool true if enough time has passed
     */
    public function shouldBeRun()
    {
        $lastReset = Application_Model_Preference::getStationPodcastDownloadResetTimer();

        return empty($lastReset) || (microtime(true) > ($lastReset + self::STATION_PODCAST_RESET_TIMER_SECONDS));
    }

    /**
     * Reset the station podcast download counter.
     */
    public function run()
    {
        Application_Model_Preference::resetStationPodcastDownloadCounter();
        Application_Model_Preference::setStationPodcastDownloadResetTimer(microtime(true));
    }
}

/**
 * Class TrackExpiryTask.
 *
 * RASTATIME 2026-05-16 - Shared pruner for the Track-Expiry and
 * Podcast-Auto-Expiry features.  Once per hour, walks cc_files for
 * rows where expires_at < NOW() and disabled = false, and flips
 * disabled = true.  Disabled tracks remain visible in the Library
 * and in already-built Smartblocks (so already-scheduled shows keep
 * playing them); they are excluded from NEW Smartblock evaluations
 * via a "disabled = false" filter on the criteria query.
 *
 * The "last run" timestamp is stored in cc_pref.track_expiry_last_run
 * via the Preference accessors below.
 */
class TrackExpiryTask implements AirtimeTask
{
    public const TRACK_EXPIRY_INTERVAL_SECONDS = 3600;  // 1 hour

    public function shouldBeRun()
    {
        $lastRun = Application_Model_Preference::getTrackExpiryLastRun();
        return empty($lastRun)
            || (microtime(true) > $lastRun + self::TRACK_EXPIRY_INTERVAL_SECONDS);
    }

    public function run()
    {
        try {
            $con = Propel::getConnection();
            // Atomic SQL: disable every still-enabled file whose
            // expires_at has passed.  Returns the count for logging.
            $stmt = $con->prepare(
                'UPDATE cc_files
                 SET disabled = true
                 WHERE expires_at IS NOT NULL
                   AND expires_at < NOW()
                   AND disabled = false'
            );
            $stmt->execute();
            $rows = $stmt->rowCount();
            if ($rows > 0) {
                Logging::info("TrackExpiryTask: disabled {$rows} expired files");
            }
        } catch (Exception $exc) {
            Logging::error('TrackExpiryTask failed: ' . $exc->getMessage());
        }
        Application_Model_Preference::setTrackExpiryLastRun(microtime(true));
    }
}

/**
 * Class LocalImportScanTask.
 *
 * RASTATIME 2026-05-16 - Drop-folder importer.  Every 5 minutes (and
 * on-demand via Settings -> Local Machine -> "Scan Now") walks the
 * operator-configured Local Import Folder, hands each audio file to
 * the standard import pipeline (CcFiles::createAndImport -> organize
 * -> analyzer -> cc_files), and deletes the source after the attempt
 * - successful OR failed.  Spec call-out: a permanently-broken file
 * must NOT pile up forever in the drop-folder; it gets deleted on the
 * first attempt so the next scan does not re-try it.
 *
 * Single configured folder, not a list.  Non-audio files are left
 * untouched (operator may have placed them there accidentally; we
 * only own audio files).
 *
 * See ARCHITECTURE Section 23.12 for the design notes (single folder,
 * Option A "copy/move to storage", drop-folder delete-after-attempt,
 * future Option C as a possible extension).
 */
class LocalImportScanTask implements AirtimeTask
{
    public const LOCAL_IMPORT_INTERVAL_SECONDS = 300;  // 5 minutes
    public const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'oga', 'aac', 'opus'];

    public function shouldBeRun()
    {
        $folder = Application_Model_Preference::getLocalImportFolder();
        if (empty($folder)) {
            return false;  // disabled
        }
        $lastRun = Application_Model_Preference::getLocalImportLastRun();
        return empty($lastRun)
            || (microtime(true) > $lastRun + self::LOCAL_IMPORT_INTERVAL_SECONDS);
    }

    public function run()
    {
        $folder = Application_Model_Preference::getLocalImportFolder();
        if (empty($folder)) {
            return;
        }
        self::scanOnce($folder);
    }

    /**
     * Walk the given folder once, import every audio file, delete the
     * source after each attempt (success or failure), and persist the
     * last-run timestamp + a short human-readable status string.
     *
     * Static so the "Scan Now" UI button (PreferenceController action)
     * can reuse the exact same path - one source of truth for the
     * importer logic.
     *
     * @param  string $folder absolute path on the RASTATIME host
     * @return array  ['imported' => int, 'failed' => int, 'skipped' => int]
     */
    public static function scanOnce($folder)
    {
        $imported = 0;
        $failed = 0;
        $skipped = 0;

        Application_Model_Preference::setLocalImportLastRun(time());

        if (!is_dir($folder)) {
            $msg = 'Folder missing or unreadable: ' . $folder;
            Logging::warn('LocalImportScanTask: ' . $msg);
            Application_Model_Preference::setLocalImportLastStatus($msg);
            return compact('imported', 'failed', 'skipped');
        }

        $entries = @scandir($folder);
        if ($entries === false) {
            $msg = 'scandir failed for: ' . $folder;
            Logging::warn('LocalImportScanTask: ' . $msg);
            Application_Model_Preference::setLocalImportLastStatus($msg);
            return compact('imported', 'failed', 'skipped');
        }

        foreach ($entries as $name) {
            if ($name === '.' || $name === '..') {
                continue;
            }
            $fullPath = $folder . DIRECTORY_SEPARATOR . $name;
            if (!is_file($fullPath)) {
                continue;  // ignore subdirs
            }
            $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
            if (!in_array($ext, self::AUDIO_EXTENSIONS, true)) {
                // Non-audio: leave it (operator may have placed
                // intentionally; we don't own arbitrary files).
                $skipped++;
                continue;
            }

            // Hand the file to the standard upload pipeline.  This
            // (a) creates a CcFiles row with import_status=PENDING,
            // (b) moves the file to <storage>/organize/, and
            // (c) signals the analyzer via RabbitMQ.
            //
            // We use the dedicated createFromImportFolder() wrapper
            // (NOT createFromLocalFile, which has an upstream
            // double-extension bug, and NOT createAndImport directly
            // because that one is private to CcFiles).
            //
            // Because moveFileToStor() uses rename() under the hood,
            // the source is removed by the move itself - we do NOT
            // need an explicit unlink() after a successful import.
            //
            // For failures (bad extension, permission denied,
            // analyzer signal failure), we DO delete the source
            // explicitly so the broken file does not pile up.
            try {
                CcFiles::createFromImportFolder($fullPath, $name, false);
                $imported++;
                Logging::info('LocalImportScanTask: imported ' . $name);
            } catch (Exception $exc) {
                $failed++;
                Logging::warn(
                    'LocalImportScanTask: import failed for ' . $name
                    . ': ' . $exc->getMessage() . ' (deleting source)'
                );
                @unlink($fullPath);
            }
        }

        $status = sprintf(
            'imported %d, failed %d, skipped %d',
            $imported, $failed, $skipped
        );
        Application_Model_Preference::setLocalImportLastStatus($status);
        if ($imported > 0 || $failed > 0) {
            Logging::info('LocalImportScanTask: ' . $status);
        }

        return compact('imported', 'failed', 'skipped');
    }
}

/**
 * Class RequestablePoolSyncTask.
 *
 * RASTATIME 2026-06-07 - Song Requests.  Keeps cc_files.requestable in
 * sync with the operator-chosen "Requestable Pool" smart block: every
 * REQUESTABLE_POOL_SYNC_INTERVAL_SECONDS it expands the pool block's
 * criteria into the set of matching file ids and flips
 * cc_files.requestable = true for exactly those rows (false for the
 * rest).  The public catalogue-search endpoint only returns requestable
 * tracks, so this is what bounds what listeners may request.
 *
 * No pool configured (preference empty / 0, or the block was deleted):
 * the task clears every requestable flag, so removing the pool disables
 * requesting cleanly.
 *
 * Pattern mirrors TrackExpiryTask: an interval gate via a cc_pref
 * timestamp + an atomic raw-SQL update.
 */
class RequestablePoolSyncTask implements AirtimeTask
{
    public const REQUESTABLE_POOL_SYNC_INTERVAL_SECONDS = 300;  // 5 minutes

    public function shouldBeRun()
    {
        $lastRun = Application_Model_Preference::getRequestablePoolLastSync();

        return empty($lastRun)
            || (microtime(true) > $lastRun + self::REQUESTABLE_POOL_SYNC_INTERVAL_SECONDS);
    }

    public function run()
    {
        try {
            $poolIds = Application_Model_Preference::getRequestablePoolBlockIds();

            // Resolve the criteria of EACH selected pool block into the
            // UNION of matching file ids.  getListofFilesMeetCriteria()
            // returns the FULL criteria-matched set (the item/time limit
            // is only applied later in getListOfFilesUnderLimit), and
            // already excludes disabled = true rows, so expired tracks
            // never become requestable.  The findPk guard means a
            // stale/deleted pool id is skipped instead of accidentally
            // matching every track via an empty-criteria block.
            $ids = [];
            foreach ($poolIds as $poolId) {
                if ($poolId > 0 && CcBlockQuery::create()->findPk($poolId) !== null) {
                    $block = new Application_Model_Block($poolId);
                    // ignoreRequestFilter=true: the pool is the CATALOGUE of
                    // what may be requested, not what is already requested,
                    // so a stray "use requests" criterion on a pool block
                    // must not empty the pool.
                    $result = $block->getListofFilesMeetCriteria(null, true);
                    if (is_array($result) && isset($result['files'])) {
                        foreach ($result['files'] as $file) {
                            $ids[] = (int) $file->getDbId();
                        }
                    }
                }
            }
            $ids = array_values(array_unique($ids));

            $con = Propel::getConnection();
            $con->beginTransaction();

            try {
                // Both updates inside one transaction so the search
                // endpoint never observes an all-false intermediate
                // state.  The IN-list is built from explicitly int-cast
                // ids (no injection vector) — same approach as
                // AutoPlaylistManager's is_scheduled reset.
                if (empty($ids)) {
                    $con->exec('UPDATE cc_files SET requestable = false WHERE requestable = true');
                } else {
                    $idsCsv = implode(',', $ids);
                    $con->exec(
                        'UPDATE cc_files SET requestable = false '
                        . "WHERE requestable = true AND id NOT IN ({$idsCsv})"
                    );
                    $con->exec(
                        'UPDATE cc_files SET requestable = true '
                        . "WHERE requestable = false AND id IN ({$idsCsv})"
                    );
                }
                $con->commit();
                Logging::info('RequestablePoolSyncTask: ' . count($ids) . ' tracks requestable');
            } catch (Exception $inner) {
                $con->rollBack();

                throw $inner;
            }
        } catch (Exception $exc) {
            Logging::error('RequestablePoolSyncTask failed: ' . $exc->getMessage());
        }
        Application_Model_Preference::setRequestablePoolLastSync(microtime(true));
    }
}

/**
 * Class RequestShowFillTask.
 *
 * RASTATIME 2026-06-07 - Song Requests, incremental just-in-time fill
 * (Variant Z).  Every REQUEST_FILL_INTERVAL_SECONDS it tops up every
 * "request show" (an autoload-playlist show whose playlist contains a
 * "use requests" smart block) that is currently running or about to
 * start, filling its schedule only up to now + LEAD_TIME_SECONDS by
 * appending the autoload playlist.  This keeps a small just-in-time
 * buffer so a request that arrives mid-show airs within ~one round,
 * while a safety lead (longer than the poll interval) prevents dead air
 * if a poll is delayed.  See AutoPlaylistManager::fillRequestShows().
 *
 * Distinct from AutoPlaylistTask: that one pre-fills NON-request
 * autoplaylist shows to 100 %; this one incrementally tops up request
 * shows and never sets autoplaylist_built.  Both intervals are
 * env-overridable for tuning.
 */
class RequestShowFillTask implements AirtimeTask
{
    public const REQUEST_FILL_INTERVAL_SECONDS = 120;  // 2 minutes
    public const LEAD_TIME_SECONDS = 480;              // 8 minutes safety lead

    public function shouldBeRun()
    {
        $interval = (int) (getenv('RASTATIME_REQUEST_FILL_INTERVAL_SECONDS')
            ?: self::REQUEST_FILL_INTERVAL_SECONDS);
        $lastRun = Application_Model_Preference::getRequestShowFillLastRun();

        return empty($lastRun) || (microtime(true) > $lastRun + $interval);
    }

    public function run()
    {
        $leadSecs = (int) (getenv('RASTATIME_REQUEST_FILL_LEAD_SECONDS')
            ?: self::LEAD_TIME_SECONDS);
        try {
            AutoPlaylistManager::fillRequestShows($leadSecs);
        } catch (Throwable $e) {
            Logging::error('RequestShowFillTask failed: ' . $e->getMessage());
        }
        Application_Model_Preference::setRequestShowFillLastRun(microtime(true));
    }
}

/**
 * Class TaskFactory Factory class to abstract task instantiation.
 */
class TaskFactory
{
    /**
     * Check if the class with the given name implements AirtimeTask.
     *
     * @param $c string class name
     *
     * @return bool true if the class $c implements AirtimeTask
     */
    private static function _isTask($c)
    {
        return array_key_exists('AirtimeTask', class_implements($c));
    }

    /**
     * Filter all declared classes to get all classes implementing the AirtimeTask interface.
     *
     * @return array all classes implementing the AirtimeTask interface
     */
    public static function getTasks()
    {
        return array_filter(get_declared_classes(), [__CLASS__, '_isTask']);
    }

    /**
     * Get an AirtimeTask based on class name.
     *
     * @param $task string name of the class implementing AirtimeTask to construct
     *
     * @return null|AirtimeTask return a task of the given type or null if no corresponding task exists
     */
    public static function getTask($task)
    {
        // Try to get a valid class name from the given string
        if (!class_exists($task)) {
            $task = str_replace(' ', '', ucwords($task)) . 'Task';
        }

        return class_exists($task) ? new $task() : null;
    }
}
