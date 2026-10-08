<?php

class IndexController extends Zend_Controller_Action
{
    public function init() {}

    public function indexAction()
    {
        $CC_CONFIG = Config::getConfig();
        $baseUrl = Config::getBasePath();
        if (Application_Model_Preference::getRadioPageDisabled()) {
            $this->_helper->redirector->gotoUrl($baseUrl . 'login');

            return;
        }

        $this->view->headTitle(Application_Model_Preference::GetHeadTitle());
        // RASTATIME 2026-09-17 (JS-modernization 5b): jQuery 3.7.1 is the
        // only path; migrate + the ?jq3 flag are retired (radio page loads
        // no jQuery-UI JS).
        $this->view->headScript()->appendFile(Assets::url('js/libs/jquery-3.7.1.min.js'), 'text/javascript')
            ->appendFile(Assets::url('js/libs/jquery-browser-shim.js'), 'text/javascript');

        $this->view->headScript()->appendFile(Assets::url('js/i18n/jquery.i18n.js'), 'text/javascript');
        $this->view->headScript()->appendFile($baseUrl . 'locale/general-translation-table', 'text/javascript');
        $this->view->headScript()->appendScript('$.i18n.setDictionary(general_dict)');
        $this->view->headScript()->appendScript("var baseUrl='{$baseUrl}'");

        // RASTATIME 2026-06-01 (JS-modernization, jPlayer part 3/3): the per-page
        // jPlayer load is gone — index.phtml drives a native <audio> player now.

        $this->view->headLink()->setStylesheet(Assets::url('css/radio-page/radio-page.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/embed/weekly-schedule-widget.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/radio-page/station-podcast.css'));
        $this->view->headLink()->appendStylesheet(Assets::url('css/bootstrap.css'));

        // player control buttons (jQuery-UI corner/icon classes used in the GUI)
        $this->view->headLink()->appendStylesheet(Assets::url('css/redmond-1.13/jquery-ui.min.css'));

        $this->_helper->layout->setLayout('radio-page');

        // translate page to station default language
        $locale = Application_Model_Preference::GetDefaultLocale();
        if ($locale) {
            Application_Model_Locale::configureLocalization($locale);
        }

        $this->view->stationLogo = Application_Model_Preference::GetStationLogo();
        // RASTATIME 2026-10-07 - background image from Settings -> General ('' = built-in)
        $this->view->landingBackgroundUrl = Application_Model_Preference::GetLandingBackgroundUrl();

        $stationName = Application_Model_Preference::GetStationName();
        $this->view->stationName = $stationName;

        $stationDescription = Application_Model_Preference::GetStationDescription();
        $this->view->stationDescription = $stationDescription;

        $this->view->stationUrl = Config::getPublicUrl();

        $displayRadioPageLoginButtonValue = Application_Model_Preference::getRadioPageDisplayLoginButton();
        if ($displayRadioPageLoginButtonValue == '') {
            $displayRadioPageLoginButtonValue = true;
        }
        $this->view->displayLoginButton = $displayRadioPageLoginButtonValue;

        // station feed episodes
        $stationPodcastId = Application_Model_Preference::getStationPodcastId();
        $podcastEpisodesService = new Application_Service_PodcastEpisodeService();
        $episodes = $podcastEpisodesService->getPodcastEpisodes($stationPodcastId, 0, 0, PodcastEpisodesPeer::PUBLICATION_DATE, 'DESC');
        foreach ($episodes as $e => $v) {
            $episodes[$e]['CcFiles']['track_title'] = htmlspecialchars($v['CcFiles']['track_title'] ?? '', ENT_QUOTES);
            $episodes[$e]['CcFiles']['artist_name'] = htmlspecialchars($v['CcFiles']['artist_name'] ?? '', ENT_QUOTES);

            $pubDate = explode(' ', $v['publication_date']);
            $episodes[$e]['publication_date'] = $pubDate[0];

            $length = explode('.', $v['CcFiles']['length']);
            $episodes[$e]['CcFiles']['length'] = $length[0];

            $episodes[$e]['mime'] = FileDataHelper::getAudioMimeTypeArray()[$v['CcFiles']['mime']];

            if (is_null($v['CcFiles']['description'])) {
                $episodes[$e]['CcFiles']['description'] = '';
            }
        }

        $episodePages = array_chunk($episodes, 10);

        $this->view->episodes = json_encode($episodePages, JSON_FORCE_OBJECT);
        $this->view->displayRssTab = (!Application_Model_Preference::getStationPodcastPrivacy());

        $stationPodcast = PodcastQuery::create()->findOneByDbId($stationPodcastId);
        $url = $stationPodcast->getDbUrl();
        $this->view->stationPodcastRssUrl = $url;

        $stationName = Application_Model_Preference::GetStationName();
        $this->view->podcastTitle = sprintf(_('%s Podcast'), !empty($stationName) ? $stationName : $CC_CONFIG['stationId']);
        $this->view->emptyPodcastMessage = _('No tracks have been published yet.');
    }

    /**
     * RASTATIME 2026-10-07 - the landing page's background image (Settings ->
     * General), streamed from the storage root with cache headers; 404 while
     * the built-in image is in use.  Public like the page itself.
     */
    public function backgroundAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $response = $this->getResponse();

        $name = Application_Model_Preference::GetLandingBackground();
        if ($name === '') {
            $response->setHttpResponseCode(404);

            return;
        }
        $path = Application_Model_Preference::landingBackgroundPath($name);
        $mime = ['jpg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'][pathinfo($name, PATHINFO_EXTENSION)];
        $mtime = (int) filemtime($path);
        $size = (int) filesize($path);
        $etag = '"' . $mtime . '-' . $size . '"';
        $response->setHeader('Cache-Control', 'public, max-age=604800', true)
            ->setHeader('ETag', $etag, true)
            ->setHeader('Last-Modified', gmdate('D, d M Y H:i:s', $mtime) . ' GMT', true);
        if (trim((string) ($_SERVER['HTTP_IF_NONE_MATCH'] ?? '')) === $etag) {
            $response->setHttpResponseCode(304);

            return;
        }
        $response->setHeader('Content-Type', $mime, true)
            ->setHeader('Content-Length', (string) $size, true)
            ->setBody(file_get_contents($path));
    }

    public function mainAction()
    {
        $this->_helper->layout->setLayout('layout');
    }

    public function maintenanceAction()
    {
        $this->getResponse()->setHttpResponseCode(503);
    }
}
