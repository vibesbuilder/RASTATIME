/**
 * T14.2 / T14.3 — Line-In source management page JavaScript.
 *
 * On DOM ready:
 *  1. Fetches GET /api/v2/audio/devices to build a stable_id → name map.
 *  2. Fetches GET /api/v2/audio/linein to load persisted entries.
 *  3. Renders the table with Name / Device / Channels / Priority / Status /
 *     Description / Actions columns.
 *
 * T14.3 adds:
 *  - "New Line-In" button opens a jQuery UI dialog (create mode).
 *  - Edit icon in each row reopens the dialog pre-populated (edit mode).
 *  - Delete icon opens a confirm prompt; removes the row on confirmation.
 *  - Enable / Disable toggle patches the enabled field without full reload.
 */

(function ($) {
  "use strict";

  /* ---------------------------------------------------------------------- */
  /* Module state                                                             */
  /* ---------------------------------------------------------------------- */

  var _deviceNameMap  = {};   // stable_id → display name
  var _availableInputs = [];  // [{stable_id, name}, ...] — inputs only
  var _lineIns        = [];   // current list (refreshed on every reload)

  /* ---------------------------------------------------------------------- */
  /* Utility                                                                  */
  /* ---------------------------------------------------------------------- */

  function showError(msg) {
    $("#linein-status-msg").html(
      "<div class='errors'>" + $("<span>").text(msg).html() + "</div>"
    );
  }

  function clearStatus() {
    $("#linein-status-msg").empty();
  }

  function showSuccess(msg) {
    $("#linein-status-msg").html(
      "<div class='success'>" + $("<span>").text(msg).html() + "</div>"
    );
  }

  /**
   * Build a map of stable_id → device name from GET /api/v2/audio/devices.
   *
   * @param  {Object} devicesData  Full devices response
   * @return {Object}              { stable_id: "Friendly Name", ... }
   */
  function buildDeviceNameMap(devicesData) {
    var map = {};
    var all = (devicesData.outputs || []).concat(devicesData.inputs || []);
    $.each(all, function (_, dev) {
      map[dev.stable_id] = dev.name;
    });
    return map;
  }

  /**
   * Build the list of available input devices for the dialog select box.
   *
   * @param  {Object} devicesData
   * @return {Array}  [{stable_id, name}, ...]
   */
  function buildInputList(devicesData) {
    return (devicesData.inputs || []).map(function (d) {
      return { stable_id: d.stable_id, name: d.name };
    });
  }

  /**
   * Format a channel_mapping array for display (1-based).
   * e.g. [0, 1] → "Ch 1–2"   [0] → "Ch 1"   [2, 3] → "Ch 3–4"
   *
   * @param  {number[]} mapping  0-based channel indices
   * @return {string}
   */
  function formatChannels(mapping) {
    if (!mapping || mapping.length === 0) { return "—"; }
    var ones = mapping.map(function (c) { return c + 1; });
    if (ones.length === 1) { return "Ch " + ones[0]; }
    var min = Math.min.apply(null, ones);
    var max = Math.max.apply(null, ones);
    return "Ch " + min + "–" + max;
  }

  /**
   * Parse a comma-separated channel string ("0,1") into an int array.
   * Returns null if any token is invalid.
   *
   * @param  {string} str
   * @return {number[]|null}
   */
  function parseChannels(str) {
    var tokens = (str || "").split(",");
    var result = [];
    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i].trim();
      if (t === "") { return null; }
      var n = parseInt(t, 10);
      if (isNaN(n) || n < 0 || String(n) !== t) { return null; }
      result.push(n);
    }
    return result.length > 0 ? result : null;
  }

  /* ---------------------------------------------------------------------- */
  /* Table rendering                                                          */
  /* ---------------------------------------------------------------------- */

  function renderTable(lineIns) {
    var i18n   = AIRTIME.linein.i18n;
    var $tbody = $("#linein-tbody");
    $tbody.empty();

    if (!lineIns || lineIns.length === 0) {
      $tbody.append(
        $("<tr>").append(
          $("<td>")
            .attr("colspan", 7)
            .css({ textAlign: "center", color: "#888", padding: "1.5em",
                   fontStyle: "italic" })
            .text(i18n.noEntries)
        )
      );
      return;
    }

    $.each(lineIns, function (_, li) {
      var deviceName = _deviceNameMap[li.device_id] || li.device_id;
      var channels   = formatChannels(li.channel_mapping);

      // Status badge + toggle button
      var isEnabled = !!li.enabled;
      var $statusBadge = isEnabled
        ? $("<span>").addClass("label label-success").text(i18n.enabled)
        : $("<span>").addClass("label label-default")
                     .css({ color: "#888" }).text(i18n.disabled);

      var $toggleBtn = $("<button>")
        .addClass("btn btn-xs linein-toggle-btn")
        .attr("data-linein-id", li.id)
        .attr("data-enabled", isEnabled ? "1" : "0")
        .attr("title", isEnabled ? i18n.disableHint : i18n.enableHint)
        .css({ marginLeft: "0.4em" })
        .append($("<span>").addClass(isEnabled
          ? "ui-icon ui-icon-pause"
          : "ui-icon ui-icon-play"));

      var $statusCell = $("<td>").append($statusBadge).append($toggleBtn);

      // Action buttons: Edit + Delete
      var $editBtn = $("<button>")
        .addClass("btn btn-xs linein-edit-btn")
        .attr("data-linein-id", li.id)
        .attr("title", i18n.editHint)
        .append($("<span>").addClass("ui-icon ui-icon-pencil"));

      var $deleteBtn = $("<button>")
        .addClass("btn btn-xs btn-danger linein-delete-btn")
        .attr("data-linein-id", li.id)
        .attr("title", i18n.deleteHint)
        .css({ marginLeft: "0.3em" })
        .append($("<span>").addClass("ui-icon ui-icon-trash"));

      var $actionsCell = $("<td>").css({ whiteSpace: "nowrap" })
        .append($editBtn).append($deleteBtn);

      var $row = $("<tr>")
        .attr("data-linein-id", li.id)
        .append($("<td>").text(li.name))
        .append($("<td>").text(deviceName))
        .append($("<td>").text(channels))
        .append($("<td>").text(li.priority))
        .append($statusCell)
        .append($("<td>").text(li.description || ""))
        .append($actionsCell);

      $tbody.append($row);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* Populate device <select> in the dialog                                  */
  /* ---------------------------------------------------------------------- */

  function populateDeviceSelect(currentDeviceId) {
    var $sel = $("#linein-field-device");
    $sel.empty().append(
      $("<option>").val("").text(AIRTIME.linein.i18n.selectDevice)
    );
    $.each(_availableInputs, function (_, dev) {
      // RASTATIME 2026-05-14 — stash the OS friendly name on the option
      // as a data attribute so submitDialog can extract it cleanly even
      // when the visible text gets decorated (e.g. ⚠ prefix for missing
      // devices).  Backend persists this as ``device_name`` for the
      // resolver's name-based fallback after USB GUID re-enumeration.
      var $opt = $("<option>")
        .val(dev.stable_id)
        .text(dev.name)
        .attr("data-name", dev.name);
      if (dev.stable_id === currentDeviceId) { $opt.prop("selected", true); }
      $sel.append($opt);
    });
    // If current device is not in the list (missing hardware) add a warning opt
    if (currentDeviceId && !_deviceNameMap[currentDeviceId]) {
      $sel.prepend(
        $("<option>")
          .val(currentDeviceId)
          .text("⚠ " + AIRTIME.linein.i18n.missingDevice + ": " + currentDeviceId)
          .prop("selected", true)
      );
    }
  }

  /* ---------------------------------------------------------------------- */
  /* Dialog helpers                                                           */
  /* ---------------------------------------------------------------------- */

  function clearDialogErrors() {
    $("#linein-dialog-error").hide().text("");
  }

  function showDialogError(msg) {
    $("#linein-dialog-error").text(msg).show();
  }

  function openDialog(title, linein) {
    // linein is null when creating; populated when editing
    var isEdit = !!linein;

    clearDialogErrors();
    $("#linein-field-id").val(isEdit ? linein.id : "");
    $("#linein-field-name").val(isEdit ? linein.name : "");
    $("#linein-field-channels").val(
      isEdit ? (linein.channel_mapping || []).join(",") : ""
    );
    $("#linein-field-priority").val(isEdit ? linein.priority : 0);
    $("#linein-field-description").val(isEdit ? (linein.description || "") : "");
    $("#linein-field-enabled").prop("checked", isEdit ? !!linein.enabled : true);

    populateDeviceSelect(isEdit ? linein.device_id : "");

    var i18n = AIRTIME.linein.i18n;

    $("#linein-dialog")
      .dialog("option", "title", title)
      .dialog("option", "buttons", [
        {
          text: isEdit ? i18n.btnSave : i18n.btnCreate,
          click: function () { submitDialog(); }
        },
        {
          text: i18n.btnCancel,
          click: function () { $(this).dialog("close"); }
        }
      ])
      .dialog("open");
  }

  function submitDialog() {
    clearDialogErrors();

    var name    = $.trim($("#linein-field-name").val());
    var devId   = $("#linein-field-device").val();
    // RASTATIME 2026-05-14 — read the friendly name off the data
    // attribute (populateDeviceSelect set it) so we can persist it
    // alongside device_id.  Falls back to "" for the placeholder
    // option or any option that didn't get a data-name (e.g. legacy
    // missing-device warning rows).
    var devName = $("#linein-field-device option:selected").attr("data-name") || "";
    var chanStr = $.trim($("#linein-field-channels").val());
    var priority    = parseInt($("#linein-field-priority").val(), 10);
    var description = $.trim($("#linein-field-description").val());
    var enabled     = $("#linein-field-enabled").is(":checked");
    var lineinId    = $("#linein-field-id").val();
    var i18n = AIRTIME.linein.i18n;

    // --- client-side validation ---
    if (!name) {
      showDialogError(i18n.errNameRequired); return;
    }
    if (!devId) {
      showDialogError(i18n.errDeviceRequired); return;
    }
    var channels = parseChannels(chanStr);
    if (!channels) {
      showDialogError(i18n.errChannelsInvalid); return;
    }
    if (isNaN(priority)) { priority = 0; }

    var payload = {
      name:            name,
      device_id:       devId,
      device_name:     devName,
      channel_mapping: channels,
      priority:        priority,
      description:     description,
      enabled:         enabled,
    };

    var url, method;
    if (lineinId) {
      url    = "/linein/update/" + encodeURIComponent(lineinId);
      method = "POST";
      // Send only fields that are actually patchable
    } else {
      url    = "/linein/create";
      method = "POST";
    }

    $.ajax({
      url:         url,
      method:      method,
      contentType: "application/json",
      data:        JSON.stringify(payload),
      dataType:    "json",
    }).done(function (data) {
      if (data && data.error) {
        showDialogError(data.error);
        return;
      }
      $("#linein-dialog").dialog("close");
      showSuccess(lineinId ? i18n.savedOk : i18n.createdOk);
      reloadTable();
    }).fail(function (xhr) {
      var msg = i18n.saveError;
      try {
        var parsed = JSON.parse(xhr.responseText);
        if (parsed && parsed.error) { msg = parsed.error; }
      } catch (e) { /* ignore */ }
      showDialogError(msg);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* Delete                                                                   */
  /* ---------------------------------------------------------------------- */

  function deleteLinein(lineinId) {
    var i18n = AIRTIME.linein.i18n;
    if (!window.confirm(i18n.confirmDelete)) { return; }

    $.ajax({
      url:      "/linein/delete/" + encodeURIComponent(lineinId),
      // ``type``, not ``method`` — legacy LibreTime is locked to
      // jQuery 1.8.3 (see PageLayoutInitPlugin.php), which only
      // gained the ``method`` alias in jQuery 1.9.  With 1.8 the
      // ``method`` key is silently ignored and the request defaults
      // to GET.  RASTATIME-2026-05-12 fix (same root cause as the
      // soundcard-settings save bug).
      type:     "POST",
      dataType: "json",
    }).done(function (data) {
      if (data && data.success === false) {
        showError(i18n.deleteError);
        return;
      }
      showSuccess(i18n.deletedOk);
      reloadTable();
    }).fail(function () {
      showError(i18n.deleteError);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* Enable / Disable toggle                                                  */
  /* ---------------------------------------------------------------------- */

  function toggleEnabled(lineinId, currentlyEnabled) {
    var newEnabled = !currentlyEnabled;
    var i18n = AIRTIME.linein.i18n;

    $.ajax({
      url:          "/linein/update/" + encodeURIComponent(lineinId),
      // See delete handler above for the jQuery-1.8 ``type``-vs-``method`` rationale.
      type:         "POST",
      contentType:  "application/json",
      data:         JSON.stringify({ enabled: newEnabled }),
      processData:  false,
      dataType:     "json",
    }).done(function (data) {
      if (data && data.error) {
        showError(data.error);
        return;
      }
      // Patch the in-memory list so re-renders are consistent
      $.each(_lineIns, function (i, li) {
        if (li.id === lineinId) { _lineIns[i].enabled = newEnabled; }
      });
      renderTable(_lineIns);
      showSuccess(newEnabled ? i18n.enabledOk : i18n.disabledOk);
    }).fail(function () {
      showError(i18n.saveError);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* Table reload                                                             */
  /* ---------------------------------------------------------------------- */

  function reloadTable() {
    $.ajax({ url: "/api/v2/audio/linein", method: "GET", dataType: "json" })
      .done(function (data) {
        _lineIns = data.line_ins || [];
        renderTable(_lineIns);
      })
      .fail(function () {
        showError(AIRTIME.linein.i18n.loadError);
      });
  }

  /* ---------------------------------------------------------------------- */
  /* Bootstrap                                                                */
  /* ---------------------------------------------------------------------- */

  function init() {
    var i18n = AIRTIME.linein.i18n;

    // --- jQuery UI dialog setup ---
    $("#linein-dialog").dialog({
      autoOpen:  false,
      modal:     true,
      width:     480,
      resizable: false,
      close:     clearDialogErrors,
    });

    // --- Add button ---
    $("#linein-add-btn").on("click", function () {
      clearStatus();
      openDialog(i18n.titleNew, null);
    });

    // --- Delegated: Edit button ---
    $("#linein-tbody").on("click", ".linein-edit-btn", function () {
      clearStatus();
      var id = $(this).data("linein-id");
      var linein = null;
      $.each(_lineIns, function (_, li) {
        if (li.id === id) { linein = li; return false; }
      });
      if (!linein) { return; }
      openDialog(i18n.titleEdit, linein);
    });

    // --- Delegated: Delete button ---
    $("#linein-tbody").on("click", ".linein-delete-btn", function () {
      clearStatus();
      deleteLinein($(this).data("linein-id"));
    });

    // --- Delegated: Enable/Disable toggle ---
    $("#linein-tbody").on("click", ".linein-toggle-btn", function () {
      clearStatus();
      var id      = $(this).data("linein-id");
      var enabled = $(this).data("enabled") === "1" || $(this).data("enabled") === 1;
      toggleEnabled(id, enabled);
    });

    // --- Initial parallel fetch ---
    $.when(
      $.ajax({ url: "/api/v2/audio/devices", method: "GET", dataType: "json" }),
      $.ajax({ url: "/api/v2/audio/linein",  method: "GET", dataType: "json" })
    ).done(function (devResult, liResult) {
      var devicesData = devResult[0];
      var liData      = liResult[0];

      _deviceNameMap   = buildDeviceNameMap(devicesData);
      _availableInputs = buildInputList(devicesData);
      _lineIns         = liData.line_ins || [];

      renderTable(_lineIns);
    }).fail(function () {
      showError(i18n.loadError);
      $("#linein-tbody").empty().append(
        $("<tr>").append(
          $("<td>").attr("colspan", 7)
            .css({ color: "#c0392b", padding: "1.5em" })
            .text(i18n.loadError)
        )
      );
    });
  }

  /* ---------------------------------------------------------------------- */
  /* Localisation shims (overridden by the PHP i18n layer when available)    */
  /* ---------------------------------------------------------------------- */

  if (!window.AIRTIME)        { window.AIRTIME = {}; }
  if (!AIRTIME.linein)        { AIRTIME.linein = {}; }
  if (!AIRTIME.linein.i18n) {
    AIRTIME.linein.i18n = {
      // table
      noEntries:     "No line-in sources configured yet.",
      loadError:     "Could not load line-in sources from the server.",
      enabled:       "Enabled",
      disabled:      "Disabled",
      // dialog titles
      titleNew:      "New Line-In Source",
      titleEdit:     "Edit Line-In Source",
      // dialog buttons
      btnCreate:     "Create",
      btnSave:       "Save",
      btnCancel:     "Cancel",
      // dialog select
      selectDevice:  "— select device —",
      missingDevice: "Device not found",
      // validation
      errNameRequired:    "Name is required.",
      errDeviceRequired:  "Please select an input device.",
      errChannelsInvalid: "Channel mapping must be comma-separated non-negative integers (e.g. 0,1).",
      // action hints
      editHint:    "Edit",
      deleteHint:  "Delete",
      enableHint:  "Enable",
      disableHint: "Disable",
      // success / error toasts
      createdOk:  "Line-in source created.",
      savedOk:    "Line-in source updated.",
      deletedOk:  "Line-in source deleted.",
      enabledOk:  "Line-in source enabled.",
      disabledOk: "Line-in source disabled.",
      confirmDelete: "Delete this line-in source? This cannot be undone.",
      saveError:   "Could not save changes. Please try again.",
      deleteError: "Could not delete the line-in source.",
    };
  }

  $(document).ready(init);

}(jQuery));
