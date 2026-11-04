/**
 *
 *    Schedule Dialog creation methods.
 *
 */

// Init Day.JS plugins
dayjs.extend(window.dayjs_plugin_utc);
dayjs.extend(window.dayjs_plugin_timezone);

// RASTATIME 2026-10-23 - collapse the advanced sections (the list the
// open path used since 2026-05-19, Repeat since 2026-10-21).  A function
// so the redraw after a close runs it too: closeAddShowForm fetches a fresh
// form asynchronously, and opened again before it arrived the new markup
// came up with every section expanded (operator).
function collapseAddShowSections() {
  $("#schedule-show-templates").hide();
  $("#schedule-show-repeat").hide();
  $("#schedule-show-auto").hide();
  $("#live-stream-override").hide();
  $("#schedule-show-record").hide();
  $("#schedule-record-rebroadcast").hide();
  $("#schedule-show-who").hide();
  $("#schedule-show-style").hide();
  // RASTATIME 2026-11-03 - Archiving comes up collapsed too (operator)
  $("#schedule-show-archiving").hide();
}

function openAddShowForm(nowOrFuture) {
  if ($("#add-show-form").length == 1) {
    if ($("#add-show-form").css("display") == "none") {
      if (nowOrFuture === true) {
        //true means "now"
        $("#add_show_start_now-now").prop("checked", true);
        setupStartTimeWidgets();
      }
      $("#add-show-form").show();

      windowResize();

      // collapse advanced configuration sections
      // RASTATIME 2026-05-19 — added #schedule-show-templates (new
      // Templates collapsible) and #schedule-show-record (the
      // Record section's real id; the legacy selector
      // #schedule-record-rebroadcast targets the rebroadcast-only
      // sub-container which no longer exists at the top level since
      // Section 23.13's record-per-show refactor — it stayed in the
      // list as a no-op).  Operator request 2026-05-19: Record and
      // Templates should both come up collapsed by default, in line
      // with Autoloading Playlist / Live Stream Input / Who / Style.
      collapseAddShowSections();
    }
    $("#schedule-show-what").show(0, function () {
      $add_show_name = $("#add_show_name");
      $add_show_name.focus();
      $add_show_name.select();
    });
  }
}

function makeAddShowButton() {
  if ($(".add-button").length === 0) {
    var space = '<span class="fc-header-space"></span>';
    var btn =
      '<span class="btn-group">' +
      '<button onclick="showForm()" class="add-button btn btn-small btn-new">' +
      '<i class="icon-white icon-plus"></i>' +
      "<span>" +
      $.i18n._("New Show") +
      "</span>" +
      "</button>" +
      "</span>";
    // FC1.5 header is .fc-header-left; FC6 (?fc6=1) uses the left toolbar chunk
    var $target = window.SCHEDULE_USE_FC6
      ? $("#schedule_calendar .fc-toolbar-chunk").first()
      : $(".fc-header-left");
    $target.prepend(space).prepend(btn);
  }
}

function showForm() {
  openAddShowForm(true);
  toggleAddShowButton();
}

function toggleAddShowButton() {
  var aTag = $(".add-button");
  aTag.prop("disabled", function (i, v) {
    return !v;
  });
}

function setupStartTimeWidgets() {
  if ($("input[name=add_show_start_now]:checked").val() == "now") {
    $("#add_show_start_date").prop("disabled", "true");
    $("#add_show_start_time").prop("disabled", "true");
    var currentTimezone = $("#add_show_timezone").val();

    //Set the show start time to now (in the show timezone)
    var now = dayjs(new Date()).tz(currentTimezone);
    $("#add_show_start_date").val(now.format("YYYY-MM-DD"));
    $("#add_show_start_time").val(now.format("HH:mm"));

    //Set the show end time to be now + 1 hour.
    var nowShowEnd = now.add(1, "h");
    $("#add_show_end_date").val(nowShowEnd.format("YYYY-MM-DD"));
    $("#add_show_end_date_no_repeat").val(nowShowEnd.format("YYYY-MM-DD"));
    $("#add_show_end_time").val(nowShowEnd.format("HH:mm"));

    //Disabled linked show option since user won't be able to schedule
    //content
    $("#add_show_linked").prop("disabled", "true").data("rtNowDisabled", true);
  } else {
    //Do not enable start date and time option when a show has already started
    // RASTATIME 2026-10-23 - prop("disabled", false), not removeProp():
    // removeProp() leaves the native boolean property undefined and the
    // browser kept the fields disabled after "Now" -> "In the future"
    // (operator); the linked box follows when "Now" had disabled it
    if (!$("#add_show_start_now-now").prop("disabled")) {
      $("#add_show_start_date").prop("disabled", false);
      $("#add_show_start_time").prop("disabled", false);
      if ($("#add_show_linked").data("rtNowDisabled")) {
        $("#add_show_linked").prop("disabled", false).removeData("rtNowDisabled");
      }
    }
  }
}

function calculateShowColor() {
  var bgColorEle = $("#add_show_background_color");
  var textColorEle = $("#add_show_color");
  var colorCode = stringToColor($("#add_show_start_time").val()); //$(this).val());
  //bgColorEle.val(colorCode);
  //textColorEle.val(getContrastYIQ(colorCode));
}

//$el is DOM element #add-show-form
//form is the new form contents to append to $el
function redrawAddShowForm($el, form) {
  //need to clean up the color picker.
  $el.find("#schedule-show-style input").each(function (i, el) {
    var $input = $(this),
      colId = $input.data("colorpickerId");

    $("#" + colId).remove();
    $input.removeData();
  });

  $el.empty().append(form);

  setAddShowEvents($el);
  // RASTATIME 2026-10-23 - a redrawn form starts with the advanced
  // sections collapsed like a freshly opened one (a validation redraw
  // reopens the sections with errors right after, showErrorSections)
  collapseAddShowSections();
}

function closeAddShowForm(event) {
  event.stopPropagation();
  event.preventDefault();

  var $el = $("#add-show-form");

  $el.hide();
  windowResize();

  $.get(baseUrl + "Schedule/get-form", { format: "json" }, function (json) {
    redrawAddShowForm($el, json.form);
  });

  toggleAddShowButton();
}

//dateText mm-dd-yy
function startDpSelect(dateText, inst) {
  var time, date;

  time = dateText.split("-");
  date = new Date(time[0], time[1] - 1, time[2]);

  if (inst.input) inst.input.trigger("input");
}

function endDpSelect(dateText, inst) {
  var time, date;

  time = dateText.split("-");
  date = new Date(time[0], time[1] - 1, time[2]);

  if (inst.input) inst.input.trigger("input");
}

