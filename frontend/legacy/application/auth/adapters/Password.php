<?php

/**
 * RASTATIME 2026-10-27 - login adapter for the local user table.
 *
 * Replaces Zend_Auth_Adapter_DbTable with setCredentialTreatment('MD5(?)'):
 * the row is fetched by login and the password is checked in PHP
 * (Application_Model_Password: bcrypt, legacy md5 accepted).  A login that
 * succeeded against a legacy md5 - or a bcrypt hash below the current cost -
 * stores the password again as bcrypt, so every account migrates on its
 * next login.  getResultRowObject() mirrors the DbTable adapter: the row's
 * columns as a stdClass, with the password left out.
 */
class LibreTime_Auth_Adaptor_Password implements Zend_Auth_Adapter_Interface
{
    private ?string $identity = null;
    private ?string $credential = null;
    private ?CcSubjs $subj = null;

    public function setIdentity($value): self
    {
        $this->identity = (string) $value;

        return $this;
    }

    public function setCredential($value): self
    {
        $this->credential = (string) $value;

        return $this;
    }

    public function authenticate(): Zend_Auth_Result
    {
        $this->subj = null;
        if ($this->identity === null || $this->identity === '') {
            return new Zend_Auth_Result(Zend_Auth_Result::FAILURE_IDENTITY_NOT_FOUND, null);
        }
        $subj = CcSubjsQuery::create()->findOneByDbLogin($this->identity);
        if ($subj === null) {
            return new Zend_Auth_Result(Zend_Auth_Result::FAILURE_IDENTITY_NOT_FOUND, null);
        }
        $stored = (string) $subj->getDbPass();
        if (!Application_Model_Password::verify((string) $this->credential, $stored)) {
            return new Zend_Auth_Result(Zend_Auth_Result::FAILURE_CREDENTIAL_INVALID, $this->identity);
        }
        if (Application_Model_Password::needsRehash($stored)) {
            try {
                $subj->setDbPass(Application_Model_Password::hash((string) $this->credential));
                $subj->save();
                Logging::info('Password of user ' . $subj->getDbLogin() . ' re-hashed at login');
            } catch (Exception $e) {
                // the login itself succeeded; the re-hash is retried next time
                Logging::warn('Password re-hash for ' . $subj->getDbLogin() . ' failed: ' . $e->getMessage());
            }
        }
        $this->subj = $subj;

        return new Zend_Auth_Result(Zend_Auth_Result::SUCCESS, $this->identity);
    }

    /**
     * The authenticated row as a stdClass (like Zend_Auth_Adapter_DbTable):
     * every cc_subjs column except the password.
     *
     * @param null|array|string $returnColumns columns to include (null = all)
     * @param null|array|string $omitColumns   columns to leave out
     */
    public function getResultRowObject($returnColumns = null, $omitColumns = null): stdClass
    {
        $o = new stdClass();
        if ($this->subj === null) {
            return $o;
        }
        $row = $this->subj->toArray(BasePeer::TYPE_FIELDNAME);
        unset($row['pass']);
        $omit = $omitColumns === null ? [] : (array) $omitColumns;
        $omit[] = 'password';
        $keep = $returnColumns === null ? null : array_flip((array) $returnColumns);
        foreach ($row as $column => $value) {
            if (in_array($column, $omit, true) || ($keep !== null && !isset($keep[$column]))) {
                continue;
            }
            $o->{$column} = $value;
        }

        return $o;
    }
}
