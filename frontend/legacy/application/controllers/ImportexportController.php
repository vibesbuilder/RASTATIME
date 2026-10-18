<?php

/**
 * RASTATIME 2026-10-13 - Settings -> Import/Export (Section 23.56).
 *
 *   GET  /importexport                page
 *   POST /importexport/preview        upload (file, type?, conflict) -> staged token + validated rows (JSON)
 *   POST /importexport/import         token + selected[] -> results (JSON)
 *   GET  /importexport/export?types=  download (single file or ZIP bundle)
 *   GET  /importexport/template       download the template bundle
 */
class ImportexportController extends Zend_Controller_Action
{
    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('preview', 'json')
            ->addActionContext('import', 'json')
            ->initContext();
    }

    private function verifyCsrf(): bool
    {
        $ns = new Zend_Session_Namespace('csrf_namespace');
        $observed = (string) $this->_getParam('csrf_token', '');

        return isset($ns->authtoken) && $observed !== '' && hash_equals((string) $ns->authtoken, $observed);
    }

    private function sendJson(array $data, int $status = 200): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $this->getResponse()
            ->setHttpResponseCode($status)
            ->setHeader('Content-Type', 'application/json; charset=utf-8', true)
            ->setBody(json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }

    public function indexAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/importexport/importexport.js'), 'text/javascript');
        $types = [];
        foreach (Application_Service_ImportExportService::handlers() as $type => $h) {
            try {
                $count = $h->count();
            } catch (Exception $e) {
                $count = null;
            }
            $types[] = ['type' => $type, 'label' => $h->label(), 'file' => $h->fileName(), 'count' => $count, 'notices' => $h->notices()];
        }
        $this->view->types = $types;
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }
        $this->view->csrf = $ns->authtoken;
        $this->view->maxUpload = ini_get('upload_max_filesize') . ' / ' . ini_get('post_max_size');
    }

    public function previewAction()
    {
        if (!$this->getRequest()->isPost()) {
            $this->sendJson(['error' => 'POST only'], 405);

            return;
        }
        if (!$this->verifyCsrf()) {
            $this->sendJson(['error' => _('Session expired - reload the page.')], 403);

            return;
        }
        if (empty($_FILES['file']) || !is_uploaded_file($_FILES['file']['tmp_name'])) {
            $code = isset($_FILES['file']['error']) ? (int) $_FILES['file']['error'] : -1;
            $msg = in_array($code, [UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE], true)
                ? sprintf(_('The file is larger than the server accepts (%s).'), ini_get('upload_max_filesize'))
                : _('No file received.');
            $this->sendJson(['error' => $msg], 400);

            return;
        }
        $type = (string) $this->_getParam('type', '');
        $conflict = (string) $this->_getParam('conflict', 'skip');
        try {
            $service = new Application_Service_ImportExportService();
            $result = $service->stageUpload($_FILES['file']['tmp_name'], (string) $_FILES['file']['name'], $type !== '' && $type !== 'auto' ? $type : null, $conflict);
            $this->sendJson($result);
        } catch (Exception $e) {
            Logging::warn('import/export preview: ' . $e->getMessage());
            $this->sendJson(['error' => $e->getMessage()], 400);
        }
    }

    /**
     * RASTATIME 2026-10-18 - validate a batch of staged rows (POST token,
     * ids[]); the page calls this repeatedly after the upload.
     */
    public function validateAction()
    {
        if (!$this->getRequest()->isPost()) {
            $this->sendJson(['error' => 'POST only'], 405);

            return;
        }
        if (!$this->verifyCsrf()) {
            $this->sendJson(['error' => _('Session expired - reload the page.')], 403);

            return;
        }
        $token = (string) $this->_getParam('token', '');
        $ids = $this->_getParam('ids', []);
        if (is_string($ids)) {
            $ids = $ids === '' ? [] : explode(',', $ids);
        }

        try {
            $service = new Application_Service_ImportExportService();
            $this->sendJson(['rows' => $service->validateRows($token, is_array($ids) ? $ids : [])]);
        } catch (Exception $e) {
            Logging::warn('import/export validate: ' . $e->getMessage());
            $this->sendJson(['error' => $e->getMessage()], 400);
        }
    }

    public function importAction()
    {
        if (!$this->getRequest()->isPost()) {
            $this->sendJson(['error' => 'POST only'], 405);

            return;
        }
        if (!$this->verifyCsrf()) {
            $this->sendJson(['error' => _('Session expired - reload the page.')], 403);

            return;
        }
        $token = (string) $this->_getParam('token', '');
        $selected = $this->_getParam('selected', []);
        if (is_string($selected)) {
            $selected = $selected === '' ? [] : explode(',', $selected);
        }
        // RASTATIME 2026-10-18 - batched import: partial=1 returns only the
        // selected rows, finish=0 keeps the staging folder for the next batch
        $partial = (string) $this->_getParam('partial', '0') === '1';
        $finish = (string) $this->_getParam('finish', '1') !== '0';

        try {
            $service = new Application_Service_ImportExportService();
            $rows = $service->import($token, is_array($selected) ? $selected : [], $finish, $partial);
            $summary = ['ok' => 0, 'skip' => 0, 'error' => 0];
            foreach ($rows as $r) {
                if (isset($summary[$r['status']])) {
                    ++$summary[$r['status']];
                }
            }
            // the playout and the calendar pick the new shows up on their next refresh
            $this->sendJson(['rows' => $rows, 'summary' => $summary]);
        } catch (Exception $e) {
            Logging::warn('import/export import: ' . $e->getMessage());
            $this->sendJson(['error' => $e->getMessage()], 400);
        }
    }

    private function sendDownload(array $file): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $this->getResponse()
            ->setHeader('Content-Type', $file['mime'], true)
            ->setHeader('Content-Disposition', 'attachment; filename="' . $file['filename'] . '"', true)
            ->setHeader('Content-Length', (string) strlen($file['content']), true)
            ->setHeader('Cache-Control', 'no-store', true)
            ->setBody($file['content']);
    }

    public function exportAction()
    {
        $types = (string) $this->_getParam('types', '');
        $list = array_filter(array_map('trim', explode(',', $types)));
        try {
            $service = new Application_Service_ImportExportService();
            $this->sendDownload($service->export($list));
        } catch (Exception $e) {
            Logging::warn('import/export export: ' . $e->getMessage());
            $this->view->layout()->disableLayout();
            $this->_helper->viewRenderer->setNoRender(true);
            $this->getResponse()->setHttpResponseCode(400)->setBody(htmlspecialchars($e->getMessage(), ENT_QUOTES, 'UTF-8'));
        }
    }

    public function templateAction()
    {
        $service = new Application_Service_ImportExportService();
        $this->sendDownload($service->template());
    }
}
