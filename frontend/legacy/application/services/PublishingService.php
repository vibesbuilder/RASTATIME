<?php

/**
 * RASTATIME 2026-11-03 - publishing stage 1 (CBA publishing, migration
 * 0074): editorial team profiles, per-show publishing defaults, per-episode
 * data (episode = show instance) with an optional image, and the yearly
 * participants overview (Analytics → Participants).
 *
 * Propel classes are not generated for the four tables; everything here is
 * raw SQL like Application_Service_RepeatFillService, and every reader
 * returns empty defaults while the tables are missing (tablesReady()).
 */
class Application_Service_PublishingService
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
                    AND table_name IN ('cc_editor_profile', 'cc_show_editor_profile', 'cc_show_publishing', 'cc_episode')"
            )->fetchColumn();
            self::$ready = ((int) $n === 4);
        }

        return self::$ready;
    }

    /** CBA licence keys (zipupload meta "license" / "image_license") => label. */
    public static function licenseOptions(): array
    {
        return [
            '' => _('(not set)'),
            'copyright' => _('All rights reserved'),
            'cc by-nc-nd' => 'CC BY-NC-ND',
            'cc by-nd' => 'CC BY-ND',
            'cc by-nc' => 'CC BY-NC',
            'cc by-sa' => 'CC BY-SA',
            'cc by' => 'CC BY',
            'cc zero' => 'CC0',
            'pd' => _('Public domain'),
        ];
    }

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
    // Per-show publishing defaults (Edit Show → Publishing)
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
        ];
        if (!self::tablesReady() || $showId <= 0) {
            return $defaults;
        }
        $rows = self::query('SELECT * FROM cc_show_publishing WHERE show_id = ?', [$showId]);
        if (!$rows) {
            return $defaults;
        }
        $r = $rows[0];

        return [
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

    /** "de, EN;fr" → "de,en,fr"; null when a code is not 2-3 letters or there are more than three. */
    public static function normalizeLanguages(string $value): ?string
    {
        $codes = [];
        foreach (preg_split('/[\s,;]+/', strtolower(trim($value)), -1, PREG_SPLIT_NO_EMPTY) as $code) {
            if (!preg_match('/^[a-z]{2,3}$/', $code)) {
                return null;
            }
            $codes[$code] = true;
        }

        return count($codes) > 3 ? null : implode(',', array_keys($codes));
    }

    /**
     * Field errors of the Publishing section (form field name => message).
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
            $errors['add_show_cba_languages'] = _('Up to three language codes such as "de, en".');
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

    /** Store the Publishing section of the show form (after validateShowData()). */
    public static function saveShow(int $showId, array $data): void
    {
        if (!self::tablesReady() || $showId <= 0) {
            return;
        }
        $con = Propel::getConnection();
        $con->beginTransaction();

        try {
            self::exec(
                'INSERT INTO cc_show_publishing
                        (show_id, participants, cba_series_id, license, category_id, languages, tags, teaser, contains_copyright, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, now())
                 ON CONFLICT (show_id) DO UPDATE SET
                        participants = EXCLUDED.participants, cba_series_id = EXCLUDED.cba_series_id,
                        license = EXCLUDED.license, category_id = EXCLUDED.category_id,
                        languages = EXCLUDED.languages, tags = EXCLUDED.tags, teaser = EXCLUDED.teaser,
                        contains_copyright = EXCLUDED.contains_copyright, updated_at = now()',
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
        ];
    }

    /**
     * Store the episode dialog (all fields optional).
     *
     * @return null|string error message
     */
    public static function saveEpisode(int $instanceId, array $data): ?string
    {
        if (!self::tablesReady()) {
            return _('The publishing tables are missing - run the database migration 0074 first.');
        }
        $title = trim((string) ($data['title'] ?? ''));
        $teaser = trim((string) ($data['teaser'] ?? ''));
        $caption = trim((string) ($data['image_caption'] ?? ''));
        $license = trim((string) ($data['image_license'] ?? ''));
        $participants = trim((string) ($data['participants'] ?? ''));
        $description = trim((string) ($data['description'] ?? ''));
        if (mb_strlen($title) > 255 || mb_strlen($caption) > 255) {
            return _('Title and image caption take 255 characters at most.');
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
                'INSERT INTO cc_episode (instance_id, title, teaser, image_license, image_caption, participants, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, now())
                 ON CONFLICT (instance_id) DO UPDATE SET
                        title = EXCLUDED.title, teaser = EXCLUDED.teaser, image_license = EXCLUDED.image_license,
                        image_caption = EXCLUDED.image_caption, participants = EXCLUDED.participants, updated_at = now()',
                [
                    $instanceId,
                    $title === '' ? null : $title,
                    $teaser === '' ? null : $teaser,
                    $license === '' ? null : $license,
                    $caption === '' ? null : $caption,
                    $participants === '' ? null : (int) $participants,
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
            return _('The publishing tables are missing - run the database migration 0074 first.');
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
            ? 'LEFT JOIN cc_episode e ON e.instance_id = si.id LEFT JOIN cc_show_publishing p ON p.show_id = si.show_id'
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
