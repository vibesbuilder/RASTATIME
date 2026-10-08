function showErrorSections() {
  $(".errors").each(function (i) {
    if ($(this).length > 0) {
      var div = $(this).closest("div");
      if (div.attr("class") == "stream-setting-content") {
        $(this).closest("div").show();
        $(this).closest("fieldset").removeClass("closed");
        $(window).scrollTop($(this).closest("div").position().top);
      }
    }
  });
  // RASTATIME 2026-10-08 - the Audio Processing segment starts collapsed; it
  // opens when it holds a validation error, so the red hint is not hidden.
  $(".collapsible-content").each(function () {
    if ($(this).find(".errors").length > 0) {
      $(this).show();
      $(this).prev(".collapsible-header").removeClass("closed");
    }
  });
}
function restrictOggBitrate(ele, on) {
  var div = ele.closest("div");
  if (on) {
    if (parseInt(div.find("select[id$=data-bitrate]").val(), 10) < 48) {
      div
        .find("select[id$=data-bitrate]")
        .find("option[value='48']")
        .attr("selected", "selected");
    }
    div
      .find("select[id$=data-bitrate]")
      .find("option[value='24']")
      .attr("disabled", "disabled");
    div
      .find("select[id$=data-bitrate]")
      .find("option[value='32']")
      .attr("disabled", "disabled");
  } else {
    div
      .find("select[id$=data-bitrate]")
      .find("option[value='24']")
      .removeAttr("disabled");
    div
      .find("select[id$=data-bitrate]")
      .find("option[value='32']")
      .removeAttr("disabled");
  }
}

// Opus only accepts 48 kHz (libopus rejects 44.1 kHz).  When the user
// selects Opus, force the Sample Rate dropdown to 48000 and disable the
// 44100 option so it cannot be saved.  When switching away from Opus,
// re-enable 44100 — the user may want it again for MP3/Vorbis/AAC.
function restrictOpusSamplerate(ele, on) {
  var div = ele.closest("div");
  var sr  = div.find("select[id$=data-samplerate]");
  if (on) {
    sr.val("48000");
    sr.find("option[value='44100']").attr("disabled", "disabled");
  } else {
    sr.find("option[value='44100']").removeAttr("disabled");
  }
}
function hideForShoutcast(ele) {
  var div = ele.closest("div");
  div.find("#outputMountpoint-label").hide();
  div.find("#outputMountpoint-element").hide();
  div.find("#outputUser-label").hide();
  div.find("#outputUser-element").hide();
  div
    .find("select[id$=data-type]")
    .find("option[value='mp3']")
    .attr("selected", "selected");
  div
    .find("select[id$=data-type]")
    .find("option[value='ogg']")
    .attr("disabled", "disabled");
  div
    .find("select[id$=data-type]")
    .find("option[value='opus']")
    .attr("disabled", "disabled");

  restrictOggBitrate(ele, false);
}

function validate(ele, evt) {
  var theEvent = evt || window.event;
  var key = theEvent.keyCode || theEvent.which;
  if (
    (ele.val().length >= 5 || key < 48 || key > 57) &&
    !(key == 8 || key == 9 || key == 13 || key == 37 || key == 39 || key == 46)
  ) {
    theEvent.returnValue = false;
    if (theEvent.preventDefault) theEvent.preventDefault();
  }
}

function showForIcecast(ele) {
  var div = ele.closest("div");
  div.find("#outputMountpoint-label").show();
  div.find("#outputMountpoint-element").show();
  div.find("#outputUser-label").show();
  div.find("#outputUser-element").show();
  div
    .find("select[id$=data-type]")
    .find("option[value='ogg']")
    .removeAttr("disabled");
  div
    .find("select[id$=data-type]")
    .find("option[value='opus']")
    .removeAttr("disabled");
}

