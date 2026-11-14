<?php

class PodcastEpisodeNotFoundException extends Exception {}

class DuplicatePodcastEpisodeException extends Exception {}

class Application_Service_PodcastEpisodeService extends Application_Service_ThirdPartyCeleryService implements Publish
{
    /**
     * Arbitrary constant identifiers for the internal tasks array.
     */
    public const DOWNLOAD = 'download';

    public const PENDING_EPISODE_TIMEOUT_SECONDS = 900;

    /**
     * @var string service name to store in ThirdPartyTrackReferences database
     */
    protected static $_SERVICE_NAME = PODCAST_SERVICE_NAME;  // Service name constant from constants.php

    /**
     * @var string exchange name for Podcast tasks
     */
    protected static $_CELERY_EXCHANGE_NAME = 'podcast';

    /**
     * @var array map of constant identifiers to Celery task names
     */
    protected static $_CELERY_TASKS = [
        self::DOWNLOAD => 'podcast-download',
    ];

    private static $privateFields = [
        'id',
    ];

    /**
     * Utility function to import and download a single episode.
     *
     * @param int   $podcastId ID of the podcast the episode should belong to
     * @param array $episode   array of episode data to store
     *
     * @return PodcastEpisodes the stored PodcastEpisodes object
     */
    public function importEpisode($podcastId, $episode)
    {
        $e = $this->addPlaceholder($podcastId, $episode);
        $p = $e->getPodcast();
        $this->_download($e->getDbId(), $e->getDbDownloadUrl(), $p->getDbTitle(), $this->_getAlbumOverride($p), $episode['title']);

        return $e;
    }

    /**
     * Given an array of episodes, store them in the database as placeholder objects until
     * they can be processed by Celery.
     *
     * @param int   $podcastId Podcast object identifier
     * @param array $episodes  array of podcast episodes
     *
     * @return array the stored PodcastEpisodes objects
     */
    public function addPodcastEpisodePlaceholders($podcastId, $episodes)
    {
        $storedEpisodes = [];
        foreach ($episodes as $episode) {
            try {
                $e = $this->addPlaceholder($podcastId, $episode);
            } catch (DuplicatePodcastEpisodeException $ex) {
                Logging::warn($ex->getMessage());

                continue;
            }
            array_push($storedEpisodes, $e);
        }

        return $storedEpisodes;
    }

    /**
     * Given an episode, store it in the database as a placeholder object until
     * it can be processed by Celery.
     *
     * @param int   $podcastId Podcast object identifier
     * @param array $episode   array of podcast episode data
     *
     * @return PodcastEpisodes the stored PodcastEpisodes object
     *
     * @throws DuplicatePodcastEpisodeException
     */
    public function addPlaceholder($podcastId, $episode)
    {
        $existingEpisode = PodcastEpisodesQuery::create()->findOneByDbEpisodeGuid($episode['guid']);
        if (!empty($existingEpisode)) {
            throw new DuplicatePodcastEpisodeException(sprintf("Episode already exists for podcast: %s, guid: %s\n", $episode['podcast_id'], $episode['guid']));
        }
        // We need to check whether the array is parsed directly from the SimplePie
        // feed object, or whether it's passed in as json
        $enclosure = $episode['enclosure'];
        $url = $enclosure instanceof SimplePie_Enclosure ? $enclosure->get_link() : $enclosure['link'];

        return $this->_buildEpisode($podcastId, $url, $episode['guid'], $episode['pub_date'], $episode['title'], $episode['description']);
    }

    /**
     * Given episode parameters, construct and store a basic PodcastEpisodes object.
     *
     * @param int    $podcastId       the podcast the episode belongs to
     * @param string $url             the download URL for the episode
     * @param string $guid            the unique id for the episode. Often the same as the download URL
     * @param string $publicationDate the publication date of the episode
     * @param string $title           the title of the episode
     * @param string $description     the description of the epsiode
     *
     * @return PodcastEpisodes the newly created PodcastEpisodes object
     *
     * @throws Exception
     * @throws PropelException
     */
    private function _buildEpisode($podcastId, $url, $guid, $publicationDate, $title = null, $description = null)
    {
        $e = new PodcastEpisodes();
        $e->setDbPodcastId($podcastId);
        $e->setDbDownloadUrl($url);
        $e->setDbEpisodeGuid($guid);
        $e->setDbPublicationDate($publicationDate);
        $e->setDbEpisodeTitle($title);
        $e->setDbEpisodeDescription($description);
        $e->save();

        return $e;
    }

