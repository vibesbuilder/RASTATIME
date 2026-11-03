<?php

/**
 * RASTATIME 2026-11-03 - publishing stage 1 (CBA publishing, migration 0074):
 *   Settings  → Editorial Team  (publishing/editors): the profiles a show's
 *                                 editorial team is chosen from
 *   Analytics → Participants    (publishing/participants, .../participants-csv):
 *                                 people involved per show and year
 * ACL resource "publishing" = program managers and admins.
 */
class PublishingController extends Zend_Controller_Action
{
    private function csrfToken()
    {
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }

        return $ns->authtoken;
    }

    public function editorsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $request = $this->getRequest();
        $session = new Zend_Session_Namespace('rt_publishing');
        $this->view->message = $session->message ?? null;
        $this->view->error = null;
        unset($session->message);
        $edit = ['id' => 0, 'name' => '', 'email' => '', 'subjs_id' => 0, 'active' => true];

        if ($request->isPost() && Application_Service_PublishingService::tablesReady()) {
            // the Acl plugin has checked the CSRF token of every legacy POST
            $op = (string) $request->getPost('op', 'save');
            $id = (int) $request->getPost('id', 0);
            if ($op === 'delete') {
                Application_Service_PublishingService::deleteProfile($id);
                $session->message = _('Profile deleted.');
                $this->_redirect('publishing/editors');

                return;
            }
            [$savedId, $error] = Application_Service_PublishingService::saveProfile(
                $id,
                (string) $request->getPost('name', ''),
                (string) $request->getPost('email', ''),
                (int) $request->getPost('subjs_id', 0),
                (bool) $request->getPost('active', false)
            );
            if ($error === null) {
                $session->message = $id > 0 ? _('Profile saved.') : _('Profile added.');
                $this->_redirect('publishing/editors');

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

        $this->view->ready = Application_Service_PublishingService::tablesReady();
        $this->view->profiles = Application_Service_PublishingService::profiles();
        $this->view->edit = $edit;
        $this->view->users = Propel::getConnection()->query(
            "SELECT id, login, trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')) AS full_name
               FROM cc_subjs ORDER BY lower(login)"
        )->fetchAll(PDO::FETCH_ASSOC);
        $this->view->csrf = $this->csrfToken();
    }

    public function participantsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $years = Application_Service_PublishingService::reportYears();
        $year = (int) $this->_getParam('year', $years[0]);
        if (!in_array($year, $years, true)) {
            $year = $years[0];
        }
        $this->view->years = $years;
        $this->view->report = Application_Service_PublishingService::participantsReport($year);
        $this->view->ready = Application_Service_PublishingService::tablesReady();
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
        $years = Application_Service_PublishingService::reportYears();
        $year = (int) $this->_getParam('year', $years[0]);
        if (!in_array($year, $years, true)) {
            $year = $years[0];
        }
        $report = Application_Service_PublishingService::participantsReport($year);
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
