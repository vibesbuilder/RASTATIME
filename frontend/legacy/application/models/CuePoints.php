<?php

/**
 * RASTATIME 2026-09-30 - cue points of a file: detection from the audio,
 * validation against the file length, and propagation into the rows of
 * the upcoming shows.
 *
 * Why: since the crossfade per track type lays jingles out with no
 * overlap, every silent tail is heard as a pause.  The analyzer detects
 * cue points only at import (ffmpeg silencedetect), the track editor
 * accepted any cue-out (6.90 s on a 5.97 s file), and the schedule keeps
 * its own copy of the cue points from the moment a row was inserted -
 * a cue change used to need every show refilled by hand.
 */
class Application_Model_CuePoints
{
    /** Same parameters as the analyzer (analyzer/pipeline/_ffmpeg.py). */
    public const SILENCE_NOISE_DB = -60;
    public const SILENCE_MIN_SECONDS = 0.3;

    /** Files longer than this are skipped by the library action (a full
     *  decode of an hour-long show takes ~10 s; the action is for jingles). */
    public const DETECT_MAX_SECONDS = 900;

    /**
     * The ffmpeg binary: FFMPEG_PATH (the analyzer's variable), else the
     * Windows install location, else whatever is on the PATH.
     */
    public static function ffmpegBinary()
    {
        $env = getenv('FFMPEG_PATH');
        if ($env && is_file($env)) {
            return $env;
        }
        foreach (['C:/ffmpeg/bin/ffmpeg.exe', '/usr/bin/ffmpeg'] as $candidate) {
            if (is_file($candidate)) {
                return $candidate;
            }
        }

        return 'ffmpeg';
    }

    /**
     * Seconds as the cc_files interval columns store them.
     */
    public static function formatSeconds($seconds)
    {
        $seconds = max(0.0, (float) $seconds);
        $hours = floor($seconds / 3600);
        $seconds -= $hours * 3600;
        $minutes = floor($seconds / 60);
        $seconds -= $minutes * 60;

        return sprintf('%02d:%02d:%09.6f', $hours, $minutes, $seconds);
    }

    /**
     * Cue in / cue out against the file length: cue in never below 0, cue
     * out never past the end, and at least a moment of audio between them
     * (otherwise the whole file).  Returns [cuein, cueout] in seconds.
     */
    public static function clamp($cueinSeconds, $cueoutSeconds, $lengthSeconds)
    {
        $length = max(0.0, (float) $lengthSeconds);
        $cuein = max(0.0, (float) $cueinSeconds);
        $cueout = (float) $cueoutSeconds;
        if ($length > 0 && $cueout > $length) {
            $cueout = $length;
        }
        if ($cueout <= 0 && $length > 0) {
            $cueout = $length;
        }
        if ($cuein >= $cueout - 0.05) {
            $cuein = 0.0;
            $cueout = $length > 0 ? $length : $cueout;
        }

        return [$cuein, $cueout];
    }

    /**
     * Detect the cue points of an audio file with ffmpeg's silencedetect
     * (the analyzer's parameters).  Cue in = end of a silence that starts
     * at the top, cue out = start of a silence that runs to the end.
     * Returns [cuein, cueout] in seconds, or null when ffmpeg is not
     * available or said nothing usable.
     *
     * @param string $absolutePath
     * @param float  $lengthSeconds the file length from cc_files
     */
    public static function detect($absolutePath, $lengthSeconds)
    {
        if (!is_file($absolutePath)) {
            return null;
        }
        $filter = sprintf(
            'highpass=frequency=80,silencedetect=noise=%ddB:duration=%s',
            self::SILENCE_NOISE_DB,
            rtrim(rtrim(number_format(self::SILENCE_MIN_SECONDS, 2, '.', ''), '0'), '.')
        );
        $cmd = escapeshellarg(self::ffmpegBinary())
            . ' -hide_banner -nostats -i ' . escapeshellarg($absolutePath)
            . ' -vn -filter ' . escapeshellarg($filter) . ' -f null ' . escapeshellarg(PHP_OS_FAMILY === 'Windows' ? 'NUL' : '/dev/null')
            . ' 2>&1';
        $output = [];
        $code = 0;
        @exec($cmd, $output, $code);
        if ($code !== 0) {
            Logging::warn('CuePoints::detect: ffmpeg exited ' . $code . ' for ' . $absolutePath);

            return null;
        }

        return self::cuesFromSilences(self::parseSilences(implode("\n", $output)), (float) $lengthSeconds);
    }

