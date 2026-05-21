/**
 * RASTATIME 2026-05-16 - Service-restart button handlers for the
 * Settings -> Status page.
 *
 * Wires the per-service "Restart" buttons and the "Restart All" button to
 * the SystemstatusController endpoints (restart-service / restart-all),
 * with a confirmation dialog for any restart that takes the UI offline
 * (Apache and Restart All).
 *
 * Status messages render into #service-restart-status; for restarts that
 * detach Apache, the page auto-reloads after a short delay so the operator
 * can observe the post-restart status table.
 */

(function ($) {
    "use strict";

    var STATUS_EL = "#service-restart-status";
    // Services that detach (Apache) or trigger Apache (Restart All) need an
    // auto-reload because the in-flight HTTP response is the last thing the
    // UI receives before the worker dies.  The server-side
    // _scheduleDetachedRestart() uses a ~6s pre-delay before invoking nssm
    // on Apache, then nssm itself takes ~5s to stop+start Apache, so the
    // earliest the UI is reachable again is ~11s after our request.
    // 15s gives a small safety buffer.
    var APACHE_RELOAD_DELAY_MS = 15000;

    function showStatus(html, klass) {
        $(STATUS_EL)
            .removeClass("alert-info alert-success alert-warning alert-danger")
            .addClass(klass || "alert-info")
            .html(html)
            .show();
    }

    function clearStatus() {
        $(STATUS_EL).hide().empty();
    }

    function csrfToken() {
        return $("#csrf").val();
    }

    function restartOne(serviceName) {
        showStatus(
            $.i18n._("Restarting") +
                " <strong>" +
                serviceName +
                "</strong>" +
                "&hellip;",
            "alert-info",
        );

        $.ajax({
            url: baseUrl + "systemstatus/restart-service",
            type: "POST",
            data: {
                service: serviceName,
                csrf_token: csrfToken(),
            },
            dataType: "json",
        })
            .done(function (resp) {
                if (resp && resp.ok) {
                    if (resp.mode === "detached") {
                        showStatus(
                            $.i18n._("Restart issued in background for") +
                                " <strong>" +
                                serviceName +
                                "</strong>. " +
                                $.i18n._(
                                    "The UI will reload shortly to refresh the status.",
                                ),
                            "alert-warning",
                        );
                        setTimeout(function () {
                            location.reload();
                        }, APACHE_RELOAD_DELAY_MS);
                    } else {
                        showStatus(
                            $.i18n._("Restart successful for") +
                                " <strong>" +
                                serviceName +
                                "</strong> " +
                                "(exit " +
                                resp.exit +
                                "). " +
                                $.i18n._("Status will refresh on next poll."),
                            "alert-success",
                        );
                    }
                } else {
                    showStatus(
                        $.i18n._("Restart failed for") +
                            " <strong>" +
                            serviceName +
                            "</strong>: " +
                            (resp && resp.error
                                ? resp.error
                                : $.i18n._("unknown error")) +
                            (resp && resp.output
                                ? "<pre>" + resp.output + "</pre>"
                                : ""),
                        "alert-danger",
                    );
                }
            })
            .fail(function (xhr, status, err) {
                showStatus(
                    $.i18n._("Restart request failed:") + " " + (err || status),
                    "alert-danger",
                );
            });
    }

    function restartAll() {
        showStatus(
            $.i18n._(
                "Restarting all RASTATIME services. The UI will be unreachable for a few seconds and then reload.",
            ),
            "alert-warning",
        );

        $.ajax({
            url: baseUrl + "systemstatus/restart-all",
            type: "POST",
            data: { csrf_token: csrfToken() },
            dataType: "json",
        })
            .done(function (resp) {
                // We always reload after restart-all - Apache will be coming
                // back up from underneath us, so this response was caught on
                // the edge of the old worker process.
                setTimeout(function () {
                    location.reload();
                }, APACHE_RELOAD_DELAY_MS);
            })
            .fail(function (xhr, status, err) {
                // Apache may already be cycling - reload anyway.
                setTimeout(function () {
                    location.reload();
                }, APACHE_RELOAD_DELAY_MS);
            });
    }

    $(document).ready(function () {
        // Per-service restart buttons.
        $(".service-restart-btn").on("click", function () {
            var svc = $(this).data("service");
            if (!svc) {
                return;
            }
            // Apache restart kills the very PHP worker serving this UI.
            // Always confirm explicitly to avoid accidental clicks.
            if (svc === "RASTATIME-APACHE") {
                if (
                    !confirm(
                        $.i18n._(
                            "Restarting Apache will make the UI unreachable for ~10 seconds.  The page will auto-reload.  Continue?",
                        ),
                    )
                ) {
                    return;
                }
            }
            restartOne(svc);
        });

        // Restart-all button.
        $(".service-restart-all-btn").on("click", function () {
            if (
                !confirm(
                    $.i18n._(
                        "This will restart EVERY RASTATIME service in the background.  Audio output will briefly drop, the UI will be unreachable for ~10 seconds, and the page will auto-reload.  Continue?",
                    ),
                )
            ) {
                return;
            }
            restartAll();
        });
    });
})(jQuery);
