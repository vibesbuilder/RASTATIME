<?php

/**
 * RASTATIME 2026-11-10 - Radioplayer "now playing" feed for ORF Sound
 * (Settings -> General, below Live Text Info).
 *
 * ORF Sound polls a JSON endpoint in the format of the Radioplayer v4
 * "events" lookup (previous / now / next) for private stations that are
 * not on the Radioplayer platform.  RASTATIME answers it at
 * /embed/radioplayer-events (EmbedController::radioplayerEventsAction),
 * independent of Live Text Info and of the public API switch.
 */
class Application_Form_RadioplayerPreferences extends Zend_Form_SubForm
{
    public function init()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/preferences_radioplayer.phtml']],
        ]);

        $enable = new Zend_Form_Element_Checkbox('enable_radioplayer');
        $enable->setDecorators(['ViewHelper', 'Errors', 'Label']);
        $enable->addDecorator('Label', ['class' => 'enable-radioplayer']);
        $enable->setLabel(_('Provide the "now playing" feed for ORF Sound (Radioplayer events)?'));
        $enable->setValue(Application_Model_Preference::getRadioplayerEnabled());
        $this->addElement($enable);

        $key = new Zend_Form_Element_Text('radioplayer_key');
        $key->setLabel(_('Access key (optional):'))
            ->setDescription(_('When set, the feed answers only with ?key=<this value> in the address (give the full address to ORF). Letters, digits, - and _ only. Empty = no key.'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^[A-Za-z0-9_-]{0,64}$/', 'messages' => _('Letters, digits, - and _ only (at most 64).')])
            ->setValue(Application_Model_Preference::getRadioplayerKey())
            ->setAttrib('class', 'input_text')
            ->setAttrib('autocomplete', 'off');
        $this->addElement($key);

        $rpId = new Zend_Form_Element_Text('radioplayer_rp_id');
        $rpId->setLabel(_('Station ID (rpId, optional):'))
            ->setDescription(_('The ID your distribution partner assigned to the station, if any. Empty = the field stays empty.'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^[A-Za-z0-9_.-]{0,32}$/', 'messages' => _('Letters, digits, ., - and _ only (at most 32).')])
            ->setValue(Application_Model_Preference::getRadioplayerRpId())
            ->setAttrib('class', 'input_text');
        $this->addElement($rpId);

        $description = new Zend_Form_Element_Text('radioplayer_service_description');
        $description->setLabel(_('Station description (serviceDescription):'))
            ->setDescription(_('Shown when nothing else is known about the programme. Empty = the station description from General.'))
            ->setFilters(['StringTrim'])
            ->setValue(Application_Model_Preference::getRadioplayerServiceDescription())
            ->setAttrib('class', 'input_text')
            ->setAttrib('maxlength', 1000);
        $this->addElement($description);

        $previous = new Zend_Form_Element_Text('radioplayer_previous');
        $previous->setLabel(_('Number of previous tracks:'))
            ->setDescription(_('How many of the last played tracks the feed lists (0..20).'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^\d{0,2}$/', 'messages' => _('Please enter a number from 0 to 20.')])
            ->setValue(Application_Model_Preference::getRadioplayerPrevious())
            ->setAttrib('class', 'input_text')
            ->setAttrib('style', 'width: 6em;');
        $this->addElement($previous);

        $minSeconds = new Zend_Form_Element_Text('radioplayer_min_seconds');
        $minSeconds->setLabel(_('Leave out tracks shorter than (s):'))
            ->setDescription(_('Jingles and station IDs stay out of the list of previous tracks and out of "now". 0 = list everything.'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^\d{0,3}$/', 'messages' => _('Please enter a number of seconds.')])
            ->setValue(Application_Model_Preference::getRadioplayerMinSeconds())
            ->setAttrib('class', 'input_text')
            ->setAttrib('style', 'width: 6em;');
        $this->addElement($minSeconds);

        $poll = new Zend_Form_Element_Text('radioplayer_poll_seconds');
        $poll->setLabel(_('Suggested polling interval (s):'))
            ->setDescription(_('Sent to the partner as pollNext (5..120 s).'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^\d{0,3}$/', 'messages' => _('Please enter a number of seconds.')])
            ->setValue(Application_Model_Preference::getRadioplayerPollSeconds())
            ->setAttrib('class', 'input_text')
            ->setAttrib('style', 'width: 6em;');
        $this->addElement($poll);
    }
}
