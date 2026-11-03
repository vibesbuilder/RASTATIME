<?php

/**
 * RASTATIME 2026-11-03 - archiving stage 1 (CBA archiving, migrations
 * 0074 and 0075): editorial team profiles, per-show archiving defaults, per-episode
 * data (episode = show instance) with an optional image, and the yearly
 * participants overview (Analytics → Participants).
 *
 * Propel classes are not generated for the four tables; everything here is
 * raw SQL like Application_Service_RepeatFillService, and every reader
 * returns empty defaults while the tables are missing (tablesReady()).
 */
class Application_Service_ArchivingService
{
    public const EPISODE_IMAGE_MAX_BYTES = 10485760;   // 10 MiB

    private const IMAGE_TYPES = ['image/jpeg' => 'jpg', 'image/png' => 'png'];

    private static $ready;

    public static function tablesReady(): bool
    {
        if (self::$ready === null) {
            $n = Propel::getConnection()->query(
                "SELECT count(*) FROM information_schema.tables
                  WHERE table_schema = current_schema()
                    AND table_name IN ('cc_editor_profile', 'cc_show_editor_profile', 'cc_show_archiving', 'cc_episode',
                                       'cc_cba_account', 'cc_cba_upload')"
            )->fetchColumn();
            self::$ready = ((int) $n === 6);
        }

        return self::$ready;
    }

    /**
     * CBA licence keys of the zipupload API (meta "license"; "image_license"
     * takes any text, the same list is offered) => label.  Stage 2: the list
     * of the API specification (no "cc by-sa"; "cc sampling+" added).
     */
    public static function licenseOptions(): array
    {
        return [
            '' => _('(not set)'),
            'copyright' => _('All rights reserved'),
            'cc by' => 'CC BY',
            'cc by-nc' => 'CC BY-NC',
            'cc by-nd' => 'CC BY-ND',
            'cc by-nc-nd' => 'CC BY-NC-ND',
            'cc zero' => 'CC0',
            'cc sampling+' => 'CC Sampling+',
            'pd' => _('Public domain'),
        ];
    }

    /**
     * Help for the licence choice (operator 2026-11-03): which licence
     * answers the questions of the CBA web form - attribution, commercial
     * use, adaptations.  HTML for rtTooltip.
     */
    public static function licenseMatrixHtml(): string
    {
        $h = fn ($v) => htmlspecialchars((string) $v, ENT_QUOTES);
        $yes = $h(_('yes'));
        $no = $h(_('no'));
        $rows = [
            ['CC BY', $yes, $yes, $yes],
            ['CC BY-NC', $yes, $no, $yes],
            ['CC BY-ND', $yes, $yes, $no],
            ['CC BY-NC-ND', $yes, $no, $no],
            ['CC0', $no, $yes, $yes],
        ];
        $html = '<table class="rt-license-matrix"><tr><th>' . $h(_('Licence')) . '</th><th>' . $h(_('Credit the author?'))
            . '</th><th>' . $h(_('Commercial use?')) . '</th><th>' . $h(_('Adaptations?')) . '</th></tr>';
        foreach ($rows as $r) {
            $html .= '<tr><td>' . implode('</td><td>', $r) . '</td></tr>';
        }

        return $html . '</table><p>' . $h(_('All rights reserved: none of it is allowed without asking. CC Sampling+: samples may be reused, the whole work only non-commercially. Public domain: no rights at all.')) . '</p>';
    }

    /** Language codes the CBA accepts (API specification 2026-11). */
    public const CBA_LANGUAGES = ['de', 'en', 'fr', 'sl', 'tr', 'da', 'es', 'cs', 'pt', 'ar', 'sr', 'hr', 'pl', 'it', 'et',
        'ce', 'lv', 'fi', 'ro', 'ru', 'hu', 'lt', 'nl', 'zh', 'fa', 'rm', 'yi', 'th', 'he', 'bg', 'is', 'no', 'bs', 'sv',
        'el', 'sq', 'az', 'ja', 'ko', 'ku', 'sk', 'mk', 'am', 'si', 'ur', 'so', 'uk', 'eo'];

    /** Visibility of an archived episode on cba.media (meta "status"). */
    public static function statusOptions(): array
    {
        return [
            'publish' => _('Public'),
            'unlisted' => _('Unlisted'),
            'private' => _('Private'),
        ];
    }

    /** Audio formats the CBA takes in the ZIP (and RASTATIME can name). */
    public const AUDIO_EXTENSIONS = ['mp3', 'ogg', 'opus'];

    private static function query(string $sql, array $params = []): array
    {
        $st = Propel::getConnection()->prepare($sql);
        $st->execute($params);

        return $st->fetchAll(PDO::FETCH_ASSOC);
    }

    private static function exec(string $sql, array $params = []): int
    {
        $st = Propel::getConnection()->prepare($sql);
        $st->execute($params);

        return $st->rowCount();
    }

    private static function intOrNull($v): ?int
    {
        $v = trim((string) $v);

        return $v === '' ? null : (int) $v;
    }

    // ------------------------------------------------------------------
    // Editorial team profiles
    // ------------------------------------------------------------------

