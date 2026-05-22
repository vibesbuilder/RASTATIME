<?php

class EmbedController extends Zend_Controller_Action
{
    public function init()
    {
        // translate widgets to station default language
        $locale = Application_Model_Preference::GetDefaultLocale();
        if ($locale) {
            Application_Model_Locale::configureLocalization($locale);
        }
    }

    /**
     * This is the action that is called to insert the player onto a web page.
     * It passes all the js and css files to the view, as well as all the
     * stream customization information.
     *
     * The view for this action contains all the inline javascript needed to
     * create the player.
     */
    public function playerAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $this->view->playerhtml5_js = Assets::url('js/airtime/player/playerhtml5.js');
        $this->view->jquery = Assets::url('js/libs/jquery-1.10.2.min.js');
        $this->view->metadata_api_url = '/api/live-info';
        $this->view->player_title = json_encode($this->view->escape($request->getParam('title')));
        $this->view->jquery_i18n = Assets::url('js/i18n/jquery.i18n.js');

        $styleParam = $request->getParam('style');
        $player_style = isset($styleParam) ? $styleParam : 'basic';
        if ($player_style == 'premium') {
            $this->view->css = Assets::url('css/radio-page/premium_player.css');
        } else {
            $this->view->css = Assets::url('css/player.css');
        }
        $this->view->player_style = $player_style;

        $stream = $request->getParam('stream');
        $streamData = Application_Model_StreamSetting::getEnabledStreamData();

        // RASTATIME 2026-05-20 — normalise the stream-data ``mobile``
        // flag to a real bool.  Upstream stores it as the literal
        // STRING `"false"` (because the cc_pref persistence layer
        // serialises everything as strings), which is truthy in PHP
        // — so the `if ($s['mobile']) { mobile-queue } else { desktop-
        // queue }` branch below would silently route every stream
        // into the mobile-only queue and leave the desktop player
        // with an empty queue.  No URL rewriting here: the operator
        // is expected to configure a publicly-reachable host in
        // Settings → Streams (Icecast `host` field) for LAN /
        // external embedding to work.
        foreach ($streamData as &$_s) {
            $m = $_s['mobile'] ?? false;
            $_s['mobile'] = ($m === true || $m === 'true' || $m === '1' || $m === 1);
        }
        unset($_s);

        $availableMobileStreams = [];
        $availableDesktopStreams = [];

