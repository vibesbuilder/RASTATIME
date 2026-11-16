<?php

/**
 * RASTATIME 2026-11-16 - show types (ARCHITECTURE 23.120).
 *
 * A show has one type out of a list kept under Settings -> Track/Show Types
 * (cc_show_types, migration 0088).  Analytics -> Programme Minutes counts a
 * show as a repeat when its type is marked "counts as repeat".  Raw SQL like
 * the other late columns: the readers check the table first and read
 * cc_show.show_type_id through to_jsonb(), so nothing breaks before the
 * migration ran (no types, no field in the show form).
 */
class Application_Model_Showtype
{
    private static $ready;

    /** True once migration 0088 created cc_show_types (and cc_show.show_type_id). */
    public static function ready(): bool
    {
        if (self::$ready === null) {
            try {
                $row = Application_Common_Database::prepareAndExecute(
                    "SELECT 1 AS ok FROM information_schema.tables WHERE table_name = 'cc_show_types'",
                    [],
                    Application_Common_Database::SINGLE
                );
                self::$ready = !empty($row);
            } catch (Exception $e) {
                self::$ready = false;
            }
        }

        return self::$ready;
    }

    /**
     * All types in their order, each with the number of shows using it.
     *
     * @return array[] id, code, type_name, counts_as_repeat (bool), sort_order, shows
     */
    public static function all(): array
    {
        if (!self::ready()) {
            return [];
        }
        $rows = Application_Common_Database::prepareAndExecute(
            "SELECT t.id, t.code, t.type_name, t.counts_as_repeat, t.sort_order,
                    (SELECT count(*) FROM cc_show s WHERE (to_jsonb(s) ->> 'show_type_id')::int = t.id) AS shows
             FROM cc_show_types t
             ORDER BY t.sort_order, lower(t.type_name), t.id"
        );

        return array_map(static function ($r) {
            return [
                'id' => (int) $r['id'],
                'code' => (string) $r['code'],
                'type_name' => (string) $r['type_name'],
                'counts_as_repeat' => in_array($r['counts_as_repeat'], [true, 't', '1', 1, 'true'], true),
                'sort_order' => (int) $r['sort_order'],
                'shows' => (int) $r['shows'],
            ];
        }, $rows ?: []);
    }

    /** [id => label] for the show form's dropdown, in the list order. */
    public static function options(): array
    {
        $out = [];
        foreach (self::all() as $t) {
            $out[$t['id']] = $t['type_name'];
        }

        return $out;
    }

    /** One type or null. */
    public static function get($id): ?array
    {
        foreach (self::all() as $t) {
            if ($t['id'] === (int) $id) {
                return $t;
            }
        }

        return null;
    }

    /**
     * Create (id empty) or update a type.  Returns a list of error messages
     * (empty = saved).
     */
    public static function save($id, $code, $name, $countsAsRepeat, $sortOrder): array
    {
        if (!self::ready()) {
            return [_('The show types are not available yet (database migration 0088 pending).')];
        }
        $code = strtolower(trim((string) $code));
        $name = trim((string) $name);
        $errors = [];
        if ($code === '' || !preg_match('/^[a-z0-9_-]{1,16}$/', $code)) {
            $errors[] = _('Code: 1 to 16 lower-case letters, digits, "-" or "_".');
        }
        if ($name === '' || mb_strlen($name) > 64) {
            $errors[] = _('Label: 1 to 64 characters.');
        }
        $order = trim((string) $sortOrder) === '' ? 0 : $sortOrder;
        if (!preg_match('/^-?\d{1,6}$/', (string) $order)) {
            $errors[] = _('Order: a whole number.');
        }
        $id = (string) $id === '' ? null : (int) $id;
        $dup = Application_Common_Database::prepareAndExecute(
            'SELECT id FROM cc_show_types WHERE lower(code) = lower(:code) AND (:id::int IS NULL OR id <> :id2::int)',
            [':code' => $code, ':id' => $id, ':id2' => $id],
            Application_Common_Database::SINGLE
        );
        if (!empty($dup)) {
            $errors[] = _('Code: another show type uses it already.');
        }
        if ($errors) {
            return $errors;
        }
        $params = [':code' => $code, ':name' => $name, ':rep' => $countsAsRepeat ? 'true' : 'false', ':ord' => (int) $order];
        if ($id === null) {
            Application_Common_Database::prepareAndExecute(
                'INSERT INTO cc_show_types (code, type_name, counts_as_repeat, sort_order) VALUES (:code, :name, :rep::boolean, :ord)',
                $params,
                Application_Common_Database::EXECUTE
            );
        } else {
            $params[':id'] = $id;
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_show_types SET code = :code, type_name = :name, counts_as_repeat = :rep::boolean, sort_order = :ord WHERE id = :id',
                $params,
                Application_Common_Database::EXECUTE
            );
        }

        return [];
    }

    /** Delete a type; its shows keep no type (ON DELETE SET NULL). */
    public static function delete($id): void
    {
        if (!self::ready()) {
            return;
        }
        Application_Common_Database::prepareAndExecute(
            'DELETE FROM cc_show_types WHERE id = :id',
            [':id' => (int) $id],
            Application_Common_Database::EXECUTE
        );
    }

    /** The type id of a show, or null. */
    public static function forShow($showId): ?int
    {
        if (!self::ready() || !$showId) {
            return null;
        }
        $row = Application_Common_Database::prepareAndExecute(
            "SELECT (to_jsonb(s) ->> 'show_type_id') AS v FROM cc_show s WHERE s.id = :id",
            [':id' => (int) $showId],
            Application_Common_Database::SINGLE
        );
        $v = $row['v'] ?? null;

        return ($v === null || $v === '') ? null : (int) $v;
    }

    /** Set the type of a show (empty / unknown = none). */
    public static function setForShow($showId, $typeId): void
    {
        if (!self::ready() || !$showId) {
            return;
        }
        $typeId = (string) $typeId === '' ? null : (int) $typeId;
        if ($typeId !== null && self::get($typeId) === null) {
            $typeId = null;
        }
        Application_Common_Database::prepareAndExecute(
            'UPDATE cc_show SET show_type_id = :t WHERE id = :id',
            [':t' => $typeId, ':id' => (int) $showId],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * RASTATIME 2026-11-16 - SQL boolean: is the show $alias (a cc_show row
     * alias) a repeat by its show type ("counts as repeat")?  Used by People
     * Involved and the CBA archiving (operator: repeats by the type, not by
     * "Repeat of another show").  Before migration 0088 there are no types:
     * $fallbackRepeatOf = true keeps the old rule then (so an update never
     * archives repeats by mistake), false means "no repeats".
     */
    public static function repeatSql(string $alias, bool $fallbackRepeatOf = true): string
    {
        if (!preg_match('/^[a-z_][a-z0-9_]*$/i', $alias)) {
            throw new InvalidArgumentException('bad table alias');
        }
        if (self::ready()) {
            return "COALESCE((SELECT rt_st.counts_as_repeat FROM cc_show_types rt_st WHERE rt_st.id = {$alias}.show_type_id), FALSE)";
        }

        return $fallbackRepeatOf ? "({$alias}.repeat_of_show_id IS NOT NULL)" : 'FALSE';
    }

    /** The id of the type whose label or code is $value (case-insensitive), or null. */
    public static function idByLabel($value): ?int
    {
        $value = mb_strtolower(trim((string) $value));
        if ($value === '') {
            return null;
        }
        foreach (self::all() as $t) {
            if (mb_strtolower($t['type_name']) === $value || mb_strtolower($t['code']) === $value) {
                return $t['id'];
            }
        }

        return null;
    }
}
