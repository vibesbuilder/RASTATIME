<?php

class Application_Model_Preference
{
    private static function getUserId()
    {
        // pass in true so the check is made with the autoloader
        // we need this check because saas calls this function from outside Zend
        if (!class_exists('Zend_Session', true) || !Zend_Session::isStarted() || !class_exists('Zend_Auth', true) || !Zend_Auth::getInstance()->hasIdentity()) {
            $userId = null;
        } else {
            $auth = Zend_Auth::getInstance();
            $userId = $auth->getIdentity()->id;
        }

        return $userId;
    }

    /**
     * @param bool  $isUserValue is true when we are setting a value for the current user
     * @param mixed $key
     * @param mixed $value
     */
    private static function setValue($key, $value, $isUserValue = false)
    {
        $con = Propel::getConnection(CcPrefPeer::DATABASE_NAME);

        // We are using row-level locking in Postgres via "FOR UPDATE" instead of a transaction here
        // because sometimes this function needs to be called while a transaction is already started.

        try {
            /* Comment this out while we reevaluate it in favor of a unique constraint
            static::_lock($con); */
            $userId = self::getUserId();

            if ($isUserValue && is_null($userId)) {
                throw new Exception("User id can't be null for a user preference {$key}.");
            }

            // Check if key already exists
            $sql = 'SELECT valstr FROM cc_pref'
                . ' WHERE keystr = :key';

            $paramMap = [];
            $paramMap[':key'] = $key;

            // For user specific preference, check if id matches as well
            if ($isUserValue) {
                $sql .= ' AND subjid = :id';
                $paramMap[':id'] = $userId;
            }

            $sql .= ' FOR UPDATE';

            $result = Application_Common_Database::prepareAndExecute(
                $sql,
                $paramMap,
                Application_Common_Database::ROW_COUNT,
                PDO::FETCH_ASSOC,
                $con
            );

            $paramMap = [];
            if ($result > 1) {
                // this case should not happen.
                $caller = debug_backtrace()[1]['function'];

                throw new Exception('Invalid number of results returned. Should be ' .
                    "0 or 1, but is '{$result}' instead, caller={$caller}");
            }
            if ($result == 1) {
                // result found
                if (!$isUserValue) {
                    // system pref
                    $sql = 'UPDATE cc_pref'
                        . ' SET subjid = NULL, valstr = :value'
                        . ' WHERE keystr = :key';
                } else {
                    // user pref
                    $sql = 'UPDATE cc_pref'
                        . ' SET valstr = :value'
                        . ' WHERE keystr = :key AND subjid = :id';

                    $paramMap[':id'] = $userId;
                }
            } else {
                // result not found
                if (!$isUserValue) {
                    // system pref
                    $sql = 'INSERT INTO cc_pref (keystr, valstr)'
                        . ' VALUES (:key, :value)';
                } else {
                    // user pref
                    $sql = 'INSERT INTO cc_pref (subjid, keystr, valstr)'
                        . ' VALUES (:id, :key, :value)';

                    $paramMap[':id'] = $userId;
                }
            }
            $paramMap[':key'] = $key;
            $paramMap[':value'] = $value;

            Application_Common_Database::prepareAndExecute(
                $sql,
                $paramMap,
                Application_Common_Database::EXECUTE,
                PDO::FETCH_ASSOC,
                $con
            );
        } catch (Exception $e) {
            header('HTTP/1.0 503 Service Unavailable');
            Logging::info('Database error: ' . $e->getMessage());

            exit;
        }
    }

    /**
     * Given a PDO connection, lock the cc_pref table for the current transaction.
     *
     * Creates a table level lock, which defaults to ACCESS EXCLUSIVE mode;
     * see https://www.postgresql.org/docs/9.1/static/explicit-locking.html
     *
     * @param PDO $con
     */
    private static function _lock($con)
    {
        // If we're not in a transaction, a lock is pointless
        if (!$con->inTransaction()) {
            return;
        }
        // Don't specify NOWAIT here; we should block on obtaining this lock
        // in case we're handling simultaneous requests.
        // Locks only last until the end of the transaction, so we shouldn't have to
        // worry about this causing any noticeable difference in request processing speed
        $sql = 'LOCK TABLE cc_pref';
        $st = $con->prepare($sql);
        $st->execute();
    }

    /**
     * @param string     $key          the preference key string
     * @param bool|false $isUserValue  select the preference for the current user
     * @param bool|false $forceDefault only look for default (no user ID) values
     *
     * @return mixed the preference value
     */
    private static function getValue($key, $isUserValue = false, $forceDefault = false)
    {
        try {
            $userId = null;
            if ($isUserValue) {
                // This is nested in here because so we can still use getValue() when the session hasn't started yet.
                $userId = self::getUserId();
                if (is_null($userId)) {
                    throw new Exception("User id can't be null for a user preference.");
                }
            }

            // Check if key already exists
            $sql = 'SELECT COUNT(*) FROM cc_pref'
                . ' WHERE keystr = :key';

            $paramMap = [];
            $paramMap[':key'] = $key;

            // For user specific preference, check if id matches as well
            if ($isUserValue) {
                $sql .= ' AND subjid = :id';
                $paramMap[':id'] = $userId;
            } elseif ($forceDefault) {
                $sql .= ' AND subjid IS NULL';
            }

            $result = Application_Common_Database::prepareAndExecute($sql, $paramMap, Application_Common_Database::COLUMN);

            // return an empty string if the result doesn't exist.
            if ($result == 0) {
                $res = '';
            } else {
                $sql = 'SELECT valstr FROM cc_pref'
                    . ' WHERE keystr = :key';

                $paramMap = [];
                $paramMap[':key'] = $key;

                // For user specific preference, check if id matches as well
                if ($isUserValue) {
                    $sql .= ' AND subjid = :id';
                    $paramMap[':id'] = $userId;
                }

                $result = Application_Common_Database::prepareAndExecute($sql, $paramMap, Application_Common_Database::COLUMN);

                $res = ($result !== false) ? $result : '';
            }

            return $res;
        } catch (Exception $e) {
            header('HTTP/1.0 503 Service Unavailable');
            Logging::info('Could not connect to database: ' . $e);

            exit;
        }
    }

    public static function GetHeadTitle()
    {
        $title = self::getValue('station_name');
        if (empty($title)) {
            $title = PRODUCT_NAME;
        }

        return $title;
    }

    public static function SetHeadTitle($title, $view = null)
    {
        self::setValue('station_name', $title);

        // in case this is called from airtime-saas script
        if ($view !== null) {
            // set session variable to new station name so that html title is updated.
            // should probably do this in a view helper to keep this controller as minimal as possible.
            $view->headTitle()->exchangeArray([]); // clear headTitle ArrayObject
            $view->headTitle(self::GetHeadTitle());
        }

        $eventType = 'update_station_name';
        $md = ['station_name' => $title];

        Application_Model_RabbitMq::SendMessageToPypo($eventType, $md);
    }

    /**
     * Set the furthest date that a never-ending show
     * should be populated until.
     *
     * @param DateTime $dateTime
     *                           A row from cc_show_days table
     */
    public static function SetShowsPopulatedUntil($dateTime)
    {
        $dateTime->setTimezone(new DateTimeZone('UTC'));
        self::setValue('shows_populated_until', $dateTime->format(DEFAULT_TIMESTAMP_FORMAT));
    }

    /**
     * Get the furthest date that a never-ending show
     * should be populated until.
     *
     * Returns null if the value hasn't been set, otherwise returns
     * a DateTime object representing the date.
     *
     * @return DateTime (in UTC Timezone)
     */
    public static function GetShowsPopulatedUntil()
    {
        $date = self::getValue('shows_populated_until');

        if ($date == '') {
            return null;
        }

        return new DateTime($date, new DateTimeZone('UTC'));
    }

    public static function SetDefaultCrossfadeDuration($duration)
    {
        self::setValue('default_crossfade_duration', $duration);
    }

    public static function GetDefaultCrossfadeDuration()
    {
        $duration = self::getValue('default_crossfade_duration');

        if ($duration === '') {
            // the default value of the fade is 00.5
            return '0';
        }

        return $duration;
    }

    // RASTATIME 2026-09-27 - Default Show Crossfade Duration: at a show
    // boundary the old show fades out over this many seconds while the
    // new show's first track starts at full level at once; the same value
    // shapes every input switch (track <-> webstream <-> line-in).
    public static function SetDefaultShowCrossfadeDuration($duration)
    {
        self::setValue('default_show_crossfade_duration', $duration);
    }

    public static function GetDefaultShowCrossfadeDuration()
    {
        $duration = self::getValue('default_show_crossfade_duration');

        if ($duration === '') {
            return '1';
        }

        return $duration;
    }

    public static function SetDefaultFadeIn($fade)
    {
        self::setValue('default_fade_in', $fade);
    }

    public static function GetDefaultFadeIn()
    {
        $fade = self::getValue('default_fade_in');

        if ($fade === '') {
            // the default value of the fade is 00.5
            return '0.5';
        }

        return $fade;
    }

    public static function SetDefaultFadeOut($fade)
    {
        self::setValue('default_fade_out', $fade);
    }

    public static function GetDefaultFadeOut()
    {
        $fade = self::getValue('default_fade_out');

        if ($fade === '') {
            // the default value of the fade is 0.5
            return '0.5';
        }

        return $fade;
    }

    public static function SetDefaultFade($fade)
    {
        self::setValue('default_fade', $fade);
    }

