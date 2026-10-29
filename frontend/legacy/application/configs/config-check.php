<?php
/*
 * We only get here after setup, or if there's an error in the configuration.
 *
 * Display a table to the user showing the necessary dependencies
 * (both PHP and binary) and the status of any application services,
 * along with steps to fix them if they're not found or misconfigured.
 */

global $extensions;

$phpDependencies = checkPhpDependencies();
$externalServices = checkExternalServices();
$postgres = $phpDependencies['postgres'];

$database = $externalServices['database'];
$rabbitmq = $externalServices['rabbitmq'];
$pypo     = $externalServices['pypo'];
$worker   = $externalServices['worker'];
$api      = $externalServices['api'];

$r1 = array_reduce($phpDependencies, 'booleanReduce', true);
$r2 = array_reduce($externalServices, 'booleanReduce', true);
$result = $r1 && $r2;
?>
<html>

<head>
    <link rel="stylesheet" type="text/css" href="css/bootstrap-3.3.1.min.css">
    <link rel="stylesheet" type="text/css" href="css/setup/config-check.css">
</head>
<style>
    /*
    This is here because we're using the config-check css for
    both this page and the system status page
    */

    html {
        background-color: #f5f5f5;
    }

    body {
        padding: 2em;
        min-width: 600px;
        text-align: center;
        margin: 3em;
        border: 1px solid lightgray;
        border-radius: 5px;
    }
</style>

<body>
    <h2>
        <img class="logo" src="css/images/airtime_logo_jp.png" /><br />
        <strong>Configuration Checklist</strong>
    </h2>

    <?php if (!$result) { ?>
        <br />
        <h3 class="error">Looks like something went wrong!</h3>
        <p>
            Take a look at the checklist below for possible solutions. If you're tried the suggestions and are
            still experiencing issues, read the
            <a href="https://github.com/libretime/libretime/releases">release notes</a>,
            come <a href="https://discourse.libretime.org/">visit our discourse</a>
            or, check <a href="https://www.libretime.org/">the website and main docs</a>.
        </p>
    <?php } else { ?>
        <p>
            Your Airtime station is up and running! Get started by logging in with the default username and password: admin/admin
        </p>
        <button onclick="location = location.pathname;">Log in to Airtime!</button>
    <?php } ?>


    <table class="table">
        <thead>
            <tr>
                <th class="component">
                    Component
                </th>
                <th class="description">
                    <strong>Description</strong>
                </th>
                <th class="solution">
                    <strong>Status or Solution</strong>
                </th>
            </tr>
        </thead>
    </table>

    <div class="checklist">
        <table class="table table-striped">
            <caption class="caption">
                PHP Dependencies
            </caption>
            <tbody>
                <tr class="<?php echo $postgres ? 'success' : 'danger'; ?>">
                    <td class="component">
                        Postgres
                    </td>
                    <td class="description">
                        PDO and PostgreSQL libraries
                    </td>
                    <?php if ($postgres) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">Try running <code>sudo apt-get install php5-pgsql</code></td>
                    <?php } ?>
                </tr>
            </tbody>
        </table>

        <table class="table table-striped">
            <caption class="caption">
                External Services
            </caption>
            <tbody>
                <tr class="<?php echo $database ? 'success' : 'danger'; ?>">
                    <td class="component">
                        Database
                    </td>
                    <td class="description">
                        Database configuration for Airtime
                    </td>
                    <?php if ($database) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">
                            Make sure you aren't missing any of the Postgres dependencies in the table above.
                            If your dependencies check out, make sure your database configuration settings in
                            <code><?php echo RASTATIME_CONFIG_FILEPATH; ?></code> are correct and the Airtime database was installed correctly.
                        </td>
                    <?php } ?>
                </tr>
                <tr class="<?php echo $rabbitmq ? 'success' : 'danger'; ?>">
                    <td class="component">
                        RabbitMQ
                    </td>
                    <td class="description">
                        RabbitMQ configuration for Airtime
                    </td>

                    <?php if ($rabbitmq) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">
                            Make sure RabbitMQ is installed correctly, and that your settings in <?php echo RASTATIME_CONFIG_FILEPATH; ?>
                            are correct. Try using <code>sudo rabbitmqctl list_users</code> and <code>sudo rabbitmqctl list_vhosts</code>
                            to see if the airtime user (or your custom RabbitMQ user) exists, then checking that
                            <code>sudo rabbitmqctl list_exchanges</code> contains entries for airtime-pypo and airtime-uploads.
                        </td>
                    <?php } ?>
                </tr>
                <tr class="<?php echo $pypo ? 'success' : 'danger'; ?>">
                    <td class="component">Playout</td>
                    <td class="description"><?php echo _('RASTATIME playout service (NSSM)'); ?></td>
                    <?php if ($pypo) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">
                            <?php echo _('Check that the RASTATIME-PLAYOUT service is installed. Run '); ?>
                            <code>sc query RASTATIME-PLAYOUT</code>
                            <?php echo _(' or open Services (services.msc) to verify.'); ?>
                            <?php echo _(' To restart: '); ?>
                            <code>sc start RASTATIME-PLAYOUT</code>
                        </td>
                    <?php } ?>
                </tr>
                <tr class="<?php echo $worker ? 'success' : 'danger'; ?>">
                    <td class="component">Worker</td>
                    <td class="description"><?php echo _('RASTATIME worker service (NSSM)'); ?></td>
                    <?php if ($worker) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">
                            <?php echo _('Check that the RASTATIME-WORKER service is installed. Run '); ?>
                            <code>sc query RASTATIME-WORKER</code>
                            <?php echo _(' or open Services (services.msc) to verify.'); ?>
                            <?php echo _(' To restart: '); ?>
                            <code>sc start RASTATIME-WORKER</code>
                        </td>
                    <?php } ?>
                </tr>
                <tr class="<?php echo $api ? 'success' : 'danger'; ?>">
                    <td class="component">API</td>
                    <td class="description"><?php echo _('RASTATIME API service (NSSM)'); ?></td>
                    <?php if ($api) { ?>
                        <td class="solution check"></td>
                    <?php } else { ?>
                        <td class="solution">
                            <?php echo _('Check that the RASTATIME-API service is installed. Run '); ?>
                            <code>sc query RASTATIME-API</code>
                            <?php echo _(' or open Services (services.msc) to verify.'); ?>
                            <?php echo _(' To restart: '); ?>
                            <code>sc start RASTATIME-API</code>
                        </td>
                    <?php } ?>
                </tr>
            </tbody>
        </table>
    </div>
    <div class="footer">
        <h3>
            PHP Extension List
        </h3>
        <p>
            <?php echo implode('|', $extensions); ?>
        </p>
    </div>
