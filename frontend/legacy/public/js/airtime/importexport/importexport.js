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
    return S.statusError || "error";
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
          $("#rt_ie_preview").show();
          var ok = $.grep(data.rows || [], function (r) { return r.status === "ok"; }).length;
          setStatus((data.rows || []).length + " rows, " + ok + " importable", false);
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
      setStatus(S.importing, true);
      $.ajax({ url: cfg.baseUrl + "/import", type: "POST", dataType: "json",
        data: { token: token, selected: selected, csrf_token: $("#rt_ie_csrf").val() } })
        .done(function (data) {
          if (data.error) { setStatus(data.error, false); return; }
          token = null;
          $("#rt_ie_preview").hide();
          var s = data.summary || { ok: 0, skip: 0, error: 0 };
          $("#rt_ie_result_summary").text((S.summary || "%1 / %2 / %3").replace("%1", s.ok).replace("%2", s.skip).replace("%3", s.error));
          $("#rt_ie_result_table").html(rowsTable(data.rows || [], false, S.resultOk));
          $("#rt_ie_result").show();
          setStatus("", false);
        })
        .fail(function (xhr) {
          var msg = S.requestFailed;
          try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* keep */ }
          setStatus(msg, false);
        })
        .always(function () { btn.prop("disabled", false); });
    });
  });
})(jQuery);
