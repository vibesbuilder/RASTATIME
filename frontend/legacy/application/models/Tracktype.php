<?php

class Application_Model_Tracktype
{
    private $_tracktypeInstance;

    public function __construct($tracktypeId)
    {
        if (empty($tracktypeId)) {
            $this->_tracktypeInstance = $this->createTracktype();
        } else {
            $this->_tracktypeInstance = CcTracktypesQuery::create()->findPK($tracktypeId);

            if (is_null($this->_tracktypeInstance)) {
                throw new Exception();
            }
        }
    }

    public function getId()
    {
        return $this->_tracktypeInstance->getDbId();
    }

    public function setCode($code)
    {
        $tracktype = $this->_tracktypeInstance;
        $tracktype->setDbCode($code);
    }

    public function setTypeName($typeName)
    {
        $tracktype = $this->_tracktypeInstance;
        $tracktype->setDbTypeName($typeName);
    }

    public function setDescription($description)
    {
        $tracktype = $this->_tracktypeInstance;
        $tracktype->setDbDescription($description);
    }

    public function setVisibility($visibility)
    {
        $tracktype = $this->_tracktypeInstance;
        $tracktype->setDbVisibility($visibility);
    }

    public function setAnalyzeCuePoints($value)
    {
        $tracktype = $this->_tracktypeInstance;
        $tracktype->setDbAnalyzeCuePoints($value);
    }

    public function getCode()
    {
        $tracktype = $this->_tracktypeInstance;

        return $tracktype->getDbCode();
    }

    public function getTypeName()
    {
        $tracktype = $this->_tracktypeInstance;

        return $tracktype->getDbTypeName();
    }

    public function getDescription()
    {
        $tracktype = $this->_tracktypeInstance;

        return $tracktype->getDbDescription();
    }

    public function getVisibility()
    {
        $tracktype = $this->_tracktypeInstance;

        return $tracktype->getDbVisibility();
    }

    public function getAnalyzeCuePoints()
    {
        $tracktype = $this->_tracktypeInstance;

        return $tracktype->getDbAnalyzeCuePoints();
    }

    /**
     * RASTATIME 2026-09-29 - crossfade per track type (migration 0062):
     * seconds two neighbouring tracks of this type overlap; null / '' =
     * the house value (Settings -> General).  Raw SQL, stored by save().
     *
     * @param mixed $value
     */
    public function setCrossfadeDuration($value)
    {
        $value = is_string($value) ? trim(str_replace(',', '.', $value)) : $value;
        if ($value === null || $value === '' || !is_numeric($value)) {
            $this->_crossfadeDuration = null;
        } else {
            $this->_crossfadeDuration = max(0.0, min(30.0, (float) $value));
        }
        $this->_crossfadeDirty = true;
    }

    /** @return null|float */
    public function getCrossfadeDuration()
    {
        if ($this->_crossfadeDirty) {
            return $this->_crossfadeDuration;
        }
        $id = $this->_tracktypeInstance->getDbId();
        if (!$id) {
            return null;
        }
        $value = Application_Common_Database::prepareAndExecute(
            'SELECT crossfade_duration FROM cc_track_types WHERE id = :id',
            [':id' => $id],
            Application_Common_Database::COLUMN
        );

        return ($value === null || $value === false || $value === '') ? null : (float) $value;
    }

    private $_crossfadeDuration;
    private $_crossfadeDirty = false;

    /**
     * RASTATIME 2026-09-30 - "No Fade during Crossover" as the type's
     * preset (migration 0063): tracks set to "As the track type" keep
     * their level while a neighbour fades.  Raw SQL, stored by save().
     *
     * @param mixed $value
     */
    public function setNoFadeCrossfade($value)
    {
        $this->_noFadeCrossfade = ($value === true || $value === 1 || $value === '1' || $value === 'true');
        $this->_noFadeDirty = true;
    }

    /** @return bool */
    public function getNoFadeCrossfade()
    {
        if ($this->_noFadeDirty) {
            return $this->_noFadeCrossfade;
        }
        $id = $this->_tracktypeInstance->getDbId();
        if (!$id) {
            return false;
        }
        $value = Application_Common_Database::prepareAndExecute(
            'SELECT no_fade_crossfade FROM cc_track_types WHERE id = :id',
            [':id' => $id],
            Application_Common_Database::COLUMN
        );

        return ($value === true || $value === 't' || $value === 1 || $value === '1');
    }

    private $_noFadeCrossfade = false;
    private $_noFadeDirty = false;

    /**
     * RASTATIME 2026-10-14 - stream metadata preset (migration 0068):
     * false = tracks of this type set to "As the track type" show
     * "Station name - Show name" instead of artist / title.  Raw SQL.
     *
     * @param mixed $value
     */
    public function setIcyForward($value)
    {
        $this->_icyForward = ($value === true || $value === 1 || $value === '1' || $value === 'true');
        $this->_icyDirty = true;
    }

