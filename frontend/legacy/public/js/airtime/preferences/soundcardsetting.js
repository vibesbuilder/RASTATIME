/**
 * T13.2 / T13.3 — Soundcard settings page JavaScript.
 *
 * Loads device inventory from GET /api/v2/audio/devices and persisted
 * settings from GET /api/v2/audio/soundcard-settings, then wires the
 * dropdowns and Save button.
 *
 * T13.3 addition: the settings response includes a ``missing_device_ids``
 * array.  Any configured device whose stable ID appears in that array is
 * currently unavailable (unplugged / driver removed).  These IDs are
 * highlighted with a warning option in the relevant dropdown and with a
 * "⚠" badge next to the corresponding line-in entry in the configured list.
 */

(function ($) {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Internal state                                                       */
  /* ------------------------------------------------------------------ */

  /** @type {string[]} Ordered list of stable IDs currently in the "configured line-ins" box. */
  var lineInIds = [];

  /** @type {Array<{stable_id: string, name: string}>} All available input devices. */
  var availableInputs = [];

  /** @type {string[]} Stable IDs that are configured but currently unavailable. */
  var missingDeviceIds = [];

  /* ------------------------------------------------------------------ */
  /* Helpers                                                              */
  /* ------------------------------------------------------------------ */

  function showStatus(html, isError) {
    var cls = isError ? "errors" : "success";
    $("#soundcard-status-msg").html(
      "<div class='" + cls + "'>" + html + "</div>"
    );
  }

  function clearStatus() {
    $("#soundcard-status-msg").empty();
  }

  function isMissing(stableId) {
    return missingDeviceIds.indexOf(stableId) !== -1;
  }

  /**
   * Populate a <select> with device options.
   *
   * @param {string}  selectId   The element id (without #).
   * @param {Array}   devices    Array of {stable_id, name} objects.
   * @param {boolean} addNone    Prepend an empty "none" option.
   * @param {string}  currentId  stable_id to pre-select (may be "").
   */
  function fillSelect(selectId, devices, addNone, currentId) {
    var $sel = $("#" + selectId);
    // RASTATIME 2026-11-02 - options the page marks data-permanent (the
    // "Off - stream only" choice, value "none") survive the fill and sit
    // right after the "None" (system default) entry.
    var $permanent = $sel.find("option[data-permanent]").detach();
    $sel.empty();

    if (addNone) {
      $sel.append($("<option>").val("").text("— " + AIRTIME.i18n.none + " —"));
    }
    $sel.append($permanent);

    $.each(devices, function (_, dev) {
      // RASTATIME 2026-05-14 — B.4 #4 output side: stash friendly name
      // on each option as data-attr so the save handler can persist
      // it as main_output_name / preview_output_name for the playout's
      // post-reboot name-fallback resolver.
      $sel.append(
        $("<option>")
          .val(dev.stable_id)
          .text(dev.name)
          .attr("data-name", dev.name)
      );
    });

    if (currentId) {
      if ($sel.find("option[value='" + currentId + "']").length) {
        $sel.val(currentId);
      } else {
        /* Device is missing — inject a warning option */
        var $warn = $("<option>")
          .val(currentId)
          .text("⚠ " + AIRTIME.i18n.deviceMissing + ": " + currentId)
          .css({ color: "#c0392b", fontStyle: "italic" });
        $sel.prepend($warn);
        $sel.val(currentId);
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Line-in list rendering                                               */
  /* ------------------------------------------------------------------ */

  function nameForId(id) {
    var found = null;
    $.each(availableInputs, function (_, dev) {
      if (dev.stable_id === id) {
        found = dev.name;
        return false; // break
      }
    });
    return found || id;
  }

  function renderLineInList() {
    var $ul = $("#soundcard-line-in-list");
    $ul.empty();

    if (lineInIds.length === 0) {
      $ul.append(
        $("<li>").css({ color: "#888", fontStyle: "italic" })
          .text(AIRTIME.i18n.noLineInsConfigured)
      );
      return;
    }

    $.each(lineInIds, function (_, id) {
      var missing = isMissing(id);
      var $li = $("<li>").css({ marginBottom: "4px" });

      var label = nameForId(id);
      if (missing) {
        label = "⚠ " + label + " (" + AIRTIME.i18n.deviceMissing + ")";
        $li.css({ color: "#c0392b", fontStyle: "italic" });
      }
      $li.text(label + " ");

      var $btn = $("<button>")
        .attr("type", "button")
        .addClass("btn btn-mini")
        .text("✕")
        .css({ marginLeft: "6px" })
        .data("id", id)
        .on("click", function () {
          var removeId = $(this).data("id");
          lineInIds = lineInIds.filter(function (x) { return x !== removeId; });
          renderLineInList();
        });
      $li.append($btn);
      $ul.append($li);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Bootstrap: load devices then settings                               */
  /* ------------------------------------------------------------------ */

  function applySettings(cfg, outputs) {
    missingDeviceIds = cfg.missing_device_ids || [];

    /* Apply main output */
    fillSelect("soundcard-main-output", outputs, true, cfg.main_output_id || "");
    // RASTATIME 2026-10-27 - the select now shows the stored device
    if (pageSection) { RtPageSave.markSaved(pageSection); }
    /* RASTATIME: preview output dropdown removed earlier; line-in list
     * moved to the Media Library (Phase A.4).  Server-side persistence
     * of both fields stays intact so they can be reinstated later. */

    /* Banner if any device is missing — only main_output now, line-in
     * device availability is surfaced in the Library row instead. */
    if (missingDeviceIds.length > 0) {
      showStatus(
        AIRTIME.i18n.devicesMissing.replace("{n}", missingDeviceIds.length),
        true
      );
    }
  }

  function init() {
    // RASTATIME 2026-10-25 (role audit S4) - through the PHP proxies
    // (Admin, CSRF on save); /api/v2/audio/* answers internal callers only.
    $.ajax({
      url: baseUrl + "preference/audio-devices",
      type: "GET",
      dataType: "json",
      success: function (data) {
        var outputs = data.outputs || [];

        /* RASTATIME 2026-05-12 — Phase A.4 cleanup: line-in
         * input list moved to the Media Library, no input-dropdown
         * population needed here anymore. */

        /* Load saved settings */
        $.ajax({
          url: baseUrl + "preference/soundcard-settings",
          type: "GET",
          dataType: "json",
          success: function (cfg) {
            applySettings(cfg, outputs);
          },
          error: function () {
            /* Settings not saved yet — fill dropdowns with no selection */
            fillSelect("soundcard-main-output", outputs, true, "");
            if (pageSection) { RtPageSave.markSaved(pageSection); }
          },
        });
      },
      error: function () {
        showStatus(AIRTIME.i18n.deviceLoadError, true);
      },
    });
  }

  /* ------------------------------------------------------------------ */
  /* Save - RASTATIME 2026-10-27: a section of the page's single Save    */
  /* (pagesave.js), posted only when the main output changed            */
  /* ------------------------------------------------------------------ */
  function saveSoundcard() {
    var done = $.Deferred();
    clearStatus();

    // ``preview_output_id`` and ``line_in_device_ids`` intentionally
    // omitted — both UI sections were removed (Phase A.4 line-in
    // moved to Media Library; preview dropdown removed earlier).
    // The POST API ignores absent keys, so any previously stored
    // values stay intact in case the panels get reinstated later.
    //
    // RASTATIME 2026-05-14 — also persist ``main_output_name`` from
    // the selected option's data-name attribute (fillSelect set it).
    // Used by the playout startup resolver as a friendly-name
    // fallback when the saved main_output_id stops resolving after
    // a USB-reshuffle reboot.  Empty string is fine — fallback then
    // just degrades to "no name to match against".
    var $selOpt = $("#soundcard-main-output option:selected");
    var payload = {
      main_output_id:   $("#soundcard-main-output").val() || null,
      main_output_name: $selOpt.attr("data-name") || "",
    };

    $.ajax({
      url: baseUrl + "preference/soundcard-settings",
      // RASTATIME 2026-05-12: must be ``type``, NOT ``method``.
      // Legacy LibreTime ships jQuery 1.8.3 globally (loaded by
      // PageLayoutInitPlugin.php on every page), and the ``method``
      // alias for ``type`` only exists since jQuery 1.9.  In 1.8
      // ``method: "POST"`` is silently ignored and the request
      // defaults to GET — with the JSON body URL-encoded onto the
      // querystring, returning 200 OK but never persisting anything.
      type: "POST",
      // RASTATIME 2026-10-25 - form fields for the PHP proxy, which
      // checks the CSRF token and forwards JSON to the API.
      data: $.extend({ csrf_token: $("#csrf").val() }, payload, {
        main_output_id: payload.main_output_id || "",
      }),
      success: function (cfg) {
        /* Re-apply with updated missing_device_ids from POST response.
         * (Line-in list rendering removed in Phase A.4 — line-ins
         * are managed in the Media Library now.) */
        missingDeviceIds = cfg.missing_device_ids || [];
        showStatus(AIRTIME.i18n.soundcardSaved, false);
        done.resolve();
      },
      error: function (xhr) {
        var msg = AIRTIME.i18n.soundcardSaveError;
        try {
          var body = JSON.parse(xhr.responseText);
          if (body.error) { msg = body.error; }
        } catch (e) { /* ignore */ }
        showStatus(msg, true);
        done.reject();
      },
    });
    return done.promise();
  }

  var pageSection = window.RtPageSave
    ? RtPageSave.register("soundcard", "#soundcard-main-output", saveSoundcard)
    : null;

  /* ------------------------------------------------------------------ */
  /* Localisation shims (filled by PHP or i18n pipeline)                */
  /* ------------------------------------------------------------------ */

  if (!window.AIRTIME) { window.AIRTIME = {}; }
  if (!AIRTIME.i18n) {
    AIRTIME.i18n = {
      none:                  "None",
      noLineInsConfigured:   "No line-in devices configured.",
      deviceLoadError:       "Could not load device list from the server.",
      deviceMissing:         "Device not found",
      devicesMissing:        "{n} configured device(s) are currently unavailable. " +
                             "Check connections or reconfigure.",
      soundcardSaved:        "Local Machine settings saved.",
      soundcardSaveError:    "Could not save Local Machine settings.",
    };
  }

  $(document).ready(init);

}(jQuery));