function createDateInput(el, onSelect) {
  var date;

  el.datepicker({
    minDate: adjustDateToServerDate(new Date(), timezoneOffset),
    onSelect: onSelect,
    dateFormat: "yy-mm-dd",
    //i18n_months, i18n_days_short are in common.js
    monthNames: i18n_months,
    dayNamesMin: i18n_days_short,
    closeText: $.i18n._("Close"),
    //showButtonPanel: true,
    firstDay: calendarPref.weekStart,
  });
}

function autoSelect(event, ui) {
  $("#add_show_hosts-" + ui.item.index).prop("checked", true);
  event.preventDefault();
}

function findHosts(request, callback) {
  var search, url;

  url = baseUrl + "User/get-hosts";
  search = request.term;

  var noResult = new Array();
  noResult[0] = new Array();
  noResult[0]["value"] = $("#add_show_hosts_autocomplete").val();
  noResult[0]["label"] = $.i18n._("No result found");
  noResult[0]["index"] = null;

  $.post(
    url,
    { format: "json", term: search },

    function (json) {
      if (json.hosts.length < 1) {
        callback(noResult);
      } else {
        callback(json.hosts);
      }
    },
  );
}

function beginEditShow(data) {
  if (data.show_error == true) {
    alertShowErrorAndReload();
    return false;
  }

  redrawAddShowForm($("#add-show-form"), data.newForm);
  toggleAddShowButton();
  openAddShowForm(false);
}

function onStartTimeSelect() {
  $("#add_show_start_time").trigger("input");
}

function onEndTimeSelect() {
  $("#add_show_end_time").trigger("input");
}

function padZeroes(number, length) {
  var str = "" + number;
  while (str.length < length) {
    str = "0" + str;
  }
  return str;
}

