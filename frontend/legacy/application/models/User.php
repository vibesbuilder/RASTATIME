<?php

class Application_Model_User
{
    private $_userInstance;

    public function __construct($userId)
    {
        if (empty($userId)) {
            $this->_userInstance = $this->createUser();
        } else {
            $this->_userInstance = CcSubjsQuery::create()->findPK($userId);

            if (is_null($this->_userInstance)) {
                throw new Exception();
            }
        }
    }

    public function getId()
    {
        return $this->_userInstance->getDbId();
    }

    public function isGuest()
    {
        return $this->getType() == UTYPE_GUEST;
    }

    public function isHostOfShow($showId)
    {
        $userId = $this->_userInstance->getDbId();

        return CcShowHostsQuery::create()
            ->filterByDbShow($showId)
            ->filterByDbHost($userId)->count() > 0;
    }

    public function isHost()
    {
        return $this->isUserType(UTYPE_HOST);
    }

    public function isPM()
    {
        return $this->isUserType(UTYPE_PROGRAM_MANAGER);
    }

    public function isAdmin()
    {
        return $this->isUserType(UTYPE_ADMIN);
    }

    public function isSuperAdmin()
    {
        return $this->isUserType(UTYPE_SUPERADMIN);
    }

    /**
     * RASTATIME 2026-10-25 (operator go) - the installation account cannot
     * be deleted (the protection the retired Super Admin role used to give).
     */
    public const PROTECTED_LOGIN = 'admin';

    public static function isProtectedLogin($login): bool
    {
        return strcasecmp((string) $login, self::PROTECTED_LOGIN) === 0;
    }

