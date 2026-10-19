<?php

/**
 * Skeleton subclass for representing a row from the 'cc_files' table.
 *
 * You should add additional methods to this class to meet the
 * application requirements.  This class will only be generated as
 * long as it does not already exist in the output directory.
 */
class InvalidMetadataException extends Exception {}

class LibreTimeFileNotFoundException extends Exception {}

class OverDiskQuotaException extends Exception {}

class CcFiles extends BaseCcFiles
{
    public const MUSIC_DIRS_STOR_PK = 1;

    public const IMPORT_STATUS_SUCCESS = 0;
    public const IMPORT_STATUS_PENDING = 1;
    public const IMPORT_STATUS_FAILED = 2;

    // fields that are not modifiable via our RESTful API
    private static $blackList = [
        'id',
        'directory',
        'filepath',
        'file_exists',
        'mtime',
        'utime',
        'lptime',
        'silan_check',
        'is_scheduled',
        'is_playlist',
    ];

    // fields we should never expose through our RESTful API
    private static $privateFields = [
        'file_exists',
        'silan_check',
        'is_scheduled',
        'is_playlist',
    ];

    /**
     * Retrieve a sanitized version of the file metadata, suitable for public access.
     *
     * @param mixed $fileId
     */
    public static function getSanitizedFileById($fileId)
    {
        $file = CcFilesQuery::create()->findPk($fileId);
        if ($file) {
            return CcFiles::sanitizeResponse($file);
        }

        throw new LibreTimeFileNotFoundException();
    }

    /** Used to create a CcFiles object from an array containing metadata and a file uploaded by POST.
     *  This is used by our Media REST API!
     *
     * @param $fileArray An array containing metadata for a CcFiles object
     *
     * @return object the sanitized response
     *
     * @throws Exception
     */
    public static function createFromUpload($fileArray)
    {
        if (Application_Model_Systemstatus::isDiskOverQuota()) {
            throw new OverDiskQuotaException();
        }

        /* If full_path is set, the post request came from ftp.
         * Users are allowed to upload folders via ftp. If this is the case
         * we need to include the folder name with the file name, otherwise
         * files won't get removed from the organize folder.
         */

        // Extract the original filename, which we set as the temporary title for the track
        // until it's finished being processed by the analyzer.
        $originalFilename = $fileArray['file']['name'];
        $tempFilePath = $fileArray['file']['tmp_name'];

        try {
            return self::createAndImport($fileArray, $tempFilePath, $originalFilename);
        } catch (Exception $e) {
            if (file_exists($tempFilePath)) {
                unlink($tempFilePath);
            }

            throw $e;
        }
    }

    /** Import a music file to the library from a local file on disk (something pre-existing).
     *  This function allows you to copy a file rather than move it, which is useful for importing
     *  static music files (like sample tracks).
     *
     * @param string $filePath  the full path to the audio file to import
     * @param bool   $copyFile  True if you want to just copy the false, false if you want to move it (default false)
     * @param mixed  $fileArray
     *
     * @throws Exception
     */
    public static function createFromLocalFile($fileArray, $filePath, $copyFile = false)
    {
        $info = pathinfo($filePath);
        $fileName = basename($filePath) . '.' . $info['extension'];
        self::createAndImport($fileArray, $filePath, $fileName, $copyFile);
    }

    /**
     * RASTATIME 2026-05-16 - Public wrapper around createAndImport()
     * for the Local Import Folder feature (Section 23.12).
     *
     * The existing createFromLocalFile() public wrapper has a known
     * double-extension bug (line 111: it does
     * `basename($filePath) . '.' . $info['extension']` which produces
     * "file.mp3.mp3"), and createFromUpload() expects a $_FILES-style
     * array which the drop-folder scanner does not have.  This
     * wrapper takes a pre-determined originalFilename and forwards
     * straight to the private createAndImport implementation.
     *
     * @param string $filePath         absolute path to the audio file
     * @param string $originalFilename filename only (no path), preserved
     *                                  in the cc_files row
     * @param bool   $copyFile         true = copy, false = move (default;
     *                                  move atomically frees the
     *                                  drop-folder slot)
     * @return mixed sanitized response (see createAndImport)
     */
    public static function createFromImportFolder($filePath, $originalFilename, $copyFile = false)
    {
        return self::createAndImport([], $filePath, $originalFilename, $copyFile, true);
    }

