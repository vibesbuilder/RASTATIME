<?php

/** Our standard page layout initialization has to be done via a plugin
 * because some of it requires session variables, and some of the routes
 * run without a session (like API calls). This is an optimization because
 * starting the session adds a fair amount of overhead.
 */
class PageLayoutInitPlugin extends Zend_Controller_Plugin_Abstract
{
    protected $_bootstrap;

    public function __construct($boostrap)
    {
        $this->_bootstrap = $boostrap;
    }

    /**
     * Start the session depending on which controller your request is going to.
     * We start the session explicitly here so that we can avoid starting sessions
     * needlessly for (stateless) requests to the API.
     *
     * @throws Zend_Session_Exception
     */
    public function routeShutdown(Zend_Controller_Request_Abstract $request)
    {
        $controller = strtolower($request->getControllerName());
        $action = strtolower($request->getActionName());

        // List of controllers where we don't need a session, and we don't need
        // all the standard HTML / JS boilerplate.
        if (!in_array($controller, [
            'index', // Radio Page
            'api',
            'auth',
            'error',
            'upgrade',
            'embed',
            'feeds',
        ])) {
            // Start the session
            Zend_Session::start();
            Application_Model_Auth::pinSessionToClient(Zend_Auth::getInstance());

            // localization configuration
            Application_Model_Locale::configureLocalization();

            $this->_initGlobals();
            $this->_initCsrfNamespace();
            $this->_initHeadLink();
            $this->_initHeadScript();
            $this->_initTitle();
            $this->_initTranslationGlobals();
            $this->_initViewHelpers();
        }

        // Skip task management when running unit tests
        if (getenv('AIRTIME_UNIT_TEST') != 1) {
            $taskManager = TaskManager::getInstance();

            // Piggyback the TaskManager onto API calls. This provides guaranteed consistency
            // (there is at least one API call made from pypo to Airtime every 7 minutes) and
            // greatly reduces the chances of lock contention on cc_pref while the TaskManager runs
            if ($controller == 'api') {
                $taskManager->runTasks();
            }
        }
    }

    protected function _initGlobals()
    {
        if (!Zend_Session::isStarted()) {
            return;
        }

        $view = $this->_bootstrap->getResource('view');
        $baseUrl = Config::getBasePath();

        $view->headScript()->appendScript("var baseUrl = '{$baseUrl}';");
        $this->_initTranslationGlobals($view);

        $user = Application_Model_User::GetCurrentUser();
        if (!is_null($user)) {
            $userType = $user->getType();
        } else {
            $userType = '';
        }
        $view->headScript()->appendScript("var userType = '{$userType}';");

        // Dropzone also accept file extensions and doesn't correctly extract certain mimetypes (eg. FLAC - try it),
        // so we append the file extensions to the list of mimetypes and that makes it work.
        $mimeTypes = FileDataHelper::getUploadAudioMimeTypeArray();
        $fileExtensions = array_values($mimeTypes);
        foreach ($fileExtensions as &$extension) {
            $extension = '.' . $extension;
        }
        $view->headScript()->appendScript('var acceptedMimeTypes = ' . json_encode(array_merge(array_keys($mimeTypes), $fileExtensions)) . ';');
    }

    /**
     * Create a global namespace to hold a session token for CSRF prevention.
     */
    protected function _initCsrfNamespace()
    {
        /*
        if (!Zend_Session::isStarted()) {
            return;
        }*/

        $csrf_namespace = new Zend_Session_Namespace('csrf_namespace');
        // Check if the token exists
        if (!$csrf_namespace->authtoken) {
            // If we don't have a token, regenerate it and set a 1 week timeout
            // Should we log the user out here if the token is expired?
            $csrf_namespace->authtoken = sha1(uniqid(random_int(0, getrandmax()), 1));
            $csrf_namespace->setExpirationSeconds(168 * 60 * 60);
        }

        // Here we are closing the session for writing because otherwise no requests
        // in this session will be handled in parallel. This gives a major boost to the perceived performance
        // of the application (page load times are more consistent, no lock contention).
        session_write_close();
        // Zend_Session::writeClose(true);
    }

    /**
     * Ideally, globals should be written to a single js file once
     * from a php init function. This will save us from having to
     * reinitialize them every request.
     */
    private function _initTranslationGlobals()
    {
        $view = $this->_bootstrap->getResource('view');
        $view->headScript()->appendScript("var PRODUCT_NAME = '" . PRODUCT_NAME . "';");
        $view->headScript()->appendScript("var USER_MANUAL_URL = '" . USER_MANUAL_URL . "';");
        $view->headScript()->appendScript("var COMPANY_NAME = '" . COMPANY_NAME . "';");
        // Each page refresh or tab open has uniqID, not to be used for security
        $view->headScript()->appendScript("var UNIQID = '" . uniqid() . "';");

        $track_type_options = [];
        $track_types = Application_Model_Tracktype::getTracktypes();

        array_multisort(array_map(function ($element) {
            return $element['type_name'];
        }, $track_types), SORT_ASC, $track_types);

        foreach ($track_types as $key => $tt) {
            $track_type_options[$tt['id']] = ['name' => $tt['type_name'], 'code' => $tt['code']];
        }
        $ttarr = json_encode($track_type_options, JSON_FORCE_OBJECT);
        $view->headScript()->appendScript('var TRACKTYPES = ' . $ttarr . ';');
    }