function hashCode(str) {
  // java String#hashCode
  var hash = 0;
  for (var i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return hash;
}

function intToRGB(i) {
  return (
    padZeroes(((i >> 16) & 0xff).toString(16), 2) +
    padZeroes(((i >> 8) & 0xff).toString(16), 2) +
    padZeroes((i & 0xff).toString(16), 2)
  );
}

function stringToColor(s) {
  var palette = [
    "42d5a1",
    "56bd99",
    "65ab93",
    "7b938b",
    "42a4d5",
    "569bbd",
    "6594ab",
    "7b8b93",
    "4264d5",
    "566fbd",
    "6576ab",
    "7b8193",
  ];
  //var palette = ['d56f42', 'aad542', '7242d5', '42d563', 'd542be'];
  return palette[Math.abs(hashCode(s)) % palette.length];
  //return intToRGB(hashCode(s));
}

function getContrastYIQ(hexcolor) {
  var r = parseInt(hexcolor.substr(0, 2), 16);
  var g = parseInt(hexcolor.substr(2, 2), 16);
  var b = parseInt(hexcolor.substr(4, 2), 16);
  var yiq = (r * 299 + g * 587 + b * 114) / 1000;
  return yiq >= 128 ? "000000" : "ffffff";
}

function setAddShowEvents(form) {
  //var form = $("#add-show-form");

  form.find("h3").click(function () {
    $(this).next().toggle();
  });
  // RASTATIME 2026-11-04 - measured once the section is open (after the toggle above)
  form
    .find("#schedule-show-archiving")
    .prev("h3")
    .click(function () {
      syncArchivingWidths(form);
    });

  form.find("input:radio[name=add_show_start_now]").click(function () {
    setupStartTimeWidgets();

    if ($(this).val() == "future") {
      $("#add_show_linked").removeProp("disabled");
    }
  });

  if (!form.find("#add_show_has_autoplaylist").prop("checked")) {
    form.find("#add_show_playlist_dropdown").hide();
    form.find("#add_show_autoplaylist_repeat").hide();
  } else {
    $("#add_show_playlist_dropdown").show();
  }

  // RASTATIME 2026-11-03 - autoloading per episode ("Edit Instance"): while
  // the episode follows the show, its autoloading fields are greyed out
  var $inherit = form.find("#add_show_autoplaylist_instance_block #add_show_autoplaylist_inherit");
  if ($inherit.length) {
    var syncInherit = function () {
      var on = $inherit.prop("checked");
      form
        .find(
          "#add_show_has_autoplaylist, select#add_show_autoplaylist_id, input#add_show_autoplaylist_repeat, select#add_show_intro_playlist_id, select#add_show_outro_playlist_id",
        )
        .prop("disabled", on);
    };
    $inherit.on("change", syncInherit);
    syncInherit();
  }

  if (!form.find("#add_show_repeats").prop("checked")) {
    form.find("#schedule-show-when > fieldset:last").hide();
    $("#add_show_rebroadcast_relative").hide();
  } else {
    $("#add_show_rebroadcast_absolute").hide();
  }

  if (!form.find("#add_show_record").prop("checked")) {
    form.find("#add_show_rebroadcast").hide();
  }

  if (!form.find("#add_show_rebroadcast").prop("checked")) {
    form
      .find("#schedule-record-rebroadcast > fieldset:not(:first-child)")
      .hide();
  }

  // If we're adding a new show or the show has no logo, hide the "Current Logo" element tree
  $("[id^=add_show_logo_current]").toggle(
    $("#add_show_logo_current").attr("src") !== "" &&
      $(".button-bar.bottom").find(".ui-button-text").text() === "Update show",
  );

  var submitButton = $(".button-bar.bottom").find(".add-show-submit");
  $("[id^=add_show_instance_description]").toggle(
    submitButton.attr("data-action") === "edit-repeating-show-instance",
  );

  form.find("#add_show_has_autoplaylist").click(function () {
    $(this).blur();
    form.find("#add_show_playlist_dropdown").toggle();
    form.find("#add_show_autoplaylist_repeat").toggle();
  });

  // RASTATIME 2026-11-03 - archiving stage 3: automatic archiving waits for
  // a description; say so while the switch is on and the show has none.
  form
    .find("#add_show_cba_auto, #add_show_description")
    .on("change input", function () {
      syncArchiveDescriptionHint(form);
    });
  syncArchiveDescriptionHint(form);

  // RASTATIME 2026-11-04 - "Number of involved people" only for own productions
  form.find("#add_show_own_production").on("change", function () {
    syncOwnProduction(form);
  });
  syncOwnProduction(form);

  form.find("#add_show_repeats").click(function () {
    $(this).blur();
    form.find("#schedule-show-when > fieldset:last").toggle();

    var checkBoxSelected = false;
    var days = form.find("#add_show_day_check-element input").each(function () {
      var currentCheckBox = $(this).prop("checked");
      if (currentCheckBox && currentCheckBox == "checked") {
        checkBoxSelected = true;
      }
    });

    if (!checkBoxSelected) {
      // RASTATIME 2026-10-19 - .val(), not .attr("value"): the attribute
      // keeps the server-rendered default (today), while a click on a
      // calendar day or the date picker only changes the property - so the
      // pre-ticked weekday was always today's.
      var d = getDateFromString(form.find("#add_show_start_date").val());
      if (d != null)
        form.find("#add_show_day_check-" + d.getDay()).prop("checked", true);
    }

    //must switch rebroadcast displays
    if (form.find("#add_show_rebroadcast").prop("checked")) {
      if ($(this).prop("checked")) {
        form.find("#add_show_rebroadcast_absolute").hide();
        form.find("#add_show_rebroadcast_relative").show();
      } else {
        form.find("#add_show_rebroadcast_absolute").show();
        form.find("#add_show_rebroadcast_relative").hide();
      }
    }
  });

  form.find("#add_show_linked").click(function () {
    if ($(this).attr("readonly")) {
      if ($("#show-link-readonly-warning").length === 0) {
        $(this)
          .parent()
          .after(
            "<ul id='show-link-readonly-warning' class='errors'><li>" +
              $.i18n._(
                "Warning: You cannot change this field while the show is currently playing",
              ) +
              "</li></ul>",
          );
      }
      return false;
    }

    //only display the warning message if a show is being edited
    if (
      $(".button-bar.bottom").find(".ui-button-text").text() === "Update show"
    ) {
      if ($(this).prop("checked") && $("#show-link-warning").length === 0) {
        $(this)
          .parent()
          .after(
            "<ul id='show-link-warning' class='errors'><li>" +
              $.i18n._(
                "Warning: All other repetitions of this show will have their contents replaced to match the show you selected 'Edit Show' with.",
              ) +
              "</li></ul>",
          );
      }

      if (!$(this).prop("checked") && $("#show-link-warning").length !== 0) {
        $("#show-link-warning").remove();
      }
    }
  });

  form
    .find("#add_show_linked-label")
    .before("<span class='show_linking_help_icon'></span>");

  form.find("#add_show_record").click(function () {
    $(this).blur();
    form.find("#add_show_rebroadcast").toggle();

    if (form.find("#add_show_record").prop("checked")) {
      form
        .find("#add_show_linked")
        .prop("checked", false)
        .attr("disabled", true);
    } else {
      form.find("#add_show_linked").attr("disabled", false);
    }

    //uncheck rebroadcast checkbox
    form.find("#add_show_rebroadcast").prop("checked", false);

    //hide rebroadcast options
    form
      .find("#schedule-record-rebroadcast > fieldset:not(:first-child)")
      .hide();
  });

  form.find("#add_show_rebroadcast").click(function () {
    $(this).blur();
    if (form.find("#add_show_record").prop("checked")) {
      if (
        $(this).prop("checked") &&
        !form.find("#add_show_repeats").prop("checked")
      ) {
        form.find("#add_show_rebroadcast_absolute").show();
      } else if (
        $(this).prop("checked") &&
        form.find("#add_show_repeats").prop("checked")
      ) {
        form.find("#add_show_rebroadcast_relative").show();
      } else {
        form
          .find("#schedule-record-rebroadcast > fieldset:not(:first-child)")
          .hide();
      }
    }
  });

  // in case user is creating a new show, there will be
  // no show_id so we have to store the default timezone
  // to be able to do the conversion when the timezone
  // setting changes
  var currentTimezone = form.find("#add_show_timezone").val();

  form.find("#add_show_timezone").change(function () {
    var startDateField = form.find("#add_show_start_date"),
      startTimeField = form.find("#add_show_start_time"),
      endDateField = form.find("#add_show_end_date_no_repeat"),
      endTimeField = form.find("#add_show_end_time"),
      newTimezone = form.find("#add_show_timezone").val();

    $.post(
      baseUrl + "Schedule/localize-start-end-time",
      {
        format: "json",
        startDate: startDateField.val(),
        startTime: startTimeField.val(),
        endDate: endDateField.val(),
        endTime: endTimeField.val(),
        newTimezone: newTimezone,
        oldTimezone: currentTimezone,
      },
      function (json) {
        startDateField.val(json.start.date);
        startTimeField.val(json.start.time);
        endDateField.val(json.end.date);
        endTimeField.val(json.end.time);
        // Change the timezone now that we've updated the times
        currentTimezone = newTimezone;
      },
    );
  });

  form.find("#add_show_repeat_type").change(function () {
    toggleRepeatDays();
    toggleMonthlyRepeatType();
  });
  toggleMonthlyRepeatType();
  toggleRepeatDays();
  function toggleRepeatDays() {
    if (
      form.find("#add_show_repeat_type").val() == 2 ||
      form.find("#add_show_repeat_type").val() == 3
    ) {
      form
        .find("#add_show_day_check-label, #add_show_day_check-element")
        .hide();
      //form.find("#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element").show();
    } else {
      form
        .find("#add_show_day_check-label, #add_show_day_check-element")
        .show();
      //form.find("#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element").hide();
    }
  }
  function toggleMonthlyRepeatType() {
    // RASTATIME 2026-10-14 - the month boxes follow the monthly radio
    if (form.find("#add_show_repeat_type").val() == 2) {
      form
        .find(
          "#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element",
        )
        .show();
    } else {
      form
        .find(
          "#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element",
        )
        .hide();
    }
  }

  form.find("#add_show_day_check-label").addClass("block-display");
  form.find("#add_show_day_check-element").addClass("block-display clearfix");
  form.find("#add_show_day_check-element label").addClass("wrapp-label");
  form.find("#add_show_day_check-element br").remove();
  // RASTATIME 2026-10-15 - the month boxes in rows of four (add-show.css)
  form.find("#add_show_month_check-label").addClass("block-display");
  form.find("#add_show_month_check-element").addClass("block-display clearfix");
  form.find("#add_show_month_check-element label").addClass("wrapp-label");
  form.find("#add_show_month_check-element br").remove();

  form.find(".show_timezone_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "Timezone is set to the station timezone by default. Shows in the calendar will be displayed in your local time defined by the " +
          "Interface Timezone in your user settings.",
      ),
    },
    placement: "right",
    interactive: true,
  });

  form.find(".show_autoplaylist_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "Autoloading playlists' contents are added to shows one hour before the show airs. <a target='_blank' href='https://libretime.org/docs/user-manual/playlists/'>More information</a>",
      ),
    },
    placement: "right",
    interactive: true,
  });

  // RASTATIME 2026-05-17 — Record-per-Show tooltip.  Mirrors the
  // Autoloading-Playlist help-icon pattern.  The text was originally
  // an inline paragraph above the checkbox; moved into a tooltip so
  // the Record section stays as visually compact as Live Stream Input.
  form.find(".show_record_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "When enabled, the Show is recorded to the folder configured in Settings → Local Machine",
      ),
    },
    placement: "right",
    interactive: true,
  });

  // RASTATIME 2026-10-21 - server-rendered help icons (data-rt-tip, text
  // already translated), e.g. "Repeat of show": nothing set them up on this
  // page, so the icon showed no tooltip.  Escaped again because rtTooltip
  // renders HTML.
  form.find("[data-rt-tip]").each(function () {
    $(this).rtTooltip({
      content: { text: $("<div>").text($(this).attr("data-rt-tip")).html() },
      placement: "right",
      interactive: true,
    });
  });
  // RASTATIME 2026-11-03 - tooltips the server built as HTML (escaped
  // there), e.g. the licence matrix of the Archiving section
  form.find("[data-rt-tip-html]").each(function () {
    $(this).rtTooltip({
      content: { text: $(this).attr("data-rt-tip-html") },
      placement: "right",
      interactive: true,
    });
  });

  form.find(".airtime_auth_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "This follows the same security pattern for the shows: only users assigned to the show can connect.",
      ),
    },
    placement: "right",
    interactive: true,
  });
  form.find(".custom_auth_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "Specify custom authentication which will work only for this show.",
      ),
    },
    placement: "right",
    interactive: true,
  });
  form.find(".stream_username_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "If your live streaming client does not ask for a username, this field should be 'source'.",
      ),
    },
    placement: "right",
    interactive: true,
  });
  form.find(".show_linking_help_icon").rtTooltip({
    content: {
      text: $.i18n._(
        "By linking your repeating shows any media items scheduled in any repeat show will also get scheduled in the other repeat shows",
      ),
    },
    placement: "right",
    interactive: true,
  });
  function endDateVisibility() {
    if (form.find("#add_show_no_end").is(":checked")) {
      form.find("#add_show_end_date").hide();
    } else {
      form.find("#add_show_end_date").show();
    }
  }
  endDateVisibility();
  form.find("#add_show_no_end").click(endDateVisibility);

  createDateInput(form.find("#add_show_start_date"), startDpSelect);
  createDateInput(form.find("#add_show_end_date_no_repeat"), endDpSelect);
  createDateInput(form.find("#add_show_end_date"), endDpSelect);

  $("#add_show_start_time").timepicker({
    amPmText: ["", ""],
    defaultTime: "00:00",
    onSelect: onStartTimeSelect,
    hourText: $.i18n._("Hour"),
    minuteText: $.i18n._("Minute"),
  });
  $("#add_show_end_time").timepicker({
    amPmText: ["", ""],
    onSelect: onEndTimeSelect,
    hourText: $.i18n._("Hour"),
    minuteText: $.i18n._("Minute"),
  });

  form.find('input[name^="add_show_rebroadcast_date_absolute"]').datepicker({
    minDate: adjustDateToServerDate(new Date(), timezoneOffset),
    dateFormat: "yy-mm-dd",
    //i18n_months, i18n_days_short are in common.js
    monthNames: i18n_months,
    dayNamesMin: i18n_days_short,
    closeText: "Close",
    showButtonPanel: true,
    firstDay: calendarPref.weekStart,
  });

  form.find('input[name^="add_show_rebroadcast_time"]').timepicker({
    amPmText: ["", ""],
    defaultTime: "",
    closeButtonText: $.i18n._("Done"),
    hourText: $.i18n._("Hour"),
    minuteText: $.i18n._("Minute"),
  });

  form.find(".add_absolute_rebroadcast_day").click(function () {
    var li = $(this)
      .parent()
      .find("ul.formrow-repeat > li:visible:last")
      .next();

    li.show();
    li = li.next();
    if (li.length === 0) {
      $(this).hide();
    }
  });

  form.find('a[id^="remove_rebroadcast"]').click(function () {
    var list = $(this).parent().parent();
    var li_num = $(this).parent().index();
    var num = list.find("li").length;
    var count = num - li_num;

    var curr = $(this).parent();
    var next = curr.next();

    for (var i = 0; i <= count; i++) {
      var date = next.find('[name^="add_show_rebroadcast_date"]').val();
      curr.find('[name^="add_show_rebroadcast_date"]').val(date);
      var time = next.find('[name^="add_show_rebroadcast_time"]').val();
      curr.find('[name^="add_show_rebroadcast_time"]').val(time);

      curr = next;
      next = curr.next();
    }

    list
      .find("li:visible:last")
      .find('[name^="add_show_rebroadcast_date"]')
      .val("")
      .end()
      .find('[name^="add_show_rebroadcast_time"]')
      .val("")
      .end()
      .hide();

    list.next().show();
  });

  form.find("#add_show_hosts_autocomplete").autocomplete({
    source: findHosts,
    select: autoSelect,
    delay: 200,
  });

  form.find("#add_show_hosts_autocomplete").keypress(function (e) {
    if (e.which == 13) {
      return false;
    }
  });

  form.find("#schedule-show-style .input_text").ColorPicker({
    onChange: function (hsb, hex, rgb, el) {
      $(el).val(hex);
    },
    onSubmit: function (hsb, hex, rgb, el) {
      $(el).val(hex);
      $(el).ColorPickerHide();
    },
    onBeforeShow: function () {
      $(this).ColorPickerSetColor(this.value);
    },
  });

  // when an image is uploaded, we want to show it to the user
  form.find("#add_show_logo").change(function (event) {
    if (this.files && this.files[0]) {
      $("#add_show_logo_preview").show();
      var reader = new FileReader(); // browser compatibility?

      reader.onload = function (e) {
        $("#add_show_logo_preview").attr("src", e.target.result);
      };

      // check image size so we don't crash the page trying to render
      if (validateImage(this.files[0], $("#add_show_logo"))) {
        // read the image data as though it were a data URI
        reader.readAsDataURL(this.files[0]);
      } else {
        // remove the file element data
        $(this).val("").replaceWith($(this).clone(true));
        $("#add_show_logo_preview").hide();
      }
    } else {
      $("#add_show_logo_preview").hide();
    }
  });

  form.find("#add_show_logo_current_remove").click(function () {
    if (
      confirm($.i18n._("Are you sure you want to delete the current logo?"))
    ) {
      var showId = $("#add_show_id").attr("value");

      if (showId && $("#add_show_logo_current").attr("src") !== "") {
        var action =
          "/rest/show-image?csrf_token=" + $("#csrf").val() + "&id=" + showId;

        $.ajax({
          url: action,
          data: "",
          type: "DELETE",
          success: function () {
            $("#add_show_logo_current").prop("src", "");
            $("[id^=add_show_logo_current]").hide();
          },
        });
      }
    }
  });

  form.find("#add-show-close").click(closeAddShowForm);

  form.find(".add-show-submit").click(function (event) {
    event.preventDefault();

    var addShowButton = $(this);

    $("#schedule-add-show").block({
      message: null,
      applyPlatformOpacityRules: false,
    });

    //when editing a show, the record option is disabled
    //we have to enable it to get the correct value when
    //we call serializeArray()
    if (form.find("#add_show_record").attr("disabled", true)) {
      form.find("#add_show_record").attr("disabled", false);
    }

    var startDateDisabled = false,
      startTimeDisabled = false;

    // Similarly, we need to re-enable start date and time if they're disabled
    if (form.find("#add_show_start_date").prop("disabled") === true) {
      form.find("#add_show_start_date").attr("disabled", false);
      startDateDisabled = true;
    }
    if (form.find("#add_show_start_time").prop("disabled") === true) {
      form.find("#add_show_start_time").attr("disabled", false);
      startTimeDisabled = true;
    }

    var data = $("form").serializeArray();
    // We need to notify the application if date and time were disabled
    data.push({ name: "start_date_disabled", value: startDateDisabled });
    data.push({ name: "start_time_disabled", value: startTimeDisabled });

    var hosts = $("#add_show_hosts-element input")
      .map(function () {
        if ($(this).prop("checked")) {
          return $(this).val();
        }
      })
      .get();

    var days = $("#add_show_day_check-element input")
      .map(function () {
        if ($(this).prop("checked")) {
          return $(this).val();
        }
      })
      .get();
    // RASTATIME 2026-10-15 - the month boxes travel like the day boxes: the
    // controller rebuilds the form data from a flat name/value list, where
    // a multi-checkbox collapses to its last value
    var months = $("#add_show_month_check-element input")
      .map(function () {
        return $(this).prop("checked") ? $(this).val() : undefined;
      })
      .get();

    var start_date = $("#add_show_start_date").val(),
      end_date = $("#add_show_end_date").val(),
      action =
        baseUrl + "Schedule/" + String(addShowButton.attr("data-action"));

    var image;
    if (
      $("#add_show_logo")[0] &&
      $("#add_show_logo")[0].files &&
      $("#add_show_logo")[0].files[0]
    ) {
      image = new FormData();
      image.append("file", $("#add_show_logo")[0].files[0]);
    }

    $.ajax({
      url: action,
      data: {
        format: "json",
        data: data,
        hosts: hosts,
        days: days,
        months: months,
      },
      success: function (json) {
        if (json.showId && image) {
          // Successfully added the show, and it contains an image to upload
          var imageAction =
            "/rest/show-image?csrf_token=" +
            $("#csrf").val() +
            "&id=" +
            json.showId;

          // perform a second xhttprequest in order to send the show image
          $.ajax({
            url: imageAction,
            data: image,
            cache: false,
            contentType: false,
            processData: false,
            type: "POST",
          });
        }

        $("#schedule-add-show").unblock();

        var $addShowForm = $("#add-show-form");

        if (json.form) {
          redrawAddShowForm($addShowForm, json.form);

          $("#add_show_end_date").val(end_date);
          $("#add_show_start_date").val(start_date);
          showErrorSections();
        } else if (json.edit) {
          // re-render the schedule calendar after a successful create/edit:
          // FC1.5 render(); FC6 (?fc6=1) refetch + updateSize, since the jQuery
          // plugin method does not apply to an FC6 instance
          var $cal = $("#schedule_calendar").removeAttr("style");
          if (window.SCHEDULE_USE_FC6) {
            if (window.scheduleFc6) {
              window.scheduleFc6.refetchEvents();
              window.scheduleFc6.updateSize();
            }
          } else {
            $cal.fullCalendar("render");
          }

          $addShowForm.hide();
          toggleAddShowButton();
          $.get(
            baseUrl + "Schedule/get-form",
            { format: "json" },
            function (json) {
              redrawAddShowForm($addShowForm, json.form);
            },
          );
        } else {
          redrawAddShowForm($addShowForm, json.newForm);
          scheduleRefetchEvents(json);
          $addShowForm.hide();
          toggleAddShowButton();
        }

        /* CC-6062: Resize the window to avoid stretching the last column */
        windowResize();
        makeAddShowButton();
      },
    });
  });

  var regDate = new RegExp(/^[0-9]{4}-[0-1][0-9]-[0-3][0-9]$/);
  var regTime = new RegExp(/^[0-2][0-9]:[0-5][0-9]$/);

  // when start date/time changes, set end date/time to start date/time+1 hr
  $("#add_show_start_date, #add_show_start_time").bind(
    "input",
    "change",
    function () {
      var startDateString = $("#add_show_start_date").val();
      var startTimeString = $("#add_show_start_time").val();

      if (regDate.test(startDateString) && regTime.test(startTimeString)) {
        var startDate = startDateString.split("-");
        var startTime = startTimeString.split(":");
        var startDateTime = new Date(
          startDate[0],
          parseInt(startDate[1], 10) - 1,
          startDate[2],
          startTime[0],
          startTime[1],
          0,
          0,
        );

        var endDateString = $("#add_show_end_date_no_repeat").val();
        var endTimeString = $("#add_show_end_time").val();
        var endDate = endDateString.split("-");
        var endTime = endTimeString.split(":");
        var endDateTime = new Date(
          endDate[0],
          parseInt(endDate[1], 10) - 1,
          endDate[2],
          endTime[0],
          endTime[1],
          0,
          0,
        );

        if (startDateTime.getTime() >= endDateTime.getTime()) {
          var duration = $("#add_show_duration").val();
          // parse duration
          var time = 0;
          var info = duration.split(" ");
          var h = parseInt(info[0], 10);
          time += h * 60 * 60 * 1000;
          if (info.length > 1 && $.trim(info[1]) !== "") {
            var m = parseInt(info[1], 10);
            time += m * 60 * 1000;
          }
          endDateTime = new Date(startDateTime.getTime() + time);
        }

        var endDateFormat =
          endDateTime.getFullYear() +
          "-" +
          pad(endDateTime.getMonth() + 1, 2) +
          "-" +
          pad(endDateTime.getDate(), 2);
        var endTimeFormat =
          pad(endDateTime.getHours(), 2) +
          ":" +
          pad(endDateTime.getMinutes(), 2);

        $("#add_show_end_date_no_repeat").val(endDateFormat);
        $("#add_show_end_time").val(endTimeFormat);

        // calculate duration
        var startDateTimeString = startDateString + " " + startTimeString;
        var endDateTimeString =
          $("#add_show_end_date_no_repeat").val() +
          " " +
          $("#add_show_end_time").val();
        var timezone = $("#add_show_timezone").val();
        calculateDuration(startDateTimeString, endDateTimeString, timezone);
      }
    },
  );

  // when end date/time changes, check if the changed date is in past of start date/time
  $("#add_show_end_date_no_repeat, #add_show_end_time").bind(
    "input",
    "change",
    function () {
      var endDateString = $("#add_show_end_date_no_repeat").val();
      var endTimeString = $("#add_show_end_time").val();

      if (regDate.test(endDateString) && regTime.test(endTimeString)) {
        var startDateString = $("#add_show_start_date").val();
        var startTimeString = $("#add_show_start_time").val();
        var startDate = startDateString.split("-");
        var startTime = startTimeString.split(":");
        var startDateTime = new Date(
          startDate[0],
          parseInt(startDate[1], 10) - 1,
          startDate[2],
          startTime[0],
          startTime[1],
          0,
          0,
        );

        var endDate = endDateString.split("-");
        var endTime = endTimeString.split(":");
        var endDateTime = new Date(
          endDate[0],
          parseInt(endDate[1], 10) - 1,
          endDate[2],
          endTime[0],
          endTime[1],
          0,
          0,
        );

        if (startDateTime.getTime() > endDateTime.getTime()) {
          $("#add_show_end_date_no_repeat").css("background-color", "#F49C9C");
          $("#add_show_end_time").css("background-color", "#F49C9C");
        } else {
          $("#add_show_end_date_no_repeat").css("background-color", "");
          $("#add_show_end_time").css("background-color", "");
        }

        // calculate duration
        var startDateTimeString = startDateString + " " + startTimeString;
        var endDateTimeString = endDateString + " " + endTimeString;
        var timezone = $("#add_show_timezone").val();
        calculateDuration(startDateTimeString, endDateTimeString, timezone);
      }
    },
  );

  if ($("#cb_custom_auth").prop("checked")) {
    $("#custom_auth_div").show();
  } else {
    $("#custom_auth_div").hide();
  }

  $("#cb_custom_auth").change(function () {
    if ($(this).prop("checked")) {
      $("#custom_auth_div").show();
    } else {
      $("#custom_auth_div").hide();
    }
  });

  function calculateDuration(startDateTime, endDateTime, timezone) {
    var loadingIcon = $("#icon-loader-small");

    loadingIcon.show();
    $.post(
      baseUrl + "Schedule/calculate-duration",
      { startTime: startDateTime, endTime: endDateTime, timezone: timezone },
      function (data) {
        $("#add_show_duration").val(JSON.parse(data));
        loadingIcon.hide();
      },
    );
  }

  // Since Zend's setAttrib won't apply through the wrapper, set accept=image/* here
  $("#add_show_logo").prop("accept", "image/*");

  //$('#add_show_name').bind('input', 'change', function(){
  $("#add_show_start_time").bind("input", "change", function () {
    calculateShowColor();
  });

  // RASTATIME 2026-05-19 — wire up Show-Template Load/Save controls
  // (Section 23.16).  Rendered in both New-Show and Edit-Show forms;
  // setupShowTemplateControls is defensive and no-ops if the controls
  // were not rendered into a future variant of the form.
  setupShowTemplateControls(form);
}

