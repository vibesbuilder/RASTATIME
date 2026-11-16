<?php

class TracktypeController extends Zend_Controller_Action
{
    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('get-tracktype-data-table-info', 'json')
            ->addActionContext('get-tracktype-data', 'json')
            ->addActionContext('remove-tracktype', 'json')
            ->initContext();
    }

    public function addTracktypeAction()
    {
        // Start the session to re-open write permission to the session so we can
        // create the namespace for our csrf token verification
        SessionHelper::reopenSessionForWriting();

        $request = $this->getRequest();

        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');

        foreach ([
            'js/datatables-1.13/js/jquery.dataTables.min.js',
            'js/datatables/plugin/dataTables.pluginAPI.js',
            'js/airtime/tracktype/tracktype.js',
        ] as $file) {
            $this->view->headScript()->appendFile(Assets::url($file), 'text/javascript');
        }

        $this->view->headLink()->appendStylesheet(Assets::url('css/tracktypes.css'));
        // RASTATIME 2026-11-16 - show types on the same page (Track/Show Types)
        $this->view->headScript()->appendFile(Assets::url('js/airtime/tracktype/showtype.js'), 'text/javascript');
        $this->view->showTypesReady = Application_Model_Showtype::ready();
        $this->view->showTypes = Application_Model_Showtype::all();

        $form = new Application_Form_AddTracktype();

        $this->view->successMessage = '';

        if ($request->isPost()) {
            $params = $request->getPost();
            $postData = explode('&', $params['data']);
            $formData = [];
            foreach ($postData as $k => $v) {
                $v = explode('=', $v);
                $formData[$v[0]] = urldecode($v[1]);
            }

            if ($form->isValid($formData)) {
                $tracktype = new Application_Model_Tracktype($formData['tracktype_id']);
                $tracktype->setCode($formData['code']);
                $tracktype->setTypeName($formData['type_name']);
                $tracktype->setDescription($formData['description']);
                $tracktype->setVisibility($formData['visibility']);
                $tracktype->setAnalyzeCuePoints($formData['analyze_cue_points']);
                // RASTATIME 2026-09-29 - crossfade per track type: a changed value
                // re-lays the rows of all upcoming shows and tells the playout
                $tracktype->setCrossfadeDuration($formData['crossfade_duration'] ?? '');
                // RASTATIME 2026-09-30 - "No Fade during Crossover" preset: the
                // overlap stays, so only the playout needs the new schedule
                $tracktype->setNoFadeCrossfade($formData['no_fade_crossfade'] ?? '0');
                // RASTATIME 2026-10-14 - stream metadata preset
                $tracktype->setIcyForward($formData['icy_forward'] ?? '0');
                // RASTATIME 2026-11-13 - loudness analysis per track type (the
                // fields exist once migration 0083 ran)
                if (array_key_exists('analyze_loudness', $formData)) {
                    $tracktype->setAnalyzeLoudness($formData['analyze_loudness']);
                }
                if (array_key_exists('fixed_gain_db', $formData)) {
                    $tracktype->setFixedGainDb($formData['fixed_gain_db']);
                }
                // RASTATIME 2026-11-15 - audio features per track type (the
                // field exists once migration 0087 ran)
                if (array_key_exists('analyze_audio_features', $formData)) {
                    $tracktype->setAnalyzeAudioFeatures($formData['analyze_audio_features']);
                }
                $changed = $tracktype->save();
                if ($changed['crossfade']) {
                    Application_Model_Scheduler::relayoutFutureInstances();
                }
                if ($changed['crossfade'] || $changed['no_fade'] || $changed['icy'] || $changed['gain']) {
                    Application_Model_RabbitMq::PushSchedule();
                }

                $form->reset();
                $this->view->form = $form;

                if (strlen($formData['tracktype_id']) == 0) {
                    $this->view->successMessage = "<div class='success'>" . _('Track Type added successfully!') . '</div>';
                } else {
                    $this->view->successMessage = "<div class='success'>" . _('Track Type updated successfully!') . '</div>';
                }

                $this->_helper->json->sendJson(['valid' => 'true', 'html' => $this->view->render('tracktype/add-tracktype.phtml')]);
            } else {
                $this->view->form = $form;
                $this->_helper->json->sendJson(['valid' => 'false', 'html' => $this->view->render('tracktype/add-tracktype.phtml')]);
            }
        }

        $this->view->form = $form;
    }

    public function getTracktypeDataTableInfoAction()
    {
        $post = $this->getRequest()->getPost();
        $tracktypes = Application_Model_Tracktype::getTracktypesDataTablesInfo($post);

        $this->_helper->json->sendJson($tracktypes);
    }

    public function getTracktypeDataAction()
    {
        $id = $this->_getParam('id');
        // RASTATIME 2026-09-30 - send the JSON ourselves (like the table-info
        // action): the AjaxContext only switches for X-Requested-With calls,
        // every other call rendered get-tracktype-data.phtml, which echoed
        // the array and died with "Array to string conversion" (HTTP 500).
        $this->_helper->json->sendJson(['entries' => Application_Model_Tracktype::GetTracktypeData($id)]);
    }

    /**
     * RASTATIME 2026-11-16 - create / update a show type (POST id, code,
     * type_name, counts_as_repeat, sort_order).  Answers the errors or the
     * re-rendered show type panel.
     */
    public function saveShowtypeAction()
    {
        $r = $this->getRequest();
        if (!$r->isPost()) {
            $this->_helper->json->sendJson(['ok' => false, 'errors' => [_('POST only.')]]);

            return;
        }
        $errors = Application_Model_Showtype::save(
            $r->getPost('id', ''),
            $r->getPost('code', ''),
            $r->getPost('type_name', ''),
            (string) $r->getPost('counts_as_repeat', '0') === '1',
            $r->getPost('sort_order', '0')
        );
        $this->_helper->json->sendJson(['ok' => !$errors, 'errors' => $errors, 'html' => $errors ? '' : $this->renderShowtypes()]);
    }

    /** RASTATIME 2026-11-16 - delete a show type (POST id); its shows keep no type. */
    public function removeShowtypeAction()
    {
        $r = $this->getRequest();
        if (!$r->isPost()) {
            $this->_helper->json->sendJson(['ok' => false]);

            return;
        }
        Application_Model_Showtype::delete($r->getPost('id'));
        $this->_helper->json->sendJson(['ok' => true, 'html' => $this->renderShowtypes()]);
    }

    private function renderShowtypes(): string
    {
        $this->view->showTypesReady = Application_Model_Showtype::ready();
        $this->view->showTypes = Application_Model_Showtype::all();

        return $this->view->render('tracktype/showtypes.phtml');
    }

    public function removeTracktypeAction()
    {
        // action body
        $delId = $this->_getParam('id');

        $tracktype = new Application_Model_Tracktype($delId);

        // Delete the track type
        // RASTATIME 2026-09-30 - the JSON is sent here (the AjaxContext only
        // switches for X-Requested-With calls; the view script that echoed the
        // array for every other call is gone).
        $this->_helper->json->sendJson(['entries' => $tracktype->delete()]);
    }
}
