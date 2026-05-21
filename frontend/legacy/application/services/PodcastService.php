<?php

class InvalidPodcastException extends Exception {}

class PodcastNotFoundException extends Exception {}

class Application_Service_PodcastService
{
    // These fields should never be modified with POST/PUT data
    private static $privateFields = [
        'id',
        'url',
        'type',
        'owner',
    ];

    /**
     * Returns parsed rss feed, or false if the given URL cannot be downloaded.
     *
     * @param string $feedUrl String containing the podcast feed URL
     *
     * @return mixed
     */
    public static function getPodcastFeed($feedUrl)
    {
        try {
            $feed = new SimplePie();
            $feed->set_feed_url($feedUrl);
            $feed->enable_cache(false);
            $feed->init();

            return $feed;
        } catch (Exception $e) {
            return false;
        }
    }

    /** Creates a Podcast object from the given podcast URL.
     *  This is used by our Podcast REST API.
     *
     * @param string $feedUrl Podcast RSS Feed Url
     *
     * @return array Podcast Array with a full list of episodes
     *
     * @throws Exception
     * @throws InvalidPodcastException
     */
    public static function createFromFeedUrl($feedUrl)
    {
        // TODO: why is this so slow?
        $rss = self::getPodcastFeed($feedUrl);
        if (!$rss) {
            throw new InvalidPodcastException();
        }
        $rssErr = $rss->error();
        if (!empty($rssErr)) {
            throw new InvalidPodcastException($rssErr);
        }

        // Ensure we are only creating Podcast with the given URL, and excluding
        // any extra data fields that may have been POSTED
        $podcastArray = [];
        $podcastArray['url'] = $feedUrl;

        $podcastArray['title'] = htmlspecialchars($rss->get_title() ?? '');
        $podcastArray['description'] = htmlspecialchars($rss->get_description() ?? '');
        $podcastArray['link'] = htmlspecialchars($rss->get_link() ?? '');
        $podcastArray['language'] = htmlspecialchars($rss->get_language() ?? '');
        $podcastArray['copyright'] = htmlspecialchars($rss->get_copyright() ?? '');

        $author = $rss->get_author();
        $name = empty($author) ? '' : $author->get_name();
        $podcastArray['creator'] = htmlspecialchars($name ?? '');

        $categories = [];
        if (is_array($rss->get_categories())) {
            foreach ($rss->get_categories() as $category) {
                array_push($categories, $category->get_scheme() . ':' . $category->get_term());
            }
        }
        $podcastArray['category'] = htmlspecialchars(implode('', $categories));

        // TODO: put in constants
        $itunesChannel = 'http://www.itunes.com/dtds/podcast-1.0.dtd';

        $itunesSubtitle = $rss->get_channel_tags($itunesChannel, 'subtitle');
        $podcastArray['itunes_subtitle'] = isset($itunesSubtitle[0]['data']) ? $itunesSubtitle[0]['data'] : '';

        $itunesCategory = $rss->get_channel_tags($itunesChannel, 'category');
        $categoryArray = [];
        if (is_array($itunesCategory)) {
            foreach ($itunesCategory as $c => $data) {
                foreach ($data['attribs'] as $attrib) {
                    array_push($categoryArray, $attrib['text']);
                }
            }
        }
        $podcastArray['itunes_category'] = implode(',', $categoryArray);

        $itunesAuthor = $rss->get_channel_tags($itunesChannel, 'author');
        $podcastArray['itunes_author'] = isset($itunesAuthor[0]['data']) ? $itunesAuthor[0]['data'] : '';

        $itunesSummary = $rss->get_channel_tags($itunesChannel, 'summary');
        $podcastArray['itunes_summary'] = isset($itunesSummary[0]['data']) ? $itunesSummary[0]['data'] : '';

        $itunesKeywords = $rss->get_channel_tags($itunesChannel, 'keywords');
        $podcastArray['itunes_keywords'] = isset($itunesKeywords[0]['data']) ? $itunesKeywords[0]['data'] : '';

        $itunesExplicit = $rss->get_channel_tags($itunesChannel, 'explicit');
        $podcastArray['itunes_explicit'] = isset($itunesExplicit[0]['data']) ? $itunesExplicit[0]['data'] : '';

        self::validatePodcastMetadata($podcastArray);

        try {
            // Base class
            $podcast = new Podcast();
            $podcast->fromArray($podcastArray, BasePeer::TYPE_FIELDNAME);
            $podcast->setDbOwner(self::getOwnerId());
            $podcast->save();

            $importedPodcast = new ImportedPodcast();
            $importedPodcast->fromArray($podcastArray, BasePeer::TYPE_FIELDNAME);
            $importedPodcast->setPodcast($podcast);
            $importedPodcast->setDbAutoIngest(true);
            $importedPodcast->save();

            // if the autosmartblock and album override are enabled then create a smartblock and playlist matching this podcast via the album name
            if (Application_Model_Preference::GetPodcastAutoSmartblock() && Application_Model_Preference::GetPodcastAlbumOverride()) {
                self::createPodcastSmartblockAndPlaylist($podcast);
            }

            return $podcast->toArray(BasePeer::TYPE_FIELDNAME);
        } catch (Exception $e) {
            $podcast->delete();

            throw $e;
        }
    }

