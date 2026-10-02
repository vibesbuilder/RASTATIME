<?php

class Application_Form_StreamSetting extends Zend_Form
{
    private $setting;

    // RASTATIME 2026-09-28 - "Measured: N of M files" for the EBU R128 block
    public $loudnessMeasured = 0;
    public $loudnessTotal = 0;

    public function init() {}

    public function setSetting($setting)
    {
        $this->setting = $setting;
    }

    public function setLoudnessStats($measured, $total)
    {
        $this->loudnessMeasured = (int) $measured;
        $this->loudnessTotal = (int) $total;
    }

    // RASTATIME 2026-10-02 - Output Processing (Stereo Tool): status line
    public $stereotoolLibraryFound = false;
    public $stereotoolLicenseSet = false;

    public function startFrom()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'preference/stream-setting.phtml']],
        ]);

        $setting = $this->setting;

        $stream_format = new Zend_Form_Element_Radio('streamFormat');
        $stream_format
            ->setLabel(_('Stream Label:'))
            ->setMultiOptions([
                _('Artist - Title'),
                _('Show - Artist - Title'),
                _('Station name - Show name'),
            ])
            ->setValue(Application_Model_Preference::GetStreamLabelFormat())
            ->setDecorators(['ViewHelper']);
        $this->addElement($stream_format);

        $offAirMeta = new Zend_Form_Element_Text('offAirMeta');
        $offAirMeta
            ->setLabel(_('Off Air Metadata'))
            ->setValue(Application_Model_Preference::getOffAirMeta())
            ->setDecorators(['ViewHelper']);
        $this->addElement($offAirMeta);

        // RASTATIME 2026-09-28 - Loudness Normalization (EBU R128, stage 1):
        // the "Enable Replay Gain" checkbox became a three-way mode.
        $loudness_mode = new Zend_Form_Element_Select('loudnessMode');
        $loudness_mode
            ->setLabel(_('Loudness Normalization'))
            ->setMultiOptions([
                'off' => _('Off'),
                'replaygain' => _('ReplayGain'),
                'r128' => _('EBU R128'),
            ])
            ->setValue(Application_Model_Preference::getLoudnessMode())
            ->setDescription(_('How the level of scheduled tracks is evened out. ReplayGain applies the value measured at import plus the modifier. EBU R128 measures every track by the broadcast loudness standard (ITU BS.1770) and plays it at the target loudness below; a peak limiter on the bus keeps the true-peak ceiling. Live sources (DJ, webstream, Line-In) are not affected in this stage.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($loudness_mode);

        $loudness_target = new Zend_Form_Element_Text('loudnessTarget');
        $loudness_target
            ->setLabel(_('Target Loudness (LUFS)'))
            ->setValue(Application_Model_Preference::getLoudnessTargetLufs())
            ->setAttribs(['type' => 'number', 'step' => '0.5', 'min' => '-40', 'max' => '-5', 'class' => 'input_text', 'style' => 'width: 90px'])
            ->setDescription(_('The integrated loudness every track is played at. EBU R128 specifies -23 LUFS (broadcast); web streams commonly use louder targets between -18 and -16 LUFS. A change re-computes the gain of every track at the next schedule refresh.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($loudness_target);

        $loudness_true_peak = new Zend_Form_Element_Text('loudnessTruePeak');
        $loudness_true_peak
            ->setLabel(_('True Peak Ceiling (dBTP)'))
            ->setValue(Application_Model_Preference::getLoudnessTruePeakDbtp())
            ->setAttribs(['type' => 'number', 'step' => '0.1', 'min' => '-12', 'max' => '0', 'class' => 'input_text', 'style' => 'width: 90px'])
            ->setDescription(_('The level no peak may exceed. A quiet track is boosted only as far as its measured true peak allows, and the peak limiter on the bus catches the rest. EBU R128 specifies -1 dBTP.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($loudness_true_peak);

        // RASTATIME 2026-10-02 - Output Processing (Stereo Tool): optional,
        // off by default.  The playout puts Liquidsoap's stereotool()
        // operator on the whole output bus when enabled and the library
        // file exists; a change is applied by its planned restart.
        $library = Application_Model_Preference::getStereoToolLibrary();
        $this->stereotoolLibraryFound = $library !== '' && is_file($library);
        $this->stereotoolLicenseSet = Application_Model_Preference::hasStereoToolLicenseKey();

        $st_enabled = new Zend_Form_Element_Checkbox('stereotoolEnabled');
        $st_enabled
            ->setLabel(_('Output Processing (Stereo Tool)'))
            ->setValue(Application_Model_Preference::getStereoToolEnabled() ? 1 : 0)
            ->setDescription(_('Runs the whole output - every stream, the 24/7 recording and the Main Output - through Stereo Tool (loudness control to the broadcast standard, multiband processing, final limiter). Off by default; needs the Stereo Tool library for Liquidsoap and a licence from the Stereo Tool website. The playout applies a change at its next planned restart; if the fresh instance does not start with Stereo Tool, it restarts without it and raises a preflight warning.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($st_enabled);

        $st_library = new Zend_Form_Element_Text('stereotoolLibrary');
        $st_library
            ->setLabel(_('Stereo Tool library (DLL)'))
            ->setValue($library)
            ->setAttribs(['class' => 'input_text', 'style' => 'width: 420px', 'placeholder' => 'C:\\Tools\\stereotool\\libStereoTool_64.dll'])
            ->setDescription(_('Full path of the Stereo Tool library for Liquidsoap on this machine (the 64-bit DLL from the Stereo Tool download page). The setting is only used when the file exists.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($st_library);

        $st_preset = new Zend_Form_Element_Text('stereotoolPreset');
        $st_preset
            ->setLabel(_('Stereo Tool preset (.sts)'))
            ->setValue(Application_Model_Preference::getStereoToolPreset())
            ->setAttribs(['class' => 'input_text', 'style' => 'width: 420px', 'placeholder' => 'C:\\Tools\\stereotool\\rastatime.sts'])
            ->setDescription(_('Optional: a preset exported from the Stereo Tool application. Without a preset the library starts with its defaults.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($st_preset);

        $st_key = new Zend_Form_Element_Password('stereotoolLicenseKey');
        $st_key
            ->setLabel(_('Stereo Tool licence key'))
            ->setAttribs(['class' => 'input_text', 'style' => 'width: 420px', 'autocomplete' => 'new-password',
                'placeholder' => $this->stereotoolLicenseSet ? _('(a key is stored - leave blank to keep it)') : ''])
            ->setDescription(_('The licence key from your Stereo Tool account. Stored on the server, never shown again; leave the field blank to keep the stored key, enter CLEAR to remove it.'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($st_key);

        $replay_gain = new Zend_Form_Element_Hidden('replayGainModifier');
        $replay_gain
            ->setLabel(_('Replay Gain Modifier'))
            ->setValue(Application_Model_Preference::getReplayGainModifier())
            ->setAttribs(['style' => 'border: 0; color: #f6931f; font-weight: bold;'])
            ->setDecorators(['ViewHelper']);
        $this->addElement($replay_gain);

        $output_sound_device = new Zend_Form_Element_Checkbox('output_sound_device');
        $output_sound_device
            ->setLabel(_('Hardware Audio Output:'))
            ->setAttrib('readonly', true)
            ->setRequired(false)
            ->setValue(($setting['output_sound_device'] == 'true') ? 1 : 0)
            ->setDecorators(['ViewHelper']);
        $this->addElement($output_sound_device);

        $output_sound_device_type = new Zend_Form_Element_Select('output_sound_device_type');
        $output_sound_device_type
            ->setLabel(_('Output Type'))
            ->setAttrib('readonly', true)
            ->setValue(isset($setting['output_sound_device_type']) ? $setting['output_sound_device_type'] : 0)
            ->setDecorators(['ViewHelper']);
        $this->addElement($output_sound_device_type);
    }
}
