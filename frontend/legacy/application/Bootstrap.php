<?php

require_once 'preload.php';

$CC_CONFIG = Config::getConfig();

require_once CONFIG_PATH . '/ACL.php';

// Since we initialize the database during the configuration check,
// check the $configRun global to avoid reinitializing unnecessarily
if (!isset($configRun) || !$configRun) {
    Propel::init(PROPEL_CONFIG_FILEPATH);
}

Logging::setLogPath(RASTATIME_LOG_FILEPATH);

if (APPLICATION_ENV != 'testing') {
    Zend_Session::setOptions([
        'strict' => true,
        'serialize_handler' => 'php_serialize',
        // RASTATIME 2026-10-25 (role audit package 3, R12) - the browser
        // sends the session cookie on cross-site requests only for top-level
        // GET navigation (no cross-site POST/iframe/fetch), and page scripts
        // cannot read it.  New cookies only: takes effect at the next login.
        'cookie_samesite' => 'Lax',
        'cookie_httponly' => true,
    ]);

    $db = Zend_Db::factory('PDO_' . $CC_CONFIG['dsn']['phptype'], [
        'host' => $CC_CONFIG['dsn']['host'],
        'port' => $CC_CONFIG['dsn']['port'],
        'username' => $CC_CONFIG['dsn']['username'],
        'password' => $CC_CONFIG['dsn']['password'],
        'dbname' => $CC_CONFIG['dsn']['database'],
    ]);
    Zend_Db_Table_Abstract::setDefaultAdapter($db);
    Zend_Session::setSaveHandler(new Zend_Session_SaveHandler_DbTable([
        'name' => 'sessions',
        'primary' => 'id',
        'modifiedColumn' => 'modified',
        'dataColumn' => 'data',
        'lifetimeColumn' => 'lifetime',
    ]));
}

Config::setAirtimeVersion();

require_once CONFIG_PATH . '/navigation.php';

Zend_Validate::setDefaultNamespaces('Zend');

$front = Zend_Controller_Front::getInstance();
$front->registerPlugin(new RabbitMqPlugin());
$front->throwExceptions(false);

/* The bootstrap class should only be used to initialize actions that return a view.
   Actions that return JSON will not use the bootstrap class! */
class Bootstrap extends Zend_Application_Bootstrap_Bootstrap
{
    protected function _initDoctype()
    {
        $this->bootstrap('view');
        $view = $this->getResource('view');
        $view->doctype('XHTML1_STRICT');
    }

    /**
     * initialize front controller.
     *
     * This is call ZFrontController to ensure it is executed last in the bootstrap process.
     */
    protected function _initZFrontController()
    {
        Zend_Controller_Front::getInstance()->throwExceptions(false);
    }

    protected function _initRouter()
    {
        $front = Zend_Controller_Front::getInstance();
        $router = $front->getRouter();
        $front->setBaseUrl(Config::getBasePath());

        $router->addRoute(
            'password-change',
            new Zend_Controller_Router_Route('password-change/:user_id/:token', [
                'module' => 'default',
                'controller' => 'login',
                'action' => 'password-change',
            ])
        );
        // RASTATIME 2026-10-01 - the in-app user manual (/manual/<lang>/
        // <CHAPTER>) deliberately has NO route of its own: the navigation
        // menu assembles every link with the route that matched the current
        // request, and a custom route cannot assemble the other pages.
        // ManualController reads the path itself (see its __call()).
    }

    public function _initPlugins()
    {
        $front = Zend_Controller_Front::getInstance();
        $front->registerPlugin(new Zend_Controller_Plugin_Maintenance());
        $front->registerPlugin(new PageLayoutInitPlugin($this));
    }
}