function checkLiquidsoapStatus() {
  var url = baseUrl + "Preference/get-liquidsoap-status/format/json";
  $.post(url, function (json_obj) {
    var keepPolling = false;
    var pollDelay   = 5000;   // default: re-check every 5 s

    for (var i = 0; i < json_obj.length; i++) {
      var obj = json_obj[i];
      var id, status;
      for (var key in obj) {
        if (key == "id")     { id     = obj[key]; }
        if (key == "status") { status = obj[key]; }
      }
      var html;
      if (status == "OK") {
        // Icecast running + mount point active — VLC is streaming
        html = '<div class="stream-status status-good"><p>' +
               $.i18n._("Connected to the streaming server") +
               "</p></div>";
        keepPolling = true;
        pollDelay   = 5000;
      } else if (status == "N/A") {
        // Stream disabled — nothing to do
        html = '<div class="stream-status status-disabled"><p>' +
               $.i18n._("The stream is disabled") +
               "</p></div>";
      } else if (status == "waiting") {
        // RASTATIME: Icecast not reachable (service not started or wrong port/host)
        html = '<div class="stream-status status-info"><p>' +
               $.i18n._("Icecast is not running. Start the RASTATIME-ICECAST service.") +
               "</p></div>";
        keepPolling = true;
        pollDelay   = 10000;  // retry every 10 s — no point hammering a stopped service
      } else if (status == "inactive") {
        // RASTATIME: Icecast is up, mount not yet active — VLC not streaming yet
        html = '<div class="stream-status status-info"><p>' +
               $.i18n._("Icecast is running. Start RASTATIME-PLAYOUT and schedule content to go live.") +
               "</p></div>";
        keepPolling = true;
        pollDelay   = 5000;   // check every 5 s to detect stream coming up
      } else {
        // Unexpected error string returned by the server
        html = '<div class="stream-status status-error"><p>' +
               $.i18n._("Cannot connect to the streaming server") +
               "</p><p>" + status + "</p></div>";
        keepPolling = true;
        pollDelay   = 5000;
      }
      $("#s" + id + "Liquidsoap-error-msg-element").html(html);
    }

    if (keepPolling) {
      setTimeout(checkLiquidsoapStatus, pollDelay);
    }
  });
}

