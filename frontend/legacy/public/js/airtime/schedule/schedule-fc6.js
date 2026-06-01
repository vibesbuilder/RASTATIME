/**
 * RASTATIME 2026-06-01 (JS-modernization stage 2): FullCalendar 6 Schedule.
 * ------------------------------------------------------------------
 * Replaces the forked FullCalendar 1.5 (js/fullcalendar/) on the Schedule page
 * with the vendored FC6 (js/libs/fullcalendar/) — the same lib the embed
 * Multi-View widget already uses.  FC6 is vanilla (no jQuery) -> removes a
 * jQuery dependency (the stage-2 goal).
 *
 * Phase a (read-only): calendar shell + event source + station-time display +
 * the three views.  Interactions (create / drag / resize / context menu) and the
 * rich event rendering (fill bar + status icons) are the next steps.
 *
 * Enabled with ?fc6=1; FC1.5 stays the default fallback until FC6 is fully
 * verified.  createFullCalendar() in schedule.js branches here.
 *
 * Timezone: the server returns event start/end as naive station-local
 * timestamps ("YYYY-MM-DD HH:MM:SS"); FC6 (timeZone 'local') renders the
 * wall-clock numbers verbatim -> station time in every browser.  FC6's `now`
 * option is set to station time so the now-line and "today" land correctly,
 * replacing the old serverTimezoneOffset hand-patch in the forked lib.
 */
var scheduleFc6 = null;
// current slot granularity in minutes (1/5/10/15/30/60) — drives the interval
// dropdown's selected value across re-injections; seeded from the saved pref.
var fc6SlotMin = 30;

// View-name mapping: the stored preference + FC1.5 use agendaDay/agendaWeek/
// month; FC6 uses timeGridDay/timeGridWeek/dayGridMonth.
var FC6_VIEW_FROM_LEGACY = {
  agendaDay: "timeGridDay",
  agendaWeek: "timeGridWeek",
  month: "dayGridMonth",
};
var FC6_VIEW_TO_LEGACY = {
  timeGridDay: "agendaDay",
  timeGridWeek: "agendaWeek",
  dayGridMonth: "month",
};

function fc6Locale() {
  var l =
    window.LOCALE ||
    (window.$ && $("html").attr("lang")) ||
    (navigator.language || "en");
  return String(l).toLowerCase().split("-")[0].split("_")[0];
}

function fc6Isoify(s) {
  // server sends naive station-local "YYYY-MM-DD HH:MM:SS"; FC6 wants ISO.
  return typeof s === "string" ? s.replace(" ", "T") : s;
}

function getScheduleFc6Events(info, success, failure) {
  var startDate = makeTimeStamp(info.start);
  var endDate = makeTimeStamp(info.end);
  var url = baseUrl + "Schedule/event-feed";
  var d = new Date();
  $.post(url, {
    format: "json",
    start: startDate,
    end: endDate,
    cachep: d.getTime(),
  })
    .done(function (json) {
      var events = (json.events || []).map(function (e) {
        // FC6 reads id/start/end/title; every other field lands in
        // event.extendedProps automatically.
        var ev = $.extend({}, e);
        ev.start = fc6Isoify(e.start);
        ev.end = fc6Isoify(e.end);
        // Explicit per-event editability: the feed sets editable:true only for
        // shows that may be moved/resized (false for recording/rebroadcast,
        // UNSET for past shows and DJ users).  Force it to a hard boolean so a
        // missing flag does not inherit the calendar's editable:true and make
        // past shows draggable — matches FC1.5's per-event-true-unlocks model.
        ev.editable = e.editable === true;
        return ev;
      });
      success(events);
    })
    .fail(function () {
      failure(new Error("Schedule/event-feed failed"));
    });
}