    /** All profiles with their login (if linked) and the number of shows. */
    public static function profiles(): array
    {
        if (!self::tablesReady()) {
            return [];
        }

        return self::query(
            'SELECT p.id, p.name, p.email, p.subjs_id, s.login, p.active,
                    (SELECT count(*) FROM cc_show_editor_profile se WHERE se.profile_id = p.id) AS shows
               FROM cc_editor_profile p
               LEFT JOIN cc_subjs s ON s.id = p.subjs_id
              ORDER BY lower(p.name), p.id'
        );
    }

    /**
     * Create (id 0) or update a profile.
     *
     * @return array [int id, ?string error]
     */
    public static function saveProfile(int $id, string $name, string $email, int $subjsId, bool $active): array
    {
        $name = trim($name);
        $email = trim($email);
        if ($name === '') {
            return [0, _('Please enter a name.')];
        }
        if (mb_strlen($name) > 255) {
            return [0, _('The name is too long (255 characters at most).')];
        }
        if ($email !== '' && (mb_strlen($email) > 255 || !filter_var($email, FILTER_VALIDATE_EMAIL))) {
            return [0, _('Please enter a valid email address or leave the field empty.')];
        }
        if ($subjsId > 0 && !self::query('SELECT 1 FROM cc_subjs WHERE id = ?', [$subjsId])) {
            return [0, _('The chosen user does not exist any more.')];
        }
        $params = [$name, $email === '' ? null : $email, $subjsId > 0 ? $subjsId : null, $active ? 't' : 'f'];
        if ($id > 0) {
            $params[] = $id;
            if (!self::exec('UPDATE cc_editor_profile SET name = ?, email = ?, subjs_id = ?, active = ? WHERE id = ?', $params)) {
                return [0, _('The profile does not exist any more.')];
            }

            return [$id, null];
        }
        $row = self::query('INSERT INTO cc_editor_profile (name, email, subjs_id, active) VALUES (?, ?, ?, ?) RETURNING id', $params);

        return [(int) $row[0]['id'], null];
    }

    public static function deleteProfile(int $id): bool
    {
        return self::exec('DELETE FROM cc_editor_profile WHERE id = ?', [$id]) > 0;
    }

    /** Options for the show form: active profiles plus inactive ones still linked to the show. */
    public static function profileOptions(int $showId = 0): array
    {
        if (!self::tablesReady()) {
            return [];
        }
        $rows = self::query(
            'SELECT p.id, p.name, p.active FROM cc_editor_profile p
              WHERE p.active OR p.id IN (SELECT profile_id FROM cc_show_editor_profile WHERE show_id = ?)
              ORDER BY lower(p.name), p.id',
            [$showId]
        );
        $options = [];
        foreach ($rows as $r) {
            $options[(int) $r['id']] = $r['active'] ? $r['name'] : sprintf(_('%s (inactive)'), $r['name']);
        }

        return $options;
    }

    public static function showProfiles(int $showId): array
    {
        if (!self::tablesReady()) {
            return [];
        }

        return self::query(
            'SELECT p.id, p.name FROM cc_show_editor_profile se
               JOIN cc_editor_profile p ON p.id = se.profile_id
              WHERE se.show_id = ? ORDER BY lower(p.name), p.id',
            [$showId]
        );
    }

    // ------------------------------------------------------------------
    // Per-show archiving defaults (Edit Show → Archiving)
    // ------------------------------------------------------------------

    public static function showSettings(int $showId): array
    {
        $defaults = [
            'participants' => null,
            'cba_series_id' => null,
            'license' => '',
            'category_id' => null,
            'languages' => '',
            'tags' => '',
            'teaser' => '',
            'contains_copyright' => false,
            'cba_account_id' => null,
            'cba_status' => 'publish',
        ];
        if (!self::tablesReady() || $showId <= 0) {
            return $defaults;
        }
        $rows = self::query('SELECT * FROM cc_show_archiving WHERE show_id = ?', [$showId]);
        if (!$rows) {
            return $defaults;
        }
        $r = $rows[0];

        return [
            'cba_account_id' => $r['cba_account_id'] === null ? null : (int) $r['cba_account_id'],
            'cba_status' => (string) $r['cba_status'],
            'participants' => $r['participants'] === null ? null : (int) $r['participants'],
            'cba_series_id' => $r['cba_series_id'] === null ? null : (int) $r['cba_series_id'],
            'license' => (string) $r['license'],
            'category_id' => $r['category_id'] === null ? null : (int) $r['category_id'],
            'languages' => (string) $r['languages'],
            'tags' => (string) $r['tags'],
            'teaser' => (string) $r['teaser'],
            'contains_copyright' => (bool) $r['contains_copyright'],
        ];
    }

    /** "de, EN;fr" → "de,en,fr"; null when a code is not one the CBA takes or there are more than three. */
    public static function normalizeLanguages(string $value): ?string
    {
        $codes = [];
        foreach (preg_split('/[\s,;]+/', strtolower(trim($value)), -1, PREG_SPLIT_NO_EMPTY) as $code) {
            if (!in_array($code, self::CBA_LANGUAGES, true)) {
                return null;
            }
            $codes[$code] = true;
        }

        return count($codes) > 3 ? null : implode(',', array_keys($codes));
    }

