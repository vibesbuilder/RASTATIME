<?php

class SystemstatusController extends Zend_Controller_Action
{
    private $version;

    // RASTATIME 2026-05-16 - Whitelist of services the operator is allowed to
    // restart from the UI.  This is the only set of NSSM service names ever
    // passed to the shell from this controller; anything else is rejected
    // before reaching exec().  Keep alphabetical to match the UI order.
    const RESTARTABLE_SERVICES = [
        'RASTATIME-ANALYZER',
        'RASTATIME-API',
        'RASTATIME-APACHE',
        'RASTATIME-ICECAST',
        'RASTATIME-PLAYOUT',
        'RASTATIME-WORKER',
    ];

    public function init()
    {
        $config = Config::getConfig();
        $this->view->headScript()->appendFile(Assets::url('js/airtime/status/status.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/status/blocked-addresses.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/status/service-restart.js'), 'text/javascript');
        $this->version = $config['airtime_version'];
    }

    public function indexAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        $partitions = Application_Model_Systemstatus::GetDiskInfo();
        $this->view->status = new stdClass();
        $this->view->status->partitions = $partitions;
        // RASTATIME 2026-05-16 - Surface the fork-local version
        // (RASTATIME_VERSION) here instead of the upstream LibreTime
        // release.  The upstream value is still kept available as
        // $this->version for callers that need it (none currently in
        // this view).
        $this->view->version = RASTATIME_VERSION;
    }

    /**
     * RASTATIME 2026-05-16 - Restart a single Windows service via NSSM.
     *
     * Apache is restarted via a detached background command because the
     * Apache worker hosting THIS very PHP request would otherwise be killed
     * mid-response; all others run synchronously so the UI can report exec
     * exit codes back to the operator.
     *
     * POST only.  CSRF-protected.  Service name must be in the whitelist.
     */
    public function restartServiceAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token on restartServiceAction');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        $service = (string) $this->_getParam('service', '');
        if (!in_array($service, self::RESTARTABLE_SERVICES, true)) {
            Logging::warn('restartServiceAction: rejected non-whitelisted service ' . $service);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'unknown-service']);
            return;
        }

        $result = $this->_restartOneService($service);
        $this->_helper->json->sendJson($result);
    }

    /**
     * RASTATIME 2026-05-16 - Restart every whitelisted service.
     *
     * Order matters: Apache is always restarted LAST, after a longer delay,
     * so the other five services have triggered cleanly and the JSON
     * response below has already been delivered before Apache itself goes
     * down.  Apache hosting this very PHP request is the trickiest case.
     *
     * All six restarts are scheduled via temp .bat files spawned with
     * `wmic process call create` for guaranteed parent-process detachment;
     * see _scheduleDetachedRestart() for why `start /B` alone is not
     * enough.
     */
    public function restartAllAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token on restartAllAction');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        // Put Apache last so the other five services have already been
        // scheduled before Apache itself starts going down.
        $order = [];
        foreach (self::RESTARTABLE_SERVICES as $s) {
            if ($s !== 'RASTATIME-APACHE') {
                $order[] = $s;
            }
        }
        $order[] = 'RASTATIME-APACHE';

        $results = [];
        foreach ($order as $service) {
            // Apache gets a longer delay (6s vs 2s) so the JSON response we
            // are about to send has time to reach the browser AND the
            // Apache worker can finish/release before nssm tries to stop it.
            $delay = ($service === 'RASTATIME-APACHE') ? 6 : 2;
            $results[$service] = $this->_restartOneService($service, true, $delay);
        }
        $this->_helper->json->sendJson(['ok' => true, 'results' => $results]);
    }

    /**
     * Issue the NSSM restart for one whitelisted service.
     *
     * @param  string $service       NSSM service name (caller already
     *                               whitelisted)
     * @param  bool   $forceDetached force background execution even for
     *                               services that would otherwise be sync
     * @param  int    $delaySeconds  for detached restarts: seconds to sleep
     *                               in the batch file before calling nssm,
     *                               so the HTTP response delivers cleanly
     * @return array                 ['ok' => bool, 'mode' => 'sync'|'detached',
     *                                'exit' => int|null, 'output' => string|null]
     */
    /**
     * RASTATIME 2026-10-06 - GET systemstatus/blocked-addresses: the
     * brute-force brakes' current state (web login per address / user, DJ
     * harbor, firewall watcher rules) for the "Blocked addresses" section.
     */
    public function blockedAddressesAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $this->_helper->json->sendJson([
            'ok' => true,
            'rows' => Application_Model_BlockedAddresses::listAll(),
            // RASTATIME 2026-10-08 - the allow list for the second table
            'allowed' => Application_Model_AllowedAddresses::all(),
            'generated_at' => gmdate('c'),
        ]);
    }

    /**
     * RASTATIME 2026-10-08 - POST systemstatus/allow-address (entry, csrf):
     * put an address or CIDR network on the allow list; a plain address is
     * unblocked on every layer at the same time ("Allow" in the blocked
     * list).
     */
    public function allowAddressAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token on allowAddressAction');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $entry = trim((string) $this->_getParam('entry', ''));
        if (!Application_Model_AllowedAddresses::isValidEntry($entry)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'bad-entry']);
            return;
        }
        Application_Model_AllowedAddresses::add($entry);
        $unblocked = null;
        if (Application_Model_BlockedAddresses::looksLikeAddress($entry)) {
            $unblocked = Application_Model_BlockedAddresses::unblock($entry);
        }
        $this->_helper->json->sendJson([
            'ok' => true,
            'entry' => Application_Model_AllowedAddresses::normalise($entry),
            'unblocked' => $unblocked,
            'allowed' => Application_Model_AllowedAddresses::all(),
        ]);
    }

    /** RASTATIME 2026-10-08 - POST systemstatus/disallow-address (entry, csrf). */
    public function disallowAddressAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token on disallowAddressAction');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $entry = trim((string) $this->_getParam('entry', ''));
        if ($entry === '') {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'bad-entry']);
            return;
        }
        Application_Model_AllowedAddresses::remove($entry);
        $this->_helper->json->sendJson(['ok' => true, 'allowed' => Application_Model_AllowedAddresses::all()]);
    }

    /**
     * RASTATIME 2026-10-06 - POST systemstatus/unblock-address (key, csrf):
     * clear one address (or "user:<login>") on every layer.
     */
    public function unblockAddressAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token on unblockAddressAction');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $key = trim((string) $this->_getParam('key', ''));
        if ($key === '' || (strpos($key, 'user:') !== 0 && !Application_Model_BlockedAddresses::looksLikeAddress($key))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'bad-key']);
            return;
        }
        $result = Application_Model_BlockedAddresses::unblock($key);
        $result['ok'] = true;
        $this->_helper->json->sendJson($result);
    }

    private function _restartOneService($service, $forceDetached = false, $delaySeconds = 4)
    {
        // Apache hosts this PHP process; synchronous restart would kill our
        // own response.  Use a detached background process so nssm runs
        // independently of this request.
        $detached = $forceDetached || $service === 'RASTATIME-APACHE';

        if ($detached) {
            return $this->_scheduleDetachedRestart($service, $delaySeconds);
        }

        // Synchronous path: safe for services that do not host this PHP
        // worker (everything except Apache).  We can wait on the exit code
        // and return it so the UI shows a concrete success/failure.
        $cmd = 'nssm restart ' . escapeshellarg($service);
        $output = [];
        $exit = 0;
        exec($cmd . ' 2>&1', $output, $exit);
        Logging::info('restartService (sync): ' . $service . ' exit=' . $exit);
        return [
            'ok' => $exit === 0,
            'mode' => 'sync',
            'exit' => $exit,
            'output' => implode("\n", $output),
        ];
    }

    /**
     * RASTATIME 2026-05-16 - Spawn a detached batch file that, after a
     * short sleep, calls `nssm restart <service>` and self-deletes.
     *
     * Why this is more complicated than `start /B "" nssm restart X`:
     *
     *   * `start /B` keeps the spawned child in the SAME console as the
     *     parent (the PHP/Apache worker).  Windows can — and on default
     *     mpm_winnt with NSSM does — group these via a Job Object.  When
     *     the Apache worker itself dies as part of the restart, the Job
     *     Object kills the child as a side effect, leaving Apache half-
     *     stopped ("Wird beendet" / SERVICE_STOP_PENDING) with no
     *     surviving process to issue `nssm start` afterwards.  This was
     *     the cause of the "Restart All" hang on 2026-05-16.
     *
     *   * `wmic process call create` spawns the new process under WMI
     *     service ownership, NOT under Apache's job object, so the child
     *     survives Apache going down.
     *
     *   * The intermediate .bat is needed because we want a delay (so the
     *     HTTP response has time to flush before nssm reaches into Apache)
     *     and because chaining `ping ... && nssm ...` inline through
     *     wmic's argument quoting is fragile.
     *
     * The batch self-deletes via `del "%~f0"` once nssm has returned.
     */
    private function _scheduleDetachedRestart($service, $delaySeconds = 4)
    {
        $tempDir = sys_get_temp_dir();
        // `ping 127.0.0.1 -n N` waits ~(N-1) seconds.  Min N=2 yields 1s.
        $pingCount = max(2, (int) $delaySeconds + 1);

        $batchName = sprintf(
            'rastatime-restart-%s-%d-%d.bat',
            strtolower($service),
            time(),
            mt_rand(1000, 9999)
        );
        $batchPath = $tempDir . DIRECTORY_SEPARATOR . $batchName;

        $batch = "@echo off\r\n"
               . "rem RASTATIME service restart - auto-generated, self-deleting\r\n"
               . "rem Service: " . $service . "\r\n"
               . "rem Created: " . date('c') . "\r\n"
               . "ping 127.0.0.1 -n " . $pingCount . " > nul\r\n"
               . "nssm restart " . $service . " > nul 2>&1\r\n"
               . "del \"%~f0\"\r\n";

        if (@file_put_contents($batchPath, $batch) === false) {
            Logging::error('_scheduleDetachedRestart: failed to write batch ' . $batchPath);
            return [
                'ok' => false,
                'mode' => 'detached',
                'exit' => null,
                'output' => 'batch-write-failed: ' . $batchPath,
            ];
        }

        // wmic syntax: spawn cmd.exe to run our batch, fully detached from
        // the Apache worker's process tree.  WMIC returns nonzero on
        // syntactical failure but the actual restart proceeds inside the
        // newly-spawned cmd process regardless.
        //
        // Escape inner double quotes for cmd: the batch path may contain
        // spaces (typical when sys_get_temp_dir() is under "C:\Users\<svc>
        // \AppData\Local\Temp"), so we wrap it in escaped quotes.
        $escapedBatch = str_replace('"', '""', $batchPath);
        $wmicCmd = 'wmic process call create "cmd.exe /c \"\"' . $escapedBatch . '\"\"" > nul 2>&1';

        $wmicExit = 0;
        $wmicOut = [];
        @exec($wmicCmd, $wmicOut, $wmicExit);

        if ($wmicExit !== 0) {
            // wmic is deprecated on recent Windows builds and may be
            // missing entirely.  Fall back to `start /B` which is less
            // robust against Job Object cleanup but better than nothing.
            Logging::warn(
                '_scheduleDetachedRestart: wmic exit=' . $wmicExit
                . ' for ' . $service . ', falling back to start /B'
            );
            $startCmd = 'start /B "" cmd /c "' . $batchPath . '"';
            $h = @popen($startCmd, 'r');
            if ($h !== false) {
                pclose($h);
            }
        }

        Logging::info(
            '_scheduleDetachedRestart: scheduled ' . $service
            . ' delay=' . $delaySeconds . 's via ' . basename($batchPath)
            . ' (wmic_exit=' . $wmicExit . ')'
        );

        return [
            'ok' => true,
            'mode' => 'detached',
            'exit' => null,
            'output' => null,
            'batch' => basename($batchPath),
            'delay_seconds' => $delaySeconds,
        ];
    }
}