/**
 * RASTATIME 2026-05-19 — Section 23.16
 *
 * Wires up the Load Template dropdown + Apply button + Save-as-
 * Template button at the top of the show form.  Used by both the
 * New-Show flow and the Edit-Show flow (the partial template
 * defines the controls unconditionally as of 2026-05-19).
 * Idempotent — clears any prior bindings + dropdown contents first.
 * Safe to call when the controls don't exist (e.g. a future variant
 * of the form that elides them).
 */
function setupShowTemplateControls(form) {
  var $controls = $("#show-template-controls");
  if ($controls.length === 0) {
    return; // no template UI rendered into this form variant
  }

  var $select = $("#show-template-select");
  var $apply = $("#show-template-apply");
  var $save = $("#show-template-save");
  var $status = $("#show-template-status");

  function setStatus(msg, isError) {
    $status.text(msg || "");
    $status.css("color", isError ? "#c66" : "#6c6");
  }

  function refreshDropdown(selectId) {
    $.getJSON(
      baseUrl + "Schedule/list-show-templates",
      { format: "json" },
      function (json) {
        $select
          .empty()
          .append('<option value="">— ' + $.i18n._("Select a template") + " —</option>");
        if (json && json.templates) {
          json.templates.forEach(function (t) {
            $select.append(
              $("<option/>").attr("value", t.id).text(t.name),
            );
          });
        }
        if (selectId) {
          $select.val(String(selectId));
        }
      },
    );
  }

  // Initial load
  refreshDropdown();

  $apply
    .off("click")
    .on("click", function (event) {
      // RASTATIME 2026-05-19 — Bug 1 mitigation.  These template
      // controls live inside <form id="add-show-form">; suppress
      // default + bubble so a stray submit cannot block the
      // subsequent "Add this show" click.
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      setStatus("");
      var tid = $select.val();
      if (!tid) {
        setStatus($.i18n._("Pick a template first."), true);
        return false;
      }
      $.getJSON(
        baseUrl + "Schedule/get-show-template/id/" + tid + "/format/json",
        function (json) {
          if (!json || json.error || !json.template) {
            setStatus(
              json && json.error
                ? json.error
                : $.i18n._("Could not load template."),
              true,
            );
            return;
          }
          applyShowTemplate(form, json.template.template_data || {});
          setStatus(
            $.i18n._("Template applied: ") + (json.template.name || ""),
          );
        },
      );
      return false;
    });

  $save
    .off("click")
    .on("click", function (event) {
      // RASTATIME 2026-05-19 — Bug 1 mitigation.  Explicitly stop the
      // click from propagating into the surrounding <form id="add-show-form">
      // so the browser cannot interpret this as a form submit (which
      // would prevent any subsequent Add-this-Show click from posting
      // because the form is still in mid-submit on the click cycle).
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      setStatus("");
      var data = $("#add-show-form").serializeArray();
      var hosts = $("#add_show_hosts-element input")
        .map(function () {
          return $(this).prop("checked") ? $(this).val() : undefined;
        })
        .get();
      var days = $("#add_show_day_check-element input")
        .map(function () {
          return $(this).prop("checked") ? $(this).val() : undefined;
        })
        .get();
      var months = $("#add_show_month_check-element input")
        .map(function () {
          return $(this).prop("checked") ? $(this).val() : undefined;
        })
        .get();
      doSaveTemplate(data, hosts, days, months, 0);
      return false;
    });

  function doSaveTemplate(data, hosts, days, months, overwrite) {
    $.post(
      baseUrl + "Schedule/save-show-template/format/json",
      { format: "json", data: data, hosts: hosts, days: days, months: months, overwrite: overwrite },
      function (json) {
        if (json && json.conflict) {
          var ok = confirm(
            $.i18n._(
              "A template with this name already exists. Overwrite?",
            ),
          );
          if (ok) {
            doSaveTemplate(data, hosts, days, months, 1);
          } else {
            setStatus($.i18n._("Save cancelled."), true);
          }
          return;
        }
        if (json && json.error) {
          setStatus(json.error, true);
          return;
        }
        setStatus(
          $.i18n._("Saved as template: ") + (json && json.name ? json.name : ""),
        );
        refreshDropdown(json && json.id);
      },
    );
  }
}

