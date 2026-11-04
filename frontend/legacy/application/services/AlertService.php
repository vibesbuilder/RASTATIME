<?php

/**
 * RASTATIME 2026-11-03 - Settings -> Alerts (alerts stage 1, operator go
 * 2026-11-03): the settings of the e-mail (SMTP) and Telegram alerts in
 * cc_pref (keys alerts_*), read by the playout and the API service
 * (rastatime_shared.alerts), and the test messages through the playout's
 * HTTP listener (/alert-test).  2026-11-04 (operator): one switch per
 * channel (alerts_mail_enabled / alerts_telegram_enabled) instead of the
 * master switch; alerts_enabled is still written as "any channel on" for
 * services that run the older code until their restart.
 */
class Application_Service_AlertService
{
    /** key => default (strings as stored); mirrors rastatime_shared.alerts.DEFAULTS */
    public const DEFAULTS = [
        'alerts_enabled' => 'false',
        // '' = not saved since 2026-11-04: load() derives it from alerts_enabled
        'alerts_mail_enabled' => '',
        'alerts_telegram_enabled' => '',
        'alerts_smtp_host' => '',
        'alerts_smtp_port' => '587',
        'alerts_smtp_security' => 'starttls',
        'alerts_smtp_user' => '',
        'alerts_smtp_password' => '',
        'alerts_mail_from' => '',
        'alerts_mail_to' => '',
        'alerts_telegram_token' => '',
        'alerts_telegram_chats' => '',
        'alerts_dead_air_seconds' => '30',
        'alerts_repeat_minutes' => '30',
        'alerts_services' => 'true',
        'alerts_preflight' => 'true',
    ];

    /** keys that are never shown again once stored (write-only) */
    public const SECRETS = ['alerts_smtp_password', 'alerts_telegram_token'];

    public const PLAYOUT_TEST_URL = 'http://127.0.0.1:8770/alert-test';

    /** The settings for the form: secrets replaced by a "stored" flag. */
    public static function load(): array
    {
        $out = [];
        foreach (self::DEFAULTS as $key => $default) {
            $v = Application_Model_Preference::getAlertSetting($key);
            $out[$key] = ($v === null || $v === '') ? $default : (string) $v;
        }
        // before the per-channel switches: on = master switch on and the channel set up
        $master = in_array($out['alerts_enabled'], ['true', '1', 't'], true);
        if ($out['alerts_mail_enabled'] === '') {
            $out['alerts_mail_enabled'] = $master && $out['alerts_smtp_host'] !== '' && $out['alerts_mail_from'] !== ''
                && $out['alerts_mail_to'] !== '' ? 'true' : 'false';
        }
        if ($out['alerts_telegram_enabled'] === '') {
            $out['alerts_telegram_enabled'] = $master && $out['alerts_telegram_token'] !== ''
                && $out['alerts_telegram_chats'] !== '' ? 'true' : 'false';
        }
        foreach (self::SECRETS as $key) {
            $out[$key . '_stored'] = $out[$key] !== '';
            $out[$key] = '';
        }

        return $out;
    }

