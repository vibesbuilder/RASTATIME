<?php

class ScheduleController extends Zend_Controller_Action
{
    protected $sched_sess;

    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('event-feed', 'json')
            ->addActionContext('event-feed-preload', 'json')
            ->addActionContext('make-context-menu', 'json')
            ->addActionContext('add-show-dialog', 'json')
            ->addActionContext('add-show', 'json')
            ->addActionContext('edit-show', 'json')
            ->addActionContext('move-show', 'json')
            ->addActionContext('resize-show', 'json')
            ->addActionContext('delete-show-instance', 'json')
            ->addActionContext('show-content-dialog', 'json')
            // RASTATIME 2026-10-16 - teaser automation stage 2
            ->addActionContext('teaser-dialog', 'json')
            ->addActionContext('clear-show', 'json')
            ->addActionContext('get-current-playlist', 'json')
            ->addActionContext('remove-group', 'json')
            ->addActionContext('populate-show-form', 'json')
            ->addActionContext('populate-repeating-show-instance-form', 'json')
            ->addActionContext('delete-show', 'json')
            ->addActionContext('cancel-current-show', 'json')
            ->addActionContext('get-form', 'json')
            ->addActionContext('upload-to-sound-cloud', 'json')
            ->addActionContext('content-context-menu', 'json')
            ->addActionContext('set-time-scale', 'json')
            ->addActionContext('set-time-interval', 'json')
            ->addActionContext('edit-repeating-show-instance', 'json')
            ->addActionContext('dj-edit-show', 'json')
            ->addActionContext('calculate-duration', 'json')
            ->addActionContext('get-current-show', 'json')
            ->addActionContext('update-future-is-scheduled', 'json')
            ->addActionContext('localize-start-end-time', 'json')
            // RASTATIME 2026-05-19 — Show-Template feature (Section 23.16)
            ->addActionContext('list-show-templates', 'json')
            ->addActionContext('get-show-template', 'json')
            ->addActionContext('save-show-template', 'json')
            ->addActionContext('rename-show-template', 'json')
            ->addActionContext('delete-show-template', 'json')
            ->initContext();

