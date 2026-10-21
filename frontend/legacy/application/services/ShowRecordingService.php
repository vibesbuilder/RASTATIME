<?php

/**
 * RASTATIME 2026-10-19 - "Copy Show Recordings into Library".
 *
 * The playout reports a closed per-show recording (api/recording-finished:
 * show instance id + absolute path).  When the operator ticked the box under
 * Settings -> Local Machine -> Show Recording, this service imports a COPY of
 * the file into the media library: the recording folder keeps its archive
 * untouched, the library gets a track of type "Recordings" linked to the show
 * instance (cc_show_instances.file_id), so the recording can be scheduled
 * again (repeat of a live show) or used in playlists.
 *
 * The copy is tagged with ffmpeg before the hand-over (title "<show>
 * <YYYY-MM-DD HH:MM>", artist = show, album "Show Recordings") because the
 * analyzer reads the file's tags and Liquidsoap wrote the stream label of
 * the first packet into them.  Without ffmpeg the untagged original is
 * copied and the analyzer falls back to the file name as the title.
 */
class Application_Service_ShowRecordingService
{
    public const TRACK_TYPE_CODE = 'recd';
    public const TRACK_TYPE_NAME = 'Recordings';
    public const ALBUM = 'Show Recordings';

    /** Extensions the per-show recorder produces (liquidsoap_config._FILE_EXT_FOR_TYPE). */
    private const EXTENSIONS = ['mp3', 'aac', 'ogg', 'opus'];

    public static function enabled(): bool
    {
        return Application_Model_Preference::getLocalRecordingCopyToLibrary();
    }

    /**
     * Import the finished recording of a show instance into the library.
     *
     * @param int    $instanceId cc_show_instances.id (0 when unknown)
     * @param string $path       absolute path of the recording file
     *
     * @return array ok, skipped|rejected reason, file_id
     */
    public static function import(int $instanceId, string $path): array
    {
        if (!self::enabled()) {
            return ['ok' => true, 'skipped' => 'disabled'];
        }
        $reason = self::rejectReason($path);
        if ($reason !== null) {
            Logging::warn("Show recording not imported ({$reason}): {$path}");

            return ['ok' => false, 'rejected' => $reason];
        }

        $instance = $instanceId > 0 ? CcShowInstancesQuery::create()->findPk($instanceId) : null;
        if ($instance !== null && (int) $instance->getDbRecordedFile() > 0) {
            $existing = CcFilesQuery::create()->findPk((int) $instance->getDbRecordedFile());
            if ($existing !== null) {
                return ['ok' => true, 'skipped' => 'already-linked', 'file_id' => (int) $existing->getDbId()];
            }
        }

        $md5 = (string) @md5_file($path);
        $dupId = $md5 !== '' ? self::findByMd5($md5) : 0;
        if ($dupId > 0) {
            if ($instance !== null) {
                self::link($instance, $dupId);
            }

            return ['ok' => true, 'skipped' => 'duplicate', 'file_id' => $dupId];
        }

        [$title, $artist] = self::labels($instance, $path);
        $trackTypeId = self::trackTypeId();
        $originalFilename = basename($path);

        $tagged = self::taggedCopy($path, $title, $artist);
        if ($tagged !== null) {
            $result = CcFiles::createFromRecording($tagged, $originalFilename, $trackTypeId, false);
        } else {
            $result = CcFiles::createFromRecording($path, $originalFilename, $trackTypeId, true);
        }
        $fileId = (int) ($result['id'] ?? 0);
        if ($fileId <= 0) {
            return ['ok' => false, 'rejected' => 'import-failed'];
        }

        // the pending row carries the labels until the analyzer confirms them
        $file = CcFilesQuery::create()->findPk($fileId);
        if ($file !== null) {
            $file->setDbTrackTitle($title);
            $file->setDbArtistName($artist);
            $file->setDbAlbumTitle(self::ALBUM);
            $file->save();
        }
        // the library copy is tagged (other bytes): remember the source md5 so
        // a repeated report of the same recording is recognised
        if ($md5 !== '') {
            self::setSourceMd5($fileId, $md5);
        }
        if ($instance !== null) {
            self::link($instance, $fileId);
        }
        Logging::info("Show recording imported as file {$fileId} (instance {$instanceId}): {$path}");

        return ['ok' => true, 'file_id' => $fileId, 'title' => $title];
    }

    /**
     * Id of a library row that already holds this recording (its own md5 or
     * the md5 of the source it was tagged from); pending rows count, failed
     * imports do not.  0 when none.
     */
    private static function findByMd5(string $md5): int
    {
        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        $stmt = $con->prepare('SELECT id FROM cc_files WHERE (md5 = :m OR source_md5 = :m) AND import_status <> :failed ORDER BY id LIMIT 1');
        $stmt->execute([':m' => strtolower($md5), ':failed' => CcFiles::IMPORT_STATUS_FAILED]);
        $id = $stmt->fetchColumn();

        return $id ? (int) $id : 0;
    }

    private static function setSourceMd5(int $fileId, string $md5): void
    {
        try {
            $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
            $stmt = $con->prepare('UPDATE cc_files SET source_md5 = :m WHERE id = :id');
            $stmt->execute([':m' => strtolower($md5), ':id' => $fileId]);
        } catch (Exception $e) {
            Logging::warn('ShowRecordingService::setSourceMd5: ' . $e->getMessage());
        }
    }