/**
 * RASTATIME 2026-05-19 — apply a template_data blob into the
 * currently-open New-Show form.  Writes each known field's *value*
 * (or checkbox state) and then runs syncDependentVisibility() to
 * recompute the show/hide state of every UI section that the existing
 * Add-Show click handlers normally toggle.
 *
 * Per design: start_date and start_time are NEVER touched here —
 * those come from the calendar click and must be preserved.
 *
 * Bug-history note (2026-05-19, test feedback):
 *  - The earlier implementation used $el.prop("checked", on)
 *    .trigger("click") to fire the existing toggle-style click handlers
 *    on Repeats / Record / Autoplaylist / etc.  jQuery 1.8.3's
 *    default-action simulation for click events on form controls fires
 *    *after* user handlers and toggles the native checked state of a
 *    checkbox a second time — so the box ended up in the inverted
 *    state with the UI synced to the wrong logical value.  Hence the
 *    split between "write the values" and "compute UI visibility from
 *    the post-write values" below.
 */
function applyShowTemplate(form, td) {
  function setVal(id, val) {
    if (val === undefined || val === null) return;
    form.find("#" + id).val(val);
  }
  function setCheck(id, val) {
    var on = val === true || val === 1 || val === "1" || val === "on";
    var $el = form.find("#" + id);
    if ($el.length === 0) return;
    $el.prop("checked", on);
  }

  // What
  setVal("add_show_name", td.add_show_name);
  setVal("add_show_url", td.add_show_url);
  setVal("add_show_genre", td.add_show_genre);
  setVal("add_show_description", td.add_show_description);

  // When (duration + repeat shape; start_date/time deliberately skipped)
  setVal("add_show_duration", td.add_show_duration);
  setCheck("add_show_repeats", td.add_show_repeats);
  setCheck("add_show_linked", td.add_show_linked);
  setVal("add_show_repeat_type", td.add_show_repeat_type);
  setVal("add_show_monthly_repeat_type", td.add_show_monthly_repeat_type);
  setVal("add_show_end_date", td.add_show_end_date);
  setCheck("add_show_no_end", td.add_show_no_end);

  // Days of the week (array of weekday indices)
  if (Array.isArray(td.add_show_day_check)) {
    form.find("#add_show_day_check-element input").prop("checked", false);
    td.add_show_day_check.forEach(function (d) {
      form.find("#add_show_day_check-" + d).prop("checked", true);
    });
  }
  // RASTATIME 2026-10-15 - months of a monthly repeat (empty = every month)
  if (Array.isArray(td.add_show_month_check)) {
    var all = td.add_show_month_check.length === 0;
    form.find("#add_show_month_check-element input").prop("checked", all);
    td.add_show_month_check.forEach(function (m) {
      form.find("#add_show_month_check-" + m).prop("checked", true);
    });
  }

  // Record (must be written *before* sync so the linked-disable
  // domain rule, applied in syncDependentVisibility, sees the right
  // record state and does not clobber an explicit linked=true from a
  // record=false template).
  setCheck("add_show_record", td.add_show_record);
  setCheck("add_show_own_production", td.add_show_own_production); // RASTATIME 2026-11-03

  // Autoloading Playlist
  setCheck("add_show_has_autoplaylist", td.add_show_has_autoplaylist);
  setVal("add_show_autoplaylist_id", td.add_show_autoplaylist_id);
  setCheck("add_show_autoplaylist_repeat", td.add_show_autoplaylist_repeat);
  setVal("add_show_intro_playlist_id", td.add_show_intro_playlist_id);
  setVal("add_show_outro_playlist_id", td.add_show_outro_playlist_id);
  setVal("add_show_repeat_of", td.add_show_repeat_of); // RASTATIME 2026-10-18

  // Live Stream Input (password deliberately not in template)
  setCheck("cb_airtime_auth", td.cb_airtime_auth);
  setCheck("cb_custom_auth", td.cb_custom_auth);
  setVal("custom_username", td.custom_username);

  // Style
  setVal("add_show_background_color", td.add_show_background_color);
  setVal("add_show_color", td.add_show_color);
  // Show logo: stored as a path reference.  We display it in the
  // current-logo preview if present; the operator can keep it
  // (no action needed) or upload a fresh image which overrides.
  if (td.add_show_logo_path) {
    form
      .find("#add_show_logo_current")
      .attr("src", baseUrl + td.add_show_logo_path)
      .show();
    form
      .find("[id^=add_show_logo_current]")
      .show();
  }

  // Hosts (array of usernames).  Resolve each to the corresponding
  // host-checkbox by matching label text — same shape used by the
  // existing host autocomplete in this file.
  if (Array.isArray(td.add_show_hosts_logins)) {
    form.find("#add_show_hosts-element input").prop("checked", false);
    var $hostInputs = form.find("#add_show_hosts-element input");
    td.add_show_hosts_logins.forEach(function (login) {
      $hostInputs.each(function () {
        var labelText = $(this).next("label").text();
        if (labelText && labelText.indexOf(login) !== -1) {
          $(this).prop("checked", true);
        }
      });
    });
  }

  // Finally, recompute all the toggle-driven visibility from the
  // now-written checkbox values.  Doing this once at the end avoids
  // ordering-dependent intermediate states (e.g. setting linked=true
  // before record=true would leave linked checked even though the
  // domain rule forbids it).
  syncDependentVisibility(form);
}

