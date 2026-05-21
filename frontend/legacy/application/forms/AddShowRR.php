<?php

class Application_Form_AddShowRR extends Zend_Form_SubForm
{
    public function init()
    {
        // RASTATIME 2026-05-17 - Label renamed from "Record from Line In?"
        // to "Record this show" because RASTATIME's Phase B Record-per-Show
        // feature (ARCHITECTURE Section 23.13) records the full on-air
        // output (whichever source happens to be playing at any moment
        // during the show: file track, web stream, line-in, master/show)
        // by tapping the first configured Icecast output mountpoint with
        // `-c copy`.  The Line-In-only semantics of the upstream label
        // no longer apply.
        // Decorators are set to ``ViewHelper`` only so we can lay out
        // the checkbox manually in the parent view-script (Record
        // section in add-show-form.phtml) the same way Autoloading
        // Playlist's add_show_has_autoplaylist checkbox is laid out —
        // a <dt>label</dt><dd>checkbox + help-icon</dd> pair inside a
        // <fieldset><dl>.  Without this override Zend prepends its
        // default label / errors wrappers and the checkbox no longer
        // lines up with the help-icon span.
        // RASTATIME 2026-05-19 — added trailing colon for visual
        // consistency with the other labels in the show form
        // ("Name:", "Description:", "Default Length:", etc.).
        $this->addElement('checkbox', 'add_show_record', [
            'label' => _('Record this show:'),
            'required' => false,
            'decorators' => ['ViewHelper'],
        ]);

        // Add record element
        $this->addElement('checkbox', 'add_show_rebroadcast', [
            'label' => _('Rebroadcast?'),
            'required' => false,
        ]);
    }

    public function disable()
    {
        $elements = $this->getElements();
        foreach ($elements as $element) {
            if ($element->getType() != 'Zend_Form_Element_Hidden') {
                $element->setAttrib('disabled', 'disabled');
            }
        }
    }
}
