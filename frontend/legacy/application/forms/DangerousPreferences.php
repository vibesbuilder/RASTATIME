<?php

class Application_Form_DangerousPreferences extends Zend_Form_SubForm
{
    public function init()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/preferences_danger.phtml']],
        ]);

        $clearLibrary = new Zend_Form_Element_Button('clear_library');
        $clearLibrary->setLabel(_('Delete All Tracks in Library'));
        // $submit->removeDecorator('Label');
        $clearLibrary->setAttribs(['class' => 'btn centered']);
        $clearLibrary->setAttrib('onclick', 'deleteAllFiles();');
        $clearLibrary->removeDecorator('DtDdWrapper');

        $this->addElement($clearLibrary);

        // RASTATIME 2026-10-14 - operator wish: empty the calendar from now on
        $clearCalendar = new Zend_Form_Element_Button('clear_calendar');
        $clearCalendar->setLabel(_('Clear Calendar'));
        $clearCalendar->setAttribs(['class' => 'btn centered']);
        $clearCalendar->setAttrib('onclick', 'clearCalendar();');
        $clearCalendar->removeDecorator('DtDdWrapper');
        $this->addElement($clearCalendar);
    }
}