    /**
     * RASTATIME 2026-10-19 - a finished show recording (see
     * Application_Service_ShowRecordingService): no upload cookie, the
     * "Recordings" track type, copy or move as the caller decides (a tagged
     * temp copy is moved, the original in the recording folder is copied).
     */
    public static function createFromRecording($filePath, $originalFilename, $trackTypeId, $copyFile)
    {
        return self::createAndImport([], $filePath, $originalFilename, $copyFile, true, (int) $trackTypeId);
    }

    /** Create a new CcFiles object/row and import a file for it.
     *  You shouldn't call this directly. Either use createFromUpload() or createFromLocalFile().
     *
     * @param array  $fileArray        Any metadata to pre-fill for the audio file
     * @param string $filePath         The full path to the audio file to import
     * @param string $originalFilename
     * @param bool   $copyFile
     *
     * @return mixed
     *
     * @throws Exception
     * @throws PropelException
     */
    private static function createAndImport($fileArray, $filePath, $originalFilename, $copyFile = false, $fromImportFolder = false, $trackTypeId = null)
    {
        $file = new CcFiles();

        try {
            // Only accept files with a file extension that we support.
            // Let the analyzer do the heavy lifting in terms of mime verification and playability
            // RASTATIME 2026-10-14 - the same list the import-folder / FTP scans use
            $fileExtension = pathinfo($originalFilename, PATHINFO_EXTENSION);
            if (!in_array(strtolower($fileExtension), FileDataHelper::getUploadAudioExtensions(), true)) {
                throw new Exception('Bad file extension.');
            }

            $fileArray = self::removeBlacklistedFields($fileArray);

            self::validateFileArray($fileArray);

            // Early md5dum processing
            $md5 = md5_file($filePath);

            // RASTATIME 2026-09-16 - artwork lives in imported/artwork/ (no owner-id level)
            $importedStorageDir = rtrim(Application_Common_Storage::root(), '/\\') . '/imported/';
            $importedDbPath = 'imported/';
            // RASTATIME 2026-10-09 - an unreadable embedded cover is no reason
            // to refuse the track (the import folder deletes a refused file)
            try {
                $artwork = FileDataHelper::saveArtworkData($filePath, $originalFilename, $importedStorageDir, $importedDbPath);
            } catch (Exception $artworkError) {
                Logging::warn('createAndImport: artwork of ' . $originalFilename . ' skipped: ' . $artworkError->getMessage());
                $artwork = '';
            }
            if (!$trackTypeId) {
                $trackTypeId = FileDataHelper::saveTrackType(!$fromImportFolder);
            }

            $file->fromArray($fileArray);
            $file->setDbOwnerId(self::getOwnerId());
            $now = new DateTime('now', new DateTimeZone('UTC'));
            $file->setDbTrackTitle($originalFilename);
            $file->setDbMd5($md5);
            $file->setDbArtwork($artwork);
            if ($trackTypeId) {
                $file->setDbTrackTypeId($trackTypeId);
            }
            $file->setDbUtime($now);
            $file->setDbHidden(true);
            // RASTATIME: Set ftype immediately so the file is usable even
            // without the analyzer service (which requires RabbitMQ).
            if (!$file->getDbFtype()) {
                $file->setDbFtype('audioclip');
            }
            $file->save();

            Application_Service_MediaService::importFileToLibrary(
                $file->getPrimaryKey(),
                self::getOwnerId(),
                $file->getDbTrackTypeId(),
                $originalFilename,
                $filePath,
                $copyFile,
                $fromImportFolder   // RASTATIME 2026-10-14 - a failed move never deletes the source
            );

            return CcFiles::sanitizeResponse($file);
        } catch (Exception $e) {
            $file->setDbImportStatus(self::IMPORT_STATUS_FAILED);
            $file->setDbHidden(true);
            // RASTATIME 2026-10-09 - a hand-over that fails before the
            // metadata is stored left a nameless row without a time stamp
            // (21 blank "Import failed" entries after the first bulk batch):
            // keep the file name and the time so Recent Uploads says what
            // failed, and when.
            if ((string) $file->getDbName() === '') {
                $file->setDbName(basename((string) $originalFilename));
            }
            if ($file->getDbUtime() === null) {
                $file->setDbUtime(new DateTime('now', new DateTimeZone('UTC')));
            }
            $file->save();

            throw $e;
        }
    }

