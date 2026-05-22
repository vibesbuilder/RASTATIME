<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the Current Show /
 * Current Track public embed widgets.
 *
 * Four text inputs, one per empty-state label.  Each input is
 * optional in the strict Zend sense (setAllowEmpty + !setRequired),
 * but the Preference setters fall back to the English defaults
 * when a blank value is persisted, so an operator who clears a
 * field gets the upstream default back rather than a blank widget.
 */
class Application_Form_WidgetCurrentShowTrack extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_current_show_track_form');

        $fields = [
            [
                'name'    => 'widget_no_current_show',
                'label'   => _('Label when no show is on air:'),
                'default' => 'No show on air',
            ],
            [
                'name'    => 'widget_no_upcoming_show',
                'label'   => _('Label when there is no upcoming show:'),
                'default' => 'No upcoming show',
            ],
            [
                'name'    => 'widget_no_current_track',
                'label'   => _('Label when no track is playing:'),
                'default' => 'No track playing',
            ],
            [
                'name'    => 'widget_no_upcoming_track',
                'label'   => _('Label when there is no upcoming track:'),
                'default' => 'No upcoming track',
            ],
        ];

        foreach ($fields as $f) {
            $el = new Zend_Form_Element_Text($f['name']);
            $el->setLabel($f['label'])
               ->setAttrib('class', 'input_text')
               ->setAttrib('maxlength', 80)
               ->setAttrib('placeholder', $f['default'])
               ->setRequired(false)
               ->setAllowEmpty(true);
            $this->addElement($el);
        }

        $submit = new Zend_Form_Element_Submit('submit');
        $submit->setLabel(_('Save'))
               ->setAttrib('class', 'btn');
        $this->addElement($submit);
    }
}
