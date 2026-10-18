<?php

/**
 *  Application_Model_StoredFile class.
 *
 * @copyright 2010 Sourcefabric O.P.S.
 * @license https://www.gnu.org/licenses/gpl.txt
 *
 * @see MetaData
 */
class Application_Model_StoredFile
{
    /**
     * @holds propel database object
     *
     * @var CcFiles
     */
    private $_file;

    /**
     * @holds PDO object reference
     */
    private $_con;

    /**
     * array of db metadata -> propel.
     */
    private $_dbMD = [
        'track_title' => 'DbTrackTitle',
        'artist_name' => 'DbArtistName',
        'album_title' => 'DbAlbumTitle',
        'genre' => 'DbGenre',
        'mood' => 'DbMood',
        'track_number' => 'DbTrackNumber',
        'bpm' => 'DbBpm',
        'label' => 'DbLabel',
        'composer' => 'DbComposer',
        'encoded_by' => 'DbEncodedBy',
        'conductor' => 'DbConductor',
        'year' => 'DbYear',
        'info_url' => 'DbInfoUrl',
        'isrc_number' => 'DbIsrcNumber',
        'copyright' => 'DbCopyright',
        'length' => 'DbLength',
        'bit_rate' => 'DbBitRate',
        'sample_rate' => 'DbSampleRate',
        'mime' => 'DbMime',
        // "md5"          => "DbMd5",
        'ftype' => 'DbFtype',
        'language' => 'DbLanguage',
        'replay_gain' => 'DbReplayGain',
        'owner_id' => 'DbOwnerId',
        'cuein' => 'DbCueIn',
        'cueout' => 'DbCueOut',
        'description' => 'DbDescription',
        'artwork' => 'DbArtwork',
        'track_type_id' => 'DbTrackTypeId',
    ];

    public function __construct($file, $con)
    {
        $this->_file = $file;
        $this->_con = $con;
    }

    public function getId()
    {
        return $this->_file->getDbId();
    }

    public function getFormat()
    {
        return $this->_file->getDbFtype();
    }

    /**
     * @return CcFiles
     */
    public function getPropelOrm()
    {
        return $this->_file;
    }

    public function setFormat($p_format)
    {
        $this->_file->setDbFtype($p_format);
    }

    /* This function is only called after liquidsoap
     * has notified that a track has started playing.
     */
    public function setLastPlayedTime($p_now)
    {
        $this->_file->setDbLPtime($p_now);
        /* Normally we would only call save after all columns have been set
         * like in setDbColMetadata(). But since we are only setting one
         * column in this case it is OK.
         */
        $this->_file->save();
    }

    public static function createWithFile($f, $con)
    {
        return new Application_Model_StoredFile($f, $con);
    }

    /**
     * Set multiple metadata values using defined metadata constants.
     *
     * @param array $p_md
     *                    example: $p_md['MDATA_KEY_URL'] = 'https://example.org'
     */
    public function setMetadata($p_md = null)
    {
        if (is_null($p_md)) {
            $this->setDbColMetadata();
        } else {
            $dbMd = [];

            if (isset($p_md['MDATA_KEY_YEAR'])) {
                // We need to make sure to clean this value before
                // inserting into database. If value is outside of range
                // [-2^31, 2^31-1] then postgresl will throw error when
                // trying to retrieve this value. We could make sure
                // number is within these bounds, but simplest is to do
                // substring to 4 digits (both values are garbage, but
                // at least our new garbage value won't cause errors).
                // If the value is 2012-01-01, then substring to first 4
                // digits is an OK result. CC-3771

                $year = $p_md['MDATA_KEY_YEAR'];

                if (strlen($year) > 4) {
                    $year = substr($year, 0, 4);
                }
                if (!is_numeric($year)) {
                    $year = 0;
                }
                $p_md['MDATA_KEY_YEAR'] = $year;
            }

            // Translate metadata attributes from media monitor (MDATA_KEY_*)
            // to their counterparts in constants.php (usually the column names)
            $track_length = $p_md['MDATA_KEY_DURATION'];
            $track_length_in_sec = Application_Common_DateHelper::calculateLengthInSeconds($track_length);
            foreach ($p_md as $mdConst => $mdValue) {
                if (defined($mdConst)) {
                    if ($mdConst == 'MDATA_KEY_CUE_OUT') {
                        if ($mdValue == '0.0') {
                            $mdValue = $track_length_in_sec;
                        } else {
                            $this->_file->setDbSilanCheck(true)->save();
                        }
                    }
                    $dbMd[constant($mdConst)] = $mdValue;
                }
            }
            $this->setDbColMetadata($dbMd);
        }
    }

