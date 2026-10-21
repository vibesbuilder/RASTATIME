<?php

class ErrorController extends Zend_Controller_Action
{
    public function init()
    {
        // The default layout includes the Dashboard header, which may contain private information.
        // We cannot show that.
        $this->view->layout()->disableLayout();
        $this->setupCSS();

        // TODO: set Help button URL based on whether or not user is logged in
        try {
            $service_user = new Application_Service_UserService();
            $service_user->getCurrentUser();
            $this->view->helpUrl = Config::getBasePath() . 'dashboard/help';
        } catch (Exception $e) {
            $this->view->helpUrl = HELP_URL;
        }
    }

    public function errorAction()
    {
        $errors = $this->_getParam('error_handler');

        // RASTATIME 2026-10-21 - a refused access is no server error.  The
        // ACL plugin throws code 401 for a REST request without session or API
        // key, CORSHelper 403 for a foreign origin; both used to become a 500
        // page with ERR + stack trace in legacy.log.  Answer with their own
        // status and log one INFO line (BACKLOG "REST-Modul ohne Anmeldung").
        $code = $errors ? (int) $errors->exception->getCode() : 0;
        if (
            $errors
            && $errors->type === Zend_Controller_Plugin_ErrorHandler::EXCEPTION_OTHER
            && in_array($code, [401, 403], true)
        ) {
            // path only: a query string can carry a download_key
            Logging::info(sprintf(
                'Access refused (%d): %s %s',
                $code,
                $errors->request->getMethod(),
                strtok((string) $errors->request->getRequestUri(), '?')
            ));
            if ($code === 401) {
                $this->error401Action($errors->exception->getMessage());
            } else {
                $this->error403Action();
            }
            $this->view->request = $errors->request;

            return;
        }

        if ($errors) {
            // log error message and stack trace
            Logging::error($errors->exception->getMessage());
            Logging::error($errors->exception->getTraceAsString());

            switch ($errors->type) {
                case Zend_Controller_Plugin_ErrorHandler::EXCEPTION_NO_ROUTE:
                case Zend_Controller_Plugin_ErrorHandler::EXCEPTION_NO_CONTROLLER:
                    $this->error404Action();

                    break;

                case Zend_Controller_Plugin_ErrorHandler::EXCEPTION_NO_ACTION:
                    $this->error400Action();

                    break;

                default:
                    $this->error500Action();

                    break;
            }
        } else {
            // $exceptions = $this->_getAllParams();
            // Logging::error($exceptions);
            $this->error404Action();

            return;
        }

        // Log exception, if logger available
        /* No idea why this doesn't work or why it was implemented like this. Disabling it -- Albert
        if (($log = $this->getLog())) {
            $log->crit($this->view->message, $errors->exception);
        }*/
        // Logging that actually works: -- Albert
        Logging::error($this->view->message . ': ' . $errors->exception);

        // conditionally display exceptions
        if ($this->getInvokeArg('displayExceptions') == true) {
            $this->view->exception = $errors->exception;
        }

        $this->view->request = $errors->request;
    }

    private function setupCSS()
    {
        $this->view->headLink()->appendStylesheet(Assets::url('css/styles.css'));
    }

    public function getLog()
    {
        $bootstrap = $this->getInvokeArg('bootstrap');
        if (!$bootstrap->hasPluginResource('Log')) {
            return false;
        }

        return $bootstrap->getResource('Log');
    }

    /**
     * 404 error - route or controller.
     */
    public function error404Action()
    {
        $this->_helper->viewRenderer('error');
        $this->getResponse()->setHttpResponseCode(404);
        $this->view->message = _('Page not found.');
    }

    /**
     * 400 error - no such action.
     */
    public function error400Action()
    {
        $this->_helper->viewRenderer('error-400');
        $this->getResponse()->setHttpResponseCode(400);
        $this->view->message = _('The requested action is not supported.');
    }

    /**
     * RASTATIME 2026-10-21 - 401 error - not authenticated (REST without
     * session or API key).  Plain text for API clients, the same wording as
     * Acl_plugin::verifyAuth; no HTML page.
     */
    public function error401Action($message = 'Incorrect API key')
    {
        $this->_helper->viewRenderer->setNoRender(true);
        $this->getResponse()
            ->setHttpResponseCode(401)
            ->setHeader('Content-Type', 'text/plain; charset=utf-8', true)
            ->setBody('ERROR: ' . rtrim((string) $message, '.') . '.');
    }

    /**
     * 403 error - permission denied.
     */
    public function error403Action()
    {
        $this->_helper->viewRenderer('error-403');
        $this->getResponse()->setHttpResponseCode(403);
        $this->view->message = _('You do not have permission to access this resource.');
    }

    /**
     * 500 error - internal server error.
     */
    public function error500Action()
    {
        $this->_helper->viewRenderer('error-500');

        $this->getResponse()->setHttpResponseCode(500);
        $this->view->message = _('An internal application error has occurred.');
    }
}
