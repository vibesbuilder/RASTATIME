<?php

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

class Application_Model_RabbitMq
{
    public static $doPush = false;

    /**
     * Sets a flag to push the schedule at the end of the request.
     */
    public static function PushSchedule()
    {
        self::$doPush = true;
    }

    /**
     * RASTATIME: notify the running RASTATIME-PLAYOUT that its
     * cached schedule is stale.  Replaces the legacy Pypo /
     * Liquidsoap RabbitMQ message that we don't use anymore.
     *
     * The endpoint is the playout's own HTTP listener on
     * 127.0.0.1:8770 (set up in source_switcher.start_listener).
     * It runs ``scheduler.refresh()`` immediately, so newly-edited
     * shows go on-air on the next track boundary instead of after
     * the next 120-second poll.
     *
     * Called once per request from RabbitMqPlugin::dispatchLoopShutdown
     * after any controller flagged PushSchedule().  Synchronous with a
     * tight timeout: a slow / dead playout adds at most ~2 s to a
     * show-save round-trip and never breaks the user-facing save.
     */
    public static function NotifyPlayoutScheduleChanged()
    {
        $url = 'http://127.0.0.1:8770/reload-schedule';
        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Length: 0\r\n",
                'content' => '',
                'timeout' => 2.0,
                'ignore_errors' => true,
            ],
        ]);

        // Suppress warnings — playout might be stopped or restarting.
        $body = @file_get_contents($url, false, $ctx);

        if ($body === false) {
            // RASTATIME 2026-10-22 - the warning stays in error_get_last()
            // despite the @, and Logging::loggingShutdownCallback() logged it
            // again as ERR at the end of every such request; the WARN below
            // is the one report.
            error_clear_last();
            Logging::warn(
                'NotifyPlayoutScheduleChanged: could not reach the playout '
                . 'listener at ' . $url . ' — scheduled changes will still '
                . 'be picked up on the next 120 s poll cycle.'
            );

            return;
        }

        // $http_response_header is auto-populated by file_get_contents
        if (isset($http_response_header[0])
            && !preg_match('#^HTTP/\S+\s+2\d\d#', $http_response_header[0])
        ) {
            Logging::warn(
                'NotifyPlayoutScheduleChanged: playout listener replied '
                . $http_response_header[0]
            );
        }
    }

    /**
     * RASTATIME: tell RASTATIME-PLAYOUT to force-disconnect a live DJ
     * source from Icecast.
     *
     * Replaces the legacy SendMessageToPypo('disconnect_source', …) call.
     * Used when the operator clicks "Cancel Show" or otherwise wants to
     * end a live slot immediately — the playout doesn't reliably detect
     * that on its own when the cancelled show has no scheduled tracks
     * (e.g. a live-DJ-only slot), so we push the kick explicitly.
     *
     * ``$sourcename`` accepts the legacy Airtime names ('master_dj' /
     * 'live_dj') as well as the RASTATIME names ('master' / 'show').
     * The Python side maps both.
     *
     * Synchronous with a tight timeout: if the playout is stopped or
     * restarting we add at most ~2 s and never break the user-facing
     * cancel.
     */
    public static function NotifyDisconnectSource($sourcename)
    {
        $url = 'http://127.0.0.1:8770/disconnect-source?source=' . urlencode($sourcename);
        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Length: 0\r\n",
                'content' => '',
                'timeout' => 2.0,
                'ignore_errors' => true,
            ],
        ]);

        $body = @file_get_contents($url, false, $ctx);

        if ($body === false) {
            error_clear_last();  // see NotifyPlayoutScheduleChanged()
            Logging::warn(
                'NotifyDisconnectSource: could not reach the playout '
                . 'listener at ' . $url . ' — the show DJ may remain '
                . 'connected until the source-timeout fires.'
            );

            return;
        }

        if (isset($http_response_header[0])
            && !preg_match('#^HTTP/\S+\s+2\d\d#', $http_response_header[0])
        ) {
            Logging::warn(
                'NotifyDisconnectSource: playout listener replied '
                . $http_response_header[0]
            );
        }
    }

    private static function sendMessage($exchange, $exchangeType, $autoDeleteExchange, $data, $queue = '')
    {
        $CC_CONFIG = Config::getConfig();

        $conn = new AMQPStreamConnection(
            $CC_CONFIG['rabbitmq']['host'],
            $CC_CONFIG['rabbitmq']['port'],
            $CC_CONFIG['rabbitmq']['user'],
            $CC_CONFIG['rabbitmq']['password'],
            $CC_CONFIG['rabbitmq']['vhost']
        );

        if (!isset($conn)) {
            throw new Exception('Cannot connect to RabbitMQ server');
        }

        $channel = $conn->channel();
        $channel->access_request(
            $CC_CONFIG['rabbitmq']['vhost'],
            false,
            false,
            true,
            true
        );

        // I'm pretty sure we DON'T want to autodelete ANY exchanges but I'm keeping the code
        // the way it is just so I don't accidentally break anything when I add the Analyzer code in. -- Albert, March 13, 2014
        $channel->exchange_declare($exchange, $exchangeType, false, true, $autoDeleteExchange);

        $msg = new AMQPMessage($data, ['content_type' => 'text/plain']);

        $channel->basic_publish($msg, $exchange);
        $channel->close();
        $conn->close();
    }

    public static function SendMessageToPypo($event_type, $md)
    {
        $md['event_type'] = $event_type;

        $exchange = 'playout';
        $data = json_encode($md, JSON_FORCE_OBJECT);
        self::sendMessage($exchange, 'fanout', true, $data);
    }

    public static function SendMessageToMediaMonitor($event_type, $md)
    {
        $md['event_type'] = $event_type;

        $exchange = 'airtime-analyzer';
        $data = json_encode($md);
        self::sendMessage($exchange, 'direct', true, $data);
    }

    public static function SendMessageToShowRecorder($event_type)
    {
        $exchange = 'playout';

        $now = new DateTime('@' . time()); // in UTC timezone
        $end_timestamp = new DateTime('@' . (time() + 3600 * 2)); // in UTC timezone

        $temp = [];
        $temp['event_type'] = $event_type;
        $temp['server_timezone'] = Application_Model_Preference::GetTimezone();
        if ($event_type == 'update_recorder_schedule') {
            $temp['shows'] = Application_Model_Show::getShows(
                $now,
                $end_timestamp,
                $onlyRecord = true
            );
        }
        $data = json_encode($temp);

        self::sendMessage($exchange, 'fanout', true, $data);
    }

    public static function SendMessageToAnalyzer(
        $tmpFilePath,
        $importedStorageDirectory,
        $originalFilename,
        $fileId,
        $fileTrackTypeId
    ) {
        $data['file_id'] = $fileId;
        $data['tmp_file_path'] = $tmpFilePath;
        $data['import_directory'] = $importedStorageDirectory;
        $data['original_filename'] = $originalFilename;

        $options = new stdClass();

        if ($fileTrackTypeId) {
            $fileTrackType = new Application_Model_Tracktype($fileTrackTypeId);
            $options->analyze_cue_points = $fileTrackType->getAnalyzeCuePoints();
        }

        // RASTATIME 2026-10-14 - lossless -> MP3 320 kbps (Settings -> Local
        // Machine, default on): the analyzer converts WAV / FLAC / ALAC / ...
        // before it files the track (decided by codec); lossy MP3, AAC, Vorbis
        // and Opus audio is never re-encoded.
        // Only the import message carries it - a loudness-only measurement
        // (SendLoudnessMeasurementToAnalyzer) never converts.
        $options->convert_lossless = (bool) Application_Model_Preference::getConvertLosslessToMp3();

        // RASTATIME 2026-11-09 - the visible track types: a Media Type tag
        // (ID3 TMED) naming one of them by code or name makes it the track's
        // type and decides the cue point analysis; the callback reports it as
        // track_type_code (CcFiles::updateFromArray checks it again).
        $options->track_types = Application_Model_Tracktype::analyzerTrackTypes();

        $data['options'] = $options;

        self::publishAnalyzerMessage($data);
    }

    /**
     * RASTATIME 2026-09-28 - EBU R128 stage 1: ask the analyzer to measure
     * an ALREADY IMPORTED file (options.loudness_only).  The analyzer reads
     * the file in place, moves nothing, and PUTs only the three loudness
     * columns back; a failed measurement reports nothing.
     */
    public static function SendLoudnessMeasurementToAnalyzer($fileId, $absolutePath)
    {
        $data = [];
        $data['file_id'] = $fileId;
        $data['tmp_file_path'] = $absolutePath;
        $data['import_directory'] = '';
        $data['original_filename'] = basename($absolutePath);
        $options = new stdClass();
        $options->loudness_only = true;
        $data['options'] = $options;

        self::publishAnalyzerMessage($data);
    }

    private static function publishAnalyzerMessage(array $data)
    {
        $config = Config::getConfig();

        $conn = new AMQPStreamConnection(
            $config['rabbitmq']['host'],
            $config['rabbitmq']['port'],
            $config['rabbitmq']['user'],
            $config['rabbitmq']['password'],
            $config['rabbitmq']['vhost']
        );

        $exchange = 'airtime-uploads';
        $exchangeType = 'topic';
        $autoDeleteExchange = false;

        $jsonData = json_encode($data);

        if (!isset($conn)) {
            throw new Exception('Cannot connect to RabbitMQ server');
        }

        $channel = $conn->channel();
        $channel->access_request(
            $config['rabbitmq']['vhost'],
            false,
            false,
            true,
            true
        );

        // I'm pretty sure we DON'T want to autodelete ANY exchanges but I'm keeping the code
        // the way it is just so I don't accidentally break anything when I add the Analyzer code in. -- Albert, March 13, 2014
        $channel->exchange_declare($exchange, $exchangeType, false, true, $autoDeleteExchange);

        $msg = new AMQPMessage($jsonData, ['content_type' => 'text/plain']);

        $channel->basic_publish($msg, $exchange);
        $channel->close();
        $conn->close();
    }
}