    /**
     * Set multiple metadata values using database columns as indexes.
     *
     * @param array $p_md
     *                    example: $p_md['url'] = 'https://www.example.com'
     */
    public function setDbColMetadata($p_md = null)
    {
        if (is_null($p_md)) {
            foreach ($this->_dbMD as $dbColumn => $propelColumn) {
                $method = "set{$propelColumn}";
                $this->_file->{$method}(null);
            }
        } else {
            // in order to edit the owner of a file we see if owner_id exists in the track form metadata otherwise
            // we determine it via the algorithm below
            if (!array_key_exists('owner_id', $p_md)) {
                $owner = $this->_file->getFkOwner();
                // if owner_id is already set we don't want to set it again.
                if (!$owner) { // no owner detected, we try to assign one.
                    // if MDATA_OWNER_ID is not set then we default to the
                    // first admin user we find
                    if (!array_key_exists('owner_id', $p_md)) {
                        // $admins = Application_Model_User::getUsers(array('A'));
                        $admins = array_merge(
                            Application_Model_User::getUsersOfType('A')->getData(),
                            Application_Model_User::getUsersOfType('S')->getData()
                        );
                        if (count($admins) > 0) { // found admin => pick first one
                            $owner = $admins[0];
                        }
                    } // get the user by id and set it like that
                    else {
                        $user = CcSubjsQuery::create()
                            ->findPk($p_md['owner_id']);
                        if ($user) {
                            $owner = $user;
                        }
                    }
                    if ($owner) {
                        $this->_file->setDbOwnerId($owner->getDbId());
                    } else {
                        Logging::info("Could not find suitable owner for file
                        '" . $p_md['filepath'] . "'");
                    }
                }
            }
            // RASTATIME 2026-09-30 - cue points are kept inside the file:
            // cue in never below 0, cue out never past the length (the
            // editor accepted 6.90 s on a 5.97 s file - a silent second
            // before the next element once jingles no longer overlap).
            // The values before the save decide whether the upcoming
            // rows have to follow.
            $cuesBefore = null;
            if (array_key_exists('cuein', $p_md) || array_key_exists('cueout', $p_md)) {
                $lengthSeconds = Application_Common_DateHelper::playlistTimeToSeconds(
                    (string) $this->_file->getDbLength()
                );
                $cuesBefore = [
                    Application_Common_DateHelper::playlistTimeToSeconds((string) $this->_file->getDbCuein()),
                    Application_Common_DateHelper::playlistTimeToSeconds((string) $this->_file->getDbCueout()),
                ];
                $cueinSeconds = array_key_exists('cuein', $p_md) && $p_md['cuein'] !== '' && $p_md['cuein'] !== null
                    ? Application_Common_DateHelper::playlistTimeToSeconds((string) $p_md['cuein'])
                    : $cuesBefore[0];
                $cueoutSeconds = array_key_exists('cueout', $p_md) && $p_md['cueout'] !== '' && $p_md['cueout'] !== null
                    ? Application_Common_DateHelper::playlistTimeToSeconds((string) $p_md['cueout'])
                    : $cuesBefore[1];
                [$cueinSeconds, $cueoutSeconds] = Application_Model_CuePoints::clamp(
                    $cueinSeconds,
                    $cueoutSeconds,
                    $lengthSeconds
                );
                $p_md['cuein'] = Application_Model_CuePoints::formatSeconds($cueinSeconds);
                $p_md['cueout'] = Application_Model_CuePoints::formatSeconds($cueoutSeconds);
                if (abs($cueinSeconds - $cuesBefore[0]) < 0.0005 && abs($cueoutSeconds - $cuesBefore[1]) < 0.0005) {
                    $cuesBefore = null;   // unchanged: nothing to propagate
                }
            }
            foreach ($p_md as $dbColumn => $mdValue) {
                // don't blank out name, defaults to original filename on first
                // insertion to database.
                if ($dbColumn == 'track_title' && (is_null($mdValue) || $mdValue == '')) {
                    continue;
                }

                // Bpm gets POSTed as a string type. With Propel 1.6 this value
                // was casted to an integer type before saving it to the db. But
                // Propel 1.7 does not do this
                if ($dbColumn == 'bpm') {
                    $mdValue = (int) $mdValue;
                }
                // TODO : refactor string evals
                if (isset($this->_dbMD[$dbColumn])) {
                    $propelColumn = $this->_dbMD[$dbColumn];
                    $method = "set{$propelColumn}";

                    /* We need to set track_number to null if it is an empty string
                     * because propel defaults empty strings to zeros */
                    if ($dbColumn == 'track_number' && empty($mdValue)) {
                        $mdValue = null;
                    }

                    // We need to set track_type_id to null if it is an empty string or 0
                    if ($dbColumn == 'track_type_id' && ($mdValue == 0 || empty($mdValue))) {
                        $mdValue = null;
                    }

                    $this->_file->{$method}($mdValue);
                }
            }
        }

        $this->_file->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
        $this->_file->save($this->_con);

        // RASTATIME 2026-09-30 - changed cue points follow into the rows of
        // the upcoming shows (the schedule keeps its own copy from the
        // moment a row was inserted); the instances are laid out again.
        if ($cuesBefore !== null) {
            try {
                $instances = Application_Model_CuePoints::applyToFutureRows($this->_file->getDbId(), $this->_con);
                Application_Model_CuePoints::relayoutInstances($instances);
                Logging::info('cue points of file ' . $this->_file->getDbId() . ' changed ('
                    . $p_md['cuein'] . ' - ' . $p_md['cueout'] . '): ' . count($instances)
                    . ' upcoming instance(s) follow');
            } catch (Exception $exc) {
                Logging::warn('cue points: propagation failed: ' . $exc->getMessage());
            }
        }

        // RASTATIME 2026-05-16 - Track Expiry (expires_at).  Propel
        // classes are not regenerated for the new column, so we apply
        // the value via raw SQL after the regular save.  Accepts
        // YYYY-MM-DD; empty string clears.  Also re-enables the row
        // (disabled = false) when the operator picks a future date or
        // clears the expiry — symmetric to the pruner which only ever
        // flips disabled to true.
        if (is_array($p_md) && array_key_exists('expires_at', $p_md)) {
            $raw = trim((string) $p_md['expires_at']);
            $fileId = $this->_file->getDbId();
            if ($raw === '') {
                $stmt = $this->_con->prepare(
                    'UPDATE cc_files
                     SET expires_at = NULL, disabled = false
                     WHERE id = :id'
                );
                $stmt->bindValue(':id', $fileId, PDO::PARAM_INT);
                $stmt->execute();
            } elseif (preg_match('/^\d{4}-\d{2}-\d{2}$/', $raw)) {
                // RASTATIME 2026-05-18 — split into two named placeholders.
                // PostgreSQL's native prepared statements (PDO with
                // ATTR_EMULATE_PREPARES=false, the default) reject the
                // same `:exp` token bound twice, which silently throws
                // away the entire UPDATE — the operator sees the form
                // close as if saved, but the DB never gets the new value.
                // Two distinct placeholders bound with the same value
                // sidestep this PDO quirk while keeping the SQL
                // semantics identical.
                $stmt = $this->_con->prepare(
                    'UPDATE cc_files
                     SET expires_at = :exp_set,
                         disabled = (CAST(:exp_cmp AS TIMESTAMP) < NOW())
                     WHERE id = :id'
                );
                $stmt->bindValue(':exp_set', $raw, PDO::PARAM_STR);
                $stmt->bindValue(':exp_cmp', $raw, PDO::PARAM_STR);
                $stmt->bindValue(':id', $fileId, PDO::PARAM_INT);
                $stmt->execute();
            }
        }

        // RASTATIME 2026-09-27 - "No Fade during Crossover" (migrations 0059/0060):
        // the checkbox posts '1' / '0'; only touched when the key is present
        // (the analyzer's metadata import never sends it).
        if (is_array($p_md) && array_key_exists('no_fade_crossfade', $p_md)) {
            $raw = $p_md['no_fade_crossfade'];
            $flag = ($raw === true || $raw === 1 || $raw === '1' || $raw === 'true' || $raw === 'on');
            $stmt = $this->_con->prepare(
                'UPDATE cc_files SET no_fade_crossfade = :flag WHERE id = :id'
            );
            $stmt->bindValue(':flag', $flag, PDO::PARAM_BOOL);
            $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
            $stmt->execute();
        }

        // RASTATIME 2026-09-29 - the track editor's three-way "Crossover"
        // field (type | nofade | exclude) sets both flags at once, so they
        // can never be on together.  A change re-lays the rows of the
        // upcoming shows that schedule this track.
        // RASTATIME 2026-10-14 - "Stream Metadata": type (NULL) | forward (1) | hide (0)
        if (is_array($p_md) && array_key_exists('icy_mode', $p_md)) {
            $icy = in_array($p_md['icy_mode'], ['type', 'forward', 'hide'], true)
                ? $p_md['icy_mode'] : 'type';
            try {
                $stmt = $this->_con->prepare('UPDATE cc_files SET icy_forward = :v WHERE id = :id');
                if ($icy === 'type') {
                    $stmt->bindValue(':v', null, PDO::PARAM_NULL);
                } else {
                    $stmt->bindValue(':v', $icy === 'forward' ? 1 : 0, PDO::PARAM_INT);
                }
                $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
                $stmt->execute();
            } catch (Exception $exc) {
                Logging::warn('icy_mode: ' . $exc->getMessage() . ' (migration 0068 pending?)');
            }
        }
        // RASTATIME 2026-10-16 - teaser links (migrations 0069/0070).  The
        // single editor posts the multiselect (absent when nothing is
        // selected, hence the hidden teaser_shows_sent marker) and the type;
        // the bulk editor only the filled field(s); a missing key keeps the
        // stored value.  'none' / an empty list clears the links; shows
        // without a type become show teasers.
        if (is_array($p_md) && (array_key_exists('teaser_show_id', $p_md) || array_key_exists('teaser_shows_sent', $p_md)
            || array_key_exists('teaser_type', $p_md))) {
            [$curShows, $curType] = self::teaserOf($this->_con, $this->_file->getDbId());
            $showsGiven = array_key_exists('teaser_show_id', $p_md) || array_key_exists('teaser_shows_sent', $p_md);
            $raw = $p_md['teaser_show_id'] ?? [];
            if (is_string($raw)) {
                $raw = $raw === '' ? [] : explode(',', $raw);
            }
            $shows = $showsGiven ? array_values(array_unique(array_filter(array_map('intval', (array) $raw), static fn ($v) => $v > 0))) : array_map('intval', $curShows);
            if ($showsGiven && in_array('none', array_map('strval', (array) $raw), true)) {
                $shows = [];
            }
            $type = array_key_exists('teaser_type', $p_md) ? trim((string) $p_md['teaser_type']) : $curType;
            if ($type === 'none') {
                $shows = [];
            }
            if ($shows) {
                $known = array_map('intval', CcShowQuery::create()->filterByDbId($shows)->select('DbId')->find()->getData());
                $shows = array_values(array_intersect($shows, $known));
            }
            if ($shows && !in_array($type, self::TEASER_TYPES, true)) {
                // the forms refuse this; a raw caller gets a log line, not a guess
                Logging::warn('teaser: shows without a type for file ' . $this->_file->getDbId() . ' - not saved');
                $shows = [];
                $type = $curType ?: null;
                if (!$curShows) {
                    return;
                }
                $shows = array_map('intval', $curShows);
            }
            try {
                $this->_con->beginTransaction();
                $stmt = $this->_con->prepare('DELETE FROM cc_file_teaser WHERE file_id = :id');
                $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
                $stmt->execute();
                $ins = $this->_con->prepare('INSERT INTO cc_file_teaser (file_id, show_id) VALUES (:f, :s)');
                foreach ($shows as $sid) {
                    $ins->bindValue(':f', $this->_file->getDbId(), PDO::PARAM_INT);
                    $ins->bindValue(':s', (int) $sid, PDO::PARAM_INT);
                    $ins->execute();
                }
                $stmt = $this->_con->prepare('UPDATE cc_files SET teaser_type = :t WHERE id = :id');
                if ($shows) {
                    $stmt->bindValue(':t', $type, PDO::PARAM_STR);
                } else {
                    $stmt->bindValue(':t', null, PDO::PARAM_NULL);
                }
                $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
                $stmt->execute();
                $this->_con->commit();
            } catch (Exception $exc) {
                try {
                    $this->_con->rollBack();
                } catch (Exception $ignored) {
                }
                Logging::warn('teaser: ' . $exc->getMessage() . ' (migration 0070 pending?)');
            }
        }
    }

    /**
     * RASTATIME 2026-10-14 - the stream-metadata choice of a file:
     * type | forward | hide (cc_files.icy_forward NULL | 1 | 0, migration 0068).
     *
     * @param mixed $con
     * @param mixed $fileId
     */
    public static function icyModeOf($con, $fileId)
    {
        try {
            $stmt = $con->prepare('SELECT icy_forward FROM cc_files WHERE id = :id');
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $v = $stmt->fetchColumn();
            if ($v === null || $v === false || $v === '') {
                return 'type';
            }

            return ((int) $v) === 0 ? 'hide' : 'forward';
        } catch (Exception $exc) {
            Logging::warn('icyModeOf: ' . $exc->getMessage());

            return 'type';
        }
    }

    /**
     * RASTATIME 2026-09-29 - the crossover mode of a file: type | nofade | exclude.
     *
     * @param mixed $con
     * @param mixed $fileId
     */
    public static function crossoverModeOf($con, $fileId)
    {
        try {
            $stmt = $con->prepare(
                'SELECT no_fade_crossfade, exclude_crossfade FROM cc_files WHERE id = :id'
            );
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $row = $stmt->fetch(PDO::FETCH_ASSOC);
            $on = function ($v) {
                return $v === true || $v === 't' || $v === 1 || $v === '1';
            };
            if ($row && $on($row['exclude_crossfade'])) {
                return 'exclude';
            }
            if ($row && $on($row['no_fade_crossfade'])) {
                return 'nofade';
            }
        } catch (Exception $exc) {
            Logging::warn('crossoverModeOf: ' . $exc->getMessage());
        }

        return 'type';
    }

    /**
     * Set metadata element value.
     *
     * @param mixed $p_category
     * @param mixed $p_value
     */
    public function setMetadataValue($p_category, $p_value)
    {
        // constant() was used because it gets quoted constant name value from
        // api_client.py. This is the wrapper funtion
        $this->setDbColMetadataValue(constant($p_category), $p_value);
    }

    /**
     * Set metadata element value.
     *
     * @param mixed $p_category
     * @param mixed $p_value
     */
    public function setDbColMetadataValue($p_category, $p_value)
    {
        // don't blank out name, defaults to original filename on first insertion to database.
        if ($p_category == 'track_title' && (is_null($p_value) || $p_value == '')) {
            return;
        }
        if (isset($this->_dbMD[$p_category])) {
            // TODO : fix this crust -- RG
            $propelColumn = $this->_dbMD[$p_category];
            $method = "set{$propelColumn}";
            $this->_file->{$method}($p_value);
            $this->_file->save();
        }
    }

    /**
     * Get metadata as array, indexed by the column names in the database.
     *
     * @return array
     */
    public function getDbColMetadata()
    {
        $md = [];
        foreach ($this->_dbMD as $dbColumn => $propelColumn) {
            $method = "get{$propelColumn}";
            $md[$dbColumn] = $this->_file->{$method}();
        }

        // RASTATIME 2026-05-16 - Track Expiry: read expires_at via raw
        // SQL (Propel class not regenerated for the column).  Format as
        // YYYY-MM-DD for the edit form's date input.  NULL => empty
        // string so the form shows an empty field.
        try {
            $stmt = $this->_con->prepare(
                "SELECT TO_CHAR(expires_at, 'YYYY-MM-DD') FROM cc_files WHERE id = :id"
            );
            $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
            $stmt->execute();
            $value = $stmt->fetchColumn();
            $md['expires_at'] = ($value === false || $value === null) ? '' : (string) $value;
        } catch (Exception $exc) {
            Logging::warn('getDbColMetadata: could not read expires_at: ' . $exc->getMessage());
            $md['expires_at'] = '';
        }

        // RASTATIME 2026-09-27 - "No Fade during Crossover" (migrations 0059/0060),
        // raw SQL like expires_at; '1' / '0' for the form checkbox.
        try {
            $stmt = $this->_con->prepare(
                'SELECT no_fade_crossfade FROM cc_files WHERE id = :id'
            );
            $stmt->bindValue(':id', $this->_file->getDbId(), PDO::PARAM_INT);
            $stmt->execute();
            $flag = $stmt->fetchColumn();
            $md['no_fade_crossfade'] = ($flag === true || $flag === 't' || $flag === 1 || $flag === '1') ? '1' : '0';
        } catch (Exception $exc) {
            Logging::warn('getDbColMetadata: could not read no_fade_crossfade: ' . $exc->getMessage());
            $md['no_fade_crossfade'] = '0';
        }
        // RASTATIME 2026-09-29 - the three-way "Crossover" field of the track editor
        $md['crossover_mode'] = self::crossoverModeOf($this->_con, $this->_file->getDbId());
        // RASTATIME 2026-10-14 - the three-way "Stream Metadata" field
        $md['icy_mode'] = self::icyModeOf($this->_con, $this->_file->getDbId());
        // RASTATIME 2026-10-16 - teaser automation (migrations 0069/0070):
        // the shows as a list of ids (multiselect), the type as a word
        [$md['teaser_show_id'], $md['teaser_type']] = self::teaserOf($this->_con, $this->_file->getDbId());

        return $md;
    }

    /**
     * RASTATIME 2026-10-16 - teaser automation.  A jingle may announce one
     * show (cc_files.teaser_show_id) in one way (cc_files.teaser_type):
     * 'show' = show teaser, usable any day; 'today' = "the show airs
     * today"; 'tomorrow' = "the show airs tomorrow".  Smart blocks pick
     * the fitting jingles (Block::teaserCriterionSql).
     */
    public const TEASER_TYPES = ['show', 'today', 'tomorrow'];

    private static $teaserColumnsReady;

    /**
     * True once migrations 0069 + 0070 have added cc_files.teaser_type and
     * the link table cc_file_teaser.  Cached per request so the library
     * query does not probe the catalogue per row.
     *
     * @param mixed $con
     */
    public static function teaserColumnsReady($con = null)
    {
        if (self::$teaserColumnsReady === null) {
            try {
                $con = $con ?: Propel::getConnection(CcFilesPeer::DATABASE_NAME);
                // EXISTS, not "1 AND 1": integer AND integer is no PostgreSQL
                // operator and the failed probe read as "not ready" (2026-10-16)
                $stmt = $con->prepare(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cc_files' AND column_name = 'teaser_type') "
                    . "AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cc_file_teaser')"
                );
                $stmt->execute();
                $v = $stmt->fetchColumn();
                self::$teaserColumnsReady = ($v === true || $v === 't' || $v === 1 || $v === '1');
            } catch (Exception $exc) {
                self::$teaserColumnsReady = false;
            }
        }

        return self::$teaserColumnsReady;
    }

    /**
     * [list of show ids as strings, type or ''] of a file.  A file without
     * linked shows is no teaser, whatever its type column says.
     *
     * @param mixed $con
     * @param mixed $fileId
     */
    public static function teaserOf($con, $fileId)
    {
        if (!self::teaserColumnsReady($con)) {
            return [[], ''];
        }
        try {
            $stmt = $con->prepare('SELECT show_id FROM cc_file_teaser WHERE file_id = :id ORDER BY show_id');
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $ids = array_map(static fn ($v) => (string) (int) $v, $stmt->fetchAll(PDO::FETCH_COLUMN));
            if (empty($ids)) {
                return [[], ''];
            }
            $stmt = $con->prepare('SELECT teaser_type FROM cc_files WHERE id = :id');
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $type = $stmt->fetchColumn();

            return [$ids, in_array($type, self::TEASER_TYPES, true) ? $type : 'show'];
        } catch (Exception $exc) {
            Logging::warn('teaserOf: ' . $exc->getMessage());

            return [[], ''];
        }
    }

    /**
     * Shows a teaser can announce: every show with an upcoming instance,
     * labelled with its next airing (several shows share a name, e.g. the
     * hourly "bbc" slots); $includeIds adds a file's current shows even
     * when they have no upcoming instance any more.  id => label.
     *
     * @param null|array $includeIds
     */
    public static function teaserShows($includeIds = null)
    {
        $ids = array_values(array_filter(array_map('intval', (array) ($includeIds ?: [])), static fn ($v) => $v > 0));
        $inner = 'SELECT s.id, s.name, MIN(i.starts) AS next_start FROM cc_show s '
            . 'JOIN cc_show_instances i ON i.show_id = s.id AND i.modified_instance = FALSE AND i.ends > NOW() '
            . 'GROUP BY s.id, s.name';
        if ($ids) {
            $inner .= ' UNION SELECT s.id, s.name, NULL FROM cc_show s WHERE s.id IN (' . implode(',', $ids) . ') AND NOT EXISTS ('
                . 'SELECT 1 FROM cc_show_instances i WHERE i.show_id = s.id AND i.modified_instance = FALSE AND i.ends > NOW())';
        }
        // ORDER BY an expression is not allowed on a UNION: sort the wrapped result
        $sql = "SELECT id, name, next_start FROM ({$inner}) AS shows ORDER BY LOWER(name), next_start NULLS LAST, id";
        $out = [];
        try {
            $tz = new DateTimeZone(Application_Model_Preference::GetDefaultTimezone() ?: 'UTC');
            foreach (Application_Common_Database::prepareAndExecute($sql, [], 'all') as $r) {
                $label = (string) $r['name'];
                if (!empty($r['next_start'])) {
                    $next = new DateTime($r['next_start'], new DateTimeZone('UTC'));
                    $next->setTimezone($tz);
                    $label .= ' (' . $next->format('D H:i') . ')';
                }
                $out[(int) $r['id']] = $label;
            }
        } catch (Exception $exc) {
            Logging::warn('teaserShows: ' . $exc->getMessage());
        }

        return $out;
    }

    /**
     * RASTATIME 2026-10-16 - stage 2: the jingles linked to one show, for the
     * calendar dialog "Teasers".  id, title, artist, type, the show's other
     * teased shows as a text.
     *
     * @param mixed $showId
     */
    public static function teasersOfShow($showId)
    {
        if (!self::teaserColumnsReady()) {
            return [];
        }
        $sql = 'SELECT f.id, f.track_title, f.artist_name, COALESCE(f.teaser_type, \'show\') AS teaser_type, '
            . '(SELECT string_agg(s2.name, \', \' ORDER BY s2.name) FROM cc_file_teaser t2 JOIN cc_show s2 ON s2.id = t2.show_id '
            . ' WHERE t2.file_id = f.id AND t2.show_id <> t.show_id) AS other_shows '
            . 'FROM cc_file_teaser t JOIN cc_files f ON f.id = t.file_id '
            . 'WHERE t.show_id = :sid AND f.file_exists = TRUE AND f.hidden = FALSE '
            . 'ORDER BY f.teaser_type, LOWER(f.track_title), f.id';

        return Application_Common_Database::prepareAndExecute($sql, [':sid' => (int) $showId], 'all');
    }

    /**
     * Link one jingle to one show; a given type is written to the jingle
     * (it applies to all its shows).  Returns false when file or show do
     * not exist.
     *
     * @param mixed       $fileId
     * @param mixed       $showId
     * @param null|string $type
     */
    public static function teaserLink($fileId, $showId, $type = null)
    {
        if (!self::teaserColumnsReady()) {
            return false;
        }
        if (CcFilesQuery::create()->findPk((int) $fileId) === null || CcShowQuery::create()->findPk((int) $showId) === null) {
            return false;
        }
        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        $con->beginTransaction();

        try {
            $stmt = $con->prepare('INSERT INTO cc_file_teaser (file_id, show_id) VALUES (:f, :s) ON CONFLICT DO NOTHING');
            $stmt->bindValue(':f', (int) $fileId, PDO::PARAM_INT);
            $stmt->bindValue(':s', (int) $showId, PDO::PARAM_INT);
            $stmt->execute();
            $t = in_array($type, self::TEASER_TYPES, true) ? $type : null;
            // a jingle linked without a type keeps its own; a jingle without any becomes a show teaser
            $stmt = $con->prepare('UPDATE cc_files SET teaser_type = COALESCE(:t, teaser_type, \'show\') WHERE id = :id');
            $stmt->bindValue(':t', $t, $t === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $con->commit();
        } catch (Exception $exc) {
            $con->rollBack();
            Logging::warn('teaserLink: ' . $exc->getMessage());

            return false;
        }

        return true;
    }

    /**
     * Remove the link of one jingle to one show; a jingle without any
     * show left loses its type.
     *
     * @param mixed $fileId
     * @param mixed $showId
     */
    public static function teaserUnlink($fileId, $showId)
    {
        if (!self::teaserColumnsReady()) {
            return false;
        }
        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        $con->beginTransaction();

        try {
            $stmt = $con->prepare('DELETE FROM cc_file_teaser WHERE file_id = :f AND show_id = :s');
            $stmt->bindValue(':f', (int) $fileId, PDO::PARAM_INT);
            $stmt->bindValue(':s', (int) $showId, PDO::PARAM_INT);
            $stmt->execute();
            $stmt = $con->prepare('UPDATE cc_files SET teaser_type = NULL WHERE id = :id AND NOT EXISTS (SELECT 1 FROM cc_file_teaser t WHERE t.file_id = :id2)');
            $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
            $stmt->bindValue(':id2', (int) $fileId, PDO::PARAM_INT);
            $stmt->execute();
            $con->commit();
        } catch (Exception $exc) {
            $con->rollBack();
            Logging::warn('teaserUnlink: ' . $exc->getMessage());

            return false;
        }

        return true;
    }

    /**
     * Audio files whose title or artist contains $q and that are not yet
     * linked to $showId (at most 20, by title), for the dialog's picker.
     *
     * @param string $q
     * @param mixed  $showId
     */
    public static function teaserSearch($q, $showId)
    {
        $q = trim((string) $q);
        if (!self::teaserColumnsReady() || mb_strlen($q) < 2) {
            return [];
        }
        $like = '%' . str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $q) . '%';
        $sql = 'SELECT f.id, f.track_title, f.artist_name, f.teaser_type, '
            . '(SELECT string_agg(s2.name, \', \' ORDER BY s2.name) FROM cc_file_teaser t2 JOIN cc_show s2 ON s2.id = t2.show_id WHERE t2.file_id = f.id) AS shows '
            . 'FROM cc_files f WHERE f.file_exists = TRUE AND f.hidden = FALSE AND COALESCE(f.ftype, \'audioclip\') IN (\'audioclip\', \'\') '
            . 'AND (f.track_title ILIKE :q OR f.artist_name ILIKE :q2) '
            . 'AND NOT EXISTS (SELECT 1 FROM cc_file_teaser t WHERE t.file_id = f.id AND t.show_id = :sid) '
            . 'ORDER BY LOWER(f.track_title), f.id LIMIT 20';

        return Application_Common_Database::prepareAndExecute($sql, [':q' => $like, ':q2' => $like, ':sid' => (int) $showId], 'all');
    }

    /** value => label of the three teaser types (translated). */
    public static function teaserTypeLabels()
    {
        return [
            'show' => _('Show teaser (any day)'),
            'today' => _('Day teaser: "today"'),
            'tomorrow' => _('Day teaser: "tomorrow"'),
        ];
    }

    /**
     * Get metadata as array, indexed by the constant names.
     *
     * @return array
     */
    public function getMetadata()
    {
        $c = get_defined_constants(true);
        $md = [];

        /* Create a copy of dbMD here and create a "filepath" key inside of
         * it. The reason we do this here, instead of creating this key inside
         * dbMD is because "filepath" isn't really metadata, and we don't want
         * filepath updated everytime the metadata changes. Also it needs extra
         * processing before we can write it to the database (needs to be split
         * into base and relative path)
         *  */
        $dbmd_copy = $this->_dbMD;
        $dbmd_copy['filepath'] = 'DbFilepath';

        foreach ($c['user'] as $constant => $value) {
            if (preg_match('/^MDATA_KEY/', $constant)) {
                if (isset($dbmd_copy[$value])) {
                    $propelColumn = $dbmd_copy[$value];
                    $method = "get{$propelColumn}";
                    $md[$constant] = $this->_file->{$method}();
                }
            }
        }

        return $md;
    }

    /**
     * Returns an array of playlist objects that this file is a part of.
     *
     * @return array
     */
    public function getPlaylists()
    {
        $con = Propel::getConnection();

        $sql = <<<'SQL'
SELECT playlist_id
FROM cc_playlist
WHERE file_id = :file_id
SQL;

        $stmt = $con->prepare($sql);
        $stmt->bindParam(':file_id', $this->id, PDO::PARAM_INT);

        if ($stmt->execute()) {
            $ids = $stmt->fetchAll();
        } else {
            $msg = implode(',', $stmt->errorInfo());

            throw new Exception("Error: {$msg}");
        }

        if (is_array($ids) && count($ids) > 0) {
            return array_map(function ($id) {
                return Application_Model_Playlist::RecallById($id);
            }, $ids);
        } else {
            return [];
        }
    }

    /**
     * Check if the file (on disk) corresponding to this class exists or not.
     *
     * @return bool true if the file exists, false otherwise
     */
    public function existsOnDisk()
    {
        $exists = false;

        try {
            $filePaths = $this->getFilePaths();
            $filePath = $filePaths[0];
            $exists = (file_exists($filePath) && !is_dir($filePath));
        } catch (Exception $e) {
            return false;
        }

        return $exists;
    }

    /**
     * Deletes the physical file from the local file system.
     *
     * @param mixed $quiet
     */
    public function delete($quiet = false)
    {
        // Check if the file is scheduled to be played in the future
        if (Application_Model_Schedule::IsFileScheduledInTheFuture($this->_file->getCcFileId())) {
            throw new DeleteScheduledFileException();
        }
        // RASTATIME 2026-10-18 - "Repeat of show": the last aired content of a
        // source show is still needed by an unfilled repeat (cc_schedule rows
        // cascade on delete, the copy would lose the track)
        $needed = Application_Service_RepeatFillService::neededByPendingRepeat($this->_file->getCcFileId());
        if ($needed !== null) {
            throw new DeleteScheduledFileException(Application_Service_RepeatFillService::neededMessage($needed));
        }

        // if we get here from the REST API, there's no valid user. APIKEY is validated already.
        if ($userInfo = Zend_Auth::getInstance()->getStorage()->read()) {
            // This call will throw "Trying to get property 'id' of non-object"
            $user = new Application_Model_User($userInfo->id);
            $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);
            if (!$isAdminOrPM && $this->getFileOwnerId() != $user->getId()) {
                throw new FileNoPermissionException();
            }
            $file_id = $this->_file->getDbId();
            Logging::info($file_id);
            Logging::info('User ' . $user->getLogin() . ' is deleting file: ' . $this->_file->getDbTrackTitle() . ' - file id: ' . $file_id);
        } else {
            Logging::info('API Auth is deleting file: ' . $this->_file->getDbTrackTitle() . ' - file id: ' . $this->_file->getDbId());
        }
        $filesize = $this->_file->getFileSize();
        if ($filesize < 0) {
            throw new Exception('Cannot delete file with filesize ' . $filesize);
        }

        // Delete the physical file from either the local stor directory
        if ($this->_file->getDbImportStatus() == CcFiles::IMPORT_STATUS_SUCCESS) {
            try {
                $this->_file->deletePhysicalFile();
            } catch (Exception $e) {
                if ($quiet) {
                    Logging::info($e);
                } else {
                    // Just log the exception and continue.
                    Logging::error($e);
                }
            }
        }

        // Update the user's disk usage
        Application_Model_Preference::updateDiskUsage(-1 * $filesize);

        // Explicitly update any playlist's and block's length that contain
        // the file getting deleted
        self::updateBlockAndPlaylistLength($this->_file->getDbId());

        // delete the file record from cc_files
        $this->_file->delete();
    }

