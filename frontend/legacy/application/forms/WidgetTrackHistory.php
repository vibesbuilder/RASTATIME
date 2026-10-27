<?php

/**
 * RASTATIME 2026-05-22 — Settings form for the Track History
 * public embed widget.
 *
 * Three persisted fields:
 *   - widget_no_track_history     : empty-state label
 *   - exclude_short_tracks         : bool toggle (default true)
 *   - min_seconds                  : threshold (default 60)
 *
 * The threshold input is only relevant when the toggle is on;
 * the settings view template shows / hides it client-side based
 * on the checkbox state, matching the Auto-Expiry pattern from
 * the podcast settings (operator-familiar UX).
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

        $excludeShort = new Zend_Form_Element_Checkbox('exclude_short_tracks');
        $excludeShort->setLabel(_('Exclude short tracks:'))
           ->setRequired(false);
        $this->addElement($excludeShort);

        $minSec = new Zend_Form_Element_Text('min_seconds');
        $minSec->setLabel(_('Exclude tracks shorter than (s):'))
           ->setAttrib('class', 'input_text')
           ->setAttrib('type', 'number')
           ->setAttrib('min', 1)
           ->setAttrib('max', 3600)
           ->setAttrib('step', 1)
           ->setAttrib('style', 'width: 6em;')
           ->setRequired(false)
           ->setAllowEmpty(true);
        $this->addElement($minSec);

        // RASTATIME 2026-05-22 v17 — display label for Line-Input
        // sessions (master_dj / live_dj source switches).  Applied
        // when the Dashboard source-switch toggles ON, written
        // into cc_playout_history's metadata table.  Both Track
        // History widget AND the Analytics Playout History
        // dashboard read it.
        $lineInLabel = new Zend_Form_Element_Text('line_input_label');
        $lineInLabel->setLabel(_('Line-Input label:'))
           ->setAttrib('class', 'input_text widget-label-input')
           ->setAttrib('maxlength', 80)
           ->setAttrib('placeholder', 'Line Input')
           ->setAttrib('style', 'width: 18em;')
           ->setAttrib('title', _('Display label written into cc_playout_history '
                . 'when a master_dj or live_dj source switch turns ON.  '
                . 'Appears as the track title in both the Track History '
                . 'widget and the Analytics Playout History dashboard.'))
           ->setRequired(false)
           ->setAllowEmpty(true);
        $this->addElement($lineInLabel);

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
