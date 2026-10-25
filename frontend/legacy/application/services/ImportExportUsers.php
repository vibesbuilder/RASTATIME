<?php

/**
 * RASTATIME 2026-10-25 - users.csv (Section 23.56 addendum, operator go).
 *
 * Columns: login, type, first_name, last_name, email, cell_phone, skype,
 * jabber, password.  The login is the key.  Imported first: shows.csv
 * names its DJs by login.
 *
 * Passwords never leave the station: the export writes the password column
 * empty (the stored hashes are unsalted MD5, see BACKLOG).  On import the
 * column sets the password of NEW users only; without it the account gets
 * a random password nobody knows, and an admin sets one under Settings ->
 * Users.  "replace" updates names, e-mail, phone, Skype, Jabber and the
 * type of an existing login - never its password, never a super admin,
 * never the own account's type, never the last admin away.
 */
class Application_Service_ImportExportUsers extends Application_Service_ImportExportType
{
    /** csv value -> cc_subjs.type; first entry per letter is the export value */
    const TYPES = [
        'admin' => UTYPE_ADMIN,
        'a' => UTYPE_ADMIN,
        'program_manager' => UTYPE_PROGRAM_MANAGER,
        'program manager' => UTYPE_PROGRAM_MANAGER,
        'pm' => UTYPE_PROGRAM_MANAGER,
        'p' => UTYPE_PROGRAM_MANAGER,
        'dj' => UTYPE_HOST,
        'host' => UTYPE_HOST,
        'h' => UTYPE_HOST,
        'guest' => UTYPE_GUEST,
        'g' => UTYPE_GUEST,
    ];

    public function type(): string
    {
        return 'users';
    }

    public function fileName(): string
    {
        return 'users.csv';
    }

    public function label(): string
    {
        return _('Users');
    }

    public function columns(): array
    {
        return ['login', 'type', 'first_name', 'last_name', 'email', 'cell_phone', 'skype', 'jabber', 'password'];
    }

    public function columnHelp(): array
    {
        return [
            'login' => 'user name (key)',
            'type' => 'admin, program_manager, dj or guest (empty = guest); super admins are never imported',
            'first_name' => 'first name',
            'last_name' => 'last name',
            'email' => 'e-mail address (required, as in the user dialog)',
            'cell_phone' => 'phone number',
            'skype' => 'Skype name',
            'jabber' => 'Jabber address',
            'password' => 'NEW users only, plain text, hashed on import; empty = random password (set one under Settings -> Users). Always empty in an export',
        ];
    }

    public function notices(): array
    {
        return [_('Passwords are never exported. The password column sets the password of new users only; without it the account gets a random password - set one under Settings -> Users. Existing logins keep their password.')];
    }

    public function exampleRows(): array
    {
        return [[
            'login' => 'dj-anna',
            'type' => 'dj',
            'first_name' => 'Anna',
            'last_name' => 'Example',
            'email' => 'anna@example.org',
            'cell_phone' => '',
            'skype' => '',
            'jabber' => '',
            'password' => '',
        ]];
    }

    public function count(): int
    {
        return (int) CcSubjsQuery::create()->count();
    }

    public function parse(string $content): array
    {
        $parsed = Application_Service_ImportExportService::csvParse($content);
        $email = new Zend_Validate_EmailAddress();
        $records = [];
        foreach ($parsed['rows'] as $row) {
            $rec = [
                'line' => $row['line'],
                'name' => $row['login'] ?? '',
                'type_in' => $row['type'] ?? '',
                'first_name' => $row['first_name'] ?? '',
                'last_name' => $row['last_name'] ?? '',
                'email' => $row['email'] ?? '',
                'cell_phone' => $row['cell_phone'] ?? '',
                'skype' => $row['skype'] ?? '',
                'jabber' => $row['jabber'] ?? '',
                'password' => $row['password'] ?? '',
                '_errors' => [],
            ];
            if ($rec['name'] === '') {
                $rec['_errors'][] = _('login is empty');
            }
            $rec['type'] = self::typeFromCsv($rec['type_in']);
            if ($rec['type'] === null) {
                $rec['_errors'][] = sprintf(_('type "%s" is unknown (admin, program_manager, dj, guest)'), $rec['type_in']);
            }
            if ($rec['email'] === '' || !$email->isValid($rec['email'])) {
                $rec['_errors'][] = _('email is empty or not a valid address');
            }
            if ($rec['jabber'] !== '' && !$email->isValid($rec['jabber'])) {
                $rec['_errors'][] = _('jabber must be an address like name@server');
            }
            $rec['summary'] = trim(($rec['type_in'] === '' ? 'guest' : $rec['type_in'])
                . ', ' . trim($rec['first_name'] . ' ' . $rec['last_name']) . ', ' . $rec['email'], ', ');
            $records[] = $rec;
        }

        return $records;
    }