    public static function SetDefaultTransitionFade($fade)
    {
        self::setValue('default_transition_fade', $fade);

        $eventType = 'update_transition_fade';
        $md = ['transition_fade' => $fade];
        Application_Model_RabbitMq::SendMessageToPypo($eventType, $md);
    }

    public static function GetDefaultTransitionFade()
    {
        $transition_fade = self::getValue('default_transition_fade');

        // RASTATIME 2026-09-28 - the field shapes the DJ hand-over now; 1 s start value.
        return ($transition_fade == '') ? '1' : $transition_fade;
    }

    public static function SetStreamLabelFormat($type)
    {
        self::setValue('stream_label_format', $type);

        $eventType = 'update_stream_format';
        $md = ['stream_format' => $type];

        Application_Model_RabbitMq::SendMessageToPypo($eventType, $md);
    }

    public static function GetStreamLabelFormat()
    {
        return self::getValue('stream_label_format');
    }

    public static function getOffAirMeta()
    {
        return self::getValue('off_air_meta');
    }

    public static function setOffAirMeta($offAirMeta)
    {
        self::setValue('off_air_meta', $offAirMeta);

        Application_Model_RabbitMq::SendMessageToPypo(
            'update_message_offline',
            ['message_offline' => $offAirMeta]
        );
    }

    public static function GetStationName()
    {
        return self::getValue('station_name');
    }

    public static function SetStationName($station_name)
    {
        self::setValue('station_name', $station_name);
    }

    public static function SetAllow3rdPartyApi($bool)
    {
        self::setValue('third_party_api', $bool);
    }

    public static function GetAllow3rdPartyApi()
    {
        $val = self::getValue('third_party_api');

        return (strlen($val) == 0) ? '1' : $val;
    }

    public static function SetPodcastAlbumOverride($bool)
    {
        self::setValue('podcast_album_override', $bool);
    }

    public static function GetPodcastAlbumOverride()
    {
        $val = self::getValue('podcast_album_override');

        return $val === '1' ? true : false;
    }

    public static function SetPodcastAutoSmartblock($bool)
    {
        self::setValue('podcast_auto_smartblock', $bool);
    }

    public static function GetPodcastAutoSmartblock()
    {
        $val = self::getValue('podcast_auto_smartblock');

        return $val === '1' ? true : false;
    }

    public static function SetTrackTypeDefault($tracktype)
    {
        self::setValue('tracktype_default', $tracktype);
    }

    public static function GetTrackTypeDefault()
    {
        return self::getValue('tracktype_default');
    }

    public static function GetIntroPlaylist()
    {
        return self::getValue('intro_playlist');
    }

    public static function GetOutroPlaylist()
    {
        return self::getValue('outro_playlist');
    }

    public static function SetIntroPlaylist($playlist)
    {
        self::setValue('intro_playlist', $playlist);
    }

    public static function SetOutroPlaylist($playlist)
    {
        self::setValue('outro_playlist', $playlist);
    }

    // RASTATIME 2026-05-21 — Section 23.20.  Auto-DJ feature settings.
    // Stored in cc_pref as plain key/value rows (no schema change).
    // Keys:
    //   auto_dj_enabled         "true" / "false"   on/off master switch
    //   auto_dj_show_name       string             default name for auto-created shows
    //   auto_dj_playlist_id     integer            cc_playlist.id of the filler playlist
    //   auto_dj_fill_any_show   "true" / "false"   if on, fill incomplete shows after auto-build
    //   auto_dj_logo_path       string             storage-root-relative path to default show logo image (2026-09-16)
    public static function GetAutoDjEnabled()
    {
        return self::getValue('auto_dj_enabled') === 'true';
    }

    public static function SetAutoDjEnabled($enabled)
    {
        self::setValue('auto_dj_enabled', $enabled ? 'true' : 'false');
    }

    public static function GetAutoDjShowName()
    {
        $name = self::getValue('auto_dj_show_name');
        return $name === '' ? 'Auto DJ' : $name;
    }

    public static function SetAutoDjShowName($name)
    {
        self::setValue('auto_dj_show_name', (string) $name);
    }

    public static function GetAutoDjPlaylistId()
    {
        $id = self::getValue('auto_dj_playlist_id');
        return ($id === '' || $id === null) ? null : (int) $id;
    }

    public static function SetAutoDjPlaylistId($id)
    {
        self::setValue('auto_dj_playlist_id', $id === null ? '' : (string) (int) $id);
    }

    public static function GetAutoDjFillAnyShow()
    {
        return self::getValue('auto_dj_fill_any_show') === 'true';
    }

    public static function SetAutoDjFillAnyShow($enabled)
    {
        self::setValue('auto_dj_fill_any_show', $enabled ? 'true' : 'false');
    }

    public static function GetAutoDjLogoPath()
    {
        return self::getValue('auto_dj_logo_path');
    }

    public static function SetAutoDjLogoPath($path)
    {
        self::setValue('auto_dj_logo_path', (string) $path);
    }

    // RASTATIME 2026-05-21 — Section 23.20 v2.  Additional show-detail
    // defaults that AutoDjService stamps onto each auto-created show.
    // All optional; missing/empty values are passed through as empty
    // strings to ShowService and silently ignored by Propel's setters.
    public static function GetAutoDjShowUrl()             { return self::getValue('auto_dj_show_url'); }
    public static function SetAutoDjShowUrl($v)           { self::setValue('auto_dj_show_url',         (string) $v); }
    public static function GetAutoDjShowGenre()           { return self::getValue('auto_dj_show_genre'); }
    public static function SetAutoDjShowGenre($v)         { self::setValue('auto_dj_show_genre',       (string) $v); }
    public static function GetAutoDjShowDescription()     { return self::getValue('auto_dj_show_description'); }
    public static function SetAutoDjShowDescription($v)   { self::setValue('auto_dj_show_description', (string) $v); }
    public static function GetAutoDjShowBgColor()         { return self::getValue('auto_dj_show_bg_color'); }
    public static function SetAutoDjShowBgColor($v)       { self::setValue('auto_dj_show_bg_color',    (string) $v); }
    public static function GetAutoDjShowTextColor()       { return self::getValue('auto_dj_show_text_color'); }
    public static function SetAutoDjShowTextColor($v)     { self::setValue('auto_dj_show_text_color',  (string) $v); }

    // RASTATIME 2026-05-22 — Now-Playing Widget empty-state texts.
    // Four operator-configurable labels that the Current Show /
    // Track widgets render when there is no current / next item.
    // Defaults match the English source strings used pre-2026-05-22
    // so an upgrading operator sees no visible behaviour change
    // until they explicitly customise the labels under
    // Widgets → Current Show/Track.
    public static function GetWidgetNoCurrentShow()
    {
        $v = self::getValue('widget_no_current_show');
        return $v === '' ? 'No show on air' : $v;
    }
    public static function SetWidgetNoCurrentShow($v)     { self::setValue('widget_no_current_show', (string) $v); }

    public static function GetWidgetNoUpcomingShow()
    {
        $v = self::getValue('widget_no_upcoming_show');
        return $v === '' ? 'No upcoming show' : $v;
    }
    public static function SetWidgetNoUpcomingShow($v)    { self::setValue('widget_no_upcoming_show', (string) $v); }

    public static function GetWidgetNoCurrentTrack()
    {
        $v = self::getValue('widget_no_current_track');
        return $v === '' ? 'No track playing' : $v;
    }
    public static function SetWidgetNoCurrentTrack($v)    { self::setValue('widget_no_current_track', (string) $v); }

    public static function GetWidgetNoUpcomingTrack()
    {
        $v = self::getValue('widget_no_upcoming_track');
        return $v === '' ? 'No upcoming track' : $v;
    }
    public static function SetWidgetNoUpcomingTrack($v)   { self::setValue('widget_no_upcoming_track', (string) $v); }

    // RASTATIME 2026-05-22 — Next-Shows / Latest-Shows widget empty-
    // state labels.  Shown by the list widget when the requested
    // show has no future (resp. no past) instances, or when the
    // operator forgot to fill in show_id / show in the iframe URL.
    // Same English-fallback pattern as the four labels above.
    public static function GetWidgetNoNextShows()
    {
        $v = self::getValue('widget_no_next_shows');
        return $v === '' ? 'No upcoming shows' : $v;
    }
    public static function SetWidgetNoNextShows($v)       { self::setValue('widget_no_next_shows', (string) $v); }

    public static function GetWidgetNoLatestShows()
    {
        $v = self::getValue('widget_no_latest_shows');
        return $v === '' ? 'No past shows' : $v;
    }
    public static function SetWidgetNoLatestShows($v)     { self::setValue('widget_no_latest_shows', (string) $v); }

    // RASTATIME 2026-05-22 — On-Air-Today widget empty-state label.
    // Shown when neither a currently-airing show nor any upcoming
    // shows fall within the station day's remaining window.
    public static function GetWidgetNoOnAirToday()
    {
        $v = self::getValue('widget_no_on_air_today');
        return $v === '' ? 'No shows on air today' : $v;
    }
    public static function SetWidgetNoOnAirToday($v)      { self::setValue('widget_no_on_air_today', (string) $v); }

    // RASTATIME 2026-05-22 — Weekly-Schedule widget empty-state
    // label.  Shown per-day-tab when the displayed week has no
    // shows scheduled for that particular day.
    public static function GetWidgetNoWeeklyShows()
    {
        $v = self::getValue('widget_no_weekly_shows');
        return $v === '' ? 'No shows scheduled on this day' : $v;
    }
    public static function SetWidgetNoWeeklyShows($v)     { self::setValue('widget_no_weekly_shows', (string) $v); }