    /** @return bool */
    public function getIcyForward()
    {
        if ($this->_icyDirty) {
            return $this->_icyForward;
        }
        $id = $this->_tracktypeInstance->getDbId();
        if (!$id) {
            return true;
        }
        try {
            $value = Application_Common_Database::prepareAndExecute(
                'SELECT icy_forward FROM cc_track_types WHERE id = :id',
                [':id' => $id],
                Application_Common_Database::COLUMN
            );
        } catch (Exception $exc) {
            return true; // column pending (migration 0068)
        }

        return !($value === false || $value === 'f' || $value === 0 || $value === '0');
    }

    private $_icyForward = true;
    private $_icyDirty = false;

    /**
     * RASTATIME 2026-11-13 - loudness analysis per track type (migration
     * 0083).  analyze_loudness FALSE: imports of the type are not measured
     * (ReplayGain, EBU R128), "Measure missing files" leaves its tracks
     * out and the playout applies fixed_gain_db instead of the measured
     * adjustment.  Reads go through to_jsonb(cc_track_types), which yields
     * NULL while the columns do not exist yet; writes wait for them.
     */
    public const FIXED_GAIN_LIMIT_DB = 30.0;

    private static $loudnessColumnsReady;

    /** True once migration 0083 has added the two columns (cached per request when true). */
    public static function loudnessColumnsReady()
    {
        if (self::$loudnessColumnsReady !== true) {
            try {
                $n = Application_Common_Database::prepareAndExecute(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name = 'cc_track_types' "
                    . "AND column_name IN ('analyze_loudness', 'fixed_gain_db')",
                    [],
                    Application_Common_Database::COLUMN
                );
                self::$loudnessColumnsReady = ((int) $n === 2);
            } catch (Exception $exc) {
                return false;
            }
        }

        return self::$loudnessColumnsReady;
    }

    /**
     * SQL that is true for a cc_files row (alias $files) whose track type
     * has the loudness analysis off; FALSE for every row before the
     * migration.
     *
     * @param string $files table name or alias of cc_files
     *
     * @return string
     */
    public static function loudnessOffSql($files = 'cc_files')
    {
        return 'EXISTS (SELECT 1 FROM cc_track_types rt_tt WHERE rt_tt.id = ' . $files . '.track_type_id '
            . "AND to_jsonb(rt_tt) ->> 'analyze_loudness' = 'false')";
    }

    /**
     * @param mixed $raw
     *
     * @return null|float the gain in dB, null when $raw is no number in range
     */
    public static function parseFixedGainDb($raw)
    {
        $text = str_replace(',', '.', trim((string) $raw));
        if ($text === '') {
            return 0.0;
        }
        if (!preg_match('/^[+-]?\d{1,2}(\.\d+)?$/', $text)) {
            return null;
        }
        $value = round((float) $text, 2);
        if (abs($value) > self::FIXED_GAIN_LIMIT_DB) {
            return null;
        }

        return $value == 0.0 ? 0.0 : $value;
    }

    /** @param mixed $value */
    public function setAnalyzeLoudness($value)
    {
        $this->_analyzeLoudness = ($value === true || $value === 1 || $value === '1' || $value === 'true');
        $this->_loudnessDirty = true;
    }

    /** @return bool */
    public function getAnalyzeLoudness()
    {
        if ($this->_loudnessDirty) {
            return $this->_analyzeLoudness;
        }
        $id = $this->_tracktypeInstance->getDbId();
        if (!$id) {
            return true;
        }
        $value = Application_Common_Database::prepareAndExecute(
            "SELECT to_jsonb(t) ->> 'analyze_loudness' FROM cc_track_types t WHERE t.id = :id",
            [':id' => $id],
            Application_Common_Database::COLUMN
        );

        return $value !== 'false';
    }

    /** @param mixed $value a number of dB; anything else counts as 0 */
    public function setFixedGainDb($value)
    {
        $parsed = self::parseFixedGainDb($value);
        $this->_fixedGainDb = $parsed === null ? 0.0 : $parsed;
        $this->_gainDirty = true;
    }

    /** @return float */
    public function getFixedGainDb()
    {
        if ($this->_gainDirty) {
            return $this->_fixedGainDb;
        }
        $id = $this->_tracktypeInstance->getDbId();
        if (!$id) {
            return 0.0;
        }
        $value = Application_Common_Database::prepareAndExecute(
            "SELECT to_jsonb(t) ->> 'fixed_gain_db' FROM cc_track_types t WHERE t.id = :id",
            [':id' => $id],
            Application_Common_Database::COLUMN
        );

        return is_numeric($value) ? round((float) $value, 2) : 0.0;
    }