    /**
     * Field errors of the Archiving section (form field name => message).
     * Used by ShowFormService::validateShowForms().
     */
    public static function validateShowData(array $data): array
    {
        $errors = [];
        foreach (['add_show_participants' => 999, 'add_show_cba_series_id' => 2147483647, 'add_show_cba_category_id' => 2147483647] as $field => $max) {
            $v = trim((string) ($data[$field] ?? ''));
            if ($v !== '' && (!ctype_digit($v) || (int) $v > $max || ($field !== 'add_show_participants' && (int) $v === 0))) {
                $errors[$field] = $field === 'add_show_participants'
                    ? _('Please enter a whole number between 0 and 999.')
                    : _('Please enter the number shown on cba.media, or leave the field empty.');
            }
        }
        if (self::normalizeLanguages((string) ($data['add_show_cba_languages'] ?? '')) === null) {
            $errors['add_show_cba_languages'] = _('Up to three language codes the CBA knows, such as "de, en".');
        }
        $account = (int) ($data['add_show_cba_account'] ?? 0);
        if ($account > 0 && !self::query('SELECT 1 FROM cc_cba_account WHERE id = ?', [$account])) {
            $errors['add_show_cba_account'] = _('The chosen CBA account does not exist any more.');
        }
        if (!array_key_exists((string) ($data['add_show_cba_status'] ?? 'publish'), self::statusOptions())) {
            $errors['add_show_cba_status'] = _('Unknown visibility.');
        }
        if (!array_key_exists((string) ($data['add_show_cba_license'] ?? ''), self::licenseOptions())) {
            $errors['add_show_cba_license'] = _('Unknown licence.');
        }
        if (mb_strlen((string) ($data['add_show_cba_tags'] ?? '')) > 512) {
            $errors['add_show_cba_tags'] = _('The tags are too long (512 characters at most).');
        }
        if (mb_strlen((string) ($data['add_show_cba_teaser'] ?? '')) > 2048) {
            $errors['add_show_cba_teaser'] = _('The teaser is too long (2048 characters at most).');
        }

        return $errors;
    }