    // RASTATIME 2026-05-22 — Multi-View Schedule widget empty-
    // state label.  Shown when the requested date range has no
    // scheduled shows.  Standalone label so the operator can
    // tune the wording independently of the simpler Weekly-
    // Schedule widget.
    public static function GetWidgetNoMultiViewSchedule()
    {
        $v = self::getValue('widget_no_multi_view_schedule');
        return $v === '' ? 'No shows scheduled' : $v;
    }
    public static function SetWidgetNoMultiViewSchedule($v) { self::setValue('widget_no_multi_view_schedule', (string) $v); }

    // RASTATIME 2026-05-22 — Track History widget empty-state
    // label.  Shown when the picked day has no track history
    // entries (e.g. the playout engine wasn't running that day,
    // or the operator picked a future date which got clamped
    // to today but today's playout hasn't started yet).
    public static function GetWidgetNoTrackHistory()
    {
        $v = self::getValue('widget_no_track_history');
        return $v === '' ? 'No tracks played on this day' : $v;
    }
    public static function SetWidgetNoTrackHistory($v)    { self::setValue('widget_no_track_history', (string) $v); }

    // RASTATIME 2026-05-22 v14 — exclude tracks shorter than N
    // seconds from the Track History widget (operator-typical:
    // short fillers / jingles / silence-tail entries clutter
    // the public log).  Two prefs: the toggle, and the
    // threshold seconds.  Defaults are "exclude shorter than
    // 60 seconds" which catches most filler material without
    // hiding legitimate short tracks like news jingles or
    // station IDs that an operator might actually want listed.
    // RASTATIME 2026-09-18 — Stream Player widget: show cover artwork.
    public static function GetWidgetPlayerShowArt()
    {
        $v = self::getValue('widget_player_show_art');
        if ($v === '' || $v === null) { return true; }   // default on
        return ($v === '1' || $v === 1 || $v === true || $v === 'true');
    }
    public static function SetWidgetPlayerShowArt($v)
    {
        self::setValue('widget_player_show_art', $v ? '1' : '0');
    }

    /**
     * RASTATIME 2026-10-01 - the player's default cover (Settings ->
     * Widgets -> Player): the last link of the cover chain (track
     * artwork, show image, default cover).  Stored like the favicon as
     * base64 in cc_pref, but scaled to at most 256 px and re-encoded as
     * PNG on upload (GD), so the blob stays small whatever the operator
     * uploads.
     *
     * @param string $imagePath the uploaded file
     *
     * @return bool false when the file is not an image GD can read
     */
    public static function SetWidgetDefaultCover($imagePath)
    {
        $bytes = @file_get_contents($imagePath);
        if ($bytes === false || $bytes === '') {
            Logging::warn('SetWidgetDefaultCover: could not read ' . $imagePath);

            return false;
        }
        $im = @imagecreatefromstring($bytes);
        if (!$im) {
            Logging::warn('SetWidgetDefaultCover: not an image GD can read');

            return false;
        }
        $w = imagesx($im);
        $h = imagesy($im);
        if (max($w, $h) > 256) {
            $scaled = imagescale($im, $w >= $h ? 256 : -1, $w >= $h ? -1 : 256);
            if ($scaled) {
                imagedestroy($im);
                $im = $scaled;
            }
        }
        imagesavealpha($im, true);
        ob_start();
        imagepng($im, null, 8);
        $png = ob_get_clean();
        imagedestroy($im);
        self::setValue('widget_default_cover', base64_encode($png));

        return true;
    }

    public static function RemoveWidgetDefaultCover()
    {
        self::setValue('widget_default_cover', '');
    }

    /** @return null|string the PNG, base64-encoded; null when none is set */
    public static function GetWidgetDefaultCover()
    {
        $b64 = self::getValue('widget_default_cover');

        return ($b64 === '' || $b64 === null) ? null : $b64;
    }

    public static function GetWidgetTrackHistoryExcludeShort()
    {
        $v = self::getValue('widget_track_history_exclude_short');
        if ($v === '' || $v === null) { return true; }   // default true
        return ($v === '1' || $v === 1 || $v === true || $v === 'true');
    }
    public static function SetWidgetTrackHistoryExcludeShort($v)
    {
        self::setValue('widget_track_history_exclude_short', $v ? '1' : '0');
    }

    public static function GetWidgetTrackHistoryMinSeconds()
    {
        $v = self::getValue('widget_track_history_min_seconds');
        if ($v === '' || $v === null) { return 60; }     // default 60 s
        $i = (int) $v;
        return max(1, min(3600, $i ?: 60));
    }
    public static function SetWidgetTrackHistoryMinSeconds($v)
    {
        $i = max(1, min(3600, (int) $v));
        self::setValue('widget_track_history_min_seconds', (string) $i);
    }

    // RASTATIME 2026-05-22 v17 — display label for Line-In
    // sessions written into cc_playout_history when a
    // master_dj / live_dj source switches ON.  Operator
    // request: surface line-input sessions in the public
    // Track History widget + the internal Playout History
    // dashboard with a recognisable name (since Liquidsoap
    // doesn't send real metadata for raw-audio sources).
    // The label is shared between master_dj and live_dj
    // switches — differentiation between the two would be
    // a follow-up if needed.
    public static function GetWidgetLineInputLabel()
    {
        $v = self::getValue('widget_line_input_label');
        return $v === '' ? 'Line Input' : $v;
    }
    public static function SetWidgetLineInputLabel($v)    { self::setValue('widget_line_input_label', (string) $v); }

    public static function SetPhone($phone)
    {
        self::setValue('phone', $phone);
    }

    public static function GetPhone()
    {
        return self::getValue('phone');
    }

    public static function SetEmail($email)
    {
        self::setValue('email', $email);
    }

    public static function GetEmail()
    {
        return self::getValue('email');
    }

    public static function SetStationWebSite($site)
    {
        self::setValue('station_website', $site);
    }

    public static function GetStationWebSite()
    {
        return self::getValue('station_website');
    }

    public static function SetSupportFeedback($feedback)
    {
        self::setValue('support_feedback', $feedback);
    }

    public static function GetSupportFeedback()
    {
        return self::getValue('support_feedback');
    }

    public static function SetPublicise($publicise)
    {
        self::setValue('publicise', $publicise);
    }

    public static function GetPublicise()
    {
        return self::getValue('publicise');
    }

    public static function SetRegistered($registered)
    {
        self::setValue('registered', $registered);
    }

    public static function GetRegistered()
    {
        return self::getValue('registered');
    }

    public static function SetStationCountry($country)
    {
        self::setValue('country', $country);
    }

    public static function GetStationCountry()
    {
        return self::getValue('country');
    }

    public static function SetStationCity($city)
    {
        self::setValue('city', $city);
    }

    public static function GetStationCity()
    {
        return self::getValue('city');
    }

    public static function SetStationDescription($description)
    {
        self::setValue('description', $description);
    }

    public static function GetStationDescription()
    {
        $description = self::getValue('description');
        if (!empty($description)) {
            return $description;
        }

        return sprintf(_('Powered by %s'), SAAS_PRODUCT_BRANDING_NAME);
    }

    // Returns station default timezone (from preferences)
    public static function GetDefaultTimezone()
    {
        return Config::get('general.timezone');
    }

    public static function SetUserTimezone($timezone = null)
    {
        self::setValue('user_timezone', $timezone, true);
    }

    public static function GetUserTimezone()
    {
        $timezone = self::getValue('user_timezone', true);
        if (!$timezone) {
            return self::GetDefaultTimezone();
        }

        return $timezone;
    }

    // Always attempts to returns the current user's personal timezone setting
    public static function GetTimezone()
    {
        $userId = self::getUserId();

        if (!is_null($userId)) {
            return self::GetUserTimezone();
        }

        return self::GetDefaultTimezone();
    }

    // This is the language setting on preferences page
    public static function SetDefaultLocale($locale)
    {
        self::setValue('locale', $locale);
    }

    public static function GetDefaultLocale()
    {
        // T20.1 — fall back to 'en_US' when cc_pref has no locale row yet
        // (e.g. fresh install without data.sql, or row deleted by mistake).
        $locale = self::getValue('locale');
        return empty($locale) ? 'en_US' : $locale;
    }

    public static function GetUserLocale()
    {
        $locale = self::getValue('user_locale', true);
        // empty() checks for null and empty strings - more robust than !val
        if (empty($locale)) {
            return self::GetDefaultLocale();
        }

        return $locale;
    }

    public static function SetUserLocale($locale = null)
    {
        // When a new user is created they will get the default locale
        // setting which the admin sets on preferences page
        if (is_null($locale)) {
            $locale = self::GetDefaultLocale();
        }
        self::setValue('user_locale', $locale, true);
    }

    public static function GetLocale()
    {
        $userId = self::getUserId();

        if (!is_null($userId)) {
            return self::GetUserLocale();
        }

        return self::GetDefaultLocale();
    }

    public static function SetStationLogo($imagePath)
    {
        if (empty($imagePath)) {
            Logging::info('Removed station logo');
        }
        $image = @file_get_contents($imagePath);
        $image = base64_encode($image);
        self::setValue('logoImage', $image);
    }

    public static function GetStationLogo()
    {
        $logoImage = self::getValue('logoImage');
        if (!empty($logoImage)) {
            return $logoImage;
        }
        // We return the Airtime logo if no logo is set in the database.
        // airtime_logo.png is stored under the public directory
        $image = @file_get_contents(ROOT_PATH . '/public/' . DEFAULT_LOGO_FILE);

        return base64_encode($image);
    }

