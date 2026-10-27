<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the Multi-View
 * Schedule public embed widget.  Single text input — the
 * empty-state placeholder.  Same English-fallback pattern as
 * the other widget label forms.
 */
class Application_Form_WidgetMultiViewSchedule extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_multi_view_schedule_form');

        $el = new Zend_Form_Element_Text('widget_no_multi_view_schedule');
        $el->setLabel(_('No shows scheduled:'))
           ->setAttrib('class', 'input_text widget-label-input')
           ->setAttrib('maxlength', 80)
           ->setAttrib('placeholder', 'No shows scheduled')
           ->setAttrib('style', 'width: 18em;')
           ->setRequired(false)
           ->setAllowEmpty(true);
        $this->addElement($el);

        $submit = new Zend_Form_Element_Submit('submit');
        $submit->setLabel(_('Save'))
               ->setAttrib('class', 'btn');
        $this->addElement($submit);

        // RASTATIME 2026-10-27 (role audit R12, CSRF phase 2) - a plain
        // form post, so the session token travels as the hidden field 'csrf'
        $csrf = new Zend_Form_Element_Hidden('csrf');
        $csrf->setValue((new Zend_Session_Namespace('csrf_namespace'))->authtoken)
             ->setDecorators(['ViewHelper']);
        $this->addElement($csrf);
    }
}