    /** Update a file with metadata specified in an array.
     * @param $fileId    string The ID of the file to update in the DB
     * @param $fileArray array An associative array containing metadata. Replaces those fields if they exist.
     *
     * @return array a sanitized version of the file metadata array
     *
     * @throws Exception
     * @throws LibreTimeFileNotFoundException
     * @throws PropelException
     */
    public static function updateFromArray($fileId, $fileArray)
    {
        $file = CcFilesQuery::create()->findPk($fileId);

        $fileArray = self::removeBlacklistedFields($fileArray);
        $fileArray = self::stripTimeStampFromYearTag($fileArray);

        try {
            self::validateFileArray($fileArray);
            if ($file) {
                $file->fromArray($fileArray, BasePeer::TYPE_FIELDNAME);

                // Our RESTful API takes "full_path" as a field, which we then split and translate to match
                // our internal schema. Internally, file path is stored relative to a directory, with the directory
                // as a foreign key to cc_music_dirs.
                if (isset($fileArray['full_path'])) {
                    $fileSizeBytes = filesize($fileArray['full_path']);
                    if (!isset($fileSizeBytes) || $fileSizeBytes === false) {
                        throw new LibreTimeFileNotFoundException("Invalid filesize for {$fileId}");
                    }
                    Application_Model_Preference::updateDiskUsage($fileSizeBytes);

                    // RASTATIME (Windows): the analyzer (Python) reports full_path with
                    // OS-native separators (backslashes), but storage.path in libretime.conf
                    // is configured with forward slashes.  Normalise both to forward slashes
                    // before comparing — otherwise strpos returns false on Windows and the
                    // filepath column never gets populated.
                    $fullPath = str_replace('\\', '/', $fileArray['full_path']);
                    $storDir  = str_replace('\\', '/', Application_Common_Storage::root());
                    $pos = strpos($fullPath, $storDir);

                    if ($pos !== false) {
                        assert($pos == 0); // Path must start with the stor directory path

                        $filePathRelativeToStor = substr($fullPath, strlen($storDir));
                        $file->setDbFilepath($filePathRelativeToStor);
                    }

                    // RASTATIME: the upstream metadata pipeline never
                    // populates cc_files.name for upload imports — the
                    // analyzer hands back metadata fields like track_title
                    // and artist_name, but no plain "name".  Result: every
                    // newly imported file shows up with name='' in any
                    // legacy code path or REST consumer that still keys
                    // off that column.  Derive it once from the filename
                    // here so the column is always usable.
                    $name = basename($fullPath);
                    if ($name !== '' && method_exists($file, 'setDbName')) {
                        $file->setDbName($name);
                    }
                }
            } else {
                throw new LibreTimeFileNotFoundException("File id {$fileId} not found");
            }

            $now = new DateTime('now', new DateTimeZone('UTC'));
            $file->setDbMtime($now);
            $file->save();

            // RASTATIME 2026-09-28 - EBU R128 measurement (migration 0061):
            // loudness_lufs / true_peak_dbtp / loudness_range_lu arrive from
            // the analyzer (import and "Measure loudness now").  Propel does
            // not know the columns, so persist them via raw SQL; a key that
            // is absent leaves the stored value untouched, null clears it.
            $loudnessKeys = ['loudness_lufs', 'true_peak_dbtp', 'loudness_range_lu'];
            $loudnessSet = [];
            foreach ($loudnessKeys as $lk) {
                if (array_key_exists($lk, $fileArray)) {
                    $lv = $fileArray[$lk];
                    $loudnessSet[$lk] = ($lv === null || $lv === '') ? null : (float) $lv;
                }
            }
            if (!empty($loudnessSet)) {
                $con = Propel::getConnection();
                $assign = [];
                foreach ($loudnessSet as $lk => $lv) {
                    $assign[] = "{$lk} = :{$lk}";
                }
                $stmt = $con->prepare('UPDATE cc_files SET ' . implode(', ', $assign) . ' WHERE id = :id');
                foreach ($loudnessSet as $lk => $lv) {
                    if ($lv === null) {
                        $stmt->bindValue(":{$lk}", null, PDO::PARAM_NULL);
                    } else {
                        $stmt->bindValue(":{$lk}", $lv);
                    }
                }
                $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
                $stmt->execute();
            }

            // RASTATIME 2026-10-14 - lossless -> MP3 320 (migration 0066):
            // when the analyzer converted the upload, md5 is the md5 of the
            // new file and source_md5 the md5 of the ORIGINAL (the bulk
            // import's duplicate check compares against both).  Propel does
            // not know the column, so persist it via raw SQL - only a
            // well-formed 32-hex value; anything else leaves the column
            // untouched.  A failure costs only this column, never the import.
            if (array_key_exists('source_md5', $fileArray)) {
                $srcMd5 = strtolower(trim((string) $fileArray['source_md5']));
                if (preg_match('/^[0-9a-f]{32}$/', $srcMd5)) {
                    try {
                        $con = Propel::getConnection();
                        $stmt = $con->prepare('UPDATE cc_files SET source_md5 = :src WHERE id = :id');
                        $stmt->bindValue(':src', $srcMd5, PDO::PARAM_STR);
                        $stmt->bindValue(':id', (int) $fileId, PDO::PARAM_INT);
                        $stmt->execute();
                    } catch (Exception $exc) {
                        Logging::warn(
                            'CcFiles::updateFromArray: failed to persist source_md5 for file id='
                            . (int) $fileId . ': ' . $exc->getMessage()
                        );
                    }
                }
            }

            // RASTATIME 2026-05-16 - Track Expiry: persist expires_at via
            // raw SQL.  Propel CcFiles class is not regenerated for this
            // column (see schema.xml note), so $file->fromArray() above
            // silently ignored any expires_at the analyzer sent.  Accepts
            // ISO 8601 date / datetime strings from the analyzer's
            // _extract_expiry_tag.  Empty / null leaves the existing
            // value untouched.
            if (
                isset($fileArray['expires_at'])
                && is_string($fileArray['expires_at'])
                && trim($fileArray['expires_at']) !== ''
            ) {
                $expRaw = trim($fileArray['expires_at']);
                try {
                    $con = Propel::getConnection();
                    $stmt = $con->prepare(
                        'UPDATE cc_files
                         SET expires_at = :exp,
                             disabled = (CAST(:exp AS TIMESTAMP) < NOW())
                         WHERE id = :id'
                    );
                    $stmt->bindValue(':exp', $expRaw, PDO::PARAM_STR);
                    $stmt->bindValue(':id', $file->getDbId(), PDO::PARAM_INT);
                    $stmt->execute();
                    Logging::info(
                        'CcFiles::updateFromArray: set expires_at='
                        . $expRaw . ' for file id=' . $file->getDbId()
                    );
                } catch (Exception $exc) {
                    Logging::warn(
                        'CcFiles::updateFromArray: failed to persist '
                        . 'expires_at=' . $expRaw . ' for file id='
                        . $file->getDbId() . ': ' . $exc->getMessage()
                    );
                }
            }
        } catch (LibreTimeFileNotFoundException $e) {
            // RASTATIME 2026-09-10: only an EXISTING row can be marked as a
            // failed import.  With an unknown id $file is null, and the old
            // unguarded call was a PHP Error (not an Exception), which turned
            // the REST 404 into an HTML 500 page.
            if ($file !== null) {
                $file->setDbImportStatus(self::IMPORT_STATUS_FAILED);
                $file->setDbHidden(true);
                $file->save();
            }

            throw $e;
        }

        return CcFiles::sanitizeResponse($file);
    }

