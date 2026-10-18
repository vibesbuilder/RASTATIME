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
     * @return array{crossfade: bool, no_fade: bool} which of the two crossover
     *                                              presets of an existing or
     *                                              new type changed
     */
    public function save()
    {
        $changed = ['crossfade' => false, 'no_fade' => false, 'icy' => false];
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
SELECT code, type_name, description, visibility, id, analyze_cue_points, crossfade_duration, no_fade_crossfade, icy_forward
FROM cc_track_types
WHERE id = :id
SQL;

        return Application_Common_Database::prepareAndExecute($sql, [
            ':id' => $id,
        ], 'single');
    }
}
