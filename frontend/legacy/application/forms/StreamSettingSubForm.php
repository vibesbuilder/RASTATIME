<?php

/**
 * RASTATIME — editable Icecast output stream sub-form.
 *
 * Each stream slot (s1–s3) renders a collapsible panel with all Icecast
 * connection parameters as proper form inputs.  Data is persisted to
 * cc_pref (not to the YAML config file) via Application_Model_Preference.
 */
class Application_Form_StreamSettingSubForm extends Zend_Form_SubForm
{
    private $prefix;
    private $setting;

    public static $customizable;

    public function init() {}

    public function setPrefix($prefix)
    {
        $this->prefix = $prefix;
    }

    public function setSetting($setting)
    {
        $this->setting = $setting;
    }

    public function startForm()
    {
        $prefix  = 's' . $this->prefix;   // e.g. "s1"
        $stream_number = $this->prefix;   // e.g. 1
        $setting = $this->setting;

        $this->setIsArray(true);
        $this->setElementsBelongTo($prefix . '_data');

        // -----------------------------------------------------------------
        // Enable / disable the whole stream
        // -----------------------------------------------------------------
        $enable = new Zend_Form_Element_Checkbox('enable');
        $enable
            ->setLabel(_('Enabled:'))
            ->setValue($setting[$prefix . '_enable'] === 'true' ? 1 : 0)
            ->setDecorators(['ViewHelper']);
        $this->addElement($enable);

        // -----------------------------------------------------------------
        // Service type — hidden, always icecast for RASTATIME
        // -----------------------------------------------------------------
        $output = new Zend_Form_Element_Hidden('output');
        $output
            ->setValue('icecast')
            ->setDecorators(['ViewHelper']);
        $this->addElement($output);

        // -----------------------------------------------------------------
        // Audio format (MP3 / OGG Vorbis / Opus / AAC)
        // -----------------------------------------------------------------
        $type = new Zend_Form_Element_Select('type');
        $type
            ->setLabel(_('Stream Type:'))
            ->setMultiOptions([
                'mp3'  => 'MP3',
                'ogg'  => 'Ogg Vorbis',
                'opus' => 'Opus',
                'aac'  => 'AAC',
            ])
            ->setValue($setting[$prefix . '_type'] ?? 'mp3')
            ->setDecorators(['ViewHelper']);
        $this->addElement($type);

        // -----------------------------------------------------------------
        // Bit rate
        // -----------------------------------------------------------------
        $bitrate = new Zend_Form_Element_Select('bitrate');
        $bitrate
            ->setLabel(_('Bit Rate:'))
            ->setMultiOptions([
                '32'  => '32 kbps',
                '48'  => '48 kbps',
                '64'  => '64 kbps',
                '96'  => '96 kbps',
                '128' => '128 kbps',
                '160' => '160 kbps',
                '192' => '192 kbps',
                '224' => '224 kbps',
                '256' => '256 kbps',
                '320' => '320 kbps',
            ])
            ->setValue((string)($setting[$prefix . '_bitrate'] ?? '128'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($bitrate);

        // -----------------------------------------------------------------
        // Channels
        // -----------------------------------------------------------------
        $channels = new Zend_Form_Element_Select('channels');
        $channels
            ->setLabel(_('Channels:'))
            ->setMultiOptions([
                'stereo' => _('Stereo'),
                'mono'   => _('Mono'),
            ])
            ->setValue($setting[$prefix . '_channels'] ?? 'stereo')
            ->setDecorators(['ViewHelper']);
        $this->addElement($channels);

        // -----------------------------------------------------------------
        // Sample rate (44.1 kHz CD quality vs 48 kHz broadcast / required by Opus)
        // -----------------------------------------------------------------
        $samplerate = new Zend_Form_Element_Select('samplerate');
        $samplerate
            ->setLabel(_('Sample Rate:'))
            ->setMultiOptions([
                '44100' => '44.1 kHz',
                '48000' => '48 kHz',
            ])
            ->setValue((string)($setting[$prefix . '_samplerate'] ?? '44100'))
            ->setDecorators(['ViewHelper']);
        $this->addElement($samplerate);

        // -----------------------------------------------------------------
        // Server / connection
        // -----------------------------------------------------------------
        $host = new Zend_Form_Element_Text('host');
        $host
            ->setLabel(_('Server'))
            ->setRequired(false)
            ->setValue($setting[$prefix . '_host'] ?? 'localhost')
            ->setDecorators(['ViewHelper']);
        $host->setAttrib('placeholder', 'localhost');
        $this->addElement($host);

        $port = new Zend_Form_Element_Text('port');
        $port
            ->setLabel(_('Port'))
            ->setRequired(false)
            ->setValue($setting[$prefix . '_port'] ?? '8000')
            ->setDecorators(['ViewHelper']);
        $port->setAttrib('placeholder', '8000');
        $this->addElement($port);

        $mount = new Zend_Form_Element_Text('mount');
        $mount
            ->setLabel(_('Mount Point'))
            ->setValue($setting[$prefix . '_mount'] ?? '')
            ->setDecorators(['ViewHelper']);
        $mount->setAttrib('placeholder', '/stream');
        $this->addElement($mount);

        // -----------------------------------------------------------------
        // Source credentials
        // -----------------------------------------------------------------
        $user = new Zend_Form_Element_Text('user');
        $user
            ->setLabel(_('Source Username'))
            ->setValue($setting[$prefix . '_user'] ?? 'source')
            ->setDecorators(['ViewHelper']);
        $user->setAttrib('placeholder', 'source');
        $this->addElement($user);

        $pass = new Zend_Form_Element_Password('pass');
        $pass
            ->setLabel(_('Source Password'))
            ->setValue($setting[$prefix . '_pass'] ?? '')
            ->setDecorators(['ViewHelper']);
        $pass->setAttrib('autocomplete', 'new-password');
        $pass->setAttrib('placeholder', '');
        $this->addElement($pass);

        // -----------------------------------------------------------------
        // Admin credentials (for listener stats)
        // -----------------------------------------------------------------
        $admin_user = new Zend_Form_Element_Text('admin_user');
        $admin_user
            ->setLabel(_('Admin Username'))
            ->setValue($setting[$prefix . '_admin_user'] ?? 'admin')
            ->setDecorators(['ViewHelper']);
        $admin_user->setAttrib('placeholder', 'admin');
        $this->addElement($admin_user);

        $admin_pass = new Zend_Form_Element_Password('admin_pass');
        $admin_pass
            ->setLabel(_('Admin Password'))
            ->setValue('')   // always empty; JS fills "xxxxxx" if set
            ->setDecorators(['ViewHelper']);
        $admin_pass->setAttrib('autocomplete', 'new-password');
        $this->addElement($admin_pass);

        // -----------------------------------------------------------------
        // Stream metadata
        // -----------------------------------------------------------------
        $name = new Zend_Form_Element_Text('name');
        $name
            ->setLabel(_('Name'))
            ->setValue($setting[$prefix . '_name'] ?? '')
            ->setDecorators(['ViewHelper']);
        $this->addElement($name);

        $genre = new Zend_Form_Element_Text('genre');
        $genre
            ->setLabel(_('Genre'))
            ->setValue($setting[$prefix . '_genre'] ?? '')
            ->setDecorators(['ViewHelper']);
        $this->addElement($genre);

        $url = new Zend_Form_Element_Text('url');
        $url
            ->setLabel(_('Website URL'))
            ->setValue($setting[$prefix . '_url'] ?? '')
            ->setDecorators(['ViewHelper']);
        $this->addElement($url);

        $description = new Zend_Form_Element_Text('description');
        $description
            ->setLabel(_('Description'))
            ->setValue($setting[$prefix . '_description'] ?? '')
            ->setDecorators(['ViewHelper']);
        $this->addElement($description);

        // -----------------------------------------------------------------
        // Mobile stream flag
        // -----------------------------------------------------------------
        $mobile = new Zend_Form_Element_Checkbox('mobile');
        $mobile
            ->setLabel(_('Mobile:'))
            ->setValue($setting[$prefix . '_mobile'] === 'true' ? 1 : 0)
            ->setDecorators(['ViewHelper']);
        $this->addElement($mobile);

        // -----------------------------------------------------------------
        // Public stream URL (read-only, auto-generated)
        // -----------------------------------------------------------------
        $public_url = new Zend_Form_Element_Text('public_url');
        $public_url
            ->setLabel(_('Stream URL'))
            ->setAttrib('readonly', true)
            ->setValue($setting[$prefix . '_public_url'] ?? '');
        $this->addElement($public_url);

        // -----------------------------------------------------------------
        // Decorate with the stream-setting-form view script
        // -----------------------------------------------------------------
        $liquidsoap_error_msg = '<div class="stream-status status-info"><p>'
            . _('Getting information from the server...')
            . '</p></div>';

        $this->setDecorators([
            ['ViewScript', [
                'viewScript'          => 'form/stream-setting-form.phtml',
                'stream_number'       => $stream_number,
                'enabled'             => $enable->getValue(),
                'liquidsoap_error_msg'=> $liquidsoap_error_msg,
            ]],
        ]);
    }
}
