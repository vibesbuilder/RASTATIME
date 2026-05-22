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
             ->setAttrib('title', _('Pick a show from the live database.  '
                . 'If both this dropdown and the manual name below are set, '
                . 'the dropdown wins (same precedence as ?show_id vs ?show '
                . 'on the public widget URL).'))
             ->setRequired(false)
             ->setAllowEmpty(true)
             ->setRegisterInArrayValidator(false);
        $this->addElement($show);

        // RASTATIME 2026-05-22 — manual show-name input.  Lets the
        // operator generate an embed snippet for a show that isn't
        // (yet) in the database, or for a name they want to point at
        // by string rather than id.  Lower precedence than the
        // dropdown: when both are filled, the dropdown wins (matches
        // the show_id > show fallback rule the public widget
        // already implements at the URL level).
        $showName = new Zend_Form_Element_Text('manual_show_name');
        $showName->setLabel(_('Show name:'))
                 ->setAttrib('class', 'input_text widget-show-name')
                 ->setAttrib('maxlength', 200)
                 ->setAttrib('placeholder', _('e.g. Morning Show'))
                 ->setAttrib('style', 'width: 18em;')
                 ->setAttrib('title', _('Manually type a cc_show.name to '
                    . 'filter on.  The chosen show from the dropdown above '
                    . 'takes precedence over this field, matching the '
                    . '?show_id > ?show rule the public widget URL uses.'))
                 ->setRequired(false)
                 ->setAllowEmpty(true);
        $this->addElement($showName);

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
