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

        // RASTATIME 2026-10-01 - the default cover: shown when neither the
        // track nor the show has a picture (scaled to 256 px on upload).
        $cover = new Zend_Form_Element_File('widget_default_cover');
        $cover->setLabel(_('Default cover:'))
            ->setRequired(false)
            ->addValidator('Count', false, 1)
            ->addValidator('Extension', false, 'png,jpg,jpeg,gif,webp')
            ->setMaxFileSize(4000000);
        $cover->setAttrib('accept', 'image/png,image/jpeg,image/gif,image/webp');
        $this->addElement($cover);

        $remove = new Zend_Form_Element_Checkbox('widget_default_cover_remove');
        $remove->setLabel(_('Remove the default cover'))
            ->setRequired(false);
        $this->addElement($remove);

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