    /*
     * This function is meant to be called when a file is getting
     * deleted from the library. It re-calculates the length of
     * all blocks and playlists that contained the deleted file.
     */
    private static function updateBlockAndPlaylistLength($fileId)
    {
        $plRows = CcPlaylistcontentsQuery::create()->filterByDbFileId($fileId)->find();
        foreach ($plRows as $row) {
            $pl = CcPlaylistQuery::create()->filterByDbId($row->getDbPlaylistId($fileId))->findOne();
            $pl->setDbLength($pl->computeDbLength(Propel::getConnection(CcPlaylistPeer::DATABASE_NAME)));
            $pl->save();
        }

        $blRows = CcBlockcontentsQuery::create()->filterByDbFileId($fileId)->find();
        foreach ($blRows as $row) {
            $bl = CcBlockQuery::create()->filterByDbId($row->getDbBlockId())->findOne();
            $bl->setDbLength($bl->computeDbLength(Propel::getConnection(CcBlockPeer::DATABASE_NAME)));
            $bl->save();
        }
    }

    /**
     * This function is for when media monitor detects deletion of file
     * and trying to update airtime side.
     *
     * @param mixed $deleteFromPlaylist
     */
    public function deleteByMediaMonitor($deleteFromPlaylist = false)
    {
        if ($deleteFromPlaylist) {
            Application_Model_Playlist::DeleteFileFromAllPlaylists($this->getId());
        }
        // set file_exists flag to false
        $this->_file->setDbFileExists(false);
        $this->_file->save();
    }

