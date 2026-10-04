<?php

define('MAX_NUM_STREAMS', 4);

class Application_Model_StreamConfig
{
    private static function toOutputKey($id)
    {
        return 's' . $id;
    }

    private static function toOutputId($key)
    {
        return intval(trim($key, 's'));
    }

    public static function getOutput($key, $add_prefix = false)
    {
        $id     = self::toOutputId($key);
        $prefix = $add_prefix ? "s{$id}_" : '';

        // RASTATIME: read from cc_pref (user-editable).
        // YAML config is ignored for output streams; settings are stored in the DB.
        $pref = Application_Model_Preference::GetStreamOutput($id);

        $enabled = ($pref['enable'] ?? 'false');
        // Normalise: may be boolean true/false or string 'true'/'false' or '1'/'0'
        $enabledStr = ($enabled === true || $enabled === 'true' || $enabled === '1') ? 'true' : 'false';

        $result = [
            $prefix . 'enable'      => $enabledStr,
            $prefix . 'output'      => 'icecast',
            $prefix . 'host'        => $pref['host']        ?? 'localhost',
            $prefix . 'port'        => $pref['port']        ?? 8000,
            $prefix . 'mount'       => $pref['mount']       ?? '',
            $prefix . 'user'        => $pref['user']        ?? 'source',
            $prefix . 'pass'        => $pref['pass']        ?? '',
            $prefix . 'admin_user'  => $pref['admin_user']  ?? 'admin',
            $prefix . 'admin_pass'  => $pref['admin_pass']  ?? '',
            $prefix . 'channels'    => $pref['channels']    ?? 'stereo',
            $prefix . 'bitrate'     => $pref['bitrate']     ?? 128,
            $prefix . 'samplerate'  => $pref['samplerate']  ?? 44100,
            $prefix . 'type'        => $pref['type']        ?? 'mp3',
            $prefix . 'name'        => $pref['name']        ?? '',
            $prefix . 'description' => $pref['description'] ?? '',
            $prefix . 'genre'       => $pref['genre']       ?? '',
            $prefix . 'url'         => $pref['url']         ?? '',
            $prefix . 'mobile'      => ($pref['mobile'] ?? 'false') === 'true' ? 'true' : 'false',
        ];

        // Listener-facing stream URL.  RASTATIME 2026-10-04 (go-live stage
        // 1): an output on the local Icecast is published as
        // <public_url>/stream/<mount> - Apache proxies /stream/ to Icecast
        // (infra/apache/rastatime-stream-proxy.conf), so the player, the
        // widgets and the embed codes work in the LAN and on the internet
        // with the same address and port 8000 stays internal.  An output
        // on a remote Icecast keeps its own host:port.
        $host  = $result[$prefix . 'host'];
        $port  = $result[$prefix . 'port'];
        $mount = ltrim($result[$prefix . 'mount'], '/');
        if (in_array(strtolower((string) $host), ['localhost', '127.0.0.1', '::1', ''], true)) {
            $result[$prefix . 'public_url'] = rtrim(Config::getPublicUrl(), '/') . '/stream/' . $mount;
        } else {
            $result[$prefix . 'public_url'] = "http://{$host}:{$port}/{$mount}";
        }

        return $result;
    }

    public static function getOutputEnabledKeys()
    {
        $keys = [];

        // RASTATIME: read enabled state from cc_pref, not from YAML.
        for ($i = 1; $i <= MAX_NUM_STREAMS; ++$i) {
            $pref    = Application_Model_Preference::GetStreamOutput($i);
            $enabled = $pref['enable'] ?? 'false';
            if ($enabled === true || $enabled === 'true' || $enabled === '1') {
                $keys[] = self::toOutputKey($i);
            }
        }

        return $keys;
    }
}

class Application_Model_StreamSetting
{
    public static function getEnabledStreamData()
    {
        $streams = [];
        $streamIds = self::getEnabledStreamIds();
        foreach ($streamIds as $id) {
            $streamData = self::getStreamData($id);
            $prefix = $id . '_';
            $streams[$id] = [
                'url' => $streamData[$prefix . 'public_url'],
                'codec' => $streamData[$prefix . 'type'],
                'bitrate' => $streamData[$prefix . 'bitrate'],
                'mobile' => $streamData[$prefix . 'mobile'],
            ];
        }

        return $streams;
    }