    protected function _initHeadLink()
    {
        $view = $this->_bootstrap->getResource('view');

        $baseUrl = Config::getBasePath();

        // RASTATIME 2026-05-15 - Custom favicon override.  GetStationFaviconHref()
        // returns a complete data: URI when the operator has uploaded one,
        // else null and we fall back to the bundled public/favicon.ico.
        $customFavicon = Application_Model_Preference::GetStationFaviconHref();
        $faviconHref = $customFavicon !== null ? $customFavicon : ($baseUrl . 'favicon.ico');
        $faviconMime = $customFavicon !== null ? Application_Model_Preference::GetStationFaviconMime() : 'image/x-icon';
        $view->headLink(['rel' => 'icon', 'href' => $faviconHref, 'type' => $faviconMime], 'PREPEND')
            ->appendStylesheet(Assets::url('css/bootstrap.css'))
            ->appendStylesheet(Assets::url(self::rtJqueryUiThemeCss()))
            ->appendStylesheet(Assets::url('css/pro_dropdown_3.css'))
            // RASTATIME 2026-06-01 (JS-modernization stage 1): rtTooltip (Floating
            // UI) styling replaces the removed qtip2 CSS.
            ->appendStylesheet(Assets::url('css/tooltip.css'))
            ->appendStylesheet(Assets::url('css/styles.css'))
            ->appendStylesheet(Assets::url('css/masterpanel.css'));
    }

    /**
     * RASTATIME 2026-06-01 (JS-modernization stage 2): jQuery 1.8 -> 3.7
     * migration flag.  When on, jQuery 3.7 + jquery-migrate + jQuery UI 1.13 are
     * loaded instead of jQuery 1.8 + UI 1.8.  ?jq3=1 turns it on, ?jq3=0 off,
     * each persisted in a session cookie so page navigation keeps the choice;
     * with no flag/cookie, jQuery 1.8 stays the default (instant rollback).
     * Shared by the main app layout (here) and the radio page (IndexController).
     */
    public static function rtUseJquery3()
    {
        if (isset($_GET['jq3'])) {
            $on = ($_GET['jq3'] === '1');
            if (!headers_sent()) {
                setcookie('rt_jq3', $on ? '1' : '0', 0, '/');
            }
            $_COOKIE['rt_jq3'] = $on ? '1' : '0';

            return $on;
        }
        if (isset($_COOKIE['rt_jq3'])) {
            return $_COOKIE['rt_jq3'] === '1';
        }

        return false;
    }

    /**
     * RASTATIME 2026-06-01 (JS-modernization stage 2): jQuery-UI theme CSS that
     * matches the active jQuery-UI version.  jQuery UI 1.13's widget markup
     * differs from 1.8, so the old redmond 1.8.8 theme renders 1.13 dialogs
     * broken (transparent overlay, missing chrome).  redmond-1.13 is the same
     * redmond palette regenerated for 1.13.
     */
    public static function rtJqueryUiThemeCss()
    {
        return self::rtUseJquery3()
            ? 'css/redmond-1.13/jquery-ui.min.css'
            : 'css/redmond/jquery-ui-1.8.8.custom.css';
    }

    /**
     * RASTATIME 2026-06-01 (JS-modernization stage 2): DataTables core path.
     * DataTables 1.9.3 is not jQuery-3 compatible; 1.13 is, and keeps the legacy
     * Hungarian options + server-side format, so the init code and the backend
     * response are unchanged.  Loaded on the ?jq3 path; 1.9 stays the default.
     * (DataTables 2.0 is a separate future step — see BACKLOG.)
     */
    public static function rtDataTablesCore()
    {
        return self::rtUseJquery3()
            ? 'js/datatables-1.13/js/jquery.dataTables.min.js'
            : 'js/datatables/js/jquery.dataTables.js';
    }

