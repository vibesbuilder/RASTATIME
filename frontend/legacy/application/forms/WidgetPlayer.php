<?php

/**
 * RASTATIME 2026-09-18 — Settings form for the Stream Player widget.
 * One checkbox: show cover artwork.  Persisted, so it also governs
 * embeds that carry no ?art= parameter (e.g. the station homepage's
 * bottom bar); an explicit ?art=on|off in an embed URL still wins.
 */
class Application_Form_WidgetPlayer extends Zend_Form
{
    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_player_form');

        $art = new Zend_Form_Element_Checkbox('widget_player_show_art');
        $art->setLabel(_('Show cover artwork:'))
            ->setRequired(false);
        $this->addElement($art);

        $submit = new Zend_Form_Element_Submit('submit');
        $submit->setLabel(_('Save'))
               ->setAttrib('class', 'btn');
        $this->addElement($submit);
    }
}