    /**
     * RASTATIME 2026-05-15 - Favicon stored as a base64-encoded blob plus its
     * MIME type, both in cc_pref.  Render path emits a data: URI link.  Empty
     * value falls back to the static public/favicon.ico (legacy behaviour).
     *
     * @param string $imagePath path to the uploaded file (empty string clears the favicon)
     */
    public static function SetStationFavicon($imagePath)
    {
        if (empty($imagePath)) {
            Logging::info('Removed station favicon');
            self::setValue('station_favicon', '');
            self::setValue('station_favicon_mime', '');
            return;
        }
        $bytes = @file_get_contents($imagePath);
        if ($bytes === false || $bytes === '') {
            Logging::warn('SetStationFavicon: could not read ' . $imagePath);
            return;
        }
        // Detect MIME type.  getimagesize() recognises PNG/JPEG/GIF/etc.
        // For .ico we fall back to a static MIME since getimagesize does not
        // identify it reliably on every PHP build.
        $mime = '';
        $info = @getimagesize($imagePath);
        if ($info !== false && !empty($info['mime'])) {
            $mime = $info['mime'];
        } else {
            $ext = strtolower(pathinfo($imagePath, PATHINFO_EXTENSION));
            if ($ext === 'ico') {
                $mime = 'image/x-icon';
            } else {
                $mime = 'image/png';  // safe default
            }
        }
        self::setValue('station_favicon', base64_encode($bytes));
        self::setValue('station_favicon_mime', $mime);
    }

    /**
     * @return string|null base64-encoded favicon data, or null if not set
     */
    public static function GetStationFavicon()
    {
        $favicon = self::getValue('station_favicon');
        return empty($favicon) ? null : $favicon;
    }

    /**
     * @return string MIME type for the stored favicon (defaults to image/png
     *                when nothing is recorded, so legacy data uploaded before
     *                the MIME column was introduced still renders).
     */
    public static function GetStationFaviconMime()
    {
        $mime = self::getValue('station_favicon_mime');
        return empty($mime) ? 'image/png' : $mime;
    }

    /**
     * Build the value to drop into the href attribute of the favicon
     * <link>.  Returns a data: URI when the operator has uploaded a custom
     * favicon, or null when nothing custom is set (caller falls back to the
     * static public/favicon.ico).
     */
    public static function GetStationFaviconHref()
    {
        $b64 = self::GetStationFavicon();
        if ($b64 === null) {
            return null;
        }
        return 'data:' . self::GetStationFaviconMime() . ';base64,' . $b64;
    }

    public static function SetUniqueId($id)
    {
        self::setValue('uniqueId', $id);
    }

    public static function GetUniqueId()
    {
        return self::getValue('uniqueId');
    }

    public static function GetCountryList()
    {
        $sql = 'SELECT * FROM cc_country';

        $res = Application_Common_Database::prepareAndExecute($sql, []);

        $out = [];
        $out[''] = _('Select Country');
        foreach ($res as $r) {
            $out[$r['isocode']] = $r['name'];
        }

        return $out;
    }

    public static function GetSystemInfo($returnArray = false, $p_testing = false)
    {
        exec('/usr/bin/airtime-check-system --no-color', $output);
        $output = preg_replace('/\s+/', ' ', $output);

        $systemInfoArray = [];
        foreach ($output as $key => &$out) {
            $info = explode('=', $out);
            if (isset($info[1])) {
                $key = str_replace(' ', '_', trim($info[0]));
                $key = strtoupper($key);
                if (
                    $key == 'WEB_SERVER' || $key == 'CPU' || $key == 'OS' || $key == 'TOTAL_RAM'
                    || $key == 'FREE_RAM' || $key == 'AIRTIME_VERSION' || $key == 'KERNAL_VERSION'
                    || $key == 'MACHINE_ARCHITECTURE' || $key == 'TOTAL_MEMORY_MBYTES' || $key == 'TOTAL_SWAP_MBYTES'
                    || $key == 'PLAYOUT_ENGINE_CPU_PERC'
                ) {
                    if ($key == 'AIRTIME_VERSION') {
                        // remove hash tag on the version string
                        $version = explode('+', $info[1]);
                        $systemInfoArray[$key] = $version[0];
                    } else {
                        $systemInfoArray[$key] = $info[1];
                    }
                }
            }
        }

        $outputArray = [];

        $outputArray['LIVE_DURATION'] = Application_Model_LiveLog::GetLiveShowDuration($p_testing);
        $outputArray['SCHEDULED_DURATION'] = Application_Model_LiveLog::GetScheduledDuration($p_testing);

        $outputArray['STATION_NAME'] = self::GetStationName();
        $outputArray['PHONE'] = self::GetPhone();
        $outputArray['EMAIL'] = self::GetEmail();
        $outputArray['STATION_WEB_SITE'] = self::GetStationWebSite();
        $outputArray['STATION_COUNTRY'] = self::GetStationCountry();
        $outputArray['STATION_CITY'] = self::GetStationCity();
        $outputArray['STATION_DESCRIPTION'] = self::GetStationDescription();

        // get web server info
        if (isset($systemInfoArray['AIRTIME_VERSION_URL'])) {
            $url = $systemInfoArray['AIRTIME_VERSION_URL'];
            $index = strpos($url, '/api/');
            $url = substr($url, 0, $index);

            $headerInfo = get_headers(trim($url), 1);
            $outputArray['WEB_SERVER'] = $headerInfo['Server'][0];
        }

        $outputArray['NUM_OF_USERS'] = Application_Model_User::getUserCount();
        $outputArray['NUM_OF_SONGS'] = Application_Model_StoredFile::getFileCount();
        $outputArray['NUM_OF_PLAYLISTS'] = Application_Model_Playlist::getPlaylistCount();
        $outputArray['NUM_OF_SCHEDULED_PLAYLISTS'] = Application_Model_Schedule::getSchduledPlaylistCount();
        $outputArray['NUM_OF_PAST_SHOWS'] = Application_Model_ShowInstance::GetShowInstanceCount(gmdate(DEFAULT_TIMESTAMP_FORMAT));
        $outputArray['UNIQUE_ID'] = self::GetUniqueId();
        $outputArray['INSTALL_METHOD'] = self::GetInstallMethod();
        $outputArray['NUM_OF_STREAMS'] = self::GetNumOfStreams();
        $outputArray['STREAM_INFO'] = Application_Model_StreamSetting::getStreamInfoForDataCollection();

        $outputArray = array_merge($systemInfoArray, $outputArray);

        $outputString = "\n";
        foreach ($outputArray as $key => $out) {
            if ($key == 'STREAM_INFO') {
                $outputString .= $key . " :\n";
                foreach ($out as $s_info) {
                    foreach ($s_info as $k => $v) {
                        $outputString .= "\t" . strtoupper($k) . ' : ' . $v . "\n";
                    }
                }
            } else {
                $outputString .= $key . ' : ' . $out . "\n";
            }
        }
        if ($returnArray) {
            $outputArray['PROMOTE'] = self::GetPublicise();
            $outputArray['LOGOIMG'] = self::GetStationLogo();

            return $outputArray;
        }

        return $outputString;
    }

    public static function SetRemindMeDate($p_never = false)
    {
        if ($p_never) {
            self::setValue('remindme', -1);
        } else {
            $weekAfter = mktime(0, 0, 0, gmdate('m'), gmdate('d') + 7, gmdate('Y'));
            self::setValue('remindme', $weekAfter);
        }
    }

    public static function GetRemindMeDate()
    {
        return self::getValue('remindme');
    }

    public static function SetImportTimestamp()
    {
        $now = time();
        if (self::GetImportTimestamp() + 5 < $now) {
            self::setValue('import_timestamp', $now);
        }
    }

    public static function GetImportTimestamp()
    {
        return (int) self::getValue('import_timestamp');
    }

    public static function SetPrivacyPolicyCheck($flag)
    {
        self::setValue('privacy_policy', $flag);
    }

    public static function GetPrivacyPolicyCheck()
    {
        return self::getValue('privacy_policy');
    }

    public static function GetNumOfStreams()
    {
        return count(Config::get('stream.outputs.merged'));
    }

    public static function SetEnableStreamConf($bool)
    {
        self::setValue('enable_stream_conf', $bool);
    }

    public static function GetEnableStreamConf()
    {
        if (self::getValue('enable_stream_conf') == null) {
            return 'true';
        }

        return self::getValue('enable_stream_conf');
    }

    public static function GetSchemaVersion()
    {
        CcPrefPeer::clearInstancePool(); // Ensure we don't get a cached Propel object (cached DB results)
        // because we're updating this version number within this HTTP request as well.

        // New versions use schema_version
        $pref = CcPrefQuery::create()
            ->filterByKeystr('schema_version')
            ->findOne();

        if (empty($pref)) {
            // Pre-2.5.2 releases all used this ambiguous "system_version" key to represent both the code and schema versions...
            $pref = CcPrefQuery::create()
                ->filterByKeystr('system_version')
                ->findOne();
        }

        return $pref->getValStr();
    }

    public static function SetSchemaVersion($version)
    {
        self::setValue('schema_version', $version);
    }

    public static function GetLatestVersion()
    {
        $config = Config::getConfig();

        $latest = json_decode(self::getValue('latest_version'));
        $nextCheck = self::getValue('latest_version_nextcheck');
        if ($latest && $nextCheck > time()) {
            return $latest;
        }

        $rss = new SimplePie();
        $rss->set_feed_url([LIBRETIME_UPDATE_FEED]);
        $rss->enable_cache(false);
        $rss->init();
        $rss->handle_content_type();
        // get all available versions ut to default github api limit
        $versions = [];
        foreach ($rss->get_items() as $item) {
            $versions[] = $item->get_title();
        }
        $latest = $versions;
        self::setValue('latest_version_nextcheck', strtotime('+1 week'));
        if (empty($latest)) {
            return [$config['airtime_version']];
        }

        self::setValue('latest_version', json_encode($latest));

        return $latest;
    }

