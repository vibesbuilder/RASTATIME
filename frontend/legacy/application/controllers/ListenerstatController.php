<?php

class ListenerstatController extends Zend_Controller_Action
{
    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext
            ->addActionContext('get-data', 'json')
            ->initContext();
    }

    public function indexAction()
    {
        $request = $this->getRequest();

        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');

        $this->view->headScript()->appendFile(Assets::url('js/flot/jquery.flot.js'), 'text/javascript');
        // RASTATIME 2026-06-05 (?jq3): Flot 0.7 is incompatible with jQuery 3.
        // Upgraded to Flot 0.8.3, which moved the time-axis (xaxis mode:"time")
        // into a separate plugin -- load it right after the core.
        $this->view->headScript()->appendFile(Assets::url('js/flot/jquery.flot.time.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/flot/jquery.flot.crosshair.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/flot/jquery.flot.resize.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/listenerstat/listenerstat.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/timepicker/jquery.ui.timepicker.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/buttons/buttons.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/utilities/utilities.js'), 'text/javascript');
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.ui.timepicker.css'));

        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($request);
        $userTimezone = new DateTimeZone(Application_Model_Preference::GetUserTimezone());
        $startsDT->setTimezone($userTimezone);
        $endsDT->setTimezone($userTimezone);

        $form = new Application_Form_DateRange();
        $form->populate([
            'his_date_start' => $startsDT->format('Y-m-d'),
            'his_time_start' => $startsDT->format('H:i'),
            'his_date_end' => $endsDT->format('Y-m-d'),
            'his_time_end' => $endsDT->format('H:i'),
        ]);

        $this->view->errorStatus = self::collectionStatus($userTimezone);
        $this->view->date_form = $form;
    }

    /**
     * RASTATIME 2026-10-26 - the "Stream Data Collection Status" box: one
     * line per ENABLED stream, in stream order, with the real cause.  Every
     * failure used to read "check admin user/password", and an error stayed
     * after Icecast had recovered (the collector never reported "OK"; fixed
     * in history/stats.py, which now writes "kind|UTC time|detail").
     *
     * @return array[] label, ok (bool), text
     */
    private static function collectionStatus(DateTimeZone $userTimezone)
    {
        $statuses = [];
        foreach (Application_Model_Preference::GetAllListenerStatErrors() as $row) {
            $parts = explode(':', $row['keystr']);
            $statuses[(int) ($parts[1] ?? 0)] = (string) $row['valstr'];
        }

        $out = [];
        for ($n = 1; $n <= 3; ++$n) {
            $stream = Application_Model_Preference::GetStreamOutput($n);
            if (strtolower((string) ($stream['enable'] ?? '')) !== 'true') {
                continue;
            }
            $mount = ltrim((string) ($stream['mount'] ?? ''), '/');
            $label = sprintf(_('Stream %d'), $n) . ($mount !== '' ? " ({$mount})" : '');

            if (trim((string) ($stream['admin_pass'] ?? '')) === '') {
                $out[] = ['label' => $label, 'ok' => false,
                    'text' => _('No admin password on Settings -> Streams: listener statistics are not collected.')];

                continue;
            }

            $status = $statuses[$n] ?? null;
            if ($status === null) {
                $out[] = ['label' => $label, 'ok' => true, 'text' => _('Waiting for the first query.')];
            } elseif ($status === 'OK') {
                $out[] = ['label' => $label, 'ok' => true, 'text' => _('OK')];
            } else {
                $out[] = ['label' => $label, 'ok' => false, 'text' => self::statusText($status, $userTimezone)];
            }
        }

        return $out;
    }

    private static function statusText(string $status, DateTimeZone $userTimezone): string
    {
        $parts = explode('|', $status, 3);
        if (count($parts) < 3) {
            // written before 2026-10-26: the raw exception text
            return strpos($status, '401') !== false
                ? _('Please make sure admin user/password is correct on Settings->Streams page.')
                : sprintf(_('Collection failed: %s'), $status);
        }
        [$kind, $when, $detail] = $parts;
        try {
            $since = (new DateTime($when, new DateTimeZone('UTC')))->setTimezone($userTimezone)->format('Y-m-d H:i');
        } catch (Exception $e) {
            $since = $when;
        }

        switch ($kind) {
            case 'auth':
                return sprintf(_('Icecast has rejected the admin user/password since %s. Please check them on Settings -> Streams.'), $since);

            case 'unreachable':
                return sprintf(_('Icecast has not been reachable since %s.'), $since);

            case 'timeout':
                return sprintf(_('Icecast has not answered in time since %s.'), $since);

            case 'invalid':
                return sprintf(_('Icecast has sent an unreadable statistics page since %s.'), $since);

            default:
                return sprintf(_('Icecast has answered with an error since %s: %s'), $since, $detail);
        }
    }

    public function showAction()
    {
        $request = $this->getRequest();
        $headScript = $this->view->headScript();
        AirtimeTableView::injectTableJavaScriptDependencies($headScript);
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $this->view->headScript()->appendFile(Assets::url('js/timepicker/jquery.ui.timepicker.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/buttons/buttons.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/utilities/utilities.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/listenerstat/showlistenerstat.js'), 'text/javascript');

        AirtimeTableView::injectTableCssDependencies($this->view->headLink());
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.ui.timepicker.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/show_analytics.css'));

        $user = Application_Model_User::getCurrentUser();
        if ($user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER])) {
            $this->view->showAllShows = true;
        }
        $data = [];
        $this->view->showData = $data;

        $form = new Application_Form_ShowListenerStat();

        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($request);
        $userTimezone = new DateTimeZone(Application_Model_Preference::GetUserTimezone());
        $startsDT->setTimezone($userTimezone);
        $endsDT->setTimezone($userTimezone);
        $form->populate([
            'his_date_start' => $startsDT->format('Y-m-d'),
            'his_time_start' => $startsDT->format('H:i'),
            'his_date_end' => $endsDT->format('Y-m-d'),
            'his_time_end' => $endsDT->format('H:i'),
        ]);

        $this->view->date_form = $form;
    }

    public function getDataAction()
    {
        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($this->getRequest());
        $data = Application_Model_ListenerStat::getDataPointsWithinRange(
            $startsDT->format(DEFAULT_TIMESTAMP_FORMAT),
            $endsDT->format(DEFAULT_TIMESTAMP_FORMAT)
        );
        $this->_helper->json->sendJson($data);
    }

    public function getShowDataAction()
    {
        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($this->getRequest());
        $show_id = $this->getRequest()->getParam('show_id', null);
        $data = Application_Model_ListenerStat::getShowDataPointsWithinRange(
            $startsDT->format(DEFAULT_TIMESTAMP_FORMAT),
            $endsDT->format(DEFAULT_TIMESTAMP_FORMAT),
            $show_id
        );
        $this->_helper->json->sendJson($data);
    }

    public function getAllShowData()
    {
        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($this->getRequest());

        return Application_Model_ListenerStat::getAllShowDataPointsWithinRange(
            $startsDT->format(DEFAULT_TIMESTAMP_FORMAT),
            $endsDT->format(DEFAULT_TIMESTAMP_FORMAT)
        );
    }

    public function getAllShowDataAction()
    {
        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($this->getRequest());
        $show_id = $this->getRequest()->getParam('show_id', null);
        $data = Application_Model_ListenerStat::getAllShowDataPointsWithinRange(
            $startsDT->format(DEFAULT_TIMESTAMP_FORMAT),
            $endsDT->format(DEFAULT_TIMESTAMP_FORMAT)
        );
        $this->_helper->json->sendJson($data);
    }
}
