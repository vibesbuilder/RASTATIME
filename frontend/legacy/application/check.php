<?php

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Exception\AMQPRuntimeException;

function booleanReduce($a, $b)
{
    return $a && $b;
}

/**
 * Check to see if RASTATIME is properly configured.
 *
 * @return bool true if all dependencies and services are properly configured
 */
function checkConfiguration()
{
    $r1 = array_reduce(checkPhpDependencies(), 'booleanReduce', true);
    $r2 = array_reduce(checkExternalServices(), 'booleanReduce', true);

    return $r1 && $r2;
}

/**
 * Check for RASTATIME's PHP dependencies.
 *
 * @return array associative array of dependency check results
 */
function checkPhpDependencies()
{
    return [
        'postgres' => checkDatabaseDependencies(),
    ];
}

/**
 * Check that the PHP dependencies for the database exist.
 *
 * @return bool true if the database dependencies exist
 */
function checkDatabaseDependencies()
{
    global $extensions;

    return in_array('pdo_pgsql', $extensions)
        && in_array('pgsql', $extensions);
}

/**
 * Check whether a Windows NSSM service is currently running.
 *
 * RASTATIME 2026-05-16 - We use PowerShell `Get-Service` because
 * `sc.exe` is fully localised on non-English Windows installs and
 * every text-based parsing strategy we tried (matching the literal
 * word "RUNNING", matching the literal label "STATE", parsing by
 * value-line position) failed in some locale or other.  PowerShell's
 * `Get-Service` returns a .NET ServiceController object whose
 * `.Status` property is the ServiceControllerStatus enum --- its
 * member names ("Running", "Stopped", "Paused", "StartPending", ...)
 * are language-invariant regardless of OS display language, because
 * they are .NET identifiers, not user-facing strings.
 *
 * Results are static-cached for the lifetime of the request so the
 * Settings -> Status page does not pay PowerShell's ~500ms startup
 * cost once per service (the page calls this for 6 services).  The
 * first call seeds the cache via a single batch invocation; later
 * calls are array lookups.
 *
 * @param  string $service_name  Windows service name (e.g. "RASTATIME-API")
 * @return bool   true if the service is in the Running state
 */
function check_windows_service($service_name)
{
    static $cache = null;

    if ($cache === null) {
        $cache = _rastatime_load_service_status_cache();
    }

    if (array_key_exists($service_name, $cache)) {
        return $cache[$service_name];
    }

    // Fall back to a single-service PowerShell call for any name not in
    // the pre-warmed batch (e.g. callers outside the Settings -> Status
    // page asking for a service we didn't predict).
    $running = _rastatime_query_service_running($service_name);
    $cache[$service_name] = $running;
    return $running;
}

/**
 * Pre-warm the service-status cache with a single batched PowerShell
 * invocation covering every RASTATIME NSSM service that the
 * Settings -> Status page renders.  One process start instead of six.
 *
 * @return array<string,bool>  service name => running?
 */
function _rastatime_load_service_status_cache()
{
    $serviceNames = [
        'RASTATIME-PLAYOUT',
        'RASTATIME-WORKER',
        'RASTATIME-API',
        'RASTATIME-ANALYZER',
        'RASTATIME-ICECAST',
        'RASTATIME-APACHE',
    ];

    $quoted = array_map(
        function ($n) { return "'" . str_replace("'", "''", $n) . "'"; },
        $serviceNames
    );
    $list = implode(',', $quoted);

    // ForEach-Object emits one line per service: "<Name>=<Status>".
    // -ErrorAction SilentlyContinue makes Get-Service skip missing
    // services instead of dying on the first one.
    //
    // RASTATIME 2026-05-16 - PowerShell on Windows defaults to UTF-16 LE
    // output (with BOM), which PHP's exec() reads byte-by-byte: every ASCII
    // character ends up interleaved with NUL bytes, and our "$line === 'Running'"
    // comparison silently fails.  Force [Console]::OutputEncoding to UTF-8 so
    // the subprocess emits plain ASCII bytes that PHP can compare directly.
    //
    // Use the absolute path to powershell.exe because the Apache/NSSM
    // service worker can run with a stripped-down PATH that does not
    // contain C:\Windows\System32\WindowsPowerShell\v1.0\.  Falling back
    // to "powershell.exe" via PATH lookup is unreliable in that context
    // (we observed exec exit=1 with empty stdout on RASTATIME 2026-05-16).
    $psExe = _rastatime_powershell_exe_path();
    $psCmd = '"' . $psExe . '" -NoProfile -NonInteractive -Command '
           . '"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; '
           . 'Get-Service -Name @(' . $list . ') -ErrorAction SilentlyContinue '
           . '| ForEach-Object { $_.Name + \'=\' + $_.Status }" 2>&1';

    $output = [];
    $status = 0;
    @exec($psCmd, $output, $status);

    $result = array_fill_keys($serviceNames, false);
    if ($status === 0) {
        foreach ($output as $line) {
            $line = trim($line);
            if ($line === '') {
                continue;
            }
            $parts = explode('=', $line, 2);
            if (count($parts) === 2 && isset($result[$parts[0]])) {
                $result[$parts[0]] = ($parts[1] === 'Running');
            }
        }
    } else {
        Logging::warn('_rastatime_load_service_status_cache: powershell exit ' . $status);
    }

    return $result;
}

