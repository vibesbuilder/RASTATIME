<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the Next-Shows /
 * Latest-Shows public embed widgets.
 *
 * Two text inputs (one per empty-state label) plus a dropdown of
 * existing shows so the operator can pick the show the embed code
 * (rendered separately in the view) should be pre-filled for.
 *
 * The dropdown is informational only — it drives the preview iframes
 * and the embed-code blocks below the form; the actual data
 * persistence covers just the two labels.
 */
class Application_Form_WidgetNextLatestShows extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_next_latest_shows_form');

        // Show picker.  Populated from cc_show in the controller via
        // setMultiOptions before the form renders; the form layer
        // only declares the element so the view can render it.
        $show = new Zend_Form_Element_Select('preview_show_id');
        $show->setLabel(_('Preview show:'))
             ->setAttrib('class', 'input_select widget-show-select')
             ->setAttrib('style', 'width: 18em;')
             ->setRequired(false)
             ->setAllowEmpty(true)
             ->setRegisterInArrayValidator(false);
        $this->addElement($show);

        $fields = [
            [
                'name'    => 'widget_no_next_shows',
                'label'   => _('No upcoming shows:'),
                'default' => 'No upcoming shows',
            ],
            [
                'name'    => 'widget_no_latest_shows',
                'label'   => _('No past shows:'),
                'default' => 'No past shows',
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
