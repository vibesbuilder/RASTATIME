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

        // RASTATIME 2026-05-22 UI polish: labels shortened to mirror
        // the empty-state strings they configure ("No show on air:"
        // instead of "Label when no show is on air:") so the form
        // reads as a list of the actual outputs rather than a list of
        // meta-descriptions.  Input width is shorter
        // (`sp_input_text_limit`-style) — 80 chars of maxlength is
        // far more than any reasonable placeholder text needs.
        $fields = [
            [
                'name'    => 'widget_no_current_show',
                'label'   => _('No show on air:'),
                'default' => 'No show on air',
            ],
            [
                'name'    => 'widget_no_upcoming_show',
                'label'   => _('No upcoming show:'),
                'default' => 'No upcoming show',
            ],
            [
                'name'    => 'widget_no_current_track',
                'label'   => _('No track playing:'),
                'default' => 'No track playing',
            ],
            [
                'name'    => 'widget_no_upcoming_track',
                'label'   => _('No upcoming track:'),
                'default' => 'No upcoming track',
            ],
        ];

        foreach ($fields as $f) {
            $el = new Zend_Form_Element_Text($f['name']);
            $el->setLabel($f['label'])
               ->setAttrib('class', 'input_text widget-label-input')
               ->setAttrib('maxlength', 80)
               ->setAttrib('placeholder', $f['default'])
               ->setAttrib('style', 'width: 18em;')
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
