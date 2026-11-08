<?php

/**
 * RASTATIME 2026-10-08 - edit the metadata of several tracks at once
 * (operator request).  Every field is optional: an empty field leaves the
 * tracks' value as it is, a filled field is written to every selected
 * track.  The values go into the database only, like the single-track
 * editor (tags inside the files are read at import and never rewritten).
 * Title, track number, BPM, cue points and artwork are per-track by
 * nature and deliberately not here.
 */
class Application_Form_BulkEditAudioMD extends Zend_Form
{
    /** field name => max length of the text fields */
    const TEXT_FIELDS = [
        'artist_name' => 512,
        'album_title' => 512,
        'genre' => 64,
        'language' => 512,
        'mood' => 64,
        'label' => 512,
        'composer' => 512,
        'conductor' => 512,
        'copyright' => 512,
    ];

    public function init() {}

    public function startForm()
    {
        $this->setDecorators([['ViewScript', ['viewScript' => 'form/bulk-edit-audio-md.phtml']]]);
        $this->setAttrib('class', 'bulk-md-form');

        $labels = [
            'artist_name' => _('Creator:'),
            'album_title' => _('Album:'),
            'genre' => _('Genre:'),
            'language' => _('Language:'),
            'mood' => _('Mood:'),
            'label' => _('Label:'),
            'composer' => _('Composer:'),
            'conductor' => _('Conductor:'),
            'copyright' => _('Copyright:'),
        ];
        foreach (self::TEXT_FIELDS as $name => $max) {
            $el = new Zend_Form_Element_Text($name);
            $el->class = 'input_text';
            $el->setLabel($labels[$name])
                ->setRequired(false)
                ->setFilters(['StringTrim'])
                ->setValidators([new Zend_Validate_StringLength(['max' => $max])])
                ->setAttrib('placeholder', _('Leave unchanged'));
            $this->addElement($el);
        }

        $year = new Zend_Form_Element_Text('year');
        $year->class = 'input_text';
        $year->setLabel(_('Year:'))
            ->setRequired(false)
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 10]),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY-MM-DD'),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY-MM'),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY'),
            ])
            ->setAttrib('placeholder', _('Leave unchanged'));
        $this->addElement($year);

        $trackTypes = Application_Model_Tracktype::getTracktypes();
        usort($trackTypes, function ($a, $b) {
            return strcasecmp($a['type_name'], $b['type_name']);
        });
        $options = ['' => _('Leave unchanged')];
        foreach ($trackTypes as $tt) {
            $options[$tt['id']] = $tt['type_name'];
        }
        $trackType = new Zend_Form_Element_Select('track_type_id');
        $trackType->class = 'input_text';
        $trackType->setLabel(_('Track Type:'))
            ->setRequired(false)
            ->setMultiOptions($options);
        $this->addElement($trackType);

        // RASTATIME 2026-10-16 - teaser automation: set the teased show and
        // the teaser type for many jingles at once.  '' leaves the field
        // alone, 'none' clears the link (the controller maps it to '').
        // RASTATIME 2026-10-16 (operator): type first, shows only with a type
        $teaserType = new Zend_Form_Element_Select('teaser_type');
        $teaserType->class = 'input_text';
        $teaserType->setLabel(_('Teaser type:'))
            ->setRequired(false)
            ->setMultiOptions(['' => _('Leave unchanged')] + Application_Model_StoredFile::teaserTypeLabels());
        $this->addElement($teaserType);
        // multiselect (migration 0070): nothing selected leaves the links alone,
        // "None" clears them, selected shows replace the list
        $teaserOptions = ['none' => _('None')] + Application_Model_StoredFile::teaserShows();
        // a checkbox per show, like the Song-Request Pool (operator 2026-10-16)
        $teaserShow = new Zend_Form_Element_MultiCheckbox('teaser_show_id');
        $teaserShow->setLabel(_('Teaser for shows:'))
            ->setRequired(false)
            ->setDescription(_('Nothing ticked leaves the links unchanged; "None" removes them.'))
            ->setMultiOptions($teaserOptions);
        $this->addElement($teaserShow);


        // RASTATIME 2026-11-08 - "Enabled From" as in the single editor
        // (migration 0080); YYYY-MM-DD sets it, "none" clears it, empty
        // leaves it
        if (Application_Model_StoredFile::trackDatesReady()) {
            $enabledFrom = new Zend_Form_Element_Text('enabled_from');
            $enabledFrom->class = 'input_text';
            $enabledFrom->setLabel(_('Enabled From:'))
                ->setRequired(false)
                ->setFilters(['StringTrim', 'StringToLower'])
                ->setValidators([
                    Application_Form_Helper_ValidationTypes::overrideRegexValidator(
                        '/^(\d{4}-\d{2}-\d{2}|none)?$/',
                        _('Enable date must be in YYYY-MM-DD format, "none" to clear it, or empty.')
                    ),
                ])
                ->setAttrib('placeholder', _('Leave unchanged'))
                ->setDescription(_('Format: YYYY-MM-DD. Enter "none" to clear the enable date of the selected tracks.'));
            $this->addElement($enabledFrom);
        }

        // RASTATIME 2026-10-08 (operator): the expiry date as in the single
        // editor; YYYY-MM-DD sets it, "none" clears it, empty leaves it
        $expiresAt = new Zend_Form_Element_Text('expires_at');
        $expiresAt->class = 'input_text';
        $expiresAt->setLabel(_('Expiry Date:'))
            ->setRequired(false)
            ->setFilters(['StringTrim', 'StringToLower'])
            ->setValidators([
                Application_Form_Helper_ValidationTypes::overrideRegexValidator(
                    '/^(\d{4}-\d{2}-\d{2}|none)?$/',
                    _('Expiry date must be in YYYY-MM-DD format, "none" to clear it, or empty.')
                ),
            ])
            ->setAttrib('placeholder', _('Leave unchanged'))
            ->setDescription(_('Format: YYYY-MM-DD. Enter "none" to clear the expiry of the selected tracks.'));
        $this->addElement($expiresAt);

        // RASTATIME 2026-11-08 - "Track disabled" for many tracks at once
        // (operator): '' leaves it alone, '1' disables by hand, '0' enables
        // and clears expiry dates that have passed and enable dates still
        // ahead (LibraryController), since either keeps the track disabled.
        $disabled = new Zend_Form_Element_Select('disabled');
        $disabled->class = 'input_text';
        $disabled->setLabel(_('Track disabled:'))
            ->setRequired(false)
            ->setMultiOptions([
                '' => _('Leave unchanged'),
                '1' => _('Yes - disable the tracks'),
                '0' => _('No - enable the tracks'),
            ])
            ->setDescription(Application_Model_StoredFile::trackDatesReady()
                ? _('Yes: smart blocks no longer pick the selected tracks. No: they are picked again; an expiry date that has passed and an enable date still ahead are cleared.')
                : _('Yes: smart blocks no longer pick the selected tracks. No: they are picked again; an expiry date that has passed is cleared.'));
        $this->addElement($disabled);

        $description = new Zend_Form_Element_Textarea('description');
        $description->class = 'input_text';
        $description->setLabel(_('Description:'))
            ->setRequired(false)
            ->setFilters(['StringTrim'])
            ->setValidators([new Zend_Validate_StringLength(['max' => 512])])
            ->setAttrib('placeholder', _('Leave unchanged'))
            ->setAttrib('rows', 3);
        $this->addElement($description);
    }

    /** The order the dialog shows the fields in. */
    /** RASTATIME 2026-10-16 - shows need a type (also here: the selected tracks need not have one yet) */
    public function isValid($data)
    {
        $ok = parent::isValid($data);
        $shows = array_filter((array) ($data['teaser_show_id'] ?? []), static fn ($v) => $v !== '' && $v !== 'none');
        if ($shows && trim((string) ($data['teaser_type'] ?? '')) === '') {
            $this->getElement('teaser_type')->addError(_('Choose a teaser type before you pick shows'));
            $ok = false;
        }
        // RASTATIME 2026-11-08 - "No - enable" together with an expiry date
        // that has passed contradicts itself
        if (Application_Form_EditAudioMD::enableWithPassedExpiry($data)) {
            $this->getElement('expires_at')->addError(Application_Form_EditAudioMD::passedExpiryMessage());
            $ok = false;
        }
        if ($this->getElement('enabled_from')) {
            if (Application_Form_EditAudioMD::enableWithPendingDate($data)) {
                $this->getElement('enabled_from')->addError(Application_Form_EditAudioMD::pendingEnableMessage());
                $ok = false;
            }
            if (!Application_Form_EditAudioMD::datesInOrder($data)) {
                $this->getElement('enabled_from')->addError(Application_Form_EditAudioMD::datesOrderMessage());
                $ok = false;
            }
        }

        return $ok;
    }

    public static function fieldOrder()
    {
        return ['artist_name', 'album_title', 'genre', 'year', 'track_type_id', 'teaser_type', 'teaser_show_id', 'language', 'mood', 'label', 'composer', 'conductor', 'copyright', 'enabled_from', 'expires_at', 'disabled', 'description'];
    }
}
