<?php

class FileDataHelper
{
    /**
     * Join a storage root with a DB-relative path safely.
     *
     * RASTATIME (Windows): cc_files.filepath is stored without a leading
     * slash for files imported via the analyzer (e.g. "imported/2/Foo.mp3"),
     * but Application_Common_Storage::root() does not have a trailing slash either
     * ("C:/rastatime/media").  Naive concatenation produced
     * "C:/rastatime/mediaimported/2/Foo.mp3", which then made setArtwork /
     * resetArtwork / removeArtwork silently fail because file_put_contents
     * could not write to a non-existent directory.
     *
     * Files imported via legacy paths (e.g. the podcast downloader) are
     * stored with a leading slash, so we strip both ends defensively.
     */
    public static function joinStoragePath($storageRoot, $relPath)
    {
        return rtrim($storageRoot, '/\\') . '/' . ltrim($relPath, '/\\');
    }

    public static function getAudioMimeTypeArray()
    {
        return [
            'audio/ogg' => 'ogg',
            'application/ogg' => 'ogg',
            'audio/vorbis' => 'ogg',
            'audio/mp3' => 'mp3',
            'audio/mpeg' => 'mp3',
            'audio/mpeg3' => 'mp3',
            'audio/x-aac' => 'aac',
            'audio/aac' => 'aac',
            'audio/aacp' => 'aac',
            'audio/mp4' => 'm4a',
            'video/mp4' => 'mp4',
            'audio/x-flac' => 'flac',
            'audio/flac' => 'flac',
            'audio/wav' => 'wav',
            'audio/x-wav' => 'wav',
            'audio/mp2' => 'mp2',
            'audio/mp1' => 'mp1',
            'audio/x-ms-wma' => 'wma',
            'audio/basic' => 'au',
        ];
    }

    public static function getUploadAudioMimeTypeArray()
    {
        $mimes = self::getAudioMimeTypeArray();
        // RASTATIME 2026-10-21 - .wma is accepted again (operator go): the
        // analyzer transcodes Windows Media Audio to MP3 on import

        // audio/opus is not a real mime type, we only set it here to allow uploading
        // .opus files
        $mimes['audio/opus'] = 'opus';

        return $mimes;
    }

    /**
     * RASTATIME 2026-10-14 - the ONE list of audio file extensions RASTATIME
     * imports (lower case, without the dot).  The upload dialog,
     * CcFiles::createAndImport and the import-folder / FTP scans all use it.
     * The scans used to accept '.oga' while createAndImport refused it
     * ("Bad file extension.") - and the scan then deleted the refused source.
     *
     * @return string[]
     */
    public static function getUploadAudioExtensions()
    {
        $extensions = array_values(self::getUploadAudioMimeTypeArray());
        // Ogg audio under its own extension (audio/ogg maps to 'ogg' above)
        $extensions[] = 'oga';

        return array_values(array_unique($extensions));
    }

    /**
     * We want to throw out invalid data and process the upload successfully
     * at all costs, so check the data and sanitize it if necessary.
     *
     * @param array $data array containing new file metadata
     */
    public static function sanitizeData(&$data)
    {
        if (array_key_exists('track_number', $data)) {
            // If the track number isn't numeric, this will return 0
            $data['track_number'] = intval($data['track_number']);
        }
        if (array_key_exists('year', $data)) {
            // If the track number isn't numeric, this will return 0
            $data['year'] = intval($data['year']);
        }
        if (array_key_exists('bpm', $data)) {
            // Some BPM tags are silly and include the word "BPM". Let's strip that...
            $data['bpm'] = str_ireplace('BPM', '', $data['bpm']);
            // This will convert floats to ints too.
            $data['bpm'] = intval($data['bpm']);
        }
        if (array_key_exists('track_type_id', $data)) {
            // RASTATIME 2026-05-18 — keep "no type chosen" as empty
            // string instead of intval-ing it to 0.  The Edit-Track
            // form's Track-Type dropdown uses '' as the key for the
            // "Select a Type" placeholder option; collapsing it to
            // 0 (which is NOT in the options list) tripped Zend's
            // InArray validator and silently rejected the WHOLE form
            // save — operators saw the dialog close as if it had
            // saved, but no field (Expiry, Description, etc.) was
            // actually persisted.  The empty value is then mapped
            // to NULL inside StoredFile::setDbColMetadata (existing
            // path), so the DB still stores a clean NULL for tracks
            // without a chosen Track-Type.
            $rawTt = $data['track_type_id'];
            if ($rawTt === '' || $rawTt === null) {
                $data['track_type_id'] = '';
            } else {
                $data['track_type_id'] = intval($rawTt);
            }
        }
    }