    /**
     * @param       $title   passed in directly from web UI input
     *                      This will automatically create a smartblock and playlist for this podcast
     * @param mixed $podcast
     */
    public static function createPodcastSmartblockAndPlaylist($podcast, $title = null)
    {
        if (is_array($podcast)) {
            $newpodcast = new Podcast();
            $newpodcast->fromArray($podcast, BasePeer::TYPE_FIELDNAME);
            $podcast = $newpodcast;
        }
        if ($title == null) {
            $title = $podcast->getDbTitle();
        }
        // Base class
        $newBl = new Application_Model_Block();
        $newBl->setCreator(Application_Model_User::getCurrentUser()->getId());
        $newBl->setName($title);
        $newBl->setDescription(_('Auto-generated smartblock for podcast'));
        $newBl->saveType('dynamic');
        // limit the smartblock to 1 item
        $row = new CcBlockcriteria();
        $row->setDbCriteria('limit');
        $row->setDbModifier('items');
        $row->setDbValue(1);
        $row->setDbBlockId($newBl->getId());
        $row->save();

        // sort so that it is the newest item
        $row = new CcBlockcriteria();
        $row->setDbCriteria('sort');
        $row->setDbModifier('N/A');
        $row->setDbValue('newest');
        $row->setDbBlockId($newBl->getId());
        $row->save();

        // match the track by ensuring the album title matches the podcast
        $row = new CcBlockcriteria();
        $row->setDbCriteria('album_title');
        $row->setDbModifier('is');
        $row->setDbValue($title);
        $row->setDbBlockId($newBl->getId());
        $row->save();

        $newPl = new Application_Model_Playlist();
        $newPl->setName($title);
        $newPl->setCreator(Application_Model_User::getCurrentUser()->getId());
        $row = new CcPlaylistcontents();
        $row->setDbBlockId($newBl->getId());
        $row->setDbPlaylistId($newPl->getId());
        $row->setDbType(2);
        $row->save();
    }

    public static function createStationPodcast()
    {
        $podcast = new Podcast();
        $podcast->setDbUrl(Config::getPublicUrl() . 'feeds/station-rss');

        $title = Application_Model_Preference::GetStationName();
        $title = empty($title) ? "My Station's Podcast" : $title;
        $podcast->setDbTitle($title);

        $podcast->setDbDescription(Application_Model_Preference::GetStationDescription());
        $podcast->setDbLink(Config::getPublicUrl());
        $podcast->setDbLanguage(explode('_', Application_Model_Preference::GetLocale())[0]);
        $podcast->setDbCreator(Application_Model_Preference::GetStationName());
        $podcast->setDbOwner(self::getOwnerId());
        $podcast->save();

        $stationPodcast = new StationPodcast();
        $stationPodcast->setPodcast($podcast);
        $stationPodcast->save();

        Application_Model_Preference::setStationPodcastId($podcast->getDbId());
        // Set the download key when we create the station podcast
        // The value is randomly generated in the setter
        Application_Model_Preference::setStationPodcastDownloadKey();

        return $podcast->getDbId();
    }

    // TODO move this somewhere where it makes sense
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

