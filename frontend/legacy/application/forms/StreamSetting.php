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