/**
 * RASTATIME 2026-05-19 — Recompute the show/hide state of every
 * collapsible section that the New-Show / Edit-Show form's click
 * handlers normally manage.  Called after applyShowTemplate() writes
 * the raw form values; mirrors the visibility rules in setAddShowEvents
 * but reads the *current* checkbox state instead of toggling.
 */
function syncDependentVisibility(form) {
  var $repeats = form.find("#add_show_repeats");
  var $record = form.find("#add_show_record");
  var $rebroadcast = form.find("#add_show_rebroadcast");
  var $autoplaylist = form.find("#add_show_has_autoplaylist");
  var $customAuth = form.find("#cb_custom_auth");
  var $noEnd = form.find("#add_show_no_end");
  var $linked = form.find("#add_show_linked");

  // Repeats — show/hide the repeat-options fieldset
  form.find("#schedule-show-when > fieldset:last").toggle(!!$repeats.prop("checked"));

  // Repeat type — day-of-week pickers + monthly-type picker visibility
  var repeatType = form.find("#add_show_repeat_type").val();
  if (repeatType == 2 || repeatType == 3) {
    form.find("#add_show_day_check-label, #add_show_day_check-element").hide();
  } else {
    form.find("#add_show_day_check-label, #add_show_day_check-element").show();
  }
  if (repeatType == 2) {
    form
      .find(
        "#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element",
      )
      .show();
  } else {
    form
      .find(
        "#add_show_monthly_repeat_type-label, #add_show_monthly_repeat_type-element, #add_show_month_check-label, #add_show_month_check-element",
      )
      .hide();
  }

  // Record — toggle rebroadcast checkbox visibility; if record, force
  // linked off + disabled (domain rule: a recorded show cannot be
  // linked because the live audio is unique to its instance).
  $rebroadcast.toggle(!!$record.prop("checked"));
  if ($record.prop("checked")) {
    $linked.prop("checked", false).attr("disabled", true);
  } else {
    $linked.attr("disabled", false);
  }

  // Rebroadcast — show absolute vs. relative fieldset based on repeats
  if ($rebroadcast.prop("checked")) {
    if ($repeats.prop("checked")) {
      form.find("#add_show_rebroadcast_absolute").hide();
      form.find("#add_show_rebroadcast_relative").show();
    } else {
      form.find("#add_show_rebroadcast_absolute").show();
      form.find("#add_show_rebroadcast_relative").hide();
    }
  } else {
    form.find("#schedule-record-rebroadcast > fieldset:not(:first-child)").hide();
  }

  // Autoloading playlist — show dropdowns when checked
  form.find("#add_show_playlist_dropdown").toggle(!!$autoplaylist.prop("checked"));
  form
    .find("#add_show_autoplaylist_repeat")
    .toggle(!!$autoplaylist.prop("checked"));

  // Custom auth — show username/password fields when checked
  form.find("#custom_auth_div").toggle(!!$customAuth.prop("checked"));

  // End date — hide if no_end checked
  if ($noEnd.prop("checked")) {
    form.find("#add_show_end_date").hide();
  } else {
    form.find("#add_show_end_date").show();
  }

  syncArchiveDescriptionHint(form);
  syncOwnProduction(form);
}