// Status-icon spans (empty / partial / overbooked / linked / autoplaylist /
// rebroadcast / now-playing) for an event, mirroring the FC1.5 eventRender()
// logic (full-calendar-functions.js).  `withTitles` adds the title="" tooltips
// FC1.5 used in month view; day/week view gets dynamic rtTooltips instead (via
// addQtipsToIcons in eventDidMount).  Returns an array of <span> DOM nodes.
function fc6StatusIcons(event, withTitles) {
  var p = event.extendedProps || {};
  var nodes = [];
  function icon(cls, title) {
    var s = document.createElement("span");
    s.className = "small-icon " + cls;
    if (withTitles && title) {
      s.setAttribute("title", title);
    }
    return s;
  }
  if (p.rebroadcast === 1) {
    // a rebroadcast only gets the rebroadcast icon (no fill-state icons)
    nodes.push(icon("rebroadcast"));
  } else {
    var linked = !!p.linked;
    var auto = p.show_has_auto_playlist === true;
    if (p.show_empty === 1) {
      if (linked) {
        nodes.push(icon("linked"));
        nodes.push(icon("show-empty", $.i18n._("Show is empty")));
      } else if (auto) {
        nodes.push(
          icon("autoplaylist", $.i18n._("Show has an automatic playlist")),
        );
      } else {
        nodes.push(icon("show-empty", $.i18n._("Show is empty")));
      }
    } else if (p.show_partial_filled === true) {
      if (linked) {
        nodes.push(icon("linked"));
        nodes.push(
          icon("show-partial-filled", $.i18n._("Show is partially filled")),
        );
      } else if (auto) {
        nodes.push(
          icon("autoplaylist", $.i18n._("Show has an automatic playlist")),
        );
      } else {
        nodes.push(
          icon("show-partial-filled", $.i18n._("Show is partially filled")),
        );
      }
    } else if (p.percent > 100) {
      var overTitle = $.i18n._(
        "Shows longer than their scheduled time will be cut off by a following show.",
      );
      if (linked) {
        nodes.push(icon("linked"));
        nodes.push(icon("show-overbooked", overTitle));
      } else if (auto) {
        nodes.push(
          icon("autoplaylist", $.i18n._("Show has an automatic playlist")),
        );
      } else {
        nodes.push(icon("show-overbooked", overTitle));
      }
    } else {
      if (linked) {
        nodes.push(icon("linked"));
      } else if (auto) {
        nodes.push(
          icon("autoplaylist", $.i18n._("Show has an automatic playlist")),
        );
      }
    }
  }
  if (p.nowPlaying === true) {
    nodes.push(icon("now-playing"));
  }
  return nodes;
}

// Build + inject the time-interval dropdown (1/5/10/15/30/60m) into the
// timeGrid top-left axis corner, mirroring FC1.5's viewDisplay().  Re-injected
// on every datesSet (the header corner is rebuilt on navigation/view switch);
// a no-op in month view (no time axis).  Changing it sets slotDuration live and
// persists the preference (Schedule/set-time-interval).
function fc6InjectIntervalDropdown() {
  if (!scheduleFc6) {
    return;
  }
  var corner = scheduleFc6.el.querySelector(".fc-timegrid-axis-frame");
  if (!corner) {
    return; // not a timeGrid view (month has no axis corner)
  }
  if (corner.querySelector(".schedule_change_slots")) {
    return; // already injected in this corner
  }
  var $select = $(
    '<select class="schedule_change_slots input_select"/>',
  ).css("width", "100%"); // fill the (narrow) axis corner; final styling later
  [1, 5, 10, 15, 30, 60].forEach(function (m) {
    $select.append(
      '<option value="' + m + '">' + $.i18n._(m + "m") + "</option>",
    );
  });
  $select.val(String(fc6SlotMin));
  $select.on("change", function () {
    var v = parseInt($(this).val(), 10) || 30;
    fc6SlotMin = v;
    scheduleFc6.setOption("slotDuration", "00:" + pad(v, 2) + ":00");
    $.post(baseUrl + "Schedule/set-time-interval/format/json", {
      timeInterval: v,
    });
    if (typeof calendarPref !== "undefined" && calendarPref) {
      calendarPref.timeInterval = v;
    }
    // the slotDuration re-render can rebuild the corner -> re-inject, keeping
    // the new selection
    window.setTimeout(fc6InjectIntervalDropdown, 0);
  });
  $(corner).empty().append($select);
}

