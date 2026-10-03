<?php

// this is not getting loaded by autloading since it has a classname
// that makes it clash with how zf1 expects to load plugins.
require_once 'customfilters/ImageSize.php';

class Application_Form_GeneralPreferences extends Zend_Form_SubForm
{
    public function init()
    {
        $maxLens = Application_Model_Show::getMaxLengths();
        $this->setEnctype(Zend_Form::ENCTYPE_MULTIPART);

        $notEmptyValidator = Application_Form_Helper_ValidationTypes::overrideNotEmptyValidator();
        $rangeValidator = Application_Form_Helper_ValidationTypes::overrideBetweenValidator(0, 59.9);
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/preferences_general.phtml']],
        ]);


        // Station name
        $this->addElement('text', 'stationName', [
            'class' => 'input_text',
            'label' => _('Station Name'),
            'required' => false,
            'filters' => ['StringTrim'],
            'value' => Application_Model_Preference::GetStationName(),
        ]);

        // Station description
        $stationDescription = new Zend_Form_Element_Textarea('stationDescription');
        $stationDescription->setLabel(_('Station Description'));
        $stationDescription->setValue(Application_Model_Preference::GetStationDescription());
        $stationDescription->setRequired(false);
        $stationDescription->setValidators([['StringLength', false, [0, $maxLens['description']]]]);
        $stationDescription->setAttrib('rows', 4);
        $this->addElement($stationDescription);

        // Station Logo
        $stationLogoUpload = new Zend_Form_Element_File('stationLogo');
        $stationLogoUpload->setLabel(_('Station Logo:'))
            ->setDescription(_('Note: Anything larger than 600x600 will be resized.'))
            ->setRequired(false)
            ->addValidator('Count', false, 1)
            ->addValidator('Extension', false, 'jpg,jpeg,png,gif')
            ->setMaxFileSize(1000000)
            ->addFilter('ImageSize');
        $stationLogoUpload->setAttrib('accept', 'image/*');
        $this->addElement($stationLogoUpload);

        $stationLogoRemove = new Zend_Form_Element_Button('stationLogoRemove');
        $stationLogoRemove->setLabel(_('Remove'));
        $stationLogoRemove->setAttrib('class', 'btn');
        $stationLogoRemove->setAttrib('id', 'logo-remove-btn');
        $stationLogoRemove->setAttrib('onclick', 'removeLogo();');
        $this->addElement($stationLogoRemove);

        // RASTATIME 2026-05-15 - Custom favicon upload.  Stored as base64
        // blob in cc_pref + a separate MIME column; rendered as a data: URI
        // in PageLayoutInitPlugin / LoginController so no file writes to
        // public/ are needed at request time.
        $stationFaviconUpload = new Zend_Form_Element_File('stationFavicon');
        $stationFaviconUpload->setLabel(_('Station Favicon:'))
            ->setDescription(_('Recommended: square PNG, at least 32x32 pixels.  ICO also accepted.'))
            ->setRequired(false)
            ->addValidator('Count', false, 1)
            ->addValidator('Extension', false, 'png,jpg,jpeg,gif,ico')
            ->setMaxFileSize(200000);  // 200 KB - favicons should be tiny
        $stationFaviconUpload->setAttrib('accept', 'image/png,image/jpeg,image/gif,image/x-icon,image/vnd.microsoft.icon,.ico');
        $this->addElement($stationFaviconUpload);

        $stationFaviconRemove = new Zend_Form_Element_Button('stationFaviconRemove');
        $stationFaviconRemove->setLabel(_('Remove'));
        $stationFaviconRemove->setAttrib('class', 'btn');
        $stationFaviconRemove->setAttrib('id', 'favicon-remove-btn');
        $stationFaviconRemove->setAttrib('onclick', 'removeFavicon();');
        $this->addElement($stationFaviconRemove);

        // RASTATIME 2026-09-29 - the UI's primary colour (was a fixed orange).
        // A hex text field; preferences.js adds a colour picker and a reset
        // button next to it.  Empty = the default orange.
        $this->addElement('text', 'uiAccentColor', [
            'class' => 'input_text',
            'label' => _('Primary Color:'),
            'description' => _('The accent color of the whole interface, the radio page and the widgets: links, highlights, selected rows, progress bars, the player. Choose a color that stands out against the dark gray background; text on it switches between white and black by itself. Empty resets to the default orange.'),
            'required' => false,
            'filters' => ['StringTrim'],
            'validators' => [
                ['regex', false, ['/^#[0-9a-fA-F]{6}$/', 'messages' => _('Please enter a color as #rrggbb (e.g. #ff5d1a).')]],
            ],
            'value' => Application_Model_AccentColor::current(),
        ]);

        // Default track crossfade duration (between two tracks of one show).
        // RASTATIME 2026-09-27 - renamed from "Default Crossfade Duration";
        // a real crossfade since then (old fades out while new fades in).
        $this->addElement('text', 'stationDefaultCrossfadeDuration', [
            'class' => 'input_text',
            'label' => _('Default Track Crossfade Duration (s):'),
            'description' => _('Between two tracks of the same show: the old track fades out while the new one fades in over this many seconds (0 = no overlap).'),
            'required' => true,
            'filters' => ['StringTrim'],
            'validators' => [
                $rangeValidator,
                $notEmptyValidator,
                ['regex', false, ['/^[0-9]+(\.\d+)?$/', 'messages' => _('Please enter a time in seconds (eg. 0.5)')]],
            ],
            'value' => Application_Model_Preference::GetDefaultCrossfadeDuration(),
        ]);

        // RASTATIME 2026-09-27 - Default show crossfade duration.  The old
        // "Default Fade In / Fade Out" fields (LibreTime, cc_schedule
        // fade_in/fade_out) had no effect since the Liquidsoap migration
        // and are no longer shown; their preference keys stay in cc_pref.
        $this->addElement('text', 'stationDefaultShowCrossfadeDuration', [
            'class' => 'input_text',
            'label' => _('Default Show Crossfade Duration (s):'),
            'description' => _('At a show boundary the old show fades out over this many seconds while the first track of the new show starts at full level at once. Also shapes every switch between tracks, webstreams and Line-Ins.'),
            'required' => true,
            'filters' => ['StringTrim'],
            'validators' => [
                $rangeValidator,
                $notEmptyValidator,
                ['regex', false, ['/^[0-9]+(\.\d+)?$/', 'messages' => _('Please enter a time in seconds (eg. 0.5)')]],
            ],
            'value' => Application_Model_Preference::GetDefaultShowCrossfadeDuration(),
        ]);

        $tracktypeDefault = new Zend_Form_Element_Select('tracktypeDefault');
        $tracktypeDefault->setLabel(_('Track Type Upload Default'));
        $tracktypeDefault->setMultiOptions(Application_Model_Library::getTracktypes());
        $tracktypeDefault->setValue(Application_Model_Preference::GetTrackTypeDefault());
        $this->addElement($tracktypeDefault);

        $playlistNames = Application_Model_Library::getPlaylistNames(true);

        // add intro playlist select here
        $introPlaylistSelect = new Zend_Form_Element_Select('introPlaylistSelect');
        $introPlaylistSelect->setLabel(_('Intro Autoloading Playlist'));
        $introPlaylistSelect->setMultiOptions($playlistNames);
        $introPlaylistSelect->setValue(Application_Model_Preference::GetIntroPlaylist());
        $this->addElement($introPlaylistSelect);

        $outroPlaylistSelect = new Zend_Form_Element_Select('outroPlaylistSelect');
        $outroPlaylistSelect->setLabel(_('Outro Autoloading Playlist'));
        $outroPlaylistSelect->setMultiOptions($playlistNames);
        $outroPlaylistSelect->setValue(Application_Model_Preference::GetOutroPlaylist());
        $this->addElement($outroPlaylistSelect);

        // RASTATIME 2026-06-07 — Song Requests: pick the smart block(s)
        // whose members listeners may request.  A sync task mirrors the
        // union of their tracks into cc_files.requestable; the public
        // catalogue-search endpoint filters on that flag.  Check none to
        // disable song requests.  Multi-checkbox so several blocks can be
        // combined (e.g. Pop + Rock + Indie).
        $requestablePoolSelect = new Zend_Form_Element_MultiCheckbox('requestablePoolSelect');
        $requestablePoolSelect->setLabel(_('Song-Request Pool (smart blocks)'));
        $requestablePoolSelect->setMultiOptions(Application_Model_Library::getBlockNames());
        $requestablePoolSelect->setValue(Application_Model_Preference::getRequestablePoolBlockIds());
        $this->addElement($requestablePoolSelect);

        // RASTATIME 2026-06-16 — Traffic Alerts: pick ONE smart block that is
        // the source of short-notice traffic MP3s.  A show carrying this block
        // in its autoload dramaturgy is filled incrementally (like a request
        // show), so a traffic slot picks up alerts imported while the show is
        // already on air and airs them within a ~10-minute SLA.  "(none)"
        // disables the feature.
        $trafficAlertSelect = new Zend_Form_Element_Select('trafficAlertBlockSelect');
        $trafficAlertSelect->setLabel(_('Traffic-Alert Smart Block'));
        $trafficAlertSelect->setMultiOptions(
            [0 => _('(none — disabled)')] + Application_Model_Library::getBlockNames()
        );
        $trafficAlertSelect->setValue(Application_Model_Preference::getTrafficAlertBlockId());
        $trafficAlertSelect->setDescription(_('New tracks added to this smart block air in the running show at its next traffic slot, within ~10 minutes. Add this block at several points in a show so alerts interrupt promptly.'));
        $this->addElement($trafficAlertSelect);

        // RASTATIME 2026-09-27 — Show-Shift filler playlist.  When a delayed
        // start pushes a show's tail past its slot, the tracks that no longer
        // fit are replaced by tracks from this playlist instead of the last
        // track being cut.  "(none)" keeps the plain clamp.
        $fillerSelect = new Zend_Form_Element_Select('showShiftFillerPlaylistSelect');
        $fillerSelect->setLabel(_('Show-Shift Filler Playlist'));
        $fillerSelect->setMultiOptions(
            [0 => _('(none — cut the last track)')] + Application_Model_Library::getPlaylistNames(true)
        );
        $fillerSelect->setValue(Application_Model_Preference::getShowShiftFillerPlaylistId());
        $fillerSelect->setDescription(_('When a delayed start pushes a show past its slot, the tracks that no longer fit are replaced by tracks from this playlist so only a filler gets cut, never a show track. A show that ends with its outro playlist keeps the outro; the tracks before it are replaced.'));
        $this->addElement($fillerSelect);

        $podcast_album_override = new Zend_Form_Element_Radio('podcastAlbumOverride');
        $podcast_album_override->setLabel(_('Overwrite Podcast Episode Metatags'));
        $podcast_album_override->setMultiOptions([
            _('Disabled'),
            _('Enabled'),
        ]);
        $podcast_album_override->setValue(Application_Model_Preference::GetPodcastAlbumOverride());
        $podcast_album_override->setDescription(_('Enabling this feature will cause podcast episode tracks to have their Artist, Title, and Album metatags set from podcast feed values. Note that enabling this feature is recommended in order to ensure reliable scheduling of episodes via smartblocks.'));
        $podcast_album_override->setSeparator(' '); // No <br> between radio buttons
        $podcast_album_override->addDecorator('HtmlTag', [
            'tag' => 'dd',
            'id' => 'podcastAlbumOverride-element',
            'class' => 'radio-inline-list',
        ]);
        $this->addElement($podcast_album_override);

        $podcast_auto_smartblock = new Zend_Form_Element_Radio('podcastAutoSmartblock');
        $podcast_auto_smartblock->setLabel(_('Generate a smartblock and a playlist upon creation of a new podcast'));
        $podcast_auto_smartblock->setMultiOptions([
            _('Disabled'),
            _('Enabled'),
        ]);
        $podcast_auto_smartblock->setValue(Application_Model_Preference::GetPodcastAutoSmartblock());
        $podcast_auto_smartblock->setDescription(_('If this option is enabled, a new smartblock and playlist matching the newest track of a podcast will be generated immediately upon creation of a new podcast. Note that the "Overwrite Podcast Episode Metatags" feature must also be enabled in order for smartblocks to reliably find episodes.'));
        $podcast_auto_smartblock->setSeparator(' '); // No <br> between radio buttons
        $podcast_auto_smartblock->addDecorator('HtmlTag', [
            'tag' => 'dd',
            'id' => 'podcastAutoSmartblock-element',
            'class' => 'radio-inline-list',
        ]);
        $this->addElement($podcast_auto_smartblock);

        $scheduleTrimOverbooked = new Zend_Form_Element_Checkbox('scheduleTrimOverbooked');
        $scheduleTrimOverbooked->setDecorators([
            'ViewHelper',
            'Errors',
            'Label',
        ]);
        $displayScheduleTrimOverbookedValue = Application_Model_Preference::getScheduleTrimOverbooked();
        $scheduleTrimOverbooked->addDecorator('Label');
        $scheduleTrimOverbooked->setLabel(_('Trim overbooked shows after autoloading?'));
        $scheduleTrimOverbooked->setValue($displayScheduleTrimOverbookedValue);
        $this->addElement($scheduleTrimOverbooked);

        // TODO add and insert Podcast Smartblock and Playlist autogenerate options

        $third_party_api = new Zend_Form_Element_Radio('thirdPartyApi');
        $third_party_api->setLabel(_('Public RASTATIME API'));
        $third_party_api->setDescription(_('Required for embeddable schedule widget.'));
        $third_party_api->setMultiOptions([
            _('Disabled'),
            _('Enabled'),
        ]);
        $third_party_api->setValue(Application_Model_Preference::GetAllow3rdPartyApi());
        $third_party_api->setDescription(_('Enabling this feature will allow RASTATIME to provide schedule data
                                            to external widgets that can be embedded in your website.'));
        $third_party_api->setSeparator(' '); // No <br> between radio buttons
        // $third_party_api->addDecorator(new Zend_Form_Decorator_Label(array('tag' => 'dd', 'class' => 'radio-inline-list')));
        $third_party_api->addDecorator('HtmlTag', [
            'tag' => 'dd',
            'id' => 'thirdPartyApi-element',
            'class' => 'radio-inline-list',
        ]);
        $this->addElement($third_party_api);

        $locale = new Zend_Form_Element_Select('locale');
        $locale->setLabel(_('Default Language'));
        $locale->setMultiOptions(Application_Model_Locale::getLocales());
        // RASTATIME 2026-05-15 - Pre-fill with GetLocale() (current user's
        // effective locale) instead of GetDefaultLocale() (global default for
        // new users).  Reason: PreferenceController::indexAction writes all
        // three locale source surfaces (global default, per-user, cookie) on
        // every save.  If we pre-filled with the global default, any save
        // where the operator did NOT touch the language dropdown (e.g.
        // saving a favicon upload) would silently overwrite their per-user
        // locale and cookie with whatever the global default happens to
        // be.  By pre-filling with the operator's current effective locale,
        // an untouched dropdown round-trips as a no-op.
        $locale->setValue(Application_Model_Preference::GetLocale());
        $this->addElement($locale);

        // Form Element for setting the Timezone
        $timezone = new Zend_Form_Element_Select('timezone');
        $timezone->setLabel(_('Station Timezone'));
        $timezone->setAttrib('disabled', 'true');
        $timezone->setMultiOptions(Application_Common_Timezone::getTimezones());
        $timezone->setValue(Application_Model_Preference::GetDefaultTimezone());
        $this->addElement($timezone);

        // Form Element for setting which day is the start of the week
        $week_start_day = new Zend_Form_Element_Select('weekStartDay');
        $week_start_day->setLabel(_('Week Starts On'));
        $week_start_day->setMultiOptions($this->getWeekStartDays());
        $week_start_day->setValue(Application_Model_Preference::GetWeekStartDay());
        $this->addElement($week_start_day);

        $radioPageLoginButton = new Zend_Form_Element_Checkbox('radioPageLoginButton');
        $radioPageLoginButton->setDecorators([
            'ViewHelper',
            'Errors',
            'Label',
        ]);
        $displayRadioPageLoginButtonValue = Application_Model_Preference::getRadioPageDisplayLoginButton();
        if ($displayRadioPageLoginButtonValue == '') {
            $displayRadioPageLoginButtonValue = true;
        }
        $radioPageLoginButton->addDecorator('Label');
        $radioPageLoginButton->setLabel(_('Display login button on your Radio Page?'));
        $radioPageLoginButton->setValue($displayRadioPageLoginButtonValue);
        $this->addElement($radioPageLoginButton);

        // add a checkbox for completely disabling the radio page
        $radioPageDisabled = new Zend_Form_Element_Checkbox('radioPageDisabled');
        $radioPageDisabled->setDecorators([
            'ViewHelper',
            'Errors',
            'Label',
        ]);
        $radioPageDisabledValue = Application_Model_Preference::getRadioPageDisabled();
        $radioPageDisabled->addDecorator('Label');
        $radioPageDisabled->setLabel(_('Disable the public radio page and redirect to the login page?'));
        $radioPageDisabled->setValue($radioPageDisabledValue);
        $this->addElement($radioPageDisabled);

        // RASTATIME 2026-05-15 - Feature Previews removed: phantom setting, never
        // consumed by any code path. Form element + render + Preference accessors
        // + PreferenceController save line all deleted. cc_pref row left in place
        // (non-destructive); may be dropped via a future migration.
    }

    private function getWeekStartDays()
    {
        return [
            _('Sunday'),
            _('Monday'),
            _('Tuesday'),
            _('Wednesday'),
            _('Thursday'),
            _('Friday'),
            _('Saturday'),
        ];
    }
}
