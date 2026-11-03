<?php

/**
 * RASTATIME 2026-11-03 - archiving stage 1 (CBA archiving, migrations 0074 and 0075):
 *   Settings  → Editorial Team  (archiving/editors): the profiles a show's
 *                                 editorial team is chosen from
 *   Analytics → Participants    (archiving/participants, .../participants-csv):
 *                                 people involved per show and year
 * ACL resource "archiving" = program managers and admins.
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
            'profile-added' => _('Profile added.'),
            'profile-saved' => _('Profile saved.'),
            'profile-deleted' => _('Profile deleted.'),
            'account-added' => _('Account added.'),
            'account-saved' => _('Account saved.'),
            'account-deleted' => _('Account deleted.'),
            'bandwidth' => _('Upload limit saved.'),
        ];

        return $messages[(string) $this->getRequest()->getParam('done', '')] ?? null;
    }

    public function editorsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $request = $this->getRequest();
        $this->view->message = $this->doneMessage();
        $this->view->error = null;
        $edit = ['id' => 0, 'name' => '', 'email' => '', 'subjs_id' => 0, 'active' => true];

        if ($request->isPost() && Application_Service_ArchivingService::tablesReady()) {
            // the Acl plugin has checked the CSRF token of every legacy POST
            $op = (string) $request->getPost('op', 'save');
            $id = (int) $request->getPost('id', 0);
            if ($op === 'delete') {
                Application_Service_ArchivingService::deleteProfile($id);
                $this->_redirect('archiving/editors?done=profile-deleted');

                return;
            }
            [$savedId, $error] = Application_Service_ArchivingService::saveProfile(
                $id,
                (string) $request->getPost('name', ''),
                (string) $request->getPost('email', ''),
                (int) $request->getPost('subjs_id', 0),
                (bool) $request->getPost('active', false)
            );
            if ($error === null) {
                $this->_redirect('archiving/editors?done=' . ($id > 0 ? 'profile-saved' : 'profile-added'));

                return;
            }
            $this->view->error = $error;
            $edit = [
                'id' => $id,
                'name' => (string) $request->getPost('name', ''),
                'email' => (string) $request->getPost('email', ''),
                'subjs_id' => (int) $request->getPost('subjs_id', 0),
                'active' => (bool) $request->getPost('active', false),
            ];
        }

        $this->view->ready = Application_Service_ArchivingService::tablesReady();
        $this->view->profiles = Application_Service_ArchivingService::profiles();
        $this->view->edit = $edit;
        $this->view->users = Propel::getConnection()->query(
            "SELECT id, login, trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')) AS full_name
               FROM cc_subjs ORDER BY lower(login)"
        )->fetchAll(PDO::FETCH_ASSOC);
        $this->view->csrf = $this->csrfToken();
    }

    /**
     * Settings → CBA Accounts (archiving stage 2, admins only by ACL): the
     * CBA users the shows are archived under, the connection test and the
     * upload bandwidth limit.  The application password is write-only.
     */
    public function accountsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $request = $this->getRequest();
        $this->view->message = $this->doneMessage();
        $this->view->messageOk = true;
        $this->view->error = null;
        $edit = ['id' => 0, 'label' => '', 'username' => ''];

        if ($request->isPost() && Application_Service_ArchivingService::tablesReady()) {
            // the Acl plugin has checked the CSRF token of every legacy POST
            $op = (string) $request->getPost('op', 'save');
            $id = (int) $request->getPost('id', 0);
            if ($op === 'delete') {
                Application_Service_ArchivingService::deleteAccount($id);
                $this->_redirect('archiving/accounts?done=account-deleted');

                return;
            }
            if ($op === 'bandwidth') {
                $mbit = (float) str_replace(',', '.', (string) $request->getPost('mbit', '4'));
                Application_Service_ArchivingService::setUploadKbit((int) round($mbit * 1000));
                $this->_redirect('archiving/accounts?done=bandwidth');

                return;
            }
            if ($op === 'test') {
                // shown right away (no redirect); the answer names the CBA user
                [$ok, $text] = Application_Service_ArchivingService::testAccount($id);
                $this->view->message = $text;
                $this->view->messageOk = $ok;
            } else {
                [$savedId, $error] = Application_Service_ArchivingService::saveAccount(
                    $id,
                    (string) $request->getPost('label', ''),
                    (string) $request->getPost('username', ''),
                    (string) $request->getPost('app_password', '')
                );
                if ($error === null) {
                    $this->_redirect('archiving/accounts?done=' . ($id > 0 ? 'account-saved' : 'account-added'));

                    return;
                }
                $this->view->error = $error;
                $edit = [
                    'id' => $id,
                    'label' => (string) $request->getPost('label', ''),
                    'username' => (string) $request->getPost('username', ''),
                ];
            }
        }

        $this->view->ready = Application_Service_ArchivingService::tablesReady();
        $this->view->accounts = Application_Service_ArchivingService::accounts();
        $this->view->edit = $edit;
        $this->view->mbit = Application_Service_ArchivingService::uploadKbit() / 1000;
        $this->view->csrf = $this->csrfToken();
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
        fputcsv($out, [_('Total'), $t['episodes'], $t['participants'], '', $t['person_episodes'], '',
            sprintf(_('%d profiles'), $t['profiles'])], ',', '"', '');
        rewind($out);
        $csv = stream_get_contents($out);
        fclose($out);
        $this->getResponse()
            ->setHeader('Content-Type', 'text/csv; charset=utf-8', true)
            ->setHeader('Content-Disposition', 'attachment; filename="participants-' . $year . '.csv"', true)
            ->setBody($csv);
    }
}