    public static function SetLatestVersion($version)
    {
        $pattern = '/^[0-9]+\.[0-9]+\.[0-9]+/';
        if (preg_match($pattern, $version)) {
            self::setValue('latest_version', $version);
        }
    }

    public static function GetLatestLink()
    {
        $link = self::getValue('latest_link');
        if ($link == null || strlen($link) == 0) {
            return LIBRETIME_WHATS_NEW_URL;
        }

        return $link;
    }

    public static function SetLatestLink($link)
    {
        $pattern = '#^(http|https|ftp)://' .
            '([a-zA-Z0-9]+\.)*[a-zA-Z0-9]+' .
            '(/[a-zA-Z0-9\-\.\_\~\:\?\#\[\]\@\!\$\&\'\(\)\*\+\,\;\=]+)*/?$#';
        if (preg_match($pattern, $link)) {
            self::setValue('latest_link', $link);
        }
    }

    public static function SetWeekStartDay($day)
    {
        self::setValue('week_start_day', $day);
    }

    public static function GetWeekStartDay()
    {
        $val = self::getValue('week_start_day');

        return (strlen($val) == 0) ? '0' : $val;
    }

    /**
     * Stores the last timestamp of user updating stream setting.
     */
    public static function SetStreamUpdateTimestamp()
    {
        $now = time();
        self::setValue('stream_update_timestamp', $now);
    }

    /**
     * Gets the last timestamp of user updating stream setting.
     */
    public static function GetStreamUpdateTimestemp()
    {
        $update_time = self::getValue('stream_update_timestamp');

        return ($update_time == null) ? 0 : $update_time;
    }

    public static function GetClientId()
    {
        return self::getValue('client_id');
    }

    public static function SetClientId($id)
    {
        if (is_numeric($id)) {
            self::setValue('client_id', $id);
        } else {
            Logging::warn("Attempting to set client_id to invalid value: {$id}");
        }
    }

    // User specific preferences start

    /**
     * Sets the time scale preference (agendaDay/agendaWeek/month) in Calendar.
     *
     * @param $timeScale new time scale
     */
    public static function SetCalendarTimeScale($timeScale)
    {
        self::setValue('calendar_time_scale', $timeScale, true /* user specific */);
    }

    /**
     * Retrieves the time scale preference for the current user.
     * Defaults to month if no entry exists.
     */
    public static function GetCalendarTimeScale()
    {
        $val = self::getValue('calendar_time_scale', true /* user specific */);
        if (strlen($val) == 0) {
            $val = 'month';
        }

        return $val;
    }

    /**
     * Sets the number of entries to show preference in library under Playlist Builder.
     *
     * @param $numEntries new number of entries to show
     */
    public static function SetLibraryNumEntries($numEntries)
    {
        self::setValue('library_num_entries', $numEntries, true /* user specific */);
    }

    /**
     * Retrieves the number of entries to show preference in library under Playlist Builder.
     * Defaults to 10 if no entry exists.
     */
    public static function GetLibraryNumEntries()
    {
        $val = self::getValue('library_num_entries', true /* user specific */);
        if (strlen($val) == 0) {
            $val = '10';
        }

        return $val;
    }

    /**
     * Sets the time interval preference in Calendar.
     *
     * @param $timeInterval new time interval
     */
    public static function SetCalendarTimeInterval($timeInterval)
    {
        self::setValue('calendar_time_interval', $timeInterval, true /* user specific */);
    }

    /**
     * Retrieves the time interval preference for the current user.
     * Defaults to 30 min if no entry exists.
     */
    public static function GetCalendarTimeInterval()
    {
        $val = self::getValue('calendar_time_interval', true /* user specific */);

        return (strlen($val) == 0) ? '30' : $val;
    }

    public static function SetDiskQuota($value)
    {
        self::setValue('disk_quota', $value, false);
    }

    public static function GetDiskQuota()
    {
        $val = self::getValue('disk_quota');

        return empty($val) ? 2147483648 : $val;  // If there is no value for disk quota, return 2GB
    }

    public static function SetLiveStreamMasterUsername($value)
    {
        self::setValue('live_stream_master_username', $value, false);
    }

    public static function GetLiveStreamMasterUsername()
    {
        return self::getValue('live_stream_master_username');
    }

    public static function SetLiveStreamMasterPassword($value)
    {
        self::setValue('live_stream_master_password', $value, false);
    }

    public static function GetLiveStreamMasterPassword()
    {
        return self::getValue('live_stream_master_password');
    }

    public static function SetSourceStatus($sourcename, $status)
    {
        self::setValue($sourcename, $status, false);
    }

    /**
     * RASTATIME 2026-05-14 — fetch live source-connection state from the
     * playout's :8770/source-state JSON endpoint, with a per-request
     * static cache so multiple calls within one dashboard poll don't
     * trigger N HTTP calls.
     *
     * Returns an associative array:
     *   [ 'master_connected' => bool, 'show_connected' => bool ]
     *
     * On any failure (playout not running, timeout, parse error) falls
     * back to ``false``/``false`` so the dashboard's On-Air light just
     * goes dark — a safe, visible failure mode.  We deliberately do
     * NOT fall back to cc_pref: those columns are no longer written by
     * any path after the direct-to-:8770 mount_add/remove refactor, so
     * reading them would yield stale data that's worse than "off".
     */
    public static function GetPlayoutSourceState()
    {
        static $cache = null;
        if ($cache !== null) {
            return $cache;
        }

        $default = ['master_connected' => false, 'show_connected' => false];

        $ctx = stream_context_create([
            'http' => [
                'method'        => 'GET',
                'timeout'       => 0.5,    // 500 ms — dashboard polls every 5 s
                'ignore_errors' => true,
            ],
        ]);
        $resp = @file_get_contents(
            'http://127.0.0.1:8770/source-state',
            false,
            $ctx
        );
        if ($resp === false) {
            $cache = $default;

            return $cache;
        }
        $data = json_decode($resp, true);
        if (!is_array($data)) {
            $cache = $default;

            return $cache;
        }
        $cache = [
            'master_connected' => (bool) ($data['master_connected'] ?? false),
            'show_connected'   => (bool) ($data['show_connected'] ?? false),
        ];

        return $cache;
    }

    public static function GetSourceStatus($sourcename)
    {
        // RASTATIME 2026-05-14 — master_dj / live_dj source-connection
        // state now comes from the playout's SourceSwitcher live state,
        // not from cc_pref (which is no longer written by anyone since
        // the direct-to-:8770 mount_add/remove refactor — see
        // backend/playout/libretime_playout/source_switcher.py and the
        // icecast.xml comment block above the <authentication> elements
        // for the full rationale).
        if ($sourcename == 'master_dj') {
            $state = self::GetPlayoutSourceState();

            return $state['master_connected'];
        }
        if ($sourcename == 'live_dj') {
            $state = self::GetPlayoutSourceState();

            return $state['show_connected'];
        }

        // Fallback for unknown source names: legacy cc_pref read.
        $value = self::getValue($sourcename);

        return !($value == null || $value == 'false');
    }

    public static function SetSourceSwitchStatus($sourcename, $status)
    {
        self::setValue($sourcename . '_switch', $status, false);
    }

    public static function GetSourceSwitchStatus($sourcename)
    {
        // Scheduled play switch should always be "on".
        // Even though we've hidden this element in the dashboard we should
        // always make sure it's on or else a station's stream could go offline.
        if ($sourcename == 'scheduled_play') {
            return 'on';
        }

        // RASTATIME 2026-05-14 — same redirect as GetSourceStatus.
        // Classic LibreTime had a separate admin-toggle here so an
        // operator could pre-emptively kick a DJ off-air via the
        // dashboard switch.  RASTATIME doesn't (yet) expose that
        // toggle in the UI, so 'on' simply mirrors "is the DJ
        // currently connected?" — when nothing is connected the
        // switch reads 'off', when a DJ is on it reads 'on'.  The
        // separate operator-kick flow is covered by the
        // /disconnect-source endpoint (Cancel Show button).
        if ($sourcename == 'master_dj') {
            $state = self::GetPlayoutSourceState();

            return $state['master_connected'] ? 'on' : 'off';
        }
        if ($sourcename == 'live_dj') {
            $state = self::GetPlayoutSourceState();

            return $state['show_connected'] ? 'on' : 'off';
        }

        $value = self::getValue($sourcename . '_switch');

        return ($value == null || $value == 'off') ? 'off' : 'on';
    }

    public static function GetMasterDJSourceConnectionURL()
    {
        if (Config::has('stream.inputs.main.public_url') && Config::get('stream.inputs.main.public_url')) {
            return Config::get('stream.inputs.main.public_url');
        }

        $host = Config::get('general.public_url_raw')->getHost();
        $port = Application_Model_StreamSetting::getMasterLiveStreamPort();
        $mount = Application_Model_StreamSetting::getMasterLiveStreamMountPoint();
        $secure = Application_Model_StreamSetting::getMasterLiveStreamSecure();

        $scheme = $secure ? 'https' : 'http';

        return "{$scheme}://{$host}:{$port}/{$mount}";
    }

