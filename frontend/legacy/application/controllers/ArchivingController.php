<?php

/**
 * RASTATIME 2026-11-03 - archiving (CBA archiving, migrations 0074-0076):
 *   Settings  → Archiving       (archiving/settings): the editorial teams a
 *                                 show chooses from and, for admins, the CBA
 *                                 accounts, the upload limit and the waiting
 *                                 time of the automatic archiving; the forms
 *                                 post to archiving/editors (program managers
 *                                 and admins) and archiving/accounts (admins)
 *   Analytics → Participants    (archiving/participants, .../participants-csv):
 *                                 people involved per show and year
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
            'team-added' => _('Team added.'),
            'team-saved' => _('Team saved.'),
            'team-deleted' => _('Team deleted.'),
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
            _('Participations'), _('Repeat'), _('Editorial team')], ',', '"', '');
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
}
