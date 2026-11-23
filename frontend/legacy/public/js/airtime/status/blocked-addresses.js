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
            var actions = '<button type="button" class="btn blocked-unblock-btn" data-key="' + esc(r.key) + '">' + esc(i18n("unblock")) + "</button>";
            if (r.address && r.layer !== "web-user") {
                // RASTATIME 2026-10-08 - one click: unblock everywhere and allow for good
                actions += ' <button type="button" class="btn blocked-allow-btn" data-entry="' + esc(r.address) + '">' + esc(i18n("allow")) + "</button>";
            }
            tr.append("<td>" + actions + "</td>");
            body.append(tr);
        });
    }

    // RASTATIME 2026-10-08 - the allow list (address or CIDR network);
    // RASTATIME 2026-11-23 - with comment (click to edit) and date added
    function editingComment() {
        return $("#allowed-addresses-body .allowed-comment-input").length > 0;
    }

    function renderAllowed(details) {
        if (editingComment()) {
            return; // the 30-s refresh must not throw away a comment being typed
        }
        var body = $("#allowed-addresses-body");
        body.empty();
        if (!details || !details.length) {
            body.append('<tr><td colspan="4" class="description">' + esc(i18n("allowed-none")) + "</td></tr>");
            return;
        }
        $.each(details, function (_, d) {
            var tr = $("<tr/>");
            tr.append('<td class="description"><strong>' + esc(d.entry) + "</strong></td>");
            var text = d.comment
                ? '<span class="allowed-comment-text" style="cursor: pointer;">' + esc(d.comment) + "</span>"
                : '<span class="allowed-comment-text" style="cursor: pointer; font-style: italic; opacity: 0.6;">' + esc(i18n("comment-add")) + "</span>";
            var td = $('<td class="description allowed-comment-cell"/>').attr("data-entry", d.entry).attr("data-comment", d.comment || "").html(text);
            tr.append(td);
            tr.append('<td class="description" style="white-space: nowrap;">' + esc(d.added || "") + "</td>");
            tr.append('<td><button type="button" class="btn allowed-remove-btn" data-entry="' + esc(d.entry) + '">' + esc(i18n("remove")) + "</button></td>");
            body.append(tr);
        });
    }

    function detailsOf(data) {
        if (data && data.allowed_details) {
            return data.allowed_details;
        }
        return $.map(data && data.allowed ? data.allowed : [], function (entry) {
            return { entry: entry, comment: "", added: "" };
        });
    }

    function startEdit(cell) {
        if (cell.find(".allowed-comment-input").length) {
            return;
        }
        var input = $('<input type="text" class="allowed-comment-input" maxlength="200" autocomplete="off" style="width: 60%;">').val(cell.attr("data-comment") || "");
        var save = $('<button type="button" class="btn allowed-comment-save"/>').text(i18n("save"));
        var cancel = $('<button type="button" class="btn allowed-comment-cancel"/>').text(i18n("cancel"));
        cell.empty().append(input, " ", save, " ", cancel);
        input.trigger("focus");
    }

    function saveComment(cell) {
        var entry = cell.attr("data-entry");
        var comment = $.trim(cell.find(".allowed-comment-input").val() || "");
        $.ajax({
            url: baseUrl + "systemstatus/allowed-address-comment",
            type: "POST",
            dataType: "json",
            data: { entry: entry, comment: comment, csrf_token: csrfToken() }
        }).done(function (data) {
            var ok = !!(data && data.ok);
            showStatus(ok ? i18n("comment-saved").replace("%s", entry) : i18n("comment-failed"), ok);
            cell.find(".allowed-comment-input").remove();
            if (ok) {
                renderAllowed(detailsOf(data));
            } else {
                load();
            }
        }).fail(function () {
            showStatus(i18n("comment-failed"), false);
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
            .done(function (data) {
                render(data && data.rows ? data.rows : []);
                renderAllowed(detailsOf(data));
            })
            .fail(function () { render([]); });
    }

    function allow(entry, comment) {
        var payload = { entry: entry, csrf_token: csrfToken() };
        if (comment) {
            payload.comment = comment;
        }
        $.ajax({
            url: baseUrl + "systemstatus/allow-address",
            type: "POST",
            dataType: "json",
            data: payload
        }).done(function (data) {
            if (data && data.ok) {
                showStatus(i18n("allowed-done").replace("%s", data.entry || entry), true);
                $("#allowed-addresses-entry").val("");
                $("#allowed-addresses-comment").val("");
            } else {
                showStatus(data && data.error === "bad-entry" ? i18n("allowed-invalid") : i18n("allowed-failed"), false);
            }
            load();
        }).fail(function () {
            showStatus(i18n("allowed-failed"), false);
        });
    }

    function disallow(entry) {
        $.ajax({
            url: baseUrl + "systemstatus/disallow-address",
            type: "POST",
            dataType: "json",
            data: { entry: entry, csrf_token: csrfToken() }
        }).done(function (data) {
            showStatus(data && data.ok ? i18n("allowed-removed").replace("%s", entry) : i18n("allowed-failed"), !!(data && data.ok));
            load();
        }).fail(function () {
            showStatus(i18n("allowed-failed"), false);
        });
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
        $(document).on("click", ".blocked-allow-btn", function () {
            allow($(this).attr("data-entry"));
        });
        $(document).on("click", ".allowed-remove-btn", function () {
            disallow($(this).attr("data-entry"));
        });
        $(document).on("click", "#allowed-addresses-add", function () {
            var entry = $.trim($("#allowed-addresses-entry").val() || "");
            if (entry) {
                allow(entry, $.trim($("#allowed-addresses-comment").val() || ""));
            }
        });
        $(document).on("keydown", "#allowed-addresses-entry, #allowed-addresses-comment", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                $("#allowed-addresses-add").trigger("click");
            }
        });
        // RASTATIME 2026-11-23 - edit a comment in place: Enter / Save stores, Escape / Cancel drops
        $(document).on("click", ".allowed-comment-text", function () {
            startEdit($(this).closest(".allowed-comment-cell"));
        });
        $(document).on("click", ".allowed-comment-save", function () {
            saveComment($(this).closest(".allowed-comment-cell"));
        });
        $(document).on("click", ".allowed-comment-cancel", function () {
            $(this).closest(".allowed-comment-cell").find(".allowed-comment-input").remove();
            load();
        });
        $(document).on("keydown", ".allowed-comment-input", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                saveComment($(this).closest(".allowed-comment-cell"));
            } else if (e.key === "Escape") {
                e.preventDefault();
                $(this).remove();
                load();
            }
        });
        var allowedHelp = $("#allowed-addresses-help");
        if (allowedHelp.length && $.fn.rtTooltip) {
            allowedHelp.rtTooltip({
                content: { text: $("<div/>").text(allowedHelp.attr("data-tip") || "").html() },
                placement: "right",
                interactive: true
            });
        }
        load();
        timer = window.setInterval(load, REFRESH_MS);
        (window.rtPollTimers = window.rtPollTimers || []).push(timer); // stopped on the first 401 (common.js)
    });
})(jQuery);