    /** Store the Archiving section of the show form (after validateShowData()). */
    public static function saveShow(int $showId, array $data): void
    {
        if (!self::tablesReady() || $showId <= 0) {
            return;
        }
        $con = Propel::getConnection();
        $con->beginTransaction();

        try {
            self::exec(
                'INSERT INTO cc_show_archiving
                        (show_id, participants, cba_series_id, license, category_id, languages, tags, teaser, contains_copyright,
                         cba_account_id, cba_status, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
                 ON CONFLICT (show_id) DO UPDATE SET
                        participants = EXCLUDED.participants, cba_series_id = EXCLUDED.cba_series_id,
                        license = EXCLUDED.license, category_id = EXCLUDED.category_id,
                        languages = EXCLUDED.languages, tags = EXCLUDED.tags, teaser = EXCLUDED.teaser,
                        contains_copyright = EXCLUDED.contains_copyright, cba_account_id = EXCLUDED.cba_account_id,
                        cba_status = EXCLUDED.cba_status, updated_at = now()',
                [
                    $showId,
                    self::intOrNull($data['add_show_participants'] ?? ''),
                    self::intOrNull($data['add_show_cba_series_id'] ?? ''),
                    trim((string) ($data['add_show_cba_license'] ?? '')) ?: null,
                    self::intOrNull($data['add_show_cba_category_id'] ?? ''),
                    self::normalizeLanguages((string) ($data['add_show_cba_languages'] ?? '')) ?: null,
                    trim((string) ($data['add_show_cba_tags'] ?? '')) ?: null,
                    trim((string) ($data['add_show_cba_teaser'] ?? '')) ?: null,
                    empty($data['add_show_cba_contains_copyright']) ? 'f' : 't',
                    (int) ($data['add_show_cba_account'] ?? 0) ?: null,
                    array_key_exists((string) ($data['add_show_cba_status'] ?? ''), self::statusOptions())
                        ? (string) $data['add_show_cba_status'] : 'publish',
                ]
            );
            self::exec('DELETE FROM cc_show_editor_profile WHERE show_id = ?', [$showId]);
            $ids = array_unique(array_filter(array_map('intval', (array) ($data['add_show_editor_profiles'] ?? []))));
            foreach ($ids as $profileId) {
                self::exec(
                    'INSERT INTO cc_show_editor_profile (show_id, profile_id)
                     SELECT ?, id FROM cc_editor_profile WHERE id = ?',
                    [$showId, $profileId]
                );
            }
            $con->commit();
        } catch (Exception $e) {
            $con->rollBack();

            throw $e;
        }
    }

    // ------------------------------------------------------------------
    // Episodes (calendar context menu → Episode...)
    // ------------------------------------------------------------------

    /**
     * Everything the episode dialog shows: the stored episode row (or
     * defaults), the show's defaults it falls back to, and the instance.
     * Null when the instance does not exist.
     */
    public static function episode(int $instanceId): ?array
    {
        $rows = self::query(
            'SELECT si.id, si.show_id, si.starts, si.ends, si.description, si.file_id, si.rebroadcast,
                    s.name AS show_name
               FROM cc_show_instances si JOIN cc_show s ON s.id = si.show_id
              WHERE si.id = ?',
            [$instanceId]
        );
        if (!$rows) {
            return null;
        }
        $i = $rows[0];
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $starts = new DateTime($i['starts'], new DateTimeZone('UTC'));
        $starts->setTimezone($tz);
        $ep = [];
        if (self::tablesReady()) {
            $ep = self::query('SELECT * FROM cc_episode WHERE instance_id = ?', [$instanceId])[0] ?? [];
        }
        $show = self::showSettings((int) $i['show_id']);

        return [
            'instance_id' => (int) $i['id'],
            'show_id' => (int) $i['show_id'],
            'show_name' => (string) $i['show_name'],
            'starts_local' => $starts->format('Y-m-d H:i'),
            'aired' => strtotime($i['ends'] . ' UTC') <= time(),
            'recording_file_id' => $i['file_id'] === null ? null : (int) $i['file_id'],
            'rebroadcast' => (int) $i['rebroadcast'] > 0,
            'description' => (string) $i['description'],
            'title' => (string) ($ep['title'] ?? ''),
            'default_title' => $i['show_name'] . ' ' . $starts->format('Y-m-d'),
            'teaser' => (string) ($ep['teaser'] ?? ''),
            'default_teaser' => $show['teaser'],
            'image_path' => (string) ($ep['image_path'] ?? ''),
            'image_license' => (string) ($ep['image_license'] ?? ''),
            'image_caption' => (string) ($ep['image_caption'] ?? ''),
            'participants' => isset($ep['participants']) ? (int) $ep['participants'] : null,
            'show_participants' => $show['participants'],
            'show_settings' => $show,
            'profiles' => self::showProfiles((int) $i['show_id']),
            // archiving stage 2
            'starts_utc' => $i['starts'],
            'broadcast_date' => $starts->format('Y-m-d'),
            'production_date' => (string) ($ep['production_date'] ?? ''),
            'no_archive' => !empty($ep['no_archive']),
            'cba_post_id' => isset($ep['cba_post_id']) ? (int) $ep['cba_post_id'] : null,
            'cba_archived_at' => (string) ($ep['cba_archived_at'] ?? ''),
            'show_description' => (string) self::query('SELECT description FROM cc_show WHERE id = ?', [(int) $i['show_id']])[0]['description'],
            'account_label' => $show['cba_account_id']
                ? (string) (self::query('SELECT label FROM cc_cba_account WHERE id = ?', [$show['cba_account_id']])[0]['label'] ?? '')
                : '',
            'job' => self::latestJob($instanceId),
        ];
    }

    /** The newest upload job of an instance (or null), with the file name it sends. */
    public static function latestJob(int $instanceId): ?array
    {
        if (!self::tablesReady()) {
            return null;
        }
        $row = self::query(
            "SELECT j.id, j.status, j.trigger, j.attempts, j.last_error, j.post_id, j.bytes_total, j.bytes_sent, j.file_id,
                    to_char(j.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS created_utc,
                    to_char(j.next_attempt_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS next_attempt_utc,
                    to_char(j.finished_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS finished_utc,
                    f.track_title, f.artist_name
               FROM cc_cba_upload j LEFT JOIN cc_files f ON f.id = j.file_id
              WHERE j.instance_id = ? ORDER BY j.id DESC LIMIT 1",
            [$instanceId]
        );

        return $row ? $row[0] : null;
    }

    /**
     * Store the episode dialog (all fields optional).
     *
     * @return null|string error message
     */
    public static function saveEpisode(int $instanceId, array $data): ?string
    {
        if (!self::tablesReady()) {
            return _('The archiving tables are missing - run the database migrations 0074 and 0075 first.');
        }
        $title = trim((string) ($data['title'] ?? ''));
        $teaser = trim((string) ($data['teaser'] ?? ''));
        $caption = trim((string) ($data['image_caption'] ?? ''));
        $license = trim((string) ($data['image_license'] ?? ''));
        $participants = trim((string) ($data['participants'] ?? ''));
        $description = trim((string) ($data['description'] ?? ''));
        $production = trim((string) ($data['production_date'] ?? ''));
        if (mb_strlen($title) > 255) {
            return _('The title takes 255 characters at most.');
        }
        if (mb_strlen($caption) > 500) {
            return _('The image caption takes 500 characters at most.');
        }
        if ($production !== '') {
            $d = DateTime::createFromFormat('!Y-m-d', $production);
            if (!$d || $d->format('Y-m-d') !== $production) {
                return _('Please enter the production date as YYYY-MM-DD, or leave it empty.');
            }
        }
        if (mb_strlen($teaser) > 2048) {
            return _('The teaser is too long (2048 characters at most).');
        }
        if (mb_strlen($description) > 8192) {
            return _('The description is too long (8192 characters at most).');
        }
        if (!array_key_exists($license, self::licenseOptions())) {
            return _('Unknown licence.');
        }
        if ($participants !== '' && (!ctype_digit($participants) || (int) $participants > 999)) {
            return _('Please enter a whole number between 0 and 999.');
        }
        $con = Propel::getConnection();
        $con->beginTransaction();

        try {
            if (!self::exec('UPDATE cc_show_instances SET description = ? WHERE id = ?', [$description === '' ? null : $description, $instanceId])) {
                $con->rollBack();

                return _('The show instance does not exist any more.');
            }
            self::exec(
                'INSERT INTO cc_episode (instance_id, title, teaser, image_license, image_caption, participants,
                                         production_date, no_archive, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, now())
                 ON CONFLICT (instance_id) DO UPDATE SET
                        title = EXCLUDED.title, teaser = EXCLUDED.teaser, image_license = EXCLUDED.image_license,
                        image_caption = EXCLUDED.image_caption, participants = EXCLUDED.participants,
                        production_date = EXCLUDED.production_date, no_archive = EXCLUDED.no_archive, updated_at = now()',
                [
                    $instanceId,
                    $title === '' ? null : $title,
                    $teaser === '' ? null : $teaser,
                    $license === '' ? null : $license,
                    $caption === '' ? null : $caption,
                    $participants === '' ? null : (int) $participants,
                    $production === '' ? null : $production,
                    empty($data['no_archive']) ? 'f' : 't',
                ]
            );
            $con->commit();
        } catch (Exception $e) {
            $con->rollBack();

            throw $e;
        }

        return null;
    }

    /** Absolute path of the episode image, null when there is none (or the file is gone). */
    public static function episodeImageFile(int $instanceId): ?string
    {
        if (!self::tablesReady()) {
            return null;
        }
        $rel = self::query('SELECT image_path FROM cc_episode WHERE instance_id = ?', [$instanceId])[0]['image_path'] ?? null;
        if (!$rel) {
            return null;
        }
        $abs = Application_Common_Storage::toAbsolute($rel);

        return is_file($abs) ? $abs : null;
    }

    /**
     * Take an uploaded JPG/PNG as the episode image, replacing an earlier one.
     *
     * @return null|string error message
     */
    public static function setEpisodeImage(int $instanceId, string $tmpPath, int $size): ?string
    {
        if (!self::tablesReady()) {
            return _('The archiving tables are missing - run the database migrations 0074 and 0075 first.');
        }
        if (!self::query('SELECT 1 FROM cc_show_instances WHERE id = ?', [$instanceId])) {
            return _('The show instance does not exist any more.');
        }
        if ($size <= 0 || $size > self::EPISODE_IMAGE_MAX_BYTES) {
            return _('The image must not be larger than 10 MB.');
        }
        $mime = (string) finfo_file(finfo_open(), $tmpPath, FILEINFO_MIME_TYPE);
        $ext = self::IMAGE_TYPES[$mime] ?? null;
        if ($ext === null) {
            return _('Please choose a JPG or PNG image.');
        }
        Application_Common_Storage::assertNotMoving();
        $dir = rtrim(Application_Common_Storage::root(), '/\\') . '/imported/episode-images/' . $instanceId;
        if (!is_dir($dir) && !mkdir($dir, 0777, true)) {
            return _('The image folder could not be created.');
        }
        $target = $dir . '/' . date('YmdHis') . '-' . bin2hex(random_bytes(4)) . '.' . $ext;
        if (!move_uploaded_file($tmpPath, $target) && !rename($tmpPath, $target)) {
            return _('The image could not be stored.');
        }
        $old = self::episodeImageFile($instanceId);
        self::exec(
            'INSERT INTO cc_episode (instance_id, image_path, updated_at) VALUES (?, ?, now())
             ON CONFLICT (instance_id) DO UPDATE SET image_path = EXCLUDED.image_path, updated_at = now()',
            [$instanceId, Application_Common_Storage::toRelative($target)]
        );
        if ($old !== null && realpath($old) !== realpath($target)) {
            @unlink($old);
        }

        return null;
    }

    public static function removeEpisodeImage(int $instanceId): void
    {
        $old = self::episodeImageFile($instanceId);
        if (self::tablesReady()) {
            self::exec('UPDATE cc_episode SET image_path = NULL, updated_at = now() WHERE instance_id = ?', [$instanceId]);
        }
        if ($old !== null) {
            @unlink($old);
        }
    }

    /**
     * "Edit Instance" makes a new instance and hides the original
     * (ShowService::editRepeatingShowInstance); the episode data and the
     * archive jobs follow it.
     */
    public static function moveEpisode(int $fromInstanceId, int $toInstanceId): void
    {
        if (!self::tablesReady() || $fromInstanceId === $toInstanceId) {
            return;
        }
        self::exec(
            'UPDATE cc_episode SET instance_id = ? WHERE instance_id = ?
                AND NOT EXISTS (SELECT 1 FROM cc_episode WHERE instance_id = ?)',
            [$toInstanceId, $fromInstanceId, $toInstanceId]
        );
        self::exec('UPDATE cc_cba_upload SET instance_id = ? WHERE instance_id = ?', [$toInstanceId, $fromInstanceId]);
    }

    // ------------------------------------------------------------------
    // CBA accounts (Settings → CBA Accounts, admins only)
    // ------------------------------------------------------------------

    /** All accounts without their password; has_password tells whether one is set. */
    public static function accounts(): array
    {
        if (!self::tablesReady()) {
            return [];
        }

        return self::query(
            "SELECT a.id, a.label, a.username, (a.app_password <> '') AS has_password,
                    (SELECT count(*) FROM cc_show_archiving s WHERE s.cba_account_id = a.id) AS shows
               FROM cc_cba_account a ORDER BY lower(a.label), a.id"
        );
    }

    public static function accountOptions(): array
    {
        $options = [0 => _('- none -')];
        foreach (self::accounts() as $a) {
            $options[(int) $a['id']] = $a['label'] . ' (' . $a['username'] . ')';
        }

        return $options;
    }

    /**
     * Create (id 0) or update an account.  An empty $password keeps the
     * stored one (the field is write-only); a new account needs one.
     *
     * @return array [int id, ?string error]
     */
    public static function saveAccount(int $id, string $label, string $username, string $password): array
    {
        $label = trim($label);
        $username = trim($username);
        $password = trim($password);
        if ($label === '' || $username === '') {
            return [0, _('Please enter a label and the CBA user name.')];
        }
        if (mb_strlen($label) > 255 || mb_strlen($username) > 255 || mb_strlen($password) > 255) {
            return [0, _('Label, user name and password take 255 characters at most.')];
        }
        if ($id > 0) {
            $n = $password === ''
                ? self::exec('UPDATE cc_cba_account SET label = ?, username = ?, updated_at = now() WHERE id = ?', [$label, $username, $id])
                : self::exec('UPDATE cc_cba_account SET label = ?, username = ?, app_password = ?, updated_at = now() WHERE id = ?',
                    [$label, $username, $password, $id]);

            return $n ? [$id, null] : [0, _('The account does not exist any more.')];
        }
        if ($password === '') {
            return [0, _('Please enter the application password of the CBA user.')];
        }
        $row = self::query('INSERT INTO cc_cba_account (label, username, app_password) VALUES (?, ?, ?) RETURNING id',
            [$label, $username, $password]);

        return [(int) $row[0]['id'], null];
    }

    public static function deleteAccount(int $id): bool
    {
        return self::exec('DELETE FROM cc_cba_account WHERE id = ?', [$id]) > 0;
    }

    /**
     * Ask cba.media who the stored credentials belong to (GET
     * wp/v2/users/me, HTTP Basic).  Nothing is uploaded.
     *
     * @return array [bool ok, string message]
     */
    public static function testAccount(int $id): array
    {
        $acc = self::query('SELECT username, app_password FROM cc_cba_account WHERE id = ?', [$id])[0] ?? null;
        if (!$acc) {
            return [false, _('The account does not exist any more.')];
        }
        if ($acc['app_password'] === '') {
            return [false, _('No application password is stored for this account.')];
        }
        $ch = curl_init(self::CBA_BASE . 'wp/v2/users/me?context=edit&_fields=name,slug,roles');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_USERPWD => $acc['username'] . ':' . $acc['app_password'],
            CURLOPT_HTTPAUTH => CURLAUTH_BASIC,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_USERAGENT => 'RASTATIME',
        ]);
        $body = curl_exec($ch);
        $code = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        if ($body === false) {
            return [false, sprintf(_('cba.media could not be reached: %s'), $err)];
        }
        $json = json_decode((string) $body, true);
        if ($code === 401 || $code === 403) {
            return [false, _('cba.media refused the user name or the application password.')];
        }
        if ($code !== 200 || !is_array($json)) {
            return [false, sprintf(_('cba.media answered with HTTP %d.'), $code)];
        }
        $roles = isset($json['roles']) && is_array($json['roles']) ? $json['roles'] : [];
        // the API description writes "stationmanager", cba.media answers "station_manager"
        $plain = array_map(fn ($r) => str_replace(['_', '-'], '', strtolower((string) $r)), $roles);
        $allowed = array_intersect($plain, ['administrator', 'admin', 'author', 'podcaster', 'stationmanager', 'channelmanager']);
        $who = (string) ($json['name'] ?? $json['slug'] ?? $acc['username']);
        if ($roles && !$allowed) {
            return [false, sprintf(_('Signed in as %s, but the role (%s) may not upload.'), $who, implode(', ', $roles))];
        }

        return [true, sprintf(_('Signed in as %s.'), $who) . ($roles ? ' (' . implode(', ', $roles) . ')' : '')];
    }

    public const CBA_BASE = 'https://cba.media/wp-json/';

    /** A station-wide cc_pref value (the worker writes cba_categories_json the same way). */
    private static function pref(string $key): ?string
    {
        $row = self::query('SELECT valstr FROM cc_pref WHERE keystr = ? AND subjid IS NULL ORDER BY id LIMIT 1', [$key]);

        return $row ? $row[0]['valstr'] : null;
    }

    /** Upload bandwidth limit in kbit/s (Settings → CBA Accounts). */
    public static function uploadKbit(): int
    {
        $v = (int) self::pref('cba_upload_kbit');

        return $v > 0 ? $v : 4000;
    }

    public static function setUploadKbit(int $kbit): void
    {
        $v = (string) max(256, min(1000000, $kbit));
        if (!self::exec('UPDATE cc_pref SET valstr = ? WHERE keystr = ? AND subjid IS NULL', [$v, 'cba_upload_kbit'])) {
            self::exec('INSERT INTO cc_pref (keystr, valstr) VALUES (?, ?)', ['cba_upload_kbit', $v]);
        }
    }

    /**
     * CBA topics (categories) as id => "Parent › Child", from the list the
     * worker fetches once a day (cc_pref cba_categories_json); empty when
     * it has not run yet - the form then offers the number field.
     */
    public static function categoryOptions(): array
    {
        $list = json_decode((string) self::pref('cba_categories_json'), true);
        if (!is_array($list) || !$list) {
            return [];
        }
        $names = [];
        foreach ($list as $c) {
            $names[(int) $c['id']] = (string) $c['name'];
        }
        $options = [];
        foreach ($list as $c) {
            $parent = (int) ($c['parent'] ?? 0);
            $options[(int) $c['id']] = ($parent && isset($names[$parent]) ? $names[$parent] . ' › ' : '') . $c['name'];
        }
        asort($options, SORT_NATURAL | SORT_FLAG_CASE);

        return $options;
    }

    // ------------------------------------------------------------------
    // Archive online (episode dialog, stage 2; the upload runs in RASTATIME-WORKER)
    // ------------------------------------------------------------------

    /** Library files the dialog may send instead of the recording (formats the CBA takes). */
    public static function archiveFileSearch(string $q): array
    {
        $q = trim($q);
        if (mb_strlen($q) < 2) {
            return [];
        }
        $like = '%' . str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $q) . '%';

        return self::query(
            "SELECT id, track_title, artist_name, length, lower(substring(filepath from '\\.([^.\\\\/]+)$')) AS ext
               FROM cc_files
              WHERE file_exists AND import_status = 0 AND hidden = FALSE
                AND lower(substring(filepath from '\\.([^.\\\\/]+)$')) IN ('mp3', 'ogg', 'opus')
                AND (track_title ILIKE ? OR artist_name ILIKE ?)
              ORDER BY id DESC LIMIT 30",
            [$like, $like]
        );
    }