    /**
     * Return a suitable extension for the given file.
     *
     * @param string $mime
     *
     * @return string file extension with(!) a dot (for convenience)
     *
     * @throws Exception
     */
    public static function getFileExtensionFromMime($mime)
    {
        $mime = trim(strtolower($mime));

        try {
            return '.' . static::getAudioMimeTypeArray()[$mime];
        } catch (Exception $e) {
            throw new Exception("Unknown file type: {$mime}");
        }
    }

    /**
     * Gets data URI from artwork file.
     *
     * @param string $file
     * @param int    $size
     * @param string $filepath
     *
     * @return string Data URI for artwork
     */
    public static function getArtworkData($file, $size, $filepath = false)
    {
        // RASTATIME 2026-10-24 - the Data URI is built from the JPG of that
        // size; the text copies (<base>-<size>, up to 2026-10-24) are only
        // read when the JPG is missing (covers made before the change and
        // not yet pruned).  Without either, the no-cover image.
        $baseUrl = Config::getPublicUrl();
        $default = $baseUrl . 'css/images/no-cover.jpg';
        $root = $filepath != false ? $filepath : Application_Common_Storage::root();
        $jpg = self::joinStoragePath($root, $file . '-' . $size . '.jpg');
        if (file_exists($jpg)) {
            $bytes = @file_get_contents($jpg);
            if ($bytes !== false && $bytes !== '') {
                return 'data:image/jpeg;charset=utf-8;base64,' . base64_encode($bytes);
            }
        }
        $legacy = self::joinStoragePath($root, $file . '-' . $size);
        if (file_exists($legacy)) {
            $text = @file_get_contents($legacy);
            if ($text !== false && $text !== '') {
                return $text;
            }
        }

        return $default;
    }

    /**
     * RASTATIME 2026-10-24 - the file extension of an embedded picture's MIME type.
     */
    private static function artworkExtension($mime)
    {
        $mime = strtolower(trim((string) $mime));
        if (strpos($mime, 'png') !== false) {
            return 'png';
        }
        if (strpos($mime, 'gif') !== false) {
            return 'gif';
        }
        if (strpos($mime, 'bmp') !== false) {
            return 'bmp';
        }

        return 'jpg';
    }

    public static function saveArtworkData($analyzeFile, $filename, $importDir = null, $DbPath = null)
    {
        if (class_exists('getID3')) {
            $getID3 = new getID3();
            $getFileInfo = $getID3->analyze($analyzeFile);
        } else {
            $getFileInfo = [];
            Logging::error('Failed to load getid3 library. Please upgrade RASTATIME.');
        }

        if (!isset($getFileInfo['comments']['picture'][0])) {
            return '';
        }
        // RASTATIME 2026-10-24 - only the five JPG sizes are written; the
        // original picture is scaled straight from memory (no Data-URI
        // original, no Data-URI copies of the sizes - ten files per cover
        // became five, 183,359 files / 8.5 GB on the live library).
        $picture = $getFileInfo['comments']['picture'][0];
        if (!file_exists($importDir . 'artwork/')) {
            if (!mkdir($importDir . 'artwork/', 0777, true)) {
                Logging::error('Failed to create artwork directory.');

                throw new Exception('Failed to create artwork directory.');
            }
        }
        $path_parts = pathinfo($filename);
        // RASTATIME 2026-10-09 - a Windows file name must not end with a
        // dot or a space ("R.A.F..mp3" -> "R.A.F."), and the reserved
        // characters are replaced; an empty remainder falls back to the
        // md5 of the audio file.
        $artworkName = rtrim(preg_replace('/[<>:"\/\\|?*\x00-\x1f]/', '_', (string) $path_parts['filename']), '. ');
        if ($artworkName === '') {
            $artworkName = md5_file($analyzeFile) ?: 'artwork';
        }
        $file = $importDir . 'artwork/' . $artworkName;
        if (self::resizeGroupFromBlob($file, (string) $picture['data'])) {
            return $DbPath . 'artwork/' . $artworkName;
        }
        Logging::error('Could not write the cover sizes for ' . $filename);

        return '';
    }

