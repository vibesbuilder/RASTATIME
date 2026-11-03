<?php

/**
 * RASTATIME 2026-05-19 — Show-Template service (Section 23.16).
 *
 * Manages the cc_show_template rows (created by migration 0053).
 * Two consumer surfaces:
 *
 *   - The Calendar's "New Show" dialog:
 *       * GET getAllForDropdown()          — populate the dropdown
 *       * GET getTemplateById($id)         — fetch one template's JSON
 *       * POST saveFromShowData($name, $data)
 *           Save (or overwrite) a template from an in-flight new-show
 *           form payload.  Called from the "Save as Template" button.
 *
 *   - The Settings → "Show Templates" page:
 *       * GET getAllForListing()
 *       * POST renameTemplate($id, $newName)
 *       * DELETE deleteTemplate($id)
 *
 * Data shape:  template_data is stored as JSONB and is roughly a
 * subset of the show-form payload (see {@see FIELDS_TO_CAPTURE}).
 * Explicitly excluded: live_stream_password (security), per-instance
 * fields, and the schedule start_date/start_time (template is
 * time-neutral).  Hosts are stored as login strings, not as cc_subjs
 * IDs, so a template that references a deleted user can degrade
 * gracefully (skipped at apply-time with a Logging::info).
 *
 * Pure raw-SQL — the legacy Propel models are not regenerated for
 * the new table, and a small key/value store does not need an ORM.
 */
class Application_Service_ShowTemplateService
{
    /**
     * Whitelist of POST keys that survive into the template_data JSON.
     *
     * Anything else in the form payload (start_date, start_time,
     * timezone, instance_description, csrf, custom_password, etc.)
     * is dropped.  Operator-confirmed list from 2026-05-19; if a
     * future schema adds a field the operator wants in templates,
     * add it here and bump the migration if a schema column is
     * needed too.
     */
    public const FIELDS_TO_CAPTURE = [
        // "What" form
        'add_show_name',
        'add_show_url',
        'add_show_genre',
        'add_show_description',
        'add_show_own_production',    // RASTATIME 2026-11-03 - yearly report
        // "When" form (duration + repeat shape only — no start_date/time)
        'add_show_duration',
        'add_show_repeats',
        'add_show_linked',
        'add_show_repeat_type',
        'add_show_monthly_repeat_type',
        'add_show_day_check',         // array of weekdays for repeating
        'add_show_month_check',       // RASTATIME 2026-10-15 - months of a monthly repeat
        'add_show_end_date',
        'add_show_no_end',
        // "Record"
        'add_show_record',
        // "Autoloading Playlist"
        'add_show_has_autoplaylist',
        'add_show_autoplaylist_id',
        'add_show_autoplaylist_repeat',
        'add_show_intro_playlist_id',
        'add_show_outro_playlist_id',
        'add_show_repeat_of',         // RASTATIME 2026-10-18 - "Repeat of show"
        // "Live Stream Input"
        'cb_airtime_auth',
        'cb_custom_auth',
        'custom_username',
        // 'custom_password' deliberately omitted — security
        // "Style"
        'add_show_background_color',
        'add_show_color',
        'add_show_logo_path',         // see below — populated by saveFromShow
        // "Who" — host usernames, not IDs (see class doc)
        'add_show_hosts_logins',      // populated by saveFromShow
    ];

    /**
     * Return all templates as a list of [id, name] for dropdowns.
     * Sorted alphabetically by name.
     *
     * @return array
     */
    public static function getAllForDropdown()
    {
        $sql = 'SELECT id, name FROM cc_show_template ORDER BY name ASC';
        try {
            $rows = Application_Common_Database::prepareAndExecute($sql, [], 'all');
            return is_array($rows) ? $rows : [];
        } catch (Throwable $exc) {
            Logging::warn('ShowTemplateService::getAllForDropdown failed: ' . $exc->getMessage());
            return [];
        }
    }