    /**
     * Why an instance cannot be archived right now (empty = it can).
     * $fileId 0 = the recording of the instance.  The worker checks again
     * before it sends anything.
     */
    public static function precheck(int $instanceId, int $fileId = 0): array
    {
        $ep = self::episode($instanceId);
        if ($ep === null) {
            return [_('The show instance does not exist any more.')];
        }
        $show = $ep['show_settings'];
        $missing = [];
        if (!$ep['aired']) {
            $missing[] = _('The episode has not aired yet.');
        }
        if ($ep['cba_post_id']) {
            $missing[] = _('The episode is archived already.');
        }
        if (!$show['cba_account_id']) {
            $missing[] = _('The show has no CBA account (Edit Show → Archiving).');
        } elseif (!(self::query("SELECT app_password <> '' AS ok FROM cc_cba_account WHERE id = ?", [$show['cba_account_id']])[0]['ok'] ?? false)) {
            $missing[] = _('The CBA account of the show has no application password (Settings → CBA Accounts).');
        }
        if (!$show['category_id']) {
            $missing[] = _('The show has no CBA topic (Edit Show → Archiving).');
        }
        if ($show['languages'] === '') {
            $missing[] = _('The show has no language (Edit Show → Archiving).');
        }
        // without a licence the CBA would publish under CC BY (its default)
        if ($show['license'] === '') {
            $missing[] = _('The show has no licence (Edit Show → Archiving).');
        }
        if (trim($ep['description']) === '' && trim($ep['show_description']) === '') {
            $missing[] = _('Neither the episode nor the show has a description - the CBA needs a text.');
        }
        $production = $ep['production_date'] !== '' ? $ep['production_date'] : $ep['broadcast_date'];
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        if ($production > (new DateTime('now', $tz))->format('Y-m-d')) {
            $missing[] = _('The production date lies in the future.');
        }
        $fid = $fileId > 0 ? $fileId : (int) $ep['recording_file_id'];
        if ($fid <= 0) {
            $missing[] = _('There is no recording of this episode in the library - choose a library file.');
        } else {
            $f = self::query('SELECT filepath, file_exists, import_status FROM cc_files WHERE id = ?', [$fid])[0] ?? null;
            $ext = $f ? strtolower(pathinfo((string) $f['filepath'], PATHINFO_EXTENSION)) : '';
            if (!$f || !$f['file_exists'] || (int) $f['import_status'] !== 0) {
                $missing[] = _('The audio file is missing or not imported yet.');
            } elseif (!in_array($ext, self::AUDIO_EXTENSIONS, true)) {
                $missing[] = sprintf(_('The CBA takes MP3, OGG and Opus, not %s.'), strtoupper($ext));
            }
        }

        return $missing;
    }

