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
     * RASTATIME 2026-09-18 — Stream Player Widget v2 (work-order point
     * 12, operator go): the last upstream widget rebuilt in the wave
     * style.  The view (embed/player.phtml) is a self-contained vanilla
     * iframe; this action only resolves the URL parameters into one
     * JSON config blob.
     *
     * URL parameters (all optional; old embeds keep working):
     *   stream = auto (default) | <name from Settings→Streams> | file
     *   file_url / file_codec   - only with stream=file
     *   title                   - header text; absent → header hidden
     *   theme  = auto|dark|light   (np-theme-* pattern like all widgets)
     *   layout = card|bar          (bar = the station-homepage bottom
     *                               bar; the legacy style=premium
     *                               parameter maps to it)
     *   cache  = 10..3600          - forwarded to the metadata poll
     */
    public function playerAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        // Theme, same validation as every other widget.
        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        // Layout; legacy ?style=premium (the pre-v2 bottom-bar skin,
        // still embedded by the station homepage) maps to 'bar'.
        $layout = $request->getParam('layout', '');
        if (!in_array($layout, ['card', 'bar'], true)) {
            $layout = $request->getParam('style') === 'premium' ? 'bar' : 'card';
        }
        $this->view->layout = $layout;

        $title = $request->getParam('title');
        $this->view->playerTitle = ($title === null || $title === '') ? null : $title;

        // Metadata poll target — the widget-family JSON endpoint (no
        // JSONP, no public-API gate).  ?cache=N is forwarded so the
        // browser cache absorbs part of the poll traffic.
        $dataUrl = Config::getBasePath() . 'embed/now-playing-data';
        $cache = (int) $request->getParam('cache', 0);
        if ($cache >= 10 && $cache <= 3600) {
            $dataUrl .= '?cache=' . $cache;
        }

        $stream = $request->getParam('stream', 'auto');
        $streamData = Application_Model_StreamSetting::getEnabledStreamData();

        // RASTATIME 2026-05-20 — normalise the stream-data ``mobile``
        // flag to a real bool.  Upstream stores it as the literal
        // STRING `"false"` (cc_pref serialises everything as strings),
        // which is truthy in PHP and would route every stream into the
        // mobile queue.  No URL rewriting here: a localhost host is
        // rewritten client-side to the page host (embed/player.phtml).
        foreach ($streamData as &$_s) {
            $m = $_s['mobile'] ?? false;
            $_s['mobile'] = ($m === true || $m === 'true' || $m === '1' || $m === 1);
        }
        unset($_s);

        $cfg = [
            'mode' => 'auto',
            'streams' => ['desktop' => [], 'mobile' => []],
            'url' => null,
            'codec' => null,
            'dataUrl' => $dataUrl,
            // RASTATIME 2026-09-18 (W4.1) — cover art: the default is
            // the operator's checkbox on Settings → Widgets → Player
            // (so it also governs the homepage bar, which carries no
            // ?art=); an explicit ?art=on|off in the embed URL wins.
            'art' => $this->_resolveArtFlag(
                $request,
                Application_Model_Preference::GetWidgetPlayerShowArt()
            ),
            'artUrlPrefix' => $this->_artworkUrlPrefix(128),
            // RASTATIME 2026-09-30 - the show's image as the fallback cover
            'showLogoUrlPrefix' => $this->_showLogoUrlPrefix(),
            // RASTATIME 2026-10-01 - the picture and the headline follow the
            // Stream Label (0 Artist - Title, 1 Show - Artist - Title,
            // 2 Station - Show); the default cover closes the chain.
            'streamLabelFormat' => (int) Application_Model_Preference::GetStreamLabelFormat(),
            'stationName' => Application_Model_Preference::GetStationName(),
            'defaultCoverUrl' => $this->_defaultCoverUrl(),
            'labels' => [
                'next' => _('Next'),
                'onAir' => _('On Air'),
                'offAir' => _('Off Air'),
                'offline' => _('Stream unavailable'),
            ],
        ];

        if ($stream === 'file') {
            $cfg['mode'] = 'file';
            $cfg['url'] = (string) $request->getParam('file_url', '');
            $cfg['codec'] = (string) $request->getParam('file_codec', '');
        } elseif ($stream !== 'auto' && isset($streamData[$stream])) {
            $cfg['mode'] = 'manual';
            $cfg['url'] = $streamData[$stream]['url'];
            $cfg['codec'] = $streamData[$stream]['codec'];
        } else {
            // auto (also the fallback for an unknown stream name — the
            // pre-v2 player crashed on that; 2026-09-18 bare-URL fix
            // folded in here).
            foreach ($streamData as $s) {
                $bucket = $s['mobile'] ? 'mobile' : 'desktop';
                $cfg['streams'][$bucket][] = [
                    'url' => $s['url'],
                    'codec' => $s['codec'],
                ];
            }
        }

        $this->view->playerConfigJson = json_encode($cfg, JSON_UNESCAPED_SLASHES);
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
     * RASTATIME 2026-06-07 — Song Request Widget (iframe embed).
     *
     * Interactive widget: a listener types into the search box, the
     * widget queries the public catalogue-search endpoint
     * (GET /api/v2/song-requests/search) restricted to the operator's
     * Requestable Pool, and a "Request" button POSTs the chosen track
     * to /api/v2/song-requests.  Drop-in iframe:
     *
     *   <iframe src=".../embed/song-request?theme=dark"
     *           width="100%" height="420" frameborder="0"></iframe>
     *
     * URL parameters:
     *   theme - auto | dark | light  (default auto)
     *
     * No API auth — the Django endpoints are public + throttled/
     * deduped per IP (see song_request_api.py).  The widget talks to
     * /api/v2 on the same station origin (Apache proxies it), so the
     * fetch URLs are relative.
     */
    public function songRequestAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        // Requesting is only possible when the operator has configured a
        // Requestable Pool (Settings → General).  Surface that so the
        // widget can show a friendly "currently unavailable" state
        // rather than an always-empty search box.
        $poolIds = Application_Model_Preference::getRequestablePoolBlockIds();
        $this->view->requestsEnabled = !empty($poolIds);

        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/song-request-widget.js');
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

        // W4.1 — covers are opt-in here (height="50" embeds, see
        // _resolveArtFlag).
        $this->view->artEnabled = $this->_resolveArtFlag($request, false);
        $this->view->artUrlPrefix = $this->_artworkUrlPrefix(64);
        $this->view->showLogoUrlPrefix = $this->_showLogoUrlPrefix();
        $this->view->defaultCoverUrl = $this->_defaultCoverUrl();

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
     * Callers can supply a different default (e.g. 300 for the
     * Multi-View Schedule which has a larger payload and refreshes
     * less often).
     */
    private function _resolveCacheTtl($defaultSeconds = 60)
    {
        $raw = (int) $this->getRequest()->getParam('cache', $defaultSeconds);
        return max(10, min(3600, $raw ?: $defaultSeconds));
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
    /**
     * RASTATIME 2026-09-18 (W4.1 cover artwork) — resolve ?art=on|off.
     *
     * The caller passes the default: OFF for the two-line Now-Playing
     * widget (documented with height="50" — a cover would change every
     * existing embed), the operator's Settings checkbox for the player.
     */
    private function _resolveArtFlag($request, $default)
    {
        $art = $request->getParam('art');
        if ($art === null || $art === '') {
            return (bool) $default;
        }
        return in_array(strtolower((string) $art), ['1', 'on', 'true', 'yes'], true);
    }

    /**
     * Artwork URL PREFIX; the id is appended by the template / JS.
     *
     * Covers come from the same endpoint the Song-Request widget uses.
     * Two caveats live here:
     *   - it is gated on Settings → Preferences → "Public API"; with the
     *     toggle off the covers 403 and the widgets stay text-only
     *     (graceful: nothing else breaks).
     *   - for a track WITHOUT artwork it answers 0-byte 200/text-html,
     *     which leaves an <img> hanging forever (neither load nor error
     *     fires).  Hence every payload carries hasArtwork and the
     *     consumers must not create an <img> without it.
     */
    private function _artworkUrlPrefix($size = 64)
    {
        return Config::getBasePath() . 'api/track?return=artwork-' . (int) $size . '&id=';
    }

    /**
     * RASTATIME 2026-09-30 - the show image endpoint (Calendar -> show ->
     * image), the fallback cover of the player and the Now Playing - Track
     * widget when the on-air item has no artwork of its own: a webstream,
     * a line-in, a track without a cover.  Same public-API gate as the
     * artwork endpoint; a show whose image file is gone answers with the
     * station logo (redirect), so the <img> never hangs.
     */
    private function _showLogoUrlPrefix()
    {
        return Config::getBasePath() . 'api/show-logo?id=';
    }

    /**
     * RASTATIME 2026-10-01 - the default cover (Settings -> Widgets ->
     * Player), null when none is set.  The URL carries a hash of the
     * picture so a new upload is not hidden by the browser cache.
     *
     * @return null|string
     */
    private function _defaultCoverUrl()
    {
        $b64 = Application_Model_Preference::GetWidgetDefaultCover();
        if ($b64 === null) {
            return null;
        }

        return Config::getBasePath() . 'embed/default-cover?v=' . substr(md5($b64), 0, 10);
    }

    /**
     * The default cover as a PNG (see _defaultCoverUrl).  Public like the
     * other embed routes; a day of caching, the URL changes with the
     * picture.  Without a default cover: 404.
     */
    public function defaultCoverAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $b64 = Application_Model_Preference::GetWidgetDefaultCover();
        if ($b64 === null) {
            $this->getResponse()->setHttpResponseCode(404);

            return;
        }
        $png = base64_decode($b64);
        header('Content-Type: image/png');
        header('Content-Length: ' . strlen($png));
        header('Cache-Control: public, max-age=86400');
        echo $png;
    }

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
            // RASTATIME 2026-09-30 - id + image presence so a consumer can
            // fall back to the show's image when the track has no cover
            'id'       => isset($show['id']) ? (int) $show['id'] : null,
            'hasImage' => isset($show['id']) && trim((string) ($show['image_path'] ?? '')) !== '',
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
        // RASTATIME 2026-09-18 (W4.1) — file id + artwork presence so a
        // consumer can build the cover URL.  A webstream / line-in entry
        // has no cc_files row at all, so both stay null/false.
        $fileId = isset($meta['id']) ? (int) $meta['id'] : null;
        $hasArt = $fileId !== null
            && trim((string) ($meta['artwork'] ?? '')) !== '';
        return [
            'fileId'      => $fileId,
            'hasArtwork'  => $hasArt,
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
        // RASTATIME 2026-10-25 - operator-defined title ('' = default)
        $this->view->titleLabel = Application_Model_Preference::GetWidgetOnAirTodayTitle();

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

    /**
     * RASTATIME 2026-05-22 — Multi-View Schedule widget (iframe).
     *
     * A FullCalendar-powered time-grid view of the station schedule,
     * with operator-switchable Day / 2-Day / Week views.  Sister
     * widget to the Weekly-Schedule v2 (which is a simpler tab
     * widget); this one is intended for stations that want a
     * richer calendar-style embed.
     *
     * Drop-in iframe (~600 px tall to comfortably fit a 24-hour
     * time grid):
     *
     *     <iframe src=".../embed/multi-view-schedule"
     *             width="100%" height="600" frameborder="0"></iframe>
     *
     * URL parameters (Wave-1 convention):
     *   view        - day | 2day | week  (default day)
     *   theme       - auto | dark | light  (default auto)
     *   cache       - 10..3600 s server-side TTL  (default 300 = 5 min,
     *                 longer than the other widgets because the
     *                 calendar payload is larger and refreshes less
     *                 often per operator request)
     *   timezone    - any IANA zone (default station)
     *   bg          - optional URL of a background image
     *   bgcolor     - optional hex background colour
     *
     * The companion JSON endpoint is multiViewScheduleDataAction —
     * FullCalendar's events:function(info,cb) callback hits it with
     * `?from=YYYY-MM-DD&to=YYYY-MM-DD&timezone=...` for the visible
     * range, so view-switches don't reload the page.
     */
    public function multiViewScheduleAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        // Cache TTL: bigger default than the other widgets (5 min
        // vs 60 s).  The calendar payload is larger and the
        // schedule doesn't usually shift mid-day, so a longer
        // cache is acceptable.
        $cacheTtl = $this->_resolveCacheTtl(300);
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();
        $this->view->timezone = $timezone;

        // Default view: day.  Operator can switch via URL parameter
        // and the in-widget toggle buttons.  Maps to a FullCalendar
        // view name client-side, but the controller keeps it human-
        // friendly here so the embed-code reads naturally.
        $view = $request->getParam('view', 'day');
        if (!in_array($view, ['day', '2day', 'week'], true)) {
            $view = 'day';
        }
        $this->view->defaultView = $view;

        // Optional cover background image + solid colour (same
        // contract as the Weekly-Schedule widget).
        $bgUrl = (string) $request->getParam('bg', '');
        $this->view->backgroundUrl = $bgUrl;

        $bgColor = (string) $request->getParam('bgcolor', '');
        if ($bgColor !== '' && !preg_match('/^#[0-9a-fA-F]{3,8}$/', $bgColor)) {
            $bgColor = '';
        }
        $this->view->backgroundColor = $bgColor;

        // Locale for FullCalendar — fall back to the station's
        // default UI locale.  FullCalendar's `locales-all` bundle
        // covers 80+ codes so any IANA-style locale that matches
        // the station setting works.
        $locale = Application_Model_Preference::GetDefaultLocale();
        if (!$locale) {
            $locale = 'en';
        }
        // FullCalendar expects two-letter codes ('en', 'de', 'fr',
        // 'es') or BCP-47 ('en-gb').  Strip a trailing _XX charset
        // suffix the GNU locale identifiers sometimes carry.
        $locale = strtolower(preg_replace('/[._].*$/', '', $locale));
        $this->view->fcLocale = $locale;

        // RASTATIME 2026-05-22 v9 — clock format.  FullCalendar
        // picks the time format from the locale by default, which
        // gives "5 PM" / "6 AM" for english locales — confusing
        // for european stations that expect 24h.  ?clock=24 (the
        // default) forces 24h regardless of locale; ?clock=12
        // forces AM/PM; ?clock=auto leaves it locale-dependent
        // (legacy behaviour, available for opt-in).
        $clock = $request->getParam('clock', '24');
        if (!in_array($clock, ['12', '24', 'auto'], true)) {
            $clock = '24';
        }
        $this->view->clock = $clock;

        $this->view->emptyLabel = Application_Model_Preference::GetWidgetNoMultiViewSchedule();

        $this->view->widgetCss        = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs         = Assets::url('js/airtime/embed/multi-view-schedule-widget.js');
        $this->view->fullCalendarJs   = Assets::url('js/libs/fullcalendar/index.global.min.js');
        $this->view->fullCalendarLoc  = Assets::url('js/libs/fullcalendar/locales-all.global.min.js');
    }

    /**
     * RASTATIME 2026-05-22 — JSON feed for the Multi-View Schedule
     * widget.  Returns events in the format FullCalendar expects,
     * filtered to the date range the client requested.
     *
     * Query params:
     *   from     - YYYY-MM-DD inclusive start (in the resolved
     *              timezone).  Required.
     *   to       - YYYY-MM-DD exclusive end.  Required.
     *   timezone - any IANA zone; defaults to station.
     *
     * Output: array of `{ id, title, start, end, url, description,
     * backgroundColor, borderColor, extendedProps:{ ... } }` objects
     * — FullCalendar's documented event shape.  The
     * `backgroundColor` / `borderColor` come from cc_show.
     * background_color (which is a 6-char hex like "1f8a70", no
     * leading `#`) — the controller prepends `#` so FullCalendar
     * accepts it as a CSS colour.  Empty backgrounds fall through
     * to a tasteful default (the accent colour) client-side.
     */
    public function multiViewScheduleDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $request  = $this->getRequest();
        $cacheTtl = $this->_resolveCacheTtl(300);
        $timezone = $this->_resolveTimezone();

        $tz = new DateTimeZone($timezone);
        $utc = new DateTimeZone('UTC');

        // Parse the from / to params.  Strict YYYY-MM-DD format;
        // fall back to today / today+1 day on bad input so a
        // hand-crafted URL still produces a sane (small) payload.
        $fromParam = (string) $request->getParam('from', '');
        $toParam   = (string) $request->getParam('to',   '');
        try {
            $from = ($fromParam !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $fromParam))
                ? new DateTime($fromParam . ' 00:00:00', $tz)
                : new DateTime('today', $tz);
        } catch (Exception $e) {
            $from = new DateTime('today', $tz);
        }
        try {
            $to = ($toParam !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $toParam))
                ? new DateTime($toParam . ' 00:00:00', $tz)
                : (clone $from)->modify('+1 day');
        } catch (Exception $e) {
            $to = (clone $from)->modify('+1 day');
        }

        // Clamp the range to a reasonable maximum (62 days) so a
        // hand-crafted ?from=2000-01-01&to=2100-01-01 URL can't
        // make the server haul a year's worth of shows.
        $fromCl = clone $from;
        $toMax  = (clone $from)->modify('+62 days');
        if ($to > $toMax) {
            $to = $toMax;
        }

        $fromUtc = (clone $from)->setTimezone($utc)->format('Y-m-d H:i:s');
        $toUtc   = (clone $to)->setTimezone($utc)->format('Y-m-d H:i:s');

        $events = $this->_fetchMultiViewEvents($fromUtc, $toUtc, $timezone);

        header('Content-Type: application/json; charset=utf-8');
        $this->_emitCacheHeaders($cacheTtl);
        echo json_encode([
            'success'  => true,
            'events'   => $events,
            'timezone' => $timezone,
        ]);
    }

    /**
     * Fetch all show instances overlapping the given UTC range,
     * shaped as FullCalendar-compatible event objects.  Direct
     * SQL against cc_show_instances JOIN cc_show — same pattern
     * the other Wave-1 widgets use.  modified_instance != TRUE
     * is filtered so cancelled / moved instances don't leak
     * through.
     */
    private function _fetchMultiViewEvents($fromUtc, $toUtc, $timezone)
    {
        // "Overlap": include any instance that starts before the
        // range ends AND ends after the range starts.  Catches the
        // edge case of a show that started before `from` but is
        // still running into the range.
        $sql = "SELECT si.id          AS instance_id,
                       s.id           AS show_id,
                       s.name         AS show_name,
                       s.url          AS show_url,
                       s.description  AS show_description,
                       s.background_color AS bg_color,
                       s.color        AS text_color,
                       si.starts      AS starts_utc,
                       si.ends        AS ends_utc
                FROM cc_show_instances si
                JOIN cc_show s ON s.id = si.show_id
                WHERE si.modified_instance != TRUE
                  AND si.starts < :to_utc
                  AND si.ends   > :from_utc
                ORDER BY si.starts ASC";

        $rows = Application_Common_Database::prepareAndExecute(
            $sql,
            [
                ':from_utc' => $fromUtc,
                ':to_utc'   => $toUtc,
            ],
            'all'
        );

        $out = [];
        foreach ($rows as $r) {
            $bg = (string) ($r['bg_color'] ?? '');
            $bgHex = ($bg !== '' && preg_match('/^[0-9a-fA-F]{6}$/', $bg))
                ? '#' . $bg
                : null;
            $fg = (string) ($r['text_color'] ?? '');
            $fgHex = ($fg !== '' && preg_match('/^[0-9a-fA-F]{6}$/', $fg))
                ? '#' . $fg
                : null;

            $out[] = [
                'id'              => (int) $r['instance_id'],
                'title'           => (string) $r['show_name'],
                'start'           => $this->_formatTimestamp($r['starts_utc'], $timezone),
                'end'             => $this->_formatTimestamp($r['ends_utc'],   $timezone),
                'url'             => (string) $r['show_url'],
                'backgroundColor' => $bgHex,
                'borderColor'     => $bgHex,
                'textColor'       => $fgHex,
                'extendedProps'   => [
                    'description' => (string) $r['show_description'],
                    'url'         => (string) $r['show_url'],
                    'showId'      => (int) $r['show_id'],
                ],
            ];
        }
        return $out;
    }

    /**
     * RASTATIME 2026-05-22 — Track History Widget (iframe embed,
     * BACKLOG Wave-3).
     *
     * Last-N-days track history widget — operator picks a day
     * (capped at -7..0 from today) and the widget shows the
     * tracks that played that day, paginated.  Click a track →
     * modal with full metadata + show context.
     *
     * Drop-in iframe (~500 px tall to comfortably show 10 rows
     * + header + load-more):
     *
     *     <iframe src=".../embed/track-history"
     *             width="100%" height="500" frameborder="0"></iframe>
     *
     * URL parameters (Wave-1 convention):
     *   date     - YYYY-MM-DD (default today; clamped to -7..0
     *              days from today in the resolved timezone)
     *   pagesize - 10 | 20 | 50 | 100  (default 10)
     *   theme    - auto | dark | light  (default auto)
     *   cache    - 10..3600 s  (default 60)
     *   timezone - any IANA zone (default station)
     *   bg / bgcolor - optional background image / colour
     *
     * Companion JSON endpoint is trackHistoryDataAction —
     * called by the Load-More button + on every date / pagesize
     * change.
     */
    public function trackHistoryAction()
    {
        $this->view->layout()->disableLayout();

        $request = $this->getRequest();

        $theme = $request->getParam('theme', 'auto');
        if (!in_array($theme, ['auto', 'dark', 'light'], true)) {
            $theme = 'auto';
        }
        $this->view->themeClass = 'np-theme-' . $theme;

        $cacheTtl = $this->_resolveCacheTtl(60);
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();
        $this->view->timezone = $timezone;

        // Resolve the requested day, capped to the last 7 days
        // (operator-set scope — BACKLOG specifies "letzte 7 Tage").
        $window = $this->_resolveTrackHistoryDay(
            $timezone,
            $request->getParam('date')
        );
        $this->view->dayLocal  = $window['day_local'];
        $this->view->minDate   = $window['min_local'];
        $this->view->maxDate   = $window['max_local'];

        // RASTATIME 2026-05-22 v14 — initial time of day.  The
        // template seeds the <input type="time"> with this so
        // the widget opens on "now" by default (operator
        // request: "Beim erstmaligen Öffnen soll immer das
        // aktuelle Datum und die aktuelle Zeit gewählt sein").
        // ?time=HH:MM URL parameter overrides for pre-pinned
        // embeds.
        $this->view->timeLocal = $this->_resolveTrackHistoryTime(
            $timezone,
            $request->getParam('time'),
            $window['day_local']
        );

        // Page size — operator can change in-widget via the
        // dropdown.  Initial render uses whatever's in the URL
        // (or 10).
        $pagesize = (int) $request->getParam('pagesize', 10);
        if (!in_array($pagesize, [10, 20, 50, 100], true)) {
            $pagesize = 10;
        }
        $this->view->pagesize = $pagesize;

        // Optional background image + colour, same contract as
        // the Weekly-Schedule + Multi-View widgets.
        $bgUrl = (string) $request->getParam('bg', '');
        $this->view->backgroundUrl = $bgUrl;
        $bgColor = (string) $request->getParam('bgcolor', '');
        if ($bgColor !== '' && !preg_match('/^#[0-9a-fA-F]{3,8}$/', $bgColor)) {
            $bgColor = '';
        }
        $this->view->backgroundColor = $bgColor;

        $this->view->emptyLabel = Application_Model_Preference::GetWidgetNoTrackHistory();

        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/track-history-widget.js');
    }

    /**
     * RASTATIME 2026-05-22 — JSON feed for the Track History
     * widget.  Returns one page of tracks for the requested day,
     * already converted to the visitor's timezone.
     *
     * Query params:
     *   date     - YYYY-MM-DD inclusive day (capped to -7..0
     *              from today).  Default today.
     *   pagesize - 10 | 20 | 50 | 100.  Default 10.
     *   page     - 1..10 (hard cap so ?page=999 doesn't haul a
     *              year of tracks).  Default 1.
     *   timezone - any IANA zone; defaults to station.
     */
    public function trackHistoryDataAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $request  = $this->getRequest();
        $cacheTtl = $this->_resolveCacheTtl(60);
        $timezone = $this->_resolveTimezone();

        $window = $this->_resolveTrackHistoryDay(
            $timezone,
            $request->getParam('date')
        );

        // RASTATIME 2026-05-22 v14 — upper-bound time-of-day
        // filter.  Visitor's date+time picks a point, widget
        // shows tracks that finished BEFORE that point (most
        // recent first).  Initial state is "now", so default
        // behaviour is "what just played".  When the visitor
        // picks an earlier time, the cap shifts back.
        $upperBoundUtc = $this->_resolveTrackHistoryUpperBound(
            $timezone,
            $window['day_local'],
            $request->getParam('time')
        );

        // Exclude-short toggle + threshold: URL params override
        // the operator-configured Preferences when present.
        $excludeShort = $this->_resolveExcludeShortFlag($request);
        $minSeconds   = $this->_resolveMinSecondsThreshold($request);

        $pagesize = (int) $request->getParam('pagesize', 10);
        if (!in_array($pagesize, [10, 20, 50, 100], true)) {
            $pagesize = 10;
        }

        $page = (int) $request->getParam('page', 1);
        $page = max(1, min(10, $page));   // hard cap 10 pages
        $offset = ($page - 1) * $pagesize;

        $tracks = $this->_fetchTrackHistoryRows(
            $window['start_utc'],
            $upperBoundUtc,
            $pagesize,
            $offset,
            $timezone,
            $excludeShort,
            $minSeconds
        );

        // hasMore: lookup +1 to know whether a next page exists.
        // Lighter than a SELECT COUNT(*) and good enough to
        // toggle the "Load more" button.
        $hasMore = false;
        if (count($tracks) === $pagesize && $page < 10) {
            $extra = $this->_fetchTrackHistoryRows(
                $window['start_utc'],
                $upperBoundUtc,
                1,
                $offset + $pagesize,
                $timezone,
                $excludeShort,
                $minSeconds
            );
            $hasMore = !empty($extra);
        }

        header('Content-Type: application/json; charset=utf-8');
        $this->_emitCacheHeaders($cacheTtl);
        echo json_encode([
            'success'  => true,
            'tracks'   => $tracks,
            'hasMore'  => $hasMore,
            'page'     => $page,
            'pagesize' => $pagesize,
            'dayLocal' => $window['day_local'],
            'timezone' => $timezone,
            'labels'   => [
                'noTrackHistory' => Application_Model_Preference::GetWidgetNoTrackHistory(),
            ],
        ]);
    }

    /**
     * RASTATIME 2026-05-22 v14 — resolve the operator-typed
     * HH:MM into "the latest moment whose tracks should appear".
     * Returns a UTC timestamp string.  When ?time is absent,
     * falls back to:
     *   - "now"  if dayLocal === today (visitor opened the
     *            widget without pinning a time → wants the
     *            currently-playing slice)
     *   - end of day  if dayLocal is a past day (visitor wants
     *            the whole day's history)
     */
    private function _resolveTrackHistoryUpperBound($timezone, $dayLocal, $timeParam)
    {
        $tz = new DateTimeZone($timezone);
        $utc = new DateTimeZone('UTC');

        // If the visitor supplied ?time=HH:MM, use exactly that
        // moment on the requested day.  Strict format check so
        // a typo'd param doesn't 500 us.
        if ($timeParam !== null && $timeParam !== ''
                && preg_match('/^([01]\d|2[0-3]):([0-5]\d)$/', $timeParam)) {
            try {
                $stamp = new DateTime($dayLocal . ' ' . $timeParam . ':59', $tz);
                return $stamp->setTimezone($utc)->format('Y-m-d H:i:s');
            } catch (Exception $e) {
                // fall through to the default below
            }
        }

        $now   = new DateTime('now', $tz);
        $today = new DateTime('today', $tz);
        if ($dayLocal === $today->format('Y-m-d')) {
            // Today → "now" is the natural upper bound.
            return $now->setTimezone($utc)->format('Y-m-d H:i:s');
        }
        // Past day → end of that day (23:59:59).
        $eod = new DateTime($dayLocal . ' 23:59:59', $tz);
        return $eod->setTimezone($utc)->format('Y-m-d H:i:s');
    }

    /**
     * Default time-of-day for the date picker on first paint.
     * Returns HH:MM (local timezone).  If ?time was supplied
     * and is valid, echo it back.  Otherwise:
     *   - today  → current HH:MM (so the widget opens on "now")
     *   - past   → 23:59         (full-day view)
     */
    private function _resolveTrackHistoryTime($timezone, $timeParam, $dayLocal)
    {
        if ($timeParam !== null && $timeParam !== ''
                && preg_match('/^([01]\d|2[0-3]):([0-5]\d)$/', $timeParam)) {
            return $timeParam;
        }
        $tz = new DateTimeZone($timezone);
        $today = new DateTime('today', $tz);
        if ($dayLocal === $today->format('Y-m-d')) {
            $now = new DateTime('now', $tz);
            return $now->format('H:i');
        }
        return '23:59';
    }

    /**
     * Operator-set Preference vs. per-embed URL override for
     * the exclude-short-tracks toggle.  Truthy values: "1",
     * "true", "yes" (case-insensitive).
     */
    private function _resolveExcludeShortFlag($request)
    {
        $raw = $request->getParam('exclude_short');
        if ($raw === null || $raw === '') {
            return Application_Model_Preference::GetWidgetTrackHistoryExcludeShort();
        }
        $low = strtolower((string) $raw);
        return in_array($low, ['1', 'true', 'yes', 'on'], true);
    }

    /**
     * Operator-set Preference vs. per-embed URL override for
     * the min-seconds threshold.
     */
    private function _resolveMinSecondsThreshold($request)
    {
        $raw = $request->getParam('min_sec');
        if ($raw === null || $raw === '') {
            return Application_Model_Preference::GetWidgetTrackHistoryMinSeconds();
        }
        $i = (int) $raw;
        return max(1, min(3600, $i ?: 60));
    }

    /**
     * Resolve the date parameter to a day-window (UTC range) +
     * the min/max dates the picker should allow.  Operator-set
     * scope: last 7 days, today included (so the picker covers
     * today minus 6 days through today).
     */
    private function _resolveTrackHistoryDay($timezone, $dayParam)
    {
        $tz = new DateTimeZone($timezone);
        $today = new DateTime('today', $tz);

        // Min date: 6 days ago (so range is 7 days inclusive
        // counting today).  Operator-typical history-lookback
        // window — anything older sits in the dashboard, not
        // in a public widget.
        $minDate = (clone $today)->modify('-6 days');

        $picked = $today;
        if ($dayParam !== null && $dayParam !== ''
                && preg_match('/^\d{4}-\d{2}-\d{2}$/', $dayParam)) {
            try {
                $candidate = new DateTime($dayParam . ' 00:00:00', $tz);
                // Clamp to [minDate, today]; out-of-range dates
                // silently snap to the nearest valid bound rather
                // than 500-ing on a hand-crafted URL.
                if ($candidate < $minDate) {
                    $picked = $minDate;
                } elseif ($candidate > $today) {
                    $picked = $today;
                } else {
                    $picked = $candidate;
                }
            } catch (Exception $e) {
                $picked = $today;
            }
        }

        $dayEnd = (clone $picked)->modify('+1 day');

        $utc = new DateTimeZone('UTC');
        return [
            'start_utc' => (clone $picked)->setTimezone($utc)->format('Y-m-d H:i:s'),
            'end_utc'   => (clone $dayEnd)->setTimezone($utc)->format('Y-m-d H:i:s'),
            'day_local' => $picked->format('Y-m-d'),
            'min_local' => $minDate->format('Y-m-d'),
            'max_local' => $today->format('Y-m-d'),
        ];
    }

    /**
     * Fetch one page of tracks from cc_playout_history, joined
     * to cc_files for title/artist and (when present) to
     * cc_show_instances → cc_show for the show context.  Tracks
     * without a file_id (e.g. some auto-DJ entries) are
     * filtered out — they have no usable display data.
     *
     * Returns rows ordered chronologically descending (most
     * recent first, most operator-typical browsing direction).
     */
    private function _fetchTrackHistoryRows(
        $fromUtc, $toUtc, $limit, $offset, $timezone,
        $excludeShort = false, $minSeconds = 60
    )
    {
        // Build the SQL with an optional duration filter.  Using
        // EXTRACT(EPOCH FROM ends-starts) gives the duration in
        // seconds as a float; null-safe because ph.ends is
        // nullable (some entries don't have an end yet — those
        // get filtered out by the IS NOT NULL clause when the
        // toggle is on).
        $durationClause = '';
        if ($excludeShort) {
            $durationClause = "
                  AND ph.ends IS NOT NULL
                  AND EXTRACT(EPOCH FROM (ph.ends - ph.starts)) >= :min_sec";
        }

        // RASTATIME 2026-05-22 v16 — include webstream entries.
        // cc_playout_history has two row shapes:
        //
        //   - Scheduled file plays: file_id IS NOT NULL, title /
        //     artist live on cc_files.{track_title,artist_name}
        //     and the JOIN below picks them up directly.
        //
        //   - Webstream plays: file_id IS NULL, title / artist
        //     live in cc_playout_history_metadata as key-value
        //     rows with keys 'track_title' / 'artist_name'
        //     (constants MDATA_KEY_TITLE / MDATA_KEY_CREATOR in
        //     /application/configs/constants.php).  HistoryService::
        //     insertWebstreamMetadata() writes them.
        //
        // The COALESCE below uses cc_files first (cheap, single
        // JOIN) and falls back to a correlated subquery against
        // cc_playout_history_metadata only when the file row is
        // missing — webstream-typical case.  Two subqueries
        // (one per metadata key) keep the SQL readable; Postgres
        // handles them well because cc_playout_history_metadata
        // is indexed on history_id.
        $sql = "SELECT ph.id        AS history_id,
                       ph.starts    AS starts_utc,
                       ph.ends      AS ends_utc,
                       COALESCE(
                           f.track_title,
                           (SELECT md.value
                              FROM cc_playout_history_metadata md
                             WHERE md.history_id = ph.id
                               AND md.key = 'track_title'
                             LIMIT 1)
                       ) AS track_title,
                       COALESCE(
                           f.artist_name,
                           (SELECT md.value
                              FROM cc_playout_history_metadata md
                             WHERE md.history_id = ph.id
                               AND md.key = 'artist_name'
                             LIMIT 1)
                       ) AS artist_name,
                       (ph.file_id IS NULL) AS is_webstream,
                       s.id         AS show_id,
                       s.name       AS show_name,
                       s.url        AS show_url,
                       s.background_color
                FROM cc_playout_history ph
                LEFT JOIN cc_files f          ON ph.file_id = f.id
                LEFT JOIN cc_show_instances si ON ph.instance_id = si.id
                LEFT JOIN cc_show s         ON si.show_id = s.id
                WHERE ph.starts >= :from_utc
                  AND ph.starts <  :to_utc
                  {$durationClause}
                ORDER BY ph.starts DESC
                LIMIT :lim OFFSET :off";

        $params = [
            ':from_utc' => $fromUtc,
            ':to_utc'   => $toUtc,
            ':lim'      => (int) $limit,
            ':off'      => (int) $offset,
        ];
        if ($excludeShort) {
            $params[':min_sec'] = (int) $minSeconds;
        }
        $rows = Application_Common_Database::prepareAndExecute(
            $sql,
            $params,
            'all'
        );

        $out = [];
        foreach ($rows as $r) {
            $bg = (string) ($r['background_color'] ?? '');
            $bgHex = ($bg !== '' && preg_match('/^[0-9a-fA-F]{6}$/', $bg))
                ? '#' . $bg
                : null;
            $title  = trim((string) ($r['track_title'] ?? ''));
            $artist = trim((string) ($r['artist_name'] ?? ''));
            // Skip rows where both title and artist are empty —
            // they'd render as blank rows; better to drop them.
            if ($title === '' && $artist === '') {
                continue;
            }
            $out[] = [
                'id'           => (int) $r['history_id'],
                'title'        => $title,
                'artist'       => $artist,
                'starts'       => $this->_formatTimestamp($r['starts_utc'], $timezone),
                'ends'         => $this->_formatTimestamp($r['ends_utc'],   $timezone),
                // RASTATIME 2026-05-22 v16: webstream marker so
                // the JS / future UI can decorate streaming
                // entries differently (right now both render
                // identically; the flag is exposed for future
                // use without breaking the payload contract).
                'isWebstream'  => (bool) $r['is_webstream'],
                'show'         => [
                    'id'    => $r['show_id'] !== null ? (int) $r['show_id'] : null,
                    'name'  => (string) ($r['show_name'] ?? ''),
                    'url'   => (string) ($r['show_url']  ?? ''),
                    'color' => $bgHex,
                ],
            ];
        }
        return $out;
    }
}