    /**
     * Given an array of episodes, extract the IDs and download URLs and send them to Celery.
     *
     * @param array $episodes array of podcast episodes
     */
    public function downloadEpisodes($episodes)
    {
        /** @var PodcastEpisodes $episode */
        foreach ($episodes as $episode) {
            $podcast = $episode->getPodcast();
            $guid = (string) $episode->getDbEpisodeGuid();
            $result = $this->_download($episode->getDbId(), $episode->getDbDownloadUrl(), $podcast->getDbTitle(), $this->_getAlbumOverride($podcast), $episode->getDbEpisodeTitle());
            // RASTATIME 2026-10-08 - a failure becomes a preflight warning
            // (dashboard banner + System Status); a later success clears it
            if ($result['ok']) {
                Application_Model_PodcastDownloadFailures::clear($guid);
            } else {
                Application_Model_PodcastDownloadFailures::record(
                    $podcast->getDbId(), $podcast->getDbTitle(), $guid, $episode->getDbEpisodeTitle(), $result['error']
                );
            }
        }
    }

    /**
     * check if there is a podcast specific album override.
     *
     * @param object $podcast podcast object
     *
     * @return bool
     */
    private function _getAlbumOverride($podcast)
    {
        $override = Application_Model_Preference::GetPodcastAlbumOverride();
        $podcast_override = $podcast->toArray();
        $podcast_override = $podcast_override['DbAlbumOverride'];
        if ($podcast_override) {
            $override = $podcast_override;
        }

        return $override;
    }