function setupEventListeners() {
  if (!$("#output_sound_device").is(":checked")) {
    $("select[id=output_sound_device_type]").attr("disabled", "disabled");
  } else {
    $("select[id=output_sound_device_type]").removeAttr("disabled");
  }

  $("#output_sound_device").change(function () {
    if ($(this).is(":checked")) {
      $("select[id=output_sound_device_type]").removeAttr("disabled");
    } else {
      $("select[id=output_sound_device_type]").attr("disabled", "disabled");
    }
  });

  $("select[id$=data-type]").change(function () {
    if ($(this).val() == "ogg") {
      restrictOggBitrate($(this), true);
    } else {
      restrictOggBitrate($(this), false);
    }
    // Opus → force 48 kHz; everything else → unlock 44.1 kHz again
    restrictOpusSamplerate($(this), $(this).val() == "opus");
  });

  $("select[id$=data-type]").each(function () {
    if ($(this).val() == "ogg") {
      restrictOggBitrate($(this), true);
    }
    if ($(this).val() == "opus") {
      restrictOpusSamplerate($(this), true);
    }
  });

  $("select[id$=data-output]").change(function () {
    if ($(this).val() == "shoutcast") {
      hideForShoutcast($(this));
    } else {
      showForIcecast($(this));
    }
  });

  $("select[id$=data-output]").each(function () {
    if ($(this).val() == "shoutcast") {
      hideForShoutcast($(this));
    }
  });

  $(".toggle legend").click(function () {
    $(this).parent().toggleClass("closed");
    return false;
  });

  $(".collapsible-header").click(function () {
    $(this).next().toggle("fast");
    $(this).toggleClass("closed");
    return false;
  });

  showErrorSections();
  checkLiquidsoapStatus();

  var userManualAnchorOpen =
    "<a target='_blank' href='" + USER_MANUAL_URL + "'>";

  // qtip for help text
  $(".override_help_icon").rtTooltip({
    content: {
      text:
        sprintf(
          $.i18n._(
            "If %s is behind a router or firewall, you may need to configure port forwarding and this field information will be incorrect. In this case you will need to manually update this field so it shows the correct host/port/mount that your DJ's need to connect to. The allowed range is between 1024 and 49151.",
          ),
          PRODUCT_NAME,
        ) +
        " " +
        sprintf(
          $.i18n._("For more details, please read the %s%s Manual%s"),
          userManualAnchorOpen,
          PRODUCT_NAME,
          "</a>",
        ),
    },
    placement: "right",
    interactive: true,
  });

  $(".icecast_metadata_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "Check this option to enable metadata for OGG streams (stream metadata is the track title, artist, and show name that is displayed in an audio player). VLC and mplayer have a serious bug when playing an OGG/VORBIS stream that has metadata information enabled: they will disconnect from the stream after every song. If you are using an OGG stream and your listeners do not require support for these audio players, then feel free to enable this option.",
      ),
    },
    placement: "right",
    interactive: true,
  });

  // RASTATIME 2026-05-14: auto_transition / auto_switch qtip help
  // popovers removed alongside their UI checkboxes — see
  // application/forms/LiveStreamingPreferences.php for the rationale.

  $(".stream_username_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "If your Icecast server expects a username of 'source', this field can be left blank.",
      ),
    },
    placement: "right",
    interactive: true,
  });

  $(".admin_username_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "This is the admin username and password for Icecast/SHOUTcast to get listener statistics.",
      ),
    },
    placement: "right",
    interactive: true,
  });

  $(".master_username_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "If your live streaming client does not ask for a username, this field should be 'source'.",
      ),
    },
    placement: "right",
    interactive: true,
  });

  $(".stream_type_help_icon").rtTooltip({
    content: {
      text: sprintf(
        $.i18n._(
          "Some stream types require extra configuration. Details about enabling %sAAC+ Support%s or %sOpus Support%s are provided.",
        ),
        "<a target='_blank' href='https://wiki.sourcefabric.org/x/NgPQ'>",
        "</a>",
        "<a target='_blank' href='https://wiki.sourcefabric.org/x/KgPQ'>",
        "</a>",
      ),
    },
    placement: "right",
    interactive: true,
  });

  setupHelpIcons();
}

// RASTATIME 2026-09-28 - Switch Transition Fade: explanation as a help
// icon next to the field, like the Master Source username below it.
// 2026-10-02: the Output Processing (Stereo Tool) checkbox as well; its
// path and licence fields sit below their label, so their icon goes
// right of the label text instead.
// 2026-10-08: called from setupEventListeners, so the icons come back after a
// save re-renders the form (they were plain paragraphs again before).
function setupHelpIcons() {
  $.rtDescriptionTooltips($(".stream-setting-global"), {
    where: "field",
    only: [
      "transition_fade",
      "loudnessMode",
      "loudnessTarget",
      "loudnessTruePeak",
      "loudnessMeasure",
      "stereotoolEnabled",
    ],
  });
  $.rtDescriptionTooltips($(".stream-setting-global"), {
    where: "label",
    only: ["stereotoolLibrary", "stereotoolPreset", "stereotoolLicenseKey"],
  });
  setupLegendHelpIcons();
}

// RASTATIME 2026-10-08 - Live Broadcasting (operator): the intro line of each
// block (DJ Hand-over, Master Source, Show Source) becomes a help icon right
// of the block title.
function setupLegendHelpIcons() {
  $("p.legend-help").each(function () {
    var p = $(this);
    var legend = p.siblings("legend").first();
    var text = $.trim(p.text());
    if (!legend.length || !text) {
      return;
    }
    p.remove();
    var icon = $('<span class="help_icon"></span>');
    legend.append(icon);
    icon.rtTooltip({
      content: { text: $("<div>").text(text).html() },
      placement: "right",
      interactive: true,
    });
  });
}