    /**
     * Trims the podcast metadata to fit the table's column max size.
     *
     * @param PodcastArray &$podcastArray
     */
    private static function validatePodcastMetadata(&$podcastArray)
    {
        $podcastTable = PodcastPeer::getTableMap();

        foreach ($podcastArray as $key => &$value) {
            try {
                // Make sure column exists in table
                $columnMaxSize = $podcastTable->getColumn($key)->getSize();
            } catch (PropelException $e) {
                continue;
            }

            if (strlen($value) > $columnMaxSize) {
                $value = substr($value, 0, $podcastTable->getColumn($key)->getSize());
            }
        }
    }

    /**
     * Fetches a Podcast's rss feed and returns all its episodes with
     * the Podcast object.
     *
     * @param mixed $podcastId
     *
     * @return array - Podcast Array with a full list of episodes
     *
     * @throws PodcastNotFoundException
     * @throws InvalidPodcastException
     */
    public static function getPodcastById($podcastId)
    {
        $podcast = PodcastQuery::create()->findPk($podcastId);
        if (!$podcast) {
            throw new PodcastNotFoundException();
        }

        $podcast = $podcast->toArray(BasePeer::TYPE_FIELDNAME);
        $podcast['itunes_explicit'] = ($podcast['itunes_explicit'] == 'yes') ? true : false;

        // RASTATIME 2026-05-17 — embed the list of all enabled cc_track_types
        // rows into the podcast JSON object so the Angular controller can
        // bind the "Track Type" dropdown without a separate REST round-trip
        // AND without relying on a server-rendered <script> tag (which is
        // not executed reliably when the editor HTML is injected via
        // jQuery's .html() inside the tab system).  Field name uses snake
        // case (track_type_options) to match every other field in this
        // podcast payload.
        $podcast['track_type_options'] = [];
        try {
            $tts = Application_Model_Tracktype::getTracktypes();
            // Sort alphabetically by display name so the dropdown matches
            // the Library's Edit-Track-Type dropdown ordering.
            array_multisort(
                array_map(function ($t) { return $t['type_name']; }, $tts),
                SORT_ASC, $tts
            );
            foreach ($tts as $tt) {
                $podcast['track_type_options'][] = [
                    'id'   => (int) $tt['id'],
                    'name' => (string) $tt['type_name'],
                ];
            }
        } catch (Throwable $exc) {
            // Throwable (not just Exception) so PHP 7+ Error instances
            // are also surfaced rather than bubbling up as opaque HTTP
            // 500.  WARN is the right level — an empty dropdown is a
            // degraded UX, not a fatal failure.
            Logging::warn('getPodcastById: could not load track types: ' . $exc->getMessage());
        }

        // RASTATIME 2026-05-16 - Read Podcast Auto-Expiry columns via raw
        // SQL.  Propel ImportedPodcast class is not regenerated for these
        // columns (see schema.xml note), so toArray() above did not
        // include them.  Empty defaults (false / null) so the edit form
        // shows an unchecked checkbox + empty days field for legacy
        // podcasts.  Same situation for default_track_type_id
        // (RASTATIME 2026-05-17, see migration 0050) — read it in the
        // same query.
        $podcast['auto_expiry_enabled'] = false;
        $podcast['auto_expiry_days'] = null;
        $podcast['default_track_type_id'] = null;
        try {
            $con = Propel::getConnection();
            $stmt = $con->prepare(
                'SELECT auto_expiry_enabled, auto_expiry_days,
                        default_track_type_id
                 FROM imported_podcast WHERE podcast_id = :pid'
            );
            $stmt->bindValue(':pid', (int) $podcastId, PDO::PARAM_INT);
            $stmt->execute();
            $row = $stmt->fetch(PDO::FETCH_ASSOC);
            if ($row !== false) {
                // PostgreSQL returns 't'/'f' for BOOLEAN over PDO; coerce.
                $podcast['auto_expiry_enabled'] = ($row['auto_expiry_enabled'] === true
                    || $row['auto_expiry_enabled'] === 't'
                    || $row['auto_expiry_enabled'] === 1
                    || $row['auto_expiry_enabled'] === '1');
                $podcast['auto_expiry_days'] = $row['auto_expiry_days'] === null
                    ? null : (int) $row['auto_expiry_days'];
                $podcast['default_track_type_id'] = $row['default_track_type_id'] === null
                    ? null : (int) $row['default_track_type_id'];
            }
        } catch (Exception $exc) {
            Logging::warn('getPodcastById: could not read auto_expiry / default_track_type: ' . $exc->getMessage());
        }

        return $podcast;
    }