    /**
     * Get the absolute filepath.
     *
     * @return array of strings
     */
    public function getFilePaths()
    {
        assert($this->_file);

        return $this->_file->getURLsForTrackPreviewOrDownload();
    }

    /**
     * Set real filename of raw media data.
     *
     * @param mixed $p_filepath
     *
     * @return string
     */
    public function setFilePath($p_filepath)
    {
        $path_info = Application_Common_Storage::splitFilePath($p_filepath);

        if (is_null($path_info)) {
            return -1;
        }
        $this->_file->setDbFilepath($path_info[1]);
        $this->_file->save($this->_con);
    }

    /**
     * Get the URL to access this file.
     */
    public function getFileUrl()
    {
        return $this->getRelativeFileUrl(Config::getPublicUrl());
    }

    /**
     * Sometimes we want a relative URL and not a full URL. See bug
     * https://dev.sourcefabric.org/browse/CC-2403.
     *
     * @param mixed $baseUrl
     */
    public function getRelativeFileUrl($baseUrl)
    {
        return $baseUrl . 'api/get-media/file/' . $this->getId();
    }

    public function getResourceId()
    {
        return $this->_file->getResourceId();
    }

    public function getFileSize()
    {
        $filesize = $this->_file->getFileSize();

        // It's OK for the file size to be zero. Pypo will make a request to Airtime and update
        // the file size and md5 hash if they are not set.
        if ($filesize < 0) {
            throw new Exception('Could not determine filesize for file id: ' . $this->_file->getDbId() . '. Filesize: ' . $filesize);
        }

        return $filesize;
    }