    /** RASTATIME 2026-10-25 (role audit) - Program Manager, Admin or Super Admin. */
    public function isAdminOrPM(): bool
    {
        return $this->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);
    }

    /**
     * RASTATIME 2026-10-25 (role audit package 2) - stop the request with 403
     * unless the logged-in user is a Program Manager or Admin.  The
     * ErrorController's 403 branch logs "Access refused (403)".
     */
    public static function requireAdminOrPM(): void
    {
        $user = self::getCurrentUser();
        if ($user === null || !$user->isAdminOrPM()) {
            throw new Zend_Controller_Action_Exception('Program Managers and Admins only', 403);
        }
    }

    public function canSchedule($p_showId)
    {
        $type = $this->getType();
        $result = false;

        // RASTATIME 2026-10-25 (role audit R11) - a show host demoted to
        // Guest keeps the host row but no longer schedules.
        if (
            $this->isAdmin()
            || $this->isSuperAdmin()
            || $this->isPM()
            || (!$this->isGuest() && self::isHostOfShow($p_showId))
        ) {
            $result = true;
        }

        return $result;
    }

    public function isSourcefabricAdmin()
    {
        $username = $this->getLogin();
        if ($username == 'sourcefabric_admin') {
            return true;
        }

        return false;
    }

    // TODO : refactor code to only accept arrays for isUserType and
    // simplify code even further
    public function isUserType($type)
    {
        if (!is_array($type)) {
            $type = [$type];
        }
        $real_type = $this->_userInstance->getDbType();

        return in_array($real_type, $type);
    }

    public function setLogin($login)
    {
        $user = $this->_userInstance;
        $user->setDbLogin($login);
    }

    public function setPassword($password)
    {
        $user = $this->_userInstance;
        // RASTATIME 2026-10-27 - bcrypt instead of unsalted md5 (Application_Model_Password)
        $user->setDbPass(Application_Model_Password::hash((string) $password));
    }

    /**
     * RASTATIME 2026-10-27 - check a plain password against the stored
     * bcrypt hash (the legacy md5 fallback is gone since 2026-11-11).  A
     * match against a hash below the current cost stores the password again
     * right away.
     */
    public function verifyPassword($password): bool
    {
        $user = $this->_userInstance;
        $stored = (string) $user->getDbPass();
        if (!Application_Model_Password::verify((string) $password, $stored)) {
            return false;
        }
        if (Application_Model_Password::needsRehash($stored)) {
            try {
                $user->setDbPass(Application_Model_Password::hash((string) $password));
                $user->save();
                Logging::info('Password of user ' . $user->getDbLogin() . ' re-hashed');
            } catch (Exception $e) {
                Logging::warn('Password re-hash for ' . $user->getDbLogin() . ' failed: ' . $e->getMessage());
            }
        }

        return true;
    }

    public function setFirstName($firstName)
    {
        $user = $this->_userInstance;
        $user->setDbFirstName($firstName);
    }

    public function setLastName($lastName)
    {
        $user = $this->_userInstance;
        $user->setDbLastName($lastName);
    }

    public function setType($type)
    {
        $user = $this->_userInstance;
        $user->setDbType($type);
    }

    public function setEmail($email)
    {
        $user = $this->_userInstance;
        $user->setDbEmail(strtolower($email));
    }

    public function setCellPhone($cellPhone)
    {
        $user = $this->_userInstance;
        $user->setDbCellPhone($cellPhone);
    }

    public function setSkype($skype)
    {
        $user = $this->_userInstance;
        $user->setDbSkypeContact($skype);
    }

    public function setJabber($jabber)
    {
        $user = $this->_userInstance;
        $user->setDbJabberContact($jabber);
    }

    public function getLogin()
    {
        $user = $this->_userInstance;

        return $user->getDbLogin();
    }

    public function getPassword()
    {
        $user = $this->_userInstance;

        return $user->getDbPass();
    }

    public function getFirstName()
    {
        $user = $this->_userInstance;

        return $user->getDbFirstName();
    }

    public function getLastName()
    {
        $user = $this->_userInstance;

        return $user->getDbLastName();
    }

    public function getType()
    {
        $user = $this->_userInstance;

        return $user->getDbType();
    }

    public function getEmail()
    {
        $user = $this->_userInstance;

        return $user->getDbEmail();
    }

    public function getCellPhone()
    {
        $user = $this->_userInstance;

        return $user->getDbCellPhone();
    }

    public function getSkype()
    {
        $user = $this->_userInstance;

        return $user->getDbSkypeContact();
    }

    public function getJabber()
    {
        $user = $this->_userInstance;

        return $user->getDbJabberContact();
    }

    public function save()
    {
        $this->_userInstance->save();
    }

    public function delete()
    {
        if (!$this->_userInstance->isDeleted()) {
            $this->_userInstance->delete();
        }
    }

    public function getOwnedFiles()
    {
        $user = $this->_userInstance;

        // do we need a find call at the end here?
        return $user->getCcFilessRelatedByDbOwnerId();
    }

    public function donateFilesTo($user) // $user is object not user id
    {
        $my_files = $this->getOwnedFiles();
        foreach ($my_files as $file) {
            $file->reassignTo($user);
        }
    }

    public function deleteAllFiles()
    {
        $my_files = $this->getOwnedFiles();
        foreach ($my_files as $file) {
            $file->delete();
        }
    }

    private function createUser()
    {
        return new CcSubjs();
    }

    public static function getUsersOfType($type)
    {
        return CcSubjsQuery::create()->filterByDbType($type)->find();
    }

    /**
     * Get the first admin user from the database.
     *
     * This function gets used in UserController in the delete action. The controller
     * uses it to figure out who to reassign the deleted users files to.
     *
     * @param $ignoreUser String optional userid of a user that shall be ignored when
     *                    when looking for the "first" admin
     *
     * @return null|CcSubj
     */
    public static function getFirstAdmin($ignoreUser = null)
    {
        $superAdmins = Application_Model_User::getUsersOfType('S');
        if (count($superAdmins) > 0) { // found superadmin => pick first one
            return $superAdmins[0];
        }
        // get all admin users
        $query = CcSubjsQuery::create()->filterByDbType('A');
        // ignore current user if one was specified
        if ($ignoreUser !== null) {
            $query->filterByDbId($ignoreUser, Criteria::NOT_EQUAL);
        }
        $admins = $query->find();
        if (count($admins) > 0) { // found admin => pick first one
            return $admins[0];
        }
        Logging::warn('Warning. no admins found in database');

        return null;
    }

    public static function getUsers(array $type, $search = null)
    {
        $con = Propel::getConnection();

        $sql_gen = 'SELECT login AS value, login AS label, id as index FROM cc_subjs ';

        $types = [];
        $params = [];
        for ($i = 0; $i < count($type); ++$i) {
            $p = ":type{$i}";
            $types[] = "type = {$p}";
            $params[$p] = $type[$i];
        }

        $sql_type = implode(' OR ', $types);

        $sql = $sql_gen . ' WHERE (' . $sql_type . ') ';

        $sql .= ' AND login ILIKE :search';
        $params[':search'] = "%{$search}%";

        $sql .= ' ORDER BY login';

        return Application_Common_Database::prepareAndExecute($sql, $params, 'all');
    }

    public static function getUserCount()
    {
        $sql_gen = 'SELECT count(*) AS cnt FROM cc_subjs';

        $query = Application_Common_Database::prepareAndExecute(
            $sql_gen,
            [],
            Application_Common_Database::COLUMN
        );

        return ($query !== false) ? $query : null;
    }

    public static function getHosts($search = null)
    {
        return Application_Model_User::getUsers(['H'], $search);
    }

    public static function getNonGuestUsers($search = null)
    {
        return Application_Model_User::getUsers(['H', 'A', 'S', 'P'], $search);
    }

    public static function getUsersDataTablesInfo($datatables)
    {
        $con = Propel::getConnection(CcSubjsPeer::DATABASE_NAME);

        $displayColumns = ['id', 'login', 'first_name', 'last_name', 'type'];
        $fromTable = 'cc_subjs';

        // get current user
        $username = '';
        $auth = Zend_Auth::getInstance();

        if ($auth->hasIdentity()) {
            $username = $auth->getIdentity()->login;
        }

        $res = Application_Model_Datatables::findEntries($con, $displayColumns, $fromTable, $datatables);

        // mark record which is for the current user
        foreach ($res['aaData'] as $key => &$record) {
            if ($record['login'] == $username) {
                $record['delete'] = 'self';
            } else {
                $record['delete'] = '';
            }

            if ($record['login'] == 'sourcefabric_admin') {
                // arrays in PHP are basically associative arrays that can be iterated in order.
                // Deleting an earlier element does not change the keys of elements that come after it. --MK
                unset($res['aaData'][$key]);
                --$res['iTotalDisplayRecords'];
                --$res['iTotalRecords'];
            }

            $record = array_map('htmlspecialchars', $record);
        }

        $res['aaData'] = array_values($res['aaData']);

        return $res;
    }

    public static function getUserData($id)
    {
        $sql = <<<'SQL'
SELECT login, first_name, last_name, type, id, email, cell_phone, skype_contact,
       jabber_contact
FROM cc_subjs
WHERE id = :id
SQL;

        return Application_Common_Database::prepareAndExecute($sql, [
            ':id' => $id,
        ], 'single');
    }

    public static function getCurrentUser()
    {
        $userinfo = Zend_Auth::getInstance()->getStorage()->read();
        if (is_null($userinfo)) {
            return null;
        }

        try {
            return new self($userinfo->id);
        } catch (Exception $e) {
            // we get here if $userinfo->id is defined, but doesn't exist
            // in the database anymore.
            Zend_Auth::getInstance()->clearIdentity();

            return null;
        }
    }
}