    /**
     * Deletes a Podcast and its podcast episodes.
     *
     * @param mixed $podcastId
     *
     * @throws Exception
     * @throws PodcastNotFoundException
     */
    public static function deletePodcastById($podcastId)
    {
        $podcast = PodcastQuery::create()->findPk($podcastId);
        if ($podcast) {
            $podcast->delete();

            // FIXME: I don't think we should be able to delete the station podcast...
            if ($podcastId == Application_Model_Preference::getStationPodcastId()) {
                Application_Model_Preference::setStationPodcastId(null);
            }
        } else {
            throw new PodcastNotFoundException();
        }
    }

    /**
     * Build a response with podcast data and embedded HTML to load on the frontend.
     *
     * @param int                 $podcastId ID of the podcast to build a response for
     * @param Zend_View_Interface $view      Zend view object to render the response HTML
     *
     * @return array the response array containing the podcast data and editor HTML
     *
     * @throws PodcastNotFoundException
     */
    public static function buildPodcastEditorResponse($podcastId, $view)
    {
        // Check the StationPodcast table rather than checking
        // the station podcast ID key in preferences for extensibility
        $podcast = StationPodcastQuery::create()->findOneByDbPodcastId($podcastId);
        $path = $podcast ? 'podcast/station.phtml' : 'podcast/podcast.phtml';
        $podcast = Application_Service_PodcastService::getPodcastById($podcastId);

        return [
            'podcast' => json_encode($podcast),
            'html' => $view->render($path),
        ];
    }

    /**
     * Updates a Podcast object with the given metadata.
     *
     * @param mixed $podcastId
     * @param mixed $data
     *
     * @return array
     *
     * @throws Exception
     * @throws PodcastNotFoundException
     */
    public static function updatePodcastFromArray($podcastId, $data)
    {
        $podcast = PodcastQuery::create()->findPk($podcastId);
        if (!$podcast) {
            throw new PodcastNotFoundException();
        }

        self::removePrivateFields($data['podcast']);
        self::validatePodcastMetadata($data['podcast']);
        if (array_key_exists('auto_ingest', $data['podcast'])) {
            self::_updateAutoIngestTimestamp($podcast, $data);
        }

        $data['podcast']['itunes_explicit'] = $data['podcast']['itunes_explicit'] ? 'yes' : 'clean';
        $podcast->fromArray($data['podcast'], BasePeer::TYPE_FIELDNAME);
        $podcast->save();

        // RASTATIME 2026-05-16 - Persist Podcast Auto-Expiry columns via
        // raw SQL.  Propel ImportedPodcast class is not regenerated for
        // these columns, so the fromArray() call above silently dropped
        // them.  We clamp days to a sensible range [1, 3650]; the UI's
        // number-input enforces the same.  Empty / null days with
        // enabled=true is treated as 30 days (sensible default rather
        // than refusing to save).
        $autoExpiryEnabled = false;
        $autoExpiryDays = null;
        if (array_key_exists('auto_expiry_enabled', $data['podcast'])) {
            $raw = $data['podcast']['auto_expiry_enabled'];
            // AngularJS sends true/false, but the form also accepts
            // checkbox-on as the string "on" or "1".  Coerce robustly.
            $autoExpiryEnabled = ($raw === true || $raw === 1
                || $raw === 'true' || $raw === '1' || $raw === 'on');
        }
        if (array_key_exists('auto_expiry_days', $data['podcast'])) {
            $rawDays = $data['podcast']['auto_expiry_days'];
            if (is_numeric($rawDays) && (int) $rawDays > 0) {
                $autoExpiryDays = max(1, min(3650, (int) $rawDays));
            }
        }
        if ($autoExpiryEnabled && $autoExpiryDays === null) {
            $autoExpiryDays = 30;
        }

        // RASTATIME 2026-05-17 - Per-podcast default Track-Type.  Same
        // raw-SQL pattern as auto_expiry above (Propel regen would
        // be the alternative).  Empty string from the dropdown means
        // "no default" (NULL); otherwise an integer FK to cc_track_types.
        $defaultTrackTypeId = null;
        if (array_key_exists('default_track_type_id', $data['podcast'])) {
            $rawTt = $data['podcast']['default_track_type_id'];
            if ($rawTt !== null && $rawTt !== '' && is_numeric($rawTt) && (int) $rawTt > 0) {
                $defaultTrackTypeId = (int) $rawTt;
            }
        }

        try {
            $con = Propel::getConnection();
            $stmt = $con->prepare(
                'UPDATE imported_podcast
                 SET auto_expiry_enabled = :enabled,
                     auto_expiry_days = :days,
                     default_track_type_id = :ttid
                 WHERE podcast_id = :pid'
            );
            $stmt->bindValue(':enabled', $autoExpiryEnabled, PDO::PARAM_BOOL);
            if ($autoExpiryDays === null) {
                $stmt->bindValue(':days', null, PDO::PARAM_NULL);
            } else {
                $stmt->bindValue(':days', $autoExpiryDays, PDO::PARAM_INT);
            }
            if ($defaultTrackTypeId === null) {
                $stmt->bindValue(':ttid', null, PDO::PARAM_NULL);
            } else {
                $stmt->bindValue(':ttid', $defaultTrackTypeId, PDO::PARAM_INT);
            }
            $stmt->bindValue(':pid', (int) $podcastId, PDO::PARAM_INT);
            $stmt->execute();
        } catch (Exception $exc) {
            Logging::warn(
                'updatePodcastFromArray: could not persist auto_expiry / default_track_type for podcast '
                . $podcastId . ': ' . $exc->getMessage()
            );
        }

        $result = $podcast->toArray(BasePeer::TYPE_FIELDNAME);
        $result['auto_expiry_enabled'] = $autoExpiryEnabled;
        $result['auto_expiry_days'] = $autoExpiryDays;
        $result['default_track_type_id'] = $defaultTrackTypeId;
        return $result;
    }