/**
 * One-off PowerShell Get-Service for a single service name (fallback
 * path when something asks about a service we didn't pre-warm).
 */
function _rastatime_query_service_running($service_name)
{
    $escaped = str_replace("'", "''", $service_name);
    $psExe = _rastatime_powershell_exe_path();
    // See batch loader for why we force UTF-8 OutputEncoding and use an
    // absolute powershell.exe path.
    $psCmd = '"' . $psExe . '" -NoProfile -NonInteractive -Command '
           . '"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; '
           . '(Get-Service -Name \'' . $escaped . '\' -ErrorAction SilentlyContinue).Status" 2>&1';

    $output = [];
    $status = 0;
    @exec($psCmd, $output, $status);

    if ($status !== 0 || empty($output)) {
        return false;
    }
    return trim(implode('', $output)) === 'Running';
}

/**
 * Resolve an absolute path to a usable powershell.exe.  Tries the
 * stock Windows PowerShell 5.1 location first (always present on a
 * modern Windows host), then PowerShell 7 (if installed), then a
 * bare "powershell.exe" as last-resort fallback for systems whose
 * PATH happens to contain it.
 *
 * The result is static-cached so probing only happens once per
 * request.
 */
function _rastatime_powershell_exe_path()
{
    static $cached = null;
    if ($cached !== null) {
        return $cached;
    }

    $systemRoot = getenv('SystemRoot');
    if (empty($systemRoot)) {
        $systemRoot = 'C:\\Windows';
    }

    $candidates = [
        $systemRoot . '\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
        'C:\\Program Files\\PowerShell\\7\\pwsh.exe',
        'C:\\Program Files\\PowerShell\\6\\pwsh.exe',
    ];

    foreach ($candidates as $candidate) {
        if (is_file($candidate)) {
            $cached = $candidate;
            return $cached;
        }
    }

    // Last resort: bare command name, relies on PATH.
    $cached = 'powershell.exe';
    return $cached;
}

/**
 * Check that all external services are configured correctly.
 *
 * @return array associative array of external service check results
 */
function checkExternalServices()
{
    return [
        'database' => checkDatabaseConfiguration(),
        'rabbitmq' => checkRMQConnection(),
        'pypo'     => check_windows_service('RASTATIME-PLAYOUT'),
        'worker'   => check_windows_service('RASTATIME-WORKER'),
        'api'      => check_windows_service('RASTATIME-API'),
        // RASTATIME 2026-05-16 - Status check extended for the remaining
        // Windows services the operator typically wants visibility on.
        'analyzer' => check_windows_service('RASTATIME-ANALYZER'),
        'icecast'  => check_windows_service('RASTATIME-ICECAST'),
        'apache'   => check_windows_service('RASTATIME-APACHE'),
    ];
}

/**
 * Check the database configuration by fetching a connection from Propel.
 *
 * @return bool true if a connection is made to the database
 */
function checkDatabaseConfiguration()
{
    configureDatabase();

    try {
        Propel::getConnection();
        Propel::close();
    } catch (Exception $exc) {
        Logging::error($exc->getMessage());

        return false;
    }

    return true;
}

/**
 * Initialize Propel to configure the database.
 */
function configureDatabase()
{
    Propel::init(PROPEL_CONFIG_FILEPATH);
}

/**
 * Check that we can connect to RabbitMQ.
 *
 * @return bool true if the RabbitMQ connection can be established
 */
function checkRMQConnection()
{
    $config = Config::getConfig();

    try {
        $conn = new AMQPStreamConnection(
            $config['rabbitmq']['host'],
            $config['rabbitmq']['port'],
            $config['rabbitmq']['user'],
            $config['rabbitmq']['password'],
            $config['rabbitmq']['vhost']
        );

        return isset($conn);
    } catch (AMQPRuntimeException $exc) {
        Logging::error($exc->getMessage());

        return false;
    }
}