        if ($stream == 'auto') {
            $this->view->playerMode = 'auto';
            $this->view->streamURL = json_encode('');
            foreach ($streamData as $s) {
                if ($s['mobile']) {
                    array_push($availableMobileStreams, $s);
                } else {
                    array_push($availableDesktopStreams, $s);
                }
            }
        } elseif ($stream == 'file') {
            $this->view->playerMode = 'file';
            $this->view->streamURL = json_encode($request->getParam('file_url'));
            $this->view->codec = $request->getParam('file_codec');
        } elseif (!empty($stream)) {
            $this->view->playerMode = 'manual';
            $selectedStreamData = $streamData[$stream];
            $this->view->streamURL = json_encode($selectedStreamData['url']);
            $this->view->codec = $selectedStreamData['codec'];
        }
        $this->view->availableMobileStreams = json_encode($availableMobileStreams);
        $this->view->availableDesktopStreams = json_encode($availableDesktopStreams);
    }

    /**
     * RASTATIME 2026-05-22 — Now-Playing Show Widget (iframe embed).
     *
     * Renders a minimal two-line text widget that an external station
     * homepage can drop in with a plain iframe:
     *
     *     <iframe src=".../embed/now-playing-show?theme=dark&cache=60"
     *             width="100%" height="50" frameborder="0"></iframe>
     *
     * Line 1: Current show name (left), remaining duration (right)
     * Line 2: Next show name (left), start - end time (right)
     *
     * URL parameters:
     *   theme  - 'auto' (default, follows prefers-color-scheme),
     *            'dark' (light text on transparent),
     *            'light' (dark text on transparent).
     *   cache  - Server-side HTTP cache TTL in seconds.  Default 60.
     *            Clamped to [10, 3600].
     *   timezone - optional, defaults to station timezone.
     *
     * No API auth required — this endpoint is intentionally public
     * (the embed mechanism is the whole point of the widget).  Data
     * comes from the same Schedule model the /api/live-info endpoint
     * uses, so the two views always stay in sync.
     */
    public function nowPlayingShowAction()
    {
        // Default Zend-1 view-resolution turns the action name
        // "nowPlayingShow" into the template "now-playing-show.phtml"
        // under the embed/ script directory, so all this needs to do
        // is populate the view variables.
        $this->_prepareNowPlayingView();
    }

    /**
     * RASTATIME 2026-05-22 — Now-Playing Track Widget (iframe embed).
     *
     * Same envelope as nowPlayingShowAction but the body shows the
     * currently-playing track (artist - title) and the upcoming
     * track.  See nowPlayingShowAction docstring for URL parameters.
     */
    public function nowPlayingTrackAction()
    {
        // Default Zend-1 view-resolution turns the action name
        // "nowPlayingTrack" into the template "now-playing-track.phtml"
        // under the embed/ script directory, so all this needs to do
        // is populate the view variables.
        $this->_prepareNowPlayingView();
    }

    /**
     * RASTATIME 2026-05-22 — JSON feed shared by both widgets.
     *
     * Polled by the in-iframe JavaScript every 30 s to refresh state
     * without a full page reload.  Server-side cache TTL is set via
     * the same ?cache=N parameter as the widget iframes — when an
     * operator embeds the widget with cache=60, the JS poll will
     * hit the browser cache for 60 s before generating a real
     * backend round-trip.
     */
    public function nowPlayingDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $cacheTtl = $this->_resolveCacheTtl();
        $timezone = $this->_resolveTimezone();

        $payload = $this->_buildNowPlayingPayload($timezone);

        header('Content-Type: application/json; charset=utf-8');
        $this->_emitCacheHeaders($cacheTtl);
        echo json_encode($payload);
    }

    /**
     * Shared view-population for the two Now-Playing widget actions.
     *
     * Each action's default template (now-playing-show.phtml /
     * now-playing-track.phtml) is rendered by the standard Zend-1
     * view-resolution — this helper only populates the variables
     * both templates consume, plus the HTTP cache headers.
     */
    private function _prepareNowPlayingView()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        // Theme is exposed to the template as a literal CSS class
        // ('np-theme-auto' / 'np-theme-dark' / 'np-theme-light') so
        // the stylesheet can switch on it without any JS.
        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        // RASTATIME 2026-05-22 — Overflow strategy: ellipsis (default)
        // truncates with "…" when the show / track label is wider
        // than the 300 px widget body; marquee instead scrolls the
        // text left so the operator can read the whole title.
        // Picked via ?overflow=ellipsis|marquee URL parameter so
        // an operator can decide per-embed without changing the
        // server-side default.
        $overflow = $request->getParam('overflow', 'ellipsis');
        if (!in_array($overflow, ['ellipsis', 'marquee'], true)) {
            $overflow = 'ellipsis';
        }
        $this->view->overflowClass = 'np-overflow-' . $overflow;

        $cacheTtl = $this->_resolveCacheTtl();
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();

        // Server-side initial render so the iframe shows real data
        // immediately even before the JS poll fires.
        $this->view->initialPayload = $this->_buildNowPlayingPayload($timezone);

        // RASTATIME 2026-05-22 — empty-state labels, configurable
        // by the operator under Widgets -> Current Show/Track.
        // Defaults match the English source strings so an
        // un-customised station is identical to the pre-2026-05-22
        // behaviour.
        $this->view->emptyLabels = [
            'noCurrentShow'  => Application_Model_Preference::GetWidgetNoCurrentShow(),
            'noUpcomingShow' => Application_Model_Preference::GetWidgetNoUpcomingShow(),
            'noCurrentTrack' => Application_Model_Preference::GetWidgetNoCurrentTrack(),
            'noUpcomingTrack'=> Application_Model_Preference::GetWidgetNoUpcomingTrack(),
        ];

        // Asset URLs computed here so the view template stays clean.
        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/now-playing-widget.js');

        // URL for the JS poller — relative because the iframe runs
        // under the station origin, same as the widget itself.
        $cacheParam = $request->getParam('cache');
        $this->view->dataUrl = '/Embed/now-playing-data'
            . ($cacheParam !== null ? '?cache=' . urlencode($cacheParam) : '');
    }

    /**
     * Read & clamp the ?cache=N URL parameter.  Default 60 s.
     */
    private function _resolveCacheTtl()
    {
        $raw = (int) $this->getRequest()->getParam('cache', 60);
        return max(10, min(3600, $raw ?: 60));
    }

    /**
     * Resolve the requested timezone (?timezone=...) or fall back to
     * the station default.
     */
    private function _resolveTimezone()
    {
        $tz = $this->getRequest()->getParam('timezone');
        if (!$tz || !in_array($tz, timezone_identifiers_list(), true)) {
            $tz = Application_Model_Preference::GetDefaultTimezone();
        }
        return $tz;
    }

    /**
     * Set Cache-Control + Expires headers for the given TTL.
     */
    private function _emitCacheHeaders($ttl)
    {
        header('Cache-Control: public, max-age=' . (int) $ttl);
        header('Expires: ' . gmdate('D, d M Y H:i:s', time() + (int) $ttl) . ' GMT');
    }

    /**
     * Assemble the slim payload both widgets consume.
     *
     * Pulled from the same Schedule::GetPlayOrderRange() that
     * ApiController::liveInfoV2Action uses, but trimmed to only
     * the fields the widgets actually render so the JSON payload
     * stays around 1-2 kB rather than the full ~20 kB live-info
     * response.
     */
    private function _buildNowPlayingPayload($timezone)
    {
        $range = Application_Model_Schedule::GetPlayOrderRange();

        $now = $range['station']['schedulerTime'] ?? gmdate(DEFAULT_TIMESTAMP_FORMAT);

        return [
            'now' => $this->_formatTimestamp($now, $timezone),
            'show' => [
                'current' => $this->_slimShow($range['shows']['current'] ?? null, $timezone),
                'next'    => $this->_slimShow($range['shows']['next'] ?? null, $timezone),
            ],
            'track' => [
                'current' => $this->_slimTrack($range['tracks']['current'] ?? null, $timezone),
                'next'    => $this->_slimTrack($range['tracks']['next'] ?? null, $timezone),
            ],
            // RASTATIME 2026-05-22 — empty-state labels shipped with
            // the payload so the in-iframe JS uses the operator-
            // configured strings on refresh, not the hard-coded
            // English fallbacks from the JS source.
            'labels' => [
                'noCurrentShow'  => Application_Model_Preference::GetWidgetNoCurrentShow(),
                'noUpcomingShow' => Application_Model_Preference::GetWidgetNoUpcomingShow(),
                'noCurrentTrack' => Application_Model_Preference::GetWidgetNoCurrentTrack(),
                'noUpcomingTrack'=> Application_Model_Preference::GetWidgetNoUpcomingTrack(),
            ],
            'timezone' => $timezone,
        ];
    }

    /**
     * Reduce a Show entry to just the four fields the widgets render.
     *
     * Returns null when the entry is missing, not an array, or
     * carries an empty name — the upstream Schedule model populates
     * a stub `{ name: "", starts: null, ends: null }` for "no show",
     * which the template's `?? 'No upcoming show'` fallback wouldn't
     * otherwise catch (empty string is not null).  Normalising to a
     * single null here lets the template stay simple.
     */
    private function _slimShow($show, $timezone)
    {
        if (empty($show) || !is_array($show)) {
            return null;
        }
        $name = isset($show['name']) ? trim((string) $show['name']) : '';
        if ($name === '') {
            return null;
        }
        return [
            'name'   => $name,
            'starts' => $this->_formatTimestamp($show['starts'] ?? null, $timezone),
            'ends'   => $this->_formatTimestamp($show['ends'] ?? null, $timezone),
        ];
    }

    /**
     * Reduce a Track entry to Artist + Title + start + end.  The
     * artist field is optional; the template shows the title alone
     * when artist is empty.
     *
     * Returns null when both title and artist are empty (same null-
     * normalisation rationale as _slimShow above).
     */
    private function _slimTrack($track, $timezone)
    {
        if (empty($track) || !is_array($track)) {
            return null;
        }
        $meta = $track['metadata'] ?? [];
        $title  = trim((string) ($meta['track_title'] ?? ($track['name'] ?? '')));
        $artist = trim((string) ($meta['artist_name'] ?? ''));
        if ($title === '' && $artist === '') {
            return null;
        }
        return [
            'title'  => $title,
            'artist' => $artist,
            'starts' => $this->_formatTimestamp(
                $track['starts'] ?? ($track['start'] ?? null),
                $timezone
            ),
            'ends'   => $this->_formatTimestamp(
                $track['ends'] ?? ($track['end'] ?? null),
                $timezone
            ),
        ];
    }

    /**
     * Normalise a timestamp to an ISO-8601 string in the requested
     * timezone.  Accepts either a UTC-string (as Schedule returns)
     * or null.  Returns null if the input is unusable.
     */
    private function _formatTimestamp($ts, $timezone)
    {
        if (empty($ts)) {
            return null;
        }
        try {
            $dt = new DateTime($ts, new DateTimeZone('UTC'));
            $dt->setTimezone(new DateTimeZone($timezone));
            return $dt->format(DateTime::ATOM);
        } catch (Exception $e) {
            return null;
        }
    }

    /**
     * RASTATIME 2026-05-22 — Next Shows Widget.
     *
     * Lists the upcoming N instances of a single recurring show as
     * a chronological table (oldest at top, newest at bottom).
     * Drop-in iframe:
     *
     *   <iframe src=".../embed/next-shows?show_id=42&limit=4"
     *           width="300" height="120" frameborder="0"></iframe>
     *
     * URL parameters:
     *   show_id  - cc_show.id of the show to filter on.  Stable
     *              across renames; covers all instances of a
     *              recurring show (since all share the show_id).
     *   show     - cc_show.name; used only as a fallback when
     *              show_id is absent.  Case-sensitive exact match.
     *              show_id takes precedence when both are set.
     *   limit    - 1..20, default 4.
     *   theme    - auto | dark | light  (default auto)
     *   cache    - 10..3600 s (default 60)
     *   overflow - ellipsis | marquee  (default ellipsis)
     *   timezone - any IANA zone (default station)
     *
     * See nowPlayingShowAction docstring for the broader rationale
     * (no auth, iframe-only, two-layer caching, etc.) which
     * applies to all the public embed widgets.
     */
    public function nextShowsAction()
    {
        $this->_prepareShowsListView('next');
    }

    /**
     * RASTATIME 2026-05-22 — Latest Shows Widget.
     *
     * Same as nextShowsAction but lists the most recent N PAST
     * instances of the show (newest at top, oldest at bottom —
     * chronologically reversed compared to next-shows).  Default
     * limit is 3 rather than 4 (operator-typical: "the last
     * couple of episodes" vs "the upcoming week").
     */
    public function latestShowsAction()
    {
        $this->_prepareShowsListView('latest');
    }

    /**
     * RASTATIME 2026-05-22 — JSON feed shared by next-shows /
     * latest-shows widgets.  Polled by the in-iframe JS every
     * cache-TTL seconds for refresh.
     */
    public function showsDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $request = $this->getRequest();
        $cacheTtl = $this->_resolveCacheTtl();
        $timezone = $this->_resolveTimezone();
        $direction = $request->getParam('direction', 'next');
        if (!in_array($direction, ['next', 'latest'], true)) {
            $direction = 'next';
        }
        $showId = $this->_resolveShowId(
            $request->getParam('show_id'),
            $request->getParam('show')
        );
        $limit = $this->_resolveShowsLimit($direction);

        $payload = [
            'direction' => $direction,
            'show'      => $showId !== null ? $this->_fetchShowMeta($showId) : null,
            'instances' => $showId !== null
                ? $this->_fetchShowInstances($showId, $direction, $limit, $timezone)
                : [],
            'limit'     => $limit,
            'timezone'  => $timezone,
            // RASTATIME 2026-05-22 — shipped with each refresh so a
            // label change in Widgets -> Next/Latest Shows shows up
            // within one cache TTL without a manual iframe reload.
            'labels'    => [
                'noNextShows'   => Application_Model_Preference::GetWidgetNoNextShows(),
                'noLatestShows' => Application_Model_Preference::GetWidgetNoLatestShows(),
            ],
        ];

        header('Content-Type: application/json; charset=utf-8');
        $this->_emitCacheHeaders($cacheTtl);
        echo json_encode($payload);
    }

    /**
     * Shared view-population for next-shows / latest-shows actions.
     */
    private function _prepareShowsListView($direction)
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        $overflow = $request->getParam('overflow', 'ellipsis');
        if (!in_array($overflow, ['ellipsis', 'marquee'], true)) {
            $overflow = 'ellipsis';
        }
        $this->view->overflowClass = 'np-overflow-' . $overflow;

        $cacheTtl = $this->_resolveCacheTtl();
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();
        $this->view->timezone = $timezone;
        $this->view->direction = $direction;

        $showId = $this->_resolveShowId(
            $request->getParam('show_id'),
            $request->getParam('show')
        );

        $limit = $this->_resolveShowsLimit($direction);
        $this->view->limit = $limit;

        $this->view->showMeta  = $showId !== null
            ? $this->_fetchShowMeta($showId)
            : null;
        $this->view->instances = $showId !== null
            ? $this->_fetchShowInstances($showId, $direction, $limit, $timezone)
            : [];

        // RASTATIME 2026-05-22 — empty-state labels, configurable by
        // the operator under Widgets -> Next/Latest Shows.  Each
        // widget kind picks the matching label so a "next shows"
        // widget with no future instances reads "No upcoming shows"
        // (or the operator's override) while the same template
        // wired as "latest shows" reads "No past shows".
        $this->view->emptyLabel = ($direction === 'latest')
            ? Application_Model_Preference::GetWidgetNoLatestShows()
            : Application_Model_Preference::GetWidgetNoNextShows();

        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/shows-list-widget.js');

        // Data URL for JS-polling, carries direction + the original
        // show identifier so the JS only knows to refresh the same
        // payload it loaded on the first render.
        $params = [
            'direction' => $direction,
            'limit'     => $limit,
        ];
        if ($showId !== null) {
            $params['show_id'] = $showId;
        }
        $cacheParam = $request->getParam('cache');
        if ($cacheParam !== null) {
            $params['cache'] = $cacheParam;
        }
        $this->view->dataUrl = '/Embed/shows-data?' . http_build_query($params);

        // Pick the right view template (the action-default convention
        // would land on "next-shows" / "latest-shows" both fine, but
        // we use a single shared template since the markup is
        // identical aside from the title row which we can drive from
        // $direction).
        $this->_helper->viewRenderer->setScriptAction('shows-list');
    }

    /**
     * Read & clamp ?limit=N URL parameter for shows-list widgets.
     * Default 4 for "next", 3 for "latest" (operator-typical
     * sizes).  Hard cap at 20 so a hand-crafted URL cannot fetch
     * the full year of weekly-show instances.
     */
    private function _resolveShowsLimit($direction)
    {
        $default = ($direction === 'latest') ? 3 : 4;
        $raw = (int) $this->getRequest()->getParam('limit', $default);
        return max(1, min(20, $raw ?: $default));
    }

    /**
     * Resolve a show identifier from either ?show_id or ?show.
     * Returns the cc_show.id integer, or null if neither parameter
     * was set or no row matched.  show_id takes precedence over
     * show name when both are set.
     */
    private function _resolveShowId($idParam, $nameParam)
    {
        if ($idParam !== null && $idParam !== '' && is_numeric($idParam)) {
            $candidate = (int) $idParam;
            // Verify the id actually exists so an invalid URL
            // returns "no instances" rather than 500-ing later in
            // the SQL pipeline.
            $sql = 'SELECT id FROM cc_show WHERE id = :id LIMIT 1';
            $row = Application_Common_Database::prepareAndExecute(
                $sql,
                [':id' => $candidate],
                'column'
            );
            if ($row) {
                return $candidate;
            }
            return null;
        }
        if ($nameParam !== null && $nameParam !== '') {
            // Case-sensitive exact match — operator decision: if the
            // operator types "morning Show" but the show is named
            // "Morning Show", the embed should fail loudly (empty
            // widget) rather than silently match.  ILIKE here would
            // also collide with same-prefix shows ("Morning Show" +
            // "Morning Show Special").
            $sql = 'SELECT id FROM cc_show WHERE name = :n LIMIT 1';
            $row = Application_Common_Database::prepareAndExecute(
                $sql,
                [':n' => (string) $nameParam],
                'column'
            );
            if ($row) {
                return (int) $row;
            }
        }
        return null;
    }

    /**
     * Fetch the show's display-name + URL + description for the
     * widget header row.  Returns null when the id no longer exists
     * (covers the edge case of an in-flight delete).
     */
    private function _fetchShowMeta($showId)
    {
        $sql = 'SELECT id, name, url, description, image_path
                FROM cc_show
                WHERE id = :id
                LIMIT 1';
        $row = Application_Common_Database::prepareAndExecute(
            $sql,
            [':id' => (int) $showId],
            'all'
        );
        if (empty($row)) {
            return null;
        }
        return [
            'id'          => (int) $row[0]['id'],
            'name'        => (string) $row[0]['name'],
            'url'         => (string) $row[0]['url'],
            'description' => (string) $row[0]['description'],
        ];
    }

    /**
     * Fetch up to $limit upcoming or past instances of the given
     * show as a chronological list, converted to the requested
     * timezone.  Output rows: ['starts' => ISO, 'ends' => ISO].
     *
     * Direction 'next' → starts >= NOW(), ORDER BY starts ASC.
     * Direction 'latest' → starts < NOW(), ORDER BY starts DESC.
     *
     * Modified-instance rows (`modified_instance = TRUE`) are
     * excluded so a moved/cancelled single instance does not
     * leave a phantom in the widget — matches the convention
     * Show::getNextShows uses.
     */
    private function _fetchShowInstances($showId, $direction, $limit, $timezone)
    {
        if ($direction === 'latest') {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc
                    FROM cc_show_instances si
                    WHERE si.show_id = :sid
                      AND si.starts < NOW() AT TIME ZONE 'UTC'
                      AND si.modified_instance != TRUE
                    ORDER BY si.starts DESC
                    LIMIT :lim";
        } else {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc
                    FROM cc_show_instances si
                    WHERE si.show_id = :sid
                      AND si.starts >= NOW() AT TIME ZONE 'UTC'
                      AND si.modified_instance != TRUE
                    ORDER BY si.starts ASC
                    LIMIT :lim";
        }
        $rows = Application_Common_Database::prepareAndExecute(
            $sql,
            [
                ':sid' => (int) $showId,
                ':lim' => (int) $limit,
            ],
            'all'
        );
        $out = [];
        foreach ($rows as $r) {
            $out[] = [
                'starts' => $this->_formatTimestamp($r['starts_utc'], $timezone),
                'ends'   => $this->_formatTimestamp($r['ends_utc'],   $timezone),
            ];
        }
        return $out;
    }

    public function weeklyProgramAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $this->view->angular = Config::getPublicUrl() . Assets::url('js/libs/angular.min.js');
        $widgetStyle = $request->getParam('style');
        if ($widgetStyle == 'premium') {
            $this->view->widgetStyle = 'premium';
            $this->view->css = Assets::url('css/embed/weekly-schedule-widget.css');
        } else {
            $this->view->widgetStyle = 'basic';
            $this->view->css = Assets::url('css/embed/weekly-schedule-widget-basic.css');
        }
        $this->view->jquery = Assets::url('js/libs/jquery-1.8.3.min.js');

        $weeklyScheduleData = WidgetHelper::getWeekInfoV2();

        $this->view->schedule_data = json_encode($weeklyScheduleData);

        $currentDay = new DateTime('now', new DateTimeZone(Application_Model_Preference::GetTimezone()));
        // day of the month without leading zeros (1 to 31)
        $this->view->currentDayOfMonth = $currentDay->format('j');
    }
}