    /**
     * Update the automatic ingestion timestamp for the given Podcast.
     *
     * @param Podcast $podcast Podcast object to update
     * @param array   $data    Podcast update data array
     */
    private static function _updateAutoIngestTimestamp($podcast, $data)
    {
        // Get podcast data with lazy loaded columns since we can't directly call getDbAutoIngest()
        $currData = $podcast->toArray(BasePeer::TYPE_FIELDNAME, true);
        // Add an auto-ingest timestamp when turning auto-ingest on
        if ($data['podcast']['auto_ingest'] == 1 && $currData['auto_ingest'] != 1) {
            $data['podcast']['auto_ingest_timestamp'] = gmdate('r');
        }
    }

    private static function removePrivateFields(&$data)
    {
        foreach (self::$privateFields as $key) {
            unset($data[$key]);
        }
    }

    private static function addEscapedChild($node, $name, $value = null, $namespace = null)
    {
        if (empty($value)) {
            return null;
        }
        $child = $node->addChild($name, null, $namespace);
        $child[0] = $value;

        return $child;
    }

    public static function createStationRssFeed()
    {
        $stationPodcastId = Application_Model_Preference::getStationPodcastId();

        try {
            $podcast = PodcastQuery::create()->findPk($stationPodcastId);
            if (!$podcast) {
                throw new PodcastNotFoundException();
            }

            $xml = new SimpleXMLElement('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"/>');

            $channel = $xml->addChild('channel');
            self::addEscapedChild($channel, 'title', $podcast->getDbTitle());
            self::addEscapedChild($channel, 'link', $podcast->getDbLink());
            self::addEscapedChild($channel, 'description', $podcast->getDbDescription());
            self::addEscapedChild($channel, 'language', $podcast->getDbLanguage());
            self::addEscapedChild($channel, 'copyright', $podcast->getDbCopyright());

            $xml->addAttribute('xmlns:xmlns:atom', 'http://www.w3.org/2005/Atom');

            $atomLink = $channel->addChild('xmlns:atom:link');
            $atomLink->addAttribute('href', Config::getPublicUrl() . 'feeds/station-rss');
            $atomLink->addAttribute('rel', 'self');
            $atomLink->addAttribute('type', 'application/rss+xml');

            $imageUrl = Config::getPublicUrl() . 'api/station-logo';
            $image = $channel->addChild('image');
            $image->addChild('title', htmlspecialchars($podcast->getDbTitle() ?? ''));
            self::addEscapedChild($image, 'url', $imageUrl);
            self::addEscapedChild($image, 'link', Config::getPublicUrl());

            $xml->addAttribute('xmlns:xmlns:itunes', ITUNES_XML_NAMESPACE_URL);
            self::addEscapedChild($channel, 'xmlns:itunes:author', $podcast->getDbItunesAuthor());
            self::addEscapedChild($channel, 'xmlns:itunes:keywords', $podcast->getDbItunesKeywords());
            self::addEscapedChild($channel, 'xmlns:itunes:summary', $podcast->getDbItunesSummary());
            self::addEscapedChild($channel, 'xmlns:itunes:subtitle', $podcast->getDbItunesSubtitle());
            self::addEscapedChild($channel, 'xmlns:itunes:explicit', $podcast->getDbItunesExplicit());
            $owner = $channel->addChild('xmlns:itunes:owner');
            self::addEscapedChild($owner, 'xmlns:itunes:name', Application_Model_Preference::GetStationName());
            self::addEscapedChild($owner, 'xmlns:itunes:email', Application_Model_Preference::GetEmail());

            $itunesImage = $channel->addChild('xmlns:itunes:image');
            $itunesImage->addAttribute('href', $imageUrl);

            // Need to split categories into separate tags
            $itunesCategories = explode(',', $podcast->getDbItunesCategory());
            foreach ($itunesCategories as $c) {
                if (!empty($c)) {
                    $category = $channel->addChild('xmlns:itunes:category');
                    $category->addAttribute('text', $c);
                }
            }

            $episodes = PodcastEpisodesQuery::create()->filterByDbPodcastId($stationPodcastId)->find();
            foreach ($episodes as $episode) {
                $item = $channel->addChild('item');
                $publishedFile = CcFilesQuery::create()->findPk($episode->getDbFileId());

                // title
                self::addEscapedChild($item, 'title', $publishedFile->getDbTrackTitle());

                // link - do we need this?

                // pubDate
                self::addEscapedChild($item, 'pubDate', gmdate(DATE_RFC2822, strtotime($episode->getDbPublicationDate())));

                // category
                foreach ($itunesCategories as $c) {
                    if (!empty($c)) {
                        self::addEscapedChild($item, 'category', $c);
                    }
                }

                // guid
                $guid = self::addEscapedChild($item, 'guid', $episode->getDbEpisodeGuid());
                $guid->addAttribute('isPermaLink', 'false');

                // description
                self::addEscapedChild($item, 'description', $publishedFile->getDbDescription());

                // encolsure - url, length, type attribs
                $enclosure = $item->addChild('enclosure');
                $enclosure->addAttribute('url', $episode->getDbDownloadUrl());
                $enclosure->addAttribute('length', $publishedFile->getDbFilesize());
                $enclosure->addAttribute('type', $publishedFile->getDbMime());

                // itunes:subtitle
                // From https://www.apple.com/ca/itunes/podcasts/specs.html#subtitle :
                // 'The contents of the <itunes:subtitle> tag are displayed in the Description column in iTunes.'
                // self::addEscapedChild($item, "xmlns:itunes:subtitle", $publishedFile->getDbTrackTitle());
                self::addEscapedChild($item, 'xmlns:itunes:subtitle', $publishedFile->getDbDescription());

                // itunes:summary
                self::addEscapedChild($item, 'xmlns:itunes:summary', $publishedFile->getDbDescription());

                // itunes:author
                self::addEscapedChild($item, 'xmlns:itunes:author', $publishedFile->getDbArtistName());

                // itunes:explicit - skip this?

                // itunes:duration
                self::addEscapedChild($item, 'xmlns:itunes:duration', explode('.', $publishedFile->getDbLength())[0]);
            }

            // Format it nicely with newlines...
            $dom = new DOMDocument();
            $dom->loadXML($xml->asXML());
            $dom->formatOutput = true;

            return $dom->saveXML();
        } catch (FeedException $e) {
            return false;
        }
    }
}