    public static function Insert($md, $con)
    {
        // save some work by checking if filepath is given right away
        if (!isset($md['MDATA_KEY_FILEPATH'])) {
            return null;
        }

        $file = new CcFiles();
        $now = new DateTime('now', new DateTimeZone('UTC'));
        $file->setDbUtime($now);
        $file->setDbMtime($now);

        $storedFile = new Application_Model_StoredFile($file, $con);

        // removed "//" in the path. Always use '/' for path separator
        // TODO : it might be better to just call OsPath::normpath on the file
        // path. Also note that mediamonitor normalizes the paths anyway
        // before passing them to php so it's not necessary to do this at all

        $filepath = str_replace('//', '/', $md['MDATA_KEY_FILEPATH']);
        $res = $storedFile->setFilePath($filepath);
        if ($res === -1) {
            return null;
        }
        $storedFile->setMetadata($md);

        return $storedFile;
    }

    /* TODO: Callers of this function should use a Propel transaction. Start
     * by creating $con outside the function with beingTransaction() */
    /**
     * @param int $p_id
     * @param Propel Connection
     * @param null|mixed $con
     *
     * @return Application_Model_StoredFile
     *
     * @throws Exception
     */
    public static function RecallById($p_id = null, $con = null)
    {
        // TODO
        if (is_null($con)) {
            $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        }

        if (isset($p_id)) {
            $p_id = intval($p_id);

            $storedFile = CcFilesQuery::create()->findPK($p_id, $con);
            if (is_null($storedFile)) {
                throw new Exception('Could not recall file with id: ' . $p_id);
            }

            return self::createWithFile($storedFile, $con);
        }

        throw new Exception('No arguments passed to RecallById');
    }

    public function getName()
    {
        return $this->_file->getFilename();
    }

    /**
     * Fetch the Application_Model_StoredFile by looking up its filepath.
     *
     * @param string $p_filepath path of file stored in Airtime
     * @param mixed  $con
     *
     * @return null|Application_Model_StoredFile
     */
    public static function RecallByFilepath($p_filepath, $con)
    {
        $path_info = Application_Common_Storage::splitFilePath($p_filepath);

        if (is_null($path_info)) {
            return null;
        }

        $file = CcFilesQuery::create()
            ->filterByDbFilepath($path_info[1])
            ->findOne($con);

        return is_null($file) ? null : self::createWithFile($file, $con);
    }

    public static function RecallByPartialFilepath($partial_path, $con)
    {
        $path_info = Application_Common_Storage::splitFilePath($partial_path);

        if (is_null($path_info)) {
            return null;
        }

        $files = CcFilesQuery::create()
            ->filterByDbFilepath("{$path_info[1]}%")
            ->find($con);
        $res = [];
        foreach ($files as $file) {
            $storedFile = new Application_Model_StoredFile($file, $con);
            $res[] = $storedFile;
        }

        return $res;
    }

    public static function getLibraryColumns()
    {
        return [
            'id', 'track_title', 'artist_name', 'album_title',
            'genre', 'length', 'year', 'utime', 'mtime', 'ftype',
            'track_number', 'mood', 'bpm', 'composer', 'info_url',
            'bit_rate', 'sample_rate', 'isrc_number', 'encoded_by', 'label',
            'copyright', 'mime', 'language', 'filepath', 'owner_id',
            'conductor', 'replay_gain', 'lptime', 'is_playlist', 'is_scheduled',
            'cuein', 'cueout', 'description', 'artwork', 'track_type_id',
            // RASTATIME 2026-05-16 - Track Expiry feature columns.
            'expires_at', 'disabled',
            // RASTATIME 2026-10-07 - times aired (rows of cc_playout_history)
            'play_count',
            // RASTATIME 2026-10-16 - "Show name (type)" of a teaser jingle
            'teaser',
        ];
    }

    public static function searchLibraryFiles($datatables)
    {
        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);

        $displayColumns = self::getLibraryColumns();

