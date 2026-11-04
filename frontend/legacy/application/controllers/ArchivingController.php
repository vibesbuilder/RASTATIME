<?php

/**
 * RASTATIME 2026-11-03 - archiving (CBA archiving, migrations 0074-0076):
 *   Settings  → Archiving       (archiving/settings): the producers a
 *                                 show chooses from and, for admins, the CBA
 *                                 accounts, the upload limit and the waiting
 *                                 time of the automatic archiving; the forms
 *                                 post to archiving/editors (program managers
 *                                 and admins) and archiving/accounts (admins)
 *   Analytics → People Involved (archiving/participants, .../participants-csv):
 *                                 people involved per own production and year
 *                                 (own menu entry since 2026-11-04)
 *   Analytics → Archive Status  (archiving/status, .../status-data, .../status-csv,
 *                                 .../status-op): uploads running and waiting,
 *                                 what the automatic archiving has ahead, open
 *                                 problems, the history; cancel, again, link
 * ACL resource "archiving" = program managers and admins; "accounts" admins only.
 */
class ArchivingController extends Zend_Controller_Action
{
    private function csrfToken()
    {
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }

        return $ns->authtoken;
    }

    /**
     * The message after a redirect.  The legacy session is already closed for
     * writing when a controller runs (PageLayoutInitPlugin), so a flash message
     * kept in the session never survived; the redirect carries a fixed code.
     */
    private function doneMessage(): ?string
    {
        $messages = [
            'team-added' => _('Producer added.'),
            'team-saved' => _('Producer saved.'),
            'team-deleted' => _('Producer deleted.'),
            'account-added' => _('Account added.'),
            'account-saved' => _('Account saved.'),
            'account-deleted' => _('Account deleted.'),
            'bandwidth' => _('Upload limit saved.'),
            'auto-delay' => _('Waiting time saved.'),
        ];

        return $messages[(string) $this->getRequest()->getParam('done', '')] ?? null;
    }

    /**
     * Settings → Archiving (operator 2026-11-03: one page instead of
     * "Editorial Team" and "CBA Accounts").  $teamForm / $accountForm carry
     * a message or a failed form back from editorsAction / accountsAction.
     */
    private function renderSettings(array $teamForm = [], array $accountForm = []): void
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $message = $this->doneMessage();
        $forTeams = strpos((string) $this->getRequest()->getParam('done', ''), 'team-') === 0;
        $this->view->teamForm = $teamForm + [
            'message' => $forTeams ? $message : null,
            'error' => null,
            'edit' => ['id' => 0, 'name' => '', 'email' => '', 'subjs_id' => 0, 'active' => true],
        ];
        $this->view->accountForm = $accountForm + [
            'message' => $forTeams ? null : $message,
            'messageOk' => true,
            'error' => null,
            'edit' => ['id' => 0, 'label' => '', 'username' => ''],
        ];
        $this->view->ready = Application_Service_ArchivingService::tablesReady();
        $this->view->profiles = Application_Service_ArchivingService::profiles();
        $this->view->users = Propel::getConnection()->query(
            "SELECT id, login, trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')) AS full_name
               FROM cc_subjs ORDER BY lower(login)"
        )->fetchAll(PDO::FETCH_ASSOC);
        // the CBA accounts are for admins (ACL privilege "accounts")
        $this->view->showAccounts = Application_Model_User::getCurrentUser()->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN]);
        if ($this->view->showAccounts) {
            $this->view->accounts = Application_Service_ArchivingService::accounts();
            $this->view->mbit = Application_Service_ArchivingService::uploadKbit() / 1000;
            $this->view->autoDelay = Application_Service_ArchivingService::autoDelayMin();
        }
        $this->view->csrf = $this->csrfToken();
        $this->_helper->viewRenderer->setScriptAction('settings');
    }

    public function settingsAction()
    {
        $this->renderSettings();
    }

    /** The editorial teams (form of Settings → Archiving); a GET goes to the page. */
    public function editorsAction()
    {
        $request = $this->getRequest();
        if (!$request->isPost() || !Application_Service_ArchivingService::tablesReady()) {
            $this->_redirect('archiving/settings');

            return;
        }
        // the Acl plugin has checked the CSRF token of every legacy POST
        $op = (string) $request->getPost('op', 'save');
        $id = (int) $request->getPost('id', 0);
        if ($op === 'delete') {
            Application_Service_ArchivingService::deleteProfile($id);
            $this->_redirect('archiving/settings?done=team-deleted');

            return;
        }
        $edit = [
            'id' => $id,
            'name' => (string) $request->getPost('name', ''),
            'email' => (string) $request->getPost('email', ''),
            'subjs_id' => (int) $request->getPost('subjs_id', 0),
            'active' => (bool) $request->getPost('active', false),
        ];
        [$savedId, $error] = Application_Service_ArchivingService::saveProfile(
            $id,
            $edit['name'],
            $edit['email'],
            $edit['subjs_id'],
            $edit['active']
        );
        if ($error === null) {
            $this->_redirect('archiving/settings?done=' . ($id > 0 ? 'team-saved' : 'team-added'));

            return;
        }
        $this->renderSettings(['error' => $error, 'edit' => $edit]);
    }

    /**
     * The CBA accounts, the connection test, the upload limit and the waiting
     * time (admins only by ACL); a GET goes to the page.  The application
     * password is write-only.
     */
    public function accountsAction()
    {
        $request = $this->getRequest();
        if (!$request->isPost() || !Application_Service_ArchivingService::tablesReady()) {
            $this->_redirect('archiving/settings#cba-accounts');

            return;
        }
        // the Acl plugin has checked the CSRF token of every legacy POST
        $op = (string) $request->getPost('op', 'save');
        $id = (int) $request->getPost('id', 0);
        if ($op === 'delete') {
            Application_Service_ArchivingService::deleteAccount($id);
            $this->_redirect('archiving/settings?done=account-deleted#cba-accounts');

            return;
        }
        if ($op === 'bandwidth') {
            $mbit = (float) str_replace(',', '.', (string) $request->getPost('mbit', '4'));
            Application_Service_ArchivingService::setUploadKbit((int) round($mbit * 1000));
            $this->_redirect('archiving/settings?done=bandwidth#cba-accounts');

            return;
        }
        if ($op === 'auto_delay') {
            Application_Service_ArchivingService::setAutoDelayMin((int) $request->getPost('minutes', 30));
            $this->_redirect('archiving/settings?done=auto-delay#cba-accounts');

            return;
        }
        if ($op === 'test') {
            // shown right away (no redirect); the answer names the CBA user
            [$ok, $text] = Application_Service_ArchivingService::testAccount($id);
            $this->renderSettings([], ['message' => $text, 'messageOk' => $ok]);

            return;
        }
        $edit = [
            'id' => $id,
            'label' => (string) $request->getPost('label', ''),
            'username' => (string) $request->getPost('username', ''),
        ];
        [$savedId, $error] = Application_Service_ArchivingService::saveAccount(
            $id,
            $edit['label'],
            $edit['username'],
            (string) $request->getPost('app_password', '')
        );
        if ($error === null) {
            $this->_redirect('archiving/settings?done=' . ($id > 0 ? 'account-saved' : 'account-added') . '#cba-accounts');

            return;
        }
        $this->renderSettings([], ['error' => $error, 'edit' => $edit]);
    }

    public function participantsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $years = Application_Service_ArchivingService::reportYears();
        $year = (int) $this->_getParam('year', $years[0]);
        if (!in_array($year, $years, true)) {
            $year = $years[0];
        }
        $this->view->years = $years;
        $this->view->report = Application_Service_ArchivingService::participantsReport($year);
        $this->view->ready = Application_Service_ArchivingService::tablesReady();
        $this->view->missingOnly = (bool) $this->_getParam('missing', false);
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $this->view->isCurrentYear = $year === (int) (new DateTime('now', $tz))->format('Y');
        $this->view->today = (new DateTime('now', $tz))->format('Y-m-d');
    }

    /** The overview of one year as CSV (UTF-8 with BOM, comma, for spreadsheets). */
    public function participantsCsvAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $years = Application_Service_ArchivingService::reportYears();
        $year = (int) $this->_getParam('year', $years[0]);
        if (!in_array($year, $years, true)) {
            $year = $years[0];
        }
        $report = Application_Service_ArchivingService::participantsReport($year);
        $out = fopen('php://temp', 'w+');
        fwrite($out, "\xEF\xBB\xBF");
        fputcsv($out, [_('Show name'), _('Episodes aired'), _('People involved'), _('Episodes with own value'),
            _('Participations'), _('Repeat'), _('Producer')], ',', '"', '');
        foreach ($report['rows'] as $r) {
            fputcsv($out, [$r['name'], $r['episodes'], $r['participants'] ?? '', $r['overrides'],
                $r['person_episodes'] ?? '', $r['is_repeat'] ? _('yes') : '', $r['team']], ',', '"', '');
        }
        $t = $report['totals'];
        // the teams are not counted (operator 2026-11-03: only the people involved)
        fputcsv($out, [_('Total'), $t['episodes'], $t['participants'], '', $t['person_episodes'], '', ''], ',', '"', '');
        rewind($out);
        $csv = stream_get_contents($out);
        fclose($out);
        $this->getResponse()
            ->setHeader('Content-Type', 'text/csv; charset=utf-8', true)
            ->setHeader('Content-Disposition', 'attachment; filename="participants-' . $year . '.csv"', true)
            ->setBody($csv);
    }

    // ------------------------------------------------------------------
    // Analytics → Archive Status (operator go 2026-11-04)
    // ------------------------------------------------------------------

    /** Rows of the history on the page; the CSV has all. */
    private const STATUS_HISTORY_ROWS = 500;

    /** The history filter from a request or the "back" field of a form, checked. */
    private function statusFilter(array $src): array
    {
        $years = Application_Service_ArchivingService::jobYears();
        $year = (int) ($src['year'] ?? $years[0]);
        $status = (string) ($src['status'] ?? '');
        $trigger = (string) ($src['trigger'] ?? '');

        return [
            'year' => in_array($year, $years, true) ? $year : $years[0],
            'month' => max(0, min(12, (int) ($src['month'] ?? 0))),
            'status' => in_array($status, Application_Service_ArchivingService::JOB_STATUSES, true) ? $status : '',
            'trigger' => in_array($trigger, ['auto', 'manual'], true) ? $trigger : '',
            'show' => mb_substr(trim((string) ($src['show'] ?? '')), 0, 100),
        ];
    }

    /** "12:running:1,13:queued:0" (id:status:attempts) - the page reloads when the open uploads change. */
    private static function statusSignature(array $open): string
    {
        return implode(',', array_map(fn ($j) => $j['id'] . ':' . $j['status'] . ':' . $j['attempts'], $open));
    }

    private function renderStatus(?string $message = null, bool $ok = true): void
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $filter = $this->statusFilter($this->getRequest()->getParams());
        $messages = [
            'cancelled' => _('The upload was cancelled.'),
            'cancel-late' => _('The upload had started already and was not cancelled.'),
            'again' => _('The upload is queued again.'),
            'linked' => _('The episode is linked to the post.'),
        ];
        $done = (string) $this->getRequest()->getParam('done', '');
        $this->view->message = $message ?? ($messages[$done] ?? null);
        $this->view->messageOk = $message === null ? $done !== 'cancel-late' : $ok;
        $this->view->filter = $filter;
        $this->view->years = Application_Service_ArchivingService::jobYears();
        $this->view->ready = Application_Service_ArchivingService::tablesReady();
        $this->view->open = Application_Service_ArchivingService::openJobs();
        $this->view->signature = self::statusSignature($this->view->open);
        $this->view->planned = Application_Service_ArchivingService::plannedEpisodes();
        $this->view->problems = Application_Service_ArchivingService::problemJobs();
        $this->view->history = Application_Service_ArchivingService::jobHistory(
            $filter['year'],
            $filter['month'],
            $filter['status'],
            $filter['trigger'],
            $filter['show'],
            self::STATUS_HISTORY_ROWS + 1
        );
        $this->view->historyMax = self::STATUS_HISTORY_ROWS;
        $this->view->autoDelay = Application_Service_ArchivingService::autoDelayMin();
        $this->view->csrf = $this->csrfToken();
        $this->_helper->viewRenderer->setScriptAction('status');
    }

    public function statusAction()
    {
        $this->renderStatus();
    }

    /** GET: the open uploads as JSON, polled by the page (progress; a change reloads it). */
    public function statusDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $open = Application_Service_ArchivingService::openJobs();
        $this->_helper->json->sendJson([
            'ok' => true,
            'signature' => self::statusSignature($open),
            'percent' => array_column($open, 'percent', 'id'),
        ]);
    }

    /**
     * POST op (cancel | again | link), id (upload job), post (link: number or
     * address), back (the history filter): the actions of the page.
     */
    public function statusOpAction()
    {
        $request = $this->getRequest();
        if (!$request->isPost() || !Application_Service_ArchivingService::tablesReady()) {
            $this->_redirect('archiving/status');

            return;
        }
        // the Acl plugin has checked the CSRF token of every legacy POST
        parse_str((string) $request->getPost('back', ''), $back);
        $filter = $this->statusFilter($back);
        $request->setParams($filter);
        $op = (string) $request->getPost('op', '');
        $id = (int) $request->getPost('id', 0);
        $user = Application_Model_User::getCurrentUser();
        $done = null;
        if ($op === 'cancel') {
            $done = Application_Service_ArchivingService::cancelJob($id, (string) $user->getLogin()) ? 'cancelled' : 'cancel-late';
        } elseif ($op === 'again') {
            [$jobId, $reasons] = Application_Service_ArchivingService::retryJob($id, (int) $user->getId());
            if (!$jobId) {
                $this->renderStatus(implode(' ', $reasons), false);

                return;
            }
            $done = 'again';
        } elseif ($op === 'link') {
            $instanceId = Application_Service_ArchivingService::jobInstance($id);
            $error = $instanceId
                ? Application_Service_ArchivingService::linkPost($instanceId, (string) $request->getPost('post', ''))
                : _('The upload does not exist any more.');
            if ($error !== null) {
                $this->renderStatus($error, false);

                return;
            }
            $done = 'linked';
        }
        $this->_redirect('archiving/status?' . http_build_query($filter + ($done ? ['done' => $done] : [])));
    }

    /** The history with the filter of the page as CSV (all rows, UTF-8 with BOM). */
    public function statusCsvAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $f = $this->statusFilter($this->getRequest()->getParams());
        $rows = Application_Service_ArchivingService::jobHistory($f['year'], $f['month'], $f['status'], $f['trigger'], $f['show']);
        $labels = self::jobStatusLabels();
        $out = fopen('php://temp', 'w+');
        fwrite($out, "\xEF\xBB\xBF");
        fputcsv($out, [_('Queued'), _('Show name'), _('Episode'), _('Started by'), _('Status'), _('Post'),
            _('Audio'), _('Size (MB)'), _('Duration (s)'), _('Attempts'), _('Note')], ',', '"', '');
        foreach ($rows as $r) {
            fputcsv($out, [
                $r['created_local'],
                $r['show_name'],
                $r['episode_local'],
                $r['trigger'] === 'auto' ? _('Automatic') : ($r['login'] !== '' ? $r['login'] : _('By hand')),
                $labels[$r['status']] ?? $r['status'],
                $r['post_id'] ? 'https://cba.media/?p=' . $r['post_id'] : '',
                $r['file'],
                $r['bytes_total'] ? round($r['bytes_total'] / 1048576, 1) : '',
                $r['secs'] ?? '',
                $r['attempts'],
                $r['error'],
            ], ',', '"', '');
        }
        rewind($out);
        $csv = stream_get_contents($out);
        fclose($out);
        $name = 'archive-status-' . $f['year'] . ($f['month'] ? sprintf('-%02d', $f['month']) : '') . '.csv';
        $this->getResponse()
            ->setHeader('Content-Type', 'text/csv; charset=utf-8', true)
            ->setHeader('Content-Disposition', 'attachment; filename="' . $name . '"', true)
            ->setBody($csv);
    }

    /** Short names of the job states (page and CSV). */
    public static function jobStatusLabels(): array
    {
        return [
            'queued' => _('Waiting'),
            'running' => _('Uploading'),
            'done' => _('Archived'),
            'failed' => _('Failed'),
            'unclear' => _('Unclear'),
            'skipped' => _('Given up'),
            'cancelled' => _('Cancelled'),
        ];
    }
}
