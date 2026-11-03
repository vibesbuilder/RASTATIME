<?php

/**
 * RASTATIME 2026-11-03 - publishing stage 1: the "Publishing" section of
 * the show form (editorial team, participants, CBA defaults).  Stored by
 * Application_Service_PublishingService::saveShow() in cc_show_publishing /
 * cc_show_editor_profile (migration 0074), not in cc_show.
 */
class Application_Form_AddShowPublishing extends Zend_Form_SubForm
{
    public function init()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/add-show-publishing.phtml']],
        ]);

        $profiles = new Zend_Form_Element_MultiCheckbox('add_show_editor_profiles');
        $profiles->setLabel(_('Editorial team'))
            ->setMultiOptions(Application_Service_PublishingService::profileOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($profiles);

        $this->addElement('text', 'add_show_participants', [
            'label' => _('People involved'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('text', 'add_show_cba_series_id', [
            'label' => _('CBA podcast ID'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);

        $license = new Zend_Form_Element_Select('add_show_cba_license');
        $license->setLabel(_('Licence'))
            ->setMultiOptions(Application_Service_PublishingService::licenseOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($license);

        $this->addElement('text', 'add_show_cba_category_id', [
            'label' => _('CBA topic ID'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('text', 'add_show_cba_languages', [
            'label' => _('Languages'),
            'class' => 'input_text',
            'placeholder' => 'de, en',
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('text', 'add_show_cba_tags', [
            'label' => _('Tags'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('textarea', 'add_show_cba_teaser', [
            'label' => _('Default teaser'),
            'class' => 'input_text_area',
            'rows' => 3,
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('checkbox', 'add_show_cba_contains_copyright', [
            'label' => _('Contains copyrighted music (AKM)'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
    }

    /** Fill from the stored values of a show (and offer its inactive profiles too). */
    public function populateFromShow(int $showId)
    {
        $this->getElement('add_show_editor_profiles')
            ->setMultiOptions(Application_Service_PublishingService::profileOptions($showId));
        $s = Application_Service_PublishingService::showSettings($showId);
        $this->populate([
            'add_show_editor_profiles' => array_map(
                fn ($p) => (int) $p['id'],
                Application_Service_PublishingService::showProfiles($showId)
            ),
            'add_show_participants' => $s['participants'],
            'add_show_cba_series_id' => $s['cba_series_id'],
            'add_show_cba_license' => $s['license'],
            'add_show_cba_category_id' => $s['category_id'],
            'add_show_cba_languages' => str_replace(',', ', ', $s['languages']),
            'add_show_cba_tags' => $s['tags'],
            'add_show_cba_teaser' => $s['teaser'],
            'add_show_cba_contains_copyright' => $s['contains_copyright'] ? 1 : 0,
        ]);
    }

    /** Attach the messages of PublishingService::validateShowData(); false when there were any. */
    public function applyErrors(array $errors): bool
    {
        foreach ($errors as $field => $message) {
            $this->getElement($field)->addError($message);
        }

        return empty($errors);
    }

    public function disable()
    {
        foreach ($this->getElements() as $element) {
            if ($element->getType() != 'Zend_Form_Element_Hidden') {
                $element->setAttrib('disabled', 'disabled');
            }
        }
    }
}
