<?php

class UsersettingsController extends Zend_Controller_Action
{
    public function init()
    {
        // Initialize action controller here
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('get-now-playing-screen-settings', 'json')
            ->addActionContext('set-now-playing-screen-settings', 'json')
            ->addActionContext('get-library-datatable', 'json')
            ->addActionContext('set-library-datatable', 'json')
            // RASTATIME 2026-10-24 - visible columns per media type
            ->addActionContext('get-library-columns', 'json')
            ->addActionContext('set-library-columns', 'json')
            ->addActionContext('get-timeline-datatable', 'json')
            ->addActionContext('set-timeline-datatable', 'json')
            ->addActionContext('remindme', 'json')
            ->addActionContext('remindme-never', 'json')
            ->addActionContext('donotshowregistrationpopup', 'json')
            ->addActionContext('set-library-screen-settings', 'json')
            ->initContext();
    }

    public function setNowPlayingScreenSettingsAction()
    {
        $request = $this->getRequest();
        $settings = $request->getParam('settings');

        Application_Model_Preference::setNowPlayingScreenSettings($settings);
    }

    public function getNowPlayingScreenSettingsAction()
    {
        $data = Application_Model_Preference::getNowPlayingScreenSettings();
        if (!is_null($data)) {
            $this->view->settings = $data;
        }
    }

    // RASTATIME 2026-09-29 - the table layouts arrive as the DataTables state
    // JSON (see rtDatatableServerState() in common.js); table=builder selects
    // the library layout of the Schedule Tracks dialog.
    private function libraryDatatableKey()
    {
        return $this->getRequest()->getParam('table') === 'builder' ? 'library_builder' : 'library';
    }

    public function setLibraryDatatableAction()
    {
        $settings = $this->getRequest()->getParam('settings');

        $this->_helper->json(Application_Model_Preference::setDatatableSetting($this->libraryDatatableKey(), $settings));
    }

    public function getLibraryDatatableAction()
    {
        $this->_helper->json(Application_Model_Preference::getDatatableSetting($this->libraryDatatableKey()));
    }

    // RASTATIME 2026-10-24 - the library's visible columns per media type
    // ({type: {mDataProp: bool}}, see library.js applyColumnProfile); one
    // profile set for the dashboard, one for the Schedule Tracks dialog
    private function libraryColumnsKey()
    {
        return $this->getRequest()->getParam('table') === 'builder' ? 'library_builder_columns' : 'library_columns';
    }

    public function setLibraryColumnsAction()
    {
        $settings = $this->getRequest()->getParam('settings');

        $this->_helper->json(Application_Model_Preference::setDatatableSetting($this->libraryColumnsKey(), $settings));
    }

    public function getLibraryColumnsAction()
    {
        $this->_helper->json(Application_Model_Preference::getDatatableSetting($this->libraryColumnsKey()) ?? new stdClass());
    }

    public function setTimelineDatatableAction()
    {
        $settings = $this->getRequest()->getParam('settings');

        $this->_helper->json(Application_Model_Preference::setDatatableSetting('timeline', $settings));
    }

    public function getTimelineDatatableAction()
    {
        $this->_helper->json(Application_Model_Preference::getDatatableSetting('timeline'));
    }

    public function remindmeAction()
    {
        // unset session
        SessionHelper::reopenSessionForWriting();
        Zend_Session::namespaceUnset('referrer');
        Application_Model_Preference::SetRemindMeDate();
    }

    public function remindmeNeverAction()
    {
        SessionHelper::reopenSessionForWriting();
        Zend_Session::namespaceUnset('referrer');
        // pass in true to indicate 'Remind me never' was clicked
        Application_Model_Preference::SetRemindMeDate(true);
    }

    public function donotshowregistrationpopupAction()
    {
        // unset session
        SessionHelper::reopenSessionForWriting();
        Zend_Session::namespaceUnset('referrer');
    }

    public function setLibraryScreenSettingsAction()
    {
        $request = $this->getRequest();
        $settings = $request->getParam('settings');
        Application_Model_Preference::setLibraryScreenSettings($settings);
    }
}