    private $_analyzeLoudness = true;
    private $_loudnessDirty = false;
    private $_fixedGainDb = 0.0;
    private $_gainDirty = false;


    /**
     * @return array{crossfade: bool, no_fade: bool} which of the two crossover
     *                                              presets of an existing or
     *                                              new type changed
     */
    public function save()
    {
        $changed = ['crossfade' => false, 'no_fade' => false, 'icy' => false, 'gain' => false];
        if ($this->_loudnessDirty || $this->_gainDirty) {
            [$wantLoudness, $wantGain] = [$this->_analyzeLoudness, $this->_fixedGainDb];
            [$loudnessDirty, $gainDirty] = [$this->_loudnessDirty, $this->_gainDirty];
            $this->_loudnessDirty = $this->_gainDirty = false;
            $changed['gain'] = ($loudnessDirty && $this->getAnalyzeLoudness() !== $wantLoudness)
                || ($gainDirty && abs($this->getFixedGainDb() - $wantGain) > 0.004);
            [$this->_loudnessDirty, $this->_gainDirty] = [$loudnessDirty, $gainDirty];
        }
        if ($this->_crossfadeDirty) {
            $this->_crossfadeDirty = false;
            $before = $this->getCrossfadeDuration();
            $this->_crossfadeDirty = true;
            $changed['crossfade'] = ($before !== $this->_crossfadeDuration);
        }
        if ($this->_noFadeDirty) {
            $this->_noFadeDirty = false;
            $before = $this->getNoFadeCrossfade();
            $this->_noFadeDirty = true;
            $changed['no_fade'] = ($before !== $this->_noFadeCrossfade);
        }
        if ($this->_icyDirty) {
            $this->_icyDirty = false;
            $before = $this->getIcyForward();
            $this->_icyDirty = true;
            $changed['icy'] = ($before !== $this->_icyForward);
        }
        $this->_tracktypeInstance->save();
        if ($this->_crossfadeDirty) {
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_track_types SET crossfade_duration = :d WHERE id = :id',
                [':d' => $this->_crossfadeDuration, ':id' => $this->_tracktypeInstance->getDbId()],
                Application_Common_Database::EXECUTE
            );
            $this->_crossfadeDirty = false;
        }
        if ($this->_noFadeDirty) {
            Application_Common_Database::prepareAndExecute(
                'UPDATE cc_track_types SET no_fade_crossfade = :f WHERE id = :id',
                [':f' => $this->_noFadeCrossfade ? 'true' : 'false', ':id' => $this->_tracktypeInstance->getDbId()],
                Application_Common_Database::EXECUTE
            );
            $this->_noFadeDirty = false;
        }
        if ($this->_icyDirty) {
            try {
                Application_Common_Database::prepareAndExecute(
                    'UPDATE cc_track_types SET icy_forward = :f WHERE id = :id',
                    [':f' => $this->_icyForward ? 'true' : 'false', ':id' => $this->_tracktypeInstance->getDbId()],
                    Application_Common_Database::EXECUTE
                );
            } catch (Exception $exc) {
                Logging::warn('Tracktype::save icy_forward: ' . $exc->getMessage() . ' (migration 0068 pending?)');
            }
            $this->_icyDirty = false;
        }
        if ($this->_loudnessDirty || $this->_gainDirty) {
            if (self::loudnessColumnsReady()) {
                $sets = [];
                $params = [':id' => $this->_tracktypeInstance->getDbId()];
                if ($this->_loudnessDirty) {
                    $sets[] = 'analyze_loudness = :l';
                    $params[':l'] = $this->_analyzeLoudness ? 'true' : 'false';
                }
                if ($this->_gainDirty) {
                    $sets[] = 'fixed_gain_db = :g';
                    $params[':g'] = number_format($this->_fixedGainDb, 2, '.', '');
                }
                Application_Common_Database::prepareAndExecute(
                    'UPDATE cc_track_types SET ' . implode(', ', $sets) . ' WHERE id = :id',
                    $params,
                    Application_Common_Database::EXECUTE
                );
            } else {
                $changed['gain'] = false;
                Logging::warn('Tracktype::save: loudness analysis / fixed gain not stored (migration 0083 pending)');
            }
            $this->_loudnessDirty = $this->_gainDirty = false;
        }

