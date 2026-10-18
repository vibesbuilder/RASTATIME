/*
 * RASTATIME 2026-10-13 - Settings -> Import/Export (Section 23.56).
 * Export: build the download URL from the ticked types.
 * Import: upload -> preview table (tick rows) -> import -> result table.
 */
(function ($) {
  "use strict";

  var cfg = window.rtImportExport || { baseUrl: "/importexport", strings: {} };
  var S = cfg.strings;
  var token = null;

  function esc(s) {
    return $("<div/>").text(s == null ? "" : String(s)).html();
  }

  function statusLabel(st) {
    if (st === "ok") return S.statusOk || "ready";
    if (st === "skip") return S.statusSkip || "skipped";
    if (st === "pending") return S.statusPending || "checking";
    return S.statusError || "error";
  }

  // RASTATIME 2026-10-18 - batches: the server checks and imports a few rows
  // per request (a single request for hundreds of shows ran past the web
  // server's 120 s and was cut off while PHP went on creating shows)
  var BATCH = 10;
  var run = 0;            // bumped by every new upload: a running batch loop stops

  function fmt(tpl, a, b) {
    return String(tpl || "%1 / %2").replace("%1", a).replace("%2", b);
  }

  function updateRow(r) {
    var $tr = $("#rt_ie_preview_table tr[data-id='" + r.id + "']");
    if (!$tr.length) return;
    var st = r.status || "error";
    $tr.attr("data-status", st);
    $tr.find("td").eq(0).html(st === "ok" ? "<input type='checkbox' class='rt-ie-row' checked />" : "");
    $tr.find("td").eq(5).attr("class", "rt-ie-st-" + esc(st)).text(statusLabel(st));
    $tr.find("td").eq(6).html($.map(r.messages || [], esc).join("<br/>"));
  }

  function validateBatches(ids, myRun, done) {
    var total = ids.length, at = 0;
    function next() {
      if (myRun !== run) return;
      if (at >= total) { done(); return; }
      var chunk = ids.slice(at, at + BATCH);
      setStatus(fmt(S.checking, Math.min(at + chunk.length, total), total), true);
      $.ajax({ url: cfg.baseUrl + "/validate", type: "POST", dataType: "json",
        data: { token: token, ids: chunk, csrf_token: $("#rt_ie_csrf").val() } })
        .done(function (data) {
          if (myRun !== run) return;
          if (data.error) { setStatus(data.error, false); return; }
          $.each(data.rows || [], function (_, r) { updateRow(r); });
          at += chunk.length;
          next();
        })
        .fail(function (xhr) {
          var msg = S.requestFailed;
          try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* keep */ }
          setStatus(msg, false);
        });
    }
    next();
  }

  function rowsTable(rows, withCheckbox, okLabel) {
    var h = "<table class='datatable'><thead><tr>";
    if (withCheckbox) h += "<th></th>";
    h += "<th>" + esc(S.type) + "</th><th>" + esc(S.line) + "</th><th>" + esc(S.name) + "</th><th>" + esc(S.details) + "</th><th>" + esc(S.status) + "</th><th>" + esc(S.messages) + "</th></tr></thead><tbody>";
    $.each(rows, function (_, r) {
      var st = r.status || "error";
      h += "<tr data-id='" + esc(r.id) + "' data-status='" + esc(st) + "'>";
      if (withCheckbox) {
        h += "<td>" + (st === "ok" ? "<input type='checkbox' class='rt-ie-row' checked />" : "") + "</td>";
      }
      h += "<td>" + esc(r.label || r.type) + "</td><td>" + esc(r.line) + "</td><td>" + esc(r.name) + "</td><td class='rt-ie-msg'>" + esc(r.summary || "") + "</td>";
      h += "<td class='rt-ie-st-" + esc(st) + "'>" + esc(st === "ok" && okLabel ? okLabel : statusLabel(st)) + "</td>";
      h += "<td class='rt-ie-msg'>" + $.map(r.messages || [], esc).join("<br/>") + "</td></tr>";
    });
    return h + "</tbody></table>";
  }

  function setStatus(text, busy) {
    $("#rt_ie_status").text(text || "").toggleClass("rt-ie-busy", !!busy);
  }

  $(function () {
    $("#rt_ie_export_btn").on("click", function () {
      var types = $("#rt_ie_export_types input:checked").map(function () { return this.value; }).get();
      if (!types.length) return;
      window.location.href = cfg.baseUrl + "/export?types=" + encodeURIComponent(types.join(","));
    });

    $("#rt_ie_preview_btn").on("click", function () {
      var input = document.getElementById("rt_ie_file");
      if (!input.files || !input.files.length) {
        setStatus(S.noFile, false);
        return;
      }
      var fd = new FormData();
      fd.append("file", input.files[0]);
      fd.append("type", $("#rt_ie_type").val());
      fd.append("conflict", $("#rt_ie_conflict").val());
      fd.append("csrf_token", $("#rt_ie_csrf").val());
      setStatus(S.uploading, true);
      $("#rt_ie_result").hide();
      $("#rt_ie_preview").hide();
      $.ajax({ url: cfg.baseUrl + "/preview", type: "POST", data: fd, processData: false, contentType: false, dataType: "json" })
        .done(function (data) {
          if (data.error) { setStatus(data.error, false); return; }
          token = data.token;
          var notices = $("#rt_ie_notices").empty();
          $.each(data.notices || [], function (_, n) { notices.append("<div class='rt-ie-notice'>" + esc(n) + "</div>"); });
          $("#rt_ie_preview_table").html(rowsTable(data.rows || [], true, null));
          $("#rt_ie_select_all").prop("checked", true);
          $("#rt_ie_import_btn").prop("disabled", true);
          $("#rt_ie_preview").show();
          var myRun = ++run;
          var ids = $.map(data.rows || [], function (r) { return r.id; });
          validateBatches(ids, myRun, function () {
            var ok = $("#rt_ie_preview_table tr[data-status='ok']").length;
            setStatus(ids.length + " rows, " + ok + " importable", false);
            $("#rt_ie_import_btn").prop("disabled", false);
          });
        })
        .fail(function (xhr) {
          var msg = S.requestFailed;
          try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* keep */ }
          setStatus(msg, false);
        });
    });

    $("#rt_ie_select_all").on("change", function () {
      $("#rt_ie_preview_table .rt-ie-row").prop("checked", this.checked);
    });

    $("#rt_ie_import_btn").on("click", function () {
      if (!token) return;
      var selected = $("#rt_ie_preview_table .rt-ie-row:checked").map(function () { return $(this).closest("tr").data("id"); }).get();
      if (!selected.length) { setStatus(S.nothingSelected, false); return; }
      var btn = $(this).prop("disabled", true);
      $("#rt_ie_preview_btn").prop("disabled", true);
      var myRun = ++run, total = selected.length, at = 0, all = [];
      function finishImport() {
        token = null;
        $("#rt_ie_preview").hide();
        var s = { ok: 0, skip: 0, error: 0 };
        $.each(all, function (_, r) { if (s[r.status] !== undefined) s[r.status]++; });
        $("#rt_ie_result_summary").text((S.summary || "%1 / %2 / %3").replace("%1", s.ok).replace("%2", s.skip).replace("%3", s.error));
        $("#rt_ie_result_table").html(rowsTable(all, false, S.resultOk));
        $("#rt_ie_result").show();
        setStatus("", false);
        btn.prop("disabled", false);
        $("#rt_ie_preview_btn").prop("disabled", false);
      }
      function next() {
        if (myRun !== run) return;
        var chunk = selected.slice(at, at + BATCH);
        var last = at + chunk.length >= total;
        setStatus(fmt(S.importingOf, Math.min(at + chunk.length, total), total), true);
        $.ajax({ url: cfg.baseUrl + "/import", type: "POST", dataType: "json",
          data: { token: token, selected: chunk, partial: 1, finish: last ? 1 : 0, csrf_token: $("#rt_ie_csrf").val() } })
          .done(function (data) {
            if (data.error) { setStatus(data.error, false); btn.prop("disabled", false); $("#rt_ie_preview_btn").prop("disabled", false); return; }
            all = all.concat(data.rows || []);
            at += chunk.length;
            if (last) { finishImport(); } else { next(); }
          })
          .fail(function (xhr) {
            var msg = S.requestFailed;
            try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* keep */ }
            setStatus(msg, false);
            btn.prop("disabled", false);
            $("#rt_ie_preview_btn").prop("disabled", false);
          });
      }
      next();
    });
  });
})(jQuery);
