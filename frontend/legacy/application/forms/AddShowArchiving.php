<?php

/**
 * RASTATIME 2026-11-03 - archiving stage 1: the "Archiving" section of
 * the show form (editorial team, participants, CBA defaults).  Stored by
 * Application_Service_ArchivingService::saveShow() in cc_show_archiving /
 * cc_show_editor_profile (migration 0074), not in cc_show.  Stage 2
 * (migration 0075): the CBA account the episodes are archived under, their
 * visibility, the topic as a list (when the worker has fetched it).
 * Stage 3 (migration 0076): "Archive automatically".
 */
class Application_Form_AddShowArchiving extends Zend_Form_SubForm
{
    /** "Y-m-d H:i" station time since when the show archives automatically, '' when off. */
    public $autoSinceLocal = '';

    public function init()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/add-show-archiving.phtml']],
        ]);

        // one team per show (operator 2026-11-03); the table still allows several
        $profiles = new Zend_Form_Element_Select('add_show_editor_profiles');
        $profiles->setLabel(_('Producer'))
            ->setMultiOptions([0 => _('- none -')] + Application_Service_ArchivingService::profileOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($profiles);

        $this->addElement('text', 'add_show_participants', [
            'label' => _('People involved'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
        $account = new Zend_Form_Element_Select('add_show_cba_account');
        $account->setLabel(_('CBA account'))
            ->setMultiOptions(Application_Service_ArchivingService::accountOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($account);

        $status = new Zend_Form_Element_Select('add_show_cba_status');
        $status->setLabel(_('Visibility on cba.media'))
            ->setMultiOptions(Application_Service_ArchivingService::statusOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($status);

        $this->addElement('text', 'add_show_cba_series_id', [
            'label' => _('CBA podcast ID'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);

        $license = new Zend_Form_Element_Select('add_show_cba_license');
        $license->setLabel(_('Licence'))
            ->setMultiOptions(Application_Service_ArchivingService::licenseOptions())
            ->setRegisterInArrayValidator(false)
            ->setDecorators(['ViewHelper']);
        $this->addElement($license);

        // the topic list once the worker has fetched it, the number before
        $topics = Application_Service_ArchivingService::categoryOptions();
        if ($topics) {
            $topic = new Zend_Form_Element_Select('add_show_cba_category_id');
            $topic->setLabel(_('CBA topic'))
                ->setMultiOptions(['' => _('(not set)')] + $topics)
                ->setRegisterInArrayValidator(false)
                ->setDecorators(['ViewHelper']);
            $this->addElement($topic);
        } else {
            $this->addElement('text', 'add_show_cba_category_id', [
                'label' => _('CBA topic ID'),
                'class' => 'input_text',
                'decorators' => ['ViewHelper'],
            ]);
        }
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
            'label' => _('Contains copyrighted music'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
        $this->addElement('checkbox', 'add_show_cba_auto', [
            'label' => _('Archive automatically'),
            'class' => 'input_text',
            'decorators' => ['ViewHelper'],
        ]);
    }

    /** Fill from the stored values of a show (and offer its inactive profiles too). */
    public function populateFromShow(int $showId)
    {
        $this->getElement('add_show_editor_profiles')
            ->setMultiOptions([0 => _('- none -')] + Application_Service_ArchivingService::profileOptions($showId));
        $s = Application_Service_ArchivingService::showSettings($showId);
        $teams = Application_Service_ArchivingService::showProfiles($showId);
        $this->populate([
            'add_show_editor_profiles' => $teams ? (int) $teams[0]['id'] : 0,
            'add_show_participants' => $s['participants'],
            'add_show_cba_series_id' => $s['cba_series_id'],
            'add_show_cba_license' => $s['license'],
            'add_show_cba_category_id' => $s['category_id'],
            'add_show_cba_languages' => str_replace(',', ', ', $s['languages']),
            'add_show_cba_tags' => $s['tags'],
            'add_show_cba_teaser' => $s['teaser'],
            'add_show_cba_contains_copyright' => $s['contains_copyright'] ? 1 : 0,
            'add_show_cba_account' => (int) $s['cba_account_id'],
            'add_show_cba_status' => $s['cba_status'],
            'add_show_cba_auto' => $s['auto_archive'] ? 1 : 0,
        ]);
        $this->autoSinceLocal = $s['auto_archive'] && $s['auto_since'] !== null
            ? Application_Service_ArchivingService::utcToLocal($s['auto_since'])
            : '';
    }

    /** Attach the messages of ArchivingService::validateShowData(); false when there were any. */
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