/**
 * RASTATIME 2026-11-04 - "CBA podcast ID" as wide as the "Licence" select
 * (operator).  The select takes the width of its longest option, which
 * differs per language, so it is measured; nothing to measure while the
 * section is collapsed.
 */
function syncArchivingWidths(form) {
  var width = form.find("#add_show_cba_license").outerWidth();
  if (width > 0) {
    form.find("#add_show_cba_series_id").outerWidth(width);
  }
}

/**
 * RASTATIME 2026-11-04 - the number of people involved belongs to own
 * productions only (operator): shown while "Own production" is ticked.  A
 * hidden value is still posted and kept, it just does not count.
 */
function syncOwnProduction(form) {
  var own = !!form.find("#add_show_own_production").prop("checked");
  // a refused value stays visible, or the save would fail without a word
  var refused = form.find("#add_show_participants-element .errors").length > 0;
  form
    .find("#add_show_participants-label, #add_show_participants-element")
    .toggle(own || refused);
}

/**
 * RASTATIME 2026-11-03 - archiving stage 3: the note below "Archive
 * automatically" while the switch is on and the show has no description
 * (each episode then needs its own, or the automatic run waits).
 */
function syncArchiveDescriptionHint(form) {
  var auto = !!form.find("#add_show_cba_auto").prop("checked");
  var desc = $.trim(form.find("#add_show_description").val() || "");
  form.find("#add_show_cba_auto_nodesc").toggle(auto && desc === "");
}