    /** Why the reported path may not be imported, null when it may. */
    public static function rejectReason(string $path): ?string
    {
        $path = str_replace('\\', '/', trim($path));
        if ($path === '' || !is_file($path)) {
            return 'no-such-file';
        }
        if ((int) @filesize($path) <= 0) {
            return 'empty-file';
        }
        $ext = strtolower((string) pathinfo($path, PATHINFO_EXTENSION));
        if (!in_array($ext, self::EXTENSIONS, true)) {
            return 'bad-extension';
        }
        $folder = str_replace('\\', '/', trim((string) Application_Model_Preference::getLocalRecordingFolder()));
        if ($folder === '') {
            return 'no-recording-folder';
        }
        $real = str_replace('\\', '/', (string) realpath($path));
        $rootReal = str_replace('\\', '/', (string) realpath($folder));
        if ($real === '' || $rootReal === '') {
            return 'outside-recording-folder';
        }
        $rootReal = rtrim($rootReal, '/') . '/';
        // Windows paths: case-insensitive
        if (strncasecmp($real, $rootReal, strlen($rootReal)) !== 0) {
            return 'outside-recording-folder';
        }

        return null;
    }

    /** [title, artist] for the library row. */
    private static function labels(?CcShowInstances $instance, string $path): array
    {
        $show = '';
        $when = '';
        if ($instance !== null) {
            try {
                $show = (string) $instance->getCcShow()->getDbName();
                $starts = $instance->getDbStarts(null);
                if ($starts instanceof DateTime) {
                    $local = clone $starts;
                    $local->setTimezone(new DateTimeZone(Application_Model_Preference::GetDefaultTimezone()));
                    $when = $local->format('Y-m-d H:i');
                }
            } catch (Exception $e) {
                Logging::warn('ShowRecordingService::labels: ' . $e->getMessage());
            }
        }
        $stem = (string) pathinfo($path, PATHINFO_FILENAME);
        if ($show === '') {
            // "<YYYY-MM-DD HH-MM-SS> - <show>" from the recorder's file name
            $show = preg_replace('/^\d{4}-\d{2}-\d{2} \d{2}-\d{2}(-\d{2})? - /', '', $stem) ?: $stem;
        }
        if ($when === '' && preg_match('/^(\d{4}-\d{2}-\d{2}) (\d{2})-(\d{2})/', $stem, $m)) {
            $when = "{$m[1]} {$m[2]}:{$m[3]}";
        }
        $title = trim($show . ' ' . $when);

        return [$title !== '' ? $title : $stem, $show !== '' ? $show : $stem];
    }

    /** The "Recordings" track type, created on first use. */
    public static function trackTypeId(): int
    {
        $tt = CcTracktypesQuery::create()->filterByDbCode(self::TRACK_TYPE_CODE)->findOne();
        if ($tt === null) {
            $tt = new CcTracktypes();
            $tt->setDbCode(self::TRACK_TYPE_CODE);
            $tt->setDbTypeName(self::TRACK_TYPE_NAME);
            $tt->setDbDescription('Per-show recordings copied into the library');
            $tt->setDbVisibility(true);
            $tt->save();
            // RASTATIME 2026-10-21 - a recording slice stands in for a live row:
            // its neighbours overlap it by the show hand-over crossfade (1 s),
            // not the 3 s track crossfade, so a repeat keeps the original's
            // length (Scheduler::crossfadeOverlapBetween takes the smaller
            // side).  Adjustable under Settings -> Track Types.
            try {
                $type = new Application_Model_Tracktype((int) $tt->getDbId());
                $type->setCrossfadeDuration(Application_Model_Preference::GetDefaultShowCrossfadeDuration());
                $type->save();
            } catch (Exception $e) {
                Logging::warn('ShowRecordingService: crossfade of the Recordings type not set: ' . $e->getMessage());
            }
            Logging::info('Track type "' . self::TRACK_TYPE_NAME . '" created for show recordings');
        }

        return (int) $tt->getDbId();
    }

    /**
     * A copy of $path in the temp dir with fresh tags (stream copy, no
     * re-encode).  null when ffmpeg is missing or fails - the caller then
     * imports the original.
     */
    private static function taggedCopy(string $path, string $title, string $artist): ?string
    {
        $ext = strtolower((string) pathinfo($path, PATHINFO_EXTENSION));
        $tmp = rtrim(sys_get_temp_dir(), '/\\') . '/rt-recording-' . bin2hex(random_bytes(4)) . '.' . $ext;
        $year = preg_match('/(\d{4})-\d{2}-\d{2}/', $title, $m) ? $m[1] : date('Y');
        $cmd = escapeshellarg(Application_Model_CuePoints::ffmpegBinary())
            . ' -y -nostdin -hide_banner -loglevel error -i ' . escapeshellarg($path)
            . ' -map 0:a -c copy -map_metadata -1'
            . ' -metadata title=' . escapeshellarg($title)
            . ' -metadata artist=' . escapeshellarg($artist)
            . ' -metadata album=' . escapeshellarg(self::ALBUM)
            . ' -metadata date=' . escapeshellarg($year)
            . ' ' . escapeshellarg($tmp) . ' 2>&1';
        $out = [];
        $code = 1;
        @exec($cmd, $out, $code);
        if ($code !== 0 || !is_file($tmp) || (int) @filesize($tmp) <= 0) {
            Logging::warn('ShowRecordingService: ffmpeg tagging failed (' . $code . '): ' . implode(' ', $out));
            @unlink($tmp);

            return null;
        }

        return $tmp;
    }

    private static function link(CcShowInstances $instance, int $fileId): void
    {
        try {
            $si = new Application_Model_ShowInstance((int) $instance->getDbId());
            $si->setRecordedFile($fileId);
        } catch (Exception $e) {
            Logging::warn('ShowRecordingService::link: ' . $e->getMessage());
        }
    }
}