        return $changed;
    }

    public function delete()
    {
        if (!$this->_tracktypeInstance->isDeleted()) {
            $this->_tracktypeInstance->delete();
        }
    }

    private function createTracktype()
    {
        return new CcTracktypes();
    }

    public static function getTracktypes($search = null)
    {
        return Application_Model_Tracktype::getTracktypesData([true], $search);
    }

    public static function getTracktypesData(array $visible, $search = null)
    {
        $con = Propel::getConnection();

        $sql_gen = 'SELECT id, code, type_name, description FROM cc_track_types ';

        $visibility = [];
        $params = [];
        for ($i = 0; $i < count($visible); ++$i) {
            $p = ":visibility{$i}";
            $visibility[] = "visibility = {$p}";
            $params[$p] = $visible[$i];
        }

        $sql_type = implode(' OR ', $visibility);

        $sql = $sql_gen . ' WHERE (' . $sql_type . ') ';

        $sql .= ' AND code ILIKE :search';
        $params[':search'] = "%{$search}%";

        $sql .= ' ORDER BY id';

        return Application_Common_Database::prepareAndExecute($sql, $params, 'all');
    }

    public static function getTracktypeCount()
    {
        $sql_gen = 'SELECT count(*) AS cnt FROM cc_track_types';

        $query = Application_Common_Database::prepareAndExecute(
            $sql_gen,
            [],
            Application_Common_Database::COLUMN
        );

        return ($query !== false) ? $query : null;
    }

    public static function getTracktypesDataTablesInfo($datatables)
    {
        $con = Propel::getConnection(CcTracktypesPeer::DATABASE_NAME);

        $displayColumns = ['id', 'code', 'type_name', 'description', 'visibility'];
        $fromTable = 'cc_track_types';
        $tracktypename = '';

        $res = Application_Model_Datatables::findEntries($con, $displayColumns, $fromTable, $datatables);

        foreach ($res['aaData'] as $key => &$record) {
            if ($record['code'] == $tracktypename) {
                $record['delete'] = 'self';
            } else {
                $record['delete'] = '';
            }
            $record = array_map('htmlspecialchars', $record);
        }

        $res['aaData'] = array_values($res['aaData']);

        return $res;
    }

    public static function getTracktypeData($id)
    {
        $sql = <<<'SQL'
SELECT code, type_name, description, visibility, id, analyze_cue_points, crossfade_duration, no_fade_crossfade, icy_forward,
       COALESCE((to_jsonb(cc_track_types) ->> 'analyze_loudness')::boolean, TRUE) AS analyze_loudness,
       COALESCE((to_jsonb(cc_track_types) ->> 'fixed_gain_db')::numeric, 0) AS fixed_gain_db
FROM cc_track_types
WHERE id = :id
SQL;

        return Application_Common_Database::prepareAndExecute($sql, [
            ':id' => $id,
        ], 'single');
    }

    /**
     * RASTATIME 2026-11-09 - the visible track types for the analyzer's import
     * message (option track_types): a Media Type tag (ID3 TMED) that names
     * one of them by code or name makes it the track's type, and that type's
     * analyze_cue_points decides the cue point analysis.  Visible = the types
     * the upload dialog offers.  An empty list (also on a database error)
     * leaves the tag unused - the import itself never fails for it.
     *
     * @return array list of ['id' => int, 'code' => string, 'name' => ?string,
     *               'analyze_cue_points' => bool]
     */
    public static function analyzerTrackTypes()
    {
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                'SELECT id, code, type_name, analyze_cue_points, '
                . "COALESCE((to_jsonb(cc_track_types) ->> 'analyze_loudness')::boolean, TRUE) AS analyze_loudness "
                . 'FROM cc_track_types WHERE visibility ORDER BY id',
                [],
                'all'
            );
        } catch (Exception $e) {
            Logging::warn('analyzerTrackTypes: ' . $e->getMessage());

            return [];
        }
        $types = [];
        foreach ((array) $rows as $row) {
            $types[] = [
                'id' => (int) $row['id'],
                'code' => (string) $row['code'],
                'name' => $row['type_name'] === null ? null : (string) $row['type_name'],
                'analyze_cue_points' => (bool) $row['analyze_cue_points'],
                // RASTATIME 2026-11-13 - false: imports of the type are not measured
                'analyze_loudness' => !($row['analyze_loudness'] === false || $row['analyze_loudness'] === 'f'
                    || $row['analyze_loudness'] === 0 || $row['analyze_loudness'] === '0'),
            ];
        }

        return $types;
    }

    /**
     * RASTATIME 2026-11-09 - the id of the VISIBLE track type with exactly
     * this code (the analyzer reports the Media Type tag's type by code), or
     * null: a type deleted or hidden since the upload is no longer taken.
     *
     * @param mixed $code
     *
     * @return null|int
     */
    public static function visibleIdByCode($code)
    {
        $code = trim((string) $code);
        if ($code === '') {
            return null;
        }
        $id = Application_Common_Database::prepareAndExecute(
            'SELECT id FROM cc_track_types WHERE code = :code AND visibility',
            [':code' => $code],
            Application_Common_Database::COLUMN
        );

        return ($id === false || $id === null) ? null : (int) $id;
    }
}
