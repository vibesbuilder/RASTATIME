<?php

class Application_Form_LiveStreamingPreferences extends Zend_Form_SubForm
{
    public function init()
    {
        $defaultFade = Application_Model_Preference::GetDefaultTransitionFade();

        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/preferences_livestream.phtml']],
        ]);

        // RASTATIME 2026-05-14 — the upstream "Auto Switch On" /
        // "Auto Switch Off" checkboxes were removed.  In LibreTime
        // their only effect path was ApiController::updateSourceStatusAction
        // sending RabbitMQ messages to the Pypo/Liquidsoap playout —
        // both removed in ADR-002.  The SourceSwitcher in
        // backend/playout/libretime_playout/source_switcher.py now
        // performs the equivalent transitions unconditionally
        // (Master > Show > Scheduled).  Re-introducing operator gates
        // requires real Use-Case input first; see CHANGELOG entry for
        // the removal rationale.

        // Default transition fade
        // RASTATIME 2026-09-28 - shapes the DJ hand-over in the Liquidsoap bus
        // (rendered into rastatime.liq, applied by the settings restart).
        $transition_fade = new Zend_Form_Element_Text('transition_fade');
        $transition_fade->setLabel(_('Switch Transition Fade (s):'))
            ->setDescription(_('When a DJ connects, the DJ is on air at once and the programme fades out underneath over this many seconds; when the DJ disconnects, the DJ fades out and the programme returns at full level at once.'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, [
                '/^\d*(\.\d+)?$/',
                'messages' => _('Please enter a time in seconds (eg. 0.5)'),
            ])
            ->setValue($defaultFade);
        $this->addElement($transition_fade);

        // Master username
        $master_username = new Zend_Form_Element_Text('master_username');
        $master_username->setAttrib('autocomplete', 'off')
            ->setAllowEmpty(true)
            ->setLabel(_('Username:'))
            ->setFilters(['StringTrim'])
            ->setValue(Application_Model_Preference::GetLiveStreamMasterUsername());
        $this->addElement($master_username);

        // Master password
        $master_password = new Zend_Form_Element_Password('master_password');
        $master_password
            ->setAttrib('autocomplete', 'off')
            ->setAttrib('renderPassword', 'true')
            ->setAllowEmpty(true)
            ->setValue(Application_Model_Preference::GetLiveStreamMasterPassword())
            ->setLabel(_('Password:'))
            ->setFilters(['StringTrim']);
        $this->addElement($master_password);

        // Master source connection url parameters
        $masterSourceHost = new Zend_Form_Element_Text('master_source_host');
        $masterSourceHost
            ->setLabel(_('Master Source Host:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_Preference::GetMasterDJSourceConnectionURL());
        $this->addElement($masterSourceHost);

        $masterSourcePort = new Zend_Form_Element_Text('master_source_port');
        $masterSourcePort
            ->setLabel(_('Master Source Port:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_StreamSetting::getMasterLiveStreamPort());
        $this->addElement($masterSourcePort);

        $masterSourceMount = new Zend_Form_Element_Text('master_source_mount');
        $masterSourceMount
            ->setLabel(_('Master Source Mount:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_StreamSetting::getMasterLiveStreamMountPoint());
        $this->addElement($masterSourceMount);

        // Show source connection url parameters
        $showSourceHost = new Zend_Form_Element_Text('show_source_host');
        $showSourceHost
            ->setLabel(_('Show Source Host:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_Preference::GetLiveDJSourceConnectionURL());
        $this->addElement($showSourceHost);

        $showSourcePort = new Zend_Form_Element_Text('show_source_port');
        $showSourcePort
            ->setLabel(_('Show Source Port:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_StreamSetting::getDjLiveStreamPort());
        $this->addElement($showSourcePort);

        $showSourceMount = new Zend_Form_Element_Text('show_source_mount');
        $showSourceMount
            ->setLabel(_('Show Source Mount:'))
            ->setAttrib('readonly', true)
            ->setValue(Application_Model_StreamSetting::getDjLiveStreamMountPoint());
        $this->addElement($showSourceMount);
    }

    public function updateVariables()
    {
        $this->setDecorators(
            [
                [
                    'ViewScript',
                    [
                        'viewScript' => 'form/preferences_livestream.phtml',
                        'master_source_host' => isset($masterSourceHost) ? Application_Model_Preference::GetMasterDJSourceConnectionURL() : '',
                        'master_source_port' => isset($masterSourcePort) ? Application_Model_StreamSetting::getMasterLiveStreamPort() : '',
                        'master_source_mount' => isset($masterSourceMount) ? Application_Model_StreamSetting::getMasterLiveStreamMountPoint() : '',
                        'show_source_host' => isset($showSourceHost) ? Application_Model_Preference::GetLiveDJSourceConnectionURL() : '',
                        'show_source_port' => isset($showSourcePort) ? Application_Model_StreamSetting::getDjLiveStreamPort() : '',
                        'show_source_mount' => isset($showSourceMount) ? Application_Model_StreamSetting::getDjLiveStreamMountPoint() : '',
                    ],
                ],
            ]
        );
    }
}