    /**
     * Reset artwork.
     *
     * @param string $trackid
     *
     * @return string $get_img Path to artwork
     */
    public static function resetArtwork($trackid)
    {
        $file = Application_Model_StoredFile::RecallById($trackid);
        $md = $file->getMetadata();
        $fp = Application_Common_Storage::root();
        $dbAudioPath = $md['MDATA_KEY_FILEPATH'];
        $fullpath = self::joinStoragePath($fp, $dbAudioPath);

        if (class_exists('getID3')) {
            $getID3 = new getID3();
            $getFileInfo = $getID3->analyze($fullpath);
        } else {
            $getFileInfo = [];
            Logging::error('Failed to load getid3 library. Please upgrade RASTATIME.');
        }

        if (!isset($getFileInfo['comments']['picture'][0])) {
            return '';
        }
        // RASTATIME 2026-10-24 - JPG sizes only (see saveArtworkData)
        $path_parts = pathinfo($fullpath);
        $base = dirname($fullpath) . '/' . $path_parts['filename'];
        if (self::resizeGroupFromBlob($base, (string) $getFileInfo['comments']['picture'][0]['data'])) {
            return dirname($dbAudioPath) . '/' . $path_parts['filename'];
        }
        Logging::error('Could not write the cover sizes for track ' . $trackid);

        return '';
    }

    /**
     * Set artwork.
     *
     * @param string $trackid
     * @param string $data    a Data URI ("data:image/...;base64,...") or "0" to remove
     *
     * @return string $get_img Path to artwork
     */
    public static function setArtwork($trackid, $data)
    {
        $file = Application_Model_StoredFile::RecallById($trackid);
        $md = $file->getMetadata();
        $fp = Application_Common_Storage::root();
        $dbAudioPath = $md['MDATA_KEY_FILEPATH'];
        $fullpath = self::joinStoragePath($fp, $dbAudioPath);

        if ($data == '0') {
            self::removeArtwork($trackid, $data);

            return '';
        }
        // RASTATIME 2026-10-24 - decode the Data URI once, write the JPG
        // sizes only (see saveArtworkData)
        $comma = strpos((string) $data, ',');
        $blob = $comma === false ? '' : base64_decode(substr((string) $data, $comma + 1), true);
        if ($blob === false || $blob === '') {
            Logging::error('setArtwork: no picture data for track ' . $trackid);

            return '';
        }
        $path_parts = pathinfo($fullpath);
        $base = dirname($fullpath) . '/' . $path_parts['filename'];
        if (self::resizeGroupFromBlob($base, $blob)) {
            return dirname($dbAudioPath) . '/' . $path_parts['filename'];
        }
        Logging::error('Could not write the cover sizes for track ' . $trackid);

        return '';
    }

    /**
     * Deletes just the artwork.
     *
     * @param mixed $trackid
     */
    public static function removeArtwork($trackid)
    {
        $file = Application_Model_StoredFile::RecallById($trackid);
        $md = $file->getMetadata();

        $fp = Application_Common_Storage::root();

        $artworkBasePath = self::joinStoragePath($fp, $md['MDATA_KEY_ARTWORK']);
        $audioPath = self::joinStoragePath($fp, $md['MDATA_KEY_FILEPATH']);

        $artworkPaths = [
            $artworkBasePath,
            $artworkBasePath . '-32.jpg',
            $artworkBasePath . '-64.jpg',
            $artworkBasePath . '-128.jpg',
            $artworkBasePath . '-256.jpg',
            $artworkBasePath . '-512.jpg',
            $artworkBasePath . '-32',
            $artworkBasePath . '-64',
            $artworkBasePath . '-128',
            $artworkBasePath . '-256',
        ];

        foreach ($artworkPaths as $filename) {
            // This should never happen. Make sure we don't delete the audio file.
            if ($filename == $audioPath) {
                continue;
            }

            if (file_exists($filename)) {
                unlink($filename);
            }
        }

        return '';
    }

    /**
     * Resize artwork group.
     *
     * @param string $file
     * @param string $ext
     */
    public static function resizeGroup($file, $ext)
    {
        // kept for callers that still hand over a file on disk (a Data-URI
        // text file or a plain image); the sizes are written by the blob
        // version
        if (!file_exists($file)) {
            return;
        }
        $content = (string) file_get_contents($file);
        if (strpos($content, 'data:') === 0) {
            $comma = strpos($content, ',');
            $content = $comma === false ? '' : (string) base64_decode(substr($content, $comma + 1), true);
        }
        self::resizeGroupFromBlob($file, $content);
    }