    /* Returns the id's of all streams that are enabled in an array. An
     * example of the array returned in JSON notation is ["s1", "s2", "s3"] */
    public static function getEnabledStreamIds()
    {
        return Application_Model_StreamConfig::getOutputEnabledKeys();
    }

    /* Returns all information related to a specific stream. An example
     * of a stream id is 's1' or 's2'. */
    public static function getStreamData($p_streamId)
    {
        return Application_Model_StreamConfig::getOutput($p_streamId, true);
    }

    /* Similar to getStreamData, but removes all sX prefixes to
     * make data easier to iterate over */
    public static function getStreamDataNormalized($p_streamId)
    {
        return Application_Model_StreamConfig::getOutput($p_streamId, false);
    }

    public static function getStreamSetting()
    {
        $settings = [];
        $numStreams = MAX_NUM_STREAMS;
        for ($streamIdx = 1; $streamIdx <= $numStreams; ++$streamIdx) {
            $settings = array_merge($settings, self::getStreamData('s' . $streamIdx));
        }
        $settings['master_live_stream_port'] = self::getMasterLiveStreamPort();
        $settings['master_live_stream_mp'] = self::getMasterLiveStreamMountPoint();
        $settings['dj_live_stream_port'] = self::getDjLiveStreamPort();
        $settings['dj_live_stream_mp'] = self::getDjLiveStreamMountPoint();
        $settings['off_air_meta'] = Application_Model_Preference::getOffAirMeta();
        $settings['icecast_vorbis_metadata'] = self::getIcecastVorbisMetadata();
        $settings['output_sound_device'] = self::getOutputSoundDevice();
        $settings['output_sound_device_type'] = self::getOutputSoundDeviceType();

        return $settings;
    }

    public static function getStreamEnabled($stream_id)
    {
        return in_array('s' . $stream_id, self::getEnabledStreamIds());
    }

    /*
     * Only returns info that is needed for data collection
     * returns array('s1'=>array(keyname=>value))
     */
    public static function getStreamInfoForDataCollection()
    {
        $result = [];
        $stream_ids = self::getEnabledStreamIds();

        foreach ($stream_ids as $stream_id) {
            $stream = self::getStreamDataNormalized($stream_id);
            $keys = array_flip(['output', 'type', 'bitrate', 'host']);
            $result[$stream_id] = array_intersect_key($stream, $keys);
        }

        return $result;
    }

    public static function getMasterLiveStreamPort()
    {
        return Config::get('stream.inputs.main.port') ?? 8001;
    }

    public static function getMasterLiveStreamMountPoint()
    {
        return Config::get('stream.inputs.main.mount') ?? 'main';
    }

    public static function getMasterLiveStreamSecure()
    {
        return Config::get('stream.inputs.main.secure') ?? false;
    }

    public static function getDjLiveStreamPort()
    {
        return Config::get('stream.inputs.show.port') ?? 8002;
    }

    public static function getDjLiveStreamMountPoint()
    {
        return Config::get('stream.inputs.show.mount') ?? 'show';
    }

    public static function getDjLiveStreamSecure()
    {
        return Config::get('stream.inputs.show.secure') ?? false;
    }

    public static function getAdminUser($stream)
    {
        return self::getStreamDataNormalized($stream)['admin_user'];
    }

    public static function getAdminPass($stream)
    {
        return self::getStreamDataNormalized($stream)['admin_pass'];
    }

    public static function getIcecastVorbisMetadata()
    {
        foreach (Config::get('stream.outputs.merged') as $output) {
            if ($output['audio']['enable_metadata'] ?? false) {
                return true;
            }
        }

        return '';
    }

    public static function getOutputSoundDevice()
    {
        return Config::get('stream.outputs.system.0.enabled') ?? 'false';
    }

    public static function getOutputSoundDeviceType()
    {
        return Config::get('stream.outputs.system.0.kind') ?? '';
    }
}