    /**
     * silencedetect lines -> list of [start, end]; a silence that runs to
     * the end of the file has no silence_end line and gets INF.
     */
    public static function parseSilences($ffmpegOutput)
    {
        $silences = [];
        $start = null;
        if (preg_match_all('/silence_(start|end): (-?\d+(?:\.\d+)?)/', $ffmpegOutput, $m, PREG_SET_ORDER)) {
            foreach ($m as $hit) {
                if ($hit[1] === 'start') {
                    $start = (float) $hit[2];
                } elseif ($start !== null) {
                    $silences[] = [$start, (float) $hit[2]];
                    $start = null;
                }
            }
        }
        if ($start !== null) {
            $silences[] = [$start, INF];
        }

        return $silences;
    }

    /**
     * The analyzer's rule: only a silence at the very top moves the cue in,
     * only a silence that reaches the end moves the cue out.
     */
    public static function cuesFromSilences(array $silences, $lengthSeconds)
    {
        $length = (float) $lengthSeconds;
        $cuein = 0.0;
        $cueout = $length;
        foreach ($silences as $silence) {
            [$s, $e] = $silence;
            if (abs(max(0.0, $s)) <= 0.1) {
                $cuein = max(0.0, min($e, $length));
            } elseif (abs(min($e, $length) - $length) <= 0.1) {
                $cueout = max(0.0, min($s, $length));
            }
        }

        return self::clamp($cuein, $cueout, $length);
    }

    /**
     * Copy the file's cue points into the rows of the upcoming shows that
     * schedule it (rows that have not started; the running row and the
     * past are left alone).  ``ends`` is NOT touched here - the caller
     * lays the instances out again (calculateCrossfades reads clip_length).
     *
     * @return int[] the ids of the instances that changed
     */
    public static function applyToFutureRows($fileId, $con = null)
    {
        $con = $con ?: Propel::getConnection(CcSchedulePeer::DATABASE_NAME);
        $stmt = $con->prepare(
            'UPDATE cc_schedule s SET cue_in = f.cuein, cue_out = f.cueout, clip_length = f.cueout - f.cuein'
            . ' FROM cc_files f, cc_show_instances i'
            . ' WHERE f.id = s.file_id AND i.id = s.instance_id AND s.file_id = :fid'
            . " AND s.starts > (now() at time zone 'utc') AND i.modified_instance = false"
            . ' AND (s.cue_in IS DISTINCT FROM f.cuein OR s.cue_out IS DISTINCT FROM f.cueout)'
            . ' RETURNING s.instance_id'
        );
        $stmt->bindValue(':fid', (int) $fileId, PDO::PARAM_INT);
        $stmt->execute();
        $instances = [];
        foreach ($stmt->fetchAll(PDO::FETCH_COLUMN, 0) as $id) {
            $instances[(int) $id] = (int) $id;
        }

        return array_values($instances);
    }

    /**
     * The same for a webstream's default length (2026-09-30, second half
     * of the day): the rows copy it at insertion, so a longer relay that
     * should fill a show did not reach the shows already built.  Rows
     * that have not started take the new length; the callers lay the
     * instances out again.
     *
     * @return int[] the ids of the instances that changed
     */
    public static function applyWebstreamLengthToFutureRows($streamId, $con = null)
    {
        $con = $con ?: Propel::getConnection(CcSchedulePeer::DATABASE_NAME);
        $stmt = $con->prepare(
            'UPDATE cc_schedule s SET clip_length = w.length, cue_out = w.length'
            . ' FROM cc_webstream w, cc_show_instances i'
            . ' WHERE w.id = s.stream_id AND i.id = s.instance_id AND s.stream_id = :sid'
            . " AND s.starts > (now() at time zone 'utc') AND i.modified_instance = false"
            . ' AND s.clip_length IS DISTINCT FROM w.length'
            . ' RETURNING s.instance_id'
        );
        $stmt->bindValue(':sid', (int) $streamId, PDO::PARAM_INT);
        $stmt->execute();
        $instances = [];
        foreach ($stmt->fetchAll(PDO::FETCH_COLUMN, 0) as $id) {
            $instances[(int) $id] = (int) $id;
        }

        return array_values($instances);
    }

    /**
     * Lay the given instances out again and tell the playout.
     */
    public static function relayoutInstances(array $instanceIds)
    {
        if (!$instanceIds) {
            return 0;
        }
        CcSchedulePeer::clearInstancePool();   // the rows were changed with raw SQL
        $scheduler = new Application_Model_Scheduler(false);
        $done = 0;
        foreach (array_unique($instanceIds) as $id) {
            try {
                $scheduler->calculateCrossfades((int) $id);
                ++$done;
            } catch (Exception $e) {
                Logging::warn('CuePoints::relayoutInstances: instance ' . $id . ': ' . $e->getMessage());
            }
        }
        if ($done) {
            Application_Model_RabbitMq::PushSchedule();
        }

        return $done;
    }
}
