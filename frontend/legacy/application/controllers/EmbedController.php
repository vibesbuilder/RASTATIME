<?php

class EmbedController extends Zend_Controller_Action
{
    /**
     * RASTATIME 2026-05-22 — Default total row count for the
     * On-Air-Today widget (1 current + 5 upcoming).  Operator can
     * override at the URL level with ?limit=N (clamped 1..20) and
     * a developer can change this default without touching the
     * URL-resolver code.
     */
    const ON_AIR_TODAY_DEFAULT_LIMIT = 6;

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
        $showIds = $this->_resolveShowIds(
            $request->getParam('show_id'),
            $request->getParam('show')
        );
        $limit = $this->_resolveShowsLimit($direction);

        $payload = [
            'direction' => $direction,
            'show'      => !empty($showIds) ? $this->_fetchShowMeta($showIds) : null,
            'instances' => !empty($showIds)
                ? $this->_fetchShowInstances($showIds, $direction, $limit, $timezone)
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

        $showIds = $this->_resolveShowIds(
            $request->getParam('show_id'),
            $request->getParam('show')
        );

        $limit = $this->_resolveShowsLimit($direction);
        $this->view->limit = $limit;

        $this->view->showMeta  = !empty($showIds)
            ? $this->_fetchShowMeta($showIds)
            : null;
        $this->view->instances = !empty($showIds)
            ? $this->_fetchShowInstances($showIds, $direction, $limit, $timezone)
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
        // Round-trip whatever identifier the operator used to load
        // the iframe: if they passed ?show_id we re-use it (cheaper
        // db round-trip on refresh); if they passed ?show we keep
        // the name so the multi-instance match stays intact.
        $rawShowId   = $request->getParam('show_id');
        $rawShowName = $request->getParam('show');
        if ($rawShowId !== null && $rawShowId !== '' && is_numeric($rawShowId)) {
            $params['show_id'] = (int) $rawShowId;
        } elseif ($rawShowName !== null && $rawShowName !== '') {
            $params['show'] = (string) $rawShowName;
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
     * Resolve a list of cc_show.id values from either ?show_id or
     * ?show.  Returns an array of ints (always — empty when nothing
     * matched, single-element for ?show_id, possibly multi-element
     * for ?show when several shows share the same name).
     *
     * show_id takes precedence over show name when both are set,
     * mirroring the precedence advertised in the widget docs.
     *
     * RASTATIME 2026-05-22 v2: previously this returned a single
     * id (or null) for ?show=Name and silently dropped duplicates;
     * the operator pointed out that stations frequently have
     * several shows with the same display name (e.g. one per
     * weekday).  The new contract aggregates ids so the widget
     * shows every instance of a same-named show family.
     */
    private function _resolveShowIds($idParam, $nameParam)
    {
        if ($idParam !== null && $idParam !== '' && is_numeric($idParam)) {
            $candidate = (int) $idParam;
            // Verify the id actually exists so an invalid URL
            // returns "no instances" rather than 500-ing later
            // in the SQL pipeline.
            $sql = 'SELECT id FROM cc_show WHERE id = :id LIMIT 1';
            $row = Application_Common_Database::prepareAndExecute(
                $sql,
                [':id' => $candidate],
                'column'
            );
            return $row ? [$candidate] : [];
        }
        if ($nameParam !== null && $nameParam !== '') {
            // Case-sensitive exact match — operator decision: if
            // the operator types "morning Show" but the show is
            // named "Morning Show", the embed should fail loudly
            // (empty widget) rather than silently match.  ILIKE
            // here would also collide with same-prefix shows
            // ("Morning Show" + "Morning Show Special").
            $sql = 'SELECT id FROM cc_show WHERE name = :n ORDER BY id ASC';
            $rows = Application_Common_Database::prepareAndExecute(
                $sql,
                [':n' => (string) $nameParam],
                'all'
            );
            $out = [];
            foreach ($rows as $r) {
                $out[] = (int) $r['id'];
            }
            return $out;
        }
        return [];
    }

    /**
     * Fetch the show family's display-name + URL + description for
     * the widget header row.  Takes an array of cc_show.id values
     * (a single-element array for a unique show; multiple ids for
     * same-named shows aggregated by `?show=Name`).
     *
     * Returns the metadata of the first id; when multiple ids
     * share the same name (the multi-instance case) all rows have
     * identical `name`, so picking the first is fine — but we
     * surface the full id list under `ids` so the JS / template
     * can show "(3 shows)" or similar if it wants.
     *
     * Returns null when the id list is empty or no row matches
     * (in-flight delete edge case).
     */
    private function _fetchShowMeta($showIds)
    {
        if (empty($showIds)) {
            return null;
        }
        $first = (int) $showIds[0];
        $sql = 'SELECT id, name, url, description, image_path
                FROM cc_show
                WHERE id = :id
                LIMIT 1';
        $row = Application_Common_Database::prepareAndExecute(
            $sql,
            [':id' => $first],
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
            'ids'         => array_map('intval', $showIds),
        ];
    }

    /**
     * Fetch up to $limit upcoming or past instances across the
     * given show id list, as a single chronological list converted
     * to the requested timezone.  Output rows: ['starts' => ISO,
     * 'ends' => ISO].
     *
     * Direction 'next' → starts >= NOW(), ORDER BY starts ASC.
     * Direction 'latest' → starts < NOW(), ORDER BY starts DESC.
     *
     * Modified-instance rows (`modified_instance = TRUE`) are
     * excluded so a moved/cancelled single instance does not
     * leave a phantom in the widget — matches the convention
     * Show::getNextShows uses.
     *
     * Multi-id support (2026-05-22 v2): the SQL uses
     * `show_id = ANY(:sids)` so the widget can list the merged
     * timeline of every show that shares the name passed via
     * `?show=Name`, instead of silently dropping all but the
     * first id.  Postgres array literal is constructed in PHP
     * to keep the prepared statement parameter binding simple.
     */
    private function _fetchShowInstances($showIds, $direction, $limit, $timezone)
    {
        if (empty($showIds)) {
            return [];
        }
        // Build the Postgres array literal manually.  Every entry
        // is an int (enforced by _resolveShowIds) so concatenation
        // is safe; we don't risk SQL injection through the literal.
        $intIds = array_map('intval', $showIds);
        $pgArray = '{' . implode(',', $intIds) . '}';

        if ($direction === 'latest') {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc
                    FROM cc_show_instances si
                    WHERE si.show_id = ANY(:sids)
                      AND si.starts < NOW() AT TIME ZONE 'UTC'
                      AND si.modified_instance != TRUE
                    ORDER BY si.starts DESC
                    LIMIT :lim";
        } else {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc
                    FROM cc_show_instances si
                    WHERE si.show_id = ANY(:sids)
                      AND si.starts >= NOW() AT TIME ZONE 'UTC'
                      AND si.modified_instance != TRUE
                    ORDER BY si.starts ASC
                    LIMIT :lim";
        }
        $rows = Application_Common_Database::prepareAndExecute(
            $sql,
            [
                ':sids' => $pgArray,
                ':lim'  => (int) $limit,
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

    /**
     * RASTATIME 2026-05-22 — On-Air-Today Widget (iframe embed).
     *
     * Lists today's schedule: the currently-airing show (if any)
     * plus the upcoming N shows of the same station day, capped at
     * the station's midnight so the widget never spills into
     * tomorrow's programme.  Drop-in iframe:
     *
     *   <iframe src=".../embed/on-air-today"
     *           width="300" height="250" frameborder="0"></iframe>
     *
     * URL parameters:
     *   limit    - 1..20 total rows (current + upcoming).  Default
     *              ON_AIR_TODAY_DEFAULT_LIMIT (6 = 1 current + 5
     *              upcoming).
     *   day      - optional YYYY-MM-DD (in the resolved timezone)
     *              to render a non-today day.  When omitted (or
     *              equal to today), the widget filters out shows
     *              that have already aired; for any other day it
     *              lists every show whose start falls inside that
     *              day's 24-hour window.  Modified / cancelled
     *              instances are excluded in both modes.
     *   theme    - auto | dark | light  (default auto)
     *   cache    - 10..3600 s (default 60)
     *   overflow - ellipsis | marquee  (default ellipsis)
     *   timezone - any IANA zone (default station)
     *
     * Each row carries the show's name + start–end time-of-day +
     * the show's URL (when configured under Show → Edit → URL) so
     * the in-template renderer can wrap the name in an <a> tag
     * that opens in a new tab via target="_blank".
     */
    public function onAirTodayAction()
    {
        $this->_prepareOnAirTodayView();
    }

    /**
     * RASTATIME 2026-05-22 — JSON feed for the On-Air-Today widget.
     * Polled by the in-iframe JS every cache-TTL seconds; reuses
     * the same Cache-Control envelope as the iframe HTML.
     */
    public function onAirTodayDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $request = $this->getRequest();
        $cacheTtl = $this->_resolveCacheTtl();
        $timezone = $this->_resolveTimezone();
        $limit    = $this->_resolveOnAirTodayLimit();
        $window   = $this->_resolveOnAirTodayWindow($timezone, $request->getParam('day'));

        $payload = [
            'isToday'  => $window['is_today'],
            'dayLabel' => $window['day_label'],
            'dayLocal' => $window['day_local'],
            'shows'    => $this->_fetchOnAirTodayShows($window, $limit, $timezone),
            'limit'    => $limit,
            'timezone' => $timezone,
            // RASTATIME 2026-05-22 — shipped with each refresh so a
            // label change in Widgets -> On Air Today shows up
            // within one cache TTL without a manual iframe reload.
            'labels'   => [
                'noOnAirToday' => Application_Model_Preference::GetWidgetNoOnAirToday(),
            ],
        ];

        header('Content-Type: application/json; charset=utf-8');
        $this->_emitCacheHeaders($cacheTtl);
        echo json_encode($payload);
    }

    /**
     * Shared view-population for the On-Air-Today action.
     */
    private function _prepareOnAirTodayView()
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

        // RASTATIME 2026-05-22 v3 — operator-configurable link
        // style.  Default flipped from 'underline' to 'plain' on
        // operator request: the underline competes with the
        // already-bold show names and makes the row layout look
        // cluttered.  'underline' is still available as an
        // opt-in URL parameter for embedding pages that want
        // the classic hyperlink affordance.
        $linkStyle = $request->getParam('link', 'plain');
        if (!in_array($linkStyle, ['underline', 'plain'], true)) {
            $linkStyle = 'plain';
        }
        $this->view->linkClass = 'np-link-' . $linkStyle;

        $cacheTtl = $this->_resolveCacheTtl();
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();
        $this->view->timezone = $timezone;

        $limit  = $this->_resolveOnAirTodayLimit();
        $window = $this->_resolveOnAirTodayWindow(
            $timezone,
            $request->getParam('day')
        );
        $this->view->limit    = $limit;
        $this->view->isToday  = $window['is_today'];
        $this->view->dayLabel = $window['day_label'];
        $this->view->dayLocal = $window['day_local'];
        $this->view->shows    = $this->_fetchOnAirTodayShows(
            $window,
            $limit,
            $timezone
        );

        // RASTATIME 2026-05-22 — operator-configurable empty-state
        // label.  Defaults to English "No shows on air today" via
        // the GetWidgetNoOnAirToday English-fallback.
        $this->view->emptyLabel = Application_Model_Preference::GetWidgetNoOnAirToday();

        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/on-air-today-widget.js');

        // JS-poller URL: carry the day-override if the operator
        // pinned a specific day, so the refresh fetches the same
        // payload.
        $params = ['limit' => $limit];
        if (!$window['is_today']) {
            $params['day'] = $window['day_local'];
        }
        $cacheParam = $request->getParam('cache');
        if ($cacheParam !== null) {
            $params['cache'] = $cacheParam;
        }
        $this->view->dataUrl = '/Embed/on-air-today-data?' . http_build_query($params);
    }

    /**
     * Read & clamp ?limit=N URL parameter.  Default
     * ON_AIR_TODAY_DEFAULT_LIMIT (6), hard cap 20 so a hand-crafted
     * URL cannot fetch a full station-day of half-hour slots.
     */
    private function _resolveOnAirTodayLimit()
    {
        $raw = (int) $this->getRequest()->getParam(
            'limit',
            self::ON_AIR_TODAY_DEFAULT_LIMIT
        );
        return max(1, min(20, $raw ?: self::ON_AIR_TODAY_DEFAULT_LIMIT));
    }

    /**
     * Resolve the day-window from an optional ?day=YYYY-MM-DD URL
     * parameter.  Always falls back to "today in $timezone".
     *
     * Returns an associative array with:
     *   start_utc - day-start (00:00 local) converted to UTC,
     *               formatted as "YYYY-MM-DD HH:MM:SS"
     *   end_utc   - day-end (next midnight local) converted to UTC
     *   is_today  - bool, true when day == today in $timezone
     *   day_local - the chosen day as YYYY-MM-DD (in $timezone)
     *   day_label - null when is_today, else a human-readable label
     *               like "Sat, 25 May 2026" for the header
     */
    private function _resolveOnAirTodayWindow($timezone, $dayParam)
    {
        $tz = new DateTimeZone($timezone);

        // Default = today; only swap to the parameter when it
        // matches the strict YYYY-MM-DD format AND parses cleanly.
        $dayStart = new DateTime('today', $tz);
        if ($dayParam !== null && $dayParam !== ''
                && preg_match('/^\d{4}-\d{2}-\d{2}$/', $dayParam)) {
            try {
                $candidate = new DateTime($dayParam . ' 00:00:00', $tz);
                $dayStart = $candidate;
            } catch (Exception $e) {
                // Bad date — silently fall back to today rather
                // than 500-ing, since this is a public endpoint
                // and a typo'd embed URL should still render.
            }
        }

        $today    = new DateTime('today', $tz);
        $isToday  = ($dayStart->format('Y-m-d') === $today->format('Y-m-d'));

        $dayEnd = clone $dayStart;
        $dayEnd->modify('+1 day');

        $utc = new DateTimeZone('UTC');
        $startUtc = (clone $dayStart)->setTimezone($utc);
        $endUtc   = (clone $dayEnd)->setTimezone($utc);

        return [
            'start_utc' => $startUtc->format('Y-m-d H:i:s'),
            'end_utc'   => $endUtc->format('Y-m-d H:i:s'),
            'is_today'  => $isToday,
            'day_local' => $dayStart->format('Y-m-d'),
            'day_label' => $isToday ? null : $dayStart->format('D, j M Y'),
        ];
    }

    /**
     * Fetch up to $limit show instances for the given day-window,
     * joined to cc_show for the display name + show-URL.  Two
     * filter modes:
     *
     *   - today (`is_today === true`): the widget shows the
     *     currently-airing show plus upcoming shows of the same
     *     day, so we require `ends > NOW()` (not yet finished)
     *     AND `starts < day_end` (started before tomorrow's
     *     midnight).  A show that started yesterday 23:30 and is
     *     still on air at 14:00 today counts as current.
     *
     *   - any other day: the operator pinned a specific date, so
     *     we list every show whose start falls inside that day's
     *     24-hour window (regardless of whether it has already
     *     aired or not yet started).  Useful for historical / next
     *     week overviews on a station's website.
     *
     * Modified-instance rows are excluded in both modes (matches
     * the convention `Application_Model_Show::getNextShows` uses
     * on the internal Dashboard) so a cancelled / moved single
     * instance doesn't leave a phantom row in the widget.
     */
    private function _fetchOnAirTodayShows($window, $limit, $timezone)
    {
        if ($window['is_today']) {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc,
                           s.id      AS show_id,
                           s.name    AS show_name,
                           s.url     AS show_url
                    FROM cc_show_instances si
                    JOIN cc_show s ON s.id = si.show_id
                    WHERE si.modified_instance != TRUE
                      AND si.ends   > NOW() AT TIME ZONE 'UTC'
                      AND si.starts < :day_end
                    ORDER BY si.starts ASC
                    LIMIT :lim";
            $params = [
                ':day_end' => $window['end_utc'],
                ':lim'     => (int) $limit,
            ];
        } else {
            $sql = "SELECT si.starts AS starts_utc,
                           si.ends   AS ends_utc,
                           s.id      AS show_id,
                           s.name    AS show_name,
                           s.url     AS show_url
                    FROM cc_show_instances si
                    JOIN cc_show s ON s.id = si.show_id
                    WHERE si.modified_instance != TRUE
                      AND si.starts >= :day_start
                      AND si.starts <  :day_end
                    ORDER BY si.starts ASC
                    LIMIT :lim";
            $params = [
                ':day_start' => $window['start_utc'],
                ':day_end'   => $window['end_utc'],
                ':lim'       => (int) $limit,
            ];
        }

        $rows = Application_Common_Database::prepareAndExecute(
            $sql,
            $params,
            'all'
        );

        $nowUtcMs = (int) (microtime(true) * 1000);

        $out = [];
        foreach ($rows as $r) {
            $startsIso = $this->_formatTimestamp($r['starts_utc'], $timezone);
            $endsIso   = $this->_formatTimestamp($r['ends_utc'],   $timezone);

            // Mark "current" = started before now and still ending
            // in the future.  Lets the template / JS highlight the
            // airing row without re-evaluating the wall clock in
            // multiple places.
            $startsMs = $startsIso ? strtotime($r['starts_utc'] . ' UTC') * 1000 : null;
            $endsMs   = $endsIso   ? strtotime($r['ends_utc']   . ' UTC') * 1000 : null;
            $isCurrent = ($startsMs !== null && $endsMs !== null
                          && $startsMs <= $nowUtcMs && $endsMs > $nowUtcMs);

            $out[] = [
                'showId'    => (int) $r['show_id'],
                'name'      => (string) $r['show_name'],
                'url'       => (string) $r['show_url'],
                'starts'    => $startsIso,
                'ends'      => $endsIso,
                'isCurrent' => $isCurrent,
            ];
        }
        return $out;
    }

    /**
     * RASTATIME 2026-05-22 — Weekly Schedule Widget v2 (iframe embed).
     *
     * Modernised replacement for the upstream jQuery 1.8.3 + Handlebars
     * widget.  Drop-in iframe (height ~340 to comfortably fit a 7-day
     * tab block + header):
     *
     *     <iframe src=".../embed/weekly-program?theme=dark"
     *             width="100%" height="340" frameborder="0"></iframe>
     *
     * URL parameters (Wave-1 convention):
     *   theme       - auto | dark | light  (default auto)
     *   cache       - 10..3600 s server-side TTL  (default 60)
     *   overflow    - ellipsis | marquee  (default ellipsis)
     *   link        - plain | underline  (default plain — matches
     *                 the On-Air-Today widget's polished default)
     *   timezone    - any IANA zone (default station)
     *   week_offset - -52..52 weeks (default 0).  ◀ / ▶ buttons in
     *                 the rendered widget edit the URL in-place to
     *                 navigate the window without a backend round-
     *                 trip until the next refresh.
     *   bg          - optional URL of a background image.  When set,
     *                 the widget body renders the image as a cover
     *                 background instead of the default transparent
     *                 fill.  Operator hosts the image themselves
     *                 (typically on the station's own site).
     */
    public function weeklyProgramAction()
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

        // Link style follows the On-Air-Today widget's polish: plain
        // (no underline) is the default for a clean text layout; the
        // hyperlink affordance can be opted back in with ?link=underline.
        $linkStyle = $request->getParam('link', 'plain');
        if (!in_array($linkStyle, ['underline', 'plain'], true)) {
            $linkStyle = 'plain';
        }
        $this->view->linkClass = 'np-link-' . $linkStyle;

        $cacheTtl = $this->_resolveCacheTtl();
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();
        $this->view->timezone = $timezone;

        // Week-offset: pin the rendered window to ±N weeks from
        // today's rolling 7-day block.  Operator-requested cap:
        // -2 (two weeks back) to +4 (four weeks ahead) — wider
        // ranges aren't useful on a public homepage and the
        // tight cap also lets the JS disable the ◀ / ▶ buttons
        // at the limits.  Constants are exposed to the view so
        // the JS shares the same clamp without duplication.
        $rawOffset = (int) $request->getParam('week_offset', 0);
        $weekOffsetMin = -2;
        $weekOffsetMax = 4;
        $weekOffset = max($weekOffsetMin, min($weekOffsetMax, $rawOffset));
        $this->view->weekOffset    = $weekOffset;
        $this->view->weekOffsetMin = $weekOffsetMin;
        $this->view->weekOffsetMax = $weekOffsetMax;

        $weeklyScheduleData = WidgetHelper::getWeekInfoV2($weekOffset);
        $this->view->schedule_data = json_encode($weeklyScheduleData);

        // Optional background-image URL — the template wires it
        // through a CSS variable so the stylesheet can switch
        // between transparent fill and cover-image without any
        // class juggling.
        $bgUrl = (string) $request->getParam('bg', '');
        $this->view->backgroundUrl = $bgUrl;

        // Optional background-color (hex only, e.g. #222 or
        // #112233 or #11223344 with alpha).  Validated against a
        // strict regex so the value can't smuggle CSS via the
        // inline style attribute the template emits.  Operator
        // can stack ?bgcolor + ?bg (image): the colour shows
        // through transparent parts of the image and acts as a
        // fallback while the image loads.
        $bgColor = (string) $request->getParam('bgcolor', '');
        if ($bgColor !== '' && !preg_match('/^#[0-9a-fA-F]{3,8}$/', $bgColor)) {
            $bgColor = '';
        }
        $this->view->backgroundColor = $bgColor;

        // Operator-configurable empty-state label.  Defaults to the
        // legacy English string so an upgrading operator sees no
        // visible change until they customise it.
        $this->view->emptyLabel = Application_Model_Preference::GetWidgetNoWeeklyShows();

        // Day-of-month for the "today" highlight in the tab strip.
        $currentDay = new DateTime('now', new DateTimeZone($timezone));
        $this->view->currentDayOfMonth = $currentDay->format('j');

        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/weekly-schedule-widget.js');
    }
}
