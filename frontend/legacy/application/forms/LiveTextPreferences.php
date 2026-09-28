<?php

/**
 * RASTATIME 2026-09-28 - Live Text Info (Settings -> General, above TuneIn).
 *
 * The "now playing" line as a text file: written by the playout at every
 * change into the public web folder (/live/now-playing.txt), optionally
 * into a local file and onto an FTP / FTPS / SFTP server.  The line is
 * built by Liquidsoap with the format chosen here (same options and
 * fallbacks as the Stream Label, but independent of it).
 */
class Application_Form_LiveTextPreferences extends Zend_Form_SubForm
{
    public function init()
    {
        $this->setDecorators([
            ['ViewScript', ['viewScript' => 'form/preferences_livetext.phtml']],
        ]);

        $enable = new Zend_Form_Element_Checkbox('enable_live_text');
        $enable->setDecorators(['ViewHelper', 'Errors', 'Label']);
        $enable->addDecorator('Label', ['class' => 'enable-live-text']);
        $enable->setLabel(_('Write the "now playing" line to a text file (Live Text Info)?'));
        $enable->setValue(Application_Model_Preference::getLiveTextEnabled());
        $this->addElement($enable);

        $format = new Zend_Form_Element_Radio('live_text_format');
        $format->setLabel(_('Live Text Format:'))
            ->setMultiOptions([
                _('Artist - Title'),
                _('Show - Artist - Title'),
                _('Station name - Show name'),
            ])
            ->setValue(Application_Model_Preference::getLiveTextFormat())
            ->setDecorators(['ViewHelper']);
        $this->addElement($format);

        $web = new Zend_Form_Element_Checkbox('live_text_web_enabled');
        $web->setDecorators(['ViewHelper', 'Errors', 'Label']);
        $web->addDecorator('Label', ['class' => 'enable-live-text-web']);
        $web->setLabel(_('Publish on the web at /live/now-playing.txt'));
        $web->setValue(Application_Model_Preference::getLiveTextWebEnabled());
        $this->addElement($web);

        $filePath = new Zend_Form_Element_Text('live_text_file_path');
        $filePath->setLabel(_('Also write to file (optional):'))
            ->setDescription(_('Absolute path on this machine or a network share, e.g. D:\\share\\now-playing.txt. Empty = no extra file.'))
            ->setFilters(['StringTrim'])
            ->setValue(Application_Model_Preference::getLiveTextFilePath())
            ->setAttrib('class', 'input_text');
        $this->addElement($filePath);

        $ftp = Application_Model_Preference::getLiveTextFtpConfig();

        $ftpEnabled = new Zend_Form_Element_Checkbox('live_text_ftp_enabled');
        $ftpEnabled->setDecorators(['ViewHelper', 'Errors', 'Label']);
        $ftpEnabled->addDecorator('Label', ['class' => 'enable-live-text-ftp']);
        $ftpEnabled->setLabel(_('Push the file to an FTP server on every change'));
        $ftpEnabled->setValue($ftp['enabled'] ? 1 : 0);
        $this->addElement($ftpEnabled);

        $protocol = new Zend_Form_Element_Select('live_text_ftp_protocol');
        $protocol->setLabel(_('Protocol:'))
            ->setMultiOptions(['ftp' => 'FTP', 'ftps' => 'FTPS (explicit TLS)', 'sftp' => 'SFTP'])
            ->setValue($ftp['protocol']);
        $this->addElement($protocol);

        $host = new Zend_Form_Element_Text('live_text_ftp_host');
        $host->setLabel(_('Host:'))->setFilters(['StringTrim'])->setValue($ftp['host'])->setAttrib('class', 'input_text');
        $this->addElement($host);

        $port = new Zend_Form_Element_Text('live_text_ftp_port');
        $port->setLabel(_('Port:'))
            ->setDescription(_('Empty = the protocol default (21 / 22).'))
            ->setFilters(['StringTrim'])
            ->addValidator('regex', false, ['/^\d*$/', 'messages' => _('Please enter a port number.')])
            ->setValue($ftp['port'])
            ->setAttrib('class', 'input_text');
        $this->addElement($port);

        $user = new Zend_Form_Element_Text('live_text_ftp_username');
        $user->setLabel(_('Username:'))->setFilters(['StringTrim'])->setValue($ftp['username'])
            ->setAttrib('class', 'input_text')->setAttrib('autocomplete', 'off');
        $this->addElement($user);

        $password = new Zend_Form_Element_Password('live_text_ftp_password');
        $password->setLabel(_('Password:'))
            ->setDescription(_('Leave empty to keep the stored password.'))
            ->setAttrib('class', 'input_text')->setAttrib('autocomplete', 'new-password');
        $this->addElement($password);

        $path = new Zend_Form_Element_Text('live_text_ftp_path');
        $path->setLabel(_('Remote path:'))
            ->setDescription(_('Target file on the server, e.g. /web/now-playing.txt. A path ending in / gets the file name now-playing.txt.'))
            ->setFilters(['StringTrim'])
            ->setValue($ftp['path'])
            ->setAttrib('class', 'input_text');
        $this->addElement($path);
    }
}