    public static function GetLiveDJSourceConnectionURL()
    {
        if (Config::has('stream.inputs.show.public_url') && Config::get('stream.inputs.show.public_url')) {
            return Config::get('stream.inputs.show.public_url');
        }

        $host = Config::get('general.public_url_raw')->getHost();
        $port = Application_Model_StreamSetting::getDjLiveStreamPort();
        $mount = Application_Model_StreamSetting::getDjLiveStreamMountPoint();
        $secure = Application_Model_StreamSetting::getDjLiveStreamSecure();

        $scheme = $secure ? 'https' : 'http';

        return "{$scheme}://{$host}:{$port}/{$mount}";
    }

    /*
     * RASTATIME 2026-05-14 — SetAutoTransition / GetAutoTransition /
     * SetAutoSwitch / GetAutoSwitch removed.  These wrapped cc_pref
     * rows that were only consumed by ApiController::updateSourceStatusAction
     * which sent RabbitMQ messages to the Liquidsoap-based Pypo playout
     * — both removed in ADR-002.  The replacement SourceSwitcher in
     * backend/playout/libretime_playout/source_switcher.py performs the
     * Master > Show > Scheduled priority transitions unconditionally.
     * The cc_pref rows themselves (keystr = 'auto_transition' /
     * 'auto_switch') are left in place for legacy data preservation;
     * they are no longer read by any code path.
     */
    // User specific preferences end

    public static function ShouldShowPopUp()
    {
        $today = mktime(0, 0, 0, gmdate('m'), gmdate('d'), gmdate('Y'));
        $remindDate = Application_Model_Preference::GetRemindMeDate();
        $retVal = false;

        if (is_null($remindDate) || ($remindDate != -1 && $today >= $remindDate)) {
            $retVal = true;
        }

        return $retVal;
    }

    /*
     * RASTATIME 2026-09-29 - per-user DataTables layouts (column order and
     * visibility, rows per page, sort) as the DataTables 1.13 state JSON,
     * one user value per table.  The library table of the Schedule Tracks
     * dialog has no Actions column, so it keeps a layout of its own next to
     * the dashboard's; the timeline is the same table in both places.
     * Values written by the DataTables 1.9 stack (PHP-serialized) do not
     * decode and read as "no layout".
     */
    private const DATATABLE_SETTING_KEYS = [
        'library' => 'library_datatable',
        'library_builder' => 'library_builder_datatable',
        'timeline' => 'timeline_datatable',
    ];

    /**
     * @param string $table key of DATATABLE_SETTING_KEYS
     * @param string $json  the DataTables state object as JSON
     *
     * @return bool false when the table or the state is not accepted
     */
    public static function setDatatableSetting($table, $json)
    {
        if (!isset(self::DATATABLE_SETTING_KEYS[$table])
            || !is_string($json) || strlen($json) > 65536) {
            return false;
        }
        $state = json_decode($json);
        if (!is_object($state)) {
            return false;
        }
        self::setValue(self::DATATABLE_SETTING_KEYS[$table], json_encode($state), true);

        return true;
    }

    /**
     * @param string $table key of DATATABLE_SETTING_KEYS
     *
     * @return null|object the saved DataTables state
     */
    public static function getDatatableSetting($table)
    {
        if (!isset(self::DATATABLE_SETTING_KEYS[$table])) {
            return null;
        }
        $state = json_decode(self::getValue(self::DATATABLE_SETTING_KEYS[$table], true));

        return is_object($state) ? $state : null;
    }

    public static function setNowPlayingScreenSettings($settings)
    {
        $data = serialize($settings);
        self::setValue('nowplaying_screen', $data, true);
    }

    public static function getNowPlayingScreenSettings()
    {
        $data = self::getValue('nowplaying_screen', true);

        return ($data != '') ? unserialize($data) : null;
    }

    public static function setLibraryScreenSettings($settings)
    {
        $data = serialize($settings);
        self::setValue('library_screen', $data, true);
    }

    public static function getLibraryScreenSettings()
    {
        $data = self::getValue('library_screen', true);

        return ($data != '') ? unserialize($data) : null;
    }

    public static function SetEnableReplayGain($value)
    {
        self::setValue('enable_replay_gain', $value, false);
    }

    public static function GetEnableReplayGain()
    {
        return self::getValue('enable_replay_gain', false);
    }

    public static function getReplayGainModifier()
    {
        $rg_modifier = self::getValue('replay_gain_modifier');

        if ($rg_modifier === '') {
            return '0';
        }

        return $rg_modifier;
    }

    public static function setReplayGainModifier($rg_modifier)
    {
        self::setValue('replay_gain_modifier', $rg_modifier, false);
    }

    // RASTATIME 2026-09-28 - Loudness Normalization (EBU R128, stage 1).
    // loudness_mode: off | replaygain | r128.  A database from before the
    // setting derives the mode from the ReplayGain switch; setting the
    // mode keeps enable_replay_gain in step for the legacy readers.
    public static function getLoudnessMode()
    {
        $mode = self::getValue('loudness_mode');
        if (in_array($mode, ['off', 'replaygain', 'r128'], true)) {
            return $mode;
        }

        return self::GetEnableReplayGain() ? 'replaygain' : 'off';
    }

    public static function setLoudnessMode($mode)
    {
        if (!in_array($mode, ['off', 'replaygain', 'r128'], true)) {
            $mode = 'off';
        }
        self::setValue('loudness_mode', $mode, false);
        self::SetEnableReplayGain($mode === 'replaygain' ? 1 : 0);
    }

    public static function getLoudnessTargetLufs()
    {
        $v = self::getValue('loudness_target_lufs');

        return ($v === '' || $v === null) ? '-23' : $v;
    }

    public static function setLoudnessTargetLufs($value)
    {
        $v = (float) str_replace(',', '.', (string) $value);
        $v = max(-40.0, min(-5.0, $v));
        self::setValue('loudness_target_lufs', (string) $v, false);
    }

    public static function getLoudnessTruePeakDbtp()
    {
        $v = self::getValue('loudness_true_peak_dbtp');

        return ($v === '' || $v === null) ? '-1' : $v;
    }

    public static function setLoudnessTruePeakDbtp($value)
    {
        $v = (float) str_replace(',', '.', (string) $value);
        $v = max(-12.0, min(0.0, $v));
        self::setValue('loudness_true_peak_dbtp', (string) $v, false);
    }

    public static function SetHistoryItemTemplate($value)
    {
        self::setValue('history_item_template', $value);
    }

    public static function GetHistoryItemTemplate()
    {
        return self::getValue('history_item_template');
    }

    public static function SetHistoryFileTemplate($value)
    {
        self::setValue('history_file_template', $value);
    }

    public static function GetHistoryFileTemplate()
    {
        return self::getValue('history_file_template');
    }

    public static function getDiskUsage()
    {
        $val = self::getValue('disk_usage');

        return (strlen($val) == 0) ? 0 : $val;
    }

    public static function setDiskUsage($value)
    {
        self::setValue('disk_usage', $value);
    }

    public static function updateDiskUsage($filesize)
    {
        $currentDiskUsage = self::getDiskUsage();
        if (empty($currentDiskUsage)) {
            $currentDiskUsage = 0;
        }

        self::setDiskUsage($currentDiskUsage + $filesize);
    }

    // RASTATIME 2026-09-28 - Live Text Info (Settings -> General): the "now
    // playing" line as a text file, written by the playout.
    public static function getLiveTextEnabled()
    {
        return self::getValue('live_text_enabled') === '1';
    }

    public static function setLiveTextEnabled($value)
    {
        self::setValue('live_text_enabled', $value ? '1' : '0');
    }

    public static function getLiveTextFormat()
    {
        $v = (int) self::getValue('live_text_format');

        return in_array($v, [0, 1, 2], true) ? $v : 0;
    }

    public static function setLiveTextFormat($value)
    {
        self::setValue('live_text_format', (string) (in_array((int) $value, [0, 1, 2], true) ? (int) $value : 0));
    }

    public static function getLiveTextWebEnabled()
    {
        $v = self::getValue('live_text_web_enabled');

        return $v === '' ? true : $v === '1';
    }

    public static function setLiveTextWebEnabled($value)
    {
        self::setValue('live_text_web_enabled', $value ? '1' : '0');
    }

    public static function getLiveTextFilePath()
    {
        return self::getValue('live_text_file_path');
    }

    public static function setLiveTextFilePath($value)
    {
        self::setValue('live_text_file_path', trim((string) $value));
    }

    // FTP push settings as one JSON row (like the FTP import); the password
    // stays here and is never sent back to the browser.
    public static function getLiveTextFtpConfig()
    {
        $defaults = [
            'enabled' => false, 'protocol' => 'ftp', 'host' => '',
            'port' => '', 'username' => '', 'password' => '', 'path' => '/',
        ];
        $raw = self::getValue('live_text_ftp_config');
        $data = $raw ? json_decode($raw, true) : null;

        return is_array($data) ? array_merge($defaults, $data) : $defaults;
    }

    public static function setLiveTextFtpConfig(array $config)
    {
        self::setValue('live_text_ftp_config', json_encode($config));
    }

    public static function setTuneinEnabled($value)
    {
        self::setValue('tunein_enabled', $value);
    }

    public static function getTuneinEnabled()
    {
        return self::getValue('tunein_enabled');
    }

    public static function setTuneinPartnerKey($value)
    {
        self::setValue('tunein_partner_key', $value);
    }

    public static function getTuneinPartnerKey()
    {
        return self::getValue('tunein_partner_key');
    }

    public static function setTuneinPartnerId($value)
    {
        self::setValue('tunein_partner_id', $value);
    }

    public static function getTuneinPartnerId()
    {
        return self::getValue('tunein_partner_id');
    }

