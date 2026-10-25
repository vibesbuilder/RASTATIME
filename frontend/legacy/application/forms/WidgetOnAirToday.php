<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the On-Air-Today public
 * embed widget.
 *
 * Just one text input — the empty-state placeholder.  Optional in
 * the strict Zend sense (setAllowEmpty + !setRequired); the
 * Preference getter falls back to the English default when blank,
 * so an operator who clears the field gets the upstream default
 * back rather than a blank widget.
 */
class Application_Form_WidgetOnAirToday extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_on_air_today_form');

        // RASTATIME 2026-10-25 (operator) - the widget title; empty = "On Air Today"
        $title = new Zend_Form_Element_Text('widget_on_air_today_title');
        $title->setLabel(_('Title:'))
              ->setAttrib('class', 'input_text widget-label-input')
              ->setAttrib('maxlength', 60)
              ->setAttrib('placeholder', 'On Air Today')
              ->setAttrib('style', 'width: 18em;')
              ->setRequired(false)
              ->setAllowEmpty(true);
        $this->addElement($title);

        $el = new Zend_Form_Element_Text('widget_no_on_air_today');
        $el->setLabel(_('No shows on air today:'))
           ->setAttrib('class', 'input_text widget-label-input')
           ->setAttrib('maxlength', 80)
           ->setAttrib('placeholder', 'No shows on air today')
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