    /** Delete a file from the database and disk.
     * @param $id The file ID
     *
     * @throws DeleteScheduledFileException
     * @throws Exception
     * @throws FileNoPermissionException
     * @throws LibreTimeFileNotFoundException
     * @throws PropelException
     */
    public static function deleteById($id)
    {
        $file = CcFilesQuery::create()->findPk($id);
        if ($file) {
            $con = Propel::getConnection();
            $storedFile = Application_Model_StoredFile::RecallById($id, $con);
            $storedFile->delete();
        } else {
            throw new LibreTimeFileNotFoundException();
        }
    }

    private static function validateFileArray(&$fileArray)
    {
        // Sanitize any wildly incorrect metadata before it goes to be validated
        FileDataHelper::sanitizeData($fileArray);

        // EditAudioMD form is used here for validation
        $fileForm = new Application_Form_EditAudioMD();
        $fileForm->startForm(0); // The file ID doesn't matter here
        $fileForm->populate($fileArray);

        /*
         * Here we are truncating metadata of any characters greater than the
         * max string length set in the database. In the rare case a track's
         * genre is more than 64 chars, for example, we don't want to reject
         * tracks for that reason
         */
        foreach ($fileArray as $tag => &$value) {
            if ($fileForm->getElement($tag)) {
                $stringLengthValidator = $fileForm->getElement($tag)->getValidator('StringLength');
                // $stringLengthValidator will be false if the StringLength validator doesn't exist on the current element
                // in which case we don't have to truncate the extra characters
                if ($stringLengthValidator) {
                    // RASTATIME 2026-10-09 - truncate on a character boundary: a byte-wise
                    // substr cut multibyte characters in half and the StringLength
                    // validator (iconv_strlen) then rejected the whole file with 400
                    $value = mb_substr($value, 0, $stringLengthValidator->getMax(), 'UTF-8');
                }

                $value = self::stripInvalidUtf8Characters($value);
            }
        }

        // RASTATIME 2026-10-14 - columns that are no fields of the track
        // editor are not cut by the loop above: cc_files.encoder is
        // VARCHAR(64), and a longer TSSE / ENCODER tag (the analyzer reads
        // it from every format since 2026-10-14) made PostgreSQL reject the
        // whole callback - the track ended as a failed import.
        foreach (['encoder' => 64, 'encoded_by' => 255] as $column => $maxLength) {
            if (isset($fileArray[$column]) && is_string($fileArray[$column])) {
                $fileArray[$column] = self::stripInvalidUtf8Characters(
                    mb_substr($fileArray[$column], 0, $maxLength, 'UTF-8')
                );
            }
        }

        if (!$fileForm->isValidPartial($fileArray)) {
            $errors = $fileForm->getErrors();
            $messages = $fileForm->getMessages();
            Logging::error($messages);

            throw new Exception("Data validation failed: {$errors} - {$messages}");
        }

        return true;
    }