    /**
     * RASTATIME 2026-10-24 - write the five JPG sizes (32/64/128/256/512)
     * of a picture held in memory next to $base ("<base>-<size>.jpg").
     * GD detects the picture format itself (JPEG, PNG, GIF, BMP, WebP).
     *
     * @param string $base the artwork base path (no extension)
     * @param string $blob the picture bytes
     *
     * @return bool true when the 512 px file exists afterwards
     */
    public static function resizeGroupFromBlob($base, $blob)
    {
        $im = $blob === '' ? false : @imagecreatefromstring($blob);
        if (!$im) {
            // an unreadable picture gets the small error image, as before
            $im = imagecreatetruecolor(150, 30);
            $bgc = imagecolorallocate($im, 255, 255, 255);
            $tc = imagecolorallocate($im, 0, 0, 0);
            imagefilledrectangle($im, 0, 0, 150, 30, $bgc);
            imagestring($im, 1, 5, 5, 'Error loading cover', $tc);
        }
        foreach ([32, 64, 128, 256, 512] as $size) {
            $scaled = imagescale($im, $size);
            if ($scaled) {
                imagejpeg($scaled, $base . '-' . $size . '.jpg', 100);
                imagedestroy($scaled);
            }
        }
        imagedestroy($im);

        return file_exists($base . '-512.jpg');
    }

    /**
     * Render image
     * Used in API to render JPEG.
     *
     * @param string $file
     */
    public static function renderImage($file)
    {
        if ($file && file_exists($file)) {
            $im = @imagecreatefromjpeg($file);
            $img = $im;

            if ($im) {
                header('Content-Type: image/jpeg');
                imagejpeg($img);
                imagedestroy($img);
            }
        }
    }

    /**
     * Render Data URI
     * Used in API to render Data URI.
     *
     * @param string $dataFile
     */
    public static function renderDataURI($dataFile)
    {
        if ($filecontent = file_get_contents($dataFile) !== false) {
            $image = @file_get_contents($dataFile);
            $image = base64_encode($image);
            if (!$image || $image === '') {
                return;
            }
            $blob = base64_decode($image);
            $f = finfo_open();
            $mime_type = finfo_buffer($f, $blob, FILEINFO_MIME_TYPE);
            finfo_close($f);
            header('Content-Type: ' . $mime_type);
            echo $blob;
        } else {
            return;
        }
    }

    /**
     * Resize Image.
     *
     * @param string $orig_filename
     * @param string $converted_filename
     * @param string $ext
     * @param string $size               Default: 500
     * @param string $quality            Default: 75
     */
    public static function resizeImage($orig_filename, $converted_filename, $ext, $size = 500, $quality = 75)
    {
        $get_cont = file_get_contents($orig_filename);
        if ($ext == 'png') {
            $im = @imagecreatefrompng($get_cont);
        } elseif ($ext == 'gif') {
            $im = @imagecreatefromgif($get_cont);
        } else {
            $im = @imagecreatefromjpeg($get_cont);
        }

        // if one of those bombs, create an error image instead
        if (!$im) {
            $im = imagecreatetruecolor(150, 30);
            $bgc = imagecolorallocate($im, 255, 255, 255);
            $tc = imagecolorallocate($im, 0, 0, 0);
            imagefilledrectangle($im, 0, 0, 150, 30, $bgc);
            imagestring($im, 1, 5, 5, 'Error loading ' . $converted_filename, $tc);
        }

        // scale if appropriate
        if ($size) {
            $im = imagescale($im, $size);
        }

        $img = $im;
        imagejpeg($img, $converted_filename, $quality);
        imagedestroy($img);
    }

    /**
     * Convert image to Data URI.
     *
     * @param string $orig_filename
     * @param string $conv_filename
     */
    public static function imgToDataURI($orig_filename, $conv_filename)
    {
        $file = file_get_contents($orig_filename);
        $Image = 'data:image/jpeg;charset=utf-8;base64,' . base64_encode($file);
        $base64 = @$Image;

        // Save Data URI
        if (file_put_contents($conv_filename, $base64)) {
        } else {
            Logging::error('Could not save Data URI');
        }
    }

    /**
     * Track Type.
     *
     * @return string Track type key value
     */
    public static function saveTrackType($useUploadCookie = true)
    {
        // RASTATIME 2026-10-09 - the upload dialog remembers its track type in
        // the tt_upload cookie.  The import-folder scan runs inside whatever
        // request triggers the task manager - also the operator's browser -
        // and must never inherit that cookie: 1,377 files of the first bulk
        // import arrived as "Shows" that way.  Import paths pass false.
        if ($useUploadCookie && isset($_COOKIE['tt_upload'])) {
            $tt = $_COOKIE['tt_upload'];
        } else {
            // Use default track type
            $tt = Application_Model_Preference::GetTrackTypeDefault();
        }

        return $tt;
    }
}
