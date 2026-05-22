<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the Track History
 * public embed widget.  Single text input — the empty-state
 * placeholder.  Same English-fallback pattern as the other
 * widget label forms.
 */
class Application_Form_WidgetTrackHistory extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_track_history_form');

        $el = new Zend_Form_Element_Text('widget_no_track_history');
        $el->setLabel(_('No tracks played on this day:'))
           ->setAttrib('class', 'input_text widget-label-input')
           ->setAttrib('maxlength', 80)
           ->setAttrib('placeholder', 'No tracks played on this day')
           ->setAttrib('style', 'width: 18em;')
           ->setRequired(false)
           ->setAllowEmpty(true);
        $this->addElement($el);

        $submit = new Zend_Form_Element_Submit('submit');
        $submit->setLabel(_('Save'))
               ->setAttrib('class', 'btn');
        $this->addElement($submit);
    }
}
