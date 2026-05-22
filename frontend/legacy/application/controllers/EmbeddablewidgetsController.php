<?php

class EmbeddableWidgetsController extends Zend_Controller_Action
{
    public function init() {}

    public function playerAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $this->view->headLink()->appendStylesheet(Assets::url('css/player-form.css'));
        $this->view->headScript()->appendFile(Assets::url('js/airtime/player/player.js'));

        $form = new Application_Form_Player();

        $apiEnabled = Application_Model_Preference::GetAllow3rdPartyApi();
        $numEnabledStreams = $form->getElement('player_stream_url')->getAttrib('numberOfEnabledStreams');

        if ($numEnabledStreams > 0 && $apiEnabled) {
            $this->view->player_form = $form;
        } else {
            $this->view->player_error_msg = _('To configure and use the embeddable player you must:<br><br>
            1. Enable at least one MP3, AAC, or OGG stream under Settings -> Streams<br>
            2. Enable the Public LibreTime API under Settings -> Preferences');
        }
    }

    /**
     * RASTATIME 2026-05-22 — Settings page for the modernised
     * Weekly Schedule widget (the v2 iframe — see EmbedController
     * ::weeklyProgramAction).
     *
     * Empty-state label form + live preview iframe (dark backdrop)
     * + ready-made embed-code snippet.  Replaces the upstream
     * preview-only page.  Doesn't gate on the public-API toggle —
     * the v2 widget is self-contained and doesn't go through
     * /api/live-info.
     */
    public function scheduleAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $request = $this->getRequest();
        $form = new Application_Form_WidgetWeeklySchedule();

        if ($request->isPost() && $form->isValid($request->getPost())) {
            Application_Model_Preference::SetWidgetNoWeeklyShows(
                $form->getValue('widget_no_weekly_shows')
            );
            $this->view->saved = true;
        } else {
            $form->populate([
                'widget_no_weekly_shows' => Application_Model_Preference::GetWidgetNoWeeklyShows(),
            ]);
        }