function showErrorSections() {
  if ($("#schedule-show-what .errors").length > 0) {
    $("#schedule-show-what").show();
  }
  if ($("#schedule-show-when .errors").length > 0) {
    $("#schedule-show-when").show();
  }
  if ($("#schedule-show-who .errors").length > 0) {
    $("#schedule-show-who").show();
  }
  if ($("#schedule-show-style .errors").length > 0) {
    $("#schedule-show-style").show();
  }
  if ($("#add_show_rebroadcast_absolute .errors").length > 0) {
    $("#schedule-record-rebroadcast").show();
    $("#add_show_rebroadcast_absolute").show();
  }
  if ($("#live-stream-override .errors").length > 0) {
    $("#live-stream-override").show();
  }
  // RASTATIME 2026-10-21 - a "Repeat of show" error (e.g. a loop) or an
  // autoloading one must not stay hidden in its collapsed section
  if ($("#schedule-show-repeat .errors").length > 0) {
    $("#schedule-show-repeat").show();
  }
  if ($("#schedule-show-auto .errors").length > 0) {
    $("#schedule-show-auto").show();
  }
  if ($("#schedule-show-archiving .errors").length > 0) {
    $("#schedule-show-archiving").show();
    syncArchivingWidths($("#schedule-add-show"));
  }
  if ($("#add_show_rebroadcast_relative .errors").length > 0) {
    $("#schedule-record-rebroadcast").show();
    $("#add_show_rebroadcast_relative").show();
  }
}

$(document).ready(function () {
  setAddShowEvents($("#add-show-form"));
});

//Alert the error and reload the page
//this function is used to resolve concurrency issue
function alertShowErrorAndReload() {
  alert($.i18n._("The show instance doesn't exist anymore!"));
  window.location.reload();
}