    /**
     * Queue an upload (manual: admins and program managers; the controller
     * checks the role).  At most one open job per instance (unique index).
     *
     * @return array [int job id, string[] reasons when refused]
     */
    public static function enqueueUpload(int $instanceId, int $fileId, int $userId, string $trigger = 'manual'): array
    {
        if (!self::tablesReady()) {
            return [0, [_('The archiving tables are missing - run the database migrations 0074 and 0075 first.')]];
        }
        $missing = self::precheck($instanceId, $fileId);
        if ($missing) {
            return [0, $missing];
        }
        if (self::query("SELECT 1 FROM cc_cba_upload WHERE instance_id = ? AND status IN ('queued', 'running')", [$instanceId])) {
            return [0, [_('An upload of this episode is already waiting or running.')]];
        }
        $fid = $fileId > 0 ? $fileId : (int) self::episode($instanceId)['recording_file_id'];
        $row = self::query(
            'INSERT INTO cc_cba_upload (instance_id, file_id, trigger, requested_by) VALUES (?, ?, ?, ?) RETURNING id',
            [$instanceId, $fid, $trigger === 'auto' ? 'auto' : 'manual', $userId > 0 ? $userId : null]
        );

        return [(int) $row[0]['id'], []];
    }

    /**
     * Link the episode to a post that exists on cba.media already (number
     * or address), or remove the link with an empty value.
     *
     * @return null|string error
     */
    public static function linkPost(int $instanceId, string $value): ?string
    {
        if (!self::tablesReady()) {
            return _('The archiving tables are missing - run the database migrations 0074 and 0075 first.');
        }
        $value = trim($value);
        $postId = null;
        if ($value !== '') {
            if (preg_match('/^\d+$/', $value)) {
                $postId = (int) $value;
            } elseif (preg_match('/[?&]p=(\d+)/', $value, $m)) {
                $postId = (int) $m[1];
            } else {
                return _('Please enter the number of the post (or an address with ?p=<number>).');
            }
        }
        if (!self::query('SELECT 1 FROM cc_show_instances WHERE id = ?', [$instanceId])) {
            return _('The show instance does not exist any more.');
        }
        self::exec(
            'INSERT INTO cc_episode (instance_id, cba_post_id, cba_archived_at, updated_at) VALUES (?, ?, ?, now())
             ON CONFLICT (instance_id) DO UPDATE SET cba_post_id = EXCLUDED.cba_post_id,
                    cba_archived_at = EXCLUDED.cba_archived_at, updated_at = now()',
            [$instanceId, $postId, $postId ? gmdate('Y-m-d H:i:s') . '+00' : null]
        );

        return null;
    }

