<?php

class PreferenceController extends Zend_Controller_Action
{
    public function init()
    {
        // Initialize action controller here
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('server-browse', 'json')
            ->addActionContext('change-stor-directory', 'json')
            ->addActionContext('reload-watch-directory', 'json')
            ->addActionContext('remove-watch-directory', 'json')
            ->addActionContext('is-import-in-progress', 'json')
            ->addActionContext('change-stream-setting', 'json')
            ->addActionContext('get-liquidsoap-status', 'json')
            ->addActionContext('get-admin-password-status', 'json')
            ->initContext();
    }

    public function indexAction()
    {
        $request = $this->getRequest();

        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        $baseUrl = Config::getBasePath();

        $this->view->headScript()->appendFile(Assets::url('js/airtime/preferences/preferences.js'), 'text/javascript');
        $this->view->statusMsg = '';

        $form = new Application_Form_Preferences();
        $values = [];

        SessionHelper::reopenSessionForWriting();

        if ($request->isPost()) {
            $values = $request->getPost();
            if ($form->isValid($values)) {
                Application_Model_Preference::SetHeadTitle($values['stationName'], $this->view);
                Application_Model_Preference::SetStationDescription($values['stationDescription']);
                Application_Model_Preference::SetTrackTypeDefault($values['tracktypeDefault']);
                // RASTATIME 2026-09-29 - a changed house crossfade re-lays the rows of
                // all upcoming shows (the layout was never refreshed before: rows laid
                // out with 1 s ran ahead of the playout after the change to 3 s)
                $crossfadeBefore = [
                    (float) Application_Model_Preference::GetDefaultCrossfadeDuration(),
                    (float) Application_Model_Preference::GetDefaultShowCrossfadeDuration(),
                ];
                Application_Model_Preference::SetDefaultCrossfadeDuration($values['stationDefaultCrossfadeDuration']);
                Application_Model_Preference::SetDefaultShowCrossfadeDuration($values['stationDefaultShowCrossfadeDuration']);
                $crossfadeAfter = [
                    (float) Application_Model_Preference::GetDefaultCrossfadeDuration(),
                    (float) Application_Model_Preference::GetDefaultShowCrossfadeDuration(),
                ];
                if ($crossfadeBefore !== $crossfadeAfter) {
                    try {
                        Application_Model_Scheduler::relayoutFutureInstances();
                        Application_Model_RabbitMq::PushSchedule();
                    } catch (Exception $e) {
                        Logging::warn('crossfade re-layout after the settings change failed: ' . $e->getMessage());
                    }
                }
                Application_Model_Preference::SetPodcastAlbumOverride($values['podcastAlbumOverride']);
                Application_Model_Preference::SetPodcastAutoSmartblock($values['podcastAutoSmartblock']);
                Application_Model_Preference::SetIntroPlaylist($values['introPlaylistSelect']);
                Application_Model_Preference::SetOutroPlaylist($values['outroPlaylistSelect']);
                Application_Model_Preference::setRequestablePoolBlockIds($values['requestablePoolSelect'] ?? []);
                Application_Model_Preference::setTrafficAlertBlockId($values['trafficAlertBlockSelect'] ?? 0);
                Application_Model_Preference::SetAllow3rdPartyApi($values['thirdPartyApi']);
                // RASTATIME 2026-05-15 - Sync all three Locale source surfaces in
                // one save.  Legacy upstream only wrote the global default
                // (cc_pref.locale), but GetLocale() for a logged-in user prefers
                // cc_pref.user_locale, and the airtime_locale cookie out-
                // prioritises both in the pre-login / Edit-User paths.  Result on
                // upstream: an admin who flips "Default Language" sees no UI
                // change for themselves.  We keep all three in lockstep.
                Application_Model_Preference::SetDefaultLocale($values['locale']);
                Application_Model_Preference::SetUserLocale($values['locale']);
                setcookie('airtime_locale', $values['locale'], [
                    'expires' => time() + (10 * 365 * 24 * 60 * 60),
                    'path'    => '/',
                ]);
                // Apply immediately so the "Preferences updated" message and the
                // re-rendered form labels are already in the new language.
                Application_Model_Locale::configureLocalization($values['locale']);
                Application_Model_Preference::SetWeekStartDay($values['weekStartDay']);
                Application_Model_Preference::setScheduleTrimOverbooked($values['scheduleTrimOverbooked']);
                // RASTATIME 2026-09-27 — Show-Shift filler playlist.
                Application_Model_Preference::setShowShiftFillerPlaylistId(
                    $values['showShiftFillerPlaylistSelect'] ?? 0
                );
                Application_Model_Preference::setRadioPageDisplayLoginButton($values['radioPageLoginButton']);
                Application_Model_Preference::setRadioPageDisabled($values['radioPageDisabled']);
                // RASTATIME 2026-09-29 - UI primary colour ('' = default).
                Application_Model_Preference::SetUiAccentColor($values['uiAccentColor'] ?? '');
                // RASTATIME 2026-10-26 - UI secondary colour ('' = default).
                Application_Model_Preference::SetUiSecondaryColor($values['uiSecondaryColor'] ?? '');
                // RASTATIME 2026-05-15 - SetFeaturePreviewMode removed (phantom setting).

                $logoUploadElement = $form->getSubForm('preferences_general')->getElement('stationLogo');
                $logoUploadElement->receive();
                $imagePath = $logoUploadElement->getFileName();

                // Only update the image logo if the new logo is non-empty
                if (!empty($imagePath) && $imagePath != '') {
                    Application_Model_Preference::SetStationLogo($imagePath);
                }

                // RASTATIME 2026-05-15 - Same pattern for the favicon upload.
                $faviconUploadElement = $form->getSubForm('preferences_general')->getElement('stationFavicon');
                $faviconUploadElement->receive();
                $faviconPath = $faviconUploadElement->getFileName();
                if (!empty($faviconPath) && $faviconPath != '') {
                    Application_Model_Preference::SetStationFavicon($faviconPath);
                }

                // RASTATIME 2026-10-07 - landing page background (a file in the storage root)
                $bgUploadElement = $form->getSubForm('preferences_general')->getElement('landingBackground');
                $bgUploadElement->receive();
                $bgPath = $bgUploadElement->getFileName();
                if (!empty($bgPath) && $bgPath != '') {
                    try {
                        Application_Model_Preference::SetLandingBackground($bgPath);
                    } catch (Exception $e) {
                        Logging::warn('Landing page background rejected: ' . $e->getMessage());
                    }
                }

                // RASTATIME 2026-09-28 - Live Text Info
                Application_Model_Preference::setLiveTextEnabled(!empty($values['enable_live_text']));
                Application_Model_Preference::setLiveTextFormat($values['live_text_format'] ?? 0);
                Application_Model_Preference::setLiveTextWebEnabled(!empty($values['live_text_web_enabled']));
                Application_Model_Preference::setLiveTextFilePath($values['live_text_file_path'] ?? '');
                $liveTextFtp = Application_Model_Preference::getLiveTextFtpConfig();
                $liveTextFtp['enabled'] = !empty($values['live_text_ftp_enabled']);
                $liveTextFtp['protocol'] = in_array($values['live_text_ftp_protocol'] ?? 'ftp', ['ftp', 'ftps', 'sftp'], true)
                    ? $values['live_text_ftp_protocol'] : 'ftp';
                $liveTextFtp['host'] = trim((string) ($values['live_text_ftp_host'] ?? ''));
                $liveTextFtp['port'] = trim((string) ($values['live_text_ftp_port'] ?? ''));
                $liveTextFtp['username'] = trim((string) ($values['live_text_ftp_username'] ?? ''));
                if (($values['live_text_ftp_password'] ?? '') !== '') {
                    $liveTextFtp['password'] = (string) $values['live_text_ftp_password'];
                }
                $liveTextFtp['path'] = trim((string) ($values['live_text_ftp_path'] ?? '')) ?: '/';
                Application_Model_Preference::setLiveTextFtpConfig($liveTextFtp);

                Application_Model_Preference::setTuneinEnabled($values['enable_tunein']);
                Application_Model_Preference::setTuneinStationId($values['tunein_station_id']);
                Application_Model_Preference::setTuneinPartnerKey($values['tunein_partner_key']);
                Application_Model_Preference::setTuneinPartnerId($values['tunein_partner_id']);

                $this->view->statusMsg = "<div class='success'>" . _('Preferences updated.') . '</div>';
                $form = new Application_Form_Preferences();
                $this->view->form = $form;
            // $this->_helper->json->sendJson(array("valid"=>"true", "html"=>$this->view->render('preference/index.phtml')));
            } else {
                $this->view->form = $form;
                // $this->_helper->json->sendJson(array("valid"=>"false", "html"=>$this->view->render('preference/index.phtml')));
            }
        }
        $this->view->logoImg = Application_Model_Preference::GetStationLogo();
        $this->view->landingBackgroundUrl = Application_Model_Preference::GetLandingBackgroundUrl();
        $this->view->faviconImg = Application_Model_Preference::GetStationFaviconHref();

        $this->view->form = $form;
    }

