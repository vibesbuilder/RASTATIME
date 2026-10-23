<?php

/**
 * @copyright 2010 Sourcefabric O.P.S.
 * @license https://www.gnu.org/licenses/gpl.txt
 */
class Application_Model_Block implements Application_Model_LibraryEditable
{
    /**
     * propel connection object.
     */
    private $con;

    /**
     * unique id for the block.
     */
    private $id;

    private $block;

    /**
     * info needed to insert a new block element.
     */
    private $blockItem = [
        'id' => '',
        'pos' => '',
        'cliplength' => '',
        'cuein' => '00:00:00',
        'cueout' => '00:00:00',
        'fadein' => '0.0',
        'fadeout' => '0.0',
        'crossfadeDuration' => 0,
    ];

    // using propel's phpNames.
    private $categories = [
        'dc:title' => 'Name',
        'dc:creator' => 'Creator',
        'dc:description' => 'Description',
        'dcterms:extent' => 'Length',
    ];

    private static $modifier2CriteriaMap = [
        CriteriaModifier::CONTAINS => Criteria::ILIKE,
        CriteriaModifier::DOES_NOT_CONTAIN => Criteria::NOT_ILIKE,
        CriteriaModifier::IS => Criteria::EQUAL,
        CriteriaModifier::IS_NOT => Criteria::NOT_EQUAL,
        CriteriaModifier::STARTS_WITH => Criteria::ILIKE,
        CriteriaModifier::ENDS_WITH => Criteria::ILIKE,
        CriteriaModifier::IS_GREATER_THAN => Criteria::GREATER_THAN,
        CriteriaModifier::IS_LESS_THAN => Criteria::LESS_THAN,
        CriteriaModifier::IS_IN_THE_RANGE => Criteria::CUSTOM,
        CriteriaModifier::BEFORE => Criteria::CUSTOM,
        CriteriaModifier::AFTER => Criteria::CUSTOM,
        CriteriaModifier::BETWEEN => Criteria::CUSTOM,
    ];

    public function __construct($id = null, $con = null)
    {
        if (isset($id)) {
            $this->block = CcBlockQuery::create()->findPk($id);

            if (is_null($this->block)) {
                throw new BlockNotFoundException();
            }
        } else {
            $this->block = new CcBlock();
            $this->block->setDbUTime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save();
        }

        $this->blockItem['fadein'] = Application_Model_Preference::GetDefaultFadeIn();
        $this->blockItem['fadeout'] = Application_Model_Preference::GetDefaultFadeOut();
        $this->blockItem['crossfadeDuration'] = Application_Model_Preference::GetDefaultCrossfadeDuration();

        $this->con = isset($con) ? $con : Propel::getConnection(CcBlockPeer::DATABASE_NAME);
        $this->id = $this->block->getDbId();
    }

    /**
     * Return local ID of virtual file.
     *
     * @return int
     */
    public function getId()
    {
        return $this->id;
    }

    /**
     * Rename stored virtual block.
     *
     * @param string $p_newname
     */
    public function setName($p_newname)
    {
        $this->block->setDbName($p_newname);
        $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
        $this->block->save($this->con);
    }

    /**
     * Get mnemonic block name.
     *
     * @return string
     */
    public function getName()
    {
        return $this->block->getDbName();
    }

    public function setDescription($p_description)
    {
        $this->block->setDbDescription($p_description);
        $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
        $this->block->save($this->con);
    }

    public function getDescription()
    {
        return $this->block->getDbDescription();
    }

    public function getCreator()
    {
        return $this->block->getCcSubjs()->getDbLogin();
    }

    public function getCreatorId()
    {
        return $this->block->getCcSubjs()->getDbId();
    }

    public function setCreator($p_id)
    {
        $this->block->setDbCreatorId($p_id);
        $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
        $this->block->save($this->con);
    }

    public function getLastModified($format = null)
    {
        return $this->block->getDbMtime($format);
    }

    public function getSize()
    {
        return $this->block->countCcBlockcontentss();
    }

    /**
     * Get the entire block as a two dimensional array, sorted in order of play.
     *
     * @param bool $filterFiles if this is true, it will only return files that has
     *                          file_exists flag set to true
     *
     * @return array
     */
    public function getContents($filterFiles = false)
    {
        $sql = <<<'SQL'
SELECT pc.id AS id,
       pc.position,
       pc.cliplength AS LENGTH,
       pc.cuein,
       pc.cueout,
       pc.fadein,
       pc.fadeout,
       pc.trackoffset,
       bl.type,
       f.LENGTH AS orig_length,
       f.id AS item_id,
       f.track_title,
       f.artist_name AS creator,
       f.file_exists AS EXISTS,
       f.filepath AS path,
       f.mime as mime
FROM cc_blockcontents AS pc
LEFT JOIN cc_files AS f ON pc.file_id=f.id
LEFT JOIN cc_block AS bl ON pc.block_id = bl.id
WHERE pc.block_id = :block_id

SQL;

        if ($filterFiles) {
            $sql .= <<<'SQL'
            AND f.file_exists = :file_exists
SQL;
        }
        $sql .= <<<'SQL'

ORDER BY pc.position
SQL;
        $params = [':block_id' => $this->id];
        if ($filterFiles) {
            $params[':file_exists'] = $filterFiles;
        }
        $rows = Application_Common_Database::prepareAndExecute($sql, $params);

        $offset = 0;
        foreach ($rows as &$row) {
            $clipSec = Application_Common_DateHelper::playlistTimeToSeconds($row['length']);

            $row['trackSec'] = $clipSec;

            $row['cueInSec'] = Application_Common_DateHelper::playlistTimeToSeconds($row['cuein']);
            $row['cueOutSec'] = Application_Common_DateHelper::playlistTimeToSeconds($row['cueout']);

            $trackoffset = $row['trackoffset'];
            $offset += $clipSec;
            $offset -= $trackoffset;
            $offset_cliplength = Application_Common_DateHelper::secondsToPlaylistTime($offset);

            // format the length for UI.
            $formatter = new LengthFormatter($row['length']);
            $row['length'] = $formatter->format();

            $formatter = new LengthFormatter($offset_cliplength);
            $row['offset'] = $formatter->format();

            // format the fades in format 00(.0)
            $fades = $this->getFadeInfo($row['position']);
            $row['fadein'] = $fades[0];
            $row['fadeout'] = $fades[1];

            // format the cues in format 00:00:00(.0)
            // we need to add the '.0' for cues and not fades
            // because propel takes care of this for us
            // (we use propel to fetch the fades)
            $row['cuein'] = str_pad(substr($row['cuein'], 0, 10), 10, '.0');
            $row['cueout'] = str_pad(substr($row['cueout'], 0, 10), 10, '.0');

            // format original length
            $formatter = new LengthFormatter($row['orig_length']);
            $row['orig_length'] = $formatter->format();

            // XSS exploit prevention
            $row['track_title'] = htmlspecialchars($row['track_title'] ?? '');
            $row['creator'] = htmlspecialchars($row['creator'] ?? '');
        }

        return $rows;
    }

    /**
     * The database stores fades in 00:00:00 Time format with optional millisecond resolution .000000
     * but this isn't practical since fades shouldn't be very long usually 1 second or less. This function
     * will normalize the fade so that it looks like 00.000000 to the user.
     *
     * @param mixed $fade
     */
    public function normalizeFade($fade)
    {
        // First get rid of the first six characters 00:00: which will be added back later for db update
        $fade = substr($fade, 6);

        // Second add .000000 if the fade does't have milliseconds format already
        $dbFadeStrPos = strpos($fade, '.');
        if ($dbFadeStrPos === false) {
            $fade .= '.000000';
        } else {
            while (strlen($fade) < 9) {
                $fade .= '0';
            }
        }

        // done, just need to set back the formated values
        return $fade;
    }

    public function getUnformatedLength()
    {
        $this->block->reload();
        if ($this->isStatic()) {
            $length = $this->block->getDbLength();
        } else {
            $length = $this->getDynamicBlockLength();
        }

        return $length;
    }

    public function getLength()
    {
        $this->block->reload();
        $prepend = '';
        if ($this->isStatic()) {
            $length = $this->block->getDbLength();
        } else {
            $length = $this->getDynamicBlockLength();
            if (!$this->hasItemLimit()) {
                $prepend = '~';
            }
        }
        $formatter = new LengthFormatter($length);

        return $prepend . $formatter->format();
    }

    public function getDynamicBlockLength()
    {
        [$value, $modifier] = $this->getLimitValueAndModifier();
        if ($modifier == 'items') {
            $length = $value . ' ' . _('items');
        } else {
            $hour = '00';
            $mins = '00';
            if ($modifier == 'minutes') {
                $mins = $value;
                if ($value > 59) {
                    $hour = intval($value / 60);
                    $mins = $value % 60;
                }
            } elseif ($modifier == 'hours') {
                $mins = $value * 60;
                if ($mins > 59) {
                    $hour = intval($mins / 60);
                    $hour = str_pad($hour, 2, '0', STR_PAD_LEFT);
                    $mins %= 60;
                }
            }
            $hour = str_pad($hour, 2, '0', STR_PAD_LEFT);
            $mins = str_pad($mins, 2, '0', STR_PAD_LEFT);
            $length = $hour . ':' . $mins . ':00';
        }

        return $length;
    }

    public function getLimitValueAndModifier()
    {
        $result = CcBlockcriteriaQuery::create()->filterByDbBlockId($this->id)
            ->filterByDbCriteria('limit')->findOne();
        if ($result) {
            $modifier = $result->getDbModifier();
            $value = $result->getDbValue();

            return [$value, $modifier];
        }
    }

    // this function returns sum of all track length under this block.
    public function getStaticLength()
    {
        $sql = <<<'SQL'
SELECT SUM(cliplength) AS LENGTH
FROM cc_blockcontents as bc
JOIN cc_files as f ON bc.file_id = f.id
WHERE block_id = :block_id
AND f.file_exists = true
SQL;
        $result = Application_Common_Database::prepareAndExecute($sql, [':block_id' => $this->id], 'all', PDO::FETCH_NUM);

        return $result[0][0];
    }

    private function insertBlockElement($info)
    {
        $row = new CcBlockcontents();
        $row->setDbBlockId($this->id);
        $row->setDbFileId($info['id']);
        $row->setDbPosition($info['pos']);
        $row->setDbCliplength($info['cliplength']);
        $row->setDbCuein($info['cuein']);
        $row->setDbCueout($info['cueout']);
        $row->setDbFadein(Application_Common_DateHelper::secondsToPlaylistTime($info['fadein']));
        $row->setDbFadeout(Application_Common_DateHelper::secondsToPlaylistTime($info['fadeout']));
        $row->setDbTrackOffset($info['crossfadeDuration']);
        $row->save($this->con);
        // above save result update on cc_block table on length column.
        // but $this->block doesn't get updated automatically
        // so we need to manually grab it again from DB so it has updated values
        // It is something to do FORMAT_ON_DEMAND( Lazy Loading )
        $this->block = CcBlockQuery::create()->findPK($this->id);
    }

    private function buildEntry($p_item, $pos)
    {
        $file = CcFilesQuery::create()->findPK($p_item, $this->con);

        if (isset($file) && $file->visible()) {
            $entry = $this->blockItem;
            $entry['id'] = $file->getDbId();
            $entry['pos'] = $pos;
            $entry['cueout'] = $file->getDbCueout();
            $entry['cuein'] = $file->getDbCuein();

            $cue_out = Application_Common_DateHelper::calculateLengthInSeconds($entry['cueout']);
            $cue_in = Application_Common_DateHelper::calculateLengthInSeconds($entry['cuein']);
            $entry['cliplength'] = Application_Common_DateHelper::secondsToPlaylistTime($cue_out - $cue_in);

            return $entry;
        }

        throw new Exception('trying to add a file that does not exist.');
    }

    public function isStatic()
    {
        return $this->block->getDbType() == 'static';
    }