        $this->view->form = $form;
        $this->view->publicUrl = Config::getPublicUrl();
    }

    /**
     * RASTATIME 2026-05-22 — Settings page for the Current Show /
     * Current Track public embed widgets.
     *
     * Operator can:
     *  1. Preview both widgets side-by-side (iframe live render).
     *  2. Customise the four empty-state labels (no current show,
     *     no upcoming show, no current track, no upcoming track) —
     *     persisted in cc_pref so a refreshed widget picks them up
     *     within one cache TTL.
     *  3. Copy the ready-made <iframe> embed code for each widget,
     *     pre-filled with the absolute station URL.
     *
     * Unlike the upstream Player / Weekly-Schedule pages, these
     * widgets do NOT require the public-API toggle (they have
     * their own embed-only endpoints that don't go through
     * /api/live-info), so no error message is shown when the API
     * is disabled.
     */
    public function currentShowTrackAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $request = $this->getRequest();
        $form = new Application_Form_WidgetCurrentShowTrack();

        // POST: validate and persist before the GET-side render.
        if ($request->isPost() && $form->isValid($request->getPost())) {
            Application_Model_Preference::SetWidgetNoCurrentShow(
                $form->getValue('widget_no_current_show')
            );
            Application_Model_Preference::SetWidgetNoUpcomingShow(
                $form->getValue('widget_no_upcoming_show')
            );
            Application_Model_Preference::SetWidgetNoCurrentTrack(
                $form->getValue('widget_no_current_track')
            );
            Application_Model_Preference::SetWidgetNoUpcomingTrack(
                $form->getValue('widget_no_upcoming_track')
            );
            $this->view->saved = true;
        } else {
            // GET (or POST-with-errors): seed the form with the
            // currently-persisted labels so the field never appears
            // empty for an operator who already customised it.
            $form->populate([
                'widget_no_current_show'  => Application_Model_Preference::GetWidgetNoCurrentShow(),
                'widget_no_upcoming_show' => Application_Model_Preference::GetWidgetNoUpcomingShow(),
                'widget_no_current_track' => Application_Model_Preference::GetWidgetNoCurrentTrack(),
                'widget_no_upcoming_track'=> Application_Model_Preference::GetWidgetNoUpcomingTrack(),
            ]);
        }

        $this->view->form = $form;
        $this->view->publicUrl = Config::getPublicUrl();
    }

    /**
     * RASTATIME 2026-05-22 — Settings page for the Next-Shows /
     * Latest-Shows public embed widgets.
     *
     * Mirrors currentShowTrackAction structurally (preview + labels +
     * embed-code) but with one extra dimension: the operator picks a
     * single existing show from a dropdown and the page rebuilds the
     * preview iframes + embed-code with that show's id baked into
     * the URL.
     *
     * Persisted settings are just the two empty-state labels; the
     * show-selection is a per-session UI helper that the operator
     * copies-and-pastes into their own homepage HTML.
     */
    public function nextLatestShowsAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $request = $this->getRequest();
        $form = new Application_Form_WidgetNextLatestShows();

        // Populate the show dropdown from cc_show.  Sorted by name
        // so the operator can scan quickly; an empty entry on top
        // covers the "no show picked yet" state so the preview
        // shows the empty-state label rather than an arbitrary
        // show.
        $shows = $this->_fetchAllShowsForPicker();
        $options = ['' => _('— pick a show —')];
        foreach ($shows as $s) {
            // Parse the Postgres array literal "{1,2,3}" returned
            // by ARRAY_AGG into a PHP int array.  Skips empty
            // groups (defensive — shouldn't happen since the SQL
            // filters out empty names).
            $idsRaw = (string) ($s['ids'] ?? '');
            $ids = [];
            if ($idsRaw !== '' && $idsRaw !== '{}') {
                foreach (explode(',', trim($idsRaw, '{}')) as $piece) {
                    $piece = trim($piece);
                    if (is_numeric($piece)) {
                        $ids[] = (int) $piece;
                    }
                }
            }
            if (empty($ids)) {
                continue;
            }
            $name = (string) $s['name'];
            if (count($ids) === 1) {
                // Single show with this name — dropdown value is
                // the numeric id, embed snippet will use
                // ?show_id=N (the stable, rename-proof form).
                $options[(int) $ids[0]] = $name;
            } else {
                // Multi-match group — dropdown value is the
                // "name:..." marker so the embed snippet falls
                // back to ?show=Name (which, after the wave-1.5
                // backend follow-up, matches every show that
                // shares the name).  Label includes the count so
                // the operator sees at a glance how many shows
                // are bundled.
                $options['name:' . $name] = sprintf(
                    _('%1$s (%2$d shows)'),
                    $name,
                    count($ids)
                );
            }
        }
        $form->getElement('preview_show_id')->setMultiOptions($options);

        // POST: validate + persist labels only.  The show-picker is
        // round-tripped in the same form but not persisted (it just
        // re-renders the preview / embed-code for the picked show).
        if ($request->isPost() && $form->isValid($request->getPost())) {
            Application_Model_Preference::SetWidgetNoNextShows(
                $form->getValue('widget_no_next_shows')
            );
            Application_Model_Preference::SetWidgetNoLatestShows(
                $form->getValue('widget_no_latest_shows')
            );
            $this->view->saved = true;
        } else {
            $form->populate([
                'widget_no_next_shows'   => Application_Model_Preference::GetWidgetNoNextShows(),
                'widget_no_latest_shows' => Application_Model_Preference::GetWidgetNoLatestShows(),
            ]);
        }

        $this->view->form = $form;
        $this->view->publicUrl = Config::getPublicUrl();

        // RASTATIME 2026-05-22 — resolve which embed-code URL to
        // generate (?show_id=N vs ?show=Name).  The dropdown
        // pick wins over the manual name field (mirrors the
        // ?show_id > ?show precedence the public widget already
        // implements at the URL level).
        //
        // Dropdown values are either a numeric show id (single-
        // match name) or the string "name:Some Name" (multi-match
        // group — see _fetchAllShowsForPicker docstring).  The
        // view consumes previewShowId / previewShowName as two
        // pre-parsed scalars so the template stays simple.
        $pickedRaw = (string) $form->getValue('preview_show_id');
        $previewShowId   = 0;
        $previewShowName = '';
        if ($pickedRaw !== '') {
            if (strpos($pickedRaw, 'name:') === 0) {
                $previewShowName = substr($pickedRaw, 5);
            } elseif (is_numeric($pickedRaw)) {
                $previewShowId = (int) $pickedRaw;
            }
        }
        // Manual name input — fallback when the dropdown is
        // empty.  Trimmed so accidental leading whitespace
        // doesn't break the embed URL.
        $manualName = trim((string) $form->getValue('manual_show_name'));
        if ($previewShowId === 0 && $previewShowName === '' && $manualName !== '') {
            $previewShowName = $manualName;
        }
        $this->view->previewShowId   = $previewShowId;
        $this->view->previewShowName = $previewShowName;
        // The raw manual value is also exposed so the view can
        // round-trip it back into the input (lets the operator
        // keep editing after a Save without retyping).
        $this->view->manualShowName  = $manualName;
    }

    /**
     * Fetch all shows for the picker dropdown.  Returns the rows
     * already grouped by `name`: each result has the display name
     * plus an array of all cc_show.id values that share it, so the
     * UI can render one dropdown entry per visible name (rather
     * than seven near-identical "bbc news" lines when the operator
     * happens to have created one show per weekday).
     */
    private function _fetchAllShowsForPicker()
    {
        // Aggregate ids into a Postgres array per name.  Ordering
        // on LOWER(name) gives stable alphabetical groups; the
        // id list inside each group is sorted ascending for
        // deterministic "first id wins" behaviour in callers that
        // need a single id.
        $sql = "SELECT name,
                       ARRAY_AGG(id ORDER BY id ASC) AS ids
                FROM cc_show
                WHERE name <> ''
                GROUP BY name
                ORDER BY LOWER(name) ASC";
        try {
            $rows = Application_Common_Database::prepareAndExecute(
                $sql,
                [],
                'all'
            );
        } catch (Exception $e) {
            return [];
        }
        return $rows ?: [];
    }

    /**
     * RASTATIME 2026-05-22 — Settings page for the On-Air-Today
     * public embed widget.
     *
     * Single empty-state label form + live preview iframe (dark
     * backdrop, matches the admin theme) + ready-made embed-code
     * snippet.  No show-picker (the widget pulls from the live
     * schedule for the whole station day).
     */
    public function onAirTodayAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $request = $this->getRequest();
        $form = new Application_Form_WidgetOnAirToday();

        if ($request->isPost() && $form->isValid($request->getPost())) {
            Application_Model_Preference::SetWidgetNoOnAirToday(
                $form->getValue('widget_no_on_air_today')
            );
            $this->view->saved = true;
        } else {
            $form->populate([
                'widget_no_on_air_today' => Application_Model_Preference::GetWidgetNoOnAirToday(),
            ]);
        }

        $this->view->form = $form;
        $this->view->publicUrl = Config::getPublicUrl();
    }

    // The Facebook widget is untested & unsupported, the widget has been removed from the navigation in navigation.php
    public function facebookAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Widgets');

        $apiEnabled = Application_Model_Preference::GetAllow3rdPartyApi();

        if (!$apiEnabled) {
            $this->view->facebook_error_msg = _('To add the Radio Tab to your Facebook Page, you must first:<br><br>
            Enable the Public LibreTime API under Settings -> Preferences');
        }

        $CC_CONFIG = Config::getConfig();
        $baseUrl = Config::getBasePath();

        $facebookAppId = $CC_CONFIG['facebook-app-id'];
        $this->view->headScript()->appendScript('var FACEBOOK_APP_ID = ' . json_encode($facebookAppId) . ';');
        $this->view->headScript()->appendFile(Assets::url('js/airtime/common/facebook.js'), 'text/javascript');
    }

    /** Airtime makes an AJAX POST here after it successfully adds a tab to your Facebook page. */
    public function facebookTabSuccessAction()
    {
        // disable the view and the layout
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        // TODO: Get list of page IDs (deserialize)

        $request = $this->getRequest();
        if (!$request->isPost()) {
            return;
        }

        $values = $request->getPost();
        $facebookPageIds = json_decode($values['pages']);

        $CC_CONFIG = Config::getConfig();
        $facebookMicroserviceUrl = $CC_CONFIG['facebook-app-url'];
        $facebookMicroserviceApiKey = $CC_CONFIG['facebook-app-api-key'];

        // Post the page tab ID and station subdomain to the social microservice so that mapping can be saved
        // in a database.
        foreach ($facebookPageIds as $facebookPageId) {
            $postfields = [];
            $postfields['facebookPageId'] = $facebookPageId;
            $postfields['stationId'] = $CC_CONFIG['stationId'];

            $query_string = '';
            foreach ($postfields as $k => $v) {
                $query_string .= "{$k}=" . urlencode($v) . '&';
            }

            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $facebookMicroserviceUrl);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_TIMEOUT, 30);
            curl_setopt($ch, CURLOPT_FAILONERROR, 1);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $query_string);
            curl_setopt($ch, CURLOPT_USERPWD, ":{$facebookMicroserviceApiKey}");
            curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);

            $jsondata = curl_exec($ch);
            if (curl_error($ch)) {
                throw new Exception('Failed to reach server in ' . __FUNCTION__ . ': '
                    . curl_errno($ch) . ' - ' . curl_error($ch) . ' - ' . curl_getinfo($ch, CURLINFO_EFFECTIVE_URL));
            }
            curl_close($ch);
        }

        // $arr = json_decode($jsondata, true); # Decode JSON String
    }
}
