<?php

/**
 * RASTATIME 2026-10-08 - failed podcast downloads as a preflight warning.
 *
 * Operator request: a failed automatic (or manual) episode download used to
 * leave nothing but a line in legacy.log.  Now every failure is kept in
 * cc_pref (key podcast_download_failures, JSON keyed by the episode guid:
 * podcast, episode title, attempts, last attempt, error) and published as
 * preflight warnings of type "podcast_download_failed" through the API's
 * per-type replace endpoint - the same table the dashboard banner and
 * System Status read.  A later successful download of the episode, or the
 * removal of the podcast, clears the entry and republishes.
 */
class Application_Model_PodcastDownloadFailures
{
    const PREF_KEY = 'podcast_download_failures';
    const WARNING_TYPE = 'podcast_download_failed';
    const REPLACE_URL = 'http://127.0.0.1:8765/api/v2/preflight/warnings/replace';

    /** @return array<string, array> guid => failure */
    public static function all()
    {
        $raw = (string) Application_Model_Preference::GetPodcastDownloadFailures();
        $list = $raw === '' ? [] : json_decode($raw, true);

        return is_array($list) ? $list : [];
    }

    private static function store(array $list)
    {
        Application_Model_Preference::SetPodcastDownloadFailures(json_encode($list));
    }

    /**
     * Records one failed attempt for the episode and republishes.
     *
     * @param int    $podcastId
     * @param string $podcastTitle
     * @param string $guid         the feed's episode guid (stable across placeholders)
     * @param string $episodeTitle
     * @param string $error        short reason (HTTP code / cURL message)
     */
    public static function record($podcastId, $podcastTitle, $guid, $episodeTitle, $error)
    {
        $guid = (string) $guid;
        if ($guid === '') {
            $guid = 'untitled:' . md5((string) $episodeTitle);
        }
        $list = self::all();
        $entry = $list[$guid] ?? ['attempts' => 0];
        $entry['podcast_id'] = (int) $podcastId;
        $entry['podcast'] = mb_substr((string) $podcastTitle, 0, 120);
        $entry['episode'] = mb_substr((string) $episodeTitle, 0, 160);
        $entry['attempts'] = (int) $entry['attempts'] + 1;
        $entry['last_attempt'] = gmdate('c');
        $entry['error'] = mb_substr(trim((string) $error), 0, 200);
        $list[$guid] = $entry;
        self::store($list);
        self::publish($list);
    }

    /** The episode downloaded after all: forget it and republish. */
    public static function clear($guid)
    {
        $list = self::all();
        if (isset($list[(string) $guid])) {
            unset($list[(string) $guid]);
            self::store($list);
            self::publish($list);
        }
    }

    /** The podcast is gone: forget its failures and republish. */
    public static function clearPodcast($podcastId)
    {
        $list = self::all();
        $kept = array_filter($list, function ($e) use ($podcastId) {
            return (int) ($e['podcast_id'] ?? 0) !== (int) $podcastId;
        });
        if (count($kept) !== count($list)) {
            self::store($kept);
            self::publish($kept);
        }
    }

    /**
     * Replaces the "podcast_download_failed" warnings with the current list.
     *
     * @return bool whether the API accepted the batch
     */
    public static function publish($list = null)
    {
        $list = $list === null ? self::all() : $list;
        $warnings = [];
        foreach ($list as $guid => $e) {
            $warnings[] = [
                'severity' => 'warning',
                'detail' => [
                    'podcast_id' => (int) ($e['podcast_id'] ?? 0),
                    'podcast' => (string) ($e['podcast'] ?? ''),
                    'episode' => (string) ($e['episode'] ?? ''),
                    'guid' => (string) $guid,
                    'attempts' => (int) ($e['attempts'] ?? 0),
                    'last_attempt' => (string) ($e['last_attempt'] ?? ''),
                    'error' => (string) ($e['error'] ?? ''),
                ],
            ];
        }
        $body = json_encode([
            'warning_type' => self::WARNING_TYPE,
            'scan_run_id' => 'legacy-' . gmdate('Ymd\THis') . '-' . substr(md5(uniqid('', true)), 0, 8),
            'warnings' => $warnings,
        ]);
        $ctx = stream_context_create(['http' => [
            'method' => 'POST',
            'timeout' => 3.0,
            'ignore_errors' => true,
            'header' => "Content-Type: application/json\r\n",
            'content' => $body,
        ]]);
        $resp = @file_get_contents(self::REPLACE_URL, false, $ctx);
        $ok = $resp !== false && is_array($data = json_decode($resp, true)) && isset($data['inserted']);
        if (!$ok) {
            Logging::warn('podcast_download: could not publish the preflight warnings (' . count($warnings) . ' failure(s)): '
                . ($resp === false ? 'API unreachable' : $resp));
        }

        return $ok;
    }
}