// Week-view title formatter (FC6 titleFormat callback).  FC6's own range
// formatting drops the ordinal period on the German start day ("1 – 7. Juni
// 2026" instead of "1. – 7. Juni 2026") because it renders only the differing
// field (a bare day number, which German Intl prints without the "."), and we
// must NOT post-process the rendered title — FC6 manages it through a preact
// virtual DOM, so mutating the node corrupts reconciliation (the title then
// accumulates across navigations).  Instead we let FC6 render our return value.
// Intl.formatRange is locale-correct for every language and keeps the period.
// The end day is computed as start + 6 days (a week is always 7) to sidestep
// FC6's inclusive/exclusive end-marker ambiguity; markers are UTC-based, so the
// ms arithmetic is DST-safe and must be formatted with timeZone:"UTC".
function fc6WeekTitle(arg) {
  var locale = fc6Locale();
  var opts = {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  };
  var start = arg && arg.start && arg.start.marker ? arg.start.marker : null;
  if (!start) {
    return "";
  }
  var end = new Date(start.getTime() + 6 * 24 * 60 * 60 * 1000);
  var fmt = new Intl.DateTimeFormat(locale, opts);
  var str =
    typeof fmt.formatRange === "function"
      ? fmt.formatRange(start, end)
      : fmt.format(start) + " – " + fmt.format(end);
  if (locale === "de") {
    // FC1.5/operator want a spaced en-dash; German Intl ranges have no spaces
    str = str.replace(/\s*[–-]\s*/, " – ");
  }
  return str;
}

// FC6 packs back-to-back shows (end == next start) into half-width columns even
// with slotEventOverlap:false — it treats the touch-boundary as a shared column,
// so the following show renders inset.  A radio schedule never has truly
// overlapping shows, so pin every event harness to the full column width.  Same
// fix as the embed Multi-View widget (css/embed/now-playing-widget.css), incl.
// its caveat: inset-inline only — adding width:100% breaks FC's internal layout
// and the events vanish.  Injected from JS so all FC6-specific styling stays
// with the FC6 code while it lives behind ?fc6=1; promote to a stylesheet when
// FC1.5 is removed (Phase c).
function fc6InjectOverlapCss() {
  if (document.getElementById("fc6-schedule-overlap-css")) {
    return;
  }
  var style = document.createElement("style");
  style.id = "fc6-schedule-overlap-css";
  style.textContent =
    "#schedule_calendar .fc-timegrid-event-harness{" +
    "inset-inline-start:0 !important;inset-inline-end:0 !important;}";
  document.head.appendChild(style);
}

