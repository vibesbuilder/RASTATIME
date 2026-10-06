/**
 * RASTATIME 2026-10-06 - System Status: "Blocked addresses".
 *
 * Lists the brute-force brakes' state (web login per address / user, DJ
 * harbor, firewall watcher rules) from systemstatus/blocked-addresses and
 * clears one entry through systemstatus/unblock-address (POST, CSRF).
 * Refreshes every 30 s while the page is open.
 */
(function ($) {
    "use strict";

    var REFRESH_MS = 30000;
    var timer = null;

    function i18n(key) {
        var el = document.getElementById("blocked-addresses-i18n");
        return el ? (el.getAttribute("data-" + key) || key) : key;
    }

    function esc(s) {
        return $("<div/>").text(s == null ? "" : String(s)).html();
    }

    function csrfToken() {
        return $("#csrf").val();
    }

    function layerLabel(layer) {
        return i18n({ "web": "web", "web-user": "web-user", "harbor": "harbor", "firewall": "firewall" }[layer] || layer);
    }

    function render(rows) {
        var body = $("#blocked-addresses-body");
        body.empty();
        if (!rows || !rows.length) {
            body.append('<tr><td colspan="5" class="description">' + esc(i18n("none")) + "</td></tr>");
            return;
        }
        $.each(rows, function (_, r) {
            var who = r.user ? r.user : r.address;
            var state = r.seconds_left > 0
                ? i18n("blocked").replace("%s", String(Math.ceil(r.seconds_left / 60)))
                : i18n("counting");
            var tr = $("<tr/>");
            tr.append('<td class="component">' + esc(layerLabel(r.layer)) + "</td>");
            tr.append('<td class="description"><strong>' + esc(who) + "</strong></td>");
            tr.append('<td class="description">' + esc(r.detail || r.count) + "</td>");
            tr.append('<td class="description"' + (r.seconds_left > 0 ? ' style="color:#c83f3f"' : "") + ">" + esc(state) + "</td>");
            tr.append('<td><button type="button" class="btn blocked-unblock-btn" data-key="' + esc(r.key) + '">' + esc(i18n("unblock")) + "</button></td>");
            body.append(tr);
        });
    }

    function showStatus(text, ok) {
        $("#blocked-addresses-status")
            .removeClass("alert-success alert-danger")
            .addClass("alert " + (ok ? "alert-success" : "alert-danger"))
            .text(text)
            .show();
    }

    function load() {
        $.ajax({ url: baseUrl + "systemstatus/blocked-addresses", type: "GET", dataType: "json", cache: false })
            .done(function (data) { render(data && data.rows ? data.rows : []); })
            .fail(function () { render([]); });
    }

    function unblock(key) {
        $.ajax({
            url: baseUrl + "systemstatus/unblock-address",
            type: "POST",
            dataType: "json",
            data: { key: key, csrf_token: csrfToken() }
        }).done(function (data) {
            if (data && data.ok) {
                showStatus(i18n("done").replace("%s", key.replace(/^user:/, "")), true);
            } else {
                showStatus(i18n("failed"), false);
            }
            load();
        }).fail(function () {
            showStatus(i18n("failed"), false);
        });
    }

    $(document).ready(function () {
        if (!$("#blocked-addresses-body").length) {
            return;
        }
        // the thresholds as a tooltip on the section title (house style:
        // .help_icon + rtTooltip, like Settings -> Streams)
        var help = $("#blocked-addresses-help");
        if (help.length && $.fn.rtTooltip) {
            help.rtTooltip({
                content: { text: $("<div/>").text(help.attr("data-tip") || "").html() },
                placement: "right",
                interactive: true
            });
        }
        $(document).on("click", ".blocked-unblock-btn", function () {
            unblock($(this).attr("data-key"));
        });
        load();
        timer = window.setInterval(load, REFRESH_MS);
    });
})(jQuery);