    public static function setTuneinStationId($value)
    {
        self::setValue('tunein_station_id', $value);
    }

    public static function getTuneinStationId()
    {
        return self::getValue('tunein_station_id');
    }

    public static function geLastTuneinMetadataUpdate()
    {
        return self::getValue('last_tunein_metadata_update');
    }

    public static function setLastTuneinMetadataUpdate($value)
    {
        self::setValue('last_tunein_metadata_update', $value);
    }

    // TaskManager Lock Timestamp

    public static function getTaskManagerLock()
    {
        return self::getValue('task_manager_lock');
    }

    public static function setTaskManagerLock($value)
    {
        self::setValue('task_manager_lock', $value);
    }

    // SAAS-876 - Toggle indicating whether user is using custom stream settings

    public static function getUsingCustomStreamSettings()
    {
        $val = self::getValue('using_custom_stream_settings');

        return empty($val) ? false : $val;
    }

    public static function setUsingCustomStreamSettings($value)
    {
        self::setValue('using_custom_stream_settings', $value);
    }

    // SAAS-876 - Store the default Icecast password to restore when switching
    //            back to Airtime Pro streaming settings

    public static function getRadioPageDisplayLoginButton()
    {
        return self::getValue('radio_page_display_login_button');
    }

    public static function setRadioPageDisplayLoginButton($value)
    {
        self::setValue('radio_page_display_login_button', $value);
    }

    public static function getScheduleTrimOverbooked()
    {
        return boolval(self::getValue('schedule_trim_overbooked', false));
    }

    public static function setScheduleTrimOverbooked($value)
    {
        self::setValue('schedule_trim_overbooked', $value);
    }

    public static function getRadioPageDisabled()
    {
        return boolval(self::getValue('radio_page_disabled', false));
    }

    public static function setRadioPageDisabled($value)
    {
        self::setValue('radio_page_disabled', $value);
    }

    // RASTATIME 2026-09-29 - the UI's primary colour, '#rrggbb' or '' for
    // the default (see Application_Model_AccentColor).
    public static function GetUiAccentColor()
    {
        return self::getValue('ui_accent_color');
    }

    public static function SetUiAccentColor($hex)
    {
        self::setValue('ui_accent_color', Application_Model_AccentColor::normalize($hex) ?? '');
    }

    public static function getLangTimezoneSetupComplete()
    {
        return self::getValue('lang_tz_setup_complete');
    }

    public static function setLangTimezoneSetupComplete($value)
    {
        self::setValue('lang_tz_setup_complete', $value);
    }

    public static function getWhatsNewDialogViewed()
    {
        $val = self::getValue('whats_new_dialog_viewed', true);
        if (empty($val)) {
            // Check the default (no user ID) value if the user value is empty
            // This is so that new stations won't see the popup
            $val = self::getValue('whats_new_dialog_viewed', false, true);
        }

        return empty($val) ? false : $val;
    }

    public static function setWhatsNewDialogViewed($value)
    {
        self::setValue('whats_new_dialog_viewed', $value, true);
    }

    public static function getAutoPlaylistPollLock()
    {
        return self::getValue('autoplaylist_poll_lock');
    }

    public static function setAutoPlaylistPollLock($value)
    {
        self::setValue('autoplaylist_poll_lock', $value);
    }

    public static function getPodcastPollLock()
    {
        return self::getValue('podcast_poll_lock');
    }

    public static function setPodcastPollLock($value)
    {
        self::setValue('podcast_poll_lock', $value);
    }

    public static function getStationPodcastId()
    {
        // Create the Station podcast if it doesn't exist.
        $stationPodcastId = self::getValue('station_podcast_id');
        if (empty($stationPodcastId)) {
            $stationPodcastId = Application_Service_PodcastService::createStationPodcast();
        }

        return $stationPodcastId;
    }

    public static function setStationPodcastId($value)
    {
        self::setValue('station_podcast_id', $value);
    }

    // SAAS-1081 - Implement a universal download key for downloading episodes from the station podcast
    //             Store and increment the download counter, resetting every month

    public static function getStationPodcastDownloadKey()
    {
        return self::getValue('station_podcast_download_key');
    }

    public static function setStationPodcastDownloadKey($value = null)
    {
        $value = empty($value) ? (new Application_Model_Auth())->generateRandomString() : $value;
        self::setValue('station_podcast_download_key', $value);
    }

    public static function getStationPodcastDownloadResetTimer()
    {
        return self::getValue('station_podcast_download_reset_timer');
    }

    public static function setStationPodcastDownloadResetTimer($value)
    {
        self::setValue('station_podcast_download_reset_timer', $value);
    }

    public static function getStationPodcastDownloadCounter()
    {
        return self::getValue('station_podcast_download_counter');
    }

    public static function resetStationPodcastDownloadCounter()
    {
        self::setValue('station_podcast_download_counter', 0);
    }

    public static function incrementStationPodcastDownloadCounter()
    {
        $c = self::getStationPodcastDownloadCounter();
        self::setValue('station_podcast_download_counter', empty($c) ? 1 : ++$c);
    }

    // For fail cases, we may need to decrement the download counter
    public static function decrementStationPodcastDownloadCounter()
    {
        $c = self::getStationPodcastDownloadCounter();
        self::setValue('station_podcast_download_counter', empty($c) ? 0 : --$c);
    }

    /**
     * @return int either 0 (public) or 1 (private)
     */
    public static function getStationPodcastPrivacy()
    {
        return self::getValue('station_podcast_privacy');
    }

    public static function setStationPodcastPrivacy($value)
    {
        self::setValue('station_podcast_privacy', $value);
    }

    // RASTATIME 2026-05-16 - Track Expiry / Podcast Auto-Expiry pruner
    // last-run timestamp.  Used by TrackExpiryTask to throttle the
    // hourly run interval (TRACK_EXPIRY_INTERVAL_SECONDS = 3600).
    public static function getTrackExpiryLastRun()
    {
        return self::getValue('track_expiry_last_run');
    }

    public static function setTrackExpiryLastRun($value)
    {
        self::setValue('track_expiry_last_run', $value);
    }

    // RASTATIME 2026-05-16 - Local Import Folder.  Operator-configured
    // absolute path on the RASTATIME host (Settings -> Local Machine).
    // A LocalImportScanTask (TaskManager, 5-min interval) walks the
    // folder, moves every audio file into the standard import pipeline
    // (organize -> analyzer -> cc_files), and deletes the source after
    // the move - successful OR failed - per design decision A modified
    // 2026-05-16 ("drop-folder semantics, single folder").
    public static function getLocalImportFolder()
    {
        return self::getValue('local_import_folder');
    }

    public static function setLocalImportFolder($value)
    {
        self::setValue('local_import_folder', trim((string) $value));
    }

    // RASTATIME 2026-09-16 - Media Library Location (Settings -> Local
    // Machine).  Empty = storage.path from libretime.conf.  The move job
    // state is JSON written by the API (libretime_api.storage.move).
    public static function getLocalStorageFolder()
    {
        return self::getValue('local_storage_folder');
    }

    public static function setLocalStorageFolder($value)
    {
        self::setValue('local_storage_folder', trim((string) $value));
    }

    public static function getLocalStorageMoveState()
    {
        return self::getValue('local_storage_move');
    }

    public static function getLocalImportLastRun()
    {
        return self::getValue('local_import_last_run');
    }

    public static function setLocalImportLastRun($value)
    {
        self::setValue('local_import_last_run', $value);
    }

    public static function getLocalImportLastStatus()
    {
        return self::getValue('local_import_last_status');
    }

    public static function setLocalImportLastStatus($value)
    {
        self::setValue('local_import_last_status', $value);
    }

    // RASTATIME 2026-09-17 - Import from FTP Server (Settings -> Local
    // Machine).  One JSON config in cc_pref: enabled, protocol
    // (ftp|ftps|sftp), host, port, username, password, path.  The
    // password lives here like the other service passwords and is never
    // sent back to the browser (the save action keeps it when the field
    // comes back empty).
    public static function getFtpImportConfig()
    {
        $defaults = [
            'enabled' => false, 'protocol' => 'ftp', 'host' => '',
            'port' => '', 'username' => '', 'password' => '', 'path' => '/',
        ];
        $raw = self::getValue('local_ftp_import_config');
        $data = $raw ? json_decode($raw, true) : null;
        return is_array($data) ? array_merge($defaults, $data) : $defaults;
    }

    public static function setFtpImportConfig(array $config)
    {
        self::setValue('local_ftp_import_config', json_encode($config));
    }

    public static function getFtpImportLastRun()
    {
        return self::getValue('local_ftp_import_last_run');
    }

    public static function setFtpImportLastRun($value)
    {
        self::setValue('local_ftp_import_last_run', $value);
    }

    public static function getFtpImportLastStatus()
    {
        return self::getValue('local_ftp_import_last_status');
    }

    public static function setFtpImportLastStatus($value)
    {
        self::setValue('local_ftp_import_last_status', $value);
    }

    /** Remote quiet rule: {name: {size, seen_at}} between fetch cycles. */
    public static function getFtpImportPending()
    {
        $raw = self::getValue('local_ftp_import_pending');
        $data = $raw ? json_decode($raw, true) : null;
        return is_array($data) ? $data : [];
    }

    public static function setFtpImportPending(array $pending)
    {
        self::setValue('local_ftp_import_pending', json_encode($pending));
    }