    protected function _initHeadScript()
    {
        if (!Zend_Session::isStarted()) {
            return;
        }

        $view = $this->_bootstrap->getResource('view');

        $baseUrl = Config::getBasePath();

        // RASTATIME 2026-06-01 (JS-modernization stage 2): jQuery 1.8 (+ UI 1.8)
        // vs jQuery 3.7 + migrate + UI 1.13, behind the ?jq3 flag.
        $hs = $view->headScript();
        if (self::rtUseJquery3()) {
            $hs->appendFile(Assets::url('js/libs/jquery-3.7.1.min.js'), 'text/javascript')
                ->appendFile(Assets::url('js/libs/jquery-migrate-3.5.2.min.js'), 'text/javascript')
                ->appendFile(Assets::url('js/libs/jquery-browser-shim.js'), 'text/javascript')
                ->appendFile(Assets::url('js/libs/jquery-ui-1.13.3.min.js'), 'text/javascript');
        } else {
            $hs->appendFile(Assets::url('js/libs/jquery-1.8.3.min.js'), 'text/javascript')
                ->appendFile(Assets::url('js/libs/jquery-ui-1.8.24.min.js'), 'text/javascript');
        }
        $hs
            // RASTATIME 2026-06-01 (JS-modernization stage 1): AngularJS 1.4.5
            // (EOL 2022) has been fully removed — the Podcast / Publish views
            // that used it are now vanilla/jQuery.
            ->appendFile(Assets::url('js/bootstrap/bootstrap.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/libs/underscore-min.js'), 'text/javascript')

            // RASTATIME 2026-06-01 (JS-modernization stage 1): Floating UI +
            // rtTooltip — replaces qtip2 (now removed).  core before dom; the
            // wrapper exposes $.fn.rtTooltip.
            ->appendFile(Assets::url('js/libs/floating-ui/floating-ui.core.umd.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/libs/floating-ui/floating-ui.dom.umd.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/airtime/common/tooltip.js'), 'text/javascript')
            // RASTATIME 2026-06-04 (?jq3): anchors the DataTables Buttons colvis
            // dropdown under its button (Floating UI); no-op on the legacy stack.
            ->appendFile(Assets::url('js/airtime/common/colvisanchor.js'), 'text/javascript')
            ->appendFile(Assets::url('js/sprintf/sprintf-0.7-beta1.js'), 'text/javascript')
            ->appendFile(Assets::url('js/cookie/js.cookie.js'), 'text/javascript')
            ->appendFile(Assets::url('js/i18n/jquery.i18n.js'), 'text/javascript')
            ->appendFile($baseUrl . 'locale/general-translation-table', 'text/javascript')
            ->appendFile($baseUrl . 'locale/datatables-translation-table', 'text/javascript')

            ->appendScript('$.i18n.setDictionary(general_dict)')
            ->appendScript("var baseUrl='{$baseUrl}'");

        // These timezones are needed to adjust javascript Date objects on the client to make sense to the user's set timezone
        // or the server's set timezone.
        $serverTimeZone = new DateTimeZone(Application_Model_Preference::GetDefaultTimezone());
        $now = new DateTime('now', $serverTimeZone);
        $offset = $now->format('Z') * -1;
        $view->headScript()->appendScript("var serverTimezoneOffset = {$offset}; //in seconds");

        if (class_exists('Zend_Auth', false) && Zend_Auth::getInstance()->hasIdentity()) {
            $userTimeZone = new DateTimeZone(Application_Model_Preference::GetUserTimezone());
            $now = new DateTime('now', $userTimeZone);
            $offset = $now->format('Z') * -1;
            $view->headScript()->appendScript("var userTimezoneOffset = {$offset}; //in seconds");
        }

        // scripts for now playing bar
        $view->headScript()->appendFile(Assets::url('js/airtime/airtime_bootstrap.js'), 'text/javascript')
            ->appendFile(Assets::url('js/airtime/dashboard/helperfunctions.js'), 'text/javascript')
            ->appendFile(Assets::url('js/airtime/dashboard/dashboard.js'), 'text/javascript')
            ->appendFile(Assets::url('js/airtime/dashboard/versiontooltip.js'), 'text/javascript')

            ->appendFile(Assets::url('js/airtime/common/common.js'), 'text/javascript')
            ->appendFile(Assets::url('js/airtime/common/audioplaytest.js'), 'text/javascript');

        // include wavesurfer.js for waveform display
        $view->headScript()->appendFile(Assets::url('js/wavesurfer/wavesurfer.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/wavesurfer/timeline.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/wavesurfer/regions.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/wavesurfer/cursor.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/wavesurfer/libretime.js'), 'text/javascript');

        $user = Application_Model_User::getCurrentUser();
        if (!is_null($user)) {
            $userType = $user->getType();
        } else {
            $userType = '';
        }

        $view->headScript()->appendScript("var userType = '{$userType}';");
    }

    protected function _initViewHelpers()
    {
        $view = $this->_bootstrap->getResource('view');
        $view->addHelperPath(APPLICATION_PATH . '/views/helpers', 'Airtime_View_Helper');
    }

    protected function _initTitle()
    {
        $view = $this->_bootstrap->getResource('view');
        $view->headTitle(Application_Model_Preference::GetHeadTitle());
    }
}