        $plSelect = [];
        $blSelect = [];
        $fileSelect = [];
        $streamSelect = [];
        foreach ($displayColumns as $key) {
            if ($key === 'id') {
                $plSelect[] = 'PL.id AS ' . $key;
                $blSelect[] = 'BL.id AS ' . $key;
                $fileSelect[] = "FILES.id AS {$key}";
                $streamSelect[] = 'ws.id AS ' . $key;
            } elseif ($key === 'track_title') {
                $plSelect[] = 'name AS ' . $key;
                $blSelect[] = 'name AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'name AS ' . $key;
            } elseif ($key === 'ftype') {
                $plSelect[] = "'playlist'::varchar AS " . $key;
                $blSelect[] = "'block'::varchar AS " . $key;
                // RASTATIME: Default to 'audioclip' when analyzer hasn't
                // populated ftype yet (empty-string DB default).
                $fileSelect[] = "COALESCE(NULLIF(FILES.{$key}, ''), 'audioclip') AS {$key}";
                $streamSelect[] = "'stream'::varchar AS " . $key;
            } elseif ($key === 'artist_name') {
                $plSelect[] = 'login AS ' . $key;
                $blSelect[] = 'login AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'login AS ' . $key;
            } elseif ($key === 'owner_id') {
                $plSelect[] = 'login AS ' . $key;
                $blSelect[] = 'login AS ' . $key;
                $fileSelect[] = "sub.login AS {$key}";
                $streamSelect[] = 'login AS ' . $key;
            } elseif ($key === 'replay_gain') {
                $plSelect[] = 'NULL::NUMERIC AS ' . $key;
                $blSelect[] = 'NULL::NUMERIC AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::NUMERIC AS ' . $key;
            } elseif ($key === 'lptime') {
                $plSelect[] = 'NULL::TIMESTAMP AS ' . $key;
                $blSelect[] = 'NULL::TIMESTAMP AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = $key;
            } elseif ($key === 'play_count') {
                // RASTATIME 2026-10-07 - how often the file aired: one row of
                // cc_playout_history per aired schedule row (the same number
                // the Playout History "File Summary" shows), joined grouped
                // in $fileTable below.  Streams and line-ins are logged
                // there too, but without a reference to their library item.
                $plSelect[] = 'NULL::int AS ' . $key;
                $blSelect[] = 'NULL::int AS ' . $key;
                $fileSelect[] = 'COALESCE(ph.play_count, 0)::int AS ' . $key;
                $streamSelect[] = 'NULL::int AS ' . $key;
            } elseif ($key === 'teaser') {
                // RASTATIME 2026-10-16 - teaser link as searchable text:
                // "Show name (today)"; NULL for everything that is no teaser
                $plSelect[] = 'NULL::text AS ' . $key;
                $blSelect[] = 'NULL::text AS ' . $key;
                // scalar subquery, not a JOIN: cc_show has genre / description
                // columns too and the file branch selects those bare
                $fileSelect[] = self::teaserColumnsReady($con)
                    ? "((SELECT string_agg(ts.name, ', ' ORDER BY ts.name) FROM cc_file_teaser ft JOIN cc_show ts ON ts.id = ft.show_id WHERE ft.file_id = FILES.id)"
                      . " || CASE WHEN FILES.teaser_type IN ('today', 'tomorrow') THEN ' Â· ' || FILES.teaser_type ELSE '' END)::text AS " . $key
                    : 'NULL::text AS ' . $key;
                $streamSelect[] = 'NULL::text AS ' . $key;
            } elseif ($key === 'is_scheduled' || $key === 'is_playlist') {
                $plSelect[] = 'NULL::boolean AS ' . $key;
                $blSelect[] = 'NULL::boolean AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::boolean AS ' . $key;
            } elseif ($key === 'cuein' || $key === 'cueout') {
                $plSelect[] = 'NULL::INTERVAL AS ' . $key;
                $blSelect[] = 'NULL::INTERVAL AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::INTERVAL AS ' . $key;
            }
            // file length is displayed based on cueout - cuein.
            elseif ($key === 'length') {
                $plSelect[] = $key;
                $blSelect[] = $key;
                $fileSelect[] = '(cueout - cuein)::INTERVAL AS length';
                $streamSelect[] = $key;
            }
            // same columns in each table.
            elseif (in_array($key, ['utime', 'mtime'])) {
                $plSelect[] = $key;
                $blSelect[] = $key;
                $fileSelect[] = $key;
                $streamSelect[] = $key;
            } elseif ($key === 'year') {
                $plSelect[] = 'EXTRACT(YEAR FROM utime)::varchar AS ' . $key;
                $blSelect[] = 'EXTRACT(YEAR FROM utime)::varchar AS ' . $key;
                $fileSelect[] = 'year AS ' . $key;
                $streamSelect[] = 'EXTRACT(YEAR FROM utime)::varchar AS ' . $key;
            }
            // need to cast certain data as ints for the union to search on.
            elseif (in_array($key, ['track_number', 'bit_rate', 'sample_rate', 'bpm', 'track_type_id'])) {
                $plSelect[] = 'NULL::int AS ' . $key;
                $blSelect[] = 'NULL::int AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::int AS ' . $key;
            } elseif ($key === 'filepath') {
                $plSelect[] = 'NULL::VARCHAR AS ' . $key;
                $blSelect[] = 'NULL::VARCHAR AS ' . $key;
                $fileSelect[] = "reverse(split_part(reverse({$key}), '/', 1)) as {$key}";
                $streamSelect[] = 'url AS ' . $key;
            } elseif ($key == 'mime') {
                $plSelect[] = 'NULL::VARCHAR AS ' . $key;
                $blSelect[] = 'NULL::VARCHAR AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = $key;
            } elseif ($key === 'expires_at') {
                // RASTATIME 2026-05-31: expires_at is a TIMESTAMP in cc_files.
                // The other UNION branches previously fell through to the
                // generic 'NULL::text' else branch below, producing
                // "UNION types text and timestamp cannot be matched" — a 500 on
                // Library/contents-feed. Cast the NULL to TIMESTAMP to match.
                $plSelect[] = 'NULL::TIMESTAMP AS ' . $key;
                $blSelect[] = 'NULL::TIMESTAMP AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::TIMESTAMP AS ' . $key;
            } elseif ($key === 'disabled') {
                // RASTATIME 2026-05-31: disabled is BOOLEAN in cc_files — same
                // UNION-type fix as expires_at above (was NULL::text via else).
                $plSelect[] = 'NULL::boolean AS ' . $key;
                $blSelect[] = 'NULL::boolean AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::boolean AS ' . $key;
            } else {
                $plSelect[] = 'NULL::text AS ' . $key;
                $blSelect[] = 'NULL::text AS ' . $key;
                $fileSelect[] = $key;
                $streamSelect[] = 'NULL::text AS ' . $key;
            }
        }

        $plSelect = 'SELECT ' . implode(',', $plSelect);
        $blSelect = 'SELECT ' . implode(',', $blSelect);
        $fileSelect = 'SELECT ' . implode(',', $fileSelect);
        $streamSelect = 'SELECT ' . implode(',', $streamSelect);

        // RASTATIME 2026-05-12 — Line-In Library UNION.
        //
        // rastatime_linein uses ``created_at`` / ``updated_at`` (Django
        // convention) rather than the Propel ``utime`` / ``mtime`` of
        // the cc_* tables, and has no FK to cc_subjs for "owner".  So
        // it can't share the generic foreach mapping above — we build
        // its SELECT clause here with explicit per-column aliases.
        //
        // Disabled rows are filtered out so they don't appear as
        // schedulable Library entries.
        $lineinSelect = [];
        foreach ($displayColumns as $key) {
            switch ($key) {
                case 'id':
                    $lineinSelect[] = 'li.id AS id';
                    break;
                case 'track_title':
                    $lineinSelect[] = 'li.name AS track_title';
                    break;
                case 'ftype':
                    $lineinSelect[] = "'linein'::varchar AS ftype";
                    break;
                case 'length':
                    // Default 30 min if the operator left "Default Length" empty.
                    $lineinSelect[] = "COALESCE(li.length, INTERVAL '30 minutes') AS length";
                    break;
                case 'utime':
                    $lineinSelect[] = 'li.created_at AS utime';
                    break;
                case 'mtime':
                    $lineinSelect[] = 'li.updated_at AS mtime';
                    break;
                case 'year':
                    $lineinSelect[] = "EXTRACT(YEAR FROM li.created_at)::varchar AS year";
                    break;
                case 'description':
                    $lineinSelect[] = 'li.description AS description';
                    break;
                case 'filepath':
                    // No file path; show the device-stable-ID so an
                    // operator can identify which input this line-in
                    // refers to at a glance.
                    $lineinSelect[] = 'li.device_id AS filepath';
                    break;
                case 'artist_name':
                case 'owner_id':
                    $lineinSelect[] = "''::varchar AS {$key}";
                    break;
                case 'replay_gain':
                    $lineinSelect[] = "NULL::NUMERIC AS {$key}";
                    break;
                case 'lptime':
                    $lineinSelect[] = "NULL::TIMESTAMP AS {$key}";
                    break;
                case 'is_playlist':
                case 'is_scheduled':
                    $lineinSelect[] = "NULL::boolean AS {$key}";
                    break;
                case 'cuein':
                case 'cueout':
                    $lineinSelect[] = "NULL::INTERVAL AS {$key}";
                    break;
                case 'track_number':
                case 'bit_rate':
                case 'sample_rate':
                case 'bpm':
                case 'track_type_id':
                    $lineinSelect[] = "NULL::int AS {$key}";
                    break;
                case 'mime':
                    $lineinSelect[] = "NULL::VARCHAR AS {$key}";
                    break;
                case 'expires_at':
                    // RASTATIME 2026-05-31: match cc_files.expires_at TIMESTAMP
                    // type across the UNION (see searchLibraryFiles fix).
                    $lineinSelect[] = "NULL::TIMESTAMP AS {$key}";
                    break;
                case 'disabled':
                    $lineinSelect[] = "NULL::boolean AS {$key}";
                    break;
                case 'play_count':
                    $lineinSelect[] = "NULL::int AS {$key}";
                    break;
                default:
                    $lineinSelect[] = "NULL::text AS {$key}";
                    break;
            }
        }
        $lineinSelect = 'SELECT ' . implode(',', $lineinSelect);

