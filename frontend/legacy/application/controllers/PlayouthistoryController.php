<?php

class PlayouthistoryController extends Zend_Controller_Action
{
    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext
            ->addActionContext('file-history-feed', 'json')
            ->addActionContext('item-history-feed', 'json')
            ->addActionContext('show-history-feed', 'json')
            ->addActionContext('edit-file-item', 'json')
            ->addActionContext('create-list-item', 'json')
            ->addActionContext('edit-list-item', 'json')
            ->addActionContext('delete-list-item', 'json')
            ->addActionContext('delete-list-items', 'json')
            ->addActionContext('update-list-item', 'json')
            ->addActionContext('update-file-item', 'json')
            ->initContext();
    }

    /**
     * RASTATIME 2026-10-25 (role audit R9) - Program Managers and Admins
     * edit every history entry; DJs create, edit and delete the entries of
     * the shows they host (operator), the per-file summary across all
     * shows stays with Program Managers and Admins.  HistoryService's own
     * check was commented out upstream - before, every DJ changed anything.
     */
    private const EDIT_ACTIONS = [
        'edit-file-item', 'create-list-item', 'edit-list-item', 'delete-list-item',
        'delete-list-items', 'update-list-item', 'update-file-item',
    ];

    public function preDispatch()
    {
        $action = $this->getRequest()->getActionName();
        if (!in_array($action, self::EDIT_ACTIONS, true)) {
            return;
        }
        $user = Application_Model_User::getCurrentUser();
        if ($user !== null && ($user->isAdminOrPM() || ($user->isHost() && $this->hostsTarget($user, $action)))) {
            return;
        }

        Logging::warn(sprintf('playouthistory/%s: user %s refused', $action, $user !== null ? $user->getId() : '-'));

        throw new Zend_Controller_Action_Exception('only the show\'s hosts, Program Managers and Admins may change this entry', 403);
    }

    /** Does the DJ host the show(s) the request touches? */
    private function hostsTarget(Application_Model_User $user, string $action): bool
    {
        $request = $this->getRequest();

        switch ($action) {
            case 'edit-list-item':     // the dialog; without an id it is a new entry
                $id = $request->getParam('id');

                return $id === null || $id === '' || self::hostsHistoryItems($user, [$id]);

            case 'create-list-item':
                return self::hostsInstance($user, $request->getParam('instance_id'));

            case 'update-list-item':   // the entry and its (possibly new) show
                return self::hostsHistoryItems($user, [$request->getParam('his_item_id')])
                    && self::hostsInstance($user, $request->getParam('instance_id'));

            case 'delete-list-item':
                return self::hostsHistoryItems($user, [$request->getParam('id')]);

            case 'delete-list-items':
                return self::hostsHistoryItems($user, (array) $request->getParam('ids', []));
        }

        return false;   // the file summary spans all shows
    }

    private static function hostsInstance(Application_Model_User $user, $instanceId): bool
    {
        $instance = (int) $instanceId > 0 ? CcShowInstancesQuery::create()->findPk((int) $instanceId) : null;

        return $instance !== null && $user->isHostOfShow($instance->getDbShowId());
    }

    private static function hostsHistoryItems(Application_Model_User $user, array $ids): bool
    {
        $ids = array_unique(array_filter(array_map('intval', $ids)));
        if ($ids === []) {
            return false;
        }
        $records = CcPlayoutHistoryQuery::create()->findPks($ids);
        if (count($records) !== count($ids)) {
            return false;
        }
        foreach ($records as $record) {
            if (!self::hostsInstance($user, $record->getDbInstanceId())) {
                return false;
            }
        }

        return true;
    }

    public function indexAction()
    {
        $CC_CONFIG = Config::getConfig();
        $baseUrl = Config::getBasePath();

        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');

        [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($this->getRequest());

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

        $this->view->date_form = $form;

        $this->view->headScript()->appendFile(Assets::url('js/contextmenu/jquery.contextMenu.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/datatables-1.13/js/jquery.dataTables.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/datatables/plugin/dataTables.pluginAPI.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/datatables/plugin/dataTables.fnSetFilteringDelay.js'), 'text/javascript');

        $this->view->headScript()->appendFile(Assets::url('js/timepicker/jquery.ui.timepicker.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/bootstrap-datetime/bootstrap-datetimepicker.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/buttons/buttons.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/utilities/utilities.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/CSVexport.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/pdfmake.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/libs/vfs_fonts.min.js'), 'text/javascript');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/playouthistory/historytable.js'), 'text/javascript');

        $this->view->headLink()->appendStylesheet(Assets::url('css/bootstrap-datetimepicker.min.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.ui.timepicker.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/playouthistory.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/history_styles.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/jquery.contextMenu.css'));

        // set datatables columns for display of data.
        $historyService = new Application_Service_HistoryService();
        $columns = json_encode($historyService->getDatatablesLogSheetColumns());
        $script = "localStorage.setItem( 'datatables-historyitem-aoColumns', JSON.stringify({$columns}) ); ";

        $columns = json_encode($historyService->getDatatablesFileSummaryColumns());
        $script .= "localStorage.setItem( 'datatables-historyfile-aoColumns', JSON.stringify({$columns}) );";

        $user = Application_Model_User::getCurrentUser();
        $this->view->userType = $user->getType();
        // role audit R9 - edit tools for Program Managers, Admins and DJs
        // (a DJ's Show Summary lists only the shows they host)
        $script .= ' var rtHistoryCanEdit = ' . ($user->isAdminOrPM() || $user->isHost() ? 'true' : 'false') . ';';
        $this->view->headScript()->appendScript($script);
    }

    public function fileHistoryFeedAction()
    {
        try {
            $request = $this->getRequest();
            $params = $request->getParams();
            $instance = $request->getParam('instance_id', null);

            [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($request);

            $historyService = new Application_Service_HistoryService();
            $r = $historyService->getFileSummaryData($startsDT, $endsDT, $params);

            $this->view->sEcho = $r['sEcho'];
            $this->view->iTotalDisplayRecords = $r['iTotalDisplayRecords'];
            $this->view->iTotalRecords = $r['iTotalRecords'];
            $this->view->history = $r['history'];
            $this->view->history = SecurityHelper::htmlescape_recursive($this->view->history);
        } catch (Exception $e) {
            Logging::info($e);
            Logging::info($e->getMessage());
        }
    }

    public function itemHistoryFeedAction()
    {
        try {
            $request = $this->getRequest();
            $params = $request->getParams();
            $instance = $request->getParam('instance_id', null);

            [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($request);

            $historyService = new Application_Service_HistoryService();
            $r = $historyService->getPlayedItemData($startsDT, $endsDT, $params, $instance);

            $this->view->sEcho = $r['sEcho'];
            $this->view->iTotalDisplayRecords = $r['iTotalDisplayRecords'];
            $this->view->iTotalRecords = $r['iTotalRecords'];
            $this->view->history = $r['history'];
            $this->view->history = SecurityHelper::htmlescape_recursive($this->view->history);
        } catch (Exception $e) {
            Logging::info($e);
            Logging::info($e->getMessage());
        }
    }

    public function showHistoryFeedAction()
    {
        try {
            $request = $this->getRequest();
            $params = $request->getParams();
            $instance = $request->getParam('instance_id', null);

            [$startsDT, $endsDT] = Application_Common_HTTPHelper::getStartEndFromRequest($request);

            $historyService = new Application_Service_HistoryService();
            $shows = $historyService->getShowList($startsDT, $endsDT);
            $shows = SecurityHelper::htmlescape_recursive($shows);

            $this->_helper->json->sendJson($shows);
        } catch (Exception $e) {
            Logging::info($e);
            Logging::info($e->getMessage());
        }
    }

    public function editFileItemAction()
    {
        $file_id = $this->_getParam('id');

        $historyService = new Application_Service_HistoryService();
        $form = $historyService->makeHistoryFileForm($file_id);

        $this->view->form = $form;
        $this->view->dialog = $this->view->render('playouthistory/dialog.phtml');

        unset($this->view->form);
    }

    public function createListItemAction()
    {
        try {
            $request = $this->getRequest();
            $params = $request->getPost();
            Logging::info($params);

            $historyService = new Application_Service_HistoryService();
            $json = $historyService->createPlayedItem($params);

            if (isset($json['form'])) {
                $this->view->form = $json['form'];
                $json['form'] = $this->view->render('playouthistory/dialog.phtml');

                unset($this->view->form);
            }

            $this->_helper->json->sendJson($json);
        } catch (Exception $e) {
            Logging::info($e);
            Logging::info($e->getMessage());
        }
    }

    public function editListItemAction()
    {
        $id = $this->_getParam('id', null);

        $populate = isset($id) ? true : false;

        $historyService = new Application_Service_HistoryService();
        $form = $historyService->makeHistoryItemForm($id, $populate);

        $this->view->form = $form;
        $this->view->dialog = $this->view->render('playouthistory/dialog.phtml');

        unset($this->view->form);
    }

    public function deleteListItemAction()
    {
        $history_id = $this->_getParam('id');

        $historyService = new Application_Service_HistoryService();
        $historyService->deletePlayedItem($history_id);
    }

    public function deleteListItemsAction()
    {
        $history_ids = $this->_getParam('ids');

        $historyService = new Application_Service_HistoryService();
        $historyService->deletePlayedItems($history_ids);
    }

    public function updateListItemAction()
    {
        try {
            $request = $this->getRequest();
            $params = $request->getPost();
            Logging::info($params);

            $historyService = new Application_Service_HistoryService();
            $json = $historyService->editPlayedItem($params);

            if (isset($json['form'])) {
                $this->view->form = $json['form'];
                $json['form'] = $this->view->render('playouthistory/dialog.phtml');

                unset($this->view->form);
            }

            $this->_helper->json->sendJson($json);
        } catch (Exception $e) {
            Logging::info($e);
            Logging::info($e->getMessage());
        }
    }

    public function updateFileItemAction()
    {
        $request = $this->getRequest();
        $params = $request->getPost();
        Logging::info($params);

        $historyService = new Application_Service_HistoryService();
        $json = $historyService->editPlayedFile($params);

        $this->_helper->json->sendJson($json);
    }
}
