<?php
/**
 * RASTATIME 2026-11-01 - re-detect the cue points of the whole library.
 *
 * Background: the analyzer never measured cue points on this machine
 * (ffmpeg's "Parsed_silencedetect" log prefix, fixed in 686ad377), so
 * 24,857 of 24,999 files carried cue_in 0 and cue_out = length.  This
 * script runs Application_Model_CuePoints (the Library button's model) over
 * the library from the command line.
 *
 * Usage (from the repo root, PowerShell):
 *   php frontend\legacy\scripts\cue_redetect_all.php --dry-run [--shard K/N] [--limit N] [--all]
 *       measure, write nothing; CSV report to logs\cue_redetect-<stamp>[-K].csv
 *   php frontend\legacy\scripts\cue_redetect_all.php --dry-run <csv> [<csv> ...]
 *       measure only the files those reports skipped (retry after a fix)
 *   php frontend\legacy\scripts\cue_redetect_all.php --apply [--skip-flagged] <csv> [<csv> ...]
 *       write the NEW values of the given reports (the reviewed numbers,
 *       no second measurement), propagate into the upcoming schedule rows,
 *       lay the touched instances out once; --skip-flagged leaves the rows
 *       with an outlier flag (cuein>10s, tail>30s, clip<1s) untouched
 *   php frontend\legacy\scripts\cue_redetect_all.php --restore <csv> [<csv> ...]
 *       write the OLD values back (rollback), same propagation
 *
 * Default selection: files that still carry the degenerate pair
 * (cue_in = 0 and cue_out = length); --all measures every existing file.
 * Files longer than DETECT_MAX_SECONDS are included (the button skips them).
 */

declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "command line only\n");
    exit(2);
}

$repoRoot = realpath(__DIR__ . '/../../..');
if (getenv('RASTATIME_CONFIG_FILEPATH') === false) {
    putenv('RASTATIME_CONFIG_FILEPATH=' . $repoRoot . '/config/rastatime.conf');
}
$_SERVER['HTTP_HOST'] = '127.0.0.1';
$_SERVER['SERVER_NAME'] = '127.0.0.1';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['PHP_SELF'] = '/index.php';
$_SERVER['SERVER_PROTOCOL'] = 'HTTP/1.1';

// ---------------------------------------------------------------- arguments
$opts = ['mode' => null, 'shard' => [0, 1], 'limit' => 0, 'all' => false, 'csv' => [], 'skip_flagged' => false];
$args = array_slice($argv, 1);
while ($args) {
    $a = array_shift($args);
    switch ($a) {
        case '--dry-run': $opts['mode'] = 'dry'; break;
        case '--apply': $opts['mode'] = 'apply'; break;
        case '--restore': $opts['mode'] = 'restore'; break;
        case '--all': $opts['all'] = true; break;
        case '--skip-flagged': $opts['skip_flagged'] = true; break;
        case '--limit': $opts['limit'] = (int) array_shift($args); break;
        case '--shard':
            if (!preg_match('/^(\d+)\/(\d+)$/', (string) array_shift($args), $m) || (int) $m[2] < 1 || (int) $m[1] >= (int) $m[2]) {
                fwrite(STDERR, "--shard expects K/N with 0 <= K < N\n");
                exit(2);
            }
            $opts['shard'] = [(int) $m[1], (int) $m[2]];
            break;
        default:
            if ($a !== '' && $a[0] === '-') {
                fwrite(STDERR, "unknown option $a\n");
                exit(2);
            }
            $opts['csv'][] = $a;
    }
}
if ($opts['mode'] === null) {
    fwrite(STDERR, "one of --dry-run, --apply <csv>, --restore <csv> is required\n");
    exit(2);
}
if ($opts['mode'] !== 'dry' && !$opts['csv']) {
    fwrite(STDERR, "--apply / --restore need at least one report csv\n");
    exit(2);
}

// ---------------------------------------------------------------- bootstrap
require $repoRoot . '/frontend/legacy/public/index.php';
if (isset($application)) {
    $application->bootstrap();
}
$con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);

function seconds(string $interval): float
{
    return (float) Application_Common_DateHelper::playlistTimeToSeconds($interval);
}

function outlier(float $length, float $in, float $out): string
{
    $flags = [];
    if ($in > 10.0) {
        $flags[] = 'cuein>10s';
    }
    if ($length - $out > 30.0) {
        $flags[] = 'tail>30s';
    }
    if ($out - $in < 1.0) {
        $flags[] = 'clip<1s';
    }
    return implode('+', $flags);
}