    /** csv type -> cc_subjs.type; '' -> guest; unknown or super admin -> null */
    private static function typeFromCsv(string $value): ?string
    {
        $v = strtolower(trim($value));
        if ($v === '') {
            return UTYPE_GUEST;
        }

        return self::TYPES[$v] ?? null;
    }

    private static function typeToCsv(string $type): string
    {
        foreach (self::TYPES as $csv => $t) {
            if ($t === $type) {
                return $csv;
            }
        }

        return $type === UTYPE_SUPERADMIN ? 'admin' : 'guest';
    }

    private static function findUser(string $login): ?CcSubjs
    {
        return $login === '' ? null : CcSubjsQuery::create()->filterByDbLogin($login)->findOne();
    }

    /** admins (and super admins) other than $exceptId */
    private static function otherAdmins(int $exceptId): int
    {
        return (int) CcSubjsQuery::create()
            ->filterByDbType([UTYPE_ADMIN, UTYPE_SUPERADMIN], Criteria::IN)
            ->filterByDbId($exceptId, Criteria::NOT_EQUAL)
            ->count();
    }

    public function validate(array $record, array &$ctx): array
    {
        if (in_array($record['name'], $ctx['pending']['users'], true)) {
            return self::error(_('the same login appears twice in the file'));
        }
        $existing = self::findUser($record['name']);
        if ($existing === null) {
            return self::ok($record['password'] === '' ? [_('no password in the file - the account gets a random one; set it under Settings -> Users')] : []);
        }
        if ($ctx['conflict'] !== 'replace') {
            return self::skip(sprintf(_('a user with the login "%s" exists already'), $record['name']));
        }
        if ($existing->getDbType() === UTYPE_SUPERADMIN) {
            return self::error(_('the super admin is never changed by an import'));
        }
        if ((int) $existing->getDbId() === (int) $ctx['userId'] && $existing->getDbType() !== $record['type']) {
            return self::error(_('your own account keeps its type - change it in the user dialog'));
        }
        if ($existing->getDbType() === UTYPE_ADMIN && $record['type'] !== UTYPE_ADMIN
            && self::otherAdmins((int) $existing->getDbId()) === 0) {
            return self::error(_('the last admin cannot lose the admin type'));
        }
        $notes = [_('will update names, e-mail, phone, Skype, Jabber and type; the password stays')];
        if ($record['password'] !== '') {
            $notes[] = _('the password column is ignored for existing users');
        }

        return self::ok($notes);
    }

    public function create(array $record, array &$ctx): array
    {
        return self::atomically(function () use ($record) {
            $existing = self::findUser($record['name']);
            $user = new Application_Model_User($existing ? $existing->getDbId() : '');
            if ($existing === null) {
                $user->setLogin($record['name']);
                $user->setPassword($record['password'] !== '' ? $record['password'] : bin2hex(random_bytes(24)));
            }
            $user->setFirstName($record['first_name']);
            $user->setLastName($record['last_name']);
            if ($existing === null || $existing->getDbType() !== UTYPE_SUPERADMIN) {
                $user->setType($record['type']);
            }
            $user->setEmail($record['email']);
            $user->setCellPhone($record['cell_phone']);
            $user->setSkype($record['skype']);
            $user->setJabber($record['jabber']);
            $user->save();

            $messages = [$existing ? _('updated') : _('created')];
            if ($existing === null && $record['password'] === '') {
                $messages[] = _('random password - set one under Settings -> Users');
            }

            return ['status' => self::STATUS_OK, 'messages' => $messages, 'id' => (int) $user->getId()];
        }, ['CcSubjsPeer']);
    }

    public function export(array &$files): string
    {
        $con = Propel::getConnection();
        $st = $con->query('SELECT login, type, first_name, last_name, email, cell_phone, skype_contact, jabber_contact FROM cc_subjs ORDER BY lower(login)');
        $rows = [];
        foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $rows[] = [
                'login' => $r['login'],
                'type' => self::typeToCsv((string) $r['type']),
                'first_name' => (string) $r['first_name'],
                'last_name' => (string) $r['last_name'],
                'email' => (string) $r['email'],
                'cell_phone' => (string) $r['cell_phone'],
                'skype' => (string) $r['skype_contact'],
                'jabber' => (string) $r['jabber_contact'],
                'password' => '',
            ];
        }

        return Application_Service_ImportExportService::csvBuild($this->columns(), $rows);
    }
}