    public function stationPodcastSettingsAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $values = json_decode($this->getRequest()->getRawBody());

        if (!Application_Model_Preference::getStationPodcastPrivacy() && $values->stationPodcastPrivacy == 1) {
            // Refresh the download key when enabling privacy
            Application_Model_Preference::setStationPodcastDownloadKey();
        }

        // Append sharing token (download key) to Station podcast URL
        $stationPodcast = PodcastQuery::create()->findOneByDbId(Application_Model_Preference::getStationPodcastId());
        $key = Application_Model_Preference::getStationPodcastDownloadKey();
        $url = Config::getPublicUrl() .
            (((int) $values->stationPodcastPrivacy) ? "feeds/station-rss?sharing_token={$key}" : 'feeds/station-rss');
        $stationPodcast->setDbUrl($url)->save();
        Application_Model_Preference::setStationPodcastPrivacy($values->stationPodcastPrivacy);

        $this->_helper->json->sendJson(['url' => $url]);
    }

    public function directoryConfigAction() {}

    public function removeLogoAction()
    {
        SessionHelper::reopenSessionForWriting();

        $this->view->layout()->disableLayout();
        // Remove reliance on .phtml files to render requests
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => false, 'error' => 'CSRF token did not match.']);

            return;
        }

        Application_Model_Preference::SetStationLogo('');
    }

    /** RASTATIME 2026-10-07 - counterpart to removeLogoAction for the landing page background. */
    public function removeLandingBackgroundAction()
    {
        SessionHelper::reopenSessionForWriting();

        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => false, 'error' => 'CSRF token did not match.']);

            return;
        }

        Application_Model_Preference::RemoveLandingBackground();
    }

    /**
     * RASTATIME 2026-09-28 - EBU R128 stage 1: how many playable library
     * files carry a loudness measurement.  Returns [measured, total].
     */
    private static function loudnessMeasurementStats()
    {
        try {
            $con = Propel::getConnection();
            $stmt = $con->query(
                'SELECT COUNT(*) FILTER (WHERE loudness_lufs IS NOT NULL) AS measured, COUNT(*) AS total '
                . 'FROM cc_files WHERE file_exists = true AND import_status = 0'
            );
            $row = $stmt->fetch(PDO::FETCH_ASSOC);

            return [(int) ($row['measured'] ?? 0), (int) ($row['total'] ?? 0)];
        } catch (Exception $e) {
            Logging::warn('loudnessMeasurementStats: ' . $e->getMessage());

            return [0, 0];
        }
    }

    /**
     * RASTATIME 2026-09-28 - EBU R128 stage 1: queue the library for the
     * analyzer's loudness measurement (POST, CSRF).  Without force only
     * files that have no measurement yet; with force=1 every file.
     * Answers {"queued": N}.
     */
    public function remeasureLoudnessAction()
    {
        SessionHelper::reopenSessionForWriting();

        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => false, 'error' => 'CSRF token did not match.']);

            return;
        }

        $force = (string) $this->_getParam('force', '0') === '1';
        $con = Propel::getConnection();
        $sql = 'SELECT id FROM cc_files WHERE file_exists = true AND import_status = 0'
            . ($force ? '' : ' AND loudness_lufs IS NULL')
            . ' ORDER BY id';
        $ids = $con->query($sql)->fetchAll(PDO::FETCH_COLUMN, 0);

        $queued = 0;
        foreach ($ids as $id) {
            $file = CcFilesQuery::create()->findPk((int) $id);
            if (!$file) {
                continue;
            }
            $path = $file->getAbsoluteFilePath();
            if (!is_file($path)) {
                continue;
            }
            try {
                Application_Model_RabbitMq::SendLoudnessMeasurementToAnalyzer((int) $id, $path);
                ++$queued;
            } catch (Exception $e) {
                Logging::error('remeasureLoudness: file ' . $id . ': ' . $e->getMessage());
                break;
            }
        }
        Logging::info('Loudness measurement queued for ' . $queued . ' file(s)' . ($force ? ' (force)' : ''));

        $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => true, 'queued' => $queued]);
    }

    // RASTATIME 2026-05-15 - Counterpart to removeLogoAction for the favicon.
    public function removeFaviconAction()
    {
        SessionHelper::reopenSessionForWriting();

        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => false, 'error' => 'CSRF token did not match.']);

            return;
        }

        Application_Model_Preference::SetStationFavicon('');
    }

    /**
     * POST /preference/ftp-import-save - RASTATIME 2026-09-17.
     *
     * Saves the "Import from FTP Server" configuration.  An empty
     * password field keeps the stored password; the password is never
     * echoed back.
     */
    public function ftpImportSaveAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $old = Application_Model_Preference::getFtpImportConfig();
        $protocol = strtolower(trim((string) $this->_getParam('protocol', 'ftp')));
        if (!in_array($protocol, FtpImportScanTask::PROTOCOLS, true)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Unknown protocol.']);
            return;
        }
        $port = trim((string) $this->_getParam('port', ''));
        if ($port !== '' && (!ctype_digit($port) || (int) $port < 1 || (int) $port > 65535)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Port must be a number (1-65535).']);
            return;
        }
        $password = (string) $this->_getParam('password', '');
        $config = [
            'enabled'  => $this->_getParam('enabled', '') === 'true',
            'protocol' => $protocol,
            'host'     => trim((string) $this->_getParam('host', '')),
            'port'     => $port,
            'username' => trim((string) $this->_getParam('username', '')),
            'password' => $password !== '' ? $password : (string) $old['password'],
            'path'     => trim((string) $this->_getParam('path', '/')),
        ];
        if ($config['enabled'] && $config['host'] === '') {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Enter a server host name.']);
            return;
        }
        Application_Model_Preference::setFtpImportConfig($config);
        Logging::info('FTP import config saved: ' . ($config['enabled'] ? 'enabled' : 'disabled')
            . ' ' . $config['protocol'] . '://' . $config['host'] . ' ' . $config['path']);
        $public = $config;
        unset($public['password']);
        $public['has_password'] = $config['password'] !== '';
        $this->_helper->json->sendJson(['ok' => true, 'config' => $public]);
    }

    /**
     * POST /preference/ftp-import-fetch-now - RASTATIME 2026-09-17.
     * Same code path as the 5-minute task, without the throttle.
     */
    public function ftpImportFetchNowAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        set_time_limit(330);
        $result = FtpImportScanTask::fetchOnce();
        $this->_helper->json->sendJson([
            'ok' => !isset($result['error']),
            'result' => array_diff_key($result, ['log' => 1]),
            'status' => Application_Model_Preference::getFtpImportLastStatus(),
        ]);
    }

    // ------------------------------------------------------------------
    // RASTATIME 2026-09-16 - Media Library Location (stage 2).  The page
    // talks to these actions (operator login + CSRF); they proxy to the
    // API on localhost with the API key, which never reaches the browser.
    // ------------------------------------------------------------------

    private const RASTATIME_API_BASE = 'http://127.0.0.1:8765/';

    private function storageApi(string $method, string $path, ?array $body = null): array
    {
        $headers = [
            'Authorization: Api-Key ' . (string) Config::get('general.api_key'),
            'Accept: application/json',
        ];
        $opts = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 20,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_CUSTOMREQUEST  => $method,
        ];
        if ($body !== null) {
            $opts[CURLOPT_POSTFIELDS] = json_encode($body);
            $headers[] = 'Content-Type: application/json';
        }
        $opts[CURLOPT_HTTPHEADER] = $headers;
        $curl = curl_init(self::RASTATIME_API_BASE . $path);
        curl_setopt_array($curl, $opts);
        $resp   = curl_exec($curl);
        $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $errno  = curl_errno($curl);
        curl_close($curl);
        $data = is_string($resp) ? (json_decode($resp, true) ?: []) : [];
        if ($status === 0) {
            // RASTATIME 2026-10-28 - a timeout is not "unreachable": the
            // API may still be working on the request (the backup start
            // used to walk a USB mirror for minutes), so say so and let the
            // status poll show what happened.
            if ($errno === CURLE_OPERATION_TIMEDOUT) {
                $status = 504;
                $data = ['errors' => ['The RASTATIME API did not answer within 20 seconds. It may still be working on the request - the status below refreshes in a moment.']];
            } else {
                $status = 502;
                $data = ['errors' => ['The RASTATIME API is not reachable.']];
            }
        }
        return [$status, $data];
    }

    private function storageReply(int $status, array $data): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $this->getResponse()->setHttpResponseCode($status);
        $this->_helper->json->sendJson($data);
    }

    /**
     * RASTATIME 2026-10-25 (role audit S4) - Settings -> Local Machine,
     * sound-card section: the device list and the sound-card setting go
     * through these actions (Admin, CSRF on save) instead of the browser
     * calling /api/v2/audio/... directly; those Django views answer
     * internal callers only now.
     */
    public function audioDevicesAction(): void
    {
        [$status, $data] = $this->storageApi('GET', 'api/v2/audio/devices');
        $this->storageReply($status, $data);
    }

    public function soundcardSettingsAction(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'GET') {
            [$status, $data] = $this->storageApi('GET', 'api/v2/audio/soundcard-settings');
            $this->storageReply($status, $data);

            return;
        }
        if (!$this->storageGuardPost()) {
            return;
        }
        $id = (string) $this->_getParam('main_output_id', '');
        [$status, $data] = $this->storageApi('POST', 'api/v2/audio/soundcard-settings', [
            'main_output_id' => $id === '' ? null : $id,
            'main_output_name' => (string) $this->_getParam('main_output_name', ''),
        ]);
        $this->storageReply($status, $data);
    }

    private function storageGuardPost(): bool
    {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->storageReply(405, ['errors' => ['method-not-allowed']]);
            return false;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->storageReply(403, ['errors' => ['CSRF token did not match.']]);
            return false;
        }
        return true;
    }

    /** GET /preference/storage-location-status */
    public function storageLocationStatusAction(): void
    {
        [$status, $data] = $this->storageApi('GET', 'api/v2/storage/location');
        $this->storageReply($status, $data);
    }

    /** POST /preference/storage-location-validate  folder=... */
    public function storageLocationValidateAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        $folder = trim((string) $this->_getParam('folder', ''));
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/move/validate', ['path' => $folder]);
        $this->storageReply($status, $data);
    }

    /** POST /preference/storage-location-move  folder=...  (starts or resumes the copy) */
    public function storageLocationMoveAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        $folder = trim((string) $this->_getParam('folder', ''));
        Logging::info('Operator started a media library move to ' . $folder);
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/move/start', ['path' => $folder]);
        $this->storageReply($status, $data);
    }

    /** POST /preference/storage-location-cancel */
    public function storageLocationCancelAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        Logging::info('Operator cancelled the media library move');
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/move/cancel');
        $this->storageReply($status, $data);
    }

    // ------------------------------------------------------------------
    // RASTATIME 2026-09-16 - Settings -> Backup (work-order point 10,
    // stage 1).  The page and its proxies follow the Media Library
    // Location pattern above: operator login + CSRF here, API key only
    // server-side.  The backup job itself runs in the API process.
    // ------------------------------------------------------------------

    /** GET /preference/backup - the Settings -> Backup page. */
    public function backupAction(): void
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        // RASTATIME 2026-10-27 - one Save for both sections
        $this->view->headScript()->appendFile(Assets::url('js/airtime/preferences/pagesave.js'), 'text/javascript');
    }

    /** GET /preference/backup-status */
    public function backupStatusAction(): void
    {
        [$status, $data] = $this->storageApi('GET', 'api/v2/storage/backup');
        $this->storageReply($status, $data);
    }

    /** POST /preference/backup-validate  folder=... */
    public function backupValidateAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        $folder = trim((string) $this->_getParam('folder', ''));
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/backup/validate', ['path' => $folder]);
        $this->storageReply($status, $data);
    }

    /** POST /preference/backup-folder  folder=...  (validates, then saves the setting) */
    public function backupFolderAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        $folder = trim((string) $this->_getParam('folder', ''));
        // RASTATIME 2026-09-17 - stage 2 bugfix: the page sends the
        // "Include media library" checkbox, but this proxy dropped it -
        // the API never saw include_media and the mirror never ran.
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/backup/folder', [
            'path' => $folder,
            'include_media' => $this->_getParam('include_media', 'false') === 'true',
        ]);
        $this->storageReply($status, $data);
    }

    /** POST /preference/backup-run */
    public function backupRunAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        Logging::info('Operator started a manual backup');
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/backup/run');
        $this->storageReply($status, $data);
    }

    /** POST /preference/backup-auto  enabled=...&every_days=...&retention_days=... */
    public function backupAutoAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/backup/auto', [
            'enabled' => $this->_getParam('enabled', 'false') === 'true',
            'every_days' => (int) $this->_getParam('every_days', 1),
            'retention_days' => (int) $this->_getParam('retention_days', 0),
        ]);
        $this->storageReply($status, $data);
    }

    /** POST /preference/backup-cancel  (stops the media mirror; the ZIP finishes) */
    public function backupCancelAction(): void
    {
        if (!$this->storageGuardPost()) {
            return;
        }
        Logging::info('Operator cancelled the running backup');
        [$status, $data] = $this->storageApi('POST', 'api/v2/storage/backup/cancel');
        $this->storageReply($status, $data);
    }

    /**
     * GET /preference/backup-download?name=rastatime-backup-....zip
     *
     * Streams the ZIP through PHP so the API key never reaches the
     * browser.  Stage-1 backups (database + config) are megabytes, so
     * buffering the body is fine; media backups (stage 2) stay on the
     * server and never travel this way.
     */
    public function backupDownloadAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $resp = $this->getResponse();
        $name = (string) $this->_getParam('name', '');
        if (!preg_match('/^rastatime-backup-[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{4}(-[0-9]+)?\.zip$/', $name)) {
            $resp->setHttpResponseCode(400)->setBody('Bad backup name.');
            return;
        }
        $curl = curl_init(self::RASTATIME_API_BASE
            . 'api/v2/storage/backup/download?name=' . rawurlencode($name));
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 300,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_HTTPHEADER     => [
                'Authorization: Api-Key ' . (string) Config::get('general.api_key'),
            ],
        ]);
        $body   = curl_exec($curl);
        $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);
        if ($status !== 200 || !is_string($body)) {
            $resp->setHttpResponseCode($status === 0 ? 502 : $status)->setBody('Download failed.');
            return;
        }
        $resp->setHeader('Content-Type', 'application/zip', true)
            ->setHeader('Content-Disposition', 'attachment; filename="' . $name . '"', true)
            ->setHeader('Content-Length', (string) strlen($body), true)
            ->setBody($body);
    }

    /**
     * RASTATIME 2026-05-16 - Save the Local Import Folder path.
     *
     * Settings -> Local Machine -> Import Folder section.  Stores
     * cc_pref.local_import_folder (string).  Empty value disables
     * the LocalImportScanTask.
     */
    public function localImportSaveAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        $folder = trim((string) $this->_getParam('folder', ''));

        // Non-empty: validate that the path exists, is a directory, and
        // is writable (files are moved out of it after the import, a failed
        // one into its _failed subfolder).  Empty value is allowed and
        // disables the scan.
        if ($folder !== '') {
            if (!is_dir($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Path is not a directory or not accessible: ' . $folder,
                ]);
                return;
            }
            if (!is_writable($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Folder is not writable (needed to move source files out of it after import): ' . $folder,
                ]);
                return;
            }
        }

        Application_Model_Preference::setLocalImportFolder($folder);
        Logging::info('Local Import Folder set to: ' . ($folder === '' ? '(disabled)' : $folder));
        $this->_helper->json->sendJson(['ok' => true, 'folder' => $folder]);
    }

    /**
     * RASTATIME 2026-05-16 - Trigger an immediate scan of the Local Import Folder.
     *
     * Same code path as the LocalImportScanTask, but bypasses the
     * 5-minute throttle so the operator can verify a new folder
     * configuration immediately.  Reuses LocalImportScanTask::scanOnce
     * so the two entry points cannot drift.
     */
    /**
     * RASTATIME 2026-10-09 - current import-folder scan state for the
     * settings page, which polls it so "Last scan" never goes stale.
     */
    public function localImportStatusAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $lastRun = (int) Application_Model_Preference::getLocalImportLastRun();
        $this->_helper->json->sendJson([
            'ok' => true,
            'last_run' => $lastRun > 0 ? date('Y-m-d H:i:s', $lastRun) : '',
            'age_seconds' => $lastRun > 0 ? max(0, time() - $lastRun) : null,
            'status' => (string) Application_Model_Preference::getLocalImportLastStatus(),
            'folder' => (string) Application_Model_Preference::getLocalImportFolder(),
        ]);
    }

    public function localImportScanNowAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        $folder = Application_Model_Preference::getLocalImportFolder();
        if (empty($folder)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'No import folder configured.']);
            return;
        }

        // RASTATIME 2026-05-16 - The non-Application_*-prefixed classes
        // in TaskManager.php (LocalImportScanTask, TrackExpiryTask, etc.)
        // are not discoverable by the Zend autoloader because their
        // class names do not follow the PSR-0 mapping convention.  We
        // require_once the file explicitly so the LocalImportScanTask
        // class is loaded before we reach for it.  The same
        // require_once is implicitly performed by PageLayoutInitPlugin
        // when it instantiates TaskManager::getInstance() on every
        // page-rendering request, but this AJAX endpoint bypasses the
        // plugin in fast-render mode.
        require_once APPLICATION_PATH . '/common/TaskManager.php';

        try {
            $result = LocalImportScanTask::scanOnce($folder);
        } catch (Exception $exc) {
            Logging::error('localImportScanNow: ' . $exc->getMessage());
            $this->_helper->json->sendJson([
                'ok' => false,
                'error' => 'Scan failed: ' . $exc->getMessage(),
            ]);
            return;
        }
        $this->_helper->json->sendJson(array_merge(['ok' => true], $result));
    }

    /**
     * RASTATIME 2026-05-17 - Save the Local Recording Folder path.
     *
     * Section 23.13.  Per-show recording reads this folder via
     * GET /api/v2/preferences/local-recording-folder.  Empty value
     * disables recording (shows flagged "Record this show" play
     * normally, only the recording is skipped).
     */
    public function localRecordingSaveAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        $folder = trim((string) $this->_getParam('folder', ''));
        // RASTATIME 2026-10-18 - encoder choice (format + bitrate)
        $format = strtolower(trim((string) $this->_getParam('format', 'mp3')));
        $bitrate = (int) $this->_getParam('bitrate', 320);
        if (!in_array($format, ['mp3', 'aac', 'ogg', 'opus'], true)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Unsupported format: ' . $format]);

            return;
        }
        if (!in_array($bitrate, [96, 128, 192, 256, 320], true)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Unsupported bitrate: ' . $bitrate]);

            return;
        }

        // Non-empty: validate existence + writability (the playout
        // creates per-day subfolders and writes the recordings into them).
        if ($folder !== '') {
            if (!is_dir($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Path is not a directory or not accessible: ' . $folder,
                ]);
                return;
            }
            if (!is_writable($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Folder is not writable: ' . $folder,
                ]);
                return;
            }
        }

        // RASTATIME 2026-10-19 - copy finished recordings into the library
        $copyToLibrary = in_array(strtolower(trim((string) $this->_getParam('copy_to_library', 'false'))), ['true', '1', 'on', 'yes'], true);
        Application_Model_Preference::setLocalRecordingFolder($folder);
        Application_Model_Preference::setLocalRecordingFormat($format);
        Application_Model_Preference::setLocalRecordingBitrate($bitrate);
        Application_Model_Preference::setLocalRecordingCopyToLibrary($copyToLibrary);
        Logging::info('Local Recording Folder set to: ' . ($folder === '' ? '(disabled)' : $folder)
            . ", format {$format} {$bitrate}k, copy to library " . ($copyToLibrary ? 'on' : 'off'));
        $this->_helper->json->sendJson([
            'ok' => true,
            'folder' => $folder,
            'format' => $format,
            'bitrate' => $bitrate,
            'copy_to_library' => $copyToLibrary,
        ]);
    }

    /**
     * RASTATIME 2026-06-05 - Save the 24/7 hourly archive recording config.
     *
     * Settings -> Local Machine -> "24/7 Recording".  Stores the cc_pref
     * keys local_247_recording_{enabled,folder,format,bitrate,retention_days}
     * that the playout render (rastatime_playout) reads at startup and the
     * retention task consults.  Changing these needs a RASTATIME-PLAYOUT
     * restart to re-render the .liq (same as a stream-output change).
     */
    public function local247RecordingSaveAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }

        $enabled = ($this->_getParam('enabled', 'false') === 'true');
        $folder = trim((string) $this->_getParam('folder', ''));
        $format = strtolower(trim((string) $this->_getParam('format', 'mp3')));
        $bitrate = (int) $this->_getParam('bitrate', 192);
        $retention = (int) $this->_getParam('retention_days', 0);

        if (!in_array($format, ['mp3', 'aac', 'ogg', 'opus'], true)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Invalid format: ' . $format]);
            return;
        }
        if ($bitrate < 32 || $bitrate > 320) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'Bitrate must be between 32 and 320 kbps.']);
            return;
        }
        if ($retention < 0) {
            $retention = 0;
        }

        // A non-empty recording OUTPUT folder is created on demand (unlike
        // the import drop-folder) so the operator can point anywhere
        // writable, inside or outside the project tree.  Enabling without a
        // folder is an error.
        if ($folder !== '') {
            if (!is_dir($folder) && !@mkdir($folder, 0777, true) && !is_dir($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Folder does not exist and could not be created (check the path, and that the web/playout service may write there): ' . $folder,
                ]);
                return;
            }
            if (!is_writable($folder)) {
                $this->_helper->json->sendJson([
                    'ok' => false,
                    'error' => 'Folder is not writable: ' . $folder,
                ]);
                return;
            }
        } elseif ($enabled) {
            $this->_helper->json->sendJson([
                'ok' => false,
                'error' => 'A folder is required when 24/7 recording is enabled.',
            ]);
            return;
        }

        Application_Model_Preference::setLocal247RecordingEnabled($enabled);
        Application_Model_Preference::setLocal247RecordingFolder($folder);
        Application_Model_Preference::setLocal247RecordingFormat($format);
        Application_Model_Preference::setLocal247RecordingBitrate($bitrate);
        Application_Model_Preference::setLocal247RecordingRetentionDays($retention);

        Logging::info(sprintf(
            '24/7 Recording config saved: enabled=%s folder=%s format=%s bitrate=%dk retention=%dd',
            $enabled ? '1' : '0',
            $folder === '' ? '(none)' : $folder,
            $format,
            $bitrate,
            $retention
        ));

        $this->_helper->json->sendJson([
            'ok' => true,
            'enabled' => $enabled,
            'folder' => $folder,
            'format' => $format,
            'bitrate' => $bitrate,
            'retention_days' => $retention,
            'restart_required' => true,
        ]);
    }

    public function streamSettingAction()
    {
        $request = $this->getRequest();

        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        $this->view->headScript()->appendFile(Assets::url('js/airtime/preferences/streamsetting.js'), 'text/javascript');

        SessionHelper::reopenSessionForWriting();

        $name_map = [
            'ogg' => 'Ogg Vorbis',
            'fdkaac' => 'AAC+',
            'aac' => 'AAC',
            'opus' => 'Opus',
            'mp3' => 'MP3',
        ];

        // RASTATIME: always show 3 Icecast output stream slots regardless of
        // YAML config (which may be empty when no streams are configured yet).
        $num_of_stream = 3;
        $form = new Application_Form_StreamSetting();

        $csrf_namespace = new Zend_Session_Namespace('csrf_namespace');
        $csrf_element = new Zend_Form_Element_Hidden('csrf');
        $csrf_element->setValue($csrf_namespace->authtoken)->setRequired('true')->removeDecorator('HtmlTag')->removeDecorator('Label');
        $form->addElement($csrf_element);

        $live_stream_subform = new Application_Form_LiveStreamingPreferences();
        $form->addSubForm($live_stream_subform, 'live_stream_subform');

        // get current settings
        $setting = Application_Model_StreamSetting::getStreamSetting();
        $form->setSetting($setting);

        if ($num_of_stream > MAX_NUM_STREAMS) {
            Logging::error('Your streams count (' . $num_of_stream . ') exceed the maximum, some of them will not be displayed');
            $num_of_stream = MAX_NUM_STREAMS;
        }

        for ($i = 1; $i <= $num_of_stream; ++$i) {
            $subform = new Application_Form_StreamSettingSubForm();
            $subform->setPrefix($i);
            $subform->setSetting($setting);
            $subform->startForm();
            $form->addSubForm($subform, 's' . $i . '_subform');
        }

        $live_stream_subform->updateVariables();
        // RASTATIME 2026-09-28 - "Measured: N of M files" for the EBU R128 block
        $form->setLoudnessStats(...self::loudnessMeasurementStats());
        $form->startFrom();

        if ($request->isPost()) {
            $params = $request->getPost();
            /* Parse through post data and put in format
             * $form->isValid() is expecting it in
             */
            $postData = explode('&', $params['data']);
            $values = [];

            foreach ($postData as $k => $v) {
                $v = explode('=', urldecode($v));
                $values[$v[0]] = $v[1];
            }

            // RASTATIME 2026-11-02 - an enabled stream needs a mount point, a
            // valid port and a source password (posted or already stored);
            // Liquidsoap otherwise connects to mount "/" without a password
            // and gets 401 forever while the status box still says "Icecast is
            // running" (install rehearsal).  Nothing is saved on a violation.
            $streamErrors = $this->validateEnabledStreams($values);
            $formValid = $form->isValid($values);

            if ($formValid && !empty($streamErrors)) {
                $items = '';
                foreach ($streamErrors as $error) {
                    $items .= '<li>' . htmlspecialchars($error, ENT_QUOTES) . '</li>';
                }
                $this->view->statusMsg = "<div class='errors' style='height: auto'><ul style='margin: 4px 0; list-style: none'>" . $items . '</ul></div>';
            }

            if ($formValid && empty($streamErrors)) {
                // this goes into cc_pref table
                $this->setStreamPreferences($values);

                // compare new values with current value
                // RASTATIME 2026-09-28 - Loudness Normalization: mode + target +
                // ceiling next to the ReplayGain modifier; any change re-fills
                // the schedule (the gain per track is computed there).
                $newMode = $values['loudnessMode'] ?? Application_Model_Preference::getLoudnessMode();
                $newTarget = $values['loudnessTarget'] ?? Application_Model_Preference::getLoudnessTargetLufs();
                $newTruePeak = $values['loudnessTruePeak'] ?? Application_Model_Preference::getLoudnessTruePeakDbtp();
                $changeRGenabled = Application_Model_Preference::getLoudnessMode() != $newMode;
                $changeRGmodifier = Application_Model_Preference::getReplayGainModifier() != $values['replayGainModifier']
                    || (float) Application_Model_Preference::getLoudnessTargetLufs() != (float) $newTarget
                    || (float) Application_Model_Preference::getLoudnessTruePeakDbtp() != (float) $newTruePeak;
                if ($changeRGenabled || $changeRGmodifier) {
                    Application_Model_Preference::setLoudnessMode($newMode);
                    Application_Model_Preference::setLoudnessTargetLufs($newTarget);
                    Application_Model_Preference::setLoudnessTruePeakDbtp($newTruePeak);
                    Application_Model_Preference::setReplayGainModifier($values['replayGainModifier']);
                    // The side effects of this function are still required to fill the schedule, we
                    // don't use the returned schedule.
                    Application_Model_Schedule::getSchedule();
                    Application_Model_RabbitMq::SendMessageToPypo('update_schedule', []);
                    // Application_Model_RabbitMq::PushSchedule();
                }

                // RASTATIME 2026-10-02 - Output Processing (Stereo Tool).  The
                // playout's settings fingerprint picks the change up and applies
                // it with a planned Liquidsoap restart.  The licence key: blank
                // keeps the stored key, CLEAR removes it; it is never logged.
                $stEnabled = ($values['stereotoolEnabled'] ?? '0');
                Application_Model_Preference::setStereoToolEnabled($stEnabled === '1' || $stEnabled === 'true');
                Application_Model_Preference::setStereoToolLibrary($values['stereotoolLibrary'] ?? '');
                Application_Model_Preference::setStereoToolPreset($values['stereotoolPreset'] ?? '');
                $stKey = trim((string) ($values['stereotoolLicenseKey'] ?? ''));
                if (strcasecmp($stKey, 'CLEAR') === 0) {
                    Application_Model_Preference::setStereoToolLicenseKey('');
                } elseif ($stKey !== '') {
                    Application_Model_Preference::setStereoToolLicenseKey($stKey);
                }

                // store stream update timestamp
                Application_Model_Preference::SetStreamUpdateTimestamp();
                // RASTATIME 2026-11-02 - a stale Liquidsoap connection error must
                // not outlive the configuration it belonged to.
                Application_Model_Preference::clearLiquidsoapErrors();

                $this->view->statusMsg = "<div class='success'>" . _('Stream Setting Updated.') . '</div>';
            }
        }

        $this->view->num_stream = $num_of_stream;
        $this->view->enable_stream_conf = Application_Model_Preference::GetEnableStreamConf();
        $this->view->form = $form;

        if ($request->isPost()) {
            // RASTATIME 2026-11-02 - real booleans: streamsetting.js reloaded the
            // page on the string 'false' too (truthy), so an error message never
            // stayed on screen.
            $this->_helper->json->sendJson([
                'valid' => $formValid && empty($streamErrors),
                'html' => $this->view->render('preference/stream-setting.phtml'),
            ]);
        }
    }

    /**
     * RASTATIME 2026-11-02 - plausibility of the enabled output streams
     * before anything is saved (see streamSettingAction).
     *
     * @param array $values the flattened POST values (s{N}_data[field] => value)
     *
     * @return string[] one translated message per problem, empty when all is well
     */
    private function validateEnabledStreams(array $values): array
    {
        $errors = [];
        for ($i = 1; $i <= 3; ++$i) {
            $ns = "s{$i}_data";
            $rawEnable = $values["{$ns}[enable]"] ?? '0';
            if ($rawEnable !== '1' && $rawEnable !== 'true') {
                continue;
            }

            $mount = ltrim(trim((string) ($values["{$ns}[mount]"] ?? '')), '/');
            if ($mount === '') {
                $errors[] = sprintf(_('Stream %d: mount point is required when the stream is enabled.'), $i);
            }

            $port = trim((string) ($values["{$ns}[port]"] ?? '8000'));
            if (!ctype_digit($port) || (int) $port < 1 || (int) $port > 65535) {
                $errors[] = sprintf(_('Stream %d: port must be a number between 1 and 65535.'), $i);
            }

            // A blank password field keeps the stored one (setStreamPreferences).
            $pass = (string) ($values["{$ns}[pass]"] ?? '');
            if ($pass === '') {
                $existing = Application_Model_Preference::GetStreamOutput($i);
                $pass = (string) ($existing['pass'] ?? '');
            }
            if ($pass === '') {
                $errors[] = sprintf(_('Stream %d: source password is required when the stream is enabled.'), $i);
            }
        }

        return $errors;
    }

    /**
     * RASTATIME 2026-05-16 - Renamed from soundcardSettingAction.
     * The page now covers both audio devices (T13.2 / T13.3) AND the
     * Local Import Folder feature (Section 23.12).  URL is
     * /preference/local-machine.  View script renamed in lockstep to
     * views/scripts/preference/local-machine.phtml.
     *
     * Device inventory is fetched client-side from
     * GET /api/v2/audio/devices; saved soundcard settings via
     * GET|POST /api/v2/audio/soundcard-settings.  Import-folder
     * config goes through localImportSaveAction below.
     */
    public function localMachineAction(): void
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        // RASTATIME 2026-10-27 - one Save for every section; loaded first,
        // soundcardsetting.js registers the Soundcard section with it
        $this->view->headScript()->appendFile(Assets::url('js/airtime/preferences/pagesave.js'), 'text/javascript');
        $this->view->headScript()->appendFile(
            Assets::url('js/airtime/preferences/soundcardsetting.js'),
            'text/javascript'
        );
        // RASTATIME 2026-09-17 — the Line-In sources section (and its
        // linein.js) left this page; the Library dialog is the one
        // line-in editor now.

        // RASTATIME 2026-10-14 — Import Format section (lossless -> MP3
        // 320 kbps); saved through importFormatSaveAction.
        $this->view->convertLosslessToMp3 = Application_Model_Preference::getConvertLosslessToMp3();
    }

    /**
     * POST /preference/import-format-save - RASTATIME 2026-10-14.
     *
     * Settings -> Local Machine -> Import Format: "Convert lossless audio
     * (WAV, FLAC, ...) to MP3 320 kbps on import" (cc_pref
     * convert_lossless_to_mp3, default on).  Takes effect with the next
     * import message (RabbitMq::SendMessageToAnalyzer) - no restart.
     */
    public function importFormatSaveAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $on = $this->_getParam('convert_lossless', '') === 'true';
        Application_Model_Preference::setConvertLosslessToMp3($on);
        Logging::info('Import format: lossless -> MP3 320 kbps conversion ' . ($on ? 'enabled' : 'disabled'));
        $this->_helper->json->sendJson([
            'ok' => true,
            'convert_lossless' => Application_Model_Preference::getConvertLosslessToMp3(),
        ]);
    }

    /**
     * POST /preference/bulk-import-save - RASTATIME 2026-10-16.
     *
     * Settings -> Local Machine -> Import Folder: "Bulk import: also import
     * files whose audio is already in the library" (cc_pref
     * bulk_import_allow_duplicates, default off).  The API management
     * command bulk_import reads it when --allow-duplicates is not given.
     */
    public function bulkImportSaveAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $on = $this->_getParam('allow_duplicates', '') === 'true';
        Application_Model_Preference::setBulkImportAllowDuplicates($on);
        Logging::info('Bulk import: duplicates (known md5) ' . ($on ? 'allowed' : 'skipped'));
        $this->_helper->json->sendJson([
            'ok' => true,
            'allow_duplicates' => Application_Model_Preference::getBulkImportAllowDuplicates(),
        ]);
    }

    /**
     * POST /preference/restart-audio-chain — apply a changed
     * "Main Output" selection by restarting the audio chain.
     *
     * RASTATIME 2026-09-03.  The Main-Output device is baked into
     * rastatime.liq by RASTATIME-PLAYOUT at startup and read by
     * RASTATIME-LIQUIDSOAP at *its* startup, so a device change needs
     * both services restarted, playout first (see
     * rastatime_restart_liquidsoap_chain() in check.php for the
     * ordering rationale).
     *
     * Deliberately NOT exposed on the Django API: that listener binds
     * 0.0.0.0:8765 without authentication, so a restart endpoint there
     * would let anyone on the LAN interrupt the broadcast.  Here it
     * sits behind the operator login plus a CSRF token.
     *
     * ON AIR IMPACT: a few seconds of stream interruption.  The UI
     * asks for confirmation before calling this.
     */
    public function restartAudioChainAction(): void
    {
        // Restarting two NSSM services takes ~25-30 s (playout, a pause
        // so it can re-render the .liq, then liquidsoap).  Make sure
        // neither PHP nor a default time limit aborts us halfway and
        // leaves the chain in a half-restarted state.
        @set_time_limit(180);

        SessionHelper::reopenSessionForWriting();

        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson([
                'valid' => false,
                'error' => _('CSRF token did not match.'),
            ]);

            return;
        }

        Logging::info(
            'Operator requested an audio-chain restart '
            . '(Settings -> Local Machine -> Main Output).'
        );

        $result = rastatime_restart_liquidsoap_chain();

        if ($result['ok']) {
            Logging::info('Audio-chain restart OK: ' . $result['detail']);
            $this->_helper->json->sendJson([
                'valid'   => true,
                'message' => _('Audio chain restarted — the Main Output setting is now active.'),
            ]);

            return;
        }

        Logging::error('Audio-chain restart FAILED: ' . $result['detail']);
        $this->_helper->json->sendJson([
            'valid' => false,
            'error' => sprintf(
                // translators: %s is a technical status string
                _('Restart failed: %s'),
                $result['detail']
            ),
        ]);
    }

    /**
     * Set stream settings preferences.
     *
     * @param array $values stream setting preference values
     */
    private function setStreamPreferences($values)
    {
        Application_Model_Preference::setOffAirMeta($values['offAirMeta']);
        // RASTATIME 2026-11-02 - no radio checked (fresh database) means no key posted;
        // option 0 ("Artist - Title") is the default instead of an undefined-key 500.
        Application_Model_Preference::SetStreamLabelFormat($values['streamFormat'] ?? '0');
        Application_Model_Preference::SetLiveStreamMasterUsername($values['master_username']);
        Application_Model_Preference::SetLiveStreamMasterPassword($values['master_password']);
        Application_Model_Preference::SetDefaultTransitionFade($values['transition_fade']);
        // RASTATIME 2026-05-14 — auto_transition / auto_switch removed
        // from the Live Broadcasting form; see LiveStreamingPreferences
        // class for the architectural reason.

        // RASTATIME: persist Icecast output stream settings to cc_pref.
        // The form serialises each stream as s{N}_data[field]=value.
        for ($i = 1; $i <= 3; ++$i) {
            $ns = "s{$i}_data";   // e.g. "s1_data"

            // Load existing data so we can merge (avoids wiping unchanged fields)
            $existing = Application_Model_Preference::GetStreamOutput($i);

            // Zend_Form_Element_Checkbox always sends a hidden "0" field, so
            // isset() is always true.  Check the actual value instead.
            $rawEnable = $values["{$ns}[enable]"] ?? '0';
            $enabled = ($rawEnable === '1' || $rawEnable === 'true') ? 'true' : 'false';

            // Source password: keep existing value if field was left blank
            $pass = $values["{$ns}[pass]"] ?? '';
            if ($pass === '') {
                $pass = $existing['pass'] ?? '';
            }

            // Admin password: keep existing value if blank or "xxxxxx" placeholder
            $admin_pass = $values["{$ns}[admin_pass]"] ?? '';
            if ($admin_pass === '' || $admin_pass === 'xxxxxx') {
                $admin_pass = $existing['admin_pass'] ?? '';
            }

            $data = [
                'enable'      => $enabled,
                'output'      => 'icecast',
                'host'        => trim($values["{$ns}[host]"]        ?? 'localhost'),
                'port'        => trim($values["{$ns}[port]"]        ?? '8000'),
                'mount'       => trim($values["{$ns}[mount]"]       ?? ''),
                'user'        => trim($values["{$ns}[user]"]        ?? 'source'),
                'pass'        => $pass,
                'admin_user'  => trim($values["{$ns}[admin_user]"]  ?? 'admin'),
                'admin_pass'  => $admin_pass,
                'type'        => $values["{$ns}[type]"]             ?? 'mp3',
                'bitrate'     => $values["{$ns}[bitrate]"]          ?? '128',
                'channels'    => $values["{$ns}[channels]"]         ?? 'stereo',
                'samplerate'  => $values["{$ns}[samplerate]"]       ?? '44100',
                'name'        => trim($values["{$ns}[name]"]        ?? ''),
                'description' => trim($values["{$ns}[description]"] ?? ''),
                'genre'       => trim($values["{$ns}[genre]"]       ?? ''),
                'url'         => trim($values["{$ns}[url]"]         ?? ''),
                'mobile'      => (($values["{$ns}[mobile]"] ?? '0') === '1') ? 'true' : 'false',
            ];

            Application_Model_Preference::SetStreamOutput($i, $data);
        }
    }

    public function serverBrowseAction()
    {
        $request = $this->getRequest();
        $path = $request->getParam('path', null);

        $result = [];

        if (is_null($path)) {
            $element = [];
            $element['name'] = _('path should be specified');
            $element['isFolder'] = false;
            $element['isError'] = true;
            $result[$path] = $element;
        } else {
            $path .= '/';
            $handle = opendir($path);
            if ($handle !== false) {
                while (false !== ($file = readdir($handle))) {
                    if ($file != '.' && $file != '..') {
                        // only show directories that aren't private.
                        if (is_dir($path . $file) && substr($file, 0, 1) != '.') {
                            $element = [];
                            $element['name'] = $file;
                            $element['isFolder'] = true;
                            $element['isError'] = false;
                            $result[$file] = $element;
                        }
                    }
                }
            }
        }
        ksort($result);
        // returns format serverBrowse is looking for.
        $this->_helper->json->sendJson($result);
    }

    public function isImportInProgressAction()
    {
        $now = time();
        $res = false;
        if (Application_Model_Preference::GetImportTimestamp() + 10 > $now) {
            $res = true;
        }
        $this->_helper->json->sendJson($res);
    }

    public function getLiquidsoapStatusAction()
    {
        $out = [];
        // RASTATIME: check each stream slot by querying Icecast's status-json API.
        // Liquidsoap is not used; the VLC playout engine connects directly to Icecast.
        // Statuses:
        //   'N/A'      — stream disabled
        //   'OK'       — Icecast running AND mount point is active (VLC streaming)
        //   'inactive' — Icecast running but mount not yet active (nothing playing)
        //   'waiting'  — Icecast not reachable (service not started or wrong host/port)
        for ($i = 1; $i <= 3; ++$i) {
            if (!Application_Model_StreamSetting::getStreamEnabled($i)) {
                $status = 'N/A';
            } else {
                $pref  = Application_Model_Preference::GetStreamOutput($i);
                $host  = $pref['host']  ?? 'localhost';
                $port  = (int)($pref['port']  ?? 8000);
                $mount = '/' . ltrim($pref['mount'] ?? '', '/');

                // RASTATIME 2026-05-20 — Windows-portability fix.
                // On Windows the local resolver tries IPv6 (::1) first
                // for "localhost"; Icecast on this fork binds to IPv4
                // only, so the connect attempt sits for the full 2 s
                // timeout before falling back.  And the timeout itself
                // becomes a fatal because the global error handler
                // promotes file_get_contents' E_WARNING into an
                // ErrorException (which `@` does NOT suppress when a
                // set_error_handler is active).  Result pre-2026-05-20:
                // every "Streams" settings poll threw HTTP 500 and the
                // UI was stuck on "Getting information from the server".
                // Two-part fix:
                //  (a) rewrite "localhost" -> "127.0.0.1" so the
                //      resolver does not even try IPv6;
                //  (b) wrap file_get_contents in try/catch (Throwable)
                //      so a transient Icecast hiccup degrades to
                //      "waiting" instead of nuking the whole response.
                $queryHost = ($host === 'localhost') ? '127.0.0.1' : $host;
                $icecastUrl = "http://{$queryHost}:{$port}/status-json.xsl";
                $ctx  = stream_context_create(['http' => ['timeout' => 2, 'ignore_errors' => true]]);
                try {
                    $json = @file_get_contents($icecastUrl, false, $ctx);
                } catch (Throwable $e) {
                    $json = false;
                }

                if ($json !== false && strlen($json) > 0) {
                    $data    = @json_decode($json, true);
                    $sources = $data['icestats']['source'] ?? null;

                    if ($sources === null) {
                        // Icecast is up but no sources connected yet
                        $status = 'inactive';
                    } else {
                        // Normalize: single source is a dict, multiple is array of dicts.
                        // Detect single source: it has a first-level non-numeric key.
                        if (!isset($sources[0])) {
                            $sources = [$sources];
                        }
                        $mountFound = false;
                        foreach ((array)$sources as $source) {
                            // Icecast 2.4: uses 'mount' key directly.
                            // Icecast 2.5: 'mount' may be absent; derive from 'listenurl'.
                            $srcMount = $source['mount'] ?? '';
                            if ($srcMount === '') {
                                $listenUrl = $source['listenurl'] ?? '';
                                $srcMount  = (string)(parse_url($listenUrl, PHP_URL_PATH) ?? '');
                            }
                            if ($srcMount === $mount) {
                                $mountFound = true;
                                break;
                            }
                        }
                        $status = $mountFound ? 'OK' : 'inactive';
                    }
                } else {
                    // Icecast not reachable — service not running or wrong host/port
                    $status = 'waiting';
                }

                // RASTATIME 2026-11-02 - Icecast is up but the mount is missing:
                // if the playout reported why Liquidsoap cannot connect (e.g.
                // "Connection failed: 401, Authentication Required", posted to
                // api/update-liquidsoap-status), show that instead of the
                // misleading "start the playout" hint.  "OK" and '' mean no error.
                if ($status === 'inactive') {
                    $liqError = trim((string) Application_Model_Preference::getLiquidsoapError($i));
                    if ($liqError !== '' && $liqError !== 'OK') {
                        $status = $liqError;
                    }
                }
            }
            $out[] = ['id' => $i, 'status' => $status];
        }
        $this->_helper->json->sendJson($out);
    }

    public function getAdminPasswordStatusAction()
    {
        SessionHelper::reopenSessionForWriting();

        $out = [];
        // RASTATIME: always check 3 output stream slots
        for ($i = 1; $i <= 3; ++$i) {
            if (Application_Model_StreamSetting::getAdminPass('s' . $i) == '') {
                $out['s' . $i] = false;
            } else {
                $out['s' . $i] = true;
            }
        }
        $this->_helper->json->sendJson($out);
    }

    /**
     * RASTATIME 2026-10-14 - Dangerous Options > Clear Calendar: every
     * instance that has not started yet goes, with its content; the past
     * and the instance on air stay (ShowService::clearCalendarFromNow).
     */
    public function clearCalendarAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);
            return;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);
            return;
        }
        $user = Application_Model_User::getCurrentUser();
        if (!$user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN])) {
            $this->getResponse()->setHttpResponseCode(403);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'forbidden']);
            return;
        }

        Logging::info('clearCalendar: requested by ' . $user->getLogin());
        try {
            $service = new Application_Service_ShowService();
            $result = $service->clearCalendarFromNow();
        } catch (Exception $exc) {
            Logging::error('clearCalendar: ' . $exc->getMessage());
            $this->_helper->json->sendJson(['ok' => false, 'error' => $exc->getMessage()]);
            return;
        }
        $this->_helper->json->sendJson(array_merge(['ok' => true], $result));
    }

    public function deleteAllFilesAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            Logging::error(__FILE__ . ': Invalid CSRF token');
            $this->_helper->json->sendJson(['jsonrpc' => '2.0', 'valid' => false, 'error' => 'CSRF token did not match.']);

            return;
        }

        // Only admin users should get here through ACL permissioning
        // Only allow POST requests
        $method = $_SERVER['REQUEST_METHOD'];
        if (!($method == 'POST')) {
            $this->getResponse()
                ->setHttpResponseCode(405)
                ->appendBody(_('Request method not accepted') . ": {$method}");

            return;
        }

        $this->deleteFutureScheduleItems();
        $this->deleteStoredFiles();

        $this->getResponse()
            ->setHttpResponseCode(200)
            ->appendBody('OK');
    }

    private function deleteFutureScheduleItems()
    {
        $utcTimezone = new DateTimeZone('UTC');
        $nowDateTime = new DateTime('now', $utcTimezone);
        $scheduleItems = CcScheduleQuery::create()
            ->filterByDbEnds($nowDateTime->format(DEFAULT_TIMESTAMP_FORMAT), Criteria::GREATER_THAN)
            ->find();

        // Delete all the schedule items
        foreach ($scheduleItems as $i) {
            // If this is the currently playing track, cancel the current show
            if ($i->isCurrentItem()) {
                $instanceId = $i->getDbInstanceId();
                $instance = CcShowInstancesQuery::create()->findPk($instanceId);
                $showId = $instance->getDbShowId();

                // From ScheduleController
                $scheduler = new Application_Model_Scheduler();
                $scheduler->cancelShow($showId);
                Application_Model_StoredFile::updatePastFilesIsScheduled();
            }

            $i->delete();
        }
    }

    private function deleteStoredFiles()
    {
        // Delete all files from the database
        $files = CcFilesQuery::create()->find();
        foreach ($files as $file) {
            $storedFile = new Application_Model_StoredFile($file, null);
            // Delete the files quietly to avoid getting Sentry errors for
            // every S3 file we delete.
            $storedFile->delete(true);
        }
    }

    /**
     * RASTATIME 2026-05-19 — Show-Templates settings page
     * (Section 23.16).  Renders the list-of-templates UI; rename /
     * delete actions are JSON calls into the ScheduleController
     * endpoints already defined for the New-Show dialog.
     */
    public function showTemplatesAction()
    {
        // RASTATIME 2026-05-20 — parent_page assignment is what keeps
        // the Settings sub-navigation (General / My Profile / Users /
        // Track Types / Show Templates / Streams / Local Machine /
        // Status) visible in the left sidebar.  Without it the
        // sub-nav collapses when the operator opens Show Templates
        // — same call as streamSettingAction / localMachineAction.
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $this->view->templates = Application_Service_ShowTemplateService::getAllForListing();
    }

    /**
     * RASTATIME 2026-05-21 — Section 23.20.  Auto-DJ settings page.
     * Reads / persists the five cc_pref keys that
     * {@see Application_Service_AutoDjService} consumes.  Logo upload
     * goes through {@see autoDjUploadLogoAction()} via a separate
     * multipart POST (analogous to the show-image upload flow).
     */
    public function autoDjAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        $request = $this->getRequest();
        $msg = '';

        if ($request->isPost()) {
            $values = $request->getPost();
            try {
                Application_Model_Preference::SetAutoDjEnabled(
                    !empty($values['auto_dj_enabled'])
                );
                Application_Model_Preference::SetAutoDjShowName(
                    trim((string) ($values['auto_dj_show_name'] ?? ''))
                );
                $plId = $values['auto_dj_playlist_id'] ?? '';
                Application_Model_Preference::SetAutoDjPlaylistId(
                    $plId === '' ? null : (int) $plId
                );
                Application_Model_Preference::SetAutoDjFillAnyShow(
                    !empty($values['auto_dj_fill_any_show'])
                );
                // RASTATIME 2026-05-21 v2 — additional show-detail defaults
                Application_Model_Preference::SetAutoDjShowUrl(
                    trim((string) ($values['auto_dj_show_url'] ?? ''))
                );
                Application_Model_Preference::SetAutoDjShowGenre(
                    trim((string) ($values['auto_dj_show_genre'] ?? ''))
                );
                Application_Model_Preference::SetAutoDjShowDescription(
                    trim((string) ($values['auto_dj_show_description'] ?? ''))
                );
                // Colour fields are stored as 6-digit hex without #
                // (matches the Show form's add_show_background_color /
                // add_show_color conventions).  Strip a leading # and
                // truncate to 6 chars defensively.
                $bg = ltrim(trim((string) ($values['auto_dj_show_bg_color'] ?? '')), '#');
                $fg = ltrim(trim((string) ($values['auto_dj_show_text_color'] ?? '')), '#');
                Application_Model_Preference::SetAutoDjShowBgColor(substr($bg, 0, 6));
                Application_Model_Preference::SetAutoDjShowTextColor(substr($fg, 0, 6));
                $msg = 'Auto DJ settings saved.';
            } catch (Throwable $e) {
                Logging::warn('autoDjAction save failed: ' . $e->getMessage());
                $msg = 'Save failed: ' . $e->getMessage();
            }
        }

        // Build the playlist dropdown.  We deliberately list only
        // playlists (no smart blocks at the top level) because the
        // operator's filler is meant to be a playlist that wraps a
        // smart block (per Section 23.18 + 23.19 design).
        $playlists = [];
        $pls = CcPlaylistQuery::create()->orderByDbName()->find();
        foreach ($pls as $pl) {
            $playlists[(int) $pl->getDbId()] = $pl->getDbName();
        }

        $this->view->statusMsg             = $msg;
        $this->view->autoDjEnabled         = Application_Model_Preference::GetAutoDjEnabled();
        $this->view->autoDjShowName        = Application_Model_Preference::GetAutoDjShowName();
        $this->view->autoDjPlaylistId      = Application_Model_Preference::GetAutoDjPlaylistId();
        $this->view->autoDjFillAnyShow     = Application_Model_Preference::GetAutoDjFillAnyShow();
        $this->view->autoDjLogoPath        = Application_Model_Preference::GetAutoDjLogoPath();
        $this->view->autoDjShowUrl         = Application_Model_Preference::GetAutoDjShowUrl();
        $this->view->autoDjShowGenre       = Application_Model_Preference::GetAutoDjShowGenre();
        $this->view->autoDjShowDescription = Application_Model_Preference::GetAutoDjShowDescription();
        $this->view->autoDjShowBgColor     = Application_Model_Preference::GetAutoDjShowBgColor();
        $this->view->autoDjShowTextColor   = Application_Model_Preference::GetAutoDjShowTextColor();
        $this->view->playlists             = $playlists;

        // RASTATIME 2026-05-21 v3 — embed the logo image as a
        // data-URI so the operator gets a visual preview of the
        // currently-saved logo (browser cannot read absolute file
        // paths from the server FS).  Same pattern as
        // ShowFormService::imagePathToDataUri().  Empty string when
        // no logo is configured or the file is unreadable.
        $this->view->autoDjLogoDataUri = '';
        $logoPath = Application_Common_Storage::toAbsolute($this->view->autoDjLogoPath);
        if (!empty($logoPath) && @is_readable($logoPath)) {
            $bytes = @file_get_contents($logoPath);
            if ($bytes !== false && $bytes !== '') {
                $mime = @mime_content_type($logoPath) ?: 'image/jpeg';
                $this->view->autoDjLogoDataUri =
                    'data:' . $mime . ';base64,' . base64_encode($bytes);
            }
        }
    }

    /**
     * RASTATIME 2026-05-21 — Section 23.20.  Default-logo upload for
     * Auto-DJ shows.  Single global logo, stored under
     * <storage>/imported/auto-dj-logos/<basename>.<ext> (root-relative in cc_pref)
     * — analogous to {@see Rest_ShowImageController::postAction()} but
     * not per-show.  Triggered via multipart POST from the Auto-DJ
     * settings page; success writes the absolute path back to
     * cc_pref via Preference::SetAutoDjLogoPath().
     */
    public function autoDjUploadLogoAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $response = $this->getResponse();

        if (!isset($_FILES['file']) || empty($_FILES['file']['tmp_name'])) {
            $response->setHttpResponseCode(400)
                ->appendBody('No file uploaded');
            return;
        }

        try {
            Application_Common_Storage::assertNotMoving();   // RASTATIME 2026-09-16
            // MIME-typed extension (re-uses the same allow-list as
            // Rest_ShowImageController to stay consistent).
            $finfo = finfo_open();
            $mime = finfo_file($finfo, $_FILES['file']['tmp_name'], FILEINFO_MIME_TYPE);
            $extensions = [
                'image/jpeg' => 'jpg',
                'image/png'  => 'png',
                'image/gif'  => 'gif',
                'image/webp' => 'webp',   // RASTATIME 2026-10-25
            ];
            if (!isset($extensions[$mime])) {
                throw new Exception('Bad file type — only JPG, PNG, GIF and WebP are accepted.');
            }
            $ext = $extensions[$mime];

            // RASTATIME 2026-09-16 - no owner-id level, path stored root-relative.
            $dir = rtrim(Application_Common_Storage::root(), '/\\') . '/imported/auto-dj-logos';
            if (!is_dir($dir) && !mkdir($dir, 0777, true)) {
                throw new Exception('Failed to create logo storage directory.');
            }

            // basename() works for both POSIX and Windows temp paths
            // (same gotcha as Section 23.x show-image fix).
            $newFileName = basename($_FILES['file']['tmp_name']) . '.' . $ext;
            $destination = Application_Common_OsPath::join($dir, $newFileName);
            if (@rename($_FILES['file']['tmp_name'], $destination) === false) {
                throw new Exception(
                    'Failed to move uploaded file — check disk space and '
                    . 'write permissions on ' . $dir
                );
            }

            Application_Model_Preference::SetAutoDjLogoPath(Application_Common_Storage::toRelative($destination));
            $response->setHttpResponseCode(201)
                ->appendBody($destination);
        } catch (Throwable $e) {
            Logging::warn('autoDjUploadLogoAction: ' . $e->getMessage());
            $response->setHttpResponseCode(500)
                ->appendBody('Error processing logo: ' . $e->getMessage());
        }
    }

    /**
     * RASTATIME 2026-05-21 — Section 23.20.  Reset the default Auto-DJ
     * logo (clears cc_pref entry; the file itself is left on disk).
     */
    public function autoDjRemoveLogoAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        Application_Model_Preference::SetAutoDjLogoPath('');
        $this->getResponse()->setHttpResponseCode(200)->appendBody('OK');
    }
}
