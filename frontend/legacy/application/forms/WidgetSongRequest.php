<?php

/**
 * RASTATIME 2026-11-14 - own listener texts of the song request widget
 * (Widgets -> Song Request).  One text field per widget text, named
 * sr_<key> after Application_Service_SongRequestTexts; an empty field keeps
 * the standard text, which the placeholder shows in the station language.
 */
class Application_Form_WidgetSongRequest extends Zend_Form
{
    /** @param array<string, string> $defaults standard texts, shown as placeholders */
    public function __construct(array $defaults = [], $options = null)
    {
        $this->defaults = $defaults;
        parent::__construct($options);
    }

    /** @var array<string, string> */
    private $defaults = [];

    public function init()
    {
        $this->setMethod('post');
        $this->setAttrib('id', 'widget_song_request_form');

        $fields = [
            'search' => [_('Search box:'), _('{total} becomes the number of tracks listeners can request.')],
            'loading' => [_('While loading:'), ''],
            'no_tracks' => [_('No tracks in the pool:'), ''],
            'no_matches' => [_('No search matches:'), ''],
            'more' => [
                _('Note under the list:'),
                _('Shown when the pool holds more tracks than the list (500).  {shown} becomes the number of tracks listed, {total} the number in the pool.'),
            ],
            'refine' => [
                _('Note on many matches:'),
                _('Shown when a search reaches its limit (50 matches).  {shown} becomes the number of matches listed.'),
            ],
            'request' => [_('Request button:'), ''],
            'success' => [_('Request received:'), ''],
            'duplicate' => [_('Already requested:'), _('The same address asked for the same track within the last 30 minutes.')],
            'ratelimit' => [_('Request limit reached:'), _('More than 5 requests an hour from one address (or more than 60 searches a minute).')],
            'error' => [_('Error:'), ''],
            'unavailable' => [_('Requests unavailable:'), _('Shown instead of the list while no song request pool is set.')],
        ];

        foreach ($fields as $key => [$label, $help]) {
            $max = $key === 'request'
                ? Application_Service_SongRequestTexts::BUTTON_MAX
                : Application_Service_SongRequestTexts::TEXT_MAX;
            $el = new Zend_Form_Element_Text('sr_' . $key);
            $el->setLabel($label)
               ->setAttrib('class', 'input_text widget-label-input')
               ->setAttrib('maxlength', $max)
               ->setAttrib('placeholder', $this->defaults[$key] ?? '')
               ->setAttrib('style', $key === 'request' ? 'width: 12em;' : 'width: 100%; max-width: 34em;')
               ->setRequired(false)
               ->setAllowEmpty(true)
               ->addValidator('StringLength', false, ['max' => $max, 'encoding' => 'UTF-8']);
            if ($help !== '') {
                $el->setDescription($help);
            }
            $this->addElement($el);
        }

        $submit = new Zend_Form_Element_Submit('submit');
        $submit->setLabel(_('Save'))
               ->setAttrib('class', 'btn');
        $this->addElement($submit);

        // a plain form post: the session token travels as the hidden field 'csrf' (role audit R12)
        $csrf = new Zend_Form_Element_Hidden('csrf');
        $csrf->setValue((new Zend_Session_Namespace('csrf_namespace'))->authtoken)
             ->setDecorators(['ViewHelper']);
        $this->addElement($csrf);
    }

    /** @return array<string, string> key => text as typed */
    public function getTexts(): array
    {
        $out = [];
        foreach (array_keys($this->defaults ?: Application_Service_SongRequestTexts::defaults()) as $key) {
            $out[$key] = (string) $this->getValue('sr_' . $key);
        }

        return $out;
    }
}