    public function getCueLength()
    {
        $cuein = $this->getDbCuein();
        $cueout = $this->getDbCueout();

        $cueinSec = Application_Common_DateHelper::calculateLengthInSeconds($cuein);
        $cueoutSec = Application_Common_DateHelper::calculateLengthInSeconds($cueout);
        $lengthSec = bcsub($cueoutSec, $cueinSec, 6);

        return Application_Common_DateHelper::secondsToPlaylistTime($lengthSec);
    }

    public function setDbTrackNumber($v)
    {
        $max = 2 ** 31 - 1;
        $v = ($v > $max) ? $max : $v;

        return parent::setDbTrackNumber($v);
    }

    // returns true if the file exists and is not hidden
    public function visible()
    {
        return $this->getDbFileExists() && !$this->getDbHidden();
    }

    public function reassignTo($user)
    {
        $this->setDbOwnerId($user->getDbId());
        $this->save();
    }

    /**
     * Strips out the private fields we do not want to send back in API responses.
     *
     * @param CcFiles $file a CcFiles object
     *
     * @return array
     */
    // TODO: rename this function?
    public static function sanitizeResponse($file)
    {
        $response = $file->toArray(BasePeer::TYPE_FIELDNAME);

        foreach (self::$privateFields as $key) {
            unset($response[$key]);
        }

        return $response;
    }

    /**
     * Returns the file size in bytes.
     */
    public function getFileSize()
    {
        return $this->getDbFilesize();
    }

    public function getFilename()
    {
        $info = pathinfo($this->getAbsoluteFilePath());

        // filename doesn't contain the extension because PHP is awful
        $mime = $this->getDbMime();
        $extension = FileDataHelper::getFileExtensionFromMime($mime);

        return $info['filename'] . $extension;
    }

    /**
     * Returns the file's absolute file path stored on disk.
     */
    public function getURLsForTrackPreviewOrDownload()
    {
        return [$this->getAbsoluteFilePath()];
    }