    /**
     * Download a podcast episode by calling the Python API directly.
     *
     * T-PODCAST-1: Replaces the defunct Celery/RabbitMQ dispatch chain.
     * The API endpoint (POST /api/v2/podcast-episodes/{id}/download) fetches
     * the audio file, embeds metadata via mutagen, uploads it to /rest/media,
     * and updates podcast_episodes.file_id — all synchronously.
     *
     * @param int        $id             episode unique ID
     * @param string     $url            download url (used by the API via DB lookup)
     * @param string     $title          podcast title (used by the API via DB lookup)
     * @param bool       $album_override album-override flag (used by the API via DB lookup)
     * @param null|mixed $track_title    episode title (used by the API via DB lookup)
     *
     * @return array{ok: bool, error: string} RASTATIME 2026-10-08
     */
    private function _download($id, $url, $title, $album_override, $track_title = null)
    {
        $config  = Config::getConfig();
        $apiKey  = $config['apiKey'][0];
        $apiUrl  = 'http://localhost:8765/api/v2/podcast-episodes/' . intval($id) . '/download';

        $ch = curl_init($apiUrl);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => '',
            CURLOPT_HTTPHEADER     => ['Authorization: Api-Key ' . $apiKey],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 300,  // 5 minutes — large episodes may take a while
        ]);

        $response  = curl_exec($ch);
        $httpCode  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlError = curl_error($ch);
        curl_close($ch);

        if ($response === false || $httpCode >= 400) {
            Logging::error(
                "podcast_download: API call failed for episode {$id}. "
                . "HTTP {$httpCode}. cURL: {$curlError}. Response: {$response}"
            );
            $decoded = is_string($response) ? json_decode($response, true) : null;
            $reason = $response === false
                ? ('API unreachable: ' . $curlError)
                : ('HTTP ' . $httpCode . (is_array($decoded) && isset($decoded['error']) ? ': ' . $decoded['error'] : ''));

            // RASTATIME 2026-05-17 — without this cleanup the
            // podcast_episodes placeholder row that addPlaceholder()
            // just inserted stays in the DB with file_id IS NULL,
            // and the UI's _getImportedPodcastEpisodeArray() reports
            // ingested=-1 (pending spinner) indefinitely.  The
            // operator's only recourse was to delete the episode by
            // hand from the database.  Removing the placeholder on
            // failure flips the UI back to "not imported" so the
            // operator can simply click Download again.  Episodes
            // that previously succeeded (file_id IS NOT NULL) are
            // never touched — this is a no-op for them.
            try {
                $stuck = PodcastEpisodesQuery::create()
                    ->filterByDbId((int) $id)
                    ->filterByDbFileId(null, Criteria::ISNULL)
                    ->findOne();
                if ($stuck !== null) {
                    Logging::info(
                        "podcast_download: removing stuck placeholder "
                        . "for episode {$id} so the UI exits pending state"
                    );
                    $stuck->delete();
                }
            } catch (Exception $e) {
                Logging::warn(
                    "podcast_download: could not clean up placeholder for "
                    . "episode {$id}: " . $e->getMessage()
                );
            }

            return ['ok' => false, 'error' => $reason];
        }

        Logging::info("podcast_download: episode {$id} imported successfully (HTTP {$httpCode})");

        return ['ok' => true, 'error' => ''];
    }

    /**
     * Update a ThirdPartyTrackReferences object for a completed upload.
     *
     * @param $task      CeleryTasks the completed CeleryTasks object
     * @param $episodeId int         PodcastEpisodes identifier
     * @param $episode   stdClass    simple object containing Podcast episode information
     * @param $status    string      Celery task status
     *
     * @return ThirdPartyTrackReferences the updated ThirdPartyTrackReferences object
     *
     * @throws Exception
     * @throws PropelException
     */
    public function updateTrackReference($task, $episodeId, $episode, $status)
    {
        $ref = parent::updateTrackReference($task, $episodeId, $episode, $status);
        $ref->setDbForeignId($episode->episodeid)->save();
        $dbEpisode = PodcastEpisodesQuery::create()->findOneByDbId($episode->episodeid);

        try {
            // If the placeholder for the episode is somehow removed, return with a warning
            if (!$dbEpisode) {
                Logging::warn("Celery task {$task} episode {$episode->episodeid} unsuccessful: episode placeholder removed");

                return $ref;
            }

            // Even if the task itself succeeds, the download could have failed, so check the status
            if ($status == CELERY_SUCCESS_STATUS && $episode->status == 1) {
                $dbEpisode->setDbFileId($episode->fileid)->save();
            } else {
                Logging::warn("Celery task {$task} episode {$episode->episodeid} unsuccessful with message {$episode->error}");
                $dbEpisode->delete();
            }
        } catch (Exception $e) {
            $dbEpisode->delete();
            Logging::warn("Catastrophic failure updating from task {$task}, recovering by deleting episode row.\n
                           This can occur if the episode's corresponding CcFile is deleted before being processed.");
        }

        return $ref;
    }

    /**
     * RASTATIME 2026-11-14 - "published until" (migration 0084, option B):
     * podcast_episodes.published_until, NULL = no end.  The episode stays
     * published through that day (station time zone); StationPodcastExpiryTask
     * unpublishes it after midnight like the Unpublish button, so feed,
     * download and public page drop it together.  Propel does not know the
     * column: reads go through to_jsonb (NULL before the migration), writes
     * check the column first.
     */
    public const UNTIL_COLUMN = 'published_until';

    /** @var null|bool */
    private static $untilReady;

    /** Whether migration 0084 ran (cached per process once true). */
    public static function publishedUntilReady(): bool
    {
        if (self::$untilReady !== true) {
            self::$untilReady = (bool) Application_Common_Database::prepareAndExecute(
                "SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'podcast_episodes' AND column_name = :c",
                [':c' => self::UNTIL_COLUMN],
                Application_Common_Database::COLUMN
            );
        }

        return self::$untilReady;
    }

    /** Today in the station time zone, YYYY-MM-DD. */
    public static function stationToday(): string
    {
        try {
            $tz = new DateTimeZone((string) Application_Model_Preference::GetDefaultTimezone());
        } catch (Exception $e) {
            $tz = new DateTimeZone(date_default_timezone_get());
        }

        return (new DateTime('now', $tz))->format('Y-m-d');
    }

    /**
     * '' / null = no end; otherwise a real YYYY-MM-DD date, today or later
     * (station time zone).
     *
     * @param mixed $value
     *
     * @throws InvalidArgumentException with a translated message
     */
    public static function normalizeUntil($value): ?string
    {
        $v = trim((string) $value);
        if ($v === '') {
            return null;
        }
        $d = DateTime::createFromFormat('!Y-m-d', $v);
        if (!$d || $d->format('Y-m-d') !== $v) {
            throw new InvalidArgumentException(_('Please enter the date as YYYY-MM-DD.'));
        }
        if ($v < self::stationToday()) {
            throw new InvalidArgumentException(_('The date lies in the past.'));
        }

        return $v;
    }

    /** The "published until" date of the file's station episode, or null. */
    public function getPublishedUntil($fileId): ?string
    {
        $v = Application_Common_Database::prepareAndExecute(
            "SELECT to_jsonb(pe) ->> 'published_until' FROM podcast_episodes pe
              WHERE pe.podcast_id = :p AND pe.file_id = :f LIMIT 1",
            [':p' => (int) Application_Model_Preference::getStationPodcastId(), ':f' => (int) $fileId],
            Application_Common_Database::COLUMN
        );

        return ($v === false || $v === null || $v === '') ? null : (string) $v;
    }

    /**
     * Set (or clear with null) the date of the file's station episode.
     *
     * @throws DomainException when a date is given before migration 0084
     */
    public function setPublishedUntil($fileId, ?string $until): void
    {
        if (!self::publishedUntilReady()) {
            if ($until === null) {
                return;
            }

            throw new DomainException(_('"Published until" needs the database update 0084 first.'));
        }
        Application_Common_Database::prepareAndExecute(
            'UPDATE podcast_episodes SET published_until = CAST(:u AS date)
              WHERE podcast_id = :p AND file_id = :f',
            [':u' => $until, ':p' => (int) Application_Model_Preference::getStationPodcastId(), ':f' => (int) $fileId],
            Application_Common_Database::EXECUTE
        );
    }

    /**
     * Change the date of an already published track (dialog "Save date").
     *
     * @param int         $fileId
     * @param null|string $until  normalised (normalizeUntil)
     */
    public function update($fileId, $until = null)
    {
        if (!$this->getPublishStatus($fileId)) {
            throw new DomainException(_('This track is no longer published.'));
        }
        $this->setPublishedUntil($fileId, $until);
    }

    /**
     * StationPodcastExpiryTask: unpublish every station episode whose
     * "published until" day lies before today (station time zone) - each
     * through Propel like the Unpublish button, one log line each.  "Before
     * today", not "yesterday", so a missed run is caught up.
     *
     * @return int episodes unpublished
     */
    public static function expireStationEpisodes(): int
    {
        if (!self::publishedUntilReady()) {
            return 0;
        }
        $today = self::stationToday();
        $rows = Application_Common_Database::prepareAndExecute(
            'SELECT id, file_id, published_until::text AS until, episode_title
               FROM podcast_episodes
              WHERE podcast_id = :p AND published_until IS NOT NULL AND published_until < CAST(:t AS date)
              ORDER BY id',
            [':p' => (int) Application_Model_Preference::getStationPodcastId(), ':t' => $today],
            Application_Common_Database::ALL
        );
        $done = 0;
        foreach ($rows as $r) {
            $episode = PodcastEpisodesQuery::create()->findPk((int) $r['id']);
            if ($episode === null) {
                continue;
            }
            $episode->delete();
            ++$done;
            Logging::info(sprintf(
                'StationPodcastExpiryTask: unpublished episode %d (file %d, "%s") - published until %s, today %s',
                (int) $r['id'],
                (int) $r['file_id'],
                (string) $r['episode_title'],
                (string) $r['until'],
                $today
            ));
        }

        return $done;
    }

    /**
     * Publish the file with the given file ID to the station podcast.
     *
     * @param int         $fileId ID of the file to be published
     * @param null|string $until  RASTATIME 2026-11-14 - last day published
     *                            (normalised, see normalizeUntil), null = no end
     */
    public function publish($fileId, $until = null)
    {
        // a date before migration 0084 is refused before anything is written
        if ($until !== null && !self::publishedUntilReady()) {
            throw new DomainException(_('"Published until" needs the database update 0084 first.'));
        }
        $id = Application_Model_Preference::getStationPodcastId();
        $url = $guid = Config::getPublicUrl() . "rest/media/{$fileId}/download";
        if (!PodcastEpisodesQuery::create()
            ->filterByDbPodcastId($id)
            ->findOneByDbFileId($fileId)) {  // Don't allow duplicate episodes
            // RASTATIME 2026-05-18 — fill episode_title and
            // episode_description from cc_files.  Both columns are
            // NOT NULL in the podcast_episodes schema, but the
            // upstream publish() path passed nulls to _buildEpisode,
            // so every "Publish to My Podcast" click produced a
            // SQLSTATE[23502] NOT NULL violation and HTTP 400 with
            // no episode created.  Fall back to the file's stored
            // name if track_title is empty, and to an empty string
            // for description (the column is NOT NULL but allows '').
            $file = CcFilesQuery::create()->findPk($fileId);
            $title = '';
            $description = '';
            if ($file !== null) {
                $title = (string) ($file->getDbTrackTitle() ?: $file->getDbName());
                $description = (string) ($file->getDbDescription() ?: '');
            }
            if ($title === '') {
                // Last-resort fallback: a non-empty title is required.
                $title = 'Track ' . $fileId;
            }
            // RASTATIME 2026-11-14 - episode and date together or neither
            $con = Propel::getConnection(PodcastEpisodesPeer::DATABASE_NAME);
            $con->beginTransaction();

            try {
                $e = $this->_buildEpisode($id, $url, $guid, date('r'), $title, $description);
                $e->setDbFileId($fileId)->save($con);
                if ($until !== null) {
                    $this->setPublishedUntil($fileId, $until);
                }
                $con->commit();
            } catch (Throwable $t) {
                $con->rollBack();

                throw $t;
            }
        }
    }

    /**
     * Unpublish the file with the given file ID from the station podcast.
     *
     * @param int $fileId ID of the file to be unpublished
     */
    public function unpublish($fileId)
    {
        $id = Application_Model_Preference::getStationPodcastId();
        // RASTATIME 2026-11-14 - already gone (the expiry task may have
        // unpublished it while the dialog was open): nothing to do
        $episode = PodcastEpisodesQuery::create()
            ->filterByDbPodcastId($id)
            ->findOneByDbFileId($fileId);
        if ($episode !== null) {
            $episode->delete();
        }
    }

    /**
     * Fetch the publication status for the file with the given ID.
     *
     * @param int $fileId the ID of the file to check
     *
     * @return int 1 if the file has been published,
     *             0 if the file has yet to be published,
     *             -1 if the file is in a pending state,
     *             2 if the source is unreachable (disconnected)
     */
    public function getPublishStatus($fileId)
    {
        $stationPodcast = StationPodcastQuery::create()
            ->findOneByDbPodcastId(Application_Model_Preference::getStationPodcastId());

        return (int) $stationPodcast->hasEpisodeForFile($fileId);
    }

    /**
     * Find any episode placeholders that have been stuck pending (empty file ID) for over
     * PENDING_EPISODE_TIMEOUT_SECONDS.
     *
     * @see Application_Service_PodcastEpisodeService::PENDING_EPISODE_TIMEOUT_SECONDS
     *
     * @return array the episode imports stuck in pending
     */
    public static function getStuckPendingImports()
    {
        $timeout = gmdate(DEFAULT_TIMESTAMP_FORMAT, intval(microtime(true)) - self::PENDING_EPISODE_TIMEOUT_SECONDS);
        $episodes = PodcastEpisodesQuery::create()
            ->filterByDbFileId()
            ->find();
        $stuckImports = [];
        foreach ($episodes as $episode) {
            $ref = ThirdPartyTrackReferencesQuery::create()
                ->findOneByDbForeignId(strval($episode->getDbId()));
            if (!empty($ref)) {
                $task = CeleryTasksQuery::create()
                    ->filterByDbDispatchTime($timeout, Criteria::LESS_EQUAL)
                    ->findOneByDbTrackReference($ref->getDbId());
                if (!empty($task)) {
                    array_push($stuckImports, $episode);
                }
            }
        }

        return $stuckImports;
    }

    /**
     * @param mixed $episodeId
     *
     * @return array
     *
     * @throws PodcastEpisodeNotFoundException
     */
    public static function getPodcastEpisodeById($episodeId)
    {
        $episode = PodcastEpisodesQuery::create()->findPk($episodeId);
        if (!$episode) {
            throw new PodcastEpisodeNotFoundException();
        }

        return $episode->toArray(BasePeer::TYPE_FIELDNAME);
    }

    /**
     * Returns an array of Podcast episodes, with the option to paginate the results.
     *
     * @param int    $offset
     * @param int    $limit
     * @param string $sortColumn
     * @param string $sortDir    "ASC" || "DESC"
     * @param mixed  $podcastId
     *
     * @return array
     *
     * @throws PodcastNotFoundException
     */
    public function getPodcastEpisodes(
        $podcastId,
        $offset = 0,
        $limit = 10,
        $sortColumn = PodcastEpisodesPeer::PUBLICATION_DATE,
        $sortDir = 'ASC'
    ) {
        $podcast = PodcastQuery::create()->findPk($podcastId);
        if (!$podcast) {
            throw new PodcastNotFoundException();
        }

        $sortDir = ($sortDir === 'DESC') ? $sortDir = Criteria::DESC : Criteria::ASC;
        $isStationPodcast = $podcastId == Application_Model_Preference::getStationPodcastId();

        $episodes = PodcastEpisodesQuery::create()
            ->filterByDbPodcastId($podcastId);
        if ($isStationPodcast && $limit != 0) {
            $episodes = $episodes->setLimit($limit);
        }
        // XXX: We should maybe try to alias this so we don't pass CcFiles as an array key to the frontend.
        //      It would require us to iterate over all the episodes and change the key for the response though...
        $episodes = $episodes->joinWith('PodcastEpisodes.CcFiles', Criteria::LEFT_JOIN)
            ->setOffset($offset)
            ->orderBy($sortColumn, $sortDir)
            ->find();

        return $isStationPodcast ? $this->_getStationPodcastEpisodeArray($episodes)
            : $this->_getImportedPodcastEpisodeArray($podcast, $episodes);
    }

    /**
     * Given an array of PodcastEpisodes objects from the Station Podcast,
     * convert the episode data into array form.
     *
     * @param array $episodes array of PodcastEpisodes to convert
     *
     * @return array
     */
    private function _getStationPodcastEpisodeArray($episodes)
    {
        $episodesArray = [];
        // RASTATIME 2026-11-14 - "published until" for the My Podcast list
        // (one query; NULL before migration 0084)
        $until = [];
        foreach (Application_Common_Database::prepareAndExecute(
            "SELECT pe.id, to_jsonb(pe) ->> 'published_until' AS until FROM podcast_episodes pe
              WHERE pe.podcast_id = :p",
            [':p' => (int) Application_Model_Preference::getStationPodcastId()],
            Application_Common_Database::ALL
        ) as $r) {
            $until[(int) $r['id']] = $r['until'];
        }
        foreach ($episodes as $episode) {
            /** @var PodcastEpisodes $episode */
            $episodeArr = $episode->toArray(BasePeer::TYPE_FIELDNAME, true, [], true);
            $episodeArr['published_until'] = $until[(int) $episode->getDbId()] ?? null;
            array_push($episodesArray, $episodeArr);
        }

        return $episodesArray;
    }

    /**
     * Given an ImportedPodcast object and an array of stored PodcastEpisodes objects,
     * fetch all episodes from the podcast RSS feed, and serialize them in a readable form.
     *
     * TODO: there's definitely a better approach than this... we should be trying to create
     *       PodcastEpisdoes objects instead of our own arrays
     *
     * @param ImportedPodcast $podcast  Podcast object to fetch the episodes for
     * @param array           $episodes array of PodcastEpisodes objects to
     *
     * @return array array of episode data
     *
     * @throws CcFiles/RastatimeFileNotFoundException
     */
    public function _getImportedPodcastEpisodeArray($podcast, $episodes)
    {
        $rss = Application_Service_PodcastService::getPodcastFeed($podcast->getDbUrl());
        $episodeIds = [];
        $episodeFiles = [];
        foreach ($episodes as $e) {
            // @var PodcastEpisodes $e
            array_push($episodeIds, $e->getDbEpisodeGuid());
            $episodeFiles[$e->getDbEpisodeGuid()] = $e->getDbFileId();
        }

        $episodesArray = [];
        foreach ($rss->get_items() as $item) {
            /** @var SimplePie_Item $item */
            // If the enclosure is empty or has not URL, this isn't a podcast episode (there's no audio data)
            // technically podcasts shouldn't have multiple enclosures but often CMS add non-audio files
            $enclosure = $item->get_enclosure();
            $url = $enclosure instanceof SimplePie_Enclosure ? $enclosure->get_link() : $enclosure['link'];
            if (empty($url)) {
                continue;
            }
            // next we check and see if the enclosure is not an audio file - this can happen from improperly
            // formatted podcasts and we instead will search through the enclosures and see if there is an audio item
            // then we pass that on, otherwise we just pass the first item since it is probably an audio file
            if (!(substr($enclosure->get_type(), 0, 5) === 'audio')) {
                // this is a rather hackish way of accessing the enclosures but get_enclosures() didnt detect multiple
                // enclosures at certain points so we search through them and then manually create an enclosure object
                // if we find an audio file in an enclosure and send it off
                Logging::info('found a non audio');
                $testenclosures = $enclosures = $item->get_item_tags(SIMPLEPIE_NAMESPACE_RSS_20, 'enclosure');
                Logging::info($testenclosures);
                // we need to check if this is an array otherwise sizeof will fail and stop this whole script
                if (is_array($testenclosures)) {
                    $numenclosures = count($testenclosures);
                    // now we loop through and look for a audio file and then stop the loop at the first one we find
                    for ($i = 0; $i < $numenclosures + 1; ++$i) {
                        $enclosure_attribs = array_values($testenclosures[$i]['attribs'])[0];
                        if (stripos($enclosure_attribs['type'], 'audio') !== false) {
                            $url = $enclosure_attribs['url'];
                            $enclosure = new SimplePie_Enclosure($enclosure_attribs['url'], $enclosure_attribs['type'], $length = $enclosure_attribs['length']);

                            break;
                        }
                        // if we didn't find an audio file we need to continue because there were no audio item enclosures
                        // so this should keep it from showing items without audio items on the episodes list
                        if ($i = $numenclosures) {
                            continue;
                        }
                    }
                } else {
                    continue;
                }
            } else {
                $enclosure = $item->get_enclosure();
            }
            // Logging::info($enclosure);
            $itemId = $item->get_id();
            $ingested = in_array($itemId, $episodeIds) ? (empty($episodeFiles[$itemId]) ? -1 : 1) : 0;
            $file = $ingested > 0 && !empty($episodeFiles[$itemId]) ?
                CcFiles::getSanitizedFileById($episodeFiles[$itemId]) : [];
            // If the analyzer hasn't finished with the file, leave it as pending
            if (!empty($file) && $file['import_status'] == CcFiles::IMPORT_STATUS_PENDING) {
                $ingested = -1;
            }

            array_push($episodesArray, [
                'podcast_id' => $podcast->getDbId(),
                'guid' => $itemId,
                'ingested' => $ingested,
                // RASTATIME 2026-09-28 - plain text, not SimplePie's HTML-safe
                // output: WordPress feeds carry typographic quotes as
                // HTML entities inside CDATA (&#8222;...&#8220;) and
                // SimplePie's sanitizer escapes the ampersand once more, so
                // "&amp;#8222;" reached episode_title, the track title and
                // the ID3 tag of 20 episodes (seen 2026-09-28).  The library
                // escapes on output, so the stored value must be the text.
                'title' => self::feedPlainText($item->get_title()),
                // From the RSS spec best practices:
                // 'An item's author element provides the e-mail address of the person who wrote the item'
                'author' => $this->_buildAuthorString($item),
                'description' => htmlspecialchars($item->get_description() ?? ''),
                'pub_date' => $item->get_gmdate(),
                'link' => $url,
                'enclosure' => $enclosure,
                'file' => $file,
            ]);
        }

        return $episodesArray;
    }

    /**
     * RASTATIME 2026-09-28 - turn a SimplePie text value into plain UTF-8.
     * SimplePie returns HTML-safe text (ampersands escaped) and feeds may
     * carry HTML entities in the text itself, so the value is decoded
     * until it no longer changes (at most three rounds).
     *
     * @param null|string $text
     *
     * @return string
     */
    public static function feedPlainText($text)
    {
        $value = (string) ($text ?? '');
        for ($round = 0; $round < 3; ++$round) {
            $decoded = html_entity_decode($value, ENT_QUOTES | ENT_HTML5, 'UTF-8');
            if ($decoded === $value) {
                break;
            }
            $value = $decoded;
        }

        return trim($value);
    }

    /**
     * Construct a string representation of the author fields of a SimplePie_Item object.
     *
     * @param SimplePie_Item $item the SimplePie_Item to extract the author data from
     *
     * @return string the string representation of the author data
     */
    private function _buildAuthorString(SimplePie_Item $item)
    {
        $authorString = $author = $item->get_author();
        if (!empty($author)) {
            $authorString = $author->get_email();
            $authorString = empty($authorString) ? $author->get_name() : $authorString;
        }

        return $authorString;
    }

    public function deletePodcastEpisodeById($episodeId)
    {
        $episode = PodcastEpisodesQuery::create()->findByDbId($episodeId);

        if ($episode) {
            $episode->delete();
        } else {
            throw new PodcastEpisodeNotFoundException();
        }
    }

    private function removePrivateFields(&$data)
    {
        foreach (self::$privateFields as $key) {
            unset($data[$key]);
        }
    }
}