    // ------------------------------------------------------------------
    // Participants overview (Analytics → Participants)
    // ------------------------------------------------------------------

    /** Years from the first instance to the current one, newest first. */
    public static function reportYears(): array
    {
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $now = (int) (new DateTime('now', $tz))->format('Y');
        $first = self::query('SELECT min(starts) AS first FROM cc_show_instances')[0]['first'] ?? null;
        $from = $first ? (int) (new DateTime($first, new DateTimeZone('UTC')))->setTimezone($tz)->format('Y') : $now;

        return range($now, min($from, $now));
    }

    /**
     * Per show: the instances that aired in $year (station time, ended by
     * now, not deleted, no rebroadcast), the show's participants value, how
     * many episodes override it and the sum over the episodes ("person
     * episodes"); totals below.
     */
    public static function participantsReport(int $year): array
    {
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $utc = new DateTimeZone('UTC');
        $from = (new DateTime(sprintf('%04d-01-01 00:00:00', $year), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');
        $to = (new DateTime(sprintf('%04d-01-01 00:00:00', $year + 1), $tz))->setTimezone($utc)->format('Y-m-d H:i:s');
        $ready = self::tablesReady();
        $epJoin = $ready
            ? 'LEFT JOIN cc_episode e ON e.instance_id = si.id LEFT JOIN cc_show_archiving p ON p.show_id = si.show_id'
            : 'LEFT JOIN (SELECT NULL::int AS instance_id, NULL::smallint AS participants) e ON FALSE
               LEFT JOIN (SELECT NULL::int AS show_id, NULL::smallint AS participants) p ON FALSE';
        $team = $ready
            ? "(SELECT string_agg(ep.name, ', ' ORDER BY lower(ep.name)) FROM cc_show_editor_profile se
                 JOIN cc_editor_profile ep ON ep.id = se.profile_id WHERE se.show_id = s.id)"
            : "''";
        $rows = self::query(
            "WITH inst AS (
                SELECT si.id, si.show_id, p.participants AS show_value, e.participants AS own_value,
                       COALESCE(e.participants, p.participants) AS eff
                  FROM cc_show_instances si {$epJoin}
                 WHERE si.modified_instance = FALSE
                   AND COALESCE(si.rebroadcast, 0) = 0
                   AND si.starts >= ? AND si.starts < ?
                   AND si.ends <= (now() AT TIME ZONE 'UTC')
             )
             SELECT s.id, s.name, count(i.id) AS episodes, max(i.show_value) AS participants,
                    count(i.own_value) AS overrides, sum(i.eff) AS person_episodes,
                    count(i.eff) AS episodes_with_value, (s.repeat_of_show_id IS NOT NULL) AS is_repeat,
                    {$team} AS team
               FROM inst i JOIN cc_show s ON s.id = i.show_id
              GROUP BY s.id, s.name, s.repeat_of_show_id
              ORDER BY lower(s.name), s.id",
            [$from, $to]
        );
        $totals = ['shows' => 0, 'episodes' => 0, 'participants' => 0, 'person_episodes' => 0, 'missing' => 0, 'profiles' => 0];
        $showIds = [];
        foreach ($rows as &$r) {
            $r['id'] = (int) $r['id'];
            $r['episodes'] = (int) $r['episodes'];
            $r['participants'] = $r['participants'] === null ? null : (int) $r['participants'];
            $r['overrides'] = (int) $r['overrides'];
            $r['person_episodes'] = $r['person_episodes'] === null ? null : (int) $r['person_episodes'];
            $r['episodes_with_value'] = (int) $r['episodes_with_value'];
            $r['is_repeat'] = (bool) $r['is_repeat'];
            $r['team'] = (string) $r['team'];
            ++$totals['shows'];
            $totals['episodes'] += $r['episodes'];
            $totals['participants'] += (int) $r['participants'];
            $totals['person_episodes'] += (int) $r['person_episodes'];
            $totals['missing'] += $r['participants'] === null ? 1 : 0;
            $showIds[] = $r['id'];
        }
        unset($r);
        if ($ready && $showIds) {
            $in = implode(',', array_fill(0, count($showIds), '?'));
            $totals['profiles'] = (int) self::query(
                "SELECT count(DISTINCT profile_id) AS n FROM cc_show_editor_profile WHERE show_id IN ({$in})",
                $showIds
            )[0]['n'];
        }

        return ['year' => $year, 'rows' => $rows, 'totals' => $totals];
    }
}