    /**
     * Returns the file's absolute file path stored on disk.
     */
    public function getAbsoluteFilePath()
    {
        $directory = Application_Common_Storage::root();
        $filepath = $this->getDbFilepath();

        return Application_Common_OsPath::join($directory, $filepath);
    }

    /**
     * Returns the artwork's absolute file path stored on disk.
     */
    public function getAbsoluteArtworkPath()
    {
        $directory = Application_Common_Storage::root();
        $filepath = $this->getDbArtwork();

        return Application_Common_OsPath::join($directory, $filepath);
    }

    /**
     * Strips out fields from incoming request data that should never be modified
     * from outside of Airtime.
     *
     * @param array $data
     */
    private static function removeBlacklistedFields($data)
    {
        foreach (self::$blackList as $key) {
            unset($data[$key]);
        }

        return $data;
    }

    private static function getOwnerId()
    {
        try {
            if (Zend_Auth::getInstance()->hasIdentity()) {
                $service_user = new Application_Service_UserService();

                return $service_user->getCurrentUser()->getDbId();
            }
            $defaultOwner = CcSubjsQuery::create()
                ->filterByDbType('A')
                ->orderByDbId()
                ->findOne();
            if (!$defaultOwner) {
                // what to do if there is no admin user?
                // should we handle this case?
                return null;
            }

            return $defaultOwner->getDbId();
        } catch (Exception $e) {
            Logging::info($e->getMessage());
        }
    }

    /*
     * It's possible that the year tag will be a timestamp but Airtime doesn't support this.
     * The year field in cc_files can only be 16 chars max.
     *
     * This functions strips the year field of it's timestamp, if one, and leaves just the year
     */
    private static function stripTimeStampFromYearTag($metadata)
    {
        if (isset($metadata['year'])) {
            if (preg_match('/^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2}):(\d{2}))?$/', $metadata['year'])) {
                $metadata['year'] = substr($metadata['year'], 0, 4);
            }
        }

        return $metadata;
    }

    private static function stripInvalidUtf8Characters($string)
    {
        // Remove invalid UTF-8 characters
        // reject overly long 2 byte sequences, as well as characters above U+10000 and replace with ?
        $string = preg_replace(
            '/[\x00-\x08\x10\x0B\x0C\x0E-\x19\x7F]' .
                '|[\x00-\x7F][\x80-\xBF]+' .
                '|([\xC0\xC1]|[\xF0-\xFF])[\x80-\xBF]*' .
                '|[\xC2-\xDF]((?![\x80-\xBF])|[\x80-\xBF]{2,})' .
                '|[\xE0-\xEF](([\x80-\xBF](?![\x80-\xBF]))|(?![\x80-\xBF]{2})|[\x80-\xBF]{3,})/S',
            '?',
            $string
        );

        // reject overly long 3 byte sequences and UTF-16 surrogates and replace with ?
        $string = preg_replace('/\xE0[\x80-\x9F][\x80-\xBF]' .
            '|\xED[\xA0-\xBF][\x80-\xBF]/S', '?', $string);

        // Do a final encoding conversion to
        return mb_convert_encoding($string, 'UTF-8', 'UTF-8');
    }

    private function removeEmptySubFolders($path)
    {
        exec("find {$path} -empty -type d -delete");
    }

    /**
     * Checks if the file is a regular file that can be previewed and downloaded.
     */
    public function isValidPhysicalFile()
    {
        return is_file($this->getAbsoluteFilePath());
    }

    /**
     * Deletes the file from the stor directory on disk.
     */
    public function deletePhysicalFile()
    {
        $filepath = $this->getAbsoluteFilePath();
        $artworkpath = $this->getAbsoluteArtworkPath();
        if (file_exists($filepath)) {
            unlink($filepath);
            // also delete related images (dataURI and jpeg files)
            foreach (glob("{$artworkpath}*", GLOB_NOSORT) as $filename) {
                unlink($filename);
            }
            unlink($artworkpath);
        } else {
            throw new Exception('Could not locate file ' . $filepath);
        }
    }

    /**
     * This function refers to the file's Amazon S3 resource id.
     * Returns null because cc_files are stored on local disk.
     */
    public function getResourceId()
    {
        return null;
    }

    public function getCcFileId()
    {
        return $this->id;
    }
} // CcFiles