    /*
     * @param array $p_items
    *     an array of audioclips to add to the block
    * @param int|null $p_afterItem
    *     item which to add the new items after in the block, null if added to the end.
    * @param string (before|after) $addAfter
    *      whether to add the clips before or after the selected item.
    */
    public function addAudioClips($p_items, $p_afterItem = null, $addType = 'after')
    {
        $this->con->beginTransaction();
        $contentsToUpdate = [];

        try {
            if (is_numeric($p_afterItem)) {
                Logging::info("Finding block content item {$p_afterItem}");

                $afterItem = CcBlockcontentsQuery::create()->findPK($p_afterItem);
                $index = $afterItem->getDbPosition();
                Logging::info("index is {$index}");
                $pos = ($addType == 'after') ? $index + 1 : $index;

                $contentsToUpdate = CcBlockcontentsQuery::create()
                    ->filterByDbBlockId($this->id)
                    ->filterByDbPosition($pos, Criteria::GREATER_EQUAL)
                    ->orderByDbPosition()
                    ->find($this->con);

                Logging::info('Adding to block');
                Logging::info("at position {$pos}");
            } else {
                // add to the end of the block
                if ($addType == 'after') {
                    $pos = $this->getSize();
                }
                // add to the beginning of the block.
                else {
                    $pos = 0;

                    $contentsToUpdate = CcBlockcontentsQuery::create()
                        ->filterByDbBlockId($this->id)
                        ->orderByDbPosition()
                        ->find($this->con);
                }

                $contentsToUpdate = CcBlockcontentsQuery::create()
                    ->filterByDbBlockId($this->id)
                    ->filterByDbPosition($pos, Criteria::GREATER_EQUAL)
                    ->orderByDbPosition()
                    ->find($this->con);

                Logging::info('Adding to block');
                Logging::info("at position {$pos}");
            }

            foreach ($p_items as $ac) {
                // Logging::info("Adding audio file {$ac[0]}");
                try {
                    if (is_array($ac) && $ac[1] == 'audioclip') {
                        $res = $this->insertBlockElement($this->buildEntry($ac[0], $pos));

                        // update is_playlist flag in cc_files to indicate the
                        // file belongs to a playlist or block (in this case a block)
                        $db_file = CcFilesQuery::create()->findPk($ac[0], $this->con);
                        $db_file->setDbIsPlaylist(true)->save($this->con);

                        ++$pos;
                    } elseif (!is_array($ac)) {
                        $res = $this->insertBlockElement($this->buildEntry($ac, $pos));
                        ++$pos;

                        $db_file = CcFilesQuery::create()->findPk($ac, $this->con);
                        $db_file->setDbIsPlaylist(true)->save($this->con);
                    }
                } catch (Exception $e) {
                    Logging::info($e->getMessage());
                }
            }

            // reset the positions of the remaining items.
            for ($i = 0; $i < count($contentsToUpdate); ++$i) {
                $contentsToUpdate[$i]->setDbPosition($pos);
                $contentsToUpdate[$i]->save($this->con);
                ++$pos;
            }

            $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save($this->con);

            $this->con->commit();

            $this->updateBlockLengthInAllPlaylist();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }
    }

    /**
     * Move audioClip to the new position in the block.
     *
     * @param array $p_items
     *                           array of unique ids of the selected items
     * @param int   $p_afterItem
     *                           unique id of the item to move the clip after
     */
    public function moveAudioClips($p_items, $p_afterItem = null)
    {
        $this->con->beginTransaction();

        try {
            $contentsToMove = CcBlockcontentsQuery::create()
                ->filterByDbId($p_items, Criteria::IN)
                ->orderByDbPosition()
                ->find($this->con);

            $otherContent = CcBlockcontentsQuery::create()
                ->filterByDbId($p_items, Criteria::NOT_IN)
                ->filterByDbBlockId($this->id)
                ->orderByDbPosition()
                ->find($this->con);

            $pos = 0;
            // moving items to beginning of the block.
            if (is_null($p_afterItem)) {
                Logging::info('moving items to beginning of block');

                foreach ($contentsToMove as $item) {
                    Logging::info("item {$item->getDbId()} to pos {$pos}");
                    $item->setDbPosition($pos);
                    $item->save($this->con);
                    ++$pos;
                }
                foreach ($otherContent as $item) {
                    Logging::info("item {$item->getDbId()} to pos {$pos}");
                    $item->setDbPosition($pos);
                    $item->save($this->con);
                    ++$pos;
                }
            } else {
                Logging::info("moving items after {$p_afterItem}");

                foreach ($otherContent as $item) {
                    Logging::info("item {$item->getDbId()} to pos {$pos}");
                    $item->setDbPosition($pos);
                    $item->save($this->con);
                    ++$pos;

                    if ($item->getDbId() == $p_afterItem) {
                        foreach ($contentsToMove as $move) {
                            Logging::info("item {$move->getDbId()} to pos {$pos}");
                            $move->setDbPosition($pos);
                            $move->save($this->con);
                            ++$pos;
                        }
                    }
                }
            }

            $this->con->commit();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }

        $this->block = CcBlockQuery::create()->findPK($this->id);
        $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
        $this->block->save($this->con);
    }

    /**
     * Remove audioClip from block.
     *
     * @param array $p_items
     *                       array of unique item ids to remove from the block..
     */
    public function delAudioClips($p_items)
    {
        $this->con->beginTransaction();

        try {
            // we need to get the file id of the item we are deleting
            // before the item gets deleted from the block
            $itemsToDelete = CcBlockcontentsQuery::create()
                ->filterByPrimaryKeys($p_items)
                ->filterByDbFileId(null, Criteria::NOT_EQUAL)
                ->find($this->con);

            CcBlockcontentsQuery::create()
                ->findPKs($p_items)
                ->delete($this->con);

            // now that the items have been deleted we can update the
            // is_playlist flag in cc_files
            Application_Model_StoredFile::setIsPlaylist($itemsToDelete, 'block', false);

            $contents = CcBlockcontentsQuery::create()
                ->filterByDbBlockId($this->id)
                ->orderByDbPosition()
                ->find($this->con);

            // reset the positions of the remaining items.
            for ($i = 0; $i < count($contents); ++$i) {
                $contents[$i]->setDbPosition($i);
                $contents[$i]->save($this->con);
            }

            $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save($this->con);

            $this->con->commit();

            $this->updateBlockLengthInAllPlaylist();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }
    }

    public function getFadeInfo($pos)
    {
        // Logging::info("Getting fade info for pos {$pos}");

        $row = CcBlockcontentsQuery::create()
            ->joinWith(CcFilesPeer::OM_CLASS)
            ->filterByDbBlockId($this->id)
            ->filterByDbPosition($pos)
            ->findOne();

        // Propel returns values in form 00.000000 format which is for only seconds.
        // We only want to display 1 decimal
        $fadeIn = substr($row->getDbFadein(), 0, 4);
        $fadeOut = substr($row->getDbFadeout(), 0, 4);

        return [$fadeIn, $fadeOut];
    }

    /*
     * create a crossfade from item in cc_playlist_contents with $id1 to item $id2.
    *
    * $fadeOut length of fade out in seconds if $id1
    * $fadeIn length of fade in in seconds of $id2
    * $offset time in seconds from end of $id1 that $id2 will begin to play.
    */
    public function createCrossfade($id1, $fadeOut, $id2, $fadeIn, $offset)
    {
        $this->con->beginTransaction();

        if (!isset($offset)) {
            $offset = Application_Model_Preference::GetDefaultCrossfadeDuration();
        }

        try {
            if (isset($id1)) {
                $this->changeFadeInfo($id1, null, $fadeOut);
            }
            if (isset($id2)) {
                $this->changeFadeInfo($id2, $fadeIn, null, $offset);
            }

            $this->con->commit();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }
    }

    /**
     * Change fadeIn and fadeOut values for block Element.
     *
     * @param string     $fadeIn
     *                            new value in ss.ssssss or extent format
     * @param string     $fadeOut
     *                            new value in ss.ssssss or extent format
     * @param mixed      $id
     * @param null|mixed $offset
     *
     * @return bool
     */
    public function changeFadeInfo($id, $fadeIn, $fadeOut, $offset = null)
    {
        // See issue CC-2065, pad the fadeIn and fadeOut so that it is TIME compatable with the DB schema
        // For the top level PlayList either fadeIn or fadeOut will sometimes be Null so need a gaurd against
        // setting it to nonNull for checks down below
        $fadeIn = $fadeIn ? '00:00:' . $fadeIn : $fadeIn;
        $fadeOut = $fadeOut ? '00:00:' . $fadeOut : $fadeOut;

        $this->con->beginTransaction();

        try {
            $row = CcBlockcontentsQuery::create()->findPK($id);

            if (is_null($row)) {
                throw new Exception('Block item does not exist.');
            }

            $clipLength = $row->getDbCliplength();

            if (!is_null($fadeIn)) {
                $sql = 'SELECT :fade_in::INTERVAL > :clip_length::INTERVAL';
                $params = [
                    ':fade_in' => $fadeIn,
                    ':clip_length' => $clipLength,
                ];

                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    // "Fade In can't be larger than overall playlength.";
                    $fadeIn = $clipLength;
                }
                $row->setDbFadein($fadeIn);

                if (!is_null($offset)) {
                    $row->setDbTrackOffset($offset);
                    Logging::info("Setting offset {$offset} on item {$id}");
                    $row->save($this->con);
                }
            }
            if (!is_null($fadeOut)) {
                $sql = 'SELECT :fade_out::INTERVAL > :clip_length::INTERVAL';
                $params = [
                    ':fade_out' => $fadeOut,
                    ':clip_length' => $clipLength,
                ];

                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    // "Fade Out can't be larger than overall playlength.";
                    $fadeOut = $clipLength;
                }
                $row->setDbFadeout($fadeOut);
            }

            $row->save($this->con);
            $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save($this->con);