// ---------------------------------------------------------------- dry run
if ($opts['mode'] === 'dry') {
    [$k, $n] = $opts['shard'];
    $where = 'file_exists = true AND import_status = 0';
    if (!$opts['all']) {
        $where .= " AND cuein = '00:00:00' AND cueout = length";
    }
    if ($n > 1) {
        $where .= " AND (id % $n) = $k";
    }
    $sql = "SELECT id FROM cc_files WHERE $where ORDER BY id";
    if ($opts['limit'] > 0) {
        $sql .= ' LIMIT ' . $opts['limit'];
    }
    if ($opts['csv']) {
        // --dry-run <csv> ...: measure only the rows those reports skipped
        $ids = [];
        foreach ($opts['csv'] as $path) {
            $fh = fopen($path, 'r');
            $header = fgetcsv($fh);
            while (($r = fgetcsv($fh)) !== false) {
                $row = array_combine($header, $r);
                if ($row && $row['changed'] === 'skipped') {
                    $ids[] = (int) $row['id'];
                }
            }
            fclose($fh);
        }
        sort($ids);
    } else {
        $ids = $con->query($sql)->fetchAll(PDO::FETCH_COLUMN, 0);
    }
    $stamp = gmdate('Ymd-His');
    $csvPath = $repoRoot . '/logs/cue_redetect-' . $stamp . ($n > 1 ? "-$k" : '') . '.csv';
    $csv = fopen($csvPath, 'w');
    fputcsv($csv, ['id', 'title', 'length', 'old_in', 'old_out', 'new_in', 'new_out', 'changed', 'flags']);
    $counts = ['files' => count($ids), 'measured' => 0, 'changed' => 0, 'skipped' => 0, 'outliers' => 0];
    $started = microtime(true);
    printf("dry run: %d file(s)%s, ffmpeg %s\n", count($ids), $n > 1 ? " (shard $k/$n)" : '', Application_Model_CuePoints::ffmpegBinary());
    foreach ($ids as $i => $id) {
        $file = Application_Model_StoredFile::RecallById((int) $id);
        if (!$file) {
            ++$counts['skipped'];
            continue;
        }
        $orm = $file->getPropelOrm();
        $title = (string) ($orm->getDbTrackTitle() ?: ('#' . $id));
        $length = seconds((string) $orm->getDbLength());
        $oldIn = seconds((string) $orm->getDbCuein());
        $oldOut = seconds((string) $orm->getDbCueout());
        $path = $orm->getAbsoluteFilePath();
        $cues = is_file($path) ? Application_Model_CuePoints::detect($path, $length) : null;
        if ($cues === null) {
            ++$counts['skipped'];
            fputcsv($csv, [$id, $title, sprintf('%.3f', $length), sprintf('%.3f', $oldIn), sprintf('%.3f', $oldOut), '', '', 'skipped', is_file($path) ? 'ffmpeg-failed' : 'file-missing']);
            continue;
        }
        ++$counts['measured'];
        $changed = abs($cues[0] - $oldIn) >= 0.005 || abs($cues[1] - $oldOut) >= 0.005;
        $flags = outlier($length, $cues[0], $cues[1]);
        if ($changed) {
            ++$counts['changed'];
        }
        if ($flags !== '') {
            ++$counts['outliers'];
        }
        fputcsv($csv, [$id, $title, sprintf('%.3f', $length), sprintf('%.3f', $oldIn), sprintf('%.3f', $oldOut),
            sprintf('%.3f', $cues[0]), sprintf('%.3f', $cues[1]), $changed ? 'yes' : 'no', $flags]);
        if (($i + 1) % 200 === 0) {
            CcFilesPeer::clearInstancePool();
            printf("  %6d / %d  (%.0f s)\n", $i + 1, count($ids), microtime(true) - $started);
        }
    }
    fclose($csv);
    printf("done: %d measured, %d would change, %d skipped, %d outlier(s) flagged, %.0f s\nreport: %s\n",
        $counts['measured'], $counts['changed'], $counts['skipped'], $counts['outliers'], microtime(true) - $started, $csvPath);
    exit(0);
}

// ---------------------------------------------------------------- apply / restore
$useNew = $opts['mode'] === 'apply';
$rows = [];
foreach ($opts['csv'] as $path) {
    $fh = fopen($path, 'r');
    if (!$fh) {
        fwrite(STDERR, "cannot read $path\n");
        exit(2);
    }
    $header = fgetcsv($fh);
    while (($r = fgetcsv($fh)) !== false) {
        $row = array_combine($header, $r);
        if ($row === false || $row['changed'] !== 'yes') {
            continue;   // skipped rows and unchanged files have nothing to write
        }
        if ($opts['skip_flagged'] && $row['flags'] !== '') {
            continue;   // --skip-flagged: leave the outliers to a manual decision
        }
        $rows[(int) $row['id']] = $row;
    }
    fclose($fh);
}
printf("%s: %d file(s) from %d report(s)\n", $useNew ? 'apply' : 'restore', count($rows), count($opts['csv']));
$update = $con->prepare('UPDATE cc_files SET cuein = :cuein, cueout = :cueout, mtime = :mtime WHERE id = :id');
$instances = [];
$written = 0;
$started = microtime(true);
$con->beginTransaction();
try {
    foreach ($rows as $id => $row) {
        $in = (float) ($useNew ? $row['new_in'] : $row['old_in']);
        $out = (float) ($useNew ? $row['new_out'] : $row['old_out']);
        $update->bindValue(':cuein', Application_Model_CuePoints::formatSeconds($in));
        $update->bindValue(':cueout', Application_Model_CuePoints::formatSeconds($out));
        $update->bindValue(':mtime', gmdate('Y-m-d H:i:s'));
        $update->bindValue(':id', $id, PDO::PARAM_INT);
        $update->execute();
        ++$written;
        foreach (Application_Model_CuePoints::applyToFutureRows($id, $con) as $instanceId) {
            $instances[$instanceId] = $instanceId;
        }
    }
    $con->commit();
} catch (Exception $e) {
    $con->rollBack();
    fwrite(STDERR, 'failed, rolled back: ' . $e->getMessage() . "\n");
    exit(1);
}
CcFilesPeer::clearInstancePool();
$relaid = Application_Model_CuePoints::relayoutInstances(array_values($instances));
Logging::info(sprintf('cue_redetect_all %s: %d file(s) written, %d instance(s) laid out again', $useNew ? 'apply' : 'restore', $written, $relaid));
printf("done: %d file(s) written, %d upcoming instance(s) laid out again, %.0f s\n", $written, $relaid, microtime(true) - $started);
