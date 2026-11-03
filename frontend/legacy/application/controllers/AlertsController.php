<?php

/**
 * RASTATIME 2026-11-03 - Settings -> Alerts (alerts stage 1, operator go
 * 2026-11-03): e-mail (SMTP) and Telegram alerts for dead air, services
 * down and pre-flight warnings.  Admins only (ACL resource 'alerts').
 */
class AlertsController extends Zend_Controller_Action
{
    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('test', 'json')->initContext();
    }

    private function csrfToken()
    {
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }

        return $ns->authtoken;
    }

    /** The settings page; a POST saves (the Acl plugin has checked the CSRF token). */
    public function settingsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Settings');
        $request = $this->getRequest();
        $errors = [];
        $values = null;
        if ($request->isPost()) {
            $errors = Application_Service_AlertService::save($request->getPost());
            if (!$errors) {
                $this->_redirect('alerts/settings?done=saved');

                return;
            }
            $values = Application_Service_AlertService::load();
            foreach ($request->getPost() as $k => $v) {
                if (array_key_exists($k, $values) && !in_array($k, Application_Service_AlertService::SECRETS, true)) {
                    $values[$k] = is_array($v) ? '' : (string) $v;
                }
            }
            foreach (['alerts_enabled', 'alerts_services', 'alerts_preflight'] as $k) {
                $values[$k] = !empty($request->getPost($k)) ? 'true' : 'false';
            }
        }
        $this->view->values = $values ?? Application_Service_AlertService::load();
        $this->view->errors = $errors;
        $this->view->saved = $request->getParam('done') === 'saved';
        $this->view->csrf = $this->csrfToken();
        $this->view->playoutUrl = Application_Service_AlertService::PLAYOUT_TEST_URL;
    }

    /** POST alerts/test?channel=mail|telegram -> {"ok": bool, "error": "..."} */
    public function testAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        if (!$this->getRequest()->isPost()) {
            $this->getResponse()->setHttpResponseCode(405);
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'method-not-allowed']);

            return;
        }
        [$ok, $error] = Application_Service_AlertService::test((string) $this->_getParam('channel', ''));
        $this->_helper->json->sendJson(['ok' => $ok, 'error' => $error]);
    }
}