function buildScheduleFc6(data) {
  var el = document.getElementById("schedule_calendar");
  if (!el || !window.FullCalendar) {
    return;
  }
  fc6InjectOverlapCss();
  var legacyView = getTimeScalePreference(data); // agendaDay/agendaWeek/month
  var slotMin = getTimeIntervalPreference(data); // minutes
  var offset = parseInt(data.calendarInit.timezoneOffset, 10);
  fc6SlotMin = slotMin > 0 ? slotMin : 30; // guard a missing/NaN preference

  if (scheduleFc6) {
    scheduleFc6.destroy();
  }

  scheduleFc6 = new FullCalendar.Calendar(el, {
    initialView: FC6_VIEW_FROM_LEGACY[legacyView] || "timeGridDay",
    locale: fc6Locale(),
    firstDay: parseInt(data.calendarInit.weekStartDay, 10) || 0,
    // week-view title: format it ourselves (vdom-safe via FC6's titleFormat) so
    // the German start day keeps its ordinal period — see fc6WeekTitle
    views: {
      timeGridWeek: { titleFormat: fc6WeekTitle },
    },
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridDay,timeGridWeek,dayGridMonth",
    },
    buttonText: {
      today: $.i18n._("Today"),
      month: $.i18n._("Month"),
      week: $.i18n._("Week"),
      day: $.i18n._("Day"),
    },
    nowIndicator: true,
    // station time for "now" / "today" (replaces the FC1.5 serverTimezoneOffset
    // hand-patch); the server feeds naive station-local event times.
    now: function () {
      return adjustDateToServerDate(new Date(), offset);
    },
    allDaySlot: false,
    // back-to-back shows must render full-width side by side, not inset/
    // overlapping (FC6 default true insets the following event) — same fix the
    // embed Multi-View widget uses.  Also keeps the fill bar at full width.
    slotEventOverlap: false,
    slotDuration: "00:" + pad(fc6SlotMin, 2) + ":00",
    slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    expandRows: true,
    // contentHeight (not height) so the grid area — excluding the header
    // toolbar — fills to the page bottom, matching FC1.5's contentHeight.
    // Same offset on init and resize so there is no jump when the window moves.
    contentHeight: $(window).height() - 200 - 24,
    windowResize: function () {
      if (scheduleFc6) {
        scheduleFc6.setOption("contentHeight", $(window).height() - 200 - 24);
      }
    },
    // calendar-level editable enables the drag/resize interaction; per-event
    // editable (set explicitly in getScheduleFc6Events) decides which shows
    // actually move.  eventDrop / eventResize below persist the change.
    editable: true,
    events: getScheduleFc6Events,

    // create-show: adapt FC6 dateClick -> the legacy dayClick() pre-fill, which
    // opens the add-show form (recurrence options unchanged).  The view object
    // only needs .name; serverTimezoneOffset is already set by
    // createFullCalendar() before this builds.
    dateClick: function (info) {
      if (typeof dayClick !== "function") {
        return;
      }
      var legacy = FC6_VIEW_TO_LEGACY[info.view.type] || "agendaDay";
      dayClick(info.date, info.allDay, info.jsEvent, { name: legacy });
    },

    // move a show: POST the day + minute delta (from the FC6 Duration) to
    // move-show; the backend validates (overlaps etc.) and on error we revert
    // the drag.  Mirrors the legacy eventDrop() (full-calendar-functions.js).
    eventDrop: function (info) {
      $.post(
        baseUrl + "Schedule/move-show/format/json",
        {
          day: info.delta.days,
          min: Math.round(info.delta.milliseconds / 60000),
          showInstanceId: info.event.id,
        },
        function (json) {
          if (json.show_error == true) {
            alertShowErrorAndReload();
          }
          if (json.error) {
            alert(json.error);
            info.revert();
          }
          scheduleRefetchEvents(json);
        },
      );
    },

    // resize a show's duration: POST the end-edge delta to resize-show; on error
    // revert.  Mirrors the legacy eventResize(); showId comes from
    // extendedProps (FC6 keeps non-standard fields there).
    eventResize: function (info) {
      $.post(
        baseUrl + "Schedule/resize-show/format/json",
        {
          day: info.endDelta.days,
          min: Math.round(info.endDelta.milliseconds / 60000),
          showId: info.event.extendedProps.showId,
          instanceId: info.event.id,
        },
        function (json) {
          if (json.show_error == true) {
            alertShowErrorAndReload();
          }
          if (json.error) {
            alert(json.error);
            info.revert();
          }
          scheduleRefetchEvents(json);
        },
      );
    },

    // post-render enhancement (FC6 renders the default time/title chip):
    // status icons + jQuery-UI fill bar + hover tooltips + data attributes.
    // Faithful port of the FC1.5 eventRender()/eventAfterRender()
    // (full-calendar-functions.js); reads the same fields from extendedProps.
    eventDidMount: function (arg) {
      var $el = $(arg.el);
      var p = arg.event.extendedProps || {};

      $el.addClass("fc-show-instance-" + arg.event.id);
      if (p.showId != null) {
        $el.attr("data-show-id", p.showId);
      }
      if (p.linked != null) {
        $el.attr("data-show-linked", p.linked);
      }
      // instance data the left-click context menu reads ($el.data("event")) —
      // same contract as FC1.5 eventRender (schedule.js $.contextMenu build())
      $el.data("event", {
        id: arg.event.id,
        showId: p.showId,
        linked: p.linked,
      });

      var isMonth = arg.view.type === "dayGridMonth";
      var isTimeGrid =
        arg.view.type === "timeGridDay" || arg.view.type === "timeGridWeek";

      // fill bar: day/week only, matching FC1.5 (agendaDay/agendaWeek).
      // Insert it directly below the show name (inside the slot), not pinned to
      // the bottom — FC6 flex-grows the title container, so append to the bottom
      // would push the bar outside the slot.
      if (isTimeGrid && typeof $.fn.progressbar === "function") {
        var $title = $el.find(".fc-event-title").first();
        if (!$el.find(".fc-show-fill-bar").length) {
          var $bar = $("<div/>", { class: "fc-show-fill-bar" })
            .height("5px")
            .width("95%")
            .css("margin-top", "1px")
            .css("margin-left", "auto")
            .css("margin-right", "auto");
          if ($title.length) {
            $title.after($bar);
          } else {
            $el.find(".fc-event-main-frame, .fc-event-main").first().append($bar);
          }
          $bar.progressbar({ value: p.percent || 0 });
        }
      }

      // status icons: before the time (day/week) or after the title (month),
      // relative to FC6's default event nodes — same as FC1.5
      var icons = fc6StatusIcons(arg.event, isMonth);
      if (icons.length) {
        if (isMonth) {
          var $title = $el.find(".fc-event-title").first();
          if ($title.length) {
            $title.after(icons);
          } else {
            $el.find(".fc-event-main").first().append(icons);
          }
        } else {
          var $time = $el.find(".fc-event-time").first();
          if ($time.length) {
            $time.before(icons);
          } else {
            $el
              .find(".fc-event-main-frame, .fc-event-main")
              .first()
              .prepend(icons);
          }
        }
      }

      // hover tooltips on the status icons (rtTooltip) — same as eventAfterRender
      if (typeof addQtipsToIcons === "function") {
        $el.find(".small-icon").each(function () {
          addQtipsToIcons($(this), arg.event.id);
        });
      }
    },

    // persist the view preference (legacy name) when the view changes, and
    // (re)inject the time-interval dropdown into the timeGrid corner
    datesSet: function (arg) {
      var legacy = FC6_VIEW_TO_LEGACY[arg.view.type];
      if (
        legacy &&
        typeof calendarPref !== "undefined" &&
        calendarPref &&
        calendarPref.timeScale !== legacy
      ) {
        calendarPref.timeScale = legacy;
        $.post(baseUrl + "Schedule/set-time-scale/format/json", {
          timeScale: legacy,
        });
      }
      // deferred so the timeGrid axis corner is painted before we inject
      window.setTimeout(function () {
        fc6InjectIntervalDropdown();
        // (re)add the "+ New Show" toolbar button — FC6 rebuilds the toolbar on
        // view switch, so re-add it here (makeAddShowButton is idempotent).
        // Same admin gate as FC1.5's viewDisplay().
        if (
          typeof makeAddShowButton === "function" &&
          typeof userType !== "undefined" &&
          (userType === "S" || userType === "A" || userType === "P")
        ) {
          makeAddShowButton();
        }
      }, 0);
    },
  });

  scheduleFc6.render();
}

// Enable via ?fc6=1 — FC1.5 stays the default fallback until FC6 is verified.
window.SCHEDULE_USE_FC6 = /[?&]fc6=1/.test(window.location.search);
