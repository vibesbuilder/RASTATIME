/**
 *
 *   Full Calendar callback methods.
 *
 */

// RASTATIME 2026-06-01 (JS-modernization stage 2): refetch the schedule
// calendar's events regardless of engine — FC1.5 jQuery plugin or the FC6
// instance behind ?fc6=1.  Shared by every action that mutates the schedule
// (create / edit / delete / clear / move / resize / dialog close).
function scheduleCalRefetch() {
  if (window.SCHEDULE_USE_FC6) {
    if (
      window.scheduleFc6 &&
      typeof window.scheduleFc6.refetchEvents === "function"
    ) {
      window.scheduleFc6.refetchEvents();
    }
    return;
  }
  $("#schedule_calendar").fullCalendar("refetchEvents");
}

function scheduleRefetchEvents(json) {
  if (json.show_error == true) {
    alert($.i18n._("The show instance doesn't exist anymore!"));
  }
  if (json.show_id) {
    var dialog_id = parseInt($("#add_show_id").val(), 10);

    //if you've deleted the show you are currently editing, close the add show dialog.
    if (dialog_id === json.show_id) {
      $("#add-show-close").click();
    }
  }
  scheduleCalRefetch();
}

function makeTimeStamp(date) {
  var sy, sm, sd, h, m, s, timestamp;
  sy = date.getFullYear();
  sm = date.getMonth() + 1;
  sd = date.getDate();
  h = date.getHours();
  m = date.getMinutes();
  s = date.getSeconds();

  timestamp =
    sy +
    "-" +
    pad(sm, 2) +
    "-" +
    pad(sd, 2) +
    " " +
    pad(h, 2) +
    ":" +
    pad(m, 2) +
    ":" +
    pad(s, 2);
  return timestamp;
}

function dayClick(date, allDay, jsEvent, view) {
  // The show from will be preloaded if the user is admin or program manager.
  // Hence, if the user if DJ then it won't open anything.
  if (userType == "S" || userType == "A" || userType == "P") {
    var now, today, selected, chosenDate, chosenTime;

    now = adjustDateToServerDate(new Date(), serverTimezoneOffset);

    if (view.name === "month") {
      today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      selected = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    } else {
      today = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        now.getHours(),
        now.getMinutes(),
      );
      selected = new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
        date.getHours(),
        date.getMinutes(),
      );
    }

    if (selected >= today) {
      var addShow = $(".add-button");

      //remove the +show button if it exists.
      if (addShow.length == 1) {
        var span = $(addShow).parent();

        $(span).next().remove();
        $(span).remove();
      }

      // get current duration value on the form
      var duration_string = $.trim($("#add_show_duration").val());
      var duration_info = duration_string.split(" ");
      var duration_h = 0;
      var duration_m = 0;
      if (duration_info[0] != null) {
        duration_h = parseInt(duration_info[0], 10);
      }
      if (duration_info[1] != null) {
        duration_m = parseInt(duration_info[1], 10);
      }
      // duration in milisec
      var duration = duration_h * 60 * 60 * 1000 + duration_m * 60 * 1000;

      var startTime_string;
      var startTime = 0;
      // get start time value on the form
      if (view.name === "month") {
        startTime_string = $("#add_show_start_time").val();
        var startTime_info = startTime_string.split(":");
        if (startTime_info.length == 2) {
          var start_time_temp =
            parseInt(startTime_info[0], 10) * 60 * 60 * 1000 +
            parseInt(startTime_info[1], 10) * 60 * 1000;
          if (!isNaN(start_time_temp)) {
            startTime = start_time_temp;
          }
        }
      } else {
        // if in day or week view, selected has all the time info as well
        // so we don't ahve to calculate it explicitly
        startTime_string =
          pad(selected.getHours(), 2) + ":" + pad(selected.getMinutes(), 2);
        startTime = 0;
      }

      // calculate endDateTime
      var endDateTime = new Date(selected.getTime() + startTime + duration);

      chosenDate =
        selected.getFullYear() +
        "-" +
        pad(selected.getMonth() + 1, 2) +
        "-" +
        pad(selected.getDate(), 2);
      var endDateFormat =
        endDateTime.getFullYear() +
        "-" +
        pad(endDateTime.getMonth() + 1, 2) +
        "-" +
        pad(endDateTime.getDate(), 2);

      //TODO: This should all be refactored into a proper initialize() function for the show form.
      $("#add_show_start_now-future").attr("checked", "checked");
      $("#add_show_start_now-now").removeProp("disabled");
      setupStartTimeWidgets(); //add-show.js
      $("#add_show_start_date").val(chosenDate);
      $("#add_show_end_date_no_repeat").val(endDateFormat);
      $("#add_show_end_date").val(endDateFormat);
      if (view.name !== "month") {
        var endTimeString =
          pad(endDateTime.getHours(), 2) +
          ":" +
          pad(endDateTime.getMinutes(), 2);
        $("#add_show_start_time").val(startTime_string);
        $("#add_show_end_time").val(endTimeString);
      }
      calculateShowColor();
      $("#schedule-show-when").show();

      openAddShowForm();
      makeAddShowButton();
      toggleAddShowButton();
    }
  }
}

