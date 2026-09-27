<?php

class Application_Form_EditAudioMD extends Zend_Form
{
    public function init() {}

    public function startForm($p_id)
    {
        // Set the method for the display form to POST
        $this->setMethod('post');
        $this->setAttrib('id', 'track_edit_' . $p_id);

        $file_id = new Zend_Form_Element_Hidden('file_id');
        $file_id->setValue($p_id);
        $file_id->setDecorators(['ViewHelper']);
        $file_id->addDecorator('HtmlTag', ['tag' => 'div', 'style' => 'display:none']);
        $file_id->removeDecorator('Label');
        $file_id->setAttrib('class', 'obj_id');
        $this->addElement($file_id);

        // Add artwork hidden field
        $artwork = new Zend_Form_Element_Hidden('artwork');
        $artwork->class = 'input_text artwork_' . $p_id;
        $artwork->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 2048]),
            ]);
        $artwork->addDecorator('HtmlTag', ['tag' => 'div', 'style' => 'display:none']);
        $artwork->removeDecorator('Label');
        $artwork->setAttrib('class', 'artwork');
        $this->addElement($artwork);

        // Set artwork hidden field.
        // RASTATIME bug fix: the upstream code first sets `->class = 'set_artwork_<id>'`
        // and then overwrites it with `->setAttrib('class', 'set_artwork')` — that
        // wipes out the per-track id-suffixed selector that library.js targets via
        // `$('.set_artwork_' + id)`.  Without the id-suffix, the JS never finds the
        // hidden input and the chosen artwork data-URI is never written into the
        // form, so save submits an empty value.  We collapse both into a single
        // setAttrib call that contains every class library.js / CSS may need.
        $set_artwork = new Zend_Form_Element_Hidden('set_artwork');
        $set_artwork->addDecorator('HtmlTag', ['tag' => 'div', 'style' => 'display:none']);
        $set_artwork->removeDecorator('Label');
        $set_artwork->setAttrib('class', 'input_text set_artwork set_artwork_' . $p_id);
        $this->addElement($set_artwork);

        // Remove artwork hidden field — same upstream class-overwrite bug as above.
        $remove_artwork = new Zend_Form_Element_Hidden('remove_artwork');
        $remove_artwork->addDecorator('HtmlTag', ['tag' => 'div', 'style' => 'display:none']);
        $remove_artwork->removeDecorator('Label');
        $remove_artwork->setAttrib('class', 'input_text remove_artwork remove_artwork_' . $p_id);
        $this->addElement($remove_artwork);

        // Add title field
        $track_title = new Zend_Form_Element_Text('track_title');
        $track_title->class = 'input_text';
        $track_title->setLabel(_('Title:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($track_title);

        // Add artist field
        $artist_name = new Zend_Form_Element_Text('artist_name');
        $artist_name->class = 'input_text';
        $artist_name->setLabel(_('Creator:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($artist_name);

        // Add album field
        $album_title = new Zend_Form_Element_Text('album_title');
        $album_title->class = 'input_text';
        $album_title->setLabel(_('Album:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($album_title);

        // Add album field
        $user_options = [];
        $users = Application_Model_User::getNonGuestUsers();

        foreach ($users as $host) {
            $user_options[$host['index']] = $host['label'];
        }

        $owner_id = new Zend_Form_Element_Select('owner_id');
        $owner_id->class = 'input_text';
        $owner_id->setLabel(_('Owner:'));
        $owner_id->setMultiOptions($user_options);
        $this->addelement($owner_id);

        // Add track type dropdown
        $track_type_options = [];
        $track_types = Application_Model_Tracktype::getTracktypes();

        array_multisort(array_map(function ($element) {
            return $element['type_name'];
        }, $track_types), SORT_ASC, $track_types);

        $track_type_options[''] = _('Select a Type');
        foreach ($track_types as $key => $tt) {
            $track_type_options[$tt['id']] = $tt['type_name'];
        }

        $track_type_id = new Zend_Form_Element_Select('track_type_id');
        $track_type_id->class = 'input_text';
        $track_type_id->setLabel(_('Track Type:'));
        $track_type_id->setMultiOptions($track_type_options);
        $this->addelement($track_type_id);

        // Description field
        $description = new Zend_Form_Element_Textarea('description');
        $description->class = 'input_text';
        $description->setLabel(_('Description:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($description);

        // Add track number field
        $track_number = new Zend_Form_Element('track_number');
        $track_number->class = 'input_text';
        $track_number->setLabel('Track Number:')
            ->setFilters(['StringTrim'])
            ->setValidators([new Zend_Validate_Int()]);
        $this->addElement($track_number);

        // Add genre field
        $genre = new Zend_Form_Element('genre');
        $genre->class = 'input_text';
        $genre->setLabel(_('Genre:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 64]),
            ]);
        $this->addElement($genre);

        // Add year field
        $year = new Zend_Form_Element_Text('year');
        $year->class = 'input_text';
        $year->setLabel(_('Year:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 10]),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY-MM-DD'),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY-MM'),
                Application_Form_Helper_ValidationTypes::overrrideDateValidator('YYYY'),
            ]);
        $this->addElement($year);

        // Add label field
        $label = new Zend_Form_Element('label');
        $label->class = 'input_text';
        $label->setLabel(_('Label:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($label);

        // Add composer field
        $composer = new Zend_Form_Element('composer');
        $composer->class = 'input_text';
        $composer->setLabel(_('Composer:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($composer);

        // Add conductor field
        $conductor = new Zend_Form_Element('conductor');
        $conductor->class = 'input_text';
        $conductor->setLabel(_('Conductor:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($conductor);

        // Add mood field
        $mood = new Zend_Form_Element('mood');
        $mood->class = 'input_text';
        $mood->setLabel(_('Mood:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 64]),
            ]);
        $this->addElement($mood);

        // Add bmp field
        $bpm = new Zend_Form_Element_Text('bpm');
        $bpm->class = 'input_text';
        $bpm->setLabel(_('BPM:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['min' => 0, 'max' => 8]),
                new Zend_Validate_Digits(),
            ]);
        $this->addElement($bpm);

        // Add copyright field
        $copyright = new Zend_Form_Element('copyright');
        $copyright->class = 'input_text';
        $copyright->setLabel(_('Copyright:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($copyright);

        // Add isrc number field
        $isrc_number = new Zend_Form_Element('isrc_number');
        $isrc_number->class = 'input_text';
        $isrc_number->setLabel(_('ISRC Number:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($isrc_number);

        // Add website field
        $info_url = new Zend_Form_Element('info_url');
        $info_url->class = 'input_text';
        $info_url->setLabel(_('Website:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($info_url);

        // Add language field
        $language = new Zend_Form_Element('language');
        $language->class = 'input_text';
        $language->setLabel(_('Language:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 512]),
            ]);
        $this->addElement($language);

        $validCuePattern = '/^(?:[0-9]{1,2}:)?(?:[0-9]{1,2}:)?[0-9]{1,6}(\.\d{1,6})?$/';

        $cueIn = new Zend_Form_Element_Text('cuein');
        $cueIn->class = 'input_text cuein_' . $p_id;
        $cueIn->setLabel('Cue In:');
        $cueInValidator = Application_Form_Helper_ValidationTypes::overrideRegexValidator(
            $validCuePattern,
            _(sprintf('Specify cue in time in the format %s', '(hh:mm:)ss(.dddddd)'))
        );
        $cueIn->setValidators([$cueInValidator]);
        $this->addElement($cueIn);

        $cueOut = new Zend_Form_Element_Text('cueout');
        $cueOut->class = 'input_text cueout_' . $p_id;
        $cueOut->setLabel('Cue Out:');
        $cueOutValidator = Application_Form_Helper_ValidationTypes::overrideRegexValidator(
            $validCuePattern,
            _(sprintf('Specify cue out time in the format %s', '(hh:mm:)ss(.dddddd)'))
        );
        $cueOut->setValidators([$cueOutValidator]);
        $this->addElement($cueOut);

        // RASTATIME 2026-05-16 - Track Expiry: manual override of the
        // expires_at value.  Accepts ISO 8601 date (YYYY-MM-DD) or empty
        // (clears the expiry).  Auto-Expiry from a parent podcast will
        // also write to this column at import time (precedence decision
        // B); the operator can override either at edit time.
        $expiresAt = new Zend_Form_Element_Text('expires_at');
        $expiresAt->class = 'input_text';
        $expiresAt->setLabel(_('Expiry Date:'));
        $expiresAt->setDescription(_('Format: YYYY-MM-DD.  Empty = no expiry.'));
        $expiresAt->setFilters(['StringTrim']);
        $expiresAt->setValidators([
            Application_Form_Helper_ValidationTypes::overrideRegexValidator(
                '/^(\d{4}-\d{2}-\d{2})?$/',
                _('Expiry date must be in YYYY-MM-DD format or empty.')
            ),
        ]);
        $this->addElement($expiresAt);

        // RASTATIME 2026-09-27 - "Exclude from Crossover" (cc_files.
        // exclude_crossfade, migration 0059, raw SQL in StoredFile).  A
        // flagged track is never faded: it plays to its end and the next
        // track follows without overlap.  Zend renders the unchecked value
        // as a hidden input, so the form POST always carries the key.
        $excludeCrossfade = new Zend_Form_Element_Checkbox('exclude_crossfade');
        $excludeCrossfade->setLabel(_('Exclude from Crossover:'));
        $excludeCrossfade->setDescription(_('This track is never faded: it plays to its end and the next track follows without overlap.'));
        $excludeCrossfade->setCheckedValue('1');
        $excludeCrossfade->setUncheckedValue('0');
        $this->addElement($excludeCrossfade);

        // Add the cancel button
        $this->addElement('button', 'editmdcancel', [
            'ignore' => true,
            'class' => 'btn md-cancel',
            'label' => _('Cancel'),
            'decorators' => [
                'ViewHelper',
            ],
        ]);

        // Add the submit button
        $this->addElement('button', 'editmdsave', [
            'ignore' => true,
            'class' => 'btn md-save',
            'label' => _('Save'),
            'decorators' => [
                'ViewHelper',
            ],
        ]);

        // Button to open the publish dialog
        $this->addElement('button', 'publishdialog', [
            'ignore' => true,
            'class' => 'btn md-publish',
            'label' => _('Publish...'),
            'decorators' => [
                'ViewHelper',
            ],
        ]);

        $this->addDisplayGroup(['publishdialog', 'editmdsave', 'editmdcancel'], 'submitButtons', [
            'decorators' => [
                'FormElements',
                'DtDdWrapper',
            ],
        ]);
    }

    public function makeReadOnly()
    {
        foreach ($this as $element) {
            $element->setAttrib('readonly', 'readonly');
        }
    }

    public function removeOwnerEdit()
    {
        $this->removeElement('owner_id');
    }

    public function removeActionButtons()
    {
        $this->removeElement('editmdsave');
        $this->removeElement('editmdcancel');
    }
}
