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
        $this->_renderNowPlayingWidget('show');
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
        $this->_renderNowPlayingWidget('track');
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
     * Shared render path for the two Now-Playing widgets.
     *
     * @param string $mode 'show' or 'track' — picks the template
     */
    private function _renderNowPlayingWidget($mode)
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

        $cacheTtl = $this->_resolveCacheTtl();
        $this->view->cacheTtl = $cacheTtl;
        $this->_emitCacheHeaders($cacheTtl);

        $timezone = $this->_resolveTimezone();

        // Server-side initial render so the iframe shows real data
        // immediately even before the JS poll fires.
        $this->view->initialPayload = $this->_buildNowPlayingPayload($timezone);

        // Asset URLs computed here so the view template stays clean.
        $this->view->widgetCss = Assets::url('css/embed/now-playing-widget.css');
        $this->view->widgetJs  = Assets::url('js/airtime/embed/now-playing-widget.js');

        // URL for the JS poller — relative because the iframe runs
        // under the station origin, same as the widget itself.
        $cacheParam = $request->getParam('cache');
        $this->view->dataUrl = '/Embed/now-playing-data'
            . ($cacheParam !== null ? '?cache=' . urlencode($cacheParam) : '');

        // Pick the right inner-template via setScript so we can keep
        // the two route names distinct while sharing 95 % of the
        // controller code.
        $this->_helper->viewRenderer->setScript('embed/now-playing-' . $mode . '.phtml');
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
            'timezone' => $timezone,
        ];
    }

    /**
     * Reduce a Show entry to just the four fields the widgets render.
     * Null-safe: returns null if no show is present.
     */
    private function _slimShow($show, $timezone)
    {
        if (empty($show) || !is_array($show)) {
            return null;
        }
        return [
            'name'   => $show['name'] ?? '',
            'starts' => $this->_formatTimestamp($show['starts'] ?? null, $timezone),
            'ends'   => $this->_formatTimestamp($show['ends'] ?? null, $timezone),
        ];
    }

    /**
     * Reduce a Track entry to Artist + Title + start + end.  The
     * artist field is optional; the JS template just shows the title
     * alone when artist is empty.
     */
    private function _slimTrack($track, $timezone)
    {
        if (empty($track) || !is_array($track)) {
            return null;
        }
        $meta = $track['metadata'] ?? [];
        return [
            'title'  => $meta['track_title'] ?? ($track['name'] ?? ''),
            'artist' => $meta['artist_name'] ?? '',
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