    // RASTATIME 2026-05-17 - Local Recording Folder (Section 23.13).
    // Operator-configured absolute path on the RASTATIME host (Settings ->
    // Local Machine).  The playout PlayoutScheduler reads this via the
    // GET /api/v2/preferences/local-recording-folder endpoint when a
    // SHOW_RECORD_START event fires, then writes
    //   <folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3
    // by tapping the first Icecast output mountpoint with `-c copy`.
    public static function getLocalRecordingFolder()
    {
        return self::getValue('local_recording_folder');
    }

    public static function setLocalRecordingFolder($value)
    {
        self::setValue('local_recording_folder', trim((string) $value));
    }

    // RASTATIME 2026-06-05 - 24/7 hourly archive recording (Record-per-Hour).
    // A continuous Liquidsoap output.file on the bus, rotating hourly,
    // independent of shows (Settings -> Local Machine -> "24/7 Recording").
    // The playout render + retention task read these cc_pref keys directly
    // (local_247_recording_*); these accessors back the Settings form.
    public static function getLocal247RecordingEnabled()
    {
        return self::getValue('local_247_recording_enabled') === 'true';
    }

    public static function setLocal247RecordingEnabled($value)
    {
        $on = ($value === true || $value === 'true' || $value === '1' || $value === 1);
        self::setValue('local_247_recording_enabled', $on ? 'true' : 'false');
    }

    public static function getLocal247RecordingFolder()
    {
        return self::getValue('local_247_recording_folder');
    }

    public static function setLocal247RecordingFolder($value)
    {
        self::setValue('local_247_recording_folder', trim((string) $value));
    }

    public static function getLocal247RecordingFormat()
    {
        $fmt = strtolower(trim((string) self::getValue('local_247_recording_format')));

        return $fmt !== '' ? $fmt : 'mp3';
    }

    public static function setLocal247RecordingFormat($value)
    {
        self::setValue('local_247_recording_format', strtolower(trim((string) $value)));
    }

    public static function getLocal247RecordingBitrate()
    {
        $b = (int) self::getValue('local_247_recording_bitrate');

        return $b > 0 ? $b : 192;
    }

    public static function setLocal247RecordingBitrate($value)
    {
        self::setValue('local_247_recording_bitrate', (string) (int) $value);
    }

    public static function getLocal247RecordingRetentionDays()
    {
        return (int) self::getValue('local_247_recording_retention_days');
    }

    public static function setLocal247RecordingRetentionDays($value)
    {
        $d = (int) $value;
        self::setValue('local_247_recording_retention_days', (string) ($d < 0 ? 0 : $d));
    }

    // RASTATIME 2026-06-07 - Song Requests: the "Requestable Pool".
    // Stores the cc_block ids of the smart block(s) whose members define
    // which tracks listeners may request, as a comma-separated string
    // (e.g. "4,6,7").  The RequestablePoolSyncTask (TaskManager) expands
    // the UNION of those blocks and flips cc_files.requestable
    // accordingly.  Empty = no pool configured (nothing requestable).
    public static function getRequestablePoolBlockIds()
    {
        $raw = trim((string) self::getValue('requestable_pool_block_ids'));
        if ($raw === '') {
            return [];
        }
        $ids = [];
        foreach (explode(',', $raw) as $part) {
            $id = (int) trim($part);
            if ($id > 0 && !in_array($id, $ids, true)) {
                $ids[] = $id;
            }
        }

        return $ids;
    }

    public static function setRequestablePoolBlockIds($values)
    {
        // Accept an array of ids (from the multicheckbox) or a CSV string.
        if (!is_array($values)) {
            $values = ($values === null || $values === '') ? [] : explode(',', (string) $values);
        }
        $ids = [];
        foreach ($values as $v) {
            $id = (int) $v;
            if ($id > 0 && !in_array($id, $ids, true)) {
                $ids[] = $id;
            }
        }
        self::setValue('requestable_pool_block_ids', implode(',', $ids));
    }

    public static function getRequestablePoolLastSync()
    {
        return self::getValue('requestable_pool_last_sync');
    }

    public static function setRequestablePoolLastSync($value)
    {
        self::setValue('requestable_pool_last_sync', $value);
    }

    // RASTATIME 2026-06-16 - Traffic Alerts: the single smart block whose
    // newly-imported tracks are auto-inserted into the running show after the
    // current track (within the SLA).  0 / empty = traffic alerts disabled.
    // RASTATIME 2026-09-27 — Show-Shift filler playlist (0 = disabled).
    // See Application_Service_ShowShiftService::fillShiftedTail().
    public static function getShowShiftFillerPlaylistId()
    {
        return (int) self::getValue('show_shift_filler_playlist_id');
    }

    public static function setShowShiftFillerPlaylistId($value)
    {
        self::setValue('show_shift_filler_playlist_id', (int) $value);
    }

    public static function getTrafficAlertBlockId()
    {
        return (int) self::getValue('traffic_alert_block_id');
    }

    public static function setTrafficAlertBlockId($value)
    {
        self::setValue('traffic_alert_block_id', (int) $value);
    }

    public static function getTrafficAlertLastRun()
    {
        return self::getValue('traffic_alert_last_run');
    }

    public static function setTrafficAlertLastRun($value)
    {
        self::setValue('traffic_alert_last_run', $value);
    }

    // RASTATIME 2026-06-07 - Song Requests: last-run timestamp for the
    // RequestShowFillTask (incremental just-in-time fill of request shows).
    public static function getRequestShowFillLastRun()
    {
        return self::getValue('request_show_fill_last_run');
    }

    public static function setRequestShowFillLastRun($value)
    {
        self::setValue('request_show_fill_last_run', $value);
    }

    // RASTATIME 2026-06-07 - Song Requests, Phase 6b: last-run timestamp for
    // the RequestPlayedTask (marks aired 'queued' requests as 'played').
    public static function getRequestPlayedLastRun()
    {
        return self::getValue('request_played_last_run');
    }

    public static function setRequestPlayedLastRun($value)
    {
        self::setValue('request_played_last_run', $value);
    }

    // RASTATIME 2026-06-07 - Song Requests, Phase 6c: last-run timestamp for
    // the RequestExpiryTask (expires stale 'pending' requests after the TTL).
    public static function getRequestExpiryLastRun()
    {
        return self::getValue('request_expiry_last_run');
    }

    public static function setRequestExpiryLastRun($value)
    {
        self::setValue('request_expiry_last_run', $value);
    }

    // RASTATIME 2026-06-15 - Show-Shift / "Allow delayed start", Phase 3a:
    // last-run timestamp for the ShowShiftTask interval gate.
    public static function getShowShiftLastRun()
    {
        return self::getValue('show_shift_last_run');
    }

    public static function setShowShiftLastRun($value)
    {
        self::setValue('show_shift_last_run', $value);
    }

    // RASTATIME 2026-05-15 - GetFeaturePreviewMode/SetFeaturePreviewMode removed:
    // the cc_pref key 'feature_preview_mode' was stored but never consumed by any
    // code path (no feature ever gated on it). Form element + render + save line
    // also deleted. cc_pref row left in place (non-destructive).

    /*
     * Stores liquidsoap status if $boot_time > save time.
     * save time is the time that user clicked save on stream setting page
     */
    public static function setLiquidsoapError($stream_id, $msg, $boot_time = null)
    {
        $update_time = Application_Model_Preference::GetStreamUpdateTimestemp();

        if ($boot_time == null || $boot_time > $update_time) {
            $stream_id = trim($stream_id, 's');
            self::setValue("stream_liquidsoap_status:{$stream_id}", $msg);
        }
    }

    public static function getLiquidsoapError($stream_id)
    {
        $result = self::getValue("stream_liquidsoap_status:{$stream_id}");

        return ($result !== false) ? $result : null;
    }

    public static function GetAllListenerStatErrors()
    {
        $sql = <<<'SQL'
SELECT *
FROM cc_pref
WHERE keystr LIKE 'stream_stats_status:%'
SQL;

        return Application_Common_Database::prepareAndExecute($sql, []);
    }

    public static function SetListenerStatError($stream_id, $value)
    {
        $stream_id = trim($stream_id, 's');
        self::setValue("stream_stats_status:{$stream_id}", $value);
    }

    // -------------------------------------------------------------------------
    // RASTATIME: Icecast Output Stream settings stored in cc_pref as JSON.
    // Keys: stream_output_1, stream_output_2, stream_output_3
    // -------------------------------------------------------------------------

    /**
     * Returns all editable settings for output stream N (1-3) as an array.
     * Falls back to safe defaults when no value has been saved yet.
     *
     * @param int $n stream index (1, 2, or 3)
     */
    public static function GetStreamOutput(int $n): array
    {
        $raw = self::getValue('stream_output_' . $n);
        if (!empty($raw)) {
            $decoded = json_decode($raw, true);
            if (is_array($decoded)) {
                return $decoded;
            }
        }

        return [
            'enable'      => 'false',
            'output'      => 'icecast',
            'host'        => 'localhost',
            'port'        => '8000',
            'mount'       => '',
            'user'        => 'source',
            'pass'        => '',
            'admin_user'  => 'admin',
            'admin_pass'  => '',
            'channels'    => 'stereo',
            'bitrate'     => '128',
            'type'        => 'mp3',
            'name'        => '',
            'description' => '',
            'genre'       => '',
            'url'         => '',
            'mobile'      => 'false',
        ];
    }

    /**
     * Persists all editable settings for output stream N to cc_pref.
     *
     * @param int   $n    stream index (1, 2, or 3)
     * @param array $data associative array of stream settings
     */
    public static function SetStreamOutput(int $n, array $data): void
    {
        self::setValue('stream_output_' . $n, json_encode($data));
    }
}
