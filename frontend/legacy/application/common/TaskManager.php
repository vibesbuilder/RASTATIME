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
    // RASTATIME 2026-09-17 - quiet-period guard: only import files
    // untouched for this long.  A file still being written (slow
    // network copy, FTP upload) must not be grabbed mid-write - the
    // move would truncate it and a failed attempt DELETES the source.
    public const QUIET_SECONDS = 60;
    public const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'oga', 'aac', 'opus'];

    public function shouldBeRun()
    {
        $folder = Application_Model_Preference::getLocalImportFolder();
        if (empty($folder)) {
            return false;  // disabled
        }
        if (Application_Common_Storage::isMoving()) {
            return false;  // RASTATIME 2026-09-16 - library move in progress
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
     * @return array  ['imported' => int, 'failed' => int, 'skipped' => int, 'settling' => int]
     */
    public static function scanOnce($folder)
    {
        $imported = 0;
        $failed = 0;
        $skipped = 0;
        $settling = 0;

        Application_Model_Preference::setLocalImportLastRun(time());

        if (!is_dir($folder)) {
            $msg = 'Folder missing or unreadable: ' . $folder;
            Logging::warn('LocalImportScanTask: ' . $msg);
            Application_Model_Preference::setLocalImportLastStatus($msg);
            return compact('imported', 'failed', 'skipped', 'settling');
        }

        $entries = @scandir($folder);
        if ($entries === false) {
            $msg = 'scandir failed for: ' . $folder;
            Logging::warn('LocalImportScanTask: ' . $msg);
            Application_Model_Preference::setLocalImportLastStatus($msg);
            return compact('imported', 'failed', 'skipped', 'settling');
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

            // RASTATIME 2026-09-17 - quiet-period guard (operator go
            // after the network/FTP-source evaluation): a file whose
            // mtime is younger than QUIET_SECONDS may still be being
            // written - leave it for the next scan.  filemtime failure
            // counts as settling too (transient share hiccup).
            $mtime = @filemtime($fullPath);
            if ($mtime === false || (time() - $mtime) < self::QUIET_SECONDS) {
                $settling++;
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
            'imported %d, failed %d, skipped %d, settling %d',
            $imported, $failed, $skipped, $settling
        );
        Application_Model_Preference::setLocalImportLastStatus($status);
        if ($imported > 0 || $failed > 0) {
            Logging::info('LocalImportScanTask: ' . $status);
        }

        return compact('imported', 'failed', 'skipped', 'settling');
    }
}

/**
 * Class FtpImportScanTask.
 *
 * RASTATIME 2026-09-17 - "Import from FTP Server" (operator go).  Every
 * 5 minutes (and on-demand via Settings -> Local Machine -> "Fetch now")
 * connects to an operator-configured FTP / FTPS / SFTP server, downloads
 * every audio file from the remote folder into the LOCAL Import Folder
 * and deletes the remote original after a verified download (mailbox
 * semantics, operator decision 2026-09-17).  From the import folder on,
 * the LocalImportScanTask chain takes over unchanged (quiet period,
 * organize, analyzer) - deliberately no second import path.
 *
 * Safety: a file is only accepted when the remote size probed AFTER the
 * download matches the local byte count - a file still being uploaded
 * changes size, the partial download is discarded and the remote file
 * stays for the next cycle.  Non-audio files are left on the server.
 * The Import Folder must be configured; without it the task refuses
 * with a clear status.  Remote deletes need delete permission on the
 * FTP account; a failed delete keeps the local copy and warns (the
 * next cycle would fetch a duplicate otherwise).
 *
 * Transfers run through PHP-curl (this build speaks ftp, ftps and
 * sftp).  "ftps" means explicit TLS on the ftp port (AUTH TLS), the
 * hoster standard.  Credentials live in the cc_pref JSON
 * local_ftp_import_config like other service passwords; they are never
 * logged and never sent back to the browser.
 */
class FtpImportScanTask implements AirtimeTask
{
    public const FTP_IMPORT_INTERVAL_SECONDS = 300;  // 5 minutes
    public const CONNECT_TIMEOUT_SECONDS = 10;
    public const TRANSFER_TIMEOUT_SECONDS = 240;     // per file
    public const RUN_BUDGET_SECONDS = 60;            // start no new download after this
    public const PROTOCOLS = ['ftp', 'ftps', 'sftp'];

    public function shouldBeRun()
    {
        $cfg = Application_Model_Preference::getFtpImportConfig();
        if (empty($cfg['enabled']) || empty($cfg['host'])) {
            return false;
        }
        if (Application_Common_Storage::isMoving()) {
            return false;
        }
        $lastRun = Application_Model_Preference::getFtpImportLastRun();
        return empty($lastRun)
            || (microtime(true) > $lastRun + self::FTP_IMPORT_INTERVAL_SECONDS);
    }

    public function run()
    {
        self::fetchOnce();
    }

    /**
     * One fetch cycle: read the config, guard the landing area, fetch,
     * persist last-run + status.  Shared by the task and "Fetch now".
     *
     * @return array result counts (see fetchFromServer) or ['error' => msg]
     */
    public static function fetchOnce()
    {
        Application_Model_Preference::setFtpImportLastRun(time());
        $cfg = Application_Model_Preference::getFtpImportConfig();
        $importFolder = Application_Model_Preference::getLocalImportFolder();
        if (empty($importFolder) || !is_dir($importFolder)) {
            $msg = 'Import Folder not configured - the FTP import needs it as its landing area.';
            Logging::warn('FtpImportScanTask: ' . $msg);
            Application_Model_Preference::setFtpImportLastStatus($msg);
            return ['error' => $msg];
        }
        $pending = Application_Model_Preference::getFtpImportPending();
        $r = self::fetchFromServer($cfg, $importFolder, $pending);
        Application_Model_Preference::setFtpImportPending($r['pending']);
        foreach ($r['log'] as $line) {
            Logging::info('FtpImportScanTask: ' . $line);
        }
        if (isset($r['error'])) {
            $status = 'ERROR: ' . $r['error'];
        } else {
            $status = sprintf(
                'fetched %d, settling %d, failed %d, non-audio left %d',
                $r['fetched'], $r['unstable'], $r['failed'], $r['non_audio']
            );
            if ($r['left'] > 0) {
                $status .= sprintf(', %d left for the next run', $r['left']);
            }
        }
        Application_Model_Preference::setFtpImportLastStatus($status);
        return $r;
    }

    /**
     * Pure worker: no Preference access, so it can be exercised from a
     * CLI test against a throwaway server.
     */
    public static function fetchFromServer(
        array $cfg,
        $importFolder,
        array $pending = [],
        $quietSeconds = LocalImportScanTask::QUIET_SECONDS
    ) {
        $fetched = 0;
        $unstable = 0;
        $failed = 0;
        $nonAudio = 0;
        $left = 0;
        $log = [];
        $newPending = [];
        $started = microtime(true);

        [$ok, $names, $err] = self::listNames($cfg);
        if (!$ok) {
            return [
                'error' => 'listing failed: ' . $err,
                'fetched' => 0, 'unstable' => 0, 'failed' => 0,
                'non_audio' => 0, 'left' => 0, 'pending' => $pending,
                'log' => ['listing failed for ' . self::describe($cfg) . ': ' . $err],
            ];
        }
        foreach ($names as $name) {
            $name = basename(trim($name));
            if ($name === '' || $name === '.' || $name === '..') {
                continue;
            }
            $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
            if (!in_array($ext, LocalImportScanTask::AUDIO_EXTENSIONS, true)) {
                $nonAudio++;
                continue;
            }
            if (microtime(true) - $started > self::RUN_BUDGET_SECONDS) {
                $left++;                       // budget spent - next cycle
                continue;
            }

            // RASTATIME 2026-09-17 - remote quiet rule (the FTP twin of the
            // local 60-s guard, added after the growing-file replica showed
            // that the post-download probe alone misses bursty uploads): a
            // file is only fetched when its size matches a sighting at
            // least $quietSeconds ago.  Everything younger stays remote and
            // is counted as "still uploading".
            $size = self::probeSize($cfg, $name);
            if ($size >= 0) {
                $seen = $pending[$name] ?? null;
                $stable = is_array($seen)
                    && (int) $seen['size'] === $size
                    && (time() - (int) $seen['seen_at']) >= $quietSeconds;
                if (!$stable) {
                    $keep = (is_array($seen) && (int) $seen['size'] === $size)
                        ? $seen : ['size' => $size, 'seen_at' => time()];
                    $newPending[$name] = $keep;
                    $unstable++;
                    continue;
                }
            }
            $tmp = $importFolder . DIRECTORY_SEPARATOR . '.ftp-' . $name . '.part';
            [$ok, $err] = self::downloadTo($cfg, $name, $tmp);
            if (!$ok) {
                $failed++;
                $log[] = 'download failed for ' . $name . ': ' . $err;
                @unlink($tmp);
                continue;
            }
            $localBytes = (int) @filesize($tmp);
            $remoteBytes = self::probeSize($cfg, $name);
            if ($remoteBytes >= 0 && $remoteBytes !== $localBytes) {
                $unstable++;                   // still being uploaded
                $newPending[$name] = ['size' => $remoteBytes, 'seen_at' => time()];
                $log[] = $name . ' is still changing on the server ('
                    . $remoteBytes . ' vs ' . $localBytes . ' bytes) - left for the next cycle';
                @unlink($tmp);
                continue;
            }
            $target = $importFolder . DIRECTORY_SEPARATOR . $name;
            if (file_exists($target)) {
                $target = $importFolder . DIRECTORY_SEPARATOR
                    . 'ftp-' . date('Ymd-His') . ' ' . $name;
            }
            if (!@rename($tmp, $target)) {
                $failed++;
                $log[] = 'could not place ' . $name . ' into the import folder';
                @unlink($tmp);
                continue;
            }
            $fetched++;
            [$ok, $err] = self::deleteRemote($cfg, $name);
            if ($ok) {
                $log[] = 'fetched ' . $name . ' (' . $localBytes . ' bytes), remote deleted';
            } else {
                $log[] = 'fetched ' . $name . ' but the REMOTE DELETE failed (' . $err
                    . ') - the next cycle will fetch a duplicate; give the account delete permission';
            }
        }

        return compact('fetched', 'unstable', 'failed', 'left', 'log')
            + ['non_audio' => $nonAudio, 'pending' => $newPending];
    }

    // ---- curl helpers ----------------------------------------------------

    /** Loggable server description - never contains credentials. */
    private static function describe(array $cfg)
    {
        return ($cfg['protocol'] ?? 'ftp') . '://' . ($cfg['host'] ?? '')
            . self::remoteDir($cfg);
    }

    /** Remote folder with leading + trailing slash ('/' stays '/'). */
    private static function remoteDir(array $cfg)
    {
        $path = trim((string) ($cfg['path'] ?? ''));
        $path = '/' . trim(str_replace('\\', '/', $path), '/');
        return $path === '/' ? '/' : $path . '/';
    }

    /**
     * A curl handle for the given remote path (already URL-encoded by
     * the caller where needed).  "ftps" = explicit TLS on the ftp port.
     */
    private static function handle(array $cfg, $remotePath)
    {
        $protocol = in_array($cfg['protocol'] ?? '', self::PROTOCOLS, true)
            ? $cfg['protocol'] : 'ftp';
        $scheme = $protocol === 'sftp' ? 'sftp' : 'ftp';
        $curl = curl_init($scheme . '://' . $cfg['host'] . $remotePath);
        $opts = [
            CURLOPT_USERNAME       => (string) ($cfg['username'] ?? ''),
            CURLOPT_PASSWORD       => (string) ($cfg['password'] ?? ''),
            CURLOPT_CONNECTTIMEOUT => self::CONNECT_TIMEOUT_SECONDS,
            CURLOPT_PROTOCOLS      => CURLPROTO_FTP | CURLPROTO_FTPS | CURLPROTO_SFTP,
        ];
        if (!empty($cfg['port'])) {
            $opts[CURLOPT_PORT] = (int) $cfg['port'];
        }
        if ($protocol === 'ftps') {
            $opts[CURLOPT_USE_SSL] = CURLUSESSL_ALL;   // AUTH TLS, verified via curl.cainfo
        }
        curl_setopt_array($curl, $opts);
        return $curl;
    }

    private static function exec($curl)
    {
        $out = curl_exec($curl);
        $err = curl_errno($curl) ? curl_error($curl) : null;
        return [$out, $err];
    }

    /** @return array [ok, names[], err] */
    private static function listNames(array $cfg)
    {
        $curl = self::handle($cfg, self::remoteDir($cfg));
        curl_setopt_array($curl, [
            CURLOPT_DIRLISTONLY    => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 30,
        ]);
        [$out, $err] = self::exec($curl);
        curl_close($curl);
        if ($err !== null || !is_string($out)) {
            return [false, [], $err ?: 'no listing'];
        }
        return [true, preg_split('/\r\n|\n|\r/', $out, -1, PREG_SPLIT_NO_EMPTY), null];
    }

    /** @return array [ok, err] */
    private static function downloadTo(array $cfg, $name, $localPath)
    {
        $fh = @fopen($localPath, 'wb');
        if ($fh === false) {
            return [false, 'cannot write ' . $localPath];
        }
        $curl = self::handle($cfg, self::remoteDir($cfg) . rawurlencode($name));
        curl_setopt_array($curl, [
            CURLOPT_FILE            => $fh,
            CURLOPT_TIMEOUT         => self::TRANSFER_TIMEOUT_SECONDS,
            CURLOPT_LOW_SPEED_LIMIT => 500,     // abort a stalled transfer
            CURLOPT_LOW_SPEED_TIME  => 30,
        ]);
        [, $err] = self::exec($curl);
        curl_close($curl);
        fclose($fh);
        return [$err === null, $err];
    }

    /** Remote size, or -1 when the server cannot report it (accept then). */
    private static function probeSize(array $cfg, $name)
    {
        $curl = self::handle($cfg, self::remoteDir($cfg) . rawurlencode($name));
        curl_setopt_array($curl, [
            CURLOPT_NOBODY         => true,
            CURLOPT_RETURNTRANSFER => true,   // keep headers off stdout
            CURLOPT_TIMEOUT        => 30,
        ]);
        [, $err] = self::exec($curl);
        $len = curl_getinfo($curl, CURLINFO_CONTENT_LENGTH_DOWNLOAD);
        curl_close($curl);
        if ($err !== null || $len === false || $len < 0) {
            return -1;
        }
        return (int) $len;
    }

    /**
     * Delete the remote original via a QUOTE command with the absolute
     * remote path (works from any directory; the remote folder must be
     * configured as an absolute path).  @return array [ok, err]
     */
    private static function deleteRemote(array $cfg, $name)
    {
        $absolute = self::remoteDir($cfg) . $name;
        $command = ($cfg['protocol'] ?? '') === 'sftp'
            ? 'rm ' . $absolute
            : 'DELE ' . $absolute;
        $curl = self::handle($cfg, self::remoteDir($cfg));
        curl_setopt_array($curl, [
            CURLOPT_DIRLISTONLY    => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_QUOTE          => [$command],
        ]);
        [, $err] = self::exec($curl);
        curl_close($curl);
        return [$err === null, $err];
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
 * Class RequestPlayedTask.
 *
 * RASTATIME 2026-06-07 — Song Requests, Phase 6b (played marking).
 *
 * Operator decision 2026-06-07: detect "played" via the schedule, NOT a
 * playout hook — no change to the live broadcast path for a status that is
 * audit-only (Phase 6a already cleared the pool filter `requested` when the
 * track was scheduled).  Every interval, any 'queued' request whose track
 * sat in a cc_schedule slot that has since ended (after the request was
 * made) becomes 'played' with played_at = now.  The cc_files aggregate is
 * untouched — Phase 6a already removed the track from the pool.
 *
 * Timezone: cc_schedule.ends is `timestamp WITHOUT tz` holding UTC, while
 * created_at is `timestamp WITH tz`.  Both sides are compared as naive UTC
 * via `AT TIME ZONE 'UTC'`, so the result is independent of the PDO session
 * timezone.
 */
class RequestPlayedTask implements AirtimeTask
{
    public const REQUEST_PLAYED_INTERVAL_SECONDS = 120;  // 2 minutes

    public function shouldBeRun()
    {
        $interval = (int) (getenv('RASTATIME_REQUEST_PLAYED_INTERVAL_SECONDS')
            ?: self::REQUEST_PLAYED_INTERVAL_SECONDS);
        $lastRun = Application_Model_Preference::getRequestPlayedLastRun();

        return empty($lastRun) || (microtime(true) > $lastRun + $interval);
    }

    public function run()
    {
        try {
            $stmt = Propel::getConnection()->prepare(
                "UPDATE rastatime_song_request
                    SET status = 'played', played_at = NOW()
                  WHERE status = 'queued'
                    AND EXISTS (
                        SELECT 1 FROM cc_schedule s
                         WHERE s.file_id = rastatime_song_request.file_id
                           AND s.ends < (NOW() AT TIME ZONE 'UTC')
                           AND s.ends >= (rastatime_song_request.created_at
                                          AT TIME ZONE 'UTC')
                    )"
            );
            $stmt->execute();
            $rows = $stmt->rowCount();
            if ($rows > 0) {
                Logging::info("RequestPlayedTask: marked {$rows} requests played");
            }
        } catch (Throwable $e) {
            Logging::error('RequestPlayedTask failed: ' . $e->getMessage());
        }
        Application_Model_Preference::setRequestPlayedLastRun(microtime(true));
    }
}

/**
 * Class RequestExpiryTask.
 *
 * RASTATIME 2026-06-07 — Song Requests, lifecycle cleanup (Phase 6c + the
 * 2026-06-09 queued-corpse re-pend).
 *
 * Two sweeps every interval:
 *  - Re-pend "queued corpses": a request that was scheduled into a show
 *    (status 'queued') whose show was then deleted before the track aired now
 *    sits in NO cc_schedule row.  It goes back to 'pending' so the next request
 *    show retries it.  ONLY genuine corpses are touched — a track still
 *    scheduled anywhere (its own show or another) is left to air and be marked
 *    'played' — so a live queued request is never re-pended and duplicated.
 *  - Expire stale: any 'pending' request older than the (env-overridable) TTL
 *    becomes 'expired'.  This also catches a re-pended corpse already older
 *    than the TTL, so a never-fulfilled wish does not loop forever.
 * The cc_files aggregate for every affected track is then recomputed from the
 * surviving pending rows: a re-pended track regains pool membership
 * (requested = true), an expired track whose last request is gone drops out.
 *
 * created_at is `timestamp WITH tz`; the TTL comparison is timestamptz vs
 * NOW() (also timestamptz), absolute and session-tz independent.  The
 * recomputed requested_at is cast to naive UTC to match the cc_files column
 * type.  The TTL is a validated integer, inlined (no bind-param interval-type
 * ambiguity).
 */
class RequestExpiryTask implements AirtimeTask
{
    public const REQUEST_EXPIRY_INTERVAL_SECONDS = 600;  // 10 minutes
    public const REQUEST_EXPIRY_TTL_HOURS = 8;

    public function shouldBeRun()
    {
        $interval = (int) (getenv('RASTATIME_REQUEST_EXPIRY_INTERVAL_SECONDS')
            ?: self::REQUEST_EXPIRY_INTERVAL_SECONDS);
        $lastRun = Application_Model_Preference::getRequestExpiryLastRun();

        return empty($lastRun) || (microtime(true) > $lastRun + $interval);
    }

    public function run()
    {
        $ttlHours = (int) (getenv('RASTATIME_REQUEST_EXPIRY_HOURS')
            ?: self::REQUEST_EXPIRY_TTL_HOURS);
        try {
            // 1. Re-pend "queued corpses": a request scheduled into a show
            //    whose show was deleted before airing now sits in NO cc_schedule
            //    row.  Put the wish back into the pool so the next request show
            //    retries it.  A track still scheduled anywhere is left alone.
            $repended = Application_Common_Database::prepareAndExecute(
                "UPDATE rastatime_song_request
                    SET status = 'pending'
                  WHERE status = 'queued'
                    AND NOT EXISTS (
                        SELECT 1 FROM cc_schedule s
                         WHERE s.file_id = rastatime_song_request.file_id)
                RETURNING file_id",
                [],
                Application_Common_Database::ALL
            );

            // 2. Expire stale pending requests (incl. any just re-pended that
            //    are already past the TTL), capturing the affected tracks.
            $expired = Application_Common_Database::prepareAndExecute(
                "UPDATE rastatime_song_request
                    SET status = 'expired'
                  WHERE status = 'pending'
                    AND created_at < NOW() - INTERVAL '1 hour' * {$ttlHours}
                RETURNING file_id",
                [],
                Application_Common_Database::ALL
            );

            if (empty($repended) && empty($expired)) {
                Application_Model_Preference::setRequestExpiryLastRun(microtime(true));

                return;
            }

            // 3. Recompute the cc_files aggregate for every affected track from
            //    the surviving pending rows (truth = rastatime_song_request):
            //    a re-pended track regains requested = true, an expired track
            //    whose last request is gone drops to requested = false.
            $ids = [];
            foreach ($repended as $r) {
                $ids[(int) $r['file_id']] = true;
            }
            foreach ($expired as $r) {
                $ids[(int) $r['file_id']] = true;  // dedupe via keys
            }
            $idList = implode(',', array_keys($ids));
            Application_Common_Database::prepareAndExecute(
                "UPDATE cc_files SET
                    request_count = (
                        SELECT COUNT(*) FROM rastatime_song_request r
                         WHERE r.file_id = cc_files.id AND r.status = 'pending'),
                    requested = EXISTS (
                        SELECT 1 FROM rastatime_song_request r
                         WHERE r.file_id = cc_files.id AND r.status = 'pending'),
                    requested_at = (
                        SELECT MIN(r.created_at AT TIME ZONE 'UTC')
                          FROM rastatime_song_request r
                         WHERE r.file_id = cc_files.id AND r.status = 'pending')
                  WHERE id IN ({$idList})",
                [],
                Application_Common_Database::EXECUTE
            );
            Logging::info(
                'RequestExpiryTask: re-pended ' . count($repended)
                . ', expired ' . count($expired)
                . ' requests, refreshed ' . count($ids) . ' tracks'
            );
        } catch (Throwable $e) {
            Logging::error('RequestExpiryTask failed: ' . $e->getMessage());
        }
        Application_Model_Preference::setRequestExpiryLastRun(microtime(true));
    }
}

/**
 * Class ShowShiftTask.
 *
 * RASTATIME 2026-06-15 — Show-Shift / "Allow delayed start", Phase 3a.
 *
 * Every interval (default 2 min, env-overridable) shifts any opted-in show
 * (cc_show.allow_delayed_start) that a preceding overrun pushes into, within
 * a 15-minute lead window.  Idempotent: a show already sitting at its
 * predecessor's content end is left alone.  Applies to manually-filled shows
 * too — it works off the cc_schedule rows, not how they were filled.  See
 * Application_Service_ShowShiftService for the mechanism.
 */
class ShowShiftTask implements AirtimeTask
{
    public const SHOW_SHIFT_INTERVAL_SECONDS = 120;  // 2 minutes

    public function shouldBeRun()
    {
        $interval = (int) (getenv('RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS')
            ?: self::SHOW_SHIFT_INTERVAL_SECONDS);
        $lastRun = Application_Model_Preference::getShowShiftLastRun();

        return empty($lastRun) || (microtime(true) > $lastRun + $interval);
    }

    public function run()
    {
        try {
            Application_Service_ShowShiftService::applyDelayedStarts();
        } catch (Throwable $e) {
            Logging::error('ShowShiftTask failed: ' . $e->getMessage());
        }
        Application_Model_Preference::setShowShiftLastRun(microtime(true));
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