// RASTATIME 2026-09-17 (JS-modernization): the five FC1.5-only callbacks
// (viewDisplay, eventRender, eventAfterRender, eventDrop, eventResize)
// were removed with the FC1.5 fork - their FC6 ports live in schedule-fc6.js.
// dayClick() above and windowResize()/addQtipsToIcons() below stay: the FC6
// integration calls them directly.

function windowResize() {
  // 200 px for top dashboard and 50 for padding on main content
  // this calculation was copied from schedule.js line 326
  var mainHeight = $(window).height() - 200 - 24;
  if (window.SCHEDULE_USE_FC6) {
    if (window.scheduleFc6) {
      window.scheduleFc6.setOption("contentHeight", mainHeight);
      // RASTATIME 2026-10-19 - the add/edit show form shares the row with
      // the calendar; FC6 only re-measures on window resize, so after the
      // form is shown or hidden the calendar kept the old width.
      window.scheduleFc6.updateSize();
    }
    return;
  }
  $("#schedule_calendar").fullCalendar("option", "contentHeight", mainHeight);
}

function preloadEventFeed() {
  createFullCalendar({ calendarInit: calendarPref });
}

var initialLoad = true;
function getFullCalendarEvents(start, end, callback) {
  if (initialLoad) {
    initialLoad = false;
    callback(calendarEvents);
  } else {
    var url, start_date, end_date;

    start_date = makeTimeStamp(start);
    end_date = makeTimeStamp(end);
    url = baseUrl + "Schedule/event-feed";

    var d = new Date();
    $.post(
      url,
      { format: "json", start: start_date, end: end_date, cachep: d.getTime() },
      function (json) {
        callback(json.events);
        getUsabilityHint();
      },
    );
  }

  $(".fc-button").addClass("btn").addClass("btn-small");
  //$("span.fc-button > :button").addClass("btn btn-small");
}

/** This function adds and removes the current
 *  show icon
 */
function getCurrentShow() {
  var url = baseUrl + "Schedule/get-current-show/format/json";

  function addNowPlaying(json) {
    var $el,
      span = '<span class="small-icon now-playing"></span>';

    $(".now-playing").remove();

    if (json.current_show === true) {
      $el = $(".fc-show-instance-" + json.si_id);

      if (view_name === "agendaDay" || view_name === "agendaWeek") {
        $el.find(".fc-event-time").before(span);
      } else if (view_name === "month") {
        $el.find(".fc-event-title").after(span);
      }
    }

    setTimeout(getCurrentShow, 5000);
  }

  $.post(url, { format: "json" }, addNowPlaying);
}

function addQtipsToIcons(ele, id) {
  if ($(ele).hasClass("progress")) {
    $(ele).rtTooltip({
      content: {
        text: $.i18n._("Uploading in progress..."),
      },
      placement: "right-start",
      extraClass: "file-md-long",
    });
  } else if ($(ele).hasClass("show-empty")) {
    $(ele).rtTooltip({
      content: {
        text: $.i18n._("This show has no scheduled content."),
      },
      placement: "right-start",
      extraClass: "file-md-long",
    });
  } else if ($(ele).hasClass("show-partial-filled")) {
    $(ele).rtTooltip({
      content: {
        text: $.i18n._("This show is not completely filled with content."),
      },
      placement: "right-start",
      extraClass: "file-md-long",
    });
  } else if ($(ele).hasClass("repeat-of")) {
    // RASTATIME 2026-10-21 - repeat icon: names the source show (escaped,
    // rtTooltip renders HTML)
    $(ele).rtTooltip({
      content: {
        text: $("<div>")
          .text(
            sprintf(
              $.i18n._('Repeat of "%s" - filled automatically shortly before it starts'),
              $(ele).attr("data-repeat-of") || "",
            ),
          )
          .html(),
      },
      placement: "right-start",
      extraClass: "file-md-long",
    });
  } else if ($(ele).hasClass("show-overbooked")) {
    $(ele).rtTooltip({
      content: {
        text: $.i18n._(
          "Shows longer than their scheduled time will be cut off by a following show.",
        ),
      },
      placement: "right-start",
      extraClass: "file-md-long",
    });
  }
}
//Alert the error and reload the page
//this function is used to resolve concurrency issue
function alertShowErrorAndReload() {
  alert($.i18n._("The show instance doesn't exist anymore!"));
  window.location.reload();
}

$(document).ready(function () {
  preloadEventFeed();
  getCurrentShow();

  // RASTATIME 2026-05-20 — refresh the calendar's event list every
  // 60 s so the per-show fill bar (rendered from event.percent in
  // eventRender() above) picks up changes made by the
  // AutoPlaylistManager polling job (also 60 s).  Before this the
  // calendar only refetched on direct user actions (drag/drop,
  // edit, delete) — an autoplaylist that filled a show 1 h before
  // its start was invisible in the calendar until the operator
  // manually reloaded the page.  refetchEvents() re-runs the
  // Schedule/event-feed AJAX call, which carries the up-to-date
  // percent from cc_show_instances.time_filled.
  // RASTATIME 2026-10-07 - registered so the first 401 stops it (common.js)
  (window.rtPollTimers = window.rtPollTimers || []).push(setInterval(function () {
    var $cal = $("#schedule_calendar");
    if ($cal.length > 0 && $cal.is(":visible")) {
      // scheduleCalRefetch() picks FC1.5 vs FC6 (?fc6=1) automatically
      scheduleCalRefetch();
    }
  }, 60 * 1000));
});

var view_name;