        $type = intval($datatables['type']);

        $plTable = "({$plSelect} FROM cc_playlist AS PL LEFT JOIN cc_subjs AS sub ON (sub.id = PL.creator_id))";
        $blTable = "({$blSelect} FROM cc_block AS BL LEFT JOIN cc_subjs AS sub ON (sub.id = BL.creator_id))";
        // RASTATIME 2026-10-07 - play_count: one grouped pass over the playout history per query
        $playCountJoin = 'LEFT JOIN (SELECT file_id, COUNT(*) AS play_count FROM cc_playout_history WHERE file_id IS NOT NULL GROUP BY file_id) AS ph ON (ph.file_id = FILES.id)';
        $fileTable = "({$fileSelect} FROM cc_files AS FILES LEFT JOIN cc_subjs AS sub ON (sub.id = FILES.owner_id) {$playCountJoin} WHERE file_exists = 'TRUE' AND hidden='FALSE')";
        // $fileTable = "({$fileSelect} FROM cc_files AS FILES WHERE file_exists = 'TRUE')";
        $streamTable = "({$streamSelect} FROM cc_webstream AS ws LEFT JOIN cc_subjs AS sub ON (sub.id = ws.creator_id))";
        $lineinTable = "({$lineinSelect} FROM rastatime_linein AS li WHERE li.enabled = TRUE)";
        $unionTable = "({$plTable} UNION {$blTable} UNION {$fileTable} UNION {$streamTable} UNION {$lineinTable}) AS RESULTS";

        // choose which table we need to select data from.
        switch ($type) {
            case MediaType::FILE:
                $fromTable = $fileTable . ' AS File'; // need an alias for the table if it's standalone.

                break;

            case MediaType::PLAYLIST:
                $fromTable = $plTable . ' AS Playlist'; // need an alias for the table if it's standalone.

                break;

            case MediaType::BLOCK:
                $fromTable = $blTable . ' AS Block'; // need an alias for the table if it's standalone.

                break;

            case MediaType::WEBSTREAM:
                $fromTable = $streamTable . ' AS StreamTable'; // need an alias for the table if it's standalone.

                break;

            case MediaType::LINEIN:
                // RASTATIME 2026-05-12 — Line-In Library filter.
                $fromTable = $lineinTable . ' AS LineinTable';

                break;

            default:
                $fromTable = $unionTable;
        }

        // update is_scheduled to false for tracks that
        // have already played out
        self::updatePastFilesIsScheduled();
        $results = Application_Model_Datatables::findEntries($con, $displayColumns, $fromTable, $datatables);

        $displayTimezone = new DateTimeZone(Application_Model_Preference::GetUserTimezone());
        $utcTimezone = new DateTimeZone('UTC');

        $fp = Application_Common_Storage::root();

        foreach ($results['aaData'] as &$row) {
            $row['id'] = intval($row['id']);

            // RASTATIME 2026-05-15 — fix copy-paste typo: this block
            // used ``$r`` (which is undefined in this scope) instead of
            // ``$row`` (the loop's reference variable).  Result: the
            // recompute-on-fetch path for playlist length and block
            // bl_type was silently skipped for every row, leaving the
            // library DataTables response with stale ``cc_playlist.length``
            // / ``cc_block.length`` DB values and a missing ``bl_type``
            // field on Smart-Block rows.
            //
            // Symptom that surfaced this bug: the dashboard's playlist
            // row context menu's "Preview" item silently did nothing,
            // because ``data.length`` then got formatted as ``"0.0"``
            // (LengthFormatter on "00:00:00") and the JS preview
            // callback's ``data.length !== "0.0"`` check returned false.
            //
            // taken from Datatables.php, needs to be cleaned up there.
            if (isset($row['ftype'])) {
                if ($row['ftype'] == 'playlist') {
                    $pl = new Application_Model_Playlist($row['id']);
                    $row['length'] = $pl->getLength();
                } elseif ($row['ftype'] == 'block') {
                    $bl = new Application_Model_Block($row['id']);
                    $row['bl_type'] = $bl->isStatic() ? 'static' : 'dynamic';
                    $row['length'] = $bl->getLength();
                }
            }

            if ($row['ftype'] === 'audioclip') {
                $cuein_formatter = new LengthFormatter($row['cuein']);
                $row['cuein'] = $cuein_formatter->format();

                $cueout_formatter = new LengthFormatter($row['cueout']);
                $row['cueout'] = $cueout_formatter->format();

                $cuein = Application_Common_DateHelper::playlistTimeToSeconds($row['cuein']);
                $cueout = Application_Common_DateHelper::playlistTimeToSeconds($row['cueout']);
                $row_length = Application_Common_DateHelper::secondsToPlaylistTime($cueout - $cuein);

                $formatter = new SamplerateFormatter($row['sample_rate']);
                $row['sample_rate'] = $formatter->format();

                $formatter = new BitrateFormatter($row['bit_rate']);
                $row['bit_rate'] = $formatter->format();

                $get_artwork = FileDataHelper::getArtworkData($row['artwork'], 32, $fp);
                $row['artwork_data'] = $get_artwork;

                // for audio preview
                $row['audioFile'] = $row['id'] . '.' . pathinfo($row['filepath'], PATHINFO_EXTENSION);
            } else {
                $row['audioFile'] = $row['id'];
                $row_length = $row['length'];
            }

            $len_formatter = new LengthFormatter($row_length);
            $row['length'] = $len_formatter->format();

            // convert mtime and utime to localtime
            $row['mtime'] = new DateTime($row['mtime'], $utcTimezone);
            $row['mtime']->setTimeZone($displayTimezone);
            $row['mtime'] = $row['mtime']->format(DEFAULT_TIMESTAMP_FORMAT);
            $row['utime'] = new DateTime($row['utime'], $utcTimezone);
            $row['utime']->setTimeZone($displayTimezone);
            $row['utime'] = $row['utime']->format(DEFAULT_TIMESTAMP_FORMAT);

            // need to convert last played to localtime if it exists.
            if (isset($row['lptime'])) {
                $row['lptime'] = new DateTime($row['lptime'], $utcTimezone);
                $row['lptime']->setTimeZone($displayTimezone);
                $row['lptime'] = $row['lptime']->format(DEFAULT_TIMESTAMP_FORMAT);
            }

            // we need to initalize the checkbox and image row because we do not retrieve
            // any data from the db for these and datatables will complain
            $row['checkbox'] = '';
            $row['image'] = '';
            $row['options'] = '';

            $type = substr($row['ftype'], 0, 2);
            $row['tr_id'] = "{$type}_{$row['id']}";
        }