        $this->sched_sess = new Zend_Session_Namespace('schedule');
    }

    public function indexAction()
    {
        // Embed the schedule in our page response so we don't have to make an AJAX request to get this data after the page load.
        $scheduleController = new ScheduleController($this->getRequest(), $this->getResponse());
        $scheduleController->eventFeedPreloadAction();
        $events = json_encode($scheduleController->view->events);

        $this->view->headScript()->appendScript(
            "var calendarPref = {};\n" .
                'calendarPref.weekStart = ' . Application_Model_Preference::GetWeekStartDay() . ";\n" .
                'calendarPref.timestamp = ' . time() . ";\n" .
                'calendarPref.timezoneOffset = ' . Application_Common_DateHelper::getUserTimezoneOffset() . ";\n" .
                "calendarPref.timeScale = '" . Application_Model_Preference::GetCalendarTimeScale() . "';\n" .
                'calendarPref.timeInterval = ' . Application_Model_Preference::GetCalendarTimeInterval() . ";\n" .
                'calendarPref.weekStartDay = ' . Application_Model_Preference::GetWeekStartDay() . ";\n" .
                "var calendarEvents = {$events};"
        );

        $this->view->headScript()->appendFile(Assets::url('js/contextmenu/jquery.contextMenu.js'), 'text/javascript');

        // full-calendar-functions.js requires this variable, so that datePicker widget can be offset to server time instead of client time
        // this should be as a default, however with our new drop down timezone changing for shows, we should reset this offset then??
        $this->view->headScript()->appendScript('var timezoneOffset = ' . Application_Common_DateHelper::getStationTimezoneOffset() . '; //in seconds');
        // set offset to ensure it loads last
        $this->view->headScript()->offsetSetFile(90, Assets::url('js/airtime/schedule/full-calendar-functions.js'), 'text/javascript');

        // RASTATIME 2026-09-17 (JS-modernization): FullCalendar 6 (vendored,
        // vanilla) is the only Schedule calendar - the patched FC1.5 fork and
        // its ?fc6 rollback flag were removed after the operator's maturity
        // signal (FC6 default since 2026-06-01; fork removed 2026-09-17).
        $this->view->headScript()->appendFile(Assets::url('js/libs/fullcalendar/index.global.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/fullcalendar/locales-all.global.min.js'), 'text/javascript');
        $this->view->headScript()->offsetSetFile(110, Assets::url('js/airtime/schedule/schedule-fc6.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/timepicker/jquery.ui.timepicker.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/colorpicker/js/colorpicker.js'), 'text/javascript');

        // This block needs to be added before the add-show.js script
        $this->view->headScript()->appendFile(Assets::url('js/libs/dayjs.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/utc.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/timezone.min.js'), 'text/javascript');

        $this->view->headScript()->appendFile(Assets::url('js/airtime/schedule/add-show.js'), 'text/javascript');
        $this->view->headScript()->offsetSetFile(100, Assets::url('js/airtime/schedule/schedule.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/blockui/jquery.blockUI.js'), 'text/javascript');

        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.ui.timepicker.css'));
        // RASTATIME 2026-09-17: schedule-fc6.css is the FC6 dark theme; the
        // FC1.5 fullcalendar.css went with the fork.
        $this->view->headLink()->appendStylesheet(Assets::url('css/schedule-fc6.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/colorpicker/css/colorpicker.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/add-show.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.contextMenu.css'));

        // Start Show builder JS/CSS requirements
        $headScript = $this->view->headScript();
        AirtimeTableView::injectTableJavaScriptDependencies($headScript);

        $this->view->headScript()->appendFile(Assets::url('js/airtime/utilities/utilities.js'), 'text/javascript');

        $this->view->headScript()->appendFile(Assets::url('js/airtime/buttons/buttons.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/library/events/library_showbuilder.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/library/library.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/showbuilder/builder.js'), 'text/javascript');

        $this->view->headLink()->appendStylesheet(Assets::url('css/media_library.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.contextMenu.css'));
        AirtimeTableView::injectTableCssDependencies($this->view->headLink());
        $this->view->headLink()->appendStylesheet(Assets::url('css/showbuilder.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/dashboard.css'));
        // End Show builder JS/CSS requirements

        $this->createShowFormAction(true);

        $user = Application_Model_User::getCurrentUser();
        if ($user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER])) {
            $this->view->preloadShowForm = true;
        }

        $this->view->addNewShow = true;
    }

    public function eventFeedAction()
    {
        $service_user = new Application_Service_UserService();
        $currentUser = $service_user->getCurrentUser();

        $userTimezone = new DateTimeZone(Application_Model_Preference::GetUserTimezone());

        $start = new DateTime($this->_getParam('start', null), $userTimezone);
        $start->setTimezone(new DateTimeZone('UTC'));
        $end = new DateTime($this->_getParam('end', null), $userTimezone);
        $end->setTimezone(new DateTimeZone('UTC'));

        $events = &Application_Model_Show::getFullCalendarEvents(
            $start,
            $end,
            $currentUser->isAdminOrPM()
        );

        $this->view->events = $events;
    }

    public function eventFeedPreloadAction()
    {
        $userInfo = Zend_Auth::getInstance()->getStorage()->read();
        $user = new Application_Model_User($userInfo->id);
        $editable = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);

        $calendar_interval = Application_Model_Preference::GetCalendarTimeScale();
        if ($calendar_interval == 'agendaDay') {
            [$start, $end] = Application_Model_Show::getStartEndCurrentDayView();
        } elseif ($calendar_interval == 'agendaWeek') {
            [$start, $end] = Application_Model_Show::getStartEndCurrentWeekView();
        } elseif ($calendar_interval == 'month') {
            [$start, $end] = Application_Model_Show::getStartEndCurrentMonthPlusView();
        } else {
            Logging::error("Invalid Calendar Interval '{$calendar_interval}'");
        }

        $events = &Application_Model_Show::getFullCalendarEvents($start, $end, $editable);
        $this->view->events = $events;
    }

    public function getCurrentShowAction()
    {
        $currentShow = Application_Model_Show::getCurrentShow();
        if (!empty($currentShow)) {
            $this->view->si_id = $currentShow[0]['instance_id'];
            $this->view->current_show = true;
        } else {
            $this->view->current_show = false;
        }
    }

    public function moveShowAction()
    {
        $deltaDay = $this->_getParam('day');
        $deltaMin = $this->_getParam('min');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/move-show';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $this->_getParam('showInstanceId');
        $log_vars['params']['delta day'] = $deltaDay;
        $log_vars['params']['delta minute'] = $deltaMin;
        Logging::info($log_vars);

        try {
            $service_calendar = new Application_Service_CalendarService(
                $this->_getParam('showInstanceId')
            );
        } catch (Exception $e) {
            $this->view->show_error = true;

            return false;
        }

        $error = $service_calendar->moveShow($deltaDay, $deltaMin);
        if (isset($error)) {
            $this->view->error = $error;
        }
    }

    public function resizeShowAction()
    {
        $deltaDay = $this->_getParam('day');
        $deltaMin = $this->_getParam('min');
        $showId = $this->_getParam('showId');
        $instanceId = $this->_getParam('instanceId');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/resize-show';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $instanceId;
        $log_vars['params']['delta day'] = $deltaDay;
        $log_vars['params']['delta minute'] = $deltaMin;
        Logging::info($log_vars);

        $userInfo = Zend_Auth::getInstance()->getStorage()->read();
        $user = new Application_Model_User($userInfo->id);

        if ($user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER])) {
            try {
                $show = new Application_Model_Show($showId);
            } catch (Exception $e) {
                $this->view->show_error = true;

                return false;
            }
            $error = $show->resizeShow($deltaDay, $deltaMin, $instanceId);
        }

        if (isset($error)) {
            $this->view->error = $error;
        }
    }

    public function deleteShowInstanceAction()
    {
        $instanceId = $this->_getParam('id');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/delete-show-instance';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $instanceId;
        Logging::info($log_vars);

        $service_show = new Application_Service_ShowService();
        $showId = $service_show->deleteShow($instanceId, true);

        if (!$showId) {
            $this->view->show_error = true;
        }
        $this->view->show_id = $showId;
    }

    public function makeContextMenuAction()
    {
        $instanceId = $this->_getParam('instanceId');

        $service_calendar = new Application_Service_CalendarService($instanceId);

        $this->view->items = $service_calendar->makeContextMenu();
    }

    public function clearShowAction()
    {
        $instanceId = $this->_getParam('id');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/clear-show';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $instanceId;
        Logging::info($log_vars);

        $service_scheduler = new Application_Service_SchedulerService();

        if (!$service_scheduler->emptyShowContent($instanceId)) {
            $this->view->show_error = true;

            return false;
        }
    }

    /** This is a nasty hack to let us embed the the data the dashboard needs into the HTML response for each page.
     *  This was originally loaded AFTER page load by AJAX, which is needlessly slow. This should have been templated in.
     */
    public static function printCurrentPlaylistForEmbedding()
    {
        // RASTATIME 2026-09-30 - the data, not the action: the action sends
        // its JSON and ends the request, which is fine for the dashboard's
        // poll but not in the middle of a page.
        echo json_encode(self::currentPlaylistData());
    }

    public function getCurrentPlaylistAction()
    {
        // RASTATIME 2026-09-30 - the JSON is sent here (the AjaxContext only
        // switches for X-Requested-With calls; the view script that echoed the
        // array for every other call is gone).
        $this->_helper->json->sendJson(self::currentPlaylistData());
    }

    /**
     * The master panel's data: the play order around now, the source and
     * switch states, the current show's name.  Served by
     * getCurrentPlaylistAction() (the dashboard poll) and embedded in every
     * page by printCurrentPlaylistForEmbedding().
     *
     * @return array{entries: array, source_status: array, switch_status: array, show_name: string}
     */
    public static function currentPlaylistData()
    {
        $range = Application_Model_Schedule::GetPlayOrderRangeOld();

        $show = Application_Model_Show::getCurrentShow();

        // Convert all UTC times to localtime before sending back to user.
        $range['schedulerTime'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['schedulerTime']);

        if (isset($range['previous'])) {
            $range['previous']['starts'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['previous']['starts']);
            $range['previous']['ends'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['previous']['ends']);
        }
        if (isset($range['current'])) {
            if (isset($range['current']['metadata'])) {
                $get_artwork = FileDataHelper::getArtworkData($range['current']['metadata']['artwork'], 256);
                $range['current']['metadata']['artwork_data'] = $get_artwork;
            }
            $range['current']['starts'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['current']['starts']);
            $range['current']['ends'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['current']['ends']);
        }
        if (isset($range['next'])) {
            $range['next']['starts'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['next']['starts']);
            $range['next']['ends'] = Application_Common_DateHelper::UTCStringToUserTimezoneString($range['next']['ends']);
        }

        Application_Common_DateHelper::convertTimestamps(
            $range['currentShow'],
            ['starts', 'ends', 'start_timestamp', 'end_timestamp'],
            'user'
        );
        Application_Common_DateHelper::convertTimestamps(
            $range['nextShow'],
            ['starts', 'ends', 'start_timestamp', 'end_timestamp'],
            'user'
        );

        // TODO: Add timezone and timezoneOffset back into the ApiController's results.
        $range['timezone'] = Application_Common_DateHelper::getUserTimezoneAbbreviation();
        $range['timezoneOffset'] = Application_Common_DateHelper::getUserTimezoneOffset();

        $source_status = [];
        $switch_status = [];
        $live_dj = Application_Model_Preference::GetSourceStatus('live_dj');
        $master_dj = Application_Model_Preference::GetSourceStatus('master_dj');

        $scheduled_play_switch = Application_Model_Preference::GetSourceSwitchStatus('scheduled_play');
        $live_dj_switch = Application_Model_Preference::GetSourceSwitchStatus('live_dj');
        $master_dj_switch = Application_Model_Preference::GetSourceSwitchStatus('master_dj');

        // might not be the correct place to implement this but for now let's just do it here
        $source_status['live_dj_source'] = $live_dj;
        $source_status['master_dj_source'] = $master_dj;

        $switch_status['live_dj_source'] = $live_dj_switch;
        $switch_status['master_dj_source'] = $master_dj_switch;
        $switch_status['scheduled_play'] = $scheduled_play_switch;

        return [
            'entries' => $range,
            'source_status' => $source_status,
            'switch_status' => $switch_status,
            'show_name' => isset($show[0]) ? $show[0]['name'] : '',
        ];
    }

    public function showContentDialogAction()
    {
        $showInstanceId = $this->_getParam('id');

        try {
            $show = new Application_Model_ShowInstance($showInstanceId);
        } catch (Exception $e) {
            $this->view->show_error = true;

            return false;
        }

        $originalShowId = $show->isRebroadcast();
        if (!is_null($originalShowId)) {
            try {
                $originalShow = new Application_Model_ShowInstance($originalShowId);
            } catch (Exception $e) {
                $this->view->show_error = true;

                return false;
            }
            $originalShowName = $originalShow->getName();
            $originalShowStart = $originalShow->getShowInstanceStart();

            // convert from UTC to user's timezone for display.
            $displayTimeZone = new DateTimeZone(Application_Model_Preference::GetTimezone());
            $originalDateTime = new DateTime($originalShowStart, new DateTimeZone('UTC'));
            $originalDateTime->setTimezone($displayTimeZone);

            $this->view->additionalShowInfo =
                sprintf(
                    _('Rebroadcast of show %s from %s at %s'),
                    $originalShowName,
                    $originalDateTime->format('l, F jS'),
                    $originalDateTime->format('G:i')
                );
        }
        // RASTATIME 2026-10-18 - "Repeat of show": where the content came from
        $filledFrom = Application_Service_RepeatFillService::filledFrom($showInstanceId);
        if ($filledFrom !== null) {
            $displayTimeZone = new DateTimeZone(Application_Model_Preference::GetTimezone());
            $srcStart = clone $filledFrom['starts'];
            $srcStart->setTimezone($displayTimeZone);
            $info = sprintf(
                _('Repeat of show %s from %s at %s'),
                $filledFrom['name'],
                $srcStart->format('l, F jS'),
                $srcStart->format('G:i')
            );
            if ($filledFrom['skipped'] > 0) {
                $info .= ' ' . sprintf(_('(%d items of the source were left out: file missing)'), $filledFrom['skipped']);
            }
            $this->view->additionalShowInfo = $info;
        }
        $this->view->showLength = $show->getShowLength();
        $this->view->timeFilled = $show->getTimeScheduled();
        $this->view->percentFilled = $show->getPercentScheduled();
        $this->view->showContent = $show->getShowListContent();
        $this->view->dialog = $this->view->render('schedule/show-content-dialog.phtml');
        $this->view->showTitle = htmlspecialchars($show->getName() ?? '');
        unset($this->view->showContent);
    }

    /**
     * RASTATIME 2026-10-16 - teaser automation stage 2: the calendar's
     * "Teasers" dialog of a show (GET id = show instance).  Lists the
     * jingles linked to the show with their type; the inline script of the
     * view links / unlinks / retypes through the three JSON actions below.
     */
    public function teaserDialogAction()
    {
        $instanceId = (int) $this->_getParam('id');

        try {
            $instance = new Application_Model_ShowInstance($instanceId);
            $showId = (int) $instance->getShowId();
            $show = new Application_Model_Show($showId);
        } catch (Exception $e) {
            $this->view->show_error = true;

            return;
        }
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }
        $this->view->csrf = $ns->authtoken;
        $this->view->showId = $showId;
        $this->view->showName = $show->getName();
        $this->view->canEdit = Application_Model_User::getCurrentUser()->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);
        $this->view->teasers = Application_Model_StoredFile::teasersOfShow($showId);
        $this->view->typeLabels = Application_Model_StoredFile::teaserTypeLabels();
        $this->view->ready = Application_Model_StoredFile::teaserColumnsReady();
        $this->view->dialog = $this->view->render('schedule/teaser-dialog.phtml');
        $this->view->showTitle = htmlspecialchars($show->getName() ?? '');
        unset($this->view->teasers, $this->view->typeLabels);
    }

    /** RASTATIME 2026-10-16 - stage 2: admin / PM, POST, CSRF; JSON {ok, error}. */
    private function teaserMutationAllowed()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);

            return false;
        }
        if (!Application_Model_User::getCurrentUser()->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER])) {
            $this->getResponse()->setHttpResponseCode(403);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'forbidden']);

            return false;
        }
        if (!SecurityHelper::verifyCSRFToken($this->_getParam('csrf_token'))) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'csrf']);

            return false;
        }

        return true;
    }

    public function teaserLinkAction()
    {
        if (!$this->teaserMutationAllowed()) {
            return;
        }
        $ok = Application_Model_StoredFile::teaserLink(
            (int) $this->_getParam('file_id'),
            (int) $this->_getParam('show_id'),
            (string) $this->_getParam('type', '')
        );
        $this->_helper->json->sendJson(['ok' => $ok, 'error' => $ok ? null : 'not-found']);
    }

    public function teaserUnlinkAction()
    {
        if (!$this->teaserMutationAllowed()) {
            return;
        }
        $ok = Application_Model_StoredFile::teaserUnlink((int) $this->_getParam('file_id'), (int) $this->_getParam('show_id'));
        $this->_helper->json->sendJson(['ok' => $ok]);
    }

    /** GET q, show_id -> JSON list of files not yet linked to the show. */
    public function teaserSearchAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $rows = Application_Model_StoredFile::teaserSearch((string) $this->_getParam('q', ''), (int) $this->_getParam('show_id'));
        $this->_helper->json->sendJson(['ok' => true, 'files' => SecurityHelper::htmlescape_recursive($rows)]);
    }

    public function populateRepeatingShowInstanceFormAction()
    {
        $showId = $this->_getParam('showId');
        $instanceId = $this->_getParam('instanceId');
        $service_showForm = new Application_Service_ShowFormService($showId, $instanceId);

        $forms = $this->createShowFormAction();

        $service_showForm->delegateShowInstanceFormPopulation($forms);

        $this->view->addNewShow = false;
        $this->view->action = 'edit-repeating-show-instance';
        $this->view->newForm = $this->view->render('schedule/add-show-form.phtml');
    }

    public function populateShowFormAction()
    {
        $service_user = new Application_Service_UserService();
        $currentUser = $service_user->getCurrentUser();

        $showId = $this->_getParam('showId');
        $instanceId = $this->_getParam('instanceId');
        $service_showForm = new Application_Service_ShowFormService($showId, $instanceId);

        $isAdminOrPM = $currentUser->isAdminOrPM();

        $forms = $this->createShowFormAction();

        $service_showForm->delegateShowFormPopulation($forms);

        if (!$isAdminOrPM) {
            foreach ($forms as $form) {
                $form->disable();
            }
        }

        $this->view->action = 'edit-show';
        $this->view->newForm = $this->view->render('schedule/add-show-form.phtml');
        $this->view->entries = 5;
    }

    public function getFormAction()
    {
        $service_user = new Application_Service_UserService();
        $currentUser = $service_user->getCurrentUser();

        if ($currentUser->isAdminOrPM()) {
            $this->createShowFormAction(true);
            $this->view->addNewShow = true;
            $this->view->form = $this->view->render('schedule/add-show-form.phtml');
        }
    }

    public function editRepeatingShowInstanceAction()
    {
        $js = $this->_getParam('data');
        $data = [];

        // need to convert from serialized jQuery array.
        foreach ($js as $j) {
            $data[$j['name']] = $j['value'];
        }

        $data['add_show_hosts'] = $this->_getParam('hosts');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/edit-repeating-show-instance';
        $log_vars['params'] = [];
        $log_vars['params']['form_data'] = $data;
        Logging::info($log_vars);

        $service_showForm = new Application_Service_ShowFormService(
            $data['add_show_id'],
            $data['add_show_instance_id']
        );
        $service_show = new Application_Service_ShowService(null, $data);

        $forms = $this->createShowFormAction();

        [$data, $validateStartDate, $validateStartTime, $originalShowStartDateTime] =
            $service_showForm->preEditShowValidationCheck($data);

        if ($service_showForm->validateShowForms(
            $forms,
            $data,
            $validateStartDate,
            $originalShowStartDateTime,
            true,
            $data['add_show_instance_id']
        )) {
            $service_show->editRepeatingShowInstance($data);

            $this->view->addNewShow = true;
            $this->view->newForm = $this->view->render('schedule/add-show-form.phtml');
        } else {
            if (!$validateStartDate) {
                $this->view->when->getElement('add_show_start_date')->setOptions(['disabled' => true]);
            }
            if (!$validateStartTime) {
                $this->view->when->getElement('add_show_start_time')->setOptions(['disabled' => true]);
            }
            // RASTATIME 2026-05-17 - Phase B: record-per-show semantic
            // (Section 23.13).  Upstream disabled the checkbox here on
            // validation failure to prevent toggling the Liquidsoap
            // linein-recording mode mid-show.  No longer applies — the
            // output-tap recorder is a parallel concern and can be
            // toggled freely.
            $this->view->addNewShow = false;
            $this->view->action = 'edit-repeating-show-instance';
            $this->view->form = $this->view->render('schedule/add-show-form.phtml');
        }
    }

    public function editShowAction()
    {
        $js = $this->_getParam('data');
        $data = [];

        // need to convert from serialized jQuery array.
        foreach ($js as $j) {
            $data[$j['name']] = $j['value'];
        }

        $service_showForm = new Application_Service_ShowFormService(
            $data['add_show_id']
        );
        $service_show = new Application_Service_ShowService(null, $data, true);

        // TODO: move this to js
        $data['add_show_hosts'] = $this->_getParam('hosts');
        $data['add_show_day_check'] = $this->_getParam('days');
        // RASTATIME 2026-10-15 - month boxes of a monthly repeat (empty = every month)
        $data['add_show_month_check'] = $this->_getParam('months', []);

        if ($data['add_show_day_check'] == '') {
            $data['add_show_day_check'] = null;
        }

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/edit-show';
        $log_vars['params'] = [];
        $log_vars['params']['form_data'] = $data;
        Logging::info($log_vars);

        $forms = $this->createShowFormAction();

        [$data, $validateStartDate, $validateStartTime, $originalShowStartDateTime] =
            $service_showForm->preEditShowValidationCheck($data);

        if ($service_showForm->validateShowForms(
            $forms,
            $data,
            $validateStartDate,
            $originalShowStartDateTime,
            true,
            $data['add_show_instance_id']
        )) {
            // Get the show ID from the show service to pass as a parameter to the RESTful ShowImageController
            $this->view->showId = $service_show->addUpdateShow($data);

            $this->view->addNewShow = true;
            $this->view->newForm = $this->view->render('schedule/add-show-form.phtml');
        } else {
            if (!$validateStartDate) {
                $this->view->when->getElement('add_show_start_date')->setOptions(['disabled' => true]);
            }
            if (!$validateStartTime) {
                $this->view->when->getElement('add_show_start_time')->setOptions(['disabled' => true]);
            }
            // $this->view->rr->getElement('add_show_record')->setOptions(array('disabled' => true));

            $this->view->addNewShow = false;
            $this->view->action = 'edit-show';
            $this->view->form = $this->view->render('schedule/add-show-form.phtml');
        }
    }

    public function addShowAction()
    {
        $service_showForm = new Application_Service_ShowFormService(null);

        $js = $this->_getParam('data');
        $data = [];

        // need to convert from serialized jQuery array.
        foreach ($js as $j) {
            $data[$j['name']] = $j['value'];
        }

        $service_show = new Application_Service_ShowService(null, $data);

        // TODO: move this to js
        $data['add_show_hosts'] = $this->_getParam('hosts');
        $data['add_show_day_check'] = $this->_getParam('days');
        // RASTATIME 2026-10-15 - month boxes of a monthly repeat (empty = every month)
        $data['add_show_month_check'] = $this->_getParam('months', []);

        if ($data['add_show_day_check'] == '') {
            $data['add_show_day_check'] = null;
        }

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/add-show';
        $log_vars['params'] = [];
        $log_vars['params']['form_data'] = $data;
        Logging::info($log_vars);

        $forms = $this->createShowFormAction();

        $this->view->addNewShow = true;

        if ($data['add_show_start_now'] == 'now') {
            // have to use the timezone the user has entered in the form to check past/present
            $showTimezone = new DateTimeZone($data['add_show_timezone']);
            $nowDateTime = new DateTime('now', $showTimezone);
            // $showStartDateTime = new DateTime($start_time, $showTimezone);
            // $showEndDateTime = new DateTime($end_time, $showTimezone);

            $data['add_show_start_time'] = $nowDateTime->format('H:i');
            $data['add_show_start_date'] = $nowDateTime->format('Y-m-d');
        }

        if ($service_showForm->validateShowForms($forms, $data)) {
            // Get the show ID from the show service to pass as a parameter to the RESTful ShowImageController
            $this->view->showId = $service_show->addUpdateShow($data);

            // send new show forms to the user
            $this->createShowFormAction(true);
            $this->view->newForm = $this->view->render('schedule/add-show-form.phtml');

            Logging::debug('Show creation succeeded');
        } else {
            $this->view->form = $this->view->render('schedule/add-show-form.phtml');
            Logging::debug('Show creation failed');
        }
    }

    public function createShowFormAction($populateDefaults = false)
    {
        $service_showForm = new Application_Service_ShowFormService();

        $forms = $service_showForm->createShowForms();

        // populate forms with default values
        if ($populateDefaults) {
            $service_showForm->populateNewShowForms(
                $forms['what'],
                $forms['when'],
                $forms['repeats']
            );
        }

        $this->view->what = $forms['what'];
        $this->view->autoplaylist = $forms['autoplaylist'];
        $this->view->when = $forms['when'];
        $this->view->repeats = $forms['repeats'];
        $this->view->live = $forms['live'];
        $this->view->rr = $forms['record'];
        $this->view->absoluteRebroadcast = $forms['abs_rebroadcast'];
        $this->view->rebroadcast = $forms['rebroadcast'];
        $this->view->who = $forms['who'];
        $this->view->style = $forms['style'];

        return $forms;
    }

    public function deleteShowAction()
    {
        $instanceId = $this->_getParam('id');

        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/delete-show';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $instanceId;
        Logging::info($log_vars);

        $service_show = new Application_Service_ShowService();
        $showId = $service_show->deleteShow($instanceId);

        if (!$showId) {
            $this->view->show_error = true;
        }
        $this->view->show_id = $showId;
    }

    public function cancelCurrentShowAction()
    {
        $log_vars = [];
        $log_vars['url'] = $_SERVER['HTTP_HOST'];
        $log_vars['action'] = 'schedule/cancel-current-show';
        $log_vars['params'] = [];
        $log_vars['params']['instance id'] = $this->_getParam('id');
        Logging::info($log_vars);

        $user = Application_Model_User::getCurrentUser();

        if ($user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER])) {
            $id = $this->_getParam('id');

            try {
                $scheduler = new Application_Model_Scheduler();
                $scheduler->cancelShow($id);
                Application_Model_StoredFile::updatePastFilesIsScheduled();
                // RASTATIME: legacy SendMessageToPypo('disconnect_source')
                // notified Liquidsoap-era Pypo, which we no longer run.
                // Push the kick directly to the playout's HTTP listener
                // so Icecast disconnects the Show DJ immediately — the
                // playout's own schedule-refresh-based cancel path is
                // unreliable for shows without scheduled tracks (live-
                // DJ-only slots), so we do not depend on it here.
                Application_Model_RabbitMq::NotifyDisconnectSource('live_dj');
            } catch (Exception $e) {
                $this->view->error = $e->getMessage();
                Logging::info($e->getMessage());
            }
        }
    }

    public function contentContextMenuAction()
    {
        $id = $this->_getParam('id');

        $params = '/format/json/id/#id#/';

        $paramsPop = str_replace('#id#', $id, $params);

        // added for download
        $id = $this->_getParam('id');

        $file_id = $this->_getParam('id', null);
        $file = Application_Model_StoredFile::RecallById($file_id);

        $baseUrl = $this->getRequest()->getBaseUrl();
        $url = $file->getRelativeFileUrl($baseUrl) . 'download/true';
        $menu = [];
        $menu[] = [
            'action' => ['type' => 'gourl', 'url' => $url],
            'title' => _('Download'),
        ];

        // returns format jjmenu is looking for.
        $this->_helper->json->sendJson($menu);
    }

    /**
     * Sets the user specific preference for which time scale to use in Calendar.
     * This is only being used by schedule.js at the moment.
     */
    public function setTimeScaleAction()
    {
        Application_Model_Preference::SetCalendarTimeScale($this->_getParam('timeScale'));
    }

    /**
     * Sets the user specific preference for which time interval to use in Calendar.
     * This is only being used by schedule.js at the moment.
     */
    public function setTimeIntervalAction()
    {
        Application_Model_Preference::SetCalendarTimeInterval($this->_getParam('timeInterval'));
    }

    public function calculateDurationAction()
    {
        $start = $this->_getParam('startTime');
        $end = $this->_getParam('endTime');
        $timezone = $this->_getParam('timezone');

        $service_showForm = new Application_Service_ShowFormService();
        $result = $service_showForm->calculateDuration($start, $end, $timezone);

        echo Zend_Json::encode($result);

        exit;
    }

    public function updateFutureIsScheduledAction()
    {
        $schedId = $this->_getParam('schedId');

        $scheduleService = new Application_Service_SchedulerService();
        $redrawLibTable = $scheduleService->updateFutureIsScheduled($schedId, false);

        $this->_helper->json->sendJson(['redrawLibTable' => $redrawLibTable]);
    }

    public function localizeStartEndTimeAction()
    {
        $newTimezone = $this->_getParam('newTimezone');
        $oldTimezone = $this->_getParam('oldTimezone');
        $localTime = [];

        $localTime['start'] = Application_Service_ShowFormService::localizeDateTime(
            $this->_getParam('startDate'),
            $this->_getParam('startTime'),
            $newTimezone,
            $oldTimezone
        );

        $localTime['end'] = Application_Service_ShowFormService::localizeDateTime(
            $this->_getParam('endDate'),
            $this->_getParam('endTime'),
            $newTimezone,
            $oldTimezone
        );

        $this->_helper->json->sendJson($localTime);
    }

    // ------------------------------------------------------------------
    // RASTATIME 2026-05-19 — Show-Template feature (Section 23.16)
    //
    // Five JSON actions consumed by the New-Show dialog and the
    // Settings → "Show Templates" page.  All routed through
    // Application_Service_ShowTemplateService; this controller is a
    // thin parameter-marshaller and JSON-envelope wrapper.
    // ------------------------------------------------------------------

    /**
     * GET /Schedule/list-show-templates
     *   Lightweight list of [id, name] for the New-Show dropdown.
     *   Also used by the Settings page (which then GETs each one
     *   individually for editing if needed).
     */
    public function listShowTemplatesAction()
    {
        try {
            $rows = Application_Service_ShowTemplateService::getAllForListing();
            $this->_helper->json->sendJson(['templates' => $rows]);
        } catch (Throwable $exc) {
            Logging::error('list-show-templates: ' . $exc->getMessage());
            $this->_helper->json->sendJson(['error' => $exc->getMessage()]);
        }
    }

    /**
     * GET /Schedule/get-show-template/id/<n>
     *   Returns one template's full template_data JSON, ready for
     *   the front-end populate-form helper to apply.
     */
    public function getShowTemplateAction()
    {
        try {
            $id = (int) $this->_getParam('id', 0);
            $tpl = Application_Service_ShowTemplateService::getTemplateById($id);
            if ($tpl === null) {
                $this->_helper->json->sendJson(['error' => _('Template not found.')]);
                return;
            }
            $this->_helper->json->sendJson(['template' => $tpl]);
        } catch (Throwable $exc) {
            Logging::error('get-show-template: ' . $exc->getMessage());
            $this->_helper->json->sendJson(['error' => $exc->getMessage()]);
        }
    }

    /**
     * POST /Schedule/save-show-template
     *   Save (or overwrite) a template from an in-flight new-show
     *   form payload.  Same {name:value} array as the editShowAction
     *   accepts; the service whitelist controls what survives.
     *
     *   Body params:
     *     - data       (jQuery serializeArray of the show form)
     *     - hosts      (array of cc_subjs.id from the Who form)
     *     - days       (array of day-of-week indices from When)
     *     - overwrite  ("1" to overwrite a same-named existing one)
     */
    public function saveShowTemplateAction()
    {
        try {
            $js = $this->_getParam('data');
            $data = [];
            foreach ($js as $j) {
                $data[$j['name']] = $j['value'];
            }
            $data['add_show_hosts'] = $this->_getParam('hosts', []);
            $data['add_show_day_check'] = $this->_getParam('days', []);
            $data['add_show_month_check'] = $this->_getParam('months', []);
            $overwrite = ((int) $this->_getParam('overwrite', 0)) === 1;

            $id = Application_Service_ShowTemplateService::saveFromShowData(
                $data, $overwrite
            );
            $this->_helper->json->sendJson([
                'id' => $id,
                'name' => $data['add_show_name'] ?? '',
            ]);
        } catch (Throwable $exc) {
            // Friendly status for the "already exists" branch so the
            // front-end can prompt the operator to overwrite.
            $msg = $exc->getMessage();
            $conflict = (strpos($msg, 'already exists') !== false);
            Logging::warn('save-show-template: ' . $msg);
            $this->_helper->json->sendJson([
                'error' => $msg,
                'conflict' => $conflict,
            ]);
        }
    }

    /**
     * POST /Schedule/rename-show-template
     *   Body params:
     *     - id
     *     - name (new name)
     */
    public function renameShowTemplateAction()
    {
        try {
            $id = (int) $this->_getParam('id', 0);
            $newName = (string) $this->_getParam('name', '');
            Application_Service_ShowTemplateService::renameTemplate($id, $newName);
            $this->_helper->json->sendJson(['id' => $id, 'name' => $newName]);
        } catch (Throwable $exc) {
            Logging::warn('rename-show-template: ' . $exc->getMessage());
            $this->_helper->json->sendJson(['error' => $exc->getMessage()]);
        }
    }

    /**
     * POST /Schedule/delete-show-template/id/<n>
     */
    public function deleteShowTemplateAction()
    {
        try {
            $id = (int) $this->_getParam('id', 0);
            Application_Service_ShowTemplateService::deleteTemplate($id);
            $this->_helper->json->sendJson(['ok' => true]);
        } catch (Throwable $exc) {
            Logging::warn('delete-show-template: ' . $exc->getMessage());
            $this->_helper->json->sendJson(['error' => $exc->getMessage()]);
        }
    }
}
