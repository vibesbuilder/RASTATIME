<?php

class Application_Form_AddTracktype extends Zend_Form
{
    public function init()
    {
        $notEmptyValidator = Application_Form_Helper_ValidationTypes::overrideNotEmptyValidator();

        $this->setAttrib('id', 'tracktype_form');

        $hidden = new Zend_Form_Element_Hidden('tracktype_id');
        $hidden->setDecorators(['ViewHelper']);
        $this->addElement($hidden);

        $this->addElement('hash', 'csrf', [
            'salt' => 'unique',
        ]);

        $typeName = new Zend_Form_Element_Text('type_name');
        $typeName->setLabel(_('Type Name:'));
        $typeName->setAttrib('class', 'input_text');
        $typeName->addFilter('StringTrim');
        $this->addElement($typeName);

        $code = new Zend_Form_Element_Text('code');
        $code->setLabel(_('Code:'));
        $code->setAttrib('class', 'input_text');
        $code->setAttrib('style', 'width: 40%');
        $code->setRequired(true);
        $code->addValidator($notEmptyValidator);

        $uniqueTrackTypeCodeValidator = new Zend_Validate_Callback(function ($value, $context) {
            if (strlen($context['tracktype_id']) === 0) { // Only check uniqueness on create
                return CcTracktypesQuery::create()->filterByDbCode($value)->count() === 0;
            }

            return true;
        });
        $uniqueTrackTypeCodeValidator->setMessage(_('Code is not unique.'));
        $code->addValidator($uniqueTrackTypeCodeValidator);

        $code->addFilter('StringTrim');
        $this->addElement($code);

        $description = new Zend_Form_Element_Textarea('description');
        $description->setLabel(_('Description:'))
            ->setFilters(['StringTrim'])
            ->setValidators([
                new Zend_Validate_StringLength(['max' => 200]),
            ]);
        $description->setAttrib('class', 'input_text');
        $description->addFilter('StringTrim');
        $this->addElement($description);

        $visibility = new Zend_Form_Element_Select('visibility');
        $visibility->setLabel(_('Visibility:'));
        $visibility->setAttrib('class', 'input_select');
        $visibility->setAttrib('style', 'width: 40%');
        $visibility->setMultiOptions([
            '0' => _('Disabled'),
            '1' => _('Enabled'),
        ]);
        // $visibility->getValue();
        $visibility->setRequired(true);
        $this->addElement($visibility);

        $analyze_cue_points = new Zend_Form_Element_Checkbox('analyze_cue_points');
        $analyze_cue_points->setLabel(_('Analyze cue points:'));
        $analyze_cue_points->setRequired(true);
        $this->addElement($analyze_cue_points);

        // RASTATIME 2026-09-29 - crossfade per track type (migration 0062)
        $crossfade = new Zend_Form_Element_Text('crossfade_duration');
        $crossfade->setLabel(_('Crossfade Duration (s):'));
        $crossfade->setAttrib('class', 'input_text');
        $crossfade->setAttrib('style', 'width: 40%');
        $crossfade->setAttrib('placeholder', _('house value'));
        $crossfade->setRequired(false);
        $crossfade->setAllowEmpty(true);
        $crossfade->addFilter('StringTrim');
        $crossfade->addValidator('Regex', false, [
            'pattern' => '/^[0-9]{1,2}([.,][0-9]{1,2})?$/',
            'messages' => ['regexNotMatch' => _('Please enter seconds between 0 and 30, e.g. 0 or 1.5.')],
        ]);
        $crossfade->setDescription(_('How long two neighbouring tracks of this type overlap and fade. Empty = the Default Track Crossfade Duration from Settings - General. Between two tracks the smaller of the two values applies, so 0 makes every track of this type start exactly at the end of the previous one (jingles, exactly timed elements). A change re-lays the rows of all upcoming shows.'));
        $this->addElement($crossfade);

        $saveBtn = new Zend_Form_Element_Button('save_tracktype');
        $saveBtn->setAttrib('class', 'btn right-floated');
        $saveBtn->setIgnore(true);
        $saveBtn->setLabel(_('Save'));
        $this->addElement($saveBtn);
    }
}