    /**
     * Return all templates with full metadata for the Settings listing.
     *
     * @return array of [id, name, created_at, updated_at]
     */
    public static function getAllForListing()
    {
        $sql = 'SELECT id, name, created_at, updated_at
                FROM cc_show_template
                ORDER BY name ASC';
        try {
            $rows = Application_Common_Database::prepareAndExecute($sql, [], 'all');
            return is_array($rows) ? $rows : [];
        } catch (Throwable $exc) {
            Logging::warn('ShowTemplateService::getAllForListing failed: ' . $exc->getMessage());
            return [];
        }
    }

    /**
     * Fetch a single template, returning its template_data as a
     * decoded associative array.  Returns null if not found.
     *
     * @param int $id
     * @return array|null
     */
    public static function getTemplateById($id)
    {
        $sql = 'SELECT id, name, template_data
                FROM cc_show_template
                WHERE id = :id';
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                $sql, [':id' => (int) $id], 'all'
            );
        } catch (Throwable $exc) {
            Logging::warn('ShowTemplateService::getTemplateById failed: ' . $exc->getMessage());
            return null;
        }
        if (empty($rows)) {
            return null;
        }
        $row = $rows[0];
        $row['template_data'] = json_decode($row['template_data'], true);
        if (!is_array($row['template_data'])) {
            $row['template_data'] = [];
        }
        return $row;
    }

    /**
     * Look up a template by name.  Used by the Save-as-Template flow
     * to decide between INSERT and UPDATE.
     *
     * @param string $name
     * @return array|null  [id, name] or null
     */
    public static function getTemplateByName($name)
    {
        $sql = 'SELECT id, name FROM cc_show_template WHERE name = :name';
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                $sql, [':name' => (string) $name], 'all'
            );
        } catch (Throwable $exc) {
            Logging::warn('ShowTemplateService::getTemplateByName failed: ' . $exc->getMessage());
            return null;
        }
        return empty($rows) ? null : $rows[0];
    }

    /**
     * Save a template from an in-flight new-show form payload.  The
     * template name defaults to the show's "add_show_name".  If a
     * template with that name already exists, the caller is expected
     * to have asked the operator whether to overwrite; this method
     * just does what {@code $overwrite} says.
     *
     * @param array $showData    The form data as merged by the
     *                           Schedule controller (already includes
     *                           add_show_hosts (array of subjs_ids) and
     *                           add_show_day_check).
     * @param bool  $overwrite   When true and a template with the same
     *                           name exists, UPDATE it; when false and
     *                           it exists, throw an Exception so the
     *                           caller can prompt the operator.
     * @return int  the cc_show_template.id (insert or update)
     * @throws Exception
     */
    public static function saveFromShowData(array $showData, $overwrite = false)
    {
        $name = trim((string) ($showData['add_show_name'] ?? ''));
        if ($name === '') {
            throw new Exception(_('Cannot save template without a show name.'));
        }

        // Build the JSON snapshot.  Pick only the whitelisted keys,
        // plus our two synthesised fields (hosts_logins, logo_path).
        $template = [];
        foreach (self::FIELDS_TO_CAPTURE as $key) {
            if (array_key_exists($key, $showData)) {
                $template[$key] = $showData[$key];
            }
        }

        // Hosts: convert the array of cc_subjs.id values that the
        // form posts into the array of login strings (so a template
        // survives the deletion + recreation of a user, and so the
        // operator sees meaningful names in the Settings UI).
        $template['add_show_hosts_logins'] = self::resolveHostLogins(
            $showData['add_show_hosts'] ?? []
        );

        // Show logo: store the path reference, not a copy.  The form
        // payload's add_show_logo_name is the relative file path
        // chosen by the file-upload widget; we keep it as-is.
        if (!empty($showData['add_show_logo_name'])) {
            $template['add_show_logo_path'] = (string) $showData['add_show_logo_name'];
        }

        $jsonStr = json_encode($template, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

        $existing = self::getTemplateByName($name);
        try {
            if ($existing === null) {
                $insert = 'INSERT INTO cc_show_template (name, template_data)
                           VALUES (:name, :data::jsonb)
                           RETURNING id';
                $rows = Application_Common_Database::prepareAndExecute(
                    $insert,
                    [':name' => $name, ':data' => $jsonStr],
                    'all'
                );
                return (int) $rows[0]['id'];
            }
            if (!$overwrite) {
                throw new Exception(sprintf(
                    _('A template named "%s" already exists.'), $name
                ));
            }
            $update = 'UPDATE cc_show_template
                       SET template_data = :data::jsonb,
                           updated_at = NOW()
                       WHERE id = :id';
            Application_Common_Database::prepareAndExecute(
                $update,
                [':data' => $jsonStr, ':id' => (int) $existing['id']],
                'execute'
            );
            return (int) $existing['id'];
        } catch (Exception $exc) {
            // Re-throw "already exists" verbatim so the caller can
            // distinguish it from a generic DB error and prompt.
            throw $exc;
        }
    }

    /**
     * Rename a template (used by the Settings page).
     *
     * @param int    $id
     * @param string $newName
     * @throws Exception when newName is empty or conflicts
     */
    public static function renameTemplate($id, $newName)
    {
        $newName = trim((string) $newName);
        if ($newName === '') {
            throw new Exception(_('Template name cannot be empty.'));
        }
        // Pre-flight conflict check so we can return a friendlier
        // message than the raw unique-violation SQLSTATE.
        $clash = self::getTemplateByName($newName);
        if ($clash !== null && (int) $clash['id'] !== (int) $id) {
            throw new Exception(sprintf(
                _('Another template is already named "%s".'), $newName
            ));
        }
        $sql = 'UPDATE cc_show_template
                SET name = :name, updated_at = NOW()
                WHERE id = :id';
        Application_Common_Database::prepareAndExecute(
            $sql, [':name' => $newName, ':id' => (int) $id], 'execute'
        );
    }

    /**
     * Delete a template.  Templates do not have FK references from
     * any show row (one-way stamp model), so this is a simple DELETE.
     *
     * @param int $id
     */
    public static function deleteTemplate($id)
    {
        $sql = 'DELETE FROM cc_show_template WHERE id = :id';
        Application_Common_Database::prepareAndExecute(
            $sql, [':id' => (int) $id], 'execute'
        );
    }

    /**
     * Translate an array of cc_subjs.id values into an array of login
     * strings, dropping any IDs that no longer exist.  Used at save
     * time so templates store stable usernames instead of brittle
     * surrogate IDs.
     *
     * @param array $subjsIds
     * @return string[]
     */
    private static function resolveHostLogins(array $subjsIds)
    {
        $logins = [];
        foreach ($subjsIds as $sid) {
            $sid = (int) $sid;
            if ($sid <= 0) {
                continue;
            }
            try {
                $u = CcSubjsQuery::create()->findPk($sid);
                if ($u !== null) {
                    $logins[] = $u->getDbLogin();
                }
            } catch (Throwable $exc) {
                // Tolerate any single-row failure; the rest of the
                // hosts still get saved.
                Logging::info('ShowTemplateService::resolveHostLogins: skipping subjs_id='
                    . $sid . ': ' . $exc->getMessage());
            }
        }
        return $logins;
    }

    /**
     * Resolve a list of login strings back to cc_subjs.id values for
     * apply-time use.  Unknown logins are silently skipped (logged at
     * info level — see Section 23.16 design note on graceful
     * degradation when a referenced user has been removed).
     *
     * @param array $logins
     * @return int[]
     */
    public static function resolveHostIds(array $logins)
    {
        $ids = [];
        foreach ($logins as $login) {
            $login = (string) $login;
            if ($login === '') {
                continue;
            }
            try {
                $u = CcSubjsQuery::create()->findOneByDbLogin($login);
                if ($u !== null) {
                    $ids[] = (int) $u->getDbId();
                } else {
                    Logging::info('ShowTemplateService::resolveHostIds: '
                        . 'no cc_subjs row for login=' . $login
                        . ' — skipping host');
                }
            } catch (Throwable $exc) {
                Logging::info('ShowTemplateService::resolveHostIds: '
                    . 'lookup failed for login=' . $login . ': '
                    . $exc->getMessage());
            }
        }
        return $ids;
    }
}