    /**
     * Validate and store the form.  Returns the error messages (field =>
     * text); nothing is written when there is one.  An empty secret keeps
     * the stored value.
     */
    public static function save(array $post): array
    {
        $errors = [];
        $v = [];
        $mailOn = !empty($post['alerts_mail_enabled']);
        $telegramOn = !empty($post['alerts_telegram_enabled']);
        $v['alerts_mail_enabled'] = $mailOn ? 'true' : 'false';
        $v['alerts_telegram_enabled'] = $telegramOn ? 'true' : 'false';
        $v['alerts_enabled'] = $mailOn || $telegramOn ? 'true' : 'false';
        $v['alerts_services'] = !empty($post['alerts_services']) ? 'true' : 'false';
        $v['alerts_preflight'] = !empty($post['alerts_preflight']) ? 'true' : 'false';
        $v['alerts_smtp_host'] = trim((string) ($post['alerts_smtp_host'] ?? ''));
        $port = trim((string) ($post['alerts_smtp_port'] ?? '587'));
        if ($port === '' || !ctype_digit($port) || (int) $port < 1 || (int) $port > 65535) {
            $errors['alerts_smtp_port'] = _('The SMTP port must be a number between 1 and 65535.');
        }
        $v['alerts_smtp_port'] = $port;
        $sec = strtolower(trim((string) ($post['alerts_smtp_security'] ?? 'starttls')));
        $v['alerts_smtp_security'] = in_array($sec, ['starttls', 'ssl', 'none'], true) ? $sec : 'starttls';
        $v['alerts_smtp_user'] = trim((string) ($post['alerts_smtp_user'] ?? ''));
        $v['alerts_mail_from'] = trim((string) ($post['alerts_mail_from'] ?? ''));
        if ($v['alerts_mail_from'] !== '' && !filter_var($v['alerts_mail_from'], FILTER_VALIDATE_EMAIL)) {
            $errors['alerts_mail_from'] = _('The sender must be an e-mail address.');
        }
        $to = self::splitList((string) ($post['alerts_mail_to'] ?? ''));
        foreach ($to as $addr) {
            if (!filter_var($addr, FILTER_VALIDATE_EMAIL)) {
                $errors['alerts_mail_to'] = sprintf(_('"%s" is not an e-mail address.'), $addr);
                break;
            }
        }
        $v['alerts_mail_to'] = implode(', ', $to);
        $chats = self::splitList((string) ($post['alerts_telegram_chats'] ?? ''));
        foreach ($chats as $chat) {
            if (!preg_match('/^-?\d{1,20}$/', $chat)) {
                $errors['alerts_telegram_chats'] = sprintf(_('"%s" is not a Telegram chat id (digits, a group id starts with -).'), $chat);
                break;
            }
        }
        $v['alerts_telegram_chats'] = implode(', ', $chats);
        $secs = trim((string) ($post['alerts_dead_air_seconds'] ?? '30'));
        if (!ctype_digit($secs) || (int) $secs < 5 || (int) $secs > 3600) {
            $errors['alerts_dead_air_seconds'] = _('Dead air: 5 to 3600 seconds.');
        }
        $v['alerts_dead_air_seconds'] = $secs;
        $rep = trim((string) ($post['alerts_repeat_minutes'] ?? '30'));
        if (!ctype_digit($rep) || (int) $rep > 1440) {
            $errors['alerts_repeat_minutes'] = _('Reminder: 0 (off) to 1440 minutes.');
        }
        $v['alerts_repeat_minutes'] = $rep;
        foreach (self::SECRETS as $key) {
            $val = (string) ($post[$key] ?? '');
            if ($val !== '') {
                if (mb_strlen($val) > 255) {
                    $errors[$key] = _('At most 255 characters.');
                }
                $v[$key] = trim($val);
            }
        }
        // a switched-on channel must be able to send
        if ($mailOn && ($v['alerts_smtp_host'] === '' || $v['alerts_mail_from'] === '' || $v['alerts_mail_to'] === '')) {
            $errors['alerts_mail_enabled'] = _('E-mail alerts need an SMTP server, a sender and at least one recipient.');
        }
        $tokenStored = (string) Application_Model_Preference::getAlertSetting('alerts_telegram_token') !== '';
        if ($telegramOn && (($v['alerts_telegram_token'] ?? '') === '' && !$tokenStored || $v['alerts_telegram_chats'] === '')) {
            $errors['alerts_telegram_enabled'] = _('Telegram alerts need a bot token and at least one chat id.');
        }
        if ($errors) {
            return $errors;
        }
        foreach ($v as $key => $val) {
            Application_Model_Preference::setAlertSetting($key, $val);
        }
        Logging::info('Alert settings saved (mail=' . $v['alerts_mail_enabled'] . ', telegram=' . $v['alerts_telegram_enabled']
            . ', smtp=' . ($v['alerts_smtp_host'] !== '' ? 'set' : 'empty')
            . ', telegram chats=' . ($v['alerts_telegram_chats'] !== '' ? 'set' : 'empty') . ')');

        return [];
    }

    /** "Send test" through the playout listener: [ok, error text]. */
    public static function test(string $channel): array
    {
        if (!in_array($channel, ['mail', 'telegram'], true)) {
            return [false, _('Unknown channel.')];
        }
        $ch = curl_init(self::PLAYOUT_TEST_URL . '?channel=' . $channel);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => '',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 40,
        ]);
        $body = curl_exec($ch);
        $code = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        if ($body === false) {
            return [false, sprintf(_('The playout service did not answer (%s). Is RASTATIME-PLAYOUT running?'), $err)];
        }
        $json = json_decode((string) $body, true);
        if (!is_array($json)) {
            return [false, sprintf(_('The playout service answered with HTTP %d.'), $code)];
        }
        if (!empty($json['ok'])) {
            return [true, ''];
        }

        return [false, (string) ($json['error'] ?? _('The test message could not be sent.'))];
    }

    private static function splitList(string $value): array
    {
        $parts = preg_split('/[,;\s]+/', $value) ?: [];

        return array_values(array_filter(array_map('trim', $parts), fn ($p) => $p !== ''));
    }
}