function setSliderForReplayGain() {
  $("#slider-range-max").slider({
    range: "max",
    min: -10,
    max: 10,
    value: $("#rg_modifier_value").html(),
    slide: function (event, ui) {
      $("#replayGainModifier").val(ui.value);
      $("#rg_modifier_value").html(ui.value);
    },
  });
  $("#replayGainModifier").val($("#slider-range-max").slider("value"));
}

// RASTATIME 2026-09-28 - Loudness Normalization (EBU R128, stage 1): show
// the fields of the chosen mode, and queue the library for measurement.
function setLoudnessModeFields() {
  var mode = $("#loudnessMode").val();
  $(".loudness-replaygain-field").toggle(mode === "replaygain");
  $(".loudness-r128-field").toggle(mode === "r128");
}

// RASTATIME 2026-10-02 - Output Processing (Stereo Tool): the path and
// licence fields only when the checkbox is on.
function setStereoToolFields() {
  $(".stereotool-field").toggle($("#stereotoolEnabled").is(":checked"));
}

function setupLoudnessListeners() {
  $("#stereotoolEnabled").off("change.stereotool").on("change.stereotool", setStereoToolFields);
  setStereoToolFields();
  $("#loudnessMode").off("change.loudness").on("change.loudness", setLoudnessModeFields);
  $(document)
    .off("click.loudness", "#loudness_measure_btn, #loudness_remeasure_btn")
    .on("click.loudness", "#loudness_measure_btn, #loudness_remeasure_btn", function () {
      var force = this.id === "loudness_remeasure_btn" ? 1 : 0;
      if (force && !confirm($.i18n._("Re-measure every file in the library? This queues all files for the analyzer."))) {
        return;
      }
      var $status = $("#loudness_measured_status");
      $status.text($.i18n._("Queuing..."));
      $.post(
        baseUrl + "Preference/remeasure-loudness",
        { csrf_token: $("#csrf").val(), force: force },
        function (json) {
          if (json && json.queued !== undefined) {
            $status.text(
              $.i18n._("Queued %s files for measurement; reload the page to see the count.").replace("%s", json.queued),
            );
          } else {
            $status.text($.i18n._("Could not queue the measurement."));
          }
        },
        "json",
      ).fail(function () {
        $status.text($.i18n._("Could not queue the measurement."));
      });
    });
}

function setPseudoAdminPassword(s1, s2, s3, s4) {
  if (s1) {
    $("#s1_data-admin_pass").val("xxxxxx");
  }
  if (s2) {
    $("#s2_data-admin_pass").val("xxxxxx");
  }
  if (s3) {
    $("#s3_data-admin_pass").val("xxxxxx");
  }
  if (s4) {
    $("#s4_data-admin_pass").val("xxxxxx");
  }
}

function getAdminPasswordStatus() {
  $.ajax({
    url: baseUrl + "Preference/get-admin-password-status/format/json",
    dataType: "json",
    success: function (data) {
      setPseudoAdminPassword(data.s1, data.s2, data.s3, data.s4);
    },
  });
}

$(document).ready(function () {
  setupEventListeners();
  setSliderForReplayGain();
  getAdminPasswordStatus();

  setLoudnessModeFields();
  setupLoudnessListeners();
  var s = $("[name^='customStreamSettings']:checked");

  $(document).on(
    "click",
    "[id^='stream_save'], [name^='customStreamSettings']",
    function () {
      var e = $(this);
      if (e[0] == s[0]) {
        return;
      }
      var data = $("#stream_form").serialize();
      var url = baseUrl + "Preference/stream-setting";

      $.post(url, { format: "json", data: data }, function (json) {
        $("#content").empty().append(json.html);
        if (json.valid) {
          window.location.reload();
        }
        setupEventListeners();
        setSliderForReplayGain();
        getAdminPasswordStatus();
        setLoudnessModeFields();
        setupLoudnessListeners();
      });
    },
  );
});
