<?php

class Application_Form_AddShowWhat extends Zend_Form_SubForm
{
    public function init()
    {
        $notEmptyValidator = Application_Form_Helper_ValidationTypes::overrideNotEmptyValidator();
        // retrieves the length limit for each char field
        // and store to assoc array
        $maxLens = Application_Model_Show::getMaxLengths();

        // Hidden element to indicate whether the show is new or
        // whether we are updating an existing show.
        $this->addElement('hidden', 'add_show_id', [
            'decorators' => ['ViewHelper'],
        ]);

        // Hidden element to indicate the instance id of the show
        // being edited.
        $this->addElement('hidden', 'add_show_instance_id', [
            'decorators' => ['ViewHelper'],
        ]);

        // Add name element
        $this->addElement('text', 'add_show_name', [
            'label' => _('Name:'),
            'class' => 'input_text',
            'required' => true,
            'filters' => ['StringTrim'],
            'value' => _('Untitled Show'),
            'validators' => [$notEmptyValidator, ['StringLength', false, [0, $maxLens['name']]]],
        ]);

        // Add URL element
        $this->addElement('text', 'add_show_url', [
            'label' => _('URL:'),
            'class' => 'input_text',
            'required' => false,
            'filters' => ['StringTrim'],
            'validators' => [$notEmptyValidator, ['StringLength', false, [0, $maxLens['url']]]],
        ]);

        // Add genre element
        $this->addElement('text', 'add_show_genre', [
            'label' => _('Genre:'),
            'class' => 'input_text',
            'required' => false,
            'filters' => ['StringTrim'],
            'validators' => [['StringLength', false, [0, $maxLens['genre']]]],
        ]);

        // RASTATIME 2026-11-03 - yearly report: the station's own production
        // (counted in Analytics -> Programme Minutes and People Involved).
        // 2026-11-04 (operator): help icon right of the label; the number of
        // people involved moved here from Archiving and shows only while the
        // box is ticked (add-show.js syncOwnProduction).  Stored in
        // cc_show_archiving.participants (ArchivingService::saveParticipants).
        $this->addElement('checkbox', 'add_show_own_production', [
            'label' => _('Own production:'),
            'description' => _('The station makes this show itself. Its aired minutes count in Analytics → Programme Minutes, its people in Analytics → People Involved.'),
            'required' => false,
            'decorators' => [['ViewScript', ['viewScript' => 'form/add-show-tip-row.phtml', 'class' => 'rt-own-production']]],
        ]);
        // 2026-11-07 (operator): "Hosts involved" - the hosts who are the
        // same in every episode, counted once per show and year; the guests
        // of a single episode are added on top (Archive Online).
        $this->addElement('text', 'add_show_participants', [
            'label' => _('Hosts involved:'),
            'description' => _('How many hosts take part in every episode. Counted once per year in Analytics → People Involved, however many episodes aired. Guests of a single episode: Archive Online in the calendar → "Guests involved".'),
            'class' => 'input_text',
            'required' => false,
            'filters' => ['StringTrim'],
            'validators' => [['Regex', false, [
                'pattern' => '/^\d{1,3}$/',
                'messages' => [Zend_Validate_Regex::NOT_MATCH => _('Please enter a whole number between 0 and 999.')],
            ]]],
            'decorators' => [['ViewScript', ['viewScript' => 'form/add-show-tip-row.phtml', 'class' => 'rt-participants-row']]],
        ]);

        // Add the description element
        $this->addElement('textarea', 'add_show_description', [
            'label' => _('Description:'),
            'required' => false,
            'class' => 'input_text_area',
            'validators' => [['StringLength', false, [0, $maxLens['description']]]],
        ]);

        $descText = $this->getElement('add_show_description');

        $descText->setDecorators([['ViewScript', [
            'viewScript' => 'form/add-show-block.phtml',
            'class' => 'block-display',
        ]]]);

        // Add the instance description
        $this->addElement('textarea', 'add_show_instance_description', [
            'label' => _('Instance Description:'),
            'required' => false,
            'class' => 'input_text_area',
            'validators' => [['StringLength', false, [0, $maxLens['description']]]],
        ]);

        $instanceDesc = $this->getElement('add_show_instance_description');

        $instanceDesc->setDecorators([['ViewScript', [
            'viewScript' => 'form/add-show-block.phtml',
            'class' => 'block-display',
        ]]]);
        $instanceDesc->setAttrib('disabled', 'disabled');
    }

    /**
     * Enable the instance description when editing a show instance.
     */
    public function enableInstanceDesc()
    {
        $el = $this->getElement('add_show_instance_description');
        $el->setAttrib('disabled', null);
        $el->setAttrib('readonly', null);
    }

    public function disable()
    {
        $elements = $this->getElements();
        foreach ($elements as $element) {
            if ($element->getType() != 'Zend_Form_Element_Hidden') {
                $element->setAttrib('disabled', 'disabled');
            }
        }
    }

    public function makeReadonly()
    {
        // RASTATIME 2026-05-18 — every "What" field stays read-only in
        // the per-instance edit dialog, including add_show_name.  The
        // show name lives on cc_show (one row per show), not on the
        // per-instance cc_show_instances row, so renaming from this
        // dialog would silently rename ALL instances of the series —
        // confusing because the operator only opened the dialog for
        // one specific instance.  The straightforward UX answer is to
        // grey out the field here and let the operator use the
        // separate "Edit Show" menu entry for a series-wide rename.
        //
        // (An earlier interim fix in this file tried to keep
        // add_show_name editable here, but the resulting "rename all
        // instances by editing one" semantics were equally
        // confusing.  The reverted behaviour matches upstream
        // LibreTime and the operator's explicit decision
        // 2026-05-18.)
        $elements = $this->getElements();
        foreach ($elements as $element) {
            if ($element->getType() != 'Zend_Form_Element_Hidden') {
                $element->setAttrib('readonly', 'readonly');
            }
        }
    }
}
