<?php

/**
 * RASTATIME 2026-10-13 - shows.csv (Section 23.56).
 *
 * One row = one show as the Calendar's "New Show" dialog would create it.
 * The row is turned into the dialog's field array, validated by the same
 * forms (Application_Service_ShowFormService::validateShowForms, which
 * includes the overlap check for every repetition) and created by
 * Application_Service_ShowService::addUpdateShow.  Overlapping shows fail
 * validation and are not imported.
 *
 * Operator decisions (2026-10-11/13): the custom live password is never
 * read from or written to the CSV; "content" (stage 1) is the name of a
 * playlist that becomes the show's autoloading playlist; logos travel in
 * the bundle's logos/ folder.
 */
class Application_Service_ImportExportShows extends Application_Service_ImportExportType
{
    const REPEAT_IN = ['none' => -1, 'weekly' => 0, 'biweekly' => 1, 'every_2_weeks' => 1, 'every_3_weeks' => 4, 'every_4_weeks' => 5,
        'monthly_date' => 2, 'monthly_weekday' => 3, 'monthly' => 2, ];
    const REPEAT_OUT = [-1 => 'none', 0 => 'weekly', 1 => 'biweekly', 4 => 'every_3_weeks', 5 => 'every_4_weeks', 2 => 'monthly_date', 3 => 'monthly_weekday'];
    const DAYS = ['sun' => 0, 'so' => 0, 'mon' => 1, 'mo' => 1, 'tue' => 2, 'di' => 2, 'wed' => 3, 'mi' => 3, 'thu' => 4, 'do' => 4,
        'fri' => 5, 'fr' => 5, 'sat' => 6, 'sa' => 6, ];
    const DAY_OUT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    // RASTATIME 2026-10-15 - month selection of the monthly repeat types
    const MONTHS = ['jan' => 1, 'jän' => 1, 'feb' => 2, 'mar' => 3, 'mär' => 3, 'apr' => 4, 'may' => 5, 'mai' => 5,
        'jun' => 6, 'jul' => 7, 'aug' => 8, 'sep' => 9, 'oct' => 10, 'okt' => 10, 'nov' => 11, 'dec' => 12, 'dez' => 12, ];
    const MONTH_OUT = [1 => 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    public function type(): string
    {
        return 'shows';
    }

    public function fileName(): string
    {
        return 'shows.csv';
    }

    public function label(): string
    {
        return _('Shows');
    }

    public function columns(): array
    {
        return ['name', 'url', 'genre', 'description', 'start_date', 'start_time', 'end_date', 'end_time', 'timezone',
            'allow_delayed_start', 'repeats', 'repeat_type', 'days', 'months', 'repeat_end_date', 'no_end', 'linked', 'record',
            'content', 'content_repeat', 'intro_playlist', 'outro_playlist', 'repeat_of', 'rastatime_auth', 'custom_auth', 'custom_username',
            'djs', 'background_color', 'text_color', 'logo', ];
    }

    public function columnHelp(): array
    {
        return [
            'name' => 'show name (required)',
            'url, genre, description' => 'free text',
            'start_date, start_time' => 'first broadcast: YYYY-MM-DD and HH:MM (station timezone unless "timezone" is set)',
            'end_date, end_time' => 'end of that broadcast; end_date may be empty (same day, or next day when end_time <= start_time)',
            'timezone' => 'IANA name, e.g. Europe/Berlin; empty = station default',
            'allow_delayed_start' => 'yes/no',
            'repeats' => 'yes/no; repeat_type: none | weekly | biweekly | every_3_weeks | every_4_weeks | monthly_date | monthly_weekday',
            'days' => 'for weekly types: Mon,Tue,Wed,Thu,Fri,Sat,Sun (also Mo,Di,Mi,Do,Fr,Sa,So); empty = weekday of start_date',
            'months' => 'for monthly types: Jan,Feb,...,Dec or 1..12 (German short names work too); empty = every month',
            'repeat_end_date, no_end' => 'last date of the repetition, or no_end = yes',
            'linked' => 'yes/no - all instances share one content',
            'record' => 'yes/no - record this show',
            'content' => 'name of a playlist used as autoloading playlist (fills every instance); content_repeat = yes repeats it until the show is full',
            'intro_playlist, outro_playlist' => 'playlist names, empty = station default',
            'repeat_of' => 'name of an existing show whose last aired content fills this show shortly before it starts; empty = none',
            'rastatime_auth, custom_auth' => 'yes/no - live DJ authentication; custom_username goes with custom_auth',
            'djs' => 'DJ logins, comma separated',
            'background_color, text_color' => 'hex without #, e.g. 1F7A8C and FFFFFF',
            'logo' => 'file name inside the bundle folder logos/ (jpg, png, gif)',
        ];
    }

    public function notices(): array
    {
        return [
            _('For security the custom live password is never part of the file: shows with custom authentication are imported without a password - set it in the Calendar afterwards. The export leaves the field out for the same reason.'),
            _('A row whose time overlaps an existing show (or an earlier row of this import) is not imported.'),
        ];
    }

    public function exampleRows(): array
    {
        $monday = date('Y-m-d', strtotime('next monday'));

        return [[
            'name' => 'Morning Show', 'url' => 'https://example.org/morning', 'genre' => 'Talk', 'description' => 'Wake-up programme',
            'start_date' => $monday, 'start_time' => '07:00', 'end_date' => '', 'end_time' => '09:00', 'timezone' => '',
            'allow_delayed_start' => 'no', 'repeats' => 'yes', 'repeat_type' => 'weekly', 'days' => 'Mon,Tue,Wed,Thu,Fri',
            'repeat_end_date' => '', 'no_end' => 'yes', 'linked' => 'no', 'record' => 'no',
            'content' => 'Morning Show', 'content_repeat' => 'yes', 'intro_playlist' => '', 'outro_playlist' => '', 'repeat_of' => '',
            'rastatime_auth' => 'yes', 'custom_auth' => 'no', 'custom_username' => '', 'djs' => 'dj1',
            'background_color' => '1F7A8C', 'text_color' => 'FFFFFF', 'logo' => 'morning-show.png',
        ]];
    }

    public function count(): int
    {
        $con = Propel::getConnection();

        return (int) $con->query("SELECT count(*) FROM cc_show s WHERE EXISTS (SELECT 1 FROM cc_show_instances i WHERE i.show_id = s.id AND i.ends > now() AT TIME ZONE 'UTC' AND i.modified_instance = false)")->fetchColumn();
    }

    // ------------------------------------------------------------------
    // parse
    // ------------------------------------------------------------------

    private static function parseDate(string $v): ?string
    {
        $v = trim($v);
        if ($v === '') {
            return null;
        }
        if (preg_match('/^(\d{4})-(\d{1,2})-(\d{1,2})$/', $v, $m) || preg_match('/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/', $v, $n)) {
            [$y, $mo, $d] = isset($m[1]) ? [$m[1], $m[2], $m[3]] : [$n[3], $n[2], $n[1]];
            if (checkdate((int) $mo, (int) $d, (int) $y)) {
                return sprintf('%04d-%02d-%02d', $y, $mo, $d);
            }
        }

        return null;
    }

    private static function parseTime(string $v): ?string
    {
        $v = trim($v);
        if (preg_match('/^(\d{1,2}):(\d{2})(?::\d{2})?$/', $v, $m) && (int) $m[1] < 24 && (int) $m[2] < 60) {
            return sprintf('%02d:%02d', $m[1], $m[2]);
        }

        return null;
    }

    private static function parseColor(string $v): ?string
    {
        $v = ltrim(trim($v), '#');
        if ($v === '') {
            return '';
        }

        return preg_match('/^[0-9a-fA-F]{6}$/', $v) ? strtolower($v) : null;
    }

    public function parse(string $content): array
    {
        $parsed = Application_Service_ImportExportService::csvParse($content);
        $defaultTz = Application_Model_Preference::GetDefaultTimezone();
        $records = [];
        foreach ($parsed['rows'] as $row) {
            $g = static fn ($k) => trim((string) ($row[$k] ?? ''));
            $rec = ['line' => $row['line'], 'name' => $g('name'), '_errors' => []];
            if ($rec['name'] === '') {
                $rec['_errors'][] = _('name is empty');
            }
            foreach (['url', 'genre', 'description', 'custom_username', 'content', 'intro_playlist', 'outro_playlist'] as $k) {
                $rec[$k] = $g($k);
            }
            $rec['timezone'] = $g('timezone') !== '' ? $g('timezone') : $defaultTz;
            if (!in_array($rec['timezone'], timezone_identifiers_list(), true)) {
                $rec['_errors'][] = sprintf(_('unknown timezone "%s"'), $rec['timezone']);
                $rec['timezone'] = $defaultTz;
            }
            $rec['start_date'] = self::parseDate($g('start_date'));
            $rec['start_time'] = self::parseTime($g('start_time'));
            $rec['end_time'] = self::parseTime($g('end_time'));
            $rec['end_date'] = $g('end_date') === '' ? null : self::parseDate($g('end_date'));
            if ($rec['start_date'] === null) {
                $rec['_errors'][] = _('start_date must be YYYY-MM-DD');
            }
            if ($rec['start_time'] === null) {
                $rec['_errors'][] = _('start_time must be HH:MM');
            }
            if ($rec['end_time'] === null) {
                $rec['_errors'][] = _('end_time must be HH:MM');
            }
            if ($g('end_date') !== '' && $rec['end_date'] === null) {
                $rec['_errors'][] = _('end_date must be YYYY-MM-DD');
            }
            $rec['duration_seconds'] = 0;
            if ($rec['start_date'] && $rec['start_time'] && $rec['end_time']) {
                try {
                    $tz = new DateTimeZone($rec['timezone']);
                    $start = new DateTime($rec['start_date'] . ' ' . $rec['start_time'], $tz);
                    $endDate = $rec['end_date'] ?? $rec['start_date'];
                    $end = new DateTime($endDate . ' ' . $rec['end_time'], $tz);
                    if ($rec['end_date'] === null && $end <= $start) {
                        $end->modify('+1 day');
                    }
                    $rec['end_date'] = $end->format('Y-m-d');
                    $rec['duration_seconds'] = $end->getTimestamp() - $start->getTimestamp();
                    if ($rec['duration_seconds'] <= 0 || $rec['duration_seconds'] > 86400) {
                        $rec['_errors'][] = _('the show must be longer than 0 and at most 24 hours');
                    }
                } catch (Exception $e) {
                    $rec['_errors'][] = $e->getMessage();
                }
            }
            $repeatType = strtolower(str_replace(['-', ' '], '_', $g('repeat_type')));
            $rec['repeats'] = self::toBool($g('repeats')) || ($repeatType !== '' && $repeatType !== 'none');
            if ($rec['repeats']) {
                if ($repeatType === '' || $repeatType === 'none') {
                    $repeatType = 'weekly';
                }
                if (!isset(self::REPEAT_IN[$repeatType]) || self::REPEAT_IN[$repeatType] === -1) {
                    $rec['_errors'][] = sprintf(_('unknown repeat_type "%s"'), $g('repeat_type'));
                    $repeatType = 'weekly';
                }
            } else {
                $repeatType = 'none';
            }
            $rec['repeat_type'] = $repeatType;
            $rec['days'] = [];
            foreach (self::splitList($g('days')) as $d) {
                $k = strtolower(substr($d, 0, 3));
                if (ctype_digit($d) && (int) $d <= 6) {
                    $rec['days'][] = (int) $d;
                } elseif (isset(self::DAYS[$k]) || isset(self::DAYS[substr($k, 0, 2)])) {
                    $rec['days'][] = self::DAYS[$k] ?? self::DAYS[substr($k, 0, 2)];
                } else {
                    $rec['_errors'][] = sprintf(_('unknown day "%s"'), $d);
                }
            }
            $rec['days'] = array_values(array_unique($rec['days']));
            if ($rec['repeats'] && in_array(self::REPEAT_IN[$repeatType] ?? -1, [0, 1, 4, 5], true) && !$rec['days'] && $rec['start_date']) {
                $rec['days'] = [(int) date('w', strtotime($rec['start_date']))];
            }
            // RASTATIME 2026-10-15 - month selection of the monthly types (empty = every month)
            $rec['months'] = [];
            foreach (self::splitList($g('months')) as $mo) {
                $k = mb_strtolower(mb_substr($mo, 0, 3));
                if (ctype_digit($mo) && (int) $mo >= 1 && (int) $mo <= 12) {
                    $rec['months'][] = (int) $mo;
                } elseif (isset(self::MONTHS[$k])) {
                    $rec['months'][] = self::MONTHS[$k];
                } else {
                    $rec['_errors'][] = sprintf(_('unknown month "%s"'), $mo);
                }
            }
            $rec['months'] = array_values(array_unique($rec['months']));
            sort($rec['months']);
            $rec['repeat_end_date'] = $g('repeat_end_date') === '' ? null : self::parseDate($g('repeat_end_date'));
            if ($g('repeat_end_date') !== '' && $rec['repeat_end_date'] === null) {
                $rec['_errors'][] = _('repeat_end_date must be YYYY-MM-DD');
            }
            $rec['no_end'] = $rec['repeats'] && ($rec['repeat_end_date'] === null || self::toBool($g('no_end')));
            foreach (['allow_delayed_start', 'linked', 'record', 'content_repeat', 'rastatime_auth', 'custom_auth'] as $b) {
                $rec[$b] = self::toBool($g($b));
            }
            if ($g('rastatime_auth') === '' && $g('custom_auth') === '') {
                $rec['rastatime_auth'] = true;          // the dialog's default
            }
            $rec['djs'] = self::splitList($g('djs'));
            $rec['repeat_of'] = trim((string) $g('repeat_of')); // RASTATIME 2026-10-18
            $rec['background_color'] = self::parseColor($g('background_color'));
            $rec['text_color'] = self::parseColor($g('text_color'));
            if ($rec['background_color'] === null || $rec['text_color'] === null) {
                $rec['_errors'][] = _('colours must be 6 hex digits, e.g. 1F7A8C');
            }
            $rec['logo'] = basename(str_replace('\\', '/', $g('logo')));
            $when = ($rec['start_date'] ?? '?') . ' ' . ($rec['start_time'] ?? '?') . '-' . ($rec['end_time'] ?? '?');
            $rec['summary'] = $when . ($rec['repeats'] ? ', ' . $repeatType . ($rec['days'] ? ' ' . implode(',', array_map(static fn ($d) => self::DAY_OUT[$d], $rec['days'])) : '') : '');
            $records[] = $rec;
        }

        return $records;
    }

    // ------------------------------------------------------------------
    // the dialog's field array
    // ------------------------------------------------------------------

    /** @return array{0:?int,1:?string} id or null; message when not found; 0 = pending in this import */
    private static function playlistRef(string $name, array $ctx): array
    {
        if ($name === '') {
            return [null, null];
        }
        if (isset($ctx['created']['playlists'][$name])) {
            return [(int) $ctx['created']['playlists'][$name], null];
        }
        $id = self::findPlaylistIdByName($name);
        if ($id !== null) {
            return [$id, null];
        }
        if (in_array($name, $ctx['pending']['playlists'], true)) {
            return [0, null];
        }

        return [null, sprintf(_('playlist "%s" not found'), $name)];
    }

    /** DJ logins -> user ids; only users of type DJ/host can be assigned (the dialog's list). */
    private static function hostIds(array $logins, array &$messages): array
    {
        $ids = [];
        foreach ($logins as $login) {
            $u = CcSubjsQuery::create()->filterByDbLogin($login)->findOne();
            if ($u === null) {
                $messages[] = sprintf(_('DJ "%s" not found'), $login);
            } elseif ($u->getDbType() !== 'H') {
                $messages[] = sprintf(_('user "%s" is not a DJ (user type DJ) and cannot be assigned'), $login);
            } else {
                $ids[] = (string) $u->getDbId();
            }
        }

        return $ids;
    }

    /** A password the dialog accepts; never shown, never from the file (operator decision 2026-10-13). */
    private static function randomPassword(): string
    {
        return bin2hex(random_bytes(12));
    }

    private static function csrfToken(): string
    {
        $ns = new Zend_Session_Namespace('csrf_namespace');
        if (empty($ns->authtoken)) {
            $ns->authtoken = sha1(uniqid((string) mt_rand(), true));
        }

        return (string) $ns->authtoken;
    }

    /**
     * Build the New-Show field array.  Playlists that this import creates
     * later are left empty during the preview (they do not exist yet) and
     * reported as a note.
     */
    private function formData(array $record, array $ctx, array &$messages, array &$notes): array
    {
        [$contentId, $m1] = self::playlistRef($record['content'], $ctx);
        [$introId, $m2] = self::playlistRef($record['intro_playlist'], $ctx);
        [$outroId, $m3] = self::playlistRef($record['outro_playlist'], $ctx);
        foreach ([$m1, $m2, $m3] as $m) {
            if ($m !== null) {
                $messages[] = $m;
            }
        }
        foreach ([[$contentId, $record['content']], [$introId, $record['intro_playlist']], [$outroId, $record['outro_playlist']]] as [$id, $name]) {
            if ($id === 0) {
                $notes[] = sprintf(_('playlist "%s" is created by this import'), $name);
            }
        }
        $hosts = self::hostIds($record['djs'], $messages);
        // RASTATIME 2026-10-18 - "Repeat of show" by name of an existing show
        $repeatOfId = 0;
        if (($record['repeat_of'] ?? '') !== '') {
            $repeatOfId = (int) (Application_Service_RepeatFillService::findShowIdByName($record['repeat_of']) ?? 0);
            if ($repeatOfId === 0) {
                $notes[] = sprintf(_('source show "%s" (repeat_of) not found - imported without it'), $record['repeat_of']);
            }
        }
        if ($record['logo'] !== '' && !isset($ctx['logos'][$record['logo']])) {
            $messages[] = sprintf(_('logo "%s" is not in the bundle (folder logos/)'), $record['logo']);
        }
        $h = intdiv($record['duration_seconds'], 3600);
        $m = intdiv($record['duration_seconds'] % 3600, 60);
        $repeatCode = self::REPEAT_IN[$record['repeat_type']] ?? -1;

        return [
            'add_show_id' => '-1',                   // -1 = new show (the dialog's convention)
            'add_show_instance_id' => '-1',
            'add_show_instance_description' => '',
            'add_show_name' => $record['name'],
            'add_show_url' => $record['url'],
            'add_show_genre' => $record['genre'],
            'add_show_description' => $record['description'],
            'add_show_start_now' => 'future',
            'add_show_start_date' => $record['start_date'],
            'add_show_start_time' => $record['start_time'],
            'add_show_end_date_no_repeat' => $record['end_date'],
            'add_show_end_time' => $record['end_time'],
            'add_show_duration' => $h . 'h ' . $m . 'm',
            'add_show_timezone' => $record['timezone'],
            'add_show_allow_delayed_start' => $record['allow_delayed_start'] ? 1 : 0,
            'add_show_repeats' => $record['repeats'] ? 1 : 0,
            'add_show_repeat_type' => $record['repeats'] ? (string) (in_array($repeatCode, [2, 3], true) ? 2 : $repeatCode) : '0',
            'add_show_monthly_repeat_type' => (string) ($repeatCode === 3 ? 3 : 2),
            'add_show_day_check' => $record['repeats'] ? array_map('strval', $record['days']) : null,
            'add_show_month_check' => ($record['repeats'] && !empty($record['months'])) ? array_map('strval', $record['months']) : [],
            'add_show_end_date' => $record['repeat_end_date'] ?? $record['start_date'],
            'add_show_no_end' => $record['no_end'] ? 1 : 0,
            'add_show_linked' => $record['linked'] ? 1 : 0,
            'add_show_record' => $record['record'] ? 1 : 0,
            'add_show_rebroadcast' => 0,
            'add_show_has_autoplaylist' => $contentId ? 1 : 0,
            'add_show_autoplaylist_id' => $contentId ? (string) $contentId : '',
            'add_show_autoplaylist_repeat' => ($contentId && $record['content_repeat']) ? 1 : 0,
            'add_show_intro_playlist_id' => $introId ? (string) $introId : '',
            'add_show_outro_playlist_id' => $outroId ? (string) $outroId : '',
            'add_show_repeat_of' => $repeatOfId,
            'cb_airtime_auth' => $record['rastatime_auth'] ? 1 : 0,
            'cb_custom_auth' => $record['custom_auth'] ? 1 : 0,
            'custom_username' => $record['custom_auth'] ? $record['custom_username'] : '',
            // never from the file (operator decision 2026-10-13): a random one, to be set in the Calendar
            'custom_password' => $record['custom_auth'] ? self::randomPassword() : '',
            'add_show_hosts' => $hosts ?: null,
            'add_show_color' => $record['text_color'],
            'add_show_background_color' => $record['background_color'],
            // the Style form carries the session's CSRF token as a required element
            'csrf' => self::csrfToken(),
        ];
    }

    /** Flatten Zend_Form::getMessages() (nested for sub-forms / multi elements). */
    private static function flattenMessages($errors, string $prefix, array &$out): void
    {
        foreach ((array) $errors as $key => $msg) {
            if (is_array($msg)) {
                self::flattenMessages($msg, is_string($key) && !is_numeric($key) ? preg_replace('/^add_show_/', '', $key) : $prefix, $out);
            } else {
                $out[] = ($prefix !== '' ? $prefix . ': ' : '') . (string) $msg;
            }
        }
    }

    private static function formMessages(array $forms): array
    {
        $out = [];
        foreach ($forms as $form) {
            foreach ($form->getMessages() as $element => $errors) {
                self::flattenMessages($errors, preg_replace('/^add_show_/', '', (string) $element), $out);
            }
        }

        return array_values(array_unique($out));
    }

    public function validate(array $record, array &$ctx): array
    {
        $messages = [];
        $notes = [];
        $data = $this->formData($record, $ctx, $messages, $notes);
        if ($messages) {
            return self::error($messages);
        }
        $fs = new Application_Service_ShowFormService();
        $forms = $fs->createShowForms();
        $fs->populateNewShowForms($forms['what'], $forms['when'], $forms['repeats']);
        if (!$fs->validateShowForms($forms, $data)) {
            $m = self::formMessages($forms);

            return self::error($m ?: [_('the show dialog rejected the row')]);
        }
        if ($record['custom_auth']) {
            $notes[] = _('custom authentication: a random password will be set - change it in the Calendar');
        }

        return self::ok($notes);
    }

    private static function storeLogo(int $showId, string $sourcePath): ?string
    {
        $ext = strtolower(pathinfo($sourcePath, PATHINFO_EXTENSION));
        if (!in_array($ext, ['jpg', 'jpeg', 'png', 'gif'], true)) {
            return null;
        }
        $dir = rtrim(Application_Common_Storage::root(), '/\\') . '/imported/show-images/' . $showId;
        if (!is_dir($dir) && !mkdir($dir, 0777, true)) {
            return null;
        }
        $target = $dir . '/' . $showId . '-' . preg_replace('/[^A-Za-z0-9._-]/', '_', basename($sourcePath));
        if (!copy($sourcePath, $target)) {
            return null;
        }
        $show = CcShowQuery::create()->findPk($showId);
        if ($show) {
            $show->setDbImagePath(Application_Common_Storage::toRelative($target));
            $show->save();
        }

        return $target;
    }

    public function create(array $record, array &$ctx): array
    {
        $messages = [];
        $notes = [];
        $data = $this->formData($record, $ctx, $messages, $notes);
        if ($messages) {
            return self::error($messages);
        }
        foreach (['add_show_autoplaylist_id', 'add_show_intro_playlist_id', 'add_show_outro_playlist_id'] as $k) {
            if ($data[$k] === '0' && $notes) {
                // a playlist of this import that was not created after all
            }
        }
        $fs = new Application_Service_ShowFormService();
        $forms = $fs->createShowForms();
        $fs->populateNewShowForms($forms['what'], $forms['when'], $forms['repeats']);
        if (!$fs->validateShowForms($forms, $data)) {
            return self::error(self::formMessages($forms) ?: [_('the show dialog rejected the row')]);
        }
        $service = new Application_Service_ShowService(null, $data);
        $showId = (int) $service->addUpdateShow($data);
        $done = [_('created')];
        if ($record['logo'] !== '' && isset($ctx['logos'][$record['logo']])) {
            if (self::storeLogo($showId, $ctx['logos'][$record['logo']]) === null) {
                $done[] = _('logo could not be stored');
            } else {
                $done[] = _('logo stored');
            }
        }
        if ($record['custom_auth']) {
            $done[] = _('custom authentication: a random password was set - change it in the Calendar');
        }

        return ['status' => self::STATUS_OK, 'messages' => $done, 'id' => $showId];
    }

    // ------------------------------------------------------------------
    // export: every show with an upcoming instance, start = next instance
    // ------------------------------------------------------------------

    public function export(array &$files): string
    {
        $con = Propel::getConnection();
        $sql = <<<'SQL'
            SELECT s.id, s.name, s.url, s.genre, s.description, s.color, s.background_color,
                   s.live_stream_using_airtime_auth, s.live_stream_using_custom_auth, s.live_stream_user,
                   s.linked, s.image_path, s.has_autoplaylist, s.autoplaylist_id, s.autoplaylist_repeat,
                   s.override_intro_playlist, s.intro_playlist_id, s.override_outro_playlist, s.outro_playlist_id,
                   s.allow_delayed_start,
                   (SELECT min(i.starts) FROM cc_show_instances i WHERE i.show_id = s.id AND i.ends > now() AT TIME ZONE 'UTC' AND i.modified_instance = false) AS next_start
              FROM cc_show s
             WHERE EXISTS (SELECT 1 FROM cc_show_instances i WHERE i.show_id = s.id AND i.ends > now() AT TIME ZONE 'UTC' AND i.modified_instance = false)
             ORDER BY next_start, lower(s.name)
SQL;
        $rows = [];
        $playlistNames = [];
        foreach ($con->query('SELECT id, name FROM cc_playlist')->fetchAll(PDO::FETCH_ASSOC) as $p) {
            $playlistNames[(int) $p['id']] = $p['name'];
        }
        // RASTATIME 2026-10-18 - "Repeat of show" (own query: tolerates migration 0071 pending)
        $repeatOfAll = Application_Service_RepeatFillService::allRepeatOf();
        $showNames = [];
        foreach ($con->query('SELECT id, name FROM cc_show')->fetchAll(PDO::FETCH_ASSOC) as $p) {
            $showNames[(int) $p['id']] = $p['name'];
        }
        $daysStmt = $con->prepare('SELECT first_show, last_show, start_time, timezone, duration, day, repeat_type, record, month_mask FROM cc_show_days WHERE show_id = :id ORDER BY id');
        $hostStmt = $con->prepare('SELECT u.login FROM cc_show_hosts h JOIN cc_subjs u ON u.id = h.subjs_id WHERE h.show_id = :id ORDER BY u.login');
        foreach ($con->query($sql)->fetchAll(PDO::FETCH_ASSOC) as $s) {
            $daysStmt->execute([':id' => $s['id']]);
            $days = $daysStmt->fetchAll(PDO::FETCH_ASSOC);
            if (!$days) {
                continue;
            }
            $first = $days[0];
            $repeat = (int) $first['repeat_type'];
            $tz = $first['timezone'] ?: Application_Model_Preference::GetDefaultTimezone();
            try {
                $zone = new DateTimeZone($tz);
            } catch (Exception $e) {
                $zone = new DateTimeZone('UTC');
            }
            $nextLocal = (new DateTime($s['next_start'], new DateTimeZone('UTC')))->setTimezone($zone);
            $startTime = substr((string) $first['start_time'], 0, 5);
            $durationSec = self::intervalToSeconds((string) $first['duration']);
            $startLocal = new DateTime($nextLocal->format('Y-m-d') . ' ' . $startTime, $zone);
            $endLocal = (clone $startLocal)->modify('+' . max(0, $durationSec) . ' seconds');
            $dayNames = [];
            if (in_array($repeat, [0, 1, 4, 5], true)) {
                foreach ($days as $d) {
                    if ($d['day'] !== null) {
                        $dayNames[] = self::DAY_OUT[(int) $d['day']];
                    }
                }
            }
            // RASTATIME 2026-10-15 - months of a monthly repeat (empty = every month)
            $monthNames = [];
            if (in_array($repeat, [2, 3], true)) {
                $mask = (int) ($first['month_mask'] ?? 4095);
                if ($mask !== 4095) {
                    for ($mo = 1; $mo <= 12; ++$mo) {
                        if ($mask & (1 << ($mo - 1))) {
                            $monthNames[] = self::MONTH_OUT[$mo];
                        }
                    }
                }
            }
            $hostStmt->execute([':id' => $s['id']]);
            $logos = '';
            if (!empty($s['image_path'])) {
                $abs = Application_Common_Storage::toAbsolute($s['image_path']);
                if (is_file($abs)) {
                    $logoName = 'show-' . $s['id'] . '-' . preg_replace('/[^A-Za-z0-9._-]/', '_', basename($abs));
                    $files[Application_Service_ImportExportService::LOGO_PREFIX . $logoName] = (string) file_get_contents($abs);
                    $logos = $logoName;
                }
            }
            $pg = static fn ($v) => $v === true || $v === 't' || $v === '1' || $v === 1;
            $rows[] = [
                'name' => $s['name'],
                'url' => (string) $s['url'],
                'genre' => (string) $s['genre'],
                'description' => (string) $s['description'],
                'start_date' => $startLocal->format('Y-m-d'),
                'start_time' => $startLocal->format('H:i'),
                'end_date' => $endLocal->format('Y-m-d') === $startLocal->format('Y-m-d') ? '' : $endLocal->format('Y-m-d'),
                'end_time' => $endLocal->format('H:i'),
                'timezone' => $tz,
                'allow_delayed_start' => self::boolOut($pg($s['allow_delayed_start'])),
                'repeats' => self::boolOut($repeat !== -1),
                'repeat_type' => self::REPEAT_OUT[$repeat] ?? 'none',
                'days' => implode(',', array_unique($dayNames)),
                'months' => implode(',', $monthNames),
                // cc_show_days.last_show is the day AFTER the last broadcast (exclusive) - the dialog's 'Date End' is inclusive
                'repeat_end_date' => $repeat !== -1 && $first['last_show'] ? (new DateTime((string) $first['last_show']))->modify('-1 day')->format('Y-m-d') : '',
                'no_end' => self::boolOut($repeat !== -1 && !$first['last_show']),
                'linked' => self::boolOut($pg($s['linked'])),
                'record' => self::boolOut((int) $first['record'] === 1),
                'content' => $pg($s['has_autoplaylist']) && $s['autoplaylist_id'] ? ($playlistNames[(int) $s['autoplaylist_id']] ?? '') : '',
                'content_repeat' => self::boolOut($pg($s['autoplaylist_repeat'])),
                'intro_playlist' => $pg($s['override_intro_playlist']) && $s['intro_playlist_id'] ? ($playlistNames[(int) $s['intro_playlist_id']] ?? '') : '',
                'outro_playlist' => $pg($s['override_outro_playlist']) && $s['outro_playlist_id'] ? ($playlistNames[(int) $s['outro_playlist_id']] ?? '') : '',
                'repeat_of' => isset($repeatOfAll[(int) $s['id']]) ? ($showNames[$repeatOfAll[(int) $s['id']]] ?? '') : '',
                'rastatime_auth' => self::boolOut($pg($s['live_stream_using_airtime_auth'])),
                'custom_auth' => self::boolOut($pg($s['live_stream_using_custom_auth'])),
                'custom_username' => (string) $s['live_stream_user'],
                'djs' => implode(',', $hostStmt->fetchAll(PDO::FETCH_COLUMN)),
                'background_color' => (string) $s['background_color'],
                'text_color' => (string) $s['color'],
                'logo' => $logos,
            ];
        }

        return Application_Service_ImportExportService::csvBuild($this->columns(), $rows);
    }
}