        return $results;
    }

    /**
     * Copy a newly uploaded audio file from its temporary upload directory
     * on the local disk (like /tmp) over to Airtime's "stor" directory,
     * which is where all ingested music/media live.
     *
     * This is done in PHP here on the web server rather than in libretime-analyzer because
     * the libretime-analyzer might be running on a different physical computer than the web server,
     * and it probably won't have access to the web server's /tmp folder. The stor/organize directory
     * is, however, both accessible to the machines running libretime-analyzer and the web server
     * on Airtime Pro.
     *
     * The file is actually copied to "stor/organize", which is a staging directory where files go
     * before they're processed by libretime-analyzer, which then moves them to "stor/imported" in the final
     * step.
     *
     * @param string $tempFilePath
     * @param string $originalFilename
     * @param bool   $copyFile         copy the file instead of moving it
     * @param mixed  $fileId
     * @param bool   $keepSourceOnFailure RASTATIME 2026-10-14 - never delete the source when the
     *                                    move fails (import folder: the file is the operator's)
     *
     * @return Ambigous <unknown, string>
     *
     * @throws Exception
     */
    public static function moveFileToStor($tempFilePath, $fileId, $originalFilename, $copyFile = false, $keepSourceOnFailure = false)
    {
        $audio_file = $tempFilePath;

        $stor = Application_Common_Storage::root();
        // check if "organize" dir exists and if not create one
        if (!file_exists($stor . '/organize')) {
            if (!mkdir($stor . '/organize', 0777)) {
                throw new Exception('Failed to create organize directory.');
            }
        }

        if (chmod($audio_file, 0644) === false) {
            Logging::info("Warning: couldn't change permissions of {$audio_file} to 0644");
        }

        // Did all the checks for real, now trying to copy
        $audio_stor = Application_Common_OsPath::join(
            $stor,
            'organize',
            $fileId . '-' . $originalFilename
        );
        // if the uploaded file is not UTF-8 encoded, let's encode it. Assuming source
        // encoding is ISO-8859-1
        $audio_stor = mb_detect_encoding($audio_stor, 'UTF-8') == 'UTF-8' ? $audio_stor : utf8_encode($audio_stor);
        if ($copyFile) {
            Logging::info("Copying file {$audio_file} to {$audio_stor}");
            if (@copy($audio_file, $audio_stor) === false) {
                throw new Exception("Failed to copy {$audio_file} to {$audio_stor}");
            }
        } else {
            Logging::info("Moving file {$audio_file} to {$audio_stor}");

            // Ensure we have permissions to overwrite the file in stor, in case it already exists.
            if (file_exists($audio_stor)) {
                chmod($audio_stor, 0644);
            }

            // Martin K.: changed to rename: Much less load + quicker since this is
            // an atomic operation
            if (rename($audio_file, $audio_stor) === false) {
                // something went wrong likely there wasn't enough space in .
                // the audio_stor to move the file too warn the user that   .
                // the file wasn't uploaded and they should check if there  .
                // is enough disk space                                     .
                // RASTATIME 2026-10-14 - only an upload's temporary copy is
                // ours to remove; a file from the import folder stays, so
                // LocalImportScanTask can move it to _failed.
                if (!$keepSourceOnFailure) {
                    unlink($audio_file); // remove the file after failed rename
                }

                throw new Exception('The file was not uploaded, this error can occur if the computer '
                    . 'hard drive does not have enough disk space or the stor '
                    . 'directory does not have correct write permissions.');
            }
        }

        return $audio_stor;
    }

    // Pass the file through Liquidsoap and test if it is readable. Return True if readable, and False otherwise.
    public static function liquidsoapFilePlayabilityTest($audio_file)
    {
        $LIQUIDSOAP_ERRORS = ['TagLib: MPEG::Properties::read() -- Could not find a valid last MPEG frame in the stream.'];

        // Ask Liquidsoap if file is playable
        // CC-5990/5991 - Changed to point directly to liquidsoap, removed PATH export
        $command = sprintf(
            'liquidsoap -v -c "output.dummy(audio_to_stereo(single(%s)))" 2>&1',
            escapeshellarg($audio_file)
        );

        exec($command, $output, $rv);

        $isError = count($output) > 0 && in_array($output[0], $LIQUIDSOAP_ERRORS);

        Logging::info('Is error?! : ' . $isError);
        Logging::info('ls playability response: ' . $rv);

        return $rv == 0 && !$isError;
    }

    public static function getFileCount()
    {
        $sql = 'SELECT count(*) as cnt FROM cc_files WHERE file_exists';

        return Application_Common_Database::prepareAndExecute(
            $sql,
            [],
            Application_Common_Database::COLUMN
        );
    }

    /**
     * Enter description here ...
     *
     * @param       $dir_id - if this is not provided, it returns all files with full
     *                     path constructed
     * @param mixed $all
     */
    public static function listAllFiles($dir_id = null, $all = true)
    {
        $con = Propel::getConnection();

        $sql = <<<'SQL'
SELECT filepath AS fp
FROM CC_FILES AS f
WHERE f.directory = :dir_id
SQL;

        if (!$all) {
            $sql .= " AND f.file_exists = 'TRUE'";
        }

        $stmt = $con->prepare($sql);
        $stmt->bindParam(':dir_id', $dir_id);

        if ($stmt->execute()) {
            $rows = $stmt->fetchAll();
        } else {
            $msg = implode(',', $stmt->errorInfo());

            throw new Exception("Error: {$msg}");
        }

        $results = [];
        foreach ($rows as $row) {
            $results[] = $row['fp'];
        }

        return $results;
    }

    // TODO: MERGE THIS FUNCTION AND "listAllFiles" -MK
    public static function listAllFiles2($dir_id = null, $limit = 'ALL')
    {
        $con = Propel::getConnection();

        $sql = <<<'SQL'
SELECT id,
       filepath AS fp
FROM cc_files
WHERE directory = :dir_id
  AND file_exists = 'TRUE'
  AND replay_gain IS NULL LIMIT :lim
SQL;

        $stmt = $con->prepare($sql);
        $stmt->bindParam(':dir_id', $dir_id);
        $stmt->bindParam(':lim', $limit);

        if ($stmt->execute()) {
            $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        } else {
            $msg = implode(',', $stmt->errorInfo());

            throw new Exception("Error: {$msg}");
        }

        return $rows;
    }

    public static function getAllFilesWithoutSilan()
    {
        $con = Propel::getConnection();

        $sql = <<<'SQL'
SELECT f.id,
       m.directory || f.filepath AS fp
FROM cc_files as f
JOIN cc_music_dirs as m ON f.directory = m.id
WHERE file_exists = 'TRUE'
  AND silan_check IS FALSE Limit 100
SQL;
        $stmt = $con->prepare($sql);

        if ($stmt->execute()) {
            $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        } else {
            $msg = implode(',', $stmt->errorInfo());

            throw new Exception("Error: {$msg}");
        }

        return $rows;
    }

    public function setFileExistsFlag($flag)
    {
        $this->_file->setDbFileExists($flag)
            ->save();
    }

    public function setFileHiddenFlag($flag)
    {
        $this->_file->setDbHidden($flag)
            ->save();
    }

    // This method seems to be unsued everywhere so I've commented it out
    // If it's absence does not have any effect then it will be completely
    // removed soon
    // public function getFileExistsFlag()
    // {
    // return $this->_file->getDbFileExists();
    // }

    public function getFileOwnerId()
    {
        return $this->_file->getDbOwnerId();
    }

    public static function setIsPlaylist($p_playlistItems, $p_type, $p_status)
    {
        foreach ($p_playlistItems as $item) {
            $file = self::RecallById($item->getDbFileId());
            $fileId = $file->_file->getDbId();
            if ($p_type == 'playlist') {
                // we have to check if the file is in another playlist before
                // we can update
                if (!is_null($fileId) && !in_array($fileId, Application_Model_Playlist::getAllPlaylistFiles())) {
                    $file->_file->setDbIsPlaylist($p_status)->save();
                }
            } elseif ($p_type == 'block') {
                if (!is_null($fileId) && !in_array($fileId, Application_Model_Block::getAllBlockFiles())) {
                    $file->_file->setDbIsPlaylist($p_status)->save();
                }
            }
        }
    }

    public static function setIsScheduled($fileId, $status)
    {
        $file = self::RecallById($fileId);
        $updateIsScheduled = false;

        if (!is_null($fileId) && !in_array(
            $fileId,
            Application_Model_Schedule::getAllFutureScheduledFiles()
        )) {
            $file->_file->setDbIsScheduled($status)->save();
            $updateIsScheduled = true;
        }

        return $updateIsScheduled;
    }

    /**
     * Updates the is_scheduled flag to false for tracks that are no longer
     * scheduled in the future. We do this by checking the difference between
     * all files scheduled in the future and all files with is_scheduled = true.
     * The difference of the two result sets is what we need to update.
     */
    public static function updatePastFilesIsScheduled()
    {
        $futureScheduledFilesSelectCriteria = new Criteria();
        $futureScheduledFilesSelectCriteria->addSelectColumn(CcSchedulePeer::FILE_ID);
        $futureScheduledFilesSelectCriteria->setDistinct();
        $futureScheduledFilesSelectCriteria->add(CcSchedulePeer::ENDS, gmdate(DEFAULT_TIMESTAMP_FORMAT), Criteria::GREATER_THAN);
        $stmt = CcSchedulePeer::doSelectStmt($futureScheduledFilesSelectCriteria);
        $filesScheduledInFuture = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);

        $filesCurrentlySetWithIsScheduledSelectCriteria = new Criteria();
        $filesCurrentlySetWithIsScheduledSelectCriteria->addSelectColumn(CcFilesPeer::ID);
        $filesCurrentlySetWithIsScheduledSelectCriteria->add(CcFilesPeer::IS_SCHEDULED, true);
        $stmt = CcFilesPeer::doSelectStmt($filesCurrentlySetWithIsScheduledSelectCriteria);
        $filesCurrentlySetWithIsScheduled = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);

        $diff = array_diff($filesCurrentlySetWithIsScheduled, $filesScheduledInFuture);

        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        $selectCriteria = new Criteria();
        $selectCriteria->add(CcFilesPeer::ID, $diff, Criteria::IN);
        $updateCriteria = new Criteria();
        $updateCriteria->add(CcFilesPeer::IS_SCHEDULED, false);
        BasePeer::doUpdate($selectCriteria, $updateCriteria, $con);
    }
}

class DeleteScheduledFileException extends Exception {}
class FileDoesNotExistException extends Exception {}
class FileNoPermissionException extends Exception {}
