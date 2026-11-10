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

        // RASTATIME 2026-11-10 - date format of both widgets; the options
        // (format => example in the station language) come from the
        // controller via setMultiOptions.
        $dateFormat = new Zend_Form_Element_Select('widget_shows_date_format');
        $dateFormat->setLabel(_('Date format:'))
                   ->setAttrib('class', 'input_select')
                   ->setAttrib('style', 'width: 18em;')
                   ->setRequired(false)
                   ->setAllowEmpty(true);
        $this->addElement($dateFormat);

        // RASTATIME 2026-11-10 - show name as heading + font size (defaults
        // for every embed; ?title=0|1 and ?size=N override them per iframe)
        $showTitle = new Zend_Form_Element_Checkbox('widget_shows_show_title');
        $showTitle->setLabel(_('Show the show name as heading:'))
                  ->setRequired(false);
        $this->addElement($showTitle);

        $fontSize = new Zend_Form_Element_Text('widget_shows_font_size');
        $fontSize->setLabel(_('Font size (px):'))
                 ->setAttrib('class', 'input_text')
                 ->setAttrib('type', 'number')
                 ->setAttrib('min', Application_Model_Preference::WIDGET_SHOWS_FONT_SIZE_MIN)
                 ->setAttrib('max', Application_Model_Preference::WIDGET_SHOWS_FONT_SIZE_MAX)
                 ->setAttrib('step', 1)
                 ->setAttrib('placeholder', (string) Application_Model_Preference::WIDGET_SHOWS_FONT_SIZE_DEFAULT)
                 ->setAttrib('style', 'width: 6em;')
                 ->setRequired(false)
                 ->setAllowEmpty(true);
        $this->addElement($fontSize);

        // RASTATIME 2026-11-10 - text colour (#rrggbb; empty = the theme
        // colours); the view adds a colour picker and a clear button
        $textColor = new Zend_Form_Element_Text('widget_shows_text_color');
        $textColor->setLabel(_('Text color:'))
                  ->setAttrib('class', 'input_text')
                  ->setAttrib('maxlength', 7)
                  ->setAttrib('placeholder', _('theme'))
                  ->setAttrib('style', 'width: 6em;')
                  ->setRequired(false)
                  ->setAllowEmpty(true)
                  ->addFilter('StringTrim')
                  ->addValidator('Regex', false, [
                      'pattern'  => '/^#[0-9a-fA-F]{6}$/',
                      'messages' => _('Please enter a color as #rrggbb (e.g. #ff5d1a).'),
                  ]);
        $this->addElement($textColor);

        // RASTATIME 2026-11-10 - background colour (#rrggbb; empty =
        // transparent); the view adds a colour picker and a clear button
        $bgColor = new Zend_Form_Element_Text('widget_shows_bg_color');
        $bgColor->setLabel(_('Background color:'))
                ->setAttrib('class', 'input_text')
                ->setAttrib('maxlength', 7)
                ->setAttrib('placeholder', _('transparent'))
                ->setAttrib('style', 'width: 6em;')
                ->setRequired(false)
                ->setAllowEmpty(true)
                ->addFilter('StringTrim')
                ->addValidator('Regex', false, [
                    'pattern'  => '/^#[0-9a-fA-F]{6}$/',
                    'messages' => _('Please enter a color as #rrggbb (e.g. #ff5d1a).'),
                ]);
        $this->addElement($bgColor);

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