            $this->con->commit();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }

        return ['fadeIn' => $fadeIn, 'fadeOut' => $fadeOut];
    }

    public function setfades($fadein, $fadeout)
    {
        if (isset($fadein)) {
            Logging::info("Setting block fade in {$fadein}");
            $row = CcBlockcontentsQuery::create()
                ->filterByDbBlockId($this->id)
                ->filterByDbPosition(0)
                ->findOne($this->con);

            $this->changeFadeInfo($row->getDbId(), $fadein, null);
        }

        if (isset($fadeout)) {
            Logging::info("Setting block fade out {$fadeout}");
            $row = CcBlockcontentsQuery::create()
                ->filterByDbBlockId($this->id)
                ->filterByDbPosition($this->getSize() - 1)
                ->findOne($this->con);

            $this->changeFadeInfo($row->getDbId(), null, $fadeout);
        }
    }

    /**
     * Change cueIn/cueOut values for block element.
     *
     * @param string $cueIn
     *                       new value in ss.ssssss or extent format
     * @param string $cueOut
     *                       new value in ss.ssssss or extent format
     * @param mixed  $id
     *
     * @return bool or pear error object
     */
    public function changeClipLength($id, $cueIn, $cueOut)
    {
        $this->con->beginTransaction();

        $errArray = [];

        try {
            if (is_null($cueIn) && is_null($cueOut)) {
                $errArray['error'] = _('Cue in and cue out are null.');

                return $errArray;
            }

            $row = CcBlockcontentsQuery::create()
                ->joinWith(CcFilesPeer::OM_CLASS)
                ->filterByPrimaryKey($id)
                ->findOne($this->con);

            if (is_null($row)) {
                throw new Exception('Block item does not exist.');
            }

            $oldCueIn = $row->getDBCuein();
            $oldCueOut = $row->getDbCueout();
            $fadeIn = $row->getDbFadein();
            $fadeOut = $row->getDbFadeout();

            $file = $row->getCcFiles($this->con);
            $origLength = $file->getDbLength();

            if (!is_null($cueIn) && !is_null($cueOut)) {
                if ($cueOut === '') {
                    $cueOut = $origLength;
                }

                $sql = 'SELECT :cue_out::INTERVAL > :orig_length::INTERVAL';
                $params = [
                    ':cue_out' => $cueOut,
                    ':orig_length' => $origLength,
                ];
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    $errArray['error'] = _("Can't set cue out to be greater than file length.");

                    return $errArray;
                }

                $sql = 'SELECT :cue_in::INTERVAL > :cue_out::INTERVAL';
                $params = [
                    ':cue_in' => $cueIn,
                    ':cue_out' => $cueOut,
                ];
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    $errArray['error'] = _("Can't set cue in to be larger than cue out.");

                    return $errArray;
                }

                $sql = 'SELECT :cue_out::INTERVAL - :cue_in::INTERVAL';
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                $cliplength = $result;

                $row->setDbCuein($cueIn);
                $row->setDbCueout($cueOut);
                $row->setDBCliplength($cliplength);
            } elseif (!is_null($cueIn)) {
                $sql = 'SELECT :cue_in::INTERVAL > :old_cue_out::INTERVAL';
                $params = [
                    ':cue_in' => $cueIn,
                    ':old_cue_out' => $oldCueOut,
                ];
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    $errArray['error'] = _("Can't set cue in to be larger than cue out.");

                    return $errArray;
                }

                $sql = 'SELECT :old_cue_out::INTERVAL - :cue_in::INTERVAL';
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                $cliplength = $result;

                $row->setDbCuein($cueIn);
                $row->setDBCliplength($cliplength);
            } elseif (!is_null($cueOut)) {
                if ($cueOut === '') {
                    $cueOut = $origLength;
                }

                $sql = 'SELECT :cue_out::INTERVAL > :orig_length::INTERVAL';
                $params = [
                    ':cue_out' => $cueOut,
                    ':orig_length' => $origLength,
                ];
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    $errArray['error'] = _("Can't set cue out to be greater than file length.");

                    return $errArray;
                }

                $sql = 'SELECT :cue_out::INTERVAL < :old_cue_in::INTERVAL';
                $params = [
                    ':cue_out' => $cueOut,
                    ':old_cue_in' => $oldCueIn,
                ];
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                if ($result) {
                    $errArray['error'] = _("Can't set cue out to be smaller than cue in.");

                    return $errArray;
                }

                $sql = 'SELECT :cue_out::INTERVAL - :old_cue_in::INTERVAL';
                $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
                $cliplength = $result;

                $row->setDbCueout($cueOut);
                $row->setDBCliplength($cliplength);
            }

            $cliplength = $row->getDbCliplength();

            $sql = 'SELECT :fade_in::INTERVAL > :clip_length::INTERVAL';
            $params = [
                ':fade_in' => $fadeIn,
                ':clip_length' => $cliplength,
            ];
            $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
            if ($result) {
                $fadeIn = $cliplength;
                $row->setDbFadein($fadeIn);
            }

            $sql = 'SELECT :fade_out::INTERVAL > :clip_length::INTERVAL';
            $params = [
                ':fade_out' => $fadeOut,
                ':clip_length' => $cliplength,
            ];
            $result = Application_Common_Database::prepareAndExecute($sql, $params, 'column');
            if ($result) {
                $fadeOut = $cliplength;
                $row->setDbFadein($fadeOut);
            }

            $row->save($this->con);
            $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save($this->con);

            $this->con->commit();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }

        return [
            'cliplength' => $cliplength, 'cueIn' => $cueIn, 'cueOut' => $cueOut, 'length' => $this->getUnformatedLength(),
            'fadeIn' => $fadeIn, 'fadeOut' => $fadeOut,
        ];
    }

    public function getAllPLMetaData()
    {
        $categories = $this->categories;
        $md = [];

        foreach ($categories as $key => $val) {
            $method = 'get' . $val;
            $md[$key] = $this->{$method}();
        }

        return $md;
    }

    public function getMetaData($category)
    {
        $cat = $this->categories[$category];
        $method = 'get' . $cat;

        return $this->{$method}();
    }

    public function setMetadata($category, $value)
    {
        $cat = $this->categories[$category];

        $method = 'set' . $cat;
        $this->{$method}($value);
    }

    public static function getBlockCount()
    {
        $sql = 'SELECT count(*) as cnt FROM cc_playlist';

        return Application_Common_Database::prepareAndExecute(
            $sql,
            [],
            Application_Common_Database::COLUMN
        );
    }

    /**
     * Delete the file from all blocks.
     *
     * @param string $p_fileId
     */
    public static function DeleteFileFromAllBlocks($p_fileId)
    {
        CcBlockcontentsQuery::create()->filterByDbFileId($p_fileId)->delete();
    }

    /**
     * Delete blocks that match the ids..
     *
     * @param array $p_ids
     * @param mixed $p_userId
     */
    public static function deleteBlocks($p_ids, $p_userId)
    {
        $userInfo = Zend_Auth::getInstance()->getStorage()->read();
        $user = new Application_Model_User($userInfo->id);
        $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);

        // get only the files from the blocks
        // we are about to delete
        $itemsToDelete = CcBlockcontentsQuery::create()
            ->filterByDbBlockId($p_ids)
            ->filterByDbFileId(null, Criteria::NOT_EQUAL)
            ->find();

        $updateIsPlaylistFlag = false;

        if (!$isAdminOrPM) {
            $leftOver = self::blocksNotOwnedByUser($p_ids, $p_userId);

            if (count($leftOver) == 0) {
                CcBlockQuery::create()->findPKs($p_ids)->delete();
                $updateIsPlaylistFlag = true;
            } else {
                throw new BlockNoPermissionException();
            }
        } else {
            CcBlockQuery::create()->findPKs($p_ids)->delete();
            $updateIsPlaylistFlag = true;
        }

        if ($updateIsPlaylistFlag) {
            // update is_playlist flag in cc_files
            Application_Model_StoredFile::setIsPlaylist(
                $itemsToDelete,
                'block',
                false
            );
        }
    }

    // This function returns that are not owen by $p_user_id among $p_ids
    private static function blocksNotOwnedByUser($p_ids, $p_userId)
    {
        $ownedByUser = CcBlockQuery::create()->filterByDbCreatorId($p_userId)->find()->getData();
        $selectedPls = $p_ids;
        $ownedPls = [];
        foreach ($ownedByUser as $pl) {
            if (in_array($pl->getDbId(), $selectedPls)) {
                $ownedPls[] = $pl->getDbId();
            }
        }

        return array_diff($selectedPls, $ownedPls);
    }

    /**
     * Delete all files from block.
     */
    public function deleteAllFilesFromBlock()
    {
        // RASTATIME 2026-10-14 - balanced transaction, as in
        // Playlist::deleteAllFilesFromPlaylist.  The method used to end with
        // a bare commit(), which inside a caller's transaction committed
        // that outer transaction early.
        $this->con->beginTransaction();

        try {
            // get only the files from the playlist
            // we are about to clear out
            $itemsToDelete = CcBlockcontentsQuery::create()
                ->filterByDbBlockId($this->id)
                ->filterByDbFileId(null, Criteria::NOT_EQUAL)
                ->find();

            CcBlockcontentsQuery::create()->findByDbBlockId($this->id)->delete();

            // update is_playlist flag in cc_files
            Application_Model_StoredFile::setIsPlaylist(
                $itemsToDelete,
                'block',
                false
            );

            // $this->block->reload();
            $this->block->setDbMtime(new DateTime('now', new DateTimeZone('UTC')));
            $this->block->save($this->con);
            $this->con->commit();
        } catch (Exception $e) {
            $this->con->rollback();

            throw $e;
        }
    }

    // smart block functions start
    public function shuffleSmartBlock()
    {
        // if it here that means it's static pl
        $this->saveType('static');
        $contents = CcBlockcontentsQuery::create()
            ->filterByDbBlockId($this->id)
            ->orderByDbPosition()
            ->find();
        $shuffledPos = range(0, count($contents) - 1);
        shuffle($shuffledPos);
        foreach ($contents as $item) {
            $item->setDbPosition(array_shift($shuffledPos));
            $item->save();
        }

        return ['result' => 0];
    }

    public function saveType($p_blockType)
    {
        // saving dynamic/static flag
        CcBlockQuery::create()->findPk($this->id)->setDbType($p_blockType)->save();
    }

    public function setLength($value)
    {
        $this->block->setDbLength($value);
        $this->block->save($this->con);
        $this->updateBlockLengthInAllPlaylist();
    }

    /**
     * Saves smart block criteria.
     *
     * @param array $p_criteria
     */
    public function saveSmartBlockCriteria($p_criteria)
    {
        $data = $this->organizeSmartPlaylistCriteria($p_criteria);

        // saving dynamic/static flag
        $blockType = $data['etc']['sp_type'] == 0 ? 'dynamic' : 'static';
        $this->saveType($blockType);
        $this->storeCriteriaIntoDb($data);

        // if the block is dynamic, put null to the length
        // as it cannot be calculated
        if ($blockType == 'dynamic') {
            if ($this->hasItemLimit()) {
                $this->setLength(null);
            } else {
                $this->setLength($this->getDynamicBlockLength());
            }
        } else {
            $length = $this->getStaticLength();
            if (!$length) {
                $length = '00:00:00';
            }
            $this->setLength($length);
        }

        $this->updateBlockLengthInAllPlaylist();
    }

    public function hasItemLimit()
    {
        [$value, $modifier] = $this->getLimitValueAndModifier();

        return $modifier == 'items';
    }

    public function storeCriteriaIntoDb($p_criteriaData)
    {
        // delete criteria under $p_blockId
        CcBlockcriteriaQuery::create()->findByDbBlockId($this->id)->delete();
        // Logging::info($p_criteriaData);
        // insert modifier rows
        if (isset($p_criteriaData['criteria'])) {
            $critKeys = array_keys($p_criteriaData['criteria']);
            for ($i = 0; $i < count($critKeys); ++$i) {
                // in order to maintain separation of different criteria to preserve AND statements for criteria
                // that might contradict itself we group them based upon their original position on the form
                $criteriaGroup = $i;
                foreach ($p_criteriaData['criteria'][$critKeys[$i]] as $d) {
                    $field = $d['sp_criteria_field'];
                    $value = $d['sp_criteria_value'];
                    $modifier = $d['sp_criteria_modifier'];
                    if (isset($d['sp_criteria_extra'])) {
                        $extra = $d['sp_criteria_extra'];
                    }
                    if (isset($d['sp_criteria_datetime_select'])) {
                        $datetimeunit = $d['sp_criteria_datetime_select'];
                    }
                    if (isset($d['sp_criteria_extra_datetime_select'])) {
                        $extradatetimeunit = $d['sp_criteria_extra_datetime_select'];
                    }

                    if ($field == 'utime' || $field == 'mtime' || $field == 'lptime') {
                        // if the date isn't relative we  want to convert the value to a specific UTC date
                        if (!in_array($modifier, ['before', 'after', 'between'])) {
                            $value = Application_Common_DateHelper::UserTimezoneStringToUTCString($value);
                        } else {
                            $value = $value . ' ' . $datetimeunit . ' ago';
                            // Logging::info($value);
                        }
                    }

                    $qry = new CcBlockcriteria();
                    $qry->setDbCriteria($field)
                        ->setDbModifier($d['sp_criteria_modifier'])
                        ->setDbValue($value)
                        ->setDbBlockId($this->id);

                    if (isset($d['sp_criteria_extra'])) {
                        if ($field == 'utime' || $field == 'mtime' || $field == 'lptime') {
                            // if the date isn't relative we  want to convert the value to a specific UTC date
                            if (!in_array($modifier, ['before', 'after', 'between'])) {
                                $extra = Application_Common_DateHelper::UserTimezoneStringToUTCString($extra);
                            } else {
                                $extra = $extra . ' ' . $extradatetimeunit . ' ago';
                            }
                        }

                        $qry->setDbExtra($extra);
                    }
                    // save the criteria group so separation via new modifiers AND can be preserved vs. lumping
                    // them all into a single or later on
                    if (isset($criteriaGroup)) {
                        $qry->setDbCriteriaGroup($criteriaGroup);
                    }
                    $qry->save();
                }
            }
        }

        // insert sort info
        // RASTATIME 2026-08-30: null-coalesce ALL etc-fields (same
        // pattern the newer toggles below always had).  A POST missing
        // one of these fields used to hit setDbValue(null) on a
        // NOT-NULL column -> PDO 23502 -> abort AFTER the DELETE at the
        // top of this method had already wiped the stored criteria =
        // silent criteria loss on a failed save.
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('sort')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_sort_options'] ?? 'random')
            ->setDbBlockId($this->id)
            ->save();

        // insert limit info
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('limit')
            ->setDbModifier($p_criteriaData['etc']['sp_limit_options'] ?? 'items')
            ->setDbValue($p_criteriaData['etc']['sp_limit_value'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // insert repeat track option
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('repeat_tracks')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_repeat_tracks'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // insert overflow track option
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('overflow_tracks')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_overflow_tracks'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // RASTATIME 2026-05-18 — only-unplayed-tracks restriction.
        // See SmartBlockCriteria.php for UX context; null-coalesce
        // so legacy POSTs without the field default to disabled
        // rather than crashing on undefined index.
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('only_unplayed')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_only_unplayed'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // RASTATIME 2026-05-18 — only-tracks-with-expiry restriction.
        // Same null-coalesce pattern as above.
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('only_with_expiry')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_only_with_expiry'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // RASTATIME 2026-06-07 — Song Requests: only-requested-tracks
        // restriction.  Same null-coalesce pattern as the toggles above.
        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('use_requests')
            ->setDbModifier('N/A')
            ->setDbValue($p_criteriaData['etc']['sp_use_requests'] ?? 0)
            ->setDbBlockId($this->id)
            ->save();

        // RASTATIME 2026-05-21 — exclude-played-lately filter.  Stores
        // two rows: the master enable flag + the hours-back window.
        // Hours is normalised to an integer in [1, 8760] when the
        // master flag is on; clamps anything outside that range
        // server-side so a hand-crafted POST cannot inject a
        // 100000-hour interval that would defeat the filter.
        //
        // "checkbox on + hours empty/zero" combination: per operator
        // decision (ii) 2026-05-21 the form validator demands ≥ 1,
        // but the server-side guard here defaults the value to 24 h
        // rather than rejecting the save, because rejecting at this
        // late stage is a worse UX (the operator already left the
        // form).  The form-side validator catches the common case;
        // this is just a defence-in-depth fallback.
        // RASTATIME 2026-10-23 - the window is in MINUTES (operator: "30
        // minutes" must be possible); rows `exclude_played_lately_minutes`
        // / `exclude_artists_lately_minutes`, range 1..525600 (a year),
        // default 1440 (= the old 24 h).  Old `*_hours` rows are read as
        // hours x 60 until the block is saved again (loadCriteria).
        $excludeOn = ((int) ($p_criteriaData['etc']['sp_exclude_played_lately'] ?? 0)) === 1;
        $excludeMinutesRaw = (int) ($p_criteriaData['etc']['sp_exclude_played_lately_minutes'] ?? 0);
        // Persist the operator's last typed value when toggling the master
        // flag off so re-enabling later restores it.  Clamped to the same
        // range so a stale invalid value does not survive a save.
        $excludeMinutes = max(1, min(self::EXCLUDE_MAX_MINUTES, $excludeMinutesRaw ?: self::EXCLUDE_DEFAULT_MINUTES));

        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('exclude_played_lately')
            ->setDbModifier('N/A')
            ->setDbValue($excludeOn ? 1 : 0)
            ->setDbBlockId($this->id)
            ->save();

        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('exclude_played_lately_minutes')
            ->setDbModifier('N/A')
            ->setDbValue($excludeMinutes)
            ->setDbBlockId($this->id)
            ->save();

        // RASTATIME 2026-05-23 — exclude_artists_lately
        // companion pair: master toggle + hours-back window.  Same
        // defence-in-depth defaults + persistence-on-off as the
        // exclude_played_lately pair above.  Match key in fetch
        // is cc_files.artist_name (vs. cc_files.lptime).
        //
        // Hotfix 2026-05-24: the v1 criteria names
        // (`exclude_artists_played_lately` + `..._hours`) were
        // 29 + 35 chars; cc_blockcriteria.criteria is VARCHAR(32),
        // so the hours row hit a PDO 22001 truncation error and
        // the entire save aborted (operator-visible as "Save
        // hangs").  Renamed to `exclude_artists_lately` + `..._hours`
        // (22 + 28 chars, both fit).  The internal $storedCrit
        // keys stay `exclude_artists_played_lately*` so the rest
        // of the code (form + WHERE clause) is unchanged.  The
        // load path accepts both names for forward-compat with any
        // rows the operator may have already gotten into the DB
        // before this hotfix.
        $excludeArtistsOn = ((int) ($p_criteriaData['etc']['sp_exclude_artists_played_lately'] ?? 0)) === 1;
        $excludeArtistsMinutesRaw = (int) ($p_criteriaData['etc']['sp_exclude_artists_played_lately_minutes'] ?? 0);
        $excludeArtistsMinutes = max(1, min(self::EXCLUDE_MAX_MINUTES, $excludeArtistsMinutesRaw ?: self::EXCLUDE_DEFAULT_MINUTES));

        // Cleanup any leftover rows from the buggy v1 names so
        // the next save is back to a clean two-row state.  Cheap
        // even when there are none.
        $cleanupSql = "DELETE FROM cc_blockcriteria "
            . 'WHERE block_id = :bid '
            . "AND criteria IN ('exclude_artists_played_lately',"
            . "'exclude_artists_played_lately_hours')";
        try {
            Application_Common_Database::prepareAndExecute(
                $cleanupSql,
                [':bid' => $this->id],
                Application_Common_Database::EXECUTE
            );
        } catch (Exception $e) {
            Logging::warn('exclude_artists v1-name cleanup failed: ' . $e->getMessage());
        }

        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('exclude_artists_lately')
            ->setDbModifier('N/A')
            ->setDbValue($excludeArtistsOn ? 1 : 0)
            ->setDbBlockId($this->id)
            ->save();

        $qry = new CcBlockcriteria();
        $qry->setDbCriteria('exclude_artists_lately_minutes')
            ->setDbModifier('N/A')
            ->setDbValue($excludeArtistsMinutes)
            ->setDbBlockId($this->id)
            ->save();
    }

    /** RASTATIME 2026-10-23 - the "played lately" windows, in minutes. */
    const EXCLUDE_MAX_MINUTES = 525600;
    const EXCLUDE_DEFAULT_MINUTES = 1440;

    /**
     * RASTATIME 2026-10-23 - the window of a "played lately" filter in
     * minutes from the loaded criteria: the `*_minutes` row, else the old
     * `*_hours` row x 60, else the default.
     *
     * @param array  $storedCrit
     * @param string $key        exclude_played_lately | exclude_artists_played_lately
     *
     * @return int minutes, clamped to 1..EXCLUDE_MAX_MINUTES
     */
    public static function excludeWindowMinutes(array $storedCrit, $key)
    {
        if (isset($storedCrit[$key . '_minutes']['value'])) {
            $minutes = (int) $storedCrit[$key . '_minutes']['value'];
        } elseif (isset($storedCrit[$key . '_hours']['value'])) {
            $minutes = (int) $storedCrit[$key . '_hours']['value'] * 60;
        } else {
            $minutes = self::EXCLUDE_DEFAULT_MINUTES;
        }

        return max(1, min(self::EXCLUDE_MAX_MINUTES, $minutes));
    }

    /**
     * generate list of tracks. This function saves criteria and generate
     * tracks.
     *
     * @param array $p_criteria
     * @param mixed $returnList
     */
    public function generateSmartBlock($p_criteria, $returnList = false)
    {
        $this->saveSmartBlockCriteria($p_criteria);
        $insertList = $this->getListOfFilesUnderLimit();
        $this->deleteAllFilesFromBlock();
        // construct id array
        $ids = [];
        foreach ($insertList as $ele) {
            $ids[] = $ele['id'];
        }
        $this->addAudioClips(array_values($ids));
        // update length in playlist contents.
        $this->updateBlockLengthInAllPlaylist();

        return ['result' => 0];
    }

    public function updateBlockLengthInAllPlaylist()
    {
        $blocks = CcPlaylistcontentsQuery::create()->filterByDbBlockId($this->id)->find();
        $blocks->getFirst();
        $iterator = $blocks->getIterator();
        while ($iterator->valid()) {
            $length = $this->getUnformatedLength();
            if (!preg_match('/^[0-9]{2}:[0-9]{2}:[0-9]{2}/', $length)) {
                $iterator->current()->setDbClipLength(null);
            } else {
                $iterator->current()->setDbClipLength($length);
            }
            $iterator->current()->save();
            $iterator->next();
        }
    }

    /**
     * @param null|float $show         seconds for a "time remaining" limit
     * @param null|float $timeOverride RASTATIME 2026-10-06 - seconds that replace a
     *                                 "duration in time" limit (the picker raises
     *                                 the block's own limit by the crossfade overlap
     *                                 so the block fills its duration ON AIR)
     */
    /**
     * RASTATIME 2026-10-16 - fill context.  A dynamic block is expanded for
     * a place in the schedule: the show instance being filled, its show,
     * and the moment the picked rows will play (the "slot").  The teaser
     * criterion and the planned-rows part of "exclude tracks played lately"
     * read it; without a context (e.g. "Generate" in the editor) the slot
     * is now and no show is excluded.  Set by AutoPlaylistManager and
     * Scheduler around the expansion, cleared afterwards.
     *
     * @var null|array{instance_id: ?int, show_id: ?int, slot: DateTime}
     */
    private static $fillContext;

    /**
     * RASTATIME 2026-10-23 - the file ids the running expansion gathered so
     * far (earlier blocks and fixed items of the same playlist); the
     * "played lately" filters leave them out.  Reset with the context.
     *
     * @var int[]
     */
    private static $fillPicked = [];

    /**
     * @param null|int      $instanceId
     * @param null|int      $showId
     * @param null|DateTime $slotUtc    when the picked rows will play (UTC)
     */
    public static function setFillContext($instanceId, $showId, $slotUtc)
    {
        $slot = $slotUtc instanceof DateTime ? clone $slotUtc : new DateTime('now', new DateTimeZone('UTC'));
        $slot->setTimezone(new DateTimeZone('UTC'));
        self::$fillContext = [
            'instance_id' => $instanceId ? (int) $instanceId : null,
            'show_id' => $showId ? (int) $showId : null,
            'slot' => $slot,
        ];
        self::$fillPicked = [];
    }

    public static function clearFillContext()
    {
        self::$fillContext = null;
        self::$fillPicked = [];
    }

    /**
     * RASTATIME 2026-10-23 - replace the list of file ids picked so far in
     * the running expansion (see $fillPicked).
     *
     * @param array<int, int|string> $fileIds
     */
    public static function setPickedInFill(array $fileIds)
    {
        self::$fillPicked = array_values(array_unique(array_map('intval', array_filter($fileIds))));
    }

    /** @return int[] */
    public static function pickedInFill()
    {
        return self::$fillPicked;
    }

    /** @return array{instance_id: ?int, show_id: ?int, slot: DateTime} */
    public static function fillContext()
    {
        if (self::$fillContext === null) {
            return ['instance_id' => null, 'show_id' => null, 'slot' => new DateTime('now', new DateTimeZone('UTC'))];
        }

        return ['instance_id' => self::$fillContext['instance_id'], 'show_id' => self::$fillContext['show_id'], 'slot' => clone self::$fillContext['slot']];
    }

    /**
     * RASTATIME 2026-10-16 - value => label of a teaser criterion's select.
     *
     * @param string $key         teaser_show | teaser_type | teaser_fits
     * @param bool   $placeholder prepend the "Select ..." row
     */
    public static function teaserCriteriaOptions($key, $placeholder = true)
    {
        switch ($key) {
            case 'teaser_show':
                $opts = [];
                foreach (Application_Model_StoredFile::teaserShows() as $id => $name) {
                    $opts[(string) $id] = $name;
                }
                $head = ['0' => _('Select show')];

                break;

            case 'teaser_type':
                $opts = Application_Model_StoredFile::teaserTypeLabels();
                $head = ['0' => _('Select teaser type')];

                break;

            case 'teaser_fits':
                $opts = ['yes' => _('the day of the show being filled')];
                $head = ['0' => _('Select')];

                break;

            default:
                return [];
        }

        return $placeholder ? $head + $opts : $opts;
    }

    /**
     * RASTATIME 2026-10-16 - SQL of a teaser criterion (used as a
     * Criteria::CUSTOM criterion, so it joins the row's AND / OR groups
     * like any other rule).
     *
     * teaser_show  is / is not <show id>
     * teaser_type  is / is not show|today|tomorrow
     * teaser_fits  is yes: the jingle fits the slot of the fill context -
     *   'today'    the teased show has an instance on the slot's day
     *              (station timezone) that starts after the slot;
     *   'tomorrow' the teased show has an instance on the following day;
     *   'show'     any day, unless the show is over for today (it had an
     *              instance today that ended before the slot and has no
     *              later one today);
     *   and never the show whose instance is being filled.
     *
     * @param string $key
     * @param string $modifier is | is not
     * @param string $value
     */
    public static function teaserCriterionSql($key, $modifier, $value)
    {
        if (!Application_Model_StoredFile::teaserColumnsReady()) {
            Logging::warn('smart block: teaser criterion used before migrations 0069/0070 - empty pool');

            return 'FALSE';
        }
        $not = trim((string) $modifier) === CriteriaModifier::IS_NOT;
        // a jingle may announce several shows (cc_file_teaser, migration 0070)
        $linked = 'SELECT 1 FROM cc_file_teaser ft WHERE ft.file_id = cc_files.id';
        if ($key === 'teaser_show') {
            $id = (int) $value;
            if ($id <= 0) {
                return 'FALSE';
            }

            return ($not ? 'NOT ' : '') . "EXISTS ({$linked} AND ft.show_id = {$id})";
        }
        if ($key === 'teaser_type') {
            $type = in_array($value, Application_Model_StoredFile::TEASER_TYPES, true) ? $value : null;
            if ($type === null) {
                return 'FALSE';
            }

            return $not
                ? "(cc_files.teaser_type IS NULL OR cc_files.teaser_type <> '{$type}')"
                : "cc_files.teaser_type = '{$type}'";
        }
        if ($key !== 'teaser_fits') {
            return 'FALSE';
        }
        $ctx = self::fillContext();
        $tz = Application_Model_Preference::GetDefaultTimezone() ?: 'UTC';
        $tzSql = str_replace("'", "''", $tz);
        $slotUtc = $ctx['slot']->format('Y-m-d H:i:s');
        $local = clone $ctx['slot'];
        $local->setTimezone(new DateTimeZone($tz));
        $day = $local->format('Y-m-d');
        $next = (clone $local)->modify('+1 day')->format('Y-m-d');
        $inst = 'SELECT 1 FROM cc_show_instances i WHERE i.show_id = ft.show_id AND i.modified_instance = FALSE '
            . "AND ((i.starts AT TIME ZONE 'UTC') AT TIME ZONE '{$tzSql}')::date = DATE '%s'";
        $onDay = sprintf($inst, $day);
        $onNext = sprintf($inst, $next);
        $laterToday = "EXISTS ({$onDay} AND i.starts > TIMESTAMP '{$slotUtc}')";
        $overToday = "EXISTS ({$onDay} AND i.ends <= TIMESTAMP '{$slotUtc}')";
        $airsTomorrow = "EXISTS ({$onNext})";
        // one fitting linked show is enough; the show being filled never counts
        $sql = "EXISTS ({$linked}";
        if ($ctx['show_id']) {
            $sql .= ' AND ft.show_id <> ' . (int) $ctx['show_id'];
        }
        $sql .= ' AND ('
            . "(cc_files.teaser_type = 'today' AND {$laterToday})"
            . " OR (cc_files.teaser_type = 'tomorrow' AND {$airsTomorrow})"
            . " OR (cc_files.teaser_type = 'show' AND (NOT {$overToday} OR {$laterToday}))"
            . '))';

        return $not ? "NOT {$sql}" : $sql;
    }

    public function getListOfFilesUnderLimit($show = null, $timeOverride = null)
    {
        $info = $this->getListofFilesMeetCriteria($show, false, $timeOverride);
        $files = $info['files'];
        $limit = $info['limit'];
        $repeat = $info['repeat_tracks'] == 1;
        $overflow = $info['overflow_tracks'] == 1;
        $isRandomSort = $info['sort_type'] == 'random';
        $blockTime = $limit['time'];
        $blockItems = $limit['items'];

        if ($files->isEmpty()) {
            return [];
        }

        // this moves the pointer to the first element in the collection
        $files->getFirst();
        $iterator = $files->getIterator();

        /**
         * @var Track[] $tracks
         */
        $tracks = [];
        $maxItems = 500;
        while ($iterator->valid() && count($tracks) < $maxItems) {
            $id = $iterator->current()->getDbId();
            $fileLength = $iterator->current()->getCueLength();
            $length = Application_Common_DateHelper::calculateLengthInSeconds($fileLength);

            $tracks[] = new Track($id, $length);

            $iterator->next();
        }

        /**
         * @var Track[] $insertList
         */
        $insertList = [];
        $totalTime = 0;
        if ($isRandomSort && !$overflow && $blockItems === null) {
            $minTrackLength = min(array_map(fn (Track $item) => $item->length, $tracks));
            do {
                $solution = SSPSolution::solve($tracks, $blockTime - $totalTime);
                $insertList = array_merge($insertList, $solution->tracks);
                $totalTime += $solution->sum;
            } while ($repeat && ($blockTime - $totalTime) > $minTrackLength);
            shuffle($insertList);
        } else {
            $isFull = function () use (&$blockItems, &$insertList, &$totalTime, &$blockTime) {
                return $blockItems !== null && count($insertList) >= $blockItems || $totalTime > $blockTime;
            };

            $addTrack = function (Track $track) use ($overflow, $blockTime, &$insertList, &$totalTime) {
                if ($overflow) {
                    $insertList[] = $track;
                    $totalTime += $track->length;
                } else {
                    $projectedTime = $totalTime + $track->length;

                    if ($projectedTime <= $blockTime) {
                        $insertList[] = $track;
                        $totalTime += $track->length;
                    }
                }
            };

            foreach ($tracks as $track) {
                $addTrack($track);

                if ($isFull()) {
                    break;
                }
            }

            $sizeOfInsert = count($insertList);

            // RASTATIME 2026-05-18 — upstream had a "repeat tracks until
            // limit is reached" loop with no safety against the case where
            // no remaining track fits.  When `overflow=false` and the
            // shortest track in the pool is larger than the remaining
            // time-to-limit, `addTrack()` silently no-ops, `totalTime`
            // stops growing, `isFull()` never flips true, and PHP spins
            // forever — eventually killed by mod_fcgid's pipe timeout,
            // returning HTTP 500 to the caller with no diagnostic in
            // legacy.log because the catch (Throwable) above never
            // executes.  Symptom in the Operator's report 2026-05-18:
            // "I can't add a Smart Block to a show" with 0 useful logs.
            //
            // Bounded retry: track the smallest track length we have and
            // bail out as soon as `(blockTime - totalTime) < minLen` —
            // at that point no track will ever fit and looping is futile.
            // Falls back to "max 1000 spins" so a logically-impossible
            // edge case (e.g. empty tracks array) still terminates.
            $minTrackLen = null;
            if (count($tracks) > 0) {
                $minTrackLen = min(array_map(
                    fn (Track $t) => $t->length, $tracks
                ));
            }
            $spinGuard = 0;
            while (!$isFull() && $repeat && $sizeOfInsert > 0) {
                if (
                    !$overflow
                    && $minTrackLen !== null
                    && ($blockTime - $totalTime) < $minTrackLen
                ) {
                    // No remaining track can fit — stop trying.
                    break;
                }
                if (++$spinGuard > 1000) {
                    Logging::warn(
                        'Block::getListOfFilesUnderLimit: repeat-fill loop '
                        . 'hit spin-guard (1000 iterations); breaking. '
                        . 'block_id=' . $this->id
                        . ' totalTime=' . $totalTime
                        . ' blockTime=' . $blockTime
                        . ' minTrackLen=' . var_export($minTrackLen, true)
                    );
                    break;
                }
                Logging::debug('adding repeated tracks.');
                Logging::debug('total time = ' . $totalTime);
                $track = $insertList[array_rand(array_slice($insertList, 0, $sizeOfInsert))];

                $addTrack($track);
            }
        }

        // RASTATIME 2026-05-25 — within-block spread for the
        // exclude_played_lately / exclude_artists_lately filters.
        // The SQL WHERE clauses upstream make sure the pool only
        // contains tracks whose artist / file has NOT been heard
        // in the configured hours-back window via cc_playout_history.
        // But once the block is generated, the tracks ARE about to
        // be played — so the same constraint must apply INSIDE the
        // generated sequence too.
        //
        // Algorithm (operator decision 2026-05-25):
        //   For every slot of the originally-selected $insertList,
        //   try the original track first.  If it conflicts with the
        //   elapsed-time window of the tracks placed so far, replace
        //   it with another track from the broader $tracks pool
        //   (the full SQL-filtered candidate set, up to maxItems 500).
        //   If no non-conflicting replacement is left in the pool,
        //   place the original anyway and emit a Logging::warn.
        //
        //   $tracks is the broader pool; $insertList is the original
        //   selection that fit the block's time / item limit.  We
        //   pass both so replacements can be pulled from outside the
        //   originally-chosen subset.
        $insertList = $this->applyWithinBlockSpread($insertList, $tracks);

        return array_map(fn (Track $track) => ['id' => $track->id, 'length' => $track->length], $insertList);
    }

    /**
     * Re-order a generated track list so that the within-block
     * spread constraints for exclude_played_lately +
     * exclude_artists_lately are honoured.  See the call site
     * comment above for the algorithm.
     *
     * @param Track[] $insertList originally-selected tracks for the block
     * @param Track[] $pool       full SQL-filtered candidate pool (incl. tracks not in $insertList) for replacements
     * @return Track[]            final track list with conflicts replaced where possible
     */
    private function applyWithinBlockSpread(array $insertList, array $pool)
    {
        if (count($insertList) < 2) {
            return $insertList;
        }

        $storedCrit = $this->getCriteria();

        $excludeTracksOn = isset($storedCrit['exclude_played_lately'])
            && $storedCrit['exclude_played_lately']['value'] == 1;
        $excludeArtistsOn = isset($storedCrit['exclude_artists_played_lately'])
            && $storedCrit['exclude_artists_played_lately']['value'] == 1;

        if (!$excludeTracksOn && !$excludeArtistsOn) {
            return $insertList;
        }

        // RASTATIME 2026-10-23 - minutes (excludeWindowMinutes reads old hours rows too)
        $excludeTracksSec = $excludeTracksOn
            ? self::excludeWindowMinutes($storedCrit, 'exclude_played_lately') * 60
            : 0;
        $excludeArtistsSec = $excludeArtistsOn
            ? self::excludeWindowMinutes($storedCrit, 'exclude_artists_played_lately') * 60
            : 0;

        // Lookup artist_name for every file_id in the broader pool
        // (not just insertList) in a single SQL round-trip — pool is
        // capped at maxItems = 500, so the IN-list stays small.
        $artistByFileId = [];
        if ($excludeArtistsOn) {
            $fileIds = array_unique(array_map(fn (Track $t) => (int) $t->id, $pool));
            if (!empty($fileIds)) {
                $sql = 'SELECT id, artist_name FROM cc_files WHERE id IN ('
                    . implode(',', array_map('intval', $fileIds)) . ')';
                try {
                    $rows = Application_Common_Database::prepareAndExecute(
                        $sql, [], Application_Common_Database::ALL
                    );
                    foreach ($rows as $r) {
                        $artistByFileId[(int) $r['id']] = trim((string) $r['artist_name']);
                    }
                } catch (Exception $e) {
                    // If the lookup fails, fall back to no artist spread —
                    // sequence stays exactly as before this pass.
                    Logging::warn('applyWithinBlockSpread artist lookup failed: ' . $e->getMessage());
                    $excludeArtistsOn = false;
                    $excludeArtistsSec = 0;
                }
            }
        }

        // SplObjectStorage tracks which Track instances we have
        // already placed in the output, so the replacement search
        // does not re-pick something already used.
        $placed = new SplObjectStorage();
        $output = [];
        $totalElapsed = 0;
        $lastTrackTime = [];   // file_id     => elapsed seconds at the last placement
        $lastArtistTime = [];  // artist_name => elapsed seconds at the last placement

        $hasConflict = function (Track $track) use (
            $excludeTracksSec,
            $excludeArtistsSec,
            $artistByFileId,
            &$lastTrackTime,
            &$lastArtistTime,
            &$totalElapsed
        ) {
            if ($excludeTracksSec > 0 && isset($lastTrackTime[$track->id])) {
                if ($totalElapsed - $lastTrackTime[$track->id] < $excludeTracksSec) {
                    return true;
                }
            }
            if ($excludeArtistsSec > 0) {
                $artist = $artistByFileId[$track->id] ?? '';
                if ($artist !== '' && isset($lastArtistTime[$artist])) {
                    if ($totalElapsed - $lastArtistTime[$artist] < $excludeArtistsSec) {
                        return true;
                    }
                }
            }

            return false;
        };

        foreach ($insertList as $slotIdx => $originalTrack) {
            $chosen = null;

            // Step 1: try the originally-selected track.
            if (!$placed->contains($originalTrack) && !$hasConflict($originalTrack)) {
                $chosen = $originalTrack;
            }

            // Step 2: original conflicts (or is already placed —
            // possible with repeat_tracks=true).  Walk the broader
            // pool for the first non-conflicting unplaced track.
            if ($chosen === null) {
                foreach ($pool as $candidate) {
                    if ($placed->contains($candidate)) {
                        continue;
                    }
                    if ($candidate === $originalTrack) {
                        continue; // already tried in step 1
                    }
                    if (!$hasConflict($candidate)) {
                        $chosen = $candidate;
                        break;
                    }
                }
            }

            // Step 3: nothing in the pool fits — place the original
            // anyway and warn (operator decision 2026-05-25).  If
            // even the original is already placed (only possible
            // with repeat_tracks=true on a tiny pool), grab any
            // unplaced track as a last resort.
            if ($chosen === null) {
                if (!$placed->contains($originalTrack)) {
                    $chosen = $originalTrack;
                } else {
                    foreach ($pool as $candidate) {
                        if (!$placed->contains($candidate)) {
                            $chosen = $candidate;
                            break;
                        }
                    }
                }
                if ($chosen !== null) {
                    Logging::warn(sprintf(
                        'Smart-block within-block spread: file_id=%d (artist=%s) '
                        . 'placed at slot %d despite a conflict — no non-conflicting '
                        . 'replacement left in the pool of %d tracks.',
                        (int) $chosen->id,
                        $artistByFileId[(int) $chosen->id] ?? '',
                        $slotIdx,
                        count($pool)
                    ));
                }
            }

            if ($chosen === null) {
                // Defensive — pool exhausted (shouldn't happen since
                // the original track is always at least one candidate).
                break;
            }

            $placed->attach($chosen);
            $output[] = $chosen;
            $lastTrackTime[$chosen->id] = $totalElapsed;
            if ($excludeArtistsOn) {
                $artist = $artistByFileId[$chosen->id] ?? '';
                if ($artist !== '') {
                    $lastArtistTime[$artist] = $totalElapsed;
                }
            }
            $totalElapsed += $chosen->length;
        }

        return $output;
    }

    /**
     * Parses each row in the database for the criteria associated with this block and renders human readable labels.
     * Returns it as an array with each criteria_name and modifier_name added based upon options array lookup.
     */
    public function getCriteria()
    {
        $allCriteria = BlockCriteria::criteriaMap();
        $allOptions = CriteriaModifier::mapToDisplay();

        // Load criteria from db
        $out = CcBlockcriteriaQuery::create()->orderByDbCriteria()->findByDbBlockId($this->id);
        $storedCrit = [];

        foreach ($out as $crit) {
            $criteria = $crit->getDbCriteria();
            $modifier = $crit->getDbModifier();
            $value = $crit->getDbValue();
            $extra = $crit->getDbExtra();
            $criteriagroup = $crit->getDbCriteriaGroup();

            if ($criteria == 'limit') {
                $storedCrit['limit'] = [
                    'value' => $value,
                    'modifier' => $modifier,
                    'display_modifier' => _($modifier),
                ];
            } elseif ($criteria == 'repeat_tracks') {
                $storedCrit['repeat_tracks'] = ['value' => $value];
            } elseif ($criteria == 'overflow_tracks') {
                $storedCrit['overflow_tracks'] = ['value' => $value];
            } elseif ($criteria == 'only_unplayed') {
                // RASTATIME 2026-05-18
                $storedCrit['only_unplayed'] = ['value' => $value];
            } elseif ($criteria == 'only_with_expiry') {
                // RASTATIME 2026-05-18
                $storedCrit['only_with_expiry'] = ['value' => $value];
            } elseif ($criteria == 'use_requests') {
                // RASTATIME 2026-06-07 — Song Requests
                $storedCrit['use_requests'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately') {
                // RASTATIME 2026-05-21 — master toggle (0/1).  The
                // companion hours value lives in a separate row
                // (criteria = 'exclude_played_lately_hours') so the
                // existing per-row schema does not need to change.
                $storedCrit['exclude_played_lately'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately_hours') {
                // RASTATIME 2026-05-21 — hours-back window (1..8760);
                // 2026-10-23 - kept readable, converted by excludeWindowMinutes
                $storedCrit['exclude_played_lately_hours'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately_minutes') {
                // RASTATIME 2026-10-23 — window in minutes (1..525600)
                $storedCrit['exclude_played_lately_minutes'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately'
                   || $criteria == 'exclude_artists_played_lately'
            ) {
                // RASTATIME 2026-05-23 — master toggle (0/1).
                // The v1 criteria name `exclude_artists_played_lately`
                // (29 chars) is also accepted for forward-compat
                // with rows the operator may have saved before the
                // 2026-05-24 VARCHAR-32 hotfix renamed the canonical
                // name to `exclude_artists_lately` (22 chars).  Both
                // collapse into the same $storedCrit key so the rest
                // of the code does not care which name was on disk.
                $storedCrit['exclude_artists_played_lately'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately_hours'
                   || $criteria == 'exclude_artists_played_lately_hours'
            ) {
                // RASTATIME 2026-05-23 — hours-back window (1..8760).
                // Both v1 + v2 names accepted (see master comment).
                // 2026-10-23 - kept readable, converted by excludeWindowMinutes
                $storedCrit['exclude_artists_played_lately_hours'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately_minutes') {
                // RASTATIME 2026-10-23 — window in minutes (1..525600)
                $storedCrit['exclude_artists_played_lately_minutes'] = ['value' => $value];
            } elseif ($criteria == 'sort') {
                $storedCrit['sort'] = ['value' => $value];
            } else {
                $c = $allCriteria[$criteria];
                $storedCrit['crit'][$criteria][] = [
                    'criteria' => $criteria,
                    'value' => $value,
                    'modifier' => $modifier,
                    'extra' => $extra,
                    'criteria_group' => $criteriagroup,
                    'display_name' => $c->display,
                    'display_modifier' => $allOptions[$modifier],
                ];
            }
        }

        return $storedCrit;
    }

    /**
     * Parses each row in the database for the criteria associated with this block and renders human readable labels.
     * Returns it as an array with each criteria_name and modifier_name added based upon options array lookup.
     * Maintains original separation of similar criteria that were separated by and statements.
     */
    public function getCriteriaGrouped()
    {
        $criteriaOptions = BlockCriteria::displayCriteria();
        $modifierOptions = CriteriaModifier::mapToDisplay();

        // Load criteria from db
        $out = CcBlockcriteriaQuery::create()->orderByDbCriteria()->findByDbBlockId($this->id);
        $storedCrit = [];

        foreach ($out as $crit) {
            $criteria = $crit->getDbCriteria();
            $modifier = $crit->getDbModifier();
            $value = $crit->getDbValue();
            $extra = $crit->getDbExtra();
            $criteriagroup = $crit->getDbCriteriaGroup();

            if ($criteria == 'limit') {
                $storedCrit['limit'] = [
                    'value' => $value,
                    'modifier' => $modifier,
                    'display_modifier' => _($modifier),
                ];
            } elseif ($criteria == 'repeat_tracks') {
                $storedCrit['repeat_tracks'] = ['value' => $value];
            } elseif ($criteria == 'overflow_tracks') {
                $storedCrit['overflow_tracks'] = ['value' => $value];
            } elseif ($criteria == 'only_unplayed') {
                // RASTATIME 2026-05-18
                $storedCrit['only_unplayed'] = ['value' => $value];
            } elseif ($criteria == 'only_with_expiry') {
                // RASTATIME 2026-05-18
                $storedCrit['only_with_expiry'] = ['value' => $value];
            } elseif ($criteria == 'use_requests') {
                // RASTATIME 2026-06-07 — Song Requests
                $storedCrit['use_requests'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately') {
                // RASTATIME 2026-05-21 — master toggle (0/1).  The
                // companion hours value lives in a separate row
                // (criteria = 'exclude_played_lately_hours') so the
                // existing per-row schema does not need to change.
                $storedCrit['exclude_played_lately'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately_hours') {
                // RASTATIME 2026-05-21 — hours-back window (1..8760);
                // 2026-10-23 - kept readable, converted by excludeWindowMinutes
                $storedCrit['exclude_played_lately_hours'] = ['value' => $value];
            } elseif ($criteria == 'exclude_played_lately_minutes') {
                // RASTATIME 2026-10-23 — window in minutes (1..525600)
                $storedCrit['exclude_played_lately_minutes'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately'
                   || $criteria == 'exclude_artists_played_lately'
            ) {
                // RASTATIME 2026-05-23 — master toggle (0/1).
                // The v1 criteria name `exclude_artists_played_lately`
                // (29 chars) is also accepted for forward-compat
                // with rows the operator may have saved before the
                // 2026-05-24 VARCHAR-32 hotfix renamed the canonical
                // name to `exclude_artists_lately` (22 chars).  Both
                // collapse into the same $storedCrit key so the rest
                // of the code does not care which name was on disk.
                $storedCrit['exclude_artists_played_lately'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately_hours'
                   || $criteria == 'exclude_artists_played_lately_hours'
            ) {
                // RASTATIME 2026-05-23 — hours-back window (1..8760).
                // Both v1 + v2 names accepted (see master comment).
                // 2026-10-23 - kept readable, converted by excludeWindowMinutes
                $storedCrit['exclude_artists_played_lately_hours'] = ['value' => $value];
            } elseif ($criteria == 'exclude_artists_lately_minutes') {
                // RASTATIME 2026-10-23 — window in minutes (1..525600)
                $storedCrit['exclude_artists_played_lately_minutes'] = ['value' => $value];
            } elseif ($criteria == 'sort') {
                $storedCrit['sort'] = ['value' => $value];
            } else {
                $storedCrit['crit'][$criteria . $criteriagroup][] = [
                    'criteria' => $criteria,
                    'value' => $value,
                    'modifier' => $modifier,
                    'extra' => $extra,
                    'display_name' => $criteriaOptions[$criteria],
                    'display_modifier' => $modifierOptions[$modifier],
                ];
            }
        }

        return $storedCrit;
    }

    private function resolveDate($value, $timeZone)
    {
        if (!is_string($value)) {
            return $value;
        }

        $dt = new DateTime('now', new DateTimeZone($timeZone));

        return preg_replace_callback(
            '/now{(.*?)}/',
            fn ($matches) => $dt->format($matches[1]),
            $value
        );
    }

    // this function return list of propel object
    //
    // RASTATIME 2026-06-07 — $ignoreRequestFilter (default false): when
    // true, the "use requests" criterion is NOT applied.  The Requestable-
    // Pool sync passes true because the pool defines WHAT MAY BE REQUESTED
    // (the catalogue), not what has already been requested.
    public function getListofFilesMeetCriteria($showLimit = null, $ignoreRequestFilter = false, $timeOverride = null)
    {
        $storedCrit = $this->getCriteria();

        $qry = CcFilesQuery::create();
        $qry->useFkOwnerQuery('subj', 'left join');

        $allCriteria = BlockCriteria::criteriaMap();
        $timeZone = Application_Model_Preference::GetDefaultTimezone();

        // Logging::info($storedCrit);
        if (isset($storedCrit['crit'])) {
            foreach ($storedCrit['crit'] as $crit) {
                // RASTATIME 2026-10-14 - one bracketed chain per field: the
                // rules of a group (an editor row and its "+" rows) are ORed,
                // the groups are ANDed, (A or B) and (C or D).  The rules used
                // to go straight into $qry->addAnd()/addOr(), which Propel
                // attaches to the field's existing criterion, so a later
                // group with alternatives nested to the left:
                // ((A or B) and C) or D.  Without that pattern the SQL is
                // unchanged.
                $fieldCriterion = null;
                $groupCriterion = null;
                $i = 0;
                $prevgroup = null;
                $group = null;
                // now we need to sort based upon extra which contains the and grouping from the form
                usort($crit, function ($a, $b) {
                    return $a['criteria_group'] - $b['criteria_group'];
                });
                // we need to run the following loop separately for each criteria group inside of each array
                foreach ($crit as $criteria) {
                    $group = $criteria['criteria_group'];
                    $spCriteria = $criteria['criteria'];
                    $spCriteriaModifier = $criteria['modifier'];

                    // RASTATIME 2026-10-16 - teaser criteria are SQL of their own
                    $virtualSql = in_array($spCriteria, BlockCriteria::TEASER_KEYS, true)
                        ? self::teaserCriterionSql($spCriteria, $spCriteriaModifier, (string) $criteria['value'])
                        : null;

                    $column = CcFilesPeer::getTableMap()->getColumnByPhpName($allCriteria[$spCriteria]->peer);

                    // data should already be in UTC, do we have to do anything special here anymore?
                    if ($virtualSql !== null) {
                        $spCriteriaValue = $virtualSql;
                        $spCriteriaExtra = null;
                    } elseif ($column->getType() == PropelColumnTypes::TIMESTAMP) {
                        $spCriteriaValue = $criteria['value'];

                        if (isset($criteria['extra'])) {
                            $spCriteriaExtra = $criteria['extra'];
                        }
                    } elseif ($spCriteria == 'bit_rate' || $spCriteria == 'sample_rate') {
                        // multiply 1000 because we store only number value
                        // e.g 192kps is stored as 192000
                        $spCriteriaValue = $criteria['value'] * 1000;
                        if (isset($criteria['extra'])) {
                            $spCriteriaExtra = $criteria['extra'] * 1000;
                        }
                    /*
                    * If user is searching for an exact match of length we need to
                    * search as if it starts with the specified length because the
                    * user only sees the rounded version (i.e. 4:02.7 is 4:02.761625
                    * in the database)
                    */
                    } elseif (in_array($spCriteria, ['length', 'cuein', 'cueout']) && $spCriteriaModifier == 'is') {
                        $spCriteriaModifier = 'starts with';
                        $spCriteria .= '::text';
                        $spCriteriaValue = $criteria['value'];
                    } else {
                        /* Propel does not escape special characters properly when using LIKE/ILIKE
                         * We have to add extra slashes in these cases
                         */
                        $tempModifier = trim(self::$modifier2CriteriaMap[$spCriteriaModifier]);
                        if ($tempModifier == 'ILIKE') {
                            $spCriteriaValue = addslashes($criteria['value']);
                            // addslashes() does not esapce '%' so we have to do it manually
                            $spCriteriaValue = str_replace('%', '\%', $spCriteriaValue);
                        } else {
                            $spCriteriaValue = $criteria['value'];
                        }
                        $spCriteriaExtra = $criteria['extra'];
                    }

                    if ($virtualSql === null) {
                        $spCriteriaValue = $this->resolveDate($spCriteriaValue, $timeZone);
                    }

                    if ($virtualSql !== null) {
                        // nothing to shape: the SQL is complete
                    } elseif ($spCriteriaModifier == CriteriaModifier::STARTS_WITH) {
                        $spCriteriaValue = "{$spCriteriaValue}%";
                    } elseif ($spCriteriaModifier == CriteriaModifier::ENDS_WITH) {
                        $spCriteriaValue = "%{$spCriteriaValue}";
                    } elseif ($spCriteriaModifier == CriteriaModifier::CONTAINS || $spCriteriaModifier == CriteriaModifier::DOES_NOT_CONTAIN) {
                        $spCriteriaValue = "%{$spCriteriaValue}%";
                    } elseif ($spCriteriaModifier == CriteriaModifier::IS_IN_THE_RANGE) {
                        $spCriteriaValue = "{$spCriteria} >= '{$spCriteriaValue}' AND {$spCriteria} <= '{$spCriteriaExtra}'";
                    } elseif ($spCriteriaModifier == CriteriaModifier::BEFORE) {
                        // need to pull in the current time and subtract the value or figure out how to make it relative
                        $relativedate = new DateTime($spCriteriaValue);
                        $dt = $relativedate->format(DateTime::ISO8601);
                        $spCriteriaValue = "COALESCE({$spCriteria}, DATE '-infinity') <= '{$dt}'";
                    } elseif ($spCriteriaModifier == CriteriaModifier::AFTER) {
                        $relativedate = new DateTime($spCriteriaValue);
                        $dt = $relativedate->format(DateTime::ISO8601);
                        $spCriteriaValue = "COALESCE({$spCriteria}, DATE '-infinity') >= '{$dt}'";
                    } elseif ($spCriteriaModifier == CriteriaModifier::BETWEEN) {
                        $fromrelativedate = new DateTime($spCriteriaValue);
                        $fdt = $fromrelativedate->format(DateTime::ISO8601);

                        $torelativedate = new DateTime($spCriteriaExtra);
                        $tdt = $torelativedate->format(DateTime::ISO8601);
                        $spCriteriaValue = "COALESCE({$spCriteria}, DATE '-infinity') >= '{$fdt}' AND COALESCE({$spCriteria}, DATE '-infinity') <= '{$tdt}'";
                    }

                    $spCriteriaModifier = $virtualSql !== null ? Criteria::CUSTOM : self::$modifier2CriteriaMap[$spCriteriaModifier];

                    try {
                        if ($spCriteria == 'owner_id') {
                            $spCriteria = 'subj.login';
                        }

                        if ($spCriteria == 'filepath') {
                            $spCriteria = "reverse(split_part(reverse(filepath), '/', 1))";
                        }

                        if ($virtualSql !== null) {
                            $spCriteria = 'cc_files.id';
                        }

                        $criterion = $qry->getNewCriterion($spCriteria, $spCriteriaValue, $spCriteriaModifier);
                        if ($i > 0 && $prevgroup == $group && $groupCriterion !== null) {
                            $groupCriterion->addOr($criterion);
                        } else {
                            if ($fieldCriterion === null) {
                                $fieldCriterion = $criterion;
                            } else {
                                $fieldCriterion->addAnd($criterion);
                            }
                            $groupCriterion = $criterion;
                        }
                        // only add this NOT LIKE null if you aren't also matching on another criteria
                        if ($i == 0) {
                            if ($spCriteriaModifier == Criteria::NOT_ILIKE || $spCriteriaModifier == Criteria::NOT_EQUAL) {
                                $groupCriterion->addOr($qry->getNewCriterion($spCriteria, null, Criteria::ISNULL));
                            }
                        }
                    } catch (Exception $e) {
                        Logging::info($e);
                    }
                    $prevgroup = $group;
                    ++$i;
                }
                if ($fieldCriterion !== null) {
                    try {
                        $qry->addAnd($fieldCriterion);
                    } catch (Exception $e) {
                        Logging::info($e);
                    }
                }
            }
        }

        // check if file exists
        $qry->add('file_exists', 'true', Criteria::EQUAL);
        $qry->add('hidden', 'false', Criteria::EQUAL);

        // RASTATIME 2026-05-16 - Exclude expired tracks from NEW Smartblock
        // evaluations.  Already-built blocks keep their entries (the
        // pruner only flips the flag; it does not touch cc_blockcontents),
        // so currently-scheduled shows continue to play normally.
        $qry->add('disabled', 'false', Criteria::EQUAL);

        $sortTracks = 'random';
        if (isset($storedCrit['sort'])) {
            $sortTracks = $storedCrit['sort']['value'];
        }
        if ($sortTracks == 'newest') {
            $qry->addDescendingOrderByColumn('utime');
        } elseif ($sortTracks == 'oldest') {
            $qry->addAscendingOrderByColumn('utime');
        } elseif ($sortTracks == 'mostrecentplay') {
            $qry->addAscendingOrderByColumn('lptime DESC NULLS LAST, filepath');
        } elseif ($sortTracks == 'leastrecentplay') {
            $qry->addAscendingOrderByColumn('lptime ASC NULLS FIRST, filepath');
        } elseif ($sortTracks == 'earliestexpiry') {
            // RASTATIME 2026-05-18 — track with the soonest expires_at
            // comes first; tracks without an expiry (NULL) go to the
            // end so they don't dilute the air-before-expiry intent.
            // filepath as secondary key keeps the order stable for
            // tracks that share the same expiry second (e.g. a batch
            // of episodes auto-expired by the same podcast setting).
            $qry->addAscendingOrderByColumn('expires_at ASC NULLS LAST, filepath');
        } elseif ($sortTracks == 'mostrequested') {
            // RASTATIME 2026-06-07 — Song Requests.  Highest request
            // count first (the "votes" ordering); requested_at ASC as
            // the tie-breaker so equally-voted tracks play oldest-first,
            // filepath last for a stable order.  NULLs (never requested)
            // sink to the bottom.
            $qry->addAscendingOrderByColumn('request_count DESC, requested_at ASC NULLS LAST, filepath');
        } elseif ($sortTracks == 'oldestrequest') {
            // RASTATIME 2026-06-07 — Song Requests.  Longest-waiting
            // request first (FIFO queue); NULLs (never requested) go
            // last so a "use requests" block drains real requests first.
            $qry->addAscendingOrderByColumn('requested_at ASC NULLS LAST, filepath');
        } elseif ($sortTracks == 'random') {
            $qry->addAscendingOrderByColumn('random()');
        } else {
            Logging::warning('Unimplemented sortTracks type in ' . __FILE__);
        }

        // construct limit restriction
        $limits = [];
        if (isset($storedCrit['limit'])) {
            if ($storedCrit['limit']['modifier'] == 'items') {
                $limits['time'] = 1440 * 60;
                $limits['items'] = $storedCrit['limit']['value'];
            } elseif ($storedCrit['limit']['modifier'] == 'remaining') {
                // show will be null unless being called inside a show instance
                if (!is_null($showLimit)) {
                    $limits['time'] = $showLimit;
                    $limits['items'] = null;
                } else {
                    $limits['time'] = 60 * 60;
                    $limits['items'] = null;
                }
            } else {
                $limits['time'] = $storedCrit['limit']['modifier'] == 'hours' ?
                    intval(floatval($storedCrit['limit']['value']) * 60 * 60) :
                    intval($storedCrit['limit']['value'] * 60);
                $limits['items'] = null;
                if ($timeOverride !== null) {
                    // RASTATIME 2026-10-06 - see getListOfFilesUnderLimit()
                    $limits['time'] = max(0.0, (float) $timeOverride);
                }
            }
        }

        $repeatTracks = 0;
        $overflowTracks = 0;

        if (isset($storedCrit['repeat_tracks'])) {
            $repeatTracks = $storedCrit['repeat_tracks']['value'];
        }

        if (isset($storedCrit['overflow_tracks'])) {
            $overflowTracks = $storedCrit['overflow_tracks']['value'];
        }

        // RASTATIME 2026-05-18 — only-unplayed-tracks restriction
        // (see SmartBlockCriteria.php for UX context).  Applied as a
        // WHERE filter on cc_files.lptime so it composes naturally
        // with whatever other criteria the operator built — same as
        // any other Propel filter() call on $qry.  Default off
        // (cc_block_criteria row missing or value=0): query is
        // unchanged from upstream behaviour.
        if (isset($storedCrit['only_unplayed']) && $storedCrit['only_unplayed']['value'] == 1) {
            $qry->where('cc_files.lptime IS NULL');
        }

        // RASTATIME 2026-05-18 — only-tracks-with-expiry restriction.
        // Same composition pattern as only_unplayed above, but on the
        // expires_at column.  Pairs naturally with the new "Earliest
        // expiry first" sort: enable both to schedule only short-lived
        // content sorted by its retention deadline.
        if (isset($storedCrit['only_with_expiry']) && $storedCrit['only_with_expiry']['value'] == 1) {
            $qry->where('cc_files.expires_at IS NOT NULL');
        }

        // RASTATIME 2026-06-07 — Song Requests: only-requested-tracks
        // restriction.  Same composition pattern as only_with_expiry
        // above, on the cc_files.requested flag (maintained by the
        // request intake + reset lifecycle).  Pairs with the
        // "Most requested first" / "Oldest request first" sorts to turn
        // a smart block into a request slot.
        // RASTATIME 2026-06-07 — skipped when $ignoreRequestFilter is set
        // (Requestable-Pool sync), so a "use requests" criterion left on a
        // pool block does not empty the pool.
        if (!$ignoreRequestFilter
            && isset($storedCrit['use_requests'])
            && $storedCrit['use_requests']['value'] == 1
        ) {
            $qry->where('cc_files.requested = true');
        }

        // RASTATIME 2026-05-21 — re-rotation protection: exclude tracks
        // played in the last N hours.  Pattern matches only_unplayed
        // above (one extra Propel ->where()) so the filter composes
        // naturally with every other criterion.
        //
        // "Never played" (cc_files.lptime IS NULL) is INCLUDED by the
        // filter per operator decision (i) 2026-05-21 — a track that
        // has never been played has by definition not been played
        // lately.  Without the IS NULL branch this filter would shrink
        // the pool of fresh / new tracks, which is the opposite of
        // what an operator picks this filter for.
        //
        // CRITICAL: outer parentheses around the OR-expression.
        // Propel concatenates ->where() raw strings with " AND " into
        // the assembled WHERE clause without wrapping them in their
        // own group.  Without explicit parens around the OR pair, the
        // resulting SQL is mis-parsed by SQL operator precedence (AND
        // binds tighter than OR) when the operator's Search Criteria
        // already used addOr() — typical case "genre is X or Y or Z".
        // The bug surfaces as the pool count GROWING when the filter
        // is toggled on (tracks that flunk the genre filter but pass
        // the < INTERVAL branch slip back in via the broken OR
        // grouping).  Bug reported + fixed 2026-05-22.
        //
        // INTERVAL '%d hours' uses a PostgreSQL-side string-formatted
        // integer; the value is already validated to [1, 8760] in
        // saveSmartBlockCriteria + the form validator, so there is no
        // SQL-injection risk from the (int) cast below — Propel will
        // pass it through to PDO unchanged.
        // RASTATIME 2026-10-16 - the window is measured from the slot the
        // picked rows will play in (fill context; now when there is none),
        // and PLANNED rows count as well: a track scheduled inside the
        // window - in the hour before, in the same show by an earlier block
        // of this fill, or in a show already laid out after it - is out,
        // although it has not played yet (operator: teaser rotation with
        // autoloading everywhere).
        $refSlot = self::fillContext()['slot']->format('Y-m-d H:i:s');
        if (isset($storedCrit['exclude_played_lately'])
            && $storedCrit['exclude_played_lately']['value'] == 1
        ) {
            // RASTATIME 2026-10-23 - window in minutes
            $excludeMinutes = self::excludeWindowMinutes($storedCrit, 'exclude_played_lately');
            $qry->where(
                "((cc_files.lptime IS NULL OR cc_files.lptime < TIMESTAMP '{$refSlot}' - INTERVAL '"
                . $excludeMinutes . " minutes') AND NOT EXISTS ("
                . 'SELECT 1 FROM cc_schedule s WHERE s.file_id = cc_files.id '
                . "AND s.starts > TIMESTAMP '{$refSlot}' - INTERVAL '" . $excludeMinutes . " minutes' "
                . "AND s.starts < TIMESTAMP '{$refSlot}' + INTERVAL '" . $excludeMinutes . " minutes'))"
            );
            // RASTATIME 2026-10-23 - a playlist is expanded block by block in
            // memory and inserted afterwards, so a track an earlier block of
            // the SAME expansion picked is in no table yet: the two "Dayteaser"
            // blocks of one playlist picked the same teaser (operator, BBC
            // News 17:00).  The expansion registers what it gathered so far
            // (setPickedInFill); those ids are out as well.
            $picked = self::pickedInFill();
            if (!empty($picked)) {
                $qry->where('cc_files.id NOT IN (' . implode(',', $picked) . ')');
            }
        }

        // RASTATIME 2026-05-23 — exclude_artists_played_lately:
        // drop any track whose artist_name matches the artist of a
        // file played in the last N hours.  NOT EXISTS subquery
        // joins cc_playout_history → cc_files for the artist-name
        // lookup (history table itself stores artist via metadata
        // rows, but for files we have the canonical value on
        // cc_files.artist_name and that's what the pool uses).
        // NULL / empty artist_name is intentionally never matched:
        // a single track with a blank artist would otherwise
        // exclude every other blank-artist track globally, which
        // is the opposite of what the operator wants.
        // Klammern-Wrap analog dem exclude_played_lately fix from
        // 2026-05-22 so OR-mixing with neighbouring WHERE blocks
        // stays predictable.
        // Hours value is already clamped to [1, 8760] in
        // saveSmartBlockCriteria + form validator — the integer
        // cast below carries no SQL-injection risk.
        if (isset($storedCrit['exclude_artists_played_lately'])
            && $storedCrit['exclude_artists_played_lately']['value'] == 1
        ) {
            // RASTATIME 2026-10-23 - window in minutes
            $excludeArtistsMinutes = self::excludeWindowMinutes($storedCrit, 'exclude_artists_played_lately');
            // RASTATIME 2026-10-16 - planned rows count too (see above)
            $qry->where(
                '(cc_files.artist_name IS NULL '
                . "OR cc_files.artist_name = '' "
                . 'OR (NOT EXISTS ('
                .   'SELECT 1 FROM cc_playout_history ph '
                .   'JOIN cc_files f ON f.id = ph.file_id '
                .   'WHERE f.artist_name = cc_files.artist_name '
                .   "AND ph.starts > TIMESTAMP '{$refSlot}' - INTERVAL '"
                . $excludeArtistsMinutes . " minutes') AND NOT EXISTS ("
                .   'SELECT 1 FROM cc_schedule s '
                .   'JOIN cc_files f2 ON f2.id = s.file_id '
                .   'WHERE f2.artist_name = cc_files.artist_name '
                .   "AND s.starts > TIMESTAMP '{$refSlot}' - INTERVAL '" . $excludeArtistsMinutes . " minutes' "
                .   "AND s.starts < TIMESTAMP '{$refSlot}' + INTERVAL '" . $excludeArtistsMinutes . " minutes')))"
            );
            // RASTATIME 2026-10-23 - artists of the tracks an earlier block of
            // the same expansion picked (see the tracks filter above)
            $picked = self::pickedInFill();
            if (!empty($picked)) {
                $qry->where(
                    "(cc_files.artist_name IS NULL OR cc_files.artist_name = '' OR NOT EXISTS ("
                    . 'SELECT 1 FROM cc_files fp WHERE fp.id IN (' . implode(',', $picked) . ') '
                    . 'AND fp.artist_name = cc_files.artist_name))'
                );
            }
        }

        try {
            $out = $qry->setFormatter(ModelCriteria::FORMAT_ON_DEMAND)->find();

            return ['files' => $out, 'limit' => $limits, 'repeat_tracks' => $repeatTracks, 'overflow_tracks' => $overflowTracks, 'count' => $out->count(), 'sort_type' => $sortTracks];
        } catch (Exception $e) {
            Logging::info($e);
        }
    }

    public static function organizeSmartPlaylistCriteria($p_criteria)
    {
        $fieldNames = ['sp_criteria_field', 'sp_criteria_modifier', 'sp_criteria_value', 'sp_criteria_extra', 'sp_criteria_datetime_select', 'sp_criteria_extra_datetime_select'];
        $output = [];
        foreach ($p_criteria as $ele) {
            $index = strrpos($ele['name'], '_');

            /* Strip field name of modifier index
             * Ex: sp_criteria_field_0_0 -> sp_criteria_field_0
             */
            $fieldName = substr($ele['name'], 0, $index);

            // Get criteria row index.
            $tempName = $ele['name'];
            // Get the last digit in the field name
            preg_match('/^\D*(?=\d)/', $tempName, $r);
            if (isset($r[0])) {
                $critIndexPos = strlen($r[0]);
                $critIndex = $tempName[$critIndexPos];
            }
            $lastChar = substr($ele['name'], -1);

            // If lastChar is an integer we should strip it off
            if (!preg_match('/^[a-zA-Z]$/', $lastChar)) {
                /* Strip field name of criteria index
                 * Ex: sp_criteria_field_0 -> sp_criteria_field
                 * We do this to check if the field name is a criteria
                 * or the block type
                 */
                $n = strrpos($fieldName, '_');
                $fieldName = substr($fieldName, 0, $n);
            }

            if (in_array($fieldName, $fieldNames)) {
                $output['criteria'][$critIndex][$lastChar][$fieldName] = trim($ele['value']);
            } else {
                $output['etc'][$ele['name']] = $ele['value'];
            }
        }

        return $output;
    }

    public static function getAllBlockFiles()
    {
        $sql = <<<'SQL'
SELECT distinct(file_id)
FROM cc_blockcontents
SQL;

        $files = Application_Common_Database::prepareAndExecute($sql, []);

        $real_files = [];
        foreach ($files as $f) {
            $real_files[] = $f['file_id'];
        }

        return $real_files;
    }
    // smart block functions end
}

class Track
{
    public int $id;

    public float $length;

    public function __construct($id, $length)
    {
        $this->id = $id;
        $this->length = $length;
    }

    public function __toString(): string
    {
        return (string) $this->id;
    }
}

/**
 * Using a randomized greedy with local improvement approximation solution for the Subset Sum Problem.
 *
 * https://web.stevens.edu/algebraic/Files/SubsetSum/przydatek99fast.pdf
 */
class SSPSolution
{
    /**
     * @var Track[]
     */
    public array $tracks;

    public float $sum = 0.0;

    public function __construct($tracks = [], $sum = null)
    {
        $this->tracks = $tracks;
        if ($sum !== null) {
            $this->sum = $sum;
        } else {
            foreach ($this->tracks as $track) {
                $this->sum += $track->length;
            }
        }
    }

    public function add(Track $track): SSPSolution
    {
        $new = $this->tracks;
        $new[] = $track;

        return new SSPSolution($new, $this->sum + $track->length);
    }

    public function replace(Track $old, Track $new): SSPSolution
    {
        return new SSPSolution(array_map(fn (Track $it) => $it === $old ? $new : $it, $this->tracks));
    }

    public static function isCloseEnough(float $delta): bool
    {
        return $delta < 0.25;
    }

    public static function maxByOrNull(array $array, callable $callback)
    {
        $max = null;
        $v = null;
        foreach ($array as $item) {
            $value = $callback($item);

            if ($max === null || $v < $value) {
                $max = $item;
                $v = $value;
            }
        }

        return $max;
    }

    /**
     * @param Track[] $tracks
     */
    public static function solve(array $tracks, float $target, int $trials = 50): SSPSolution
    {
        $best = new SSPSolution();
        for ($trial = 0; $trial < $trials; ++$trial) {
            shuffle($tracks);
            $initial = array_reduce($tracks, function (SSPSolution $solution, Track $track) use ($target) {
                $new = $solution->add($track);
                if ($new->sum <= $target) {
                    return $new;
                }

                return $solution;
            }, new SSPSolution());

            if (count($initial->tracks) == count($tracks)) {
                return $initial;
            }

            $acceptedItems = $initial->tracks;
            shuffle($acceptedItems);
            $localImprovement = array_reduce($acceptedItems, function (SSPSolution $solution, Track $track) use ($target, $tracks) {
                $delta = $target - $solution->sum;
                if (self::isCloseEnough($delta)) {
                    return $solution;
                }

                $replacement = self::maxByOrNull(
                    array_filter(
                        array_diff($tracks, $solution->tracks),
                        fn (Track $it) => $it->length > $track->length && $it->length - $track->length <= $delta,
                    ),
                    fn (Track $it) => $it->length,
                );

                if ($replacement === null) {
                    return $solution;
                }

                return $solution->replace($track, $replacement);
            }, $initial);

            if ($localImprovement->sum > $best->sum) {
                $best = $localImprovement;
            }
            if ($best->sum === 0.0) {
                return $best;
            }
        }

        return $best;
    }
}

class BlockNotFoundException extends Exception {}
class BlockNoPermissionException extends Exception {}
class BlockOutDatedException extends Exception {}
class BlockDyanmicException extends Exception {}
